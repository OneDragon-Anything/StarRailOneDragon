"""货币战争 祈愿试炼 overlay 处理 op(事件长尾:2026-08-08 实跑发现,bot 卡此 overlay 68min)。

「祈愿试炼」= **节点级 quest 选择 overlay**(出现在特定节点前,如「再临仪式-二」「遭遇战」):
选 1 个试炼 → 该节点/本局完成 objective(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」)
→ 得奖励(金币 / 阵营星徽)。overlay 叠在备战上,**挡备战分支** → 必须在备战分支(1)前检测处理。

交互(2026-08-08 实测):ESC **不关**;点试炼卡身 → 选中(金色边框 + 确认选择亮)→ 点
「确认选择」→ overlay 关回备战。候选卡数/内容随节点变(实测 2 张)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation。观察 node = 入口门(标识-祈愿试炼,miss = round_fail 交回
外循环重判)+ objective 一次读(OCR 桶 join,入口帧一次读,与现役决策体读
同帧等价)→ ``report_screen_wish_trial_obs`` 落容器 ``wish_trial_opts`` /
``wish_trial_opts_xy``(无空门,空桶照写,同门双写,op-layer.md §1.1 :35)
→ obs 挂实例属性进决策 node。决策动作 node = 重入裁决顶部(确认已发 →
标识不在 = overlay 已关 → 此刻才写 chosen_wish + success 交回;在 = 确认未
落地 → 清标志重走)→ 决策出口守卫:match 缺席(局外)= 零决策零点击
round_success 终结交回(op-layer.md §1.1 局外单跑条款,遭遇屏先例同款);
返回 None/词表外 = 具名 round_fail 零盲发;idx 越界 = 守卫断言
AssertionError;策略异常自然传播——守卫均在派发前、零点击 → 决策从容器
零参读 → 选卡+确认链经 ``CwActionPickWishTrialOp`` 派发(pick-op-unify 批
机械链迁入动作 op,env 仅携 op;点击坐标 = 动作 op 自容器
``wish_trial_opts_xy`` 按 idx 取,op-layer.md §1.1 :35)→ round_wait 循环
(不烧节点重试预算,无防御上限)。chosen_wish = 重入裁决点单次逻辑写入
留守(动作事实边界,不进 report);本屏 sim 腿 = 不适用(sim 无对应画面
段,事件浮层族即时落定),等价判据主承重 = 实机在册行为锁
(test_cw_game_state_consume chosen_wish 接线锁)。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_screen_report.wish_trial import (
    CwScreenWishTrialObs,
    report_screen_wish_trial_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickWishTrialParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenWishTrial(SrOperation):
    """祈愿试炼 overlay:OCR objective → decide_wish_trial 策略选卡 → 确认。"""

    # 卡位不建 screen_info area(op-layer.md §1.1 :35 辖域判据:选项点击
    # 坐标属观察上报的选项集构成数据,入坐标域;确认钮等静态控件锚维持
    # screen_info area 现取,确认按钮已 area 化)。以下卡位 = 观察侧解点
    # 锚(x = 桶锚、y = 卡身,观察期一次解析随 obs 上报
    # ``wish_trial_opts_xy``)兼决策守卫槽数界来源,决策段零坐标消费。
    CARD_Y: ClassVar[int] = 340
    # 卡 x 中心(实测左卡 660 命中;多卡间距 ~300;读 objective 后近邻分流)
    CARD_XS: ClassVar[tuple[int, ...]] = (660, 960, 1260)
    TEXT_Y_LO: ClassVar[int] = 250
    TEXT_Y_HI: ClassVar[int] = 400

    def __init__(self, ctx: SrContext):
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
        门后 objective OCR 桶一次读 + 槽位坐标观察期一次解析(x = 桶锚
        ``CARD_XS``、y = 卡身 ``CARD_Y``)→ ``report_screen_wish_trial_obs``
        同门双写容器 ``wish_trial_opts`` / ``wish_trial_opts_xy``
        (op-layer.md §1.1 :35 坐标单一真相源 = 观察上报;无空门,空桶照写);
        match/gs 缺席的局外路径跳过 report(决策面无局外兜底:无 match =
        零决策零点击 round_success 终结交回,op-layer.md §1.1 局外单跑
        条款,守卫见 act)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return self.round_fail('非祈愿试炼屏')
        # 槽位坐标观察期一次解出(x = CARD_XS 桶锚,y = CARD_Y 卡身;
        # 与 options 同序等长,随 obs 一并上报入容器)。
        option_points = [(x, CwScreenWishTrial.CARD_Y) for x in self.CARD_XS]
        obs = CwScreenWishTrialObs(on_screen=True,
                                   options=self._read_objectives(screen),
                                   option_points=option_points,
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
        确认未落地 → 清标志重走(重读重选)。

        决策出口守卫(op-layer.md §1.1/§1.3):match 缺席(局外)= 零决策
        零点击 round_success 终结交回(局外单跑条款,遭遇屏先例同款);
        返回 None/词表外 = 具名 round_fail 零盲发(出口③);idx 越界 =
        守卫断言 AssertionError;策略异常自然传播(离屏失约 ValueError 不
        再被吞)——守卫均在派发前、零点击。派发 = 策略产实例直发,env 仅
        携 op(点击坐标 = 动作 op 自容器 ``wish_trial_opts_xy`` 按 idx 取,
        坐标单一真相源 = 观察上报,op-layer.md §1.1 :35)。"""
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
        # 决策出口守卫(次序:先输入、后返回契约、再值域;均在任何点击
        # 之前——派发即发出不可逆点击链,必须派发前拦):match 缺席(局外)
        # = 零决策零点击 round_success 终结交回(op-layer.md §1.1 局外单跑
        # 条款,遭遇屏先例同款),不设任何兜底决策路径——原「盲发首卡」
        # 退役申报;返回 None/词表外 = 具名 fail 零盲发(op-layer.md §1.1
        # 出口③);idx 越界 = 守卫断言(op-layer.md §1.3);策略异常自然
        # 传播(离屏失约 ValueError 不再被吞);空候选 = 策略侧自主决策
        # (策略器返回 idx=0),非兜底。
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is None:
            return self.round_success(
                '[cw-wish] 局外无 match,零决策零点击终结交回'
                '(op-layer.md §1.1 局外单跑条款)')
        pick = _match.strategy.decide_wish_trial()
        if not isinstance(pick, CwActionPickWishTrialParam):
            return self.round_fail(
                f'decide_wish_trial 决策无有效输出(词表外/None): {pick!r}')
        if not (0 <= pick.idx < len(self.CARD_XS)):
            raise AssertionError(
                f'[cw-wish] pick idx 越界(策略器 bug,禁钳位): '
                f'idx={pick.idx} 槽数={len(self.CARD_XS)} pick={pick!r}')
        pick_desc = f'卡{pick.idx + 1}({objs[pick.idx][:20] or "OCR空"})'
        log.info('[cw-wish] 祈愿决策: %s → idx=%d', pick_desc, pick.idx)
        # 选卡+确认链经工厂直发(pick-op-unify 批:机械链迁入
        # ``CwActionPickWishTrialOp``,本 op 只决策;点击坐标 = 动作 op 自
        # 容器 ``wish_trial_opts_xy`` 按 idx 取,op-layer.md §1.1 :35,env
        # 仅携 op 零坐标)。派发实例 = 策略产 CwActionPickWishTrialParam
        # (直发零重建,上报 param = 策略产值原值)。
        # 机械交回(验证废除,用户裁定 2026-09-14 删确认后同轮「标识消失」
        # 判——同轮验关 = 退役的落地回执消费形态):确认是否落地由下一轮
        # 重入裁决(本方法顶部 pending 分支)承载,chosen_wish 写端随之在
        # 裁决点;未落地轮重走重选。round_wait 推进循环(不烧节点重试预算,
        # 无防御上限)。
        self._confirm_pending = (list(objs), pick.idx)
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self)
        action_op_for(pick, self.ctx, _env).execute()
        return self.round_wait(wait=1)

    def _record_chosen(self, objs: list[str] | None, pick_idx: int) -> None:
        """选卡落地记录面:写 ``chosen_wish``(单次逻辑写入,申报豁免;
        调用点 = 重入裁决出口,选卡落地后值才可信)。

        值 = 选中卡 objective 原文名(OCR 分桶 join 语义)。守卫口径 = 事实
        落地选择记录:objective 未读到/选中槽文本空不写(None 保持「无记录」,
        与 chosen_tome 式同口径);策略异常 = 决策出口守卫 fail 零盲发,不
        存在降级选择轮,故无『策略降级路径选择』记录。记录面失败不阻塞
        本轮成功。"""
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
