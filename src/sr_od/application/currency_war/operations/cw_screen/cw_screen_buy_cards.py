
import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_occupied,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_of,
    tracked_unobserved,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    area_center,
    shop_card_click_points,
)
from sr_od.application.currency_war.kernel.cw_screen_report.buy_cards import (
    CwScreenBuyCardsObs,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.kernel.cw_telemetry_exit import journal_refs
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionBuyCardParam,
    CwActionDeployMoveParam,
    CwActionLevelUpParam,
    CwActionLevelUpShopParam,
    CwActionRefreshShopParam,
    CwActionSellBenchParam,
)
from sr_od.application.currency_war.obs.cw_observation import (
    PHASE_PREP_SHOP_OPEN,
    GameStateReadReceipt,
    ensure_portrait_templates,
    new_bench_slots,
    read_game_state,
    read_gold_opt,  # noqa: F401  模块属性路由:cw_shop_action_ops 经本模块名取读函数(替身缝)
    read_shop_cards,  # noqa: F401  替身缝:测试经本模块名桩读链(非本文件运行时消费)
)
from sr_od.application.currency_war.obs.cw_shop_refresh_obs import (
    refresh_board_changed_of,
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
    from sr_od.application.currency_war.kernel.cw_vocab import (
        Action,
        CwActionCloseShopParam,
        CwActionLevelUpShopParam,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopVisitLedger,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        CurrencyWarMatch,
    )


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


# 牌名集三值对比单一源 = cw_shop_refresh_obs.refresh_board_changed_of
# (消费点 = 刷新回执 extra 与本文件入口观察对账点);判效权归观察侧
# reconcile。


def _shop_entry_names(shop: list) -> list[str]:
    """入口回执 shop 域 → content 具名牌名集(两路径形态兼容)。

    读路径条目 = 槽包装(kind/card);容器紧缩路径(``_entry_receipt_from_
    container``)= 裸 card(缺 kind 视作 content,该路径本就只产 content)。
    """
    names: list[str] = []
    for _s in shop or []:
        _kind = getattr(_s, 'kind', 'content')
        _name = getattr(getattr(_s, 'card', _s), 'name', '') or ''
        if _kind == 'content' and _name:
            names.append(_name)
    return names


def _record_free_refresh_proc(op: SrOperation, ledger: 'ShopVisitLedger', *,
                              pre_gold: int, gold_after: int,
                              pre_names: list[str], post_names: list[str],
                              plane: int, round_num: int) -> None:
    """免费刷新 proc 留证(ADR-0456 通道;对账类判定,宿主 = 入口观察
    对账点)。

    比对收口纪律(T-219 裁定):判定随对账走不随动作走——三腿比对
    (上段刷新已发 ∧ 金未扣 ∧ 牌面已变)在对账点评完才进本函数,函数体
    只做存证(截图+flag+log),零决策零改道;免费来源的频率汇总与处置
    归 flag 消费方。通道归属 = 观察侧对账点(按比对收口纪律维护),
    非独立的常驻承诺。
    """
    from datetime import datetime as _dt

    from one_dragon.utils.file_utils import get_project_root
    from sr_od.application.currency_war.telemetry import state as _cw_tel
    _free_shot = op.save_screenshot(prefix='free_refresh_proc')
    _flag_p = get_project_root() / '.debug' / 'temp' \
        / 'cw_free_refresh_proc.flag'
    _flag_p.parent.mkdir(parents=True, exist_ok=True)
    _flag_p.write_text(
        'FREE-REFRESH-PROC: 免费刷新实机正证据(非停机,bot 照常跑)\n'
        f'run={_cw_tel.current_run_id()} '
        f'plane={plane} round={round_num} '
        f'wave={ledger.total_refresh} '
        f'ts={_dt.now().isoformat(timespec="seconds")}\n'
        f'前后牌面: {sorted(pre_names or [])} -> {sorted(post_names or [])}\n'
        f'gold: 前={pre_gold} 后={gold_after}(未扣=免费)\n'
        f'截图: {_free_shot}\n'
        '处理: 汇总频率判免费来源(棱 45%/策略类/未知),确认后删本 flag;'
        '通道住观察侧对账点(比对收口纪律)。\n',
        encoding='utf-8')
    log.warning(
        '[cw!][shop] 免费刷新 proc:牌面已变 金未扣(前=%s 后=%s)'
        '→ 留证不停 flag=cw_free_refresh_proc.flag',
        pre_gold, gold_after)


def _reconcile_refresh_pending(op: SrOperation, ledger: 'ShopVisitLedger',
                               entry: GameStateReadReceipt) -> None:
    """免费刷新对账点(对账类判定收口,宿主 = 入口观察;T-219 裁定 +
    统一动作工厂批4 比对收口扩展)。上段刷新已发
    (ledger.refresh_pending_reconcile,写入端 = RefreshShopOp.execute)
    → 两腿零决策判定:

    - 免费腿:金未扣(入口金 = 刷前金)∧ 牌面已变——三值对比单一源 =
      ``cw_shop_refresh_obs.refresh_board_changed_of``(刷前/刷后名集由
      RefreshShopOp 落账,批4 自动作 op 迁出)→ 存证(截图+flag+log);
    - 期望腿(refresh_expect_mismatch,批4 自 RefreshShopOp 迁入):刷前
      构建的期望随账本外发(ledger.refresh_expect),与入口观察金/具名
      牌数对票,失配落缺陷台账——零决策留证语义由缺陷台账承接。

    任一腿失读/不满足 = 静默放行(宁缺勿造);标记消费即清(清点在调用
    方),生命周期 = 一次刷新恰一段(刷新为终结 op,段间无其他动作覆盖
    字段)。判定值源同帧化申报:免费腿牌面判定与存证 post_names 同取
    入口观察帧(迁出前 = 点击后现读与入口读两窗口;刷新为终结 op,段间
    无写面,两读恒同板面)。
    """
    _entry_names = _shop_entry_names(entry.shop)
    if (refresh_board_changed_of(ledger.refresh_pre_names, _entry_names) is True
            and ledger.refresh_pre_gold is not None
            and entry.gold == ledger.refresh_pre_gold):
        with contextlib.suppress(Exception):
            _record_free_refresh_proc(
                op, ledger,
                pre_gold=ledger.refresh_pre_gold,
                gold_after=entry.gold,
                pre_names=ledger.refresh_pre_names,
                post_names=_entry_names,
                plane=entry.plane, round_num=entry.round_num)
    if ledger.refresh_expect is not None:
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
            refresh_reconcile_mismatches,
        )
        for _m in refresh_reconcile_mismatches(ledger.refresh_expect[0],
                                               entry.gold, len(_entry_names)):
            defects.record_defect(
                'shop', 'refresh_expect_mismatch',
                expected=(f'{_m["domain"]}/{_m["slot"]}: '
                          f'{_m["expected"]}'),
                observed=_m['observed'],
                plane=ledger.refresh_expect[1],
                round_num=ledger.refresh_expect[2],
                verdict='留证-刷新期望不符(零决策)',
                reader_source='refresh_expect_reconcile',
                note='期望三输入波前现读,None 跳过;'
                     '判据真值表已锁')


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

    本单元执行了 ≥1 次 CwActionBuyCardParam → ``new_bench_slots``(pixel-diff,身份无关)
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

    期望:新占槽数累计 = 本单元 CwActionBuyCardParam 数 − 中途卖出数(设计原文口径)。
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

    「仅刷新波」= plan 首动作即 CwActionRefreshShopParam(执行前缀截在该刷,波内
    无任何买卡/升级/卖出)。此时波循环顶的整帧读未被本波动作污染,
    state.gold / state.shop 即刷新点击前现读——``w592_free_refresh_fix/``
    (ADR-0456 勘误)禁用 state.shop 当刷前读的失效条件(「波内买卡
    不从 state.shop 摘已买牌」)在仅刷新波不成立,可安全复用。
    返回 False 的波(前缀含买/卖)维持刷前 pre-shot 现读,语义不变。
    """
    return bool(actions) and isinstance(actions[0], CwActionRefreshShopParam)


def _shop_entry_read(op: SrOperation, match: 'CurrencyWarMatch',
                     ) -> tuple[GameStateReadReceipt | None, Any,
                                OperationRoundResult | None]:
    """商店入口观察读半部(段顶唯一读屏点的读+防抖+停机闸三段;
    生产读屏路径与观察 node 共用单一实现,零第二转录)。

    - read_game_state 直连(漏斗容器直写 + 原生回执);
    - 店开入口防抖:开店转场/淡入帧可令收起锚 miss → shop payload 未入
      容器(fresh 容器无上一牌面可沿用,decide 前置门即炸——实机买光店
      五败定谳),有界重读(3 × 0.8s)直至 shop 入容器;仍缺 = 真离屏/
      持续失读,交由决策前置门大声失败(禁静默空态);
    - 商店未识别卡停机(2026-09-16 迁移+框架化,用户裁定「识别不到就是
      bug」):判据 = 读链终判(read_shop_cards 内部易误判重观察之后)仍含
      unknown 槽;处置 = stop_running(框架截图留证 + [stop] 日志行)+
      round_fail,协作停机窗内不续波,交回外循环收口。处理流程知识归
      guards.md §3。

    Returns:
        (入口回执, 入口帧, None) 正常;(None, None, round_fail) 停机闸
        命中(stop_running 已发,调用方以 (round_fail, None) 收工)。
    """
    _entry_shot = op.screenshot()
    _entry = read_game_state(op.ctx, _entry_shot,
                             phase=PHASE_PREP_SHOP_OPEN,
                             screen_name=SHOP_SCREEN_NAME)   # ADR-0462 开店动作期
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_of as _gs_of_debounce,
    )
    for _attempt in range(3):
        if _gs_of_debounce(match.session).shop.value is not None:
            break
        time.sleep(0.8)
        _entry_shot = op.screenshot()
        _entry = read_game_state(op.ctx, _entry_shot,
                                 phase=PHASE_PREP_SHOP_OPEN,
                                 screen_name=SHOP_SCREEN_NAME)
    _unk = [i + 1 for i, s in enumerate(_entry.shop)
            if getattr(s, 'kind', '') == 'unknown']
    if _unk:
        log.warning('[cw!] [shop] 未识别卡槽%s(读链终判)→ 停机留证待建档',
                    _unk)
        _rc = getattr(op.ctx, 'run_context', None)
        if _rc is not None:
            _rc.stop_running(reason='hook:shop_unknown_card',
                             save_screenshot=True)
        return (None, None, op.round_fail(
            status=f'shop 未识别卡槽{_unk},停机留证'))
    return _entry, _entry_shot, None


def _form_progress(comp: 'Comp', session) -> float:
    """fp 遥测helper(review 要求:fp 轨迹可观测;调用方保证 comp 非 None)。

    归属申报:state 原经过渡桥装箱 = 统一 state 过渡桥语义
    (T-70 线),本 hunk 实际随 T-13 提交入库而原提交信息未申报,此处
    补记归属供审计对账。**换源(T-146,T-163 后措辞更正)**:T-163 删帧
    链后本 helper 输入域 = 段顶入口观察帧(非 simulate 推演态,旧措辞
    「波内逻辑态帧」作废);该帧在 visit 段顶已合成进 session 容器单例,
    本读改直取单例(board 同帧同源),桥消费随之清零。
    """
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    return form_progress(comp, game_state_of(session))


# 「购买经验」按钮(= 买经验升等级)screen_info area 名;中心运行时读(area_center)
BUY_EXP_AREA: str = '备战标识-购买经验'


def _fmt_action(a: 'Action') -> str:
    """单 Action → 紧凑日志串(调试/复盘读 plan 用)。"""
    if isinstance(a, CwActionBuyCardParam):
        return f'Buy({a.card.faction}/{a.card.name}/{a.card.cost})'
    if isinstance(a, (CwActionLevelUpParam, CwActionLevelUpShopParam)):
        return f'LvUp({a.cost})'
    if isinstance(a, CwActionDeployMoveParam):
        return f'Deploy(bench{a.bench_idx}->{a.to_row})'
    if isinstance(a, CwActionRefreshShopParam):
        return 'Refresh'
    if isinstance(a, CwActionSellBenchParam):
        return f'Sell(bench{a.bench_idx})'
    return type(a).__name__


def apply_action_outcome(
        action: 'CwActionBuyCardParam | CwActionRefreshShopParam | CwActionSellBenchParam | CwActionLevelUpShopParam | CwActionCloseShopParam',
        _ok: bool, _cur: 'GameStateReadReceipt',
        match: 'CurrencyWarMatch', ledger: 'ShopVisitLedger',
        visit_actions: list) -> None:
    """执行结果落地门(调用环单一源;落地审补办清单 C1 调用环级锁的承载体。

    C1 语义 = 旧 return True 使期望账逻辑态与 tracked 实账分叉;应修-2 语义
    = 已买集无条件追加使检出帧名污染 prefer_names/churn(落地审补办审,
    2026-09-05;原清单为会话产物不入库,语义以此为准)。

    未落地(_ok=False,如执行侧检出购买未生效)⇒ **两侧都不动**:不写逻辑态、
    不入「已买」集(防检出帧名污染 prefer_names/churn/P60,应修-2)。
    容器逻辑态直写已随动作 op 重组批③ 收编进各 op 自上报(op 内直调
    自己的上报函数,design.md §1.3)——原非终结直写块(apply_shop_action_
    logic + 合成升星腿)删除 = 双记防线;终结跳写判断随 op 自辖不再需要。
    本门保留面:卖出 route-tag 泄漏显影、效果账本 BUY 计数。(刷新侧
    计数与留证票已随 2026-09-18 迁入裁决归刷新 op 自上报单口,见
    cw_refresh_shop_action。)

    ``_cur`` = 段顶入口观察回执(defects 留证行 plane/round 基准;载体 =
    :class:`GameStateReadReceipt`,visit 内 plane/round 恒定不变)。
    """
    visit_actions.append(action)
    if _ok and isinstance(action, CwActionSellBenchParam):
        # T-159 §3.3 误标检出位(s1_reset_mischannel 交叉对账的运行时半):
        # 商店域落地门不辖 S1 清键(落域澄清:店内段 S1 语义正在成立中,
        # 域内卖出经由六序域内闭环旗标无感)——landed 族 A 卖出若携带
        # 备战域白名单 route tag = tag 泄漏进商店域的结构性错位,计数
        # 显影(现役构造面不可达:族 A 动作无 route_tag 字段,防御位)。
        # 离线对账半 = s1_reset_by_* 与卖出通道计数交叉判读。
        from sr_od.application.currency_war.kernel.cw_vocab import (
            S1_RESET_ROUTE_TAGS,
        )
        _rt = getattr(action, 'route_tag', '') or ''
        if _rt in S1_RESET_ROUTE_TAGS:
            _st_mis = strategy_state_of(match.session)
            _ct_mis = getattr(_st_mis, 'cw4_counters', None)
            if isinstance(_ct_mis, dict):
                _ct_mis['s1_reset_mischannel'] = \
                    _ct_mis.get('s1_reset_mischannel', 0) + 1
    if _ok and isinstance(action, CwActionBuyCardParam) and action.card.name:
        strategy_state_of(match.session).cw4_visit_bought_names.append(action.card.name)
        # 效果账本购买计数推进(迁移批次三,设计 §5.1「刷新=计数累加」的
        # 购买侧;载体 = CounterKey.BUY,§5.3 返利族「每购 3 张 5 费」计数
        # 面)。挂点 = 执行落地门(未落地不计数,同刷新计数组纪律)。
        # best-effort 记录面,失败不阻塞执行回执链。
        try:
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                CounterKey,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            game_state_of(match.session).effects.bump_key(CounterKey.BUY)
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-buy] 效果账本 BUY 计数失败(不阻塞): {e}')
    # 刷新侧保留面已随 2026-09-18 迁入裁决清空:三计数(效果账本统一计算)
    # 由刷新 op 自上报经上报函数单口触发(sink 吸收路径 = 接收侧补触发),
    # 真值↔账本分歧/次数联动两张留证票随真值读搬进刷新 op(点击前同帧
    # 口径)。本门刷新侧零代码。
    # (容器逻辑态直写块已随动作 op 重组批③ 删除:非终结动作的期望态
    #  推进 = op 自上报单点(apply_shop_action_logic/apply_shop_merge_leg
    #  调用面退役,双记防线 = 本删除);终结动作跳写语义由 op 自辖。
    #  段内续动作标记照常落账。)
    ledger.refresh_first_action = False


def accrue_release_spent(match: 'CurrencyWarMatch',
                         action: 'CwActionBuyCardParam | CwActionRefreshShopParam | CwActionSellBenchParam | CwActionLevelUpShopParam | CwActionCloseShopParam',
                         ok: bool) -> None:
    """v3_release_spent 执行回执位记账(T-88 写点;裁决 = ADR-0571)。

    首版口径 = **只计刷新实花**(「宁窄勿虚」的遥测诚实性选择:买牌/
    升级是否计入「义务实花」全渠道口径在 mandate_v1 语义下未经证明,
    混入会虚高——扩口径挂 ADR-0571 待裁)。刷新单通道前提:R1 = 今日
    唯一刷新发射点(kernel/cw_state.CwActionRefreshShopParam.reason 值域契约)。
    记账位语义 = 动作执行成功回执(本函数在 apply_action_outcome 之后
    调用),轮键 = 容器读口现读(迁移批 3.2:原入口帧 plane/round 形参
    随黑板帧退役删除;visit 内轮键恒定,容器同值)。

    F4 栈守卫:仅当披露面轮键戳 == 当前 (plane, round)(即 mandate_v1
    本轮 prep 装配已跑)才累计——非 mandate_v1 栈(异型策略状态对象无
    键戳)或键戳过期帧不累计,防「spent>0 而预算三字段=None」的混合行
    形态(recorder「default 栈帧无写点 → None 语义」声明)。字段经防御
    getattr 访问(披露面形态;ADR-0563 B4 收缩申报)。
    """
    if not ok or not isinstance(action, CwActionRefreshShopParam):
        return
    from sr_od.application.currency_war.kernel.cw_game_state import (
        plane_of,
        round_num_of,
    )
    _gs_ar = game_state_of(match.session)
    st = strategy_state_of(match.session)
    key = (int(plane_of(_gs_ar)), int(round_num_of(_gs_ar)))
    if getattr(st, 'v3_disclosure_key', None) != key:
        return
    st.v3_release_spent += max(0, int(getattr(action, 'cost', 0) or 0))


def note_shop_action_receipt(match: 'CurrencyWarMatch', action: 'Action', *,
                             applied: bool, reason: str = '',
                             extra: dict | None = None,
                             include_payload: bool = True) -> None:
    """商店动作执行回执(R2 §3.2.5;receipts 域,渠道② logic_action)。

    run_buy_waves 的**单一写点**:逐动作执行落地挂点 + 受阻挂点(刷新
    硬墙跳过 / spend_gate 政策闸拒)都经本函数落一条回执行(每动作 op
    一条 logic_action 行;受阻 = applied=false + reason + 执行面结构化
    字段——exec_events「受阻/放弃可见」收编)。发出即簿记非验证(M1③):
    applied = 动作 op 自身机械事实透传,零成败判定。journal 常开(ADR-0634)
    回执写入无条件,无局跳过在
    kernel 口(:func:`~...kernel.cw_game_state.note_action_receipt`);
    best-effort 不阻塞循环。

    ``include_payload``:True = 回执行附带 ``action`` 键(serialize_action
    同 schema)。缺省 True = 发射行(execute 后落点);受阻挂点(硬墙/闸拒,
    动作未发射)传 False,载荷不入行。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            note_action_receipt,
        )
        session = getattr(match, 'session', None)
        if session is None:
            return
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        from sr_od.application.currency_war.telemetry.schema import (
            serialize_action,
        )
        _extra = dict(extra or {})
        if include_payload:
            _extra['action'] = serialize_action(action)
        note_action_receipt(
            game_state_of(session), op=type(action).__name__,
            applied=bool(applied), reason=reason, screen=SHOP_SCREEN_NAME,
            actor='CwScreenBuyCards', extra=_extra)
    except Exception as e:  # noqa: BLE001  回执失败不阻塞循环
        log.warning('[cw][receipt] 商店动作回执写入失败(不阻塞): %s', e)


