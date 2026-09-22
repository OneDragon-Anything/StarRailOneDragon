"""货币战争 BOSS 简报 op。

boss 节点前弹「强敌来袭」简报横幅:识别阵营徽记模板锚「标识-阵营徽记」/
「强敌」片段判别兜底(#26 建档;锚从标题 OCR 换徽记模板,标题 OCR 会被
误读击穿而徽记像素稳定)→ 点空白推进 → **直接交回外循环重判**(点掉后
去向由 loop 全分支自然处理——boss 战自动开打/备战流转;旧「轮询备战
商店开」完成承诺实证错误:boss 简报点掉后直接开 boss 战,商店永不开,
等锚必超时,第七局/第八局接管实录)。

接线教训(实机走查实锤):主循环判定序无此分支时,boss 简报帧(横幅遮挡
观察,SIFT 双空读)误落备战分支反复空转 598s(SENTINEL-STALL)——分支
必须**先于备战双锚**。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation,
轻屏统一形态):观察 node = 横幅门(徽记模板锚 miss → 「强敌」片段判别
兜底;不在 = 已推进 → 早退 success 交回外循环重判,obs 不装载)+ 门内
obs{on_screen} → ``report_screen_boss_briefing_obs``(boss 类型直定写端,
目标 = 现 hist——迭代 2026-09-20-node-advance-action-report 切换批自旧
BOSS 简报腿迁移,design §2.5 表;直定前置同源守卫见 kernel 屏文件,
match/gs 缺席跳过)→ obs 挂实例属性进
决策 node。决策动作 node = 点空白一次推进 → success 交回(本屏一次点击
即终结,横幅退场裁决 = 外循环重派后的下一次入口门,不做 op 内轮询)。
**判别单一源红线**:迁移只改宿主类,禁改 ``BOSS_BRIEFING_TOKENS``/
``is_boss_briefing_texts`` 判别面——三处消费同源(op 内锚兜底/
``CwScreenBattleWait._hit_completion_anchor`` 完成白名单/loop 阶段一位
面过渡身份臂排他)不变。本屏 sim 腿 = 不适用(sim 无对应画面段),等价
判据主承重 = 实机在册行为锁(锁面 = sr-od-test test_cw_obs_arch_phase_
screens.py + test_cw_anchor_exclusion.py)。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.boss_briefing import (
    CwScreenBossBriefingObs,
    report_screen_boss_briefing_obs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# ===== 两画面判别单一源 =====
#
# boss 简报与位面过渡**共享「点击空白处继续」交互文案**(共享文案不作判据,
# od-dev-screen-onboarding「判别锚必须是画面专属特征」);而旧锚
# 「标识-强敌来袭」(OCR+LCS)被误读形态击穿——一局全帧 OCR 把「强敌来袭」
# 读成「强敌米」(来袭→米)→ BOSS 简报旧锚不接管 → 位面过渡误分发 → fail 循环。
# 判别单一源 = 「强敌」二字高区分片段,op 内锚兜底 /
# CwScreenBattleWait 完成白名单 / loop 阶段一位面过渡身份分支排他
# 三处消费同源。

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
    # 横幅锚 = 阵营徽记模板(二值化模板匹配,OCR 误读免疫;从标题 OCR 锚
    # 「标识-强敌来袭」换装——标题锚被「强敌米」/「強敌来袭」实测帧击穿,
    # 徽记为固定资产,简报三家阵营卡与横幅旗标同资产实证)。
    MARK_AREA: ClassVar[str] = '标识-阵营徽记'
    PROMPT_AREA: ClassVar[str] = '提示-点击空白处继续'
    BLANK_AREA: ClassVar[str] = '区域-空白点击'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-BOSS简报')
        # 观察结果(观察 node 产物;门早退轮不装载)。
        self._obs: CwScreenBossBriefingObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """横幅门 + obs{on_screen} → report 接线(boss 类型直定)。

        门判定:徽记模板锚「标识-阵营徽记」miss → 「强敌」片段判别兜底
        (``is_boss_briefing_texts``,判别单一源,**禁顺手复制判别逻辑**;
        横幅动画相位致模板 miss 时,片段判别按全帧 OCR 文本补一刀)。不在
        = 已推进 → 早退 success 交回外循环重判(loop 全分支识别点掉后的
        任何画面——boss 战/备战/流转);在 → obs 装载 + report(boss 类型
        直定,目标 = 现 hist;match/gs 缺席跳过)。"""
        screen = self.last_screenshot
        banner_hit = self.round_by_find_area(
            screen, CwScreenBossBriefing.SCREEN_NAME, CwScreenBossBriefing.MARK_AREA,
            crop_first=False).is_success
        if not banner_hit:
            # 锚加固纵深:徽记模板锚已是 OCR 误读免疫(二值化模板匹配),
            # 片段判别兜底仍保留(判别单一源;横幅动画相位致模板 miss 时,
            # 片段判别按全帧 OCR 文本补一刀)。
            banner_hit = is_boss_briefing_texts(read_ocr_texts(self.ctx, screen))
        if not banner_hit:
            # 横幅已退 = 点空白已生效推进 → 直接交回外循环重判。
            log.info('[cw-flow-boss] 横幅已退(点空白已生效)→ 交回外循环重判')
            return self.round_success('BOSS 简报推进完成,交回外循环重判')
        obs = CwScreenBossBriefingObs(on_screen=True, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_boss_briefing_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """点空白推进体:读「区域-空白点击」center(缺失 → fail 留证缺建档)
        → 点空白 → success 交回(横幅退场由外循环重派后的下一次入口门判定)。"""
        blank = area_center(self.ctx, CwScreenBossBriefing.BLANK_AREA,
                            CwScreenBossBriefing.SCREEN_NAME)
        if blank is None:
            return self.round_fail('BOSS 简报缺「区域-空白点击」建档')
        log.info('[cw-flow-boss] 强敌来袭横幅命中 → 点空白 (%s,%s)', blank.x, blank.y)
        # 防吞点击(mouse_move 先,overlay 族同款)
        self.ctx.controller.mouse_move(blank)
        self.ctx.controller.click(blank)
        time.sleep(1.0)   # click 异步落地 + 横幅退场动画
        return self.round_success('点空白已发,交回外循环重判')
