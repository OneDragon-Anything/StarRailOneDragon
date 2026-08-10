# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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

if TYPE_CHECKING:
    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext

# 公开 API:re-export 数据(Equipment/EQUIPMENTS/get_equip 来自 cw_equipment_data)+ SIFT(load_equip_templates/read_equips)
# + 穿戴装备 TM 识别(load_equip_tm_grays/read_equipped_below)
# __all__ 告知 ruff 这些 re-export 非 unused(F401)
__all__ = ['Equipment', 'EQUIPMENTS', 'EQUIPMENT_ROSTER', 'get_equip', 'load_equip_templates', 'read_equips',
           'load_equip_tm_grays', 'read_equipped_below', 'ensure_equip_tm_templates']

# R16 P0-1 已解决(2026-08-10):SIFT 段拆到本文件(手维护),数据在 ``cw_equipment_data``(生成器产物)。
# 生成器(``tools/cw/gen_equip_registry.py``)只写 ``cw_equipment_data``,永不覆盖本文件 → 旧覆盖地雷已除。
# ===== 装备视觉识别(cw_equip SIFT;D-27 突破:owned icon 在装备区,D-40 确认多列 col1 x1800-1918 + col2 x1660-1800 + ...)=====
# ①-a 全程 VLM 误判「装饰球体」(D-18~D-26),cw_equip SIFT 才识别到 owned icon(test_equip_recog.py)。
# 教训(D-28/D-38):VLM 不懂游戏,装备 icon 识别易误判(D-18~D-26 误判球体;D-38 把星徽当空槽)。cw_equip SIFT + click ground truth 交叉验证才准;别依赖 VLM 推断游戏事实,游戏知识以用户/图鉴为准。


_EQUIP_SIFT = cv2.SIFT_create()
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
    gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
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
    return clustered


# ===== 穿戴装备识别(below-avatar icon;D-45 路径① multi-scale TM 替 SIFT;D-49 确认 icon 固定尺寸)=====
# below-avatar icon = 角色已穿装备的小图标(头像下方)。**icon 固定 ~32px,不随装备数变(D-49 CV+pi 验)**;
# SIFT patch 天花板对 32px 小 icon 失效(D-45)→ multi-scale TM(98px 模板缩到 ~32px)+ NMS(同位置取最高,
# 防合成材料误匹配:滑轮鞋/折叠小刀同 icon 位置)更稳。实测(D-49):3件全中 0.745-0.781 @ scale0.33;
# threshold 0.6 baseline。D-48「icon 随数量缩/3件分辨率墙」已推翻(根因=harvest 投影法裁切假象)。
_EQUIP_TM_SCALES: tuple[float, ...] = (0.28, 0.30, 0.33, 0.36, 0.39)  # 98px→27-38px 覆盖固定 ~32px icon(D-49)


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
) -> dict[int, list[str]]:
    """每槽 below-avatar 区 multi-scale TM + NMS → ``{slot_idx: [装备名]}``(纯 CV,可离线测)。

    识别**角色已穿装备**(头像下方 icon),与 ``read_equips``(owned 列,未穿)互补。

    **icon 固定 ~32px(D-49)**:below-avatar 装备 icon 不随装备数变(98px 模板 × scale 0.33 ≈ 32px);
    3件态全中(0.745-0.781),无分辨率墙(D-48「icon 缩」已推翻)。multi-scale(0.28-0.39)给 icon
    微变余量;NMS 防同位置多命中(合成材料:滑轮鞋/折叠小刀)。

    :param screen: 备战画面截图(BGR,1080p)。
    :param tmpl_grays: ``load_equip_tm_grays`` 结果(``{name: gray}``,98px 大图模板)。
    :param below_rects: ``[(slot_idx, Rect), ...]`` —— 每槽 below-avatar 搜索区(调用方从 screen_info
        槽 rect 算:avatar 底部下方,icon y 中心 ≈ avatar_y2 + 14,见 ``cw_identity_obs.avatar_to_below``)。
    :param scales: 98px 模板缩放档(覆盖固定 ~32px icon;0.28-0.39 → 27-38px)。
    :param threshold: TM 命中阈值;0.6(实测 top1 0.74+,保守留余量)。
    :param nms_radius: 同位置去重半径(icon 间距 ~35px → 18);同 ``±radius`` 内多命中取 val 最高
        (防合成材料误匹配:滑轮鞋/折叠小刀同位置)。
    :return: ``{slot_idx: [装备名]}``;空槽 / 无命中 → 该 slot 不在 dict。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer / op(并发安全)。
    """
    out: dict[int, list[str]] = {}
    for slot_idx, rect in below_rects:
        crop = cv2.cvtColor(screen[rect.y1:rect.y2, rect.x1:rect.x2], cv2.COLOR_BGR2GRAY)
        raw: list[tuple[str, float, int]] = []  # (name, val, x_in_crop)
        # 98px 大图模板 multi-scale TM(icon 固定 ~32px,D-49;缩到 27-38px 覆盖)
        for name, tgray in tmpl_grays.items():
            th, tw = tgray.shape
            for s in scales:
                nw, nh = int(tw * s), int(th * s)
                if nw < 12 or nh < 12 or nw >= crop.shape[1] or nh >= crop.shape[0]:
                    continue
                resized = cv2.resize(tgray, (nw, nh), interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(crop, resized, cv2.TM_CCOEFF_NORMED)
                _, mx, _, mloc = cv2.minMaxLoc(r)
                if mx >= threshold:
                    raw.append((name, float(mx), mloc[0]))
        # NMS:按 x 位置聚类(±nms_radius),每簇取 val 最高(mini + 98px 合并,mini 高 val 自动赢)
        raw.sort(key=lambda t: -t[1])
        kept: list[tuple[str, float, int]] = []
        for name, val, x in raw:
            if any(abs(x - kx) <= nms_radius for _, _, kx in kept):
                continue
            kept.append((name, val, x))
        if kept:
            out[slot_idx] = [n for n, _, _ in kept]
    return out


def ensure_equip_tm_templates(ctx: SrContext) -> dict[str, MatLike] | None:
    """确保 ctx 缓存 cw_equip TM 模板(98px grays);返 ``grays`` 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_equip_tm_grays``;后续读缓存。recognizer 装备识别的 templates 加载点
    (owned 列 SIFT 模板由 ``equip_all._get_templates`` 另加载,不冲突)。mini 库已删(D-49,icon 固定
    ~32px,大图 scale 0.33 直接覆盖)。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    grays = getattr(ctx, 'cw_equip_tm_grays', None)
    if grays is None:
        equip_dir = Path(__file__).resolve().parents[4] / 'assets' / 'template' / 'cw_equip'
        if not equip_dir.is_dir():
            return None
        grays = load_equip_tm_grays(equip_dir)
        ctx.cw_equip_tm_grays = grays
    return grays
