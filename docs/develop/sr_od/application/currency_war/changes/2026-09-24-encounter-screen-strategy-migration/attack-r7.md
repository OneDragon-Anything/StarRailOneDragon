# 遭遇迁移设计 对抗审查报告(第七轮)

> 攻击对象 = 本目录 design.md / landing.md / README.md 三件。此前轮次报告未读未采信(隔离声明:全部发现由本轮独立直调得出)。
> 判据源直调:00_framework.md §1(宪法五/六原文)、01_math_framework.md §6(【拍】定义/三要件/禁域条款/分界条款原文)、04_survival_budget.md §7 裁定表第 9 行、screens/op-layer.md §1.4、proofs/p64-encounter-dstat-static-map-uncalibratable.md(辖域原文)、math_proofs.md 索引 P15/P26/P85 行、proofs/validations/P9_VALIDATION.md:10、iteration-design.md、strategy-work.md、项目 AGENTS.md;先例批(invest-env / supply)design 直调;现役代码逐符号直调(文件:行 见各条);sr-od-test 显式 grep(测试仓被 gitignore,主仓 grep 不覆盖,已单独直调);全仓消费面 grep。
> 结论摘要:设计主体事实面直调**全部属实**(逐符号核验清单见「零发现面申报」);发现集中在 landing↔design 同步、跨批同族面、章程修订时序三处治理面。

## 发现清单

### R7-F1 [严重度:高] landing 3.3 正本更新清单的 31 号稿「数学挂账」集与 design §2.9 失同步,且含一项与「不再挂账」定谳正面矛盾的清单行
- 位置:landing.md「正本更新清单」首行(31 号稿行);design.md §2.9(31 号稿段)、§2.5、§2.12 锚 7
- 发现:两份清单的挂账集不一致——design §2.9 的数学挂账 = {比值分支复活=浮层读数通道批, E-3 标定〔注入位=策略层〕, EV 形态挂 P26, 档位↑⇒奖励价值↑ 采样验证, P2 序列两源对账, 窗口战斗类变体触发器};landing 清单 = {档位↑⇒奖励价值↑ 采样验证, **流程防线挂账交接**, 窗口变体触发器, P2 序列对账}。差异两面:①design 独有的三项(比值分支复活/E-3 标定/EV 形态挂 P26)在 landing 清单缺失——landing 阶段小节 = 账本唯一源(iteration-design.md §3.1),3.3 照单执行则 31 号稿缺三条在册挂账;②landing 独有的「**流程防线挂账交接**」与 landing 3.2 自己的定谳申报「防线已随本阶段落……**不再挂账**」(landing.md:26)及 design §2.5 防线随批落、§2.12 锚 7「持续重现 = OCR 读缺回观察批」(哨兵,非挂账)正面矛盾,系防线从「挂账方案」改「随批落」后的残留旧口径——正是 iteration-design.md §5.4 硬规则点名的失同步形态。
- 修正方向:landing 清单对齐 design §2.9(补比值分支复活/E-3 标定〔含 fill 双定谳激活义务,见 R7-F9〕/EV 形态挂 P26 三项;删「流程防线挂账交接」或改写为「实机锚⑦哨兵判读交接」);定稿前按 iteration-design §5.4 做 design↔landing↔README 全量反查。

### R7-F2 [严重度:中] cw_difficulty_account「孤儿申报」按符号为真但模块级不完备——漏报 GROWTH_PER_STREAK 的 sim 活消费,未来物理删除批照此申报删模块即破坏 sim
- 位置:design.md §2.7(孤儿申报条)
- 发现:申报原文「marginal_value 唯一消费链 = 被删的 encounter_tier_score;DifficultyAccount 全仓零生产消费」两条**符号级陈述经直调为真**(marginal_value 生产消费仅 cw_survey19_hooks.py:14/24;DifficultyAccount 类零外部引用;测试仓零命中)。但该模块常量 `GROWTH_PER_STREAK` 有活消费:`sim/cw_sim_enemy.py:33-35` import、`:128` 参与伟大征服特殊加成计算。「孤儿态」叙事自然导出「模块可整体物理删除」,而 design 明言「物理删除归后续清理批」——本申报正是彼批的删码依据,照单执行 = sim import 断裂。
- 修正方向:孤儿申报补注「模块常量 GROWTH_PER_STREAK 有 sim 活消费(sim/cw_sim_enemy.py:33/128);后续物理删除批辖域 = DifficultyAccount/marginal_value/encounter_tier_score 符号族,常量留置或与 sim 消费同批迁移」。

