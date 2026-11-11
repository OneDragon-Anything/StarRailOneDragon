"""替换屏筛选与排序设置 op（「筛选 → 逐件看词缀 → 人定 → 替换」流程的筛选端）。

职责：把替换列表设到「目标部位 + 可选套装筛选 + 可选静态属性排序」——
后续扫描（ScanRelicCandidatesOp）与约束直装（EquipRelicOp 词缀约束）在
该列表状态上进行。筛选与排序**不做清除收尾**：筛选态是扫描的流程前提
（保留即意图）；共享持久筛选态的跨 op 防线见 EquipRelicOp 入口预检与
game coach 流程档。

交互事实（2026-11-12 实机摸底，全部帧已归档 sr-od-test/screens/遗器-替换/，
事实编号 F1-F16 见迭代设计 design.md §2.1）：

- 筛选漏斗 = 筛选面板 toggle（F1）；套装「点击选择」→「筛选规则」弹窗
  （F3）；套装行勾选 = 点行文本中心（F4）；弹窗「确认」后面板保持打开、
  列表即时刷新（F5）；筛选生效 = 漏斗上方橙色「筛选中」角标（F7）；当前
  穿着件不受套装筛选影响恒置顶（F8）；替换屏与背包侧共享同一持久筛选
  状态（F9）。
- 排序弹窗属性行 = 12 属性多选 + 优先级序号制（F13），行 y 随滚动浮动、
  靠滚动区内 OCR 动态定位（F12）；属性行点选有选中历史保留（F11）——
  设新排序前先点「全部清除」清残留，否则产出混合优先级；确认后列表 =
  基础排序 + 属性排序静态重排（F14）；左下按钮条文本 = 排序摘要读区
  （F15），OCR 实读逗号为全角「，」，全等校验前归一标点。
- 与背包侧「筛选规则」弹窗为同一游戏组件、像素级同构——弹窗内操作一律
  用屏名取 area + 区域级锚，不依赖全局画面判定（明细见画面 doc
  遗器-替换-筛选规则.md §2）。

排序前置子链（开弹窗 → 关建议排序 → 选等级 → 不确认）与 ``equip_relic.py``
同源复制并在此注明出处——域内节点复制为既有惯例；与 equip_relic 版本的
差异：**不含确认节点**（属性行点选后统一确认），确认前多两步属性行操作。

边界：多属性排序不支持（单 ``sort_stat``，UI 优先级多选语义后置）；数值
型排序约束不做。
"""

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.application.cultivation.relic.relic_list_recognizer import (
    RelicReplaceRecognizer,
)
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_relic_sets import resolve_set_kind
from sr_od.mys.sr_relic_stats import resolve_criteria_word
from sr_od.operations.sr_operation import SrOperation

_RELIC_TAB_SCREEN: str = '角色-遗器'
_REPLACE_SCREEN: str = '遗器-替换'
_FILTER_SCREEN: str = '遗器-替换-筛选'
_FILTER_RULE_SCREEN: str = '遗器-替换-筛选规则'
_SORT_RULE_SCREEN: str = '遗器-排序规则'
_ENTRY_SCREENS: list[str] = [_RELIC_TAB_SCREEN, _REPLACE_SCREEN, _FILTER_SCREEN]

#: 排序弹窗属性行文本 = 排序弹窗 UI 用「百分比」后缀、标准名体系用「提高」
#: 后缀（F12 行文本枚举与 sr_relic_stats 标准名全集的映射）；不在表内的
#: 标准名（充能/治疗/属性伤害提高）不在弹窗 12 行内，构造时显式拒绝
_ATTR_ROW_TEXT_BY_STANDARD: dict[str, str] = {
    '生命值提高': '生命值百分比',
    '生命值': '生命值',
    '攻击力提高': '攻击力百分比',
    '攻击力': '攻击力',
    '防御力提高': '防御力百分比',
    '防御力': '防御力',
    '速度': '速度',
    '暴击率': '暴击率',
    '暴击伤害': '暴击伤害',
    '效果命中': '效果命中',
    '效果抵抗': '效果抵抗',
    '击破特攻': '击破特攻',
}

#: 属性行滚动定位的最大拖拽次数（属性排序分区在弹窗滚动区下部，F12；
#: 超限仍找不到目标行按 fail 处理）
_ATTR_SCROLL_MAX: int = 3

#: 弹窗滚动区下拉拖距（px，向下翻页 = 终点 y 大于起点 y；拖距按相邻滚动态
#: 有重叠量标定，防止跳行漏扫）
_ATTR_SCROLL_DRAG: int = 250

