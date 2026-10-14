"""板满/等待件谓词(arm1_existence 触发信号)+ 目标线 K/零重叠 +
「挂后台效果」资格谓词(前置半步 0 载体)。

01_math_framework §2 三行的唯一实现:P39 臂一三元(板满 ∧ 阵营相关等待件不限星级 ∧
上场边际贡献>0——板面谓词保证 w>0,01_math_framework §3.3 #3:臂一只用 w>0 不需精确值)
=R2-2 移入的 arm1_existence 触发信号(M3 消费,板面可观测量,非 EV 项);
目标线 K(阵容 的 core/shared/flex 名单,cw_comps.COMP_LIBRARY 运行时可判定)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_comps import RUST_AFFIX_NAME, Comp
from sr_od.application.currency_war.kernel.cw_economy import loss_exact
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
    bench_slot_unit,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    deployed_rows_of,
    plane_of,
    round_num_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        Unit,
    )


def bench_effect_context(state: GameState, unit: Unit,
                         k_members: tuple[str, ...] = (),
                         ) -> BenchEffectContext:
    """三消费位(fuel_sell 豁免/凑利息档序资格/支付支撑变现)共享的语境
    装配函数(IMPL_ADV_R200 症3:语境从容器现读,禁各通道自拼)。

    可观测来源(逐项):
    - ``rust_affix_present``:``gs.enemy_affixes`` 含
      ``RUST_AFFIX_NAME``(与 kernel/cw_registry H2② 同一判据源);
    - ``equipped``:被评估单位自身 ``unit.equips`` 非空(单位级现读,
      恒可得);
    - ``herta_star_supply``:黑塔纪元 augment 局(``gs.
      active_strategies`` 含 ``proof.DIRECT_LINE_SIGNAL_STRATEGIES``
      成员,单一源)∨ 板面(行域)存在星级供强承载对象
      「大黑塔」(名册锚=cw_chars CHARACTERS['大黑塔'],银河学者星级
      供强线)∨ 线内(K 成员含承载对象——换线过渡期语境)。

    ``equipped`` 恒单位级现读。影响面=仅 bench_effect 载体件(现册仅
    「黑塔」),纯燃料件类级默认不受影响。
    """
    equipped = bool(getattr(unit, 'equips', None))
    affixes = list(state.enemy_affixes.value or ())
    rust = RUST_AFFIX_NAME in affixes
    herta = _herta_supply_present(state, k_members)
    return BenchEffectContext(rust_affix_present=rust, equipped=equipped,
                              herta_star_supply=herta)


#: 星级供强的承载对象(供给目标;名册锚=cw_chars CHARACTERS 注册条目
#: 「大黑塔」——小黑塔 bench_effect='星级供强' 的合成对象,final_daheita
#: 线知识)。名取自注册表名,非拟合值。
_HERTA_SUPPLY_TARGET: str = '大黑塔'


def _herta_supply_present(state: GameState,
                          k_members: tuple[str, ...]) -> bool:
    """星级供强语境在场判定(例外①的观测面:augment 局 ∨ 板面 ∨ 线内)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import proof
    strategies = list(state.active_strategies.value or ())
    front, back = deployed_rows_of(state)
    if any(s in proof.DIRECT_LINE_SIGNAL_STRATEGIES for s in strategies):
        return True
    if any((getattr(d, 'char_id', '') or '') == _HERTA_SUPPLY_TARGET
           for d in (*front, *back) if d is not None):
        return True
    return _HERTA_SUPPLY_TARGET in k_members


