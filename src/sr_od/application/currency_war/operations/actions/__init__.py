"""货币战争公用底层动作原语(简单参数、单一动作、零决策;flow 层与 MCP agent 共用)。

本包 = 动作 op 的**纯动作部分**(机械一段:点击/拖拽,零读屏零判效零决策),
构造参数只用 JSON 直传简单类型(MCP 可运行单元契约,od-dev-write-operation §5.0)。
与 ``cw_op/`` 域耦合动作 op(领域 param + env,服务 CwLoop 决策循环)的分界:
本包参数为简单类型、决策一律不进本包(决策在 flow 层编排或调用方 agent)。

消费方(两条路共用同一动作原语):
- flow 层(一条龙脚本):cw_loop/编排 op 组合本包动作;
- MCP agent:analyze_screen extras 读数 → 本包 op 执行 → 再观察对账。

机械发出零判效(用户裁定,同 cw_op 动作层):点击后不验证像素,落地事实归
调用方下一帧 analyze_screen 对账。
"""
