"""deploy 域判定纯逻辑(换阵计划/配方底线/点火序/支撑观测;单一源)。

部署「选人 + 落位」计划已迁策略层(design 2026-09-20-benchchar-retirement
§2.2 落位决策权归策略层):单一源 =
``strategies/impl/mandate_v1/deploy_plan.py``(``select_deployments``/
``select_deployments_reasoned``/``has_deployable``/``can_deploy_single``/
落位策略 ``deploy_row_pref``/``deploy_slot_plans``/出战链计划入口)。
本模块保留其消费的判定 helper(围栏集/点火增益/配方底线门/供给谓词)
与换阵计划链(select_swap_plan,卖后上序经注入参消费选人函数——包依赖
矩阵禁 kernel→strategies 直引,注入契约同 line_members 先例)。

这里只收**纯决策**。输入 = 容器形状(bench = 占席条目 ``BenchSlot``
紧缩序,身份经 ``bench_slot_unit`` 解包;deployed = 行域 ``Unit``,
benchchar-retirement P4 容器形),身份可判(char_id 空串=未识别,
围栏语义「照旧上」保留)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    SIDE_PICK_DUAL_BONDS,
    side_pick_bond,
)
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_BACK_CAPACITY,
    DEPLOYED_FRONT_CAPACITY,
    bench_slot_unit,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    game_state_of,
    max_units_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS,
    RECIPE_FACTIONS,
)
from sr_od.application.currency_war.kernel.cw_system_cards import SYSTEM_CARDS

if TYPE_CHECKING:
    from collections.abc import Callable

    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        Unit,
    )


def _bench_cid(b) -> str:
    """占席条目 → 身份名(单位 = 内嵌 Unit.char_id;占位件/None = '')。
    本模块 BenchSlot 解包单一读点(P4 容器形,解包口 = bench_slot_unit)。"""
    u = bench_slot_unit(b)
    return (getattr(u, 'char_id', '') or '') if u is not None else ''


def _bonds_of(bc) -> set[str]:
    """角色全羁绊(factions+flows);未识别/未注册 → 空集。
    入参 = 容器条目(bench 占席条目 BenchSlot 解包 / 行域 Unit 直读,
    P4 容器形)。"""
    u = bench_slot_unit(bc) if getattr(bc, 'kind', None) is not None else bc
    cid = (getattr(u, 'char_id', '') or '') if u is not None else ''
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
# 三羁绊(阵营,阈值)对从 SYSTEM_CARDS 派生(排除 seele 卡
# ——希儿系是 deployed 单卡判定非阵营计数,deploy 排序/形态维无意义,
# 见 ignition_gain 注);tier 阈值经 FACTIONS 注册表,单一源。
# ⚠️ 遗留副本(迁移计划原文已删,git 历史可溯):
# 权威副本 = knowledge/cw_engine_facts.TRANSITION_TRAITS(同派生式,零字面双源);
# 本副本仅为 sim/旧判据消费点保留;权威副本删除后随之清理;勿新增消费。
TRANSITION_TRAITS: tuple[tuple[str, int], ...] = tuple(
    (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
    for card in SYSTEM_CARDS.values() if card.card_id != 'seele'
)

#: 配方底线门档值(单源派生,模块级常量收敛于此)。
#: ⚠️ 待办关联:本常量派生自上方 TRANSITION_TRAITS 副本,
#: 该副本带迁移待办(权威副本 = knowledge/cw_engine_facts.
#: TRANSITION_TRAITS,按 legacy cleanup 计划随本文件删除)——本常量属
#: 既有消费方向的模块级化(cw_intention 本就 import TRANSITION_TRAITS,
#: 非新增消费方文件),副本迁移执行时本常量须随迁,禁留断链。
RECIPE_FLOOR_TRAIN_CAP: int = dict(TRANSITION_TRAITS).get('列车同行', 2)
RECIPE_FLOOR_XZ_BASE: int = dict(TRANSITION_TRAITS).get('仙舟', 3)


# 守卫适用范围体系集:四过渡体系全覆盖(三羁绊 + 希儿系
# 单卡判据,tier=1)。适用范围语义与 TRANSITION_TRAITS 的 deploy 排序语义
# **分离**——后者是阵营计数排序维(希儿系单卡判定在 deploy 维无意义,
# 故排除,历史理由保留),但 卖侧守卫/保护集借用
# 该常量后「四体系」声称只剩三羁绊适用范围(实机巡检发现的适用范围漂移)。守卫/
# 保护类消费改用本集,不再借 TRANSITION_TRAITS(一常量两语义的根修)。
SEELE_SYSTEM_KEY: str = '希儿系'
#: 希儿系放大器阵营(量子/贝——伤害在希儿技能层,放大器非独立伤害源,
#: transition_combos.md 四体系表;桑博=贝+DOT 双籍是常态不是边界)
SEELE_AMP_FACTIONS: frozenset[str] = frozenset({'量子同频', '贝洛伯格'})
#: 守卫适用范围体系集(GUARD_SYSTEM_TIERS 的本体:三羁绊 + 希儿系 tier=1)
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
    if seele_system_formed(board_factions, deployed_names):
        n += 1
    return n


def seele_system_formed(board_factions: dict[str, int],
                        deployed_names: frozenset[str] | set[str]) -> bool:
    """希儿系达成谓词(单一实现;engines_count 与转型分支守恒门同吃)。

    希儿在场 ∧ 放大器 ≥2(量子同频 ∨ 贝洛伯格任一,「或」口径)。
    从 engines_count 内联式提出:守恒门需要**逐体系**的达成布尔
    (engines_count 只出总数,粒度不够),提函数 = 不写第二份希儿系
    判定(新资格族语义只在判定函数链实现一次)。
    """
    return ('希儿' in deployed_names
            and (board_factions.get('量子同频', 0) >= 2
                 or board_factions.get('贝洛伯格', 0) >= 2))


def is_seele_system_member(char_id: str, bonds: set[str]) -> bool:
    """希儿系贡献件判据(单卡 + 放大器;守卫/保护适用范围口径)。

    希儿本人(单卡)+ 量子同频/贝洛伯格放大器件——与 cw_evolution.
    _engine_systems_formed/_contributes_engine_system/_is_member 的
    希儿系分支同口径(此前已有单卡判据先例,此处提为单一源函数)。
    tier=1:希儿系作为四过渡体系之一的档(已退役口述登记簿 四体系封闭
    裁定,transitions.md;希儿系引擎=希儿在场 ∧ 放大器 ≥2,但**恢复
    种子**的适用范围口径取贡献件全计——清空任意最后一件贡献件都使该体系
    归零,owned 计数含希儿与全部放大器件)。
    """
    return char_id == '希儿' or bool(bonds & SEELE_AMP_FACTIONS)


#: B_t 板面线内阵营集(四过渡体系:TRANSITION_TRAITS 三羁绊阵营 ∪
#: 希儿系放大器阵营;与 engines_count 同适用范围的支撑面)。纯遥测观测
#: 适用范围(纯遥测口径延续),不进任何判据。
SYSTEM_LINE_FACTIONS: frozenset[str] = (
    frozenset(b for b, _t in TRANSITION_TRAITS) | SEELE_AMP_FACTIONS)


def board_target_line_weight(
        deployed_names: frozenset[str] | set[str] | list[str]) -> int:
    """B_t:板面目标线支撑计数(件级单一源;form_score 替代披露口径)。

    逐件判定 = 全羁绊(factions+flows,CHARACTERS 注册表)∩
    ``SYSTEM_LINE_FACTIONS`` 非空,或希儿本人(单卡判据,与
    ``is_seele_system_member`` 希儿分支同口径);命中件计 1——桑博=贝+DOT 双籍
    只计 1 件(件级非阵营级,阵营级计数会双籍重复)。bench 囤件不计入
    (与旧 form_score 同裁决口径:「上场了才算支撑」)。

    定位:纯遥测观测面,不进判据(零行为面)。替代口径的依据 =
    form_score 预测力判定(sim 90 局全量:现口径在决策
    关键帧恒常数 1.0 零方差、预测力为零;B_t 是唯一 p<0.001 显著
    代理,预测力集中于 boss 战存活深度,对伤害差/终局 hp 仅弱正
    ——判读时按此边界解读,勿拔高用途)。与换人判据的支撑件计数
    (换人通道统一批新增判据)为**不同辖域的两个口径**:后者 = 锁定
    终局阵容名单成员 ∪ 终局键集标签命中外部件(单一源 =
    ``terminal_key_label_hit_names``/``_bond_gate_support_count``,
    进换人行为面、计数随 ``bond_gate_keys`` 变);本计数 = 四过渡体系
    披露口径,纯遥测不进判据、不随锁定键集变。两口径并存,禁互相
    替代。禁第二实现:任何 B_t
    消费只走本函数。
    """
    n = 0
    for name in deployed_names:
        if name == '希儿' or bool(_bonds_named(name) & SYSTEM_LINE_FACTIONS):
            n += 1
    return n


def _bonds_named(char_id: str) -> set[str]:
    """按名字查全羁绊(factions+flows);未识别/未注册 → 空集。"""
    ch = CHARACTERS.get(char_id) if char_id else None
    if ch is None:
        return set()
    return set(ch.factions) | set(ch.flows)


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


def recipe_floor_holds(main_faction: str,
                       train_now: int,
                       xz_now: int,
                       lock_exempt_armed: bool,
                       supply_exists: bool) -> bool:
    """配方底线门单一判定(含锁定线语境豁免;kernel 单一源)。

    返回 True = 该件应被门持有(拒因 'recipe_floor')。消费面(禁任何
    分支副本,门本体 + 豁免)= mandate_v1 deploy_plan
    (select_deployments 选人门)/ select_swap_plan(经注入 select_up
    复用)。

    豁免语义:lock_exempt_armed(豁免条件(1)锁定线语境成立,单源 =
    ``cw_intention.locked_line_recipe_floor_conflict``)∧ not
    supply_exists(豁免条件(2)本帧无有效仙舟供给,单源 =
    ``xianzhou_supply_exists``)→ 门让位——锁定线收束期列车 core 不被
    门空槽拦死,仙舟基础线保护由供给保留条款继续承保。

    :param main_faction: 件的主阵营(CHARACTERS factions[0];与
        mandate_v1 deploy_plan.select_deployments 内 bench_fac 同源口径)。
    :param train_now: 运行阵营列车档(kernel 侧 ``_fac_run`` 循环逐件
        增量 / op 侧 ``_deployed_fac`` 拖拽逐件增量——动态重判的防线
        价值在各消费方自持,本函数只共享判定不共享状态)。
    :param xz_now: 运行阵营仙舟档(口径同上)。
    :param supply_exists: 出战就绪时由调用方现算喂入;disarmed 时传
        False(惰性语义:armed=False 时本值不被读取)。
    """
    if main_faction != '列车同行':
        return False
    if not (train_now >= RECIPE_FLOOR_TRAIN_CAP
            and xz_now < RECIPE_FLOOR_XZ_BASE):
        return False
    # 豁免:锁定线语境武装 ∧ 本帧无有效仙舟供给 → 门让位(供给保留
    # 条款:bench 有真供给时门照拦,供给先上)。
    return not (lock_exempt_armed and not supply_exists)


def xianzhou_supply_exists(bench: list,
                           on_board_cids: set[str]) -> bool:
    """本帧 bench 是否存在「有效仙舟供给」(配方底线门豁免条件(2))。

    有效供给 = 存在 bench 件同时满足四条(死供给三类排除,I2 防复发
    ——按名义供给计数时,任一死供给形态在场 = 豁免恒闭 = 列车 core
    恒拦,死锁换形复发):

    ① 全羁绊(factions+flows)含 '仙舟'(与门增量口径同式——凡部署
       推进仙舟档的件都算供给,对照 select_deployments 的 ``_fac_run``
       全羁绊 +1 口径);
    ② 非占位件(槽位 kind ∈ tome/bookcard/supply_box 恒拒、永不上场
       = 死供给;§2.4 字段映射 kind 口);
    ③ char_id ∉ on_board_cids(同名在场拷贝恒 held = 死供给;
       on_board_cids = deployed_cids ∪ 本帧已上——kernel 侧传
       deployed_cids | _up_names,op 侧 _deployed_cids 已含同执行增量);
    ④ 主阵营 ≠ '列车同行'(防御性排除,当前注册表无实例——防未来
       「flows 含仙舟 ∧ 主阵营列车同行」形态件:其自身被本门拦,永远
       轮不到它贡献仙舟档 = 死供给;主阵营口径 = ch.factions[0])。

    ⚠️ 数据依赖声明(豁免条件节):谓词完备性依赖注册表现状
    「仙舟羁绊件主阵营恒=仙舟」;凡新增仙舟羁绊件入表,须核对其主阵营
    取值——未来入表「flows 含仙舟 ∧ 主阵营 ∉ 配方阵营」的件会被散牌
    围栏/成对门拦住上不了场、却仍被判有效供给 → 豁免闭合 → 列车 core
    恒拦(死供给第四类换形)。

    未注册/未识别件:无羁绊可判 → 非供给(与 ``_bonds_of`` 同形)。
    本谓词恒不抛异常(全分支防御读),消费方无需 try。
    """
    for bc in bench or []:
        if getattr(bc, 'kind', 'unit') in ('tome', 'bookcard', 'supply_box'):
            continue
        u = bench_slot_unit(bc)
        cid = (getattr(u, 'char_id', '') or '') if u is not None else ''
        if not cid or cid in on_board_cids:
            continue
        ch = CHARACTERS.get(cid)
        if ch is None or not ch.factions:
            continue
        if '仙舟' not in (set(ch.factions) | set(ch.flows)):
            continue
        if ch.factions[0] == '列车同行':
            continue
        return True
    return False


def deployed_bond_counts(deployed_cids: set[str]) -> dict[str, int]:
    """已上场角色全羁绊计数(factions+flows 逐项 +1;r361b 全羁绊口径)。

    消费面 = mandate_v1 deploy_plan 计划装配(``_deploy_plan_inputs``)与
    select_swap_plan 卖后假想档(两侧计数同循环同口径,单一源;未注册名
    不计——无名可判即无阵营信号,件本身的去重/fail-open 由
    deploy_plan.select_deployments 的 cid 分支管)。
    选边型双羁绊角色(布洛妮娅,``cw_chars.SIDE_PICK_DUAL_BONDS``)按
    ``cw_chars.side_pick_bond`` 选边单边计入(贡献 = [side] 替代双边
    出身;基数 = 其余在场 cid 的注册表出身,同图鉴「角色的数量」口径,
    不含装备贡献)。
    """
    out: dict[str, int] = {}
    cids = list(deployed_cids)
    for cid in cids:
        ch = CHARACTERS.get(cid) if cid else None
        if ch is None:
            continue
        if cid in SIDE_PICK_DUAL_BONDS:
            tags: tuple[str, ...] = (side_pick_bond(
                cid, [c for c in cids if c != cid]),)
        else:
            tags = tuple(ch.factions or ()) + tuple(ch.flows or ())
        for f in tags:
            out[f] = out.get(f, 0) + 1
    return out


def deploy_target_sets(target_comp: object | None,
                       transition_framework: str = '',
                       ) -> tuple[set[str], set[str]]:
    """deploy 围栏 target 集装配(装配单一源的**围栏视图 helper**;案 B)。

    视图归属定案(.debug/progress/2026-09-11-cw-clear-run/定谳记录-deploy围栏.md
    第六节:围栏目标视图 = 成型面装配语义,本函数退出独立第二装配入口地位):
    - 双轨期(``transition_framework`` 非 ''):配方伪 comp all_factions
      (``cw_recipe.recipe_comp`` 单一源;「过渡=配方即方向」,终局阵容特有键
      不混入——方向混装移除是定案申报的行为差)。框架方向键面完备性由配方
      数据承载(仙舟配方持续伤害键,B2 修正条件),**显式 ``∪ FRAMEWORK_
      FACTIONS`` 停用**(并集语义只许配方一处,双源即分裂);
    - 定型/无框架:终局 comp all_factions(= factions ∪ flex_factions,
      与装配单一源 assemble_swap_plan_inputs 的 target 视图同链同值;
      flex 键入场是定案申报行为差③)。
    返回 ``(target_factions, fw_carry)``:fw_carry = 框架注册表成员
    (``cw_line_facts.framework_members`` 现算;统一保护集迭代 design §2.4 ①
    迁移,原策展档位过滤随 TRANSITION_PACK 符号退役)。
    信任边界:``fw`` 非 '' 即双轨期信号(与 ``cw_recipe.decision_target`` 的
    committed 门同向;定型后框架无写端=休眠,不存在 committed 携 fw 帧)。
    防御退型:框架无配方注册(理论态)/阵容无 all_factions 属性(鸭子型
    阵容)→ 逐位退旧语义,零漂移。消费面 = mandate_v1 deploy_plan 计划
    装配(``_deploy_plan_inputs``,动作发出点与出战链单一源)——选人抑制谓词
    (发出×执行契约)与换阵分支各写一份即双源,禁复制。
    """
    fw = transition_framework or ''
    fw_carry: set[str] = set()
    if fw:
        from sr_od.application.currency_war.kernel.cw_recipe import recipe_comp
        from sr_od.application.currency_war.knowledge.cw_line_facts import (
            FRAMEWORK_FACTIONS,
            framework_members,
        )
        rc = recipe_comp(fw)
        if rc is not None:
            tgt = set(rc.all_factions)
        else:
            # 未注册框架(理论态):退旧并集语义(零漂移保守侧)
            tgt = set(getattr(target_comp, 'factions', None) or ()) \
                | set(FRAMEWORK_FACTIONS.get(fw, ()))
        fw_carry = set(framework_members(fw))
    else:
        tgt = set(getattr(target_comp, 'all_factions', None)
                  or getattr(target_comp, 'factions', None) or ())
    return tgt, fw_carry


def residual_fill_plan(held: list, front_empty: list, back_empty: list,
                       bench_pos: dict, bench_cid: dict,
                       deployed_cids: set, cap: int | None,
                       deployed_count: int) -> list[tuple[int, str, int]]:
    """P24 残余补部署计划(纯函数,可离线直测;判据单一源 = 本函数,
    消费面 = 动作发出面谓词(mandate m1p 换人分支 ``select_swap_plan`` 调用面),
    机械执行侧 ``CwActionSellDeployedOp`` 不消费本函数;原部署机侧同名
    转发适配器已停用)。

    主排序循环结束后空槽仍存在(cap 未满)且散牌留置(``held``)非空时,
    对留置散牌生成补部署计划。判据 = P24 残余补部署支配定理
    (docs/develop/sr_od/application/currency_war/proofs/
    p24-residual-fill-dominance.md):零支出域(C=I=0,补部署不触碰金账
    任何记账点)下,空 cap 槽上任意**合法**单位上阵
    ΔEV = Δp·ΣL_c·S ≥ 0 恒成立(u>0 且 Δp>0 时严格>0)——
    「有羁绊的板 > 空槽」,故合法留置件逐件补上,不存在负 EV 退补路径;
    非法件(同名 dup)与物理上限(cap 满/两排皆满)是守卫剔除面而非
    EV 判负。散牌留 bench 与配方围栏覆盖「选谁优先」语义,
    不支配「空槽 vs 空板」。消费时机 = 部署执行帧主拖拽循环之后
    (拖拽后 fresh 复查占用喂入),禁移动作发出面——fill 依赖拖拽后真值,
    移动作发出点 = 时序行为变更。

    返回 ``[(bench_idx, to_row, slot_idx)]``——``bench_idx`` =
    ``held`` 元素原值(备战栏槽位下标,0 基,与 ``bench_pos``/
    ``bench_cid`` 键域同域);``slot_idx`` = 对应排行点位列表的 0-based
    下标(主循环 ``front_empty``/``back_empty`` 同域,执行侧
    ``row_pts[slot_idx]`` 取拖点、``slot_idx+1`` 即物理槽号)。守卫照搬
    主循环:
    - 同名禁双(5.1.7):``bench_cid[i]`` 已在 ``deployed_cids`` → 跳过
      (游戏拒收同名,局14 藿藿 5 连败实证——dup 是 3合1 素材不是可
      上阵件);
    - cap 动态:``deployed_count`` + 已计划数达 ``cap`` → 停(cap=None
      不设门,拖到游戏拒即真值,同主循环 5.1.8 口径);
    - 选排按 ``bench_pos``(position_pref),首选排无空槽 fallback 另一排,
      两排皆满停。
    """
    plan: list[tuple[int, str, int]] = []
    fe = list(front_empty)
    be = list(back_empty)
    for i in held:
        cid = bench_cid.get(i)
        if cid and cid in deployed_cids:
            continue   # 同名禁双(dup 留 bench 待 3合1)
        if cap is not None and cap > 0 and deployed_count + len(plan) >= cap:
            break   # cap 满,动态停(同主循环)
        pref = bench_pos.get(i, 'back')
        row = pref
        slot = next((s for s in (fe if pref == 'front' else be)), None)
        if slot is None:
            row = 'back' if pref == 'front' else 'front'
            slot = next((s for s in (be if pref == 'front' else fe)), None)
            if slot is None:
                break   # 两排皆满
        (fe if row == 'front' else be).remove(slot)
        plan.append((i, row, slot))
    return plan


# ===== 换阵卖出义务分支(自 cw_op_deploy 迁 kernel;单一源收敛)=====
# 为什么迁 kernel:swap 动作发出面谓词(select_swap_plan,本文件尾)与执行侧
# 卖出分支共吃同一 fenced 分支判据——判据驻 operations 桶时 kernel 谓词够不着
# (包依赖矩阵禁 kernel→operations),自写 fp/板满组合 = 第三源(先例:
# cw_launch_admission.py DEPLOY_FENCE 注释,r271 批同型双源清退)。
# cw_op_deploy 保留同名 re-export,既有消费路径(生产 deploy 卖出分支/
# 测试)零迁移。

def swap_arm_deployed_count(board: dict | None,
                            tracked_deployed: list) -> int:
    """换阵卖出义务分支「板满」条件的部署数喂入(单一口径)。

    = 容器占用数(占用判定 = 元素非 None 计 1;P4 容器形,行域本身即
    紧凑占用序)。**禁用
    ``sum(board.values())``**:board 语义 = 阵营名 → 该阵营在场人数
    (一人多阵营贡献多次,4 人可贡献 11 阵营次)——把羁绊计数当部署数
    喂「板满」门 = 建模对象错,板未满即开分支、熔断自线成型起事实失效。
    """
    return sum(1 for d in (tracked_deployed if isinstance(tracked_deployed, list)
                           else []) if d is not None)


def fenced_swap_arm_of(fp: float, deployed_n: int, cap: int | None) -> bool:
    """换阵卖出义务分支触发判据(纯函数,测试面):线成型(fp≥1.00,
    单一源 ``cw_comps.form_progress``)∧ 板满(占用数 ≥ cap——cap =
    可上阵数占用数口径,与 select_swap_plan 板满门同一派生链
    ``max_units_of``(level+宝钻、封顶 = 4+back_max 动态真值
    〔GameState.back_layout,值域 10-13〕;物理槽表常数 DEPLOYED_
    CAPACITY 禁作阈值,理由见下),
    喂入单一源 = ``swap_arm_deployed_count``)。两条件并存 =
    熔断的振荡防护前提(买/演进层仍要 fenced 件)消失、且 bench target
    无空槽可进——此时 off-line fenced 件让位。

    口径裁决(REVISION_R2 同根双源收敛):板满门禁用物理槽位总数
    (front+back=10)——XP_TO_NEXT_LEVEL 键域 3..9 ⇒ level≤9 ⇒
    level 驱动 cap 全域 <10,物理门恒不可达 ⇒ 分支全游戏恒死;cap
    缺读(None/≤0)= 分支关(fail-closed,与谓词 cap_unreadable 同向)。
    """
    if fp < 1.0 or not cap or cap <= 0:
        return False
    return deployed_n >= cap


# ===== 转型域双门(bond gate;bench→板 换人通道核判据层)=====
# 换人合法性 = 组换后板态 × 锁定终局阵容(2026-10-26-swap-channel-unified
# design §2.0)。转型域判别子三合取 + 门 1 收益门四腿在此实现;旧转型分支
# 机器(回滚常量/混轨域谓词/装配级键集收窄/域快照)已由双门取代退役
# (design §2.3.1)——转型域 = 本节判别子钉死的「终局阵容锁定帧」;
# P1 配方对锁帧(腿②)按 pair 帧路由钉死(design §2.3.1)逐位走现行混轨
# 机器,不进本域。
# 病灶史:旧转型分支(locked ∧ fp<1.00 ∧ 板满帧 fenced victim 经守恒门
# 逐件放行)只修触发层,多层
# 判据(触发/守恒/放行/让位)各自演化仍封死同一批 victim——本域把
# 触发/守恒/让位三层归一判定函数链(素材/窗口两层按 design §2.0 保留
# 各自折法),单帧语义锚 = 枚举情形表(design §2.2)。

#: 转型分支守恒门体系档表:GUARD_SYSTEM_TIERS ∪ 护盾
#: (FACTIONS tiers 注册表消费,零硬编码档)。直核不变式:守恒门体系集
#: ⊇ DEPLOY_FENCE(熔断替代论证的支撑前提——门适用范围覆盖原一刀切保护对象)。
#: 希儿系档 = 单卡二元判定(见 ``seele_system_formed``),不进 tiers 计数。
SWAP_GUARD_SYSTEMS: tuple[tuple[str, tuple[int, ...]], ...] = (
    tuple((bond, (tier,)) for bond, tier in GUARD_SYSTEM_TIERS)
    + (('护盾', tuple(FACTIONS['护盾'].tiers)),)
)
assert {k for k, _ in SWAP_GUARD_SYSTEMS} >= set(DEPLOY_FENCE), \
    '转型臂守恒门体系集必须覆盖 DEPLOY_FENCE(熔断替代论证前提)'


def _swap_guard_achieved(board_factions: dict[str, int],
                         deployed_names: set[str] | frozenset[str],
                         ) -> dict[str, int]:
    """守恒门的逐体系达成档数:achieved(s) =
    |{t ∈ tiers: board_count(s) ≥ t}|;希儿系 = 0/1(单卡二元)。"""
    ach: dict[str, int] = {}
    for bond, tiers in SWAP_GUARD_SYSTEMS:
        if bond == SEELE_SYSTEM_KEY:
            ach[bond] = 1 if seele_system_formed(board_factions,
                                                 deployed_names) else 0
        else:
            cnt = board_factions.get(bond, 0)
            ach[bond] = sum(1 for t in tiers if cnt >= t)
    return ach


def swap_bond_gate_domain_of(locked_core: bool, fp: float | None,
                             board_full: bool) -> bool:
    """转型域判别子(原始字段形态;单一源;design §2.0 三合取)。

    = 腿①(终局阵容锁定,**显式排除 p1_pair 腿②**)∧ fp < 1.00 ∧ 板满,
    三合取全继承现行语义:
    - 腿① 判定权威 = 锁定线槽非空(cw_intention 判定权威腿① =
      ``ist.locked_comp`` 非空);配方对锁帧不进本域——pair 帧按
      design §2.3.1 pair 路由钉死逐位走现行混轨机器,committed_authority
      全值(含配方对锁腿②)不可作本判别子;
    - 板满腿继承 = 现行换人只在板满帧发(板满门单点 =
      ``required_swap_arm_pending`` 同链)——不继承则与 M1 直上通道
      抢活白卖;
    - fp<1.00 腿继承 = 成型帧不进换人域(fp≥1.00 键集回全量的现行分界)
      ——丢弃则成型帧行为差未申报;fp 缺读 = 域外(fail-closed,与
      fenced 关门分支 fp_unreadable 同向)。

    消费面 = ``swap_sell_exclusion_reason``(资格域分流)/
    ``select_swap_plan``(组贪心域分流)/
    ``assemble_swap_plan_inputs``(域字段装配)/
    mandate_v1 ``swap_transition_narrow_frame``(买侧收窄谓词源)——
    判定只此一份,禁各消费位自写第二份合取。
    """
    return bool(locked_core) and fp is not None and fp < 1.00 and board_full


def swap_bond_gate_domain(ctx: SwapPlanContext | None) -> bool:
    """转型域判别子(ctx 形态;字段读法单一源,见原始形态 docstring)。

    腿① 读 ``ctx.locked_core``(终局阵容锁定,非 pair);域外
    (未锁帧/配方对锁帧/成型帧/板不满帧)恒 False。
    """
    if ctx is None:
        return False
    return swap_bond_gate_domain_of(
        bool(getattr(ctx, 'locked_core', False)),
        getattr(ctx, 'fp', None),
        bool(getattr(ctx, 'board_full', False)))


def fenced_swap_gate_open(locked: bool, fp: float | None,
                          board_full: bool) -> bool:
    """fenced 关门分支域腿(混轨;design §2.3.1 逐帧真值表)。

    关门判定 = 混轨 locked(腿①∨p1_pair 腿②)∧ fp<1.00 ∧ 板满,
    **无回滚常量腿**(转型分支机器退役,表达式内联脱钩退役符号,
    语义与现行逐帧等价)。四行真值表:
    - 未锁帧 → 关(fenced 件为未来换人货币受保护,``fenced_arm_closed``);
    - 锁定 ∧ fp<1.00 ∧ 板满 → 开门落资格族/让位检验(pair 双轨帧与
      转型域帧同此形态);
    - 锁定 ∧ fp≥1.00(成型帧)→ 关(现行);
    - 锁定 ∧ fp 缺读 → 关(消费位单列 ``fp_unreadable``,fail-closed 同向)。

    消费面 = ``swap_sell_exclusion_reason``(资格分流早退腿与 fenced
    件关门腿)/ ``select_swap_plan``(F1 合取②跳过域 = 旧混轨转型域帧集,
    逐帧等价)。
    """
    return bool(locked) and fp is not None and fp < 1.00 and board_full


def _swap_yield_union_achieved(target_factions: frozenset[str] | set[str],
                               names: set[str] | frozenset[str]) -> int:
    """让渡序度量的并集达成档总数(P79-4)。

    度量域 = target 视图 ∪ SWAP_GUARD_SYSTEMS 的**体系集**(并集去重,
    重叠键计一次),逐体系 achieved 档数求和;计数源 = deployed_bond_
    counts(注册表口径),tier 源 = FACTIONS 自然档表(重叠键仙舟取
    (3,5,7,10)),希儿系 = seele_system_formed 二元。
    度量域显式钉死(design §2.7):键集收窄退役后调用面喂
    ``comp.all_factions`` **全量并集**(与旧收窄域等价性同源——收窄剔除
    键 achieved 恒 0,差分恒 0),非终局键集字面——锚帧青雀(仙舟+战技点)
    贡献 2 的算术依赖战技点经 flex_factions 入域,按字面喂终局键集会使
    锚帧算术失效。禁换第二度量。
    """
    counts = deployed_bond_counts(set(names))
    total = 0
    for key in set(target_factions) | {b for b, _t in SWAP_GUARD_SYSTEMS}:
        if key == SEELE_SYSTEM_KEY:
            total += 1 if seele_system_formed(counts, names) else 0
            continue
        info = FACTIONS.get(key)
        if info is None:
            continue
        cnt = counts.get(key, 0)
        total += sum(1 for t in info.tiers if cnt >= t)
    return total


def swap_yield_contribution(target_factions: frozenset[str] | set[str],
                            deployed_names: set[str] | frozenset[str],
                            name: str) -> int:
    """结构档边际贡献(P79-4 让渡序首键)。

    = 该件离场使「target 视图 ∪ SWAP_GUARD_SYSTEMS」并集各档 achieved
    档数下降的量(纯结构计数,零星级零战力项);0 = 纯过渡件 = 让渡序
    首件候选。资格保护不在本度量(治「先换谁」不治「能不能换」,守恒门
    承载资格,两者正交)。"""
    names = set(deployed_names)
    before = _swap_yield_union_achieved(target_factions, names)
    after = _swap_yield_union_achieved(target_factions, names - {name})
    return before - after


# ===== 板满换阵补部署计划(M1″ 动作发出面谓词;与 select_deployments 同族)=====
# 语义出处:(board-full swap redeploy)。
# 结构:消费面 = 动作发出面(mandate M1″ 换人分支)单一——assemble_swap_plan_inputs
# 同一装配契约,输入源 = 决策帧黑板;机械执行侧 CwActionSellDeployedOp
# 不消费本函数(机械单发零现读,原执行侧卖出分支输入轨已停用);
# 发出输入的逐字段装配契约由装配单一源钉死,禁另起第三路。
# 拒因键(闭集):cap_unreadable / membership_unreadable / input_missing
# (弃权三键,计划空)+ 逐件拒因 fenced_arm_closed / target_keep /
# protected / buy_membership / fresh_buy / post_sell_held。

# 轮内新鲜度排除载体(宿主 = ``GameState.round_fresh_buys``,字段
# 定义注 = kernel/cw_game_state.py;渠道②动作上报,经本模块
# record_fresh_buy 单口):动作发出点买入时逐名写入的名集,键式 =
# {'phase': (plane, round_num), 'names': list[str]}——位面/轮次推进自动
# 失效(M7 标志键式同构)。写点 = 生产 shop.py 全部 CwActionBuyCardParam 动作发出点
# 经 ``_emit_buy`` 收束调用(5edcf324)。
# 取舍声明:沿用动作发出点写入(与 ``cw4_fuel_filler_stall_buys`` 先例同位),
# 被截断器丢弃的买入意图也入排除集 = 过度排除压制合法 swap,方向安全
# (留置合法稳态,动作发出契约口径),失真经 fresh_buy 拒因可追溯;单调性由
# 义务集排除独立承载,本载体只承担防抖+暴露(拒因照记,不宣称切环)。


def _fresh_phase(state: GameState | None) -> tuple:
    """相位键读法(容器读口;None = 缺读缺省 (None, 1))。"""
    if state is None:
        return (None, 1)
    return (plane_of(state), round_num_of(state))


def record_fresh_buy(session: object, gs: GameState | None,
                     name: str) -> None:
    """轮内新鲜度排除登记(买入意图逐名写入;动作发出点调用)。

    同一发出批的多个买入意图**逐名**入集(防批量买入漏记——漏记 =
    卖出环切不断,防抖失效静默)。键式见 ``GameState.round_fresh_buys``
    (kernel/cw_game_state.py 字段注)。宿主解析与旧载体同构:gs 在场 =
    写 gs 字段(调用方契约 = 容器单例);gs 缺席 = session 容器读口兜底
    (None session 一次性空载体,与旧载体「一次性宿主」形态一致)。
    """
    if not name:
        return
    host = gs if gs is not None else game_state_of(session)
    reg = host.round_fresh_buys.value
    phase = _fresh_phase(gs)
    if not isinstance(reg, dict) or reg.get('phase') != phase:
        names: list[str] = []   # 新相位(或首次):整体换记录(set→list 转形)
    else:
        _cur = reg.get('names')
        names = list(_cur) if isinstance(_cur, list) else []
    if name not in names:
        names.append(name)
    host.write_logic(host.round_fresh_buys, {'phase': phase, 'names': names},
                     produced_by='record_fresh_buy',
                     evidence='fresh_buy_emit',
                     sig=ChannelSig(family='logic_action',
                                    actor='CwDeployLogic', mode='compute'))


def fresh_buys_of(session: object,
                  gs: GameState | None) -> frozenset[str]:
    """读当前位面轮内有效的新鲜买入名集(跨轮 = 空集,自动失效)。"""
    host = gs if gs is not None else game_state_of(session)
    reg = host.round_fresh_buys.value
    if not isinstance(reg, dict):
        return frozenset()
    phase = _fresh_phase(gs)
    if reg.get('phase') != phase:
        return frozenset()
    names = reg.get('names')
    return frozenset(names) if isinstance(names, list) else frozenset()


def fresh_buys_sell_face(session: object) -> frozenset[str]:
    """L1 卖侧统一标志读端(r408
    「本轮已买」半边的消费面补全——该半边存活于本载体,
    读面此前仅 deploy 侧换出守卫)。

    读端自治(fail-closed 语义):相位 (plane, round_num) 自
    session 容器 node 读口解析(黑板槽停用后容器直读——登记相位
    写端 ``record_fresh_buy._fresh_phase`` 本就取容器读口,读端同源消
    过渡期双源窗),不消费消费位显式传轮——``current_round`` 漏接线帧
    不再静默放行(对 V2-09 在 L1 硬面的显式翻转;v1 缺口 C:漏接线
    静默裸奔,纪律覆盖改结构保证)。

    - 黑板帧可得:常规键对读(相位失配 = 空集,与 ``fresh_buys_of``
      同形态,轮界自动过期);
    - 黑板帧不可得(轮号解析失败帧)= 排除登记当前记录 names 全集
      ——单记录载体下「当前记录」恒为最新相位写入(新相位写入即整体
      作废旧记录),历史轮名不泄入,过度排除上界 = 单轮,方向安全;
    - 读取零销账(过期由相位失配整体作废,与档 2 载体
      mandate.ROUND_SOLD_ATTR 同形态,读端无逐名生命周期面)。
    """
    reg = game_state_of(session).round_fresh_buys.value
    if not isinstance(reg, dict):
        return frozenset()
    names = reg.get('names')
    if not isinstance(names, list):
        return frozenset()
    _gs = game_state_of(session)
    node = _gs.node.value
    if node is not None:
        phase = (plane_of(_gs), round_num_of(_gs))
        if reg.get('phase') != phase:
            return frozenset()   # 相位失配 = 跨轮,整体作废(零销账)
        return frozenset(names)
    # 节点未定帧(开局前):fail-closed 排除当前记录全集(方向安全,上界单轮)
    return frozenset(names)


def required_swap_arm_pending(ctx: SwapPlanContext | None) -> bool:
    """板满换入分支触发谓词(纯函数;判定单一源)。

    两分支任一成立即武装(板满 = 占用数口径,与 M1″ 板满门同链;板不满
    帧不覆盖——空位由 M1 部署通道直上,无需卖出换人):
    - **必需件滞留**:required_names 非空(目标阵容带 required_deployed;
      现役两实例 = 希儿系 pair 的 ``pair_target_comp`` 与 COMP_LIBRARY
      静态套「希儿量子」(P2+ 锁定路径),单一源 = ``SEELE_CARRY_CHAR``)
      ∧ 必需件不在板 ∧ bench 存在必需件;
    - **配方完成件滞留**(双轨对锁期通道):方向锁在效(``ctx.locked``,
      终局阵容锁定 ∨ P1 配方对锁,适用范围门单点 = ``_completion_swap_ins``)∧
      fp < 1.0 ∧ bench 存在「入板即成型」件——桥池 pair 的
      required_deployed 恒空,双轨期板面义务本体 = 过渡配方(cw_recipe
      模块不变量),完成件压席帧由本分支承接;✗→✓ 严格优(换入后物化
      判据改善才准换;依据 = 口述条目 20(登记簿已退役) 配方驱动板面 / [13]
      凑齐优先;出处 = 2026-09-18 sim 实证:配方对锁局板满帧全
      plan_empty)。

    fail 方向:ctx None / 板满缺读 / fp 缺读 = 分支关(不放宽 target 保护,
    与基座分支 fail-closed 同向)。
    """
    if ctx is None or not ctx.board_full:
        return False
    names = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    if ctx.required_names and not (set(ctx.required_names) & names):
        bench_names = {_bench_cid(b) for b in (ctx.bench or [])
                       if b is not None and _bench_cid(b)}
        if set(ctx.required_names) & bench_names:
            return True
    return bool(_completion_swap_ins(ctx))


class _HypotheticalPanel:
    """换入分支假想面板(form_progress 鸭型位;与 _deploy_advances_form
    同型,只提供折法消费的三个视图槽)。"""

    def __init__(self, board_counts: dict[str, int],
                 deployed_names: set[str]) -> None:
        from types import SimpleNamespace

        from sr_od.application.currency_war.kernel.cw_game_state import (
            DeployedView,
        )
        self.board = SimpleNamespace(value=dict(board_counts))
        # required 腿席位经视图读:假想板上必需件按「已换入」计(分支前提 =
        # 卖后上序底线保证必需件落位;在此不计则判据恒缺腿,分支永不开)。
        self.deployed = SimpleNamespace(
            value=DeployedView(
                front_slots=[SimpleNamespace(char_id=n)
                             for n in deployed_names],
                back_slots=[]))


def _required_swap_victim_completion_holds(ctx: SwapPlanContext,
                                           name: str) -> bool:
    """换入分支 victim 判据保持检验(单一源折法,零自写 AND/OR 内联)。

    = 假想面板(victim 离场 ∧ 必需件按已换入计)下
    ``cw_comps.form_progress(阵容, panel) >= 1.0``——与
    ``readiness_form_ok`` 同式同源(成型判据唯一折法契约,含
    OR 组承接同键档规则;禁消费位绕过自写 AND 账,静态套「希儿量子」
    form_tiers 全被 OR 承接的形态由此天然正确)。阵容缺读 = 检验不过
    = 分支不开(保守)。
    """
    comp = ctx.target_comp
    if comp is None:
        return False
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    names = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    hyp_names = (names - {name}) | set(ctx.required_names)
    panel = _HypotheticalPanel(deployed_bond_counts(hyp_names), hyp_names)
    return form_progress(comp, panel) >= 1.0


def _completion_swap_ins(ctx: SwapPlanContext) -> frozenset[str]:
    """完成品换入候选集(判据 ✗→✓ 严格优;单帧现算,无状态)。

    适用范围门(本函数单点,判据域参数化;design §2.3 收窄点钉死):
    方向锁在效(``ctx.locked`` 混轨 = 终局阵容锁定腿① ∨ 配方对锁腿②,
    装配单一源)——未对锁帧恒空集,三消费位(触发谓词完成分支/
    victim 让位检验/卖后上序底线)同吃零签名,禁消费位另设第二份门。
    内部按域分派:双轨域(腿② pair 帧)= 现行配方完成件 fp✗→✓ 折法;
    转型域(腿①)= 门 1④ 同源折法——两域折法同一函数 =
    ``cw_comps.form_progress``(成型判据唯一折法,含 OR 组承接/required
    腿),「分派」= 同一单点门两域各自适用范围,**禁复制第二实现**。
    门 1④ 消费(组贪心)经同一函数对本候选集语义成立:候选 M 入板即
    成型 ⟺ 该换入对的门 1④ 成立。

    = bench 中「入板即成型」的件名:M 在 bench ∧ 板上无同名 ∧ 假想面板
    (板 ∪ {M})下 ``form_progress(ctx.target_comp) >= 1.0``。前提帧 =
    ctx.fp < 1.0(已成型帧无完成缺口,覆盖成型/基座分支)∧ 板满(空位帧由
    M1 通道直上)。成型腿键 ⊆ 阵容视图键 ⇒ 目标视图成员资格由判据本体
    蕴含,不另设第二份视图过滤(双源禁)。空集 = 通道关(fail 向不换)。

    出处 = 2026-09-18 sim 实证:配方对锁局板满帧全 plan_empty,配方
    完成件压席无解(必需件分支只覆盖 required_deployed 成员,桥池 pair
    required 恒空);玩法口径 = 口述条目 20(登记簿已退役)/[13]。
    """
    if ctx is None or not ctx.board_full:
        return frozenset()
    if not getattr(ctx, 'locked', False):
        return frozenset()   # 方向锁不在效帧通道关(未锁/未对锁语义照旧)
    comp = ctx.target_comp
    if comp is None:
        return frozenset()
    fp = getattr(ctx, 'fp', None)
    if fp is None or fp >= 1.0:
        return frozenset()   # 成型帧无完成缺口;fp 缺读 = 判据不可得,关
    names = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    out: set[str] = set()
    for b in (ctx.bench or []):
        m = _bench_cid(b)
        if not m or m in names:
            continue   # 同名在板:真上序被 name_dup 恒留置,入选无意义
        hyp = names | {m}
        panel = _HypotheticalPanel(deployed_bond_counts(hyp), hyp)
        if form_progress(comp, panel) >= 1.0:
            out.add(m)
    return frozenset(out)


def _swap_victim_yields_for_swap_in(ctx: SwapPlanContext, name: str) -> bool:
    """victim 让位总检验(消费位 = swap_sell_exclusion_reason 让位门)。

    = 必需件 hold(假想面板 victim 离场 ∧ required 全体按已换入
    计,判据满)∨ 完成件 hold(∃ 完成件 M:victim 离场 ∧ M 入板后判据
    满)。两 hold 同一折法(form_progress 假想面板)——让位当且仅当
    「换入后判据 ✗→✓ 或不下坠」,否则凑齐倒退不可换。
    """
    if _required_swap_victim_completion_holds(ctx, name):
        return True
    comp = ctx.target_comp
    if comp is None:
        return False
    ins = _completion_swap_ins(ctx)
    if not ins:
        return False
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    names = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    for m in sorted(ins):
        hyp = (names - {name}) | {m}
        panel = _HypotheticalPanel(deployed_bond_counts(hyp), hyp)
        if form_progress(comp, panel) >= 1.0:
            return True
    return False


def _seat_completes_form(ctx: SwapPlanContext, victim: str,
                         up_name: str) -> bool:
    """卖后落位复检:up_name 真入板(该 victim 离场)后成型判据满。

    卖后上序底线专用,与候选集判定(``_completion_swap_ins``)互补:候选
    集只证「该件有完成能力」,不绑定 victim 成对——「候选普通成员占位、
    完成件仍滞留」的白卖形态须按计划的实际 (victim, up) 对折算在此拒。
    同名在板件 = 真上序被 name_dup 留置,落位不发生,恒 False。
    """
    comp = ctx.target_comp
    if comp is None or not up_name or up_name == victim:
        return False
    names = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    if up_name in names:
        return False
    from sr_od.application.currency_war.kernel.cw_comps import form_progress
    hyp = (names - {victim}) | {up_name}
    panel = _HypotheticalPanel(deployed_bond_counts(hyp), hyp)
    return form_progress(comp, panel) >= 1.0


def _swap_star_and_merge_guards(name: str, ctx: SwapPlanContext, *,
                                star: int | None = None,
                                bench: list | None = None,
                                deployed: list | None = None) -> str:
    """1★ 限卖(star_guard)+ 合成素材守卫(域共吃段;禁第二实现)。

    两域(转型域门 2 / 域外现行资格族)同吃本段,守卫语义逐位同旧:
    star_guard 在演进降级换人分支武装帧对可读星级 >1 让位(arm =
    ``SwapPlanContext.evolution_swap_armed``,谓词单一源 =
    ``evolution_swap_arm_trigger``);星级不可读恒拒(fail 向不换,武装
    不豁免——不可判星级 = 不可判弱序,分级序的排序输入缺失)。
    合成素材守卫按同名同星全场域计数(含自身,``cw_state.same_star_count``
    单一源)= 2 未完态拒。

    **演进降级排除(design 2026-10-26-swap-channel-unified §2.8 堵回
    降口一)**:武装释放面不豁免终局键集标签命中件——降级换人无门 1
    组级收益约束,标签件(未来板面成员)经此通道离场会破坏「板上标签
    命中件唯一离场通道 = 配对骨架换人且组级支撑数净非降」的不变式前提
    (§2.8 段一);辖域 = 武装释放面本身(star>1 腿),1★ 标签件的资格
    归各域自有机器(转型域 = 门 2 白名单通道 2,不属演进分支资格面)。
    拒因沿用既有键 ``star_guard``(资格族闭集不扩,mandate 逐件分键
    闭集零改)。
    """
    _deployed = deployed if deployed is not None else ctx.deployed
    _bench = bench if bench is not None else ctx.bench
    star_eff = star if star is not None else next(
        (x.star for x in _deployed
         if x is not None and (x.char_id or '') == name), None)
    star_n = star_eff or 1
    if star_eff is None or (star_n > 1
                            and not getattr(ctx, 'evolution_swap_armed',
                                            False)):
        return 'star_guard'   # 星级不可读/非 1★ = fail 向不换(出战就绪让位见上注)
    if star_n > 1 and (_bonds_named(name)
                       & getattr(ctx, 'bond_gate_keys', frozenset())):
        # 走到此处 = 武装释放面(star>1 ∧ evolution armed):标签命中件
        # 不获释放(design §2.8 堵回降口一,拒因沿用 star_guard 键)。
        return 'star_guard'
    from sr_od.application.currency_war.kernel.cw_vocab import same_star_count
    if same_star_count(name, star_n, _bench, _deployed) == 2:
        return 'merge_material_guard'
    return ''


def _bond_gate_same_star_up_available(ctx: SwapPlanContext, name: str) -> bool:
    """让位通道 3(a) 可用性:bench 存在同名牌且星级严格升(design §2.2/§2.7)。

    门 1③ 谓词钉死的前半:换入件与被换件**同名**(必要条件——异名星级
    升换属 E 类无结构收益,不构成 3(a))∧ 换入件星级严格升。victim 星级
    从板上现读(缺读按 1 计,与 star_guard 同向)。
    """
    victim_star = next((x.star for x in ctx.deployed
                        if x is not None and (x.char_id or '') == name), None)
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    for b in (ctx.bench or []):
        if b is None:
            continue
        if _bench_cid(b) != name:
            continue
        up_star = getattr(bench_slot_unit(b), 'star', None)
        if (up_star or 1) > (victim_star or 1):
            return True
    return False


def _bond_gate_victim_reject(name: str, bonds: set[str], ctx: SwapPlanContext,
                             *, star: int | None = None,
                             bench: list | None = None,
                             deployed: list | None = None) -> str:
    """转型域 victim 资格(门 2;design §2.2/§2.2.1 让位语义)。

    身份保护面 = 终局名单成员 ∪ 保护集(fw_carry) ∪ 替班契约件
    (现行 P41②/P78 保护语义 + 「替班=不卖」契约 C4 照旧):
    - fw_carry:恒拒 target_keep(对称排除照旧);
    - 替班契约件(protect_names − 名单):恒拒 target_keep——替班件不因
      白名单沦为 victim(design §2.2.1 身份保护面钉死);
    - 名单成员:仅两条让位通道——3(a) 同名升星横换(门 1③ 同名必要)/
      3(b) 分支 hold 让位(必需件/完成件 hold 现行检验,含量席让位语义);
    非名单:**让位白名单取代阵营视图恒拒**(C1 解锁点)——
    - 纯过渡件(终局键集零标签命中):通道 1,一级 victim;
    - 终局标签支撑件(非名单):通道 2,二级 victim。
    守恒面域切分(design §2.3):本域**无逐件守恒门**——engines_guard 的
    守恒职由组级「终局档位非降」承接(组换后板态口径 = 门 1① 档位面
    同一函数,禁逐件第二份折法);star_guard/素材守卫照旧(域共吃段)。
    义务集拒(buy_membership)已在调用侧按路径域豁免(转型域换人让位
    路径整体豁免,design §2.2)。
    """
    if name in ctx.fw_carry:
        return 'target_keep'   # fw_carry 对称排除
    members = frozenset(getattr(ctx, 'k_members', ()) or ()) \
        or frozenset(ctx.target_cores)
    if name in ctx.protect_names and name not in members:
        return 'target_keep'   # 替班契约件:恒拒(替班=不卖契约 C4)
    if name in members:
        # 名单成员:仅两让位通道(design §2.2.1 通道 3)
        if not (_bond_gate_same_star_up_available(ctx, name)
                or (required_swap_arm_pending(ctx)
                    and _swap_victim_yields_for_swap_in(ctx, name))):
            return 'target_keep'
    # 非名单:白名单通道 1/2 自动成立(纯过渡件一级/标签支撑件二级;
    # 键集标签命中与否只影响两级序分层,不影响资格)。
    return _swap_star_and_merge_guards(
        name, ctx, star=star, bench=bench, deployed=deployed)


def swap_sell_exclusion_reason(name: str, ctx: SwapPlanContext | None, *,
                               star: int | None = None,
                               bench: list | None = None,
                               deployed: list | None = None,
                               ) -> str:
    """卖出 victim 的单一判定(逐件;转型域双门 + 域外现行机器)。

    消费面 = 动作发出面谓词(mandate m1p 换人分支 ``select_swap_plan`` 调用面);
    机械执行侧 ``CwActionSellDeployedOp`` 不消费本函数(执行侧现役零调用,
    原部署机卖出分支消费面已停用)——卖出通道统一排除适用范围 +
    **逐件可卖性**
    的唯一交汇点(内聚声明:守恒门/合成素材守卫/转型域判别子的消费点
    全部落回本函数或其唯一调用链,新资格族语义只在此实现一次,
    发出⇔执行资格自动同值,禁分轨态)。

    返回 '' = 可卖。拒因闭集:
    - 排除族:membership_unreadable / buy_membership / fresh_buy。
      **义务集面域切分**(design §2.2):``locked_buy_membership`` 拒卖腿
      在转型域换人让位路径**整体豁免**(让位白名单三通道全免;豁免依据 =
      §2.8 段一四腿各自蕴含的净非降承接义务集保护意图);来金/演进/
      普通卖出通道不豁免(本函数只辖换人路径);membership **缺读**
      (None)弃权保留在前(fail-closed);
    - 资格族(per-piece):target_keep / fenced_arm_closed /
      engines_guard / merge_material_guard / star_guard / fp_unreadable。
      star_guard 辖域含演进降级排除(§2.8 堵回降口一):武装释放面对
      终局键集标签命中件不豁免(拒因沿用本键,见
      ``_swap_star_and_merge_guards`` 节注)。
      **转型域**(判别子 = ``swap_bond_gate_domain`` 三合取)内走门 2
      白名单(``_bond_gate_victim_reject``):fenced 与否统一由门 1(组态
      收益,组级)与门 2 其余资格面裁定(锁定帧行为延续,design
      §2.3.1);守恒面由组级档位非降承接,逐件不设第二折法。
      **域外**(未锁帧/配方对锁 pair 帧/成型帧)现行机器逐位照旧:
      基座/成型分支经 ``offtarget_sell_allowed`` 参数化接入(本体零修改);
      fenced 关门分支域腿钉死混轨语义(design §2.3.1 真值表,表达式
      内联脱钩退役符号)——pair 帧 locked ∧ fp<1.00 ∧ 板满开门落资格族
      (engines_guard/star_guard/素材守卫照常消费,禁判别子统一换装
      造成双轨域静默跳过),未锁/成型帧关门拒因照旧。

    :param star: victim 星级覆盖(执行侧 SIFT 现读喂入;None = 从
        deployed 域按名回查;仍不可得 = star_guard 拒,fail 向 = 不换)。
    :param bench: 全场域计数用 bench 域覆盖(执行侧 SIFT 现读喂入;
        缺省用 ctx.bench)。合成素材守卫按同名同星全场域计数(含自身,
        ``cw_state.same_star_count`` 单一源)。
    :param deployed: 同上 deployed 域覆盖(守恒门/希儿系/星级回查域)。
    """
    if ctx is None or not name:
        return ''
    if ctx.membership is None:
        return 'membership_unreadable'
    _bond_gate = swap_bond_gate_domain(ctx)
    # 义务集面域切分(转型域换人让位路径整体豁免;design §2.2/§2.8):
    # 白名单三通道的 victim 均豁免义务集拒——按通道枚举豁免(仅 1/2)
    # 会使名单成员让位通道不可达,与枚举表 D/§2.7 矛盾,故裁路径域豁免。
    if not _bond_gate and name in ctx.membership:
        return 'buy_membership'
    if name in ctx.fresh_buys:
        return 'fresh_buy'
    # ---- 逐件资格(基座/成型分支经 offtarget_sell_allowed 参数化接入)----
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        offtarget_sell_allowed,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return ''   # 未注册件不可判羁绊(调用面均已先剔除,防御缺省照旧)
    bonds = set(ch.factions) | set(ch.flows)
    if _bond_gate:
        # 转型域:门 2 白名单(design §2.2.1;义务集已豁免,见上)。
        return _bond_gate_victim_reject(
            name, bonds, ctx, star=star, bench=bench, deployed=deployed)
    _fp = getattr(ctx, 'fp', None)
    _locked = bool(getattr(ctx, 'locked', False))
    if offtarget_sell_allowed(name, bonds, set(ctx.target_factions),
                              set(ctx.target_cores),
                              fenced_offline_sellable=ctx.fenced_on,
                              protect_names=ctx.protect_names):
        if not _locked:
            return ''   # 未锁帧基座/成型分支语义照旧
        if _fp is None:
            return 'fp_unreadable'   # 锁定帧 fp 缺读两分支同弃权
        if not fenced_swap_gate_open(_locked, _fp, ctx.board_full):
            return ''   # 成型帧(fp≥1.00)/板不满帧:成型分支语义照旧(方案 §2.3 不动)
        # fenced 开门帧(混轨 locked ∧ fp<1.00 ∧ 板满;pair 双轨帧在此形态)
        # 释放件:落下方资格族——pair 帧守恒门(engines_guard/star_guard/
        # 素材守卫)照常消费(design §2.3.1 pair 路由钉死①,禁静默跳过)。
    else:
        # 板满换入分支(target 单位分支判定先行;fence 键集适用范围 ≠ target
        # 键集适用范围——量子/贝成员不在 DEPLOY_FENCE 而在 pair target 键集,
        # 旧「先查 fence 后查 target」次序会把量/贝 target 件挡在分支外):
        # 分支候选排除保护域扩展集(protect_names − target_cores =
        # shared ∪ 替班):P41② 禁卖护栏不因换阵解除 + ``Comp.
        # substitute_plan``「替班=不卖」字段契约。core 成员(本就在
        # target_cores)不经此排除——判据必需件优先的本体 = 冗余 core
        # 件让位(20260915 sim 找问题报告问题 2 形态:量3 过剩档,
        # 卖一量席换入希儿 = form ✗→✓ 严格优),其安全性由判据保持
        # 检验(离场不破成型)承载,非护栏豁免。
        if name in (set(ctx.protect_names) - set(ctx.target_cores)):
            return 'target_keep'
        is_target_member = bool(
            bonds & set(ctx.target_factions) or name in ctx.target_cores)
        if is_target_member:
            # 换入分支(判据必需件/完成件优先于非必需板件):pair/静态套
            # 判据以 required_deployed 在板为必要条件(``Comp.required_
            # deployed`` 字段契约 + seele_system_formed 合取支),必需件
            # 滞留 bench ∧ 板满 = 结构性凑齐失败形态(sim n1000 s91700
            # 基线 12 失败希儿系局主形态);双轨对锁期扩展 = 配方完成件
            # 滞留(桥池 pair required 恒空,``required_swap_arm_pending``
            # 完成分支)。victim 让位条件 = 假想面板(victim 离场 ∧
            # 换入件按已换入计)下成型判据仍满——破坏 = 凑齐倒退不可换;
            # 保持 = 换入后判据 ✗→✓ 严格优(支配改进,无新数值参数)。
            # 让位后落资格族(engines_guard/star_guard/merge 素材守卫
            # 照走,禁直落 fenced 关门分支——target 件非该分支适用范围)。
            if not (required_swap_arm_pending(ctx)
                    and _swap_victim_yields_for_swap_in(ctx, name)):
                return 'target_keep'   # target 单位(offtarget 拒因归因,先于分支)
        elif not bonds & DEPLOY_FENCE:
            return 'target_keep'
        elif not fenced_swap_gate_open(_locked, _fp, ctx.board_full):
            # fenced 关门分支(域腿钉死混轨;design §2.3.1 真值表):
            # 未锁帧 → 关;锁定 ∧ 成型帧(fp≥1.00)→ 关;锁定 ∧ 板不满 → 关;
            # 锁定 ∧ fp 缺读 → fp_unreadable(fail-closed 同向)。
            if not _locked:
                return 'fenced_arm_closed'
            if _fp is None:
                return 'fp_unreadable'   # fp 缺读两分支同弃权(fail-closed)
            return 'fenced_arm_closed'   # 成型帧 ∨ 板不满 → 分支关
        # fenced 开门帧(pair 双轨帧)fenced off-line 件:落资格族
        # (与释放件同族;design §2.3.1 pair 路由钉死①)。
    if name in ctx.fw_carry:
        return 'target_keep'   # fw_carry 对称排除
    _deployed = deployed if deployed is not None else ctx.deployed
    _bench = bench if bench is not None else ctx.bench
    _names = {x.char_id for x in _deployed if x is not None and x.char_id}
    # ---- 档位守恒门:逐体系 achieved 档数不减(域外双轨/既有域原样;
    # 转型域守恒职已切至组级档位非降,不经此处,design §2.3)----
    _fac = deployed_bond_counts(_names)
    _fac2 = deployed_bond_counts(_names - {name})
    _ach_b = _swap_guard_achieved(_fac, _names)
    _ach_a = _swap_guard_achieved(_fac2, _names - {name})
    if any(_ach_a[k] < _ach_b[k] for k in _ach_b):
        return 'engines_guard'
    return _swap_star_and_merge_guards(
        name, ctx, star=star, bench=bench, deployed=deployed)


@dataclass
class SwapPlanContext:
    """swap 计划谓词的共享输入快照(装配函数产物;发出/执行同契约消费)。

    字段语义与装配源:
    - ``target_factions``/``target_cores``:target 视图(双轨口径,装配
      内经 committed_from→decision_target 伪阵容链,与执行侧卖出决策
      同一条链)= all_factions 全量(键集收窄已随转型分支机器退役,
      design §2.3.1;域分流消费转型域判别子与 ``bond_gate_keys``)——
      消费位同吃本字段,单一源;
    - ``bond_gate_keys``:终局键集(design §2.1 键集来源 =
      ``Comp.form_tiers`` 键)——门 1① 档位梯计数/守恒档位面/支撑件
      判定的键域单一源;form_tiers 本体仍承担成型判据(readiness_form_ok
      现行不动)与门 1④ 折法(form_progress),档位梯单源 = cw_factions
      FACTIONS tiers 逐档(bond_gate_tier_profile),**不做梯子**;
    - ``k_members``:终局名单(core ∪ shared;与 mandate_v1
      ``predicates.line_members`` 同构同值,等价性由测试钉住)——
      支撑件并集视图/让位白名单通道 3 的名单单一源;
    - ``membership``:买面义务排除集(单一源 = ``cw_intention.
      locked_buy_membership`` 容量可行截断集 B',cap_hold 现读;与 M4
      燃料集 ``exclude_names`` 同参同源——两侧同吃 B');
      None = 缺读(谓词弃权,fail-closed);未锁定帧 = 空集(无锁定帧
      不存在 hoard 义务,非缺读);转型域换人让位路径对该拒卖腿
      **整体豁免**(design §2.2,豁免依据 = §2.8 段一净非降);
    - ``fresh_buys``:轮内新鲜度排除名集(见 ``fresh_buys_of``);
    - ``fenced_on``:换阵卖出义务分支态(fenced off-line 件可卖与否)。
    """
    target_factions: frozenset[str]
    target_cores: frozenset[str]
    fw_carry: frozenset[str]
    locked_factions: frozenset[str]
    protect_names: frozenset[str]
    membership: frozenset[str] | None
    fresh_buys: frozenset[str]
    board: dict[str, int]
    deployed: list[Unit]
    bench: list[BenchSlot]
    cap: int | None
    front_slots: int = DEPLOYED_FRONT_CAPACITY
    back_slots: int = DEPLOYED_BACK_CAPACITY
    fenced_on: bool = False
    #: 成型度单一源快照(form_progress;None = 缺读 ⇒ 资格面 fp_unreadable
    #: 弃权,两分支同 fail-closed)。发出⇔执行同函数装配 ⇒ 同帧同值。
    fp: float | None = None
    #: 换人域方向锁 = 终局阵容锁定 ∨ P1 配方对锁(装配单一源 =
    #: ``assemble_swap_plan_inputs``;配方对锁语义见 strategy-docs/
    #: 24_deploy_segment.md 换人节)。终局阵容锁定判定本身单源仍归
    #: strategy-docs/17_stall_form_spend_authority.md §1.1(两词显式分名,
    #: 禁按本字段反推终局阵容锁定口径)。
    locked: bool = False
    #: 方向锁腿①(终局阵容锁定,显式不含 P1 配方对锁腿②)——转型域
    #: 判别子第一腿的装配源(design §2.0;判定权威 = 锁定线槽非空)。
    #: 与 ``locked``(混轨)并存各有辖域:混轨供 fenced 关门分支/
    #: evolution 触发等既有域,本字段供转型域判别子,禁互借。
    locked_core: bool = False
    #: 终局键集(design §2.1 键集来源 = ``Comp.form_tiers`` 键;见类注)。
    bond_gate_keys: frozenset[str] = frozenset()
    #: 终局名单(core ∪ shared;与 predicates.line_members 同构,见类注)。
    k_members: frozenset[str] = frozenset()
    #: 板满(占用数 ≥ cap,与 fenced 分支同一派生链;换人域触发前提之一)。
    board_full: bool = False
    #: 锁定线语境豁免武装位(配方底线门):装配自
    #: ist.locked_comp(经 cw_intention.locked_line_recipe_floor_conflict,
    #: 与 ``locked`` 同点同源装配——发出⇔执行⇔sim 意图三面经同一装配
    #: 同帧同值)。缺省 False = swap 上序(卖后假想态复用
    #: select_deployments_reasoned)行为逐位同旧。
    recipe_floor_lock_exempt: bool = False
    #: 装配实际消费的 target 阵容视图本体(双轨口径:双轨期 =
    #: decision_target 伪阵容,定型后 = strategy_state.target_comp;
    #: None = 手装 ctx/装配缺读)。消费面 = mandate 部署执行放行判定的
    #: 档关键件判读源(审查判读源与本计划的阵容同源,禁放行判定
    #: 另读 state_of 二份——双轨帧两源可分歧,判据源分裂 = 同型分叉)。
    target_comp: object | None = None
    #: 演进降级换人分支武装位(缺省 False = 逐位同旧;装配函数单点计算,
    #: 执行侧 bench 域分轨面经 :func:`evolution_swap_arm_trigger` 现读
    #: 重算覆写)。True 时 :func:`swap_sell_exclusion_reason` 的
    #: star_guard 对可读星级 >1 的 victim 让位——演进层 分级
    #: 降级换人语义(弱序星级→费用)接入换人机制的参数化面,适用范围 =
    #: 锁定转型域 ∧ 板满 ∧ bench 已登记线件待上(
    #: 语义宿主 = kernel.cw_evolution 的分级保护机器(该模块已停用),本分支不新增
    #: 资格语义,只放开既有 1★ 限制并以其余守卫全保留为界)。释放面
    #: **不豁免终局键集标签命中件**(演进降级排除,design
    #: 2026-10-26-swap-channel-unified §2.8 堵回降口一,拒因沿用
    #: star_guard;见 ``_swap_star_and_merge_guards``)。
    evolution_swap_armed: bool = False
    #: 判据必需件名集(装配单一源 = 目标阵容 ``required_deployed``;与
    #: mandate_v1 deploy_plan ``_deploy_plan_inputs`` 同源同值)。消费面 = select_swap_plan
    #: 卖后上序(必需件首桶,使「卖了换人后」的首个空位优先落必需件——
    #: 不穿则换人腾出的位仍会被普通成员按旧序占走)、
    #: ``swap_sell_exclusion_reason`` 的板满换入分支;执行侧卖出后补部署
    #: 重 derive 已停用,现役归 m1p 发出分支逐件产原子 + 环内重 derive。
    required_names: frozenset[str] = frozenset()


# ===== 换阵可兑现谓词(F1 单一源;发出-执行接缝合拢)=====
# 语义出处:无方向幻影部署软卡死事故。
# 为什么存在:动作发出面(select_swap_plan)与执行面(原部署机卖出分支两门,
# 已停用)对「这场换阵能否兑现」判定不同源时,动作发出面会发出执行面
# 必然空转的 RunDeploy(2026-09-08 实机软卡死 run_20260908_210431:无方向态
# 发出 53 次幻影部署,执行 0 次真实换阵,交替活锁 15 分钟)——本谓词是
# 「发出⇔执行同谓词」的单一实现,两面各消费其合取支,禁任一面自写
# 第二份口径。支出出口总图防双改清单的共享单点对账持久家(推导 历史)
# 本谓词消费 form 成型度(fp 经装配 ctx 单字段)与
# victim 资格(swap_sell_exclusion_reason)两个已登记共享单点,零新增
# 派生链——只消费装配 ctx(SwapPlanContext)字段,禁第二份 fp/目标视图
# 派生。

#: swap_realizable 拒因闭集(plan 级弃权键;层位 = plan 级弃权键,
#: 非逐件拒因闭集——后者见 swap_sell_exclusion_reason docstring)。
SWAP_REALIZABLE_WHY: tuple[str, ...] = (
    'no_direction', 'no_bench_target', 'no_sellable_offtarget',
)


def target_view_present(ctx: SwapPlanContext | None) -> bool:
    """合取①:目标视图非空(阵营视图 ∪ 核心件任一非空)。

    为什么含 core:目标视图 = cores ∪ factions 双字段(cw_comps 口径,
    白厄类空羁绊单卡阵容只有 core_chars)——只看 factions 会把
    「有方向(核心件)」误标 no_direction;执行面旧门只看 factions 是
    同族窄口径,一并收敛(有向 core-only 帧卖出分支从结构性关闭
    变为可开门,方向同收束语义,的伴随申报面)。
    """
    return ctx is not None and bool(ctx.target_factions or ctx.target_cores)


def target_view_char_is(ctx: SwapPlanContext, char_id: str) -> bool:
    """单件目标视图判定(收束后唯一实现;fw_carry 口径 = **含**)。

    fw_carry 收束依据(择一裁决,申报持久家):①上序裁判
    select_deployments 的 is_tgt 判定含 fw_carry(本文件 :474,框架件
    r120 起是部署一等公民)——为 fw_carry 件腾位是可兑现的换阵,执行面
    不认它则发出⇔执行再次分叉;②卖出侧 swap_sell_exclusion_reason 对
    fw_carry 板件同样 target_keep 保护(对称排除)——同口径
    才自洽;③旧执行面 _is_tgt_char 不含 fw_carry 正是本次收敛要消灭的
    「同一判据两份实现」病样本,收束 = 向 kernel 口径(含)对齐。
    有向态行为变化面(如实申报):执行面 max_sell 上限自此计 fw_carry
    bench 件,可多卖一件 off-target 为其腾位——腾位对象是上序真会部署
    的件,方向安全(用例预期更新随实现同步)。
    """
    cid = char_id or ''
    if cid in ctx.target_cores or cid in ctx.fw_carry:
        return True
    ch = CHARACTERS.get(cid) if cid else None
    return ch is not None and bool(
        (set(ch.factions) | set(ch.flows)) & ctx.target_factions)


def support_view_char_is(ctx: SwapPlanContext, char_id: str) -> bool:
    """支撑件并集视图(转型域 up 侧 target 视图判据单一源;design §2.1/§2.7)。

    = 终局名单成员(k_members,无条件计入)∪ 羁绊标签命中终局键集
    (``bond_gate_keys``)的外部件(按标签计入)。消费面(三消费位,
    design §2.7 钉死):组贪心的换入候选池过滤/逐对底线(up ∈ 支撑件
    视图,``post_sell_offline``)/``select_deployments is_tgt``(经组
    贪心 select_up 调用的 target 视图参数映射 = 键集 + 名单,同一口径
    的参数化表达)。与 ``target_view_char_is`` **并存各有辖域、禁交叉
    引用**(两处域外消费位——``bench_target_count`` 合取②域外活、
    mandate 放行门对锁期读法——照旧挂旧视图,改本体 = 未申报行为差)。
    """
    cid = char_id or ''
    if cid in ctx.k_members:
        return True
    ch = CHARACTERS.get(cid) if cid else None
    return ch is not None and bool(
        (set(ch.factions) | set(ch.flows)) & ctx.bond_gate_keys)


def terminal_key_label_hit_names(
        bond_gate_keys: frozenset[str] | set[str]) -> frozenset[str]:
    """终局键集标签命中件名集(全注册表;design §2.1 标签命中判据的
    集合形态单一源)。

    谓词 = 单位羁绊标签(factions ∪ flows,读法单一源 = ``_bonds_named``,
    与 ``support_view_char_is`` 同式)命中键集即计入——**不看是否已承载
    激活档位**(design 2026-10-26-swap-channel-unified §2.8 排除谓词
    语义钉死:现行 ``is_field_irrelevant_unit`` 仅资格级覆盖「有已达成
    档」件,本集合盖住无档标签件的泄露面——义务基座按费用序截断〔B′〕
    可把非名单标签件裁出保护面,来金通道即由此泄露);名单成员命中亦
    计入 = 冗余兜底(义务集已保,无害)。键集空(未锁定帧无终局键集)
    恒空集,谓词零面。教义锚:「哪怕下远坂凛都不能拆能量」(cw_comps.py
    双王圣杯 branch_key 注记)——标签命中一律保护,bench 标签件为未来
    板面成员同受保护。

    消费面 = sell_gate 装配 A 身份段(来金族资格增补排除,design §2.8
    堵回降口二);禁消费位自建第二份集合口径。
    """
    keys = set(bond_gate_keys)
    if not keys:
        return frozenset()
    return frozenset(n for n in CHARACTERS if _bonds_named(n) & keys)


def bench_target_count(ctx: SwapPlanContext | None, *,
                       bench: list | None = None) -> int:
    """合取②(计数形态):bench 目标视图件数(>0 即合取②成立)。

    :param bench: 域覆盖(执行面 SIFT 现读喂入;缺省 ctx.bench 帧)。
      与 swap_sell_exclusion_reason 的 bench 覆盖参同规(同函数异参、
      输入源两侧分轨,装配源契约)。
    """
    if ctx is None:
        return 0
    _bench = bench if bench is not None else ctx.bench
    return sum(1 for b in _bench
               if target_view_char_is(ctx, _bench_cid(b)))


def board_sellable_offtarget_exists(ctx: SwapPlanContext | None, *,
                                    deployed: list | None = None,
                                    ) -> bool:
    """合取③:板上存在其资格分支下可卖的 off-target 件。

    逐件判定 = swap_sell_exclusion_reason 单一源(返 '' = 该件在当前
    分支态下可卖且必为 off-target——target 视图件被该函数 target_keep
    拒,语义内含)。未识别/未注册件不入候选(select_swap_plan victim
    扫描同款:不可判羁绊即不可判资格)。与动作发出面 victim 扫描同构同源,
    差异仅在输入域(动作发出面 ctx 帧域 / 执行面 SIFT 现读域,分轨既定)。
    """
    if ctx is None:
        return False
    _dep = deployed if deployed is not None else ctx.deployed
    for d in _dep:
        name = getattr(d, 'char_id', '') or ''
        if not name or CHARACTERS.get(name) is None:
            continue   # 未识别/未注册件不可判羁绊,不入候选(扫描同款)
        if swap_sell_exclusion_reason(name, ctx, deployed=_dep) == '':
            return True
    return False


def swap_realizable(ctx: SwapPlanContext | None, *,
                    bench: list | None = None,
                    deployed: list | None = None,
                    ) -> tuple[bool, str]:
    """换阵可兑现谓词(三合取;发出⇔执行同吃,F1 单一源)。

    realizable ⟺ ①目标视图非空 ∧ ②bench 存在目标视图件 ∧ ③板上存在
    其资格分支下可卖的 off-target 件(钉死的
    三合取;原「fenced 分支开 ∨ bench 存在目标视图件」形态
    会使执行面卖出分支在
    「fenced 开 ∧ bench 无目标件」帧仍跳过,发出⇔执行在有向成型态再次
    分叉,故改写)。

    消费面与合取支的对应:
    - 动作发出面(select_swap_plan)门①显式弃权(abstain no_direction);门②
      域外(非锁定转型域)显式弃权(abstain no_bench_target)——转型域
      跳过门②:转型分支自带更强的卖后上序底线(post_sell_offline),计划
      非空 ⟹ up2 含 target 视图件 ⟹ bench 必有目标视图件,门②被底线
      蕴含,预判只会把逐件暴露挤成单键;门③由 victim 扫描自然承载
      (逐件同判 swap_sell_exclusion_reason,扫描空即计划空,语义等价
      且逐件拒因保留暴露);
    - 执行面(原部署机卖出分支两门)已停用,现役零执行侧消费——
      机械执行 = `CwActionSellDeployedOp` 逐件原子,资格判定全部前移动作发出面;
    - sim 镜像经 select_swap_plan 自动继承。

    :returns: (ok, why)。why ∈ SWAP_REALIZABLE_WHY(拒因闭集)或 ''
        (ok=True)。ctx None 按无方向弃权(fail-closed,与装配不可得
        「不静默发出」同向)。
    """
    if not target_view_present(ctx):
        return False, 'no_direction'
    if bench_target_count(ctx, bench=bench) == 0:
        return False, 'no_bench_target'
    if not board_sellable_offtarget_exists(ctx, deployed=deployed):
        return False, 'no_sellable_offtarget'
    return True, ''


@dataclass
class SwapPlan:
    """swap 计划(卖序 + 上序 + 逐件拒因;空计划 = 两序空)。

    ``arm`` = 胜出 victim 的资格族标注(:'' = 空计划 / 'base' =
    基座合格 / 'formed' = 成型分支(fenced_on)/ 'transition' = 双轨域
    转型分支标注(pair 帧,现行保留,design §2.3.1)/ 'bond_gate' =
    转型域双门组计划)。
    计划形态分域:域外(未锁/pair 双轨帧)= **单对计划形态**(现行:
    sell_names/up_bench = 单 victim 及其卖后上序);转型域 =
    **多对组计划形态**(本迭代新建,design §2.7:第 k 对 =
    (sell_names[k], up_bench[k]),1:1 配对骨架,序参数经
    ``SwapGroupOrder`` ports 注入)。域外胜出序 = victim 序首个可成交者,
    arm 只随胜出者标注;转型域组 = 最小充分组贪心的首个可行组。
    组计划附加字段:``bond_gate_leg``(accept 分键首达腿,值域 =
    tier/support/star/completion)/``victim_tier``(首对 victim 层来源,
    值域 = 一级/二级/名单末位)/``bond_gate_reject``(拒绝侧分键来源,
    值域 = nogain/conservation/novictim,非空 = 转型域计划空)。
    """
    sell_names: list[str] = field(default_factory=list)
    up_bench: list[int] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    abstain: str = ''
    arm: str = ''
    #: 门 1 首达腿(accept 分键源;'tier'/'support'/'star'/'completion')
    bond_gate_leg: str = ''
    #: 首对 victim 层来源('一级'/'二级'/'名单末位')
    victim_tier: str = ''
    #: 转型域计划空时的拒绝侧分键来源('nogain'/'conservation'/'novictim')
    bond_gate_reject: str = ''

    @property
    def nonempty(self) -> bool:
        return bool(self.sell_names) and bool(self.up_bench)


def swap_plan_up_names(plan: SwapPlan | None,
                       ctx: SwapPlanContext | None) -> list[str]:
    """``SwapPlan.up_bench`` 下标 → 备战名单(名字级单一换算)。

    ``up_bench`` 元素是 ``ctx.bench``(**装配时点紧缩占用序**)的下标、
    非名字(F3:消费面按对象断言会脆,必须先换名再核对/记录)——本
    函数是该换算的唯一实现,记录面(sim ``_m1p_plan_and_record`` 的
    ``up_names``)与发出载荷面(mandate ``cw4_m1p_plan_pending['up']``)
    同吃,禁消费位各写第二份下标换算。越界下标跳过(防御,装配⇔消费
    同 ctx 引用时不可达)。
    """
    if plan is None or ctx is None:
        return []
    bench = getattr(ctx, 'bench', None) or []
    return [_bench_cid(bench[i])
            for i in plan.up_bench if isinstance(i, int) and 0 <= i < len(bench)]


def evolution_swap_arm_trigger(membership: frozenset[str] | None,
                               bench: list | None, *,
                               locked: bool,
                               fp: float | None,
                               board_full: bool) -> bool:
    """演进降级换人分支触发谓词(纯函数,语义)。

    最小等效通道的准入面:「锁定转型域 ∧ 板满 ∧ bench 有已登记线件待上」
    (修向「板满∧bench有locked线core→发出卖线外件上core事务」
    的准入三元)。两面消费(装配级缺省计算 = 动作发出面 mandate M1″,sim 与
    实机同链共用;原执行侧 SIFT 现读重算覆写轨已停用,机械执行侧
    `CwActionSellDeployedOp` 不消费本函数)——同函数同谓词,消费面资格
    自动同值,禁分轨态
    (同款纪律)。

    各腿单一源与 fail-closed:
    - ``locked``/``fp``/``board_full`` = 装配 ctx 同源字段(fp 缺读 =
      分支关,与转型分支 fp_unreadable 两分支同弃权口径一致;
      fp≥1.00 = 线已成型无完成缺口,分支适用范围外);
    - ``membership`` = ``cw_intention.locked_buy_membership``(锁定帧
      采购集正典口径,与 M4 燃料集/卖出义务排除同参同源;None = 缺读
      分支关)。bench 待上判定用买面义务集而非部署面 line_members:
      集合构成声明 = 存-2 裁决两口径分域的已登记复用(entry.emit 装配
      注),本分支不新增第三口径;
    - 「已登记 core 待上」= bench 占用件名 ∈ membership(采购集=线名册
      全集,含 core∪shared∪替班;能否真上场不由本谓词答——上序裁判 =
      select_swap_plan 的卖后 select_deployments 底线,结构性排除
      「白卖」形态)。

    与转型域谓词的对账声明(design §2.3.1 域腿钉死):本谓词**维持现行
    混轨语义不迁移**——准入三元含 pair 帧(腿②)为现行已验证形态,
    迁移 = 未申报行为差;该谓词非退役符号,与 fenced 关门分支域腿
    (``fenced_swap_gate_open``,同款混轨三腿)同形并存,申报为
    「并存已申报形态」,零行为差;域定义变更时本谓词须随其对账,
    禁静默分叉。

    :param bench: bench 域(None 缺省 = 空域分支关);动作发出面 = 决策帧
        黑板,执行面 = SIFT 现读(装配源契约的既定分轨)。
    """
    if not locked or fp is None or fp >= 1.0 or not board_full:
        return False
    if not membership:
        return False
    return any(_bench_cid(b) in membership
               for b in (bench or []) if b is not None)


def assemble_swap_plan_inputs(
        session: object,
        *,
        state: GameState | None,
        deployed: list[Unit],
        bench: list[BenchSlot],
        cap: int | None,
        deployed_n: int | None = None,
        front_slots: int = DEPLOYED_FRONT_CAPACITY,
        back_slots: int = DEPLOYED_BACK_CAPACITY,
        fresh_buys: frozenset[str] | None = None,
) -> SwapPlanContext | None:
    """swap 计划输入装配单一源(发出侧与执行侧**同函数、同一装配契约**);

    装配源契约(对抗收束方案钉死原话,last_state 链停用批
    措辞更新)= 执行侧卖出决策实际消费的快照链,不用 PrepObservation
    另起一路:board/fp 消费调用方传入的 ``state``(执行侧/发出侧/sim
    后端三方均传容器单例 game_state_of——装配源换源把执行侧从
    旧滞后帧链切容器,sim 侧后端经同一容器直写);deployed/
    bench 消费调用方现读(执行侧 = SIFT 读面,发出侧 = PrepObservation
    帧)。派生逻辑(target 视图双轨口径/fenced 分支/义务排除集/保护域/
    转型域双门字段)全在本函数,两侧禁自写第二份。两侧输入的逐字段对齐
    由 seam 核对批兑现(对齐证据 = 开闸小批前置义务,待办 IMPL_REPORT),
    核对通过前发出位保持关闭。
    转型域双门字段装配(design §2.0/§2.1):``locked_core``(腿①)/
    ``bond_gate_keys``(终局键集 = form_tiers 键)/``k_members``
    (终局名单 = core ∪ shared)随 target_comp 同点装配(design §2.7
    「随 target_comp 注入」)——键集收窄已随转型分支机器退役,
    ``target_factions`` 恒 = all_factions 全量,禁消费位内联第二份收窄。

    返回 None = 装配不可得(target 视图/板面字典缺读),调用方按
    谓词弃权处理(计划空,不静默发出)。
    ``deployed``/``bench`` = 容器形状(行域 Unit / 占席条目 BenchSlot,
    P4 容器形;发出侧 = 决策帧容器现读,执行侧 = SIFT 现读域,
    装配源契约分轨不变)。

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
            locked_buy_cap_hold,
            locked_buy_membership,
            locked_faction_scope,
            locked_line_recipe_floor_conflict,
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
    # decision_target 伪阵容,定型后走 strategy_state_of(session).target_comp)
    tgt_comp = None
    try:
        if not committed_from(session, state):
            #  state 已切容器形态,decision_target 直吃容器(桥停用位)。
            tgt_comp = (decision_target(session, state)
                        if state is not None else
                        None)
    except Exception:   # noqa: BLE001  双轨读端缺供给 → 退 target_comp
        tgt_comp = None
    if tgt_comp is None:
        from sr_od.application.currency_war.kernel.cw_strategy_session import (
            strategy_state_of,
        )
        tgt_comp = getattr(strategy_state_of(session), 'target_comp', None)
    target_factions = frozenset(getattr(tgt_comp, 'all_factions', None) or ())
    target_cores = frozenset(getattr(tgt_comp, 'core_chars', None) or ())
    # fenced 分支(fp 单一源 form_progress,板满 = 占用数 ≥ cap 占用数
    # 口径;cap 现算 = state.max_units() 单点收束链——与 select_swap_plan
    # 板满门同源,禁经调用方 cap 参数分叉出第二口径;执行侧 cap=None
    # (不消费谓词 cap 门)帧同吃现算)。fp/locked/board_full 同点装配:
    # 转型分支输入与 fenced 分支同源同值(装配单一源)。
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    ist = getattr(strategy_state_of(session), 'v3_intention', None)
    locked_core = bool(getattr(ist, 'locked_comp', None)) if ist is not None \
        else False   # 方向锁腿① = 终局阵容锁定(判定单源归 17_stall_form_
    # spend_authority §1.1;转型域判别子第一腿,design §2.0)。
    locked = locked_core   # 字段终值见下方推广(混轨 = 腿① ∨ P1 配方对锁腿②)。
    # 方向锁推广(双轨对锁期):P1 配方对锁(ist.p1_pair 非空,
    # 意向锁定产物;冻结标志 p1_pair_frozen 钉向)与终局阵容锁定同为
    # 「方向锁在效」(仅混轨 ``locked``;``locked_core`` 不随本推广——
    # 转型域判别子显式排除 pair 帧,design §2.0)。换人域前提按适用范围对齐:
    # 双轨期板面义务本体 = 过渡配方(cw_recipe 模块不变量),配方对锁帧
    # 不进转型域 = 配方完成件压席由双轨域完成品分支承接(现行通道保留,
    # design §2.3 收窄点钉死;2026-09-18 sim 实证出处)。演进降级换人分支
    # 不受影响:pair 帧 membership 空集(locked_buy_membership 未锁帧缺省)
    # 使其 member 门恒关,适用范围仍在终局线。店侧 S_spec 收窄
    # (mandate.swap_transition_narrow_frame)谓词源已迁移挂转型域判别子
    # 全合取(入参同现行:腿① ∧ 板满 ∧ fp<1.00,design §2.3.1),消费位
    # 保留(shop.py/mandate.py),P88 登记域不倒转。
    if ist is not None and getattr(ist, 'p1_pair', ()):
        locked = True
    fenced_on = False
    fp: float | None = None
    board_full = False
    # 占用数 = 容器占用判定(元素非 None 计 1;P4 容器形,行域本身即
    # 紧凑占用序;deployed_n 覆盖参数语义不变——执行侧真读槽位口径,
    # None 退现算)。
    _n = deployed_n if deployed_n is not None else sum(
        1 for d in (deployed or []) if d is not None)
    if tgt_comp is not None and state is not None:
        try:
            _fp = float(form_progress(tgt_comp, state))
        except Exception:   # noqa: BLE001  成型度不可得 = 分支关(保守)
            _fp = 0.0       # fenced 分支维持 0.0 保守侧;fp 留 None ⇒ 转型分支
            # fp_unreadable 弃权(fp 缺读两分支同 fail-closed)
        else:
            fp = _fp
        board_full = _n >= max_units_of(state)
        fenced_on = fenced_swap_arm_of(_fp, _n, max_units_of(state))
    elif cap is not None:
        board_full = _n >= cap   # state 缺读退型:调用方 cap 口径(保守侧)
    # 买面义务排除集(与 M4 燃料集同参同源;起两侧同吃截断集
    # B',cap_hold = locked_buy_cap_hold 现读):锁定帧 =
    # locked_buy_membership 截断口径;ist 缺失 = 缺读(None,谓词弃权);
    # 未锁定帧 = 空集。state 缺读帧 cap_hold=None ⇒ 保宽(fail-closed
    # 零漂移端,与全消费位同向)。
    membership: frozenset[str] | None
    if ist is None:
        membership = None
    else:
        _lm = locked_buy_membership(
            ist, cap_hold=locked_buy_cap_hold(state))
        membership = _lm if _lm is not None else frozenset()
    board = dict(state.board.value or {}) if state is not None \
        else {}
    try:
        _lf = locked_faction_scope(ist) or frozenset()
    except Exception:   # noqa: BLE001  围栏兜底 best-effort(同执行侧)
        _lf = frozenset()
    # 锁定线语境豁免武装位(配方底线门):只与终局阵容锁定第一腿
    # 同读(ist.locked_comp 非空),不随 ``locked`` 方向锁推广(P1 配方
    # 对锁帧不豁免),两词口径分名见 17_stall_form_spend_authority §1.1
    # (helper 自身 fail-safe:清空路径/套名解析失败自动 False,无需调用
    # 侧兜底)。
    recipe_floor_lock_exempt = locked_line_recipe_floor_conflict(ist)
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    fw_name = getattr(strategy_state_of(session), 'transition_framework', '') or ''
    _tgt_fw, fw_carry = deploy_target_sets(tgt_comp, fw_name)
    # 转型域双门字段(随 target_comp 同点装配;design §2.0/§2.1/§2.7):
    # 终局键集 = form_tiers 键(form_tiers 只承担键集/成型判据/门 1④,
    # 档位梯单源 = cw_factions FACTIONS tiers 逐档);终局名单 = core ∪
    # shared(与 mandate_v1 predicates.line_members 同构同值,等价性由
    # 测试钉住,禁两源漂移)。
    bond_gate_keys = frozenset(getattr(tgt_comp, 'form_tiers', None) or ())
    k_members = frozenset(dict.fromkeys([
        *(getattr(tgt_comp, 'core_chars', None) or ()),
        *(getattr(tgt_comp, 'shared_chars', None) or ()),
    ]))
    # 演进降级换人分支(装配级缺省计算;执行侧 bench 域分轨面在
    # cw_op_deploy 卖出分支 SIFT 现读后经同一触发函数重算覆写,声明见
    # evolution_swap_arm_trigger)。
    _bench_occ = [b for b in (bench or []) if b is not None]
    evolution_armed = evolution_swap_arm_trigger(
        membership, _bench_occ,
        locked=locked, fp=fp, board_full=board_full)
    return SwapPlanContext(
        target_factions=target_factions,   # all_factions 全量(键集收窄已退役,design §2.3.1)
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
        bench=_bench_occ,
        cap=cap,
        front_slots=front_slots,
        back_slots=back_slots,
        fenced_on=fenced_on,
        fp=fp,
        locked=locked,
        locked_core=locked_core,
        bond_gate_keys=bond_gate_keys,
        k_members=k_members,
        board_full=board_full,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        target_comp=tgt_comp,
        evolution_swap_armed=evolution_armed,
        required_names=frozenset(
            getattr(tgt_comp, 'required_deployed', ()) or ()),
    )


# ============================================================
# 转型域门 1(收益门四腿)+ 守恒(终局档位非降)+ 组贪心序参数
# (design §2.2/§2.3/§2.7;kernel 只含机械执行,序参数由策略层
# ports 注入,门 1 判据本体驻 kernel = 跨策略不变的转型域结构约束,
# 任何羁绊组策略通用,design §2.7 宪法第 5 条判据线作答)
# ============================================================

def bond_gate_tier_profile(bond_gate_keys: frozenset[str] | set[str],
                           names: set[str] | frozenset[str]) -> dict[str, int]:
    """终局键集档位梯逐档计数(design §2.1 档位语义源切分的计数单一源)。

    键值 = 该键计数已达的**档数**(逐档计数,非单阈值);计数源 =
    ``deployed_bond_counts`` 注册表口径(与守恒门/度量同源;禁 state.board
    面板口径——星间旅人面板欠计类已实证);档位梯单源 = cw_factions
    ``FACTIONS`` tiers 逐档(``Comp.form_tiers`` 只承担键集来源/成型判据/
    门 1④ 折法,**不是档位梯子**)。注册表无键(理论态)按 0 档计
    (不承载,保守向)。
    """
    counts = deployed_bond_counts(set(names))
    out: dict[str, int] = {}
    for key in bond_gate_keys:
        info = FACTIONS.get(key)
        if info is None:
            out[key] = 0
            continue
        cnt = counts.get(key, 0)
        out[key] = sum(1 for t in info.tiers if cnt >= t)
    return out


def _bond_gate_support_count(bond_gate_keys: frozenset[str] | set[str],
                             k_members: frozenset[str] | set[str],
                             names: set[str] | frozenset[str]) -> int:
    """支撑件计数(design §2.1 并集口径):名单成员无条件计 1;
    外部件按羁绊标签命中终局键集计 1(件级,双籍件只计 1)。"""
    n = 0
    for name in names:
        if name in k_members:
            n += 1
            continue
        if _bonds_named(name) & set(bond_gate_keys):
            n += 1
    return n


def _bond_gate_view(ctx: SwapPlanContext,
                    victims: list[str], ups: list[str],
                    ) -> tuple[set[str], set[str]]:
    """门 1/守恒的组换后板态视图(design §2.0):板上单位集合 − 换出
    victims + 换入组 的派生名字集,档位与支撑计数在视图上现算。"""
    before = {x.char_id for x in ctx.deployed if x is not None and x.char_id}
    after = (before - set(victims)) | set(ups)
    return before, after


def swap_bond_gate_conservation(ctx: SwapPlanContext, *,
                                victims: list[str],
                                ups: list[str]) -> bool:
    """转型域守恒判定 = 终局档位非降(组换后板态口径;design §2.3)。

    与门 1① 的档位面**同一函数**(bond_gate_tier_profile,禁第二实现);
    过渡体系(engines_guard 守恒对象)在本域不守恒——过渡侧损失由 victim
    序自然最小化(design §2.3 掉档语义申报,【拍】裁定)。
    """
    before, after = _bond_gate_view(ctx, victims, ups)
    prof_b = bond_gate_tier_profile(ctx.bond_gate_keys, before)
    prof_a = bond_gate_tier_profile(ctx.bond_gate_keys, after)
    return all(prof_a[k] >= prof_b[k] for k in prof_b)


def swap_bond_gate_benefit(ctx: SwapPlanContext, *,
                           victims: list[str],
                           ups: list[str],
                           pairs: list[tuple[str, str]] = (),
                           up_stars: dict[str, int] | None = None,
                           ) -> tuple[bool, str]:
    """门 1 收益门(四腿任一;对组换后板态判定;design §2.2)。

    检查序钉死 = **④→①→②→③**:成品腿优先(design §2.2 枚举表 C/G 行
    把组生长型与 OR 承接型归因到 ④;四腿任一通过即放行,分键归因 =
    首达腿)。返回 (是否通过, 首达腿键∈{'completion','tier','support',
    'star'});不通过 = (False, '')。

    - **④ 成品腿**:组换后成型判据达成(fp ✗→✓)——折法单一源 =
      ``cw_comps.form_progress`` 现行契约(含 OR 组承接/required 腿;
      与 ``_completion_swap_ins`` 单点门同函数,禁复制第二实现);
      前提 = ctx.fp < 1.0(域判别子已保证,防御再查);
    - **① 激活终局羁绊新档位**:档位梯逐档计数(design §2.1)后档数
      严格增——与守恒面同一计数函数;
    - **② 支撑件数严格增**(§2.1 并集口径);
    - **③ 同名升星横换**:换入件与被换件**同名**(必要条件,异名星级
      升换属 E 类无结构收益)∧ 换入件星级严格升;pairs = 组内
      (victim, up) 对表。

    门 1 判定的羁绊范围 = 终局键集,不含其他羁绊(design §2.2)。
    """
    before, after = _bond_gate_view(ctx, victims, ups)
    _fp = getattr(ctx, 'fp', None)
    comp = ctx.target_comp
    if comp is not None and _fp is not None and _fp < 1.0:
        from sr_od.application.currency_war.kernel.cw_comps import (
            form_progress,
        )
        panel = _HypotheticalPanel(deployed_bond_counts(after), after)
        if form_progress(comp, panel) >= 1.0:
            return True, 'completion'
    prof_b = bond_gate_tier_profile(ctx.bond_gate_keys, before)
    prof_a = bond_gate_tier_profile(ctx.bond_gate_keys, after)
    if any(prof_a[k] > prof_b[k] for k in prof_b):
        return True, 'tier'
    if _bond_gate_support_count(ctx.bond_gate_keys, ctx.k_members,
                                after) > _bond_gate_support_count(
                                    ctx.bond_gate_keys, ctx.k_members, before):
        return True, 'support'
    victim_stars = {x.char_id: (x.star or 1) for x in ctx.deployed
                    if x is not None and x.char_id}
    for v_name, u_name in pairs:
        if v_name == u_name \
                and (up_stars or {}).get(u_name, 1) > victim_stars.get(v_name, 1):
            return True, 'star'
    return False, ''


@dataclass(frozen=True)
class SwapGroupOrder:
    """组贪心序参数(策略层 ports 注入;design §2.7 宪法第 5 条判据线)。

    换策略可能要不同的序:序参数(两级 victim 序/换入序的排序键)由
    策略层构建注入,kernel 只含机械执行(遍历序 = 换入主循环 × victim
    内层循环,字典序第一可行组),策略语义可换而宿主不动。两键必须返回
    **全序** tuple(并列 tie-break 已折入键内;3.5 预测表确定性要求全序
    钉死,禁随机/集合序)。生产构建单一源 = mandate_v1 deploy_plan.
    ``build_swap_group_order``(序语义 = design §2.7 钉死面)。
    """
    #: 换入候选序键(bench 下标 → 全序键;换入主循环序)
    up_sort_key: Callable[[int], tuple]
    #: victim 候选序键(板名 → 全序键;victim 内层循环序,含两级 +
    #: 名单末位桶分层)
    victim_sort_key: Callable[[str], tuple]


def _select_swap_group_plan(ctx: SwapPlanContext,
                            reasons: dict[str, str],
                            select_up: Callable[..., tuple[list[int],
                                                           list[int],
                                                           dict[int, str]]],
                            order: SwapGroupOrder | None) -> SwapPlan:
    """转型域最小充分组贪心(design §2.7;kernel 机械执行体)。

    组生长语义(钉死):逐对追加成组——累积组门 1 失败 → 失败前缀保留
    继续生长(门 1④ 存在多对合取才达成的形态,只试单对会使情形 C 不可达)
    → 直到门 1 通过或候选耗尽;守恒/收益判定点 = 累积组现算(部分组态
    只是搜索中间产物不发射,组定稿后才进执行形态)。遍历序(design §2.7
    钉死「先换 victim(内层耗尽)→ 再换 up」):当前 up 的 victim 辅序
    **逐个试组**(门 1 未中的试组不并入前缀——本 up 未定稿,禁同 up
    重复入组),内层耗尽才把本 up 的字典序指定对(victim 辅序首个过
    全部前置闸者)并入前缀、推进下一 up;**首个可行组即停**;「首个
    可行组」= 换入主序 × victim 辅序的字典序第一个可行组(内层回退使
    「首 victim 挡道的 no-op 对」不再遮蔽后续可行组——下帧续发形态的
    必要条件,缺口补丁见 3.2 交付报告)。

    逐对可入性(四道,全部现算):
    1. victim 资格 = 池层逐件单一判定 ``swap_sell_exclusion_reason``
       (门 2 白名单已含通道 3(a)/3(b);配对可行性谓词限域①②级桶 =
       名在板 ∧ 非保护 ∧ 过门 2,名单末位桶按让位通道判定——同在本
       资格面内,无第二道逐对资格;**同名去重不适用于换人 victim 场景**
       ——换人的 victim 本就是同名离场语义,D 情形可达,上序裁判在
       victim 离场后的假想板上自然放行同名换入);
    2. 换入侧裁判 = 卖后假想板(累积 − victim)复用 ``select_up`` 全套
       留置规则(围栏/成对/点火序/核心桶/cap/同名去重/配方底线),
       裁判域单一源不动,贪心只产「谁进谁出」;target 视图参数按
       §2.7 支撑件并集口径映射(键集 + 名单,is_tgt = 支撑件视图);
    3. 卖后上序底线照旧:``post_sell_req_missing``(required/完成件
       成对兑现,三消费位之一)+ up ∈ 支撑件视图
       (``post_sell_offline``,支撑件并集口径);
    4. 守恒 = 累积组终局档位非降(与门 1① 同一函数,禁第二实现)。

    拒绝侧分键来源(design §2.3.1 闭集):victim 池/换入池空 =
    'novictim'(无可行组零动作);搜索中有守恒拦且未成组 =
    'conservation';其余未成组 = 'nogain'(四腿全不中)。三态选择
    钉死优先序 novictim > conservation > nogain(确定性)。
    """
    _members = set(ctx.k_members)
    _keys = set(ctx.bond_gate_keys)
    # victim 池(逐件资格单一源;拒因逐件保留暴露)
    pool: list[tuple[str, int]] = []
    for _scan, d in enumerate(ctx.deployed):
        name = d.char_id or ''
        if not name or CHARACTERS.get(name) is None:
            continue   # 未注册件不可判羁绊,不入 victim(扫描同款)
        _rej = swap_sell_exclusion_reason(name, ctx)
        if _rej:
            reasons[name] = _rej
            continue
        pool.append((name, _scan))
    tier_of = {n: ('名单末位' if n in _members else
                   ('二级' if (_bonds_named(n) & _keys) else '一级'))
               for n, _s in pool}
    reject = ''
    ups: list[int] = []
    if not pool or order is None:
        reject = 'novictim'   # 无 victim 候选(或序参数缺失 = 无法成组,fail-closed 零动作)
    else:
        ups = [i for i in range(len(ctx.bench))
               if (lambda cid: bool(cid) and CHARACTERS.get(cid) is not None
                   and support_view_char_is(ctx, cid))(_bench_cid(ctx.bench[i]))]
        if not ups:
            reject = 'novictim'   # 无合法换入候选 = 无可行组
        else:
            pool.sort(key=lambda t: order.victim_sort_key(t[0]))
            ups.sort(key=order.up_sort_key)
    group: list[tuple[int, str]] = []
    conservation_blocked = False
    if reject == '':
        used_v: set[str] = set()
        acc_names = {d.char_id for d in ctx.deployed if d.char_id}
        acc_victims: list[str] = []
        acc_ups: list[str] = []
        for ui in ups:
            up_name = _bench_cid(ctx.bench[ui])
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                bench_slot_unit,
            )
            up_star = getattr(bench_slot_unit(ctx.bench[ui]), 'star',
                              None) or 1
            # 本 up 的字典序指定对 = victim 辅序首个过全部前置闸(裁判/
            # 底线/守恒)的对;内层耗尽仍无门 1 通过时并入前缀(生长载体,
            # design §2.7「每入一个换入件从 victim 序配一个」)。
            designated: tuple[int, str] | None = None
            designated_acc: tuple[list[str], list[str], set[str]] | None = None
            for v_name, _scan in pool:
                if v_name in used_v:
                    continue
                kept = acc_names - {v_name}
                fac2 = deployed_bond_counts(kept)
                up2, held2, _hr = select_up(
                    ctx.bench, deployed_cids=kept, deployed_fac=fac2,
                    board=dict(fac2), cap=ctx.cap,
                    front_total=ctx.front_slots, back_total=ctx.back_slots,
                    # up 侧 target 视图 = 支撑件并集口径(design §2.7):
                    # is_tgt = bonds ∩ 键集 ∪ 名单 ∪ fw_carry,经参数映射
                    # 表达,select_deployments 本体零修改。
                    target_factions=frozenset(_keys),
                    target_cores=frozenset(_members),
                    fw_carry=ctx.fw_carry,
                    locked_factions=ctx.locked_factions,
                    recipe_floor_lock_exempt=ctx.recipe_floor_lock_exempt,
                    required_names=ctx.required_names)
                for _hi in held2:
                    _hn = _bench_cid(ctx.bench[_hi])
                    reasons[_hn] = 'post_sell_held'
                if ui not in up2:
                    continue   # 换入侧裁判不认(围栏/cap 竞争/同名去重/配方底线)→ 内层换 victim
                # 底线①:post_sell_req_missing 照旧(design §2.7;
                # 完成品分支三消费位之一——上序底线,零签名)
                if required_swap_arm_pending(ctx) and not (
                        up_name in set(ctx.required_names)
                        or _seat_completes_form(ctx, v_name, up_name)):
                    reasons[v_name] = 'post_sell_req_missing'
                    continue
                # 底线②:up ∈ 支撑件视图(post_sell_offline;三消费位之一,
                # design §2.7 支撑件并集口径)
                if not support_view_char_is(ctx, up_name):
                    reasons[v_name] = 'post_sell_offline'
                    continue
                # 守恒:累积组现算(终局档位非降 = 门 1① 档位面同一函数)
                if not swap_bond_gate_conservation(
                        ctx, victims=acc_victims + [v_name],
                        ups=acc_ups + [up_name]):
                    conservation_blocked = True
                    continue   # 守恒拦 → 内层换 victim
                if designated is None:
                    # 字典序指定对登记(首个过前置闸的 victim;victim 辅序
                    # 即循环序,首中即指定——确定性零随机)。
                    designated = (ui, v_name)
                    designated_acc = (acc_victims + [v_name],
                                      acc_ups + [up_name],
                                      kept | {up_name})
                # 试组:累积组 + 本对,门 1 现算(design §2.7 组生长语义)
                _v = acc_victims + [v_name]
                _u = acc_ups + [up_name]
                ok, leg = swap_bond_gate_benefit(
                    ctx, victims=_v, ups=_u,
                    pairs=[(v_name, up_name)], up_stars={up_name: up_star})
                if ok:
                    group.append((ui, v_name))
                    return SwapPlan(
                        sell_names=[v for _ui, v in group],
                        up_bench=[u for u, _v in group],
                        reasons=reasons, arm='bond_gate',
                        bond_gate_leg=leg,
                        victim_tier=tier_of.get(group[0][1], ''),
                    )   # 首个可行组即停(组定稿)
                # 门 1 未过 → 内层换 victim 重试(design §2.7 组构造遍历序
                # 「先换 victim(内层耗尽)→ 再换 up」;回退试组不并入前缀
                # ——本 up 未定稿,禁同 up 重复入组;指定对已在上方登记,
                # 内层耗尽时经其保前缀生长,禁深回溯移除已并入对)
            # 内层耗尽:指定对并入前缀(失败前缀保留继续生长,情形 C 通道)
            # → 外层推进下一 up;无指定对 = 本 up 无可配 victim,前缀不动。
            if designated is not None:
                group.append(designated)
                acc_victims, acc_ups, acc_names = designated_acc
                used_v.add(designated[1])
    if group and not reject:
        # 生长耗尽仍未过门 1(部分组态只是搜索中间产物,不发射)→ 零动作
        reject = 'conservation' if conservation_blocked else 'nogain'
    elif not reject:
        reject = 'nogain'
    return SwapPlan(reasons=reasons, arm='bond_gate', bond_gate_reject=reject)


