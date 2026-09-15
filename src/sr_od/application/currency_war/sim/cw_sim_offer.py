"""sim 重做·投资策略/环境 offer 引擎(M11/M02)与注入核。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M11/M02、§2.3 U07/U08、
§2.4.1(cw_sim_invest 预置面删除、注入核保留改接 U07 固定轮次):

- **offer 日程 = 固定轮次**(U07① 已裁决):P1r3/P2r2/P3r2 各一次,
  触发 = 打完 1-2 / 2-1 / 3-1(节点结算完成,生效于下一轮备战窗口);
  罕见离群触发点(观测 ~1-2%,触发源未归因)不建模,作 sim 披露;
  P3r2 受 M03「P3 未观测不运行」辖域约束,补采后自然生效;
- **开局 (1,1) 无策略选卡**(U07②);开局环境屏 = RunConfig.env_present
  为真时的 opening_env 相位(U08:候选 3 占位选 1,结构与 U07 同构);
- **候选生成**(U07③):先随机品质、再从该品质池均匀取 1 张;
  offer 内去重,**全程不重复**(已出选项不再入本局任何后续 offer,
  刷新重掷同规则排除);
- 品质分布 = 显式常量参数(候实机数据回填;首版三档均匀 = 中性占位,
  不伪装实证分布,随披露面申报);环境无品质注册(``PlazaPortal``
  无 rarity 字段,亲验 ``data/cw_invest_data.py``)→ 环境 offer 按
  排除后全池均匀,品质掷点不适用(披露键见
  :data:`ENV_QUALITY_DISCLOSURE`);
- **联席决策**(注册表 id122)→ 2-6 节点额外策略选卡槽(机制文档
  原文;u07u28 报告样本未命中,候实机对账);
- 品质覆写族环境(彩虹/黄金/白银时代/头彩/尾彩/银·金·彩,注册表
  id110/111/112/123/124/135)首版不建模:命中即披露(设计稿 M11
  挂钩清单仅点名联席决策,覆写族候实机对账后建模;
  :data:`QUALITY_REWRITE_ENV_NAMES` 供引擎层披露判据);
- **注入核**(定向测试通道,§2.4.1 保留面):显式点名投资选择直写
  容器,绕过 offer 采样——供定向测试在固定持卡/环境下驱动策略器;
  旧 SimInvestProfile 预置剧本与 plaza 频次候选(统计镜像,§0 已裁
  边界⑤)随旧 ``cw_sim_invest.py`` 删除面消亡(S10),本模块 = 注入核
  与 offer 引擎的重做归宿(与 r1 对 ``sim/pool.py`` 同款「能力迁居、
  文件名换新」处置)。

随机流键(引擎侧装配):策略 ``M11/offer/{plane}/{round}``、
环境 ``M02/env-offer``。
"""
from __future__ import annotations

import random
from collections.abc import Iterable, Set

from sr_od.application.currency_war.kernel.cw_game_state import GameState
from sr_od.application.currency_war.kernel.cw_investments import (
    INVESTMENT_ENVS,
    INVESTMENT_STRATEGIES,
)
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

#: 策略 offer 固定日程(U07① 已裁决;(plane, round_num) 对;P3r2 随
#: M03 P3 辖域自然延后生效)。
INVEST_OFFER_SCHEDULE: tuple[tuple[int, int], ...] = ((1, 3), (2, 2), (3, 2))

#: 联席决策环境注册表规范名(id122;效果原文「在2-6节点进行一次额外的
#: 投资策略三选一」)。
JOINT_DECISION_ENV_NAME: str = '联席决策'

#: 联席决策额外策略选卡槽(机制文档口径挂 2-6;样本未命中候实机对账)。
JOINT_DECISION_EXTRA_SLOT: tuple[int, int] = (2, 6)

#: 单次 offer 候选张数(画面语义三选一;环境屏同构占位,U08)。
OFFER_CANDIDATES: int = 3

#: 品质掷点分布(显式常量参数,候实机数据回填;首版三档均匀 = 中性
#: 占位非实证,随局披露键 :data:`QUALITY_DISTRIBUTION_DISCLOSURE`)。
QUALITY_DISTRIBUTION: tuple[tuple[str, float], ...] = (
    ('银', 1.0 / 3.0), ('金', 1.0 / 3.0), ('棱彩', 1.0 / 3.0),
)

#: 品质分布占位披露键(均匀占位非实证;候实机回填后移除)。
QUALITY_DISTRIBUTION_DISCLOSURE: str = 'invest_quality_distribution_uniform_pending'

#: 环境品质维度缺失披露键(PlazaPortal 无 rarity 注册,品质掷点不适用)。
ENV_QUALITY_DISCLOSURE: str = 'env_quality_not_registered'

#: 品质覆写族环境在册名(注册表 id110/111/112/123/124/135;首版不建模,
#: 命中即披露,披露键 :data:`QUALITY_REWRITE_ENVS_PENDING`)。
QUALITY_REWRITE_ENV_NAMES: frozenset[str] = frozenset({
    '彩虹时代', '黄金时代', '白银时代', '头彩', '尾彩', '银·金·彩',
})

#: 品质覆写族未建模披露键。
QUALITY_REWRITE_ENVS_PENDING: str = 'invest_quality_rewrite_envs_pending'

