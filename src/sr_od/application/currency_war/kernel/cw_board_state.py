"""货币战争 BoardState 局内记录(迁移批次一骨架)。

**正本** = ``docs/develop/currency_war/design/BoardState-数据结构设计.md``
(下按节号引用)。BoardState = 当前仍为真的局内已知事实快照:单例,每局新建,
只描述「此刻」;画面 op 与决策 op 写,策略器读(设计 §1)。历史序列归遥测,
不经本结构。

**与现役 GameState 的关系**:并行记录,本批(迁移批次一,设计 §8.7)不切
消费——GameState 消费者行为零变化;消费切换归迁移批次二。字段准入按设计
§8.8 治理三件:派生量(席空数/席满判定/board 下档阈值)是计算函数不存储;
识别质量位是写入闸门不存储(失读统一口径 = §2.2 carried/机制性 None)。

**三个关键结构**(设计 §2.4,随本批建立):
1. 预期条目表(:class:`PendingEntry`)——逻辑写入两步机制的本体(§2.5):
   expect 记待核实预期(字段值不动,策略器读不到),核对通过经 confirm
   转正写入(source=logic),失败经 discard_expected 清账(观察赢,§2.3)。
2. 帧观察完整度标注 + 心跳——标注(full/view/none)消费即清;停更检测
   哨兵用只增不减的写点序号 :attr:`BoardState.write_seq`,不用标注现值。
3. bs_schema——域粒度版本映射(缺域键 = 该域未建模,§3.7.1)。

**单例宿主** = session 旁表(:func:`board_state_of`;同 ``cw_exec_state``
旁表模式,弱引用表 + 桩面兜底)——session 对象 = 局身份,新局新 session
即天然新建,符合「单例,每局新建」(§1/§6.2)。

**sim 合成口** = :func:`synthesize_from_game_state`:sim 以 GameState 真值
合成时同样记 observation,evidence 恒带 ``sim:synthesized``(§2.1);
bench 槽位保序映射——记录模型按实机真值箱占席(§3.2.5),不采 sim
「无箱实体」的内部口径约定。
"""
from __future__ import annotations

import contextlib
import dataclasses
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    ActiveEffectInventory,
)

if TYPE_CHECKING:
    # 仅类型注解引用(项目规范);运行时按鸭子类型读 GameState 属性,
    # 避免与 cw_state 建立运行时依赖(cw_state 将来消费本模块时不成环)。
    from sr_od.application.currency_war.kernel.cw_state import GameState


# ============================================================ 常量

#: 备战席容量默认恒 9,不随等级/职级变化(§3.2.5;现役同口径常量 =
#: ``cw_state.BENCH_CAPACITY``)。唯一改写源 = 节省工位时限效果(激活期 3、
#: 3 节点后自动回 9,经效果账本 §5.1 逻辑写入)。
BENCH_CAPACITY_DEFAULT: int = 9

#: 行级 schema 版本(§3.7.1)。域版本映射见 ``DEFAULT_BS_SCHEMA``。
BS_SCHEMA_VERSION: int = 1

#: 域粒度版本映射的当前全集(缺域键 = 该域未建模,禁建「None=未建模」占位
#: 字段,§2.2/§8.8)。域增删或字段语义破坏性变更时 bump 对应域版本。
DEFAULT_BS_SCHEMA: dict[str, int] = {
    'node': 1,              # node/node_path(§3.2.1/§3.2.2)
    'units': 1,             # front_row/back_row/bench/back_layout(§3.2.3-§3.2.7)
    'economy': 1,           # gold/level/xp/streak/hp/level_up_cost(§3.2.9-§3.2.13)
    'match_facts': 1,       # 职级/对局类型/敌人难度/boss/词缀/环境/持卡/board(§3.1/§3.2.6/§3.2.14/§3.2.20)
    'refresh_counters': 1,  # 商店刷新计数组(§3.3.6-§3.3.9,写入=仅逻辑)
    'node_screen_refresh': 1,  # 节点屏刷新计数组(§3.4.1-§3.4.4;遭遇/补给/环境/策略逐卡)
    'inventory': 1,         # equips/consumables/免战牌(§3.2.15/§3.2.16/§3.2.19〔勘误:免战牌正本=effect_inventory.remaining_uses,§8.6-3——本域不含其字段〕)
    'spheres': 1,           # 奖励球(§3.2.8,不占席)
    'substate': 1,          # 分类子态/事件浮层(§3.2.17/§3.6.1)
    'shop': 1,              # 商店开态 payload(§3.3)
    'encounter': 1,         # 遭遇屏 payload(§3.4.1)
    'supply': 1,            # 补给屏 payload(§3.4.2)
    'event_choices': 1,     # 十事件屏 chosen_*(§3.4/§4 事件选择)
    'settlement': 1,        # 结算真值组 + hp 保底事件位(§3.5)
    'effects': 1,           # 在场效果激活账本(§5.1,非 Field 载体)
}

#: 画面附加域(§2.2 显式例外):语义 = 「当前画面的 payload,非当前画面
#: =None」——离开画面置 None 是结构事实非失读,不受 carried 硬边界辖。
_PAYLOAD_DOMAINS: frozenset[str] = frozenset({'shop', 'encounter', 'supply'})

#: 帧观察完整度三档(§2.4 关键结构 2)。
FrameObsLevel = Literal['full', 'view', 'none']

#: 来源四分类字面量(§2.1)。
FieldSource = Literal['observation', 'logic', 'carried', 'prior']

#: sim 合成口统一 evidence 标记(§2.1:sim 侧真值合成恒带)。
SIM_SYNTHESIZED: str = 'sim:synthesized'

#: 字段值类型参数(Field 泛型;值域由各字段注解承载,运行期不做 isinstance
#: 门——观察值类型由写入端调用点保证)。
_T = TypeVar('_T')


# ============================================================ 字段容器


@dataclass(frozen=True)
class Field(Generic[_T]):
    """一个字段:值 + 来源 + 可选源注记。只存正式值——待核实的预期不在这里
    (§2.5,预期走 :meth:`BoardState.expect` 入预期条目表)。

    - observation = 亲眼看到的(识别结果/sim 真值合成,evidence 恒带标记);
    - logic = 决策动作的预期效果,经核对点确认后写入,**保持 logic 不翻
      observation**(§8.1),直到下一次观察覆盖;
    - carried = 沿用上次好值,evidence 必带 ``carried:<来源帧>``
      (§2.1/§2.2 失读处置①);
    - prior = 历史遥测先验(开局 hp,§3.1.6),evidence 必带 ``prior:<来源>``;
      仅限显式申报条目,禁扩散。

    frozen = 帧替换语义的结构保证(§2.4):写入只能经 BoardState API 以
    写时刻现引用为基底换新帧,禁原地改旧帧后跨耗时段写回。
    """

    value: Any | None = None
    source: FieldSource = 'observation'
    evidence: str | None = None


