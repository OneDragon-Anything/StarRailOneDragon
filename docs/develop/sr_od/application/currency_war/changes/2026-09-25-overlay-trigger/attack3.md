# 2026-09-25-overlay-trigger 设计对抗审报告(第三轮·无前提攻击)

> 攻击章程:iteration-design.md §7 核一 + §5 写作硬规则。零前提独立发起:不预设焦点,不信任文档主张,逐条对照权威源(容器/上报/sim/data/流程代码 + 正本与画面档)核实,结论只看证据。本轮不继承前两轮报告的焦点;前两轮报告仅在定稿后用于标注本轮融资现是否为「已处置项残留」(标注于各条)。报告只写发现与证据,不写修复建议。

## A1【打回级】回调集合与判据归位在四份文档四种口径;landing 3.3 与其自指的设计依据正面矛盾

- **攻击对象**:landing.md 3.3;design.md §2「C-回调」;details/faction-trigger.md「问题与约束」+「值域回调级联」表 +「判据归位」表。
- **主张原文**:
  - landing 3.3:"派生维护按名分解 → **四回调(on_units_changed/on_equips_changed/on_star_changed/on_board_changed)**挂点;**判据归位(S2 伙伴/S1b 重选 → 角色变动;S1a 档位跨越 → 羁绊**;S3 星级 → 星级回调;资格集语义)";其设计依据自指 "details/faction-trigger.md(**级联表/判据归位**/资格集/星徽链路)"。
  - design.md C-回调:四个回调 = on_units_changed/on_equips_changed/**on_qualification_changed**/on_star_changed,其中 "**资格集变更回调** `on_qualification_changed(gs, old_sets, new_sets, source)` → **判 S2 伙伴/S1b 重选/S1a 档位跨越**";board 仅作视图表述("羁绊计数 = 集合大小,现役 board 字段为其视图"),**无 on_board_changed 回调**。
  - faction-trigger 问题与约束:"总纲契约 C-回调:**四个值域回调(on_units_changed/on_board_changed/on_equips_changed/on_star_changed)**……签名以总纲为准"——**无 on_qualification_changed**,且与总纲实际文本不符。
  - faction-trigger 级联表:共 **5** 个回调(增 on_board_changed"羁绊变更回调");资格集变更回调行 = "判据:S2 伙伴、S1b 重选、S1a 档位跨越(**全部资格集判据**)";on_units_changed行 = "overlay 判据不住此(判据统一住资格集变更回调)";on_board_changed 行 = "S1a 判据住资格集回调"。判据归位表:S2/S1b/S1a 三行住处均 = "资格集变更回调"。
- **攻击角度**:同一契约四种枚举——design(4,有 qualification 无 board)/ faction-trigger 约束节(4,有 board 无 qualification,且自称"以总纲为准"但引文与总纲不符)/ faction-trigger 方案表(5)/ landing(4,有 board 无 qualification)。landing 3.3 的判据归位(S2/S1b→角色变动、S1a→羁绊)与其设计依据自指的 faction-trigger「判据归位」表及总纲 C-回调**方向相反**:按 landing 施工,S2/S1b/S1a 判据写进 on_units_changed/on_board_changed、资格集回调反而不建——恰恰违反详设明文"判据统一住资格集变更回调"。on_board_changed 存在与否(总纲无、详设方案表有)无单一答案,而 C-回调是章程要求"唯一必须在总纲定死"的接口契约(iteration-design.md §2.1)。机制清晰可辨:修订引入 on_qualification_changed 并迁移判据后,只同步了 design.md 与 faction-trigger 方案表,landing 3.3 与 faction-trigger 约束节未反查——硬规则 4(修订后全量同步复查)失守,且为同族第三现(第一轮 P4、第二轮 R4 均为 design↔landing 失同步;iteration-design §5-4 明载"design↔landing 失同步在同一迭代两次实证,二次复发即流程级")。landing 阶段小节 = 账本唯一源,此错直接立出错误任务面(第一轮 C6 同族,处置后于新位置复发)。
- **证据**:landing.md:30/:31;design.md:44-48;faction-trigger.md:5/:17-22/:40-44;iteration-design.md §2.1/§3.1/§5-4;attack.md P4/C6、attack2.md R4(同族先例)。

## A2【打回级】design.md C-回调 残留「synthesis_names 供排除」——与「零来源排除」用户裁定正面冲突

