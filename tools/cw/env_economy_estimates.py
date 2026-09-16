"""投资环境经济估算参数·数据批(2026-09-12 invest-env 迭代 3.3;design.md §2.2.4)。

从对局档案遥测(telemetry/matches 按局档案)统计 B/C 类估值参数,产出可直接
落入 ``kernel/cw_env_economy.ENV_ECONOMY_ESTIMATES`` 的注册表块与口径申报。
**参数值只在代码注册表**(值只在代码,data doc 只记「凭什么信」);本脚本是
重采入口:版本更新/策略行为漂移后重跑 → 对照旧值 → 手工更新注册表
(注册表是手维护常量,本脚本不回写源码,防自动改行为面)。

统计口径(与注册表 landed 值同批,细则 = changes/2026-09-12-invest-env/
details/data-batch-estimates.md):
- 样本:真实局档案(文件名不含 fake;``endgame.result ∈ {win, loss}`` 的
  完成局参与比例/分布统计——弃局(collapse/停机)截断了局 horizon,计入会
  系统性低估整局行为量;败局是完整 horizon(死亡即终点)不剔除。
- 位面到达:P(到达位面 k) = 完成局中 ``endgame.plane_reached ≥ k`` 占比;
  区间 = Wilson 95% 比例区间(小样本比例的标准选择,下界不塌 0/1)。
- 刷新计数:逐局 ``rounds[].actions`` 中 ``RefreshShop`` 动作计数;
  **付费口径 = action.cost > 0**(长线利好「花费金币进行30次刷新」= 付费
  阈值,GameState §3.3.7 paid_refresh_count 载体);**总口径 = 全部
  RefreshShop**(二手市场「商店刷新20次后」= 总阈值,§3.3.8
  total_refresh_count 载体)。cost 为 None 的旧 schema 行按未知剔除该动作。
  已知风险:免费刷新若以陈旧 cost(>0)落账会并入付费计数——当前语料
  无 cost=0 行(高效决策持卡局 1 局、零免费刷记录),分型风险暂无实证。
- 条件期望 E[(N−threshold)+ | N≥threshold]:条件子样本均值 + percentile
  bootstrap 95% 区间(固定种子可复现);零样本 → 参数不落(注册表缺位 =
  fail-closed,禁拍值)。
- 扑满化增益(C 类 每奖励节点期望增益):**零有效估计**——扑满局在册
  (8 局:经济过热 ×7 + 经济严重过热 ×1)但遥测无扑满战利品独立字段,
  奖励轮金差分混入备战净支出(买/卖/刷/升级),无法把增益从收支里分离;
  注册表不落该参数 → C 类通道 fail-closed(裸分维持)。
  采集通路现状(T-143 起):①识别面已通——sim 注入受控批入口
  ``sr_od.application.currency_war.sim.cw_sim_piggy``(变体 normal/super
  同 seed 对照)产出扑满帧样本面;实机侧 piggy_reward 遥测字段
  (telemetry schema)写点已修复(mandate_v1 两栈,判据单一源
  kernel/cw_reward_node)。②真值面仍缺(本参数落参的必要源)——档案
  无扑满战利品独立字段,需实机门开后按扑满局战利品流观察定采集点另批
  落地(现有 8 扑满局档案无新增信息)。
  **落参就绪判据**(三件同时满足,届时重跑本脚本核对后手工落表):
  ① 档案面:每变体可用「扑满奖励节点」样本 ≥ 20 轮(变体分键;经济
  严重过热自然到局频率 ≈0.7%,按需加速到局),且增益分解口径成文
  (战利品金对应字段、与基础/息/连胜的分离规则、失败轮(打不过=零奖励)
  处置);② 统计面:增益均值 bootstrap 95% CI 下端 > 0(fail-closed 门
  方向闭合,与注册表既有门同语义);③ 对拍面:sim 注入批识别面分布与
  实机 piggy_reward 字段方向一致(变体分键无结构性矛盾)。

用法:
  uv run python tools/cw/env_economy_estimates.py [--matches-dir DIR] [--ci 95]
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

#: 缺省档案目录(生产布局 = kernel/cw_observe MATCHES_ROOT 同域;脚本独立
#: 内联路径,保持判别工具不依赖被审代码的导入链)
DEFAULT_MATCHES_DIR = Path('.debug/currency_war/telemetry/matches')

#: bootstrap 重采样数与随机种子(可复现)
_BOOTSTRAP_N = 2000
_BOOTSTRAP_SEED = 20260912

_Z: float = 1.959964   # 95% 双侧正态分位(显式常量,不引 scipy)


def wilson_interval(hits: int, n: int, z: float = _Z) -> tuple[float, float]:
    """Wilson 比例区间(n=0 → [0,0],调用方按零样本处置)。"""
    if n == 0:
        return (0.0, 0.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_mean_ci(xs: list[float], z: float = _Z,
                      n_boot: int = _BOOTSTRAP_N,
                      seed: int = _BOOTSTRAP_SEED) -> tuple[float, float] | None:
    """条件子样本均值的 percentile bootstrap 区间(零样本 → None)。"""
    if not xs:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(xs, k=len(xs))) / len(xs)
                   for _ in range(n_boot))
    # 正态分位数对应的百分位切点(与 Wilson 同 95% 置信水平)
    lo_q = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    hi_q = 1.0 - lo_q
    return (means[int(lo_q * (n_boot - 1))], means[int(hi_q * (n_boot - 1))])


def _is_real_archive(p: Path) -> bool:
    return p.name.startswith('match_g_') and 'fake' not in p.name


def collect(matches_dir: Path) -> dict:
    """全档案扫描 → 原始样本集(完成局过滤后的位面到达/刷新计数序列)。"""
    files = sorted(p for p in matches_dir.glob('match_g_*.json')
                   if _is_real_archive(p))
    n_all = 0
    plane_reached: list[int] = []       # 完成局
    paid_list: list[int] = []           # 完成局
    total_list: list[int] = []          # 完成局
    env_counter: dict[str, int] = {}
    slot_modes: dict[tuple[int, int], dict[str, int]] = {}
    cost_values: dict[int, int] = {}
    difficulties: dict[str, int] = {}
    for f in files:
        j = json.loads(f.read_text(encoding='utf-8'))
        n_all += 1
        eg = j.get('endgame') or {}
        op = j.get('opening') or {}
        diff = str(op.get('difficulty') or '未知')
        difficulties[diff] = difficulties.get(diff, 0) + 1
        for e in (op.get('chosen_env') or []):
            name = e.get('name') if isinstance(e, dict) else str(e)
            env_counter[name] = env_counter.get(name, 0) + 1
        done = eg.get('result') in ('win', 'loss')
        paid = total = 0
        for r in j.get('rounds') or []:
            nt = r.get('node_type')
            if nt:
                key = (int(r.get('plane') or 0), int(r.get('round') or 0))
                slot_modes.setdefault(key, {})
                slot_modes[key][nt] = slot_modes[key].get(nt, 0) + 1
            for a in r.get('actions') or []:
                if a.get('__type__') != 'RefreshShop':
                    continue
                c = a.get('cost')
                if c is None:
                    continue   # 旧 schema 无金额:该动作不计入任何口径
                cost_values[int(c)] = cost_values.get(int(c), 0) + 1
                total += 1
                if c > 0:
                    paid += 1
        if done and eg.get('plane_reached') is not None:
            plane_reached.append(int(eg['plane_reached']))
            paid_list.append(paid)
            total_list.append(total)
    return {
        'n_all': n_all, 'n_done': len(plane_reached),
        'plane_reached': plane_reached, 'paid_list': paid_list,
        'total_list': total_list, 'env_counter': env_counter,
        'slot_modes': slot_modes, 'cost_values': cost_values,
        'difficulties': difficulties,
    }


def fmt_est(name: str, hits: int | float, n: int,
            ci: tuple[float, float]) -> str:
    """注册表条目草稿行(值/CI 保留 4 位;source/cutoff 由调用方批注)。"""
    v = hits / n if n else 0.0
    return (f"    {name!r}: EconomyEstimate(value={v:.4f}, "
            f"ci=({ci[0]:.4f}, {ci[1]:.4f}), source=..., cutoff=...),"
            f"  # hits={hits} n={n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--matches-dir', type=Path, default=DEFAULT_MATCHES_DIR)
    args = ap.parse_args()
    d = collect(args.matches_dir)
    n_done = d['n_done']
    print(f'=== 样本 ===\n档案 {d["n_all"]} 局;完成局 {n_done};'
          f'难度分布 {d["difficulties"]}')
    print(f'选择环境计数(含弃局): {d["env_counter"]}')
    print(f'RefreshShop cost 分布(全部局): '
          f'{dict(sorted(d["cost_values"].items()))}')

    print('\n=== 位面到达(完成局) ===')
    for k in (2, 3):
        hits = sum(1 for p in d['plane_reached'] if p >= k)
        ci = wilson_interval(hits, n_done)
        print(fmt_est(f'plane_arrival_p{k}', hits, n_done, ci))

    print('\n=== 刷新阈值概率(完成局;付费=cost>0 / 总=全部 RefreshShop) ===')
    for scope, xs in (('total', d['total_list']), ('paid', d['paid_list'])):
        for th in (20, 30):
            hits = sum(1 for x in xs if x >= th)
            ci = wilson_interval(hits, len(xs))
            print(fmt_est(f'refresh_{scope}_ge{th}_p', hits, len(xs), ci))

    print('\n=== 条件后继期望 E[(N-th)+ | N>=th](完成局) ===')
    for scope, xs in (('total', d['total_list']), ('paid', d['paid_list'])):
        for th in (20, 30):
            over = [float(x - th) for x in xs if x >= th]
            ci = bootstrap_mean_ci(over)
            if ci is None:
                print(f'    refresh_{scope}_after{th}_e: 零样本 → 不落注册表')
            else:
                mean = sum(over) / len(over)
                print(f'    refresh_{scope}_after{th}_e: value={mean:.4f} '
                      f'ci=({ci[0]:.4f}, {ci[1]:.4f})  # n={len(over)}')

    print('\n=== 节点槽位众数表(全部局;奖励槽位结构参考) ===')
    for key in sorted(d['slot_modes']):
        counts = d['slot_modes'][key]
        mode, n_mode = max(counts.items(), key=lambda kv: kv[1])
        print(f'  p{key[0]}r{key[1]}: {mode} (n={n_mode}/{sum(counts.values())})')

    print('\n=== 扑满化增益(C 类) ===')
    piggy = {k: v for k, v in d['env_counter'].items() if '过热' in str(k)}
    print(f'扑满环境局数: {piggy};零有效估计 → 注册表不落,通道 fail-closed')


if __name__ == '__main__':
    main()
