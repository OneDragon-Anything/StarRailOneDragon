# 2026-09-25-overlay-trigger 设计对抗审报告(第二轮·无前提攻击)

> 攻击章程:iteration-design.md §7 核一 + §5 写作硬规则。不预设焦点;文档主张逐条对照权威源(代码/画面档/游戏知识档)核实;结论只看证据。本轮为零前提独立发起,不继承第一轮报告的焦点;引文与行号均为本轮直核。

## 打回级

### R1 kind 词表缺 S6 两个成员的 kind——总纲定死的词表契约不完整,且「对齐现役」面临三名并存未裁定

- **攻击对象**:details/register-consume.md「kind 词表」节 + 「S6 点击类」节;design.md §2「C-登记」。
- **主张原文**:「**kind 词表(对齐现役画面/动作名,禁新造同物异名)**」(词表共 7 项:partner/megastar/planner/wish_trial/fortune/aha/star_tome);「三个 open_* 上报(open_box/open_bookcard/open_tome)各加一行 register_screen_change」;design.md:「kind 词表 = partner/megastar/planner/wish_trial/fortune/aha/star_tome(对齐现役画面与动作名)」。
- **攻击角度**:S6 裁定三个 open_* 全部登记,但词表只覆盖 open_tome(star_tome);open_box(画面 货币战争-备战-武装箱选择)与 open_bookcard(画面 货币战争-备战-专家邀请函)无 kind 可用。`register_screen_change(gs, kind, screen_name, source)` 的 kind 是必填位——实现者要么自造 kind(直接违反本句「禁新造同物异名」),要么停手,二者都撞 §5-2「实现者无需再设计」。且「对齐现役」在专家邀请函上并非唯一解:现役词表已有三个名字并存——sim `OVERLAY_KINDS` 的 `'expert'`、overlay registry 的 `bail_tag='bookcard'`(专家邀请函屏)、动作名 `pick_expert_invite`——设计未裁定新 kind 取哪个,「对齐」主张落空。去重(consume 按 kind 匹配)与 sim 呈现门都吃 kind,缺口是契约级的。
- **证据**:zero_writes.py:141(`report_action_pick_box_card_param`)/:157(`report_action_pick_expert_invite_param`);cw_sim_overlay.py:41(`OVERLAY_KINDS` 含 `'expert'`);cw_overlay_registry.py:284-293(备战-专家邀请函条目 `bail_tag='bookcard'`);cw_loop.py:550(分发清单含 货币战争-备战-武装箱选择)。

### R2 kind 表「现役词表锚」列引两个不存在的动作名 + aha 无上报函数致消费点无落点 + star_tome 画面名与档名不符

- **攻击对象**:details/register-consume.md「kind 词表」表 + 「实机消费·生命周期」节。
- **主张原文**:「star_tome | 货币战争-星徽秘典 | 屏档 bookcard.md;**动作 confirm_tome**」;「aha | (锚 = 备战.标识-简易装备) | aha_equip_pick.md;**动作 pick_aha_equip**」;「①精确消费 = 选卡动作上报处调 consume(**pick_partner/pick_megastar/… 上报函数内,两世界同一行代码**)」。
- **攻击角度**:三处代码事实错误。(a) `confirm_tome` 全仓无此动作——星徽秘典选卡动作 = `pick_star_tome`;仓内确有 `ConfirmTome` 字样,但那是选卡落地后的**到账登记 tag**,不是动作,词表锚把两者混为一谈。(b) `pick_aha_equip` 全仓无匹配——阿哈装备选择是画面 op `CwScreenAhaEquipPick`,「空决策形态无 report:本屏零容器写点」,根本没有动作上报函数;于是消费生命周期①「选卡动作上报处调 consume」对 kind=aha 无处落(实机与 sim 同病——sim 的 consume 同口主张也依赖「同一批上报函数」),设计未给 aha 的 consume 落点。(c) star_tome 行画面名写「货币战争-星徽秘典」,实际档名/分发名 = **货币战争-星徽秘典弹窗**;`PendingScreen.screen_name` 是分发排序的匹配键,错名 = 该 kind 的排序提速永不命中。
- **证据**:zero_writes.py:125(`report_action_pick_star_tome_param`);cw_pick_star_tome_action.py:57(节点名 `pick_star_tome`);cw_screen_bookcard.py:282 + cw_exec_state.py:102/:124(`ConfirmTome` = `register_confirm_arrival` 到账登记 tag,非动作);cw_screen_aha_equip_pick.py:13-18(「空决策形态无 report:本屏零容器写点」);cw_loop.py:551 / cw_overlay_registry.py:275 / bookcard.md 标题 / cw_game_state.py:254(档名均为 货币战争-星徽秘典弹窗);`confirm_tome|pick_aha_equip` 全仓 grep 0 命中。

