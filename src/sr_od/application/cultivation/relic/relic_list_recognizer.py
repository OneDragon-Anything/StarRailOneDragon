"""遗器替换列表画面识别器:分层定位 + 分层识别(自含实现,不跨域共用)。

``analyze_screen`` 精准命中「遗器-替换」后,按「网格多目标识别分层范式」识别:
**定位层**——每卡底部「+N」文本锚点 + 轮廓补充(锚点漏读真卡) + 网格吸附
过滤;滚动裁切卡(贴列表边缘、等级文本滚出、图案只露部分)信息不全,不识别;
**身份层**——masked 模板匹配(TM):卡面 = 图标 × UI 缩放常量合成(同渲染),
按绝对目标像素缩放模板,前景 mask(底色距分割)后 TM_CCORR_NORMED 匹配,
低于拒答门槛诚实返回 None 不硬猜。缩放按模板原始尺寸换算(256 正源 → 90px、
512 连结绳 → 96px),卡面渲染像素才是常量,比例随模板分辨率派生——混合尺寸
模板库禁用「比例」参数(512 件按 256 比例会缩小一半,连结绳全帧误判实证)。
**占用者**——角标区角色头像 SIFT 匹配。

网格定位/角标匹配的实现为本模块内副本(光锥/遗器两域零 import——域自治口径
见项目文档 docs/develop/sr_od/application/cultivation/README.md §3)。
卡片上无装备名称文本(名字只在选中后右侧详情出现)——定位与装备某件走
``EquipRelicOp``/``SelectBagRelicOp``。并发安全:recognize 纯读,模板预处理
缓存均为只读懒加载(幂等)。
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
from sr_od.config.character_const import get_character_by_id
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.mys.sr_relic_sets import PIECE_TO_SET, icon_webp_rel_path

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

_LEVEL_VALUE_RE = re.compile(r'(\d{1,3})')

# masked TM 身份层参数(2026-11-11 实机六部位帧验证:真值卡彩色 NCC 0.93-0.99,
# 全部判对;错误匹配峰值 ~0.93 出现在缩放档错位时,档位对齐后未复现)
_TM_TARGET_PX = 90        # 256 系正源模板的目标像素(卡面渲染实测 ~90px)
_TM_TARGET_PX_ROPE = 92   # 连结绳(pos6,512×512 正源)未选中卡渲染实测 ~92px
_TM_TARGET_PX_ROPE_SEL = 96  # 连结绳选中卡(白框)渲染放大 ~4% → 96px(尺度扫描峰值)
_TM_TARGET_PX_SELECTED = 96  # 256 系选中卡(白框)渲染实测 96px(尺度扫描峰值;与连结绳选中卡同值)
_TM_CASCADE_GATE = 0.95   # 级联门槛:主档 NCC 低于此的卡再跑选中档(选中卡通常 0-2 张,增量成本可忽略)
_TM_SEARCH_PAD = 22       # 卡矩形外扩(吸收定位偏差与版本间网格漂移)
_TM_GATE = 0.85           # 拒答门槛:低于此视为无有效图案(重掷中遮挡卡 0.86 级),诚实返回 None
# 轮廓补充卡的完整高度下限:低于视为滚动裁切的部分卡(完整卡 160 高;部分卡实测 111)
_CONTOUR_MIN_CARD_H = 140
# 网格插行的标准行距(遗器卡行距实机恒定,diag 帧行带 180/328/477/626/775 间距 148-149)
_GRID_ROW_GAP_PX: int = 149
# 插行判定的间距容差(锚点行带 cy 有个位数噪声)
_GRID_ROW_GAP_TOL_PX: int = 40

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
        同列同行 → 保留(锚点漏读的真卡,信息完整);贴列表上下边缘 → 丢弃
        (滚动裁切卡,等级文本已滚出、图案只露部分,信息不全不识别,见
        _filter_contour_offgrid);其余丢弃。

        :return: (卡矩形清单, 全图 OCR 结果)
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
        return merged, ocr_results

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
            if id(rect) in anchor_set:
                kept.append(rect)
                continue
            cx, cy = (rect.x1 + rect.x2) / 2, (rect.y1 + rect.y2) / 2
            col_ok = min(abs(cx - c) for c in col_centers) <= _CONTOUR_COL_SNAP_PX
            if not col_ok:
                # 列吸附是硬条件:真卡(含滚动裁切卡)x 方向必在列上;网格间隙
                # 纹理矩形顶到列表上边缘也不在列上(实机 476 中心 vs 列 429 实证)
                continue
            # 裁切判据 = 可见高度不足(轮廓只包住卡的一部分),而非「贴列表边缘」
            # ——网格行1 卡 y1 会略超列表区上界(area 标定偏大/版本网格漂移),
            # 完整卡按贴边误杀会整行丢失(4.7 版本脚部帧行1 三卡实证)
            if (rect.y2 - rect.y1) < _CONTOUR_MIN_CARD_H:
                continue  # 部分可见卡:图案不全,识别无消费价值,丢弃
            if not anchor_rects:
                # 无锚点(OCR 全空极端位)时轮廓是唯一信息源:行检查豁免,
                # 列吸附与贴边裁切卡检查照走(裁切卡丢弃语义与有锚一致)
                kept.append(rect)
                continue
            row_ok = min(abs(cy - (a.y1 + a.y2) / 2) for a in anchor_rects) <= _CONTOUR_ROW_SNAP_PX
            if row_ok:
                kept.append(rect)
        return kept

class RelicReplaceRecognizer(_EquipListRecognizerBase):
    """「遗器-替换」画面:分层定位 + 每件 = 件名/套装/部位/强化等级/占用者。"""

    screen_name = '遗器-替换'

    extras_doc: dict[str, str] = {
        'items': '遗器件清单 [{cell:[x1,y1,x2,y2] 卡片矩形, piece:单件名, '
                 'set:套装名, pos_cn:部位, level:强化等级(0-15), '
                 'owner:占用角色(中文名), identity: tm(NCC)/masked'
                 '(重掷动画遮罩卡,身份不判)/none}],按卡位置排序;'
                 '全部识别失败的卡不列',
        'total_cards': '定位到的卡总数(锚点 + 网格吸附过滤后的轮廓补充)',
    }

    def _badge_rect(self, card_rect: Rect) -> Rect:
        # 角标区(遗器卡,网格放大判读标定):头像圆心 ≈ (x2-19, y1+34)、直径
        # ≈40px(小于光锥角标 44px),圆右缘可超出卡右缘 ~1px —— 检测窗右缘
        # 外扩 6px 保证完整圆,否则圆被裁缺角导致匹配降分。语义与光锥同:
        # 角标 = 当前穿着者(2026-11-10 实机 3 帧审计实证:12 件在穿副本
        # 角标齐全且逐一识别正确,仓库件无角标)。
        return Rect(card_rect.x2 - 55, card_rect.y1 + 10,
                    card_rect.x2 + 6, card_rect.y1 + 62)

    def _list_area_name(self) -> str:
        return '区域-遗器列表'

    def _col_centers(self, list_rect: Rect) -> list[float]:
        """4 列中心:列表区 x1+66 起步、列距 123px(实机亮度剖面实测
        列中心 99/224/346/469;与 EquipRelicOp 同源)。"""
        return [list_rect.x1 + 66 + 123 * i for i in range(4)]

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
            return self._recognize(ctx, image, *_tm_templates_for_pos(pos))
        return self._recognize(ctx, image, *_tm_templates_all_lists())

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
        return self._recognize(ctx, image, *_tm_templates_for_pos(pos))

    def _recognize(self, ctx: SrContext, image: MatLike,
                   main_templates: list[tuple[str, np.ndarray, np.ndarray]],
                   sel_templates: list[tuple[str, np.ndarray, np.ndarray]]) -> dict | None:
        """遗器列表识别主体;TM 模板集可替换(全库 / 部位子集)。"""
        list_area = ctx.screen_loader.get_area(self.screen_name, self._list_area_name())
        card_rects, ocr_results = self._locate_cards(ctx, image, list_area)

        identity_by_card = _tm_identify_cells(image, main_templates, sel_templates, card_rects)

        items: list[dict] = []
        for idx, card_rect in enumerate(card_rects):
            owner, _score = match_owner(image, self._badge_rect(card_rect),
                                        min_inliers=self._owner_min_inliers())
            level = self._read_level(ocr_results, card_rect)
            if self._is_masked_card(ocr_results, card_rect):
                # 重掷动画帧:卡面被遮罩持续污染,身份不可信——标记 masked 不猜
                piece_name, identity_src = None, 'masked'
            else:
                ident = identity_by_card.get(idx)
                piece_name, identity_src = ((ident[1], f'tm({ident[0]:.3f})')
                                            if ident else (None, 'none'))
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
_tm_prep_cache: dict[str, list[tuple[np.ndarray, np.ndarray]]] | None = None


def load_template_rgb(rel_path: str) -> np.ndarray | None:
    """加载图标模板 RGB 图(cv2 产物 BGR,读入后立即转 RGB——口径纪律见 AGENTS.md §5)。

    :param rel_path: 项目相对路径(如 assets/game_data/... 的 / 分隔形式)
    :return: RGB 图;文件不存在返回 None(调用方判停)
    """
    path = os_utils.get_path_under_work_dir(*rel_path.split('/'))
    img = cv2_utils.read_image(path)
    if img is None:
        return None
    return img


def _fg_mask_from_rgb(rgb: np.ndarray) -> np.ndarray:
    """归档 webp 的前景 mask:四角中位取合成底色,色距 >30 为前景。

    归档模板无 alpha(透明区已合成深紫底),底色平坦不产生匹配信号;TM 逐
    像素比对必须剔除底色,否则底色互相关稀释前景分数。
    """
    corners = np.stack([rgb[:4, :4].reshape(-1, 3), rgb[:4, -4:].reshape(-1, 3),
                        rgb[-4:, :4].reshape(-1, 3), rgb[-4:, -4:].reshape(-1, 3)])
    bg = np.median(corners.reshape(-1, 3), axis=0)
    return np.linalg.norm(rgb.astype(np.float64) - bg[None, None, :], axis=2) > 30


def _tm_templates_all() -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """遗器件名 → [(RGB 模板, 前景 mask), ...] 按档位,已缩放到目标像素(进程级缓存)。

    缩放按模板原始尺寸归一:256 正源 → _TM_TARGET_PX、512 连结绳 → 92/96 双档
    ——卡面渲染像素才是常量,比例随模板分辨率派生;连结绳双档覆盖列表常态与
    选中卡(白框)的放大渲染。
    """
    global _tm_prep_cache
    if _tm_prep_cache is None:
        prep: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
        for piece_name, set_def in PIECE_TO_SET.items():
            piece = next((p for p in set_def.pieces if p.name == piece_name), None)
            if piece is None:
                continue
            img = load_template_rgb(icon_webp_rel_path(set_def.set_name, piece_name))
            if img is None:
                continue
            mask = _fg_mask_from_rgb(img)
            # 双档:主档(未选中卡渲染) + 选中档(选中卡白框放大 ~4%)。
            # 相似件分数接近时,选中卡的放大差足以让次优件反超(行1列2 死水头
            # 被透镜反超实证),双档级联为必需而非可选。
            targets = ((_TM_TARGET_PX_ROPE, _TM_TARGET_PX_ROPE_SEL) if piece.pos == 6
                       else (_TM_TARGET_PX, _TM_TARGET_PX_SELECTED))
            entries = []
            for target in targets:
                tpl = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA).astype(np.float32)
                mask_s = (cv2.resize(mask.astype(np.uint8), (target, target),
                                     interpolation=cv2.INTER_NEAREST) * 255).astype(np.uint8)
                entries.append((tpl, mask_s))
            prep[piece_name] = entries
        _tm_prep_cache = prep
    return _tm_prep_cache


def _tm_templates_all_lists() -> tuple[list, list]:
    """全库 TM 模板,分 (主档 list, 选中档 list) 两组(全库识别用)。"""
    all_tmpl = _tm_templates_all()
    main = [(name, *entries[0]) for name, entries in all_tmpl.items()]
    sel = [(name, tpl, mask)
           for name, entries in all_tmpl.items() for tpl, mask in entries[1:]]
    return main, sel


def _tm_templates_for_pos(pos: int) -> tuple[list, list]:
    """部位过滤的 TM 模板子集,分 (主档 list, 选中档 list) 两组(pos 见
    SrRelicPieceDef 坐标系)。

    替换界面顶部部位筛选 tab 锁定列表内容——列表内全部为该部位件,候选从
    全库 192 件收缩到单部位(隧洞 ≤34 件),跨部位误配同步下降(部位先验
    由调用方提供:替换 op 从着装页点部位进来,部位恒已知)。
    """
    all_tmpl = _tm_templates_all()
    main: list[tuple[str, np.ndarray, np.ndarray]] = []
    sel: list[tuple[str, np.ndarray, np.ndarray]] = []
    for name in all_tmpl:
        if next(p for p in PIECE_TO_SET[name].pieces if p.name == name).pos != pos:
            continue
        entries = all_tmpl[name]
        main.append((name, *entries[0]))
        for tpl, mask in entries[1:]:
            sel.append((name, tpl, mask))
    return main, sel


def _tm_identify_cells(image: MatLike, main_templates: list[tuple[str, np.ndarray, np.ndarray]],
                       sel_templates: list[tuple[str, np.ndarray, np.ndarray]],
                       card_rects: list[Rect]) -> dict[int, tuple[float, str]]:
    """逐卡 masked TM 身份匹配,返回 {卡序号: (NCC, 件名)};低于门槛不返回。

    每卡搜索区 = 卡矩形外扩 _TM_SEARCH_PAD(吸收定位偏差与版本间网格漂移);
    模板前景 mask 后 TM_CCORR_NORMED(逐像素真实比对,无 SIFT 的特征库存量
    偏差——argmax 认成的是最万金油模板而非最近似件的缺陷不复现)。级联:
    先跑主档,低于 _TM_CASCADE_GATE 的卡再跑选中档(选中卡白框渲染放大 ~4%,
    相似件分数接近时主档会被次优件反超)取两档最高;仍低于 _TM_GATE 不进
    结果(重掷中遮挡卡等无有效身份的诚实拒答,不硬猜)。
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
    """从全图 OCR 结果提取装备卡的等级文本锚点,按**网格刚性拓扑**换算卡矩形。

    行列解耦(替代逐锚点独立换算):锚点 OCR 框的 **cx 随文本长度漂移**
    (短文本框偏差实测 ±20px),不可信;**列位置用固定列中心先验**(列距恒定,
    实测误差 ≤1px),锚点 cx 仅用于吸附到最近列;**行位置用锚点 cy 的聚类
    众数**(同行多锚点取均值,单锚 y 噪声被平均;OCR 的 y 定位实测稳定)。

    **网格插值补卡**(网格刚性拓扑下锚点只是采样点,漏采样不改变网格):
    ①行带内补列——非末行带恒满(列表按排序连续填充、无分组),缺列按固定
    列先验补出(4.7 实机脚部帧行1 单锚点确立行带,列1/3/4 漏锚网格补齐实证);
    ②行带间插行——相邻行带间距为标准行距整数倍时,中间必夹整行漏锚卡,
    按网格插值补出。**只在证实行带之间插补,不向最高行带之上/最低行带之下
    外推**(列表边界/滚动裁切的不确定性留在边缘)。**最后一个行带只出锚点
    位**:列表无分组、只有末行可能不满——末行带的缺列无法区分「空格」与
    「漏锚真卡」,不补(宁缺不猜);该行滚动后成为中间行,按恒满规则自然
    补全,不损失召回。

    :param ocr_results: 全图 OCR 结果列表(OcrMatchResult,含 .data/.rect)
    :param list_rect: 列表区(锚点须落在其内,排除右侧详情面板等)
    :param col_centers: 固定列中心 x 列表(光锥 9 列/遗器 4 列,由列表区 rect
        按实测列距推导,见 cone_col_centers/relic_col_centers)
    :return: 卡矩形清单(锚点位 + 非末行带补位,按 (行, 列) 排序)。
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

    # 3. 出卡:列表连续无分组(部位筛选后的持有清单),非末行带恒满,缺列
    #    补出;最后一个行带只出锚点位(该行可能不满,空格与漏锚卡不可分,
    #    宁缺不猜——滚动后该行成为中间行,按恒满规则自然补全)。卡样式按
    #    锚点文本判定(整张列表同款,同一画面不会混样式)
    cone_style = any(text.startswith('等级') for _, _, text in anchors)
    top_off, bot_off = (143, 12) if cone_style else (138, 22)
    x2_off = 69 if cone_style else 60
    anchor_cells: set[tuple[int, int]] = set()
    for cx, cy, _text in anchors:
        col = min(range(len(col_centers)), key=lambda i: abs(cx - col_centers[i]))
        band = min(grid_rows, key=lambda b: abs(b - cy))
        anchor_cells.add((band, col))
    last_band = grid_rows[-1]
    rects: list[Rect] = []
    for band in grid_rows:
        for col_idx, col_cx in enumerate(col_centers):
            if band == last_band and (band, col_idx) not in anchor_cells:
                continue  # 末行带只出锚点位
            rect_card = (Rect(col_cx - 70, band - top_off, col_cx + x2_off, band + bot_off)
                         if cone_style else
                         Rect(col_cx - 60, band - top_off, col_cx + 60, band + bot_off))
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
