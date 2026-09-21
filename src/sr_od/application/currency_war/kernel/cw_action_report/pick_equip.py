"""货币战争动作上报:选择装备三选一(report_action_pick_equip_param)。

**即时单相上报**(迭代 2026-09-21-pick-planner-equip-immediate-report
design §2.0/§2.1;用户裁定 2026-09-21 = action_ops.md §1 增补 2:动作 op
点完就立即上报,按成功把结果写进 game state):``CwActionPickEquipOp``
点卡后(点卡即选,无确认步)一口写完整效果逻辑态,无发射/落地两相、无
证据闩。写序:

- **归一件名命中**(param.norm_item):装备入栏(write_logic;装备区未
  观察跳写等观察)+ 获得后果链(:func:
  `cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则
  送角色腿 → bench + 合成级联,购买同语义);
- **未解析**(norm_item=''):禁猜名,equips 值不变翻来源 + 留证行
  (观察覆盖差异 = 预期内收口自愈,识别修因后走主路)。

确认未生效重派 → 效果腿重复应用的风险按增补 2 禁止清单第 4 条接受,
不设防。装备入栏/后果腿的写语义单点 = 本函数(点卡即选无第二写边)。

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


def report_action_pick_equip_param(gs: GameState, param: Any,
                                   sig: ChannelSig) -> LogicOutcome:
    """选择装备三选一上报(即时单相:点卡后一口写完整效果逻辑态)。

    写序 = 模块头 ①归一件名命中 → 入栏 + 获得后果链(同源 write_logic);
    ②未解析(norm_item='')→ equips 值不变翻来源 + 留证行
    (kind=pick_equip_name_unresolved)。出参 applied=True = 动作受理。
    """
    _validate_sig(sig, ('logic_action',))
    item = str(getattr(param, 'norm_item', '') or '')
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
        log.info('[cw-pick-equip] 上报(件名未解析): %s', '; '.join(steps))
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
    log.info('[cw-pick-equip] 上报(item=%s): %s', item, '; '.join(steps))
    return LogicOutcome(applied=True,
                        reason=f'equip_applied(consequence={c.granted or "none"},'
                               f'placed={c.performed})')
