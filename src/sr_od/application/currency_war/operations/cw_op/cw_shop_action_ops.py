"""商店单动作动作 op 集(ADR-0517 决策 3/10;flow 实施批)。

动作基类单方法(execute;原 execute+project 两方法契约(ADR-0517 决策 10)
的 project 半已删——T-163 纯规则路线裁定(用户 2026-09-12):策略与实机
操作链零 simulate 前瞻消费,期望态推进改走容器投影直写
(``apply_shop_action_logic`` 简单腿 + ``apply_shop_merge_leg`` 合成升星腿,
kernel 规则单一源,与序列驱动器同形;等价性由锁 M1 钉,
test_cw_shop_projection_logic)):

- ``execute(env)``:机械执行(点击/拖拽;op 框架既有的重试/等待语义
  在此层),无判断。

**知识缺口申报(ADR-0517 决策 7 边界注;merge_mechanics 通篇未载)**:
非满栏常态时合成槽位买的一击张数无 research 记载——本实现取保守假设
**一击一张**(kernel 规则面同判:常态单击单张,满栏例外按 merge_buy_k
一击多张),规则模型误差由入口
对账兜底(下一画面入口观察 = 事实重建,决策 8)。实机冻结解除后补档
验证:验证未过则该买面升格为终结 op(fallback 语义,见 CompTransactionOp)。

守卫断言(决策 9):执行侧检查 = 防 bug 路栏非控制流分支,非法返回 =
策略器 bug 响亮暴露——``guard_proposal_vs_expected``(提案动作的对象在
期望态中存在且未被消费,防策略器算术 bug)+ ``guard_expected_vs_tracked``
(期望态投影链 vs 执行侧 tracked 账双账对拍,投影建模 bug 的唯一在环
检测器——历次投影口径返工史证明投影建模错是常态)。双账断言
零读屏(tracked 账纯内存随动),不违决策 1/8「循环内不读屏」。

执行侧观测通道(ADR-0517 §执行侧观测通道去向,候选 a;T-192 判效
拆除后的保留面):卖回金实收遥测/牌面变化留证位(安灯 free_refresh_proc
豁免判定输入)/免费刷新证据保留为 execute 实现层遥测,与决策读屏解耦
(均观测职责,非决策输入;刷新有效性判效半已随 T-192 拆除,判效权归
观察侧 reconcile)。
"""
from __future__ import annotations

import contextlib
import time
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    BenchChar,
    bench_occupied,
    exec_state_of,
    pad_bench,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import merge_buy_k
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
    _area_rect,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    CloseShop,
    CompTransaction,
    LevelUp,
    RefreshShop,
    SellBench,
    mutate_bench_deployed,
)

# 刷新钮真值 reader 经模块属性路由消费(替身缝:测试 monkeypatch 模块属性,
# 直接 from-import 会绑死旧引用绕开替身,同 _buy_cards_mod 约定)。
from sr_od.application.currency_war.obs import cw_shop_refresh_obs
from sr_od.application.currency_war.telemetry import defects

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Action
    from sr_od.operations.sr_operation import SrOperation  # noqa: F401


# ---------------------------------------------------------------------------
# 访问账本与执行环境
# ---------------------------------------------------------------------------

@dataclass
class ShopVisitLedger:
    """商店访问执行账(旧 ``run_buy_waves`` 闭包计数器的具名化,ADR-0517)。

    ``refresh_first_action`` = 本访问段(两次刷新之间的段)此前零动作
    ——「仅刷新波」判定输入(``refresh_wave_is_refresh_only`` 单一判据,
    刷前现读复用段顶整帧读的边界条件)。
    """

    total_buy: int = 0
    total_level: int = 0
    total_refresh: int = 0
    total_sell: int = 0
    total_sell_income: int = 0
    total_sell_skip: int = 0
    spend_executed: int = 0
    plan_truncated: bool = False
    refresh_attempted: bool = False
    refresh_board_changed: bool | None = None
    bought_names: list[str] = field(default_factory=list)
    refresh_first_action: bool = True
    did_refresh: bool = False
    # `w536_merge_expect/` 买牌期望态基座(单元尾计算消费):
    buy_purchases: list = field(default_factory=list)
    buy_has_sell: bool = False
    buy_unidentified: bool = False
    # 买牌期望态基座(单元执行前 tracked 快照;迁移批 3.2 起随账本外发,
    # 消费方 = finalize 的 compute_buy_expect——事后取 tracked 已被本单元
    # 动作推进,必须取入口时点快照)。
    buy_pre_bench: list = field(default_factory=list)
    buy_pre_deployed: list = field(default_factory=list)
    # [索引定义] 访问事实行(安灯暂存载体;迁移批 3.2 切片5):list 下标 =
    # 发射序(先进先出;元素 = 发射/受阻时点构造的回执行 dict——发射行带
    # serialize_action 同 schema 动作载荷,受阻行仅结构化 extra);取值时机
    # = 发射时增量追加(写点 = note_shop_action_receipt,与 receipts 域
    # 同点同构造),自积累无容量上界,禁回读 receipts 滚动窗(容量 8 会
    # 截断繁忙访问段的计划侧 = 该停不停)。消费方 = visit_open_shop 经
    # unit_exec_facts_from_receipts 派生安灯判定输入。
    fact_rows: list = field(default_factory=list)
    # T-13 真值通道:刷前刷新钮按钮态 UI 读数(RefreshShopOp.execute 点击前
    # 帧快照,一次刷新写一次;消费方 = cw_op_buy_cards.apply_action_outcome
    # 免费闸)。None = 失读回退逻辑账(接线前保守形态),禁当 False。
    refresh_free_truth: bool | None = None
    # T-13 次数余量联动:免费态钮内剩余次数 UI 读数(同帧快照;消费方 =
    # apply_action_outcome 与 free_refresh_balance 逻辑账刷前值对票,失配落
    # 缺陷台账零决策)。
    refresh_free_remaining_truth: int | None = None
    # `w536_merge_expect/` 买牌期望态基座(单元尾计算消费):
    buy_purchases: list = field(default_factory=list)
    buy_has_sell: bool = False
    buy_unidentified: bool = False


