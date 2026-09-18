"""货币战争 位面过渡 op。

「点击空白处继续」提示出现即点空白(简报下一步后 / 每个 boss 位面开始时各一次)。
完成 = 提示消失(真转移)交回循环;提示未现 = 该步不适用(编排壳按步分流)。
识别与点击坐标均走 screen_info(``currency_war_plane_transition``:
提示 text area + 区域-空白点击,cw_loop 实证空白点建档)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation):
观察 node = 提示门(「提示-点击空白继续」miss 未发 = round_fail 交编排
壳/循环重新分流)+ 过渡链观察一次读:底部全亮行读数构造链值(plane
派生与 TokenCell 构造留守观察侧,见 ``_build_transition_chain``;与
kernel report 的协同契约见该屏 kernel 屏文件)→ ``report_screen_plane_
transition_obs`` 写 ``node_path``/``node_path_baseline``(链防御在
report 内;读+写整体 best-effort 抑制留守观察侧,不阻塞推进)→ obs 挂
实例属性进决策 node。决策动作 node = 重入裁决顶部(点空白已发 → 提示
不在 = 过渡完成 → success 交回(外循环 0q 的误分发计数只认 fail,完成
路径必须 success);提示在 = 点击未落地 → 重点)→ 点空白推进 →
round_wait 循环(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露,无防御
上限)。原单 node 形态「pending 先行、miss fail 后置」位序随两 node 拆
分自然消解(门在观察 node 先行,裁决住决策 node 顶部)。本屏 sim 腿 =
不适用(sim 无对应画面段),等价判据主承重 = 实机在册行为锁 +
sr-od-test 链观察锁(test_cw_transition_node_chain.py)。
"""
import contextlib
import time
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    NodeChain,
    TokenCell,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.plane_transition import (
    CwScreenPlaneTransitionObs,
    report_screen_plane_transition_obs,
)
from sr_od.application.currency_war.obs.cw_node_reader import HU_DIST_UNRECOGNIZED
from sr_od.application.currency_war.obs.cw_observation import read_node_sequence
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _build_transition_chain(gs: GameState | None,
                            slots: list | None) -> NodeChain | None:
    """过渡屏链构造(观察侧读半部;写半部 = ``report_screen_plane_transition_obs``)。

    过渡屏底部行 = **刚离开位面**的全亮完整节点行(无暗格无 current 态,
    fixture plane_1to2 实证),逐格:upcoming→hu/超阈 none;boss 末槽→
    sift,SIFT miss→none/None 禁回落 Hu(槽 Hu 距离系统性不可靠,
    cw_node_reader 在案)。行归属位面:开局判别 = 容器节点镜像与 hist 双缺
    (复用 kernel 过渡腿三源全缺先例语义,cw_game_state
    ``_derive_node_plane_transition``)= P1 入口;非开局 = 节点镜像 plane,
    镜像缺失返回 None(行归属不可知,禁猜;report 内同门兜底);镜像在
    位面切换窗的滞后语义恰与「刚离开位面」同向。
    """
    if gs is None or not slots:
        return None
    mirror = gs.node.value
    opening = mirror is None and gs.node_hist_ord is None
    if not opening and mirror is None:
        return None   # 非开局且镜像缺:行归属位面不可知,禁猜
    plane = 1 if opening else int(mirror.plane)
    ordered = sorted(slots, key=lambda s: s.idx)
    last_idx = ordered[-1].idx
    cells: list[TokenCell] = []
    for s in ordered:
        if s.idx == last_idx:
            cells.append(TokenCell('boss', 'sift', s.hu_dist)
                         if s.boss else TokenCell(None, 'none'))
        elif s.node_type and s.hu_dist is not None \
                and s.hu_dist <= HU_DIST_UNRECOGNIZED:
            cells.append(TokenCell(s.node_type, 'hu', s.hu_dist))
        else:
            cells.append(TokenCell(None, 'none'))
    return NodeChain(plane=plane, seq=cells)


class CwScreenPlaneTransition(SrOperation):
    """位面过渡:识别「点击空白处继续」→ 点空白 → 重入观察裁决交回(验证废除)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-位面过渡'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-位面过渡')
        # 点空白已发待重入裁决标志(验证废除形态):重入裁决住决策动作
        # node 顶部——提示不在 + 已发 = 过渡完成 → success 交回;提示在 =
        # 点击未落地 → 重点。
        self._click_pending: bool = False
        # 观察结果(观察 node 产物;链值 None = 行空/读缺,report 诚实缺位)。
        self._obs: CwScreenPlaneTransitionObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """提示门 + 过渡链观察一次读 → report 落容器。

        门 miss = round_fail 早退交编排壳按步分流(现役首闸同 status;门
        早退不进读链)。门 hit → 底部全亮行读数构造链值 →
        ``report_screen_plane_transition_obs`` 写链(基线/离场快照;防御
        逐位在 report 内:chain 缺诚实缺位/非开局且镜像缺禁猜跳写/基线
        幂等门;离场快照链 diff 触发 snapshot=True 随写点同迁)→ obs 挂
        实例属性。读+写整体 best-effort(异常抑制,不阻塞点击推进)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, CwScreenPlaneTransition.SCREEN_NAME,
                CwScreenPlaneTransition.PROMPT_AREA, crop_first=False).is_success:
            return self.round_fail('位面过渡提示未出现')
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        _chain: NodeChain | None = None
        if _gs is not None:
            with contextlib.suppress(Exception):
                _chain = _build_transition_chain(
                    _gs, read_node_sequence(self.ctx, screen))
        obs = CwScreenPlaneTransitionObs(on_screen=True, chain=_chain,
                                         screen=screen)
        if _gs is not None:
            with contextlib.suppress(Exception):
                report_screen_plane_transition_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 点空白推进 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮点空白已发 → 提示不在 =
        过渡完成(提示已消失)→ success 交回;提示在 = 点击未落地 → 重点。
        循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮
        暴露,无防御上限)。"""
        if self._click_pending:
            self._click_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenPlaneTransition.SCREEN_NAME,
                    CwScreenPlaneTransition.PROMPT_AREA, crop_first=False).is_success:
                log.info('[cw-flow-plane] 过渡完成(重入观察:提示已消失)')
                return self.round_success('位面过渡完成(重入观察裁决)', wait=1.0)
        blank = area_center(self.ctx, CwScreenPlaneTransition.BLANK_AREA,
                            CwScreenPlaneTransition.SCREEN_NAME)
        if blank is None:
            return self.round_fail('位面过渡缺「区域-空白点击」建档')
        log.info('[cw-flow-plane] 过渡提示命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 过渡翻页动画
        # 机械交回(验证废除):提示消失与否由下一轮重入观察裁决(act 顶部)。
        self._click_pending = True
        return self.round_wait('点空白已发,重入观察裁决')
