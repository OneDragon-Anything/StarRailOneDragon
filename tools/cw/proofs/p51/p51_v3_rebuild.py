# P51 v3 λ_death 表重建脚本(v3 候选,2026-09-09;入库可复跑)
#
# 背景:旧表(桶×节点,sim AB 账本标定)被基座攻击报告(IMPL_LAMBDA_FOUNDATION_ATTACK §2/§4)
# 证伪桶可交换性(桶内 hp 亚组危险率差 0.000→0.904)、0.1 阈值路由翻转面 19-55%。
# 本脚本按用户新方向在【实机语料】上重估:钥匙=难度带×血量带×板面粗档×节点类型,
# 单调性约束(血↓危↑/难度↑危↑/板面↑危↓),难度=局内读取真值优先、公式计算值兜底+对账。
#
# 数据:.debug/temp/currency_war/replay/matches/match_g_*.json(实机 66-68 局,slices 内
# decisions.jsonl/outcomes.jsonl 逐轮档)。只读语料,无任何 sim 输入(公理:禁 sim 账本)。
#
# v3.2(R30 键单一源对齐,2026-09):**主表输出=PL 键(位面键:难度带×血带×位面[P1/P2+]×
# 节点)**——原板面键(难度×血×板面粗档×节点)降为对照存档(板面档标签 B0/B1/B2 保留,
# 防与位面键撞名;候选期「B1」自此改称「PL 键(位面键)」);Part 8 消费标签/C 集合/
# top-2 格/语料访问率锚全部按 PL 键重做。位面维单调方向=位面↑危↑(候选评估期曾借用
# 板面负方向池化,主表按正方向重拟)。
#
# v3.3(F1 血带轴方向修复,2026-09,依据=IMPL_LAMBDA_ATTACK_R3):血带维 dims 自 v3.0 起
# 误写 up=True(hp 升序下标 ⇒ 约束为「血↑危↑」),与全链文档语义(P51 证明件/脚本表头/
# Part 8 支配偏序的「血↓危↑」)相反——D0×P1×noncombat 三格拟合=列合并均值 0.316 系方向
# 反转的算术实锤。v3.3 起血带维改 up=False(HP 序=['hp<=15','hp15-40','hp>40'] 升序下,
# up=False ⇒ λ(hp≤15)≥λ(hp15-40)≥λ(hp>40)=血↓危↑),全部键形态(板面键存档/PL 键主表/
# Part 9 对比)同步修正;monotone_fit_generic 增拟合后方向断言护栏(防再翻转)。
# 连带:F2(R31-6 #T distinct 口径界+n 次键落脚本)/F3(位面方向违反格受污注+监督计数)/
# F4(空格 P1 经验流量披露);旧「hp≤15 低估/D0×hp>40 抬高」受污标签体系随方向修复作废,
# 改数据驱动的池化偏移注(按新表重判)。
#
# 运行(Windows PowerShell):
#   $env:PYTHONPATH='src'; $env:PYTHONIOENCODING='utf-8'
#   uv run python tools/cw/proofs/p51/p51_v3_rebuild.py
#
# ⚠️ 全部难度公式值标「interim 计算值」:公式缺位面递进/难度修改器/遭遇等级/圣杯特殊项
# (economy §9 自认完整规则未建模),真值对账见 Part 2。

import json
import random
import sys
from itertools import product
from pathlib import Path
from statistics import mean, median

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parents[3] / 'src'))

from sr_od.application.currency_war.kernel.cw_investments import (  # noqa: E402
    INVESTMENT_STRATEGIES,
    normalize_invest_name,
)

MATCH_DIR = BASE.parents[3] / '.debug/temp/currency_war/replay/matches'
N_BOOT = 1000
ALPHA = 0.05
DEATH_HORIZON = 3      # λ3:3 轮累积危险率(与旧表同口径)
ROUTE_THR = 0.1        # 0.1 阈值路由判据(基座攻击 §4.2 口径)

# 难度公式(economy §9,interim):基础 108 + 品质加成(银0/金3/棱彩6,远见豁免)
# + 遭遇等级(遥测无字段,缺位置 0) + 特殊(伟大征服+当前连胜)。缺项见文件头注。
DIFF_BASE = 108
RARITY_BONUS = {'银': 0, '金': 3, '棱彩': 6}


# ---------- 语料装载:每局逐轮表(decisions 末帧 × outcomes)----------
def load_matches() -> list[dict]:
    matches = []
    for fp in sorted(MATCH_DIR.glob('match_g_*.json')):
        j = json.loads(fp.read_text(encoding='utf-8'))
        sl = j.get('slices') or {}  # {slice名: 行列表};取逐轮档
        if isinstance(sl, list):
            sl = sl[0] if sl else {}
        dec_rows = sl.get('decisions.jsonl') or []
        out_rows = sl.get('outcomes.jsonl') or []
        if not dec_rows or not out_rows:
            continue
        # 每 (plane, round) 取最后一帧决策(最接近开战的板面/金/血相)
        dec = {}
        for r in dec_rows:
            st = r.get('state') or {}
            if 'enemy_difficulty' not in st:
                continue  # 终局摘要行等无 state 逐帧字段
            k = (r.get('plane'), r.get('round_num'))
            dec[k] = r
        rounds = []
        for o in out_rows:
            k = (o.get('plane'), o.get('round_num'))
            d = dec.get(k)
            if d is None:
                continue
            st = d['state']
            rounds.append({
                'plane': o['plane'], 'round': o['round_num'],
                'node': o['node_type'],
                'hp_after': o.get('hp_after'),
                'killed': o.get('killed'),
                'gold': st.get('gold'),
                'hp': st.get('hp'),
                'streak': st.get('streak') or 0,
                'star_sum': sum((c.get('star') or 1) for c in (st.get('deployed') or [])),
                'n_deployed': len(st.get('deployed') or []),
                'diff_truth': st.get('enemy_difficulty'),
                'diff_live': st.get('enemy_difficulty_live'),
                'strategies': list(st.get('active_strategies') or []),
            })
        if not rounds:
            continue
        matches.append({
            'game_id': j.get('game_id') or fp.stem,
            'date': fp.stem.split('_')[2],
            'rounds': rounds,
        })
    return matches


# ---------- 难度公式值(interim 计算值)----------
# 繁体/异体 OCR 变体回正(语料 invest_cards/active_strategies 中实测出现的变体;
# 只做字符级映射,不改注册表)
_TRAD_FIX = str.maketrans({'強': '强', '黃': '黄'})


def diff_formula(strategies: list[str], streak: int) -> int:
    v = DIFF_BASE
    for name in strategies:
        nm = normalize_invest_name(name.translate(_TRAD_FIX))
        s = INVESTMENT_STRATEGIES.get(nm)
        if s is None:
            continue  # 未登记名不入账,Part 2 对账段披露计数
        eco = getattr(s, 'economy', None)
        if eco is not None and getattr(eco, 'difficulty_inflation_exempt', False):
            continue  # 远见:不增加敌人难度
        v += RARITY_BONUS.get(s.rarity, 0)
        if eco is not None and getattr(eco, 'difficulty_per_streak', 0):
            v += eco.difficulty_per_streak * streak  # 伟大征服:+当前连胜
    return v


