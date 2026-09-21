"""事件线 pick 动作 op 族(动作 op 重组批③ 换壳:原 ``EncounterPickOp``
等 5 类,ActionOp ABC → 框架 SrOperation,构造 = (ctx, param, env),
design.md §1.1/§1.2)。事件线意图词表(kernel/cw_events pick 五类)→
overlay act 确认链 op 类,经 ``cw_action_registry.action_op_for`` 工厂
分派——各 overlay 画面 op 的 act 段保持工厂分派,散在画面 op 内的点选+
确认过程代码收拢为「意图类型 → 点击链」声明式(统一观察架构 §6.2)。

域 env = :class:`OverlayPickExecEnv`(结构化包,构造时传入);机械参数
(定位点/选定快照/未选中实证/确认钮定位)由各画面 op 决策半现算后经
env 显式传入,op 类体内零决策零读决策输入。轮次结果(确认链末步
``round_*`` 产物)经 ``round_result`` 旁路字段回传——op 自身 round 结果
恒成功(发出即职责完成),画面 op act 分派面读旁路字段。族先例 =
cw_tool_use_action。

**自上报统一(pick-op-unify 批,撤销 2026-09-18 动作 op 重组批 §1.1
「零上报例外登记」)**:本族每类 run 体在机械链(选中点击 → 确认点击)
发出后直调自己的上报函数 ``report_action_pick_<snake>_param``
(``kernel/cw_action_report``,零写族落 zero_writes)——与 buy_card 等
其它动作 op 同一执行契约;上报发射相零写,容器写语义(chosen_*/Confirm*
到账)仍由画面 op 原写点承载。银狼闭环迭代起三线例外:pick_invest /
pick_equip / pick_supply = 分步实现(发射相仅意图遥测,落地相在画面 op
重入裁决出口/节点完成门,证据闩语义);pick_planner 发射相 = 意图遥测
(零容器写),效果腿同候证据闩。partner 确认点读缺的 retry 旁路分支未发
确认点击,不上报。

体迁纪律(零行为):各 op 类 run 体 = 现役 overlay act 确认链逐字迁移
(接收者 ``self``→``env.op``、机械参数→env 字段两处归一,批4 已迁;
本批只换壳不改体)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.pick_equip import (
    report_action_pick_equip_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.pick_invest import (
    report_action_pick_invest_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.pick_planner import (
    report_action_pick_planner_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.pick_supply import (
    report_action_pick_supply_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_pick_box_card_param,
    report_action_pick_encounter_param,
    report_action_pick_expert_invite_param,
    report_action_pick_fortune_param,
    report_action_pick_megastar_param,
    report_action_pick_partner_param,
    report_action_pick_star_tome_param,
    report_action_pick_wish_trial_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
    report_node_advance,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickBoxCardParam,
    CwActionPickEncounterParam,
    CwActionPickEquipParam,
    CwActionPickExpertInviteParam,
    CwActionPickFortuneParam,
    CwActionPickInvestParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickStarTomeParam,
    CwActionPickSupplyParam,
    CwActionPickWishTrialParam,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_encounter import (
    CwScreenEncounter,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_fortune import (
    CwScreenFortune,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_megastar import (
    CwScreenMegastar,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_yinlang import (
    CwScreenYinLang,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


@dataclass
class OverlayPickExecEnv:
    """事件线 pick 域执行环境(统一动作工厂批4 起;pick-op-unify 批扩字段)。

    公共字段 ``op``/``match``/``config`` + 域字段 = 决策半产物(机械参数,
    构造时显式传入,op 类体内不自算):``idx`` = 生效选中下标(决策半
    钳位后)、``target`` = 点卡定位点、``picked`` = 选定快照(到账登记
    输入)、``unselected`` = 未选中提示在场实证。
    ``confirm`` = 确认钮中心(决策半从 screen_info 现取;None = 点卡即选
    族无确认步);``entry_keyword`` = 确认裁决词(emit_overlay_confirm
    消费,仅日志与调用方重入裁决对照);``need_select`` = 选中半开关
    (巨星迁入半:True = 先点 ``target`` 候选选中再确认;False = 跳过
    选中直发确认)。
    ``round_result`` = 旁路回传(确认链末步 ``round_*`` 产物;op 自身
    round 结果恒成功不携带语义),op 类写;现行两 node 宿主画面 op 均不
    消费本字段(循环推进按宿主自身形态返回 round_wait),保留作分派面
    需要逐结果路由时的旁路面。
    ``leg_type``/``norm_item`` = 银狼策划腿型载荷(银狼闭环 design
    §2.1①;决策半经 ``classify_planner_leg`` 现算,随发射透传给上报函数
    登记意图遥测;leg_type ∈ upgrade|weaken|equip|unknown,norm_item =
    归一件名或空)。
    """

    op: SrOperation
    match: object = None      # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None     # 公共面(pick 确认链零 config 消费)
    idx: int = 0              # [索引定义] 坐标系: 决策半候选列表下标(0 起);
    #             取值时机: 决策半现算快照(钳位后生效值,执行期恒稳)
    target: Any = None        # Point|None 点卡定位点(决策半从 screen_info/OCR 现算)
    confirm: Any = None       # Point|None 确认钮中心(决策半现取;None=点卡即选)
    entry_keyword: str = ''   # 确认裁决词(emit_overlay_confirm;仅日志/重入对照)
    need_select: bool = False  # True = 先点 target 选中再确认(巨星选中半)
    picked: dict | None = None
    unselected: bool = False
    leg_type: str = ''        # 策划腿型载荷(decision 半 classify_planner_leg 产物)
    norm_item: str = ''       # 策划装备腿归一件名('' = 未解析/非装备腿)
    round_result: OperationRoundResult | None = None


class CwActionPickEncounterOp(SrOperation):
    """遭遇节点 pick 确认链(机械语义单一源,统一动作工厂批4 迁入)。

    点卡选中(screen_info 坐标缺失走历史实测兜底常量)→ 确认机械交回
    (验证废除:不读屏判「overlay 关没关」,落地由画面 op handle 顶部
    重入裁决承载;docstring「插空白点击取消选中→死循环」风险的防线由
    重入裁决 + 预算耗尽 bail 承接——机械语义单一源随体迁入本类)。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickEncounterParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickEncounterOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_encounter', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;轮次结果经 ``env.round_result`` 旁路回传。"""
        action = self.param
        env = self.env
        op = env.op
        idx = action.idx
        card_left = area_center(op.ctx, '遭遇卡-其一', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.CARD_LEFT
        card_right = area_center(op.ctx, '遭遇卡-其二', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.CARD_RIGHT
        select_btn = area_center(op.ctx, '按钮-选择', CwScreenEncounter.SCREEN_NAME) or CwScreenEncounter.SELECT_BTN
        card = card_left if idx == 0 else card_right
        safe_click(op, card, tag='cw-encounter')
        time.sleep(0.8)
        # 选择确认机械交回(裁决词 = 标题「遭遇节点」,4 字 vs 备战「遭遇」
        # 标签 2 字,LCS 0.5<0.8 不误匹配;live 2026-08-15)。
        env.round_result = emit_overlay_confirm(op, confirm_point=select_btn,
                                                entry_keyword='遭遇节点', lcs_percent=0.8, tag='cw-encounter')
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_encounter_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('遭遇选择确认链已发(结果经旁路回传)')


class CwActionPickSupplyOp(SrOperation):
    """补给节点 pick 确认链(统一动作工厂批4 迁入)。

    刷新圆钮机械点击留守画面 op(刷新链 = ``SupplyPick.refresh`` 决策的
    执行半)——pick execute 语义 = 点卡选中 → 确认,不含刷新臂。
    到账登记 = 确认收尾的写边(ConfirmSupply → owned += 选中装备名),
    随确认链同体,时序逐位保持。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickSupplyParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickSupplyOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_supply', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 固定等待 → 确认 → 到账登记;零判效)。"""
        action = self.param
        env = self.env
        op = env.op
        match = env.match
        target = env.target
        picked = env.picked
        op.ctx.controller.mouse_move(target)
        op.ctx.controller.click(target)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)。转移证据 = 下一节点
        # 备战锚(E11:补给确认 → 下一节点干净备战帧,无自动弹链)。
        # 辖域契约修正案(迭代 2026-09-20-node-advance-action-report
        # design §2.3 触发点 2):转移证据在本 op 的角色 = **上报时点门**
        # (决定报不报),非执行验证——证据 miss 不上报、不重试、不恢复、
        # 不判效,兜底 = 观察锚定补推(design §2.2);故不把 until 塞进
        # 点击链(until_find_all 会驱节点 runner 轮询重试 = 验证编排,
        # 与 op-layer §1.2「动作 op 禁验证」禁令相抵)。
        confirm_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)
        # 到账登记(§3.3 #18 ConfirmSupply):owned += 选中装备名(粗粒度
        # expected,单轮即回备战覆盖点实读清账;equip 未读到 = 无 item 不登记)。
        if match is not None and picked is not None and picked.get('equip'):
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(match.session, 'ConfirmSupply',
                                     picked['equip'],
                                     produced_by='CwScreenSupplyNode')
        # 自上报(发射相:仅登记意图遥测,容器零写;落地相按实际开出内容
        # 应用 = 单位腿 + 装备后果腿,宿主 = 画面 op 节点完成门证据闩——
        # 银狼闭环 design §2.2,pick_supply 迁出零写族)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_supply_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            # 节点推进上报(supply_confirm;时点门 = 备战锚单探在场的
            # 转移证据,设计单一源 = design §2.3 触发点 2)。证据 miss =
            # 不上报不重试(兜底 = 观察锚定补推;局外 gs 缺席同跳过)。
            if (confirm_result.is_success and op.round_by_find_area(
                    op.screenshot(), '货币战争-备战',
                    '标识-备战阶段').is_success):
                report_node_advance(gs, trigger='supply_confirm')
        # 选定事实现役归宿 = journal chosen 域 + 到账登记。
        return self.round_success('补给选择确认链已发')


