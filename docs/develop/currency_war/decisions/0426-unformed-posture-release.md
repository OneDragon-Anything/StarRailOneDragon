# ADR-0426:未成型期姿态泄息通道(release)——FLIP 双谓词辖域、预算三方合并与死分支教训

- 日期:2026-08-28
- 状态:accepted(开臂 commit `2232c640`;编排者审定)
- 谱系:设计 `.debug/temp/currency_war/w328_unformed_posture/DESIGN.md`(v3);实现 `66b014bd`;断链修复 `61d16733`;V_D 息损项闭合 `940b7a96`;开臂 `2232c640`
- 关联命题:math_proofs P11(泄息义务存在性前提)、P13(位面末窗特例)、P17(A/B 度量合法性,`docs/game/currency_war/research/proofs/p17-ab-hp-measure-legality.md`)、P18(门辖帧集合过滤不变式,`p18-release-gate-no-interest-sell.md`)
- 同批姊妹篇:ADR-0427(目标外同名副本 press 通道;两通道为「凑档」病灶的买/卖两侧互补治理,验证同池同口径,互引见 Consequences)

## Context(为什么)

run48(局 `run_20260827_194456`)暴露 P1 出口 82 金/hp3 的危局:未成型期溢余金被攒息规则锁死,而溢余段(金 > 利息上限线)的持有边际恒等于 0——P11 已证这是参数无关的确定性结论。因此「泄息通道必须结构性存在、预算恒 = 溢余段」不需要重证,需要的是姿态层落地:什么时候花(谓词)、花多少(预算)、与既有攒息/追级/应急语义如何并存。

设计经两轮对抗修订(一轮缺口 A/B + 攻击①-⑧;二轮末窗单臂化/三方预算合并/门口径)收敛为 DESIGN v3。实现落地后又暴露一次生产链教训:初版把「release 帧不卖息凑档」的意图写在了一条**永远不会执行的死分支**上,直到审查与 A/B 才暴露——本 ADR 同时记录该教训(见 Decision 3)。

## Decision(逐条)

### 1. FLIP 谓词与双谓词辖域

翻转谓词(单一源 `decision_v2/posture_release.py`):

```
FLIP = phase==FORM ∧ 未成型 ∧ g>50 ∧ hp>25
       ∧ ( 非末窗: hp < blood_margin_low_hp      —— 持续兑现臂
         ∨ 末窗:   hp − boss_tax_p75 < emergency_hp )  —— 末窗投影臂
```

- **辖区不相交**:hp ≤ emergency_hp 的应急态(`filters._is_emergency`)全权接管,FLIP 让位;[25, ∞) 归 FLIP 评估。两谓词不重不漏,防双触发。
- **末窗单臂化**:末窗锚 = 本轮 node_type==boss 的首个买相位(单轮 latch 窗,随 boss 战结束关闭)。原「round≥8」臂实证双失效——过宽(r8 非 boss 轮 14 帧套 boss 税投影语义错误)且对短位面局(r1 boss)全盲——废除。
- **boss 税分位锚**:常量 `boss_tax_p75`(语料 66 场 P1 boss 战掉血 p75=34;常量名与所装分位严格一致)。max=58 的肥尾声明为遗留风险,boss 税标定以分位数锚组进 registry,不做单点(P2 侧挂账见 Consequences)。

### 2. release 预算三方合并(义务 vs 许可)

同一帧有三个独立刷金预算来源,合并规则:

| 来源 | 语义 |
|---|---|
| FLIP/release 溢余预算 | 必须花的下界(地板):g − interest_floor |
| DP `refresh_budget` | DP 授权的可刷上界 |
| plan 层刷新帽 | 评分层可刷上界(自带 HP-gate 与档金表) |

