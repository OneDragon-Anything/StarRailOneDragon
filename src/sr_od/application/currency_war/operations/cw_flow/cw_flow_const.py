"""货币战争 开局序列 / overlay 族 op 完成承诺常量(DD-011 形态①固定时长)。

单一源声明:本模块只承载 cw_flow 新 op 的完成承诺时长;商店开/收动画等既有
DD-011 常量仍在 ``prep_actions``(SHOP_CLOSE_ANIM_S / SHOP_OPEN_ANIM_S)。
值依据均为用户口述时序(docs/game/currency_war/research/screen_flow_timing.md),
待实机校准时只改这里。
"""
from __future__ import annotations

#: 简报:点「下一步」离锚(简报标识消失,BriefingOp 出口已验)后的固定时长
#: (W971 01-opening §1,#1 口述「锚出现后 ~1s 动画完结」)。
BRIEFING_SETTLE_S: float = 1.0

#: 备战触发型 overlay 族(盛会之星/列车同行/武装箱/祈愿/策划/命运/秘典)确认后
#: 固定等待(W971 06-overlays §4/§5:关闭速度都快,固定 1.0s 交回循环)。
CW_OVERLAY_SETTLE_S: float = 1.0

#: 1-1 开局动画等待上界(用户口径 ~10s,待校准;W971 01-opening §2:
#: 开局补给动画长且无结束标志,超时 = 异常,留证交循环)。
ONE_ONE_MAX_WAIT_S: float = 10.0

#: 1-1 备战锚轮询间隔(「备战阶段」文本为主判据,round_wait 重跑当前节点)。
ONE_ONE_POLL_INTERVAL_S: float = 1.0