class CwActionPickMegastarOp(SrOperation):
    """盛会之星 pick 确认链(统一动作工厂批4 迁入)。

    候选选中半迁入本类(pick-op-unify 批,``env.need_select`` 驱动,见
    ``run``);``chosen_megastar`` 写端留守画面 op(单次逻辑写入豁免面,
    派发前写)——确认机械半 = 确认钮单发。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickMegastarParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickMegastarOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_megastar', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(选中半[need_select] → 确认钮单发 + 固定等待;零判效)。

        选中半(pick-op-unify 批自画面 op 迁入):``env.need_select`` 且
        ``env.target`` 在场 → 点候选选中 + 固定等待(原选中后 0.6s 动画窗,
        时序逐位保留)。``chosen_megastar`` 写端与选中旗标留守画面 op
        (单次逻辑写入豁免面,派发前写——时序申报见迭代 design.md §2)。"""
        action = self.param
        env = self.env
        op = env.op
        if env.need_select and env.target is not None:
            op.ctx.controller.mouse_move(env.target)
            op.ctx.controller.click(env.target)
            time.sleep(0.6)
        # confirm(确认钮纯机械单发;overlay 关否由下一帧重入裁决)。
        # 确认钮中心从 screen_info 读(task#103 化债,W265);缺失兜底常量。
        confirm = area_center(op.ctx, '按钮-确认选择', '货币战争-盛会之星') or CwScreenMegastar.CONFIRM
        op.ctx.controller.mouse_move(confirm)
        op.ctx.controller.click(confirm)
        time.sleep(0.9)
        # 确认 = 纯机械单发(用户裁定 2026-09-14:step2 安全网拆除)。
        # 「请选择强化角色」文本 = 确认钮旁伴随文案(建档证据更正
        # 2026-09-14,巨星调研已证同款误读,非第二画面步骤),禁据它判步。
        # 确认未落地 overlay 残留 =
        # 下一帧重入裁决自愈:节点循环读「仍在巨星 overlay?」(标识锚仍
        # 命中)→ 重走本方法 → 候选已选 → 机械单发确认再推进
        # (计 node_max_retry_times 预算)。
        # (原「到账登记」ConfirmMegastar 块已随 ADR-0651 两态制废除:
        #  chosen_megastar 写端 = 候选选中时点的 session 写 + write_logic
        #  直写(画面 op 候选分支),无挂账登记环节。)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_megastar_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('盛会之星确认已发')


