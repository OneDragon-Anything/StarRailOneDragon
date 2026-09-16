# 设计对抗报告·第三轮:备战访问编排 op 化

> 审查依据:`docs/develop/harness/iteration-design.md` §7(攻击三核)+ §5(写作硬规则三条)。
> 方法 = 前两轮 20 条逐条闭合核对(对照真实文件与代码)+ 无前提自找角度(试读逐阶段/文件面可开工性/
> 正本清单锚对账/行为序实证/接口契约一致性)。全部结论基于被引文件与 `src/` 真实代码逐处核对,非设计转述。

## 结论(仍有阻断项)

**仍有阻断项**——方案本体(交回契约/执行器合一/前置发射位/浮层闸内嵌)经三轮对抗已立稳,前两轮 20 条闭合 8 条;但阻断面已集中转移到落地件:landing 3.1 存在「范围-判据」自相矛盾(退役 readiness_battle_launch ∧ 不动达标臂分支 ∧ 三调用面同一函数三者不可同时成立)、两处文件面失实/缺口(prep_actions.py 路径不存在、词表与 sim 适配器无归属)、正本更新清单锚失实与缺面(session.md 载体表不存在等四处)、design↔landing 同步缺陷**第二次复发**(核三升流程级)——凭 landing 现状不可开工,未达定稿门槛。

## 前两轮 20 条闭合核验表

判定口径:**闭合** = 方案与派工面(landing)均已按修复;**未闭合** = 残留实体缺陷(注明残留在哪);**合规关闭** = 无。

