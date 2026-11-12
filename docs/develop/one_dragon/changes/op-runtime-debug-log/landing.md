# op-runtime-debug-log 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（`$env:PYTHONPATH="src"` 前置）;
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集；**测试面现状**：sr-od-test 无 screen_utils 识别链路与 operation 主循环的既有覆盖，各阶段以新增烟囱测试（见判据）+ 人工日志样例对照为验收主体）;
- 提交:逐文件点名 `git add`（禁 `-A`/目录级）,commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 screen_utils 识别层日志（A/B/I 组）

**范围**：A1/A2（get_match_screen_name / from_last 判定序收集 + 口径按 design §2.1 A）、B1/B1a/B2（find_area / find_area_binary / find_area_in_screen / find_area_in_screen_binary / find_and_click_area，binary 系格式与主路径一致）、`find_area_in_screen(_binary)` 加可选 screen_name 参数 + `is_target_screen` 透传 screen_info.screen_name、I 组 update_current_screen_name 加 source 参数。边界——不含 operation.py；不改 tl_as_team_recognizer / cw_observation 两业务文件（日志退化 area_name）。
**设计依据**：design.md §2.1 A/B/I、§2.4。
**文件面**：`src/one_dragon/base/screen/screen_utils.py`；update_current_screen_name 所在的 screen_loader 模块文件；`sr-od-test/test/one_dragon/base/screen/`（新增烟囱测试文件）。
**依赖**：无。
**优先级建议**：9。
**完成判据**：
- 每个日志点按 design.md §2.1 格式落位（含 binary 系与 B 组两式的行序示例），级别 debug；
- `find_area_in_screen(screen_name=None)` 旧调用方式行为不变、日志退化 area_name；`update_current_screen_name(source=None)` 兼容既有调用；
- 烟囱测试：fixture_controller 或 mock 画面驱动 find_area 路径，caplog 断言 B1a 触发且返回值与改动前一致（行为零变化 + 日志行为双锁）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：日志样例对照（design 格式逐条）；烟囱测试通过输出。

## 3.2 operation 运行层日志（C/D/F/H 组 + I 调用位）

**范围**：C1（until 逐锚行按实际验证集 + 总结论行，break 语义按 design §2.1 C）、D2/D3（INFO 行尾缀，D3=递增后值）、F2（goto 路由）、I 组四个调用位传 source、删 1473 行重复 debug。边界——不含 screen_utils.py。（原 H1 失败自动存图经用户裁定移除：部分 op 允许失败为合法出口，逐失败存图成噪声。）
**设计依据**：design.md §2.1 C/D/F/H/I。
**文件面**：`src/one_dragon/base/operation/operation.py`。
**依赖**：3.1（I 组参数先行；联调同批验证）。
**优先级建议**：9。
**完成判据**：
- 各日志点按 §2.1 格式与定义落位（until 行序、retry 口径、H1 插入点三处拍板均已由设计给定）；
- INFO 行语义不变（仅尾缀追加）；save_screenshot 无 last_screenshot 时不炸（复用现有守卫）；
- 跑一个现有 op（如 run_operation read_warp_status）实测一轮，日志含完整决策链（画面判定→识别→点击→until→节点流转）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：日志样例对照 + 实测一轮日志摘录。

## 3.3 MCP server debug 链路核实 + 实测指引 + ZZZ 同步

**范围**：核实 MCP server 启动链路是否必经 `context.init()`（is_debug→set_log_level 联动生效点，design §2.3）；若否，在 server 入口补一次 set_log_level；写实测期开 debug 的操作指引（供 skill od-dev-write-operation ⑥ 实测章引用）；写 SR→ZZZ 同步文件。
**设计依据**：design.md §2.3。
**文件面**：`tools/mcp/` 启动脚本（核实后定；若需补 set_log_level 则为其入口文件）；`.debug/temp/skill_feedback.md`（追加：skill ⑥ 实测章应写 debug 开启指引）；`.debug/temp/zzz/<日期-debug日志>.md`（不入库）。
**依赖**：3.1、3.2。
**优先级建议**：7。
**完成判据**：
- 「实测期开 debug」有可执行路径（配置项名 + 生效链路写明，或入口补调用）；
- skill 反馈与 ZZZ 同步文件落盘。
**验收凭据形式**：开启操作步骤文 + 两文件存在。

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- docs/develop/one_dragon/ 下运行链路相关正本文档 → 补 debug 日志点与开启方式说明（若无可挂靠正本则本条登记为「新建 runtime-observability.md 正本」再清零——9 点 + overlay 边界值得一份正本）。
- 技术债指针（正本内登记，不在本迭代实施）：识别逻辑三套并行实现的合并重构；log 与 overlay 统一运行事件模型。
