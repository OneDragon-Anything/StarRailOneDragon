"""BOSS 简报屏观察契约与上报(kernel 纯数据;正本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 入口裁决:门判定 + 稳定帧引用。report 写点 = **BOSS 类型直定**
(迭代 2026-09-20-node-advance-action-report 切换批自旧 BOSS 简报腿迁移,
design §2.5 表):简报屏上报经 kernel ``_write_derived_node_type`` 直定
boss 类型,目标 = 现 hist——简报屏仍是 boss 类型权威。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_BOSS_BRIEFING,
    ChannelSig,
    GameState,
    _write_derived_node_type,
)


@dataclass
class CwScreenBossBriefingObs:
    """BOSS 简报屏观察结果(统一形态:门判定 + 帧引用)。"""

    on_screen: bool = False
    screen: Any = None


def report_screen_boss_briefing_obs(gs: GameState,
                                    obs: CwScreenBossBriefingObs, *,
                                    sig: ChannelSig | None = None) -> None:
    """BOSS 简报屏观察上报:boss 类型直定(目标 = 现 hist;design §2.5 表,
   攻击 F4 迁移)。

    - **直定前置守卫(去证据门形态,用户裁定 2026-09-21)**:结算确认
      点击即上报(无证据等待)⇒ 上报先于下一节点任何画面渲染恒成立
      ⇒ 简报 op 被分派时 hist 已被 settle_confirm 推进至 boss 节点
      ——「hist 落后、类型写错节点」结构性不可达。hist None(锚先于
      任何上报的假想形态)= 零写禁猜(防御性保留);
    - 序号推进半部已随旧腿退役:boss 节点序由结算确认上报推进,本口零
      node_ord 写;
    - 幂等:同 hist 重复上报走 _write_derived_node_type 冲突纪律(同节点
      同类型 = 同值重写行,自然幂等);
    - actor = CwScreenBossBriefing(宿主 op 登记名,留证归因);类型直定
      经 _derive_write 走 logic_hook 渠道③,行型不变。
    """
    if not obs.on_screen:
        return
    hist = gs.node_hist_ord
    if hist is None:
        return   # hist 未推进:目标不可知,禁猜零写(结构性不可达,防御性保留)
    _write_derived_node_type(
        gs, 'boss', target_ord=int(hist),
        actor='CwScreenBossBriefing',
        trigger_screen=SCREEN_BOSS_BRIEFING, seq=gs.write_seq + 1)
