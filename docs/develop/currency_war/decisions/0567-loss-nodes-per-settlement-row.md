# ADR-0567: loss_nodes 逐结算行化(战斗腿口径)——同轮补给+战斗掉血不再被净额抵减/整条漏记,rounds 链零变化

- 状态:已实施
- 关联:ADR-0235(遥测审计 P0 批,loss_nodes 首版口径)、ADR-0282(hp 三层)、`telemetry/query.py` `_outcome_hp_trusted`/`query_hp`(可信门与「伪值不推进链」纪律单一源)、`telemetry/match_archive.py`(装配本体,SCHEMA_VERSION v8)、`operations/cw_loop.py` `_record_supply_outcome`(合成补给行写端,本批只登记不修)

## 1. 背景与问题

对局档案的 `loss_nodes`(败场节点列表)按「轮」派生:`rounds.hp_delta = 本轮 hp − 前轮 hp`,而轮 hp 取该轮 **ts 最末**一行结算行(`outcomes.jsonl` 后写覆盖)。同轮出现两行结算——补给合成行(`source='synthetic_supply'`,hp 是最近备战帧快照)+ 战斗结算行——时,轮 delta 变成**净额**:凡「同轮补给回血+战斗掉血」的局,败场掉血幅度被回血量系统性抵减;补给回血 ≥ 战斗掉血(净额 ≥ 0)时,该轮被 `delta<0` 过滤掉,**败场节点整条漏记**。

实证(g_20260906_182456 p2r4):前轮末 hp=31;同轮补给行 hp_after=45(18:58:00)、战斗行 hp_after=12(19:02:23)。装配结果 delta = 12−31 = **−19**(净额),而战斗腿 = 45→12 = **−33**;p72 证明文档 F11 口径注记载的双读数混淆即源于此。影响:跨局对照低估战斗腿断层,「掉血分型/死因素材」消费面拿到被回血稀释的数字。

## 2. Considered Options

- **A(否决)条目内分步 delta 列表(steps 嵌套)**:loss_nodes 主字段 delta 仍是净额,消费端必须逐处教会「去 steps 挖战斗腿」——p72 F11 的双读数混淆被永久制度化而非消除;净额≥0 轮的漏记仍需另写派生逻辑。
- **B(采纳)逐结算行化:loss_nodes 一条目对一个掉血结算行(战斗腿)**。三条结构优势:①字段本身就是战斗腿,全部已知消费端(cli 只打计数、`--match` 视图重算不读、离线回放器迭代/过滤形态)零适配拿到正确数字;②净额≥0 的轮因战斗腿<0 **免费入链**(a/c 结构上做不到——在 a/c 里补「派生败腿条目」等于再造一遍 b);③与 `query_hp` 既有「逐结算行推进」口径对齐,全档案只剩一种「掉血」读法。信息零丢失:净额仍可从 rounds.hp_delta 与条目 hp 端点读出。
- **C(否决)单槽净额 + composition 字段**:与 a 同构(净额主字段+嵌套分解),同样两个缺陷不除。
- **迁移三案同难度**:档案 = replay 源流纯派生,v4→v7 四次演进全部靠「bump + 读端 auto-rebuild」,零读端版本分支;b 不引入嵌套新形状、只有行数可变,旧消费端对多行天然耐受,故 b 兼容性最好。

## 3. 已实施架构

- **装配端(`match_archive._build_rounds`,单文件)**:
  - 结算行收集 dict → list(同轮全保留,ts 升序;append 留在排序遍历内,轮槽 `[-1]` 与旧「后写覆盖」取同一行——rounds 表逐字节不变的前提);轮槽 outcome 仍取末行,`_hp_entry` 签名语义不动。
  - 新增与 rounds 链平行的 **settlement 步进链**:同轮每个 hp 可信的结算行按 ts 序各成一步(`step_delta = 本步 hp − 步进游标`),掉血步出一条目;游标独立于轮级 prev_hp(两链各推各的,防双推进)。
  - **可信门只设在步进链**(`_settlement_hp_usable`):判据复用 `query._outcome_hp_trusted`(单一源),另加合成行 0 值防御(见 §4)——无门则 OCR miss 兜底行(hp=0/conf=0)会伪造「掉血 −prev」条目并把游标打穿到 0、毒化后续全部战斗腿。
  - **单步回落**:该轮无可信结算行 → 用轮槽 hp_e 成一步(hp_source 沿用轮槽口径,游标推进规则与 rounds 链一致:凡非 None 即推进)——「无结算行轮备帧掉血也入 loss_nodes」与「仅不可信结算行轮」的既有行为保住,全回落局与旧实现逐字节同退化。
  - **条目形状**:`{plane, round, node_type, hp, delta, hp_source}` 同键同序 + 加法键 `outcome_source`(条目 hp 直接来源结算行的 source 字段,''=屏面真值行)/`ts`(该行 ts);回落条目 hp 来源非结算行(备帧)时两键为 None(L3 契约)。消费端全部 `.get`/按名取键,加法键无破坏。
  - `SCHEMA_VERSION` 7→8;读端零版本分支、零容错合并,旧档案经 `load_archive`/`assemble_pending` 任一触发即原地重装配(loss_nodes 净额→战斗腿)。