| # | 前轮发现 | 判定 | 证据(文件:行) |
|---|---|---|---|
| F1 | 浮层闸退役「行为等价」申报被证伪 | **闭合** | design.md:21(方案 2「整建制内嵌:锚表扫描+遭遇 OCR 兜底,捕获面与判据原样——两调用面同保」)、design.md:29(方案 4「不退役」,清场注册表不收交互浮层依据保留)、design.md:34(行为申报已改写,被证伪旧口径消失)、landing.md:12(3.1 判据内嵌位)、landing.md:34(3.3 范围「整建制内嵌」)。方案/申报/派工三面一致 |
| F2 | 跨帧发射活性与「恰一次」未证 | **闭合** | 三子项全钉:①发射永不到来 → design.md:25「段内已访问则次帧无条件产 StartBattle(…无死循环)」;②节流/闩 → design.md:25「访问意图不经 S1 开店闩与 OpenShop 节流(旧仲裁直调 open_shop 不过闩,同形态)」,实码核验旧形态确不过闩(cw_loop.py:570 直调,无 `cw4_shopped_phase` 检查;闩消费点 = mandate.py:1220-1230);③armed 破功 → 归入合法多段再访形态(残余的申报措辞问题归 R2-8 行) |
| F3 | 仲裁意图词表形态与判定单一源未钉死 | **未闭合(残留两项)** | 已钉:意图形态 = OpenShop 扩展受限字段+两适配器同批(design.md:25,40)、帧级判定 = `in_launch_spend_zone` 直调+禁内联+对账表登记(design.md:24;cw_economy.py:306-325 明文)。**残留**:①访问内逐动作预算闸的判定源仍未点名——design.md:42 契约只写「预算闸 = 息线,值源 = kernel 派生」,未钉 = kernel `launch_arbitration_gate` 复用(cw_launch_arbitrage.py:107-132,模块头 :19-24「判定语义单一源……两面直调禁字面量散写」),op 受限访问机器(threads 闸为新增,cw_screen_prep.py:2991,3031)自写第二套闸语义的在册风险未消除;②route_tag 值域与 action_key 幂等粒度仍只字未提(cw_vocab.py:842-860:read_only 不在排除表,新字段将入键,先例可循但未申报) |
| F4 | 遥测载体与正本更新清单不完备 | **未闭合(锚失实移交 R3-4)** | [cw-op] 行去向已钉(design.md:29,37「保留,出口改 op 内受限访问处」+ landing.md:42)、分键申报已立(design.md:37)、shop.md 已列(landing.md:63)。**但**清单所列 `flow/session.md` 载体表经全文核查**不存在**(见 R3-4)——该闭合是锚在幻影上的闭合 |
| F5 | 交回契约两处实现者需拍板 | **闭合** | design.md:20「两处钉死」:①launch_fired 优先于 outcome(outcome=fail 不覆盖置位,帧锚兜底照旧申报——cw_loop.py:2194 帧锚第二入口在案);②置位点 = 统一执行器返回成功时由 op act 段落(实现通道实证可落:prep_actions.py:405-412 last_launch_ok 写点、:585-592 `_dispatch_action` 对 StartBattle 返回 emitted)。契约行 design.md:39 同口径 |
| F6 | 统一执行器契约三套异宿主语义捏合未拆 | **未闭合(残留两项)** | 已钉:逐面行为差矩阵入 3.1 判据(landing.md:12)、失败分轨以实码为准(design.md:21「具体失败语义以 3.1 审计实测现存实码为准,禁据漂移文本立规格」)、部署原子序入钉死序(design.md:21)。**残留**:①3.1 审计清单五项(landing.md:12)仍不含部署维度,审计兜不住逐面部署语义差(达标臂面每帧现读 vs 恢复局面面 `_cw_locked_sync_done` 闩,cw_loop.py:285-310);②调用面值域失配:契约写「两调用面(op 面、loop 恢复局面面)」(design.md:41),3.1 判据写「三个调用面(达标臂/恢复局面/策略终点)」(landing.md:13),调用面标记是契约入参,值域两说未并(并入 R3-1 修) |
| F7 | 前置发射位插入位次与实体面优先级未定 | **未闭合(landing 残留)** | 总纲已钉:design.md:22「entry.py 入口最前(任何 pass 之前),armed 帧连 boxes/spheres 实体面一并短路」+ 前置依赖序申报。landing.md:19 范围已对齐「入口最前」。**残留**:landing.md:21 文件面仍写「entry/mandate 任一契合位」——与总纲钉死位次矛盾的酌情措辞原样存活(= R2-9 同一残留) |
| R2-1 | 被证伪浮层闸口径残留在行为申报与 landing 3.3 | **闭合** | design.md:34 已改「浮层闸:整建制内嵌统一执行器(锚表 + 遭遇 OCR 兜底捕获面原样;弹窗帧不发射——误触防护保留,非退役)」;landing.md:34 已改「浮层闸整建制内嵌统一执行器(捕获面原样)」。三处口径一致 |
| R2-2 | 前置发射位与 S1 开店闩冲突形态未定义 | **闭合** | design.md:25 显式钉死「访问意图不经 S1 开店闩与 OpenShop 节流(旧仲裁直调 open_shop 不过闩,同形态;空转防护由段旗承载)」——三选一中选定「无视相位闩」且与旧形态等价(实码核验:cw_loop.py:570 仲裁直调 open_shop,全段无闩检查),故无行为差需申报;空转防护载体 = 段旗(与 R2-7 同载体) |
| R2-3 | 执行器钉死内部序漏部署原子序 | **未闭合(残留两项)** | 已钉:design.md:21 内部序补「**部署原子序(RunDeploy 组合)**→ 出战点击链」,与 14_p1 C1 原文含部署半边一致(14_p1:630「单一发射核(RunDeploy+StartBattle)」;实码 cw_loop.py:253-318 两面部署语义在案)。**残留**:①3.1 审计清单(landing.md:12)五项无部署项——审计兜不住(同 F6①);②逐面部署语义(op 面 = 每帧现读零 move 形态、loop 面 = sync_once 闩语义原样)仍未钉,矩阵未强制该维度 |
| R2-4 | 失败分轨引用已整删的连败停机语义 | **未闭合(派工面残留)** | 方案侧已按真值修:design.md:21「具体失败语义以 3.1 审计实测现存实码为准(start-battle.md §1 正本有漂移,禁据漂移文本立规格),两套计数不静默统一」;漂移修正已排期(landing.md:61「§1 漂移文本修正(T-286 后失败语义实况)」)。**残留**:landing.md:12 审计清单仍裸列「重发长按/连败停机」为合并项(未标注「已随 T-286 整删」——实码:cw_start_battle_action.py:20-24 整删申报、prep_actions.py:855-859 薄委托,两语义在两路径均不存在);更重者 landing.md:13 判据「既有出战行为锁全绿(含免战牌、**重发、连败停机锁**)」——sr-od-test 全量检索无此两类锁(grep 重发/连败/launch_dead:仅命中无关项;出战域现役锁 = test_cw_unified_action_3.py 点击序列/弹窗/免战族),判据指向不存在的验收物 |
| R2-5 | 遥测分键申报账实不符(7≠8 键等) | **未闭合(映射句与交付锚残留)** | 已修:8 键(design.md:37;实码核验 cw_launch_arbitrage.py:62-81 恰 8 个 KEY_)、KEY_PRECHECK_SKIP/KEY_ABANDONED_LAUNCH 退役申报(写点核验:cw_loop.py:514 与 :1985,随预检退役/达标臂拆除消亡,申报属实)、3.2 判据收窄(landing.md:27「策略宿主键写点就位(执行器宿主键归 3.1…)」)。**残留**:①「执行器/操作工宿主键(复验/发射面)写点留统一执行器」一句宿主映射仍不精确——readiness_launch_fail/giveup 留 loop 失败 streak 环(cw_loop.py:2027-2041,方案 5 保留该环)、open_failed/gate_blocked/zero_consume/cross_line 新宿主 = op 受限访问机器非执行器;②「逐键宿主映射随 3.1 审计清单交付」(design.md:37)在 landing 3.1 判据无对应项(landing.md:12 审计清单、:14 仅有「日志标签审计输出」,与 cw4_counters 分键是两类载体)——交付物无验收锚 |
| R2-6 | 帧级判定单一源钉错 kernel 函数 | **未闭合(判据行残留)** | design.md:24 已正钉:「直调 kernel `in_launch_spend_zone`(帧级「金>息线」单一源现址…);`launch_arbitration_gate` 为逐动作闸非帧级判定,不作本判定源」;landing.md:19,26 已对齐。**残留**:landing.md:25 单帧锁判据仍写「armed ∧ **gate** 命中帧 → 受限访问意图」——被降格符号在被钉死的判据行复活,与 design.md:24 直接矛盾措辞(验收锁按哪个口径写,worker 需猜) |
| R2-7 | 「每武装段恰一次」状态载体未钉 | **闭合** | design.md:25「段 = armed 连续期(StrategySession 段旗承载,先例 = cw4_reopen_armed_phase),失武装复位」;先例实码核验:mandate_state.py:339 `cw4_reopen_armed_phase` = 策略器状态对象字段(session.md:27 目标态「策略器状态 = 实现包自定义的状态对象」同宿主族),landing.md:26 判据同口径。载体/生命周期/复位点均已定 |
| R2-8 | 「行为等价(恰一次)」存在反例形态未定性 | **未闭合(申报未收窄)** | 形态已定性:design.md:25「复位后若再武装且仍命中,**允许新段再访**(合法形态例:访问内升级抬息帽 → 息线抬升 → 失武装 → 段复位 → 金仍超线 → 新段再访)」——多段再访显式合法。**但** design.md:33 行为变化申报仍写无限定全称「对外行为等价(**受限访问恰一次、发射恰一次**)」——与 :25 刚申报的合法再访形态(同条件下受限访问可发生两次)直接矛盾;承重结论两处不同步,验收按 :33 读会否决 :25 的合法行为 |
| R2-9 | landing 酌情措辞未清 + 「entry.decide()」符号不存在 | **未闭合(残留一处)** | 符号已修:design.md:22 不再引 `entry.decide()`,改「mandate 决策入口三遍编排函数(entry.py)」(实码 = `emit`,entry.py:432-443 编排①-⑥;调用链 bridge.py:105-125 → :254 decide_from_turn → :267 emit,单一入口可定位);landing.md:19 已改「入口最前」。**残留**:landing.md:21「entry/mandate 任一契合位」(同 F7 行) |
| R2-10 | 统一执行器把复验+扫描加到每备战帧例行 ⑥ 出战面,成本与拒绝语义未申报 | **未闭合(零处理)** | 本轮修订对例行策略终点面只字未提:design.md:21「两调用面同保」、契约 :41「两调用面」均未覆盖例行 ⑥ 面(landing.md:13 自己都把「策略终点」列为第三调用面);实码:⑥ = `if not out: StartBattle`(entry.py:943-944)是备战环最高频出口,现行该路径零复验零扫描(cw_start_battle_action.py:1-24 找钮→点击→弹窗收口)——合一后每备战帧等待出口新增双锚复验 + 锚表扫描 + 全帧 OCR(「遭遇其」,lcs 0.9),以及「例行帧遇浮层 → 不发射交回重判」的新拒绝语义,均未申报未评估;design.md:46「总耗时同量级」取舍只算了访问拆帧 |
| R2-11 | armed 帧宿主更换的编排前置未申报 | **未闭合(子点残留)** | 主申报已补:design.md:22「前置位依赖序:op 五段 observe/入口清场先于 decide,armed 帧编排前置为既有五段时序」(实码核验:五段序 op-layer.md:94-105、清场在观察段 cw_screen_prep.py:2154)。**残留**:观察失约子点未申报——`prep_obs_frame` 缺失 = ValueError(bridge.py:114-119),armed 发射新依赖该帧观察成功(旧形态判定只读容器不经 op),失约帧发射顺延交回重判的活性前提未写;行为变化申报列表(design.md:32-37)亦无对应行 |
| R2-12 | 过程叙事入设计正文 | **闭合** | design.md:47 取舍 4 已删「一轮对抗 F1 证伪」引导,直接以三条设计事实为放弃理由;全稿扫描无「本轮/修订后/已改」类措辞 |
| R2-13 | prep_actions 模块宪章张力未申报 | **闭合** | design.md:21「**宿主宪章张力申报**:prep_actions 宪章「不含玩法判断」——内嵌项均为画面态安全检查(浮层/复验 = 画面知识)与动作编排(RunDeploy 组合),非玩法判断,合宪;审计清单复核此界」——张力显式申报 + 合宪裁定 + 审计复核闭环(实码宪章:prep_actions.py:3-4) |

