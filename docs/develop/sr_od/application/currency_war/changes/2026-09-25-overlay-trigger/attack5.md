# 第五轮无前提攻击(最终确认轮)

> 攻击章程:iteration-design.md §7 核一(无前提:不预设焦点、不信任文档主张、逐条对照权威源)+ §5 写作硬规则(依据标注/无需再设计/无过程叙事/全量同步复查)。对象 = 本目录七份设计文档。行号主张按「小漂移不立案、语义符即可」核;跨文档口径按「任何两处不同即打回级」核。本轮职责 = 核实收敛是否真实成立:零实质发现 = 合法且期望的结论,发现照实报、不因轮次放水。

## 发现 1【需澄清】触面清单「写方」行漏 pick_planner.py(真实行域写方 + 换算函数消费方)

- **攻击对象**:details/deployed-merge.md「触面清单」表「写方」行;连带 landing.md 3.1「文件面」。
- **主张原文**:「写方:deploy_move、sell_deployed、buy_card(pre_dep 快照)、gain 链(merge 工作表+落写)、wear_equip、工具装备分支、swap_deploy(:93-99,真实行域写方,消费换算函数+Unit.slot,策略侧 live 引用)、观察链(分排读屏 → 合一写视图)」;landing 3.1 文件面:「kernel/cw_game_state.py、全部行域写方/读方、观察链、测试仓相应断言(**清单见详设触面表**,不含 tracked 退役面)」。
- **攻击角度**:枚举完整性。pick_planner.py 的升费分支是真实行域写方且直读/直写 front_row/back_row 字段本体、消费换算五函数——3.1 删字段后该文件不改即崩——但写方行 8 项无一涵盖:它不是工具装备分支(tool_use/collect_ore/cw_effect_inventory 效果族)、不是 gain 链入口(cw_gain_chain)、不在 tracked 侧行、不走派生读口(deployed_rows_of 族,读口重写零消费位改动的豁免不适用——它直读字段)。3.3 文件面的「kernel/cw_action_report/(判据落点各上报)」也不涵盖(S3 判据住星级回调,pick_planner 非判据落点;且字段改名必须发生在 3.1,3.1 判据「测试仓全量绿」要求全部读写点已改)。landing 3.1 文件面以触面表为 normative 清单指针,枚举失真 → worker 按清单开工会在清单外文件撞红灯,按交付契约段停手令须回设计提请修订(iteration-design §5-2 所防形态)。
- **证据**:pick_planner.py:215-216(`front = gs.front_row.value; back = gs.back_row.value`)、:236(`work_dep = deployed_rows_to_indexed(front, back)`)、:272-277(升费分支 2★→1★ 变换后 `gs.write_logic(gs.front_row, f2, …)`/`gs.write_logic(gs.back_row, b2, …)` 写回)。全仓 `\.front_row\.value` 直读点扫描逐一归类:其余全部命中触面表已枚举类别(deploy_move:83/buy_card:79/collect_ore:117/sell_deployed:49/swap_deploy:58/tool_use:142 = 点名或工具分支;cw_effect_inventory:797/:1501 = 工具装备分支;cw_gain_chain:307 = gain 链;sim backend :1512/:1523 = 读方行点名;mandate_v1/deploy_plan.py:535 = 「策略层部署决策」;obs/cw_megastar_obs.py:283 = 观察链(obs/ 侧);cw_game_state 内部 = 容器行),唯一无类可归 = pick_planner.py。
- **缓解面(如实记)**:landing 3.1 文件面全称「全部行域写方/读方」字面涵盖该文件;3.1 判据(测试仓全量绿)与 3.2 判据(换算五函数全仓归零 grep)都会把漏改暴露为红灯而非静默通过。故定级需澄清而非打回:无两处口径冲突、判据可验收,缺口 = 派工清单失真。

## 发现 2【低】「sim 修正清单六项」计数标签与枚举原子项数不齐

