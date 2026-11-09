"""网格卡片模板定位:SIFT 特征点落格投票(装备替换类列表共用)。

解包装备图标(光锥 348×408 / 遗器部件 512×512 透明底)作识别模板的实测边界:
- ``matchTemplate`` 像素比对不可用 —— 重采样渲染差异使分数带重叠;
- Homography 全局定位被实机卡面中心裁剪构图拉偏(实测偏差可达 120px);
- **逐匹配点落格投票**鲁棒:目标卡格得票显著(光锥实测 15:2;遗器同套装
  多件同屏时票分裂但件名相同,选任一件均满足意图)。

行定位不预设行带 —— 特征点 y 聚簇(间隔超阈值分行)动态获得,滚动后行位
变化天然适配。列中心序列由调用方提供(网格几何在各自 op 声明坐标系)。
"""


import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils, os_utils

# 特征点 y 聚簇的行间隔阈值(卡行高+间隙的量级)
_ROW_CLUSTER_GAP_PX: int = 100
# 列带吸附半径(约列间距一半)
_COL_SNAP_PX: int = 70
# 定位成功的最低票数(实机单卡 9~205 票,噪声 <3)
_MIN_CELL_VOTES: int = 4


def load_template_gray(rel_path: str) -> np.ndarray | None:
    """加载解包图标灰度图(透明底合成白底,避免透明区噪声特征)。

    :param rel_path: 项目相对路径(如 assets/game_data/... 的 / 分隔形式)
    :return: 灰度图;文件不存在返回 None(调用方判停)
    """
    path = os_utils.get_path_under_work_dir(*rel_path.split('/'))
    img = cv2_utils.read_image(path)
    if img is None:
        return None
    if img.shape[2] == 4:
        alpha = img[:, :, 3:4] / 255.0
        rgb = img[:, :, :3] * alpha + 255 * (1 - alpha)
        return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)


def identify_cells(screen_gray: np.ndarray, named_templates: dict[str, np.ndarray],
                   list_rect: Rect, col_centers: list[float],
                   min_votes: int = _MIN_CELL_VOTES) -> dict[tuple[int, int], str]:
    """批量身份识别:截图特征**只算一次**,逐命名模板落格投票,格 → 身份名。

    与逐件调 :meth:`locate_cells_by_votes` 等价,但 screen 特征(全屏检测
    ~0.5s)只算一次 + 模板特征走进程级缓存(同对象重复调用零提取成本)——
    大模板库场景(遗器全库 192 件部件图)每屏增量 ~5s。

    :param named_templates: 身份名 → 模板灰度图(如遗器件名 → 部件图)。
        同图标多件副本共享同一身份名(遗器件名 = 套装+部位唯一确定)。
        dict 需常驻(特征缓存按对象 id 键控,临时对象无法命中缓存)。
    :return: {(格 x, 格 y): 身份名};一格多模板命中时取票数最高者。
        格 y = 该模板特征点的 y 聚簇均值(非网格行带中心,调用方按需归一)。
    """
    s_kp, s_desc = cv2_utils.feature_detect_and_compute(screen_gray)
    x1, y1, x2, y2 = list_rect.x1, list_rect.y1, list_rect.x2, list_rect.y2

    cell_owner: dict[tuple[int, int], tuple[str, int]] = {}
    for name, template_gray in named_templates.items():
        t_kp, t_desc = _cached_template_features(template_gray)
        good, _, _, _ = cv2_utils.feature_match(s_kp, s_desc, t_kp, t_desc)
        pts = []
        for m in good:
            px, py = s_kp[m.trainIdx].pt
            if x1 <= px <= x2 and y1 <= py <= y2:
                pts.append((px, py))
        if len(pts) < min_votes:
            continue
        pts.sort(key=lambda p: p[1])
        clusters: list[list[tuple[float, float]]] = []
        for p in pts:
            if clusters and p[1] - clusters[-1][-1][1] <= _ROW_CLUSTER_GAP_PX:
                clusters[-1].append(p)
            else:
                clusters.append([p])
        for cluster in clusters:
            if len(cluster) < min_votes:
                continue
            cy = sum(p[1] for p in cluster) / len(cluster)
            votes = [sum(1 for p in cluster if abs(p[0] - cx) < _COL_SNAP_PX)
                     for cx in col_centers]
            for i, v in enumerate(votes):
                if v >= min_votes:
                    key = (round(col_centers[i]), round(cy))
                    prev = cell_owner.get(key)
                    if prev is None or v > prev[1]:
                        cell_owner[key] = (name, v)

    return {key: name for key, (name, _v) in cell_owner.items()}


