# overlay 触发登记 迭代设计·对抗审报告(无前提攻击)

> 攻击章程:iteration-design.md §7 核一 + §5 写作硬规则。全部主张已逐条对照权威源(kernel/sim/data/流程代码 + 正本与画面档)核实;本报告只写发现与证据,不写修复建议。行号语义已核对(小漂移不立案,见各条)。
> 核实面覆盖:7 份设计文档全部小节;权威源 = cw_game_state.py、cw_action_report/ 全目录、cw_gain_chain.py、cw_event_hooks.py、sim/ 三件、data/ 注册表、cw_loop.py、operations/ 抽样、game/develop 文档锚逐一打开。

## P1【打回级】deployed-merge 对现存 `TrackedBooks.deployed`(0-9 下标簿记)零认知:命名冲突 + 触面遗漏 + 「换算层退役」主张被 tracked 侧消费直接证伪

- **攻击对象**:details/deployed-merge.md「方案·目标模型」「触面清单」;design.md §2 C-合并。
- **主张原文**:"0-9 合并下标换算层退役:`deployed_idx_of(to_row, to_slot)` 类投影换算不再需要"(deployed-merge.md:27);"`deployed: Field[list[Unit]]` 单字段"(design.md §2);触面清单(deployed-merge.md:31-37)容器行仅列 字段定义/种子/快照/_write_logic_frame/_absorb_*/mutate_bench_deployed_local/detect_merge_upgrade,写方行仅列 deploy_move、sell_deployed、buy_card、gain 链、wear_equip、工具装备分支、观察链。
- **攻击角度**:①kernel 里**已有一个 `deployed`**——`TrackedBooks.deployed: list[Unit|None]` 定长 10,"表下标 = deployed_idx 动作坐标,恒稳;排归属由下标派生(0-3 前排 / 4-9 后排)"(cw_game_state.py:1921-1941,字段注释 :2266"tracked_books.deployed = tracked 上阵")。新增 `GameState.deployed` 后 kernel 内并存两个同名、**索引语义相反**的 deployed(一个 Unit.row/slot、一个 0-9 下标),设计全文一字未提该结构与命名冲突。②「deployed_idx_of 不再需要」为假:TrackedBooks.deployed 的全部写端持续消费该换算——动作随动同步(prep_actions.py:779/:789/:818"tracked 写入下标 = deployed_idx_of(to_row, to_slot)"、tool_use.py:136-143、wear_equip.py:127/:169-172、deploy_move.py:58/:92)、观察锚定写回(cw_reconcile.py:196/:216,行视图→0-9 下标)、词表执行侧(cw_vocab.py:1082/:1125/:1132)、读端(mandate.py:369 用 deployed_row_slot 换算)。换算函数本体住 cw_exec_state.py:243/:255,该文件不在触面清单。③触面清单遗漏整批 tracked 侧文件:cw_exec_state.py、prep_actions.py、cw_reconcile.py、cw_vocab.py、mandate.py、cw_sell_deployed_action.py(:57 用 deployed_row_slot)。④触面清单自己点名的 `mutate_bench_deployed_local`(:1574)其 `deployed` 形参就是 0-9 下标工作表——清单行与"0-9 世界退役"叙事自相缠绕而不自觉。
- **证据**:cw_game_state.py:1921-1941/:2266/:2273/:1574;cw_exec_state.py:243/:255;prep_actions.py:779/:789/:818;cw_reconcile.py:196/:216;cw_vocab.py:1082/:1132;mandate.py:369;tool_use.py:143;wear_equip.py:172;deploy_move.py:92;cw_sell_deployed_action.py:57。
- **后果**:实现者按触面清单施工必然漏改 tracked 同步链(或误删换算层炸掉 tracked 写端);两 deployed 并存的术语歧义无裁决。

## P2【打回级】羁绊判据与事实基座的星徽路径自相矛盾:S1b ∧ 型判据漏「卸徽失格名未消失」形态;「装备变化→S2 静默」与伙伴星徽增减面直接冲突

