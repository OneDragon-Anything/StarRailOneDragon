# CW 复审返工批独立复审(REWORK_REVIEW_20260903)

> 复审者=独立 review agent(2026-09-03)。对象=REWORK_R1234 修复批
> (报告 `REWORK_R1234_REPORT.md`;文件面=cw4/{shop,mandate,entry,
> criteria/contracts}.py、kernel/cw_intention.py 新增部分、sim/ab_core_swap.py、
> 测试三件)。方法论=治本性三问逐项独立作答;修复批自评不采信,全部
> 声称的验证亲跑复现;对抗脚本自设计(`review_probe_20260903.py`,
> 独立于修复批的 rework_adv——走真实消费路径/攻守卫盲区,不复刻其语义)。
> 零生产代码改动、零 git 操作。

---

## 0. 总判决

| 修 | 判决 | 一句话依据 |
|---|---|---|
| R1 mandate 契约接线 | **真解决** | 三消费位+stop_buy 两处亲读核实;A1-A3 亲跑+单测亲跑;消费点 cap 现读 `state.max_units()`,域错位形态(固定常数喂入)实测不可达判据 |
| R2 r1 消费位分键 | **真解决** | 有值期走 `('refresh','r1_commitment_account')` 本键(P4 亲验:CalibValue 形态本键零违例、r1_start 键零触发);None 期仍 r1_start 逐字零漂移(冒烟 0/0/0/0/0 亲跑) |
| R3 K 投影域扩三带 | **真解决(带一个维持低立案的余项)** | 三带回退单一源=cw_intention 新包装(零复制亲读);C/D 场景亲跑翻绿;我方 P3 攻击(单一源解析空集)实测违例+不回退;锁线过渡带旧锁重推有出处有 docstring |
| R4 cap 真值源统一 | **真解决** | grep 全树无残余观察复合;mandate(消费点)/shop(funding 帧)/entry(帧构造)三处同链 `max_units()` 亲读;`MandateFrame.deploy_cap` docstring 声明口径 |
| 契约硬化(ev_slot/k_projection 可核验派生) | **真解决,防线强度有界** | E1/E2 我方在**真实消费路径**(monkeypatch provisional.get / cw_intention 单一源)复现检测力(P2/P3 全过);但静态守卫存在两个盲区(见 §3 F1) |
| v6 mark 行硬化 | **真解决(流程性防线如实)** | B1-B3 亲跑;代码亲读(入口 raise+checklist 独立复验+evidence 随行);order/text 行边界维持既知极限,如实申报 |
| sell 饥饿(附带诊断) | **守卫层=真解决;深层根=合法显式延后** | 冒烟+守卫亲跑逐位复现(escalated_runs=9、sell=1、ok=True);升级耗尽仍 raise 有单测;M4 构造性不可达的深层根(None 期买量门)显式申报归标定批,非隐性图省事 |

**总评:本批无「表面绕过」与「修复引入新问题」判项。** 七项修复的根层
声明与实际修法层对齐(逐项见 §1);我独立发现的问题全部是**防线强度/
措辞精度级**(§3),不推翻任何修复本体。

---

## 1. 治本性三问(逐修独立作答)

### R1(mandate.py 契约漏接)
- **修的是根吗**:根=接线完备性(契约纪律「消费位核验」未兑现全集,
  FIX_REVIEW ①R1 定谳)。修在接线层:arm1(L318-323)/lv9_stop(L324-327)/
  spend_unified(L330-333)三消费位全部 ensure_contract;shop.py:332 类
  stop_buy 消费位两处(shop.py:417/entry.py:356)同补。且 arm1 消费位
  cap 改**消费点现读** `state.max_units()`(L317)——判据输入不采信
  调用方喂入值,这是比单纯接线更深的半步:即使 frame.deploy_cap 被
  喂固定常数,arm1 判据也不可达(A1/A2 亲跑)。✓ 同层。
