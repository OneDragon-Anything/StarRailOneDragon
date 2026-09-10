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

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
装配点分流在**选卡节点顶部**(决策承载段:读板面→选卡→点击→验关内联其
handle 语义;两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径,生产行为零变化 §9.1);**开卡节点两路径均留旧路径**(纯导航:找书册
卡/点开启/过渡帧等待,零决策消费面,申报面 = test_cw_obs_arch_event_screens_
step3::test_expert_open_card_node_stays_legacy 源面锁)。迁移手法单一源 =
盛会之星先例(reviews/T-215-r1.md 验收;T-215-r1 §五.5 统一形态注意项 =
lifecycle_observe 消费 ``_observation_port()`` 位):门后读板面+选卡+验关链
纯移入 ``_handle_overlay``(两路径共享零转录);本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;chosen_expert = 出口验真通过分支单次逻辑
写入豁免 §2.2/§6.5-6,留守共享体;ConfirmExpertCash 到账登记 = expected_state
载体非注册表辖)。本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面段,
事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_board_state_consume chosen_expert 锁 + test_cw_node_screens 接线锁
+ 本批锁 test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from typing import Any

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class ExpertObservation:
    """专家邀请函观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 弹窗在场门 + 帧引用(板面/卡羁绊 OCR 读取归共享动作体
    现役内聚;实机识别域载体,不出端口,架构设计 §2.1;sim 适配器 =
    不适用,F11 例外清单)。
    """

    screen: Any = None


class ExpertLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏 observe = 弹窗在场门已归 ``lifecycle_observe``;适配器仅装配帧
    引用。sim 实现 = 不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenExpertInvite') -> ExpertObservation:
        return op._observe_frame()


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


class CwScreenExpertInvite(CwScreenOpBase):
    """书册卡处理链:开卡 → 邀请函选卡(默认策略)→ 验弹窗关。

    两个入口态都收敛到本 op(备战环检测到书册卡 / 外环撞见已开的邀请函弹窗)。
    """

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-书册卡处理')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(弹窗在场门 + 帧引用封口);动作口 = None = 直连现役
        # 共享体 ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome
        # 注册表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = ExpertLiveObservationAdapter()

    def _observe_frame(self) -> ExpertObservation:
        """轻观察帧装配(实机适配器①封口内容):弹窗在场门在 observe 段,
        本方法仅携带当前帧引用(板面/羁绊读取归共享体现役内聚)。"""
        return ExpertObservation(screen=self.last_screenshot)

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
        """读板面阵营 → 默认策略选卡 → 点击 → 验弹窗关(收案)。

        装配点分流在本节点顶部(决策承载段;试点步骤 3;开卡节点两路径均
        留旧路径,见模块 docstring 申报面)。"""
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.screenshot()
        if not self.round_by_find_area(
                screen, INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            # 开卡后弹窗未现(点击落空/动画未完)→ 回开卡节点重判
            return self.round_fail('选卡入口:邀请函弹窗未现')
        return self._handle_overlay(screen)

    def _handle_overlay(self, screen) -> OperationRoundResult:
        """门后读板面+选卡+验关链(旧 choose 门后体纯移入,两路径共享零
        转录;试点步骤 3,先例 = 盛会之星 ``_do_action`` 共享式)。
        chosen_expert 写端 = 出口验真通过分支单次逻辑写入豁免留守(§2.2);
        ConfirmExpertCash 到账登记语义逐位保留。"""
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
        # BoardState 写端(设计 §3.4.5:专家邀请函=书册卡羁绊,选卡写入
        # chosen_expert;单次逻辑写入,§3.4 申报豁免)。出口验真(弹窗关)
        # 通过才到此处 = 选卡落地。
        self._record_chosen_expert(idx, card_bonds)
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

    def _record_chosen_expert(self, idx: int, card_bonds: list[str | None]) -> None:
        """选卡落地记录面:写 ``chosen_expert``(设计 §3.4.5;单次逻辑写入,
        §3.4 申报豁免;调用点 = 出口验真通过后)。

        真选守卫照 chosen_tome 式(CwScreenBookcard):仅卡分支写,值 = 该卡
        羁绊原文名(choose_expert_index 仅在羁绊读出时返非负下标);「现金
        为王」兜底分支不写——chosen_expert 语义 = 受邀专家(羁绊),现金 =
        无专家受邀,该事实由 ConfirmExpertCash +4 金到账登记通道承载(照旧
        不动)。记录面失败不阻塞收案。"""
        _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        if _sess is None or not (0 <= idx < len(card_bonds)):
            return
        _bond = card_bonds[idx]
        if not _bond:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_board_state import (
                board_state_of,
            )
            _bs = board_state_of(_sess)
            _bs.write_logic(_bs.chosen_expert, _bond,
                            produced_by='CwScreenExpertInvite')
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞收案
            log.warning('[cw-bookcard] chosen_expert 记录失败(不阻塞): %s', e)

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星;
    # ---- 辖选卡节点,开卡节点留旧路径见模块 docstring 申报面)----

    def lifecycle_observe(self
                          ) -> tuple[ExpertObservation,
                                     OperationRoundResult | None]:
        """段1 observe:弹窗在场门(标识-专家邀请函,旧 choose 首闸逐位
        转录)→ 轻观察 payload。门失败 = round_fail 早退(与旧 choose 同
        status,选卡节点无 fail 边 = op FAIL 语义不变),后续段不执行。"""
        screen = self.screenshot()
        if not self.round_by_find_area(
                screen, INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            return (ExpertObservation(screen=screen),
                    self.round_fail('选卡入口:邀请函弹窗未现'))
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: ExpertObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (板面读数/卡羁绊解析/默认策略/点卡/验关/chosen 与到账登记全部原位,
        两路径共享零转录)。段5 on_outcome = 本屏无落地登记件(注册表缺席
        = 零动作,见 __init__ 申报);出口验真/轮次结果语义在共享体内逐位
        保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay(payload.screen)
        self._lifecycle_mark('act')
        return rs