@dataclass
class ShopExecEnv:
    """动作 op 执行环境(画面 op 注入;动作 op 不自持画面层状态)。"""

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object
    click_pts: list
    level_btn: Point
    refresh_btn: Point
    ledger: ShopVisitLedger
    # 当前期望态(W6 波 4 容器化,设计件 §2.4-2:执行侧读点改容器单例
    # board_state_of(match.session);满栏 k 计等消费经席位/payload 读口)
    state: GameState


def _container_cards(state: GameState) -> list:
    """商店 payload 牌列表(容器;离屏 None = 空列表)。"""
    payload = state.shop.value
    return shop_payload_content_cards(payload)


def _plane_of(state: GameState) -> int:
    from sr_od.application.currency_war.kernel.cw_game_state import plane_of
    return plane_of(state)


def _round_of(state: GameState) -> int:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        round_num_of,
    )
    return round_num_of(state)


# ---------------------------------------------------------------------------
# 守卫断言(决策 9:防 bug 路栏,非法 = 响亮暴露)
# ---------------------------------------------------------------------------

def guard_proposal_vs_expected(action: Action, state: GameState) -> None:
    """proposal-vs-expected 断言(ADR-0517 §守卫两属 (i))。

    提案动作引用的对象在期望态中确实存在且未被消费——防策略器算术 bug
    (单动作循环下期望态每动作后即更新,此属天然成立;断言炸出 = 策略器
    bug,禁静默跳过)。辖面:SellBench 的槽位占用与 expect 名一致性;
    BuyCard 的所购牌名在期望态店中(已买走/陈旧快照牌再提案 = 跨代际
    提案,炸出;未识别牌 name 空 = 无名可对,跳过名断言交未识别面处理;
    满栏 merge 买的「一击多张」豁免属 expected-vs-tracked 双账豁免,
    本断言不受豁免——提案时点牌仍在店中,名恒可对)。
    """
    # bench_slots_of 读口在函数顶导入:函数体内任何位置的 import 语句都会
    # 把名字绑定为全函数局部变量——曾放 BuyCard 分支内,SellBench 分支
    # 未执行该 import 即引用,UnboundLocalError(2026-09-13 实机 T-181:
    # r2 席满卖人决策被守卫自身炸掉,触发买空店重进崩溃循环)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
    )
    if isinstance(action, BuyCard):
        _name = action.card.name or ''
        _payload = state.shop.value
        if _name and not any((c.name or '') == _name
                             for c in shop_payload_content_cards(_payload)):
            raise AssertionError(
                f'[cw-shop][guard] BuyCard 提案牌不在期望态店中:'
                f'name={_name!r} cost={action.card.cost} '
                f'shop={[(c.name or "") for c in shop_payload_content_cards(_payload)]}'
                '(策略器 bug:跨代际/已消费提案,ADR-0517 决策 9)')
        return
    if isinstance(action, SellBench):
        _slots = bench_slots_of(state)
        tgt = (_slots[action.bench_idx]
               if 0 <= action.bench_idx < len(_slots) else None)
        if tgt is None:
            raise AssertionError(
                f'[cw-shop][guard] SellBench 提案指向空槽/越界:'
                f'bench_idx={action.bench_idx} expect={action.expect!r} '
                f'bench={[b.char_id if b else None for b in _slots]}'
                '(策略器 bug:期望态无此对象,ADR-0517 决策 9)')
        if action.expect and (tgt.char_id or '') != action.expect:
            raise AssertionError(
                f'[cw-shop][guard] SellBench 名-槽不一致:'
                f'idx={action.bench_idx} expect={action.expect!r} '
                f'实际={(tgt.char_id or "")!r}'
                '(策略器 bug:跨代际提案,ADR-0517 决策 9)')


def _bench_identity_signature(
        table: list[BenchChar | None]) -> list[tuple[str, int]]:
    """槽位表的占用身份签名(逐槽 (char_id, star);None 槽跳过)。"""
    return [(b.char_id or '', b.star or 1)
            for b in (table or []) if b is not None]


