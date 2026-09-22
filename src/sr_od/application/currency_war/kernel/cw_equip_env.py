"""货币战争 装备环境信号包(决策层读取口)。

(fill-to-3 量变体与变宝为废牺牲合成的序变体已随各自开关族
(equip_env_fill3_enabled / junk_first_sacrifice_enabled)删除——旧方案
清退批,清查报告 OLD_MIX_AUDIT §1.3:两开关默认关+开臂判据挂账未跑
即整体出局,``apply_equip_env_variants`` 退化为基分配直通(与全关
零漂移行为一致),kernel/cw_junk_first.py 模块同批删。机制真值
(软弱无力/额外打击/变宝为废词缀原文)保留在
data/affix_effects_data。)

保留件:
- ``build_equip_env_signals``:equip_all 决策调用处的环境信号单源
  构造点(生锈豁免等门变体仍消费 ``signals.enemy_affixes``,设计
  §2.2「变体不各自摸 state」纪律不变);
- ``apply_equip_env_variants``:EquipAll 唯一分配入口(签名保留,
  调用零改),现恒返回 ``cw_comps.equip_allocation`` 基分配。

18 号稿落码批新增——装备穿戴释放判据面(策略侧单一源):
- ``resolve_wear_release``:释放判据表五行评估(18 号稿 §2.1),产出
  布尔释放位——**hold 触发权归策略侧**:执行层只消费
  ``WearReleaseDecision.hold``,禁在执行层加第二套时机判断
  (与裁定 3 同理由);
- ``resolve_affix_priority_order``:词缀条件优先层求序(18 号稿 §3.2,
  限输出侧罚则族;载体 = data/affix_wear_semantics_data 结构化缓存)。

21 号稿落码批新增——opening 窗口收窄 + 工具件消费判据面:
- ``resolve_wear_release`` 扩展:O1 战斗前置释放门(§2.3 三门)+ 自由件
  谓词;row1(opening hold)从「无条件扣留」收窄为「三门全不中 ∧ 保留域
  命中才扣」,row2(committed)语义零改动(21 号稿 §2.3);
- ``classify_item_hold``:逐件扣留判定(B1 伴生:帧级布尔无法表达
  「自由件穿+key 扣留」混合态,消费位改件级输出);求值序 = O3 豁免 →
  O1/O2 释放门 → 保留域①-⑤ → 清单外一律释放(§2.3);
- ``evaluate_tool_actions``/``admitted_tool_actions``:工具件消费判据
  (全量收编 10 号稿 §2.1 三道门,本批只落冷启动分支 = 炉准入+扳手闸,
  其余 fail-closed 带拒因分键)+ G1 发射位准入(防第四个闩;
  ARCH_REFLECTION_3STALLS)。

工具执行批增量——执行通道建成开臂:
- ``TOOL_EXEC_CHANNEL_READY`` False→True(开臂判据 = UI 建档前置以既有
  owned 网格建档满足,常量节注释);
- 发射位 = mandate_v1 工具消费(逐备战帧评估打 ``[cw!][tools]`` 拒因
  分键,admitted 非空逐件发原子动作,执行位闩 = mark_tools_pass_
  executed);执行载体 = 工具原子动作 op(CwActionToolUseOp,组合壳
  RunTools 已退役)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 环境词缀识别名(画面 OCR 原名;affix_effects_data 注册表同名)
# (fill3 变体已删,保留名单供判读/建档引用。)
EQUIP_ENV_FILL3_AFFIXES: tuple[str, str] = ('软弱无力', '额外打击')


@dataclass(frozen=True)
class EquipEnvSignals:
    """装备环境信号包(equip_all 决策调用处构造一次,门变体共享;设计 §2.2)。

    ``enemy_affixes`` = state.enemy_affixes(简报∪随采;state 缺失=空集);
    ``plane``/``round_num`` = state 记账/窗口字段(预留)。
    """
    enemy_affixes: frozenset[str]
    plane: int | None
    round_num: int | None


def build_equip_env_signals(state) -> EquipEnvSignals:
    """state → 信号包(唯一读取点;state 缺失/字段未观察 = 安全默认,不抛错)。

    ``state`` = session 容器单例(game_state_of;装配源换源,旧
    ``session.last_state`` 帧链退役);容器/None 两态宽容读(鸭子 getattr
    + Field .value 取值),词缀未观察/节点未观察 = 空集 / None。
    """
    if state is None:
        return EquipEnvSignals(enemy_affixes=frozenset(),
                               plane=None, round_num=None)
    _aff = getattr(state, 'enemy_affixes', None)
    _aff_val = getattr(_aff, 'value', _aff)   # 容器 Field→.value;帧 list→自身
    affixes = list(_aff_val or [])
    node = getattr(state, 'node', None)
    node = getattr(node, 'value', None) if node is not None else None
    return EquipEnvSignals(
        enemy_affixes=frozenset(affixes),
        plane=int(node.plane) if node is not None else None,
        round_num=int(node.round_num) if node is not None else None,
    )


def apply_equip_env_variants(signals: EquipEnvSignals,
                             registry,
                             session,
                             comp: Comp | None,
                             deployed_rows: tuple[list, list],
                             owned: list[str],
                             occupied: dict[tuple[str, int], list[str]] | None,
                             hold_active: bool,
                             priority_order: list[str] | None = None,
                             ) -> tuple[list[tuple[str, str]], list[str]]:
    """装备分配入口(EquipAll 唯一调用点;基分配直通)。

    (原门→量→序变体管道的量(fill3)与序(变宝为废牺牲合成)两级已随
    开关族删除——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3;门级
    hold/生锈豁免在 equip_all 调用侧生效,不经本函数。``registry``/
    ``session``/``signals``/``hold_active`` 参数占位不再参与取值。)
    ``deployed_rows`` = 容器行域 ``(front_row, back_row)``,元素 = 容器
    ``Unit``(P4 容器形,直通 ``equip_allocation`` 同名参数)。
    ``priority_order``(18 号稿 §3.2/§3.3):词缀条件优先层
    重排输入序,直通 ``equip_allocation`` 同名可选参数(缺省 None 零漂移);
    决策/执行分层同 裁定 3——序由策略侧 resolve_affix_priority_order
    产出,本入口只转发,禁内嵌评分。
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    base = equip_allocation(comp, deployed_rows, owned, occupied,
                            priority_order=priority_order)
    return base, []


