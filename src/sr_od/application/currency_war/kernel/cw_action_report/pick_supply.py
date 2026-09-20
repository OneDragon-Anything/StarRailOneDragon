"""货币战争动作上报:补给节点选择(report_action_pick_supply_param)。

**零写族迁出·两相实现**(银狼闭环迭代 design.md §2.2 确定性通道·通道
宿主迁移;照 pick_invest 同款两相语义,效果腿幂等 = 证据闩):

- **发射相**(evidence 缺省,消费面 = ``CwActionPickSupplyOp`` 确认机械链
  发出后):仅登记意图遥测(日志行),容器零写——确认未落地重走不重复;
  装备入栏写端 = 确认收尾既有 ConfirmSupply 到账边(owned += 选中装备
  名,``CwActionPickSupplyOp`` 随链登记,发射相时序)留守不迁——本函数
  落地相不重复写 equips(无双计面);
- **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`,消费面 =
  cw_screen_supply_node handler 节点完成门 miss = 确认已落地):按实际
  开出内容应用一次(design §2.2 单位/补给腿)——
  1. **单位腿**(列含角色,param.char_name 命中):角色入备战席 + 合成
     级联(:func:`grant_bench_unit_cascade`,与商店购买同语义;入席星级
     1★ = 获取面单位恒 1★、升星仅经合成的先验口径,先验错 = 确定面
     响停修因非随机);
  2. **装备腿**(param.norm_item 归一命中):获得后果链(:func:
     `cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表
     则送角色腿 → bench + 级联);未解析 → 禁猜名,equips 值不变翻来源
     + 留证行(发射相 ConfirmSupply 收的是 OCR 原始名,翻来源防形变
     失配响停);
  3. **内容全未知**(兜底点卡路径无载荷):bench/equips 值不变翻来源 +
     留证行(内容不可辨禁猜,观察覆盖差异收口自愈)。

动作上报函数族拆分件(每动作一文件;族规约 = 包 ``cw_action_report.
__init__`` docstring)。本包 → 容器单向依赖。
"""
from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_effect_inventory import (
    apply_equip_acquire_consequence,
    grant_bench_unit_cascade,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _emit_defect,
    _validate_sig,
)

_PRODUCER: str = 'CwActionPickSupplyParam'

#: 落地相证据值(handler 节点完成门出口传参;非空即视为落地)。
EVIDENCE_OVERLAY_CLOSED: str = 'overlay_closed'

#: 补给单位腿入席星级(获取面单位恒 1★,升星仅经合成——先验口径,
#: 声明见模块头;错 = 确定面失配响停修因)。
_SUPPLY_GRANT_STAR: int = 1


def report_action_pick_supply_param(gs: GameState, param: Any, sig: ChannelSig,
                                    *, evidence: str = '') -> LogicOutcome:
    """补给节点选择上报(零写族迁出·两相实现;design §2.2 确定性通道)。

    - **发射相**(evidence 缺省):意图遥测(日志),容器零写(装备入栏
      = ConfirmSupply 既有到账边,留守发射相,见模块头);
    - **落地相**(evidence = :data:`EVIDENCE_OVERLAY_CLOSED`):按实际开出
      内容应用一次——单位腿(char_name)+ 装备后果腿(norm_item)/ 未解析
      翻来源留证 / 内容全未知翻来源留证。出参 applied=True = 动作受理。
    """
    _validate_sig(sig, ('logic_action',))
    char_name = str(getattr(param, 'char_name', '') or '')
    item = str(getattr(param, 'norm_item', '') or '')
    if evidence != EVIDENCE_OVERLAY_CLOSED:
        # 发射相:意图遥测(日志行;行级台账无意图行型,申报见模块头)。
        log.info('[cw-pick-supply] 意图遥测:char=%s item=%s idx=%s'
                 '(落地效果候证据闩)', char_name or '-', item or '-',
                 getattr(param, 'idx', '?'))
        return LogicOutcome(applied=True, reason='intent_only')
    steps: list[str] = []
    if not char_name and not item:
        # 内容全未知(兜底点卡路径):禁猜,受影响域值不变翻来源 + 留证。
        for dom, fld in (('bench', gs.bench), ('equips', gs.equips)):
            if fld.value is not None:
                gs.write_logic_rand(fld, fld.value, produced_by=_PRODUCER,
                                    evidence='pick_supply_content_flip',
                                    sig=sig)
                steps.append(f'flip:{dom}')
        _emit_defect(field_name='supply', expected='picked_content',
                     actual='unresolved', evidence='pick_supply_landing',
                     sig=sig, kind='pick_supply_content_unresolved')
        log.info('[cw-pick-supply] 落地(内容未知): %s', '; '.join(steps))
        return LogicOutcome(applied=True, reason='content_unresolved')
    if char_name:
        r = grant_bench_unit_cascade(gs, char_name, _SUPPLY_GRANT_STAR,
                                     rand=False, evidence='pick_supply_char',
                                     producer=_PRODUCER, sig=sig)
        steps.append(f'char:{char_name}(placed={r.placed},'
                     f'merge={r.merge_steps})')
    if item:
        # 装备腿 = 获得后果链(入栏已由 ConfirmSupply 到账边承载,零双写)。
        c = apply_equip_acquire_consequence(gs, item, frame='pick_supply',
                                            rand=False, sig=sig)
        if c.performed:
            steps.append(f'consequence:{c.granted}x{c.star}')
    else:
        # 装备名未解析:禁猜,equips 值不变翻来源 + 留证(ConfirmSupply
        # 收的原始 OCR 名防形变失配响停)。
        if gs.equips.value is not None:
            gs.write_logic_rand(gs.equips, gs.equips.value,
                                produced_by=_PRODUCER,
                                evidence='pick_supply_name_unresolved',
                                sig=sig)
            steps.append('equips_flip')
        _emit_defect(field_name='equips', expected='pick_supply_equip_name',
                     actual='unresolved', evidence='pick_supply_landing',
                     sig=sig, kind='pick_supply_name_unresolved')
    log.info('[cw-pick-supply] 落地(char=%s item=%s): %s', char_name, item,
             '; '.join(steps) or 'no-leg')
    return LogicOutcome(applied=True, reason='landing_applied')
