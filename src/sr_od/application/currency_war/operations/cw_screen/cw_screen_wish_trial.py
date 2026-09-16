# 已接入 cw_loop:255(2026-08-08 实测:bot 卡此 overlay 68min 后接入检测 + CwScreenWishTrial 点卡+确认+验关;出战不再被 overlay 卡,D-87~89 闭环)。
# r104(2026-08-20):选卡接入策略模块 decide_wish_trial(用户定调「所有 overlay 选择都接策略」)——
# OCR 各卡 objective 文字 → 策略打分(金币/阵营相关/操作向)→ 点选中卡。OCR 失败 fallback 第 1 张。

"""货币战争 祈愿试炼 overlay 处理 op(事件长尾:2026-08-08 实跑发现,bot 卡此 overlay 68min)。

「祈愿试炼」= **节点级 quest 选择 overlay**(出现在特定节点前,如「再临仪式-二」「遭遇战」):
选 1 个试炼 → 该节点/本局完成 objective(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」)
→ 得奖励(金币 / 阵营星徽)。overlay 叠在备战上,**挡备战分支** → 必须在备战分支(1)前检测处理。

交互(2026-08-08 实测):ESC **不关**;点试炼卡身 → 选中(金色边框 + 确认选择亮)→ 点
「确认选择」→ overlay 关回备战。候选卡数/内容随节点变(实测 2 张)。

统一观察架构逐屏迁移(试点步骤 3;架构设计 §9.2 迁移步骤 4 + 开放问题清单
B3 三段走第二段「补给 + 余事件屏按族批量」):本类是 CwScreenOpBase 子类,
handle 顶部装配点分流(两端口完整在场 → 五段生命周期新路径;缺省 None =
生产直连旧路径,生产行为零变化 §9.1)。迁移手法单一源 = 盛会之星先例
(验收评审统一形态注意项 = lifecycle_observe
消费 ``_observation_port()`` 位):门后选卡+确认链纯移入 ``_handle_overlay``
(两路径共享零转录);本屏无 on_outcome 落地登记件(§6.4 收编面无事件屏
chosen 行;chosen_wish = 重入裁决点单次逻辑写入豁免 §2.2/§6.5-6,留守
裁决出口——用户裁定 2026-09-14 验关残留修:确认后同轮「标识消失」判
拆除,改 pending+重入裁决,照星徽款)。本屏 sim 腿 = 不适用(F11 例外清单:
sim 无对应画面段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_game_state_consume chosen_wish 接线锁 + 本批锁
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
class WishTrialObservation:
    """祈愿试炼观察 payload(五段之段1产物;试点步骤 3 实机转录形态)。

    observe 段 = 入口门 + 帧引用(objective OCR 读取归共享动作体现役内聚,
    避免新增读屏;实机识别域载体,不出端口,架构设计 §2.1;sim 适配器 =
    不适用,F11 例外清单)。
    """

    screen: Any = None


class WishTrialLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口,试点步骤 3)。

    本屏 observe = 入口门已归 ``lifecycle_observe``;适配器仅装配帧引用。
    sim 实现 = 不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenWishTrial') -> WishTrialObservation:
        return op._observe_frame()


class CwScreenWishTrial(CwScreenOpBase):
    """祈愿试炼 overlay:OCR objective → decide_wish_trial 策略选卡 → 确认 → 验关。"""

    # ⚠️ 待实机核(坐标单一源清点项):以下卡位为实测字面量,未 area 化
    # (确认按钮已 area 化;卡身建档挂账实机批——本批实机纪律不可测)。
    CARD_Y: ClassVar[int] = 340
    # 卡 x 中心(实测左卡 660 命中;多卡间距 ~300;读 objective 后近邻分流)
    CARD_XS: ClassVar[tuple[int, ...]] = (660, 960, 1260)
    TEXT_Y_LO: ClassVar[int] = 250
    TEXT_Y_HI: ClassVar[int] = 400
    FIRST_CARD: ClassVar[Point] = Point(660, 340)

    def __init__(self, ctx: SrContext):
        # r116 热修(局33 实证:r104 重写本类时漏传 ctx → 祈愿试炼触发即崩,
        # loop 空转 553 iter;签名对齐其他 handler)
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-祈愿试炼')
        # 适配器位缺省装配(试点步骤 3;先例 = CwScreenPrep/盛会之星):观察口 =
        # 实机适配器(入口门 + 帧引用封口);动作口 = None = 直连现役共享体
        # ``_handle_overlay``(多步链,无单意图 act 分派面)。on_outcome 注册
        # 表:本屏无落地登记件(§6.4 收编面无事件屏 chosen 行,见模块
        # docstring)。
        self._observation_adapter = WishTrialLiveObservationAdapter()
        # 确认已发待重入裁决的选卡 (objs, pick_idx) 快照(验证废除形态,
        # 照星徽款/遭遇款 pending+重入裁决;用户裁定 2026-09-14 验关残留修):
        # 确认点击发出后置位,下一轮重入由入口观察裁决——标识不在 = overlay
        # 已关(选卡落地)→ 此刻才写 chosen_wish;标识在 = 确认未落地 → 清
        # 标志重走(计节点预算,重读重选)。None = 无待裁决选卡。
        self._confirm_pending: tuple[list[str] | None, int] | None = None

    def _observe_frame(self) -> WishTrialObservation:
        """轻观察帧装配(实机适配器①封口内容):入口门在 observe 段,
        本方法仅携带当前帧引用(objective 读取归共享体现役内聚)。"""
        return WishTrialObservation(screen=self.last_screenshot)

    def _read_objectives(self, screen) -> list[str]:
        """OCR 各卡 objective 文字 → 按 x 近邻分流到卡槽。"""
        ocr = self.ctx.ocr_service.get_ocr_result_list(screen, crop_first=False)
        buckets: dict[int, list[str]] = {x: [] for x in self.CARD_XS}
        for o in ocr:
            t = (o.data or '').strip()
            if not t or not (self.TEXT_Y_LO <= o.y + o.h // 2 <= self.TEXT_Y_HI):
                continue
            cx = o.x + o.w // 2
            nearest = min(self.CARD_XS, key=lambda x: abs(x - cx))
            if abs(nearest - cx) < 160:
                buckets[nearest].append(t)
        return [' '.join(buckets[x]) for x in self.CARD_XS]

    @operation_node(name='祈愿试炼', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        # 重入裁决(观察驱动,验证废除形态,照星徽款 pending+重入裁决;
        # 用户裁定 2026-09-14 验关残留修):上轮确认已发 → 标识不在 =
        # overlay 已关(选卡落地)→ 此刻才写 chosen_wish + success 交回;
        # 标识在 = 确认未落地 → 清标志重走(计节点预算,重读重选)。
        # 两路径共用(分流前挂,先于五段 lifecycle 的 observe 门)。
        if self._confirm_pending is not None:
            _objs, _pick_idx = self._confirm_pending
            self._confirm_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, '货币战争-祈愿试炼',
                    '标识-祈愿试炼').is_success:
                self._record_chosen(_objs, _pick_idx)
                return self.round_success('祈愿试炼选卡已确认(重入观察裁决)',
                                          wait=2)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run):
        # cw_game_ports 两端口完整在场(= 测试 harness 显式装配)→ 五段生命
        # 周期新路径;缺省 None = 生产直连旧路径(下方原序列,试点等价门
        # 通过前生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return self.round_fail('非祈愿试炼屏')
        return self._handle_overlay(screen)

    def _handle_overlay(self, screen) -> OperationRoundResult:
        """门后选卡+确认链(旧 handle 门后体纯移入,两路径共享零转录;
        试点步骤 3,先例 = 盛会之星 ``_do_action`` 共享式)。确认 = 机械
        交回(用户裁定 2026-09-14:删确认后同轮「标识消失」判),落地判定
        归 handle 顶部重入裁决;chosen_wish 写端 = 重入裁决点承载
        (单次逻辑写入豁免 §2.2)。"""
        # 策略决策(r104):OCR objective → decide_wish_trial → 对应卡
        target = CwScreenWishTrial.FIRST_CARD
        pick_desc = 'fallback第1张'
        objs: list[str] | None = None   # 策略分支外的兜底路径也留选项面(None=未读到)
        pick_idx = 0
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                objs = self._read_objectives(screen)
                # 决策输入消费切换(迁移批次二):GameState 视图替 last_state 直读。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of,
                )
                _st = game_state_of(_match.session)
                idx = _match.strategy.decide_wish_trial(
                    objs, _st, _match.session, getattr(_match, 'config', None))
                if 0 <= idx < len(self.CARD_XS):
                    target = Point(self.CARD_XS[idx], CwScreenWishTrial.CARD_Y)
                    pick_idx = idx
                    pick_desc = f'卡{idx + 1}({objs[idx][:20] or "OCR空"})'
            except Exception as e:   # noqa: BLE001  策略失败 fallback 第1张
                log.warning('[cw-wish] 策略决策异常(fallback 第1张): %s', e)
        log.info('[cw-wish] 祈愿决策: %s → 点 (%s,%s)', pick_desc, target.x, target.y)
        # (wish_trial objective 存证行已随 exogenous 流写入端退役删除——删除波 1。)
        # 点卡选中(bug#1 缓解:mouse_move 先,零移动落 click,防 before_screenshot 移光标)。
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.0)
        # 确认选择(本屏 area 位置;祈愿试炼 独有检测在前,不与 partner/megastar 的「确认选择」撞)。
        self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择', success_wait=1.5)
        # 机械交回(验证废除,用户裁定 2026-09-14 删确认后同轮「标识消失」
        # 判——同轮验关 = 退役的落地回执消费形态):确认是否落地由下一轮
        # 重入裁决(handle 顶部 pending 分支)承载,chosen_wish 写端随之移
        # 至裁决点;未落地轮重走重选(计节点预算)。
        self._confirm_pending = (objs, pick_idx)
        return self.round_retry(wait=1)

    def _record_chosen(self, objs: list[str] | None, pick_idx: int) -> None:
        """选卡落地记录面:写 ``chosen_wish``(设计 §3.4.5 单选事件屏
        chosen_* 写端;单次逻辑写入,§3.4 申报豁免)。

        值 = 选中卡 objective 原文名(OCR 分桶 join 语义)。守卫口径=事实落地选择记录(含策略降级路径的选择,区别于 tome 的决策不可判不写式);
        chosen_tome 式(CwScreenBookcard):objective 未读到(None)/选中槽
        文本为空 = 盲选 fallback 第 1 张,不写(None 保持「无记录」)。
        记录面失败不阻塞本轮成功。"""
        _sess = getattr(getattr(self.ctx, 'cw_match', None), 'session', None)
        if _sess is None or not objs or not (0 <= pick_idx < len(objs)):
            return
        _text = objs[pick_idx].strip()
        if not _text:
            return
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                ChannelSig,
                game_state_of,
            )
            _gs = game_state_of(_sess)
            _gs.write_logic(_gs.chosen_wish, _text,
                            produced_by='CwScreenWishTrial',
                            sig=ChannelSig(family='logic_action',
                                           actor='CwScreenWishTrial',
                                           mode='compute'))
        except Exception as e:   # noqa: BLE001  记录面失败不阻塞
            log.warning(f'[cw-wish] chosen_wish 记录失败(不阻塞): {e}')

    # ---- 五段生命周期(统一观察架构 §5.1;试点步骤 3,先例 = 盛会之星)----

    def lifecycle_observe(self
                          ) -> tuple[WishTrialObservation,
                                     OperationRoundResult | None]:
        """段1 observe:入口门(标识-祈愿试炼,旧 handle 首闸逐位转录)→
        轻观察 payload。门失败 = round_fail 早退(与旧 handle 同 status),
        后续段不执行。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return (WishTrialObservation(screen=screen),
                    self.round_fail('非祈愿试炼屏'))
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else self._observe_frame())
        return obs, None

    def lifecycle_decision_cycle(self, payload: WishTrialObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作内聚):decide+act 内聚于 ``_handle_overlay`` 共享体
        (objective OCR/决策/遥测/点卡/确认/chosen 写端全部原位,两路径
        共享零转录;同轮验关已拆,用户裁定 2026-09-14——落地判定与 chosen
        写端归重入裁决点)。段5 on_outcome = 本屏无落地登记件(注册表缺席
        = 零动作,见 __init__ 申报);轮次结果语义在共享体内逐位保留
        (段迹到 act)。"""
        self._lifecycle_mark('decide')
        rs = self._handle_overlay(payload.screen)
        self._lifecycle_mark('act')
        return rs
