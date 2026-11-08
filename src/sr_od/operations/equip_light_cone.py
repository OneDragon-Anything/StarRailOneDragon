"""光锥 TAB → 替换光锥 operation(为当前角色装备指定光锥)。

角色养成系列的装备线 op:换光锥是配装调整动作(如刷材料前换辅助光锥)。
交互链全流程实机摸底:
- 光锥 TAB 点「替换」→ 光锥替换界面:9 列卡片网格,分「与角色命途相符 /
  不相符」两组;**卡片上没有光锥名**(名字仅选中后右侧对比栏可读);
- 选卡后右侧变对比布局(当前装备 → 新选中),底部出现「替换」按钮;
- 点「替换」**直接生效并自动回光锥 TAB,无确认弹窗** —— 替换是即时操作。

识别定位(解包图标作识别模板的算法边界实测):
- 解包图(``assets/game_data/light_cone_icons``,348×408 斜置卡牌)经
  ``cv2_utils.feature_match`` 特征匹配可直接当模板(透明底合成白底转灰度;
  ``matchTemplate`` 像素比对不可用——重采样渲染差异使分数带重叠);
- 定位用**特征点落格投票**而非 Homography 框:实机卡面是斜置卡牌的中心
  裁剪构图,Homography 估计会被拉偏(实测偏差可达 120px);逐匹配点按
  「x 落列带 + y 聚簇(间隔 >100px 分行)」投票,目标卡格得票显著最高
  (实机 15:2 / 9:2),取最高票簇中心吸附列中心点击;
- 未命中滚动一屏重扫(拖拽,有界);OCR 验证用右侧对比栏读区(名带形近
  变体,如「於/于」,fuzzy 匹配兜底)。

前置:光锥 TAB(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('光锥') 保证);起点不符显式失败。
⚠️ 装备即改变角色配装(即时生效),调用方须确认目标光锥正确。
"""


import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, os_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_light_cones import LIGHT_CONE_BY_NAME, icon_webp_rel_path
from sr_od.operations.sr_operation import SrOperation

_LC_TAB_SCREEN: str = '角色-光锥'
_REPLACE_SCREEN: str = '光锥-替换'

# 网格几何:9 列均分列表区(列中心由区域 rect 推导,实测误差 <2px);
# 行位置随滚动变化,不预设行带 —— 由特征点 y 聚簇动态获得
_GRID_COLS: int = 9
# 每屏扫描的滚动拖拽:列表中心上移 300px(约 2 行卡位,避免跳行)
_SCROLL_DRAG_PX: int = 300
# 滚动扫描的屏幕数上限(全列表多屏,防无限滚)
_SCAN_MAX_SCREENS: int = 12
# 特征点聚簇的行间隔阈值(卡行高 ~170px + 间隙)
_ROW_CLUSTER_GAP_PX: int = 100
# 列带吸附半径(列间距 ~139px 的一半)
_COL_SNAP_PX: int = 70
# 定位成功的最低票数(实机单卡 9~19 票,噪声 <3)
_MIN_CELL_VOTES: int = 4


def _load_template_gray(cone_name: str) -> np.ndarray | None:
    """按光锥名加载解包图标灰度图(透明底合成白底,避免透明区噪声特征)。

    :raises KeyError: 光锥名不在常量表(调用方前置校验过,防御保留)
    """
    cone = LIGHT_CONE_BY_NAME.get(cone_name)
    if cone is None:
        return None
    path = os_utils.get_path_under_work_dir(*icon_webp_rel_path(cone.tid).split('/'))
    img = cv2_utils.read_image(path)
    if img is None:
        return None
    if img.shape[2] == 4:
        alpha = img[:, :, 3:4] / 255.0
        rgb = img[:, :, :3] * alpha + 255 * (1 - alpha)
        return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)