### R3 trigger-inventory §1.7/§1.8「待裁」残留与已定裁定矛盾,且指向不存在的「register-consume.md §待裁」节

- **攻击对象**:details/trigger-inventory.md §1.7/§1.8(对照同文 §1.9、details/register-consume.md S6、design.md §2-4)。
- **主张原文**:§1.7「是否统一入登记接口待裁(register-consume.md §待裁)。」;§1.8「同上待裁。」——而 §1.9 已写「→ S6 统一入登记(用户裁定:选项 a)」,register-consume S6 节写「用户裁定 2026-09-25:选项 a 统一入登记」,design.md §2-4 写「S6 点击类统一入登记(用户裁定 2026-09-25…)」。
- **攻击角度**:§5-4「修订后全量同步复查」失守的实证——S6 裁定落地后只改了 §1.9 与 register-consume,§1.7/§1.8 的「待裁」未同步;同一文档内 §1.7/§1.8 与 §1.9 给出相反结论,实现者读到的是「box/expert 是否入登记未定论」。同时指针目标「register-consume.md §待裁」节不存在(该文无任何待裁节)——悬空引用。
- **证据**:trigger-inventory.md:69/:73(待裁句)对 :79(§1.9 裁定句);register-consume.md 全文章节枚举(接口/kind 词表/存处/实机消费/sim 消费/其余触发类,无「待裁」节)。

### R4 landing 3.4 残留已明文弃用的 kind 名「diviner」

- **攻击对象**:landing.md §3.4(对照 details/register-consume.md「sim 词表处置」、design.md §2 系统级变化 4)。
- **主张原文**:landing 3.4 范围:「sim 呈现读 pending + 逐 kind 呈现门(**diviner** 仅备战底层)」——register-consume:「原拟新造 'grail'/'diviner' 弃用(同物四名…)」、kind = fortune;design.md:「逐 kind 呈现门:fortune 仅备战底层」。
- **攻击角度**:§5-4 全量同步失守——弃用决定落在 register-consume 与 design 后,landing 的判据承载行未同步。落地文档是派工与验收的单一源,worker 照 3.4 施工即把弃用名带回实现,违反词表单一源。
- **证据**:landing.md:42;register-consume.md:40/:60;design.md:39。

### R5 正本更新清单与触面清单引用不存在的 screen_op.md