class CwActionPickPartnerOp(SrOperation):
    """选择伙伴 pick 确认链(统一动作工厂批4 迁入)。

    「点选候选 → 确认」脉冲链整体迁入(未选中实证下重点选,单选语义
    无反选面;确认被拒的防线判定留守画面 op 决策半)。选中态标记
    (``_pick_point``)与脉冲计数(``_confirm_pulses``/``_confirm_pending``)
    宿主仍是画面 op,经 env.op 消费——计数生命周期 = 节点级,画面 op
    单一归属不变。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickPartnerParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickPartnerOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_partner', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点选脉冲 + 确认脉冲;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        unselected = env.unselected
        if unselected or op._confirm_pulses == 0:
            # 未选中实证(或首轮强制)→ 点候选卡选中。y 由建档「候选-卡区」
            # 带中心锚定:旧 offset「label cy-60」实点落在立绘底边下方卡体
            # 死区(几何根源见 ``_pick_point_for`` 注)。
            op.ctx.controller.mouse_move(op._pick_point)
            op.ctx.controller.click(op._pick_point)
            time.sleep(0.7)
            log.info('[cw-partner] 点选候选 %s(未选中提示在场=%s)',
                     op._pick_point, unselected)
        # bug#1 吞(before_screenshot 移光标)→ overlay 不关 flat-loop(2026-08-06 r6 stall;手动 click 即关)。
        confirm = op._find_text_center(op.screenshot(), '确认选择')
        if confirm is None:
            log.info('[cw-partner] 未找到 确认选择 → round_retry')
            env.round_result = op.round_retry(wait=1)
            return self.round_success('确认点未找到(重试经旁路回传)')
        op.ctx.controller.mouse_move(confirm)
        op.ctx.controller.click(confirm)
        time.sleep(1.0)
        op._confirm_pulses += 1
        # 确认 = 单屏单选的一次确认(用户澄清+建档证据更正 2026-09-14):
        # 本屏无第二画面、无「选强化目标」步——点选→确认 → 重入裁决即完。
        # retry 轮重复确认零副作用(置灰态被游戏拒绝,无确认穿透风险)。
        op._confirm_pending = True
        # 自上报(确认点击发出后;零写,契约面统一。读缺旁路分支未发
        # 确认点击,不上报——见模块头)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_partner_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        env.round_result = op.round_retry(wait=1)
        return self.round_success('伙伴选择确认脉冲已发(重入裁决承接)')


class CwActionPickPlannerOp(SrOperation):
    """银狼策划 pick 确认链(统一动作工厂批4 迁入)。

    点卡选中(避开卡内「详情」按钮区的选中点几何归决策半 ``_card_point``
    单一源)→ 确认机械交回(裁决词 = 全词「我来当策划」,r327 终审 E;
    详情面板防御已拆,面板若真弹出归下一帧重入自愈——用户裁定
    2026-09-14)。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickPlannerParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickPlannerOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_planner', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        target = env.target
        # 3. 点卡选中(⚠️ 避开卡内「详情」按钮区 x~880-950/y~420-450——局29 手动点
        # (755,400) 触发详情面板的实证;点卡身上部 y=310)
        op.ctx.controller.mouse_move(target)
        op.ctx.controller.click(target, press_time=op.CLICK_PRESS_TIME)
        time.sleep(1.2)   # 等选中动画
        # 点卡 = 机械单发(用户裁定 2026-09-14:详情面板检测拆;用户定性
        # = 详情弹出 = 点错所致,该面归选中点几何治理,面板检测是症状侧
        # 补丁)。面板若真弹出,后果归下一帧重入:本屏分发即门,外循环按当前画面
        # 重分派(详情 overlay 族分支/本 op 重走链)自愈。
        # 4. 点确认+机械交回(r326/P1⑦ 防线语义由重入裁决+预算耗尽 bail
        # 承接,验关半拆除——用户裁定 2026-09-10:动作 op 禁验证)。
        # r327(终审 E):裁决词用全词「我来当策划」(入场锚同词,
        # cw_yinlang_star_up.yml:26 live-verified)——短词「策划」
        # 在艺术字漏读时可能假通过。
        op._confirm_pending = True
        # 确认点主源 = 建档「按钮-骇入确认」中心(坐标单一真相源);area 缺失回退
        # 兜底常量(megastar/invest_env 同款派生 + 缺损兜底模式)。
        _confirm = (area_center(op.ctx, '按钮-骇入确认', CwScreenYinLang.CARD_AREA_SCREEN)
                    or CwScreenYinLang.CONFIRM)
        env.round_result = emit_overlay_confirm(
            op, confirm_point=_confirm,
            entry_keyword='我来当策划', tag='cw-planner',
            press_time=op.CLICK_PRESS_TIME)
        # 自上报(发射相:仅登记意图遥测,容器零写;效果腿在「overlay 已关」
        # 落地证据应用一次,宿主 = 画面 op 重入裁决出口——银狼闭环
        # design §2.1① 证据闩语义)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_planner_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                leg_type=env.leg_type, norm_item=env.norm_item)
        return self.round_success('策划选择确认链已发(结果经旁路回传)')