# ===== 18 号稿落码批:穿戴释放判据面(策略侧单一源)=====

@dataclass(frozen=True)
class WearReleaseDecision:
    """释放判据表评估产物(18 号稿 §2.1;执行层只消费 ``hold`` 布尔释放位)。

    合并规则(§2.1):判据表按行序评估,扣留行「任一命中即扣留」,
    豁免行「命中即解除其对应扣留域」(豁免取并集,无次序依赖):
    - row4 生锈豁免辖「一切扣留」(opening ∨ committed 都解);
    - row5 输出侧词缀豁免只辖已定型(committed)扣留域,不辖 opening hold
      (不对称理由 = 罚则结算时点:生锈按 owned 滞留计罚,软弱无力族只在
      战斗结算时点施罚,r≤2 奖励轮无罚结算点,§2.1)。
    最终 ``hold`` = (opening_hold ∧ ¬rust) ∨ (committed_hold ∧ ¬rust ∧ ¬penalty)。

    21 号稿收窄后(v2,B1/B3):row1(opening) 域的帧级布尔不再表达真实
    消费面——扣留收窄为「三门全不中 ∧ 保留域命中」的**逐件**判定
    (``classify_item_hold``),同帧可出现「自由件穿+key 扣留」混合态;
    ``hold`` 属性降格为 row2(committed) 遗留释放位,仅作观测/兼容,
    opening 域消费一律走件级判定。新增字段:
    - ``battle_precede_release`` = O1 战斗前置释放门(后随节点为战斗类,
      备战帧是穿戴唯一发生点,扣到战斗帧就晚了,§2.3 三门表);
    - ``node_type_unknown`` = row1 帧域内 node_type 缺失(保留域⑤
      「维持 hold」的判据输入;None 回查失败时 True)。
    """

    opening_hold: bool
    """row1:P1 r≤2 ∧ 当前节点非战斗类(R3 + 收窄;
    node_type 缺失维持 hold,观察缺失不改既有行为)。21 号稿收窄后本字段
    只表示「row1 帧域活跃」(逐件判定走 classify_item_hold),不再直接
    等于帧级扣留。"""
    committed_hold: bool
    """row2:已定型扣留(r70 过渡持有语义;激活 = committed 权威
    (cw_intention.committed_from)∧ 0<form<COMMIT_FRAC ∧ 非双轨;
    未定型(双轨)帧扣留不激活,18 号稿 §2.1 方向声明)。"""
    rust_release: bool
    """row4:库藏生锈在场豁免一切扣留(registry
    rust_wear_release_enabled 门)。"""
    output_penalty_release: bool
    """row5:输出侧罚则词缀在场豁免已定型扣留(18 号稿 §2.1 新裁行;
    载体 = data/affix_wear_semantics_data 结构化条目,行为无条件化——
    行为输入已就绪,按开关生命周期门不悬置默认关)。"""
    battle_precede_release: bool = False
    """O1(21 号稿 §2.3):后随节点为战斗类时,备战帧释放自由件+key 命中件
    (保留域④唯一件除外,§2.5 有意行为变化)。"""
    node_type_unknown: bool = False
    """保留域⑤判据输入(21 号稿 §2.3):row1 帧域内 node_type 缺失
    (既有 None 回查);仅 row1 帧域内有意义。"""

    @property
    def hold(self) -> bool:
        """帧级遗留释放位(True = 扣留;21 号稿收窄后只辖 row2 域)。

        row1 域消费禁读本属性(混合态不可表达),一律走
        ``classify_item_hold``;本属性保留 = row2 语义与既有观测面兼容。
        """
        if self.rust_release:
            return False
        if self.committed_hold:
            return not self.output_penalty_release
        return False