- **攻击对象**:design.md §2「C-回调」末行。
- **主张原文**:"按名分解 diff(成员增减/存活对;存活对 star 变 = 合成事件,**名入 synthesis_names 供排除**);观察写零回调。"(design.md:49)
- **攻击角度**:同一 C-回调块上一行刚定"判据**零来源排除**(经典合成集合不变天然不弹,合成继承获资格弹——用户裁定)"(design.md:47);详设定稿口径三处一致:"S2 伙伴 = ……**无来源排除**(用户裁定 2026-09-25:合成继承星徽获得新资格也弹……)"、"**按名分解的结构性收获(零排除规则)**:全部判据无来源排除——……原「同帧 2×低星消失+1×高星出现」签名匹配特判**自始不存在**于本设计"(faction-trigger.md:28/:36);事实基座收口:"**伙伴合成继承获资格也弹,排除规则作废**"(trigger-inventory.md:128)。"synthesis_names 供排除"是排除机制时代的残留:全迭代文档 grep 唯一命中(design.md:49),定稿设计里没有任何判据消费排除名单——按总纲字面施工即实现一条已被用户裁定**作废**的排除规则,并与零排除版资格集判据并存成双语义。第一轮 P2/C2 攻击的是 S1b/S2 判据与签名硬规则(处置 = 资格集语义 + 删除详设侧签名节),总纲这行是处置未及的残留。
- **证据**:design.md:47 vs :49(全迭代唯一命中);faction-trigger.md:28/:36;trigger-inventory.md:128。

## A3【打回级】design.md §2 残留「升星确认候选迁对账层独立簿记组」——与详设「弃」、landing「宿主不动」口径相反(第二轮 C6 处置未同步总纲)

- **攻击对象**:design.md §2 系统级变化 1;details/deployed-merge.md「TrackedBooks 退役」表 +「关键取舍」;landing 3.2 完成判据。
- **主张原文**:design.md:36"……**TrackedBooks 整体退役**(用户裁定 2026-09-25:消灭第二账——主域可槽位直址后,执行器直址/守卫 expected 侧/锚定写回全部改读主域,**升星确认候选迁对账层独立簿记组**)——表示层治本……"。对照:deployed-merge 退役表"**候选宿主不动**(本就在 cw_reconcile 局旁表);真变更 = 比较基线从 tracked 表改为主域派生视图";关键取舍"升星候选宿主不动、比较基线改主域派生(取)vs **迁独立簿记组(弃)**:候选本就住在 cw_reconcile 局旁表,迁移是无事生非";landing 3.2 判据"候选宿主不动——本就在 cw_reconcile 局旁表"。
- **攻击角度**:第二轮 C6 已判定「迁对账层独立簿记组/新宿主」叙述了一个不存在的搬迁(候选态现役宿主 = cw_reconcile 按局身份旁表),处置落在了 deployed-merge 与 landing——总纲未反查同步。按总纲施工 = 在现存旁表之外另起第二源,正是 C6 指出的事故形态;§5-4 全量同步复查再次失守。次要同段口径差:总纲"锚定写回……改读主域" vs 详设"写回腿**删除**(观察通道本就写主域)"——删除与改读是两个不同动作。
- **证据**:design.md:36;deployed-merge.md:40/:68;landing.md:24;attack2.md C6(处置记录);cw_reconcile.py:73(现役宿主在册)。

## A4【打回级】sim 对拍白名单漏 planner 两项行为修正;「三条建模错误」三文档三口径——判据照字面执行必红

