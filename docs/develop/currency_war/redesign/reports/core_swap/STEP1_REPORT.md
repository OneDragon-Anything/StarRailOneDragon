# CW 换核迁移序 步1:序列契约接线批 报告

> 任务 = §6.4-R R189-6 步1(R190 修注后口径)。规格单一源 =
> `.debug/temp/currency_war/redesign/IMPL_DESIGN.md` §6.4-R(R189-1 ④-1
> R190 重编号改造件清单①③④ + R189-6 步1 R190 修注② 两域验收);
> 契约 = `.debug/temp/currency_war/redesign/CONTRACT_SERIES_DECISION.md`
> v1(已冻结,2026-09-03 用户批准;决策记录 dd-020)。
> 「Decision.ops 多元素化」按 R190 修注**不属本批**(降级为离线装配路径
> 序列化,未实施)。
>
> **R192 症2 改向(2026-09-03,编排者裁决,推翻本批首版原位改法)**:
> 适配器形态 = **包装形态**,禁原位改 `DecisionV2Strategy` 本体——依据 =
> 契约 v1 §1 冻结文字即「包一层长度 1 序列的适配器」+ IMPL_DESIGN §4.1
> 「decision_v2 保持冻结基线:不改一行」辖 `decision/decision_v2/strategy.py`。
> 首版原位改动已回退;现形态 = 薄包装子类 `DecisionV2SeriesAdapter`
> (`decision/decision_v2/series_adapter.py`,新建文件),生产接线 = 注册桥
> `DecisionV2Live` 改继承包装(`strategies/decision_v2_strategy.py`,
> `strategy_id='decision_v2'` 语义不变,`match.strategy` 拿到包装实例)。
> 包装同时覆写 deprecated 别名 `decide_prep_action` 保单动作语义(MRO:
> 父类别名经 `self.decide_prep_screen` 动态派发,不覆写会落到 list 返回)。
> 冻结基线 `decision/decision_v2/strategy.py` 现与 HEAD 零 diff(回退核验)。

## 1. 规格条款对照表(每项实现 → 条款出处)

| # | 实现 | 改动文件 | 条款出处 |
|---|---|---|---|
| 1 | ABC `decide_prep_screen` 注解升 `-> list[PrepAction]`,docstring 按契约全量重述(执行序=列表序/fail-stop/帧稳定域/空批/控制流/生命周期归框架/长度1迁移期适配),引用 dd-020 | `decision/cw_strategy.py` | 契约 §1/§2/§4/§5;§6.4-R R189-1 ④-1 裁决(零翻案,改接线) |
| 2 | 长度1适配器(**包装形态**,R192 症2):新建 `DecisionV2SeriesAdapter(DecisionV2Strategy)`(`decision/decision_v2/series_adapter.py`)——`decide_prep_screen` 返回 `[super() 单动作]`,覆写 deprecated 别名 `decide_prep_action` 保单动作语义(MRO 派发防穿透);docstring 引 dd-020+R192 症2。冻结基线 `DecisionV2Strategy` 本体**零改动**(IMPL_DESIGN §4.1「不改一行」,回退核验零 diff) | `decision/decision_v2/series_adapter.py`(新建) | 契约 §1「迁移期适配(并行使能)」冻结文字(「包一层长度1序列适配器」);R192 症2;§6.4-R R189-6 步1 R190 重编号① |
| 2b | 生产接线(最小侵入面):注册桥 `DecisionV2Live` 改继承 `DecisionV2SeriesAdapter`——生产构造路径 = `establish_new_match → StrategyManager.instantiate('decision_v2') → DecisionV2Live`(strategies/ 注册面唯一 BUILTIN 桥),`match.strategy` 即拿到包装实例;`strategy_id='decision_v2'` 语义与 GUI 显示不变 | `strategies/decision_v2_strategy.py` | R192 症2 ③;§6.4-R R189-2 免做④(注册桥机制照抄模式) |
| 3 | 生产备战消费段序列化:`run()` 决策段改收 list(F3 形状校验 list[PrepAction])→ 逐动作 `_record_step`/控制流/F3/④期望态/⑤执行/执行后 heavy 重观察+对账;任一动作未落地 = fail-stop(丢弃余下+恢复原语+交回外循环重观察);空批 = 合法交回重观察(现役核不可达,注记);DeferSpheres/BailToOuter 不进 execute 链、defer 计数归框架 | `operations/cw_screen/cw_screen_prep.py`(run 决策-执行段) | 契约 §2(fail-stop/逐动作验证保留)/§4(空批与控制流);R190 重编号③;§6.4-R R189-6 步1 |
| 4 | 席满破墙段(第二生产消费点,§6.4-R R189-0 R190 修注①点名的 L1193/L1351 两处之一)同步序列化:逐动作执行 + fail-stop | 同上(`_bench_full_break_round`) | 契约 §2;R189-0 R190 修注① |
| 5 | 离线装配路径连通(非生产受牿面,仅接口兼容):`prep_brain._select` 归一**过渡期两形态**(冻结基线单动作 / 包装 list)后取单动作(DecideAdapter 单元素批现状保持;空批在该路径不支持,抛错显式) | `decision/decision_v2/prep_brain.py` | 契约 §1;§6.4-R R189-0 R190 修注③(装配链=离线/测试路径);R192 症2(基线不再原位返 list) |
| 6 | sim 两离线消费点:`cw_replay.py` **零改动**——实读确认其唯一决策消费 = `decide_shop_screen`(L239-240,商店线),prep 接口零调用,辖域仅商店线;`checks/decision_v2.py` 新增 `check_prep_series_contract()` 序列形状契约锁 + 包装等价门(受检对象 = `DecisionV2SeriesAdapter` 输出,R192 症2 ⑥;见 §3) | `sim/checks/decision_v2.py` | §6.4-R R189-1 ⑤(R190 重编号④);SIM_CONSUMPTION_MAP Q1(prep 在 sim 零调用) |
| 7 | as-built:`07_plugin.md` 接口节按契约重写备战线返回 list + 序列语义 + dd-020 引用;迁移期描述 = **包装形态**(`DecisionV2SeriesAdapter` + `DecisionV2Live` 继承接线;只写 as-built 语义) | `docs/develop/currency_war/strategy/07_plugin.md` | 契约头部(as-built 承接归 07_plugin.md);R192 症2;任务书第 5 项 |