def battle_precede_release_active(round_num: int | None,
                                  next_node_type: str | None,
                                  battle_gate: bool,
                                  battle_nodes: frozenset[str]) -> bool:
    """O1 战斗前置释放门(21 号稿 §2.3 三门;只辖 row1 帧域 P1 ∧ r≤2)。

    后随节点 = 本备战帧之后第一个节点(执行层经 ``ledger_node_type``
    读 r+1 台账);node_type 判定词汇表与 row1 同源(registry
    ``opening_hold_battle_nodes`` + None 回查)。next_node 缺失 → 门不中
    (保守侧 = 维持保留域判定,不引入第二套词汇表)。
    """
    if round_num is None or round_num > 2:
        return False
    if not battle_gate or next_node_type is None:
        return False
    return next_node_type in battle_nodes


def is_unique_equipment(name: str) -> bool:
    """唯一件谓词(21 号稿 §2.3 保留域④;机制篇 §4)。

    注册表 effect 正文标记「唯一装备」(全角/半角括号并存,取子串免括号
    形态漂移)。全场唯一/一人一件三解读未实测 → 本批按最强解读保守扣留
    (§2.5);实测定谳为弱解读时随 §2.5 收窄撤销。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENTS,
    )
    e = EQUIPMENTS.get(name)
    return e is not None and '唯一装备' in e.effect


def is_free_item(name: str, comp) -> bool:
    """自由件谓词(21 号稿 §6 术语;静态注册表纯函数,sim 可达)。

    自由件 = 非 key_equips 候选 ∧ 非 RESERVED_COMPONENT ∧ category≠工具
    ∧ 非唯一件。comp=None(target 真空)→ key 集为空,其余三条件照判
    (与 18 号稿 key 白名单「target 真空→白名单空」同向)。工具件在调用方
    穿戴候选过滤已排除,此处重复排除 = 判据面防御(不进表语义,§3.2)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    from sr_od.application.currency_war.data.cw_synthesis import (
        RESERVED_COMPONENTS,
    )
    e = EQUIPMENTS.get(name)
    if e is None or e.category == EQUIP_TOOL_CATEGORY:
        return False
    keys = set(getattr(comp, 'key_equips', None) or []) if comp is not None \
        else set()
    if name in keys:
        return False
    if name in RESERVED_COMPONENTS:
        return False
    return not is_unique_equipment(name)