def select_swap_plan(ctx: SwapPlanContext | None,
                     reasons_out: dict[str, str] | None = None,
                     *,
                     select_up: Callable[..., tuple[list[int], list[int],
                                                    dict[int, str]]],
                     group_order: SwapGroupOrder | None = None,
                     ) -> SwapPlan:
    """板满换阵补部署计划谓词(M1″ 动作发出面;选人判定同族纯函数)。

    计划形态分域(design §2.7):转型域(判别子 = ``swap_bond_gate_domain``)
    = **多对组计划形态**(最小充分组贪心,``_select_swap_group_plan``,
    序参数经 ``group_order`` ports 注入);域外(未锁帧/pair 双轨帧/
    成型帧)= 单对计划形态(现行语义逐位照旧)。

    域外单对语义(组合式,零新启发式)::

        swap 计划非空 ⟺ cap 满(占用数口径)∧ 义务/新鲜排除后存在
        合格 victim ∧ 对「卖出 victim 后假想状态」复用选人判定
        判 up 非空

    - **板满门 = 占用数口径**:``,len(deployed)``(占用件数,含 SIFT
      未识别 char_id='' 占位件)≥ cap——与执行侧 cap 门「禁用衍生计数」
      同向(占用数 = 非 None 件逐件计;禁 ``len(deployed_cids)`` 衍生
      集,SIFT 未识别占位件漏计 = 板实满判未满);
    - **victim 资格** = 逐件单一判定 ``swap_sell_exclusion_reason``(义务
      集排除/缺读弃权/轮内新鲜度/per-piece 资格族——基座/成型分支经
      ``offtarget_sell_allowed`` 参数化、pair 双轨帧经守恒门/素材守卫/
      1★ 守卫逐件放行,见该函数 docstring;fenced 分支态经装配注入);
    - **双轨域胜出者的卖后上序底线**:up ∩ target 视图 ≠ ∅(拒因
      ``post_sell_offline``;arm='transition' 现行保留,design §2.3.1);
      base/formed 分支维持现状判 up 非空;
    - **上序 = 组合语义**:对卖出后假想板面复用 ``select_up`` 注入的选人
      判定(单一源 = mandate_v1 deploy_plan.select_deployments_reasoned;
      围栏/成对/填空/点火序/核心桶/cap/同名去重/配方底线
      全套留置规则就是上序的最终裁判);底线规则留 bench 的件**不作
      上序候选**(拒因 ``post_sell_held``),「白卖一件板面变弱」形态
      在谓词内不可达;
    - **cap 缺读**(``cap is None``)⇒ 弃权 ``cap_unreadable``,与 M1/
      M1′ vacancy=0 门同 fail-closed(动作发出契约);
    - **换阵可兑现门(F1;发出-执行接缝合拢)**:合取①目标视图
      非空(假 ⇒ 弃权 ``no_direction``,2026-09-08 实机无方向幻影部署
      软卡死的直接根除位)∧ 合取②bench 存在目标视图件(假 ⇒ 弃权
      ``no_bench_target``;跳过域 = fenced 开门帧集 = 旧混轨转型域帧集,
      逐帧等价——转型域与 pair 双轨帧自带更强的卖后上序底线,与合取②
      在「bench 无目标视图件」帧同判计划空,plan 级预判只会把逐件暴露
      挤成单键;且 plan 非空 ⟹ up 含 target 视图件 ⟹ bench 必有目标
      视图件,合取②被底线蕴含,发出⇔执行零分叉)。合取③(板上存在
      可卖 off-target 件)由 victim 扫描/组贪心 victim 池自然承载
      (逐件同判 swap_sell_exclusion_reason,扫描空即计划空),逐件
      拒因保留暴露。判定实现单一源 = swap_realizable 合取支函数族,
      禁第二份口径。弃权序:供给缺读面(input_missing/cap/membership,
      装配侧更早失败点)先报,语义谓词门在其后。

    :param reasons_out: 传入 dict 时逐件拒因(名 → 拒因键)写入;
        plan 级弃权以键 ``'(plan)'`` 写入(既有惯例)。
    :param select_up: 选人判定注入参(必填;单一源 = mandate_v1
        deploy_plan.select_deployments_reasoned,包依赖矩阵禁
        kernel→strategies 直引,由调用方注入同一函数对象——契约同
        cw_launch_admission line_members 先例)。
    :param group_order: 组贪心序参数 ports 注入(转型域必填;生产构建
        单一源 = mandate_v1 deploy_plan.build_swap_group_order;None 时
        转型域 fail-closed 零动作,序参数缺失 = 无法成组)。
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
    # F1 换阵可兑现门(合取①②;实现单一源见 swap_realizable 合取支
    # 函数族。合取③ = 下方 victim 扫描自然承载,不预判——预判会把逐件
    # 拒因(fenced_arm_closed 等)挤成 plan 级单键,丢暴露)。
    # 合取②跳过域 = fenced 开门帧集(混轨 locked ∧ fp<1.00 ∧ 板满;
    # 与旧混轨转型域帧集逐帧等价——判别子排除 pair 后,转型域与 pair
    # 双轨帧同落本集,域腿单一源 = fenced_swap_gate_open,design §2.3.1)。
    _fenced_open = fenced_swap_gate_open(
        bool(getattr(ctx, 'locked', False)), getattr(ctx, 'fp', None),
        bool(getattr(ctx, 'board_full', False)))
    if not target_view_present(ctx):
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'no_direction'})
        return SwapPlan(abstain='no_direction')
    if not _fenced_open and bench_target_count(ctx) == 0:
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'no_bench_target'})
        return SwapPlan(abstain='no_bench_target')
    occupied = len(ctx.deployed)   # 占用数口径(含未识别占位件)
    if occupied < ctx.cap:
        return SwapPlan(reasons=reasons)
    if swap_bond_gate_domain(ctx):
        # 转型域:多对组计划形态(design §2.7 组贪心;域分流单一源 =
        # swap_bond_gate_domain)。
        plan = _select_swap_group_plan(ctx, reasons, select_up, group_order)
        if reasons_out is not None:
            reasons_out.update(reasons)
        return plan
    # ---- 域外单对计划形态(现行机器逐位照旧;pair 双轨帧在此路径,
    # arm='transition' + P79-4 让渡序 + 放行门 P79-3 全现行,§2.3.1)----
    _dep_names = {x.char_id for x in ctx.deployed if x.char_id}
    victims: list[tuple[tuple, Unit, set[str], str]] = []
    for _scan, d in enumerate(ctx.deployed):
        name = d.char_id or ''
        ch = CHARACTERS.get(name) if name else None
        if ch is None:
            continue   # 未识别件不可判羁绊,不入 victim(执行侧同款)
        bonds = set(ch.factions) | set(ch.flows)
        # 逐件单一判定(排除族∪资格族;发出⇔执行同函数,同位扩展):
        # offtarget_sell_allowed 经判定函数参数化接入(fenced 布尔在函数
        # 内喂入),谓词不再自写第二份资格语义(禁分轨态)。
        _rej = swap_sell_exclusion_reason(name, ctx)
        if _rej:
            reasons[name] = _rej
            continue
        # arm = 胜出者资格族标注:fenced 件在 fenced_on(fp≥1.00)
        # 帧 = 成型分支,否则(其唯一可卖路径)= 双轨域转型分支标注;
        # fp 单值互斥 ⇒ 无歧义。fenced 开门帧混轨恒标 'transition'
        # (禁落 'base')——swap_arm_transition_trigger 分键归因依赖
        # 此标注(design §2.3.1:双轨域 arm='transition' 照旧)。
        _arm = ('formed' if ctx.fenced_on else 'transition') \
            if bonds & DEPLOY_FENCE else 'base'
        if _fenced_open:
            _arm = 'transition'
        # victim 序(P79-4 让渡序;的
        # 「1★ 优先单键」在其适用范围外照旧):fenced 开门帧 = 结构档边际
        # 贡献升序(纯结构计数,度量单一源 = swap_yield_contribution,
        # 度量域 = all_factions 全量并集,design §2.7)→ 星级升序
        # → ctx.deployed 板槽位序首个(显式定义,零新排序键);资格门与
        # 排序键正交(排序治「先换谁」、资格治「能不能换」)。域外键 =
        # 旧 1★ 优先 + 扫描序稳定序,逐位同旧。
        _contrib = swap_yield_contribution(
            ctx.target_factions, _dep_names, name) if _fenced_open else 0
        victims.append((
            (_contrib,
             0 if (d.star or 1) <= 1 else 1,
             _scan),
            d, bonds, _arm))
    victims.sort(key=lambda t: t[0])

    # bench 件是否 target 视图(双轨域卖后上序底线:up ∩ target ≠ ∅;
    # 判定单一源 = target_view_char_is,fw_carry 口径收敛后禁第二实现。
    # 本路径只辖域外(未锁/pair 双轨帧)——转型域底线已切支撑件并集
    # 视图(support_view_char_is,design §2.7 三消费位钉死),两视图
    # 并存各有辖域禁交叉引用。)
    def _bench_is_target(i: int) -> bool:
        return target_view_char_is(ctx, _bench_cid(ctx.bench[i]))

    plan = SwapPlan(reasons=reasons)
    for _rank, d, _bonds, _arm in victims:
        name = d.char_id or ''
        # 卖出后假想态:该件从占用序移除,板面/阵营档按剩余件重算
        kept = [x for x in ctx.deployed if x is not d]
        cids2 = {x.char_id for x in kept if x.char_id}
        fac2 = deployed_bond_counts(cids2)
        up2, held2, held_reasons2 = select_up(
            ctx.bench, deployed_cids=cids2, deployed_fac=fac2,
            board=dict(fac2), cap=ctx.cap,
            front_total=ctx.front_slots, back_total=ctx.back_slots,
            target_factions=ctx.target_factions,
            target_cores=ctx.target_cores, fw_carry=ctx.fw_carry,
            locked_factions=ctx.locked_factions,
            recipe_floor_lock_exempt=ctx.recipe_floor_lock_exempt,
            required_names=ctx.required_names)
        for _hi in held2:
            _hn = _bench_cid(ctx.bench[_hi])
            reasons[_hn] = 'post_sell_held'
        # 换入分支卖后上序底线:分支武装帧(up 空间 = 本分支腾出)卖后上序必须
        # 真兑现换入对象——required 件直接认名;完成件按**实际落位复检**
        # (该 victim 离场 ∧ 该 up 名入板后成型判据满,``_seat_completes_
        # form``):候选集成员资格不足以防「同属候选的普通成员占位」白卖,
        # 须绑定卖出 victim 成对兑现。适用范围 = ``required_swap_arm_pending``
        # 真帧——required 在板帧完成分支仍可武装(有意设计,
        # test_deploy 完成件让位测试钉定),此帧底线同样会覆盖;
        # 谓词假帧不覆盖,逐位同旧。
        if up2 and required_swap_arm_pending(ctx):
            _req = set(ctx.required_names)
            _up_names = [_bench_cid(ctx.bench[_i]) for _i in up2]
            if not (any(_u in _req for _u in _up_names)
                    or any(_seat_completes_form(ctx, name, _u)
                           for _u in _up_names)):
                reasons[name] = 'post_sell_req_missing'
                continue
        if up2 and (_arm != 'transition' or any(
                _bench_is_target(_i) for _i in up2)):
            plan.sell_names = [name]
            plan.up_bench = list(up2)
            plan.arm = _arm
            break
        if up2 and _arm == 'transition':
            reasons[name] = 'post_sell_offline'   # 卖后上序无 target 视图件
        # 该 victim 卖了也上不了(全部候选被留置)→ 计划收窄试下一
        # victim;最后一个 victim 的留置拒因保留在 reasons 暴露。
    if reasons_out is not None:
        reasons_out.update(reasons)
    return plan


# ============================================================
# 板上唯一性守卫
# board_unique_key(唯一活消费方 = 部署围栏,本模块同域)。
# ============================================================



def board_unique_key(bc: Unit) -> str | None:
    """板上同名唯一性判据键(设计裁定:场上同角色仅 1;P4 容器形重写:
    入参 = 行域/工作表 ``Unit``,唯一消费域;§2.4)。

    - ``char_id`` 空 = 未知身份 → None(不参与查重——两个未知不是可证明的重复);
    - 开拓者各排形态(char_id 随排切换)归一为同一键(场上同样仅 1 个开拓者);
    - 其余 = char_id 本身。
    """
    cid = getattr(bc, 'char_id', '') or ''
    if not cid:
        return None
    from sr_od.application.currency_war.data.cw_chars import is_trailblazer
    return '__trailblazer__' if is_trailblazer(cid) else cid
