# live-verified 2026-08-21(局32 P2r2 卡死 30min 后建;交互实锤:点卡下半部
# y≈480 选中,确认 (1491,600) 消费成功——同策划事件坐标族)。

"""货币战争 命运卜者「强化效果三选一」overlay 处理 op(r115)。

事件族:策划系 overlay(标题=事件名+「请选择N个强化效果」+N 卡+Q 详情+确认)。
银狼策划(r103)同族;命运卜者强化在 P2 出现(黑天鹅/奥迹系强化)。
布局(局32 实拍):标题 y~58-94 / 指令 y~122 / 卡文字 y~296-405 / 三卡
x≈510/900/1290 / 确认 (1441-1543,584-615)。

识别:「请选择」+「强化效果」关键词(id_mark 由 screen_info 承担)。
策略:OCR 三卡文字 → 判据单一源 = kernel ``cw_events.decide_fortune``
(战力关键词权重 argmax,无匹配缺省卡 1;本文件零内联打分,判据本体
单一源),消费唯一入口 = 策略器零参 ``decide_fortune()``,
写槽 → 零参决策,handler 零打分实现。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。本屏无 op 内入口门(入口判定归主循环阶段一身份分发,
分发即门)→ 观察 node = 三卡位 OCR 一次读 + 三卡点击坐标(入口帧一次读,
与现役决策体读同帧等价;坐标 = area 主源 + 兜底)→
``report_screen_fortune_obs`` 双写容器 ``fortune_opts``/``fortune_opts_xy``
(无空门,空表照写)→ obs 挂实例属性进决策 node。决策动作 node = 重入裁决
顶部(入口词「命运卜者」不在 = overlay 已关 → success 交回)→ 决策从容器
零参读;无 match = 零决策零点击 round_success 终结交回(op-layer.md §1.1
:37)→ 两守卫(返回词表外/None = 具名 round_fail 零盲发;idx 越界 = 守卫
断言 AssertionError;策略异常自然传播)→ 选卡+确认链经
``CwActionPickFortuneOp`` 派发(pick-op-unify 批机械链迁入动作 op)→
round_wait 循环(不烧节点重试预算,无防御上限;确认未落地轮重走)。
本屏无 chosen_* 写端(fields.md §4「事件选择」在册:写端未接线 = 先补档;
选择后果走下一帧观察覆盖);本屏 sim 腿
= 不适用(sim 无对应画面段,事件浮层族即时落定),等价判据主承重 = 实机
在册行为锁。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
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
    # ⚠️ 待实机核(载体迁移非新证):卡位/文字带 = 2026-08-21 live 实锤
    # 字面量(文件头实拍布局);坐标已 area 化 = cw_fortune_picker.yml
    # 「卡-强化1/2/3」(中心 = 本组字面量平移,同真值),本组常量 = 观察
    # 侧 None 回退兜底;三区实机点击落点挂账实机批。
    # 消费点 = 观察 node 坐标上报(area 主源 + 兜底,坐标随报条款)与
    # 守卫②槽数界;执行侧不自算坐标。
    # 三卡卡身(选中点击点=卡下半部,避详情按钮 y~430-462;同策划事件教训)
    CARD_XS: ClassVar[tuple[int, ...]] = (510, 900, 1290)
    CARD_Y: ClassVar[int] = 480
    TEXT_Y_LO: ClassVar[int] = 290
    TEXT_Y_HI: ClassVar[int] = 410

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
        """三卡位 OCR 一次读 + 三卡点击坐标 → report 双写容器
        ``fortune_opts``/``fortune_opts_xy``(无空门,空表照写;match/gs
        缺席的局外路径跳过 report——report 跳写 = 容器写闸,与决策无关;
        决策面无局外兜底,无 match = 零决策零点击 round_success 终结交回
        (op-layer.md §1.1 :37,遭遇屏先例同款),守卫见 act)。"""
        screen = self.last_screenshot
        options = self._read_cards(screen)
        option_points: list[tuple[int, int]] = []
        for i in range(len(self.CARD_XS)):
            pt = area_center(self.ctx, f'卡-强化{i + 1}', self.SCREEN_NAME)
            if pt is None:
                # 兜底常量与建档同真值(2026-08-21 live 实锤字面量平移),
                # 防建档误删致观察断裂,非第二坐标源(§3.4.5a「禁二次取点
                # 回退」辖动作/上报层读端,观察写门内唯一出口不受涉)。
                log.warning('[cw][fortune] 建档「卡-强化%d」读缺,坐标回退兜底常量',
                            i + 1)
                option_points.append((self.CARD_XS[i], self.CARD_Y))
            else:
                option_points.append((pt.x, pt.y))
        obs = CwScreenFortuneObs(on_screen=True,
                                 options=options,
                                 option_points=option_points,
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

        重入裁决(观察驱动;形态正本 = screens/op-layer.md §1.1「重入裁决
        留在决策动作 node 顶部」):本屏分发即门(无 op 内入口守卫),
        round_wait 重入不经外循环分发 → 顶部出口门补位:入口词不在 =
        overlay 已关(上轮确认已落地)→ success 交回外循环;在 = 重走
        选卡+确认。

        决策出口守卫:无 match = 零决策零点击 round_success 终结交回
        (op-layer.md §1.1 :37,遭遇屏先例同款);决策返回词表外/None =
        具名 round_fail 零盲发;idx 越界 = 守卫断言 AssertionError;策略
        异常自然传播(离屏失约 ValueError 不再被吞)——守卫均在派发前、
        零点击;派发 env 仅携 op,点击坐标 = 动作 op 自容器读(坐标随报
        条款)。"""
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_ocr(self.last_screenshot, '命运卜者',
                                     lcs_percent=0.5).is_success:
                return self.round_success('命运卜者强化已确认(重入观察裁决)',
                                          wait=2.0)
        texts = self._obs.options if self._obs is not None else []
        _match = getattr(self.ctx, 'cw_match', None)
        # 守卫⓪(局外,op-layer.md §1.1 :37):无 match = 零决策零点击
        # round_success 终结交回(遭遇屏先例同款);kernel 直调兜底派发退役
        # ——「此类支持代码不做」,不设任何兜底决策路径。
        if _match is None:
            return self.round_success(
                '[cw][fortune] 局外无 match,零决策零点击终结交回(op-layer §1.1 :37)')
        pick = _match.strategy.decide_fortune()
        # 守卫①(返回契约):词表外/None = 决策无有效输出,具名 fail 零盲发
        # (op-layer.md §1.1 出口③);消息含原值 repr = 留证。
        if not isinstance(pick, CwActionPickFortuneParam):
            return self.round_fail(
                f'[cw][fortune] decide_fortune 决策无有效输出(词表外/None): {pick!r}')
        # 守卫②(值域):idx 越界 = 策略器 bug,守卫断言响亮暴露,禁钳位
        # (op-layer.md §1.3);界 = CARD_XS 槽数(与候选槽 fortune_opts 恒 3 同长)。
        if not (0 <= pick.idx < len(self.CARD_XS)):
            raise AssertionError(
                f'[cw][fortune] pick idx 越界(策略器 bug,禁钳位): '
                f'idx={pick.idx} 槽数={len(self.CARD_XS)} pick={pick!r}')
        _card_text = texts[pick.idx] if 0 <= pick.idx < len(texts) else ''
        log.info('[cw][fortune] 命运卜者强化:卡=%s → 选卡%d(%s)',
                 [t[:12] for t in texts], pick.idx + 1, _card_text[:20] or 'OCR空')
        # 选卡+确认链经工厂直发(派发实例 = 策略产 CwActionPickFortuneParam,
        # 守卫后直发;上报 param 即真实选择)。env 仅携 op——点击坐标 =
        # 动作 op 按下标自容器 fortune_opts_xy 读(坐标随报条款),env.idx/
        # target 停喂。round_wait 推进循环(不烧节点重试预算;确认未落地轮
        # 重走,无防御上限)。
        self._confirm_pending = True
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self)
        action_op_for(pick, self.ctx, _env).execute()
        return self.round_wait()
