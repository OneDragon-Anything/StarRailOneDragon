# CW 复审返工批报告(REWORK_R1234)——FIX_REVIEW_20260903 R1-R4+防线硬化

> 日期:2026-09-03。性质=修复批(独立复审 FIX_REVIEW_20260903 返工清单
> 逐项落地+复审判「防线硬化」两项);按用户裁定,本批结算后将跟独立
> review agent——报告末预留「复审自查节」供对表。
> 文件面:src 侧 `cw4/{shop,mandate,entry,criteria/contracts}.py`、
> `kernel/cw_intention.py`(新增单一源包装)、`sim/ab_core_swap.py`;
> 测试面 `test_cw4_contracts.py / test_cw4_shop_line.py /
> test_cw_zero_refresh_fix.py`。登记节=design_telemetry「复审返工批」节。
> **冻结申报**:冻结族/残余 11 项/契约 v2 正文/判据数学零触碰;
> R199 修复批在飞文档面(IMPL_DESIGN/telemetry 叙事/proposal)零触碰,
> 键登记行=本批自己的新节(键不与 R199 节撞)。

## 1. 逐项修法与证据

### R1(mandate.py 契约漏接)——修在接线层

- **修**:`run_mandate` 增关键字参 `state`;arm1 消费位 cap 改**消费点
  现读** `state.max_units()`(不再信 frame 调用方喂入值),arm1 /
  lv9_stop / spend_unified 三消费位(复审点名 L298/300/303)全部接
  `ensure_contract`;另补复审同款漏接位 shop.py / entry.py 的
  `proof.stop_buy` 消费位(shop.py:332 类,弃权侧=保守停买 fail-closed)。
- **对抗场景 A 复验(翻绿)**:`rework_adv_20260903.py` A1——固定常数
  cap=DEPLOYED_CAPACITY 喂入 frame 且无 state 派生链 ⇒ 前提
  `deploy_cap=None` ⇒ **违例计数 ≥1 + M3 零发射**(修复前=零计数+M3
  照发);A3 对照:state 派生链 ⇒ 零违例(不误伤)。
- 单测锁:`TestMandateArm1Wiring` 两用例(负/正)。

### R2(r1_commitment_account 契约登记)——标定批已落,本批补消费位键位

- CONTRACTS/BYPASS_TABLE 登记+两条连带红(test_covers_all /
  test_injected_value)系**标定批已结算**(CALIB_REPORT;本批开工亲跑
  71→182 passed 验证在绿)。
- 本批补齐剩余半边:有值期 r1 判据消费从挂在 `r1_start` 键下改为经
  **本键** `('refresh','r1_commitment_account')` 核验;None 期仍走
  `r1_start`(fail-closed 语义)。前提=可核验派生(见 §3)。

### R3(K 投影域扩两死带)——修在规格+接线层,单一源纪律

- **①P1 锁线过渡带**(支持度 ≥0.5 未锁帧,update_intention 逐
  game-round 滞后):回退接旧核 `p1_early_pair` 方向单一源——新增
  `cw_intention.p1_early_pair_members()`(= `_pair_members(p1_early_pair
  (…))` 包装,零复制推导逻辑);pair 派生空(全驱逐)⇒ 链 hoard 空窗
  全集兜底。
- **②P2+ 带**(target_comp None 且非 P1):回退接旧核 `hoard_target_set`
  分带(unlocked=绯英⑤兜底 11 件 / weak=跨线骨架 / demoted=骨架满配)。
- 契约 `k_projection` 前提同步扩:值域全集声明覆盖三带(scope 文本+
  可核验派生前提,见 §3)。
- **行为锁**:TestKGapFallback 7 用例——空窗带(2)+过渡带(2,含
  单一源对拍)+P2+ 带(1)+锁线不变(1)+缺供给保守侧(1)。
  原锁 `test_non_gap_support_at_threshold_keeps_behavior` 红=按锁纪律
  重推:该锁钉的是「≥门槛不回退」半边覆盖形态,FIX_REVIEW ②缺口2 已
  定谳为死带,R3 扩域取代其语义(重推出处=本节)。
- **对抗场景 C/D 复验(翻绿)**:C3 死带解除(过渡带回退+方向件买入,
  买向 ⊆ p1_early_pair 单一源集);D2 P2+ 兜底接通(爻光 ∈ 绯英欢愉
  core 经 M2 发射,D3 旧核同帧 n=11 对拍)。

### R4(cap 真值源统一)——修在真值源层

