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
唯一入口 = 策略器零参 ``decide_equip_pick()``,写槽 → 零参决策,handler
零判据零意向读。locked_comp 意向读随判据迁策略侧(策略入口自 self.state
取值注入 kernel 参数);S13 裁定语义随判据在 kernel 注释在案:未锁线无
任何绑定项(stash/伪 comp 方向不再进装备选择)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两
段直继承 SrOperation。本屏无 op 内入口门(入口判定归主循环 0 系分发双
id_mark,分发即门)→ 观察 node = 三卡位 OCR 一次读(入口帧一次读,与现役
决策体读同帧等价)→ ``report_screen_equip_pick_obs`` 落容器
``equip_pick_opts`` → obs 挂实例属性进决策 node。决策动作 node = 重入裁决
顶部(点击已发 → 「请选择」不在 = 落地 → 装备腿落地相按证据闩应用一次
(零写族迁出批:上报 = report_action_pick_equip_param 两相语义,归一件名
= normalize_equip_name 现算;银狼闭环 design §2.2 确定性通道)→ success
交回)→ 决策从容器零参读 → 点卡 → round_wait 循环(不烧节点重试预算,无
防御上限;选卡点击已发未落地轮重点选)。本屏无 chosen_* 写端(选择存证行
已随删除波 1 退役);
本屏 sim 腿 = 不适用(sim 无对应画面段,事件浮层族即时落定),等价判据
主承重 = 实机在册行为锁。
"""
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.pick_equip import (
    EVIDENCE_OVERLAY_CLOSED,
    report_action_pick_equip_param,
)
from sr_od.application.currency_war.kernel.cw_events import normalize_equip_name
from sr_od.application.currency_war.kernel.cw_game_state import ChannelSig
from sr_od.application.currency_war.kernel.cw_screen_report.equip_pick import (
    CwScreenEquipPickObs,
    report_screen_equip_pick_obs,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickEquipParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenEquipPick(SrOperation):
    """选择装备三选一:OCR 卡名 → 策略选卡(点卡即选,出战按钮由主流程点)。"""

    # ⚠️ 待实机核(坐标单一源清点项):以下卡位为 2026-08-20 实拍字面量,
    # 未 area 化(本批实机纪律不可测,建档 area 化挂账实机批);布局变更需实拍重校。
    CARD_XS: ClassVar[tuple[int, ...]] = (780, 1070, 1380)
    CARD_Y: ClassVar[int] = 280          # 卡名带中心(避开下方详情按钮 y≈310)
    TEXT_Y_LO: ClassVar[int] = 235
    TEXT_Y_HI: ClassVar[int] = 300

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-选择装备')
        # 选卡点击已发待重入裁决标志(验证废除形态):本屏分发即门(无 op 内
        # 入口守卫),重入出口裁决见决策动作 node 顶部。
        self._pick_pending: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;options = 入口帧一次读)。
        self._obs: CwScreenEquipPickObs | None = None
        # 已派发选择载荷(装备腿落地相证据闩消费;类级缺省 None = 局外
        # 桩替 __init__ 的兜底路径同样安全)。
        self._pending_pick: CwActionPickEquipParam | None = None

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

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """三卡位 OCR 一次读 → report 落容器(入口帧一次读,与现役决策体
        读同帧等价;本屏无 op 内入口门,分发即门)。match/gs 缺席的局外
        兜底路径跳过 report(决策走 kernel 直调防御分支,分支原样)。"""
        screen = self.last_screenshot
        obs = CwScreenEquipPickObs(on_screen=True,
                                   options=self._read_cards(screen),
                                   screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_equip_pick_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=5)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 零参决策 → 点卡 → round_wait 循环。

        重入裁决(观察驱动,M7 同化先例):本屏分发即门(无 op 内入口守卫),
        round_wait 重入不经外循环分发 → 顶部出口门补位:「请选择」不在 =
        overlay 已关(点卡即选已落地)→ 装备腿落地相按证据闩应用一次
        (report_action_pick_equip_param;零写族迁出批,银狼闭环 design
        §2.2 确定性通道)后 success 交回外循环(出战按钮由主流程处理);
        在 = 重走选卡(重点选,证据未到效果腿不应用)。"""
        if self._pick_pending:
            self._pick_pending = False
            if not self.round_by_ocr(self.last_screenshot, '请选择',
                                     lcs_percent=0.5).is_success:
                _param, self._pending_pick = self._pending_pick, None
                _match = getattr(self.ctx, 'cw_match', None)
                _gs = getattr(_match, 'gs', None) if _match is not None else None
                if _param is not None and _gs is not None:
                    report_action_pick_equip_param(
                        _gs, _param,
                        ChannelSig(family='logic_action',
                                   actor='CwScreenEquipPick', mode='compute'),
                        evidence=EVIDENCE_OVERLAY_CLOSED)
                return self.round_success(status='装备选择完成(重入观察裁决)')
        texts = self._obs.options if self._obs is not None else []
        # 选卡判据(普查迁移批 2:单一源 = kernel decide_equip_overlay_pick;
        # 唯一入口 = 策略对象,handler 禁自拟打分与意向读,kernel 直调仅无
        # match 防御路径)。写槽已由 report 落容器 → 零参决策;locked_comp
        # 由策略入口自 self.state 注入 kernel(本 handler 零意向读)。
        best_i = 0
        _match = getattr(self.ctx, 'cw_match', None)
        if _match is not None:
            try:
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
        # 选中件载荷(零写族迁出批,照 PickInvest 先例):归一件名 = 判定
        # 单源 normalize_equip_name 现算,OCR 原始卡名不静默改写由 handler
        # 持有;随发射进上报意图遥测 + 本实例待落地存证(重入裁决出口消费)。
        _opt_text = texts[best_i] if 0 <= best_i < len(texts) else ''
        _param = CwActionPickEquipParam(idx=best_i,
                                        norm_item=normalize_equip_name(_opt_text))
        self._pending_pick = _param
        log.info('[cw-equip-pick] 装备选择:卡=%s → 选卡%d(%s) item=%s',
                 [t[:10] for t in texts], best_i + 1,
                 _opt_text[:16] or 'OCR空', _param.norm_item or '-')
        # 选卡链经工厂(pick-op-unify 批:点卡即选机械链迁入
        # ``CwActionPickEquipOp``,本 op 只决策;定位点决策半现算经 env
        # 显式传入)。派发实例携真实选中下标(上报 param 即真实选择;
        # 越界防御/策略异常 fallback = 0)。
        # 单选即定(出战按钮由主流程处理);机械交回(验证废除):「请选择」
        # 标题在不在由下一轮重入出口门裁决(本方法顶部)。round_wait 推进
        # 循环(不烧节点重试预算;不落地轮重点选,无防御上限)。
        self._pick_pending = True
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_action import (
            OverlayPickExecEnv,
        )
        _env = OverlayPickExecEnv(op=self, idx=best_i, target=target)
        action_op_for(_param, self.ctx, _env).execute()
        return self.round_wait(wait=1, status='装备选择点击已发,重入观察裁决')