class CwActionPickInvestOp(SrOperation):
    """投资选择确认链(投资环境/投资策略两屏共用,pick-op-unify 批新建)。

    两屏机械链同构:点选中位(safe_click bug#1 缓解)→ 固定等待 →
    确认(emit_overlay_confirm 机械交回)。屏间差异全部经 env 显式
    传入(定位点 = 决策半从各自建档 area 现算;确认钮中心 = 决策半
    从各自「按钮-确认」现取;裁决词 = '投资环境'/'投资策略'),op
    类体内零决策零读屏。``active_env``/``active_strategies`` 及效果
    登记/置闩等容器写留守画面 op 原写点(零行为)。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickInvestParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickInvestOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_invest', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡选中 → 选中动画等待 → 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        # 点卡选中(bug#1 缓解:click 前 mouse_move)→ 选中动画固定等待
        #(环境屏 0.7s/策略屏同值,时序逐位保留)。
        safe_click(op, env.target, tag='cw-pick-invest')
        time.sleep(0.7)
        # 确认 + 机械交回(验证废除:落地由下一轮重入裁决;裁决词 =
        # 各屏入口标题,经 env.entry_keyword 传入)。
        env.round_result = emit_overlay_confirm(
            op, confirm_point=env.confirm,
            entry_keyword=env.entry_keyword, tag='cw-pick-invest')
        # 自上报(发射相:仅登记意图遥测,容器零写;落地分步 = 双屏分流 +
        # 效果分派,由两屏 handler 重入裁决出口持证据调用——银狼闭环
        # design §2.3,pick_invest 迁出零写族)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_invest_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('投资选择确认链已发(结果经旁路回传)')


class CwActionPickFortuneOp(SrOperation):
    """命运卜者强化三选一确认链(pick-op-unify 批收编)。

    点卡选中(safe_click bug#1 缓解;选中点 = 卡下半部避「详情」按钮区,
    决策半从 OCR 桶现算经 env 传入)→ 选中动画固定等待 → 确认
    (emit_overlay_confirm 机械交回,裁决词 = 标题「命运卜者」)。确认钮
    中心 = 建档「按钮-确认选择」现取,缺失兜底常量(巨星/策划同款派生
    模式)。本屏零 chosen 写端(选择存证已退役),容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickFortuneParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickFortuneOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_fortune', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        safe_click(op, env.target, tag='cw-pick-fortune')
        time.sleep(1.2)
        # 确认钮主源 = 建档「按钮-确认选择」中心(坐标单一真相源);缺失
        # 回退兜底常量。
        _confirm = (area_center(op.ctx, '按钮-确认选择', CwScreenFortune.SCREEN_NAME)
                    or CwScreenFortune.CONFIRM)
        env.round_result = emit_overlay_confirm(
            op, confirm_point=_confirm,
            entry_keyword='命运卜者', tag='cw-pick-fortune')
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_fortune_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('命运卜者确认链已发(结果经旁路回传)')


