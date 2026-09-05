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

18 号稿落码批(ADR-0526)新增——装备穿戴释放判据面(策略侧单一源):
- ``resolve_wear_release``:释放判据表五行评估(18 号稿 §2.1),产出
  布尔释放位——**hold 触发权归策略侧**:执行层(CwOpEquipAll)只消费
  ``WearReleaseDecision.hold``,禁在执行层加第二套时机判断
  (与 ADR-0461 裁定 3 同理由);
- ``classify_zero_wear_stop_reason``:零上身哨兵 stop_reason 辖域二分
  (18 号稿 §1.2:策略 by-design / 策略缺口 / 执行链 + 枚举外兜底行);
- ``resolve_affix_priority_order``:词缀条件优先层求序(18 号稿 §3.2,
  限输出侧罚则族;载体 = data/affix_wear_semantics_data 结构化缓存)。
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
    """state → 信号包(唯一读取点;state 缺失/字段缺失 = 安全默认,不抛错)。

    ``state`` = ``session.last_state``(可为 None,离线/旧栈);字段经 getattr
    宽读,缺 = None / 空集。
    """
    affixes = list(getattr(state, 'enemy_affixes', None) or []) if state is not None else []
    plane = getattr(state, 'plane', None) if state is not None else None
    round_num = getattr(state, 'round_num', None) if state is not None else None
    return EquipEnvSignals(
        enemy_affixes=frozenset(affixes),
        plane=int(plane) if plane is not None else None,
        round_num=int(round_num) if round_num is not None else None,
    )


