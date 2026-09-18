# 已接入 cw_loop:255(2026-08-08 实测:bot 卡此 overlay 68min 后接入检测 + CwScreenWishTrial 点卡+确认+验关;出战不再被 overlay 卡,D-87~89 闭环)。
# r104(2026-08-20):选卡接入策略模块 decide_wish_trial(用户定调「所有 overlay 选择都接策略」)——
# OCR 各卡 objective 文字 → 策略打分(金币/阵营相关/操作向)→ 点选中卡。OCR 失败 fallback 第 1 张。

"""货币战争 祈愿试炼 overlay 处理 op(事件长尾:2026-08-08 实跑发现,bot 卡此 overlay 68min)。

「祈愿试炼」= **节点级 quest 选择 overlay**(出现在特定节点前,如「再临仪式-二」「遭遇战」):
选 1 个试炼 → 该节点/本局完成 objective(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」)
→ 得奖励(金币 / 阵营星徽)。overlay 叠在备战上,**挡备战分支** → 必须在备战分支(1)前检测处理。

交互(2026-08-08 实测):ESC **不关**;点试炼卡身 → 选中(金色边框 + 确认选择亮)→ 点
「确认选择」→ overlay 关回备战。候选卡数/内容随节点变(实测 2 张)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 入口门(标识-祈愿试炼,miss = round_fail 交回
外循环重判)+ objective 一次读(OCR 桶 join,入口帧一次读,与现役决策体读
同帧等价)→ ``report_screen_wish_trial_obs`` 落容器 ``wish_trial_opts``
(无空门,空桶照写)→ obs 挂实例属性进决策 node。决策动作 node = 重入裁决
顶部(确认已发 → 标识不在 = overlay 已关 → 此刻才写 chosen_wish + success
交回;在 = 确认未落地 → 清标志重走)→ 决策从容器零参读 → 点卡 + 确认 →
round_wait 循环(不烧节点重试预算,无防御上限)。chosen_wish = 重入裁决点
单次逻辑写入留守(动作事实边界,不进 report);本屏 sim 腿 = 不适用(sim
无对应画面段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_game_state_consume chosen_wish 接线锁)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.wish_trial import (
    CwScreenWishTrialObs,
    report_screen_wish_trial_obs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenWishTrial(SrOperation):
    """祈愿试炼 overlay:OCR objective → decide_wish_trial 策略选卡 → 确认。"""

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
        SrOperation.__init__(self, ctx, op_name='货币战争-祈愿试炼')
        # 确认已发待重入裁决的选卡 (objs, pick_idx) 快照(验证废除形态,
        # 照星徽款/遭遇款 pending+重入裁决;用户裁定 2026-09-14 验关残留修):
        # 确认点击发出后置位,下一轮重入由入口观察裁决——标识不在 = overlay
        # 已关(选卡落地)→ 此刻才写 chosen_wish;标识在 = 确认未落地 → 清
        # 标志重走(重读重选)。None = 无待裁决选卡。
        self._confirm_pending: tuple[list[str] | None, int] | None = None
        # 观察结果(观察 node 产物,决策动作 node 消费;options = 入口帧一次读)。
        self._obs: CwScreenWishTrialObs | None = None

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

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + objective 一次读 → report 落容器。

        门 miss = round_fail 早退(与现役首闸同 status,交回外循环重判)。
        门后 objective OCR 桶一次读 → ``report_screen_wish_trial_obs``
        (无空门,空桶照写);match/gs 缺席的局外兜底路径跳过 report
        (决策走决策面 fallback 分支,分支原样)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return self.round_fail('非祈愿试炼屏')
        obs = CwScreenWishTrialObs(on_screen=True,
                                   options=self._read_objectives(screen),
                                   screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_wish_trial_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 点卡 + 确认 → round_wait。

        重入裁决(观察驱动,验证废除形态,照星徽款 pending+重入裁决;
        用户裁定 2026-09-14 验关残留修):上轮确认已发 → 标识不在 = overlay
        已关(选卡落地)→ 此刻才写 chosen_wish + success 交回;标识在 =
        确认未落地 → 清标志重走(重读重选)。"""
        if self._confirm_pending is not None:
            _objs, _pick_idx = self._confirm_pending
            self._confirm_pending = None
            if not self.round_by_find_area(
                    self.last_screenshot, '货币战争-祈愿试炼',
                    '标识-祈愿试炼').is_success:
                self._record_chosen(_objs, _pick_idx)
                return self.round_success('祈愿试炼选卡已确认(重入观察裁决)',
                                          wait=2)
        objs = self._obs.options if self._obs is not None else []
        # 策略决策(r104):写槽已由 report 落容器 wish_trial_opts →
        # 零参决策;决策链异常 fallback 第 1 张(姊妹 handler 同姿态)。
        target = CwScreenWishTrial.FIRST_CARD
        pick_desc = 'fallback第1张'
        pick_idx = 0
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                idx = _match.strategy.decide_wish_trial().idx
                if 0 <= idx < len(self.CARD_XS):
                    target = Point(self.CARD_XS[idx], CwScreenWishTrial.CARD_Y)
                    pick_idx = idx
                    pick_desc = f'卡{idx + 1}({objs[idx][:20] or "OCR空"})'
            except Exception as e:   # noqa: BLE001  策略失败 fallback 第1张
                log.warning('[cw-wish] 策略决策异常(fallback 第1张): %s', e)
        log.info('[cw-wish] 祈愿决策: %s → 点 (%s,%s)', pick_desc, target.x, target.y)
        # 点卡选中(bug#1 缓解:mouse_move 先,零移动落 click,防 before_screenshot 移光标)。
        self.ctx.controller.mouse_move(target)
        self.ctx.controller.click(target)
        time.sleep(1.0)
        # 确认选择(本屏 area 位置;祈愿试炼 独有检测在前,不与 partner/megastar 的「确认选择」撞)。
        self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择', success_wait=1.5)
        # 机械交回(验证废除,用户裁定 2026-09-14 删确认后同轮「标识消失」
        # 判——同轮验关 = 退役的落地回执消费形态):确认是否落地由下一轮
        # 重入裁决(本方法顶部 pending 分支)承载,chosen_wish 写端随之在
        # 裁决点;未落地轮重走重选。round_wait 推进循环(不烧节点重试预算,
        # 无防御上限)。
        self._confirm_pending = (list(objs), pick_idx)
        return self.round_wait(wait=1)

    def _record_chosen(self, objs: list[str] | None, pick_idx: int) -> None:
        """选卡落地记录面:写 ``chosen_wish``(单次逻辑写入,申报豁免;
        调用点 = 重入裁决出口,选卡落地后值才可信)。

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
