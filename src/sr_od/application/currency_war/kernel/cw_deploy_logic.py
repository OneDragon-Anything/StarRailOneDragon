"""deploy 域判定纯逻辑(支撑观测/新鲜度账本/唯一性键;单一源)。

部署「选人 + 落位」计划已迁策略层(design 2026-09-20-benchchar-retirement
§2.2 落位决策权归策略层):单一源 =
``strategies/impl/mandate_v1/deploy_plan.py``(``select_deployments``/
``select_deployments_reasoned``/``has_deployable``/``can_deploy_single``/
落位策略 ``deploy_row_pref``/``deploy_slot_plans``/出战链计划入口)。
换阵计划链(select_swap_plan 族)已随部署统一批丁纳入统一管理删除——场上去留 =
统一部署搜索定型单属(unified-deploy-order §2.7);本模块现役面 =
其历史消费的判定 helper(围栏集/点火增益/配方底线门/供给谓词,随七桶
选人退役批次处置)、fresh 账本族(差分执行器新鲜度守卫 + L1 卖侧排除)、
board_unique_key(统一搜索枚举基本单位)、engines_count 族(过渡体系
机制事实)、deployed_bond_counts/board_target_line_weight(支撑观测)与
swap_bond_gate_domain_of(P88 买侧收窄谓词源)。

这里只收**纯决策**。输入 = 状态容器形状(bench = 占席条目 ``BenchSlot``
紧缩序,身份经 ``bench_slot_unit`` 解包;deployed = 行域 ``Unit``,
benchchar-retirement P4 状态容器形),身份可判(char_id 空串=未识别,
围栏语义「照旧上」保留)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    SIDE_PICK_DUAL_BONDS,
    side_pick_bond,
)
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    game_state_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_system_cards import SYSTEM_CARDS

if TYPE_CHECKING:

    from sr_od.application.currency_war.kernel.cw_game_state import (
        Unit,
    )

#: 过渡体系阈值(仙舟3/列车2/DOT2;三羁绊(阵营,阈值)对从 SYSTEM_CARDS 派生
#: (排除 seele 卡——希儿系是 deployed 单卡判定非阵营计数);
#: tier 阈值经 FACTIONS 注册表,单一源。
#: ⚠️ 遗留副本(迁移计划原文已删,git 历史可溯):
#: 权威副本 = knowledge/cw_engine_facts.TRANSITION_TRAITS(同派生式,零字面双源);
#: 本副本仅为 sim/旧判据消费点保留;权威副本删除后随之清理;勿新增消费。
TRANSITION_TRAITS: tuple[tuple[str, int], ...] = tuple(
    (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
    for card in SYSTEM_CARDS.values() if card.card_id != 'seele'
)

#: 希儿系放大器阵营(量子/贝——伤害在希儿技能层,放大器非独立伤害源,
#: transition_combos.md 四体系表;桑博=贝+DOT 双籍是常态不是边界)
#: (希儿系体系键 SEELE_SYSTEM_KEY 已随 kernel swap 机器纳入统一管理删除:历史
#: 消费 = 让渡序度量域/守恒门,现役单卡体系键 = deploy_search 私有
#: 副本,统一搜索计分面自足。)
SEELE_AMP_FACTIONS: frozenset[str] = frozenset({'量子同频', '贝洛伯格'})


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
    终局阵容名单成员 ∪ 终局键集标签命中外部件(判定核 = ``_bond_gate_support_count``
    内联标签命中判定;
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


# (点火增益/配方底线门/仙舟供给谓词/围栏集(DEPLOY_FENCE)与七桶选人
#  消费面(cap_roomy_of/tier_completes/ignition_gain/recipe_floor_holds/
#  xianzhou_supply_exists/RECIPE_FLOOR_*/deploy_target_sets/residual_
#  fill_plan)已随部署统一批丁丁批纳入统一管理删除——unified-deploy-order §2/§4:
#  选人 = 统一部署搜索定型,围栏/底线门/点火序 = 旧线性序补丁史;
#  deployed_bond_counts/board_target_line_weight 支撑观测面保留。)


def deployed_bond_counts(deployed_cids: set[str]) -> dict[str, int]:
    """场上羁绊计数(件级;board 域标签单一源)。

    消费面 = 卖出评估器支撑判定与推判重放板面重推导(原七桶选人/
    swap 计划消费点已随部署统一批丁纳入统一管理删除;未注册名不计——无名可判
    即无阵营信号,件本身的去重/fail-open 由消费面管)。
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

# (换阵卖出义务分支 fenced_swap_arm_of 与转型域双门件(SWAP_GUARD_SYSTEMS/
#  _swap_guard_achieved)已随部署统一批丁纳入统一管理删除——unified-deploy-order
#  §2.7/§4 kernel swap 机器行;判别子 swap_bond_gate_domain_of 保留 =
#  P88 买侧收窄谓词源(mandate_v1.swap_transition_narrow_frame 消费)。)


