# ADR-0571 — 决策环数据流断链修复(双缺陷):R1 合格集 inf 污染根修 + W611 预算投影遥测写点(披露面豁免裁决)

- **Status**: accepted
- **Date**: 2026-09-07
- **关联**: ADR-0516(R1 形式二路径总账——缺陷①判据语义的契约源)、ADR-0445(W611 经济循环总模型——预算投影权威)、ADR-0503(危机金出口臂——sess_release_spent 开臂判据②数据源)、ADR-0563(session 职责分离——strategy_state_of 读口与 B4 收缩申报)、ADR-0463(四遥测键接线申报的初版 ADR)
- **方案与审**: `.debug/temp/currency_war/t88_dataflow/方案.md`(实施唯一口径)+ 同目录 `方案审.md`(零阻断;必改 3 条 F1/F3/F5 全部折入,建议 7 条采纳 F4/F7/F8,F6 随 F3 一并落, F2 属方案文档勘误不涉代码,F9 协调申报见 §6)
- **触发档案**: g_20260907_021326(P1 全部 9 个刷新评估帧 0 刷店;52 行 decisions 切片四字段全 `(0, 0, 0, 0, '')`)

## 1. 背景与问题(双缺陷归层结论)

**缺陷① 刷新通道整局失能(0 刷店)。归层:运行时·策略判据实现层(主根)+ 决策装配数据流层(架构共根)。**
`strategies/impl/mandate_v1/shop.py` 的 `_r1_ledger_terms` 旧实现:单个「当前等级不可追」成员(高费成员在 lv3-6 无出牌档,`refresh_prob=0`)把共享累加器打成 `e_sum = float('inf')` 且无复位——非空合格集被错判「无可追」,R1 以 `no_chaseable_member` 结构性恒关;必花域逃生门只认 `account_over_budget` 拒因,同被锁死。实现与自身声明契约矛盾(函数 docstring 返回契约、`r1_commitment_account` 边界注释都写「inf = 合格集空」),档案逐帧复现 9/9 帧吻合、零残差。架构共根:W611 预算投影(`assembly._budget`)每 prep 帧现算后全链丢弃——行为半边(kernel `refresh_ev_budget` 授权无消费者)与遥测半边(缺陷②四字段)同断。

**缺陷② 遥测四字段全库零赋值。归层:遥测数据流层。**
`v3_reserve_cap / v3_reserve_overflow / v3_release_budget / v3_release_spent` 有字段声明(MandateState)、有读端(recorder.py 透传 / sim engine_p1 轮快照,T-84 已修),但零写点——算完即丢,真值帧(升级窗口/滞留金轮)全落 `(0,0,0,0)`。

**因果假说推翻(对抗审查定谳)**:复盘报告候选 #1 的「0 刷店与 EV/θ 双引擎不可用互为因果」不成立——`shop_ev_u_unavailable`(EV 买面)与 `theta_unavailable`(换线影子面)都是标定槽缺省 None 的 fail-closed 设计态(诚实遥测),且都不是刷新门输入(R1 判据链不消费 U_X/θ)。双引擎点亮归标定批(禁 inject 绕闸),不属本批。

## 2. 决策(裁决)

### 2.1 缺陷① 根修 = 删污染行,复权合格集

`_r1_ledger_terms` 内 `e_sum = float('inf')` 一行删除,仅保留 `continue`:不可追成员剔出本级合格集,inf 仅由 `not qualified_any`(合格集空:成员集空/全部 2★ 成型/该级全不可追)承载。修复与函数返回契约、`r1_commitment_account` 边界注释(P40 R0-1「合格集空 ⇒ EV 恒负」刷新侧特例)、兄弟实现 `r2_card_reserve` 的 continue 过滤四方对齐——ρ 与总账消除同帧两套口径。跨级追账不受影响:不可追成员不消失,T_up 在 L+1 级重估同一成员集(「升 7 搜 5 费」结构)。行为面变化 = P1 必花域帧(金 > g*)新增「R1-yield + r2_budget」刷新发射通道;域外(金 ≤ g*)零漂移,息线纪律由 `account_over_budget` 结构承载。as-built 同步:`11_shop_decisions.md` §3 完成账语义段的「推向更高可齐级」旧表述随污染语义勘误(用户裁定 2026-09-04 的「整套缺件集补齐」读法本身保留,修正的只是装配承载)。

### 2.2 缺陷② 写点 = 装配点三字段幂等覆写 + 键戳轮界 + 执行回执位 spent 累计

