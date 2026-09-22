"""deploy 域判定纯逻辑(换阵计划/配方底线/点火序/承重观测;单一源)。

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

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
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

#: r288 配方底线门档值(单源派生的模块级化;原
#: select_deployments 局部派生与 op 侧内联派生 cw_op_deploy 两处同消费
#: 本常量,收口于此)。
#: ⚠️ 挂账关联:本常量派生自上方 TRANSITION_TRAITS 副本,
#: 该副本带迁移挂账(权威副本 = knowledge/cw_engine_facts.
#: TRANSITION_TRAITS,按 legacy cleanup 计划随本文件删除)——本常量属
#: 既有消费方向的模块级化(cw_intention 本就 import TRANSITION_TRAITS,
#: 非新增消费方文件),副本迁移执行时本常量须随迁,禁留断链。
RECIPE_FLOOR_TRAIN_CAP: int = dict(TRANSITION_TRAITS).get('列车同行', 2)
RECIPE_FLOOR_XZ_BASE: int = dict(TRANSITION_TRAITS).get('仙舟', 3)


# 守卫辖域体系集:四过渡体系全辖(三羁绊 + 希儿系
# 单卡判据,tier=1)。辖域语义与 TRANSITION_TRAITS 的 deploy 排序语义
# **分离**——后者是阵营计数排序维(希儿系单卡判定在 deploy 维无意义,
# 故排除,历史理由保留),但 卖侧守卫/保护集借用
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
    if seele_system_formed(board_factions, deployed_names):
        n += 1
    return n


def seele_system_formed(board_factions: dict[str, int],
                        deployed_names: frozenset[str] | set[str]) -> bool:
    """希儿系达成谓词(单一实现;engines_count 与转型臂守恒门同吃)。

    希儿在场 ∧ 放大器 ≥2(量子同频 ∨ 贝洛伯格任一,「或」口径)。
    从 engines_count 内联式提出:守恒门需要**逐体系**的达成布尔
    (engines_count 只出总数,粒度不够),提函数 = 不写第二份希儿系
    判定(:新资格族语义只在判定函数链实现一次)。
    """
    return ('希儿' in deployed_names
            and (board_factions.get('量子同频', 0) >= 2
                 or board_factions.get('贝洛伯格', 0) >= 2))


def is_seele_system_member(char_id: str, bonds: set[str]) -> bool:
    """希儿系贡献件判据(单卡 + 放大器;守卫/保护辖域口径)。

    希儿本人(单卡)+ 量子同频/贝洛伯格放大器件——与 cw_evolution.
    _engine_systems_formed/_contributes_engine_system/_is_member 的
    希儿系分支同口径(此前已有单卡判据先例,此处提为单一源函数)。
    tier=1:希儿系作为四过渡体系之一的档(user_playstyle 四体系封闭
    裁定,transitions.md;希儿系引擎=希儿在场 ∧ 放大器 ≥2,但**恢复
    种子**的辖域口径取贡献件全计——清空任意最后一件贡献件都使该体系
    归零,owned 计数含希儿与全部放大器件)。
    """
    return char_id == '希儿' or bool(bonds & SEELE_AMP_FACTIONS)


#: B_t 板面线内阵营集(四过渡体系:TRANSITION_TRAITS 三羁绊阵营 ∪
#: 希儿系放大器阵营;与 engines_count 同辖域的承重面)。纯遥测观测
#: 辖域(纯遥测口径延续),不进任何判据。
SYSTEM_LINE_FACTIONS: frozenset[str] = (
    frozenset(b for b, _t in TRANSITION_TRAITS) | SEELE_AMP_FACTIONS)


def board_target_line_weight(
        deployed_names: frozenset[str] | set[str] | list[str]) -> int:
    """B_t:板面目标线承重计数(件级单一源;form_score 替代披露口径)。

    逐件判定 = 全羁绊(factions+flows,CHARACTERS 注册表)∩
    ``SYSTEM_LINE_FACTIONS`` 非空,或希儿本人(单卡判据,与
    ``is_seele_system_member`` 希儿分支同口径);命中件计 1——桑博=贝+DOT 双籍
    只计 1 件(件级非阵营级,阵营级计数会双籍重复)。bench 囤件不计入
    (与旧 form_score 同裁决口径:「上场了才算承重」)。

    定位:纯遥测观测面,不进判据(零行为面)。替代口径的依据 =
    form_score 预测力判定(sim61-63 三批 90 局全量:现口径在决策
    关键帧恒常数 1.0 零方差、预测力为零;B_t 是唯一 p<0.001 显著
    代理,预测力集中于 boss 战存活深度,对伤害差/终局 hp 仅弱正
    ——判读时按此边界解读,勿拔高用途)。禁第二实现:任何 B_t
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
    """r288 配方底线门单一判定(含锁定线语境豁免;kernel 单一源)。

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
    :param supply_exists: armed 时由调用方现算喂入;disarmed 时传
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
    """deploy 围栏 target 集装配(装配单一源的**围栏视图 helper**;案 B)。

    视图归属定谳(.debug/progress/2026-09-11-cw-clear-run/定谳记录-deploy围栏.md
    第六节:围栏目标视图 = 成型面装配语义,本函数退出独立第二装配入口地位):
    - 双轨期(``transition_framework`` 非 ''):配方伪 comp all_factions
      (``cw_recipe.recipe_comp`` 单一源;「过渡=配方即方向」,终局 comp 特有键
      不混入——方向混装移除是定谳申报的行为差)。框架方向键面完备性由配方
      数据承载(仙舟配方持续伤害键,B2 修正条件),**显式 ``∪ FRAMEWORK_
      FACTIONS`` 退役**(并集语义只许配方一处,双源即分裂);
    - 定型/无框架:终局 comp all_factions(= factions ∪ flex_factions,
      与装配单一源 assemble_swap_plan_inputs 的 target 视图同链同值;
      flex 键入场是定谳申报行为差③)。
    返回 ``(target_factions, fw_carry)``:fw_carry = 框架(或通用)非 drop 件
    (先框架非 drop + 通用 carry,散件 drop 不认;两分支同式,零漂移面)。
    信任边界:``fw`` 非 '' 即双轨期信号(与 ``cw_recipe.decision_target`` 的
    committed 门同向;定型后框架无写端=休眠,不存在 committed 携 fw 帧)。
    防御退型:框架无配方注册(理论态)/comp 无 all_factions 属性(鸭子型
    comp)→ 逐位退旧语义,零漂移。消费面 = mandate_v1 deploy_plan 计划
    装配(``_deploy_plan_inputs``,发射位与出战链单一源)——选人抑制谓词
    (发射×执行契约)与换阵臂各写一份即双源,禁复制。
    """
    fw = transition_framework or ''
    fw_carry: set[str] = set()
    if fw:
        from sr_od.application.currency_war.kernel.cw_recipe import recipe_comp
        from sr_od.application.currency_war.knowledge.cw_line_facts import (
            FRAMEWORK_FACTIONS,
            TRANSITION_PACK,
        )
        rc = recipe_comp(fw)
        if rc is not None:
            tgt = set(rc.all_factions)
        else:
            # 未注册框架(理论态):退旧并集语义(零漂移保守侧)
            tgt = set(getattr(target_comp, 'factions', None) or ()) \
                | set(FRAMEWORK_FACTIONS.get(fw, ()))
        fw_carry = {n for n, (f, t) in TRANSITION_PACK.items()
                    if (f == fw or f == '通用') and t != 'drop'}
    else:
        tgt = set(getattr(target_comp, 'all_factions', None)
                  or getattr(target_comp, 'factions', None) or ())
    return tgt, fw_carry


def residual_fill_plan(held: list, front_empty: list, back_empty: list,
                       bench_pos: dict, bench_cid: dict,
                       deployed_cids: set, cap: int | None,
                       deployed_count: int) -> list[tuple[int, str, int]]:
    """P24 残余补部署计划(纯函数,可离线直测;判据单一源 = 本函数,
    CwScreenDeploy 侧同名函数仅转发适配器,仿彼处 r288_hold_now 先例)。

    主排序循环结束后空槽仍存在(cap 未满)且散牌留置(``held``)非空时,
    对留置散牌生成补部署计划。判据 = P24 残余补部署支配定理
    (docs/develop/sr_od/application/currency_war/proofs/
    p24-residual-fill-dominance.md):零支出域(C=I=0,补部署不触碰金账
    任何记账点)下,空 cap 槽上任意**合法**单位上阵
    ΔEV = Δp·ΣL_c·S ≥ 0 恒成立(u>0 且 Δp>0 时严格>0)——
    「有羁绊的板 > 空槽」,故合法留置件逐件补上,不存在负 EV 退补路径;
    非法件(同名 dup)与物理上限(cap 满/两排皆满)是守卫剔除面而非
    EV 判负。散牌留 bench 与配方围栏辖「选谁优先」语义,
    不支配「空槽 vs 空板」。消费时机 = 部署执行帧主拖拽循环之后
    (拖拽后 fresh 复查占用喂入),禁移发射面——fill 依赖拖拽后真值,
    移发射位 = 时序行为变更。

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

    = 容器占用数(占用判定 = 元素非 None 计 1;P4 容器形,行域本身即
    紧凑占用序)。**禁用
    ``sum(board.values())``**:board 语义 = 阵营名 → 该阵营在场人数
    (一人多阵营贡献多次,4 人可贡献 11 阵营次)——把羁绊计数当部署数
    喂「板满」门 = 建模对象错,板未满即开臂、熔断自线成型起事实失效。
    """
    return sum(1 for d in (tracked_deployed if isinstance(tracked_deployed, list)
                           else []) if d is not None)


def fenced_swap_arm_of(fp: float, deployed_n: int, cap: int | None) -> bool:
    """换阵卖出义务臂触发判据(纯函数,锁测试面):线成型(fp≥1.00,
    单一源 ``cw_comps.form_progress``)∧ 板满(占用数 ≥ cap——cap =
    可上阵数占用数口径,与 select_swap_plan 板满门同一派生链
    ``max_units_of``(level+宝钻、封顶 = 4+back_max 动态真值
    〔GameState.back_layout,值域 10-13〕;物理槽表常数 DEPLOYED_
    CAPACITY 禁作阈值,理由见下),
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


# ===== 转型臂(M1″ swap 谓词触发域扩展;bench→板 换血通道)=====
# 语义出处:(docs/develop/sr_od/application/currency_war/decisions/
# 0534-swap-transition-arm.md)。病灶:基座/成型臂都不辖「锁线后
# fp<1.00 转型期」(成型臂门 fp≥1.00),板满帧 fenced victim 全被
# W209 熔断拒 ⇒ victim 空 ⇒ 换血死锁(实机「锁线 core 坐板凳、
# deployed 恒旧线过渡件」形态,§背景)。本臂 = 追加资格族:
# locked ∧ fp<1.00 ∧ 板满帧,fenced victim 经守恒门逐件放行。

#: 转型臂回滚常量(缺省开):翻 False = 仅关转型臂(资格判定
#: 单点生效,发射⇔执行两臂自动同关,无分轨态);基座/成型臂不受牵连。
#: 它不是「默认关等裁决」的行为分轨开关,是单点回滚手段(与 revert 等价);
#: seam 门(cw4_m1p_seam_verified)是 M1″ 基座开闸载体,**不作为本臂回滚
#: 路径**(写回会连坐基座)。删码时同删本常量,无永久悬置。
SWAP_TRANSITION_ARM_ENABLED: bool = True

#: 转型臂守恒门体系档表:GUARD_SYSTEM_TIERS ∪ 护盾
#: (FACTIONS tiers 注册表消费,零硬编码档)。直核不变式:守恒门体系集
#: ⊇ DEPLOY_FENCE(熔断替代论证的承重前提——门辖域覆盖原一刀切保护对象)。
#: 希儿系档 = 单卡二元判定(见 ``seele_system_formed``),不进 tiers 计数。
SWAP_GUARD_SYSTEMS: tuple[tuple[str, tuple[int, ...]], ...] = (
    tuple((bond, (tier,)) for bond, tier in GUARD_SYSTEM_TIERS)
    + (('护盾', tuple(FACTIONS['护盾'].tiers)),)
)
assert {k for k, _ in SWAP_GUARD_SYSTEMS} >= set(DEPLOY_FENCE), \
    '转型臂守恒门体系集必须覆盖 DEPLOY_FENCE(熔断替代论证前提)'


def _flex_key_achieved(key: str, counts: dict[str, int],
                       deployed_names: set[str] | frozenset[str]) -> bool:
    """弹性键「当前板面计数已达任一激活档」判定。

    收窄键集的承载判定,三钉源:
    - 计数源 = ``deployed_bond_counts`` 注册表口径(与守恒门同源;禁
      state.board 面板口径——星间旅人面板 1 vs 注册表真值 2 的欠计类已
      实证,面板口径会引发键集抖动);
    - tier 源 = ``FACTIONS`` tiers(唯一自然源);重叠键仙舟取向 = FACTIONS
      (3,5,7,10)(守恒门侧单档 (3,) 语义不同,两处各有辖域禁互借);
    - 希儿系特例 = FACTIONS 无此键,复用 ``seele_system_formed`` 二元判定。
    """
    if key == SEELE_SYSTEM_KEY:
        return seele_system_formed(counts, deployed_names)
    info = FACTIONS.get(key)
    if info is None:
        return False   # 注册表无键无档可达 → 不承载(保护面收窄侧取保守)
    cnt = counts.get(key, 0)
    return any(cnt >= t for t in info.tiers)


def locked_redeploy_target_keys(
        target_factions: frozenset[str] | set[str],
        core_factions: frozenset[str] | set[str],
        deployed_names: set[str] | frozenset[str]) -> frozenset[str]:
    """锁线域装配级键集收窄(读法 D 规格)。

    锁线域 ``ctx.target_factions`` := 核心羁绊集(comp.factions)∪ 已达成
    档承载弹性键(flex_factions 中计数已达任一 tier 的键;剔除未达成
    flex 键)。收窄只发生在**装配层单一源**(``assemble_swap_plan_inputs``),
    下游五消费位自动同值:offtarget-②(``offtarget_sell_allowed`` target
    早拒)/ ``swap_sell_exclusion_reason`` 宽口径 target 归因 / 上行
    is_tgt(``select_deployments``)/ ``_bench_is_target`` /
    ``post_sell_offline`` 底线——禁任何消费位各自内联第二份收窄
    (双源 = 五面视图分裂,方案 §3.1 读法反例存档)。消费辖域 = 锁线
    **转型域**(落地审 F1 修订):转型域外(未锁帧/锁线成型帧 fp≥1.00)
    不消费本函数,键集逐位同旧 all_factions 全量,成型臂语义照旧
    零行为差。
    """
    core = set(core_factions) & set(target_factions)
    flex = set(target_factions) - core
    names = set(deployed_names)
    counts = deployed_bond_counts(names)
    return frozenset(core | {k for k in flex
                             if _flex_key_achieved(k, counts, names)})


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


def _swap_transition_domain_of(armed: bool, locked: bool,
                               fp: float | None, board_full: bool) -> bool:
    """锁线转型域判定(原始字段形态;单一源,装配点与 ctx 形态同吃)。

    = 转型臂开 ∧ locked ∧ fp<1.00 ∧ 板满(触发谓词)。
    fp 缺读不算已武装(缺读帧按 「两臂同弃权」口径显影)。
    收窄辖域钉本域(落地审 F1 修订):锁线∧成型帧
    (fp≥1.00)键集回全量——否则成型帧释放件经成型臂绕过资格族
    (star_guard/P41②/守恒门),与「成型臂语义照旧」声明矛盾。"""
    return (armed and locked and fp is not None and fp < 1.00
            and board_full)


def _swap_transition_domain(ctx: SwapPlanContext | None) -> bool:
    """锁线转型域谓词(ctx 形态;行 #5 基座臂封堵辖域单一源)。

    消费面 = ``swap_sell_exclusion_reason``(资格分流)/
    ``select_swap_plan``(arm 标注/让渡序)/``assemble_swap_plan_inputs``
    (收窄辖域,经 ``_swap_transition_domain_of`` 原始形态)——辖域判定
    只此一份,禁调用面各写第二份。域外(未锁帧/锁线成型帧 fp≥1.00)
    语义照旧(不动,封堵与收窄均不外溢)。
    """
    if ctx is None:
        return False
    return _swap_transition_domain_of(
        SWAP_TRANSITION_ARM_ENABLED,
        bool(getattr(ctx, 'locked', False)),
        getattr(ctx, 'fp', None),
        bool(getattr(ctx, 'board_full', False)))


def _swap_yield_union_achieved(target_factions: frozenset[str] | set[str],
                               names: set[str] | frozenset[str]) -> int:
    """让渡序度量的并集达成档总数(P79-4)。

    度量域 = target 视图 ∪ SWAP_GUARD_SYSTEMS 的**体系集**(并集去重,
    重叠键计一次),逐体系 achieved 档数求和;计数源 = deployed_bond_
    counts(注册表口径),tier 源 = FACTIONS 自然档表(重叠键仙舟取
    (3,5,7,10),与收窄判定同源),希儿系 = seele_system_formed 二元。
    锁线域 target 视图为收窄键集时度量仍与「all_factions ∪ guard」全量
    并集等价:收窄剔除键 = 未达成键(achieved 恒 0),离场差分恒 0——
    等价性由收窄构造保证,非数值巧合。
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


# ===== 板满换阵补部署计划(M1″ 发射面谓词;与 select_deployments 同族)=====
# 语义出处:(board-full swap redeploy)。
# 结构:发射侧(mandate M1″)与执行侧(CwScreenDeploy 卖出臂)**同函数、
# 同一装配契约**(assemble_swap_plan_inputs),但输入源两侧分轨——发射
# = 决策帧黑板,执行 = last_state + SIFT(装配源契约钉死为执行侧卖出
# 决策实际消费的快照链,禁另起第三路);两侧输入的逐字段对齐由 seam
# 核对批兑现(cw4_m1p_seam_verified 唯一写点),对齐证据是开闸前置
# 义务——「同谓词 ∧ 同输入快照 ⇒ 发射⇔执行可开出卖序」是条件式不变式
# 拒因键(闭集):cap_unreadable / membership_unreadable / input_missing
# (弃权三键,计划空)+ 逐件拒因 fenced_arm_closed / target_keep /
# protected / buy_membership / fresh_buy / post_sell_held。

# 轮内新鲜度排除载体(宿主 = ``GameState.round_fresh_buys``,字段
# 定义注 = kernel/cw_game_state.py;渠道②动作上报,经本模块
# record_fresh_buy 单口):发射位买入时逐名写入的名集,键式 =
# {'phase': (plane, round_num), 'names': list[str]}——位面/轮次推进自动
# 失效(M7 闩键式同构)。写点 = 生产 shop.py 全部 CwActionBuyCardParam 发射位
# 经 ``_emit_buy`` 收口调用(5edcf324)。
# 取舍声明:沿用发射位写入(与 ``cw4_fuel_filler_stall_buys`` 先例同位),
# 被截断器丢弃的买入意图也入排除集 = 过度排除压制合法 swap,方向安全
# (留置合法稳态,发射契约口径),失真经 fresh_buy 拒因可追溯;单调性由
# 义务集排除独立承载,本载体只承担防抖+显影(拒因照记,不宣称切环)。


def _fresh_phase(state: GameState | None) -> tuple:
    """相位键读法(容器读口;None = 缺读缺省 (None, 1))。"""
    if state is None:
        return (None, 1)
    return (plane_of(state), round_num_of(state))


def record_fresh_buy(session: object, gs: GameState | None,
                     name: str) -> None:
    """轮内新鲜度排除登记(买入意图逐名写入;发射位调用)。

    同一发射批的多个买入意图**逐名**入集(防批量买入漏记——漏记 =
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
    """L1 卖侧统一闩读端(r408
    「本轮已买」半边的消费面补全——该半边存活于本载体,
    读面此前仅 deploy 侧换出守卫)。

    读端自治(fail-closed 语义):相位 (plane, round_num) 自
    session 容器 node 读口解析(W6 波 4 黑板容器化:原 last_state 优先/
    shop_state_frame 兜底的双槽解析随黑板槽退役改容器直读——登记相位
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
    """板满换入臂触发谓词(纯函数;判定单一源)。

    两分支任一成立即武装(板满 = 占用数口径,与 M1″ 板满门同链;板不满
    帧不辖——空位由 M1 部署通道直上,无需卖出换血):
    - **必需件滞留**:required_names 非空(目标 comp 带 required_deployed;
      现役两实例 = 希儿系 pair 的 ``pair_target_comp`` 与 COMP_LIBRARY
      静态套「希儿量子」(P2+ 锁线路径),单一源 = ``SEELE_CARRY_CHAR``)
      ∧ 必需件不在板 ∧ bench 存在必需件;
    - **配方完成件滞留**(双轨对锁期通道):方向锁在效(``ctx.locked``,
      终局线锁 ∨ P1 配方对锁,辖域门单点 = ``_completion_swap_ins``)∧
      fp < 1.0 ∧ bench 存在「入板即成型」件——桥池 pair 的
      required_deployed 恒空,双轨期板面义务本体 = 过渡配方(cw_recipe
      模块不变量),完成件压席帧由本分支承接;✗→✓ 严格优(换入后物化
      判据改善才准换;依据 = user_playstyle [20] 配方驱动板面 / [13]
      凑齐优先;出处 = 2026-09-18 sim 实证:配方对锁局板满帧全
      plan_empty)。

    fail 方向:ctx None / 板满缺读 / fp 缺读 = 臂关(不放宽 target 保护,
    与基座臂 fail-closed 同向)。
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
    """换入臂假想面板(form_progress 鸭型位;与 _deploy_advances_form
    同型,只提供折法消费的三个视图槽)。"""

    def __init__(self, board_counts: dict[str, int],
                 deployed_names: set[str]) -> None:
        from types import SimpleNamespace
        self.board = SimpleNamespace(value=dict(board_counts))
        # required 腿席位经行读:假想板上必需件按「已换入」计(臂前提 =
        # 卖后上序底线保证必需件落位;在此不计则判据恒缺腿,臂永不开)。
        self.front_row = SimpleNamespace(
            value=tuple(SimpleNamespace(char_id=n) for n in deployed_names))
        self.back_row = SimpleNamespace(value=())


def _required_swap_victim_completion_holds(ctx: SwapPlanContext,
                                           name: str) -> bool:
    """换入臂 victim 判据保持检验(单一源折法,零自写 AND/OR 内联)。

    = 假想面板(victim 离场 ∧ 必需件按已换入计)下
    ``cw_comps.form_progress(comp, panel) >= 1.0``——与
    ``readiness_form_ok`` 同式同源(成型判据唯一折法契约,含
    OR 组承接同键档规则;禁消费位绕过自写 AND 账,静态套「希儿量子」
    form_tiers 全被 OR 承接的形态由此天然正确)。comp 缺读 = 检验不过
    = 臂不开(保守)。
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
    """配方完成件换入候选集(判据 ✗→✓ 严格优;单帧现算,无状态)。

    辖域门(本函数单点):方向锁在效(``ctx.locked``,终局线锁 ∨ 配方
    对锁,装配单一源)——未对锁帧恒空集,三消费位(触发谓词完成分支/
    victim 让位检验/卖后上序底线)同吃,禁消费位另设第二份门。

    = bench 中「入板即成型」的件名:M 在 bench ∧ 板上无同名 ∧ 假想面板
    (板 ∪ {M})下 ``form_progress(ctx.target_comp) >= 1.0``。前提帧 =
    ctx.fp < 1.0(已成型帧无完成缺口,辖成型/基座臂)∧ 板满(空位帧由
    M1 通道直上)。折法单一源 = form_progress(与必需件 hold 同一折法,
    含 OR 组承接/required 腿;禁消费位自写 AND/OR 内联)。成型腿键 ⊆
    comp 视图键 ⇒ 目标视图成员资格由判据本体蕴含,不另设第二份视图过滤
    (双源禁)。空集 = 通道关(fail 向不换)。

    出处 = 2026-09-18 sim 实证:配方对锁局板满帧全 plan_empty,配方
    完成件压席无解(必需件臂只辖 required_deployed 成员,桥池 pair
    required 恒空);玩法口径 = user_playstyle [20]/[13]。
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

    = 必需件 hold(T-17:假想面板 victim 离场 ∧ required 全体按已换入
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


def swap_sell_exclusion_reason(name: str, ctx: SwapPlanContext | None, *,
                               star: int | None = None,
                               bench: list | None = None,
                               deployed: list | None = None,
                               ) -> str:
    """卖出 victim 的单一判定(逐件;+ 转型臂同位扩展)。

    消费面 = 发射面谓词(select_swap_plan)与执行侧卖出臂(CwScreenDeploy
    `_sell_offtarget_deployed`)——卖出通道统一排除辖域 + **逐件可卖性**
    的唯一交汇点(内聚声明:守恒门/合成素材守卫/
    SWAP_TRANSITION_ARM_ENABLED 的消费点全部落回本函数或其唯一调用链,
    新资格族语义只在此实现一次,发射⇔执行资格自动同值,禁分轨态)。

    返回 '' = 可卖。拒因闭集:
    - 排除族(原样):membership_unreadable / buy_membership /
      fresh_buy;
    - 资格族(per-piece,扩展):target_keep /
      fenced_arm_closed / engines_guard / merge_material_guard /
      star_guard / fp_unreadable。star_guard 在演进降级换血臂武装帧
      对可读星级 >1 让位(arm = ``SwapPlanContext.evolution_swap_armed``,
      谓词单一源 = evolution_swap_arm_trigger;/,判定
      见该分支注)。fenced 件可卖性 =
      ``fenced_on ∨ 转型臂资格``——基座/成型臂经
      ``offtarget_sell_allowed`` 参数化接入(本体零修改,守恒门参数化
      喂 fenced 布尔);转型臂拒因逐件显影,执行侧卖出仲裁同吃本函数
      (:放行参数逐件形态,禁退化标量 fenced_on)。
      扩展:锁线转型域(``_swap_transition_domain``)内经
      键集收窄释放的 candidate 无论 fenced 与否统一落转型臂资格族
      (守恒门/star_guard/素材守卫/卖后上序底线全适用),基座臂提前
      返回在域内封堵;未锁帧与成型帧(fp≥1.00)语义逐位照旧)。

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
    if name in ctx.membership:
        return 'buy_membership'
    if name in ctx.fresh_buys:
        return 'fresh_buy'
    # ---- 逐件资格(基座/成型臂经 offtarget_sell_allowed 参数化接入)----
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        offtarget_sell_allowed,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return ''   # 未注册件不可判羁绊(调用面均已先剔除,防御缺省照旧)
    bonds = set(ch.factions) | set(ch.flows)
    # 锁线转型域(行 #5 封堵辖域,谓词单一源 = _swap_transition_domain):
    # 域内经收窄释放的 candidate 无论 fenced 与否统一走转型臂资格族,
    # 基座臂提前返回封堵——否则「弹性键未达成 + 希儿系经贝洛伯格成形」
    # 类板面可达希儿系泄漏(非 fenced 释放件经基座臂可卖,破成形引擎
    # +拆素材对)。域外(未锁帧/成型帧)语义照旧。
    _trans = _swap_transition_domain(ctx)
    _fp = getattr(ctx, 'fp', None)
    _locked = bool(getattr(ctx, 'locked', False))
    if offtarget_sell_allowed(name, bonds, set(ctx.target_factions),
                              set(ctx.target_cores),
                              fenced_offline_sellable=ctx.fenced_on,
                              protect_names=ctx.protect_names):
        if not _locked:
            return ''   # 未锁帧基座/成型臂语义照旧
        if _fp is None:
            return 'fp_unreadable'   # 锁线帧 fp 缺读两臂同弃权
        if not _trans:
            return ''   # 成型帧(fp≥1.00):成型臂语义照旧(方案 §2.3 不动)
        # 转型域释放件:不取基座臂提前返回,落下方资格族(行 #5)。
    else:
        # 板满换入臂(target 单位分支判定先行;fence 键集辖域 ≠ target
        # 键集辖域——量子/贝成员不在 DEPLOY_FENCE 而在 pair target 键集,
        # 旧「先查 fence 后查 target」次序会把量/贝 target 件挡在臂外):
        # 臂候选排除保护域扩展集(protect_names − target_cores =
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
            # 换入臂(判据必需件/完成件优先于非必需板件):pair/静态套
            # 判据以 required_deployed 在板为必要条件(``Comp.required_
            # deployed`` 字段契约 + seele_system_formed 合取支),必需件
            # 滞留 bench ∧ 板满 = 结构性凑齐失败形态(sim n1000 s91700
            # 基线 12 失败希儿系局主形态);双轨对锁期扩展 = 配方完成件
            # 滞留(桥池 pair required 恒空,``required_swap_arm_pending``
            # 完成分支)。victim 让位条件 = 假想面板(victim 离场 ∧
            # 换入件按已换入计)下成型判据仍满——破坏 = 凑齐倒退不可换;
            # 保持 = 换入后判据 ✗→✓ 严格优(支配改进,无新数值参数)。
            # 让位后落资格族(engines_guard/star_guard/merge 素材守卫
            # 照走,禁直落 fenced 转型臂分支——target 件非转型臂辖域)。
            if not (required_swap_arm_pending(ctx)
                    and _swap_victim_yields_for_swap_in(ctx, name)):
                return 'target_keep'   # target 单位(offtarget 拒因归因,先于臂分支)
        elif not bonds & DEPLOY_FENCE:
            return 'target_keep'
        elif not _trans:
            # fenced 件被基座/成型臂拒 ⇒ 转型臂资格(原 分支):
            if not SWAP_TRANSITION_ARM_ENABLED or not _locked:
                return 'fenced_arm_closed'
            if _fp is None:
                return 'fp_unreadable'   # fp 缺读两臂同弃权(fail-closed)
            return 'fenced_arm_closed'   # fp≥1.00 ∨ 板不满 → 臂关
        # 转型域 fenced off-line 件:同样落资格族(与释放件同族,行 #5)。
    if name in ctx.fw_carry:
        return 'target_keep'   # fw_carry 对称排除
    _deployed = deployed if deployed is not None else ctx.deployed
    _bench = bench if bench is not None else ctx.bench
    _names = {x.char_id for x in _deployed if x is not None and x.char_id}
    # ---- 档位守恒门:逐体系 achieved 档数不减 ----
    _fac = deployed_bond_counts(_names)
    _fac2 = deployed_bond_counts(_names - {name})
    _ach_b = _swap_guard_achieved(_fac, _names)
    _ach_a = _swap_guard_achieved(_fac2, _names - {name})
    if any(_ach_a[k] < _ach_b[k] for k in _ach_b):
        return 'engines_guard'
    # ---- 1★ 限卖(star_guard)----
    # 演进降级换血臂让位(arm 谓词单一源 = evolution_swap_arm_trigger,
    # 装配级计算见 SwapPlanContext.evolution_swap_armed 注):武装帧放行
    # 可读星级 >1 的 victim——分级降级换血语义(弱序星级→费用,
    # G0 非引擎锁定线件/G1 未成型引擎件可动)接入换血机器的参数化面
    # 其余守卫(target/engines/merge/fresh/membership)全保留,
    # 卖出代价轴重推,推导考古走 git 历史。星级不可读恒拒(fail 向
    # 不换,武装不豁免——不可判星级 = 不可判弱序,分级序的
    # 排序输入缺失);未武装帧逐位同旧。
    star_eff = star if star is not None else next(
        (x.star for x in _deployed
         if x is not None and (x.char_id or '') == name), None)
    star_n = star_eff or 1
    if star_eff is None or (star_n > 1
                            and not getattr(ctx, 'evolution_swap_armed',
                                            False)):
        return 'star_guard'   # 星级不可读/非 1★ = fail 向不换(armed 让位见上注)
    # ---- 合成素材守卫:含自身全场域同名同星计数 = 2 未完态拒 ----
    from sr_od.application.currency_war.kernel.cw_vocab import same_star_count
    if same_star_count(name, star_n, _bench, _deployed) == 2:
        return 'merge_material_guard'
    return ''


@dataclass
class SwapPlanContext:
    """swap 计划谓词的共享输入快照(装配函数产物;发射/执行同契约消费)。

    字段语义与装配源:
    - ``target_factions``/``target_cores``:target 视图(双轨口径,装配
      内经 committed_from→decision_target 伪 comp 链,与执行侧卖出决策
      同一条链)。锁线域 = 装配级收窄键集(核心羁绊 ∪ 已达成档承载弹性
      键,行 #4;未锁域 = all_factions 全量逐位同旧)——五消费位同吃
      本字段,单一源;
    - ``membership``:买面义务排除集(单一源 = ``cw_intention.
      locked_buy_membership`` 容量可行截断集 B',cap_hold 现读;与 M4
      燃料集 ``exclude_names`` 同参同源——两侧同吃 B');
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
    deployed: list[Unit]
    bench: list[BenchSlot]
    cap: int | None
    front_slots: int = DEPLOYED_FRONT_CAPACITY
    back_slots: int = DEPLOYED_BACK_CAPACITY
    fenced_on: bool = False
    #: 成型度单一源快照(form_progress;None = 缺读 ⇒ 转型臂 fp_unreadable
    #: 弃权,两臂同 fail-closed)。发射⇔执行同函数装配 ⇒ 同帧同值。
    fp: float | None = None
    #: 换血域方向锁 = 终局线锁 ∨ P1 配方对锁(装配单一源 =
    #: ``assemble_swap_plan_inputs``;配方对锁语义见 strategy-docs/
    #: 24_deploy_segment.md 换血节)。终局线锁判定本身单源仍归
    #: strategy-docs/17_stall_form_spend_authority.md §1.1(两词显式分名,
    #: 禁按本字段反推终局线锁口径)。
    locked: bool = False
    #: 板满(占用数 ≥ cap,与 fenced 臂同一派生链;转型臂触发前提之一)。
    board_full: bool = False
    #: 锁定线语境豁免武装位(配方底线门):装配自
    #: ist.locked_comp(经 cw_intention.locked_line_recipe_floor_conflict,
    #: 与 ``locked`` 同点同源装配——发射⇔执行⇔sim 意图三面经同一装配
    #: 同帧同值)。缺省 False = swap 上序(卖后假想态复用
    #: select_deployments_reasoned)行为逐位同旧。
    recipe_floor_lock_exempt: bool = False
    #: 装配实际消费的 target comp 视图本体(双轨口径:双轨期 =
    #: decision_target 伪 comp,定型后 = strategy_state.target_comp;
    #: None = 手装 ctx/装配缺读)。消费面 = mandate 部署执行放行判定的
    #: 档关键件判读源(落地审 F2:判读源与本计划的 comp 同源,禁放行判定
    #: 另读 state_of 二份——双轨帧两源可分歧,判据源分裂 = 同型分叉)。
    target_comp: object | None = None
    #: 演进降级换血臂武装位(缺省 False = 逐位同旧;装配函数单点计算,
    #: 执行侧 bench 域分轨面经 :func:`evolution_swap_arm_trigger` 现读
    #: 重算覆写)。True 时 :func:`swap_sell_exclusion_reason` 的
    #: star_guard 对可读星级 >1 的 victim 让位——演进层 分级
    #: 降级换血语义(弱序星级→费用)接入换血机器的参数化面,辖域 =
    #: 锁线转型域 ∧ 板满 ∧ bench 在册线件待上(
    #: 语义宿主 = kernel.cw_evolution 的分级保护机器(该模块已随 W8 退役删除,历史语义归 git),本臂不新增
    #: 资格语义,只放开既有 1★ 限制并以其余守卫全保留为界)。
    evolution_swap_armed: bool = False
    #: 锁线转型域事实快照(装配时点 = ``_swap_transition_domain_of`` 同点
    #: 现算):``target_factions`` 是否经收窄。为什么存快照而
    #: 非消费位现算:域谓词含 board_full 腿,M1″ 卖出后补部署的重 derive
    #: 帧(board_full 翻假)现算必丢收窄辖域——域辖域是**计划时点事实**,
    #: 不可从卖出后状态重推;消费面(mandate 发射载荷/sim R1-b 重 derive
    #: 钉定参)读本字段。手装 ctx 缺省 False = 域外(与裸构造语义一致)。
    transition_domain: bool = False
    #: 判据必需件名集(装配单一源 = 目标 comp ``required_deployed``;与
    #: mandate_v1 deploy_plan ``_deploy_plan_inputs`` 同源同值)。消费面 = select_swap_plan
    #: 卖后上序(必需件首桶,使「卖了换血后」的首个空位优先落必需件——
    #: 不穿则换血腾出的位仍会被普通成员按旧序占走)、
    #: ``swap_sell_exclusion_reason`` 的板满换入臂,与执行侧卖出后补部署
    #: 重 derive 的同名穿参(cw_screen_deploy R1-b 回落臂;发射⇔执行
    #: 同源第三路)。
    required_names: frozenset[str] = frozenset()


# ===== 换阵可兑现谓词(F1 单一源;发射-执行接缝合拢)=====
# 语义出处:无方向幻影部署软卡死事故。
# 为什么存在:发射面(select_swap_plan)与执行面(CwScreenDeploy 卖出臂两门)
# 对「这场换阵能否兑现」判定不同源时,发射面会发出执行面必然空转的
# RunDeploy(2026-09-08 实机软卡死 run_20260908_210431:无方向态
# 发射 53 次幻影部署,执行 0 次真实换阵,交替活锁 15 分钟)——本谓词是
# 「发射⇔执行同谓词」的单一实现,两面各消费其合取支,禁任一面自写
# 第二份口径。支出出口总图防双改清单的共享单点对账持久家(推导考古走 git 历史)
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
    白厄类空羁绊单卡 comp 只有 core_chars)——只看 factions 会把
    「有方向(核心件)」误标 no_direction;执行面旧门只看 factions 是
    同族窄口径,一并收口(有向 core-only 帧卖出臂从结构性关闭
    变为可开门,方向同收口语义,的伴随申报面)。
    """
    return ctx is not None and bool(ctx.target_factions or ctx.target_cores)


def target_view_char_is(ctx: SwapPlanContext, char_id: str) -> bool:
    """单件目标视图判定(收口后唯一实现;fw_carry 口径 = **含**)。

    fw_carry 收口依据(择一裁决,申报持久家):①上序裁判
    select_deployments 的 is_tgt 判定含 fw_carry(本文件 :474,框架件
    r120 起是部署一等公民)——为 fw_carry 件腾位是可兑现的换阵,执行面
    不认它则发射⇔执行再次分叉;②卖出侧 swap_sell_exclusion_reason 对
    fw_carry 板件同样 target_keep 保护(对称排除)——同口径
    才自洽;③旧执行面 _is_tgt_char 不含 fw_carry 正是本批要消灭的
    「同一判据两份实现」病样本,收口 = 向 kernel 口径(含)对齐。
    有向态行为变化面(如实申报):执行面 max_sell 上限自此计 fw_carry
    bench 件,可多卖一件 off-target 为其腾位——腾位对象是上序真会部署
    的件,方向安全(用例预期更新随批)。
    """
    cid = char_id or ''
    if cid in ctx.target_cores or cid in ctx.fw_carry:
        return True
    ch = CHARACTERS.get(cid) if cid else None
    return ch is not None and bool(
        (set(ch.factions) | set(ch.flows)) & ctx.target_factions)


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
    """合取③:板上存在其资格臂下可卖的 off-target 件。

    逐件判定 = swap_sell_exclusion_reason 单一源(返 '' = 该件在当前
    臂态下可卖且必为 off-target——target 视图件被该函数 target_keep
    拒,语义内含)。未识别/未注册件不入候选(select_swap_plan victim
    扫描同款:不可判羁绊即不可判资格)。与发射面 victim 扫描同构同源,
    差异仅在输入域(发射面 ctx 帧域 / 执行面 SIFT 现读域,分轨既定)。
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
    """换阵可兑现谓词(三合取;发射⇔执行同吃,F1 单一源)。

    realizable ⟺ ①目标视图非空 ∧ ②bench 存在目标视图件 ∧ ③板上存在
    其资格臂下可卖的 off-target 件(钉死的
    三合取;原「fenced 臂开 ∨ bench 存在目标视图件」形态
    会使执行面卖出臂在
    「fenced 开 ∧ bench 无目标件」帧仍跳过,发射⇔执行在有向成型态再次
    分叉,故改写)。

    消费面与合取支的对应:
    - 发射面(select_swap_plan)门①显式弃权(abstain no_direction);门②
      域外(非锁线转型域)显式弃权(abstain no_bench_target)——转型域
      跳过门②:转型臂自带更强的卖后上序底线(post_sell_offline),计划
      非空 ⟹ up2 含 target 视图件 ⟹ bench 必有目标视图件,门②被底线
      蕴含,预判只会把逐件显影挤成单键;门③由 victim 扫描自然承载
      (逐件同判 swap_sell_exclusion_reason,扫描空即计划空,语义等价
      且逐件拒因保留显影);
    - 执行面(CwScreenDeploy 卖出臂两门)消费本函数与合取②计数;
    - sim 镜像经 select_swap_plan 自动继承。

    :returns: (ok, why)。why ∈ SWAP_REALIZABLE_WHY(拒因闭集)或 ''
        (ok=True)。ctx None 按无方向弃权(fail-closed,与装配不可得
        「不静默发射」同向)。
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
    基座合格 / 'formed' = 成型臂(fenced_on)/ 'transition' = 转型臂)。
    胜出序 = victim 序首个可成交者,arm 只随胜出者标注。序分域:锁线
    转型域 = P79-4 让渡序(结构档边际贡献升序 → 星级升序 → deployed
    板槽位序);域外 = 现行 1★ 优先 + 扫描序稳定序(/
    0534 语义照旧,零行为差)。
    """
    sell_names: list[str] = field(default_factory=list)
    up_bench: list[int] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    abstain: str = ''
    arm: str = ''

    @property
    def nonempty(self) -> bool:
        return bool(self.sell_names) and bool(self.up_bench)


def swap_plan_up_names(plan: SwapPlan | None,
                       ctx: SwapPlanContext | None) -> list[str]:
    """``SwapPlan.up_bench`` 下标 → 备战名单(名字级单一换算)。

    ``up_bench`` 元素是 ``ctx.bench``(**装配时点紧缩占用序**)的下标、
    非名字(F3:消费面按对象断言会脆,必须先换名再核对/记录)——本
    函数是该换算的唯一实现,记录面(sim ``_m1p_plan_and_record`` 的
    ``up_names``)与发射载荷面(mandate ``cw4_m1p_plan_pending['up']``)
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
    """演进降级换血臂触发谓词(纯函数,语义)。

    最小等效通道的准入面:「锁线转型域 ∧ 板满 ∧ bench 有在册线件待上」
    (修向「板满∧bench有locked线core→发射卖线外件上core事务」
    的准入三元)。三面消费(装配级缺省计算 = 发射面 mandate M1″ 与
    sim 引擎;执行侧 CwScreenDeploy 卖出臂经本函数用 SIFT 现读 bench 域
    重算覆写)——同函数同谓词,发射⇔执行资格自动同值,禁分轨态
    (同款纪律)。

    各腿单一源与 fail-closed:
    - ``locked``/``fp``/``board_full`` = 装配 ctx 同源字段(fp 缺读 =
      臂关,与转型臂 fp_unreadable 两臂同弃权口径一致;
      fp≥1.00 = 线已成型无完成缺口,臂辖域外);
    - ``membership`` = ``cw_intention.locked_buy_membership``(锁线帧
      采购集正典口径,与 M4 燃料集/卖出义务排除同参同源;None = 缺读
      臂关)。bench 待上判定用买面义务集而非部署面 line_members:
      集合构成声明 = 存-2 裁决两口径分域的在册复用(entry.emit 装配
      注),本臂不新增第三口径;
    - 「在册 core 待上」= bench 占用件名 ∈ membership(采购集=线名册
      全集,含 core∪shared∪替班;能否真上场不由本谓词答——上序裁判 =
      select_swap_plan 的卖后 select_deployments 底线,结构性排除
      「白卖」形态)。

    与转型域谓词的偏差申报(F6):本谓词内联三腿(locked∧fp<1.00∧板满)
    未消费 ``_swap_transition_domain_of``(其辖域含
    SWAP_TRANSITION_ARM_ENABLED 回滚腿)。行为安全性由可达性拓扑兜住:
    ENABLED=False 时 select_swap_plan 的转型域全关(fenced_arm_closed
    全拒),本臂即便 armed 亦无计划可成——偏差无行为面;域定义变更时
    本谓词须随 对账,禁静默分叉。

    :param bench: bench 域(None 缺省 = 空域臂关);发射面 = 决策帧
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
        transition_domain: bool | None = None,
) -> SwapPlanContext | None:
    """swap 计划输入装配单一源(发射侧与执行侧**同函数、同一装配契约**);

    装配源契约(对抗收口方案钉死原话,last_state 链退役批
    措辞更新)= 执行侧卖出决策实际消费的快照链,不用 PrepObservation
    另起一路:board/fp 消费调用方传入的 ``state``(执行侧/发射侧/sim
    引擎三方均传容器单例 game_state_of——装配源换源把执行侧从
    旧滞后帧链切容器,sim 侧引擎直写容器);deployed/
    bench 消费调用方现读(执行侧 = SIFT 读面,发射侧 = PrepObservation
    帧)。派生逻辑(target 视图双轨口径/fenced 臂/义务排除集/保护域)全在
    本函数,两侧禁自写第二份。两侧输入的逐字段对齐由 seam 核对批兑现
    (对齐证据 = 开闸小批前置义务,挂账 IMPL_REPORT),核对通过前发射
    位保持关闭。
    追加派生:锁线域装配级键集收窄(``locked_redeploy_
    target_keys``)——收窄键集自本函数单一源同喂五个消费位,消费位禁
    各自内联第二份。

    返回 None = 装配不可得(target 视图/板面字典缺读),调用方按
    谓词弃权处理(计划空,不静默发射)。
    ``deployed``/``bench`` = 容器形状(行域 Unit / 占席条目 BenchSlot,
    P4 容器形;发射侧 = 决策帧容器现读,执行侧 = SIFT 现读域,
    装配源契约分轨不变)。

    :param deployed_n: 板满计数覆盖(执行侧喂 ``swap_arm_deployed_count``
        真读槽位口径;None = 按 ``deployed`` 占用件数计——同一占用数
        口径,含 SIFT 未识别占位件)。
    :param transition_domain: 锁线转型域事实钉定(M1″ 卖出后
        补部署重 derive 路径专用):None(缺省)= 域谓词现算,逐位同旧;
        True/False = 调用方钉域事实(计划时点快照,``SwapPlanContext.
        transition_domain`` 同源)——为什么可钉:域谓词含 board_full 腿,
        卖出后帧 board_full 翻假,现算必丢收窄辖域,而收窄辖域是计划
        时点事实;钉定仍经本装配函数单一传导收窄(禁消费位内联第二份)。
        非 m1p 显式动作轮推广原则(定谳记录-deploy围栏.md 攻击线 B6,
        第六节 4 条):同一显式轮内,轮首/事务决议时点与轮末残余补部署
        **同吃同一域事实**(快照在决议时点取,禁补部署侧对卖出后帧现算
        ——与 m1p 局 18 实证「现算丢收窄辖域」同形);本参数即该原则的
        m1p 接线形态,非 m1p 显式轮残余 fill 接线时复用同参同源钉定,
        禁在消费位另立第二快照载体。
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
    # decision_target 伪 comp,定型后走 strategy_state_of(session).target_comp)
    tgt_comp = None
    try:
        if not committed_from(session, state):
            # W6 波3:state 已切容器形态,decision_target 直吃容器(桥退役位)。
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
    # fenced 臂(fp 单一源 form_progress,板满 = 占用数 ≥ cap 占用数
    # 口径;cap 现算 = state.max_units() 单点收口链——与 select_swap_plan
    # 板满门同源,禁经调用方 cap 参数分叉出第二口径;执行侧 cap=None
    # (不消费谓词 cap 门)帧同吃现算)。fp/locked/board_full 同点装配:
    # 转型臂输入与 fenced 臂同源同值(装配单一源)。
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    ist = getattr(strategy_state_of(session), 'v3_intention', None)
    locked = bool(getattr(ist, 'locked_comp', None)) if ist is not None \
        else False   # 方向锁第一腿 = 终局线锁(判定单源归 17_stall_form_
    # spend_authority §1.1;字段终值见下方推广,不再等于本腿)。
    # 方向锁推广(双轨对锁期):P1 配方对锁(ist.p1_pair 非空,
    # 意向锁定产物;冻结闩 p1_pair_frozen 钉向)与终局线锁同为
    # 「方向锁在效」。换血域前提按辖域对齐:双轨期板面义务本体 = 过渡
    # 配方(cw_recipe 模块不变量),配方对锁帧不开转型域 = 配方完成件
    # 压席无合法 victim(2026-09-18 sim 实证:配方对锁局板满帧全
    # plan_empty,fenced_arm_closed/target_keep 主导;判定尺 =
    # user_playstyle [20]/[13])。演进降级换血臂不受影响:pair 帧
    # membership 空集(locked_buy_membership 未锁帧缺省)使其 member 门
    # 恒关,辖域仍在终局线。店侧 S_spec 收窄
    # (mandate.swap_transition_narrow_frame)直读 ist.locked_comp,
    # 刻意不随本推广(买侧收窄辖域不变,对称申报见其 docstring)。
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
        except Exception:   # noqa: BLE001  成型度不可得 = 臂关(保守)
            _fp = 0.0       # fenced 臂维持 0.0 保守侧;fp 留 None ⇒ 转型臂
            # fp_unreadable 弃权(fp 缺读两臂同 fail-closed)
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
    # 锁定线语境豁免武装位(配方底线门):只与终局线锁第一腿
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
    # 域事实单点:缺省 = 谓词现算(逐位同旧);钉定参在场 = 计划时点
    # 事实覆盖(仅 M1″ 卖出后重 derive 路径传入,见参数 docstring)。
    _domain = _swap_transition_domain_of(
        SWAP_TRANSITION_ARM_ENABLED, locked, fp, board_full) \
        if transition_domain is None else bool(transition_domain)
    if _domain:
        # 锁线**转型域**装配级键集收窄(读法 D;
        # 辖域钉转型域 = 落地审 F1 修订:锁线∧成型帧(fp≥1.00)键集回全量,
        # 成型臂释放件不经收窄绕过资格族)。收窄只发生在本装配函数(单一
        # 源),产物同喂五个消费位(offtarget-②/宽口径 target 归因/
        # select_deployments is_tgt/_bench_is_target/post_sell_offline
        # 底线)——任一消费位再各自收窄即双源,禁(读法反例存档见方案
        # §3.1)。计数域 = 过滤后 deployed(与 ctx.deployed 同一列表语义)。
        _dep_names = {d.char_id for d in deployed
                      if d is not None and d.char_id}
        target_factions = locked_redeploy_target_keys(
            target_factions,
            frozenset(getattr(tgt_comp, 'factions', None) or ()),
            _dep_names)
    # 演进降级换血臂(装配级缺省计算;执行侧 bench 域分轨面在
    # cw_op_deploy 卖出臂 SIFT 现读后经同一触发函数重算覆写,声明见
    # evolution_swap_arm_trigger)。
    _bench_occ = [b for b in (bench or []) if b is not None]
    evolution_armed = evolution_swap_arm_trigger(
        membership, _bench_occ,
        locked=locked, fp=fp, board_full=board_full)
    return SwapPlanContext(
        target_factions=target_factions,   # 转型域 = 收窄键集(行 #4);域外(未锁/成型帧) = all_factions 全量
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
        board_full=board_full,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        target_comp=tgt_comp,
        evolution_swap_armed=evolution_armed,
        transition_domain=_domain,   # 装配时点域事实快照(字段注释/)
        required_names=frozenset(
            getattr(tgt_comp, 'required_deployed', ()) or ()),
    )


def select_swap_plan(ctx: SwapPlanContext | None,
                     reasons_out: dict[str, str] | None = None,
                     *,
                     select_up: Callable[..., tuple[list[int], list[int],
                                                    dict[int, str]]],
                     ) -> SwapPlan:
    """板满换阵补部署计划谓词(M1″ 发射面;选人判定同族纯函数)。

    语义(组合式,零新启发式)::

        swap 计划非空 ⟺ cap 满(占用数口径)∧ 义务/新鲜排除后存在
        合格 victim ∧ 对「卖出 victim 后假想状态」复用选人判定
        判 up 非空

    - **板满门 = 占用数口径**:``,len(deployed)``(占用件数,含 SIFT
      未识别 char_id='' 占位件)≥ cap——与执行侧 cap 门「禁用衍生计数」
      同向(占用数 = 非 None 件逐件计;禁 ``len(deployed_cids)`` 衍生
      集,SIFT 未识别占位件漏计 = 板实满判未满);
    - **victim 资格** = 逐件单一判定 ``swap_sell_exclusion_reason``(义务
      集排除 ``buy_membership``/缺读弃权 ``membership_unreadable`` +
      轮内新鲜度 ``fresh_buy`` + per-piece 资格族——基座/成型臂经
      ``offtarget_sell_allowed`` 参数化、转型臂经守恒门/素材守卫/1★
      守卫逐件放行,见该函数 docstring;fenced 臂态经装配注入);
    - **转型臂胜出者的卖后上序底线**:up ∩ target 视图 ≠ ∅(拒因
      ``post_sell_offline``);base/formed 臂维持现状判 up 非空;
    - **上序 = 组合语义**:对卖出后假想板面复用 ``select_up`` 注入的选人
      判定(单一源 = mandate_v1 deploy_plan.select_deployments_reasoned;
      围栏/成对/填空/点火序/核心桶/cap/同名去重/配方底线
      全套留置规则就是上序的最终裁判);底线规则留 bench 的件**不作
      上序候选**(拒因 ``post_sell_held``),「白卖一件板面变弱」形态
      在谓词内不可达;
    - **cap 缺读**(``cap is None``)⇒ 弃权 ``cap_unreadable``,与 M1/
      M1′ vacancy=0 门同 fail-closed(发射契约);
    - **换阵可兑现门(F1;发射-执行接缝合拢)**:合取①目标视图
      非空(假 ⇒ 弃权 ``no_direction``,2026-09-08 实机无方向幻影部署
      软卡死的直接根除位)∧ 合取②bench 存在目标视图件(假 ⇒ 弃权
      ``no_bench_target``,根除 base/formed 臂「上序非目标件填空」的
      执行面必然空转形态,如实申报的行为变化面)。合取③(板上存在
      可卖 off-target 件)由 victim 扫描自然承载(逐件同判
      swap_sell_exclusion_reason,扫描空即计划空),逐件拒因保留显影。
      判定实现单一源 = swap_realizable 合取支函数族,禁第二份口径。
      弃权序:供给缺读面(input_missing/cap/membership,装配侧更早
      失败点)先报,语义谓词门在其后。

    :param reasons_out: 传入 dict 时逐件拒因(名 → 拒因键)写入;
        plan 级弃权以键 ``'(plan)'`` 写入(既有惯例)。
    :param select_up: 选人判定注入参(必填;单一源 = mandate_v1
        deploy_plan.select_deployments_reasoned,包依赖矩阵禁
        kernel→strategies 直引,由调用方注入同一函数对象——契约同
        cw_launch_admission line_members 先例)。
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
    # 拒因(fenced_arm_closed 等)挤成 plan 级单键,丢显影)。
    # 合取②辖域修正:锁线转型域跳过——转型臂自带更强的卖后上序底线
    #(post_sell_offline,逐 victim 判 up ∩ target ≠ ∅),与合取②在
    # 「bench 无目标视图件」帧同判计划空(底线把 victim 全拒),plan
    # 级预判只会把逐件显影挤成单键;且 plan 非空 ⟹ up2 含 target 视图
    # 件 ⟹ bench 必有目标视图件,合取②被底线蕴含,发射⇔执行零分叉。
    _trans = _swap_transition_domain(ctx)
    if not target_view_present(ctx):
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'no_direction'})
        return SwapPlan(abstain='no_direction')
    if not _trans and bench_target_count(ctx) == 0:
        if reasons_out is not None:
            reasons_out.update({'(plan)': 'no_bench_target'})
        return SwapPlan(abstain='no_bench_target')
    occupied = len(ctx.deployed)   # 占用数口径(含未识别占位件)
    if occupied < ctx.cap:
        return SwapPlan(reasons=reasons)
    # 锁线转型域(辖域谓词单一源 = _swap_transition_domain):域内
    # arm 标注恒 'transition'(行 #5/N5)且 victim 序 = P79-4 让渡序。
    _dep_names = {x.char_id for x in ctx.deployed if x.char_id}
    victims: list[tuple[tuple, Unit, set[str], str]] = []
    for _scan, d in enumerate(ctx.deployed):
        name = d.char_id or ''
        ch = CHARACTERS.get(name) if name else None
        if ch is None:
            continue   # 未识别件不可判羁绊,不入 victim(执行侧同款)
        bonds = set(ch.factions) | set(ch.flows)
        # 逐件单一判定(排除族∪资格族;发射⇔执行同函数,同位扩展):
        # offtarget_sell_allowed 经判定函数参数化接入(fenced 布尔在函数
        # 内喂入),谓词不再自写第二份资格语义(禁分轨态)。
        _rej = swap_sell_exclusion_reason(name, ctx)
        if _rej:
            reasons[name] = _rej
            continue
        # arm = 胜出者资格族标注:fenced 件在 fenced_on(fp≥1.00)
        # 帧 = 成型臂,否则(其唯一可卖路径)= 转型臂;fp 单值互斥 ⇒ 无歧义。
        # 三轮 N5:转型域经收窄释放且过资格族的非 fenced 件
        # 恒标 'transition'(禁落 'base')——swap_arm_transition_trigger
        # 分键归因依赖此标注。
        _arm = ('formed' if ctx.fenced_on else 'transition') \
            if bonds & DEPLOY_FENCE else 'base'
        if _trans:
            _arm = 'transition'
        # victim 序(P79-4 让渡序;的
        # 「1★ 优先单键」在其辖域外照旧):转型域 = 结构档边际贡献升序
        # (纯结构计数,度量单一源 = swap_yield_contribution)→ 星级升序
        # → ctx.deployed 板槽位序首个(显式定义,零新排序键);资格门与
        # 排序键正交(排序治「先换谁」、资格治「能不能换」)。域外键 =
        # 旧 1★ 优先 + 扫描序稳定序,逐位同旧。
        _contrib = swap_yield_contribution(
            ctx.target_factions, _dep_names, name) if _trans else 0
        victims.append((
            (_contrib,
             0 if (d.star or 1) <= 1 else 1,
             _scan),
            d, bonds, _arm))
    victims.sort(key=lambda t: t[0])

    # bench 件是否 target 视图(转型臂卖后上序底线:up ∩ target ≠ ∅;
    # 判定单一源 = target_view_char_is,fw_carry 口径收口后禁第二实现)
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
        # 换入臂卖后上序底线:臂武装帧(up 空间 = 本臂腾出)卖后上序必须
        # 真兑现换入对象——required 件直接认名;完成件按**实际落位复检**
        # (该 victim 离场 ∧ 该 up 名入板后成型判据满,``_seat_completes_
        # form``):候选集成员资格不足以防「同属候选的普通成员占位」白卖,
        # 须绑定卖出 victim 成对兑现。辖域 = ``required_swap_arm_pending``
        # 真帧——required 在板帧完成分支仍可武装(有意设计,
        # test_cw_swap_pair_domain 完成件让位锁钉定),此帧底线同样会辖;
        # 谓词假帧不辖,逐位同旧。
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
        # victim;最后一个 victim 的留置拒因保留在 reasons 显影。
    if reasons_out is not None:
        reasons_out.update(reasons)
    return plan


# ============================================================
# 候裁9 词汇迁入(原 kernel/cw_state.py;第 5 归宿):板上唯一性守卫
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