def apply_equip_env_variants(signals: EquipEnvSignals,
                             registry,
                             session,
                             comp: Comp | None,
                             deployed: list,
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
    ``priority_order``(18 号稿 §3.2/§3.3,ADR-0526):词缀条件优先层
    重排输入序,直通 ``equip_allocation`` 同名可选参数(缺省 None 零漂移);
    决策/执行分层同 ADR-0461 裁定 3——序由策略侧 resolve_affix_priority_order
    产出,本入口只转发,禁内嵌评分。
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    base = equip_allocation(comp, deployed, owned, occupied,
                            priority_order=priority_order)
    return base, []


# ===== 18 号稿落码批(ADR-0526):穿戴释放判据面(策略侧单一源)=====

#: 零上身哨兵 stop_reason 辖域二分(18 号稿 §1.2)四归域常量。
ZERO_WEAR_STRATEGY_BY_DESIGN: str = 'strategy_by_design'
ZERO_WEAR_STRATEGY_GAP: str = 'strategy_gap'
ZERO_WEAR_EXECUTION: str = 'execution'
ZERO_WEAR_EXECUTION_PENDING: str = 'execution_pending'

#: 执行链 stop_reason 全枚举(精确匹配行;18 号稿 §1.2 值域)。
#: 字符串值 = cw_op_equip_all 写入端字面量(单一写入点)。
_ZERO_WEAR_EXECUTION_REASONS: frozenset[str] = frozenset({
    'drag 落空(失败继续,dd-015)',
    'pool_empty(无穿戴候选)',
    '分配对全部拉黑(drag 连败,dd-015)',
    '画面非干净备战',
})


def classify_zero_wear_stop_reason(stop_reason: str) -> str:
    """零上身哨兵 stop_reason → 辖域归域(纯函数;18 号稿 §1.2 二分表)。

    归域:
    - ``strategy_by_design``:过渡期/opening hold 命中(策略 by-design,
      由 18 号稿 §2.1 释放判据表解释,非执行缺陷);
    - ``strategy_gap``:分配方案空(策略语义缺口,归词缀条件优先层
      (§3)与工具消费空缺评估);
    - ``execution``:执行链(drag 落空 / pool_empty / 分配对全部拉黑 /
      槽位坐标缺失 / 画面非干净备战);
    - ``execution_pending``:**兜底行**——枚举外的一切 stop_reason(含
      空串 stall)暂归执行链待分诊;新枚举值出现时回 18 号稿 §1.2 补行。
    """
    s = stop_reason or ''
    if s.startswith('过渡期hold'):
        return ZERO_WEAR_STRATEGY_BY_DESIGN
    if s.startswith('分配方案空'):
        return ZERO_WEAR_STRATEGY_GAP
    if s in _ZERO_WEAR_EXECUTION_REASONS:
        return ZERO_WEAR_EXECUTION
    if s.endswith('槽位坐标缺失'):
        return ZERO_WEAR_EXECUTION
    return ZERO_WEAR_EXECUTION_PENDING


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
    """

    opening_hold: bool
    """row1:P1 r≤2 ∧ 当前节点非战斗类(ADR-0257 R3 + ADR-0461 H3 收窄;
    node_type 缺失维持 hold,观察缺失不改既有行为)。"""
    committed_hold: bool
    """row2:已定型扣留(r70 过渡持有语义;激活 = committed 权威
    (cw_intention.committed_from)∧ 0<form<COMMIT_FRAC ∧ 非双轨;
    未定型(双轨)帧扣留不激活,18 号稿 §2.1 方向声明)。"""
    rust_release: bool
    """row4:库藏生锈在场豁免一切扣留(ADR-0461 H2②;registry
    rust_wear_release_enabled 门)。"""
    output_penalty_release: bool
    """row5:输出侧罚则词缀在场豁免已定型扣留(18 号稿 §2.1 新裁行;
    载体 = data/affix_wear_semantics_data 结构化条目,行为无条件化——
    行为输入已就绪,按开关生命周期门不悬置默认关)。"""

    @property
    def hold(self) -> bool:
        """布尔释放位(True = 扣留;执行层唯一消费面)。"""
        if self.rust_release:
            return False
        if self.opening_hold:
            return True
        if self.committed_hold:
            return not self.output_penalty_release
        return False


def opening_hold_active(round_num: int | None, node_type: str | None,
                        battle_gate: bool, battle_nodes: frozenset[str]) -> bool:
    """row1:opening hold(r388/ADR-0257 × ADR-0461 H3 收窄;自 cw_op_equip_all
    迁入策略侧,语义逐字不变)。

    - r388:开局轮(P1 r≤2)hold 无条件生效——key_equips 白名单来自
      target,target 真空(重启后首局)时白名单为空;旧判
      ``tgt_comp is not None`` 会让 hold 全不生效(ADR-0257)。
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
    """row2:已定型扣留(r70 过渡持有语义;自 cw_op_equip_all 迁入策略侧)。

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
    """row4:库藏生锈豁免(ADR-0461 H2②;自 cw_op_equip_all 迁入策略侧,
    语义逐字不变)。滞留边际代价在计件封顶(registry cap=10)内单调上升,
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
                         rust_gate: bool) -> WearReleaseDecision:
    """释放判据表五行评估(18 号稿 §2.1;策略侧唯一入口,执行层只拿布尔位)。

    行 3(战斗类节点释放)不单独出字段——它是 row1 的否定支
    (opening_hold=False 即释放),与哨兵 expected 的 round≥3 自带条件
    无冲突。多行命中合并规则见 ``WearReleaseDecision`` 注。
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
    )


def resolve_affix_priority_order(comp, deployed: list,
                                 enemy_affixes: list[str] | None,
                                 occupied: dict[tuple[str, int], list[str]] | None = None,
                                 ) -> list[str] | None:
    """词缀条件优先层求序(18 号稿 §3.2 一般形,限输出侧罚则族)。

    返回 ``equip_allocation(priority_order=...)`` 的重排输入序;None =
    词缀层不启用(无输出侧谓词词缀在场 / 谓词全满足 / comp 缺失),回落
    基分配序(零重排)。纯函数;决策层产物,执行层禁内嵌评分(ADR-0461
    裁定 3 分层)。

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
    present = [getattr(d, 'char_id', '') for d in deployed
               if getattr(d, 'char_id', '')]
    if not present:
        return None
    occ = occupied or {}
    worn: dict[str, int] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        cnt = len(occ.get((getattr(d, 'position_pref', '') or '',
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
