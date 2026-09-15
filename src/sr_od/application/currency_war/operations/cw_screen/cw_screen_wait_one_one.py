"""货币战争 等待 1-1 备战 op(W971 P3a;01-opening §2 CwScreenWaitOneOne 形态)。

投资环境确认后进 1-1:开局补给动画长且无结束标志(用户裁定特殊等待)。
主判据 = 轮询「备战阶段」文本出现(备战屏建档锚 ``标识-备战阶段``——该文本
两档同址无画面判别力,但此处只判「备战面板就绪」非画面分支,用途正当);
固定 ~10s(ONE_ONE_MAX_WAIT_S,待校准)仅作超时兜底:锚一直不现 = 异常,
留证(存图)交循环。不给备战循环加「现在是 1-1」特殊状态参数。

统一观察架构逐屏迁移(收尾五屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 首行装配点分流(本屏**无重入裁决旗标** → 分流
在首行,先例 = 战斗等待屏 wait();收尾屏详设 §4):cw_game_ports 两端口
完整在场 → 五段生命周期新路径;缺省 None = 生产直连旧路径(原序列,生产行
为零变化)。五段形态:observe = 锚命中早退 success(1-1 备战就绪)+ 超时
早退 fail 留证(``_first_seen_ts`` 起 ≥ ``ONE_ONE_MAX_WAIT_S``,存图)+ 否则
帧引用 payload(实机适配器① = 轻观察封口,战斗等待屏同式);reconcile =
空申报;decide/act = 空申报(decision cycle = round_wait
(``ONE_ONE_POLL_INTERVAL_S``)轮询等下一帧,act 段零动作如实申报);on_outcome
= 无登记件(注册表缺席 = 零动作,__init__ 申报)。本屏 sim 腿 = 不适用
(F11 例外清单:sim 无对应画面段),等价判据主承重 = 实机在册行为锁
(test_cw_flow_ops.py)+ 新路径行为锁(test_cw_obs_arch_closing_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    ONE_ONE_MAX_WAIT_S,
    ONE_ONE_POLL_INTERVAL_S,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


def _monotonic() -> float:
    """可测时钟(模块级单点:测试换假时钟验超时,生产等价 time.monotonic)。"""
    return time.monotonic()


@dataclass
class WaitOneOneObservation:
    """等待 1-1 观察 payload(五段之段1产物;实机转录形态)。

    纯等待型轻观察(收尾屏详设 §4):锚命中/超时两早退判定在段内;payload
    仅携带稳定帧引用(实机识别域载体,不出端口——sim 适配器落位时该域 =
    None 帧语义,F11 例外清单本批不建)。
    """

    screen: Any = None


class WaitOneOneLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口)。

    轻观察封口(先例 = 战斗等待屏轻观察适配器):早退判定(锚命中/
    超时)须在段内产出轮次,归 ``lifecycle_observe``;适配器仅装配稳定帧
    引用。sim 实现 = 不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenWaitOneOne') -> WaitOneOneObservation:
        return WaitOneOneObservation(screen=op.last_screenshot)


class CwScreenWaitOneOne(CwScreenOpBase):
    """等待 1-1 备战就绪:轮询「备战阶段」锚;超上界留证 fail 交循环。"""

    PREP_SCREEN: ClassVar[str] = '货币战争-备战'
    PREP_ANCHOR: ClassVar[str] = '标识-备战阶段'

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-等待1-1备战')
        # 适配器位缺省装配(先例 = 五相位屏):观察口 = 实机适配器
        #(轻观察封口);动作口 = None = 直连现役动作体(基类「None = 子类
        # 缺省实现自担」)。on_outcome 注册表:本屏无登记件(注册表缺席 =
        # 零动作)。
        self._observation_adapter = WaitOneOneLiveObservationAdapter()
        self._first_seen_ts: float | None = None   # 首见非就绪帧的时钟起点(超时兜底基)

    @operation_node(name='等待1-1', is_start_node=True)
    def handle(self) -> OperationRoundResult:
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = 战斗等待屏 wait():
        # 两端口完整在场(= 测试 harness 显式装配)→ 五段生命周期新路径;
        # 缺省 None = 生产直连旧路径(下方原序列,生产行为零变化)。本屏无
        # 重入裁决旗标 → 分流在首行、锚判定之前(收尾屏详设 §4)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, self.PREP_SCREEN, self.PREP_ANCHOR, crop_first=False).is_success:
            log.info('[cw-flow-wait11] 备战阶段锚命中(1-1 备战就绪)')
            return self.round_success('1-1 备战就绪')
        now = _monotonic()
        if self._first_seen_ts is None:
            self._first_seen_ts = now
        if now - self._first_seen_ts >= ONE_ONE_MAX_WAIT_S:
            self.save_screenshot(prefix='wait_one_one_timeout')   # 留证交循环
            log.warning('[cw-flow-wait11] 等待超时(%.0fs 锚未现),留证交循环',
                        ONE_ONE_MAX_WAIT_S)
            return self.round_fail('等待 1-1 备战超时(锚未现,已留证)')
        # round_wait 重跑本节点且不耗 retry:轮询由固定超时兜底,不吃框架预算。
        return self.round_wait(wait=ONE_ONE_POLL_INTERVAL_S)

    # ---- 五段生命周期(统一观察架构 §5.1,先例 = 战斗等待屏驻留型)----

    def lifecycle_observe(self
                          ) -> tuple[WaitOneOneObservation,
                                     OperationRoundResult | None]:
        """段1 observe:锚「标识-备战阶段」命中 → 早退 success(1-1 备战
        就绪);超时(``_first_seen_ts`` 起 ≥ ``ONE_ONE_MAX_WAIT_S``)→ 早退
        fail 留证(存图);否则帧引用 payload(旧 handle :40-52 逐位转录;
        收尾屏详设 §4 五段表)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else WaitOneOneObservation(screen=self.last_screenshot))
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, self.PREP_SCREEN, self.PREP_ANCHOR, crop_first=False).is_success:
            log.info('[cw-flow-wait11] 备战阶段锚命中(1-1 备战就绪)')
            return obs, self.round_success('1-1 备战就绪')
        now = _monotonic()
        if self._first_seen_ts is None:
            self._first_seen_ts = now
        if now - self._first_seen_ts >= ONE_ONE_MAX_WAIT_S:
            self.save_screenshot(prefix='wait_one_one_timeout')   # 留证交循环
            log.warning('[cw-flow-wait11] 等待超时(%.0fs 锚未现),留证交循环',
                        ONE_ONE_MAX_WAIT_S)
            return obs, self.round_fail('等待 1-1 备战超时(锚未现,已留证)')
        return obs, None

    def lifecycle_decision_cycle(self, payload: WaitOneOneObservation
                                 ) -> OperationRoundResult:
        """段3-5:act 段零动作如实申报(纯等待型,收尾屏详设 §4 五段表)
        ——decision cycle = round_wait(``ONE_ONE_POLL_INTERVAL_S``)轮询等
        下一帧(wait 语义不吃 retry 预算,轮询由固定超时兜底,已前移 observe
        段早退);on_outcome = 本屏无登记件(注册表缺席 = 零动作,__init__
        申报)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        self._lifecycle_mark('on_outcome')
        # round_wait 重跑本节点且不耗 retry:轮询由固定超时兜底,不吃框架预算。
        return self.round_wait(wait=ONE_ONE_POLL_INTERVAL_S)
