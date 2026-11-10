"""背包-遗器选中件 → 强化到满级 operation(遗器养成线)。

装备养成三件套之一(识别/强化/替换,与 EquipRelicOp/EquipLightConeOp 同族)。
交互链实机摸底(2026-11-10 全流程):
- 入口 = 背包-遗器**选中件**底部按钮:未满级显示「强化」、满级显示「重掷」
  (按钮位互斥,按文本区分——满级件无强化入口);
- 强化页 = 遗器详情框架的「强化」tab:右侧「+N」与「N/M」经验读数、消耗
  材料槽区(2×4)、「4星及以下」筛选与「自动置入」;
- **自动置入一次填满**(实机:一键置入经验材料堆,+0 件预览直通 +15、消耗
  信用点 11.4 万量级)——不存在逐级强化交互,本 op 语义即「强化到满级/
  材料耗尽」,不支持中间等级停点;
- 强化执行后弹「等级提升」结果横幅(等级0»等级15 + 词条前后对比),
  点空白处关闭回强化页;
- 满级态:右上角绿字「满级」、底部按钮位变灰字「已强化至当前等级上限」。

前置:背包-遗器界面且目标件已选中(选件导航后续迭代,当前由调用方保证);
起点不符显式失败。结果状态:MAX_LEVEL(强化至满级)/ ALREADY_MAX(起点已满)。

⚠️ 真实消耗:经验材料(自动置入按「4星及以下」筛选填入)+ 信用点(满强化
11 万+/件)。调用方发起前自行确认消耗可接受——低星废弃料喂狗粮是常规
养成路径,不涉及稀缺资源。
"""

import re

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_BAG_RELIC_SCREEN: str = '背包-遗器'
_ENHANCE_SCREEN: str = '遗器强化'
_RESULT_SCREEN: str = '遗器强化结果'

# 强化执行动画+结果横幅的稳定等待(等级提升横幅含词条对比动画)
_ENHANCE_SETTLE_SEC: float = 4.0
# 等级读数的「+N」解析(N 1-15)
_LEVEL_RE = re.compile(r'\+\s*(\d{1,2})')


