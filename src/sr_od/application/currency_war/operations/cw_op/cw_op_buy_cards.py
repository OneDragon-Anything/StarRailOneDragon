
import contextlib
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import (
    action_sink,
    observation_source,
)
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
    _area_rect,
    area_center,
    shop_card_click_points,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    BenchChar,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    bench_occupied,
    ledger_node_type,
    pad_bench,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.kernel.cw_telemetry_exit import journal_refs
from sr_od.application.currency_war.obs.cw_observation import (
    PHASE_PREP_SHOP_OPEN,
    ensure_portrait_templates,
    new_bench_slots,
    read_game_state,
    read_gold,
    read_gold_opt,  # noqa: F401  模块属性路由:cw_shop_action_ops 经本模块名取读函数(替身缝)
    read_shop_cards,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.application.currency_war.operations.decision_frame_hooks import (
    save_decision_frame,
)
from sr_od.application.currency_war.telemetry import defects
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    # 注解专用。消费关系锚点 = cw_observation.read_gold_opt 经本模块名
    # 取读的替身缝(monkeypatch 面),cw_shop_action_ops 因此以函数内
    # lazy import 消费本文件;注解不经运行时求值,不新增模块级反向依赖。
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_state import (
        Action,
        CloseShop,
        LevelUpShop,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopActionOp,
        ShopVisitLedger,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        CurrencyWarMatch,
    )


def _apply_hp(state: GameState, hp_value: int | None,
              readable: bool, trusted: bool) -> None:
    """hp 值+保真位同写(单一写点;覆盖丢位根治)。

    旧覆盖点只写 ``state.hp`` 不动 ``hp_readable/hp_trusted``,shop 开帧
    read_game_state 产出的 (False, False) 两位与覆盖进来的值分家 → 产出
    值位自洽的「带毒假值」形态。同写后位语义恒与值来源一致:真读覆盖
    → (v, True, True);结算真值覆盖(fresh 门过)→ (v, False, True);
    ``hp_value=None``(无真读且无新鲜结算真值)→ **不覆盖**,保留
    read_game_state 对账层产物(位面正确标注,血线消费门按 fail-closed
    拒收)。消费口径单一源=decision_v2.posture_release.hp_decision_trusted。
    """
    if hp_value is None:
        return
    state.hp = hp_value
    state.hp_readable = readable
    state.hp_trusted = trusted


# 商店牌行区 rect(1080p)——读卡自愈门的目标区,与刷新分支(r325)同区。
# 派生化:优先按建档 area「商店牌-1」现算(单一源=screen_info);area 缺失
# 才回退字面量(1080p 项目既有前提,与 r325 同值)。
_SHOP_ROW_RECTS: tuple | None = None


def _shop_row_rects(op: SrOperation) -> tuple:
    """牌行区 rect 派生(建档 area 优先,字面量兜底);进程内缓存。"""
    global _SHOP_ROW_RECTS
    if _SHOP_ROW_RECTS is None:
        from one_dragon.base.geometry.rectangle import Rect
        _r = None
        with contextlib.suppress(Exception):
            _r = _area_rect(op.ctx, f'{A_SHOP_CARD_PREFIX}1', SHOP_SCREEN_NAME)
        _SHOP_ROW_RECTS = (_r if _r is not None
                           else Rect(300, 228, 1560, 326),)
    return _SHOP_ROW_RECTS


# 超时回退补偿:调用方契约是「等稳后读」,超时(画面 2s 永变)返回时若
# 立即读 = 把「未稳」当「已尽最大等待」;补 0.5s 静置再交读,与被替换的
# M35 blind sleep(读前必有 ≥1.0s 等待)语义对齐。
_SETTLE_TIMEOUT_COMPENSATE_S: float = 0.5


def _wait_shop_row_stable(op: SrOperation, max_wait_s: float = 2.0,
                          min_observe_s: float = 1.0) -> bool:
    """等待商店牌行区「两帧指纹一致」(动画/settle 收敛判据,非 blind sleep)。

    为什么不用固定 sleep:M35 之前未识别停机钩子的防抖重读是 blind
    sleep(1.0s×2),对「刷新动画/settle 瞬时帧」类 miss 自愈靠猜时长;
    判据化后读卡前先等牌行区连续两帧指纹一致(与刷新分支 r325 同门同
    rect),稳定即读。

    **fast-path 最短观察窗(W952 审计 P2-1)**:两帧相同即放行会被慢机
    冻结帧骗过(两次采样落在同一冻结画面上,间隔可短至 0.5s)→ 非终帧
    放行 → 本可自愈的 case 烧成真停(M35「0.3s 不够」教训同型)。故
    指纹相同还须**观察时长 ≥ min_observe_s**(默认 1.0,对齐被替换的
    M35 单次等待)才放行;冻结帧最短也观察满 1.0s。

    **超时回退补偿(W952 审计 P2-2)**:超时返回 False 前,静置
    ``_SETTLE_TIMEOUT_COMPENSATE_S`` 再交还调用方——调用方契约是
    「等稳后读」,永变超时立读 = 未稳即读;补偿后单次门最短等待语义
    恒 ≥1.0s,与被替换行为对齐。

    边界:模态覆盖层(如「我来当策划·骇入效果」弹窗)压暗全屏时画面
    本身稳定,本门按 fast-path 放行——该形态不是瞬态帧,重读不会自愈,
    由调用方的有限次预算耗尽后走停机留证(弹窗处置归弹窗批域)。

    返回 True=观测到稳定帧(且已观察 ≥min_observe_s);False=超时
    (已补偿静置)。截图异常按离线契约降级继续等(r327 同契约)。

    预算总时长(调用方声明):钩子 2 次重读 × (门 ≤2.0s+补偿 0.5s)
    ≈ 最坏 5.0s + 2 次读卡耗时,量级与被替换 M35(2×1.0s+读)同档。
    """
    rects = _shop_row_rects(op)
    from one_dragon.utils import cv2_utils
    base = None
    start = time.monotonic()
    deadline = start + max_wait_s
    while True:
        time.sleep(0.25)
        fp = None
        try:
            fp = cv2_utils.fingerprint_in_rects(op.screenshot(), rects)
        except Exception:   # noqa: BLE001  离线契约(r327 同款)
            fp = None
        if fp is not None and base is not None \
                and cv2_utils.fingerprint_same(fp, base) \
                and time.monotonic() - start >= min_observe_s:
            return True
        if fp is not None:
            base = fp
        if time.monotonic() >= deadline:
            time.sleep(_SETTLE_TIMEOUT_COMPENSATE_S)
            return False


def _r1_retry_read_hp(read_fn) -> int | None:
    """r1 备战 HP 重试读(用户修正前提:r1 血量固定但**不恒为 100**,随当局
    难度/词缀变化——真值源=备战画面显示值,默认 100 兜底在 r1 是错误值)。

    备战画面血量可见,miss=时序/识别抖动 → 最多再试 2 次;仍 miss=返回
    None(诚实未知,严禁落 100 兜底)。返回值即真读,可信度等同真读。
    """
    for _ in range(2):
        time.sleep(0.6)
        v = read_fn()
        if v is not None:
            return v
    return None


def sell_guard_ok(expected: str | None, live: str | None) -> bool:
    """卖前对拍守卫(ADR-0329 件2 设计章2.5 轻守卫)。

    生成期快照 ``state.bench[idx].char_id``(期望名)vs 执行期实况
    ``tracked_bench_chars`` 现槽名——不符 = 槽位内容已被本循环前序动作消费
    (3合1 merge 删件/前笔卖出)→ 整笔跳过(stale_proposal,与 cw_state 拒绝
    语义同词)。两表同源于循环顶(``state.bench`` 按 tracked 下标直拷播种,
    T-308/ADR-0646 S1),mid-loop 漂移必被抓。残余风险(不防「tracked 名字
    本身错」)= buy-OCR 误读,属既有跟踪保真度问题(迁移审计 w57(git 历史)
    F6),不在本批根治。
    """
    return bool(expected) and live is not None and live == expected


def expected_gold_after_actions(state_gold: int, spend: int,
                                sell_income: int) -> int:
    """买后预期金(ADR-0329 件2 设计章2.7 必改项):开店金 − 花出 + 卖入。

    gold 差值对拍口径:卖出接线后,卖轮实际金 = state.gold − spend + sell_income
    (游戏侧卖出入账),与旧 ``_expected = state.gold - _spend`` 恒差 income →
    每卖轮误报 gold_delta 冲突留证。修 = 对拍纳入卖入(与 ``query_economy``
    的 income 口径同式:income 在 actions 里)。
    """
    return state_gold - spend + sell_income


def refresh_effective(before_names: list[str] | tuple[str, ...],
                      after_names: list[str] | tuple[str, ...]) -> bool | None:
    """刷新有效性判据(观测自检框架设计 §2.5;纯观测零决策)。

    刷后牌名集合 == 刷前集合 → 刷新未生效(点击落空/费金照扣没刷/动画帧
    误读)。真刷出全同 5 牌是牌池组合级小概率、连续两次全同更低——「两连全同
    才确认」的防抖由台账复现计数承载(同特征首见 L1、再现升 L0),本函数只给
    单波判定。任一侧含未识别槽('')→ 读不可判返 None 不猜(宁缺勿造,与既有
    unknown miss 语义同);空列表同样视为不可判(牌面整帧失读)。
    """
    if (not before_names or not after_names
            or any(not n for n in before_names)
            or any(not n for n in after_names)):
        return None
    return set(before_names) != set(after_names)


# 买牌动画(卡牌飞行)收敛等待:首采无新槽后重采前的延迟秒数。
# 取值 ≈ 一次买牌动画时长(实机停线现场为飞行中帧,数秒内收敛),0.8-1.2s 区间。
BENCH_BUY_SETTLE_RETRY_DELAY_S: float = 1.0


def bench_buy_slots_settle_retry(
    bought_count: int,
    first_slots: list[int],
    resample: Callable[[], list[int]],
    delay_s: float = BENCH_BUY_SETTLE_RETRY_DELAY_S,
) -> tuple[list[int], bool]:
    """买牌后新占槽 pixel-diff 观测的动画收敛重采(观测时序修复,零行为外溢)。

    买牌有卡牌飞行动画:对比帧早于动画收敛采样会误判「新占槽=0」
    (实机 run_20260830_071711 P1r3 L0 安灯停线实证:停线截图卡牌飞行中,
    数分钟后板凳实际 1→2 占用、gold 22→21——买真实执行,纯观测时序误报)。
    修法:买 ≥1 张且首采无新槽 → 延迟 delay_s 后经 resample 重采一次,
    仍无才把空结果交上游破缺判定(:func:`bench_buy_occupancy_ok`)。
    边界:未买牌或首采已有新槽 → 原样返回不 sleep 不重采;全程只读屏
    (resample 由调用方提供,本函数不点击、不碰决策/买牌执行)。

    返回 (最终新占槽列表, 是否发生过重采)。
    """
    if bought_count <= 0 or first_slots:
        return first_slots, False
    time.sleep(delay_s)
    return resample(), True


def bench_buy_occupancy_ok(bought_count: int, new_slot_count: int) -> bool | None:
    """买牌占位判据(观测自检框架设计 §2.2;纯观测零决策)。

    本单元执行了 ≥1 次 BuyCard → ``new_bench_slots``(pixel-diff,身份无关)
    应有 ≥1 新占槽;0 新槽 = 「占位不出现」——设计点名的唯一硬失败形态
    (点击落空/动画帧误判),按 gap_large 落台账。未买牌 → None 不判。
    首采 0 新槽先经 :func:`bench_buy_slots_settle_retry` 重采(动画收敛),
    仍 0 才判 False——本函数语义不变,收敛处理在采样侧。
    """
    if bought_count <= 0:
        return None
    return new_slot_count > 0


def bench_buy_count_ok(bought_count: int, new_slot_count: int,
                       sold_count: int) -> bool | None:
    """买牌落位计数总账(观测自检框架设计 §2.2;纯观测零决策)。

    期望:新占槽数累计 = 本单元 BuyCard 数 − 中途卖出数(设计原文口径)。
    已知留证级误报源(设计 §2.2「单槽误判被总账对冲」的延伸):pixel-diff
    只认「槽变了」不认方向——本单元卖出/3合1 合并引起的槽变化也会计入
    新槽,故计数不符只留证(gap_large=False),由单元总账语义对冲,不作
    硬失败。未买牌 → None 不判。
    """
    if bought_count <= 0:
        return None
    return new_slot_count == bought_count - sold_count


def bench_buy_identity_missing(bought_names: list[str],
                               readback_names: list[str]) -> list[str] | None:
    """买牌身份回读对拍(观测自检框架设计 §2.2;纯留证,非失败判据)。

    返回回读身份中未出现的买牌名(留证清单)。设计明示「身份留证不算失败,
    占位不出现才算失败」——占位由 :func:`bench_buy_occupancy_ok` 另判。
    匹配口径:两侧均为注册表规范名(买牌名 = shop OCR 名经 ``get_char``
    校验链;回读名 = SIFT 经 ``resolve_char_name`` 规范),全等即匹配——
    设计写的 LCS 名匹配针对 OCR 形变场景,此对拍两侧已规范化的名字无形变
    输入,不需要容差层。回读为空 = SIFT 整帧失读/模板未加载 → None 不猜
    (宁缺勿造,与既有 unknown miss 语义同)。
    """
    if not bought_names or not readback_names:
        return None
    _have = set(readback_names)
    return [n for n in bought_names if n and n not in _have]


def refresh_wave_is_refresh_only(actions: list) -> bool:
    """仅刷新波判定(执行边界压缩·连击共享往返的单一判据)。

    「仅刷新波」= plan 首动作即 RefreshShop(执行前缀截在该刷,波内
    无任何买卡/升级/卖出)。此时波循环顶的整帧读未被本波动作污染,
    state.gold / state.shop 即刷新点击前现读——``w592_free_refresh_fix/``
    (ADR-0456 勘误)禁用 state.shop 当刷前读的失效条件(「波内买卡
    不从 state.shop 摘已买牌」)在仅刷新波不成立,可安全复用。
    返回 False 的波(前缀含买/卖)维持刷前 pre-shot 现读,语义不变。
    """
    return bool(actions) and isinstance(actions[0], RefreshShop)


def build_post_buy_incremental_state(
        last_state: GameState,
        gold_read: int | None,
        tracked_bench_chars: list[BenchChar],
        hp_value: int | None,
        hp_readable: bool,
        hp_trusted: bool,
) -> GameState | None:
    """买后重估增量态构造(执行边界压缩·买后验证增量的单一构造点)。

    机制不变量:买牌/卖牌/刷新不触 plane/round/board/level/xp/streak/
    node_type(升级触 level/xp,由调用方 total_level 门拦截,不进本函数);
    gold 用关店帧真读;bench 重播 tracked_bench_chars(执行侧
    mutate_bench_deployed 逐动作同步的权威源,末波垫底 state 的 bench
    是执行前快照,必须重播)。node_type 随 deepcopy 沿垫底帧透传——垫底
    帧值由店开帧组装供给(台账查表,ADR-0587),本构造点禁再接会话滞后
    标量覆盖(旧 last_node_type 参数已删,与买后重估回退分支同理由)。
    fail-closed 两维:①gold_read=None(金失读)→ 返回 None,调用方回退
    全量 read_game_state;②tracked_bench_chars 为空 → 同样返回 None。
    ②的理由:bench 真空(全部署/合成清空)与跟踪丢失在本构造点不可区分,
    而垫底 state.bench 是执行前快照——空 tracked 时沿用它会把陈旧 bench
    当真值喂给方向刷新(误读维度造值;消费位 = finalize 暂存帧,ADR-0583)。
    回退全量读后两种情形都得到 OCR 真值,代价只是罕见情形多一次整帧读。
    """
    if gold_read is None:
        return None
    if not tracked_bench_chars:
        return None   # 空 tracked:真空/丢跟踪不可区分 → fail-closed 回退全量读
    post = deepcopy(last_state)
    post.gold = gold_read
    # T-308/ADR-0646 S1:tracked 输入域下标直拷(pad 补 None;禁读 slot 字段
    # ——tracked 域 slot 与下标的一致性由 S2 写回端保证,消费端下标即布局)。
    # 旧 bench_from_compact 槽号重构仅对 SIFT 现读域(slot 与读序同帧同源)
    # 合法,见 ADR-0646 消费点分界。
    post.bench = pad_bench(deepcopy(tracked_bench_chars))
    _apply_hp(post, hp_value, hp_readable, hp_trusted)
    return post


def _form_progress(comp: 'Comp', state: GameState) -> float:
    """fp 遥测helper(review 要求:fp 轨迹可观测;调用方保证 comp 非 None)。

    归属申报:state 经 board_state_bridge 装箱 = 统一 state 过渡桥语义
    (T-70 线),本 hunk 实际随 T-13 提交入库而原提交信息未申报,此处
    补记归属供审计对账。
    """
    from sr_od.application.currency_war.kernel.cw_board_state import (
        board_state_bridge,
    )
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    return form_progress(comp, board_state_bridge(state))


# 「购买经验」按钮(= 买经验升等级)screen_info area 名;中心运行时读(area_center)
BUY_EXP_AREA: str = '备战标识-购买经验'
LEVEL_UP_FALLBACK: Point = Point(296, 860)   # screen_info 缺失时兜底
REFRESH_FALLBACK: Point = Point(1592, 472)   # 「刷新」按钮兜底(screen_info 按钮-刷新)
# D牌(刷新)硬上限:plan 的 _refresh_cap 是单次 plan 软上限;两阶段循环里再加硬墙防死循环
MAX_REFRESH: int = 4
# 单段决策循环防御帧帽(ADR-0518):决策侧席位门等提案门失效时的执行侧
# 兜底,与 cw_screen_prep.VISIT_ACTION_CAP 同款防线——决策循环不收敛 =
# 投影或策略器 bug,超帽响亮暴露(RuntimeError)+ 遥测分键
# plan_visit_action_cap,禁静默续跑。
SHOP_SEGMENT_ACTION_CAP: int = 16


def _fmt_action(a: 'Action') -> str:
    """单 Action → 紧凑日志串(调试/复盘读 plan 用)。"""
    if isinstance(a, BuyCard):
        return f'Buy({a.card.faction}/{a.card.name}/{a.card.cost})'
    if isinstance(a, LevelUp):
        return f'LvUp({a.cost})'
    if isinstance(a, DeployMove):
        return f'Deploy(bench{a.bench_idx}->{a.to_row})'
    if isinstance(a, RefreshShop):
        return 'Refresh'
    if isinstance(a, SellBench):
        return f'Sell(bench{a.bench_idx})'
    return type(a).__name__


@dataclass
class BuyCardsOutcome:
    """买牌波循环产出(编排壳消费;W970 批 A §4.3.4「CwOpBuyCards 产出」)。

    state = 末波融合态;total_* / spend_executed / gold_open = 动作账与
    对拍基线(壳侧 gold 差值对拍消费);plan_truncated / refresh_* 执行
    事实(set_unit_exec_facts 消费);buy_* 期望态基座(w536 单元尾
    计算暂存消费);bought_names 已在 buy_cards 内消费(pixel-diff 落位),
    不外发。
    """
    state: GameState
    config: CurrencyWarConfig
    total_buy: int
    total_level: int
    total_refresh: int
    total_sell: int
    total_sell_income: int
    total_sell_skip: int
    total_sell_fail: int
    spend_executed: int
    gold_open: int | None
    plan_truncated: bool
    refresh_skipped: str | None
    refresh_attempted: bool
    refresh_board_changed: bool | None
    buy_purchases: list  # list[cw_prep_expect.BuyPurchase](惰性 import,注解不实体化)
    buy_has_sell: bool
    buy_unidentified: bool
    buy_pre_bench: list[BenchChar]
    buy_pre_deployed: list[BenchChar]
    # [索引定义] visit_actions = 本访问段发射过的动作对象列表(list 下标 =
    # 发射序,先进先出;元素 = 真实 Action 实例,含未落地动作);取值时机 =
    # run_buy_waves 出口快照(单元收口后不再变)。消费方 = 安灯执行失败
    # 停机钩子(W3/T-255:serialize_action 后喂 classify_spend_unit 单一源,
    # 替代已停写的 decisions plan 行读面)。
    visit_actions: list


def apply_action_outcome(_aop: 'ShopActionOp',
                         action: 'BuyCard | RefreshShop | SellBench | LevelUpShop | CloseShop',
                         _ok: bool, _cur: GameState,
                         match: 'CurrencyWarMatch', ledger: 'ShopVisitLedger',
                         visit_actions: list) -> None:
    """执行结果落地门(调用环单一源;落地审补办清单 C1 调用环级锁的承载体。

    C1 语义 = 旧 return True 使期望账投影与 tracked 实账分叉、guard 当轮
    炸;应修-2 语义 = 已买集无条件追加使检出帧名污染 prefer_names/churn
    (落地审补办审,2026-09-05;原清单为会话产物不入库,语义以此为准)。

    未落地(_ok=False,如执行侧检出购买未生效)⇒ **两侧都不动**:不投影、
    不守卫、不入「已买」集(防检出帧名污染 prefer_names/churn/P60,
    应修-2);落地且非终结 ⇒ 投影(决策 10)+ guard_expected_vs_tracked
    (满栏买入豁免照旧:豁免面 = 游戏接受而两模型都不收编的残余窗;
    合成满栏买面已随 T-182 同构化——tracked mutate 带 shop 视图与
    simulate 同走 `_apply_full_bench_merge_buy`,不再丢件漏记)。
    """
    visit_actions.append(action)
    _post_frame = None   # 动作后投影帧(终结/未落地 = None → journal delta 省略)
    if _ok and isinstance(action, SellBench):
        # T-159 §3.3 误标检出位(s1_reset_mischannel 交叉对账的运行时半):
        # 商店域落地门不辖 S1 清键(落域澄清:店内段 S1 语义正在成立中,
        # 域内卖出经由六序域内闭环旗标无感)——landed 族 A 卖出若携带
        # 备战域白名单 route tag = tag 泄漏进商店域的结构性错位,计数
        # 显影(现役构造面不可达:族 A 动作无 route_tag 字段,防御位)。
        # 离线对账半 = s1_reset_by_* 与卖出通道计数交叉判读。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
            S1_RESET_ROUTE_TAGS,
        )
        _rt = getattr(action, 'route_tag', '') or ''
        if _rt in S1_RESET_ROUTE_TAGS:
            _st_mis = strategy_state_of(match.session)
            _ct_mis = getattr(_st_mis, 'cw4_counters', None)
            if isinstance(_ct_mis, dict):
                _ct_mis['s1_reset_mischannel'] = \
                    _ct_mis.get('s1_reset_mischannel', 0) + 1
    if _ok and isinstance(action, BuyCard) and action.card.name:
        strategy_state_of(match.session).cw4_visit_bought_names.append(action.card.name)
        # 效果账本购买计数推进(迁移批次三,设计 §5.1「刷新=计数累加」的
        # 购买侧;载体 = CounterKey.BUY,§5.3 返利族「每购 3 张 5 费」计数
        # 面)。挂点 = 执行落地门(未落地不计数,同刷新计数组纪律)。
        # best-effort 记录面,失败不阻塞执行回执链。
        try:
            from sr_od.application.currency_war.kernel.cw_board_state import (
                board_state_of,
            )
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                CounterKey,
            )
            board_state_of(match.session).effects.bump_key(CounterKey.BUY)
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-buy] 效果账本 BUY 计数失败(不阻塞): {e}')
    if _ok and isinstance(action, RefreshShop):
        # 刷新执行事实组接线(迁移批次二,设计 §3.3.6-§3.3.8;写入=仅逻辑,
        # 记录挂执行回执点 = 落地门,未落地不计数)。免费帧闸(§3.3.7 申报):
        # 免费帧不进付费计数;免费判定输入 = 刷前按钮态真值优先(T-13 真值
        # 通道,下方),失读回退免费刷新余额(效果账本激活面;余额未建模局
        # 恒 paid = 接线前保守形态)。
        # shop_refresh_cost 本口不写(§3.3.4 写端=现场 OCR 唯一;免费帧
        # 「免费」读数 OCR 为 None → 喂入口 carried,不落 0,免费帧不写闸
        # 由观察通道结构性满足)。
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of,
            record_refresh_execution,
        )
        _bs = board_state_of(match.session)
        _logic_bal = _bs.free_refresh_balance.value
        # 免费判定(§4.2 RefreshShop 行)真值优先(T-13 真值通道):刷前
        # 按钮态 UI 读数在场即按 UI 事实(观察赢,fields.md §2.3)——覆盖
        # 逻辑账未建模的授予/回收形态(概率事件 45% proc 不进余额账、高效
        # 决策 45s 窗到期清零无逆向桥)。失读(None)回退逻辑账 = 接线前
        # 保守形态,行为逐位不变(§4.2「余额未建模局恒 paid」)。
        _truth = getattr(ledger, 'refresh_free_truth', None)
        _free = _truth if _truth is not None else (_logic_bal or 0) > 0
        if _truth is not None and _truth != ((_logic_bal or 0) > 0):
            # 真值↔逻辑账分歧票(零决策留证):记账已按真值,分歧 =
            # 发放/回收链建模缺口信号(欠发=真免费∧账空;幽灵=账>0∧UI 付费)。
            defects.record_defect(
                'shop_refresh', 'free_truth_logic_divergence',
                expected=(f'按钮真值 free={_truth} 与逻辑账余额'
                          f'({_logic_bal})判定一致'),
                observed=(f'按钮真值 free={_truth} vs 逻辑账判定 '
                          f'free={(_logic_bal or 0) > 0}(余额={_logic_bal})'),
                plane=getattr(_cur, 'plane', 0) or 0,
                round_num=getattr(_cur, 'round_num', 0) or 0,
                verdict='留证-免费真值与逻辑账分歧(观察赢,按真值记账)',
                reader_source='shop_refresh_button_truth',
                note='T-13 真值通道接线票;欠发查授予桥漏型,幽灵查窗期回收')
        record_refresh_execution(
            _bs, free=_free,
            frame=f'p{getattr(_cur, "plane", 1) or 1}-r{getattr(_cur, "round_num", 1) or 1}')
        # 次数余量联动票(T-13 机制语义):免费态 UI 次数 vs 逻辑账刷前值
        # (两者同帧口径——UI 快照与余额读数都在点击前;失配 = 发放链或
        # 消耗链漂移的唯一在环检测位,零决策留证)。
        _ui_n = getattr(ledger, 'refresh_free_remaining_truth', None)
        if _free and _ui_n is not None and _logic_bal is not None \
                and _ui_n != int(_logic_bal):
            defects.record_defect(
                'shop_refresh', 'free_balance_ui_mismatch',
                expected=f'UI 剩余次数={_ui_n} == 逻辑账余额={int(_logic_bal)}',
                observed=f'UI 剩余次数={_ui_n} vs 逻辑账余额={int(_logic_bal)}',
                plane=getattr(_cur, 'plane', 0) or 0,
                round_num=getattr(_cur, 'round_num', 0) or 0,
                verdict='留证-免费刷新余额联动不符(零决策)',
                reader_source='shop_refresh_button_count',
                note='T-13 次数余量联动票;发放桥(固定理财/大裁员/加油站/'
                     '本金充裕条件族)与消耗闸的漂移归因入口')
        # 效果账本刷新计数推进(迁移批次三,§5.1「刷新=计数累加」;载体 =
        # CounterKey.REFRESH,§5.3 采购专员族门槛 7/5 计数面)。同挂执行
        # 落地门;best-effort 记录面。
        try:
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                CounterKey,
            )
            _bs.effects.bump_key(CounterKey.REFRESH)
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-buy] 效果账本 REFRESH 计数失败(不阻塞): {e}')
    if _ok and not _aop.terminal:
        from sr_od.application.currency_war.kernel.cw_board_state import (
            bench_slots_of as _sg_slots,
        )
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of as _sg_bs,
        )
        _skip_guard = (isinstance(action, BuyCard)
                       and bench_occupied(
                           _sg_slots(_sg_bs(match.session)))
                       >= BENCH_CAPACITY)
        _proj = _aop.project(_cur)
        # 商店动作投影直写·容器通道(波 4 黑板容器化步 1:投影直写接线,
        # 设计件《商店黑板容器化方案》§2.4-1;黑板帧投影 _proj 同步保留
        # = 读写双轨过渡,黑板槽仍供旧读者,步 2 读者切换后槽退役)。
        # 写序申报:本口先写(含 bench 简单落位),下方升星整表直写后写
        # 覆盖(后写赢)——两写合计对 simulate 输出等价(设计件 §4-M1)。
        # 执行回执(设计件 §2.1-2):k = 执行侧实购张数(merge_buy_k 计数,
        # ledger.buy_purchases 执行落地事实);LevelUpShop 单动作形态恒
        # 1 击;非买/升动作无执行期决定量(空回执)。
        from sr_od.application.currency_war.kernel.cw_board_state import (
            ChannelSig as _ProjSig,
        )
        from sr_od.application.currency_war.kernel.cw_board_state import (
            ShopActionExecuted as _ShopExecuted,
        )
        from sr_od.application.currency_war.kernel.cw_board_state import (
            apply_shop_action_logic as _apply_shop_logic,
        )
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of as _bs_of_proj,
        )
        _bs_proj = _bs_of_proj(match.session)
        _executed = _ShopExecuted()
        if isinstance(action, BuyCard):
            _k = 1
            if ledger.buy_purchases \
                    and (ledger.buy_purchases[-1].name or '') \
                    == (getattr(action.card, 'name', '') or ''):
                _k = max(1, int(ledger.buy_purchases[-1].count or 1))
            _executed = _ShopExecuted(bought_count=_k)
        elif isinstance(action, LevelUp):
            _executed = _ShopExecuted(levelup_clicks=1)
        _apply_shop_logic(
            _bs_proj, action, executed=_executed,
            produced_by=type(action).__name__,
            sig=_ProjSig(family='logic_action', actor='CwOpBuyCards',
                         mode='compute',
                         group_id=f'act:CwOpBuyCards@{_bs_proj.write_seq + 1}'))
        if isinstance(action, BuyCard) and _proj is not None:
            # 合成升星逻辑直写(§3.2.18 窟窿一修法 a;两态制 ADR-0651:
            # expect/confirm 两步废除,推算值直接写字段):BuyCard 投影
            # 发生 3 合 1 升星 → 投影 bench 视图经 write_logic 直写
            # (source=logic,策略器立即可读);下一备战帧实读照常覆盖
            # (观察赢),失配 = 投影模型 bug,缺陷台账留证后修推算代码。
            # last-wins:同段级联合并只留末张投影。纯记录面,决策零影响
            # (bench 为消费视图透传域,§8.7 批次二 as-built)。
            from sr_od.application.currency_war.kernel.cw_board_state import (
                ChannelSig,
                bench_view_of_slots,
                board_state_of,
                detect_merge_upgrade,
            )
            if detect_merge_upgrade(_cur, _proj):
                _bs_m = board_state_of(match.session)
                _bs_m.write_logic(
                    _bs_m.bench, bench_view_of_slots(_proj.bench),
                    produced_by='BuyCard',
                    sig=ChannelSig(family='logic_action', actor='CwOpBuyCards',
                                   mode='compute',
                                   group_id=f'act:CwOpBuyCards@{_bs_m.write_seq + 1}'))
        match.session.shop_state_frame = _proj
        _post_frame = _proj
        if not _skip_guard:
            # 守卫输入 = 容器(W6 波 4 读者切换;期望态读值经投影口直写
            # 的容器 bench,payload 域集同源;帧 _proj 保留 = 日志遥测)
            from sr_od.application.currency_war.kernel.cw_board_state import (
                board_state_of as _gt_bs,
            )
            from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
                guard_expected_vs_tracked,
            )
            guard_expected_vs_tracked(_gt_bs(match.session), match.session)
        ledger.refresh_first_action = False
    # 遥测(T-113/ADR-0579):逐动作执行回执行(op_journal.jsonl;全量叶级
    # delta 零漏报)。置于投影之后:_post_frame = 本动作后的期望态帧,防取到
    # 上一段陈旧帧。CloseShop 终结不入行(ADR-0518 行形态契约);未执行动作
    # 零行的语义由调用点保证(闸拒/硬墙 break 在本函数之前)。
    if not getattr(_aop, 'terminal', False):
        try:
            from sr_od.application.currency_war.telemetry.op_journal import (
                record_action_journal,
            )
            record_action_journal(match, action, len(visit_actions), _ok,
                                  _cur, _post_frame)
        except Exception:   # noqa: BLE001  journal best-effort
            pass