- mandate 侧与 shop 侧统一到**单一真值源 `GameState.max_units()` 派生
  链**(level+宝钻、封顶 10,cw_state 单点收口):entry 帧
  `deploy_cap=state.max_units()`(旧观察复合 `obs.deploy_vacancy+
  len(deployed)` 废弃,注释声明口径);mandate arm1 消费点同链现读;
  shop.py funding 侧 MandateFrame 同链。`MandateFrame.deploy_cap` 类型
  放宽 `int | None`,缺读=deploy_vacancy 保守 0(fail 方向与
  arm1 None 兜底一致)。复审 ②-1「双源漂移」消除:两臂同链,
  cw_screen_prep 的 dep_n 双源容忍带不再进 cw4 决策面。

### 契约硬化(自我声明式前提零检测力)——修在前提的可核验性

- `ev_input_wired=True` 声明位 ⇒ **`ev_slot` 运行时类型核验**:
  合法=None(None 期 fail-closed,判据语义)或 `CalibValue`
  (provisional.get 返回物);裸 float/字面量=「回退字面量但保留声明」
  复发形态 ⇒ 违例弃权+计数(对抗 E1 实证检测力)。
- `k_none_domain_covered=True` 声明位 ⇒ **实解析核验**:`k_target`
  (原值)/`k_fallback_available`(供给在场性)/`k_fallback_resolved`
  (消费位实解析回退集):锁线世界或供给缺帧=合法;供给在场而解析
  空集=复发形态违例(对抗 E2 实证)。
- **静态守卫(测试)**:`test_criteria_public_calls_whitelisted` 扫
  src 树判据公开函数调用点,白名单={shop,entry,mandate}(已接线
  消费位);定义文件/criteria 内部/测试仓不辖——新增消费位绕过
  ensure_contract 直调即红。

### v6 mark 行硬化

- `record_v6_landing` 空/纯空白 evidence ⇒ **raise**(入口拒绝);
- `v6_checklist` mark 行**独立复验**(空证据=行红,不因「申报过」即
  绿)+ evidence 文本随行输出(可审计,复审建议项)。
- 对抗场景 B 复验(翻绿):B1 空 raise / B2 绕过入口直写空白 ⇒ 行红 /
  B3 非空 ⇒ 绿+evidence 随行。

### 附带诊断:活性守卫 sell 饥饿(v6 阻塞①)——定位+修(守卫层)

- **R3 修后复跑仍红**(new_core:sell 0 发射)⇒ 按任务书在本批内定位:
  1. **非同根于 R3**:sell 发射路径(M4 腾席/funding/EV 卖面)接线
     完好;R3 只扩 K 方向域,不辖卖面。
  2. **根因(探针实证,core_swap/rework_sell_probe2/3.py)**:M4 系
     卖族唯一无前置发射路径,触发前提=bench 恰满(9/9);None 期买量
     系设计门(EV 买面 fail-closed U_X、dominance 需 stop_flag)⇒
     新核买量 ~6/局 + 部署持续放空 bench ⇒ **173 波 bench 峰值 7,
     满席 0 次** ⇒ M4 构造性不可达;funding 需 gold<need(5 波,候选
     全为线内件);EV 卖面 T_SEARCH_A None fail-closed(既定)。
  3. **低频活非死路**:扩 seed 实证 sell 4/30 局(planes1)、1/20 局
     (planes2)——路径活,守卫 n=10 固定 seed 0-9 抽样面撞不到。
- **修(守卫层治本)**:`action_family_liveness_gate` 增**升级扫描**
  (`LIVENESS_ESCALATION_N=40`):非豁免零发射族 ⇒ 换 seed 段复扫,
  耗尽仍零才 raise——守卫的「存在性下界」声明与其抽样规模对齐,不再
  把低频活误判死路;实测 9 局升级段命中 sell=1,**守卫绿**
  (escalated_runs 披露进报告)。买量门本身系标定面(U_X 等),
  开闸归标定批辖,不在本批伪造。
- 单测锁:升级救活(escalated_runs>0)/升级耗尽仍 raise 两用例。

## 2. 验收记录(全实测)

