"""光锥替换列表画面识别器:分层定位 + 分层识别(自含实现,不跨域共用)。

``analyze_screen`` 精准命中「光锥-替换」后,按「列表 / 网格内容识别范式」识别
(od-dev-write-operation references/list-grid-content-recognition.md):
**定位层**——每卡底部「等级N」文本锚点 + 轮廓补充(锚点漏读真卡) + 网格刚性
拓扑补全(行带内补列 / 行带间插行,只在证实行带之间补,不外推);列表按命途
分组、组末行常不满,补位须过内容证据门槛(空格是纯星空背景),滚动裁切卡
(可见高度不足、图案只露部分)信息不全,不识别;
**身份层**——masked 模板匹配(TM):卡面 = 图标构图贴图 × UI 缩放常量合成。
模板正源(卡面库单一入口 iter_light_cone_templates,TemplateLoader 规范目录
light_cone_icon/<id>/raw.webp,256×256)与实机列表卡面**同构图同源**——「列表
只渲染立绘一部分」发生在立绘→构图贴图一步,不发生在贴图→卡面一步,卡面是
构图贴图的等比缩小(实测 ~0.39),逐像素比对成立(实机 27 卡单尺度全对、
NCC 0.981-0.995,错误模板天花板 0.961)。按绝对目标像素缩放(主档 100px;
选中卡白框放大 ~6% → 106px 双档级联),前景 mask(底色距分割)后
TM_CCORR_NORMED 匹配,低于拒答门槛诚实返回 None 不硬猜。缩放按模板原始
尺寸换算——卡面渲染像素才是常量,比例随模板分辨率派生,混合尺寸模板库
禁用「比例」参数(遗器连结绳 512 件按 256 比例缩半全帧误判实证)。
**占用者**——角标区角色头像 SIFT 匹配。

网格定位/TM 身份/角标匹配的实现为本模块内副本(relic_list_recognizer 各持
一份,两域零 import——域自治裁定见
docs/develop/sr_od/application/cultivation/changes/2026-11-11-domain-restructure/
design.md §2.2)。卡片上无装备名称文本(名字只在选中后右侧详情出现)——定位与
装备某件走 ``EquipLightConeOp``。并发安全:recognize 纯读,模板预处理缓存均为
只读懒加载(幂等)。
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import CHARACTER_PATH_LIST, get_character_by_id
from sr_od.config.light_cone_templates import iter_light_cone_templates
from sr_od.mys.sr_light_cones import LIGHT_CONE_BY_NAME

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')

# masked TM 身份层参数(实机替换列表 27 卡标定:真值卡彩色 NCC 0.981-0.995、
# 同款多副本(最多 9 连)判名一致、次高模板天花板 0.961)
_TM_TARGET_PX = 100        # 256 正源模板的目标像素(卡面渲染实测 ~100px,2px 步进扫描峰值)
_TM_TARGET_PX_SELECTED = 106  # 选中卡(白框)渲染放大 ~6% → 106px(尺度扫描峰值)
_TM_CASCADE_GATE = 0.97    # 级联门槛:主档 NCC 低于此的卡再跑选中档(选中卡主档 ~0.97,
                           # 正常卡 ≥0.981 不触发,增量成本可忽略)
_TM_SEARCH_PAD = 22        # 卡矩形外扩(吸收定位偏差与版本间网格漂移)
_TM_GATE = 0.85            # 拒答门槛:低于此视为无有效图案,诚实返回 None 不硬猜
# 轮廓补充卡的完整高度下限:低于视为滚动裁切的部分卡(完整卡 155 高)
_CONTOUR_MIN_CARD_H = 135
# 网格插行的标准行距(光锥卡行距实机恒定,标定帧行带 cy 597/770/942 间距 172-173)
_GRID_ROW_GAP_PX: int = 172
# 插行判定的间距容差(锚点行带 cy 有个位数噪声)
_GRID_ROW_GAP_TOL_PX: int = 40

# 插值补全位的空格判别阈:卡矩形内 Canny(40,120) 边缘像素数下限。实机标定
# (替换列表滚动帧):真卡 ≥826、空格(纯星空背景)≤636,阈值取 700——插值位
# 真卡按「宁可漏不猜错」原则,证据不足即不出卡(用户裁定:分组列表只补
# 有肯定证据的位置,难定的算了)
_EMPTY_SLOT_MIN_EDGES = 700

# 与锚点卡去重的 IoU 门槛(轮廓矩形与锚点矩形重叠过半视为同一卡)
_DEDUPE_IOU = 0.5

# 轮廓补充卡的网格吸附半径:中心 x 距列中心 / 中心 y 距锚点行带(卡中心)的
# 最大偏差。真卡(含 OCR 漏锚卡)中心必与「列中心 × 锚点行带」交点吻合,
# 网格间隙纹理的伪矩形中心落在列与列之间,以此区分,不吸附且不贴列表边缘
# 的轮廓矩形丢弃。
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
        'total_cards': '定位到的卡总数(锚点 + 网格吸附过滤后的轮廓补充)',
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
                      list_area) -> tuple[list[Rect], list]:
        """定位层:等级文本锚点 + 轮廓补充,去重合并后按网格吸附过滤。

        轮廓补充的误检源实机实证:网格间隙的装饰底纹会形成闭合轮廓,矩形
        尺寸恰好落进卡尺寸窗,但中心不落在任何网格交点上;真卡(含 OCR 漏
        锚卡)中心必与「列中心 × 锚点行带」交点吻合。过滤规则:与锚点卡
        同列同行 → 保留(锚点漏读的真卡,信息完整);可见高度不足 → 丢弃
        (滚动裁切卡,等级文本已滚出、图案只露部分,信息不全不识别,见
        _filter_contour_offgrid);其余丢弃。

        :return: (卡矩形清单, 全图 OCR 结果)
        """
        ocr_results = ctx.ocr_service.get_ocr_result_list(image=image, crop_first=False)
        anchor_rects, interp_rects = detect_card_anchors(
            ocr_results, list_area.rect, self._col_centers(list_area.rect))
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        contour_rects = detect_card_rects_contours(gray, list_area.rect)
        merged = list(anchor_rects)
        for c_rect in contour_rects:
            if all(_iou(c_rect, a) < _DEDUPE_IOU for a in anchor_rects):
                merged.append(c_rect)
        merged = self._filter_contour_offgrid(merged, anchor_rects, list_area.rect)
        merged.extend(self._keep_evidenced_interps(merged, interp_rects, gray))
        merged.sort(key=lambda r: (r.y1 // 100, r.x1))
        return merged, ocr_results

    def _keep_evidenced_interps(self, merged: list[Rect], interp_rects: list[Rect],
                                gray: np.ndarray) -> list[Rect]:
        """网格插值补全位的证据门槛:未被已有卡覆盖且卡内容达标的才出卡。

        光锥替换列表按命途分组,组末行常不满(如 28 张 = 3 满行 + 1)——网格
        补位若无条件出卡,会把空格(纯星空背景)也补成卡;空格 TM 可达
        0.90-0.95(高于拒答门槛,实机幻影条目实证)。补全位判定:
        ①与已出卡(锚点/轮廓卡)重叠 → 同一卡,不重复出;
        ②卡矩形内边缘像素数 ≥_EMPTY_SLOT_MIN_EDGES → 有卡内容,出;
        ③都不满足 → 丢弃(难定的算了,滚动后完整卡会以锚点形态出现,
        不损失召回)。"""
        kept: list[Rect] = []
        for rect in interp_rects:
            if any(_iou(rect, m) >= _DEDUPE_IOU for m in merged):
                continue
            roi = gray[rect.y1:rect.y2, rect.x1:rect.x2]
            edges = cv2.Canny(roi, 40, 120)
            if int((edges > 0).sum()) >= _EMPTY_SLOT_MIN_EDGES:
                kept.append(rect)
        return kept

    def _filter_contour_offgrid(self, merged: list[Rect],
                                anchor_rects: list[Rect], list_rect: Rect) -> list[Rect]:
        """丢弃不吸附锚点网格的轮廓误检矩形与滚动裁切卡。

        锚点卡(行列解耦换算)天然在网格上,原样保留;仅对轮廓补充卡校验:
        中心 x 吸附列中心(固定列先验)、中心 y 与某锚点卡中心同行带,两者
        同时成立视为网格上的真卡(锚点 OCR 漏读场景);可见高度不足的轮廓卡
        是滚动裁切卡,直接丢弃——裁切卡等级文本已滚出可视区(输出必缺等级)、
        图案只露部分,识别无消费价值;完整卡在滚动后必以完整形态出现,不损失
        召回(多目标识别范式「不与任何预期区域重叠的命中丢弃」)。
        """
        col_centers = self._col_centers(list_rect)
        kept: list[Rect] = []
        anchor_set = {id(a) for a in anchor_rects}
        for rect in merged:
            if id(rect) in anchor_set:
                kept.append(rect)
                continue
            cx, cy = (rect.x1 + rect.x2) / 2, (rect.y1 + rect.y2) / 2
            col_ok = min(abs(cx - c) for c in col_centers) <= _CONTOUR_COL_SNAP_PX
            if not col_ok:
                # 列吸附是硬条件:真卡(含滚动裁切卡)x 方向必在列上;网格间隙
                # 纹理矩形顶到列表上边缘也不在列上
                continue
            # 裁切判据 = 可见高度不足(轮廓只包住卡的一部分),而非「贴列表边缘」
            # ——网格行1 卡 y1 会略超列表区上界(area 标定偏大/版本网格漂移),
            # 完整卡按贴边误杀会整行丢失(遗器侧 4.7 实机实证)
            if (rect.y2 - rect.y1) < _CONTOUR_MIN_CARD_H:
                continue  # 部分可见卡:图案不全,识别无消费价值,丢弃
            if not anchor_rects:
                # 无锚点(OCR 全空极端位)时轮廓是唯一信息源:行检查豁免,
                # 列吸附与部分卡检查照走(丢弃语义与有锚一致)
                kept.append(rect)
                continue
            row_ok = min(abs(cy - (a.y1 + a.y2) / 2) for a in anchor_rects) <= _CONTOUR_ROW_SNAP_PX
            if row_ok:
                kept.append(rect)
        return kept


class LightConeReplaceRecognizer(_EquipListRecognizerBase):
    """「光锥-替换」画面:分层定位 + 每件 = 光锥名/命途/等级/占用者/叠影。"""

    screen_name = '光锥-替换'

    extras_doc: dict[str, str] = {
        'items': '光锥件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, cone:光锥名, '
                 'path_cn:命途, level:光锥等级(1-80), owner:占用角色(中文名), '
                 'rank:叠影数(1-5,罗马数字标识别,判不出为 null), '
                 'identity: tm(NCC=masked 模板匹配置信)/none}],按卡位置排序;'
                 '全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 网格吸附过滤后的轮廓补充)',
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
        """光锥列表完整绑定:每件 {光锥名, 命途, 等级, 占用者, 叠影}。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, ocr_results = self._locate_cards(ctx, image, list_area)

        identity_by_card = _tm_identify_cells(image, *_tm_template_lists(ctx), card_rects)

        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_inliers=self._owner_min_inliers())
            level = self._read_level(ocr_results, card_rect)
            rank = self._read_superimpose(ctx, image, card_rect)
            ident = identity_by_card.get(idx)
            cone_name, identity_src = ((ident[1], f'tm({ident[0]:.3f})')
                                       if ident else (None, 'none'))
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


