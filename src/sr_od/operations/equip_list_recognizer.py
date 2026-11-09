"""装备替换列表(光锥/遗器)画面识别器:分层定位 + 分层识别。

``analyze_screen`` 精准命中「光锥-替换」/「遗器-替换」后,按「网格多目标识别
分层范式」识别(od-dev-write-operation 多目标特征识别节的通用范式,装备列表
实证):**定位与内容识别分层**。

**定位层**(每张卡在哪,滚动 / 命途分组头 / 空格天然免疫):
- 主锚:列表每卡底部的等级徽章文本(光锥「等级N」/ 遗器「+N」)OCR 命中位置;
- 补充:轮廓检测定位锚漏的卡(**不完整轮廓 = 不完整卡位**——滚动到边缘被
  裁切的卡没有等级文本锚,可见部分轮廓仍可检出),与锚点卡去重合并。

**内容识别层**(每张卡是什么),按确定性先验分层(替换列表每张有等级锚的卡
必是全库之一,空格已被定位层过滤 → 取匹配度最高即可,无需分数阈值):
- 主匹配:全库模板对**整屏**一次特征提取 + 逐模板匹配,命中簇中心落入卡矩形
  即归属(光锥 170 件图标 / 遗器 192 件部件图,模板特征进程级缓存);
- 降级匹配:主匹配未覆盖的卡 → **只取该卡区域内特征**对全库匹配取 argmax
  (整屏匹配的 Lowe 比值测试会被同框式斜置卡牌间的歧义竞争淘汰真匹配,
  格内局部匹配竞争者少,真匹配存活)。

**占用者**:逐卡裁角标区做角色头像匹配(equip_owner_match)——列表卡右上角
的圆形角标 = 装备者头像,与解包 avatarminiicon 同源同渲染。

卡片上无装备名称文本(名字只在选中后右侧详情出现)——定位与装备某件走
``EquipLightConeOp`` / ``EquipRelicOp``。并发安全:recognize 纯读,模板库
与特征缓存均为只读懒加载(幂等)。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils import cv2_utils
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
    detect_card_rects_contours,
    identify_cells,
    load_template_gray,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')

# 降级匹配的模板预缩放尺寸(实机列表渲染 ≈ 0.28-0.5 倍,同尺度匹配实测有效;
# 全尺寸模板在整屏/格内匹配均因描述子尺度差失败,2026-11-09 实验矩阵实证)
_FALLBACK_TEMPLATE_SIZE = (174, 204)
# 降级匹配的接受线(格内聚簇 good 数;晚安与睡颜实证 15,噪声本底 ≤7)
_FALLBACK_MIN_CLUSTER = 8

# 与锚点卡去重的 IoU 门槛(轮廓矩形与锚点矩形重叠过半视为同一卡)
_DEDUPE_IOU = 0.5


def _iou(a: Rect, b: Rect) -> float:
    ix = max(0, min(a.x2, b.x2) - max(a.x1, b.x1))
    iy = max(0, min(a.y2, b.y2) - max(a.y1, b.y1))
    inter = ix * iy
    union = a.x1 * 0 + (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
    return inter / union if union > 0 else 0.0


class _EquipListRecognizerBase(ScreenRecognizer):
    """分层定位 + 分层识别的公共实现;子类声明画面名 / 区域 / 阈值。"""

    extras_doc: dict[str, str] = {
        'items': '装备件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, owner:占用角色(中文名)}],'
                 '按卡位置排序;全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 轮廓补充)',
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

    def _locate_cards(self, ctx: SrContext, image: MatLike,
                      list_area) -> list[Rect]:
        """定位层:等级文本锚点 + 轮廓补充,去重合并(锚点优先)。"""
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        anchor_rects = detect_card_anchors(ocr_results, list_area.rect)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        contour_rects = detect_card_rects_contours(gray, list_area.rect)
        merged = list(anchor_rects)
        for c_rect in contour_rects:
            if all(_iou(c_rect, a) < _DEDUPE_IOU for a in anchor_rects):
                merged.append(c_rect)
        merged.sort(key=lambda r: (r.y1 // 100, r.x1))
        return merged, ocr_results

    def recognize(
        self,
        ctx: OneDragonContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """锚点+轮廓定位卡位 → 逐卡占用者识别;列表区缺档返 None。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, _ocr = self._locate_cards(ctx, image, list_area)

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
    """「光锥-替换」画面:分层定位 + 每件 = 光锥名/命途/等级/占用者。"""

    screen_name = '光锥-替换'

    extras_doc: dict[str, str] = {
        'items': '光锥件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, cone:光锥名, '
                 'path_cn:命途, level:光锥等级(1-80), owner:占用角色(中文名), '
                 'identity: full(主匹配)/fallback(降级匹配)/none}],按卡位置排序;'
                 '全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 轮廓补充)',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移实测(光锥卡):卡片矩形内右上角
        return Rect(card_rect.x1 + 88, card_rect.y1 - 5,
                    card_rect.x1 + 148, card_rect.y1 + 45)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _owner_min_score(self) -> float:
        return CONE_OWNER_SCORE

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """光锥列表完整绑定:每件 {光锥名, 命途, 等级, 占用者, 识别层级}。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, ocr_results = self._locate_cards(ctx, image, list_area)

        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _light_cone_templates(),
            list_area.rect)
        identity_by_card: dict[int, tuple[str, str]] = {}
        for ccx, ccy, votes, name in identity_hits:
            for idx, card_rect in enumerate(card_rects):
                center = card_rect.center
                if abs(ccx - center.x) <= 70 and abs(ccy - center.y) <= 78:
                    prev = identity_by_card.get(idx)
                    if prev is None or votes > prev[1]:
                        identity_by_card[idx] = (name, f'full({votes}票)')
                    break

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            level = self._read_level(ocr_results, card_rect)
            ident = identity_by_card.get(idx)
            cone_name, identity_src = (ident if ident else (None, 'none'))
            if cone_name is None:
                cone_name, confidence = _fallback_identity(
                    gray, card_rect, _light_cone_templates_scaled())
                if cone_name is not None:
                    identity_src = f'fallback({confidence}簇)'
            if cone_name is None and owner is None and level is None:
                continue  # 全部识别失败的卡,不猜测
            item = {'cell': [card_rect.x1, card_rect.y1,
                             card_rect.x2, card_rect.y2],
                    'cone': cone_name, 'level': level, 'owner': owner,
                    'identity': identity_src}
            if cone_name is not None:
                cone_def = LIGHT_CONE_BY_NAME[cone_name]
                item['path_cn'] = next((p.cn for p in CHARACTER_PATH_LIST
                                        if p.id == cone_def.path_id), None)
            items.append(item)
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cards': len(card_rects)}

    def _read_level(self, ocr_results: list, card_rect: Rect) -> int | None:
        """从锚点 OCR 结果解析本卡的等级「等级N」(1-80)。"""
        for r in ocr_results:
            text = str(r.data).strip()
            if not text.startswith('等级'):
                continue
            rect = r.rect
            if rect.center.y > card_rect.y2 or rect.center.y < card_rect.y2 - 60:
                continue
            if abs(rect.center.x - card_rect.center.x) > 70:
                continue
            m = _LEVEL_VALUE_RE.search(text)
            if m:
                level = int(m.group(1))
                if 1 <= level <= 80:
                    return level
        return None


class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:分层定位 + 每件 = 件名/套装/部位/强化等级/占用者。"""

    screen_name = '遗器-替换'

    extras_doc: dict[str, str] = {
        'items': '遗器件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, piece:单件名, '
                 'set:套装名, pos_cn:部位, level:强化等级(0-15), '
                 'owner:占用角色(中文名), identity: full/fallback}],'
                 '按卡位置排序;全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 轮廓补充)',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移实测(遗器卡):卡片矩形内右上角
        return Rect(card_rect.x2 - 55, card_rect.y1 + 17,
                    card_rect.x2, card_rect.y1 + 67)

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
        card_rects, ocr_results = self._locate_cards(ctx, image, list_area)

        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _relic_piece_templates(),
            list_area.rect)
        identity_by_card: dict[int, tuple[str, str]] = {}
        for ccx, ccy, votes, name in identity_hits:
            for idx, card_rect in enumerate(card_rects):
                center = card_rect.center
                if abs(ccx - center.x) <= 60 and abs(ccy - center.y) <= 60:
                    prev = identity_by_card.get(idx)
                    if prev is None or votes > prev[1]:
                        identity_by_card[idx] = (name, f'full({votes}票)')
                    break

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            level = self._read_level(ocr_results, card_rect)
            ident = identity_by_card.get(idx)
            piece_name, identity_src = (ident if ident else (None, 'none'))
            if piece_name is None:
                piece_name, confidence = _fallback_identity(
                    gray, card_rect, _relic_piece_templates_scaled())
                if piece_name is not None:
                    identity_src = f'fallback({confidence}簇)'
            if piece_name is None and owner is None and level is None:
                continue  # 全部识别失败的卡,不猜测
            item = {'cell': [card_rect.x1, card_rect.y1,
                             card_rect.x2, card_rect.y2],
                    'piece': piece_name, 'level': level, 'owner': owner,
                    'identity': identity_src}
            if piece_name is not None:
                set_def = PIECE_TO_SET[piece_name]
                pos = next(p.pos for p in set_def.pieces if p.name == piece_name)
                item['set'] = set_def.set_name
                item['pos_cn'] = RELIC_POS_CN[pos]
            items.append(item)
        items.sort(key=lambda item: (item['cell'][1], item['cell'][0]))
        return {'items': items, 'total_cards': len(card_rects)}

    def _read_level(self, ocr_results: list, card_rect: Rect) -> int | None:
        """从锚点 OCR 结果解析本卡的强化等级「+N」(0-15)。"""
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


#------------------- 模板库(全量,进程级常驻) -------------------#

_light_cone_template_cache: dict[str, MatLike] | None = None
_light_cone_scaled_cache: dict[str, np.ndarray] | None = None
_relic_piece_template_cache: dict[str, MatLike] | None = None
_relic_piece_scaled_cache: dict[str, np.ndarray] | None = None


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


def _light_cone_templates_scaled() -> dict[str, np.ndarray]:
    """光锥名 → 预缩放灰度模板(降级匹配用,与实机列表渲染同尺度)。"""
    global _light_cone_scaled_cache
    if _light_cone_scaled_cache is None:
        _light_cone_scaled_cache = {
            name: cv2.resize(t, _FALLBACK_TEMPLATE_SIZE)
            for name, t in _light_cone_templates().items()}
    return _light_cone_scaled_cache


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


def _relic_piece_templates_scaled() -> dict[str, np.ndarray]:
    """遗器件名 → 预缩放灰度模板(降级匹配用)。"""
    global _relic_piece_scaled_cache
    if _relic_piece_scaled_cache is None:
        _relic_piece_scaled_cache = {
            name: cv2.resize(t, _FALLBACK_TEMPLATE_SIZE)
            for name, t in _relic_piece_templates().items()}
    return _relic_piece_scaled_cache


def _fallback_identity(gray: np.ndarray, card_rect: Rect,
                       scaled_templates: dict[str, np.ndarray]) -> tuple[str | None, int]:
    """降级匹配:只取该卡区域内特征,对全库模板匹配取聚簇最大者(argmax,无阈值)。

    整屏匹配的 Lowe 比值测试在同框式斜置卡牌间存在歧义竞争,真匹配被淘汰;
    格内局部匹配竞争者少,真匹配存活(晚安与睡颜实证:整屏 2 票 vs 格内 15 聚簇)。
    返回 (光锥名/件名, 聚簇 good 数);全库均无 ≥_FALLBACK_MIN_CLUSTER 的聚簇
    返 (None, 0)。
    """
    zone = gray[card_rect.y1:card_rect.y2, card_rect.x1:card_rect.x2]
    z_kp, z_desc = cv2_utils.feature_detect_and_compute(zone)
    if z_desc is None or len(z_kp) == 0:
        return None, 0
    bf = cv2.BFMatcher()
    best_name: str | None = None
    best_cluster = 0
    for name, t_s in scaled_templates.items():
        t_kp, t_desc = cv2_utils.feature_detect_and_compute(t_s)
        if t_desc is None:
            continue
        matches = bf.knnMatch(t_desc, z_desc, k=2)
        good_pts = [z_kp[m.trainIdx].pt for p in matches if len(p) == 2
                    and (m := p[0]) and m.distance < 0.75 * p[1].distance]
        if len(good_pts) < _FALLBACK_MIN_CLUSTER:
            continue
        # 聚簇:60px 半径内最大友好数(真命中聚在卡牌同位,误配分散)
        pts = np.float32(good_pts)
        cluster = 0
        for i in range(len(pts)):
            cluster = max(cluster, int((np.abs(pts - pts[i]).max(axis=1) < 60).sum()))
        if cluster > best_cluster:
            best_name, best_cluster = name, cluster
    if best_cluster < _FALLBACK_MIN_CLUSTER:
        return None, best_cluster
    return best_name, best_cluster
