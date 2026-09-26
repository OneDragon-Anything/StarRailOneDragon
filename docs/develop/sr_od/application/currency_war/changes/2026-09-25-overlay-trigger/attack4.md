# 2026-09-25-overlay-trigger 设计对抗审报告(第四轮·收敛轮·无前提攻击)

> 攻击章程:iteration-design.md §7 核一 + §5 写作硬规则。零前提独立发起:不预设焦点,不信任文档主张,逐条对照权威源(容器/上报/tracked/sim/data/流程代码 + 正本与画面档)核实,结论只看证据。收敛轮重点 = 跨文档一致性(回调契约/判据归位/kind 词表/sim 修正清单/换算归属/TrackedBooks 去向/簿记口径/文件路径/行号)、试读、依据标注、事实核查、可验收性。报告只写发现与证据,不写修复建议。

## D1【打回级】巨星簿记口径三处互斥(megastar_fired_tier「迁容器簿记」vs「无簿记」vs「退役」),且 sim 对拍豁免清单漏巨星行为变更——判据照字面执行必红

- **攻击对象**:details/register-consume.md「sim 消费·迁移退役清单」+ design.md §2「C-簿记」+ landing.md 3.4「sim 对拍」判据 + landing.md 3.5。
- **主张原文**:
  - register-consume.md:64:「**迁移退役清单**:OverlayQueue/megastar_fired_tier/planner_fired/planner_seen_star **迁容器簿记**」;
  - design.md C-簿记:「**巨星无簿记**(每次上穿档线即弹,降档再升也弹……)」;faction-trigger.md 判据归位表 S1a:「**无簿记**(每次上穿即弹,用户裁定:降档再升也弹)」;register-consume.md 存处节:「巨星无簿记——上穿即弹」;
  - landing.md 3.5:「sim ……OverlayQueue/megastar_fired_tier/planner_fired/planner_seen_star **退役**」;
  - landing.md 3.4 完成判据:「sim 对拍:同局脚本结果与迁移前一致(除 sim 修正清单五项的显式行为差异:planner 扫描范围[备→场]、planner 簿记[一次性→每费用档]、fate → wish_trial / expert → expert_invite / hack → planner 正名、fortune 补 kind)」。
- **攻击角度**:同一符号 megastar_fired_tier 的处置,register-consume 归「迁容器簿记」、landing 归「退役」、总纲/详设判据面说「巨星无簿记」——按 C-簿记的容器簿记枚举(祈愿档位/planner 费用档两处 + 占卜屋计数),megastar_fired_tier 没有合法迁移目标;照 register-consume 字面施工会在容器里造出一个巨星簿记位,正面违反「无簿记」裁定。簿记口径属收敛轮逐一比对清单,任何两处不同即打回级。行为面连锁:sim 现役巨星评估器是**水位语义**(`tier_idx > megastar_fired_tier` 才入队,降档再升回原档不弹),新设计 S1a 是**逐次上穿**(降档再升也弹)——降-升再穿档场景两口径结果不同;这是设计显式引入的第六项行为差异,但 landing 3.4 对拍判据只豁免五项(全为 planner/词表项,无巨星)。判据与设计行为矛盾:对拍脚本一旦含巨星降-升再穿档,照判据必红;不含则判据掩盖真实差异。「sim 修正清单五项」(design/register-consume/landing 三处逐字一致)同样未收纳巨星项。
- **证据**:src/sr_od/application/currency_war/sim/cw_sim_backend.py:1472-1485(`_evaluate_megastar`:`if tier_idx > self.megastar_fired_tier:` 严格大于才 push,水位语义);register-consume.md:64/:48;design.md:51;faction-trigger.md:43;landing.md:50/:55。

## D2【打回级】TrackedBooks 消费面去向:总纲摘要与详设退役表对「锚定写回」给出相反动作(「改读主域」vs「写回腿删除」)

- **攻击对象**:design.md §2「系统级变化·1」+ details/deployed-merge.md「TrackedBooks 退役」表。
- **主张原文**:
  - design.md:36:「TrackedBooks 整体退役(用户裁定 2026-09-25:消灭第二账——主域可槽位直址后,**执行器直址/守卫 expected 侧/锚定写回全部改读主域**,升星确认候选宿主不动(局旁表)、比较基线改主域派生视图)」;
  - deployed-merge.md 退役表行 3:「reconcile 锚定写回(cw_reconcile.py tracked 整表写回腿)| **写回腿删除**(观察通道本就写主域)」;行 1:执行器随动同步腿「**腿全部删除**——动作写主域(逻辑通道)即同步,第二账无可同步」。
