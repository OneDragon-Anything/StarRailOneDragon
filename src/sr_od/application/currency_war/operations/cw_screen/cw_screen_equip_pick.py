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
策略:卡名 OCR → 判据单一源 = kernel
``cw_equip_value.decide_equip_overlay_pick``(已锁线 key_fit_names 子串
+100 / 泛用关键词 +1.0;普查迁移批 2 自本文件 handler 打分收编),消费
唯一入口 = 策略器零参 ``decide_equip_pick()``(契约扩员 12→15),写槽 →
零参决策,handler 零判据零意向读。locked_comp 意向读随判据迁策略侧
(策略入口自 self.state 取值注入 kernel 参数,终态契约 §2.5 参数注入桶);
S13 裁定语义随判据在 kernel 注释在案:未锁线无任何绑定项(stash/伪 comp
方向不再进装备选择)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(验收评审统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):handle 体纯移入 ``_handle_overlay``
(两路径共享零转录);**本屏无 op 内入口门**(入口判定归主循环 0 系分发
双 id_mark,observe 段 = 轻观察帧引用);本屏无 on_outcome 落地登记件
(§6.4 收编面无事件屏 chosen 行;equip_pick 无 chosen_* 写端,选择存证行已
随删除波 1 退役)。本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面
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
        # 选卡点击已发待重入裁决标志(验证废除形态):本屏分发即门(无 op 内
        # 入口守卫),重入出口裁决见 _handle_overlay 顶部。
        self._pick_pending: bool = False

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
        盛会之星 ``_do_action`` 共享式)。key_equips 打分语义逐位保留;重读
        选中态验效半拆除(用户裁定 2026-09-10:动作 op 禁验证),落地由重入
        出口门裁决。"""
        # 重入裁决(观察驱动,M7 同化先例):本屏分发即门(无 op 内入口守卫),
        # round_retry 重入不经外循环分发 → 顶部出口门补位:「请选择」不在 =
        # overlay 已关(点卡即选已落地)→ success 交回外循环(出战按钮由
        # 主流程处理);在 = 重走选卡(计节点预算)。
        if self._pick_pending:
            self._pick_pending = False
            if not self.round_by_ocr(self.screenshot(), '请选择',
                                     lcs_percent=0.5).is_success:
                return self.round_success(status='装备选择完成(重入观察裁决)')
        screen = self.screenshot()
        texts = self._read_cards(screen)
        # 选卡判据(普查迁移批 2:单一源 = kernel decide_equip_overlay_pick;
        # 唯一入口 = 策略对象,handler 禁自拟打分与意向读,kernel 直调仅无
        # match 防御路径)。写槽 → 零参决策(终态契约 §2.7);locked_comp
        # 由策略入口自 self.state 注入 kernel(本 handler 零意向读)。
        best_i = 0
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    ChannelSig,
                )
                _match.gs.write_logic(
                    _match.gs.equip_pick_opts, list(texts),
                    produced_by='CwScreenEquipPick',
                    sig=ChannelSig(family='logic_action',
                                   actor='CwScreenEquipPick', mode='compute'))
                best_i = _match.strategy.decide_equip_pick().idx
                if not (0 <= best_i < len(self.CARD_XS)):
                    best_i = 0   # 越界防御 = 缺省首卡(判据侧并列同款)
            except Exception as e:   # noqa: BLE001  策略失败 fallback 第1张
                log.warning('[cw-equip-pick] 策略决策异常(fallback 第1张): %s',
                            e)
                best_i = 0
        else:
            # 无 match 局外兜底(已申报豁免面):kernel 直调,未锁态语义
            #(仅泛用腿)= 原 handler 空 key_fit 集分支同款
            from sr_od.application.currency_war.kernel.cw_equip_value import (
                decide_equip_overlay_pick,
            )
            best_i = decide_equip_overlay_pick(list(texts))
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw-equip-pick] 装备选择:卡=%s → 选卡%d(%s)',
                 [t[:10] for t in texts], best_i + 1, texts[best_i][:16] or 'OCR空')
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.2)
        # 单选即定(出战按钮由主流程处理);机械交回(验证废除):「请选择」
        # 标题在不在由下一轮重入出口门裁决(本方法顶部)。
        self._pick_pending = True
        return self.round_retry(wait=1, status='装备选择点击已发,重入观察裁决')

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
