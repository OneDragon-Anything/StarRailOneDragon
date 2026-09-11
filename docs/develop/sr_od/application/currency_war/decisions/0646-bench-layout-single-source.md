# ADR-0646: bench 布局真相单一源化(T-308;T-280 诊断落码)——对账写回重建槽位表 + tracked 域下标直拷 + 布局代次检差通道

- 状态:accepted(2026-09-12)
- 背靠:T-280 交付报告 §③ v2 修订版(方案正本,经方案对抗审收口:`.debug/progress/2026-09-06-currency-war-redesign/reviews/T-280-方案对抗审.md`);ADR-0316(bench 槽位语义模型,本件为其「槽位表语义写入端」承诺的补全);ADR-0392(deployed 侧单一源适配先例);ADR-0387(对账装备合并语义,本件保持不动);T-182(同族 tracked 账同构化先例)
- 落点:`kernel/cw_reconcile.py`(写回重建+健康门+epoch 递增)/`kernel/cw_exec_state.py`(epoch 字段+类型注解修正)/`operations/cw_op/cw_op_buy_cards.py`(播种+期望态基座下标直拷、单动作循环检差三步)/`operations/cw_op/cw_shop_action_ops.py`(guard 下标直拷、卖出归一下标直拷、检差封装 `reseed_bench_if_layout_stale`)

## 背景与动机

两例降级 WARNING(2026-09-09 实机,`.log/mcp_server.log.2026-09-09` L10016/L12149)的分叉根 = **bench 布局真相双源**:`tracked_bench_chars` 的「列表下标布局」(mutate/simulate 动作面消费)与「BenchChar.slot 字段」(投影播种与 guard 构造消费)脱节;脱节的持续制造者 = `reconcile_tracking` 写回直拷 SIFT 紧凑列表——破坏 ADR-0316 的「槽位表语义写入端」形状契约(同文件注释早已自申报此风险)。buy 落洞动作(`bench_place` 首空槽)在两域各按自己的布局找洞,洞位置不同源 → 新卡落槽不同 → 槽序排列分叉(成员集不变 → 多集等价 → guard 降级 WARNING),每次落洞动作放大一次差异。

诊断排他结论(T-280 §④):45 组合枚举证明不存在任何单一静态 seed 形态能同时复现两域实证值 → 排除单侧建模错,锁定「两域对同一 seed 读数不同源」;修法若只做事件通道不做写回重建,播种仍按 slot 重构、脱节每局再生(被否案③)。

## 决策

三层(主修 + 防御 + 通道):

1. **S2(主修,充分条件):对账写回恢复形状契约+重建布局。** `reconcile_tracking` 的 bench 写回经 `bench_from_compact` 转定长 9 槽位表再写 `tracked_bench_chars`——与同函数 deployed 侧既有 `deployed_from_compact` 写回(ADR-0392 单一源适配)**同构**,bench 侧是同构修法的漏网侧,本件补齐既有模式,非发明新机制。效果:写回后列表布局=画面布局(洞在真实位置)、slot 字段与下标天然一致(下标+1),紧凑态从写入端消失;消费端 `bench_from_compact(pad 态且 slot 健康)` 退化为恒等,两域播种自动同源。
2. **S1(结构防御):tracked 输入域消费点改「下标直拷」**(`pad_bench(deepcopy(tracked))` 替代 `bench_from_compact`),恰 4 点:投影播种(cw_op_buy_cards)、买牌期望态基座(cw_op_buy_cards)、guard tracked 构造(cw_shop_action_ops)、卖出侧 tracked 归一(cw_shop_action_ops)。**`cw_screen_prep.py` 的 `bench_from_compact` 两点禁改**:其输入是 `obs.bench_chars`(SIFT 现读)非 tracked——SIFT 读的 slot 字段与自身读序同帧同源,是 SIFT 域唯一布局真相;「禁读 slot」只在 tracked 输入域成立(slot 与下标的一致性由 S2 写回端保证)。guard 点 deepcopy 隔离顺带关闭旧 `bench_from_compact` 冲突分支经 `bench_place` 就地改 `bc.slot` 的守卫读路径写副作用。
3. **S2 写回前置槽号健康门**(与 `_reseed_bench_layout` 同式:占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY,违者**拒绝写回**保旧+留证):把 `bench_from_compact` 对无效槽号的静默 fallback 在写回点升级为显式拒绝,防脏读数固化为形状自洽的槽位表(布局错而守卫恒过,比现状更难发现)。留证通道 = `_conflict`(obs_conflict 行经旁路进缺陷台账;kernel 层落账出口约束下与 `_reseed` 的 telemetry kind 行分属两层,语义等价)。
4. **S3(防复发结构通道):布局代次(epoch)计数最小面+检差三步。** `ExecState.bench_layout_epoch`(局级单调计数);reconcile「bench 写回 ∧ 纠漂」写回点递增(deployed 驱动的纠漂不递增——bench 布局未变;误递增无害=重播种幂等,漏递增有害);商店单动作循环每动作消费前检差(`reseed_bench_if_layout_stale` 封装,三态):命中 → ①截断在飞计划(dd-020 截断语义,布局变化使已发射动作的 bench_idx 代际失效,不可只换 state.bench;plan_truncated 记账)→ ②按 tracked 重播种(复用 `_reseed_bench_layout` 含健康门;失败=fail-stop 本段收工交回外循环重观察)→ ③重入决策。**否「并入 S2 写回直接重播种」**:reconcile 跑在 visit 外,该时刻商店决策帧不在消费周期,直接重播种无消费者、越过播种单一源、且把 kernel 层与投影层直接耦合。当前架构 reconcile 均在 visit 外,S2+S1 后 epoch 恒不变(S3 纯未来防御:防 visit 中段未来引入读屏/对账点时布局变化无人知晓)。