def accrue_release_spent(match: 'CurrencyWarMatch',
                         action: 'BuyCard | RefreshShop | SellBench | LevelUpShop | CloseShop',
                         ok: bool, state: GameState) -> None:
    """v3_release_spent 执行回执位记账(T-88 写点;裁决 = ADR-0571)。

    首版口径 = **只计刷新实花**(「宁窄勿虚」的遥测诚实性选择:买牌/
    升级是否计入「义务实花」全渠道口径在 mandate_v1 语义下未经证明,
    混入会虚高——扩口径挂 ADR-0571 待裁)。刷新单通道前提:R1 = 今日
    唯一刷新发射点(kernel/cw_state.RefreshShop.reason 值域契约)。
    记账位语义 = 动作执行成功回执(本函数在 apply_action_outcome 之后
    调用),决策帧值 = 轮内截至采样时点累计(schema 同款声明)。

    F4 栈守卫:仅当披露面轮键戳 == 当前 (plane, round)(即 mandate_v1
    本轮 prep 装配已跑)才累计——非 mandate_v1 栈(异型策略状态对象无
    键戳)或键戳过期帧不累计,防「spent>0 而预算三字段=None」的混合行
    形态(recorder「default 栈帧无写点 → None 语义」声明)。字段经防御
    getattr 访问(披露面形态;ADR-0563 B4 收缩申报)。
    """
    if not ok or not isinstance(action, RefreshShop):
        return
    st = strategy_state_of(match.session)
    key = (int(getattr(state, 'plane', 0) or 0),
           int(getattr(state, 'round_num', 0) or 0))
    if getattr(st, 'v3_disclosure_key', None) != key:
        return
    st.v3_release_spent += max(0, int(getattr(action, 'cost', 0) or 0))


