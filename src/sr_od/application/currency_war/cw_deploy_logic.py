"""deploy 选人纯逻辑(sim 与 DeployBench op 共用单一源;r389/r390)。

背景(2026-08-23 用户定调「这些问题明明都可以模拟发现」):局53-62
实机暴露的 deploy 侧 bug(r373 桥期 target 真空/r387 cap 富余仍拦
散牌)全是 **DeployBench op 的选人围栏**行为——而 sim 的 deployed
是自动代理(bench 引擎件直进,围栏零覆盖),执行层 bug 天然测不出。

本模块把围栏判定提取为**纯函数**(无 ctx/无画面/无 SIFT):输入
bench/deployed/目标集/围栏集/cap,输出「谁上场」。DeployBench op
与 cw_sim 都调它——同一份逻辑,实机改=sim 改,漂移不可能。

⚠️ 漂移已对齐(ADR-0261 裁决「1+3 组合」落地,2026-08-24):
① DeployBench op `_deploy_deterministic` 排序已补 ignition_gain 首键
(经本模块 `ignition_gain`,与 select_deployments 同语义);② 本模块
select_deployments 已补 r288 配方底线门(列车≥2 且仙舟<3 → 列车件
让位留 bench,与 op 侧 r288 同语义)——sim 从此能测出「引擎件被配方
底线拦」形态(局64 姬子躺 bench 不再是 sim 盲区)。对齐后 op 与本
函数的行为差异只剩「读屏 vs 内存态」(op 的 SIFT 读身份/槽位坐标/
drag 验证留在 op)。

注意:op 侧还有画面依赖部分(SIFT 读身份/槽位坐标/drag 验证),
那些留在 op;这里只收**纯决策**。输入的 bench 用 BenchChar,
身份可判(char_id 空串=未识别,围栏语义「照旧上」保留)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_line_defs import (
    ENGINE_FACTIONS,
    RECIPE_BASE,
    RECIPE_FACTIONS,
)
from sr_od.application.currency_war.cw_state import BenchChar
from sr_od.application.currency_war.cw_system_cards import SYSTEM_CARDS


def _bonds_of(bc: BenchChar) -> set[str]:
    """角色全羁绊(factions+flows);未识别/未注册 → 空集。"""
    cid = getattr(bc, 'char_id', '') or ''
    ch = CHARACTERS.get(cid) if cid else None
    if ch is None:
        return set()
    return set(ch.factions) | set(ch.flows)

# 与 op 侧同源(r357:RECIPE ∪ ENGINE 桥派生集)
DEPLOY_FENCE: frozenset[str] = frozenset(RECIPE_FACTIONS | ENGINE_FACTIONS)


def cap_roomy_of(front_empty: int, back_empty: int, must_up: int) -> bool:
    """r387:cap 是否富余(空位 > 必上件数)。富余=散牌填空不稀释。"""
    return (front_empty + back_empty) > must_up


def tier_completes(bonds, deployed_fac: dict[str, int]) -> int:
    """r361 补档键:上阵后任一阵营恰达激活档 → 1,否则 0。"""
    from sr_od.application.currency_war.cw_factions import FACTIONS
    for _f in bonds:
        _now = (deployed_fac.get(_f, 0) or 0) + 1
        if _now in (FACTIONS.get(_f).tiers if FACTIONS.get(_f) else ()):
            return 1
    return 0


# r404-A1(四体系判据,与 cw_sim._TRANSITION_TRAITS 同语义;此模块
# 不 import cw_sim——sim 消费本模块,反向 import 成环——sim 侧改为
# alias import 本常量,两边不再各写一份)。
# W47 统一化:三羁绊(阵营, 阈值)对改从 SYSTEM_CARDS 派生(排除 seele 卡
# ——希儿系是 deployed 单卡判定非阵营计数,deploy 排序/形态维无意义,
# 见 ignition_gain 注);tier 阈值经 FACTIONS 注册表,单一源。
TRANSITION_TRAITS: tuple[tuple[str, int], ...] = tuple(
    (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
    for card in SYSTEM_CARDS.values() if card.card_id != 'seele'
)


def ignition_gain(bonds, deployed_fac: dict[str, int]) -> int:
    """r404-A1 点火增量:该角色上阵后「过渡体系达成数」的增量。

    体系=仙舟3/列车2/DOT2(transition_combos.md 四体系的三羁绊
    部分;希儿系在 deploy 排序无意义——希儿本人是 target 件)。
    增量>0 = 这张是「恰好点火」件(第 tier 人);优先级最高的
    上场候选——60 局 r6 归因:未成型局 44% =「差1人·bench有货
    未上」,根因是 r251 排序只看阵营身份不看点火(冗余第4仙舟
    挤掉点火列车2,探针实证)。
    """

    def _sys_count(fac: dict[str, int]) -> int:
        return sum(1 for bond, tier in TRANSITION_TRAITS
                   if fac.get(bond, 0) >= tier)

    after = dict(deployed_fac)
    for f in bonds:
        after[f] = after.get(f, 0) + 1
    return _sys_count(after) - _sys_count(deployed_fac)


def select_deployments(
    bench: list[BenchChar],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[int], list[int]]:
    """围栏判定:返回 (上场 bench 下标序, 留 bench 下标)。

    语义与 DeployBench op 的 deterministic 段逐条对应
    (ADR-0130 散牌围栏/r361 补档序/r251 引擎对优先/r387 cap 富余
    填空/r404-A1 点火首键+桶序/r288 配方底线门/板空保底),唯一省略:
    SIFT 未识别(char_id 空)照旧上
    ——调用方传空 char_id 即走该分支。
    cap 语义 = 已 deployed 数 + 本轮上场数 ≤ cap(cap=None 不限,
    调用方传大数)。
    """
    vacancy = front_total + back_total - len(deployed_cids)
    vacancy = max(vacancy, 0)

    tgt_idx: list[int] = []
    rest: list[int] = []
    bench_fac: dict[int, str] = {}
    pair_counts: dict[str, int] = dict(board)
    for i, bc in enumerate(bench):
        cid = getattr(bc, 'char_id', '') or ''
        ch = CHARACTERS.get(cid) if cid else None
        bonds: set[str] = set()
        if ch is not None:
            bonds = set(ch.factions) | set(ch.flows)
            if ch.factions:
                bench_fac[i] = ch.factions[0]
                pair_counts[ch.factions[0]] = pair_counts.get(ch.factions[0], 0) + 1
        is_tgt = bool(bonds & set(target_factions)) or cid in target_cores \
            or cid in fw_carry
        (tgt_idx if is_tgt else rest).append(i)
    # r404-A1:tgt 初始序也按点火首键(围栏前的序影响 cap 竞争时
    # 谁先上;旧版纯 tier_completes)
    tgt_idx.sort(key=lambda i: (
        -ignition_gain(_bonds_of(bench[i]), deployed_fac),
        -tier_completes(_bonds_of(bench[i]), deployed_fac)))

    held: list[int] = []
    fill_mode = vacancy > 2
    board_recipe = sum(v for k, v in board.items() if k in RECIPE_FACTIONS)
    recipe_starved = board_recipe < RECIPE_BASE
    must_up = len(tgt_idx) + sum(
        1 for i in rest
        if bench_fac.get(i) is not None
        and pair_counts.get(bench_fac[i], 0) >= 2)
    roomy = cap_roomy_of(vacancy, 0, must_up)
    for i in list(rest):
        cid = getattr(bench[i], 'char_id', '') or ''
        if not cid:
            continue    # 未识别:照旧上(围栏无法判)
        f = bench_fac.get(i)
        # [31] 凑档降级(部署侧;ADR-0288):无目标件可上(tgt 空)时,
        # 凑档件——board∪bench 主阵营计数 ≥2(含自身 = board 已有
        # ≥1,入后凑 2 档)——不被配方围栏拦:降级上场「有总比没有
        # 厉害」(P3:e0→e1 +1.4 金/轮);tgt 空集时不存在挤占目标件
        # 位置的问题(tgt 非空时围栏照旧——降级件不挤目标件)。
        _bond_paired = f is not None and pair_counts.get(f, 0) >= 2
        if f is not None and f not in DEPLOY_FENCE \
                and recipe_starved and not roomy \
                and not (not tgt_idx and _bond_paired):
            rest.remove(i)
            held.append(i)
            continue
        if f is not None and pair_counts.get(f, 0) >= 2:
            continue    # 成对:上
        if fill_mode:
            continue    # 人口扩展期:散牌填位
        rest.remove(i)
        held.append(i)
    board_empty = len(deployed_cids) == 0
    if board_empty and not tgt_idx and not rest and held:
        rest.append(held.pop(0))   # 板空保底:上 1 个
    # r404-A1:点火增量首键——「恰好让某体系凑满 tier 的那张」
    # 排最前(冗余件/无关件让位)。r251 引擎身份键降为次键
    # (探针实证:vacancy=1 时冗余第4仙舟曾挤掉点火列车2)。
    _ENGINE = {'仙舟', '列车同行', '持续伤害'}
    rest.sort(key=lambda i: (
        -ignition_gain(_bonds_of(bench[i]), deployed_fac),
        0 if (bench_fac.get(i) in _ENGINE or
              _bonds_of(bench[i]) & _ENGINE) else 1))
    # r404-A1:桶序修正——tgt 全体压 rest 的旧序会让「冗余 tgt 件」
    # 挤掉「点火 rest 件」(探针④:第4仙舟压点火三月七)。点火增量
    # >0 的 rest 件先于 ignition=0 的 tgt 件上场(点火=四体系成型
    # 的关键跳变,语义高于 target 身份;tgt 内部序已按点火排)。
    ignite_rest = [i for i in rest
                   if ignition_gain(_bonds_of(bench[i]), deployed_fac) > 0]
    plain_rest = [i for i in rest if i not in ignite_rest]
    order = ignite_rest + tgt_idx + plain_rest
    # cap 截断(动态停语义:超 cap 的留 bench)
    # r404-A2:同名去重(5.1.7 不变量:同角色在场只 1)扩到
    # **本轮已上名单**——旧版只查传入 deployed_cids(实机=开局
    # 一次读取/sim=恒空集),本轮内第二张同名(cid 不在 deployed_
    # cids)照样上——60 局实证 40 局「重复件占位」的直接机制
    # (爻光×3 同场=第2张起对体系零增益白占 cap)。3合1 素材
    # 留 bench(r383b 囤件语义不受影响:囤的是 bench 不是上场)。
    up: list[int] = []
    _up_names: set[str] = set()
    # r288 配方底线门(ADR-0261 裁决选项3,与 deploy_bench op 同语义):
    # 列车≥2 且仙舟<3 → 列车件让位留 bench(仙舟基础线优先,防列车
    # 第 3 人挤占配方深度;局23/24 实锤的既定配方纪律)。op 侧在 drag
    # 循环内逐件动态仲裁(每次成功上场同步阵营档);此处用 running
    # 副本 `_fac_run` 等价模拟(ADR-0261 裁决修订2:**循环内逐件增量
    # 维护**,每上一件按全羁绊 r363b 口径 +1,不得用入参初始快照——
    # 否则门系统性偏松)。门判定的阵营口径 = bench_fac(主阵营),与
    # op 的 _bench_fac 同源。
    # 修订3(单一源):门的 2/3 档数值**从 TRANSITION_TRAITS 派生**
    # (列车2/仙舟3 = 过渡体系 tier,同一批数字)——不造第三处硬编码;
    # op 侧 r288 的历史硬编码点已同步改为本派生引用。
    _tier_of = dict(TRANSITION_TRAITS)
    _train_cap = _tier_of.get('列车同行', 2)
    _xz_base = _tier_of.get('仙舟', 3)
    _fac_run = dict(deployed_fac)
    for i in order:
        if len(deployed_cids) + len(up) >= cap:
            held.append(i)
            continue
        cid = getattr(bench[i], 'char_id', '') or ''
        if cid and (cid in deployed_cids or cid in _up_names):
            held.append(i)   # 去重(5.1.7,含本轮已上):留 bench
            continue
        if bench_fac.get(i) == '列车同行' \
                and _fac_run.get('列车同行', 0) >= _train_cap \
                and _fac_run.get('仙舟', 0) < _xz_base:
            held.append(i)   # r288:列车件让位(仙舟基础线优先)
            continue
        up.append(i)
        if cid:
            _up_names.add(cid)
        for f in _bonds_of(bench[i]):
            _fac_run[f] = _fac_run.get(f, 0) + 1
    return up, held