- **写端 1**:`assembly._disclose_budget`(每 prep 装配帧)——`reserve_cap/obligation` 取 BudgetView 现算值幂等覆写;`overflow = max(0, gold − reserve_cap)` 纯派生直算(禁二次调 `economy_cycle.overflow`,防 reserve_cap 双算分叉);`v3_disclosure_key`(新增 MandateState 字段,坐标系 = (plane, round) 1 基二元组,取值时机 = 装配帧现读)键戳变更 ⇒ `v3_release_spent/v3_release_reason` 轮界清零并盖新戳。
- **F5 裁决(二选一写死,取①)**:reason 并入键戳清零块——与 schema「sess_release_reason = 当轮义务来源」语义对齐,杜绝跨轮陈读;`'must_spend'` 同步扩进 schema 值域枚举注释。不复用 `v3_release_round`(W332b 泄息指令旧轮语义)。
- **写端 2**:`cw_op_buy_cards.accrue_release_spent`(商店单动作循环执行回执位,`apply_action_outcome` 之后、terminal break 之前)——`RefreshShop` 执行成功(`_ok=True`)逐笔累计 `action.cost`。
- **写端 3(双写语义,实机首局 g_20260907_025608 锚⑤定谳补遗)**:`assembly.disclose_budget_at_shop_frame`,调用点 = `cw_op_buy_cards.run_buy_waves` 段顶入口观察帧(best-effort,失败降级保留 prep 值)——prep 装配帧处关店态,F2 门(gold 仅店开态可信,`cw_screen_prep`)使装配态 gold 不可得 ⇒ overflow/obligation 在 prep 快照恒 0(「金未采」已知语义,非真 0);店开帧 gold 过 F2 门为真值,同一 BudgetView 链覆写三预算字段 ⇒ overflow/budget 变**帧现值**。键戳同轮 ⇒ 不清 spent(轮界清零由键戳承载,本写点只比较不盖戳)。判读:decisions 行 sess_* 取「最近一次写点」值——店开行=帧现值,prep 行=0(金未采,与真 0 分义);sim 侧 prep 快照 gold 恒可信,无需第二写点。
- **必花域帧 reason 写点**:`shop.py` `_zone_hit` 帧写 `'must_spend'`(帧内 last-wins,域外不覆写)。
- **读端零改**:recorder.py 透传 / sim engine_p1 轮快照零改动,sim 经共用装配链自动受益。

### 2.3 装配纪律披露面豁免(禁决策判据消费,硬禁令)

`turn_state.py` 装配纪律「派生值一律不落 session」的立法目的 = 根治**决策输入**读跨帧旧共享态的污染类缺陷。本批四字段 + 键戳是**遥测披露面**:写端只有 `assembly._disclose_budget`(prep 装配帧 + 店开观察帧两调用点,后者经 `disclose_budget_at_shop_frame` 薄壳)与执行回执位,读端只有 recorder / engine_p1 遥测读链;**禁任何决策判据消费这些字段**——决策输入一律走 TurnState 幂等投影。豁免边界申报:BudgetView 本身仍不落不回读,纪律本意零破坏;防回归 = F8 grep 守卫锁(`test_cw_budget_disclosure.test_disclosure_fields_not_consumed_by_decision_modules`,披露面字段在 strategies/impl 决策面白名单外零命中)+ 字段定义注释同禁令。

**已知交互面(策略审查 12/13 轮挂账,申报不修)**:店开帧写点(`cw_op_buy_cards.run_buy_waves` 段顶)无 strategy_id 门——非 mandate 栈经店开路径时同样被盖 `v3_disclosure_key` 键戳,击穿 F4 探针②「非 mandate 栈无键戳」前提;且 registry 经 `getattr` 兜底 DEFAULT 时向 recorder 透传 mandate 模型值。当前注册表单策略,两形态实际不可达=零行为影响;多策略落地前必须加 strategy_id 门(或等价隔离),本申报行即该义务的跟踪载体(三窗催办后于窗口 3 落申报,完整门候批)。

### 2.4 spent 首版口径 = 只计刷新实花(宁窄勿虚)

买牌/升级是否计入「义务实花」全渠道口径在 mandate_v1 语义下未经证明(M2 义务买/支配买与 release 义务不同源,混入会虚高);schema 旧注释引用的 `authorize_release_refresh`/`_accrue_release_frame_spend` 是 decision_v2 时代已退役机制。裁决 = 裁决前收窄口径并如实申报(schema/recorder/mandate_state 注释同步纠偏),扩口径挂 §5 待裁。这是遥测诚实性选择,非功能缺失。

### 2.5 无开关

双缺陷均为断链修复(恢复既有设计意图),无新策略开关;回滚靠 git revert。

## 3. 验收(锁与红证)

