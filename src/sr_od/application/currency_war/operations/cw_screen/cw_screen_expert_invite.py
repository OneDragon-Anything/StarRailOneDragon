"""货币战争 专家邀请函弹窗画面 op(选卡;2026-08-30 停机钩子实机建档后落码)。

「书册卡」= 备战席占槽道具(青蓝卡+白色书册 icon+「开启」,模板
``assets/template/currency_war/supply/书册卡_未知.png``,find_bookcards 识别):
其开卡动作自 R10 归位备战词表(``kernel/cw_vocab.CwActionOpenBookcardParam``);
用户裁定 2026-09-19 开卡时机归策略实现管后,发射位 = 策略器 entry ①
prep 实体面卡片臂(原备战环入口清场段代发撤销)——本 op 只辖
**弹窗已开后的选卡**:点选一个 → 该角色加入商店(由正常商店逻辑接管)/
或 +4 金 → 弹窗关回备战。

处理链(批2c 链拆后;开卡半随拆迁出,弹窗交外循环 0k 按画面分发进本 op):
  弹窗在场门 → 选卡(读板面阵营 → 默认策略选卡)→ 机械交回(重入裁决收案)。
  交互事实来源 = 2026-08-30 实机人工处理实录(点槽开弹窗;点停云卡 → 弹窗关、
  回备战、停云入商店)。

默认策略判据(普查迁移批 2 收编 kernel:单一源 =
``kernel/cw_events.choose_expert_index``,三级语义原样=在场浓度版):
读当前羁绊面板(``read_board``,弹窗帧左侧面板透出可读)→ ①选与**主力
阵营**(在场计数最大)同线的卡;②无主力同线 → 选与任一在场阵营同线的卡
(凑档边际仍正);③全无同线 → 现金为王(经济兜底,不引入板外新阵营)。
实机首例:board 仙舟3 → 四选一人工选停云(仙舟),与本判据一致。
消费唯一入口 = 策略器零参 ``decide_expert_invite()``,
写槽(弹窗载体 = 卡羁绊解析 + 板面计数)→ 零参决策,handler 零判据实现。
行为分叉申报:E9 在案规格(13_pick_family.md §2,目标线成员优先 → 池
浓度)与实码(在场计数版)分叉,已挂账独立行为变更(迁移批 2 报告),
迁移保持实码行为。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。观察 node = 弹窗在场门(标识-专家邀请函,miss =
round_fail 交回外循环重识别)+ 弹窗载体一次读(四卡区羁绊解析 + 羁绊面板
现读计数,入口帧一次读,与现役决策体读同帧等价)→
``report_screen_expert_invite_obs`` 落容器 ``expert_invite``(payload 双输入
打包)→ obs 挂实例属性进决策 node。决策动作 node = 重入裁决顶部(选卡
点击已发 → 弹窗不在 = 选卡落地 → 此刻才写 chosen_expert + 现金为王到账
登记 + success 交回;在 = 点击未落地 → 清标志重走)→ 决策从容器零参读
(kernel 直调仅防御路径:无 match 分支 + 决策链异常降级)→ 点选 →
round_wait 循环(不烧节点重试预算,无防御上限)。chosen_expert 与
ConfirmExpertCash 到账登记 = 重入裁决点留守(动作事实边界,不进 report;
ConfirmExpertCash 逻辑推进 = gold +4 直推);本屏 sim 腿 = 不适用(sim 无
对应画面段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_game_state_consume chosen_expert 锁 +
test_cw_screen_two_node_family 形态锁;接线锁补档 = 开放设计注,
见 screens/expert_invite.md §9)。
"""
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.expert_invite import (
    CwScreenExpertInviteObs,
    report_screen_expert_invite_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickExpertInviteParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 专家邀请函弹窗画面(assets/game_data/screen_info/currency_war_expert_invitation.yml)
INVITE_SCREEN: str = '货币战争-备战-专家邀请函'
#: 弹窗 id_mark area(画面身份判定)
INVITE_MARK_AREA: str = '标识-专家邀请函'
#: 四张角色卡 area(点选目标与 OCR 分区);现金为王单独一个 area
CARD_AREAS: tuple[str, ...] = ('卡-1', '卡-2', '卡-3', '卡-4')
CASH_AREA: str = '卡-现金为王'


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
    """专家邀请函弹窗选卡(默认策略)→ 验弹窗关(收案)。

    入口态单一 = 弹窗已开(外循环 0k 按画面分发;开卡半已随 R10 链拆
    归备战词表 ``CwActionOpenBookcardParam``,见模块 docstring)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-书册卡处理')
        # 选卡点击已发待重入裁决的 (idx, card_bonds)(验证废除形态):
        # 重入裁决由决策动作 node 顶部承载(弹窗不在 = 选卡落地)→ 此刻才写
        # chosen_expert + 到账登记;弹窗仍在 = 点击未落地 → 重走。
        self._pick_pending: tuple[int, list[str | None]] | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费;card_bonds/board =
        # 弹窗帧一次读)。
        self._obs: CwScreenExpertInviteObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """弹窗在场门 + 弹窗载体一次读 → report 落容器。

        门 miss = round_fail 早退(与现役首闸同 status:弹窗不在(已被处理 /
        0k 检测后消失)→ 交回外循环重识别,外循环按下一帧画面重分发自愈;
        开卡缺位由备战词表 CwActionOpenBookcardParam 链承接,与本 op 无关)。
        门后载体一次读(板面读数失败 = {} 的现金为王兜底语义原样携带)→
        ``report_screen_expert_invite_obs``;match/gs 缺席的局外兜底路径跳过
        report(决策走 kernel 直调防御分支,分支原样)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, INVITE_SCREEN, INVITE_MARK_AREA,
                crop_first=False).is_success:
            return self.round_fail('选卡入口:邀请函弹窗未现')
        board: dict[str, int] = {}
        try:
            from sr_od.application.currency_war.obs.cw_observation import read_board
            board = read_board(self.ctx, screen) or {}
        except Exception as e:   # noqa: BLE001  板面读数失败走兜底(现金为王)
            log.warning('[cw-bookcard] 羁绊面板读数失败(走现金为王兜底): %s', e)
        card_bonds = [_resolve_card_bonds(self.ctx, screen, a)
                      for a in CARD_AREAS]
        obs = CwScreenExpertInviteObs(on_screen=True, card_bonds=card_bonds,
                                      board=board, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_expert_invite_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=6)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 点选 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮选卡已发 → 弹窗不在 = 选卡
        落地 → 写 chosen_expert + 到账登记 + success 交回;弹窗仍在 = 未落地
        → 重走。"""
        if self._pick_pending is not None:
            _idx, _bonds = self._pick_pending
            self._pick_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, INVITE_SCREEN, INVITE_MARK_AREA,
                    crop_first=False).is_success:
                self._record_chosen_expert(_idx, _bonds)
                if _idx < 0:
                    from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
                        register_confirm_arrival,
                    )
                    _sess = getattr(getattr(self.ctx, 'cw_match', None),
                                    'session', None)
                    register_confirm_arrival(_sess, 'ConfirmExpertCash', '现金为王',
                                             produced_by='CwScreenExpertInvite')
                return self.round_success('邀请函选卡已确认(重入观察裁决)', wait=2)
        obs = self._obs
        board = obs.board if obs is not None else {}
        card_bonds = (list(obs.card_bonds) if obs is not None else [])
        # 选卡判据(普查迁移批 2:单一源 = kernel choose_expert_index;唯一
        # 入口 = 策略对象,handler 禁自拟判据,kernel 直调限防御路径:无
        # match 分支 + 决策链异常降级)。写槽已由 report 落容器 expert_invite
        # → 零参决策(决策调用形态不变)。
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                idx = _match.strategy.decide_expert_invite().idx
            except Exception as e:   # noqa: BLE001  决策链异常降级,不出 op
                # 兜底 = kernel 直调同无 match else 分支(现金为王语义一致,
                # 判据仍单一源 kernel,handler 零自拟);可直调因防御路径豁免
                # 在案——「kernel 直调仅无 match」辖正常路径,catch 降级同属
                # 防御面(fortune/equip 两姊妹 handler 同姿态)。
                log.warning('[cw-bookcard] 决策链异常(落现金为王兜底): %s', e)
                from sr_od.application.currency_war.kernel.cw_events import (
                    choose_expert_index,
                )
                idx = choose_expert_index(card_bonds, board)
        else:
            from sr_od.application.currency_war.kernel.cw_events import (
                choose_expert_index,
            )
            idx = choose_expert_index(card_bonds, board)
        area = CASH_AREA if idx < 0 else CARD_AREAS[idx]
        pick_desc = ('现金为王(经济兜底)' if idx < 0
                     else f'卡{idx + 1}(羁绊={card_bonds[idx]})')
        from sr_od.application.currency_war.kernel.cw_obs_core import area_center
        pt = area_center(self.ctx, area, INVITE_SCREEN)
        if pt is None:
            return self.round_fail(f'选卡 area 缺坐标:{area}')
        log.info('[cw-bookcard] 邀请函选卡: board=%s 卡羁绊=%s → %s @(%s,%s)',
                 board, card_bonds, pick_desc, pt.x, pt.y)
        # 选卡链经工厂(pick-op-unify 批:点卡即选 + 弹窗关闭动画等待迁入
        # ``CwActionPickExpertInviteOp``,本 op 只决策;定位点决策半现算
        # (含 idx=-1 = 卡-现金为王 area 解析)经 env 显式传入)。派发实例
        # 携真实选中下标(上报 param 即真实选择,含 -1 现金为王语义)。
        # 机械交回(验证废除):弹窗关没关由下一轮重入裁决(本方法顶部
        # _pick_pending 分支),chosen_expert/ConfirmExpertCash 到账随裁决
        # 出口。round_wait 推进循环(不烧节点重试预算,无防御上限)。
        self._pick_pending = (idx, card_bonds)
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=idx, target=pt)
        action_op_for(CwActionPickExpertInviteParam(idx=idx), self.ctx,
                      _env).execute()
        return self.round_wait('邀请函选卡点击已发,重入观察裁决', wait=1)

    def _record_chosen_expert(self, idx: int, card_bonds: list[str | None]) -> None:
        """选卡落地记录面:写 ``chosen_expert``(单次逻辑写入,申报豁免;
        调用点 = 重入裁决出口,选卡落地后值才可信)。

        真选守卫照 chosen_tome 式(CwScreenBookcard):仅卡分支写,值 = 该卡
        羁绊原文名(kernel choose_expert_index 仅在羁绊读出时返非负下标);
        「现金
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
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            _gs = game_state_of(_sess)
            _gs.write_logic(_gs.chosen_expert, _bond,
                            produced_by='CwScreenExpertInvite',
                            sig=ChannelSig(family='logic_action',
                                           actor='CwScreenExpertInvite',
                                           mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞收案
            log.warning('[cw-bookcard] chosen_expert 记录失败(不阻塞): %s', e)
