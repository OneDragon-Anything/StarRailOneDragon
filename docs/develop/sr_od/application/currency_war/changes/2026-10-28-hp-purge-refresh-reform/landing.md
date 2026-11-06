# hp-purge-refresh-reform 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（L1 快速集 = `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；受影响域点名按阶段文件面定）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面；
- 删除阶段附加：删除面对应验收词表残留扫描清零——**扫描范围 = 符号级验收词全仓**（各详设词表逐符号唯一、无误捕风险）＋ 本阶段文件面结构核对；`docs/` 正本章残留扫描归末阶段（宽词盘点词表 = 各详设验收词并集 ∪ P92/R 族/危机词族，豁免清单随申报出具）；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节 + 迭代裁定 #3 删除纪律。

## 验证与保全（prereg 完整性硬门；各阶段行为判据引用本节）

受本迭代影响的既有验收线清单（strategy-work §6 硬门）：

| 线 | 载体 | 保全论证义务 |
|---|---|---|
| 位面 1 出口金 / 过渡凑齐率 / 终局金 / 终局阵容完成率 | sim 四指标（sim-testing §一） | hp 删除后升级更早更频，经济曲线变化由改后对照批核对四指标不恶化（判读按「新预期」：死时金 ≥50 形态应消失） |
| FM-1 防线（金支出出口） | `11_shop_decisions.md` §5 | 改后死时金分布对照：滞留形态消失为**目标达成**非防线破坏（防线语义随裁定 #1 更新，见正本更新清单） |
| FM-1 对照读数行基线 | `11_shop_decisions.md:186` | 改后批读数更新该行（新基线记录，旧读数归 git） |
| 锁线行为（R-3 已裁删血项、机制保留） | `12_line_and_intention.md` | 锁定时点不变；可行性与回退带不再随血低收紧，P2 未锁定窗口囤货方向对照申报 |

验证手段现状声明：A/B 批跑通道挂起（sim-testing「先知道边界」末条）→ 本迭代验证 = L1/L2 测试阶梯 + 单帧测试（refresh-chain 详设 §5 清单）+ 同 seed 单局 sim 对照（`cw_sim_match_drive`，对照组 = g_20261028_011013 存档；对照种子集 ≥3 个含原 seed 20260118）；A/B 恢复后补批侧确认。策略/判据层改动 sim 可见（A/B 可观测性声明：本迭代全部改动落判据/策略层，无 operations 执行层改动）。

## 3.1 hp 判据族删除

**范围**：hp 清查件 A 组**全量**（含 A-9 应急带归零链，归属更正见 hp-purge §2）+ B 组孤儿 + C 组边界核对（不动）+ E 组测试逐条 + R-1/R-3 处置。边界：`criteria/refresh.py` 不动（归 3.2）；D 组正本章删归末阶段；开工前先按 hp-purge §7 快照抄录三份证据文件与词表至 `details/hp-purge-appendix.md`（执行单一源）。
**设计依据**：`details/hp-purge.md` 全篇 + 总纲 §3（R-1/R-3 已裁决通过）
**文件面**：`kernel/cw_discipline_rules.py`、`criteria/levelup.py`、`kernel/cw_economy.py`（含 A-9 链）、`kernel/cw_intention.py`、`kernel/cw_comps.py`、`kernel/cw_performance.py`、`kernel/cw_registry.py`、`kernel/cw_hp_policy.py`、`kernel/cw_game_state.py`、`kernel/cw_vocab.py`、`mandate_state.py`（计数器与孤儿字段行）、`statefn/predicates.py`、`statefn/lambda_death.py`（B-12 零消费子集，HP_BAND_NEAR_DEATH 保留）、`audit/provisional.py`、`entry.py:844-846`（血闸措辞同步，清查件 R-1 面）、`shop.py:373/:327/:996` 三行（总纲 §2.1 carve-out）、`mandate.py:963/:996`（hp 残留行）、`criteria/contracts.py:243-246` 与 `criteria/__init__.py:54-55`（hp 行级；contracts.py:88-106/:166-171 守卫面经直调不读 H——无需改码）、`economy_cycle.py:12/:14/:29-30/:177/:187`、`statefn/odds.py:67`、`telemetry/schema.py:460-465/:488-489`、`cw_investments.py:1216`（blood_xp_mode carve-out）、`obs/`、`operations/`、`currency_war_config.py`、`cw_entry_policy`、`cw_decision_trace`（B 组连带注释面，总纲 §2.1 授权）、`sr-od-test` 对应测试（含 `test_no_target_three_arms.py` 带断言更新、`test_decision_payload.py`、`test_line_select.py`、`test_levelup_prob_axis.py`）
**依赖**：无（R-1/R-3 已于 2026-10-28 用户裁决通过）
**优先级建议**：9
**完成判据**：
- hp 清查件 A 组全量（含 A-9）逐条删除到位；B 组孤儿清零；R-1/R-3 按裁决落地（A-10 归类币种通式 / A-11 删血项、`k_empty_window_fallback` 机制保留，细目 = hp-purge §3 处置细目①-④）；
- 残留扫描清零（hp-purge 详设 §6 词表）；
- 升级发射门序 7→6 的单帧测试更新并过；新增「无 hp 支」语义单帧测试；
- <完成前常规检查（本文件首节）>
**验收凭据形式**：残留扫描输出 + 测试名清单 + 单帧测试通过记录