**保守口径显式呈报(任务书授权项)**:批内轻验证/批尾 heavy 节流——契约与
§6.4-R 未给消费侧节流细则,本批按**现役逐动作 heavy 重观察**保守实现
(每动作落地后 `_observe(heavy=True)` + `_v2_post_frame_accounting`,与旧
单动作路径逐位同构;长度1下零行为差)。另:契约 §3 截断判归发射器(策略器),
消费侧仅把已知画面出口(StartBattle=契约 §3 终点;OpenShop=切商店画面非帧
稳定)作序列终点,其余动作落地后续发——多动作场景现役核不可达,新核序列
发射器落地时按契约枚举收紧。

## 2. 两域验收(R190 修正后判据,全实测)

### (a) 商店线零漂移门(辖域=商店路径,证明本批未污染)

`runner.simulate_core_ab(old=现役核工厂 DecisionV2Strategy(registry=
sim_decision_registry()), new=None 默认构造, n=20, planes=1, pool=snapshot)`:

| 指标 | 实测值 |
|---|---|
| ledger_diff_pairs | **0** |
| identical_result_pairs | **20/20** |
| pool_fingerprint(双臂同源) | `a369f5ecf6626c66+eqg1`(单值,对拍公平) |
| avg_hp_a / avg_hp_b | 53.15 / 53.15 |

(附带说明:sim 对 `decide_prep_screen` 零调用,SIM_CONSUMPTION_MAP Q1;
本门按规格仍实测跑足 n≥20,结果与该测绘自洽。)

### (b) prep 线等价门(核心)

**b-1 离线探针语料逐帧恒等**(`checks/decision_v2.py::check_prep_series_contract`,
受检对象 = `DecisionV2SeriesAdapter` 包装输出(R192 症2 ⑥),
测试锁 = `test_cw_prep_director.py::test_dd020_prep_series_contract_check_clean`):

| 指标 | 实测值 |
|---|---|
| violations | **0** |
| frames_checked | 14 |
| family_hits(每族帧数) | OpenShop 2 / DeployMove 2 / SellBench 2 / RunEquip 2 / StartBattle 2 / DeferSpheres 2(另 RunDeploy 2 附带覆盖) |
| 断言口径 | 逐帧 `包装输出 == [冻结基线 _decide_prep_action_impl 单动作输出]`(类型 + dataclass 字段逐项相等);形状=list[PrepAction]、长度=1、包装 deprecated 别名单动作=首元素 |

**b-2 cw_screen_prep 消费契约不变生产回归**(test_cw_prep_director 族扩展,6 条全绿):
- `test_dd020_series_len1_consumes_same_as_single`:长度1序列同帧同动作,单轮恰一次决策、恰执行该动作、status 语义不变(read_only 编排透出);
- `test_dd020_series_fail_stop_drops_remaining`:三动作序列第2个未落地 → 第3个不执行(执行器调用数=2)、恢复原语一次、交回外循环;
- `test_dd020_series_control_flow_defer_not_executed`:DeferSpheres 首位 → 零执行器调用、defer_count=1、余下动作丢弃;
- `test_dd020_series_empty_batch_hands_back`:空批 → 零执行、交回重观察;
- `test_dd020_production_registration_returns_series`(R192 症2 ③ 接线锁):`DecisionV2Live` is-a `DecisionV2SeriesAdapter`、STRATEGY_ID 不变、实例 `decide_prep_screen` 返回长度 1 list;
- 帧级新旧入口对拍锁 `test_cw_w971_blackboard.py::test_prep_screen_par_old_vs_new` 升级为包装口径(基线单动作 == 包装序列唯一元素)。

