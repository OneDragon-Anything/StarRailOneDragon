# review 修订(review round-1,2026-08-14):H-1 观察分层(执行过的游戏动作一律 heavy 重读,
# light 仅控制流;light 沿用上次 heavy 缓存)/H-2 恢复-屏蔽-bail 分型语义/M-2 模板路径复用
# ensure_portrait_templates/M-3 gold 可信标记/L-1 对账漂移 [cw!]+截图/L-4 强制出战异常兜底。

"""货币战争 备战决策环(PrepDirector)—— 两层环之内环(框架层;strategy/03(原 doc 15))。

**框架不含任何玩法判断**:何时收球/卖谁/何时出战 = 策略(CwStrategy.decide_prep_action);
本模块只保证八项框架不变式(F1-F8,strategy/03(原 doc 15§5.0)):
- F1 单步契约: 每步 = observe → decide_prep_action → execute(带验证) → 再 observe
- F2 观察真实: obs 只由现成 reader 产出;gold 可信度由框架显式标记
  (state_gold_trusted:仅 shop 开态重读的 state 才 True,关态读空不可信)
- F3 动作合法域: 策略输出须在动作全集内(白名单);框架校验参数后执行
- F4 验证与防护: 每动作完成验证;fail 计数/恢复原语/屏蔽/预算强制出战(§7)
- F5 出口兜底: 策略不出战且 stall/预算耗尽 → 框架强制出战
- F6 无状态策略: 环不污染策略实例;跨步意图走 StrategySession
- F7 可换策略: strategy 由配置选(11 号);换策略只换决策
- F8 可回放: obs+action 序列落 telemetry(P1 仅落盘)

**观察分层(P1 实现,review H-1 定稿)**:执行过的游戏动作(含组合)**一律 heavy 重读**
(买/卖/部署/装备/开箱/点球/升级/商店开关都改变结构 —— 单步决策环几乎每步都是结构变化);
light 观察(仅控制流 DeferSpheres / 拒绝步后)**沿用上次 heavy 的 state/bench_chars/
deployed_chars/deploy_vacancy 缓存**(不重 SIFT/OCR,只刷新轻字段)。性能(每步 heavy
~2-3s)live 校准后再分层细化。

**防死循环三层(§7 + review H-2 修订)**:同动作验证连败 2 → 恢复原语(一次/动作实例)→
恢复后仍连败 2(恢复无效)→ **分型**:恢复时关过已知弹层 → BailToOuter(环让位交外环,
弹层分支/停机钩子接手);恢复时只是兜底点空白(无已知弹层 = 状态/识别类失败)→ 本环
屏蔽该动作实例(策略须换路;StartBattle 豁免)。stall≥5 且恢复已试 → 强制出战(F5)。

挂载:battle_loop 备战分支 → PrepDirector(替换 BattlePrepCycle 固定序列;P1)。
环入口对账(SIFT 重读 vs tracking)是 deploy_bench._reconcile_tracking /
battle_prep._verify_recognition 钩子的继任宿主。
"""
from __future__ import annotations

import re
import time
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import SHOP_SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    XP_TO_NEXT_LEVEL,
    BenchChar,
    GameState,
    bench_from_compact,
    bench_place,
    deployed_slot_no,
    same_star_count,
    xp_apply_clicks,
    xp_clicks_to_level,
)
from sr_od.application.currency_war.kernel.cw_state import (
    _merge_bench as cw_merge_bench,  # 合成落点模型单一源(场上吸收/备战最左/连锁)
)
from sr_od.application.currency_war.obs.currency_war_cv import slot_occupied
from sr_od.application.currency_war.obs.cw_faction_obs import (
    compare_factions,
    read_displayed_factions,
    report_faction_reconcile,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_tomes as cw_identity_obs_read_tomes,
)
from sr_od.application.currency_war.obs.cw_observation import (
    board_from_tracked,
    read_deploy_cap,
    read_deployed_count,
)
from sr_od.application.currency_war.obs.cw_shop_obs import (
    RefreshExpect,
    check_shop_pool,
    compare_merge_preview,
    refresh_expect,
)
from sr_od.application.currency_war.prep_actions import (
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    LevelUp,
    OpenTome,
    PrepAction,
    PrepActionExecutor,
    RunBuyPhase,
    SellBench,
    SellDeployed,
    StartBattle,
    action_key,
    row_area_centers,
    try_recovery,
)
from sr_od.application.currency_war.telemetry import cw_telemetry
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.obs.cw_equipment import EquipCell


def store_plane_table(sess, seq: list[str], plane: int | None) -> bool:
    """开局帧槽序表的**每位面首帧**写入(ADR-0368,W169)。

    旧 write-once 守卫(``not plane_node_table``)使 P1 的 9 槽表整局滞留:
    生产进 P2 后 7 槽真值永不落盘 → nodes_of_plane / battles_left_p2 /
    位面日程真值(cw_plane_table.schedule_of;原 DP 期生产 P2 读陈旧 P1 表恒 9 的已知问题随 DP 退役
    (连表缺回退告警都不发——表「在」但是错的)。修:按
    ``plane_node_table_plane`` 锚定,位面变更即重写(位面内恒定语义不变,
    同位面多次 probe 不覆写);同时 append ``plane_lengths_seen``
    (DP 位面日程真值序列,P3 进表即自适应)。

    返回是否写入(供调用方记日志)。纯 session 写入,无画面依赖,可单测。
    """
    if not seq or plane is None:
        return False
    if getattr(sess, 'plane_node_table_plane', None) == plane:
        return False
    sess.plane_node_table = list(seq)
    sess.plane_node_table_plane = plane
    if sess.plane_lengths_seen is None:
        sess.plane_lengths_seen = []
    sess.plane_lengths_seen.append(len(seq))
    return True


# [停机钩子·临时采证,W494 spend_ledger 续;安灯式,用户裁决采纳]
# 触发:购买单元关闭时分类器判 mismatch(计划花费>0 且金差≈0 = 动作发出但金没动)。
# 生命周期(od-dev-stop-hooks §2.1 临时捕获类):失败模式根因修完并验证后删整段
# (谓词/写 flag/挂点一并删),不留开关/参数。

#: 哨兵 flag 路径(仓根锚定绝对路径:daemon spawn 的非 CWD 进程里相对路径会落错,
#: 同 shop_unk 钩子审查#4 教训;测试经 write_exec_fail_flag 参数注入 tmp_path)。
_EXEC_FAIL_FLAG_RELPATH = Path('.debug') / 'temp' / 'cw_exec_fail_hook.flag'


def exec_fail_flag_path() -> Path:
    """哨兵 flag 绝对路径(锚仓根,经 one_dragon.utils.file_utils.get_project_root 定位)。"""
    return get_project_root() / _EXEC_FAIL_FLAG_RELPATH


def exec_fail_should_stop(plan_actions: list | None, gold_open, gold_close, *,
                          boundary: str = 'closed',
                          executed: dict | None = None) -> bool:
    """安灯式停机谓词(纯函数,可单测):mismatch 才停。

    mismatch = 分类器 not_effective(计划花费>0 且金差≈0 且**已尝试**——
    真点击落空);partial_mismatch(金动了但对不上账)与 unknown(读数缺失/
    半单元)不停——前者可能是口径差非执行失败,后者证据不足。W577(ADR-0456)
    扩两豁免态:**plan_truncated**(plan 有动作未尝试——硬墙跳过/截断,口径差)
    与 **free_refresh_proc**(刷新已尝试+牌面已变+金差≈0,免费生效)——verdict
    域变宽,本谓词仍只对 not_effective 停,自动豁免两新态。判定复用
    ``cw_telemetry.classify_spend_unit``,不建第二套分类。
    """
    from sr_od.application.currency_war.telemetry.cw_telemetry import (
        classify_spend_unit,
    )
    cls = classify_spend_unit(plan_actions or [], gold_open, gold_close,
                              boundary=boundary, executed=executed)
    return cls['verdict'] == 'not_effective'


def write_exec_fail_flag(flag_path: Path, *, run_id: str, plane: int,
                         round_num: int, unit_seq: int, plan_summary: str,
                         gold_open, gold_close) -> str:
    """写哨兵 flag(纯 IO,可单测;内容锁 od-dev-stop-hooks flag 三要素)。

    三要素:触发定位(HOOK-STOP 标记+钩子位置+触发态+时间)/ 可执行处理步骤 /
    删除条件(临时捕获类 = 根因修完删整段钩子)。返回写入内容(测试断言用)。
    """
    content = (
        '[HOOK-STOP] 执行失败停机钩子(临时采证,安灯式;prep_director 购买单元记账边界)\n'
        f'触发:购买单元关闭时分类器判 mismatch(计划花费>0 且金差≈0 = 动作发出但金没动;'
        f'partial/unknown 不停)。\n'
        f'定位:run_id={run_id} p{plane}r{round_num} unit_seq={unit_seq} '
        f'ts={time.strftime("%Y-%m-%d %H:%M:%S")}\n'
        f'plan 摘要:{plan_summary}\n'
        f'gold:开={gold_open} 关={gold_close}\n'
        f'截图:.debug/images/exec_fail_* (前缀含 run_id/轮/unit_seq)\n'
        f'处理步骤:1. 看截图核购买单元画面;2. 对拍 replay 三流(spend_ledger 单元行/'
        f'decisions shop plan 行/obs_conflicts gold_delta 行)确认是执行未生效'
        f'(点击落空/被拦)还是口径失配;3. 修失败模式并验证后,删本 flag + 删整段钩子'
        f'(prep_director 安灯段)+ 重启载入代码的进程。\n'
        f'删除条件:临时采证钩子——失败模式根因修完并验证后删整段,不留开关。\n'
    )
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(content, encoding='utf-8')
    return content


#: 环入口预收探针的重试间隔(秒)。时序竞争背景:战斗胜利后新回合
#: 游戏自动开商店的时刻**晚于**环入口预收探针——首探探不到
#: 「按钮-收起」→ 落进 PROFILE_CLOSED 完整门,商店开后关态锚永不
#: 命中,打满 12s 超时才由容忍探针收起+round_retry 重进(实机每局
#: 9-25 次,依据单局耗时深挖报告
#: .debug/temp/currency_war/w417_duration_audit/REPORT.md「确定可压」
#: 第 1 条)。修法=探针前置重试:窗内对开态持续检测(同一探测原语,
#: 不新增判据),探到即走既有「收起→收紧超时 gate」路径。
PRECOLLAPSE_RETRY_S: float = 1.0

#: 预收探针重试次数上限(窗 ≈ 次数×间隔+探针自身成本,~4.5s 档)。
#: 上限的意义:从不自动开商店的轮次(新位面首环/无自动开店)最多
#: 多付一个窗的探针成本,不引入无界等待;超过窗仍未开 → 走原
#: 12s 完整门,行为不变。
PRECOLLAPSE_RETRIES: int = 3


# ===== 拖动期望态对账(期望态层·逻辑版本)=====
# 架构原则(用户 2026-08-28 裁决):指令发出时用纯函数从动作意图计算
# 「执行后世界应有的增量」;动作完成后的定型帧实读逐槽对账;不一致落
# 缺陷台账(复现升 L0,停线由 W515 分级安灯承接),一致不打扰,零决策
# 行为变更。同族先例=观测自检框架设计 §2.2 买牌落位对拍
# (.debug/temp/currency_war/w505_obs_audit/DESIGN.md)。
# 边界:本对账只辖 prep_director 直发链的拖动动作(SellBench/DeployMove)。
# 买牌期望态走独立通道:购买意图在 shop.py 买入点记录(compute_buy_expect,
# 落点规则单一源 = cw_state._merge_bench),由本环在 RunBuyPhase 后的 heavy
# 定型帧上消费对账(_reconcile_buy_expect,台账 kind=buy_expect_mismatch);
# RunBuyPhase 内 shop.py 的 SellBench 仍走 §2.2 既有通道,破警告分支
# (bench_full)无定型帧不进对账。

#: 台账 surface/kind(缺陷台账复现计数按 (surface, kind, expected) 分档,
#: 消费端按字符串聚合;勿改已有行口径)。
_DRAG_DEFECT_SURFACE = 'bench'
_DRAG_DEFECT_KIND = 'intent_state_mismatch'


@dataclass
class DragExpect:
    """一次拖动动作的期望态(compute_drag_expect 产出 / compare_drag_expect 消费)。

    [索引定义] from_slot = 备战栏画面物理槽位 1-9(prep_actions 族 B 坐标系);
    target_slot = 部署排**排内**物理槽位 1-N。取值时机 = 动作发出时快照
    (源 = 上次 heavy 观察的 SIFT 身份,非执行期现读)。
    identity/target_identity = SIFT 规范名;identity 空 = 源槽身份未识别。
    """
    kind: str                # 'sell'(拖卖出)| 'deploy_move'(拖到部署排)
    identity: str            # 被拖角色身份(SIFT 名)
    from_slot: int           # bench 源物理槽位 1-9
    target_row: str = ''     # deploy_move:'front'/'back'
    target_slot: int = 0     # deploy_move:目标排内槽位
    target_kind: str = ''    # deploy_move:'place'(空槽落位)/'swap'(互换)
    target_identity: str = ''  # 目标槽执行前身份(swap 期望换回本槽用)


def compute_drag_expect(action: PrepAction,
                        bench_chars: list[BenchChar],
                        deployed_chars: list[BenchChar]) -> DragExpect | None:
    """动作意图 → 期望态(纯函数;期望态由发指令的同一条代码路径更新,
    动作语义单一源,防模型与现实分叉——架构原则边界②)。

    无法建真值 → None 不评(对齐「无法建真值不评」基准口径,不猜):
    - 源槽身份未识别(上次 heavy SIFT 无该槽条目);
    - deploy_move 目标槽为**同名**占用——merge_mechanics.md §3 恒成立约束
      「场上同名同星 ≤1」+ 部署链 5.1.7 不变量「同角色在场只 1」下该动作
      不可达(游戏拒绝),期望态不定义(原「语义未核实」口径按该档收口)。
    """
    if isinstance(action, SellBench):
        ident = next((bc.char_id for bc in bench_chars
                      if bc.slot == action.slot and bc.char_id), '')
        if not ident:
            return None
        return DragExpect(kind='sell', identity=ident, from_slot=action.slot)
    if isinstance(action, DeployMove):
        ident = next((bc.char_id for bc in bench_chars
                      if bc.slot == action.from_slot and bc.char_id), '')
        if not ident:
            return None
        tgt = next((dc for dc in deployed_chars
                    if dc.position_pref == action.to_row
                    and dc.slot == action.to_slot and dc.char_id), None)
        if tgt is None:
            tk, ti = 'place', ''
        elif tgt.char_id == ident:
            return None   # 同名占位:游戏语义未核实,不发明期望
        else:
            tk, ti = 'swap', tgt.char_id
        return DragExpect(kind='deploy_move', identity=ident,
                          from_slot=action.from_slot,
                          target_row=action.to_row, target_slot=action.to_slot,
                          target_kind=tk, target_identity=ti)
    return None


def compare_drag_expect(expect: DragExpect,
                        bench_read: list[BenchChar],
                        deployed_read: list[BenchChar]) -> list[dict[str, str]]:
    """期望态 vs 定型帧实读逐槽比对(纯函数)。

    判据(槽位级身份比对):
    - sell:源槽**不得再出现该身份**(原槽位空/无该身份;SIFT 未识别≠空槽,
      槽内其他身份不构成本判据的不一致——身份消失即满足任务语义①);
    - deploy_move/place:源槽无该身份 + 目标槽=该身份(空槽落位);
    - deploy_move/swap:两槽互换(源槽=原目标身份 + 目标槽=被拖身份)。
    实读中该槽**无条目**(SIFT 未识别/空读)= 无法建真值 → 跳过不评,
    不算一致也不算不一致。返回不一致项列表(空列表=全部可比项一致)。
    """
    mism: list[dict[str, str]] = []

    def _bench_at(slot: int) -> BenchChar | None:
        return next((c for c in bench_read if c.slot == slot and c.char_id), None)

    def _dep_at(row: str, slot: int) -> BenchChar | None:
        return next((c for c in deployed_read
                     if c.position_pref == row and c.slot == slot and c.char_id), None)

    def _add(domain: str, slot: int, want: str, got: str) -> None:
        mism.append({'domain': domain, 'slot': str(slot),
                     'expected': want, 'observed': got})

    if expect.kind == 'sell':
        src = _bench_at(expect.from_slot)
        if src is not None and src.char_id == expect.identity:
            _add('bench', expect.from_slot, f'无 {expect.identity}(已卖出)',
                 src.char_id)
        return mism
    # deploy_move:源槽
    src = _bench_at(expect.from_slot)
    if expect.target_kind == 'place':
        if src is not None and src.char_id == expect.identity:
            _add('bench', expect.from_slot, f'无 {expect.identity}(已离槽)',
                 src.char_id)
    else:   # swap
        if src is not None and src.char_id != expect.target_identity:
            _add('bench', expect.from_slot, expect.target_identity, src.char_id)
    # 目标槽(place 与 swap 同判:应是被拖身份)
    tgt = _dep_at(expect.target_row, expect.target_slot)
    if tgt is not None and tgt.char_id != expect.identity:
        _add(f'deployed.{expect.target_row}', expect.target_slot,
             expect.identity, tgt.char_id)
    return mism


# ===== 买牌期望态(merge_mechanics.md §1/§2/§2.5 落点规则的期望态层)=====

#: 台账 surface/kind(买牌通道;surface 与拖动通道同域——都是备战板面身份账,
#: 复现计数按 (surface, kind, expected) 分档,kind 区分通道)。
_BUY_DEFECT_KIND = 'buy_expect_mismatch'


@dataclass
class BuyPurchase:
    """一次 RunBuyPhase 单元内记录的单条购买意图(shop.py 买入点写入)。

    [定义注释] name/star = 商店牌 OCR 身份与星级(ShopCard 真值源);
    count = 该牌本单元购入张数 k——常态=1;备战栏满且可触发合成时 =
    游戏自动多买 min(店内同牌张数, 3−已有数 mod 3)(merge_mechanics §2.5,
    【置信:低】,由对账网实证修正);unit_cost = 单体招募费(无折扣:
    总价 = k×unit_cost,§2.5 无价格优惠)。
    """
    name: str
    star: int
    count: int
    unit_cost: int
    #: 买前商店帧中该牌的矩形裁片(numpy .copy(),~125KB/张;整帧被帧缓存
    #: 复用覆写,必须拷贝;一帧原则:来自读牌时已截的帧,零新增截屏)。
    #: 对账不一致时落盘 = 「买了什么」的像素级证据(比意图对象硬);平时零磁盘写入。
    crop: object = None


@dataclass
class BuyExpect:
    """一次 RunBuyPhase 购买单元的期望态(compute_buy_expect 产出 /
    compare_buy_expect 消费)。

    [索引定义] bench_after = 期望备战栏槽位表(下标 0-8 = 物理槽位 1-9,
    None=空槽);deployed_after = 期望上阵槽位表(下标 0-3=前排排内槽 1-4、
    4-9=后排排内槽 1-6,ADR-0392 槽位语义)。changed_* = 相对购买前快照
    发生变化的槽位集(对账只评增量槽位,存量漂移归 reconcile_tracking)。
    取值时机 = 购买意图记录期快照(shop.py 买入点),写入端 = shop.buy。
    """
    bench_after: list[BenchChar | None]
    deployed_after: list[BenchChar | None]
    changed_bench: list[int]       # 1-based 物理槽位
    changed_deployed: list[int]    # deployed 槽位下标 0-9
    summary: str                   # 购买意图摘要(台账 refs 用)
    total_cost: int                # 期望扣金 = Σ(k×单价)(无折扣口径)
    low_confidence: bool = False   # 含满栏自动多买子案(k>1,§2.5 置信低)
    #: 各次购买的商店牌裁片拷贝 [(角色名, 裁片)];随期望态带到对账点作
    #: 「买了什么」像素证据,对账完成即释放(置 None),平时零磁盘写入。
    crops: list | None = None


