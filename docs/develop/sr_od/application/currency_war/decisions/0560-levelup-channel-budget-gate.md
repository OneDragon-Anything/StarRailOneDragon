# ADR-0560: 升级通道预算闸(P71-b 溢余段判据落码)——M3 三发射位量闸 + ρ 公共源提升 + 必花域闸生效 + M6 同帧挂起

- 状态:已实施(方案审两轮收敛[无前提对抗 v1「需修订」→ v2「放行实施」]后落码)
- 关联:P71(docs/develop/sr_od/application/currency_war/proofs/p71-levelup-channel-budget-gate.md,判据式本体)、P54(ρ 单一源 p54-r2-interest-floor §②)、P48(整买引理,(1) 辖域)、P21(兑现视界)、P39/P40(通道比较与窗口预留)、P70(溢余段零息)、ADR-0528(必花域让位——被本闸收窄,见 §5 交互)、ADR-0517(单动作发射序)、ADR-0557(sim 下沉)

## 1. 背景与问题

sim62③ + sim72③ 两批同族病灶(判定报告 = .debug/temp/currency_war/20260906-131356-simfind/report.md §问题3,个案 = 局 73002 p2r3):升级通道无**量**闸——M3 批发射位唯一金约束是可负担性(check_affordable),P48 整买只保批内无零收益击、P21 只辖血面、P39/P40 是比较判据,三者都不给单轮升级支出设上限。73002 实测:g=82 起手 15 连 LevelUp 60 金一次性穿息线 28 金,息损 L∈[3,9] 未入账,且该形态恰发生在必花域内(域豁免把血预算停付支压掉)。数学修复已证:P71-b 判据式,升级支出合法 ⟺ 四合取,其中 (3) 溢余段预算闸为本决策新增:`g − s ≥ g* + ρ + Σ窗口预留`。本 ADR 记其落码裁决;数学面见 P71,不在此复制。

## 2. Considered Options

- **A(采纳)B_L = min(U_L, g−g*−ρ−Σ预留) 规范形式落码**:闸值三分量全为已证单一源(saturation_line / P54 ρ / P54 A2 单卡下界),零新自由参数。方案审 §8 指认:(1) 整买强制 s≡U_L,min 恒退化,实现写单比较(`U_L ≤ g−g*−ρ−Σ预留`)。
- **B(否决)XP 占金比 s/g ≤ α 常数闸**:任何常数 α 无规范依据(g 大时过松、g 贴 g* 时过紧),是「没建的模型的替身」;P71-c ④ 定谳其仅为退化极限。
- **Σ预留口径(P71 落码前置定义,v1 B2 阻断项)**:候选① 合格集全完成链 Σ(k−j)×cost(`_r1_ledger_terms` 口径)——**否决**,放进每轮闸值会把闸压成常态负值令升级通道近乎永闭,行为漂移远超修 15 连倾泻的靶面;候选②(采纳)**下帧窗口一张命中卡价**,与 ρ 消费同一函数同参(`refresh.r2_card_reserve`),与 P54 floor「满息档+至少一张命中卡可买」语义逐位对齐。两分量并存是语义角色差异(ρ=本轮升级后买卡臂对一张命中卡的即时购买力;Σ预留=下帧窗口购买力),此口径下多数帧数值相同(闸值退化 g−g*−2ρ)——判据函数 docstring 显式防删一,禁后人当重复项合并。
- **must_spend 域豁免(否决)**:域内豁免 = 病灶发生域不闭合(73002 即域内帧),修复不成立。采纳「要花 ≠ 花在哪」口径:必花域授权辖消费义务,不辖消费通道选择——闸拒只把升级通道的量闸住,买卡臂仍是合法出口,义务不被否决。

## 3. 已实施架构

