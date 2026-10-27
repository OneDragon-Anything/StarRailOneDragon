# 羁绊组换人判据 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（L1 快速集 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；commit 前 L3 全量 `uv run pytest sr-od-test/ -m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面；
- 策略批 prereg 完整性硬门：受本批影响的已登记验收线逐条列出并证明保全（strategy-work「对抗循环」节；保不住 = 设计缺陷非胜利，回设计层）。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节 + strategy-work 硬门。

## 3.1 门 1/门 2 判据实现

**范围**：`kernel/cw_deploy_logic.py` 换人触发与让位判据按 design §2.2/§2.3/§2.4 改造——`bond_gate_swap_ins`/`bond_gate_victim_yields` 替换完成品折法两处；必需件分支与演进降级分支保留；既有守卫零豁免。不含 P61 引用清理（3.3）与同 seed 复测（3.4）。
**设计依据**：design.md §2.1–§2.5
**文件面**：`src/sr_od/application/currency_war/kernel/cw_deploy_logic.py`；`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 单帧测试覆盖门 1①②③ 放行面与拒绝面（枚举 A/B/C/D 情形放行、E/F 情形拒绝，情形定义见 design §2.2/§2.8），断言写语义不写牌面，docstring 引 design 出处；
- 既有换人测试全量一次通过（L1 快速集）；语义被取代的旧断言按测试纪律改写（引本设计，禁机械跟绿）；
- 常规检查（本文件首节）。
**验收凭据形式**：新单帧测试名清单 + L1 通过记录

## 3.2 接线对账（窗口/原子序/底线）

**范围**：方向线成员窗口豁免、外部凑档件不受窗口辖、同帧逐对原子序、`post_sell_req_missing` 底线，逐项对照 design §2.3/§2.4 核实接线（含 `entry.py`/`mandate.py` 消费面符号锚）；波及测试同步。
**设计依据**：design.md §2.3–§2.5
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/entry.py`、`mandate.py`（及测试）
**依赖**：3.1
**优先级建议**：6
**完成判据**：接线核对清单逐项过（每项带 design 节锚 + 代码符号锚）；受影响测试过；常规检查。
**验收凭据形式**：核对清单 + 测试记录

## 3.3 P61 退役与引用清理

**范围**：删 `proofs/p61-bt-swap-arm-dominance.md`、`math_proofs.md` P61 行；全仓 grep（`p61`/`P61`/`B_t`）穷尽清点引用并改写（收敛角色接替 = design §2.6 注记）；禁留退役注记残迹（未证即停用通则：删除不留标记）。
**设计依据**：design.md §2.6
**文件面**：`docs/develop/sr_od/application/currency_war/proofs/**`、strategy-docs 引用行、src 注释引用行（含 `kernel/cw_launch_admission.py`）
**依赖**：3.1
**优先级建议**：4
**完成判据**：位点穷尽核对（改写点逐一对、残留点 grep 为零，双向）；常规检查。
**验收凭据形式**：grep 输出对照（改前/改后）

## 3.4 同 seed 复测与行为验证

**范围**：`cw_sim_match_drive.py --seed 20261216` 复跑；对照锚 = 2-1 至 2-4 换人/部署动作面（缺席→发生；Saber 换远坂凛 1 换 1；圣杯 2 不掉档、能量 2→3）；复测报告落批目录，结论回填账本。
**设计依据**：design.md §2.7
**文件面**：`.debug/currency_war/telemetry/sim/`（产出，不提交）；报告文件
**依赖**：3.1、3.2
**优先级建议**：5
**完成判据**：复测局换人动作面对照锚命中（或偏离有归因结论）；常规检查（提交面 = 报告与账本，代码零改动）。
**验收凭据形式**：复测报告（journal 行锚摘录）

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1–3.4 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- strategy-docs/24_deploy_segment.md：换人节判据语义重写 ← 3.1
- strategy-docs/02_mandate_layer.md：§7 sell 行与 M1 行判据指针同步 ← 3.1
- strategy-docs/math_proofs.md：P61 行删除 ← 3.3
- strategy-docs/14_p1_consume_arms.md：推迟上界行 P61 引用改写 ← 3.3
- strategy-docs/proofs/p88.md、proofs/p89.md：P61 交叉引用改写 ← 3.3
- kernel/cw_launch_admission.py：收敛注释改写 ← 3.3
- strategy-docs/17_stall_form_spend_authority.md：换人域措辞核对 ← 末阶段
- screens/README.md、screens/deploy.md：换人判定单一源表述核对 ← 末阶段
- flow/projection_contract.md：换人臂节语义核对 ← 末阶段
