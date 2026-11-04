"""动作后果声明 WorldDecl(kernel 纯数据件;零依赖)。

声明化动机(一句话):「动作落地 → 状态副本后果」的知识原散落在动作注册表
``terminal`` 属性、转移事件封闭集、SimBackend 分派表三处,新增转移动作
须同步三处、漏一即漂移;本件把后果收敛为上报函数自产的数据——动作 op
经 ``cw_sim_ports.declare_world`` 喂入 sim 后端驱动状态副本推进,实机侧
(端口未装 = no-op)作 journal 预期画面记账料,禁作判效断言。

设计依据 = 动作后果声明化迭代总纲 ``design.md`` §1/§2.2 与详设
``details/world-decl.md``(迭代收尾后契约归宿 = sim 权威版本
``sim-design.md`` §6.3);本模块只放 schema,零 import 零机制——
``trigger`` 封闭集的代码单一源 = ``sim/cw_sim_backend`` 的 advance
分派表键集,构造点校验不在本件(与上报函数纯函数纪律同向:零机制)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorldDecl:
    """动作后果声明(上报函数构造;消费面见详设 §4)。"""

    #: 动作后确定的下一画面 screen_info 档名;'' = 无画面(局终等未建模终态)。
    next_screen: str
    #: 推进分派类别(advance 分派表);'' = 无。
    trigger: str
    #: 动作参数槽位载荷(缺省空 = 无载荷)。坐标系 = 动作参数类 slots 同源
    #: (投资逐卡刷新 = 投资界面卡槽物理排位 0 基,CwActionRefreshInvestCardsParam
    #: 同款);取值时机 = 生成期快照(上报函数自 param 透传,状态副本消费端现读)。
    #: 写入端 = 上报函数(报告 param.slots 原样)。仅参数化动作携带,
    #: 转移类动作缺省空(消费端按 trigger 判载荷必要性)。
    slots: tuple[int, ...] = ()
