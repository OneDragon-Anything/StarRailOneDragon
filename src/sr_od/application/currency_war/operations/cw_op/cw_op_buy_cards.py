
import contextlib
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_intention import serialize_intention
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
    _area_rect,
    area_center,
    shop_card_click_points,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    REFRESH_COST_BASE,
    BenchChar,
    BuyCard,
    DeployMove,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    bench_from_compact,
    bench_occupied,
    merge_buy_k,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.obs.cw_observation import (
    ensure_portrait_templates,
    new_bench_slots,
    read_game_state,
    read_gold,
    read_gold_opt,
    read_shop_cards,
)
from sr_od.application.currency_war.obs.cw_observation_gate import (
    PHASE_PREP_SHOP_OPEN,
)
from sr_od.application.currency_war.telemetry import defects, recorder
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


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
    """卖前对拍守卫(迁移审计 w62(git 历史) 件2 设计章2.5 轻守卫;ADR-0329)。

    生成期快照 ``state.bench[idx].char_id``(期望名)vs 执行期实况
    ``tracked_bench_chars`` 现槽名——不符 = 槽位内容已被本循环前序动作消费
    (3合1 merge 删件/前笔卖出)→ 整笔跳过(stale_proposal,与 cw_state 拒绝
    语义同词)。两表同源于循环顶(``state.bench = bench_from_compact(tracked)``),
    mid-loop 漂移必被抓。残余风险(不防「tracked 名字本身错」)= buy-OCR 误读,
    属既有跟踪保真度问题(迁移审计 w57(git 历史) F6),不在本批根治。
    """
    return bool(expected) and live is not None and live == expected