#: 离群触发点未建模披露键(U07① ~1-2% 触发源未归因,不作机制建模)。
OFFER_OUTLIER_DISCLOSURE: str = 'invest_offer_outlier_triggers_unmodeled'


def offer_slots(plane: int, round_num: int,
                active_env: str | None) -> bool:
    """该 (plane, round_num) 是否存在策略 offer 槽。

    固定日程(U07①)∨ 联席决策额外槽(id122 挂 2-6;环境按容器
    ``active_env`` 现值判定)。环境名不可辨(None/空)→ 仅按固定日程。
    """
    key = (int(plane), int(round_num))
    if key in INVEST_OFFER_SCHEDULE:
        return True
    return (key == JOINT_DECISION_EXTRA_SLOT
            and (active_env or '') == JOINT_DECISION_ENV_NAME)


def _roll_quality(rng: random.Random) -> str:
    """品质掷点(按 :data:`QUALITY_DISTRIBUTION` 加权;概率质量恒和 1)。"""
    qualities = [q for q, _ in QUALITY_DISTRIBUTION]
    weights = [w for _, w in QUALITY_DISTRIBUTION]
    return rng.choices(qualities, weights=weights, k=1)[0]


def sample_strategy_offer(rng: random.Random, excluded: Iterable[str],
                          ) -> tuple[str, ...]:
    """策略 offer 候选生成(U07③:先掷品质 → 该品质池均匀取 1;
    offer 内去重 + 排除已出选项 = 全程不重复,刷新重掷同规则)。

    ``excluded`` = 本局已出过的全部选项名(引擎持有的累计集;调用方
    须把返回值并入该集)。边界:某品质池被排除集吃光(极端局)→ 该
    候选回退全池(排除后)取;全池亦空 → 候选数不足如实少发(注册表
    335 张、单局最多出 ~6 张,两边界实际不可达,防御性声明)。
    """
    banned = set(excluded)
    picks: list[str] = []
    for _ in range(OFFER_CANDIDATES):
        quality = _roll_quality(rng)
        pool = [n for n, s in INVESTMENT_STRATEGIES.items()
                if s.rarity == quality and n not in banned]
        if not pool:
            pool = [n for n in INVESTMENT_STRATEGIES if n not in banned]
        if not pool:
            break
        name = pool[rng.randrange(len(pool))]
        picks.append(name)
        banned.add(name)
    return tuple(picks)


def sample_env_offer(rng: random.Random, excluded: Iterable[str],
                     ) -> tuple[str, ...]:
    """环境 offer 候选生成(U08 与 U07 同构;环境无品质注册 → 排除后
    全池均匀,品质掷点不适用——披露面消费 :data:`ENV_QUALITY_DISCLOSURE`)。
    """
    banned = set(excluded)
    pool = sorted(n for n in INVESTMENT_ENVS if n not in banned)
    if not pool:
        return ()
    k = min(OFFER_CANDIDATES, len(pool))
    return tuple(rng.sample(pool, k))


def apply_env_pick(bs: GameState, name: str) -> None:
    """环境选卡入账(obs 渠道写容器 ``active_env``;实机写点语义 =
    cw_screen_invest_env 选 1 张定局)。"""
    bs.observe(bs.active_env, name, evidence=sim_evidence('env:pick'),
               sig=obs_sig(group_id='sim:env'))


def apply_strategy_pick(bs: GameState, name: str) -> None:
    """策略选卡入账(obs 渠道 append 容器 ``active_strategies``)。

    去重防重选与实机 handler 对齐(cw_screen_invest_strategy 同名不
    重复入列);已持名的重发属引擎侧生成规则问题(U07③ 全程去重),
    此处兜底不重复入列。
    """
    held = list(bs.active_strategies.value or [])
    if name in held:
        return
    held.append(name)
    bs.observe(bs.active_strategies, held,
               evidence=sim_evidence('invest:pick'),
               sig=obs_sig(group_id='sim:invest'))


def inject_choices(bs: GameState, *, env_name: str | None = None,
                   strategy_names: Iterable[str] = (),
                   ) -> None:
    """注入核:显式点名投资选择直写容器(定向测试通道,§2.4.1 保留面)。

    绕过 offer 采样与策略器裁决——定向测试要「固定环境/固定持卡下
    驱动策略器」时,reset 后调用本函数把选择定死;日程仍由引擎按
    U07 固定轮次触发(注入只定「选什么」,不定「何时出现」)。
    环境名/策略名不做注册表校验(定向测试可注入任意名字;误名会在
    经济聚合/品质查询侧显式 miss,不在注入层静默改写)。
    """
    if env_name is not None:
        apply_env_pick(bs, env_name)
    for name in strategy_names:
        apply_strategy_pick(bs, name)


def quality_rewrite_hit(active_env: str | None) -> bool:
    """当前环境是否命中品质覆写族(引擎层披露判据;首版不建模,
    命中即按 :data:`QUALITY_REWRITE_ENVS_PENDING` 披露)。"""
    return (active_env or '') in QUALITY_REWRITE_ENV_NAMES


def offer_exclusions_snapshot(excluded: Set[str]) -> tuple[str, ...]:
    """已出选项累计集的稳定快照(引擎交接/判读用;排序保证可复现)。"""
    return tuple(sorted(excluded))
