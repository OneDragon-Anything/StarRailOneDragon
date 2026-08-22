"""cw_equipment 视觉识别(SIFT;**手维护,非生成**)。

数据模型(Equipment / EQUIPMENTS / get_equip)在 ``cw_equipment_data``(由
``tools/cw/gen_equip_registry.py`` 从 ``docs/game/currency_war/data/equipment.md`` 生成)。
本文件只含 SIFT 代码(load_equip_templates / read_equips),``from .cw_equipment_data import`` 数据。
**拆分目的(R16 P0-1)**:生成器只写 ``cw_equipment_data``,永不覆盖本文件 SIFT 段(旧覆盖地雷已除)。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from cv2.typing import MatLike

from sr_od.application.currency_war.cw_equipment_data import (
    EQUIPMENT_ROSTER,
    EQUIPMENTS,
    Equipment,
    get_equip,
)
from sr_od.application.currency_war.cw_observe import cw_log, cw_shot

if TYPE_CHECKING:
    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext

# 公开 API:re-export 数据(Equipment/EQUIPMENTS/get_equip 来自 cw_equipment_data)+ SIFT(load_equip_templates/read_equips)
# + 穿戴装备 TM 识别(load_equip_tm_grays/read_equipped_below)
# __all__ 告知 ruff 这些 re-export 非 unused(F401)
__all__ = ['Equipment', 'EQUIPMENTS', 'EQUIPMENT_ROSTER', 'get_equip', 'load_equip_templates', 'read_equips',
           'load_equip_tm_grays', 'read_equipped_below', 'ensure_equip_tm_templates', 'ensure_equip_sift_templates']

# R16 P0-1 已解决(2026-08-10):SIFT 段拆到本文件(手维护),数据在 ``cw_equipment_data``(生成器产物)。
# 生成器(``tools/cw/gen_equip_registry.py``)只写 ``cw_equipment_data``,永不覆盖本文件 → 旧覆盖地雷已除。
# ===== 装备视觉识别(cw_equip SIFT;D-27 突破:owned icon 在装备区,D-40 确认多列 col1 x1800-1918 + col2 x1660-1800 + ...)=====
# ①-a 全程 VLM 误判「装饰球体」(D-18~D-26),cw_equip SIFT 才识别到 owned icon(test_equip_recog.py)。
# 教训(D-28/D-38):VLM 不懂游戏,装备 icon 识别易误判(D-18~D-26 误判球体;D-38 把星徽当空槽)。cw_equip SIFT + click ground truth 交叉验证才准;别依赖 VLM 推断游戏事实,游戏知识以用户/图鉴为准。


_EQUIP_SIFT = cv2.SIFT_create()  # type: ignore[attr-defined]  # cv2 stubs 不含 SIFT(实际存在)
_EQUIP_MATCHER = cv2.BFMatcher()


def load_equip_templates(equip_dir: Path) -> dict[str, tuple[MatLike, tuple, np.ndarray]]:
    """加载 cw_equip 模板库(``<名>.png`` → SIFT 关键点/描述子)。

    cw_equip 是单 png(非 ``<id>/raw.png`` 结构),直接读 png → gray → SIFT。
    返回 ``{name: (gray, keypoints, descriptors)}``(同 ``load_avatar_templates`` 结构)。
    """
    templates: dict[str, tuple[MatLike, tuple, np.ndarray]] = {}
    for png in sorted(equip_dir.glob('*.png')):
        img = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, desc = _EQUIP_SIFT.detectAndCompute(gray, None)
        if desc is not None and len(kp) >= 4:
            templates[png.stem] = (gray, kp, desc)
    return templates


def read_equips(
    screen: MatLike,
    templates: dict[str, tuple[MatLike, tuple, np.ndarray]],
    equip_rect: tuple[int, int, int, int] = (1620, 90, 1918, 710),  # 多列:col1(x1800-1918)+col2(x1660-1800)+...,D-40
    min_inliers: int = 7,
    cluster_radius: int = 20,
) -> list[tuple[str, tuple[int, int], int]]:
    """装备区 SIFT 匹配 cw_equip → owned icon ``[(name, (cx, cy), inliers)]``。

    equip_rect 默认 **多列装备区**(x1620-1918, y90-710)—— 覆盖 col1(x1800-1918)+col2(x1660-1800)+col3(D-40:用户纠正不止一列,owned 从右往左填充,列满溢左)。
    左半 x1252-1450 = 角色立绘(排除,假匹配装备模板),x1450-1620 = 详情面板(排除);col4-5 若溢到面板区需关面板再扫。thr7 下 x1620-1918 实测 8/8 全命中两列无杂散。
    返回 owned 装备(名 + 原图绝对坐标 + inliers),按 inliers 降序。

    三处健全性(D-28 审查 P0-3 修):
    - centroid 用 RANSAC ``mask`` 标记的 inlier 子集(非 Lowe ``good`` 全部 —— 含 outlier 会偏移 icon 中心);
    - ``cluster_radius`` 簇聚合:同坐标 ±px 内多模板命中归一到 inliers 最高者(防相似装备模板重复命中同一 icon);
    - ``min_inliers=7``(D-39:=10 漏 和平手枪/折叠小刀 inliers=8;7 全命中 7 owned + 阈值 5/3 同 7 无杂散 → 稳)。
      D-28 设 10 为「降假阳性」,但假阳性根因(空槽)D-38 作废(装备列无空槽)→ 无假阳风险,降阈值安全。待跨局面验证阈值 7 无杂散。

    纯读(只 SIFT screen + templates,不写 session/全局),可进 recognizer / op。
    """
    x1, y1, x2, y2 = equip_rect
    zone = screen[y1:y2, x1:x2]
    gray = cv2.cvtColor(zone, cv2.COLOR_RGB2GRAY)  # sr_od screen RGB(D-52 同类,read_equips 也通道错)
    kp_z, desc_z = _EQUIP_SIFT.detectAndCompute(gray, None)
    raw_hits: list[tuple[str, tuple[int, int], int]] = []
    if desc_z is None or len(kp_z) < 4:
        return raw_hits
    for name, (_tgray, tkp, tdesc) in templates.items():
        matches = _EQUIP_MATCHER.knnMatch(tdesc, desc_z, k=2)
        good = [mm[0] for mm in matches if len(mm) >= 2 and mm[0].distance < 0.75 * mm[1].distance]
        if len(good) >= 8:
            src = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32([kp_z[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
            if mask is None:
                continue
            inliers = int(mask.sum())
            if inliers < min_inliers:
                continue
            # centroid 用 RANSAC inlier(非全部 good —— outlier 偏移中心,审查 P0-3①)
            inlier_pts = [kp_z[good[i].trainIdx].pt for i in range(len(good)) if mask[i]]
            cx = int(np.median([p[0] for p in inlier_pts])) + x1
            cy = int(np.median([p[1] for p in inlier_pts])) + y1
            raw_hits.append((name, (cx, cy), inliers))
    # 簇聚合:同坐标 cluster_radius 内多命中归一到 inliers 最高(审查 P0-3③)
    raw_hits.sort(key=lambda h: -h[2])  # inliers 降序,高者优先保留
    clustered: list[tuple[str, tuple[int, int], int]] = []
    for name, (cx, cy), inliers in raw_hits:
        if any(abs(cx - ocx) <= cluster_radius and abs(cy - ocy) <= cluster_radius
               for _, (ocx, ocy), _ in clustered):
            continue  # 已被更高 inliers 命中吞并(去重)
        clustered.append((name, (cx, cy), inliers))
    _check_owned_order(clustered, screen, equip_rect)
    return clustered


#: owned 栏同一行的 cy 容差(行距 ≈ 98px = owned icon 大图尺寸,D-49;行内抖动实测 ~10px)
_OWNED_ROW_DY: int = 45


def _owned_order_anomaly(pts: list[tuple[int, int]]) -> str | None:
    """owned 栏**行内**跳格检测(纯函数;2026-08-18 治本重构)。

    布局(D-40/D-49):多列网格,行内从右到左连续填充(列步距 ~51px),行距 ~98px。
    **跳格只在行内有意义**:某行相邻 icon 的 x 间距 > 1.8×行内中位步距 = 该行有
    漏检槽位(识别到"后面"装备但"前面"位置空)。
    旧实现(欧氏间距全局中位)把**行尾→行首的换行跳变**误判为跳格 —— 换行时
    x 从左列跳回右列(live 2026-08-18 10:45/10:47 实锤:row1 两件 + row2 两件,
    [1]->[2] 间距 220 vs 中位 78 = 每逢跨行必误报,遥测噪声)。
    ⚠️ 已知盲区(r58 review P2-5,纯遥测灵敏度限制):行内恰 3 icon 且漏 1 槽时
    gaps=[s,2s] 中位=2s 阈值 3.6s 检不出(需 ≥4 icon 中位才稳);接受现状。
    """
    if len(pts) < 4:
        return None   # 太少无法判连续性
    srt = sorted(pts, key=lambda p: (p[1], -p[0]))
    # 行聚类:cy 与当前行末点差 ≤ _OWNED_ROW_DY → 同行;否则新行
    rows: list[list[tuple[int, int]]] = []
    for p in srt:
        if rows and abs(p[1] - rows[-1][-1][1]) <= _OWNED_ROW_DY:
            rows[-1].append(p)
        else:
            rows.append([p])
    for row in rows:
        if len(row) < 3:
            continue   # 两点无中位可判(首行独立布局常见,直接放行)
        xs = sorted(p[0] for p in row)
        gaps = [b - a for a, b in zip(xs, xs[1:], strict=False)]
        med = sorted(gaps)[len(gaps) // 2]
        if med <= 0:
            continue
        for i, g in enumerate(gaps):
            if g > 1.8 * med:
                return (f'跳格 行内x[{xs[i]}]->[{xs[i + 1]}] 间距{g}>1.8×中位{med}'
                        f'(该行可能漏检)')
    return None


def _check_owned_order(
    equips: list[tuple[str, tuple[int, int], int]],
    screen: MatLike,
    equip_rect: tuple[int, int, int, int],
) -> None:
    """owned 栏顺序异常检测(诊断留证,无行为影响):行内跳格 = 前面可能漏检,
    记 ``[cw!]`` + 存 owned 栏截图。判定逻辑纯函数化 → ``_owned_order_anomaly``。"""
    pts = [(e[1][0], e[1][1]) for e in equips]
    anomaly = _owned_order_anomaly(pts)
    if anomaly is None:
        return
    x1, y1, x2, y2 = equip_rect
    cw_log('read_equips', step='order', target='owned', attn=True,
           anomaly=anomaly, count=len(equips),
           shot=cw_shot(screen[y1:y2, x1:x2], 'owned_anomaly'))


# ===== 穿戴装备识别(below-avatar icon;D-45 路径① multi-scale TM 替 SIFT;D-49 确认 icon 固定尺寸)=====
# below-avatar icon = 角色已穿装备的小图标(头像下方)。**icon 固定 ~32px,不随装备数变(D-49 CV+pi 验)**;
# SIFT patch 天花板对 32px 小 icon 失效(D-45)→ multi-scale TM(98px 模板缩到 ~32px)+ NMS(同位置取最高,
# 防合成材料误匹配:滑轮鞋/折叠小刀同 icon 位置)更稳。实测(D-49):3件全中 0.745-0.781 @ scale0.33;
# threshold 0.6 baseline。D-48「icon 随数量缩/3件分辨率墙」已推翻(根因=harvest 投影法裁切假象)。
_EQUIP_TM_SCALES: tuple[float, ...] = (0.30, 0.33, 0.35, 0.37)  # 98px→29-36px;icon 32-34px 随位置变(梯形视角:前排~32px/后排最右~34px),0.33+0.35 覆盖两 best(D-51:0.35 抓后排-6 武器大师,step 0.03 会漏)
# below-avatar icon 横排布局(D-49 CV 验):icon 相对 below cx 的 offset,件数决定。
# 1件{0} / 2件{-21,+21} / 3件{-43,0,+43};候选点(5个)覆盖所有可能。
_EQUIP_CANDIDATES: tuple[int, ...] = (-43, -21, 0, 21, 43)
_EQUIP_LAYOUTS: tuple[tuple[int, ...], ...] = ((-43, 0, 43), (-21, 21), (0,))  # 3件/2件/1件,大到小(完整布局优先)


def load_equip_tm_grays(equip_dir: Path) -> dict[str, MatLike]:
    """加载 cw_equip 模板为 gray dict(``{name: gray}``;TM 用,非 SIFT 的 keypoints/descriptors)。

    与 ``load_equip_templates`` 互补:本函数返简单 gray(TM matchTemplate 用),后者返 SIFT 预计算
    (keypoints/descriptors,read_equips owned 列用)。两套并存 —— owned 列 icon 大(~98px,SIFT 稳);
    below-avatar mini icon 小(~35px,SIFT 失效用 TM)。
    """
    grays: dict[str, MatLike] = {}
    for png in sorted(equip_dir.glob('*.png')):
        img = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        grays[png.stem] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return grays


def read_equipped_below(
    screen: MatLike,
    tmpl_grays: dict[str, MatLike],
    below_rects: list[tuple[int, Rect]],
    scales: tuple[float, ...] = _EQUIP_TM_SCALES,
    threshold: float = 0.6,
    nms_radius: int = 18,
    miss_threshold: float = 0.55,
) -> dict[int, list[str]]:
    """每槽 below-avatar 区 multi-scale TM + NMS → ``{slot_idx: [装备名]}``(纯 CV,可离线测)。

    识别**角色已穿装备**(头像下方 icon),与 ``read_equips``(owned 列,未穿)互补。

    **icon ~32-34px 随位置变(D-49/D-51)**:below-avatar 装备 icon 不随装备数变,但随角色位置/梯形视角
    略变(前排 ~32px / 后排最右 ~34px)。multi-scale(0.30/0.33/0.35/0.37 → 29-36px)枚举覆盖,每个 icon
    在最接近 scale 命中最高 val(D-51:漏 0.35 致后排-6 武器大师漏);NMS 防同位置多命中(合成材料:滑轮鞋/折叠小刀)。

    :param screen: 备战画面截图(RGB,1080p;sr_od ``cv2_utils.read_image`` 约定,非 BGR)。
    :param tmpl_grays: ``load_equip_tm_grays`` 结果(``{name: gray}``,98px 大图模板)。
    :param below_rects: ``[(slot_idx, Rect), ...]`` —— 每槽 below-avatar 搜索区(调用方从 screen_info
        槽 rect 算:avatar 底部下方,icon y 中心 ≈ avatar_y2 + 14,见 ``cw_identity_obs.avatar_to_below``)。
    :param scales: 98px 模板缩放档(覆盖 ~32-34px icon;0.30-0.37 → 29-36px,D-51)。
    :param threshold: TM 命中阈值;0.6(实测 top1 0.74+,保守留余量)。
    :param nms_radius: 同位置去重半径(icon 间距 ~35px → 18);同 ``±radius`` 内多命中取 val 最高
        (防合成材料误匹配:滑轮鞋/折叠小刀同位置)。
    :param miss_threshold: MISS 日志阈值;val 在 [miss_threshold, threshold) 的近命中记 MISS(可能漏检,
        如 D-51 武器大师后排-6 val0.57)。0.55 避低 val 噪声。MISS 经 ``cw_observe.cw_log`` 记(``[cw!]``),
        grep ``\\[cw!\\].*MISS`` 找;存 below crop(``cw_observe.cw_shot``)定位根因。
    :return: ``{slot_idx: [装备名]}``;空槽 / 无命中 → 该 slot 不在 dict。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer / op(并发安全)。
    """
    out: dict[int, list[str]] = {}
    for slot_idx, rect in below_rects:
        crop = cv2.cvtColor(screen[rect.y1:rect.y2, rect.x1:rect.x2], cv2.COLOR_RGB2GRAY)  # sr_od screen 是 RGB(cv2_utils.read_image),非 BGR
        raw: list[tuple[str, float, int]] = []  # (name, val, icon_center) 命中(>=threshold)
        near: dict[str, float] = {}  # 近命中(name->max val, miss_threshold<=val<threshold),MISS 日志用
        # 大图模板 multi-scale TM(icon ~32-34px 随位置变,D-49/D-51;缩到 29-36px 覆盖)。
        # scales 语义 = 相对 98px 基准;混合库(plaza 官方烘焙已统一 98px,用户 2026-08-15 定)
        # 归一换算保留作防御(模板若非 98 尺寸仍等效目标像素)。
        for name, tgray in tmpl_grays.items():
            th, tw = tgray.shape
            k = 98.0 / max(tw, th)   # 模板宽→98 基准的换算系数
            for s in scales:
                nw, nh = int(tw * s * k), int(th * s * k)
                if nw < 12 or nh < 12 or nw >= crop.shape[1] or nh >= crop.shape[0]:
                    continue
                resized = cv2.resize(tgray, (nw, nh), interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(crop, resized, cv2.TM_CCOEFF_NORMED)
                _, mx, _, mloc = cv2.minMaxLoc(r)
                if mx >= threshold:
                    raw.append((name, float(mx), mloc[0] + nw // 2))  # icon 中心(模板左 + 半宽)
                elif mx >= miss_threshold and mx > near.get(name, 0.0):
                    near[name] = float(mx)
        # NMS:按 icon 中心聚类(±nms_radius),每簇取 val 最高(同 icon 多模板/多尺度命中去重)
        raw.sort(key=lambda t: -t[1])
        kept: list[tuple[str, float, int]] = []  # (name, val, icon_center)
        for name, val, icon_center in raw:
            if any(abs(icon_center - kc) <= nms_radius for _, _, kc in kept):
                continue
            kept.append((name, val, icon_center))
        # 布局约束(D-49):icon 中心归候选点(cx±43/±21/0),取最大完整 1/2/3件布局,剔孤立误检 + 缺候选 MISS。
        equipped = _select_equipped_layout(kept, crop.shape[1] // 2, slot_idx, screen, rect)
        if equipped:
            out[slot_idx] = equipped
        # icon 数守卫:角色 below 最多3件,>3 = 误检/邻槽串入
        if len(kept) > 3:
            cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
                   anomaly=f'icon数{len(kept)}>3(误检/邻槽串入)', equips=str([n for n, _, _ in kept]),
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'over3_slot{slot_idx}'))
        # MISS 日志:近命中(val 刚低于 threshold)可能是漏检(如 D-51 武器大师后排-6 val0.57<0.6)。
        # ⚠️ 分级([cw!]=需关注/[cw]=普通,语义详 ``cw_observe``):清晰读(val_top≥0.7)的 near-MISS 是被拒候选
        # (噪声,非漏检)→ [cw] 普通;疑似漏检(val_top<0.7 / kept 空)→ [cw!] 需关注。
        # grep `\[cw!\].*MISS` 找真漏检;`\[cw\].*MISS` 看被拒候选(诊断)。miss_threshold 0.55 避低 val 噪声。
        if near:
            kept_names = {n for n, _, _ in kept}
            miss_items = sorted(((n, v) for n, v in near.items() if n not in kept_names), key=lambda t: -t[1])
            if miss_items:
                miss_str = ','.join(f'{n}({v:.2f})' for n, v in miss_items[:5])
                val_top = kept[0][1] if kept else 0.0
                shot = cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'miss_slot{slot_idx}')
                cw_log('read_equipped', target=f'slot={slot_idx}', attn=val_top < 0.7,
                       equips=str([n for n, _, _ in kept]), val_top=f'{val_top:.2f}',
                       MISS=f'[{miss_str}]', shot=shot)
    return out


def _select_equipped_layout(
    kept: list[tuple[str, float, int]],
    below_cx: int,
    slot_idx: int,
    screen: MatLike,
    rect: Rect,
) -> list[str]:
    """布局约束选装备(D-49):kept icon 中心归候选点(cx±43/±21/0),取最大完整 1/2/3件布局。

    - icon 中心归最近候选(±11 内);非候选 = 孤立(误检,不取)。
    - 命中候选取最大完整布局(3件{-43,0,+43} > 2件{-21,+21} > 1件{0};候选 ⊆ 命中)→ 该布局装备。
    - 更大布局部分中(缺候选)= MISS(漏检)``[cw!]``;无完整布局 = 异常 ``[cw!]`` + 截图。
    """
    cand_name: dict[int, str] = {}
    for name, _val, icon_center in kept:
        off = icon_center - below_cx
        nearest = min(_EQUIP_CANDIDATES, key=lambda c: abs(c - off))
        if abs(nearest - off) <= 11:
            cand_name.setdefault(nearest, name)  # NMS 已 val 降序,首个=最高
    hit = set(cand_name)
    chosen = next((lay for lay in _EQUIP_LAYOUTS if set(lay) <= hit), None)
    if chosen is not None:
        return [cand_name[o] for o in chosen]
    # 无完整布局(D-61):CW 每角色最多3件,1/2/3件布局覆盖全部合法配置;无完整布局 = 误检
    # (D-61:完美投影仪 val0.62 单件落 +21 候选,非合法布局 → 空槽误匹配)。返 [] 不返 fallback 候选
    # (防 recognizer/P0-2 把不可靠候选当 occupied —— D-61 实测致 front_equips 假阳)。anomaly + MISS 日志保留(诊断)。
    if hit:
        cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
               anomaly=f'无完整1/2/3件布局(命中候选{sorted(hit)})→判空(误检,不返)',
               equips=str([cand_name[o] for o in sorted(cand_name)]),
               shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'nolayout_slot{slot_idx}'))
    # MISS:更大布局部分中(缺候选 = 漏检)
    for lay in _EQUIP_LAYOUTS:
        partial = set(lay) & hit
        if partial and not set(lay) <= hit:
            missing = [c for c in lay if c not in hit]
            cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
                   MISS=f'布局{lay}缺候选{missing}(漏检)',
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'layoutmiss_slot{slot_idx}'))
            break
    return []


def ensure_equip_tm_templates(ctx: SrContext) -> dict[str, MatLike] | None:
    """确保 ctx 缓存 cw_equip TM 模板(98px grays);返 ``grays`` 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_equip_tm_grays``;后续读缓存。recognizer 装备识别的 templates 加载点
    (owned 列 SIFT 模板由 ``equip_all._get_templates`` 另加载,不冲突)。mini 库已删(D-49/D-51,icon
    ~32-34px 随位置变,大图 multi-scale 0.30-0.37 覆盖)。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    grays = getattr(ctx, 'cw_equip_tm_grays', None)
    if grays is None:
        base = Path(__file__).resolve().parents[4] / 'assets' / 'template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(plaza 官方 59 + 手工补充 96;生成器 gen_plaza_chars.py 产物)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'   # 回退:旧手工库
        if not equip_dir.is_dir():
            return None
        grays = load_equip_tm_grays(equip_dir)
        ctx.cw_equip_tm_grays = grays
    return grays


def ensure_equip_sift_templates(ctx: SrContext) -> dict[str, tuple[MatLike, tuple, np.ndarray]] | None:
    """确保 ctx 缓存 cw_equip SIFT 模板(owned 列 ``read_equips`` 用);返 ``templates`` 或 None(目录缺)。

    首次 ``load_equip_templates`` 缓存 ``ctx.cw_equip_sift_templates``;后续读缓存。与
    ``ensure_equip_tm_templates``(below-avatar TM grays)互补 —— 本函数返 SIFT 预计算(keypoints/descriptors,
    owned 列大 icon ~98px SIFT 稳),TM 版返简单 gray(below mini icon ~32px TM 稳)。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    templates = getattr(ctx, 'cw_equip_sift_templates', None)
    if templates is None:
        base = Path(__file__).resolve().parents[4] / 'assets' / 'template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(同 ensure_equip_tm_templates)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'   # 回退:旧手工库
        if not equip_dir.is_dir():
            return None
        templates = load_equip_templates(equip_dir)
        ctx.cw_equip_sift_templates = templates
    return templates