- **攻击对象**:design.md §2 系统级变化 4;landing.md 3.4 完成判据;details/register-consume.md「sim 消费」节。
- **主张原文**:三处均为「sim 修正清单六项 = planner 扫描范围(备→场)/planner 簿记(一次性→每费用档)/megastar 簿记(水位→逐次上穿,降档再升也弹)/fate → wish_trial / expert → expert_invite / hack → planner 正名(…)/ fortune 补 kind」。
- **攻击角度**:计数与枚举对不上。枚举原子子项 = 7 个(扫描、planner 簿记、megastar 簿记、fate、expert、hack、fortune),「六项」标签在任何自然切分下都无法与枚举建立一一对应(按「/」切 = 6 项但第六项含 hack 正名 + fortune 补两件事;按原子切 = 7)。实现无歧义——三处枚举逐字同集、清单自足,数字只是标签——故为措辞级。第三轮曾以「计数失真」打回同段(attack3 第 33-34 行),修正后计数标签与枚举仍差一,历轮未再核此粒度。
- **证据**:design.md:39、landing.md:50、register-consume.md:64 三处枚举原文比对(逐字同集,7 原子项)。

## 发现 3【低】关键取舍含修订史指涉「2026-09-25 前稿」

- **攻击对象**:details/deployed-merge.md「关键取舍」首条。
- **主张原文**:「**完整槽位表(取)vs 单位带 row/slot 属性 + 缺席表达空位(弃,2026-09-25 前稿)**」。
- **攻击角度**:iteration-design §5-3 无过程叙事——「不写谁审的、第几轮攻击、上稿改了什么;卡点:形式检查」。取舍条目写「备选方案 + 为何放弃」是模板要求,但「(弃,2026-09-25 前稿)」中「前稿」直接指认稿次,属「上稿是什么」的修订史引用;写「(弃)」即自足。同族较轻形态:faction-trigger.md「原『同帧 2×低星消失+1×高星出现』签名匹配特判自始不存在于本设计」不指稿次、功能是本设计边界澄清,不单列。
- **证据**:iteration-design.md §5 第 3 条原文;deployed-merge.md:66。

## 发现计数汇总

| 严重度 | 计数 |
|---|---|
| 打回级 | 0 |
| 需澄清 | 1(触面清单漏 pick_planner.py) |
| 低 | 2(sim 清单计数标签;「前稿」修订史措辞) |

三条均为清单/措辞级,无接口契约冲突、无判据不可验收项、无依据缺失项;发现 1 是历轮四批 49 条均未覆盖的新缺口(文件面枚举完整性),处置 = 触面表「写方」行补一行(landing 文件面全称已涵盖,无需另行改)。

## 已核实为准确的抽样清单(定稿信心)

### 跨文档一致性(历轮打回主因,本轮全量复扫)

1. **四回调签名**:design C-回调与 faction-trigger 值域回调级联表逐参数一致(`on_units_changed(gs, added_units, removed_units, source)`/`on_equips_changed(gs, changed_pairs, source)`/`on_qualification_changed(gs, old_sets, new_sets, source)`/`on_star_changed(gs, old_star, new_star, source)`);landing 3.3 范围、register-consume「其余触发类」节归位一致(通知/判据/S3 分工同口径)。
2. **kind 词表九项**:design C-登记、register-consume kind 表、trigger-inventory §3 S6 行三处同名同集(partner/megastar/planner/wish_trial/fortune/star_tome/box_card/expert_invite/aha);landing 3.4「八个有上报的 pick + aha 特例」与 register-consume 生命周期①逐项吻合。
3. **判据归位与簿记口径**:design C-簿记 ↔ faction-trigger 判据归位表 ↔ register-consume 存处节 ↔ landing 3.3 范围四处一致:祈愿 = 首次达档一次(降档再回不弹)、planner = 每费用档一次、巨星无簿记(上穿即弹)、占卜屋 = 战斗计数;「已触发档位集合两处同型」三处同句;megastar_fired_tier「直接退役不迁移」三处一致。
4. **换算五函数归属**:design「随 tracked 消费端退役后删除」↔ landing 3.1「不含…(= 3.2,tracked 消费端在 3.1 窗口期仍用)」↔ landing 3.2 判据 ↔ deployed-merge「0-9 换算层退役」四一致;五函数名逐字同且定义确在 kernel/cw_exec_state.py(deployed_slot_no:237/deployed_row_slot:243/deployed_idx_of:255/deployed_rows_to_indexed:266/deployed_indexed_to_rows:295)。
5. **TrackedBooks 消费面五去向**:design §2.1 摘要 ↔ deployed-merge 退役表 ↔ landing 3.2 范围/判据一致,含锚定写回分支(cw_reconcile.py:426/:454-455 tracked 整表写回在册)、升星确认候选宿主不动(cw_reconcile 局旁表 :73/:89)、比较基线改主域派生(:389-390 `_tracked_sig(_books.bench/.deployed)` 现役)、tracked_account_observed 两态制(cw_game_state.py:1907-1915)。
6. **6 处 emit 行号**:deploy_move.py:143、buy_card.py:184/:186、wear_equip.py:187、sell_bench.py:121、sell_deployed.py:78 逐一命中(grep 全域恰 6 调用点 + cw_event_hooks.py:50 定义);FactEvent/FACT_EVENT_KINDS/set_fact_event_sink 三件套在册;landing 3.5 与 register-consume 退役清单两处逐字同。

