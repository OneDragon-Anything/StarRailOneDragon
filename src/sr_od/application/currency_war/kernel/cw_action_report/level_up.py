"""货币战争动作上报:购买经验(单击/多击)(report_action_level_up_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。状态容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 状态容器单向依赖。
语义权威版本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _record_lv8_window_start,
    _validate_sig,
    level_of,
    mark_gold_spent,
)


def report_action_level_up_param(gs: GameState, param: Any, sig: ChannelSig,
                                 executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """购买经验上报(单击/多击):xp/level 跨门槛推进(推进算子单一源 =
    ``xp_apply_clicks``,跨级连跳+溢出结转)+ gold −cost×clicks 直写。
    达帽 = applied=False + reason='level_cap' 零写(帽单一源 =
    ``cw_economy.level_cap_of``:无卡 = MAX_PLAYER_LEVEL,持等级帽卡 =
    注册表覆写经聚合归一);executed None = 击数自算 1(理想执行,sim 路径)。
    现役触发面 = 备战域(商店域发射通道已退役,
    商店域双类型词表随 T-4 退役删除)。

    **升级连锁(商业间谍/节节高升/窗口记位)**:三块连锁已统一迁入升级
    值变更回调(调度器单一源 = ``cw_levelup_callbacks.on_level_up_change``,
    宿主 = ``GameState._write_logic_frame`` level 分支尾;源 = 任意经验
    来源升级,不只买经验动作)——本上报函数的跨级 level 直写在写尾自动
    触发全套连锁,本函数零连锁代码。连锁的 spy 状态副本写入分支声明经状态容器簿记
    队列 ``pending_levelup_world_decls`` 流转(写端唯一 = 调度器 spy
    分支,只在模拟器装配时写入):本上报尾取走队列头部装入 LogicOutcome
    (见函数尾),动作执行点立即喂入 ``cw_sim_ports.declare_world``,商店
    分支当拍执行;live 未装配 = 队列恒空 = world_decl None(端口 no-op,
    状态副本后果归游戏引擎)。

    **升级窗口达成位记录**(尾段):上报收敛即调
    ``_record_lv8_window_start``(环境「成功经验」通道主插入位置;跨级事件
    级检测已归值回调,本位 = xp-only 迟到达扫描——等级从 ≥8 才买经验的
    漏记纠偏与 xp-only 帧扫描;未持条目/未达标/生效位未锚定 = 零动作)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        XP_TO_NEXT_LEVEL,
        level_cap_of,
        xp_apply_clicks,
    )

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionLevelUpParam',
                       evidence=evidence, sig=_grp_sig)

    clicks = executed.levelup_clicks if executed is not None else 1
    if clicks is None:
        return LogicOutcome(applied=False, reason='levelup_clicks_not_fed')
    clicks = max(0, int(clicks))
    # 满级门取帽单一源 = level_cap_of(无卡 = MAX_PLAYER_LEVEL 既有语义;
    # 持等级帽卡时门随帽提前——live 侧与游戏自算拒发同向,状态副本写分歧由
    # 下一帧观察 reconcile 兜底,现役观察覆盖语义不变)。
    _cap = level_cap_of(gs)
    if level_of(gs) >= _cap:
        return LogicOutcome(applied=False, reason='level_cap')
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) - int(getattr(param, 'cost', 0) or 0) * clicks,
           'proj_levelup_gold')
    _lv_v = gs.level.value
    xp_v = gs.xp.value
    if xp_v is not None and _lv_v is not None:
        _new_lvl, _cur = xp_apply_clicks(int(_lv_v), int(xp_v[0]), clicks,
                                         level_cap=_cap)
        _w(gs.xp, (_cur, XP_TO_NEXT_LEVEL.get(_new_lvl, _cur)),
           'proj_levelup_xp')
        if _new_lvl != int(_lv_v):
            # 跨级直写:写尾触发升级值变更回调(三块连锁,见模块头)。
            _w(gs.level, _new_lvl, 'proj_levelup_level')
    # 升级窗口达成位记录(成功经验通道主插入位置;内部自判条目在场 ∧ 未记录 ∧
    # level_of >= 阈值,零旁路条件安全——xp-only 帧也扫,迟到达纠偏承载位)。
    _record_lv8_window_start(gs)
    # 金币花费事件置位(存款回报条件输入,fields.md §3.3.9):零费击
    # (cost×clicks=0)= 无金离手不计花费;cost 缺省 0 视同零费。
    if int(getattr(param, 'cost', 0) or 0) * clicks > 0:
        mark_gold_spent(gs, produced_by='CwActionLevelUpParam', sig=_grp_sig)
    # 升级连锁状态副本声明出队(上报尾消费口,取走即清):买经验单次 level 写
    # = 单值变迁 = 队列至多含本动作自己刚写入的声明;余项(防御形态)留待
    # 模拟器 advance 尾统一排空,留证 log 不静默。
    from sr_od.application.currency_war.kernel.cw_levelup_callbacks import (
        take_levelup_world_decl,
    )
    _world_decl = take_levelup_world_decl(gs)
    _left = len(gs.pending_levelup_world_decls)
    if _left:
        log.info('[cw][levelup] 升级声明队列余项留待 advance 尾排空: n=%d',
                 _left)
    return LogicOutcome(applied=True, world_decl=_world_decl)
