# live-verified 2026-08-21(局32 P2r2 卡死 30min 后建;交互实锤:点卡下半部
# y≈480 选中,确认 (1491,600) 消费成功——同策划事件坐标族)。

"""货币战争 命运卜者「强化效果三选一」overlay 处理 op(r115)。

事件族:策划系 overlay(标题=事件名+「请选择N个强化效果」+N 卡+Q 详情+确认)。
银狼策划(r103)同族;命运卜者强化在 P2 出现(黑天鹅/奥迹系强化)。
布局(局32 实拍):标题 y~58-94 / 指令 y~122 / 卡文字 y~296-405 / 三卡
x≈510/900/1290 / 确认 (1441-1543,584-615)。

识别:「请选择」+「强化效果」关键词(id_mark 由 screen_info 承担)。
策略:OCR 三卡文字 → decide_event 类打分(机制词缀向);v1 用
decide_planner 同款文本规则(奥迹/伤害=战力类,留白=保守)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(reviews/T-215-r1.md 验收;T-215-r1 §五.5 统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):handle 体纯移入 ``_handle_overlay``
(两路径共享零转录);**本屏无 op 内入口门**(入口判定归主循环 0 系分发,
observe 段 = 轻观察帧引用);本屏无 on_outcome 落地登记件(§6.4 收编面无
事件屏 chosen 行;fortune 无 chosen_* 写端,选择存证行已随删除波 1 退役)。
本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面
段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁(本批锁
test_cw_obs_arch_event_screens_step3)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class FortuneObservation:
    """命运卜者观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 轻观察帧引用(卡面 OCR 读取归共享动作体现役内聚;实机
    识别域载体,不出端口,架构设计 §2.1;sim 适配器 = 不适用,F11 例外
    清单)。
    """

    screen: Any = None


class FortuneLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏无 op 内入口门(分发即门),适配器仅装配帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenFortune') -> FortuneObservation:
        return op._observe_frame()


class CwScreenFortune(CwScreenOpBase):
    """命运卜者强化三选一:OCR 卡文字 → 文本策略选卡 → 确认。"""

    # ⚠️ 待实机核(坐标单一源清点项):以下为 2026-08-21 live 实锤字面量
    # (文件头实拍布局),未 area 化(本批实机纪律不可测,建档挂账实机批)。
    # 三卡卡身(选中点击点=卡下半部,避详情按钮 y~430-462;同策划事件教训)
    CARD_XS: ClassVar[tuple[int, ...]] = (510, 900, 1290)
    CARD_Y: ClassVar[int] = 480
    TEXT_Y_LO: ClassVar[int] = 290
    TEXT_Y_HI: ClassVar[int] = 410
    CONFIRM: ClassVar[Point] = Point(1491, 600)

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-命运卜者强化')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome 注册
        # 表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = FortuneLiveObservationAdapter()
        # 确认已发待重入裁决标志(验证废除形态):本屏分发即门(无 op 内入口
        # 守卫),重入出口裁决区分「首发 miss」与「重入 miss(= overlay 已关
        # → success 交回)」,见 _handle_overlay 顶部。
        self._confirm_pending: bool = False

    def _observe_frame(self) -> FortuneObservation:
        """轻观察帧装配(实机适配器①封口内容;卡面读取归共享体现役内聚)。"""
        return FortuneObservation(screen=self.last_screenshot)

    def _read_cards(self, screen) -> list[str]:
        """OCR 三卡文字 → x 近邻分流。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        buckets: dict[int, list[str]] = {x: [] for x in self.CARD_XS}
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            cx = mrl.max.center.x
            if not (self.TEXT_Y_LO <= cy <= self.TEXT_Y_HI):
                continue
            nearest = min(self.CARD_XS, key=lambda x: abs(x - cx))
            if abs(nearest - cx) < 190:
                buckets[nearest].append(text)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='命运卜者强化', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(原序列整体移入
        # _handle_overlay 共享体,试点等价门通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return self._handle_overlay()

    def _handle_overlay(self) -> OperationRoundResult:
        """选卡+确认链(旧 handle 体纯移入,两路径共享零转录;试点步骤 3,
        先例 = 盛会之星 ``_do_action`` 共享式)。文本策略 v1/safe_click/
        确认机械交回语义逐位保留;验关半拆除(用户裁定 2026-09-10)。"""
        # 重入裁决(观察驱动,M7 同化先例 + cw_entry_start 守卫先例):本屏
        # 分发即门(无 op 内入口守卫),round_retry 重入不经外循环分发 →
        # 顶部出口门补位:入口词不在 = overlay 已关(上轮确认已落地)→
        # success 交回外循环;在 = 重走选卡+确认(计节点预算)。
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_ocr(self.screenshot(), '命运卜者',
                                     lcs_percent=0.5).is_success:
                return self.round_success('命运卜者强化已确认(重入观察裁决)',
                                          wait=2.0)
        screen = self.screenshot()
        texts = self._read_cards(screen)
        # 文本策略 v1:战力关键词优先(伤害/强度/提高),无匹配选第一张
        best_i, best_s = 0, -1.0
        for i, t in enumerate(texts):
            s = 0.0
            for kw, w in (('伤害倍率', 3.0), ('强度提高', 2.0), ('层数提高', 2.0),
                          ('伤害', 1.0), ('提高', 0.5)):
                if kw in t:
                    s += w
            if s > best_s:
                best_i, best_s = i, s
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
                 [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
        # (event_choice 存证行已随 exogenous 流写入端退役删除——删除波 1。)
        # 选卡=safe_click(bug#1 缓解);确认=机械交回(点+固定等待,不验关;
        # 重入裁决见本方法顶部)。原 r315「确认落空→round_retry 计预算兜底」
        # 防线由重入裁决 + 预算耗尽 bail 承接。
        from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
            emit_overlay_confirm,
            safe_click,
        )
        safe_click(self, target, tag='cw-fortune')
        time.sleep(1.2)
        self._confirm_pending = True
        return emit_overlay_confirm(
            self, confirm_point=self.CONFIRM,
            entry_keyword='命运卜者', tag='cw-fortune')

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[FortuneObservation,
                                     OperationRoundResult | None]:
        """段1 observe:本屏无 op 内入口门(入口判定归主循环 0 系分发,
        分发即门)→ 轻观察 payload 直接交后续段(盛会之星同式,帧引用
        载体)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: FortuneObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (卡面 OCR/文本策略/遥测/点卡/确认收尾全部原位,两路径共享零转录)。
        段5 on_outcome = 本屏无落地登记件(注册表缺席 = 零动作,见 __init__
        申报);轮次结果语义在共享体内逐位保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay()
        self._lifecycle_mark('act')
        return rs