- **攻击对象**:landing.md 3.4 完成判据(+3.5 范围);design.md §1 症状 2;details/register-consume.md「sim 消费」迁移退役清单。
- **主张原文**:landing 3.4 判据:"sim 对拍:同局脚本结果与迁移前一致(**除三条建模错误修正的显式差异:fate → wish_trial、expert → expert_invite 正名,fortune 补 kind**)";design §1:"sim 现役建模**三错**:planner 判据扫备战席(应只场上,用户裁定);planner_fired 全局一次性(应每费用档首 2★ 一次,用户裁定);OVERLAY_KINDS 的 'fate' 张冠李戴";register-consume:"sim **三条**建模错误修正随判据入 kernel(planner 备份扫描/planner 每费用档/fate → wish_trial 与 expert → expert_invite 正名 + fortune 补 kind)"。
- **攻击角度**:①对拍白名单 = {fate→wish_trial、expert→expert_invite、fortune},**不含 planner 两修正**(扫备战席→只场上;全局一次性→每费用档)。planner 修正改变 sim 的 overlay 触发行为:备战囤 2★ 的局旧版弹、新版不弹;多费用档旧版只弹一次、新版逐档弹——银狼滚动投资是成册阵容(研究档 final_yinlang_joy.md 在册),对拍脚本必然覆盖该形状;无论"迁移前"读作迭代前还是 3.4 前,白名单枚举都与本迭代(3.3 判据"planner(合成落场上/2★ 上场/每费用档一次/备战不触发)"明文强制)的行为差异不同集——判据照字面验收必红,或逼 worker 把法定差异判为失败。②"三条"所指三处互不相同:design = planner×2+fate;landing 3.4 = fate/expert/fortune;register-consume 同名"三条"名下列**五**项(且"planner **备份**扫描"系"备战席扫描"笔误)。阶段判据 = 账本 criteria 预注册源,枚举失真即埋不可验收判据(iteration-design §5-4 所防事故的又一形态)。
- **证据**:landing.md:50/:55;design.md:17;landing.md:36(3.3 判据);register-consume.md:64;cw_sim_backend.py:1492-1500(planner_fired 全局一次性)/:1502-1506(判据扫备战席);docs/game/currency_war/research/final_comps/final_yinlang_joy.md(在册)。

## A5【打回级】换算五函数的阶段归属三处互相矛盾,且 3.1 范围按字面施工时序不可行

- **攻击对象**:landing.md 3.1 范围/文件面 vs 3.2 完成判据;details/deployed-merge.md「触面清单」tracked 侧行。
- **主张原文**:3.1 范围"……**0-9 换算层删除**;快照 schema 升版 + 迁移函数;观察链合一写。**不含 TrackedBooks 退役(= 3.2)**";3.1 文件面"……kernel/cw_exec_state.py(换算删除)、测试仓相应断言(清单见详设触面表,**不含 tracked 退役面**)";3.2 判据"**换算层五函数归零**(deployed_slot_no/deployed_row_slot/deployed_idx_of/deployed_rows_to_indexed/deployed_indexed_to_rows,均在 kernel/cw_exec_state.py)";触面清单 tracked 侧行"cw_exec_state(**换算五函数**+容量常量删)"。
- **攻击角度**:①五函数在触面表归 tracked 侧(= 3.2 的设计依据行),3.1 文件面一边声明"不含 tracked 退役面"、一边列"cw_exec_state(换算删除)",范围行又含"换算层删除"——同一工作项 3.1/3.2 双认领且 3.1 内部自相矛盾。②时序不可行:3.1 明确保留 TrackedBooks(退役在 3.2,依赖 = 3.1),而 tracked 随动腿在 3.1 期间仍消费五函数(_track_* 三腿 prep_actions.py:745/:763/:784、wear/tool tracked 腿、reconcile 锚定写回、mutate_bench_deployed——第一轮 P1 证据链;TrackedBooks 类注自证"换算单一源 = cw_exec_state.deployed_row_slot/deployed_idx_of",cw_game_state.py:1931)——3.1 删函数即破坏存活至 3.2 的写腿;不删则 3.1 范围项无法完成。按 3.1 字面施工只有两个出口:越界做 3.2 的活,或留函数不删,都违反阶段边界(账本照此立任务即错)。
- **证据**:landing.md:4/:6/:18/:25;deployed-merge.md:59;cw_exec_state.py:237/:243/:255/:266/:295;cw_game_state.py:1929-1932;attack.md P1 证据列。

## B1【需澄清】「资格集(set)/计数 = |集合|/board 增量口径」三种语义并存;「现役 board 字段 = 其计数视图」身份主张被设计自引的两个事实证伪

