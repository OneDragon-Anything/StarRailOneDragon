"""层 E 转正数据批:全通道 μ_E 重算 + π_offer 实采 + 序一致性检验(T-155)。

品质改写型层 E(design = changes/2026-09-12-invest-env/details/
env-value-models.md §2.2)的两参数表落参批重采入口:
- ``STRAT_POOL_ECON_MEANS``:μ_E(q; H) = 品质子池全通道金流均值,键 (品质, 视界);
- ``OFFER_QUALITY_DIST``:π_offer,k(q) = 第 k 次取卡 offer 品质分布。

**全通道口径**(转正准入门第 1 条,§2.2.2):受限直接金流/XP 通道(v1 八通道)
+ 排除集补参——刷新族(免费刷新期望节金 = min(可发次数, 观测刷新需求窗口量)
× 基价 2)、息档覆写(观测金路径逐节点 E[min(g//10, cap)] − E[min(g//10, 5)]
递推,息律单源 = proofs/p47-interest-account.md,零新拟合)、合成/卖价族
(卖价倍数按观测卖出收入窗口期望;合成按档案逐轮星级事件计数)。仍无金流
参数化的通道按 0 计入并在输出中逐条申报(下偏方向):采购专员(商店构成
稳定器,层 Q 残域)、伟大征服连胜倍率(收入分解缺连胜独立分量)、武力刷新
(装备合成不可观测)、远见/期货族(期权=层 Q)、血本位族(换币种非金流)、
gold_per_20hp_lost(schema 注明故意不进经济分)、固定理财位面开始段(注册表
既挂待建模)。

**样本与滤波**(口径文档 = changes/2026-09-12-invest-env/details/
data-batch-estimates.md 同源纪律):真实档案(文件名不含 fake);完成局
(``endgame.result ∈ {win, loss}``)参与统计。统计面再排除两类「整局剔除」
污染——①品质改写局:chosen_env ∈ ENV_POOL_REWRITE,或任一取卡帧命中改写
后续 offer 的策略源(远见/彩虹期货±/黄金期货±/黄金投资/白银投资),取卡流
序号与品质分布被整体挪位;②扑满过热局:chosen_env 含 经济过热/经济严重
过热(奖励节点被扑满主题替换,卖出收入/金路径/息档等窗口先验系非普通局
形态)——净帧口径(对齐采样面「148 总/140 普通」裁定,T-152 扑满局同集)。
已知覆盖限制:chosen_env 仅部分档案非空,缺读局的①②按 env 判别的半边
失效(策略源判别不受影响;量化申报 = 口径文档 §2)。

**日程与截断口径**:全局节点号按结构日程 P1=9/P2=7/P3=9 先验(总 25;
P2=7 = economy.md §10.2 位面典型节点表 + boss@p2r7 档案实证;P3 语料零
完成局取上端 9)。语料完成局全部为败局,最大观测节点 < 总视界——窗口量对
语料未达的尾段节点按 0 计入(截断保守低估,_REWARD_SLOTS「P3 结构零样本
不计」先例同款);窗口参数因此系统性下偏,方向申报。

**取卡点位 H_k 实采**:档案 opening.invest_cards 的 strategy 帧按 ts 分组
(同 ts 三行 = 一次取卡事件,chosen=True 行标记真实选定);选定事件按时间
序编号 k=1..n,经逐轮 terminal_ts 夹逼定位帧所在轮(首个 terminal_ts ≥
帧时刻),已完成节点数 = 位面偏移 + (轮−1)(偏移按上述结构日程),H_k =
总视界 − 已完成(取卡发生在轮 r 进行中,当前轮计入剩余)。注册门:每 k
有效选定事件 n ≥ 20(与扑满采集门槛同族),不足则该位哨兵不落(禁拍值)。

**π_offer 归一口径**(data-batch-estimates.md §6 约定):offer 卡品质按注册
表 rarity 查得;查不得计「未解析」,按已知三品质份额等比例摊入归一。采样
警告在册:档案帧未区分取卡 offer 与同次取卡内刷新后的新 offer(全部帧行
计入,k 归属 = 该组时间夹逼到的取卡位)。

**μ_E 区间口径**:CI = 品质子池内逐卡全通道值的 percentile bootstrap 95%
(固定种子可复现)——辖「抽到哪张卡」的方差;窗口参数(刷新需求/金路径等)
的估计不确定度未向 μ_E 传播(二阶,申报)。窗口参数 CI = 跨局 bootstrap,
输出仅申报点值与口径。

**序一致性检验**(准入门第 2 条):每个已注册视界 H 上 μ_E(棱彩) > μ_E(金)
> μ_E(银) 须与品质游戏序【注】及 pick_value 品质中位序(定序证据)方向一致;
不一致 = 基数层测的不是「品质的价值」,维持 fail-closed 并回炉通道定义。

用法:
  uv run python tools/cw/env_pool_rewrite_estimates.py [--matches-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_POOL_REWRITE,
    INVESTMENT_STRATEGIES,
    EconomyEffect,
    normalize_invest_name,
    resolve_strategy_canonical,
)
from sr_od.application.currency_war.kernel.cw_vocab import REFRESH_COST_BASE

#: 缺省档案目录(与 tools/cw/env_economy_estimates.py 同域)
DEFAULT_MATCHES_DIR = Path('.debug/currency_war/telemetry/matches')

#: bootstrap 重采样数与随机种子(与 T-129 数据批同种子约定,可复现)
_BOOTSTRAP_N = 2000
_BOOTSTRAP_SEED = 20260912

_Z: float = 1.959964   # 95% 双侧正态分位(显式常量,不引 scipy)

#: 局总节点日程(结构真值口径):P1=9 恒(cw_plane_table NODES_PER_PLANE)、
#: P2=7(经济研究 §10.2 位面典型节点表 + boss@p2r7 实证 + kernel
#: nodes_of_plane「P2=7 槽 16 局语料实证」;注释引用不 import,判别工具
#: 独立)、P3=9 先验(语料零完成局,端点纪律 = 结构上端 9)。总视界 25。
#: v1 详设的「schedule_of 先验 9+9+9=27」是 P2 真值入册前的回退口径,本批
#: 落参以结构真值 25 为准(H_k 实采同映射,两口径差随批申报)。
_PLANE_OFFSETS: dict[int, int] = {1: 0, 2: 9, 3: 16}
_TOTAL_NODES = 25
_NODES_PER_PLANE = 9

#: 首领槽位先验 = 各位面末槽(cw_plane_table.plane_end_slots 语义「boss
#: 奖金槽」;1 基全局号;(9,7,9) → {9, 16, 25})。档案实证:boss 记录只出现
#: 在 (1,9)/(2,7),从未出现在其它轮——「逐轮众数 >50%」门在本语料受死亡轮
#: 记录噪声压制(16 号槽 boss 13/23),故取结构规则并附实证计数申报。
_BOSS_SLOTS: tuple[int, ...] = (9, 16, 25)

#: H_k/π_offer,k 每取卡位注册门(有效样本下限;与扑满采集 ≥20 门槛同族)
_MIN_PICK_SAMPLES = 20

#: 改写后续取卡 offer 的策略源(效果原文:远见=后续策略节点改棱彩;彩虹期货
#: ±=N 节点后一次棱彩取卡;黄金期货± 同构金;黄金/白银投资=即时+3 节点后
#: 各一次定品质取卡)。命中任一 → 该局整体排除(取卡流序号被挪位)。
_QUALITY_PICK_SOURCES = frozenset({
    '远见', '彩虹期货', '彩虹期货+', '黄金期货', '黄金期货+',
    '黄金投资', '白银投资',
})

#: 扑满变体环境(净帧口径排除集):效果原文「本局的全部奖励节点替换为次元
#: 扑满主题,掉落更多战利品」——卖出收入/金路径/息档等窗口先验系非普通局
#: 形态,混入系统性抬高统计面。与 T-152 扑满局在册集(经济过热 ×7 + 经济
#: 严重过热 ×1)同源;采样面裁定「148 总/140 普通」的「普通」即非扑满局。
_PIGGY_ENVS = frozenset({'经济过热', '经济严重过热'})

#: v1 在册 H_1 参照值(cw_env_economy._STRAT_PICK_HORIZONS 现值;对拍用)
_V1_H1_REF = 24

#: 品质递增方向(准入门第 2 条基准:棱彩 > 金 > 银)
_QUALITY_ORDER = ('银', '金', '棱彩')


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
    """均值的 percentile bootstrap 区间(零样本 → None)。"""
    if not xs:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(xs, k=len(xs))) / len(xs)
                   for _ in range(n_boot))
    lo_q = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    hi_q = 1.0 - lo_q
    return (means[int(lo_q * (n_boot - 1))], means[int(hi_q * (n_boot - 1))])


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _is_real_archive(p: Path) -> bool:
    return p.name.startswith('match_g_') and 'fake' not in p.name


def _char_cost(char_id: str) -> int:
    """角色费用(注册表查不得 = 0,星级事件按未知费用不计 2 费合成)。"""
    c = CHARACTERS.get(char_id)
    return int(c.cost) if c is not None and c.cost else 0


class MatchRecord:
    """单局提取结果:逐全局节点窗口量 + 取卡帧组 + 污染判别。"""

    def __init__(self) -> None:
        #: 逐节点原始窗口量(node 1 基全局 → 累计 dict;含 n = 局数计数)
        self.node_obs: dict[int, dict[str, float]] = {}
        #: 取卡帧组:按时间序 [(ts, [卡名×3], chosen_any)]
        self.pick_groups: list[tuple[datetime, list[str], bool]] = []
        #: 品质改写污染(env 或取卡源命中)
        self.polluted = False
        self.pollution_reasons: list[str] = []
        self.completed = False

    def note_pollution(self, reason: str) -> None:
        self.polluted = True
        self.pollution_reasons.append(reason)


def _scan_match(path: Path) -> MatchRecord:
    """单档案解析:窗口量逐节点聚合 + 取卡帧组 + 污染判别。

    逐轮量口径:CwActionLevelUpParam 动作数 = 购经验单击数(4 金/击);CwActionRefreshShopParam
    cost>0 记付费(旧 schema cost=None 剔除该动作);CwActionSellBenchParam.income 累加
    为卖出收入;CwActionBuyCardParam cost==5 计 5 费购买;星级事件 = deployed∪bench 中
    角色星级首次达到 2/3(同角色跨轮取最大,卖出后重合成的重复事件不计 =
    下偏申报);金/等级观测取该轮落账值。
    """
    rec = MatchRecord()
    j = json.loads(path.read_text(encoding='utf-8'))
    eg = j.get('endgame') or {}
    rec.completed = eg.get('result') in ('win', 'loss')

    # 污染判别 ①:环境在册名 ∩ ENV_POOL_REWRITE(品质改写挪位取卡流)
    # ∪ 扑满过热集(净帧口径,窗口先验非普通局形态)
    for e in ((j.get('opening') or {}).get('chosen_env') or []):
        name = e.get('name') if isinstance(e, dict) else str(e)
        if not name:
            continue
        name = normalize_invest_name(name)
        if name in ENV_POOL_REWRITE:
            rec.note_pollution(f'env={name}')
        elif name in _PIGGY_ENVS:
            rec.note_pollution(f'piggy={name}')

    # 取卡帧组:kind=strategy 按 ts 分组(同 ts = 同次取卡事件)
    groups: dict[datetime, list[str]] = {}
    group_chosen: dict[datetime, bool] = {}
    for card in ((j.get('opening') or {}).get('invest_cards') or []):
        if card.get('kind') != 'strategy':
            continue
        ts = _parse_ts(card.get('ts'))
        if ts is None:
            continue
        groups.setdefault(ts, []).append(str(card.get('name') or ''))
        if card.get('chosen'):
            group_chosen[ts] = True
    rec.pick_groups = sorted(
        ((ts, names, group_chosen.get(ts, False)) for ts, names in groups.items()),
        key=lambda g: g[0])

    # 污染判别 ②:任一帧组名单(保守:全组而非仅 chosen 行,防 chosen 行
    # OCR 残缺漏检)命中改写源 → 整局排除
    for _ts, names, _c in rec.pick_groups:
        hit = False
        for n in names:
            canon = resolve_strategy_canonical(normalize_invest_name(n))
            if canon is not None and canon in _QUALITY_PICK_SOURCES:
                rec.note_pollution(f'strategy={canon}')
                hit = True
                break
        if hit:
            break

    if not rec.completed:
        return rec   # 弃局:窗口量不入(截断 horizon);帧流已留判污染用

    prev_level: int | None = None
    for r in (j.get('rounds') or []):
        try:
            plane = int(r.get('plane') or 0)
            rnd = int(r.get('round') or 0)
        except (TypeError, ValueError):
            continue
        if plane < 1 or rnd < 1:
            continue
        node = _PLANE_OFFSETS.get(plane, 0) + rnd
        if plane not in _PLANE_OFFSETS or not 1 <= node <= _TOTAL_NODES:
            continue
        obs = rec.node_obs.setdefault(node, {
            'n': 0, 'refresh_total': 0.0, 'refresh_paid': 0.0,
            'sell_income': 0.0, 'buys5': 0.0, 'lu_clicks': 0.0,
            'levelup': 0.0, 'm2_any': 0.0, 'm2_cost2': 0.0, 'm3': 0.0,
            'gold': 0.0, 'gold_n': 0.0, 'min5': 0.0, 'min9': 0.0,
            'min10': 0.0, 'lv9': 0.0,
        })
        obs['n'] += 1
        for a in (r.get('actions') or []):
            t = a.get('__type__')
            if t == 'CwActionRefreshShopParam':
                c = a.get('cost')
                if c is None:
                    continue   # 旧 schema 无金额:不计入任何口径
                obs['refresh_total'] += 1
                if c > 0:
                    obs['refresh_paid'] += 1
            elif t == 'CwActionSellBenchParam':
                with suppress(TypeError, ValueError):
                    obs['sell_income'] += float(a.get('income') or 0)
            elif t == 'CwActionBuyCardParam':
                cost = (a.get('card') or {}).get('cost')
                try:
                    if cost is not None and int(cost) == 5:
                        obs['buys5'] += 1
                except (TypeError, ValueError):
                    pass
            elif t == 'CwActionLevelUpParam':
                obs['lu_clicks'] += 1
        # 星级事件(deployed ∪ bench;条目可含 None 占位)
        max_star: dict[str, int] = getattr(rec, '_max_star', None)
        if max_star is None:
            max_star = rec._max_star = {}
        for entry in list(r.get('deployed') or []) + list(r.get('bench') or []):
            if not isinstance(entry, dict):
                continue
            cid = entry.get('char_id')
            star = entry.get('star')
            if not cid or not star:
                continue
            try:
                star = int(star)
            except (TypeError, ValueError):
                continue
            seen = max_star.get(cid, 1)
            if star > seen:
                if star == 2:
                    obs['m2_any'] += 1
                    if _char_cost(cid) == 2:
                        obs['m2_cost2'] += 1
                elif star >= 3:
                    obs['m3'] += 1
                max_star[cid] = star
        # 等级轨迹:升级事件 + lv9 达成 + 金路径息档
        level = r.get('level')
        gold = r.get('gold')
        try:
            level = int(level) if level is not None else None
        except (TypeError, ValueError):
            level = None
        try:
            gold = float(gold) if gold is not None else None
        except (TypeError, ValueError):
            gold = None
        if level is not None:
            if prev_level is not None and level > prev_level:
                obs['levelup'] += (level - prev_level)
            if level >= 9:
                obs['lv9'] = 1.0
            prev_level = level
        if gold is not None:
            obs['gold'] += gold
            obs['gold_n'] += 1
            obs['min5'] += min(gold // 10, 5)
            obs['min9'] += min(gold // 10, 9)
            obs['min10'] += min(gold // 10, 10)
    return rec


def pick_events(rec: MatchRecord) -> list[tuple[int, list[str]]]:
    """取卡流:(k, 组内名单) 按时间序;含未选定刷新重读组。

    遍历:遇选定组(chosen=True)→ 取卡位 c+1 确立;未选定组归属 = 下一个
    将确立的取卡位 c+1(取卡屏刷新后的重读,同位);尾部落单的未选定组
    (最后一次选定后的屏重读,无后续取卡)按「k > 已确立位数」截断丢弃。
    k 从 1 起。
    """
    out: list[tuple[int, list[str]]] = []
    c = 0
    for _ts, names, chosen_any in rec.pick_groups:
        if chosen_any:
            c += 1
        out.append((c + (0 if chosen_any else 1), names))
    return [(k, names) for k, names in out if k <= c]


def collect(matches_dir: Path) -> tuple[int, int, list[MatchRecord], list[Path]]:
    """全档案扫描 → (目录文件数含 fake, 真实档案数, 匹配记录列表, 文件列表)。

    fake 档案计数后照旧排除(样本口径「148 总/140 普通」的总数面需要它;
    统计面永远只用真实档案)。
    """
    all_files = sorted(matches_dir.glob('match_g_*.json'))
    files = [p for p in all_files if _is_real_archive(p)]
    records: list[MatchRecord] = []
    for f in files:
        try:
            records.append(_scan_match(f))
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError) as exc:
            print(f'[warn] 档案解析失败跳过 {f.name}: {exc}')
            records.append(MatchRecord())   # 占位保持与文件索引对齐
    return len(all_files), len(files), records, files


def pick_horizon_samples(
        records: list[MatchRecord],
        rounds_by_index: dict[int, list[dict]]) -> dict[int, list[int]]:
    """H_k 实采:选定事件 k → 已完成节点数 → H = 25 − 已完成。

    时间夹逼:帧时刻落在「上一非空 terminal_ts 之后、首个 terminal_ts ≥ 帧
    时刻的轮」= 该轮进行中。全局节点号按结构日程映射(P1=9/P2=7/P3=9 先验,
    见 _PLANE_OFFSETS)。弃局不参与(horizon 被截断,后续取卡位不可定义);
    污染局整局排除。返回 (k → [H 样本])。
    """
    samples: dict[int, list[int]] = {}
    for idx, rec in enumerate(records):
        if rec.polluted or not rec.completed:
            continue
        ends: list[tuple[datetime, int, int]] = []
        for r in (rounds_by_index.get(idx) or []):
            ts = _parse_ts(r.get('terminal_ts'))
            if ts is None:
                continue
            try:
                ends.append((ts, int(r.get('plane') or 0), int(r.get('round') or 0)))
            except (TypeError, ValueError):
                continue
        if not ends:
            continue
        ends.sort()
        c = 0
        for ts, _names, chosen_any in rec.pick_groups:
            if not chosen_any:
                continue
            c += 1
            cur = next(((p, r) for t, p, r in ends if t >= ts), ends[-1][1:])
            completed = _PLANE_OFFSETS.get(cur[0], 0) + (cur[1] - 1)
            h = _TOTAL_NODES - completed
            if h >= 1:
                samples.setdefault(c, []).append(h)
    return samples


def pick_position_samples(
        records: list[MatchRecord],
        rounds_by_index: dict[int, list[dict]]) -> dict[int, Counter]:
    """取卡位 → (位面, 轮) 分布(实采落点申报用;滤波同 H_k)。"""
    positions: dict[int, Counter] = {}
    for idx, rec in enumerate(records):
        if rec.polluted or not rec.completed:
            continue
        ends: list[tuple[datetime, int, int]] = []
        for r in (rounds_by_index.get(idx) or []):
            ts = _parse_ts(r.get('terminal_ts'))
            if ts is None:
                continue
            try:
                ends.append((ts, int(r.get('plane') or 0), int(r.get('round') or 0)))
            except (TypeError, ValueError):
                continue
        if not ends:
            continue
        ends.sort()
        c = 0
        for ts, _names, chosen_any in rec.pick_groups:
            if not chosen_any:
                continue
            c += 1
            cur = next(((p, r) for t, p, r in ends if t >= ts), ends[-1][1:])
            positions.setdefault(c, Counter())[(cur[0], cur[1])] += 1
    return positions


def offer_quality_samples(records: list[MatchRecord]) -> dict[int, Counter]:
    """π_offer,k 原始计数:全部帧行(含刷新重读组)按取卡位 k × 品质计数。

    品质 = 注册表 rarity 查得;查不得计「未解析」(归一口径按已知三品质
    摊入,见模块 docstring)。污染局整局排除。
    """
    counts: dict[int, Counter] = {}
    for rec in records:
        if rec.polluted:
            continue
        for k, names in pick_events(rec):
            bucket = counts.setdefault(k, Counter())
            for n in names:
                s = INVESTMENT_STRATEGIES.get(normalize_invest_name(n))
                bucket[s.rarity if s is not None else '未解析'] += 1
    return counts


def node_profiles(records: list[MatchRecord]) -> dict[int, dict[str, float]]:
    """逐全局节点先验:完成局(净流)在该节点的窗口量均值 + 幸存局数。

    幸存者口径:只有到达该节的局贡献(语义 = 「若你在该节,期望量」);
    返回 {node: {key: 均值}},'survivors' 键 = 该节点幸存局数(原值,非均值)。
    """
    acc: dict[int, dict[str, float]] = {}
    for rec in records:
        if rec.polluted or not rec.completed:
            continue
        for node, obs in rec.node_obs.items():
            slot = acc.setdefault(node, {})
            for key, val in obs.items():
                slot[key + '_sum'] = slot.get(key + '_sum', 0.0) + val
    out: dict[int, dict[str, float]] = {}
    for node, slot in acc.items():
        n = slot.get('n_sum', 0.0)
        if n <= 0:
            continue
        means = {key[:-4]: val / n for key, val in slot.items()}
        means['survivors'] = n
        out[node] = means
    return out


def window_sum(profiles: dict[int, dict[str, float]], key: str,
               start_node: int, horizon: int) -> float | None:
    """窗口量 = Σ_{i=start+1..start+horizon} profile[i][key](节点越 25 截断;
    语料零幸存的尾段节点按 0 计入 = 截断保守低估,口径 = _REWARD_SLOTS
    「P3 结构零样本不计」先例;窗口内全部节点零样本 → None = 参数不可用)。"""
    total = 0.0
    seen = 0
    for node in range(start_node + 1,
                      min(_TOTAL_NODES, start_node + horizon) + 1):
        p = profiles.get(node)
        if p is None or key not in p:
            continue   # 语料未达的尾段:截断低估,不阻塞
        total += p[key]
        seen += 1
    return total if seen else None


def econ_value_full(eff: EconomyEffect, h: int, ctx: dict,
                    restricted: bool = False) -> float:
    """单策略全通道金流期望(econ_gold(s; H);restricted=True 退 v1 八通道,
    供详设初测(银3.31/金2.42/棱彩4.16)对拍验证通道实现同构)。"""
    start = _TOTAL_NODES - h
    v = 0.0
    # —— v1 受限八通道(详设 §2.2.2 econ_gold_v1 清单)——
    v += eff.instant_gold
    v += eff.gold_per_node * h
    v += eff.interest_flat_per_node * h
    v += eff.xp_per_node * h * ctx['xp_rate']
    v += eff.xp_instant * ctx['xp_rate']
    v += eff.gold_per_boss_node * ctx['bosses_in_window'](start, h)
    if eff.gold_next_nodes_count:
        v += eff.gold_next_nodes_amount * min(eff.gold_next_nodes_count, h)
    if eff.gold_at_level and eff.gold_at_level_target <= ctx['max_level_target']:
        # v1 口径 = 到达即全额(「升 8/9 必然发生」同族假设);全通道精化为
        # 窗口末经验 P(等级 ≥ target)(ctx['p_level_at'];语料未达尾段冻结
        # 在最大观测节点值,保守)
        p = 1.0 if restricted else ctx['p_level_at'](start + h)
        v += eff.gold_at_level * p
    # 受限名单外、确定性时点金(全通道补入;超发货币负债腿按注册表既有口径
    # 由消费端记,数值侧只记回流 +70)
    if not restricted and eff.gold_at_node and eff.gold_at_node_offset <= h:
        v += eff.gold_at_node
    if restricted:
        return v
    # —— 全通道补参(排除集;窗口量 None = 缺参 → 该通道按 0 计入)——
    e_total = ctx['w_total'](start, h)
    e_paid = ctx['w_paid'](start, h)
    if eff.free_refresh_burst and e_total is not None:
        v += min(eff.free_refresh_burst, e_total) * REFRESH_COST_BASE
    if eff.free_refresh_per_node and e_total is not None:
        v += min(eff.free_refresh_per_node * h, e_total) * REFRESH_COST_BASE
    if (eff.free_refresh_cond_gold_above and e_total is not None
            and ctx['cond_grants'](start, h) is not None):
        # 条件授予窗口期望(ctx['cond_grants'] 已按窗口逐节点求和),需求帽同族
        grants = ctx['cond_grants'](start, h)
        v += min(grants, e_total) * REFRESH_COST_BASE
    if eff.refresh_free_chance and e_total is not None:
        # 期望免费刷 = 概率 × 观测需求;持卡抬升需求未计 = 下偏申报
        v += eff.refresh_free_chance * e_total * REFRESH_COST_BASE
    if eff.xp_per_refresh and e_paid is not None:
        v += eff.xp_per_refresh * e_paid * ctx['xp_rate']
    if eff.xp_buy_cost_discount and ctx['w_lu'](start, h) is not None:
        v += eff.xp_buy_cost_discount * ctx['w_lu'](start, h)
    # 息档覆写:观测金路径逐节点 E[min(g//10, cap)] − E[min(g//10, 5)]
    # (息律单源 p47;买断制 cap=0 → 息归零,负项如实计入)
    if eff.interest_cap_override is not None:
        delta = ctx['interest_delta'](start, h, eff.interest_cap_override)
        if delta is not None:
            v += delta
    # 合成/卖价族(正常成型路上白得的被动经济)
    if eff.sell_price_mult != 1.0 and ctx['w_sell'](start, h) is not None:
        v += (eff.sell_price_mult - 1.0) * ctx['w_sell'](start, h)
    if eff.gold_per_2star2cost_merge and ctx['w_m2cost2'](start, h) is not None:
        v += eff.gold_per_2star2cost_merge * ctx['w_m2cost2'](start, h)
    if eff.gold_per_3star_merge and ctx['w_m3'](start, h) is not None:
        v += eff.gold_per_3star_merge * ctx['w_m3'](start, h)
    # 计数可观测通道
    if eff.gold_per_three_5cost and ctx['w_buys5'](start, h) is not None:
        v += eff.gold_per_three_5cost * ctx['w_buys5'](start, h)
    if eff.gold_per_level_up and ctx['w_levelup'](start, h) is not None:
        v += eff.gold_per_level_up * ctx['w_levelup'](start, h)
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--matches-dir', type=Path, default=DEFAULT_MATCHES_DIR)
    args = ap.parse_args()
    n_files, n_all, records, files = collect(args.matches_dir)
    n_completed = sum(1 for r in records if r.completed)
    n_polluted = sum(1 for r in records if r.polluted)
    n_piggy = sum(1 for r in records
                  if any(x.startswith('piggy=') for x in r.pollution_reasons))
    print(f'=== 样本(净帧口径) ===\n档案文件 {n_files}(含 fake '
          f'{n_files - n_all});真实 {n_all};扑满过热局 {n_piggy}'
          f'(真实普通口径 {n_all - n_piggy});完成局 {n_completed};'
          f'整局剔除污染局(改写 env/取卡源/扑满,含完成局) {n_polluted};'
          f'净帧完成局 {sum(1 for r in records if r.completed and not r.polluted)}')

    # 原始轮次二次读取(H_k 时间夹逼 + boss 槽)
    rounds_by_index: dict[int, list[dict]] = {}
    for i, f in enumerate(files):
        try:
            j = json.loads(f.read_text(encoding='utf-8'))
            rounds_by_index[i] = list(j.get('rounds') or [])
        except (json.JSONDecodeError, OSError):
            rounds_by_index[i] = []

    # ---- H_k 实采 ----
    h_samples = pick_horizon_samples(records, rounds_by_index)
    pos_samples = pick_position_samples(records, rounds_by_index)
    horizons: dict[int, int] = {}
    print(f'\n=== 取卡点位 H_k(净流完成局;日程 P1=9/P2=7/P3=9 先验,总 25;'
          f'H = 25 − 已完成;注册门 n≥{_MIN_PICK_SAMPLES}) ===')
    for k in sorted(h_samples):
        xs = h_samples[k]
        med = statistics.median(xs)
        ok = len(xs) >= _MIN_PICK_SAMPLES
        print(f'  k={k}: n={len(xs)} 落点(位面,轮)={dict(sorted(pos_samples[k].items()))} '
              f'中位 H={med:.1f} 分布={dict(sorted(Counter(xs).items()))}'
              f'{"  → 注册" if ok else "  → 样本不足,哨兵不落"}')
        if ok:
            horizons[k] = int(round(med))
    if 1 in horizons and horizons[1] != _V1_H1_REF:
        print(f'  (v1 在册 H_1={_V1_H1_REF} 系回退口径 9+9+9=27 下的参照值;'
              f'本批以结构日程 25 + 实采中位为准,差异随批申报)')

    # ---- boss 槽实证申报(槽位取结构规则 _BOSS_SLOTS,附档案 boss 计数)----
    boss_counter: dict[tuple[int, int], int] = {}
    for i in range(n_all):
        rec = records[i]
        if rec.polluted or not rec.completed:
            continue
        for r in (rounds_by_index.get(i) or []):
            if (r.get('node_type') or '') == 'boss':
                try:
                    key = (int(r.get('plane') or 0), int(r.get('round') or 0))
                except (TypeError, ValueError):
                    continue
                boss_counter[key] = boss_counter.get(key, 0) + 1
    print(f'\n=== 首领槽位先验(结构规则 = 位面末槽 {_BOSS_SLOTS};'
          f'档案 boss 记录计数 = {dict(sorted(boss_counter.items()))})===')

    # ---- 逐节点先验与窗口函数 ----
    prof = node_profiles(records)

    def _w(key: str):
        def f(start: int, h: int) -> float | None:
            return window_sum(prof, key, start, h)
        return f

    def _cond_grants(start: int, h: int) -> float | None:
        """本金充裕系:逐节点 E[条件免费刷授予数](观测金路径 50/10/3;
        语料未达尾段截断跳过,与 window_sum 同口径)。"""
        total = 0.0
        seen = 0
        for node in range(start + 1,
                          min(_TOTAL_NODES, start + h) + 1):
            slot = prof.get(node)
            if slot is None or slot.get('gold_n', 0) <= 0:
                continue
            g_mean = slot['gold'] / slot['gold_n']
            total += 0.0 if g_mean <= 50 else min(3.0, (g_mean - 50) // 10)
            seen += 1
        return total if seen else None

    def _interest_delta(start: int, h: int, cap: int) -> float | None:
        total = 0.0
        seen = 0
        for node in range(start + 1,
                          min(_TOTAL_NODES, start + h) + 1):
            slot = prof.get(node)
            if slot is None or slot.get('gold_n', 0) <= 0:
                continue
            if cap == 0:
                base = 0.0
            elif cap in (9, 10):
                base = slot[f'min{cap}'] / slot['gold_n']
            else:
                return None
            total += base - slot['min5'] / slot['gold_n']
            seen += 1
        return total if seen else None

    def _bosses_in_window(start: int, h: int) -> int:
        return sum(1 for b in _BOSS_SLOTS if start < b <= start + h)

    # P(等级 ≥ 9 @ 窗末):语料未达的窗末节点冻结在最大观测节点的值
    # (P 单调不减,冻结 = 保守;冻结值本身申报)
    _max_obs_node = max(prof) if prof else 0
    p_level = {node: prof[node].get('lv9', 0.0) for node in prof}
    _frozen_lv9 = p_level.get(_max_obs_node, 0.0)

    def _p_level_at(node: int) -> float:
        return p_level.get(node, _frozen_lv9)

    ctx = {
        'xp_rate': 1.0,   # XP_GOLD_RATE 用户裁定暂定 1:1(与 kernel 同值)
        'max_level_target': 9,
        'w_total': _w('refresh_total'), 'w_paid': _w('refresh_paid'),
        'w_sell': _w('sell_income'), 'w_buys5': _w('buys5'),
        'w_lu': _w('lu_clicks'), 'w_levelup': _w('levelup'),
        'w_m2cost2': _w('m2_cost2'), 'w_m3': _w('m3'),
        'cond_grants': _cond_grants, 'interest_delta': _interest_delta,
        'bosses_in_window': _bosses_in_window, 'p_level_at': _p_level_at,
    }

    # ---- 窗口参数申报 ----
    print('\n=== 窗口参数(逐节点先验 × 视界;点值,幸存者口径;'
          f'语料最大观测节点 = {_max_obs_node},尾段截断低估) ===')
    for k in sorted(horizons):
        h = horizons[k]
        start = _TOTAL_NODES - h
        row = {
            'E[总刷新]': _w('refresh_total')(start, h),
            'E[付费刷新]': _w('refresh_paid')(start, h),
            'E[卖出收入]': _w('sell_income')(start, h),
            'E[5费购]': _w('buys5')(start, h),
            'E[购经验击]': _w('lu_clicks')(start, h),
            'E[升级次数]': _w('levelup')(start, h),
            'E[2星2费合成]': _w('m2_cost2')(start, h),
            'E[3星合成]': _w('m3')(start, h),
            'E[充裕授予/窗]': _cond_grants(start, h),
            '息Δ(cap9)': _interest_delta(start, h, 9),
            '息Δ(cap10)': _interest_delta(start, h, 10),
            '息Δ(cap0)': _interest_delta(start, h, 0),
            'boss数': _bosses_in_window(start, h),
            'P(lv9@窗末)': _p_level_at(start + h),
        }
        fmt = {kk: (round(vv, 4) if isinstance(vv, float) else vv)
               for kk, vv in row.items()}
        print(f'  H={h}(start={start}): {fmt}')

    # ---- 品质子池 ----
    pools: dict[str, list] = {q: [] for q in _QUALITY_ORDER}
    for s in INVESTMENT_STRATEGIES.values():
        if s.rarity in pools:
            pools[s.rarity].append(s)
    print('\n=== 品质子池 ===')
    for q in _QUALITY_ORDER:
        print(f'  {q}: |S|={len(pools[q])}')
    pv_med: dict[str, float | None] = {}
    for q in _QUALITY_ORDER:
        vals = sorted(s.pick_value for s in pools[q] if s.pick_value > 0)
        pv_med[q] = statistics.median(vals) if vals else None
    print(f'  pick_value 非零中位序: {pv_med}(详设引 彩45/金35/银32)')

    def pool_card_values(h: int, restricted: bool) -> dict[str, list[float]]:
        """品质子池逐卡全通道值(μ 与成对差值 CI 共用的底层样本)。"""
        return {q: [econ_value_full(
            s.economy if s.economy is not None else EconomyEffect(),
            h, ctx, restricted) for s in pools[q]] for q in _QUALITY_ORDER}

    def diff_ci(vals_a: list[float], vals_b: list[float],
                seed: int = _BOOTSTRAP_SEED) -> tuple[float, float]:
        """成对差值 CI:两池独立重采样均差 percentile 95%(每对独立同种子,
        与验收复核脚本同方案,输出可交叉对拍;2000 次,种子 20260912)。"""
        rng = random.Random(seed)
        ds = sorted(sum(rng.choices(vals_a, k=len(vals_a))) / len(vals_a)
                    - sum(rng.choices(vals_b, k=len(vals_b))) / len(vals_b)
                    for _ in range(_BOOTSTRAP_N))
        lo_q = 0.5 * (1 - math.erf(_Z / math.sqrt(2)))
        return (ds[int(lo_q * (_BOOTSTRAP_N - 1))],
                ds[int((1 - lo_q) * (_BOOTSTRAP_N - 1))])

    def mu_table(restricted: bool,
                 horizons_local: dict[int, int]) -> dict:
        out: dict[tuple[str, int], tuple[float, tuple[float, float] | None, int]] = {}
        for k, h in sorted(horizons_local.items()):
            for q, vals in pool_card_values(h, restricted).items():
                mean = sum(vals) / len(vals) if vals else 0.0
                ci = bootstrap_mean_ci(vals, seed=_BOOTSTRAP_SEED + k)
                out[(q, h)] = (mean, ci, len(vals))
        return out

    # restricted 对拍(v1 八通道 @ H=24 参照)
    restr = mu_table(True, {1: _V1_H1_REF})
    print(f'\n=== restricted 对拍(v1 八通道 @ H={_V1_H1_REF};详设初测 '
          f'银3.31/金2.42/棱彩4.16) ===')
    for q in _QUALITY_ORDER:
        m, ci, n = restr[(q, _V1_H1_REF)]
        ci_s = f'({ci[0]:.4f}, {ci[1]:.4f})' if ci else 'None'
        print(f'  {q}: μ={m:.4f} ci={ci_s} n={n}')

    # ---- μ_E 全通道 ----
    full: dict[tuple[str, int], tuple[float, tuple[float, float] | None, int]] = {}
    if not horizons:
        print('\n=== μ_E 全通道 ===\n  无可注册视界(H_k 全部样本不足)→ '
              'STRAT_POOL_ECON_MEANS 不落')
    else:
        full = mu_table(False, horizons)
        print('\n=== μ_E 全通道 per (品质, H) ===')
        for (q, h), (m, ci, n) in sorted(full.items(),
                                         key=lambda kv: (kv[0][1], kv[0][0])):
            ci_s = f'({ci[0]:.4f}, {ci[1]:.4f})' if ci else 'None'
            print(f'  ({q!r}, {h}): value={m:.4f} ci={ci_s} n={n}')

        # ---- 序一致性检验(准入门第 2 条)----
        print('\n=== 序一致性检验(每 H:棱彩 > 金 > 银) ===')
        all_ok = True
        for h in sorted({h for _q, h in full}):
            mus = {q: full[(q, h)][0] for q in _QUALITY_ORDER}
            ok = mus['棱彩'] > mus['金'] > mus['银']
            all_ok = all_ok and ok
            print(f'  H={h}: 银 {mus["银"]:.4f} / 金 {mus["金"]:.4f} / '
                  f'棱彩 {mus["棱彩"]:.4f} → {"✅ 一致" if ok else "❌ 违序"}')
            # 成对差值 CI(统计辨析凭据,自本入口可复现;方案见 diff_ci)
            _vals = pool_card_values(h, False)
            for _a, _b in (('棱彩', '金'), ('金', '银'), ('棱彩', '银')):
                _lo, _hi = diff_ci(_vals[_a], _vals[_b])
                _verdict = ('显著>0' if _lo > 0
                            else ('显著<0' if _hi < 0 else '含 0(不可分辨)'))
                print(f'    μ({_a})−μ({_b}): [{_lo:+.4f}, {_hi:+.4f}] → {_verdict}')
        print(f'  pick_value 中位序辅助证据: {pv_med}')

    # ---- π_offer,k ----
    print('\n=== π_offer,k(全部帧行;归一 = 未解析按三品质摊入) ===')
    offer_counts = offer_quality_samples(records)
    for k in sorted(offer_counts):
        bucket = offer_counts[k]
        n_cards = sum(bucket.values())
        n_frames = n_cards / 3 if n_cards else 0
        known = {q: bucket.get(q, 0) for q in _QUALITY_ORDER}
        n_known = sum(known.values())
        unresolved = bucket.get('未解析', 0)
        ok = n_frames >= _MIN_PICK_SAMPLES
        print(f'  k={k}: 帧组≈{n_frames:.0f} 卡数={n_cards}(未解析 '
              f'{unresolved});注册门帧组≥{_MIN_PICK_SAMPLES} → '
              f'{"注册" if ok else "哨兵不落"}')
        if not ok or n_known == 0:
            continue
        norm = {q: known[q] / n_known for q in _QUALITY_ORDER}
        cis = {q: wilson_interval(known[q], n_known) for q in _QUALITY_ORDER}
        print('    归一: ' + '  '.join(
            f'{q}={norm[q]:.4f}[{cis[q][0]:.4f},{cis[q][1]:.4f}]'
            for q in _QUALITY_ORDER))

    print('\n=== 准入门判定(人工核对后落参;本脚本不回写源码) ===')
    print('  ① 全通道重算:见 μ_E 全通道表与窗口参数(排除集补参申报内嵌)')
    print('  ② 序一致性:见逐 H 判定;任一 H 违序 = 维持 fail-closed 回炉')


if __name__ == '__main__':
    main()
