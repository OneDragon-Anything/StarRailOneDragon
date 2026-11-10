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
的圆形角标 = 装备者头像,与游戏内列表角标渲染同源。

卡片上无装备名称文本(名字只在选中后右侧详情出现)——定位与装备某件走
``EquipLightConeOp`` / ``EquipRelicOp``。并发安全:recognize 纯读,模板库
与特征缓存均为只读懒加载(幂等)。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import CHARACTER_PATH_LIST
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_light_cones import LIGHT_CONE_BY_NAME
from sr_od.mys.sr_light_cones import icon_webp_rel_path as cone_icon_rel_path
from sr_od.mys.sr_relic_sets import PIECE_TO_SET, icon_webp_rel_path
from sr_od.operations.equip_owner_match import (
    _MIN_OWNER_SCORE,
    LIGHT_CONE_OWNER_SCORE,
    match_owner,
)
from sr_od.operations.grid_template_locate import (
    _cached_template_features,
    detect_card_anchors,
    detect_card_rects_contours,
    identify_cells,
    load_template_gray,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')

# 降级匹配的模板预缩放尺寸(实机列表渲染 ≈ 0.28-0.5 倍,同尺度匹配实测有效;
# 全尺寸模板在整屏/格内匹配均因描述子尺度差失败,多方案对比实验实证)
_FALLBACK_TEMPLATE_SIZE = (174, 204)

# 与锚点卡去重的 IoU 门槛(轮廓矩形与锚点矩形重叠过半视为同一卡)
_DEDUPE_IOU = 0.5

# 轮廓补充卡的网格吸附半径:中心 x 距列中心 / 中心 y 距锚点行带(卡中心)的
# 最大偏差。实机验证:网格间隙纹理被 Canny 检出的伪矩形(如 122×113 的间隙
# 框)中心落在列与列之间(偏差 ≥31px),真卡(含 OCR 漏锚卡)中心与网格交点
# 偏差 ≤17px —— 以此区分,不吸附且不贴列表边缘的轮廓矩形丢弃。
_CONTOUR_COL_SNAP_PX = 28
_CONTOUR_ROW_SNAP_PX = 70

# 部位筛选 tab(遗器-替换顶部):area 名 → 部位号。tab 为纯图标位无文字,
# 选中态 = 图标提亮 + 底部白色横线指示器(与 SrRelicPieceDef.pos 同坐标系)
_POS_TAB_AREAS: tuple[tuple[str, int], ...] = (
    ('部位TAB-头部', 1), ('部位TAB-手部', 2), ('部位TAB-躯干', 3),
    ('部位TAB-腿部', 4), ('部位TAB-位面球', 5), ('部位TAB-连结绳', 6),
)
# 白条判据阈值:横线像素(区域底部 8 行内灰度>180)实机选中格 28px、未选中
# 全 0 —— ≥10px 判选中,低于则判不出退全库(不劣于无先验路径)
_TAB_BAR_MIN_PX: int = 10


def _iou(a: Rect, b: Rect) -> float:
    ix = max(0, min(a.x2, b.x2) - max(a.x1, b.x1))
    iy = max(0, min(a.y2, b.y2) - max(a.y1, b.y1))
    inter = ix * iy
    union = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
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

    def _col_centers(self, list_rect: Rect) -> list[float]:
        """固定列中心 x 列表(行列解耦定位的列先验,列距按实机标定)。"""
        raise NotImplementedError

    def _owner_min_score(self) -> float:
        """角标匹配阈值(光锥界面角标更小,匹配天花板低 → 阈值单独放低)。"""
        raise NotImplementedError

    def _badge_rect(self, card_rect: Rect) -> Rect:
        """角标检测区(卡片矩形内右上角,偏移实测)。"""
        raise NotImplementedError

    def _locate_cards(self, ctx: SrContext, image: MatLike,
                      list_area) -> tuple[list[Rect], list, MatLike]:
        """定位层:等级文本锚点 + 轮廓补充,去重合并后按网格吸附过滤。

        轮廓补充的误检源实机实证:网格间隙的装饰底纹会形成闭合轮廓,矩形
        尺寸恰好落进卡尺寸窗,但中心不落在任何网格交点上;真卡(含 OCR 漏
        锚卡)中心必与「列中心 × 锚点行带」交点吻合。过滤规则:与锚点卡
        同列同行 → 保留(锚点漏读的真卡);贴列表上下边缘 → 保留(滚动
        裁切卡,无完整网格交点);其余丢弃。

        :return: (卡矩形清单, 全图 OCR 结果, 列表灰度图)——灰度图供识别层
            复用,避免整帧 cvtColor 重复计算。
        """
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        anchor_rects = detect_card_anchors(ocr_results, list_area.rect, self._col_centers(list_area.rect))
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        contour_rects = detect_card_rects_contours(gray, list_area.rect)
        merged = list(anchor_rects)
        for c_rect in contour_rects:
            if all(_iou(c_rect, a) < _DEDUPE_IOU for a in anchor_rects):
                merged.append(c_rect)
        merged = self._filter_contour_offgrid(merged, anchor_rects, list_area.rect)
        merged.sort(key=lambda r: (r.y1 // 100, r.x1))
        return merged, ocr_results, gray

    def _filter_contour_offgrid(self, merged: list[Rect],
                                anchor_rects: list[Rect], list_rect: Rect) -> list[Rect]:
        """丢弃不吸附锚点网格、也不贴列表边缘的轮廓误检矩形。

        锚点卡(行列解耦换算)天然在网格上,原样保留;仅对轮廓补充卡校验:
        中心 x 吸附列中心(固定列先验)、中心 y 与某锚点卡中心同行带,两者
        同时成立视为网格上的真卡(锚点 OCR 漏读场景);贴列表上下边缘的
        轮廓卡是滚动裁切卡(无完整网格交点),保留。
        """
        col_centers = self._col_centers(list_rect)
        kept: list[Rect] = []
        anchor_set = {id(a) for a in anchor_rects}
        for rect in merged:
            if id(rect) in anchor_set or len(anchor_rects) == 0:
                kept.append(rect)
                continue
            cx, cy = (rect.x1 + rect.x2) / 2, (rect.y1 + rect.y2) / 2
            col_ok = min(abs(cx - c) for c in col_centers) <= _CONTOUR_COL_SNAP_PX
            if not col_ok:
                # 列吸附是硬条件:真卡(含滚动裁切卡)x 方向必在列上;网格间隙
                # 纹理矩形顶到列表上边缘也不在列上(实机 476 中心 vs 列 429 实证)
                continue
            clipped_by_edge = (rect.y1 <= list_rect.y1 + 5
                               or rect.y2 >= list_rect.y2 - 5)
            if clipped_by_edge:
                kept.append(rect)  # 裁切卡只豁免行检查(y 被截断,x 仍在列上)
                continue
            row_ok = min(abs(cy - (a.y1 + a.y2) / 2) for a in anchor_rects) <= _CONTOUR_ROW_SNAP_PX
            if row_ok:
                kept.append(rect)
        return kept


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:分层定位 + 每件 = 光锥名/命途/等级/占用者/叠影。"""

    screen_name = '光锥-替换'

    extras_doc: dict[str, str] = {
        'items': '光锥件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, cone:光锥名(全库 argmax), '
                 'path_cn:命途, level:光锥等级(1-80), owner:占用角色(中文名), '
                 'rank:叠影数(1-5,罗马数字标识别,判不出为 null), '
                 'identity: full(N票=整屏主匹配)/fallback(N簇=格内聚簇强度,低簇=低置信,'
                 '可与同款兄弟格对照复核)}],按卡位置排序;'
                 '全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 轮廓补充)',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移实测(光锥卡):卡片矩形内右上角
        return Rect(card_rect.x1 + 88, card_rect.y1 - 5,
                    card_rect.x1 + 148, card_rect.y1 + 45)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _col_centers(self, list_rect: Rect) -> list[float]:
        """9 列中心:首卡中心 x1+72.5 起步、列距恒 139px(锚点卡实测)。"""
        return [list_rect.x1 + 72.5 + 139 * i for i in range(9)]

    def _owner_min_score(self) -> float:
        return LIGHT_CONE_OWNER_SCORE

    def _read_superimpose(self, image: MatLike, card_rect: Rect) -> int | None:
        """卡左缘叠影圆标 → 叠影数(1-5);无法判定返回 None。

        叠影圆相对卡原点位置恒定(实机标定 +6,+48 起 34×34)——同位
        裁窗与分档整圆 ROI 模板(assets/template/light_cone_superimpose/
        <叠影数>_<序号>.png)直接 TM_CCOEFF_NORMED 匹配取最高分档,≥0.6 判定。
        模板按配色态分文件(亮金底黑字 / 暗底金字同档相关系数为负,必须分模板)。
        III/IV 档候实机采样补档,当前该两档判 None。"""
        templates = _superimpose_templates()
        if not templates:
            return None
        roi = cv2.cvtColor(
            image[card_rect.y1 + 48:card_rect.y1 + 82,
                  card_rect.x1 + 6:card_rect.x1 + 40], cv2.COLOR_RGB2GRAY)
        best_rank, best_score = None, 0.0
        for rank, tpl_list in templates.items():
            for tpl in tpl_list:
                score = float(cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)[0][0])
                if score > best_score:
                    best_rank, best_score = rank, score
        if best_score < _SUPERIMPOSE_MATCH_MIN:
            return None
        return best_rank

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """光锥列表完整绑定:每件 {光锥名, 命途, 等级, 占用者, 识别层级}。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, ocr_results, gray = self._locate_cards(ctx, image, list_area)

        anchor_cx = [r.center.x for r in card_rects]
        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), _light_cone_templates(),
            list_area.rect, anchor_cx=anchor_cx)
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
            level = self._read_level(ocr_results, card_rect)
            rank = self._read_superimpose(image, card_rect)
            ident = identity_by_card.get(idx)
            cone_name, identity_src = ((ident[1], f'full({ident[0]}票)') if ident else (None, 'none'))
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
                    'rank': rank, 'identity': identity_src}
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
                 'owner:占用角色(中文名), identity: full(N票)/fallback(N簇)/masked'
                 '(重掷动画遮罩卡,身份不判)/none}],按卡位置排序;'
                 '全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 网格吸附过滤后的轮廓补充)',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区偏移(遗器卡实机霍夫圆实测):头像圆心 ≈ (x2-19, y1+34)、直径
        # 35-37px,圆右缘超出卡右缘 ~1px —— 检测窗右缘外扩 6px 保证完整圆,
        # 否则圆被裁缺角、matchTemplate 分数从 0.81 跌到 0.47(全灭实证)
        return Rect(card_rect.x2 - 55, card_rect.y1 + 10,
                    card_rect.x2 + 6, card_rect.y1 + 62)

    def _list_area_name(self) -> str:
        return '区域-遗器列表'

    def _col_centers(self, list_rect: Rect) -> list[float]:
        """4 列中心:列表区 x1+66 起步、列距 123px(实机亮度剖面实测
        列中心 99/224/346/469;与 EquipRelicOp/grid_template_locate 同源)。"""
        return [list_rect.x1 + 66 + 123 * i for i in range(4)]

    def _owner_min_score(self) -> float:
        return _MIN_OWNER_SCORE

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,
    ) -> dict | None:
        """遗器列表完整绑定:每件 {件名, 套装, 部位, 强化等级, 占用者}。

        部位先验自读:顶部筛选 tab 的选中态白条指示器可判时,候选收缩到
        单部位(替换界面列表恒按选中部位筛选);判不出退全库,不劣于旧路径。"""
        pos = self._detect_pos_from_tabs(ctx, image)
        if pos is not None:
            return self._recognize(ctx, image,
                                   _relic_piece_templates_for_pos(pos),
                                   _relic_piece_templates_scaled_for_pos(pos))
        return self._recognize(ctx, image,
                               _relic_piece_templates(), _relic_piece_templates_scaled())

    def _detect_pos_from_tabs(self, ctx: SrContext, image: MatLike) -> int | None:
        """读顶部部位筛选 tab 的选中态 → 部位号;判不出返回 None(退全库)。

        选中态判据(实机实测,当前筛选=头部帧):tab 为纯图标位(无文字),
        选中 = 图标提亮 + **底部白色横线指示器**——横线像素(区域底部 8 行内
        灰度>180)选中格 28px、未选中格全 0,白条 ≥10px 判选中;取白条最多的
        tab。画面与建档不符(全 0)时诚实返回 None。"""
        best_pos, best_bar = None, 0
        for area_name, pos in _POS_TAB_AREAS:
            area = ctx.screen_loader.get_area(self.screen_name, area_name)
            rect = area.rect
            roi = cv2.cvtColor(image[rect.y1:rect.y2, rect.x1:rect.x2],
                               cv2.COLOR_RGB2GRAY)
            bar = int((roi[-8:, :] > 180).sum())
            if bar > best_bar:
                best_pos, best_bar = pos, bar
        if best_bar >= _TAB_BAR_MIN_PX:
            return best_pos
        return None

    def recognize_for_pos(self, ctx: SrContext, image: MatLike, pos: int) -> dict | None:
        """带部位先验的遗器列表识别(替换 op 用:从着装页点部位进来,列表已被
        该部位筛选锁定——候选收缩到单部位,同框歧义与跨部位误配同时下降)。

        :param pos: 装备部位号(1=头部 2=手部 3=躯干 4=脚部 5=位面球 6=连结绳,
            与 SrRelicPieceDef.pos 同坐标系)。
        """
        return self._recognize(ctx, image,
                               _relic_piece_templates_for_pos(pos),
                               _relic_piece_templates_scaled_for_pos(pos))

    def _recognize(self, ctx: SrContext, image: MatLike,
                   templates: dict[str, MatLike],
                   scaled_templates: dict[str, np.ndarray]) -> dict | None:
        """遗器列表识别主体;模板集可替换(全库 / 部位子集)。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, ocr_results, gray = self._locate_cards(ctx, image, list_area)

        anchor_cx = [r.center.x for r in card_rects]
        identity_hits = identify_cells(
            cv2.cvtColor(image, cv2.COLOR_RGB2GRAY), templates,
            list_area.rect, anchor_cx=anchor_cx)
        identity_by_card: dict[int, tuple[int, str]] = {}
        for ccx, ccy, votes, name in identity_hits:
            for idx, card_rect in enumerate(card_rects):
                center = card_rect.center
                if abs(ccx - center.x) <= 60 and abs(ccy - center.y) <= 60:
                    prev = identity_by_card.get(idx)
                    if prev is None or votes > prev[0]:
                        identity_by_card[idx] = (votes, name)
                    break

        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_score=self._owner_min_score())
            level = self._read_level(ocr_results, card_rect)
            if self._is_masked_card(ocr_results, card_rect):
                # 重掷动画帧:卡面被遮罩持续污染(同卡三帧 argmax 三个不同答案
                # 实证),身份不可信——标记 masked 不猜,其余字段照常输出
                piece_name, identity_src = None, 'masked'
            else:
                ident = identity_by_card.get(idx)
                piece_name, identity_src = ((ident[1], f'full({ident[0]}票)')
                                            if ident else (None, 'none'))
                if piece_name is None:
                    piece_name, confidence = _fallback_identity(gray, card_rect, scaled_templates)
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

    def _is_masked_card(self, ocr_results: list, card_rect: Rect) -> bool:
        """卡面被「重掷中」动画遮罩覆盖的检测(该卡身份不可识别,不猜测)。

        重掷动画期间卡面上方覆盖黄色横幅与动态特效,卡面特征被持续污染
        (同一卡连续三帧 fallback argmax 三个不同答案实证)——检测卡矩形内
        是否出现「重掷」类文本(右下角重掷按钮在列表区外,不会被误命中)。
        """
        for r in ocr_results:
            text = str(r.data).strip()
            if not text.startswith('重'):
                continue
            rect = r.rect
            if (card_rect.x1 + 10 <= (rect.x1 + rect.x2) / 2 <= card_rect.x2 - 10
                    and card_rect.y1 <= (rect.y1 + rect.y2) / 2 <= card_rect.y2):
                return True
        return False

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
    """光锥名 → 图标灰度模板(全量;常驻以命中 identify_cells 的特征缓存)。"""
    global _light_cone_template_cache
    if _light_cone_template_cache is None:
        lib: dict[str, MatLike] = {}
        for cone_name, cone_def in LIGHT_CONE_BY_NAME.items():
            template = load_template_gray(cone_icon_rel_path(cone_def.name))
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


#------------------- 光锥叠影模板(卡左缘罗马数字标) -------------------#

# 模板目录:<叠影数>_<序号>.png 的**整圆 ROI 灰度裁片**(34×34,含圆+字体+
# 配色态;亮金底黑字 / 暗底金字各配色态独立模板——同档异态的相关系数为负,
# 必须分模板)。叠影圆相对卡原点位置恒定 → 识别时同位裁窗直接对齐匹配。
# III/IV 档候实机采样补档(账号当前无该两档叠影的光锥),缺档判 None。
_SUPERIMPOSE_TEMPLATE_DIR = 'assets/template/light_cone_superimpose'
_SUPERIMPOSE_MATCH_MIN: float = 0.6
_superimpose_tpl_cache: dict[int, list[np.ndarray]] | None = None


def _superimpose_templates() -> dict[int, list[np.ndarray]]:
    """叠影数 → 整圆 ROI 灰度模板列表(每档可含多配色态;进程级常驻)。"""
    global _superimpose_tpl_cache
    if _superimpose_tpl_cache is None:
        base = Path(os_utils.get_path_under_work_dir(*_SUPERIMPOSE_TEMPLATE_DIR.split('/')))
        lib: dict[int, list[np.ndarray]] = {}
        for f in sorted(base.glob('*.png')):
            stem_rank = f.stem.split('_')[0]
            if not stem_rank.isdigit():
                continue
            img = cv2_utils.read_image(str(f))
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
            lib.setdefault(int(stem_rank), []).append(gray)
        _superimpose_tpl_cache = lib
    return _superimpose_tpl_cache


def _relic_piece_templates() -> dict[str, MatLike]:
    """遗器件名 → 部件图灰度模板(全量;常驻以命中 identify_cells 的特征缓存)。"""
    global _relic_piece_template_cache
    if _relic_piece_template_cache is None:
        lib: dict[str, MatLike] = {}
        for piece_name, set_def in PIECE_TO_SET.items():
            piece = next((p for p in set_def.pieces if p.name == piece_name), None)
            if piece is None:
                continue
            template = load_template_gray(icon_webp_rel_path(set_def.set_name, piece.name))
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


_pos_piece_template_cache: dict[int, dict[str, MatLike]] = {}
_pos_piece_scaled_cache: dict[int, dict[str, np.ndarray]] = {}


def _relic_piece_templates_for_pos(pos: int) -> dict[str, MatLike]:
    """部位过滤的遗器模板子集(pos 见 SrRelicPieceDef 坐标系;进程级缓存)。

    替换界面顶部部位筛选 tab 锁定列表内容——列表内全部为该部位件,候选从
    全库 192 件收缩到单部位(隧洞 ≤34 件),同框歧义竞争与跨部位误配同时
    下降(部位先验由调用方提供:替换 op 从着装页点部位进来,部位恒已知)。
    """
    if pos not in _pos_piece_template_cache:
        _pos_piece_template_cache[pos] = {
            name: t for name, t in _relic_piece_templates().items()
            if next(p for p in PIECE_TO_SET[name].pieces if p.name == name).pos == pos}
    return _pos_piece_template_cache[pos]


def _relic_piece_templates_scaled_for_pos(pos: int) -> dict[str, np.ndarray]:
    """部位过滤的预缩放遗器模板子集(降级匹配用;与全尺寸子集同键同源)。"""
    if pos not in _pos_piece_scaled_cache:
        _pos_piece_scaled_cache[pos] = {
            name: cv2.resize(t, _FALLBACK_TEMPLATE_SIZE)
            for name, t in _relic_piece_templates_for_pos(pos).items()}
    return _pos_piece_scaled_cache[pos]


def _fallback_identity(gray: np.ndarray, card_rect: Rect,
                       scaled_templates: dict[str, np.ndarray]) -> tuple[str | None, int]:
    """降级匹配:只取该卡区域内特征,对全库模板匹配取聚簇最大者(纯 argmax,无阈值)。

    整屏匹配的 Lowe 比值测试在同框式斜置卡牌间存在歧义竞争,真匹配被淘汰;
    格内局部匹配竞争者少,真匹配存活(晚安与睡颜实证:整屏 2 票 vs 格内 15 聚簇)。
    确定性先验:有等级锚点的卡必是全库之一(空格已被定位层过滤)——直接取聚簇
    最高的名字,不设分数门槛(用户裁定:认错也只会认成库内最近似,优于 null)。
    返回 (光锥名/件名, 聚簇 good 数);全库均无有效匹配时返 (None, 0)。
    """
    zone = gray[card_rect.y1:card_rect.y2, card_rect.x1:card_rect.x2]
    z_kp, z_desc = cv2_utils.feature_detect_and_compute(zone)
    if z_desc is None or len(z_kp) == 0:
        return None, 0
    bf = cv2.BFMatcher()
    best_name: str | None = None
    best_cluster = 0
    for name, t_s in scaled_templates.items():
        t_kp, t_desc = _cached_template_features(t_s)
        if t_desc is None:
            continue
        matches = bf.knnMatch(t_desc, z_desc, k=2)
        good_pts = [z_kp[m.trainIdx].pt for p in matches if len(p) == 2
                    and (m := p[0]) and m.distance < 0.75 * p[1].distance]
        if len(good_pts) < 3:
            continue
        # 聚簇:60px 半径内最大友好数(真命中聚在卡牌同位,误配分散)
        pts = np.float32(good_pts)
        cluster = 0
        for i in range(len(pts)):
            cluster = max(cluster, int((np.abs(pts - pts[i]).max(axis=1) < 60).sum()))
        if cluster > best_cluster:
            best_name, best_cluster = name, cluster
    return best_name, best_cluster