- **攻击对象**:details/faction-trigger.md「资格集语义」+ 级联表「羁绊计数视图」「羁绊变更回调」行 +「关键取舍」;design.md C-回调。
- **主张原文**:"**成员资格**(角色对某阵营 F)= 出身阵营 F ∨ 持 F 阵营星徽……资格集族 = 派生存值(dict[faction → set[名]])……羁绊计数 = 集合大小(**现役 board 字段 = 其计数视图,策略消费口不变**)";级联表"计数 = |集合|";关键取舍"羁绊值维护**增量口径(保留)vs 全量重算(弃)**:观察基座含左面板真值的装备贡献(环境卡授予星徽只在面板、行单位 equips 为空,2026-09-18 run 实锤),全量重算抹掉基座真值"。
- **攻击角度**:两个已核事实使「计数 = |资格集|、board = 其视图」不成立:(a)**卡带贡献是多集**——星核猎手卡带无条件 +1(非成员佩戴也计数)、欢愉卡带成员双计(cw_equipment_data.py:226-229 原文;cw_bond_equips unit_bond_tags 对卡带无条件 append、可重复,:141-148;_recount_board 按出现次数累计,:172-184)——单一源(trigger-inventory §3 自定 = cw_bond_equips)产出的是计数多集而非名集;且「出身 ∨ 持徽」的成员资格定义不含卡带,卡带贡献的名既可能不在集内(星核猎手卡带)也可能在集内但计 2(欢愉卡带)。(b)**环境卡授予星徽只在面板、行单位 equips 为空**(设计自引 2026-09-18 实锤)——派生资格集(从 deployed 单位现值算)不含这些贡献,而游戏弹窗真值跟左面板走:S1a 判「资格集大小上穿档线」会漏环境授徽致跨档的真弹窗(反应式兜底接得住,但预测面静默丢失,与迭代立项的提速目标相悖);反之 board 若真改成 |set| 视图,增量基座(面板幽灵计数)被抹——「保留增量」与「= 视图」二选一必弃其一。S1a/S2 三阵营(盛会之星/命运圣杯/列车同行)无卡带、判据语义本身不受 (a) 影响,但 3.3 派生维护(资格集怎么算、board 怎么维护)与「策略消费口不变」承诺在现文本下无唯一解——实现者须在「集合派生覆盖 board」「增量维护 + 判据读派生集」等落法间自行拍板(硬规则 2 形态)。
- **证据**:cw_bond_equips.py:56-72/:141-148/:172-184;cw_game_state.py:2700-2714(_absorb_board_derived:"环境卡星徽等装备羁绊贡献只显于面板、容器行未建模……幽灵计数");faction-trigger.md:19-20/:26/:81-82;trigger-inventory.md:124。

## B2【需澄清】sim 'hack' kind 族(OVERLAY_KINDS 成员/chosen_hack/占位清单)在九 kind 词表与迁移退役清单零处置

- **攻击对象**:details/register-consume.md「kind 词表」「sim 词表处置」「迁移退役清单」;details/trigger-inventory.md §1.3/§3。
- **主张原文**:"sim 词表处置:现役 'fate'(= 圣杯任务链)→ 正名 'wish_trial';现役 'expert' → 正名 'expert_invite';占卜屋补 kind 'fortune'。";迁移退役清单枚举 OverlayQueue/簿记迁移/评估器/事实事件三件套/"sim 三条建模错误修正"——两文档全文无 'hack'。
- **攻击角度**:现役 OVERLAY_KINDS 七成员含 'hack'(cw_sim_overlay.py:41),配套:chosen_hack 写位映射(apply_disclosed_pick :157-158)、占位披露项 hack_trigger/hack_effect(:60-61)、选项采样分支(:121-129)、后端注释将 hack 与 partner/expert/fate/aha 并列(cw_sim_backend.py:40)。而 'hack' 与 planner 同物:cw_sim_overlay.py:16 自注"骇入 = planner 族变体";游戏侧「我来当策划/请选择一个骇入效果」即 货币战争-银狼升星 屏(gameplay.md:76-79)。九 kind 词表无 hack;OverlayQueue 退役、呈现状态机改读 pending(九 kind)后,hack 族符号(OVERLAY_KINDS 成员、chosen_hack 映射、占位清单项)去向无人认领:删除?并入 planner?保留为死词?——实现者须自行拍板(硬规则 2 形态)。fate/expert/fortune 各有显式处置而 hack 沉默,「迁移退役清单」声称的完备枚举失真。第一轮 R1/C3、第二轮 R2 攻击的是词表缺失/命名,未及 hack。
- **证据**:cw_sim_overlay.py:16/:40-42/:60-61/:121-129/:154/:157-158;cw_sim_backend.py:40;gameplay.md:76-79;register-consume.md:28-42/:64(全文无 hack);trigger-inventory.md(全文无 hack/骇入)。

## B3【需澄清】观察吸收键定义自相矛盾:引「现役 _absorb_slot_reorder 键口径」又定为「名字级」——名字级键会把装备真值变化误豁免为重排

