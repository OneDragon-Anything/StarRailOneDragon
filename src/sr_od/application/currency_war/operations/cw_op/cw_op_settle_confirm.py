"""货币战争 结算确认动作 op(迭代 2026-09-20-node-advance-action-report
design §2.3 触发点 1;landing §3.2)。

非策略动作面(不经动作注册表、无 CwAction param;命名与构造从画面框
op 惯例 ``CwOpOpenShop``)。职责四件(自 ``CwScreenBattleWait`` ②段迁入,
归属界定见下):点击「货币战争-结算/按钮-继续挑战」(含 M39 长按兜底
重试)→ 等完成判据白名单命中(转移证据)→ ``report_node_advance(
trigger='settle_confirm')``。

**证据集同源条款(design §2.3,攻击 R3 封 E12 拆批缝)**:转移证据集 =
完成判据白名单**全集**(备战系/补给/遭遇/投资策略/强敌来袭锚),与
``CwScreenBattleWait`` ③段出口判定共用同一 helper
(:func:`hit_settle_completion_anchor`,本模块 = 单一源);等待语义同
③段(白名单命中即返,无独立短超时)。由此 boss 流「证据 miss 而流转
真实发生」结构性不可达:流转发生 ⇒ 简报锚现身 ⇒ 白名单命中 ⇒ 上报
先于简报 op 分派,hist 已推进至 boss 节点。

**转移证据的角色 = 上报时点门**(design §2.3 辖域契约修正案,攻击 F5):
决定报不报,非执行验证——证据 miss = 不上报不重试编排(长按兜底按
现行为继续),兜底归观察锚定(kernel ``observe_node_anchor`` 补推)。

**归属界定(攻击 B2)**:随本 op 迁移的仅 = 点击/长按兜底/证据等待/
推进上报;结算读点、``_record_round_outcome``、rounds_done 计数等结算
链记留宿主 ``CwScreenBattleWait`` 不动。战败分支不进本 op、不推进
(终局流转,节点序止于终局)。
"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 结算完成判据白名单(自 ``CwScreenBattleWait`` ③段迁出的单一源;语义 =
#: 「已回备战系画面」的到达判定(宽;面板就位判定由循环判定序承接)。
#: 位面简报不在切换链上(仅入场出现一次,用户裁决 2026-09-02),不列。
#: BOSS简报锚 = 阵营徽记模板(2026-09-16 从标题 OCR 锚换装,误读免疫)。
SETTLE_COMPLETION_ANCHORS: tuple[tuple[str, str], ...] = (
    ('货币战争-备战', '备战标识-购买经验'),
    ('货币战争-补给', '标识-补给阶段'),
    ('货币战争-遭遇节点', '标识-遭遇节点'),
    ('货币战争-投资策略', '标识-请选择投资策略'),
    ('货币战争-BOSS简报', '标识-阵营徽记'),
)


def hit_settle_completion_anchor(op: SrOperation, screen) -> bool:
    """结算完成判据白名单任一命中(纯判定;结算确认 op 转移证据与
    ``CwScreenBattleWait`` ③段出口共用的单一源——证据集同源条款,
    design §2.3/攻击 R3:两处判定分开维护 = boss 流拆批缝)。

    备战用单锚(宽到达判定;「按钮-出战」双锚精判是循环备战分支的
    职责,此处重复即双源)。BOSS简报锚 = 阵营徽记模板(OCR 误读免疫);
    「强敌」片段判别为锚 miss 的兜底(判别单一源见
    cw_screen_boss_briefing)——boss 帧完成判定交回循环阶段一身份接管。
    位面过渡锚(boss 局每位面开始出现一次;boss 简报帧已在上方排他
    ——共享文案不误判为本白名单项)。
    """
    for _scr, _area in SETTLE_COMPLETION_ANCHORS:
        if op.round_by_find_area(screen, _scr, _area,
                                 crop_first=False).is_success:
            return True
    from sr_od.application.currency_war.operations.cw_screen.cw_screen_boss_briefing import (
        is_boss_briefing_texts,
        read_ocr_texts,
    )
    _texts = read_ocr_texts(op.ctx, screen)
    if is_boss_briefing_texts(_texts):
        return True   # boss 简报帧(徽记模板锚 miss 的形态)→ 完成判定,交回循环阶段一身份接管
    return op.round_by_ocr(screen, '点击空白处继续',
                           lcs_percent=0.8).is_success


class CwOpSettleConfirm(SrOperation):
    """货币战争-结算确认 原子动作 op(点击 + M39 长按兜底 + 证据等待 +
    推进上报;design §2.3 触发点 1)。

    生产路径 = ``CwScreenBattleWait`` ②段委托本类 ``execute()``(子 op
    先例 = cw_screen 屏 op 对动作 op 的 ``action_op_for(...).execute()``
    委托);单 node 循环形态:每轮先查转移证据(白名单命中即上报收工,
    已命中帧不重复点击——重入幂等),再点「继续挑战」(M39 停留 ≥3 轮
    长按兜底),二者皆 miss = 过渡帧等待(未知连续超限 bail 交宿主,
    同宿主 UNKNOWN_BAIL_N 语义)。上报 = best-effort(局外/session 缺
    跳过、kernel 观察态门挡零推进,均不炸主流程)。
    """

    #: M39 长按兜底(2026-08-16 3-1 实证):「继续挑战」点击不响应 → 结算屏
    #: 停留 ≥3 轮 → 长按 (960,898) 兜底推进。
    SETTLE_STAY_LONG_PRESS: ClassVar[int] = 3
    #: M39 长按兜底专用点(「继续挑战」长按 (960,898);普通点击已改点
    #: OCR/area 命中位置——检测/点击分离时点击坐标须随命中,画面 op 规范
    #: 符合性判读 2026-09-12 整改项)。
    SETTLEMENT_NEXT: ClassVar[Point] = Point(960, 898)
    #: 过渡帧(点击已发、流转未达且白名单未命中)连续上界;超限 = bail
    #: 交宿主(语义同宿主 CwScreenBattleWait.UNKNOWN_BAIL_N)。
    UNKNOWN_BAIL_N: ClassVar[int] = 10

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-结算确认')
        # 结算屏停留计数(M39 长按兜底触发器;单次 execute 内跨轮累积,
        # 证据命中/长按后归零)
        self._stay: int = 0
        # 过渡帧未知计数(bail 上界)
        self._unknown_streak: int = 0

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

    @operation_node(name='结算确认', is_start_node=True, node_max_retry_times=400)
    def confirm(self) -> OperationRoundResult:
        """驻留轮:转移证据先行(命中即上报收工)→ 结算点击(M39 兜底)
        → 过渡帧等待。"""
        screen = self.last_screenshot
        if hit_settle_completion_anchor(self, screen):
            _advanced = self._report_node_advance()
            log.info('[cw-settle-confirm] 转移证据命中(白名单) → '
                     'settle_confirm 上报(advanced=%s)', _advanced)
            return self.round_success('转移证据命中,上报完成')
        if self.round_by_find_and_click_area(
                self.screenshot(), '货币战争-结算', '按钮-继续挑战',
                success_wait=1).is_success:
            self._unknown_streak = 0
            self._stay += 1
            if self._stay >= CwOpSettleConfirm.SETTLE_STAY_LONG_PRESS:
                log.info('[cw-settle-confirm] 结算屏停留 %s 轮(点击未生效)'
                         '→ 长按 (960,898) 兜底推进', self._stay)
                self.ctx.controller.click(
                    CwOpSettleConfirm.SETTLEMENT_NEXT, press_time=0.5)
                self.park_cursor(after_wait=0.1)
                self._stay = 0
            return self.round_wait(wait=1.0)
        # 过渡帧:点击已发、流转未达且白名单未命中 → 等待;连续未知超限
        # bail(卡死不烧无限轮次,兜底链裁决权交宿主/主循环)。
        self._unknown_streak += 1
        if self._unknown_streak >= CwOpSettleConfirm.UNKNOWN_BAIL_N:
            log.warning('[cw!][settle-confirm] 连续 %s 轮无证据无按钮 → '
                        'bail 交宿主兜底', self._unknown_streak)
            return self.round_fail('结算确认转移等待连续未识别,bail 交宿主兜底')
        return self.round_wait(wait=1.0)