- **攻击对象**:details/faction-trigger.md「值域回调级联」表、「按名分解」节、「diff 粒度」节、「判据归位」表;对照 details/trigger-inventory.md §1.1/§1.2。
- **主张原文**:事实基座(用户确认 2026-09-25)——"卸下选中者星徽致其失去资格(出身阵营与持徽**两者皆失**才失效)→ 重选弹"(trigger-inventory.md:15);伙伴"穿/卸「列车同行星徽」同样改变成员资格 → 增减面同辖"(trigger-inventory.md:27)。判据侧——"S1b 巨星重选(chosen 名消失 ∧ 资格判据)"(faction-trigger.md:17);"removed 含 chosen_megastar(按名)∧ 写后资格判据"(faction-trigger.md:33);"装备变化 = remove(旧单位)+add(新单位)同名 → 名字级 S2 静默、tag 级 S1a 生效"(faction-trigger.md:63);"换排名字没动 → 天然不弹;卖出名消失 → 弹;S1b 选中者被合成(同名产物在场)名还在 → 天然不弹"(faction-trigger.md:26)。
- **攻击角度**:卸下选中者星徽 = 同名单位的 equips 变更,按名 diff 下**名未消失**——`chosen 名消失 ∧ 资格判据` 恒假,S1b 漏掉事实基座白纸黑字的用户确认形态;同一矛盾在 S2:仅靠徽章取得列车同行资格的单位被卸徽 = 成员减(应弹),而"装备变化→名字级 S2 静默"是毯式断言,把该形态一并静默。若改按键级 removed 集合再按名匹配,则"选中者被合成名还在→天然不弹"又不成立(键级 removed 含旧 chosen)。两种 diff 语义下写出的判据都无法同时满足事实基座的三个已确认行为(卸徽失格弹/合成不弹/卖出弹),判据与事实未调和。
- **证据**:trigger-inventory.md:15/:27;faction-trigger.md:17/:26/:33/:63;资格语义旁证 = screens/megastar.md §3(:16,"匹配域 = cw_chars「盛会之星」阵营派生规范名 ∪ 场上持「盛会之星星徽」的角色")。

## P3【打回级】跨详设接口契约签名不一致:faction-trigger 引用的「总纲契约 C-回调」与总纲实际文本不符

- **攻击对象**:design.md §2「跨详设接口契约」;details/faction-trigger.md「问题与约束」。
- **攻击原文**:design.md:44-47 定义四个回调,其中羁绊变更回调 = `on_board_changed(gs, old_counts, new_counts, source)`;faction-trigger.md:5 却写"总纲契约 C-回调:`on_board_changed(gs, old_counts, new_counts, added_units, removed_units, source)`,固定位置参数(用户裁定:函数禁 `*` 参数)"。
- **攻击角度**:总纲契约是章程要求"唯一必须在总纲定死的深度内容"(iteration-design.md §2.1);详设引用的契约签名混入了 `on_units_changed` 的 added/removed 参数,与总纲现行文本不一致——契约漂移已在批内发生,恰是 C-回调要防的事故形态。faction-trigger 自己的级联表又与总纲一致,即同文档内两处签名互斥。
- **证据**:design.md:44-47;faction-trigger.md:5 vs :17-18。

## P4【打回级】S6 裁定状态三处矛盾 + README ⏳ 滞后:硬规则 4(修订后全量同步复查)失守

- **攻击对象**:design.md §2 详设划分;trigger-inventory.md §4#11;register-consume.md「⏳ 待裁」「其余触发类」;landing.md 3.4;README.md。
- **主张原文**:已裁口径——"点击类(S6,用户裁定 2026-09-25 统一入登记…)"(design.md:53);"✅ 已闭(用户裁定 2026-09-25:选项 a)"(trigger-inventory.md:137);register-consume.md:59"S6 点击类(用户裁定 2026-09-25:选项 a 统一入登记)"。未裁口径(同批并存)——register-consume.md:50-52 整节"### ⏳ 待裁:S6 点击类统一入登记?…**待用户裁**";:54 节头"其余触发类(S3-S5 已收口;**S6 待裁**)";landing.md:31"S6 统一入登记(**待裁**)"。进度面——README.md:12"触发类 S1-S6 全部收口";README.md:7 详设行仍标 faction-trigger"(⏳ 讨论中:星徽装备变动链路)",而该节在详设内的标题已是"星徽装备变动链路(**经代码全量核实**)"(faction-trigger.md:48)。
- **攻击角度**:同一问题在本批文档里同时存在「已裁/待裁」两种记载,实现者无从判断 S6 是否在辖、3.4 是否含 S6;README ⏳ 标注与详设实际状态脱节,同根因 = 裁定落文档时未做全量反查。
- **证据**:design.md:53;trigger-inventory.md:137;register-consume.md:50-52/:54/:59;landing.md:31;README.md:7/:12;faction-trigger.md:48。

