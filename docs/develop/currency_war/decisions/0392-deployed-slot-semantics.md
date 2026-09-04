# ADR-0392: deployed 槽位语义模型(定长 10 槽,front 0-3 / back 4-9,空槽留 None 不紧缩)

- 状态:accepted
- 日期:2026-09-01
- 背靠:动作索引约定提案(.debug/temp/action_idx_contract_proposal.md)§4 方案 A
  与 §6 步骤 4(迁移顺序①-⑥);ADR-0316(bench 域同构先例)推广到 deployed 域;
  W57 索引坐标系审查剩余左移面;AGENTS.md「索引/槽位字段必须带定义注释」。
- 落点:`cw_state.py`(`GameState.deployed`/helpers/`simulate`/
  `mutate_bench_deployed`/`_resolve_comp_transaction`/`_apply_comp_transaction`/
  `_merge_bench`)+ 全部 deployed 消费端(decision_v2 全家/cw_plan/cw_evolution/
  cw_sim/cw_evaluate/cw_events/cw_comps/cw_intention/cw_telemetry 序列化等)。

## 背景与动机

ADR-0316 把 bench 升格为定长 9 槽位表后,**剩余的「删除即左移」病族全部集中在
deployed 域**:`simulate(SellDeployed)` 与 `mutate_bench_deployed` 仍是
`deployed.pop(idx)`(cw_state 旧 L1113/L1232),`CompTransaction` 的
undeploy/sell(deployed) 与 `_remove_by_identity` 同走紧缩删除。由此:

- **批内多笔删除索引漂移**:同轮两笔 SellDeployed,前者 pop 后后者下标左移,
  指向别人或越界——现状靠 expect 按名拦截(stale_proposal 拒绝),提案 §4
  方案 C 已声明其缺口:按名不按位,同位同名不同对象(重复同名单位)时拦不住;
  本质是「拒绝坏单」不是「让单不可能坏」。
- **跨源拼接(F2 同型)**:arbiter/演进/补偿多源动作组共享 deployed 索引,
  先动容器的源让后源的 idx 漂移——bench 域已被槽位不变量消灭,deployed 域仍在。
- **表示与画面语义不符**:画面卖出/下阵后场上槽位不左移(与 bench 同理由,
  用户口述权威);紧缩 list 是表示层自造的坐标系。

用户裁定(提案 §4):方案 A(deployed 槽位表化,推广 ADR-0316)为目标态,
方案 C(expect 名校验)保留为过渡防线、槽位化后降级为遥测观测字段。

## 决策

**核心不变量**:`GameState.deployed: list[BenchChar | None]` 定长
`DEPLOYED_CAPACITY`(10)槽表;下标 0-3 = 前排槽 1-4、下标 4-9 = 后排槽 1-6
(`BenchChar.position_pref`='front'/'back' 与 `slot` 1-based 排内槽号保留为
信息位;权威槽位 = 列表下标)。`StrategySession.tracked_deployed` 同契约
(与 tracked_bench_chars 同理,mutate_bench_deployed 就地维护)。

- **坐标系**:`deployed_idx`(SellDeployed/SwapDeploy/CompTransaction.undeploy/
  sell(deployed))= **deployed 槽位表下标 0-9**;生成期 = 执行期(恒稳)。
  与族 B `prep_actions.SellDeployed(row, slot)` 的对齐关系:族 B 的
  (row='front', slot=s) ↔ 族 A 下标 s-1;(row='back', slot=s) ↔ 下标 4+s-1。
- **删除语义**:SellDeployed / CompTransaction undeploy/sell(deployed) /
  3合1 消耗 deployed 份 → **置 None 不 pop**;`_remove_by_identity`(deployed
  侧)→ `_deployed_clear_by_identity`(按身份置 None)。
- **放置语义**:`deployed_place` 按 `position_pref` 路由到对应排的首个空槽
  (front 区 0-3 / back 区 4-9;首选排满时落全局首个空槽兜底——旧行为 append
  不看排,容量门在上游,兜底保持「合法动作必成功」)。
- **容量判据** = 占用数 `deployed_occupied`(**禁止 `len(deployed)`**——定长下
  len 恒 10);迭代一律 `iter_occupied_deployed`(None 跳过)——禁止裸
  `for d in deployed`。
- **入口防御**:`GameState.__post_init__` / `simulate` / `mutate_bench_deployed`
  入口 `pad_deployed`(None 补到定长 10;紧缩前缀顺延占用 0..n-1——旧构造
  兼容,与 ADR-0316 pad_bench 同式)。
- **紧缩序互转**:`deployed_from_compact` / `deployed_to_compact`——紧缩构造
  入槽位表、槽位表出紧缩序(占用序)的单一源;sim 账本与遥测序列化保持
  紧缩序(下游 checks/视图零迁移,ADR-0316 同款决策)。