#: 套装列表翻页的最大拖拽次数（目标套装不在弹窗首屏时翻找；超限 fail）
_SET_SCROLL_MAX: int = 4

#: 套装列表下拉拖距（px；列表行高 ≈62px，拖距留两行重叠防跳行漏扫）
_SET_SCROLL_DRAG: int = 250


def _normalize_summary_text(text: str) -> str:
    """排序摘要 OCR 文本归一（全等校验前）：全角逗号/竖线转半角、去空白。

    全角形态是 OCR 实读（排序方向反转帧实测「稀有度|暴击率，速度」）。"""
    return (text.replace('，', ',').replace('｜', '|').replace(' ', '').strip())


#: 排序摘要校验的期望形态生成:基础排序固定「等级」;属性名用 UI 短名——
#: 摘要实读样本「稀有度|暴击率,速度」(排序方向反转帧)中属性名无「百分比」
#: 后缀,与排序弹窗行文本(「攻击力百分比」)不同体系;百分比三属性的摘要
#: 短名按行文本去「百分比」后缀生成,实机验收时对帧复核
def _expected_summary(attr_row_text: str) -> str:
    attr_short = attr_row_text.removesuffix('百分比')
    return _normalize_summary_text(f'等级|{attr_short}')


class FilterRelicReplaceOp(SrOperation):
    """把替换列表设到「目标部位 + 可选套装筛选 + 可选静态属性排序」。

    结果状态:FILTER_SET(set_name 链完成)/SORT_SET(排序链完成)/NOOP(两参
    均空,仅保证部位正确的幂等空跑)。
    失败:套装名未入常量 / 排序词条不支持 / 弹窗内找不到目标行 / 摘要
    校验不符(含残留属性混合)。
    """

    def __init__(self, ctx: SrContext, pos: int,
                 set_name: str | None = None, sort_stat: str | None = None):
        """
        :param pos: 部位号 1-6(1=头部 2=手部 3=躯干 4=脚部 5=位面球
            6=连结绳,与 SrRelicPieceDef.pos 同坐标系)。
        :param set_name: 目标套装全名(官方名;None = 不设套装筛选)。设置
            范围含弹窗内「全部清除」——重复运行同参数不反选(幂等)。
        :param sort_stat: 静态排序的单个属性(标准名或别名,经解析层归一;
            None = 不改排序)。基础排序固定选「等级」,期望摘要 =
            「等级|<属性名>」。排序设置会在重进替换列表时被游戏重置回建议
            排序,复用列表(不重进)则保持——本 op 不主动重进。
        """
        if pos not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f'部位 pos={pos} 超出 1-6')
        if set_name is not None and resolve_set_kind(set_name) is None:
            raise ValueError(f'套装名「{set_name}」未入常量表(sr_relic_sets),'
                             f'无法确定筛选弹窗 TAB 类别')
        self.pos: int = pos
        self.set_name: str | None = set_name
        self.sort_stat: str | None = sort_stat
        #: sort_stat → 排序弹窗属性行文本(UI「百分比」后缀);构造期校验,
        #: 不支持的词条在此显式失败而非弹窗里静默找不到
        self._attr_row_text: str | None = None
        if sort_stat is not None:
            resolved = resolve_criteria_word(sort_stat)
            if resolved is None or len(resolved) != 1:
                raise ValueError(f'排序词条「{sort_stat}」需归一为单个标准名'
                                 f'(解析结果: {resolved})')
            row_text = _ATTR_ROW_TEXT_BY_STANDARD.get(resolved[0])
            if row_text is None:
                raise ValueError(f'标准名「{resolved[0]}」不在排序弹窗 12 属性行内'
                                 f'(充能/治疗/属性伤害类不支持)')
            self._attr_row_text = row_text
        #: 属性行点击坐标(scroll_to_attr_row 定位后供 clear_attr_and_click 用;
        #: 执行期快照,弹窗滚动态不变即恒稳)
        self._attr_row_point: Point | None = None
        self._attr_drags_left: int = _ATTR_SCROLL_MAX
        #: 套装列表翻页剩余预算(pick_target_set 消耗)
        self._set_drags_left: int = _SET_SCROLL_MAX
        SrOperation.__init__(self, ctx,
                             op_name=gt('设置替换列表筛选') + f'({RELIC_POS_CN[pos]})',
                             node_max_retry_times=12)

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """画面级判定:已在正确部位替换列表复用;筛选面板开态先关回详情
        面板(上次运行残留,toggle 语义 F1);不符先点返回回着装页。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _FILTER_SCREEN:
            funnel = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-筛选漏斗')
            self.ctx.controller.click(funnel.rect.center)
            return self.round_retry('筛选面板开着(上次残留),点漏斗关回详情面板',
                                    wait=1.5)
        if current == _REPLACE_SCREEN:
            current_pos = RelicReplaceRecognizer()._detect_pos_from_tabs(
                self.ctx, self.last_screenshot)
            if current_pos == self.pos:
                return self.round_success(status='IN_REPLACE')
            back_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-返回')
            self.ctx.controller.click(back_area.rect.center)
            return self.round_retry(
                f'已在替换列表但部位不符(筛选={current_pos},目标={self.pos}),'
                f'点返回回着装页', wait=1.5)
        if current != _RELIC_TAB_SCREEN:
            return self.round_fail(f'不在遗器着装页(当前画面判定: {current};'
                                   f'前置:进详情 + 选角色 + 切「遗器」页签)')
        return self.round_success(status='ON_TAB')

    @node_from(from_name='入口核对')
    @node_from(from_name='入口核对', status='ON_TAB')
    @node_from(from_name='入口核对', status='IN_REPLACE')
    @operation_node(name='打开列表', node_max_retry_times=12)
    def open_list(self) -> OperationRoundResult:
        """着装页点目标遗器位进替换列表(纯坐标直点,转移下轮画面判定确认);
        已在正确部位列表幂等通过。不滚顶:筛选与排序设置不依赖列表滚动位。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _RELIC_TAB_SCREEN:
            slot = self.ctx.screen_loader.get_area(
                _RELIC_TAB_SCREEN, f'遗器位-{RELIC_POS_CN[self.pos]}')
            self.ctx.controller.click(slot.rect.center)
            return self.round_retry('已点击遗器位,等待进入替换界面', wait=1.5)
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'异常画面,无法打开替换列表(当前判定: {current})')
        if self.set_name is None and self.sort_stat is None:
            return self.round_success(status='NOOP')
        if self.set_name is not None:
            return self.round_success(status='TO_FILTER')
        return self.round_success(status='TO_SORT')

    # ------------------------------------------------------------------ #
    # set_name 链:漏斗开面板 → 套装弹窗(切 TAB/全部清除/点行) → 确认 → 关面板
    # ------------------------------------------------------------------ #

    @node_from(from_name='打开列表', status='TO_FILTER')
    @operation_node(name='打开筛选面板', node_max_retry_times=6)
    def open_filter_panel(self) -> OperationRoundResult:
        """点漏斗开筛选面板(纯坐标区,toggle F1);验证 = 面板 id_mark 文本
        出现。未出现重入再点(点击被吞由节点重试兜住)。"""
        if self.round_by_find_area(self.last_screenshot, _FILTER_SCREEN,
                                   '文本-快速操作').is_success:
            return self.round_success(status='FILTER_PANEL_OPENED')
        funnel = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-筛选漏斗')
        self.ctx.controller.click(funnel.rect.center)
        if self.round_by_find_area(self.screenshot(), _FILTER_SCREEN,
                                   '文本-快速操作').is_success:
            return self.round_success(status='FILTER_PANEL_OPENED', wait=0.5)
        return self.round_retry('点漏斗后筛选面板未确认,重试', wait=1.5)

    @node_from(from_name='打开筛选面板')
    @operation_node(name='打开套装弹窗', node_max_retry_times=6)
    def open_set_dialog(self) -> OperationRoundResult:
        """点套装「点击选择」条(F3;chip 态下该条位置恒定,chip 只加在其
        下方);验证 = 弹窗标题出现(区域级锚,不依赖全局画面判定)。"""
        if self.round_by_find_area(self.last_screenshot, _FILTER_RULE_SCREEN,
                                   '标题-筛选规则').is_success:
            return self.round_success(status='DIALOG_OPENED')
        select_area = self.ctx.screen_loader.get_area(_FILTER_SCREEN, '按钮-套装选择')
        self.ctx.controller.click(select_area.rect.center)
        if self.round_by_find_area(self.screenshot(), _FILTER_RULE_SCREEN,
                                   '标题-筛选规则').is_success:
            return self.round_success(status='DIALOG_OPENED', wait=0.5)
        return self.round_retry('点套装选择后弹窗未确认,重试', wait=1.5)

    @node_from(from_name='打开套装弹窗')
    @operation_node(name='切套装类别TAB', node_max_retry_times=6)
    def switch_set_tab(self) -> OperationRoundResult:
        """按套装类别切弹窗 TAB(cavern=隧洞/ornament=位面饰品);TAB 点击
        幂等(已在目标 TAB 时点击无害),文本命中即成功。"""
        kind = resolve_set_kind(self.set_name)
        tab_name = 'TAB-隧洞遗器' if kind == 'cavern' else 'TAB-位面饰品'
        return self.round_by_find_and_click_area(
            self.last_screenshot, _FILTER_RULE_SCREEN, tab_name,
            pre_delay=0.5, success_wait=0.8, retry_wait=1.5,
        )

    @node_from(from_name='切套装类别TAB')
    @operation_node(name='清残留并勾选套装', node_max_retry_times=8)
    def clear_and_pick_set(self) -> OperationRoundResult:
        """先点「全部清除」清残留勾选(幂等依据:行已勾选时盲点即反选,F4;
        无勾选态点它无副作用),再 OCR 找目标套装行点行文本中心。行不在
        首屏时在套装列表区拖拽翻找(限次)。"""
        clear_result = self.round_by_find_and_click_area(
            self.last_screenshot, _FILTER_RULE_SCREEN, '按钮-全部清除',
            pre_delay=0.3, success_wait=0.5, retry_wait=1,
        )
        if not clear_result.is_success:
            return clear_result
        # 点清除后列表可能滚回顶部,重置翻页预算
        self._set_drags_left = _SET_SCROLL_MAX
        return self.round_success(status='CLEARED', wait=0.5)

    @node_from(from_name='清残留并勾选套装', status='CLEARED')
    @operation_node(name='点选目标套装', node_max_retry_times=8)
    def pick_target_set(self) -> OperationRoundResult:
        """套装列表区内 OCR 找目标套装行点行文本中心(F4);找不到拖拽翻页
        重找(限次,超限 fail——套装名经构造期校验,找不到 = 列表渲染异常)。"""
        list_area = self.ctx.screen_loader.get_area(_FILTER_RULE_SCREEN, '区域-套装列表')
        result = self.round_by_ocr_and_click(
            self.last_screenshot, self.set_name,
            area=list_area,
            lcs_percent=0.8, success_wait=0.8, retry_wait=0.5,
        )
        if result.is_success:
            return self.round_success(status='SET_PICKED')
        if self._set_drags_left > 0:
            center = list_area.rect.center
            # 下滑翻页(终点 y 大于起点 y),拖距留两行重叠防跳行漏扫
            self.ctx.controller.drag_to(Point(center.x, center.y + _SET_SCROLL_DRAG),
                                         Point(center.x, center.y - _SET_SCROLL_DRAG))
            self._set_drags_left -= 1
            return self.round_retry(f'未找到套装行,下滑翻页(剩 {self._set_drags_left} 次)', wait=1)
        return self.round_fail(f'筛选弹窗内未找到套装「{self.set_name}」'
                               f'(翻页 {_SET_SCROLL_MAX} 次后)')

    @node_from(from_name='点选目标套装', status='SET_PICKED')
    @operation_node(name='确认筛选', node_max_retry_times=6)
    def confirm_filter(self) -> OperationRoundResult:
        """点弹窗「确认」(F5:弹窗收起、面板保持打开、列表即时刷新);
        验证 = 弹窗标题消失 + 「筛选中」角标出现(F7)。"""
        if (not self.round_by_find_area(self.last_screenshot, _FILTER_RULE_SCREEN,
                                        '标题-筛选规则').is_success
                and self.round_by_find_area(self.last_screenshot, _REPLACE_SCREEN,
                                            '标识-筛选中').is_success):
            return self.round_success(status='FILTER_APPLIED')
        confirm_area = self.ctx.screen_loader.get_area(_FILTER_RULE_SCREEN, '按钮-确认')
        self.ctx.controller.click(confirm_area.rect.center)
        screen = self.screenshot()
        if (not self.round_by_find_area(screen, _FILTER_RULE_SCREEN,
                                        '标题-筛选规则').is_success
                and self.round_by_find_area(screen, _REPLACE_SCREEN,
                                            '标识-筛选中').is_success):
            return self.round_success(status='FILTER_APPLIED', wait=0.5)
        return self.round_retry('点确认后弹窗收起或筛选角标未确认,重试', wait=1.5)

    @node_from(from_name='确认筛选')
    @operation_node(name='关闭筛选面板')
    def close_filter_panel(self) -> OperationRoundResult:
        """点漏斗关筛选面板(toggle F1),收尾停回替换屏详情态;验证 = 面板
        id_mark 文本消失。后续排序链在详情态的替换屏上进行。"""
        if not self.round_by_find_area(self.last_screenshot, _FILTER_SCREEN,
                                       '文本-快速操作').is_success:
            next_status = 'TO_SORT' if self.sort_stat is not None else 'FILTER_SET'
            return self.round_success(status=next_status)
        funnel = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-筛选漏斗')
        self.ctx.controller.click(funnel.rect.center)
        if not self.round_by_find_area(self.screenshot(), _FILTER_SCREEN,
                                       '文本-快速操作').is_success:
            next_status = 'TO_SORT' if self.sort_stat is not None else 'FILTER_SET'
            return self.round_success(status=next_status, wait=0.5)
        return self.round_retry('点漏斗后筛选面板未关闭,重试', wait=1.5)

    # ---------------------------------------------------------------- #
    # sort_stat 链:排序前置子链(与 equip_relic 同源复制,注明出处;不含
    # 确认节点) → 属性行清残留点选 → 确认 → 摘要全等校验
    # ---------------------------------------------------------------- #

    @node_from(from_name='关闭筛选面板', status='TO_SORT')
    @node_from(from_name='打开列表', status='TO_SORT')
    @operation_node(name='打开排序弹窗', node_max_retry_times=6)
    def open_sort_dialog(self) -> OperationRoundResult:
        """点替换屏「按钮-排序设置」纯坐标区打开排序弹窗;验证 = 弹窗标题
        出现。同源 equip_relic.open_sort_dialog(按钮条文本随排序形态变化,
        文本 find 不恒命中 → 纯坐标直点)。"""
        if self.round_by_find_area(self.last_screenshot, _SORT_RULE_SCREEN,
                                   '标题-排序规则').is_success:
            return self.round_success(status='SORT_DIALOG_OPENED')
        area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-排序设置')
        self.ctx.controller.click(area.rect.center)
        if self.round_by_find_area(self.screenshot(), _SORT_RULE_SCREEN,
                                   '标题-排序规则').is_success:
            return self.round_success(status='SORT_DIALOG_OPENED', wait=0.5)
        return self.round_retry('点排序设置后排序弹窗未确认,重试', wait=2)

    @node_from(from_name='打开排序弹窗')
    @operation_node(name='关建议排序', node_max_retry_times=6)
    def disable_suggested_sort(self) -> OperationRoundResult:
        """关「建议排序」开关(模板命中 = ON;已关跳过防呆)。同源复制
        equip_relic.disable_suggested_sort——until 重入验证机制见其
        docstring(开关点击被吞时静默带病下行在此防线)。"""
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, _SORT_RULE_SCREEN,
                                       '开关-建议排序').is_success:
            return self.round_success(status='SORT_OFF')
        return self.round_by_find_and_click_area(
            screen, _SORT_RULE_SCREEN, '开关-建议排序',
            until_not_find_all=[(_SORT_RULE_SCREEN, '开关-建议排序')],
            pre_delay=0.5, success_wait=1, retry_wait=2,
        )

    @node_from(from_name='关建议排序')
    @node_from(from_name='关建议排序', status='SORT_OFF')
    @operation_node(name='选等级排序', node_max_retry_times=6)
    def select_level_sort(self) -> OperationRoundResult:
        """基础排序固定选「等级」(已选中跳过防呆)。同源复制
        equip_relic.select_level_sort;radio 点击被吞的防线同源。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SORT_RULE_SCREEN,
                                   '单选-等级选中').is_success:
            return self.round_success(status='LEVEL_SELECTED')
        return self.round_by_find_and_click_area(
            screen, _SORT_RULE_SCREEN, '单选-等级',
            until_find_all=[(_SORT_RULE_SCREEN, '单选-等级选中')],
            pre_delay=0.5, success_wait=1, retry_wait=2,
        )

    @node_from(from_name='选等级排序')
    @node_from(from_name='选等级排序', status='LEVEL_SELECTED')
    @operation_node(name='滚动定位属性行', node_max_retry_times=6)
    def scroll_to_attr_row(self) -> OperationRoundResult:
        """弹窗滚动区内 OCR 动态定位目标属性行(F12:行 y 随滚动浮动,静态
        area 不可行);不确认——属性行点选后统一确认。行不在当前视口时下拉
        拖拽翻找(限次)。定位结果存实例坐标供下一点节点点击。"""
        row_text = self._attr_row_text
        scroll_area = self.ctx.screen_loader.get_area(_SORT_RULE_SCREEN, '区域-弹窗滚动区')
        ocr_list = self.ctx.ocr_service.get_ocr_result_list(
            image=self.last_screenshot, rect=scroll_area.rect,
        )
        for ocr_result in ocr_list:
            # 行文本全等优先(高对比 UI 文本 conf 恒 1.0);LCS 0.9 兜 OCR 近似
            # (0.7 会「攻击力」误配「攻击力百分比」行——同前缀行全等不可省)
            if (ocr_result.data.strip() == row_text
                    or str_utils.find_by_lcs(row_text, ocr_result.data, percent=0.9)):
                self._attr_row_point = ocr_result.center
                return self.round_success(status='ATTR_ROW_FOUND')
        if self._attr_drags_left > 0:
            scroll_area = self.ctx.screen_loader.get_area(_SORT_RULE_SCREEN, '区域-弹窗滚动区')
            center = scroll_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + _ATTR_SCROLL_DRAG),
                                         Point(center.x, center.y - _ATTR_SCROLL_DRAG))
            self._attr_drags_left -= 1
            return self.round_retry(f'未找到属性行「{row_text}」,下拉翻找'
                                    f'(剩 {self._attr_drags_left} 次)', wait=1)
        return self.round_fail(f'排序弹窗滚动区内未找到属性行「{row_text}」'
                               f'(下拉 {_ATTR_SCROLL_MAX} 次后)')

    @node_from(from_name='滚动定位属性行', status='ATTR_ROW_FOUND')
    @operation_node(name='清残留并点属性行', node_max_retry_times=6)
    def clear_and_click_attr_row(self) -> OperationRoundResult:
        """先点「全部清除」清属性排序残留(F13 多选优先级制 + F11 选中历史
        保留:不清则产出「残留属性+目标属性」混合优先级——确认后的摘要
        全等校验拦混合优先级,此处源头防),再点目标属性行(执行期快照坐标;
        清除只改选中态不改滚动位置,行坐标仍有效)。"""
        clear_result = self.round_by_find_and_click_area(
            self.last_screenshot, _SORT_RULE_SCREEN, '按钮-全部清除',
            pre_delay=0.3, success_wait=0.5, retry_wait=1,
        )
        if not clear_result.is_success:
            return clear_result
        self.ctx.controller.click(self._attr_row_point)
        return self.round_success(status='ATTR_CLICKED', wait=0.5)

    @node_from(from_name='清残留并点属性行', status='ATTR_CLICKED')
    @operation_node(name='确认排序', node_max_retry_times=6)
    def confirm_sort(self) -> OperationRoundResult:
        """点「确认」提交(F14:列表按基础+属性排序静态重排);验证 = 弹窗
        标题消失。同源 equip_relic 确认节点语义。"""
        if not self.round_by_find_area(self.last_screenshot, _SORT_RULE_SCREEN,
                                       '标题-排序规则').is_success:
            return self.round_success(status='SORT_CONFIRMED')
        confirm_area = self.ctx.screen_loader.get_area(_SORT_RULE_SCREEN, '按钮-确认')
        self.ctx.controller.click(confirm_area.rect.center)
        if not self.round_by_find_area(self.screenshot(), _SORT_RULE_SCREEN,
                                       '标题-排序规则').is_success:
            return self.round_success(status='SORT_CONFIRMED', wait=0.5)
        return self.round_retry('点确认后排序弹窗未关闭,重试', wait=1.5)

    @node_from(from_name='确认排序')
    @operation_node(name='校验排序摘要')
    def verify_sort_summary(self) -> OperationRoundResult:
        """排序摘要读区与期望「等级|<属性名>」全等(F15;含式校验拦不住
        残留属性混合,混合优先级在此全等拦下)。OCR 实读逗号为全角,归一后
        比对;基础排序固定「等级」由选等级节点保证。"""
        summary_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '读区-排序摘要')
        ocr_list = self.ctx.ocr_service.get_ocr_result_list(
            image=self.last_screenshot, rect=summary_area.rect)
        actual = _normalize_summary_text(
            ' '.join(r.data for r in ocr_list)) if ocr_list else ''
        expected = _expected_summary(self._attr_row_text)
        if actual == expected:
            return self.round_success(status='SORT_SET')
        return self.round_fail(f'排序摘要校验不符:期望「{expected}」,实读「{actual}」'
                               f'(列表可能带残留属性排序或设置未生效)')
