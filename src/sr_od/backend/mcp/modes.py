"""MCP 运行模式常量与开发专属工具名单(单一源)。

独立成模块避免循环导入:``app.py``(注册入口)与 ``prompts.py``(guide 过滤)、
``entry/server.py``(启动参数)都依赖这些常量,而 ``app.py`` 与 ``prompts.py``
互相导入。

模式由启动参数决定(entry/server.py ``--mode``),进程级状态——切换需重启
server + MCP 客户端重连。设计文档:
docs/develop/sr_od/backend/changes/mcp-mode-split/design.md。
"""

MCP_MODE_PLAYER = 'player'
MCP_MODE_DEV = 'dev'

# 开发专属工具名单:玩家模式不暴露。
# 归属判据 = 「维护自动化产品」而非「完成游戏内容」;新维护类工具必须登记于此,
# 契约测试锁「dev 工具集 - player 工具集 == 本名单」防漂移。
# 新工具默认进玩家面(玩家面缺工具=玩家任务办不成,主路径优先)。
DEV_ONLY_TOOLS: frozenset[str] = frozenset({
    'create_screen',            # 画面建档写操作(识别资产维护)
    'upsert_screen_area',       # 同上
    'delete_screen_area',       # 同上
    'delete_screen',            # 同上
    'describe_operation_flow',  # op 节点流转图:改 op 的编排审查用;「用 op」的 list/describe/run 归玩家
    'record_screen',            # 录屏取证(dev 依赖 imageio-ffmpeg)
})