def arm1_existence(deployed_count: int, bench_names: list[str],
                   deployed_names: list[str],
                   deploy_cap: int | None = None) -> bool:
    """P39 臂一三元触发信号(R2-2 移入 statefn;M3 消费)。

    ①板满:``deployed_count == deploy_cap``——**cap 口径 = 当前可上阵数**
    (deploy_cap 真值链 / MandateFrame.deploy_cap:level+宝钻、封顶
    = 4+back_max 动态真值〔GameState.back_layout,值域 10-13〕),非固定槽表常数 ``DEPLOYED_CAPACITY``(=10,定长槽表
    的物理长度)。结论出处:2026-09-03 零刷新诊断批(ZERO_REFRESH_DIAG
    §4.2)实证 M3 升级门 13/13 波恒 False 的根因即此——旧条件拿 10 当
    板满阈值,而板面实际上板量受等级驱动 cap 约束(P1 期 3→5 量级),
    ``deployed_count`` 构造性不可达 10 ⇒ 触发面恒空;按 cap 口径重算
    同语料 10/13、5/12 波真(``.debug/temp/currency_war/core_swap/
    arm1_diag.py`)。边界:``deploy_cap=None``(观察帧缺 cap 读数)时
    兜底固定槽表常数 10——**该分支在生产消费位(run_mandate/商店线)
    经 ensure_contract 前提 ``_arm1_cap_level_driven``(deploy_cap=None
    ⇒ 违例弃权)已不可达**(契约层弃权优先于函数内兜底,IMPL_ADV_R200
    OBS-3 收尾);保留仅作函数局部完备性(直调/测试面),非生产语义。
    cap>10 时按 10 封顶(本函数局部表示域钳制 = 十槽槽表面,
    扩板另案;max_units 本体封顶已随 back_max 动态真值,本处不随)。
    ②③见下,不变。
    ②阵营相关等待件:bench 存在与当前板面(deployed∪bench 域成员性,
    P39 裁定宽域:不限星级)共享阵营/流派羁绊的单位;③上场边际贡献>0:
    由①②结构承载(w>0 板面谓词,01_math_framework §3.3 #3——臂一只需 w>0,无需 w
    精确值,【拟】#3 的 w 标定面不触发)。
    """
    cap = (DEPLOYED_CAPACITY if deploy_cap is None
           else min(deploy_cap, DEPLOYED_CAPACITY))
    if deployed_count < cap or not bench_names:
        return False
    board_tags: set[str] = set()
    for name in deployed_names:
        ch = CHARACTERS.get(name)
        if ch is not None:
            board_tags.update(ch.factions)
            board_tags.update(ch.flows)
    if not board_tags:
        return False
    for name in bench_names:
        ch = CHARACTERS.get(name)
        if ch is None:
            continue
        if board_tags & (set(ch.factions) | set(ch.flows)):
            return True
    return False


def line_members(comp: Comp | None) -> tuple[str, ...]:
    """目标线 K = 阵容 的 core/shared/flex 名单(COMP_LIBRARY 运行时可判定;
    线内/线外分类的锚,01_math_framework §2「目标线 K」行)。阵容 缺 → 空元组(零重叠全开,
    fail 方向=可逆面默认做,01_math_framework §5.3)。"""
    if comp is None:
        return ()
    # 线内成员 = core ∪ shared(cw_comps L435:transition_chars 不计——打工后
    # 卖的,不构成路线;core/shared 是终局成员)。「flex 名单」按 01_math_framework §2 表述
    # 对应本注册表的 shared+替班语义,不另建第三名单。
    members: list[str] = list(getattr(comp, 'core_chars', []) or [])
    members += list(getattr(comp, 'shared_chars', []) or [])
    return tuple(dict.fromkeys(members))


def zero_overlap(name: str, k: tuple[str, ...]) -> bool:
    """与目标线 K 零重叠(P41 分类表第一行资格条件「与终局阵容锁定零重叠」;
    M4 燃料件卖出的前提之一)。"""
    return name not in k


def item_slot_unsellable(unit: BenchSlot) -> bool:
    """占位件物理门(腾席卖出资格跨通道共享谓词;三通道资格循环首门)。

    真值 = 备战席槽位 kind ∈ ('tome','bookcard','supply_box')
    (观察写端按容器观察 kind 落位)——备战槽非角色占席物品(补给箱/星徽秘典/典籍书册等)
    无卖出交互且无金币现值——实机采证:同参数拖拽出售,角色 9 连全卖、
    箱零效果;宝箱面 = 4 选 1 装备面板,无金币现值、无出售项。任何星级
    不可变现 ⇒ 恒不入腾席卖出资格集。知识锚 =
    docs/game/currency_war/research/board_structure.md §备战栏
    「备战槽可被非角色物品占据」。

    消费位 = ``mandate.fuel_sell_candidates``(M4 燃料)/ ``criteria/sell.
    sell_for_interest``(凑息)/ ``criteria/sell.funding_support_sell``
    (支付变现)三通道资格循环首门,判读先于其余资格门;生产观察层
    SIFT 不产占位件条目,sim 假环境经观察面直喂 bench——本门 = 各卖出
    通道发出前唯一的占位件资格防线。新卖出通道必须经本谓词,禁第三处
    kind 判定内联复制(静态锁 = sr-od-test
    test_sell_candidates.py 占位件物理门段)。与部署侧 ``cw_deploy_logic``
    'item_slot' 恒 held 同谓词同向(该面防误上,本面防误卖)。
    缺省 False = 无标记形态不误伤(与部署侧同款防御读)。
    """
    return bench_slot_unit(unit) is None


