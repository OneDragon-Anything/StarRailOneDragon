# R41 两量化件预注册批脚本(2026-09;入库可复跑,数字全实测)
#
import sys

# Windows 控制台默认 GBK,输出含 ⇒/λ 等字符会 UnicodeEncodeError——强制 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
#
# 任务背景:R41-1 把「λ_U 序 vs 点估计全序的触发集同集性」升格为前提验证位
# (v3.3 表先验算+预注册进判前锁,重合度<1 即红);R41-3 把 P3 回退先验下修值
# 定谳为 P3 长度语料统计量(【拟·语料统计】槽位带出处)。本脚本一次性算两件:
#
# 任务1(R41-1 同集先验算):直读 v3.3 主表产物 p51_v33_run.txt——Part 8 C 集合
#   (|C|=21,各格 n/点估计[单调估计]/λ_U[CI 上端])与 Part 3M 主表各格 bootstrap CI,
#   按 R32-中④ 排序键(点估计主键降序;λ_U=1.000 饱和截断格按 CI 下端次键;n 第三键)
#   与 λ_U 序(λ_U 主键降序)各取 top-8,算两触发集重合度=|∩|/8。
#   CI 下端次键存在两读(主表 bootstrap 下端 vs Part 8 薄格强制 Wilson 下端),
#   两读各算一遍——结论对次键读法稳健性一并申报。
#
# 任务2(R41-3 P3 长度分布统计):设计前提核验+语料直读。生产语义的 plane_lengths_seen
#   =各位面首帧实读槽序表长度(prep_director.store_plane_table);对局档案未落该字段
#   (全仓 JSON grep 零命中),档案侧同构量=逐位面**去重轮数**(outcomes 逐轮档按
#   (plane, round_num) 去重——原始行含同轮多重结算,不去重会多数)。终局位面在
#   死亡局系右删失(只见到死亡前轮数=长度下界,非揭示长度);完整观测=走完该位面
#   (局进入下一位面)。脚本按此分类出:P1/P2 完整观测复核 + P3 槽观测形态判定。
#
# 运行(Windows PowerShell):
#   $env:PYTHONIOENCODING='utf-8'
#   uv run python tools/cw/proofs/p51/p51_r41_prereg.py

import json
import random
import re
from collections import Counter
from pathlib import Path
from statistics import median

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
# 数据源优先级:同目录入库副本(保证「入库可复跑」成立,p15 corpus 同先例)→ .debug 迭代工作面
RUN_TXT = (BASE / 'p51_v33_run.txt') if (BASE / 'p51_v33_run.txt').exists() else (
    REPO / '.debug/temp/currency_war/redesign/p51_v33_run.txt')
MATCH_DIR = REPO / '.debug/temp/currency_war/replay/matches'
N_BOOT = 1000
SEED = 20260902  # 判前锁口径:预注册数字须可复算,固定种子

CELL_RE = re.compile(
    r'#(\d+) (D[01])×(hp[<=\w>-]+)×(P[12][+]?)×(\w+): n=(\d+) '
    r'单调=([\d.]+) λ_U\(CI上端\)=([\d.]+)'
)
MAIN_RE = re.compile(
    r'^\s*(D[01])\((\d+<\d+)\) (hp[<=\w>-]+) (P[12][+]?) (\w+):'
    r'(?:<空格 n=0>| n=(\d+) 原始=[\d.]+ 单调=[\d.]+ \[([\d.]+),([\d.]+)\])'
)
WILSON_RE = re.compile(r'CI 下限强制 Wilson=([\d.]+)')


def load_cells() -> list[dict]:
    """直读 v3.3 产物:C 集合 21 格 + 主表 CI 下端(bootstrap) + 薄格 Wilson 强制下端。"""
    text = RUN_TXT.read_text(encoding='utf-8')
    # 主表 CI(bounds):键=(难度带,血带,位面,节点) → (λ_L_bootstrap, λ_U)
    ci_map: dict[tuple[str, str, str, str], tuple[float, float]] = {}
    wilson_map: dict[tuple[str, str, str, str], float] = {}
    in_part8 = False
    for line in text.splitlines():
        m = MAIN_RE.match(line)
        if m and m.group(6):
            ci_map[(m.group(1), m.group(3), m.group(4), m.group(5))] = (
                float(m.group(7)), float(m.group(8)))
        wm = WILSON_RE.search(line)
        if wm and line.startswith('  ') and ':' in line and '→ 可消费' in line:
            # Part 8 消费标签行:「D0 hp<=15 P2+ encounter: … → 可消费(薄 n=9,CI 下限强制 Wilson=…)」
            head = line.split(':', 1)[0].split()
            wilson_map[(head[0], head[1], head[2], head[3])] = float(wm.group(1))
        if line.startswith('C 集合'):
            in_part8 = True
        elif in_part8 and line.startswith('top-2'):
            in_part8 = False
        if in_part8:
            cm = CELL_RE.search(line)
            if cm:
                key = (cm.group(2), cm.group(3), cm.group(4), cm.group(5))
                cells = {
                    'id': int(cm.group(1)), 'key': key, 'n': int(cm.group(6)),
                    'pe': float(cm.group(7)), 'lam_u': float(cm.group(8)),
                }
                CACHED.append(cells)
    if len(CACHED) != 21:
        raise SystemExit(f'C 集合格数={len(CACHED)} != 21,产物形态异常')
    for c in CACHED:
        if c['key'] not in ci_map:
            raise SystemExit(f"格 {c['key']} 不在主表 CI 映射内")
        c['lam_l_boot'] = ci_map[c['key']][0]
        c['lam_l_wilson'] = wilson_map.get(c['key'])
    return CACHED