**b-3 测试面同步更新**(消费单动作的既有锁,按锁语义重推后改锚,非机械跟绿):
- `test_cw_w971_p3b_seg2.py` `_StubStrategy` 返回 `[action]`;
- `test_cw_gate_hooks.py` 两处策略替身返回 `[action]`;
- `test_cw_deploy_ops.py::test_w530_wiring_locks` 与 `test_cw_w543_equip_expect.py::test_w543_wiring_locks` 源码锚自 `action = match.strategy.decide_prep_screen(...)` 放宽到调用面 `match.strategy.decide_prep_screen(session, config)`——锁语义(决策→期望态先于 execute→heavy 对账)原样保留,不再钉死已被契约取代的单动作变量名。

### 测试运行(R192 改向后复测)

- 受影响文件定向:7 个测试文件(prepared_director / blackboard / p3b_seg2 / gate_hooks / deploy_ops / w543_equip_expect / expected_state)→ **214 passed, 1 skipped**;
- L1 快速集 `uv run pytest @sr-od-test/cw_quick.txt -m "not slow"` → **2130 passed, 3 skipped, 1 xpassed**(149s);
- ruff:7 个 src 改动文件(含新建 series_adapter.py、注册桥)**全过**;测试文件带既有 E402 合并文件债(机械拼接体例),本批新增沿用该文件体例,未新增错误类别。

## 3. 探针语料清单(check_prep_series_contract)

| scenario | 帧构造 | 覆盖族 |
|---|---|---|
| main_flow_free1 / free2 | 空 obs(free_bench_slots=1/2)×4 连调,主流程阶段位推进 | OpenShop(普通买)/ RunDeploy(部署组合)/ RunEquip(装备)/ StartBattle(出战) |
| chain_a ×2 | 有球无空席 + deploy 空位 + 同阵营 count≥2(slot 变体) | DeployMove(部署拖拽) |
| chain_c ×2 | 满席 + level10 + 零金 + 杂件(bench 变体) | SellBench(卖) |
| defer ×2 | 满席 + level10 + 全 3合1 保护件(球数变体) | DeferSpheres(球留置) |

空批:**不可达注记**——现役核规则序恒出动作(含 DeferSpheres 兜底),
无探针可构造,登记为检查器 note 非违规(消费侧空批分支由生产回归
b-2 的 stub 策略驱动覆盖)。

## 4. 让路冲突

目标文件(`decision/cw_strategy.py` / `decision_v2/strategy.py` /
`decision_v2/prep_brain.py` / `operations/cw_screen/cw_screen_prep.py` /
`sim/checks/decision_v2.py` / `07_plugin.md` / 相关测试)**开工时均无
在飞改动,零冲突**。并行批在飞文件(`kernel/cw_investments.py` /
`prep_actions.py`(app 层壳)/ `sim/runner.py` / screen_info yml 等)本批
**零编辑、零依赖改动**(runner 仅只读调用 simulate_core_ab)。

## 5. 已知边界

1. **多动作续发的消费侧防线**:契约把帧稳定截断判归发射器;现役核长度1
   下多动作不可达。未来新核发射多动作时,消费侧对非画面出口动作落地后续发
   (依赖发射器截断正确性);批尾 heavy 节流未做(保守逐动作重观察,见 §1
   保守口径)——两項待新核序列发射器批按契约收紧。
2. **`prep_brain._select` 两形态归一**:冻结基线单动作 / 包装 list 过渡期并存(R192 症2 后基线不再原位返 list),归一处见 §1#5;空批抛错(DecideAdapter 绑定表单键现状);若该路径需要序列化,走 R190 降级的独立离线装配路径改造件,不在本批。
3. **bench-full 破墙段**无 F3/期望态(沿旧状,仅加 fail-stop);其消费
   形态与新核发射器对齐归后续批。
4. **契约 §3 截断枚举的消费侧对应物**:OpenShop 作为序列终点是消费侧
   保守判定(契约表无 OpenShop 条目——它属 prep 线画面编排动作);若发射器
   实现期需将其正式入表,回契约 v2 改版。
5. ruff 对 sr-od-test 既有 E402 债未清(非本批辖域)。
