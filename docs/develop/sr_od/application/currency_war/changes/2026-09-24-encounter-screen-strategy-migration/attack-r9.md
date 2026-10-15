# 遭遇迁移设计 对抗审查报告(第九轮)

> 审查对象 = 本目录 design.md / landing.md / README.md。审查基线 = docs/develop/harness/iteration-design.md(§5 写作硬规则/§7 三核)、.dsh/skills/sr-od-currency-war-dev/references/strategy-work.md、项目 AGENTS.md。判据源全部直调:00_framework.md §1、01_math_framework.md §6、04_survival_budget.md §7 第 9 行、screens/op-layer.md §1.4、proofs/p64-*.md 与 math_proofs.md P15/P26/P85 行;现役代码逐符号直调(src/sr_od/application/currency_war/ 下 25+ 文件)并全仓 grep 删除面符号消费方(src + sr-od-test 双仓);先例两批 design;文档面 25/13/08/04/README 号稿与 screens/encounter.md、docs/game/screens/currency_war_encounter.md。零转述。

## 发现清单

### R9-F1 [严重度:高] 标定注入面 `_CALIBRATABLE` 迁移键集三处口径互相矛盾,landing 3.2 与 design §2.3 对 `D_ENC_VARIANT` 的归属直接冲突
- 位置:design.md §2.3(:109);landing.md §3.1 范围(:4);landing.md §3.2 完成判据②(:22)
- 发现:同一注入面的合法键集有三份互斥规格——①design §2.3:「apply_calibration(**合法键缩为两保留键**,未知键名抛错防线照旧)」= 2 键(fill 双定谳键);②landing §3.1:「沿用 `_CALIBRATABLE` 结构名,键集 = **fill 双键 + 立场两值**」= 4 键;③landing §3.2②:「策略层新文件沿用 `_CALIBRATABLE` 结构名、键集缩为保留键——**含装填拨盘 `D_ENC_VARIANT` 与 fill 双键**」= 3 键。其中③与 design §2.3(:107)「**`D_ENC_VARIANT` 槽保留 kernel(不退役)**……槽与装填分支原样留 kernel」直接冲突:直调 `operations/cw_screen/cw_screen_battle_wait.py:303-306/:319-323`,装填分支 import 与读的是 **kernel `cw_encounter_selection` 模块槽**;若按③把 `D_ENC_VARIANT` 放进策略层 `_CALIBRATABLE`,同一拨盘存在 kernel/策略层两份槽(第二源),未来注入极易注错份——battle_wait 读的 kernel 份恒 None,装填行为静默停在保守前置形态。①与②的矛盾还使「立场两值是否走 apply_calibration 注入」无答案(§2.2 只说「未过目期 None、过目后注入」,未指认注入口)。
- 修正方向:统一为单一口径并三处同改(建议:策略层键集 = fill 双键 + 立场两值;`D_ENC_VARIANT` 明确写入「不入策略层键集、留 kernel 槽」;立场两值的注入机制点名 = 策略层 apply_calibration)。违反 iteration-design.md §5.4 全量同步复查(定稿前逐一核每个符号/口径)。

### R9-F2 [严重度:中] design §2.5 内部残句自相矛盾:第一条「op 层零行为改动」与第三条「防线随批落(op 层一处行为改动)」冲突
- 位置:design.md §2.5(:122 vs :123)
- 发现::122「op 侧重调路径……仍返 Suggestion → 零点击终结交回,**op 层零行为改动(仅注释收口,§2.8)**」;:123 同节「处置 = **防线随批落(op 层一处行为改动)**:`cw_screen_encounter` 重调分支改为「重调仍返 Suggestion ∧ 刷新锚读缺 → `round_fail` 交回」」。同一分支两句话给出相反的行为结论。§2.8、§2.12 验收锚⑦、landing 3.2 均一致取 round_fail,可判定 :122 为防线决策加入后未清的旧口径残句。
- 修正方向:删改 :122 尾句为「重调分支处置见下条防线」;按 §5.4 对 §2.5 全节复扫。