- FLIP 未命中帧:维持现状,`min(DP, plan)` 许可取交;
- FLIP 命中帧:release 预算覆盖,`max(g−50, DP)`——**release 是义务,DP/plan 是许可;义务激活时义务优先**。血量维度已由 FLIP 谓词评估,plan 层的 HP-gate 让位,同一维度只评一次防双主。
- **release 与追级同轮并存裁决**:实证 DP 的 level_up 分支即席返回、丢弃同帧刷新预算(短路使「interest < release < level」排序作废)。裁决 = slot 守卫先于姿态选择:末窗有空位时追级无本窗边际,显式注入 `release_budget = max(g−50, DP 预算)`,姿态强制输出 release 不落 hold——防「泄息通道静默关闭」的第三路径。
- **不新增破息例外**:release 只消费溢余段,是「什么时候该破」的谓词;既有例外列举(位面末追级豁免、boss_floor)语义不变。

### 3. spend_mode 生产链教训:死分支在死栈

初版实现(`66b014bd` 前)把「release 帧不卖息凑档」写在旧攒息卖路径的 release 档分支上——但该路径的调用栈早已不产 release 态(姿态映射被 horizon 短路),**分支永远不执行,开关与测试全绿,行为却不存在**。审查链的暴露过程:

- 六问审查(W345,`.debug/temp/currency_war/w345_posture_six_review/`)设计层通过但挂条件,并发现该断链;
- 修复(`61d16733`):死分支整体删除,泄息意图挂**活栈单一源**——`posture_release.spend_gate_active` 读每轮入口写入的 `session.v3_release`,消费面(评分层息 EV 中性、生成层卖门)经此读,不在各自层重算 FLIP(防第二判定源绕开 latch)。

教训固化:**任何新姿态的下游抑制/授权必须挂在会被执行到的活判定源上**;「加了开关但栈死了」比不加更危险,因为它伪装成已实现。

### 4. 卖侧门(凑档卖抑制)

`candidates._release_sell_gate`:门辖帧内,候选生成器不产生凑息向卖档(`off_target`/`for_gold`)——P18 已证为集合过滤不变式。`free_bench` 腾席卖豁免(动机是腾 slot 非凑息);演进替换事务卖不经生成器,结构上不受辖。

### 5. 同族残留闭合:V_D 的 C_dec 息损项

门辖帧内,V_D 找件期望账的成本侧息损项(`scoring` 的 C_dec)同步计 0——与 Decision 4 同属「release 帧破息成本应为 0」的同一语义,修复 `940b7a96`,消除「卖侧拦了、买侧评分还在罚息损」的残留不对齐。

### 6. 开臂依据链

- **修复前 A/B(W347,`.debug/temp/currency_war/w347_posture_after/`,n=300/臂,v11 冻结池)**:位面末携金 >50 占比 14.33%→11.00%,Newcombe 95% 区间跨 0 不显著——零回退但主判据不动,与断链存在一致(通道名义存在、行为未兑现)。
- **度量合法性(P17)**:「P1 出口 hp」是五级下游的第三级度量,只可作度量仪读数;主门 = 带金占比(姿态专属控制变量的直接读数)与形态达标。hp 差分作主门判据不合法。
- **修复后开臂 A/B(W355,`.debug/temp/currency_war/w355_gate_ab/`,n=300/臂,同池)**:FLIP 局凑息向卖 25→4 笔(−84%),残留 4 笔经探针核实全为 free_bench 腾席(豁免面内)——断链修复在行为面兑现 → `2232c640` 开臂 `release_spend_gate_enabled=True`。

### 7. 触发面 9% 的定位(W351 复盘,`.debug/temp/currency_war/w351_flip_trigger_review/`)

触发 27/300 局(9%),逐帧条件分解证明双峰均符合设计意图:P2 首轮附近危局群(12 局,boss 战后携金 >50 带入 P2、hp 落 (25,40)、未成型 100%)与 P1 末窗群(15 局,投影臂+第三路径)。触发局 hp0 率近乎全灭**不是通道失效**——before 臂同画像局结局相同。定位声明:**作用面天然小**(人群=低血∧高金∧未成型的危局交集);要扩大覆盖须走上游(姿态参数、boss 税锚、成型判据),禁止在谓词上直接放宽辖域。本节触发面为 sim 口径;实机有一专属缺口——FLIP 唯一消费点受 hp 可读性压制(shop 开态血量区物理读不到、假帧守卫把沿用真值帧一并拒 → 实机商店帧结构性 0 触发),已拆出为 ADR-0428(hp_trusted 可信位)独立修复。

