"""货币战争 盛会之星画面 op(NAMING 迁移:原 overlay 族文件收敛为巨星单画面 op)。

其余 overlay 已按 NAMING §2 迁独立 cw_screen_*.py(委托壳溶解:入口门由
主循环 0 系分支承担,处理本体 = 各画面 op 真身);本文件仅存巨星内联实现。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 节点完成门(``_in_node``,miss = round_success
交回外循环,选中标记复位副作用在门内)+ 候选观察(懒读保真:仅「本访问将
选择」即未选中时读候选;确认访问不重读,迁移不增加读屏)→
``report_screen_megastar_obs`` 落容器 ``megastar_opts`` → obs 挂实例属性进
决策 node。决策动作 node = 节点完成复检(每轮新帧,overlay 消失 = 完成)→
决策从容器零参读 → 候选选中点击/确认单发一个动作 → round_wait 循环推进
(不烧节点重试预算;不收敛 = 策略 bug 响亮暴露,无防御上限)。
``chosen_megastar`` = 选择点单次逻辑写入留守决策面(动作事实边界,不进
report);选中旗标宿主 = 策略器 StrategyState(经 kernel strategy_state_of
None-safe 通道,执行层不冷建)。本屏 sim 腿 = 不适用(sim 无对应画面段,
事件浮层族即时落定),等价判据主承重 = 实机在册行为锁。

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
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.megastar import (
    CwScreenMegastarObs,
    report_screen_megastar_obs,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.obs.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    CW_OVERLAY_SETTLE_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenMegastar(SrOperation):
    """盛会之星:候选立绘 → decide_megastar 选巨星 + 确认(旧巨星节点执行器内联)。

    节点完成门 = 「仍在巨星 overlay?」(标识-盛会之星);确认未落地 =
    下一帧门复检自愈(动作链 bug 归动作层修,不加验证段)。committed-but-
    verifying 单动作形态与 ADR-0264 关态稳定基线预置语义沿旧节点循环平移。
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
        SrOperation.__init__(self, ctx, op_name='货币战争-巨星节点')
        # 观察结果(观察 node 产物,决策动作 node 消费;options 懒读门槛见
        # ``observe`` 注:仅「本访问将选择」即未选中时填充)。
        self._obs: CwScreenMegastarObs | None = None

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

    @staticmethod
    def _clicked_of(match: object) -> bool:
        """选中标记读侧防御(局级旗标,跨 re-dispatch 持久;原实例态在重派时
        重置 → re-click toggle 反选 → confirm 无候选卡死)。读侧 getattr:
        状态对象缺席(None)或异型缺字段退 False(经 kernel strategy_state_of
        通道,禁 getattr session 猜宿主/禁 impl state_of 冷建)。"""
        return (getattr(strategy_state_of(match.session),
                        'megastar_clicked', False)
                if match else False)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """节点完成门 + 候选观察上报(懒读保真)。

        门 miss = overlay 消失 / 进了下一节点 → 节点完成,交还外层
        (含 ``_in_node`` 选中标记复位副作用,须在门内)。在门内 → 仅
        「本访问将选择」(未选中)才读候选;确认访问不重读(迁移不增加
        读屏)→ ``report_screen_megastar_obs`` 写 ``megastar_opts``
        (空候选不写,闸在 report 内);match/gs 缺席的局外兜底路径跳过
        report(决策走决策面防御分支,分支原样)。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        _match = self.ctx.cw_match
        options = ([] if self._clicked_of(_match)
                   else read_megastar_options(self.ctx, screen))
        obs = CwScreenMegastarObs(in_node=True, options=options, screen=screen)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_megastar_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """节点完成复检 + 单动作(选候选 ∨ 确认)+ round_wait 循环推进。

        每轮 node runner 新帧复检节点完成门(round_wait 不计节点预算,
        不收敛 = 策略实现 bug 响亮暴露,无防御上限);确认未落地由下一轮
        门复检自愈。"""
        screen = self.last_screenshot
        if not self._in_node(screen):
            return self.round_success('巨星节点完成(已离开本节点画面)',
                                      wait=CW_OVERLAY_SETTLE_S)
        self._do_action()
        return self.round_wait(wait=1.5)

    def _do_action(self) -> None:
        """单动作体:未选中 → 决策(容器零参读)+ 候选选中点击 + chosen
        写端留守;两态都收尾确认单发(经工厂,方法级替身缝保留)。"""
        _match = self.ctx.cw_match
        if not self._clicked_of(_match):
            options = self._obs.options if self._obs is not None else []
            idx = 0
            if _match is not None and options:
                # 零参决策(写槽已由 report 落容器 megastar_opts;决策
                # 调用形态不变)。空候选/无 match = 缺省支(局外兜底分支原样)。
                pick = _match.strategy.decide_megastar()
                if 0 <= pick.idx < len(options):
                    idx = pick.idx
                log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{idx} {pick.reason}')
            else:
                log.info(f'[cw-megastar] options={len(options)} match={_match is not None} → default idx0')
            # 结果回写 session.chosen_megastar 照常。
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
                # r358d(遥测接线):巨星选择落容器(chosen_megastar,gs 单一源
                # ——终态契约 §B:session 份退役;桩无 gs = 跳过写)。
                # chosen_* = 动作事实边界:留守选择点,不进 report。
                if options and 0 <= idx < len(options) \
                        and getattr(_match, 'gs', None) is not None:
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        ChannelSig,
                    )
                    _match.gs.write_logic(
                        _match.gs.chosen_megastar,
                        options[idx].char_id or '',
                        produced_by='CwScreenMegastar',
                        sig=ChannelSig(family='logic_action',
                                       actor='CwScreenMegastar',
                                       mode='compute'))
            time.sleep(0.6)
        # 确认半经工厂(统一动作工厂批4:体迁 ``cw_overlay_pick_action
        # .MegastarPickOp``,方法级替身缝保留)。候选选中点击留守上方:
        # 候选选中半与 chosen_megastar 写端在体内交错(单次逻辑写入豁免
        # 面)。派发实例仅作注册表解析键(机械参数 = 确认钮定位,op 类
        # 体内自读 screen_info)。
        from sr_od.application.currency_war.kernel.cw_vocab import (
            CwActionPickMegastarParam,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self)
        action_op_for(CwActionPickMegastarParam(idx=0), self.ctx,
                      _env).execute()
