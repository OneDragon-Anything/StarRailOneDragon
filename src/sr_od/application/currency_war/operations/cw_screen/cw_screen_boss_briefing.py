"""货币战争 BOSS 简报 op(W971 P3b 返工:06-overlays §3 设计落地)。

boss 节点前弹「强敌来袭」简报横幅:识别「标识-强敌来袭」/「强敌」片段
(#26 建档)→ 点空白推进 → **直接交回外循环重判**(新架构:点掉后去向
由 loop 全分支自然处理——boss 战自动开打/备战流转;旧「轮询备战商店开」
完成承诺实证错误:boss 简报点掉后直接开 boss 战,商店永不开,等锚必超时,
第七局/第八局接管实录)。

接线教训(P3b 实机第三局走查实锤):主循环判定序无此分支时,boss 简报帧
(横幅遮挡观察,SIFT 双空读)误落备战分支反复空转 598s(SENTINEL-STALL)
——分支必须**先于备战双锚**。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# ===== 两画面判别单一源(P4R3 返工,第五局 1-9 实锤)=====
#
# boss 简报与位面过渡**共享「点击空白处继续」交互文案**(共享文案不作判据,
# od-dev-screen-onboarding「判别锚必须是画面专属特征」);而 0p 旧锚
# 「标识-强敌来袭」(OCR+LCS)被误读形态击穿——一局全帧 OCR 把「强敌来袭」
# 读成「强敌米」(来袭→米)→ 0p 不接管 → 0q 位面过渡误分发 → fail 循环。
# 判别单一源 = 「强敌」二字高区分片段,0p 锚加固 / 0q 排他 /
# CwScreenBattleWait 完成白名单三处消费同源。

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


class CwScreenBossBriefing(SrOperation):
    """BOSS 简报:识别「强敌来袭」→ 点空白 → 交回外循环重判。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-BOSS简报'
    MARK_AREA: ClassVar[str] = '标识-强敌来袭'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白处继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-BOSS简报')

    @operation_node(name='boss简报', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
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
        blank = area_center(self.ctx, self.BLANK_AREA, self.SCREEN_NAME)
        if blank is None:
            return self.round_fail('BOSS 简报缺「区域-空白点击」建档')
        log.info('[cw-flow-boss] 强敌来袭横幅命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 横幅退场动画
        return self.round_success('点空白已发,交回外循环重判')
