"""货币战争 sim 扑满环境注入批(受控对照采集面;T-143)。

背景:ENV_ECONOMY C 类环境(经济过热/经济严重过热)的估值参数
``reward_node_bonus_{variant}``(kernel/cw_env_economy.ENV_ECONOMY_ESTIMATES)
零样本不落在册(禁拍值,T-129 数据批)。本模块是识别面样本的批入口:
同 seed 同池多臂注入 ``SimInvestProfile``(W162/ADR-0364 注入口),产出
``piggy_reward`` 扑满帧样本面(写点 = mandate_v1 两栈刷新,判据单一源
kernel/cw_reward_node.is_piggy_reward_frame;识别面修复 = T-143,shop 栈
写点曾因旧 ``CwSimFrame.node_type`` 属性失联)。

**辖域边界(读前必知)**:sim 不建模扑满战利品金流——注入臂的奖励轮
收入 = 普通奖励节点注册表值,两臂收入面结构性零差。本批样本因此只承载
**识别面**(扑满帧分布/逐(位面,轮)槽位对照/基线零污染闸),增益真值
(每奖励节点期望增益)只能来自实机对局档案采集;落参数据就绪判据 =
tools/cw/env_economy_estimates.py 重采入口头注(P8 重推前置清单 #1 的
sim 侧由本模块兑现,P8 §4 兑现判据 = 注入局 ``piggy_reward: true`` 样本 >0)。

**种子段纪律**(sim-testing「种子段分配纪律」):各臂共用同一段
``[seed_base, seed_base+n)``,同 seed 跨臂配对 = 受控对照;并行批派发时
seed_base 由编排者统一下发,批 manifest.json 的 seeds 键 = 占用段对账锚。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_reward_node import PIGGY_ENV_NAMES
from sr_od.application.currency_war.sim.cw_sim_invest import SimInvestProfile
from sr_od.application.currency_war.sim.engine_p1 import SimResult, simulate_p1

#: 扑满变体 → 注入环境名(空串 = 基线臂,本局无环境)。
#: 变体键与 kernel/cw_env_economy 的估算参数键族 reward_node_bonus_{variant}
#: 对齐(normal/super);对应关系由测试锁钉住(防单侧改名漂移)。
#: 环境名单一致性 = 构建期校验(_validate_variants,import 即炸):
#: 注入臂环境必须 ∈ PIGGY_ENV_NAMES(注册表效果文本「奖励节点替换」
#: 派生单一源)——名单漂移(版本改词)时这里先炸,禁注入哑臂。
PIGGY_VARIANT_ENVS: dict[str, str] = {
    'baseline': '',
    'normal': '经济过热',
    'super': '经济严重过热',
}


def _validate_variants() -> None:
    """变体表构建校验(import 即炸):非基线臂环境必须在扑满名单内。"""
    for _variant, _env in PIGGY_VARIANT_ENVS.items():
        if not _env:
            continue
        if _env not in PIGGY_ENV_NAMES:
            raise ValueError(
                f'扑满注入臂环境不在 PIGGY_ENV_NAMES 名单(注册表效果文本'
                f'漂移?注入将得到哑臂):{_variant!r} -> {_env!r}')


_validate_variants()


def piggy_profile(variant: str) -> SimInvestProfile:
    """变体 → 注入剧本(环境直注入;策略选卡日程不注入,缺省空 = 干净对照)。

    选卡日程刻意留空:本批对照的唯一差异面是环境(策略选卡日程引入的
    持卡差异会混入行为对照面);需要日程的批显式自建 SimInvestProfile。
    """
    try:
        env = PIGGY_VARIANT_ENVS[variant]
    except KeyError:
        raise ValueError(
            f'未知扑满变体: {variant!r}(合法: {sorted(PIGGY_VARIANT_ENVS)})'
        ) from None
    return SimInvestProfile(active_env=env)


@dataclass(frozen=True)
class PiggyArmStats:
    """单臂扑满帧统计(账本行级聚合;行键语义见 engine 账本 piggy_reward)。

    - piggy_frames_by_slot 键 = (plane, round_num)(位面内轮次,1 基,
      账本行坐标);值 = 该槽位确认帧数。
    - **确认帧口径** = ``piggy_reward=True`` ∧ 账本行 node='reward'——
      扑满标记跨轮有已知的滞留形态(该轮首段无商店决策时引擎轮快照读
      到上一奖励帧的旧值;引擎侧快照机制辖域,非写点语义),按行消费
      一律以奖励节点容器为准,裸 True 行单独计数披露(piggy_leak_rows)。
    - reward_frames_total = ``node='reward'`` 账本行数——扑满帧的天然
      容器(基线臂该值>0 而 piggy_frames_total=0 = 环境未污染的结构证据)。
    """

    variant: str
    env: str
    n_games: int
    games_with_piggy: int
    piggy_frames_total: int
    reward_frames_total: int
    piggy_leak_rows: int
    piggy_frames_by_slot: dict[tuple[int, int], int]

    def as_dict(self) -> dict[str, Any]:
        """JSON 安全投影(by_slot 键元组转 'p{plane}r{round}' 字符串)。"""
        return {
            'variant': self.variant,
            'env': self.env,
            'n_games': self.n_games,
            'games_with_piggy': self.games_with_piggy,
            'piggy_frames_total': self.piggy_frames_total,
            'reward_frames_total': self.reward_frames_total,
            'piggy_leak_rows': self.piggy_leak_rows,
            'piggy_frames_by_slot': {
                f'p{p}r{r}': c for (p, r), c in sorted(
                    self.piggy_frames_by_slot.items())
            },
        }


def aggregate_arm(variant: str, results: list[SimResult]) -> PiggyArmStats:
    """单臂账本行聚合(纯函数;零行为面,输入 = 已跑完的局结果)。"""
    env = PIGGY_VARIANT_ENVS[variant]
    by_slot: dict[tuple[int, int], int] = {}
    piggy_rows = 0
    leak_rows = 0
    reward_rows = 0
    games_with_piggy = 0
    for res in results:
        game_piggy = 0
        for row in res.ledger:
            is_reward = (row.get('sim') or {}).get('node') == 'reward'
            if is_reward:
                reward_rows += 1
            if row.get('piggy_reward'):
                if is_reward:
                    piggy_rows += 1
                    game_piggy += 1
                    key = (int(row.get('plane') or 1),
                           int(row.get('round_num') or 0))
                    by_slot[key] = by_slot.get(key, 0) + 1
                else:
                    leak_rows += 1
        if game_piggy:
            games_with_piggy += 1
    return PiggyArmStats(
        variant=variant, env=env, n_games=len(results),
        games_with_piggy=games_with_piggy, piggy_frames_total=piggy_rows,
        reward_frames_total=reward_rows, piggy_leak_rows=leak_rows,
        piggy_frames_by_slot=by_slot)


def run_piggy_batch(
        variants: tuple[str, ...] = ('baseline', 'normal', 'super'),
        n: int = 20, *,
        seed_base: int = 42000,
        pool: str | Path = 'snapshot',
        planes: int = 1,
        use_refresh: bool = True,
        anchor_reason: str = '',
) -> dict[str, Any]:
    """扑满注入受控批:各臂同 seed 段跑 n 局,聚合识别面统计并落账本。

    - 各臂 = ``PIGGY_VARIANT_ENVS`` 中点名的变体(缺省含 baseline 零环境
      臂 = 基线零污染闸的结构证据);臂内逐局 ``simulate_p1(seed_base+i)``,
      跨臂同 seed 配对(受控对照的唯一差异面 = 注入环境)。
    - 账本落盘 = ``write_batch_ledger``(decisions/outcomes/shop_snapshots
      + manifest,批目录名 ``sim_piggy_<variant>_…``;滚动清理窗口语义与
      普通批一致)。``anchor_reason`` 非空时给各臂批目录打锚定标记
      (免滚动清理,复现链锚点;证据批建议锚定)。
    - 池指纹跨臂必须一致(simulate_core_ab 同款公平闸,不一致直接炸)。
    - 返回 = 批报告 dict(池指纹/占用种子段/逐臂统计;调用方落盘或直读)。
    """
    import logging
    import time

    from sr_od.application.currency_war.sim.runner import (
        SIM_RUNS_DIR,
        anchor_batch,
        write_batch_ledger,
    )

    unknown = [v for v in variants if v not in PIGGY_VARIANT_ENVS]
    if unknown:
        raise ValueError(f'未知扑满变体: {unknown}(合法: '
                         f'{sorted(PIGGY_VARIANT_ENVS)})')
    logging.disable(logging.CRITICAL)   # 批量跑静音(决策日志逐段刷屏)
    arms: dict[str, list[SimResult]] = {}
    try:
        for variant in variants:
            arms[variant] = [
                simulate_p1(seed_base + i,
                            pool=pool, planes=planes,
                            use_refresh=use_refresh,
                            invest=piggy_profile(variant))
                for i in range(n)
            ]
    finally:
        logging.disable(logging.NOTSET)

    fps = {r.pool_fingerprint for rows in arms.values() for r in rows}
    if len(fps) != 1:
        raise RuntimeError(f'跨臂池指纹不一致(对拍不公平): {sorted(fps)}')
    pool_fp = next(iter(fps))

    stamp = time.strftime('%Y%m%d_%H%M%S')
    arm_stats: dict[str, Any] = {}
    batch_dirs: dict[str, str] = {}
    for variant, rows in arms.items():
        out_dir = SIM_RUNS_DIR / (
            f'sim_piggy_{variant}_{stamp}_n{n}_s{seed_base}_{pool_fp[:8]}')
        write_batch_ledger(rows, out_dir, pool_fp=pool_fp)
        if anchor_reason:
            anchor_batch(out_dir, anchor_reason)
        batch_dirs[variant] = out_dir.name
        arm_stats[variant] = aggregate_arm(variant, rows).as_dict()

    report: dict[str, Any] = {
        'batch_stamp': stamp,
        'seed_segment': [seed_base, seed_base + n],
        'n': n,
        'planes': planes,
        'pool_fingerprint': pool_fp,
        'batch_dirs': batch_dirs,
        'arms': arm_stats,
    }
    baseline = arm_stats.get('baseline')
    if baseline is not None:
        report['baseline_zero_piggy'] = baseline['piggy_frames_total'] == 0
    return report