def _reseed_bench_layout(state: GameState,
                         tracked: list[BenchChar | None]) -> bool:
    """投影 bench 布局按执行侧 tracked 槽位表就地回写(布局单一源重播种:
    churn 后 tracked/实况是重排侧真值,投影副本跟随)。

    槽号健康门:tracked 槽号来自 SIFT/对账 churn,属无守卫数据——占用
    槽号须唯一 ∧ 全在 1..BENCH_CAPACITY,违者**拒绝重播种**维持旧布局
    (防坏槽号污染投影后进入 M4 卖出链:重播种后两账同源,
    guard_proposal_vs_expected 对表位置-物理格错位结构性失明,错格拖拽
    = 卖错人/卖空格),并落 ``bench_slot_unhealthy`` 台账分键留证。
    返回是否实际重播种。
    """
    occupied = [b for b in (tracked or []) if b is not None]
    slots = [b.slot for b in occupied]
    healthy = all(isinstance(s, int) and 1 <= s <= BENCH_CAPACITY
                  for s in slots) and len(set(slots)) == len(slots)
    if not healthy:
        with contextlib.suppress(Exception):
            defects.record_defect(
                'bench', defects.DEFECT_KIND_BENCH_SLOT_UNHEALTHY,
                expected='tracked 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY',
                observed=f'slots={sorted(slots)}',
                verdict=('留证-tracked 槽号不健康,拒绝重播种(维持旧投影'
                         '布局,坏槽号不进不可逆卖出链;根因=对账 churn '
                         '槽号无守卫,归观察层仲裁批)'),
                reader_source='reseed_health_gate',
                gap_large=True,
                note='重播种槽号健康门(占用表槽号唯一性与值域校验)')
        return False
    # 写目标 = 容器 bench 域(W6 波 4,设计件 §2.3:重播种写点 =
    # write_logic(bs.bench, tracked 重建 BenchView),投影域集例外申报
    # 面;原「投影帧就地回写」随黑板槽退役消亡)。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        bench_view_of_slots,
    )
    assert isinstance(state, GameState)   # 容器形态唯一(波 4 起)
    state.write_logic(state.bench, bench_view_of_slots(list(tracked)),
                      produced_by='reseed_bench_layout',
                      sig=ChannelSig(
                          family='logic_action', actor='CwOpBuyCards',
                          mode='compute',
                          group_id=(f'act:CwOpBuyCards@'
                                    f'{state.write_seq + 1}')))
    return True


def reseed_bench_if_layout_stale(state: GameState, session,
                                 seed_epoch: int) -> str:
    """S3 布局代次检差三步的封装(ADR-0646;单动作循环每动作消费前调用)。

    检差:exec_state 布局代次 vs 播种期快照——命中 = visit 内布局已重排
    (reconcile 纠漂递增,唯一写点 kernel/cw_reconcile),已发射动作的
    bench_idx 代际失效,不可只换 state.bench。三步语义:
    ①截断在飞计划(序列决策契约截断语义,plan_truncated 记账由调用方承担——
      本函数零 ledger 依赖,保持纯投影面可单测);
    ②按 tracked 重播种(下标直拷 pad 后经 ``_reseed_bench_layout``,
      含槽号健康门——脏槽号拒绝重播种维持旧布局);
    ③重入决策(调用方 continue,decide 消费重播种后黑板帧)。

    Returns:
        'clean' = 代次未变(常态,当前架构 S2+S1 后恒此值——reconcile 均在
        visit 外跑);'reseeded' = 检差命中且重播种成功(调用方重入决策);
        'failed' = 检差命中但重播种被槽号健康门拒绝(布局不可信,调用方应
        fail-stop 本段收工交回外循环重观察——禁在不可信布局上继续发射)。
    """
    if exec_state_of(session).bench_layout_epoch == seed_epoch:
        return 'clean'
    tracked = pad_bench(deepcopy(
        getattr(exec_state_of(session), 'tracked_bench_chars', None) or []))
    if not _reseed_bench_layout(state, tracked):
        return 'failed'
    return 'reseeded'


