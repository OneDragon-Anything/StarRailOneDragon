"""sim 重做·单局运行配置(局级输入,M01 正典字段清单)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M01:开局参数是**局级输入**,
由调用方给定,sim 内不猜开局条件分布;本 dataclass = 全稿唯一的字段
清单汇总面(M02/M20/U21/U27 一律引用此处,不再各自加字段)。

字段定案出处:
- 环境在场 = U07④ 已裁决的必填输入,缺省 False = 无环境支路
  (entry 跳过环境屏;环境身份由 M02 offer 引擎采样,非本配置);
- boss 名单覆盖 = U02 已裁决(缺省 None = sim 内置逐位面 boss 表);
- 位面强化词 = U21 定稿口径「首版不建模,RunConfig 预留」;
- 优势布局/昔涟诗篇 = U27 定稿口径「不建模,预留」;
- seed 与开局手牌**不入**本配置(seed 是 reset 的独立参数,开局手牌由
  sim 按 U28 生成)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunConfig:
    """单局开局参数(调用方给定;值域与缺省语义见类注释)。"""

    #: 职级(开局确认屏所选档,'A1'..'A8' 及 A8 子档;容器
    #: selected_difficulty 同名同义)。开局 HP 查表唯一实证档 = 'A8',
    #: 其余档报错索样本(U15 定稿口径,不外推)。
    selected_difficulty: str
    #: 数值难度档(局内左上旗牌数值;开局 HP 查表实证档 = 108)。
    #: None = 调用方未给定(开局 HP 查表即报错索样本)。
    enemy_difficulty: int | None
    #: 敌人词缀名单(简报 OCR 原名;开局 HP 修正查表键,「开局不利」
    #: 恒 −20 由 kernel/cw_opening_hp 单一承载,M20 词缀引擎禁再实现)。
    enemy_affixes: tuple[str, ...] = ()
    #: 对局类型(标准博弈/超频博弈;U27 定稿口径:sim 首版辖域 = 标准博弈,
    #: 非标准值在引擎入口显式拒,不在本配置层猜差异)。
    game_mode: str = '标准博弈'
    #: 投资环境在场(U07④ 必填输入)。False = 无环境支路,entry 跳过
    #: 环境屏;True = 开局环境 offer 由 M02 引擎按机制采样。
    env_present: bool = False
    #: boss 名单覆盖(U02:三位面 boss 名,下标 = 位面−1;元素 None =
    #: 该位面按内置表)。None = 全部用 sim 内置逐位面 boss 表。
    boss_roster_override: tuple[str | None, str | None, str | None] | None = None
    #: 位面强化词(U21 预留,首版不建模;非 None 时引擎披露未建模)。
    plane_reinforce: str | None = None
    #: 优势布局(U27 预留,首版不建模)。
    advantage_layout: str | None = None
    #: 昔涟诗篇(U27 预留,首版不建模)。
    ripple_poem: str | None = None
