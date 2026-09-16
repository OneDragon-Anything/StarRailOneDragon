"""货币战争 BOSS 简报 op(W971 P3b 返工:06-overlays §3 设计落地)。

boss 节点前弹「强敌来袭」简报横幅:识别「标识-强敌来袭」/「强敌」片段
(#26 建档)→ 点空白推进 → **直接交回外循环重判**(新架构:点掉后去向
由 loop 全分支自然处理——boss 战自动开打/备战流转;旧「轮询备战商店开」
完成承诺实证错误:boss 简报点掉后直接开 boss 战,商店永不开,等锚必超时,
第七局/第八局接管实录)。

接线教训(P3b 实机第三局走查实锤):主循环判定序无此分支时,boss 简报帧
(横幅遮挡观察,SIFT 双空读)误落备战分支反复空转 598s(SENTINEL-STALL)
——分支必须**先于备战双锚**。

统一观察架构逐屏迁移(五相位屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 首行装配点分流(本屏无重入裁决旗标):两端口
完整在场 → 五段生命周期新路径;缺省 None = 生产直连旧路径(原序列,生产
行为零变化)。五段形态:observe = 横幅判定(area 锚 miss → 「强敌」片段
判别兜底;不在 = 已推进 → 早退 success 交回外循环重判);decide+act 内聚
``_click_blank``(读「区域-空白点击」center → 点空白 → success 交回,两
路径共享零转录;横幅退场由下一轮 observe 判定);reconcile/on_outcome =
空申报(本屏无登记件)。**判别单一源红线(详设 §5)**:迁移只改宿主类,
禁改 ``BOSS_BRIEFING_TOKENS``/``is_boss_briefing_texts`` 判别面——四处消费
同源(0p 锚加固/0q 排他/``CwScreenBattleWait._hit_completion_anchor``
/loop 阶段一位面过渡身份分支排他)不变。
本屏 sim 腿 = 不适用(F11 例外清单:sim 无对应画面段),等价判据主承重 =
实机在册行为锁(锁面 = sr-od-test test_cw_obs_arch_phase_screens.py +
test_cw_anchor_exclusion.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext

# ===== 两画面判别单一源(P4R3 返工,第五局 1-9 实锤)=====
#
# boss 简报与位面过渡**共享「点击空白处继续」交互文案**(共享文案不作判据,
# od-dev-screen-onboarding「判别锚必须是画面专属特征」);而 0p 旧锚
# 「标识-强敌来袭」(OCR+LCS)被误读形态击穿——一局全帧 OCR 把「强敌来袭」
# 读成「强敌米」(来袭→米)→ 0p 不接管 → 0q 位面过渡误分发 → fail 循环。
# 判别单一源 = 「强敌」二字高区分片段,0p 锚加固 / 0q 排他 /
# CwScreenBattleWait 完成白名单 / loop 阶段一位面过渡身份分支排他
# 四处消费同源。

#: 「强敌」判别片段(误读鲁棒;勿改回全词「强敌来袭」——来袭二字可误读)。
#: 双形态:简体「强敌」 + 繁首「強敌」——同一横幅标题的 OCR 输出随渲染波动
#: (实证:一局读「强敌米」,另一局读「強敌来袭」繁首,analyze 实锤)。
BOSS_BRIEFING_TOKENS: tuple[str, ...] = ('强敌', '強敌')


def is_boss_briefing_texts(texts: list[str]) -> bool:
    """全帧 OCR 文本 → 是否 boss 简报画面(纯函数;判别单一源)。"""
    return any(tok in (t or '') for t in texts for tok in BOSS_BRIEFING_TOKENS)


def read_ocr_texts(ctx, screen) -> list[str]:
    """全帧 OCR 文本(共享判别用;同帧多次读由 ocr_service 按 image 缓存)。"""
    return [r.data for r in ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, color_range=None, crop_first=False)]


@dataclass
class BossBriefingObservation:
    """BOSS 简报观察 payload(五段之段1产物;实机转录形态)。

    轻观察(详设 §5 最简):横幅判定在段内(不在 = 已推进 → 早退 success
    交回外循环重判);payload 仅携带稳定帧引用(实机识别域载体,不出端口
    ——sim 适配器落位时该域 = None 帧语义,F11 例外清单本批不建)。
    """

    screen: Any = None


class BossBriefingLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口)。

    轻观察封口(先例 = 盛会之星轻观察适配器):横幅判定须在段内产出早退
    轮次,归 ``lifecycle_observe``;适配器仅装配稳定帧引用。sim 实现 = 不
    适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenBossBriefing') -> BossBriefingObservation:
        return BossBriefingObservation(screen=op.last_screenshot)


class CwScreenBossBriefing(CwScreenOpBase):
    """BOSS 简报:识别「强敌来袭」→ 点空白 → 交回外循环重判。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-BOSS简报'
    MARK_AREA: ClassVar[str] = '标识-强敌来袭'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白处继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-BOSS简报')
        # 适配器位缺省装配(先例 = CwScreenPrep/CwScreenEncounter):观察口 =
        # 实机适配器(轻观察封口);动作口 = None = 直连现役动作体(基类
        # 「None = 子类缺省实现自担」)。on_outcome 注册表:本屏无登记件。
        self._observation_adapter = BossBriefingLiveObservationAdapter()

    @operation_node(name='boss简报', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场 → 五段生命周期新路径;
        # 缺省 None = 生产直连旧路径(下方原序列,生产行为零变化)。本屏无
        # 重入裁决旗标 → 分流在首行。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        screen = self.last_screenshot
        banner_hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.MARK_AREA,
            crop_first=False).is_success
        if not banner_hit:
            # P4R3 锚加固:area 锚(LCS)会被 OCR 误读击穿(「强敌来袭」→
            # 「强敌米」/「強敌来袭」实测帧)→ 片段判别兜底(判别单一源)。
            banner_hit = is_boss_briefing_texts(read_ocr_texts(self.ctx, screen))
        if not banner_hit:
            # 横幅已退 = 点空白已生效推进 → 直接交回外循环重判(新架构:
            # loop 全分支识别点掉后的任何画面——boss 战/备战/流转)。
            log.info('[cw-flow-boss] 横幅已退(点空白已生效)→ 交回外循环重判')
            return self.round_success('BOSS 简报推进完成,交回外循环重判')
        return self._click_blank()

    def _click_blank(self) -> OperationRoundResult:
        """点空白推进内聚体(五段 decide+act 两路径共享零转录;旧 handle
        :75-83 逐位平移):读「区域-空白点击」center(缺失 → fail 留证缺
        建档)→ 点空白(bug#1 mouse_move 缓解)→ success 交回(本屏无重
        入裁决,横幅退场由下一轮 observe 判定)。"""
        blank = area_center(self.ctx, self.BLANK_AREA, self.SCREEN_NAME)
        if blank is None:
            return self.round_fail('BOSS 简报缺「区域-空白点击」建档')
        log.info('[cw-flow-boss] 强敌来袭横幅命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 横幅退场动画
        return self.round_success('点空白已发,交回外循环重判')

    # ---- 五段生命周期(统一观察架构 §5.1,先例 = CwScreenEncounter)----

    def lifecycle_observe(self
                          ) -> tuple[BossBriefingObservation,
                                     OperationRoundResult | None]:
        """段1 observe:横幅判定(旧 handle 首闸逐位转录)——area 锚
        「标识-强敌来袭」miss → 「强敌」片段判别兜底(``is_boss_briefing_
        texts``,判别单一源,**禁顺手复制判别逻辑**);不在 = 已推进 → 早退
        success 交回外循环重判;在 → 稳定帧 payload 进决策循环。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else BossBriefingObservation(screen=self.last_screenshot))
        screen = self.last_screenshot
        banner_hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.MARK_AREA,
            crop_first=False).is_success
        if not banner_hit:
            # P4R3 锚加固:area 锚(LCS)会被 OCR 误读击穿(「强敌来袭」→
            # 「强敌米」/「強敌来袭」实测帧)→ 片段判别兜底(判别单一源)。
            banner_hit = is_boss_briefing_texts(read_ocr_texts(self.ctx, screen))
        if not banner_hit:
            # 横幅已退 = 点空白已生效推进 → 直接交回外循环重判(新架构:
            # loop 全分支识别点掉后的任何画面——boss 战/备战/流转)。
            log.info('[cw-flow-boss] 横幅已退(点空白已生效)→ 交回外循环重判')
            return obs, self.round_success('BOSS 简报推进完成,交回外循环重判')
        return obs, None

    def lifecycle_decision_cycle(self, payload: BossBriefingObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_click_blank``(读区
        → 点空白 → success 交回,两路径共享零转录);on_outcome = 本屏无登
        记件(注册表缺席 = 零动作,__init__ 申报)。轮次终结出口 = 点空白
        success(横幅退场由下一轮 observe 判定)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._click_blank()
        self._lifecycle_mark('on_outcome')
        return rs