# ===== 未观察商店访问:跳过留痕与连续跳过熔断(T-268 ④)=====

#: 连续「未观察跳过」熔断上限(对局级,载体 = strategy_state.cw4_counters)。
#: K=2 论证(改值前先驳):跳过链 = 策略关店 → 编排壳收店 → 外循环备战
#: 分支 heavy 观察(reconcile 置 observed)→ 再进店。连续两次跳过 = 两轮
#: 完整 heavy 观察均未锚定(识别域未就绪/读链退化类结构性形态),非单帧
#: 瞬时;继续静默循环 = 无界重试,禁。
SHOP_UNOBSERVED_SKIP_LIMIT: int = 2

#: 连续跳过计数的载体键(cw4_counters;执行控制键非纯观测:参与熔断
#: 谓词,判读同表)。写点 = _note_shop_skip_unobserved 递增 / run_buy_waves
#: 段顶复位;消费点 = 本函数熔断谓词。
CW4_KEY_SHOP_SKIP_UNOBSERVED_STREAK = 'shop_skipped_unobserved_streak'


def _note_shop_skip_unobserved(op: SrOperation,
                               match: Any) -> OperationRoundResult | None:
    """未观察态商店访问跳过的留痕与熔断(T-268 ④;CwActionCloseShopParam 出口消费)。

    触发形态:策略未观察门(strategies/impl/flow.py decide_shop_action)
    返回恒可用终结 CwActionCloseShopParam → 本 visit 零动作收工。每次跳过 = 缺陷台账
    分键 ``shop_skipped_unobserved`` 留一行(防静默)+ 连续计数 +1;计数达
    ``SHOP_UNOBSERVED_SKIP_LIMIT`` = 锚定失败显式出口(round_fail 交兜底
    链,禁无限静默重试)。载体缺席(非 mandate 生产形态)= 只留痕不计数
    不熔断(无停机语义可落,保守端与缺省口径一致)。

    Returns:
        None = 留痕完成,调用方照常收工;OperationRoundResult = 熔断停机
        支,调用方以 (round_fail, None) 收工。
    """
    _ct = getattr(strategy_state_of(match.session), 'cw4_counters', None)
    _streak = 0
    if isinstance(_ct, dict):
        _streak = _ct.get(CW4_KEY_SHOP_SKIP_UNOBSERVED_STREAK, 0) + 1
        _ct[CW4_KEY_SHOP_SKIP_UNOBSERVED_STREAK] = _streak
    with contextlib.suppress(Exception):
        defects.record_defect(
            'bench', 'shop_skipped_unobserved',
            expected='商店访问时 tracked 主账已按屏幕真值锚定(observed)',
            observed=('tracked 未观察(接管/失效后备战 heavy 观察未完成'
                      '锚定)→ 本 visit 零动作跳过'),
            verdict=('留证-未观察商店访问跳过(策略关店交回外循环,备战环'
                     'heavy 观察锚定后再进店;连续跳过查 '
                     'shop_skipped_unobserved_streak 计数,达上限熔断停)'),
            reader_source='decide_shop_action_unobserved_gate',
            gap_large=False,
            note='分键登记 = 本写点注释(内联 kind,先例 = seed_divergence 族)')
    log.warning('[cw!][shop] tracked 未观察 → 商店访问跳过(策略关店,'
                '连续 %s/%s)', _streak, SHOP_UNOBSERVED_SKIP_LIMIT)
    if isinstance(_ct, dict) and _streak >= SHOP_UNOBSERVED_SKIP_LIMIT:
        with contextlib.suppress(Exception):
            op.save_screenshot(prefix='shop_skip_unobserved_stop')
        with contextlib.suppress(Exception):
            defects.record_defect(
                'bench', 'shop_skipped_unobserved_stop',
                expected=(f'关店→备战 heavy 观察→再进店链在 '
                          f'{SHOP_UNOBSERVED_SKIP_LIMIT} 次内完成锚定'),
                observed=f'连续 {_streak} 次商店访问仍未观察(锚定失败)',
                verdict=('停机-未观察连续跳过熔断(锚定失败显式出口;'
                         '判读查 heavy 观察链:portrait 模板加载/'
                         'observe_full bench 读数/reconcile 健康门)'),
                reader_source='decide_shop_action_unobserved_gate',
                gap_large=True,
                note='分键登记 = 本写点注释(同跳过分键口径)')
        log.error('[cw!] 未观察商店访问连续 %s 次(上限 %s)→ 锚定失败'
                  '显式出口,round_fail 交兜底链', _streak,
                  SHOP_UNOBSERVED_SKIP_LIMIT)
        return op.round_fail(
            f'未观察商店访问连续跳过 {_streak}/{SHOP_UNOBSERVED_SKIP_LIMIT}'
            f'(锚定失败,交兜底链)')
    return None


