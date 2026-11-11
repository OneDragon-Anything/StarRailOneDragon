"""遗器位 → 替换遗器 operation(为当前角色装备指定套装的指定部位遗器)。

角色养成系列的装备线 op(与 EquipLightConeOp 同构,定位算法共用
grid_template_locate)。交互链实机摸底:
- 角色遗器着装页**点目标遗器位直达该部位的替换界面**(部位筛选已锁定,
  无需先点「替换」再选部位);4 列卡片网格;
- 卡片上无遗器名(单件名只在选中后右侧详情可读);同套装同部位件名相同
  (单件名由套装+部位唯一确定)——定位走 RelicReplaceRecognizer.recognize_for_pos
  部位先验整屏识别(替换界面已按部位筛选,候选收缩到单部位),目标件名按
  常量表名称直配;候选未装备件优先,
  同套装多件同屏时票分裂到多列但件名相同,选任一件均满足意图;
- 选中未装备件后底部按钮「卸下」变「替换」;点「替换」即装备(实测即时
  生效,给已由他人装备的件会直接从对方身上换下)。
- 重进替换列表后、扫描前执行排序前置(打开排序弹窗 → 关「遗器建议排序」
  开关 → 选「等级」基础排序 → 确认):建议排序按匹配度动态重排,重掷动画
  期间评分持续变化 → 持续重排 + 滚动自动回顶,「识别 → 点击」间隔超 2 秒
  即落空;静态排序下列表稳定。快速路径(复用已在正确部位的列表)不重进
  ——排序设置只在重进时被重置,复用时排序已静态,不重复执行前置。

前置:角色遗器着装页(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('遗器') 保证);起点不符显式失败。
⚠️ 装备即时生效且可能从其他角色身上换下,调用方须确认目标正确。
"""


import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_relic_sets import PIECE_TO_SET
from sr_od.operations.equip_list_recognizer import RelicReplaceRecognizer
from sr_od.operations.sr_operation import SrOperation

_RELIC_TAB_SCREEN: str = '角色-遗器'
_REPLACE_SCREEN: str = '遗器-替换'
_SORT_RULE_SCREEN: str = '遗器-排序规则'

# 网格几何:4 列,首列中心相对列表区 x1 偏移 66px、列间距 123px
# (实机亮度剖面实测列中心 99/224/346/469;列表区 rect 见 screen_info
# 「区域-遗器列表」,等分推导不成立 —— 左边距与卡间距不均匀,故用偏移+
# 间距双常量声明,坐标系 = 列表区 rect 内像素)
_GRID_COL_OFFSET: int = 66
_GRID_COL_GAP: int = 123
# 每屏扫描的滚动拖拽:列表中心上移 300px(约 2 行卡位,避免跳行)
_SCROLL_DRAG_PX: int = 300
# 滚动扫描的屏幕数上限
_SCAN_MAX_SCREENS: int = 12
# 验证选中连续不符次数达此值 → 转回重新定位
_RESELECT_AFTER: int = 3
# 快速路径(复用已有正确部位列表)滚回顶部的拖拽次数
_RESET_TOP_DRAGS: int = 4

# 部位 pos → 着装页遗器位 area 名(skill 坐标系:1头 2手 3躯干 4脚 5球 6绳)
_POS_TO_SLOT_AREA: dict[int, str] = {
    1: '遗器位-头部',
    2: '遗器位-手部',
    3: '遗器位-躯干',
    4: '遗器位-脚部',
    5: '遗器位-位面球',
    6: '遗器位-连结绳',
}


def _relic_col_centers(list_rect) -> list[float]:
    """4 列中心:列表区 x1 + 首列偏移 + 间距 × i(实测坐标系,见常量注释)。"""
    x1 = list_rect.x1
    return [x1 + _GRID_COL_OFFSET + _GRID_COL_GAP * i for i in range(4)]


