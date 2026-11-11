"""遗器单件模板统一遍历(模板库单一入口)。

模板库 = ``assets/template/relic_icon/<template_id>/raw.webp``。命名约定即注册表:
- 目录名 == ``f'{RelicSetDef.id}_{RELIC_POS_EN[pos]}'`` → 该套装该部位的单件模板;
- 其余 → 资产命名错误,遍历时直接 raise(受控资产错误立即暴露,优于静默跳过)。
- 国际服词条未同步的套装(套装 id 为空串)尚无 id,不在模板库中,回填后补录
  （7 套 20 件,名单由测试白名单锁定）。

与光锥卡面库的差异:光锥一套一模板(卡面),遗器一套多件(隧洞 4 件/位面 2 件),
template_id 由套装 id + 部位英文组合定位到单件。

消费方(遗器识别)一律经 :func:`iter_relic_templates` 取模板集,
不得自行扫目录或按名称键拼路径——id 回填、目录增删的归属关系都由本模块
的约定解析统一维护。匹配与锚定归各消费场景自行实现。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import os_utils
from sr_od.mys.sr_relic_sets import (
    RELIC_POS_EN,
    RELIC_SETS,
    RelicSetDef,
    SrRelicPieceDef,
)

if TYPE_CHECKING:
    from one_dragon.base.screen.template_info import TemplateInfo
    from sr_od.context.sr_context import SrContext

#: 模板库在 assets/template 下的分类目录名
RELIC_TEMPLATE_SUB_DIR = 'relic_icon'


def relic_template_id(relic_set: RelicSetDef, pos: int) -> str:
    """套装 + 部位号 → 模板目录名。pos 坐标系见 SrRelicPieceDef(生成期快照,恒稳)。"""
    return f'{relic_set.id}_{RELIC_POS_EN[pos]}'


@dataclass
class RelicTemplate:
    """单个遗器单件模板条目。

    Attributes:
        template_id: 模板目录名(== 套装 id + 部位英文,TemplateLoader 的 template_id)。
        relic_set: 模板对应的套装定义。
        piece: 模板对应的单件定义(pos 与 template_id 部位段一致)。
        info: 模板信息(raw 与 SIFT 特征惰性加载)。
    """

    template_id: str
    relic_set: RelicSetDef
    piece: SrRelicPieceDef
    info: TemplateInfo


def iter_relic_templates(ctx: SrContext) -> list[RelicTemplate]:
    """模板库全量模板遍历(ctx 级缓存,幂等,纯读)。

    目录名必须命中「有 id 套装 × 部位」组合(空 id 套装不入库),违者 raise;
    模板缺失(raw 读不到)视为资产错误 raise,与命名校验同一口径。
    """
    cached = getattr(ctx, 'relic_templates', None)
    if cached is not None:
        return cached
    # 预期入库集合:非空 id 套装全部件 → template_id
    expected: dict[str, tuple[RelicSetDef, SrRelicPieceDef]] = {
        relic_template_id(relic_set, piece.pos): (relic_set, piece)
        for relic_set in RELIC_SETS if relic_set.id
        for piece in relic_set.pieces
    }
    root = os_utils.get_path_under_work_dir('assets', 'template', RELIC_TEMPLATE_SUB_DIR)
    loader = TemplateLoader()
    entries: list[RelicTemplate] = []
    for dir_name in sorted(os.listdir(root)):
        full = os.path.join(root, dir_name)
        if not os.path.isdir(full):
            continue
        hit = expected.get(dir_name)
        if hit is None:
            raise ValueError(
                f'遗器模板库存在不合命名约定的目录: {dir_name}'
                f'(应为 套装id_部位英文,如 spacesealingstation_planarsphere)')
        relic_set, piece = hit
        info = loader.get_template(RELIC_TEMPLATE_SUB_DIR, dir_name)
        if info is None or info.raw is None:
            raise ValueError(f'遗器模板缺失原图: {dir_name}')
        entries.append(RelicTemplate(dir_name, relic_set, piece, info))
    ctx.relic_templates = entries
    return entries