## P5【打回级】未定稿面遍布:landing 全部完成判据待补、deployed-merge 五条 ⏳、3.4 设计依据待详设——硬规则 2(实现者无需再设计)不满足

- **攻击对象**:landing.md 全文;details/deployed-merge.md「⏳ 待设计细节」。
- **主张原文**:landing.md:3"完成判据在设计定稿后按各阶段小节补齐(硬规则 2…当前不满足)"——自认不满足;:11"<设计定稿后补——等价判据 = 测试全量 + sim 对拍>";:19"<设计定稿后补(羁绊类含星徽装备链路收口)>";:27"<设计定稿后补>";:32"<待详设——羁绊类收口后逐类补>";:35/:43"<待>"。deployed-merge.md:39-45 五条 ⏳:Unit.row 字面量类型与校验、观察链写形、legacy 读口处置、快照/恢复 schema 升版迁移、_absorb_slot_reorder 键定义。
- **攻击角度**:章程明列「待定/讨论中/⏳/设计定稿后补」= 直接攻击点;阶段小节 = 账本唯一源(iteration-design.md §3.1),判据空缺则阶段不可立任务、不可验收。deployed-merge 五条 ⏳ 中快照迁移与 reorder 键口径直接决定 3.1 的"等价重构"能否成立,不是细节而是方案本体。
- **证据**:landing.md:3/:11/:19/:27/:32/:35/:43;deployed-merge.md:39-45。

## P6【打回级】无过程叙事违规进正文(硬规则 3 卡点:「本轮/修订后/已改」类措辞即打回)

- **攻击对象**:details/trigger-inventory.md §1.9、§1.3、§4。
- **主张原文**:"正本四处的'点两次/BoxPick'过期记载**已于 2026-09-25 勘误**(action_ops.md §4.2 / …)"(trigger-inventory.md:79)——纯变更史叙事(上稿改了什么、何时改的);"选完回商店还是备战(**用户忘记**,待实机/遥测核…)"(:42)——讨论过程内容;§4 待裁清单"✅ 已闭(星徽三连问,2026-09-25)"等 **5 处状态标记**(:127-131/:133)——裁决过程状态,过程应住对抗报告与账本、进度只住 README(iteration-design.md §5.3)。
- **证据**:trigger-inventory.md:42/:79/:127-133;iteration-design.md §5.3。

## C1【需澄清】星级派生存值的前提「场上同名角色唯一」强于代码在册不变量;判据「旧<2 ∧ 新=2」未覆盖「无→3」形态

- **攻击对象**:details/faction-trigger.md「值域回调级联」表星级行、「星级判据的天然边界」;trigger-inventory.md §1.3。
- **主张原文**:"场上银狼星级(派生存值;场上同名唯一 → 至多一只,值域 = 无/1/2/3)"(faction-trigger.md:20);"3★(2→3)不弹(只认跨入 2★)"(faction-trigger.md:24);"场上同名角色唯一(用户裁定 2026-09-25)"(trigger-inventory.md:35)。
- **攻击角度**:①代码恒稳不变量是**同名同星 ≤1**(cw_gain_chain.py:169"场上同名同星 ≤1 恒成立不变量:违例即抛"),弱于设计前提"同名唯一";若游戏允许同名异星并场上(不变量不禁止),单值派生存值(无/1/2/3)失去定义。用户裁定可作依据,但与代码不变量的落差未申报。②备战囤三张 2★ 合成 → 3★ 落备战(载体=备战最左,cw_gain_chain.py:164)→ deploy 该 3★:星级值 无→3,判据 `旧<2 ∧ 新=2` 不弹;该 3★ 从未以 2★ 身份上场、其费用档从未弹过——游戏是否弹未在待裁清单登记,事实基座亦无此形态。
- **证据**:cw_gain_chain.py:164/:169;faction-trigger.md:20/:24;trigger-inventory.md:35/:125-136(待裁清单无此条)。