- **expect 字段降级**:SellDeployed.expect / SwapDeploy.expect_deployed /
  CompTransaction.expect_undeploy/expect_sell(deployed 侧)在槽位表下索引
  恒稳,不再承担「拦截漂移」职责——降级为**遥测观测字段**(记录生成期期望名,
  供判读对照;校验逻辑保留但恒稳下不再触发 stale_proposal 的漂移面)。
  字段不删(发射点/账本/判读仍消费)。

### 后排布局档取舍(表长为何恒 10)

实读 `cw_back_layout._LAYOUT_PREFIX`:后排实际格数随布局档 6/7/8 变
(= 6+(cap−level),ADR-0385)。**表长仍按 10(4+6 基线)**:超过 6 的后排
扩展格属于**画面布局域**(cap 差驱动的屏幕档位,cw_back_layout/select_back_layout
单一源),不进 GameState 表示——扩展格上的单位在 tracked_deployed 里仍占
back 区 4-9 的空槽(基线 6 格不够时落到「排内槽号 >6」的信息位,下标仍在
4-9 内循环复用首个空槽)。理由:①GameState 是策略/账本坐标系,布局档是
执行器坐标系,两者混装会让表长随 cap 抖动、序列化下游全部重迁移;②策略层
从不按「第 7/8 格」决策(排上限 front_max/back_max 门已辖容量);③执行器
拖拽坐标走族 B (row, slot) 物理槽位,不经 GameState 下标。

## Considered Options

- **维持紧缩 + expect 名校验(现状,提案方案 C)**——被否:拦截是「拒绝坏单」
  不是「让单不可能坏」;同名重复单位(3合1 素材)同位时按名拦不住;且每个
  新发射点都要「记得写 expect」,与 ADR-0316 否决降序发射同一形态的约定层债。
- **删除后重解析(方案 B)**——被否:每个发射点逐步重映射,重映射本身是新
  漂移源(ADR-0316 Considered Options 同款理由)。
- **稳定 id 替代下标(方案 D)**——被否:重复同名单位需引入实例 token = 新
  状态字段 + 全发射点改造,比槽位表改动更大且与 bench 域表示分叉。
- **表长随布局档 4+(6/7/8)**——被否:见上节取舍;表示随 cap 抖动,下游
  序列化/对账全部重迁移,收益仅「slot 信息位精确到扩展格」,而 slot 本就
  声明为信息位非权威。
- **deployed 槽位表化(根,选中)**:表示层与画面语义一致(留空不移动),
  生成期索引 = 执行期索引恒等式成立——发射点对 deployed 消费零免疫改造
  (索引生成端从紧缩 enumerate 换槽位 enumerate 即可);消费端一次性适配
  (iter_occupied_deployed/deployed_occupied/None 守卫),之后新增动作类型
  无索引债。

## 影响

- `cw_state.py`:`GameState.deployed` 语义 + deployed helpers 五件
  (iter_occupied_deployed/iter_deployed_slots/deployed_occupied/
  deployed_place/deployed_clear/pad_deployed/deployed_from_compact/
  deployed_to_compact)+ simulate/mutate_bench_deployed 槽位化 +
  CompTransaction 校验/应用按槽位 + `_merge_bench` deployed 份置 None +
  Action 节约定块双族对照表 deployed 行更新 + 族 A 动作字段坐标系注释更新。
- 消费端全仓适配:decision_v2(arbiter/candidates/discipline/ev/phase/
  remediation/scoring/strategy)/cw_plan/cw_evolution/cw_sim/cw_evaluate/
  cw_events/cw_comps/cw_intention/cw_bundle/cw_system_cards/cw_performance/
  cw_bench_equips/cw_board_by_row 的裸迭代/len 容量判断 →
  iter_occupied_deployed/deployed_occupied/None 守卫;写入端
  (cw_observation/default_strategy/prep_actions/cw_reconcile/cw_replay/
  cw_sim 初始化)改产槽位表形态。
- sim 账本/遥测:deployed 序列化保持占用序紧缩(下游 checks/视图零迁移,
  占用数 = len 语义不变)。
- 测试:test_cw_idx_contract.py A 组锁从「拒绝语义」改锁「恒稳语义」
  (两笔 SellDeployed 同容器批,前者置 None 后者索引恒稳命中原人);
  新增 F2 型跨源共存锁(同轮多源混合动作组,断言每个 deployed_idx 执行后
  命中的恰是生成期指向的槽);0316 时未辖的 deployed 紧缩旧锁逐个适配
  (len(deployed) 容量断言/pop 左移断言 → 槽位语义)。
- 行为面:仅「索引恒稳」一项(执行语义等价改造);容量/迭代语义经
  deployed_occupied/iter_occupied_deployed 还原为与旧紧缩语义等价,
  无新策略语义;expect 校验逻辑保留,恒稳下 stale_proposal 的漂移触发面
  消失(拒绝路径仍可达:越界/空槽/名不符的跨代际提案)。