def guard_expected_vs_tracked(state: GameState, session,
                              stage: str = 'project') -> None:
    """expected-vs-tracked 双账断言(ADR-0517 §守卫两属 (ii))。

    期望态(容器投影直写链 = apply_shop_action_logic/合成升星腿维护;
    T-163 起 simulate 前瞻投影已删)vs 执行侧 tracked 账
    (``tracked_bench_chars`` 经 mutate 随执行更新)的对拍——分叉的
    在环检测器。零读屏(tracked 纯内存)。

    两级分型(签名比较先做多集(multiset)等价,再走两属归因):
    - **多集等价(槽位布局漂移,降级不炸)**:成员账对齐、仅槽位排列
      分歧——历史 bug 态(tracked 紧凑 × slot 稀疏)下对账 churn 后两域
      落洞不同源。根因申报(T-308/ADR-0646 已治本):漂移之根 =
      reconcile 写回紧凑列表制造**布局双源**——两域在播种时刻即读出
      不同布局(投影=bench_from_compact 槽号重构、tracked=mutate 下标
      演化),每次落洞动作放大一次差异。治本 = S2 写回经
      bench_from_compact 重建槽位表(kernel/cw_reconcile,deployed 侧
      同构先例补齐)+ S1 tracked 域消费点下标直拷(播种同源,本守卫的
      tracked 构造即其一点);本重播种保留为 guard 内自愈通道 + S3
      epoch 检差(``reseed_bench_if_layout_stale``)的复用件,历史
      bug 态(tracked 未及 S2 重建)残留时仍可显影自愈。
      处置 = WARNING + 台账分键 ``bench_slot_layout_drift`` 留证
      (判读工具可查)+ 按 tracked 真值就地重播种投影 bench
      (``_reseed_bench_layout``,含槽号健康门)——回写源选 tracked
      而非 ``match.bench_slot_map`` 的依据:后者只在买组确认后产出
      (守卫炸点在组中,来不及)且只含所购名→槽、不承载 churn 重排
      与洞位;tracked 账纯内存随执行与对账更新,是重排侧,零读屏。
    - **真多集分歧**:按 stage 两属归因,断言炸出(消息见下)。
      stage='seed'(visit 入口首动作前):期望侧 = 容器 bench(唯一实机
      漏斗写端 = 备战装配环 bench 观察块;合成口对未读域跳写,见
      CwSimFrame.bench_readable),两账多集分歧 = 观察漏斗与执行账
      真实分叉(跟踪账丢件/观察失真),fail-stop 交回重观察——下一入口
      heavy 读屏重建可归零。
      stage='project'(默认,动作投影后):分叉 = 投影直写/mutate 模型
      分叉——投影建模 bug 的唯一在环检测器(错误卖出会实际执行、损害
      不可逆,历次投影口径返工史为证)。

    已申报豁免(非分叉 bug 的已知建模分叉,豁免帧由调用方判定):
    满栏买入(豁免面 = 游戏接受而两模型都不收编的残余窗:非合成满栏买
    被游戏拒绝而像素差漏检的 fail-open 形态。合成满栏买面已随 T-182
    同构化——mutate 带 shop 视图走 `_apply_full_bench_merge_buy` 同
    分支,不再丢件漏记)。豁免面外的真分叉 = 断言炸出。
    """
    # T-308/ADR-0646 S1:tracked 输入域下标直拷(pad 补 None;deepcopy 隔离
    # ——旧 bench_from_compact 冲突分支经 bench_place 就地改 bc.slot,守卫
    # 读路径存在写副作用,直拷后自然关闭)。禁读 slot 字段:tracked 域
    # slot 与下标的一致性由 S2 写回端保证,消费端下标即布局(与 SIFT 现读
    # 域「slot 与读序同帧同源」是两套命题,分界见 ADR-0646)。
    tracked = pad_bench(deepcopy(
        getattr(exec_state_of(session), 'tracked_bench_chars', None) or []))
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
    )
    expect_sig = _bench_identity_signature(bench_slots_of(state))
    tracked_sig = _bench_identity_signature(tracked)
    if expect_sig != tracked_sig:
        from collections import Counter as _Counter
        if _Counter(expect_sig) == _Counter(tracked_sig):
            log.warning(
                '[cw-shop][guard] 双账槽位布局漂移(多集等价,降级不炸;'
                '已按 tracked 重播种投影 bench):expected=%s tracked=%s',
                expect_sig, tracked_sig)
            with contextlib.suppress(Exception):
                defects.record_defect(
                    'bench', defects.DEFECT_KIND_BENCH_SLOT_LAYOUT_DRIFT,
                    expected=f'expected={expect_sig}',
                    observed=f'tracked={tracked_sig}',
                    verdict=('留证-双账槽位布局漂移(多集等价,仅槽序分歧;'
                             '降级不炸,已按 tracked 真值重播种投影 bench;'
                             '根因=播种双源已随 T-308/ADR-0646 S2+S1 治本,'
                             '本行为历史 bug 态残留自愈面,复发=回退哨兵)'),
                    reader_source='guard_expected_vs_tracked',
                    gap_large=False,
                    note='双账对拍守卫降级分支(多集等价;真分歧仍 AssertionError)')
            _reseed_bench_layout(state, tracked)
            return
        if stage == 'seed':
            raise AssertionError(
                '[cw-shop][guard] tracked 主账为空而屏幕 bench 非空'
                '(跟踪账丢件/识别幻影嫌疑,非播种错误——播种 bug 形态'
                '已随 ADR-0520 旧账退役消失):'
                f'expected={expect_sig} tracked={tracked_sig}'
                '(期望态在首动作前即与 tracked 账不同源,投影链无责;'
                '下一入口 heavy 读屏重建可归零)')
        raise AssertionError(
            '[cw-shop][guard] 期望态 vs tracked 双账分离(投影建模 bug?):'
            f'expected={expect_sig} tracked={tracked_sig}'
            '(ADR-0517 §守卫两属 (ii);首动作前另有播种期对账,'
            '此处炸出 = project/mutate 模型分叉)')


# ---------------------------------------------------------------------------
# 动作基类与具体动作 op
# ---------------------------------------------------------------------------

class ShopActionOp(ABC):
    """商店动作 op 基类(execute 单方法;原 project 投影半已删,T-163
    纯规则路线——期望态推进 = 容器投影直写,模块头申报)。"""

    #: 终结动作(执行即本画面访问结束,交回外循环;决策 4)
    terminal: bool = False

    def __init__(self, action: Action):
        self.action = action

    @abstractmethod
    def execute(self, env: ShopExecEnv) -> bool:
        """机械执行;返回恒 True(T-223 终裁:发出即职责完成,零判效——
        落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定改道)。"""