## C2【需澄清】「合成签名排除规则退役」与「合成签名判据实现要点(硬规则)」同批并存,未说明后者服务于谁

- **攻击对象**:design.md §2 C-回调;details/faction-trigger.md「按名分解」「星徽装备变动链路」。
- **主张原文**:"按名分解 diff:合成/换排天然非成员变更(**合成签名排除规则退役**)"(design.md:48);"原「同帧 2×低星消失+1×高星出现」签名特判**不再需要**"(faction-trigger.md:26);同文档后文又立硬规则:"**合成签名判据实现要点(硬规则)**:签名按 (char_id, star) 子键判,禁用全键——合成装备继承使产物 equips = 三方并集,removed/added 的全键必不相等,按全键判合成签名恒失效"(faction-trigger.md:64)。
- **攻击角度**:签名特判究竟退役还是仍为实现必需?若按名/派生存值已天然分解,(char_id, star) 子键签名判据的消费者是谁、判什么,文档没有交代;实现者面对"退役"与"硬规则"两组互相打架的指令,只能自行拍板 = 硬规则 2 违例形态。
- **证据**:design.md:48;faction-trigger.md:26/:64。

## C3【需澄清】kind 词表与现役动作/画面词表不对齐:'grail'/'diviner' 无映射交代,「fate 正名」目标名未指定

- **攻击对象**:details/register-consume.md「接口」「迁移退役清单」;details/trigger-inventory.md §1.4/§1.5。
- **主张原文**:"kind: str # 'partner'/'megastar'/'planner'/'diviner'/'grail'/'aha'/'star_tome'..."(register-consume.md:16);"fate 词表正名+占卜屋补 kind"(register-consume.md:48);trigger-inventory §1.4 标题用"祈愿试炼(**wish_trial**)"(:45)、§1.5 用"命运卜者(占卜屋)"(:53)。
- **攻击角度**:现役封闭词表里祈愿 = `pick_wish_trial`(zero_writes.py:39/:133-137)、占卜屋 = `pick_fortune`"命运卜者强化三选一"(zero_writes.py:149-153),分发画面 = '货币战争-命运卜者强化'(cw_loop.py:548)、屏档 = fortune.md/wish_trial.md;新 kind 'grail'/'diviner' 与现役名各岔开一步,同物四名(占卜屋/命运卜者/fortune/diviner)。'fate' 正名后的目标名(是 'grail' 还是沿用 'wish_trial')未指定,正名动作不可实现为唯一解。
- **证据**:zero_writes.py:39-43/:133-137/:149-153;cw_loop.py:548;screens/fortune.md、screens/wish_trial.md(在册屏档);register-consume.md:16/:48。

## C4【需澄清】「装备→羁绊计数」贡献族枚举不全:漏星核猎手卡带系(无条件 +1),且未引现役单一源 cw_bond_equips

- **攻击对象**:details/trigger-inventory.md §3「星徽全域」段。
- **主张原文**:"**22 个阵营星徽**统一模式「装备者加入【XX】羁绊」(cw_equipment_data.py:110-131);骇客类「欢愉卡带(-Max)」双重计数机制(已是成员则计数再 +1——单装备贡献可 >1,tag 计算机制注记)。判据 = 注册表驱动的 tag 差,零硬编码"(trigger-inventory.md:123)。
- **攻击角度**:22 星徽(:110-131)与欢愉卡带(:228-229,"已是成员则计数+1")核实无误,但同族还有**星核猎手卡带/Max**(:226-227,"「星核猎手」羁绊计数+1。"——**无条件** +1,非成员穿戴也计数,单装备贡献同样可 >1),事实基座未列;且现役贡献建模单一源 = kernel/cw_bond_equips.py(:37-39 注释明载"欢愉卡带系/星核猎手卡带系"两分),设计全文未引该文件——"注册表驱动零硬编码"落到哪份代码/表,实现者只能猜。
- **证据**:cw_equipment_data.py:226-229;cw_bond_equips.py:37-39/:57-64;trigger-inventory.md:123。