CACHED: list[dict] = []


def sort_point_estimate(cells: list[dict], lower: str) -> list[dict]:
    """R32-中④ 排序键:点估计主键降序;λ_U=1.000 饱和截断格按 CI 下端次键;n 第三键。
    lower='boot'(主表 bootstrap 下端)/'wilson'(薄格强制 Wilson 下端,缺格回退 bootstrap)。
    """
    def key(c: dict) -> tuple:
        sub = c['lam_l_wilson'] if lower == 'wilson' and c['lam_l_wilson'] is not None else c['lam_l_boot']
        sat_break = sub if c['lam_u'] >= 1.0 else 0.0  # 仅饱和截断格启用次键
        return (-c['pe'], -sat_break, -c['n'], c['id'])
    return sorted(cells, key=key)


def top8_lam_u(cells: list[dict]) -> list[dict]:
    """λ_U 序对照读法:λ_U 主键降序,并列按 CI 下端(bootstrap)次键、n 第三键打破。"""
    return sorted(cells, key=lambda c: (-c['lam_u'], -c['lam_l_boot'], -c['n'], c['id']))[:8]


def task1() -> None:
    print('== 任务1(R41-1). 同集前提先验算:v3.3 主表 点估计全序 vs λ_U 序 top-8 重合度 ==')
    cells = load_cells()
    lam8 = top8_lam_u(cells)
    lam_ids = [c['id'] for c in lam8]
    for lower in ('boot', 'wilson'):
        pt8 = sort_point_estimate(cells, lower)[:8]
        pt_ids = [c['id'] for c in pt8]
        inter = sorted(set(pt_ids) & set(lam_ids))
        overlap = len(inter) / 8
        verdict = '绿(同集前提成立)' if overlap == 1.0 else '红(同集前提失效,<1)'
        print(f'\n[次键读法={lower}] 点估计全序 top-8 = {pt_ids}')
        print(f'[次键读法={lower}]   λ_U 序 top-8 = {lam_ids}')
        print(f'[次键读法={lower}]   交集 = {inter} → 重合度 = {len(inter)}/8 = {overlap:.3f} ⇒ {verdict}')
    # 分歧格解剖(两读法共通的点估计序前 8 与 λ_U 序前 8 的差)
    ptA = [c['id'] for c in sort_point_estimate(cells, 'boot')[:8]]
    ptB = [c['id'] for c in sort_point_estimate(cells, 'wilson')[:8]]
    only_pt = set(ptA) | set(ptB)
    print(f'\n分歧解剖:λ_U 序独有格 = {sorted(set(lam_ids) - only_pt)};'
          f'点估计序独有格(读法依赖) = {sorted((set(ptA) | set(ptB)) - set(lam_ids))}')
    print('判定口径(预注册):重合度<1 即红 ⇒ 当前表两序已分歧,#T 与触发集按点估计全序'
          '重算(设计 §2.0-3 规格① R41-1 段定谳的生产线度量);λ_U 序口径语料参考值'
          '(6.2%/25.7%/11.3%)保持参考值地位(R37-1)')


def plane_lengths_from_match(j: dict) -> list[int]:
    """档案同构量:逐位面去重轮数(outcomes 同轮多重结算去重;终局位面右删失=下界)。"""
    sl = j.get('slices') or {}
    if isinstance(sl, list):
        sl = sl[0] if sl else {}
    rounds_by_plane: dict[int, set[int]] = {}
    for o in sl.get('outcomes.jsonl') or []:
        p = o.get('plane')
        if p is not None:
            rounds_by_plane.setdefault(int(p), set()).add(o.get('round_num'))
    return [len(rounds_by_plane[p]) for p in sorted(rounds_by_plane)]