## 增补(2026-08-28):P2 预算重校裁决与 C3 概念无效(W370/W371/W376/W377)

以下为后续演进,不改上方 Decision。

### A. P2 预算参数重校(W370,`.debug/temp/currency_war/w370_p2_recalib/REPORT.md`;对抗审计=`.debug/temp/currency_war/w371_recal_attack/ATTACK.md`)

- `vd_p2_loss` 保留(P2 条件败局伤害),补精度声明(M3):SD 与 t95% CI、run 级聚类 CI、三源对照(冻结语料 / 实机存活谱 / coarse)与取沿理由入 registry 注释,撤销精度主张;受益侧仅方向修正、量级未标定,显式声明(A4,删除「93%→胜率≈0」类论证)。
- `P2_LOSS_SCALE` = 常数口径(M1a,取三源中位/CI 下界)。**结构边界(W371 A1 实证):确定性 DP 递推不得全量灌条件伤害**——「无条件≈条件」喂确定性 DP 等于每战必输全额条件伤,必死区扩大且平局裁决退化为「死→烧光」;治本件=两态递推 `(1−p)·L_cond`(挂账)。
- P2 平局扫描序保守化:DP solve 内 P2 槽改花费升序 + strict> 保首,全死区 V≡0 平局裁决=**存息**(不再烧光);P1/P3 槽逐位不变。
- A/B(M4 判据,n=150/臂,池指纹 `7af8197782d42c05`):P2 支出姿态占比 1.7%→15.5%、V_D 触发率 2.26%→4.07%(行为面显著);终局面零回退(功效不足,只作冒烟)。保留新参数。
- 本 ADR 的 release 门波及:无——W376 各臂 P17 回退守卫(含 P1 末窗金>50 占比)全部不劣,release 通道不受重校影响。

### B. C3(濒死带支出收窄)概念无效裁决(W376,`.debug/temp/currency_war/w376_c3c4_gate_ab/REPORT.md`)

本 ADR 挂账 2 的 C3 打回项(重设计=`.debug/temp/currency_war/w373_c3c4_redesign/REDESIGN.md`)经 W376 开臂 A/B 裁决为**概念无效,不开臂**:通道活着(87.67% 局有濒死帧、三类删除合计 1802 笔全按设计兑现、滤死升级反模式未复发)但濒死种子集 hp0 率差 −0.38pp 不显著、死亡局 P2 存活轮数分布未后移。机制解释:**濒死帧的定义就是「再输一场即死」,省下的金在下一场开打前来不及变成板面战力**——收窄删支出不改变下一战胜负。裁决:`dying_band_account_enabled` 默认关维持(开关本体是 W373 结构先行件,删除原因通道仍被检查网与测试锁消费)。杠杆定位转上游:P1 出口血量管理与 P2 成型提速(W350 §7 两段拆解);W377 连胜动力学(`.debug/temp/currency_war/w377_streak_dynamics/REPORT.md`)量化出口 hp 为第一杠杆(前 5 轮胜场数,投入产出比 >9:1)。C4 的接线与重测见 ADR-0429(含其 2026-08-28 增补节)。

## 增补(2026-08-28):FLIP 实机触发三断点修复链

以下为后续演进,不改上方 Decision。定位链:Agora 定位报告 `.debug/temp/currency_war/w378_flip_missing/REPORT.md`(断点一)与 `.debug/temp/currency_war/w390_flip_bp2/REPORT.md`(断点二);修复 commit `c65ea6f1`(断点一)与 `9a01a3d0`(断点二);断点一细节归 ADR-0428。

