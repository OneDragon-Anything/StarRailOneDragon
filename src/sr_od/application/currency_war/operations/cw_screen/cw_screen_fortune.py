# live-verified 2026-08-21(局32 P2r2 卡死 30min 后建;交互实锤:点卡下半部
# y≈480 选中,确认 (1491,600) 消费成功——同策划事件坐标族)。

"""货币战争 命运卜者「强化效果三选一」overlay 处理 op(r115)。

事件族:策划系 overlay(标题=事件名+「请选择N个强化效果」+N 卡+Q 详情+确认)。
银狼策划(r103)同族;命运卜者强化在 P2 出现(黑天鹅/奥迹系强化)。
布局(局32 实拍):标题 y~58-94 / 指令 y~122 / 卡文字 y~296-405 / 三卡
x≈510/900/1290 / 确认 (1441-1543,584-615)。

识别:「请选择」+「强化效果」关键词(id_mark 由 screen_info 承担)。
策略:OCR 三卡文字 → 判据单一源 = kernel ``cw_events.decide_fortune``
(战力关键词权重 argmax,无匹配缺省卡 1;普查迁移批 2 自本文件 v1 内联
文本规则收编),消费唯一入口 = 策略器零参 ``decide_fortune()``,
写槽 → 零参决策,handler 零打分实现。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。本屏无 op 内入口门(入口判定归主循环 0 系分发,
分发即门)→ 观察 node = 三卡位 OCR 一次读(入口帧一次读,与现役决策体读
同帧等价)→ ``report_screen_fortune_obs`` 落容器 ``fortune_opts``(无空门,
空表照写)→ obs 挂实例属性进决策 node。决策动作 node = 重入裁决顶部
(入口词「命运卜者」不在 = overlay 已关 → success 交回)→ 决策从容器零参
读(kernel 直调仅无 match 防御路径)→ 选卡+确认链经 ``CwActionPickFortuneOp``
派发(pick-op-unify 批机械链迁入动作 op)→ round_wait 循环(不烧节点重试
预算,无防御上限;确认未落地轮重走)。
本屏无 chosen_* 写端(fortune 选择存证行已随删除波 1 退役);本屏 sim 腿
= 不适用(sim 无对应画面段,事件浮层族即时落定),等价判据主承重 = 实机
在册行为锁。
"""
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.fortune import (
    CwScreenFortuneObs,
    report_screen_fortune_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickFortuneParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenFortune(SrOperation):
    """命运卜者强化三选一:OCR 卡文字 → 文本策略选卡 → 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-命运卜者强化'   # screen_info 画面(cw_fortune_picker.yml)
    # ⚠️ 待实机核(坐标单一源清点项):以下卡位/文字带为 2026-08-21 live 实锤字面量
    # (文件头实拍布局),未 area 化(本批实机纪律不可测,建档挂账实机批)。
    # 三卡卡身(选中点击点=卡下半部,避详情按钮 y~430-462;同策划事件教训)
    CARD_XS: ClassVar[tuple[int, ...]] = (510, 900, 1290)
    CARD_Y: ClassVar[int] = 480
    TEXT_Y_LO: ClassVar[int] = 290
    TEXT_Y_HI: ClassVar[int] = 410
    # 确认按钮兜底常量(首选 area_center('按钮-确认选择'):建档 cw_fortune_picker.yml
    # rect (1420,575,1560,625) 中心 (1490,600),与本常量同按钮差 1px;同策划事件坐标族)
    CONFIRM: ClassVar[Point] = Point(1491, 600)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-命运卜者强化')
        # 确认已发待重入裁决标志(验证废除形态):本屏分发即门(无 op 内入口
        # 守卫),重入出口裁决区分「首发 miss」与「重入 miss(= overlay 已关
        # → success 交回)」,见决策动作 node 顶部。
        self._confirm_pending: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;options = 入口帧一次读)。
        self._obs: CwScreenFortuneObs | None = None

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

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """三卡位 OCR 一次读 → report 落容器(无空门,空表照写;match/gs
        缺席的局外兜底路径跳过 report,决策走 kernel 直调防御分支,分支
        原样)。"""
        screen = self.last_screenshot
        obs = CwScreenFortuneObs(on_screen=True,
                                 options=self._read_cards(screen),
                                 screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_fortune_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 选卡+确认机械交回 → round_wait。

        重入裁决(观察驱动,M7 同化先例 + cw_entry_start 守卫先例):本屏
        分发即门(无 op 内入口守卫),round_wait 重入不经外循环分发 →
        顶部出口门补位:入口词不在 = overlay 已关(上轮确认已落地)→
        success 交回外循环;在 = 重走选卡+确认。"""
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_ocr(self.last_screenshot, '命运卜者',
                                     lcs_percent=0.5).is_success:
                return self.round_success('命运卜者强化已确认(重入观察裁决)',
                                          wait=2.0)
        texts = self._obs.options if self._obs is not None else []
        # 选卡判据(普查迁移批 2:单一源 = kernel decide_fortune;唯一入口
        # = 策略对象,handler 禁自拟打分,kernel 直调仅无 match 防御路径
        # ——cw_screen_yinlang 同款)。写槽已由 report 落容器 → 零参决策;
        # 本屏无 chosen 写端(fortune 选择存证行已随删除波 1 退役)。
        best_i = 0
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
                best_i = _match.strategy.decide_fortune().idx
                if not (0 <= best_i < len(self.CARD_XS)):
                    best_i = 0   # 越界防御 = 缺省首卡(判据侧无匹配同款)
            except Exception as e:   # noqa: BLE001  策略失败 fallback 第1张
                log.warning('[cw][fortune] 策略决策异常(fallback 第1张): %s', e)
                best_i = 0
        else:
            # 无 match 局外兜底(已申报豁免面):kernel 直调,零策略构造
            from sr_od.application.currency_war.kernel.cw_events import (
                decide_fortune,
            )
            best_i = decide_fortune(list(texts))
        target = Point(self.CARD_XS[best_i], self.CARD_Y)
        log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
                 [t[:12] for t in texts], best_i + 1, texts[best_i][:20] or 'OCR空')
        # 选卡+确认链经工厂(pick-op-unify 批:机械链迁入
        # ``CwActionPickFortuneOp``,本 op 只决策;定位点决策半现算经 env
        # 显式传入,确认钮定位 = op 类体内自读 screen_info)。派发实例携
        # 真实选中下标(上报 param 即真实选择;fallback/越界 = 0)。
        # round_wait 推进循环(不烧节点重试预算;确认未落地轮重走,无防御
        # 上限)。
        self._confirm_pending = True
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=best_i, target=target,
                                  entry_keyword='命运卜者')
        action_op_for(CwActionPickFortuneParam(idx=best_i), self.ctx,
                      _env).execute()
        return self.round_wait()