小计:闭合 8 / 未闭合 12(其中 9 条为主修复已落、残留集中于 landing 派工面与申报措辞;零处理 1 条 = R2-10)/ 合规关闭 0。

## 新发现清单(自找角度)

### R3-1 landing 3.1「范围-判据」自相矛盾:退役 ∧ 冻结达标臂 ∧ 三调用面同一函数不可同时成立
- **位置**:landing.md:6(3.1 范围「`readiness_battle_launch` 退役。边界:不动达标臂分支(其随 3.3 迁移)」)、landing.md:13(判据「合一后:达标臂/恢复局面/策略终点三个调用面走同一执行函数」);design.md:41(契约「两调用面」)。
- **问题**:实码中 `readiness_battle_launch` 全仓唯一调用点 = 达标臂分支(cw_loop.py:1976;定义 :346)。3.1 冻结达标臂分支 → 该调用点原地保留 → 函数不能删,「退役」判据在 3.1 时点不可满足;反之真删 = :1976 引用悬空,模块即坏;若以「改薄委托保留函数」解,「退役」与「调用面走同一执行函数」的判定又取决于 worker 对两个词的自选解释。三个约束两两组合必有一步靠实现者拍板,违写作硬规则 2(定稿门槛:实现者无需再设计);该阶段以 3.1 为账本任务的 criteria 预注册源(iteration-design.md §3.1),立任务即埋下不可验收判据。附带:契约入参「调用面标记」值域在 design.md:41(两调用面)与 landing.md:13(三个调用面)两说,标记枚举未定。
- **严重度**:重要(阻断 3.1 派工)。
- **依据文件:行**:landing.md:6,13;design.md:41;cw_loop.py:346,1976;iteration-design.md §5-2。
- **建议**:3.1 改写为:统一执行器落 prep_actions.py;恢复局面调用点与策略终点路径(`_start_battle` 委托)改调统一执行器;`readiness_battle_launch` **本体改薄委托**(判据「grep 无第二实现」由薄委托满足),**删除(退役)移入 3.3** 随达标臂拆除一并;契约调用面标记值域与 3.1 判据并成一套枚举(建议:op 策略面/loop 恢复局面面/策略终点面三值,或两宿主 + 面子标记,二选一钉死)。