def arm0_need(deployed: list[Unit], bench: list[BenchSlot],
              k_members: tuple[str, ...]) -> int:
    """arm0 v2 上阵人数需求 = 期望态现量,零派生规则(14号稿 §4.2 A4:
    v1 need_slots 从 TRANSITION_SYSTEMS 派生已作废——派生规则本身即一组
    新拍定选择)。

    = |deployed| + |{ b ∈ bench | b ∈ k_members(predicates core∪shared
    口径)∧ b.name ∉ deployed 名集 }|,bench 内同名去重(集合计)。
    ``bench`` = 占席条目域(容器 BenchSlot,身份经解包读口;
    benchchar-retirement P4 容器形)。

    排除口径 = **纯 name**(口径对齐收尾,P1消费分支批落地审:与真实部署去重语义对齐——
    check_seats 对象列同名禁上阵 + cw_deploy_logic 按 cid 去重的实际
    规则即「同名不可再上阵」;Y3 的 (名,星) 字面让位于部署真实语义,
    不为凑字面制造虚 need:①同名异星 bench 件按 name 排除后不再虚计
    (旧口径计 it = 为不可执行部署买等级);②bench 同名 ×2(臂① j=2
    形态)去重计 1(双计消除,need 恒高估修正)。**同名异星可否同场的
    机制事实未定案**(14号稿 §8⑫ 登记的待定项,核验结论 = 证据
    不足:机制原文只辖同名同星,档案 deployed 面系台账跟踪值不作机制
    证据)——纯 name 口径是**执行层语义对齐**(与部署去重一致,防为
    不可执行部署买等级),不是机制定案;若后续实机证得异星可双上阵,
    本谓词 need 将低估,回写口径时一并修。)
    成员集分叉声明(编排者存-2 裁决 = 有意设计):本谓词只量 k_members
    (可部署现量),臂①囤腿的 buy_members 超集成员不入 need——囤腿件
    走合成→上板,部署/升级授权面与囤腿面两口径禁混。
    """
    dep_names = {getattr(d, 'char_id', '') or '' for d in (deployed or [])}
    kset = set(k_members)
    extra = set()
    for b in bench or []:
        u = bench_slot_unit(b)
        cid = (u.char_id if u is not None else '') or ''
        if cid in kset and cid not in dep_names:
            extra.add(cid)
    return len(deployed or []) + len(extra)


def arm0_level_lag(level: int, readable: bool, deployed: list[Unit], bench: list[BenchSlot],
                   k_members: tuple[str, ...],
                   deploy_cap: int | None) -> tuple[bool, str]:
    """arm0 触发谓词 v2(14号稿 §4.2):等级落后于上阵人数需求。

    返回 (是否触发, 拒因分键——不触发时显式理由,零静默):
    - level 消费只认 authoritative 位(``level_readable``,C4 采纳:与
      15 号稿 §4.3 共用单一源可信位定义)——不可信帧 fail 向不触发
      (E3 型毒化帧 fail 向,分键 'level_unreadable');
    - level ≥ deploy_cap(等级容量已到,升级无对象)⇒ 'level_at_cap';
    - level < arm0_need ⟹ 触发(cap 容不下已持有的可上阵线内件)。
    常态保证:need > level ⇒ 至少一件与场上异 (名,星) 的 bench 线内件
    ⇒ 升级后通常存在合法部署候选(围栏 held 路径例外由探针
    arm0_post_level_no_deploy 承载,不作恒 0 断言——14号稿 §4.2 例外声明)。
    零新自由参数,全量期望态现读。
    """
    if not readable:
        return False, 'level_unreadable'
    if deploy_cap is not None and level >= deploy_cap:
        return False, 'level_at_cap'
    if level < arm0_need(deployed, bench, k_members):
        return True, ''
    return False, 'level_ge_need'


