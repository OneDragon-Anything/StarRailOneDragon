"""货币战争 **节点行类型识别**(纯 CV,无框架依赖;``cw_observation.read_node_sequence`` 包装接入)。

节点行(备战顶部)模型(2026-08-12 实证 + pi/VLM 确认):
- 基础 8 槽(槽 i = 第 1+i 轮),但 invest-env 会增/改节点(人身意外险+补给 / 战争边疆战斗→遭遇 /
  经济过热奖励→扑满)→ **每次到备战画面重新识别**,``detect_node_circles`` HoughCircles 动态定圆
  (圆位置/数量会变,不硬编码)。
- 三态着色:``_circle_state`` —— 已过(灰暗,低 V)/ 当前(高亮,高 S + 高 V)/ 未来(低 S)。
- 当前节点有 OCR 文字标签(``cw_observation.read_node_type``);未来节点只有图标 → Hu 矩形状匹配。
- 节点类型:战斗/奖励/遭遇/补给 4 种需模板 + 首领(= 位面最后节点,按位置判,**无模板**)+
  巨星(≠ 节点,是凑齐「盛会之星」阵营触发的强化事件)。

模板:``assets/game_data/cw_node_types/node_type_{battle,supply,encounter,reward}.png``(1-1 备战截,
pi 验圆心准)。Hu 矩(形状)匹配 —— TM 灰度/彩色对小图标不可靠(同图跨帧仅 0.5、彩色不区分),
Hu 抓 Otsu 二值化后的轮廓才稳(encounter/reward 完美、supply 可分;见 events.md 3.5.5)。

⚠️ 判态阈值 + Hu 未识别阈值来自单对局实证(2026-08-12),跨对局/版本可能漂移 → 多样本校准。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# 节点行区域(备战顶部,全屏 1080p):y 25-120, x 540-1280(商店关闭态可见;商店打开态图标仍露在 y48-70)
NODE_ROW_RECT: tuple[int, int, int, int] = (540, 25, 1280, 120)
# 判态阈值(2026-08-12 单对局实证 + 2026-08-16 V 门修正):
# - S 分:未来(低 20-37) vs 当前/过去(高 81-136)——S<60 → 未来;
# - V 分:当前(高 69-132) vs 过去(低 39-65)——V>67 → 当前,else 过去;
# - **V 下限门(2026-08-16,63 张误报实证)**:变暗的**过去**节点饱和度 S 也降到未来区间
#   (S<60)→ 仅按 S 判会把过去节点判成未来(实测 63 张「未识别误报」全是此类),下游
#   Hu 匹配/采集钩子全被污染。真未来节点亮(V 84-99),变暗过去节点暗(V 47-88 mean 67)
#   → 加 V≥V_MIN_UPCOMING 双门:V 低于此且 S 低 → 判「过去(变暗)」而非未来。
#   取 80(真未来实测 min 84 留 4 余量;变暗样本 mean 67 大半拦下;多样本校准待 3.5.5)。
STATE_S_UPCOMING: float = 60.0
STATE_V_CURRENT: float = 67.0
V_MIN_UPCOMING: float = 80.0
# 圆心采样半径(HSV 判态 + Hu 矩都用此窗,实证 R=18 稳)
_SAMPLE_R: int = 18
# Hu 未识别阈值:最近 Hu 距离 > 此 → 无模板接近(扑满/新节点类型)→ 未识别(触发采集 hook)。
# 已知类型最近距离:encounter 0.58 / reward 0.0 / supply 1.83 / battle ~1-2;故阈值取 2.8 留余量。
HU_DIST_UNRECOGNIZED: float = 2.8

HuLike = np.ndarray


@dataclass
class NodeSlot:
    """节点行一个槽的识别结果。"""

    idx: int                       # 槽号(左→右 0..)
    cx: int                        # 圆心 x(节点行裁图坐标)
    cy: int                        # 圆心 y(节点行裁图坐标;采集未识别图标定位用)
    state: str                     # past / current / upcoming
    node_type: str | None          # best Hu 匹配(未来);None(当前/过去;当前类型由 OCR 定)
    hu_dist: float | None          # 最近 Hu 距离(未来);None(当前/过去)。> HU_DIST_UNRECOGNIZED → 未识别


def _hu_moments(gray: np.ndarray) -> HuLike:
    """灰度图 → Otsu 二值 → Hu 矩(7,)。Hu 抓形状轮廓(TM 灰度对小图标不可靠)。"""
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.HuMoments(cv2.moments(th)).flatten()


def _hu_distance(a: HuLike, b: HuLike) -> float:
    """两 Hu 矩的 log-L2 距离(越小越像;Hu 跨尺度大 → log 归一)。"""
    return float(np.linalg.norm(np.log(np.abs(a) + 1e-12) - np.log(np.abs(b) + 1e-12)))


def load_node_type_templates(templates_dir: Path) -> dict[str, HuLike]:
    """加载 4 节点类型模板(battle/supply/encounter/reward)→ {type: Hu 矩(RGB luma)}。

    ⚠️ 通道对齐(2026-08-16 review P1 修正):模板 PNG 经 imdecode 读到 **BGR** → 先翻成
    RGB 语义再 ``RGB2GRAY`` 正确 luma —— 与 classify_node_row(live RGB 截图)同侧。
    (旧注释「灰度/Hu 对 RGB/BGR 无关」不成立:灰度化权重 R/B 互换产生不同 luma →
    不同 Otsu 二值 → 不同 Hu;仅 S/V 对通道序无关。)
    """
    out: dict[str, HuLike] = {}
    for t in ('battle', 'supply', 'encounter', 'reward'):
        p = templates_dir / f'node_type_{t}.png'
        if not p.exists():
            continue
        img = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        out[t] = _hu_moments(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY))
    return out


def detect_node_circles(row_gray: np.ndarray) -> list[tuple[int, int, int]]:
    """节点行灰度图 → 圆心列表 [(cx, cy, r)](左→右排)。HoughCircles(3x 放大提小圆信噪比)。"""
    big = cv2.resize(row_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    circ = cv2.HoughCircles(big, cv2.HOUGH_GRADIENT, dp=1, minDist=200,
                            param1=60, param2=40, minRadius=30, maxRadius=75)
    if circ is None:
        return []
    return sorted((int(x / 3), int(y / 3), int(r / 3)) for x, y, r in np.round(circ[0]).astype(int))


def _circle_state(row_rgb: np.ndarray, cx: int, cy: int) -> str:
    """圆的态(已过/当前/未来)via HSV 平均饱和度 S + 亮度 V(采样窗 _SAMPLE_R;RGB 输入)。

    判定序(2026-08-16 修正):
    1. S ≥ STATE_S_UPCOMING(高饱和)→ 当前/过去:V > STATE_V_CURRENT → current else past;
    2. S < 60(低饱和)但 **V < V_MIN_UPCOMING(暗)** → **past(变暗的过去节点** —— 饱和度
       随亮度一起降,单看 S 会把它误判未来,63 张误报实证);
    3. S < 60 且 V ≥ V_MIN_UPCOMING(低饱和且亮)→ upcoming(真未来,灰白图标亮底)。
    HSV 转换用 RGB2HSV(通道序与输入一致;S/V 对 RGB/BGR 序无关,H 通道有序但本函数不用)。
    """
    x0, x1 = max(0, cx - _SAMPLE_R), cx + _SAMPLE_R
    y0, y1 = max(0, cy - _SAMPLE_R), cy + _SAMPLE_R
    reg = row_rgb[y0:y1, x0:x1]
    hsv = cv2.cvtColor(reg, cv2.COLOR_RGB2HSV)
    s = float(hsv[:, :, 1].mean())
    v = float(hsv[:, :, 2].mean())
    if s >= STATE_S_UPCOMING:
        return 'current' if v > STATE_V_CURRENT else 'past'
    if v < V_MIN_UPCOMING:
        return 'past'   # 低饱和且暗 = 变暗过去节点(非未来)
    return 'upcoming'


def classify_node_row(row_rgb: np.ndarray, templates: dict[str, HuLike]) -> list[NodeSlot]:
    """节点行裁图(**RGB**,框架截图通道)→ 槽识别列表。纯 CV(无框架依赖)。

    ⚠️ 通道语义(2026-08-16 review P1 修正):框架截图链 GDI/mss → ``BGRA2RGB`` → **live 是
    RGB**;本函数此前用 ``COLOR_BGR2GRAY`` 把 RGB 当 BGR 灰度化(R/B 权重互换,错误 luma)。
    模板/fixture 经 imdecode 走 BGR —— 两侧恰好都在"错误侧"自洽,BGR 路径测试绿但 live
    从未被验证(review 实锤:RGB 传入时 idx4 supply(0.00)→encounter(1.66) 翻转)。修正:
    本函数与模板加载统一 **RGB 语义 + ``RGB2GRAY`` 正确 luma**;调用方(read_node_sequence)
    直传框架 RGB 截图;测试 fixture 传 imdecode 结果需先翻成 RGB(BGR→RGB)。

    - HoughCircles 动态定圆(数量/位置随 invest-env 变)。
    - **两段判态(2026-08-16 修正)**:
      ① HSV 找「当前槽」:S ≥ STATE_S_UPCOMING 且 V > STATE_V_CURRENT(高饱和高亮,独一);
      ② **位置先验**:节点行时间左→右递进 —— 当前槽左侧一律 past(变暗图标,HSV 单特征
         与真未来交叠 V 79-99 vs 87-88 分不开,63 张误报实证),右侧一律 upcoming。
      (旧单特征判态 S<60→upcoming 把变暗过去节点误判未来,Hu 匹配/采集钩子全被污染。)
    - 未来圆 Hu 矩匹配 4 模板 → best 类型 + 最近距离;当前/过去 node_type=None(当前类型
      由上层 OCR 标签定,见 cw_observation.read_node_sequence)。
    - 未来圆 hu_dist > HU_DIST_UNRECOGNIZED → 未识别(上层触发采集 hook,如新节点类型)。
    """
    gray = cv2.cvtColor(row_rgb, cv2.COLOR_RGB2GRAY)
    circles = detect_node_circles(gray)
    slots: list[NodeSlot] = []
    # 先定位当前槽(高饱和 + 高亮);找不到 → 退化为旧 HSV 逐槽判(保守)
    cur_idx = -1
    for i, (cx, cy, _r) in enumerate(circles):
        if _circle_state(row_rgb, cx, cy) == 'current':
            cur_idx = i
            break
    for i, (cx, cy, _r) in enumerate(circles):
        if cur_idx >= 0:
            state = 'current' if i == cur_idx else ('past' if i < cur_idx else 'upcoming')
        else:
            state = _circle_state(row_rgb, cx, cy)   # 无当前锚(罕见)→ 旧单特征兜底
        node_type: str | None = None
        hu_dist: float | None = None
        if state == 'upcoming' and templates:
            x0, x1 = max(0, cx - _SAMPLE_R), cx + _SAMPLE_R
            y0, y1 = max(0, cy - _SAMPLE_R), cy + _SAMPLE_R
            h = _hu_moments(gray[y0:y1, x0:x1])
            hu_dist, best = min((_hu_distance(h, hu), t) for t, hu in templates.items())
            node_type = best
        slots.append(NodeSlot(idx=i, cx=cx, cy=cy, state=state, node_type=node_type, hu_dist=hu_dist))
    return slots
