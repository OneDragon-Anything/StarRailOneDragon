# 0380 — 卖侧下界守卫执行点补全 + CompTransaction 单位守恒修复(own_gap 演进谱系)

- 日期: 2026-09-01
- 状态: accepted (采纳)
- 关联: ADR-0373(卖侧唯一体系引擎守卫——本批补其执行点缺口)、ADR-0375(希儿系辖域——判据单一源沿用)、ADR-0371(W174 补完守卫——边界声明)、ADR-0360 件3(保留序——本批撤销其溢出卖出豁免的一半)、ADR-0379(W195 零修法——本批为其移交的唯一遗留可修面)、W196 发现①(谱系无覆盖的巡检)
- 批: W197(W188 移交②/W196 巡检发现①:演进事务卖通道辖域复审)

## 背景与问题

W188 记档 own_gap [136,269] = 「演进事务 CompTransaction 链拆板 dep=∅ 执行层形态」,
W196 巡检确认该谱系无任何已收账批覆盖。本批因果探针(monkeypatch
execute_replacement/_engine_completion_tx + _sell_tag 逐笔,池 861fc9f6 重放)
**先探后修**,结论与 W188 记档有一处实质出入:

- **136(列车 tier2,主凶)**:r7 同段两笔 off_target 卖三月七经
  **arbiter 卖候选通道**(非 CompTransaction 内部卖出——W188「经 CompTransaction
  卖出」归因错记):候选生成对**批前状态**计数(列车在手 3>tier 2),两笔
  逐笔合法、同批采纳后聚合 3→1 跌破 tier;ADR-0373 的两消费点
  (`_sell_tag` 候选生成 + `sell_priority_key` 弱序)都是**决策期单件口径**,
  对同批前序卖出不可见,采纳执行点无复检。意向层无辜:pair 全程含列车
  (W195 判读同判「非错位局」),拆板本身病,W195 零修法不改变此机制。
- **269(DOT tier2)**:艾丝妲全程被卖侧守卫保护(sell_tag 逐轮恒 None),
  换线下场进 bench 合法;DOT 第二 distinct 件(卡芙卡)r9 才出现,owned≥tier
  到 r9 才成立(补完守卫辖域=owned≥tier,不辖成型缺口)——**供给侧主导**
  (与 W195 判读一致),非拆板。可修面≈0(终轮边缘),本批不改其行为。
- **附带发现(件③,单帧锁构造时暴露)**:`_apply_comp_transaction` 应用序
  undeploy 先于 deploy 清槽——bench 满时 `bench_place` 无空槽返回 None,
  保留件(retained,回滚窗语义)被**静默删除**(无卖出退款、不回卡池);
  终态容量校验只算终态(n_bench_final),看不见中间态溢出。单位守恒违约,
  独立于守卫语义的执行层 bug。

辖域判定:136 的两处缺口(arbiter 批内聚合 + execute_replacement 溢出卖出)
同根——ADR-0373「TT 体系件在手≤tier 不可卖」语义在其声称覆盖的通道上
**没有执行点守卫**:溢出卖出此前由「保留序(相对优先级,bench 满截断时
保护件照卖)+ engine_guard(仅 engines≥2 局)」辖,ADR-0373 不辖清单第 3 条
「演进事务卖出已辖」的声称不成立。

## 决策

**卖侧下界守卫执行点补全**(flag `registry.sell_floor_exec_guard_enabled`
默认开,关=逐位回 W195 后行为):

- **件① arbiter 采纳点复检**:`arbitrate` 主循环对卖 tag 候选
  (off_target/for_gold/free_bench)采纳前,对 **working**(前序采纳后的
  状态)复检 `sole_engine_sell_blocked`——前序卖出计入计数,批量语义经
  逐笔复检实现(carry_gate/补偿器通道逐笔发射本就对渐进态评估,不在辖域)。
- **件② execute_replacement 溢出卖出下界**:`sold` 名单中命中下界的件
  (TT/希儿系,在手≤tier)不再卖出而改**留场**(回 deployed_keep,同
  engine_guard keep_extra 先例——换血可以,清空不可),新上场名单相应收紧;
  保留序/undeploy/回滚窗语义不变。ADR-0373 不辖清单第 3 条对「卖出面」的
  豁免撤销(undeploy 面保持——[ADR-0373 Considered Options]「禁下场压死
  良性轮换」语义不变)。补完事务 `_engine_completion_tx` 的 sell_cands
  已被 `_locked_protected_names`(引擎键∪pair 成员)排除 TT/希儿件,
  W192 辖域不变,本批不重复设卡。
- **件③ CompTransaction 单位守恒(无 flag,bug 修复)**:`_apply_comp_
  transaction` 应用序改为 sell → **deploy 源清槽** → undeploy → deploy;
  `_resolve_comp_transaction` 的 post_bench 构造同式同步。清槽提前只影响
  中间态,终态与旧序一致。