### A. 断点一:假帧守卫把沿用真值帧全量拒绝(ADR-0428)

shop 开态血量区被 UI 遮挡 → OCR 恒空 → `reconcile_hp` 返回「沿用 last_hp_real 真值 + `hp_readable=False`」→ `flip_hit` 假帧守卫把两种语义不同的 False 混拒,实机 **26/26 个 P1 商店决策帧**全量拒绝,FLIP 唯一消费点(shop `decide_prep`)结构性 0 触发。修复 = GameState 新增 `hp_trusted` 可信位区分「沿用真值 vs 兜底 100 假值」,守卫改 `hp_readable or hp_trusted`;兜底帧 hp=100 时两臂(投影 100−boss_tax_p75≥emergency_hp / 持续臂 100<blood_margin_low_hp 不成立)天然不命中,无误触发面。**sim 不可见风险面实锤**:sim 的 state.hp 恒可读 → 触发面 27/300 正常,该缺口是实机专属、sim 完全不可见——ADR-0426 §7 已预警的「实机静默收窄」被证实为 100% 收窄。

### B. 断点二:末窗投影臂被相位门错误辖域(相位门重排)

断点一修复后第 3 例仍不触发,定位到 `flip_hit` 相位门:末窗投影臂被 `phase≠FORM` 门**整体包住**,而其机制理由「hp−boss_tax_p75<emergency_hp → 战后必入应急带」是**保命义务,与成型相位无关**(hp 不读 form_ok)。实机帧(posture_release.py 注释锚定的进店帧):phase=SPEND / hp=38 / gold=67(溢余>interest_floor)/ 投影 4<emergency_hp 命中,被相位门短路;同帧第三路径(slot 守卫第三路径)又被 `deployed<cap` 挡住(cap 满员 6/6)——两条臂双盲,release_directive 返回 None,泄息通道结构性静默。修复(`9a01a3d0`)两件:

1. **flip_hit 重排**:可信位/plane/gold>floor/hp>emergency_hp 四门前置,末窗投影臂移到相位门之前(相位无关),持续兑现臂维持 FORM 辖域不动;
2. **第三路径(规则 1)同步前移 + cap 满员规则 2 承接**:投影臂前置后,`release_directive` 的第三路径(末窗 slot 守卫压 level、显式注入泄息预算)必须先于 FLIP 判定——其理由(新槽位下位面才兑现)同样相位无关;cap 满员帧(slot 守卫 False)落 FLIP 命中后的并存裁决(追级与泄息同轮共用溢余预算,DESIGN §②规则 2)。

附带漂移已声明:FORM 末窗 slot 守卫帧从「level 保留」变「第三路径压制」(与设计规则 1 原文一致)。

### C. 防回归:三层锁 + 6 锁

三层锁:①hp_trusted 语义/写入端**源级派生锁**(写入端唯一=read_game_state,派生式钉死);②**相位无关 r9 形态 fixture 锁**(实机观察局 r9 进店帧形态:SPEND 相位+末窗+投影命中必触发,hp 高于投影带帧拒绝);③**兜底帧不回归锁**(开局无真值 100 兜底帧两臂仍拒)。合计 6 锁(相位无关锁+非末窗零漂移锁+cap 满员规则 2 锁+旧死区锁改写等),W391 批 35 passed、全量 2303 passed/0 failed、ruff 干净(commit `9a01a3d0` 描述)。

### D. 实机观察结论

- **修复前**:3 例实机观察局(run `20260828_031008` / `20260828_040618` / `20260828_060339`)r9 同形态(未成型或刚成型 + boss 末窗 + 溢余金 + 投影命中)均不触发——三例同根因链(前 2 例断点一、第 3 例暴露断点二)。
- **修复后**:释放通道首启从观察局⑦起;有效性判据 = shop 帧遥测影子行 tag 出现 `'release'`(release tag)+ **泄息去向分项账**(预算金逐笔去向:刷新/追级/结余,W385 A5 要求的账式口径)。