class BuyCardOp(ShopActionOp):
    """买一张 = 一个动作 op(ADR-0517 决策 3;满栏例外下一击多张仍一个
    op,张数由游戏规则定、投影按 merge_buy_k 计——方案 A 补裁)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.base.geometry.point import Point as _Pt
        action: BuyCard = self.action
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of,
        )
        op, match, ledger, state = env.op, env.match, env.ledger, env.state
        # 点击定位 = 牌自带物理槽号 slot(读链写入)→ screen_info
        # 「商店牌-N」现取(W6 波 4 双 ShopCard 归一:容器牌无 x 坐标,
        # 坐标单一真相源 = screen_info,设计件 §2.5-5)。身份匹配优先
        # 同一性(action 由决策核自 payload 产出),退化按 (name, star)
        # ——匹配下标仅作槽号缺失时的兜底锚,见下方点击解析。
        # 槽号主源 = payload 定长槽阵列位置(三态模型:数组下标+1 =
        # 物理槽;身份同一性优先,退化 (name, star));card.slot 兼容
        # 字段降为最后兜底(退役面审计:T-190 批2)。
        _slot_no_matched = None
        _payload = state.shop.value
        _slots = (_payload.cards if _payload is not None else [])
        for _i, _s in enumerate(_slots):
            if _s.kind == 'content' and _s.card is not None \
                    and _s.card is action.card:
                _slot_no_matched = _i + 1
                break
        if _slot_no_matched is None:
            for _i, _s in enumerate(_slots):
                if _s.kind == 'content' and _s.card is not None \
                        and (_s.card.name or '') == (action.card.name or '') \
                        and int(_s.card.star or 1) == int(action.card.star or 1):
                    _slot_no_matched = _i + 1
                    break
        # 点击坐标 = 牌自带实测槽位(观察期读链写入的物理槽号)→ screen_info
        # 「商店牌-N」中心。紧凑下标只在牌行满列期与物理槽位等价:游戏买入
        # 后不压缩剩余卡位(牌行打洞),紧凑列表全体下标偏离物理槽位,按下标
        # 取固定槽坐标 = 点击落空槽框(实机局实证:1 槽空、卡在 2-5 槽时恒打
        # 1 槽框,「买牌点击不注册」根因;布局双源同族 = ADR-0646 bench 布局
        # 错位的商店牌行版)。槽号缺省(0 = sim/离线构造、修复前旧档)退回
        # 紧凑下标映射(旧行为)。
        _slot_no = _slot_no_matched
        if _slot_no is None:
            # 兼容兜底:旧档/sim 构造牌的 slot 字段(退役过渡期保留)
            _slot_no = int(getattr(action.card, 'slot', 0) or 0)
        if 1 <= _slot_no <= len(env.click_pts):
            pt = env.click_pts[_slot_no - 1]
        else:
            pt = (_Pt(0, 288) if not env.click_pts else env.click_pts[0])
        # 买前裁该片矩形拷贝(`w536_merge_expect/`:「买了什么」的像素级
        # 证据,随期望态带到对账点;一帧原则,必须 copy 防帧缓存覆写)。
        # 纯留证零判效(T-192):crop 只进 buy_purchases 遥测;落地事实
        # 归下一帧入口观察 reconcile,不据执行侧像素判定改道。
        _card_crop = None
        with contextlib.suppress(Exception):
            _frame = op.screenshot()
            for _i in range(1, 6):
                _r = _area_rect(op.ctx,
                                f'{A_SHOP_CARD_PREFIX}{_i}',
                                SHOP_SCREEN_NAME)
                if _r is not None and _r.x1 <= pt.x <= _r.x2:
                    _card_crop = _frame[_r.y1:_r.y2, _r.x1:_r.x2].copy()
                    break
        op.ctx.controller.click(pt)
        log.info(f'[cw-shop] Buy click slot={_slot_no} @({pt.x},{pt.y}) '
                 f'{action.card.faction}/{action.card.name}/'
                 f'{action.card.cost}')
        time.sleep(0.4)
        ledger.total_buy += 1
        ledger.spend_executed += action.card.cost
        if action.card.name:
            ledger.bought_names.append(action.card.name)
            # 撤销操作证据留存(纯观测,零行为变更):体系成员买入不重置
            # 干旱计数(重置单一源 = 商店可见性 _update_pair_drought),
            # 解锁流程审计面落台账。复用 defect_ledger,异常不阻断买入。
            with contextlib.suppress(Exception):
                _ist_e = getattr(strategy_state_of(match.session), 'v3_intention', None)
                _pd = getattr(_ist_e, 'pair_drought', None)
                if isinstance(_pd, dict):
                    from sr_od.application.currency_war.kernel.cw_intention import (
                        members_in_shop,
                    )
                    from sr_od.application.currency_war.telemetry.undo_evidence import (
                        record_drought_buy_no_reset,
                    )
                    for _sys, _d in _pd.items():
                        if _d and _sys and members_in_shop(
                                _sys, {action.card.name}):
                            record_drought_buy_no_reset(
                                member=action.card.name,
                                system=_sys, drought=_d)
        # tracking 同步:满栏合成买与投影同分支单一源(T-182:shop 视图
        # 进 tracked mutate,满栏完成合成的买入在 tracked 侧同样合成腾槽
        # ——旧丢件行为使 tracked 漏记合成,同 visit 下一动作守卫对拍
        # 误炸;2026-09-09 05:52 运行局双响事故)。
        _payload_cards = (shop_payload_content_cards(state.shop.value)
                          if state.shop.value is not None else [])
        mutate_bench_deployed(exec_state_of(match.session).tracked_bench_chars,
                              exec_state_of(match.session).tracked_deployed,
                              action, shop=_payload_cards)
        if action.card.name:
            _cnt = 1
            if bench_occupied(bench_slots_of(state)) >= BENCH_CAPACITY:
                # 满栏例外(merge_mechanics §2.5 方案 A):一击多张,张数
                # 单一源 = merge_buy_k(禁执行侧重算);金账无折扣 = 总价
                # k×单价,执行账补差 (k−1)×单价。
                _cnt = max(1, merge_buy_k(
                    action.card.name, action.card.star or 1,
                    bench_slots_of(state),
                    exec_state_of(match.session).tracked_deployed,
                    _payload_cards))
                ledger.spend_executed += (action.card.cost or 0) * (_cnt - 1)
            from sr_od.application.currency_war.kernel.cw_prep_expect import (
                BuyPurchase,
            )
            ledger.buy_purchases.append(BuyPurchase(
                name=action.card.name, star=action.card.star,
                count=_cnt, unit_cost=action.card.cost or 0,
                crop=_card_crop))
        else:
            ledger.buy_unidentified = True
        return True


class LevelUpOp(ShopActionOp):
    """升一级 = 一个动作 op(决策 3;clicks 序列 = 动作内部步骤,外部买
    面不可插花,ADR-0517 §权衡构造性消解)。单动作形态下每帧恰发一个
    「购买经验」单击,序列由决策循环逐帧重组。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: LevelUp = self.action
        op, ledger = env.op, env.ledger
        op.ctx.controller.click(env.level_btn)
        log.info(f'[cw-shop] LevelUp click @({env.level_btn.x},'
                 f'{env.level_btn.y})')
        # 用户口述口径(screen_flow_timing.md #22,2026-09-02):购买经验
        # 动画 ~1s(原 0.6s 不足;光标遮挡由段顶 park_cursor 防)。
        time.sleep(1.0)
        # (血购执行回执行挂点已随 exogenous 流写入端退役删除——删除波 1;
        #  血本位单点击扣血的机械事实面不变。)
        ledger.total_level += 1
        ledger.spend_executed += action.cost
        return True