- **泛化步**:静态守卫测试(白名单外直调红)+ ev_slot 类型核验。
  但守卫有盲区(§3 F1),泛化声明只对「模块属性调用形态」成立。
- **引入新问题吗**:run_mandate 增关键字参 `state=None`,默认缺 state
  ⇒ arm1 恒弃权+计数。全树 grep 消费点唯一=entry.py:417(显式传
  state)——无失配调用面。测试三件亲跑绿。未见新问题。

### R2(r1_commitment_account 消费位键位)
- **根**:新增判据消费位未走本键(标定批登记表、消费侧挂 r1_start)。
  修=分键:有值期经 `('refresh','r1_commitment_account')`(shop.py
  L673-681),None 期走 r1_start(L666-671)。**我方 P4 亲验**:注入
  CalibValue 形态下本键零违例、r1_start 键零触发——分键语义真实落码,
  非申报性。✓
- **泛化**:criteria 全公开函数⇄CONTRACTS 静态对拍门既有(亲跑绿)。
- **新问题**:None 期零漂移由冒烟 n=5 全 0 亲证,不误伤。

### R3(K 投影域扩两死带)
- **修的是根吗**:根=规格层「值域全集覆盖」承诺与实现不一致(FIX_REVIEW
  ②缺口1/2)。修在规格(契约 scope 扩三带)+接线层三带回退,且单一源
  纪律真实兑现:`p1_early_pair_members`(cw_intention.py:602-615)=
  `p1_early_pair` 包装+`_pair_members` 同一算子,**零复制推导逻辑亲读
  核实**;带路由判据 `p1_gap_window` 与 `_derive_p1_pair` 同一
  `_p1_system_support`+同一门槛常数(亲读 L496-529)。✓ 规格层+接线层。
- **攻击纪律(数值锚点)**:回退集全部经注册表派生(`_pair_members`
  ← CHARACTERS factions/flows 直读),消费位无自造清单;C4 亲跑
  买向 ⊆ 单一源方向集——「对得上旧核行为」由 D3 同帧对拍(n=11)承载。
- **泛化步**:「旧核有、规格无、新核丢」余项(②-3 回退无方向序/
  ②-4 drought)申报维持低立案/过线后批——与 FIX_REVIEW 清单一致,
  无瞒报。**我方补一项观察**:三带回退发射序仍 `tuple(sorted(...))`
  字母序(shop.py:407),锁线过渡带的方向性只在**成员资格**层面成立、
  不在**购买优先级**层面——同 FIX_REVIEW ②-3 已立案形态,维持低立案
  合理,但「top-2 方向」措辞在报告里略强于实际(方向=集合方向,非序)。
- **新问题**:旧锁 `test_non_gap_support_at_threshold_keeps_behavior`
  重写为 `..._lock_band_fallback`,docstring 引 FIX_REVIEW ②缺口2 定谳
  ——按锁纪律走了「重推语义」而非机械跟绿,合规。P2+ 带/锁线不变/
  缺供给保守三边界均有锁(7 用例亲跑)。

### R4(cap 真值源统一)
- **根**:双源漂移(mandate 观察复合 vs shop max_units)。修=单一
  真值源 `GameState.max_units()` 派生链三处同链(entry 帧构造 L413/
  mandate 消费点 L317/shop funding 帧 L737),grep 全树无残余
  `obs.deploy_vacancy + len(deployed)` 复合(cw_screen_prep.py 的
  dep_n 双源容忍带仍在,但已不进 cw4 决策面——与申报一致)。✓
- **边界核实**:`max_units()` 语义亲读(cw_state.py:278-287:deploy_cap
  真值优先、<level 防噪兜底、封顶 10)=「level+宝钻、封顶 10」申报属实。
- **新问题**:MandateFrame.deploy_vacancy 在 cap=None 时保守 0——
  fail 方向与 arm1 None 兜底一致,docstring 声明在案。未见。