def compute_buy_expect(purchases: list[BuyPurchase],
                       bench: list[BenchChar | None],
                       deployed: list[BenchChar | None]) -> BuyExpect | None:
    """购买意图序列 → 买后期望态(纯函数;merge_mechanics.md 规则映射):

    - 买牌落点(§1):默认 = 备战栏首个空槽(bench_place);触发 3 合 1 时
      落点优先级(场上吸收 > 备战最左)= ``cw_state._merge_bench`` 载体
      选择单一源,连锁合成(§2)= 其不动点循环;
    - 满栏自动多买(§2.5):k>1 时逐张入表(满栏暂溢出表尾),合并腾槽后
      仍有无处安放散牌 → 保留溢出表(对账只评 1-9 槽,散牌槽自然跳过,
      不一致=证据落台账,不改语义——文档声明由对账实证修正);
    - 无价格优惠(§2.5):total_cost = Σ(k×unit_cost) 记全款。

    无法建真值 → None 不评:任一意图身份未识别(OCR 空名——期望缺该牌
    增量必成片假不一致,宁缺勿造)。
    """
    if any(not p.name for p in purchases):
        return None
    bench_t: list[BenchChar | None] = [None] * BENCH_CAPACITY
    for bc in bench:
        if bc is not None:
            bench_place(bench_t, deepcopy(bc))
    dep_t: list[BenchChar | None] = list(deployed) if deployed else []
    dep_t = [deepcopy(c) for c in dep_t]
    low_conf = False
    for p in purchases:
        for _ in range(max(1, p.count)):
            if p.count > 1:
                low_conf = True
            bc = BenchChar(slot=0, char_id=p.name, star=p.star,
                           position_pref='back')
            if bench_place(bench_t, bc) is None:
                bench_t.append(bc)   # 满栏暂溢出(§2.5 例外购买)
    cw_merge_bench(bench_t, dep_t)
    changed_b = [i + 1 for i in range(BENCH_CAPACITY)
                 if _slot_diff(bench_t[i] if i < len(bench_t) else None,
                               bench[i] if i < len(bench) else None)]
    changed_d = [i for i in range(len(dep_t))
                 if _slot_diff(dep_t[i],
                               deployed[i] if i < len(deployed) else None)]
    summary = ';'.join(f'{p.name}/{p.star}星×{p.count}@{p.unit_cost}'
                       for p in purchases)
    return BuyExpect(bench_after=bench_t, deployed_after=dep_t,
                     changed_bench=changed_b, changed_deployed=changed_d,
                     summary=summary,
                     total_cost=sum(p.unit_cost * max(1, p.count)
                                    for p in purchases),
                     low_confidence=low_conf,
                     crops=[(p.name, p.crop) for p in purchases
                            if p.crop is not None] or None)


def _slot_diff(a: BenchChar | None, b: BenchChar | None) -> bool:
    """槽位级 (身份, 星级) 差异判据(compute_buy_expect 增量集用)。"""
    ka = (getattr(a, 'char_id', '') or '', getattr(a, 'star', 1) or 1) \
        if a is not None else None
    kb = (getattr(b, 'char_id', '') or '', getattr(b, 'star', 1) or 1) \
        if b is not None else None
    return ka != kb


def compare_buy_expect(expect: BuyExpect,
                       bench_read: list[BenchChar],
                       deployed_read: list[BenchChar]) -> list[dict[str, str]]:
    """买牌期望态 vs 定型帧实读逐槽比对(纯函数;仅评增量槽位)。

    判据(槽位级身份+星级比对,W530 同款宁缺勿造):实读中该槽无条目
    (SIFT 未识别/空读)= 无法建真值 → 跳过不评,不算一致也不算不一致;
    期望空槽而实读有身份 = 不一致(合成腾槽未发生/多买散牌证据)。
    返回不一致项列表(空列表=全部可比项一致)。
    """
    mism: list[dict[str, str]] = []

    def _add(domain: str, slot: int | str, want: str, got: str) -> None:
        mism.append({'domain': domain, 'slot': str(slot),
                     'expected': want, 'observed': got})

    for slot in expect.changed_bench:
        exp = expect.bench_after[slot - 1]
        got = next((c for c in bench_read
                    if c.slot == slot and c.char_id), None)
        if got is None:
            continue   # 实读无条目:不评
        want_id = exp.char_id if exp is not None else ''
        if got.char_id != want_id or _slot_diff(exp, got):
            _add('bench', slot,
                 f'{want_id or "空"}{f"/{exp.star}星" if exp is not None else ""}',
                 f'{got.char_id}/{got.star}星')
    for idx in expect.changed_deployed:
        exp = expect.deployed_after[idx] if idx < len(expect.deployed_after) \
            else None
        row = 'front' if idx < 4 else 'back'
        slot_no = deployed_slot_no(idx)
        got = next((c for c in deployed_read
                    if c.position_pref == row and c.slot == slot_no
                    and c.char_id), None)
        if got is None:
            continue
        want_id = exp.char_id if exp is not None else ''
        if got.char_id != want_id or _slot_diff(exp, got):
            _add(f'deployed.{row}', slot_no,
                 f'{want_id or "空"}{f"/{exp.star}星" if exp is not None else ""}',
                 f'{got.char_id}/{got.star}星')
    return mism


def _save_buy_evidence(evidence_dir: str, file_tag: str, expect: BuyExpect,
                       mism: list[dict[str, str]], frame: MatLike | None,
                       bench_slots: list[tuple[int, Rect]]) -> list[str]:
    """对账不一致时的现场留证(钩子素材;平时零磁盘写入)。

    落盘两类裁片:①买前商店帧的被买牌裁片(expect.crops——像素级「买了
    什么」证据,比意图对象硬);②定型帧中不一致备战槽的对应裁片(实读
    现场证据)。文件名带 file_tag(位面-轮次)与身份,便于与台账行互查。
    返回落盘路径列表(best-effort:单张失败跳过,不阻塞对账记账)。
    调用方在对账完成后置 ``expect.crops = None`` 释放内存(裁片是拷贝,
    不留整帧,~125KB/张)。
    """
    from one_dragon.utils import cv2_utils
    paths: list[str] = []
    try:
        base = Path(evidence_dir)
        base.mkdir(parents=True, exist_ok=True)
        for name, crop in (expect.crops or []):
            if crop is None:
                continue
            p = base / f'buy_expect_{file_tag}_buy_{name}_{len(paths)}.webp'
            cv2_utils.save_image(crop, str(p))
            paths.append(str(p))
        if frame is not None:
            for m in mism:
                if m['domain'] != 'bench':
                    continue
                slot = int(m['slot'])
                rect = next((r for s, r in bench_slots if s == slot), None)
                if rect is None:
                    continue
                crop = frame[rect.y1:rect.y2, rect.x1:rect.x2]
                p = base / (f'buy_expect_{file_tag}_settle_bench'
                            f'{slot}_{len(paths)}.webp')
                cv2_utils.save_image(crop, str(p))
                paths.append(str(p))
    except Exception:   # noqa: BLE001  留证 best-effort,不阻塞对账记账
        pass
    return paths


# ===== 经验期望态账本(W552:XP/等级期望态对账;架构同 W536 买牌/W530 拖动)=====

#: 台账 surface/kind(经验通道;复现计数按 (surface, kind, expected) 分档)。
_XP_DEFECT_SURFACE = 'xp'
_XP_DEFECT_KIND = 'xp_expect_mismatch'

#: RunBuyPhase 执行返回 detail 中「升级次数」的解析形态。来源链:shop.py
#: 单元收尾摘要 'plan 买N张 升M次 刷K次 …'(total_level = 执行侧实际单击数)
#: → prep_actions._run_composite 透传为 director 的 execute detail。
_XP_BUY_CLICKS_PAT = re.compile(r'升(\d+)次')


@dataclass
class XpLedger:
    """计算侧经验账本(会话级;锚点 + 意图推进 + 逐段对账,零决策记账)。

    [字段定义] level/xp_cur/xp_next = 计算侧期望的 (等级, 当前级已攒经验,
    当前级门槛)——坐标系 = 游戏 XP 条整局语义(门槛表 = XP_TO_NEXT_LEVEL
    单一源);取值时机 = 锚点帧读数或购买意图经 xp_apply_clicks 纯推算,
    **非执行期现读**;写入端 = PrepDirector._xp_* 三方法(单写者)。
    anchored = 对局首帧锚定是否完成(锚定前不对账——纯推算的起点必须是
    真实读数,否则整段账失真)。
    round_key = 本对账段 (plane, round_num)——**轮界即重锚点**:轮间存在
    未建模外生经验流(局⑳+1 replay 实测轮间 +2、位面过渡更大,来源未定),
    吸收进锚点不进对账,累计披露于 exogenous_xp(把未知变实测,不硬编码)。
    pending_clicks = 锚点后本段累计购买经验击数(>0 才对账;对账一次即清)。
    events_txt = 本段事件摘要(台账 refs 用)。
    exogenous_xp = 轮界重锚吸收的外生经验累计(纯观测披露,不参与对账)。
    """
    level: int = 0
    xp_cur: int = 0
    xp_next: int = 0
    anchored: bool = False
    round_key: tuple[int, int] | None = None
    pending_clicks: int = 0
    events_txt: str = ''
    exogenous_xp: int = 0


def _xp_parse_buy_clicks(detail: str) -> int:
    """RunBuyPhase 执行 detail → 购买经验单击数;解析不出 → 0(宁缺勿造:
    该单元不进经验账,不做猜测推进)。"""
    m = _XP_BUY_CLICKS_PAT.search(detail or '')
    return int(m.group(1)) if m else 0


def _xp_compare(ledger: XpLedger, display: tuple[int, int] | None,
                level_obs: int) -> list[dict[str, str]]:
    """计算侧期望 vs 备战稳定帧显示读数(纯函数;XP/等级双源对账判据)。

    - display = read_xp_progress 显示读数 (cur, next);None = 无法建真值
      → 不评(宁缺勿造);
    - level_obs = 显示等级(read_game_state 三源解析值);≤0 = 失读不评;
    - 等级判据:计算 level vs 显示 level——等级是 deploy cap 的输入,
      双源一致 = cap 可信(交叉验证);xp 判据:cur / next 逐项。
    返回不一致项列表(空列表 = 全部可比项一致)。
    """
    mism: list[dict[str, str]] = []
    if display is None or level_obs <= 0:
        return mism
    if ledger.level != level_obs:
        mism.append({'domain': 'level', 'slot': '-',
                     'expected': str(ledger.level), 'observed': str(level_obs)})
    cur, nxt = display
    if ledger.xp_cur != cur:
        mism.append({'domain': 'xp', 'slot': 'cur',
                     'expected': str(ledger.xp_cur), 'observed': str(cur)})
    if ledger.xp_next != nxt:
        mism.append({'domain': 'xp', 'slot': 'next',
                     'expected': str(ledger.xp_next), 'observed': str(nxt)})
    return mism


# ===== 商店打开态对账(W564:cw_shop_obs 接线;纯记账+对账,零决策行为变更)=====

#: 台账 surface/kind(商店通道;复现计数按 (surface, kind, expected) 分档)。
_SHOP_DEFECT_SURFACE = 'shop'
_SHOP_POOL_DEFECT_KIND = 'shop_pool_violation'
_SHOP_REFRESH_DEFECT_KIND = 'refresh_expect_mismatch'
_SHOP_MERGE_DEFECT_KIND = 'merge_preview_mismatch'


def _shop_pool_inputs(st: GameState) -> tuple[list[tuple[str, int]], int]:
    """商店帧 state.shop → (参评牌列表, 未识别张数)(纯函数)。

    参评 = 有身份牌 ``(name, cost)``;未识别牌(name 空,SIFT miss 占位,
    cost=0)不进 check_shop_pool——空名+0 费会成 invalid_cost 假票,且
    「识别失败」已由 W512 置信通道管辖,此处只计数随 refs 披露。
    """
    shop = list(getattr(st, 'shop', None) or [])
    cards = [(c.name, c.cost) for c in shop if getattr(c, 'name', '')]
    return cards, len(shop) - len(cards)


def _merge_preview_inputs(st: GameState) -> tuple[dict[int, bool], dict[int, bool], int]:
    """商店帧 state → (我方合成旗, 识别读数旗, 未识别张数)(纯函数;
    compare_merge_preview 接线的入参折算单一源)。

    槽位键 = state.shop 列表下标(商店五格物理槽位,0 基左→右;同
    read_shop_cards 顺序,即 cw_shop_obs.compare_merge_preview 的槽位坐标系)。
    - our:``cw_state.same_star_count`` 全场域同名同星持有 >0(合成预览语义
      单一源 = merge_mechanics.md §2.7:✦ 数 = 已持同名同星副本份数;商店牌
      恒 1★,star 兜 1)。bench/deployed 取 state(由 session tracked 播种,
      与卡池票同帧一致)。
    - det:该牌 merge_preview > 0(W600 激活评估定的语义映射;0 是「无副本 ∨
      读不到」双义,映射为 False,our_suspect 祇当对账率归因,不逐票判死)。
    - 未识别牌(name 空,SIFT miss)两侧都算不出 → 不进 compare,只计数
      (同 _shop_pool_inputs 口径:识别失败归 W512 置信通道,此处不评)。
    """
    our: dict[int, bool] = {}
    det: dict[int, bool] = {}
    unnamed = 0
    bench = list(getattr(st, 'bench', None) or [])
    deployed = list(getattr(st, 'deployed', None) or [])
    for i, c in enumerate(list(getattr(st, 'shop', None) or [])):
        if not getattr(c, 'name', ''):
            unnamed += 1
            continue
        our[i] = same_star_count(c.name, getattr(c, 'star', 1) or 1,
                                 bench, deployed) > 0
        det[i] = int(getattr(c, 'merge_preview', 0) or 0) > 0
    return our, det, unnamed


def build_refresh_expect(gold: int | None,
                         refresh_cost: int | None,
                         cards_old: list[tuple[str, int]],
                         plane: int,
                         round_num: int) -> tuple[RefreshExpect, int, int] | None:
    """刷新动作发出点 → 期望增量(纯函数;producer 契约,None 口径单一源)。

    刷价输入契约(W577,ADR-0456):调用方传 ``cw_state.REFRESH_COST_BASE``
    基价常量——实付恒基价 2,「文本-刷新金币数」rect 是面板徽标(利息数值)
    非刷价,期望=实付,refresh_expect_mismatch 缺陷类随之归零。签名保留
    ``refresh_cost: int | None``:None 仍返回 None 跳过对账(gold 失读同理),
    供测试与未来免费 proc 建模(届时按「基价−免费抵扣」在此处计)传参;
    **禁把面板徽标读数当刷价传入**。

    挂账(producer 集成点):期望必须在**刷新波内**构建——波前金与波前
    面板费都是单元内部现读;prep_director 持有的 RunBuyPhase 前后帧均为
    关店帧(F2 下金不可信、五格牌不可读),无合法评估窗。集成点 =
    ``operations/prep/shop.py`` 刷新波现读处(先例 = pending_buy_expect
    同文件暂存、本环 heavy 帧消费);消费判据 = refresh_reconcile_mismatches
    (本文件,真值表已锁),落台账 kind=refresh_expect_mismatch。
    """
    if gold is None or refresh_cost is None:
        return None
    return refresh_expect(gold, cards_old, refresh_cost), plane, round_num


def refresh_reconcile_mismatches(expect: RefreshExpect,
                                 gold_after_obs: int | None,
                                 cards_named: int) -> list[dict[str, str]]:
    """刷新期望 vs 实读对账判据(纯函数;W556 口径:只硬验金差+有牌)。

    - 金腿:``gold_after_obs`` None = 失读不评(宁缺勿造);不等 = 一票
      (期望侧 gold_after 由 build_refresh_expect 保证基于波前现读,
      真值表含 0 与 None 分道)。
    - 牌腿:``cards_named`` = 实读有身份牌数;==0 = 刷新未生效形态开票;
      1-4 张**不判错**——低等级后槽未解锁是常态,槽位解锁规则未建模,
      「满格」期望无真值,计数由调用方随 refs 披露。
    """
    mism: list[dict[str, str]] = []
    if gold_after_obs is not None and gold_after_obs != expect.gold_after:
        mism.append({'domain': 'gold', 'slot': '-',
                     'expected': str(expect.gold_after),
                     'observed': str(gold_after_obs)})
    if cards_named <= 0:
        mism.append({'domain': 'cards', 'slot': '-',
                     'expected': '>=1', 'observed': '0'})
    return mism


@dataclass
class PrepObservation:
    """备战决策环统一观察(§3;决策单一输入,组合现成 reader 不新写识别)。

    P1 恒空字段(§13.4,策略不得依赖):overlay_state / overlay_options / shop_cards /
    owned_equips(P4 工具域接线)。

    分层语义:state/bench_chars/deployed_chars/deploy_vacancy 只在 heavy
    观察刷新(环入口 + 每个执行过的游戏动作后);light 步沿用上次 heavy 值(可能 stale,
    单线程内 stale 窗口 = 无动作步,安全)。轻字段(spheres/boxes/占用/shop_open/overlay)
    每步现读。
    """
    state: GameState | None = None        # heavy 重读;gold 仅 shop_open 时可信(F2)
    state_gold_trusted: bool = False      # F2:state.gold 是否可信(= heavy 时 shop 开)
    # r333(批次3):子态可读性(observe_full 产出;heavy 刷新/
    # light 沿用)——node_seq/shop_cards 本帧是否可读(按子态
    # 尽力读,跨步拼装全面性;方案 v5 A5)。
    substate: dict = field(default_factory=dict)
    bench_chars: list[BenchChar] = field(default_factory=list)   # heavy: SIFT 身份
    deployed_chars: list[BenchChar] = field(default_factory=list)
    spheres: list = field(default_factory=list)       # read_reward_spheres [(color, Point, r)]
    boxes: list = field(default_factory=list)         # read_supply_boxes [(slot, Point)]
    tomes: list = field(default_factory=list)         # read_tomes [(slot, Point)] 秘密典籍(2026-08-16)
    free_bench_slots: int = 0           # 9 − 占用(角色+箱都占席;CV 每步现读)
    deploy_vacancy: int = 0             # deploy_cap − deployed_count(heavy 刷新)
    shop_open: bool = False             # 锚点「按钮-收起」可见(每步现读)
    box_overlay_open: bool = False      # 武装箱 overlay(标识-请选择;每步现读)
    front_occupied: set = field(default_factory=set)  # 前排占用物理槽位号(每步现读)
    back_occupied: set = field(default_factory=set)
    front_size: int = 4
    back_size: int = 6
    overlay_state: str | None = None    # P5
    # 事件 overlay 检测(P1-4 过渡:盛会之星/选择伙伴/祈愿试炼 —— 挡操作,检测到即 BailToOuter
    # 交外环分支 handler;live 2026-08-15 实锤:盛会之星 overlay 下 deploy 全灭 → 空场 HP 82→1)
    event_overlay: str | None = None
    overlay_options: list | None = None # P5
    shop_cards: list | None = None      # P1 恒 None(仅买牌阶段刷新)