## 3.2 刷新链三组件改革

**范围**：金线闸新算式（ρ 重定义含未锁窗口 ρ=0 声明 + 整级预留分支删）、目标可买条件并入判据（席位腿 = 备战席燃料口径；合成腿 = 机制全集口径）、P92 整门删除（含 `contracts.py:283` 契约行、`test_seat_recoverable_narrow.py`/`test_sim_levelup_cycle.py` 测试面迁移）、危机不变式全链删除（含三处注释残留）、R 族死码清理、免费分支目标可买检查。**资金序声明落地**：升级推迟期刷新维持拒绝（资金序声明，见 refresh-chain §2 末条）。
**设计依据**：`details/refresh-chain.md` 全篇 + 总纲 §2.0 第 2/3 条
**文件面**：`criteria/refresh.py`、`shop.py:1-233`（头部与 ρ 别名）+ `shop.py:267-315`（p92_seat_recoverable 删除段）+ `shop.py:1962-2080`（刷新发射/收工/计数键）、`mandate.py:4/:1078-1079`（crisis docstring 与序位声明）、`criteria/contracts.py:252/:255/:261-267/:273/:279-291/:283/:288-291`、`criteria/__init__.py:60/:62/:65/:71-73/:76`、`economy_cycle.py:24/:233`（危机注释残留）、`telemetry/schema.py:500`（注释残留）、`cw_investments.py`（如免费分支需效果侧配合）、`sr-od-test` 对应测试（`test_seat_recoverable_narrow.py` 改造、`test_sim_levelup_cycle.py`）
**依赖**：3.1（levelup.py 净态：门④/`level_spend_blocked` 删除后，判据消费的 `stay_target_of` 语义落定）
**优先级建议**：9
**完成判据**：
- 发射段实现 = refresh-chain 详设 §5 终态伪码逐行对照；单帧测试清单 §5 七条全过；
- P92/危机不变式/R 族删除面残留扫描清零（refresh-chain 详设 §1/§3 各段验收词）；
- 追星误拦场景回归：席满+可合成帧发射、席满+零燃料+不可合成帧拒（关店）；
- <完成前常规检查（本文件首节）>
**验收凭据形式**：单帧测试七条 + 残留扫描输出 + 行为对照（3.4）

## 3.3 买面席位与追星改革

**范围**：买臂 need_star 星级口径统一、停留刷窗口压牌库让位、刷新负结果记忆（含免费分支标记）。
**设计依据**：`details/shop-buy-reform.md` 全篇
**文件面**：`shop.py:234-266`（合成腿谓词段）+ `shop.py:316-1961`（六序买入/M6:1543-1616/垫件/序 5/序 6/C1）+ `mandate.py::fuel_sell_candidates` 本体（:392，若 W4 需调整其行为）+ `shop_session.py`（访问计数消费）+ `mandate_state.py`（负结果记忆标记字段新增行——载体 = StrategyState，与 3.1 的 :123-124/:174 行级分工）+ `criteria/levelup.py`（`unfinished_star_targets` 消费接线，只消费不改编据本体）+ `sr-od-test` 对应测试
**依赖**：3.2（让位窗口与负结果记忆消费刷新判定现值）
**优先级建议**：7
**完成判据**：
- 星级口径：未完成成员副本可买（含 2★ 追 3★ 场景单帧）、达标成员显式停买（拒因 `star_goal_met`）；
- 窗口让位：停留刷窗口内 M6 零发射单帧测试；非窗口 M6 照常回归；
- 负结果记忆：拒绝态关店后无状态变化不重入提刷（单帧/会话级测试）；免费分支受记忆约束；
- <完成前常规检查（本文件首节）>
**验收凭据形式**：单帧/会话测试清单 + 拒因键观测样本

## 3.4 行为对照验收