### 契约硬化(可核验派生)
- **根**:自我声明式前提零检测力。修=前提改为核验**实参形态**:
  `ev_slot` 运行时类型(None/CalibValue 合法,裸 float 违例)、
  `k_projection` 实解析(供给在场而解析空集=违例)。**我方在真实消费
  路径复现检测力**:P2(monkeypatch `provisional.get`→裸 float 24.7,
  decide_shop_wave 实跑 ⇒ 本键违例+零刷新)、P3(monkeypatch 单一源
  全空 ⇒ k_projection 违例+零 BuyCard)。两形态均非只测 ensure_contract
  单元的空转——检测力在真实路径成立。✓
- **静态守卫的强度(§3 F1)**:正则只捕 `<alias>.<fn>(` 模块属性形态;
  `from x import lv9_stop; lv9_stop(3)` 裸名直调漏网(P1b 实证);白名单
  按 basename 豁免 ⇒ 任意目录下同名 shop.py/entry.py/mandate.py 亦逃逸
  (P1c 逻辑核)。守卫对「新增消费位绕过」的声明只在模块属性形态下成立。

### v6 mark 行硬化
- 入口 raise + checklist 独立复验 + evidence 随行(B1-B3 亲跑;代码
  亲读 ab_core_swap.py:349-360/454-460)。仍是流程性防线(order 行
  自报时间戳/text 行子串匹配边界),报告如实申报不扩——与 FIX_REVIEW
  ③ 判决一致,无倒退。

### sell 饥饿(附带诊断)
- **守卫层修法评估**:`LIVENESS_ESCALATION_N=40` 升级扫描(代码亲读
  L293-314)使守卫抽样规模与其「存在性下界」声明对齐——这是**量具
  对齐**而非量具放水:真死路仍 raise(升级耗尽单测亲跑绿),且
  escalated_runs 披露进报告(不静默)。冒烟亲跑逐位复现报告数字
  (escalated_runs=9、new_core sell=1、baseline 全族活)。
- **深层根处置**:M4 构造性不可达(None 期买量门 ⇒ bench 峰值 7 永不
  满席)申报归标定批(U_X 开闸)——**显式战术权衡+归属声明**,符合
  「显式权衡 vs 隐性图省事」分野。注意:sell 实测 ~1/19 局,存在性
  通过但分布极瘦;量级健康归判前锁/标定批,守卫辖域声明在案。
- **新问题候选**:升级扫描对全部零发射族生效(非 sell 特判,亲读
  核实),不构成定向放水。

---

## 2. 亲跑复现记录(全部本人执行,2026-09-03)

| # | 项 | 报告声称 | 我方结果 |
|---|---|---|---|
| 1 | rework_adv 15 断言 | 全绿 | **全绿**(逐条 A1-A3/B1-B3/C1-C4/D1-D3/E1-E2) |
| 2 | 测试三件(not slow) | — | 79 passed |
| 3 | cw4 快集五件 | 182 passed | **182 passed** ✓ |
| 4 | CW L1 全量 | 2407 passed/2 skip/1 xp/+1 预存红 | **2406 passed/2 skipped/1 xpassed/1 failed**——passed 差 1(见 F2);同一预存红 test_cw_w614 旧核 digest |
| 5 | 冒烟 n=5 None 期 | 刷新 5/5==0、升级池化 156 | **逐位一致**(0/0/0/0/0;156) |
| 6 | 注入态刷新链 | 0/0/0/0/2、升级 168 | **逐位一致** |
| 7 | 活性守卫 n=10 注入态 | ok=True,sell=1,escalated_runs=9 | **逐位一致**(池指纹 b22d0c50a5d9325c+eqg1) |
| 8 | 我方探针(自设计) | — | P1a-P1c/P2a-P2b/P3a-P3c/P4a-P4b 全过(P1=盲区实证,见 F1) |

产物:`review_probe_20260903.py` / `review_probe_20260903_out.txt`(本目录)。

---

## 3. 独立发现(与报告结论的差异/新增)

