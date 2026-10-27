# 转型域换人通道统一设计 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（L1 快速集 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；commit 前 L3 全量 `uv run pytest sr-od-test/ -m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面；
- 策略批 prereg 完整性硬门：逐条对照本文件「prereg 实体清单」证明保全（保不住 = 设计缺陷非胜利，回设计层）。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节 + strategy-work 硬门。

## prereg 实体清单（受本迭代影响的已登记验收线；状态以各载体现读为准，实现批开盘先逐条核状态）

| 线 | 登记载体 | 与本迭代关系 | 保全/对照义务 |
|---|---|---|---|
| P89 预注册行为线（R1-R4 SellDeployed ≥0.75 次/轮 + 末轮保留率带内占比） | `proofs/math_proofs.md` P89 行约束段 | **直接受影响**（换人判据即本批改动对象） | 修后 sim 批对照读数并归因（判据改 = 行为面预期变化，对照≠达标裁决；A/B 无裁决权） |
| 02 §8 命题 A 判前锁预期（零动作轮<5%、SellBench≥200 笔、成型率≥80% 等） | `strategy-docs/02_mandate_layer.md` §8（命题 A 载体节） | 换人面直接受影响 | 修后 sim 批对照读数并归因 |
| 升级触发统一批 sim 基线（升级发射帧=0、资金门 defer=0 等） | `strategy-docs/11_shop_decisions.md` 新基线记录行 | 升级面不碰，声明不受影响 | 复测批零漂移核对（同 seed 基线帧位） |
| FM-1 死亡形态对照（死时金≥50、四联完整死型=0） | `strategy-docs/11_shop_decisions.md` FM-1 对照读数 | 经济面间接（来金资格排除可能减少卖出收入） | 复测批对照读数，偏离归因 |
| T-115 经济纪律（三不状态=最差持有） | 历史迭代 dag 裁定（git 历史可溯） | 不受影响声明 | 不核对行为，仅声明 |
- 盘点义务：实现批开盘按 strategy-work §6 盘点入口（当期迭代 criteria 行 + ADR 判据节 + batch_stats 读数行）穷尽补全本清单，禁只保上表。

## 3.1 转型域双门 + 守恒/判别子域切分 + 组算法（kernel 核判据层）

**范围**：`kernel/cw_deploy_logic.py`——转型域判别子新增（`locked_comp` 腿①显式排除 p1_pair 腿②，design §2.0）；触发完成品分支**收窄至双轨域保留**、锁定域由 `bond_gate_swap_ins`/`bond_gate_victim_yields` 双门接管（design §2.2/§2.11 行为差申报①）；守恒判定转型域切至终局档位非降、双轨域 `engines_guard` 原样（design §2.3）；**现行转型分支机器 0534 转型域退役**（`SWAP_TRANSITION_ARM_ENABLED`/`_swap_transition_domain`/五消费位键集收窄/快照——design §2.3.1）；`target_keep` 转型域口径收窄（design §2.2.1，`cw_launch_admission.py` 谓词 + 让位消费面）；**最小充分组贪心算法宿主**（kernel `select_swap_plan` 多对计划形态，design §2.7——含两级 victim 序与换入侧裁判权对接）；档位语义源切分（form_tiers=成型判据/键集，cw_factions=档位梯，design §2.1）。不含放行接线（3.2）、来金资格（3.3）、P61 清理（3.4）、复测（3.5）。
**设计依据**：design.md §2.0–§2.4、§2.2.1、§2.7
**文件面**：`src/sr_od/application/currency_war/kernel/cw_deploy_logic.py`、`src/sr_od/application/currency_war/kernel/cw_launch_admission.py`；`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 单帧测试覆盖枚举表 A/A′/B/C/D/E/F 全情形（design §2.2，锚数值按 §2.1 档位梯直调）；
- 双轨域零行为差回归（完成品分支/必需件分支/守恒照旧—— untouched 面 grep 证明零改动面）；
- 锁定帧行为差申报①的覆盖性测试（现行完成品换入动作在双门下仍发出的同动作对照，design §2.11）；
- target_keep 口径收窄的单帧测试（标签过渡件可入 victim 池、名单成员仍恒拒）；
- 0534 转型域退役面测试（转型域双门接管、双轨域分支照旧）；
- 组算法测试（两级 victim 序锚帧复验：Saber 换青雀；超员降级；无可行组零动作稳态）；
- 断言写语义，docstring 引 design 节锚；
- 既有换人测试全量一次通过（L1）；语义被取代的旧断言按测试纪律改写（引本设计，禁机械跟绿）；
- 常规检查（本文件首节）。
**验收凭据形式**：单帧测试名清单 + L1 通过记录 + 双轨零行为差对照 + 锁定帧行为差对照

## 3.2 放行层复算接线 + 策略层消费对账

**范围**：组计划消费接线（kernel 计划 → 策略层动作发射）与同帧逐对原子序执行形态（含中途失败语义与下帧竞速申报落地，design §2.7）；P79-3 三轴废弃改复算统一门（design §2.5）；`post_sell_req_missing` 底线与窗口豁免/外部件不受辖核对（design §2.6）；`flow/action_exec.md` 帧稳定契约对账申报。
**设计依据**：design.md §2.5–§2.7
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`、`entry.py`（及测试）；`docs/develop/sr_od/application/currency_war/flow/action_exec.md` 契约对账记录（如需修订入正本清单）
**依赖**：3.1
**优先级建议**：7
**完成判据**：接线核对清单逐项过（每项带 design 节锚 + 代码符号锚）；组算法单帧测试（含超员降级、无可行组零动作稳态）；受影响测试过；常规检查。
**验收凭据形式**：核对清单 + 测试记录