- **ρ 公共源单一源**:`criteria/refresh.r2_card_reserve`(实现自 shop.py 私有 `_r2_card_reserve` 提升,签名/等级过滤语义逐位不变)。落点裁定 = 方案审 v2:ρ 依赖 data 注册表(CHARACTERS/refresh_prob)属判据面,禁进 kernel 经济层破坏输入纯度。shop.py 保留 `_r2_card_reserve` 别名重导出(R2 门生产调用点 shop.py R1 段逐位不变;测试面 test_cw_r2_interest_floor.py 私有名直引零漂移,4 键不改断言全绿)。docstring 锚定与 `statefn/s_line.rho`(P48 整买价值率)**同名异义**区分。
- **闸判据单一源**:`criteria/levelup.levelup_budget_gate(state, gold, cap_resolved, k_members, bench, deployed, clicks, click_cost) -> (ok, reason)`,拒因恒 `levelup_budget_gate_blocked`。契约登记 `('levelup','levelup_budget_gate')`(前提 = 现读金+等级驱动 cap 在场)与 `('refresh','r2_card_reserve')`(无前提,注册表纯函数)。g* 用 cap_resolved_of_session 口径(投资覆写语境禁裸 level 推 cap)。等级过滤口径 = 当前级(闸在升级授权前评估,与 P54 floor 同帧同等级;R1 的 L* 目标级重估是刷新语境,不辖本闸)。pop_slot 不入闸(P71-a 是收益侧分域命题,dep 满判定塞进闸会误杀 4-5 费搜窗域)。常开无开关(证明已闭环,无「输入未就绪」合法理由)。
- **三发射位全接(拒 = 整批推迟,禁部分买)**:①prep 位 mandate.py M3(spend_unified/check_affordable 之后、Emitted(LevelUp) 之前);②商店波 M3 shop.py(同链位,拒后 fall-through);③必花域 L3 shop.py 域内(独立分键)。发射序中闸位次在 P48 整买与可负担性之后——P71-b 四合取 (1)(2)(4) 既有门串联在前,闸只辖量。
- **拒因分键(遥测显影,零行为旁路)**:`levelup_budget_gate_blocked`(prep+shop M3 共键)/ `budget_gate_must_spend_defer`(必花域 L3,与域外分开归因)/ `budget_gate_must_spend_deadend`(域内闸拒 ∧ bench 无空席 = 金滞留死角,纯观测,攒 sim 数据后再裁是否需要域内降档——降档 = 部分买,与 P48 整买冲突,当前禁做)/ `m6_budget_gate_suspend`(见下)。
- **M6 同帧挂起(shop 侧辖域)**:闸拒帧 M6 压库挂起——闸刚护住的预留金不得被同帧压库击穿(拒后照发 = 金换通道,预留语义同帧失效)。挂起只辖 shop 侧 M6;prep 位「M6」是 emit OpenShop(转店后 shop 帧 M3 重过闸兜住),不重复挂起(防双闸,两侧注释在案)。
- **对账位两处**:①entry.py `_reconcile_posture_authorization` 逐门镜像增闸(签名加 k_members 入参),闸拒归因 = `levelup_budget_gate_blocked`,禁落 contract_other 兜底桶;②sim 检查器 `sim/checks/ledger.check_levelup_budget_gate`(注册名 `levelup_budget_gate`):m3_batch 授权的升级批支出 > 溢余段预算 = 绕闸违规;奖励/补给节点豁免([16]② 同款;**↺ 勘误注,T-115 对齐 = ADR-0580**:[16]② 已删除,奖励节点 = 升级抑制对象,检查器节点型 skip 已退役——授权判定回归 ADR-0471 收编口径的节点无关通道分类,奖励帧 m3_batch 绕闸 = 违规可见);近似声明(首波金时点/上一轮 level/cap 线性回退/ρ 名册超集)全部宽松向,构造性不冤枉合法批;辖域镜像同条件(g ≤ g* skip,落地审 B1 补——镜像缺口 = 开局低金合法批假违规复现)。

## 4. 边界申报

- **辖域限定(g ≤ g* 闸不辖;证明域澄清,交付时申报编排者复核)**:本闸名与 P71 边界 1 均锚定溢余段——金 ≤ g* 帧不存在可保护的溢余预算(息律零档,L≡0),判据式在该域给负闸值,是「预算不存在」的代数信号而非「恒拒」指令;按恒拒落码会封死开局追级通道(lv3 批 4 金帧被拒 = arm0/arm1 升级授权语义断层,L1 三锁红实证)。落码取:g ≤ g* 帧闸 vacuous 通过,升级量由可负担性 + P39/P21 既有门承载;73002 病灶域(g > g*)不受影响。P71 证明文本若需补一句「(3) 辖溢余段帧」,归证明面小修,编排者裁决。
- **推迟语义**:闸拒 = 该批攒到金 ≥ g*+ρ+Σ预留+U_L 的帧一次买齐;禁实现「按 B_L 截断击数」的部分买(动 (1) 属未授权范围扩张,方案审 v1 §7 定谳)。P71 证明文本的「分轮续齐」叙事在现行 spend_unified 判据下不可实现,落码语义 = 推迟。
- **域内死角**:必花域闸拒帧若无可买出口,金本帧滞留(CloseShop)——`budget_gate_must_spend_deadend` 观测,处置(域内降档/改道排序)挂 sim 数据后再裁。
- **flat-4 覆盖面/版本面**:沿 P71 边界 3/5(单价随级上浮则闸值偏松须随实采复核;REFRESH_PROB 表变即重验)。

## 5. 与 ADR-0528 的交互(分域裁决,在案)

G_must = g* = 10×cap_resolved(同一派生),而闸辖域 = 溢余段(g > g*,见 §4)⇒ 与必花域闩按金位**天然分域**:①入域帧(g > g*):闸在域内生效(v2 采纳 3),穿线批整批推迟——ADR-0528 的「停付让位显影」计数面保持,但其升级发射载体在该域被闸收窄,「花光」义务改道买卡臂(test_cw_must_spend_zone 十九局 r9 档案回放帧按此重推改写,docstring 在案);②闩延命残金帧(g ≤ g*):闸 vacuous,ADR-0528 的发射语义**原样保持**(残金帧升级通道未被本闸触碰,test_cw_l3_prep_must_spend_latch 帧 B 发射断言保持原文)。若实机/sim 判读发现入域帧金滞留恶化,回锅点 = 本节(死角观测分键 `budget_gate_must_spend_deadend` 为判读输入)。

## 6. 风险与后果

- 升级批次频下降(闸收紧的本来目的);sim A/B(闸前/后同池对拍)归验收批,采纳判据 = 数学证明(非 A/B,strategy-work §3 第 1 档)。
- 锁语义连带(已在案):既有放行形态锁红按「闸 = 新设计合法收紧」重推,禁机械跟绿(先例与改写清单见 §5)。
