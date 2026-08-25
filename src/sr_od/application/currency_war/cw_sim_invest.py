"""货币战争 sim 投资策略/环境注入(W162/ADR-0364)。

背景缺口(W161 裁决):cw_sim 全文不建模 ``active_strategies``/``active_env``
——实机这两者由 handle_invest_strategy/handle_invest_env 局中采集并进 session
(消费面:意向层①资格通道[ADR-0338 直通线锁定]、economy 聚合、cw_events 打分)。
W145(ADR-0357)后 P1 锁 comp 仅剩①资格通道 → sim 缺输入 = ①通道永不点火 →
P1 永不锁 comp → V_D 目标恒空 → sim 一切含 D 的 P1 结论零外推力
(W161:757/757 帧死在「①目标空」)。

本模块 = 注入的**数据面单一源**:
- ``SimInvestProfile``:注入剧本(环境名 + 逐(位面,轮)的策略选卡日程);
- ``sample_invest_profile(seed)``:按 plaza 实选频次分布确定性采样
  (独立 rng 流,不触碰 sim 主 rng → 默认关 = 主路径逐位零漂移);
- 选卡频次表 = ``cw_plaza_comps.PLAZA_CARRY_CLUSTERS`` 聚合(784 篇高难帖
  augs/portals 频次;注册表外名字丢弃并计数披露——plaza 名与注册表名的
  分隔符差异[全角冒号等]在 ``_canon`` 归一)。

注入语义与实机 handler 对齐(单一源参照):
- 环境:开局选 1 张,写 ``session.active_env``(handle_invest_env L197);
- 策略:按日程逐张选,append 进 ``session.active_strategies``(去重防重选,
  handle_invest_strategy L200-202);session→state 的每帧同步在生产由
  cw_observation 完成,sim 侧由 cw_sim 在注入点直写两处(等价语义)。

注入后 sim 经济聚合生效的字段子集(其余字段不建模,见 ADR-0364 排除表):
``instant_gold``(选卡时点)/ ``gold_per_node`` / ``interest_cap_override`` /
``free_refresh_per_node``。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimInvestProfile:
    """单局注入剧本(显式传入 = 固定剧本集用法;见 ADR-0364 选型)。

    :param active_env: 开局投资环境名(注册表规范名;空 = 本局无环境)
    :param picks: 逐(位面, 轮)的策略选卡日程,元素 = (plane, round, 策略名)。
        同一 (plane, round) 至多一条(实机同一屏只选一张);重名跨轮出现时
        按 handler 去重语义忽略(不重复入列)。
    """
    active_env: str = ''
    picks: tuple[tuple[int, int, str], ...] = ()


# ===== 选卡日程(实机 replay 真值;decisions.jsonl 63 局 + entry 流程) =====
# 数据边界:活跃频次 = decisions.jsonl 里 active_strategies 计数增加的轮
# (63 局,43 局进 P2);entry 屏(简报→投资环境→投资策略→备战)的开局
# 选卡在遥测里不可见(match 建立前写点丢失,见 W162 报告残缺清单),
# 按流程固定出现建 (1,1) 必选。
SIM_STRATEGY_PICK_SCHEDULE: tuple[tuple[int, int, float], ...] = (
    (1, 1, 1.0),    # 开局投资策略屏(entry 流程固定;50/63 主选卡在 P1 r3,
                    # entry 卡遥测不可见——两张都建,r3 概率按可见口径)
    (1, 3, 0.79),   # P1 r3 主选卡(50/63 局)
    (1, 9, 0.08),   # P1 末段二卡(r4/r7/r9 合计 5/63)
    (2, 2, 0.40),   # P2 r2(17/43 进场局)
    (2, 6, 0.02),   # P2 r6 罕见(1/43)
)


def _canon(name: str) -> str:
    """plaza 原始名 → 注册表规范名的无歧义归一(全角冒号→半角)。

    plaza 数据用全角冒号(如「骇客专家：银狼」),注册表键是半角;
    normalize_invest_name 只归一分隔符族(·),冒号在此归一。
    """
    return name.replace('：', ':')


def _plaza_freq(counter_field: str,
                is_known) -> tuple[tuple[str, int], ...]:
    """聚合 PLAZA_CARRY_CLUSTERS 的频次字段 → 注册表内 (名, 频次) 表。

    注册表外名字丢弃(数据缺口披露给调用方);频次跨聚类求和
    (全局经验分布,不做条件化——plaza 聚类按终局 carry 分桶,注入
    反向作用于选线,条件化会制造循环因果)。
    """
    from sr_od.application.currency_war.cw_plaza_comps import (
        PLAZA_CARRY_CLUSTERS,
    )
    agg: dict[str, int] = {}
    for cluster in PLAZA_CARRY_CLUSTERS:
        for name, cnt in getattr(cluster, counter_field):
            key = _canon(name)
            if not is_known(key):
                continue
            agg[key] = agg.get(key, 0) + int(cnt)
    return tuple(sorted(agg.items(), key=lambda kv: -kv[1]))


_FREQ_CACHE: dict[str, tuple[tuple[str, int], ...]] = {}
_FREQ_DROPPED: dict[str, int] = {}


def _freq(counter_field: str, is_known) -> tuple[tuple[str, int], ...]:
    """频次表惰性构建 + 缓存(导入期零开销;丢名字计数披露)。"""
    ck = counter_field
    if ck not in _FREQ_CACHE:
        from sr_od.application.currency_war.cw_plaza_comps import (
            PLAZA_CARRY_CLUSTERS,
        )
        dropped: dict[str, int] = {}
        for cluster in PLAZA_CARRY_CLUSTERS:
            for name, cnt in getattr(cluster, counter_field):
                key = _canon(name)
                if not is_known(key):
                    dropped[key] = dropped.get(key, 0) + int(cnt)
        _FREQ_CACHE[ck] = _plaza_freq(counter_field, is_known)
        _FREQ_DROPPED.update(dropped)
    return _FREQ_CACHE[ck]


def strategy_freq_table() -> tuple[tuple[str, int], ...]:
    """投资策略实选频次表(plaza 聚合,注册表内;判读/测试用)。"""
    from sr_od.application.currency_war.cw_investments import get_strategy
    return _freq('augs', lambda n: get_strategy(n) is not None)


def env_freq_table() -> tuple[tuple[str, int], ...]:
    """投资环境偏好频次表(plaza 聚合,注册表内;判读/测试用)。"""
    from sr_od.application.currency_war.cw_investments import get_env
    return _freq('portals', lambda n: get_env(n) is not None)


def freq_dropped_names() -> dict[str, int]:
    """频次聚合中被丢弃的注册表外名字(数据缺口披露)。"""
    return dict(_FREQ_DROPPED)


def _weighted(rng: random.Random,
              table: tuple[tuple[str, int], ...]) -> str:
    """按频次加权抽名(表空 → ''=本局不注入)。"""
    if not table:
        return ''
    names = [n for n, _ in table]
    weights = [c for _, c in table]
    return rng.choices(names, weights=weights, k=1)[0]


def sample_invest_profile(seed: int) -> SimInvestProfile:
    """按 seed 确定性采样注入剧本(ADR-0364 选型 a+c)。

    独立 rng 流(字符串种子命名空间,与 sim 主 rng 无交集)——同 seed
    同剧本,A/B 两臂同 seed 即同注入 = 配对可比;主 rng 消耗序不受影响
    (invest=False 的局逐位零漂移)。
    """
    rng = random.Random(f'w162-invest-{seed}')
    env = _weighted(rng, env_freq_table())
    held: set[str] = set()
    picks: list[tuple[int, int, str]] = []
    for plane, rnd, prob in SIM_STRATEGY_PICK_SCHEDULE:
        if rng.random() >= prob:
            continue
        name = _weighted(rng, strategy_freq_table())
        if not name or name in held:
            continue   # handler 去重语义:同名不重复入列
        held.add(name)
        picks.append((plane, rnd, name))
    return SimInvestProfile(active_env=env, picks=tuple(picks))


@dataclass(frozen=True)
class InvestInjectionState:
    """注入执行态(cw_sim 消费;也可供测试断言)。"""
    profile: SimInvestProfile
    picks_by_key: dict[tuple[int, int], str] = field(default_factory=dict)

    @classmethod
    def build(cls, profile: SimInvestProfile) -> InvestInjectionState:
        return cls(profile=profile,
                   picks_by_key={(p, r): n for p, r, n in profile.picks})