### R9-F3 [严重度:中] design §2.7 测试面「行为断言保留」与 §2.5/landing 3.2「重调行为锁改写(零点击交回 → fail 交回)」冲突
- 位置:design.md §2.7(:148)vs §2.5(:123)/landing.md §3.2 范围(:16)
- 发现::148「同文件重调零点击行为锁(『重调仍建议刷新 → 零点击终结交回』)……随批更新(**行为断言保留**,照补给批闸叙述收口先例)」——引号内即 `test_cw_obs_arch_event_screens.py::test_encounter_refresh_gate_mismatch_zero_click_terminal` 的被锁行为(直调 :387-404:断言 `rs.is_success` + 零点击 + 零派发)。而 :123 与 landing 3.2 明文该锁「随批改写(零点击交回 → fail 交回)」。同一把锁一处说保断言、两处说改断言;若按 :148 保留断言,防线落地后该锁必红。
- 修正方向::148 改为「行为断言随防线改写(round_fail 交回 + 计入重派上限),docstring 同批更新」;与 F2 同根(防线决策加入后的全量同步复查漏改),修时一并泛化复扫「零行为改动/断言保留」类表述。

### R9-F4 [严重度:中] 窗口候选 B 的否决主论据工作示例与两源日程表不符,且同句内两个窗口口径互斥
- 位置:design.md §2.2(:96);§2.10(:173,复述为「主论据」)
- 发现:设计示例「战斗类窗口在跨位面帧会把**上一位面的遭遇行**带进本位面首遭遇帧的 κ_S 评估(如 **P2 r5 帧 = P1 遭遇行 + P2 r4 普战行**,普战窗口则 = P2 r2/r4)」。直调两源逐行核:①kernel 真值表(`cw_node_schedule.py:34-36`)P2 = battle/battle/supply/battle/encounter——P1-r7 遭遇行与 P2-r5 之间夹 P2-r1/r2/r4 **三行战斗类**,战斗类窗口 last-2 = P2-r2/r4,与候选 A 完全相同,**污染不可能发生**;②economy.md §10.2 P2 行(双遭遇 r3/r5)下,P2-r5 帧战斗类窗口 = P2-r2 普战 + **P2-r3 遭遇行**(同位面前一遭遇),也不是 P1 遭遇行。更关键:示例自身承认 P2-r2/r4 普战行在环内(普战窗口 = P2 r2/r4),则战斗类 last-2 必含 P2-r4 与 P2-r2——「P1 遭遇行 + P2 r4」与「普战窗口 = P2 r2/r4」在同一句内互斥。「上一位面遭遇行入窗」在两源任一之日程下都构不成;真实风险 = 同位面跨遭遇行入窗(双遭遇 P2 形态)与 P3 采齐后形态。维持候选 A 的结论有独立支撑(改形本身未经论证 + P2 两源分歧未定谳),但主论据的机制示例错误,变体触发器(§2.2 :97)的将来评估面会按错误机制设计。
- 修正方向:重写 :96 示例——两源分别给出真实窗口形态(kernel 源:两窗口同形无差异;economy 源:P2-r3 遭遇行入窗),否决论据改立于「窗口语义变更 = 未证的证据迁移假设 + 两源分歧未定谳」本身,§2.10 复述同步改。