- **攻击角度**:TrackedBooks 消费面去向属收敛轮逐一比对清单,任何两处口径不同即打回级。「锚定写回」的真实处置是**删除**(写回腿的写入对象 tracked 消失,腿无存在形式;「改读主域」对一个写腿不是连贯操作),总纲写成「改读主域」= 与详设相反的动作;「执行器直址……改读主域」对随动同步腿同理(详设 = 腿全部删除)。landing 3.2 与 grep 归零判据兜底使误实现概率有限,但收敛判据按字面不成立:同一消费面在总纲与详设各出现一次、动作相反。
- **证据**:design.md:36;deployed-merge.md:37/:39;landing.md:17-25;iteration-design.md §5-4(修订后全量同步复查)。

## D3【需澄清】触面清单与代码实况不符:漏四个真实触点、含一个幻影触点

- **攻击对象**:details/deployed-merge.md「触面清单」表(写方行 + tracked 侧行)+ landing.md 3.2「文件面」。
- **主张原文**:deployed-merge.md 写方行:「deploy_move、sell_deployed、buy_card(pre_dep 快照)、gain 链(merge 工作表+落写)、wear_equip、工具装备腿、观察链(分排读屏 → 合一写视图)」;tracked 侧行:「cw_exec_state……、prep_actions(_track_* 三腿删)、cw_reconcile……、cw_vocab……、strategies/impl/mandate_v1/(mandate 读口改主域派生)、cw_deploy_move_action/cw_sell_deployed_action(同步分支删)、cw_observation(cw_observation.py:2434 读口改)、cw_screen_prep(:548 读口改)、cw_buy_card_action(:161 mutate 调用与 :177 tracked 读点改)」;退役表行 1 括号内含「**wear/tool tracked 腿**」;landing.md 3.2 文件面:「operations/cw_op/(deploy_move/sell_deployed/buy_card 同步分支)」。
- **攻击角度**:①**写方行漏 swap_deploy**:kernel/cw_action_report/swap_deploy.py:93-99 构造 `replace(..., slot=deployed_slot_no(d_idx))`、经 `deployed_indexed_to_rows` 转两行后 `_w(gs.front_row, ...)`/`_w(gs.back_row, ...)` 双写——是 front_row/back_row 的真实写方(消费两换算函数 + Unit.slot 构造,三件全在 3.1/3.2 退役面内),策略侧 live 引用(strategies/impl/flow.py:929/:985、mandate_v1/bridge.py:276/:329 构造该参数);faction-trigger.md 自己也写明「SwapDeploy……词表/sim 在册」,触面表却不列。②**tracked 侧漏三处**:`kernel/cw_action_report/sell_bench.py:89-102`(报告层 tracked bench 对称吸收腿——`_books.bench` 整表写,正是「动作随动同步腿」物种);`operations/cw_op/cw_prep_sell_bench_action.py:66`(`ex._track_remove_bench` 执行腿);`operations/cw_screen/cw_screen_shop.py:532`(`tracked_books.bench` 读,商店播种遥测源)——TrackedBooks 类删后此三处为运行时断点。③**幻影触点**:「wear/tool tracked 腿」的 tool 腿在代码中不存在(tool_use.py 全文零 tracked/books 引用;wear 腿实在 wear_equip.py:167-182)。landing 3.2 的 grep 归零判据(`tracked_books`/`_track_`/`mutate_bench_deployed` 引用归零)与 3.1 测试全量绿可机械兜住以上遗漏,故不升级;但触面表被 landing 明示为清单源(「清单见详设触面表」),其完备性主张与代码实况不符。
- **证据**:swap_deploy.py:93-99;sell_bench.py:89-102;cw_prep_sell_bench_action.py:66;cw_screen_shop.py:532;tool_use.py(全文件 grep `books|tracked|_track` 零命中);wear_equip.py:167-182;deployed-merge.md:58-59;landing.md:6/:19。

## D4【低】「定长 10 装不下后 7-10 槽」数值与权威源不符(应为后 7-9 槽)

- **攻击对象**:details/deployed-merge.md「目标模型·后排动态容量」。
- **主张原文**:「定长 10 装不下**后 7-10 槽**的表示缺陷(现役 tracked 表硬上限)随之消失」。
- **攻击角度**:后排格数上界的代码与知识档双源均为 9:代码注释明文「后排实际格数 = 6 + (cap−level) 值域 6-9……扩展格 **7-9** 的跟踪缺口」;游戏知识正本明文「**上限 9 格**(用户口述 2026-09-11 重申确认)」。「后 7-10 槽」多算一格,超出两条权威源的值域。设计决策本身(动态 back_slots 消灭硬上限)不受影响,属论据数值失准。
- **证据**:src/sr_od/application/currency_war/kernel/cw_exec_state.py:167-171;docs/game/currency_war/research/board_structure.md:25。

## D5【低】design.md §0 状态字段残留轮次叙事(进度第二源)