### R7-F3 [严重度:中] 补给链现役存在同款「建议刷 ∧ 锚读缺 → 重调仍 Suggestion → 零点击终结交回」无界循环面(30 批已落地),本批识别同构风险并为遭遇落防线,却未申报、未挂账补给侧孪生面——跨件半问缺位
- 位置:design.md §2.5、§2.11(批间协调);对照 `operations/cw_screen/cw_screen_supply_node.py:283-290`
- 发现:design §2.5 对遭遇判定「外循环对该循环无防护(直调属实:`operations/cw_loop.py:462-482` `op_fail_redispatch_tick` 任一 op ok 即整窗清零,零点击 round_success 不计数)→ 卡死一条龙级风险 → 防线随批落(round_fail 交回)」,论证成立。但同构面在补给链**现已在产**:30 批落地后 `supply.decide` 可返 Suggestion(`supply.py:126-131`,三级全空 ∧ 容器 left≥1 残值),`cw_screen_supply_node.py:283-290` 现役即「对照闸拒绝(含锚点缺)→ 重调 → 仍 Suggestion → 零点击终结交回」,无界重进循环面与 design §2.5 描述逐字同构;supply 批 design §2.4 当时申报「op 层零行为改动」。本批三件均未提补给侧孪生面——同族修法第二次出现未触发架构级归问(AGENTS.local 跨件半问),也是「防线只落一半」的口径残留。
- 修正方向:design §2.11 或 §2.12 登记「supply 链同款防线」挂账(照本批 §2.5 同构论证,op 层一处行为改动,归补给批收口或独立小批);并在 §2.5 注明遭遇防线为该族首件、补给孪生面挂账在册。

### R7-F4 [严重度:中] cap=2 按【拍】登记与章程 §6 分界条款正面冲突,且「两项值过目」与「章程 §6 修订提案裁定」两道闸未绑定——存在修订未裁而值已生效的章程真空窗
- 位置:design.md §2.2(形态申报段);判据源 01_math_framework.md §6【拍】与【拟】分界条款
- 发现:章程原文(01 §6):「【拍】禁用于伪装经验拟合——凡『数值大小参与方向/闸门判断』的量归【推】/【拟】纪律,【拍】只承载『登记即立场、分差即偏好强度』的加法立场值」。cap=2 按设计自述即「数值闸门量」(§2.2:「数值/序数闸门量,按【拍】立场登记」),按现行章程不可【拍】。design 诚实申报章程缺口并以修订提案兜底(「以用户裁定为准」),禁域条款(宪法一禁域)确不涉——这部分成立。缺口在时序:§2.2③ 只把「两项值不生效」绑定到值过目(「过目未过 → 该两项不生效」),未绑定修订提案本身的裁定;若用户过目通过而 §6 修订未同步裁定,cap=2 即以现行章程明确排除的形态落入决策闸门(【拟】无 CI 数据、【推】无推导,两者皆不可得 = 未登记形态消费,strategy-work.md §1「新增任何数字前先答属于哪一类,答不出 = 不许落码」同判)。
- 修正方向:§2.2③ 改为单一裁决门——「章程 §6 修订与两项值同场裁定;修订未过 = cap 不落码,遭遇选档维持最低档 fail 向(现役暗装等价保守形态)」;31 号稿裁定登记节同场记录两项裁定结论。

