"""逐光捡金编队识别:弱点属性(建议属性)+ 节点队伍槽(右侧)。

弱点主路径:OCR 锚「建议属性」→ 图块带 → 色块检测 → 元素模板匹配主判 +
色相域交叉仲裁;boss 名查静态弱点表覆盖。每节点绑定该节点弱点 + 该节点当前编队
成员(槽位裁片识别,标定见 ``_ARC_*`` 常量块)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.base.geometry.point import Point
from one_dragon.base.screen.template_info import TemplateInfo
from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import os_utils
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    MemberGuess,
    NodeInfo,
    get_area_rect,
    identify_crop,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

# --------------------------------------------------------------------------
# 弱点属性(建议属性)识别:OCR 锚「建议属性」→ 图块带 → 色块检测 →
# 元素模板匹配(element_weakness 底板合成模板)主判 + 色相域交叉仲裁。
# 锚定位使识别对布局平移不敏感(环境描述行数变化会推移内容,固定 rect 会错位)。
# 图块带相对锚行有两种布局(weakness_layout):
# - 'below':图块带在锚行正下方(忘却之庭/虚构叙事编队屏);
# - 'inline':图块带与锚文字同行、紧贴其右(末日幻影编队屏 boss 卡)。
# 色相域标定:实机帧(物竞天择其一/其十)6 blob 全对 —— 雷 H≈122 /
# 量子 H≈144 / 冰 H≈95 / 虚数 H≈26 / 火 H≈1 / 物理=白色纹样(S<30,V>150);
# 风未见样本,按色相域预留(模板已入库,出现样本后回验)。
# --------------------------------------------------------------------------
_WEAKNESS_ANCHOR_TEXT: str = '建议属性'
_WEAKNESS_LAYOUT_BELOW: str = 'below'    #: 图块带在锚行正下方
_WEAKNESS_LAYOUT_INLINE: str = 'inline'  #: 图块带与锚文字同行、紧贴其右
_WEAKNESS_INLINE_X_OFF: int = 90     #: inline 图标带起点相对锚行左缘偏移
                                     # (「建议属性」4 字宽+间隙;OCR det 框常把首图标
                                     #  粘进文本框,框右缘不可用,实机帧标定)
_WEAKNESS_INLINE_ZONE_W: int = 100   #: inline 图标带搜索区宽(4 图标带+余量,
                                     #  不及右侧相邻元素防误检,实机帧标定)
_WEAKNESS_INLINE_BLOB_MAX: int = 40  #: inline 图标外接框上限(两图标粘连拦截)
_WEAKNESS_ZONE_W: int = 200          #: below 图块带搜索区宽(锚点左对齐)
_WEAKNESS_ZONE_H: int = 60           #: 图块带搜索区高(below:标签底缘起;inline:锚行框扩)
_WEAKNESS_HUE_BUCKETS: tuple[tuple[str, int, int], ...] = (
    ('火', 0, 12), ('火', 168, 179), ('虚数', 15, 35), ('风', 40, 80),
    ('冰', 84, 110), ('雷', 112, 132), ('量子', 136, 158),
)
_ELEMENT_NAMES: tuple[str, ...] = ('火', '冰', '雷', '风', '量子', '虚数', '物理')
_ELEMENT_TEMPLATE_DIR: str = 'element_weakness'
_WEAKNESS_BLOB_MIN: int = 16         #: 图标色块外接框下限(px,膨胀后)
_WEAKNESS_BLOB_MAX: int = 64         #: 图标色块外接框上限
_WEAKNESS_TM_MIN: float = 0.45       #: TM 置信下限(低于 = 走色相域回退)
_WEAKNESS_MAX_ROWS: int = 4          #: 节点锚行上限(防 OCR 误检炸量;当前模式最多 2-3)
_BOSS_WEAKNESS_FILE: str = 'tl_boss_weaknesses.yml'  #: boss 弱点表(assets/game_data 下)

_WEAKNESS_BOSS_MAX_DY: int = 300      #: boss 名行与其节点锚行的最大纵向距离
                                     # (同 boss 卡内;超出视为跨卡,不覆盖)

# --------------------------------------------------------------------------
# 星启(三节点)布局槽位标定:编队屏收起态行内槽位剪影的真实位置(已填充帧
# 目测 + 脸库匹配验证:56px 裁片诚实命中,64px 会引入跨槽假阳性)。双节点
# 布局(难度 01-03)槽位用静态 screen_info area;星启(难度 04)行位置整体
# 上移且槽位 x 区间不同,静态 area 与「锚 y+固定 x」均错位——锚行数 >2 时
# 全行按本组常量计算裁片。裁片以头像中心为基准;置信普遍低于 FH(特写变体
# 差异,个别角色零命中属已知缺口)。
# --------------------------------------------------------------------------
_ARC_ROW_SLOT_CYS: tuple[int, ...] = (337, 548, 763)  #: 三行槽位头像中心 y(行序)
_ARC_SLOT_CXS: tuple[int, ...] = (1494, 1547, 1600, 1653)  #: 4 槽头像中心 x
_ARC_SLOT_SIZE: int = 56                #: 槽位裁片边长(方)
# ⚠️ 星启空槽判定未解决:空槽底板亮度(V≈182)与有角色无法按 V 区分;SIFT 特征数
# 亦不可分(实测空槽 33/36 vs 有人 20/35——空槽剪影本身高纹理)。
# 候选方案 = 空槽剪影模板匹配(空编 fixture 裁模板),标定后再实装。


def ensure_element_templates(ctx: SrContext) -> dict[str, TemplateInfo]:
    """元素弱点模板(元素名→TemplateInfo;assets/template/element_weakness/<元素>/raw.png)。

    模板源 = 官方元素图标(64px RGBA),入库前预合成到实采底板色(RGB 31,30,50)上
    —— 与游戏内「暗色圆板 + 彩色纹样」渲染一致。缓存 ctx(只读资源,幂等,并发安全);
    缺失降级为空 dict(走色相域回退)。
    """
    cached = getattr(ctx, 'tl_element_templates', None)
    if cached:
        return cached
    loader = TemplateLoader()
    out: dict[str, TemplateInfo] = {}
    for cname in _ELEMENT_NAMES:
        t = loader.get_template(_ELEMENT_TEMPLATE_DIR, cname)
        if t is not None:
            out[cname] = t
    ctx.tl_element_templates = out
    return out


def ensure_boss_weakness_map(ctx: SrContext) -> dict[str, list[str]]:
    """boss 名 → 弱点表(全玩法扁平;assets/game_data/tl_boss_weaknesses.yml)。

    弱点主路径:「建议属性」图标过小且 boss 卡底板带 tint,雷紫/量子蓝色相域
    跨场景渲染重叠,像素颜色识别无法稳定仲裁紫色系;boss 名为大字高置信 OCR,
    以名查表为弱点唯一来源,颜色识别仅作表未收录 boss 的降级。表未命中 = 空
    dict(纯降级,不报错)。缓存 ctx(只读资源,幂等,并发安全)。
    """
    cached = getattr(ctx, 'tl_boss_weakness_map', None)
    if cached is not None:
        return cached
    path = os_utils.get_path_under_work_dir('assets', 'game_data', _BOSS_WEAKNESS_FILE)
    data = YamlOperator(path).data or {}
    out: dict[str, list[str]] = {}
    for mode_bosses in data.values():
        if isinstance(mode_bosses, dict):
            out.update(mode_bosses)
    ctx.tl_boss_weakness_map = out
    return out


def _weakness_hue(crop: MatLike) -> int:
    """色块裁片彩色纹样像素的中位 H(S>60,V>80;无彩像素返 -1)。"""
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    colored = (s > 60) & (v > 80)
    if int(colored.sum()) < 15:
        return -1
    return int(np.median(hsv[:, :, 0][colored]))


def _weakness_hue_element(hue: int) -> str | None:
    """色相中位 → 元素名(域表见 _WEAKNESS_HUE_BUCKETS;域外 None)。"""
    for name, lo, hi in _WEAKNESS_HUE_BUCKETS:
        if lo <= hue <= hi:
            return name
    return None


def _classify_weakness_blob(crop: MatLike, templates: dict[str, TemplateInfo]) -> str | None:
    """弱点图块裁片 → 元素名。

    TM 主判:元素模板缩放到色块尺寸后 CCOEFF_NORMED(模板已含底板,
    与游戏渲染一致;CCOEFF 去均值抑制底色差)。两道交叉:
    - 白色纹样直判:blob 内白像素占优(相邻图标边缘可能渗入少量彩像素,按占比裁断)
      → 物理(白色双剑=物理,实机帧标定);
    - 紫对仲裁:TM 最佳为 雷/量子 且色相明确落在另一域 → 按色相纠正(同色不同相,
      TM 色彩主导会互串,实机帧实测雷/量子互错);
    - 低分回退:TM < 阈值 → 色相域判定(全 blob 标定全对)。
    """
    bh, bw = crop.shape[:2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    colored_px = int(((s > 60) & (v > 80)).sum())
    white_px = int(((s < 60) & (v > 130)).sum())
    if white_px >= 30 and white_px >= colored_px * 2:
        return '物理'
    hue = int(np.median(hsv[:, :, 0][(s > 60) & (v > 80)])) if colored_px >= 15 else -1
    best_name: str | None = None
    best_score = -1.0
    for cname, t in templates.items():
        t_s = cv2.resize(t.raw, (bw, bh), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(crop, t_s, cv2.TM_CCOEFF_NORMED)
        res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
        score = float(res.max())
        if score > best_score:
            best_name, best_score = cname, score
    if best_name is None:
        return None
    if best_name in ('雷', '量子') and hue >= 0:
        hue_elem = _weakness_hue_element(hue)
        if hue_elem in ('雷', '量子') and hue_elem != best_name:
            return hue_elem
    if best_score < _WEAKNESS_TM_MIN:
        return _weakness_hue_element(hue)
    return best_name


def _detect_weakness_blobs(zone: MatLike,
                           blob_max: int = _WEAKNESS_BLOB_MAX) -> list[tuple[int, int, int, int]]:
    """图块带 → 图标外接框列表(按 x 序;彩色纹样 + 白色纹样双路,膨胀融臂去重)。

    白色路放宽到 S<60,V>130:底板带 tint 的画面(如末日幻影 boss 卡)会把
    物理白色纹样压灰(S 40-60),过严会整图标漏检;彩色图标(S>60)不受影响。
    """
    hsv = cv2.cvtColor(zone, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    kernel = np.ones((3, 3), np.uint8)
    boxes: list[tuple[int, int, int, int]] = []
    seen: list[tuple[int, int]] = []
    for mask_bool in ((s > 60) & (v > 80), (s < 60) & (v > 130)):
        mask = mask_bool.astype(np.uint8) * 255
        mask = cv2.dilate(mask, kernel, iterations=1)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (_WEAKNESS_BLOB_MIN <= w <= blob_max
                    and _WEAKNESS_BLOB_MIN <= h <= blob_max):
                continue
            if any(abs(x - sx) < 12 and abs(y - sy) < 12 for sx, sy in seen):
                continue
            seen.append((x, y))
            boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: b[0])
    return boxes


def _match_boss_weaknesses(ocr_results: list,
                           anchor_y: int,
                           mapping: dict[str, list[str]]) -> list[str] | None:
    """锚行上方的 boss 名 OCR 文本 → 弱点表值;未命中返回 None。

    boss 名行(「节点N | boss名」标题行)在其节点锚行上方同一 boss 卡内;
    OCR 可能将「节点一」与 boss 名粘为一条,故按「文本含表名」匹配,
    多命中取距锚最近者(同一卡内唯一,跨卡由距离上限拦截)。
    """
    best_name: str | None = None
    best_dy: int | None = None
    for r in ocr_results:
        text = (r.data or '').strip()
        if not text or r.y >= anchor_y:
            continue
        dy = anchor_y - r.y
        if dy > _WEAKNESS_BOSS_MAX_DY:
            continue
        for boss_name in mapping:
            if boss_name in text and (best_dy is None or dy < best_dy):
                best_name, best_dy = boss_name, dy
                break
    if best_name is None:
        return None
    return list(mapping[best_name])


def read_team_nodes(ctx: SrContext, image: MatLike,
                    screen_name: str = '忘却之庭-编队',
                    weakness_layout: str = _WEAKNESS_LAYOUT_BELOW,
                    boss_weakness_map: dict[str, list[str]] | None = None) -> list[NodeInfo]:
    """按「建议属性」锚行装配节点列表(每锚 = 一节点,数量实读)。

    每节点绑定:该节点弱点属性 + 该节点当前编队成员(槽位 area 按行号取,
    area 未建档的行 members = [],不返回不完整列表,不编造)。锚未读到 = 空列表
    (降级不编造)。screen_name:槽位 area 的归属屏——逐光捡金各编队屏行结构
    同构但槽位坐标逐屏独立建档(FH=忘却之庭-编队 / PF=虚构叙事-编队 /
    AS=末日幻影-编队,槽间距 90px vs 65px)。
    weakness_layout:弱点图块带相对锚行的布局,'below'=锚行正下方(忘却之庭/
    虚构叙事), 'inline'=与锚文字同行紧贴其右(末日幻影 boss 卡);
    布局错配 = 图块带落在搜索区外,弱点恒为空列表(不报错,降级语义)。
    boss_weakness_map:boss 名 → 弱点表(ensure_boss_weakness_map)。命中时
    覆盖该节点颜色识别结果(主路径);boss 名取锚行上方同卡标题行的 OCR 文本
    (含即命中,最近优先,距离上限 300px 防跨卡误配)。"""
    from sr_od.config.avatar_templates import iter_avatar_templates

    templates = iter_avatar_templates(ctx)
    results = ctx.ocr_service.get_ocr_result_list(image=image)
    anchors = sorted(
        (r for r in results if _WEAKNESS_ANCHOR_TEXT in (r.data or '')),
        key=lambda r: r.y,
    )
    # 锚行数 >2 = 星启三节点布局:槽位 rect 走锚偏移(静态 area 仅双节点标定)
    multi_row = len(anchors) > 2
    nodes: list[NodeInfo] = []
    for idx, a in enumerate(anchors[:_WEAKNESS_MAX_ROWS], start=1):
        if weakness_layout == _WEAKNESS_LAYOUT_INLINE:
            # 同行布局:OCR det 框可能粘进首图标,起点用固定偏移绕开;
            # 带宽只盖图标带(不及右侧相邻元素防误检)
            x1 = a.x + _WEAKNESS_INLINE_X_OFF
            y1 = max(0, a.y - 8)
            zone_w, zone_h = _WEAKNESS_INLINE_ZONE_W, a.h + 16
            blobs = _detect_weakness_blobs(image[y1:y1 + zone_h, x1:x1 + zone_w],
                                           blob_max=_WEAKNESS_INLINE_BLOB_MAX)
        else:
            x1 = max(0, a.x - 15)
            y1 = a.y + a.h + 2
            zone_w, zone_h = _WEAKNESS_ZONE_W, _WEAKNESS_ZONE_H
            blobs = _detect_weakness_blobs(image[y1:y1 + zone_h, x1:x1 + zone_w])
        weaknesses: list[str] = []
        for (bx, by, bw, bh) in blobs:
            pad = 4
            zone = image[y1:y1 + zone_h, x1:x1 + zone_w]
            crop = zone[max(0, by - pad):by + bh + pad, max(0, bx - pad):bx + bw + pad]
            name = _classify_weakness_blob(crop, ensure_element_templates(ctx))
            if name:
                weaknesses.append(name)
        if boss_weakness_map:
            mapped = _match_boss_weaknesses(results, a.y, boss_weakness_map)
            if mapped is not None:
                weaknesses = mapped
        members: list[MemberGuess] = []
        if multi_row:
            # 锚行序号 ↔ 槽位行 y 一一对应(行循环外初始化会把三行累积进同一列表)
            cy = _ARC_ROW_SLOT_CYS[idx - 1]
            half = _ARC_SLOT_SIZE // 2
            for cx in _ARC_SLOT_CXS:
                crop = image[cy - half:cy + half, cx - half:cx + half]
                members.append(identify_crop(crop, templates))
        else:
            area_missing = False
            for i in range(1, 5):
                rect = get_area_rect(ctx, f'槽位{idx}头像-{i}', screen_name)
                if rect is None:
                    area_missing = True
                    continue
                crop = image[rect.y1:rect.y2, rect.x1:rect.x2]
                members.append(identify_crop(crop, templates))
            if area_missing:
                members = []   # 该行槽位未建档 → 不返回不完整列表
        nodes.append(NodeInfo(node_idx=idx, weaknesses=weaknesses, members=members))
    return nodes


def node_row_select_point(ctx: SrContext, node_idx: int) -> Point | None:
    """节点行选中点击点(该行敌人预览区中心,非交互控件;1 基 node_idx;缺失 None)。

    点击该行任意非控件区即选中该行(白框态),后续点角色卡填入本行 —— 交互实测
    点预设套用前点行选中生效。
    """
    rect = get_area_rect(ctx, f'槽位{node_idx}头像-1')
    if rect is None:
        return None
    return Point(rect.x1 - 180, rect.y1 + 46)