- **攻击对象**:details/deployed-merge.md「观察与吸收口径」。
- **主张原文**:"同子表内成员集合相同、排列不同 = 读数抖动,吸收(**现役 `_absorb_slot_reorder` 键口径的槽位化转译**);换排是我们发起的逻辑写,不进观察吸收。**键 = 成员集合(名字级)**,与阶段B 按名分解同口径。"
- **攻击角度**:现役键 = `_rows_unit_key`,实现明示"槽位号不在键内,**装备集在键内——穿戴变化不算重排**"(cw_game_state.py:2675)——装备差帧走失配分流(留证/纠偏),不被重排豁免吞掉。名字级键则"同名 + 异装备 + 异排列"的观察帧被误判为纯重排 → 记 deploy_slot_reorder 豁免行(无告警无停机)而非失配,装备真值变化(冶金炉拆徽、观察纠偏等场景)被静默改道为"游戏重排"。所引"与阶段B 按名分解同口径"同样失真:按名分解显式处理同名单位的装备/星级差(存活单位变更对,faction-trigger.md:27),不是名字级盲等。同一节先引现役键口径(含装备)再定义键 = 名字级,两读本不相容,3.1 实现者须择一(硬规则 2 形态);第一轮 P5 点名的"_absorb_slot_reorder 键定义"待设计项,处置文本自身带矛盾。
- **证据**:cw_game_state.py:2667-2698(尤其 :2674-2676);faction-trigger.md:27;deployed-merge.md:46。

## C1【低】design.md §0 状态字段残留对抗轮次叙事(第二轮 C9 同族处置后以变体复发)

- **攻击对象**:design.md §0。
- **主张原文**:"状态:草案(对抗审中;**两轮攻击 33 条全部处置,待第三轮收敛确认**)"。
- **攻击角度**:§5-3 无过程叙事("不写谁审的、第几轮攻击");§0 状态字段规约取值 = 草案/对抗审中/定稿(iteration-design.md §2.1/附录A);轮次与处置计数属 README 进度面(README.md:13-14 已载同信息,设计正文重复即第二源)。第二轮 C9 对同族措辞("第一轮已落;待第二轮对抗")已出具,处置后以"两轮攻击 33 条……"变体存留。
- **证据**:design.md:6;iteration-design.md:34/:105-107;README.md:13-14。

## C2【低】deployed-merge 引「prep.md §2」作两态制锚,实文在 §3/§6

- **攻击对象**:details/deployed-merge.md「TrackedBooks 退役」表末行。
- **主张原文**:"锚定语义重定义为主域观察锚(观察边界对账唯一发生点不变,两态制不变——**prep.md §2**)"。
- **攻击角度**:prep.md §2 = "画面形态声明",无两态制内容;两态制表述在 §3 对账边界(:24"动作落地判定 = 容器逻辑态直写 + 本帧观察覆盖")与 §6(:84"两态制:逻辑态直写 + 观察覆盖")。同文件触面清单的 tracked 行锚已随第二轮 C8 改为 §6,此行残留旧锚。
- **证据**:screens/prep.md:11/:24/:84;deployed-merge.md:41。

## C3【低】trigger-inventory S6 成员列与 §1.7 用「box_pick」与 kind「box_card」同物并列

- **攻击对象**:details/trigger-inventory.md §1.7 标题、§3 形状表 S6 行。
- **主张原文**:"### 1.7 武装箱选择(**box_pick**)——S6 统一入登记……本迭代改上报直登(**kind = box_card**)";§3 S6 行成员 = "**box_pick**/expert_invite/star_tome"。
- **攻击角度**:S6 行把非 kind 标签(box_pick = sim 相位/op 类既有名)与 kind(expert_invite/star_tome)并列在同一"成员"列,而词表纪律自定「禁新造同物异名」——在 kind 语境下并列呈现,引导实现者在 register/consume 调用里用错名。判据无实害(kind 表为权威),属文内一致性缺口。
- **证据**:trigger-inventory.md:68/:120;register-consume.md:38(kind = box_card)。

---

## 发现计数汇总