# 模板特征进程级缓存(键 = 模板对象 id;调用方需持模板 dict 常驻才能命中——
# 临时新加载对象缓存 miss 无害,只是无收益)
_template_feature_cache: dict[int, tuple] = {}


def _cached_template_features(template_gray: np.ndarray) -> tuple:
    """模板 SIFT 特征的进程级缓存包装(id 键控;常驻模板字典场景全量命中)。"""
    key = id(template_gray)
    if key not in _template_feature_cache:
        _template_feature_cache[key] = cv2_utils.feature_detect_and_compute(template_gray)
    return _template_feature_cache[key]


def locate_cells_by_votes(screen_gray: np.ndarray, template_gray: np.ndarray,
                          list_rect: Rect, col_centers: list[float],
                          col_snap_px: int = _COL_SNAP_PX,
                          row_gap_px: int = _ROW_CLUSTER_GAP_PX,
                          min_votes: int = _MIN_CELL_VOTES) -> list[tuple[Point, int]]:
    """在替换类列表截图里定位模板图所在卡:**全量清单** —— 列表内每一个
    同图标件的位置都识别出来,不丢件、不隐式偏好。

    对每个 good match 点:计入列表区内的点,y 排序聚簇(间隔超阈值分行),
    对每个 (簇, 列) 组合计票,票数 ≥ min_votes 的组合全部返回。

    :return: [(格中心, 票数), ...] 按票数降序。同名光锥/同套装同部位的多件
        副本各占一格 —— **选哪件是调用方基于全量清单的决策**(如多角色装备
        同一把光锥时依次取不同副本,避免重复选中同一件),识别层不做隐式筛选。
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
    if len(pts) < min_votes:
        return []

    pts.sort(key=lambda p: p[1])
    clusters: list[list[tuple[float, float]]] = []
    for p in pts:
        if clusters and p[1] - clusters[-1][-1][1] <= row_gap_px:
            clusters[-1].append(p)
        else:
            clusters.append([p])

    candidates: list[tuple[Point, int]] = []
    for cluster in clusters:
        if len(cluster) < min_votes:
            continue
        cy = sum(p[1] for p in cluster) / len(cluster)
        votes = [sum(1 for p in cluster if abs(p[0] - cx) < col_snap_px) for cx in col_centers]
        for i, v in enumerate(votes):
            if v >= min_votes:
                candidates.append((Point(col_centers[i], cy), v))
    candidates.sort(key=lambda c: -c[1])
    return candidates


def locate_cell_by_votes(screen_gray: np.ndarray, template_gray: np.ndarray,
                         list_rect: Rect, col_centers: list[float],
                         col_snap_px: int = _COL_SNAP_PX,
                         row_gap_px: int = _ROW_CLUSTER_GAP_PX,
                         min_votes: int = _MIN_CELL_VOTES) -> Point | None:
    """定位模板图所在卡(最高票候选);无候选返回 None。

    多件副本场景建议用 :meth:`locate_cells_by_votes` 取全量清单
    (选哪件由调用方决策,识别层不隐式筛选)。"""
    cells = locate_cells_by_votes(screen_gray, template_gray, list_rect, col_centers,
                                  col_snap_px=col_snap_px, row_gap_px=row_gap_px,
                                  min_votes=min_votes)
    return cells[0][0] if cells else None


#------------------- 装备替换列表网格几何(识别器与 op 共用) -------------------#
# 行带中心 = 实机标定的固定值(1080p;列表可视区内完整可见的行)
# 光锥-替换:9 列等分(列中心由列表区 rect 推导),行带中心间距 200px
def cone_grid_cells(list_rect: Rect) -> list[Point]:
    """光锥替换列表全部格中心(9 列 × 4 行,行带中心 278/478/678/878 实机标定)。"""
    cell_w = (list_rect.x2 - list_rect.x1) / 9
    col_centers = [list_rect.x1 + cell_w * (i + 0.5) for i in range(9)]
    return [Point(cx, cy) for cy in (278, 478, 678, 878) for cx in col_centers]


# 遗器-替换:4 列(列表区 x1 + 首列偏移 66 + 间距 110),行带中心 260+183k 实机标定
def relic_col_centers(list_rect: Rect) -> list[float]:
    """遗器替换列表列中心(偏移+间距常量,与格中心函数同源)。"""
    return [list_rect.x1 + 66 + 110 * i for i in range(4)]


def relic_grid_cells(list_rect: Rect) -> list[Point]:
    """遗器替换列表全部格中心(4 列 × 4 行,只含列表区内完整可见行)。"""
    col_centers = relic_col_centers(list_rect)
    return [Point(cx, cy) for cy in (260, 443, 626, 809) for cx in col_centers]