### 回调契约与机制依据

7. **两段式判定提速机制**:screen_utils.py:368-373 原文核——传入 screen_name_list 只作过滤集(`if screen_info.screen_name not in screen_name_list: continue`)、按 `ctx.screen_loader.screen_info_list` loader 序遍历,「不承传入序」主张精确;cw_loop.py:1476 身份问询点命中(CW_DISPATCH_SCREENS 传入 :1477-1479)。
8. **同名唯一前提**:board_unique_key 定义 cw_deploy_logic.py:1769(char_id 级);cw_vocab.py:1120-1121(deploy)/:1168-1170(swap)入口同守卫命中(设计写 :1117/:1162,小漂移);「同名同星≤1 仅 merge 工作表内部不变量」与 cw_gain_chain.py:169 docstring 吻合。
9. **观察写零回调 / mutator 零记忆**:观察通道与逻辑写通道分立在册(cw_game_state write_logic/_write_logic_frame:2932 族 vs observe 族),faction-trigger「边界」节主张有结构对应。

### kind 词表锚(代码)

10. **七个 zero_writes 行号逐一精确命中**:pick_megastar:109/pick_partner:117/pick_star_tome:125/pick_wish_trial:133/pick_box_card:141/pick_fortune:149/pick_expert_invite:157(zero_writes.py);「aha 无上报动作」属实(全仓无 report_action_pick_aha;CwScreenAhaEquipPick 仅观察侧);「八个有上报的 pick」计数相符(pick_planner 上报在 kernel/cw_action_report/pick_planner.py:78)。
11. **画面档真实**:「货币战争-命运卜者强化」= cw_fortune_picker.yml,cw_screen_fortune.py:55 SCREEN_NAME 命中,cw_loop.py:548 分发在册;其余八 kind 对应画面名均在 CW_DISPATCH_SCREENS(:547-556)或备战场(aha 无独立档,锚 = 备战.标识-简易装备,与 aha_equip_pick.md 一致)。
12. **S6「受影响声明两条」自洽**:现役指向弹窗屏的 WorldDecl 恰两条(open_box = zero_writes.py:34 next_screen='货币战争-备战-武装箱选择' trigger='open_box';open_bookcard.py:30);open_tome.py 无 WorldDecl(全文 51 行核),「声明两条 + open_box trigger 保留」与代码对齐。

### sim 现役主张(六项修正的现状描述)

