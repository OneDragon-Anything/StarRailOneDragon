"""遗器位 → 替换遗器 operation(为当前角色装备指定套装的指定部位遗器)。

角色养成系列的装备线 op(与 EquipLightConeOp 同构,定位算法共用
grid_template_locate)。交互链实机摸底:
- 角色遗器着装页**点目标遗器位直达该部位的替换界面**(部位筛选已锁定,
  无需先点「替换」再选部位);4 列卡片网格;
- 卡片上无遗器名(单件名只在选中后右侧详情可读);同套装同部位件名相同
  (单件名由套装+部位唯一确定)——识别参数 = 单件名,PIECE_TO_SET 反查
  套装与部位;解包部件图(iconrelic_<set_id>_<pos>)作 SIFT 模板落格投票,
  同套装多件同屏时票分裂到多列但件名相同,选任一件均满足意图;
- 选中未装备件后底部按钮「卸下」变「替换」;点「替换」即装备(实测即时
  生效,给已由他人装备的件会直接从对方身上换下)。

前置:角色遗器着装页(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('遗器') 保证);起点不符显式失败。
⚠️ 装备即时生效且可能从其他角色身上换下,调用方须确认目标正确。
"""


import time

import cv2

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_relic_sets import PIECE_TO_SET, icon_webp_rel_path
from sr_od.operations.grid_template_locate import (
    load_template_gray,
    locate_cell_by_votes,
)
from sr_od.operations.sr_operation import SrOperation

_RELIC_TAB_SCREEN: str = '角色-遗器'
_REPLACE_SCREEN: str = '遗器-替换'

# 网格几何:4 列,首列中心相对列表区 x1 偏移 66px、列间距 110px
# (实机实测;列表区 rect 见 screen_info「区域-遗器列表」,等分推导不成立 ——
#  左边距与卡间距不均匀,故用偏移+间距双常量声明,坐标系 = 列表区 rect 内像素)
_GRID_COL_OFFSET: int = 66
_GRID_COL_GAP: int = 110
# 每屏扫描的滚动拖拽:列表中心上移 300px(约 2 行卡位,避免跳行)
_SCROLL_DRAG_PX: int = 300
# 滚动扫描的屏幕数上限
_SCAN_MAX_SCREENS: int = 12
# 验证选中连续不符次数达此值 → 转回重新定位
_RESELECT_AFTER: int = 3

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


