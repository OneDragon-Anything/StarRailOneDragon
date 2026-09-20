"""货币战争动作上报:选择装备三选一(report_action_pick_equip_param)。

**零写族迁出·两相实现**(银狼闭环迭代 design.md §2.2 确定性通道·通道
宿主迁移;照 pick_invest 同款两相语义,效果腿幂等 = 证据闩):

- **发射相**(evidence 缺省,消费面 = ``CwActionPickEquipOp`` 点卡机械链
  发出后):仅登记意图遥测(日志行;行级台账无「意图」行型,不强造),
  容器零写——点卡未落地重走不重复;
- **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`,消费面 =
  cw_screen_equip_pick handler 重入裁决出口「请选择」不在 = 选卡已落地):
  装备腿应用一次——归一件名(param.norm_item)命中 → 装备入栏
  (write_logic;装备区未观察跳写等观察)+ 获得后果链(:func:
  `cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则
  送角色腿 → bench + 合成级联,购买同语义);未解析 → 禁猜名,equips
  值不变翻来源 + 留证行(照 cw_screen_yinlang 装备腿既有形态,观察覆盖
  差异 = 预期内收口自愈)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    apply_equip_acquire_consequence,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)

_PRODUCER: str = 'CwActionPickEquipParam'

#: 落地相证据值(handler 重入裁决出口传参;非空即视为落地)。
EVIDENCE_OVERLAY_CLOSED: str = 'overlay_closed'


def report_action_pick_equip_param(gs: GameState, param: Any, sig: ChannelSig,
                                   *, evidence: str = '') -> LogicOutcome:
    """选择装备三选一上报(零写族迁出·两相实现;design §2.2 确定性通道)。

    - **发射相**(evidence 缺省):意图遥测(日志),容器零写;
    - **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`):装备腿
      应用一次——归一件名命中 → 入栏 + 获得后果链(同源 write_logic);
      未解析(norm_item='')→ equips 值不变翻来源 + 留证行
      (kind=pick_equip_name_unresolved)。出参 applied=True = 动作受理。
    """
    _validate_sig(sig, ('logic_action',))
    item = str(getattr(param, 'norm_item', '') or '')
    if evidence != EVIDENCE_OVERLAY_CLOSED:
        # 发射相:意图遥测(日志行;行级台账无意图行型,申报见模块头)。
        log.info('[cw-pick-equip] 意图遥测:item=%s idx=%s(落地效果候证据闩)',
                 item or '-', getattr(param, 'idx', '?'))
        return LogicOutcome(applied=True, reason='intent_only')
    steps: list[str] = []
    if not item:
        # 未解析:禁猜名,equips 值不变翻来源(collect_ore 步2 同款)+
        # 留证行——观察覆盖差异 = 预期内收口自愈,识别修因后走主路。
        if gs.equips.value is not None:
            gs.write_logic_rand(gs.equips, gs.equips.value,
                                produced_by=_PRODUCER,
                                evidence='pick_equip_name_unresolved',
                                sig=sig)
            steps.append('equips_flip')
        _emit_defect(field_name='equips', expected='pick_equip_name',
                     actual='unresolved', evidence='pick_equip_landing',
                     sig=sig, kind='pick_equip_name_unresolved')
        log.info('[cw-pick-equip] 落地(件名未解析): %s', '; '.join(steps))
        return LogicOutcome(applied=True, reason='equip_name_unresolved')
    inv = gs.equips.value
    if inv is not None:
        gs.write_logic(gs.equips, list(inv) + [item],
                       produced_by=_PRODUCER, evidence='pick_equip_gain',
                       sig=sig)
        steps.append('equips+1')
    else:
        steps.append('equips_unobserved(入栏跳写)')
    # 获得后果链(表外件零写零行为;入栏与后果同源 write_logic)。
    c = apply_equip_acquire_consequence(gs, item, frame='pick_equip',
                                        rand=False, sig=sig)
    if c.performed:
        steps.append(f'consequence:{c.granted}x{c.star}')
    log.info('[cw-pick-equip] 落地(item=%s): %s', item, '; '.join(steps))
    return LogicOutcome(applied=True,
                        reason=f'equip_applied(consequence={c.granted or "none"},'
                               f'placed={c.performed})')
