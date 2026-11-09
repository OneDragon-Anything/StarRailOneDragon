"""装备替换列表(光锥/遗器)画面识别器。

``analyze_screen`` 精准命中「光锥-替换」/「遗器-替换」后,按网格几何对列表
做结构化识别,把「每件装备的绑定信息」塞进 ``extras``:

- **占用者**(两类画面):逐格裁角标区做角色头像匹配(equip_owner_match)——
  列表卡右上角的圆形角标 = 装备者头像,与解包 avatarminiicon 同源同渲染;
- **遗器身份 + 等级**(仅遗器画面):192 件部件图解包模板批量 SIFT
  (``identify_cells``,截图特征一次 + 模板特征进程缓存)认出每格的件名
  (套装+部位唯一确定),逐格 OCR 等级徽章「+N」;
- **光锥身份**:卡面是斜置卡牌的中心裁剪构图,部件图同款 matchTemplate
  不可用,但 SIFT 定位可行(定位器已实证)——全库 170 件逐模板跑当前未
  集成(单屏增量 ~10s),光锥 extras 暂只有占用者;需要时按遗器同款方法接。

未列出格 = 空格 / 什么都识别不出(不猜测)。定位与装备某件走
``EquipLightConeOp`` / ``EquipRelicOp``(指定名称的 SIFT 全量清单)。

并发安全:recognize 纯读 —— 不写 ``self.``、不写任何全局;模板库与特征
缓存均为只读懒加载(幂等)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import cv2

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.mys.sr_relic_sets import PIECE_TO_SET, icon_webp_rel_path
from sr_od.operations.equip_owner_match import (
    _MIN_OWNER_SCORE,
    CONE_OWNER_SCORE,
    match_owner,
)
from sr_od.operations.grid_template_locate import (
    cone_grid_cells,
    identify_cells,
    load_template_gray,
    relic_col_centers,
    relic_grid_cells,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.geometry.point import Point
    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


class _EquipListRecognizerBase(ScreenRecognizer):
    """网格逐格占用者识别的公共实现;子类声明画面名 + 网格几何 + 角标偏移。"""

    extras_doc: dict[str, str] = {
        'items': '占用件清单 [{cell:[x,y], owner:角色id}],按格坐标排序;'
                 '只含有占用者识别的格 —— 未装备/空格/角色不在模板库的格不列出',
        'total_cells': '网格内可见格总数(含未装备/空格)',
        'hint': '卡片上无装备名称文本;定位与装备某件走 EquipLightConeOp/EquipRelicOp',
    }

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        """本画面的网格几何(格中心清单),几何实机标定值见 grid_template_locate。"""
        raise NotImplementedError

    def _badge_rect(self, cell: Point) -> Rect:
        """本画面的角标检测区(相对格中心的实测偏移)。"""
        raise NotImplementedError

    def _list_area_name(self) -> str:
        """本画面列表区 area 名(坐标单一真相源)。"""
        raise NotImplementedError

    def _owner_min_score(self) -> float:
        """角标匹配阈值(光锥界面角标更小,匹配天花板低 → 阈值单独放低)。"""
        raise NotImplementedError

    def recognize(
        self,
        ctx: OneDragonContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """网格逐格裁角标区跑角色头像匹配,返回占用件清单;列表区缺档返 None。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        items: list[dict] = []
        cells = self._grid_cells(list_area.rect)
        for cell in cells:
            owner, _score = match_owner(image, self._badge_rect(cell),
                                        min_score=self._owner_min_score())
            if owner is not None:
                items.append({'cell': [round(cell.x), round(cell.y)], 'owner': owner})
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cells': len(cells)}


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:9 列网格逐格占用者识别。"""

    screen_name = '光锥-替换'

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        return cone_grid_cells(list_rect)

    def _badge_rect(self, cell: Point) -> Rect:
        # 角标区偏移实测(光锥卡):格中心 +18/-83 ~ +78/-33
        return Rect(cell.x + 18, cell.y - 83, cell.x + 78, cell.y - 33)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _owner_min_score(self) -> float:
        return CONE_OWNER_SCORE


class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:4 列网格,每件 = 身份(件名) + 等级 + 占用者。"""

    screen_name = '遗器-替换'

    def _grid_cells(self, list_rect: Rect) -> list[Point]:
        return relic_grid_cells(list_rect)

    def _badge_rect(self, cell: Point) -> Rect:
        # 角标区偏移实测(遗器卡):格中心 +6/-63 ~ +61/-13
        return Rect(cell.x + 6, cell.y - 63, cell.x + 61, cell.y - 13)

    def _list_area_name(self) -> str:
        return '区域-遗器列表'

    def _owner_min_score(self) -> float:
        return _MIN_OWNER_SCORE

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """遗器列表完整绑定:每格 {件名, 等级, 占用者};全空格不列。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        cells = relic_grid_cells(list_area.rect)
        col_centers = relic_col_centers(list_area.rect)

        identity = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _relic_piece_templates(),
            list_area.rect, col_centers)
        identity_by_cell: dict[int, str] = {}
        for (kx, ky), name in identity.items():
            for idx, cell in enumerate(cells):
                if abs(kx - cell.x) <= 60 and abs(ky - cell.y) <= 45:
                    # 同格多命中(相邻模板)保留先到;不同格互不覆盖
                    identity_by_cell.setdefault(idx, name)
                    break

        items: list[dict] = []
        for idx, cell in enumerate(cells):
            owner, _score = match_owner(image, self._badge_rect(cell),
                                        min_score=self._owner_min_score())
            level = _read_level_badge(ctx, image, self._badge_level_rect(cell))
            piece = identity_by_cell.get(idx)
            if piece is None and owner is None and level is None:
                continue  # 空格(或全部识别失败,不猜测)
            items.append({'cell': [round(cell.x), round(cell.y)],
                          'piece': piece, 'level': level, 'owner': owner})
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cells': len(cells)}

    def _badge_level_rect(self, cell: Point) -> Rect:
        # 等级徽章「+N」区实测(遗器卡):格中心 -30/+46 ~ +32/+74
        return Rect(cell.x - 30, cell.y + 46, cell.x + 32, cell.y + 74)


#------------------- 遗器件名模板库(全量 192 件,进程级常驻) -------------------#

_relic_piece_template_cache: dict[str, MatLike] | None = None


def _relic_piece_templates() -> dict[str, MatLike]:
    """遗器件名 → 部件图灰度模板(全量;常驻以命中 identify_cells 的特征缓存)。"""
    global _relic_piece_template_cache
    if _relic_piece_template_cache is None:
        lib: dict[str, MatLike] = {}
        for piece_name, set_def in PIECE_TO_SET.items():
            template = load_template_gray(icon_webp_rel_path(set_def.set_id, piece_name))
            if template is not None:
                lib[piece_name] = template
        _relic_piece_template_cache = lib
    return _relic_piece_template_cache


_LEVEL_RE = re.compile(r'\+?\s*(\d{1,2})')


def _read_level_badge(ctx: SrContext, image: MatLike, badge_rect: Rect) -> int | None:
    """OCR 等级徽章「+N」(如 +15);读不到/非法返 None。"""
    area = ctx.ocr_service.get_ocr_result_list(
        image=image, rect=badge_rect, crop_first=True)
    for result in area:
        m = _LEVEL_RE.search(str(result.data))
        if m:
            level = int(m.group(1))
            if 0 <= level <= 15:
                return level
    return None