#------------------- masked TM 身份层(域内副本) -------------------#

_tm_prep_cache: dict[str, list[tuple[np.ndarray, np.ndarray]]] | None = None


def _fg_mask_from_rgb(rgb: np.ndarray) -> np.ndarray:
    """归档 webp 的前景 mask:四角中位取合成底色,色距 >30 为前景。

    归档模板无 alpha(透明区已按稀有度合成卡框底色),底色平坦不产生匹配
    信号;TM 逐像素比对必须剔除底色,否则底色互相关稀释前景分数。
    """
    corners = np.stack([rgb[:4, :4].reshape(-1, 3), rgb[:4, -4:].reshape(-1, 3),
                        rgb[-4:, :4].reshape(-1, 3), rgb[-4:, -4:].reshape(-1, 3)])
    bg = np.median(corners.reshape(-1, 3), axis=0)
    return np.linalg.norm(rgb.astype(np.float64) - bg[None, None, :], axis=2) > 30


def _tm_templates_all(ctx: SrContext) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """光锥名 → [(RGB 模板, 前景 mask), ...] 按档位,已缩放到目标像素(进程级缓存)。

    模板经卡面库单一入口 iter_light_cone_templates 取(规范目录
    assets/template/light_cone_icon/<id>/raw.webp;空 id 锥暂缺不入库,等
    国际版 wiki 同步补 id 自动生效)。缩放按模板原始尺寸归一:256 正源 →
    主档 100px / 选中档 106px——卡面渲染像素才是常量,比例随模板分辨率
    派生;双档覆盖列表常态与选中卡(白框)的放大渲染。
    """
    global _tm_prep_cache
    if _tm_prep_cache is not None:
        return _tm_prep_cache
    prep: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
    for entry in iter_light_cone_templates(ctx):
        img = entry.info.raw
        mask = _fg_mask_from_rgb(img)
        # 双档:主档(未选中卡渲染) + 选中档(选中卡白框放大 ~6%)。
        # 相似件分数接近时,选中卡的放大差足以让次优件反超(遗器侧行内
        # 死水头被透镜反超实证),双档级联为必需而非可选。
        entries = []
        for target in (_TM_TARGET_PX, _TM_TARGET_PX_SELECTED):
            tpl = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA).astype(np.float32)
            mask_s = (cv2.resize(mask.astype(np.uint8), (target, target),
                                 interpolation=cv2.INTER_NEAREST) * 255).astype(np.uint8)
            entries.append((tpl, mask_s))
        prep[entry.light_cone.name] = entries
    _tm_prep_cache = prep
    return _tm_prep_cache