class CwActionPickWishTrialOp(SrOperation):
    """祈愿试炼确认链(pick-op-unify 批收编)。

    点试炼卡身选中(bug#1 缓解,选中点 = 建档卡位决策半现算)→ 选中
    动画固定等待 → 确认(「按钮-确认选择」area 位置点击,success_wait
    =1.5,现役形态逐位迁移;本屏独有检测在前,不与伙伴/巨星的
    「确认选择」撞)。``chosen_wish`` = 重入裁决出口写,留守画面 op。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickWishTrialParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickWishTrialOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_wish_trial', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → area 确认;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        # 点卡选中(bug#1 缓解:mouse_move 先,零移动落 click)。
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        time.sleep(1.0)
        # 确认选择(祈愿试炼屏 area;原位形态:找到才点,success_wait 等
        # 关闭动画,零判效)。轮次结果经旁路回传(族形态)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择',
            success_wait=1.5)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_wish_trial_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('祈愿试炼确认链已发')


class CwActionPickEquipOp(SrOperation):
    """选择装备三选一选卡链(pick-op-unify 批收编;点卡即选,无确认钮)。

    点卡(mouse_move+click bug#1 缓解;选中点 = 卡名带 x + 卡身 y,决策半
    现算经 env 传入)→ 选中动画固定等待。本屏零 chosen 写端(选择存证已
    退役),容器写零。落地判定归画面 op 重入裁决(「请选择」不在)。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickEquipParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickEquipOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_equip', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡即选 + 固定等待;轮次结果经旁路回传恒成功)。"""
        action = self.param
        env = self.env
        op = env.op
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        time.sleep(1.2)
        # 自上报(发射相:仅登记意图遥测,容器零写;装备腿落地相 = 入栏 +
        # 获得后果链,宿主 = 画面 op 重入裁决出口证据闩——银狼闭环
        # design §2.2,pick_equip 迁出零写族)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_equip_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('装备选卡点击已发(结果经旁路回传)')


