"""货币战争 MCP 手动游玩动作 op(纯动作抽取;供 MCP agent 直调)。

本包 = 动作 op 的**纯动作部分**(机械一段:点击/拖拽,零读屏零判效零决策),
构造参数只用 JSON 直传简单类型(MCP 可运行单元契约,od-dev-write-operation §5.0)。
与 ``cw_op/`` 域耦合动作 op(领域 param + env,服务 CwLoop 决策循环)的分界:
本包消费方 = MCP agent(analyze_screen extras 读数 → 本包 op 执行 → 再观察对账),
不读状态容器、不接策略器、不写上报。

机械发出零判效(用户裁定,同 cw_op 动作层):点击后不验证像素,落地事实归
调用方下一帧 analyze_screen 对账。
"""
