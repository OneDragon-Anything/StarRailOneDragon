# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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

# SIFT 检测器(与 one_dragon.utils.cv2_utils.feature_detector 同源)
_SIFT = cv2.SIFT_create()
_MATCHER = cv2.BFMatcher()

AvatarTemplates = dict[str, tuple[MatLike, tuple, np.ndarray]]
"""{char_id: (gray, keypoints, descriptors)}"""


def load_avatar_templates(avatar_dir: Path) -> AvatarTemplates:
    """加载目录下所有角色头像模板(``<id>/raw.png``),预计算 SIFT 关键点/描述子。

    若同目录存在 ``mask.png``(官方库烘焙产物,alpha 二值掩码),SIFT 只在掩码区提特征
    (背景色不进描述子;ADR 见烘焙生成器 tools/cw/gen_plaza_chars.py)。无 mask 则全图(旧手采库兼容)。
    """
    templates: AvatarTemplates = {}
    for child in sorted(avatar_dir.iterdir()):
        raw = child / 'raw.png'
        if not raw.is_file():
            continue
        img = cv2.imdecode(np.fromfile(str(raw), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mask_file = child / 'mask.png'
        mask = None
        if mask_file.is_file():
            m = cv2.imdecode(np.fromfile(str(mask_file), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if m is not None and m.shape == gray.shape:
                mask = m
        kp, desc = _SIFT.detectAndCompute(gray, mask)
        templates[child.name] = (gray, kp, desc)
    return templates


def _inliers(skp, sdesc, tkp, tdesc, knn: float = 0.75) -> int:
    """SIFT + ratio test + RANSAC 内点数(越大越匹配;<4 good 直接返回)。"""
    if sdesc is None or tdesc is None or len(skp) < 4 or len(tkp) < 4:
        return 0
    matches = _MATCHER.knnMatch(tdesc, sdesc, k=2)
    good: list = []
    for t in matches:
        if len(t) < 2:
            continue
        m, n = t
        if m.distance < knn * n.distance:
            good.append(m)
    if len(good) < 4:
        return len(good)
    tp = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    sp = np.float32([skp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(tp, sp, cv2.RANSAC, 5.0)
    if mask is None:
        return len(good)
    return int((mask.ravel() == 1).sum())


def identify_character(
    slot_img: MatLike,
    templates: AvatarTemplates,
    min_inliers: int = 10,
    ambiguity_ratio: float = 1.5,
) -> tuple[str | None, int]:
    """识别槽内角色。

    :param slot_img: 槽位裁图(**RGB**,sr_od 框架截图约定;screencapper BGRA2RGB,cv2_utils.read_image 同)。
    :param templates: :func:`load_avatar_templates` 的结果(op 集成时由 ctx.ih 预加载传入)。
    :param min_inliers: 最低内点数,低于此判 unknown(配饰角色/非角色会落这)。
    :param ambiguity_ratio: best 需 ≥ ratio × second 才算非歧义。
    :return: ``(char_id or None, best_inliers)``。None = 未知 / 歧义 / 低于阈值。

    歧义仲裁(r75 狸猫兄弟案):**同型异色单位对**(狸小虎蓝/狸小龙红,同投资策略「龙虎
    兄弟狸」造型仅色异)灰度 SIFT 形状互撞 —— ratio 1.28 < 1.5 判歧义 None,但两者的
    **色相签名是决定性的**(蓝狸 B≫R / 红狸 R>B,模板与现场实测一致)。歧义时若 top2
    恰为已知色相对(RED_HUE_PAIRS),按 slot_img 的色相差仲裁 —— SIFT 定「是这对兄弟」,
    色相定「是哪只」。
    """
    gray = cv2.cvtColor(slot_img, cv2.COLOR_RGB2GRAY)   # sr_od screen 是 RGB(screencapper BGRA2RGB;D-52 装备侧同类修,本处 2026-08-19 补)
    skp, sdesc = _SIFT.detectAndCompute(gray, None)
    scores: list[tuple[str, int]] = [
        (cid, _inliers(skp, sdesc, tkp, tdesc))
        for cid, (_g, tkp, tdesc) in templates.items()
    ]
    scores.sort(key=lambda t: -t[1])
    best_id, best = scores[0]
    second_id, second = (scores[1] if len(scores) > 1 else ('', 0))
    if best < min_inliers:
        return None, best
    if second > 0 and best < ambiguity_ratio * second:
        # r75 色相仲裁:top2 是已知同型异色对 → 色相差定夺
        arb = _hue_arbitrate(slot_img, best_id, second_id)
        if arb is not None:
            return arb, best
        return None, best
    return best_id, best


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

    repo = Path(__file__).resolve().parents[4]  # src/sr_od/application/currency_war -> repo
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
