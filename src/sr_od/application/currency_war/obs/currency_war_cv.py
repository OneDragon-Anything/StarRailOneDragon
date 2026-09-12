"""货币战争 备战阶段 CV 检测工具(传统 cv2)。

本文件现役只保留 **槽位占用判据**(slot_occupied):布局仲裁信号③(占用
一致性,``cw_back_layout._occupancy_consistency_arbitration``)与占槽簿记
消费。历史上的 deploy 两要素颜色检测(备战栏饱和度找头像/浅青描边找空槽/
Canny 边框找槽中心)已随 deploy 链路改走 screen_info 布局档 rect + 本判据
退役删除(零外部消费实证 2026-09-12;git 历史可复活)。
"""

import cv2
from cv2.typing import MatLike

# 槽位占用判据(替 SIFT;SIFT 对备战立绘不可靠见 D-4):灰度 std。
# 空槽 placeholder 低方差(~11),立绘高方差(~39-67);阈值 25 干净分离(2026-08-09 实测)。
SLOT_OCCUPY_HALF: int = 55
SLOT_OCCUPY_STD_THR: float = 25.0


def slot_occupied(
    screen: MatLike, cx: int, cy: int,
    half: int = SLOT_OCCUPY_HALF, thr: float = SLOT_OCCUPY_STD_THR,
) -> bool:
    """槽位是否已占(有立绘)。取 (cx,cy) ± half 区域灰度 std > thr = 已占。

    替 SIFT 占用判(D-4:SIFT 误判空槽为占用 → deploy 跳前排 → 前排空 → 出战阻塞)。
    CV 灰度 std 对「立绘 vs placeholder」稳,不依赖角色身份/颜色(白角色也准)。
    """
    x1, y1 = max(0, cx - half), max(0, cy - half)
    x2, y2 = cx + half, cy + half
    crop = cv2.cvtColor(screen[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    return float(crop.std()) > thr