- **攻击对象**:design.md §0 元信息。
- **主张原文**:「状态:草案(对抗审中;**三轮攻击全部处置,待收敛轮确认**)」。
- **攻击角度**:iteration-design §5-3「不写谁审的、第几轮攻击……过程住对抗报告与账本,**进度只住 README**」;§0 状态字段的规约取值 = 草案/对抗审中/定稿。「三轮攻击全部处置,待收敛轮确认」是轮次叙事,且 README 进度区已载同信息(README.md:13-14)——设计正文重复即第二源,changes/ 清理时该行随正本失效面死亡。设计语义零影响,且状态迁移到「定稿」时该行按规约改写,属自愈型违规。
- **证据**:design.md:6;README.md:13-14;iteration-design.md:95/:105-107。

---

## 发现计数汇总

| 严重度 | 计数 | 编号 |
|---|---|---|
| 打回级 | 2 | D1 巨星簿记口径三处互斥 + sim 对拍豁免清单漏巨星行为变更;D2 TrackedBooks「锚定写回」去向总纲(改读)与详设(删除)相反 |
| 需澄清 | 1 | D3 触面清单漏 swap_deploy 写方与三处 tracked 触点、含幻影「tool tracked 腿」 |
| 低 | 2 | D4 「后 7-10 槽」应为 7-9;D5 design §0 状态字段轮次叙事 |

## 已核实为准确的抽样清单(边界界定,命中即准确,非穷举)

**回调契约**
1. 四回调集合与签名在 design.md C-回调、faction-trigger.md 约束节/级联表、landing 3.3 三处逐字一致(on_units_changed/on_equips_changed/on_qualification_changed/on_star_changed;faction-trigger 第 5 行显式标「(非回调)羁绊计数字段」不构成第五回调);landing 3.3 判据归位(判据住资格集回调、S3 住星级回调)与 faction-trigger「判据归位」表方向一致。
2. C-登记三口签名 `register_screen_change(gs, kind, screen_name, source)`/`consume_screen_change(gs, kind)`/`clear_screen_changes(gs)` 在 design 与 register-consume 接口块一致;PendingScreen 三字段(kind/screen_name/source)与总纲「pending 条目」描述一致。

**kind 词表**
3. 九 kind = design C-登记枚举与 register-consume kind 表逐项同名(partner/megastar/planner/wish_trial/fortune/star_tome/box_card/expert_invite/aha)。
4. 七个 zero_writes 选卡上报行号逐一命中:pick_megastar:109/pick_partner:117/pick_star_tome:125/pick_wish_trial:133/pick_box_card:141/pick_fortune:149/pick_expert_invite:157(zero_writes.py 直核);「aha 无上报动作」属实(zero_writes 无 pick_aha);「八个有上报的 pick」计数相符(pick_planner 在 pick_planner.py:78)。
5. kind 表画面档名与外循环分发清单实况对齐:八屏名全部实在 cw_loop.py:546-557 CW_DISPATCH_SCREENS;design §1「外循环 28 候选全扫识别」= 清单恰 28 项(逐项点数)。

**簿记口径(准确部分)**
6. 祈愿首达一次/planner 每费用档首 2★ 一次/占卜屋 2 倍数/伙伴无上限,在 design C-簿记、faction-trigger 判据归位、register-consume 存处、landing 3.3 四处一致;「已触发档位集合两处同型(祈愿/planner)」三处一致。
7. `gs.lv999_cost_tier` 锚准:cw_game_state.py:2380 字段在,:2376-2377 注释明文写端 = pick_planner 升费腿/deploy_move 上阵变费腿,与 faction-trigger 声明一致;deploy_move.py:134 实证升费写点。

**换算归属**
8. 五函数实在 kernel/cw_exec_state.py:237-295(deployed_slot_no/deployed_row_slot/deployed_idx_of/deployed_rows_to_indexed/deployed_indexed_to_rows);阶段归属三处一致:design「随 tracked 消费端退役后删除」、landing 3.1 显式排除(窗口期仍用)+ 3.2 删除。
9. 五函数消费点实证:deploy_move.py:83/:92-94、swap_deploy.py:93/:97、sell_deployed.py:63、wear_equip.py:172、prep_actions.py:767/:779/:804-818。

**TrackedBooks 去向(准确部分)**
10. 升星确认候选宿主 = cw_reconcile 局旁表实证(_STAR_GATES WeakKeyDictionary,cw_reconcile.py:73-103),与「候选宿主不动(本就在 cw_reconcile 局旁表)」一致。
11. `tracked_account_observed`/`tracked_unobserved` 实在 cw_game_state.py:2094-2097(消费面注释与 deployed-merge 行 5 的「锚定语义重定义、两态制不变」对得上);prep_actions 三腿 `_track_remove_bench`/`_track_remove_deployed`/`_track_move_deployed` 实在 :745/:763/:784;TrackedBooks 类(bench 定长 9/deployed 定长 10)实在 cw_game_state.py:1922-1941。

