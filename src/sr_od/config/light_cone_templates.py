"""光锥卡面模板统一遍历(卡面库单一入口)。

卡面库 = ``assets/template/light_cone_icon/<template_id>/raw.webp``。命名约定即注册表:
- 目录名 == ``LightConeDef.id`` → 该光锥的卡面模板;
- 其余 → 资产命名错误,遍历时直接 raise(受控资产错误立即暴露,优于静默跳过)。
- 国际服词条未同步的光锥(id 为空串)尚无 id,不在卡面库中,回填后补录。

消费方(光锥识别)一律经 :func:`iter_light_cone_templates` 取模板集,
不得自行扫目录或按名称键拼路径——id 回填、目录增删的归属关系都由本模块
的约定解析统一维护。匹配与锚定归各消费场景自行实现。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import os_utils
from sr_od.mys.sr_light_cones import LIGHT_CONES, LightConeDef

if TYPE_CHECKING:
    from one_dragon.base.screen.template_info import TemplateInfo
    from sr_od.context.sr_context import SrContext

#: 卡面库在 assets/template 下的分类目录名
LIGHT_CONE_TEMPLATE_SUB_DIR = 'light_cone_icon'


@dataclass
class LightConeTemplate:
    """单个光锥卡面模板条目。

    Attributes:
        template_id: 模板目录名(== LightConeDef.id,TemplateLoader 的 template_id)。
        light_cone: 模板对应的光锥定义。
        info: 模板信息(raw 与 SIFT 特征惰性加载)。
    """

    template_id: str
    light_cone: LightConeDef
    info: TemplateInfo


def iter_light_cone_templates(ctx: SrContext) -> list[LightConeTemplate]:
    """卡面库全量模板遍历(ctx 级缓存,幂等,纯读)。

    目录名必须命中某把光锥的 id(空 id 光锥不入库),违者 raise;
    模板缺失(raw 读不到)视为资产错误 raise,与命名校验同一口径。
    """
    cached = getattr(ctx, 'light_cone_templates', None)
    if cached is not None:
        return cached
    by_id = {c.id: c for c in LIGHT_CONES if c.id}
    root = os_utils.get_path_under_work_dir('assets', 'template', LIGHT_CONE_TEMPLATE_SUB_DIR)
    loader = TemplateLoader()
    entries: list[LightConeTemplate] = []
    for dir_name in sorted(os.listdir(root)):
        full = os.path.join(root, dir_name)
        if not os.path.isdir(full):
            continue
        cone = by_id.get(dir_name)
        if cone is None:
            raise ValueError(
                f'光锥卡面库存在不合命名约定的目录: {dir_name}(应为 LightConeDef.id)')
        info = loader.get_template(LIGHT_CONE_TEMPLATE_SUB_DIR, dir_name)
        if info is None or info.raw is None:
            raise ValueError(f'光锥卡面模板缺失原图: {dir_name}')
        entries.append(LightConeTemplate(dir_name, cone, info))
    ctx.light_cone_templates = entries
    return entries
