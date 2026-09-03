"""货币战争 书册卡处理链 op(2026-08-30 停机钩子实机建档后落码)。

「书册卡」= 备战席占槽道具(青蓝卡+白色书册 icon+「开启」,模板
``assets/template/currency_war/supply/书册卡_未知.png``,find_bookcards 识别):
点槽位中心开启 → 弹「专家邀请函」五选一(4 角色卡 + 现金为王 4 金项)→
点选一个 → 该角色加入商店(由正常商店逻辑接管)/ 或 +4 金 → 弹窗关回备战。

处理链(旧 bookcard_confirm 停机钩子的自动处理替换;钩子段已随本 op 接线删除):
  开卡(检测+点击)→ 选卡(读板面阵营 → 默认策略选卡)→ 验弹窗关(收案)。
  交互事实来源 = 2026-08-30 实机人工处理实录(点槽开弹窗;点停云卡 → 弹窗关、
  回备战、停云入商店)。

默认策略判据(任务判据,实机首例背书):读当前羁绊面板(``read_board``,
弹窗帧左侧面板透出可读)→ ①选与**主力阵营**(在场计数最大)同线的卡;
②无主力同线 → 选与任一在场阵营同线的卡(凑档边际仍正);③全无同线 →
现金为王(经济兜底,不引入板外新阵营)。实机首例:board 仙舟3 → 四选一
人工选停云(仙舟),与本判据一致。
"""
import time

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 专家邀请函弹窗画面(assets/game_data/screen_info/currency_war_expert_invitation.yml)
INVITE_SCREEN: str = '货币战争-备战-专家邀请函'
#: 弹窗 id_mark area(画面身份判定)
INVITE_MARK_AREA: str = '标识-专家邀请函'
#: 四张角色卡 area(点选目标与 OCR 分区);现金为王单独一个 area
CARD_AREAS: tuple[str, ...] = ('卡-1', '卡-2', '卡-3', '卡-4')
CASH_AREA: str = '卡-现金为王'


def choose_expert_index(card_bonds: list[str | None],
                        board: dict[str, int]) -> int:
    """默认策略:返回应点选的卡下标(0..n-1);-1 = 现金为王。

    判据(见模块 docstring;纯函数,单测锁行为):
    ① 主力阵营(在场计数最大;并列取名字序首个,保证确定性)同线优先;
    ② 次选任意在场阵营(board 计数 > 0)同线——羁绊面板口径 = factions∪flows
    并计(read_board),卡上阵营/流派标签同属一个羁绊命名空间,可直接对键;
    ③ 全无同线 → -1(现金为王)。
    board 为空(读数失败)走 ③:选卡无依据时经济兜底优于盲选。
    """
    if not card_bonds or not board:
        return -1
    dominant = max(sorted(board), key=lambda f: board[f])
    for i, bond in enumerate(card_bonds):
        if bond is not None and bond == dominant:
            return i
    for i, bond in enumerate(card_bonds):
        if bond is not None and board.get(bond, 0) > 0:
            return i
    return -1


