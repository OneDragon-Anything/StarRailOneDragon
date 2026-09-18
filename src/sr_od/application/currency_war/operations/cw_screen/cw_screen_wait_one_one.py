"""货币战争 等待 1-1 备战 op。

投资环境确认后进 1-1:开局补给动画长且无结束标志(用户裁定特殊等待)。
主判据 = 轮询「备战阶段」文本出现(备战屏建档锚 ``标识-备战阶段``——该文本
两档同址无画面判别力,但此处只判「备战面板就绪」非画面分支,用途正当);
固定 ~10s(ONE_ONE_MAX_WAIT_S,待校准)仅作超时兜底:锚一直不现 = 异常,
留证(存图)交循环。不给备战循环加「现在是 1-1」特殊状态参数。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
纯等待型映射,现役 handle 逐位):观察 node = 锚命中/超时两早退判定——
锚「标识-备战阶段」命中 → obs 装载(on_screen)→ 占位
``report_screen_wait_one_one_obs`` 接线(统一形态;本屏现役零容器写点,
接口为占位,match/gs 缺席跳过)→ round_success 进决策动作 node;超时
(``_first_seen_ts`` 起 ≥ ``ONE_ONE_MAX_WAIT_S``)→ 存图留证 + round_fail
交循环(现役出口);未出现且未超时 → round_wait
(``ONE_ONE_POLL_INTERVAL_S``)自环节点轮询等下一帧(wait 语义不吃重试
预算,轮询由固定超时兜底)。决策动作 node = 零动作交回节点(纯等待型无
推进动作,备战就绪即 success 交回主循环——现役「act 段零动作如实申报」
的两段形态承接)。本屏 sim 腿 = 不适用(sim 无对应画面段),等价判据
主承重 = 实机在册行为锁(test_cw_obs_arch_closing_screens.py)。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.wait_one_one import (
    CwScreenWaitOneOneObs,
    report_screen_wait_one_one_obs,
)
from sr_od.application.currency_war.operations.cw_screen.cw_flow_const import (
    ONE_ONE_MAX_WAIT_S,
    ONE_ONE_POLL_INTERVAL_S,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _monotonic() -> float:
    """可测时钟(模块级单点:测试换假时钟验超时,生产等价 time.monotonic)。"""
    return time.monotonic()


class CwScreenWaitOneOne(SrOperation):
    """等待 1-1 备战就绪:轮询「备战阶段」锚;超上界留证 fail 交循环。"""

    PREP_SCREEN: ClassVar[str] = '货币战争-备战'
    PREP_ANCHOR: ClassVar[str] = '标识-备战阶段'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-等待1-1备战')
        self._first_seen_ts: float | None = None   # 首见非就绪帧的时钟起点(超时兜底基)
        # 观察结果(观察 node 产物;锚命中轮装载)。
        self._obs: CwScreenWaitOneOneObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """锚命中/超时两早退判定 + 锚命中轮 obs 装载 → 占位 report 接线。

        映射(现役 handle 逐位):锚命中 → obs 装载 + 占位 report(match/gs
        缺席跳过)→ round_success 进决策动作 node;超时 → 存图留证 +
        round_fail(现役出口);未出现且未超时 → round_wait 轮询(不吃
        重试预算)。轮询轮与超时轮不装载 obs(迁移不增加读屏,锚判定外
        零读屏)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(
                screen, CwScreenWaitOneOne.PREP_SCREEN,
                CwScreenWaitOneOne.PREP_ANCHOR, crop_first=False).is_success:
            log.info('[cw-flow-wait11] 备战阶段锚命中(1-1 备战就绪)')
            obs = CwScreenWaitOneOneObs(on_screen=True, screen=screen)
            _match = getattr(self.ctx, 'cw_match', None)
            _gs = getattr(_match, 'gs', None) if _match is not None else None
            if _gs is not None:
                report_screen_wait_one_one_obs(_gs, obs)
            self._obs = obs
            return self.round_success()
        now = _monotonic()
        if self._first_seen_ts is None:
            self._first_seen_ts = now
        if now - self._first_seen_ts >= ONE_ONE_MAX_WAIT_S:
            self.save_screenshot(prefix='wait_one_one_timeout')   # 留证交循环
            log.warning('[cw-flow-wait11] 等待超时(%.0fs 锚未现),留证交循环',
                        ONE_ONE_MAX_WAIT_S)
            return self.round_fail('等待 1-1 备战超时(锚未现,已留证)')
        return self.round_wait(wait=ONE_ONE_POLL_INTERVAL_S)

    @node_from(from_name='观察')
    @operation_node(name='决策动作')
    def act(self) -> OperationRoundResult:
        """零动作交回节点:纯等待型无推进动作,备战就绪即 success 交回
        主循环(现役 act 段零动作的两段形态承接)。"""
        return self.round_success('1-1 备战就绪')