### R7-F5 [严重度:低] 状态纪律与时态残留:landing 3.2「落地检查项」以完成时态申报,与 README「落地:未开始」及同文件范围段冲突;design §2.5 内部残留一条被本节防线推翻的「零行为改动」句
- 位置:landing.md 3.2「落地检查项 → 已定谳申报」段;README.md「进度」节;design.md §2.5 第二条
- 发现:①landing.md:26「防线**已随本阶段落**……**不再挂账**」为完成时态,而 README.md:10「落地:未开始」、landing 3.2 范围段自身写「**随批落**」——检查项段被写成验收后状态,违反「设计/落地文档正文不写进度」(iteration-design.md §4);②design.md §2.5 第二条「op 层零行为改动(仅注释收口,§2.8)」与同节第三条防线(op 层一处行为改动)及 §2.8「防线一处」残留矛盾,应读作「除防线一处外」。
- 修正方向:landing 检查项段改「本阶段应落;验收时核『防线后不再出现零点击循环形态,出现即回设计层』」;design §2.5 第二条改「除防线一处(见下条)外 op 层零行为改动」。

### R7-F6 [严重度:低] README 进度链漏列 attack-r6.md(文件已在盘),对抗报告链断档
- 位置:README.md「进度」节
- 发现:README.md:9 报告链 = attack.md · r2 · r3 · r4 · r5;glob 直调本目录实存 `attack-r6.md`(未列入)。README 是进度唯一源(iteration-design.md §4),链漏 = 后续轮次对账缺口(本轮为 r7,亦依赖链条完整)。
- 修正方向:README 报告链补 [attack-r6.md](attack-r6.md)(及本轮 attack-r7.md)。

### R7-F7 [严重度:低] 画面文档收口范围漏「刷新闸拒绝/重调行为叙述」句:防线落批后 screens/encounter.md 的两处现役行为描述即过期,3.3 清单只点名「决策委托/算法描述句」
- 位置:design.md §2.9(画面文档策略指针面);landing.md 正本更新清单末行;对照 `docs/develop/sr_od/application/currency_war/screens/encounter.md:30/:67`
- 发现:encounter.md:30(动作表刷新行)与 :67(刷新单次条)现文均为「重调仍建议刷新(闸数据不一致)→ **零点击终结交回**」——3.2 防线落地(round_fail 交回)后即失实;design §2.9 对该文档的收口范围写「(如含 **kernel 决策委托句**)」、landing 清单写「**决策委托/算法描述**句」,均未辖刷新闸行为叙述句。「已知点全列 + 末阶段全仓复扫兜底」可兜底,但已知点清单既然点名到句,应列全。
- 修正方向:design §2.9 / landing 清单的画面文档面补「刷新闸拒绝/重调行为叙述句(随防线改写)」;docs/game/screens/currency_war_encounter.md 同面核对。

### R7-F8 [严重度:低] 选档主序「难度=奖励量」的依据引用链松:所引「M13 competitors 节点表」该行无此直陈,游戏原文直陈句在 currency_war_encounter.md 未引
- 位置:design.md §2.2 决策序第 6 步
- 发现:主序依据标注「『难度=奖励量』知识判据,M13 competitors 节点表」;直调 `docs/game/currency_war/data/competitors.md:123` 该行仅有「A8 常比 BOSS 凶;可刷新 1 次重置分支难度/奖励;阵容未成型选最低难度」——「难度↑⇒奖励↑」非该行直陈。更硬的在册依据是 `docs/game/screens/currency_war_encounter.md:43`:游戏原文「难度越高敌人越强大,请谨慎选择」+ 实测「右卡通常难度高、奖励更好」(两例卡面:其一=金币×2 / 其四=随机4费×3)。依据就地标注(iteration-design.md §5.1)应指向最强源。
- 修正方向:主序依据补引 currency_war_encounter.md:43(游戏原文+实测),competitors 节点表降为辅证;档位↑⇒奖励价值↑ 采样验证挂账语义不变。