**范围**：同 seed 单局 sim 对照批（seed = 20260118 原局 + ≥2 个新 seed）跑前跑后行为对照；四指标核对（对照手段受限于单局形态，分布级确认挂 A/B 恢复——验证与保全节声明）。
**设计依据**：总纲 §2.1 验证接口 + 本文件「验证与保全」节
**文件面**：只读运行（`.debug/` 产物）；无代码面
**依赖**：3.1、3.2、3.3
**优先级建议**：5
**完成判据**：
- 同 seed 轨迹差异点逐帧对账（锚 = 追查件 §1.2/§1.4）：差异应落在「升级发射帧出现（原 17 帧全拦 → 现按带判据发射）」「追星刷新在席位可腾帧发生」「无重复提刷白转帧」等正向期望上——「危机带/金滞留形态消失」为机理说明（机制已删，结构性不可能重现，无鉴别力），不作验收判据；
- FM-1 形态核读：死时金分布对照申报（滞留形态消失 = 目标达成）；
- 四指标单局读数记录并申报（分布级结论挂 A/B 恢复，如实申报）；
- <完成前常规检查——本阶段无代码面，只核对产物落盘>
**验收凭据形式**：对照批 journal/档案 + 判读记录（锚点事前写，strategy-work §4）

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2、3.3、3.4
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

> 完整逐章清单单一源 = hp 清查件 §2.4 D 组（落地批开工前随 hp-purge §7 快照抄录至本迭代目录）——下表为按阶段归并的关键行索引，两处不一致以清查件快照为准。

- `strategy-docs/00_framework.md`：§3 硬闸门授权面重写 + §4（hp 删除后授权面收窄申报）← 3.1（清查件 D-1）
- `strategy-docs/11_shop_decisions.md`：§2 资格门链（7→6 门）与拦截层处置行 ← 3.1；§2.1 资金线门行（血本位归类随 R-1）← 3.1；§3 刷新判据段整节重写（三组件/目标可买/新算式；R1/R2/P92/危机不变式旧段删）← 3.2；§1 序 1 星级口径 ← 3.3；§5 FM-1 防线行（滞留形态语义更新）← 3.4；:186 批读数行新基线 ← 3.4
- `strategy-docs/02_mandate_layer.md`：§3 M3 行（门序/血闸归类）← 3.1；M6 行（窗口让位）← 3.3；§4 hp 边界行复核 ← 3.1
- `strategy-docs/23_shop_screen.md`：§1 刷新放行条件行整行重写（三组件）+ 动作清单刷新行 ← 3.2
- `strategy-docs/01_math_framework.md`：P36/P92/all_channel_exists 行删、P21/P86 行处置 ← 3.1/3.2；§3.4 R2 门 ρ 口径行（停留目标卡价）← 3.2；§5 状态函数表刷新判据行 ← 3.2
- `proofs/math_proofs.md`（路径注意 = proofs/ 下，非 strategy-docs/）：P36/P92/P21/P40/P54/P86 行按各详设处置段执行 ← 3.1/3.2
- `proofs/validations/`：随母命题处置（P40 validation 等）← 3.2
- `strategy-docs/20_large_balance_must_spend.md`：清查件 D-10 收尾行 ← 3.1
- `proofs/p36-crisis-firepower-floor.md` 整文件删 ← 3.2；`proofs/p21-*.md`（D-19 降级义务）与 p37/p71/p72/p85/p86/p92/p28/p24 相关引用行 ← 3.1/3.2
- `proofs/出口生存余量设计批-命题与因果链.md`：:112/:238 P92 节随 P92 删除处置 ← 3.2
- `strategy-docs/14_p1_consume_arms.md`：§5.2 危机带判据修订段删 ← 3.2
- `strategy-docs/04_survival_budget.md`：§7 对账表 hp 行清 + §6-1 口径差核对项申报 ← 3.1
- `strategy-docs/12_line_and_intention.md`：§2 方向状态载体视界相关段（R-3 删血项后 H 语义更新）← 3.1
- `strategy-docs/10_prep_decisions.md`：:199 历史注记清 ← 3.2
- `strategy-docs/22_prep_screen.md`：§1 第 4 步升级检查血预算类拒发表述 ← 3.1（清查件 D-12）
- `strategy-docs/26_battle_settlement.md`、`17_stall_form_spend_authority.md`、`19_reinforce_channel_and_survival_discount.md`、`21_opening_window_and_tool_consume.md`、`strategy-docs/README.md` ← 3.1（清查件 D-8/D-9/D-11/D-14/D-16）
- `flow/README.md`、`flow/action_ops.md`、`flow/session.md`：§2.1 表 hp 三行过期清 + decision_hp/B-7 联动行 ← 3.1（清查件 D-27/D-28/D-29）
- `game_state/fields.md` 等字段文档 ← 3.1（清查件 D-29）
- `telemetry/schema.py`：义务来源枚举 `'crisis'`（:488-489）清 ← 3.1；`:500` 注释残留清 ← 3.2