## 增补(2026-08-28):C3 濒死带定谳清理(删码留档;W388 分通道补账后裁决)

以上增补 B 节裁决「概念无效,不开臂、默认关维持」后,W388 分通道补账(`.debug/temp/currency_war/w388_crisis_channels/REPORT.md`,三分通道全负:帧级配对存活差恰 0.0000/金去向非囤积/混杂归因不成立)补齐了门所需的最后证据——开臂前置已永不满足 ∧ 概念已定谳 → 按策略开关生命周期第 4 态执行定谳清理(评估=`.debug/temp/currency_war/w407_c3_cleanup_eval/REPORT.md`)。本节只记清理决策与范围,不重复否决论证。

### 删除清单

- **生产面**(`decision_v2/filters.py` + `registry.py`):`dying_band_account_enabled`(+注释块)/`dying_band_active`/`_next_battle_loss`/`filter_candidates` 濒死段(BuyCard 'hoard_buy'/RefreshShop 'blind_refresh'/LevelUp 'levelup_no_deploy' 三删因)/`dying or c1` 条件改纯 `c1`/链日志 `dying_band` 字段。
- **改名**:`dying_band_high_cost_floor` → `directed_refresh_high_cost_floor`(消费点 `filters._refreshable_names` 同步;取值与消费语义不变,消 C3 幽灵命名)。
- **测试面**:`test_cw_p2_survival_band.py` C3 段 8 锁+夹具;`test_cw_w373_c3c4_redesign.py` C3-L1~L6 与 `_next_battle_loss` 导入及阈值/桶位断言;`test_cw_adr0293_calibration.py` 默认关断言改 `not hasattr`、字段账注释收敛、registry hash 锁同步。
- **新增锁**:定谳卫生锁(已删符号 `not hasattr` + 共享面健在:损血表仍被 C4 投影消费、`_deploy_free(_after_merge)`/`_refreshable_names`/`hp_decision_trusted` 仍供 C1)。

### 共享面边界声明(删而不伤)

`p2_node_loss_table`/`node_loss_kind`(归 C4 投影,消费面双降单后表述随批改写)、`_deploy_free(_after_merge)`/`_refreshable_names`/`hp_decision_trusted`(归 C1 判据与 FLIP 守卫)全部保留;C3 专属结构(触发谓词嵌套应急带+损血查表包装)不含 C1 缺失的任何结构,可复用残余(Δp_board 符号谓词/合成豁免完备式/刷新名集)已由 C1 段经共享 helper 承载。

### 行为不变量与复活条件

- **零漂移不变量**:被删开关默认恒 False,删除=恒 False 分支移除——C1/FLIP/C4 默认行为逐位一致(全量 CW 测试回归验证,registry hash 锁同步)。
- **复活条件(显式)**:仅当游戏机制使「濒死帧支出可跨多轮备战变现」(如多轮备战窗/出战前可多动一轮)时概念才可复活;届时从本 ADR 增补 B + W373 REDESIGN + git 历史重建,不复用删除前代码。

## Consequences

- **正面**:溢余金死资本(P11)有了结构性出口;凑档卖 −84% 且残留全在豁免面;V_D 成本侧口径对齐;触发面逐帧可解释。
- **负面/边界**:触发面窄是设计内声明——主判据(带金占比)在 W347 口径下不显著,通道价值兑现依赖断链修复后的行为面(W355);hp>25 与应急带的边界帧(25 附近抖动)由假帧不评估 + 单轮 latch 防振荡,跨边界语义不保证连续。
- **挂账**:
  1. **boss_tax P2 标定**:P2 期 boss 税无语料(语料成型局为 0,对照做不了),`boss_tax_p75` 仅 P1 标定;分位数锚组 {P50, P75, P90} 进 registry 待 P2 语料。
  2. **W363 打回项独立演进**:对抗审计(`.debug/temp/currency_war/w363_c3c4_attack/ATTACK.md`)打回了 P2 生存设计的 C3(濒死带「期望账」支出收窄——授权/删除清单与 Δp 账无推导关系)与 C4(换线存活轮数门——轮单位语义错 + 删失偏差反保守)。两者骨架成立、数学内核须重做,**拆出为独立演进,不属于本 ADR 辖域**;release 谓词与门不受其影响。
  3. 与 ADR-0427 的关系:本 ADR 治「凑档」的卖侧(门辖帧不卖息凑档),ADR-0427 治其买侧(凑档带副本从被拦转放行);两通道共用的经济卫生锚(破息轮次/溢余滞花)在 ADR-0427 的 A/B 中同批观测且改善,互为旁证。