- **判据单一源**:新增 `discipline.sole_engine_sell_floor_plan(bcs, state)`
  批量口径(前序「可卖」件从计数扣减,blocked 件不扣),`sole_engine_
  sell_blocked` 重构为同一计数底座(`_sell_floor_counts`/`_sell_floor_eval`,
  TT 三羁绊 ≤tier + 希儿系核心条件辖,两判据取或)——单笔输入与单件谓词
  逐位一致;件② 事务内多笔同序扣减用同一函数。

### 与既有守卫的边界声明

| 通道 | 守卫 | 状态 |
|---|---|---|
| arbiter 三卖 tag 候选(决策期) | `_sell_tag` 生成期谓词 | ADR-0373 既有 |
| arbiter 三卖 tag 候选(采纳期,同批多笔) | working 复检 | **本批件①** |
| carry_gate ④ / 两补偿器 | `sell_priority_key`(逐笔渐进态) | ADR-0373 既有 |
| execute_replacement 溢出卖出 | 保留序优先级 → 下界留场 | 保留序=ADR-0360 件3,下界=**本批件②** |
| 补完事务 sell/undeploy | `_locked_protected_names` 保护集 | W174/W192 既有,不变 |
| 谷底回滚 SellDeployed | 恢复机件豁免 | ADR-0373 既有 |

## Considered Options

- **缓判等 W195(意向层自愈)**:拒——探针实证 pair 全程含列车/艾丝妲全程
  被卖守卫保护,两局均非意向错位驱动;W195 已零修法收账(ADR-0379)且把
  本谱系列为唯一遗留可修面。
- **只在候选生成端修(把 `_sell_tag` 改成对「本批拟卖集合」评估)**:拒——
  候选生成是逐件纯函数,引入批上下文会拉扯层1 契约;采纳点复检(one line,
  working 已存在)同样闭合且语义更准(执行前真值)。
- **溢出卖出改为「整事务拒绝」**:拒——事务拒绝(退避 2 轮)会压死良性
  换血(新线成型被旧线唯一件阻塞);留场语义与 engine_guard keep_extra
  先例一致,换血照旧、清空不可。
- **溢出卖出下界并入保留序(截断前把下界件永远排进 retained)**:拒——
  retained 容量由 bench_free 决定,排进 retained 只是把「卖掉」换成
  「占掉别的件的 bench 位」,当下界件数 > bench_free 时仍溢出;留场才是
  不变量级保证。
- **件③ 加 flag 走 A/B**:拒——单位守恒是契约级 bug(静默删单位,无退款
  不回池),不存在「回退到 bug 行为」的合法 A/B 臂;修复以既有全量测试
  与 A/B 主指标不回退作验证(A 臂锚失配若出现=其生效面披露,如实记档)。

## 验证

- 新单帧锁 8(`test_cw_w197_sell_floor_exec.py`):批内复检主锁(两笔同名
  TT 件第一笔采纳/第二笔拒)/批量计划口径(单笔与谓词逐位一致 + 同批扣减
  [F,F,T])/溢出留场(在手=tier 不卖不丢,事务 applied)/冗余不辖
  (在手 tier+1 照卖,卖后仍 ≥tier)/flag off 双点逐位回退(两笔均采纳 +
  溢出卖出恢复)/件③ 由溢出锁的「在手数不跌破 tier」断言承载
  (旧序下 retained 件被静默删除,该断言必红)。
- 既有锁语义化适配:ADR-0328 ②(fixture 三月七→银枝,TT 辖域由新锁承接)、
  W52 先采纳卖(fixture 卡芙卡→银枝)、W35 接线锁(桩收 sell_floor 参)、
  ADR-0293 registry hash 锁同步。
- sim A/B n=300(同池 861fc9f6 导出件重放,seeds 0-299,invest on,
  A=flag off,B=flag on 含件③):主指标=own_gap [136,269] 清零或归因改判/
  benign→mal=0/全指标不回退——数字见 W197 报告
  (`.debug/temp/currency_war/cw_dev/deep_read/W197_报告.md`)。
- 探针脚本与数据:`.debug/temp/currency_war/w197_comptx/`(w197_probe.py
  因果探针/w197_probe2.py 通道钉死/w197_ab.py A/B + json)。

## 影响

- decision_v2/discipline(`sole_engine_sell_floor_plan` +
  `_sell_floor_counts`/`_sell_floor_eval`/`_sell_floor_decrement` 底座,
  `sole_engine_sell_blocked` 重构为同源)、decision_v2/arbiter(采纳点
  复检)、decision_v2/registry(`sell_floor_exec_guard_enabled`)、
  decision_v2/strategy(注入一行)、cw_evolution(execute_replacement
  溢出下界 + sell_floor 透传)、cw_state(_apply_comp_transaction/
  _resolve_comp_transaction 应用序);
- strategy/03_tactics.md(卖侧守卫执行点语义)/01 架构篇(CompTransaction
  应用序)同步;
- 269 own_gap 归因改判供给侧(探针证据记档),ADR-0379「唯一遗留可修面」
  收口:never-2 残差至此在全部谱系(门/评分候选/意向/演进执行层)探尽。