def _resolve_card_bonds(ctx: SrContext, screen, card_area: str) -> str | None:
    """单卡区域内 OCR → 该卡的有效羁绊名(无依据 → None)。

    解析优先级:① 文本命中 FACTIONS 键(阵营/流派标签,如「仙舟」「能量」);
    ② 文本含 FACTIONS 键(OCR 噪声容错);③ 文本 = 角色注册表名 → 取其首个
    羁绊(factions 优先,空则 flows)。全部未命中 → None(策略层走兜底)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect

    rect = _area_rect(ctx, card_area, INVITE_SCREEN)
    if rect is None:
        return None
    ocr = ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
    texts: list[str] = []
    for o in ocr:
        t = (o.data or '').strip()
        if not t:
            continue
        cx, cy = o.x + o.w // 2, o.y + o.h // 2
        if rect.x1 <= cx <= rect.x2 and rect.y1 <= cy <= rect.y2:
            texts.append(t)
    for t in texts:
        if t in FACTIONS:
            return t
    for t in texts:
        hit = next((f for f in FACTIONS if f in t), None)
        if hit is not None:
            return hit
    for t in texts:
        ch = CHARACTERS.get(t)
        if ch is not None:
            if ch.factions:
                return ch.factions[0]
            if ch.flows:
                return ch.flows[0]
    return None


class CwScreenExpertInvite(SrOperation):
    """书册卡处理链:开卡 → 邀请函选卡(默认策略)→ 验弹窗关。

    两个入口态都收敛到本 op(备战环检测到书册卡 / 外环撞见已开的邀请函弹窗)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-书册卡处理')

    @operation_node(name='开卡', is_start_node=True, node_max_retry_times=6)
    def open_card(self) -> OperationRoundResult:
        """弹窗已开 → 直通选卡;否则找书册卡点击开启;卡与弹窗都无 → fail。"""
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            return self.round_success('弹窗已开')
        from sr_od.application.currency_war.kernel.cw_obs_core import (
            is_prep_like_frame,
        )
        from sr_od.application.currency_war.obs.cw_identity_obs import (
            _ctx_slots,
            find_bookcards,
        )
        cards = find_bookcards(screen, _ctx_slots(self.ctx, '备战栏', 9))
        if not cards:
            return self.round_fail('无书册卡且无邀请函弹窗')
        if not is_prep_like_frame(self.ctx, screen):
            # 过渡帧点击会落空(r133 同型教训)→ 等下帧再判,不计入失败
            return self.round_wait(wait=1)
        slot, center = cards[0]
        self.ctx.controller.mouse_move(center)   # bug#1 缓解(同揭示卡/点球口径)
        self.ctx.controller.click(center)
        log.info('[cw-bookcard] 书册卡 slot%s → 点击开启', slot)
        time.sleep(1.5)   # 开启动画 + 弹窗弹出窗
        return self.round_wait()

    @node_from(from_name='开卡')
    @operation_node(name='选卡', node_max_retry_times=6)
    def choose(self) -> OperationRoundResult:
        """读板面阵营 → 默认策略选卡 → 点击 → 验弹窗关(收案)。"""
        screen = self.screenshot()
        if not self.round_by_find_area(
                screen, INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            # 开卡后弹窗未现(点击落空/动画未完)→ 回开卡节点重判
            return self.round_fail('选卡入口:邀请函弹窗未现')
        board: dict[str, int] = {}
        try:
            from sr_od.application.currency_war.obs.cw_observation import read_board
            board = read_board(self.ctx, screen) or {}
        except Exception as e:   # noqa: BLE001  板面读数失败走兜底(现金为王)
            log.warning('[cw-bookcard] 羁绊面板读数失败(走现金为王兜底): %s', e)
        card_bonds = [_resolve_card_bonds(self.ctx, screen, a)
                      for a in CARD_AREAS]
        idx = choose_expert_index(card_bonds, board)
        area = CASH_AREA if idx < 0 else CARD_AREAS[idx]
        pick_desc = ('现金为王(经济兜底)' if idx < 0
                     else f'卡{idx + 1}(羁绊={card_bonds[idx]})')
        from sr_od.application.currency_war.kernel.cw_obs_core import area_center
        pt = area_center(self.ctx, area, INVITE_SCREEN)
        if pt is None:
            return self.round_fail(f'选卡 area 缺坐标:{area}')
        self.ctx.controller.mouse_move(pt)
        self.ctx.controller.click(pt)
        log.info('[cw-bookcard] 邀请函选卡: board=%s 卡羁绊=%s → %s @(%s,%s)',
                 board, card_bonds, pick_desc, pt.x, pt.y)
        time.sleep(1.2)   # 选卡 → 弹窗关闭动画窗
        if self.round_by_find_area(
                self.screenshot(), INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            log.info('[cw-bookcard] 选卡后弹窗仍在 → round_retry')
            return self.round_retry(wait=1)
        log.info('[cw-bookcard] 弹窗关 → 收案(专家入商店,交正常商店逻辑)')
        # 到账登记(§3.3 对照):「现金为王」= gold +4(待实读,绑 shop_wave_top
        # gold 可信源覆盖点);选角色分支 = 专家入商店由正常商店逻辑接管,
        # 无 session 局状态字段变更 → 不登记(§3 C 区无对应行,理由区口径)。
        if idx < 0:
            from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                register_confirm_arrival,
            )
            _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
            register_confirm_arrival(_sess, 'ConfirmExpertCash', '现金为王',
                                     produced_by='CwScreenExpertInvite')
        return self.round_success(wait=2)
