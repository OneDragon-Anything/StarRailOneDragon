"""货币战争 结算确认动作 op(迭代 2026-09-20-node-advance-action-report
design §2.3 触发点 1;landing §3.2)。

非策略动作面(不经动作注册表、无 CwAction param;命名与构造从画面框
op 惯例 ``CwOpOpenShop``)。职责 = 点击「货币战争-结算/按钮-继续挑战」
(含 M39 长按兜底的点击力学)→ ``report_node_advance(
trigger='settle_confirm')`` → 返回。

**去证据门(用户裁定 2026-09-21)**:动作 op 不做任何确认——点了就是
上报推进;推进里只有 node_ord 为观察态(source==observation 且 value
在场)才落账。转移证据机制(探锚/等待/bail/补报)整体退役,原「证据
集同源条款」「上报时点门」随裁定作废。无证据等待 ⇒「上报先于下一节点
任何画面渲染」恒成立,原 R3 缝结构性消失。死点击自愈链:幻影上报
(logic 态)→ 重试点击再上报被观察态门挡(零推进)→ 某次点击落地 →
备战帧读数 = hist → 等值 reanchor 翻锚定 → 下一节点解锁(最坏损失 =
幻影那次多 tick 一档发放,用户已知悉接受)。

**归属界定(攻击 B2)**:随本 op 的仅 = 点击/长按兜底/推进上报;结算
读点、``_record_round_outcome``、rounds_done 计数等结算链记留宿主
``CwScreenBattleWait`` 不动。战败分支不进本 op、不推进(终局流转,
节点序止于终局)。完成判据白名单(``SETTLE_COMPLETION_ANCHORS``/
``hit_settle_completion_anchor``)= 宿主 ③段出口判定独用,已迁回
``cw_screen_battle_wait.py``。
"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwOpSettleConfirm(SrOperation):
    """货币战争-结算确认 原子动作 op(点击 + M39 长按兜底 + 推进上报;
    design §2.3 触发点 1,去证据门形态 2026-09-21)。

    生产路径 = ``CwScreenBattleWait`` ②段委托本类 ``execute()``。单 node
    驻留形态:每轮点「继续挑战」(M39 停留 ≥3 轮长按兜底)→ 点击即上报
    (重复上报被 kernel 观察态门结构性挡,零推进零危害);按钮不在场
    (流转已发生/过渡帧)→ round_success 交回宿主(出口判定 = 宿主 ③段
    白名单,非本 op 职责)。上报 = best-effort(局外/session 缺跳过、
    kernel 观察态门挡零推进,均不炸主流程)。
    """

    #: M39 长按兜底(2026-08-16 3-1 实证):「继续挑战」点击不响应 → 结算屏
    #: 停留 ≥3 轮 → 长按 (960,898) 兜底推进。
    SETTLE_STAY_LONG_PRESS: ClassVar[int] = 3
    #: M39 长按兜底专用点(「继续挑战」长按 (960,898);普通点击已改点
    #: OCR/area 命中位置——检测/点击分离时点击坐标须随命中,画面 op 规范
    #: 符合性判读 2026-09-12 整改项)。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-结算确认')
        # 结算屏停留计数(M39 长按兜底触发器;单次 execute 内跨轮累积,
        # 长按后归零)
        self._stay: int = 0

    def _report_node_advance(self) -> bool:
        """settle_confirm 上报(容器获取参照宿主 gs 获取方式:session
        旁表;局外/session 缺 = 跳过上报 best-effort,不炸主流程)。"""
        _match = getattr(self.ctx, 'cw_match', None)
        _session = getattr(_match, 'session', None) if _match is not None else None
        if _session is None:
            log.info('[cw-settle-confirm] 局外/session 缺 → 跳过推进上报'
                     '(best-effort)')
            return False
        from sr_od.application.currency_war.kernel.cw_game_state import (
            gs_of_ctx,
            report_node_advance,
        )
        return report_node_advance(gs_of_ctx(self.ctx, _session),
                                   trigger='settle_confirm')

    def _claim_encounter_reward(self) -> None:
        """遭遇奖励兑现回调(遭遇扩围批;best-effort:局外/session 缺跳过、
        异常不炸主流程——兑现是语义账面,不阻塞结算推进)。判据与单次
        消费语义 = ``cw_encounter_selection.claim_encounter_reward``。"""
        _match = getattr(self.ctx, 'cw_match', None)
        _session = getattr(_match, 'session', None) if _match is not None else None
        if _session is None:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_encounter_selection import (
                claim_encounter_reward,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gs_of_ctx,
            )
            _verdict = claim_encounter_reward(gs_of_ctx(self.ctx, _session))
            if _verdict == 'claimed':
                log.info('[cw-settle-confirm] 遭遇奖励已兑现'
                         '(单次消费:chosen 已清)')
            elif _verdict != 'not-encounter':
                log.info('[cw-settle-confirm] 兑现未触发(%s)', _verdict)
        except Exception as e:   # noqa: BLE001  兑现面不阻塞结算
            log.info('[cw-settle-confirm] 兑现回调异常(不阻塞): %s', e)

    @operation_node(name='结算确认', is_start_node=True, node_max_retry_times=400)
    def confirm(self) -> OperationRoundResult:
        """驻留轮:点「继续挑战」(M39 长按兜底)→ 兑现回调 → 点击即上报;
        按钮不在场 → 交回宿主(出口判定归宿主 ③段白名单)。"""
        if self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-结算', '按钮-继续挑战',
                success_wait=1).is_success:
            self._stay += 1
            if self._stay >= CwOpSettleConfirm.SETTLE_STAY_LONG_PRESS:
                log.info('[cw-settle-confirm] 结算屏停留 %s 轮(点击未生效)'
                         '→ 长按 (960,898) 兜底推进', self._stay)
                self.ctx.controller.click(
                    CwOpSettleConfirm.SETTLEMENT_NEXT, press_time=0.5)
                self.park_cursor(after_wait=0.1)
                self._stay = 0
            # 遭遇奖励兑现(推进上报前调:语义顺序 = 先记账后推进;并防御
            # 下一备战帧观察早到覆写 node 镜像——report_node_advance 只
            # 推进 node_ord,镜像读值本身不随推进变。本局结算数据就绪性
            # 由宿主 battle_wait ②段保证:读点先于本 op 派发)。
            self._claim_encounter_reward()
            # 点击即上报(去证据门,用户裁定 2026-09-21):重复上报被
            # kernel 观察态门挡(零推进),死点击重试链自愈。
            _advanced = self._report_node_advance()
            log.info('[cw-settle-confirm] 继续挑战点击已发 → settle_confirm '
                     '上报(advanced=%s)', _advanced)
            return self.round_wait(wait=1.0)
        # 按钮不在场:流转已发生(或过渡帧)→ 交回宿主;宿主 ③段白名单
        # 出口收口,miss 则下轮重判/重分派。
        return self.round_success('结算确认点击已发,交回宿主出口判定')