# ---------- 死亡标记:每局首个 hp_after<=0 的轮(跨位面全序列)----------
def mark_deaths(matches: list[dict]) -> None:
    for m in matches:
        rs = m['rounds']
        death_i = None
        for i, r in enumerate(rs):
            if r['hp_after'] is not None and r['hp_after'] <= 0:
                death_i = i
                break
        m['death_i'] = death_i
        for i, r in enumerate(rs):
            r['died'] = death_i is not None
            r['dist_end'] = (death_i - i) if death_i is not None else 10**6


# ---------- 分带 ----------
def hp_band(hp):
    if hp is None:
        return None
    return 'hp<=15' if hp <= 15 else ('hp15-40' if hp <= 40 else 'hp>40')


NODE4 = {'普通战斗': 'battle', '遭遇': 'encounter', 'boss': 'boss'}


def node4(node):
    return NODE4.get(node, 'noncombat')  # 奖励/补给归非战斗第 4 类


def main() -> None:
    matches = load_matches()
    mark_deaths(matches)
    n_dead = sum(1 for m in matches if m['death_i'] is not None)
    print(f'== 语料:{len(matches)} 局(死亡 {n_dead} 局),逐轮行 '
          f'{sum(len(m["rounds"]) for m in matches)} ==')

    # ===== Part 1:难度真值覆盖 + 公式值(interim)对账 =====
    unknown_names = set()
    resid = []
    n_suspect = 0
    for m in matches:
        for r in m['rounds']:
            r['diff_formula'] = diff_formula(r['strategies'], r['streak'])
            for nm in r['strategies']:
                if normalize_invest_name(nm.translate(_TRAD_FIX)) not in INVESTMENT_STRATEGIES:
                    unknown_names.add(nm)
            # 真值可疑筛:A8 账号基线 108,读数 <50(低职级旗牌/断码)或 >200(溢出态,
            # economy §9 实测值域注)不作案内难度真值 → 公式兜底并计数
            if r['diff_truth'] is not None and not (50 <= r['diff_truth'] <= 200):
                n_suspect += 1
                r['diff_truth'] = None
            if r['diff_truth'] is not None:
                resid.append((r['diff_truth'] - r['diff_formula'], r['plane'], node4(r['node']), r))
    if resid:
        n_tot = len(matches) * 0 + sum(len(m['rounds']) for m in matches)
        print(f'\n== Part 1. 难度:真值覆盖(可疑筛后){len(resid)}/{n_tot} 轮 ==')
        ds = [x[0] for x in resid]
        print(f'公式(interim)−真值 残差:n={len(resid)} 均值={mean(ds):+.1f} '
              f'中位={median(ds):+.0f} 值域=[{min(ds):+d},{max(ds):+d}]')
        for pl in (1, 2, 3):
            dpl = [x[0] for x in resid if x[1] == pl]
            if dpl:
                print(f'  位面{pl}: n={len(dpl)} 残差均值={mean(dpl):+.1f} '
                      f'值域=[{min(dpl):+d},{max(dpl):+d}]')
        for nd in ('battle', 'encounter', 'boss', 'noncombat'):
            dn = [x[0] for x in resid if x[2] == nd]
            if dn:
                print(f'  节点{nd}: n={len(dn)} 残差均值={mean(dn):+.1f}')
        # 残差主体成分(位面递进/难度修改器缺项的实证读数)
        from collections import Counter
        print(f'  残差值分布(top):{Counter(int(d) for d in ds).most_common(8)}')
    if unknown_names:
        print(f'  公式未能映射的策略名(不入账):{sorted(unknown_names)}')
    print(f'  可疑真值读数(<50 或 >200,已筛除走公式兜底):{n_suspect} 轮')
    # 难度值域(真值优先,公式兜底)→ 分带
    for m in matches:
        for r in m['rounds']:
            r['diff'] = r['diff_truth'] if r['diff_truth'] is not None else r['diff_formula']
    all_diff = sorted(r['diff'] for m in matches for r in m['rounds'])
    n_fallback = sum(1 for m in matches for r in m['rounds']
                     if r['diff_truth'] is None)
    print(f'难度采用:真值 {len(all_diff) - n_fallback} 轮 / 公式兜底 {n_fallback} 轮;'
          f'值分布分位 p10={all_diff[len(all_diff)//10]} p50={all_diff[len(all_diff)//2]} '
          f'p90={all_diff[9*len(all_diff)//10]} min={all_diff[0]} max={all_diff[-1]}')

    # 难度带:按数据分布定界(~3-4 档看离散度;单账号窄难度带若退化则如实降档)
    uniq = sorted(set(all_diff))
    if uniq[-1] - uniq[0] <= 6:
        bands = [(uniq[0] - 1, uniq[-1] + 1)]
    elif len(uniq) <= 8:
        # 小值集:按自然断点二分/三分
        q = [uniq[0] - 1] + [all_diff[len(all_diff) * k // 3] for k in (1, 2)] + [uniq[-1] + 1]
        # 去重保序
        edges = sorted(set(q))
        bands = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
    else:
        edges = sorted({all_diff[0] - 1,
                        all_diff[len(all_diff) // 3],
                        all_diff[2 * len(all_diff) // 3],
                        all_diff[-1] + 1})
        bands = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
    print(f'难度带定界(数据分布驱动):{bands}')

    def diff_band(v):
        for i, (lo, hi) in enumerate(bands):
            if lo < v <= hi:
                return i
        return 0

    # 板面粗档:deployed 星数和按分布 2-3 档
    stars = sorted(r['star_sum'] for m in matches for r in m['rounds']
                   if r['hp_after'] is not None)
    e = sorted({-1, stars[len(stars) // 3], stars[2 * len(stars) // 3], max(stars) + 1})
    star_edges = [(e[i], e[i + 1]) for i in range(len(e) - 1)]
    print(f'板面粗档定界(deployed 星数和):{star_edges}')

    def board_band(v):
        for i, (lo, hi) in enumerate(star_edges):
            if lo < v <= hi:
                return i
        return 0

    # 组装行级表(带新钥匙)
    rows = []
    for mi, m in enumerate(matches):
        for r in m['rounds']:
            r['match'] = mi
            r['node4'] = node4(r['node'])
            r['dband'] = diff_band(r['diff'])
            r['hband'] = hp_band(r['hp'])
            r['bband'] = board_band(r['star_sum'])
            r['pband'] = 0 if r['plane'] == 1 else 1
            r['y'] = 1 if (r['died'] and r['dist_end'] <= DEATH_HORIZON) else 0
            rows.append(r)
    HB = ['hp<=15', 'hp15-40', 'hp>40']
    ND, NB, NN = len(bands), len(star_edges), 4

    # ===== Part 3A(v3.2 对照存档). 板面键 λ3 表(标签 B0/B1/B2 保留;禁再作主表消费)=====
    print('\n== Part 3A(v3.2 对照存档). 板面键 λ3(视界 3 轮;单调约束:血↓危↑/难度↑危↑/板面↑危↓)==')
    print(f'格子全集:{ND}难度带 × 3血带 × {NB}板面档(B0/B1/B2) × 4节点 = {ND*3*NB*NN} 格')

    def cell_of(r):
        return (r['dband'], HB.index(r['hband']), r['bband'], ['battle', 'encounter', 'boss', 'noncombat'].index(r['node4']))

    cells = {}
    for r in rows:
        cells.setdefault(cell_of(r), []).append(r)

    def raw_rates(cells_):
        return {c: (sum(x['y'] for x in v) / len(v), len(v)) for c, v in cells_.items() if v}

    raw = raw_rates(cells)

    def _assert_monotone_dirs(cur, dims):
        """方向断言护栏(v3.3,F1):拟合完成后逐轴逐列校验单调方向,违反即抛错终止。

        血带维(hp 升序下标)约束=非增(血↓危↑);其余约束轴按 dims 声明方向核验。
        缘由:血带维曾以 up=True(hp 升序 ⇒「血↑危↑」)静默运行至 v3.2,与全链文档语义
        相反,主表数值面整体翻案(攻击第三轮 F1)——本断言使任何方向回退在跑批时即失败,
        不再依赖文档对账才被发现。
        """
        nax = len(dims)
        for axis, (size, up) in enumerate(dims):
            if up is None:
                continue
            others = [i for i in range(nax) if i != axis]
            for combo in product(*[range(dims[i][0]) for i in others]):
                seq = []
                for v in range(size):
                    key = [0] * nax
                    for pos, i in enumerate(others):
                        key[i] = combo[pos]
                    key[axis] = v
                    if tuple(key) in cur:
                        seq.append(cur[tuple(key)])
                for a, b in zip(seq, seq[1:], strict=False):
                    # 容差 1e-4:循环坐标 PAV 收敛后仍留 ~1e-6 量级的跨轴浮点残差,
                    # 真方向违反(历史 bug 量级 ≥0.1)在此容差下必然命中。
                    if up and a > b + 1e-4:
                        raise AssertionError(
                            f'方向护栏:轴{axis} 应沿下标非降,违反 {a:.4f}>{b:.4f}')
                    if (not up) and a < b - 1e-4:
                        raise AssertionError(
                            f'方向护栏:轴{axis} 应沿下标非增(血带=血↓危↑),违反 {a:.4f}<{b:.4f}')

    def monotone_fit_generic(cells_, dims, n_iter=60):
        """边缘回fitting PAV:dims=[(维长, 方向up/None)] 逐轴池化;方向 None 的轴只作切片。

        v3.2 泛化:板面键(对照存档)与 PL 键(主表)共用同一拟合器,只换 dims——
        位面维方向=up(位面↑危↑),修复候选评估期(旧 Part 9)借用板面负方向池化
        位面维的近似(彼时仅为候选对比的权宜,主表按正方向重拟)。
        v3.3:血带维(hp 升序下标)方向=down(血↓危↑),修复自 v3.0 起的反向约束;
        拟合后经 _assert_monotone_dirs 逐轴核验(方向护栏)。
        """
        cur = {}
        for c, (rate, _n) in raw_rates(cells_).items():
            cur[c] = rate
        nmap = {c: len(v) for c, v in cells_.items()}
        nax = len(dims)
        for _ in range(n_iter):
            before = dict(cur)
            for axis, (size, up) in enumerate(dims):
                if up is None:
                    continue
                others = [i for i in range(nax) if i != axis]
                for combo in product(*[range(dims[i][0]) for i in others]):
                    cs = []
                    for v in range(size):
                        key = [0] * nax
                        for pos, i in enumerate(others):
                            key[i] = combo[pos]
                        key[axis] = v
                        cs.append(tuple(key))
                    _pool(cur, nmap, cs, up=up)
            if all(abs(cur[c] - before[c]) < 1e-9 for c in cur):
                break
        _assert_monotone_dirs(cur, dims)
        return cur

    # 板面键(对照存档):难度↑危↑ / 血↓危↑(v3.3 方向修复) / 板面↑危↓ / 节点=切片
    def monotone_fit(cells_, n_iter=60):
        return monotone_fit_generic(cells_, [(ND, True), (3, False), (NB, False), (4, None)], n_iter)

    def _pool(cur, nmap, cs, up=True):
        idx = [c for c in cs if c in cur]
        if len(idx) < 2:
            return
        vs = [cur[c] for c in idx]
        ws = [nmap[c] for c in idx]
        pooled = _pav_seq(vs, ws, up)
        for c, v in zip(idx, pooled, strict=False):
            cur[c] = v

    def _pav_seq(vs, ws, up=True):
        if not up:
            vs = [-v for v in vs]
        blocks = []  # [start, value, weight]
        for v, w in zip(vs, ws, strict=False):
            blocks.append([v, w, 1])
            while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
                v2 = (blocks[-2][0] * blocks[-2][1] + blocks[-1][0] * blocks[-1][1]) / (blocks[-2][1] + blocks[-1][1])
                w2 = blocks[-2][1] + blocks[-1][1]
                cnt = blocks[-2][2] + blocks[-1][2]
                blocks = blocks[:-2]
                blocks.append([v2, w2, cnt])
        out = []
        for b in blocks:
            out.extend([b[0]] * b[2])
        if not up:
            out = [-v for v in out]
        return out

    fit = monotone_fit(cells)

    # cluster bootstrap(match 级):重跑 raw+monotone,得每格 CI
    rng = random.Random(42)
    boot = {c: [] for c in fit}
    ms = list(matches)
    for _ in range(N_BOOT):
        samp = [ms[rng.randrange(len(ms))] for _ in range(len(ms))]
        bcells = {}
        for m in samp:
            for r in m['rounds']:
                bcells.setdefault(cell_of(r), []).append(r)
        if not bcells:
            continue
        {c: (sum(x['y'] for x in v) / len(v), len(v)) for c, v in bcells.items()}
        bfit = monotone_fit(bcells)
        for c in fit:
            if c in bfit:
                boot[c].append(bfit[c])
    print('\nλ3 表(格: 难度带/血带/板面/节点 | n实数 | 原始率 | 单调估计 [95%CI]):')
    empty = 0
    nn_names = ['battle', 'encounter', 'boss', 'noncombat']
    for d in range(ND):
        for h in range(3):
            for b in range(NB):
                for nn in range(NN):
                    c = (d, h, b, nn)
                    lo_band, hi_band = bands[d]
                    if c not in fit:
                        empty += 1
                        print(f'  D{d}({lo_band}<{hi_band}) {HB[h]} B{b} {nn_names[nn]}:<空格 n=0>')
                        continue
                    rate, n = raw[c]
                    bs = sorted(boot[c])
                    if bs:
                        lo = bs[int(ALPHA / 2 * len(bs))]
                        hi = bs[min(len(bs) - 1, int((1 - ALPHA / 2) * len(bs)))]
                    else:
                        lo = hi = float('nan')
                    print(f'  D{d}({lo_band}<{hi_band}) {HB[h]} B{b} {nn_names[nn]}: '
                          f'n={n} 原始={rate:.3f} 单调={fit[c]:.3f} '
                          f'[{lo:.3f},{hi:.3f}]'
                          + ('  ⚠原始n小' if n < 20 else ''))
    print(f'空格数:{empty}/{ND*3*NB*NN}(显式标空,禁填假值)')

    # ===== Part 3M(v3.2 主表). PL 键(位面键)λ3 表:完整格值 + CI + 单调估计 =====
    # R30-1:位面键候选升为主表输出——设计件键声明(难度×血×位面×节点)与工件主表自此
    # 同构;板面键表(Part 3A,上文)降为对照存档,标签 B0/B1/B2 保留防撞名。
    NPL = 2
    PL = ['P1', 'P2+']
    print('\n== Part 3M(v3.3 主表). PL 键(位面键)λ3(视界 3 轮;单调:血↓危↑[v3.3 方向修复]/难度↑危↑/位面↑危↑)==')
    print(f'格子全集:{ND}难度带 × 3血带 × {NPL}位面(P1/P2+) × 4节点 = {ND*3*NPL*NN} 格')

    def cellPL(r):
        return (r['dband'], HB.index(r['hband']), r['pband'],
                ['battle', 'encounter', 'boss', 'noncombat'].index(r['node4']))

    pl_cells = {}
    for r in rows:
        pl_cells.setdefault(cellPL(r), []).append(r)
    raw_pl = raw_rates(pl_cells)

    # PL 键(主表)单调拟合:难度↑危↑ / 血↓危↑(v3.3 方向修复) / 位面↑危↑
    def monotone_fit_pl(cells_, n_iter=60):
        return monotone_fit_generic(cells_, [(ND, True), (3, False), (NPL, True), (4, None)], n_iter)

    fit_pl = monotone_fit_pl(pl_cells)

    # cluster bootstrap(match 级,与板面键存档同管道/同种子口径)
    rng_pl = random.Random(42)
    boot_pl = {c: [] for c in fit_pl}
    for _ in range(N_BOOT):
        samp = [ms[rng_pl.randrange(len(ms))] for _ in range(len(ms))]
        bcells = {}
        for m in samp:
            for r in m['rounds']:
                bcells.setdefault(cellPL(r), []).append(r)
        if not bcells:
            continue
        bfit = monotone_fit_pl(bcells)
        for c in fit_pl:
            if c in bfit:
                boot_pl[c].append(bfit[c])
    print('\nPL 键 λ3 主表(格: 难度带/血带/位面/节点 | n实数 | 原始率 | 单调估计 [95%CI]):')
    empty_pl = 0
    for d in range(ND):
        for h in range(3):
            for p in range(NPL):
                for nn in range(NN):
                    c = (d, h, p, nn)
                    lo_band, hi_band = bands[d]
                    if c not in fit_pl:
                        empty_pl += 1
                        print(f'  D{d}({lo_band}<{hi_band}) {HB[h]} {PL[p]} {nn_names[nn]}:<空格 n=0>')
                        continue
                    rate, n = raw_pl[c]
                    bs = sorted(boot_pl[c])
                    if bs:
                        lo = bs[int(ALPHA / 2 * len(bs))]
                        hi = bs[min(len(bs) - 1, int((1 - ALPHA / 2) * len(bs)))]
                    else:
                        lo = hi = float('nan')
                    print(f'  D{d}({lo_band}<{hi_band}) {HB[h]} {PL[p]} {nn_names[nn]}: '
                          f'n={n} 原始={rate:.3f} 单调={fit_pl[c]:.3f} '
                          f'[{lo:.3f},{hi:.3f}]'
                          + ('  ⚠原始n小' if n < 20 else ''))
    print(f'PL 键(主表)空格数:{empty_pl}/{ND*3*NPL*NN}(显式标空,禁填假值);'
          f'非空格 {ND*3*NPL*NN - empty_pl}')

    # ===== Part 4-7(v3.2 注):板面键(对照存档)验证组——旧键(板面×节点)vs 板面键四维
    # 的对照口径,v3.2 后服务于对照存档与 v3.1-1 扫描带历史声明;主表(PL 键)的跨形态
    # 验证=Part 9(PL 键 vs 板面键 vs 残差化,held-out/LOO/AIC)=====
    print('\n== Part 4-1. 同格亚组异质性复检(实机语料直测;板面键对照存档口径)==')
    # 旧钥匙:板面粗档(3)×节点(3 战斗类)——hp 不入键(旧表口径)
    old_cells = {}
    for r in rows:
        if r['node4'] == 'noncombat':
            continue
        old_cells.setdefault((r['bband'], r['node4']), []).append(r)

    def spread(cs_rows, key_fn):
        """格内按 key_fn 分亚组的 λ3 极差(带亚组 n>=10 才计入)。"""
        subs = {}
        for r in cs_rows:
            subs.setdefault(key_fn(r), []).append(r['y'])
        vals = [(mean(v), len(v)) for v in subs.values() if len(v) >= 10]
        if len(vals) < 2:
            return None
        return max(v for v, _ in vals) - min(v for v, _ in vals)

    old_spreads = []
    for c, v in old_cells.items():
        s = spread(v, lambda r: hp_band(r['hp']))
        if s is not None:
            old_spreads.append((s, c, len(v)))
    if old_spreads:
        print(f'旧钥匙格内按【血带】亚组 λ3 极差:n格={len(old_spreads)} '
              f'最大={max(s for s,_,_ in old_spreads):.3f} '
              f'中位={median(sorted(s for s,_,_ in old_spreads)):.3f}')
        for s, c, n in sorted(old_spreads, reverse=True)[:5]:
            print(f'    旧格 B{c[0]}×{c[1]} n={n}: 血带极差={s:.3f}')
    new_spreads_gold, new_spreads_plane = [], []
    for c, v in cells.items():
        if c not in fit or c[3] == 3:
            continue
        sg = spread(v, lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50')
        sp = spread(v, lambda r: min(r['plane'], 2))
        if sg is not None:
            new_spreads_gold.append(sg)
        if sp is not None:
            new_spreads_plane.append(sp)
    for tag, arr in (('金位(<=50/>50)', new_spreads_gold), ('位面(1/2+)', new_spreads_plane)):
        if arr:
            print(f'新钥匙格内按【{tag}】残余亚组 λ3 极差:n格={len(arr)} '
                  f'最大={max(arr):.3f} 中位={median(sorted(arr)):.3f}')

    # ===== Part 5:验证② held-out 留出(前后半分治交叉)=====
    print('\n== Part 4-2. held-out 留出验证(按日期前/后半交叉)==')
    dates = sorted(m['date'] for m in matches)
    cut = dates[len(dates) // 2]
    half_a = [m for m in matches if m['date'] < cut]
    half_b = [m for m in matches if m['date'] >= cut]
    print(f'切分点={cut}:前半 {len(half_a)} 局 / 后半 {len(half_b)} 局')
    for tag, tr, te in (('前半→后半', half_a, half_b), ('后半→前半', half_b, half_a)):
        tcells = {}
        for m in tr:
            for r in m['rounds']:
                tcells.setdefault(cell_of(r), []).append(r)
        tfit = monotone_fit(tcells)
        ter = [r for m in te for r in m['rounds'] if cell_of(r) in tfit]
        if not ter:
            print(f'{tag}:测试侧无可预测行')
            continue
        obs = mean(r['y'] for r in ter)
        pred = mean(tfit[cell_of(r)] for r in ter)
        # 校准:按预测值两档(>0.1 / <=0.1)看观测
        hi = [r for r in ter if tfit[cell_of(r)] > ROUTE_THR]
        lo_ = [r for r in ter if tfit[cell_of(r)] <= ROUTE_THR]
        cal = (f'高段 n={len(hi)} 预测={mean(tfit[cell_of(r)] for r in hi):.3f} '
               f'观测={mean(r["y"] for r in hi):.3f}') if hi else '高段无行'
        cal2 = (f'低段 n={len(lo_)} 预测={mean(tfit[cell_of(r)] for r in lo_):.3f} '
                f'观测={mean(r["y"] for r in lo_):.3f}') if lo_ else '低段无行'
        print(f'{tag}: 覆盖 {len(ter)} 行 | 总体 预测={pred:.3f} 观测={obs:.3f} '
              f'绝对校准差={abs(pred - obs):.3f} | {cal} | {cal2}')

    # ===== Part 6:验证③ 0.1 阈值路由翻转面 =====
    print('\n== Part 4-3. 0.1 阈值路由翻转面(实机行级;对照旧钥匙混合值)==')
    # 旧钥匙混合估计(板面×节点,战斗行,不分血/难度——旧表形态)
    old_mixed = {c: mean(r['y'] for r in v) for c, v in old_cells.items() if v}
    flips = 0
    tot = 0
    for r in rows:
        if r['node4'] == 'noncombat':
            continue
        oc = (r['bband'], r['node4'])
        if oc not in old_mixed or cell_of(r) not in fit:
            continue
        tot += 1
        if (old_mixed[oc] > ROUTE_THR) != (fit[cell_of(r)] > ROUTE_THR):
            flips += 1
    if tot:
        print(f'战斗行 n={tot}:旧混合值 vs 新分层值在 {ROUTE_THR} 阈值两侧翻转 '
              f'{flips} 行 = {flips / tot:.1%}(旧表内部对照口径下的翻转面)')
    # 新钥匙自身的阈值稳健性:0.1 落在格 CI 内的行占比(高=决策余量不足)
    frag = sum(1 for r in rows
               if r['node4'] != 'noncombat' and cell_of(r) in fit
               and boot.get(cell_of(r))
               and min(boot[cell_of(r)]) <= ROUTE_THR <= max(boot[cell_of(r)]))
    ncomb = sum(1 for r in rows if r['node4'] != 'noncombat' and cell_of(r) in fit)
    if ncomb:
        print(f'新钥匙:0.1 落在格 bootstrap CI 内的战斗行 {frag}/{ncomb} = {frag / ncomb:.1%}'
              f'(越低=阈值余量越足)')
    # 与攻击报告 §4.2 同口径的行级翻转:格值 vs 格内【亚组】值在阈值两侧翻转的比例
    # (旧钥匙亚组=血带——攻击报告的翻转源;新钥匙亚组=金位带——残余混杂检验)。
    # 阈值组:0.1(旧表刻度)+ 实机战斗行 λ3 分布的 p25/p50(相对刻度——实机危险率
    # 整体高于 sim 旧表一个量级,0.1 在实机分布上不切分,须用分位阈值解耦
    # 「分层稳定性」与「绝对刻度」两个问题)
    def row_flip(cells_, sub_fn, thr):
        nrow = nfl = 0
        for _c, v in cells_.items():
            cv = mean(r['y'] for r in v)
            subs = {}
            for r in v:
                subs.setdefault(sub_fn(r), []).append(r)
            for r in v:
                sv = subs[sub_fn(r)]
                if len(sv) < 5:
                    continue  # 亚组太薄不构成可信对照
                nrow += 1
                if (cv > thr) != (mean(x['y'] for x in sv) > thr):
                    nfl += 1
        return nfl, nrow

    sorted(r['y'] for r in rows if r['node4'] != 'noncombat')
    # 阈值刻度:实机格值分布的分位(逐行 y 是 0/1,分位须在预测值层面取)
    preds = sorted(fit[cell_of(r)] for r in rows
                   if r['node4'] != 'noncombat' and cell_of(r) in fit)
    q33 = preds[len(preds) // 3]
    q50 = preds[len(preds) // 2]
    new_combat = {c: v for c, v in cells.items() if c in fit and c[3] != 3}
    for thr, tag in ((ROUTE_THR, '0.1(旧表刻度)'), (q33, f'实机预测p33={q33:.2f}'),
                     (q50, f'实机预测p50={q50:.2f}')):
        fo, no = row_flip(old_cells, lambda r: hp_band(r['hp']), thr)
        fn_, nn_ = row_flip(new_combat, lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50', thr)
        fo2, no2 = row_flip(old_cells, lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50', thr)
        print(f'  阈值{tag}: 旧键[亚组=血带] {fo}/{no}={fo / no:.1%} | '
              f'旧键[亚组=金位] {fo2}/{no2}={fo2 / no2:.1%} | '
              f'新键[亚组=金位] {fn_}/{nn_}={fn_ / nn_:.1%}')

    # ===== Part 7(v3.1). 阈值消费改扫描带:thr∈[0.40,0.65] 翻转面全扫描 =====
    # 缘由:基座攻击第二轮 §3 判决——官方 p33 在单调估计上=0.58 且 p33==p50(池化平台,
    # 分位不唯一),「减半」结论是阈值位置的函数(thr∈[0.43,0.59] 窄带内对比三次变号)。
    # v3.1 处置:废弃单 p33 锚,产出全扫描曲线;消费端只许引用「阈值带 + 带内翻转面上界」。
    print('\n== Part 7(v3.1). 翻转面阈值扫描带(thr 0.40→0.65,步长 0.01)==')
    from math import sqrt

    def wilson_lo(k: int, n: int, z: float = 1.96) -> float:
        """Wilson 下限(n<20 薄格的强制下界口径;bootstrap CI 会锁死伪精度)。"""
        if n == 0:
            return float('nan')
        p = k / n
        d = 1 + z * z / n
        c = p + z * z / (2 * n)
        h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return max(0.0, (c - h) / d)

    # 池化臂:全部战斗行当一格(无分层),亚组翻转=池化形态的固有病(攻击报告口径)
    pool_combat_rows = [r for r in rows if r['node4'] != 'noncombat' and cell_of(r) in fit]

    def flip_pooled(sub_fn, thr):
        cv = mean(r['y'] for r in pool_combat_rows)
        subs = {}
        for r in pool_combat_rows:
            subs.setdefault(sub_fn(r), []).append(r['y'])
        nrow = nfl = 0
        for r in pool_combat_rows:
            sv = subs[sub_fn(r)]
            if len(sv) < 5:
                continue
            nrow += 1
            if (cv > thr) != (mean(sv) > thr):
                nfl += 1
        return nfl, nrow

    thrs = [round(0.40 + 0.01 * i, 2) for i in range(26)]
    print('thr   | 新键[金位] | 旧键[金位] | 旧键[血带] | 池化[血带] | 池化[金位] | 新vs旧(金位)')
    scan = []
    for thr in thrs:
        fn_, nn_ = row_flip(new_combat, lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50', thr)
        fo2, no2 = row_flip(old_cells, lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50', thr)
        fo, no = row_flip(old_cells, lambda r: hp_band(r['hp']), thr)
        fp, np_ = flip_pooled(lambda r: hp_band(r['hp']), thr)
        fpg, npg = flip_pooled(lambda r: 'g<=50' if (r['gold'] or 0) <= 50 else 'g>50', thr)
        a, b = fn_ / nn_, fo2 / no2
        sign = '新<旧' if a < b else ('新>旧' if a > b else '持平')
        scan.append((thr, a, b))
        print(f'{thr:.2f}  |   {a:5.1%}   |   {b:5.1%}   |   {fo / no:5.1%}   |   '
              f'{fp / np_:5.1%}   |   {fpg / npg:5.1%}   | {sign}')
    # 变号区间(新 vs 旧[金位] 的次序在带内何处翻转——三变号如实呈现)
    signs = [('新<旧' if a < b else ('新>旧' if a > b else '持平')) for _, a, b in scan]
    intervals = []
    start = 0
    for i in range(1, len(signs) + 1):
        if i == len(signs) or signs[i] != signs[start]:
            intervals.append((scan[start][0], scan[i - 1][0], signs[start]))
            start = i
    print('带内次序区间(新键 vs 旧键,金位亚组):')
    for lo_, hi_, s in intervals:
        print(f'  thr∈[{lo_:.2f},{hi_:.2f}]:{s}')
    band_max_new = max(a for _, a, _ in scan)
    band_max_old = max(b for _, _, b in scan)
    print(f'带内翻转面上界:新键[金位] {band_max_new:.1%} / 旧键[金位] {band_max_old:.1%} '
          f'(消费端声明形态=「thr∈[0.40,0.65] 带内上界」,禁单点引用「减半」)')
    # p33 锚废弃的证据(平台态 + 两口径差)
    preds_raw_rows = sorted(raw[cell_of(r)][0] for r in rows
                            if r['node4'] != 'noncombat' and cell_of(r) in fit)
    print(f'注:单调估计口径下 p33==p50=={q50:.2f}(池化平台,分位不唯一);原始率口径 '
          f'p33={preds_raw_rows[len(preds_raw_rows) // 3]:.3f}'
          f'(与单调口径差约 0.15——单点锚不可用的第二证据)')

    # ===== Part 8(v3.2). PL 键(主表)空格回退处置 + 逐格消费标签 + C 集合/top-2/语料锚 =====
    # 缘由:v3.1-2/3 的处置表系板面键口径;R30-1 键单一源对齐后,消费标签/C 集合/
    # top-2 λ_U 格/激活率语料锚(R29-2 消费的 7 消费格枚举)全部按 PL 键(位面键)主表
    # 重做——板面键版标签(可消费 7/仅方向 28/禁用 18)随板面键表降为对照存档,禁再被
    # 下游(设计件 §2.0-3 规格① 的 |C|、§5.2 验收级锚)引用。
    # R31-1 对齐:本处置表三分类(有界外推/濒死转语义/守息)=设计件 §1 状态机第四态
    # 「空格回退格」的表侧权威编码,与域外(无行)/损坏(槽位 None)两态显式区分。
    print('\n== Part 8(v3.3). PL 键(主表)空格回退处置 + 逐格消费标签(可消费/仅方向/禁用)==')
    empty_cells = [(d, h, p, nn) for d in range(ND) for h in range(3) for p in range(NPL)
                   for nn in range(4) if (d, h, p, nn) not in fit_pl]

    def dominates_pl(nb, c):
        """单调偏序支配:难度≥/血带≤(血更低更危)/位面≤(位面更早更弱)⇒ λ(nb)≥λ(c)。"""
        return nb[0] >= c[0] and nb[1] <= c[1] and nb[2] <= c[2] and nb[3] == c[3]

    print(f'空格处置({len(empty_cells)} 格):')
    n_extrap = n_conv = n_hold = 0
    for c in sorted(empty_cells):
        sups = [fit_pl[nb] for nb in fit_pl if dominates_pl(nb, c)]
        if sups:
            n_extrap += 1
            fb = f'有界外推:λ≤{max(sups):.3f}(支配邻居上确界)'
        elif c[1] == 0:
            n_conv += 1
            fb = '转化优先段语义(P51 §7-1,非守息)'
        else:
            n_hold += 1
            fb = '守息(非濒死,维持)'
        print(f'  D{c[0]} {HB[c[1]]} {PL[c[2]]} {nn_names[c[3]]}: {fb}')
    print(f'计数:有界外推 {n_extrap} / 濒死转语义 {n_conv} / 守息 {n_hold}')
    # v3.3(F4):空格经验流量披露——空格全部在 P1 且语料 P1 无 hp≤15 决策行(濒死行只在
    # P2+ 出现)⇒ 第四态濒死分支(转化优先)经验触发面≈0;会实际走到的是 P1×hp15-40 的
    # 守息格与外推格。规格层闭合(R2 反向病已治)但经验层零流量,如实降格声明。
    p1_empty = [c for c in empty_cells if c[2] == 0]
    p1_lowhp_rows = sum(1 for r in rows if r['pband'] == 0 and r['hband'] == 'hp<=15')
    print(f'空格经验流量披露(F4):空格 P1 占 {len(p1_empty)}/{len(empty_cells)};'
          f'语料 P1×hp<=15 决策行={p1_lowhp_rows} 行(战斗类濒死行全在 P2+,P1 濒死行只落'
          f' noncombat 薄禁用格)——第四态濒死分支'
          f'(转化优先)经验触发面≈0,规格闭合/经验零流量(P1 空格 {len(p1_empty)} 格;'
          f'语料扩窗后 P1 濒死行出现时该分支自然激活,结构上保留)')
    print('论证:①濒死空格回退守息把「最需要转化止损的区域」推向错误默认(P51 §7-1 '
          '濒死转化优先),方向冲突是结构性的(v3.1-2 同款);②有界外推只在单调约束本身'
          '成立的偏序内借幅,上界=支配格现值,不引入新参数;③外推值只作「敞口上界」消费'
          '(禁当点估计);④无支配邻居的濒死格借不到幅,退给 hp 结构规则主干(转化优先),'
          '不是守息;⑤空格回退格=表状态机第四态(设计件 §1 R31-1 对齐):空格≠域外'
          '(无行)≠损坏(槽位 None)——本处置表产物系表侧权威回退,显式豁免「禁实现层'
          '外推」禁令(回退值≠表值≠外推消费)。')

    # 逐格消费标签(PL 键,v3.3):旧受污类「hp≤15 单调低估 / D0×hp>40 池化抬高」系血带轴
    # 方向反转 bug 的产物(方向修复后 hp≤15 不被压低、hp>40 不被拖高),随 F1 作废——
    # 改为数据驱动的池化偏移注:|拟合−原始|≥0.15 记「仅方向(池化偏移)」(如实报告实际
    # 池化方向与幅度,不再预设有两类病因);位面方向违反格(F3)=同(难度,血,节点)内
    # P2+ 原始率 < P1 原始率(双侧 n≥5)的 P2+ 格,加受污注并入重估监督项计数。
    print('\n逐格消费标签(PL 键主表;受污注=池化偏移 |Δfit−raw|≥0.15 / 位面方向违反[P2+ raw<P1]):')
    plane_viol_cells = set()
    n_plane_viol_pairs = 0
    for d in range(ND):
        for h in range(3):
            for nn in range(NN):
                c1 = (d, h, 0, nn)
                c2 = (d, h, 1, nn)
                if c1 in raw_pl and c2 in raw_pl and min(raw_pl[c1][1], raw_pl[c2][1]) >= 5:
                    if raw_pl[c2][0] < raw_pl[c1][0]:
                        plane_viol_cells.add(c2)
                        n_plane_viol_pairs += 1
    disp_stat = {'可消费': 0, '仅方向': 0, '禁用': 0, '空格': 0}
    n_pool_note = n_plane_note = 0
    labels_pl = {}
    for d in range(ND):
        for h in range(3):
            for p in range(NPL):
                for nn in range(4):
                    c = (d, h, p, nn)
                    if c not in fit_pl:
                        disp_stat['空格'] += 1
                        continue
                    rate, n = raw_pl[c]
                    bs = boot_pl.get(c) or []
                    ci_deg = bs and (max(bs) - min(bs)) < 1e-6  # bootstrap CI 锁死=伪精度
                    if n < 5:
                        lab = '禁用(n<5 外推畸形;CI 伪精度)' + ('[CI锁死]' if ci_deg else '')
                        disp_stat['禁用'] += 1
                    else:
                        shift = fit_pl[c] - rate
                        if abs(shift) >= 0.15:
                            lab = f'仅方向(池化偏移 Δ={shift:+.3f})'
                            disp_stat['仅方向'] += 1
                            n_pool_note += 1
                        else:
                            k = round(rate * n)
                            lab = ('可消费(n≥20)' if n >= 20
                                   else f'可消费(薄 n={n},CI 下限强制 Wilson={wilson_lo(k, n):.3f})')
                            disp_stat['可消费'] += 1
                        if c in plane_viol_cells:
                            lab += ' ⚠位面方向违反(P2+ 原始率<P1)'
                            n_plane_note += 1
                    if n < 20:
                        lab += ' ⚠n<20'
                    labels_pl[c] = lab
                    print(f'  D{d} {HB[h]} {PL[p]} {nn_names[nn]}: n={n} 原始={rate:.3f} '
                          f'单调={fit_pl[c]:.3f} → {lab}')
    print(f'标签汇总:{disp_stat};池化偏移注 {n_pool_note} 格;'
          f'位面方向违反 {n_plane_viol_pairs} 对/{n_plane_note} 格'
          f'(重估监督项:方向违反计数,语料扩窗后复跑对照)')
    # 池化偏移分布(受污面全量披露,供重估监督:0.05≤|Δ|<0.15 的轻偏移不换标签但计数)
    n_shift_5_15 = sum(1 for c in labels_pl
                       if c in fit_pl and c in raw_pl and 0.05 <= abs(fit_pl[c] - raw_pl[c][0]) < 0.15)
    print(f'池化偏移监督:|Δ|≥0.15(换标签){n_pool_note} 格 / 0.05≤|Δ|<0.15(轻偏移,不换标签)'
          f'{n_shift_5_15} 格 / 位面方向违反 {n_plane_viol_pairs} 对')

    # C 集合(可消费格)枚举 + top-2 λ_U 格 + 语料访问率锚(R29-2 枚举的 PL 键重做版;
    # 消费位=设计件 §2.0-3 规格① 的 k∈C 谓词与 §5.2 验收级锚)
    c_set = sorted(c for c, lab in labels_pl.items() if lab.startswith('可消费'))

    def _ceil_frac(x):
        return int(-(-x // 1))

    def ci_upper_pl(c):
        bs = sorted(boot_pl.get(c) or [])
        if not bs:
            return fit_pl[c]
        return bs[min(len(bs) - 1, int((1 - ALPHA / 2) * len(bs)))]

    print(f'\nC 集合(可消费格 {len(c_set)} 个;键坐标=难度×血带×位面×节点):')
    for i, c in enumerate(c_set, 1):
        rate, n = raw_pl[c]
        print(f'  #{i} D{c[0]}×{HB[c[1]]}×{PL[c[2]]}×{nn_names[c[3]]}: '
              f'n={n} 单调={fit_pl[c]:.3f} λ_U(CI上端)={ci_upper_pl(c):.3f}')
    # v3.3(F2,R31-6 落地):#T 界改 λ_U 去重 distinct 值口径——k_max = 位置口径界 +
    # (最大并列组大小−1);排序次键=n 大者优先(λ_U 并列时确定性打破,可复现);
    # 并列度一行入重估监督(旧位置口径在 λ_U=1.000 并列组下不是上界)。
    def lam_u_sort_key(c):
        _, n = raw_pl[c]
        return (ci_upper_pl(c), n, fit_pl[c])

    top2 = sorted(c_set, key=lam_u_sort_key, reverse=True)[:2]
    visits = sum(len(pl_cells[c]) for c in top2 if c in pl_cells)
    n_rows = len(rows)
    print('top-2 λ_U 格:' + ';'.join(
        f' D{c[0]}×{HB[c[1]]}×{PL[c[2]]}×{nn_names[c[3]]}(λ_U={ci_upper_pl(c):.3f})'
        for c in top2))
    n_c = len(c_set)
    lu_seq = sorted((ci_upper_pl(c) for c in c_set), reverse=True)
    tie_cnt = {}
    for v in lu_seq:
        tie_cnt[round(v, 6)] = tie_cnt.get(round(v, 6), 0) + 1
    n_distinct = len(tie_cnt)
    max_tie = max(tie_cnt.values())
    k_pos = n_c - _ceil_frac(0.80 * n_c) + 1  # 位置口径界(p 带下端 0.80)
    k_max = k_pos + (max_tie - 1)             # distinct 口径界(R31-6)
    topk = sorted(c_set, key=lam_u_sort_key, reverse=True)[:k_max]
    visits_k = sum(len(pl_cells[c]) for c in topk if c in pl_cells)
    print(f'#T 并列界(R31-6 distinct 口径):|C|={n_c},λ_U distinct 值 {n_distinct} 个,'
          f'最大并列组大小 {max_tie} ⇒ k_max={k_pos}+({max_tie}−1)={k_max}'
          f'(位置口径界 {k_pos} 在并列组下不是上界,禁单独引用);'
          f'λ_U 全序={[round(v, 3) for v in lu_seq]}(重估监督项:并列度超限同步重算)')
    print(f'带内最宽触发格数 k_max={k_max}(distinct 口径);top-{k_max} 并集=' + ';'.join(
              f'D{c[0]}×{HB[c[1]]}×{PL[c[2]]}×{nn_names[c[3]]}' for c in topk))
    print(f'语料访问率锚:top-2 格访问行数={visits}/{n_rows}≈{visits / n_rows:.1%};'
          f'top-{k_max} 并集(稳健上界口径,distinct 界)={visits_k}/{n_rows}≈{visits_k / n_rows:.1%}'
          '(行=逐 (plane,round) 末帧决策行,与 §5.2 门的帧口径单位不同——R30-6 口径声明:'
          '行≈12.8 行/局系逐轮末帧行,非备战期决策帧;门的帧占比分母须换算或声明同单位)')
    print('n<20 合并规则(v3.1 口径随主表继承):薄格报告值=单调池化值(PAV 已向单调相邻格'
          '池化),CI 下限强制取该格原始 n 的 Wilson 下限(不吃池化方差);n=2/3 的 CI[1,1]'
          ' 形态(bootstrap 锁死)一律按禁用处理,禁入消费。')

    # ===== Part 9(v3.2). 键形态对比:PL 键(位面键·主表)vs 板面键(对照存档)vs 残差化 =====
    # 缘由:基座攻击第二轮 §2(b)——B0 行 405/405 全在 P1、B2 行 171/228 在 P2,板面维
    # 在本语料≈位面/进程代理,信息量被进程吃掉。PL 键=去板面换位面(v3.1 候选期名「B1」,
    # v3.2 更名「PL 键(位面键)」防与板面档 B1 撞名,升主表);板面残差化=对照
    # (star_sum 减同位面×轮段中位,残差分 3 档)。对比口径=held-out 校准差 + LOO
    # (leave-one-match-out)log-loss/Brier + binomial AIC(k=非空格数)。
    # v3.2 修正:PL 键的拟合 dims=位面↑危↑——候选期(旧 Part 9)借用板面负方向池化
    # 位面维系评估近似,主表与对比均按正方向重拟(数字相对 v3.1 存档有变化,如实重报)。
    print('\n== Part 9(v3.3). 键形态对比(PL 键(位面键)=难度×血×位面×节点·主表 / A=板面键·对照存档 / B2=板面残差化;血带维均按 v3.3 方向修复重拟)==')
    import math as _m

    # 位面带:P1 / P2+(P2 并 P3,P3 n 极薄);pband 已在行组装段定义
    # B2 残差化:同 (plane, round) 中位 star_sum 为期望,残差按三分位分档
    med_sr = {}
    for r in rows:
        med_sr.setdefault((r['plane'], r['round']), []).append(r['star_sum'])
    med_map = {k: median(v) for k, v in med_sr.items()}
    resid = sorted(r['star_sum'] - med_map[(r['plane'], r['round'])] for r in rows)
    r_edges = sorted({-10**6, resid[len(resid) // 3], resid[2 * len(resid) // 3], 10**6})

    def resid_band(v):
        for i in range(len(r_edges) - 1):
            if r_edges[i] <= v < r_edges[i + 1]:
                return i
        return len(r_edges) - 2

    def cellA(r):
        return cell_of(r)

    def cellB1(r):
        return (r['dband'], HB.index(r['hband']), r['pband'],
                ['battle', 'encounter', 'boss', 'noncombat'].index(r['node4']))

    def cellB2(r):
        return (r['dband'], HB.index(r['hband']), resid_band(r['star_sum'] - med_map[(r['plane'], r['round'])]),
                ['battle', 'encounter', 'boss', 'noncombat'].index(r['node4']))

    def logloss(p, y):
        p = min(max(p, 1e-6), 1 - 1e-6)
        return -(y * _m.log(p) + (1 - y) * _m.log(1 - p))

    def eval_form(cf, tag, dims):
        # dims=该键形态的单调拟合维规格(见 monotone_fit_generic)
        # (i) held-out 日期分半(与 Part 5 同口径)
        ho = []
        for _t, tr, te in (('前→后', half_a, half_b), ('后→前', half_b, half_a)):
            tc = {}
            for m in tr:
                for r in m['rounds']:
                    tc.setdefault(cf(r), []).append(r)
            tfit = monotone_fit_generic(tc, dims)
            ter = [r for m in te for r in m['rounds'] if cf(r) in tfit]
            if not ter:
                continue
            ho.append(abs(mean(tfit[cf(r)] for r in ter) - mean(r['y'] for r in ter)))
        # (ii) LOO(leave-one-match-out,monotone 每折重拟)
        ll = br = cnt = 0
        for i in range(len(matches)):
            tc = {}
            for j, m in enumerate(matches):
                if j == i:
                    continue
                for r in m['rounds']:
                    tc.setdefault(cf(r), []).append(r)
            tfit = monotone_fit_generic(tc, dims)
            for r in matches[i]['rounds']:
                if cf(r) in tfit:
                    ll += logloss(tfit[cf(r)], r['y'])
                    br += (tfit[cf(r)] - r['y']) ** 2
                    cnt += 1
        # (iii) binomial AIC(全量拟,k=非空格数)
        allc = {}
        for r in rows:
            allc.setdefault(cf(r), []).append(r)
        afit = monotone_fit_generic(allc, dims)
        dev = 2 * sum(logloss(afit[cf(r)], r['y']) for r in rows if cf(r) in afit)
        k = len(afit)
        aic = dev + 2 * k
        print(f'  {tag}: 非空格={k} | held-out 校准差={"/".join(f"{x:.3f}" for x in ho)} | '
              f'LOO log-loss={ll / cnt:.4f} Brier={br / cnt:.4f} | AIC={aic:.0f}(dev={dev:.0f},k={k})')
        return {'tag': tag, 'k': k, 'ho': ho, 'loo_ll': ll / cnt, 'brier': br / cnt, 'aic': aic}

    dims_board = [(ND, True), (3, False), (NB, False), (4, None)]  # v3.3:血带维 down
    dims_pl = [(ND, True), (3, False), (NPL, True), (4, None)]     # v3.3:血带维 down
    eval_form(cellA, 'A(板面键 B0/B1/B2·对照存档)', dims_board)
    eval_form(cellB1, 'PL 键(位面键)·主表', dims_pl)
    eval_form(cellB2, 'B2(难度×血×板面残差×节点·对照)', dims_board)
    print('\n  读法:AIC 越低越好(同时惩罚格数);LOO/Brier 越低越好;held-out 越低越好。'
          'AIC 差 <10 视为无实质差异。')

    print('\n[完成] 表值与验证数字供 P51_V3_REBUILD.md 引用;空格已显式标空。')


if __name__ == '__main__':
    main()
