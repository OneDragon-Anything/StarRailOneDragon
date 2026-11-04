"""sim 重做·敌人难度派生与 boss 名单(M19/M20)。

设计权威版本 = ``docs/develop/sr_od/application/currency_war/sim/sim-design.md``
(§2.2 敌人侧)第一期口径:

- **M19**:难度账 = 纯派生函数(构成公式已定案成分直接实现);基础
  难度逐节点曲线 = 候实机数据(补采前基础分量按 None 披露,禁插值;
  U25 定稿口径:「局级输入档 + 已定案修正项」)。已定案成分:
  - 投资策略品质加成 白0/金3/彩6 每持 1 个(``research/economy.md`` §9);
  - 遭遇等级加成 0/10/20/30(本模块 ``ENCOUNTER_TIER_BONUS``
    同表单一源);
  - 特殊加成:伟大征服 +当前连胜数(注册表 ``difficulty_per_streak``)
    + 圣杯试炼 +30(已定案数值;激活态随 fate overlay 占位未建模,
    首版恒未激活,披露键申报);
  - 策略静态 Δ(简单模式 −3 等 C 类)与节点型限定(难度修改器:
    遭遇+首领 −4)按注册表 ``difficulty_delta``/``difficulty_node_types``;
  - 溢出 bug(>200 敌 −100%)默认不建模,列边界(版本敏感);
- **M20**:boss 名单第一期建档(U02 已裁决:只建 boss 名单)——每局
  3 位面各 1 boss、池中随机 3(``data/bosses.md`` 定位行);内置表 =
  从 boss 机制注册表全池逐位面采样,``RunConfig.boss_roster_override``
  局级输入优先;普通节点敌人逐只构成不建模(第一期随机输出面无
  消费)。词缀列表 = 局级输入(RunConfig);「开局不利」恒 −20 HP 由
  M01 ``cw_opening_hp`` 单一承载(词缀采样分支禁再实现任何 HP 类修正);
  词缀对战斗数值面的影响随第一期随机输出面无消费。

随机流键(后端侧装配):boss 逐位面采样 ``M20/boss/{plane}``。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from sr_od.application.currency_war.kernel.cw_difficulty_account import (
    GROWTH_PER_STREAK,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    get_strategy,
    normalize_invest_name,
)

#: 品质加成表(白0/金3/彩6 每持 1 个;economy.md §9 已定案;银=白档 0)。
QUALITY_DIFFICULTY_BONUS: dict[str, int] = {'银': 0, '金': 3, '棱彩': 6}

#: 遭遇等级加成四档真值(其一0/其二10/其三20/其四30;economy.md §9 已定案;
#: 归宿 = 难度账域(本模块,与加成消费同域);单一消费面 = 难度派生
#: ``difficulty_of``——遭遇选项生成面不读本表,档数走 backend
#: ``encounter_options`` 独立常量)。
ENCOUNTER_TIER_BONUS: tuple[int, ...] = (0, 10, 20, 30)

#: 圣杯试炼特殊加成真值(economy.md §9 已定案 +30;激活态 = fate overlay
#: 占位面,首版恒未激活——披露键见 :data:`HOLY_GRAIL_PENDING`)。
HOLY_GRAIL_BONUS: int = 30
HOLY_GRAIL_PENDING: str = 'holy_grail_activation_pending_u14'

#: 基础难度曲线未采披露键(U25;基础 None 时 total 亦 None,禁插值)。
DIFFICULTY_BASE_PENDING_U25: str = 'difficulty_base_curve_pending_u25'

#: boss 去重语义占位披露键(bosses.md「池中随机 3」的放回/不放回无档,
#: 首版逐位面独立放回采样)。
BOSS_DEDUP_PENDING: str = 'plane_boss_dedup_pending_u02'


@dataclass(frozen=True)
class DifficultyBreakdown:
    """难度账分解(已定案成分逐项披露;base None = 基础曲线未采)。"""

    #: 基础难度(节点曲线分量;U25 候实机数据,补采前恒 None)
    base: int | None
    #: 持卡品质加成合计(金3/彩6 每持 1)
    quality_bonus: int
    #: 遭遇等级加成(所选档;非遭遇节点 = 0)
    encounter_tier_bonus: int
    #: 特殊加成合计(伟大征服 streak 项;圣杯项未激活恒 0)
    special_bonus: int
    #: 策略静态 Δ 合计(节点型限定已应用;压难度为负值)
    strategy_delta: int
    #: 合计(base None → None:缺基础分量禁出合计值)
    total: int | None


@dataclass(frozen=True)
class DifficultyRecord:
    """难度账快照(每场战斗结算时点一条;2026-10-14 用户裁定:sim 对
    选择后的难度做记录更新)。

    - 时点语义 = 「这一仗按什么难度打」:品质分量/策略静态 Δ 取已选
      策略结算前现值,特殊加成取胜负前连胜(连胜转移在结算后),
      遭遇档取该节点所选档;base 恒 None(U25 基础曲线未采,禁插值)、
      圣杯恒未激活(fate 占位面)。
    - 纯簿记零结算耦合:难度不接入胜负面(胜负建模另批),零随机流
      消费。落账方 = sim 后端 ``_resolve_battle``,消费方 = 验收测试与
      后续难度分析。
    - 坐标系:``plane``/``round_num`` = 节点序位(与 ``gs.node`` 同源);
      ``node_kind`` = 结算节点类型(battle/encounter/boss/reward 等
      结算路径覆盖的战斗类节点;非战斗节点无难度语义不落账)。
    """

    plane: int
    round_num: int
    node_kind: str
    breakdown: DifficultyBreakdown


def _strategy_delta_of(strategy_names: list[str], node_kind: str,
                       ) -> tuple[int, int]:
    """策略静态 Δ 合计(节点型限定在此应用)。

    Returns:
        ``(静态 Δ 合计, 伟大征服族 per_streak 系数合计)``——动态项与
        节点无关(连胜驱动),静态项按 ``difficulty_node_types`` 过滤
        (注册表词 '遭遇'/'首领' ↔ 节点词表 'encounter'/'boss' 映射)。
    """
    node_type_cn = {'encounter': '遭遇', 'boss': '首领'}.get(node_kind, '')
    delta_sum = 0
    per_streak_sum = 0
    for raw in strategy_names:
        s = get_strategy(normalize_invest_name(raw))
        if s is None or s.economy is None:
            continue
        e = s.economy
        if e.difficulty_delta:
            scoped = e.difficulty_node_types
            if not scoped or node_type_cn in scoped:
                delta_sum += e.difficulty_delta
        if e.difficulty_per_streak:
            per_streak_sum += e.difficulty_per_streak
    return delta_sum, per_streak_sum


def difficulty_of(strategy_names: list[str], *, node_kind: str,
                  streak: int, encounter_tier: int | None = None,
                  base: int | None = None,
                  holy_grail_active: bool = False,
                  ) -> DifficultyBreakdown:
    """难度账派生(M19;纯函数,全部输入显式传入)。

    - ``streak`` = 收入侧无符号连胜计数(伟大征服动态项乘子);
    - ``encounter_tier`` = 遭遇所选档 1 基(1..4);非遭遇节点传 None;
    - ``base`` = 基础难度(局级输入档读数可传,节点曲线未采时 None);
    - ``holy_grail_active`` = 圣杯试炼激活态(fate 占位面,首版恒 False)。
    """
    quality = 0
    for raw in strategy_names:
        s = get_strategy(normalize_invest_name(raw))
        if s is not None:
            # 难度豁免守卫(注册面 = cw_investments
            # .difficulty_inflation_exempt,全注册表唯一挂值 = 远见;
            # P51 diff_formula 同式跳过整条目):读法 A 自身豁免——远见
            # 自身 rarity 不计品质通胀。依据链 = 实现惯例链(registry
            # 字段落位 + P51 代码化 + 知识文档转抄),773 轮聚合对账对本
            # 分支系空载背书不构成实证;证伪通道 = sim 随局披露键
            # FORESIGHT_EXEMPTION_READING(远见局 settled 备战帧敌方
            # 难度读数逐轮微分,归遥测批)。
            if (s.economy is not None
                    and s.economy.difficulty_inflation_exempt):
                continue
            quality += QUALITY_DIFFICULTY_BONUS.get(s.rarity, 0)
    tier_bonus = (ENCOUNTER_TIER_BONUS[encounter_tier - 1]
                  if encounter_tier is not None
                  and 1 <= encounter_tier <= len(ENCOUNTER_TIER_BONUS) else 0)
    delta, per_streak = _strategy_delta_of(strategy_names, node_kind)
    special = round(per_streak * GROWTH_PER_STREAK * streak)
    if holy_grail_active:
        special += HOLY_GRAIL_BONUS
    known = quality + tier_bonus + special + delta
    total = (base + known) if base is not None else None
    return DifficultyBreakdown(base=base, quality_bonus=quality,
                               encounter_tier_bonus=tier_bonus,
                               special_bonus=special,
                               strategy_delta=delta, total=total)


# ============================================================ M20 boss 名单

def boss_pool() -> tuple[str, ...]:
    """boss 全池(20 名;数据源 = ``data/cw_enemy_data.BOSS_MECHANICS``
    注册表键集,bosses.md 2026-08-17 全量重采)。"""
    from sr_od.application.currency_war.data.cw_enemy_data import (
        BOSS_MECHANICS,
    )
    return tuple(sorted(BOSS_MECHANICS))


def sample_plane_boss(rng: random.Random, plane: int) -> str:
    """单一位面 boss 采样(池均匀放回;``M20/boss/{plane}`` 流,引擎
    装配逐位面子流——去重语义无档,披露 :data:`BOSS_DEDUP_PENDING`)。"""
    pool = boss_pool()
    return pool[rng.randrange(len(pool))]


def resolve_plane_bosses(override: tuple[str | None, str | None, str | None]
                         | None,
                         sample: random.Random) -> tuple[str | None,
                                                         str | None,
                                                         str | None]:
    """三位面 boss 名单(RunConfig 局级输入优先,U02)。

    ``override`` 位非 None 直用(局级输入);None 位 → 内置池采样。
    ``sample`` = 引擎装配的 ``M20/boss`` 合流子流(逐位面依序消耗)。
    """
    return tuple(override[i] if override is not None
                 and override[i] is not None
                 else sample_plane_boss(sample, i + 1)
                 for i in range(3))
