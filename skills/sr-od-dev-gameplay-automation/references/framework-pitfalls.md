# 框架级踩坑(遇过就记,反复发作)

> 本文件是 SKILL.md「框架级踩坑」的 situational 参考清单。遇 op 点不中/行为怪先查这里。这些是框架地基级行为(整个框架靠它,改名 = 重写),写全名便于全局搜。

1. **`before_screenshot` 会移鼠标 → 吞掉紧接的 click(bug #1)**:框架每个 op 轮次开始自动截图,截图前把鼠标移到角落;紧接的 `controller.click` 被游戏判成"拖拽"而落空。**症状:同坐标 op 点不中、手动 `click_game` 一发即中**。缓解:关键 click 前 `active_window()` + `sleep(0.5)` 让鼠标 settle,且 click 之间不要再截图。
2. **MCP click/key 异步**:`click_game` / `key_tap` 立即返回但 ~1s 后才落地;`analyze_screen` 前必须 `sleep ~1.5s`,否则截到点击前画面 + 乱导航。
3. **OCR 关键词选画面独有的 LCS 坑**:见 `screen-identification.md` §中文关键词 LCS 误匹配。
4. **ONNX session 异步调用走 `gpu_executor.submit`**,别并发直调多个 session。
5. **配置生效**:server 启动时把配置(当前实例/账号/各 yml)读进内存缓存,运行时不再重读文件。故 GUI 改配置、手改 yml、改 op 代码,server 都不自动跟随 —— 经 daemon 重启 server(`restart_sr_od_mcp_server`)即生效(客户端**无需**重连)。只有改 MCP 自身元信息(instructions/tool 描述/增减 method)才需客户端 /mcp 重连。
6. **录屏走 MCP 后端**(`record_screen`,Session 1),别从服务会话(Session 0)Bash 起 ffmpeg(BitBlt 录不到交互桌面)。
7. **MCP server 日志默认 GBK → mojibake 不可读**:daemon 用 `subprocess.Popen(stdout=log_file)` 启 server,server 的 Python stdout 用 Windows locale(GBK)写 → 进 UTF-8 文件变乱码(op 名/OCR 全 mojibake,无法日志诊断)。修:**MCP server 入口起手** `sys.stdout/stderr.reconfigure(encoding='utf-8')`。验证:`.debug/sr_od_mcp/main_server.log` 按 utf-8 能解码 + Read 工具显示正常中文。日志不可读 = 无法用「读日志」方法论诊断,优先修。
