"""装备列表卡「占用者识别」:角标区角色头像匹配。

替换列表每件装备右上角的圆形头像角标 = 当前装备者头像的渲染,与游戏内
列表角标渲染同源(64×64 圆形)—— 缩放到 36px 后 matchTemplate
匹配可靠(实测:同角色 0.878 / 异角色 0.24-0.45,阈值 0.75 可分)。

⚠️ 颜色/亮度统计判「有无角标」不具泛化性,已实测排除:卡面图案明暗盖过
角标差异(光锥界面角标比卡面亮 +41,遗器界面反而暗 -36,两方向均反向)。
占用识别只走头像匹配正路;全部模板低于阈值 = 未装备或角标角色不在库,
诚实返回 None(不猜测)。

模板库:`assets/template/character_avatar_mini/<角色id>.png` —— 文件名 =
Character.id(生成端 archive_mini_icons 按 character_const 的 avatar_id
权威表转写);衣装变体 = `<角色id>_skin<衣装号>`(如
march7th_preservation_skin01),识别时按角色归一(剥 _skin 后缀)。
⚠️ 同角色不同衣装的角标渲染帧可能差异大(三月七皮肤:源图睁眼 vs
列表角标闭眼猫爪,匹配 0.42 不过阈)——皮肤角标识别失败时按「不在库」
诚实返回 None,不作猜测;实机发现新失败形态优先目检角标帧再补模板。
"""

import re
from pathlib import Path

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import get_character_by_id

_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标圆的有效直径 ~40px,mini 原始 64px 缩放到 36px 实测最优档
_TEMPLATE_SIZE: int = 36
# 角标渲染**尺寸不统一**(遗器替换界面实机:同一列表内两档圆径 ~30px 与
# ~48px 并存,固定 36px 模板只命中小档、大档 0.47 全灭)——匹配按多尺度
# 展开,取各档最高分;档位覆盖实测两档圆径
_TEMPLATE_SIZES: tuple[int, ...] = (36, 48)
# 命中阈值(实测同角色最低 0.878、异角色最高 0.453,取中)
_MIN_OWNER_SCORE: float = 0.75
# 光锥界面角标渲染更小/更糊,实测同角色好匹配 0.72-0.91、噪声上限约 0.66,阈值 0.70 裕度薄,调参需回归;
# 两界面的异角色误配上限都很低(0.35-0.45),放低不失区分度
LIGHT_CONE_OWNER_SCORE: float = 0.70

_mini_cache: dict[int, dict[str, np.ndarray]] = {}


def _owner_templates() -> dict[int, dict[str, np.ndarray]]:
    """懒加载全部角色 mini 模板,按匹配尺度分档。

    模板文件名 = Character.id(生成端 archive_mini_icons 已对齐,皮肤 =
    `<角色id>_skin<衣装号>`);中文名归一统一在 _owner_cn 做(含皮肤名
    剥后缀),本函数只管加载与分档。
    :return: 尺度 → (角色 id → 该尺度灰度模板);键常驻保证缓存命中。
    """
    if _mini_cache:
        return _mini_cache
    lib: dict[int, dict[str, np.ndarray]] = {size: {} for size in _TEMPLATE_SIZES}
    base = Path(os_utils.get_path_under_work_dir(*_MINI_DIR_REL.split('/')))
    for f in base.glob('*.png'):
        img = cv2_utils.read_image(str(f))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        for size in _TEMPLATE_SIZES:
            lib[size][f.stem] = cv2.resize(gray, (size, size))
    _mini_cache.update(lib)
    return _mini_cache


def match_owner(screen_rgb: np.ndarray, badge_rect: Rect,
                min_score: float = _MIN_OWNER_SCORE) -> tuple[str | None, float]:
    """识别角标区的占用角色,返回**中文角色名**(如「黄泉」)。

    多尺度匹配:角标渲染尺寸两档并存(见 _TEMPLATE_SIZES 注),各档独立
    matchTemplate 取全局最高分判阈。

    :param screen_rgb: 整屏截图(RGB)
    :param badge_rect: 角标检测区(调用方按所在界面的角标偏移换算,见各 op 常量)
    :param min_score: 命中阈值;遗器界面用默认,光锥界面传 LIGHT_CONE_OWNER_SCORE
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
    for templates_by_name in _owner_templates().values():
        for name, tmpl in templates_by_name.items():
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
    """模板名 → 中文角色名;皮肤模板(`<角色id>_skin<衣装号>`)剥后缀归一。

    模板文件名 = Character.id(生成端 archive_mini_icons 保证),
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