### R7-F9 [严重度:低] `_FILL_EDGE_THRESHOLD=0.5` 随迁后在 fill 双定谳注入时即成活闸门数字,但全篇无其三形态登记位,31 号稿挂账集亦未明列该申报义务
- 位置:design.md §2.1(迁移面「阈值 0.5 是判据值」)、§2.3(fill 双定谳槽随迁)、§2.9(31 号稿数学挂账集)
- 发现:fill 分支现态不激活(双定谳 None,直调 `cw_encounter_selection.py:316-322`),0.5 暂不消费——迁移本身合法;但 design §2.1 自认「0.5 是判据值」,E-3 标定批注入 `PROGRESS_BAR_DIRECTION`/`BAR_SEMANTICS` 后即成活闸门数字,按章程凡闸门数字须登记三形态(现仅有「节点内归一对称中点」的结构性出处注释,代码 :284)。design §2.9 挂账集虽有「E-3 标定」,未明列 fill 阈值的形态申报义务;landing 清单(见 R7-F1)更是整组缺失。
- 修正方向:31 号稿数学挂账 E-3 标定项内明列「fill 阈值 0.5 形态申报(结构中点立【注】化出处,或随双定谳批按章程登记)」,义务随 E-3 批执行。

## 零发现面申报(实际攻击过、未发现问题的面)

**章程/裁定/证明链(逐字直调)**:宪法五/六原文与 design §0/§2.1 引用一致;【拍】三要件、禁域条款(宪法一禁域)与 §2.2 申报的「不触禁域」读法一致(冲突仅在分界条款,见 R7-F4);04 §7 第 9 行原文与 §0/§2.2 的授权辖域转述一致(「判据正本 = kernel/cw_encounter_selection.py」句确在册,§2.9 改指义务成立);op-layer.md §1.4 剩余语义(None = 拒刷)与设计一致;P64 辖域原文 = 静态 dict[敌方难度读数→stat],DELTA_T 判死确系「引申申报,非 P64 原文结论」(申报如实);math_proofs P15 行 boss 26.79 [24.25,29.23]/battle 10.45 直调相符;P26 待证双挂账(Δp_prep/L_node)与 §1「明确不解决」一致;P85 行判据 N×G×R 不消费选档输出(验收线保全申报成立);P9_VALIDATION.md:10 确证 cw_survey19_hooks「P1/P9/P8」旧编号与 math_proofs 无关。

