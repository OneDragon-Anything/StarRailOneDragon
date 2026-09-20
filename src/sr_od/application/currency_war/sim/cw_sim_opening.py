"""sim 重做·对局开局(M01)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M01 / U15 / U28 已裁决口径:

- 开局 HP = ``kernel/cw_opening_hp.opening_hp_prior`` 查表(唯一单一
  承载方;「开局不利」恒 −20 内嵌于该表,词缀引擎禁再实现 HP 类修正,
  R5 折入定案);无实证档(非 A8/108)**报错索样本,不外推**(U15);
- 开局经济 = 金 3 / 等级 3 / deploy_cap 3(u07u28 报告 §③,两独立源
  一致;旧「金 5」为开局帧读数偏差已废,U28);
- 开局手牌 = 4 张全 1★,费用形状 (1,1,1,3) 概率 2/3、(1,1,2,2) 概率
  1/3(U28 已裁决,流键 ``M01/opening_hand``);卡名 = 形状定档后按各自
  费用档从 M06 固定牌库该费档名集内均匀抽名(开局时 held 为空,等价
  于全池均匀;开局补给通道真实名单分布候实机数据,U28 候实机数据行);
- 开局备战席写入 = M06 派生池不变量(剩余 = 固定 − held)的**首个写端**,
  先于任何商店发牌(held 由容器 bench/deployed 星级派生,M06);
- 不属本模块:环境 offer(RunConfig.env_present 为真时由 M02 引擎采样)。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_chars import Character, chars_by_cost
from sr_od.application.currency_war.data.cw_shop_odds import POOL_COPIES_PER_CARD
from sr_od.application.currency_war.kernel.cw_economy import XP_TO_NEXT_LEVEL
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    bench_place,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    BenchSlot,
    GameState,
    Unit,
    bench_view_of_working,
)
from sr_od.application.currency_war.kernel.cw_opening_hp import opening_hp_prior
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence
from sr_od.application.currency_war.sim.cw_sim_run_config import RunConfig

#: 开局手牌张数(U28 定案四要素之一;替换旧 START_BENCH_COUNT 遥测校准)。
OPENING_HAND_SIZE: int = 4

#: 开局手牌费用形状采样表(U28 已裁决):(1,1,1,3) 2/3、(1,1,2,2) 1/3。
#: 元素 = (费用形状, 概率);概率质量恒和 1,替换旧 START_BENCH_COST_
#: WEIGHTS(1/2 费 65/35,永抽不到 3 费、2 费占比高估一倍)。
OPENING_HAND_SHAPES: tuple[tuple[tuple[int, ...], float], ...] = (
    ((1, 1, 1, 3), 2.0 / 3.0),
    ((1, 1, 2, 2), 1.0 / 3.0),
)

#: 开局固定初值(u07u28 报告 §③;U28 同帧定案)。
OPENING_GOLD: int = 3
OPENING_LEVEL: int = 3
OPENING_DEPLOY_CAP: int = 3


class OpeningHpUnsampledError(RuntimeError):
    """开局 HP 无实证档时的显式停机(U15 定稿口径:按实证档硬表,
    无实证档报错索样本,禁外推)。"""


def opening_hp_or_raise(cfg: RunConfig) -> int:
    """开局 HP 真值(实证档查表;无实证档 = :class:`OpeningHpUnsampledError`)。

    查表单一源 = ``cw_opening_hp.opening_hp_prior``(133 局普查;A8/108
    基础 82、「开局不利」恒 −20 → 62)。其余职级/数值难度无数据,禁
    拍值:调用方补采样数据入 ``cw_opening_hp`` 表后自然解锁。
    """
    hp = opening_hp_prior(list(cfg.enemy_affixes), cfg.selected_difficulty,
                          cfg.enemy_difficulty)
    if hp is None:
        raise OpeningHpUnsampledError(
            f'开局 HP 无实证档(职级={cfg.selected_difficulty!r}, '
            f'数值难度={cfg.enemy_difficulty!r})——U15 定稿口径:按实证档硬表'
            '(cw_opening_hp,当前实证域 = A8/难度108),无实证档报错索样本,'
            '禁外推;请补实机开局帧采样后扩表')
    return hp


def sample_opening_shape(rng: random.Random) -> tuple[int, ...]:
    """开局手牌费用形状采样(U28 双形状 2:1;``M01/opening_hand`` 流)。"""
    shapes = [s for s, _ in OPENING_HAND_SHAPES]
    weights = [w for _, w in OPENING_HAND_SHAPES]
    return tuple(rng.choices(shapes, weights=weights, k=1)[0])


def _uniform_char_of_cost(rng: random.Random, cost: int) -> Character:
    """费用档内均匀抽一名(M01 首版占位口径:M06 固定牌库该费档名集;
    开局 held 为空 → 剩余池 = 固定牌库,等价全池均匀)。"""
    roster = chars_by_cost(cost)
    if not roster or POOL_COPIES_PER_CARD.get(cost, 0) <= 0:
        raise ValueError(f'费用档 {cost} 固定牌库为空(注册表/副本数配置漂移)')
    return roster[rng.randrange(len(roster))]


def opening_bench_chars(rng: random.Random) -> list[BenchSlot]:
    """开局手牌 → 备战席件表(U28:4 张全 1★;卡名按 M01 占位口径均匀抽)。

    返回 1 基槽位已定位的件表(P1 容器原生 BenchSlot,席恒 9 槽,pad
    语义由容器视图承载)。"""
    shape = sample_opening_shape(rng)
    chars: list[BenchSlot] = []
    for cost in shape:
        ch = _uniform_char_of_cost(rng, cost)
        chars.append(BenchSlot(kind='unit', unit=Unit(
            char_id=ch.name, star=1)))
    if len(chars) != OPENING_HAND_SIZE:
        raise ValueError(f'开局手牌张数 {len(chars)} ≠ U28 定案 '
                         f'{OPENING_HAND_SIZE}')
    return chars


def apply_opening(gs: GameState, cfg: RunConfig,
                  rng: random.Random) -> None:
    """开局态写入容器(obs 渠道;引擎在 reset 时调用一次)。

    写入集 = M01 开局状态域:职级/数值难度/词缀/对局类型(局级输入
    申报)+ HP 查表 + 金 3 / 等级 3 / deploy_cap 3 / xp 清零 / streak 0
    + 开局手牌(M06 派生池首个写端)。不写节点键(节点序列由引擎按
    M03 相位推进写入)。
    """
    sig = obs_sig(group_id='sim:engine:opening')
    hp = opening_hp_or_raise(cfg)
    chars = opening_bench_chars(rng)
    slots: list[BenchSlot | None] = [None] * BENCH_CAPACITY
    for slot in chars:
        bench_place(slots, slot)

    def _obs(field, value, tag: str) -> None:
        gs.observe(field, value, evidence=sim_evidence(tag), sig=sig)

    _obs(gs.selected_difficulty, cfg.selected_difficulty, 'opening')
    if cfg.enemy_difficulty is not None:
        _obs(gs.enemy_difficulty, cfg.enemy_difficulty, 'opening')
    _obs(gs.enemy_affixes, list(cfg.enemy_affixes), 'opening')
    _obs(gs.game_mode, cfg.game_mode, 'opening')
    _obs(gs.hp, hp, 'opening')
    _obs(gs.gold, OPENING_GOLD, 'opening')
    _obs(gs.level, OPENING_LEVEL, 'opening')
    _obs(gs.deploy_cap, OPENING_DEPLOY_CAP, 'opening')
    _obs(gs.xp, (0, XP_TO_NEXT_LEVEL.get(OPENING_LEVEL, 4)), 'opening')
    _obs(gs.streak, 0, 'opening')
    _obs(gs.bench, bench_view_of_working(slots, BENCH_CAPACITY), 'opening')
