"""货币战争角色识别:SIFT 特征匹配 character_avatar 模板库。

实测(2026-08-02,任务 10):仓库已有 ``assets/template/character_avatar/``(~90 角色,
忘却之庭配队画面截的**脸近景**)。SIFT 匹配备战槽内角色:
- 脸部独特角色(herta 28 内点)→ 清晰命中;
- 配饰/半身角色(黑天鹅等)→ 模糊(脸近景 ≠ 备战半身立绘,显著特征如帽子不在模板)。
故本模块对「脸部独特」角色可靠、对配饰角色不可靠 → 可靠识别需货币战争专属模板
(从备战/商店截)或 OCR 名字兜底。``min_inliers`` + 歧义比过滤低置信结果。

部署/循环 op 用本模块时,模板由 ``ctx.ih`` 预加载传入(避免每次重算);离线测试用
``load_avatar_templates`` 从磁盘加载。
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
    """加载目录下所有角色头像模板(``<id>/raw.png``),预计算 SIFT 关键点/描述子。"""
    templates: AvatarTemplates = {}
    for child in sorted(avatar_dir.iterdir()):
        raw = child / 'raw.png'
        if not raw.is_file():
            continue
        img = cv2.imread(str(raw))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, desc = _SIFT.detectAndCompute(gray, None)
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

    :param slot_img: 槽位裁图(BGR)。
    :param templates: :func:`load_avatar_templates` 的结果(op 集成时由 ctx.ih 预加载传入)。
    :param min_inliers: 最低内点数,低于此判 unknown(配饰角色/非角色会落这)。
    :param ambiguity_ratio: best 需 ≥ ratio × second 才算非歧义。
    :return: ``(char_id or None, best_inliers)``。None = 未知 / 歧义 / 低于阈值。
    """
    gray = cv2.cvtColor(slot_img, cv2.COLOR_BGR2GRAY)
    skp, sdesc = _SIFT.detectAndCompute(gray, None)
    scores: list[tuple[str, int]] = [
        (cid, _inliers(skp, sdesc, tkp, tdesc))
        for cid, (_g, tkp, tdesc) in templates.items()
    ]
    scores.sort(key=lambda t: -t[1])
    best_id, best = scores[0]
    second = scores[1][1] if len(scores) > 1 else 0
    if best < min_inliers:
        return None, best
    if second > 0 and best < ambiguity_ratio * second:
        return None, best
    return best_id, best


if __name__ == '__main__':
    """离线自测:对备战截图的填充槽(bench-1/2/5)识别,验证模块。"""
    import sys

    repo = Path(__file__).resolve().parents[4]  # src/sr_od/application/currency_war -> repo
    screen_path = sys.argv[1] if len(sys.argv) > 1 else str(
        repo / '.debug' / 'sr_od_mcp' / 'screenshot' / 'screenshot_20260802_121926_271794.png'
    )
    avatar_dir = repo / 'assets' / 'template' / 'character_avatar'
    # 填充的备战槽(GT 坐标,峰高证实有角色)
    slots = {
        'bench-1': (382, 845, 495, 979),
        'bench-2': (507, 844, 620, 978),
        'bench-5': (882, 846, 995, 980),
    }
    screen = cv2.imread(screen_path)
    templates = load_avatar_templates(avatar_dir)
    print(f'模板 {len(templates)} 个;截图 {screen_path}')
    for name, (x1, y1, x2, y2) in slots.items():
        cid, score = identify_character(screen[y1:y2, x1:x2], templates)
        print(f'  {name}: -> {cid} (inliers={score})')
