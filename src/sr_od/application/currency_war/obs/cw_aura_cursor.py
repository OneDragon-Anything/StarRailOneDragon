"""货币战争 前排主角光环蓝色光标识别(光环归属可视标记,obs 纯读)。

**语义**(用户设计裁定,见 CW 跨迭代挂账 §㊲):备战画面前排角色头顶的
蓝色雪花形光标 = 主角光环的可视标记(光环在谁头上)。识别它即知光环
归属,备战帧就能读,不必依赖选择记账或点开左上角角落详情面板
(角落太小不建档识别,取舍已定;接管局真值补采走角落详情面板,
面板形态候实机探索,登记为后续口)。

**识别方案**(单模板带内 TM,先例 = ``battle_prep_recognizer.find_rail_shop_train``
横幅列车图案):光标 = 亮蓝白 8 角雪花,39×41 紧裁模板(帧 20261121_191638
前排-1 顶带,assets/template/cw_aura_marker/cw_aura_marker/raw.webp 无损归档),
带内全搜 = 画面档「标识-主角光环光标」带状 pc_rect(前排四槽头顶带
y 283-345:覆盖光标本体 y 300-341、排除各槽卡顶固有蓝条 y≥347——
该蓝条为卡片固有元素非光环标记,四槽 occupied 卡同形实证)。
命中中心 x 按建档「前排-N」槽域映射前排物理槽号。

**分离度实证**(归档帧语料 74 帧离线扫描,2026-11-21):真阳性 4 帧
(光标在槽 1 ×1 / 槽 3 ×3)score 0.806-0.964;阴性 70 帧最高 0.463;
阈值 0.7 落分离带中央,webp 归档帧真阳性仍 ≥0.806(压缩劣化不破阈)。
跨帧形态微变(发光动画疑)由带内约束 + 分离带余量吸收。

并发安全同备战识别器纪律:本模块全部纯读(不写 self./全局状态;
模板缓存 = 模块级只读幂等,同 ``_get_rail_train_gray`` 手法),可在
CW operation 运行期间被并发调用。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.kernel.cw_game_state import (
    DEPLOYED_FRONT_CAPACITY_DEFAULT,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    _area_rect,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext


#: TM 匹配阈值(与画面档「标识-主角光环光标」template_match_threshold 同口径;
#: 分离度实证见模块 docstring)。
_AURA_CURSOR_TM_THR: float = 0.7

#: 光标搜索带 area 名(前排四槽头顶带,坐标单一真相源 = screen_info)。
A_AURA_CURSOR: str = '标识-主角光环光标'

_marker_gray: MatLike | None = None
_marker_loaded: bool = False


def _get_marker_gray() -> MatLike | None:
    """加载光标模板灰度图(模块级缓存,幂等,缺文件 → None)。

    加载手法同 ``battle_prep_recognizer._get_rail_train_gray``
    (并发安全:模块级只读模板缓存)。模板与画面同权重转灰度,
    相对匹配一致(转换口径与真值通道序无关)。
    """
    global _marker_gray, _marker_loaded
    if not _marker_loaded:
        _marker_loaded = True
        p = (get_project_root() / 'assets' / 'template'
             / 'cw_aura_marker' / 'cw_aura_marker' / 'raw.webp')
        img = cv2.imdecode(np.fromfile(str(p), np.uint8),
                           cv2.IMREAD_COLOR) if p.is_file() else None
        _marker_gray = (cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        if img is not None else None)
    return _marker_gray


def find_aura_cursor(screen: MatLike, rect: Rect) -> tuple[float, int, int] | None:
    """纯 CV 核心:光标带内 TM 匹配 → ``(score, cx, cy)`` | None(离线可测,无 ctx 依赖)。

    命中判定 score ≥ ``_AURA_CURSOR_TM_THR``(与画面档阈值同口径);
    cx/cy = 匹配中心(1080p 绝对坐标,槽位映射消费,非点击点)。
    灰度转换与模板加载同 ``find_rail_shop_train`` 手法。

    Args:
        screen: 备战画面截图。
        rect: 搜索带(画面档「标识-主角光环光标」pc_rect)。
    """
    tm = _get_marker_gray()
    if tm is None:
        return None
    gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    crop = gray[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.shape[0] < tm.shape[0] or crop.shape[1] < tm.shape[1]:
        return None
    _, max_val, _, max_loc = cv2.minMaxLoc(
        cv2.matchTemplate(crop, tm, cv2.TM_CCOEFF_NORMED))
    if max_val < _AURA_CURSOR_TM_THR:
        return None
    return (max_val, rect.x1 + max_loc[0] + tm.shape[1] // 2,
            rect.y1 + max_loc[1] + tm.shape[0] // 2)


def map_aura_x_to_slot(cx: int, slot_rects: list[Rect]) -> int | None:
    """光标命中中心 x → 前排物理槽号(纯函数,离线可测)。

    Args:
        cx: TM 命中中心 x(1080p 绝对坐标)。
        slot_rects: 前排槽域 rect 列表(建档「前排-N」升序,下标 = 槽号-1)。

    Returns:
        槽号 1 基;cx 落在全部槽域之外 = None(读链漂移信号,宁缺勿造)。
    """
    for i, r in enumerate(slot_rects):
        if r.x1 <= cx <= r.x2:
            return i + 1
    return None


def read_front_aura_slot(ctx: SrContext, screen: MatLike) -> int | None:
    """备战画面读前排主角光环光标槽位(纯读)→ 前排物理槽 1 基 | None。

    消费方 = 备战 heavy 观察(CwScreenPrep,写 game state ``aura_slot``)
    与备战识别器 extras(MCP 读数面,同源单一实现)。

    - 模板未归档 / 带域或前排槽域建档缺失 → None(识别域未就绪,宁缺勿造);
    - 带内 TM 未命中 → None(无光环 / 主角在后排的未采样形态——
      识别面 = 前排四槽头顶带,用户裁定取舍;识别不到交调用方走
      失读保旧值纪律,接管局角落详情面板补真值为登记后续口)。
    """
    if _get_marker_gray() is None:
        return None
    band = _area_rect(ctx, A_AURA_CURSOR, SCREEN_NAME)
    if band is None:
        return None
    slot_rects: list[Rect] = []
    for i in range(1, DEPLOYED_FRONT_CAPACITY_DEFAULT + 1):
        r = _area_rect(ctx, f'前排-{i}', SCREEN_NAME)
        if r is None:
            return None
        slot_rects.append(r)
    hit = find_aura_cursor(screen, band)
    if hit is None:
        return None
    _, cx, _cy = hit
    return map_aura_x_to_slot(cx, slot_rects)