@dataclass(frozen=True)
class PendingEntry:
    """预期条目表一条(§2.4 关键结构 1;五键对齐现役 ExpectedEntry,
    ``cw_expected_state.ExpectedEntry``)。

    - path = 字段名寻址(本模块字段是定长 schema,名即路径);
    - value = 待核实的预期值(§2.5:执行后应该变成什么样);
    - confirm_point = 绑定的核对点——条目只在绑定的核对点可确认转正;
    - group_id = 组内条目全有全无清账,禁单字段半确认中间态;
    - at_round = 轮键('p{plane}-r{round}' 形,登记期快照);
    - produced_by = 产生者(op 名/sim 段名,留证用)。
    """

    path: str
    value: Any
    confirm_point: str = 'prep_obs'
    group_id: str = ''
    at_round: str = ''
    produced_by: str = ''


# ============================================================ 单位与槽位(§8.2)


@dataclass(frozen=True)
class Unit:
    """一个单位(前台/后台通用):角色带星级与装备。

    **阵营不存**(§3.2.3/§8.6-7):阵营是角色静态属性,由 char_id 查角色
    注册表(cw_chars)派生;唯一例外开拓者形态随排(前台=记忆/后台=欢愉),
    由 char_id+当前排推导(ADR-0158)。禁在 Unit 另存阵营(防注册表双源)。
    """

    char_id: str
    star: int                       # 星级 1..3(合成上限;观察期快照)
    equips: list[str] = field(default_factory=list)
    # [索引定义] slot = 屏幕槽位号,行内 1 基(前排 1..4/后排 X 槽 1..N/
    # 备战栏 1..9,坐标 = screen_info 区域);与现役 deployed 容器 0 基下标
    # (ADR-0392:0-3 前台/4-9 后台)的换算归迁移映射层(批次二)。
    # 取值时机 = 观察期快照。
    slot: int = 0


@dataclass(frozen=True)
class BenchSlot:
    """备战席一槽:四种内容之一(统一槽位视图,占位真值一份,§3.2.5)。

    占席真值 = :func:`slot_occupies`:unit/supply_box/tome 占 1 槽、empty
    不占(奖励球不占席——它是点击目标不是席位居民,§3.2.5)。sim 合成帧
    「箱不占席」= sim 无箱实体的内部口径约定,**记录模型按实机真值**。
    """

    kind: Literal['unit', 'supply_box', 'tome', 'empty'] = 'empty'
    unit: Unit | None = None        # kind='unit' 时有效
    # tome=星徽秘典:席位内容物之一,占席待实机证实(§3.2.5——画面档案只有
    # 弹窗、无席位区域锚);按「席位内容物」建模即占席,证伪时改归不占席域。


@dataclass(frozen=True)
class BenchView:
    """备战席统一槽位视图 = 槽位表 + 容量(§8.2 实现注意:capacity 随效果
    改写,默认恒 9;唯一临时改写 = 节省工位时限效果,§3.2.5)。

    槽位表按物理槽位 1..capacity 定位:slots[i] = 物理槽 i+1(0 基列表下标
    ↔ 1 基屏幕槽位,与现役 ``cw_state.bench`` 下标语义同构,ADR-0316)。
    席空数/席满判定 = 派生计算(:func:`bench_free_slots`/:func:`bench_is_full`),
    不入 schema(§8.8 字段准入③)。
    """

    slots: list[BenchSlot] = field(default_factory=list)
    capacity: int = BENCH_CAPACITY_DEFAULT


@dataclass(frozen=True)
class SphereSight:
    """奖励球观察面(§3.2.8):数量/颜色——交互机会信号,**不占席**。

    colors 为画面读取到的颜色标签元组(词表随识别线建线批定型,先以
    不透明字符串承载);count None = 未读到。
    """

    count: int | None = None
    colors: tuple[str, ...] = ()


# ============================================================ 节点与画面载荷(§8.3)


@dataclass(frozen=True)
class NodeKey:
    """当前节点坐标系(跨位面 round 重启,plane 必在键内,§3.2.1)。"""

    plane: int = 1
    # [索引定义] round_num = 位面内轮次,1 基(跨位面重启,与 plane 组成
    # 复合键);取值时机 = 备战帧节点条现读(权威写端,§3.2.1)。
    round_num: int = 1
    kind: str = 'prep'              # battle/encounter/supply/reward/boss/prep/…


@dataclass(frozen=True)
class ShopCard:
    """商店一张牌(§3.3.1)。

    升星预览不入存储——派生计算函数(bench/rows+注册表合成规则自算,
    merge_mechanics §2.7 口径);✦ 读取器读数仅核对信号(ADR-0416 降级)。
    牌位点击坐标不入存储——坐标单一真相源 = screen_info「商店牌-N」区域
    (cw_obs_core.shop_card_click_points)。
    """

    name: str = ''
    faction: str = ''
    cost: int = 0
    star: int = 1
    # 信源位(§3.3.1):**原值透传不折叠**(P2-4 落地审:证据分级禁丢)——
    # 词表 = 现役 GameState.ShopCard.cost_source 三值:badge=费用徽章直读 /
    # roster=注册表查表(sim/replay 构造缺省) / roster_fallback=徽章失读
    # 退查表。设计的两值口径(badge=徽章直读 vs registry=注册表查表)的
    # 归并消费归批次二,消费前必须保住 roster_fallback 的「徽章失读」分级。
    cost_source: str = 'badge'


@dataclass(frozen=True)
class ShopPayload:
    """商店开态附加(§3.3):五张牌与概率条。非当前画面 = None(§2.2 例外)。"""

    cards: list[ShopCard] = field(default_factory=list)            # 恒 5 张
    refresh_probs: dict[int, float] = field(default_factory=dict)  # 费用档→概率(§3.3.2 契约)


@dataclass(frozen=True)
class EncounterPayload:
    """遭遇屏附加(§3.4.1):分支选项。options = (难度档 1..6, 奖励文本)。"""

    options: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class SupplyPayload:
    """补给屏附加(§3.4.2):列数动态——通常4选1,效果改写3-5,勿写死(cw_node_obs.py:279-282)。options = (角色, 装备, 有钻石)。"""

    options: list[tuple[str, str, bool]] = field(default_factory=list)


@dataclass(frozen=True)
class Settlement:
    """结算屏真值组(§3.5.1):战斗后覆盖更新的数据源。

    伤害不入本结构——遥测面(字段准入①:无决策消费,设计 §3.5.1 明示);
    金仅胜局有值(败局结算屏无收入面板);等级/经验仅胜局结算页可读
    (cw_settlement_obs.py:118-135)。
    """

    hp_after: int | None = None
    streak_after: int | None = None                 # 带符号(§3.2.12)
    killed: bool | None = None
    progress_delta: int | None = None
    gold: int | None = None                         # 仅胜局(§3.5.1)
    level: int | None = None                        # 仅胜局结算页可读
    xp: int | None = None


# ============================================================ 缺陷台账挂点(§2.3)

#: 缺陷行缓冲(进程内,供装配点取走/测试断言);容量截断防长局堆积。
_DEFECT_BUFFER: list[dict] = []
_DEFECT_BUFFER_CAP: int = 200
#: 逐行外送钩子(生产装配点接遥测;**缺省关** = 只缓冲不外送——测试纪律
#: 「缺省关+显式接通」,生产武装点挂迁移批次二装配面)。
_DEFECT_SINK: Callable[[dict], None] | None = None