def classify_item_hold(decision: WearReleaseDecision, item_name: str,
                       comp, free_slot_available: bool) -> bool:
    """逐件扣留判定(21 号稿 §2.3 求值序;True = 扣留,消费位唯一判据)。

    求值序(逐件,高→低):
      1. O3 豁免:生锈在场 → 释放(无条件压倒保留域全体,含唯一件/node
         None 共现帧——v1 保留域优先对该帧的第二答已作废);
      2. O1/O2 释放门:row1 帧域内,O1(后随战斗)释放自由件+key 命中件、
         O2(自由件 ∧ 有空槽)释放自由件——唯一件两门均不适用(§2.5:唯一
         key 件扣留是有意行为变化,非 18 号稿语义偏离);
      3. 保留域①-⑤(仅 row1 帧域;row2 域语义 = 18 号稿原样):
         ② RESERVED_COMPONENT(key 未命中;P1 判据面第一道,消费端排除
         为第二道)→ 扣;④ 唯一件 → 扣;① 非 key ∧ committed 活跃 → 扣;
         ⑤ node_type 缺失 → 非 key 扣(key 命中件不受 hold);
      4. 清单外一律释放(row1 帧 key 命中件经此兜出,v3,L6 锁钉死);
      row2(非 row1)帧:key 命中随时穿、输出侧词缀豁免、其余扣(18 号稿
      row2 原文,唯一件例外不辖 row2——收窄只改 row1 处置)。
    工具件按 §3.2「不进表」防御性返回 True(调用方穿戴候选过滤已排除)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    from sr_od.application.currency_war.data.cw_synthesis import (
        RESERVED_COMPONENTS,
    )
    e = EQUIPMENTS.get(item_name)
    if e is None or e.category == EQUIP_TOOL_CATEGORY:
        return True
    if decision.rust_release:   # 求值序第 1 级:O3 压倒一切
        return False
    keys = set(getattr(comp, 'key_equips', None) or []) if comp is not None \
        else set()
    key_hit = item_name in keys
    unique = is_unique_equipment(item_name)
    if decision.opening_hold:
        # 第 2 级:O1/O2 释放门(逐件;唯一件除外)
        free = is_free_item(item_name, comp)
        if not unique and (decision.battle_precede_release
                           and (free or key_hit)):
            return False
        if free and free_slot_available:   # O2
            return False
        # 第 3 级:保留域①-⑤
        if item_name in RESERVED_COMPONENTS and not key_hit:
            return True   # ②
        if unique:
            return True   # ④(含唯一 key 件,§2.5)
        if (not key_hit) and decision.committed_hold:
            return True   # ①(两行共现帧承接,§2.3 叠加关系)
        # ⑤:node_type 缺失对剩余非 key 件维持 hold,其余清单外一律释放
        return (not key_hit) and decision.node_type_unknown
    if decision.committed_hold:   # row2 域:18 号稿 row2 原样
        return not (key_hit or decision.output_penalty_release)
    return False


def opening_hold_active(round_num: int | None, node_type: str | None,
                        battle_gate: bool, battle_nodes: frozenset[str]) -> bool:
    """row1:opening hold(r388/× 收窄;自备战执行器模块迁入,
    语义逐字不变;考古归 git)。

    - r388:开局轮(P1 r≤2)hold 无条件生效——key_equips 白名单来自
      target,target 真空(重启后首局)时白名单为空;旧判
      ``tgt_comp is not None`` 会让 hold 全不生效。
    - H3 收窄:hold 仅当 r≤2 且当前节点非战斗类(战斗类名单 =
      registry.opening_hold_battle_nodes);r≤2 战斗类节点释放 =
      18 号稿 §2.1 row3(释放帧走 M7 既有分配序全量穿)。
    - 降级路径:``round_num`` 缺失 → False;``node_type`` 缺失 → 维持
      hold(观察缺失不改变既有行为);开关关 → 逐位旧行为(零漂移锚)。
    """
    if round_num is None or round_num > 2:
        return False
    if not battle_gate:
        return True
    if node_type is None:
        return True
    return node_type not in battle_nodes


def committed_hold_active(comp, form: float, committed: bool) -> bool:
    """row2:已定型扣留(r70 过渡持有语义;自备战执行器模块迁入,
    语义逐字不变;考古归 git)。
    激活 = target 在(comp 非 None,form 的载体)∧ 0<form<COMMIT_FRAC
    ∧ committed(权威 = ``cw_intention.committed_from``:位面 2 起恒定型
    ∨ 意向已锁 ∨ P1 配对线非空;缺供给 = False 保守侧 = 双轨)。
    **方向声明(18 号稿 §2.1)**:未定型(双轨)帧扣留不激活——「攒给
    成型核心」只在目标核心已定时保留。参数名 ``committed`` 即「非双轨」
    (迁移前旧签名 ``dual`` 取反,行为逐位不变)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import COMMIT_FRAC
    return comp is not None and 0.0 < form < COMMIT_FRAC and committed


