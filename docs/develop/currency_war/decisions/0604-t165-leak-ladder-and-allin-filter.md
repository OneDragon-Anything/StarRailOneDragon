# ADR-0604: T-165 P2 转化期经济·泄金阶梯(档 0-3)+ ALL IN 窗 XP 类别过滤

- 状态:已实施(落地审需修小修项 D1/D3/D4/D5 已闭环;commit 候编排者统一门)
- 关联:ADR-0580(②(b) 死金压库/规则①②③④,本批摘其判据前置旗但不改判据本体)、ADR-0585(P78 卖出仲裁/发射登记闭集,第 13 臂入册)、ADR-0560(m6_budget_gate_suspend 挂起先例,档 1 复用)、ADR-0603(P72 保底金门,ALL IN 支内位次衔接:类别过滤先于保底门——P21 域内 XP 即便生存域/保底让位也拒)、ADR-0448/设计件 12(停升级线锚表,ALL IN 过滤辖域单一源)、ADR-0528(必花域停付线让位,ALL IN 帧不辖——类别白名单另轴)、ADR-0525(出口③ 垫件臂,与档 1 候选互斥切分 F12)、ADR-0530/SWAP_FRESH_BUYS(轮内新鲜度载体同构先例)、math_proofs P24(支配性优先序)/P49(档匹配)/P41②/P21(到账延迟)、01_math_framework §3.8(支配先于数值比较)
- 方案正本:`.debug/temp/currency_war/attacks/t165_p2_conversion/设计方案.md`(R2+复核审 G1-G6 修订+落地审 D1 勘误;本 ADR = 其落码批持久归档载体,代码注释引注一律指本 ADR)
- 权威链:设计方案 R2 对抗审 16 项+复核审 6 项(G1-G6)全闭合;进度账本级判据增补一条(批#5:s108 同轮卖X买回X再卖X 实证 → 档 2 候选集轮内新鲜度排除,设计方案本体后增补,本 ADR §3-5 收编);落地审 9 项(D1-D9)处置见 §5

## 1. 背景与病理(归层:决策层·买臂合取)

必花域(gold>g*)转化期帧的买臂被触发前置合取关死:dominance/M6 两臂共用的 stop_flag(线成型旗)在线未齐帧恒 False,②(b) 死金压库辖 gold<g* 带与病灶正交,唯一出口 = 2 金/次搜索刷新(P2 RefreshShop:BuyCard ≈4.9:1,终局阵容完成率 4/100)。修向 = 摘旗(档 0/档 2)+ 补「可上场」「压库」覆盖(档 1),刷新降末档(档 3);伴生交付 = ALL IN 窗 XP 类别过滤(P21 域辖,指标 G=0)。板满∧席满真空帧显式不治(移交 T-168);hp 闸批 1 整体移交总图实施序第 5 步(候用户确认)。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 摘 stop_flag(触发前置移除,判据本体不动) | ✓ | 病灶 = 触发前置合取关死非候选判据缺陷;[13] 停手线纪律语义由候选集判据承载(P49 档匹配/线内排除/1★ 全额退),迁移完备性见 §4-① |
| 保留旗+另立新臂绕行 | ✗ | 双臂同候选类双源,候选集漂移面更大;摘旗 = 单点 revert 可回滚 |
| 档 1 锁线门用 k_members 非空 | ✗ | 恒真不可作门(17号稿 §1.1 应修-8 B-1 在库定谳);单一源 = `_ist.locked_comp`(同出口③ D 支,#15 两制择一随本批落定 = 形式核对) |
| 档 2 窗口改「合格集费用带」 | ✗ | 两语义独立(合格集空≠塌缩带空)且恰改靶帧行为;维持在产 `tier_search_window(level, ω)`(§4-#11) |
| 新鲜度排除复用 visit 级 `cw4_recent_sold_names` | ✗ | visit 级窄于设计口径「轮内」(S2 重开路径同轮跨 visit 可达);新载体键式 {phase: (plane, round), names} 与 SWAP_FRESH_BUYS 同构,跨轮自动失效 |
| 新鲜度写端全域收口(含 entry funding/line_switch) | ✗(部分) | 换线/筹资买回属线账/P78-5 豁免面语义,实证病灶无该域样本;M4 族(含 entry 球路径)同口径全登记,funding/line_switch 不登记面显式申报(§3-5)留观测键判读 |
| ALL IN XP 收窄落点 = kernel [18] 豁免支(blood_budget_levelup_blocked) | ✗ | 支A 谓词在策略层(P39 锚对单一源),kernel 侧窄化需跨层搬谓词;且该支决策层消费面(arbiter/remediation)不在本批辖域 |
| ALL IN XP 收窄落点 = P72 闸 `levelup_budget_gate` ALL IN 支 | ✓ | cw4 栈全部 LevelUp 发射必经此闸(shop M3/prep M3/entry funding/L3 变体四消费位单漏斗),单点收窄即 XP=0;[18] 豁免窗 kernel 分支维持 let-pass(被闸收窄掩蔽,行为等价,语义迁移申报 §4-F5) |
| P21 域建「按下一节点型查表」 | ✗ | 第二套血线表(违 04 §4-3/总图 §2.2 血预算算术共享点)且替邻批清偿重校债;落码 = 在产停升级线单一源(P1=11/P2=21),口径差申报 §4-D1 |

## 3. 已实施架构

1. **档 0 支配性优先序(摘旗三处)**:`mandate.dominance_buy_eligible` 去参(shop:1068/prep 两消费位同步)、shop `_m6_arms`、prep M6 位——全仓 grep 无第四处 stop_flag 买臂门(shop 计算位/路由面消费为既有非买臂面,保留)。发射序 = M2 义务 → dominance → C1/④ 定向 → ②(b)(gold<g* 正交带)→ 档 1 → 档 2 → 出口③ → EV → R1 终结:支配性先于带参臂(P24/01 §3.8)。
2. **档 1 可上场非定向买**(`press_buy_deployable`,shop 档 1 位):必花域 ∧ `_ist.locked_comp` ∧ `cap_now−len(deployed)>0` ∧ bench_free≥1 ∧ 候选(非线内 ∧ 非垫件类[F12] ∧ can_deploy_single 围栏可落) ∧ 地板 `g−cost≥g*`;九分键零静默;P72 拒帧挂起复用 `m6_budget_gate_suspend` 先例(只辖 NORMAL,F16 申报 §4);登记闭集第 13 臂 `press_buy_deployable→press`。判据性质 = [31]②/[32] 口述+结构判据(非支配,F10 降格),立项命题候选挂账(§4-待证钩子)。
3. **档 2 压库摘旗扩域**:触发 `gold>g* ∧ bench_free>0`,判据本体不动(P49 fail-closed/P56 s_reserve/线内排除全保留),窗口维持在产 ω 塌缩带(§4-#11);prep 位同步摘旗(emit OpenShop 转店重过闸)。
4. **档 3 刷新降末档**:R1 判据本体零改动(diff 零 hunk),降末档 = 档 0-2 物理在前的自然结果,切分线保留。
5. **轮内新鲜度排除(档 2 候选集;账本级增补收编)**:载体 `cw4_round_sold_names` 键式 {(plane, round_num) → names}(SWAP_FRESH_BUYS 同构,跨轮/跨位面自动失效,排除上界 ≤1 轮);写端 = 卖出发射位全 M4 族(prep 凑息/prep M4/wanted 腿2/shop `_note_sell` 收口四发射位/entry 球路径 M4)+ 读端 = 档 2 候选集(`m6_round_sold_excluded` 分键)。**覆盖面申报**:entry funding 兜底/line_switch 卖出不登记(线账/P78-5 豁免面语义,病灶无该域样本,扩域候观测键判读)。
6. **ALL IN 窗 XP 类别过滤**:kernel 新谓词 `all_in_xp_domain_hit` = `plane_last_battle ∧ hp_decision_trusted ∧ hp 非 None ∧ hp≤停升级线单一源`(不可信/None 帧不过滤:[18]「末战花光是时机不是血线判断」豁免在不可信帧仍生效,与 p2_crisis_band 非对称口径一致);闸侧收窄 = `levelup_budget_gate` ALL IN 支前置 `not _realize_chain_ready ∧ all_in_xp_domain_hit → 拒(分键 all_in_xp_category_filtered)`,位次先于 ADR-0603 保底金门(P21 域内 XP 即便生存域/保底让位也拒);域外帧(hp>停线)与支A 形态维持全豁放行。**宪法姿态(N5 记录)**:消费既有停升级线 hp 读数,零新增阈值/零第二套血线表/零 gated_hp 误接(信任门 = hp_decision_trusted 单一源,采纳复核审 G2),既有授权辖域收窄非新增 hp 点;hp 闸批(血线地板解锁包)零偷跑,移交总图实施序第 5 步。

## 4. 必答项(设计方案 §6 随批清偿)

- **① #7 stop_flag 摘除语义迁移完备性**:买臂门恰三处(§3-1 grep 申报);[13] 停手线 = 「失去购买优先级而非禁令」,纪律由候选集承载(档 0 候选 = 1★ 全额退零重叠;档 2 候选 = P49 档匹配拒纯冗余/线内排除保目标件),transition 件 1★ 全额退属可逆持有不在禁令域;[28] 双指标验收不变(档 1 地板/档 2 s_reserve 保息基);`stop_buy` 计算位与 M2 义务门/路由面消费保留(非买臂溢余面)。登记闭集 12→13 臂(P78 映射表随批)。
- **② #11 窗口源维持**:档 2 窗 = 在产 ω 塌缩带(`tier_search_window(level, ω)` 全游戏定义量)单一源,替换案弃(行为变更+恰改靶帧行为)。
- **③ #17 总图 §4.3 先行前提**:a) P78-1 登记簿承压评估——档 2 摘旗抬高 press 类发射频次,同 visit 卖回禁令(W1 窗口段)与新鲜度排除双向收窄凑息×press 同轮交互,登记簿轮界过期承载有界性(≤1 轮),承压面 = 簿条目数上界不变(按名覆盖写),零新键;b) 奖励帧资格——档 0-2 无帧型分支(必花域判定帧型无关),②(b) 奖励帧抑制先辖不受本批影响;c) C1 交互 criteria 申报——C1(registry core/恒买)与档 1 候选集按身份分层互斥(registry_core 层不落档 1 候选),锁线∧成型重叠带两通道动作同致(既有通道序位在前);d) **T-161 不触发声明**——②(b) 判据零改动(diff 零 hunk),五态锁重推不触发。
- **④ F16 申报**:P72 拒帧挂起只辖 NORMAL;FLOOR_ON 帧挂起让位给凑息禁令的分支随 hp 闸批(总图第 5 步)落位,本批无该分支(L4 锁 NORMAL 限定)。
- **⑤ §7.4 豁免语义迁移申报行(F5)**:本过滤实质收窄 P72 ALL IN 豁免支(§3-6)的 XP 类通道;[18] 豁免窗 kernel 分支(blood_budget_levelup_blocked ALL IN let-pass)本体未改,其 cw4 M3 XP 通道由闸收窄掩蔽达成同行为(等价性:cw4 栈 LevelUp 发射必经 P72 闸,单漏斗),decision_v2 侧消费面零触;与 §1.3 stop_flag 迁移同一申报标准。
- **⑥ D1 辖域口径差申报**:设计「按下一节点型 L_c^stop 查表」落码 = 在产停升级线单一源(P1=11 不分节点型/P2=21;04 §2 行为差披露在案,重校债归重设计落码批第一批)——实现取向正确(禁第二套血线表),**指标 G 判读域随载体 = 该单一源**;设计方案 §0.3 现状描述已随批勘误。
- **⑦ 待证钩子**:档 1 filler-buy vs refresh 边际账命题(P24 残余补部署仅辖零支出域,不辖必花域帧);新鲜度 funding/line_switch 扩域候观测键判读。

## 5. 落地审处置与验证

- 需修四项闭环:D1(§4-⑥+设计方案 §0.3 勘误)/D3(本 ADR+INDEX+代码引注 ADR-NN 化,.debug 路径清零)/D4(entry 球路径 M4 写端+模块注 taxonomy 修正)/D5(A/B 脚本 G 域决策帧 hp=上一行滚动,与 segments.py `_blood_budget_levelup_events` 同口径);挂账:D2(shop 域「四发射位」计数指 shop 域内,域外写点归 §3-5 覆盖面申报)/D6(unpolluted 归因盲区头注)/D8(红清单计数随 commit 流水)/D9(套件顺序污染债,独立定位批候选,p71 锁辖本批 ALL IN 支敏感面须先清)。D7(T-167 混批 hunk 打破 prep_flag_machine:203)非本批内容,提交捆绑归编排者裁(T-167 侧修测试先行或并审同车)。
- 验证面:单帧锁 8 条(L1/L1b/L2/L5/LF/L3/L4/L7)+变异三连有牙(摘旗回退→L3 红;M6 回退→L2/L5/LF 红;新鲜度移除→LF 红);同族旧锁重推五处(引据 §2/§4-F6/F12)非跟绿;A/B 判读脚本 `tools/cw/ab_t165_leak_ladder.py`(双批 seed 不相交拒读+同池指纹核+A ≤3.5 方向线+G=0 0 容忍+D/H 只报+归因①臂计数键,合成样本自测 PASS);跑批候 T-169 重锚(污染声明:成型率/引擎周期指标修复前不测)。