def expected_gold_after_actions(state_gold: int, spend: int,
                                sell_income: int) -> int:
    """买后预期金(迁移审计 w62(git 历史) 件2 设计章2.7 必改项;ADR-0329):开店金 − 花出 + 卖入。

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
        last_node_type: str | None,
        hp_value: int | None,
        hp_readable: bool,
        hp_trusted: bool,
) -> GameState | None:
    """买后重估增量态构造(执行边界压缩·买后验证增量的单一构造点)。

    机制不变量:买牌/卖牌/刷新不触 plane/round/board/level/xp/streak/
    node_type(升级触 level/xp,由调用方 total_level 门拦截,不进本函数);
    gold 用关店帧真读;bench 重播 tracked_bench_chars(执行侧
    mutate_bench_deployed 逐动作同步的权威源,末波垫底 state 的 bench
    是执行前快照,必须重播)。
    fail-closed 两维:①gold_read=None(金失读)→ 返回 None,调用方回退
    全量 read_game_state;②tracked_bench_chars 为空 → 同样返回 None。
    ②的理由:bench 真空(全部署/合成清空)与跟踪丢失在本构造点不可区分,
    而垫底 state.bench 是执行前快照——空 tracked 时沿用它会把陈旧 bench
    当真值喂给 update_target(误读维度造值)。回退全量读后两种情形都得到
    OCR 真值,代价只是罕见情形多一次整帧读。
    """
    if gold_read is None:
        return None
    if not tracked_bench_chars:
        return None   # 空 tracked:真空/丢跟踪不可区分 → fail-closed 回退全量读
    post = deepcopy(last_state)
    post.gold = gold_read
    post.bench = bench_from_compact(deepcopy(tracked_bench_chars))
    _apply_hp(post, hp_value, hp_readable, hp_trusted)
    if last_node_type:
        post.node_type = last_node_type
    return post


def _form_progress(comp, state) -> float:
    """fp 遥测helper(review 要求:fp 轨迹可观测;comp None 时不调)。"""
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    return form_progress(comp, state)


def _tracked_bench_chars(names: list[str]) -> list[BenchChar]:
    """tracked_bench(buy OCR 的角色名)→ BenchChar 列表(跨轮 seed state.bench)。

    buy 时 ``read_shop_cards`` OCR 的规范名(T#92 验证可靠)持久化,跨轮 seed bench →
    plan / char_quality / comp core check 知 bot 自有角色。**SIFT 立绘识别现已可行**(plaza
    官方立绘库,D-8/D-10/D-12 验证)—— deploy op 后用 SIFT 真实身份纠 tracking 漂(deploy_bench
    ``_reconcile_tracking``,D-12);buy 期 bench 仍用 OCR 名跟踪(buy 改变 bench,SIFT 单帧跟不上)。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    out: list[BenchChar] = []
    for i, n in enumerate(names):
        if not n:
            continue
        ch = get_char(n)
        # faction 语义(2026-08-17 清理):'?' = 未知(名不在注册表);'' = 已知无阵营(白厄「救世主」类,
        # 复制效果不计阵营人数)。旧版两者混填 '?',日志无法区分"识别失败"与"本来就无阵营"。
        out.append(BenchChar(
            slot=i, char_id=n,
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
        ))
    return out


# 「购买经验」按钮(= 买经验升等级)screen_info area 名;中心运行时读(area_center)
BUY_EXP_AREA: str = '备战标识-购买经验'
LEVEL_UP_FALLBACK: Point = Point(296, 860)   # screen_info 缺失时兜底
REFRESH_FALLBACK: Point = Point(1592, 472)   # 「刷新」按钮兜底(screen_info 按钮-刷新)
# D牌(刷新)硬上限:plan 的 _refresh_cap 是单次 plan 软上限;两阶段循环里再加硬墙防死循环
MAX_REFRESH: int = 4


def _fmt_action(a) -> str:
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


def run_buy_waves(op: SrOperation, match,
                  hp_value: int | None, hp_readable: bool,
                  hp_trusted: bool) -> tuple[OperationRoundResult | None,
                                             BuyCardsOutcome | None]:
    """买牌波循环主体(W970 批 A 原子化:原 CwOpBuyCards 波循环随迁)。

    读牌面 → d2 决策(decide_prep)→ 执行至首个 RefreshShop(含)→
    刷新重判,MAX_REFRESH 硬墙;含 gold 融合读救援/d2 卖通道/遥测写点
    (原样随迁,决策逻辑零改动)。hp 三件组来自调用方的 shop 关闭帧读链
    (W970 §4.3.4:商店开态 HP 区不可读),波顶 read_game_state 后经
    :func:`_apply_hp` 值位同写覆盖。

    match=None(独立 run_operation 调本 op)→ 临时 match,不挂 ctx
    (局外不复用)。config 本函数内构造(W970 §4.3.4:CwOpBuyCards 产出,
    壳侧买后重估经 outcome.config 消费)。

    返回 (失败 round 结果, 产出)。正常收工 → (None, outcome);
    未识别卡停机钩子触发 → (round_fail 留证结果, None)——壳侧直接返回,
    与原实现「钩子返回即退出 buy」同语义。
    """
    config = CurrencyWarConfig(op.ctx.current_instance_idx)
    if match is None:
        # 防御:无对局态(独立 run_operation 调本 op)→ 临时 match,不挂 ctx(局外不复用)
        # (default 栈退役后,防御具现改用唯一策略载体 decision_v2)
        from sr_od.application.currency_war.decision.cw_strategy import (
            CurrencyWarMatch,
        )
        from sr_od.application.currency_war.decision.decision_v2.strategy import (
            DecisionV2Strategy,
        )
        _def = DecisionV2Strategy()
        match = CurrencyWarMatch(_def, _def.create_session(config))

    # 牌位/升级/刷新中心从 screen_info 读(缺失兜底)。target 由 strategy.update_target 管理(下方)。
    click_pts = shop_card_click_points(op.ctx)
    level_btn = area_center(op.ctx, BUY_EXP_AREA) or LEVEL_UP_FALLBACK
    refresh_btn = area_center(op.ctx, '按钮-刷新', SHOP_SCREEN_NAME) or REFRESH_FALLBACK

    total_buy = total_level = total_refresh = 0
    # `w577_refresh_fee_and_andon/`(ADR-0456)「计划≠尝试」执行事实:plan 里被硬墙跳过/截断丢弃的
    # 动作不再静默——单元落账时经 set_unit_exec_facts 进 spend_ledger,
    # 安灯分类器据此把「计划了但没点」分流为 plan_truncated(不停)。
    _plan_truncated = False
    _refresh_skipped: str | None = None
    _refresh_attempted = False
    _refresh_board_changed: bool | None = None
    # 迁移审计 w62(git 历史) 件2(ADR-0329):卖通道执行计数(income 遥测 + gold 对拍纳入卖入)
    total_sell = total_sell_income = total_sell_skip = total_sell_fail = 0
    # 关店对拍账基座:执行侧逐动作累计花金(买价+升级费+当次刷新费)。
    # 刷新费必须在点击时按「当次刷价」累计进本单元总账 —— 不能用
    # total_refresh(跨波计数)× 末波刷价 事后乘:关店对拍的期望若基于
    # 末波重读金,前面各波的刷新费已在其中净扣过,再按总波数扣一遍 =
    # 跨波重复扣,多波刷新时对拍期望含刷新费×(波数−1)的常量偏差。
    _spend_executed = 0
    # 对拍基线 = 开店首读金:首波循环顶读、任何动作执行前快照(含假 0
    # 救援后的值)。末波重读值已净含各波花销,当基线会与全程动作账双重相减。
    gold_open: int | None = None
    # 两阶段 plan(r6 F8):simulate(RefreshShop) 不换牌 → plan 在 RefreshShop 之后的 BuyCard
    # 是旧 shop 的失效决策。故每轮:plan → 执行至**首个 RefreshShop(含)** → 若刷新了则重 OCR + 重 plan。
    # 硬墙 MAX_REFRESH 防死循环(plan _refresh_cap 是单次软上限,每轮 plan 重置)。
    # _after_shot(同为 shop-OPEN)做 pixel-diff,差值才只反映 buy 带来的 bench 占位变化。旧代码用
    _buy_baseline = op.screenshot()
    # `w536_merge_expect/`(merge_mechanics §4 消费点):买牌期望态基座。期望 = 购买意图
    # 经落点规则的纯函数(compute_buy_expect;合成落点单一源 =
    # cw_state._merge_bench),由 CwScreenPrep 主环在 RunBuyPhase 后的
    # heavy 定型帧上对账(零决策记账)。本单元含卖出/未识别牌 → 期望
    # 不建(宁缺勿造:卖出使追踪基线与纯意图模型错位;缺身份必成片
    # 假不一致),这些动作仍走既有对账通道。

    from sr_od.application.currency_war.kernel.cw_prep_expect import BuyPurchase
    _buy_purchases: list[BuyPurchase] = []
    _buy_has_sell = False
    _buy_unidentified = False
    _buy_pre_bench = deepcopy(match.session.tracked_bench_chars)
    _buy_pre_deployed = deepcopy(match.session.tracked_deployed)
    # 执行边界压缩(本批):_target_seeded = 首波 update_target 已做
    # (替代原开店后独立读);_prev_refresh_only =
    # 上一波是「仅刷新波」(连击续刷判定输入,判据单一源 =
    # refresh_wave_is_refresh_only)。
    _target_seeded = False
    _prev_refresh_only = False
    _bought_names: list[str] = []
    for _ in range(MAX_REFRESH + 1):
        if not _prev_refresh_only:
            time.sleep(0.3)  # 等 board 面板 settle(买牌/shop 开 → panel 动画显示 tier 链"2/4/6/8"→ OCR 误读;连击续刷波前一动作是刷新,面板未变,跳过)
        # 光标 parking(审计 P0,2026-08-16):上轮 BuyCard/LevelUp/Refresh 点击后光标停在按钮上
        # (购买经验距等级区 18px/牌位=识别区本身)→ 污染本帧 read_game_state;park 后再读。
        op.park_cursor(after_wait=0.1)
        state = read_game_state(op.ctx, op.screenshot(),
                                phase=PHASE_PREP_SHOP_OPEN)   # ADR-0462 开店动作期
        _apply_hp(state, hp_value, hp_readable, hp_trusted)   # shop 开帧 hp 区空 → 用 shop 关闭帧值覆盖(值+位同写,`w580_hp_trust_defense/`)
        if not _target_seeded:
            # 执行边界压缩:原开店后 update_target 专用读的首波替代。
            _target_seeded = True
            match.strategy.update_target(state, match.session, config)
        # r7 review P0-①:shop 开帧节点行被遮 node_type 恒 None(plan 路径 1700/1706 None 实证,
        # boss 判定死码)→ 拷 Director shop 关态真值(仿 hp_value 同法)。
        if match is not None and match.session.last_node_type:
            state.node_type = match.session.last_node_type
        # r73 review RC3 修(dual_track_phase 战术层接线断裂):update_target 写在
        # _tgt_state(每轮首对象),循环内 read_game_state 新建 state 默认 False →
        # ADR-0209 双轨买门/stash 放行/DP 攒息压制在实跑买牌路径**从未执行**
        # (遥测指纹:每轮首条 True、循环内全 False)。修:dual 态单一源挂 session
        # (cw_strategy),循环态每轮拷贝(仿 hp/node_type 同法);读端 =
        # R1 唯一合法读端 committed_from(蓝图 §4.3,禁 session 直读散落)。
        from sr_od.application.currency_war.decision.decision_v2.prep_brain import (
            committed_from,
        )
        state.dual_track_phase = not committed_from(match.session)
        if getattr(match.session, 'transition_framework', ''):
            state.focus_factions = getattr(match.session, 'focus_factions', set())
        # gold-robust:gold 数字 stylized,paddle OCR det 间歇漏(同帧读 3/0/空;实锤 click-test
        # 买牌成功 gold≥1 但 reader 读 0,见 process_log)→ 读 0 时重读几帧取首个 >0(deterministic 同帧
        # 重读无意义,故重截图)。不根治(stylized 漏读),但把「读 0 不买」概率降到「连读 0 才认 0」。
        # 观察冲突审计 #6(2026-08-16):救援结果留证 —— 救回(首读假 0)/连读 0(真 0 或持续漏),
        # 统计 stylized 漏读率,为 gold 双源(购买差值)排期供数据。
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
        # 开店首读金快照(仅首波;救援后取值——救援值比假 0 更接近真值)
        if gold_open is None:
            gold_open = state.gold
        # task#105:优先 tracked_bench_chars(带 star+merge,mutate 同步);空(首轮)退 tracked_bench(旧 star 恒1)。
        if match.session.tracked_bench_chars:
            # ADR-0316:tracked 是占用列表(带 1-based slot)→ 槽位表
            state.bench = bench_from_compact(
                deepcopy(match.session.tracked_bench_chars))  # copy 防下游 plan 污染持久态
            log.info(f'[cw] tracked_bench_chars(seed)='
                     f'{[(c.char_id, c.star) for c in state.bench if c is not None]}')
        elif match.session.tracked_bench:
            # ADR-0316:旧 seed 路径同样走槽位表(紧凑→定长 9 含 None),不直接覆盖契约
            state.bench = bench_from_compact(_tracked_bench_chars(match.session.tracked_bench))
            log.info(f'[cw] tracked_bench(旧 seed)={match.session.tracked_bench}')
        # 读 comp 成型度 —— overlay 时 board 不可读,用上次备战读的近似。
        match.session.last_state = state
        # r95 审计必修②:plan 异常也要留证(run16 模式:7 个买牌回合 record_decision
        # 整体缺席 + 40s 无 op 记录 = decide_prep 抛错被上层吞,事后不可诊断)。
        # 异常时仍写一条 decisions(Error 占位)+ 完整栈到 log,再向上抛(行为不变)。
        # 黑板写路径(W971 §2,P2):本波融合观察态(牌面现读+hp 覆盖+node_type/
        # dual/focus 拷入+gold 救援+tracked 播种,上方融合段即组装点)直写
        # session.shop_state_frame——写者白名单 = 本段;读者 = decide_shop_screen。
        match.session.shop_state_frame = state
        # 期望态覆盖点·商店波顶(EXPECTED_STATE §2:gold 可信源 + 备战席占位
        # ——星级身份不可见,期望态存活主场景):gold 族条目可信读清账;tracked
        # 族条目绑 prep_obs 覆盖点,此处透传不确认(F7)。best-effort。
        try:
            from sr_od.application.currency_war.kernel.cw_expected_state import (
                reconcile_expected,
            )
            _store = getattr(match.session, 'expected_state', None) or {}
            _act = {}
            for _p, _e in list(_store.items()):
                if _e.confirm_point != 'shop_wave_top':
                    continue
                _act[_p] = (getattr(state, 'gold', None),
                            getattr(state, 'gold_readable', True))
            reconcile_expected(match.session, 'shop_wave_top', _act)
        except Exception as _e:  # noqa: BLE001  观测面不阻塞波循环
            log.debug(f'[cw-shop] expected reconcile skip: {_e}')
        try:
            actions = match.strategy.decide_shop_screen(match.session, config)
        except Exception:
            import traceback

            from sr_od.application.currency_war.telemetry.recorder import (
                record_decision as _rd_err,
            )
            _tb = traceback.format_exc()
            log.error('[cw!][plan] decide_prep 异常(留证后上抛):\n%s', _tb)
            with contextlib.suppress(Exception):
                # eval_breakdown 是 dict[str,float],错误信号用 len(_tb) 数值占位
                # (异常本体全文在 log,此处只留"该回合 plan 崩了"的可检索标记)
                _rd_err(state, match.session.target_comp.name if match.session.target_comp else '',
                        {}, {'plan_error': 1.0, 'plan_error_len': float(len(_tb))}, [])
            raise
        # A2:target 由 session 管理(update_target 写),日志/telemetry 直接读 session.target_comp。
        target_name = match.session.target_comp.name if match.session.target_comp is not None else ''

        _fp_v = _form_progress(match.session.target_comp, state) if match.session.target_comp is not None else -1.0
        # r295(用户定调:判读必须看节点类型——判读人看日志时
        # 备战帧没有节点上下文,r8"+2 回升"会被误读成遭遇段
        # 胜利):state 行带 node(本节点类型)+next(下节点,
        # 左移推断源)——判读一眼看出"这轮备战的是什么节点"。
        _node = getattr(match.session, 'node_type_current', None) or '?'
        _upc = getattr(match.session, 'upcoming_types', None) or []
        _next = _upc[0] if _upc else '?'
        log.info(f'[cw] state gold={state.gold} hp={state.hp} lv={state.level} '
                 f'plane={state.plane} round={state.round_num} node={_node} '
                 f'next={_next} board={state.board} '
                 f'target={target_name!r} fp={_fp_v:.2f} bench={bench_occupied(state.bench)}')
        log.info(f'[cw] shop={[(c.faction, c.name, c.cost) for c in state.shop]} '
                 f'plan={[_fmt_action(a) for a in actions]}')
        # r97 供给快照(进店首见):全波牌面真值源之一 —— 只记 decisions 会丢 refresh 波
        recorder.record_shop_snapshot('offer', state.shop, state.gold,
                                          state.plane, state.round_num)
        _cand = dict(getattr(match.session, 'last_candidate_scores', {}) or {})
        if getattr(match.session, 'last_candidate_scores_round', None) != state.round_num:
            _cand = {}   # r3 review②:非本轮回合的分数是陈旧值(仅选线轮写入)→ 清空防 close_call 污染
        # r73 RC6:fp 落遥测(form_progress 此前只在日志,P1→P2 断崖审计只能从 board 推)
        _eb: dict[str, float] = {}
        if match.session.target_comp is not None:
            _eb['fp'] = round(_form_progress(match.session.target_comp, state), 3)
        # r101 session 态快照(redesign/102:完整决策输入落盘,回放/快照回归用)
        _sess = match.session
        _extra = {
            'sess_framework': getattr(_sess, 'transition_framework', '') or '',
            'sess_dual_track': not committed_from(_sess),   # R1 唯一读端
            'sess_drought': getattr(_sess, 'target_drought', None),
            'sess_commit_scores': dict(getattr(getattr(_sess, 'commit_signals', None), 'scores', {}) or {}),
            'sess_active_env': getattr(_sess, 'active_env', '') or '',
            # ADR-0343:成型停手态(层2 写;检查器豁免/判读锚点)
            'formed_stop': bool(getattr(_sess, 'v3_formed_stop', False)),
            # 迁移审计 w114(git 历史)/ADR-0346 相位影子观测(零消费;每轮 decide_prep 入口
            # 算,session 写,此处只透传给遥测 rounds 行)
            'phase': getattr(_sess, 'v3_phase', '') or '',
            'form_ok': bool(getattr(_sess, 'v3_form_ok', False)),
            'form_score': round(float(getattr(_sess, 'v3_form_score', 0.0) or 0.0), 3),
            # 迁移审计 w119(git 历史)/ADR-0347 授权依据 trace:当轮 DP 日程表姿态
            # (ev.RoundPosture.posture.tag;""=查询失败/default 栈)
            'dp_posture': str(getattr(getattr(
                getattr(_sess, 'v3_dp_posture', None),
                'posture', None), 'tag', '') or ''),
            # ADR-0348 ↺:扑满节点识别遥测(过热局 reward 帧 True;
            # ②b 观测与实机建档数据面——识别≠深花授权,消费边界
            # =scoring 豁免×P8 上限)
            'piggy_reward': bool(getattr(_sess, 'v3_piggy_reward',
                                         False)),
            # r226 策略 v2 遥测字段(ADR-0336 后 LineStrategy 已删:
            # v2_* 恒空串/None,字段保留作历史 schema 兼容;
            # decision_v2 的模式/意向走 v3_* 字段)
            'strategy_id': getattr(config, 'strategy_id', 'decision_v2'),
            'v2_mode': (_sess.v2_state[0] if _sess.v2_state else ''),
            'v2_locked_line': _sess.locked_line or '',
            'v2_bridge': _sess.bridge_id or '',
            # r359(回放忠实化,ADR-0231):v2 相位机元组全量落盘
            # (LineStrategy 时代字段;ADR-0336 后恒 None,保留
            # 兼容历史回放)
            # r359(回放忠实化,ADR-0231):v2 相位机元组全量落盘
            # (LineStrategy 时代字段;ADR-0336 后恒 None,保留
            # 兼容历史回放)
            'sess_v2_state': list(_sess.v2_state)
            if getattr(_sess, 'v2_state', None) else None,
            # 迁移审计 w146(git 历史) v3 意向状态落遥测(ADR-0336 后 v2_locked_line
            # 恒空,锁定时点/目标只有这里可读;None=无意向状态机)
            'v3_intention': serialize_intention(
                getattr(_sess, 'v3_intention', None)),
            # (换线存活门决策位 line_gate_blocked/cf_blocked 已随
            #  C4 开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT
            #  §1.3;v3_line_gate_* session 字段同批删。)
            # `w224_handoff/`/ADR-0399:P2 承接快照(纯观测;plane>=2 位面首帧
            # decide_prep 写 session.v3_handoff,此处透传——仅 P2
            # 首轮行非空,与 sim SimResult.p2_handoff 同源同构)
            'handoff': (getattr(_sess, 'v3_handoff', None).as_dict()
                        if getattr(_sess, 'v3_handoff', None)
                        is not None else None),
        }
        # 迁移审计 w222(git 历史) 遥测缺口①(迁移审计 w220(git 历史) 判读实锤:两局 decisions.state.equips 恒空):
        # owned 穿戴池的唯一 session 写端在 equip_all,读端拷贝只接在
        # _pseudo_state(策略层决策内部 state)——record 用的
        # 本 state 是 OCR 现读对象,equip reader 不填 state.equips →
        # 落盘链断在这里。record 前补拷(同 hp/node_type/dual_track 的
        # session 拷贝族)。⚠️ 位置必须在 decide_prep **之后**:
        # cw_comps 装备动态权重读 state.equips,提前拷=改决策行为
        # (观测链修复禁越界;本行之后 plan 已定,执行走点击不读 state)。
        state.equips = list(getattr(match.session, 'last_owned_equips', []) or [])
        recorder.record_decision(state, target_name, _cand, _eb, actions, extra=_extra)

        # 执行至首个 RefreshShop(含);无 RefreshShop 则执行全部(DeployMove/SellBench 仍跳过)
        refresh_idx = next((i for i, a in enumerate(actions) if isinstance(a, RefreshShop)), None)
        prefix = actions if refresh_idx is None else actions[:refresh_idx + 1]
        _wave_refresh_only = refresh_wave_is_refresh_only(actions)
        if refresh_idx is not None and refresh_idx + 1 < len(actions):
            # `w577_refresh_fee_and_andon/`:截断丢弃的尾部动作(下波会重 plan,但本 plan 行已按
            # 全量记账)对分类器是「计划≠尝试」,可见化不停(ADR-0456)
            _plan_truncated = True
        bought_x: set[int] = set()
        did_refresh = False
        for action in prefix:
            if isinstance(action, BuyCard):
                # plan sim 不从 shop 移除已买牌 → 可能重复 emit 同 x;执行侧按 x 去重
                if action.card.x in bought_x:
                    continue
                bought_x.add(action.card.x)
                pt = (min(click_pts, key=lambda p: abs(p.x - action.card.x))
                      if click_pts else Point(action.card.x, 288))
                # `w536_merge_expect/`:买前裁该片矩形拷贝(numpy .copy(),~125KB/张)——
                # 「买了什么」的像素级证据,随期望态带到对账点,不一致才
                # 落盘(平时零磁盘写入)。一帧原则:来自读牌时已截的帧,
                # 零新增截屏;必须 copy——整帧会被帧缓存复用覆写。
                _card_crop = None
                with contextlib.suppress(Exception):
                    _frame = op.screenshot()
                    for _i in range(1, 6):
                        _r = _area_rect(op.ctx,
                                        f'{A_SHOP_CARD_PREFIX}{_i}',
                                        SHOP_SCREEN_NAME)
                        if _r is not None and _r.x1 <= pt.x <= _r.x2:
                            _card_crop = _frame[_r.y1:_r.y2,
                                                _r.x1:_r.x2].copy()
                            break
                op.ctx.controller.click(pt)
                log.info(f'[cw-shop] Buy click @({pt.x},{pt.y}) '
                         f'{action.card.faction}/{action.card.name}/{action.card.cost}')
                time.sleep(0.4)
                total_buy += 1
                _spend_executed += action.card.cost
                if action.card.name:
                    match.session.tracked_bench.append(action.card.name)
                    _bought_names.append(action.card.name)
                mutate_bench_deployed(match.session.tracked_bench_chars, match.session.tracked_deployed, action)
                # `w536_merge_expect/`:记录购买意图(身份/星级/张数)。张数:常态=1;
                # 备战栏满且可触发合成 → 游戏自动多买 k 张
                # (merge_mechanics §2.5,【置信:低——连升子案】,按
                # 说法实现、由对账网实证修正)。k 公式单一源 =
                # cw_state.merge_buy_k(与 decision_v2 满栏购买门同一
                # 公式,`w544_fullbench_mergebuy/`/ADR-0453 收敛,禁执行侧重算)。
                # 金账无折扣:总价 = k×单价(§2.5)——执行账本笔记
                # 1× 单价 + 多买补差 (k−1)×,与游戏一次点击扣全款
                # 对齐(gold 差值对拍 ±2 容差内);不满栏 _cnt=1 补差 0。
                if action.card.name:
                    _cnt = 1
                    if bench_occupied(state.bench) >= BENCH_CAPACITY:
                        _cnt = max(1, merge_buy_k(
                            action.card.name, action.card.star or 1,
                            state.bench,
                            match.session.tracked_deployed, state.shop))
                        _spend_executed += (action.card.cost or 0) \
                            * (_cnt - 1)
                    _buy_purchases.append(BuyPurchase(
                        name=action.card.name, star=action.card.star,
                        count=_cnt, unit_cost=action.card.cost or 0,
                        crop=_card_crop))
                else:
                    _buy_unidentified = True
            elif isinstance(action, LevelUp):
                op.ctx.controller.click(level_btn)
                log.info(f'[cw-shop] LevelUp click @({level_btn.x},{level_btn.y})')
                # 用户口述口径(screen_flow_timing.md #22,2026-09-02):
                # 购买经验动画 ~1s;光标遮挡由下一波循环顶 park_cursor 防
                #(波内路径)——本 sleep 只对齐动画时长(原 0.6s 不足)。
                time.sleep(1.0)
                total_level += 1
                _spend_executed += action.cost
            elif isinstance(action, RefreshShop):
                if total_refresh >= MAX_REFRESH:
                    # `w577_refresh_fee_and_andon/`:硬墙跳过=计划了但未尝试,可见化(局22 误停根因:
                    # 此前静默 continue 被分类器当「点击落空」误判 not_effective)
                    _plan_truncated = True
                    _refresh_skipped = 'max_cap'
                    continue   # 硬墙:不再刷新(本轮当未刷新 → 收工)
                _refresh_attempted = True
                # 刷新期望对账 producer(契约单一源=cw_screen_prep.
                # build_refresh_expect docstring;唯一合法评估窗=本波内
                # ——director 只持关店帧,无「刷新后开店帧」;先例=下方
                # pending_buy_expect 同型惰性 import)。
                # 期望三输入点击前现读;刷价 = 基价常量(ADR-0456:徽标
                # 读数非刷价,期望=实付基价 2,refresh_expect_mismatch
                # 缺陷类随之归零);构建失败静默跳过,不阻塞买牌。
                _refresh_expect = None
                _reconcile = None
                _pre_shop_names: list[str] | None = None
                try:




                    from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
                        build_refresh_expect,
                        refresh_reconcile_mismatches,
                    )
                    # 刷前现读两口径(执行边界压缩·连击共享往返):
                    # - 仅刷新波(_wave_refresh_only,判据单一源 =
                    #   refresh_wave_is_refresh_only):本波无买卡/卖出,
                    #   波循环顶整帧读未被本波动作污染 → state.gold/
                    #   state.shop 即点击前现读,跳过 pre-shot 重复读;
                    # - 其余波:`w592_free_refresh_fix/`(ADR-0456 勘误)
                    #   原语义——点击前一帧现读金 + 牌名集。刷前名集
                    #   不得用 state.shop:那是本波 plan 期读数,波内
                    #   买卡不从 state.shop 摘已买牌,买+刷新波里
                    #   「plan 读 vs 点击后实读」集合必不等,刷新真落空
                    #   会被误判成免费生效。
                    if _wave_refresh_only:
                        _pre_gold = state.gold if state.gold > 0 else None
                        _pre_shop_names = [c.name for c in state.shop
                                           if c.name]
                    else:
                        _pre_shot = op.screenshot()
                        _pre_gold = read_gold_opt(op.ctx, _pre_shot)
                        # 本波已买槽位现读为空槽/未识别(''),是自身买卡
                        # 所致、不含刷新证据,比较前剔除;刷后一侧不剔除
                        # ——含 '' 仍按不可判不猜(语义同 refresh_effective)。
                        _pre_shop_names = [c.name
                                           for c in read_shop_cards(op.ctx,
                                                                    _pre_shot)
                                           if c.name]
                    _refresh_expect = build_refresh_expect(
                        _pre_gold, REFRESH_COST_BASE,
                        [(c.name, c.star) for c in state.shop],
                        state.plane, state.round_num)
                    _reconcile = refresh_reconcile_mismatches
                except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
                    _refresh_expect = None
                    _reconcile = None
                op.ctx.controller.click(refresh_btn)
                log.info(f'[cw-shop] Refresh click @({refresh_btn.x},{refresh_btn.y})')
                # r325(P1⑤ 等画面审查):刷新后固定 sleep(1.0)
                # 改**两帧一致门**——牌行区指纹连续两帧一致才
                # 采快照/重 plan(刷新动画帧上的 SIFT miss 是
                # r97/38 样本实证的根因;基元=cv2_utils
                # fingerprint_in_rects/same,r324 下沉件)。
                # 超时 2.5s 回退旧 sleep 语义(不阻塞买牌)。
                from one_dragon.base.geometry.rectangle import Rect
                from one_dragon.utils import cv2_utils as _cvu
                _rects = (Rect(300, 228, 1560, 326),)   # 商店牌行
                _base = None
                _stable = False
                import time as _t3
                for _ in range(8):   # ≤2s@0.25s 步长
                    _t3.sleep(0.25)
                    # r327(终审 D):截图裸调会炸 refresh 分支
                    # (离线 mock/瞬断)——与同文件快照段/gate
                    # 调用同契约:suppress 降级为继续等,
                    # 循环尽=超时回退旧 sleep 语义。
                    _fp = None
                    try:
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
                    _t3.sleep(0.5)   # 超时回退(≈旧 1.0s 总量)
                # 当次刷价进花销账 = 基价常量(ADR-0456:实付恒基价,
                # 不随波变;``or 2`` 兜底在字段恒基价后不再触发,保留
                # 消费点契约不动)
                _refresh_fee = state.shop_refresh_cost or 2
                _spend_executed += _refresh_fee
                total_refresh += 1
                did_refresh = True
                # r97 供给快照(refresh 波):刷出来的新牌面落盘(局18 教训:只记进店帧
                # → 「配方件来没来」复盘断章取义,健康线被误判断供弃线)。
                try:
                    _new_shop = read_shop_cards(op.ctx, op.screenshot())
                    recorder.record_shop_snapshot(
                        'refresh', _new_shop, state.gold - _refresh_fee,
                        state.plane, state.round_num)
                    # 刷新有效性对拍(观测自检框架设计 §2.5):r97 刷后重读
                    # (_new_shop)与刷前牌名集合全同 = 刷新未生效(点击落空/
                    # 费金照扣没刷/动画帧误读)→ 落缺陷台账。刷前名集 =
                    # 点击前现读(_pre_shop_names,`w592_free_refresh_fix/` 勘误:原 state.shop
                    # plan 读会把买+刷新波的真落空洗成免费生效)。
                    # shop_refresh 是决策关键面,「全同」按
                    # 硬失败形态传 gap_large;复现防抖在台账层(同特征首见
                    # L1、两连全同升 L0 初判)。纯记账留证,零决策行为变更
                    # (刷新照点、买牌照买,停机接线未启)。
                    # `w577_refresh_fee_and_andon/`:牌面变没变同时是「计划≠尝试」三分的观测面。
                    # refresh_effective 三值:False=全同(未变)/True=已变/
                    # None=不可判(不可判不可当已变——会把真落空洗成免费,
                    # 安灯失去停线面),原样透传给分类器。
                    _refresh_board_changed = refresh_effective(
                        _pre_shop_names or [],
                        [c.name for c in _new_shop])
                    if _refresh_board_changed is False:
                        _ineff_shot = None
                        with contextlib.suppress(Exception):   # 截图 best-effort
                            _ineff_shot = op.save_screenshot(
                                prefix='refresh_ineffective')
                        defects.record_defect(
                            'shop_refresh', 'invariant_break',
                            expected=('刷后牌面≠刷前:'
                                      f'{sorted(_pre_shop_names or [])}'),
                            observed=('刷新后5牌与刷前全同(点击落空/费金照扣未刷/'
                                      f'动画误读):{sorted(c.name for c in _new_shop)}'),
                            plane=state.plane, round_num=state.round_num,
                            verdict='留证-刷新未生效嫌疑(费金照扣牌面未变)',
                            shot=_ineff_shot,
                            reader_source='refresh_set_compare',
                            gap_large=True,
                            refs=[{'stream': 'decisions',
                                   'key': (f'plane={state.plane}|round={state.round_num}'
                                           f'|refresh_wave={total_refresh + 1}')}],
                            note='观测自检框架设计 §2.5:全同=刷新未生效;'
                                 '两连全同才确认(台账复现计数)')
                    # 刷新期望 vs 实读对账(零决策记账)。
                    # 金腿=点后现读 vs 期望 gold_after(失读不评);牌腿=
                    # 有身份牌数>0(槽位解锁未建模,1-4 张不判错)。判据=
                    # refresh_reconcile_mismatches(真值表已锁);
                    # 本段异常由外层 except 兜住,不阻塞买牌。
                    if _refresh_expect is not None and _reconcile is not None:
                        _gold_after = read_gold_opt(op.ctx, op.screenshot())
                        # `w577_refresh_fee_and_andon/` 免费刷新事后正证据通道(ADR-0456,永久保留——
                        # 这是修正后的判定语义的一部分,非采证钩子):刷新已
                        # 点击 ∧ 牌面已变(相对点击前现读,`w592_free_refresh_fix/` 勘误)∧
                        # 点后金=点前金 → 免费刷新 proc 真实
                        # 发生(覆盖棱/策略/未知一切免费来源),截图+flag 留证
                        # (**不停机**——免费不是失败)。
                        if (_refresh_board_changed is True
                                and _pre_gold is not None
                                and _gold_after is not None
                                and _gold_after == _pre_gold):
                            with contextlib.suppress(Exception):
                                # 遥测模块须显式别名:裸 `state` 在本域是
                                # GameState 变量,期 6 U3 消费面重写曾把
                                # telemetry.state 误绑到它(AttributeError
                                # 被 suppress 吞掉 → 留证/执行事实静默断流)
                                from sr_od.application.currency_war.telemetry import (
                                    state as _cw_tel,
                                )
                                _free_shot = op.save_screenshot(
                                    prefix='free_refresh_proc')
                                # 局部 import:仅本证据段使用,不占模块级命名面
                                from datetime import datetime as _free_dt
                                _flag_p = get_project_root() \
                                    / '.debug' / 'temp' / 'cw_free_refresh_proc.flag'
                                _flag_p.parent.mkdir(parents=True, exist_ok=True)
                                _flag_p.write_text(
                                    'FREE-REFRESH-PROC: 免费刷新实机正证据(非停机,bot 照常跑)\n'
                                    f'run={_cw_tel.current_run_id()} '
                                    f'plane={state.plane} round={state.round_num} '
                                    f'wave={total_refresh} ts={_free_dt.now().isoformat(timespec="seconds")}\n'
                                    f'前后牌面: {sorted(_pre_shop_names or [])} -> '
                                    f'{sorted(c.name for c in _new_shop)}\n'
                                    f'gold: 前={_pre_gold} 后={_gold_after}(未扣=免费)\n'
                                    f'截图: {_free_shot}\n'
                                    '处理: 汇总频率判免费来源(棱 45%/策略类/未知),'
                                    '确认后删本 flag;通道本身保留(对账防线)。\n',
                                    encoding='utf-8')
                                log.warning(
                                    '[cw!][shop] 免费刷新 proc:牌面已变 金未扣'
                                    '(前=%s 后=%s)→ 留证不停 flag=cw_free_refresh_proc.flag',
                                    _pre_gold, _gold_after)
                        _cards_named = sum(1 for c in _new_shop if c.name)
                        for _m in _reconcile(_refresh_expect[0], _gold_after,
                                             _cards_named):
                            defects.record_defect(
                                'shop', 'refresh_expect_mismatch',
                                expected=(f'{_m["domain"]}/{_m["slot"]}: '
                                          f'{_m["expected"]}'),
                                observed=_m['observed'],
                                plane=state.plane, round_num=state.round_num,
                                verdict='留证-刷新期望不符(零决策)',
                                reader_source='refresh_expect_reconcile',
                                note='期望三输入波前现读,None 跳过;'
                                     '判据真值表已锁')
                except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
                    pass
            elif isinstance(action, SellBench):
                # 迁移审计 w62(git 历史) 件2(ADR-0329):d2 卖通道生产接线(design 章2.3)。
                # bench_idx = 槽位下标 0-8(ADR-0316),生成期索引 = 执行期索引;
                # 执行置 None 不紧缩(mutate_bench_deployed),多笔任意发射序零漂移。
                # ── 防误卖轻守卫(design 章2.5):生成期快照 state.bench(循环顶真值)
                #    vs 执行期实况 tracked(买/卖/合并随动)——mid-loop 槽位内容已被
                #    前序动作消费(3合1 merge 删件/前笔卖出)→ 整笔跳过(stale_proposal)。
                _expected = (state.bench[action.bench_idx].char_id
                             if (0 <= action.bench_idx < len(state.bench)
                                 and state.bench[action.bench_idx] is not None)
                             else None)
                _live = None
                if match is not None and match.session is not None:
                    # tracked 可能是紧凑列表(对账写回)或 pad 态(买后 mutate)→
                    # 统一经 bench_from_compact 转槽位表再按下标取(与 state.bench 同源)。
                    _live_table = bench_from_compact(
                        [bc for bc in match.session.tracked_bench_chars
                         if bc is not None])
                    _live = (_live_table[action.bench_idx].char_id
                             if (0 <= action.bench_idx < len(_live_table)
                                 and _live_table[action.bench_idx] is not None)
                             else None)
                if not sell_guard_ok(_expected, _live):
                    log.warning(
                        '[cw-shop] SellBench 守卫拦截(stale_proposal):idx=%s'
                        ' 期望=%s 现=%s → 跳过(下轮重 plan 会重评估)',
                        action.bench_idx, _expected, _live)
                    total_sell_skip += 1
                    continue   # 不卖错件
                from sr_od.application.currency_war.prep_actions import (
                    drag_bench_to_sell,
                )
                # 卖牌实收回金=执行前后 gold OCR 差,
                # 拖拽前取基数(拖拽本身不改金;miss=None,视图回退兼容)。
                _gold_before = None
                with contextlib.suppress(Exception):   # 观测 best-effort 不阻断卖出
                    _gold_before = read_gold(op.ctx, op.screenshot())
                ok = drag_bench_to_sell(op, op.ctx, action.bench_idx)
                if ok:
                    # tracking 同步:置 None 不紧缩(mutate_bench_deployed 已支持
                    # SellBench 分支,ADR-0316)
                    # P1 修复(独立 review):mutate 入口 pad_bench 按 index 补 None,
                    # 紧凑态 tracked(对账写回,含中间空槽)直接传入会 index≠槽位 → 清错槽;
                    # 与守卫/决策层同源,先经 bench_from_compact 统一为槽位表语义,
                    # 就地(切片赋值保同一引用)再 mutate。
                    _tracked = match.session.tracked_bench_chars
                    _tracked[:] = bench_from_compact(
                        [bc for bc in _tracked if bc is not None])
                    mutate_bench_deployed(
                        _tracked,
                        match.session.tracked_deployed, action)
                    # ADR-0328 执行域对齐:卖出件入同轮已卖集(同轮不回买)。
                    # 决策层已在动作采纳处登记(arbiter/carry_gate/补偿器),此处
                    # 执行侧幂等加固——执行成功是卖出事实的权威(register_round_sold
                    # 带轮键自校验,跨轮误写防御)。
                    from sr_od.application.currency_war.decision.decision_v2.discipline import (
                        register_round_sold,
                    )
                    register_round_sold([_expected], state, match.session)
                    total_sell += 1
                    _buy_has_sell = True   # `w536_merge_expect/`:含卖出 → 本单元期望态不建
                    total_sell_income += action.income or 0
                    # 实收回金落盘(exogenous
                    # kind='sell_income',消费=economy 视图卖回格)。
                    # 计划值 action.income 是 sim 口径;生产行只有这里
                    # 能拿到执行前后 gold 差。best-effort 不阻断买牌。
                    try:
                        time.sleep(0.5)   # 卖出入账动画(与买卖 sleep 同量级)
                        _gold_after = read_gold(op.ctx, op.screenshot())
                        recorder.record_sell_income(
                            state, action.bench_idx, _expected or '',
                            _gold_before, _gold_after)
                    except Exception:   # noqa: BLE001  观测 best-effort
                        pass
                    log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                             action.bench_idx, _expected, action.income or '?')
                else:
                    total_sell_fail += 1   # 拖 3 次源槽未变(现有语义)
                    log.warning('[cw-shop] Sell bench%d %s 拖3次源槽未变',
                                action.bench_idx, _expected)
        # 连击续刷判定输入:本波是否「仅刷新且真点击」(硬墙跳过/未刷
        # 均为 False → 下一波恢复波顶 settle 与 pre-shot 语义)。
        _prev_refresh_only = bool(_wave_refresh_only and did_refresh)
        if not did_refresh:
            break   # 本轮无刷新(或硬墙)→ 买完收工

    # [停机钩子·临时,采完删(用户 2026-08-15 指示)]未购买(含刷新后仍未购买)且商店有
    # 未识别卡(SIFT miss:昔涟诗篇等非角色内容/立绘缺的角色)→ 停机留画面给 AI 建档。
    # read_shop_cards 的采集钩子已存整屏+flag;此处只做停机判定(方案 D:stop_running+保画面)。
    # 立绘缺(开拓者·欢愉/加拉赫)会持续触发——现场采到立绘原料后即不再触发,一石二鸟。
    #
    # 📋 调研档案(2026-08-17 阮·梅/白厄单帧 miss 归因闭环,下次触发先读这段):
    # - 历史触发(r16-r17 留 38 样本 + 当天 14:52/14:54 两次)**全部是刷新动画/settle 瞬时帧**:
    #   ①离线 plaza 库对拍 38 样本全识别(73-119 内点,无一真未知——注意 cw_shot_unique 存的
    #   是检测后另截的稳定帧,≠ miss 当帧,「同图全识别」不能证伪);②本 hook 防抖重读两次均
    #   自愈 → 瞬时性实锤。非光照变体、非立绘库缺。
    # - 已做:刷新后等待 0.8→1.0s(上方 RefreshShop);cw_observation 内嵌 flag 写入钩子已删
    #   (无消费端纯积压)。本 hook 保留:真未知(新版本新卡/昔涟诗篇类非角色内容)仍需它兜底。
    # - 下次触发排查序:①看防抖重读是否自愈(自愈=瞬时帧,考虑再调等待);②未自愈 → 对停机
    #   画面跑 analyze_screen + 离线 SIFT 对拍(真实rect 商店牌-1..5)确认真未知 → 建档/补库。
    # M35 防抖(2026-08-16):全槽 unknown 但 Fate 角色全在库 → 判商店开态动画/settle 瞬时读失败
    # (0.3s sleep 偶不够)——停机前重读 2 帧(各 1s),仍 unknown 才真停(真缺模板不会因重读消失)。
    # W944 治本(2026-08-31,局2 r7「我来当策划」弹窗压暗实锤):blind sleep 改
    # **判据化自愈**——每次重读前先等牌行区两帧指纹一致(_wait_shop_row_stable,
    # 与刷新分支 r325 同门同 rect),稳定即读;预算仍 2 次(真缺模板/模态
    # 弹窗压暗不会因重读消失,预算耗尽才真停)。为什么不是 blind sleep:
    # 瞬态帧的自愈靠「帧稳定」判据而非猜时长;模态弹窗压暗形态画面本就
    # 稳定,门秒过 → 预算耗尽真停留证(弹窗处置归弹窗批域,flag 挂账)。
    # f570a76e 审查#1 修:**去 total_buy 门**——「买了≥1 张+仍有未识别槽」
    # 恰是在残缺牌面上做了买牌决策(ADR-0244 裁决理由本尊),原门让它
    # 零留证通过 = 暗门;防抖重读对任何未识别残留都该跑。
    if any(not c.name for c in state.shop):
        _unk = [i + 1 for i, c in enumerate(state.shop) if not c.name]
        for _ in range(2):
            _wait_shop_row_stable(op)
            _reshop = read_shop_cards(op.ctx, op.screenshot())
            _unk = [i + 1 for i, c in enumerate(_reshop) if not c.name]
            if not _unk:
                log.info('[cw-shop][hook] 重读后全识别(动画/settle 瞬时)→ 不停机')
                break
        if _unk:
            # [停机钩子·恢复]r34 曾降级为留证不停机(理由:连续两局
            # 阻断实跑);2026-08-24 用户裁决**不能降级,恢复停机**——
            # 未识别卡按非 target 跳过 = 带病跑:错过新内容建档窗口
            # 且买牌决策在残缺牌面上做(潜在新卡/新版本内容不可见)。
            # 代价已知会(阻断实跑),用户明示接受。
            _shot = op.save_screenshot(prefix=f'shop_unk_slot{_unk[0]}')
            from datetime import datetime as _dt
            # 绝对路径锚仓根(审查#4:相对路径在 daemon spawn 的
            # 非 CWD 进程里落错地方,AI 巡检靠 flag 发现停机会失明)
            _fp = get_project_root() / '.debug' / 'temp' \
                / 'currency_war' / 'shop_unk.flag'
            _fp.parent.mkdir(parents=True, exist_ok=True)
            _fp.write_text(
                f'[HOOK-STOP] shop 未识别卡停机钩子(方案D,恢复):operations/cw_op/cw_op_buy_cards.py run_buy_waves\n'
                f'触发:未购买且商店槽{_unk}未识别(防抖重读 2 帧后仍 miss)——\n'
                f'   新版本新卡/昔涟诗篇类非角色内容/立绘缺。r34 降级已被用户否决\n'
                f'   (2026-08-24:未识别不能降级,带病跑错过建档窗口)。\n'
                f'处理步骤:1. 看 shot={_shot};对停机画面跑 analyze_screen\n'
                f'   + 离线 SIFT 对拍(真实rect 商店牌-1..5)确认真未知;\n'
                f'   2. 新卡 → 建档(screen_info/立绘库);瞬时帧类 → 调上方\n'
                f'   RefreshShop 后等待;3. 删本 flag + 重启 MCP server 重跑。\n'
                f'删除条件:连续多局零触发(未知内容建模收敛)后按 skill\n'
                f'   od-dev-stop-hooks 生命周期判据评估删除。\n'
                f'ts={_dt.now().strftime("%m-%d %H:%M:%S")}\n',
                encoding='utf-8')
            log.warning('[cw!] [shop] 未识别卡槽%s(重读后仍 miss)→ 停机留画面'
                        '待建档 shot=%s(用户裁决恢复:未识别不能降级)', _unk, _shot)
            op.ctx.run_context.stop_running(reason='hook:shop_unknown_card')
            return op.round_fail(status=f'shop 未识别卡槽{_unk},停机留证'), None

    # plan() 在最后一轮(无 refresh)的完整 actions 里含 DeployMove —— 取最后一次完整 plan 的 deploy moves。
    # ⚖️ pending_deploys 写入已删(2026-08-16 review D16/TOP4:0 读者,CwOpDeploy 实读
    # last_state.board;只写不读 = 腐化名单)。留日志行(计划可见性)。

    # → 新占槽 = bought 卡落点(left-to-right = buy 顺序,bench 从左到右填)。**两帧同 shop-OPEN 状态**
    # 自修正:deployed 后 deploy_bench 删该 slot;空槽 drag bench-count 不降 → retry-stick skip)。
    if _bought_names:
        _after_shot = op.screenshot()
        _new_slots = new_bench_slots(op.ctx, _buy_baseline, _after_shot)
        # 买牌动画(卡牌飞行)未收敛时首采会误判「新占槽=0」(L0 安灯误报
        # 实证)→ 延迟重采一次,仍无才交下方破缺判定。只动观测时序。
        _new_slots, _ = bench_buy_slots_settle_retry(
            len(_bought_names), _new_slots,
            lambda: new_bench_slots(op.ctx, _buy_baseline,
                                    op.screenshot()))
        if _new_slots and match is not None:
            _slot_map = dict(zip(_bought_names, _new_slots, strict=False))
            if not hasattr(match, 'bench_slot_map') or match.bench_slot_map is None:
                match.bench_slot_map = {}
            match.bench_slot_map.update(_slot_map)   # 合并(跨回合累积),非覆盖
            log.info(f'[cw-shop] char→slot(pixel-diff,合并):{_slot_map} → 全 map={match.bench_slot_map}')
        # 买牌落位对拍(观测自检框架设计 §2.2;纯记账零决策):像素差已给
        # 落位事实(上方 new_bench_slots),此处按设计判据分级留证——
        # 占位不出现(买≥1 张而新槽=0)是设计点名的硬失败形态(gap_large);
        # 计数总账与身份回读是留证级(设计明示「身份留证不算失败」;计数
        # 受卖出/合并引起的槽变化干扰,见 bench_buy_count_ok 注)。失败路径
        # 无 return/retry/屏蔽,买牌照常收工。
        with contextlib.suppress(Exception):
            _occ = bench_buy_occupancy_ok(len(_bought_names), len(_new_slots))
            _bench_refs = [{'stream': 'decisions',
                            'key': (f'plane={state.plane}|round={state.round_num}'
                                    f'|bought={len(_bought_names)}')}]
            if _occ is False:
                _occ_shot = None
                with contextlib.suppress(Exception):   # 截图 best-effort
                    _occ_shot = op.save_screenshot(prefix='bench_buy_no_slot')
                defects.record_defect(
                    'bench', 'invariant_break',
                    expected=(f'买{len(_bought_names)}张 → new_bench_slots '
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
            _cnt = bench_buy_count_ok(len(_bought_names), len(_new_slots),
                                      total_sell)
            if _occ is not False and _cnt is False:
                defects.record_defect(
                    'bench', 'invariant_break',
                    expected=(f'新占槽={len(_bought_names)} − 中途卖出'
                              f'{total_sell} = {len(_bought_names) - total_sell}'),
                    observed=f'pixel-diff 新占槽={len(_new_slots)}',
                    plane=state.plane, round_num=state.round_num,
                    verdict=('留证-落位计数不符(pixel-diff 不分方向,卖出/'
                             '合并槽变化计入,单元总账留证)'),
                    reader_source='bench_buy_pixel_diff',
                    gap_large=False, refs=_bench_refs,
                    note='观测自检框架设计 §2.2:新槽数累计=买牌数−中途卖出数')
            # 身份回读(留证级):SIFT 纯读走 identify_slots(无 ctx 依赖的
            # 纯 CV),**不经 read_bench_chars**——后者内置召唤物/书册卡停机
            # 钩子,买后动画帧误触停机即违背本对拍零行为约束。复用既有
            # _after_shot 帧 + ensure_portrait_templates 缓存,零新增读屏。
            _templates = ensure_portrait_templates(op.ctx)
            if _templates is not None:
                from sr_od.application.currency_war.obs.cw_identity_obs import (
                    _ctx_slots,
                    identify_slots,
                )
                _rb = identify_slots(_after_shot, _templates,
                                     _ctx_slots(op.ctx, '备战栏', 9), '')
                _missing = bench_buy_identity_missing(
                    _bought_names, [c.char_id for c in _rb])
                if _missing:
                    defects.record_defect(
                        'bench', 'perception_conflict',
                        expected=f'回读身份含买牌名:{sorted(_bought_names)}',
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
        total_buy=total_buy, total_level=total_level,
        total_refresh=total_refresh, total_sell=total_sell,
        total_sell_income=total_sell_income, total_sell_skip=total_sell_skip,
        total_sell_fail=total_sell_fail, spend_executed=_spend_executed,
        gold_open=gold_open, plan_truncated=_plan_truncated,
        refresh_skipped=_refresh_skipped, refresh_attempted=_refresh_attempted,
        refresh_board_changed=_refresh_board_changed,
        buy_purchases=_buy_purchases, buy_has_sell=_buy_has_sell,
        buy_unidentified=_buy_unidentified, buy_pre_bench=_buy_pre_bench,
        buy_pre_deployed=_buy_pre_deployed)
    return None, outcome


class CwOpBuyCards(SrOperation):
    """备战-开商店原子 op:执行商店动作波循环(W970 批 A 契约 §4.2)。

    生产路径由 BuyShopCards 编排壳直调 :func:`run_buy_waves`(宿主 op 复用,
    保证读屏次序/替身桩行为等价);本类为独立可跑壳(``run_operation``
    单跑定位失败步,W970 批 C 流程层接管后成为编排单元)。
    hp 三件组缺省 (None, False, False) = 无覆盖(商店开态 HP 区本就不可读,
    单跑调试语义);生产入口必须传 shop 关闭帧读链产物。
    """

    def __init__(self, ctx: SrContext, hp_value: int | None = None,
                 hp_readable: bool = False, hp_trusted: bool = False):
        SrOperation.__init__(self, ctx, op_name='货币战争-买牌')
        self._hp_value = hp_value
        self._hp_readable = hp_readable
        self._hp_trusted = hp_trusted

    @operation_node(name='买牌', is_start_node=True)
    def buy(self) -> OperationRoundResult:
        rr, outcome = run_buy_waves(self, self.ctx.cw_match,
                                    self._hp_value, self._hp_readable,
                                    self._hp_trusted)
        if rr is not None:
            return rr
        return self.round_success(
            f'plan 买{outcome.total_buy}张 升{outcome.total_level}次 '
            f'刷{outcome.total_refresh}次 卖{outcome.total_sell}张')
