# ADR-0326:「拒绝→补裁决」通用回连机制(层4 末段补偿趟)

- 状态:accepted(W52 核心批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `decision_v2/remediation.py`
  (新文件:RejectReason/Rejection/remediation_pass/三补偿器)+
  `decision_v2/arbiter.py`(结构化拒绝捕获 + 末段补偿趟 + disc_view
  参数)+ `decision_v2/registry.py`(remedy_buy_tags/remedy_min_score/
  remedy_alarm_refresh)+ `decision_v2/strategy.py`(v2_remedy_used
  轮键 + ⑤b 收编删除)+ `cw_state.py`(SellBench.expect,§1.7)。
  W52 执行序第 3-7/9 步。

## 背景(现象与根因)

层4 `_check_constraint` 对候选返回拒绝原因,进 `res.log` 的
`reject` 字段后**被丢弃**——「拒绝事件不回流」:被拒候选的「资源
不足」信息不反向驱动补偿决策(卖件凑金/腾位/换人),被拒动作在同轮
获得资源后也无法重试。S1(买卡金不足常态无变现)曾以
`liquidity_actions` 通道式消解(leader 追加 2026-08-25),但通道是
**逐断链打补丁**:refresh 金不足、bench 满、上阵满各有断链未覆盖
(R3 共同根因结论),且触发源用层3 预测的 `state.gold`(同轮已有采纳
买消耗金时会多卖)。

**根在哪一层**:流程层——拒绝事件是决策循环的**中间产物**,却被
当作终态丢弃;修根 = 通用回连机制(拒绝 → 结构化捕获 → 同轮定向
补偿 → 事务性重验 → 重试),禁止逐断链打 if 补丁。

## 决策

1. **结构化拒绝**(`RejectReason`):`_check_constraint` 返回
   `RejectReason | None`(constraint/resource/shortfall/describe)。
   仅资源型约束(gold_floor→gold / bench_capacity→bench /
   deploy_cap→slot)填 resource/shortfall(补偿路由键/缺口量);
   纪律型拒绝(interest_rule/copies_cap/same_round_mutex/
   boss_levelup_ban/refresh_budget)resource='' 占位,**不进回连**。
   log 行格式不变(`f'{cname}:{describe}'`,判读面零波及)。
2. **捕获两点**(N2):主循环约束拒绝处 + refresh 收尾裁决处;捕获
   条件 = 资源型 + 正分候选(非正分被拒是评分病不是资源病,回连
   无意义——防环第一道闸)。产出 `ArbiterResult.rejections`。
3. **补偿趟**(`remediation_pass`):arbiter 末段,rejections 非空且
   `v2_remedy_used` 未置(轮键,strategy 轮首清零)→ 按资源维序
   gold → bench → slot 取首个可补偿维,构造补偿动作组(卖先于买/
   换)→ arbiter 在 working 上逐动作 `_check_constraint`(资源型三
   约束)+simulate 推进 → **受益候选最后重验**(在其自身 simulate 前
   的 working 上——买后金已扣,simulate 后重验恒误拒)→ 全过整组
   追加,任一失败整组放弃(事务性)+ `v3_remedy_abandoned` 计数 +
   遥测 log;`v2_remedy_used = True`(每轮至多一趟,防环)。
4. **拓扑(方案 B)**:remediation **不 import arbiter**——Rejection
   定义在 remediation,arbiter 反向 import;地板
   (`_active_floor` 结果)经参传入 remediation_pass(避免 arbiter
   import 环);disc_view 经 arbitrate 参数传入(strategy 侧
   assess_discipline 已算,避免重复评估;None 时 arbitrate 内部自取)。
5. **S1 收编**(liquidity → `_compensate_gold`):删除
   `liquidity_actions` + `LIQUIDITY_BUY_TAGS` + strategy ⑤b;
   remedy_buy_tags(含 'carry_gate',ADR-0326 H1)迁 registry;
   **触发源修正**:缺口按 `working.gold`(层4 真缺口)而非
   `state.gold`(层3 预测)——同轮已有采纳买消耗金时旧版多卖、新版
   按真缺口少卖;缺口已足时**重试受益买本身**(不带卖件,「被拒动作
   获得资源后重试」);守卫全量继承 liquidity + **边际羁绊贡献守卫**
   (r3,[20]/[31]:与 board 阵营凑羁绊的配方正件不进补偿卖序)。
6. **S6**(`_compensate_bench`):bench_capacity 拒(非 merge)→ 腾位
   卖 + 重试买;缺槽数 = 占用 − 容量 + 1;槽位已腾出时重试受益买;
   腾位卖件选择 = 保护集与边际羁绊贡献守卫**取并集**挡(r3 修正:
   两条线都不可卖的件才是真正钉死)。
7. **S4**(`_compensate_slot`,D3/H2):deploy_cap 拒 → ①评估 LevelUp
   ②弱件换上。①LevelUp = 单击 +XP_PER_BUY 经验(ADR-0129),
   n=ceil(剩余XP/XP_PER_BUY) 次点击**整组** [LevelUp]*n(执行层
   逐动作独立应用,无节流/去重——§9.6 已核);非 boss 轮 + cap 由
   level 驱动才发;息引擎门按 n×总价口径(补偿器前置);**受益
   DeployMove 本轮仍拒**(升级解的是下轮,cap+n 次点击后才 +1,下轮
   部署管线消化——设计 §9-2 自评点,一致性靠注释维持);②SwapDeploy:
   场上最弱(deployed 中非 target_cores/非引擎件)↔ 被拒上场件;
   「换上不优不换」守卫(被拒件弱于/等于场上最弱可换件 → 无动作)。
8. **S2 残余**(报警 refresh 辖域):refresh 金拒仅当
   `remedy_alarm_refresh` 且 `disc_view.allow_refresh_in_war`
   (报警升级态)才补偿——不为常态刷新借钱;非报警态 refresh 金拒
   进 rejections(捕获照常)但不补偿。25/40 两档口径 docstring
   (25=应急清仓线 / 40=报警降档线,两线并存,均非补偿触发器)。
9. **§1.7 硬规范**(expect 代际校验;AD9-1-1):
   `SellBench.expect: str = ''`(ADR-0317 第三块);simulate/mutate
   分支加校验(expect 非空且与槽内名不符 → no-op + stale_proposal
   语义,对齐 SellDeployed/SwapDeploy 既有守卫);remediation 发射的
   SellBench/SwapDeploy **必填 expect**(从候选生成时的 state 快照
   取名,禁从 working 取——working 被同批先行动作改变,取 working
   名=校验恒过,防线失效)。
10. **检查网**:`decision_v2_remedy_loop`(连续放弃轮 ≥3 = 设计容量
    不足信号;数据源 = cw_sim 账本新增 `sim.remedy_abandoned` 轮级
    信号)+ 变异自检探针(两向锁钉死,防安慰剂)。

## Considered Options

- 方案 A(层2/层4 拒绝旁路返回调用方,调用方再发补动作):拒绝事件
  跨层回流,调用方要感知约束细节 → 层间耦合膨胀;否决。
- 方案 B(补偿趟挂 arbiter 内部 + disc_view 传参,**采纳**):拒绝
  在产出点就地补偿,拓扑单向(remediation → discipline →
  cw_state),无环;策略侧 disc_view 单一来源。
- 方案 C(补偿趟独立于 arbitrate,由 decide_prep 在层4 后另行调用):
  与层4 约束判定脱节(补偿动作的重验需重查约束),否决。
- 三方案均否决的旧通道式(liquidity 逐断链打补丁):根因未碰,
  断链随新动作类型复发;收编为通用机制后删除。

## 影响面

- 行为变化清单:
  - 金不足目标件买:旧 liquidity(层3 预测触发,每轮一笔)→ 新
    补偿趟(层4 实际触发,整组事务)——**意图内**(S1 收编,
    触发源修正)。
  - 同轮先采纳卖→金足:买直接通过、无补偿——**意图内**
    (W56 攻击面 3 锁)。
  - 买先被拒、后续卖补齐金:补偿趟**重试受益买**(旧版买丢失)——
    **意图内**(回连目的)。
  - refresh 金拒:非报警态由「无变现」保持,报警升级态新增补偿——
    **意图内**(S2)。
  - 上阵满:新增 LevelUp/SwapDeploy 补偿——**意图内**(S4)。
- 测试:liquidity 旧锁语义化重写(锁语义不锁函数名);新增
  test_cw_w52_remediation.py 30 锁(§7 全清单对账)。

