"""deploy 选人纯逻辑(sim 与 CwOpDeploy op 共用单一源)。

背景(用户定调「这些问题明明都可以模拟发现」):实机暴露的
deploy 侧 bug(桥期 target 真空/cap 富余仍拦
散牌)全是 **CwOpDeploy op 的选人围栏**行为——而 sim 的 deployed
是自动代理(bench 引擎件直进,围栏零覆盖),执行层 bug 天然测不出。

本模块把围栏判定提取为**纯函数**(无 ctx/无画面/无 SIFT):输入
bench/deployed/目标集/围栏集/cap,输出「谁上场」。CwOpDeploy op
与 cw_sim 都调它——同一份逻辑,实机改=sim 改,漂移不可能。

⚠️ 对齐语义(ADR-0261 裁决「1+3 组合」):
① CwOpDeploy op `_deploy_deterministic` 排序含 ignition_gain 首键
(经本模块 `ignition_gain`,与 select_deployments 同语义);② 本模块
select_deployments 含配方底线门(列车≥2 且仙舟<3 → 列车件
让位留 bench,与 op 侧同语义)。对齐后 op 与本
函数的行为差异只剩「读屏 vs 内存态」(op 的 SIFT 读身份/槽位坐标/
drag 验证留在 op)。

这里只收**纯决策**。输入的 bench 用 BenchChar,
身份可判(char_id 空串=未识别,围栏语义「照旧上」保留)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS,
    RECIPE_BASE,
    RECIPE_FACTIONS,
)
from sr_od.application.currency_war.kernel.cw_state import (
    DEPLOYED_BACK_CAPACITY,
    DEPLOYED_FRONT_CAPACITY,
    BenchChar,
    GameState,
    deployed_occupied,
)
from sr_od.application.currency_war.kernel.cw_system_cards import SYSTEM_CARDS


def _bonds_of(bc: BenchChar) -> set[str]:
    """角色全羁绊(factions+flows);未识别/未注册 → 空集。"""
    cid = getattr(bc, 'char_id', '') or ''
    ch = CHARACTERS.get(cid) if cid else None
    if ch is None:
        return set()
    return set(ch.factions) | set(ch.flows)

# 与 op 侧同源(RECIPE ∪ ENGINE 桥派生集)
DEPLOY_FENCE: frozenset[str] = frozenset(RECIPE_FACTIONS | ENGINE_FACTIONS)


def cap_roomy_of(front_empty: int, back_empty: int, must_up: int) -> bool:
    """cap 是否富余(空位 > 必上件数)。富余=散牌填空不稀释。"""
    return (front_empty + back_empty) > must_up


def tier_completes(bonds, deployed_fac: dict[str, int]) -> int:
    """补档键:上阵后任一阵营恰达激活档 → 1,否则 0。"""
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    for _f in bonds:
        _now = (deployed_fac.get(_f, 0) or 0) + 1
        if _now in (FACTIONS.get(_f).tiers if FACTIONS.get(_f) else ()):
            return 1
    return 0


# 四体系判据(与 cw_sim._TRANSITION_TRAITS 同语义;此模块
# 不 import cw_sim——sim 消费本模块,反向 import 成环——sim 侧改为
# alias import 本常量,两边不再各写一份)。
# 三羁绊(阵营, 阈值)对从 SYSTEM_CARDS 派生(排除 seele 卡
# ——希儿系是 deployed 单卡判定非阵营计数,deploy 排序/形态维无意义,
# 见 ignition_gain 注);tier 阈值经 FACTIONS 注册表,单一源。
# ⚠️ 迁移挂账(docs/develop/currency_war/archive/redesign/03_legacy_cleanup_plan.md):
# 权威副本 = knowledge/cw_engine_facts.TRANSITION_TRAITS(同派生式,零字面双源);
# 本副本仅为 sim/旧判据未迁消费点保留,按该计划随文件删除;勿新增消费。
TRANSITION_TRAITS: tuple[tuple[str, int], ...] = tuple(
    (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
    for card in SYSTEM_CARDS.values() if card.card_id != 'seele'
)


# ADR-0375 守卫辖域体系集:四过渡体系全辖(三羁绊 + 希儿系
# 单卡判据,tier=1)。辖域语义与 TRANSITION_TRAITS 的 deploy 排序语义
# **分离**——后者是阵营计数排序维(希儿系单卡判定在 deploy 维无意义,
# 故排除,历史理由保留),但 ADR-0373 卖侧守卫/ADR-0371 保护集借用
# 该常量后「四体系」声称只剩三羁绊辖域(实机巡检发现的辖域漂移)。守卫/
# 保护类消费改用本集,不再借 TRANSITION_TRAITS(一常量两语义的根修)。
SEELE_SYSTEM_KEY: str = '希儿系'
#: 希儿系放大器阵营(量子/贝——伤害在希儿技能层,放大器非独立伤害源,
#: transition_combos.md 四体系表;桑博=贝+DOT 双籍是常态不是边界)
SEELE_AMP_FACTIONS: frozenset[str] = frozenset({'量子同频', '贝洛伯格'})
#: 守卫辖域体系集(GUARD_SYSTEM_TIERS 的本体:三羁绊 + 希儿系 tier=1)
GUARD_SYSTEM_TIERS: tuple[tuple[str, int], ...] = (
    TRANSITION_TRAITS + ((SEELE_SYSTEM_KEY, 1),))


def engines_count(board_factions: dict[str, int],
                  deployed_names: frozenset[str] | set[str] = frozenset()
                  ) -> int:
    """过渡体系达成数(由 cw_battle_calib._engines_count 上移而来的**单一源**;
    cw_sim 侧保留同名薄委托,checks 模块经本模块消费——检查网不
    import cw_sim 的架构锁由依赖方向保证)。

    四体系:仙舟3/列车2/DOT2(TRANSITION_TRAITS 阈值)+ 希儿系
    (希儿在场 ∧ 放大器≥2)。两两组合=过渡成型。
    """
    n = sum(1 for bond, tier in TRANSITION_TRAITS
            if board_factions.get(bond, 0) >= tier)
    seele = ('希儿' in deployed_names
             and (board_factions.get('量子同频', 0) >= 2
                  or board_factions.get('贝洛伯格', 0) >= 2))
    if seele:
        n += 1
    return n


def is_seele_system_member(char_id: str, bonds: set[str]) -> bool:
    """希儿系贡献件判据(单卡 + 放大器;守卫/保护辖域口径,ADR-0375)。

    希儿本人(单卡)+ 量子同频/贝洛伯格放大器件——与 cw_evolution.
    _engine_systems_formed/_contributes_engine_system/_is_member 的
    希儿系分支同口径(此前已有单卡判据先例,此处提为单一源函数)。
    tier=1:希儿系作为四过渡体系之一的档(user_playstyle 四体系封闭
    裁定,transitions.md;希儿系引擎=希儿在场 ∧ 放大器 ≥2,但**恢复
    种子**的辖域口径取贡献件全计——清空任意最后一件贡献件都使该体系
    归零,owned 计数含希儿与全部放大器件)。
    """
    return char_id == '希儿' or bool(bonds & SEELE_AMP_FACTIONS)


def ignition_gain(bonds, deployed_fac: dict[str, int]) -> int:
    """点火增量:该角色上阵后「过渡体系达成数」的增量。

    体系=仙舟3/列车2/DOT2(transition_combos.md 四体系的三羁绊
    部分;希儿系在 deploy 排序无意义——希儿本人是 target 件)。
    增量>0 = 这张是「恰好点火」件(第 tier 人);优先级最高的
    上场候选——60 局归因:未成型局 44% =「差1人·bench有货
    未上」,根因是旧排序只看阵营身份不看点火(冗余第4仙舟
    挤掉点火列车2,探针实证)。
    """

    def _sys_count(fac: dict[str, int]) -> int:
        return sum(1 for bond, tier in TRANSITION_TRAITS
                   if fac.get(bond, 0) >= tier)

    after = dict(deployed_fac)
    for f in bonds:
        after[f] = after.get(f, 0) + 1
    return _sys_count(after) - _sys_count(deployed_fac)


def has_deployable(
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
    locked_factions: frozenset[str] | set[str] = frozenset(),
) -> bool:
    """「是否存在可部署件」的单一源谓词(dd-037)。

    = ``bool(select_deployments(...)[0])``——发射方(决策核准备战段)与
    执行方(CwOpDeploy)共用同一份围栏/去重/cap/配方底线语义判「还有没有
    部署可做」。背景(run 20260904_28xx 局11 停机形态):发射方判「bench
    有货该部署」、执行方按配方底线规则把该件留 bench → RunDeploy 空计划
    被包装成 ✓「已部署角色」→ 同签名动作批零推进环,环级无进展守卫停机。
    修后发射方在计划为空时不发射 RunDeploy(bench=1 是合法稳态)。

    语义口径与 ``select_deployments`` 完全一致(含 SIFT 未识别 char_id=''
    「照旧上」的 fail-open:身份不可判时恒 True,不做激进留 bench)。
    """
    up, _held = select_deployments(
        bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total, back_total=back_total,
        target_factions=target_factions, target_cores=target_cores,
        fw_carry=fw_carry, locked_factions=locked_factions)
    return bool(up)


def deployed_bond_counts(deployed_cids: set[str]) -> dict[str, int]:
    """已上场角色全羁绊计数(factions+flows 逐项 +1;r361b 全羁绊口径)。

    消费面 = ``has_deployable`` 发射侧装配与 CwOpDeploy 执行侧的
    ``_deployed_fac``(两侧计数同循环同口径,单一源;未注册名不计
    ——无名可判即无阵营信号,件本身的去重/fail-open 由
    select_deployments 的 cid 分支管)。
    """
    out: dict[str, int] = {}
    for cid in deployed_cids:
        ch = CHARACTERS.get(cid) if cid else None
        if ch is None:
            continue
        for f in tuple(ch.factions or ()) + tuple(ch.flows or ()):
            out[f] = out.get(f, 0) + 1
    return out


def deploy_target_sets(target_comp: object | None,
                       transition_framework: str = '',
                       ) -> tuple[set[str], set[str]]:
    """deploy 围栏 target 集装配(r70 双轨口径单一源)。

    返回 ``(target_factions, fw_carry)``:comp 阵营 ∪ 过渡框架阵营;
    fw_carry = 框架(或通用)非 drop 件(先框架非 drop + 通用 carry,
    散件 drop 不认)。消费面 = CwOpDeploy 执行侧与 mandate 发射侧
    ``select_deployments``/``has_deployable`` 的同参装配——发射侧
    抑制谓词(dd-037)接线后两侧各写一份即双源,禁复制。
    """
    tgt = set(getattr(target_comp, 'factions', None) or ())
    fw = transition_framework or ''
    fw_carry: set[str] = set()
    if fw:
        from sr_od.application.currency_war.kernel.cw_transition import (
            FRAMEWORK_FACTIONS,
            TRANSITION_PACK,
        )
        tgt |= set(FRAMEWORK_FACTIONS.get(fw, ()))
        fw_carry = {n for n, (f, t) in TRANSITION_PACK.items()
                    if (f == fw or f == '通用') and t != 'drop'}
    return tgt, fw_carry


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
    locked_factions: frozenset[str] | set[str] = frozenset(),
    reasons_out: dict[int, str] | None = None,
) -> tuple[list[int], list[int]]:
    """围栏判定:返回 (上场 bench 下标序, 留 bench 下标)。

    语义与 CwOpDeploy op 的 deterministic 段逐条对应
    (ADR-0130 散牌围栏/补档序/引擎对优先/cap 富余
    填空/点火首键+桶序/配方底线门/板空保底),唯一省略:
    SIFT 未识别(char_id 空)照旧上
    ——调用方传空 char_id 即走该分支。
    cap 语义 = 已 deployed 数 + 本轮上场数 ≤ cap(cap=None 不限,
    调用方传大数)。

    ADR-0360 件4(deploy 围栏兜底,ADR-0226 同型扩位):
    ``locked_factions`` = 锁定帧体系键(``cw_intention.locked_faction_
    scope``)并入围栏放行集——锁定 comp 的阵营(欢愉/公司等非 RECIPE ∪
    ENGINE 阵营)不再被配方围栏摁 bench(strict 局挤出后 59% 不回
    场,围栏是回场路径;锁定目标件保护,空窗期无锁定帧不辖)。

    **held 拒因返回(N2 规格单一源,17 号稿 §7.1)**:传 ``reasons_out``
    dict 时,held 下标 → 拒因('scatter_fence' 散牌围栏/'rest_capacity'
    人口非扩展留置/'cap'/'name_dup' 同名去重/'recipe_floor' 配方底线门)
    逐项写入——held 判定语义单一源在本函数,消费面(出口③围栏预检/
    部署执行侧闭环分键)禁第二套围栏语义;带 reason 消费走
    ``select_deployments_reasoned``。
    """
    reasons: dict[int, str] = {}
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
    # tgt 初始序也按点火首键(围栏前的序影响 cap 竞争时
    # 谁先上)
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
        # 凑档降级(部署侧;ADR-0288):无目标件可上(tgt 空)时,
        # 凑档件——board∪bench 主阵营计数 ≥2(含自身 = board 已有
        # ≥1,入后凑 2 档)——不被配方围栏拦:降级上场「有总比没有
        # 厉害」(P3:e0→e1 +1.4 金/轮);tgt 空集时不存在挤占目标件
        # 位置的问题(tgt 非空时围栏照旧——降级件不挤目标件)。
        _bond_paired = f is not None and pair_counts.get(f, 0) >= 2
        # ADR-0360 件4:锁定帧体系键(常为流派键——燃血/欢愉等,
        # 而围栏基准键=主阵营)按**全羁绊**匹配放行;未传锁定帧时
        # `not (... & 空)` 恒 True,围栏行为与旧版逐位一致
        if f is not None and f not in DEPLOY_FENCE \
                and not (_bonds_of(bench[i]) & set(locked_factions)) \
                and recipe_starved and not roomy \
                and not (not tgt_idx and _bond_paired):
            rest.remove(i)
            held.append(i)
            reasons[i] = 'scatter_fence'
            continue
        if f is not None and pair_counts.get(f, 0) >= 2:
            continue    # 成对:上
        if fill_mode:
            continue    # 人口扩展期:散牌填位
        rest.remove(i)
        held.append(i)
        reasons[i] = 'rest_capacity'
    board_empty = len(deployed_cids) == 0
    if board_empty and not tgt_idx and not rest and held:
        first = held.pop(0)
        reasons.pop(first, None)   # 板空保底:上 1 个(拒因随之消除)
        rest.append(first)
    # 点火增量首键——「恰好让某体系凑满 tier 的那张」
    # 排最前(冗余件/无关件让位)。引擎身份键降为次键
    # (探针实证:vacancy=1 时冗余第4仙舟曾挤掉点火列车2)。
    _ENGINE = {'仙舟', '列车同行', '持续伤害'}
    rest.sort(key=lambda i: (
        -ignition_gain(_bonds_of(bench[i]), deployed_fac),
        0 if (bench_fac.get(i) in _ENGINE or
              _bonds_of(bench[i]) & _ENGINE) else 1))
    # 桶序修正——tgt 全体压 rest 的旧序会让「冗余 tgt 件」
    # 挤掉「点火 rest 件」(探针④:第4仙舟压点火三月七)。点火增量
    # >0 的 rest 件先于 ignition=0 的 tgt 件上场(点火=四体系成型
    # 的关键跳变,语义高于 target 身份;tgt 内部序已按点火排)。
    ignite_rest = [i for i in rest
                   if ignition_gain(_bonds_of(bench[i]), deployed_fac) > 0]
    plain_rest = [i for i in rest if i not in ignite_rest]
    # 锁定线核心优先桶(ADR-0323):意向锁定的线核心优先于过渡填充件——tgt 中
    # target_cores 成员(锁定 comp 的 core_chars;sim/candidates 从
    # session.target_comp 注入)提到最前,「同 cap 内先核心后填充」
    # (变阵窗口语义:锁定线核心在窗口优先上板;对照语义:过渡配方
    # 照常占位,但核心不因 cap 竞争被填充件挤掉;不扩 cap)。
    # 非锁定局 target_cores 空 → 本桶恒空,序不变;「点火 >
    # 冗余 target」语义保留(core_tgt 之外的 tgt 仍在 ignite_rest 之后)。
    _core_set = set(target_cores)
    core_tgt = [i for i in tgt_idx
                if (getattr(bench[i], 'char_id', '') or '') in _core_set]
    other_tgt = [i for i in tgt_idx if i not in core_tgt]
    order = core_tgt + ignite_rest + other_tgt + plain_rest
    # cap 截断(动态停语义:超 cap 的留 bench)
    # 同名去重(5.1.7 不变量:同角色在场只 1)扩到
    # **本轮已上名单**——传入 deployed_cids 在实机=开局
    # 一次读取/sim=恒空集,只查它拦不住本轮内第二张同名
    # (cid 不在 deployed_cids)——60 局实证 40 局「重复件占位」的直接机制
    # (爻光×3 同场=第2张起对体系零增益白占 cap)。3合1 素材
    # 留 bench(囤件语义不受影响:囤的是 bench 不是上场)。
    up: list[int] = []
    _up_names: set[str] = set()
    # 配方底线门(ADR-0261 裁决选项3,与 deploy_bench op 同语义):
    # 列车≥2 且仙舟<3 → 列车件让位留 bench(仙舟基础线优先,防列车
    # 第 3 人挤占配方深度;实机实锤的既定配方纪律)。op 侧在 drag
    # 循环内逐件动态仲裁(每次成功上场同步阵营档);此处用 running
    # 副本 `_fac_run` 等价模拟(ADR-0261 裁决:**循环内逐件增量
    # 维护**,每上一件按全羁绊口径 +1,不得用入参初始快照——
    # 否则门系统性偏松)。门判定的阵营口径 = bench_fac(主阵营),与
    # op 的 _bench_fac 同源。
    # 门 2/3 档数值从 TRANSITION_TRAITS 派生
    # (列车2/仙舟3 = 过渡体系 tier,同一批数字)——不造第三处硬编码,
    # op 侧同源引用。
    _tier_of = dict(TRANSITION_TRAITS)
    _train_cap = _tier_of.get('列车同行', 2)
    _xz_base = _tier_of.get('仙舟', 3)
    _fac_run = dict(deployed_fac)
    for i in order:
        if len(deployed_cids) + len(up) >= cap:
            held.append(i)
            reasons[i] = 'cap'
            continue
        cid = getattr(bench[i], 'char_id', '') or ''
        if cid and (cid in deployed_cids or cid in _up_names):
            held.append(i)   # 去重(5.1.7,含本轮已上):留 bench
            reasons[i] = 'name_dup'
            continue
        if bench_fac.get(i) == '列车同行' \
                and _fac_run.get('列车同行', 0) >= _train_cap \
                and _fac_run.get('仙舟', 0) < _xz_base:
            held.append(i)   # 配方底线门:列车件让位(仙舟基础线优先)
            reasons[i] = 'recipe_floor'
            continue
        up.append(i)
        if cid:
            _up_names.add(cid)
        for f in _bonds_of(bench[i]):
            _fac_run[f] = _fac_run.get(f, 0) + 1
    if reasons_out is not None:
        reasons_out.update(reasons)
    return up, held


def select_deployments_reasoned(
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
    locked_factions: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[int], list[int], dict[int, str]]:
    """N2 规格①:select_deployments 的带拒因形态(单一源同函数路径)。

    返回 ``(up, held, reasons)``——reasons = held 下标 → 拒因
    ('scatter_fence'/'rest_capacity'/'cap'/'name_dup'/'recipe_floor')。
    消费面 = 出口③围栏预检(17 号稿 §7.1)与部署执行侧闭环分键
    (fuel_filler_stall_held_postbuy);预检/分键禁第二套围栏语义。
    """
    reasons: dict[int, str] = {}
    up, held = select_deployments(
        bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total,
        back_total=back_total, target_factions=target_factions,
        target_cores=target_cores, fw_carry=fw_carry,
        locked_factions=locked_factions, reasons_out=reasons)
    return up, held, reasons


def can_deploy_single(
    candidate: BenchChar,
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
    locked_factions: frozenset[str] | set[str] = frozenset(),
) -> tuple[bool, str]:
    """N2 规格②:单件假想查询(17 号稿 §7.1)。

    输入 = 候选件 + 假想 bench/板面快照(现有 bench 追加 candidate,
    其余量传当前真实快照),输出 = (可落板, 拒因);拒因口径 =
    ``select_deployments_reasoned``(scatter_fence/rest_capacity/cap/
    name_dup/recipe_floor)。出口③围栏放行预检**只消费本 API**,
    禁发射面自算第二套围栏语义。查询不可得(快照缺失/语义冲突)由
    调用方按 ``precheck_unavailable`` 分键处理(与围栏拒 'fenced' 禁
    混键,17 号稿 §7.1 fail 向)。
    """
    bench2 = list(bench) + [candidate]
    idx = len(bench2) - 1
    up, _held, reasons = select_deployments_reasoned(
        bench2, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total,
        back_total=back_total, target_factions=target_factions,
        target_cores=target_cores, fw_carry=fw_carry,
        locked_factions=locked_factions)
    if idx in up:
        return True, ''
    # 缺省 'unannotated' 显影(策略审查二十三跳必改项):候选 held 而拒因
    # 字典无标注 = 未来新增 hold 路径漏标拒因的缺口形态——不冒名 'cap',
    # 显影回炉标注(既有五拒因调用面零变化)。
    return False, reasons.get(idx, 'unannotated')


# ===== 换阵卖出义务臂(自 cw_op_deploy 迁 kernel;单一源收口)=====
# 为什么迁 kernel:swap 发射面谓词(select_swap_plan,本文件尾)与执行侧
# 卖出臂共吃同一 fenced 臂判据——判据驻 operations 桶时 kernel 谓词够不着
# (包依赖矩阵禁 kernel→operations),自写 fp/板满组合 = 第三源(先例:
# cw_launch_admission.py DEPLOY_FENCE 注释,r271 批同型双源清退)。
# cw_op_deploy 保留同名 re-export,既有消费路径(生产 deploy 卖出臂/锁
# 测试)零迁移。

def swap_arm_deployed_count(board: dict | None,
                            tracked_deployed: list) -> int:
    """换阵卖出义务臂「板满」条件的部署数喂入(单一口径)。

    = 占用槽位表计数(``cw_state.deployed_occupied``,数据源 =
    reconcile_tracking 的 SIFT 真读槽位表)。**禁用
    ``sum(board.values())``**:board 语义 = 阵营名 → 该阵营在场人数
    (一人多阵营贡献多次,4 人可贡献 11 阵营次)——把羁绊计数当部署数
    喂「板满」门 = 建模对象错,板未满即开臂、熔断自线成型起事实失效。
    """
    return deployed_occupied(tracked_deployed or [])


def fenced_swap_arm_of(fp: float, deployed_n: int, cap: int | None) -> bool:
    """换阵卖出义务臂触发判据(纯函数,锁测试面):线成型(fp≥1.00,
    单一源 ``cw_comps.form_progress``)∧ 板满(占用数 ≥ cap——cap =
    可上阵数占用数口径,与 select_swap_plan 板满门同一派生链
    ``GameState.max_units``(level+宝钻、封顶 DEPLOYED_CAPACITY),
    喂入单一源 = ``swap_arm_deployed_count``)。两条件并存 =
    熔断的振荡防护前提(买/演进层仍要 fenced 件)消失、且 bench target
    无空槽可进——此时 off-line fenced 件让位。

    口径裁决(REVISION_R2 同根双源收口):板满门禁用物理槽位总数
    (front+back=10)——XP_TO_NEXT_LEVEL 键域 3..9 ⇒ level≤9 ⇒
    level 驱动 cap 全域 <10,物理门恒不可达 ⇒ 臂全游戏恒死;cap
    缺读(None/≤0)= 臂关(fail-closed,与谓词 cap_unreadable 同向)。
    """
    if fp < 1.0 or not cap or cap <= 0:
        return False
    return deployed_n >= cap


# ===== 板满换阵补部署计划(M1″ 发射面谓词;与 select_deployments 同族)=====
# 语义出处:ADR-0530(board-full swap redeploy)。
# 结构:发射侧(mandate M1″)与执行侧(CwOpDeploy 卖出臂)**同函数、
# 同一装配契约**(assemble_swap_plan_inputs),但输入源两侧分轨——发射
# = 决策帧黑板,执行 = last_state + SIFT(装配源契约钉死为执行侧卖出
# 决策实际消费的快照链,禁另起第三路);两侧输入的逐字段对齐由 seam
# 核对批兑现(cw4_m1p_seam_verified 唯一写点),对齐证据是开闸前置
# 义务——「同谓词 ∧ 同输入快照 ⇒ 发射⇔执行可开出卖序」是条件式不变式
# (ADR-0530)。
# 拒因键(闭集):cap_unreadable / membership_unreadable / input_missing
# (弃权三键,计划空)+ 逐件拒因 fenced_arm_closed / target_keep /
# protected / buy_membership / fresh_buy / post_sell_held。

#: 轮内新鲜度排除载体(session 属性名):发射位买入时逐名写入的名集,
#: 键式 = {'phase': (plane, round_num), 'names': set[str]}——位面/轮次
#: 推进自动失效(M7 闩键式同构)。⚠️ 写点现状(三审 C1 勘误):当前仅
#: sim/engine_p1 决策帧接线,生产买入发射位(shop.py)写点候 M1″ 开闸
#: 小批补接(ADR-0530 挂账)——实机侧防抖在此前不生效,失真经 fresh_buy
#: 拒因不可追溯(与 sim 侧不对称,开闸前置义务)。取舍声明:沿用发射位
#: 写入(与 ``cw4_fuel_filler_stall_buys`` 先例同位),被截断器丢弃的买入
#: 意图也入排除集 = 过度排除压制合法 swap,方向安全(留置合法稳态,
#: dd-037 口径),失真经 fresh_buy 拒因可追溯;单调性由义务集排除独立
#: 承载,本载体只承担防抖+显影(拒因照记,不宣称切环)。
SWAP_FRESH_BUYS_ATTR: str = 'cw4_swap_fresh_buys'


def record_fresh_buy(session: object, state: GameState | None,
                     name: str) -> None:
    """轮内新鲜度排除登记(买入意图逐名写入;发射位调用)。

    同一发射批的多个买入意图**逐名**入集(防批量买入漏记——漏记 =
    卖出环切不断,防抖失效静默)。键式见 ``SWAP_FRESH_BUYS_ATTR``。
    """
    if not name:
        return
    reg = getattr(session, SWAP_FRESH_BUYS_ATTR, None)
    phase = (getattr(state, 'plane', None),
             getattr(state, 'round_num', 1))
    if not isinstance(reg, dict) or reg.get('phase') != phase:
        reg = {'phase': phase, 'names': set()}
        setattr(session, SWAP_FRESH_BUYS_ATTR, reg)
    reg['names'].add(name)


def fresh_buys_of(session: object,
                  state: GameState | None) -> frozenset[str]:
    """读当前位面轮内有效的新鲜买入名集(跨轮 = 空集,自动失效)。"""
    reg = getattr(session, SWAP_FRESH_BUYS_ATTR, None)
    if not isinstance(reg, dict):
        return frozenset()
    phase = (getattr(state, 'plane', None),
             getattr(state, 'round_num', 1))
    if reg.get('phase') != phase:
        return frozenset()
    names = reg.get('names')
    return frozenset(names) if isinstance(names, set) else frozenset()


def swap_sell_exclusion_reason(name: str, ctx: SwapPlanContext | None,
                               ) -> str:
    """卖出 victim 义务集∪新鲜度排除的单一判定(ADR-0530)。

    消费面 = 发射面谓词(select_swap_plan)与执行侧卖出臂(CwOpDeploy
    `_sell_offtarget_deployed`)——卖出通道统一义务集排除辖域表 swap 行
    「经 kernel 共享输入;执行侧迁移批同步接线」的兑付点,禁消费面各写
    第二份排除判定(P60 换手循环的实体在执行路径)。返回 '' = 不排除。
    """
    if ctx is None or not name:
        return ''
    if ctx.membership is None:
        return 'membership_unreadable'
    if name in ctx.membership:
        return 'buy_membership'
    if name in ctx.fresh_buys:
        return 'fresh_buy'
    return ''


@dataclass
class SwapPlanContext:
    """swap 计划谓词的共享输入快照(装配函数产物;发射/执行同契约消费)。

    字段语义与装配源:
    - ``target_factions``/``target_cores``:target 视图(双轨口径,装配
      内经 committed_from→decision_target 伪 comp 链,与执行侧卖出决策
      同一条链);
    - ``membership``:买面义务排除集(单一源 = ``cw_intention.
      locked_buy_membership``;与 M4 燃料集 ``exclude_names`` 同参同源)。
      None = 缺读(谓词弃权,fail-closed);未锁定帧 = 空集(无锁定帧
      不存在 hoard 义务,非缺读);
    - ``fresh_buys``:轮内新鲜度排除名集(见 ``fresh_buys_of``);
    - ``fenced_on``:换阵卖出义务臂态(fenced off-line 件可卖与否)。
    """
    target_factions: frozenset[str]
    target_cores: frozenset[str]
    fw_carry: frozenset[str]
    locked_factions: frozenset[str]
    protect_names: frozenset[str]
    membership: frozenset[str] | None
    fresh_buys: frozenset[str]
    board: dict[str, int]
    deployed: list[BenchChar]
    bench: list[BenchChar]
    cap: int | None
    front_slots: int = DEPLOYED_FRONT_CAPACITY
    back_slots: int = DEPLOYED_BACK_CAPACITY
    fenced_on: bool = False


@dataclass
class SwapPlan:
    """swap 计划(卖序 + 上序 + 逐件拒因;空计划 = 两序空)。"""
    sell_names: list[str] = field(default_factory=list)
    up_bench: list[int] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    abstain: str = ''

    @property
    def nonempty(self) -> bool:
        return bool(self.sell_names) and bool(self.up_bench)


def assemble_swap_plan_inputs(
        session: object,
        *,
        state: GameState | None,
        deployed: list[BenchChar],
        bench: list[BenchChar],
        cap: int | None,
        deployed_n: int | None = None,
        front_slots: int = DEPLOYED_FRONT_CAPACITY,
        back_slots: int = DEPLOYED_BACK_CAPACITY,
        fresh_buys: frozenset[str] | None = None,
) -> SwapPlanContext | None:
    """swap 计划输入装配单一源(发射侧与执行侧**同函数、同一装配契约**;
    ADR-0530)。

    装配源契约(ADR-0530;对抗收口方案钉死原话)= 执行侧卖出决策实际消费的
    快照链,不用 PrepObservation 另起一路:board/fp 消费调用方传入的
    ``state``(执行侧传 ``session.last_state`` 滞后帧链,发射侧传决策帧
    黑板——同函数、异参,输入源两侧分轨是既定事实);deployed/bench 消
    费调用方现读(执行侧 = SIFT 读面,发射侧 = PrepObservation 帧)。
    派生逻辑(target 视图双轨口径/fenced 臂/义务排除集/保护域)全在
    本函数,两侧禁自写第二份。两侧输入的逐字段对齐由 seam 核对批兑现
    (对齐证据 = 开闸小批前置义务,挂账 IMPL_REPORT),核对通过前发射
    位保持关闭。

    返回 None = 装配不可得(target 视图/板面字典缺读),调用方按
    谓词弃权处理(计划空,不静默发射)。

    :param deployed_n: 板满计数覆盖(执行侧喂 ``swap_arm_deployed_count``
        真读槽位口径;None = 按 ``deployed`` 占用件数计——同一占用数
        口径,含 SIFT 未识别占位件)。
    """
    if state is None and cap is None:
        return None
    try:
        from sr_od.application.currency_war.kernel.cw_comps import (
            form_progress,
        )
        from sr_od.application.currency_war.kernel.cw_intention import (
            committed_from,
            locked_buy_membership,
            locked_faction_scope,
        )
        from sr_od.application.currency_war.kernel.cw_launch_admission import (
            protect_names_of,
        )
        from sr_od.application.currency_war.kernel.cw_recipe import (
            decision_target,
        )
    except Exception:   # noqa: BLE001  派生面缺供给 = 装配不可得
        return None
    # target 视图(双轨口径;与 cw_op_deploy 执行侧同链:双轨期走
    # decision_target 伪 comp,定型后走 session.target_comp)
    tgt_comp = None
    try:
        if not committed_from(session, state):
            tgt_comp = decision_target(session, state) if state is not None \
                else None
    except Exception:   # noqa: BLE001  双轨读端缺供给 → 退 target_comp
        tgt_comp = None
    if tgt_comp is None:
        tgt_comp = getattr(session, 'target_comp', None)
    target_factions = frozenset(getattr(tgt_comp, 'all_factions', None) or ())
    target_cores = frozenset(getattr(tgt_comp, 'core_chars', None) or ())
    # fenced 臂(fp 单一源 form_progress,板满 = 占用数 ≥ cap 占用数
    # 口径;cap 现算 = state.max_units() 单点收口链——与 select_swap_plan
    # 板满门同源,禁经调用方 cap 参数分叉出第二口径;执行侧 cap=None
    # (不消费谓词 cap 门)帧同吃现算)
    fenced_on = False
    if tgt_comp is not None and state is not None:
        try:
            _fp = form_progress(tgt_comp, state)
        except Exception:   # noqa: BLE001  成型度不可得 = 臂关(保守)
            _fp = 0.0
        _n = deployed_n if deployed_n is not None else len(
            [d for d in deployed if d is not None])
        fenced_on = fenced_swap_arm_of(_fp, _n, state.max_units())
    # 买面义务排除集(与 M4 燃料集同参同源):锁定帧 = locked_buy_
    # membership;ist 缺失 = 缺读(None,谓词弃权);未锁定帧 = 空集。
    ist = getattr(session, 'v3_intention', None)
    membership: frozenset[str] | None
    if ist is None:
        membership = None
    else:
        _lm = locked_buy_membership(ist)
        membership = _lm if _lm is not None else frozenset()
    board = dict(getattr(state, 'board', None) or {}) if state is not None \
        else {}
    try:
        _lf = locked_faction_scope(ist) or frozenset()
    except Exception:   # noqa: BLE001  围栏兜底 best-effort(同执行侧)
        _lf = frozenset()
    fw_name = getattr(session, 'transition_framework', '') or ''
    _tgt_fw, fw_carry = deploy_target_sets(tgt_comp, fw_name)
    return SwapPlanContext(
        target_factions=target_factions,   # 与执行侧卖出面同口径(all_factions,不含框架并集)
        target_cores=target_cores,
        fw_carry=frozenset(fw_carry),
        locked_factions=frozenset(_lf),
        protect_names=protect_names_of(tgt_comp) if tgt_comp is not None
        else frozenset(),
        membership=membership,
        fresh_buys=fresh_buys if fresh_buys is not None
        else fresh_buys_of(session, state),
        board=board,
        deployed=[d for d in deployed if d is not None],
        bench=[b for b in bench if b is not None],
        cap=cap,
        front_slots=front_slots,
        back_slots=back_slots,
        fenced_on=fenced_on,
    )


def select_swap_plan(ctx: SwapPlanContext | None,
                     reasons_out: dict[str, str] | None = None,
                     ) -> SwapPlan:
    """板满换阵补部署计划谓词(M1″ 发射面;select_deployments 同族纯函数)。

    语义(组合式,零新启发式)::

        swap 计划非空 ⟺ cap 满(占用数口径)∧ 义务/新鲜排除后存在
        合格 victim ∧ 对「卖出 victim 后假想状态」复用 select_
        deployments 判 up 非空

    - **板满门 = 占用数口径**:``,len(deployed)``(占用件数,含 SIFT
      未识别 char_id='' 占位件)≥ cap——与执行侧 cap 门「禁用衍生计数」
      同向(``deployed_occupied`` 同源;禁 ``len(deployed_cids)`` 衍生
      集,SIFT 未识别占位件漏计 = 板实满判未满);
    - **victim 资格** = ``cw_launch_admission.offtarget_sell_allowed``
      (fenced 臂态经装配注入,语义单一源)+ 买面义务集排除(拒因
      ``buy_membership``,与 M4 燃料集同参同源;缺读 = 谓词弃权
      ``membership_unreadable``,fail-closed,与 cap 缺读同构——
      dd-037「留 bench 合法稳态」不对称口径)+ 轮内新鲜度排除(拒因
      ``fresh_buy``,防抖+显影辅助);
    - **上序 = 组合语义**:对卖出后假想板面复用 ``select_deployments_
      reasoned``(围栏/成对/填空/点火序/核心桶/cap/同名去重/配方底线
      全套留置规则就是上序的最终裁判);底线规则留 bench 的件**不作
      上序候选**(拒因 ``post_sell_held``),「白卖一件板面变弱」形态
      在谓词内不可达;
    - **cap 缺读**(``cap is None``)⇒ 弃权 ``cap_unreadable``,与 M1/
      M1′ vacancy=0 门同 fail-closed(dd-037)。

    :param reasons_out: 传入 dict 时逐件拒因(名 → 拒因键)写入。
    """
    reasons: dict[str, str] = {}
    if ctx is None:
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'input_missing'})
        return SwapPlan(abstain='input_missing')
    if ctx.cap is None or ctx.cap <= 0:
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'cap_unreadable'})
        return SwapPlan(abstain='cap_unreadable')
    if ctx.membership is None:
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'membership_unreadable'})
        return SwapPlan(abstain='membership_unreadable')
    occupied = len(ctx.deployed)   # 占用数口径(含未识别占位件)
    if occupied < ctx.cap:
        return SwapPlan(reasons=reasons)
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        offtarget_sell_allowed,
    )
    victims: list[tuple[tuple, BenchChar, set[str]]] = []
    for d in ctx.deployed:
        name = d.char_id or ''
        ch = CHARACTERS.get(name) if name else None
        if ch is None:
            continue   # 未识别件不可判羁绊,不入 victim(执行侧同款)
        bonds = set(ch.factions) | set(ch.flows)
        if not offtarget_sell_allowed(
                name, bonds, set(ctx.target_factions),
                set(ctx.target_cores), fenced_offline_sellable=ctx.fenced_on,
                protect_names=ctx.protect_names):
            reasons[name] = ('fenced_arm_closed'
                             if (bonds & DEPLOY_FENCE and not ctx.fenced_on)
                             else 'target_keep')
            continue
        # 义务集∪新鲜度排除单一判定(执行侧卖出臂同源消费,ADR-0530)
        _excl = swap_sell_exclusion_reason(name, ctx)
        if _excl and _excl != 'membership_unreadable':
            reasons[name] = _excl
            continue
        # 排序对齐执行侧 _sell_offtarget_deployed 候选序:1★ 优先
        victims.append(((0 if (d.star or 1) <= 1 else 1,), d, bonds))
    victims.sort(key=lambda t: t[0])
    plan = SwapPlan(reasons=reasons)
    for _rank, d, _bonds in victims:
        name = d.char_id or ''
        # 卖出后假想态:该件从占用序移除,板面/阵营档按剩余件重算
        kept = [x for x in ctx.deployed if x is not d]
        cids2 = {x.char_id for x in kept if x.char_id}
        fac2 = deployed_bond_counts(cids2)
        up2, held2, held_reasons2 = select_deployments_reasoned(
            ctx.bench, deployed_cids=cids2, deployed_fac=fac2,
            board=dict(fac2), cap=ctx.cap,
            front_total=ctx.front_slots, back_total=ctx.back_slots,
            target_factions=ctx.target_factions,
            target_cores=ctx.target_cores, fw_carry=ctx.fw_carry,
            locked_factions=ctx.locked_factions)
        for _hi in held2:
            _hn = ctx.bench[_hi].char_id or ''
            reasons[_hn] = 'post_sell_held'
        if up2:
            plan.sell_names = [name]
            plan.up_bench = list(up2)
            break
        # 该 victim 卖了也上不了(全部候选被留置)→ 计划收窄试下一
        # victim;最后一个 victim 的留置拒因保留在 reasons 显影。
    if reasons_out is not None:
        reasons_out.update(reasons)
    return plan
