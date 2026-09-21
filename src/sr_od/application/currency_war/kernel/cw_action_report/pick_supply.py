"""货币战争动作上报:补给节点选择(report_action_pick_supply_param)。

**即时单相上报**(迭代 2026-09-21-event-refresh-unify-supply-pick
design §2.0B;用户裁定 2026-09-21 = action_ops.md §1 增补 2:动作 op
点完立即上报完整结果):``CwActionPickSupplyOp`` 确认点击后一口写全部
效果逻辑态,无发射/落地两相、无证据闩。写序:

1. **内容全未知**(兜底点卡路径,char_name 与 norm_item 双空):bench/
   equips 值不变翻来源 + ``pick_supply_content_unresolved`` 留证行
   (内容不可辨禁猜,观察覆盖差异收口自愈)——分支逐位保持旧落地相形态;
2. **单位腿**(param.char_name):角色入备战席 + 合成级联(:func:
   `grant_bench_unit_cascade`,与商店购买同语义;入席星级 1★ = 获取面
   单位恒 1★、升星仅经合成的先验口径,先验错 = 确定面响停修因非随机);
3. **装备腿**(param.norm_item = 注册表级分层归一规范名):owned += 规范名
   (账面恒标准名——owned 权威写端 ``read_equips`` 观察摄取本产规范名,
   原始 OCR 名到账是账面异类形态,本批退出)+ 获得后果链(:func:
   `cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则
   送角色腿 → bench + 级联);norm_item = ''(未解析)→ 禁猜,equips 值
   不变翻来源 + 留证行(fail-closed:错名不入账,观察覆盖自愈)。

装备入栏/后果腿的写语义单点 = 本函数(补给确认无第二写边)。

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

#: 补给单位腿入席星级(获取面单位恒 1★,升星仅经合成——先验口径,
#: 声明见模块头;错 = 确定面失配响停修因)。
_SUPPLY_GRANT_STAR: int = 1


def report_action_pick_supply_param(gs: GameState, param: Any,
                                    sig: ChannelSig) -> LogicOutcome:
    """补给节点选择上报(即时单相:确认点击后一口写全部效果逻辑态)。

    写序 = 模块头 ①内容全未知翻来源留证 / ②单位腿 / ③装备腿(owned
    += 规范名 + 获得后果链;norm_item 未解析 = 翻来源留证)。出参
    applied=True = 动作受理。
    """
    _validate_sig(sig, ('logic_action',))
    char_name = str(getattr(param, 'char_name', '') or '')
    item = str(getattr(param, 'norm_item', '') or '')
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
        log.info('[cw-pick-supply] 上报(内容未知): %s', '; '.join(steps))
        return LogicOutcome(applied=True, reason='content_unresolved')
    if char_name:
        r = grant_bench_unit_cascade(gs, char_name, _SUPPLY_GRANT_STAR,
                                     rand=False, evidence='pick_supply_char',
                                     producer=_PRODUCER, sig=sig)
        steps.append(f'char:{char_name}(placed={r.placed},'
                     f'merge={r.merge_steps})')
    if item:
        # 装备腿:owned += 规范名(账面恒标准名;单一源 = gs.equips 现读-
        # 改写-回写,与 cw_exec_state 确认族同形)+ 获得后果链(获得即送)。
        owned = list(gs.equips.value or [])
        owned.append(item)
        gs.write_logic(gs.equips, owned, produced_by=_PRODUCER,
                       evidence=f'owned[{item}] +1', sig=sig)
        steps.append(f'owned:{item}')
        c = apply_equip_acquire_consequence(gs, item, frame='pick_supply',
                                            rand=False, sig=sig)
        if c.performed:
            steps.append(f'consequence:{c.granted}x{c.star}')
    else:
        # 装备名未解析:禁猜,equips 值不变翻来源 + 留证(分层归一多/零
        # 命中 = 件名不可辨,错名不入账由观察覆盖自愈)。
        if gs.equips.value is not None:
            gs.write_logic_rand(gs.equips, gs.equips.value,
                                produced_by=_PRODUCER,
                                evidence='pick_supply_name_unresolved',
                                sig=sig)
            steps.append('equips_flip')
        _emit_defect(field_name='equips', expected='pick_supply_equip_name',
                     actual='unresolved', evidence='pick_supply_landing',
                     sig=sig, kind='pick_supply_name_unresolved')
    log.info('[cw-pick-supply] 上报(char=%s item=%s): %s', char_name, item,
             '; '.join(steps) or 'no-leg')
    return LogicOutcome(applied=True, reason='landing_applied')