## C5【需澄清】OpenTome 双击 bug 处置归属三处口径不一:归修复批 / 进本迭代 3.5 / 退役清单不含

- **攻击对象**:details/trigger-inventory.md §1.9;landing.md 3.5;details/register-consume.md「迁移退役清单」;design.md §1「明确不解决」。
- **主张原文**:"归**修复批**实机核后改单击"(trigger-inventory.md:78);landing 3.5 范围却含"**OpenTome 双击 bug 候选处置(实机核后)**"(landing.md:39),其设计依据 = "details/register-consume.md(迁移退役清单)"(landing.md:40)——该清单(register-consume.md:48)只列 OverlayQueue/簿记/评估器/事实事件/sim 三错,**不含 OpenTome**;design.md §1 明确不解决清单(:25-29)也未提。
- **攻击角度**:同一 bug 在事实基座说外委、在落地阶段说在内、在被指为设计依据的清单里不存在——范围边界(章程:明确不解决什么,防外溢)失守;3.5 的设计依据指向不覆盖其范围。
- **证据**:trigger-inventory.md:78;landing.md:39-40;register-consume.md:48;design.md:25-29。

## C6【需澄清】landing 3.2 范围行与详设回调族不一致:S2/S1b 住 on_units_changed,范围行只写 on_board_changed

- **攻击对象**:landing.md 3.2;details/faction-trigger.md「值域回调级联」表。
- **主张原文**:3.2 范围 ="on_board_changed 回调挂点/三判据(S1a/S2/S1b)/簿记/register 接口与容器存处"(landing.md:15);详设 = S2 与 S1b 判据住**角色变动回调 on_units_changed**、装备贡献住 on_equips_changed、S1a 才住 on_board_changed(faction-trigger.md:17-19);总纲 C-回调共四个回调(design.md:44-47)。
- **攻击角度**:按 landing 范围行实现 3.2 会只建 on_board_changed 一个回调,漏 on_units_changed/on_equips_changed——S2/S1b(本阶段判据主体)无宿主;阶段范围与设计依据内容脱节,阶段小节作为账本唯一源会立出错误任务面。
- **证据**:landing.md:15;faction-trigger.md:17-19;design.md:44-47。

## C7【需澄清】「18 动作表」引用无文件锚,本体住另一迭代 changes/ 目录(引用寿命无保障)