### R3-2 3.1 文件面指向不存在的路径:operations/prep_actions.py 不存在
- **位置**:landing.md:8(「**文件面**:`src/sr_od/application/currency_war/operations/prep_actions.py`…」)。
- **问题**:实际文件 = `src/sr_od/application/currency_war/prep_actions.py`(应用包顶层;glob 全树核验:`operations/` 下无 prep_actions.py;另存在同名前缀异文件 `kernel/cw_prep_actions.py`——设计通篇引「`_start_battle` 住 prep_actions」,worker 按错误文件面找文件时,`kernel/cw_prep_actions.py` 是一个真实存在的误触候选)。文件面 = 阶段允许动的文件清单与开箱第一锚(iteration-design.md §3.1 七件之一),指向不存在路径 = 开工即撞墙。
- **严重度**:重要。
- **依据文件:行**:landing.md:8;glob 核验(两路径存在性);design.md:21(「落 `prep_actions.py`」未带路径,不受影响)。
- **建议**:landing.md:8 更正为 `src/sr_od/application/currency_war/prep_actions.py`;design.md:21 同步补全限定路径防歧义。

### R3-3 3.2 文件面缺口:词表契约变更(kernel/cw_vocab.py)与 sim 适配器映射无任何阶段可落
- **位置**:landing.md:21(3.2 文件面 = `strategies/impl/mandate_v1/`(entry/mandate)+ 测试)、landing.md:36(3.3 文件面 = `cw_loop.py` + `cw_screen/cw_screen_prep.py` + 测试)。
- **问题**:设计自承的义务面比文件面大:①受限字段 = 改 `OpenShop` dataclass,定义在 `kernel/cw_vocab.py:807-817`——不在 3.2 文件面(`strategies/impl/mandate_v1/` 之外)也不在 3.3 文件面;②「词表契约变更按 op-layer §2.5 两适配器同批给映射」(design.md:25;op-layer.md:115 明文「新动作入词表 = 先改契约(两适配器同批给映射)再落码」)——sim 适配器的意图映射文件(sim/cw_sim_actions.py 族)同样不在任何阶段文件面。worker 照文件面落码 = 无法合法完成设计要求的最小改动;越过文件面 = 违反阶段边界纪律。
- **严重度**:重要。
- **依据文件:行**:landing.md:21,36;design.md:25,40;cw_vocab.py:807-817;op-layer.md:115。
- **建议**:3.2 文件面补 `kernel/cw_vocab.py`(受限字段 + CW_ACTION_TYPES 核查)与 sim 适配器映射文件(或显式把 sim 映射划入 3.3 并在 3.3 文件面补),同时申报两适配器同批义务的归属阶段。