class SellBenchOp(ShopActionOp):
    """卖一张 = 一个动作 op;卖回金实收遥测 = 执行实现层(候选 a)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: SellBench = self.action
        op, match, ledger = env.op, env.match, env.ledger
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of,
        )
        state = env.state
        _slots = bench_slots_of(state)
        _expected = (_slots[action.bench_idx]
                     if 0 <= action.bench_idx < len(_slots) else None)
        _expected_name = (_expected.char_id if _expected is not None else None)
        # (卖出前 gold 基数读数 _gold_before 已随 sell_income 外生行退役删除
        #  ——删除波 1;卖牌实收回金 = 收入账 total_sell_income(计划值)。)
        from sr_od.application.currency_war.prep_actions import (
            drag_bench_to_sell,
        )
        ok = drag_bench_to_sell(op, op.ctx, action.bench_idx)
        if not ok:
            ledger.total_sell_fail += 1   # 拖 3 次源槽未变(现有语义)
            log.warning('[cw-shop] Sell bench%d %s 拖3次源槽未变',
                        action.bench_idx, _expected_name)
            return False
        # tracking 同步:置 None 不紧缩(ADR-0316)。T-308/ADR-0646 S1:
        # 下标直拷(pad 补 None)替代 bench_from_compact 槽号重构——S2 写回
        # 端保证 tracked 恒槽位表后本归一恒等;历史 bug 态(紧凑)下布局以
        # 列表下标为准(与 mutate 入口 pad 同构),不再按 slot 重构(陈旧
        # slot 会把卡放错槽;错位卖出由下方 mutate 代际校验拦截 no-op,
        # 安全非等价——故 S2 先于 S1 生效)。
        _tracked = exec_state_of(match.session).tracked_bench_chars
        pad_bench(_tracked)
        mutate_bench_deployed(_tracked, exec_state_of(match.session).tracked_deployed, action)
        # ADR-0328 执行域对齐:卖出件入同轮已卖集(执行成功是卖出事实的
        # 权威,register_round_sold 带轮键自校验)。
        # 换源 T-146(登记集消点):轮键源 = session 容器单例(node = 本
        # 节点备战帧写端,与波内帧 plane/round 同节点同值);旧过渡桥装箱
        # 退役。register_round_sold 消费面 = plane/round 轮键(轮键不匹配
        # 自拒 = 原防御语义不变)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )
        from sr_od.application.currency_war.kernel.cw_round_ledger import (
            register_round_sold,
        )
        register_round_sold([_expected_name],
                            board_state_of(match.session),
                            match.session)
        ledger.total_sell += 1
        ledger.buy_has_sell = True   # 含卖出 → 本单元期望态不建(`w536`)
        ledger.total_sell_income += action.income or 0
        log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                 action.bench_idx, _expected_name, action.income or '?')
        return True


class RefreshShopOp(ShopActionOp):
    """刷新 = 终结 op(决策 7:唯一引入新事实的动作,期望态必须在新事实
    处重建——终结后外循环入口重观察)。T-192 判效半拆除:牌名集三值
    对比仅作安灯豁免判定输入 + 遥测字段(候选 a 留证遥测半合法保留);
    免费刷新证据/刷新期望对账 = 执行实现层遥测(与决策读屏解耦);
    「刷新是否生效」的判效权归观察侧 reconcile。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        from one_dragon.utils import cv2_utils as _cvu

        # 读函数经 cw_op_buy_cards 模块属性路由(该模块的读点替身缝,
        # 测试 monkeypatch 面;自本模块直接 import 会绕开替身)。
        from sr_od.application.currency_war.operations.cw_op import (
            cw_op_buy_cards as _buy_cards_mod,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
            build_refresh_expect,
            refresh_reconcile_mismatches,
        )
        op, _match, ledger, state = (env.op, env.match, env.ledger,
                                    env.state)
        ledger.refresh_attempted = True
        # 刷前现读两口径(执行边界压缩·连击共享往返):「仅刷新段」
        # (段内零先行动作)复用段顶整帧读;其余段点击前一帧现读金+牌名集
        # (`w592_free_refresh_fix/`:波内买卡不从 state.shop 摘已买牌,
        # plan 读 vs 点击后实读集合必不等,真落空会被洗成免费生效)。
        _pre_shop_names: list[str] | None = None
        _refresh_expect = None
        _reconcile = None
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gold_of,
            )
            if ledger.refresh_first_action:
                _pre_gold = gold_of(state) if gold_of(state) > 0 else None
                _pre_shop_names = [c.name for c in _container_cards(state)
                                   if c.name]
            else:
                _pre_shot = op.screenshot()
                _pre_gold = _buy_cards_mod.read_gold_opt(op.ctx, _pre_shot)
                _pre_shop_names = [
                    s.card.name for s in (
                        _buy_cards_mod.read_shop_cards(op.ctx, _pre_shot)
                        or [])
                    if s.kind == 'content' and s.card and s.card.name]
            _refresh_expect = build_refresh_expect(
                _pre_gold, REFRESH_COST_BASE,
                [(c.name, c.star) for c in _container_cards(state)],
                _plane_of(state), _round_of(state))
            _reconcile = refresh_reconcile_mismatches
        except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
            _refresh_expect = None
            _reconcile = None
        # 刷前刷新钮真值读(T-13 读链接入):按钮三态 + 免费态剩余次数。
        # 经模块属性路由 = 测试替身缝(同 _buy_cards_mod 约定)。best-effort:
        # 识别层故障不阻塞执行链,ledger 字段保持 None = 免费闸回退逻辑账。
        _btn = None
        try:
            _btn = cw_shop_refresh_obs.read_shop_refresh_button(
                op.ctx, op.screenshot(), gold=_pre_gold)
        except Exception:   # noqa: BLE001  best-effort 不阻塞执行
            _btn = None
        if _btn is not None:
            ledger.refresh_free_truth = _btn.free
            ledger.refresh_free_remaining_truth = _btn.free_remaining
            log.info('[cw-shop] refresh button truth: free=%s remaining=%s '
                     'price=%s affordable=%s',
                     _btn.free, _btn.free_remaining, _btn.price, _btn.affordable)
        op.ctx.controller.click(env.refresh_btn)
        log.info(f'[cw-shop] Refresh click @({env.refresh_btn.x},'
                 f'{env.refresh_btn.y})')
        # r325(P1⑤):刷新后两帧一致门(牌行区指纹;刷新动画帧上的
        # SIFT miss 是 r97/383 样本实证根因);超时 2.5s 回退旧 sleep 语义。
        # 牌行 rect 单一源:改调 _shop_row_rects()(建档 area 派生+字面量
        # 兜底同门),删除本文件第二副本字面量(坐标单一源清点项)。
        _rects = _buy_cards_mod._shop_row_rects(op)   # 商店牌行
        _base = None
        _stable = False
        for _ in range(8):   # ≤2s@0.25s 步长
            time.sleep(0.25)
            _fp = None
            try:   # r327:截图裸调炸分支 → suppress 降级继续等
                _shot = op.screenshot()
                _fp = _cvu.fingerprint_in_rects(_shot, _rects)
            except Exception:   # noqa: BLE001  离线契约
                _fp = None
            if _fp is not None and _base is not None \
                    and _cvu.fingerprint_same(_fp, _base):
                _stable = True
                break
            if _fp is not None:
                _base = _fp
        if not _stable:
            time.sleep(0.5)   # 超时回退(≈旧 1.0s 总量)
        # 当次刷价进花销账 = 基价常量(ADR-0456:实付恒基价)
        _refresh_fee = state.shop_refresh_cost or REFRESH_COST_BASE
        ledger.spend_executed += _refresh_fee
        ledger.total_refresh += 1
        ledger.did_refresh = True
        try:
            _new_shop = _buy_cards_mod.read_shop_cards(op.ctx, op.screenshot())
            # (refresh 牌面快照行已随 shop_snapshots 流写入端退役删除
            #  ——删除波 1;牌面现役归宿 = journal 快照行自带 shop 域。)
            # 留证遥测半(T-192 判效半拆除后的保留面,候选 a):刷前/刷后
            # 牌名集三值对比只作安灯 free_refresh_proc 豁免判定输入
            # (classify_spend_unit 判定序③)+ 遥测字段
            # (schema.refresh_board_changed),不再产「刷新未生效嫌疑」
            # 判效结论——判效权归观察侧 reconcile。任一侧空(整帧失读/
            # 买光全空位)= None 不可判,不猜。
            _post_shop_names = [s.card.name for s in (_new_shop or [])
                                if s.kind == 'content' and s.card
                                and s.card.name]
            ledger.refresh_board_changed = (
                None if not _pre_shop_names or not _post_shop_names
                else set(_pre_shop_names) != set(_post_shop_names))
            # 刷新期望 vs 实读对账(零决策记账):金腿 + 牌腿。
            if _refresh_expect is not None and _reconcile is not None:
                _gold_after = _buy_cards_mod.read_gold_opt(
                    op.ctx, op.screenshot())
                # 免费刷新事后正证据通道(ADR-0456,永久保留——判定语义
                # 的一部分):刷新已点击 ∧ 牌面已变 ∧ 点后金=点前金 →
                # 免费 proc 真实发生,截图+flag 留证(不停机)。
                if (ledger.refresh_board_changed is True
                        and _pre_gold is not None
                        and _gold_after is not None
                        and _gold_after == _pre_gold):
                    with contextlib.suppress(Exception):
                        _record_free_refresh_proc(
                            op, state, ledger, _pre_gold, _gold_after,
                            _pre_shop_names, _new_shop)
                _cards_named = sum(1 for c in _new_shop if c.name)
                for _m in _reconcile(_refresh_expect[0], _gold_after,
                                     _cards_named):
                    defects.record_defect(
                        'shop', 'refresh_expect_mismatch',
                        expected=(f'{_m["domain"]}/{_m["slot"]}: '
                                  f'{_m["expected"]}'),
                        observed=_m['observed'],
                        plane=_plane_of(state), round_num=_round_of(state),
                        verdict='留证-刷新期望不符(零决策)',
                        reader_source='refresh_expect_reconcile',
                        note='期望三输入波前现读,None 跳过;'
                             '判据真值表已锁')
        except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
            pass
        return True


