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

每格 ``cell`` = 卡片矩形 [x1,y1,x2,y2](1080p,可直接用于点击/裁图/可视化)。
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
from sr_od.mys.sr_codes import RELIC_POS_CN
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

    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


class _EquipListRecognizerBase(ScreenRecognizer):
    """网格逐格占用者识别的公共实现;子类声明画面名 + 网格几何 + 角标偏移。"""

    extras_doc: dict[str, str] = {
        'items': '占用件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, owner:角色id}],'
                 '按格坐标排序;只含有占用者识别的格 —— 未装备/空格/角色不在'
                 '模板库的格不列出',
        'total_cells': '网格内可见格总数(含未装备/空格)',
        'hint': '卡片上无装备名称文本;定位与装备某件走 EquipLightConeOp/EquipRelicOp',
    }

    def _grid_cells(self, list_rect: Rect) -> list[Rect]:
        """本画面的网格几何(每格卡片矩形),实机标定值见 grid_template_locate。"""
        raise NotImplementedError

    def _badge_rect(self, cell_rect: Rect) -> Rect:
        """本画面的角标检测区(由卡片矩形换算,偏移实测)。"""
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
        cell_rects = self._grid_cells(list_area.rect)
        items: list[dict] = []
        for cell_rect in cell_rects:
            owner, _score = match_owner(image, self._badge_rect(cell_rect),
                                        min_score=self._owner_min_score())
            if owner is not None:
                items.append({'cell': [cell_rect.x1, cell_rect.y1,
                                       cell_rect.x2, cell_rect.y2], 'owner': owner})
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cells': len(cell_rects)}


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:9 列网格逐格占用者识别。"""

    screen_name = '光锥-替换'

    def _grid_cells(self, list_rect: Rect) -> list[Rect]:
        return cone_grid_cells(list_rect)

    def _badge_rect(self, cell_rect: Rect) -> Rect:
        # 角标区偏移实测(光锥卡):卡片矩形内右上角
        return Rect(cell_rect.x1 + 88, cell_rect.y1 - 5,
                    cell_rect.x1 + 148, cell_rect.y1 + 45)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _owner_min_score(self) -> float:
        return CONE_OWNER_SCORE


class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:4 列网格,每件 = 身份(件名) + 等级 + 占用者。"""

    screen_name = '遗器-替换'

    extras_doc: dict[str, str] = {
        'items': '遗器件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, piece:单件名, '
                 'set:套装名, pos_cn:部位, level:强化等级, owner:占用角色id}],'
                 '按格坐标排序;空格/全识别失败的格不列',
        'total_cells': '网格内可见格总数(含未装备/空格)',
    }

    def _grid_cells(self, list_rect: Rect) -> list[Rect]:
        return relic_grid_cells(list_rect)

    def _badge_rect(self, cell_rect: Rect) -> Rect:
        # 角标区偏移实测(遗器卡):卡片矩形内右上角
        return Rect(cell_rect.x2 - 55, cell_rect.y1 + 17,
                    cell_rect.x2, cell_rect.y1 + 67)

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
        """遗器列表完整绑定:每格 {件名, 套装, 部位, 等级, 占用者};全空格不列。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        cells = relic_grid_cells(list_area.rect)
        col_centers = relic_col_centers(list_area.rect)

        identity = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _relic_piece_templates(),
            list_area.rect, col_centers)
        identity_by_cell: dict[int, str] = {}
        for (kx, ky), name in identity.items():
            for idx, cell_rect in enumerate(cells):
                center = cell_rect.center
                if abs(kx - center.x) <= 60 and abs(ky - center.y) <= 45:
                    # 同格多命中(相邻模板)保留先到;不同格互不覆盖
                    identity_by_cell.setdefault(idx, name)
                    break

        items: list[dict] = []
        for idx, cell_rect in enumerate(cells):
            owner, _score = match_owner(image, self._badge_rect(cell_rect),
                                        min_score=self._owner_min_score())
            level = _read_level_badge(ctx, image, self._level_rect(cell_rect))
            piece = identity_by_cell.get(idx)
            if piece is None and owner is None and level is None:
                continue  # 空格(或全部识别失败,不猜测)
            item = {'cell': [cell_rect.x1, cell_rect.y1,
                             cell_rect.x2, cell_rect.y2],
                    'piece': piece, 'level': level, 'owner': owner}
            if piece is not None:
                set_def = PIECE_TO_SET[piece]
                pos = next(p.pos for p in set_def.pieces if p.name == piece)
                item['set'] = set_def.set_name
                item['pos_cn'] = RELIC_POS_CN[pos]
            items.append(item)
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cells': len(cells)}

    def _level_rect(self, cell_rect: Rect) -> Rect:
        # 等级徽章「+N」区实测(遗器卡):卡片矩形内底部中央
        return Rect(cell_rect.center.x - 30, cell_rect.y2 - 35,
                    cell_rect.center.x + 32, cell_rect.y2 - 7)


#------------------- 遗器件名模板库(全量 192 件,进程级常驻) -------------------#

_relic_piece_template_cache: dict[str, MatLike] | None = None


def _relic_piece_templates() -> dict[str, MatLike]:
    """遗器件名 → 部件图灰度模板(全量;常驻以命中 identify_cells 的特征缓存)。"""
    global _relic_piece_template_cache
    if _relic_piece_template_cache is None:
        lib: dict[str, MatLike] = {}
        for piece_name, set_def in PIECE_TO_SET.items():
            piece = next((p for p in set_def.pieces if p.name == piece_name), None)
            if piece is None:
                continue
            template = load_template_gray(icon_webp_rel_path(set_def.set_id, piece.pos))
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
