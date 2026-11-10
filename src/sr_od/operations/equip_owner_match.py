"""装备列表卡「占用者识别」:角标区角色头像匹配。

替换列表每件装备右上角的圆形头像角标 = 当前装备者头像的渲染,与
avatarminiicon 源图同源 —— 检测窗取角标整圆外接正方形(44×44,圆心
居中)、模板缩放到 44px 单档后 matchTemplate 匹配可靠(实测:11 角色
真匹配 1.00、无角标卡面假相似 ≤0.67)。

⚠️ 颜色/亮度统计判「有无角标」不具泛化性,已实测排除:卡面图案明暗盖过
角标差异(光锥界面角标比卡面亮 +41,遗器界面反而暗 -36,两方向均反向)。
占用识别只走头像匹配正路;全部模板低于阈值 = 未装备或角标角色不在库,
诚实返回 None(不猜测)。

模板库:`assets/template/character_avatar_mini/<角色id>.png` —— 文件名 =
Character.id(生成端 archive_mini_icons 按 character_const 的 avatar_id
权威表转写);衣装变体 = `<角色id>_skin<衣装号>`(如
march7th_preservation_skin01),识别时按角色归一(剥 _skin 后缀)。
⚠️ 同角色不同衣装的角标渲染帧可能差异大(三月七皮肤:源图睁眼 vs
列表角标闭眼,匹配分数显著不同)——识别失败时按「不在库」诚实返回
None,不作猜测;实机发现新失败形态优先目检角标帧再补模板。
"""

import re
from pathlib import Path

import cv2
import numpy as np

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils, os_utils
from sr_od.config.character_const import get_character_by_id

_MINI_DIR_REL = 'assets/template/character_avatar_mini'
# 角标窗 = 角标整圆(含描边)外接正方形 44×44(卡内 (x1+95,y1+3)~(x1+139,y1+47),
# 霍夫圆实测圆心 (x1+117,y1+25) 整圆直径≈45px);模板 = avatarminiicon 源图
# 原生 44×44,与角标渲染天然同尺寸,**不做任何缩放**(实测 44 原生模板+44 窗:
# 11 角色真匹配 1.00、无角标卡面假相似 ≤0.67;任何 resize 都会引入插值失配)
_TEMPLATE_SIZES: tuple[int, ...] = (44,)
# 命中阈值(实测同角色最低 0.878、异角色最高 0.453,取中)
_MIN_OWNER_SCORE: float = 0.75
# 光锥界面角标渲染更小/更糊,avatarminiicon 源模板的真匹配分数实测
# 0.46-0.72(花火/停云/缇宝等掉阈值下漏报,渐进治理:等解包头像源调研
# 定位更同源素材);无角标卡面的假相似上限实测 ≤0.53,阈值 0.70 两侧
# 均不误报
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
