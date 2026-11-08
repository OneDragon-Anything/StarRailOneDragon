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


def locate_cell_by_votes(screen_gray: np.ndarray, template_gray: np.ndarray,
                         list_rect: Rect, col_centers: list[float],
                         col_snap_px: int = _COL_SNAP_PX,
                         row_gap_px: int = _ROW_CLUSTER_GAP_PX,
                         min_votes: int = _MIN_CELL_VOTES) -> Point | None:
    """在替换类列表截图里定位模板图所在卡:特征点落格投票。

    对每个 good match 点:计入列表区内的点,y 排序聚簇(间隔超阈值分行),
    取最大簇(≥ 最低票数),簇内点按列带投票取最高列。返回该格点击中心
    (最高票列中心, 簇 y 均值);票数不足/簇过小返回 None(目标不在当前屏)。

    同套装多件同屏(遗器场景)时票可能分裂到多列 —— 件名相同,任一列均
    满足意图,取最高票列。
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
        return None

    pts.sort(key=lambda p: p[1])
    clusters: list[list[tuple[float, float]]] = []
    for p in pts:
        if clusters and p[1] - clusters[-1][-1][1] <= row_gap_px:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    best = max(clusters, key=len)
    if len(best) < min_votes:
        return None

    votes = [sum(1 for p in best if abs(p[0] - cx) < col_snap_px) for cx in col_centers]
    best_col = max(range(len(col_centers)), key=lambda i: votes[i])
    if votes[best_col] < min_votes or votes[best_col] < len(best) * 0.5:
        return None

    cy = sum(p[1] for p in best) / len(best)
    return Point(col_centers[best_col], cy)