### R3-4 正本更新清单锚失实与缺面:四处
- **位置**:landing.md:58-65(正本更新清单)。
- **问题**:①`flow/session.md` 载体表**不存在**——session.md 全文(§0-§7)零处提及 `[cw-op]`/「发射帧仲裁商店访问」/三载体口径,其 §2 各表均为 StrategySession 字段清册(grep 核验零命中);「三载体口径见 session.md 载体表」的正本真身在 `flow/outer_loop.md:112`(op 调用流行),而清单的 outer_loop.md 条目(landing.md:58)只覆盖「§3 进入序收敛」,不含 :112 补行点口径的改写——前轮 R2 依据表把「session.md 载体表」核成 ✓ 系误验,清单沿用该误验落了锚;②`screens/README.md:92` 缺项——终结总表出战行明文「发射核 = `readiness_launch_decision` + `operations/cw_loop.py::readiness_battle_launch`(达标臂)」,发射核宿主随本迭代更换,必改而未列;③`strategy-docs/22_prep_screen.md:28` 缺项——出战行动作表触发列明文「达标臂(`kernel/cw_launch_admission.py::readiness_launch_decision`)」,触发宿主随 3.2 迁移,必改而未列;④「遥测分键面」行(landing.md:62)无正本文档路径(§3.2 格式 = 每行「正本文档:节」)——现役唯一提及该键族的 schema 面 = `game_state/决策行文件schema设计.md:192`,清单未指向任何可改文件。3.4 是收尾固定阶段,判据 = 清单清零;清单锚失实/缺面 = 收尾义务不可执行或漏执行。
- **严重度**:重要。
- **依据文件:行**:landing.md:58-65;session.md 全文(1-262,grep 零命中);outer_loop.md:112;screens/README.md:92;strategy-docs/22_prep_screen.md:28;game_state/决策行文件schema设计.md:192。
- **建议**:①session.md 行改为 `flow/outer_loop.md:112`(op 调用流行:补行点口径改「op 内受限访问出口落行」)——或先在正本把三载体口径表真正建于 session.md 再保留原行,二选一,禁保留幻影锚;②清单补 screens/README.md:92 出战行(发射核符号 → 统一执行器/策略前置发射位);③补 22_prep_screen.md:28 出战行(触发宿主 → mandate_v1 前置发射位);④遥测分键面行落实文档路径(建议 = 决策行文件schema设计.md 键归属节,或该键族正本现居面),格式对齐 §3.2。