def rust_release_active(enemy_affixes: list[str] | None, gate: bool) -> bool:
    """row4:库藏生锈豁免(自备战执行器模块迁入,
    语义逐字不变;考古归 git)。滞留边际代价在计件封顶(registry cap=10)内单调上升,
    压倒「攒给成型核心」的机会成本。"""
    if not gate:
        return False
    from sr_od.application.currency_war.kernel.cw_comps import RUST_AFFIX_NAME
    return RUST_AFFIX_NAME in set(enemy_affixes or [])


def output_penalty_release_active(enemy_affixes: list[str] | None) -> bool:
    """row5:输出侧罚则词缀在场(18 号稿 §2.1;行为无条件化)。

    判据源 = data/affix_wear_semantics_data 结构化载体:在册词缀集判定
    规则 = 结构条目存在 ∧ ``wear_predicate`` 非空 ∧ ``penalty_side ==
    'output'``(缺结构化条目的散文词缀不进,防解析散文)。附带跑互检
    显警(§3.1 检测面,显警不拦截、只 log——防新词缀漏建模静默)。
    """
    from sr_od.application.currency_war.data.affix_wear_semantics_data import (
        WEAR_AFFIX_SEMANTICS,
        check_wear_semantics_coverage,
    )
    for w in check_wear_semantics_coverage():
        log.warning('[cw-equip-rel] 词缀穿戴语义互检显警: %s', w)
    for a in set(enemy_affixes or []):
        e = WEAR_AFFIX_SEMANTICS.get(a)
        if e is not None and e.wear_predicate is not None \
                and e.penalty_side == 'output':
            return True
    return False


def resolve_wear_release(round_num: int | None, node_type: str | None,
                         battle_gate: bool, battle_nodes: frozenset[str],
                         comp, form: float, committed: bool,
                         enemy_affixes: list[str] | None,
                         rust_gate: bool,
                         next_node_type: str | None = None,
                         ) -> WearReleaseDecision:
    """释放判据表评估(18 号稿 §2.1 + 21 号稿 §2.3 收窄;策略侧唯一入口)。

    行 3(战斗类节点释放)不单独出字段——它是 row1 的否定支
    (opening_hold=False 即释放),与哨兵 expected 的 round≥3 自带条件
    无冲突。21 号稿收窄:row1 帧域扣留降为逐件判定(``classify_item_hold``),
    本函数新增 ``next_node_type``(O1 门输入,执行层读 r+1 台账)与
    ``node_type_unknown``(保留域⑤);row2 语义零改动。
    多行命中合并规则见 ``WearReleaseDecision`` 注。
    """
    opening = opening_hold_active(round_num, node_type, battle_gate, battle_nodes)
    committed_h = committed_hold_active(comp, form, committed)
    rust = rust_release_active(enemy_affixes, rust_gate)
    penalty = output_penalty_release_active(enemy_affixes)
    return WearReleaseDecision(
        opening_hold=opening,
        committed_hold=committed_h,
        rust_release=rust,
        output_penalty_release=penalty,
        battle_precede_release=battle_precede_release_active(
            round_num, next_node_type, battle_gate, battle_nodes),
        node_type_unknown=(opening and node_type is None),
    )