def _locate_cone_cell(screen_gray: np.ndarray, template_gray: np.ndarray,
                      list_rect: Rect) -> Point | None:
    """在替换界面截图里定位目标光锥卡:特征点落格投票。

    对每个 good match 点:计入列表区内的点,y 排序聚簇(间隔超阈值分行),
    取最大簇(≥ 最低票数),簇内点按列带投票取最高列。返回该格点击中心
    (列中心, 簇 y 均值);票数不足/簇过小返回 None(目标不在当前屏)。
    """
    s_kp, s_desc = cv2_utils.feature_detect_and_compute(screen_gray)
    t_kp, t_desc = cv2_utils.feature_detect_and_compute(template_gray)
    good, _, _, _ = cv2_utils.feature_match(s_kp, s_desc, t_kp, t_desc)

    x1, y1, x2, y2 = list_rect.x1, list_rect.y1, list_rect.x2, list_rect.y2
    pts = []
    for m in good:
        px, py = s_kp[m.trainIdx].pt
        if x1 <= px <= x2 and y1 <= py <= y2:
            pts.append((px, py))
    if len(pts) < _MIN_CELL_VOTES:
        return None

    pts.sort(key=lambda p: p[1])
    clusters: list[list[tuple[float, float]]] = []
    for p in pts:
        if clusters and p[1] - clusters[-1][-1][1] <= _ROW_CLUSTER_GAP_PX:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    best = max(clusters, key=len)
    if len(best) < _MIN_CELL_VOTES:
        return None

    cell_w = (x2 - x1) / _GRID_COLS
    col_centers = [x1 + cell_w * (i + 0.5) for i in range(_GRID_COLS)]
    votes = [sum(1 for p in best if abs(p[0] - cx) < _COL_SNAP_PX) for cx in col_centers]
    best_col = max(range(_GRID_COLS), key=lambda i: votes[i])
    if votes[best_col] < _MIN_CELL_VOTES or votes[best_col] < len(best) * 0.5:
        return None

    cy = sum(p[1] for p in best) / len(best)
    return Point(col_centers[best_col], cy)