class EquipRelicOp(SrOperation):
    """为当前角色装备指定遗器(按单件名定位套装与部位),终点 = 遗器着装页。

    结果状态:ALREADY_EQUIPPED(已装备,幂等成功)/ RELIC_EQUIPPED(替换完成,
    着装页套装效果读区含目标套装名核对)。
    失败:PIECE_NOT_FOUND(件名不在常量表)/ 列表扫完未找到(未拥有或识别失败)。
    ⚠️ 替换即时生效;目标件若由其他角色装备中,会直接从对方身上换下。
    """

    def __init__(self, ctx: SrContext, piece_name: str):
        """
        :param ctx: 上下文
        :param piece_name: 遗器单件名(如「先驱的绝热围壳」;套装+部位唯一确定,
            同套装同部位的多件副本任意一件均满足)
        """
        piece_def = PIECE_TO_SET.get(piece_name)
        if piece_def is None:
            raise ValueError(f'遗器单件名 {piece_name} 不在常量表(PIECE_TO_SET)')
        piece = next(p for p in piece_def.pieces if p.name == piece_name)
        self.piece_name: str = piece_name
        self.set_name: str = piece_def.set_name
        self.pos: int = piece.pos  # 部位坐标:1头 2手 3躯干 4脚 5位面球 6连结绳(常量表固化)
        self._scan_screens: int = 0
        self._select_retries: int = 0
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

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对并进入部位', is_start_node=True, node_max_retry_times=8)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:点目标遗器位直达该部位替换界面。

        着装页遗器位与替换界面返回箭头均为**纯坐标区**(无文本/模板,find
        不命中)—— 一律坐标点击;转移验证:点遗器位后查替换界面标题,点返回
        后靠节点重入(重入时替换界面应已关)。重入已在替换界面时先返回着装
        页 —— 界面按部位筛选,重入的筛选部位可能与目标不符(实机复现)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _REPLACE_SCREEN, '标题-遗器替换').is_success:
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
            return self.round_success(status='ENTERED_REPLACE', wait=1)
        return self.round_retry('点遗器位后替换界面未确认,重试', wait=1.5)

    @node_from(from_name='入口核对并进入部位')
    @operation_node(name='当前装备核对', node_max_retry_times=6)
    def check_current(self) -> OperationRoundResult:
        """替换界面右侧详情默认显示当前装备件:已是目标 = 幂等成功。"""
        if self._read_piece_name(_REPLACE_SCREEN, '读区-遗器名') is not None:
            log.info('替换遗器: %s 已装备当前角色', self.piece_name)
            return self.round_success(status='ALREADY_EQUIPPED')
        return self.round_success(status='NEED_REPLACE')

    @node_from(from_name='当前装备核对', status='NEED_REPLACE')
    @operation_node(name='定位并选卡', node_max_retry_times=30)
    def find_and_select(self) -> OperationRoundResult:
        """SIFT 落格投票定位目标套装件 → 点击;未命中滚动重扫(框架重试驱动)。"""
        if self._scan_screens >= _SCAN_MAX_SCREENS:
            return self.round_fail(f'滚动 {_SCAN_MAX_SCREENS} 屏未找到 {self.piece_name}'
                                   f'(未拥有或识别失败)')

        screen_img = self.screenshot()
        set_def = PIECE_TO_SET[self.piece_name]
        template = load_template_gray(icon_webp_rel_path(set_def.set_id, self.pos))
        if template is None:
            return self.round_fail(f'遗器图标缺失:'
                                   f'{icon_webp_rel_path(set_def.set_id, self.pos)}')
        list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-遗器列表')
        cell = locate_cell_by_votes(cv2.cvtColor(screen_img, cv2.COLOR_RGB2GRAY),
                                    template, list_area.rect, _relic_col_centers(list_area.rect))
        if cell is None:
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + _SCROLL_DRAG_PX // 2),
                                        Point(center.x, center.y - _SCROLL_DRAG_PX // 2))
            self._scan_screens += 1
            return self.round_retry('当前屏未命中,滚动一屏重扫', wait=1)

        self.ctx.controller.click(cell)
        self._select_retries = 0  # 重新点击后重置验证计数
        log.info('替换遗器: 定位到目标卡 (%.0f, %.0f),第 %d 屏', cell.x, cell.y, self._scan_screens + 1)
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
        """点「替换」即装备 → 自动回着装页(until=标题回 TAB)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _REPLACE_SCREEN, '按钮-替换装备',
            until_find_all=[(_RELIC_TAB_SCREEN, '标题-遗器着装')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='确认替换')
    @operation_node(name='结果核对', node_max_retry_times=5)
    def verify_result(self) -> OperationRoundResult:
        """装备结果核对:重进部位替换界面读装备件名。

        着装页无单件名读区,套装效果读区仅在成套(≥2 件)时含套装名 ——
        散件换装(1 件)读不到,故重进部位界面读右侧详情的当前装备件名核对
        (替换界面默认选中当前装备件)。收尾停在替换界面,下次 op 重入会
        自动先回着装页。"""
        slot = self.ctx.screen_loader.get_area(_RELIC_TAB_SCREEN, _POS_TO_SLOT_AREA[self.pos])
        self.ctx.controller.click(slot.rect.center)
        result = self.round_by_find_area(self.screenshot(), _REPLACE_SCREEN, '标题-遗器替换')
        if not result.is_success:
            return self.round_fail('重进部位界面失败,无法核对装备结果')
        if self._read_piece_name(_REPLACE_SCREEN, '读区-遗器名') is not None:
            log.info('替换遗器: %s 已装备当前角色', self.piece_name)
            return self.round_success(status='RELIC_EQUIPPED', wait=0.5)
        return self.round_fail('装备结果核对失败:部位界面读区与目标件名不符')