def resolve_affix_priority_order(comp, deployed_rows: tuple[list, list],
                                 enemy_affixes: list[str] | None,
                                 occupied: dict[tuple[str, int], list[str]] | None = None,
                                 ) -> list[str] | None:
    """词缀条件优先层求序(18 号稿 §3.2 一般形,限输出侧罚则族)。

    返回 ``equip_allocation(priority_order=...)`` 的重排输入序;None =
    词缀层不启用(无输出侧谓词词缀在场 / 谓词全满足 / comp 缺失),回落
    基分配序(零重排)。纯函数;决策层产物,执行层禁内嵌评分(
    裁定 3 分层)。
    ``deployed_rows`` = 容器行域 ``(front_row, back_row)``,元素 = 容器
    ``Unit``(排归属由行承载,occupied 键 (row, 行内槽号))。

    判据(§3.2,零新自由参数——N 与罚值全部来自结构化载体):
    1. 在册词缀集 = 载体条目 ∧ wear_predicate 非空 ∧ penalty_side=='output';
    2. 谓词涉及角色集合 = **在场角色全集**(不限已锁线成员——罚则按角色
       个体结算,不按阵容资格);
    3. 排序 = [9] 既有优先序(plaza_carry → core_chars → 其余在场按
       deployed 序)内重排:谓词未满足者置前(词缀层只重排,不造第二套
       角色评分);
    4. 全员满足 → None(谓词满足后回落基分配序)。

    契约(与 ``equip_allocation`` priority_order 参数对齐):返回序的每个
    成员在分配侧都会被**吃满至容量**(凑满谓词语义),故本函数只放
    「谓词未满足成员 ∪ core」——core 恒在列(保持基分配「core 吃满」
    语义),非 core 未提及者仍走每人 1 件保底。
    **脱落预防(18 号稿 §1.2-3)**:重排只改「穿给谁」的次序,分配器为
    fill-only(occupied 仅作容量扣减,不触碰任何已穿件,key 与否同判)
    ——重排不可能取下已穿 key 件。
    """
    if comp is None:
        return None   # §3.3:未定型帧词缀谓词集合退化,零重排
    from sr_od.application.currency_war.data.affix_wear_semantics_data import (
        WEAR_AFFIX_SEMANTICS,
    )
    entries = []
    for a in set(enemy_affixes or []):
        e = WEAR_AFFIX_SEMANTICS.get(a)
        if e is not None and e.wear_predicate is not None \
                and e.penalty_side == 'output':
            entries.append(e)
    if not entries:
        return None
    from sr_od.application.currency_war.kernel.cw_comps import (
        _iter_deployed_rows,
    )
    _units = _iter_deployed_rows(deployed_rows)
    present = [getattr(d, 'char_id', '') for _rn, d in _units
               if getattr(d, 'char_id', '')]
    if not present:
        return None
    occ = occupied or {}
    worn: dict[str, int] = {}
    for _rn, d in _units:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        cnt = len(occ.get((_rn,
                           int(getattr(d, 'slot', 0) or 0)), []))
        worn[n] = worn.get(n, 0) + cnt
    # [9] 基序:plaza_carry → core_chars → 其余在场(deployed 序)
    base: list[str] = []
    if comp.plaza_carry and comp.plaza_carry in present:
        base.append(comp.plaza_carry)
    for c in comp.core_chars:
        if c in present and c not in base:
            base.append(c)
    for c in present:
        if c not in base:
            base.append(c)
    # 谓词未满足 = 任一在册输出侧条目的 N 未达(多词缀各谓词都须满足)
    unsatisfied = [c for c in base
                   if any(worn.get(c, 0) < e.wear_predicate[1] for e in entries)]
    if not unsatisfied:
        return None   # 谓词满足 → 回落基分配序(零重排)
    core_set = set(comp.core_chars)
    rest_cores = [c for c in base if c not in unsatisfied and c in core_set]
    return unsatisfied + rest_cores


# ===== 21 号稿 §3:工具件消费判据面(全量收编 10 号稿 §2.1,零改写)=====