13. **'fate' = 圣杯任务链**:cw_sim_overlay.py:23-24(「fate:2F-5F 各一次二选一接取 = §0.1 攻略补记单源」)——张冠李戴主张成立,正名 wish_trial 有据(wish_trial 画面档/tiers 互证)。
14. **'hack' 与 planner 同物**:cw_sim_overlay.py:16 自注「骇入 = planner 族变体」;游戏侧 gameplay/currency_war.md:76-79「我来当策划」弹窗副标题 =「请选择一个骇入效果」(2026-08-20 用户口述、局29 实证);cw_game_state.py:2370 chosen_hack 行注「骇入策划」。hack → planner 正名(并入,词表不留 hack)主张成立。
15. **planner 两错现状**:_silver_wolf_max_star 扫 bench+front+back(backend:1502-1515,docstring 自认「扫描必须全域」)✓ 应只场上;planner_fired 全局一次性(:743 bool、:1492 早退、:1498 置位)✓ 应每费用档。
16. **megastar 水位语义**:backend:1483 `if tier_idx > self.megastar_fired_tier`(严格大于才入队)——「降档再升回原档不弹」的现役描述精确,改逐次上穿的差异申报准确。
17. **fortune 缺 kind**:OVERLAY_KINDS(cw_sim_overlay.py:40-42)七成员无 'fortune' ✓「占卜屋无 kind——本批补建模」现状准确。
18. **私有评估器符号在册**:_evaluate_megastar:1472/_evaluate_planner:1487/_board_truth:1519/_refresh_board:1532/OverlayQueue:74/megastar_fired_tier:748/planner_seen_star:746(cw_sim_backend.py + cw_sim_overlay.py),退役清单符号全部真实。

### 执行侧与容器(3.1/3.2 派工面)

19. **deploy_move 动作拓扑与替换语义**:deploy_move.py:57-70 docstring(「bench 源槽摘槽 + 载荷直落…目标槽空 = 放置;有人 = 交换——被占位单位回源 bench 槽」)= :65-66 精确命中;faction-trigger:31 的拓扑描述与之一致。升费变换窗(:50-53/:69-70,银狼 3★ 上场写下一档 1★)支撑「升费 deploy 新值 1<2 不弹」边界。
20. **buy_card 双锚**:detect_merge_upgrade 调用在 buy_card.py:161(trigger-inventory §1.3 锚精确);cw_buy_card_action.py:161(mutate_bench_deployed 调用)/:177(_books.deployed tracked 读点)双锚精确。
21. **tracked 侧行全部行号**:sell_bench.py:89-102(报告层 tracked 吸收分支,定长 9 补洞直写)、cw_prep_sell_bench_action.py:66(`ex._track_remove_bench`)、cw_screen_shop.py:532(`tracked_books.bench` 读口)、cw_screen_prep.py:547-548(board_from_tracked(tracked_books.deployed))、cw_observation.py:2434(tracked 读口)、wear_equip.py:173-182(wear tracked 分支)、tool_use 无 tracked 分支(tool_use.py 全文无 tracked_books)——逐行命中。
22. **prep_actions 三条分支**:_track_remove_bench:745/_track_remove_deployed:763/_track_move_deployed:784 ✓;TrackedBooks 结构 = bench 定长 9/deployed 定长 10(cw_game_state.py:1922-1929)✓;BENCH_CAPACITY=9(cw_exec_state.py:166);BenchView/ShopPayload(cw_game_state.py:488/:583)、kind='empty' 语义、「三态定长 5 槽模型」(logic-updates/buy-card.md:57)、ShopPayload 紧凑下标 docstring(cw_game_state.py:560/:573)均在册。
23. **容器触点全在**:seed_opening_state:1818/_write_logic_frame:2932/_resync_board_delta:2741/_absorb_slot_reorder:2667(:2675 docstring 即 _rows_unit_key 键口径「槽位号不在键内,装备集在键内」)/mutate_bench_deployed_local:1574/detect_merge_upgrade:1385(cw_game_state.py);读口五兄弟 deployed_rows_of:3724/deployed_count_of:3779/front_count_of:3786/back_count_of:3793/max_units_of:3799——「读口重写、消费位零改动」策略有结构基础(读口消费面 128 处均经读口)。
24. **swap_deploy**:swap_deploy.py:93(`slot=deployed_slot_no(d_idx)`)消费换算+Unit.slot ✓;「策略侧 live 引用」属实(strategies/impl/flow.py:929/:985、mandate_v1/bridge.py:276/:329 调 report_action_swap_deploy_param);「生产执行器未接线」与正本 prep-executor-actions.md:21 一致。
25. **mandate_v1 tracked 读口**:mandate.py:1169(「席位翻正读数 = 执行器 tracked 账 pre/post 现读」)真实对应触面表「mandate 读口改主域派生」。