def p1_blood_floor(state: GameState) -> bool:
    """P1 濒死带域谓词(hp ≤ HP_BAND_NEAR_DEATH ∧ plane 1 ∧ 可信)。

    **现行消费面 = 纯观测**(entry.py 形态⑥金滞留观测的带判定/
    flow.py 锁生成可行性观察件共谓词)——决策面消费(血线硬地板
    解锁包三件:经验停付让位/凑息禁令/跌破利息档批解锁)已随血线地板
    删除链停用(迭代 2026-10-12-prep-shop-workflow-redesign 批 3.4;
    line_and_upgrade §2.3 血线地板解锁行;正典依据 user_playstyle
    [39]「HP 不作决策依据」——濒死响应 = 修经济/阵容本身)。本谓词
    保留为观测分键的带判定读口。

    判定:信任门 = ``hp_decision_trusted``(kernel 单一源;不可信帧/
    hp 无值帧 fail 向不判线);位面域 = 仅 plane 1(P2+ 半边 =
    :func:`p2_blood_floor`,两域互补且不交);阈值常量单一源 =
    ``lambda_death.HP_BAND_NEAR_DEATH``(血带结构锚,禁本处字面量
    第二份)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if state is None:
        return False   # 缺供给 fail-closed(D2 语义族;None 守卫显式化)
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) != 1:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


def p2_blood_floor(state: GameState) -> bool:
    """P2 濒死带域谓词(与 p1_blood_floor 同构的 P2+ 半边)。

    **现行消费面 = 纯观测**(flow.py 锁生成可行性观察件的 boss 濒死
    死区分键 / entry.py 形态⑥金滞留观测的带判定)——决策面消费
    (解锁包三件:M3 停付让位/凑息禁令/濒死解锁)已随血线地板删除
    链停用(迭代 2026-10-12-prep-shop-workflow-redesign 批 3.4;
    line_and_upgrade §2.3 血线地板解锁行),本谓词保留为观测分键的
    带判定读口,不再有解锁包合成口(原 ``p2_blood_floor_unlock``
    随决策消费面消亡)。

    判定(同构不同域,原设计稿 §2.1):
    - 信任门 = ``hp_decision_trusted``(kernel 单一源,同 p1);
    - 位面域 = plane ≥ 2(与 p1 的 plane==1 互补且不交);
    - 阈值常量单一源 = ``lambda_death.HP_BAND_NEAR_DEATH``(血带结构
      锚,禁本处字面量第二份)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if state is None:
        return False   # 缺供给 fail-closed(D2 语义族;None 守卫显式化)
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) < 2:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


@dataclass(frozen=True)
class BenchEffectContext:
    """「挂后台效果」资格谓词的语境输入(R32-中⑤ 前置半步 0)。

    - ``rust_affix_present``:库藏生锈词缀是否在场(词缀识别名 =
      ``cw_comps.RUST_AFFIX_NAME`` 单一源,01_math_framework §3.4 #4);
    - ``equipped``:被评估单位当前是否已穿装备(谓词读装备态的分支入参——
      穿装备改变词缀计数资格,与 01_math_framework §3.4 #4 无用件聚拢穿到工具人有交互);
    - ``herta_star_supply``:黑塔·银河学者星级供强语境(板面/线内存在
      大黑塔·银河学者成员,或黑塔纪元 augment 局)——例外①的显式枚举载体。
    """

    rust_affix_present: bool = False
    equipped: bool = False
    herta_star_supply: bool = False


def bench_effect_qualified(name: str, ctx: BenchEffectContext) -> bool:
    """「挂后台效果」资格谓词(前置半步 0;单位级载体 = cw_chars.Character
    ``bench_effect`` 字段,注册表单一源)。

    语义:该 bench 单位的后台效果当前是否生效(生效 ⇒ 三消费位按「不可当
    燃料/凑息件处置」处理)。判定 = 载体字段非空 ∧ 例外①②显式枚举:

    - **例外①(黑塔·银河学者星级供强语境,含黑塔纪元 augment 局)**:小黑塔
      (``bench_effect='星级供强'``)在星级供强语境下**保持资格**——其为
      1 费件,类级默认(低费=燃料)会静默放行例外件,故必须显式枚举
      (R32-中⑤ 载体缺口闭合的对象);语境不在场时星级供强无承载对象,
      不享保护(回归燃料类)。
    - **例外②(库藏生锈词缀局)**:生锈罚按未穿装备计数 ⇒ 合取条件
      「生锈不在场 ∨ 该件已穿装备」——生锈在场且未穿 ⇒ 资格不成立
      (排除出卖面桶不动子集);已穿装备 ⇒ 照常入桶不动子集。

    三消费位(判据层步 4 落地时消费,本批只建载体):fuel_sell 豁免 /
    凑利息档序资格 / 危局阀桶不动子集。
    """
    ch = CHARACTERS.get(name)
    if ch is None or not getattr(ch, 'bench_effect', ''):
        return False
    # 例外①:星级供强语境显式枚举(语境不在场=无承载对象,不享保护)
    if ch.bench_effect == '星级供强' and not ctx.herta_star_supply:
        return False
    # 例外②:生锈合取条件「生锈不在场 ∨ 已穿装备」(读装备态分支)
    return not (ctx.rust_affix_present and not ctx.equipped)


