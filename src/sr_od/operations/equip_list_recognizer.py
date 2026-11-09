"""装备替换列表(光锥/遗器)画面识别器:等级文本锚点定位 + 逐卡绑定识别。

``analyze_screen`` 精准命中「光锥-替换」/「遗器-替换」后,按**等级文本锚点**
定位每张卡(替换列表每卡底部都有等级徽章文本:光锥「等级N」/ 遗器「+N」),
对每张卡识别完整绑定信息塞进 ``extras``:

- **占用者**:逐卡裁角标区做角色头像匹配(equip_owner_match)——列表卡右上角
  的圆形角标 = 装备者头像,与解包 avatarminiicon 同源同渲染;
- **光锥身份**(仅光锥画面):170 件解包图标全库 SIFT(identify_cells,截图特征
  一次 + 模板特征进程缓存),命中簇中心落入哪张卡矩形即归属哪卡;
- **遗器身份**(仅遗器画面):192 件部件图同款批量 SIFT;
- **等级**:锚点文本自身解析(「等级80」→ 80 /「+15」→ 15),无需二次 OCR。

**锚点定位 vs 固定网格**:列表可滚动,命途分组头插入会使固定行带错位——
锚点法每屏实时 OCR,滚动 / 分组 / 空格天然免疫。卡片上无装备名称文本
(名字只在选中后右侧详情出现)——定位与装备某件走 ``EquipLightConeOp`` /
``EquipRelicOp``(指定名称的 SIFT 全量清单)。

未列出的卡 = 全部识别失败(不猜测)。并发安全:recognize 纯读,模板库与
特征缓存均为只读懒加载(幂等)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import cv2

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.config.character_const import CHARACTER_PATH_LIST
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_light_cones import LIGHT_CONE_BY_NAME
from sr_od.mys.sr_light_cones import icon_webp_rel_path as cone_icon_rel_path
from sr_od.mys.sr_relic_sets import PIECE_TO_SET, icon_webp_rel_path
from sr_od.operations.equip_owner_match import (
    _MIN_OWNER_SCORE,
    CONE_OWNER_SCORE,
    match_owner,
)
from sr_od.operations.grid_template_locate import (
    detect_card_anchors,
    identify_cells,
    load_template_gray,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')


class _EquipListRecognizerBase(ScreenRecognizer):
    """等级文本锚点定位 + 逐卡绑定识别的公共实现。"""

    extras_doc: dict[str, str] = {
        'items': '装备件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, owner:占用角色(中文名)}],'
                 '按卡位置排序;全部识别失败的卡不列',
        'total_cards': '锚点定位到的卡总数',
        'hint': '卡片上不印装备名称(名字只在选中后右侧详情出现)——身份与占用者'
                '均靠图像匹配识别;定位与装备某件走 EquipLightConeOp/EquipRelicOp',
    }

    def _list_area_name(self) -> str:
        """本画面列表区 area 名(坐标单一真相源)。"""
        raise NotImplementedError

    def _owner_min_score(self) -> float:
        """角标匹配阈值(光锥界面角标更小,匹配天花板低 → 阈值单独放低)。"""
        raise NotImplementedError

    def _badge_rect(self, card_rect: Rect) -> Rect:
        """角标检测区(卡片矩形内右上角,偏移实测)。"""
        raise NotImplementedError

    def recognize(
        self,
        ctx: OneDragonContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """锚点定位卡位 → 逐卡占用者识别;列表区缺档返 None。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        card_rects = detect_card_anchors(ocr_results, list_area.rect)

        items: list[dict] = []
        for card_rect in card_rects:
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            if owner is None:
                continue
            items.append({'cell': [card_rect.x1, card_rect.y1,
                                   card_rect.x2, card_rect.y2], 'owner': owner})
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cards': len(card_rects)}


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:锚点定位 + 每件 = 光锥名/命途/等级/占用者。"""

    screen_name = '光锥-替换'

    extras_doc: dict[str, str] = {
        'items': '光锥件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, cone:光锥名, '
                 'path_cn:命途, level:光锥等级(1-80), owner:占用角色(中文名)}],'
                 '按卡位置排序;全部识别失败的卡不列',
        'total_cards': '锚点定位到的卡总数',
    }

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _owner_min_score(self) -> float:
        return CONE_OWNER_SCORE

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移实测(光锥卡):卡片矩形内右上角
        return Rect(cell_rect_x1(card_rect) + 88, card_rect.y1 - 5,
                    cell_rect_x1(card_rect) + 148, card_rect.y1 + 45)

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """光锥列表完整绑定:每件 {光锥名, 命途, 等级, 占用者}。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        card_rects = detect_card_anchors(ocr_results, list_area.rect)

        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _light_cone_templates(),
            list_area.rect)
        # 命中簇中心落入哪张卡矩形即归属哪卡(位置由匹配自身给出)
        identity_by_card: dict[int, tuple[int, str]] = {}
        for ccx, ccy, votes, name in identity_hits:
            for idx, card_rect in enumerate(card_rects):
                center = card_rect.center
                if abs(ccx - center.x) <= 70 and abs(ccy - center.y) <= 78:
                    prev = identity_by_card.get(idx)
                    if prev is None or votes > prev[0]:
                        identity_by_card[idx] = (votes, name)
                    break

        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            level, cone = None, identity_by_card.get(idx)
            cone_name = cone[1] if cone else None
            for r in ocr_results:
                rect = r.rect
                text = str(r.data).strip()
                if rect.center.y > card_rect.y2 or rect.center.y < card_rect.y2 - 60:
                    continue
                if abs(rect.center.x - card_rect.center.x) > 70:
                    continue
                m = _LEVEL_VALUE_RE.search(text)
                if m and text.startswith('等级'):
                    level = int(m.group(1))
                    break
            if cone_name is None and owner is None and level is None:
                continue  # 全部识别失败的卡,不猜测
            item = {'cell': [card_rect.x1, card_rect.y1,
                             card_rect.x2, card_rect.y2],
                    'cone': cone_name, 'level': level, 'owner': owner}
            if cone_name is not None:
                cone_def = LIGHT_CONE_BY_NAME[cone_name]
                item['path_cn'] = next((p.cn for p in CHARACTER_PATH_LIST
                                        if p.id == cone_def.path_id), None)
            items.append(item)
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cards': len(card_rects)}