- **攻击对象**:details/trigger-inventory.md §1.5;details/register-consume.md S6。
- **主张原文**:"settle_confirm 一条分支全覆盖(pick_encounter next_screen = 结算档,**18 动作表 #4**)"(trigger-inventory.md:56);"18 动作表两条 + advance 两 case"(register-consume.md:52)、"18 动作表两条与 sim advance 两 case 随落地批改"(:59)。
- **攻击角度**:「18 动作表」实指 changes/2026-09-24-action-world-decl/details/world-decl.md §2 表(其 #4 行 = pick_encounter,trigger=battle_resolve,next_screen='货币战争-结算',内容核实无误),但引用既无文件路径也无迭代名;该表住**另一迭代的 changes/**——changes/ 会不定期无理由删减(项目 AGENTS.md「文档规范」铁律),跨迭代裸引随清理即死链,且正本化前它不是稳定权威源。
- **证据**:changes/2026-09-24-action-world-decl/details/world-decl.md §2(:37-:46,#4 行 :46);trigger-inventory.md:56;register-consume.md:52/:59。

## L1【低】「5 处 emit 调用」计数错误:实际 6 个调用点

- **攻击对象**:details/register-consume.md「迁移退役清单」;design.md §1 症状 1。
- **主张原文**:design.md:16"散在 5 个上报点(buy_card/deploy_move/sell_bench/sell_deployed/wear_equip)"(文件数,正确);register-consume.md:48"FactEvent/FACT_EVENT_KINDS/set_fact_event_sink + **5 处 emit 调用**整体退役"(调用数,错误)。
- **攻击角度**:buy_card.py 含两个 emit('board_changed' :184 + 'star_up' :186),全仓 emit 调用共 6 处(deploy_move:143、buy_card:184/186、wear_equip:187、sell_bench:121、sell_deployed:78);退役清扫按"5 处"找点会漏 star_up 一处。
- **证据**:cw_action_report/{deploy_move.py:143, buy_card.py:184/:186, wear_equip.py:187, sell_bench.py:121, sell_deployed.py:78}。

## L2【低】多处机制主张无就地依据标注(硬规则 1:无依据必攻)

- **攻击对象**:details/trigger-inventory.md §1.1/§1.4/§1.5。
- **主张原文**:"替换(一增一减,**被替者下场回备战**)"(:12);"触发动作落地即弹,叠备战,挡后续动作"(:17);"deploy 落地即弹,叠备战,挡出战"(:50);"行域现读黑天鹅在场(**战斗期间板面冻结**)"(:57)。
- **攻击角度**:被替者去向、各弹窗时点、板面冻结均为游戏机制主张,既无画面档/研究档节引用也无用户裁定标注(同文档其它主张均有标注,这几条裸立);硬规则 1 卡点 = 无依据标注的主张默认攻击目标。同类:§1.2"替换同名(名集不变,推断)"已自标推断,不列。
- **证据**:trigger-inventory.md:12/:17/:50/:57(对照同文档 :11 megastar.md §1、:34 用户裁定 等有标注主张)。

---

## 发现计数汇总

| 严重度 | 数量 | 编号 |
|---|---|---|
| 打回级 | 6 | P1 deployed-merge 漏 TrackedBooks.deployed(命名冲突/触面遗漏/换算层退役证伪);P2 S1b/S2 判据与星徽路径事实基座冲突;P3 C-回调契约签名跨文档不一致;P4 S6 裁定三态矛盾+README ⏳ 滞后(全量同步复查失守);P5 landing 判据全待补+deployed-merge 五条 ⏳+3.4 待详设(硬规则 2 不满足);P6 无过程叙事违规(勘误史/用户忘记/✅ 已闭×5) |
| 需澄清 | 7 | C1 同名唯一前提强于代码不变量+无→3 形态未覆盖;C2 合成签名退役 vs 硬规则并存;C3 kind 词表不对齐('grail'/'diviner'/fate 正名目标未定);C4 贡献族漏星核猎手卡带+未引 cw_bond_equips;C5 OpenTome 双击 bug 归属三口径;C6 landing 3.2 范围行漏 on_units_changed/on_equips_changed;C7 「18 动作表」无锚且住邻迭代 changes/ |
| 低 | 2 | L1 emit 计数 5≠6;L2 四处机制主张无依据标注 |
| **合计** | **15** | |

> 已核实为准确、未立案的抽样(供定稿信心,非发现):sim 三错(planner 扫备战席 cw_sim_backend.py:1502-1515、planner_fired 一次性 :743/:1492/:1498、'fate'=圣杯链 cw_sim_overlay.py:23/:41);28 候选(cw_loop.py:546-557)与 :1476 区引用;cw_factions.py:67 tiers=(2,3,4,5);cw_equipment_data.py:110-131(22 星徽)/:116(红钻+幸运星)/:119;cw_invest_data.py:166 阿哈大悦效果全文;merge_step_once:164 载体规则;buy_card.py:161 detect_merge_upgrade;wear_equip `_locate_unit` 全域/域整表重建;tool_use 冶金炉双模式/扳手清空写;sell_deployed.py:71/sell_bench.py:114 回库存;lv999_cost_tier(:2380)及双写端(deploy_move.py:134/pick_planner.py:278);事实事件三件套与 5 上报点;tracked_books/bind_session_container/note_obs_event 先例;正本更新清单全部文档锚(fields.md §3.2.3/§3.2.4、sim-design §4/§6.3、sim-wiring §六、outer_loop §2.2、action_ops §4.8、action-logic-state §3.5、open-tome.md §9、screens/README §5.3、invest_effects §0.1、aha_equip_pick/megastar §1 内容);OpenTome 双击 docstring 与正本勘误已落地(grep 点两次 零残留)。
