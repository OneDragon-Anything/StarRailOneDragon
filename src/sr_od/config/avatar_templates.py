"""角色头像模板统一遍历(脸库单一入口)。

脸库 = ``assets/template/character_avatar/<template_id>/raw.webp``。命名约定即注册表:
- 目录名 == ``Character.id`` → 默认衣装模板;
- 目录名 == ``<Character.id>_skin<序号>`` → 该角色的皮肤衣装模板;
- 两者皆非 → 资产命名错误,遍历时直接 raise(受控资产错误立即暴露,优于静默跳过)。

消费方(s op 内头像识别)一律经 :func:`iter_avatar_templates` 取模板集,
不得自行扫目录或按 CHARACTER_LIST 直拼——皮肤条目、未来新增变体的
归属关系都由本模块的约定解析统一维护。匹配与锚定归各消费场景自行实现
(锚定方式天然场景特定:列表卡文本锚 / 槽位网格 / 预设卡子区 / 队伍栏 area)。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import os_utils
from sr_od.config.character_const import CHARACTER_LIST, Character

if TYPE_CHECKING:
    from one_dragon.base.screen.template_info import TemplateInfo
    from sr_od.context.sr_context import SrContext

#: 皮肤目录命名约定:<Character.id>_skin<序号>
_SKIN_DIR_PATTERN = re.compile(r'^(.+)_skin(\d+)$')

#: 脸库在 assets/template 下的分类目录名
AVATAR_TEMPLATE_SUB_DIR = 'character_avatar'


@dataclass
class AvatarTemplate:
    """单个头像模板条目。

    Attributes:
        template_id: 模板目录名(TemplateLoader 的 template_id)。
        character: 模板对应的角色(皮肤条目指向本体角色,如
            march7th_preservation_skin01 → march7th_preservation)。
        variant: 衣装变体;'default'=默认衣装,'skin<序号>'=皮肤。
        info: 模板信息(raw 与 SIFT 特征惰性加载)。
    """

    template_id: str
    character: Character
    variant: str
    info: 'TemplateInfo'


def iter_avatar_templates(ctx: SrContext) -> list[AvatarTemplate]:
    """脸库全量模板遍历(默认 + 皮肤;ctx 级缓存,幂等,纯读)。

    皮肤条目与默认条目可能同 Character 并存(同一角色多衣装),
    消费方按 template_id / variant 区分。模板缺失(raw 读不到)视为
    资产错误 raise,与命名校验同一口径。
    """
    cached = getattr(ctx, 'avatar_templates', None)
    if cached is not None:
        return cached
    by_id = {c.id: c for c in CHARACTER_LIST}
    root = os_utils.get_path_under_work_dir('assets', 'template', AVATAR_TEMPLATE_SUB_DIR)
    loader = TemplateLoader()
    entries: list[AvatarTemplate] = []
    for dir_name in sorted(os.listdir(root)):
        full = os.path.join(root, dir_name)
        if not os.path.isdir(full):
            continue
        if dir_name in by_id:
            character, variant = by_id[dir_name], 'default'
        else:
            m = _SKIN_DIR_PATTERN.fullmatch(dir_name)
            if m is None or m.group(1) not in by_id:
                raise ValueError(
                    f'角色脸库存在不合命名约定的目录: {dir_name}'
                    f'(应为 Character.id 或 <Character.id>_skin<序号>)')
            character, variant = by_id[m.group(1)], f'skin{m.group(2)}'
        info = loader.get_template(AVATAR_TEMPLATE_SUB_DIR, dir_name)
        if info is None or info.raw is None:
            raise ValueError(f'角色头像模板缺失原图: {dir_name}')
        entries.append(AvatarTemplate(dir_name, character, variant, info))
    ctx.avatar_templates = entries
    return entries