def task2() -> None:
    print('\n== 任务2(R41-3). P3 长度语料统计:档案直读 + 观测形态判定 ==')
    per_match: list[tuple[str, str, list[int]]] = []
    for fp in sorted(MATCH_DIR.glob('match_g_*.json')):
        j = json.loads(fp.read_text(encoding='utf-8'))
        eg = j.get('endgame') or {}
        lens = plane_lengths_from_match(j)
        for v in lens:
            if not 1 <= v <= 9:  # 同注册表守卫同款:合法域 [1,9] 夹取
                raise SystemExit(f'{fp.name}: 位面长度 {v} 越界 [1,9]')
        per_match.append((fp.name, str(eg.get('result')), lens))
    n = len(per_match)
    results = Counter(r for _, r, _ in per_match)
    # 每槽:i 槽完整观测 = 局进入第 i+1 位面(走完第 i 位面);终局位面 = 右删失下界
    print(f'档案局数={n};result 分布={dict(results)}(无通关局)')
    p3_complete: list[int] = []   # P3 完整观测(进入过 P4 的局——语料结构上不存在,守卫列出)
    p3_censored: list[int] = []   # P3 右删失下界(死于 P3)
    for _, _res, lens in per_match:
        if len(lens) >= 3:
            (p3_complete if len(lens) >= 4 else p3_censored).append(lens[2])
    dist_c = Counter(p3_censored)
    print(f'P3 槽:完整观测 m_complete={len(p3_complete)};右删失下界样本 m_censored={len(p3_censored)}')
    print('P3 右删失下界分布(去重轮数→局数):'
          + '; '.join(f'{v}轮:{dist_c[v]}局' for v in sorted(dist_c)))
    # P1/P2 复核(P2=7 系 R25-1 语料定谳,同法复核)
    p1_done = [lens[0] for _, _, lens in per_match if len(lens) >= 2]
    p2_done = [lens[1] for _, _, lens in per_match if len(lens) >= 3]
    d1, d2 = Counter(p1_done), Counter(p2_done)
    print(f'复核 P1(完整观测 {len(p1_done)} 局):' + '; '.join(f'{v}轮:{d1[v]}局' for v in sorted(d1)))
    print(f'复核 P2(完整观测 {len(p2_done)} 局):' + '; '.join(f'{v}轮:{d2[v]}局' for v in sorted(d2)))
    rng = random.Random(SEED)
    if p3_complete:
        # (语料出现通关局后自然启用)完整观测样本上的众数/中位 + bootstrap CI
        mode_n = Counter(p3_complete)
        best = max(mode_n.values())
        modes = sorted(v for v, c in mode_n.items() if c == best)
        med = median(p3_complete)
        boots_mode: list[int] = []
        boots_med: list[float] = []
        for _ in range(N_BOOT):
            r = [p3_complete[rng.randrange(len(p3_complete))] for _ in range(len(p3_complete))]
            bcnt = Counter(r)
            bbest = max(bcnt.values())
            boots_mode.append(min(v for v, c in bcnt.items() if c == bbest))
            boots_med.append(median(r))
        boots_mode.sort()
        boots_med.sort()
        lo_m = boots_mode[round(0.025 * (N_BOOT - 1))]
        hi_m = boots_mode[round(0.975 * (N_BOOT - 1))]
        lo_d = boots_med[round(0.025 * (N_BOOT - 1))]
        hi_d = boots_med[round(0.975 * (N_BOOT - 1))]
        print(f'P3 完整观测:众数={modes}(bootstrap 95%CI=[{lo_m},{hi_m}]);'
              f'中位={med}(CI=[{lo_d},{hi_d}]);推荐值=众数最小={min(modes)}')
    else:
        print('判定:【拟·语料统计】槽位**不可填值**——P3 完整观测为零(全部 74 局 loss/stopped/'
              'abandoned,无一走完 P3;右删失下界非揭示长度,禁作统计量)。')
        print('处置:P3 回退先验保持 9(脏表上界回退原文语义);复算触发条件=语料出现通关局'
              '(完整 P3 观测)或对局档案落 plane_lengths_seen 字段;设计件 R41-3 段'
              '「已揭晓 P3 实测长度分布」前提按实测打标修正(档案无字段,前提不成立)。')
        print(f'辅助复核结论:P1=9({d1.get(9, 0)}/{len(p1_done)} 完整局);'
              f'P2=7({d2.get(7, 0)}/{len(p2_done)} 完整局,R25-1 定谳复核成立)')


def main() -> None:
    task1()
    task2()


if __name__ == '__main__':
    main()
