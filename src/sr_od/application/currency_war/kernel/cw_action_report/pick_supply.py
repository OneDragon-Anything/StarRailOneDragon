"""货币战争动作上报:补给节点选择(report_action_pick_supply_param)。

**即时单相上报**(行为正本 = `flow/action_ops.md` §4.5 PickSupply 行;
用户裁定 2026-09-21 = action_ops.md §1 增补 2:动作 op
点完立即上报完整结果):``CwActionPickSupplyOp`` 确认点击后一口写全部
效果逻辑态,无发出/落地两相、无证据标志。写序:

1. **内容全未知**(兜底点卡路径,char_name/norm_item/extra_norm_items
   三载荷全空):bench/equips 值不变翻来源 + ``pick_supply_content_unresolved``
   留存证据行(内容不可辨禁猜,观察覆盖差异收束自愈)——分支逐位保持旧落地补写形态形态;
2. **单位腿**(param.char_name):角色入备战席 + 合成级联(:func:
   `grant_bench_unit_cascade`,与商店购买同语义;入席星级 1★ = 获取面
   单位恒 1★、升星仅经合成的先验口径,先验错 = 确定面响停修因非随机);
3. **装备腿 0..n 件**(列 = 角色+装备组,):集合 = ``(norm_item,
   *extra_norm_items)``,写序 = 主件 → 附加件(画面 y 序),同 sig 同窗
   相邻(同一确认动作的原子面,/ 同 sig 相邻先例)。非空件逐件走
   同形写入:owned += 归一规范名(账面恒标准名——owned 权威写端
   ``read_equips`` 观察摄取本产规范名)+ 获得后果链(:func:
   `cw_effect_inventory.apply_equip_acquire_consequence`,命中后果表则
   送角色腿 → bench + 级联);'' 件(归一未解析)逐件禁猜 → equips 值
   不变翻来源 + 留存证据行 fail-closed(错名不入账,观察覆盖自愈),已解析
   件照常入账(不整批弃)。
   **零装备名分支**(char_name 非空 ∧ 装备腿集合无非空件):装备域零写
   + 留存证据 ``pick_supply_no_equip_column``(日志行 + 返回 reason 载体;
   装备域无写帧,evidence 参数无处挂)、**不发缺陷**。语义 = 该列零
   装备名读数,覆盖两形态:①char-only 列(人才储备类,合法无装备);
   ②列有装备行但件名全失读——读链层面①②不可分(件名失读即无文本
   条目);失配仍由 equips 观察整表覆盖下一帧暴露(fail-visible)。

装备入栏/后果腿的写语义单点 = 本函数(补给确认无第二写边)。

**后果声明**(动作后果声明化详设 world-decl.md §2 表 #12):applied 出口
构造 ``WorldDecl``(trigger = ``pick_supply``;``next_screen`` = 补给屏
——选卡后画面本瞬间不变,随后到的 node_advance 声明才切走),转移事件
广播随本动作单轨切换摘除。

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
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

_PRODUCER: str = 'CwActionPickSupplyParam'

#: 补给单位腿入席星级(获取面单位恒 1★,升星仅经合成——先验口径,
#: 声明见模块头;错 = 确定面失配响停修因)。
_SUPPLY_GRANT_STAR: int = 1

#: 补给声明的推进分派类别(详设 §2 表 #12;封闭集单一源 = sim 后端
#: advance 分派表键集,值零新词沿用现役动作名)。
_DECL_TRIGGER: str = 'pick_supply'

#: 补给声明(宝钻写归 backend ``_on_supply_picked`` 读容器现值,本上报
#: 零写;next_screen 权威 = screen_info 补给档 + sim ``_on_supply_picked``
#: 零画面写停留)。
_DECL: WorldDecl = WorldDecl(next_screen='货币战争-补给',
                             trigger=_DECL_TRIGGER)


def report_action_pick_supply_param(gs: GameState, param: Any,
                                    sig: ChannelSig) -> LogicOutcome:
    """补给节点选择上报(即时单相:确认点击后一口写全部效果逻辑态)。

    写序 = 模块头 ①内容全未知翻来源留存证据 / ②单位腿 / ③装备腿 0..n 件
    (集合 = norm_item + extra_norm_items,主件 → 附加件画面 y 序;'' 件
    逐件 fail-closed;零装备名列 = 装备域零写 + ``pick_supply_no_equip_
    column`` 留存证据、不发缺陷)。出参 applied=True = 动作受理,出口构造
    后果声明(:data:`_DECL`)。
    """
    _validate_sig(sig, ('logic_action',))
    char_name = str(getattr(param, 'char_name', '') or '')
    item = str(getattr(param, 'norm_item', '') or '')
    extras = tuple(str(e) for e in (getattr(param, 'extra_norm_items', ())
                                    or ()))
    equip_legs = (item, *extras)
    steps: list[str] = []
    if not char_name and not any(equip_legs):
        # 内容全未知(兜底点卡路径):禁猜,受影响域值不变翻来源 + 留存证据。
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
        return LogicOutcome(applied=True, reason='content_unresolved',
                            world_decl=_DECL)
    if char_name:
        r = grant_bench_unit_cascade(gs, char_name, _SUPPLY_GRANT_STAR,
                                     rand=False, evidence='pick_supply_char',
                                     producer=_PRODUCER, sig=sig)
        steps.append(f'char:{char_name}(placed={r.placed},'
                     f'merge={r.merge_steps})')
    if not any(equip_legs):
        # 零装备名分支(char-only 列 / 件名全失读,两形态读链不可分):
        # 本列无装备名读数,装备域零写(无预测无期望,零翻来源)+ 留存证据
        # (日志行 + reason;装备域无写帧,evidence 参数无处挂)、不发
        # 缺陷——现役 else 分支按 item='' 归因会把合法 char-only 列误发
        # 「装备名未解析」缺陷,本分支消除该伪缺陷;件名失读子况的失配
        # 仍由 equips 观察整表覆盖下一帧暴露(fail-visible)。
        log.info('[cw-pick-supply] 上报(char=%s 无装备名读数): %s',
                 char_name, '; '.join(steps) or 'no-leg')
        return LogicOutcome(applied=True, reason='no_equip_column',
                            world_decl=_DECL)
    # 装备腿 0..n 件:主件 → 附加件(画面 y 序),同 sig 同窗相邻(同一
    # 确认动作的原子面);非空件 = owned += 规范名 + 获得后果链(获得即
    # 送),'' 件逐件禁猜翻来源留存证据 fail-closed(已解析件照常入账)。
    for _leg in equip_legs:
        if _leg:
            # 装备腿:owned += 规范名(账面恒标准名;单一源 = gs.equips
            # 现读-改写-回写,与 cw_exec_state 确认族同形)。
            owned = list(gs.equips.value or [])
            owned.append(_leg)
            gs.write_logic(gs.equips, owned, produced_by=_PRODUCER,
                           evidence=f'owned[{_leg}] +1', sig=sig)
            steps.append(f'owned:{_leg}')
            c = apply_equip_acquire_consequence(gs, _leg, frame='pick_supply',
                                                rand=False, sig=sig)
            if c.performed:
                steps.append(f'consequence:{c.granted}x{c.star}')
        else:
            # 装备名未解析:禁猜,equips 值不变翻来源 + 留存证据(分层归一
            # 多/零命中 = 件名不可辨,错名不入账由观察覆盖自愈)。
            if gs.equips.value is not None:
                gs.write_logic_rand(gs.equips, gs.equips.value,
                                    produced_by=_PRODUCER,
                                    evidence='pick_supply_name_unresolved',
                                    sig=sig)
                steps.append('equips_flip')
            _emit_defect(field_name='equips',
                         expected='pick_supply_equip_name',
                         actual='unresolved', evidence='pick_supply_landing',
                         sig=sig, kind='pick_supply_name_unresolved')
    log.info('[cw-pick-supply] 上报(char=%s equips=%s): %s', char_name,
             list(equip_legs), '; '.join(steps) or 'no-leg')
    return LogicOutcome(applied=True, reason='landing_applied',
                        world_decl=_DECL)