## 增补 C:release 花后金下限=boss_floor,与息基指标的关系(边界声明)

- **边界**:release 授权链的花后金下限是 `boss_floor`(P1 出口金生存边际,r278 破息地板),**不是 interest_floor(50)**。预算取 `max(泄息义务, DP 预算)`(义务=金−interest_floor;DP 预算臂无息基下限保护),故授权范围内合法跌破息基、下探至 boss_floor 属设计内行为;跌破 boss_floor 才是越权信号。
- **与息基验收指标的关系**:release 帧(泄息授权窗)不计入息基达标率分母——息基达标率度量常态帧过程纪律,不是泄息义务窗的下限;[28]「息基保住」与 FLIP 保命义务在末窗投影命中时由 boss_floor 兜底衔接。
- **实证**:位面 1 末窗投影命中局两次泄息谷值(26/40)均 ≥ boss_floor,逐帧复算为预算臂授权行为(保命义务相位无关,增补 B)。
- **遥测缺口(挂账)**:逐笔刷新的授权说明串只进运行日志不进 decisions 行;release 帧 dp_posture 只落 tag 字符串、DP 原姿态(含预算额)丢失——建议 decisions 行补记 release 帧 (budget_gold, spent) 快照并保留 DP 原姿态影子。另:刷价若轮内递增,预算按创建帧 cost 快照折算 roll 数有失真面(现网刷新价恒定语义下无实害,留观察)。

## 增补 D:FLIP 谓词简化为溢余判定(血量维度退场;经济循环总模型吞并)

- **决策**:FLIP 谓词由「低血∧高金∧未成型」的危局交集谓词(§7 自认触发面 9%)简化为**溢余判定** `g > R*(储备线)∧ C_t>0(存在正 EV 转化帧)∧ 非应急`——血量维度(hp<40 持续臂/末窗投影臂/可信位守卫)整体退场,P3 并入辖域,相位门删除。设计单一源=经济循环总模型(ADR-0445):溢余段持有边际恒 0(息帽截断)→ 强制转化弱占优的论证不依赖血量与成型相位;旧谓词与已成型 SPEND 帧互为死钱盲区(W471 §2.3)。
- **保留不变**:应急带让位(辖区不相交);boss 窗花后 boss_floor 下限(增补 C 边界);预算三方合并结构与 latch 单窗;第三路径(slot 守卫注入,溢余基改 R*)。
- **第 4 态清理(同批)**:`release_enabled`/`release_spend_gate_enabled` 两开关被总模型吞并,删字段+消费门恒接线;W355 开臂 A/B 的结论(凑档卖抑制)由恒接线语义继承。溢余基由息线 50 收窄为储备线 R*=50+窗口内排程升级费(息基守卫只辖 g≤R* 常态帧,零漂移锚=I-1)。
- **判据**:W471 DESIGN §1.4/§2.3/§3.4 + W481 对抗审计 A-3(谓词替换优先于 DP 罚项:改动面小、行为面可单帧锁、不引二阶行为风险);锁面=test_cw_w332b_release 重推重写(旧血量/辖域语义锁按锁的存在性纪律判定为被本增补取代)+ test_cw_economy_cycle_pair_signal 新锁;ADR-0445 详账。