def run_buy_waves(op: SrOperation, match: 'CurrencyWarMatch | None',
                  *, spend_gate: Callable[[object], tuple[bool, str]] | None = None,
                  pre_entry: 'tuple[GameStateReadReceipt, Any] | None' = None,
                  ) -> tuple[OperationRoundResult | None, 'ShopVisitLedger']:
    """商店单动作循环主体(ADR-0517 迁移批;前身份 = 买牌波循环)。

    ``spend_gate``(缺省 None = 既有行为零漂移):可选单动作政策闸,发射帧
    受限消费仲裁消费(出口 B;kernel 判定单一源 =
    ``kernel/cw_launch_arbitrage.launch_arbitration_gate``,ADR-0566)。
    语义 = 逐动作执行前咨询;``(False, why)`` ⇒ 该动作**不执行**、本访问
    即刻收工(拒绝语义 = 消费终止非跳过续试:跳过高位动作改试低位 = 重排
    既有评估序,违金出口族红线 5)——同为「终结降级关店」路径,关店由
    编排壳承担。闸自身遥测由闭包侧计数,本函数零感知闸语义。

    ``pre_entry``(缺省 None = 既有行为零漂移):CwScreenBuyCards 观察 node
    已完成的段顶入口观察 ``(回执, 帧引用)``,首段复用不重读(迁移不增加
    读屏;防抖与未识别卡停机闸已在观察 node 过闸);缺省 None = 段顶照旧
    现读(生产编排壳直调路径,行为逐位不变)。

    一次画面访问 = 轮「入口观察 + 逐动作决策循环」(ADR-0517 决策 1):

    - 入口观察(段顶,唯一读屏点):真实读屏 → 漏斗容器直写(obs 族 sig,
      决策读单源 = 容器单例;迁移批 3.2 起 read_game_state 不再构造帧,
      返回 :class:`GameStateReadReceipt` 供逐帧读数消费;黑板槽已退役,
      visit 基准载体 = 局部 ``_cur`` 回执);
    - 决策循环(零读屏,决策 1/8):``decide_shop_action`` 每次恰返回一个
      动作 → proposal 守卫(``guard_proposal_vs_expected``,防策略器算术
      bug)→ 执行(动作 op ``execute``,观测通道候选 a
      遥测在内)→ 容器逻辑态直写推进期望态(op 自上报,上报函数族
      简单腿 + 合成升星腿;T-163 起零 simulate 前瞻消费)。tracked 未观察
      时策略门返回 CwActionCloseShopParam = 跳过访问,留痕与熔断见段顶/出口注(T-268)。
    - 终结 op(CwActionRefreshShopParam/CwActionCloseShopParam):执行即本段结束。刷新终结 = 交回
      外循环重进——物理载体 = 本函数段循环的下一次迭代(入口观察重建,
      读屏次数与波批持平,ADR-0517 §读屏成本·节奏对拍);关店终结 = 本
      访问收工(关店点击由编排壳 CwOpCloseShop 承担)。刷新无次数上限
      (用户裁定:无限刷新环 = 策略实现 bug,框架不兜底)。

    (访问内 hp 决策消费统一经容器政策读口 decision_hp,门前真值由备战帧
     观察/结算既有写端承接,段间无战斗值同源,覆盖回写是绕行。)

    match=None(独立 run_operation 调本 op)→ 兜底建核:直调引导漏斗
    establish_new_match 建容器挂 ctx(供漏斗写块寻址;局外不复用 =
    先弃置残留容器,每次独立调用新建)。config 本函数内构造(W970 §4.3.4)。

    返回 (失败 round 结果, 访问账本)。正常收工 → (None, ledger);
    未识别卡停机钩子触发 → (round_fail 留证结果, None)。
    (迁移批 3.2:产出载体 = ShopVisitLedger 本体——BuyCardsOutcome 已退役,
    动作账/期望态基座随账本外发。)
    """
    # 工厂住单一注册表(动作 op 重组批③:op 构造 = 注册表类级解析 +
    # (ctx, param, env) 组装,design.md §1.3)
    from sr_od.application.currency_war.kernel.cw_vocab import CwActionCloseShopParam
    from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
        action_op_class_for,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopExecEnv,
        ShopVisitLedger,
        guard_proposal_vs_expected,
    )

    config = CurrencyWarConfig(op.ctx.current_instance_idx)
    if match is None:
        # 防御:无对局态(独立 run_operation 调本 op)→ 兜底建核,直调
        # 引导漏斗同款序(establish_new_match = 生产唯一容器建立漏斗)。
        # 此前裸构造 CurrencyWarMatch 与漏斗实差三处行为——rng 种子(漏斗
        # 按 config.strategy_seed 播 session.rng)/布局未知态计数复位
        # (reset_layout_unknown_state 新局起点)/遥测 run_id_provider
        # (局容器建立点注入 journal 装配)——终态切换批改道漏斗一并消除;
        # 策略实例化同漏斗走 StrategyManager 按 config.strategy_id,不再
        # 硬编 mandate_v1。「局外不复用」语义保持:先弃置残留容器再建
        # (每次独立 run_operation 新建;与入口链 CwEntryStart 的
        # discard+establish 同款衔接),漏斗幂等分支经前一步清场必走新建。
        from sr_od.application.currency_war.strategies.impl.cw_strategy import (
            discard_stale_match_container,
        )
        from sr_od.application.currency_war.strategies.impl.cw_strategy_manager import (
            establish_new_match,
        )
        discard_stale_match_container(op.ctx, 'buy_cards_defensive_rebuild')
        establish_new_match(op.ctx, config)
        match = op.ctx.cw_match

    # 牌位/升级/刷新中心从 screen_info 直取;area 缺失 = 建档漂移,显式
    # round_fail(信息带 area 名),禁兜底坐标静默点击(坐标单一真相源)。
    # 方向视图由策略器决策入口内化刷新(帧代次标注触发,ADR-0583)。
    click_pts = shop_card_click_points(op.ctx)
    level_btn = area_center(op.ctx, BUY_EXP_AREA)
    if level_btn is None:
        return (op.round_fail(
            f'area 缺失:{BUY_EXP_AREA}({SCREEN_NAME}),禁兜底点击'), None)
    refresh_btn = area_center(op.ctx, '按钮-刷新', SHOP_SCREEN_NAME)
    if refresh_btn is None:
        return (op.round_fail(
            f'area 缺失:按钮-刷新({SHOP_SCREEN_NAME}),禁兜底点击'), None)

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
    # (对拍基线 gold_open 随 outcome 退役移出本函数——迁移批 3.2:基线
    #  = 编排壳在 visit 入口的容器 gold 现读暂存,单一捕获点同供安灯。)
    _buy_baseline = op.screenshot()
    # 执行边界压缩:首段入口观察已带全量语境(替代原开店后独立读);
    # _entry_frame_marked = visit 首段已标 full(续段标 none,连击续刷判定输入
    # 所在的段循环共用此分段);
    # _prev_refresh_only = 上一段是「仅刷新段」(连击续刷判定输入,
    # 判据单一源 = refresh_wave_is_refresh_only)。
    _entry_frame_marked = False
    _prev_refresh_only = False
    _entry: GameStateReadReceipt | None = None
    _pre = pre_entry
    while True:
        ledger.refresh_first_action = True   # 段级复位(仅刷新段判定输入)
        # did_refresh 段级复位(终结 op 语义 review 修复批暴露):两消费点
        # (段尾 _prev_refresh_only / did_refresh=False 收工判定)语义都是
        # 「本段」——不复位时首段刷新后的所有后续段都被陈旧 True 钉住。
        ledger.did_refresh = False
        if _pre is None and not _prev_refresh_only:
            time.sleep(0.3)  # 等 board 面板 settle(连击续刷段前一动作是刷新,面板未变,跳过;
                             # 首段入口观察已由观察 node 完成时本段 park+读半在彼处,同样跳过)
        if _pre is not None:
            # 首段:入口观察已由 CwScreenBuyCards 观察 node 完成(_shop_entry_
            # read:防抖与停机闸已过)——本段复用其回执,不重读(迁移不增加
            # 读屏);段头其余簿记照常。
            _entry, _entry_shot = _pre
            _pre = None
        else:
            # 光标 parking(审计 P0,2026-08-16):上轮 CwActionBuyCardParam/CwActionLevelUpParam/Refresh 点击后光标停在按钮上
            # → 污染本帧 read_game_state;park 后再读。
            op.park_cursor(after_wait=0.1)
            # ---- 入口观察(ADR-0517 决策 1/8:唯一读屏点,即对账)----
            # (观察源端口分支已随画面 op 基类退役删除:read_game_state
            #  直连 = 唯一路径,读+防抖+停机闸三段单一实现 = _shop_entry_read。)
            _entry, _entry_shot, _stop = _shop_entry_read(op, match)
            if _stop is not None:
                return (_stop, None)
        save_decision_frame(op, 'shop_entry', _entry_shot)   # 识别完成点原始帧留证(牌面仲裁基准;每段一帧,刷新重观察同点覆盖)
        # 免费刷新对账点(T-219 裁定:对账类判定收口在观察态写入的对账
        # 点,动作 op 内不做;批4 比对收口扩展 = 两腿判定迁宿主
        # ``_reconcile_refresh_pending``——免费腿三值单一源在观察侧模块,
        # 期望腿缺陷台账承接,零决策零改道)。任一腿失读/不满足 = 静默
        # 放行(宁缺勿造);标记消费即清,生命周期 = 一次刷新恰一段
        #(刷新为终结 op,段间无其他动作覆盖)。
        if ledger.refresh_pending_reconcile:
            _reconcile_refresh_pending(op, ledger, _entry)
            ledger.refresh_pending_reconcile = False
        # (hp 三件组覆盖随黑板帧退役删除——迁移批 3.2,波 4 步 4 同款结论:
        #  容器 hp 由备战帧观察/结算既有写端承接,消费统一经 decision_hp,
        #  覆盖回写 = 绕行;传参链同批移除。)
        # 节点类型来源 = 派生管线四②「商店查现行链」(kernel 派生步在店开
        # 上下文写入时自查链直定 node.kind,链观察落地批接线)。本处的台账
        # 本处无台账回填写端——logic 通道覆盖会吞掉派生层的观察对账,
        # 且属流程层散写。ADR-0587 滞后拷贝禁令(禁退回 last_node_type)
        # 继续有效,由查链零内建回落语义承接:链缺位 = kind None → ②(b)
        # 不发射,同 None fail-open 语义。
        # (frame.dual_track_phase/focus_factions 回填点已随 last_state 链
        #  退役批删除(T-166 对账表 E 类行 30/31 兑现):决策读端 =
        #  committed_from(session) 派生与 StrategyState 真家,帧字段无
        #  消费面,随帧退役不迁容器。)
        # (gold 救援补写已删,用户裁定:动作过程不含观察——首读假 0 的
        #  自愈归下一入口观察,假 0 期间策略按容器值决策自然空过一段。)
        # (开店首读金快照 gold_open 随 outcome 退役移出本函数——迁移批
        #  3.2:基线 = 编排壳 visit 入口容器 gold 现读暂存,详见 visit_open_shop。)
        # 播种单一源 = tracked_bench_chars(带 star+merge,mutate/对账全程同步)。
        # 空 = bench 真空(全部署/合成清空的事实正确态),不回退任何残账——
        # 旧 tracked_bench 回退分支已退役:单动作架构下「首轮」场景由入口
        # heavy 读屏重建(ADR-0517 决策 8,入口观察即对账);残账仅 CwActionBuyCardParam
        # 追加、无人清理,回退会复活陈旧名(实证 = 2026-09-05 CwActionOpenShopParam
        # 双账分叉事故,诊断档
        # .debug/temp/currency_war/20260905_openshop_fork_diag/report.md)。
        # (tracked 播种已随 W6 波 4 黑板容器化取消——设计件 §2.1-5:容器
        #  bench = prep 帧观察值(观察漏斗写端)+ visit 内逻辑态直写;黑板帧
        #  播种的唯一消费者 = 旧帧决策链,读者切换后无行为面。)
        if game_state_of(match.session).tracked_books.bench:
            log.info(f'[cw] tracked_bench_chars='
                     f'{[(c.char_id, c.star) for c in game_state_of(match.session).tracked_books.bench if c is not None]}'
                     f'(播种取消,仅日志显影)')
        # 段顶入口观察的局内事实宿主 = 容器单例,写入 = 观察漏斗直写。
        # visit 基准载体(黑板槽退役收口,ADR-0651 容器单源):段顶入口
        # 观察回执,T-163 起恒定不随动作推进(帧级逻辑态推算链已随 simulate 前瞻
        # 消费删除退役);仅供落地门 defects 留证行 plane/round 基准,决策/守卫/env 读点
        # = 容器(波 4 读者切换已承接;迁移批 3.2 起载体 = 轻量回执)。
        _cur = _entry
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of as _gs_of_entry,
        )
        _gs_of_entry = _gs_of_entry(match.session)
        # (容器入口喂入 synthesize_from_game_state 随黑板帧退役删除——迁移
        #  批 3.2:生产路径容器写入已由 read_game_state 漏斗直写承接(obs 族
        #  sig);假环境路径的容器真值写入 = 观察源端口实现方契约。)
        if not _entry.shop:
            log.info('[cw] 店开入口牌面空(买空/OCR 失读窗):离屏语义关断,'
                     '容器沿用现值牌面决策')
        # 帧代次标注(ADR-0583 §3.4):visit 首段入口观察 = full(方向视图
        # 由 decide_shop_action 入口消费刷新);续段刷新重观察 = none
        #(= 旧 _target_seeded「仅首段重估」语义,段内视图不随买入漂移)。
        game_state_of(match.session).frame_class_shop = (
            'full' if not _entry_frame_marked else 'none')
        _entry_frame_marked = True
        # 店开观察帧披露覆写(T-88 双写第二写点;ADR-0571 §2.2):备战
        # 决策入口披露帧关店态 gold 过 F2 门不可得 ⇒ overflow/budget 在
        # prep 帧恒 0(金未采语义);此处店开帧 gold 为真值,经同一现算链
        # (economy_cycle.disclose_budget)覆写三预算字段
        # (overflow/budget=帧现值;键戳同轮不清 spent,
        # 轮界清零由键戳承载)。遥测 best-effort:失败降级保留 prep 帧值
        # 不阻塞动作循环,warning 留痕(防无声退化 no-op,锚⑤缺陷无声
        # 复发)。
        try:
            from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
                disclose_budget_at_shop_frame,
            )
            disclose_budget_at_shop_frame(
                None, match.session,
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
        # 牌面真值现役归宿 = journal 快照行自带 shop 域。
        # A2:target 由策略器状态管理(方向刷新写,ADR-0583 内化)。
        _tc = getattr(strategy_state_of(match.session), 'target_comp', None)
        target_name = _tc.name if _tc is not None else ''
        _fp_v = _form_progress(_tc, match.session) if _tc is not None else -1.0
        # r295(判读必须看节点类型):state 行带 node(本节点类型,gs 推导
        # 单一源,终态契约 §A′)+next(upcoming 源退役,'?' 降级申报 §1.3)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            node_kind_of,
        )
        _gs_row = match.gs if match.gs is not None else game_state_of(match.session)
        _node = node_kind_of(_gs_row) or '?'
        _next = '?'
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of as _blog_slots,
        )
        log.info(f'[cw] state gold={_entry.gold} hp={_entry.hp} lv={_entry.level} '
                 f'plane={_entry.plane} round={_entry.round_num} node={_node} '
                 f'next={_next} board={_entry.board} '
                 f'target={target_name!r} fp={_fp_v:.2f} '
                 f'bench={bench_occupied(_blog_slots(_gs_of_entry))}')
        # 决策行披露 = 日志披露行(上方)。
        # ---- 单动作决策循环(ADR-0517 决策 1/2;循环内零读屏)----
        # 未观察态的锚定 = 「策略关店 → 备战环 heavy 观察」链,店内零
        # 重建,观察态 = 容器字段 GameState.tracked_account_observed,与
        # 下方 CwActionCloseShopParam 出口的跳过留痕/熔断。连续跳过计数复位不在段顶:
        # 见函数尾「完整收工且未跳过」的完成点复位。
        visit_actions: list = []
        while True:
            # (决策循环帧帽已删,用户裁定:不收敛 = 策略实现 bug,框架不兜底。)
            # r95 审计必修②:决策异常留证(完整栈到 log,再向上抛,行为不变)。
            try:
                action = match.strategy.decide_shop_action()   # 终态零参口(§2.1)
            except Exception:
                import traceback

                _tb = traceback.format_exc()
                log.error('[cw!][plan] decide_shop_action 异常(留证后上抛):\n%s', _tb)
                raise
            if isinstance(action, CwActionCloseShopParam):
                # 恒可用终结:本段收工(关店由编排壳承担)。CloseShopOp.execute
                # 是 no-op,此处提前退出与「execute 后按 terminal 统一 break」
                # 行为等价;保留 execute 前落点是有意声明——保持 decisions
                # 行形态契约(CwActionCloseShopParam 终结不入行,ADR-0518 §decisions 遥测行,
                # 安灯/判读输入面)。可执行终结(CwActionRefreshShopParam)
                # 的统一退出在 execute 之后(下方 _aop.terminal 分支),两条路径
                # 承载同一语义「终结 = 本段结束」,非双轨。
                # T-268:未观察态的策略关店 = 跳过访问,留痕 + 连续跳过
                # 熔断(锚定失败显式出口);观察态(含已观察空账)零感知。
                if tracked_unobserved(match.session):
                    _stop = _note_shop_skip_unobserved(op, match)
                    if _stop is not None:
                        return (_stop, None)
                break
            # (刷新硬墙闸已删,用户裁定:无限刷新环 = 策略实现 bug,
            #  框架不兜底——刷新建议照常执行,无次数上限。)
            if spend_gate is not None:
                # 单动作政策闸(缺省 None 零漂移;发射帧仲裁专用,ADR-0566):
                # 拒 = 本动作不执行 + 本访问收工(消费终止语义,见签名注)。
                _g_ok, _g_why = spend_gate(action)
                if not _g_ok:
                    # 受阻也簿记(R2 回执域):闸拒动作在账可见(exec_events
                    # 词表「受阻」族;终止单发射帧受限消费的判读输入面)。
                    # 动作未发射 → include_payload=False(安灯 plan 口径 =
                    # 发射行,与旧 visit_actions 成员资格同界)。
                    note_shop_action_receipt(
                        match, action, applied=False,
                        reason=f'blocked:spend_gate:{_g_why}',
                        extra={'blocked': 'spend_gate'},
                        include_payload=False)
                    break
            # 守卫/env 读点 = 容器(波 4 读者切换,设计件 §2.4-2:
            # guard_proposal_vs_expected 守卫输入 + ShopExecEnv.state
            # 改容器单例);_cur = visit 局部逻辑态链。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of as _gs_of_cur,
            )
            _cur_gs = _gs_of_cur(match.session)
            guard_proposal_vs_expected(action, _cur_gs)
            # 动作 op 重组批③:op 经注册表类级解析 +
            # (ctx, param, env) 组装;上报由 op 自调,落地门只留计数/回执。
            _op_cls = action_op_class_for(action)
            _env = ShopExecEnv(
                op=op, match=match, config=config, click_pts=click_pts,
                level_btn=level_btn, refresh_btn=refresh_btn,
                ledger=ledger, state=_cur_gs)
            # (执行器端口分支已随画面 op 基类退役删除:直调节点函数 =
            # 唯一路径;重试/停机查归包络与交回面,动作层零重试;节点异常
            # 原样上抛 = 执行异常通道不变。)
            _result = _op_cls(op.ctx, action, env=_env).run()
            _ok = bool(_result.is_success)
            # 执行落地回执(R2 回执域,逐动作 op 一条 logic_action 行):
            # applied = 动作 op 自身机械事实(round 成功态;未落地 = False
            # + 摘要),发出即簿记非验证——本行零新增读屏零成败判定。
            # (迁移批 3.2 安灯换轨:发射行附 serialize_action 同 schema
            #  动作载荷 = 安灯动作序列源;刷新行附 refresh 留证半边的
            #  牌面变化位——free_refresh_proc 豁免判定输入。批4 比对收口:
            #  三值对比单一源 = cw_shop_refresh_obs.refresh_board_changed_
            #  of,刷前/刷后名集由刷新 op 落账,此处按单一源现算,
            #  行值与迁出前 execute 预算式逐位同值。)
            _rcpt_extra = (
                {'refresh_board_changed':
                 refresh_board_changed_of(ledger.refresh_pre_names,
                                          ledger.refresh_post_names)}
                if isinstance(action, CwActionRefreshShopParam) else None)
            note_shop_action_receipt(
                match, action, applied=bool(_ok),
                reason='' if _ok else f'执行未落地({_op_cls.__name__})',
                extra=_rcpt_extra)
            apply_action_outcome(action, _ok, _cur, match,
                                 ledger, visit_actions)
            # T-82 续段 token 写入(生产商店循环执行位):动作确认已执行
            # 后置位 (动作型名, 当前段序号);未执行路径(闸拒/硬墙/
            # CwActionCloseShopParam 提前退出)不写。策略器入口读后即清,下一帧据其
            # 判定 M2 停摆续段缓存命中。状态对象缺席 = 跳过(B4 口径)。
            if _ok:
                _st_tok = strategy_state_of(match.session)
                if _st_tok is not None:
                    _st_tok.cw4_frame_action_record = (
                        type(action).__name__, _st_tok.cw4_segment_serial)
            # 义务实花回执位记账(T-88;闸前不记——spend_gate 拒绝帧
            # 未执行,本位只在 execute 成功回执后累计,F4 栈守卫见函数注)。
            accrue_release_spent(match, action, _ok)
            # (帧链推进随 simulate 前瞻消费删除退役,T-163:_cur 恒为段顶
            # 入口观察帧,visit 内 plane/round 不变,journal 行基准语义
            # 不变;期望态真值在容器,由逻辑态直写口推进。)
            if _op_cls.terminal:
                # 终结 op 统一退出(ADR-0517 决策 4/7;终结 op 语义 review
                # V1/V2 修复,P35 实证):终结动作 execute 后黑板不写逻辑态
                # (apply_action_outcome 对终结跳过,期望态按规格作废)——
                # 循环若不在此退出,下一帧 decide 读到的仍是刷前旧牌面,
                # 策略器(期望态的确定性纯函数)对旧牌面重发 CwActionRefreshShopParam
                # 连发至硬墙,或把旧牌面的 CwActionBuyCardParam 提案点在新牌面槽位
                # (错买随机卡)。break 后段循环下一次迭代的入口观察重建
                # 期望态 = 「交回外循环重进」的物理载体;CwActionRefreshShopParam 与
                # CwActionCloseShopParam 同路径(原 CompTransaction 终结邻接 fallback
                # 已随 unified-action-factory 批2b R3 删除)。
                break
        log.info('[cw] shop=%s plan=%s',
                 [(s.kind,
                   (s.card.name, s.card.faction, s.card.cost)
                   if s.card else None) for s in _entry.shop],
                 [_fmt_action(a) for a in visit_actions])
        # 装备库存容器写端 = 备战装配点 observe + 载体中继兜底
        # (cw_observation)。
        # 连击续刷判定输入:本段是否「仅刷新且真点击」。
        _prev_refresh_only = bool(
            ledger.did_refresh and refresh_wave_is_refresh_only(visit_actions))
        if not ledger.did_refresh:
            break   # 本段无刷新(或硬墙)→ 收工

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
            # refs 指 journal (run_id,v) 锚(plane/round/bought 数已在
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
                    plane=_entry.plane, round_num=_entry.round_num,
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
                    plane=_entry.plane, round_num=_entry.round_num,
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
                        plane=_entry.plane, round_num=_entry.round_num,
                        verdict=('留证-身份回读未含买牌名(容未识别;'
                                 '占位已另判,不构成失败)'),
                        reader_source='bench_buy_sift_readback',
                        gap_large=False, refs=_bench_refs,
                        note='观测自检框架设计 §2.2:身份留证不算失败')

    # 动作账/期望态基座 = ledger 本体外发(消费方 = cw_screen_prep.
    # visit_open_shop/finalize_buy_phase 与 cw_loop 仲裁段)。
    # 连续跳过计数复位(T-268 编排者核进):复位条件 = 「完成了一次未跳过
    # 的正常访问」——本 visit 观察态已锚定且完整收工才重开熔断计数窗,
    # K=2 数的是连续因未观察跳过,非任意间隔;跳过 visit(未观察)与中途
    # 停机支都不复位。载体缺席静默跳过 = 无计数面。
    if not tracked_unobserved(match.session):
        _ct_fin = getattr(strategy_state_of(match.session),
                          'cw4_counters', None)
        if isinstance(_ct_fin, dict):
            _ct_fin[CW4_KEY_SHOP_SKIP_UNOBSERVED_STREAK] = 0
    return None, ledger