def set_defect_sink(fn: Callable[[dict], None] | None) -> None:
    """注入缺陷台账外送钩子(None = 关,缺省态;同 ``cw_expected_state
    .set_evidence_sink`` 注入槽模式)。"""
    global _DEFECT_SINK
    _DEFECT_SINK = fn


def consume_defect_sink() -> list[dict]:
    """取走并清空缺陷行缓冲(装配点消费口;防跨局残留)。"""
    rows = list(_DEFECT_BUFFER)
    _DEFECT_BUFFER.clear()
    return rows


def _emit_defect(*, field_name: str, expected: Any, actual: Any,
                 evidence: str | None,
                 kind: str = 'observe_vs_logic_mismatch') -> None:
    """缺陷台账留证(§2.3 观察赢;kind 扩展 = 预期核对点失配
    expect_vs_obs_mismatch,§2.5 两步闭环)。best-effort:
    外送钩子异常不阻塞观察主链。"""
    row: dict = {'kind': kind, 'field': field_name,
                 'expected': expected, 'actual': actual,
                 'observed_evidence': evidence}
    _DEFECT_BUFFER.append(row)
    if len(_DEFECT_BUFFER) > _DEFECT_BUFFER_CAP:
        del _DEFECT_BUFFER[:len(_DEFECT_BUFFER) - _DEFECT_BUFFER_CAP]
    if _DEFECT_SINK is not None:
        try:
            _DEFECT_SINK(dict(row))
        except Exception as e:  # noqa: BLE001  留证 best-effort
            log.debug(f'[cw-bs] defect sink skip: {e}')
    log.warning(f'[cw!][bs] 观察覆盖 logic 失配:{field_name} '
                f'预期[{expected}] 实读[{actual}](§2.3 观察赢)')


# ============================================================ 派生计算(不存储)


def slot_occupies(kind: str) -> bool:
    """槽位占席谓词(§3.2.5 实机真值):unit/supply_box/tome 占 1 槽,
    empty 不占。席满判定/席空数同源派生的底座。"""
    return kind != 'empty'


def bench_free_slots(bs: BoardState) -> int | None:
    """席空数(§3.2.5 派生计算,不入 schema)。bench 从未观察 → None
    (= 不确定,**禁猜 0**);已观察 → max(capacity − 占席槽数, 0)。"""
    view = bs.bench.value
    if view is None:
        return None
    used = sum(1 for s in view.slots if slot_occupies(s.kind))
    return max(view.capacity - used, 0)


def bench_is_full(bs: BoardState) -> bool | None:
    """席满判定 = 同源派生(席空数==0,§3.2.5;含商店开态满栏买牌判定)。
    bench 未观察 → None(不确定);「备战席已满」警告 OCR 不做识别
    (玩家裁定 2026-09-09,现役 read_bench_full 通道退役挂批次二)。"""
    free = bench_free_slots(bs)
    return None if free is None else free == 0


def board_next_tier_of(board_factions: dict[str, int]) -> dict[str, int]:
    """board 下档阈值派生(§3.2.6/§8.8 准入③:计算函数不存储)。

    语义 = 左面板「X/Y」的 Y:对注册表 ``FACTIONS[].tiers`` 取 >当前人数
    的最小档,无更高档不计入。**本函数 = 该推导的 kernel 单一源**——
    迁移批次二起,obs computed 支(cw_observation read_game_state)与
    sim 观测键(engine_p1._board_next_tier_of,ADR-0488 硬依赖键供给)
    均委托至此,禁第三份推导(sim 侧旧注释「与 obs computed 支同一式」
    的对齐义务由委托结构保证)。
    """
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    out: dict[str, int] = {}
    for _f, _c in board_factions.items():
        _tiers = FACTIONS[_f].tiers if _f in FACTIONS else ()
        _nt = next((t for t in _tiers if t > _c), 0)
        if _nt:
            out[_f] = _nt
    return out


# ============================================================ cost_source 三值归并(§3.3.1/§8.6-9)

#: cost_source 消费词表二值(§3.3.1):badge=徽章直读 / registry=注册表查表。
COST_SOURCE_BADGE: str = 'badge'
COST_SOURCE_REGISTRY: str = 'registry'


def cost_source_group(cost_source: str) -> str:
    """cost_source 三值 → 消费二值归并(§8.6-9,迁移批次二)。

    存储侧保三值不折叠(roster_fallback 的「徽章失读」证据分级禁丢,
    P2-4 落地审);消费侧归并 = 对**费用数值**的可信度只分两域——badge
    徽章直读与 registry 注册表查表(含 roster_fallback 失读退查)给出的
    都是角色招募费真值,按费用消费的分支(估价/卖价/合成费用档)无需
    区分后两者。归并不丢证据:原值仍在 :attr:`ShopCard.cost_source`,
    失配归因/缺陷台账按原值分档。未知值保守归 registry(与 reader 缺省
    语义同向;词表外值 = 上游漂移信号,归因时看原值)。
    """
    return COST_SOURCE_BADGE if cost_source == COST_SOURCE_BADGE \
        else COST_SOURCE_REGISTRY


# ============================================================ 刷新执行事实组(§3.3.5-§3.3.9)

def record_refresh_execution(bs: BoardState, *, free: bool,
                             frame: str = '') -> None:
    """RefreshShop op 执行回执 → 刷新计数组逻辑写入(§3.3.6-§3.3.8,
    写入=仅逻辑;接线点 = cw_op_buy_cards 执行落地门,迁移批次二)。

    行为口径(§4 RefreshShop 行为申报配套):
    - total_refresh_count 恒 +1(§3.3.8:付费+免费全量);
    - free=True(免费帧):**不写** paid_refresh_count(§3.3.7 该键=付费
      累计,长线利好触发载体,免费帧混入即计数毒化)并消耗免费余额
      (§3.3.6 余额 −1,下限 0);
    - free=False:paid_refresh_count +1;
    - 计数从未写过(值 None)按 0 基线起算——计数器是局内单调累计,
      0 基线是构造事实非观察兜底(与「禁兜底改值」的观察域无关)。

    免费判定输入 = 调用方(执行侧按免费余额/效果账本判定后传入;
    余额未建模局恒 paid = 现状保守形态,行为与接线前逐位一致)。
    frame = 轮键留证(写入 evidence)。
    """
    _ev = f'refresh_exec@{frame}' if frame else 'refresh_exec'
    total = bs.total_refresh_count.value or 0
    bs.write_logic(bs.total_refresh_count, int(total) + 1,
                   produced_by='RefreshShop', evidence=_ev)
    if free:
        balance = bs.free_refresh_balance.value or 0
        bs.write_logic(bs.free_refresh_balance, max(int(balance) - 1, 0),
                       produced_by='RefreshShop', evidence=_ev)
    else:
        paid = bs.paid_refresh_count.value or 0
        bs.write_logic(bs.paid_refresh_count, int(paid) + 1,
                       produced_by='RefreshShop', evidence=_ev)