### R9-F5 [严重度:中] 「未过目 fail 向」分支的归因词缺失,封闭因词枚举不闭合;裁定拒绝路径下 3.2 是否照常接线未定
- 位置:design.md §2.2(:64 归因串段 :100-102、裁定未过分支 :64);landing.md §3.1(:7)
- 发现:①§2.2 规定「因词封闭枚举(判读侧契约)」只收 `window-insufficient`/`kappa-不足`/`empty-reachable` 三因(refresh-valve 与 dark-fallback 共用);但「cap 与偏好序常量保持 None → decide 走未过目 fail 向分支(恒最低档、零刷新)」的 reason 因词全文未定义——该分支在三因之外,判读侧无法从 reason 分辨「立场未过目」与三因 fail 向,封闭枚举自宣布即不闭合。②§2.3「暗装概念退场:全槽 None 不再导致暗装」与 §2.2「未过目期 = 现役暗装等价保守形态」并存:退场的是标定型暗装,立场未过目型 fail 向仍在产(且在裁定拒绝路径下成为长期形态),两处用词需对齐,否则「grep dark-install 段不再产出」的验收判据(landing 3.2①未含此词,幸而①②集均未把它当残留词)与「暗装退场」表述会给实现者「该分支不存在」的误读。③裁定拒绝时 landing 3.1 依赖行只写「立场两值注入随过目记录在 3.2 接线**前**完成」,未写拒绝时 3.2 接线是否照常(None 态接线 = 生产行为与改前逐位一致但迭代目的落空)——停手令该问设计无答案。
- 修正方向:①为未过目分支定名因词(建议 `stance-unratified`,入封闭枚举并写明判读语义);②§2.3 补一句「暗装退场 = 标定型;立场未过目 fail 向为另一 fail-closed 形,非暗装回潮」;③landing 3.1/3.2 依赖行补「裁定拒绝 → 3.2 停手回设计层」。

### R9-F6 [严重度:中] 立场两值注入步骤无所属阶段与文件面归属,账本立任务时无家可归
- 位置:landing.md §3.1 依赖行(:7)、§3.2 文件面(:18)
- 发现:landing 3.1 依赖行要求「立场两值注入随过目记录**在 3.2 接线前**完成」,但 3.1 按完成判据以 None 态收口(其判据锁含未过目分支),3.2 文件面 15 项**不含 `strategies/impl/mandate_v1/encounter_pick.py`**——注入动作(编辑该文件常量区)落在两个阶段的文件面之外。landing 规范(iteration-design §3.1)「文件面 = 本阶段允许动的文件」「阶段小节 = 账本唯一源」下,该注入 commit 无所属阶段:执行者要么违 3.1 已收口范围,要么在 3.2 动文件面外文件。
- 修正方向:三选一并落笔:①注入归 3.2(文件面补 encounter_pick.py,范围行补「立场两值注入(过目记录凭据)」);②3.1 拆出 3.2 前置微阶段;③明确注入 = 3.1 范围内的追加交付(3.1 完成判据补「过目后注入 + 单帧锁复绿」)。

### R9-F7 [严重度:低] `D_ENC_VARIANT` 保留 kernel 后注入面悬空,未来读点定谳批的注入位未指认
- 位置:design.md §2.3(:107)、§2.7(:142 模块 docstring 重写面)
- 发现:该槽现役唯一注入口径 = kernel `apply_calibration`(直调 :72-73 `_CALIBRATABLE` 含它;docstring :12「E-3 标定批经 apply_calibration 注入」)。本批 apply_calibration/reset_calibration 随迁策略层且键集不含 `D_ENC_VARIANT`(§2.3「合法键缩为两保留键」),kernel 侧无替代注入口。比值腿复活/E-3 定谳批将来要把该槽拨到 'i'/'ii'(装填分支消费,cw_screen_battle_wait:319-321),设计未答届时从哪个口注入——直改模块常量违反「注入单点、防散注」的既有纪律(provisional.py 注入形态同款理由)。
- 修正方向:§2.7 模块 docstring 重写面补一句「`D_ENC_VARIANT` 定谳批注入位 = kernel 侧保留微型注入口(或显式申报届时直接常量赋值的豁免理由)」,或登记进 31 号稿 E-3 挂账条目。

### R9-F8 [严重度:低] landing 3.2 零残留判据存在盲区:cw_events 侧被删私有符号与 `EVENT_PICK_TYPES`/`EventPick` 摘位形态不在任何 grep 集内
- 位置:landing.md §3.2 完成判据(:22)
- 发现:①集只扫 `cw_encounter_selection.py`+`cw_survey19_hooks.py` 两文件,②全仓词边界集只收 `EncounterPick`/`F_MIN`/`G_BASE`/`DELTA_T`/`encounter_tier_score`/`REWARD_TIER_LAST`。`cw_events._option_mechanics`/`_reward_value` 若删除遗漏(保留为孤儿函数,ruff 对未引用模块级函数不报错),任何判据抓不到;`EVENT_PICK_TYPES`/`EventPick` 摘位若漏改,import 即 NameError(测试能抓),但「位已摘」的正面验证缺席。
- 修正方向:①集补 `cw_events.py` 并把 `_option_mechanics`/`_reward_value` 加入;或②集补两符号名。

