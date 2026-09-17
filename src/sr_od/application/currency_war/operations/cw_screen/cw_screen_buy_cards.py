
import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import (
    action_sink,
    observation_source,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    bench_occupied,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_of,
    shop_payload_content_cards,
    tracked_unobserved,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    area_center,
    shop_card_click_points,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.kernel.cw_telemetry_exit import journal_refs
from sr_od.application.currency_war.kernel.cw_vocab import (
    BuyCard,
    DeployMove,
    LevelUp,
    RefreshShop,
    SellBench,
)
from sr_od.application.currency_war.obs.cw_observation import (
    PHASE_PREP_SHOP_OPEN,
    GameStateReadReceipt,
    ensure_portrait_templates,
    new_bench_slots,
    read_game_state,
    read_gold,
    read_gold_opt,  # noqa: F401  模块属性路由:cw_shop_action_ops 经本模块名取读函数(替身缝)
    read_shop_cards,
)
from sr_od.application.currency_war.obs.cw_shop_refresh_obs import (
    refresh_board_changed_of,
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
    from sr_od.application.currency_war.kernel.cw_vocab import (
        Action,
        CloseShop,
        LevelUpShop,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
        ActionOp,
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


def _entry_receipt_from_container(gs) -> GameStateReadReceipt:
    """端口路径入口回执装配(迁移批 3.2/切片4:假环境容器真值 → 轻量回执)。

    观察源端口实现方已把真值直写容器(与读屏路径漏斗直写同语义契约),
    本装配把决策/日志/安灯消费的逐帧读数面从容器读口映射为
    :class:`GameStateReadReceipt`——生产路径同面由 read_game_state 原生
    产出。完美观测形态:gold/hp 可读位 = source=='observation'(假环境
    恒真读);shop = 容器 payload 牌(容器 ShopCard 形态,消费面
    name/faction/cost 兼容)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        gold_of,
        level_of,
        node_kind_of,
        plane_of,
        round_num_of,
    )
    payload = gs.shop.value
    hp_val = gs.hp.value
    return GameStateReadReceipt(
        gold=gold_of(gs),
        gold_readable=bool(gs.gold.source == 'observation'),
        hp=int(hp_val) if hp_val is not None else None,
        hp_readable=bool(gs.hp.source == 'observation'),
        level=level_of(gs),
        plane=plane_of(gs),
        round_num=round_num_of(gs),
        node_type=node_kind_of(gs),
        board=dict(gs.board.value or {}),
        shop=shop_payload_content_cards(payload))


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
# D牌(刷新)硬上限:plan 的 _refresh_cap 是单次 plan 软上限;两阶段循环里再加硬墙防死循环
MAX_REFRESH: int = 4
# 单段决策循环防御帧帽(ADR-0518):决策侧席位门等提案门失效时的执行侧
# 兜底,与 cw_screen_prep.VISIT_ACTION_CAP 同款防线——决策循环不收敛 =
# 逻辑态或策略器 bug,超帽响亮暴露(RuntimeError)+ 遥测分键
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


def apply_action_outcome(_aop: 'ActionOp',
                         action: 'BuyCard | RefreshShop | SellBench | LevelUpShop | CloseShop',
                         _ok: bool, _cur: 'GameStateReadReceipt',
                         match: 'CurrencyWarMatch', ledger: 'ShopVisitLedger',
                         visit_actions: list) -> None:
    """执行结果落地门(调用环单一源;落地审补办清单 C1 调用环级锁的承载体。

    C1 语义 = 旧 return True 使期望账逻辑态与 tracked 实账分叉;应修-2 语义
    = 已买集无条件追加使检出帧名污染 prefer_names/churn(落地审补办审,
    2026-09-05;原清单为会话产物不入库,语义以此为准)。

    未落地(_ok=False,如执行侧检出购买未生效)⇒ **两侧都不动**:不写逻辑态、
    不入「已买」集(防检出帧名污染 prefer_names/churn/P60,应修-2);
    落地且非终结 ⇒ 逻辑态直写(容器规则通道:直写口简单腿 + 合成升星腿)。
    原「+ guard_expected_vs_tracked 双账对拍(满栏买入豁免)」已随 T-268
    退役(对账归属原则:双态比对唯一合法时点 = 观察边界 kernel
    cw_reconcile)——逻辑态建模 bug 的检出归 reconcile 纠漂显影(观察赢)。

    ``_cur`` = 段顶入口观察回执(defects 留证行 plane/round 基准 + 逻辑
    直写帧标识;期望态真值在容器,函数无返回值,调用方不再推进任何帧链载体;迁移批 3.2 起载体 =
    :class:`GameStateReadReceipt`,visit 内 plane/round 恒定不变)。
    """
    visit_actions.append(action)
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
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                CounterKey,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            game_state_of(match.session).effects.bump_key(CounterKey.BUY)
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
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
            record_refresh_execution,
        )
        _gs = game_state_of(match.session)
        _logic_bal = _gs.free_refresh_balance.value
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
            _gs, free=_free,
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
            _gs.effects.bump_key(CounterKey.REFRESH)
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-buy] 效果账本 REFRESH 计数失败(不阻塞): {e}')
    if _ok and not _aop.terminal:
        # 商店动作逻辑态直写·容器通道(纯规则路线,T-163:期望态推进 =
        # 逻辑态直写口 + 合成升星腿,与序列驱动器
        # 同形单一源;设计件《商店黑板容器化方案》§2.1-2/§4-M1)。
        # 写序申报:直写口先写(含 bench 简单落位),升星整表直写后写覆盖
        # (后写赢)——两写合计的期望态由投影直锁钉住(锁 M1,
        # test_cw_shop_projection_logic)。
        # 执行回执(设计件 §2.1-2):k = 执行侧实购张数(merge_buy_k 计数,
        # ledger.buy_purchases 执行落地事实);LevelUpShop 单动作形态恒
        # 1 击;非买/升动作无执行期决定量(空回执)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig as _ProjSig,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ShopActionExecuted as _ShopExecuted,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            apply_shop_action_logic as _apply_shop_logic,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            apply_shop_merge_leg as _apply_merge_leg,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of as _sg_slots,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of as _gs_of_proj,
        )
        _gs_proj = _gs_of_proj(match.session)
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
        # 买前快照三件组(升星腿 scratch 基点;必须在直写口写之前取——
        # 基点误取买后容器会重复落位,shop 视图缺失会漏满栏合成,失准
        # 形态申报见 apply_shop_merge_leg docstring)。
        if isinstance(action, BuyCard):
            from sr_od.application.currency_war.kernel.cw_game_state import (
                deployed_slots_of as _sg_dep,
            )
            _pre_bench = list(_sg_slots(_gs_proj))
            _pre_dep = list(_sg_dep(_gs_proj))
            _payload_now = _gs_proj.shop.value
            _pre_shop = (shop_payload_content_cards(_payload_now)
                         if _payload_now is not None else [])
        _proj_sig = _ProjSig(family='logic_action', actor='CwScreenBuyCards',
                             mode='compute',
                             group_id=(f'act:CwScreenBuyCards@'
                                       f'{_gs_proj.write_seq + 1}'))
        _apply_shop_logic(_gs_proj, action, executed=_executed,
                          produced_by=type(action).__name__,
                          sig=_proj_sig)
        if isinstance(action, BuyCard):
            # 合成升星整表直写(升星腿,买前快照基点):发生 3 合 1 升星 →
            # 合成后 bench 视图经 write_logic 直写(source=logic,策略器
            # 立即可读);下一备战帧实读照常覆盖(观察赢),失配 = 逻辑态
            # 模型 bug,缺陷台账留证后修推算代码。last-wins:同段级联
            # 合并只留末张直写。纯记录面,决策零影响(bench 为消费视图
            # 透传域,§8.7 批次二 as-built)。
            _apply_merge_leg(_gs_proj, action, sig=_proj_sig,
                             pre_bench=_pre_bench, pre_deployed=_pre_dep,
                             pre_shop=_pre_shop)
        ledger.refresh_first_action = False


def accrue_release_spent(match: 'CurrencyWarMatch',
                         action: 'BuyCard | RefreshShop | SellBench | LevelUpShop | CloseShop',
                         ok: bool) -> None:
    """v3_release_spent 执行回执位记账(T-88 写点;裁决 = ADR-0571)。

    首版口径 = **只计刷新实花**(「宁窄勿虚」的遥测诚实性选择:买牌/
    升级是否计入「义务实花」全渠道口径在 mandate_v1 语义下未经证明,
    混入会虚高——扩口径挂 ADR-0571 待裁)。刷新单通道前提:R1 = 今日
    唯一刷新发射点(kernel/cw_state.RefreshShop.reason 值域契约)。
    记账位语义 = 动作执行成功回执(本函数在 apply_action_outcome 之后
    调用),轮键 = 容器读口现读(迁移批 3.2:原入口帧 plane/round 形参
    随黑板帧退役删除;visit 内轮键恒定,容器同值)。

    F4 栈守卫:仅当披露面轮键戳 == 当前 (plane, round)(即 mandate_v1
    本轮 prep 装配已跑)才累计——非 mandate_v1 栈(异型策略状态对象无
    键戳)或键戳过期帧不累计,防「spent>0 而预算三字段=None」的混合行
    形态(recorder「default 栈帧无写点 → None 语义」声明)。字段经防御
    getattr 访问(披露面形态;ADR-0563 B4 收缩申报)。
    """
    if not ok or not isinstance(action, RefreshShop):
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
    """未观察态商店访问跳过的留痕与熔断(T-268 ④;CloseShop 出口消费)。

    触发形态:策略未观察门(strategies/impl/flow.py decide_shop_action)
    返回恒可用终结 CloseShop → 本 visit 零动作收工。每次跳过 = 缺陷台账
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
                  ) -> tuple[OperationRoundResult | None, 'ShopVisitLedger']:
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

    - 入口观察(段顶,唯一读屏点):真实读屏 → 漏斗容器直写(obs 族 sig,
      决策读单源 = 容器单例;迁移批 3.2 起 read_game_state 不再构造帧,
      返回 :class:`GameStateReadReceipt` 供逐帧读数消费;黑板槽已退役,
      visit 基准载体 = 局部 ``_cur`` 回执);
    - 决策循环(零读屏,决策 1/8):``decide_shop_action`` 每次恰返回一个
      动作 → proposal 守卫(``guard_proposal_vs_expected``,防策略器算术
      bug)→ 执行(动作 op ``execute``,观测通道候选 a
      遥测在内)→ 容器逻辑态直写推进期望态(``apply_shop_action_logic``
      简单腿 + 合成升星腿;T-163 起零 simulate 前瞻消费)。tracked 未观察
      时策略门返回 CloseShop = 跳过访问,留痕与熔断见段顶/出口注(T-268)。
    - 终结 op(RefreshShop/CloseShop):执行即本段结束。刷新终结 = 交回
      外循环重进——物理载体 = 本函数段循环的下一次迭代(入口观察重建,
      读屏次数与波批持平,ADR-0517 §读屏成本·节奏对拍);关店终结 = 本
      访问收工(关店点击由编排壳 CwOpCloseShop 承担)。MAX_REFRESH 硬墙
      重定位 = 执行侧 visit 级计数(``ledger.total_refresh``,§3.1 候选
      (a) 同款防线:防「终结→重进→再刷新」无进展环)。

    (访问内 hp 决策消费统一经容器政策读口 decision_hp,门前真值由备战帧
     观察/结算既有写端承接,段间无战斗值同源,覆盖回写是绕行。)

    match=None(独立 run_operation 调本 op)→ 临时 match,不挂 ctx
    (局外不复用)。config 本函数内构造(W970 §4.3.4)。

    返回 (失败 round 结果, 访问账本)。正常收工 → (None, ledger);
    未识别卡停机钩子触发 → (round_fail 留证结果, None)。
    (迁移批 3.2:产出载体 = ShopVisitLedger 本体——BuyCardsOutcome 已退役,
    动作账/期望态基座随账本外发。)
    """
    # 工厂住聚合注册文件(动作 op 一 op 一文件后 cw_shop_action_ops 不持 op 类)
    from sr_od.application.currency_war.kernel.cw_vocab import CloseShop
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopExecEnv,
        ShopVisitLedger,
        guard_proposal_vs_expected,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_shop_actions import (
        shop_action_op_for,
    )

    config = CurrencyWarConfig(op.ctx.current_instance_idx)
    if match is None:
        # 防御:无对局态(独立 run_operation 调本 op)→ 临时 match。
        # (迁移批 3.2 起必须挂 ctx:read_game_state 容器直写按 ctx.cw_match
        # 定位 session 容器,不挂 = 漏斗写块整体跳过 → decide 前置门
        # shop=None。「局外不复用」语义由「每次 run_operation 新建」保持,
        # 挂 ctx 只是给漏斗写块一个可寻址的 session 容器。该路径经
        # create_session 冷建(ADR-0583:live 初值 v3_phase='FORM' 随唯一
        # 冷建口在此落位;phase 列仅诊断用)。
        from sr_od.application.currency_war.strategies.impl.cw_strategy import (
            CurrencyWarMatch,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            MandateV1Strategy,
        )
        _def = MandateV1Strategy()
        _session = _def.create_session(config)
        # 终态契约 Match 终形含 gs/performance(landing §3.1);防御路径
        # 同漏斗口径建容器(改道引导漏斗归终态切换批,本批先保构造合法)。
        match = CurrencyWarMatch(
            _def, _session, game_state_of(_session),
            performance=getattr(_session, 'performance', None))
        op.ctx.cw_match = match

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
        # 观察源端口改道(T-120 方案 §2.3/§3.3,批 1;迁移批 3.2 切片4:
        # 端口契约 = 容器形态,实现方直写真值,消费面经容器读口装配回执);
        # 缺省 None = 生产真实读屏(read_game_state 漏斗直写 + 原生回执)。
        _src = observation_source()
        _entry_shot = op.screenshot()
        if _src is not None:
            _src.observe_prep(op.ctx, PHASE_PREP_SHOP_OPEN)
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of as _gs_of_port,
            )
            _entry = _entry_receipt_from_container(
                _gs_of_port(match.session))
        else:
            _entry = read_game_state(op.ctx, _entry_shot,
                                     phase=PHASE_PREP_SHOP_OPEN,
                                     screen_name=SHOP_SCREEN_NAME)   # ADR-0462 开店动作期
            # 店开入口防抖:开店转场/淡入帧可令收起锚 miss → shop payload
            # 未入容器(fresh 容器无上一牌面可沿用,decide 前置门即炸——
            # 实机买光店五败定谳;已渲染帧离线全链复现全绿,读数函数无恙)。
            # 本 op 前置已知店在屏,有界重读(3 × 0.8s)直至 shop 入容器;
            # 仍缺 = 真离屏/持续失读,交由决策前置门大声失败(禁静默空态)。
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
        # gold-robust:gold 数字 stylized,paddle OCR det 间歇漏 → 读 0 时重读几帧取首个 >0。
        # 观察冲突审计 #6:救援结果留证(救回/连读 0 统计,为 gold 双源排期供数据)。
        _gold_rescued = None
        if _entry.gold == 0:
            for _ in range(4):
                time.sleep(0.4)
                gv = read_gold(op.ctx, op.screenshot())
                if gv > 0:
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
            # 经既有观察喂入口写 gs.gold,禁静默丢失)。首读假 0 已由观察
            # 漏斗 observe 落容器,救援值同渠道覆盖(观察赢,来源同级)。
            if _gold_rescued is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig as _RescueSig,
                )
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of as _gs_of_rescue,
                )
                _gs_rescue = _gs_of_rescue(match.session)
                _gs_rescue.observe(
                    _gs_rescue.gold, int(_gold_rescued),
                    evidence='gold_rescue:shop_first_read_fake_zero',
                    sig=_RescueSig(family='obs', actor='CwScreenBuyCards',
                                   mode='read',
                                   group_id=(f'obs:CwScreenBuyCards@'
                                             f'{_gs_rescue.write_seq + 1}')))
        # (开店首读金快照 gold_open 随 outcome 退役移出本函数——迁移批
        #  3.2:基线 = 编排壳 visit 入口容器 gold 现读暂存,详见 visit_open_shop。)
        # 播种单一源 = tracked_bench_chars(带 star+merge,mutate/对账全程同步)。
        # 空 = bench 真空(全部署/合成清空的事实正确态),不回退任何残账——
        # 旧 tracked_bench 回退分支已退役:单动作架构下「首轮」场景由入口
        # heavy 读屏重建(ADR-0517 决策 8,入口观察即对账);残账仅 BuyCard
        # 追加、无人清理,回退会复活陈旧名(实证 = 2026-09-05 OpenShop
        # 双账分叉事故,诊断档
        # .debug/temp/currency_war/20260905_openshop_fork_diag/report.md)。
        # (tracked 播种已随 W6 波 4 黑板容器化取消——设计件 §2.1-5:容器
        #  bench = prep 帧观察值(观察漏斗写端)+ visit 内逻辑态直写;黑板帧
        #  播种的唯一消费者 = 旧帧决策链,读者切换后无行为面。)
        if game_state_of(match.session).tracked_books.bench:
            log.info(f'[cw] tracked_bench_chars='
                     f'{[(c.char_id, c.star) for c in game_state_of(match.session).tracked_books.bench if c is not None]}'
                     f'(播种取消,仅日志显影)')
        # T-308 S3:播种期布局代次快照(单动作循环每动作消费前检差用;
        # 空播种段同样取值——检差面不依赖是否播种)。宿主 = 容器簿记组
        # ExecBooks(载体解散迭代迁入;写点 = kernel/cw_reconcile 纠漂期)。
        _seed_epoch = game_state_of(match.session).exec_books.bench_layout_epoch
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
        match.session.shop_frame_class = (
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
        # r295(判读必须看节点类型):state 行带 node(本节点类型)+next。
        _node = getattr(match.session, 'node_type_current', None) or '?'
        _upc = getattr(match.session, 'upcoming_types', None) or []
        _next = _upc[0] if _upc else '?'
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
        # 下方 CloseShop 出口的跳过留痕/熔断。连续跳过计数复位不在段顶:
        # 见函数尾「完整收工且未跳过」的完成点复位。
        visit_actions: list = []
        _seg_frames = 0
        while True:
            _seg_frames += 1
            # S3 布局代次检差(fail-stop 形态,T-271):命中 = visit 内
            # 布局已重排(reconcile 纠漂递增 epoch),已发射动作的
            # bench_idx 代际失效 → 本段收工交回外循环重观察(与未观察
            # 机制同构:关店→备战 heavy 观察→reconcile 锚定后再进店)。
            # 禁店内按执行侧簿记重播种容器 bench(原 reseed 三步封装
            # 删除):那是 op 层第二条容器 bench 写口,违写口归属硬规则
            #(对账/仲裁唯一发生在观察边界,screen_op §4 + action-logic-
            # state §1.3)。
            from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
                bench_layout_stale,
            )
            if bench_layout_stale(match.session, _seed_epoch):
                ledger.plan_truncated = True
                log.warning('[cw!][plan] 布局代次检差命中 → fail-stop '
                            '本段收工,交回外循环重观察')
                break
            # 段界序号 _seg_frames 只服务帧帽防线。
            if _seg_frames > SHOP_SEGMENT_ACTION_CAP:
                # 防御帧帽(对抗发现:决策循环不收敛的响亮暴露——禁静默续跑/
                # 禁吞异常续跑。收敛根因修复在决策侧席位门,本帽 = 执行
                # 侧最后防线,与 prep 线 VISIT_ACTION_CAP 同构但更严:
                # 商店段动作单价高(买/卖不可逆),超帽不交回外循环重试)。
                # 帧帽诊断读 = 容器(W6 波 4 读者切换,设计件 §2.4-2)
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    bench_slots_of as _bslots_of,
                )
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of as _bcap_of,
                )
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    gold_of as _gold_of,
                )
                _st_cap = _bcap_of(match.session)
                _msg = (f'[cw!][plan] 决策循环帧数超帽'
                        f'({SHOP_SEGMENT_ACTION_CAP}),疑逻辑态/策略器不收敛'
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
                # 安灯/判读输入面)。可执行终结(RefreshShop)
                # 的统一退出在 execute 之后(下方 _aop.terminal 分支),两条路径
                # 承载同一语义「终结 = 本段结束」,非双轨。
                # T-268:未观察态的策略关店 = 跳过访问,留痕 + 连续跳过
                # 熔断(锚定失败显式出口);观察态(含已观察空账)零感知。
                if tracked_unobserved(match.session):
                    _stop = _note_shop_skip_unobserved(op, match)
                    if _stop is not None:
                        return (_stop, None)
                break
            if isinstance(action, RefreshShop) and ledger.total_refresh >= MAX_REFRESH:
                # 硬墙重定位(ADR-0517 §3.1 候选 (a)):visit 级刷新计数超墙
                # ⇒ 终结集降级为仅关店。硬墙跳过=计划了但未尝试,可见化
                # 不停(`w577_refresh_fee_and_andon/`,局22 误停根因)。
                # plan_truncated 现役载体 = receipts extra(本行;安灯换轨
                # 后数据源,迁移批 3.2)。
                ledger.plan_truncated = True
                # 受阻也簿记(R2 回执域):计划未尝试在账可见(exec_events
                # 词表「放弃」族;plan_truncated/refresh_skipped 结构化入回执)。
                # 动作未发射 → include_payload=False(plan 口径与旧 visit_actions 同界)。
                note_shop_action_receipt(
                    match, action, applied=False,
                    reason='skipped:max_cap(刷新硬墙,计划未尝试)',
                    extra={'plan_truncated': True,
                           'refresh_skipped': 'max_cap'},
                    include_payload=False)
                break
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
            _aop = shop_action_op_for(action)
            _env = ShopExecEnv(
                op=op, match=match, config=config, click_pts=click_pts,
                level_btn=level_btn, refresh_btn=refresh_btn,
                ledger=ledger, state=_cur_gs)
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
            # (迁移批 3.2 安灯换轨:发射行附 serialize_action 同 schema
            #  动作载荷 = 安灯动作序列源;刷新行附 refresh 留证半边的
            #  牌面变化位——free_refresh_proc 豁免判定输入。批4 比对收口:
            #  三值对比单一源 = cw_shop_refresh_obs.refresh_board_changed_
            #  of,刷前/刷后名集由 RefreshShopOp 落账,此处按单一源现算,
            #  行值与迁出前 execute 预算式逐位同值。)
            _rcpt_extra = (
                {'refresh_board_changed':
                 refresh_board_changed_of(ledger.refresh_pre_names,
                                          ledger.refresh_post_names)}
                if isinstance(action, RefreshShop) else None)
            note_shop_action_receipt(
                match, action, applied=bool(_ok),
                reason='' if _ok else f'执行未落地({type(_aop).__name__})',
                extra=_rcpt_extra)
            apply_action_outcome(_aop, action, _ok, _cur, match,
                                 ledger, visit_actions)
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
            accrue_release_spent(match, action, _ok)
            # (帧链推进随 simulate 前瞻消费删除退役,T-163:_cur 恒为段顶
            # 入口观察帧,visit 内 plane/round 不变,journal 行基准语义
            # 不变;期望态真值在容器,由逻辑态直写口推进。)
            if _aop.terminal:
                # 终结 op 统一退出(ADR-0517 决策 4/7;终结 op 语义 review
                # V1/V2 修复,P35 实证):终结动作 execute 后黑板不写逻辑态
                # (apply_action_outcome 对终结跳过,期望态按规格作废)——
                # 循环若不在此退出,下一帧 decide 读到的仍是刷前旧牌面,
                # 策略器(期望态的确定性纯函数)对旧牌面重发 RefreshShop
                # 连发至硬墙,或把旧牌面的 BuyCard 提案点在新牌面槽位
                # (错买随机卡)。break 后段循环下一次迭代的入口观察重建
                # 期望态 = 「交回外循环重进」的物理载体;RefreshShop 与
                # CloseShop 同路径(原 CompTransaction 终结邻接 fallback
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

    # [停机钩子·常驻兜底(od-dev-stop-hooks §2.1 分类;原「临时,采完删(用户
    # 2026-08-15 指示)」标注系误分类)]未购买(含刷新后仍未购买)且商店有
    # 未识别卡(SIFT miss)→ 停机留画面给 AI 建档。触发条件兜「商店出现
    # 未识别卡」整类(新版本新卡/非角色内容/立绘缺/瞬时帧)持续可能复发 =
    # 安全网;移除条件 = 未识别卡类建模收敛(见下方 flag 文字),平时触发
    # 只删 flag 不删钩子。
    # 📋 调研档案(2026-08-17 阮·梅/白厄单帧 miss 归因闭环,下次触发先读这段):
    # - 历史触发全部是刷新动画/settle 瞬时帧;本 hook 防抖重读两次均自愈。
    # - 重读 = 立即再读(两帧指纹等稳门已废弃,T-219;动画/settle 类瞬态
    #   由刷新分支的固定等待 REFRESH_CLICK_SETTLE_WAIT_S 前置收敛);
    #   预算 2 次,耗尽才真停(模态弹窗压暗不因重读消失)。
    # - f570a76e 审查#1 修:去 total_buy 门——残缺牌面上的买牌决策同样要留证。
    # 硬必改(商店域审计 D 项):判据 any(not c.name) → kind=='unknown'
    # (三态模型:empty=识别确证空位非未识别;content 恒有 name)。
    if _entry is not None and any(
            getattr(s, 'kind', '') == 'unknown' for s in _entry.shop):
        _unk = [i + 1 for i, s in enumerate(_entry.shop)
                if getattr(s, 'kind', '') == 'unknown']
        for _ in range(2):
            _reshop = read_shop_cards(op.ctx, op.screenshot())
            _unk = [i + 1 for i, s in enumerate(_reshop or [])
                    if s.kind == 'unknown']
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
                f'operations/cw_screen/cw_screen_buy_cards.py run_buy_waves\n'
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


class CwScreenBuyCards(CwScreenOpBase):
    """备战-开商店原子 op:执行商店单动作循环(ADR-0517 迁移批;
    前身份 = 商店动作波循环,W970 批 A 契约 §4.2)。

    生产路径由编排壳直调 :func:`run_buy_waves`(宿主 op 复用,保证读屏
    次序/替身桩行为等价);本类为独立可跑壳(``run_operation`` 单跑定位
    失败步)。hp 决策消费统一经容器政策读口 decision_hp(迁移批 3.2 起
    hp 三件组传参链随黑板帧退役删除)。

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

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-买牌')

    def _buy_round(self) -> OperationRoundResult:
        """旧路径委托体(buy 节点旧路径与变体决策循环共享的单一实现)。"""
        rr, ledger = run_buy_waves(self, self.ctx.cw_match)
        if rr is not None:
            return rr
        return self.round_success(
            f'plan 买{ledger.total_buy}张 经验{ledger.total_xp_buy}击 '
            f'刷{ledger.total_refresh}次 卖{ledger.total_sell}张')

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
        """段2 reconcile:空申报(旧体委托变体——观察/对账住委托体段循环内,
        无独立对账面;对账唯一发生点 = 观察边界 kernel cw_reconcile)。"""
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
