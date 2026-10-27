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
| 升级触发统一批 sim 基线（升级发射帧=0、资金门 defer=0 等） | `strategy-docs/11_shop_decisions.md` 新基线记录行 | **凑金可达性输入面受 3.3 排除影响，基线可能漂移** | 复测批对照读数，漂移如实申报并归因（对齐 FM-1 行申报姿态，禁虚假保全声明） |
| FM-1 死亡形态对照（死时金≥50、四联完整死型=0） | `strategy-docs/11_shop_decisions.md` FM-1 对照读数 | 经济面间接（来金资格排除可能减少卖出收入） | 复测批对照读数，偏离归因 |
| T-115 经济纪律（三不状态=最差持有） | 用户裁定（2026-09-07，裁定实质亲验在案） | 不受影响声明 | 不核对行为，仅声明 |
- 盘点义务：实现批开盘按 strategy-work §6 盘点入口（当期迭代 criteria 行 + ADR 判据节 + batch_stats 读数行）穷尽补全本清单，禁只保上表。

## 3.1 转型域双门（四腿）+ 判别子三合取 + 守恒/域切分 + 组算法（kernel 核判据层）

**范围**：`kernel/cw_deploy_logic.py`——转型域判别子新增三合取（锁定线槽腿①排除 p1_pair 腿② ∧ 板满继承 ∧ fp<1.00 继承，design §2.0）；触发门 1 扩四腿（①新档 ②支撑数增 ③升星横换 ④成品腿 fp✗→✓，design §2.2）、完成品分支**收窄至双轨域保留**、转型域由双门接管（design §2.3/§2.11 申报①）；守恒判定转型域切至终局档位非降、双轨域 `engines_guard` 原样（design §2.3）；**现行转型分支机器退役**（`SWAP_TRANSITION_ARM_ENABLED`/`_swap_transition_domain`/五消费位键集收窄/快照——design §2.3.1，**pair 帧 fenced off-target 路径保持现行**，design §2.11 申报④）；`target_keep` 转型域口径收窄 + 让位白名单（design §2.2.1，`cw_launch_admission.py` 谓词 + 让位消费面；名单成员两让位通道：同名升星 3(a) / 分支 hold 3(b) 含量席让位保留）；**最小充分组贪心算法宿主**（kernel `select_swap_plan` 多对计划形态为本迭代新建，design §2.7——两级 victim 序、换入侧裁判权对接、无新增 admission 闸）；**up 侧 target 视图口径切名单**（design §2.7，三消费位）；**arm 分键新键族**（`bond_gate_*` 四键 + victim 序来源键，`cw4_m1p_arm_pending` 载体保留，design §2.3.1）；档位语义源切分（form_tiers=成型判据/键集/④判据，cw_factions=档位梯，design §2.1）。不含放行接线（3.2）、来金资格（3.3）、P61 清理（3.4）、复测（3.5）。
**设计依据**：design.md §2.0–§2.4、§2.2.1、§2.7、§2.11
**文件面**：`src/sr_od/application/currency_war/kernel/cw_deploy_logic.py`、`src/sr_od/application/currency_war/kernel/cw_launch_admission.py`、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`（bond_gate_* 分键写点）、`src/sr_od/application/currency_war/strategies/impl/mandate_v1/deploy_plan.py`（up 侧消费位之一；另两处消费位在 cw_deploy_logic.py）；`sr-od-test` 对应测试
**依赖**：无
**优先级建议**：8
**完成判据**：
- 单帧测试覆盖枚举表 A/A′/B/C/D/G/E/F 全情形（design §2.2，锚数值按 §2.1 档位梯直调）；
- **门 1③ 谓词钉死测试**：同名必要（异名星级升换拒绝）+ 名单让位全序末位语义；
- **OR 承接阵容专项**：希儿量子静态套完成品换入经门 1④ 放行（design §2.11 申报①覆盖性论证的行为测试）；
- **名单成员让位通道专项**：同名升星让位（3(a)）放行 + 量席让位现行语义保留（3(b)）回归；
- 双轨域零行为差回归（完成品分支/必需件分支/守恒照旧）+ pair 帧 fenced off-target 路径保持现行（申报④，fenced 关门分支判定迁移到转型域判别子）；
- **`evolution_swap_arm_trigger` 域腿对账**（design §2.3.1，禁静默分叉）；
- 转型域判别子三合取单帧测试（腿①排除配方锁帧、板满与 fp<1.00 继承语义）；
- target_keep 口径收窄的单帧测试（标签过渡件可入 victim 池、名单成员仅两通道让位）；
- 转型分支退役面测试（转型域双门接管、双轨域分支照旧）+ arm 分键新键族写入断言；
- 组算法测试（两级 victim 序锚帧复验：Saber 换爻光；超员降级；无可行组零动作稳态）；
- 断言写语义，docstring 引 design 节锚；
- 既有换人测试全量一次通过（L1）；语义被取代的旧断言按测试纪律改写（引本设计，禁机械跟绿）；
- 常规检查（本文件首节）。
**验收凭据形式**：单帧测试名清单 + L1 通过记录 + 双轨零行为差对照 + 转型域行为差对照（申报①–⑥逐项）

## 3.2 放行层复算接线 + 策略层消费对账

**范围**：组计划消费接线（kernel 计划 → 策略层动作发射）与同帧逐对原子序执行形态（含中途失败语义与下帧竞速申报落地，design §2.7）；P79-3 三轴废弃改复算统一门（design §2.5，复算语义钉死：发射帧现读板态按计划组重算门 1、通过即放行、分叉撤计划）；`post_sell_req_missing` 底线与窗口豁免/外部件不受辖核对（design §2.6）；计划发射不新增 admission 闸核对（观测面照常记录，design §2.7）；`flow/action_exec.md` 帧稳定契约对账申报。
**设计依据**：design.md §2.5–§2.7
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py`、`entry.py`（及测试）；`docs/develop/sr_od/application/currency_war/flow/action_exec.md` 契约对账记录（如需修订入正本清单）
**依赖**：3.1
**优先级建议**：7
**完成判据**：接线核对清单逐项过（每项带 design 节锚 + 代码符号锚）；同帧逐对原子序与失败语义落地核对（中途失败停发/下帧重算）；受影响测试过；常规检查。
**验收凭据形式**：核对清单 + 测试记录