- **攻击对象**:landing.md「正本更新清单」;details/deployed-merge.md「触面清单·文档正本」行。
- **主张原文**:「screen_op.md 对账节(升星候选宿主) ← 3.2」(landing);「…screens/prep.md §2(tracked 行)、**screen_op 对账节**、op-layer.md §1.2…」(deployed-merge)。
- **攻击角度**:docs/** 全树无 screen_op*.md(glob 0 命中)。固定末阶段(正本更新)的完成判据 = 「清单清零」——悬空行不可验收;§5-4 定稿门槛明列「文件面真实路径/正本清单」逐项核,此为漏核实证。触面清单同引,两处同病。
- **证据**:`docs/**/screen_op*.md` glob 0 命中;升星确认候选的实际文档面 nowhere 以该名存在(候选态实现与注释住 kernel/cw_reconcile.py:55-89)。

## 需澄清

### C1 「现役 kernel 不变量『同名同星≤1』弱于游戏」与代码不符,「随 3.1 收严」是无落点的幽灵工作项

- **攻击对象**:details/faction-trigger.md「值域回调级联」表星级回调行。
- **主张原文**:「同名唯一为游戏事实,容器不变量随 3.1 收严——现役 kernel 不变量"同名同星≤1"弱于游戏,收严归部署批」。
- **攻击角度**:现役 deploy/swap 入口已是**同名唯一**守卫(W43 裁决 1,判据键 = char_id 级),不是「同名同星≤1」;前提不成立,「收严」无事可做。且 landing 3.1 范围与 deployed-merge 全文均无「不变量收严」条目——faction-trigger 单方面派给 3.1 的动作在 3.1 的设计文档与落地阶段里都不存在(跨文档同步缺口)。设计需要的假设(场上同名唯一→银狼至多一只)现役已成立,结论不受影响,但现状主张是错的。
- **证据**:cw_deploy_logic.py:1769-1781(`board_unique_key`:"板上同名唯一性判据键(设计裁定:场上同角色仅 1)",char_id 级、开拓者归一);cw_vocab.py:1117-1121(「同名唯一性守卫(W43 裁决 1…):已在场同名不上(游戏拒收同名部署,swap 换入同名也同拒)」)/:1162-1170(swap 同守卫);「同名同星≤1」字样仅见于 merge 工作表内部不变量(cw_gain_chain.py:169)与升费连锁注释,非板上身份不变量。

### C2 「bot 链:deploy_move(三形态)」——换排形态在现役 deploy_move 上不可达

- **攻击对象**:details/trigger-inventory.md §1.1/§1.2「到达路径」「bot 链」。
- **主张原文**:「deploy 三形态 = 空槽上场/替换(一增一减…)/换排(成员集合不变)」+「**bot 链:deploy_move(三形态)**/sell_deployed/wear_equip+工具腿」。
- **攻击角度**:现役 DeployMove 载荷源恒为备战槽(`param.bench_idx`,docstring「bench 源槽摘槽」),只覆盖 空槽放置/目标有人=交换 两形态;换排(场上→场上、成员集合不变)没有任何现役动作路径——`SwapDeploy` 是 bench↔deployed 换位,也不是换排。§1.2 对「显式拖下场」申报了「游戏支持、bot 现役无动作」,却未对换排作同样申报,反而把它归进 deploy_move 的bot链——对代码现状的叙述失真。触发判据本身(换排不弹)不受影响,但到达路径一节的「bot 链」不可按图施工。
- **证据**:deploy_move.py:57-70(docstring「bench 源槽摘槽 + 载荷 (to_row, to_slot) 直落…目标槽空 = 放置;有人 = 交换」)/:84(`from_idx = int(param.bench_idx)`);swap_deploy.py:1/:29-30(「bench ↔ deployed 换位:原槽对调」);cw_action_report/ 目录无场上→场上动作。

### C3 「排 CW_DISPATCH_SCREENS 最前 → get_match_screen_name 首中即返」的机制主张与 API 行为不符

- **攻击对象**:details/register-consume.md「实机消费」表外循环分发行;landing.md §3.4 完成判据。
- **主张原文**:「pending 的 screen_name 排 CW_DISPATCH_SCREENS 最前 → get_match_screen_name 首中即返(28 锚检→1);未命中落回全扫描」;判据「pending 画面首中(get_match_screen_name **候选序**,测试)」。
- **攻击角度**:`get_match_screen_name(ctx, screen, screen_name_list)` 收到列表后按 **screen_loader 的装载序**遍历、仅做成员过滤,传入列表的先后不承序——把 pending 画面「排最前」字面实现后遍历序不变,28 锚检一锚不少,提速为零。要得到「28→1」需两段式调用(先只传 pending 画面、未中再全量),设计文本未写两段式;判据里的「候选序」在现 API 上不是可测属性。cw_loop 自己的分发注释与该机制主张直接矛盾。
- **证据**:screen_utils.py:368-373(按 `ctx.screen_loader.screen_info_list` 序过滤成员);cw_loop.py:541-542(「遍历序 = loader 序,非优先级……顺序不承重」)。

### C4 S2 伙伴判据的挂点:总纲四回调契约与详设「判据归位」口径不一,徽变化路径在契约签名里无家

- **攻击对象**:design.md §2「C-回调」对 details/faction-trigger.md「判据归位」表/「资格集语义」节。
- **主张原文**:design.md C-回调:「角色变动回调 `on_units_changed(gs, added_units, removed_units, source)` → **判 S2 伙伴**/S1b 重选(资格集语义)…装备变更回调 `on_equips_changed(gs, changed_pairs, source)` → 按情况(星徽贡献)喂资格集/羁绊」;faction-trigger 判据归位:「S2 伙伴 | **角色变动回调(+装备/排面事件)**」+资格集语义:「资格集变化覆盖三来源:成员增减…、存活单位徽变化(穿/卸列车星徽)、存活单位排变化(开拓者形态切换)」。
- **攻击角度**:总纲自称「签名以总纲为准」「跨详设接口契约(总纲定死)」,但其契约把 S2 判定放在 on_units_changed,而该回调签名只携 added/removed 单位——穿/卸列车星徽(§1.2 明文「星徽路径…增减面同辖」)不产生成员增减,S2 判定在总纲契约下无触发路径;详设用「(+装备/排面事件)」补口,等于判据实际挂在 diff 分解层而非某个回调内——两份文档对同一判据的挂点口径不一致,实现者面对「S2 判定代码写在哪个函数里」没有唯一答案。
- **证据**:design.md:45-50(C-回调四签名);faction-trigger.md:17(级联表 on_units_changed 行「判据:S2 伙伴、S1b 巨星重选」)/:40(判据归位「+装备/排面事件」)/:26(三来源);trigger-inventory.md:27(§1.2 星徽路径同辖)。

### C5 「换算三函数」少计:0-9 换算层实有 5 个函数,grep 归零判据只点名 1 个

- **攻击对象**:details/deployed-merge.md「目标模型·0-9 换算层退役」+ landing.md §3.2 完成判据。
- **主张原文**:「`deployed_idx_of`/`deployed_row_slot`/`deployed_rows_to_indexed`(kernel/cw_exec_state.py)删除——(row, slot) 与存储位置一一对应,零换算」;landing 3.2 判据:「全仓 `tracked_books`/`_track_`/`mutate_bench_deployed`/`deployed_idx_of` 引用归零」。
- **攻击角度**:cw_exec_state 的换算族实有 5 个——另有 `deployed_slot_no`(:237)与 `deployed_indexed_to_rows`(:295),后者是 deploy_move/swap_deploy 现役 import 的反向换算,3.1 改 DeployedView 后同样失去存在理由。触面写「三函数」、归零判据只点名 `deployed_idx_of`:按单施工会留两个死函数,且判据抓不到(不满足「清单清零」的完备性)。
- **证据**:cw_exec_state.py:237/:243/:255/:266/:295(五函数);deploy_move.py:32/:128、swap_deploy.py:15-17(`deployed_indexed_to_rows` 现役消费)。

### C6 「升星确认候选迁对账层独立簿记组/新宿主」与现状不符:候选态宿主本就在对账层旁表

- **攻击对象**:details/deployed-merge.md「TrackedBooks 退役」表升星确认候选行 + landing.md §3.2 完成判据。
- **主张原文**:「**升星确认候选**(观察跨帧一致性状态)| 唯一派生不出的工作状态:**迁对账层独立最小簿记组**」;landing 3.2 判据:「升星确认(两帧一致)行为等价:对账测试绿(**候选簿记组新宿主**)」。
- **攻击角度**:候选态现役宿主已经是 cw_reconcile 的按局身份旁表(WeakKeyDictionary),不在 TrackedBooks 里——「迁/新宿主」叙述了一个不存在的搬迁。真正随 TrackedBooks 退役而要改的是该门的**比较基线**(「锚上星读 ≠ tracked = 候选」的 tracked 侧),设计未点名这一变更;「新宿主」字样会诱导实现者另起一套簿记组(与现存旁表并存的第二源)。
- **证据**:cw_reconcile.py:73(「候选态宿主 = 按局身份 session 的旁表(WeakKeyDictionary 主路…)」)/:89(候选态取口)/:65(「锚上星读 ≠ tracked = 候选」——基线读 tracked)。

### C7 落地文件面两处路径失真:flow/cw_loop.py 与 kernel/mandate.py 均非真实代码路径

- **攻击对象**:landing.md §3.4「文件面」、§3.2「文件面」。
- **主张原文**:3.4「**文件面**:flow/cw_loop.py、operations/cw_screen/(宿主 op 与 pick op)、sim/(backend/overlay)…」;3.2「**文件面**:kernel/cw_game_state.py(类删)、prep_actions.py、cw_reconcile.py、cw_vocab.py、**kernel/mandate.py(读口)**、operations/cw_op/(…)」。
- **攻击角度**:代码里 cw_loop.py 住 `operations/`(flow/ 是文档目录);mandate 住 `strategies/impl/mandate_v1/mandate.py`(读 tracked 的注释在 :1169),kernel/ 下无 mandate.py。文件面 = 阶段允许动的文件集,是派工与验收边界——路径失真轻则误导定位,重则把真实触点排除在允许面外。另 3.2 清单里 cw_reconcile.py 实在 kernel/ 却写裸名,同段两种路径风格,属同类不严谨。
- **证据**:src/sr_od/application/currency_war/operations/cw_loop.py(实际位置;src 下无 flow/ 代码目录);src/sr_od/application/currency_war/strategies/impl/mandate_v1/mandate.py:1169(「席位翻正读数 = 执行器 tracked 账 pre/post 现读」);kernel/mandate.py glob 0 命中。

### C8 正本清单锚点错位:prep.md「§2 tracked 行」实为 §6;projection_contract「§3.6」不存在

- **攻击对象**:landing.md「正本更新清单」;details/deployed-merge.md「触面清单·文档正本」行。
- **主张原文**:「screens/prep.md:§2 tracked 行 ← 3.2」;「projection_contract.md:§3.6/§4(槽位表立法段/双账段/换算段) ← 3.1/3.2」;deployed-merge 触面:「…action-logic-state.md §1.4(随动账行)、screens/prep.md §2(tracked 行)…」。
- **攻击角度**:prep.md 的 §2 是「画面形态声明」,tracked 主账随动行在 **§6 状态上报面**;projection_contract.md 的 §3 无 3.6 小节——tracked 定长槽位表立法与账随动是 §3 的第 1/4 条。正本更新是固定末阶段,按错锚执行找不到目标段,「清单清零」验收口径失真。§5-4 明列「引用锚存在性」为复查项。
- **证据**:screens/prep.md:11(§2 标题)/:84(tracked 主账随动行,在 §6);flow/projection_contract.md:72-80(§3 为编号条目 1-7,无 3.6;槽位表形状 = 第 1 条 :74,tracked 账随动 = 第 4 条 :77)。

### C9 过程叙事与对抗轮次编号进设计正文(§5-3 卡点措辞)

- **攻击对象**:details/register-consume.md「sim 词表处置」;design.md §0「状态」。
- **主张原文**:「原拟新造 'grail'/'diviner' 弃用(同物四名,**攻击 C3**)」;design.md §0:「状态:草案(**对抗修正第一轮已落;待第二轮对抗**)」。
- **攻击角度**:iteration-design §5-3:「不写谁审的、第几轮攻击、上稿改了什么;过程住对抗报告与账本」——「攻击 C3」是对抗报告内的发现编号(随 changes/ 清理即死的局部标识),「第一轮已落/待第二轮」是轮次叙事;§0 状态字段的规约取值为 草案/对抗审中/定稿,轮次信息属 README 进度面。两处均为形式检查可直接命中的措辞。
- **证据**:iteration-design.md:105-107(§5-3 及卡点「『本轮/修订后/已改』类措辞即打回」)/:34(§0 状态规约);register-consume.md:40;design.md:6。

### C10 「action-world-decl」跨迭代 changes/ 裸引——同族缺陷第一轮已出具修正,本篇复发(同族二现)

- **攻击对象**:details/register-consume.md「S6 点击类」节。
- **主张原文**:「声明 next_screen 语义回归『底层屏 = 备战』(与 **action-world-decl** 底层屏语义自洽;…)」。
- **攻击角度**:"action-world-decl" 无路径、无「正本」限定,指向另一迭代目录 changes/2026-09-24-action-world-decl/——changes/ 会不定期无理由删减(项目 AGENTS.md 文档规范铁律),跨迭代裸引随时死链。同句后文自己引了正本单一源(flow/action_ops.md 动作总册声明列,即 §4.8 十八动作声明终表),前半句的裸引是冗余且不稳定的第二锚。第一轮对抗报告已对同族缺陷(trigger-inventory 裸引该迭代 §2 表)出具修正意见且 trigger-inventory 已改引正本——同类引用在本篇复发,按 iteration-design §7 核三「跨件半问」属流程级信号:该类自查应升级为出稿前的清单项,而非逐处补。
- **证据**:register-consume.md:69;changes/2026-09-24-action-world-decl/(迭代目录,README/attack.md 在);attack.md:94-95(第一轮对同族裸引的处置记录);flow/action_ops.md:176-178(§4.8 声明终表 = 正本)。

## 低

### L1 「待裁 10①」悬空编号——待裁清单仅 7 条,替换两问是第 5 条

- **攻击对象**:details/trigger-inventory.md §1.1 到达路径。
- **主张原文**:「替换(一增一减,被替者下场;去向 = 回备战系推断,**待裁 10①**)」。
- **攻击角度**:§4 待裁清单共 7 条,「替换形态两问」是第 5 条(①②)——「10①」指向不存在的条目编号,系清单重排后的残留;读者按编号索骥落空。
- **证据**:trigger-inventory.md:125-132(待裁清单 1-7 项,第 5 项 = 替换形态两问)。

### L2 cw_buy_card_action.py:177 不是 mutate 调用点

- **攻击对象**:details/deployed-merge.md「TrackedBooks 退役」表动作随动同步腿行。
- **主张原文**:「buy 链 `mutate_bench_deployed`(**cw_buy_card_action.py:161/177**)」。
- **攻击角度**::161 是 mutate 调用(✓);:177 是 `_books.deployed` 作为 `merge_buy_k` 的实参(**读** tracked 表),不是 mutate 调用——该文件中 mutate 调用仅 :161 一处。把读点并列写成调用点,触面性质标错(前者随 3.2 的判据面处置,后者属主域派生化)。
- **证据**:cw_buy_card_action.py:160-162(mutate 调用)/:174-178(`merge_buy_k(..., _books.deployed, ...)` 读)。

### L3 kind 表词表锚精度不一:pick_wish_trial 锚指注释行而非函数定义

- **攻击对象**:details/register-consume.md「kind 词表」表 wish_trial 行。
- **主张原文**:「wish_trial | 货币战争-祈愿试炼 | 屏档 wish_trial.md;**动作 pick_wish_trial(zero_writes.py:39)**」。
- **攻击角度**:zero_writes.py:39 是列族名的注释行;函数定义 `report_action_pick_wish_trial_param` 在 :133。同表 fortune 行的「zero_writes.py:149」却是精确函数行——同一列两种锚精度,前者按行号直取取不到目标符号。
- **证据**:zero_writes.py:39-41(注释)/:133(函数)/:149(函数)。

## 发现计数汇总

| 严重度 | 数量 | 编号 |
|---|---|---|
| 打回级 | 5 | R1-R5 |
| 需澄清 | 10 | C1-C10 |
| 低 | 3 | L1-L3 |
| **合计** | **18** | |

## 已核实为准确的抽样清单(供定稿信心)

以下主张经权威源直核**准确**,列出以界定本轮发现的边界(命中即准确,非穷举):

1. **事实事件 6 处 emit 行号全部精确**:deploy_move.py:143、buy_card.py:184/:186、wear_equip.py:187、sell_bench.py:121、sell_deployed.py:78;「5 文件 6 处」计数准确;「获得链内合成零 emit」准确(cw_gain_chain.py 无 emit_fact_event)。
2. **事实事件三件套符号存在**:FactEvent/FACT_EVENT_KINDS/set_fact_event_sink(cw_event_hooks.py:27/:35/:44)。
3. **sim 三建模错误全部属实**:OVERLAY_KINDS 含 'fate' 且模块注释明示 fate=2F-5F 圣杯任务链(cw_sim_overlay.py:23/:41);planner 判据扫备战席(`_silver_wolf_max_star`「备战席+前台+后台」,cw_sim_backend.py:1502-1506);`planner_fired` 全局一次性(:1492)。
4. **sim 退役符号全部存在**:OverlayQueue/megastar_fired_tier/planner_fired/planner_seen_star/on_fact_event/_evaluate_megastar/_evaluate_planner/_board_truth/_refresh_board/_on_overlay_picked(cw_sim_backend.py:741-748/:939/:1141/:1472/:1487/:1519/:1532;cw_sim_overlay.py:74)。
5. **CW_DISPATCH_SCREENS 恰 28 项**(cw_loop.py:546-557,逐条点数);fortune 分发行 :548、身份问询区 :1476-1479 均精确。
6. **lv999_cost_tier 字段行 cw_game_state.py:2380 精确**;写端 = deploy_move 升费腿(:134)+ pick_planner(:278)属实。
7. **buy_card.py:161 detect_merge_upgrade + pre_bench/pre_dep 快照**(:77/:79/:161)属实。
8. **merge_step_once 载体规则**「take 含场上 → 场上位置;全备战 → 最左」在 cw_gain_chain.py:164 逐字相符。
9. **数据注册表核对相符**:cw_factions.py:67 命运圣杯 tiers=(2,3,4,5);盛会之星档位 (2,3,4,5,6);黑天鹅 independent=命运卜者、姬子·启行/三月七 = 列车同行(cw_chars.py:114/:136/:169)。
10. **装备注册表核对相符**:星徽 22 枚区间 :110-131(段头自计 22);:119 命运圣杯星徽效果原文逐字;卡带两分 :226-229(欢愉条件双计/星核猎手无条件 +1);cw_bond_equips.py:37-39 两分 regex 在册;「红钻+幸运星合成盛会之星星徽」与配方表 :116 相符。
11. **星徽装备链路表逐行相符**:wear_equip `_locate_unit` 全域定位 bench→front→back(wear_equip.py:71-102);穿着即合成 worn 两两配方(:49-50);`_write_row_equips_cleared`(tool_use.py:149,冶金炉拖角色 :328/扳手族 :439 消费);冶金炉拖角色 = 全拆+白名单采样替换(:261-262);卖出回收 sold.equips 全量回库存 sell_deployed.py:71-72 / sell_bench.py:114-115 行号精确。
12. **tracked 侧符号全部存在**:TrackedBooks(cw_game_state.py:1922)、tracked_books(:2275;bench 定长 9/deployed 定长 10/0-3 前 4-9 后,:2265-2268)、_track_* 三腿(prep_actions.py:745/:763/:784)、mutate_bench_deployed(cw_buy_card_action.py:161;cw_vocab.py:1054)、换算函数(cw_exec_state.py:243/:255/:266)、tracked_account_observed(:2097)/tracked_unobserved(:1907)。
13. **tracked 读口行号精确**:cw_observation.py:2434、cw_screen_prep.py:547-548。
14. **容器侧符号全部存在且性质相符**:front_row/back_row 紧凑列表(:2079-2080)、seed_opening_state(:1818)、_write_logic_frame(:2932)、_resync_board_delta(:2741)、_absorb_slot_reorder(:2667,键不含槽位含装备 :2675)、mutate_bench_deployed_local(:1574)、detect_merge_upgrade(:1385)、deployed_rows_of/front_count_of/back_count_of/deployed_count_of/max_units_of(:3724-3799)、_row_unit_tags→cw_bond_equips.unit_bond_tags(:852-873);deploy_move 对 front/back 两行双写(:129-130)与「跨行双写中间态」叙述相符。
15. **同族先例引文逐字相符**:ShopSlot docscript「紧凑下标≠物理槽位的历史病灶类(同族)在本模型下结构性消失」(cw_game_state.py:573-574);ShopPayload.cards 定长 5 三态(:568/:586);「买牌点击落空槽框」真事故记载(:560-562);BenchView/capity 先例(deploy_move.py:123-126 消费)。
16. **「定长 10 装不下后 7-10 槽」有据**:后排可扩至 7-10 槽(docs/game/gameplay/currency_war.md:72/:88)> tracked 后排 6 槽(DEPLOYED_BACK_CAPACITY=6,cw_exec_state.py:173)。
17. **S4 链路相符**:settle_confirm 腿在册(NODE_ADVANCE_TRIGGERS,cw_game_state.py:3198);pick_encounter 声明 trigger='battle_resolve'/next_screen=货币战争-结算(pick_encounter.py:75-76;SCREEN_SETTLE=cw_game_state.py:294);正本锚 flow/action_ops.md §4.8 声明列存在。
18. **S6 现役声明核对相符**:open_box trigger='open_box'/next_screen=备战-武装箱选择(zero_writes.py:33-34);open_bookcard 纯转移 next_screen=备战-专家邀请函(open_bookcard.py:30-31,trigger='');ADVANCE_TRIGGER_KINDS 含 'open_box' 且 advance 有专属分支(cw_sim_backend.py:690/:980)——「trigger 保留」主张有据;「受影响声明两条」与 open_tome 无 WorldDecl 相洽(open_tome.py 无 decl)。
19. **OpenTome 双击 bug 在册属实**:cw_open_tome_action.py:4/:31/:46(「点两次」);四处正本勘误记载属实(screens/README.md:100「点槽一次开启…CwScreenBookcard」、action-logic-state.md:228「单次点击即弹」、action_ops.md §4.2、logic-updates/open-tome.md §9 锚均在)。
20. **阿哈大悦效果注记与注册表原文相符**(cw_invest_data.py:166);aha 锚 = 备战.标识-简易装备 与 CwScreenAhaEquipPick 入口(:46-47)相符。
21. **基础设施符号存在**:bind_session_container(cw_game_state.py:1743)、note_obs_event(:2524)、cw_overlay_registry.py(OVERLAY_REGISTRY/OverlaySpec,register-consume「overlay registry 的 screen_name/anchor」所指真实)。
22. **画面档核对相符**:megastar.md §1「跨档激活/一局可多次/候选含持星徽者」(:8/:16/:45);wish_trial.md「叠备战、挡出战」(:3);满栏自动多买至 3 的倍数(op-layer.md:51);七份屏档(partner/megastar/planner/wish_trial/fortune/aha_equip_pick/bookcard)与 invest_effects.md §0.1 均存在;bookcard.md 确为星徽秘典弹窗档(与 cw_screen_bookcard.py 对应)。
23. **正本锚存在项**:fields.md §3.2.3/§3.2.4、action-logic-state.md §1.4/§2/§3.5、sim-design.md §4/§6.3、sim-wiring.md §六、outer_loop.md §2.2、op-layer.md §1.2、architecture.md 内核层节、gameplay/currency_war.md 银狼段(:75-79,含「5费升 2 星也触发/双装备」与每费用档口径相容的勘误基础)均存在。