class CwScreenBuyCards(SrOperation):
    """备战-开商店原子 op(两 node 形态;ADR-0517 迁移批,前身份 = 商店
    动作波循环,W970 批 A 契约 §4.2)。

    生产路径由编排壳直调 :func:`run_buy_waves`(宿主 op 复用,保证读屏
    次序/替身桩行为等价);本类为独立可跑壳(``run_operation`` 单跑定位
    失败步)。hp 决策消费统一经容器政策读口 decision_hp(迁移批 3.2 起
    hp 三件组传参链随黑板帧退役删除)。

    两 node 形态:观察 node = ①入口段(park + 入口观察 read_game_state
    直连 + 店开防抖 3×0.8s + 未识别卡停机闸,读+防抖+闸三段单一实现 =
    :func:`_shop_entry_read`)→ CwScreenBuyCardsObs(入口回执同面镜像,
    挂实例属性供决策侧/测试消费;无容器摄入面——容器写端在观察漏斗,
    report 保持占位);决策动作 node = 波循环(:func:`run_buy_waves` 内核:
    段循环/账本/终结判定/CloseShop 收尾)整体,首段复用观察 node 回执
    不重读。**波循环例外申报**(同备战 VISIT_ACTION_CAP 口径):循环宿主
    = 波循环内聚状态机(段循环 = 「刷新终结交回重进」的物理载体,决策
    循环零读屏),不是 node 轮次 round_wait 循环——round_wait 化属行为
    变更,本批不拆不改,交编排者/用户知悉。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-买牌')
        # 观察 node 产物:入口回执镜像(obs,决策侧/测试消费面)与首段
        # 复用载荷((回执, 帧),决策动作 node 首段不重读)。
        self._obs: CwScreenBuyCardsObs | None = None
        self._pre_entry: tuple[GameStateReadReceipt, Any] | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """①入口段:park + 入口观察 + 店开防抖 + 未识别卡停机闸。

        无对局(独立单跑)= 入口观察的防抖/停机闸需容器宿主(match
        .session)→ 空 obs 交决策动作 node,:func:`run_buy_waves` 兜底建核
        后段顶照旧现读(与旧单节点形态同序,行为零差)。"""
        match = getattr(self.ctx, 'cw_match', None)
        if match is None:
            self._obs = CwScreenBuyCardsObs()
            return self.round_success('无对局(独立单跑,决策 node 兜底建核)')
        # 等 board 面板 settle(波循环首段段头时序随观察 node 前移,值不变)
        time.sleep(0.3)
        # 光标 parking(审计 P0,2026-08-16):park 后再读。
        self.park_cursor(after_wait=0.1)
        _entry, _entry_shot, _stop = _shop_entry_read(self, match)
        if _stop is not None:
            return _stop
        self._obs = CwScreenBuyCardsObs(
            gold=_entry.gold, gold_readable=_entry.gold_readable,
            hp=_entry.hp, hp_readable=_entry.hp_readable,
            hp_trusted=_entry.hp_trusted,
            level=_entry.level, level_readable=_entry.level_readable,
            plane=_entry.plane, round_num=_entry.round_num,
            node_type=_entry.node_type, board=dict(_entry.board or {}),
            shop=list(_entry.shop or []), screen=_entry_shot)
        self._pre_entry = (_entry, _entry_shot)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """波循环整体(:func:`run_buy_waves` 内核;例外申报见类注)。"""
        rr, ledger = run_buy_waves(self, self.ctx.cw_match,
                                   pre_entry=self._pre_entry)
        self._pre_entry = None
        if rr is not None:
            return rr
        return self.round_success(
            f'plan 买{ledger.total_buy}张 经验{ledger.total_xp_buy}击 '
            f'刷{ledger.total_refresh}次 卖{ledger.total_sell}张')
