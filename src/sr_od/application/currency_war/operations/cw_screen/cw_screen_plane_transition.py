"""货币战争 位面过渡 op(W971 P3a;01-opening §2/§3)。

「点击空白处继续」提示出现即点空白(简报下一步后 / 每个 boss 位面开始时各一次)。
完成 = 提示消失(真转移)交回循环;提示未现 = 该步不适用(编排壳按步分流)。
识别与点击坐标均走 screen_info(``currency_war_plane_transition``:
提示 text area + 区域-空白点击,cw_loop 实证空白点建档)。

统一观察架构逐屏迁移(收尾五屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流;总纲契约 6):
cw_game_ports 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径(原序列,生产行为零变化)。五段形态:observe = 提示门(miss 未发 →
fail 交编排壳)+ 帧引用(实机适配器① = 轻观察封口,简报屏同式;重入
裁决不在本段,总纲契约 6:留守 handle 分流前共享段);reconcile = 空申报;
decide+act 内聚 ``_click_blank``(读空白点 center → mouse_move+click+1s →
置位,两路径共享零转录);on_outcome = 无登记件(注册表缺席 = 零动作,
__init__ 申报)。本屏裁决位序 = pending 先行、miss fail 后置(与未达上限
弹窗的 miss 分支内序不同,逐字保真禁统一,收尾屏详设 §3)。本屏 sim 腿 =
不适用(F11 例外清单:sim 无对应画面段),等价判据主承重 = 实机在册行为锁
(test_cw_flow_ops.py)+ 新路径行为锁(test_cw_obs_arch_closing_screens.py)。
"""
import contextlib
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.obs.cw_observation import read_node_sequence
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


def _write_transition_node_chain(session: object, slots: list | None) -> None:
    """过渡屏链观察(链观察落地批;语义正本 =
    game_state/chain-observation.md §3:基线链 transition_row + 现行链
    离场快照 transition_snapshot)。

    过渡屏底部行 = **刚离开位面**的全亮完整节点行(无暗格无 current 态,
    fixture plane_1to2 实证),逐格:upcoming→hu/超阈 none;boss 末槽→
    sift,SIFT miss→none/None 禁回落 Hu(槽 Hu 距离系统性不可靠,
    cw_node_reader 在案)。行归属位面:开局判别 = 容器节点镜像与 hist 双缺
    (复用 kernel 过渡腿三源全缺先例语义,cw_game_state
    ``_derive_node_plane_transition``)= P1 入口基线(transition_row,仅
    基线空时写);非开局 = 节点镜像 plane,镜像缺失跳写(诚实缺位);
    镜像在位面切换窗的滞后语义恰与「刚离开位面」同向。接管局残余风险
    (镜像全缺且行已变异的极端恢复形态)已在迭代 design §2.1-3 申报。
    纯观测写点:异常不阻塞点击推进。
    """
    if session is None or not slots:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            NodeChain,
            TokenCell,
            board_state_of,
        )
        from sr_od.application.currency_war.obs.cw_node_reader import (
            HU_DIST_UNRECOGNIZED,
        )
        bs = board_state_of(session)
        mirror = bs.node.value
        opening = mirror is None and bs.node_hist_ord is None
        if not opening and mirror is None:
            return   # 非开局且镜像缺:行归属位面不可知,禁猜跳写
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
        chain = NodeChain(plane=plane, seq=cells)
        sig = ChannelSig(family='obs', actor='CwScreenPlaneTransition',
                         screen='货币战争-位面过渡', mode='read')
        bs.observe(bs.node_path, chain, evidence='transition_snapshot',
                   sig=sig)
        if opening and bs.node_path_baseline.value is None:
            bs.observe(bs.node_path_baseline, chain,
                       evidence='transition_row', sig=sig)
        # 链 diff 触发:离场快照豁免两帧门(单帧即终审,链正本 §4)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            maybe_emit_chain_diff,
        )
        maybe_emit_chain_diff(bs, snapshot=True, in_mutation_window=False,
                              sig=sig)
    except Exception:   # noqa: BLE001  观测写点 best-effort,不阻塞点击推进
        pass


@dataclass
class PlaneTransitionObservation:
    """位面过渡观察 payload(五段之段1产物;实机转录形态)。

    过渡相位屏轻观察(收尾屏详设 §1):提示门判定在段内(门失败 →
    round_fail 早退交编排壳按步分流);payload 仅携带稳定帧引用(实机
    识别域载体,不出端口——sim 适配器落位时该域 = None 帧语义,F11
    例外清单本批不建)。
    """

    screen: Any = None


class PlaneTransitionLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口)。

    轻观察封口(先例 = 简报屏轻观察适配器):提示门须在段内产出早退
    轮次,归 ``lifecycle_observe``;适配器仅装配稳定帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenPlaneTransition') -> PlaneTransitionObservation:
        return PlaneTransitionObservation(screen=op.last_screenshot)


class CwScreenPlaneTransition(CwScreenOpBase):
    """位面过渡:识别「点击空白处继续」→ 点空白 → 重入观察裁决交回(验证废除)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-位面过渡'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-位面过渡')
        # 适配器位缺省装配(先例 = 五相位屏):观察口 = 实机适配器
        #(轻观察封口);动作口 = None = 直连现役动作体(基类「None = 子类
        # 缺省实现自担」)。on_outcome 注册表:本屏无登记件(注册表缺席 =
        # 零动作)。
        self._observation_adapter = PlaneTransitionLiveObservationAdapter()
        # 点空白已发待重入裁决标志(验证废除形态,用户裁定 2026-09-10):
        # 重入裁决见 handle——提示不在 + 已发 = 过渡完成 → success 交回
        #(外循环 0q 的误分发计数只认 fail,完成路径必须 success)。
        self._click_pending: bool = False

    @operation_node(name='位面过渡', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.PROMPT_AREA, crop_first=False).is_success
        # 重入裁决(观察驱动):上轮点空白已发 → 提示不在 = 过渡完成(提示
        # 已消失)→ success 交回;提示在 = 点击未落地 → 重点(计节点预算)。
        # 两路径共用(分流前挂,先于五段 lifecycle 的 observe 门;总纲契约 6,
        # 先例锚 cw_screen_encounter.py :241-251/:252-258)。
        if self._click_pending:
            self._click_pending = False
            if not _hit:
                log.info('[cw-flow-plane] 过渡完成(重入观察:提示已消失)')
                return self.round_success('位面过渡完成(重入观察裁决)', wait=1.0)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场(= 测试 harness 显式装配)
        # → 五段生命周期新路径;缺省 None = 生产直连旧路径(下方原序列,
        # 生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        # 旧路径原序列(§9.1 并存期逐位保留):
        if not _hit:
            # 提示未现:未到位(上位面未结束)或已过去 → fail 交编排壳/循环重新分流。
            return self.round_fail('位面过渡提示未出现')
        return self._click_blank()

    def _click_blank(self) -> OperationRoundResult:
        """点空白推进体(五段 decide+act 两路径共享零转录;旧 handle :48-58
        逐位平移):读「区域-空白点击」center(缺失 → fail 缺建档)→
        mouse_move+click+1s → 置位(落地判定归下一轮重入裁决)。"""
        blank = area_center(self.ctx, self.BLANK_AREA, self.SCREEN_NAME)
        if blank is None:
            return self.round_fail('位面过渡缺「区域-空白点击」建档')
        # 链观察(链观察落地批):过渡屏全亮行 = 刚离开位面的完整序列,
        # 点击前读行写链(基线/离场快照,见 _write_transition_node_chain);
        # best-effort 不阻塞点击推进(读+写整体抑制,离线/桩帧同免)。
        with contextlib.suppress(Exception):
            _write_transition_node_chain(
                getattr(getattr(self.ctx, 'cw_match', None), 'session', None),
                read_node_sequence(self.ctx, self.last_screenshot))
        log.info('[cw-flow-plane] 过渡提示命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 过渡翻页动画
        # 机械交回(验证废除):提示消失与否由下一轮重入观察裁决(handle 顶部)。
        self._click_pending = True
        return self.round_retry('点空白已发,重入观察裁决')

    # ---- 五段生命周期(统一观察架构 §5.1;先例 = 简报屏)----

    def lifecycle_observe(self
                          ) -> tuple[PlaneTransitionObservation,
                                     OperationRoundResult | None]:
        """段1 observe:提示门(「提示-点击空白继续」miss 未发 → round_fail
        早退交编排壳按步分流,旧 handle 首闸逐位转录)→ 轻观察 payload。
        重入裁决不在本段(总纲契约 6:留守 handle 分流前共享段)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else PlaneTransitionObservation(screen=self.last_screenshot))
        _hit = self.round_by_find_area(
            self.last_screenshot, self.SCREEN_NAME, self.PROMPT_AREA,
            crop_first=False).is_success
        if not _hit:
            return obs, self.round_fail('位面过渡提示未出现')
        return obs, None

    def lifecycle_decision_cycle(self, payload: PlaneTransitionObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_click_blank``
        (点空白推进体,两路径共享零转录);on_outcome = 本屏无登记件
        (注册表缺席 = 零动作,__init__ 申报)。轮次终结出口 = 机械交回
        round_retry(落地判定归下一轮重入裁决,验证废除形态)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._click_blank()
        self._lifecycle_mark('on_outcome')
        return rs
