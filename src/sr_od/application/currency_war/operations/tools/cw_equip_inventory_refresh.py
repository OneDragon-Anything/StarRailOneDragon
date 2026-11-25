"""货币战争 装备读帧刷新原语(MCP 直调会话专用观察写端)。

r9 诊断缺陷面 3(H3 坐标新鲜度契约在直调局结构性失效)的处置件:MCP 直调局
无人触发备战入口 heavy 观察装配点 → ``gs.owned_equip_xy`` 伴随域无人刷新 →
穿装/工具记账按坐标反查恒拒单。本原语给直调 agent 一个可及的观察写端:
读帧 → 读数可信性判定(不可信则拒写)→ 共享读函数 ``read_owned_equips_dual_key``
(与框架观察环同一次 read_equips 派生,出现序口径单一源)→ ``gs.observe``
双键整表覆盖。

定位申报(**直调会话专用,框架决策环禁消费**):框架环已有重观察原语
(``CwActionObsParam``)与入口 heavy 装配点,本原语是第三观察写端,只补
「直调局无人写表」的洞;双驾驶互作 = 直调刷新不清框架侧
``cw4_equip_xy_pending`` 交替位 → 框架侧按自身节拍多发一帧无害 Obs 重观察
(fail-safe 方向既有申报已认定安全),量级零。本原语不置位不清位任何交替位
(交替机制仅在框架决策环内自洽)。

读数可信性判定(不可信 → 拒写,保现值)。这是观察写端的读数有效性条件,不是
动作前的防线:浮层期 owned_equips 会把「=」产物预览框误读为已入库装备
(r9 实证形态),角色详情面板盖住装备栏同族误读——读帧刷新在这两种状态下执行
= 毒化伴随域,宁拒写不毒化;商店面板展开时不识别右侧装备。三样判定都用本 op
自己截的那一帧:① 角色详情面板 = 画面判定(``货币战争-备战-角色详情`` 的识别
标志全中);② 商店开着 = 画面判定(``货币战争-备战-开商店`` 的识别标志全中);
③ 合成确认浮层 = 备战子态识别函数(``obs/cw_synthesis_overlay_obs.py``):
在场、歧义、有候选但配不成对,任一即拒写。
"""
from __future__ import annotations

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.obs import cw_synthesis_overlay_obs as overlay_obs
from sr_od.application.currency_war.obs.cw_observe_full import (
    read_owned_equips_dual_key,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

#: 按画面判定挡住的三种状态:(画面名, 读数不可信的原因)。这两个画面各有自己的
#: 识别标志组合,全中才算命中——不靠逐个试按钮。
_SCREEN_BLOCKS: tuple[tuple[str, str], ...] = (
    ('货币战争-备战-角色详情', '角色详情面板在场'),
    ('货币战争-备战-开商店', '商店面板展开'),
)


def untrusted_reading_reason(ctx: SrContext, screen: MatLike) -> str | None:
    """本帧装备栏读数不可信的原因;``None`` = 可信,可以读。

    三样判定都用入参的这一帧:先按画面判定挡角色详情面板与商店开着,再调合成
    确认浮层的识别函数。按钮模板或装备栏搜索矩形取不到时,识别函数抛
    ``SynthesisOverlayInputError``——照常上抛(读不准就不读,不判「可信」)。
    """
    for screen_name, reason in _SCREEN_BLOCKS:
        if screen_utils.is_target_screen(ctx, screen, screen_name=screen_name):
            return reason
    result = overlay_obs.read_synthesis_overlay_of(ctx, screen)
    if result.state == overlay_obs.STATE_PRESENT:
        return '合成确认浮层在场'
    if result.state in (overlay_obs.STATE_AMBIGUOUS, overlay_obs.STATE_UNPAIRED):
        # 候选明细只进日志:失败文案要短,排查时看日志。
        log.info('[cw][equip-refresh] 合成确认浮层按钮候选读不准(%s):%s',
                 result.state, result.candidates_detail())
        return '合成确认浮层的按钮候选读不准'
    return None


class CwEquipInventoryRefresh(CwOperation):
    """读当前帧装备栏,刷新装备库存与坐标伴随域(观察写端,直调会话专用)。
    起点:货币战争-备战画面(装备栏可见,商店面板收起);终点:gs.equips 与
    gs.owned_equip_xy 已按本帧实读整表覆盖,读数经运行结果 data 返回,停留原画面。
    消耗:零——只读识别 + 状态容器观察写,永不触碰任何扣费控件。

    读数不可信的帧拒写(保现值,宁缺勿造),三种情况:合成确认浮层在场、角色详情
    面板在场、商店面板展开——这时读到的装备栏会把浮层的产物预览格读成已入库,
    写进去就是毒化伴随域。处置浮层 / 关面板 / 收起商店之后再调本原语。

    直调口径(刷新 → 单穿 → 再刷新):从本 op 的 round data 取
    ``owned_equip_xy`` 坐标发穿装/工具调用——「读帧→记账反查」天然同快照;
    **连穿多件每件之间必须重调本原语**(穿着后装备栏 reflow,旧坐标失效),
    「刷新 → 单穿 → 再刷新 → …」循环。无局(session 缺)时 data 照返回但
    不写状态容器——记账将恒拒单(机械拖拽已发生、禁补拖),docstring 契约
    见穿装/工具 op。

    双驾驶互作申报:本原语不清框架侧 ``cw4_equip_xy_pending`` 交替位 →
    框架侧按自身节拍多发一帧无害 Obs 重观察(fail-safe 方向,量级零);
    框架决策环禁消费本原语(已有重观察原语,双环混用 = 多余第二源)。
    本 op 无业务参数(构造仅 ctx)。
    """

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='装备读帧刷新',
                             need_check_game_win=False)

    @operation_node(name='刷新装备读数', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """截图 → 读数可信性判定(不可信则拒写)→ 共享读 → observe 双键(无局只读)。"""
        from sr_od.application.currency_war.sim import cw_sim_ports
        if cw_sim_ports.sim_backend_installed():
            # sim 装配:哨兵帧读 None 本就不写(宁缺);显式门零开销跳过,
            # 机械面零触及。
            return self.round_success('sim 装配:零读零写跳过')
        screen = self.screenshot()
        reason = untrusted_reading_reason(self.ctx, screen)
        if reason is not None:
            log.info('[cw][equip-refresh] 读数不可信(%s)→ 拒写保现值', reason)
            return self.round_fail(
                f'未执行:读数不可信({reason};装备读拒写)'
                '——先处置浮层 / 关面板 / 收起商店,再调本原语')
        dual = read_owned_equips_dual_key(self.ctx, screen)
        if dual is None:
            # 识别域未就绪(模板库/建档缺)→ 不写保现值(宁缺勿造,与
            # 框架环同守卫),失败交调用方重试。
            return self.round_fail('识别域未就绪(模板库未加载/建档缺),保现值不写')
        names, xy = dual
        data = {'owned_equips': names, 'owned_equip_xy': xy}
        gs = game_state_from_ctx(self.ctx)
        if gs is None:
            # 无局:不写,data 照返回(调用方取坐标可拖,但须知记账恒拒单)。
            return self.round_success('无局只读(伴随域未写)', data=data, wait=0)
        sig = ChannelSig(family='obs', actor='CwEquipInventoryRefresh',
                         mode='read')
        # 同环同 sig 双键整值覆盖(观察写端,与框架装配点同通道同纪律;
        # 禁动作逻辑消费方借道本原语写猜值)。
        gs.observe(gs.equips, names, sig=sig)
        gs.observe(gs.owned_equip_xy, xy, sig=sig)
        log.info('[cw][equip-refresh] 双键已刷新:owned=%d 伴随键=%d',
                 len(names), len(xy))
        return self.round_success('已刷新(双键整表覆盖)', data=data, wait=0)
