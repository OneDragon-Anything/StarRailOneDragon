import time
from collections.abc import Callable
from typing import Any, ClassVar

from one_dragon.base.operation.operation_base import OperationResult as _OperationResult
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import (
    OperationRoundResult,
    OperationRoundResultEnum,
)
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig

# 迁移审计 w75(git 历史)(ADR-0335):after_operation_done 的 result 注解在类定义期求值,OperationResult
# 必须**运行期可导入**(TYPE_CHECKING 块对此场景不够——本模块无
# `from __future__ import annotations`;用 _ 别名避与参数名冲突)。
from sr_od.application.currency_war.kernel.cw_exec_state import exec_state_of
from sr_od.application.currency_war.kernel.cw_run_allocator import MatchOutcome
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.obs.cw_observation import (
    read_game_state,
    read_node_sequence,
    read_phase_round,
    reset_phase_round_cache,
)
from sr_od.application.currency_war.obs.cw_resume_lock import (
    locked_after_start_battle,
    probe_resolve,
    resume_candidate,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_aha_equip_pick import (
    CwScreenAhaEquipPick,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_armory_box import (
    CwScreenArmoryBox,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_battle_wait import (
    CwScreenBattleWait,
    SettlementState,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_bookcard import (
    CwScreenBookcard,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
    CwScreenBossBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_briefing import (
    CwScreenBriefing,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_consumable_overlay import (
    CwScreenConsumableOverlay,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_deploy_not_full import (
    CwScreenDeployNotFull,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_emblem_detail_popup import (
    CwScreenEmblemDetailPopup,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_encounter import (
    CwScreenEncounter,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_expert_invite import (
    CwScreenExpertInvite,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_fortune import (
    CwScreenFortune,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_interrupt_dialog import (
    CwScreenInterruptDialog,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_strategy import (
    CwScreenInvestStrategy,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_item_detail_popup import (
    CwScreenItemDetailPopup,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_megastar import (
    CwScreenMegastar,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_next_button import (
    CwScreenNextButton,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_partner import (
    CwScreenPartner,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_plane_detail import (
    CwScreenPlaneDetail,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_plane_transition import (
    CwScreenPlaneTransition,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_planner import (
    CwScreenPlanner,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
    CwScreenPrep,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep_locked_return import (
    CwScreenPrepLockedReturn,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_refresh_odds_popup import (
    CwScreenRefreshOddsPopup,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_role_detail_overlay import (
    CwScreenRoleDetailOverlay,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_shop_card_detail import (
    CwScreenShopCardDetailPopup,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_supply_node import (
    CwScreenSupplyNode,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_wait_one_one import (
    CwScreenWaitOneOne,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_wish_trial import (
    CwScreenWishTrial,
)
from sr_od.application.currency_war.operations.decision_frame_hooks import (
    save_decision_frame,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import StrategySession
from sr_od.application.currency_war.telemetry import state
from sr_od.application.currency_war.telemetry.op_journal import (
    _op_journal_pos_of,
    record_op_enter,
    record_op_exit,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# (期望态滞留 stall 线索 prep_stall_pending_expected 已随 ADR-0651 两态制
#  废除:expected_state 条目表拆除后无挂账滞留可报;无进展守卫的线索面 =
#  prep_no_progress_state_fingerprint 状态指纹 + 动作批并集,语义不变。)

#: gold 分量可信陈值载体(session 属性名;T-167 gold 分量钉死)。
#: 键式 = 标量 int。
#: 写点唯一 = prep_no_progress_state_fingerprint(开态可信帧现读写入);
#: 生命周期随 session(新局新容器自动失效)。同族键式载体 =
#: kernel ExecState.cw4_swap_fresh_buys(收编落点形态可参照)。
PREP_GOLD_TRUSTED_ATTR: str = 'cw4_prep_gold_trusted'


def prep_no_progress_state_fingerprint(session) -> tuple:
    """备战环状态指纹(环级无进展守卫的状态腿;只读 observe 现成字段,
    零新增识别)。

    任一分量变化 = 状态有推进:plane/round_num(轮次)、last_node_type
    (节点序推进,CwScreenPrep 观察段写)、gold(分量语义钉死见下)、
    bench/deployed 身份串(部署/装备/合成必变;deploy_count 用身份串而非
    计数,防「同数换人」漏检)。故意比旧留证线的对账字段族窄的部分
    (球/箱/vacancy)不再进指纹:它们由窗口动作批并集覆盖(动作在窗口
    出现过 ⇒ 其意图在案),收窄只为防识别抖动(球体检测闪烁)误计数。

    gold 分量语义(T-167 钉死,持久家 = ADR-0554 修订节第 5 条;
    last_state 链退役批换源申报):
    分量源 = 容器 ``bs.gold``——观察漏斗(``_feed_board_state``)仅
    gold_readable 帧观察写入,失读帧走 carry 不落值(关店帧 0 兜底
    与 OCR 噪声结构性进不了记录)。本函数钉死为「仅开态可信帧
    (prep_obs_frame.state_gold_trusted = heavy ∧ 店开,单一写点
    cw_screen_prep)更新可信陈值(session 属性 PREP_GOLD_TRUSTED_ATTR),
    其余帧沿用陈值」:真买入/升级/刷新必经开店帧,真值写入即变指纹,
    进展检测无损;卖出有 bench/deployed 身份串兜底;关店帧 gold 抖动
    不再归零计数——防「恒态下指纹分量抖动 = 永不触发」的失效方向。
    无陈值时(开局首店前)回退容器现值:未观察 = None,漏斗质量门保证
    容器无噪声值,旧 raw 兜底的「噪声至多延迟出口」面随之消失(同向
    更稳,守卫停机/哨兵兜底不变)。⚠️ 本函数带一次 session 属性写入
    (可信陈值更新),属守卫消费链的记账副作用,不改变「纯读 observe
    现成字段」的识别面。轮次分量源 = 容器节点读口(plane_of/round_num_
    of,引导窗缺省镜像旧帧缺省;last_state 槽已随链退役批删除)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        board_state_of,
        plane_of,
        round_num_of,
    )
    _frame = getattr(session, 'prep_obs_frame', None)
    _ids = lambda chars: tuple(  # noqa: E731  身份串(零新识别,读 heavy 观察现成字段)
        getattr(bc, 'char_id', '') for bc in (chars or []))
    _bs = board_state_of(session)
    _gold_obs = _bs.gold.value
    if getattr(_frame, 'state_gold_trusted', False) and _gold_obs is not None:
        setattr(session, PREP_GOLD_TRUSTED_ATTR, _gold_obs)
    _gold = getattr(session, PREP_GOLD_TRUSTED_ATTR, _gold_obs)
    return (
        plane_of(_bs),
        round_num_of(_bs),
        getattr(session, 'last_node_type', None),
        _gold,
        _ids(getattr(_frame, 'bench_chars', None)),
        _ids(getattr(_frame, 'deployed_chars', None)),
    )


def prep_no_progress_tick(prev_sig: tuple | None, prev_count: int,
                          prev_actions: frozenset[str] | None,
                          sig: tuple,
                          actions: tuple[str, ...]) -> tuple[
        tuple | None, int, frozenset[str]]:
    """守卫计数纯函数(F2 单键化,T-167):同状态指纹累加,异指纹归零;
    窗口动作批并集累积器随指纹变化归零重开(便于三历史重放/健康序列
    锁测)。

    计数键变更依据(T-167 诊断②结构缺口):旧键 (动作批, 指纹) 被策略
    闩驱动的签名振荡穿透——交替 OpenShop/RunDeploy 每帧归零,相位级
    出口全灭。守卫语义 = 「相位不推进」,状态指纹单键即相位真值;
    振荡签名 + 恒指纹恰是最纯的「忙而无功」。动作批降级为窗口留证与
    臂判别输入(并集累积器)。

    :param prev_actions: 窗口动作批并集累积器(同指纹逐环并入;指纹变化
        即重开为本环动作)。
    :param actions: 本环动作批(调用方保证非 None;None 批 = overlay
        交回/策略异常/破墙前,调用方在共同出口归零计数与并集——overlay
        垄断形态维持哨兵档,本守卫不越界,ADR-0554 修订节第 3 条)。
    """
    if sig == prev_sig:
        return prev_sig, prev_count + 1, (prev_actions or frozenset()) | set(actions)
    return sig, 0, frozenset(actions)


#: 收益耗尽臂窗口动作白名单(F2 判据放宽;ADR-0554 修订节第 2 条):
#: 恒指纹窗口
#: 内出现过的动作批并集 ⊆ {OpenShop, RunDeploy} 才可能出战——真实进展
#: 必变指纹,能留在恒指纹窗口的动作定义性零变换(零购买开店=纯读、
#: 无部署可做 RunDeploy=合法稳态);第三类动作(DeferSpheres/ClickSpheres/
#: RunEquip/SellBench 等)在窗口出现 = 语义未核实,不出战、落守卫停机
#: 留证交判读(不代打)。
EXHAUSTION_WINDOW_ACTIONS: frozenset[str] = frozenset({'OpenShop', 'RunDeploy'})


def prep_exhaustion_launch_eligible(action_sig: tuple | None,
                                    last_prep_success: bool | None,
                                    actions_union: frozenset[str] | None = None,
                                    ) -> bool:
    """备战收益耗尽 → 出战判据(纯函数;消费点 = 环级无进展守卫触发位)。

    机制依据(docs/game/currency_war/data/gameplay.md 权威机制):备战环
    等待的边际收益恒等于 0——商店「每个节点自动刷新 1 次」(节点推进以
    战斗完成为前提)、基础金币/利息/连胜奖励均在「每场战斗结束时」结算。
    出战的边际收益 ≥ 0(战斗必有结算收入),且战力由当前板面决定、与
    等待时长无关(等待不改变任何战力输入)⇒ 支配性论证:收益耗尽帧
    出战严格优于继续等待,无参数权衡,零拍定值。

    判据(F2 放宽,T-167;ADR-0554 修订):
    - **恒指纹窗口动作批并集 ⊆ {OpenShop, RunDeploy}**(EXHAUSTION_WINDOW_
      ACTIONS):恒指纹本身已是窗口内全部动作的定义性零变换证明——真实
      买入/卖出/升级必变 gold 或身份串,无需逐动作核实计划是否为零;
      窗口含白名单外动作 = 语义未核实形态 → 不出战(守卫停机留证);
    - **末批 = RunDeploy**(``action_sig[-1]``):有部署意图在场才替以
      出战;末批 = OpenShop 的第 3 恒指纹环判据假 → 落守卫停机留证——
      出战/停机出口按末批相位二选一,3 环内必有出口,结构性缺口闭合
      是确定性的(两种末批相位形态都锁,实机验收断言「必出战」
      只对末批=RunDeploy 相位成立);
    - **上一备战环 success**:发射契约保证「计划空+0 落地 = STATUS_
      NOOP 合法稳态」走 success、「计划非空+0 落地 = 执行面失败」走
      round_fail——success 即排除执行面失败形态(拖拽落空/遮罩挡拖拽);
    - None 批不累计(调用方共同出口归零)。
    """
    return (last_prep_success is True
            and bool(action_sig)
            and action_sig[-1] == 'RunDeploy'
            and bool(actions_union)
            and actions_union <= EXHAUSTION_WINDOW_ACTIONS)


def no_progress_flag_path():
    """守卫停机 flag 落点(与 stall_watch.flag/unknown_state.flag 同目录族)。"""
    return (get_project_root() / '.debug' / 'temp' / 'currency_war'
            / 'prep_no_progress.flag')


def prep_exhaustion_exclusion_reason(ctx, screen) -> str:
    """收益耗尽臂排除族(F2 边界;返回拒因键,'' = 不排除,可出战)。

    排除族可扩展形态(T-167):新排除形态在此追加一腿,消费位零改。

    - ``exhaustion_supply``:补给节点出战不推进(节点推进以战斗完成为
      前提,补给节点的出口是补流程非出战——既有 divert 分支同语义),
      该形态收益耗尽的正确出口 = 补流程,维持守卫停机交留证判读;
    - ``exhaustion_reward_sphere``:奖励节点 ∧ 球在场 → 暂缓强制出战。
      ⚠️ **实机观测项,离线不可判**(T-167 前置声明):「奖励球滞留态
      强制出战,球/奖励是否随节点推进继承」玩法文档未记录(screen_flow_
      timing.md #16 只记点球动画时长与席满容忍语义,未记滞留球奖励
      归属)。与 supply 排除同构式实现(当前节点类型='reward' ∧ 球在场
      两条件合取——防「奖励节点球已收清」帧被误排除);若实机核实球随
      节点推进继承,删本腿即可(排除族可扩展形态承载)。检测退化
      (识别异常)不排除——出战优先,同前置引入前的现行为。
      登记持久家 = ADR-0554 修订节第 6 条。

    节点类型读法 = read_node_sequence 的 current 槽(与 divert 分支同源)。
    """
    _slot = next(
        (s for s in (read_node_sequence(ctx, screen) or [])
         if s.state == 'current'), None)
    _node_type = getattr(_slot, 'node_type', None) if _slot is not None else None
    if _node_type == 'supply':
        return 'exhaustion_supply'
    if _node_type == 'reward':
        try:
            from sr_od.application.currency_war.obs.cw_identity_obs import (
                read_reward_spheres,
            )
            if read_reward_spheres(ctx, screen):
                return 'exhaustion_reward_sphere'
        except Exception:   # noqa: BLE001  检测退化不排除(出战优先)
            pass
    return ''


def write_no_progress_flag(count: int, sig: tuple, shot: str,
                           path=None) -> str:
    """守卫存证 flag(计数+状态指纹+截图路径+处理指引;测试传 tmp_path)。

    ``sig`` = 状态指纹单键(F2;旧二元组「动作批, 指纹」的计数键随
    T-167 迁移,动作批降级为窗口留证,见 prep_no_progress_tick)。
    """
    p = path if path is not None else no_progress_flag_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f'[HOOK-STOP] 环级无进展守卫触发:连续 {count} 个备战环'
        f'「状态指纹零推进」(F2 单键计数;窗口动作批并集见判定日志)\n'
        f'状态指纹(plane,round,node,gold,bench_ids,deployed_ids):\n'
        f'{sig}\n'
        f'处理流程:\n'
        f'1. 看决策日志备战环动作批:同相位动作反复发射而板面/金/轮次不动'
        f'= 忙而无功(执行面变换失败/策略闩振荡/闩漏网活锁)→ 按截图判'
        f'当前画面:\n'
        f'   未建档 overlay → od-dev-screen-onboarding 建档 + cw_loop 0x 分支\n'
        f'   加 handler;已建档 → 查该动作执行链为何零变换;\n'
        f'2. 处理完删本 flag + 重启 MCP server。\n'
        f'shot={shot}', encoding='utf-8')
    return str(p)


def locked_resume_sync_and_battle(op, ctx):
    """恢复局锁定直出战(ADR-0329)+ **首战前备战同步步**(裁定出处 =
    策略审查报告 .debug/temp/currency_war/20260905-093104-strategy-review/
    策略审查-第十二跳.md #7):恢复局分支原样跳过全部备战交互直接
    StartBattle,板面调整被跳过(实证:恢复局首战快照 board_before 为空
    ——部署面零执行)。本函数在 StartBattle 前插一次 **RunDeploy 组合
    同步步**(deploy-swap/腾席/确定性部署整面跑一遍,零商店交互——锁定
    局「商店探针零响应」禁令只辖商店域,部署面不受辖)。

    证据位语义(批3a 修订,T-223 最严读法申报「发出即写」):同步步
    RunDeploy **发射后立即置位** ``op._cw_locked_sync_done``——原「ok=True
    才置位 + 失败重试(上限 3)」消费执行器成败回执,回执随 T-223 退役,
    失败概念在发射型下消解,重试/放弃治理结构随之退役(发射次数预算
    承载归批4 J2 形态,同源重推);「部署是否真落地」由下一帧观察侧
    reconcile 对账暴露(同 T-82 token 门「发出即写」同款裁定)。锁定
    确认分支复位证据位。

    隐藏前提声明(R3):同步步的「不误卖」依赖恢复局 session 必新鲜——
    恢复检测链(cw_resume_lock.is_new_match)恒走新容器,节点未观察
    ⇒ deploy-swap 卖出通道整体跳过(board 未观察不可判),同步步实际
    只做确定性部署;若未来恢复检测放开 mid-run 复用 session,stale board
    会让同步步按旧目标线卖新局板面——届时须先加卖出输入守卫。

    **无条件插入,零血线判据**:hp 入参合规口径 = λ 表血带维或已确认
    硬地板授权(00_framework §3)——「hp≤阈值则强制同步」形态不落码,
    挂账待玩家确认。与「达标即出战」臂(§9.6)的关系按 C1 规格:本函数
    = 恢复局面调用面(闩辖),底层发射核 = ``launch_prepared_battle``
    单一函数,达标臂经 ``readiness_battle_launch`` 调用面共用发射核、
    **不过本闩**(W1:旧「须经本函数单一发射位,禁旁路」话术与 C1 矛盾,
    按规格改写)。
    """
    return launch_prepared_battle(op, ctx, sync_once=True)


def launch_prepared_battle(op, ctx, *, sync_once: bool = False):
    """出战底层发射核(C1 单一发射函数,14号稿 §9.6):RunDeploy 组合 +
    StartBattle 的执行核,恢复局面与达标臂两调用面共用,禁各写一套
    StartBattle 发射位。

    - ``sync_once=True``(恢复局面面,调用面 = locked_resume_sync_and_
      battle):首战前插备战同步步,**发出即置位**证据位
      ``op._cw_locked_sync_done``(批3a,T-223 回执退役后失败概念消解,
      见 locked_resume_sync_and_battle docstring);连续失败放弃结构随
      退役。锁定确认分支复位证据位。
    - ``sync_once=False``(达标臂面,调用面 = readiness_battle_launch):
      **不过闩**——每达标帧都 RunDeploy+StartBattle(部署面现读重建,
      已同步形态下 RunDeploy 合法 no-op 即零待部署;闩只辖恢复局面,
      达标臂第二次发射被「每局恰一次」闩吞 = C1 明令防的双源病)。

    返回 ``(launch_ok, detail)`` = StartBattle 发射位**内部事实**(执行器
    last_launch_ok 旁路;A6 出战链判效面,批4 随 J2/J3/J4 消费端同退役,
    非 T-223 端口回执——端口本 身已无返回)。W209j 刹车短路(停机标志
    已设)→ 返回 (False, '已停止[W209j刹车]'),交回外循环由 loop 顶退出。
    """
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        RunDeploy,
        StartBattle,
    )
    from sr_od.application.currency_war.prep_actions import (
        PrepActionExecutor,
        StopBrakeShortCircuit,
    )
    ex = PrepActionExecutor(op, ctx)
    try:
        if sync_once:
            if not getattr(op, '_cw_locked_sync_done', False):
                ex.execute(RunDeploy())   # 机械执行无返回(T-223)
                # 发出即写(批3a 申报,T-223 回执退役;失败概念消解)
                op._cw_locked_sync_done = True
                log.info('[cw-loop] 恢复局备战同步步(RunDeploy)已发出: %s',
                         getattr(ex, 'last_detail', ''))
            else:
                log.debug('[cw-loop] 恢复局同步步已置位,跳过 RunDeploy')
        else:
            # 达标臂面:每帧 RunDeploy(部署面现读重建;已同步形态合法 no-op)
            ex.execute(RunDeploy())
            log.info('[cw-loop] 达标臂 RunDeploy: %s', getattr(ex, 'last_detail', ''))
        ex.execute(StartBattle())
    except StopBrakeShortCircuit as e:
        log.info('[cw-loop] 停机刹车(%s)→ 出战链动作未发出,交回外循环', e)
        return False, '已停止[W209j刹车]'
    # StartBattle 发射位内部事实(A6 判效面,批4 同退役;getattr 容缺 =
    # __new__/桩形态兼容)
    return bool(getattr(ex, 'last_launch_ok', False) or False), \
        getattr(ex, 'last_detail', '')


def readiness_admission_report(state, comp) -> dict:
    """达标臂 G1 准入预估(§9.2 三元+victim 收口,发射面显影用)。

    实现单一源 = ``kernel.cw_launch_admission.launch_admission_report``
    (发射面观测批迁出:sim 桶不可依 app 桶——包依赖矩阵 LEGAL_EDGES,
    纯判据入 kernel 后 sim 引擎/cw_loop/测试三方共用;线成员谓词由本
    调用面注入同一单一源,禁各面自写第二实现)。判据语义、三元口径与
    **帧对齐说明**(预估源 = 容器单例 board_state_of,T-146 装配源迁移
    ——旧 last_state 滞后帧+过渡桥装箱退役;单例与滞后帧同为备战观察
    写端刷新,预估显影非拦截,一轮滞后语义本就可接受)见彼处 docstring。
    ``state`` = session(容器单例取源)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        board_state_of,
    )
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        launch_admission_report,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )
    return launch_admission_report(board_state_of(state), comp,
                                   line_members=line_members)


def readiness_battle_launch(op, ctx):
    """达标即出战臂调用面(14号稿 §9.6):线成型(fp≥1.00,备战环锚帧)
    ∧ 战斗就绪 ⇒ 立即 RunDeploy 组合 + StartBattle,不过
    ``_cw_locked_sync_done`` 闩(C1:闩只辖恢复局面,达标臂每达标帧发射)
    ——发射核与恢复局面共用 ``launch_prepared_battle``,禁第二套
    StartBattle 发射位。

    **执行时刻新鲜屏态复验**(切屏竞态实测病例·遭遇屏形态:loop 早前读的备战双锚到
    执行时已过期——切屏瞬间误真,9 拖全空挥 placed=0):发射前重截图
    复验备战屏锚(复用既有锚,零新参数);非备战屏 → 放弃本次发射,
    ``readiness_stale_screen`` 分键零静默,屏态过期**非发射失败**(返回
    (False, 'readiness_stale_screen'),调用方不消耗 C1 失败计数)。

    发射前过 **G1 准入预估**(§9.2 三元+victim 收口,
    ``readiness_admission_report``):板满∧bench core∧victim 缺失形态
    记 ``deploy_swap_no_victim`` 分键(零静默,§9.2);准入只显影不拦截
    (出战优先)。位次 = 备战环动作链之前、守卫计数之前(§10)。"""
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    try:
        _fresh = op.screenshot()
        _still_prep = _prep_anchors_hit(op, _fresh)   # C3:双锚单一源
    except Exception as e:  # noqa: BLE001  复验不可用不阻塞(保守放行;
        # 放行/放弃之辩归编排者裁,本批只补观测面:分键零静默与 stale 分支对齐)
        log.warning('[cw-loop] 达标臂屏态复验失败(保守放行): %s', e)
        try:
            from sr_od.application.currency_war.telemetry.defects import (
                record_defect,
            )
            record_defect(
                'deploy', 'readiness_recheck_error',
                expected='复验链 screenshot/find_area 正常',
                observed=f'异常:{type(e).__name__}',
                gap_large=False, auto_resolved=False,
                verdict=('留证-屏态复验异常保守放行(切屏瞬间误真 9 拖空挥'
                         '面重新暴露的观测入口;放行/放弃裁归编排者)'),
                reader_source='readiness_recheck',
                note='复验异常分键(与 readiness_stale_screen 分支对齐零静默)')
        except Exception:   # noqa: BLE001  遥测 best-effort
            pass
        _still_prep = True
    if not _still_prep:
        counters = getattr(strategy_state_of(_sess), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters['readiness_stale_screen'] = \
                counters.get('readiness_stale_screen', 0) + 1
        log.info('[cw-loop] 达标臂放弃发射:执行时刻非备战屏'
                 '(屏态过期,readiness_stale_screen)')
        return False, 'readiness_stale_screen'
    try:
        _tc_adm = getattr(strategy_state_of(_sess), 'target_comp', None)
        if _sess is not None and _tc_adm is not None:
            # 换源 T-146:预估源 = 容器单例(读 side 改传 session,见
            # readiness_admission_report docstring)
            _adm = readiness_admission_report(_sess, _tc_adm)
            if (_adm['board_full'] and _adm['bench_core_waiting']
                    and _adm['victim_missing']):
                counters = getattr(strategy_state_of(_sess), 'cw4_counters', None)
                if isinstance(counters, dict):
                    counters['deploy_swap_no_victim'] = \
                        counters.get('deploy_swap_no_victim', 0) + 1
                log.warning('[cw!][loop] 达标臂 G1:板满 ∧ bench core 待上 '
                            '∧ 无合格 victim → 本帧出战无腾位(显影,'
                            'deploy_swap_no_victim)')
    except Exception as e:  # noqa: BLE001  准入预估 best-effort,不阻塞出战
        log.debug('[cw-loop] G1 准入预估失败(不阻塞): %s', e)
    return launch_prepared_battle(op, ctx, sync_once=False)


def _prep_anchors_hit(op, screen) -> bool:
    """备战双锚命中判定(小helper,复用 0 系锚表同款两锚;禁判据外散写)。"""
    return (op.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验',
                                  crop_first=False).is_success
            and op.round_by_find_area(screen, '货币战争-备战', '按钮-出战',
                                      crop_first=False).is_success)


def _launch_arb_counter(op, key: str) -> None:
    """仲裁分键自增(best-effort;计数容器缺席静默跳过,家族同口径)。"""
    try:
        counters = getattr(strategy_state_of(
            op.ctx.cw_match.session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters[key] = counters.get(key, 0) + 1
    except Exception:   # noqa: BLE001  遥测 best-effort,不阻塞游戏流
        pass


def _launch_frame_arbitration(op) -> dict:
    """发射帧受限消费仲裁(出口 B 溢出段;金出口族 DESIGN v1.1 §3.2,
    落码裁决 = ADR-0566)。

    **位次契约(v1.1 I-2 钉死)**:只在「确将发射」路径执行 = ①armed
    判定通过(调用点上游 ``readiness_launch_decision``,判据零改动)→
    ②浮层在场闸通过(调用点上游,``_ov_hit is None``)→ ③本函数内
    ``_prep_anchors_hit`` 预检通过——预检只作仲裁段的门,发射链零改动;
    调用点 = ``readiness_battle_launch`` 之前,发射核内部屏态复验保留作
    纵深防线:仲裁若未恢复备战屏态 ⇒ 走既有 stale 分支弃射,调用点记
    ``launch_arbitrage_abandoned_launch`` defect 分键(可辨识残量,从
    「非发射帧 digest 零变化」锚辖域显式豁免,禁静默)。

    **语义**:溢出段(g > g*,判定单一源 = kernel ``in_launch_spend_zone``
    与必花域共享 saturation_line 链)开一次受限商店访问 = open_shop →
    ``run_buy_waves(spend_gate=预算闸闭包)`` → close_shop。消费对象与
    评估序全部由 shop 出口族既有评估栈(策略器单动作核)裁决,闸只辖
    「花后金位 ≥ g*」(P70 Δ息=0 形;花穿息线部分出辖 = p70 边界 1,
    判定单一源 = ``kernel/cw_launch_arbitrage.launch_arbitration_gate``)
    ——不新造第二套评估语义(金出口族红线 1/5)。带内段(g ≤ g*)挂
    L1' 独立命题 fail-closed 不开店(证不出不花;带内帧计
    ``launch_arbitrage_inband_closed`` 分键,与「溢出帧零消费」可辨)。

    **预算闸闭包读金口径** = 期望态黑板现读(``session.shop_state_frame``,
    run_buy_waves 逐动作投影回写)= 决策与闸同帧同值。后验跌破 g* 检测
    (合并多买等投影外成本)计 ``launch_arbitrage_cross_line``,正常恒 0。

    返回报告 dict:``entered``(是否进入过商店访问——弃射豁免判定位)、
    ``zone``('overflow'/'inband')、``executed``(本帧消费动作数)、
    ``gate_blocks``(闸拦截数)。

    遥测载体:溢出段访问落 op='发射帧仲裁商店访问' enter/exit 行(第三
    载体,ADR-0584 §5.1;预检/带内路径零行)。
    """
    report: dict = {'entered': False, 'zone': 'inband', 'executed': 0,
                    'gate_blocks': 0, 'abort': False}
    # 第三载体 op 行 token(ADR-0584 §5.1):None = 访问窗口未开(预检/带
    # 内路径零行);非 None 期间任何出口(含异常)必须配对 exit,孤儿 enter
    # 语义回归「进程中断专属」。
    _arb_token: dict | None = None
    from sr_od.application.currency_war.kernel import cw_launch_arbitrage
    try:
        _fresh = op.screenshot()
        if not _prep_anchors_hit(op, _fresh):
            # 预检失败 = 屏态存疑:仲裁段不进入(开商店切屏会污染待判屏),
            # 交发射核既有屏态复验裁定;分键显影防「静默跳过」形态。
            _launch_arb_counter(op, cw_launch_arbitrage.KEY_PRECHECK_SKIP)
            return report
        from sr_od.application.currency_war.kernel.cw_economy import (
            cap_resolved_of_session,
            in_launch_spend_zone,
            saturation_line,
        )
        from sr_od.application.currency_war.obs.cw_observation import (
            PHASE_PREP_CLEAN,
            read_game_state,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_buy_cards import (
            run_buy_waves,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_close_shop import (
            close_shop,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_op_open_shop import (
            open_shop,
        )
        match = op.ctx.cw_match
        session = match.session
        # 开店前干净备战全量读(关店帧 = hp 真读主路径):hp 三件组供评估栈
        # 血线消费门(危机停付/血预算),传缺省会让升级臂被 fail-closed 全拦;
        # 金位预判只作开店门,权威判定在访问内预算闸(入口观察含 gold 救援)。
        _pre = read_game_state(op.ctx, _fresh, phase=PHASE_PREP_CLEAN)
        _sess_hp = session
        if not in_launch_spend_zone(int(_pre.gold or 0), _sess_hp):
            # 带内段 fail-closed(DESIGN v1.1 §3.2;L1' 挂账):不开店不花。
            _launch_arb_counter(op, cw_launch_arbitrage.KEY_INBAND_CLOSED)
            return report
        _launch_arb_counter(op, cw_launch_arbitrage.KEY_ZONE_FRAMES)
        # 第三载体 op 行(ADR-0584 §5.1):仲裁触发的商店访问此前零边界
        # 载体——不经 dispatch 包装、无 OpenShop 决策行,档案只剩无头商店
        # 段决策行,复盘按行重建会误归 0n。enter 挂 open_shop 前(行窗口 =
        # 访问尝试边界),exit 覆盖全部出口(open 失败/abort/正常/异常)。
        _arb_token = record_op_enter('发射帧仲裁商店访问',
                                     *_op_journal_pos_of(op.ctx))
        # B3 拆除(验证废除,用户裁定 2026-09-10;M1③ 调用方不问成败):
        # open_shop 的 is_success=False 仅余「入口观察失败(动作没发出)」
        # 一种来路(「点击已发」走机械 retry 语义由编排壳重入承载,直调场景
        # 不再可得)——此分支语义 = 访问没发生,如实计 open_failed,非动作
        # 验证。
        _r_open = open_shop(op)
        if not _r_open.is_success:
            _launch_arb_counter(op, cw_launch_arbitrage.KEY_OPEN_FAILED)
            record_op_exit(_arb_token, outcome='fail', detail='open_failed')
            _arb_token = None
            return report
        report['entered'] = True

        def _gate(action) -> tuple[bool, str]:
            # 读金口径(W6 波 4 黑板容器化,设计件 §2.4-2):容器读口
            # ``gold_of``(缺省 0 镜像,与原 ``int(... or 0)`` 兜底同型
            # 零行为差;禁裸 bs.gold.value 引入 None 形态行为差)——黑板
            # 槽退役后闸与决策同读容器,逐动作投影回写经
            # apply_shop_action_logic 承接,同帧同值语义不变。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
                gold_of,
            )
            gold_now = gold_of(board_state_of(session))
            ok, why = cw_launch_arbitrage.launch_arbitration_gate(
                action, gold_now, _sess_hp)
            if not ok:
                report['gate_blocks'] += 1
                _launch_arb_counter(op, cw_launch_arbitrage.KEY_GATE_BLOCKS)
            return ok, why

        _hp = getattr(_pre, 'hp', None)
        _hp_readable = bool(getattr(_pre, 'hp_readable', False))
        _hp_trusted = bool(getattr(_pre, 'hp_trusted', False))
        _rr, outcome = run_buy_waves(op, match, _hp, _hp_readable,
                                     _hp_trusted, spend_gate=_gate)
        if _rr is not None:
            # 访问失败路径不开收(店留着,与 prep 链同语义;典型 = 未识别卡
            # 停机钩子已置 stop_running——保画面待建档,禁关店/禁发射摧毁
            # 现场):abort 旗交调用点跳过本轮发射,交回外环由停机接管。
            report['abort'] = True
            record_op_exit(_arb_token, outcome='fail', detail='abort')
            _arb_token = None
            return report
        _ = close_shop(op)   # B3 拆除:发出即过,不问成败(关店动作本身必发)
        if outcome is not None:
            report['executed'] = int(outcome.total_buy + outcome.total_level
                                     + outcome.total_refresh)
            if report['executed'] == 0:
                _launch_arb_counter(op,
                                    cw_launch_arbitrage.KEY_ZERO_CONSUME)
            # 后验跌破检测:闸投影成本与执行侧真实成本存在模型差时暴露
            # (正常恒 0;>0 = 残量显影,判读归 ADR-0566)。
            g_star = saturation_line(cap_resolved_of_session(_sess_hp))
            _final_gold = int(getattr(outcome.state, 'gold', 0) or 0)
            if report['executed'] > 0 and _final_gold < g_star:
                _launch_arb_counter(op, cw_launch_arbitrage.KEY_CROSS_LINE)
        # B3 拆除(同上,M1③):close_shop 的验关型失败回执退役——直调场景
        # close 的 is_success=False 来路已不存在(点击已发 = 机械 retry 语义,
        # 幂等观察 success / 点击已发 retry;关没关由下一帧观察侧对账 0n
        # 三锚/备战双锚自然闭环),出口行恒 ok。
        record_op_exit(_arb_token, outcome='ok', detail='')
        _arb_token = None
        return report
    except Exception as e:   # noqa: BLE001  仲裁异常不阻塞发射(出战优先,
        # 14号稿 §9.6 出战优先语义;异常帧=零消费帧,digest 锚辖域内)
        if _arb_token is not None:
            # 异常路径也必须闭合 op 行(ADR-0584 §5.2 同一口径):补行后
            # 仲裁段自身不得新增孤儿 enter。
            record_op_exit(_arb_token, outcome='error', detail=str(e)[:120])
            _arb_token = None
        log.warning('[cw-loop] 发射帧仲裁异常(不阻塞发射,零消费): %s', e)
        return report


def _shop_open_anchors_hit(op, screen) -> bool:
    """开商店态三 id_mark 锚判定(备战子态族分支 0n 判据单一源)。

    锚集 = 「备战标识-购买经验」+「按钮-收起」+「标识-备战阶段」
    (画面档 currency_war_battle_prep_shop_open.yml,idmark 审计批定稿)。
    三锚全命中才认商店态;互斥依据 = 离线配对验证(idmark 审计表 §三):
    干净备战帧「按钮-收起」不存在 → 开商店档零候选,不与备战(1)双门
    竞争(但序位仍须在备战前,见分支注释)。
    """
    return (op.round_by_find_area(screen, '货币战争-备战-开商店',
                                  '备战标识-购买经验',
                                  crop_first=False).is_success
            and op.round_by_find_area(screen, '货币战争-备战-开商店',
                                      '按钮-收起',
                                      crop_first=False).is_success
            and op.round_by_find_area(screen, '货币战争-备战-开商店',
                                      '标识-备战阶段',
                                      crop_first=False).is_success)


def _shop_card_detail_anchor_hit(op, screen) -> bool:
    """商店卡牌详情弹窗双 id_mark 锚判定(0t 分支判据单一源,T-163 建档)。

    锚集 = 「按钮-购买」+「按钮-角色详情」(画面档 currency_war_shop_card_
    detail.yml,id_mark 均取弹窗前景独有元素;禁取衬底透出的底层锚——弹窗
    暗色衬底遮蔽底层屏档全部锚,T-163 实证:开商店三锚/备战双锚在该衬底
    下 OCR 全灭,锚必须挂在弹窗自己的前景上)。双锚全中才接管,单锚形态
    (其他带购买按钮的弹窗)不放行。
    """
    return (op.round_by_find_area(screen, '货币战争-商店卡牌详情',
                                  '按钮-购买',
                                  crop_first=False).is_success
            and op.round_by_find_area(screen, '货币战争-商店卡牌详情',
                                      '按钮-角色详情',
                                      crop_first=False).is_success)


def _role_detail_anchor_hit(op, screen) -> bool:
    """详情弹窗双锚其一判定(1b 分支判据单一源,T-163 锚化)。

    锚集 = 「按钮-装备推荐」(角色详情变体,归档 fixture 4/4 命中)∨
    「装备详情-合成公式」(可合成列表变体,该变体 fixture 命中),同档
    currency_war_battle_prep_equip_detail.yml。取代旧全屏 OCR「可合成列表」
    ∨「角色详情」(lcs 0.8):全屏「角色详情」与商店卡牌详情弹窗底部按钮
    (x560-930)全等共享(LCS 1.0,收紧无济于事)→ T-163 弹窗被 1b 垄断
    26 分钟——outer_loop.md §2.1「优先 area 化」的存量欠账清偿,位置约束
    天然区分两变体。
    """
    return (op.round_by_find_area(screen, '货币战争-备战-角色详情',
                                  '按钮-装备推荐',
                                  crop_first=False).is_success
            or op.round_by_find_area(screen, '货币战争-备战-角色详情',
                                     '装备详情-合成公式',
                                     crop_first=False).is_success)


def _invest_anchor_hit(op, screen) -> bool:
    """投资策略浮层 id_mark 标识锚(固定位置全等,既有 0e 判据;便宜
    area 对拍)。"""
    return op.round_by_find_area(screen, '货币战争-投资策略',
                                 '标识-请选择投资策略',
                                 crop_first=False).is_success


def _invest_ocr_hit(op, screen) -> bool:
    """投资策略浮层 OCR 全短语信号(「请选择投资策略」+ lcs 0.8,承 0e
    分支既有口径杀「投资环境」交叉误匹配;全屏 OCR,首探与复探各付一次,
    成本申报见 _invest_overlay_dispatch docstring)。"""
    return op.round_by_ocr(screen, '请选择投资策略',
                           lcs_percent=0.8).is_success


def _invest_overlay_dispatch(op, screen):
    """0e 投资策略浮层分发判据(N5 稳定化,根修)。返回 (dispatch, screen)。

    **病灶**(第十五局两时序形态一正一误):同投资策略浮层,14:52 首帧
    锚命中走 overlay 分支;15:14 浮层淡入动画期首帧采样 miss → 判别翻转
    落备战链 → 空挥 37s。单探测判据对淡入期采样不稳定 = 分发层根因。

    **稳定化 + 成本门控(三审 C2/C1 修)**:
    - 首探双信号(id_mark 锚 ∨ OCR 全短语「请选择投资策略」)**不受
      双锚门控**——浮层淡入∧双锚也 miss 形态下删 OCR 兜底 = 删保险
      (判别翻转回潮面);
    - 复探(短窗 + 新截图,执行层时序常量)仅在穿透形态(双锚命中,
      浮层盖备战的可达形态)触发——常规帧(双锚未命中)在首探 miss 后
      短路,零复探等待/零新截图(三审 C2 成本门控);
    - 两时序形态(首帧命中/复探命中)同判据同路由;仍 miss 才放行备战链。
    OCR 腿对 outer_loop §2.1「优先 area 化」的豁免记录见该文档 0e 行。
    消费点防御(达标臂浮层排除/遭遇 OCR/C1 计数)与本判据分层:本件管
    「路由稳定」,彼件管「路由误判后的发射兜底」,禁合并谓词。
    """
    prep = _prep_anchors_hit(op, screen)
    if _invest_anchor_hit(op, screen) or _invest_ocr_hit(op, screen):
        return True, screen
    if not prep:
        return False, screen   # 常规帧短路:零复探等待/零新截图(三审 C2)
    time.sleep(op.INVEST_REPROBE_WAIT)
    screen = op.screenshot()
    if _invest_anchor_hit(op, screen) or _invest_ocr_hit(op, screen):
        return True, screen
    return False, screen


class _FnResult:
    """零参可调用步骤的结果轻壳(ADR-0584 §2.3 的 0n 适配形,二选一之「轻壳」)。

    ``CwScreenPrep.visit_open_shop`` 返回 ``(ok, detail)`` 元组,与画面 op
    ``execute()`` 的 OperationResult(.success/.status)契约不同;本壳统一读面
    供 ``_dispatch_screen_op`` 判定 outcome。硬边界:visit_open_shop 本体一字
    不动(它同时是显式开店通道的汇合点,改签名会波及 cw_screen_prep)。
    """

    def __init__(self, success: bool, status: str) -> None:
        self.success: bool = success
        self.status: str = status


class CwLoop(SrOperation):
    """货币战争 对局内主循环:反复「备战单轮 + 轮间过渡」直到对局结束 / 超时。

    状态机(每轮截图后按优先级匹配):
    1. 备战阶段(「购买经验」)→ CwScreenPrep 备战单轮(观察→对账→决策→期望态→执行)→ 等战斗;
    2. 「点击空白加速」/「点击空白处继续」→ 点空白(加速战斗 / 关教程叠层);
    3. 「挑战成功」后「继续挑战」→ 点 → 下一轮;
    4. 「投资环境」3 选 1 → 点左牌 + 「确认」;
    5. 「下一步」等前进按钮 → 点。

    naive 策略(买全部 + 填位 deploy);对局从已进入的备战开始跑(开对局由
    ``CwEntryStart`` 负责,本 op 只跑对局内循环)。MAX_ITER 防失控。
    """

    MAX_ITER: ClassVar[int] = 2000  # 整局 3 位面多轮(备战+战斗+多类事件);战斗 round_wait 占大量迭代。
    # 2026-08-04 实跑:500 不够 —— reactive 弱阵战斗慢,plane2 r5 打「蚕食者之影」时 iter 撞 500
    # →「对局循环超时」失败(bot 一直在推进,非逻辑 bug,是迭代预算耗尽)。bump 到 2000(≈66min 预算)。
    # 待优化:MAX_ITER 应只计「动作迭代」(备战/事件/结算),不计战斗 round_wait(战斗长短不该吃预算)。
    # 未知画面常驻兜底钩子(方案 D):连续 N 轮未识别画面 → stop_running 保画面待 AI 建档。
    # 常驻安全网——兜一切未知态,不是点名某态的临时捕获;移除条件 = 该类未知态全部建档,
    # 实际不可达(实现见本类 _handle_unknown_fallback)。
    # 15 轮 ≈ 30s 纯卡(过渡帧 1-2 轮内被上面分支接走,不累计);远 < MAX_ITER。
    UNKNOWN_STOP_THRESHOLD: ClassVar[int] = 15
    #: 未知帧重试退避封顶(秒)。连续未识别帧的重试间隔按 2s 起步每连续一次翻倍,
    #: 封顶本值——旧实现恒 2s 立即重试,战斗特效长动画/未建档画面期每 2s 打一次
    #: 全量截图+OCR 空转(重试无退避缺陷)。阈值触达总时长由 ≈30s 放宽到 ≈2min,
    #: 换取停机钩子触发前画面有充分自愈窗口(若真是过渡帧,长动画期 2s 恒重试
    #: 只烧预算不推进)。
    UNKNOWN_RETRY_BACKOFF_CAP_S: ClassVar[float] = 10.0
    #: P4R:0j「前台无角色」恢复链的验证重部署重试上限(本 run 累计;出战
    #: 真转移后复位)。超限 round_fail 交未知画面兜底链——不再无限 round_wait
    #(1-1 事故 5h 死循环返工)。
    FRONTLESS_REDEPLOY_LIMIT: ClassVar[int] = 2
    #: P4R3:0q 位面过渡误分发型 fail 上限(连续计;0p 接管/过渡成功清零)。
    #: 超限 round_fail 交未知画面兜底链——第五局实锤:boss 简报帧误分发
    #: CwScreenPlaneTransition(「提示未出现」fail)每 2s 无限循环。
    PLANE_MISDISPATCH_LIMIT: ClassVar[int] = 3
    # r119 停滞 watchdog 参数:每 5 iter 采一次指纹(≈5-10s),连续 6 次相同
    # (≈1-2min 同屏)→ 哨兵。合法静止态(结算族)按固定短语豁免,见
    # STALL_EXEMPT_PHRASES;战斗进行期由 BATTLE_WATCH_GRACE_S 宽限窗承管。
    STALL_SNAPSHOT_EVERY: ClassVar[int] = 5
    STALL_N: ClassVar[int] = 6
    #: 停滞豁免固定短语表(T-163 去盲,2026-09-08 实机事故):合法静止态的
    #: **全帧 OCR 固定短语**,非裸子串。旧裸子串表(战斗/胜利/挑战/结算/
    #: 准备/倒计时)被弹窗正文撞车致盲——天赋文本「进入战斗前为自己打造
    #: 装备」含「战斗」、词缀描述含「倒计时/战斗节点」→ 豁免恒中 → 停滞
    #: 计数恒清零,卡死 26 分钟无人报(哨兵 stall_watch.flag 零落盘实证)。
    #: 短语集取自归档结算族 fixture 实测 OCR(货币战争-结算/结算-失败/
    #: 挑战失败 三屏):挑战成功/继续挑战(win)、挑战结束/前往结算(轮败)、
    #: 挑战失败(团灭)。战斗进行期本就零关键词(ADR-0250 局54 实锤:
    #: HUD 词可全程缺位),由宽限窗承管,不入本表——本表只辖「结算/等待
    #: 态合法静止」。新增豁免态须先归档 fixture、从实帧 OCR 取短语,
    #: 禁凭裸词直觉回填(裸词 = T-163 同型致盲面)。
    STALL_EXEMPT_PHRASES: ClassVar[tuple[str, ...]] = (
        '挑战成功', '挑战失败', '挑战结束', '继续挑战', '前往结算',
    )
    #: 战斗窗口 watch 宽限(ADR-0250):出战后合法静止上限。实测战斗 4-5.5min
    #: (P1r9 boss 4min20s/P2r1 遭遇 5min20s),600s 覆盖余量后仍可哨兵真挂死。
    BATTLE_WATCH_GRACE_S: ClassVar[float] = 600.0
    # (收口终局行 TERMINAL_OUTCOME_SOURCE 已随 outcomes 流写入端退役删除
    #  ——删除波 1,用户 2026-09-10 直迁裁定;T-185 末轮补全面随之消亡,
    #  结算真值的现役归宿 = GameState settlement 域 apply_settlement_cover。)
    # (结算链常量族 SETTLE_PANEL_WAIT_S/SETTLE_DEFEAT_LATCH_MIN_T/
    #  RELAUNCH_SETTLE_GRACE_S/BLANK/SETTLEMENT_NEXT 已随 1f/2/3/3b/6 分支
    #  收编 CwScreenBattleWait(W971 05-battle §1),常量随 op 迁移单一源。)
    # ⚖️ PREP_SETTLE_S 备战稳定门已退役(W971 §2.6/03-prep §1):「识别到什么
    # 画面,就进入对应的 op」——半开帧/延迟 overlay 防护替身 = ①逐动作回流程层
    # 确认画面(overlay 弹出当步即见,转入 overlay op)②触发计算式追加等待
    # (03-prep §3 DeployMove 行)③director 环入口清场+自动开店预收探针。
    # 原「按最长动画盲等 3s」的门与其 bookkeeping(_frame_is_prep 族)一并删除。
    # 同批退役:_post_settle_auto_shop 标志位(结算后自动开店判稳收编 director
    # 环入口预收探针 + 准备就绪锚,不再跨分支传标志)。
    #: 环级无进展守卫阈值(架构反思三卡死批防线①,「第 5 局放行硬门」):
    #: 连续 N 个备战环「状态指纹零推进」(F2 单键计数,动作批振荡不再
    #: 穿透计数)→ 存证(截图+flag)→ 出战臂或 stop_running。取代旧备战
    #: stall 留证线(只留证不停机的 state-only 计数)——单一计数单一键,
    #: 不留两套并行;N 沿用旧值 3。三起实机卡死(8-34 分钟人工发现)在
    #: 3 环(≈1 分钟)内自动停机留证。
    #: ADR-0554 修订:触发位先过「备战收益耗尽 → 出战臂」——恒指纹窗口
    #: 合法形态(判据 = prep_exhaustion_launch_eligible)改判出战不属
    #: 执行面卡死;其余形态维持停机留证语义。阈值沿用守卫常量,零新
    #: 拍定值。
    PREP_NO_PROGRESS_ROUNDS: ClassVar[int] = 3

    #: 0e 投资策略浮层分发复探窗口(N5 分发判别稳定化):首探测 miss 且
    #: 备战双锚命中(浮层穿透形态)时,短窗后新截图复探一次。执行层时序
    #: 常量(淡入动画期采样窗),沿 PREP_NO_PROGRESS_ROUNDS 先例,非策略
    #: 数值参数。
    INVEST_REPROBE_WAIT: ClassVar[float] = 0.6

    #: 主循环全部分支判定锚 ``画面名.area名``(分发预检枚举源)。
    #: 运行时画面加载只读 _od_merged.yml;分文件改名后 merged 漏再生时,分支
    #: 检测 get_area→None→AREA_NO_CONFIG 被 is_success 静默吞掉(第三起实机
    #: 卡死根因:选择伙伴遮罩下部署死局 ~8min,日志零线索)。本表在 iter1 对
    #: 全部锚做可解析预检,缺失逐条 log.error(带分支名),把「配置缺失」在
    #: 第一轮就炸到日志面。新增浮层分支须同步登记本表与测试仓序锁矩阵
    #: (test_cw_dispatch_order_matrix:矩阵锁序位,本表锁运行时可解析)。
    DISPATCH_AREA_ANCHORS: ClassVar[tuple[tuple[str, str, str], ...]] = (
        # (分支名, 画面名, 锚 area 名)
        ('0a0 选择装备', '货币战争-选择装备', '标识-选择装备'),
        ('0a0 选择装备副题', '货币战争-选择装备', '标识-请选择1个装备'),
        ('0a 选择伙伴', '货币战争-列车同行', '标识-选择伙伴'),
        ('0a2 策划事件', '货币战争-骇入策划', '标识-我来当策划'),
        ('0a3 命运卜者', '货币战争-命运卜者强化', '标识-命运卜者'),
        ('0a3 命运卜者副题', '货币战争-命运卜者强化', '标识-请选择强化效果'),
        ('0a4 位面详情', '货币战争-位面详情', '标识-位面详情标题'),
        ('0a4 位面详情关闭', '货币战争-位面详情', '按钮-关闭位面详情'),
        ('0b 巨星强化', '货币战争-盛会之星', '标识-盛会之星'),
        ('0b 巨星 step2', '货币战争-盛会之星', '按钮-请选择强化角色'),
        ('0c 遭遇节点', '货币战争-遭遇节点', '标识-遭遇节点'),
        ('0d 未达上限警告', '货币战争-未达上限警告', '标识-未达上限警告'),
        ('0e 投资策略', '货币战争-投资策略', '标识-请选择投资策略'),
        ('0e1 补给阶段', '货币战争-补给', '标识-补给阶段'),
        ('0f 武装箱', '货币战争-武装箱弹窗', '标识-简易武装箱'),
        ('0e2 概率表', '货币战争-商店刷新概率表', '标识-刷新概率表'),
        ('0h 祈愿试炼', '货币战争-祈愿试炼', '标识-祈愿试炼'),
        ('0i 星徽秘典', '货币战争-星徽秘典弹窗', '标识-星徽秘典'),
        ('0k 专家邀请函', '货币战争-备战-专家邀请函', '标识-专家邀请函'),
        ('0t 卡牌详情·购买', '货币战争-商店卡牌详情', '按钮-购买'),
        ('0t 卡牌详情·角色详情', '货币战争-商店卡牌详情', '按钮-角色详情'),
        ('0t 卡牌详情关闭', '货币战争-商店卡牌详情', '按钮-关闭'),
        ('1b 详情·装备推荐', '货币战争-备战-角色详情', '按钮-装备推荐'),
        ('1b 详情·合成公式', '货币战争-备战-角色详情', '装备详情-合成公式'),
        ('0m 策略锁定', '货币战争-备战-策略锁定', '按钮-返回投资策略选择'),
        ('0m 遭遇锁定', '货币战争-备战-遭遇锁定', '按钮-返回遭遇选择'),
        ('0n 开商店·购买经验', '货币战争-备战-开商店', '备战标识-购买经验'),
        ('0n 开商店·备战阶段', '货币战争-备战-开商店', '标识-备战阶段'),
        ('0j 前台无角色', '货币战争-提示-前台无角色', '标识-无角色提示'),
        ('0j 前台无角色确认', '货币战争-提示-前台无角色', '按钮-确认'),
        ('0p BOSS简报', '货币战争-BOSS简报', '标识-强敌来袭'),
        ('0r 位面简报', '货币战争-简报', '标识-本场对局首领'),
        ('0s 投资环境', '货币战争-投资环境', '标识-投资环境'),
        ('1 备战双锚·购买经验', '货币战争-备战', '备战标识-购买经验'),
        ('1 备战双锚·出战', '货币战争-备战', '按钮-出战'),
        ('0n 开商店·收起', '货币战争-备战-开商店', '按钮-收起'),
        # T-121 三处硬坐标 area 化(ADR-0584 §6.1:矩形中心 = 原 Point,
        # 处理锚随批登记,先例 = 0a4 判定/处理锚同行在表)
        ('0e2 概率表关闭', '货币战争-商店刷新概率表', '按钮-关闭概率表'),
        ('0e3 道具详情关闭', '货币战争-道具详情弹窗', '按钮-关闭'),
        ('0g 简易装备首件', '货币战争-备战', '按钮-简易装备首件'),
    )

    def _dispatch_anchor_precheck(self) -> None:
        """iter1 分发锚可解析预检(防 merged 漏再生漂移):任一锚不在运行时 screen_info
        (merged)→ log.error 逐条点名。不中止运行(缺锚分支退化为「该画面
        不识别」,其余分支照常推进;中止会造成无对局可跑)。异常吞掉不阻塞
        (预检失败不能比事故本身更贵)。"""
        try:
            missing: list[str] = []
            for branch, screen, area in CwLoop.DISPATCH_AREA_ANCHORS:
                if self.ctx.screen_loader.get_area(screen, area) is None:
                    missing.append(f'{branch}: {screen}.{area}')
            if missing:
                log.error('[cw!][loop] 分发锚预检:%d 个锚不在运行时 screen_info'
                          '(画面改名后 merged 漏再生?)→ 对应分支每帧静默跳过'
                          '(历史事故形态):%s', len(missing), '; '.join(missing))
        except Exception as e:   # noqa: BLE001  预检失败不阻塞对局
            log.debug('[cw-loop] 分发锚预检失败(不阻塞): %s', e)

    def __init__(self, ctx: SrContext, max_rounds: int | None = None):
        SrOperation.__init__(self, ctx, op_name='货币战争-对局循环')
        self._iter: int = 0
        # 迁移审计 w75(git 历史)(ADR-0335):run 收口——中止/卡死/停机局不走 3c 回大厅
        # → 收口位永不置(哨兵 [RUNS-GAP] 连报史实,r363)。机制:正常终局(3c)
        # 收口后置本标记;``after_operation_done`` 收口钩子(成功/失败/停止
        # 全路径必达)检查未收口 → 补收口。删除波 1 后收口 = close_run
        # (零落盘,置跨局 run_id 重铸位),runs 行写入已退役。
        self._summary_written: bool = False
        # 可控轮数(单/多轮验证 + 采样本):跑完 max_rounds 轮后,停在下一轮备战屏(analyze board/star)。
        # 轮锚点 = 分支3「挑战成功」结算(每打赢 1 轮 +1);停点 = 分支1 备战 gate(rounds_done≥max → 停)。
        # None = 现行跑到对局结束/超时(向后兼容)。app 从 config.max_rounds 透传;run_operation 可直传。
        self._max_rounds: int | None = max_rounds
        # (轮计数 _rounds_done 已随结算链收编 CwScreenBattleWait → SettlementState
        #  .rounds_done(W971 05-battle §1);本类经 self._settle.rounds_done 读。)
        # r119 停滞 watchdog 状态:画面指纹采样(OCR 关键词 frozenset 哈希)。
        # 每 STALL_SNAPSHOT_EVERY iter 采样一次;连续 STALL_N 次相同 → 哨兵。
        self._stall_last_fp: int | None = None
        self._stall_count: int = 0
        self._stall_flag_written: bool = False
        # 战斗窗口宽限计时起点(monotonic;出战/战斗帧双入口赋值)。接管局首帧
        # 可直接落战斗窗口(先于任何出战),必须在此初始化——否则 1213 行
        # ``self._settle.battle_ts = self._battle_ts`` 直接访问未初始化属性
        # (第八局接管实证:stop 间隙游戏自走进战斗,再起局即崩循环)。
        self._battle_ts: float | None = None
        # B4(ADR-0170):跨局分配器实例(进程级单例——后验跨局累积;失败安全:任何异常静默禁用)
        self._allocator = _get_or_init_allocator(self.ctx)
        # 本局遥测 run_id(旧流采集面已随删除波 1 退役;现役消费 = journal 行归属)。
        # ADR-0588:铸造单点已前移到入口链(简报锚/投资屏分支,先于任何开局
        # 遥测行)——此处改「认领」:新局路径同容器 open run 已在,不重铸
        # (一段一 id);接管局/run_operation/恢复路径上 run 已收口(_RUN_CLOSED)
        # → 按 gate 重铸,等价旧「每次 loop 执行新 run_id」语义。
        # difficulty:ctx.cw_selected_difficulty(CwEntryStart 难度确认屏读存;此时**尚未**被
        # 下方取走 —— 取走在 cw_match new 之后,此处先读传 telemetry,review 半接线「difficulty 恒空」修复)。
        _diff_for_telemetry = self.ctx.cw_selected_difficulty or ''
        state.ensure_run_started(match=self.ctx.cw_match,
                                 difficulty=_diff_for_telemetry)
        # R4-1(迁移审计 w52(git 历史) §3.1):recovered 三字段(_run_start_ts/_first_settlement_seen/
        # _is_new_match)+ match 建立/续用块 + 每局缓存清空,已迁 handle_init——
        # 框架语义:execute() 每次开头 _init_before_execute 调 handle_init,
        # __init__ 不随 execute 重入重跑(原写在 __init__ → 重入不重置,R4 审查
        # 报告检查项 4:「漏标不误标」保守退化,此处根治)。
        # _is_new_match 与 match 建立块必须**同块迁移**:_is_new_match 的求值
        # (ctx.cw_match is None)在「match 尚未建立」时点才有意义——只迁三字段
        # 会让首次 execute 重判时 cw_match 恒已存在(_is_new_match 恒 False,
        # 新局标记/残留屏判定双双失活)。整块迁移后:首次 execute 时序与
        # 原 __init__ 等价(本方法在首个节点运行前执行);execute 重入时重判
        # ——cw_match 若已建立则不再当新局(保守方向:漏标不误标,R4 已证)。

    def handle_init(self) -> None:
        """run 级状态初始化(框架钩子:每次 execute() 开头由
        ``_init_before_execute`` 调用;见类注 R4-1 迁移说明)。"""
        # 迁移审计 w28(git 历史) 缺陷①:run 启动时刻 + 首见结算屏标记(relaunch 残留结算判据)
        # ——已随结算链收编 CwScreenBattleWait(SettlementState,W971 05-battle §1):
        # run 启动时刻/新局标记在下方 _is_new_match 求值后注入。
        # 每局清空 plane/round last-known-good(防跨局复用上局值;task#24)
        reset_phase_round_cache()
        # SrOperation 还没 last_screenshot(截图由 node runner 进 @operation_node 时给)→ 不能 read_game_state;
        # 新局初值经 create_session 唯一冷建口承载(ADR-0583;见 _iter==1 分支)。跨步状态进 strategy_state_of(session).target_comp
        # (替代旧 BuyShopCards._target_comp class-attr hack,语义等价:每局新建已是现行为)。
        # 续跑支持(手动逐轮验证):cw_match 已存在(上轮 RunLoop 留下)→ 延用,不 new;否则 new(整局开始)。
        # 手动逐轮(max_rounds=1 反复 run_operation)靠此跨 run 延续 match state(target 稳定不每轮重选振荡)。
        # 停 app / 手停 / 重启 server 后 cw_match 清(None)→ 下次 run 重新 new(新局)。
        self._is_new_match: bool = self.ctx.cw_match is None
        # 战斗窗口驻留闩:出战成功置位 → 后续帧委托 CwScreenBattleWait 直到其
        # 完成(白名单/终局/bail);帧锚激活(接管局/残留屏)为第二入口。
        self._battle_wait_active: bool = False
        # 迁移审计 w62(git 历史) 件1(ADR-0329):恢复局(locked-resume)检测状态。
        # 候选 = 新 match(无本局记录),首个备战相位 round>1 时探针裁决;续跑恒 False。
        self._cw_resume_candidate: bool = self._is_new_match
        self._cw_locked_resume: bool = False   # 锁定确认(探针零响应)→ 直接出战
        self._cw_locked_round: int = 0         # 锁定确认时的轮次(遥测/日志锚)
        # 「返回投资策略选择」按钮出现计数(症状报警用:出现=上游策略屏处理失败)
        self._cw_back_btn_count: int = 0
        # (策略失活早停状态对 _cw_strategy_dead_streak/_cw_dead_prev_key 已随
        #  decisions 流写入端退役删除——删除波 1:数据源(决策行)停写后
        #  新局恒「零心跳行」,检查保留会误杀每一局;消费面与离线检查网
        #  随数据源同批退役,存量语料判读走判读 CLI 新账视图/按局档案。)
        # 备战收益耗尽出战臂(ADR-0554)状态:上一备战环 success(判据输入,
        # CwScreenPrep 返回后写)+ 发射失败连击(与达标臂 _cw_readiness_fail_n
        # 同构,达 3 放弃短路回落守卫停机)。
        self._prep_last_success: bool | None = None
        self._cw_exhaust_fail_n: int = 0
        self._cw_config: CurrencyWarConfig = CurrencyWarConfig(self.ctx.current_instance_idx)
        # 战斗/结算链状态机 + CwScreenBattleWait 实例(W971 05-battle §1 收编):
        # 结算读点/点继续/败局链/终局分叉的状态随 op 迁移,本 loop 只持引用
        # (3c 收口/summary 读真值)。op 实例跨场复用(状态机生命周期 = 局级;
        # 每 execute 重handle_init → run 启动时刻/新局标记随之刷新,与原
        # _run_start_ts/_first_settlement_seen 的 run 级语义一致)。
        self._settle = SettlementState(
            run_start_ts=time.monotonic(), is_new_match=self._is_new_match)
        self._battle_wait = CwScreenBattleWait(self.ctx, self._settle, self._cw_config)
        if self._is_new_match:
            # match 建立(兜底分支):正常路径已由 CwEntryStart 在
            # 进对局时经 establish_new_match 前移建立(W971 §2.1,CwScreenBriefing
            # 直写 session 的时序前提);此处覆盖「绕过入口链直跑 loop」
            # 的场景(如 run_operation 单跑),同一 helper 无逻辑分叉。
            from sr_od.application.currency_war.strategies.impl.cw_strategy_manager import (
                establish_new_match,
            )
            establish_new_match(self.ctx, self._cw_config)
            # (r339b 板深快照注册 set_ctx_match 已随旧流快照消费方退役删除
            #  ——删除波 1:槽唯一消费方 = outcomes/decisions 行的板深/session
            #  快照,写入端退役后槽体一并删除。)
        # 入口链 ctx 中转吸收(P3b 收缩:仅剩职级难度——难度确认屏读存
        # ctx.cw_selected_difficulty,非简报信箱域)。简报词缀/boss/敌人难度
        # 的 ctx 信箱已退役(W971 §2.1「消灭 ctx 信箱」P3 批口径):唯一写点 =
        # CwScreenBriefing 直写 session,本段不再吸收。
        self._absorb_selected_difficulty(self.ctx.cw_match.session)
        # else 续跑:延用 self.ctx.cw_match(上轮留下),仅刷新 _cw_config(用户可能改 max_rounds 等运行时配置)

    def _absorb_selected_difficulty(self, session: StrategySession) -> None:
        """入口链职级难度 ctx 中转 → session(自原 _absorb_ctx_mailbox 收缩)。

        迁移自原 handle_init 新局分支(行为不变);简报三字段吸收段已随
        ctx 信箱退役删除(W971 §2.1 P3 批口径,见调用处注释)。
        """
        # 本局职级(CwEntryStart 难度确认屏读存 ctx.cw_selected_difficulty)→ session.selected_difficulty
        # → 策略层填 state → effective_hp_threshold D-32(3.5.1 接线)
        if self.ctx.cw_selected_difficulty:
            session.selected_difficulty = self.ctx.cw_selected_difficulty
            self.ctx.cw_selected_difficulty = None  # 取走清空(防跨局复用)

    def _snap(self, tag: str) -> None:
        """初期接触玩法:关键决策点存 debug 截图 + 全量 OCR 日志(定位问题用,验证后去掉)。

        见 od-dev-gameplay-automation「开发时预留日志 + 截图开关 / 信息密度论」:让一次
        实跑暴露尽量多的问题(选人选项长啥样 / OCR 误读 / 坐标漂移 / 漏事件),而非每次只测
        一种情况。截图存 ``.debug/images/``(``save_screenshot``),日志带当前帧全量 OCR 文本
        (选人/事件选项 OCR 现无策略评估 → 先靠 snap 看清每局都 offered 什么,再建评估)。
        非关键路径:try 兜底,debug 失败不影响对局推进。
        """
        try:
            ocr_map = self.ctx.ocr_service.get_ocr_result_map(
                image=self.last_screenshot, rect=None, color_range=None, crop_first=False,
            )
            texts = [k for k, mrl in ocr_map.items() if mrl.max is not None]
            path = self.save_screenshot(prefix=f'cw_{tag}')
            log.info(f'[cw-snap] {tag} iter={self._iter} shot={path} ocr={texts[:15]}')
        except Exception as e:  # noqa: BLE001  debug 路径,失败不阻塞对局
            log.warning(f'[cw-snap] {tag} iter={self._iter} failed: {e}')

    @staticmethod
    def _watch_in_battle_grace(battle_ts: float | None, now: float) -> bool:
        """战斗窗口宽限判定(纯函数,ADR-0250):``battle_ts`` 非空且未超
        ``BATTLE_WATCH_GRACE_S`` → True(watch 不计数)。None/超时 → False。"""
        return (battle_ts is not None
                and now - battle_ts < CwLoop.BATTLE_WATCH_GRACE_S)

    @staticmethod
    def _stall_exempt(texts: frozenset[str]) -> bool:
        """停滞豁免判据(T-163 去盲):全帧 OCR 含任一合法静止态固定短语。

        短语集与致盲机理见 ``STALL_EXEMPT_PHRASES`` 注;独立成纯函数供
        测试仓锁「弹窗正文类文本不豁免」(裸子串回归 = 26min 致盲复发面)。
        """
        return any(p in t for t in texts
                   for p in CwLoop.STALL_EXEMPT_PHRASES)

    def _stall_watch_tick(self, screen) -> None:
        """r119 停滞 watchdog:同屏指纹连续相同 → 哨兵(不停机,日志+flag 双通道)。

        指纹 = OCR 关键词 frozenset 哈希(5 iter 采一次,~5-10s 粒度)。战斗/
        结算/等待态按固定短语豁免(合法静止,STALL_EXEMPT_PHRASES;战斗
        进行期归下方宽限窗)。触发 = 写 stall_watch.flag
        (含处理指引)+ [cw!] 日志一次;画面变化后自动清计数(flag 留给 AI 巡检
        后删)。设计:采集哨兵非停机(bot 可能只是慢,停机代价>等待代价;
        od-dev-stop-hooks 采集/停机分流判据)。
        """
        if self._iter % CwLoop.STALL_SNAPSHOT_EVERY != 0:
            return
        # ADR-0250(战斗窗口宽限,局54 哨兵误报复盘):出战后的战斗进行期是
        # 合法静止(实测 4-5.5min > watch 阈值 ≈2.5min),且战斗 HUD 关键词
        # 可全程不含豁免词(局54 实锤:4 词缀+3 首领+难度常驻简报信息面板,
        # 「决战在即」是词缀名非战斗标语)→ 关键词豁免兜不住,误报稀释真哨兵
        # 信号。窗口内不计数;宽限过 → 恢复正常判定(出战卡死类真挂死仍可触发)。
        # 开窗=备战环出口(出战);关窗=结算观测回路(battle_wait)/备战分支再入。
        if self._watch_in_battle_grace(
                getattr(self, '_battle_ts', None), time.monotonic()):
            self._stall_count = 0
            self._stall_last_fp = None
            return
        if getattr(self, '_battle_ts', None) is not None:
            self._battle_ts = None   # 宽限已过 → 恢复正常停滞判定
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        texts = frozenset(k for k, mrl in ocr_map.items() if mrl.max is not None)
        # 结算/等待态豁免(合法静止;固定短语判据,T-163 去盲——旧裸子串
        # 「战斗」被弹窗正文撞车致盲 26min,机理见 STALL_EXEMPT_PHRASES 注)
        if self._stall_exempt(texts):
            self._stall_count = 0
            self._stall_last_fp = None
            return
        fp = hash(texts)
        if fp == self._stall_last_fp:
            self._stall_count += 1
        else:
            self._stall_count = 0
            self._stall_last_fp = fp
            self._stall_flag_written = False   # 画面动了 → 哨兵可再次触发(新一轮停滞)
        if self._stall_count >= CwLoop.STALL_N and not self._stall_flag_written:
            _shot = self.save_screenshot(prefix='cw_stall')
            _sentinel = (get_project_root() / '.debug' / 'temp'
                         / 'currency_war' / 'stall_watch.flag')
            _sentinel.parent.mkdir(parents=True, exist_ok=True)
            _sentinel.write_text(
                f'停滞 watchdog:iter={self._iter} 同屏指纹连续 {self._stall_count} 次'
                f'(≈{self._stall_count * CwLoop.STALL_SNAPSHOT_EVERY} iter)\n'
                f'OCR 关键词: {sorted(texts)[:12]}\n'
                f'处理流程:\n'
                f'1. 看关键词/截图:疑似事件 overlay(未建档 handler)→ 按\n'
                f'   od-dev-screen-onboarding 建档 + cw_loop 0x 分支加 handler;\n'
                f'2. 处理完删本 flag。bot 未停机(可能只是慢),处理完可继续跑。\n'
                f'shot={_shot}', encoding='utf-8')
            log.warning('[cw!][watch] 停滞哨兵:同屏 %s 次(≈%s iter)关键词=%s '
                        'shot=%s —— 疑似未处理 overlay/操作循环,详见 stall_watch.flag',
                        self._stall_count,
                        self._stall_count * CwLoop.STALL_SNAPSHOT_EVERY,
                        sorted(texts)[:8], _shot)
            self._stall_flag_written = True   # 只写一次,画面变化后可重置重写

    def _clear_bail_count(self, reason: str) -> None:
        """外环 handler 成功消化某 overlay 后清其 bail 计数(M11 误停机修复)。

        Director 对同一 overlay 的多次 bail 若都被外环**成功处理**(巨星节点每场触发一次,连胜连开),
        是合法流转而非 ping-pong —— 不清零会在第 3 次合法出现时误升级停机(M11 2-2 巨星实锤)。
        """
        _m = self.ctx.cw_match
        if _m is not None and getattr(_m.exec_state, 'bail_reason_counts', None):
            _m.exec_state.bail_reason_counts.pop(reason, None)

    def _cw4_counters_snapshot(self, session: Any) -> dict[str, int] | None:
        """策略行为观测计数局终聚合快照(R5 W4 键收编载体,r5-migration-plan.md §2 W4)。

        旧计数流写端已随 W4 流删退役(流文件名一并注销);局终级全键
        聚合现归宿 = 局终域行载荷 ``MatchFinal.cw4_counters``(两收口
        路径在 ``write_match_final`` 调用点现读传入)。取值 = 策略 state
        容器(``strategy_state_of(session).cw4_counters``)的**浅拷贝**
        (快照语义,防收口后策略侧续写串账);session 缺/容器未初始化
        (策略未进 mandate_v1)→ None = 诚实缺省,与「零计数空 dict」
        可辨。
        """
        if session is None:
            return None
        counters = getattr(strategy_state_of(session), 'cw4_counters', None)
        return dict(counters) if isinstance(counters, dict) else None

    # (收口终局行族 _run_has_outcome_at/_write_terminal_outcome_row 已随
    #  outcomes 流写入端退役删除——删除波 1,T-185 末轮补全面随流消亡;
    #  结算真值现役归宿 = GameState settlement 域 apply_settlement_cover,
    #  局终收口形态归宿 = 局终域 match_final 行,写点接线归后续批。)

    def _op_journal_pos(self) -> tuple[int, int]:
        """op 行位置键(ADR-0579):最后已知 (plane, round),缺省 (0, 0)。"""
        return _op_journal_pos_of(self.ctx)

    def _note_branch_screen(self, screen_name: str) -> None:
        """开局链分支标识 → 画面上下域(R2 开局链写点;弹窗腿守卫集
        prev_branch 供给,设计 v3.1 §3.4.1)。

        - 只写分支标识,**不碰分派逻辑**——分支判定/序位/守卫域零改动,
          本方法在分支命中点旁路调用(最小侵入面);
        - 写入口 = GameState :meth:`observe_screen_context` 唯一写口
          (域准入:上下文域 ①obs 家族;分支命中 = 锚级画面识别,mode=
          read,actor = 本外循环 op 类名);旧 current 转 prev 成对同组,
          下一次分派观察(漏斗/下一分支)即弹窗腿守卫集的 prev 输入;
        - 分支级标识变体:「等待 1-1」无独立画面建档,token 同
          ``BATTLE_WAIT_CONTEXT`` 申报(kernel 常量注释;R3 判定方案
          §3.3 规则二② 开局链五成员之一);
        - journal 常开(R5 W1 影子闸折叠,ADR-0634)写入无条件;无局跳过;
          best-effort 不阻塞分派。
        """
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                board_state_from_ctx,
            )
            bs = board_state_from_ctx(self.ctx)
            if bs is None:
                return
            bs.observe_screen_context(
                screen_name,
                sig=ChannelSig(family='obs', actor='CwLoop',
                               screen=screen_name, mode='read'))
        except Exception as e:  # noqa: BLE001  上下文写入不阻塞分派
            log.debug(f'[cw-loop] 分支标识写入跳过: {e}')

    def _mark_session_resumed(self) -> None:
        """恢复局旗标 → session 执行态(D2 live 接线;R1 缺口承接,R3 判定
        方案规则六弹窗腿禁用供给面)。

        写点 = 恢复检测两确认点(战斗帧恢复检测/备战帧 resume_candidate
        确认);读端 = 观察汇聚漏斗(经 observe_screen_context(resumed=…)
        进派生规则,恢复局弹窗腿 hist 空时禁用不猜)。best-effort 不阻塞
        分派;session 缺(局外/桩)静默跳过。
        """
        try:
            match = getattr(self.ctx, 'cw_match', None)
            session = getattr(match, 'session', None) if match is not None \
                else None
            if session is None:
                return
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                exec_state_of,
            )
            exec_state_of(session).cw_resumed_match = True
        except Exception as e:  # noqa: BLE001  旗标写入不阻塞分派
            log.debug(f'[cw-loop] 恢复局旗标写入跳过: {e}')

    def _dispatch_screen_op(
        self,
        op: Any,
        *,
        journal_name: str,
        frame_tag: str | None,
        wait: float,
        on_fail_retry: bool = False,
        on_result: Callable[[bool, Any], OperationRoundResult | None] | None = None,
    ) -> OperationRoundResult:
        """画面分支统一 dispatch 包装(ADR-0584 §2.3,外循环唯一新增结构)。

        统一面 = 留证帧 + op_journal enter/exit + 结果映射;分支特有守卫钩子
        走 ``on_result`` 调用点邻接闭包,**禁塞进本包装本体**(包装知晓分支
        语义 = 分工倒退)。判定锚/排他/序位/守卫域仍全部在外循环分支体。

        :param op: 画面 op 实例(有 ``execute()``)或零参可调用——可调用返回
            ``(ok, detail)`` 元组时经 ``_FnResult`` 适配(0n 的 visit_open_shop
            形),返回 OperationRoundResult 时链形透传(0j/3c 恢复链/收口链,
            轮次结果即分支出口,outcome = 非 FAIL/RETRY 即 ok)。
        :param journal_name: op_journal 行的 op 名(复盘「分发了谁」直读键)
        :param frame_tag: 决策帧 tag;None = 跳过落帧(留证面零扩的可退选项)
        :param wait: 默认映射的 round_wait 等待秒数
        :param on_fail_retry: True = op 失败映射 loop 级 round_retry(与既有
            分支内联 round_retry 消费同一 retry 池);False = 失败也 round_wait
        :param on_result: 守卫钩子回调 ``(ok, res) -> round | None``;返回
            None = 走默认映射,返回 round 对象 = 覆盖默认返回(如 0q 超限
            round_fail)。调用点 = execute 之后、record_op_exit 之前。
        :return: 分支的轮次结果

        异常安全(ADR-0584 §5.2):``op`` 体或 ``on_result`` 抛异常时,补发
        outcome='error' 的 exit 行后原样上抛——异常语义归节点级重试链不变,
        孤儿 enter 语义回归「进程中断专属」;结果映射(round_wait/retry)
        在 exit 之后,映射段异常不产生双 exit。
        """
        if frame_tag is not None:
            save_decision_frame(self, frame_tag, self.last_screenshot)
        token = record_op_enter(journal_name, *self._op_journal_pos())
        try:
            if hasattr(op, 'execute'):
                res = op.execute()
            else:
                raw = op()
                res = (_FnResult(bool(raw[0]), str(raw[1] if len(raw) > 1 else ''))
                       if isinstance(raw, tuple) else raw)
            if isinstance(res, OperationRoundResult):
                # 链形(0j/3c):轮次结果即分支出口,包装只补 journal/帧,不改分流。
                ok = res.result not in (OperationRoundResultEnum.FAIL,
                                        OperationRoundResultEnum.RETRY)
            else:
                ok = res is not None and getattr(res, 'success', False)
            hook_ret = on_result(ok, res) if on_result is not None else None
            record_op_exit(token, outcome='ok' if ok else 'fail')
        except Exception as e:   # noqa: BLE001  出口行补发后原样上抛(异常
        # 处理归节点级重试链,包装只保 journal 配对;ADR-0584 §5.2)。
            record_op_exit(token, outcome='error', detail=str(e)[:120])
            raise
        if isinstance(res, OperationRoundResult):
            return res if hook_ret is None else hook_ret
        if hook_ret is not None:
            return hook_ret
        if on_fail_retry and not ok:
            return self.round_retry(wait=wait)
        return self.round_wait(wait=wait)


    def _last_true_hp(self, fallback_hp: int | None) -> int | None:
        """收口 final_hp 真值源(r3 live 修):结算链内存轨迹的末条真 hp。

        hp 轨迹由 CwScreenBattleWait 结算链维持
        (SettlementState.last_outcome_hp,W971 05-battle §1 收编);
        死局回大厅 fallback 兜底常为 100(hp_readable=False 污染读面的
        旧码行;容器 hp 由结算覆盖/观察漏斗质量门写入,兜底面不复现)。
        """
        hp = self._settle.last_outcome_hp
        return hp if hp is not None else fallback_hp

    def after_operation_done(self, result: '_OperationResult') -> None:
        """局终 runs summary 收口(迁移审计 w75(git 历史)/ADR-0335;治本 r363 死码)。

        r363 把 stop 兜底放在 loop() 顶 —— 但 ``operation.execute()`` 每轮前
        (operation.py:408)先查 ``is_context_stop``,stop 到达后 ``loop()`` 不再被调,
        loop 顶检查几乎永不触发(MCP stop 四局 [RUNS-GAP] 哨兵连报实锤)。
        本钩子在 ``execute()`` 全路径收口(after_operation_done 对成功/失败/停止
        必达,operation.py:492):未写 summary 的对局在此补写,hp/plane/round
        取最后已知值(session 容器单例;hp 走 ``_last_true_hp`` 防兜底值毒化),
        result='stopped'(停止) / 'abandoned'(超时/异常退出)。
        """
        super().after_operation_done(result)
        self._write_terminal_summary_if_needed()

    # (GameState 局终归档写点 _archive_board_state 已随 R5 W7 退役删除
    #  ——补遗流 board_state_archive 写面下线,能力归宿 W2 已落位
    #  (bs_prov=快照来源注记/局终速查=match_final 行,retirement.md §2);
    #  存量数据文件归档只读(不删不写,裸读考古,r5-migration-plan §4-6)。)

    def _write_terminal_summary_if_needed(self) -> None:
        """局终/中止收口(幂等:_summary_written 守卫)。

        正常终局(3c 回大厅)已收口 → 跳过。停止/超时/异常 → 取最后已知值补收口。
        P4R4 假局守卫语义修正(run_20260903_004418 超时 fail / run_20260903_
        204908 stop 两实例 runs 缺行定位):旧守卫「零 outcome = 假局不写」
        把**部署死循环等零结算阶段的真局**也吞了(2 小时 400 轮循环、备战
        观察全程活动,却因无战斗/补给结算行被当成开局失败)。
        新判定:**「从未观察到对局态」才算假局**(容器节点未观察 ∧ 零
        outcome = 开局即失败,镜像 3c 守卫;last_state 缺失判定随链退役
        换源 = ``bs.node.value is None``,观察漏斗每帧刷新节点);只要
        观察过对局态或有过任一结算行,就是真局,必走收口。

        删除波 1:runs summary 写行与 outcomes 收口终局行(T-185)随旧流
        写入端退役;W4 流删:cw4 计数流写面亦退役,局终级全键聚合改由
        match_final 载荷携带(上方写点 cw4_counters=)。W7:补遗流
        board_state_archive 写点(_archive_board_state)退役,存量
        归档只读(不删不写,裸读考古;r5-migration-plan §4-6)。本收口现役
        面 = match_final 收口行(含计数聚合)+ run 收口位(跨局 run_id
        重铸承接口)+ 档案装配。
        """
        if self._summary_written:
            return
        _m = self.ctx.cw_match
        _sess = getattr(_m, 'session', None) if _m is not None else None
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
            plane_of,
            round_num_of,
            write_match_final,
        )
        _bs = board_state_of(_sess) if _sess is not None else None
        _observed = _bs is not None and _bs.node.value is not None
        _has_outcome = not (self._settle.last_outcome_hp is None
                            and self._settle.rounds_done == 0)
        if not _observed and not _has_outcome:
            return   # 真假局:从未观察到对局态也无结算痕迹(开局即失败)
        try:
            _stopped = bool(getattr(self.ctx.run_context, 'is_context_stop', False))
            _bs_hp = (_bs.hp.value if _bs is not None else None)
            _final_hp = self._last_true_hp(_bs_hp if _bs_hp is not None else 0)
            # match_final 局终收口行(W3 在线接线,非正常终局形态;判定序
            # 停止>败局>plane==3>abnormal 与 close_run result 同源;写口
            # 段内幂等 G12,best-effort;先于 close_run 落局时间窗)。
            try:
                from sr_od.application.currency_war.obs.cw_observation import (
                    resolve_final_type,
                )
                _mf_type = resolve_final_type(
                    stop_requested=_stopped,
                    saw_defeat=self._settle.saw_defeat_settlement,
                    plane_reached=(plane_of(_bs) if _observed else 1),
                    rounds_played=_has_outcome)
                if _bs is not None and _mf_type is not None:
                    write_match_final(
                        _bs, final_type=_mf_type,
                        plane=(plane_of(_bs) if _observed else 1),
                        round_num=(round_num_of(_bs) if _observed else 1),
                        hp=(int(_final_hp) if _final_hp else None),
                        gold=(_bs.gold.value if _observed else None),
                        streak=(_bs.streak.value if _observed else None),
                        backfilled=(_mf_type == 'abnormal'),
                        # 策略行为观测计数局终聚合(R5 W4 键收编载体;
                        # 收口时点现读快照,先于 close_run,聚合随时点真值)。
                        cw4_counters=self._cw4_counters_snapshot(_sess),
                        note=('online:w75_stopped' if _stopped
                              else 'online:w75_abandoned'))
            except Exception as e:   # noqa: BLE001  观测旁路,不阻塞收口
                log.warning('[cw][loop] match_final 收口行写入失败(不阻塞): %s', e)
            state.close_run(
                result='stopped' if _stopped else 'abandoned',
                plane_reached=plane_of(_bs) if _observed else 1,
                rounds_survived=round_num_of(_bs) if _observed else 1,
                final_hp=int(_final_hp or 0),
                notes=('stopped:operation 收口(W75)' if _stopped
                       else 'abandoned:operation 异常收口(W75)'))
            self._summary_written = True
            log.info('[cw][loop] 局终 summary 收口:%s p%s-r%s hp=%s',
                     'stopped' if _stopped else 'abandoned',
                     plane_of(_bs) if _observed else 1,
                     round_num_of(_bs) if _observed else 1, _final_hp)
            # 按局存档装配随补写收口(P4R4:非正常终局此前只在 3c 装配,
            # 补写的 runs 行没有装配机会 → 对局档案缺该局;失败不阻塞)。
            try:
                from sr_od.application.currency_war.telemetry import match_archive
                match_archive.assemble_pending(
                    state.get_recorder().replay_dir)
            except Exception as e:   # noqa: BLE001  观测旁路,best-effort
                log.warning('[cw][loop] 局终装配失败(不阻塞): %s', e)
        except Exception as e:   # noqa: BLE001  遥测 best-effort,不阻塞退出
            log.warning('[cw][loop] 局终 summary 收口失败(不阻塞): %s', e)


    # (补给合成 outcome 行 _record_supply_outcome 已随 outcomes 流写入端
    #  退役删除——删除波 1;补给节点完成事实的现役归宿 = 快照行自带域
    #  (journal),选择快照暂存槽 set_last_supply_pick 同批退役。)

    @operation_node(name='对局循环', is_start_node=True, node_max_retry_times=400)
    def loop(self) -> OperationRoundResult:
        self._iter += 1
        if self._iter > CwLoop.MAX_ITER:
            return self.round_fail(status='对局循环超时')
        # 迁移审计 w75(git 历史)(ADR-0335):stop 路径 runs summary 收口已从 loop 顶迁到
        # ``after_operation_done`` —— r363 在 loop() 顶检查 is_context_stop,
        # 但 operation.execute() 每轮前(operation.py:408)先查 stop,stop 到达后
        # loop() 不再被调 → 原检查几乎永不触发(MCP stop 四局 [RUNS-GAP] 实锤)。
        # 收口钩子对成功/失败/停止全路径必达(operation.py:492),见类注。
        screen = self.last_screenshot

        # iter1 分发锚可解析预检:配置缺失第一轮炸到日志面,
        # 不等卡死 8 分钟后再排障。
        if self._iter == 1:
            self._dispatch_anchor_precheck()

        # r119 停滞 watchdog(用户 2026-08-21 纠偏「卡 30min 没发现」):
        # 局29 银狼 41min/局32 命运卜者 30min/局33 祈愿崩 553 iter——轮询监控
        # 只看进度摘要,卡死形态(同屏不动/空转)要跨采样对比才可见。本钩子
        # 让 bot 自己检测:**每 STALL_SNAPSHOT_EVERY 次迭代采样一次画面指纹
        # (OCR 关键词集合的哈希),连续 STALL_N 次指纹相同且非战斗/结算态
        # → 写 stall_watch.flag 哨兵**(AI 下次巡检/交互第一时间可见,处理
        # 流程写在 flag 里)。不停机(bot 可能只是慢),哨兵+日志双通道。
        try:
            self._stall_watch_tick(screen)
        except Exception as _e:   # noqa: BLE001  watchdog 失败不阻塞
            log.debug('[cw-watch] 停滞检测失败(不阻塞): %s', _e)

        # 窗口焦点防线(loop 级,失焦僵尸根治):每 10 迭代主动验窗口焦点,失焦即激活。
        # 实证依据:窗口后台化时输入静默丢/截图正常 → 环僵尸;click/drag 点位守卫
        # 只护单操作,本防线兜全类(未覆盖操作/未来新动作)。best-effort。
        if self._iter % 10 == 0:
            import contextlib
            with contextlib.suppress(Exception):
                _gw = self.ctx.controller.game_win
                if not _gw.is_win_active:
                    log.warning('[cw!][loop] 窗口失焦(输入静默丢风险)→ 主动激活')
                    _gw.active()

        # 尽力而为 read_game_state(默认实现不读);**不做 hp 覆盖** —— hp 覆盖归观察终饰/策略器内化刷新(ADR-0583)。
        if self._iter == 1 and self._is_new_match:
            # ADR-0462:消费面只有 plane/round(恢复对局检测)。
            # 生命周期钩子已随 ADR-0583 收编删除:on_match_start 的冷建与
            # live 初值(v3_phase='FORM')由 create_session 唯一冷建口承载
            #(establish_new_match 进对局前移点/防御路径/回放三处同源)。
            # → battle/过渡帧最小读(仅位面轮次,其余字段该帧无备战可读)。
            _st0 = read_game_state(self.ctx, screen, phase='battle_or_transit')
            # r25 恢复对局标记(telemetry):bot 侧新 match 但游戏已在中局(首读 round>1
            # = 上局残局;第十/十一局三次数据归属混乱实证)。只标不改行为。
            if _st0.round_num > 1 or _st0.plane > 1:
                # A18(hook审计退役批(ADR-0466/0467/0469)):数据归属标记,只标不改行为 → [cw] 非 [cw!]
                log.warning('[cw][loop] 恢复对局检测:新 match 但游戏在 P%s-r%s(上局残局,'
                            '本 run_id 数据含残局段)', _st0.plane, _st0.round_num)
                self._mark_session_resumed()   # D2:恢复局旗标(弹窗腿禁用供给面)
                # (resumed_match 外生行已随 exogenous 流写入端退役删除——删除波 1;
                #  恢复局形态现役证据 = 弹窗腿禁用旗标 + journal 派生行段界。)
            # 接管局补采(boss+词缀)挂点 = 干净备战观察(W971 §2.1,CwScreenPrep
            # 环入口 gate 后稳定帧执行;稳定门退役后由备战观察承担)。

        # 「返回投资策略选择」分支已挪入备战分支(2026-08-26 用户定性:
        # 该按钮出现 = 上游投资策略屏处理失败的 symptom)——确定是备战画面后再
        # 特殊处理,不在备战判定前全屏扫(原位置吞掉策略屏自身 → 点标题死循环)。
        # (原子态稳定门 bookkeeping 随 PREP_SETTLE_S 退役删除,见类常量注。)

        # [历史停机钩子已全部建档移除](hook审计 S8/r351 删死代码:循环体
        # `for ... in ():` 永不执行)——r24 教训见 git:钩子停机的前提是该屏
        # **偶发**出现;建档完成后立即删除,别留到「下次遇到」(曾致每局必停
        # 被误判「外部会话拦截」排查一整晚)。

        # 0a0. 选择装备 overlay(r129,局37 r3 哨兵推送实证:**必须在 0a 选择伙伴前**——
        #      装备选择的副题也是「请选择1个」,选择伙伴屏的 标识-选择伙伴(文本
        #      「请选择1个」)在本屏同样命中 → CwScreenPartner 误派发找不到
        #      确认按钮 → 失败循环。双 id_mark 门:装备标题+请选择1个都命中才派发。
        if (self.round_by_find_area(screen, '货币战争-选择装备', '标识-选择装备', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-选择装备', '标识-请选择1个装备', crop_first=False).is_success):
            from sr_od.application.currency_war.operations.cw_screen.cw_screen_equip_pick import (
                CwScreenEquipPick,
            )

            def _on_equip_pick(ok: bool, _res: Any) -> None:
                if ok:   # review M2:仅成功才清(失败保计数=ping-pong 安全网)
                    self._clear_bail_count('事件overlay:equip_pick')

            return self._dispatch_screen_op(
                CwScreenEquipPick(self.ctx), journal_name='选择装备',
                frame_tag='overlay_equip_pick', wait=2, on_result=_on_equip_pick)

        # 0a. 选择伙伴 overlay(必须在 0b 巨星前:选择伙伴也有"确认选择"但候选是 stage 立绘)
        #     → CwScreenPartner(overlay 分发接管;委托现役 handler,详见 op)。
        #     用 screen_info 标题 area(标识-选择伙伴)位置区分,非全屏 LCS:「选择伙伴」与「请选择投资策略」
        #     共享「选择」(2/4=0.5=默认阈值)会误匹配全屏 LCS → 投资策略屏被误派发(2026-08-04 snap 实测)。
        #     area 位置不同(选择伙伴 overlay 标题在 top-center id_mark rect)→ 不命中(同 0d/0e area 化理由)。
        if self.round_by_find_area(screen, '货币战争-列车同行', '标识-选择伙伴', crop_first=False).is_success:
            self._snap('choose_partner')  # 选人选项(立绘名)→ 后续建策略评估用

            def _on_partner(ok: bool, _res: Any) -> None:
                if ok:   # review M2:仅成功才清(失败保计数=ping-pong 安全网)
                    self._clear_bail_count('事件overlay:partner')

            return self._dispatch_screen_op(
                CwScreenPartner(self.ctx), journal_name='选择伙伴',
                frame_tag='overlay_partner', wait=2, on_result=_on_partner)

        # 0a2. 银狼「我来当策划」策划事件 overlay(r103,局29 P2r6 41min 卡死实证;
        #      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节)→ CwScreenPlanner
        #      (W971 P3b overlay 分发接管;二选一卡,首次升2星=升费 vs 其他,默认升费;
        #      选卡后可能弹「属性详情」面板 → handler 内关)。
        #      ⚠️ 必须在 0a 后/备战(1)前:overlay 盖备战屏,loop 不认它就反复空读。
        if self.round_by_find_area(screen, '货币战争-骇入策划', '标识-我来当策划', crop_first=False).is_success:

            def _on_planner(ok: bool, _res: Any) -> None:
                if ok:
                    self._clear_bail_count('事件overlay:planner')

            # 失败 round_retry(与原分支内联同语义,消费同一 retry 池)
            return self._dispatch_screen_op(
                CwScreenPlanner(self.ctx), journal_name='策划事件',
                frame_tag='overlay_planner', wait=2, on_result=_on_planner,
                on_fail_retry=True)

        # 0a3. 命运卜者「强化效果三选一」overlay(r115,局32 P2r2 卡死 30min 实证;
        #      策划系事件族:标题+三卡+Q详情+确认,布局同策划事件)→ CwScreenFortune
        #      (W971 P3b overlay 分发接管)。P2 强化关。
        if (self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-命运卜者', crop_first=False).is_success
                and self.round_by_find_area(screen, '货币战争-命运卜者强化', '标识-请选择强化效果', crop_first=False).is_success):

            def _on_fortune(ok: bool, _res: Any) -> None:
                if ok:
                    self._clear_bail_count('事件overlay:fortune')

            return self._dispatch_screen_op(
                CwScreenFortune(self.ctx), journal_name='命运卜者',
                frame_tag='overlay_fortune', wait=2, on_result=_on_fortune,
                on_fail_retry=True)

        # 0a4. 位面详情 overlay(主循环兜底):情报采集 op 失败退出残留/开局自动
        #      弹出等一切来源 → 点 X 验标题消失。此前不在 0 系名单:2026-08-30
        #      残局恢复局实证,采集失败滞留详情屏 → 主循环连 15 轮未识别自停
        #      (ADR-0269「新增画面忘进名单」结构性缺口再现)。采集子 op 运行中
        #      不经此路(子 op 自带详情识别与关闭);恢复局商店探针/出战等
        #      in-match 分支全部位于本分支之后,overlay 不再污染其判读。
        if self.round_by_find_area(screen, '货币战争-位面详情', '标识-位面详情标题',
                                   crop_first=False).is_success:

            def _on_plane_detail(ok: bool, _res: Any) -> None:
                if ok:   # 仅成功清(原 :1309 语义:fail 不清 bail 计数)
                    self._clear_bail_count('事件overlay:plane_detail')
                    log.info('[cw-loop] 位面详情 overlay 已关(主循环兜底)')

            # 验消失迁入 op(单尝试);关不掉 → on_fail_retry 映射 round_retry
            #(与原分支内联 retry 同语义,消费同一 retry 池)
            return self._dispatch_screen_op(
                CwScreenPlaneDetail(self.ctx), journal_name='位面详情',
                frame_tag='overlay_plane_detail', wait=1.0,
                on_result=_on_plane_detail, on_fail_retry=True)

        # 0b. 巨星强化(盛会之星选择 overlay)→ CwScreenMegastar(选候选 + 确认,已内联旧巨星节点执行器实现)。
        #     用 screen_info 标题 area(标识-盛会之星)位置区分。原用全屏「确认选择」(lcs 0.7 防「请选择投资策略」
        #     共享「选择」误匹配)—— 但「确认选择」partner overlay 也有(靠 0a 先捕 partner 区分);改用 megastar
        #     独有标题「盛会之星」更直接(独有标题位置区分,无需依赖分支先后)。
        if self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success:
            self._snap('megastar')  # 巨星候选(立绘名)→ 后续建策略评估用

            def _on_megastar(ok: bool, _res: Any) -> None:
                if ok:   # 合法 bail 清计数(live M11 误停机;M2:仅成功才清)
                    self._clear_bail_count('事件overlay:megastar')

            # 生命周期 owner:验证 overlay 消失,超预算 bail(op 内 as-built)
            return self._dispatch_screen_op(
                CwScreenMegastar(self.ctx), journal_name='巨星强化',
                frame_tag='overlay_megastar', wait=2, on_result=_on_megastar)

        # 0c. 遭遇节点(难度二选一 + 选择)→ CwScreenEncounter(点卡选中 + 选择确认)。
        #     live 2026-08-15:改 id_mark area 检测(标识-遭遇节点,yml 已建)—— 旧全屏 OCR「遭遇其一」
        #     lcs 0.9 在卡标题 OCR 截断帧(「遭遇其」3/4=0.75)miss → 整屏落未知画面停机。
        #     handler 交互(2026-08-04 实测):点卡身选中 → 点选择确认(中间勿插空白点击会取消选中)。
        if self.round_by_find_area(screen, '货币战争-遭遇节点', '标识-遭遇节点', crop_first=False).is_success:
            self._snap('encounter')
            return self._dispatch_screen_op(
                CwScreenEncounter(self.ctx), journal_name='遭遇节点',
                frame_tag='overlay_encounter', wait=2)

        # 0d. 出战确认弹窗(未达上限)→ CwScreenDeployNotFull(勾本局不再提示 + 确认,详见 op)。
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:投资策略屏的策略描述「能量上限」
        # 与「未达上限」共享子序列「上限」(LCS 2/4=0.5)会误匹配全屏 LCS → 投资策略屏被本分支吞 → 反复触发
        # CwScreenDeployNotFull 卡死(2026-08-05 实跑)。id_mark area 位置不同 → 不命中(同 0e invest area 化理由)。
        if self.round_by_find_area(screen, '货币战争-未达上限警告', '标识-未达上限警告', crop_first=False).is_success:
            return self._dispatch_screen_op(
                CwScreenDeployNotFull(self.ctx), journal_name='未达上限确认',
                frame_tag='overlay_deploy_not_full', wait=3)

        # 0e. 选择类事件 overlay(投资策略/环境 3 选 1;补给动态 N 选,通常 4/augment 变
        #     3-5 + 确认)→ **必须在备战(1)前检测**:
        #     这些 overlay 叠在备战上,「购买经验」会从 overlay 后透出(底部左下未遮)→ 若先检查备战
        #     会误派 BuyShopCards(overlay 遮商店→"找不到商店/收起"失败→死循环)。
        #     2026-08-04 实跑发现:投资策略屏被误派 BuyShopCards(购买经验透出命中),卡死。
        #     lcs_percent=0.8:「投资策略」与「投资环境」共享「投资」(2/4=0.5)→ 0.8 杀交叉误匹配。
        # 用 screen_info id_mark area 检测(固定位置全等),非全屏 LCS —— 失败结算屏(对局未完成)含
        # 「投资策略/投资环境」(对局信息)会误匹配全屏 LCS(2026-08-06 实跑:loop 卡失败结算,
        # CwScreenInvestStrategy 误派点「标准博弈」死循环)。id_mark area 位置不同(失败结算在对局信息区,
        # 不在真屏 id_mark pc_rect)→ 不命中,落到 3b「下一页」回大厅。
        # N5 分发判别稳定化:单探测 → miss 且备战双锚命中(浮层穿透形态)
        # → 短窗复探一次(两时序形态同判据同路由,见 _invest_overlay_dispatch);
        # 复探产出的新截图回写 screen(未命中时后续分支也吃更新帧)。
        _ov_dispatch, screen = _invest_overlay_dispatch(self, screen)
        if _ov_dispatch:
            self._snap('invest_strategy')
            return self._dispatch_screen_op(
                CwScreenInvestStrategy(self.ctx), journal_name='投资策略',
                frame_tag='overlay_invest_strategy', wait=2)
         # 开局投资环境段(01-opening §2,OpeningSequence 已拆解退役):投资环境仅开场一次
        # (#11:开场 1-1 前弹,1-3 后局中只弹投资策略,两画面不同 handler),
        # 开局投资环境由 0s 分支分发(OpeningSequence 拆解退役:外循环按画面自然流转)。
        if self.round_by_find_area(screen, '货币战争-补给', '标识-补给阶段', crop_first=False).is_success:
            self._snap('supply')
            # (补给合成 outcome 行 on_result 挂点已随 outcomes 流写入端退役
            #  删除——删除波 1;派发契约 on_result 参数保留。)

            # 生命周期 owner:验证 overlay 消失才完成,超预算 bail(op 内 as-built)
            return self._dispatch_screen_op(
                CwScreenSupplyNode(self.ctx), journal_name='补给节点',
                frame_tag='overlay_supply', wait=2)

        # 0f. 节点武装箱弹窗(「武装突入」类节点,2026-08-15 M19 首见停机建档)→
        #     CwScreenArmoryBox(道具获得说明弹窗,点 × 关闭;M20 实锤改关闭模型,
        #     弹窗内箱图标是展示图不可点)。四选一选卡职责在备战箱槽链
        #     (_pick_box_card,决策单一源=策略 decide_box_card),本 op 只关弹窗。
        if self.round_by_find_area(screen, '货币战争-武装箱弹窗', '标识-简易武装箱', crop_first=False).is_success:
            self._snap('armory_box')
            return self._dispatch_screen_op(
                CwScreenArmoryBox(self.ctx), journal_name='武装箱',
                frame_tag='overlay_armory_box', wait=2)

        # 0e2. 商店刷新概率表弹窗 → 点 × 关闭(live 2026-08-14 1-2 实锤补:点球误触开后无分支消化,
        #       遮出战按钮 → Director bail → 外环也认不出 → 停机)。× 位置 VLM 定位 (1501,263);
        #       mouse_move 必带(bug#1:恢复原语同坐标点击曾落空)。
        if self.round_by_find_area(screen, '货币战争-商店刷新概率表', '标识-刷新概率表',
                                   crop_first=False).is_success:

            def _on_refresh_odds(ok: bool, _res: Any) -> None:
                log.info('[cw-loop] 概率表弹窗 → 点× 关闭')

            # × 坐标已 area 化(按钮-关闭概率表,中心 = 原 (1501,263));
            # mouse_move bug#1 缓解保留在 op 内
            return self._dispatch_screen_op(
                CwScreenRefreshOddsPopup(self.ctx), journal_name='商店刷新概率表',
                frame_tag='overlay_refresh_odds', wait=1.5,
                on_result=_on_refresh_odds)
        # 0e3. 道具详情弹窗(聘用书类;live 2026-08-15 M13 首遇):获得 3费聘用书 等道具后自动弹介绍 modal,
        #       关键词与消耗品(消耗品+拖动到)不同 → 落未知画面停机。点 ×(1862,65 VLM 定位)关;道具使用属 P4 工具域。
        #       ⚠️ r31 死循环修(live 实锤 15min+):祈愿试炼选项名含「聘用书」(4费聘用书)→ 本分支
        #       截胡 0h 祈愿分支(反复点×无效)。加祈愿屏排除:标识-祈愿试炼 命中 → 让路 0h。
        if (self.round_by_ocr(screen, '聘用书', lcs_percent=0.8).is_success
                and not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼',
                                                crop_first=False).is_success):

            def _on_item_detail(ok: bool, _res: Any) -> None:
                log.info('[cw-loop] 道具详情弹窗(聘用书)→ 点× 关闭')

            # 祈愿排他留外循环(分发判定,§1.4);× 坐标已 area 化(中心 = 原 (1862,65))
            return self._dispatch_screen_op(
                CwScreenItemDetailPopup(self.ctx), journal_name='道具详情弹窗',
                frame_tag='overlay_item_detail', wait=1.5,
                on_result=_on_item_detail)
        # 0f. 消耗品详情浮层 → ESC 关。获消耗品奖励(投资策略「星星相印」给【员工投影仪】等)后游戏自动弹
        #     介绍 modal,遮挡备战/投资策略屏 → 上面所有分支都不命中 → round_retry 死循环(2026-08-06 实跑:
        #     plane2 supply 后弹「员工投影仪」modal,flat retry ~19min 失败;**非策略死,UI 弹窗卡死**)。
        #     签名「消耗品」(类型 label) AND 「拖动到」(拖动使用说明 —— 只出现在消耗品详情 modal,备战底部
        #     消耗品栏无)→ 双条件精确,不误匹配备战。装备类详情 modal(无「拖动到」)是长尾,观察到再补。
        if (self.round_by_ocr(screen, '消耗品', lcs_percent=0.9).is_success
                and self.round_by_ocr(screen, '拖动到', lcs_percent=0.9).is_success):
            # 双条件判定留外循环(分发判定);ESC 关迁入 op,无验效
            return self._dispatch_screen_op(
                CwScreenConsumableOverlay(self.ctx), journal_name='消耗品浮层',
                frame_tag='overlay_consumable', wait=1.5)

        # 0g. 投资策略「阿哈大悦」装备选择 overlay(为阿哈选1件简易装备)→ 点装备自动关。
        #     阿哈投资策略在某节点弹此 overlay(选1件简易装备给阿哈)。bot 不选 → overlay 持 → 卡备战
        #     (2026-08-07 实跑:plane1 1-3 卡此 overlay 666s)。点第1装备(幸运星位 626,250;策略可后续
        #     按 key_equips 选,先关 overlay 推进)→ 实测自动关 overlay 回备战。
        if self.round_by_find_area(screen, '货币战争-备战', '标识-简易装备', crop_first=False).is_success:
            # 固定策略申报:点首件 = 现行为(注释详见 CwScreenAhaEquipPick);
            # 首件坐标已 area 化(按钮-简易装备首件,中心 = 原 (626,250))
            return self._dispatch_screen_op(
                CwScreenAhaEquipPick(self.ctx), journal_name='阿哈装备选择',
                frame_tag='overlay_aha_equip', wait=1.5)

        # 0h. 祈愿试炼 overlay(节点级 quest 选择:选1试炼 → 完 objective 得奖励)→ CwScreenWishTrial
        #     (W971 P3b overlay 分发接管;点第1卡 + 确认选择)。叠备战上挡备战分支 →
        #     必须在备战(1)前检测。2026-08-08 实跑发现:bot 卡此 overlay 68min(购买经验
        #     透出命中 → 备战分支误派 → shop 被遮失败 → 死循环)。ESC 不关;
        #     点卡身选中(金色边框)→ 确认选择 → 关回备战。
        if self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼', crop_first=False).is_success:

            def _on_wish_trial(ok: bool, _res: Any) -> None:
                if ok:
                    self._clear_bail_count('事件overlay:wish_trial')

            return self._dispatch_screen_op(
                CwScreenWishTrial(self.ctx), journal_name='祈愿试炼',
                frame_tag='overlay_wish_trial', wait=2, on_result=_on_wish_trial)

        # 0i. 星徽秘典四选一(2026-08-16 M45 完整建档,用户指导):备战席「秘密典籍」道具
        #     开启后弹四选一星徽 → CwScreenBookcard(overlay 分发接管,选卡读法按
        #     原内联 _handle_star_tome_pick 直写进 op)。判据(review P2 加固):id_mark
        #     命中即接管 —— 提示词 OCR miss 时也进 handler(fallback 卡1),**不放行到
        #     备战分支**(弹窗盖备战 → 误派 CwScreenPrep ping-pong)。
        if self.round_by_find_area(screen, '货币战争-星徽秘典弹窗', '标识-星徽秘典', crop_first=False).is_success:
            return self._dispatch_screen_op(
                CwScreenBookcard(self.ctx), journal_name='星徽秘典',
                frame_tag='overlay_bookcard', wait=2)

        # 0k. 专家邀请函弹窗(2026-08-30 建档):备战席「书册卡」点开后的五选一
        #     (4 角色卡+现金为王)→ CwScreenExpertInvite 全链(开卡/选卡/收案;选卡
        #     判据=主力阵营同线→在场阵营同线→现金为王兜底,见 handler docstring)。
        #     判据同 0i:id_mark 命中即接管,不放行到备战分支(弹窗盖备战 →
        #     误派 CwScreenPrep ping-pong)。替代原 bookcard_confirm 停机钩子
        #     (钩子段已随本分支接线删除)。
        if self.round_by_find_area(screen, '货币战争-备战-专家邀请函', '标识-专家邀请函', crop_first=False).is_success:
            return self._dispatch_screen_op(
                CwScreenExpertInvite(self.ctx), journal_name='专家邀请函',
                frame_tag='overlay_expert_invite', wait=2)

        # 0t. 商店卡牌详情弹窗(T-163 实机事故建档:奖励节点点球误触开的
        #     角色 offer 购买页——0e2 概率表/1d 星徽详情之后同族第三例)。
        #     弹窗暗色衬底遮蔽底层全部锚(T-163 实证:开商店三锚/备战双锚
        #     OCR 全灭),不先分流则只剩 1b 变体不敏感关键词兜底接住 =
        #     「点 X 坐标落面板内零效果 → 无验效假成功 → 外循环重分发」
        #     的 26 分钟死循环形态。处理 = 点 X(弹窗内坐标,1d 先例「永远
        #     安全」;不点购买——买不买归商店域,关闭动作不代替购买决策)
        #     → 验 X 消失 → 交回重判(店开 → 0n 商店访问;备战 → 备战环)。
        #     弹窗从此任何时刻有主,无孤儿形态。
        if _shop_card_detail_anchor_hit(self, screen):

            def _on_shop_card_detail(ok: bool, _res: Any) -> None:
                if ok:
                    self._clear_bail_count('事件overlay:shop_card_detail')
                log.info('[cw-loop] 商店卡牌详情弹窗 → 点X关闭(ok=%s)', ok)

            # 关不掉 → on_fail_retry 映射 round_retry(消费同一 retry 池,
            # 「点了≠成了」由 op 内验效承载,T-163 D3)
            return self._dispatch_screen_op(
                CwScreenShopCardDetailPopup(self.ctx), journal_name='商店卡牌详情',
                frame_tag='overlay_shop_card_detail', wait=1.5,
                on_result=_on_shop_card_detail, on_fail_retry=True)

        # 0m. 备战「锁定」暗色子态族(2026-09-02 建档+接线,用户口述时序 #12/#20):
        #     overlay 点「返回备战界面」→ 备战画面带暗色蒙层,右上「返回XX选择」
        #     可回对应 overlay。⚠️ 此态下备战双锚(购买经验/出战)仍精准命中
        #     (用户截图 analyze 实测 is_precise)——不先分流会被当正常备战操作
        #     (读暗牌/暗 gold)。命中即点对应按钮回 overlay(0e 系/0c 分支接管);
        #     备战分支内旧 OCR 兜底(双锚后)保留作双保险。
        #     通用规则单一源 = screen_flow_timing.md #18(暗色态判别锚=右上按钮)。
        for _lock_screen, _lock_area in (
                ('货币战争-备战-策略锁定', '按钮-返回投资策略选择'),
                ('货币战争-备战-遭遇锁定', '按钮-返回遭遇选择'),
        ):
            if self.round_by_find_area(screen, _lock_screen, _lock_area, crop_first=False).is_success:

                def _on_prep_locked(ok: bool, _res: Any,
                                    _ls: str = _lock_screen) -> None:
                    log.info('[cw-loop] 暗色锁定态(%s)→ 点返回按钮(success=%s)',
                             _ls, ok)

                # 两画面档一份 op 类,分发处传命中的那对(带参构造)
                return self._dispatch_screen_op(
                    CwScreenPrepLockedReturn(self.ctx, _lock_screen, _lock_area),
                    journal_name='备战暗色锁定', frame_tag='overlay_lock',
                    wait=1.5, on_result=_on_prep_locked)

        # 0n. 备战-开商店子态(备战子态族;与 0m 暗色锁定分支同段语义:
        #     画面 = 备战底板 + 浮层子态,判据锚在浮层独有元素上)。
        #     ⚠️ 序位 = 必须先于备战双锚(1):商店浮层不遮双锚锚区,
        #     「购买经验/出战」在浮层下透出命中 → 商店开着时双锚判据穿透,
        #     备战分支内的发射面(达标臂 RunDeploy+StartBattle)会把部署/
        #     出战点击打在浮层上被挡(实机事故:商店浮层上跑部署空挥段,
        #     详见进度流水 2026-09-06 外循环开商店分支批)。判据单一源 =
        #     _shop_open_anchors_hit(三 id_mark:idmark 审计批定稿;互斥
        #     依据 = 干净备战帧「按钮-收起」不存在,开商店档零候选,离线
        #     配对验证见 idmark 审计表 §三)。
        #     处理 = 转交商店访问路径(ADR-0562,用户裁定 2026-09-06):委托
        #     CwScreenPrep.visit_open_shop(店已开态编排单一源)——入口观察
        #     现读牌面 → 策略器逐动作决策(买/升/刷)→ CloseShop 终结收店
        #     交回重判。禁路由层硬编码收起:「收不收」由策略器基于期望态
        #     决定(CloseShop = 商店画面 op 的一等终结动作,ADR-0517 决策
        #     4/5),旧「点收起交回重判」既越权又造成无谓往返(收起→重开
        #     店想买时多一轮)。分键:branch_shop_open_hit = 分支命中;
        #     branch_shop_open_visit_ok/_fail = 商店访问结果。深度防御
        #     保留:达标臂浮层扫描(readiness_overlay_hold)与 CwScreenPrep
        #     环入口 _try_collapse_open_shop 守卫不删——彼两处降级为单点
        #     兜底(0n 分支处理不再收店后,环入口守卫仍兜「漏帧进备战环」)。
        if _shop_open_anchors_hit(self, screen):
            _so_counters = getattr(strategy_state_of(
                self.ctx.cw_match.session), 'cw4_counters', None)
            if isinstance(_so_counters, dict):
                _so_counters['branch_shop_open_hit'] = \
                    _so_counters.get('branch_shop_open_hit', 0) + 1
            _prep = CwScreenPrep(self.ctx)

            def _on_shop_visit(ok: bool, res: Any) -> None:
                if isinstance(_so_counters, dict):
                    _k = 'branch_shop_open_visit_ok' if ok \
                        else 'branch_shop_open_visit_fail'
                    _so_counters[_k] = _so_counters.get(_k, 0) + 1
                log.info('[cw-loop] 开商店态(备战子态族)→ 商店访问路径'
                         '(策略器决策+关店终结)(ok=%s detail=%s)',
                         ok, getattr(res, 'status', ''))

            # 0n 转交通道经包装落 op='商店访问' 行(S11 对齐关键行:复盘按
            # journal 直读商店访问边界,ADR-0584 §3.3)。visit_open_shop 返回
            # (ok, detail) 元组 → 包装可调用形经 _FnResult 适配;visit_open_shop
            # 本体一字不动(显式开店通道同一汇合点)。
            return self._dispatch_screen_op(
                _prep.visit_open_shop, journal_name='商店访问',
                frame_tag='overlay_shop_open', wait=1.5, on_result=_on_shop_visit)

        # 0j. 「前台区域无角色,无法出战」提示弹窗(2026-08-17 M49 停机建档)。
        #     P4R 升级(1-1 事故 5h 死循环返工):确认关闭 → **带落点验证的
        #     重部署**(CwOpDeploy,落点 CV 已收编)→ 本迭代内直接再出战;
        #     重试上限 FRONTLESS_REDEPLOY_LIMIT,超限 round_fail 交未知画面
        #     兜底链(旧「确认关闭→等下轮 CwScreenPrep→StartBattle 假成功」
        #     形态 = 无限 round_wait,根因见弹窗污染守卫 prep_actions
        #     .POST_LAUNCH_BLOCKERS)。T-176 V-1:出口像素判效读拆除,失败
        #     信号 = 出战链弹窗守卫(游戏承载,见下方收编注)→ 本分支重试
        #     预算兜底。
        if self.round_by_find_area(
                screen, '货币战争-提示-前台无角色', '标识-无角色提示', crop_first=False).is_success:

            def _frontless_recovery_step() -> OperationRoundResult:
                _ok_pt = self.round_by_find_and_click_area(
                    screen, '货币战争-提示-前台无角色', '按钮-确认', success_wait=1)
                self._frontless_redeploy = getattr(self, '_frontless_redeploy', 0) + 1
                if self._frontless_redeploy > CwLoop.FRONTLESS_REDEPLOY_LIMIT:
                    log.error('[cw!] [loop] 前台无角色:验证重部署 %d 次仍前台空 → '
                              'round_fail 交兜底链(不再无限重试)',
                              CwLoop.FRONTLESS_REDEPLOY_LIMIT)
                    return self.round_fail('前台无角色重部署超限(前台仍空)')
                log.info('[cw-loop] 前台无角色提示 → 确认关闭(%d/%d)→ 带验证重部署',
                         self._frontless_redeploy,
                         CwLoop.FRONTLESS_REDEPLOY_LIMIT)
                from sr_od.application.currency_war.operations.cw_op.cw_op_deploy import (
                    CwOpDeploy,
                )
                _rd = CwOpDeploy(self.ctx).execute()
                log.info('[cw-loop] 前台无角色重部署 → %s',
                         getattr(_rd, 'status', '') or ('成功' if getattr(_rd, 'success', False) else '失败'))
                # T-176 V-1 收编:外循环像素判效读(slot_occupied 判前排 ≥1)
                # 已拆除——分发段判效与「动作 op 只管机械执行,落地判定归观察
                # 侧」裁定冲突(统一观察架构 §5.1 v11/T-223)。失败信号改由
                # 两道既有机制承载:①deploy 侧落点验证(LIVE_SEAL 收编面);
                # ②出战链 POST_LAUNCH_BLOCKERS 弹窗守卫(游戏对「出战时前台
                # 空」的弹窗信号,前排仍空再出战即弹「前台无角色」→ 守卫判
                # False → round_retry 回本分支,重试计数+1,超限 round_fail
                # 兜底——本分支的存在本身就是该信号的观察侧响应)。
                time.sleep(1.0)   # 部署动画/特效窗(出战点击时序,防特效帧落空;机械等待非判效)
                # 前排已有角色 → 本迭代内直接再出战(不再依赖下轮 CwScreenPrep
                # 重派——旧链的假成功正是发生在这段间隙)。
                from sr_od.application.currency_war.kernel.cw_prep_actions import (
                    StartBattle as _StartBattle,
                )
                from sr_od.application.currency_war.prep_actions import (
                    PrepActionExecutor as _PAE,
                )
                _sb_ok, _sb_detail = _PAE(self, self.ctx).execute(_StartBattle())
                if _sb_ok:
                    self._frontless_redeploy = 0   # 出战真转移 → 重试预算复位
                    self._battle_ts = time.monotonic()
                    self._battle_wait_active = True
                    log.info('[cw-loop] 前台无角色恢复链:重部署 → 出战成功')
                    return self.round_wait(wait=3)
                log.warning('[cw!] [loop] 前台无角色恢复链:重部署后出战未落地(%s)'
                            '→ retry(下轮再入本分支计重试;失败信号 = '
                            'POST_LAUNCH_BLOCKERS 弹窗守卫)',
                            _sb_detail)
                return self.round_retry(wait=2)

            # C1(ADR-0584 §1.3):准推进恢复链非纯推进画面——与发射核/战斗窗口
            # 状态耦合,本批只接包装补 op='前台无角色恢复' 行,链体零改;op 化
            # 前置 = 「出战已发射」状态交回契约设计(挂后续批)。链形透传:
            # 轮次结果即分支出口,包装只补 journal 行与留证帧。
            return self._dispatch_screen_op(
                _frontless_recovery_step, journal_name='前台无角色恢复',
                frame_tag='overlay_frontless', wait=1.0)

        # 0p. BOSS 简报(P3b 实机第三局走查补:06-overlays §3 设计有、实现漏;
        #     #26 建档「标识-强敌来袭」)→ CwScreenBossBriefing(点空白 → 完成承诺 =
        #     等备战商店开,「按钮-收起」锚+上界兜底)。**分支序锚位 = 先于备战
        #     双锚**(事故教训:横幅遮挡下双锚模板仍透出命中,无本分支时帧误落
        #     备战分支空转 598s/SENTINEL-STALL)。
        #     P4R3 锚加固(第五局 1-9 实锤):area 锚被 OCR 误读击穿(「强敌
        #     来袭」读成「强敌米」)→ 分发改共享判别单一源 is_boss_briefing_
        #     texts(「强敌」片段,误读形态鲁棒;CwScreenBossBriefing 内部同源兜底)。
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
            is_boss_briefing_texts as _is_boss_frame,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
            read_ocr_texts as _frame_texts,
        )
        if (self.round_by_find_area(
                screen, '货币战争-BOSS简报', '标识-强敌来袭',
                crop_first=False).is_success
                or _is_boss_frame(_frame_texts(self.ctx, screen))):
            self._note_branch_screen('货币战争-BOSS简报')   # R2 开局链写点

            def _on_boss_briefing(ok: bool, res: Any) -> None:
                # 0q 排他生效 = 误分发流恢复 → 计数清零(p4r3 字面复位挂点①)
                self._plane_mis_streak = 0
                log.info('[cw-loop] BOSS 简报 → CwScreenBossBriefing → %s',
                         getattr(res, 'status', ''))

            return self._dispatch_screen_op(
                CwScreenBossBriefing(self.ctx), journal_name='BOSS简报',
                frame_tag='flow_boss_briefing', wait=1.0,
                on_result=_on_boss_briefing)

        # 0q. 位面过渡(P4R2 序位返工:原在备战分支之后——「浮层叠备战」家族
        #     审计中唯一的序位漏项;全浮层序位纪律 = 先于备战双锚,序锁矩阵
        #     test_cw_dispatch_order_matrix.py 逐一钉死)。
        #     P4R3 两画面排他(第五局 1-9 实锤):boss 简报画面**也含**「点击
        #     空白处继续」(共享交互文案不作判据)——「强敌」特征在场 = boss
        #     简报帧,不进位面过渡(留给 0p);误分发型 fail(过渡提示不在)
        #     连续达上限 → round_fail 交未知兜底链(不再 2s 无限循环)。
        if self.round_by_ocr(screen, '点击空白处继续', lcs_percent=0.8).is_success:
            if _is_boss_frame(_frame_texts(self.ctx, screen)):
                log.info('[cw-loop] boss 简报帧含共享文案「点击空白处继续」→ '
                         '排他,留 0p(不误分发位面过渡)')
                return self.round_wait(wait=1.0)
            self._note_branch_screen('货币战争-位面过渡')   # R2 开局链写点

            def _on_plane_transition(ok: bool, res: Any) -> OperationRoundResult | None:
                # 误分发型 fail streak 计数 + 超限 round_fail(p4r3 守卫域,留
                # 外循环;字面复位挂点②:闭包内联于 loop 源,禁提取为方法级
                # 函数——字面移出 loop 源 = 锁红,test_cw_p4r3 :95)
                if ok:
                    self._plane_mis_streak = 0
                    log.info('[cw-loop] 位面过渡 → CwScreenPlaneTransition → %s',
                             getattr(res, 'status', ''))
                    return None   # 默认映射 round_wait(1.0)
                self._plane_mis_streak = getattr(self, '_plane_mis_streak', 0) + 1
                if self._plane_mis_streak >= CwLoop.PLANE_MISDISPATCH_LIMIT:
                    try:
                        _shot = self.save_screenshot(prefix='plane_misdispatch')
                    except Exception:  # noqa: BLE001  留证失败不阻塞
                        _shot = ''
                    log.error('[cw!] [loop] 位面过渡连续 %d 次 fail(疑误分发/'
                              '误读)→ round_fail 交兜底链(shot=%s)',
                              self._plane_mis_streak, _shot)
                    return self.round_fail('位面过渡连续 fail 超上限(交兜底链)')
                log.info('[cw-loop] 位面过渡 → CwScreenPlaneTransition → %s',
                         getattr(res, 'status', ''))
                return None

            return self._dispatch_screen_op(
                CwScreenPlaneTransition(self.ctx), journal_name='位面过渡',
                frame_tag='flow_plane_transition', wait=1.0,
                on_result=_on_plane_transition)

        # 0r. 位面简报(开场三 boss+词缀;接管局/重入首帧落此屏时兜底分流)
        #     → CwScreenBriefing(读简报写 session 位面序真值 → 点「下一步」链)。
        #     原 OpeningSequence 拆解退役(用户裁决:抽象不成立):四步各有
        #     画面 op,外循环按画面分发天然顺序流转(简报→位面过渡 0q→
        #     投资环境 0s→备战 1),接管局由分发器自然续走。
        if self.round_by_find_area(screen, '货币战争-简报', '标识-本场对局首领',
                                   crop_first=False).is_success:
            self._note_branch_screen('货币战争-简报')   # R2 开局链写点

            def _on_briefing(ok: bool, res: Any) -> None:
                log.info('[cw-loop] 位面简报 → CwScreenBriefing → %s',
                         getattr(res, 'status', ''))

            return self._dispatch_screen_op(
                CwScreenBriefing(self.ctx), journal_name='位面简报',
                frame_tag='flow_briefing', wait=1.0, on_result=_on_briefing)

        # 0s. 投资环境(开场 1-1 前弹一次;接管局重入此屏时兜底分流)
        #     → CwScreenInvestEnv(节点台账重读/刷新流,现役 handler 全逻辑)。
        #     成功后链 CwScreenWaitOneOne:开局补给动画长且无结束标志(用户裁定
        #     特殊等待),等「备战阶段」锚就绪再交备战分支(承接退役序列的
        #     终步语义;锚一直不现由其超时上界留证 fail 交循环)。
        if self.round_by_find_area(screen, '货币战争-投资环境', '标识-投资环境',
                                   crop_first=False).is_success:
            self._note_branch_screen('货币战争-投资环境')   # R2 开局链写点
            from sr_od.application.currency_war.operations.cw_screen.cw_screen_invest_env import (
                CwScreenInvestEnv,
            )

            def _on_invest_env(ok: bool, res: Any) -> None:
                log.info('[cw-loop] 投资环境 → CwScreenInvestEnv → %s',
                         getattr(res, 'status', ''))

            def _on_wait_one_one(ok: bool, res: Any) -> None:
                log.info('[cw-loop] 等待1-1 → CwScreenWaitOneOne → %s',
                         getattr(res, 'status', ''))

            # 链序保留(用户裁定特殊等待):环境 op → 等 1-1 备战锚 op;
            # 两 op 两对 journal 行(0s 补行,ADR-0584 §3.4)。首段轮次结果
            # 只记日志不分流(与原内联同形),返回尾段结果。
            self._dispatch_screen_op(
                CwScreenInvestEnv(self.ctx), journal_name='投资环境',
                frame_tag='flow_invest_env', wait=0, on_result=_on_invest_env)
            self._note_branch_screen('货币战争-等待1-1')   # R2 开局链写点(分支级 token)
            return self._dispatch_screen_op(
                CwScreenWaitOneOne(self.ctx), journal_name='等待1-1',
                frame_tag='flow_wait_one_one', wait=1.0,
                on_result=_on_wait_one_one)
        # 1. 备战阶段 → 备战单轮 op(CwScreenPrep 单轮五段:观察→对账→决策→
        #    期望态→执行,交回本循环;W971 P3b 返工定稿:内环已拆,外循环是
        #    唯一循环)。注:遭遇/选择伙伴 等 event overlay 已在 0 系分支处理。
        # 画面判定 = **双锚**(2026-08-26 用户定调「全面的 id mark」):「备战标识-购买经验」
        # (左下,conf 0.9999)+「按钮-出战」(右,跨 shop 开/关子态恒在;单锚在 overlay
        # 半开帧可从底层透出命中,prep.md §时序)。双锚同帧命中才认备战。
        if (self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success
                and self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success):
            self._battle_ts = None   # ADR-0250:回备战 → 战斗窗口关(watch 恢复)
            # GameState 心跳观察者采样(迁移批次一;正本 = GameState-数据
            # 结构设计.md §2.4 关键结构 2):备战环入口读单调写点序号,连续
            # ≥2 环零推进 = 观察断流诊断(log.warning 不停机,处置交既有
            # 守卫链)。纯采样零行为面。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
                note_board_state_heartbeat,
            )
            note_board_state_heartbeat(self.ctx)
            # 效果账本节点 tick 挂点(迁移批次三,设计 §5.1「节点推进=倒计时
            # 递减」/§8.4 用法块「进节点边界(备战帧观察后调用)」)。同节点
            # 去重与登记当节点不推进的守卫都在 tick_node 内(键 = 节点序
            # 快照);到期移除条目 = 尾款触发面,此处只做观测留证——尾款
            # 金面走观察覆盖兜底(设计 §4.1 九卡纠偏:躺平类延迟金不经
            # instant_gold 写字段,禁此处 logic 直写金币防双计)。best-effort:
            # 账本推进失败不阻塞备战主链。
            try:
                _bs_tick = board_state_of(self.ctx.cw_match.session)
                _nd_tick = _bs_tick.node.value
                # advance_node(None) 守卫(迁移尾批附带项,None = 无条件推进
                # 语义是测试/sim 直调形态;生产挂点 node 未观察帧整段跳过,
                # 禁把「未观察」当「真进节点」无条件推进虚耗余期/虚累余额)
                _adv, _ex_list = False, []
                if _nd_tick is not None:
                    _ord_tick = (_nd_tick.plane - 1) * 9 + _nd_tick.round_num
                    _adv, _ex_list = _bs_tick.effects.advance_node(_ord_tick)
                for _ex_eff in _ex_list:
                    log.warning('[cw!][effect] 效果到期移除:%s(尾款触发面;'
                                '金面走观察覆盖兜底,设计 §4.1/§5.1)',
                                _ex_eff.spec.name)
                # 账本→字段桥(迁移批次三 B1,设计 §5.1/§3.3.5-6/§3.2.5):
                # per_node 余额累加仅在真实推进时(每节点恰一次,闸门=
                # advance_node advanced 位);容量投影每 pass 重锚(观察构造器
                # 按默认容量建视图会覆盖投影值,备战帧观察后须回写)。均
                # write_logic 记录面,best-effort 不阻塞备战主链。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    grant_effect_node_refresh_balance,
                    project_effect_capacity,
                )
                if _adv:
                    grant_effect_node_refresh_balance(
                        _bs_tick,
                        frame=f'p{_nd_tick.plane}-r{_nd_tick.round_num}'
                        if _nd_tick is not None else '')
                    # 装备写端·节点边界金结算(T-70 生产接线;载体 =
                    # settle_node_boundary_gold,指定挂点 = 备战分支
                    # advance_node 点,T-63 交付申报):轮首收入三支
                    # (cw_economy.round_start_income 单一源)+ 装备贡献
                    # (财富现读现算;宝钻 = 逐件进度载体缺位,透传 0 保守
                    # 零授予,T-51 缺口申报维持)合并单次金面 write_logic,
                    # live 写端收口——值随后受备战帧观察覆盖辖,失配 =
                    # 推算 bug(设计 §2.3)。保守闸:最近结算败局(killed
                    # =False)或结算/连胜不可知时整拍跳过——败补口径
                    # (ADR-0623 决策3)与开局轮首入账待实机实证,该窗维持
                    # 观察覆盖兜底(与接线前零行为差);金未读载体自跳。
                    # 倍率/息修饰 = aggregate_economy 聚合链(载体 docstring
                    # 指派归接线批的调用方契约)。best-effort 同本块纪律。
                    if self.ctx.cw_match is not None:
                        from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                            settle_node_boundary_gold,
                        )
                        from sr_od.application.currency_war.kernel.cw_investments import (
                            aggregate_economy,
                        )
                        _sett_nb = _bs_tick.settlement.value
                        _streak_nb = _bs_tick.streak.value
                        if (_nd_tick is not None
                                and _sett_nb is not None
                                and _sett_nb.killed is True
                                and _streak_nb is not None):
                            _agg_nb = aggregate_economy(list(getattr(
                                self.ctx.cw_match.session,
                                'active_strategies', None) or []))
                            _nb = settle_node_boundary_gold(
                                _bs_tick,
                                plane=_nd_tick.plane,
                                round_num=_nd_tick.round_num,
                                node_type=_nd_tick.kind,
                                streak=int(max(0, _streak_nb)),
                                win_reward_mult=_agg_nb.win_reward_mult,
                                interest_flat=_agg_nb.interest_flat_per_node,
                                interest_cap=_agg_nb.interest_cap_override,
                                diamond_gold=0,
                                frame=f'p{_nd_tick.plane}-r{_nd_tick.round_num}'
                                if _nd_tick is not None else '')
                            if _nb.written:
                                log.info(
                                    '[cw-loop] 节点边界金结算 logic 写入'
                                    '(branch=%s total=%s=收入%s+财富%s+宝钻%s)',
                                    _nb.branch, _nb.total, _nb.income_total,
                                    _nb.wealth_gold, _nb.diamond_gold)
                project_effect_capacity(_bs_tick)
            except Exception as e:   # noqa: BLE001  观测面失败不阻塞
                log.warning(f'[cw-loop] 效果账本 tick 失败(不阻塞): {e}')
            # 达标即出战臂(14号稿 §9.6,第七局复盘病灶:达标后 3 轮
            # RunDeploy 合法 no-op 靠守卫停机才重置):判据核 = kernel
            # ``readiness_launch_decision`` 单一源(sim 决策下沉两小批①
            # 上收;线成型 fp≥1.00 与 P59/ADR-0522 触发门同源,禁本面
            # 内联第二实现)∧ 战斗就绪(备战双锚已命中 = 战斗入口可用;
            # overlay 在 0 系分支先行清场)⇒ 立即经底层发射核出战,短路
            # 备战动作链。位次 = 动作链之前、守卫计数之前(§10;守卫规格
            # 零改动,达标帧守卫分键零命中——§7.3 锚③);不过
            # _cw_locked_sync_done 闩(C1:闩只辖恢复局面)。非达标帧现行
            # 序零变化,不重排。
            from sr_od.application.currency_war.kernel.cw_launch_admission import (
                LAUNCH_QUALITY_DEFER_FRAMES_KEY,
                LAUNCH_QUALITY_EVAL_ERROR_KEY,
                readiness_launch_decision,
            )
            from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
                line_members as _line_members,
            )
            _tc = getattr(strategy_state_of(self.ctx.cw_match.session), 'target_comp', None)
            # 换源 T-146:达标臂判据源 = 容器单例(旧 last_state 滞后帧 +
            # 过渡桥装箱退役;同备战观察写端刷新,判据面逐字段重验在册)
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
            )
            _arm_core = readiness_launch_decision(
                board_state_of(self.ctx.cw_match.session), _tc,
                line_members=_line_members)
            _arm_armed = _arm_core['armed']
            # 质量闸观测分键(ADR-0570 待标定①实机观测 sink:推迟帧/评估
            # 异常帧;best-effort,容器缺席静默跳过,与 readiness_overlay_
            # hold 同写入族;键名单一源 = kernel 常量,三审07轮 C2)。
            counters = getattr(strategy_state_of(
                self.ctx.cw_match.session), 'cw4_counters', None)
            if isinstance(counters, dict):
                if _arm_core.get('quality_eval_error'):
                    counters[LAUNCH_QUALITY_EVAL_ERROR_KEY] = \
                        counters.get(LAUNCH_QUALITY_EVAL_ERROR_KEY, 0) + 1
                _q_armed = _arm_core.get('quality')
                if _q_armed is not None and _q_armed.get('defer_by_quality'):
                    counters[LAUNCH_QUALITY_DEFER_FRAMES_KEY] = \
                        counters.get(LAUNCH_QUALITY_DEFER_FRAMES_KEY, 0) + 1
            if _arm_armed:
                # 浮层在场排除(第十五局实机雷:投资策略浮层盖备战后弹出,
                # 双锚模板穿透命中 → RunDeploy 拖拽落空 placed=0)。探测复用
                # 0 系分发锚表(零新参数):备战自身锚以外任一锚命中 = 浮层
                # 在场 → 本轮不发射,交由浮层接管面(0 系分支)处理;分键
                # 零静默。深度防御注:本扫描 = 单点兜底,商店浮层穿透的
                # 主防线已前移至 0n 开商店分支(路由级,先于备战分支整链)。
                _ov_hit = None
                for _ov_branch, _ov_screen, _ov_area in \
                        CwLoop.DISPATCH_AREA_ANCHORS:
                    if _ov_screen == '货币战争-备战':
                        continue   # 备战自身锚(双锚),非浮层
                    if self.round_by_find_area(
                            screen, _ov_screen, _ov_area,
                            crop_first=False).is_success:
                        _ov_hit = f'{_ov_screen}.{_ov_area}'
                        break
                if _ov_hit is None and self.round_by_ocr(
                        screen, '遭遇其', lcs_percent=0.9).is_success:
                    # 遭遇选择面板 = 备战屏上的面板(非独立屏;切屏竞态实测
                    # 病例):双锚仍可见但板面槽区被面板覆盖 → 拖拽落进面板
                    # 覆盖的中部槽区。锚表探不到,补 OCR 词「遭遇其」前缀
                    #(其X 卡题视遭遇池而定,前缀更稳——出处 =
                    # docs/game/screens/currency_war_encounter.md:22;
                    # cw_entry_exit 同款复用,零新参数)。面板在场同不发射,
                    # 交遭遇接管面。
                    _ov_hit = '遭遇选择面板(OCR:遭遇其*)'
                if _ov_hit is not None:
                    _arm_armed = False
                    counters = getattr(strategy_state_of(
                        self.ctx.cw_match.session), 'cw4_counters', None)
                    if isinstance(counters, dict):
                        counters['readiness_overlay_hold'] = \
                            counters.get('readiness_overlay_hold', 0) + 1
                    log.info('[cw-loop] 达标臂浮层在场(%s)→ 本轮不发射,'
                             '交由浮层接管面', _ov_hit)
            if _arm_armed:
                # 发射帧受限消费仲裁(出口 B;ADR-0566):位次契约 = armed
                # 判定通过 ∧ 浮层在场闸通过 ∧ 预检通过(helper 内)∧ 发射核
                # 调用之前(I-2 钉死「确将发射」路径独占)。溢出段先消费后
                # 出战;带内/预检未过帧零动作直落发射,行为与非发射帧同构。
                _arb = _launch_frame_arbitration(self)
                if _arb.get('abort'):
                    # 仲裁访问失败路径(未识别卡停机钩子等):保画面交回
                    # 外环,停机接管;禁在本帧发射摧毁现场。
                    log.info('[cw-loop] 发射帧仲裁访问中止(失败路径保画面)'
                             ',本轮不发射')
                    return self.round_wait(wait=1)
                _ok_r, _detail_r = readiness_battle_launch(self, self.ctx)
                if _detail_r == 'readiness_stale_screen':
                    if _arb.get('entered'):
                        # 仲裁消费后弃射(可辨识残量,DESIGN v1.1 §3.2):
                        # 仲裁段已切屏而发射核屏态复验未过,该帧从「非发射
                        # 帧 digest 零变化」锚辖域显式豁免,defect 分键禁静默。
                        from sr_od.application.currency_war.kernel import (
                            cw_launch_arbitrage as _kla,
                        )
                        _launch_arb_counter(self, _kla.KEY_ABANDONED_LAUNCH)
                        try:
                            from sr_od.application.currency_war.kernel.cw_game_state import (
                                board_state_of as _bso_arb,
                            )
                            from sr_od.application.currency_war.telemetry.defects import (
                                record_defect as _rd_arb,
                            )
                            _sess_arb = getattr(self.ctx.cw_match, 'session', None)
                            _nd_arb = (_bso_arb(_sess_arb).node.value
                                       if _sess_arb is not None else None)
                            _rd_arb(
                                'launch', _kla.KEY_ABANDONED_LAUNCH,
                                expected='仲裁关店后备战屏态恢复,发射核复验通过',
                                observed='屏态复验 stale,本轮弃射落守卫链',
                                plane=int(_nd_arb.plane) if _nd_arb is not None else 0,
                                round_num=int(_nd_arb.round_num)
                                if _nd_arb is not None else 0,
                                verdict=('可辨识残量申报:仲裁切屏与发射核'
                                         '复验竞态的单列计数,禁静默'),
                                reader_source='launch_arbitrage',
                                gap_large=False, auto_resolved=True,
                                note='豁免与计数语义 = ADR-0566/DESIGN §3.2')
                        except Exception:   # noqa: BLE001  遥测 best-effort
                            pass
                    # 屏态过期非发射失败:不消耗 C1 计数、不短路,落到守卫
                    # 链继续(下一环新截图重判真实屏)
                    log.info('[cw-loop] 达标臂屏态过期放弃发射,本轮交既有链')
                else:
                    log.info('[cw-loop] 达标即出战(fp≥1.00,ok=%s): %s',
                             _ok_r, _detail_r)
                    if _ok_r:
                        # 成功复位失败计数(窗口 = 连续失败,非累计)
                        self._cw_readiness_fail_n = 0
                        return self.round_wait(wait=3)
                    # 发射失败连续计数(防线 C1,出处 = 14 号稿 §7.1 as-built
                    # 发射门准入三元语义):fp≥1.00 恒真 +
                    # StartBattle 持续失败 + round_wait 不耗 retry = 框架内
                    # 零防线自旋。连续 3 次失败放弃短路,回落守卫链(守卫
                    # 照常计数,卡死仍可停机),分键零静默;成功即复位。
                    _rf = getattr(self, '_cw_readiness_fail_n', 0) + 1
                    self._cw_readiness_fail_n = _rf
                    counters = getattr(strategy_state_of(
                        self.ctx.cw_match.session), 'cw4_counters', None)
                    if isinstance(counters, dict):
                        counters['readiness_launch_fail'] = \
                            counters.get('readiness_launch_fail', 0) + 1
                    if _rf >= 3:
                        self._cw_readiness_fail_n = 0
                        if isinstance(counters, dict):
                            counters['readiness_launch_giveup'] = \
                                counters.get('readiness_launch_giveup', 0) + 1
                        log.error('[cw!][loop] 达标臂连续 %d 次发射失败(最后一次:'
                                  ' %s)→ 放弃短路,回落守卫链(防线 C1)', _rf,
                                  _detail_r)
                    else:
                        log.warning('[cw!][loop] 达标臂发射失败(第 %d/3 次,%s)'
                                    '→ 下环重试', _rf, _detail_r)
                        return self.round_wait(wait=3)
            # (原 PREP_SETTLE_S 子态稳定门 + _post_settle_auto_shop 自动开店判稳
            # 标志位已退役,W971 §2.6/§2.11:半开帧防护替身 = 单轮 op 清场 +
            # 自动开店收起探针;稳定性由外循环每轮重识别保证。)
            # 环级无进展守卫(F2 单键计数,T-167;架构反思三卡死批防线①,
            # 取代旧 stall 留证线——单一计数勿留两套):连续
            # PREP_NO_PROGRESS_ROUNDS 个备战环「状态指纹零推进」→ 存证
            #(截图+flag)→ 出战臂或 stop_running。计数键 = 状态指纹单键
            #(相位真值;动作批振荡不再穿透计数——T-167 事故的交替活锁
            # 引擎),动作批 = 窗口并集累积器留证 + 臂判别。动作批签名 =
            # CwScreenPrep 上一环 decide 输出的动作类型序列
            #(session.last_prep_action_sig,备战单轮 op 写);None(overlay
            # 交回/策略异常/破墙派生帧前)在共同出口归零计数与并集
            #(ADR-0554 修订节第 3 条:overlay 垄断形态维持哨兵档)。不误伤依据:
            # ①战斗等待期不进本分支(备战双锚不命中),且回备战时 round 必变
            #  → 指纹变 → 归零;
            # ②正常多帧部署:每次成功动作改变 bench/deployed 身份或 gold
            #  → 指纹变 → 归零;
            # ③闩跳过帧:动作批不同不再归零(F2 语义变更)——恒指纹下的
            #  振荡 = 忙而无功,恰是本守卫要捕的形态(T-167 事故定谳);
            #  gold 分量按开态可信帧钉死,关店帧噪声不归零(ADR-0554 修订节第 5 条)。
            _np_actions = getattr(exec_state_of(self.ctx.cw_match.session),
                                  'last_prep_action_sig', None)
            _np_fp = prep_no_progress_state_fingerprint(
                self.ctx.cw_match.session)
            if _np_actions is None:
                self._prep_np_sig = None
                self._prep_np_count = 0
                self._prep_np_actions = frozenset()
            else:
                self._prep_np_sig, self._prep_np_count, self._prep_np_actions = \
                    prep_no_progress_tick(
                        getattr(self, '_prep_np_sig', None),
                        getattr(self, '_prep_np_count', 0),
                        getattr(self, '_prep_np_actions', frozenset()),
                        _np_fp, _np_actions)
            # 守卫计数归零共同出口(None 交回环 / 状态指纹推进,F2 单键):
            # 收益耗尽臂总尝试计数同步归零——新冻结情节从零起算,总限只辖
            # 单一冻结情节(ADR-0554 双限防线)。归零必须在共同出口:只挂
            # tick 分支会漏 None 路径,跨情节残留计数会让新情节提前总限
            # giveup(三审后补必修1)。界定重推(ADR-0554 修订节第 4 条,F2 迁移后):旧键下
            # 「情节」= 同动作批 ∧ 同指纹持续期;新键下 = 同指纹持续期
            #(较旧更短或等长,归零频率上升)——总限预算(2×守卫阈值)在
            # 每个恒指纹情节内重置,跨情节残留不可能,单情节内发射预算
            # 不变量保持;动作批振荡不再触发归零(这正是 F2 要捕的形态,
            # 振荡情节内总限照常累计,交错自旋防线语义增强)。
            if self._prep_np_count == 0:
                self._cw_exhaust_attempts = 0
            if self._prep_np_count >= self.PREP_NO_PROGRESS_ROUNDS:
                # 备战收益耗尽 → 出战臂(ADR-0554;F2 判据放宽,T-167):
                # 恒指纹窗口动作批并集 ⊆ {OpenShop, RunDeploy} ∧ 末批
                # RunDeploy ∧ 上环 success 的形态不属执行面卡死,停机只会
                # 烧掉不可复现的对局预算——备战等待零收益(机制依据见判据
                # docstring),出战支配性优于等待。发射核与达标臂共用
                # readiness_battle_launch(C1 单一发射函数);失败连击
                # 达 3 放弃短路回落守卫停机(与达标臂防线 C1 同构)。
                if prep_exhaustion_launch_eligible(
                        _np_actions, getattr(self, '_prep_last_success',
                                             None),
                        getattr(self, '_prep_np_actions', frozenset())):
                    # 排除族(F2 边界,单一源 = prep_exhaustion_exclusion_
                    # reason):补给节点(出战不推进,正确出口是补流程)/
                    # 奖励节点滞留球(见该函数 docstring 实机观测项)——
                    # 命中不出战,维持守卫停机(交留证判读)。
                    _exh_excl = prep_exhaustion_exclusion_reason(
                        self.ctx, screen)
                    if not _exh_excl:
                        # 双限防线②·总尝试限(ADR-0554 三审定稿):交错
                        # 序列可让 fail/stale 两个同型连击计数器互复位
                        # 永不达限 = 无界自旋复活(三审定谳「治本缺半」)
                        # → 总尝试上限 = 2 × PREP_NO_PROGRESS_ROUNDS
                        # (任一结果累计)兜底。推导:结果三型(success/
                        # fail/stale)中任一型连续 3 即停,总限只在三型
                        # 均不连续达 3 时生效——最小交错周期 2(两型交替),
                        # 6 次 = 3 个完整交错周期,足以证「持续无法发射」
                        # 而非偶发交错;量纲 = 2 倍守卫停机环预算,零新
                        # 拍定值(派生自守卫常量)。
                        _xa = getattr(self, '_cw_exhaust_attempts', 0) + 1
                        self._cw_exhaust_attempts = _xa
                        _exh_over_cap = (_xa >
                                         self.PREP_NO_PROGRESS_ROUNDS * 2)
                        if _exh_over_cap:
                            self._cw_exhaust_attempts = 0
                            _exh_m = getattr(self.ctx, 'cw_match', None)
                            _exh_counters = getattr(
                                strategy_state_of(_exh_m.session)
                                if _exh_m is not None else None,
                                'cw4_counters', None)
                            if isinstance(_exh_counters, dict):
                                _exh_counters[
                                    'exhaustion_launch_total_giveup'] = \
                                    _exh_counters.get(
                                        'exhaustion_launch_total_giveup',
                                        0) + 1
                            log.error('[cw!][loop] 收益耗尽臂总尝试达上限 '
                                      '%d(同型连击未达但交错持续)→ 放弃'
                                      '发射,回落守卫停机',
                                      self.PREP_NO_PROGRESS_ROUNDS * 2)
                            # 不 return:落穿到下方守卫停机留证
                        else:
                            _ex_m = getattr(self.ctx, 'cw_match', None)
                            _ex_counters = getattr(
                                strategy_state_of(_ex_m.session)
                                if _ex_m is not None else None,
                                'cw4_counters', None)
                            _ex_c = (_ex_counters
                                     if isinstance(_ex_counters, dict)
                                     else None)
                            if _ex_c is not None:
                                _ex_c['exhaustion_battle_launch'] = \
                                    _ex_c.get('exhaustion_battle_launch',
                                              0) + 1
                            _ok_x, _detail_x = readiness_battle_launch(
                                self, self.ctx)
                            if _detail_x == 'readiness_stale_screen':
                                # 屏态过期(过渡帧):单帧不停机(无执行面
                                # 卡死证据,交回下轮重判)。同型自旋上限 3:
                                # 连续 stale 达限放弃回落守卫停机;发射
                                # 成功/失败即复位——持续 stale = 发射核
                                # 无法工作,同属需留证的结构性形态。选独立
                                # 上限而非「落回守卫链」:本臂位于守卫触发
                                # 位内侧,落回=立即停机,会把偶发过渡帧误升
                                # 停机(语义不对齐)。stale 同时复位失败
                                # 连击(反之亦然):「连续」辖同型结果。
                                self._cw_exhaust_fail_n = 0
                                _xs = getattr(self, '_cw_exhaust_stale_n',
                                              0) + 1
                                self._cw_exhaust_stale_n = _xs
                                if _xs >= 3:
                                    self._cw_exhaust_stale_n = 0
                                    if _ex_c is not None:
                                        _ex_c['exhaustion_launch_stale_giveup'] = \
                                            _ex_c.get(
                                                'exhaustion_launch_stale_giveup',
                                                0) + 1
                                    log.error('[cw!][loop] 收益耗尽臂连续 %d 次'
                                              '屏态过期(readiness_stale_screen)'
                                              '→ 放弃重试,回落守卫停机', _xs)
                                    # 不 return:落穿到下方守卫停机留证
                                else:
                                    log.info('[cw-loop] 收益耗尽臂屏态过期'
                                             '(第 %d/3 次)交回下轮重判', _xs)
                                    return self.round_wait(wait=1.0)
                            elif _ok_x:
                                self._cw_exhaust_fail_n = 0
                                self._cw_exhaust_stale_n = 0
                                self._cw_exhaust_attempts = 0
                                self._battle_ts = time.monotonic()  # ADR-0250
                                self._battle_wait_active = True
                                log.info('[cw-loop] 备战收益耗尽(连续 %d 环 '
                                         '状态指纹零推进,窗口动作批并集 %s ∧ '
                                         '末批 RunDeploy)→ 出战: %s',
                                         self._prep_np_count,
                                         sorted(getattr(
                                             self, '_prep_np_actions',
                                             frozenset())) or '空',
                                         _detail_x)
                                return self.round_wait(wait=3)
                            else:
                                self._cw_exhaust_stale_n = 0
                                _xf = getattr(self, '_cw_exhaust_fail_n',
                                              0) + 1
                                self._cw_exhaust_fail_n = _xf
                                if _ex_c is not None:
                                    _ex_c['exhaustion_launch_fail'] = \
                                        _ex_c.get('exhaustion_launch_fail',
                                                  0) + 1
                                if _xf >= 3:
                                    self._cw_exhaust_fail_n = 0
                                    if _ex_c is not None:
                                        _ex_c['exhaustion_launch_giveup'] = \
                                            _ex_c.get(
                                                'exhaustion_launch_giveup',
                                                0) + 1
                                    log.error('[cw!][loop] 收益耗尽臂连续 %d 次发射失败'
                                              '(最后一次: %s)→ 放弃短路,回落守卫停机',
                                              _xf, _detail_x)
                                else:
                                    log.warning('[cw!][loop] 收益耗尽臂发射失败'
                                                '(第 %d/3 次,%s)→ 下环重试',
                                                _xf, _detail_x)
                                    return self.round_wait(wait=3)
                try:
                    _np_shot = self.save_screenshot(prefix='prep_no_progress')
                except Exception:  # noqa: BLE001  留证失败不拦停机(flag 是主哨兵)
                    _np_shot = ''
                try:
                    write_no_progress_flag(
                        self._prep_np_count, _np_fp, _np_shot)
                except Exception as e:  # noqa: BLE001  flag 失败仍停机(日志留证)
                    log.warning('[cw-loop] 无进展守卫 flag 写入失败: %s', e)
                log.error('[cw!][loop] 环级无进展守卫:连续 %d 个备战环状态'
                          '指纹零推进(F2 单键)→ 停机留证(末环动作批 %s ∧ '
                          '窗口动作批并集 %s;flag=prep_no_progress.flag '
                          'shot=%s)',
                          self._prep_np_count, list(_np_actions),
                          sorted(getattr(self, '_prep_np_actions',
                                         frozenset())) or '空', _np_shot)
                self.ctx.run_context.stop_running(
                    reason='hook:prep_no_progress')
                return self.round_fail(
                    status='备战环无进展守卫触发(状态指纹连续'
                           f'{self._prep_np_count}环零推进),停机留证')
            # 备战被锁(顶部「返回投资策略选择」按钮)→ 点去选策略(check#4 接手)。
            # 2026-08-26 挪位(原在备战判定前全屏扫):用户定性该按钮出现 = 上游
            # 投资策略屏处理失败的 symptom(策略屏点歪才退回备战带此按钮;同族 =
            # 补给/遭遇屏的「返回XX选择」)→ 先确定是备战画面(双锚)
            # 再特殊处理,顺带免掉每帧全屏 OCR。lcs_percent=0.9 保留:防与
            # 「请选择投资策略」共享「选择投资策略」(6/8=0.75=默认阈值之上)误匹配
            # → 投资策略屏被吞(点标题不动作)→ 死循环(2026-08-04 实跑,卡 plane1)。
            # 真「返回投资策略选择」按钮 OCR 1.0 不受影响。
            if self.round_by_ocr_and_click(screen, '返回投资策略选择', success_wait=2, lcs_percent=0.9).is_success:
                self._cw_back_btn_count += 1
                log.warning('[cw!][loop] 返回按钮=上游选择屏处理失败症状(策略屏点歪),第%d次',
                            self._cw_back_btn_count)
                return self.round_wait(wait=2)
            # 接管局补采(boss+词缀)已迁 CwScreenPrep(W971 §2.1/01-opening §2.1:
            # 稳定门退役后挂点 = 干净备战观察;见 cw_screen_prep._run_loop 采集块)。
            # (策略失活早停块已随 decisions 流写入端退役删除——删除波 1:
            #  心跳决策行停写后新局恒「零心跳行」,检查保留 = 误杀每一局;
            #  消费面、数据源与离线失活判据族同批封闭退役,现役防线 =
            #  哨兵 journal 面断流探测(skills 侧 cw_sentinel)。)
            # 迁移审计 w62(git 历史) 件1(ADR-0329):恢复局(locked-resume)检测与直接出战。
            # 判据(设计章1.2)= 新 match(无本局记录)+ 首个备战相位 round>1 → 候选;
            # 一次「点商店→验收起」探针(章1.3)区分锁定/未锁(锁定唯一可观测特征
            # =商店按钮零响应);锁定态跳过全部备战交互直接出战(复用 StartBattle
            # 执行体,内含未达上限确认),出战成功即解除(章1.5)。误判防线:候选
            # 撤回(1-1 正常新局)/探针可开(非锁定)两处都不进锁定分支。
            if self._cw_resume_candidate:
                _pr = read_phase_round(self.ctx, screen)
                if not resume_candidate(self._is_new_match, _pr[0], _pr[1]):
                    self._cw_resume_candidate = False   # 1-1 正常新局,撤回候选
                else:
                    self._mark_session_resumed()   # D2:恢复局旗标(弹窗腿禁用供给面)
                    self.round_by_find_and_click_area(
                        screen, '货币战争-备战', '按钮-商店', success_wait=1.2)
                    _opened = self.round_by_find_area(
                        self.screenshot(), '货币战争-备战-开商店', '按钮-收起',
                        crop_first=False).is_success
                    self._cw_resume_candidate = False
                    if probe_resolve(_opened) == 'normal':
                        # 非锁定(误判防线):收起关店,清候选 → 落常规 CwScreenPrep
                        self.round_by_find_and_click_area(
                            self.screenshot(), '货币战争-备战-开商店', '按钮-收起',
                            success_wait=1.0)
                        log.info('[cw-loop] 恢复候选但商店可开 → 非锁定,走常规')
                    else:
                        self._cw_locked_resume = True
                        self._cw_locked_round = _pr[1]
                        self._cw_locked_sync_done = False   # 新锁定局:首战前同步步待执行
                        log.warning('[cw!][loop] 恢复局锁定确认(P%s-r%s,商店探针'
                                    '零响应)→ 直接出战', _pr[0], _pr[1])
            if self._cw_locked_resume:
                # 首战前备战同步步 + StartBattle(组合封装,见函数 docstring;
                # 同步步每锁定局恰一次,证据位 _cw_locked_sync_done)。
                progressed, detail = locked_resume_sync_and_battle(self, self.ctx)
                if progressed:
                    self._cw_locked_resume = locked_after_start_battle(progressed)
                    self._battle_ts = time.monotonic()   # ADR-0250:战斗窗口开
                    self._battle_wait_active = True   # 战斗窗口 → 下轮委托 CwScreenBattleWait
                    log.info('[cw-loop] 锁定恢复局 → 出战成功,锁解除(恢复正常循环)')
                    # (exec_events 发射事件行与流程心跳载体行已随 decisions/
                    #  exec_events 流写入端退役删除——删除波 1。)
                    return self.round_wait(wait=3)
                log.warning('[cw!][loop] 锁定模式出战未落地(%s)→ retry(保锁定)',
                            detail)
                return self.round_retry(wait=2)
            # 过渡门说明(r7 review P0-B):0e 系分支(上方)先于本分支检查同截图同三元组(id_mark
            # 位置判),OCR 按 id(image) 缓存 → 到达此处时 overlay 检查必全 False——旧「半开帧
            # 等 1.2s」门为不可达死码,已删;其继任者 = 上方子态稳定门(连续 3s,非同帧检查)。
            # 可控轮数:已跑完 max_rounds 轮 → 停备战屏(可 analyze board/star + star 钩子采样本),不跑备战单轮。
            if self._max_rounds is not None and self._settle.rounds_done >= self._max_rounds:
                log.info('[cw-loop] max_rounds=%s 已跑 %s 轮 → 停备战屏(单/多轮验证)',
                         self._max_rounds, self._settle.rounds_done)
                return self.round_success(
                    f'已跑 {self._settle.rounds_done} 轮停备战(达 max_rounds={self._max_rounds})')
            # 补给节点(nodeseq 当前节点类型=supply):出战不推进(无出战打怪,确认补给即完成节点进下回合,
            # live 确认 2026-08-13)→ 点「返回补给阶段」进补给屏,下轮 Loop 0e 分支 CwScreenSupplyNode 选+确认。
            # ⚠️ 用 nodeseq 节点类型判,非「返回补给阶段」按钮 —— 该按钮 battle 节点也在(可 revisit),不可靠
            # (2026-08-13 实跑:1-6 battle 节点出战成功 + 也有该按钮)。nodeseq 读失败(非 clean 帧)→ 不 divert
            # (默认备战分支,保险不误判 battle 为 supply)。
            _cur_slot = next((s for s in (read_node_sequence(self.ctx, screen) or [])
                              if s.state == 'current'), None)
            if _cur_slot is not None and _cur_slot.node_type == 'supply':
                self.round_by_find_and_click_area(screen, '货币战争-备战', '按钮-返回补给阶段', success_wait=2)
                log.info('[cw-loop] 补给节点(nodeseq current=supply)→ 点返回补给阶段 进补给屏(下轮 CwScreenSupplyNode)')
                return self.round_wait(wait=2)
            # r332(批次3/终审①③:cw_loop 消费返回值——
            # 旧版忽略 execute() 结果 → director 失败后下轮
            # 无条件重派新实例(实例计数清零)= 无限 ping-pong
            # (Y-1c/D-2.3 七轮 review 实证)。修:连续 N 次失败
            # →告警+视为停滞(交 stall 哨兵/unknown 兜底链),
            # 不再无限静默重派。
            # ⚠ 语义澄清(review 第9条):round_fail 在本节点
            # node_max_retry_times=400 下**不停机**——刻意:
            # 消除的是「静默」(无日志)而非「重试」;warning 进
            # 日志 = 哨兵(SENTINEL-HIT 检 [cw!])与人都能看到,
            # 停机决策留给观察者(对拍期不想因 gate bug 硬停局)。
            # T-176 V-2 收编:备战分支派发前的试用揭示卡/书册卡清场识别+点击
            # 已迁 CwScreenPrep 环入口清场段(``_clear_prep_cards``,与
            # ENTRY_OVERLAY_CLOSE 一键关注册表同位)——外循环只保留画面识别
            # 分派,识别机制不出分发层(设计 §3.4 过渡相位件收编挂账兑现;
            # 书册卡处理链经 journal 包装保 op 行,先例 = 本文件 0k 分支)。
            def _on_prep_round(ok: bool, res: Any) -> OperationRoundResult | None:
                # 备战环出口 success 记录(收益耗尽判据输入,ADR-0554):RunDeploy
                # 发射契约下 success 含 STATUS_NOOP 合法稳态,fail = 执行面失败。
                self._prep_last_success = ok
                if not ok:   # 迁移审计 w68(git 历史):OperationResult 无 __bool__,
                    # bool(FAIL)=True——裸 not _ok 恒 False,r332 停滞守卫成死码
                    # (验证局 206 次崩溃-重派无限循环实录);success 才是判据。
                    self._director_fail_streak = getattr(
                        self, '_director_fail_streak', 0) + 1
                    if self._director_fail_streak >= 5:
                        log.warning('[cw!][loop] CwScreenPrep 连续 %d 次失败'
                                    '(gate/环异常?)→ 本轮按未知画面处理'
                                    '(哨兵/兜底链接管)', self._director_fail_streak)
                        return self.round_fail('CwScreenPrep 连续失败(停滞)')
                else:
                    self._director_fail_streak = 0
                    # 正常备战环跑完一轮 = 部署链健康 → 0j 恢复链重试预算复位
                    #(预算只辖「前台无角色→重部署」连续失败窗,非整局总量)。
                    # F3/T-174(ADR-0610)复位条件收紧:StartBattle 发射但
                    # 内部发射事实为 False 的环在外循环仍记 round_success
                    #(发出即终结交回)——1-1 冻结局实证该形态每环误复位预算
                    #(两次显示 (1/2)),预算形同虚设、唯一止住循环的是环级
                    # 守卫。故「发射但 False」不复位;「本环未发射」(None)
                    # 或发射 True 才复位。读后即清防跨环残留。
                    _prep_sess = (self.ctx.cw_match.session
                                  if self.ctx.cw_match is not None else None)
                    _launch_ok = getattr(
                        exec_state_of(_prep_sess),
                        'last_prep_battle_launch_ok', None)
                    if _launch_ok is not False:
                        self._frontless_redeploy = 0
                    exec_state_of(_prep_sess).last_prep_battle_launch_ok = None
                    # ADR-0250:备战环经出战出口 → 战斗窗口开(watch 宽限计时起点)
                    self._battle_ts = time.monotonic()
                    # 环出口含出战 → 战斗窗口驻留闩置位(下轮委托 CwScreenBattleWait;
                    # 环入口分诊交回/bail 的返回由下轮重判自然分流——非出战返回帧
                    # 仍是备战画面,委托入口的帧锚不命中,闩却会错误置位?否:
                    # 闩只表达「出战已发射」,CwScreenBattleWait 对非战斗帧走宽限等待,
                    # 白名单锚(备战双锚单锚宽判定)命中即 success 交回,零风险)。
                    self._battle_wait_active = True
                # 环让位重入契约(W971 §2.9,实机 P1-r6 bail ping-pong 修复):
                # director 返回(含环入口分诊交回/事件 overlay bail)后**必经本
                # return → 下轮 loop 顶全分支重判**(0x overlay 分支先于备战双锚),
                # 不在同一迭代内直接回备战分支/环。日志留痕 = 重入可观测
                #(此前 bail↔重派静默,排障无从分辨「没重判」vs「判了没接住」)。
                log.info('[cw-loop] 备战环返回(success=%s status=%s)→ 交回顶层分发'
                         '(下轮全分支重判)', ok, getattr(res, 'status', '') or '')
                return None   # 默认映射 round_wait(1.0) = 下轮重新识别分发

            return self._dispatch_screen_op(
                CwScreenPrep(self.ctx), journal_name='备战',
                frame_tag='flow_prep_entry', wait=1.0, on_result=_on_prep_round)

        # 1b. 详情弹窗(点卡/点角色触发的:可合成列表祝福详情 / 角色详情角色
        #     信息)→ 点面板外空白关闭。判据(T-163 锚化)= archive 双锚其一
        #     (_role_detail_anchor_hit 判据单一源:装备推荐 ∨ 合成公式)——
        #     旧全屏 OCR「可合成列表」∨「角色详情」(lcs 0.8)退役:全屏
        #     「角色详情」与商店卡牌详情弹窗底部按钮全等共享(LCS 1.0)→
        #     T-163 弹窗被本分支垄断 26 分钟(outer_loop.md §2.1 存量欠账)。
        #     序位在备战后不变(右侧面板锚区被大面板帧独占,与 0t 双锚天然互斥)。
        if _role_detail_anchor_hit(self, screen):
            # 锚化判定留外循环(序位不变);空白关+验效迁 op(T-163 D3)。
            # on_fail_retry 同 0a2/0a3/0a4/0t(落地审 F2):op 单尝试 fail
            # 映射 loop 级 round_retry 消费 retry 池,否则零预算重派。
            return self._dispatch_screen_op(
                CwScreenRoleDetailOverlay(self.ctx), journal_name='详情弹窗',
                frame_tag='overlay_role_detail', wait=1.5,
                on_fail_retry=True)

        # 1d. 星徽详情弹窗(2026-08-17 M53 停机建档:「XX星徽套组」标题 + 流派星徽类型 + 效果/
        #     适配角色/合成公式面板;点球/装备操作误点开星徽图标的详情)。点右上 X 关回备战。
        #     不用 ESC(bug#2:面板已关时 ESC 落备战弹中断挑战);X 是弹窗内坐标永远安全。
        if (self.round_by_find_area(screen, '货币战争-星徽详情', '标识-流派星徽', crop_first=False).is_success
                or self.round_by_find_area(screen, '货币战争-星徽详情', '标识-套组标题', crop_first=False).is_success):
            # 双锚判定留外循环;点X 关迁入 op(「不用 ESC」理由随迁 op 注释,禁顺手统一)
            return self._dispatch_screen_op(
                CwScreenEmblemDetailPopup(self.ctx), journal_name='星徽详情',
                frame_tag='overlay_emblem_detail', wait=1.5)

        # 1g. 中断挑战 dialog(bug#2:ESC 误按/误点左上角弹「是否中断挑战」,历史 3 次实锤;
        #     2026-08-17 建档「货币战争-中断挑战弹窗」,替原停机钩子)。真模态、点遮罩无效;
        #     出口:ESC / 右上X 关回备战(无副作用)。bot 策略 = 点右上 X 关闭继续对局
        #     (不点「暂时离开」免中断对局,绝不点「放弃并结算」——不可逆放弃进度)。
        #     弹窗内「小队生命值」为 HP 真值快照,顺带对账(备用,暂不消费)。
        if self.round_by_find_area(screen, '货币战争-中断挑战弹窗', '标识-中断挑战',
                                   crop_first=False).is_success:
            # 真 modal:绝不点「放弃并结算」(语义红线随迁 CwScreenInterruptDialog);
            # exogenous popup 行随 op 迁移;X 失败兜底 ESC 同迁
            return self._dispatch_screen_op(
                CwScreenInterruptDialog(self.ctx), journal_name='中断挑战弹窗',
                frame_tag='overlay_interrupt_dialog', wait=1.5)

        # 战斗/结算窗口 → CwScreenBattleWait(W971 05-battle §1:原 1f/2/3/3b/5/6
        # 内联分支收编;三段式 = 等结算画面 / 结算处理(遥测读点 + 点继续挑战)
        # / 完成判据白名单;团灭终局分叉(多页 → 返回货币战争 → 大厅)交回本
        # 循环 3c 收口——runs summary/分配器/存档写端不随 op 化迁移,遥测
        # 连续性红线)。双入口:①出战驻留闩(出战成功置位);②帧锚(接管局/
        # relaunch 残留结算屏,等价旧「战斗中帧直接落 1f/2/3 分支」语义)。
        # op 返回后必经本 return → 下轮 loop 顶全分支重判(环让位重入契约)。
        if (self._battle_wait_active
                or self._frame_in_battle_window(screen)):
            self._settle.battle_ts = self._battle_ts

            def _on_battle_wait(ok: bool, res: Any) -> None:
                # ADR-0250:op 内已见结算屏 → 战斗窗口关(watch 恢复)。
                # 出口归一:白名单命中/终局/bail 都清闩(窗口单元结束);bail 帧
                # 交未知画面兜底链(超时兜底语义,裁决权留外循环)。
                # 时序申报(ADR-0584 §2.3):闩清原在 journal exit 之后,现随
                # 回调提前到 exit 前——journal exit 行不含闩状态、闩清只影响
                # 下轮分发,该时序微差无观察面,收敛等价。
                if self._settle.saw_settlement:
                    self._battle_ts = None
                self._battle_wait_active = False
                log.info('[cw-loop] 战斗等待返回(success=%s status=%s)→ 交回顶层分发'
                         '(下轮全分支重判)', ok,
                         getattr(res, 'status', '') or '')

            # settle 注入/窗口关/闩清 = 战斗宽限守卫域(ADR-0250),留外循环回调
            return self._dispatch_screen_op(
                self._battle_wait, journal_name='战斗等待',
                frame_tag='flow_battle_wait', wait=1.0, on_result=_on_battle_wait)
        # 3c. 回到大厅(对局结束)→ loop 完成,避免在 lobby 无动作无限 retry。
        # 用「创业指南」(大厅左菜单独有、无特殊括号,OCR 稳)而非「开始「货币战争」」(括号 gt 不稳)
        # (W971 05-battle §1:团灭终局链的终点由 CwScreenBattleWait 终局分叉交回此处
        # 收口——runs summary/分配器/存档/match 清理写端不随 op 化迁移。)
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:

            def _lobby_return_step() -> OperationRoundResult:
                # r10 假局守卫:本 loop 从未记过 round_outcome(未打过任何一回合)却见大厅
                # = 开局失败/中断(第四局实证:开局失败回大厅 → 用旧 session 拼假 loss,
                # final_hp=100/rounds=2 全污染)。不记 summary、不喂分配器,仅清理 match。
                if self._settle.last_outcome_hp is None and self._settle.rounds_done == 0:
                    log.warning('[cw][loop] 开局阶段即回大厅(无任何 round_outcome)→ 判开局失败,不记假 summary')
                    self.ctx.cw_match = None
                    return self.round_success('开局失败/中断(未产生对局数据,不记 summary)')
                if self.ctx.cw_match is not None:
                    # B4(ADR-0170 telemetry 接线):终局真实数据灌 MatchOutcome(原桩全默认)——
                    # won=回大厅即本局结束;plane/round/hp 取 session 容器单例
                    # (观察漏斗/结算覆盖链刷新的记录;last_state 槽随链退役
                    # 批删除换源;⚠️ CurrencyWarMatch 无 state 字段——review
                    # 子代理 P0 实锤,勿写 cw_match.state)。hp 语义随换源
                    # 修正申报:旧帧沿用 hp(带门控/兜底形态)→ 容器 hp
                    # (结算覆盖真值,apply_settlement_cover 置信门写入)——
                    # 跨局分配输入更贴真实终局血量。喂跨局分配器(0170,分级
                    # 奖励);生命周期钩子 on_match_end 已随 ADR-0583 收编删除
                    #(原实现 = P1 no-op,零行为)。
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        board_state_of,
                        plane_of,
                        round_num_of,
                        write_match_final,
                    )
                    _bs = board_state_of(self.ctx.cw_match.session)
                    _observed = _bs.node.value is not None
                    # ⚠️ 假 win 守卫(2026-08-17 M70 事故):won 曾用 `plane >= 3`——恢复对局时 plane
                    # 被 OCR 读成 8(A8 难度泄漏)→ 8>=3 → 假通关进遥测。现要求 **plane==3 精确值**
                    # (值域守卫已在上游拒 8,此处双保险);且死局(本局见过战败结算屏)不判 win。
                    _died_this_run = self._settle.saw_defeat_settlement
                    _final_plane = plane_of(_bs) if _observed else 1
                    _final_round = round_num_of(_bs) if _observed else 1
                    _bs_hp = _bs.hp.value
                    _outcome = MatchOutcome(
                        won=(_final_plane == 3 and not _died_this_run),
                        final_plane=_final_plane,
                        final_round=_final_round,
                        final_hp=(_bs_hp if _bs_hp is not None else 0),
                    )
                    self._allocator_update(_outcome)
                    # match_final 局终收口行(W3 在线接线,W2 落地审 §⑤
                    # 遗留义务;runs 断流探测与判读的唯一收口证据源):
                    # 在线判定面单一源 = resolve_final_type(判定序
                    # 停止>败局>plane==3 精确值>abnormal,与本地 won 判定
                    # 同口径);写口自带段内幂等查重(G12),best-effort
                    # 不阻塞收口流转。先于 close_run(行 ts 落局时间窗)。
                    try:
                        from sr_od.application.currency_war.obs.cw_observation import (
                            resolve_final_type,
                        )
                        _mf_type = resolve_final_type(
                            stop_requested=bool(getattr(
                                self.ctx.run_context, 'is_context_stop',
                                False)),
                            saw_defeat=_died_this_run,
                            plane_reached=_outcome.final_plane,
                            rounds_played=True)
                        if _mf_type is not None:
                            write_match_final(
                                _bs, final_type=_mf_type,
                                plane=_outcome.final_plane,
                                round_num=_outcome.final_round,
                                hp=(_outcome.final_hp
                                    if _outcome.final_hp else None),
                                gold=(_bs.gold.value if _observed else None),
                                streak=(_bs.streak.value if _observed else None),
                                # 策略行为观测计数局终聚合(R5 W4 键收编
                                # 载体;收口时点现读快照,先于 close_run)。
                                cw4_counters=self._cw4_counters_snapshot(
                                    self.ctx.cw_match.session),
                                note='online:lobby_return')
                    except Exception as e:   # noqa: BLE001  观测旁路
                        log.warning('[cw][loop] match_final 收口行写入失败'
                                    '(不阻塞): %s', e)
                    # run 收口(删除波 1:runs summary 写行随旧流写入端退役;
                    # close_run 零落盘,置跨局 run_id 重铸位)。B4 的 outcome
                    # 真值同源喂分配器;局终元数据 journal 归宿 = 局终域
                    # match_final 行(上方 W3 在线接线)。
                    state.close_run(
                        result='win' if _outcome.won else 'loss',
                        plane_reached=_outcome.final_plane,
                        rounds_survived=_outcome.final_round,
                        final_hp=self._last_true_hp(_outcome.final_hp),
                        notes='auto')
                    # (GameState 局终归档调用点已随 W7 写点退役删除——
                    #  归档只读声明见 _write_terminal_summary_if_needed。)
                    self._summary_written = True
                    # 按局存档装配(终局旁路,零运行时侵入):挂在局终收口
                    #(原 on_match_end 调用点之后同一生命周期;该钩子已随
                    # ADR-0583 收编删除);只读 replay/*.jsonl 写 matches/,
                    # 不碰任何内存态/决策路径,失败不阻塞局终收口。
                    try:
                        from sr_od.application.currency_war.telemetry import (
                            match_archive,
                        )
                        match_archive.assemble_pending(
                            state.get_recorder().replay_dir)
                    except Exception as e:   # noqa: BLE001  观测旁路,best-effort
                        log.warning('[cw][archive] 局终装配失败(不阻塞): %s', e)
                    self.ctx.cw_match = None
                return self.round_success('对局结束,回大厅')

            # C2(ADR-0584 §1.3):收口面非推进画面,runs summary/分配器/存档
            # 写端不随 op 化迁移(遥测连续性红线);本批只接包装补
            # op='回大厅收口' 行,链体零改(链形透传,轮次结果即分支出口)。
            return self._dispatch_screen_op(
                _lobby_return_step, journal_name='回大厅收口',
                frame_tag='flow_lobby_return', wait=1.0)

        # 5. 前进按钮(简报等):OCR 判定留外循环,点击迁入 op(无验效)
        if self.round_by_ocr(screen, '下一步').is_success:
            return self._dispatch_screen_op(
                CwScreenNextButton(self.ctx), journal_name='前进按钮',
                frame_tag='flow_next_button', wait=1.5)

        # 兜底(M43-resume 修复 2026-08-16):所有分支不命中 → 停机钩子(streak 累计/保画面停机)。
        # 此前钩子代码被 _allocator_update 插错位置卷进方法体(从未执行)→ loop 隐式返 None。
        return self._handle_unknown_fallback()

    # ===== B4(ADR-0170):终局喂分配器(影子期:只记后验不改选臂;分级奖励+adherence) =====
    def _allocator_update(self, outcome: MatchOutcome) -> None:
        """终局 update:臂 = 终局 target_comp 名(adherence 近似 1;开局臂双列待 v1)。"""
        if self._allocator is None or self.ctx.cw_match is None:
            return
        try:
            arm_obj = getattr(strategy_state_of(self.ctx.cw_match.session), 'target_comp', None)
            comp_name = getattr(arm_obj, 'name', '') if arm_obj is not None else ''
            # 57-A1 修(臂命名空间):臂表键 = plaza carry 角色名,update 侧是 comp 阵容名
            # → 恒 no-op(62 局零累积实证)。comp→carry 归一映射(comp.plaza_carry)。
            arm_id = ''
            if comp_name:
                from sr_od.application.currency_war.kernel.cw_comps import get_comp
                _c = get_comp(comp_name)
                arm_id = getattr(_c, 'plaza_carry', '') or ''
            if not arm_id or arm_id not in self._allocator.arms:
                return
            reward = self._allocator.reward_graded(
                outcome.won, outcome.final_plane, rounds=outcome.final_round)
            self._allocator.update(arm_id, reward, adherence=1.0)
            log.info('[cw-alloc] 终局 update: arm=%s won=%s plane=%s reward=%.2f → mean=%.3f',
                     arm_id, outcome.won, outcome.final_plane, reward,
                     self._allocator.arms[arm_id].mean)
        except Exception as e:   # noqa: BLE001  影子期失败安全
            log.info(f'[cw-alloc] update 失败(跳过): {e}')

    def _frame_in_battle_window(self, screen) -> bool:
        """帧锚:当前帧是否战斗/结算窗口画面(CwScreenBattleWait 第二入口)。

        覆盖接管局/relaunch 残留结算屏场景(闩未置位但画面已在战斗/结算窗
        口,等价旧「战斗中帧直接落 1f/2/3 分支」语义)。锚集 = 战斗/结算
        独有信号:继续挑战按钮/败局页模板/数据统计锚/点击空白加速/总伤害/
        前往结算·返回货币战争(终局链按钮,lcs 0.9 防「返回备战界面」子序列
        误匹配——同 3b 旧判据理由,lcs 收紧由位置唯一性兜底)。简报「下一步」
        不列(与终局链共享词形,误激活代价 = 白跑一窗口,宁缺勿造)。
        """
        return (
            self.round_by_find_area(screen, '货币战争-结算', '按钮-继续挑战',
                                    crop_first=False).is_success
            or self.round_by_find_area(screen, '货币战争-结算-失败', '标识-挑战结束',
                                       crop_first=False).is_success
            or self.round_by_find_area(screen, '货币战争-结算', '标识-数据统计',
                                       crop_first=False).is_success
            or self.round_by_ocr(screen, '点击空白加速').is_success
            or self.round_by_ocr(screen, '总伤害').is_success
            or self.round_by_ocr(screen, '前往结算', lcs_percent=0.9).is_success
            or self.round_by_ocr(screen, '返回货币战争', lcs_percent=0.9).is_success
        )

    def _handle_unknown_fallback(self) -> OperationRoundResult:
        """[常驻兜底] loop 尾未知画面安全网(hook审计 S5/r351 分类修正:
        触发条件=「loop 尾所有分支不命中」= 兜一切未知的常驻安全网,
        **不是临时随机态钩子**——按临时写有误删风险;移除条件=该类
        未知态全部建档,实际不可达,长期保留)。方案 D,M43-resume 修复
        2026-08-16:战斗特效帧 OCR 乱码/新未建档画面 → streak 累计 →
        保画面停机待建档。曾被 _allocator_update 插入位置错误卷进方法体
        (从未执行)→ loop 隐式返 None(19:59 实锤)。
        """
        if getattr(self, '_unknown_last_iter', -1) == self._iter - 1:
            self._unknown_streak = getattr(self, '_unknown_streak', 0) + 1
        else:
            self._unknown_streak = 1
        self._unknown_last_iter = self._iter
        if self._unknown_streak >= CwLoop.UNKNOWN_STOP_THRESHOLD:
            try:
                _shot = self.save_screenshot(prefix='cw_unknown')
                _sentinel = (get_project_root() / '.debug' / 'temp'
                             / 'currency_war' / 'unknown_state.flag')
                _sentinel.parent.mkdir(parents=True, exist_ok=True)
                _sentinel.write_text(
                    f'[HOOK-STOP] 持久未识别画面停机钩子([常驻兜底] loop 尾安全网):'
                    f'cw_loop._handle_unknown_fallback iter={self._iter} '
                    f'streak={self._unknown_streak}\n'
                    f'处理流程(r100k 补,别跳过):\n'
                    f'1. 用截图离线分析:analyze_screen(screenshot=<shot 路径>) 看已建档命中;\n'
                    f'2. 未命中 → 按元素语义判断:新画面/弹窗 → od-dev-screen-onboarding 建档\n'
                    f'   + cw_loop 0x 分支加 handler;战斗特效帧(OCR 乱码)→ **先确认\n'
                    f'   非新画面(analyze_screen 为准)才可**加大 UNKNOWN_STOP_THRESHOLD\n'
                    f'   或加等待,不是新画面;\n'
                    f'3. 建档完删本 flag + 重启 MCP server;若判断为瞬时帧误触发 → 删 flag\n'
                    f'   直接重跑(阈值/防抖在 UNKNOWN_STOP_THRESHOLD)。\n'
                    f'移除条件:该类未知态全部建档(实际不可达,长期保留)。\n'
                    f'shot={_shot}', encoding='utf-8')
                log.info('[cw!] [loop] 持久未识别画面 → stop_running 待 AI 建档 shot=%s streak=%s',
                         _shot, self._unknown_streak)
            except Exception as e:  # noqa: BLE001  钩子失败不阻塞
                log.warning('[cw-loop] unknown stop 钩子失败(不阻塞): %s', e)
            self.ctx.run_context.stop_running(reason='hook:battle_unknown_screen')
            return self.round_fail(status='持久未识别画面,停机待建档')
        # 连续未知帧退避(重试无退避缺陷修复):等待随 _unknown_streak 翻倍封顶;
        # 画面被任何分支接走 → streak 归 1,退避自动复位(见 UNKNOWN_RETRY_BACKOFF_CAP_S 注)。
        return self.round_retry(wait=self._unknown_backoff_wait(self._unknown_streak))

    @staticmethod
    def _unknown_backoff_wait(streak: int) -> float:
        """连续未识别帧第 ``streak`` 次(≥1,连续计数,归零复位)重试的等待秒数。

        2s 起步每连续一次翻倍、封顶 ``UNKNOWN_RETRY_BACKOFF_CAP_S``;纯函数便于锁测。
        """
        return min(2.0 * (2 ** (max(streak, 1) - 1)),
                   CwLoop.UNKNOWN_RETRY_BACKOFF_CAP_S)


# ===== B4(ADR-0170):跨局分配器进程级单例 + 终局 update =====
_ALLOCATOR = None          # 进程级(后验跨局累积;server 不重启跨局延续)


def _get_or_init_allocator(ctx: SrContext):
    """惰性建分配器(失败安全:建不出来 → None,update no-op)。plaza 份额先验。"""
    global _ALLOCATOR
    if _ALLOCATOR is not None:
        return _ALLOCATOR
    try:
        from sr_od.application.currency_war.data.cw_plaza_comps import (
            PLAZA_CARRY_CLUSTERS,
        )
        from sr_od.application.currency_war.kernel.cw_run_allocator import (
            ThompsonAllocator,
        )
        total = sum(max(c.n_posts, 0) for c in PLAZA_CARRY_CLUSTERS) or 1
        share = {c.carry: c.n_posts / total for c in PLAZA_CARRY_CLUSTERS if c.n_posts >= 15}
        _ALLOCATOR = ThompsonAllocator.from_plaza(share)
    except Exception as e:   # noqa: BLE001  影子期失败安全
        log.info(f'[cw-alloc] 分配器初始化失败(禁用): {e}')
        _ALLOCATOR = None
    return _ALLOCATOR