#: G1 发射位准入(21 号稿 §2.4-2/§3.2;流程:197 常驻锁,ARCH_REFLECTION_
#: 3STALLS 防第四个闩):工具动作是**新的执行动作类**,不骑 M7
#: 穿戴通道。
#: 执行通道前置(开臂判据,两件均随工具执行批交付):
#: ①UI 建档(工具 icon 拖曳交互)——工具 icon 在 owned 多列网格内,与穿戴类
#:   同一建档(「区域-道具装备」D-40;col2 冶金炉 click 实锤),拖曳目标 =
#:   同网格另一 icon(炉→死库存件 icon / 特权卡→key 对应进阶成品 icon),
#:   无新画面 → 建档前置以既有 owned 网格建档满足;
#: ②工具拖曳 op 落码 = 工具原子动作 op(CwActionToolUseOp,判据→G1 准入
#:   →逐件原子发射;消耗确认对拍随组合壳退役,上报 = 机械执行直接上报写
#:   容器,容器写正本 = cw_action_report/tool_use)。
#: 开臂后拒因分键仍分键可见:判据拒原样透传,准入拒仅在通道回关时出现
#: (对照锁 sr-od-test test_cw_tools_exec_channel.py)。
TOOL_EXEC_CHANNEL_READY: bool = True

#: 工具拒因分键(21 号稿 §4/§5 遥测:该烧没烧/误烧率/拒因分键)。
TOOL_REJECT_G1_NOT_ADMITTED: str = 'g1_not_admitted(执行通道未建档)'
TOOL_REJECT_NO_TARGET: str = 'key_equips 空(recycle_qualified 空集,fail-closed)'
TOOL_REJECT_IN_DEMAND: str = '件在需求向量内(留合成)'
TOOL_REJECT_M1_GAP: str = 'm=1 缺件专留(P14 定理 2,不值得喂炉)'
TOOL_REJECT_DEST_UNREADY: str = '去向登记制未落地(10 号稿 §2.1.2)'
TOOL_REJECT_RC_MISSING: str = 'R(c) 缺档 fail-closed(21 号稿 §3.4)'
TOOL_REJECT_COLD_START_LATER: str = '冷启动分支外(10 号稿 §2.1.7 准入顺序)'


@dataclass(frozen=True)
class ToolAction:
    """单件工具的判据评估产物(门 A 到货拍评估一次,不进跨轮计划)。

    ``tool`` = 工具注册名;``action`` = 拟执行动作(如 'furnace_single');
    ``usable`` = 判据是否放行;``reason`` = usable=False 时的拒因分键
    (usable=True 时为 '')。本批不产生任何执行语义(判据面先行)。
    """
    tool: str
    action: str
    usable: bool
    reason: str = ''


def _privilege_base_name(priv_name: str) -> str | None:
    """特权件名 → 对应进阶成品名('X·特权' → 'X';非特权名 → None)。

    进阶→特权映射 = 注册表命名规则(P14 Q4:特权件无合成/炉/令牌通道,
    特权卡是唯一获取通道;对应进阶 = 同名去「·特权」后缀且在注册表)。
    """
    suffix = '·特权'
    if not priv_name.endswith(suffix):
        return None
    return priv_name[: -len(suffix)]


