"""货币战争角色识别:SIFT 特征匹配模板库(纯 CV;库由调用方传 ``avatar_dir``,生产用立绘库)。

**生产实际用的库(2026-08-17 起)**:``deploy_bench._get_templates`` 等加载
``assets/template/currency_war/portrait_plaza``(**官方立绘库**,plaza big_icon 烘焙,72 角色,
中文规范名 key,含变体分开取:姬子/姬子·启行、丹恒·饮月/丹恒·腾荒、刃/千冶·刃、银狼/银狼LV.999;
``tools/cw/gen_plaza_chars.py`` 生成)。``resolve_char_name``
对中文 key 直接返(立绘库),对英文 id 映射(脸库),两库兼容。旧手采库 ``character_cw_portrait``
(白框法)与其前身 ``currency_war_portrait``(R/B 存反,AGENTS.local 图像通道约定所记事故)已于
2026-08-17 删除,plaza 库为唯一立绘库。

⚠️ **识别可靠性:实测初步可用(2026-08-09 D-22)**:离线对 r1-8 备战截图跑 SIFT(`test_portrait_recog.py`),
立绘库对 **6/6 有角色槽全命中**(inliers 29-48),空槽 None(best=0-1 不误识别)→ **立绘库可靠,
推翻脸库旧结论**(脸库只 4 角色强命中)。下方「4 角色强命中」是 character_avatar(脸库)旧实测,仅作
下界参考。**待补**:更多样本(尤其共脸变体 姬子/姬子·启行 能否靠服装区分)+ 角色名 ground truth
(详情面板 OCR)。

**2026-08-06 旧实测(character_avatar 脸库,仅作下界参考)**:脸近景库对面部独特角色强命中(4/4:
佩拉/黑塔/Saber/藿藿,best inliers 23-30 vs 第二名 3-4);配饰/帽子重角色、货币战争专属变体待核。
此结论「脸库够用、无需半身模板」与代码实际加载立绘库不符 —— 以代码为准(立绘库)。

匹配要点:``min_inliers`` 最低内点 + ``ambiguity_ratio`` 歧义比过滤低置信结果(空槽位/非角色特征
少 → 自然落 None,无需额外「槽位是否填充」预判)。

本模块**纯 CV**(无 ctx/screen_info 依赖,可离线测):``load_avatar_templates`` 预计算 SIFT 关键点/
描述子;``identify_character`` 返回 ``(avatar_id, inliers)``,avatar_id = 模板目录名(立绘库=中文
规范名如 ``藿藿``;脸库=主游英文 id 如 ``pela``;生产用立绘库)。avatar_id → 货币战争规范名映射在
``cw_identity_obs.resolve_char_name``。

部署/循环 op 用本模块时,模板由调用方加载传入(``deploy_bench`` 加载立绘库缓存到
``ctx.cw_portrait_templates``);离线测试用 ``load_avatar_templates`` 从磁盘加载。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.utils.file_utils import get_project_root

# SIFT 检测器(与 one_dragon.utils.cv2_utils.feature_detector 同源)
_SIFT = cv2.SIFT_create()  # type: ignore[attr-defined]  # cv2 stubs 不含 SIFT(实际存在,opencv-python>=4.4 内置)
_MATCHER = cv2.BFMatcher()

AvatarTemplates = dict[str, tuple[MatLike, tuple, np.ndarray]]
"""{char_id: (gray, keypoints, descriptors)}"""


def load_avatar_templates(avatar_dir: Path) -> AvatarTemplates:
    """加载目录下所有角色头像模板,预计算 SIFT 关键点/描述子。

    模板文件:每角色目录 ``raw.png``(主模板,官方图鉴 art)+ 可选变体
    ``raw_*.png``(现场采集 art,如商店卡立绘与图鉴 pose 不同时补采样;
    键带 ``#k`` 后缀,识别返回时剥离——见 ``identify_character`` 返回值)。
    2026-08-26 run20 停机事故实证:开拓者·欢愉图鉴 art 对商店卡仅 5 内点
    (阈值 10),玩家名遮挡卡名时 SIFT 是唯一通道 → 变体机制必要。

    若同目录存在 ``mask.png``(官方库烘焙产物,alpha 二值掩码),SIFT 只在掩码区提特征
    (背景色不进描述子;ADR 见烘焙生成器 tools/cw/gen_plaza_chars.py)。无 mask 则全图(旧手采库兼容)。

    **变体模板逐文件掩码**(2026-08-28,ADR-0452):变体 ``raw_<域>.png`` 优先读同目录
    ``mask_<域>.png``(如 ``raw_board.png`` ↔ ``mask_board.png``),缺失再退 ``mask.png``
    (形状须与该文件一致,不一致按无掩码)。根因:``mask.png`` 尺寸只配主档 ``raw.png``,
    变体形状必然失配 → 变体曾整体无掩码入库,卡框/角标等**跨卡恒定的 UI 铬特征**进描述子,
    在任意同域裁片上互撞(那刻夏被 艾丝妲 board 变体的卡框内点 13 抬成歧义假拒,实测)。
    ``银枝/mask_plaza.png`` 是该约定的既有资产(此前加载器从未读过)。
    """
    templates: AvatarTemplates = {}
    for child in sorted(avatar_dir.iterdir()):
        if not child.is_dir():
            continue
        variant_idx = 0
        for raw in sorted(child.glob('raw*.png')):
            if raw.stem != 'raw' and (not raw.name.startswith('raw_') or 'bak' in raw.stem):
                continue   # raw_bak*.png 等备份文件不进库;变体=raw_*.png(现场采样)
            img = cv2.imdecode(np.fromfile(str(raw), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mask_file = (child / 'mask.png' if raw.stem == 'raw'
                         else child / f'mask_{raw.stem.removeprefix("raw_")}.png')
            if not mask_file.is_file():
                mask_file = child / 'mask.png'   # 变体无专属掩码 → 退主档掩码(形状仍须匹配)
            mask = None
            if mask_file.is_file():
                m = cv2.imdecode(np.fromfile(str(mask_file), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if m is not None and m.shape == gray.shape:
                    mask = m
            kp, desc = _SIFT.detectAndCompute(gray, mask)
            key = child.name if variant_idx == 0 else f'{child.name}#{variant_idx}'
            templates[key] = (gray, kp, desc)
            variant_idx += 1
    return templates


def _ratio_good(tdesc, sdesc, knn: float = 0.75) -> list:
    """ratio test 通过的 good 匹配(免 RANSAC;两阶段第一阶段)。"""
    matches = _MATCHER.knnMatch(tdesc, sdesc, k=2)
    good: list = []
    for t in matches:
        if len(t) < 2:
            continue
        m, n = t
        if m.distance < knn * n.distance:
            good.append(m)
    return good


def _ransac_homography(skp, tkp, good: list) -> tuple[int, MatLike | None, list[int]]:
    """good 匹配的 RANSAC:返 (内点数, homography, 内点在 good 中的下标表)。

    内点数语义与旧 ``_ransac_inliers`` 一致(mask None → good 数,下标=全量)。
    下标表供 ``identify_hypotheses`` 做核内内点计数(ADR-0452)。
    """
    if len(good) < 4:
        return len(good), None, list(range(len(good)))
    tp = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    sp = np.float32([skp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    h_mat, mask = cv2.findHomography(tp, sp, cv2.RANSAC, 5.0)
    if mask is None:
        return len(good), h_mat, list(range(len(good)))
    idxs = [i for i, v in enumerate(mask.ravel()) if v == 1]
    return len(idxs), h_mat, idxs


def _ransac_inliers(skp, tkp, good: list) -> int:
    """good 匹配的 RANSAC 内点数(mask None → good 数,同旧语义)。"""
    return _ransac_homography(skp, tkp, good)[0]


def ransac_locate_x(tkp, skp, good: list, tmpl_gray: MatLike, x_off: int = 0) -> float | None:
    """SIFT 单点定位:good 匹配的 homography 把**模板中心**投影到场景 → 场景 x 坐标。

    与 ``_ransac_inliers`` 同向(query=模板 / train=场景);部分可见也能定位
    (homography 拟合整体变换,不依赖模板完整在画)。定位失败(匹配不足/homography
    奇异)→ None。``x_off`` = band 在全图中的 x 偏移(band 裁切定位用)。
    用途:系统单位恒最右布局自检(ADR-0281,cw_identity_obs.check_system_unit_layout)。
    """
    if len(good) < 8:
        return None
    tp = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    sp = np.float32([skp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    h_mat, _ = cv2.findHomography(tp, sp, cv2.RANSAC, 5.0)
    if h_mat is None:
        return None
    th, tw = tmpl_gray.shape[:2]
    p = h_mat @ np.array([tw / 2.0, th / 2.0, 1.0])
    if abs(p[2]) < 1e-6:
        return None
    return float(p[0] / p[2]) + x_off


def identify_hypotheses(slot_img: MatLike, templates: AvatarTemplates,
                        min_good: int = 4,
                        core_range: tuple[float, float] | None = None,
                        ) -> list[tuple[str, int, float, int]]:
    """全库匹配假设列表 ``[(模板键, 内点, 投影模板中心 x, 核内内点)]``(无决策,全扫描)。

    与 ``identify_character`` 的区别:不设 min_inliers/歧义比、不做两阶段剪枝 ——
    返回每个 good≥``min_good`` 模板的完整假设,供调用方做**位置感知裁决**
    (部署排中心归属门,ADR-0452:邻卡渗漏假设的中心落在槽核外,凭内点数
    无法与真身区分、凭几何一眼可判)。全扫描(无剪枝)是位置裁决的前提:
    被剪枝者可能是「渗漏高内点」假设,剪掉就丢失了它的几何证据。
    耗时:每模板一次 RANSAC(≤83 次/槽),部署排逐槽调用可接受。

    :param slot_img: 裁片(RGB,同 identify_character 约定)。
    :param core_range: 裁片坐标系 ``(x1, x2)``,**核内内点** = 场景点 x 落在该区间
        的 RANSAC 内点数(证据落点计数)。渗漏/跨域噪声假设的特征:中心可能
        蹭进核(如噪声中心贴核边缘),但**证据质量**大多落在核外 —— 裁决计
        核内内点,双保险(ADR-0452 佩佩局空槽 忘归人 21 内点案)。
    :return: 按内点降序;homography 奇异/模板退化者不进列表。
    """
    gray = cv2.cvtColor(slot_img, cv2.COLOR_RGB2GRAY)
    skp, sdesc = _SIFT.detectAndCompute(gray, None)
    if sdesc is None or len(skp) < 4:
        return []
    out: list[tuple[str, int, float, int]] = []
    for cid, (tg, tkp, tdesc) in templates.items():
        if tdesc is None or len(tkp) < 4:
            continue
        good = _ratio_good(tdesc, sdesc)
        if len(good) < min_good:
            continue
        inl, h_mat, inl_idxs = _ransac_homography(skp, tkp, good)
        if h_mat is None:
            continue
        # 退化 homography 守卫(ADR-0452):RANSAC 可能把一片模板点映射到
        # 单个场景点(实测:佩佩局空槽 忘归人 21 内点中 19 点塌缩到同一
        # 场景坐标)—— 此时内点数与投影中心都是伪值。内点场景坐标去重后
        # 不足 ``_HYP_MIN_UNIQUE_INLIERS`` 个 → 无几何证据,丢弃。
        scene_pts = {(round(float(skp[good[i].trainIdx].pt[0])),
                      round(float(skp[good[i].trainIdx].pt[1])))
                     for i in inl_idxs}
        if len(scene_pts) < _HYP_MIN_UNIQUE_INLIERS:
            continue
        p = h_mat @ np.array([tg.shape[1] / 2.0, tg.shape[0] / 2.0, 1.0])
        if abs(p[2]) < 1e-6:
            continue
        if core_range is not None:
            inl_core = sum(1 for i in inl_idxs
                           if core_range[0] <= skp[good[i].trainIdx].pt[0] <= core_range[1])
        else:
            inl_core = inl
        out.append((cid, inl, float(p[0] / p[2]), inl_core))
    out.sort(key=lambda t: -t[1])
    return out


#: 假设退化守卫:内点场景坐标去重下限(见 identify_hypotheses 内注释)。
#: 真假设的内点散布在整卡(几十个不同点);8 = 远低于真假设、高于塌缩型
#: 伪假设(实测伪假设 3 个唯一点)的保守值。
_HYP_MIN_UNIQUE_INLIERS: int = 8


def _inliers(skp, sdesc, tkp, tdesc, knn: float = 0.75) -> int:
    """SIFT + ratio test + RANSAC 内点数(越大越匹配;<4 good 直接返回)。

    单模板完整算(旧路径;``identify_character`` 已不走此函数,改两阶段
    惰性 RANSAC)。保留作单一语义参考与离线诊断。
    """
    if sdesc is None or tdesc is None or len(skp) < 4 or len(tkp) < 4:
        return 0
    good = _ratio_good(tdesc, sdesc, knn)
    return _ransac_inliers(skp, tkp, good)


def identify_character(
    slot_img: MatLike,
    templates: AvatarTemplates,
    min_inliers: int = 10,
    ambiguity_ratio: float = 1.5,
    return_key: bool = False,
) -> tuple[str | None, int]:
    """识别槽内角色。

    :param slot_img: 槽位裁图(**RGB**,sr_od 框架截图约定;screencapper BGRA2RGB,cv2_utils.read_image 同)。
    :param templates: :func:`load_avatar_templates` 的结果(op 集成时由 ctx.ih 预加载传入)。
    :param min_inliers: 最低内点数,低于此判 unknown(配饰角色/非角色会落这)。
    :param ambiguity_ratio: best 需 ≥ ratio × second 才算非歧义。
    :param return_key: True 时命中返回**原始模板键**(可能带 ``#k`` 变体后缀,
        如 ``卡芙卡#1``=现场采集变体),False(默认)返回剥离后的规范名 ——
        2026-08-26 佩佩局:部署排需区分命中源(plaza 官方 art 跨域匹配在
        棋盘背景上有 11-26 内点假阳带,现场变体才是可靠信号),调用方
        (cw_identity_obs.identify_slots live_only)用。
    :return: ``(char_id or None, best_inliers)``。None = 未知 / 歧义 / 低于阈值。

    歧义仲裁(r75 狸猫兄弟案):**同型异色单位对**(狸小虎蓝/狸小龙红,同投资策略「龙虎
    兄弟狸」造型仅色异)灰度 SIFT 形状互撞 —— ratio 1.28 < 1.5 判歧义 None,但两者的
    **色相签名是决定性的**(蓝狸 B≫R / 红狸 R>B,模板与现场实测一致)。歧义时若 top2
    恰为已知色相对(RED_HUE_PAIRS),按 slot_img 的色相差仲裁 —— SIFT 定「是这对兄弟」,
    色相定「是哪只」。
    """
    gray = cv2.cvtColor(slot_img, cv2.COLOR_RGB2GRAY)   # sr_od screen 是 RGB(screencapper BGRA2RGB;D-52 装备侧同类修,本处 2026-08-19 补)
    skp, sdesc = _SIFT.detectAndCompute(gray, None)
    if sdesc is None or len(skp) < 4:
        # 旧路径此况全模板返 0 → best=0 < min_inliers;等价直返
        return None, 0
    # 两阶段惰性 RANSAC(2026-08-24 性能优化;决策语义与旧全扫逐位等价,
    # ADR-0247):
    # 阶段1 全模板 ratio-test good 数(免 RANSAC,knnMatch 是 BF 高效项);
    # 阶段2 按 good 降序惰性 RANSAC,剪枝 g ≤ best/ambiguity_ratio ——
    #   内点 ≤ good(RANSAC 只减不加),被剪者不可能超 best、也不可能
    #   在歧义触发时占第二(歧义需 second > best/ratio,被剪者 g ≤
    #   best/ratio 恒不满足)→ best/second_id/歧义判定与全扫一致。
    #   剪枝记录 upper bound(g)不参与任何决策路径。ratio≤1 时不剪
    #   (threshold 退化会破等价,防御)。
    goods: list[tuple[str, list]] = []
    for cid, (_g, tkp, tdesc) in templates.items():
        if tdesc is None or len(tkp) < 4:
            goods.append((cid, []))
            continue
        goods.append((cid, _ratio_good(tdesc, sdesc)))
    goods.sort(key=lambda t: -len(t[1]))
    scores: list[tuple[str, int]] = []
    best: int = 0
    _prune_ok = ambiguity_ratio > 1.0
    for cid, good in goods:
        g = len(good)
        if g < 4:
            scores.append((cid, g))
            continue
        if _prune_ok and best > 0 and g <= best / ambiguity_ratio:
            scores.append((cid, g))   # upper bound;决策不可达(见上)
            continue
        inl = _ransac_inliers(skp, templates[cid][1], good)
        scores.append((cid, inl))
        if inl > best:
            best = inl
    return _resolve_best(scores, slot_img, min_inliers, ambiguity_ratio, return_key)


def _resolve_best(scores: list[tuple[str, int]], slot_img: MatLike,
                  min_inliers: int, ambiguity_ratio: float,
                  return_key: bool) -> tuple[str | None, int]:
    """分数表 → 决策(阈值/歧义比/色相仲裁),identify_character 的决策尾段。

    从 identify_character 抽出共用:部署排中心归属门(ADR-0452)先按几何筛候选,
    再用**同一套**阈值/歧义语义定夺 —— 两路径决策语义单一源。

    :param scores: ``[(模板键, 分数)]``(内部降序排序,调用方无需预排)。
    :param slot_img: 裁片(RGB;色相仲裁用)。
    :return: ``(模板键 or None, best 分数)``;None = 未知 / 歧义 / 低于阈值。
    """
    scores.sort(key=lambda t: -t[1])
    if not scores:
        return None, 0
    best_id, best = scores[0]
    second_id, second = (scores[1] if len(scores) > 1 else ('', 0))
    if best < min_inliers:
        return None, best
    # 变体模板键(#k 后缀)剥离:同一角色的多 art 模板互不构成「歧义」——
    # 同 cid 变体在 top2 时取高者即最终答案(2026-08-26 变体机制)。
    _base = best_id.split('#')[0]
    if second > 0 and best < ambiguity_ratio * second:
        if second_id.split('#')[0] != _base:
            # r75 色相仲裁:top2 是已知同型异色对 → 色相差定夺
            arb = _hue_arbitrate(slot_img, _base, second_id.split('#')[0])
            if arb is not None:
                return arb, best
            return None, best
    return (best_id if return_key else _base), best


#: 同型异色对(冷色成员, 暖色成员)——歧义时按 slot 色相偏向哪边仲裁(r75 狸猫兄弟)
_RED_HUE_PAIRS: dict[frozenset[str], str] = {
    frozenset({'狸小虎', '狸小龙'}): '狸小虎',   # 值 = 冷色(蓝)成员名
}


def _hue_arbitrate(slot_img: MatLike, a: str, b: str) -> str | None:
    """歧义 top2 恰为已知色相对时,按 slot 色相(B−R 均值差)返回胜者;非已知对 → None。

    判据(狸猫局实测):蓝狸现场 B−R ≈ +26 / 红狸 ≈ −1~−3(模板 +24 / −3);阈值取 +10
    (两侧实测带间隔充分)。
    """
    pair = _RED_HUE_PAIRS.get(frozenset({a, b}))
    if pair is None:
        return None
    diff = float(slot_img[:, :, 2].mean()) - float(slot_img[:, :, 0].mean())
    return pair if diff > 10.0 else (b if pair == a else a)


if __name__ == '__main__':
    """离线自测:对备战截图的填充槽(bench-1/2/5)识别,验证模块。"""
    import sys

    repo = get_project_root()  # src/sr_od/application/currency_war -> repo
    screen_path = sys.argv[1] if len(sys.argv) > 1 else str(
        repo / '.debug' / 'sr_od_mcp' / 'screenshot' / 'screenshot_20260802_121926_271794.png'
    )
    avatar_dir = repo / 'assets' / 'template' / 'currency_war/portrait_plaza'   # 官方立绘库(plaza big_icon 烘焙,唯一库)   # noqa: E501  # 与 deploy_bench 生产路径一致;旧 demo 用 character_avatar 脸库,2026-08-09 对齐)
    # 填充的备战槽(GT 坐标,峰高证实有角色)
    slots = {
        'bench-1': (382, 845, 495, 979),
        'bench-2': (507, 844, 620, 978),
        'bench-5': (882, 846, 995, 980),
    }
    from one_dragon.utils import cv2_utils

    screen = cv2_utils.read_image(screen_path)   # RGB(与生产截图同约定;cv2.imread 返 BGR 勿直用)
    templates = load_avatar_templates(avatar_dir)
    print(f'模板 {len(templates)} 个;截图 {screen_path}')
    for name, (x1, y1, x2, y2) in slots.items():
        cid, score = identify_character(screen[y1:y2, x1:x2], templates)
        print(f'  {name}: -> {cid} (inliers={score})')