### R3-5 design↔landing 同步残留族第二次复发(核三:升流程级处置)
- **位置**:五处残留:①landing.md:12(3.1 审计清单无部署项;design.md:21 钉死序已含);②landing.md:13(判据引不存在的「重发、连败停机锁」;实码两语义已删、sr-od-test 无此锁);③landing.md:25(「gate 命中」;design.md:24 已钉 gate 不作帧级判定源);④landing.md:21(「任一契合位」;design.md:22 已钉「入口最前」);⑤design.md:37(逐键映射「随 3.1 审计清单交付」在 landing 3.1 判据无验收锚,详见 R2-5 残留)。
- **问题**:同族缺陷 = 「design 侧修复未同步 landing 派工面」。第一次 = 上轮 R2-1(被证伪浮层闸口径残留 landing,曾以致命定级);本轮闭合核对再抓出五处同类——按核三「同族问题第二次出现 = 升架构级设计件(跨件半问)」,这不是五处独立笔误,是修订流程缺一步:设计修订后没有对 landing/正本清单做全量 diff 复查。landing 阶段小节 = 账本唯一源(iteration-design.md §3.1),此族残留的直接后果 = worker 按 landing 落码复现已被 design 否决的行为(③④)或验收锚空转(①②⑤)。
- **严重度**:重要(阻断定稿;逐处修法见各残留行,流程修法见建议)。
- **依据文件:行**:上列五处;attack-r2.md R2-1(第一复发记录);iteration-design.md §3.1、§7 核三。
- **建议**:①本轮修订时对 design.md 每一处已钉死语义做 landing 全量反查(diff 逐节对照),禁逐点补;②流程级:在 iteration-design.md §5/§6(或编排 skill 的修订步骤)增一条硬规则——「设计文档任何修订提交前,必须对 landing.md 判据行与正本更新清单做一次全量同步复查,产物 = 修订说明附『已反查清单』」,把该族缺陷从对抗审兜底改为流程自查;此为跨迭代通则,建议同步写 skill 反馈(`.debug/temp/skill_feedback.md`)。

