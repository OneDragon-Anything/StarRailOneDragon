# CW 判据契约化批报告(CONTRACTS_REPORT,R198,2026-09-03)

> 任务:判据契约化(用户 2026-09-03 批准的组合性改进①:assume-guarantee 纪律做严)。
> 缺陷背景:零刷新/arm1 两案均为「语境前提未被核验」类缺陷(r1 EV 输入字面量 None 绕过前提;arm1 拿固定槽表常数当阈值域错位)——契约化 = 把每个判据的语境前提写成谓词级契约,接线处核验:前提不成立 = 判据弃权 + 违例计数,禁静默执行。
> 约束遵守:契约化零改判据数学(判据本体函数零触碰);冻结族零触碰;冻结残余 11 项不动;契约 v2(CONTRACT_SERIES_DECISION.md)零改动;seeds1-3 诊断批目录 `ab_run_20260903` 零触碰(仅只读引用 ZERO_REFRESH_DIAG)。

## 1. 契约表清单(单一源 = `src/sr_od/application/currency_war/decision/cw4/criteria/contracts.py`)

`CONTRACTS` 注册表 27 条:键=(模块, 函数);值=`Contract(前提谓词|None, 辖域声明, 规格锚)`;前提谓词签名统一 `ContractCtx → bool`(决策帧上下文:k_members/gold/reserve/deploy_cap/ev_input_wired,消费点现读)。

| 面 | 在册函数(前提) |
|---|---|
| buy | ev_buy_candidates(**先例①**)、ev_buy_veto(None)、p2_lock_buy(None) |
| sell | line_switch_sell(None)、sell_for_interest(None)、funding_support_sell(None) |
| levelup | arm2_schedule / saturation_floor / spend_unified / batch_form / lv9_stop / pop_slot(全 None,显式辖域) |
| refresh | r0_stop(None)、r1_start(**槽位现读前提**)、r2_budget(**先例②**)、crisis_refresh_invariant(None)、hard_node_reinforce_gate(None) |
| stockpile | stockpile_buy(**先例①**) |
| equipment | wear_release / affix_allocation / keep_policy / endgame_context(全 None) |
| 换线(第七面,proof 判据位) | stop_buy / should_switch / signal_arm(全 None;影子面,前提核验随实装接线批) |
| 非 criteria 先例消费位 | mandate.dominance_buy(**先例①**)、predicates.arm1_existence(**先例③**) |

配套:`criteria/__init__.py` BYPASS_TABLE 补 `('contracts','ensure_contract')` 行(谓词/不旁路;R9-1 缺行病静态对拍测试要求包内全函数在册)。

## 2. 三先例前后对照

| 先例 | 前提谓词 | 修前(隐式) | 修后(契约化) |
|---|---|---|---|
| ① S 预留/硬约束③ | `_s_reserve_line_formed`:k_members 非空(目标线成型) | S 预留辖域只活在规格文字与注释(零刷新诊断 §3 第 3 条证伪「54 卡死 r2」预诊时逐条人工核辖域);R196 `_s_reserve` 恒 54 同型挂账 | EV 买面 + M6 + dominance_buy 三消费位接 `ensure_contract`,K 未成型 ⇒ 弃权 + `criteria_contract_violation:buy.ev_buy_candidates` 等分键计数;「禁恒预留」由谓词机器承载 |
| ② 刷新 r2 预算门 | `_gold_minus_reserve_ctx`:gold 与 reserve 现读均在场 | 「金−预留 ≥ 刷价才批」的语境输入无核验(反事实 D 证明单一 reserve 常数形态压不住,正确形态 = P40 预算递推,挂标定批) | r2 消费位(shop.py)接契约:缺现读输入 ⇒ 弃权 + 计数;r2 不在 S 预留拦截对象列的辖域澄清随辖域声明入册 |
| ③ arm1_existence | `_arm1_cap_level_driven`:deploy_cap 非 None(等级驱动现读) | 零刷新修复批把口径修为 `state.max_units()` 单点,但「消费位退回固定常数」无防线(`deploy_cap=None` 兜底 10 即域错位形态) | shop.py M3 消费位接契约:`deploy_cap=None` ⇒ 弃权 + 计数;域错位复发在接线层可见 |
| 附 r1(零刷新修复批接线位) | `_ev_input_from_slot`:ev_input_wired=True(消费位声明槽位现读) | r1 字面量 None 缺口已修(V_GAP 现读),但回退无防线 | shop.py r1 消费位接契约,接线位声明入册 |

