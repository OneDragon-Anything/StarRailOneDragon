"""终局线选择内核(候选-锁定制;line_and_upgrade §1;迭代
2026-10-12-prep-shop-workflow-redesign 批 3.7)。

判据唯一源 = line_and_upgrade §1(候选-锁定制,用户裁定 2026-10-12 选线
专题定稿:硬规则查表判据 + 零标定参数)。本模块承载三件:

- **热度映射常量表**(:data:`LINE_HEAT`)——排序立场数据(换策略会换
  值),按宪法第 5 条落策略层 mandate_v1 侧,**不落 kernel**(玩法知识
  四字段清单不含它);数据源 = final_comps 类索引表十类帖数;
- **线分数**(§1.2 字典序:环境分级 → 持有证据级 → 攻略热度——比较序
  逐级,先高级定序再比下级,零拟合参数)+ top3 候选;
- **锁定双触发判定**(§1.4:硬规则查表〔策略型/角色型,知识卡原语
  ``strategy_lock_hit``/``char_lock_hit`` 单一判定源〕+ 时点兜底;同帧
  多命中裁决 = 线分数最高 + 热度 tie-break + COMP_LIBRARY 注册序终局,
  **禁遍历序隐式定锁**)。

锁定写入与连带动作的唯一所有者 = :func:`session_scope.write_line_lock`
(本模块只产判定,不写键——禁绕过 write_line_lock 直写锁定线槽)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_comps import (
    COMP_LIBRARY,
    carry_set,
    char_lock_hit,
    strategy_lock_hit,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import GameState


#: 攻略热度映射常量表(§1.2 平分裁定行;[38] 修订版——线分数平分时按
#: 攻略热度定优先级,十类帖数降序)。**排序立场数据**:换一套策略实现
#: 可能要不同的 tie-break → 落策略层,禁迁 kernel(宪法第 5 条)。
#:
#: 数据源 = docs/game/currency_war/research/final_comps/README.md 类索引表
#: 「篇数」列(官方投稿 API 784 篇 Final 段,十类深读已登记):十类各自
#: 取类级篇数;COMP_LIBRARY 20 线按类归属映射——同类多线(圣杯双核心
#: 两线/DOT 两线)共享类帖数;**其他长尾桶(~40,README 已登记值)覆盖
#: 八条无专篇长尾线**(千冶减益/巡海击破/龙丹战技点/火花星间旅人/
#: 银枝群攻/昼神阿雅/追击飞霄/景元仙舟)——桶内热度不可分,终局裁定
#: 走 COMP_LIBRARY 注册序首线(§1.2 显式规则声明,非遍历序隐式定锁)。
#: 未登记线热度取 0(缺表 fail 方向 = 热度维最低)。
LINE_HEAT: dict[str, int] = {
    # —— 十类(类级篇数)——
    '列车同行': 274,        # 姬子列车
    '命运圣杯红A': 118,     # 圣杯双核心
    '双王圣杯': 118,        # 圣杯双核心
    '狼尊欢愉': 68,         # 银狼欢愉
    '黄泉减益': 50,
    '万敌单C': 40,          # 万敌燃血
    '希儿量子': 38,
    '反甲白厄': 38,         # 白厄反甲
    '大黑塔银河学者': 38,   # 大黑塔群攻
    '绯英欢愉': 25,
    'DOT队': 20,            # DOT 卡芙卡
    '专家桑博DOT': 20,      # DOT 卡芙卡(桑博专家变体)
    # —— 其他长尾桶(~40;桶内终局裁定 = 注册序)——
    '千冶减益': 40,
    '巡海击破': 40,
    '龙丹战技点': 40,
    '火花星间旅人': 40,
    '银枝群攻': 40,
    '昼神阿雅': 40,
    '追击飞霄': 40,
    '景元仙舟': 40,
}

#: COMP_LIBRARY 注册序索引(§1.2 共享热度的终局裁定 = 注册序首线;
#: 「显式规则声明,非遍历序隐式定锁——稳定且可实现」)。
_COMP_REG_INDEX: dict[str, int] = {c.name: i for i, c in enumerate(COMP_LIBRARY)}

#: 候选数量(用户裁定 2026-10-12:候选数量 = 3;§1.3)。
CANDIDATE_TOP_N: int = 3


def held_chars_of(gs: GameState) -> frozenset[str]:
    """持有角色名集(bench ∪ 场上;锁定判定与持有证据分的持有读面)。

    空名不计(占位件/未识别件不构成持有证据)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_units_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(gs)
    names = {u.char_id for u in (*front, *back, *bench_units_of(gs))
             if u is not None and u.char_id}
    return frozenset(names)


def held_invest_names_of(gs: GameState) -> frozenset[str]:
    """已持有投资名集(投资策略名单 ∪ 已选投资环境;策略型锁定与
    环境分级的输入面——``strategy_lock_hit`` 契约:消费侧组好传入)。"""
    strategies = list(gs.active_strategies.value or ())
    env = gs.active_env.value
    if env:
        strategies.append(env)
    return frozenset(strategies)