| 严重度 | 数量 | 编号 |
|---|---|---|
| 打回级 | 5 | A1 回调集合/判据归位四文档四口径(landing 3.3 与自指依据相反,硬规则 4 第三现);A2 design 残留「synthesis_names 供排除」与零排除裁定冲突;A3 design 残留「升星候选迁独立簿记组」与详设「弃」/landing「宿主不动」相反(二轮 C6 处置未同步总纲);A4 sim 对拍白名单漏 planner 两修正+「三条」三口径(判据必红);A5 换算五函数阶段归属三处矛盾且 3.1 时序不可行 |
| 需澄清 | 3 | B1 资格集 set/计数\|集\|/board 增量三语义并存(卡带多集+环境授徽两事实证伪视图主张);B2 sim 'hack' kind 族零处置;B3 观察吸收键「现役口径(含装备)」vs「名字级」自相矛盾 |
| 低 | 3 | C1 design §0 轮次叙事残留;C2 两态制锚 prep.md §2 应为 §3/§6;C3 S6 成员列 box_pick/box_card 同物并列 |
| **合计** | **11** | |

## 已核实为准确的抽样清单(供定稿信心)

以下主张经权威源直核**准确**(本轮独立复核,与前两轮抽样互补;命中即准确,非穷举):

1. **emit 六处行号全部精确**:deploy_move.py:143、buy_card.py:184/:186、wear_equip.py:187、sell_bench.py:121、sell_deployed.py:78;「5 文件 6 处」计数与三文档(design §1/register-consume/landing 3.5)一致;获得链零 emit(cw_gain_chain.py 无 emit_fact_event)。
2. **zero_writes.py 选卡函数行号全表精确**:pick_megastar:109/pick_partner:117/pick_star_tome:125/pick_wish_trial:133/pick_box_card:141/pick_fortune:149/pick_expert_invite:157——与 kind 表锚逐行相符;「八个有上报的 pick」计数正确。
3. **deploy_move 语义锚**:docstring :57-70(载荷恒 bench 源、空槽放置/占位交换)、:65-66(被占位单位回源 bench 槽)、:143(emit)、:83/:128-130(front_row/back_row 双写,证「紧凑两字段+跨行双写」现状主张)。
4. **数据注册表**:盛会之星 tiers=(2,3,4,5,6)(cw_factions.py:61)、命运圣杯 tiers=(2,3,4,5)(:67);星徽 22 枚区间 cw_equipment_data.py:110-131;:119 命运圣杯星徽效果原文;卡带两分 :226-229(星核猎手无条件/欢愉条件双计);cw_bond_equips.py:37-40 两分 regex 在册;阿哈大悦效果全文(cw_invest_data.py:166,四件选一/变为所选件/送简易武装箱/进阶拆散/回装备栏五要素齐)。
5. **同名唯一前提成立**:board_unique_key(cw_deploy_logic.py:1769-1781,char_id 级、开拓者归一)+ deploy/swap 入口同守卫(cw_vocab.py:1117/:1162);「同名同星≤1 仅为 merge 工作表不变量」(cw_gain_chain.py:169)定性准确;gameplay.md:68「场上同名角色禁双」游戏侧互证。
6. **merge_step_once 载体规则**:cw_gain_chain.py:164「take 含场上 → 场上那个的位置;全备战 → 最左」逐字相符。
7. **容器符号全集**:front_row/back_row 紧凑列表(cw_game_state.py:2079-2080)、TrackedBooks(:1922,bench 定长 9/deployed 定长 10、0-3 前/4-9 后,:1926-1932)、tracked_books(:2275)、tracked_account_observed(:2097)/tracked_unobserved(:1907)、seed_opening_state(:1818)、_write_logic_frame(:2932,行域分支 :2946-2951)、_resync_board_delta(:2741)、_absorb_slot_reorder(:2667)、mutate_bench_deployed_local(:1574)、detect_merge_upgrade(:1385)、lv999_cost_tier(:2380)及 deploy_move 写端(:134)。
8. **换算五函数与容量**:deployed_slot_no/:237、deployed_row_slot/:243、deployed_idx_of/:255、deployed_rows_to_indexed/:266、deployed_indexed_to_rows/:295(均在 cw_exec_state.py);DEPLOYED_FRONT/BACK_CAPACITY = 4/6(:172-174)。
9. **tracked 侧触面**:prep_actions._track_* 三腿(:745/:763/:784)、mutate_bench_deployed(cw_vocab.py:1054;cw_buy_card_action.py:161 调用/:177 读点——「调用与读点」标性准确)、cw_reconcile.reconcile_tracking(:332)、cw_observation.py:2434 与 cw_screen_prep.py:547-548 tracked 读口、mandate.py:1169 tracked 读注。
10. **两段式机制依据成立**:screen_utils.py:368-373——传入列表仅作成员过滤、遍历序 = ctx.screen_loader.screen_info_list 的 loader 序(「重排列表不能改变扫描优先级」准确);CW_DISPATCH_SCREENS 恰 28 项(cw_loop.py:546-557 逐条点数);身份问询区 :1476-1479。
11. **kind 表八个画面名全部真实且在分发清单内**:货币战争-列车同行/盛会之星/银狼升星/祈愿试炼/命运卜者强化/星徽秘典弹窗/备战-武装箱选择/备战-专家邀请函(cw_loop.py:547-556 逐名命中)。
12. **SwapDeploy「词表在册、生产执行器未接线」准确**:CwActionSwapDeployParam(cw_vocab.py:456)+ 上报 swap_deploy.py 在;operations/cw_op/ 无 swap op 文件。
13. **sim 退役符号全部存在**:OVERLAY_KINDS(:40-41)、OverlayQueue(:74)、megastar_fired_tier/planner_fired/planner_seen_star(:748/:743/:746)、_evaluate_megastar/_evaluate_planner(:1472/:1487)、_board_truth/_refresh_board(:1519/:1532)、_on_overlay_picked(:1141)——'fate'/'expert' 在册、'fortune' 缺(与「补 kind」处置相洽)。
14. **OpenTome 双击 bug 在册**:cw_open_tome_action.py:4/:31(docstring「点两次」)+ :72-74(两击间隔 1s 实码);正本四面已勘误(action_ops.md §4.2 经 logic-updates/open-tome.md:46 转引「单击开启」核对)。
15. **S4/S5/S6 现役锚**:pick_encounter _DECL_TRIGGER='battle_resolve'(pick_encounter.py:44);open_box 声明 next_screen='货币战争-备战-武装箱选择'/trigger='open_box'(zero_writes.py:34);open_bookcard 纯转移 next_screen='货币战争-备战-专家邀请函'(open_bookcard.py:30-31);「受影响声明两条」与 open_tome 无 WorldDecl 相洽。
16. **同族先例引文**:ShopSlot「紧凑下标≠物理槽位的历史病灶类(同族)在本模型下结构性消失」逐字(cw_game_state.py:573-574);BenchView(:488)/ShopPayload(:583)。
17. **画面档内容**:megastar.md §1「盛会羁绊激活时弹出……一局可多次」+ §3「候选数 = 场上盛会之星角色数含持星徽者」(:8/:16);wish_trial.md「叠备战、挡出战」(:3);aha_equip_pick.md「不选 → overlay 持续卡备战」+ 锚 = 备战.标识-简易装备(:7);bookcard.md = 货币战争-星徽秘典弹窗档、点卡即选、接管方 CwScreenBookcard(:3);op-layer.md:51 满栏自动多买至 3 的倍数。
18. **正本更新清单锚存在性**:fields.md §3.2.3/§3.2.4(:239/:253)、projection_contract.md §4/§4.1、architecture.md、sim-design.md/sim-wiring.md、flow/outer_loop.md §2.2、screens/op-layer.md §1.2、logic-updates/open-tome.md、invest_effects.md(docs/game/currency_war/research/)、gameplay.md 银狼段(:75-79,含「5费升 2 星也触发/双装备」与每费用档口径的勘误基础)、megastar.md/planner.md 均在。
19. **基础设施**:bind_session_container(:1743)、note_obs_event(:2524)、cw_overlay_registry(存在,round2 核过,本轮 kind 表 screen_name 注释所指真实)。
20. **「后 7-10 槽」引用源成立**:gameplay.md:72/:88(「后台 6→7……还可能 8/9/10」「后排槽位 6/7/8/9/10 随 level+宝钻动态」)——设计口径随其引用的游戏知识档;代码侧 back_layout 值域 6-9、>9 域外超集(cw_back_layout.py:6/cw_game_state.py:2082)为另一层保守处理,与设计主张不构成矛盾。
21. **事实事件三件套**:FactEvent/FACT_EVENT_KINDS/set_fact_event_sink(cw_event_hooks.py,emit_fact_event :50)。
22. **「触发时点 ≠ 状态达成时点」的代码支撑**:buy_card.py:157-162(pre_bench/pre_dep 快照 + detect_merge_upgrade :161)与序贯 B 叙述相容。
