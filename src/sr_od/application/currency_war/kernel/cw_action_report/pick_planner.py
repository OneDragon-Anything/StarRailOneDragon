"""货币战争动作上报:银狼策划「我来当策划」选择(report_action_pick_planner_param)。

**零写族迁出·两相形态**(推广批,承接 2026-09-18-yinlang-exclusive-loop
design.md §2.1⑤;与 pick_invest 同构,用户定稿 = 每动作一文件分步更新):
上报收敛自 ``zero_writes`` 占位(发射相)与画面 op 过渡位宿主
(``cw_screen_yinlang.apply_pick_planner_landing``,已退役),按 ``evidence``
分相:

- **发射相**(evidence 缺省,消费面 = ``CwActionPickPlannerOp`` 机械链发出后):
  仅登记意图遥测(日志行;行级台账无「意图」行型,不强造——同 pick_invest
  申报),容器零写——确认未落地重走不重复;
- **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`,消费面 = 画面 op
  ``CwScreenYinLang`` 重入裁决出口「入口词不在 = overlay 已关」):腿型分派
  应用一次——
  - **equip**:件名命中 → 装备入栏(write_logic)+ 获得后果链
    (apply_equip_acquire_consequence);未解析 → 禁猜,equips 值不变翻
    来源 + 留证行;
  - **upgrade**:变换窗三态 + 档行(见 :func:`_apply_upgrade_transform`);
  - **unknown**:零记账 + 留证行;**weaken**:零记账(全场弱化为节点态
    语义,无容器字段)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.pick_invest import (
    EVIDENCE_OVERLAY_CLOSED,
)
from sr_od.application.currency_war.kernel.cw_economy import effective_cost
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    apply_equip_acquire_consequence,
    merge_cascade_write,
)
from sr_od.application.currency_war.kernel.cw_events import (
    PLANNER_LEG_EQUIP,
    PLANNER_LEG_UNKNOWN,
    PLANNER_LEG_UPGRADE,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)

_PLANNER_PRODUCER: str = 'CwActionPickPlannerParam'
_LV999_ID: str = '银狼LV.999'   # 变换窗/级联/档行身份名(cw_chars 规范名)


def report_action_pick_planner_param(gs: GameState, param: Any, sig: ChannelSig,
                                     *, leg_type: str = '',
                                     norm_item: str = '',
                                     evidence: str = '') -> LogicOutcome:
    """银狼策划选择上报(两相;与 pick_invest 同构)。

    - **发射相**(evidence 缺省):意图遥测日志行,容器零写;
    - **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`):腿型分派
      逐步应用,逐字段各落一行遥测(单次动作报告多次写遥测 = 预期行为):
      equip 入栏+后果链 / upgrade 变换窗三态+档行 / unknown·weaken 零记账;
    - ``leg_type``/``norm_item`` = 决策半腿型载荷(classify_planner_leg
      产物,经 OverlayPickExecEnv 随发射透传、画面 op 实例存证至落地);
    - 出参 applied=True = 动作受理(拒分支走落地相内域守卫,不整批拒)。
    """
    _validate_sig(sig, ('logic_action',))
    if evidence != EVIDENCE_OVERLAY_CLOSED:
        # 发射相:意图遥测(日志行;行级台账无意图行型,申报见模块头)。
        log.info('[cw-pick-planner] 意图遥测:leg_type=%s norm_item=%s idx=%s'
                 '(效果腿候证据闩)', leg_type or '?', norm_item or '',
                 getattr(param, 'idx', '?'))
        return LogicOutcome(applied=True, reason='intent_only')
    if leg_type == PLANNER_LEG_EQUIP:
        return _apply_equip_leg(gs, norm_item, sig)
    if leg_type == PLANNER_LEG_UPGRADE:
        return _apply_upgrade_transform(gs, sig)
    if leg_type == PLANNER_LEG_UNKNOWN:
        _emit_defect(field_name='planner_opts', expected='planner_leg',
                     actual='unrecognized_text', evidence='planner_landing',
                     sig=sig, kind='planner_leg_unknown')
        return LogicOutcome(applied=True, reason='unknown_leg_evidenced')
    return LogicOutcome(applied=True, reason='weaken_leg_zero_write')


def _apply_equip_leg(gs: GameState, norm_item: str,
                     sig: ChannelSig) -> LogicOutcome:
    """装备腿(确定性通道,design §2.1②):入栏 + 获得后果链。"""
    if not norm_item:
        # 未解析:禁猜名,equips 值不变翻来源(collect_ore 步2 同款)+
        # 留证行——观察覆盖差异 = 预期内收口自愈。
        if gs.equips.value is not None:
            gs.write_logic_rand(gs.equips, gs.equips.value,
                                produced_by=_PLANNER_PRODUCER,
                                evidence='planner_equip_unresolved', sig=sig)
        _emit_defect(field_name='equips', expected='planner_equip_name',
                     actual='unresolved', evidence='planner_landing',
                     sig=sig, kind='planner_equip_name_unresolved')
        return LogicOutcome(applied=True, reason='equip_name_unresolved')
    inv = gs.equips.value
    if inv is not None:
        gs.write_logic(gs.equips, list(inv) + [norm_item],
                       produced_by=_PLANNER_PRODUCER,
                       evidence='planner_equip_gain', sig=sig)
    # 获得后果链(表外件零写零行为;入栏与后果同源 write_logic)。
    c = apply_equip_acquire_consequence(gs, norm_item, frame='planner',
                                        rand=False, sig=sig)
    return LogicOutcome(applied=True,
                        reason=f'equip_applied(consequence={c.granted or "none"},'
                               f'placed={c.performed})')


def _apply_upgrade_transform(gs: GameState,
                             sig: ChannelSig) -> LogicOutcome:
    """升费腿 = 变换窗三态 + 档行(design §2.2/§2.1③):前置硬校验对发射
    时容器观察态(bench ∪ front_row ∪ back_row 多重集)的 (银狼LV.999, 2★)
    计数:

    - **现档 ≥ 5**(误走本腿:5 费升 2 星两选项皆装备,upgrade 不应出现;
      出现 = 识别或机制异常)→ 不写变换不写档,留证行
      (kind=``planner_upgrade_tier_ceiling``);
    - **恰一枚** → 工作副本变换(−2★ +1★,槽位无关,落点不建模观察为
      真值)→ **档行**(变换落行后、级联前;现档 = :func:`effective_cost`,
      档 +1 = 牌库改变的容器表达——升费后池桶归属迁到新费用档)→ 级联
      (merge_cascade_write 正常推演——费用档不同时存在[口述·权威
      2026-09-18],分组键无跨档歧义)→ 受影响域各落一行(write_logic);
    - **多枚**(二次升费现实可发)→ 触发单位不可辨(禁猜)→ 受影响域
      值不变翻来源 + 留证行(kind=planner_upgrade_ambiguous),档不动;
    - **零枚/未观察** → 不写 + 留证行(真异常,照真失配响停,fail-closed
      禁猜),档不动。

    费用档不建模于单位(档 = 容器 match 级字段 lv999_cost_tier,本腿即其
    写端);「新费档银狼刷进商店」连带腿 = 档行兼任(池桶归属随档迁移),
    不另造申报行(设计 §2.2)。
    """
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        deployed_indexed_to_rows,
        deployed_rows_to_indexed,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_of_working,
    )

    view = gs.bench.value
    front = gs.front_row.value
    back = gs.back_row.value
    if view is None and front is None and back is None:
        _emit_defect(field_name='bench',
                     expected=f'({_LV999_ID},2)×1',
                     actual='containers_unobserved', evidence='planner_landing',
                     sig=sig, kind='planner_upgrade_source_missing')
        return LogicOutcome(applied=False,
                            reason='upgrade_source_unobserved')
    # 现档封顶闸(设计 §2.2):5 费档 upgrade 腿不期出现,出现即留证零写。
    tier = effective_cost(gs, _LV999_ID)
    if tier >= 5:
        _emit_defect(field_name='lv999_cost_tier',
                     expected='现档 < 5(升费腿仅 3/4 档触发)',
                     actual=f'现档={tier}', evidence='planner_landing',
                     sig=sig, kind='planner_upgrade_tier_ceiling')
        return LogicOutcome(applied=False, reason='upgrade_tier_ceiling')
    # P1 容器原生工作副本:bench = BenchView 槽序、deployed = 行域下标
    # 派生表(§2.1);元素 frozen,浅拷贝列表即快照(变换 = replace 新
    # 构造,零别名)。
    work_bench = list(view.slots) if view is not None else []
    work_dep = deployed_rows_to_indexed(front, back)
    hits = [i for i, b in enumerate(work_bench)
            if b is not None and b.kind == 'unit' and b.unit is not None
            and b.unit.char_id == _LV999_ID and b.unit.star == 2]
    hits_dep = [i for i, d in enumerate(work_dep)
                if d is not None and d.char_id == _LV999_ID and d.star == 2]
    count = len(hits) + len(hits_dep)
    if count == 0:
        _emit_defect(field_name='bench',
                     expected=f'({_LV999_ID},2)×1', actual='count=0',
                     evidence='planner_landing', sig=sig,
                     kind='planner_upgrade_source_missing')
        return LogicOutcome(applied=False, reason='upgrade_source_missing')
    if count > 1:
        # 多枚:值不变翻来源(受影响域全集,未观察域跳写)+ 留证行自愈。
        for fld in (gs.bench, gs.front_row, gs.back_row):
            if fld.value is None:
                continue
            gs.write_logic_rand(fld, fld.value,
                                produced_by=_PLANNER_PRODUCER,
                                evidence='planner_upgrade_ambiguous_mark',
                                sig=sig)
        _emit_defect(field_name='bench',
                     expected=f'({_LV999_ID},2)×1', actual=f'count={count}',
                     evidence='planner_landing', sig=sig,
                     kind='planner_upgrade_ambiguous')
        return LogicOutcome(applied=True, reason='upgrade_ambiguous_flipped')
    # 恰一枚:工作副本变换(槽位无关)→ 档行(变换落行后、级联前)→
    # 受影响域落行 → 级联。
    if hits:
        _s = work_bench[hits[0]]
        work_bench[hits[0]] = replace(_s, unit=replace(_s.unit, star=1))
        gs.write_logic(gs.bench, bench_view_of_working(work_bench, view),
                       produced_by=_PLANNER_PRODUCER,
                       evidence='planner_upgrade_transform', sig=sig)
    else:
        work_dep[hits_dep[0]] = replace(work_dep[hits_dep[0]], star=1)
        f2, b2 = deployed_indexed_to_rows(work_dep)
        gs.write_logic(gs.front_row, f2, produced_by=_PLANNER_PRODUCER,
                       evidence='planner_upgrade_transform', sig=sig)
        gs.write_logic(gs.back_row, b2, produced_by=_PLANNER_PRODUCER,
                       evidence='planner_upgrade_transform', sig=sig)
    gs.write_logic(gs.lv999_cost_tier, tier + 1,
                   produced_by=_PLANNER_PRODUCER,
                   evidence='planner_upgrade_tier', sig=sig)
    merge_cascade_write(gs, work_bench, work_dep, rand=False,
                        evidence='planner_upgrade_merge',
                        producer=_PLANNER_PRODUCER, sig=sig,
                        orig_view=view)
    return LogicOutcome(applied=True, reason='upgrade_transformed')
