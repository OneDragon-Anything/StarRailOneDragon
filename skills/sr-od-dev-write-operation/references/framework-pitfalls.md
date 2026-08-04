# 框架级踩坑(op 作者视角,reference)

> `sr-od-dev-write-operation` 的 situational reference。这些是 op 里反复发作的框架行为,遇过就守。SKILL.md 列了最频发的;本文件给完整 + 缓解。

## 1. bug#1:`before_screenshot` 移鼠标 → 吞掉紧接的 click

框架每个 op 轮次开始(`_execute_one_round` 进节点前,若 `screenshot_before_round=True`)自动 `self.screenshot()`,截图前把鼠标移到角落;紧接的 `controller.click`(从角落到目标)被游戏判成**拖拽** → click **落空**(不 register)。

**症状**:op 里某坐标点不中;手动 `click_game` 同坐标一发即中(手动无前置截图)。

**缓解(按场景)**:
- **关键 click 前 `mouse_move(target)` 再 `click(target)`**:`mouse_move` 是纯移动不触发拖拽判断 → 鼠标已到目标 → `click` 零移动 → 不被判拖拽 → 必落。这是通用修复模式。
- **click 之间别再截图**:截图会再次移鼠标,把上一个 click 的鼠标到位状态打掉。
- **active_window 紧贴 click,别留间隙**:`round_by_ocr_and_click` 有 `pre_delay=0.3`(点击前等);若节点起手 `active_window()` 再走 helper,active_window 到 click 间有 0.3s+ 间隙,游戏窗口可能在此间隙失焦 → click 落空。需焦点时 `active_window` 紧贴 `controller.click`,无 pre_delay 间隙。

## 2. MCP click / key 异步

`click_game` / `key_tap` 立即返回,但 ~1s 后才落地。操作后**必须 `sleep`(~1.5s)再读屏验证**,否则截到点击前画面 → 误判还在原画面 → 乱导航 / 乱重试。坐标用 screen_info 精确值,别凭目测。

## 3. ONNX session 异步走 `gpu_executor`

OCR / 检测等 ONNX session 的异步调用必须经 `one_dragon.utils.gpu_executor.submit`,**别并发直调多个 session**(撞 GPU 资源 / 报错)。

## 4. 配置改了不自动生效

MCP server 启动时把配置(当前实例 / 账号 / 各 yml)读进内存缓存,运行时不再重读文件。故 **GUI 改配置 / 手改 yml / 改 op 代码,server 都不自动跟随** —— 经 daemon 重启 server(`restart_sr_od_mcp_server`)即生效(客户端**无需**重连)。只有改 MCP 自身元信息(instructions / tool 描述 / 增减 method)才需客户端 `/mcp` 重连。遇"改了配置 / 代码但行为没变",先想这条。

## 5. 录屏走 MCP 后端

录 bot 实战用 `record_screen` MCP tool(Session 1 后端,observe 不占跑道,可与 bot run 并行)。**别从服务会话(Session 0)Bash 起 ffmpeg** —— BitBlt 录不到交互桌面。`mode='start'` → 跑 bot → `mode='stop'`。

## 6. server 日志默认 GBK → mojibake 不可读

server 的 Python stdout 用 Windows locale(GBK)写 → 进 UTF-8 文件变乱码(op 名 / OCR 全 mojibake,无法"读日志"诊断)。server 入口(`sr_od/backend/entry/server.py`)起手 `sys.stdout/stderr.reconfigure(encoding='utf-8')`。日志不可读 = 无法用"读日志"方法论,优先修。验证:`.debug/sr_od_mcp/main_server.log` 按 utf-8 能解码 + Read 工具显示正常中文。