class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:锚点定位 + 每件 = 件名/套装/部位/强化等级/占用者。"""

    screen_name = '遗器-替换'

    extras_doc: dict[str, str] = {
        'items': '遗器件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, piece:单件名, '
                 'set:套装名, pos_cn:部位, level:强化等级(0-15), '
                 'owner:占用角色(中文名)}],按卡位置排序;全部识别失败的卡不列',
        'total_cards': '锚点定位到的卡总数',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移实测(遗器卡):卡片矩形内右上角
        return Rect(cell_rect_x2(card_rect) - 55, card_rect.y1 + 17,
                    cell_rect_x2(card_rect), card_rect.y1 + 67)

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
        """遗器列表完整绑定:每件 {件名, 套装, 部位, 强化等级, 占用者}。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        card_rects = detect_card_anchors(ocr_results, list_area.rect)

        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _relic_piece_templates(),
            list_area.rect)
        identity_by_card: dict[int, str] = {}
        for ccx, ccy, _votes, name in identity_hits:
            for idx, card_rect in enumerate(card_rects):
                center = card_rect.center
                if abs(ccx - center.x) <= 60 and abs(ccy - center.y) <= 60:
                    identity_by_card.setdefault(idx, name)
                    break

        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            level = _read_relic_level(ocr_results, card_rect)
            piece = identity_by_card.get(idx)
            if piece is None and owner is None and level is None:
                continue  # 全部识别失败的卡,不猜测
            item = {'cell': [card_rect.x1, card_rect.y1,
                             card_rect.x2, card_rect.y2],
                    'piece': piece, 'level': level, 'owner': owner}
            if piece is not None:
                set_def = PIECE_TO_SET[piece]
                pos = next(p.pos for p in set_def.pieces if p.name == piece)
                item['set'] = set_def.set_name
                item['pos_cn'] = RELIC_POS_CN[pos]
            items.append(item)
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cards': len(card_rects)}

    def _level_rect(self, card_rect: Rect) -> Rect:
        """强化等级「+N」文本过滤区(卡片矩形内底部)。"""
        return Rect(card_rect.center.x - 45, card_rect.y2 - 40,
                    card_rect.center.x + 45, card_rect.y2 - 4)


#------------------- 光锥/遗器模板库(全量,进程级常驻) -------------------#

_light_cone_template_cache: dict[str, MatLike] | None = None


def _light_cone_templates() -> dict[str, MatLike]:
    """光锥名 → 解包图标灰度模板(全量;常驻以命中 identify_cells 的特征缓存)。"""
    global _light_cone_template_cache
    if _light_cone_template_cache is None:
        lib: dict[str, MatLike] = {}
        for cone_name, cone_def in LIGHT_CONE_BY_NAME.items():
            template = load_template_gray(cone_icon_rel_path(cone_def.tid))
            if template is not None:
                lib[cone_name] = template
        _light_cone_template_cache = lib
    return _light_cone_template_cache


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


_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')


def _read_relic_level(ocr_results: list, card_rect: Rect) -> int | None:
    """从锚点 OCR 结果解析本卡的强化等级「+N」(0-15);读不到返 None。"""
    for r in ocr_results:
        text = str(r.data).strip()
        if not text.startswith('+'):
            continue
        rect = r.rect
        if rect.center.y > card_rect.y2 or rect.center.y < card_rect.y2 - 40:
            continue
        if abs(rect.center.x - card_rect.center.x) > 45:
            continue
        m = _LEVEL_VALUE_RE.search(text)
        if m:
            level = int(m.group(1))
            if 0 <= level <= 15:
                return level
    return None


def cell_rect_x1(rect: Rect) -> float:
    return rect.x1


def cell_rect_x2(rect: Rect) -> float:
    return rect.x2
