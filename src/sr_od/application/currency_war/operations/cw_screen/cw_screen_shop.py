"""货币战争商店画面 op(两 node 规范形态;op-layer §1.1 单动作 round_wait
循环)。

- 观察 node(每访问恰一次,唯一读屏点):兜底建核(独立单跑)→ 入口
  观察(读 + 未识别卡停机闸两段单一实现 = :func:`_shop_entry_read`)
  → obs 镜像 → 段首簿记(segment serial / 帧代次 full / 预算披露 /
  状态行日志 / shop_entry 决策帧)。
- 决策动作 node(round_wait 单动作循环,循环内零读屏零拦截零闸):
  决策(容器零参读)→ 守卫 → 注册表派发 execute(全动作统一路径,
  含 CloseShop 真点击)→ 簿记 → 终结读注册表:非终结 round_wait,
  终结(RefreshShop/CloseShop)round_success 交回外循环。

生产调用点(0n 转交与显式开店同口 ``cw_screen_prep.visit_open_shop``、
``run_operation`` 单跑)构造本类并节点函数直驱(不经框架 execute 循环,
决策循环轮间零截图)。出参交接契约(详设 §2.2):失败判定 = 轮结果
``is_success``;执行账 = 实例 :attr:`CwScreenShop.ledger`(run 完成
后有效)。节点行观察已归备战观察域(详设 §2.8,宿主 =
``cw_screen_prep._write_prep_node_chain``),商店域零探针。
"""

import contextlib
import time
from typing import TYPE_CHECKING, Any

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import (
    OperationRoundResult,
)
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.kernel.cw_game_state import (
    bench_entries_of,
    game_state_of,
    tracked_unobserved,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    area_center,
    shop_card_click_points,
)
from sr_od.application.currency_war.kernel.cw_screen_report.shop import (
    CwScreenShopObs,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.obs.cw_observation import (
    PHASE_PREP_SHOP_OPEN,
    GameStateReadReceipt,
    read_game_state,
)
from sr_od.application.currency_war.operations.decision_frame_hooks import (
    save_decision_frame,
)
from sr_od.application.currency_war.telemetry import defects
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    # 注解专用。运行时消费 = 函数内 lazy import(注册表/账本/守卫住
    # cw_op 桶,保持画面 op 桶 → 动作 op 桶单向惰性依赖)。
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_vocab import (
        Action,
        CwActionBuyCardParam,
        CwActionCloseShopParam,
        CwActionLevelUpShopParam,
        CwActionRefreshShopParam,
        CwActionSellBenchParam,
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


def _shop_entry_read(op: SrOperation, match: 'CurrencyWarMatch',
                     ) -> tuple[GameStateReadReceipt | None, Any,
                                OperationRoundResult | None]:
    """商店入口观察读半部(唯一读屏点的读+停机闸两段;
    生产读屏路径与观察 node 共用单一实现,零第二转录)。

    - read_game_state 直连(漏斗容器直写 + 原生回执);
    - 单次读零防抖(用户裁定:店开防抖没必要——开店转场帧读缺交决策
      前置门响亮失败,禁重读等待);
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
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionBuyCardParam,
        CwActionDeployMoveParam,
        CwActionLevelUpParam,
        CwActionLevelUpShopParam,
        CwActionRefreshShopParam,
        CwActionSellBenchParam,
    )
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
    本门保留面:卖出 route-tag 泄漏显影。(效果账本 BUY 计数已迁买牌
    上报函数获取计算完时点的 ``gs.effects.on_buy`` 回调单点——live/sim
    同源,消除落地门计数分叉;刷新侧计数与免费腿扣减 = 刷新 op 自上报
    经上报函数单口,见 cw_action_report/refresh_shop。)

    ``_cur`` = 入口观察回执(defects 留证行 plane/round 基准;载体 =
    :class:`GameStateReadReceipt`,visit 内 plane/round 恒定不变)。
    """
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionBuyCardParam,
        CwActionSellBenchParam,
    )
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
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionRefreshShopParam,
    )
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

    决策动作 node 的逐动作执行落地写点:每动作 op 一条 logic_action 行,
    发出即簿记非验证(M1③):applied = 动作 op 自身机械事实透传,零成败
    判定。CloseShop **不写**(「终结不入 decisions 行」契约;执行事实
    回执由动作 op 自身承担)。journal 常开(ADR-0634)回执写入无条件,
    无局跳过在 kernel 口
    (:func:`~...kernel.cw_game_state.note_action_receipt`);
    best-effort 不阻塞循环。

    ``include_payload``:True = 回执行附带 ``action`` 键(serialize_action
    同 schema)。缺省 True = 发射行(execute 后落点);受阻挂点(动作未
    发射)传 False,载荷不入行。
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
            actor='CwScreenShop', extra=_extra)
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
#: 谓词,判读同表)。写点 = _note_shop_skip_unobserved 递增 / 访问完成
#: 出口复位;消费点 = 本函数熔断谓词。
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