def line_score_key(comp: Comp, held_chars: frozenset[str],
                   held_invest: frozenset[str]) -> tuple[int, int, int, int, int]:
    """线分数比较键(§1.2 字典序的排序载体;升序排序消费,各维取负
    使「高级在前」)。

    比较序逐级(先高级定序再比下级,纯字典序 + 计数,零连续加权/零
    相对幅度参数):

    1. **环境分级**:强关联策略命中线 = 最高级(``strategy_lock_hit``
       查 ``lock_rules`` 策略型——环境分的强关联高分同源本字段,§1.2),
       其余普通级——策略型信号门槛级语义,非加数;
    2. **持有证据级**:CARRY 有无(``carry_set`` 合流口径)→ 骨架计数
       (``key_items``)→ 插件计数(线成员 − CARRY − 骨架余集,派生)——
       已有越多分越高,替换成本语义由此承载;
    3. **攻略热度**::data:`LINE_HEAT` 查表。

    终局裁定(全维平分)= COMP_LIBRARY 注册序(:func:`_line_sort_key`
    追加注册序维;同帧多命中裁决与候选排序共用同一全序,禁遍历序)。
    """
    env_tier = 1 if strategy_lock_hit(comp, held_invest) else 0
    carry = carry_set(comp)
    carry_hit = 1 if (carry & held_chars) else 0
    skeleton = len(set(comp.key_items or ()) & held_chars)
    members = set(comp.core_chars) | set(comp.shared_chars or ())
    plugin = len((members - carry - set(comp.key_items or ())) & held_chars)
    heat = LINE_HEAT.get(comp.name, 0)
    return (-env_tier, -carry_hit, -skeleton, -plugin, -heat)


def _line_sort_key(comp: Comp, held_chars: frozenset[str],
                   held_invest: frozenset[str]) -> tuple:
    """全序排序键(线分数 + 注册序终局;候选快照与锁定裁决的同一全序)。"""
    return (*line_score_key(comp, held_chars, held_invest),
            _COMP_REG_INDEX.get(comp.name, len(COMP_LIBRARY)))


def compute_candidates(held_chars: frozenset[str],
                       held_invest: frozenset[str]) -> tuple[str, ...]:
    """全 20 线算分取 top N 候选(§1.3:每帧对全部线算分,top3 为候选;
    签名幂等——同持有面重算同值)。返回线名元组(分数降序)。"""
    ranked = sorted(COMP_LIBRARY,
                    key=lambda c: _line_sort_key(c, held_chars, held_invest))
    return tuple(c.name for c in ranked[:CANDIDATE_TOP_N])


def hard_lock_hit_lines(held_chars: frozenset[str],
                        held_invest: frozenset[str]) -> tuple[str, ...]:
    """硬规则命中线集(§1.4 双触发的硬规则半边,随时可锁含 P1)。

    每线一条显式条件(``lock_rules``):策略型 = 强关联策略任一到手
    (OR);角色型 = 关键角色组合全员在手(AND)。判定单一源 = 知识卡
    原语 ``strategy_lock_hit``/``char_lock_hit``,禁消费位自拼子集判定。
    返回按线分数全序排序的命中线名(同帧多命中裁决取首)。
    """
    hits = [c for c in COMP_LIBRARY
            if char_lock_hit(c, held_chars)
            or strategy_lock_hit(c, held_invest)]
    hits.sort(key=lambda c: _line_sort_key(c, held_chars, held_invest))
    return tuple(c.name for c in hits)


def evaluate_lock(candidates: tuple[str, ...],
                  held_chars: frozenset[str],
                  held_invest: frozenset[str], *,
                  plane2_started: bool,
                  p2_strategy_pick_done: bool) -> str | None:
    """锁定判定(§1.4 双触发,先到先锁;返回应终局阵容锁定名,None = 不锁)。

    - **硬规则**:命中线按线分数全序取首(同帧多命中裁决 = 线分数
      最高 + 热度 tie-break + 注册序终局——与候选排序同一全序,
      ``hard_lock_hit_lines`` 内承载,禁遍历序);
    - **时点兜底**:时点后仍无硬条件命中 → 锁定 top3 中分数最高者
      (平分按攻略热度;候选元组已按全序降序,取首)。触发 =
      ``plane2_started``(3.1 窗口谓词:第 10 结点 = 首入 (2,*) 段,
      P1 内即时/延迟加场卡被结算节点边界锚排除)∧ ``p2_strategy_pick_done``
      (P2 起首次投资策略三选一完成——active_strategies 集合增长侦测)。

    锁后只读由调用侧(``session_scope`` 锁定守卫)承载:本函数只在
    未锁定态被求值。
    """
    hits = hard_lock_hit_lines(held_chars, held_invest)
    if hits:
        return hits[0]
    if plane2_started and p2_strategy_pick_done and candidates:
        return candidates[0]
    return None
