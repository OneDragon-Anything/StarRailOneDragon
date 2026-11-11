"""光锥替换列表画面识别器:分层定位 + 分层识别(自含实现,不跨域共用)。

``analyze_screen`` 精准命中「光锥-替换」后,按「网格多目标识别分层范式」识别
(od-dev-write-operation 多目标特征识别节):
**定位层**——每卡底部「等级N」文本锚点 + 轮廓补充(锚点漏读真卡) + 网格吸附
过滤;滚动裁切卡(贴列表边缘、等级文本滚出、图案只露部分)信息不全,不识别;
**内容识别层**——整屏主匹配 ``full(N票)`` + 格内兜底 ``fallback(N簇)``;
**占用者**——角标区角色头像 SIFT 匹配。

网格定位/身份投票/角标匹配的实现为本模块内副本(relic_list_recognizer 各持
一份,两域零 import——域自治裁定见
docs/develop/sr_od/application/cultivation/changes/2026-11-11-domain-restructure/
design.md §2.2),代码逐行与拆分前 equip_list_recognizer /
grid_template_locate / equip_owner_match 一致(行为锁定,批次B 判据)。
卡片上无装备名称文本(名字只在选中后右侧详情出现)——定位与装备某件走
``EquipLightConeOp``。并发安全:recognize 纯读,模板库与特征缓存均为只读
懒加载(幂等)。
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import CHARACTER_PATH_LIST, get_character_by_id
from sr_od.mys.sr_light_cones import LIGHT_CONE_BY_NAME
from sr_od.mys.sr_light_cones import icon_webp_rel_path as cone_icon_rel_path

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

    def _owner_min_inliers(self) -> int:
        """角标 SIFT 匹配的 RANSAC 内点数判定阈(光锥/遗器同阈,标定见
        equip_owner_match 模块 docstring;界面有独立标定需求时覆写)。"""
        return OWNER_MATCH_MIN_INLIERS

    def _badge_rect(self, card_rect: Rect) -> Rect:
        """角标检测区(卡片矩形内右上角,偏移实测)。"""
        raise NotImplementedError

    def _locate_cards(self, ctx: SrContext, image: MatLike,
                      list_area) -> tuple[list[Rect], list, MatLike]:
        """定位层:等级文本锚点 + 轮廓补充,去重合并后按网格吸附过滤。

        轮廓补充的误检源实机实证:网格间隙的装饰底纹会形成闭合轮廓,矩形
        尺寸恰好落进卡尺寸窗,但中心不落在任何网格交点上;真卡(含 OCR 漏
        锚卡)中心必与「列中心 × 锚点行带」交点吻合。过滤规则:与锚点卡
        同列同行 → 保留(锚点漏读的真卡,信息完整);贴列表上下边缘 → 丢弃
        (滚动裁切卡,等级文本已滚出、图案只露部分,信息不全不识别,见
        _filter_contour_offgrid);其余丢弃。

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
        """丢弃不吸附锚点网格的轮廓误检矩形与滚动裁切卡。

        锚点卡(行列解耦换算)天然在网格上,原样保留;仅对轮廓补充卡校验:
        中心 x 吸附列中心(固定列先验)、中心 y 与某锚点卡中心同行带,两者
        同时成立视为网格上的真卡(锚点 OCR 漏读场景);贴列表上下边缘的
        轮廓卡是滚动裁切卡,直接丢弃——裁切卡等级文本已滚出可视区(输出必缺
        等级)、图案只露部分(特征更弱,错认风险高于完整卡),识别无消费价值;
        完整卡在滚动后必以完整形态出现,不损失召回(多目标识别范式「不与任何
        预期区域重叠的命中丢弃」,od-dev-write-operation)。
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
                continue  # 裁切卡:等级文本滚出、图案不全,识别无消费价值,丢弃
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
        # 角标区 = 角标整圆(含白描边)外接正方形 44×44:圆心 ≈ 卡内
        # (x1+117, y1+31)、外径 ≈44px(Canny 环带点拟合 7 卡一致 + 径向
        # 亮度峰值交叉验证;网格规整,相对位置恒定)。
        return Rect(card_rect.x1 + 95, card_rect.y1 + 9,
                    card_rect.x1 + 139, card_rect.y1 + 53)

    def _list_area_name(self) -> str:
        return '区域-光锥列表'

    def _col_centers(self, list_rect: Rect) -> list[float]:
        """9 列中心:首卡中心 x1+72.5 起步、列距恒 139px(锚点卡实测)。"""
        return [list_rect.x1 + 72.5 + 139 * i for i in range(9)]

    def _read_superimpose(self, ctx: SrContext, image: MatLike,
                          card_rect: Rect) -> int | None:
        """卡左缘叠影圆标 → 叠影数(1-5);无法判定返回 None。

        流程(固定相对坐标 + 放大窗滑动匹配,不找圆——网格卡矩形规整一致,
        圆在卡内的相对位置恒定,实机目检圆心 ≈ 卡内 (+27,+62)、r 11-15):
        ① 探针 = 卡左缘放大窗 (x+2,y+42) 起 40×40(含圆完整+滑动余量;左界
        收 x+2 吸收卡 rect 可能的右偏漂移,避免圆左缘被窗缘切掉导致匹配
        失败;卡面装饰竖线在 x+50 外,不进窗);
        ② 与分档紧圆模板(assets/template/light_cone_superimpose/<叠影数>/
        raw.webp,26×26=圆心 ±13,TemplateLoader 规范 webp 存储)
        TM_CCOEFF_NORMED 滑动匹配取最高分,≥0.6 判定——位置漂移由滑动
        吸收,无需逐卡找圆。模板 id 带 -dark 后缀 = 暗底金字态(同档异态
        相关系数为负,必须分模板),rank 取 id 前缀数字。
        III/IV 档候实机采样补档,当前该两档判 None。"""
        templates = _superimpose_templates(ctx)
        if not templates:
            return None
        probe = cv2.cvtColor(
            image[card_rect.y1 + 42:card_rect.y1 + 82,
                  card_rect.x1 + 2:card_rect.x1 + 42], cv2.COLOR_RGB2GRAY)
        best_id, best_score = None, 0.0
        for tid, tpl in templates.items():
            res = cv2.matchTemplate(probe, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_score, _, _ = cv2.minMaxLoc(res)
            if max_score > best_score:
                best_id, best_score = tid, max_score
        if best_score < _SUPERIMPOSE_MATCH_MIN:
            return None
        return _superimpose_rank_of(best_id)

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
                                        min_inliers=self._owner_min_inliers())
            level = self._read_level(ocr_results, card_rect)
            rank = self._read_superimpose(ctx, image, card_rect)
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
_light_cone_template_cache: dict[str, MatLike] | None = None
_light_cone_scaled_cache: dict[str, np.ndarray] | None = None
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

# 模板目录(TemplateLoader 规范二级结构):<叠影数>/raw.webp = 归一 26×26
# 紧圆窗灰度裁片(圆心 ±13)。rank = 目录名数字,每档一个模板。底色与明暗差异(半透明圆透出的卡底
# 色差、1 星白底卡的亮底暗字反相)均被归一化相关系数 + 滑动匹配吸收,
# 实测白底 III 卡对暗底模板 0.669、暗紫底 I 卡对金褐底模板 0.999——
# 曾按底色/明暗分过多套模板,逐套实测均为冗余,已并。五档齐(1-5)。底色差异(半透明圆透出卡底)由 TM_CCOEFF_NORMED 的
# 去均值除方差 + 探针滑动匹配吸收,无需按底色分模板(暗紫底卡对金褐底
# 模板实测 0.99)。
_SUPERIMPOSE_SUB_DIR = 'light_cone_superimpose'
_SUPERIMPOSE_MATCH_MIN: float = 0.6
_SUPERIMPOSE_NORM_SIZE = (24, 24)
_superimpose_tpl_cache: dict[str, np.ndarray] | None = None


def _superimpose_templates(ctx: SrContext) -> dict[str, np.ndarray]:
    """模板 id → 归一灰度圆盘(24×24;经 ctx.template_loader,进程级常驻)。"""
    global _superimpose_tpl_cache
    if _superimpose_tpl_cache is None:
        lib: dict[str, np.ndarray] = {}
        for info in ctx.template_loader.get_all_template_info_from_disk():
            if info.sub_dir != _SUPERIMPOSE_SUB_DIR:
                continue
            raw = info.raw
            if raw is None:
                continue
            gray = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY) if raw.ndim == 3 else raw
            lib[info.template_id] = gray
        _superimpose_tpl_cache = lib
    return _superimpose_tpl_cache


def _superimpose_rank_of(template_id: str) -> int | None:
    rank = template_id.split('_')[0]  # id 形如 '5' / '1_dark'——前缀数字 = 叠影数
    return int(rank) if rank.isdigit() else None
def _fallback_identity(gray: np.ndarray, card_rect: Rect,
                       scaled_templates: dict[str, np.ndarray]) -> tuple[str | None, int]:
    """降级匹配:只取该卡区域内特征,对全库模板匹配取聚簇最大者(纯 argmax,无阈值)。

    整屏匹配的 Lowe 比值测试在同框式斜置卡牌间存在歧义竞争,真匹配被淘汰;
    格内局部匹配竞争者少,真匹配存活(晚安与睡颜实证:整屏 2 票 vs 格内 15 聚簇)。
    确定性先验:定位层过滤空格后留下的卡必是库内真件(锚点卡或锚点漏读的
    完整图案卡)——直接取聚簇最高的名字,不设分数门槛(用户裁定:认错也只会
    认成库内最近似,优于 null)。
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
# 特征点 y 聚簇的行间隔阈值(卡行高+间隙的量级)
_ROW_CLUSTER_GAP_PX: int = 100
# 列带吸附半径(约列间距一半)
_COL_SNAP_PX: int = 70
# 定位成功的最低票数(实机单卡 9~205 票;幻影簇可达 4~6 票,靠归属窗兜住)
_MIN_CELL_VOTES: int = 4
def load_template_gray(rel_path: str) -> np.ndarray | None:
    """加载图标模板灰度图。注:webp 走 read_image 时 alpha 已被强制丢弃,透明区合成分支实际不可达,模板底色由归档脚本预合成。

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
# 模板特征进程级缓存(键 = 模板对象 id;调用方需持模板 dict 常驻才能命中——
# 注:临时对象 id 撞上已释放条目会错配旧特征,模板 dict 必须常驻)
_template_feature_cache: dict[int, tuple] = {}


def _cached_template_features(template_gray: np.ndarray) -> tuple:
    """模板 SIFT 特征的进程级缓存包装(id 键控;常驻模板字典场景全量命中)。"""
    key = id(template_gray)
    if key not in _template_feature_cache:
        _template_feature_cache[key] = cv2_utils.feature_detect_and_compute(template_gray)
    return _template_feature_cache[key]
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
        相邻卡的点混算成 1 票(同行跨卡混算漏检实证);None 时回退簇均值
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
def detect_card_anchors(ocr_results: list, list_rect: Rect,
                        col_centers: list[float]) -> list[Rect]:
    """从全图 OCR 结果提取装备卡的等级文本锚点,按**行列解耦**换算卡矩形。

    行列解耦(替代逐锚点独立换算):锚点 OCR 框的 **cx 随文本长度漂移**
    (短文本框偏差实测 ±20px),不可信;**列位置用固定列中心先验**(列距恒定,
    实测误差 ≤1px),锚点 cx 仅用于吸附到最近列;**行位置用锚点 cy 的聚类
    众数**(同行多锚点取均值,单锚 y 噪声被平均;OCR 的 y 定位实测稳定)。

    :param ocr_results: 全图 OCR 结果列表(OcrMatchResult,含 .data/.rect)
    :param list_rect: 列表区(锚点须落在其内,排除右侧详情面板等)
    :param col_centers: 固定列中心 x 列表(光锥 9 列/遗器 4 列,由列表区 rect
        按实测列距推导,见 cone_col_centers/relic_col_centers)
    :return: 卡矩形清单(每个等级文本一张卡),按 (行, 列) 排序。
        换算标定:光锥卡 139×155、卡底=锚点行带 cy+12;
        遗器卡 120×160、卡底=锚点行带 cy+22(按文本样式自动区分)。
    """
    # 1. 收集锚点 (cy, text)
    anchors = []
    for r in ocr_results:
        text = str(r.data).strip()
        if not _LEVEL_TEXT_RE.match(text):
            continue
        rect = r.rect
        cx = (rect.x1 + rect.x2) / 2
        cy = (rect.y1 + rect.y2) / 2
        if not (list_rect.x1 <= cx <= list_rect.x2 and list_rect.y1 <= cy <= list_rect.y2):
            continue
        anchors.append((cx, cy, text))
    if not anchors:
        return []

    # 2. 行带聚类:锚点 cy 排序后按间隔分簇(行距 183~200px,簇内间隔阈值 100px),
    #    每簇行带取 cy 整数**众数**(出现频次最高的值)——均值会被离群锚点拉偏,
    #    众数反映最多锚点的共识位置
    anchors.sort(key=lambda a: a[1])
    row_bands: list[float] = []
    cluster_cys: list[float] = []
    prev_cy = None
    for _, cy, _text in anchors:
        if prev_cy is not None and cy - prev_cy <= 100:
            cluster_cys.append(cy)
        else:
            if cluster_cys:
                int_cys = [int(round(c)) for c in cluster_cys]
                row_bands.append(Counter(int_cys).most_common(1)[0][0])
            cluster_cys = [cy]
        prev_cy = cy
    if cluster_cys:
        int_cys = [int(round(c)) for c in cluster_cys]
        row_bands.append(Counter(int_cys).most_common(1)[0][0])

    # 3. 行 × 列组合:锚点吸附最近列中心,卡矩形 x 由固定列中心决定(cx 偏差不进入)
    rects: list[Rect] = []
    seen: set[tuple[int, int]] = set()
    for cx, cy, text in anchors:
        col = min(range(len(col_centers)), key=lambda i: abs(cx - col_centers[i]))
        row = min(range(len(row_bands)), key=lambda i: abs(cy - row_bands[i]))
        key = (row, col)
        if key in seen:
            continue
        seen.add(key)
        col_cx = col_centers[col]
        band_cy = row_bands[row]
        if text.startswith('等级'):  # 光锥:卡 139×155
            rect_card = Rect(col_cx - 70, band_cy - 143, col_cx + 69, band_cy + 12)
        else:  # 遗器「+N」:卡 120×160
            rect_card = Rect(col_cx - 60, band_cy - 138, col_cx + 60, band_cy + 22)
        if rect_card.x2 < list_rect.x1 or rect_card.x1 > list_rect.x2:
            continue
        if rect_card.y2 < list_rect.y1 or rect_card.y1 > list_rect.y2:
            continue
        rects.append(rect_card)
    rects.sort(key=lambda r: (r.y1 // 100, r.x1))
    return rects
_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标窗边长与匹配扩边:扩边吸收调用方定位偏差与选中卡放大溢出
_TEMPLATE_SIZE: int = 44
_ZONE_PAD: int = 16
# 上采样倍率:两尺度互补(部分角色仅在其一尺度上出足特征)
_UPSAMPLE_SCALES: tuple[int, ...] = (2, 3)
# Lowe 比值阈值(见模块 docstring 第 2 条:0.75+ 会让假一致内点过阈)
_LOWES_RATIO: float = 0.7
# 内点判定阈(光锥真角标 18-61 / 无角标卡面 ≤11;遗器真 16-30 / 无角标 4-8
# —— 两界面共用,偏真侧留漏报余量)
OWNER_MATCH_MIN_INLIERS: int = 15
# 颜色验证闸:最高内点模板的直方图距离全库排名须小于此值
_HIST_RANK_MAX: int = 5
# 歧义降级:次高(不同角色)内点 ≥ 最高×此比例且 ≥ 内点阈 → None
_AMBIG_RATIO: float = 0.75
# 场景侧直方图采样圆半径(zone 76×76 内的角标内圆)
_ZONE_HIST_RADIUS: int = 19

_SIFT = cv2.SIFT_create(nfeatures=400)
_MATCHER = cv2.BFMatcher()

_tpl_cache: dict[str, np.ndarray] | None = None
_feat_cache: dict[str, dict[int, tuple[list, np.ndarray | None]]] | None = None
_hist_cache: dict[str, np.ndarray] | None = None
def _templates() -> dict[str, np.ndarray]:
    """全部模板 RGB。avatarminiicon 为 RGBA(圆外透明),取 RGB 三通道。"""
    global _tpl_cache
    if _tpl_cache is not None:
        return _tpl_cache
    out: dict[str, np.ndarray] = {}
    base = Path(os_utils.get_path_under_work_dir(*_MINI_DIR_REL.split('/')))
    for f in sorted(base.glob('*.png')):
        img = cv2_utils.read_image(str(f))
        if img is None:
            continue
        if img.ndim == 3 and img.shape[2] == 4:
            img = img[:, :, :3]
        out[f.stem] = img
    _tpl_cache = out
    return out


def _tpl_features() -> dict[str, dict[int, tuple[list, np.ndarray | None]]]:
    """模板特征缓存:名字 → 尺度 → (关键点, 描述子);描述子 None = 该尺度特征贫乏。"""
    global _feat_cache
    if _feat_cache is not None:
        return _feat_cache
    out: dict[str, dict[int, tuple[list, np.ndarray | None]]] = {}
    for name, img in _templates().items():
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        by_scale: dict[int, tuple[list, np.ndarray | None]] = {}
        for k in _UPSAMPLE_SCALES:
            g_up = cv2.resize(gray, (gray.shape[1] * k, gray.shape[0] * k),
                              interpolation=cv2.INTER_CUBIC)
            by_scale[k] = _SIFT.detectAndCompute(g_up, None)
        out[name] = by_scale
    _feat_cache = out
    return out


def _tpl_hists() -> dict[str, np.ndarray]:
    """模板 HSV 色相/饱和直方图缓存(模板圆内采样,归一化)。"""
    global _hist_cache
    if _hist_cache is not None:
        return _hist_cache
    out: dict[str, np.ndarray] = {}
    for name, img in _templates().items():
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.circle(mask, (img.shape[1] // 2, img.shape[0] // 2),
                   int(img.shape[0] * 0.45), 255, -1)
        hist = cv2.calcHist([hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        out[name] = hist
    _hist_cache = out
    return out


def _inliers_at_scale(kp_z: list, des_z: np.ndarray | None,
                      tkp: list, tdesc: np.ndarray | None) -> int:
    """单尺度匹配:knnMatch(Lowe ratio)+ RANSAC,返回内点数。"""
    if des_z is None or tdesc is None or len(kp_z) < 4 or len(tkp) < 4 or len(des_z) < 4:
        return 0
    matches = _MATCHER.knnMatch(tdesc, des_z, k=2)
    good = [m[0] for m in matches
            if len(m) == 2 and m[0].distance < _LOWES_RATIO * m[1].distance]
    if len(good) < 4:
        return 0
    src = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_z[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, ransac_mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return int(ransac_mask.sum()) if ransac_mask is not None else 0
def match_owner(screen_rgb: np.ndarray, badge_rect: Rect,
                min_inliers: int = OWNER_MATCH_MIN_INLIERS) -> tuple[str | None, int]:
    """识别角标区的占用角色,返回**中文角色名**(如「黄泉」)。

    流程:角标窗扩边 → 场景 SIFT 特征(每尺度一次)→ 全库模板双尺度比对
    → 内点阈 → 直方图距离排名验证 → 歧义降级 → 中文名。

    :param screen_rgb: 整屏截图(RGB)
    :param badge_rect: 角标检测区(调用方按所在界面的角标偏移换算,见各 op 常量;
        窗须完整含角标圆,内部自动扩边吸收定位偏差)
    :param min_inliers: RANSAC 内点数判定阈
    :return: (中文角色名, 最高内点数);任一道判定不过返回 (None, 最高内点数) ——
        未装备 / 角标角色不在模板库 / 证据歧义,不猜测。中文映射缺失的角色
        兜底返回模板英文 id。
    """
    x1 = max(0, badge_rect.x1 - _ZONE_PAD)
    y1 = max(0, badge_rect.y1 - _ZONE_PAD)
    x2 = min(screen_rgb.shape[1], badge_rect.x2 + _ZONE_PAD)
    y2 = min(screen_rgb.shape[0], badge_rect.y2 + _ZONE_PAD)
    zone = screen_rgb[y1:y2, x1:x2]
    if zone.size == 0:
        return None, 0
    if zone.ndim == 3 and zone.shape[2] == 4:
        zone = zone[:, :, :3]
    gray_zone = cv2.cvtColor(zone, cv2.COLOR_RGB2GRAY)

    zone_feats: dict[int, tuple[list, np.ndarray | None]] = {}
    for k in _UPSAMPLE_SCALES:
        g_up = cv2.resize(gray_zone, (gray_zone.shape[1] * k, gray_zone.shape[0] * k),
                          interpolation=cv2.INTER_CUBIC)
        zone_feats[k] = _SIFT.detectAndCompute(g_up, None)

    per: dict[str, int] = {}
    for name, by_scale in _tpl_features().items():
        per[name] = max(_inliers_at_scale(*zone_feats[k], *by_scale[k])
                        for k in _UPSAMPLE_SCALES)
    order = sorted(per.items(), key=lambda kv: -kv[1])
    best_name, best_inliers = order[0]
    if best_inliers < min_inliers:
        return None, best_inliers

    dists = {n: cv2.compareHist(h, _zone_hist(zone), cv2.HISTCMP_BHATTACHARYYA)
             for n, h in _tpl_hists().items()}
    hist_rank = sorted(dists, key=dists.get).index(best_name)
    if hist_rank >= _HIST_RANK_MAX:
        return None, best_inliers

    if len(order) > 1:
        second_name, second_inliers = order[1]
        if (_owner_cn(second_name) != _owner_cn(best_name)
                and second_inliers >= _AMBIG_RATIO * best_inliers
                and second_inliers >= min_inliers):
            return None, best_inliers

    return _owner_cn(best_name), best_inliers


def _zone_hist(zone_rgb: np.ndarray) -> np.ndarray:
    """场景侧直方图:角标窗中心内圆采样(与模板圆同口径)。"""
    hsv = cv2.cvtColor(zone_rgb, cv2.COLOR_RGB2HSV)
    mask = np.zeros(zone_rgb.shape[:2], np.uint8)
    cv2.circle(mask, (zone_rgb.shape[1] // 2, zone_rgb.shape[0] // 2),
               _ZONE_HIST_RADIUS, 255, -1)
    hist = cv2.calcHist([hsv], [0, 1], mask, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist


def _owner_cn(template_name: str) -> str:
    """模板名 → 中文角色名;皮肤模板(`<角色id>_skin<衣装号>`)剥后缀归一。

    模板文件名 = Character.id(生成器按 character_const 保证),
    character_const 直接可查;未收录的角色(库先于角色录入更新)兜底
    返回模板名原串,不猜测。"""
    character = get_character_by_id(template_name)
    if character is not None:
        return character.cn
    base = re.sub(r'_skin\d+$', '', template_name)
    if base != template_name:
        character = get_character_by_id(base)
        if character is not None:
            return character.cn
    return template_name