def _tm_template_lists(ctx: SrContext) -> tuple[list, list]:
    """全库 TM 模板,分 (主档 list, 选中档 list) 两组。"""
    all_tmpl = _tm_templates_all(ctx)
    main = [(name, *entries[0]) for name, entries in all_tmpl.items()]
    sel = [(name, *entries[1]) for name, entries in all_tmpl.items()]
    return main, sel


def _tm_identify_cells(image: MatLike, main_templates: list[tuple[str, np.ndarray, np.ndarray]],
                       sel_templates: list[tuple[str, np.ndarray, np.ndarray]],
                       card_rects: list[Rect]) -> dict[int, tuple[float, str]]:
    """逐卡 masked TM 身份匹配,返回 {卡序号: (NCC, 光锥名)};低于门槛不返回。

    每卡搜索区 = 卡矩形外扩 _TM_SEARCH_PAD(吸收定位偏差与版本间网格漂移);
    模板前景 mask 后 TM_CCORR_NORMED(逐像素真实比对,无 SIFT 的特征库存量
    偏差——argmax 认成的是最万金油模板而非最近似件的缺陷不复现)。级联:
    先跑主档,低于 _TM_CASCADE_GATE 的卡再跑选中档(选中卡白框渲染放大 ~6%,
    相似件分数接近时主档会被次优件反超)取两档最高;仍低于 _TM_GATE 不进
    结果(无有效身份的诚实拒答,不硬猜)。
    """

    def _run(templates: list[tuple[str, np.ndarray, np.ndarray]],
             region: np.ndarray) -> tuple[float, str | None]:
        best_name, best_ncc = None, -1.0
        for name, tpl, mask in templates:
            th, tw = tpl.shape[:2]
            if th >= region.shape[0] or tw >= region.shape[1] or not mask.any():
                continue
            res = cv2.matchTemplate(region, tpl, cv2.TM_CCORR_NORMED, mask=mask)
            res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
            _, mx, _, _ = cv2.minMaxLoc(res)
            if mx > best_ncc:
                best_name, best_ncc = name, float(mx)
        return best_ncc, best_name

    img_f = image.astype(np.float32)
    results: dict[int, tuple[float, str]] = {}
    for idx, rect in enumerate(card_rects):
        rx1 = max(0, rect.x1 - _TM_SEARCH_PAD)
        ry1 = max(0, rect.y1 - _TM_SEARCH_PAD)
        rx2 = rect.x2 + _TM_SEARCH_PAD
        ry2 = rect.y2 + _TM_SEARCH_PAD
        region = img_f[ry1:ry2, rx1:rx2]
        ncc, name = _run(main_templates, region)
        if ncc < _TM_CASCADE_GATE and sel_templates:
            ncc2, name2 = _run(sel_templates, region)
            if ncc2 > ncc:
                ncc, name = ncc2, name2
        if name is not None and ncc >= _TM_GATE:
            results[idx] = (ncc, name)
    return results


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


