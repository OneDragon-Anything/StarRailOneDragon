"""货币战争动作上报:购买经验(单击/多击)(report_action_level_up_param)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留在 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _record_lv8_window_start,
    _validate_sig,
    level_of,
)


def report_action_level_up_param(gs: GameState, param: Any, sig: ChannelSig,
                                 executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """购买经验上报(单击/多击):xp/level 跨门槛推进(推进算子单一源 =
    ``xp_apply_clicks``,跨级连跳+溢出结转)+ gold −cost×clicks 直写。
    满级 = applied=False + reason='level_cap' 零写(MAX_PLAYER_LEVEL
    封顶单一源);executed None = 击数自算 1(理想执行,sim 路径)。
    现役触发面 = 备战域(商店域发射已随 2026-10-17 迭代 T-1 退役,
    商店域双类型词表随 T-4 退役删除)。

    **商业间谍升级回调**(2026-10-17-levelup-shop-transition design
    §2.3;触发点 = 本上报函数升级生效时点):升级真跨级(``_new_lvl !=
    _lv_v``)∧ 在册持有(单一源 = ``cw_investments.spy_on_level_up_
    active``)> 0 → ①置随机态信号 ``shop_randomized_pending = True``
    (§2.4 写端唯一 = 本回调第 4 步;实机同样生效——游戏侧真实刷新+
    偷牌,重开位读真牌面)②随附 ``world_decl``(trigger =
    ``spy_shop_refresh``,next_screen = 备战档)供动作 op 经
    ``cw_sim_ports.declare_world`` 喂入 sim 后端执行世界腿①-③(抽 5 张
    /偷最贵 3 张入席/剩余 2 张 = 商店新牌面;sim 采样即世界真值,实机
    端口未装 = no-op,世界后果归游戏引擎)。无商业间谍 = 零商店副作用
    (牌面不变;重开靠备战执行帧清标记通道,design §2.3 末条)。

    **升级窗口达成位记录**(尾段,商业间谍回调块后):上报收敛即调
    ``_record_lv8_window_start``(环境「成功经验」通道主挂点——买经验推 8
    时记达成节点位,窗口发放归 kernel 发放桥 grant_effect_node_xp;未持
    条目/未达标/生效位未锚定 = 零动作)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    from sr_od.application.currency_war.kernel.cw_economy import (
        MAX_PLAYER_LEVEL,
        XP_TO_NEXT_LEVEL,
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
    if level_of(gs) >= MAX_PLAYER_LEVEL:
        return LogicOutcome(applied=False, reason='level_cap')
    g = gs.gold.value
    if g is not None:
        _w(gs.gold, int(g) - int(getattr(param, 'cost', 0) or 0) * clicks,
           'proj_levelup_gold')
    _lv_v = gs.level.value
    xp_v = gs.xp.value
    _spy_decl = None
    if xp_v is not None and _lv_v is not None:
        _new_lvl, _cur = xp_apply_clicks(int(_lv_v), int(xp_v[0]), clicks)
        _w(gs.xp, (_cur, XP_TO_NEXT_LEVEL.get(_new_lvl, _cur)),
           'proj_levelup_xp')
        if _new_lvl != int(_lv_v):
            _w(gs.level, _new_lvl, 'proj_levelup_level')
            # —— 商业间谍升级回调(升级真跨级才触发;xp-only 帧零副作用)——
            from sr_od.application.currency_war.kernel.cw_investments import (
                spy_on_level_up_active,
            )
            if spy_on_level_up_active(gs) > 0:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    SCREEN_PREP_FRAME,
                    mark_shop_randomized_pending,
                )
                from sr_od.application.currency_war.kernel.cw_world_decl import (
                    WorldDecl,
                )
                # 步④:置随机态信号(非 Field 簿记槽直写;写端唯一 = 本
                # 回调,槽注申报;幂等,连升多级同帧只置位)。
                mark_shop_randomized_pending(gs)
                # 世界腿①-③声明(op 层喂入 sim 后端;实机 no-op)。
                _spy_decl = WorldDecl(next_screen=SCREEN_PREP_FRAME,
                                      trigger='spy_shop_refresh')
    # 升级窗口达成位记录(成功经验通道主挂点;内部自判条目在场 ∧ 未记录 ∧
    # level_of >= 阈值,零旁路条件——全量零动作安全,见 _record_lv8_window_start)。
    _record_lv8_window_start(gs)
    return LogicOutcome(applied=True, world_decl=_spy_decl)