# ============================================================ 备战席观察写端(§3.2.5)


def bench_view_from_obs(bench_chars: list) -> BenchView | None:
    """备战席 SIFT 读链 → BenchView(观察写端的值构造;§3.2.5 观察写端=本屏)。

    - **空集 = 失读非全空**(P2-1 批次二落地审):overlay 残留/动画帧/识别
      退化都会产空集,≠实席真清空——返 None,调用方走 carried(§2.2 处置①;
      先例 = 商店空牌面「宁缺勿造不写」),禁把「9 槽全空」当 observation
      入记录(席空数派生误报 free=9/挂起合成升星预期被空视图误清);
    - 槽位越界条目丢弃并 log 留证(物理槽 1..capacity 外 = 读链漂移信号,
      静默丢弃 = 身份静默丢失);
    - 非 None 返回 = 槽位保序映射(下标 i = 物理槽 i+1,与 sim 合成口同构)。
    """
    if not bench_chars:
        return None
    slots: list[BenchSlot] = [BenchSlot(kind='empty')] * BENCH_CAPACITY_DEFAULT
    for bc in bench_chars:
        s = int(getattr(bc, 'slot', 0) or 0)
        if 1 <= s <= BENCH_CAPACITY_DEFAULT:
            slots[s - 1] = BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=s))
        else:
            log.warning('[cw!][bs-bench] 备战席读链槽位越界丢弃:'
                        'slot=%s char=%s(SIFT/星级读链漂移信号)',
                        s, getattr(bc, 'char_id', '?'))
    return BenchView(slots=slots, capacity=BENCH_CAPACITY_DEFAULT)


# ============================================================ 局终归档快照(§6.2/§8.8)

def archive_snapshot(bs: BoardState) -> dict:
    """局终 BoardState 归档快照(§6.2 局终归档喂遥测,先于连刷重建;
    §8.8 遥测行形状正本的三键:bs_prov/bs_pending/bs_extra)。

    - bs_prov = 非默认来源注记(稀疏化,不逐字段灌满):source 非
      observation、或 observation 带 evidence 的字段才入——默认 observation
      无注记的字段 = 「本帧真读」语义,键面留白;
    - bs_pending = 预期条目表快照(局终尚有挂起预期 = 未闭合写端信号,
      归档保留供判读);
    - bs_extra = 工程结构(schema 版本/域版本/心跳/效果账本规模)+
      全部非 None 字段值(JSON 安全形态,供离线判读)。

    返回 dict 直接入档(由局终装配器并档);序列化失败逐字段跳过
    (归档 best-effort,不阻塞局终流转)。
    """
    prov: dict[str, dict] = {}
    extra_values: dict[str, object] = {}
    for f in dataclasses.fields(bs):
        val = getattr(bs, f.name, None)
        if not isinstance(val, Field):
            continue
        if val.value is not None:
            with contextlib.suppress(Exception):
                extra_values[f.name] = _json_safe(val.value)
        if val.source != 'observation' or val.evidence is not None:
            prov[f.name] = {'source': val.source, 'evidence': val.evidence}
    return {
        'schema_version': bs.schema_version,
        'bs_prov': prov,
        'bs_pending': [dataclasses.asdict(e) for e in bs.pending_entries()],
        'bs_extra': {
            'values': extra_values,
            'bs_schema': dict(bs.bs_schema),
            'write_seq': bs.write_seq,
            'frame_obs': bs.frame_obs,
            'effects_count': len(getattr(bs.effects, 'effects', []) or []),
        },
    }


