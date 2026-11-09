"""逐光捡金编队识别:左侧角色列表(锚驱动整页主扫 / 固定网格 / 点击中心)。

角色列表卡主路径 = **整页多目标模板匹配**(见 ``_match_page_characters``):
区域特征一次提取 → 全模板 SIFT 定位 → 等级锚归属 → 内点数仲裁;无命中锚
回退逐格裁片匹配兜底(模板特征贫乏的角色在整页比值测试下好匹配不足)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    SCREEN_NAME,
    AnchorCell,
    GridCell,
    MemberGuess,
    PageHit,
    get_area_rect,
    identify_crop,
)
from sr_od.config.avatar_templates import AvatarTemplate, iter_avatar_templates

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

# --------------------------------------------------------------------------
# 左侧角色网格几何(相对「区域-角色网格」rect 原点;实机帧标定)
# 4 列 × 可见 4 行;单元格头像子区 88x94,列距 117、行距 165。
# 网格可滚动,超出可见行的成员不在本帧结果内(跨帧合并是消费方职责)。
# --------------------------------------------------------------------------
_GRID_COLS: int = 4
_GRID_ROWS: int = 4
_GRID_CELL_X_OFF: int = 15          #: 首列头像子区 x 偏移(全图 53 - 网格区 x1 38)
_GRID_CELL_Y_OFF: int = 16          #: 首行头像子区 y 偏移(全图 186 - 网格区 y1 170)
_GRID_CELL_DX: int = 117            #: 列距(首格中心 97 → 次列 215)
_GRID_CELL_DY: int = 165            #: 行距(首行 240 → 次行 405)
_GRID_CELL_W: int = 88
_GRID_CELL_H: int = 94

# --------------------------------------------------------------------------
# 等级文本锚驱动识别(角色列表,滚动停驻位置无关):
# 每张卡下方有「等级NN」文本条,OCR 找锚 → 锚上方裁头像区 → 脸库匹配。
# 固定网格几何(read_character_grid)在滚动停半格时行列偏移裁错位——锚跟随
# 卡片实际位置,任意停驻都可识别。裁片几何按实机帧标定:
# 锚(x)=卡左缘+5,锚(y)=等级条文本顶;头像区 = 锚上方 95px 高、宽 95px
# (x1 = 锚左移 10px 与卡面左缘对齐,右缘位置不变)。
# --------------------------------------------------------------------------
_LEVEL_ANCHOR_TEXT: str = '等级'
_LEVEL_ANCHOR_AVATAR_W: int = 95
_LEVEL_ANCHOR_AVATAR_H: int = 95
_LEVEL_ANCHOR_DX: int = -10           #: 头像区 x1 相对锚 x 偏移(左缘与卡面可视左缘对齐;
                                      #  原 -5/宽90 左缘切进卡面约 5px,实机帧标注比对确认)
_LEVEL_ANCHOR_DY: int = -97           #: 头像区 y1 相对锚 y 偏移

# --------------------------------------------------------------------------
# 整页多目标模板匹配(角色列表主识别路径):
# 列表区特征提取一次 → 脸库逐模板 knn 比值测试 + RANSAC 单应 → 模板四角投影
# 定位 → 内点数门槛,命中投影框与锚头像区重叠归属。替代逐格裁片匹配的动机:
# ①页面特征只算一次、全模板共享;②命中自带全图定位,无裁剪窗口错位类问题;
# ③RANSAC 内点数是更可信的置信量纲——真身命中内点多且内点率≈1.0,伪命中内点少。
# 标定(角色头像模板库实机帧):整行真身 13-59 内点,半行弱卡与伪命中更低,门槛取间隙。
# 边界:模板特征贫乏的角色(特征点 <40)在整页比值测试下好匹配不足、RANSAC
# 不收敛——由空锚裁片兜底覆盖(见 read_character_cells_by_level);
# 两级比值测试(严格级不足再放宽重筛)经实验否决:放宽不增加贫乏模板的真身
# 命中,反而引入跨区域假投影框。
# --------------------------------------------------------------------------
_PAGE_RATIO_TEST: float = 0.70       #: knn 比值测试阈值(与裁片路径现役口径一致)
_PAGE_MATCH_MIN_INLIERS: int = 12    #: 命中门槛:RANSAC 内点数(真身 13-59 的下沿)
_PAGE_AMBIGUITY_RATIO: float = 1.25  #: top1/top2 内点比门槛(低于 = 候选诚实返回不硬猜)
_PAGE_OVERLAP_MIN_IOU: float = 0.15  #: 投影框与锚头像区重叠判定的 IoU 下限(框中心在头像区内也命中)


def read_character_grid(ctx: SrContext, image: MatLike) -> list[GridCell]:
    """角色列表 tab 的可见网格(4 列 × 可见 4 行;几何标定见模块 docstring)。

    ⚠️ 仅列表停驻位置与标定帧一致时可靠;滚动任意停驻(半格)用
    ``read_character_cells_by_level``(锚点驱动,位置无关)。"""
    area_rect = get_area_rect(ctx, '区域-角色网格')
    templates = iter_avatar_templates(ctx)
    cells: list[GridCell] = []
    if area_rect is None:
        return cells
    for row in range(_GRID_ROWS):
        for col in range(_GRID_COLS):
            x1 = area_rect.x1 + _GRID_CELL_X_OFF + col * _GRID_CELL_DX
            y1 = area_rect.y1 + _GRID_CELL_Y_OFF + row * _GRID_CELL_DY
            crop = image[y1:y1 + _GRID_CELL_H, x1:x1 + _GRID_CELL_W]
            cells.append(GridCell(row=row, col=col, guess=identify_crop(crop, templates)))
    return cells


def _match_page_characters(image: MatLike, area_rect: Rect,
                           templates: list[AvatarTemplate]) -> list[PageHit]:
    """整页多目标模板匹配(常量块注释的动机与边界)。

    对列表区大图提取一次特征,脸库逐模板做比值测试 + RANSAC 单应估计,
    模板四角投影得命中框,内点数过门槛才算命中。返回命中集(乱序;
    锚归属与冲突仲裁是调用方职责——同一卡位可能有多模板命中,按内点数取最高)。
    """
    page = image[area_rect.y1:area_rect.y2, area_rect.x1:area_rect.x2]
    page_kp, page_desc = cv2_utils.feature_detect_and_compute(page)
    matcher = cv2.BFMatcher()
    hits: list[PageHit] = []
    for entry in templates:
        tkp, tdesc = entry.info.features
        matches = matcher.knnMatch(tdesc, page_desc, k=2)
        good = []
        for pair in matches:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < _PAGE_RATIO_TEST * n.distance:
                good.append(m)
        if len(good) < 4:
            continue
        template_points = np.float32(
            [tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        source_points = np.float32(
            [page_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        homography, mask = cv2.findHomography(
            template_points, source_points, cv2.RANSAC, 5.0)
        if homography is None or mask is None:
            continue
        inliers = int(mask.sum())
        if inliers < _PAGE_MATCH_MIN_INLIERS:
            continue
        raw_w, raw_h = entry.info.raw.shape[1], entry.info.raw.shape[0]
        corners = np.float32(
            [[0, 0], [raw_w, 0], [raw_w, raw_h], [0, raw_h]]).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
        x1, y1 = projected.min(axis=0)
        x2, y2 = projected.max(axis=0)
        hits.append(PageHit(
            character=entry.character,
            template_id=entry.template_id,
            inliers=inliers,
            inlier_ratio=inliers / len(good),
            rect=Rect(int(area_rect.x1 + x1), int(area_rect.y1 + y1),
                      int(area_rect.x1 + x2), int(area_rect.y1 + y2))))
    return hits


def _guess_by_page_hits(page_hits: list[PageHit], avatar_rect: Rect) -> MemberGuess | None:
    """整页命中按头像区归属为单格结论;无重叠命中返回 None(调用方走裁片兜底)。

    归属判定:投影框中心落在头像区内,或与头像区 IoU 过门槛(投影框因模板
    与游戏渲染的缩放差可能略大于头像区,纯中心判定会漏贴合偏移的命中)。
    同位多模板按内点数降序取最高;仅一候选或 top1/top2 内点比过歧义门槛才给
    置信结论,否则候选诚实返回(char=None)。candidates 数值分量为内点率
    (0-1,与裁片路径的 SIFT 置信量纲不同,仅供排序与展示)。
    """
    cands: list[PageHit] = []
    for hit in page_hits:
        cx = (hit.rect.x1 + hit.rect.x2) / 2
        cy = (hit.rect.y1 + hit.rect.y2) / 2
        center_in = (avatar_rect.x1 <= cx <= avatar_rect.x2
                     and avatar_rect.y1 <= cy <= avatar_rect.y2)
        inter_w = min(hit.rect.x2, avatar_rect.x2) - max(hit.rect.x1, avatar_rect.x1)
        inter_h = min(hit.rect.y2, avatar_rect.y2) - max(hit.rect.y1, avatar_rect.y1)
        inter = max(0, inter_w) * max(0, inter_h)
        hit_area = (hit.rect.x2 - hit.rect.x1) * (hit.rect.y2 - hit.rect.y1)
        union = (hit_area
                 + (avatar_rect.x2 - avatar_rect.x1) * (avatar_rect.y2 - avatar_rect.y1)
                 - inter)
        iou = inter / union if union > 0 else 0.0
        if center_in or iou > _PAGE_OVERLAP_MIN_IOU:
            cands.append(hit)
    if not cands:
        return None
    cands.sort(key=lambda h: -h.inliers)
    if len(cands) >= 2:
        confident = cands[0].inliers / cands[1].inliers >= _PAGE_AMBIGUITY_RATIO
    else:
        confident = True
    return MemberGuess(
        char=cands[0].character.cn if confident else None,
        confident=confident,
        candidates=[(h.character.cn, round(h.inlier_ratio, 3)) for h in cands[:3]],
    )


def read_character_cells_by_level(ctx: SrContext, image: MatLike,
                                  screen_name: str = SCREEN_NAME) -> list[AnchorCell]:
    """等级文本锚驱动的角色列表识别(滚动停驻位置无关)。

    OCR 找列表区全部「等级」文本锚(每张卡下方一条「等级NN」),角色身份
    主路径 = 整页多目标模板匹配(见 ``_match_page_characters``):命中投影框
    与锚上方头像区重叠归属,同位多模板按内点数仲裁,歧义比不足则候选诚实
    返回;整页无命中的锚走锚上方裁片匹配兜底——模板特征贫乏的角色在整页
    比值测试下好匹配不足,小裁片环境可过 RANSAC。返回按 (y, x) 排序
    (自上而下、自左而右)。

    screen_name:识别哪屏的角色网格区(「区域-角色网格」area 须在该屏建档)。
    同构列表(如角色详情页的角色列表浮层)按屏独立建档后传屏名复用本识别;
    不传 = 逐光捡金编队屏(默认)。"""
    area_rect = get_area_rect(ctx, '区域-角色网格', screen_name=screen_name)
    templates = iter_avatar_templates(ctx)
    cells: list[AnchorCell] = []
    if area_rect is None:
        return cells
    results = ctx.ocr_service.get_ocr_result_list(image=image, rect=area_rect)
    page_hits = _match_page_characters(image, area_rect, templates)
    for r in results:
        if _LEVEL_ANCHOR_TEXT not in (r.data or ''):
            continue
        ax = r.x + _LEVEL_ANCHOR_DX
        ay = r.y + _LEVEL_ANCHOR_DY
        if (ax < 0 or ay < 0
                or ay + _LEVEL_ANCHOR_AVATAR_H > image.shape[0]
                or ax + _LEVEL_ANCHOR_AVATAR_W > image.shape[1]):
            continue  # 裁片出界跳过
        avatar_rect = Rect(ax, ay, ax + _LEVEL_ANCHOR_AVATAR_W, ay + _LEVEL_ANCHOR_AVATAR_H)
        guess = _guess_by_page_hits(page_hits, avatar_rect)
        if guess is None:
            crop = image[ay:ay + _LEVEL_ANCHOR_AVATAR_H, ax:ax + _LEVEL_ANCHOR_AVATAR_W]
            guess = identify_crop(crop, templates)
        cells.append(AnchorCell(
            center=Point(ax + _LEVEL_ANCHOR_AVATAR_W // 2,
                         ay + _LEVEL_ANCHOR_AVATAR_H // 2),
            guess=guess,
            rect=avatar_rect))
    cells.sort(key=lambda c: (c.center.y, c.center.x))
    return cells


def grid_cell_center(ctx: SrContext, row: int, col: int) -> Point | None:
    """角色网格单元格点击中心(1080p 全图坐标;区域缺失 None)。"""
    area_rect = get_area_rect(ctx, '区域-角色网格')
    if area_rect is None:
        return None
    x = area_rect.x1 + _GRID_CELL_X_OFF + col * _GRID_CELL_DX + _GRID_CELL_W // 2
    y = area_rect.y1 + _GRID_CELL_Y_OFF + row * _GRID_CELL_DY + _GRID_CELL_H // 2
    return Point(x, y)