### R3-6 方案 5「备战分支剩余」序与实码不符:恢复局面分支实际先于派发
- **位置**:design.md:30(「备战分支剩余 = 双锚守卫 → 派发 CwScreenPrep → 读交回事实置战斗窗 → 恢复局面分支(调统一执行器) → 失败 streak 环 → 环让位契约」)。
- **问题**:实码序 = 达标臂块 → 恢复候选/锁定分支(cw_loop.py:2074-2112)→ max_rounds/补给 → **派发 CwScreenPrep**(:2182,on_result 内读交回置战斗窗 :2149-2180)。设计把「派发 → 读交回」排在「恢复局面分支」**之前**,按字面重排 = 锁定帧先被派发进 CwScreenPrep 吃一轮备战交互,再进恢复局面——与 3.3 判据「非达标帧备战序零变化」「锁定局直通行为零变化」直接冲突,且该重排从未作为行为变化申报。若意图只是「枚举剩余构件」而非序,则序号箭头是误导性表述。
- **严重度**:次要。
- **依据文件:行**:design.md:30;cw_loop.py:2074-2112,2149-2184;landing.md:40,43。
- **建议**:design.md:30 改为与实码一致的序(双锚守卫 → 恢复局面分支(调统一执行器) → 派发 CwScreenPrep → on_result 读交回事实置战斗窗 + 失败 streak 环 → 环让位契约),或显式声明「枚举非时序」。