def _json_safe(value: Any) -> Any:
    """归档值的 JSON 安全化(dataclass → dict;容器递归;其余原样)。"""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _json_safe(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ============================================================ 合成升星预期写端(§3.2.18 窟窿一,修法 a)

def bench_view_of_slots(bench_list: list) -> BenchView:
    """GameState.bench 槽位表(0 基下标 + None 洞)→ BenchView(记录模型
    形状契约;槽 i = 物理槽 i+1,与 sim 合成口同构映射)。投影面用
    (BuyCard 升星预期写端的期望值构造源)。"""
    slots: list[BenchSlot] = []
    for i, bc in enumerate(bench_list or []):
        if bc is None:
            slots.append(BenchSlot(kind='empty'))
        else:
            slots.append(BenchSlot(kind='unit', unit=Unit(
                char_id=str(getattr(bc, 'char_id', '') or ''),
                star=int(getattr(bc, 'star', 1) or 1),
                equips=list(getattr(bc, 'equips', None) or []),
                slot=i + 1)))
    while len(slots) < BENCH_CAPACITY_DEFAULT:
        slots.append(BenchSlot(kind='empty'))
    return BenchView(slots=slots, capacity=BENCH_CAPACITY_DEFAULT)


def detect_merge_upgrade(cur: Any, proj: Any) -> bool:
    """BuyCard 投影是否发生 3 合 1 升星(§3.2.18 修法 a 触发判定;纯函数)。

    判据 = 同名角色投影后最高星级 > 投影前同名最高星——3 份合成是该
    签名的唯一来源(星级只经合成上升;买新卡不抬同名最高星)。合成域 =
    全场(bench+deployed,``cw_state._merge_bench`` 同口径)。级联合并
    (3×1★→2★→…)只看「有抬升」真值,层级数不影响本判定。
    """
    def _max_star(st: Any) -> dict[str, int]:
        best: dict[str, int] = {}
        for c in (list(getattr(st, 'bench', None) or [])
                  + list(getattr(st, 'deployed', None) or [])):
            if c is not None:
                cid = str(getattr(c, 'char_id', '') or '')
                if not cid:
                    continue
                s = int(getattr(c, 'star', 1) or 1)
                if s > best.get(cid, 0):
                    best[cid] = s
        return best
    before, after = _max_star(cur), _max_star(proj)
    return any(after.get(cid, 0) > s for cid, s in before.items())


def reconcile_pending_observation(bs: BoardState, target: Field,
                                  observed: Any, *,
                                  at_point: str) -> str:
    """核对点闭环(§2.5 两步机制的核对半;迁移批次二扩单件 1)。

    对绑定 ``at_point`` 的该字段挂起预期与观察值比对:
    - 一致 → :meth:`confirm` 转正(source=logic;决策推算被核实);
    - 失配 → :meth:`discard_expected` 清账 + 缺陷台账留证
      (kind=expect_vs_obs_mismatch;§2.3 观察赢,观察覆盖已先行写入真值);
    - 无挂起预期或条目绑定其他核对点 → 不动(返回 'none')。

    返回 'confirmed' | 'discarded' | 'none'。
    """
    name = bs._field_name(target)
    entry = bs.expected.get(name)
    if entry is None or entry.confirm_point != at_point:
        return 'none'
    if entry.value == observed:
        bs.confirm(entry, at_point=at_point)
        return 'confirmed'
    bs.discard_expected(entry)
    _emit_defect(kind='expect_vs_obs_mismatch', field_name=name,
                 expected=entry.value, actual=observed,
                 evidence=f'at:{at_point}')
    return 'discarded'


# ============================================================ 结算覆盖写端(§3.5.1)

def apply_settlement_cover(bs: BoardState, *, hp_after: int | None,
                           streak_after: int | None,
                           killed: bool | None = None,
                           progress_delta: int | None = None,
                           gold: int | None = None,
                           level: int | None = None,
                           xp: tuple[int, int] | None = None) -> None:
    """结算屏真值覆盖(§3.5.1;接线点 = cw_screen_battle_wait 结算块,
    迁移批次二任务书件 8)。

    本屏同时是这些字段的覆盖写端:hp(§3.2.13)/streak 带方向真值
    (§3.2.12:备战幅度读数无方向,带方向值只有本写端与逻辑推进)/
    金币仅胜局(§3.2.9,败局结算屏无收入面板)/等级/经验仅胜局结算页
    可读(cw_settlement_obs.py:118-135)。伤害不入本结构(遥测面,
    字段准入①)。全部 observation 写入(真值覆盖)。
    """
    if hp_after is not None:
        bs.observe(bs.hp, int(hp_after))
    if streak_after is not None:
        bs.observe(bs.streak, int(streak_after))
    if gold is not None:
        bs.observe(bs.gold, int(gold))
    if level is not None:
        bs.observe(bs.level, int(level))
    if xp is not None:
        bs.observe(bs.xp, (int(xp[0]), int(xp[1])))
    bs.observe(bs.settlement, Settlement(
        hp_after=hp_after, streak_after=streak_after, killed=killed,
        progress_delta=progress_delta, gold=gold, level=level,
        xp=(int(xp[0]), int(xp[1])) if xp is not None else None))


# ============================================================ 单例宿主


_BS_BY_SESSION: weakref.WeakKeyDictionary[object, BoardState] = \
    weakref.WeakKeyDictionary()
#: 桩面兜底第二级:属性不可写对象(__slots__ 族)的 id() 键 dict
#: (同 cw_exec_state 桩面存储两级结构;挂对象属性优先)。
_BS_BY_SESSION_ID: dict[int, BoardState] = {}
_BS_ATTR = '_cw_board_state'


def board_state_of(session: object) -> BoardState:
    """BoardState 单例访问口(session 旁表;弱引用表 + 桩面兜底,与
    ``cw_exec_state.exec_state_of`` 同构)。

    - session = 局身份:新 session 对象 = 新局 = 新 BoardState(§1 每局新建);
    - None → 一次性空载体(不缓存——None 的 id 恒定,缓存即跨调用串染);
    - 裸 session(测试/sim 桩)→ 惰性建并挂对象自身属性(生命周期随对象)。
    """
    if session is None:
        return BoardState(schema_version=BS_SCHEMA_VERSION)
    try:
        bs = _BS_BY_SESSION.get(session)
    except TypeError:   # 不可弱引用对象(测试桩)
        bs = getattr(session, _BS_ATTR, None)
        if bs is None:
            bs = BoardState(schema_version=BS_SCHEMA_VERSION)
            try:
                setattr(session, _BS_ATTR, bs)
            except (AttributeError, TypeError):
                _BS_BY_SESSION_ID[id(session)] = bs
        return bs
    if bs is None:
        bs = BoardState(schema_version=BS_SCHEMA_VERSION)
        _BS_BY_SESSION[session] = bs
    return bs


# ============================================================ BoardState 单例


@dataclass
class BoardState:
    """局内记录:当前局内状态的唯一一份快照(单例,只描述此刻,§8.4)。

    写入纪律(§2.4):op 层一律经 observe/carry/write_prior/expect/confirm
    API 写入,不直接摸字段;写点以写时刻的单例现引用为基底构造新帧
    (frozen 帧替换——旧 Field 引用保持旧值,持旧引用的读者不被污染)。

    字段集 = §8.4 目标 dataclass + §8.6-3/4 缺口域(迁移批次一补齐):
    开局初值域(§3.1)/十事件屏 chosen_*(§3.4)/商店刷新计数组(§3.3.6-9)/
    节点屏刷新计数组(§3.4.1-4)/持久账本组(§3.2.15/16/19)/board(§3.2.6)/
    level_up_cost(§3.2.11)/back_layout(§3.2.7)/spheres(§3.2.8)/分类子态
    (§3.2.17)/对局类型(§3.1.2)/节点序列台账(§3.2.2)/hp 保底事件位(§3.5.3)。
    """

    schema_version: int              # 行级版本,无默认值(§3.7.1;新局必显式申报)

    # —— 节点 ——
    node: Field[NodeKey] = field(default_factory=Field)          # 当前节点(§3.2.1)
    node_path: Field[list[str]] = field(default_factory=Field)   # 节点类型序台账(§3.2.2;备战帧 node_path 现读=权威写端)

    # —— 单位域(含星级与装备)——
    front_row: Field[list[Unit]] = field(default_factory=Field)  # 前排成员(§3.2.3)
    back_row: Field[list[Unit]] = field(default_factory=Field)   # 后排成员(§3.2.4)
    bench: Field[BenchView] = field(default_factory=Field)       # 备战席统一槽位视图(§3.2.5;capacity 随效果改写)
    back_layout: Field[int] = field(default_factory=Field)       # 后台格数 6/7/8(§3.2.7;域外=8 格超集+superset 标记)

    # —— 经济与成长 ——
    gold: Field[int] = field(default_factory=Field)              # None=不可读(§3.2.9)
    level: Field[int] = field(default_factory=Field)             # 等级(§3.2.10;启发式兜底值禁入——非真读走 carried)
    xp: Field[tuple[int, int]] = field(default_factory=Field)    # (当前级已攒, 升下一级所需)(§3.2.10;同文本两分量成对存)
    streak: Field[int] = field(default_factory=Field)            # 带符号:正=连胜/负=连败(§3.2.12)
    hp: Field[int] = field(default_factory=Field)                # 写入闸 §3.2.13:非真读帧不经 observe(§8.8 假值防线)
    level_up_cost: Field[int] = field(default_factory=Field)     # 单击买经验价(§3.2.11;None=未读到禁兜底)

    # —— 局级事实 ——
    selected_difficulty: Field[str] = field(default_factory=Field)   # 职级,开局写定恒稳(§3.1.1)
    game_mode: Field[str] = field(default_factory=Field)             # 对局类型:标准/超频博弈(§3.1.2;两屏无建档,接线前补档)
    enemy_difficulty: Field[int] = field(default_factory=Field)      # 非单调(§3.2.14)
    plane_bosses: Field[list[str | None]] = field(default_factory=Field)  # 三位面 boss 名,None=该位面无身份(ADR-0398)
    active_env: Field[str | None] = field(default_factory=Field)     # 已选投资环境(§3.2.20/§3.4.3)
    enemy_affixes: Field[list[str]] = field(default_factory=Field)   # 当前词缀名单(§3.1.3;≠投资环境)
    active_strategies: Field[list[str]] = field(default_factory=Field)   # 持有投资策略名单(§3.4.4;品质锚挂建模批)
    board: Field[dict[str, int]] = field(default_factory=Field)      # 上阵羁绊计数(§3.2.6;下档阈值=派生不存储)
    shop_refresh_cost: Field[int] = field(default_factory=Field)     # 刷新费,动态(§3.3.4/ADR-0622 现场 OCR;免费帧不写,None≠0)

    # —— 商店刷新计数组(§3.3.6-§3.3.9;写入=仅逻辑,无 UI 观察通道)——
    free_refresh_balance: Field[int] = field(default_factory=Field)  # 未消耗免费刷新次数(§3.3.6)
    paid_refresh_count: Field[int] = field(default_factory=Field)    # 累计付费刷新(§3.3.7;长线利好触发计数载体)
    total_refresh_count: Field[int] = field(default_factory=Field)   # 累计全部刷新(§3.3.8;二手市场/采购专员计数载体)
    prev_node_spent: Field[bool] = field(default_factory=Field)      # 上节点是否花费(§3.3.9;存款回报条件输入,观察需求)

    # —— 节点屏刷新计数组(P1-2 批次一落地审补;§3.4.1-§3.4.4;字段先入
    # schema,**写端未接**——遭遇/补给刷新已用现役走 exec_state 侧标
    # (cw_exec_state._encounter_refresh_used/_supply_refresh_used),四字段
    # 零写端;接线挂批次三/建模批申报,零写端期间禁按字段值做决策)——
    encounter_refresh_used: Field[int] = field(default_factory=Field)    # 遭遇刷新已用(§3.4.1;cw_screen_encounter 置位口径)
    supply_refresh_used: Field[int] = field(default_factory=Field)       # 补给刷新已用(§3.4.2;「无布局局原生可刷」收窄待证,字段位先申报禁静默)
    env_refresh_used: Field[int] = field(default_factory=Field)          # 环境刷新已用(§3.4.3;观察通道在册 cw_node_obs「剩余次数」)
    strategy_refresh_used: Field[dict[str, int]] = field(default_factory=Field)  # 投资策略逐卡刷新已用(§3.4.4)。**键口径显式申报(迁移批次二)**:键 = 注册表规范卡名(normalize_invest_name 归一后;选名不选 spec.id 的理由 = 效果注册表 STRATEGY_EFFECTS 即以规范名为键,写端 OCR 名经同一归一函数入键,免双坐标系换算)。值域纪律:基线每卡 1 次、例外三族(银金彩环境+2/投资卡族=3/期货族=0/远见=0)以注册表官方全文为唯一口径,禁按基线做核对预期

    # —— 持久账本组(跨画面保留)——
    # ⚠️ 免战牌不在本组(§8.6-3 载体归一,迁移批次二):激活态+剩余次数
    # 正本 = effect_inventory.remaining_uses(§5.1,ActiveEffect.remaining_
    # uses「次数类余量(免战牌×2 等)」,同型躺平/节省工位;批次一骨架的
    # skip_battle_active/remaining 两 Field 已按正本归一移除,消费走
    # bs.effects 查询)。
    equips: Field[list[str]] = field(default_factory=Field)          # 装备库存(§3.2.15)
    consumables: Field[list[str]] = field(default_factory=Field)     # 消耗品库存(§3.2.16)

    # —— 奖励球(§3.2.8,不占席)——
    spheres: Field[SphereSight] = field(default_factory=Field)

    # —— 交互状态 ——
    prep_substate: Field[str] = field(default_factory=Field)     # 分类子态四档(§3.2.17;恢复锁定=会话推断档,写端=接管协议 §6.3)
    event_overlay: Field[str | None] = field(default_factory=Field)  # 'none'=确认无浮层;None=没读到(§3.6.1 双义禁令)

    # —— 画面附加域(当前画面的 payload,非当前画面=None,§2.2 例外)——
    shop: Field[ShopPayload | None] = field(default_factory=Field)
    encounter: Field[EncounterPayload | None] = field(default_factory=Field)
    supply: Field[SupplyPayload | None] = field(default_factory=Field)

    # —— 十事件屏选择结果(§3.4/§4 事件选择:chosen_* 由选择 handler 单次逻辑写入)——
    chosen_encounter: Field[tuple[int, str] | None] = field(default_factory=Field)   # (难度档, 奖励文本)
    chosen_supply: Field[tuple[str, str, bool] | None] = field(default_factory=Field)  # (角色, 装备, 有钻石)
    chosen_megastar: Field[str | None] = field(default_factory=Field)   # 盛会之星(§3.4.5)
    chosen_partner: Field[str | None] = field(default_factory=Field)    # 伙伴(候选阵营)
    chosen_wish: Field[str | None] = field(default_factory=Field)       # 祈愿试炼目标文本(暂无建档,接线前补档)
    chosen_fortune: Field[str | None] = field(default_factory=Field)    # 命运卜者(暂无画面建档)
    chosen_hack: Field[str | None] = field(default_factory=Field)       # 骇入策划(暂无画面建档)
    chosen_expert: Field[str | None] = field(default_factory=Field)     # 专家邀请函
    chosen_tome: Field[str | None] = field(default_factory=Field)       # 星徽秘典弹窗卡名
    chosen_equip: Field[str | None] = field(default_factory=Field)      # 装备三选一(暂无画面建档)

    # —— 结算(战斗后真值覆盖的数据源)——
    settlement: Field[Settlement | None] = field(default_factory=Field)
    hp_floor_triggered: Field[bool] = field(default_factory=Field)   # hp 保底触发事件位(§3.5.3;纯观察登记,无判据载体)

    # ---- 持续型效果账本(§5.1):不走 Field 封装 ----
    # 存储形态 = ActiveEffect 记录列表(现役 cw_effect_inventory 同构)。
    # session 级可变账本,不参与 frozen 帧替换(帧替换管观察/逻辑字段)。
    effects: ActiveEffectInventory = field(default_factory=ActiveEffectInventory)

    # ---- 工程结构(非 Field,§2.4 三个关键结构 + 心跳观察者)----
    # 预期条目表:path → PendingEntry(last-wins 同 path 覆盖)。
    expected: dict[str, PendingEntry] = field(default_factory=dict)
    # 域粒度版本映射(§3.7.1;缺域键 = 该域未建模)。
    bs_schema: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_BS_SCHEMA))
    # 帧观察完整度标注(full/view/none)——消费即清,不当停更哨兵(§2.4)。
    frame_obs: FrameObsLevel = 'none'
    # 心跳载体:写点序号,只增不减(§2.4 停更检测哨兵)。
    write_seq: int = 0
    # 心跳观察者上次采样值(None=未采样);stall 计数 = 连续零推进次数。
    hb_prev_seq: int | None = None
    hb_stall_count: int = 0

    def __post_init__(self) -> None:
        """构造守卫(任务书件 5/§8.6-5):schema_version 正整数 + Field
        冻结不变式断言(帧替换语义的结构前提,破即构造炸错不静默)。"""
        if not isinstance(self.schema_version, int) or self.schema_version <= 0:
            raise ValueError('schema_version 必须为正整数(§3.7.1)')
        probe = Field(value=None)
        try:
            probe.value = 1  # type: ignore[misc]  # 刻意触发冻结守卫
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise RuntimeError('Field 必须保持 frozen(§2.4 帧替换语义被破坏)')

    # —— 写入 API(op 层经此写,不直接摸字段;§8.4)——

    def _field_name(self, target: Field) -> str:
        """现引用 → 字段名(身份匹配)。传非本单例的字段实例 = 调用错,
        显式炸错(禁静默写丢)。"""
        for f in dataclasses.fields(self):
            if getattr(self, f.name) is target:
                return f.name
        raise KeyError('target 不是本 BoardState 的字段现引用'
                       '(须传 bs.xxx;跨单例引用 = 写丢事故)')

    def _swap(self, name: str, new_field: Field) -> None:
        """帧替换写点:换新 frozen 帧 + 心跳推进(只增不减,§2.4)。"""
        setattr(self, name, new_field)
        self.write_seq += 1

    def observe(self, target: Field, value: Any, *,
                evidence: str | None = None) -> None:
        """观察写入:亲眼看,覆盖旧值(§2.1 observation)。

        - value=None 拒绝(§2.2 硬边界:失读不是观察值,走 :meth:`carry`
          或画面附加域 :meth:`leave_screen`;字段一旦有过正式值任何失读
          不得清成 None);
        - 覆盖 logic 来源值且失配 → 缺陷台账留证(§2.3 观察赢),来源
          改回 observation;未核实的预期条目不受影响(§2.3:观察帧不得
          确认或清除预期)。
        """
        if value is None:
            raise ValueError('observe 不接受 None(§2.2:失读走 carry/'
                             'leave_screen,禁清正式值)')
        name = self._field_name(target)
        if target.source == 'logic' and target.value is not None \
                and target.value != value:
            _emit_defect(field_name=name, expected=target.value,
                         actual=value, evidence=evidence)
        self._swap(name, Field(value=value, source='observation',
                               evidence=evidence))

    def carry(self, target: Field, *, frame: str) -> None:
        """失读处置①(§2.2):沿用上次好值,evidence = carried:<来源帧>。
        字段从未读过(处置②机制性 None)→ 保持 None 不写。"""
        if target.value is None:
            return
        name = self._field_name(target)
        self._swap(name, Field(value=target.value, source='carried',
                               evidence=f'carried:{frame}'))

    def write_prior(self, target: Field, value: Any, *,
                    evidence: str) -> None:
        """先验写入(§2.1 prior 类,§3.1.6 开局 hp):evidence 必带
        ``prior:`` 前缀;本类仅限显式申报条目,禁扩散。"""
        if not evidence.startswith('prior:'):
            raise ValueError('prior 写入 evidence 必带 prior: 前缀(§2.1)')
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='prior', evidence=evidence))

    def leave_screen(self, target: Field) -> None:
        """画面附加域离屏(§2.2 显式例外):置 None 是结构事实非失读,
        不受 carried 硬边界辖。仅 shop/encounter/supply 三域合法,整局
        字段禁走此口(显式炸错防误用扩散)。"""
        name = self._field_name(target)
        if name not in _PAYLOAD_DOMAINS:
            raise ValueError(f'{name} 非画面附加域,禁离屏清值(§2.2 硬边界)')
        self._swap(name, Field(value=None, source='observation',
                               evidence='left_screen'))

    def expect(self, target: Field, value: Any, *,
               confirm_point: str = 'prep_obs', group_id: str = '',
               at_round: str = '', produced_by: str = '') -> PendingEntry:
        """记待核实预期(§2.5 两步第一步):入预期条目表,字段值暂不动
        (策略器读不到)。五键见 :class:`PendingEntry`;同字段后写覆盖
        前写(last-wins)。"""
        name = self._field_name(target)
        entry = PendingEntry(path=name, value=value,
                             confirm_point=confirm_point, group_id=group_id,
                             at_round=at_round, produced_by=produced_by)
        self.expected[name] = entry
        return entry

    def confirm(self, entry: PendingEntry, *,
                at_point: str | None = None) -> None:
        """核对通过(§2.5 两步第二步):预期转正——写入字段(source=logic,
        保持 logic 不翻 observation,§8.1)并清账。

        - at_point 给定时须与条目绑定的核对点一致(§2.4 五键②),否则炸错;
        - 组条目全有全无:entry 带 group_id 时整组一并转正+清账(§2.4 五键③,
          禁单字段半确认中间态);
        - 条目已被 last-wins 覆盖或已清账 → 炸错(禁确认过期条目)。
        """
        current = self.expected.get(entry.path)
        if current is not entry:
            raise KeyError('条目已失效(last-wins 被覆盖或已清账),禁确认')
        if at_point is not None and at_point != entry.confirm_point:
            raise ValueError(f'核对点不符:条目绑 {entry.confirm_point},'
                             f'来点 {at_point}(§2.4 五键②)')
        if entry.group_id:
            group = [e for e in self.expected.values()
                     if e.group_id == entry.group_id]
        else:
            group = [entry]
        for e in group:
            self._swap(e.path, Field(value=e.value, source='logic'))
            self.expected.pop(e.path, None)

    def write_logic(self, target: Field, value: Any, *,
                    produced_by: str, evidence: str | None = None) -> None:
        """单次逻辑写入(直接转正,不经预期条目表)。

        仅限设计**显式申报豁免**的写端——「不为它记待核实预期」(§3.4 通用
        机制:事件屏 chosen_* 由选择 handler 单次逻辑写入;§4 事件选择行;
        §3.3.6-8 刷新计数组=仅逻辑)。豁免语义 = 该写端的真值在写入时点
        即确定(选择事实/自身动作事实),不存在可核对的后续定型帧,不是
        免检通道:字段值之后仍受观察覆盖辖(§2.3 观察赢)。其余决策动作
        禁走此口,必须走 expect/confirm 两步(§2.5);判断不符的调用 =
        设计缺口,先回设计文档申报再落码。

        produced_by = 产生者标识(op/handler 名,留证用);
        evidence = 可选来源注记(如刷新执行的轮键 refresh_exec@p1-r2)。
        """
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='logic', evidence=evidence))

    def relay(self, target: Field, value: Any) -> bool:
        """载体中继(§2.1,**不设第五来源类**;迁移批次二收敛)。

        接管/初始化把会话已知事实补写进**从未写过的字段**:
        - source = logic + evidence = 'session_carrier'(中继是已核实事实
          的搬运,非本帧观察,禁标 observation);
        - **已有正式值的字段一律跳过**(返回 False)——禁把 handler 已写的
          logic 翻成 observation(§8.1),真写端(write_logic/观察覆盖)优先。
        """
        if target.value is not None:
            return False
        name = self._field_name(target)
        self._swap(name, Field(value=value, source='logic',
                               evidence='session_carrier'))
        return True

    def discard_expected(self, entry: PendingEntry) -> None:
        """核对失败清账(§8.4 用法块第 4 步:点击落空 → 观察赢 + 条目清账,
        不写字段);组条目同式整组清。"""
        current = self.expected.get(entry.path)
        if current is not entry:
            return
        group_ids = {entry.group_id} if entry.group_id else set()
        self.expected.pop(entry.path, None)
        if group_ids:
            for p in [p for p, e in self.expected.items()
                      if e.group_id in group_ids]:
                del self.expected[p]

    def logic_written_fields(self) -> list[str]:
        """全部 logic 来源字段名(已确认、尚未被观察重锚——对账巡检用,§8.4)。"""
        return [f.name for f in dataclasses.fields(self)
                if isinstance(getattr(self, f.name), Field)
                and getattr(self, f.name).source == 'logic']

    def pending_entries(self) -> list[PendingEntry]:
        """预期条目表快照(登记序)。"""
        return list(self.expected.values())

    # —— 心跳观察者(§2.4 关键结构 2)——

    def heartbeat(self) -> int:
        """单调推进量现值(写点序号,只增不减);停更检测哨兵的唯一合法
        载体——帧观察完整度标注消费即清,当不了哨兵。"""
        return self.write_seq

    def mark_frame_obs(self, level: FrameObsLevel) -> None:
        """标注本帧观察完整度(写入端;消费即清语义见 consume)。"""
        if level not in ('full', 'view', 'none'):
            raise ValueError(f'非法帧观察完整度:{level}')
        self.frame_obs = level

    def consume_frame_obs(self) -> FrameObsLevel:
        """消费帧观察完整度(消费即清 → 'none');不影响心跳计数。"""
        cur = self.frame_obs
        self.frame_obs = 'none'
        return cur