## 3.3 演进/来金资格增补 + 收敛不变式测试

**范围**：演进降级换人 victim 资格增补排除「**终局键集标签命中件**」（design §2.8）；**来金族出售候选池资格增补排除「终局键集标签命中件」**（不限已承载档位件——design §2.8，现行羁绊贡献仅为排序项、`is_field_irrelevant_unit` 仅覆盖有档件，真实泄露 = 无档标签件）；**排除落点 = 卖出资格装配 A 身份段（`sell_gate.identity_exclusions`）**；支撑数全局单调不变式的测试固化（含「板上标签命中件不可经卖出通道离场」「bench 侧标签件仍可来金卖出」两条边界锚）。
**设计依据**：design.md §2.8
**文件面**：`src/sr_od/application/currency_war/kernel/cw_deploy_logic.py`（演进分支）；`src/sr_od/application/currency_war/strategies/impl/mandate_v1/criteria/sell_candidates.py`、`sell_gate.py`（来金资格面 + 装配 A 身份段）；`sr-od-test` 对应测试
**依赖**：3.1
**优先级建议**：5
**完成判据**：标签命中排除谓词的单帧测试（有档/无档标签件都拒、**bench 侧标签件同样拒**、纯过渡件放行）+ 不变式回归测试过（「板上标签命中件不可经卖出通道离场」边界锚）；常规检查。
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

**范围**：`cw_sim_match_drive.py --seed 20261216` 复跑；跑前先写 2-1..2-4 预测动作表（判读锚点事前写），跑后逐帧对照：锚 ①2-1 换人发生（**Saber 换爻光**，1 换 1，两级序+贡献度量唯一推导，圣杯 3 二阶与能量 3 一阶激活）②后续帧对照组算法推演；prereg 实体清单逐条对照；复测报告落批目录。
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
- strategy-docs/24_deploy_segment.md：换人节全面重写（双门四腿/组算法/守恒域切分），并顺手钉正其引「22 §1 第 5 步」漂移（实际第 6 步） ← 3.1
- strategy-docs/02_mandate_layer.md：§7 sell 行、M1 行判据指针 ← 3.1
- strategy-docs/10_prep_decisions.md：§1 部署判据的守恒/换人引用核对 ← 3.1
- strategy-docs/22_prep_screen.md：§1 部署步窗口表述核对（第 6 步） ← 3.2
- strategy-docs/14_p1_consume_arms.md：:602 P61 引用行改写；:385 B_t 面随 §2.9 迁移核对 ← 3.4
- proofs/math_proofs.md：P61 行删除、P87 行（:108）P61 先例引用改写、P78 行（:100）随装配 A 构成变化改写 ← 3.4
- proofs/p63-bt-depth-prediction-lower-bound.md、proofs/p87-seele-form-port-or-nesting.md、proofs/p88.md、proofs/p89.md：P61/B_t 交叉引用改写 ← 3.4
- proofs/出口生存余量设计批-命题与因果链.md：P61 引用改写 ← 3.4
- strategy-docs/11_shop_decisions.md：§4.0 卖出候选评估器资格面随装配 A 构成变化改写 ← 3.3
- strategy-docs/17_stall_form_spend_authority.md：换人域措辞核对 ← 末阶段
- screens/README.md、screens/deploy.md：换人判定单一源表述核对 ← 末阶段
- flow/projection_contract.md：换人臂节语义核对 ← 末阶段
- flow/action_exec.md：同帧逐对原子序契约对账/修订 ← 3.2

**代码注释引用面（随所属阶段提交，非正本文档）**：
- kernel/cw_launch_admission.py：收敛注释改写 ← 3.4
- 其余 grep 命中的 src 注释面（flow.py、telemetry schema 等） ← 3.4