### R3-7 执行器接口契约行与方案 2 内部不同步:仍列已删语义、缺部署
- **位置**:design.md:41(「内部承载屏态复验/**重发**/失败计数/**连败停机**全语义」)。
- **问题**:方案 2(design.md:21)已把失败语义改为「以 3.1 审计实测现存实码为准」并钉死含**部署原子序**的内部序,但契约行仍枚举「重发/连败停机」两项目前在两执行路径均不存在的语义(cw_start_battle_action.py:20-24 整删申报;prep_actions.py:855-859 薄委托),且枚举中无部署——同一执行器在方案 2 与契约行是两份成员清单,实现者按契约行落码会漏部署、按已删语义造机制。
- **严重度**:次要。
- **依据文件:行**:design.md:21,41;cw_start_battle_action.py:20-24;prep_actions.py:855-859。
- **建议**:契约行改写为与方案 2 一致:「内部承载屏态复验/浮层安全检查/部署原子序/出战点击链;失败语义按调用面分轨,具体以 3.1 审计实码为准」。

### R3-8 状态元信息不同步:design §0「草案」vs README「对抗审中」
- **位置**:design.md:5(「状态:草案」)与 README.md:8(「迭代设计:对抗审中」)。
- **问题**:iteration-design.md §2.1 状态枚举「草案 → 对抗审中 → 定稿」、§6 生命周期明示对抗批启动即处于「对抗审中」;设计已过两轮对抗、正处第三轮,§0 自报仍为草案,元信息与自身进度矛盾(进度唯一住 README 的纪律管进度行,§0 状态是模板必填生命周期位)。
- **严重度**:次要。
- **依据文件:行**:design.md:5;README.md:8;iteration-design.md §2.1、§6。
- **建议**:design.md:5 更新为「对抗审中」。

## 依据核验表

| 设计声称的出处/主张 | 核验 | 备注 |
|---|---|---|
| start-battle.md §3-1 战斗窗置位归外循环(design.md:20) | ✓ | start-battle.md:17 |
| 「op-layer §2.5 动作端口契约(动作无返回)」(design.md:20) | ✓(节引可再精) | §2.5 标题确为「动作端口契约」(op-layer.md:113),:116「机械执行,不做落地判定」;「执行无返回」原句在 §1.2(:26)。语义成立,前轮 R2 节次偏移注按实文收敛 |
| 14_p1 C1「RunDeploy 组合 + StartBattle 执行核,禁各写一套发射位」(design.md:21) | ✓ | 14_p1:630(单一发射核两调用面)+ cw_loop.py:253-256 docstring 同文 |
| start-battle.md §1 正本漂移(重发长按/连败停机)(design.md:21) | ✓ | start-battle.md:7 vs cw_start_battle_action.py:20-24(整删申报)、prep_actions.py:855-859(薄委托),漂移属实 |
| 段旗先例 = cw4_reopen_armed_phase(design.md:25) | ✓ | mandate_state.py:339(策略器状态对象字段);session.md:27 目标态同宿主族 |
| 「op 五段 observe/入口清场先于 decide」(design.md:22) | ✓ | op-layer.md:94-105 五段序;清场在观察段 cw_screen_prep.py:2154;bridge 链 bridge.py:105-125 → :254 → entry.py:432 |
| 帧级判定单一源 = `in_launch_spend_zone`,禁内联,消费点回 DESIGN §5 对账表(design.md:24) | ✓ | cw_economy.py:306-325(:318-320 明文) |
| 「旧仲裁直调 open_shop 不过闩」(design.md:25) | ✓ | cw_loop.py:570 直调,仲裁段无 `cw4_shopped_phase` 检查;闩 = mandate.py:1220-1230(`_emit_open_shop`) |
| OpenShop 既有 read_only 字段先例(design.md:25,40) | ✓ | cw_vocab.py:807-817;注意 read_only 不在 action_key 排除表(cw_vocab.py:845-847)——新受限字段将入幂等键,F3 残留 |
| 清场注册表不收交互类浮层(design.md:29) | ✓ | cw_screen_prep.py:159-169 |
| `_prep_anchors_hit` 预检 + KEY_PRECHECK_SKIP 随预检退役(design.md:30,37) | ✓ | cw_loop.py:511-514(唯一写点),:414-419(判定体) |
| KEY_ABANDONED_LAUNCH 随达标臂拆除退役(design.md:37) | ✓ | 唯一写点 = cw_loop.py:1985(仲裁消费后 stale 弃射分支,:1977-2009) |
| `launch_arbitrage_*` 8 键(design.md:37) | ✓ | cw_launch_arbitrage.py:62-81 恰 8 个 KEY_ 常量 |
| 契约「两调用面(op 面、loop 恢复局面面)」(design.md:41) | ✗ | 与 landing.md:13「三个调用面」不一致——R3-1 一并修 |
| 3.1 文件面 `operations/prep_actions.py`(landing.md:8) | ✗ | 路径不存在;实际 `src/sr_od/application/currency_war/prep_actions.py`;同前缀异文件 `kernel/cw_prep_actions.py` 在册——R3-2 |
| 3.2 词表/sim 适配器文件面覆盖义务(design.md:25,40) | ✗ | OpenShop 在 kernel/cw_vocab.py:807-817、sim 映射面均不在 landing.md:21,36 文件面——R3-3 |
| 正本清单 `flow/session.md` 载体表(landing.md:64) | ✗ | session.md 全文零命中([cw-op]/三载体/发射帧仲裁商店访问);真身 = outer_loop.md:112——R3-4(前轮 R2 依据表此行误验 ✓) |
| 正本清单完备面(landing.md:58-65) | 部分 | shop.md:45 spend_gate 行 ✓、outer_loop.md:90 达标臂行 ✓、26_battle_settlement.md:8 ✓、start-battle.md:7 ✓ 均在列;缺 screens/README.md:92 与 22_prep_screen.md:28——R3-4 |
| cw_launch_admission 消费面 = cw_deploy_logic + cw_screen_deploy(design.md:48) | ✓ | cw_deploy_logic.py:1087,1512 + cw_screen_deploy.py:30-33(另有 flow.py:294,列举未穷尽但方向属实) |
| 「达标臂四段 ≈150 行」(design.md:9) | ✓ | cw_loop.py:1887-2045 ≈ 160 行,量级成立 |
| 「既有出战行为锁…重发、连败停机锁」(landing.md:13) | ✗ | sr-od-test 全量检索无此两类锁;出战域现役锁 = test_cw_unified_action_3.py(点击序列/弹窗确认/免战子态/免战牌递减)——R3-5② |
| 「mandate 决策入口三遍编排函数(entry.py)」= 可锚定入口(design.md:22) | ✓ | `emit`(entry.py:432-443);⑥兜底 = entry.py:943-944;counters 初始化 = entry.py:448-449(前置位与初始化的相对位次未钉,归 R2-9 残留注) |
| 方案 5 剩余分支序(design.md:30) | ✗ | 实码:恢复局面(:2074-2112)先于派发(:2182)——R3-6 |
| design §0 状态「草案」(design.md:5) | ✗ | 与 README.md:8「对抗审中」不同步——R3-8 |

---

*报告完。仅新增本文件(attack-r3.md),未改动其他任何文件。*