# ===== 装备期望态(装备拖拽语义的期望态层;语义单一源 =
# docs/game/currency_war/research/equipment_mechanics.md §1.1)=====

#: 台账 surface/kind(equip=中决策相关面,见 cw_telemetry.MEDIUM_CRITICAL_
#: SURFACES;复现计数按 (surface, kind, expected) 分档,勿改已有行口径)。
_EQUIP_DEFECT_SURFACE = 'equip'
_EQUIP_DEFECT_KIND = 'equip_expect_mismatch'


@dataclass
class EquipDragIntent:
    """一次装备区拖拽的意图载体(compute_equip_drag_expect 输入)。

    [定义注释] source_name = 被拖装备(装备区 owned 件,模板规范名;
    sell_char 语义下不适用,恒空);target_name = cell_synth:栏内拖放
    目标简易名 / wear_synth:目标角色已穿简易名(其余类空);
    equipped_names = sell_char:被卖角色已穿装备全量(动作发出帧
    read_equipped_below 快照;精度未验证,空读/失读按不评口径不进期望)。
    取值时机 = 动作发出时快照;写入端 = 动作发出点。
    """
    kind: str                  # 'cell_synth'|'wear'|'wear_synth'|'unequip'|'sell_char'
    source_name: str
    target_name: str = ''
    equipped_names: tuple[str, ...] = ()


@dataclass
class EquipExpect:
    """一次装备拖拽的期望态(compute_equip_drag_expect 产出 /
    compare_equip_expect 消费)。

    [定义注释] owned_before = 意图记录帧装备区占用计数快照(名字→格数;
    只算非遮挡占用格——遮挡格进快照会污染 after 对账基准);deltas =
    期望增量(名字→±n,装备区网格口径,不堆叠语义每格一件);product =
    合成产物名(台账 refs 用,非合成类空)。
    """
    kind: str
    summary: str
    deltas: dict[str, int]
    owned_before: dict[str, int]
    product: str = ''


def _synth_pair(a: str, b: str) -> str | None:
    """两件装备的合成产物(合成规则单一源 = cw_synthesis:交叉
    ``synthesize_target`` / 自配 ``self_advance``;非两基础件可合对 → None)。"""
    from sr_od.application.currency_war.data.cw_synthesis import (
        self_advance,
        synthesize_target,
    )
    if a == b:
        return self_advance(a)
    return synthesize_target(a, b)


def compute_equip_drag_expect(intent: EquipDragIntent,
                              owned_before: dict[str, int]) -> EquipExpect | None:
    """拖拽意图 → 装备区期望增量(纯函数;equipment_mechanics.md §1.1 映射):

    - cell_synth(栏内简易A→简易B):两件简易必合成(§1.1 28/28 配方
      实证),A/B 消耗、产物落 B 位(位置语义「合成落点」的栏内对应;
      网格对账按计数,产物占哪格不评);配对不可合(非法对/非简易/
      未知名)→ None 不评;
    - wear(简易→角色未穿简易):穿戴即离栏,网格 −1(角色侧本批不评
      —— read_equipped_below 精度未验证,按不评口径);
    - wear_synth(简易→角色已穿简易):两简易不能共存必合成(§1.1),
      产物落角色最左简易槽;拖入件离栏(网格 −1),已穿件在角色侧消耗、
      产物上角色(角色侧不评)。配对不可合 → None 不评;
    - unequip(卸下):回栏,网格 +1;
    - sell_char(卖角色):已穿装备全量回装备区(§1.1),网格逐件 +1;
      equipped_names 空(未穿/穿戴读失读)= 无可评增量 → None 不评。

    不堆叠语义(§1.1):装备区每格一件,计数=格数;row1 材料堆叠件
    (扳手等,非合成图谱)不进本批期望。source_name 空(sell_char 除外)
    → None。
    """
    src = intent.source_name
    if intent.kind != 'sell_char' and not src:
        return None
    deltas: dict[str, int] = {}
    product = ''

    def _dec(name: str) -> None:
        deltas[name] = deltas.get(name, 0) - 1

    if intent.kind == 'cell_synth':
        tgt = intent.target_name
        adv = _synth_pair(src, tgt) if tgt else None
        if adv is None:
            return None
        _dec(src)
        _dec(tgt)
        deltas[adv] = deltas.get(adv, 0) + 1
        product = adv
    elif intent.kind == 'wear':
        _dec(src)
    elif intent.kind == 'wear_synth':
        adv = (_synth_pair(src, intent.target_name)
               if intent.target_name else None)
        if adv is None:
            return None
        _dec(src)   # 已穿件在角色侧消耗,产物上角色(网格只减拖入件)
        product = adv
    elif intent.kind == 'unequip':
        deltas[src] = deltas.get(src, 0) + 1
    elif intent.kind == 'sell_char':
        for n in intent.equipped_names:
            deltas[n] = deltas.get(n, 0) + 1
        if not deltas:
            return None
    else:
        return None
    summary = (f'{intent.kind} {src}'
               + (f'→{intent.target_name}' if intent.target_name else '')
               + (f' 产物{product}' if product else '')
               + (f' 回栏×{len(intent.equipped_names)}'
                  if intent.kind == 'sell_char' else ''))
    return EquipExpect(kind=intent.kind, summary=summary, deltas=deltas,
                       owned_before=dict(owned_before), product=product)


def compare_equip_expect(expect: EquipExpect,
                         cells: list[EquipCell]) -> list[dict[str, str]]:
    """期望态 vs 装备区逐格实读比对(纯函数;cells = read_equip_grid 结果)。

    判据:deltas 涉及的每个名字,期望格数 = owned_before + delta,
    实读格数 = 非遮挡占用格计数;不等 = 不一致。遮挡格(详情面板盖住)
    实读 name=None——存在遮挡格时该名字可能正躺在遮挡格里,计数不可信
    → 整体跳过不评(不算一致也不算不一致,宁缺勿造)。实读中 deltas
    未涉及的名字 = 存量漂移(归 reconcile_tracking 既有通道),不进本对账。
    返回不一致项列表(空列表=全部可比项一致或整体不评)。
    """
    if any(c.occluded for c in cells):
        return []   # 遮挡格三态如实跳过(不评不算错)
    observed: dict[str, int] = {}
    for c in cells:
        if c.name is not None:
            observed[c.name] = observed.get(c.name, 0) + 1
    mism: list[dict[str, str]] = []
    for name, d in expect.deltas.items():
        want = expect.owned_before.get(name, 0) + d
        got = observed.get(name, 0)
        if want != got:
            mism.append({'domain': 'equip_grid', 'slot': name,
                         'expected': f'{want}格', 'observed': f'{got}格'})
    return mism


#: 未识别节点图标采集防抖(idx → 上次采集时刻)。module-level:r80 审计 c)实锤
#: PrepDirector 每备战环重建(battle_loop loop 内构造),实例属性跨环零存活 → 300s 窗
#: 失效(同 idx 每环各采一张,内容哈希对帧微变不设防)。
_NODE_ICON_SHOT_TS: dict[int, float] = {}


class PrepDirector(SrOperation):
    """备战决策环:观察驱动单步决策,替代 BattlePrepCycle 固定序列(P1)。

    单「决策环」节点 + 内部 while;环级预算 MAX_STEPS(步数)与 STALL_LIMIT(零进展)
    兜底强制出战(F5);ping-pong 由外环 MAX_ITER=2000 承担(勿引 node_max_retry —— round_wait
    不消耗 node 重试预算,operation.py:453-461 仅 RETRY 递增;strategy/03(原 doc 15§7) v7 M-1)。
    """

    # 环级预算(§7 环级:步数>60 或 stall≥5 且恢复已试尽 → 强制 StartBattle;实跑校准 §10)
    MAX_STEPS: ClassVar[int] = 60
    STALL_LIMIT: ClassVar[int] = 5
    # 同动作验证连败 2 → 恢复原语(一次/动作实例)→ 恢复后仍连败 2 → 分型 bail/屏蔽(§7)
    FAIL_TO_RECOVER: ClassVar[int] = 2
    BAIL_SAME_REASON_DIAG: ClassVar[int] = 3   # 同因 bail ≥3 → [cw!] 升诊断(局级计数)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-备战决策环')
        self._executor: PrepActionExecutor | None = None
        self._steps: int = 0
        self._stall: int = 0
        self._fail_counts: dict[str, int] = {}      # 动作实例键 → 连续验证失败次数
        self._blocked: set[str] = set()             # 本环屏蔽动作实例键(§7;StartBattle 豁免)
        self._recovered: set[str] = set()           # 已试过恢复原语的动作实例键(一次/实例)
        self._recovery_closed_known: dict[str, bool] = {}   # 恢复时是否关过已知弹层(分型用)
        self._recovery_tried: bool = False          # 本环恢复原语是否已试(强制出战门)
        self._bench_pts = []                        # screen_info 槽位中心(首步惰性读)
        # light 步沿用的 heavy 缓存(观察分层,review H-1)
        self._cached_state: GameState | None = None
        self._cached_bench: list[BenchChar] = []
        self._cached_deployed: list[BenchChar] = []
        self._cached_vacancy: int = 0
        self._cached_gold_trusted: bool = False
        # W494 spend_ledger:购买单元记账态(纯观测;unit_seq 本局序,run() 清零)
        self._spend_unit_seq: int = 0
        self._unit_meta: dict | None = None
        self._exec_fail_hook_fired: bool = False   # 安灯:每局最多停一次

    # ===== 观察(F2:只由现成 reader 产出)=====

    def _observe(self, heavy: bool, screen: MatLike | None = None) -> PrepObservation:
        """组装备战观察。heavy=True(环入口 + 每个执行过的游戏动作后):SIFT 身份 + GameState
        + cap 全重读;False(控制流/拒绝步后):只现读轻字段,heavy 字段沿用缓存。

        screen 传入时(r344:gate 末帧)复用该帧不重截——gate 稳定帧的全图 OCR 已
        按 id(image) 缓存,本方法所有 crop_first=False 读取(id_mark 判定/
        observe_full)全部缓存命中,heavy 观察的 OCR 成本归零;且观察的就是
        「已验证稳定」的那一帧(gate 语义),而非稳定后又隔一拍的帧。
        """
        # 光标 parking(审计 P0,2026-08-16,用户指示):上个动作(买牌点购买经验/拖拽停目标/
        # 点球)后光标停在点击处,与识别区重叠 → OCR/SIFT 污染(M38 level 毒化根因链)。
        # F1 契约:heavy 在每个执行过的游戏动作后必调 → 此处 park 覆盖全部动作后首读。
        if heavy:
            self.park_cursor()
        screen = screen if screen is not None else self.screenshot()
        obs = PrepObservation()
        if not self._bench_pts:
            self._bench_pts = row_area_centers(self.ctx, '备战栏')
        # 轻:球/箱/典籍/overlay/占用(每步现读)
        obs.spheres = read_reward_spheres(self.ctx, screen)
        obs.boxes = read_supply_boxes(self.ctx, screen)
        obs.tomes = cw_identity_obs_read_tomes(self.ctx, screen)
        obs.shop_open = self.round_by_find_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起', crop_first=False).is_success
        obs.box_overlay_open = self.round_by_find_area(
            screen, '货币战争-备战-武装箱选择', '标识-请选择', crop_first=False).is_success
        # 事件 overlay(挡操作:deploy/equip 全灭根因,live 2026-08-15):检测到即由环 bail 交外环。
        # star_tome(星徽秘典四选一)2026-08-16 补(review P2:纵深防御 —— loop 0i 判据 miss 时
        # 误派本环,穿模观察/动作失败搅动;加清单 → 即刻 bail 交回外环 0i 接管)。
        for _scr, _area, _tag in (
            ('货币战争-盛会之星', '标识-盛会之星', 'megastar'),
            ('货币战争-选择伙伴', '标识-选择伙伴', 'partner'),
            ('货币战争-祈愿试炼', '标识-祈愿试炼', 'wish_trial'),
            ('货币战争-星徽秘典弹窗', '标识-星徽秘典', 'star_tome'),
            # r10 review 根因修:投资策略/投资环境/补给 3 个 0e 屏(此前白名单缺 → 在策略屏上
            # 卡片立绘被 HoughCircles 误检成假球 → ClickSpheres 连败 → 恢复原语盲点 (960,530)
            # = 中卡描述区正中 → 误开星徽详情弹窗 → 15 streak 停机,M53 实锤)。
            ('货币战争-投资策略', '标识-请选择投资策略', 'invest_strategy'),
            ('货币战争-投资环境', '标识-投资环境', 'invest_env'),
            ('货币战争-补给', '标识-补给阶段', 'supply'),
        ):
            if self.round_by_find_area(screen, _scr, _area, crop_first=False).is_success:
                obs.event_overlay = _tag
                break
        occupied = [i + 1 for i, p in enumerate(self._bench_pts)
                    if slot_occupied(screen, int(p.x), int(p.y))]
        obs.free_bench_slots = max(0, len(self._bench_pts) - len(occupied))
        front_pts = row_area_centers(self.ctx, '前排')
        back_pts = row_area_centers(self.ctx, '后排')
        obs.front_size = len(front_pts)
        obs.back_size = len(back_pts)
        obs.front_occupied = {i + 1 for i, p in enumerate(front_pts)
                              if slot_occupied(screen, int(p.x), int(p.y))}
        obs.back_occupied = {i + 1 for i, p in enumerate(back_pts)
                             if slot_occupied(screen, int(p.x), int(p.y))}
        # 重:身份/星级/GameState/cap(环入口 + 结构变化 = 每个执行过的游戏动作)
        if heavy:
            # r331(批次1 收尾:observe_full 接线,终审最大缺口):
            # 可重定位读取(身份/gold==0 重读/substate)进组装层
            # 单一源;director 保留副作用编排(session 写/审计/
            # 缓存——单写者原则,批次3 全收敛)。
            from sr_od.application.currency_war.obs.cw_observe_full import (
                observe_full,
            )
            _of = observe_full(self.ctx, screen, tier='heavy',
                               source='director', op=self,
                               shop_open=obs.shop_open)   # r334:F2 门
            templates = ensure_portrait_templates(self.ctx)   # M-2:复用单一源(路径+缓存)
            if templates is not None:
                obs.bench_chars = _of.get('bench_chars') or []
                obs.deployed_chars = _of.get('deployed_chars') or []
                self._reconcile_tracking(obs.bench_chars, obs.deployed_chars, screen)
            else:
                obs.bench_chars = list(self._cached_bench)
                obs.deployed_chars = list(self._cached_deployed)
            st = _of['state']
            session = self._session()
            # r7 review P0-①:shop 关态帧节点行可读 → node_type 真值写 session(商店开态被遮恒 None,
            # plan 路径 boss 判定全死码的根因);仿 last_hp 模式。
            if session is not None and st.node_type:
                session.last_node_type = st.node_type
            st.bench = bench_from_compact(
                list(obs.bench_chars
                     or (session.tracked_bench_chars if session else [])))
            obs.state = st
            obs.state_gold_trusted = obs.shop_open   # F2:gold 仅 shop 开态可信(关态读空)
            if not obs.state_gold_trusted:
                log.debug('[cw][director] heavy 读 state 于 shop 关态 → gold 不可信')
            # MED-2 gold==0 重读已在 observe_full 内(r331 收敛
            # 双源:此处不再重复——终审「双源易漏同步」风险)
            if session is not None:
                # r333(批次3:单写者语义——hp 双源收口):写
                # last_state 前过 gated_hp(与 shop.py 同门同
                # 单源 helper)——修「director 写 32(gated)→
                # shop 写 100(现读)」反向翻转(r68 comp churn
                # 主燃料;终审 D-4)。两写者保留(各有上下文)
                # 但**写出的 hp 同源**:结算真值优先,新鲜度
                # 门拒绝陈值。
                _st_t = ((st.plane - 1) * 9 + st.round_num) \
                    if (st.plane and st.round_num) else None
                from sr_od.application.currency_war.cw_strategy import (
                    gated_hp as _gh,
                )
                st.hp = _gh(st.hp, session, _st_t,
                            current_readable=bool(
                                getattr(st, 'hp_readable', True)))
                session.last_state = st
            # r333(批次3:substate 消费)——observe_full 的可读性
            # 标注落 PrepObservation(下游对账/日志可判;轻步
            # 沿用缓存,同 _cached_state 语义)。
            obs.substate = _of.get('substate') or {}
            # ⚠ r334(review 第4条):以下 cap/双源审计用 heavy 段
            # 开头的旧 screen,而 st 可能来自 gold 重读的 0.3-0.9s
            # 后异帧——跨帧对拍在轮转动画窗内可假分歧(低概率,
            # 留证非阻塞);r334 后重读仅在 shop 开态,窗口缩小。
            cap = read_deploy_cap(self.ctx, screen)
            # 观察冲突审计 #15(2026-08-16;⚠ 2026-08-22 两段反转,ADR-0220+用户点题;
            # 2026-08-23 ADR-0281 再适配):财富宝钻官方效果「拥有即可使团队规模
            # 上限+1,无论是否被角色穿戴」可叠加(局38 r2 实证 cap5/lv3=两宝钻)。
            # 布局与 cap 无关(ADR-0281:level 驱动)后本检查只剩:
            # - cap < level → 不可能(读错/毒化)→ 留证(三源网 M38 天敌);
            # - cap ≥ level → 合法(cap>level=宝钻叠加,debug 记宝钻数)。
            if cap is not None and cap < st.level:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                # hook审计 L9(r351):verdict 补处理步骤——r350b 只补了
                # unverified 分支,这半还是裸的(deploy_cap 案例同款)
                obs_conflict('deploy_cap_vs_level', st.level, cap, screen,
                             verdict=('留证-cap<level不可能(cap或level读错;'
                                      '处理:看截图读「区域-部署数」X/Y 原文核 X>Y guard '
                                      '是否该拒,level 查 XP 反推是否一致;'
                                      '确认 reader 缺陷则修 read_deploy_cap/level 守卫;'
                                      '单次按 OCR 噪声忽略,复现 ≥3 次才排期)'),
                             source='paddle_cap')
            elif cap is not None:
                # W209/ADR-0385:cap>level(宝钻/钻石叠加)不再只是经济信息——口述
                # 公式「后台格数 = 6+(cap−level)」使 cap 差直接驱动布局选档
                # (cw_back_layout.select_back_layout,含 7 格未建档留证);
                # 旧 lv6 待采留证(note_pending_7slots)随 level 驱动模型作废删除。
                # review-L1(r353b):cap==level 是常态(无宝钻),别打
                # "宝钻×0"误导判读;仅真叠加(cap>level)才记
                if cap > st.level:
                    log.debug('[cw][obs] cap=%d(宝钻×%d 叠加,合法;后排扩展 +%d 格)',
                              cap, cap - st.level, cap - st.level)
            dep_n = read_deployed_count(self.ctx, screen)
            if cap is not None and dep_n is not None:
                obs.deploy_vacancy = max(0, cap - dep_n)
            else:
                obs.deploy_vacancy = self._cached_vacancy
            # 观察冲突审计 #9(2026-08-16):deployed 总数三源对拍(同帧全齐)——
            # board OCR 阵营计数和 vs paddle X(读 deployed_count)vs CV 占用(front+back)。
            # ⚠️ 语义修正(2026-08-17 r3 live):sum(board.values()) ≠ 部署角色数——
            # 一个角色贡献多阵营(藿藿=仙舟+治疗,4 人可贡献 11 阵营次),board 的 X 是
            # 「该阵营在场人数」非「角色数」→ board_sum 系统性 ≥ 部署数,拿它对拍恒分歧
            # (live M 实测 board_ocr=11/paddle=4/cv=4 的"分歧"全是本语义错,非 reader 毒化)。
            # 修:board 源改「独立羁绊外的最大单阵营计数」也不对(同阵营多角色)——board
            # 根本给不出角色数,**移出三源对拍**,对拍改双源(paddle X vs CV 占用)。
            _cv_occ = len(obs.front_occupied) + len(obs.back_occupied)
            if dep_n is not None:
                _spread = abs(dep_n - _cv_occ)
                if _spread > 1:
                    from sr_od.application.currency_war.kernel.cw_observe import (
                        obs_conflict,
                    )
                    # hook审计 L8(r351):verdict 补处理步骤(原只列根因无指引)
                    obs_conflict('deployed_count_2src',
                                 {'paddle_x': dep_n, 'cv_occupied': _cv_occ},
                                 'spread>1', screen,
                                 verdict=('留证-双源分歧(处理:看截图数前排+后排占用实数,'
                                          '与 paddle X 对拍;哪源对修哪源——paddle 对→CV '
                                          '阈值/遮挡误漏,CV 对→X/Y 拆框;'
                                          '单次按噪声忽略,同局 ≥3 次排期修)'),
                                 source='director_heavy')
            # 更新 light 沿用缓存(trusted 位随 state 缓存,MED-1 —— light 步不重判 shop 态,
            # 缓存 state 生成时的可信度就是它的可信度)
            self._cached_state = st
            self._cached_bench = list(obs.bench_chars)
            self._cached_deployed = list(obs.deployed_chars)
            self._cached_vacancy = obs.deploy_vacancy
            self._cached_gold_trusted = obs.state_gold_trusted
        else:
            # light:heavy 字段沿用缓存(上次真读值;review H-1 — 不再恒默认导致永动机)
            obs.state = self._cached_state
            obs.state_gold_trusted = self._cached_gold_trusted   # MED-1:trusted 位随缓存 state
            obs.bench_chars = list(self._cached_bench)
            obs.deployed_chars = list(self._cached_deployed)
            obs.deploy_vacancy = self._cached_vacancy
        return obs

    def _reconcile_tracking(self, bench: list[BenchChar], deployed: list[BenchChar],
                            screen=None) -> None:
        """环入口对账(§3:read≠tracking 漂移是既有 bug 源 → SIFT 真值重置 tracking)。

        继任宿主:deploy_bench._reconcile_tracking + battle_prep._verify_recognition(P1 挂载
        切换搬入;star 用 read_star 实机金星,同 D-12 语义)。read 失败(templates None)不动。
        漂移 = 需关注([cw!] + 截图存证,继承 _verify_recognition 语义,review L-1)。
        2026-08-16(观察冲突审计 #11):改调公共 ``cw_reconcile.reconcile_tracking`` ——
        与 deploy_bench 版同语义统一(空读守卫/漂移留证/obs_conflict JSONL 单一实现)。
        """
        session = self._session()
        if session is None:
            return
        from sr_od.application.currency_war.kernel.cw_reconcile import (
            reconcile_tracking,
        )
        reconcile_tracking(session, bench, deployed, screen, source='director', ctx=self.ctx)

    def _reconcile_drag_expect(self, expect: DragExpect) -> None:
        """拖动期望态对账(动作完成后调用;零决策行为变更:不一致仅落台账)。

        读法:复用动作后 heavy 重观察的定型帧(``last_screenshot``,零新增
        截屏);身份读走 identify_slots 纯读组合(**不经 read_bench_chars**
        ——后者内置召唤物/书册卡停机钩子,动画帧误触停机即违背本对账零
        行为约束;先例=观测自检框架 §2.2 身份回读)。deployed 排复用
        read_deployed_chars(其挂点均为留证级非停机,且后排布局选档单一源)。
        全部 best-effort:任一环节失败静默跳过(宁缺勿造)。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            templates = ensure_portrait_templates(self.ctx)
            if templates is None:
                return
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                identify_slots,
                read_deployed_chars,
            )
            bench_read = identify_slots(
                frame, templates, _ctx_slots(self.ctx, '备战栏', 9), '')
            deployed_read = read_deployed_chars(self.ctx, frame, templates)
            mism = compare_drag_expect(expect, bench_read, deployed_read)
            if not mism:
                return
            obs_st = self._cached_state
            exp_txt = (f'{expect.kind} identity={expect.identity} '
                       f'from_slot={expect.from_slot}'
                       + (f' target={expect.target_row}{expect.target_slot}'
                          f'/{expect.target_kind}' if expect.kind == 'deploy_move' else ''))
            obs_txt = ';'.join(f"{m['domain']}槽{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            cw_telemetry.record_defect(
                _DRAG_DEFECT_SURFACE, _DRAG_DEFECT_KIND,
                expected=exp_txt, observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-拖动后期望态与定型帧实读不一致(身份未识别槽不评;'
                         '单次 L1,复现自动升 L0,停线由分级安灯承接;本对账'
                         '零决策行为,不 return/不重拖)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('kind', expect.kind), ('identity', expect.identity),
                    ('from_slot', str(expect.from_slot)),
                    ('target_row', expect.target_row),
                    ('target_slot', str(expect.target_slot)),
                    ('target_kind', expect.target_kind))],
                reader_source='drag_expect_reconcile',
                note='期望态层:期望=动作意图纯函数,与 W512 paddle 动作级对拍分立(身份级 vs 计数级)')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] drag_expect reconcile skip: {e}')

    def _reconcile_buy_expect(self, expect: BuyExpect) -> None:
        """买牌期望态对账(RunBuyPhase 完成后调用;零决策行为变更:不一致仅落台账)。

        读法与 _reconcile_drag_expect 同款:复用 heavy 定型帧(last_screenshot,
        零新增截屏)+ identify_slots/read_deployed_chars 纯读组合(不经
        read_bench_chars 停机钩子)。全部 best-effort:任一环节失败静默跳过
        (宁缺勿造)。低置信子案(满栏自动多买)不一致照常落账——对账不一致
        =证据,如实落台账不改语义(merge_mechanics §2.5 声明由对账实证修正)。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            templates = ensure_portrait_templates(self.ctx)
            if templates is None:
                return
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                identify_slots,
                read_deployed_chars,
            )
            bench_read = identify_slots(
                frame, templates, _ctx_slots(self.ctx, '备战栏', 9), '')
            deployed_read = read_deployed_chars(self.ctx, frame, templates)
            mism = compare_buy_expect(expect, bench_read, deployed_read)
            if not mism:
                return
            obs_st = self._cached_state
            exp_txt = (f'buy {expect.summary} 总价{expect.total_cost}'
                       + ('(低置信:满栏自动多买)' if expect.low_confidence else ''))
            obs_txt = ';'.join(f"{m['domain']}槽{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            # 现场留证(仅不一致时落盘,平时零磁盘写入):买前商店牌裁片
            # (像素级「买了什么」证据)+ 定型帧不一致备战槽裁片;落在台账
            # 回放目录(与 defect_ledger 同域)。file_tag=位面-轮次 便于互查。
            evidence: list[str] = []
            try:
                _rec = cw_telemetry.get_recorder()
                _dir = getattr(_rec, 'replay_dir', None) if _rec else None
                if _dir:
                    _tag = (f"p{int(getattr(obs_st, 'plane', 0) or 0)}"
                            f"-r{int(getattr(obs_st, 'round_num', 0) or 0)}")
                    evidence = _save_buy_evidence(
                        str(_dir), _tag, expect, mism, frame,
                        _ctx_slots(self.ctx, '备战栏', 9))
            except Exception:   # noqa: BLE001  留证 best-effort
                evidence = []
            cw_telemetry.record_defect(
                _DRAG_DEFECT_SURFACE, _BUY_DEFECT_KIND,
                expected=exp_txt, observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-买牌后期望态与定型帧实读不一致(仅评增量槽;'
                         '身份未识别槽不评;单次 L1,复现自动升 L0,停线由'
                         '分级安灯承接;本对账零决策行为,不 return/不重买)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('summary', expect.summary),
                    ('total_cost', str(expect.total_cost)),
                    ('low_confidence', str(expect.low_confidence)),
                    ('changed_bench', ','.join(map(str, expect.changed_bench))),
                    ('changed_deployed', ','.join(map(str, expect.changed_deployed))),
                    ('evidence', ';'.join(evidence)))],
                shot=evidence[0] if evidence else None,
                reader_source='buy_expect_reconcile',
                note='期望态层·买牌:期望=购买意图纯函数(落点规则单一源 '
                     'cw_state._merge_bench),与拖动通道 intent_state_mismatch 分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] buy_expect reconcile skip: {e}')
        finally:
            expect.crops = None   # 对账完成即释放裁片拷贝(内存,~125KB/张)

