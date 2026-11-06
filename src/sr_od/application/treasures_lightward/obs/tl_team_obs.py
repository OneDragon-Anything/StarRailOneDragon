"""忘却之庭-编队画面结构化识别:聚合入口(消费方统一 import 路径)。

识别实现按域拆分(同目录):
- ``tl_team_common``:公共底座(共享阈值 / 区域工具 / 单格头像识别 / 全部识别数据类);
- ``tl_stage_info_obs``:右上关卡信息(关卡名 / 环境效果 / 挑战目标);
- ``tl_weakness_obs``:弱点属性(建议属性)+ 节点队伍槽(右侧);
- ``tl_character_list_obs``:左侧角色列表(等级锚整页主扫 / 固定网格 / 点击中心);
- ``tl_preset_obs``:预设编队 tab。

本文件只做两件事:①re-export 各域公共符号(消费方 import 路径不变);
②整装 ``collect_tl_team_info``(按激活 tab 装配左右两侧识别结果)。

**副本类型差异的消化层**:各玩法(FH/PF/AS)的编队识别**共享同一套算法**,差异不在文件级——
- 坐标/锚差异 → screen_info 各屏独立建档(忘却之庭-编队/虚构叙事-编队/末日幻影-编队
  各自 yml),识别函数经 ``screen_name`` 参数走各屏 area;
- 布局差异 → 函数参数(如弱点图块带 ``weakness_layout``: FH/PF='below' / AS='inline';
  星启(难度 04)三行槽位走锚偏移标定,见 tl_weakness_obs 的 ``_ARC_*`` 常量块);
- 对外识别入口已按屏分文件 → ``recognizers/``(tl_team_recognizer=忘却之庭 /
  tl_as_team_recognizer=末日幻影)。
因此不要按副本类型再拆识别文件(会复制同构算法);出现新副本屏时优先建档+传参,
标定常量在所属域文件内按屏分组注释,量大到跨域膨胀时再考虑抽标定配置模块。
关卡序号术语统一「难度」(FH 难度 1-12 / PF·AS 难度 01-04;游戏内 FH 显示「第N关」,
定案见 skill sr-od-treasures-lightward references/gameplay.md「关卡结构术语」)。

⚠️ 适用范围:识别标定(槽位坐标/建议属性/预设卡/阈值)全部基于**混沌回忆**的编队屏
实机帧;逐光捡金其余玩法(虚构叙事/末日幻影)的编队屏布局若不同,需另行建档识别,
不可直接复用本模块的常量与 area(人类老莫明确:其他类型的填充可能不一样)。

消费面:
- per-screen recognizer(``recognizers/tl_team_recognizer.py``):analyze_screen 精准命中
  「忘却之庭-编队」后把结构化事实塞进 extras,供智能体/HTTP 直读;
- 自动化 op:配队检查 / 预设应用决策直接调本模块纯函数。

**头像识别**:项目脸库 ``assets/template/character_avatar``(统一高分辨率方形头像源,
160×188;目录名 = 角色 id,皮肤衣装 = ``<角色id>_skin<序号>``;遍历与命名约定见
``sr_od/config/avatar_templates.py``)。角色列表卡主路径 = **整页多目标模板匹配**
(列表区特征一次提取 → 全模板 SIFT 定位 → 等级锚归属 → 内点数仲裁;标定见
tl_character_list_obs 的 ``_PAGE_*`` 常量块),模板特征贫乏或无命中的锚回退
逐格裁片匹配。右侧队伍槽(74px 圆裁)、预设卡、固定网格为裁片范式。
**穿皮肤(衣装)的角色渲染皮肤版头像,与默认模板不同源**:皮肤模板同库分目录
(``<角色id>_skin<序号>``),整页主扫默认+皮肤统一仲裁,同位冲突按内点数取最高;
皮肤条目未覆盖的造型识别失败为预期行为,候选诚实返回。

**阈值标定**(实机帧,fixture = sr-od-test/screens/忘却之庭-编队/):
- 裁片范式:真实头像 confidence ≥0.766,空槽占位图标伪命中 0.588 → 门槛 0.70;
- 歧义比(top1/top2)<1.25 → 拒绝单一结论,返回候选;
- 空槽:裁片 HSV 平均 V<60(空槽 34.6 vs 实头像 85-145);
- tab 激活:标签区平均 V≥140(激活 ~178 vs 非激活 ~95-105)。

纯读约束:全部函数不写 ctx/模块全局(模板缓存为只读资源,recognizer 可与运行中 op 并发)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.treasures_lightward.obs.tl_character_list_obs import (
    GridCell,
    grid_cell_center,
    read_character_cells_by_level,
    read_character_grid,
)
from sr_od.application.treasures_lightward.obs.tl_preset_obs import read_preset_teams
from sr_od.application.treasures_lightward.obs.tl_stage_info_obs import (
    read_environment,
    read_stage_name,
    read_star_targets,
)
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    ACTIVE_TAB_MEAN_V,
    AMBIGUITY_RATIO,
    EMPTY_SLOT_MEAN_V,
    MIN_CONFIDENCE,
    SCREEN_NAME,
    AnchorCell,
    MemberGuess,
    NodeInfo,
    PageHit,
    PresetTeam,
    TlTeamView,
    get_area_rect,
    identify_crop,
    mean_v,
    ocr_lines,
    read_left_tab,
)
from sr_od.application.treasures_lightward.obs.tl_weakness_obs import (
    ensure_boss_weakness_map,
    ensure_element_templates,
    node_row_select_point,
    read_team_nodes,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

__all__ = [
    'SCREEN_NAME',
    'MIN_CONFIDENCE',
    'AMBIGUITY_RATIO',
    'EMPTY_SLOT_MEAN_V',
    'ACTIVE_TAB_MEAN_V',
    'MemberGuess',
    'PresetTeam',
    'GridCell',
    'AnchorCell',
    'PageHit',
    'NodeInfo',
    'TlTeamView',
    'get_area_rect',
    'identify_crop',
    'mean_v',
    'ocr_lines',
    'read_left_tab',
    'read_stage_name',
    'read_environment',
    'read_star_targets',
    'read_team_nodes',
    'node_row_select_point',
    'ensure_element_templates',
    'ensure_boss_weakness_map',
    'read_character_grid',
    'read_character_cells_by_level',
    'grid_cell_center',
    'read_preset_teams',
    'collect_tl_team_info',
]


def collect_tl_team_info(ctx: SrContext, image: MatLike) -> TlTeamView:
    """整帧装配(按激活 tab 决定左侧列表走哪套识别;左右两块互不影响)。"""
    tab = read_left_tab(ctx, image)
    character_grid: list[GridCell] | None = None
    preset_teams: list[PresetTeam] | None = None
    if tab == '角色列表':
        character_grid = read_character_grid(ctx, image)
    elif tab == '预设编队':
        preset_teams = read_preset_teams(ctx, image)
    return TlTeamView(
        stage_name=read_stage_name(ctx, image),
        environment_text=read_environment(ctx, image),
        star_targets=read_star_targets(ctx, image),
        left_tab=tab,
        nodes=read_team_nodes(ctx, image),
        character_grid=character_grid,
        preset_teams=preset_teams,
    )