def t5_p1_false(gold: int, spend: int, rounds: int, net_income: int,
                cap_resolved: int) -> bool:
    """T5 未锁定止血买的结构判据承重谓词(/§4;p46 P1 谓词
    原式,判据 = loss_exact 现算,不按任何帧集清单)。

    ``L(g,c,R_全局,Ī,cap) == 0`` ⟺ P1 假 ⟺ 该帧出 p46 否决域(D =
    P1∧P2∧P3 恒假)——无需 E_rev、无需 V_deploy、无需 P2 分析,止血买
    的正当性由「占用集合基数严格扩 + 全额可退可逆 + 息账零损」三结构量
    的支配论证独立承载(仅作「有比没有强」接受
    形态的在册先例,适用范围限定同节)。判据全为注册表派生量,零 hp/胜率/
    掉血先验/板面评分消费——不在 00_framework §3 硬闸门适用范围,无开关。

    ``net_income`` 形参 = 逐节点净收入 Ī 的现算值(调用方经
    cw_economy.net_income 供给;非 i_bar 常量,命名随 cw_economy
    docstring 术语口径)。边界:cap=0(买断制)局 L≡0 ⇒ 全帧 P1 假
    ⇒ T5 全开,方向安全;P1 真帧(现算 L>0)结构层
    不发出,落行为层挂起(V_deploy 候用户逐项授权,宪法硬闸,禁自裁)。
    """
    return loss_exact(gold, spend, rounds, net_income, cap_resolved) == 0


# ===== 前窗/零成型谓词族(P90 面①;设计正本 =
# .debug/temp/currency_war/attacks/t175_exit_margin/设计方案.md §4.1,
# 命题 = math_proofs P90-P94 行)=====

#: 零战斗节点词集(节点表查表的战斗性判定的非战斗半边):生产表中文词
#: (P1_NODE_TEMPLATE 词表,tools/cw_node_validate)+ 英文词;英文半边的单一源 =
#: kernel cw_line_switch._ZERO_LOSS_NODE_KINDS 同集(此处展开因该常量
#: 为模块私有,战斗性判定需中英并集,勿再散落第三份)。
_FRONT_NONCOMBAT_NODES: frozenset[str] = frozenset(
    {'reward', 'supply', '奖励', '补给'})


def front_window_table_ready(gs: GameState) -> bool:
    """前窗查表前提探针(front_window_frame 的表在场半边;调用方用于
    「P1 帧但表缺」的零静默分键,避免调用侧复刻锚定逻辑)。"""
    return (gs.node_books.plane_node_table_plane == 1
            and bool(gs.node_books.plane_node_table))


