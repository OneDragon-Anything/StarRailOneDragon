# 单个 Operation 的测试(reference)

> `sr-od-dev-write-operation` 的 situational reference。测试**策略**在 SKILL.md / `sr-od-dev-gameplay-automation`,本文件给 op 级测试**机制**。

## 实机单跑(最快定位)

写完一个 op,先用 MCP 后台单跑它,确认这一步行为对,再接入主流程:

```
run_operation(op_id='<module>.<ClassName>', args={...}, block=false)
```
- `op_id` = `<dotted module path>.<ClassName>`(可从 `list_operations` 取)。
- `block=false` 立即返回,`get_run_status` 查进度(实现-测试流水线:后台跑前一个 op,等待时写下个)。
- 单跑道:同时只能一个 op 在跑,别并发。

## 单元测试:mock 截图 + 断言

op 的单元测试在 `sr-od-test/`(独立测试仓库,放仓库根目录)。**看现有 op 测试抄测试骨架**,别从零搭。核心模式:

- **注入 mock 截图**:op 每轮 `self.screenshot()` 实际由测试喂 fixture 图(项目用 mock 截图注入 helper,如 `add_mock_screenshot`,喂**序列**fixture 模拟跨多屏推进)。跨多屏的流程 op 喂序列;单画面 op 喂一张。
- **断言客观输出**:节点流转(走到哪个节点)、OCR 结果、检测函数返回值、决策函数选了哪个。**别断言不可观测的运行时副作用**(click 是否真落地 / 时序)。

## TDD vs 刻画测试(分情况)

- **新写纯逻辑**(reader / OCR 解析 / 决策函数):**先写 fixture 测试断言期望输出,再实现**(TDD)。改前跑、改后跑,锁回归。
- **改存量 op**:先补**刻画测试**(用真实截图 fixture 锁当前行为)→ 改 → 重跑 → 无回归才提交。
- **每个画面状态 1-2 张典型 fixture**:别凭一两种状态写整个流程;漏状态 = 回归。改 reader / 解析前把所有相关状态 fixture 跑一遍。

## TDD 锁得住什么、锁不住什么(关键)

- **锁得住**:**纯逻辑回归** —— 给定截图,检测对不对 / 该点哪 / 纯函数算对不对。
- **锁不住**:**运行时 bug** —— click 时序被 `before_screenshot` 吞(bug#1)、MCP 异步、真机 OCR 抖动。
- → **绿测试 ≠ 实机能跑**。单元测试过之后,仍要实机 `run_operation` 验(看 → 动 → 等 → 验)。别拿绿测试当"实机通了"的证据。

## 实机验证时

- 决策点开**临时日志 + debug 截图**(OCR 摘要 / 点击坐标 / 分支结果),一次实跑就能复盘每个决策点发生了什么。验证通过后逐步去掉(减运行时开销)。
- 失败先读 `.debug/sr_od_mcp/` 日志(实际 OCR / 节点流转 / 决策状态),别盲改。