# ============================================================ 心跳观察者


def note_board_state_heartbeat(ctx_or_session: object) -> None:
    """心跳观察者采样(§2.4;生产接线点 = cw_loop 备战分支)。

    读单调推进量现值并与上次采样比对:连续 ≥2 次零推进 = 观察断流诊断
    (log.warning 留痕,**不停机**——停更处置交既有守卫链;首个备战环只
    建基线不计数)。宿主可传 ctx(取 ctx.cw_match.session)或 session 本体
    (测试/sim)。
    """
    match = getattr(ctx_or_session, 'cw_match', None)
    session = (getattr(match, 'session', None) if match is not None
               else ctx_or_session)
    if session is None:
        return
    bs = board_state_of(session)
    if bs.hb_prev_seq is None:
        pass    # 首采:只建基线
    elif bs.write_seq == bs.hb_prev_seq:
        bs.hb_stall_count += 1
        if bs.hb_stall_count >= 2:
            log.warning('[cw!][bs-heartbeat] BoardState 观察断流:连续 %d 次'
                        '采样零推进(写点序号 %d)——检查 read_game_state '
                        '观察链是否被跳过', bs.hb_stall_count, bs.write_seq)
    else:
        bs.hb_stall_count = 0
    bs.hb_prev_seq = bs.write_seq