class EquipLightConeOp(SrOperation):
    """为当前角色装备指定光锥,终点 = 光锥 TAB(读区已显示目标光锥)。

    结果状态:ALREADY_EQUIPPED(已装备,幂等成功)/ LIGHT_CONE_EQUIPPED(替换完成)。
    失败:CONE_NOT_FOUND(名字不在常量表)/ 列表扫完未找到(未拥有或识别失败)。
    ⚠️ 替换即时生效,调用方须确认目标光锥正确。
    """

    def __init__(self, ctx: SrContext, cone_name: str):
        """
        :param ctx: 上下文
        :param cone_name: 目标光锥全名(如「行于流逝的岸」;须与光锥列表显示名一致)
        """
        self.cone_name: str = cone_name
        self._scan_screens: int = 0   #: 已扫描的屏幕数(滚动预算)
        SrOperation.__init__(self, ctx, op_name=gt('替换光锥') + f'({cone_name})',
                             node_max_retry_times=24)

    #------------------- 识别辅助 -------------------#

    def _read_name(self, screen_name: str, area_name: str) -> str | None:
        """OCR 读指定画面的名字读区,返回最相似的目标名判定由调用方做。"""
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.pc_rect, crop_first=True)
        texts = [str(r.data) for r in results]
        idx = str_utils.find_in_list_with_fuzzy(self.cone_name, texts, cutoff=0.6)
        return texts[idx] if idx is not None else None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:光锥 TAB 或替换界面;已装备目标光锥直接成功(幂等)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _REPLACE_SCREEN, '标题-光锥替换').is_success:
            return self.round_success(status='IN_REPLACE_SCREEN')

        if not self.round_by_find_area(screen, _LC_TAB_SCREEN, '标题-角色光锥').is_success:
            return self.round_fail('不在光锥 TAB(前置:进详情 + 选角色 + 切「光锥」页签)')

        if self._read_name(_LC_TAB_SCREEN, '读区-光锥名') is not None:
            log.info('替换光锥: %s 已装备当前角色', self.cone_name)
            return self.round_success(status='ALREADY_EQUIPPED')
        return self.round_success(status='CAN_REPLACE')

    @node_from(from_name='入口核对', status='ALREADY_EQUIPPED')
    @operation_node(name='已装备收尾')
    def already_equipped(self) -> OperationRoundResult:
        return self.round_success(status='ALREADY_EQUIPPED')

    @node_from(from_name='入口核对', status='CAN_REPLACE')
    @node_from(from_name='入口核对', status='IN_REPLACE_SCREEN')
    @operation_node(name='打开替换界面', node_max_retry_times=6)
    def open_replace(self) -> OperationRoundResult:
        """光锥 TAB 点「替换」→ 替换界面(until=双锚:标题+命途相符组头)。

        已在替换界面(IN_REPLACE_SCREEN)时直接确认成功。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _REPLACE_SCREEN, '标题-光锥替换').is_success:
            return self.round_success(status='REPLACE_SCREEN_OPEN')
        return self.round_by_find_and_click_area(
            screen, _LC_TAB_SCREEN, '按钮-替换',
            until_find_all=[
                (_REPLACE_SCREEN, '标题-光锥替换'),
                (_REPLACE_SCREEN, '文本-命途相符组头'),
            ],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开替换界面')
    @node_from(from_name='打开替换界面', status='REPLACE_SCREEN_OPEN')
    @operation_node(name='定位并选卡', node_max_retry_times=30)
    def find_and_select(self) -> OperationRoundResult:
        """SIFT 落格投票定位目标卡 → 点击;未命中滚动重扫(框架重试驱动,有界)。"""
        if self._scan_screens >= _SCAN_MAX_SCREENS:
            return self.round_fail(f'滚动 {_SCAN_MAX_SCREENS} 屏未找到 {self.cone_name}'
                                   f'(未拥有或识别失败)')

        screen_img = self.screenshot()
        template = _load_template_gray(self.cone_name)
        if template is None:
            return self.round_fail(f'光锥名 {self.cone_name} 不在常量表(CONES_NOT_FOUND)')
        list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-光锥列表')
        cell = _locate_cone_cell(cv2.cvtColor(screen_img, cv2.COLOR_RGB2GRAY),
                                 template, list_area.rect)
        if cell is None:
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + _SCROLL_DRAG_PX // 2),
                                        Point(center.x, center.y - _SCROLL_DRAG_PX // 2))
            self._scan_screens += 1
            return self.round_retry('当前屏未命中,滚动一屏重扫', wait=1)

        self.ctx.controller.click(cell)
        log.info('替换光锥: 定位到目标卡 (%.0f, %.0f),第 %d 屏', cell.x, cell.y, self._scan_screens + 1)
        return self.round_success(status='CLICKED', wait=1.2)

    @node_from(from_name='定位并选卡', status='CLICKED')
    @operation_node(name='验证选中', node_max_retry_times=10)
    def verify_selected(self) -> OperationRoundResult:
        """OCR 右侧对比栏选中名,与目标名 fuzzy 匹配(名带形近变体)。"""
        if self._read_name(_REPLACE_SCREEN, '读区-选中光锥名') is not None:
            return self.round_success(status='SELECTED_MATCHED')
        return self.round_retry('选中名与目标不符,重读', wait=1)

    @node_from(from_name='验证选中', status='SELECTED_MATCHED')
    @operation_node(name='确认替换', node_max_retry_times=6)
    def confirm_replace(self) -> OperationRoundResult:
        """点「替换」→ 直接生效并自动回光锥 TAB(until=标题回 TAB)。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _REPLACE_SCREEN, '按钮-替换',
            until_find_all=[(_LC_TAB_SCREEN, '标题-角色光锥')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='确认替换')
    @operation_node(name='结果核对')
    def verify_result(self) -> OperationRoundResult:
        """回 TAB 后读光锥名读区做最终核对。"""
        if self._read_name(_LC_TAB_SCREEN, '读区-光锥名') is not None:
            log.info('替换光锥: %s 已装备当前角色', self.cone_name)
            return self.round_success(status='LIGHT_CONE_EQUIPPED', wait=0.5)
        return self.round_fail('替换后光锥名读区与目标不符(识别失败或替换未生效)')
