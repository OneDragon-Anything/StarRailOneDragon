"""装备列表卡「占用者识别」:角标区角色头像匹配。

替换列表每件装备右上角的圆形头像角标 = 当前装备者头像的渲染,与游戏内
列表角标渲染同源(64×64 圆形)—— 缩放到 36px 后 matchTemplate
匹配可靠(实测:同角色 0.878 / 异角色 0.24-0.45,阈值 0.75 可分)。

⚠️ 颜色/亮度统计判「有无角标」不具泛化性,已实测排除:卡面图案明暗盖过
角标差异(光锥界面角标比卡面亮 +41,遗器界面反而暗 -36,两方向均反向)。
占用识别只走头像匹配正路;全部模板低于阈值 = 未装备或角标角色不在库,
诚实返回 None(不猜测)。

模板库:`assets/template/character_avatar_mini/<角色id>.png`
(``skin_`` 前缀为衣装变体,占用识别按角色归一)。
"""

from pathlib import Path

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import get_character_by_id

_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标圆的有效直径 ~40px,mini 原始 64px 缩放到 36px 实测最优档
_TEMPLATE_SIZE: int = 36
# 命中阈值(实测同角色最低 0.878、异角色最高 0.453,取中)
_MIN_OWNER_SCORE: float = 0.75
# 光锥界面角标渲染更小/更糊,实测同角色好匹配 0.72-0.91、噪声上限约 0.66,阈值 0.70 裕度薄,调参需回归;
# 两界面的异角色误配上限都很低(0.35-0.45),放低不失区分度
CONE_OWNER_SCORE: float = 0.70

_mini_cache: dict[str, np.ndarray] | None = None


def _owner_templates() -> dict[str, np.ndarray]:
    """懒加载全部角色 mini 模板(灰度 36×36;skin_ 前缀归一到角色 id)。"""
    global _mini_cache
    if _mini_cache is not None:
        return _mini_cache
    _mini_cache = {}
    base = Path(os_utils.get_path_under_work_dir(*_MINI_DIR_REL.split('/')))
    for f in base.glob('*.png'):
        img = cv2_utils.read_image(str(f))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        name = f.stem[5:] if f.stem.startswith('skin_') else f.stem
        _mini_cache[name] = cv2.resize(gray, (_TEMPLATE_SIZE, _TEMPLATE_SIZE))
    return _mini_cache


def match_owner(screen_rgb: np.ndarray, badge_rect: Rect,
                min_score: float = _MIN_OWNER_SCORE) -> tuple[str | None, float]:
    """识别角标区的占用角色,返回**中文角色名**(如「黄泉」)。

    :param screen_rgb: 整屏截图(RGB)
    :param badge_rect: 角标检测区(调用方按所在界面的角标偏移换算,见各 op 常量)
    :param min_score: 命中阈值;遗器界面用默认,光锥界面传 CONE_OWNER_SCORE
        (角标渲染更小,匹配天花板低)
    :return: (中文角色名, 最高分);最高分 < 阈值返回 (None, 最高分) —— 未装备
        或角标角色不在模板库,不猜测。中文映射缺失的角色兜底返回模板英文 id。
    """
    zone = screen_rgb[badge_rect.y1:badge_rect.y2, badge_rect.x1:badge_rect.x2]
    if zone.size == 0:
        return None, 0.0
    gray_zone = cv2.cvtColor(zone, cv2.COLOR_RGB2GRAY)

    best_name: str | None = None
    best_score = 0.0
    for name, tmpl in _owner_templates().items():
        if tmpl.shape[0] > gray_zone.shape[0] or tmpl.shape[1] > gray_zone.shape[1]:
            continue
        res = cv2.matchTemplate(gray_zone, tmpl, cv2.TM_CCOEFF_NORMED)
        _, mv, _, _ = cv2.minMaxLoc(res)
        if mv > best_score:
            best_name, best_score = name, mv

    if best_score < min_score:
        return None, best_score
    return _owner_cn(best_name), best_score


def _owner_cn(template_name: str) -> str:
    """模板英文 id → 中文角色名;character_const 未收录的兜底返回英文 id。"""
    character = get_character_by_id(template_name)
    if character is not None:
        return character.cn
    # mini 库 tag 与项目 Character.id 的已知差异(模板库 tag 用官方英文缩写,
    # 项目 id 是全称;随新角色出现按需补录)
    alias = {'danhengil': 'danhengimbibitorlunae', 'topaz': 'topaznumby'}
    alias_id = alias.get(template_name)
    if alias_id is not None:
        character = get_character_by_id(alias_id)
        if character is not None:
            return character.cn
    return template_name