## 3.3 演进/来金资格增补 + 收敛不变式测试

**范围**：演进降级换人 victim 资格增补排除「终局档位承载件」（design §2.8）；**来金族出售候选池资格增补排除「离场使终局档位下降的支撑件」**（节末凑息/升级凑金/会话内筹资——design §2.8，现行羁绊贡献仅为排序项非资格排除，需新增资格面）；支撑数全局单调不变式的测试固化（含终局件受保护、外部支撑件经排除后不可卖两条回归锚）。
**设计依据**：design.md §2.8
**文件面**：`src/sr_od/application/currency_war/kernel/cw_deploy_logic.py`（演进分支）；`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`、`sell_gate.py`（来金资格面）；`sr-od-test` 对应测试
**依赖**：3.1
**优先级建议**：5
**完成判据**：两类排除谓词的单帧测试 + 不变式回归测试过（含「凑息帧遇终局档位承载件→不入选」语义断言）；常规检查。
**验收凭据形式**：测试名清单 + 通过记录

## 3.4 P61 退役与全仓引用清理

**范围**：删 `proofs/p61-bt-swap-arm-dominance.md`、`proofs/math_proofs.md` P61 行；全仓 grep（`P61`/`p61`/`B_t`/`SWAP_TRANSITION_ARM_ENABLED`/`_swap_transition_domain`）穷尽清点、逐位点核语义改写；18 号篇同号异命题禁改核对；B_t 存续消费点单一源关系处置（design §2.9）；0534 退役引用面随本阶段（design §2.3.1）；删除不留残迹。
**设计依据**：design.md §2.9
**文件面**：`docs/develop/sr_od/application/currency_war/proofs/**`、`docs/develop/sr_od/application/currency_war/strategy-docs/` 引用行（`14_p1_consume_arms.md` 等）、出口生存余量篇、src 注释引用行（`kernel/cw_launch_admission.py`、`kernel/cw_deploy_logic.py`、`strategies/impl/mandate_v1/mandate.py`、`flow.py`、telemetry schema 等 grep 命中面）
**依赖**：3.1
**优先级建议**：4
**完成判据**：位点穷尽核对（改写点逐一对、残留点 grep 为零，双向）；18 号篇 P61 原样核对；常规检查。
**验收凭据形式**：grep 输出对照（改前/改后）+ 位点清单

## 3.5 同 seed 复测与行为验证

**范围**：`cw_sim_match_drive.py --seed 20261216` 复跑；跑前先写 2-1..2-4 预测动作表（判读锚点事前写），跑后逐帧对照：锚 ①2-1 换人发生（Saber 换爻光或青雀 1 换 1，圣杯 3 二阶与能量 3 一阶激活）②后续帧对照组算法推演；prereg 实体清单逐条对照；复测报告落批目录。
**设计依据**：design.md §2.10
**文件面**：`.debug/currency_war/telemetry/sim/`（产出，不提交）；报告文件
**依赖**：3.1、3.2、3.3
**优先级建议**：5
**完成判据**：预测表逐帧对照完成（偏离有归因结论）；prereg 清单逐条过；常规检查（提交面 = 报告与账本，代码零改动）。
**验收凭据形式**：复测报告（journal 行锚摘录）+ prereg 对照表

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1–3.5 全部
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单（粒度与阶段文件面对齐）

**正本文档**（路径相对 `docs/develop/sr_od/application/currency_war/`）：
- strategy-docs/24_deploy_segment.md：换人节全面重写（双门/组算法/守恒域切分） ← 3.1/3.2
- strategy-docs/02_mandate_layer.md：§7 sell 行、M1 行判据指针 ← 3.1
- strategy-docs/10_prep_decisions.md：§1 部署判据的守恒/换人引用核对 ← 3.1
- strategy-docs/22_prep_screen.md：§1 部署步窗口表述核对（第 6 步） ← 3.2
- strategy-docs/14_p1_consume_arms.md：P61 引用行改写（:385/:602） ← 3.4
- proofs/math_proofs.md：P61 行删除 ← 3.4
- proofs/p63-bt-depth-prediction-lower-bound.md、proofs/p87-bt-depth-correlation.md、proofs/p88.md、proofs/p89.md：P61/B_t 交叉引用改写 ← 3.4
- proofs/出口生存余量篇：P61 引用改写 ← 3.4
- strategy-docs/17_stall_form_spend_authority.md：换人域措辞核对 ← 末阶段
- screens/README.md、screens/deploy.md：换人判定单一源表述核对 ← 末阶段
- flow/projection_contract.md：换人臂节语义核对 ← 末阶段
- flow/action_exec.md：同帧逐对原子序契约对账/修订 ← 3.2

**代码注释引用面（随所属阶段提交，非正本文档）**：
- kernel/cw_launch_admission.py：收敛注释改写 ← 3.4
- 其余 grep 命中的 src 注释面（flow.py、telemetry schema 等） ← 3.4
