"""货币战争 BOSS 简报 op(W971 P3b 返工:06-overlays §3 设计落地)。

boss 节点前弹「强敌来袭」简报横幅(火线动力机甲·萨姆等):识别
「标识-强敌来袭」(#26 建档)→ 点空白推进 → 结束判定 = 轮询备战商店开
画面(「按钮-收起」独有锚,节点后 overlay 完成承诺场景①口径,06 §5;
上界兜底超时留证 fail 交循环)。

接线教训(P3b 实机第三局走查实锤):主循环判定序无此分支时,boss 简报帧
(横幅遮挡观察,SIFT 双空读)误落备战分支反复空转 598s(SENTINEL-STALL)
——分支必须**先于备战双锚**。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SHOP_SCREEN_NAME,
    area_center,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 完成承诺轮询上界(节点后 overlay:boss 简报点击空白 → 回备战 + 商店自动开;
#: 用户口述单帧推进 ~1s,上界放宽覆盖动画/加载抖动;超时 = 异常留证交循环)。
BOSS_BRIEFING_SETTLE_TIMEOUT_S: float = 12.0
BOSS_BRIEFING_POLL_INTERVAL_S: float = 1.0


def _monotonic() -> float:
    """可测时钟(模块级单点:测试换假时钟验超时,生产等价 time.monotonic)。"""
    return time.monotonic()


# ===== 两画面判别单一源(P4R3 返工,第五局 1-9 实锤)=====
#
# boss 简报与位面过渡**共享「点击空白处继续」交互文案**(共享文案不作判据,
# od-dev-screen-onboarding「判别锚必须是画面专属特征」);而 0p 旧锚
# 「标识-强敌来袭」(OCR+LCS)被误读形态击穿——09:04:39 帧全帧 OCR 把
# 「强敌来袭」读成「强敌米」(来袭→米)→ 0p 不接管 → 0q 位面过渡误分发
# → fail 每 2s 无限循环。判别单一源 = 「强敌」二字高区分片段(前缀,
# 「强敌米」/「强敌来袭」/「强敌」三形态全命中;纯函数可单测),0p 锚
# 加固 / 0q 排他 / CwScreenBattleWait 完成白名单三处消费同源。

#: 「强敌」判别片段(误读鲁棒;勿改回全词「强敌来袭」——来袭二字可误读)。
#: 双形态:简体「强敌」 + 繁首「強敌」——同一横幅标题的 OCR 输出随渲染波动
#: (实证:一局读「强敌米」,另一局读「強敌来袭」繁首,analyze 实锤)。
BOSS_BRIEFING_TOKENS: tuple[str, ...] = ('强敌', '強敌')
def is_boss_briefing_texts(texts: list[str]) -> bool:
    """全帧 OCR 文本 → 是否 boss 简报画面(纯函数;判别单一源)。"""
    return any(tok in (t or "") for t in texts for tok in BOSS_BRIEFING_TOKENS)


def read_ocr_texts(ctx, screen) -> list[str]:
    """全帧 OCR 文本(共享判别用;同帧多次读由 ocr_service 按 image 缓存)。"""
    return [r.data for r in ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, color_range=None, crop_first=False)]


class CwScreenBossBriefing(SrOperation):
    """BOSS 简报:识别「强敌来袭」→ 点空白 → 等备战商店开(按钮-收起锚)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-BOSS简报'
    MARK_AREA: ClassVar[str] = '标识-强敌来袭'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白处继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'
    #: 完成承诺锚(节点后 overlay:等备战商店开画面出现,「按钮-收起」独有锚,
    #: 06-overlays §5 场景①判稳锚纪律)。
    DONE_SCREEN: ClassVar[str] = SHOP_SCREEN_NAME
    DONE_AREA: ClassVar[str] = '按钮-收起'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-BOSS简报')
        self._first_seen_ts: float | None = None   # 完成承诺轮询起点(超时兜底基)

    @operation_node(name='boss简报', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 完成承诺先行判定(round_wait 重入同节点):备战商店开锚命中 = 点击
        # 已生效推进完成 → 收口交回循环(不重复点空白,误点会跳过面板/误触)。
        if self.round_by_find_area(
                screen, self.DONE_SCREEN, self.DONE_AREA, crop_first=False).is_success:
            log.info('[cw-flow-boss] 备战商店开锚命中(按钮-收起)→ 交回外循环')
            return self.round_success('BOSS 简报推进完成(商店开)')
        banner_hit = self.round_by_find_area(
            screen, self.SCREEN_NAME, self.MARK_AREA, crop_first=False).is_success
        if not banner_hit:
            # P4R3 锚加固:area 锚(LCS)会被 OCR 误读击穿(「强敌来袭」→
            # 「强敌米」实测帧)→ 片段判别兜底(判别单一源,见模块头)。
            banner_hit = is_boss_briefing_texts(read_ocr_texts(self.ctx, screen))
        if not banner_hit:
            # 横幅已退、商店锚未现 = 转场进行中(round_wait 轮询,不耗重试预算;
            # 超时兜底:上界内锚必现,否则异常留证 fail 交循环)。
            now = _monotonic()
            if self._first_seen_ts is None:
                self._first_seen_ts = now
            if now - self._first_seen_ts >= BOSS_BRIEFING_SETTLE_TIMEOUT_S:
                self.save_screenshot(prefix='boss_briefing_settle_timeout')
                log.warning('[cw-flow-boss] 等备战商店开超上界(%.0fs 锚未现),留证交循环',
                            BOSS_BRIEFING_SETTLE_TIMEOUT_S)
                return self.round_fail('BOSS 简报后商店开锚未现(超上界,已留证)')
            return self.round_wait('横幅已退,轮询备战商店开锚', wait=BOSS_BRIEFING_POLL_INTERVAL_S)
        self._first_seen_ts = None   # 横幅仍在 = 未推进,重置完成承诺计时基
        blank = area_center(self.ctx, self.BLANK_AREA, self.SCREEN_NAME)
        if blank is None:
            return self.round_fail('BOSS 简报缺「区域-空白点击」建档')
        log.info('[cw-flow-boss] 强敌来袭横幅命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # bug#1 缓解(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 横幅退场动画
        return self.round_wait('点空白已发,轮询备战商店开锚', wait=BOSS_BRIEFING_POLL_INTERVAL_S)
