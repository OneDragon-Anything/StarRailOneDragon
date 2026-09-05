"""板满/等待件谓词(arm1_existence 触发信号)+ 目标线 K/零重叠 +
「挂后台效果」资格谓词(前置半步 0 载体)。

NMF §2 三行的唯一实现:P39 臂一三元(板满 ∧ 阵营相关等待件不限星级 ∧
上场边际贡献>0——板面谓词保证 w>0,NMF §3.3 #3:臂一只用 w>0 不需精确值)
=R2-2 移入的 arm1_existence 触发信号(M3 消费,板面可观测量,非 EV 项);
目标线 K(comp 的 core/shared/flex 名单,cw_comps.COMP_LIBRARY 运行时可判定)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_comps import RUST_AFFIX_NAME, Comp
from sr_od.application.currency_war.kernel.cw_state import DEPLOYED_CAPACITY

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_state import (
        BenchChar,
        GameState,
    )


def bench_effect_context(state: GameState | None, unit: BenchChar,
                         k_members: tuple[str, ...] = (),
                         ) -> BenchEffectContext:
    """三消费位(fuel_sell 豁免/凑息档序资格/支付支撑变现)共享的语境
    装配函数(IMPL_ADV_R200 症3:语境从 state 现读,禁各通道自拼)。

    可观测来源(逐项):
    - ``rust_affix_present``:``state.enemy_affixes`` 含
      ``RUST_AFFIX_NAME``(与 kernel/cw_registry H2② 同一判据源);
    - ``equipped``:被评估单位自身 ``unit.equips`` 非空(单位级现读,
      恒可得);
    - ``herta_star_supply``:黑塔纪元 augment 局(``state.
      active_strategies`` 含 ``proof.DIRECT_LINE_SIGNAL_STRATEGIES``
      成员,单一源)∨ 板面(``state.deployed``)存在星级供强承载对象
      「大黑塔」(名册锚=cw_chars CHARACTERS['大黑塔'],银河学者星级
      供强线)∨ 线内(K 成员含承载对象——换线过渡期语境)。

    缺省保守端申报:``state=None``(旧调用面/手工帧)时两维语境不可
    观测 ⇒ 按保护端处置——``herta_star_supply=True``(例外①在场)∧
    ``rust_affix_present=False``(例外②的排除支「生锈在场∧未穿」不成立
    ⇒ 资格保持):两维合成结果=载体件受保护(不可逆卖出面缺输入默认
    不做,§2.2.1 同款 fail 方向)。生锈局滞留代价由 wear_release 通道
    另行承载,不在此翻转卖面缺省。``equipped`` 恒单位级现读。影响面=
    仅 bench_effect 载体件(现册仅「黑塔」),纯燃料件类级默认不受影响。
    """
    equipped = bool(getattr(unit, 'equips', None))
    if state is None:
        return BenchEffectContext(rust_affix_present=False, equipped=equipped,
                                  herta_star_supply=True)
    rust = RUST_AFFIX_NAME in (getattr(state, 'enemy_affixes', None) or ())
    herta = _herta_supply_present(state, k_members)
    return BenchEffectContext(rust_affix_present=rust, equipped=equipped,
                              herta_star_supply=herta)


#: 星级供强的承载对象(供给目标;名册锚=cw_chars CHARACTERS 注册条目
#: 「大黑塔」——小黑塔 bench_effect='星级供强' 的合成对象,final_daheita
#: 线知识)。名取自注册表名,非拟合值。
_HERTA_SUPPLY_TARGET: str = '大黑塔'


def _herta_supply_present(state: GameState | None,
                          k_members: tuple[str, ...]) -> bool:
    """星级供强语境在场判定(例外①的观测面:augment 局 ∨ 板面 ∨ 线内)。"""
    if state is None:
        return True    # 缺读保守端(见 bench_effect_context 申报)
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import proof
    strategies = getattr(state, 'active_strategies', None) or ()
    if any(s in proof.DIRECT_LINE_SIGNAL_STRATEGIES for s in strategies):
        return True
    deployed = getattr(state, 'deployed', None) or []
    if any((getattr(d, 'char_id', '') or '') == _HERTA_SUPPLY_TARGET
           for d in deployed if d is not None):
        return True
    return _HERTA_SUPPLY_TARGET in k_members


def arm1_existence(deployed_count: int, bench_names: list[str],
                   deployed_names: list[str],
                   deploy_cap: int | None = None) -> bool:
    """P39 臂一三元触发信号(R2-2 移入 statefn;M3 消费)。

    ①板满:``deployed_count == deploy_cap``——**cap 口径 = 当前可上阵数**
    (GameState.max_units() / MandateFrame.deploy_cap:level+宝钻、封顶
    10),非固定槽表常数 ``DEPLOYED_CAPACITY``(=10,ADR-0392 定长槽表
    的物理长度)。结论出处:2026-09-03 零刷新诊断批(ZERO_REFRESH_DIAG
    §4.2)实证 M3 升级门 13/13 波恒 False 的根因即此——旧条件拿 10 当
    板满阈值,而板面实际上板量受等级驱动 cap 约束(P1 期 3→5 量级),
    ``deployed_count`` 构造性不可达 10 ⇒ 触发面恒空;按 cap 口径重算
    同语料 10/13、5/12 波真(``.debug/temp/currency_war/core_swap/
    arm1_diag.py`)。边界:``deploy_cap=None``(观察帧缺 cap 读数)时
    兜底固定槽表常数 10——**该分支在生产消费位(run_mandate/商店线)
    经 ensure_contract 前提 ``_arm1_cap_level_driven``(deploy_cap=None
    ⇒ 违例弃权)已不可达**(契约层弃权优先于函数内兜底,IMPL_ADV_R200
    OBS-3 收口);保留仅作函数局部完备性(直调/测试面),非生产语义。
    cap>10 时按 10 封顶(max_units 同款)。②③见下,不变。
    ②阵营相关等待件:bench 存在与当前板面(deployed∪bench 域成员性,
    P39 裁定宽域:不限星级)共享阵营/流派羁绊的单位;③上场边际贡献>0:
    由①②结构承载(w>0 板面谓词,NMF §3.3 #3——臂一只需 w>0,无需 w
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
    """目标线 K = comp 的 core/shared/flex 名单(COMP_LIBRARY 运行时可判定;
    线内/线外分类的锚,NMF §2「目标线 K」行)。comp 缺 → 空元组(零重叠全开,
    fail 方向=可逆面默认做,NMF §5.3)。"""
    if comp is None:
        return ()
    # 线内成员 = core ∪ shared(cw_comps L435:transition_chars 不计——打工后
    # 卖的,不构成路线;core/shared 是终局成员)。「flex 名单」按 NMF §2 表述
    # 对应本注册表的 shared+替班语义,不另建第三名单。
    members: list[str] = list(getattr(comp, 'core_chars', []) or [])
    members += list(getattr(comp, 'shared_chars', []) or [])
    return tuple(dict.fromkeys(members))


def zero_overlap(name: str, k: tuple[str, ...]) -> bool:
    """与目标线 K 零重叠(P41 分类表第一行资格条件「与锁线零重叠」;
    M4 燃料件卖出的前提之一)。"""
    return name not in k


def arm0_need(deployed: list[BenchChar], bench: list[BenchChar],
              k_members: tuple[str, ...]) -> int:
    """arm0 v2 上阵人数需求 = 期望态现量,零派生规则(14号稿 §4.2 A4:
    v1 need_slots 从 TRANSITION_SYSTEMS 派生已作废——派生规则本身即一组
    新拍定选择)。

    = |deployed| + |{ b ∈ bench | b ∈ k_members(predicates core∪shared
    口径)∧ b.name ∉ deployed 名集 }|,bench 内同名去重(集合计)。

    排除口径 = **纯 name**(口径对齐收口,落地审清单 20260905_cp1_landing_review/问题清单.md:与真实部署去重语义对齐——
    check_seats 对象列同名禁上阵 + cw_deploy_logic 按 cid 去重的实际
    规则即「同名不可再上阵」;Y3 的 (名,星) 字面让位于部署真实语义,
    不为凑字面制造虚 need:①同名异星 bench 件按 name 排除后不再虚计
    (旧口径计 it = 为不可执行部署买等级);②bench 同名 ×2(臂① j=2
    形态)去重计 1(双计消除,need 恒高估修正)。同名异星可否同场的
    机制事实 = cw_deploy_logic 实答「不可」,§8⑫ 挂账相应收窄。)
    成员集分叉声明(编排者存-2 裁决 = 有意设计):本谓词只量 k_members
    (可部署现量),臂①囤腿的 buy_members 超集成员不入 need——囤腿件
    走合成→上板,部署/升级授权面与囤腿面两口径禁混。
    """
    dep_names = {d.char_id or '' for d in (deployed or [])}
    kset = set(k_members)
    extra = {b.char_id or '' for b in bench or []
             if (b.char_id or '') in kset
             and (b.char_id or '') not in dep_names}
    return len(deployed or []) + len(extra)


def arm0_level_lag(level: int, readable: bool, deployed: list[BenchChar], bench: list[BenchChar],
                   k_members: tuple[str, ...],
                   deploy_cap: int | None) -> tuple[bool, str]:
    """arm0 触发谓词 v2(14号稿 §4.2):等级落后于上阵人数需求。

    返回 (是否触发, 拒因分键——不触发时显式理由,W6 零静默):
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


def p1_blood_floor(state) -> bool:
    """血线硬地板(λ_death 死亡线;≤15 族,在册授权)。

    **定位 = 不影响发展主线的最后保命,非主要求生手段**:触发域 hp≤15
    深血线,辖域 = 反深血线死握(持金至死零支出,实机三局独立复现,
    14号稿 §5.4)——解锁包三件 = ①M3 破息批解锁至饱和线下(经验支出
    停付线让位)+ ②凑息禁令(凑息卖回拉不发射)+ ③转化优先(M2 义务
    买/囤腿本就不走息律门,零行为差申报);发展面不在本线辖域,零变化。

    授权链(00§3):阈值族 = 血线硬地板 ≤15 用户在册确认(形态/阈值域/
    解锁包三件);阈值常量单一源 = ``lambda_death.HP_BAND_NEAR_DEATH``
    (血带结构锚,禁本处字面量第二份)。信任门 = ``hp_decision_trusted``
    (kernel 单一源;P1 hp 读链毒化史,不可信帧/hp 无值帧 fail 向不判线
    ——fail 向 = 本线不触发,各消费面维持既有语义)。
    **位面域 = 仅 plane 1**(落地审清单应-A,20260905_cp1_landing_review/问题清单.md):解锁包授权族 = P1 血线硬地板
    ——P2 深血线有自己的在产口径(p2_crisis_band ≈41,更宽域更早介入),
    P2 帧 hp≤15 若误开 P1 专属解锁包 = 授权域外搭车,不可接受;域外帧
    fail 向不判线,消费面维持既有语义。
    同族在册废弃件对照:p1_crisis_band(≈22 带判据)经用户裁决不授权、
    废弃((b)2/(b)3 消费位永久挂空,14号稿 §11.8)——不在授权族,禁
    借本件复活。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if state is None or not hp_decision_trusted(state):
        return False
    if getattr(state, 'plane', None) != 1:
        return False
    hp = getattr(state, 'hp', None)
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


@dataclass(frozen=True)
class BenchEffectContext:
    """「挂后台效果」资格谓词的语境输入(R32-中⑤ 前置半步 0)。

    - ``rust_affix_present``:库藏生锈词缀是否在场(词缀识别名 =
      ``cw_comps.RUST_AFFIX_NAME`` 单一源,NMF §3.4 #4);
    - ``equipped``:被评估单位当前是否已穿装备(谓词读装备态的分支入参——
      穿装备改变词缀计数资格,与 NMF §3.4 #4 无用件聚拢穿到工具人有交互);
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
    凑息档序资格 / 危局阀桶不动子集。
    """
    ch = CHARACTERS.get(name)
    if ch is None or not getattr(ch, 'bench_effect', ''):
        return False
    # 例外①:星级供强语境显式枚举(语境不在场=无承载对象,不享保护)
    if ch.bench_effect == '星级供强' and not ctx.herta_star_supply:
        return False
    # 例外②:生锈合取条件「生锈不在场 ∨ 已穿装备」(读装备态分支)
    return not (ctx.rust_affix_present and not ctx.equipped)


__all__ = [
    'BenchEffectContext', 'RUST_AFFIX_NAME', 'arm1_existence',
    'bench_effect_context', 'bench_effect_qualified', 'line_members',
    'zero_overlap',
]
