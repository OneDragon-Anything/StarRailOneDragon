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
from sr_od.application.currency_war.kernel.cw_board_state import (
    BoardState,
    deployed_slots_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_comps import RUST_AFFIX_NAME, Comp
from sr_od.application.currency_war.kernel.cw_economy import loss_exact
from sr_od.application.currency_war.kernel.cw_exec_state import DEPLOYED_CAPACITY

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar


def bench_effect_context(state: BoardState, unit: BenchChar,
                         k_members: tuple[str, ...] = (),
                         ) -> BenchEffectContext:
    """三消费位(fuel_sell 豁免/凑息档序资格/支付支撑变现)共享的语境
    装配函数(IMPL_ADV_R200 症3:语境从容器现读,禁各通道自拼)。

    可观测来源(逐项):
    - ``rust_affix_present``:``bs.enemy_affixes`` 含
      ``RUST_AFFIX_NAME``(与 kernel/cw_registry H2② 同一判据源);
    - ``equipped``:被评估单位自身 ``unit.equips`` 非空(单位级现读,
      恒可得);
    - ``herta_star_supply``:黑塔纪元 augment 局(``bs.
      active_strategies`` 含 ``proof.DIRECT_LINE_SIGNAL_STRATEGIES``
      成员,单一源)∨ 板面(``deployed_slots_of``)存在星级供强承载对象
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


def _herta_supply_present(state: BoardState,
                          k_members: tuple[str, ...]) -> bool:
    """星级供强语境在场判定(例外①的观测面:augment 局 ∨ 板面 ∨ 线内)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import proof
    strategies = list(state.active_strategies.value or ())
    deployed = deployed_slots_of(state)
    if any(s in proof.DIRECT_LINE_SIGNAL_STRATEGIES for s in strategies):
        return True
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
    = 4+back_max 动态真值〔BoardState.back_layout,值域 10-13〕),非固定槽表常数 ``DEPLOYED_CAPACITY``(=10,ADR-0392 定长槽表
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
    cap>10 时按 10 封顶(本函数局部表示域钳制 = ADR-0392 十槽槽表面,
    扩板另案;max_units 本体封顶已随 back_max 动态真值,本处不随)。
    ②③见下,不变。
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


def item_slot_unsellable(unit: BenchChar) -> bool:
    """占位件物理门(腾席卖出资格跨通道共享谓词;三通道资格循环首门)。

    真值 = ``BenchChar.is_item_slot``(部署装配点 assemble_bench_list
    显式标记,operations/cw_op/cw_op_deploy):备战槽非角色占席物品
    (补给箱/星徽秘典/典籍书册等)无卖出交互且无金币现值——实机采证:
    同参数拖拽出售,角色 9 连全卖、箱零效果;宝箱面 = 4 选 1 装备面板,
    无金币现值、无出售项。任何星级不可变现 ⇒ 恒不入腾席卖出资格集。
    知识锚 = docs/game/currency_war/research/board_structure.md §备战栏
    「备战槽可被非角色物品占据」。

    消费位 = ``mandate.fuel_sell_candidates``(M4 燃料)/ ``criteria/sell.
    sell_for_interest``(凑息)/ ``criteria/sell.funding_support_sell``
    (支付变现)三通道资格循环首门,判读先于其余资格门;生产观察层
    SIFT 不产占位件条目,sim 假环境经观察面直喂 bench——本门 = 各卖出
    通道发射前唯一的占位件资格防线。新卖出通道必须经本谓词,禁第三处
    ``is_item_slot`` 内联读复制(静态锁 = sr-od-test
    test_cw_sell_item_slot_predicate.py)。与部署侧 ``cw_deploy_logic``
    'item_slot' 恒 held 同谓词同向(该面防误上,本面防误卖)。
    ``getattr`` 缺省 False = 无标记形态不误伤(与部署侧同款防御读)。
    """
    return getattr(unit, 'is_item_slot', False)


def arm0_need(deployed: list[BenchChar], bench: list[BenchChar],
              k_members: tuple[str, ...]) -> int:
    """arm0 v2 上阵人数需求 = 期望态现量,零派生规则(14号稿 §4.2 A4:
    v1 need_slots 从 TRANSITION_SYSTEMS 派生已作废——派生规则本身即一组
    新拍定选择)。

    = |deployed| + |{ b ∈ bench | b ∈ k_members(predicates core∪shared
    口径)∧ b.name ∉ deployed 名集 }|,bench 内同名去重(集合计)。

    排除口径 = **纯 name**(口径对齐收口,P1消费臂批落地审:与真实部署去重语义对齐——
    check_seats 对象列同名禁上阵 + cw_deploy_logic 按 cid 去重的实际
    规则即「同名不可再上阵」;Y3 的 (名,星) 字面让位于部署真实语义,
    不为凑字面制造虚 need:①同名异星 bench 件按 name 排除后不再虚计
    (旧口径计 it = 为不可执行部署买等级);②bench 同名 ×2(臂① j=2
    形态)去重计 1(双计消除,need 恒高估修正)。**同名异星可否同场的
    机制事实未定谳**(14号稿 §8⑫ 挂账保留,2026-09-06 核验批 = 证据
    不足:机制原文只辖同名同星,档案 deployed 面系台账跟踪值不作机制
    证据)——纯 name 口径是**执行层语义对齐**(与部署去重一致,防为
    不可执行部署买等级),不是机制定谳;若后续实机证得异星可双上阵,
    本谓词 need 将低估,回写口径时一并修。)
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


def p1_blood_floor(state: BoardState) -> bool:
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
    **位面域 = 仅 plane 1**(P1消费臂批落地审应-A):解锁包授权族 = P1 血线硬地板
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
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) != 1:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


#: P2 低血带授权域统一裁定的授权闩(单点布尔;设计出处 =
#: .debug/temp/currency_war/_archive_20260908/p2_blood_band_unified_design/
#: DESIGN.md §1.2「判定面与消费面分层」+ 候裁条目定稿 = 同目录
#: supply_arbitration_design/DESIGN.md §15.2「P2 低血带授权域统一裁定」覆①②)。
#: 语义 =「P2 域 hp 族授权已被用户裁定 + 命题双门(濒死带格级重推命题)同时收口」;
#: 收口前恒 False ⇒ 面①(消费让位)面②(濒死定向豁免)全部 P2 行为支
#: fail-closed,只落观测分键(设计稿 §2.1/§3.2-3:无第三态、禁调参挂账)。
#: **为什么是代码常量不是配置开关**:本位不是 A/B 悬置开关(禁悬置默认关,
#: 策略开关生命周期门),而是「授权事件未发生」的 fail-closed 结构态——
#: 翻 True 的唯一合法动作 = 授权批用户裁定 + 命题门收口后的落码批
#: (改本常量 + ADR 文号回填),禁任何运行期改道。
P2_BLOOD_BAND_AUTHORITY_OPEN: bool = False


def p2_blood_floor(state: BoardState) -> bool:
    """P2 濒死带域谓词(p1_blood_floor 的 P2+ 半边同构件;设计出处 =
    p2_blood_band_unified_design/DESIGN.md §2.1,与 241 §15.2 覆①②共谓词,
    禁第二谓词)。

    只答「帧在域内」,**不含授权闩**——置位生效(解锁包三件消费)一律经
    :func:`p2_blood_floor_unlock` 的合成(授权闩 ∧ 本谓词;设计稿 §1.2:
    禁以任一门单独充当另一门的判据)。

    与 p1_blood_floor 的逐行同构关系(设计稿 §2.1「同构不同域,禁搭车」):
    - 信任门 = ``hp_decision_trusted``(kernel 单一源,同 p1);
    - **位面域 = plane ≥ 2**(与 p1 的 plane==1 互补且不交;p1 帧误开
      P2 解锁包同理 = 授权域外搭车,不可接受);
    - 阈值常量单一源 = ``lambda_death.HP_BAND_NEAR_DEATH``(血带结构锚,
      禁本处字面量第二份,predicates 既有纪律同款);
    - P1 域零改动:本谓词不触 p1_blood_floor 任何一行(设计稿 §1.3-1),
      neardeath_unlock 闩(entry.py)触发面照旧不动、禁另立第二闩(§1.3-3)。
    与在产 p2_crisis_band(≈41,更宽域)的关系:并存两域,危机带更宽、
    濒死带(≤15)更窄;本谓词不改 p2_crisis_band 任何语义(§1.3-4),
    其让位仅在 p2_blood_floor 帧 ∧ 裁定+命题双门收口后发生(p2_crisis_band
    未收口前照常全额管辖)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    if not hp_decision_trusted(state):
        return False
    if plane_of(state) < 2:
        return False
    hp = state.hp.value
    return hp is not None and hp <= HP_BAND_NEAR_DEATH


def p2_blood_floor_unlock(state: BoardState) -> bool:
    """P2 濒死带解锁包消费位(唯一合成口;设计出处 =
    p2_blood_band_unified_design/DESIGN.md §1.2/§2.1)。

    合成 = ``P2_BLOOD_BAND_AUTHORITY_OPEN ∧ p2_blood_floor(state)``——
    授权闩管「域已授权」、谓词内含 ``hp_decision_trusted`` 管「值可信」,
    两门正交(245 §2.3 正交合成声明,任一门禁单独充当另一门判据)。
    面①(消费让位:M3 停付让位/凑息禁令/转化优先)与面②(濒死定向
    豁免,行为交付挂空)的全部消费位一律经本口,禁直调 p2_blood_floor
    或读闩常量自拼(合成单点 = 防「闩开了谓词漏判」/「谓词真了闩没开」
    两种半门误放)。闩 False 期间恒 False ⇒ 全消费位 fail-closed,
    行为零变更(收口前全局 fail-closed,设计稿 §3.2-3)。
    """
    if not P2_BLOOD_BAND_AUTHORITY_OPEN:
        return False
    return p2_blood_floor(state)


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


def t5_p1_false(gold: int, spend: int, rounds: int, net_income: int,
                cap_resolved: int) -> bool:
    """T5 未锁线止血买的结构判据承重谓词(ADR-0556 §2/§4;p46 P1 谓词
    原式,判据 = loss_exact 现算,不按任何帧集清单)。

    ``L(g,c,R_全局,Ī,cap) == 0`` ⟺ P1 假 ⟺ 该帧出 p46 否决域(D =
    P1∧P2∧P3 恒假)——无需 E_rev、无需 V_deploy、无需 P2 分析,止血买
    的正当性由「占用集合基数严格扩 + 全额可退可逆 + 息账零损」三结构量
    的支配论证独立承载(ADR-0556 §4;ADR-0288 仅作「有比没有强」接受
    形态的在册先例,辖域限定同节)。判据全为注册表派生量,零 hp/胜率/
    掉血先验/板面评分消费——不在 00_framework §3 硬闸门辖域,无开关。

    ``net_income`` 形参 = 逐节点净收入 Ī 的现算值(调用方经
    cw_economy.net_income 供给;非 i_bar 常量,命名随 cw_economy
    docstring 术语口径)。边界:cap=0(买断制)局 L≡0 ⇒ 全帧 P1 假
    ⇒ T5 全开,方向安全(ADR-0556 §2);P1 真帧(现算 L>0)结构层
    不发射,落行为层挂起(V_deploy 候用户逐项授权,宪法硬闸,禁自裁;
    ADR-0556 §7 挂账)。
    """
    return loss_exact(gold, spend, rounds, net_income, cap_resolved) == 0


# ===== T-263 前窗/零成型谓词族(P90 面①;设计正本 =
# .debug/temp/currency_war/attacks/t175_exit_margin/设计方案.md §4.1,
# 命题 = math_proofs P90-P94 行)=====

#: 零战斗节点词集(节点表查表的战斗性判定的非战斗半边):生产表中文词
#: (P1_NODE_TEMPLATE 词表,tools/cw_node_validate)+ sim 表英文词
#: (engine_p1.P2_NODE_SEQUENCE 同词表);英文半边的单一源 =
#: kernel cw_line_switch._ZERO_LOSS_NODE_KINDS 同集(此处展开因该常量
#: 为模块私有,战斗性判定需中英并集,勿再散落第三份)。
_FRONT_NONCOMBAT_NODES: frozenset[str] = frozenset(
    {'reward', 'supply', '奖励', '补给'})


def front_window_table_ready(session) -> bool:
    """前窗查表前提探针(front_window_frame 的表在场半边;调用方用于
    「P1 帧但表缺」的零静默分键,避免调用侧复刻锚定逻辑)。"""
    return (getattr(session, 'plane_node_table_plane', None) == 1
            and bool(getattr(session, 'plane_node_table', None)))


def front_window_frame(state: BoardState, session) -> bool:
    """P1 前窗备战帧谓词(v3 面①;位面参数化 = 节点表查表定义,禁位面
    字面量,01 §8-1)。

    语义 = plane==1 ∧ 当前轮 ≤ 首个战斗节点槽位(前窗 = 首战前窗,含
    首战备战帧——v3 面①(b)「r3 备战帧上」的 r3 即查表产物,P1 众数
    表下 = 第 3 轮)。节点表单一源 = ``session.plane_node_table``
    (开局帧实读槽序,cw_screen_prep.store_plane_table 每位面首帧写 /
    sim engine P1 段同构写);位面锚 = ``plane_node_table_plane``(防
    旧表滞留跨位面误读);战斗性判定 = 槽词不在 ``_FRONT_NONCOMBAT_
    NODES`` 零战斗词集(中英并集,出处见常量注)。

    fail-closed 边界:表缺/锚不符 ⇒ False(前窗行为不发生 = 现行为),
    调用方分键 ``p90_front_table_missing`` 显影;表全为零战斗词(脏表,
    每位面必有战斗的结构下退化域)⇒ 静默 False **不落分键**(落地审
    H4 修:显影主张收窄至表缺/锚不符两支)。
    """
    plane = plane_of(state)
    round_num = round_num_of(state)
    if plane != 1:
        return False
    if getattr(session, 'plane_node_table_plane', None) != 1:
        return False
    table = getattr(session, 'plane_node_table', None) or []
    first_battle_idx: int | None = None
    for i, node in enumerate(table):
        if str(node).strip() not in _FRONT_NONCOMBAT_NODES:
            first_battle_idx = i
            break
    if first_battle_idx is None:
        return False   # 脏表退化域:静默 False(边界注见 docstring)
    return 1 <= int(round_num or 0) <= first_battle_idx + 1


def zero_form_frame(deployed: list) -> bool:
    """零成型帧谓词(P90 收窄辖域 e=0;P94 谓词原文 = per-体系
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