def front_window_frame(state: GameState) -> bool:
    """P1 前窗备战帧谓词(v3 面①;位面参数化 = 节点表查表定义,禁位面
    字面量,01 §8-1)。

    语义 = plane==1 ∧ 当前轮 ≤ 首个战斗节点槽位(前窗 = 首战前窗,含
    首战备战帧——v3 面①(b)「r3 备战帧上」的 r3 即查表产物,P1 众数
    表下 = 第 3 轮)。节点表单一源 = ``gs.node_books.plane_node_table``
    (开局帧实读槽序;唯一写端 = cw_screen_prep.store_plane_table 每
    位面首帧写,读端同源先例 = cw_plane_table.nodes_of_plane);位面
    锚 = ``node_books.plane_node_table_plane``(防旧表滞留跨位面误
    读);战斗性判定 = 槽词不在 ``_FRONT_NONCOMBAT_NODES`` 零战斗词集
    (中英并集,出处见常量注)。

    fail-closed 边界:表缺/锚不符 ⇒ False(前窗行为不发生 = 现行为),
    调用方分键 ``p90_front_table_missing`` 显影;表全为零战斗词(脏表,
    每位面必有战斗的结构下退化域)⇒ 静默 False **不落分键**(落地审
    H4 修:显影主张收窄至表缺/锚不符两支)。
    """
    plane = plane_of(state)
    round_num = round_num_of(state)
    if plane != 1:
        return False
    node_books = state.node_books
    if node_books.plane_node_table_plane != 1:
        return False
    table = node_books.plane_node_table or []
    first_battle_idx: int | None = None
    for i, node in enumerate(table):
        if str(node).strip() not in _FRONT_NONCOMBAT_NODES:
            first_battle_idx = i
            break
    if first_battle_idx is None:
        return False   # 脏表退化域:静默 False(边界注见 docstring)
    return 1 <= int(round_num or 0) <= first_battle_idx + 1


def zero_form_frame(deployed: list) -> bool:
    """零成型帧谓词(P90 收窄适用范围 e=0;P94 谓词原文 = per-体系
    ``board_factions[s] < FACTIONS[s].tiers[0]``,希儿系复合判据单列)。

    四体系 = 三羁绊系(阈值对 = knowledge/cw_engine_facts.
    TRANSITION_TRAITS 的同注册表派生式——SYSTEM_CARDS × FACTIONS tiers[0];
    strategies→knowledge 非法桶边故本地同式派生,零漂移契约同款:
    同一注册表派生不存在字面双源,禁写字面阈值)+ 希儿系(复合判据
    单一实现 = kernel ``seele_system_formed``)。板面计数 = 已上场全
    羁绊计数(kernel ``deployed_bond_counts`` 单一源,bench 持有不计
    ——激活档是板面档)。``engines_count`` 为四体系合计标量,禁作
    per-体系谓词(设计轮一低 8③ 口径),本函数逐体系比较。
    """
    from sr_od.application.currency_war.data.cw_factions import FACTIONS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        deployed_bond_counts,
        seele_system_formed,
    )
    from sr_od.application.currency_war.kernel.cw_system_cards import (
        SYSTEM_CARDS,
    )
    system_tiers = tuple(
        (card.judge_factions[0], FACTIONS[card.judge_factions[0]].tiers[0])
        for card in SYSTEM_CARDS.values() if card.card_id != 'seele')
    deployed_names = {d.char_id or '' for d in (deployed or [])
                      if d is not None and (d.char_id or '')}
    board_factions = deployed_bond_counts(deployed_names)
    for bond, tier in system_tiers:
        if board_factions.get(bond, 0) >= tier:
            return False
    return not seele_system_formed(board_factions, deployed_names)


def advances_four_system(name: str) -> bool:
    """四体系推进件判定(零成型帧排序层前移对象;P20 方向级背书,
    非金量纲、不构成支出放行)。

    推进件 = 店内卡所属阵营/流派命中三羁绊体系键(SYSTEM_CARDS ×
    FACTIONS 注册表同注册表派生,zero_form_frame 同源注释)∨ 希儿系
    贡献件(kernel ``is_seele_system_member`` 单一源,入参 = 该卡自身
    bonds:希儿本人 + 量子/贝放大器)。零成型帧上全部体系 < tiers[0],
    任一体系成员买入都单调推进激活进度(P90 收益面 iii)。
    """
    if not name:
        return False
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        is_seele_system_member,
    )
    from sr_od.application.currency_war.kernel.cw_system_cards import (
        SYSTEM_CARDS,
    )
    ch = CHARACTERS.get(name)
    if ch is None:
        return False
    bonds = {card.judge_factions[0]
             for card in SYSTEM_CARDS.values() if card.card_id != 'seele'}
    if bonds & ({*ch.factions} | {*ch.flows}):
        return True
    return is_seele_system_member(name, {*ch.factions} | {*ch.flows})


__all__ = [
    'BenchEffectContext', 'RUST_AFFIX_NAME', 'advances_four_system',
    'arm1_existence', 'bench_effect_context', 'bench_effect_qualified',
    'front_window_frame', 'front_window_table_ready', 'line_members',
    't5_p1_false', 'zero_form_frame', 'zero_overlap',
]