- **消费端适配**:`build_timeline.py`(离线回放器)`build_reconcile` 的 `ln[0]` 单取改「单条目标量(与 v7 形态一致)/多条目列表」,渲染端逐行打印、零条目守卫不渲染(L2);`diseases_section` 病③迭代形态天然逐条目,零改动。src 内其余消费点核实零适配(cli 计数/`--match` 视图/index 计数)。
- **测试**(`test_cw_telemetry_archive.py`):T1 修复主用例(修前红:delta −19 ≠ −33)+ T2 净额≥0 漏记修正(修前红:0 条目)+ T3 不可信合成行毒链防御守卫(修前修后同绿)+ M1 形态分叉锁(§4)+ T4 迁移三态(auto rebuild 写回 / auto_rebuild=False 只读 / 源清退回+警告;v7 存量用既有 v4 迁移用例同款降级抹键手法构造)。

## 4. 边界申报

- **旧不变量解除(O1)**:「loss_nodes 条目集 ≡ {rounds.hp_delta<0 的轮}」自 v8 不再成立。全消费面核实无人依赖该不变量;两链分工——rounds 链 = 轮级血面净额(本职),步进链 = 结算腿——已写入 `_build_rounds` docstring,判读侧禁按旧直觉假设 `loss_nodes ⊆ rounds 掉血轮`。
- **等价声明的限定(M1)**:「单结算可信轮条目与旧实现逐字节相同」仅在**前缀链无同轮可信/不可信混合形态**时成立。混合形态(可信行在前+不可信行在后)下两链自该轮分叉:步进游标停可信行、轮槽取不可信末行,后续轮条目按游标计算(新条目 −40 vs 旧 −7)。新行为 = 「伪值不推进链」纪律,方向与 `query_hp` 一致,是正确侧分歧而非回归;有专门测试钉此形态。
- **写端洞登记(M2,本批不修)**:`cw_loop._record_supply_outcome` 在 `last_state.hp is None` 时写 `hp_after=0`、`hp_readable` 属性缺省按 True 兜底 `conf=1.0`(cw_loop.py:1124-1125)——可产出「hp=0 且 conf=1.0」合成行,**通过** conf 可信门。本批在步进链加显式防御(合成行 `hp_after≤0` 结构上不可能是真值——0 血=战败走战斗结算屏——即便 conf 可信也拒锚),但 rounds 链与 `query_hp` 同样暴露于此写端形态,根治须修写端兜底(与相邻观察项 2 同族,宜另立小批)。
- **相邻观察项(同根家族,维持登记态)**:①rounds 链净额语义使 `cw_batch_stats` 连败派生把「补给+败战净额≥0」轮判成胜轮——rounds 链是轮级血面口径本批不动,数据源(outcome 行 killed 字段)现成;②「末结算行 conf=0 时 hp=0 入 rounds 链」——今天已存在的形态,rounds 链零变化故不顺手改。
- **计数口径(L4)**:`n_loss_nodes`(cli 概览/index)语义变为「掉血结算行数」,存量局随重建数值可变(净额≥0 形态 0→1、混合可信形态条目移位、伪值锚条目消失)——修复语义内的变化,非回归。
- **存量档案(O2)**:v8 落地后任一读取触发即把 v7 档案重装配,loss_nodes 数值原地从净额变战斗腿(如 g_20260906_182456 p2r4 −19→−33)。符合「能修复就修复」数据治理判据;历史判读记录(复盘文档/抽查对照)按当时口径成立不改——p72 F11 与 sim-design P72-6 两处口径注已加 v8 勘误指针,防「文档 −19、档案 −33」被判数据伪造。
- **残余边界**:源 jsonl 已清理的档案无法重建 → `load_archive` 退回旧档案 + 警告(既有路径),消费端拿 v7 净额形态按旧口径判读,诚实降级;直读 JSON 的离线脚本对未升级档案天然 `.get` 耐受,任一 `--match` 查询触发重装配后自愈。

## 5. 验证

- 红证:T1/T2/M1/T4 对未修改实现单跑 4 红(T1 断言点恰在缺陷本体 `assert (-19 == -33)`),T3 守卫绿(方案审定谳:防过度修复用例,非红)。
- 修后:新增 5 用例 + 既有 `test_archive_hp_truth_chain`/`_hp_entry` 键形状锁/迁移用例全绿(两文件 90 passed);`ruff check` 改动文件绿;全量 `uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` 全绿;全量套件归编排者 commit 门。

## 6. 风险与后果

- Σ(loss_nodes.delta) ≠ 全局总掉血(按设计):链对账性质本就住 rounds[].hp_delta,无消费端对 loss_nodes 求和,性质迁移无受害者。
- 两链分叉形态(M1)若未来出现「可信门收紧/放宽」的改动,分叉点随门移动——判读侧对单轮数字存疑时,以结算行 ts 序直读 `slices.outcomes.jsonl` 为仲裁源。
- 写端洞(§4 M2)不修期间,「合成行 hp=0/conf=1.0 且恰为该轮唯一结算行」的轮仍会经单步回落产出伪条目(rounds 链今天同样吃该伪值)——已登记,根治归写端小批。