### 数据注册表与游戏知识

26. **档位表**:cw_factions.py:61 盛会之星 tiers=(2,3,4,5,6)(首档 2 主张的基础)精确;:67 命运圣杯 tiers=(2,3,4,5)(祈愿 2F-5F 与注册表互证)精确。
27. **星徽/卡带**:cw_equipment_data.py:110-131 星徽 22 枚区、:119 命运圣杯星徽「装备者加入【命运圣杯】羁绊」、:226-227 星核猎手卡带无条件 +1、:228-229 欢愉卡带条件双计——逐行命中;cw_bond_equips.py:34-40 卡带两分正则与「贡献建模单一源」主张吻合。
28. **载体规则**:cw_gain_chain.py:164(「take 中含场上 → 场上那个的位置;全备战 → 最左」)与 :169(「场上同名同星 ≤1 恒成立不变量」)精确命中(trigger-inventory §1.3 序贯 A/B 的判据事实)。
29. **lv999_cost_tier**:cw_game_state.py:2380 Field 定义;双写端 = deploy_move.py:134(deploy 升费分支)/pick_planner.py:278(选升费分支)精确。
30. **占卜屋机制**:黑天鹅.md:18 官方羁绊原文「每累计参与2场战斗后可以打开占卜屋,并选择1张启示卡」——S4 计数 2 倍数主张的游戏知识基础成立;settle_confirm 分支载体在册(report_node_advance cw_game_state.py:3282;NODE_ADVANCE_TRIGGERS:3198 含 settle_confirm;pick_encounter.py:44/:75 trigger='battle_resolve'+next_screen=SCREEN_SETTLE)。
31. **OpenTome 双击现役**:cw_open_tome_action.py:4/:31/:72/:74(「点两次(选中→开启)」「第一次:选中」「第二次:开启」)——bug 候选申报的代码事实精确;正本勘误四锚(action_ops.md §4.2/action-logic-state.md §3.5/screens/README.md §5.3/logic-updates/open-tome.md)均存在。

### landing 判据与正本更新清单

32. **判据可验证性**:3.1 逐槽对拍/写序断言/restore 迁移、3.2 grep 归零清单(tracked_books/_track_/mutate_bench_deployed + 五函数)、3.3 判据逐条行为测试(与 faction-trigger 判据归位表逐项对应)、3.4 宿主交回/排序提速/sim 对拍、3.5 grep 归零 + journal——均有可执行验证面;依赖序 3.1→3.2/3.3→3.4→3.5→正本无环。
33. **正本更新清单 13 行锚全部真实**:fields.md §3.2.3(:239)/§3.2.4(:253)、projection_contract.md §4.1(:84)、action-logic-state.md §1.4(:45)/§3.5(:226)、screens/prep.md、screens/op-layer.md §1.2(:47)、sim-design.md §4(:121)/§6.3(:177)、sim-wiring.md §六、architecture.md、flow/action_ops.md §4.2(:83)、flow/outer_loop.md §2.2(:44)、screens/megastar.md/wish_trial.md、game/gameplay/currency_war.md 银狼段(:75-79)——全部存在且语义对口。
34. **「外循环 28 候选」**:cw_loop.py:546-556 恰 28 项,逐项数核。
35. **满栏例外锚**:op-layer.md:51「满栏例外:板凳满时点合成槽位,游戏机制自动多买至 3 的倍数张…一击多张 = 一个动作 op」——trigger-inventory §1.3 引用精确;代码对应 merge_buy_k(cw_buy_card_action.py:170-178)。