- **锁 A**(合格集语义,`test_cw_r1_refresh_ledger`):混合集(可追+不可追)⇒ 账有限;三变异探针(全不可追/全 2★ 成型/成员集空)⇒ `(inf, 0)`;F7 成型先序探针封「重排判定回流」回归路。红证(修复前亲跑):真注册表体系对 15 名 lv3-6 得 `(inf, 21/42/78/78)`——账无穷同时卡费为正。
- **锁 B**(档案帧端到端,p1r8 内联):修复前 rkey=`no_chaseable_member` 零动作;修复后必花域帧 `RefreshShop(reason='must_spend_r1_yielded')` 发射 + 域外帧(gold 40)零发射零漂移。
- **锁 C**(写读闭环,`test_cw_budget_disclosure`):装配后状态四字段 == 同帧独立现算值 + recorder 行 sess_* 键与状态一致且非 None。红证 = 现码恒 0(52 行全零)。
- **锁 D**(轮界清零):p1r8→p1r9 新轮首帧 spent==0、reason==''(F5①)、键戳翻新;同轮重装配不清账。
- **锁 E**(spent 累计):刷新 2 金/笔逐笔累计;未落地不记;非刷新动作不记;F4 栈守卫双探针(键戳过期/无键戳不累计)。
- **锁 F**(店开帧双写,实机锚⑤补遗):prep 关店帧(gold 过 F2 门不可得)⇒ overflow/budget 恒 0「金未采」语义 + reserve_cap 不受影响;店开帧覆写 ⇒ overflow/budget 帧现值(gold 64>cap 50 ⇒ 14/义务>0)且同轮 spent 不清;下轮 prep 关店帧 ⇒ 键戳翻轮清零 + 关店 0 语义恢复。
- 存量锁重推 4 例(3 文件,非机械跟绿;重推依据详见各测试 docstring):
  - `test_cw4_shop_line`:`test_refresh_face_fail_closed` 帧改全 2★ 成型钉真空合格集(旧帧钉的是污染病理);`test_d_hard_node_gate_consumed` 金位收至 g* 钉门接线活性(旧帧修复后落刷新发射,链在门位前返回);
  - `test_cw_must_spend_zone`:`test_zone_l3_consumes_when_arms_idle` 帧改未锁线(锁线帧 R1 买入义务集 = 锁定采购集 15 名,根修后合格集非空 ⇒ R1 yield 先于分层序末位的 L3,按设计让位;旧帧绿恰依赖 inf 污染把 R1 错判全空);
  - `test_cw_vgap_frame_horizon`:`TestMixedPeakCompletionAccount::test_lv6_mixed_set_inf_r1_rejects` 旧锁钉「任一成员不可追 ⇒ E=∞」即污染语义本身,改钉剔除语义(账 = 花火单成员贡献有限 + 小预算帧拒因归真 account_over_budget);`test_lv7_account_finite` 同类强化为整套求和锚(双成员卡费逐位)。

## 4. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 保留 inf 作「推向更高可齐级」的升级路由 | ✗ | 对抗审查攻破:lv3-6 的 T_up 在 L+1 同被打 inf,可齐级推不出,刷新臂 3-6 级结构性死亡(g_20260907_021326 实证);与返回契约/R0-1/兄弟实现三方矛盾 |
| 四字段改走决策投影随 TurnState 下发,遥测另算 | ✗ | 遥测读链(recorder/engine_p1)已按 MandateState 字段契约修好(T-84),改投影 = 拆重修读端;披露面豁免 + 禁消费守卫已封「决策误读」风险 |
| spent 首版即全渠道口径(刷新+买牌+升级) | ✗ | mandate_v1 下义务买/支配买与 release 义务异源,混入虚高违遥测诚实性;扩口径需独立证明,挂账待裁 |
| reason 域外帧不覆写、跨轮保留陈值(只 ADR 申报) | ✗ | 与 schema「当轮义务来源」语义冲突,判读歧义;并入键戳清零块成本一行 |
| U_X/θ 标定槽本批一并点亮 | ✗ | 归标定批 CI 验收五件套;inject 绕闸 = TUNING#1/#2 事故形态,禁触 |

## 5. 显式不修项(划界)与挂账

- kernel `refresh_ev_budget` 行为接线断链与定向刷新车道挂账(W611 行为接线批):需独立证明与对抗审,不搭车;R1 修好后判据链自洽,kernel 授权与 R1 判据双轨并存态如实申报。
- 「遭遇前弃息 D 保血」无行为臂(`hard_node_reinforce_gate` 观察级接线只计数):策略行为缺口,归策略批对抗循环立臂。
- spent 扩口径(§2.4)、修复后 R1 域内实际发射频次与 `r2_budget` 拒因分布、满级帧 R1 首跑行为:待实机/sim 采样判读。
- 档案 rounds 表 4 列增强(方案 §4.5 可选件)不属断链本体,未随批(切片 decisions.jsonl 全字段透传自动带真值)。

## 6. 协调面申报(F9)

`cw_op_buy_cards.py` 存在 ADR-0566 在飞未提交改动(`spend_gate` 签名 +4 行、闸块 +6 行):闸在 execute **之前**(拒绝即 break,不产生执行回执),本批记账位在 `apply_action_outcome` **之后**——语义无冲突、空间分离(本批插入点:新函数置于 `apply_action_outcome` 与 `run_buy_waves` 之间,调用点在闸块之后 8 行);shop.py 在飞改动(lv9_stop 两处,ADR-0565)不涉 R1 段。两批提交顺序由编排者统一裁决;行为验收(F10)注意:修复开启的必花域刷新发射会经过在飞仲裁闸,闸拦截(`must_spend_r1_budget_fail`/闸侧分键)与 R1 判据拒绝须分开归因,勿把闸拦误判为修复无效。