- **F1(中)静态守卫两盲区**:`test_criteria_public_calls_whitelisted`
  的正则只匹配模块属性调用形态;`from ...criteria.levelup import
  lv9_stop` 后裸名直调**漏网**(P1b 实证);白名单按 basename 豁免,
  任意目录新建同名 shop.py/entry.py/mandate.py 同样逃逸(P1c)。报告
  「新增消费位绕过 ensure_contract 直调即红」的声明强于守卫实际能力。
  建议后续批:正则补裸名调用形态(结合 import 行分析)或白名单改
  路径全限定。不推翻修复本体(运行时核验已独立有效)。
- **F2(低)L1 计数差 1**:报告 2407 vs 我方 2406 passed。工作树系多批
  零 commit 叠加态,测试面有并行漂移可能;同一时点重跑无意义,呈报
  备查——不构成对本批的指控,但提示报告的「全量数字」有时点性。
- **F3(低)stop_buy 弃权侧措辞**:shop.py:419 注释称弃权侧=「保守停买
  (fail-closed,不落入支配买/溢余面)」——但商店线 M2 线成员买入循环
  不受 stop_flag 门(仅 dominance/M6 受门),「保守停买」在商店线只对
  支配买/溢余面成立、对 M2 义务面不成立(M2 系义务不走停手门,行为
  本身正确,是**注释辖域写得比实际宽**)。修注释一句话的事。
- **F4(备查)R3 方向性措辞**:锁线过渡带「top-2 方向」在成员资格层面
  成立(C4 锁),购买优先级仍字母序(sorted)——同 FIX_REVIEW ②-3
  已立案形态;报告 §1 R3 行措辞易读成「有序向」,建议未来批落
  支持度序时一并收口。
- **F5(核验限制申报)**:「判据数学零触碰 criteria/*」在零 commit
  叠加态下**不可独立核验**(cw4/ 整包 untracked,无基线可 diff)。
  间接证据:cw4 快集+L1 行为锁全绿、criteria 公开函数集与 CONTRACTS
  对拍绿。同理「冻结族/契约 v2 正文零触碰」只能核现行态一致,无法
  核「未动过」。
- **F6(中)w614 预存红归属**:红=decision_v2 旧核行为 digest 不匹配。
  本批新代码对旧核的可达面亲查:`p1_early_pair_members` 全树唯一消费
  =cw4/shop.py(grep 亲跑),cw_intention 其余改动为纯新增包装;
  ab_core_swap 不进旧核路径。与报告「并行在飞文件所致」结论**方向
  一致**,但 git 禁令下无法 stash 并行改动做排除法,证据强度=中
  (代码可达性分析,非实验隔离)。归属维持「非本批」,留并行批收口。

---

## 4. 复审自查节对表(报告 §4 七行的独立裁定)

| 修 | 报告根层/泛化声明 | 我方裁定 |
|---|---|---|
| R1 | 接线完备性/静态守卫+ev_slot | 成立;守卫泛化面有 F1 盲区 |
| R2 | 分键核验/完备性门 | 成立(P4 亲验) |
| R3 | 规格层值域/余项清单 | 成立;方向序余项维持低立案合规(F4) |
| R4 | 真值源双源/②-2②-3 呈报不代修 | 成立(grep 无残余;呈报项在案) |
| 契约硬化 | 可核验派生/其余前提有检测力 | 成立;静态守卫半边有 F1 |
| v6 | 入口拒绝+复验/text 行极限呈报 | 成立 |
| sell | 守卫抽样对齐/深层根归标定批 | 成立(显式权衡,escalated_runs 披露) |

**可推翻条件五条(报告留给复审)逐条执行结果**:①E1=P2 真实路径 ✓
违例;②E2=P3 真实路径 ✓ 违例;③白名单外直调=**部分**(模块属性形态红、
裸名形态漏,F1);④A1/A2 ✓ 亲跑;⑤升级耗尽 raise ✓ 单测亲跑。

> 复审零仓库代码改动、零 git 操作;产物=本报告 +
> `review_probe_20260903.py` + `review_probe_20260903_out.txt`(core_swap/)。
