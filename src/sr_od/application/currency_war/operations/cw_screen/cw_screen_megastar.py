"""货币战争 盛会之星画面 op(NAMING 迁移:原 overlay 族文件收敛为巨星单画面 op)。

其余 overlay 已按 NAMING §2 迁独立 cw_screen_*.py(委托壳溶解:入口门由
主循环 0 系分支承担,处理本体 = 各画面 op 真身);本文件仅存巨星内联实现。

统一观察架构逐屏迁移首批(试点步骤 2;架构设计 §9.2 迁移步骤 4 + 开放
问题清单 B3「盛会之星 = 纯选卡最简代表屏」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;chosen_megastar = 选择 handler 单次逻辑
写入豁免留守 ``_do_action``);五段形态 = observe(节点完成门,轻观察)→
decide+act 内聚于 ``_do_action`` 现役动作体(两路径共享零转录);节点
完成判定 = 下一轮 observe 门复检(观察驱动节点循环,非生命周期验证段
——用户裁定 2026-09-10:验证段废除,动作未生效归动作层修可靠性)。
本屏 sim 腿 =
不适用(F11 例外清单:sim 无对应画面段,事件浮层族即时落定),等价判据
主承重 = 实机在册行为锁(锁面 = sr-od-test test_cw_obs_arch_event_screens.py
+ test_cw_runnode_retire.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class MegastarObservation:
    """盛会之星观察 payload(五段之段1产物;试点步骤 2 实机转录形态)。

    本屏观察轻(B3「纯选卡最简」):observe 段 = 节点完成门(候选读取归
    decide 段动作体 ``_do_action`` 现役内聚,避免新增读屏)——payload 仅
    携带稳定帧引用(实机识别域载体,不出端口;架构设计 §2.1)。
    """

    screen: Any = None


class MegastarLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 2)。

    本屏 observe = 节点完成门已归 ``CwScreenMegastar.lifecycle_observe``
    (门判定含选中标记复位副作用,须在门内);适配器仅装配稳定帧引用。
    sim 实现 = 不适用(F11 例外清单:sim 无对应画面段),本批不建。
    """

    def observe(self, op: 'CwScreenMegastar') -> MegastarObservation:
        return MegastarObservation(screen=op.last_screenshot)


