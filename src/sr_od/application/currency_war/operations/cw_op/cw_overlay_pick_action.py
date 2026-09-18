"""事件线 pick 动作 op 族(动作 op 重组批③ 换壳:原 ``EncounterPickOp``
等 5 类,ActionOp ABC → 框架 SrOperation,构造 = (ctx, param, env),
design.md §1.1/§1.2)。事件线意图词表(kernel/cw_events pick 五类)→
overlay act 确认链 op 类,经 ``cw_action_registry.action_op_for`` 工厂
分派——各 overlay 画面 op 的 act 段保持工厂分派,散在画面 op 内的点选+
确认过程代码收拢为「意图类型 → 点击链」声明式(统一观察架构 §6.2)。

域 env = :class:`OverlayPickExecEnv`(结构化包,构造时传入);机械参数
(定位点/选定快照/未选中实证)由各画面 op 决策半现算后经 env 显式传入,
op 类体内零决策零读决策输入。轮次结果(确认链末步 ``round_*`` 产物)经
``round_result`` 旁路字段回传——op 自身 round 结果恒成功(发出即职责
完成),画面 op act 分派面读旁路字段。族先例 = cw_tool_use_action。

**零上报例外登记**(design.md §1.1):本族上报函数为零写,原体无上报位
——本批仅换壳,体内**不调上报**(完备锁不辖 op 内接线)。

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
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickEncounterParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickSupplyParam,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_encounter import (
    CwScreenEncounter,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_megastar import (
    CwScreenMegastar,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_planner import (
    CwScreenPlanner,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


@dataclass
class OverlayPickExecEnv:
    """事件线 pick 域执行环境(统一动作工厂批4 起)。

    公共字段 ``op``/``match``/``config`` + 域字段 = 决策半产物(机械参数,
    构造时显式传入,op 类体内不自算):``idx`` = 生效选中下标(决策半
    钳位后)、``target`` = 点卡定位点、``picked`` = 选定快照(到账登记
    输入)、``unselected`` = 未选中提示在场实证。
    ``round_result`` = 旁路回传(确认链末步 ``round_*`` 产物;op 自身
    round 结果恒成功不携带语义),op 类写、画面 op act 分派面读。
    """

    op: SrOperation
    match: object = None      # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None     # 公共面(pick 确认链零 config 消费)
    idx: int = 0              # [索引定义] 坐标系: 决策半候选列表下标(0 起);
    #             取值时机: 决策半现算快照(钳位后生效值,执行期恒稳)
    target: Any = None        # Point|None 点卡定位点(决策半从 screen_info/OCR 现算)
    picked: dict | None = None
    unselected: bool = False
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
        env = self.env
        op = env.op
        match = env.match
        target = env.target
        picked = env.picked
        op.ctx.controller.mouse_move(target)
        op.ctx.controller.click(target)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)
        op.round_by_find_and_click_area(op.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)
        # 到账登记(§3.3 #18 ConfirmSupply):owned += 选中装备名(粗粒度
        # expected,单轮即回备战覆盖点实读清账;equip 未读到 = 无 item 不登记)。
        if match is not None and picked is not None and picked.get('equip'):
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            register_confirm_arrival(match.session, 'ConfirmSupply',
                                     picked['equip'],
                                     produced_by='CwScreenSupplyNode')
        # 选定事实现役归宿 = journal chosen 域 + 到账登记。
        return self.round_success('补给选择确认链已发')


class CwActionPickMegastarOp(SrOperation):
    """盛会之星 pick 确认链(统一动作工厂批4 迁入)。

    候选选中点击留守画面 op:候选选中半与 chosen_megastar 写端交错
    (点击 → 写端 → 动画等待),写端属单次逻辑写入豁免面——确认机械半
    收拢本类,候选半留守画面 op。"""

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
        """机械执行(确认钮单发 + 固定等待;零判效)。"""
        env = self.env
        op = env.op
        # confirm(确认钮纯机械单发;候选选中半留守画面 op,overlay 关否由下一帧重入裁决)。
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
        # cw_hacker_planner.yml:26 live-verified)——短词「策划」
        # 在艺术字漏读时可能假通过。
        op._confirm_pending = True
        # 确认点主源 = 建档「按钮-骇入确认」中心(坐标单一真相源);area 缺失回退
        # 兜底常量(megastar/invest_env 同款派生 + 缺损兜底模式)。
        _confirm = (area_center(op.ctx, '按钮-骇入确认', CwScreenPlanner.CARD_AREA_SCREEN)
                    or CwScreenPlanner.CONFIRM)
        env.round_result = emit_overlay_confirm(
            op, confirm_point=_confirm,
            entry_keyword='我来当策划', tag='cw-planner',
            press_time=op.CLICK_PRESS_TIME)
        return self.round_success('策划选择确认链已发(结果经旁路回传)')
