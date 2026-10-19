"""板面/目标线谓词(目标线 K/零重叠)+「挂后台效果」资格谓词。

01_math_framework §2 的在产实现:目标线 K(阵容 的 core/shared/flex
名单,cw_comps.COMP_LIBRARY 运行时可判定)与零重叠资格(M4 燃料件
卖出前提)。升级触发不落本模块——单判据三分派单一源 =
criteria/levelup.upgrade_trigger。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_comps import RUST_AFFIX_NAME, Comp
from sr_od.application.currency_war.kernel.cw_economy import loss_exact
from sr_od.application.currency_war.kernel.cw_exec_state import (
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
    kind 判定内联复制(静态测试 = sr-od-test
    test_sell_candidates.py 占位件物理门段)。与部署侧 ``cw_deploy_logic``
    'item_slot' 恒 held 同谓词同向(该面防误上,本面防误卖)。
    缺省 False = 无标记形态不误伤(与部署侧同款防御读)。
    """
    return bench_slot_unit(unit) is None


def p1_blood_floor(state: GameState) -> bool:
    """P1 濒死带域谓词(hp ≤ HP_BAND_NEAR_DEATH ∧ plane 1 ∧ 可信)。

    **现行消费面 = 纯观测**(entry.py 形态⑥金滞留观测的带判定/
    flow.py 锁生成可行性观察件共谓词)——决策面消费(血线硬地板
    解锁包三件:经验停付让位/凑息禁令/跌破利息档批解锁)已随血线地板
    删除链停用(line_and_upgrade §2.3 血线地板解锁行;正典依据 口述条目 39(登记簿已退役)「HP 不作决策依据」——濒死响应 = 修经济/阵容本身)。本谓词
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
    (解锁包三件:M3 停付让位/凑息禁令/濒死解锁)已删除(随血线地板删除链;
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
    """T5 未锁定止血买的结构判据支撑谓词(/§4;p46 P1 谓词
    原式,判据 = loss_exact 现算,不按任何帧集清单)。

    ``L(g,c,R_全局,Ī,cap) == 0`` ⟺ P1 假 ⟺ 该帧出 p46 否决域(D =
    P1∧P2∧P3 恒假)——无需 E_rev、无需 V_deploy、无需 P2 分析,止血买
    的正当性由「占用集合基数严格扩 + 全额可退可逆 + 息账零损」三结构量
    的支配论证独立承载(仅作「有比没有强」接受
    形态的已登记先例,适用范围限定同节)。判据全为注册表派生量,零 hp/胜率/
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
    调用方分键 ``p90_front_table_missing`` 暴露;表全为零战斗词(脏表,
    每位面必有战斗的结构下退化域)⇒ 静默 False **不落分键**(审查
    H4 修:暴露主张收窄至表缺/锚不符两支)。
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
    'bench_effect_context', 'bench_effect_qualified',
    'front_window_frame', 'front_window_table_ready', 'line_members',
    't5_p1_false', 'zero_form_frame', 'zero_overlap',
]