## 3. 接线核验点

- `entry.py`:`_criteria_pass`(line_switch_sell、funding_support_sell)+ `emit` 骨架臂 funding_support_sell。
- `shop.py`:dominance_buy、arm1_existence、lv9_stop、spend_unified、stockpile_buy、ev_buy_candidates、ev_buy_veto、r1_start、r2_budget、sell_for_interest、funding_support_sell、hard_node_reinforce_gate(全部消费位)。
- `ensure_contract(fn_key, ctx, counters)`:前提不成立 ⇒ 该判据本帧弃权(不发)+ `criteria_contract_violation:<模块>.<函数>` 计数(分键=判据名);fail-closed 不抛异常不断局(未登记键/谓词异常同判弃权)。

## 4. 验收数字(全实测)

| 验收项 | 结果 |
|---|---|
| 新增契约测试(test_cw4_contracts.py) | **13 passed**(注册完备性 4:六模块全公开函数在册+键引真实函数+第七面/先例键在册+辖域声明非空;先例谓词正反 5:①②③+r1+fail-closed[未登记键/谓词异常];接线正反 4:K 未成型 EV 买弃权+计数 / arm1 无违例 / 正常波零违例×2) |
| cw4 快集(既有+新增) | `uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` = **2393 passed / 2 skipped / 1 xpassed**;唯一红 = `test_cw_w614_sim_fidelity.py::test_default_path_behavior_digest_unchanged`,系并行批在飞改动(sim/runner.py +173 行、decision_v2 族,git status 在案)的预存红——该测试零引用 cw4(Select-String 'cw4' 命中 0),与本批无关;期间另见 plane_intel 一过性红后自愈(并行批活跃编辑中) |
| 违例计数正反测 | 先例①②③ + r1 + 未登记键 + 谓词异常六路:前提成立零计数放行 / 不成立弃权且分键计数==1(②双缺输入累计==2)——见 test_cw4_contracts.py TestPrecedentPredicates |
| n=5 冒烟(契约层零误伤) | seed0-4,mandate_v1 新核,A=契约层现行为 vs B=monkeypatch `ensure_contract` 恒 True(= 契约层引入前等价行为;判据数学零改动,契约层是唯一差):**逐局 ledger+final_hp 全等,drift=0**(产物 `contracts_smoke.json`;refreshes 5/5==0,None 期零刷新保持) |
| ruff | 三改动文件(contracts.py / entry.py / shop.py)All checks passed |

## 5. 文档同步(三同步)

- **IMPL_DESIGN.md §4.2.2「判据契约纪律」**(R198 标形态,打标不删史):单一源=contracts.py;违例=弃权+计数;禁改判据数学;新增判据须同步登记(静态断言封死 R9-1 缺行病)。
- **design_telemetry.md 文末 R198 节**:新键族 `criteria_contract_violation:<模块>.<函数>` 登记(分键=判据名)+ 三先例前提 + 复验记录。
- 代码注释引 IMPL_DESIGN §4.2.2 / ZERO_REFRESH_DIAG 节(持久索引,无会话局部标识符)。

## 6. 遗留与呈报

1. r2 的 P40 总账形态(c_eff·E[refreshes] ≤ V_gap)仍挂标定批(零刷新修复批既定欠账,契约层不改其归属)。
2. w614 默认路径摘要红的归属=并行 sim 量具批,建议其批内收口;本批不代修(文件面纪律)。
3. 第七面(换线)proof 判据位当前为 None 前提 + 影子面辖外声明,实装接线批落位时须补真实前提(同 arm1 模式)。
