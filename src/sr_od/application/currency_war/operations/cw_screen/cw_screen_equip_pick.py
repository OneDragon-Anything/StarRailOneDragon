# 实拍建档 2026-08-20 09:45(局37 r3;哨兵推送 2 分钟响应闭环)。
# 布局:标题"选择装备"(1048,22-53)/副题"请选择1个"(1050,65-89)/三卡
# x≈736/1027/1350 y≈253-283(卡名带)/每卡下方"查看详情"按钮(y≈307-335)。
# 交互(VLM+布局推断):单选,选中后出战按钮确认;无独立"确认选择"按钮
# (选择伙伴屏的 确认选择 区在这里不存在——正是误派发的根因)。

"""货币战争 选择装备三选一(r129):OCR 卡名 → 策略选卡 → 点卡。

误派发根因:选择伙伴屏的 标识-选择伙伴(文本「请选择1个」)在本屏
也命中(装备选择同文案)→ CwScreenPartner 被误派发找不到确认按钮
→ 失败循环(哨兵 09:45 推送实证)。修:本屏建档(标识-选择装备 id_mark
优先)+ 本 handler + loop 分支在选择伙伴**之前**(双 id_mark:装备标题
+ 请选择1个都命中才算)。
策略:卡名 OCR → key_equips 命中(target/stash comp)+100 / 材料类次之
(与 decide_box_card 同语义,r104 家族)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(reviews/T-215-r1.md 验收;T-215-r1 §五.5 统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):handle 体纯移入 ``_handle_overlay``
(两路径共享零转录);**本屏无 op 内入口门**(入口判定归主循环 0 系分发
双 id_mark,observe 段 = 轻观察帧引用);本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;equip_pick 无 chosen_* 写端,选择落遥测
record_event_choice)。本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面
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
from sr_od.application.currency_war.telemetry.recorder import record_event_choice
from sr_od.context.sr_context import SrContext


@dataclass
class EquipPickObservation:
    """选择装备观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 轻观察帧引用(卡名 OCR 读取归共享动作体现役内聚;实机
    识别域载体,不出端口,架构设计 §2.1;sim 适配器 = 不适用,F11 例外
    清单)。
    """

    screen: Any = None


class EquipPickLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏无 op 内入口门(分发即门),适配器仅装配帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenEquipPick') -> EquipPickObservation:
        return op._observe_frame()


class CwScreenEquipPick(CwScreenOpBase):
    """选择装备三选一:OCR 卡名 → 策略选卡(点卡即选,出战按钮由主流程点)。"""

    # ⚠️ 待实机核(坐标单一源清点项):以下卡位为 2026-08-20 实拍字面量,
    # 未 area 化(本批实机纪律不可测,建档 area 化挂账实机批);布局变更需实拍重校。
    CARD_XS: ClassVar[tuple[int, ...]] = (780, 1070, 1380)
    CARD_Y: ClassVar[int] = 280          # 卡名带中心(避开下方详情按钮 y≈310)
    TEXT_Y_LO: ClassVar[int] = 235
    TEXT_Y_HI: ClassVar[int] = 300

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-选择装备')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome 注册
        # 表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = EquipPickLiveObservationAdapter()

    def _observe_frame(self) -> EquipPickObservation:
        """轻观察帧装配(实机适配器①封口内容;卡名读取归共享体现役内聚)。"""
        return EquipPickObservation(screen=self.last_screenshot)

    def _read_cards(self, screen) -> list[str]:
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
            if abs(nearest - cx) < 160:
                buckets[nearest].append(text)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='选择装备', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(原序列整体移入
        # _handle_overlay 共享体,试点等价门通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        return self._handle_overlay()

    def _handle_overlay(self) -> OperationRoundResult:
        """选卡链(旧 handle 体纯移入,两路径共享零转录;试点步骤 3,先例 =
        盛会之星 ``_do_action`` 共享式)。key_equips 打分/重读选中态语义
        逐位保留。"""
        screen = self.screenshot()
        texts = self._read_cards(screen)
        # 策略:key_equips 命中优先(与 decide_box_card 同语义)
        _match = getattr(self.ctx, 'cw_match', None)
        key_equips: list[str] = []
        if _match is not None and _match.session is not None:
            # 策略器状态读点(合法通道 = 访问函数;ADR-0563)
            from sr_od.application.currency_war.kernel.cw_strategy_session import (
                strategy_state_of,
            )
            _mst = strategy_state_of(_match.session)
            for comp in (getattr(_mst, 'target_comp', None),
                         getattr(_mst, 'stash_comp', None)):
                key_equips.extend(getattr(comp, 'key_equips', ()) or ())
        best_i, best_s = 0, -1.0
        for i, t in enumerate(texts):
            s = 0.0
            for ke in key_equips:
                if ke and ke in t:
                    s += 100.0
                    break
            if s <= 0 and any(kw in t for kw in ('伤害', '强度', '提高')):
                s = 1.0   # 泛用增益次之
            if s > best_s:
                best_i, best_s = i, s
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw-equip-pick] 装备选择:卡=%s → 选卡%d(%s)',
                 [t[:10] for t in texts], best_i + 1, texts[best_i][:16] or 'OCR空')
        # 遥测:三选一卡名+选择落账本(此前只 log)。
        record_event_choice('equip_pick', texts, best_i,
                            reason=f'key_equips/text_rule(best_score={best_s})')
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.2)
        # 单选即定(出战按钮由主流程处理);重读验证选中态/标题仍在则 retry
        screen2 = self.screenshot()
        ocr2 = self.ctx.ocr_service.get_ocr_result_map(
            image=screen2, rect=None, color_range=None, crop_first=False,
        )
        if any('请选择' in t for t in ocr2):
            return self.round_retry(wait=1, status='装备选择未生效,重试')
        return self.round_success(status=f'装备选择卡{best_i + 1}')

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[EquipPickObservation,
                                     OperationRoundResult | None]:
        """段1 observe:本屏无 op 内入口门(入口判定归主循环 0 系分发双
        id_mark,分发即门)→ 轻观察 payload 直接交后续段(盛会之星同式,
        帧引用载体)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: EquipPickObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (卡名 OCR/key_equips 打分/遥测/点卡/重读选中态全部原位,两路径共享
        零转录)。段5 on_outcome = 本屏无落地登记件(注册表缺席 = 零动作,
        见 __init__ 申报);轮次结果语义在共享体内逐位保留(段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay()
        self._lifecycle_mark('act')
        return rs