**现役代码(逐符号直调,全部与设计声明相符)**:六标定槽全 None → 恒暗装(恒最低档+零刷新,`cw_encounter_selection.py:47-64/:367-373`);暗装门序四比值槽先于 κ_S;`_kappa_state` 三态表语义与新决策序逐位同构(含一胜一删失=边缘、fill 分支双定谳前不激活 :316-322);cap 边缘 2/足量 6 且 cap 过滤在经验层前(:417-434);主序/tiebreak(`'/'.join(o.rewards)`、(档, idx) 序 :440-444)/fail 向同构;因词三枚举与现役三因逐一对应(:396/:406/:438);`reward_tier` 四档映射与 §2.4 一致(含空文本→末档 :269-278);kernel→obs 反向依赖实证(:266-268 import obs),strategies/ 全域零 obs import、kernel 零 strategies import(grep 定谳);obs→kernel 方向在册合法(cw_observe.py:244「obs→kernel 合法向」+ cw_node_obs.py:23 现役先例);`game_start_reset` 全仓零调用(:206 唯一定义;ring 生命周期实由 GameState default_factory 字段承担,cw_game_state.py:2132/2135);`record_settlement_row` 生产消费唯一 = cw_screen_battle_wait.py:305/330;`claim_encounter_reward` 生产消费在产(cw_op_settle_confirm.py:104/136);`REWARD_TIER_LAST` 零消费;`last_normal_battles` 生产消费唯一 = 判据本体;`apply_calibration`/`reset_calibration` 全仓零外部引用;`encounter_tier_score` 唯一消费 = cw_events 旧核 :129/:145;旧核 P3 位面字面量分支(:137 `plane_of(gs) == 3`)与 EncounterOption.difficulty 三档旧 docstring(:55)实证;EVENT_PICK_TYPES/EventPick 模块级运行时构造(:538/:543)且零外部消费;EV 核 src+测试仓双零消费、`encounter.py` 的 EncounterPick 顶层运行时依赖 = import(:81)+六处签名/构造(:264/:268/:280/:306/:308/:387)+docstring(:67),与「六处」申报精确相符;bridge 顶层 import(:34)+运行时注解(:281)+refresh_used 预计算(:276-277);flow 现役调用 cw_events 旧核(:604)与 :656/:793/:807 三处保留消费;provisional 双槽(:107/:118)与头部指针句(:22);cw_vocab 两处「替代 EncounterPick」(:715/:906);cw_economy 败补「6 个决策消费点…encounter.py」句(:414);cw_difficulty_account from_strategies「挂 decide_encounter 消费批」句(:59);cw_screen_encounter 重调分支现役「仍 Suggestion → 零点击 round_success」(:180-195)与空候选/守卫结构;`read_encounter_options` affixes 恒空(:39/:73)、标题正则到「其六」、漏读「一」→1(:26-30/:56);OP_FAIL_REDISPATCH_LIMIT 语义(ok 清零/同键累加/达 5 round_fail,cw_loop.py:462-482/:858-867);sim 结算环零写端、`refresh_left=None`(:1377-1378)、ENCOUNTER_TIER_COUNT=4(:488)、占位奖励文本不含「金币」字面(:537-538,`金+N(占位,…)`)→ reward_tier 落末档逐位复核;生成契约:gen_equip_registry.py main() `write_text` 整文件覆写(:355)+「勿手改」模板头(:360/:363),三钻在注册表无派生字段(category「特殊」16 件非钻、official_category 仅财富宝钻='宝钻'),cw_obs_core 手维护宿主合理;`CwActionPickEncounterParam(idx=1)` 可构造(cw_vocab.py:716/:721),`report_action_pick_encounter_param` param: Any 鸭子取 idx(pick_encounter.py:47/:58)。

**测试面(sr-od-test 显式 grep)**:test_cw_unified_action_4.py :28/:259/:278 精确相符;test_cw_obs_arch_event_screens.py :417-419 保留面 import 零改动申报成立、:387-404 重调零点击行为测试在册(改写面真实);EV 核纯函数测试确认不存在;无验收线以遭遇选档为直接判据面(P85 行直调旁证)。

**文档面**:25 号稿头注 9 项含 1 退役注记 + §2 表行「装备」残留(§1.5/§2.9 申报属实);13:21「双轨」过期行、13:39 E3 目录行;08:18 E3 行三格结构与「待 derive/P26 锚」申报一致;strategy-docs/README.md:56 导航句现值 18-30;先例两批承接声明(env §1、supply §1 明确不解决面均含遭遇)属实;补 给批已落地证据链(supply.py 现役、25 头注 30 行、cw_survey19_hooks 仅余两件)成立;节点日程两源分歧如实(kernel P1=supply@r5+encounter@r7/P2=supply@r3+encounter@r5 均单遭遇 vs economy §10.2 P2 行 r3/r5 双遭遇、1 帧待复核),跨位面窗口算例(P2 r5 帧 = P1 遭遇行 + P2 r4 普战;普战窗 = P2 r2/r4)按 P1/P2 序列与环深 10 复算成立;combat.md §3 达标制/浮层入口②建档属实。

**核三(治本)**:§1 归层成立(判据本体驻 kernel + 三核并存 = 宪法五层;暗装门粒度 = 表示层——均有代码实证);§2 主体修根(本体迁移+三核收敛单一源、暗装门按判据线重构、钻石真值归 kernel 读数域且避开生成文件陷阱);防线属新暴露风险面的失败治理,非症状补丁;唯 supply 孪生面未触发跨件半问(R7-F3)。