class CwActionPickBoxCardOp(SrOperation):
    """武装箱四选一选卡链(pick-op-unify 批收编;点卡选中即确认,单步)。

    点卡(mouse_move+click bug#1 缓解;点击点 = 卡名带下方 y=290 避
    「查看详情」按钮,决策半现算经 env 传入)→ overlay 动画固定等待
    (``_OVERLAY_ANIM_WAIT_S``,与开箱终结交回等待同源)。选卡即终结 =
    画面 op 派发后 round_success 交回(落地归下一帧观察);本 op 零
    chosen 写端,容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickBoxCardParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickBoxCardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_box_card', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡选中即确认 + 动画等待;轮次结果经旁路回传)。"""
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        action = self.param
        env = self.env
        op = env.op
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        # 固定动画等待(来源写死 = 现役 overlay 动画等待常量)。
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_box_card_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('武装箱选卡点击已发(结果经旁路回传)')


class CwActionPickStarTomeOp(SrOperation):
    """星徽秘典四选一选卡链(pick-op-unify 批收编;点卡即选,弹窗自关)。

    点卡(safe_click bug#1 缓解;选中点 = 建档「星徽卡-N」近邻匹配,决策半
    现算经 env 传入)→ 选中动画固定等待。``chosen_tome``/ConfirmTome 到账
    登记留守画面 op 重入裁决出口(动作事实边界),本 op 容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickStarTomeParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickStarTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_star_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡即选 + 固定等待;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        safe_click(op, env.target, tag='cw-pick-tome')
        time.sleep(1.0)
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_star_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('星徽秘典选卡点击已发(结果经旁路回传)')


class CwActionPickExpertInviteOp(SrOperation):
    """专家邀请函选卡链(pick-op-unify 批收编;点卡即选,无确认钮)。

    点选(area 中心 = 建档「卡-N」/「卡-现金为王」现取,idx=-1 = 现金为王
    由决策半解析为定位点,area 缺失在决策半显式失败)→ 弹窗关闭动画
    固定等待。``chosen_expert``/ConfirmExpertCash 到账登记留守画面 op
    重入裁决出口(动作事实边界),本 op 容器写零。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickExpertInviteParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickExpertInviteOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_expert_invite', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点选 + 弹窗关闭动画等待;轮次结果经旁路回传)。"""
        action = self.param
        env = self.env
        op = env.op
        op.ctx.controller.mouse_move(env.target)
        op.ctx.controller.click(env.target)
        time.sleep(1.2)   # 选卡 → 弹窗关闭动画窗
        # 自上报(机械链发出后;零写,契约面统一)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_expert_invite_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success('邀请函选卡点击已发(结果经旁路回传)')