**landing 判据与机制依据**
12. 六 emit 点行号逐一对拍全准:deploy_move.py:143、buy_card.py:184/:186、wear_equip.py:187、sell_bench.py:121、sell_deployed.py:78;获得链零 emit 属实(cw_gain_chain.py 无 emit_fact_event);FactEvent/FACT_EVENT_KINDS/set_fact_event_sink 实在 cw_event_hooks.py:27-55。
13. sim 私有评估器/队列符号实在:_evaluate_megastar:1472/_evaluate_planner:1487/_board_truth:1519/_refresh_board:1532(cw_sim_backend.py)、OverlayQueue(cw_sim_overlay.py:74)、megastar_fired_tier:1483/planner_fired:1492/planner_seen_star:1493;sim 三错主张全准:planner 扫备战席(_silver_wolf_max_star:1502-1515 注释自认「备战席+前台+后台」)、planner_fired 全局一次性(:1492 早退 + :1498 置位)、OVERLAY_KINDS 含 'fate'(cw_sim_overlay.py:41)且 'expert'/'hack' 在册、'fortune' 缺席;「'hack' 与 planner 同物」有 :16 自注「骇入 = planner 族变体」支撑。
14. 两段式判定机制依据逐字核实:screen_utils.py:368-373——传入 screen_name_list 仅作过滤集(`if screen_info.screen_name not in screen_name_list: continue`),遍历序 = `ctx.screen_loader.screen_info_list`,重排列表不承序;cw_loop.py:1476 锚准(`sim_or_live_identity` 调用行);register-consume「外循环分发 | CwLoop.loop 身份问询前(operations/cw_loop.py:1476 区)」与代码一致。
15. S6「受影响声明两条」属实:open_box(_DECL_OPEN_BOX,zero_writes.py:33-34,trigger='open_box' + next_screen='备战-武装箱选择')与 open_bookcard(open_bookcard.py:30-31,纯转移 + next_screen='备战-专家邀请函')有声明;open_tome.py 无 WorldDecl(open_tome.py 全文);「open_box 的 trigger 保留」与现役常量一致。OpenTome 双击 bug 实在:cw_open_tome_action.py:72/:74 两击序列 + docstring「点两次」。
16. 判据锚:buy_card.py:161 detect_merge_upgrade 准;deploy_move.py:65-66 替换语义(占位者回源 bench 槽)docstring 原文准;pick_encounter 声明 trigger='battle_resolve'/next_screen=结算(pick_encounter.py:44/:75)准;满栏多买 merge_buy_k 实在 cw_buy_card_action.py:170-178;cw_buy_card_action.py:161/:177 双锚准。

**正本锚**
17. landing 正本更新清单 12 行所引文件全部实在:fields.md、flow/projection_contract.md、action-logic-state.md、screens/prep.md、screens/op-layer.md、sim/sim-design.md、sim/sim-wiring.md、architecture.md、flow/action_ops.md、flow/outer_loop.md、screens/megastar.md、screens/planner.md、docs/game/gameplay/currency_war.md。
18. 抽查节锚:outer_loop.md §2.2 =「两阶段分发」(含「清单 = 过滤器非优先级,遍历序 = loader 序」原文,与新设计机制依据同源);megastar.md §1「一局可多次」、wish_trial.md「叠备战、挡出战」、trigger-inventory 引 game_state/logic-updates/open-tome.md 实在。

**数据/判据事实**
19. cw_factions.py:61 盛会之星 tiers=(2,3,4,5,6)、:67 命运圣杯 tiers=(2,3,4,5) 逐字准;22 星徽块 cw_equipment_data.py:110-131(恰 22 行)统一「装备者加入【XX】羁绊」句式准;:119 命运圣杯星徽原文准;:226-227 星核猎手卡带无条件计数+1、:228-229 欢愉卡带条件双计准;cw_bond_equips.py:37-40 卡带两系正则(_RX_TAPE/_RX_TAPE_COUNT)与「两分在册」一致。
20. 同名唯一守卫链准:cw_deploy_logic.py:1769-1781 board_unique_key(char_id 级、开拓者归一)+ cw_vocab.py:1117(deploy)/:1162(swap)双入口守卫;cw_gain_chain.py:164 载体规则(take 含场上→场上位置;全备战→最左)、:169 场上同名同星≤1 不变量,逐字准;`_rows_unit_key` 键口径锚 cw_game_state.py:2675(名/星/装备集,槽号不在键)准;BenchView(:487-499,capacity 先例)与 ShopSlot(:566-576,「紧凑下标≠物理槽位……结构性消失」docstring)同族先例引文逐字准。