### R9-F9 [严重度:低] README 进度区报告清单缺 attack-r8.md,索引落后于目录实态
- 位置:README.md(:9)
- 发现:目录内 attack-r8.md 已在册(glob 直调),README「设计对抗」行的报告链只列到 attack-r7.md——README 是进度单一源(iteration-design §4),索引不全即进度失真。
- 修正方向:报告链补 r8,本轮收尾时随 r9 一并更新。

## 零发现面申报(实际攻击过、无发现的面)

1. **删除面符号全消费方盘点(逐符号全仓 grep,src + sr-od-test 双仓)**——与设计申报全部一致,零漏报:`EncounterPick`(src 仅 cw_encounter_selection/cw_events/cw_vocab 两 docstring/bridge/encounter EV 核;tests 仅 test_cw_unified_action_4 :28/:259/:278);`EVENT_PICK_TYPES`/`EventPick`(仅 cw_events 定义处,零外部消费);`encounter_tier_score`(唯一消费 = cw_events 被删 `_score`,:129/:145);`marginal_value`(唯一链 = encounter_tier_score,cw_survey19_hooks:14/:24);`DifficultyAccount`(全仓零生产消费);`GROWTH_PER_STREAK`(sim 活消费 cw_sim_enemy:33-34/:128——§2.7 辖域注「清理批不得整模块删」属实);`REWARD_TIER_LAST`(全仓零消费,孤儿申报属实);`selection_state_of`/`last_normal_battles`(唯一消费 = 判据本体 :389/:390);`game_start_reset`(src+tests 全仓零调用——「docstring 失实」申报属实);`apply_calibration`/`reset_calibration`(零外部引用,仅 provisional.py:22 指针注释);`g_ratio`/`_kappa_state`/`_lowest_idx`/`reward_tier`/`F_MIN`/`G_BASE`/`DELTA_T`(零跨文件消费;cw_synthesis 的 `_GUANGNENG_BASE` 为子串假阳性);`D_ENC_VARIANT`(kernel 外唯一消费 = cw_screen_battle_wait :303-306/:319-323,行号引注逐位准确);`DIAMOND_EQUIP_NAMES`(消费面 = obs 自身 :216/:221/:244 + reward_tier :267/:272 + 两处 docstring(cw_events:171/supply.py:12);tests 零引用——迁移面五方申报属实)。
2. **章程与裁定引文逐字核对**:00_framework §1 第 5/6 条(判据线「换一套策略实现,会不会要不同的值/序?会 → 策略层」逐字一致;第 2 条对 P3 `plane_of(gs)==3` 分支的违例定性成立,cw_events:137 直调);01_math_framework §6(分界条款「凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律」逐字一致;【拍】三要件与设计落点①②映射成立,「过目记录归落地验收凭据」与章程 :166 同语;【拟】三要素概括一致);04_survival_budget §7 第 9 行(授权辖域 = 敌方通道 killed/进度填充率 + 持久化、「判据正本 = kernel/cw_encounter_selection.py」失配事实,转述准确);P64(辖域 = 静态 dict[敌方难度读数→stat]、条件表不在辖域、金额侧同判、点亮前置链① = 浮层读数通道——四点转述准确;DELTA_T 判死标「引申申报,非 P64 原文结论」如实);math_proofs P15(boss 26.79 [24.25,29.23]/普战 10.45 [9.59,11.24])/P26(待证明,Δp_prep 条件表 + L_node 分位口径未采)/P85(硬节点前置命题,D_N={遭遇,boss})行。
3. **行为锁与外循环防线语义**:`cw_loop.py:529/:830-858`——`OP_FAIL_REDISPATCH_LIMIT=5` 只计连续 fail、任一 ok 清零窗,直调核实;故「零点击 round_success 交回不计数且清零 → 无界重进循环面」论证成立(round_fail 计数路径 :852-858 同核);`cw_screen_encounter.py:180-195` 现重调分支与设计描述一致;补给孪生面在产确认(cw_screen_supply_node:284-291 同款零点击终结)。
4. **κ_S 三态表逐位对照**:design §2.2 决策序与 kernel `_kappa_state`(:297-323)逐位一致(双删失/一败一删失 → 不足;恰一胜 → 边缘;fill 分支双定谳 None 期不激活);cap=2/6(:418)、经验层交集顺序(先 cap 后 t≤4 分支)、tiebreak `(档, idx)` 序(:441-444)、窗口 = last_normal_battles(2) 普战口径,全部「与原核逐位同构」申报属实。
5. **sim 申报**:sim 零 `record_settlement_row` 写端、后端 `refresh_left=None`(cw_sim_backend:1377-1378)、占位四档 `ENCOUNTER_TIER_COUNT=4`/`金+20(占位…)` 不含「金币」字面(:488/:491/:536-539)→ §2.12「改前改后 sim 逐位一致 + 占位全落末档」成立。
6. **依赖方向声明**:strategies/ 全树零 obs import;kernel 零 strategies import(cw_launch_admission 仅注释性提及注入方);obs→kernel 方向已有在册先例(cw_node_obs:23 import cw_obs_core);cw_obs_core 零兄弟观测模块依赖,接收检测集无环。
7. **生成契约**:gen_equip_registry.py:355 `write_text` 整文件覆写 + cw_equipment_data.py:3-4「勿手改」头 + 三钻 category=「特殊」无标志字段(cw_equipment_data:53/:64/:65 直调)→「不可迁 data 文件、宿主 = kernel 手维护件」论证成立。
8. **文档面现状**:25 号稿头注 9 项含 1 退役注记 + §2 表行「装备」残留(:3/:19);13 号稿 decide_encounter 行「双轨」漂移(:21);08 号稿 E3 行列结构与改写方案匹配(:18);strategy-docs README :56「18-30」导航句与分篇表 28/29/30 行;04 号稿裁定 9 行;screens/encounter.md 决策委托句(:12)与刷新闸行为句(:30/:67);docs/game/screens/currency_war_encounter.md 算法描述句(:86)——§2.9 全部收口目标在册、清单与 landing 3.3 逐行一致。
9. **日程与机制依据**:cw_node_schedule P1(supply@r5/encounter@r7)/P2(supply@r3/encounter@r5)与 42 局/7 局口径;economy.md §10.2 P2 双遭遇行(1 帧待复核);combat.md §3 达标制(killed=True 蕴含达标方向安全);验收锚 6 的「P1 首遭遇帧窗口 = r4/r6」属实。
10. **接线与守卫面**:flow:594-609(refresh_used 预计算 :601-602、内务 :603、_require_slot_options :414-422)、bridge 覆写形态(:252-285)、动作链与 EncounterPick 零耦合(CwActionPickEncounterOp 静态入参词表 + report param: Any 鸭子取 idx)、cw_events 保留消费 flow:656/:793/:807、测试面保留符号 import(test_cw_obs_arch_event_screens:417-420)、空候选守卫(op :166-172)——§2.6/§2.7 相关申报全部属实。
11. **落地阶段结构**:三阶段七件齐、依赖序合理(3.1 基建无行为变化 → 3.2 原子切换 → 3.3 正本)、验收锚 1-7 分配(1-6 归 3.1 单帧锁、7 归 3.2)自洽;先例两批(supply/invest-env)承接指针(design §1「明确不解决」清单)直调属实。
12. **治本核验(核三)**:§1 归层成立——三核并存属宪法五所有权/语义层,暗装门粒度属表示层;§2 修根——判据本体迁策略层 + 三核收敛 + 门收窄,非症状补丁;`D_ENC_VARIANT` 保留有宪法五③非打分基建依据;【拍】两值未经裁定不落码,无章程真空窗;补给孪生面已按跨件半问升架构级登记(op-layer §1.4 全域条款)并给短期小批 owner/期限,合规。