def _record_free_refresh_proc(op, state: GameState, ledger: ShopVisitLedger,
                              pre_gold, gold_after, pre_names,
                              new_shop) -> None:
    """免费刷新 proc 留证(ADR-0456;自 RefreshShopOp 抽出,单一行为)。"""
    from datetime import datetime as _dt

    from one_dragon.utils.file_utils import get_project_root
    from sr_od.application.currency_war.telemetry import (
        state as _cw_tel,
    )
    _free_shot = op.save_screenshot(prefix='free_refresh_proc')
    _flag_p = get_project_root() / '.debug' / 'temp' \
        / 'cw_free_refresh_proc.flag'
    _flag_p.parent.mkdir(parents=True, exist_ok=True)
    _flag_p.write_text(
        'FREE-REFRESH-PROC: 免费刷新实机正证据(非停机,bot 照常跑)\n'
        f'run={_cw_tel.current_run_id()} '
        f'plane={_plane_of(state)} round={_round_of(state)} '
        f'wave={ledger.total_refresh} ts={_dt.now().isoformat(timespec="seconds")}\n'
        f'前后牌面: {sorted(pre_names or [])} -> '
        f'{sorted(c.name for c in new_shop)}\n'
        f'gold: 前={pre_gold} 后={gold_after}(未扣=免费)\n'
        f'截图: {_free_shot}\n'
        '处理: 汇总频率判免费来源(棱 45%/策略类/未知),'
        '确认后删本 flag;通道本身保留(对账防线)。\n',
        encoding='utf-8')
    log.warning(
        '[cw!][shop] 免费刷新 proc:牌面已变 金未扣'
        '(前=%s 后=%s)→ 留证不停 flag=cw_free_refresh_proc.flag',
        pre_gold, gold_after)