def evaluate_tool_actions(owned: list[str], comp) -> list[ToolAction]:
    """工具件消费判据(10 号稿 §2.1 三道门 + 21 号稿 §3.4 增量;纯函数)。

    门 A(评估时点):调用方在备战期 owned 快照到达时**评估一次**,不进
    跨轮计划(到货随机,规划无从附着)——本函数无内部状态,天然满足。
    门 B(价值面):工具动作零金币,金面默认不管(两处派生金流按息律
    通则搭车,不入本判据,21 号稿 §3.3);经济审只查「被操作装备在不在
    目标需求向量里」(recycle_qualified/hoard_gaps 同源)。
    门 C(不可逆分级):一次性工具证据要求更高;本批落地分支 =
    冷启动两件(炉准入 + 扳手闸),其余按 fail-closed 带拒因分键。

    逐件判据(21 号稿 §3.4 收编转写):
    - 冶金炉(单件用法):owned 存在 b ∈ recycle_qualified(K)(死库存,
      P14 定理 3)→ 放行;K 空 → 拒(no_target);全部死库存已在炉面无件
      可烧 → 不产条目;b 满足但 hoard_gaps 正份额档恰为 1(m=1 缺件专留)
      → 拒(m1_gap)。角色模式三件同刷(P14 定理 2 流水线)候工具拖曳
      op 批(执行面依赖扳手先行取下判定),本批不产条目。
    - 拆装扳手/精密扳手:去向登记制(每件取下物落位①重穿②回囤,找不
      到去向 = 不拆)未落地 → 一律拒(dest_unready,fail-closed——拆完
      散落 owned 无主是负操作)。
    - 员工/完美投影仪:q 再遇比较与费用域分支候冷启动后续批 → 拒
      (cold_start_later)。
    - 好运令牌:R(c) 推荐表未采集 → 拒(rc_missing,fail-closed;四选一
      选错整件报废,门 C)。
    - 特权赋予卡:key_equips 显式含特权件 ∧ 对应进阶成品在手(栏内拖法,
      精确控制配对)→ 放行;无特权目标 → 拒(in_demand 同族「留」语义,
      分键用 in_demand)。本判据面只产**库存腿**(target_kind='equip'):
      拖角色腿从未发射(用户裁定 2026-09-21 按不能拖角色处理候实机,
      上报侧收到 char 腿 = fail-closed 留证)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    from sr_od.application.currency_war.data.cw_synthesis import (
        hoard_gaps,
        recycle_qualified,
    )
    keys = list(getattr(comp, 'key_equips', None) or []) if comp is not None \
        else []
    owned_set = list(owned or [])
    tools = sorted({n for n in owned_set
                    if EQUIPMENTS.get(n) is not None
                    and EQUIPMENTS[n].category == EQUIP_TOOL_CATEGORY})
    actions: list[ToolAction] = []
    for t in tools:
        if t == '冶金炉':
            if not keys:
                actions.append(ToolAction(t, 'furnace_single', False,
                                          TOOL_REJECT_NO_TARGET))
                continue
            rq = recycle_qualified(keys)
            burnable = [b for b in owned_set if b in rq]
            if not burnable:
                continue   # 无死库存可烧,不产条目(非拒因,是无操作面)
            gaps = hoard_gaps(keys, owned_set)
            positive = [g for g, v in gaps.items() if v > 0]
            if len(positive) == 1:
                actions.append(ToolAction(t, 'furnace_single', False,
                                          TOOL_REJECT_M1_GAP))
            else:
                actions.append(ToolAction(t, 'furnace_single', True))
        elif t in ('拆装扳手', '精密拆装扳手'):
            actions.append(ToolAction(t, 'wrench_detach', False,
                                      TOOL_REJECT_DEST_UNREADY))
        elif t in ('员工投影仪', '完美投影仪'):
            actions.append(ToolAction(t, 'projector_copy', False,
                                      TOOL_REJECT_COLD_START_LATER))
        elif t == '好运令牌':
            actions.append(ToolAction(t, 'lucky_token_pick', False,
                                      TOOL_REJECT_RC_MISSING))
        elif t == '特权赋予卡':
            hit = any(_privilege_base_name(k) in owned_set
                      for k in keys if _privilege_base_name(k) is not None)
            if hit:
                actions.append(ToolAction(t, 'privilege_upgrade', True))
            else:
                actions.append(ToolAction(t, 'privilege_upgrade', False,
                                          TOOL_REJECT_IN_DEMAND))
        else:
            # 未逐件建模的工具新条目(注册表扩容)一律 fail-closed,
            # 拒因复用冷启动分键;扩容批回本函数补行。
            actions.append(ToolAction(t, 'unknown_tool_action', False,
                                      TOOL_REJECT_COLD_START_LATER))
    return actions


def admitted_tool_actions(actions: list[ToolAction]) -> list[ToolAction]:
    """G1 发射位准入过滤(21 号稿 §2.4-2/流程:197;防第四个闩)。

    判据放行(usable)∧ 执行通道就绪(TOOL_EXEC_CHANNEL_READY)才可发射;
    通道未就绪时全部拒(g1_not_admitted 分键,原判据拒因保留在先——
    拒因可观测性:判据拒与准入拒分开可见,禁静默吞)。
    """
    if TOOL_EXEC_CHANNEL_READY:
        return list(actions)
    out: list[ToolAction] = []
    for a in actions:
        out.append(a if not a.usable else ToolAction(
            a.tool, a.action, False, TOOL_REJECT_G1_NOT_ADMITTED))
    return out