class CwScreenMegastar(CwScreenOpBase):
    """盛会之星:候选立绘 → decide_megastar 选巨星 + 确认(旧巨星节点执行器内联)。

    **节点完成模型 = observe 门复检 + 节点预算**(NAMING.md §6 选型判据
    「多步序列/每步可独立失败/历史卡死」侧;旧节点基类退役批内联,行为
    等价红线):每轮 observe 门读「仍在巨星 overlay?」(标识-盛会之星)
    → 仍在 = 本节点尚有动作待执行(选候选/确认一个动作)→ round_retry
    (计 node_max_retry_times=8 预算,超 → FAIL bail);overlay 消失 =
    完成 → round_success。节点循环 = 观察驱动的框架节点迭代(下一轮
    observe 读新帧世界事实,非生命周期验证段——用户裁定 2026-09-10
    验证段废除;confirm 点击系统性不生效 = 动作链 bug,根修动作链不加
    验证)。committed-but-verifying 节点循环与 ADR-0264 关态稳定基线
    预置原样平移(旧基类节点循环语义)。

    **玩法机制(米游社 wiki content/6239 + 实机日志/截图核实,2026-08-07)**:
    盛会之星 = 阵营羁绊;「巨星」= 选 1 名盛会之星角色当巨星,给全队独特 buff。
    触发 = 羁绊激活时弹出(非固定节点),一局可多次 → 选中标记不能跨节点保持。
    dispatch 是 OCR 反应式(主循环 0b 检测「盛会之星」就接)→ 不管何时弹都接得住。
    本节点 = 「选巨星候选 → 确认」,确认 = 纯机械单发(用户裁定 2026-09-14:
    「罕见残留再 confirm」安全网拆除)——「请选择强化角色」文本 = 确认钮旁
    伴随文案(建档证据更正,曾误读为可选第二画面),确认未落地归下一帧
    重入裁决,节点循环单确认自愈。候选坐标经 screen_info
    ``currency_war_megastar``(候选-左/右 + 按钮-确认选择);缺失用兜底常量。
    """

    # 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边);名位置 = 卡身选中区。
    # 常量=screen_info 缺失兜底;首选 area_center('候选-左')。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)
    # 右候选(星期日)位 —— OCR 名 @x1061 y334(cw_megastar 实测 2026-08-07);同 y。
    # 常量=兜底;首选 area_center('候选-右')。
    CANDIDATE_RIGHT: ClassVar[Point] = Point(1061, 333)
    # 「确认选择」钮中心(OCR 确认选择 x1442y548;钮中心 ~1490,560)。常量=兜底;
    # 首选 area_center('按钮-确认选择')。
    CONFIRM: ClassVar[Point] = Point(1490, 560)

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-巨星节点')
        # 适配器位缺省装配(试点步骤 2;先例 = CwScreenPrep):观察口 =
        # 实机适配器(本屏轻观察封口);动作口 = None = 直连现役动作体
        # ``_do_action``(基类「None = 子类缺省实现自担」;committed-but-
        # verifying 单动作内聚于该方法,两路径共享零转录,禁适配器私有
        # 动作类型词表 §6.1)。on_outcome 注册表:本屏无落地登记件
        # (§6.4 收编面无事件屏 chosen 行;chosen_megastar = 选择 handler
        # 单次逻辑直写,write_logic,ADR-0651)。
        self._observation_adapter = MegastarLiveObservationAdapter()

    def _in_node(self, screen) -> bool:
        # 巨星 overlay:盛会之星标题在(用 screen_info 标题 area 位置区分,非全屏 LCS)。原用「确认选择
        # AND NOT 选择伙伴」(lcs 0.7 防共享「选择」误匹配)—— 改用 megastar 独有标题「盛会之星」更直接。
        still_in = self.round_by_find_area(screen, '货币战争-盛会之星', '标识-盛会之星', crop_first=False).is_success
        # megastar 一局可能多次(每次持有盛会之星角色触发,见类 docstring),flag 不能跨节点保持 True。
        # 节点完成即复位:经 kernel strategy_state_of None-safe 通道,状态
        # 对象缺席跳过写(禁执行层触发 impl state_of 的 None 冷建装配语义)。
        if not still_in:
            _match = self.ctx.cw_match
            if _match is not None:
                _st = strategy_state_of(_match.session)
                if _st is not None:
                    _st.megastar_clicked = False
        return still_in

    @operation_node(name='巨星处理', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        """committed-but-verifying 节点循环(旧基类逻辑内联,零行为变更)。"""
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # 两端口完整在场(= 测试 harness 显式装配)→ 五段生命周期新路径;
        # 缺省 None = 生产直连旧路径(下方原序列,生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        # 验证完成:已不在本节点画面 = overlay 消失 / 进了下一节点 → 节点完成,交还外层。
        if not self._in_node(screen):
            # (gate 清尾批 2026-09-03:原此处向已退役的 gate 稳定门预置基线;
            #  wait_stable_frame 在 旧内环拆除后已无生产调用方,基线写端
            #  无读端 → 调用删除。外循环重判兜底,等待语义不变。)
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        # 仍在节点内 → 做一个动作;round_retry 重跑本节点(计预算,超 → FAIL bail)。
        self._do_action(screen)
        return self.round_retry(wait=1.5)

    def _do_action(self, screen) -> None:
        # 选中标记挂策略器状态 StrategyState(局级,跨 re-dispatch 持久;
        # 原实例态在重派时重置 → re-click toggle 反选 → confirm 无候选
        # → 卡死)。读侧防御 getattr:状态对象缺席(None)或异型缺字段
        # 退 False(经 kernel strategy_state_of 通道,禁 getattr session
        # 猜宿主/禁 impl state_of 冷建)。megastar 选中态视觉(金边)。
        _match = self.ctx.cw_match
        _clicked = (getattr(strategy_state_of(_match.session),
                            'megastar_clicked', False)
                    if _match else False)
        if not _clicked:
            options = read_megastar_options(self.ctx, screen)
            match = self.ctx.cw_match
            idx = 0
            if match is not None and options:
                # 决策输入消费切换(迁移批次二):GameState 视图替 last_state 直读;
                # overlay 时用上次备战快照(语义同旧,值源切 GameState)。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of,
                )
                _state = game_state_of(match.session)
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_megastar(options, _state, match.session, _cfg)
                if 0 <= pick.idx < len(options):
                    idx = pick.idx
                log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{idx} {pick.reason}')
            else:
                log.info(f'[cw-megastar] options={len(options)} match={match is not None} → default idx0')
            # (W312 巨星候选面存证行已随 exogenous 流写入端退役删除——删除波 1;
            #  结果回写 session.chosen_megastar 照常。)
            # 候选坐标从 screen_info 读(task#103 化债,W265);缺失走历史实测兜底常量。
            candidate = ((area_center(self.ctx, '候选-左', '货币战争-盛会之星') or CwScreenMegastar.CANDIDATE_LEFT)
                         if idx == 0 else
                         (area_center(self.ctx, '候选-右', '货币战争-盛会之星') or CwScreenMegastar.CANDIDATE_RIGHT))
            self.ctx.controller.mouse_move(candidate)
            self.ctx.controller.click(candidate)
            if _match is not None:
                # 置位经 kernel strategy_state_of(None-safe 不冷建):状态
                # 对象缺席跳过写(局级:跨 re-dispatch 持久,session.md
                # §2.4 B1 定案的宿主级语义)。
                _st = strategy_state_of(_match.session)
                if _st is not None:
                    _st.megastar_clicked = True
                # r358d(遥测接线):巨星选择落 session(复盘「绑定与 comp 匹配」维度)。
                if options and 0 <= idx < len(options):
                    _match.session.chosen_megastar = options[idx].char_id or ''
                    # GameState 写端(迁移批次二,§3.4.5:各屏选卡写入
                    # chosen_*;单次逻辑写入,§3.4 申报豁免)。
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                        game_state_of,
                    )
                    game_state_of(_match.session).write_logic(
                        game_state_of(_match.session).chosen_megastar,
                        _match.session.chosen_megastar,
                        produced_by='CwScreenMegastar',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenMegastar',
                                       mode='compute'))
            time.sleep(0.6)
        # 确认半经工厂(统一动作工厂批4:体迁 ``cw_overlay_pick_action
        # .MegastarPickOp``,方法级替身缝保留)。候选选中点击留守上方:
        # 候选选中半与 chosen_megastar 写端在原体内交错(§3.4.5 单次逻辑
        # 写入豁免面),逐字连续搬迁不可得——确认机械半先收拢,候选半随
        # 写端迁移批再收拢(裁定申报见 T-216 交付报告)。派发实例仅作
        # 注册表解析键(机械参数 = 确认钮定位,op 类体内自读 screen_info)。
        from sr_od.application.currency_war.kernel.cw_events import MegastarPick
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        action_op_for(MegastarPick(idx=0)).execute(
            OverlayPickExecEnv(op=self))

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 2,先例 = CwScreenPrep)----

    def lifecycle_observe(self
                          ) -> tuple[MegastarObservation,
                                     OperationRoundResult | None]:
        """段1 observe:节点完成门(``_in_node`` 复检含选中标记复位副作用,
        须在门内)→ 轻观察 payload。已离开本节点画面 = 节点完成,早退交还
        外层(旧 handle 首闸逐位转录,含完成 settle 等待语义)。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            # (gate 清尾批 2026-09-03:原此处向已退役的 gate 稳定门预置基线;
            #  wait_stable_frame 在 旧内环拆除后已无生产调用方,基线写端
            #  无读端 → 调用删除。外循环重判兜底,等待语义不变。)
            return (MegastarObservation(screen=screen),
                    self.round_success('巨星节点完成(已离开本节点画面)',
                                       wait=CW_OVERLAY_SETTLE_S))
        return MegastarObservation(screen=screen), None

    def lifecycle_decision_cycle(self, payload: MegastarObservation
                                 ) -> OperationRoundResult:
        """段3-4(单动作内聚):decide+act 内聚于 ``_do_action`` 现役动作体
        (选候选 ∨ 确认一个动作;候选决策/遥测/session 写端/到账登记全部
        原位,两路径共享零转录)。段5 on_outcome = 本屏无落地登记件(注册
        表缺席 = 零动作,见 __init__ 申报);节点完成判定 = 下一轮 observe
        段 ``_in_node`` 复检(观察驱动节点循环:round_retry 重入后由观察
        门读新帧世界事实,非生命周期验证段——用户裁定 2026-09-10 验证段
        废除;confirm 点击系统性不生效 → 修动作链),round_retry 计
        node_max_retry_times=8 预算不变,故段迹到 act 为止。"""
        self._lifecycle_mark('decide')
        _adp = self._action_port()
        if _adp is not None:
            _adp.execute(self, None)   # 注入替位(测试桩);动作体归一
        else:
            self._do_action(payload.screen)
        self._lifecycle_mark('act')
        # 仍在节点内 → round_retry 重跑本节点(计预算,超 → FAIL bail)。
        return self.round_retry(wait=1.5)