class CloseShopOp(ShopActionOp):
    """关店 = 恒可用终结 op(决策 4/6):执行即本画面访问结束;关店点击
    由编排壳(CwOpCloseShop)承担——与旧「空序列触发关店」同一落点,
    动作 op 内为 no-op。"""

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        return True


class CompTransactionOp(ShopActionOp):
    """整档替换事务 = 复合动作类(ADR-0517 §复合动作类):一个 op、
    原子投影、C1 前置合法性(任一子步资源不足 ⇒ 整体不提案)。

    **终结邻接 fallback(现行档)**:合成建模验证未过(非满栏一击张数
    = research 知识缺口,模块头申报)⇒ 执行后本画面访问结束交回外循环
    重观察(= 旧截断点语义,禁半档中间态)。商店单动作决策核现行不提案
    CompTransaction(词表保留;提案面在备战域),本 op 为词表完备性落位。
    """

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        log.info('[cw-shop] CompTransaction(终结邻接 fallback:'
                 '执行后交回外循环重观察,ADR-0517 §复合动作类)')
        return True


_OP_TABLE = {
    BuyCard: BuyCardOp,
    LevelUp: LevelUpOp,       # LevelUpShop is-a LevelUp,同 op(单击)
    RefreshShop: RefreshShopOp,
    SellBench: SellBenchOp,
    CloseShop: CloseShopOp,
    CompTransaction: CompTransactionOp,
}


def shop_action_op_for(action: Action) -> ShopActionOp:
    """动作词表 → 动作 op(词表外类型 = 策略器 bug 响亮暴露,决策 9)。"""
    for cls, op_cls in _OP_TABLE.items():
        if isinstance(action, cls):
            return op_cls(action)
    raise AssertionError(
        f'[cw-shop][guard] 商店动作词表外类型:{type(action).__name__}'
        '(ADR-0517 决策 9:非法返回 = 策略器 bug,禁静默跳过)')