def note_shop_action_receipt(match: 'CurrencyWarMatch', action: 'Action', *,
                             applied: bool, reason: str = '',
                             extra: dict | None = None) -> None:
    """商店动作执行回执(R2 §3.2.5;receipts 域,渠道② logic_action)。

    run_buy_waves 的**单一写点**:逐动作执行落地挂点 + 受阻挂点(刷新
    硬墙跳过 / spend_gate 政策闸拒)都经本函数落一条回执行(每动作 op
    一条 logic_action 行;受阻 = applied=false + reason + 执行面结构化
    字段——exec_events「受阻/放弃可见」收编)。发出即簿记非验证(M1③):
    applied = 动作 op 自身机械事实透传,零成败判定。journal 常开(ADR-0634)
    回执写入无条件,无局跳过在
    kernel 口(:func:`~...kernel.cw_board_state.note_action_receipt`);
    best-effort 不阻塞循环。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_board_state import (
            note_action_receipt,
        )
        session = getattr(match, 'session', None)
        if session is None:
            return
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of,
        )
        note_action_receipt(
            board_state_of(session), op=type(action).__name__,
            applied=bool(applied), reason=reason, screen=SHOP_SCREEN_NAME,
            actor='CwOpBuyCards', extra=extra)
    except Exception as e:  # noqa: BLE001  回执失败不阻塞循环
        log.warning('[cw][receipt] 商店动作回执写入失败(不阻塞): %s', e)


def run_buy_waves(op: SrOperation, match: 'CurrencyWarMatch | None',
                  hp_value: int | None, hp_readable: bool,
                  hp_trusted: bool,
                  *, spend_gate: Callable[[object], tuple[bool, str]] | None = None,
                  ) -> tuple[OperationRoundResult | None,
                             BuyCardsOutcome | None]:
    """商店单动作循环主体(ADR-0517 迁移批;前身份 = 买牌波循环)。

    ``spend_gate``(缺省 None = 既有行为零漂移):可选单动作政策闸,发射帧
    受限消费仲裁消费(出口 B;kernel 判定单一源 =
    ``kernel/cw_launch_arbitrage.launch_arbitration_gate``,ADR-0566)。
    语义 = 逐动作执行前咨询;``(False, why)`` ⇒ 该动作**不执行**、本访问
    即刻收工(拒绝语义 = 消费终止非跳过续试:跳过高位动作改试低位 = 重排
    既有评估序,违金出口族红线 5)——与既有 MAX_REFRESH 硬墙同为「终结
    降级关店」路径,关店由编排壳承担。闸自身遥测由闭包侧计数,本函数
    零感知闸语义。

    一次画面访问 = 轮「入口观察 + 逐动作决策循环」(ADR-0517 决策 1):

    - 入口观察(段顶,唯一读屏点):真实读屏 → 融合(hp/node_type/dual/
      gold 救援/tracked 播种)→ 生成期望态(``session.shop_state_frame``);
    - 决策循环(零读屏,决策 1/8):``decide_shop_action`` 每次恰返回一个
      动作 → 守卫断言(proposal-vs-expected + expected-vs-tracked 双账,
      ``cw_shop_action_ops``)→ 执行(动作 op ``execute``,观测通道候选 a
      遥测在内)→ ``project`` 纯计算更新期望态;
    - 终结 op(RefreshShop/CloseShop):执行即本段结束。刷新终结 = 交回
      外循环重进——物理载体 = 本函数段循环的下一次迭代(入口观察重建,
      读屏次数与波批持平,ADR-0517 §读屏成本·节奏对拍);关店终结 = 本
      访问收工(关店点击由编排壳 CwOpCloseShop 承担)。MAX_REFRESH 硬墙
      重定位 = 执行侧 visit 级计数(``ledger.total_refresh``,§3.1 候选
      (a) 同款防线:防「终结→重进→再刷新」无进展环)。

    hp 三件组来自调用方的 shop 关闭帧读链(W970 §4.3.4:商店开态 HP 区
    不可读),段顶 read_game_state 后经 :func:`_apply_hp` 值位同写覆盖。

    match=None(独立 run_operation 调本 op)→ 临时 match,不挂 ctx
    (局外不复用)。config 本函数内构造(W970 §4.3.4)。

    返回 (失败 round 结果, 产出)。正常收工 → (None, outcome);
    未识别卡停机钩子触发 → (round_fail 留证结果, None)。
    """
    from sr_od.application.currency_war.kernel.cw_state import (
        CloseShop,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopExecEnv,
        ShopVisitLedger,
        guard_proposal_vs_expected,
        shop_action_op_for,
    )

    config = CurrencyWarConfig(op.ctx.current_instance_idx)
    if match is None:
        # 防御:无对局态(独立 run_operation 调本 op)→ 临时 match,不挂 ctx(局外不复用)
        # (防御具现 = 活策略核 mandate_v1,与生产注册面同源;统一迁移批重指向)。
        # 该路径经 create_session 冷建(ADR-0583:live 初值 v3_phase='FORM'
        # 随唯一冷建口在此落位,旧 on_match_start 写点已删;phase 列仅诊断用)。
        from sr_od.application.currency_war.strategies.impl.cw_strategy import (
            CurrencyWarMatch,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            MandateV1Strategy,
        )
        _def = MandateV1Strategy()
        match = CurrencyWarMatch(_def, _def.create_session(config))

    # 牌位/升级/刷新中心从 screen_info 读(缺失兜底)。方向视图由策略器
    # 决策入口内化刷新(帧代次标注触发,ADR-0583)。
    click_pts = shop_card_click_points(op.ctx)
    level_btn = area_center(op.ctx, BUY_EXP_AREA) or LEVEL_UP_FALLBACK
    refresh_btn = area_center(op.ctx, '按钮-刷新', SHOP_SCREEN_NAME) or REFRESH_FALLBACK

    ledger = ShopVisitLedger()
    # T-82 段序号置位(商店 visit 开始;发射帧仲裁段消费 = 本函数带
    # spend_gate 的调用,共用本入口,两类段一并推进):visit = 腾席拒绝
    # 结论的输入不变性段,入口 +1 使上一 visit/上一域(备战)残留的
    # 续段 token/结论闩按序号不等自动失效(跨 visit/跨战斗伪命中封死)。
    # 状态对象缺席(第三方策略面/桩)= 无缓存载体,跳过置位(B4 缺席
    # 退缺省口径,决策核侧冷建自 0 起 = 恒重推导,保守端安全)。
    _st_seg = strategy_state_of(match.session)
    if _st_seg is not None:
        _st_seg.cw4_segment_serial += 1
    # 对拍基线 = 开店首读金:首段循环顶读、任何动作执行前快照(含假 0
    # 救援后的值)。末段重读值已净含各段花销,当基线会与全程动作账双重相减。
    gold_open: int | None = None
    _buy_baseline = op.screenshot()
    # `w536_merge_expect/`:买牌期望态基座(pre 快照 = 单元执行前 tracked)。
    _buy_pre_bench = deepcopy(exec_state_of(match.session).tracked_bench_chars)
    _buy_pre_deployed = deepcopy(exec_state_of(match.session).tracked_deployed)
    # 执行边界压缩:首段入口观察已带全量语境(替代原开店后独立读);
    # _entry_frame_marked = visit 首段已标 full(续段标 none,连击续刷判定输入
    # 所在的段循环共用此分段);
    # _prev_refresh_only = 上一段是「仅刷新段」(连击续刷判定输入,
    # 判据单一源 = refresh_wave_is_refresh_only)。
    _entry_frame_marked = False
    _prev_refresh_only = False
    state: GameState | None = None
    for _ in range(MAX_REFRESH + 1):
        ledger.refresh_first_action = True   # 段级复位(仅刷新段判定输入)
        # did_refresh 段级复位(终结 op 语义 review 修复批暴露):两消费点
        # (段尾 _prev_refresh_only / did_refresh=False 收工判定)语义都是
        # 「本段」——不复位时首段刷新后的所有后续段都被陈旧 True 钉住,
        # 段循环跑满 range(MAX_REFRESH+1) 不收工(终结 break 落地后每段
        # 恰一刷新,该残留即显形;修复前被「段内连刷至硬墙」形态掩盖)。
        ledger.did_refresh = False
        if not _prev_refresh_only:
            time.sleep(0.3)  # 等 board 面板 settle(连击续刷段前一动作是刷新,面板未变,跳过)
        # 光标 parking(审计 P0,2026-08-16):上轮 BuyCard/LevelUp/Refresh 点击后光标停在按钮上
        # → 污染本帧 read_game_state;park 后再读。
        op.park_cursor(after_wait=0.1)
        # ---- 入口观察(ADR-0517 决策 1/8:唯一读屏点,即对账)----
        # 观察源端口改道(T-120 方案 §2.3/§3.3,批 1;封闭集登记 =
        # sr-od-test test_cw_game_ports 改道集守卫):端口在场(假环境)
        # 时入口观察 = observe_prep 状态真值直出,跳过读图;缺省 None =
        # 生产真实读屏,行为逐位不变。
        _src = observation_source()
        _entry_shot = op.screenshot()
        state = (_src.observe_prep(op.ctx, PHASE_PREP_SHOP_OPEN).state
                 if _src is not None else
                 read_game_state(op.ctx, _entry_shot,
                                 phase=PHASE_PREP_SHOP_OPEN))   # ADR-0462 开店动作期
        save_decision_frame(op, 'shop_entry', _entry_shot)   # 识别完成点原始帧留证(牌面仲裁基准;每段一帧,刷新重观察同点覆盖)
        _apply_hp(state, hp_value, hp_readable, hp_trusted)   # shop 开帧 hp 区空 → 用 shop 关闭帧值覆盖
        # 店开帧节点行被遮 node_type 恒 None → 查位面节点序列台账(键 =
        # 本帧 phase_round 现读的 (plane, round),写入端=位面详情采集/投资
        # 环境后重读,结构上不可能滞后)。ADR-0587:旧实现无条件拷
        # session.last_node_type,该值唯一写点(备战环 heavy 观察)节拍天然
        # 晚于本轮店开,拷到的恒为上一轮值——曾以滞后奖励值误开 ②(b) 并
        # 误抑制 M3 升级。查不到(台账缺档/续局未随局建/位次越界)→ 保持
        # None fail-open:②(b) 不发射(ADR-0580 None 语义),死金域义务由
        # 节点无关的 ②(a) 备战凑息承载;禁再退回 last_node_type 滞后拷贝
        # (连续硬节点段靠它侥幸开门的形态=有意变 None 关门,ADR-0587)。
        _ledger_node = ledger_node_type(match.session, state.plane,
                                        state.round_num)
        if _ledger_node is not None:
            state.node_type = _ledger_node
        # r73 review RC3 修:dual 态单一源挂 session,循环态每段拷贝;读端 =
        # R1 唯一合法读端 committed_from(蓝图 §4.3,禁 session 直读散落)。
        from sr_od.application.currency_war.kernel.cw_intention import (
            committed_from,
        )
        state.dual_track_phase = not committed_from(match.session)
        if getattr(strategy_state_of(match.session), 'transition_framework', ''):
            state.focus_factions = getattr(strategy_state_of(match.session), 'focus_factions', set())
        # gold-robust:gold 数字 stylized,paddle OCR det 间歇漏 → 读 0 时重读几帧取首个 >0。
        # 观察冲突审计 #6:救援结果留证(救回/连读 0 统计,为 gold 双源排期供数据)。
        if state.gold == 0:
            _gold_rescued = None
            for _ in range(4):
                time.sleep(0.4)
                gv = read_gold(op.ctx, op.screenshot())
                if gv > 0:
                    state.gold = gv
                    _gold_rescued = gv
                    break
            from sr_od.application.currency_war.kernel.cw_observe import (
                obs_conflict,
            )
            obs_conflict('gold', 0, _gold_rescued if _gold_rescued is not None else 0,
                         None, verdict=('采新-救援成功(首读假0,stylized漏)' if _gold_rescued is not None
                                        else '确认真0(4帧连读0)'),
                         source='shop_rescue')
            # gold 救援喂入口写(波 4 黑板容器化,设计件《商店黑板容器化
            # 方案》§2.4-4:gold 救援保留——识别质量机制非黑板拷入,结果
            # 经既有观察喂入口写 bs.gold,禁静默丢失)。首读假 0 已由观察
            # 漏斗 observe 落容器,救援值同渠道覆盖(观察赢,来源同级)。
            if _gold_rescued is not None:
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    ChannelSig as _RescueSig,
                )
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    board_state_of as _bs_of_rescue,
                )
                _bs_rescue = _bs_of_rescue(match.session)
                _bs_rescue.observe(
                    _bs_rescue.gold, int(_gold_rescued),
                    evidence='gold_rescue:shop_first_read_fake_zero',
                    sig=_RescueSig(family='obs', actor='CwOpBuyCards',
                                   mode='read',
                                   group_id=(f'obs:CwOpBuyCards@'
                                             f'{_bs_rescue.write_seq + 1}')))
        # 开店首读金快照(仅首段;救援后取值——救援值比假 0 更接近真值)
        if gold_open is None:
            gold_open = state.gold
        # 播种单一源 = tracked_bench_chars(带 star+merge,mutate/对账全程同步)。
        # 空 = bench 真空(全部署/合成清空的事实正确态),不回退任何残账——
        # 旧 tracked_bench 回退分支已退役:单动作架构下「首轮」场景由入口
        # heavy 读屏重建(ADR-0517 决策 8,入口观察即对账);残账仅 BuyCard
        # 追加、无人清理,回退会复活陈旧名(实证 = 2026-09-05 OpenShop
        # 双账分叉事故,诊断档
        # .debug/temp/currency_war/20260905_openshop_fork_diag/report.md)。
        # (tracked 播种已随 W6 波 4 黑板容器化取消——设计件 §2.1-5:容器
        #  bench = prep 帧观察值(观察漏斗写端)+ visit 内投影直写;黑板帧
        #  播种的唯一消费者 = 旧帧决策链,读者切换后无行为面。)
        if exec_state_of(match.session).tracked_bench_chars:
            log.info(f'[cw] tracked_bench_chars='
                     f'{[(c.char_id, c.star) for c in exec_state_of(match.session).tracked_bench_chars if c is not None]}'
                     f'(播种取消,仅日志显影)')
        # T-308 S3:播种期布局代次快照(单动作循环每动作消费前检差用;
        # 空播种段同样取值——检差面不依赖是否播种)。
        _seed_epoch = exec_state_of(match.session).bench_layout_epoch
        match.session.last_state = state
        # 黑板写路径(W971 §2,P2):入口观察态(牌面现读+hp 覆盖+node_type/
        # dual/focus 拷入+gold 救援+tracked 播种 + 单动作投影段)直写
        # session.shop_state_frame——W6 波 4 起决策读者已切容器(本写退化为
        # last_state 遥测载体,槽本体退役挂步 4);容器写端 = 观察漏斗
        # (_feed_board_state observe)+ gold 救援喂入口写 + 执行落地门投影。
        match.session.shop_state_frame = state
        from sr_od.application.currency_war.kernel.cw_board_state import (
            board_state_of as _bs_of_entry,
        )
        from sr_od.application.currency_war.kernel.cw_board_state import (
            synthesize_from_game_state as _syn_entry,
        )
        _bs_of_entry = _bs_of_entry(match.session)
        # 容器入口喂入(生产同路 = sim 合成口):决策读者已切容器,黑板帧
        # 写不再承载决策输入——假环境(sim 适配器直驱,不经 read_game_state
        # 漏斗)此位无漏斗写端,必须显式合成,否则在屏前置 shop=None 抛错。
        _syn_entry(_bs_of_entry, state)
        # 帧代次标注(ADR-0583 §3.4):visit 首段入口观察 = full(方向视图
        # 由 decide_shop_action 入口消费刷新);续段刷新重观察 = none
        #(= 旧 _target_seeded「仅首段重估」语义,段内视图不随买入漂移)。
        match.session.shop_frame_class = (
            'full' if not _entry_frame_marked else 'none')
        _entry_frame_marked = True
        # 店开观察帧披露覆写(T-88 双写第二写点;ADR-0571 §2.2):prep
        # 装配帧关店态 gold 过 F2 门不可得 ⇒ overflow/budget 在 prep 快照
        # 恒 0(金未采语义);此处店开帧 gold 为真值,同一 BudgetView 链
        # 覆写三预算字段(overflow/budget=帧现值;键戳同轮不清 spent,
        # 轮界清零由键戳承载)。遥测 best-effort:失败降级保留 prep 帧值
        # 不阻塞动作循环,warning 留痕(防无声退化 no-op,锚⑤缺陷无声
        # 复发)。
        try:
            from sr_od.application.currency_war.strategies.impl.mandate_v1.assembly import (
                disclose_budget_at_shop_frame,
            )
            disclose_budget_at_shop_frame(
                state, match.session,
                registry=getattr(getattr(match, 'strategy', None),
                                 'registry', None))
        except Exception:  # noqa: BLE001  遥测 best-effort(降级留痕)
            log.warning('[cw][shop] 店开帧预算披露覆写失败(降级保留 prep 值)',
                        exc_info=True)
        # 本访问已买件(carried 融合:R2-N1 刚买件首卖偏好)段级清零。
        strategy_state_of(match.session).cw4_visit_bought_names = []
        # (期望态覆盖点·商店段顶的对账块已随 ADR-0651 两态制废除:金账
        #  delta 为逻辑直推字段,本帧 state.gold 实读即观察覆盖真值,
        #  失配 = 推算 bug,缺陷台账留证——无挂账对账环节。)
        # (r97 供给快照行已随 shop_snapshots 流写入端退役删除——删除波 1;
        #  牌面真值现役归宿 = journal 快照行自带 shop 域。)
        # A2:target 由策略器状态管理(方向刷新写,ADR-0583 内化)。
        _tc = getattr(strategy_state_of(match.session), 'target_comp', None)
        target_name = _tc.name if _tc is not None else ''
        _fp_v = _form_progress(_tc, state) if _tc is not None else -1.0
        # r295(判读必须看节点类型):state 行带 node(本节点类型)+next。
        _node = getattr(match.session, 'node_type_current', None) or '?'
        _upc = getattr(match.session, 'upcoming_types', None) or []
        _next = _upc[0] if _upc else '?'
        log.info(f'[cw] state gold={state.gold} hp={state.hp} lv={state.level} '
                 f'plane={state.plane} round={state.round_num} node={_node} '
                 f'next={_next} board={state.board} '
                 f'target={target_name!r} fp={_fp_v:.2f} bench={bench_occupied(state.bench)}')
        # (决策行披露值构造块 _cand/_eb/_extra 与统一 state 段入口版本钉
        #  _seg_pin_version 已随 decisions 流写入端退役删除——删除波 1;
        #  日志披露行(上方)保留。)
        # ---- 单动作决策循环(ADR-0517 决策 1/2;循环内零读屏)----
        # 播种期对账(守卫两属消息分离的判定序):首动作前先对一次账,
        # 分叉在此出现 = 归「播种/入口账分叉」;此后投影后出现的分叉才归
        # 「project/mutate 模型分叉」(2026-09-05 OpenShop 事故:播种层
        # 双源分叉曾被投影消息误标,误导排查方向)。
        from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
            guard_expected_vs_tracked as _guard_seed,
        )
        # 对账守卫输入 = 容器(W6 波 4,设计件 §2.5-2:期望态读值改
        # 容器;tracked 播种取消后分叉归因「播种/入口账 vs 模型」语义不变)
        _guard_seed(_bs_of_entry, match.session, stage='seed')
        visit_actions: list = []
        _seg_frames = 0
        while True:
            _seg_frames += 1
            # T-308/ADR-0646 S3 布局代次检差(每动作消费前):命中 = visit 内
            # 布局已重排(reconcile 纠漂递增 epoch),已发射动作的 bench_idx
            # 代际失效,不可只换 state.bench → 三步:①截断在飞计划(dd-020
            # 截断语义,plan_truncated 记账)→ ②按 tracked 重播种(helper
            # 内含槽号健康门)→ ③重入决策(decide 消费重播种后黑板帧)。
            # 重播种被健康门拒绝 = 布局不可信 → fail-stop 本段收工交回外
            # 循环重观察(dd-020 fail-stop 语义;禁在不可信布局上继续发射)。
            from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
                reseed_bench_if_layout_stale,
            )
            # 重播种写目标 = 容器 bench 域(设计件 §2.3 reseed 写点;
            # 输入改容器单例,投影帧不再承载 bench)
            _stale = reseed_bench_if_layout_stale(_bs_of_entry,
                                                  match.session,
                                                  _seed_epoch)
            if _stale == 'reseeded':
                _seed_epoch = exec_state_of(match.session).bench_layout_epoch
                ledger.plan_truncated = True
                log.warning('[cw!][plan] 布局代次检差命中:在飞计划截断(dd-020),'
                            '已按 tracked 重播种投影 bench,重入决策')
                continue
            if _stale == 'failed':
                ledger.plan_truncated = True
                log.warning('[cw!][plan] 布局代次检差命中但重播种被槽号健康门'
                            '拒绝 → fail-stop 本段收工,交回外循环重观察')
                break
            # 帧序推进(T-113/ADR-0579):段序号与 decisions 行同源,动作行
            # frame_seq 关联键读取端(op_journal.current_frame_seq)。
            from sr_od.application.currency_war.telemetry.op_journal import (
                advance_frame_seq as _adv_seq,
            )
            with contextlib.suppress(Exception):
                _adv_seq()
            if _seg_frames > SHOP_SEGMENT_ACTION_CAP:
                # 防御帧帽(对抗发现:决策循环不收敛的响亮暴露——禁静默续跑/
                # 禁吞异常续跑。收敛根因修复在决策侧席位门,本帽 = 执行
                # 侧最后防线,与 prep 线 VISIT_ACTION_CAP 同构但更严:
                # 商店段动作单价高(买/卖不可逆),超帽不交回外循环重试)。
                # 帧帽诊断读 = 容器(W6 波 4 读者切换,设计件 §2.4-2)
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    bench_slots_of as _bslots_of,
                )
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    board_state_of as _bcap_of,
                )
                from sr_od.application.currency_war.kernel.cw_board_state import (
                    gold_of as _gold_of,
                )
                _st_cap = _bcap_of(match.session)
                _msg = (f'[cw!][plan] 决策循环帧数超帽'
                        f'({SHOP_SEGMENT_ACTION_CAP}),疑投影/策略器不收敛'
                        f'(末态 gold={_gold_of(_st_cap)} '
                        f'bench={bench_occupied(_bslots_of(_st_cap))})')
                log.error('%s', _msg)
                raise RuntimeError(_msg)
            # r95 审计必修②:决策异常留证(完整栈到 log,再向上抛,行为不变)。
            try:
                action = match.strategy.decide_shop_action(match.session,
                                                           config)
            except Exception:
                import traceback

                _tb = traceback.format_exc()
                log.error('[cw!][plan] decide_shop_action 异常(留证后上抛):\n%s', _tb)
                raise
            if isinstance(action, CloseShop):
                # 恒可用终结:本段收工(关店由编排壳承担)。CloseShopOp.execute
                # 是 no-op,此处提前退出与「execute 后按 terminal 统一 break」
                # 行为等价;保留 execute 前落点是有意声明——保持 decisions
                # 行形态契约(CloseShop 终结不入行,ADR-0518 §decisions 遥测行,
                # 安灯/判读输入面)。可执行终结(RefreshShop/CompTransaction)
                # 的统一退出在 execute 之后(下方 _aop.terminal 分支),两条路径
                # 承载同一语义「终结 = 本段结束」,非双轨。
                break
            if isinstance(action, RefreshShop) and ledger.total_refresh >= MAX_REFRESH:
                # 硬墙重定位(ADR-0517 §3.1 候选 (a)):visit 级刷新计数超墙
                # ⇒ 终结集降级为仅关店。硬墙跳过=计划了但未尝试,可见化
                # 不停(`w577_refresh_fee_and_andon/`,局22 误停根因)。
                ledger.plan_truncated = True
                ledger.refresh_skipped = 'max_cap'
                # 受阻也簿记(R2 回执域):计划未尝试在账可见(exec_events
                # 词表「放弃」族;plan_truncated/refresh_skipped 结构化入回执)。
                note_shop_action_receipt(
                    match, action, applied=False,
                    reason='skipped:max_cap(刷新硬墙,计划未尝试)',
                    extra={'plan_truncated': True,
                           'refresh_skipped': 'max_cap'})
                break
            if spend_gate is not None:
                # 单动作政策闸(缺省 None 零漂移;发射帧仲裁专用,ADR-0566):
                # 拒 = 本动作不执行 + 本访问收工(消费终止语义,见签名注)。
                _g_ok, _g_why = spend_gate(action)
                if not _g_ok:
                    # 受阻也簿记(R2 回执域):闸拒动作在账可见(exec_events
                    # 词表「受阻」族;终止单发射帧受限消费的判读输入面)。
                    note_shop_action_receipt(
                        match, action, applied=False,
                        reason=f'blocked:spend_gate:{_g_why}',
                        extra={'blocked': 'spend_gate'})
                    break
            _cur = match.session.shop_state_frame
            # 守卫/env 读点 = 容器(W6 波 4 读者切换,设计件 §2.4-2:
            # guard_proposal_vs_expected 守卫输入 + ShopExecEnv.state
            # 改容器单例;帧 _cur 保留 = 投影/回执日志遥测,槽退役挂 S3)。
            from sr_od.application.currency_war.kernel.cw_board_state import (
                board_state_of as _bs_of_cur,
            )
            _cur_bs = _bs_of_cur(match.session)
            guard_proposal_vs_expected(action, _cur_bs)
            _aop = shop_action_op_for(action)
            _env = ShopExecEnv(
                op=op, match=match, config=config, click_pts=click_pts,
                level_btn=level_btn, refresh_btn=refresh_btn,
                ledger=ledger, state=_cur_bs)
            # 执行器端口改道(T-120 方案 §2.4/§3.3,批 1):端口在场(假
            # 环境)时动作落假游戏状态机(sink 账本位随动,机械点击层
            # 被替换);缺省 None = 生产真实执行,行为逐位不变。
            _sink = action_sink()
            if _sink is not None:
                _ok = _sink.execute_action(op.ctx, action, _env).applied
            else:
                _ok = _aop.execute(_env)
            # 执行落地回执(R2 回执域,逐动作 op 一条 logic_action 行):
            # applied = 动作 op 自身机械事实(未落地 = False + 摘要),
            # 发出即簿记非验证——本行零新增读屏零成败判定。
            note_shop_action_receipt(
                match, action, applied=bool(_ok),
                reason='' if _ok else f'执行未落地({type(_aop).__name__})')
            apply_action_outcome(_aop, action, _ok, _cur, match, ledger,
                                 visit_actions)
            # T-82 续段 token 写入(生产商店循环执行位):动作确认已执行
            # 后置位 (动作型名, 当前段序号);未执行路径(闸拒/硬墙/
            # CloseShop 提前退出)不写。策略器入口读后即清,下一帧据其
            # 判定 M2 停摆续段缓存命中。状态对象缺席 = 跳过(B4 口径)。
            if _ok:
                _st_tok = strategy_state_of(match.session)
                if _st_tok is not None:
                    _st_tok.cw4_frame_action_record = (
                        type(action).__name__, _st_tok.cw4_segment_serial)
            # 义务实花回执位记账(T-88;闸前不记——spend_gate 拒绝帧
            # 未执行,本位只在 execute 成功回执后累计,F4 栈守卫见函数注)。
            accrue_release_spent(match, action, _ok, _cur)
            if _aop.terminal:
                # 终结 op 统一退出(ADR-0517 决策 4/7;终结 op 语义 review
                # V1/V2 修复,P35 实证):终结动作 execute 后黑板不投影
                # (apply_action_outcome 对终结跳过,期望态按规格作废)——
                # 循环若不在此退出,下一帧 decide 读到的仍是刷前旧牌面,
                # 策略器(期望态的确定性纯函数)对旧牌面重发 RefreshShop
                # 连发至硬墙,或把旧牌面的 BuyCard 提案点在新牌面槽位
                # (错买随机卡)。break 后段循环下一次迭代的入口观察重建
                # 期望态 = 「交回外循环重进」的物理载体;RefreshShop 与
                # CompTransaction(终结邻接 fallback,禁半档中间态)同路径。
                break
        log.info(f'[cw] shop={[(c.faction, c.name, c.cost) for c in state.shop]} '
                 f'plan={[_fmt_action(a) for a in visit_actions]}')
        # (段尾 decisions 行已随 decisions 流写入端退役删除——删除波 1。)
        # ⚠️ equips 拷贝必须在决策循环之后(cw_comps 装备动态权重读
        # state.equips,提前拷=改决策行为,w222 遥测缺口①;原「决策之后」
        # 的时序锚 = 段尾 decisions 行,行退役后时序约束不变,落在段循环
        # 收尾处)。
        state.equips = list(getattr(match.session, 'last_owned_equips', []) or [])
        # 连击续刷判定输入:本段是否「仅刷新且真点击」。
        _prev_refresh_only = bool(
            ledger.did_refresh and refresh_wave_is_refresh_only(visit_actions))
        if not ledger.did_refresh:
            break   # 本段无刷新(或硬墙)→ 收工

    # [停机钩子·常驻兜底(od-dev-stop-hooks §2.1 分类;原「临时,采完删(用户
    # 2026-08-15 指示)」标注系误分类)]未购买(含刷新后仍未购买)且商店有
    # 未识别卡(SIFT miss)→ 停机留画面给 AI 建档。触发条件兜「商店出现
    # 未识别卡」整类(新版本新卡/非角色内容/立绘缺/瞬时帧)持续可能复发 =
    # 安全网;移除条件 = 未识别卡类建模收敛(见下方 flag 文字),平时触发
    # 只删 flag 不删钩子。
    # 📋 调研档案(2026-08-17 阮·梅/白厄单帧 miss 归因闭环,下次触发先读这段):
    # - 历史触发全部是刷新动画/settle 瞬时帧;本 hook 防抖重读两次均自愈。
    # - W944 治本(2026-08-31):blind sleep 改判据化自愈(_wait_shop_row_stable,
    #   与刷新分支同门同 rect);预算 2 次,耗尽才真停(模态弹窗压暗不因重读消失)。
    # - f570a76e 审查#1 修:去 total_buy 门——残缺牌面上的买牌决策同样要留证。
    if state is not None and any(not c.name for c in state.shop):
        _unk = [i + 1 for i, c in enumerate(state.shop) if not c.name]
        for _ in range(2):
            _wait_shop_row_stable(op)
            _reshop = read_shop_cards(op.ctx, op.screenshot())
            _unk = [i + 1 for i, c in enumerate(_reshop) if not c.name]
            if not _unk:
                log.info('[cw-shop][hook] 重读后全识别(动画/settle 瞬时)→ 不停机')
                break
        if _unk:
            # [停机钩子·恢复]r34 降级已被用户否决(2026-08-24:未识别不能
            # 降级,带病跑错过建档窗口)。代价已知会(阻断实跑),用户明示接受。
            _shot = op.save_screenshot(prefix=f'shop_unk_slot{_unk[0]}')
            from datetime import datetime as _dt
            _fp = get_project_root() / '.debug' / 'temp' \
                / 'currency_war' / 'shop_unk.flag'
            _fp.parent.mkdir(parents=True, exist_ok=True)
            _fp.write_text(
                f'[HOOK-STOP] shop 未识别卡停机钩子(常驻兜底,方案D恢复):'
                f'operations/cw_op/cw_op_buy_cards.py run_buy_waves\n'
                f'触发:未购买且商店槽{_unk}未识别(防抖重读 2 帧后仍 miss)——\n'
                f'   新版本新卡/昔涟诗篇类非角色内容/立绘缺。\n'
                f'处理步骤:1. 看 shot={_shot};对停机画面跑 analyze_screen\n'
                f'   + 离线 SIFT 对拍(真实rect 商店牌-1..5)确认真未知;\n'
                f'   2. 新卡 → 建档(screen_info/立绘库);瞬时帧类 → 调上方\n'
                f'   RefreshShop 后等待;3. 删本 flag(钩子保留)+ 重启 MCP server 重跑。\n'
                f'移除条件:常驻兜底——未识别卡类建模收敛(连续多局零触发)后按\n'
                f'   od-dev-stop-hooks §2.1 评估移除整段;平时触发只删 flag 不删钩子。\n'
                f'ts={_dt.now().strftime("%m-%d %H:%M:%S")}\n',
                encoding='utf-8')
            log.warning('[cw!] [shop] 未识别卡槽%s(重读后仍 miss)→ 停机留画面'
                        '待建档 shot=%s(用户裁决恢复:未识别不能降级)', _unk, _shot)
            op.ctx.run_context.stop_running(reason='hook:shop_unknown_card')
            return op.round_fail(status=f'shop 未识别卡槽{_unk},停机留证'), None

    # → 新占槽 = bought 卡落点(pixel-diff;两帧同 shop-OPEN 状态)。
    if ledger.bought_names:
        _after_shot = op.screenshot()
        _new_slots = new_bench_slots(op.ctx, _buy_baseline, _after_shot)
        # 买牌动画未收敛时首采误判「新占槽=0」→ 延迟重采一次(观测时序)。
        _new_slots, _ = bench_buy_slots_settle_retry(
            len(ledger.bought_names), _new_slots,
            lambda: new_bench_slots(op.ctx, _buy_baseline,
                                    op.screenshot()))
        if _new_slots and match is not None:
            _slot_map = dict(zip(ledger.bought_names, _new_slots, strict=False))
            if not hasattr(match, 'bench_slot_map') or match.bench_slot_map is None:
                match.bench_slot_map = {}
            match.bench_slot_map.update(_slot_map)   # 合并(跨回合累积),非覆盖
            log.info(f'[cw-shop] char→slot(pixel-diff,合并):{_slot_map} → 全 map={match.bench_slot_map}')
        # 买牌落位对拍(观测自检框架设计 §2.2;纯记账零决策):占位不出现
        # (买≥1 张而新槽=0)是设计点名的硬失败形态(gap_large);计数总账
        # 与身份回读是留证级。失败路径无 return/retry/屏蔽,买牌照常收工。
        with contextlib.suppress(Exception):
            _occ = bench_buy_occupancy_ok(len(ledger.bought_names), len(_new_slots))
            # refs 旧挂点清理(W7 refs 迁移):decisions 流已随删除波 1
            # 退役,改指 journal (run_id,v) 锚(plane/round/bought 数已在
            # 行参/expected/observed 内联)。
            _bench_refs = journal_refs()
            if _occ is False:
                _occ_shot = None
                with contextlib.suppress(Exception):   # 截图 best-effort
                    _occ_shot = op.save_screenshot(prefix='bench_buy_no_slot')
                defects.record_defect(
                    'bench', 'invariant_break',
                    expected=(f'买{len(ledger.bought_names)}张 → new_bench_slots '
                              '≥1 新占槽'),
                    observed=('pixel-diff 新占槽=0(占位不出现:点击落空/'
                              '动画帧误判基线帧)'),
                    plane=state.plane, round_num=state.round_num,
                    verdict='留证-买牌占位未出现(设计§2.2 硬失败形态;'
                            '复现升级由台账复现计数承载)',
                    shot=_occ_shot,
                    reader_source='bench_buy_pixel_diff',
                    gap_large=True, refs=_bench_refs,
                    note='观测自检框架设计 §2.2:占位不出现才算失败')
            _cnt = bench_buy_count_ok(len(ledger.bought_names), len(_new_slots),
                                      ledger.total_sell)
            if _occ is not False and _cnt is False:
                defects.record_defect(
                    'bench', 'invariant_break',
                    expected=(f'新占槽={len(ledger.bought_names)} − 中途卖出'
                              f'{ledger.total_sell} = '
                              f'{len(ledger.bought_names) - ledger.total_sell}'),
                    observed=f'pixel-diff 新占槽={len(_new_slots)}',
                    plane=state.plane, round_num=state.round_num,
                    verdict=('留证-落位计数不符(pixel-diff 不分方向,卖出/'
                             '合并槽变化计入,单元总账留证)'),
                    reader_source='bench_buy_pixel_diff',
                    gap_large=False, refs=_bench_refs,
                    note='观测自检框架设计 §2.2:新槽数累计=买牌数−中途卖出数')
            # 身份回读(留证级):SIFT 纯读走 identify_slots(不经
            # read_bench_chars,防其内置停机钩子误触)。
            _templates = ensure_portrait_templates(op.ctx)
            if _templates is not None:
                from sr_od.application.currency_war.obs.cw_identity_obs import (
                    _ctx_slots,
                    identify_slots,
                )
                _rb = identify_slots(_after_shot, _templates,
                                     _ctx_slots(op.ctx, '备战栏', 9), '')
                _missing = bench_buy_identity_missing(
                    ledger.bought_names, [c.char_id for c in _rb])
                if _missing:
                    defects.record_defect(
                        'bench', 'perception_conflict',
                        expected=f'回读身份含买牌名:{sorted(ledger.bought_names)}',
                        observed=(f'回读={sorted(c.char_id for c in _rb)};'
                                  f'未出现:{sorted(_missing)}'),
                        plane=state.plane, round_num=state.round_num,
                        verdict=('留证-身份回读未含买牌名(容未识别;'
                                 '占位已另判,不构成失败)'),
                        reader_source='bench_buy_sift_readback',
                        gap_large=False, refs=_bench_refs,
                        note='观测自检框架设计 §2.2:身份留证不算失败')

    outcome = BuyCardsOutcome(
        state=state, config=config,
        total_buy=ledger.total_buy, total_level=ledger.total_level,
        total_refresh=ledger.total_refresh, total_sell=ledger.total_sell,
        total_sell_income=ledger.total_sell_income,
        total_sell_skip=ledger.total_sell_skip,
        total_sell_fail=ledger.total_sell_fail,
        spend_executed=ledger.spend_executed,
        gold_open=gold_open, plan_truncated=ledger.plan_truncated,
        refresh_skipped=ledger.refresh_skipped,
        refresh_attempted=ledger.refresh_attempted,
        refresh_board_changed=ledger.refresh_board_changed,
        buy_purchases=ledger.buy_purchases, buy_has_sell=ledger.buy_has_sell,
        buy_unidentified=ledger.buy_unidentified,
        buy_pre_bench=_buy_pre_bench,
        buy_pre_deployed=_buy_pre_deployed,
        visit_actions=visit_actions)
    return None, outcome


class CwOpBuyCards(CwScreenOpBase):
    """备战-开商店原子 op:执行商店单动作循环(ADR-0517 迁移批;
    前身份 = 商店动作波循环,W970 批 A 契约 §4.2)。

    生产路径由编排壳直调 :func:`run_buy_waves`(宿主 op 复用,保证读屏
    次序/替身桩行为等价);本类为独立可跑壳(``run_operation`` 单跑定位
    失败步)。hp 三件组缺省 (None, False, False) = 无覆盖(商店开态
    HP 区本就不可读,单跑调试语义);生产入口必须传 shop 关闭帧读链产物。

    统一观察架构收编(B4 挂账批,账本 T-45):改挂 ``CwScreenOpBase``,
    ``buy`` 节点顶部装配点分流(架构设计 §9.1 并存纪律:两端口完整在场
    → ``run_lifecycle()``;缺省 None = 生产直连旧路径,原序列逐位保留,
    生产行为零变化)。变体形态申报 = **旧体委托**(直迁全五段的过渡
    替代):入口观察/播种对账/单动作决策循环全部住 :func:`run_buy_waves`
    段循环内(每段一次),本类不拆段循环——拆段会把「刷新终结交回重进」
    的物理载体(段循环下一次迭代,ADR-0517)改成节点重入、并连带改节点
    预算语义,违总纲契约 5 行为零变更红线;全五段直迁留待旧路径退役批。
    变体五段在本类的映射:observe/reconcile = 空申报(无独立早退面/
    对账面——两半住委托体内,非空决策合同声明)、decide/act 及其后 =
    决策循环段承载委托体(:func:`_buy_round` 单一共享,新旧路径同一份;
    策略消费在委托体内 ``decide_shop_action``,**不申报** B4 选项②空
    决策合同——与只读/导航变体的空申报语义区分)、on_outcome = 无登记件
    (注册表缺席 = 零动作)。
    """

    def __init__(self, ctx: SrContext, hp_value: int | None = None,
                 hp_readable: bool = False, hp_trusted: bool = False):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-买牌')
        self._hp_value = hp_value
        self._hp_readable = hp_readable
        self._hp_trusted = hp_trusted

    def _buy_round(self) -> OperationRoundResult:
        """旧路径委托体(buy 节点旧路径与变体决策循环共享的单一实现)。"""
        rr, outcome = run_buy_waves(self, self.ctx.cw_match,
                                    self._hp_value, self._hp_readable,
                                    self._hp_trusted)
        if rr is not None:
            return rr
        return self.round_success(
            f'plan 买{outcome.total_buy}张 升{outcome.total_level}次 '
            f'刷{outcome.total_refresh}次 卖{outcome.total_sell}张')

    @operation_node(name='买牌', is_start_node=True)
    def buy(self) -> OperationRoundResult:
        # 装配点分流(架构设计 §9.1 并存期;先例锚 = cw_screen_encounter
        # 同式判据):两端口完整在场 → 变体五段(旧体委托);缺省 None =
        # 生产直连下方旧路径(原序列逐位保留)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return self._buy_round()

    # ---- 变体五段(旧体委托形态;映射申报见类 docstring)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:空申报(旧体委托变体)。

        入口观察住 :func:`run_buy_waves` 段循环内(每段一次,含
        ``cw_game_ports`` 端口改道),变体不拆段循环(拆段 = 「刷新终结
        交回重进」物理载体与节点预算语义变更,总纲契约 5 红线)——
        无独立早退面,恒不早退。
        """
        return None, None

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:空申报(播种对账 ``guard_expected_vs_tracked``
        stage='seed' 住委托体段循环内,无独立对账面)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-5:决策循环段承载委托体(:func:`_buy_round` 单一共享)。

        策略消费(decide_shop_action)住委托体内,本段**不申报** B4
        选项②空决策合同(与只读/导航变体的空申报语义区分);on_outcome
        = 无登记件(注册表缺席 = 零动作)。
        """
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._buy_round()
        self._lifecycle_mark('on_outcome')
        return rs