# ============================================================ sim 合成口


def synthesize_from_game_state(bs: BoardState, st: GameState, *,
                               at_round: str = '') -> None:
    """sim 合成口:GameState 真值 → BoardState 观察(§2.1)。

    - sim 无识别过程 = 恒真值帧:可读字段全记 observation,evidence 恒带
      ``sim:synthesized``(at_round 非空时并入轮键后缀
      ``sim:synthesized@p{plane}-r{round}``,供遥测定位合成时点——P2-6
      落地审:参数必有消费);真值 None/未建模域不写(保持 None,禁合成假值);
    - **bench 槽位保序映射**(§3.2.5 任务书件 7):GameState.bench 的
      0 基下标 1:1 映射物理槽位(BenchChar → kind='unit',None → 'empty'),
      记录模型按实机真值箱占席——sim「无箱实体」只是内部口径约定,
      不进记录模型(占席谓词 = :func:`slot_occupies`,箱/秘典占席);
    - at_round = 轮键('p{plane}-r{round}' 形,登记期快照)。
    """
    _ev = f'{SIM_SYNTHESIZED}@{at_round}' if at_round else SIM_SYNTHESIZED
    # node_type None(裸 GameState 未建模该帧)不写 node——禁 'prep' 占位
    # 假值(P1-1 同型泛化;engine 路径 node_type 恒引擎真值不受影响)
    _node_type = getattr(st, 'node_type', None)
    if _node_type is not None:
        bs.observe(bs.node,
                   NodeKey(plane=int(getattr(st, 'plane', 1) or 1),
                           round_num=int(getattr(st, 'round_num', 1) or 1),
                           kind=str(_node_type)),
                   evidence=_ev)
    if getattr(st, 'gold_readable', True) and st.gold is not None:
        bs.observe(bs.gold, int(st.gold), evidence=_ev)
    if getattr(st, 'level_readable', True):
        bs.observe(bs.level, int(st.level), evidence=_ev)
    if st.xp_progress is not None:
        bs.observe(bs.xp, tuple(st.xp_progress), evidence=_ev)
    if st.streak is not None:
        bs.observe(bs.streak, int(st.streak), evidence=_ev)
    if st.hp is not None:
        bs.observe(bs.hp, int(st.hp), evidence=_ev)
    bench_slots: list[BenchSlot] = []
    for i, bc in enumerate(st.bench):
        if bc is None:
            bench_slots.append(BenchSlot(kind='empty'))
        else:
            bench_slots.append(BenchSlot(
                kind='unit',
                unit=Unit(char_id=str(getattr(bc, 'char_id', '') or ''),
                          star=int(getattr(bc, 'star', 1) or 1),
                          equips=list(getattr(bc, 'equips', None) or []),
                          slot=i + 1)))
    # 输出补齐到容量:定长槽位表是记录模型的形状契约(§3.2.5/ADR-0316 同构),
    # 兼容旧紧缩构造(前缀顺延占用)不丢槽位语义。
    while len(bench_slots) < BENCH_CAPACITY_DEFAULT:
        bench_slots.append(BenchSlot(kind='empty'))
    bs.observe(bs.bench,
               BenchView(slots=bench_slots, capacity=BENCH_CAPACITY_DEFAULT),
               evidence=_ev)
    if getattr(st, 'board_readable', True) and st.board:
        bs.observe(bs.board, dict(st.board), evidence=_ev)
    if st.shop:
        # cost_source 原值透传不折叠(P2-4;词表见 BoardState.ShopCard)
        cards = [ShopCard(name=str(getattr(c, 'name', '') or ''),
                          faction=str(getattr(c, 'faction', '') or ''),
                          cost=int(getattr(c, 'cost', 0) or 0),
                          star=int(getattr(c, 'star', 1) or 1),
                          cost_source=str(getattr(c, 'cost_source', '')
                                          or 'roster'))
                 for c in st.shop]
        probs = ({int(k): float(v) for k, v in st.refresh_probs.items()}
                 if st.refresh_probs else {})
        bs.observe(bs.shop, ShopPayload(cards=cards, refresh_probs=probs),
                   evidence=_ev)
    if st.active_strategies:
        bs.observe(bs.active_strategies, list(st.active_strategies),
                   evidence=_ev)
    bs.mark_frame_obs('full')