def _filter_candidates(matched: list[dict], allow_take_over: bool,
                       rob_cells: set[tuple[int, int]]) -> list[dict]:
    """候选过滤与排序(纯函数,allow_take_over 语义的单一实现点)。

    False(默认):仅无主件(owner=None),且弹框取消过的格(_rob_cells)不再试
    —— owner 漏报的已装备件由弹框分支兜底取消后记入,防同格反复弹框死循环
    (实机教训)。True(交换语义):被穿着件也作候选,但无主件稳定排前 —— 先试
    无主件,减少对他人配装的扰动;_rob_cells 防线只属取消路径,True 走确认
    不维护。
    """
    if allow_take_over:
        kept = [item for item in matched
                if (item['cell'][0], item['cell'][1]) not in rob_cells]
        kept.sort(key=lambda item: 0 if item['owner'] is None else 1)
        return kept
    return [item for item in matched
            if item['owner'] is None
            and (item['cell'][0], item['cell'][1]) not in rob_cells]


class EquipRelicOp(SrOperation):
    """为当前角色装备指定遗器(按单件名定位套装与部位),终点 = 遗器着装页。

    结果状态:ALREADY_EQUIPPED(已装备,幂等成功)/ RELIC_EQUIPPED(替换完成,
    着装页套装效果读区含目标套装名核对)。
    失败:PIECE_NOT_FOUND(件名不在常量表)/ 列表扫完未找到(未拥有或识别失败)。
    装备语义(用户裁定,与光锥同):遗器装备 = 交换——目标件在他人身上时,
    对方拿到当前角色脱下的件,不产生空手。默认 allow_take_over=False 不主动
    动他人装备(候选只取无主件+弹框一律取消),True 才允许交换。
    """

    def __init__(self, ctx: SrContext, piece_name: str, expected_character: str | None = None,
                 allow_take_over: bool = False):
        """
        :param ctx: 上下文
        :param piece_name: 遗器单件名(如「先驱的绝热围壳」;套装+部位唯一确定,
            同套装同部位的多件副本任意一件均满足)
        :param expected_character: 目标角色中文名(替换界面标题下「命途/角色名」
            核对,防在错误角色上换装;None = 跳过核对)。角色名经 OCR fuzzy 比对,
            OCR 误读(如「布洛妮娅」读缺字)不判失败,仅明显不同才判。
        :param allow_take_over: 是否允许占用他人装备中的件(用户裁定:遗器装备
            与光锥同为交换机制,对方拿到当前角色脱下的件,不产生空手)。False
            (默认)=候选只取无主件,误点被穿着件时弹框一律取消;True=被穿着件
            也作为候选(仍无主件优先),弹框点确认完成交换。True 前调用方必须
            向用户确认——交换会改变对方配装。
        """
        piece_def = PIECE_TO_SET.get(piece_name)
        if piece_def is None:
            raise ValueError(f'遗器单件名 {piece_name} 不在常量表(PIECE_TO_SET)')
        piece = next(p for p in piece_def.pieces if p.name == piece_name)
        self.piece_name: str = piece_name
        self.set_name: str = piece_def.set_name
        self.pos: int = piece.pos  # 部位坐标:1头 2手 3躯干 4脚 5位面球 6连结绳(常量表固化)
        self.expected_character: str | None = expected_character
        self.allow_take_over: bool = allow_take_over
        self._scan_screens: int = 0
        self._candidate_idx: int = 0  #: 当前屏候选游标(点击验证失败后推进到下一候选)
        self._select_retries: int = 0
        self._reset_drags_left: int = 0  #: 快速路径待滚顶次数(check_entry 设置,reset_top 消耗)
        self._rob_cells: set[tuple[int, int]] = set()  #: 抢件弹框格(cell 左上角)——
        #: 仅 allow_take_over=False 时维护:弹框=该格是 owner 漏报的已装备件,
        #: 取消后记录并不再点击(死循环防线)
        self._last_clicked_cell: tuple[int, int] | None = None  #: 最近点击格左上角
        SrOperation.__init__(self, ctx, op_name=gt('替换遗器') + f'({piece_name})',
                             node_max_retry_times=24)

    #------------------- 识别辅助 -------------------#

    def _read_piece_name(self, screen_name: str, area_name: str) -> str | None:
        """OCR 读名字读区,与目标件名 fuzzy 匹配(形近变体兜底),命中返回文本。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        texts = [str(r.data) for r in results]
        idx = str_utils.find_in_list_with_fuzzy(self.piece_name, texts, cutoff=0.6)
        return texts[idx] if idx is not None else None

    def _check_character_on_replace_screen(self) -> OperationRoundResult | None:
        """替换界面标题下「命途/角色名」核对目标角色(expected_character 提供
        时才核;防在错误角色上换装的安全校验)。OCR 读整行(如「虚无/黄泉」),
        角色名精确子串命中即过;个别字 OCR 误读按字符覆盖率 ≥0.5 兜底;
        核对通过返回 None,失败返回 round_fail。"""
        if self.expected_character is None:
            return None  #: 调用方未要求核对,整体跳过(连读区 OCR 也省)
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '读区-角色命途名')
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        text = ''.join(str(r.data) for r in results).replace(' ', '')
        if self.expected_character in text:
            return None
        hit = sum(1 for ch in self.expected_character if ch in text)
        if hit / len(self.expected_character) >= 0.5:
            return None
        return self.round_fail(f'替换界面角色核对失败:期望「{self.expected_character}」,'
                               f'实读「{text}」—— 当前角色不符,请先切到目标角色')

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对并进入部位', is_start_node=True, node_max_retry_times=8)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:点目标遗器位直达该部位替换界面。

        着装页遗器位与替换界面返回箭头均为**纯坐标区**(无文本/模板,find
        不命中)—— 一律坐标点击;转移验证:点遗器位后查替换界面标题,点返回
        后靠节点重入(重入时替换界面应已关)。重入已在替换界面时读部位筛选:
        与目标一致则直接复用本列表(先滚回顶部作干净扫描起点)——重进会把
        用户手动切换的排序设置重置回「建议排序」(实机复现:动态重排下卡面
        识别大面积漂移,故静态列表能复用就不重进);不一致才返回着装页重进。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _REPLACE_SCREEN, '标题-遗器替换').is_success:
            current_pos = RelicReplaceRecognizer()._detect_pos_from_tabs(
                self.ctx, self.last_screenshot)
            if current_pos == self.pos:
                check = self._check_character_on_replace_screen()
                if check is not None:
                    return check
                self._reset_drags_left = _RESET_TOP_DRAGS  #: 待滚顶次数(open_list 消耗)
                return self.round_success(status='IN_REPLACE_RESET_TOP')
            back_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-返回')
            self.ctx.controller.click(back_area.rect.center)
            return self.round_retry('已在替换界面,点返回回着装页', wait=1.5)

        if not self.round_by_find_area(screen, _RELIC_TAB_SCREEN, '标题-遗器着装').is_success:
            return self.round_fail('不在遗器着装页(前置:进详情 + 选角色 + 切「遗器」页签)')

        slot_area = _POS_TO_SLOT_AREA.get(self.pos)
        if slot_area is None:
            return self.round_fail(f'部位 pos={self.pos} 无对应遗器位 area')
        slot = self.ctx.screen_loader.get_area(_RELIC_TAB_SCREEN, slot_area)
        self.ctx.controller.click(slot.rect.center)
        # 先等过渡动画再验证标题 —— 点完立即查必查不到(动画中),而重入的
        # 返回分支会把这个刚开对的界面关掉形成死循环(实机复现)
        time.sleep(1.5)
        result = self.round_by_find_area(self.screenshot(), _REPLACE_SCREEN, '标题-遗器替换')
        if result.is_success:
            check = self._check_character_on_replace_screen()
            if check is not None:
                return check
            return self.round_success(status='ENTERED_REPLACE', wait=1)
        return self.round_retry('点遗器位后替换界面未确认,重试', wait=1.5)

    @node_from(from_name='入口核对并进入部位', status='ENTERED_REPLACE')
    @operation_node(name='打开排序弹窗', node_max_retry_times=6)
    def open_sort_dialog(self) -> OperationRoundResult:
        """点替换屏「遗器建议排序」按钮打开排序规则弹窗,until = 弹窗标题出现。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, _REPLACE_SCREEN, '按钮-遗器建议排序',
            until_find_all=[(_SORT_RULE_SCREEN, '标题-排序规则')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开排序弹窗')
    @operation_node(name='关建议排序', node_max_retry_times=6)
    def disable_suggested_sort(self) -> OperationRoundResult:
        """把「遗器建议排序」开关关掉(模板命中 = 开关橙色 ON)。

        开关开着时列表按建议匹配度动态重排(重掷动画期间评分持续变化 →
        持续重排 + 滚动自动回顶),「识别 → 点击」间隔超 2 秒即落空,是
        扫描失败的根因;本节点把它转静态。开关已关(模板不命中)时跳过
        ——防呆:不重复点击已关闭的开关。
        until 的真实验证机制:not_find_all 预检与入口防呆读同一帧(能走
        到点击说明模板仍命中,预检恒不成功),真正验证 = until 使点击成功
        返回 round_wait(operation.round_by_find_and_click_area,点击后无
        until 参数才直接 round_success)强制本节点重入,重入轮以新帧重跑
        入口防呆——模板已消失即走跳过分支确认翻转,点击被吞则再次点击。
        until 参数不可删:删除则失去重入验证,开关点击被游戏吞掉时会静默
        带病下行(动态重排扫描落空的原病无声回归)。"""
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
    @operation_node(name='选等级排序', node_max_retry_times=6)
    def select_level_sort(self) -> OperationRoundResult:
        """基础排序选「等级」(静态排序;等级未选中时灰 radio 模板命中)。

        等级已选中(橙色 radio 模板命中)时跳过——radio 点击幂等但防呆
        不重复点。
        until 的真实验证机制:find_all 预检与入口防呆读同一帧(能走到点击
        说明选中态模板未命中,预检恒不成功),真正验证 = until 使点击成功
        返回 round_wait(operation.round_by_find_and_click_area,点击后无
        until 参数才直接 round_success)强制本节点重入,重入轮以新帧重跑
        入口防呆——选中态模板命中即走跳过分支确认生效,点击被吞则再次
        点击。until 参数不可删:删除则失去重入验证,radio 点击被游戏吞掉
        时弹窗带着「等级未选」状态被下一节点确认关闭,等级排序意图静默
        落空且无下游拦截。"""
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
    @operation_node(name='确认排序规则', node_max_retry_times=6)
    def confirm_sort_rule(self) -> OperationRoundResult:
        """点「确认」提交排序设置,until = 弹窗标题消失(弹窗关闭 = 列表
        已按静态排序固定)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, _SORT_RULE_SCREEN, '按钮-确认',
            until_not_find_all=[(_SORT_RULE_SCREEN, '标题-排序规则')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='入口核对并进入部位', status='IN_REPLACE_RESET_TOP')
    @operation_node(name='滚回列表顶部', node_max_retry_times=8)
    def reset_top(self) -> OperationRoundResult:
        """快速路径(IN_REPLACE_RESET_TOP)专用:复用已有列表前滚回顶部。
        重进路径经排序前置节点链固定静态排序后直达当前装备核对
        (列表天然在顶部,无需滚顶)。"""
        if self._reset_drags_left > 0:
            list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-遗器列表')
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + 400),
                                        Point(center.x, center.y - 400))
            self._reset_drags_left -= 1
            return self.round_retry(f'滚回列表顶部(剩 {self._reset_drags_left} 次)', wait=1)
        return self.round_success(status='TOP_RESETTED')

    @node_from(from_name='滚回列表顶部')
    @node_from(from_name='确认排序规则')
    @operation_node(name='当前装备核对', node_max_retry_times=6)
    def check_current(self) -> OperationRoundResult:
        """替换界面右侧详情默认显示当前装备件:已是目标 = 幂等成功。"""
        if self._read_piece_name(_REPLACE_SCREEN, '读区-遗器名') is not None:
            log.info('替换遗器: %s 已装备当前角色', self.piece_name)
            return self.round_success(status='ALREADY_EQUIPPED')
        return self.round_success(status='NEED_REPLACE')

    @node_from(from_name='当前装备核对', status='NEED_REPLACE')
    @node_from(from_name='确认替换', status='ROB_CONFIRM_CANCELLED')
    @node_from(from_name='验证选中', status='RESELECT')
    @operation_node(name='定位并选卡', node_max_retry_times=30)
    def find_and_select(self) -> OperationRoundResult:
        """识别器驱动的整屏识别定位目标件候选 → 逐个点击;屏内候选耗尽滚动重扫。

        定位走 RelicReplaceRecognizer.recognize_for_pos(部位先验子集:替换界面
        已按部位筛选锁定,候选收缩到单部位;与 MCP analyze_screen 同一识别链)
        —— 整屏识别一次给出全部件清单,目标件名按常量表名称直配(识别层
        argmax 输出即常量表名,无 OCR 误差)。候选排序:未装备(owner=None)
        优先 —— 同套装多副本场景下避免抢走他人装备的件。"""
        if self._scan_screens >= _SCAN_MAX_SCREENS:
            return self.round_fail(f'滚动 {_SCAN_MAX_SCREENS} 屏未找到 {self.piece_name}'
                                   f'(未拥有或识别失败)')

        screen_img = self.screenshot()
        out = RelicReplaceRecognizer().recognize_for_pos(self.ctx, screen_img, self.pos)
        matched: list[dict] = []
        if out is not None:
            matched = [item for item in out['items'] if item['piece'] == self.piece_name]
        # allow_take_over 语义的过滤与排序见 _filter_candidates(单一实现点)
        matched = _filter_candidates(matched, self.allow_take_over, self._rob_cells)

        log.info('替换遗器: 本屏识别 %d 件、目标未装备 %d 件 %s(第 %d 屏)',
                 len(out['items']) if out else 0, len(matched),
                 [(item['cell'][0], item['cell'][1]) for item in matched],
                 self._scan_screens + 1)
        if self._candidate_idx >= len(matched):
            list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-遗器列表')
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + _SCROLL_DRAG_PX // 2),
                                        Point(center.x, center.y - _SCROLL_DRAG_PX // 2))
            self._scan_screens += 1
            self._candidate_idx = 0
            return self.round_retry('当前屏候选耗尽,滚动一屏重扫', wait=1)

        item = matched[self._candidate_idx]
        cell = item['cell']
        self.ctx.controller.click(Point((cell[0] + cell[2]) // 2, (cell[1] + cell[3]) // 2))
        self._candidate_idx += 1
        self._select_retries = 0  # 重新点击后重置验证计数
        self._last_clicked_cell = (cell[0], cell[1])  #: 当前点击格(抢件弹框时记入 _rob_cells)
        log.info('替换遗器: 点击候选 %d/%d (%d,%d) owner=%s',
                 self._candidate_idx, len(matched),
                 (cell[0] + cell[2]) // 2, (cell[1] + cell[3]) // 2, item['owner'])
        return self.round_success(status='CLICKED', wait=1.2)

    @node_from(from_name='定位并选卡', status='CLICKED')
    @operation_node(name='验证选中', node_max_retry_times=10)
    def verify_selected(self) -> OperationRoundResult:
        """OCR 右侧详情件名,与目标件名 fuzzy 匹配;连续不符转回重新定位。"""
        if self._read_piece_name(_REPLACE_SCREEN, '读区-遗器名') is not None:
            return self.round_success(status='SELECTED_MATCHED')
        self._select_retries += 1
        if self._select_retries >= _RESELECT_AFTER:
            return self.round_success(status='RESELECT')
        return self.round_retry('选中名与目标不符,重读', wait=1)

    @node_from(from_name='验证选中', status='SELECTED_MATCHED')
    @operation_node(name='确认替换', node_max_retry_times=6)
    def confirm_replace(self) -> OperationRoundResult:
        """点「替换」即装备。**与光锥不同:遗器替换后停在替换界面不回着装页**,
        列表重排且选中态自动切到新装备件 —— 按钮从「替换」变回「卸下」即
        装备生效的可靠锚(until)。
        抢件确认框:owner 漏报/被穿着件点击后游戏弹「遗器已被 X 装备,
        是否替换?」—— allow_take_over=False(默认)点取消并记录该格不再点击,
        转回定位换下一候选;True 点确认完成交换(遗器装备=交换,对方拿到当前
        角色脱下的件)。取消/确认均用 area 中心直点 + 显式等待消失
        (round_by_find_and_click 的 0.8s until 判定实测误报失败)。
        ⚠️ 确认按钮 area 尚未实机建档(候实机抓坐标),True 时弹框出现会显式
        失败不误跑。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _REPLACE_SCREEN, '文本-抢件确认').is_success:
            if self.allow_take_over:
                confirm_area = self.ctx.screen_loader.get_area(
                    _REPLACE_SCREEN, '按钮-抢件确认')
                if confirm_area is None:
                    return self.round_fail(
                        'allow_take_over=True 但「按钮-抢件确认」未实机建档,'
                        '为保护双方配装显式失败(候实机抓坐标补档后重试)')
                self.ctx.controller.click(confirm_area.rect.center)
                time.sleep(1.5)
                if self.round_by_find_area(
                        self.screenshot(), _REPLACE_SCREEN, '文本-抢件确认').is_success:
                    return self.round_retry('交换确认框仍在,再点确认', wait=0.5)
                log.info('替换遗器: 交换确认已点确认(交换生效)')
                return self.round_success(status='ROB_CONFIRM_ACCEPTED')
            if self._last_clicked_cell is not None:
                self._rob_cells.add(self._last_clicked_cell)
            cancel_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-抢件取消')
            self.ctx.controller.click(cancel_area.rect.center)
            time.sleep(1.5)
            if self.round_by_find_area(self.screenshot(), _REPLACE_SCREEN, '文本-抢件确认').is_success:
                return self.round_retry('弹框仍在,再点取消', wait=0.5)
            log.info('替换遗器: 抢件确认已取消(格 %s 记入跳过清单)', self._last_clicked_cell)
            return self.round_success(status='ROB_CONFIRM_CANCELLED')
        return self.round_by_find_and_click_area(
            screen, _REPLACE_SCREEN, '按钮-替换装备',
            until_find_all=[(_REPLACE_SCREEN, '按钮-卸下')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='确认替换')
    @operation_node(name='结果核对', node_max_retry_times=5)
    def verify_result(self) -> OperationRoundResult:
        """装备结果核对:替换生效后选中态即新装备件,直接读件名核对。

        收尾停在替换界面(遗器替换的实机行为),下次 op 重入会自动先回着装页。"""
        if self._read_piece_name(_REPLACE_SCREEN, '读区-遗器名') is not None:
            log.info('替换遗器: %s 已装备当前角色', self.piece_name)
            return self.round_success(status='RELIC_EQUIPPED', wait=0.5)
        return self.round_fail('装备结果核对失败:替换界面读区与目标件名不符')