**SIFT slot 写点亲读结论(S2 正确性前提锚定)**:`read_bench_chars` 的 slot 赋值链 = `_ctx_slots(ctx, '备战栏', 9)`(cw_identity_obs.py)从 screen_info 取 `备战栏-1..9` area rect,slot_idx = **area 编号 = 画面物理槽号(1-based)**;`identify_slots` 逐槽扫描,每个 SIFT 命中角色的 `BenchChar.slot = 该命中槽的物理槽号`——slot 与画面槽位一一对应、与读序同帧同源(空槽不进列表,画面有中间洞时读序≠槽位序,slot 是唯一布局真相)。S2 信任 slot 有物理层面依据;健康门防御的是识别噪声域(例1 对账实读的幻影/多张噪声证明噪声存在)。

**数学先行(证明归宿声明)**:不变量 I(∀ 商店 visit 内动作帧,两域下标布局逐槽相等)= 引理 1(转移同构:两域动作转移全部经同一 helper 家族——buy=`bench_place`+`_merge_bench`、sell=`bench_clear`、deploy=`bench_clear`+`deployed_place`,代码单一源已保证)+ 引理 2(播种同构:S2+S1 后两域起点为同一列表布局)⇒ 归纳成立 ⇒ guard 多集等价分支前提结构性不可达(守卫回归纯断言职责)。**证明载体 = 结构单一源 + 变异锁有牙性(测试锁 15 条含守卫有牙性锁与写回端变异红证),math_proofs 零增行**(T-182 先例:再立命题构成双源)。本批零策略语义、零新数值判据、零位面字面量。

## Considered Options

- **守卫侧提前对拍洞位**:被否——症状治理,分叉已在账,每次放大照旧。
- **simulate/mutate 合并单引擎双视图**:被否——动作面大改,现有转移已单一源(引理 1),收益不抵风险。
- **只做 S3 不做 S2**:被否——播种仍按 slot 重构,脱节每局再生,分叉复发(诊断实证机制直接否决)。
- **S2 写回直接重播种投影**:被否——见决策 4(reconcile 位无消费者/越播种单一源/kernel↔投影直耦)。
- **S1 卷入 `cw_screen_prep.py:548/702`**(方案 v1 缺陷,对抗审应修-1 收窄):被否——该两点输入是 SIFT 现读非 tracked,下标直拷会把投影布局从画面槽位布局扭成占用挤前,族 A 动作 bench_idx 在错误布局上发射=卖错人/拖空格,且使投影与画面常态分叉(比现状更糟)。

## 影响

- tracked_bench_chars 形状契约自本件起 = 恒定长 9 槽位表(S2 写回端保证),`ExecState` 双账类型注解修正为 `list[BenchChar | None]`(tracked_bench_chars 随批;tracked_deployed = 落地审 accept 附随义务同批补齐——其恒为含 None 槽位表形态与 bench 侧同构,projection_contract.md §6-G2 登记项全量闭环)。
- guard docstring/defect verdict 根因句更新为本诊断精化口径(播种双源),「simulate 落洞规则不随 churn 重排」旧表述退役——历史 bug 态(tracked 未及 S2 重建)残留时多集等价分支仍可显影自愈,复发=回退哨兵。
- 卖出侧归一(488 点)语义从「slot 重构」变「下标保序」:S2 生效前提下恒等;历史 bug 态下不再按陈旧 slot 重构,错位卖出由 mutate 代际校验拦截 no-op(安全非等价)——故 S2 先于 S1 生效,同批禁拆。
- 测试:sr-od-test `test_cw_t308_bench_layout_single_source.py` 15 锁(S2 形状×2/端到端播种同构/T-280 例2 帧重放/健康门×3/epoch×3/检差三态×3/守卫有牙性);写回端变异红证(紧凑直拷变异 → 恰 3 个 S2 承载锁红 → 还原绿)。