def swap_bond_gate_domain_of(locked_core: bool, fp: float | None,
                             board_full: bool) -> bool:
    """转型域判别子(原始字段形态;单一源;design §2.0 三合取)。

    = 终局阵容锁定 ∧ fp < 1.00 ∧ 板满(原配方对分支②已随配方决策层
    退役消亡)。
    消费面 = mandate_v1 ``swap_transition_narrow_frame``(P88 买侧收窄
    谓词源)——判定只此一份,禁各消费位自写第二份合取;域语义与分支
    继承的完整论证见 git 历史(swap 机器纳入统一管理批前 docstring)。
    """
    return bool(locked_core) and fp is not None and fp < 1.00 and board_full


# (ctx 形态判别子 swap_bond_gate_domain / fenced_swap_gate_open / 让渡序
#  度量对(_swap_yield_union_achieved/swap_yield_contribution,P79-4)已随部署
#  统一批丁纳入统一管理删除:换谁下 = 统一部署搜索定型单属,独立让渡度量退役。)


# (板满换阵补部署计划头注(M1″ 动作发出面谓词,assemble_swap_plan_inputs
#  装配契约与拒因键闭集)已随 kernel swap 机器纳入统一管理删除;下方 fresh 账本族
#  保留——消费面 = 差分执行器新鲜度守卫(D2-17)与 L1 卖侧排除,拒因
#  fresh_buy 随 swap 机器退役,账本防抖语义由统一拖动链继续消费。)

# 轮内新鲜度排除载体(宿主 = ``GameState.round_fresh_buys``,字段
# 定义注 = kernel/cw_game_state.py;渠道②动作上报,经本模块
# record_fresh_buy 唯一入口):动作发出点买入时逐名写入的名集,键式 =
# {'phase': (plane, round_num), 'names': list[str]}——位面/轮次推进自动
# 失效(M7 标志键式同构)。写点 = 生产 shop.py 全部 CwActionBuyCardParam 动作发出点
# 经 ``_emit_buy`` 收束调用(5edcf324)。
# 取舍声明:沿用动作发出点写入(与 ``cw4_fuel_filler_stall_buys`` 先例同位),
# 被截断器丢弃的买入意图也入排除集 = 过度排除压制合法 swap,方向安全
# (留置合法稳态,动作发出契约口径),失真经 fresh_buy 拒因可追溯;单调性由
# 义务集排除独立承载,本载体只承担防抖+暴露(拒因照记,不宣称切环)。


def _fresh_phase(state: GameState | None) -> tuple:
    """相位键读法(状态容器读口;None = 缺读缺省 (None, 1))。"""
    if state is None:
        return (None, 1)
    return (plane_of(state), round_num_of(state))


def record_fresh_buy(session: object, gs: GameState | None,
                     name: str) -> None:
    """轮内新鲜度排除登记(买入意图逐名写入;动作发出点调用)。

    同一发出批的多个买入意图**逐名**入集(防批量买入漏记——漏记 =
    卖出环切不断,防抖失效静默)。键式见 ``GameState.round_fresh_buys``
    (kernel/cw_game_state.py 字段注)。宿主解析与旧载体同构:gs 在场 =
    写 gs 字段(调用方契约 = 状态容器单例);gs 缺席 = session 状态容器读口兜底
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
    session 状态容器 node 读口解析(黑板槽停用后状态容器直读——登记相位
    写端 ``record_fresh_buy._fresh_phase`` 本就取状态容器读口,读端同源消
    过渡期双源窗),不消费消费位显式传轮——``current_round`` 漏接入调用帧
    不再静默放行(对 V2-09 在 L1 硬面的显式翻转;v1 缺口 C:漏接入调用
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


# (kernel swap 机器(required_swap_arm_pending / _HypotheticalPanel / victim 守卫族 /
#  swap_sell_exclusion_reason / SwapPlanContext / target 与 support 视图 / SwapPlan /
#  swap_plan_up_names / evolution_swap_arm_trigger / assemble_swap_plan_inputs /
#  bond_gate 门族 / SwapGroupOrder / _select_swap_group_plan / select_swap_plan)
#  已随部署统一批丁纳入统一管理删除:要不要换/换谁下 = 统一部署搜索定型,
#  kernel swap 资格链与让渡序的独立度量退役——unified-deploy-order §2.7/§4;
#  被换下者回 bench 由卖出场景按统一让位序处置,让渡序消费面同批改接。
#  保留:swap_bond_gate_domain_of(P88 买侧收窄谓词源,mandate.swap_
#  transition_narrow_frame 消费)/ fresh 账本族 / board_unique_key /
#  engines_count 族 / deployed_bond_counts / board_target_line_weight。)
# ============================================================
# 板上唯一性守卫
# board_unique_key(唯一活消费方 = 部署围栏,本模块同域)。
# ============================================================



def board_unique_key(bc: Unit) -> str | None:
    """板上同名唯一性判据键(设计裁定:场上同角色仅 1;P4 状态容器形重写:
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
