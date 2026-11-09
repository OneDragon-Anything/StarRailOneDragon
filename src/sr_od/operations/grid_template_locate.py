"""网格卡片模板定位:SIFT 特征点落格投票(装备替换类列表共用)。

装备图标模板(光锥 348×408 / 遗器部件 512×512 透明底)的识别边界实测:
- ``matchTemplate`` 像素比对不可用 —— 重采样渲染差异使分数带重叠;
- Homography 全局定位被实机卡面中心裁剪构图拉偏(实测偏差可达 120px);
- **逐匹配点落格投票**鲁棒:目标卡格得票显著(光锥实测 15:2;遗器同套装
  多件同屏时票分裂但件名相同,选任一件均满足意图)。

行定位不预设行带 —— 特征点 y 聚簇(间隔超阈值分行)动态获得,滚动后行位
变化天然适配。列中心序列由调用方提供(网格几何在各自 op 声明坐标系)。
"""


import re

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
    """加载图标模板灰度图(透明底合成白底,避免透明区噪声特征)。

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
                   list_rect: Rect, anchor_cx: list[float] | None = None,
                   min_votes: int = _MIN_CELL_VOTES) -> list[tuple[float, float, int, str]]:
    """批量身份识别:截图特征**只算一次**,逐命名模板落格投票,输出命中簇明细。

    与逐件调 :meth:`locate_cells_by_votes` 等价,但 screen 特征(全屏检测
    ~0.5s)只算一次 + 模板特征走进程级缓存(同对象重复调用零提取成本)——
    大模板库场景(遗器全库 192 件部件图)每屏增量 ~5s。

    :param named_templates: 身份名 → 模板灰度图(如遗器件名 → 部件图)。
        同图标多件副本共享同一身份名(遗器件名 = 套装+部位唯一确定)。
        dict 需常驻(特征缓存按对象 id 键控,临时对象无法命中缓存)。
    :param anchor_cx: 计票吸附的列中心 x 列表(卡矩形中心 x,锚点/轮廓检测给出)。
        同一行内多个卡位的匹配点必须**对各卡位分别计票**——簇均值自吸附会把
        相邻卡的点混算成 1 票(2026-11-09 实证漏检根因);None 时回退簇均值
        自吸附(单卡场景)。
    :return: [(簇中心 x, 簇中心 y, 票数, 身份名), ...] 按票数降序;
        **位置由匹配自身给出**(调用方与锚点推算的卡区域做重叠归属,
        不依赖预设网格)。一格多模板命中时各模板条目并存,由调用方仲裁。
    """
    s_kp, s_desc = cv2_utils.feature_detect_and_compute(screen_gray)
    x1, y1, x2, y2 = list_rect.x1, list_rect.y1, list_rect.x2, list_rect.y2

    hits: dict[tuple[int, int], tuple[str, int]] = {}
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
            ccx = sum(p[0] for p in cluster) / len(cluster)
            ccy = sum(p[1] for p in cluster) / len(cluster)
            centers = anchor_cx if anchor_cx else [ccx]
            for cx in centers:
                votes = sum(1 for p in cluster if abs(p[0] - cx) < _COL_SNAP_PX)
                if votes >= min_votes:
                    key = (round(cx), round(ccy))
                    prev = hits.get(key)
                    if prev is None or votes > prev[1]:
                        hits[key] = (name, votes)

    return [(float(k[0]), float(k[1]), v, name)
            for k, (name, v) in sorted(hits.items(), key=lambda kv: -kv[1][1])]


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


#------------------- 装备替换列表卡位:等级文本锚点(识别器用) -------------------#
# 替换列表每张卡底部都有等级徽章文本(光锥「等级N」/ 遗器「+N」)——OCR 命中位置
# 即卡位锚点,滚动 / 命途分组头 / 空格天然免疫;固定网格几何在滚动后失效,已废弃。

_LEVEL_TEXT_RE = re.compile(r'^(等级\d+|\+\d+)$')


def detect_card_rects_contours(screen_gray: np.ndarray, list_rect: Rect) -> list[Rect]:
    """轮廓检测定位列表卡(等级文本锚点的补充锚):Canny+外轮廓,按卡尺寸窗过滤。

    价值在「不完整卡位」:滚动到列表边缘被裁切的卡没有等级文本锚(文本滚出
    可视区),但可见部分的轮廓仍可检出 —— 检出矩形可能只是卡的一部分(不完整),
    调用方据此标记该卡为部分可见。与锚点卡去重(IoU 重叠)后合并使用。

    :return: 检出的卡矩形(可见部分),按 (行, 列) 排序。
    """
    roi = screen_gray[list_rect.y1:list_rect.y2, list_rect.x1:list_rect.x2]
    edges = cv2.Canny(roi, 40, 120)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects: list[Rect] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # 卡尺寸窗(光锥 139×155 / 遗器 120×160,部分可见卡允许缩小)
        if not (60 < w < 200 and 70 < h < 220):
            continue
        if cv2.contourArea(c) / (w * h) < 0.5:
            continue
        rects.append(Rect(x + list_rect.x1, y + list_rect.y1,
                          x + w + list_rect.x1, y + h + list_rect.y1))
    rects.sort(key=lambda r: (r.y1 // 100, r.x1))
    return rects


def detect_card_anchors(ocr_results: list, list_rect: Rect) -> list[Rect]:
    """从全图 OCR 结果提取装备卡的等级文本锚点,换算卡矩形预期区域。

    :param ocr_results: 全图 OCR 结果列表(OcrMatchResult,含 .data/.rect)
    :param list_rect: 列表区(锚点须落在其内,排除右侧详情面板等)
    :return: 卡矩形清单(每个等级文本一张卡),按 (行, 列) 排序。
        换算标定:光锥卡 139×155、文本中心=卡中心 x、卡底=文本 cy+12;
        遗器卡 120×160、文本中心=卡中心 x、卡底=文本 cy+22(按文本样式自动区分)。
    """
    rects: list[Rect] = []
    for r in ocr_results:
        text = str(r.data).strip()
        if not _LEVEL_TEXT_RE.match(text):
            continue
        rect = r.rect
        cx = (rect.x1 + rect.x2) / 2
        cy = (rect.y1 + rect.y2) / 2
        if text.startswith('等级'):  # 光锥:卡 139×155
            rect_card = Rect(cx - 70, cy - 143, cx + 69, cy + 12)
        else:  # 遗器「+N」:卡 120×160
            rect_card = Rect(cx - 60, cy - 138, cx + 60, cy + 22)
        # 卡矩形须与列表区相交(排除详情面板等区外文本)
        if rect_card.x2 < list_rect.x1 or rect_card.x1 > list_rect.x2:
            continue
        if rect_card.y2 < list_rect.y1 or rect_card.y1 > list_rect.y2:
            continue
        rects.append(rect_card)
    rects.sort(key=lambda r: (r.y1 // 100, r.x1))
    return rects


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


#------------------- 装备替换列表网格几何(已废弃固定网格,卡位走等级文本锚点) -------------------#
# 遗器 4 列列中心公式仍被替换 op 的特征落格投票使用(op 自身在列表顶部工作,列位置固定)。
def relic_col_centers(list_rect: Rect) -> list[float]:
    """遗器替换列表列中心(偏移+间距常量,与替换 op 同源)。"""
    return [list_rect.x1 + 66 + 110 * i for i in range(4)]