class EquipRelicEnhanceOp(SrOperation):
    """把背包选中的遗器强化到满级(或材料耗尽),终点 = 背包-遗器。

    结果状态:MAX_LEVEL(强化至满级)/ ALREADY_MAX(起点已是满级件)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('遗器强化'),
                             node_max_retry_times=16)
        self._enhanced_to: int | None = None  #: 强化执行后的等级读数(报告用)
        self._stat_baseline: list[str] | None = None  #: 强化前词条行基线(变化对比用)

    def _read_level(self) -> int | None:
        """强化页右上角「+N」等级读数(读区-等级经验裁剪 OCR)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_ENHANCE_SCREEN, '读区-等级经验')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        for r in results:
            m = _LEVEL_RE.search(str(r.data or ''))
            if m:
                level = int(m.group(1))
                if 0 <= level <= 15:
                    return level
        return None

    def _read_stat_lines(self) -> list[str]:
        """强化页右侧词条区 OCR 原始行(词条识别基线素材;解析器候实机校准)。

        行形态实机样本:「攻击力 6.9%」(主词条,金色列首)、「速度 6②」/
        「暴击率 5.5%①」(副词条带强化次数圈标)、「生命值 (+3可激活) 38」
        (未激活第 4 词条灰字)。圈数字 OCR 识别率未实测,先原样保留文本行,
        结构化解析候实机样本后迭代——当前只用于强化前后行级对比(行集合
        差异 = 词条变化的可读证据)。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_ENHANCE_SCREEN, '读区-词条列表')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        # 按 y 排序聚行(OCR 输出无序),同 y(±10px)合并为一条词条行
        rows: list[tuple[int, str]] = []
        for r in sorted(results, key=lambda item: item.rect.y1):
            text = str(r.data or '').strip()
            if not text:
                continue
            cy = (r.rect.y1 + r.rect.y2) // 2
            if rows and abs(cy - rows[-1][0]) <= 10:
                rows[-1] = (rows[-1][0], rows[-1][1] + ' ' + text)
            else:
                rows.append((cy, text))
        return [text for _cy, text in rows]

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在背包-遗器且选中件可强化(底部按钮分流)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, _BAG_RELIC_SCREEN, '二级标题-遗器').is_success:
            return self.round_fail('不在背包-遗器界面(前置:打开背包并切遗器页签)')
        if self.round_by_find_area(screen, _BAG_RELIC_SCREEN, '按钮-强化').is_success:
            return self.round_success(status='CAN_ENHANCE')
        if self.round_by_find_area(screen, _BAG_RELIC_SCREEN, '按钮-重掷').is_success:
            return self.round_success(status='ALREADY_MAX')
        return self.round_fail('未选中遗器件(底部无强化/重掷按钮):先由调用方选中目标件')

    @node_from(from_name='入口核对', status='ALREADY_MAX')
    @operation_node(name='已满级收尾')
    def already_max(self) -> OperationRoundResult:
        """起点已是满级件:直接成功。"""
        return self.round_success(status='ALREADY_MAX')

    @node_from(from_name='入口核对', status='CAN_ENHANCE')
    @operation_node(name='打开强化页', node_max_retry_times=6)
    def open_enhance(self) -> OperationRoundResult:
        """背包底部点「强化」→ 强化页(until=双锚:标题+规则说明)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _BAG_RELIC_SCREEN, '按钮-强化',
            until_find_all=[
                (_ENHANCE_SCREEN, '标题-遗器详情'),
                (_ENHANCE_SCREEN, '标识-规则说明'),
            ],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开强化页')
    @operation_node(name='强化循环', node_max_retry_times=16)
    def enhance_loop(self) -> OperationRoundResult:
        """flat loop:结果弹层 → 满级判定 → 置入+强化执行。

        每轮分类(优先级):
        ① 「等级提升」结果横幅在 → 点空白关闭,重入循环;
        ② 底部灰字「已强化至当前等级上限」在 → 读最终等级,关页收尾;
        ③ 强化页裸露 → 点「自动置入」填料 → 点「强化」执行 → 等动画重入。
        自动置入一次填满的实机行为下循环通常 1-2 轮;轮次预算兜底异常。"""
        screen = self.last_screenshot

        # ① 结果横幅:点空白处关闭 → 回强化页
        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-等级提升').is_success:
            result = self.round_by_find_and_click_area(
                screen, _RESULT_SCREEN, '按钮-点击空白处关闭',
                until_find_all=[
                    (_ENHANCE_SCREEN, '标题-遗器详情'),
                    (_ENHANCE_SCREEN, '标识-规则说明'),
                ],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_retry('结果横幅已关,重入循环', wait=1)
            return result

        # ② 满级判定:底部按钮位变灰字提示 → 读等级+词条变化,关页收尾
        if self.round_by_find_area(screen, _ENHANCE_SCREEN, '读区-满级提示').is_success:
            self._enhanced_to = self._read_level()
            final_stats = self._read_stat_lines()
            changed = [line for line in final_stats
                       if self._stat_baseline is None or line not in self._stat_baseline]
            log.info('遗器强化: 已达满级(等级 %s),词条基线 %s 行 → 终态 %s 行,变化行 %s',
                     self._enhanced_to,
                     len(self._stat_baseline) if self._stat_baseline is not None else '?',
                     len(final_stats), changed)
            result = self.round_by_find_and_click_area(
                screen, _ENHANCE_SCREEN, '按钮-关闭',
                until_find_all=[(_BAG_RELIC_SCREEN, '二级标题-遗器')],
                pre_delay=0.5, success_wait=1.5, retry_wait=2,
            )
            if result.is_success:
                return self.round_success(status='MAX_LEVEL', wait=1.5)
            return result

        # ③ 强化页裸露:置入 → 执行
        if not self.round_by_find_area(screen, _ENHANCE_SCREEN, '标识-规则说明').is_success:
            return self.round_fail('不在强化页且无满级提示(画面状态未知)')

        if self._stat_baseline is None:
            self._stat_baseline = self._read_stat_lines()
            log.info('遗器强化: 词条基线 %s 行', len(self._stat_baseline))

        result = self.round_by_find_and_click_area(
            screen, _ENHANCE_SCREEN, '按钮-自动置入',
            until_find_all=[(_ENHANCE_SCREEN, '按钮-强化')],
            pre_delay=0.3, success_wait=0.8, retry_wait=1.5,
        )
        if not result.is_success:
            return result
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _ENHANCE_SCREEN, '按钮-强化',
            until_find_all=[(_RESULT_SCREEN, '标题-等级提升')],
            pre_delay=0.3, success_wait=_ENHANCE_SETTLE_SEC, retry_wait=2.5,
        )