class CwScreenShop(SrOperation):
    """货币战争商店画面 op(两 node 规范形态)。

    生产两路(外循环 0n 转交与备战显式开店同口 ``visit_open_shop``、
    ``run_operation`` 单跑)构造本类并节点函数直驱(观察 node 恰一次 →
    决策动作 node round_wait 循环至终结)。出参交接契约:实例暴露
    :attr:`ledger`(访问执行账,run 完成后有效);失败判定 = 轮结果
    ``is_success``。

    - 观察 node(每访问恰一次,唯一读屏点)= 兜底建核(独立单跑)→
      点击点位/升级钮/刷新钮 screen_info 锚定(缺失 = 建档漂移显式
      round_fail,禁兜底坐标静默点击)→ settle + park + 入口观察
      (:func:`_shop_entry_read`,读 + 未识别卡停机闸两段,单次读零防抖)
      → obs 镜像 → 段首簿记:段序号 +1(visit 边界 = op 边界,腾席拒绝
      结论的输入不变性段,跨 visit 伪命中封死)/ 帧代次 ``frame_class_shop
      = 'full'``(每访问入口;刷新后新访问重估方向视图,限频由方向重算
      既有键守卫「每 game-round 恰一次」承载)/ 店开帧预算披露覆写 /
      本访问已买件清零 / 状态行日志 / ``save_decision_frame('shop_entry')``
      (每访问一帧)。入口观察漏斗自带刷新次数观察锚定(观察写端在
      read_game_state 漏斗 shop-open 段,本 op 零额外调用)。
    - 决策动作 node(round_wait 单动作循环,与单选族节点循环同形)=
      决策(``decide_shop_action`` 终态零参口,容器零参读;异常留证后
      上抛)→(CloseShop 且 tracked 未观察 → 留痕/熔断,留痕后照常执行)
      → proposal 守卫 → 注册表类级解析 + ``ShopExecEnv`` 组装 + execute
      (全动作统一路径,零特例拦截零闸;CloseShop = 真点击)→ 簿记
      (回执/落地门/续段 token/义务实花;CloseShop 跳过回执)→ 终结读
      注册表:非终结 round_wait(帧不消费,零读屏);终结 round_success
      交回外循环(访问动作日志行交回前 log,回执 detail = 执行账汇总串)。
      刷新无次数上限(无限刷新环 = 策略实现 bug,框架不兜底)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-商店')
        from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
            ShopVisitLedger,
        )
        # 访问执行账(出参交接契约:run 完成后调用方读本属性;失败路径
        # 由薄壳映射为 None,消费面以 is_success 判定为准)。类型 =
        # ShopVisitLedger(operations/cw_op/cw_shop_action_ops)。
        self.ledger = ShopVisitLedger()
        # 观察 node 产物:入口回执镜像(obs,决策侧/测试消费面)、入口
        # 回执本体(落地门 defects 留证基准)与每访问一次的装配
        # (config/点击点位/升级钮/刷新钮/动作累积),决策动作 node 消费。
        self._obs: CwScreenShopObs | None = None
        self._entry: GameStateReadReceipt | None = None
        self._config: Any = None
        self._click_pts: list = []
        self._level_btn: Any = None
        self._refresh_btn: Any = None
        self._visit_actions: list = []

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """①兜底建核(独立单跑)②area 锚定 ③入口观察(单次读+停机闸)
        ④obs 镜像 ⑤段首簿记(每访问恰一次)。"""
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        match = getattr(self.ctx, 'cw_match', None)
        if match is None:
            # 防御:无对局态(独立 run_operation 调本 op)→ 兜底建核,直调
            # 引导漏斗同款序(establish_new_match = 生产唯一容器建立漏斗)。
            # 此前裸构造 CurrencyWarMatch 与漏斗实差三处行为——rng 种子(漏斗
            # 按 config.strategy_seed 播 session.rng)/布局未知态计数复位
            # (reset_layout_unknown_state 新局起点)/遥测 run_id_provider
            # (局容器建立点注入 journal 装配)。「局外不复用」语义保持:
            # 先弃置残留容器再建(每次独立 run_operation 新建;与入口链
            # CwEntryStart 的 discard+establish 同款衔接),漏斗幂等分支经
            # 前一步清场必走新建。
            from sr_od.application.currency_war.strategies.impl.cw_strategy import (
                discard_stale_match_container,
            )
            from sr_od.application.currency_war.strategies.impl.cw_strategy_manager import (
                establish_new_match,
            )
            discard_stale_match_container(self.ctx, 'buy_cards_defensive_rebuild')
            establish_new_match(self.ctx, config)
            match = self.ctx.cw_match
        self._config = config
        # 牌位/升级/刷新中心从 screen_info 直取;area 缺失 = 建档漂移,显式
        # round_fail(信息带 area 名),禁兜底坐标静默点击(坐标单一真相源)。
        # 方向视图由策略器决策入口内化刷新(帧代次标注触发,ADR-0583)。
        self._click_pts = shop_card_click_points(self.ctx)
        self._level_btn = area_center(self.ctx, BUY_EXP_AREA)
        if self._level_btn is None:
            return self.round_fail(
                f'area 缺失:{BUY_EXP_AREA}({SCREEN_NAME}),禁兜底点击')
        self._refresh_btn = area_center(self.ctx, '按钮-刷新', SHOP_SCREEN_NAME)
        if self._refresh_btn is None:
            return self.round_fail(
                f'area 缺失:按钮-刷新({SHOP_SCREEN_NAME}),禁兜底点击')
        # 等 board 面板 settle + 光标 parking(审计 P0,2026-08-16):park
        # 后再读。
        time.sleep(0.3)
        self.park_cursor(after_wait=0.1)
        # ---- 入口观察(唯一读屏点,即对账)----
        _entry, _entry_shot, _stop = _shop_entry_read(self, match)
        if _stop is not None:
            return _stop
        self._obs = CwScreenShopObs(
            gold=_entry.gold, gold_readable=_entry.gold_readable,
            hp=_entry.hp, hp_readable=_entry.hp_readable,
            hp_trusted=_entry.hp_trusted,
            level=_entry.level, level_readable=_entry.level_readable,
            plane=_entry.plane, round_num=_entry.round_num,
            node_type=_entry.node_type, board=dict(_entry.board or {}),
            shop=list(_entry.shop or []), screen=_entry_shot)
        self._entry = _entry
        save_decision_frame(self, 'shop_entry', _entry_shot)   # 识别完成点原始帧留证(牌面仲裁基准;每访问一帧)
        # (免费刷新的事实可见性宿主 = 容器字段 free_refresh_left 的观察
        #  锚定失配安灯 + 效果账本计数:入口锚定写端 = 观察漏斗 shop-open
        #  段刷新钮三态(漏斗自带,本 op 零额外调用);本文件无金/牌面
        #  快照比对对账件。)
        # T-82 段序号置位(商店 visit 开始):visit = 腾席拒绝结论的输入
        # 不变性段,入口 +1 使上一 visit/上一域(备战)残留的续段 token/
        # 结论闩按序号不等自动失效(跨 visit/跨战斗伪命中封死)。状态对象
        # 缺席(第三方策略面/桩)= 无缓存载体,跳过置位(缺席退缺省口径,
        # 决策核侧冷建自 0 起 = 恒重推导,保守端安全)。
        _st_seg = strategy_state_of(match.session)
        if _st_seg is not None:
            _st_seg.cw4_segment_serial += 1
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
        _tb = game_state_of(match.session).tracked_books.bench
        # P1 tracked bench = list[BenchSlot | None]:unit 槽读内嵌身份,
        # 占位件槽无身份以 ('', 1) 显影。
        _tb_rows = []
        for _b in (_tb or []):
            if _b is None:
                continue
            if getattr(_b, 'kind', None) == 'unit' and _b.unit is not None:
                _tb_rows.append((_b.unit.char_id, _b.unit.star))
            else:
                _tb_rows.append(('', 1))
        if _tb_rows:
            log.info(f'[cw] tracked_bench_chars='
                     f'{_tb_rows}(播种取消,仅日志显影)')
        if not _entry.shop:
            log.info('[cw] 店开入口牌面空(买空/OCR 失读窗):离屏语义关断,'
                     '容器沿用现值牌面决策')
        # 帧代次标注(ADR-0583 §3.4):每访问入口 = full(方向视图由
        # decide_shop_action 入口消费刷新;刷新后新访问 = 全新入口重估,
        # 限频由方向重算键守卫「每 game-round 恰一次」承载)。
        game_state_of(match.session).frame_class_shop = 'full'
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
        # 本访问已买件(carried 融合:R2-N1 刚买件首卖偏好)访问级清零。
        strategy_state_of(match.session).cw4_visit_bought_names = []
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
        log.info(f'[cw] state gold={_entry.gold} hp={_entry.hp} lv={_entry.level} '
                 f'plane={_entry.plane} round={_entry.round_num} node={_node} '
                 f'next={_next} board={_entry.board} '
                 f'target={target_name!r} fp={_fp_v:.2f} '
                 f'bench={len(bench_entries_of(game_state_of(match.session)))}')
        self._visit_actions = []
        # 未观察态的锚定 = 「策略关店 → 备战环 heavy 观察」链,店内零
        # 重建,观察态 = 容器字段 GameState.tracked_account_observed,出口
        # 跳过留痕/熔断见 :func:`_note_shop_skip_unobserved`;连续跳过计数
        # 复位在访问终结出口。
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """单动作 round_wait 循环(每轮恰一动作;循环内零读屏,帧不消费)。

        全动作统一路径零特例拦截零闸:受限消费政策 = 策略侧自限
        (详设 §2.10,决策入口提案后经谓词检);本循环零政策闸。
        """
        from sr_od.application.currency_war.kernel.cw_vocab import (
            CwActionCloseShopParam,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_class_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
            ShopExecEnv,
            guard_proposal_vs_expected,
        )

        match = self.ctx.cw_match
        # 决策异常留证(完整栈到 log,再向上抛,行为不变)。
        try:
            action = match.strategy.decide_shop_action()   # 终态零参口(§2.1)
        except Exception:
            import traceback

            _tb = traceback.format_exc()
            log.error('[cw!][plan] decide_shop_action 异常(留证后上抛):\n%s', _tb)
            raise
        # T-268:未观察态的策略关店 = 跳过访问,留痕 + 连续跳过熔断
        # (锚定失败显式出口);观察态(含已观察空账)零感知。留痕后
        # 照常走统一执行路径(未观察跳过 = 零消费动作,仅执行关店离店,
        # 备战环 heavy 观察锚定后再进店)。
        if isinstance(action, CwActionCloseShopParam) \
                and tracked_unobserved(match.session):
            _stop = _note_shop_skip_unobserved(self, match)
            if _stop is not None:
                return _stop
        # 守卫/env 读点 = 容器单例(提案动作的对象在期望态中存在且未被
        # 消费,炸出 = 策略器 bug)。
        _cur_gs = game_state_of(match.session)
        guard_proposal_vs_expected(action, _cur_gs)
        # 动作 op 重组批③:op 经注册表类级解析 + (ctx, param, env) 组装;
        # 上报由 op 自调,落地门只留计数/回执。(执行器端口分支已随画面
        # op 基类退役删除:直调节点函数 = 唯一路径;重试/停机查归包络与
        # 交回面,动作层零重试;节点异常原样上抛 = 执行异常通道不变。)
        _op_cls = action_op_class_for(action)
        _env = ShopExecEnv(
            op=self, match=match, config=self._config,
            click_pts=self._click_pts, level_btn=self._level_btn,
            refresh_btn=self._refresh_btn, ledger=self.ledger,
            state=_cur_gs)
        _result = _op_cls(self.ctx, action, env=_env).run()
        _ok = bool(_result.is_success)
        # 执行落地回执(R2 回执域,逐动作 op 一条 logic_action 行):
        # applied = 动作 op 自身机械事实(round 成功态;未落地 = False
        # + 摘要),发出即簿记非验证——本行零新增读屏零成败判定。
        # CloseShop 跳过:「终结不入 decisions 行」契约(执行事实回执由
        # 关店动作 op 自身承担)。
        if not isinstance(action, CwActionCloseShopParam):
            note_shop_action_receipt(
                match, action, applied=bool(_ok),
                reason='' if _ok else f'执行未落地({_op_cls.__name__})')
        apply_action_outcome(action, _ok, self._entry, match,
                             self.ledger, self._visit_actions)
        # T-82 续段 token 写入(生产商店循环执行位):动作确认已执行
        # 后置位 (动作型名, 当前段序号);未执行路径不写。策略器入口读后
        # 即清,下一帧据其判定 M2 停摆续段缓存命中。状态对象缺席 = 跳过
        # (B4 口径)。
        if _ok:
            _st_tok = strategy_state_of(match.session)
            if _st_tok is not None:
                _st_tok.cw4_frame_action_record = (
                    type(action).__name__, _st_tok.cw4_segment_serial)
        # 义务实花回执位记账(T-88;只在 execute 成功回执后累计,F4 栈
        # 守卫见函数注)。
        accrue_release_spent(match, action, _ok)
        if not _op_cls.terminal:
            # 非终结:round_wait(帧不消费,零读屏;决策循环无防御上限,
            # 不收敛 = 策略实现 bug)。
            return self.round_wait()
        # 访问终结(RefreshShop/CloseShop):访问动作日志行(plan=…,随轮
        # 累积)交回前 log;round_success 回执 detail = 执行账汇总串。交回
        # 外循环零额外动作——节点行观察归备战观察域,商店域零探针。
        log.info('[cw] shop=%s plan=%s',
                 [(s.kind,
                   (s.card.name, s.card.faction, s.card.cost)
                   if s.card else None) for s in (self._obs.shop
                                                  if self._obs else [])],
                 [_fmt_action(a) for a in self._visit_actions])
        # 连续跳过计数复位(T-268 编排者核进):复位条件 = 「完成了一次
        # 未跳过的正常访问」——本 visit 观察态已锚定且完整收工才重开熔断
        # 计数窗,K=2 数的是连续因未观察跳过,非任意间隔;跳过 visit
        # (未观察)与中途停机支都不复位。载体缺席静默跳过 = 无计数面。
        if not tracked_unobserved(match.session):
            _ct_fin = getattr(strategy_state_of(match.session),
                              'cw4_counters', None)
            if isinstance(_ct_fin, dict):
                _ct_fin[CW4_KEY_SHOP_SKIP_UNOBSERVED_STREAK] = 0
        return self.round_success(
            f'plan 买{self.ledger.total_buy}张 经验{self.ledger.total_xp_buy}击 '
            f'刷{self.ledger.total_refresh}次 卖{self.ledger.total_sell}张')