# ===== 经验期望态账本(W552;纯记账+对账,零决策行为变更)=====

    def _xp_ledger(self) -> XpLedger | None:
        """会话级账本取存(动态属性挂 StrategySession——pending_buy_expect
        同款先例;session 每局新建 → 账本天然局级生命周期,跨局零残留)。"""
        session = self._session()
        if session is None:
            return None
        led = getattr(session, 'xp_expect_ledger', None)
        if led is None:
            led = XpLedger()
            session.xp_expect_ledger = led
        return led

    def _xp_apply_levelup(self) -> None:
        """直接 LevelUp 动作通道推进账本(腾席链「循环点至 level+1、首次
        OCR 验证成功即停」;仅 progressed 调用 = 升级已验证达成,实际击数
        = xp_clicks_to_level 最小击数,无超额点击)。未锚定 → 丢弃(对局
        首帧锚定前的意图不推算,由锚点吸收)。"""
        led = self._xp_ledger()
        if led is None or not led.anchored:
            return
        clicks = xp_clicks_to_level(led.level, led.xp_cur)
        if clicks <= 0:
            return
        led.level, led.xp_cur = xp_apply_clicks(led.level, led.xp_cur, clicks)
        led.xp_next = XP_TO_NEXT_LEVEL.get(led.level, led.xp_cur)
        led.pending_clicks += clicks
        led.events_txt += f'+LevelUp×{clicks}(至{led.level}级)'

    def _xp_apply_buy_clicks(self, detail: str) -> None:
        """RunBuyPhase 通道推进账本:执行 detail 解析升级次数(执行侧实况
        计数,shop.py total_level 口径;调用方仅 progressed 分支——单元
        失败=未购买不推算)。已知盲区:shop._handle_bench_full 席满急救的
        盲击购买经验不经单元摘要 → 不在账,该形态的不一致是本对账的预期
        留证对象(verdict 注明,不改语义)。未锚定 → 丢弃(同上)。"""
        led = self._xp_ledger()
        if led is None or not led.anchored:
            return
        clicks = _xp_parse_buy_clicks(detail)
        if clicks <= 0:
            return
        led.level, led.xp_cur = xp_apply_clicks(led.level, led.xp_cur, clicks)
        led.xp_next = XP_TO_NEXT_LEVEL.get(led.level, led.xp_cur)
        led.pending_clicks += clicks
        led.events_txt += f'+buy×{clicks}击'

    def _reconcile_xp_expect(self, obs: PrepObservation) -> None:
        """备战稳定帧经验对账(heavy 帧消费;零决策:不一致仅落缺陷台账,
        不 return/不重买)。段语义见 XpLedger:轮界重锚(外生经验吸收并
        披露)/锚定前不对账/同段有未对账购买意图才评;display 或 level
        失读 → 保 pending 不评下帧重试(宁缺勿造)。全程 best-effort。"""
        try:
            led = self._xp_ledger()
            st = obs.state
            if led is None or st is None:
                return
            display = getattr(st, 'xp_progress', None)
            level_obs = int(getattr(st, 'level', 0) or 0)
            key = (int(getattr(st, 'plane', 0) or 0),
                   int(getattr(st, 'round_num', 0) or 0))
            if not led.anchored:
                if display is not None and level_obs > 0:
                    led.level, led.xp_cur = level_obs, display[0]
                    led.xp_next = display[1]
                    led.anchored = True
                    led.round_key = key
                    led.pending_clicks = 0
                    led.events_txt = ''
                return
            if led.round_key != key:
                # 轮界重锚:外生经验流(轮奖励/位面过渡,未建模)吸收进锚点;
                # 同级同门槛帧才把差值记入 exogenous_xp(异级差值不可分,不记)。
                if display is not None and level_obs > 0:
                    if led.level == level_obs and display[1] == led.xp_next:
                        led.exogenous_xp += max(0, display[0] - led.xp_cur)
                    led.level, led.xp_cur = level_obs, display[0]
                    led.xp_next = display[1]
                    led.round_key = key
                    led.pending_clicks = 0
                    led.events_txt = ''
                return
            if led.pending_clicks <= 0:
                return
            mism = _xp_compare(led, display, level_obs)
            clicks = led.pending_clicks
            events = led.events_txt
            led.pending_clicks = 0
            led.events_txt = ''
            if not mism:
                return
            obs_txt = ';'.join(f"{m['domain']}/{m['slot']} "
                               f"期望[{m['expected']}] 实读[{m['observed']}]"
                               for m in mism)
            cw_telemetry.record_defect(
                _XP_DEFECT_SURFACE, _XP_DEFECT_KIND,
                expected=(f'lv{led.level} xp {led.xp_cur}/{led.xp_next}'
                          f'(账本;events={events or "本段"})'),
                observed=(f'lv{level_obs} xp '
                          + (f'{display[0]}/{display[1]}' if display else '失读')
                          + (f';{obs_txt}' if obs_txt else '')),
                plane=key[0], round_num=key[1],
                gap_large=True,
                verdict=('留证-买经验后期望账本与显示读数不一致(零决策记账;'
                         '已知盲区=shop 席满急救盲击购买经验不经账,该形态为'
                         '预期留证;单次 L1,复现升 L0 由分级安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('pending_clicks', str(clicks)), ('events', events))],
                reader_source='xp_expect_reconcile',
                note='期望态层·经验:期望=锚点读数+购买意图纯函数推进'
                     '(XP_TO_NEXT_LEVEL 结转),与买牌/拖动通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] xp_expect reconcile skip: {e}')

    def _reconcile_faction_display(self, obs: PrepObservation) -> None:
        """备战稳定帧羁绊显示对账(cw_faction_obs 接线;零决策:不一致仅落
        缺陷台账,不纠漂不重读——羁绊状态以计算侧为主源,显示只作对账票)。

        computed 侧 = ``board_from_tracked``(session tracked_deployed,全集
        主源;None=含未知身份算不出 → 宁缺勿造跳过);显示侧 = 左侧羁绊面板
        OCR(cw_faction_obs.read_displayed_factions,只读可视条目)。截断/
        OCR 失读/残名按 cw_faction_obs 口径不评不判错,仅计数随 refs 披露;
        ``computed_missing`` 形态(compare 第四态)同为留证不判错,
        report_faction_reconcile 只转发 mismatch 行。节奏 = 与
        _reconcile_xp_expect 同款 heavy 定型帧消费,全程 best-effort。
        """
        try:
            session = self._session()
            if session is None:
                return
            computed = board_from_tracked(
                list(getattr(session, 'tracked_deployed', None) or []))
            if computed is None:
                return
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            reading = read_displayed_factions(self.ctx, frame)
            result = compare_factions(computed, reading.entries,
                                      reading.unreadable)
            st = obs.state
            plane = int(getattr(st, 'plane', 0) or 0)
            round_num = int(getattr(st, 'round_num', 0) or 0)
            if result.mismatch_count <= 0:
                # 不一致为零也留一条 debug(含不评口径计数),频率统计靠台账
                # 数据说话,不在此落账
                log.debug(f'[cw][director] faction_display reconcile: '
                          f'ok({len(result.rows)}行) '
                          f'ocr_skip={len(result.ocr_skipped)} '
                          f'trunc_suspect={len(result.truncation_suspects)} '
                          f'computed_missing='
                          f'{sum(1 for r in result.rows if r.verdict == "computed_missing")}')
                return
            refs = [
                {'field': 'ocr_skipped', 'value': ','.join(result.ocr_skipped)},
                {'field': 'unmatched', 'value': ','.join(reading.unmatched)},
                {'field': 'truncated', 'value': str(reading.truncated)},
                {'field': 'truncation_suspects',
                 'value': ','.join(result.truncation_suspects)},
                {'field': 'computed_missing',
                 'value': ','.join(r.faction for r in result.rows
                                   if r.verdict == 'computed_missing')},
            ]
            n = report_faction_reconcile(
                result, plane=plane, round_num=round_num,
                gap_large=True,
                verdict=('留证-羁绊面板显示计数与计算侧不一致(计算侧= tracked '
                         '全集主源,显示只作对账票;零决策记账不纠漂。已知不评:'
                         '面板底部截断/OCR 失读/残名/computed_missing 均只计数'
                         '不判错;单次 L1,复现升 L0 由分级安灯承接)'),
                refs=refs,
                reader_source='faction_display_reconcile',
            )
            log.debug(f'[cw-director] faction_display reconcile: '
                      f'{result.mismatch_count} mismatch → {n} 行台账')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] faction_display reconcile skip: {e}')

    def _reconcile_shop_pool(self, obs: PrepObservation) -> None:
        """商店打开 heavy 帧卡池一致性票(cw_shop_obs.check_shop_pool 接线;
        零决策:违例仅落缺陷台账,不 return/不重读不纠错)。

        帧 = obs.shop_open 且 state.shop 非空(shop 关态 read_shop_cards
        自带收起锚门返空,天然跳过;state.shop 即 read_game_state 内
        read_shop_cards 现读链,零新增 SIFT)。pool_state:无池追踪账
        (cw_state 只有我方 tracked 持有,池内剩余无人建账)→ 传 None =
        只查 tier 门,池守恒查如实降级(W556 口径),refs 披露。
        tier_locked = 该费用档在当前等级概率为 0(REFRESH_PROB 单一源)
        = 牌识别错或等级读错的强证据。节奏 = 与 _reconcile_xp_expect
        同款 heavy 定型帧消费,全程 best-effort。
        """
        try:
            st = obs.state
            if st is None or not obs.shop_open:
                return
            cards, unnamed = _shop_pool_inputs(st)
            if not cards:
                return
            violations = check_shop_pool(cards, int(st.level or 0), None)
            if not violations:
                return
            obs_txt = ';'.join(f'{v.name}/{v.cost}:{v.kind}({v.detail})'
                               for v in violations)
            cw_telemetry.record_defect(
                _SHOP_DEFECT_SURFACE, _SHOP_POOL_DEFECT_KIND,
                expected='0 违例(五牌两查)',
                observed=obs_txt,
                plane=int(getattr(st, 'plane', 0) or 0),
                round_num=int(getattr(st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-商店牌卡池一致性违例(tier_locked=该费用档本'
                         '等级概率为0,牌识别错或等级读错;invalid_cost=费用'
                         'OCR误读。pool_state 无账本传 None,池守恒查如实'
                         '降级未做;零决策记账,单次 L1,复现升 L0 由分级'
                         '安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('level', str(int(st.level or 0))),
                    ('cards', str(len(cards))),
                    ('unnamed', str(unnamed)),
                    ('pool_state', 'None(池查降级)'))],
                reader_source='shop_pool_reconcile',
                note='期望态层·商店:违例票=cw_shop_obs.check_shop_pool'
                     ' 纯函数(REFRESH_PROB/POOL_COPIES_PER_CARD 单一源),'
                     '与买牌/经验/羁绊通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] shop_pool reconcile skip: {e}')

    def _reconcile_merge_preview(self, obs: PrepObservation) -> None:
        """商店打开 heavy 帧合成预览交叉验证(cw_shop_obs.compare_merge_preview
        接线,与 _reconcile_shop_pool 同族同帧;零决策:mismatch 仅落缺陷台账,
        不 return/不重读不纠错)。

        帧 = obs.shop_open 且 state.shop 非空(与卡池票同门)。our =
        ``_merge_preview_inputs`` 按同名同星持有折算;det = 商店快照逐牌
        merge_preview>0(reader = cw_identity_obs.read_merge_preview,已
        在产线;激活依据 = W600 批B 评估:136 组同刻重复读数 0 分歧/15
        非零事件 8 例精确相符)。our_suspect/game_extra 均开票留证——
        our_suspect = 我方合成计算嫌疑(单向罚则唯一对象),game_extra =
        我方漏算(不判罚只计数);our_suspect 祇当「持有 ≥1 副本但同刻
        重复读数恒 0」的系统性形态才是暗相漏检证据(回退采帧解锁条件见
        W600 报告),单票不判死。节奏 = 同款 heavy 定型帧消费,best-effort。
        """
        try:
            st = obs.state
            if st is None or not obs.shop_open:
                return
            our, det, unnamed = _merge_preview_inputs(st)
            if not our:
                return
            result = compare_merge_preview(our, det)
            mism = [r for r in result.rows if r.verdict != 'match']
            if not mism:
                return
            obs_txt = ';'.join(
                f'slot{r.slot}:{r.verdict}(our={r.our} det={r.detected})'
                for r in mism)
            cw_telemetry.record_defect(
                _SHOP_DEFECT_SURFACE, _SHOP_MERGE_DEFECT_KIND,
                expected='0 mismatch(合成预览=我方同名同星持有>0 vs 识别✦>0)',
                observed=obs_txt,
                plane=int(getattr(st, 'plane', 0) or 0),
                round_num=int(getattr(st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-商店牌合成预览对账不一致(our_suspect=我方算'
                         '有副本而识别无✦=合成计算嫌疑或识别暗相漏检,双义'
                         '不逐票判死;game_extra=识别有✦而我方无账=漏算'
                         '留证不判罚。merge_preview 读 0 双义=真无副本∨'
                         'fail-silent 读不到;零决策记账,单次 L1,复现升'
                         'L0 由分级安灯承接)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('slots', str(len(our))),
                    ('unnamed', str(unnamed)),
                    ('our_suspect', ','.join(str(r.slot) for r in mism
                                             if r.verdict == 'our_suspect')),
                    ('game_extra', ','.join(str(r.slot) for r in mism
                                            if r.verdict == 'game_extra')),
                    ('reader', 'shop.merge_preview(已产线)'))],
                reader_source='merge_preview_reconcile',
                note='期望态层·商店:对账票=cw_shop_obs.compare_merge_preview'
                     ' 纯函数(单向验证,合成主源=我方计算),与卡池票同帧'
                     '分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] merge_preview reconcile skip: {e}')

    # ===== 装备期望态对账(W543;纯记账+对账,零决策行为变更)=====
    # 语义单一源 = docs/game/currency_war/research/equipment_mechanics.md §1.1
    # (两件简易必合成无共存 28/28 配方实证 / 角色装备上限 3 件 / 合成落点 =
    # 角色最左简易槽 / 装备不堆叠每格一件 / 卖角色=装备全量回装备区;
    # 唯一件=待确认项,本批不建模)。合成规则单一源 = cw_synthesis
    # (synthesize_target/self_advance,图谱派生自注册表,勿自造第二套)。
    # 架构与买牌(W536)/拖动(W530)/经验(W552)通道同构:动作意图 →
    # 期望增量(纯函数)→ heavy 定型帧实读(read_equip_grid 逐格三态)比对
    # → 不一致落缺陷台账;一致/不可评不打扰。遮挡格按三态如实跳过
    # (不评不算错);穿戴侧(read_equipped_below)精度未验证,按不评口径
    # (失读/空读一律不建期望,宁缺勿造)。

    def _equip_expect_for_sell(self, action: SellDeployed) -> EquipExpect | None:
        """卖上阵角色 → 「装备全量回装备区」期望(equipment_mechanics §1.1)。

        已穿装备读 = read_equipped_below(below-avatar TM;精度未验证——
        按不评口径:空读/失读/坐标缺失一律 None 不评,不发明期望);
        装备区 before 快照 = 同帧 read_equip_grid 非遮挡占用计数(遮挡格
        进快照会污染 after 对账基准 → 有遮挡即不评)。全程 best-effort。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return None
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout,
            )
            from sr_od.application.currency_war.obs.cw_equipment import (
                ensure_equip_sift_templates,
                ensure_equip_tm_templates,
                read_equip_grid,
                read_equipped_below,
            )
            grays = ensure_equip_tm_templates(self.ctx)
            templates = ensure_equip_sift_templates(self.ctx)
            if grays is None or templates is None:
                return None
            if action.row == 'front':
                prefix, n = '前排', 4
            else:
                n, prefix = select_back_layout(self.ctx, frame)
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                _ctx_slots,
                avatar_to_below,
            )
            rect = next((r for i, r in _ctx_slots(self.ctx, prefix, n)
                         if i == action.slot), None)
            if rect is None:
                return None
            equipped = read_equipped_below(
                frame, grays, [(action.slot, avatar_to_below(rect))]
            ).get(action.slot, [])
            if not equipped:
                return None   # 未穿/穿戴读失读:无可评增量,不评
            cells = read_equip_grid(frame, templates)
            if any(c.occluded for c in cells):
                return None   # before 快照被遮挡污染 → 不评
            before: dict[str, int] = {}
            for c in cells:
                if c.name is not None:
                    before[c.name] = before.get(c.name, 0) + 1
            return compute_equip_drag_expect(
                EquipDragIntent(kind='sell_char', source_name='',
                                equipped_names=tuple(sorted(equipped))), before)
        except Exception:   # noqa: BLE001  期望构建 best-effort,不阻塞环
            return None

    def _reconcile_equip_expect(self, expect: EquipExpect) -> None:
        """装备期望态对账(heavy 定型帧消费;零决策:不一致仅落缺陷台账,
        不 return/不重拖)。读法 = read_equip_grid 纯读逐格分类(三态),
        复用本轮 heavy 定型帧(last_screenshot,零新增截屏)。全程 best-effort。
        """
        try:
            frame = getattr(self, 'last_screenshot', None)
            if frame is None:
                return
            from sr_od.application.currency_war.obs.cw_equipment import (
                ensure_equip_sift_templates,
                read_equip_grid,
            )
            templates = ensure_equip_sift_templates(self.ctx)
            if templates is None:
                return
            cells = read_equip_grid(frame, templates)
            mism = compare_equip_expect(expect, cells)
            if not mism:
                return
            obs_st = self._cached_state
            obs_txt = ';'.join(f"{m['slot']} 期望[{m['expected']}] "
                               f"实读[{m['observed']}]" for m in mism)
            cw_telemetry.record_defect(
                _EQUIP_DEFECT_SURFACE, _EQUIP_DEFECT_KIND,
                expected=f'equip {expect.summary}',
                observed=obs_txt,
                plane=int(getattr(obs_st, 'plane', 0) or 0),
                round_num=int(getattr(obs_st, 'round_num', 0) or 0),
                gap_large=True,
                verdict=('留证-装备拖拽期望态与装备区实读不一致(遮挡格不评;'
                         '穿戴读精度未验证按不评口径;equip=中决策相关面,'
                         '单次 L2 初判,复现升 L1;本对账零决策行为,'
                         '不 return/不重拖)'),
                refs=[{'field': k, 'value': v} for k, v in (
                    ('kind', expect.kind), ('summary', expect.summary),
                    ('product', expect.product),
                    ('deltas', ';'.join(f'{k}:{v:+d}'
                                        for k, v in expect.deltas.items())))],
                reader_source='equip_expect_reconcile',
                note='期望态层·装备:期望=拖拽意图纯函数(equipment_mechanics '
                     '§1.1;合成单一源 cw_synthesis),与买牌/拖动/经验通道分立')
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] equip_expect reconcile skip: {e}')

    def _session(self):
        match = getattr(self.ctx, 'cw_match', None)
        return match.session if (match is not None and match.session is not None) else None

    def _match(self):
        return getattr(self.ctx, 'cw_match', None)

    # ===== 环主体(F1 单步契约;抽普通方法便于离线 mock 测,run 只做入口)=====

    @operation_node(name='备战决策环', is_start_node=True, node_max_retry_times=6)
    def run(self) -> OperationRoundResult:
        match = self._match()
        if match is None or match.strategy is None:
            return self.round_fail(status='无 cw_match(对局未初始化)')
        # 环入口:环级计数清零(§4.2b/§7;局级 bail_reason_counts 不清)
        session = match.session
        session.defer_count = 0
        session.prep_phase = 0
        # r366b(review A1 修,实证驱动):free_bench_gold_wait **不在环入口清**——
        # 局47 死循环实际路径 = run() 环入口 bench-full 分支 round_wait 后外环
        # 重派 Director 重入 run()(每次重入环入口清零 → 计数永不到 2 →
        # EnsureShopOpen 无限重发,修复失效)。改:**警告解除时清**(下方
        # read_bench_full False 分支)——警告持续期间计数跨 run() 重入存活。
        session.prep_phase_retry = 0
        self._executor = PrepActionExecutor(self, self.ctx)
        self._steps = 0
        self._stall = 0
        self._fail_counts = {}
        self._blocked = set()
        self._recovered = set()
        self._recovery_closed_known = {}
        self._recovery_tried = False
        self._cached_state = None
        self._cached_bench = []
        self._cached_deployed = []
        self._cached_vacancy = 0
        self._cached_gold_trusted = False
        self._spend_unit_seq = 0   # W494:购买单元序按局重置
        self._unit_meta = None
        self._exec_fail_hook_fired = False
        # r297(P0③):_probe_node_type 迁至 EnsureShopClosed 后
        #(原 run() 入口调用已删;曾同挂点的 _probe_node_reward
        # 采集钩子 W284 判读完成后曾删,W307 按 r314 原样重挂)。
        return self._run_loop(match)

    def _clear_entry_overlays(self) -> None:
        """P0 清场前置段(规范入口序列「先清场、再识别、后动作」;ADR-0462):
        环入口先逐屏探可一键关闭的 overlay(注册表 = ``cw_observation_gate.
        ENTRY_OVERLAY_CLOSE``,锚判定走现有 screen 体系),命中即点其关闭按钮,
        拿干净备战画面再进 gate/全量识别——识别与 overlay 状态交织是死读与
        冲突噪声的共同根。只收「无决策语义的弹窗/面板」;投资环境/策略等
        交互 overlay 有专属 handler,关闭即丢决策内容,不进注册表、仍走既有
        event_overlay bail → 外环消化路径。fail-open:截图/识别/点击任一异常
        静默返回(=现行为,gate 的帧态门继续兜底)。"""
        from one_dragon.base.screen import screen_utils
        from sr_od.application.currency_war.obs.cw_observation_gate import (
            ENTRY_OVERLAY_CLEAR_ROUNDS,
            ENTRY_OVERLAY_CLOSE,
            ENTRY_OVERLAY_SETTLE_S,
        )
        for _ in range(ENTRY_OVERLAY_CLEAR_ROUNDS):
            try:
                frame = self.screenshot()
            except Exception:   # noqa: BLE001  离线契约
                return
            _hit = None
            for _name in ENTRY_OVERLAY_CLOSE:
                try:
                    if screen_utils.get_match_screen_name(
                            ctx=self.ctx, screen=frame,
                            screen_name_list=[_name],
                            crop_first=False) is not None:
                        _hit = _name
                        break
                except Exception:   # noqa: BLE001  离线契约
                    return
            if _hit is None:
                return
            _area = ENTRY_OVERLAY_CLOSE[_hit]
            log.info(f'[cw][director] P0 清场:{_hit} 在场 → 点 {_area}')
            try:
                self.round_by_find_and_click_area(
                    frame, _hit, _area, success_wait=0.5)
            except Exception:   # noqa: BLE001  离线契约
                return
            time.sleep(ENTRY_OVERLAY_SETTLE_S)

    def _try_collapse_open_shop(self) -> bool:
        """环入口遇开商店稳定态(战斗胜利后新回合游戏可能自动开)→
        收起返回 True;非开态(真特效/overlay)返回 False。

        两个调用方:① 环入口 gate 前的预收(主路径:开 → 收起后
        以收紧超时等关店态 stable,直接进本轮,不再 round_retry;
        见 _run_loop 环入口注释;首探 miss 后环入口会在有限窗内
        重试本探针,覆盖「自动开商店晚于首探」的时序竞争);② gate
        超时后的容忍探测(兜底:收起 + round_retry 重进,r346 语义
        保留)。

        HP/gold 读取语义本要求关态(shop.py 同款收起逻辑)。
        离线契约:探测/点击异常 → False(放行,等价旧探针 except
        break;不让容忍路径把离线 mock 测试炸掉)。
        """
        try:
            _sc = self.screenshot()
            if not self.round_by_find_area(
                    _sc, SHOP_SCREEN_NAME, '按钮-收起',
                    crop_first=False).is_success:
                return False
            log.info('[cw][director] 环入口开商店态(合法态非特效)→ 收起')
            self.round_by_find_and_click_area(
                _sc, SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
            return True
        except Exception:   # noqa: BLE001  离线契约
            return False

    def _run_loop(self, match) -> OperationRoundResult:
        """环循环主体(可离线 mock 测):observe → decide → execute → 再 observe。"""
        session = match.session
        from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        # ⚠️ 特效消化等待(用户 2026-08-16 实证):上一步动作(drag 上场/买卡合成)会触发羁绊
        # 特效/升星 overlay(盛会之星/圣杯/银狼升级等)遮挡画面 —— heavy 观察(SIFT/OCR)在特效
        # 帧读 = 污染。环入口先截一帧探「备战标识」,miss(被特效遮)→ 等 1s 重试,最多 3 次
        # 让特效播完再观察(非交互 overlay 播完即走;交互型由下方 event_overlay 检测 bail)。
        # 探针 best-effort(截图/识别异常不阻塞 —— 离线 mock 测试无真画面)。
        # r297(审查 P0①:单锚过弱实锤 16:42:35 deployed 6人读成
        # 1人——「购买经验」按钮在 shop 开/关两态均可见,特效
        # 盖舞台不盖底部按钮时门照样放行;全日志消化门 0 触发
        # 而污染证据 370+682 次):①锚改「备战屏(shop 关)专属
        # 的舞台锚(按钮-出战)」——shop 开态帧不再放行(该帧
        # SIFT 本就不可信);②探 3 次仍不 clean 也**不再
        # fall-through 盲 observe**,bail 重试(外环重进消化)。
        # r347(旧路径删除,用户定调「几个节点没问题后删」):对拍
        # 验证已过(局38 r1-r3 新路径 3 节点干净+path=old 恒 0),
        # gate_director 无条件化——删 flag 分支与旧 3 探针循环。
        # ⚠️ 特效消化等待(用户 2026-08-16 实证)语义保留:gate 的
        # 时间稳定窗就是消化门;离线契约(截图异常 raise)=放行
        # _observe(None→自截图,行为同旧探针 except break)。
        # r310(ADR-0213 批次1)原接线说明:gate_director flag on 时
        # 走 wait_stable_frame;off 保持旧路径(对拍期)——对拍期
        # 已结束,r347 起只有新路径。
        # r346:开商店容忍路径(gate 超时先探合法开态,收起重进;
        # 真特效/overlay 才 bail 3-strike)。
        _gate_frame = None
        _gate_err = False
        # P0 清场前置段(ADR-0462「先清场、再识别、后动作」):先把可一键
        # 关闭的 overlay/弹窗清掉,再等关店态 stable 做全量识别——清场失败
        # 不阻塞(后续 gate/容忍探测/bail 链照旧兜底)。
        self._clear_entry_overlays()
        try:
            from sr_od.application.currency_war.obs.cw_observation_gate import (
                GATE_POST_COLLAPSE_TIMEOUT_S,
                PROFILE_CLOSED,
                wait_stable_frame,
            )
            log.info('[cw][gate] path=new(director 环入口)')
            # 战后首环开店态预收:战斗胜利后新回合游戏常自动开商店,
            # 此时直接等关店态锚(PROFILE_CLOSED)永不命中,旧路径每轮
            # 必打满 12s 超时才走「收起重进」(实机单局 16 轮 × ~12s
            # 纯等;依据实机单局耗时深挖报告
            # .debug/temp/currency_war/w358_time_depth/REPORT.md
            # 可压缩清单 #1)。修:入口先探开商店态——开 → 收起后以
            # 收紧超时(GATE_POST_COLLAPSE_TIMEOUT_S,实测收起后 ~2s
            # 即关店态 stable)直接等本轮 gate 帧,省掉超时 + 重进往返;
            # 未开(含特效帧/新位面首环)走原 12s 完整门,行为不变。
            # ADR-0264 终裁:环入口(节点结束段/battle 后新备战相位)
            # 走融合默认路径——锚命中即进指纹快 poll(骨架加速器①,
            # 不做纯信任放行),指纹双轮窗真实测量。
            # 未开(含特效帧/新位面首环)走原 12s 完整门,行为不变。
            # 时序竞争修复(预收探针重试):自动开商店可能发生在首探
            # **之后**(探不到「按钮-收起」≠ 本轮不会开)——首探 miss
            # 不立即进完整门,先在有限窗内按 PRECOLLAPSE_RETRY_S 间隔
            # 重试同一探针(同原语,不新增判据);任一次探到开 → 走
            # 上方收紧超时路径,省掉 12s 死等+重进往返(实机每局
            # 9-25 次,依据 .debug/temp/currency_war/w417_duration_audit/
            # REPORT.md「确定可压」第 1 条);窗内未开 → 原完整门,
            # 行为不变(重试上限防无界等待)。
            _collapsed = self._try_collapse_open_shop()
            if not _collapsed:
                for _ in range(PRECOLLAPSE_RETRIES):
                    time.sleep(PRECOLLAPSE_RETRY_S)
                    if self._try_collapse_open_shop():
                        _collapsed = True
                        break
            if _collapsed:
                _gate_frame = wait_stable_frame(
                    self, profile=PROFILE_CLOSED,
                    timeout_s=GATE_POST_COLLAPSE_TIMEOUT_S)
            else:
                _gate_frame = wait_stable_frame(
                    self, profile=PROFILE_CLOSED)
        except Exception:   # noqa: BLE001  离线契约:放行(observe 自截图)
            _gate_err = True   # 异常≠超时:超时走容忍探测,异常直接放行
            log.debug('[cw][gate] 环入口 gate 异常(离线契约)→ 放行')
        if _gate_frame is None and not _gate_err:
            # 预收后的收紧超时未达成 stable(收起动画偶发拖长)→ 有界
            # 兜底:落回原 12s 完整门;仍未达成才进下方容忍探测
            # (收起探针/3-strike bail)——不引入无界等待。
            try:
                _gate_frame = wait_stable_frame(
                    self, profile=PROFILE_CLOSED)
            except Exception:   # noqa: BLE001  离线契约:放行
                _gate_err = True
                log.debug('[cw][gate] 环入口兜底 gate 异常(离线契约)→ 放行')
        if _gate_frame is None and not _gate_err:
            # r346:先探开商店态(合法稳定态,收起重进);非开态才是
            # 真特效/overlay → bail 交外环(3-strike 聚合)。
            if self._try_collapse_open_shop():
                return self.round_retry('环入口商店开,已收起重进')
            return self._bail(match, '环入口帧不clean(特效/overlay未消化)')
        # r344:gate 末帧透传 _observe——OCR 缓存贯穿(gate 全图
        # OCR 一次,observe 的 id_mark 判定/observe_full 全命中),
        # 且观察对象=已验证稳定帧;旧路径(gate off/异常)None=
        # _observe 自截图,行为不变。
        obs = self._observe(heavy=True, screen=_gate_frame)   # 环入口重观察 + 对账
        if obs.event_overlay is not None:   # 事件 overlay 挡操作 → 环让位(交外环 handler)
            return self._bail(match, f'事件overlay:{obs.event_overlay}')
        # r287→r292:钩子挂点迁至 EnsureShopClosed 执行成功后
        #(见 _run_loop while 内;此处保留说明,原调用已删)。
        # ADR-0136(M16 死循环 86min 根因):「备战席已满」警告模态下游戏**拒绝一切拖拽/出战** ——
        # Director 若无视警告继续发 DeployMove/StartBattle,全部"源槽未变/未落地"连环失败 → stall
        # 死循环。环入口感知警告(read_bench_full)→ 立即走腾席链破警告(优先升级扩容;点不起 → 卖最弱),
        # 警告解除后才继续常规决策。每次环入口重判(警告可反复出现)。
        from sr_od.application.currency_war.obs.cw_observation import read_bench_full
        _scr_full = getattr(self, 'last_screenshot', None)
        _bench_full_now = (_scr_full is not None
                           and read_bench_full(self.ctx, _scr_full))
        if not _bench_full_now:
            # r366b(review A1):警告解除 → 等待计数清零(正常态恢复预算)
            if getattr(session, 'free_bench_gold_wait', 0):
                session.free_bench_gold_wait = 0
        if _bench_full_now:
            log.warning('[cw!][director] 备战席已满警告(模态挡拖拽/出战)→ 破警告优先(腾席链)')
            # r2 review#1(P0):曾用 type() 造假 obs(缺 tomes 等字段)→ 策略一读即 AttributeError
            # 炸环。改 dataclasses.replace 从真 obs 派生(全字段保真,仅覆写腾席相关)。
            import dataclasses
            bf_obs = dataclasses.replace(
                obs, box_overlay_open=False, boxes=[], spheres=[],
                free_bench_slots=0, shop_open=False,
                # ADR-0136 补修:横幅在时拖放被游戏拒 → vacancy 置 0 强制走 b(升级)/c(卖最弱)
                deploy_vacancy=0)
            action = match.strategy.decide_prep_action(bf_obs, session, config)
            progressed, detail = self._executor.execute(action)
            log.info(f'[cw][director] 破警告动作 {type(action).__name__} → {"✓" if progressed else "✗"} {detail}')
            # r11 review #2(盲节点可观测性):破墙路径此前零遥测——M55 r3 的 59 金+双跳级全发生在
            # decisions.jsonl 外(复盘盲区)。破墙动作也记一条(类名带 BenchFull 前缀,审计可辨)。
            # r1 review#4:曾传 type() 造假对象(非 dataclass)→ serialize_action TypeError 被吞
            # → 破墙遥测从未落盘。改 exec_events 通道(本就为执行事件设计)。
            try:
                from sr_od.application.currency_war.telemetry import cw_telemetry

                if obs.state is not None:
                    _bf_rid = cw_telemetry.current_run_id() or '-'
                    if _bf_rid == '-' and self.ctx.cw_match is not None:
                        _bf_rid = f'match:{id(self.ctx.cw_match) & 0xffff:x}'   # 与 _record_exec_obs 兜底一致
                    # r98 类型 gate 抓真 bug:record_exec_event 是 TelemetryRecorder 类方法,
                    # 模块级直调 = AttributeError(此前被 except 吞 → 破墙遥测从未落盘)。
                    cw_telemetry.get_recorder().record_exec_event(
                        run_id=_bf_rid,
                        round_num=obs.state.round_num,
                        action_family=f'BenchFull_{type(action).__name__}',
                        screen='battle_prep', event='bench_full_break',
                        reason='备战席满破墙')
            except Exception:   # noqa: BLE001  遥测 best-effort
                pass
            return self.round_wait(status=f'备战席已满,已试破警告({type(action).__name__})', wait=1.0)
        # MED-4:战略层 update_target 环入口调一次(strategy/03(原 doc 15§6);RunBuyPhase 内 shop.py:166 仍会
        # 调 = P1 允许的双调)。失败不炸环(沿用上轮 target 继续步级决策)。
        # ⚖️ r68 review:**入口先过 HP 新鲜度门再调**(cw_strategy.gated_hp,与 shop.py 同门)——
        # 旧版 obs.state.hp 常是 shop 开态 100 兜底 → maybe_pivot 在假 hp 上做信号1涌现判定,
        # 10s 后 shop 侧真 hp 又触发信号3保命反向换线(r68 实证:hp=100 转红A → hp=26 转DOT队,
        # 同节点两次方向相反 pivot = comp churn 主燃料)。
        if obs.state is not None:
            from sr_od.application.currency_war.cw_strategy import gated_hp
            from sr_od.application.currency_war.decision_v2.prep_brain import (
                committed_from,
                drive_intention,
            )
            _os = obs.state
            # 批 2 方向层接管(P7 驱动点契约):意向状态机每 game-round 恰
            # 一次,锚定 = 环入口(update_target 之前);段级重入守卫 =
            # v3_intention_key(与 decision_v2 栈共享键面,双驱动幂等)。
            # registry 缺省 = DEFAULT_REGISTRY(缺省栈无注入臂;A/B 注入
            # 经策略构造 registry 透传,P6 契约)。
            try:
                drive_intention(_os, session)
            except Exception as e:  # noqa: BLE001  方向驱动失败不阻塞步级决策
                log.warning(f'[cw!][director] 意向驱动异常(沿用旧方向): {e}')
            # r73 RC3:dual 态拷回(读端 = R1 唯一合法读端 committed_from;
            # 批 2 起读端内部 = cw_intention 权威派生,消费端同 commit 面
            # 换源,session 侧双轨字段已无读点)
            _os.dual_track_phase = not committed_from(session, _os)
            _os_t = ((_os.plane - 1) * 9 + _os.round_num) if (_os.plane and _os.round_num) else None
            _os.hp = gated_hp(_os.hp, session, _os_t,
                              current_readable=bool(getattr(_os, 'hp_readable', True)))
        try:
            match.strategy.update_target(obs.state or GameState(), session, config)
        except Exception as e:  # noqa: BLE001  战略层失败不阻塞步级决策
            log.warning(f'[cw!][director] update_target 异常(沿用旧 target): {e}')
        # W620 批 1(蓝图 §7 批 1 行):DirectorV2 接线升正——新环 = 唯一
        # 生产路径(无开关 directive,`director_v2_prep_enabled` 已删;回退
        # = git revert)。共享前置(gate/bench-full 破警告/gated_hp/
        # update_target)全在此前,新旧环共用零重写。
        return self._run_prep_loop_v2(match, session, config)

        # ---- 旧环主体(生产不再可达;保留至批 3 退役,蓝图 §5 批 1 行
        # 「旧 prep_director 并行一窗口后退役」。期间仅离线/影子对照复用)----
        while True:
            # ⚖️ W209j 刹车语义(run 27 停机事故第三层实证,ADR-0388):停机标志
            # 设置后本循环曾继续发 StartBattle——14:09:08 Deploy 钩子 stop_running
            # → 14:09:14「出战成功」(log 32489/32504/32514),CW 备战不自动出战,
            # 出战必是 bot 点的 = **停 bot 后执行流仍在落地动作**。环顶每步先查
            # 「运行中被停」(last_run_result 非空——run_state STOP 是 idle 初始态,
            # 不能直接用;last_run_result 在 start_running 清 None/stop 时写入,
            # 是「本次运行被请求停止」的精确判据),已停 → 立即收口不再发任何
            # 动作。同族钩子(star/summon/shop_unknown/battle_unknown 等)经本
            # 循环的全部受益;op 层直连循环(battle_loop 等)各自节点自查。
            _rc = getattr(self.ctx, 'run_context', None)
            if _rc is not None and getattr(_rc, 'last_run_result', None) is not None:
                log.info('[cw][director] 停机标志已设 → 环收口(不再执行动作,'
                         'W209j 刹车语义)')
                return self.round_fail(status='已停止[hook]')
            self._steps += 1
            if self._steps > PrepDirector.MAX_STEPS:
                log.warning(f'[cw!][director] 步数>{PrepDirector.MAX_STEPS} → 强制出战(F5)')
                return self._force_battle('步数预算耗尽')
            try:
                action = match.strategy.decide_prep_action(obs, session, config)
            except Exception as e:  # noqa: BLE001  策略异常:上抛 = 本环 fail(§13.2 路径 3)
                log.warning(f'[cw!][director] decide_prep_action 异常: {e}')
                return self.round_fail(status=f'策略决策异常: {e}')
            if not isinstance(action, PrepAction):
                log.warning(f'[cw!][director] 策略输出非 PrepAction: {type(action).__name__}')
                return self.round_fail(status='策略输出非 PrepAction(F3)')
            self._record_step(obs, action)
            # W606 影子比对(协议门1;开关默认关):旧环当权后同帧影子
            # 决策逐位对照。全隔离——影子路径任何异常只计数留证,绝不
            # 影响本步动作与现役决策(adapter.shadow_compare_step 承诺)。
            from sr_od.application.currency_war.decision_v2.adapter import (
                shadow_compare_enabled,
                shadow_compare_step,
            )
            if shadow_compare_enabled(match.strategy):
                shadow_compare_step(self, match, obs, session, config, action)

            # —— 控制流(不走 execute 验证链,§4.2b)——
            if isinstance(action, DeferSpheres):
                session.defer_count += 1
                log.info(f'[cw][director] DeferSpheres(defer={session.defer_count})')
                obs = self._observe(heavy=False)
                continue
            if isinstance(action, BailToOuter):
                return self._bail(match, action.reason or '未注明')

            # —— F3 校验(全集白名单 + 参数;非法:拒绝执行 + stall + 遥测,§13.2 路径 2)——
            err = self._executor.validate(action)
            key = action_key(action)
            if err is not None:
                log.warning(f'[cw!][director] 参数非法 {key}: {err} → 拒绝 + 计 stall')
                self._stall += 1
                gate = self._stall_gate()   # MED-3:拒绝路径也要兜 stall 门(防 55 步空转)
                if gate is not None:
                    return gate
                obs = self._observe(heavy=False)
                continue
            # 屏蔽命中:拒绝执行 + stall + 遥测(策略确定性重提案同动作被拒,M-5)
            if key in self._blocked and not isinstance(action, StartBattle):
                log.warning(f'[cw!][director] 动作已屏蔽 {key} → 拒绝 + 计 stall(M-5)')
                self._stall += 1
                gate = self._stall_gate()   # MED-3:同上
                if gate is not None:
                    return gate
                obs = self._observe(heavy=False)
                continue

            # —— 执行(验证失败路径:计 fail;异常自然上抛 = 本环 fail)——
            # W494:RunBuyPhase = 一个购买单元(开店→买/升/刷→关店),执行边界
            # 记账(纯观测);失败/异常同样关单元,判定门在读端(boundary)。
            _unit_open = isinstance(action, RunBuyPhase)
            if _unit_open:
                self._spend_unit_open(obs)
            # W512(观测自检设计 §2.3/§5-B5 动作级板面对拍,前读):部署/卖出
            # 执行前读一帧 paddle X(read_deployed_count 区域 OCR,毫秒级;部署
            # 动作本身秒级,占比可忽略)。后读复用下方 heavy 重观察帧,零新增
            # 截图。仅 DeployMove(期望 +1)/ SellDeployed(期望 −1);其余动作
            # 不进对拍。
            _dep_delta = 0
            _dep_pre: int | None = None
            # 期望态层(动作发出点):拖动动作从意图导出期望态增量(纯函数,
            # 架构原则②——期望态由发指令的同一条代码路径计算)。None=无法
            # 建真值(源槽身份未识别/同名占位语义未定义)→ 后续不评。
            _drag_expect = None
            if isinstance(action, (SellBench, DeployMove)):
                _drag_expect = compute_drag_expect(
                    action, obs.bench_chars, obs.deployed_chars)
            # 期望态层·装备(W543):卖上阵角色 = 已穿装备全量回装备区
            # (equipment_mechanics §1.1),期望在动作发出点从穿戴快照导出
            # (纯函数;失读/空读不评)。None=无法建真值 → 后续不评。
            _equip_expect = None
            if isinstance(action, SellDeployed):
                _equip_expect = self._equip_expect_for_sell(action)
            if isinstance(action, (DeployMove, SellDeployed)):
                _dep_delta = 1 if isinstance(action, DeployMove) else -1
                _dep_frame = getattr(self, 'last_screenshot', None)
                if _dep_frame is not None:
                    try:
                        _dep_pre = read_deployed_count(self.ctx, _dep_frame)
                    except Exception:   # noqa: BLE001  观测 best-effort
                        _dep_pre = None
            try:
                progressed, detail = self._executor.execute(action)
                if _unit_open:
                    self._spend_unit_close(progressed=progressed, detail=detail,
                                           boundary='closed' if progressed else 'failed')
            except Exception as e:  # noqa: BLE001
                if _unit_open:
                    self._spend_unit_close(progressed=False, detail=f'执行异常:{e}',
                                           boundary='aborted')
                log.warning(f'[cw!][director] 执行异常 {key}: {e} → 本环 fail')
                return self.round_fail(status=f'执行异常 {key}: {e}')
            log.info(f'[cw][director] step{self._steps} {key} → {"✓" if progressed else "✗"} {detail}')
            # 期望态层·经验(W552):购买经验意图 → 账本推进(零决策记账;
            # 仅 progressed 分支——执行失败=未购买,期望不适用)。
            if progressed and isinstance(action, LevelUp):
                self._xp_apply_levelup()
            elif progressed and isinstance(action, RunBuyPhase):
                self._xp_apply_buy_clicks(detail)

            # r292+P0③(r297):EnsureShopClosed 执行成功后=店确定关
            # 的可靠时点,**_probe_node_type 挂点**(审查 P0③:原挂
            # run() 入口一次性读,skip 69%——shop 开态帧读不了节点行,
            # 与已删 reward 钩子 r280-294 四次静默同病根)。
            # r314(ADR-0213 批次1)+r347(旧路径删除):前置
            # wait_stable_frame 无条件化(原 gate_hook flag 分支删;
            # 超时=放行——离线契约);2s 预估等待兼作操作段基线重置点
            # (ADR-0264 终裁加速器②)。
            # W284:曾同挂点的 _probe_node_reward 采集钩子(临时,
            # r280 用户交办)判读完成曾删整段——连胜四档表 + 基础奖励
            # 真值已固化(economy.md「基础奖励」行);W307 重挂采集
            # 1-3~1-8,经取证定谳挂点失活(关店已入 RunBuyPhase 内部,
            # EnsureShopClosed 路径零执行)且 1-6=5 封顶点已采,销案
            # 删整段(取证报告=.debug/temp/currency_war/w587_cw_reward_verdict/REPORT.md)。
            if 'EnsureShopClosed' in key and progressed:
                try:
                    from sr_od.application.currency_war.obs.cw_observation_gate import (
                        PROFILE_CLOSED,
                        wait_stable_frame,
                    )
                    log.info('[cw][gate] path=new(钩子前置)')
                    wait_stable_frame(
                        self, profile=PROFILE_CLOSED,
                        segment='op_settle')
                except Exception:   # noqa: BLE001  离线契约:放行
                    pass
                self._probe_node_type()

            if isinstance(action, StartBattle) and progressed:
                return self.round_success('出战(环出口)', wait=3)
            if progressed:
                self._stall = 0
                self._fail_counts.pop(key, None)
            else:
                try:
                    bail = self._on_verify_fail(match, action, key)
                except Exception as e:  # noqa: BLE001  LOW-5:恢复原语点击异常同执行异常路径
                    log.warning(f'[cw!][director] 失败处理/恢复原语异常 {key}: {e} → 本环 fail')
                    return self.round_fail(status=f'失败处理异常 {key}: {e}')
                if bail is not None:
                    return bail
            # 再观察:执行过的游戏动作一律 heavy(结构变化,review H-1);控制流走 light(上方)
            obs = self._observe(heavy=True)
            # W512(观测自检设计 §2.3/§5-B5 动作级板面对拍,后读):heavy 重观察帧
            # 上再读 paddle X,执行成功时期望 = 前读 ±1;不等 = 部署/卖出未生效
            #(点击落空/对账链双源都错)。纯留证零决策行为——与 deployed_align 的
            # 区别:那是跟踪表 vs paddle 的自动纠漂(裁决已自动恒 L2),本对拍是
            # 「动作声称的改变是否真发生」,不可自动纠,分级走 judge_severity
            #(关键面+计数差≥1,复现自动升 L0 初判;停机接线未启,仅落账标记)。
            # 任一端失读(None)= 无对拍基准,宁缺勿造跳过(paddle 既有语义)。
            if _dep_pre is not None:
                try:
                    _dep_post = read_deployed_count(self.ctx, self.last_screenshot)
                    if _dep_post is not None and _dep_post - _dep_pre != _dep_delta:
                        _gap = _dep_post - _dep_pre
                        cw_telemetry.record_defect(
                            'deployed', 'invariant_break',
                            expected=f'{key} 执行后 paddle={_dep_pre + _dep_delta}',
                            observed=f'paddle={_dep_post}',
                            plane=int(getattr(obs.state, 'plane', 0) or 0),
                            round_num=int(getattr(obs.state, 'round_num', 0) or 0),
                            gap=float(_gap), gap_large=True,
                            reader_source='paddle_action_audit',
                            note='部署/卖出动作级即时对拍(§2.3;与 deployed_align 自动纠漂分立)')
                except Exception:   # noqa: BLE001  观测 best-effort
                    pass
            # 期望态层(定型帧对账):动作完成且可建期望 → 在本轮 heavy 重观察
            # 定型帧上逐槽对账;不一致落缺陷台账(复现升 L0 由安灯承接),
            # 一致/不可评不打扰。仅 progressed 分支——验证失败=动作未发生,
            # 期望态不适用(该失败由 fail/恢复链管辖)。
            if progressed and _drag_expect is not None:
                self._reconcile_drag_expect(_drag_expect)
            _drag_expect = None
            # 期望态层·买牌(W536):RunBuyPhase 单元的购买期望由 shop.py 买入
            # 点写入 session.pending_buy_expect(StrategySession 正式字段,
            # 见 cw_strategy 字段定义);此处在本轮 heavy 定型帧上消费对账
            # (bench/buy_expect_mismatch)。零决策记账:不一致不重买不改
            # 行为;执行失败(未购买单元)期望作废只清不评。
            _pending_buy = session.pending_buy_expect
            if _pending_buy is not None:
                session.pending_buy_expect = None
                if progressed:
                    self._reconcile_buy_expect(_pending_buy)
            # 期望态层·经验(W552):同帧对账(锚定/轮界重锚/段内对账;
            # 内部 best-effort,异常不阻塞环)。
            self._reconcile_xp_expect(obs)
            # 羁绊显示对账(cw_faction_obs 接线):同帧消费——computed=tracked
            # 全集 vs 面板 OCR,mismatch 落缺陷台账(kind=faction_display_mismatch,
            # 零决策不纠漂;内部 best-effort)。
            self._reconcile_faction_display(obs)
            # 商店打开态对账(W564):同帧消费——商店打开 heavy 帧(腾席链
            # EnsureShopOpen 后)上五牌卡池一致性票(shop_pool_violation;
            # 零决策记账,内部 best-effort;关店帧自带锚门空跳)。
            self._reconcile_shop_pool(obs)
            # 合成预览对账(W601 激活,W600 批B 评估裁定):同帧消费——
            # compare_merge_preview 接线(merge_preview_mismatch;零决策
            # 记账,内部 best-effort;关店帧/无持有帧自带空跳)。
            self._reconcile_merge_preview(obs)
            # 期望态层·装备(W543):卖角色「装备全量回装备区」期望在本轮
            # heavy 定型帧上消费对账(equip/equip_expect_mismatch;零决策
            # 记账:不一致不重拖不改行为;不可评口径已在构建端丢弃)。
            if progressed and _equip_expect is not None:
                self._reconcile_equip_expect(_equip_expect)
            _equip_expect = None
            if obs.event_overlay is not None:   # 动作后浮出事件 overlay(mid-prep 弹出)→ bail
                return self._bail(match, f'事件overlay:{obs.event_overlay}')

    def _record_exec_obs(self, key: str, event: str, reason: str = '') -> None:
        """观测钩子(常驻,27 号能力画像):执行事件落 exec_events.jsonl。

        run_id 兜底:current_run_id → match 短 id。动作族:key 是动作 repr → 取首
        `(` 前类名;bail 类事件 key 是 reason 字符串 → 族归 'bail'。round_num 用
        游戏 轮次(r2#5:环步数重入清零且重复,与 decisions/outcomes 无法对齐;
        last_state.round_num 才是 join key)。best-effort。
        """
        try:
            from sr_od.application.currency_war.telemetry.cw_telemetry import (
                current_run_id,
                get_recorder,
            )
            run_id = current_run_id() or '-'
            game_round = 0
            _m = self.ctx.cw_match
            if _m is not None:
                run_id = run_id if run_id != '-' else f'match:{id(_m) & 0xffff:x}'
                _st = getattr(_m.session, 'last_state', None)
                if _st is not None:
                    game_round = getattr(_st, 'round_num', 0) or 0
            family = 'bail' if event == 'bail' else (
                key.split('(')[0].split(':')[0].strip() or '?')
            get_recorder().record_exec_event(
                run_id=run_id, round_num=game_round,
                action_family=family,
                screen='battle_prep', event=event, reason=reason or key,
                retry_count=self._fail_counts.get(key, 0))
        except Exception:   # noqa: BLE001  观测 best-effort
            pass

    # ===== 购买单元记账(W494 spend_ledger;纯观测,零行为变更)=====

    def _spend_unit_open(self, obs: PrepObservation) -> None:
        """开购买单元(RunBuyPhase 执行前):记时点与单元开时点 gold 观测。

        F2 语义:本时点商店关,gold 恒不可信——诚实记录不冒充真值,只作
        辅助对拍。plane/round 取 session.last_state(与 exec_events 同
        join 口径)。纯内存写,失败不影响环。
        """
        st = obs.state
        sess = self._session()
        ls = getattr(sess, 'last_state', None) if sess is not None else None
        self._spend_unit_seq += 1
        self._unit_meta = {
            'seq': self._spend_unit_seq,
            't0': time.monotonic(),
            'gold': getattr(st, 'gold', None) if st is not None else None,
            'gold_trusted': bool(obs.state_gold_trusted),
            'plane': int(getattr(ls, 'plane', 0) or 0),
            'round': int(getattr(ls, 'round_num', 0) or 0),
        }

    def _spend_unit_close(self, progressed: bool, detail: str = '',
                          boundary: str = 'closed') -> None:
        """关购买单元:框架事实落 spend_ledger.jsonl(best-effort)。

        boundary:closed=执行返回且进展 / failed=执行返回但未进展 /
        aborted=执行抛异常。plan 与金真值不在此复制——读端 join
        decisions/obs_conflicts(cw_telemetry.query_spend_ledger)。
        """
        meta = self._unit_meta
        self._unit_meta = None
        if meta is None:
            return
        try:
            from sr_od.application.currency_war.telemetry.cw_telemetry import (
                record_spend_unit,
            )
            record_spend_unit(
                plane=meta['plane'], round_num=meta['round'],
                unit_seq=meta['seq'], boundary=boundary,
                progressed=progressed,
                duration_s=time.monotonic() - meta['t0'],
                detail=detail or '',
                gold_before=meta['gold'],
                gold_before_trusted=meta['gold_trusted'])
        except Exception as e:  # noqa: BLE001  观测 best-effort,不阻塞环
            log.debug(f'[cw-director] spend_ledger skip: {e}')
        # [停机钩子·临时采证,安灯式;见模块头钩子段声明] 判定与记账同点:
        # 命中 mismatch → 哨兵(截图+flag)→ stop_running → 不再点击保画面。
        # 每局最多停一次;判定复用分类器,数据源与离线读端同一套
        #(shop 关店对拍的冲突行在本单元返回前已同步落盘 journal)。
        if not self._exec_fail_hook_fired:
            try:
                self._exec_fail_hook_check(meta, boundary)
            except Exception as e:  # noqa: BLE001  钩子 best-effort,不阻塞环收口
                log.debug(f'[cw-director] exec_fail hook skip: {e}')

    def _exec_fail_hook_check(self, meta: dict, boundary: str) -> None:
        """安灯判定+触发(内部方法;谓词与 flag 写入是模块级纯函数,离线可测)。

        数据源:decisions.jsonl 本轮 shop plan 行(plan/开店金,shop 开态可信)
        + obs_conflicts.jsonl 本轮 gold_delta 行(关店实读金,mismatch 形态下
        shop 审计必落行:金没动而计划花费>2 → gap>2)。任一缺失 = 分类器
        unknown = 不停(不猜)。
        """
        run_id = cw_telemetry.current_run_id()
        if not run_id:
            return
        replay_dir = cw_telemetry.get_recorder().replay_dir
        plan_row = cw_telemetry._shop_plan_rows(
            replay_dir, run_id).get((meta['plane'], meta['round']))
        if plan_row is None:
            return
        import datetime as _dt
        conf = cw_telemetry._match_conflict(
            cw_telemetry._read_conflict_gold_delta(replay_dir),
            meta['plane'], meta['round'],
            _dt.datetime.now().isoformat(timespec='seconds'))
        plan_actions = plan_row.get('actions') or []
        gold_open = plan_row.get('gold')
        gold_close = (conf or {}).get('new')
        # W577(ADR-0456):数据源补 spend_ledger 单元行的执行侧「计划≠尝试」
        # 字段(与 plan 行/gold_delta 行同一 replay join 面)——硬墙跳过/
        # 截断的单元分流 plan_truncated 豁免(局22 误停根因),不再被当
        # 「点击落空」误停。行缺失 → executed=None,退回 W494 原语义。
        unit_row = cw_telemetry._spend_unit_row(
            replay_dir, run_id, meta['plane'], meta['round'], meta['seq'])
        executed = None
        if unit_row is not None:
            executed = {
                'plan_truncated': unit_row.get('plan_truncated'),
                'refresh_attempted': unit_row.get('refresh_attempted'),
                'refresh_board_changed': unit_row.get('refresh_board_changed'),
            }
        if not exec_fail_should_stop(plan_actions, gold_open, gold_close,
                                     boundary=boundary, executed=executed):
            return
        self._exec_fail_hook_fired = True
        items = cw_telemetry.plan_gold_flow(plan_actions)['items']
        plan_summary = ';'.join(
            f"{i['type']}:{i['target']}:{i['cost']}" for i in items) or '(空plan)'
        shot_prefix = (f'exec_fail_{run_id}_p{meta["plane"]}'
                       f'r{meta["round"]}u{meta["seq"]}')
        import contextlib
        with contextlib.suppress(Exception):   # 截图失败不拦停机(flag 是主哨兵)
            self.save_screenshot(prefix=shot_prefix)
        write_exec_fail_flag(exec_fail_flag_path(),
                             run_id=run_id, plane=meta['plane'],
                             round_num=meta['round'], unit_seq=meta['seq'],
                             plan_summary=plan_summary,
                             gold_open=gold_open, gold_close=gold_close)
        log.warning('[cw!][director] 安灯:购买单元执行失败(计划花费>0 金差≈0)'
                    ' p%sr%s u%s → 停机留现场 flag=cw_exec_fail_hook.flag',
                    meta['plane'], meta['round'], meta['seq'])
        rc = getattr(self.ctx, 'run_context', None)
        if rc is not None:
            rc.stop_running(reason='hook:exec_fail_mismatch')

    def _stall_gate(self) -> OperationRoundResult | None:
        """环级强制出战门(§7 H-2b):stall≥5 且恢复已试尽 → 强制 StartBattle(F5)。

        MED-3:所有计 stall 的路径(验证失败/参数非法/屏蔽拒绝)统一走本门 —— 否则屏蔽后
        策略确定性重提案会 55 步空转到 MAX_STEPS 才兜住。
        """
        if self._stall >= PrepDirector.STALL_LIMIT and self._recovery_tried:
            log.warning(f'[cw!][director] stall≥{PrepDirector.STALL_LIMIT} 且恢复已试尽 → 强制出战(F5)')
            return self._force_battle('stall+恢复试尽')
        return None

    def _on_verify_fail(self, match, action: PrepAction, key: str) -> OperationRoundResult | None:
        """验证失败处理(review H-2 修订):连败 2 → 恢复原语(一次/实例)→ 仍连败 2 → 分型
        bail(关过已知弹层 = 弹层顽固)/屏蔽(无弹层 = 状态类失败)。返回非 None = 环终止。"""
        self._fail_counts[key] = self._fail_counts.get(key, 0) + 1
        fails = self._fail_counts[key]
        self._stall += 1
        # 观测钩子(常驻,27 号能力画像数据源):失败计数落盘(原来局终即弃)
        self._record_exec_obs(key, 'fail', f'fails={fails}')
        if fails >= PrepDirector.FAIL_TO_RECOVER and key not in self._recovered:
            # 首次连败门:恢复原语(一次/动作实例),重置计数给恢复后重试窗
            prim, closed_known = try_recovery(self, self.ctx)
            self._recovered.add(key)
            self._recovery_closed_known[key] = closed_known
            self._recovery_tried = True
            log.info(f'[cw][director] {key} 连败{fails} → 恢复原语({prim}),重试窗开启')
            time.sleep(1.0)
            self._fail_counts[key] = 0
            return None
        if fails >= PrepDirector.FAIL_TO_RECOVER and key in self._recovered:
            # 恢复后仍连败(恢复无效)→ 分型(§7 优先级条落地语义,ADR-0123):
            # 关过已知弹层仍败 = 弹层顽固/未知 → 环让位(bail 交外环弹层分支/停机钩子);
            # 无已知弹层(兜底点空白)仍败 = 状态/识别类失败 → 本环屏蔽(策略换路)。
            # ClickSpheres 特判(live M12 二停):假球点击打开的道具详情弹层被恢复关掉 →
            # closed_known=True 误走 bail 分支 ×3 停机。收球的恢复无效本质是识别类失败(假球),
            # 一律走 shield+defer(那个"弹层"是我们自己点出来的,非阻塞弹层)。
            if self._recovery_closed_known.get(key, False) and not isinstance(action, ClickSpheres):
                log.warning(f'[cw!][director] {key} 恢复(关弹层)后仍连败 → BailToOuter(弹层顽固)')
                return self._bail(match, f'恢复无效-弹层:{key}')
            if not isinstance(action, StartBattle):
                self._blocked.add(key)
                self._record_exec_obs(key, 'blocked', '恢复无效-状态类')
                # r93 审计 46336415:DeployMove 被屏蔽 = 落点被游戏拒(同名在场/行限制等)
                # → 写 session.deploy_fail_counts,策略腾席链跳过该角色(防下轮同卡重提案;
                # 第14局 r9 藿藿 5 连败实证)。备战场面变化后 heavy 对账自然换候选。
                try:
                    if isinstance(action, DeployMove):
                        _bc = (getattr(match.session, 'tracked_bench_chars', None) or [])
                        _hit = next((b for b in _bc if b.slot == action.from_slot), None)
                        if _hit is not None and _hit.char_id:
                            match.session.deploy_fail_counts[_hit.char_id] = (
                                match.session.deploy_fail_counts.get(_hit.char_id, 0) + 1)
                            log.info('[cw-director] DeployMove 失败记忆 %s(腾席链将跳过,换下一候选)',
                                     _hit.char_id)
                except Exception:   # noqa: BLE001  记忆 best-effort
                    pass
            if isinstance(action, ClickSpheres):
                match.session.defer_count = max(match.session.defer_count, 2)
            if isinstance(action, OpenTome):
                # r15 review P0-②:defer 门对 OpenTome 曾是死码(defer 只由 DeferSpheres/
                # ClickSpheres 置位)——失败置 defer 让策略侧门(规则 2)真正生效。
                match.session.defer_count = max(match.session.defer_count, 2)
            log.warning(f'[cw!][director] {key} 恢复(无弹层)后仍连败 → 本环屏蔽(策略须换路)')
            self._fail_counts[key] = 0   # 屏蔽后拒绝走 stall 路径,计数归零防重复触发
            return None
        # 环级强制出战门(stall≥5 且恢复已试尽,§7 H-2b)
        return self._stall_gate()

    def _bail(self, match, reason: str) -> OperationRoundResult:
        """环让位:交外环处理(§4.2b;外环重入重建 Director 时环级计数全清零)。"""
        session = match.session
        self._record_exec_obs(reason, 'bail', '环让位')
        session.bail_reason_counts[reason] = session.bail_reason_counts.get(reason, 0) + 1
        n = session.bail_reason_counts[reason]
        if n >= PrepDirector.BAIL_SAME_REASON_DIAG:
            # MED-7:同因 bail≥3 = 外环 3 次未消化该弹层(bail↔重入 ping-pong,MAX_ITER 兜底
            # 需多小时)→ 升级停机钩子(方案 D):存证 + stop_running 保画面待 AI 建档/排查。
            # hook审计 S4(r351):补 sentinel flag 三要素——接管者从 status=stopped +
            # 本 flag 即知谁停的/怎么处理/钩子分类,不走「不知道谁停的」四层排查。
            import time as _t
            log.warning(f'[cw!][director] 同因 bail ×{n}: {reason} → 升级停机(ping-pong,保画面建档)')
            import contextlib
            with contextlib.suppress(Exception):
                self.save_screenshot(prefix='bail_pingpong')
            with contextlib.suppress(Exception):
                from pathlib import Path as _P
                _P('.debug/temp/currency_war/bail_pingpong_hook.flag').write_text(
                    f'[HOOK-STOP] bail ping-pong 停机钩子(常驻兜底):prep_director._bail\n'
                    f'触发:同因 BailToOuter ×{n}(reason={reason})——外环 3 次未消化该弹层。\n'
                    f'处理步骤:1. 看 .debug/images/bail_pingpong_* 截图识别该弹层/overlay;\n'
                    f'   2. 已建档屏 → battle_loop 分发应有 handler,grep 该屏名查为何没接住\n'
                    f'      (派发条件/锚点失效?);3. 新画面 → od-dev-screen-onboarding 建档\n'
                    f'      + 加 handler;4. 合法重复出现 → 确认 _clear_bail_count 为何没清\n'
                    f'      (handler 成功路径漏调?)。\n'
                    f'移除条件:本钩子是 ping-pong 安全网,常驻不删;处理完删本 flag\n'
                    f'+ run_standalone_app 重启对局。ts={_t.strftime("%m-%d %H:%M:%S")}\n',
                    encoding='utf-8')
            rc = getattr(self.ctx, 'run_context', None)
            if rc is not None:
                with contextlib.suppress(Exception):
                    rc.stop_running(reason='hook:director_bail_pingpong')
            return self.round_fail(status=f'同因 bail ×{n}({reason}) 停机待建档')
        log.info(f'[cw][director] BailToOuter({reason}) → 交外环')
        return self.round_success(f'BailToOuter({reason})', wait=1)

    def _force_battle(self, why: str) -> OperationRoundResult:
        """F5 出口兜底:框架强制出战(策略挂了流程不断;StartBattle 豁免屏蔽)。"""
        if self._executor is None:
            return self.round_fail(status='无执行器')
        try:
            progressed, detail = self._executor.execute(StartBattle())
        except Exception as e:  # noqa: BLE001  L-4:强制出战异常不裸传(防整环 retry 重跑)
            log.warning(f'[cw!][director] 强制出战异常({why}): {e}')
            return self.round_fail(status=f'强制出战异常({why}): {e}')
        if progressed:
            return self.round_success(f'强制出战({why})', wait=3)
        return self.round_fail(status=f'强制出战失败({why}): {detail}')

    # ===== DirectorV2 接线(W606 阶段2批③;设计单一源 =
    # .debug/temp/currency_war/w606_stage2_batch3/DIRECTOR_ADAPTER_DESIGN.md §5/§6)=====

    def _run_prep_loop_v2(self, match, session, config) -> OperationRoundResult:
        """DirectorV2 备战循环(W620 批 1 起 = 唯一生产路径;端口全部复用现役件)。

        端口映射:decide/execute = adapter.DecideAdapter(经 prep_brain
        装配点管线,现役决策核 + 现役执行器 F3 验证链);observe = 本类
        _observe → snapshot_from_obs;recover = try_recovery(旧环恢复原语,
        返回「关过已知弹层」bool);force_battle/is_stopped/stop_with_evidence
        见内联。出口 → 轮次语义映射见 ``_v2_outcome_to_round``。

        动作级记账通道(旧环逐位对齐,零决策):期望态构建/前读在 execute
        端口,同帧对账族在 heavy 观察端口——旧环在循环体里逐帧消费的
        记账面(paddle 审计/买牌·拖动·装备·经验·羁绊·商店池·合成预览
        对账)经 ``_v2_post_frame_accounting`` 在新环 heavy 定型帧上等时
        消费,含 W536 买牌期望上报通道转正(蓝图 §7 批 1 行)。
        """
        from sr_od.application.currency_war.decision_v2.adapter import (
            DecideAdapter,
            snapshot_from_obs,
        )
        from sr_od.application.currency_war.decision_v2.director_v2 import (
            DirectorV2,
            _DirectorPorts,
        )
        from sr_od.application.currency_war.obs.cw_observation import (
            read_deployed_count,
        )
        from sr_od.application.currency_war.prep_actions import (
            DeployMove,
            LevelUp,
            RunBuyPhase,
            SellBench,
            SellDeployed,
            StartBattle,
        )

        adapter = DecideAdapter(match.strategy, config, self._executor)
        forced_ok = {'ok': False}   # force_battle 端口结果(出口映射消费)
        # 动作级记账状态(端口间传递;生命周期 = 单步,每次 execute 重置)
        acct: dict = {'last_obs': None, 'key': None, 'progressed': False,
                      'drag_expect': None, 'equip_expect': None,
                      'dep_delta': 0, 'dep_pre': None, 'unit_open': False}

        def _observe_port(heavy: bool):
            obs = self._observe(heavy)
            acct['last_obs'] = obs
            if heavy:
                # heavy 定型帧上的同帧对账族(旧环同款时点:动作完成后
                # heavy 重观察帧;零决策记账,异常不阻塞环)
                self._v2_post_frame_accounting(obs, acct, session)
            return snapshot_from_obs(obs, session)

        def _decide_port(snapshot, session_):
            decision = adapter.decide(snapshot, session_)
            # F8 步进遥测(旧环 _record_step 同款;obs = 最近观察帧)
            if acct['last_obs'] is not None and adapter.last_action is not None:
                self._record_step(acct['last_obs'], adapter.last_action)
            return decision

        def _execute_port(op) -> tuple[bool, str]:
            action = adapter.bound_action(op.op_key)
            if action is None:
                return False, f'v2适配器:op_key 无绑定 {op.op_key}'
            obs = acct['last_obs']
            key = op.op_key
            acct.update(key=key, progressed=False, drag_expect=None,
                        equip_expect=None, dep_delta=0, dep_pre=None,
                        unit_open=False)
            # 期望态构建 + 前读(旧环动作发出点同款;None=无法建真值不评)
            if isinstance(action, (SellBench, DeployMove)) and obs is not None:
                acct['drag_expect'] = compute_drag_expect(
                    action, obs.bench_chars, obs.deployed_chars)
            if isinstance(action, SellDeployed):
                acct['equip_expect'] = self._equip_expect_for_sell(action)
            if isinstance(action, (DeployMove, SellDeployed)):
                acct['dep_delta'] = 1 if isinstance(action, DeployMove) else -1
                _dep_frame = getattr(self, 'last_screenshot', None)
                if _dep_frame is not None:
                    try:
                        acct['dep_pre'] = read_deployed_count(self.ctx, _dep_frame)
                    except Exception:   # noqa: BLE001  观测 best-effort
                        acct['dep_pre'] = None
            acct['unit_open'] = isinstance(action, RunBuyPhase)
            if acct['unit_open'] and obs is not None:
                self._spend_unit_open(obs)
            try:
                progressed, detail = adapter.execute(op)
            except Exception as e:
                if acct['unit_open']:
                    self._spend_unit_close(progressed=False, detail=f'执行异常:{e}',
                                           boundary='aborted')
                raise
            if acct['unit_open']:
                self._spend_unit_close(progressed=progressed, detail=detail,
                                       boundary='closed' if progressed else 'failed')
            acct['progressed'] = progressed
            log.info(f'[cw][director-v2] step {key} → {"✓" if progressed else "✗"} {detail}')
            # 期望态层·经验(W552;仅 progressed 分支,旧环同款)
            if progressed and isinstance(action, LevelUp):
                self._xp_apply_levelup()
            elif progressed and isinstance(action, RunBuyPhase):
                self._xp_apply_buy_clicks(detail)
            # r292+P0③:EnsureShopClosed 执行成功后 = 店确定关的可靠时点
            #(节点行探针挂点;前置 wait_stable_frame 无条件化,离线契约放行)
            if 'EnsureShopClosed' in key and progressed:
                try:
                    from sr_od.application.currency_war.obs.cw_observation_gate import (
                        PROFILE_CLOSED,
                        wait_stable_frame,
                    )
                    wait_stable_frame(self, profile=PROFILE_CLOSED,
                                      segment='op_settle')
                except Exception:   # noqa: BLE001  离线契约:放行
                    pass
                self._probe_node_type()
            return progressed, detail

        def _recover_port() -> bool:
            _prim, closed_known = try_recovery(self, self.ctx)
            return closed_known

        def _force_battle_port(_why: str) -> bool:
            if self._executor is None:
                return False
            try:
                progressed, _d = self._executor.execute(StartBattle())
            except Exception as e:   # noqa: BLE001  对齐 _force_battle 不裸传
                log.warning(f'[cw!][director-v2] 强制出战异常({_why}): {e}')
                return False
            forced_ok['ok'] = progressed
            return progressed

        def _is_stopped() -> bool:
            # W209j 刹车精确判据(旧环同款;现读不缓存)
            rc = getattr(self.ctx, 'run_context', None)
            return rc is not None and getattr(rc, 'last_run_result', None) is not None

        def _stop_with_evidence(reason: str) -> None:
            # 停机留证钩子(方案 D,与 _bail ping-pong 同款三要素)
            import contextlib
            with contextlib.suppress(Exception):
                self.save_screenshot(prefix='v2_evidence_stop')
            with contextlib.suppress(Exception):
                from pathlib import Path as _P
                _P('.debug/temp/currency_war/v2_evidence_stop_hook.flag').write_text(
                    f'[HOOK-STOP] DirectorV2 留证停机\n触发: {reason}\n'
                    f'处理:看 .debug/images/v2_evidence_stop_* 截图建档/排查;'
                    f'处理完删本 flag + 重启对局。\n',
                    encoding='utf-8')
            rc = getattr(self.ctx, 'run_context', None)
            if rc is not None:
                with contextlib.suppress(Exception):
                    rc.stop_running(reason='hook:v2_evidence_stop')

        def _record_defect(kind: str, detail: str) -> None:
            log.warning(f'[cw!][director-v2] 缺陷 {kind}: {detail}')
            try:
                from sr_od.application.currency_war.telemetry import cw_telemetry
                rid = cw_telemetry.current_run_id() or '-'
                cw_telemetry.get_recorder().record_exec_event(
                    run_id=rid, round_num=0, action_family='DirectorV2',
                    screen='battle_prep', event=f'defect_{kind}',
                    reason=detail[:200])
            except Exception:   # noqa: BLE001  遥测 best-effort
                pass

        ports = _DirectorPorts(
            decide=_decide_port,
            observe=_observe_port,
            execute=_execute_port,
            recover=_recover_port,
            force_battle=_force_battle_port,
            is_stopped=_is_stopped,
            stop_with_evidence=_stop_with_evidence,
            record_defect=_record_defect,
        )
        outcome = DirectorV2(ports).run(session)
        return self._v2_outcome_to_round(outcome, forced_ok['ok'])

    def _v2_post_frame_accounting(self, obs, acct: dict,
                                  session) -> None:
        """新环 heavy 定型帧上的动作级对账族(旧环同帧消费逐位对齐;零决策)。

        输入 = 本帧 obs + acct(最近一步动作记账状态);每通道内部
        best-effort,异常不阻塞环。覆盖:paddle 审计 / 拖动期望 / 买牌
        期望(W536 上报通道转正,蓝图 §7 批 1 行)/ 经验 / 羁绊显示 /
        商店池 / 合成预览 / 卖角色装备期望。
        """
        import contextlib

        from sr_od.application.currency_war.obs.cw_observation import (
            read_deployed_count,
        )

        key = acct.get('key')
        progressed = bool(acct.get('progressed'))
        # W512 动作级板面对拍(后读;期望不等 = 未生效证据,纯留证)
        if acct.get('dep_pre') is not None:
            with contextlib.suppress(Exception):
                _dep_post = read_deployed_count(self.ctx, self.last_screenshot)
                if _dep_post is not None and _dep_post - acct['dep_pre'] != acct['dep_delta']:
                    _gap = _dep_post - acct['dep_pre']
                    cw_telemetry.record_defect(
                        'deployed', 'invariant_break',
                        expected=f'{key} 执行后 paddle={acct["dep_pre"] + acct["dep_delta"]}',
                        observed=f'paddle={_dep_post}',
                        plane=int(getattr(obs.state, 'plane', 0) or 0),
                        round_num=int(getattr(obs.state, 'round_num', 0) or 0),
                        gap=float(_gap), gap_large=True,
                        reader_source='paddle_action_audit',
                        note='部署/卖出动作级即时对拍(§2.3;与 deployed_align 自动纠漂分立)')
        # 期望态对账(仅 progressed 分支——验证失败 = 动作未发生,期望不适用)
        with contextlib.suppress(Exception):
            if progressed and acct.get('drag_expect') is not None:
                self._reconcile_drag_expect(acct['drag_expect'])
        # 期望态层·买牌(W536 上报通道转正):RunBuyPhase 单元购买期望由
        # shop.py 买入点写入 session.pending_buy_expect;本帧消费对账。
        with contextlib.suppress(Exception):
            _pending_buy = session.pending_buy_expect
            if _pending_buy is not None:
                session.pending_buy_expect = None
                if progressed:
                    self._reconcile_buy_expect(_pending_buy)
        with contextlib.suppress(Exception):
            self._reconcile_xp_expect(obs)
        with contextlib.suppress(Exception):
            self._reconcile_faction_display(obs)
        with contextlib.suppress(Exception):
            self._reconcile_shop_pool(obs)
        with contextlib.suppress(Exception):
            self._reconcile_merge_preview(obs)
        with contextlib.suppress(Exception):
            if progressed and acct.get('equip_expect') is not None:
                self._reconcile_equip_expect(acct['equip_expect'])
        acct.update(key=None, progressed=False, drag_expect=None,
                    equip_expect=None, dep_delta=0, dep_pre=None,
                    unit_open=False)

    def _v2_outcome_to_round(self, outcome, forced_ok: bool) -> OperationRoundResult:
        """LoopOutcome → SrOperation 轮次语义(设计 §6 映射表;现役行为锚见行内)。"""
        from sr_od.application.currency_war.decision_v2.director_v2 import (
            LoopOutcomeKind,
        )
        kind = outcome.kind
        reason = outcome.reason
        if kind is LoopOutcomeKind.BATTLE:
            return self.round_success('出战(环出口)', wait=3)
        if kind is LoopOutcomeKind.BATTLE_FORCED:
            if forced_ok:
                return self.round_success(f'强制出战({reason})', wait=3)
            return self.round_fail(status=f'强制出战失败({reason})')
        if kind is LoopOutcomeKind.BAIL:
            # bail 计数已由引擎 _bail 完成(局级只增不清,ping-pong 在引擎)
            return self.round_success(f'BailToOuter({reason})', wait=1)
        if kind is LoopOutcomeKind.PINGPONG_STOP:
            # 留证已由 stop_with_evidence 端口完成
            return self.round_fail(status=reason or 'ping-pong 停机')
        if kind is LoopOutcomeKind.BRAKE_STOPPED:
            return self.round_fail(status='已停止[hook]')
        if kind is LoopOutcomeKind.EVIDENCE_STOP:
            return self.round_fail(status=reason or '留证停机')
        return self.round_fail(status=reason or 'v2 环失败')

    def _probe_node_type(self) -> None:
        """[观测] 备战入场读节点行序列(read_node_sequence)→ log。

        自 battle_prep._probe_node_type 搬入(P1 挂载切换,doc §7 L1)。read_node_sequence =
        HoughCircles 动态定圆 + HSV 三态 + Hu 匹配 + OCR(见 cw_node_reader)。
        未识别图标采集钩子(版本前哨,保留):未来圆 hu_dist > 阈值 → 裁图标存盘。
        ⚠️ 已知误报(2026-08-16 复盘):历史 61 张采集全是**宝箱(奖励)图标的小尺寸 Hu 漂移**
        (idx 4/5/7 远处节点,非新类型)——HU_DIST_UNRECOGNIZED=2.8 对远距小图标过严,
        修阈值/过滤属 reader 校准待办(与扑满无关:扑满=奖励图标已实证,M45 current:reward
        直接命中)。真新类型出现时本钩子仍是唯一自动捕获渠道,保留。"""
        try:
            from sr_od.application.currency_war.obs.cw_node_reader import (
                HU_DIST_UNRECOGNIZED,
                NODE_ROW_RECT,
            )
            from sr_od.application.currency_war.obs.cw_observation import (
                read_node_sequence,
            )
            screen = self.screenshot()
            slots = read_node_sequence(self.ctx, screen)
            if not slots:
                log.info('[cw-director][nodeseq] skip(模板未加载 / 非 clean 备战帧)')
                return
            summary = ', '.join(
                f'{s.idx}:{s.state}:{s.node_type}' + (f'({s.hu_dist:.1f})' if s.hu_dist else '')
                for s in slots)
            log.info(f'[cw-director][nodeseq] n={len(slots)} | {summary}')
            self._capture_unrecognized_node_icons(screen, slots, NODE_ROW_RECT, HU_DIST_UNRECOGNIZED)
            # r265:current 槽类型写 session(battle_loop on_round_end 消费——
            # 节点类型分层遥测;权威源=备战节点行,替代结算屏 OCR 推断)。
            # r266(current 恒 None 修复):current 高亮态 Hu 不匹配(模板只对
            # future 生效)+OCR 标签错位守卫 → current 直读恒 None。
            # 修:**last-known upcoming**——上一备战帧 upcoming[i] 就是本轮
            # current(节点行固定序列左移);本帧 upcoming 同时存下轮用。
            try:
                _sess = (self.ctx.cw_match.session
                         if self.ctx.cw_match is not None else None)
                if _sess is not None:
                    # r363(审计 P0-1/P0-2):首帧(r1 或重启后)写开局
                    # 槽序表——r362 的 battle_loop 兜底此前**无写入者**
                    # (审计实锤死读);plane_node_table = 本帧全部槽
                    # (current+upcoming+past 按 idx)的类型序。
                    _all = sorted(slots, key=lambda s: s.idx)
                    _seq = [s.node_type for s in _all if s.node_type]
                    _st_now = (self.ctx.cw_match.session.last_state
                               if self.ctx.cw_match is not None else None)
                    _plane_now = (_st_now.plane
                                  if _st_now is not None else None)
                    if store_plane_table(_sess, _seq, _plane_now):
                        log.info('[cw-director][nodeseq] 槽序表存 p%s %d 槽:%s',
                                 _plane_now, len(_seq), _seq)
                    # r290(current 覆盖链改左移优先):OCR 标签
                    # 位置门(r80)拦不住相邻同类标签(局20 实证:
                    # r3 结算屏「战斗」vs current 读 reward——
                    # reward 标签恰在 current 下方 x 对上)→
                    # current 直读不可信。改:**左移推断优先**
                    # (上帧 upcoming[0],r266 已有),OCR 标签
                    # 只在左移无值时兜底(开局首帧)。
                    # r363(审计 P0-2 修):左移**锚定轮次**——同轮
                    # 多次 probe(开店/关店/重开)时 upcoming 还是本轮
                    # 的,旧代码会把 current 写成下一节点(超前一位)。
                    # 只在上次 probe 是更早轮次时才左移;同轮保持原值。
                    _anchor = (_st_now.plane, _st_now.round_num) \
                        if _st_now is not None else None
                    _prev_anchor = getattr(
                        _sess, 'nodeseq_probe_anchor', None)
                    if _anchor is not None and _anchor != _prev_anchor:
                        _prev = getattr(_sess, 'upcoming_types', None) or []
                        _direct = _prev[0] if _prev else None
                        if _direct is not None:
                            _sess.node_type_current = _direct
                        _sess.nodeseq_probe_anchor = _anchor
                    # current 直读兜底(首帧:无左移源时)
                    if getattr(_sess, 'node_type_current', None) is None:
                        _cur = next((s for s in slots
                                     if s.state == 'current'), None)
                        if _cur is not None and _cur.node_type:
                            _sess.node_type_current = _cur.node_type
                    # 存本帧 upcoming(下轮左移用; idx 升序)
                    _sess.upcoming_types = [
                        s.node_type for s in sorted(
                            (x for x in slots if x.state == 'upcoming'),
                            key=lambda x: x.idx) if s.node_type]
                    # r306(用户指路,方向修正):
                    # **实时识别是权威**——每备战帧读节点行,
                    # 应对 invest-env 等策略对节点的改变;
                    # 开局帧的完整槽序存 plane_node_table 只作
                    # **离线统计源**(跨局累积建「位面典型节点表」
                    # 进 sim 骨架/策略知识)+ current 槽高亮读不到
                    # 时的左移兜底参照。不做决策主源。
            except Exception:   # noqa: BLE001  best-effort 写入
                pass
        except Exception as e:  # noqa: BLE001  live 验证 best-effort,失败不阻塞备战
            log.info(f'[cw-director] nodeseq skip: {e}')

    def _capture_unrecognized_node_icons(self, screen, slots, node_row_rect, hu_threshold) -> None:
        """未识别图标采集(版本前哨):未来圆 Hu 无显著最近 → 裁图标存盘(内容哈希去重)。

        仅 upcoming 槽(判态已修 V 门,变暗过去节点不再混入);RGB 裁剪存盘(颜色信息保留,
        模板同样 RGB——2026-08-16 用户指导)。
        r80(审计 P1-3):**同 idx 300s 时间窗防抖** —— 内容哈希去重防不住备战帧微变
        (光标/金币动画/抗锯齿 → 哈希必新),同 idx 每帧重采刷屏(2-7 实证 idx4/5 连发);
        已知误报源是远距小图标 Hu 漂移(61 张复盘),300s 窗足够人工/离线跟进,新类型
        (真未识别)首采不受影响。
        """
        import time as _time

        from sr_od.application.currency_war.kernel.cw_observe import cw_shot_unique
        icon_r = 24   # 采集分析窗(略 > 分类窗 _SAMPLE_R=18,多上下文)
        x0, y0, x1, y1 = node_row_rect
        row = screen[y0:y1, x0:x1]
        now = _time.monotonic()
        for s in slots:
            if s.state != 'upcoming' or s.hu_dist is None or s.hu_dist <= hu_threshold:
                continue
            if now - _NODE_ICON_SHOT_TS.get(s.idx, 0.0) < 300:
                continue   # 同 idx 时间窗内已采过(帧微变哈希必新,内容哈希去重失效;r80 审计c:module-level 跨环存活)
            yc0, yc1 = max(0, s.cy - icon_r), s.cy + icon_r
            xc0, xc1 = max(0, s.cx - icon_r), s.cx + icon_r
            fn = cw_shot_unique(row[yc0:yc1, xc0:xc1], f'node_unknown_{s.idx}')
            if fn:
                _NODE_ICON_SHOT_TS[s.idx] = now
                log.info(f'[cw-director][nodeseq] 未识别图标 idx={s.idx} hu={s.hu_dist:.1f} → 采 {fn}')

    def _record_step(self, obs: PrepObservation, action: PrepAction) -> None:
        """F8:obs+action 序列落 telemetry(P1 仅落盘;replay 评分后置)。"""
        try:
            st = obs.state
            _sess = self._session()
            if st is not None:
                st = st.copy()
                # W222 遥测缺口①同源(shop record 点已补,本处是步进行):
                # obs.state 是 OCR 现读态(equips 恒空),从 session owned 快照
                # 补拷。copy 后再写——cw_comps 装备权重读 state.equips,
                # 原地写会污染 director 后续决策输入(观测链修复禁越界)。
                st.equips = list(getattr(_sess, 'last_owned_equips', []) or []) \
                    if _sess is not None else []
            cw_telemetry.record_decision(
                st if st is not None else GameState(),
                target_comp=(_sess.target_comp.name
                             if _sess is not None and _sess.target_comp else ''),
                candidate_scores={},
                eval_breakdown={'prep_step': float(self._steps)},
                actions=[action],   # type: ignore[list-item]  PrepAction 与旧 Action 并存(P2 归一)
                gold_point=False,   # r68 review:步进记录不进 gold_trajectory(每回合一采样,shop 侧采)
                extra={'formed_stop': bool(getattr(
                    _sess, 'v3_formed_stop', False)),  # ADR-0343 豁免联动
                    # P1 配方对平铺观测(P1 备战帧判读「终局线何时锁」的
                    # 上游量;锁定产物/副方向取序见 p1_pair_label)
                    'sess_p1_pair': cw_telemetry.p1_pair_label(
                        getattr(_sess, 'v3_intention', None))},
            )
        except Exception as e:  # noqa: BLE001  遥测失败不阻塞环
            log.debug(f'[cw-director] telemetry skip: {e}')