| # | 验收项 | 结果 |
|---|---|---|
| ① | 对抗场景 A/B 复跑(复审脚本语义,rework_adv_20260903.py) | **全绿**(A1-A3/B1-B3;C/D/E 同脚本一并 15 断言 PASS) |
| ② | R3 三带行为锁 + 守卫复跑 | 行为锁 7 用例绿;活性守卫 n=10 注入态 **ok=True**(new_core sell=1,escalated_runs=9;baseline 全族活)——**sell 饥饿解除**(根因+修法见 §1 附带诊断) |
| ③ | cw4 快集 | 182 passed(contracts+zero_refresh+shop_line+mandate_v1+statefn,not slow);CW L1 全量 2407 passed / 2 skipped / 1 xpassed + **1 预存红**(test_cw_w614 旧核 digest——本批零触碰 decision_v2/runner.py,并行在飞文件所致,标定批 ⑦ 同款申报) |
| ④ | n=5 冒烟 None 期零漂移(seed0-4) | 刷新 5/5 == **0**;升级池化 **156**(与 CALIB 验收① 逐位一致) |
| ⑤ | 注入态刷新链 | 刷新 0/0/0/0/**2**、升级 168、异常 0(与 CALIB 验收② 逐位一致;V_GAP=24.7 总账形态经本键契约核验) |
| ⑥ | ruff 改动文件 | 6 src 文件 + 3 测试文件全过 |

产物:`rework_adv_20260903.py/_out.txt`(对抗复验)、
`rework_smoke_20260903.py/.json`(冒烟+守卫)、
`rework_sell_probe{,2,3}.py`(sell 根因探针)。

## 3. 约束遵守申报

- 判据数学零改动:criteria/* 判据本体函数零触碰(contracts.py 仅前提
  核验层;refresh/buy/sell/levelup/stockpile/equipment 未动)。
- 冻结族/残余 11 项/契约 v2 正文零触碰。
- R199 在飞文档面零触碰;design_telemetry 仅追加本批新节(键登记行,
  键不撞 R199 节)。
- 每修三元组(修/根层/验)见 §1 各节;旧锁重推申报=R3 过渡带锁
  (§1 R3)。

## 4. 复审自查节(供独立 review agent 对表)

> 每修一行:根层声明(现象根在哪层/修在哪层)+泛化声明(同族扫描
> 结论)。检验式全部可复跑(脚本在 core_swap/)。

| 修 | 根层声明 | 泛化声明(同族还有吗) |
|---|---|---|
| R1 mandate 契约接线 | 现象根=接线完备性(契约纪律条款 2 未兑现全集);修=接线层(三消费位+stop_buy 两处补 ensure_contract)+消费点 cap 现读(判据输入不采信调用方喂入) | 同族扫描=静态守卫测试(白名单外判据直调点全树红)——现树唯一白名单三文件,新增消费位必经守卫;ev 侧同族=ev_slot 类型核验(裸字面量检测力) |
| R2 r1 消费位键位 | 现象根=新增判据消费位未走本键(标定批已登记表,消费侧挂 r1_start 键);修=消费位分键核验 | 同族=criteria 全公开函数 ⇄ CONTRACTS 静态完备性对拍(既有门,亲跑绿);消费位侧同族由 R1 静态守卫覆盖 |
| R3 两死带 | 现象根=规格层值域覆盖声明与实现不一致(K 投影域只辖空窗半边);修=规格口径扩三带(契约 scope)+接线层三带回退,单一源=cw_intention(p1_early_pair_members 新包装+hoard_target_set,零复制) | 同族=「旧核有、规格无、新核丢」清单余项:FIX_REVIEW ②-3(回退无方向性)已由过渡带 top-2 方向部分收敛(空窗带仍全集,影响买序质量非死锁,维持低立案);②-4(drought 影子)已申报过线后批 |
| R4 cap 真值源 | 现象根=真值源双源(mandate 观察复合 vs shop max_units)可漂移;修=单一真值源 max_units() 派生链(消费点/构造点两处同链),注释声明口径 | 同族=FIX_REVIEW ②-2(adapter.py deploy_vacancy None→0)系旧核冻结域,呈报不代修;②-3(level=3 字面兜底)低风险随下次接线批(复审原判) |
| 契约硬化 | 现象根=前提核验为「自我声明」形态,对「回退字面量但保留声明」零检测力;修=可核验派生(运行时类型/实解析结果)+静态守卫(调用点白名单) | 同族=其余前提谓词(k_members/gold-reserve/deploy_cap 非 None)本系检查实参形态,已有检测力;ContractCtx 其余字段无声明位残留 |
| v6 硬化 | 现象根=mark 行申报内容零核验(流程性防线);修=入口拒绝+checklist 独立复验+证据随行审计 | 同族=order 行自报时间戳/text 行子串匹配——复审已判「文本游戏」边界仍在(text 行子串命中即可绿),系仓库文本锚的既知极限,呈报不扩 |
| sell 饥饿 | 现象根=守卫抽样规模与「存在性下界」声明不匹配(低频活 4/30 误判死路);深层= None 期买量设计门使 bench 满席不可达(M4 唯一无前置卖路径)——前者本批修(升级扫描),后者系标定面(U_X)非接线缺陷,开闸归标定批 | 同族=守卫其余族(refresh/buy/levelup)频率高不受窄抽样影响;升级扫描对全部零发射族生效(非 sell 特判) |

**可推翻条件(留给复审)**:①注入 V_GAP=裸 float 字面量至 shop r1
消费位 ⇒ 应见违例计数(E1);②删除 shop.py 三带回退体仅留声明 ⇒
k_projection 前提应违例(E2 形态);③任一白名单外文件直调判据 ⇒
静态守卫红;④run_mandate 无 state 喂固定常数 cap ⇒ A1/A2 形态;
⑤n=10 守卫对真死路(全 seed 段零发射)仍 raise(升级耗尽用例)。