#------------------- 装备替换列表卡位:等级文本锚点(识别器用) -------------------#
# 替换列表每张卡底部都有等级徽章文本(光锥「等级N」)——OCR 命中位置即卡位
# 锚点,滚动 / 命途分组头 / 空格天然免疫;固定网格几何在滚动后失效,已废弃。

_LEVEL_TEXT_RE = re.compile(r'^等级\d+$')


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
        # 卡尺寸窗(光锥 139×155,部分可见卡允许缩小)
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
    """从全图 OCR 结果提取光锥卡的等级文本锚点,按**网格刚性拓扑**换算卡矩形。

    行列解耦(替代逐锚点独立换算):锚点 OCR 框的 **cx 随文本长度漂移**
    (短文本框偏差实测 ±20px),不可信;**列位置用固定列中心先验**(列距恒定,
    实测误差 ≤1px),锚点 cx 仅用于吸附到最近列;**行位置用锚点 cy 的聚类
    众数**(同行多锚点取均值,单锚 y 噪声被平均;OCR 的 y 定位实测稳定)。

    **网格插值补卡**(网格刚性拓扑下锚点只是采样点,漏采样不改变网格):
    ①行带内补列——同行带锚点数 < 列数时缺列按固定列先验补出;②行带间
    插行——相邻行带间距为标准行距整数倍时,中间必夹整行漏锚卡,按网格
    插值补出。**只在证实行带之间插补,不向最高行带之上/最低行带之下外推**
    (列表边界/滚动裁切/组末不满行的不确定性留在边缘)。**补位 ≠ 出卡**:
    列表按命途分组,组末行常不满(如 28 张 = 3 满行 + 1),无条件补位会把
    空格也补成卡(实机幻影条目实证)——补位候选单列返回,由调用方按轮廓/
    内容证据取舍(见 ``_keep_evidenced_interps``)。

    :param ocr_results: 全图 OCR 结果列表(OcrMatchResult,含 .data/.rect)
    :param list_rect: 列表区(锚点须落在其内,排除右侧详情面板等)
    :param col_centers: 固定列中心 x 列表(9 列,由列表区 rect 按实测列距推导)
    :return: (锚点证据卡矩形清单, 网格补位候选清单),各自按 (行, 列) 排序。
        换算标定:光锥卡 139×155、卡底=锚点行带 cy+12。
    """
    # 1. 收集锚点 (cx, cy)
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

    # 2. 行带聚类:锚点 cy 排序后按间隔分簇(行距 ~172px,簇内间隔阈值 100px),
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

    # 2.5 网格插行:相邻行带间距为标准行距整数倍时,中间必夹整行漏锚卡,
    #     按网格插值补出中间行带(间距容差内才插,异常间距不乱补);
    #     最高行带之上/最低行带之下不外推(边缘不确定性,见 docstring)
    grid_rows: list[int] = []
    for i, band in enumerate(row_bands):
        if i > 0:
            gap = band - row_bands[i - 1]
            k = round(gap / _GRID_ROW_GAP_PX)
            if k >= 2 and abs(gap - k * _GRID_ROW_GAP_PX) <= _GRID_ROW_GAP_TOL_PX:
                for j in range(1, k):
                    grid_rows.append(row_bands[i - 1] + round(j * gap / k))
        grid_rows.append(band)

    # 3. 锚点位(证据卡)与网格补位(候选)分开出:锚点吸附的 (行带, 列) 为
    #    锚点证据位,其余(缺列补位 + 插值行全位)为补位候选,由调用方按
    #    证据取舍;光锥卡 139×155
    anchor_cells: set[tuple[int, int]] = set()
    for cx, cy, _text in anchors:
        col = min(range(len(col_centers)), key=lambda i: abs(cx - col_centers[i]))
        band = min(grid_rows, key=lambda b: abs(b - cy))
        anchor_cells.add((band, col))
    evidenced: list[Rect] = []
    interpolated: list[Rect] = []
    for band in grid_rows:
        for col_idx, col_cx in enumerate(col_centers):
            rect_card = Rect(col_cx - 70, band - 143, col_cx + 69, band + 12)
            if rect_card.x2 < list_rect.x1 or rect_card.x1 > list_rect.x2:
                continue
            if rect_card.y2 < list_rect.y1 or rect_card.y1 > list_rect.y2:
                continue
            if (band, col_idx) in anchor_cells:
                evidenced.append(rect_card)
            else:
                interpolated.append(rect_card)
    evidenced.sort(key=lambda r: (r.y1 // 100, r.x1))
    interpolated.sort(key=lambda r: (r.y1 // 100, r.x1))
    return evidenced, interpolated


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
