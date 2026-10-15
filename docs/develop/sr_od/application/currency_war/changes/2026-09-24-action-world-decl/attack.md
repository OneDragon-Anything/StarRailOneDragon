# 2026-09-24-action-world-decl 设计对抗审报告

## 结论行

**阻断级 4 / 缺陷级 5 / 建议 5 —— 不收敛，不可定稿。** 三核结论：核一（无前提）不通过——总纲/详设/landing 的结构完整性与锚存在性总体良好，但详设有 4 处关键主张与现役代码直接冲突（含一处 next_screen 非档名值、一处推导规则自相矛盾、一处喂入点指错文件、一处依赖方向未裁决），3.2 阶段按文不可开工；核二（规范遵循）部分通过——文档构成齐、七件齐、无过程叙事，但「依据就地标注」有 5 处锚错/跨迭代引用，「实现者无需再设计」在 4 处语义选择上无答案；核三（治本）成立——归层正确（三处并行实证），声明化修的是根，trigger 收敛有准入判据与单一源，残留结构问题即阻断项 A2/A3。

修复 A1–A4 并完成全量同步复查后需再过一轮试读。

---

## 一、发现清单

### 阻断级

**A1｜`node_advance` 的 next_screen 推导规则自相矛盾（off-by-one），与自称权威的 backend 推导直接冲突**
- 位置：details/world-decl.md §2「`node_advance` 的 next_screen 推导规则」代码块；design.md §2.2 契约 1
- 发现：规则两行在「eff 读数时机」的任一读法下都有一条是错的。总纲 §2.1 明确声明在「**写完容器后**构造后果声明」，此时 `effective_node_ord(gs)` 已是新节点序（现役 `report_node_advance` = `advance_node_effective(gs, effective + 1, ...)` 后才到构造点，cw_game_state.py:3243-3247）。则：
  - 读法一（按总纲时序，eff = 新序）：局终分支「eff 超出总长 → ''」与 backend `_on_node_advance` 一致（cw_sim_backend.py:959 `eff > sum(len(node_sequence_of(p)) for p in (1,2))` → game_over ✓），但「下一序 = eff+1 → 映射」错——backend 映射的是 **eff 本身**（cw_sim_backend.py:965 `plane, r = self._ordinal_to_node(eff)` → `_enter_node_window(plane, r)` 呈现新节点屏），按 eff+1 推导则**每个节点推进的声明都指向再下一个节点的画面**，系统性错一位；
  - 读法二（eff = 推进前旧序，映射 eff+1 = 新节点则对）：局终分支错一位——P2 末节点确认时旧 eff = 16 = 总长，「16 > 16」不成立 → 落入映射 ordinal 17 → 超出 P1+P2 辖域（`_ordinal_to_node` 该域越界即 raise，cw_sim_backend.py:1120）。**恰在详设自己反复强调的局终旗舰场景（design.md §2.1/§2.2、详设 §4 依据②）上崩**。
- 依据：src/sr_od/application/currency_war/kernel/cw_game_state.py:3209-3254（report_node_advance 先进后广播）；sim/cw_sim_backend.py:949-967（eff=新序、超界局终、映射 eff）。
- 修订建议：规则改为单读法——构造点（推进后）取 `eff = effective_node_ord(gs)`；`eff > P1+P2 总长 → ''`；否则 `eff → (plane, round) → kind 映射`（与 `_ordinal_to_node`/`_screen_for_node` 同映射）；`plane>1 ∧ round==1 → 位面过渡`。并同步修对照表 #1/#2 的「规则见下表」引用。

**A2｜supply_confirm 喂入点指错文件；一次补给动作产生两份声明，单声明契约未定义如何并喂**
- 位置：details/world-decl.md §4 喂入落点括注「settle/supply_confirm 的喂入点 = `cw_op_settle_confirm` 的确认上报出口，同函数两 kind 由 `report_node_advance` 声明归一」；landing.md 3.2 文件面
- 发现：现役 **supply_confirm 从补给动作 op 发出**，不从结算 op：`cw_pick_supply_action.py:84` `report_node_advance(gs, trigger='supply_confirm')`；`cw_op_settle_confirm` 只发 settle_confirm（cw_op_settle_confirm.py:77）。按设计实现（喂入只加在 cw_op_settle_confirm），sim 在补给节点选卡后将**收不到 node_advance 声明** → 世界停在补给屏不推进，3.2 的 e2e 对拍判据必然暴露卡死。连带两个缺口：① landing 3.2 文件面列了 `cw_op_settle_confirm.py` 却**漏 `cw_pick_supply_action.py`**（supply_confirm 喂入行的真实落点）；② 现役补给动作 op 一次上报两支——`report_action_pick_supply_param`（pick_supply 声明，对照表 #12）+ `report_node_advance`（node_advance 声明，对照表 #2）——schema 是一 LogicOutcome 一 `world_decl`、喂入契约是「自上报后一行」，**双声明怎么并喂（两次 declare_world？round data 带哪份？）设计无答案**。
- 依据：operations/cw_op/cw_pick_supply_action.py:76-84；operations/cw_op/cw_op_settle_confirm.py:64-78,130；kernel/cw_event_hooks.py:137-153（applied=True 出口广播，一支一装饰器）；screens/op-layer.md §1.2（正本亦写「节点推进上报（**结算/补给确认**的 report_node_advance 调用）」——正本都知道补给确认不在结算 op）。
- 修订建议：喂入落点改为「settle_confirm → cw_op_settle_confirm；supply_confirm → cw_pick_supply_action（与 pick_supply 声明同 op 两支，各随各自上报出口喂 declare_world）」；landing 3.2 文件面补 `cw_pick_supply_action.py`；§4 补一段双声明并喂契约（含 round data 只携其一时的取舍规则）。

**A3｜推导规则的「kernel 节点序列机器」实际住 sim 包，kernel 侧有明文架构锁禁 import sim，设计未给归属裁决**
- 位置：details/world-decl.md §1「单值依据」（「kernel 节点序列机器 `node_sequence_of`/`effective_node_ord`」「上报函数与 backend 同住 kernel，调用 = 复用单一源非复制」）
- 发现：`node_sequence_of` 定义在 **`sim/cw_sim_plane_schedule.py:45`**，不在 kernel；kernel 内现无任何 import sim 的先例，且 `kernel/cw_deploy_logic.py:90` 明文「不 import cw_sim——sim 消费本模块，反向 import 成环」、:135「import cw_sim 的架构锁由依赖方向保证」。让 kernel 的 `report_node_advance` 调 `node_sequence_of` 构造 next_screen，三条路都没答案：① kernel import sim 模块 = 违反在册架构锁；② 把序列机器迁进 kernel = 触碰 sim 全部消费点（backend/生成器/测试），不在 3.1/3.2 任何文件面内；③ kernel 复制一份表 = 被设计自己禁止（「复用单一源非复制」）。实现者撞墙必须自行拍板 = 违反定稿门槛（iteration-design §5 规则 2）。
- 依据：sim/cw_sim_plane_schedule.py（模块全貌：纯数据零依赖，迁 kernel 无技术障碍）；kernel/cw_deploy_logic.py:90,135；grep 全 kernel 无 sim import（本次实测）。
- 修订建议：三选一并写进详设 §1：把 `cw_sim_plane_schedule` 的真值表迁为 kernel 模块（backend 改 import，文件面补入 3.1 或 3.2）；或推导不查序列表、改为**读 backend 同款映射的 kernel 侧等价物**（`NodeKey.kind` 已在容器 `gs.node` 新值上，直接按新节点 kind 映射画面即可，根本无需序列表——见修订后的 A1 规则：eff→(plane,round) 反解可以省略，容器 NodeKey 自带 plane/round_num/kind）；或显式豁免本条架构锁并记 why。注意修订后规则只需「新节点 kind → 画面档」一个映射，`gs.node.value.kind` 即真值，A3 可随之消解。

**A4｜对照表 #3/#4 next_screen = `'货币战争-战斗等待'` 不是 screen_info 档名，且与 sim 现役呈现矛盾**
- 位置：details/world-decl.md §2 表 #3 start_battle、#4 pick_encounter 的 next_screen 列
- 发现：三重错误。① 权威性：本篇自设「画面档名字面值权威 = `assets/game_data/screen_info/` 各档 + `sim/cw_sim_backend.py` 档名常量」（详设 §问题与约束），但 screen_info 档名集与 backend 常量集中**均无**「货币战争-战斗等待」——它是 journal 上下文名/op 名（cw_game_state.py:275 `BATTLE_WAIT_CONTEXT`；CwScreenBattleWait 的 op_name），非画面档。② sim 行为：`battle_resolve` 腿 `_resolve_battle` 终态呈现 `SCREEN_SETTLE = '货币战争-结算'`（cw_sim_backend.py:185,1340；模块注释还专门记录了 T-2 初版取错档名致推进链不可达的教训）→ §3 对账面「实际画面 == next_screen 等值断言」**每场战斗必失配**。③ 设计自引依据自相矛盾：#3 行内标注「sim `_resolve_battle` 呈现结算页」，结算页 = '货币战争-结算' ≠ 表值。对照测试若按表实现 = 把语义错误钉进 schema。
- 依据：grep screen_info 全部 yml `screen_name`（无「货币战争-战斗等待」，实存 = 货币战争-战斗结算/结算/结算-失败/结算-战报/结算-对局详情）；sim/cw_sim_backend.py:180-185,1340-1341；kernel/cw_game_state.py:275。
- 修订建议：#3/#4 next_screen 改 `'货币战争-结算'`（与 trigger=battle_resolve 的 sim 呈现一致，对账可成立）；实机侧该值仅作 journal 记账料，同样以结算档为准。

### 缺陷级

**D1｜`report_node_advance` 现役返回 `bool`，不是 LogicOutcome——「声明随 LogicOutcome.world_decl 返回」契约对它不成立，签名改形未申报**
- 位置：design.md §2.2 契约 2；details/world-decl.md §2 表 #1/#2 上报落点、§1 构造义务
- 发现：契约要求「构造声明是上报函数 `applied=True` 出口的义务」且载体 = `LogicOutcome.world_decl`；18 个上报落点中 17 个返回 LogicOutcome，唯 `report_node_advance` 返回 `bool`（cw_game_state.py:3209-3210「返回 True = 实际推进落账」），且有两个 op 级消费点按 bool 消费（cw_op_settle_confirm.py:64,77,130 `_advanced` 记日志；cw_pick_supply_action.py:83-84）。改成返回 LogicOutcome（applied=advanced）是自然修法，但属 kernel API 签名/语义变更，设计零申报，实现者需自定出口形态。
- 依据：kernel/cw_game_state.py:3209-3254；两处调用点（见上）。
- 修订建议：详设 §1 构造义务段补一条「report_node_advance 返回形态 bool → LogicOutcome（applied=推进落账位），两个 bool 消费点随 3.2 改造」，或改走 A3 修订建议的独立声明构造函数并声明之。

**D2｜详设 §4 喂入落点列 `cw_pick_invest_env_action`——该 op 不存在**
- 位置：details/world-decl.md §4 喂入落点清单
- 发现：现役投资两屏**同指一个 op**：registry 行 `CwActionPickInvestEnvParam: CwActionPickInvestOp`（cw_action_registry.py:204，行注释「投资两屏拆类后两行同指一 op」），实体在 `cw_pick_invest_action.py`（同文件双 param 分派上报）。`cw_pick_invest_env_action` 无文件无类。违反「全量同步复查：逐一核设计引用的每个符号/路径存在性」（iteration-design §5 规则 4 卡点）。
- 依据：operations/cw_op/cw_action_registry.py:199-210；glob/grep 全仓无 cw_pick_invest_env_action。
- 修订建议：落点清单改为 `cw_pick_invest_action`（env/strategy 两 param 同 op，声明随各 param 的上报出口各构造各喂）。

**D3｜对账面等值断言在多个「设计内」场景必然失配（缺陷警报噪声），局终空串断言机制未定义**
- 位置：details/world-decl.md §3「对账面」
- 发现：① node_advance 推进后，若 overlay 队列非空，backend 走 `_window_resume='offer'` + `_present_pending_overlay` 呈现巨星/策划屏（cw_sim_backend.py:1209-1211）——实际画面 ≠ 推导的节点屏，**总纲 §2.1 自己举的「部署/买牌触发盛会之星」就是这个场景**；② offer 日程命中时呈现投资策略屏而非节点屏（cw_sim_backend.py:1224-1241）；③ 节点窗让路期间选卡族模态交回走 `_dismiss_modal` 恢复位 → 恢复到 offer 屏/节点屏，与选卡族 next_screen='货币战争-备战' 失配——设计只说「对账在该出口做」，未定义这些**建模内合法失配**的豁免口径，漂移警报通道将被设计内行为刷满噪声；④ 「局终空串 = 断言局终态成立」未定义断言载体（断 `done` 位？断 SCREEN_LOBBY？`_game_over` 实际呈现的是 '货币战争-大厅' 非 ''，cw_sim_backend.py:1425-1432——按字面等值必炸）。
- 依据：sim/cw_sim_backend.py:1043-1071（_dismiss_modal 恢复位三态）、1064-1071（_after_modal_pick）、1206-1242、1425-1432。
- 修订建议：对账面改口径——advance 后实际画面 ∈ {decl.next_screen} ∪ 建模内让路集（overlay 呈现屏、投资策略 offer 屏），或对「声明 next_screen = 节点屏/底层屏」的 advance 断言**底层画面**而非最上层呈现；局终空串明确断言载体（建议 = `backend.done` 为真 ∧ 呈现 ∈ {大厅}）。

**D4｜design.md §1 依据锚错：终结判定总表在 screens/README.md §6，非 §4**
- 位置：design.md §1 现状症状①「（交回与否，`screens/README.md` §4 终结判定总表）」
- 发现：screens/README.md §4 = 「动作词表与执行载体」，§6 = 「回外循环(终结)语义总表」。锚指向真实存在的节（iteration-design §7 核一）不成立。
- 依据：docs/develop/sr_od/application/currency_war/screens/README.md:40（§4 标题）、:132（§6 标题）。
- 修订建议：锚改 §6。

**D5｜关键定案依据跨迭代引用 changes/ 工件（flow-seam 附录 B），锚寿命必死于上游迭代清理**
- 位置：design.md §1 明确不解决 #2/#3、§2.1「交回与转移正交」依据①；details/world-decl.md §4 交回判断依据①、关键取舍「terminal 保留而非吸收」「喂入点在动作 op 内」
- 发现：flow-seam.md 位于 `changes/2026-09-23-sim-backend-unification/details/`——**上一迭代的 changes/ 过程区**。AGENTS.md 铁律「changes/ 会不定期、无理由删减」+ iteration-design §1 引用寿命分层：本迭代设计文档引用它属长寿命引用短寿命锚，而该依据承载的是本迭代的定案级语义（交回与转移正交、terminal 保留的全部论证）。
- 依据：glob 定位 flow-seam.md 路径；AGENTS.md「双层文档流」节；docs/develop/harness/iteration-design.md §1。
- 修订建议：把所依赖的两条事实就地落锚到持久源——① refresh 族 terminal=True 无转移：`operations/cw_op/cw_refresh_shop_action.py:46` + `screens/README.md` §6；② 点击源不入事件集：`sim/cw_sim_backend.py:820-836`（_handle_click_source 逐 case）。flow-seam 仅可作迭代内旁证。

### 建议

**S1｜退役清单「装饰器应用 17 处」实数 16 处**
- 位置：details/world-decl.md §6 退役清单
- 发现/依据：grep `transition_event_on_applied` 计数 = cw_action_report 下 8 个具名文件各 1 处 + zero_writes.py 8 处 = **16**；另加 `report_node_advance` 内 emit 调用 1 处（清单已单列）。验收是 grep 归零故不挡 3.4，但数字是可复核事实，照实改。

**S2｜pick_invest_env/strategy 的 next_screen='货币战争-备战' 隐性耦合现役 offer 日程**
- 位置：details/world-decl.md §2 表 #7/#8
- 发现/依据：sim 中投资策略 offer 呈现于节点窗内（`_present_offer_or_node_screen`），选卡交回后呈现**该节点自己的屏**——补给/遭遇/boss 节点则非备战（cw_sim_backend.py:1244-1283）。现值成立仅因日程 P1r3/P2r2/联席 2-6 恰都是 battle/reward 节点（cw_sim_plane_schedule.py:23-31 + cw_sim_backend.py:386,393）。建议表内注明该耦合；日程扩面时此值须随节点 kind 推导化。

**S3｜「观察赢」的引用锚不精确**
- 位置：design.md §2.1「（「观察赢」，flow/README §3）」
- 发现/依据：术语「观察赢」定义在 flow/README.md 卷首术语注（:7），§3 是各篇导读。锚可改「flow/README 卷首术语注」。

**S4｜advance 对集外 trigger 的处置未声明——现行事件系统 Value 响亮防线的去留**
- 位置：design.md §2.2 契约 1/5；details/world-decl.md §3
- 发现/依据：现役 `emit_transition_event` 对集外 kind ValueError 响亮（cw_event_hooks.py:110-113），总纲 §1 还把它列为现行防漂移优点；新机制 trigger 封闭集（9+空）的集外处置（响亮 raise？缺陷留证？）无答案。建议声明与旧机制同等响亮。

**S5｜待核核定规则引用的 overlay registry 对 #14 pick_fortune 空转**
- 位置：details/world-decl.md §2 待核核定规则（「交回目标 = 该 overlay 的底层屏（overlay registry 条目所在分发域）」）
- 发现/依据：「货币战争-命运卜者强化」**不在** OVERLAY_REGISTRY（kernel/cw_overlay_registry.py:97-365 全表无此条；其分发走独立画面域 cw_screen_fortune）。规则对 6 个待核值之一不可机械执行（本次按「底层屏 = 备战」语义径直核定，值本身不受影响）。建议规则补一句「registry 外屏按其宿主画面域底层屏」。

---

## 二、待核值核定表（详设 §2 表 #12–#17 终值）

核定口径：优先 screens/<篇>.md §5 交回落点名值；无名值者按详设核定规则取 overlay 底层屏；sim 侧以 `advance` 后状态机呈现屏复核等值可成立。

| # | 动作 | 核定终值 | 依据 |
|---|---|---|---|
| 12 | pick_supply | `'货币战争-补给'` | screens/supply.md §5 选卡派发行交回落点无名值（交回外循环）；supply 屏在册且选卡后本瞬间画面不变——sim `_on_supply_picked` 零画面写（cw_sim_backend.py:969-979），状态机停留 SCREEN_SUPPLY；registry 条目在册（cw_overlay_registry.py:296-305）。注意：该值只在 A2 修订的「双声明模型」下自洽（随后到的 node_advance 声明才切走）。设计原候选成立 |
| 13 | pick_partner | `'货币战争-备战'` | screens/partner.md §5 交回落点无名值 → 核定规则取底层屏；列车同行为 registry decision 条目（cw_overlay_registry.py:99-108），叠备战；sim `_dismiss_modal` 恢复底层 prep。设计原候选成立 |
| 14 | pick_fortune | `'货币战争-备战'` | screens/fortune.md §5 交回落点无名值 → 底层屏；命运卜者强化 overlay 叠备战（registry 外屏，见 S5）；sim 恢复面同型 |
| 15 | pick_wish_trial | `'货币战争-备战'` | screens/wish_trial.md §5 **明示**「round_success 交回外循环重分发**（回备战）**」；祈愿试炼 registry 条目叠备战（cw_overlay_registry.py:109-120） |
| 16 | pick_star_tome | `'货币战争-备战'` | screens/bookcard.md §5 交回落点无名值 → 底层屏；星徽秘典弹窗为 registry decision 条目叠备战（cw_overlay_registry.py:271-280，正文「不放行备战分支」= 叠备战语境）；点卡即选弹窗自关（bookcard.md §1） |
| 17 | pick_expert_invite | `'货币战争-备战'` | screens/expert_invite.md §3 **明示**「弹窗关回备战」+ §5 交回外循环重分发；overlay 档 = '货币战争-备战-专家邀请函'（registry cw_overlay_registry.py:281-290） |

六值均可直接回填对照表（landing 3.3 的「附带盘点」可凭本表收口，无须再等落地批现核）。

---

## 三、试读结论（逐 landing 阶段：凭总纲+详设能开工吗）

| 阶段 | 试读结论 | 卡点 |
|---|---|---|
| 3.1 声明基建 | **可开工** | WorldDecl 形状、LogicOutcome 字段（frozen dataclass 加缺省尾字段，构造点兼容已核）、declare_world 端口（未装 no-op 与 sim_or_live_* 族同型先例）、advance 骨架均有明确规格；文件面全部实存。对账骨架受 D3 边界口径缺口影响，但骨架本体不挡 |
| 3.2 主链声明化 | **不可开工（按文）** | A1 推导规则 off-by-one（锁错值/局终崩）；A2 supply_confirm 喂入点指错文件 + 双声明并喂无契约 + 文件面漏 cw_pick_supply_action.py；A3 kernel→sim 依赖无裁决；A4 对照表 #3/#4 值非档名；D1 report_node_advance 返回形态未申报。五项修复并全量同步复查后可开工 |
| 3.3 选卡族/箱/书册卡/关店 | **有条件可开工** | 待核六值本报告已核定（可直接回填）；D2 落点名 cw_pick_invest_env_action 需先改；pick_supply 双声明同样受 A2 约束；其余 12 动作的 trigger/next_screen 与现役逐一核对无冲突 |
| 3.4 转移事件退役 | **可开工** | 退役符号全部实证在役（cw_event_hooks.py 全套、backend 订阅/install_backend:1482、测试断言 test_cw_sim_seam.py:176-192 与 test_cw_sim_backend.py:193,720）；S1 计数笔误不影响 grep 归零验收 |
| 末阶段 正本更新 | **可开工** | 清单 5 条锚全部实存：sim-design.md §6.3「kernel 事件钩子槽」在册；sim-wiring.md、flow/action_ops.md、screens/op-layer.md §1.2 在册；projection_contract.md §3.6 = §3 写入端不变式条目 6「期望态两执行面同源」在册（:79） |

---

## 四、全量同步复查（符号/路径/锚存在性核对记录）

设计引用的符号与锚，本次逐项核验结果：

- **实存且语义相符**：`TRANSITION_EVENT_KINDS` 18 成员（cw_event_hooks.py:59-78）；装饰器/emit/sink 机制全套；FACT_EVENT_KINDS 保留面；`LogicOutcome` 形状与 applied 语义（cw_game_state.py:1498-1520）；`report_node_advance` 签名与观察态门（:3209-3254）；backend `on_transition_event` 13 组 case 与详设 §3 分派表逐行一致（cw_sim_backend.py:900-934）；`_on_open_box`/`_on_box_picked`（gain_equipment 入栏 + dismiss）/`_on_supply_picked`/`_on_invest_picked`/`_on_overlay_picked`/`_dismiss_modal`（三态恢复位）/`_on_node_advance`/`_resolve_battle`/`_screen_for_node`/`_after_modal_pick`（opening 第二腿 = `gs.node.value is None` ✓ 推导可靠性成立，现役两个呈现点下 env 恒开局/strategy 恒非开局）；`gain_equipment`「equips 追加 + 送单位回调 + 无升星判断」（cw_gain_chain.py:511-530）；zero_writes 8 个占位上报（与对照表「上报落点」列逐行一致）；open_bookcard 腾席写端 / close_shop 离屏写端（各在其上报函数内，写端归属判据逐行核真）；refresh 族 terminal=True 无转移（cw_refresh_shop_action.py:46）；terminal 登记面与消费点（cw_screen_prep.py:761-763 `_op_cls.terminal` → `_terminal_exit`；cw_screen_shop.py:699）；`OperationRoundResult.data: Any`（operation_round_result.py:24）；端口五口形状与 declare_world 兼容性（cw_sim_ports.py）；`container_snapshot`/`run_sim_full_match`（sim_backend_runner.py:177,270）；`NODE_ADVANCE_TRIGGERS` 封闭集与 `_NODE_ADVANCE_ACTORS`（cw_game_state.py:3166-3171）；测试仓转移事件断言在册（退役清单「测试断言盘点」依据成立）。
- **不实/错位**（已入发现清单）：'货币战争-战斗等待'（A4）、`cw_pick_invest_env_action`（D2）、screens/README §4→§6（D4）、「kernel 节点序列机器 node_sequence_of」（A3）、装饰器 17 处（S1）、flow/README §3 观察赢（S3）、flow-seam 附录 B 跨迭代锚（D5）。
- **landing↔design 同步**：阶段设计依据所引节全部实存；文件面除 3.2 漏 cw_pick_supply_action.py（A2）外均实存且与本迭代改动面相符；正本更新清单 5 条锚全实存。
- **文档构成（核二）**：README 索引/总纲四节（§0–§2 含 §2.3 详设划分）/详设三部分（问题与约束/方案/关键取舍）/landing 阶段小节七件——齐；无过程叙事——合规。

---

## 复审（修订后第二轮）

### 结论行

**不收敛（部分收敛）：阻断 1（R1，A1/A3 修订方向错误复发）/ 缺陷 0 / 建议 0。** 第一轮 9 项发现中 7 项（A2/A4/D1/D2/D3/D4/D5）确认修复且未引入新矛盾，5 条建议（S1–S5）全部采纳落实；唯 A1+A3 的合并修订把推导数据源改成了「容器 NodeKey 真值」——该前提与现役容器语义不符，off-by-one 以新形态复发且局终/位面切换两分支全错，design.md 契约 1 随之带病。R1 修复并全量同步后需再走一轮定点试读（仅 3.2）。

### 复审声明（攻击者自查）

第一轮 A3 修订建议中「eff→(plane,round) 反解可以省略，容器 NodeKey 自带 plane/round_num/kind」一句**是错误建议**——NodeKey 镜像携带的是旧节点键（见 R1 依据 3），本轮修订沿该建议走偏；复审以现役代码证伪并纠正，责任在攻击者侧。

### R1（阻断）｜修订后 node_advance 推导规则的数据源前提不成立：`gs.node` 在推进落账后仍是旧节点键

- 位置：details/world-decl.md §1「单值依据」（修订段）、§2 推导规则代码块（`node = gs.node.value`）与「落地核对点」；design.md §2.2 契约 1（「推导权威源 = 容器 NodeKey 真值…零序列表依赖」）
- 发现：规则四行全部建立在「推进落账后 `gs.node` 即新节点真值」上，但现役容器语义相反：
  1. `advance_node_effective` 只写 `node_ord`（write_logic）与 `node_hist_ord`，**不写 `gs.node`**（cw_game_state.py:3199-3205；:3074 明注「序号前进唯一入口 = advance_node_effective」，派生写口 `_derive_write` 只辖类型直定）；
  2. `gs.node`（Field[NodeKey]，:2051）的写端 = 观察漏斗（:3000「`gs.node` 观察镜像写端保留在漏斗」）、类型派生 `_write_derived_node_type`（:3361）、sim backend `_enter_node_window`（observe 写新键）——三者都在声明构造点**之后**；
  3. 现役代码自证：`cw_op_settle_confirm.py:124`「report_node_advance 只推进 node_ord，**镜像读值本身不随推进变**」；`node_kind_of`（:3627-3630）读的正是该镜像。
- 后果（逐分支）：
  - **kind 映射错一位**：P1r4(battle) 确认 → 新节点 P1r5(supply)，规则读旧 kind=battle → 声明 `'货币战争-备战'`，backend 进窗呈现 `'货币战争-补给'`（cw_sim_backend.py:949-967,1250-1256）——对账系统性失配、journal 错值，A1 以「恒指旧节点」形态复发；
  - **位面切换分支失效**：P1r9(boss, plane=1) 确认 → 新节点 P2r1 应声明 `'货币战争-位面过渡'`；旧键 (1,9) 落 kind 映射 → `'货币战争-BOSS简报'`；
  - **局终分支永不可达**：旧节点 kind 恒在五类映射域内 → 「kind 不在映射域 → ''」永不触发；P2r7(boss) 末确认声明 BOSS 简报档而 backend `_game_over` → 大厅 → 详设 §3 新局终断言（`done ∧ 大厅`）必炸；
  - **「落地核对点」不可执行**（§2:75「eff=17 时 NodeKey kind 取值/守卫分支，对照测试按核对结果锁定」）：eff=17 时容器内**不存在**对应 NodeKey（镜像停在 P2r7），预设的「取值」无从核对；且「按核对结果锁定」= 把局终语义留给实现期发现，违反 iteration-design §5 规则 2（「看情况/待定」= 未定稿）。
- 「零序列表依赖」立论本身不成立：新节点的 kind 在构造时刻容器内**任何位置都不存在**——NodeKey 未写；`chain_node_type`（:3382-3405）诚实缺位 = None 禁猜，且链写端 = 过渡屏/备战帧观察（:84-85），settle 时点无「下一位面链已在位」契约。要推出新节点画面绕不开序列真值，其在役唯一宿主 = `sim/cw_sim_plane_schedule.py`（A3 的原发现仍然成立，只是换了表述藏进了「NodeKey 真值」）。
- 修订方向（三选一，设计方裁决后全量同步 design.md 契约 1、详设 §1/§2、landing 3.2 范围与判据）：
  - **(a) 序列真值表迁 kernel**（推荐）：`cw_sim_plane_schedule.py` 纯数据零依赖已核，迁为 kernel 模块、backend 改 import；推导 = 推进后 `effective_node_ord(gs)` → kernel 公式反解 (plane, round)（`node_ordinal_of` :284-287 / `_node_key_for_ord` :3120-3126 现成；公式 = 9/位面，与 backend 变长累加在 P1+P2 域重合的前提 P1=9 须随注声明）→ 表取 kind → 映射画面；`eff > P1+P2 总长 → ''`。保住双维契约与实机 journal 记账。landing 3.1 或 3.2 文件面补该迁移。
  - **(b) node_advance 的 next_screen 恒 ''**（改动最小）：语义 =「声明不携带，backend 自派」；backend `_on_node_advance` 自派画面、对账对其自洽（断言窗呈结果与自身推导一致）；实机 journal 对 node_advance 类无预期画面。须同步收窄总纲 §2.1 消费表（node_advance 行 sim 退化为 trigger-only）与详设 §7 对照测试（该类只校验 trigger）。
  - **(c) 构造点延后到「新键已写」——否决**：不存在这样的 kernel 侧时机（新键由观察写），供裁决时排除。
- 同步面（R1 修复时一并改）：① design.md 契约 1 的「容器 NodeKey 真值…零序列表依赖」句；② 详设 §1 单值依据段、§2 规则块与落地核对点；③ landing 3.2 范围「按 NodeKey 真值映射推导」句与完成判据「含局终分支核对——P2 末确认在现役观察态门内的形态」（同病的实现期核对措辞，改为按修订后规则确定性锁定）。

### 已确认修复项（第一轮 → 复审核对）

| 项 | 修订落点 | 复审核对 |
|---|---|---|
| A2 | 详设 §4 喂入点核对 + 多支并喂契约；landing 3.2 文件面补 `cw_pick_supply_action.py` | ✅ 喂入点与现役一致（settle→结算 op；supply_confirm→补给 op :84）；并喂契约自洽：每支上报出口各跟一行喂入，顺序 = 现役事件序（pick_supply 先、node_advance 后），data 携带最后一份——定义明确无歧义 |
| A4 | 对照表 #3/#4 = `'货币战争-结算'` | ✅ 与 SCREEN_SETTLE（cw_sim_backend.py:185,1340）及 screen_info 档名集一致 |
| D1 | 详设 §1「签名改形申报」；design 契约 2；landing 3.2 范围/文件面/依据 | ✅ bool→LogicOutcome、applied=推进落账位、两个 bool 消费点随 3.2 改造——三处同步一致 |
| D2 | 详设 §4 `cw_pick_invest_action`（一 op 双 param）；landing 3.3 同步 | ✅ 与 registry :204-205 一致 |
| D3 | 详设 §3 对账面改「底层稳态画面 == next_screen」+ 三条豁免集 + 局终断言载体（done ∧ 大厅）；design 契约 5 同步 | ✅ 可执行：稳态判定可落在现有状态面（`_window_resume` 消费完、无挂起交回、overlay 队列空）；豁免集与现役让路/呈现路径逐一对应；`_game_over` 呈现大厅（:1425-1432）引用行号核对无误 |
| D4 | design §1 锚改 screens/README.md §6 | ✅ |
| D5 | flow-seam 引用全部移除，改持久锚（`_handle_click_source` 逐 case、refresh terminal 登记 + screens/README §6） | ✅ 三文档 grep 无 flow-seam/战斗等待/「17 处」残留（仅 attack.md 历史记录，合法） |
| S1–S5 | 退役清单 16 处 ✅；表 #7/#8 offer 日程耦合注 ✅；「flow/README 卷首术语注」✅；集外 trigger ValueError（详设 §3 + design 契约 5）✅；#14 行注「registry 外屏按宿主画面域底层屏」✅ | 全部采纳落实 |

### 全量同步复查（第二轮）

- 新增/改动的引用锚逐个核对：`cw_sim_backend.py:959-965`（eff 即新序）✓、`:1425-1432`（_game_over→大厅）✓、`cw_pick_supply_action.py:84` ✓、`node_ordinal_of`/`_node_key_for_ord`/`chain_node_type` 行号（本轮复审新查证，供 R1(a) 采用时引用）✓；kernel 禁 import sim 架构锁锚（cw_deploy_logic 模块注）✓。
- landing↔design 一致性：3.2 范围/判据与详设 §1 签名改形、§4 并喂契约同步 ✓；3.3 依据/文件面与回填终值、投资两屏落点同步 ✓；正本更新清单 5 条锚不变且实存 ✓。
- 带病同步面：design.md 契约 1 与详设 §1/§2 的「NodeKey 真值」表述同源错误——已并入 R1 同步面，修复时三处一并改。
- 文档构成/无过程叙事：修订稿仍合规；README 进度行已更新为「设计对抗:进行中」并带第一轮计数，收敛后按本节结论刷新即可（进度面，不构成发现）。

### 试读结论（第二轮，仅更新受 R1 影响的面）

| 阶段 | 结论 |
|---|---|
| 3.1 声明基建 | **可开工**（不变；若采 R1(a)，序列表迁移并入本阶段文件面） |
| 3.2 主链声明化 | **仍不可开工**——唯一卡点 = R1 推导规则数据源；修复并同步后可开工（其余四动作链路 A2/A4/D1 修后已通） |
| 3.3 选卡族/箱/书册卡/关店 | **可开工**（回填终值 + D2 修后无卡点；不受 R1 影响——本阶段无 node_advance 类声明） |
| 3.4 退役 / 正本更新 | **可开工**（不变） |

### 定点复验（R1）

#### 结论行

**不收敛（一行级残留）：缺陷 1 / 建议 2。** R1 核心修复正确——修法 (a) 落地（kernel 节点日程真值表 + effective_node_ord，禁读观察镜像）数据源、局终判定、位面序、kind 映射全部与现役权威逐项对上；三处同步面（design 契约 1 / 详设 §1§2 / landing 3.2）一致，无新矛盾。残留 = 推导规则块缺「查表取 kind」一步且引用函数签名与现役不符（F1，一行补齐）；F1 修复并定点确认后即收敛，无需再走全轮对抗。

#### R1 核心核对（通过项）

- 数据源定案：§1「禁读容器 gs.node 作推导口——观察镜像不随推进变」与现役一致（advance_node_effective 只写 node_ord/node_hist_ord，cw_game_state.py:3199-3205；镜像写端在构造点之后）✓；`chain_node_type` 诚实缺位论证保留 ✓。
- 规则块逐行：`eff = effective_node_ord(gs)` = 推进落账后新序 ✓（与 backend `_on_node_advance` 同一读数，:952-965——A1 的两处 off-by-one 均消解）；局终判定 `eff > 总长 → ''` 与 backend game-over 判据逐字符同式（:959）✓；位面切换优先序与 `_enter_node_window`（:1145-1149）一致 ✓；kind→画面映射与 `_screen_for_node`/`_present_node_screen`（:1152-1157,1244-1283）逐值一致 ✓；「落地核对点」已删，局终改为确定性锁定（详设 §2 + landing 3.2 判据「eff 超总长 → next_screen=''」）✓。
- A3 消解确认：真值表迁 kernel 新模块后，声明构造（kernel）与 backend 消费同源 import 同一张表，「零序列表依赖」的错误立论已被「表在 kernel」的正确定案替代；kernel 禁 import sim 架构锁不再被触碰 ✓。
- 三处同步面一致：design.md 契约 1（kernel 真值表 + effective_node_ord + 禁读镜像句）✓；详设 §1 单值依据 ✓；landing 3.2 范围句/文件面（`kernel/cw_node_schedule.py` 新增、`sim/cw_sim_plane_schedule.py`、sim 消费点 import 改向）/完成判据 ✓。
- 消费点盘点实证：sim 侧 node_sequence_of 消费 = backend 6 处（:152-153,959,1116,1132,1163,1182,1249）；测试仓 = test_cw_sim_opening.py（含 P3UnobservedError/P1/P2 序列断言）——「backend/测试」覆盖属实。

#### 残留发现

**F1（缺陷，一行级）｜推导规则块缺「查表取 kind」步骤，且引用函数签名与现役不符**
- 位置：details/world-decl.md §2 推导规则块第 4 行
- 发现：`node_key = _node_key_for_ord(eff)` 注释称「kernel 现成公式（cw_game_state.py:3120）→ (plane, round_num, kind)」——但现役该函数签名 = `_node_key_for_ord(ordinal, kind)`，**kind 是入参非产出**（:3120-3126，docstring 自注「派生域只持单序,类型落 node.kind 需 (plane, round) 键」）；规则块通篇没有 kind 的来源语句。按文实现此行缺参报错，kind 从哪来需实现者自行推断（可从行 66 的真值表与 backend 同型做法恢复，但本规则块两轮攻击均落在其上，应一步不缺）。
- 依据：kernel/cw_game_state.py:3120-3126；backend 同型查表 = `node_sequence_of(plane)[r - 1]`（cw_sim_backend.py:1182,1249）。
- 修订建议：规则块改两步——①公式反解得 (plane, round_num)（引用 :3120 公式）；②`kind = node_sequence_of(plane)[round_num - 1]`（迁入 kernel 的真值表），随注「kind 来源 = 真值表按位查」，并修正注释中「→ kind」的产出表述。

**F2（建议）｜kernel 固定 9/位面公式与 backend 变长累加的重合前提未随注**
- 位置：details/world-decl.md §2 规则块（`_node_key_for_ord` 引用处）
- 发现/依据：kernel 公式 = 9/位面（cw_game_state.py:3124-3126），backend `_ordinal_to_node`/`_node_ordinal` = 按位面实际长度变长累加（P1=9/P2=7，cw_sim_backend.py:1111-1120,1159-1167）——两坐标系仅在 P1=9 时于 P1+P2 域内数值重合。规则把局终判定排在公式之前（eff ∈ 1..16 才进公式），当前构造下安全；建议一句话随注该重合前提，防未来位面长度修订/补采扩面时静默分叉（R1 修法 (a) 原始建议项，未随注）。

**F3（建议）｜迁移件文件面簿记三小项**
- 位置：landing.md 3.2 文件面；details/world-decl.md §2 迁移件注
- 发现/依据：① `kernel/cw_battle_calib.py:15` 模块注释指针「节点序列真值 = sim/cw_sim_plane_schedule.py」迁表后失配，该文件不在 3.2 文件面——补入或并入迁移件说明（一行注释随批改）；② 「退役或薄委托」二选一悬置——迁移后 sim 模块零消费，薄委托是留一个无人 import 的死壳，建议写死「退役」；若保留薄委托则 3.4 退役清单需补行（现行清单无此模块），否则无收尾出口；③ 消费点清单中「生成器」实际零消费（grep 实证），over-cover 无害，可删保准确。

#### 试读结论（定点，仅 3.2）

3.2 **仍差一行**——F1 修复（规则块补 kind 查表步 + 修注释）后即可开工；其余阶段结论不变。F1 修复后无需再走全轮对抗，定点确认规则块一处即可收敛。

### 定点复验第二轮（R1）

#### 时间线澄清（回应父代质询）

上一轮「零改动」核实时 R1 修复尚未写盘（当时 mtime 13:20–13:21 < 复审节落盘 13:27:57，陈述在当时为真）；随后 13:29 写盘的 R1 修复版即为本轮上一节「定点复验（R1）」的实际审读对象（其引文——kernel 真值表迁入/eff 规则/禁读镜像——均为修复后内容，F1 即针对该版指认）；13:34:39/13:34:49 的再写盘（F1/F2/F3 修复应用）晚于该节落盘（13:33:58），为本节审读对象。本节全部结论基于当前磁盘现值重读。

#### 结论行

**不收敛（残留缺陷 1，一行级）：F1b。** F1/F2/F3 三项修复本身均已正确落盘并采纳（F1 kind 查表步补齐 ✓、F2 重合前提随注在位 ✓、F3 三小项全落 ✓），但 F2 随注与规则块第 4 行的引用构成**新的内部矛盾**（F1b，下述）——随注禁用固定 9 公式，第 4 行引用的恰是固定 9 公式函数。修一行引用后即收敛，无需再走全轮对抗。

#### F1/F2/F3 修复核对（通过项）

- **F1 ✓**：规则块现分两步——`plane, round_num = _node_key_for_ord(eff)`（反解坐标）+ `kind = node_sequence_of(plane)[round_num - 1]`（迁入 kernel 的真值表取 kind，随注「backend 同型做法」）——kind 来源步已补，与 backend 现役同型（cw_sim_backend.py:1182,1249）✓。
- **F2 ✓（但引入 F1b，见下）**：迁入随注（详设 §2:78）「总长与反解一律用迁入表的变长累加/公式（与 backend 同型），禁用固定位面长度常量（固定 9 仅在 P1=9 时与变长重合，非通用前提）」——重合前提已随注，方向正确。
- **F3 ✓**：①旧模块处置写死「退役（薄委托 = 零消费死壳不留）」（详设 §2:80 + landing 3.2 文件面「退役」）✓；②`kernel/cw_battle_calib.py:15` 指针修正入 3.2 文件面（「模块注释指针随迁修正」）✓；③消费点清单改「实测 = backend/测试（生成器零消费）」✓（与 grep 实证一致）。

#### F1b（缺陷，一行级）｜规则块内部矛盾：随注禁用固定 9 公式，第 4 行引用的恰是固定 9 公式函数

- 位置：details/world-decl.md §2 推导规则块第 4 行（:68）与迁入随注（:78）
- 发现：随注明令「反解一律用迁入表的变长累加/公式（与 backend 同型），**禁用固定位面长度常量**（固定 9 仅在 P1=9 时与变长重合，非通用前提）」；但第 4 行引用 `kernel 现成公式（cw_game_state.py:3120）` = `_node_key_for_ord`，其函数体即固定 9 公式（`plane=(ordinal-1)//9+1, round_num=(ordinal-1)%9+1`，:3124-3126）——引用与禁令指向同一处，两条指令不可同时遵守。语义裁决可从随注理由导出（变长累加与 backend 同型是正解），但承重规则块内自相矛盾 = 定稿门槛违例（同块第三轮被攻，应零容忍）。
- 依据：kernel/cw_game_state.py:3120-3126（固定 9 公式本体）；cw_sim_backend.py:1111-1120/1159-1167（backend 变长累加正反解，`_ordinal_to_node`/`_node_ordinal`）；details/world-decl.md:68 与 :78。
- 修订建议：第 4 行引用改为「反解 = 仿 backend `_ordinal_to_node`（cw_sim_backend.py:1111-1120）按迁入表变长累加，实现落 kernel 迁移件（`cw_node_schedule.py` 内新增反解口）」，删除对 `_node_key_for_ord` 的引用（该固定 9 助手与本规则无关）；随注「变长累加与 backend 同型」保留即可，二者随即自洽。固定 9 与变长在 P1+P2 域内数值等价（eff ∈ 1..16），故本矛盾不产生行为分叉——是引用一致性缺陷非语义缺陷。

#### 试读结论（定点第二轮，仅 3.2）

3.2 **差 F1b 一行引用替换**——修后规则块自洽，3.2 可开工，迭代收敛（其余阶段结论不变：3.1/3.3/3.4/正本更新均可开工）。F1b 修复后无需再走全轮对抗，定点确认该行即可。

### 定点确认（F1-F3）

#### 结论行

**收敛。** 磁盘现值（world-decl.md 13:37:26 / landing.md 13:34:49 / design.md 13:29:34）重读核对：F1b 已修（规则块第 4 行引用已换）、F1/F2/F3 修复维持原判、三文档无残留矛盾与失活引用——全部阻断/缺陷/建议项闭环，试读全阶段可开工，迭代设计达定稿门槛。

#### 三处改动核对（磁盘现值）

1. **F1b（上轮残留缺陷）✅ 已修**：规则块第 4 行现为 `plane, round_num = 反解(eff)`，注释 = 「仿 backend `_ordinal_to_node`（cw_sim_backend.py:1111-1120）按迁入表变长累加，实现落 kernel 迁移件 cw_node_schedule.py」——固定 9 公式函数 `_node_key_for_ord` 的引用已删（grep 三文档零命中，仅 attack.md 历史记录），与第 78 行随注「禁用固定位面长度常量」自洽。反解语义与 backend 正反解同型（变长累加），真值单一源收敛到 kernel 迁移表。
2. **F1 ✅ 维持已修**：kind 来源步在位（`kind = node_sequence_of(plane)[round_num - 1]`，随注「backend 同型做法」，cw_sim_backend.py:1182,1249 同型）。
3. **F2 ✅ 维持已修**：迁入随注（:78）重合前提声明在位，且与新的第 4 行引用不再冲突。
4. **F3 ✅ 维持已修**：迁移件写死「退役（薄委托 = 零消费死壳不留）」（详设 :80 + landing 3.2 文件面「退役」）；`kernel/cw_battle_calib.py:15` 指针修正入 3.2 文件面；消费点清单「实测 = backend/测试（生成器零消费）」与 grep 实证一致。

#### 全局状态（历轮发现闭环台账）

第一轮 A1–A4/D1–D5/S1–S5（第二轮复审确认）→ 第二轮 R1（定点复验确认修法 (a) 落地）→ 定点复验 F1/F2/F3（本轮确认）→ F1b（本轮确认修复）——全部闭环，无未决项。

#### 试读结论（最终）

| 阶段 | 结论 |
|---|---|
| 3.1 声明基建 | 可开工 |
| 3.2 主链声明化 | **可开工**（推导规则块自洽：eff 新序 → 局终门 → 变长反解 → 查表取 kind → 位面过渡优先 → kind 映射，各步与现役权威逐项对上） |
| 3.3 选卡族/箱/书册卡/关店 | 可开工（待核六值已核定回填） |
| 3.4 退役 / 正本更新 | 可开工 |

迭代设计达定稿门槛（攻击收敛 + 试读过），可立阶段任务。

### 定点确认（F1b）

**收敛。** 磁盘现值重读（world-decl.md 13:37:26 / landing.md 13:34:49，均与「定点确认（F1-F3）」时一致）：规则块第 4 行 = `plane, round_num = 反解(eff)  # 仿 backend `_ordinal_to_node`（cw_sim_backend.py:1111-1120）按迁入表变长累加，实现落 kernel 迁移件 cw_node_schedule.py`，第 5 行 kind 查表步在位；`_node_key_for_ord` 在三设计文档零命中（仅 attack.md 历史记录）。随注与规则块自洽，无新改动引入矛盾。design.md 13:39:03 的变化 = §0 状态置「定稿」（总纲 §0/§1/§2 逐行与本报告历轮核对结论一致）——系依本报告收敛结论的生命周期动作，非新审读对象。

**最终结论：迭代设计收敛定稿，landing 五阶段全部可开工。**（随批 housekeeping：README 进度行「设计对抗」可同步为「收敛」。）

### 定点复验第三轮（R1·独立终验）

#### 时间线与节名说明

父代任务指定的节名「定点复验第二轮（R1）」已被上文同名节占用（该节实际审读对象 = F1/F2/F3 修复版并产出 F1b）。本轮为**独立定点终验**：以磁盘终态（world-decl.md 149 行 / landing.md 72 行 / design.md 53 行版〔§0:5 状态 = 定稿，契约 1:43 未变〕 / attack.md 288 行版）为准，独立重跑 R1 五项复验清单——不采信前置节结论，全部凭据自取。核验中途文件曾并发更新（初读 world-decl.md 为 F1b 修前版，中段重读已为修后版），本节全部行号 = 终态版读数。

#### 结论行

**收敛（5 项全 PASS，零残留）。** R1 修法 (a) 修复及 F1/F2/F3/F1b 全链修复在磁盘终态成立；三处同步面（design 契约 1 / 详设 §1§2 / landing 3.2）一致；推导规则与 backend 现役行为逐步对核通过；迁表纯数据零依赖、消费点面完整；kernel 公式现成。与上文「定点确认（F1-F3）」「定点确认（F1b）」两节结论交叉一致。

#### 逐项核验表

| # | 清单项 | 判定 | 依据（磁盘现值读数） |
|---|---|---|---|
| 1 | 三处文本与修法 (a) 一致，无旧表述残留 | **PASS** | 详设 §1:23「推导权威源 = kernel 节点日程真值表（…迁入 kernel 新模块 `cw_node_schedule.py`…）+ `effective_node_ord`（`report_node_advance` 推进落账写 `node_ord`）。**禁读容器 `gs.node` 作推导口**——它是观察镜像，不随推进变」；§2:62「声明构造点 = `report_node_advance` 推进落账**后**；`node_ord` 已是新节点序——序数字段随推进写，与观察镜像 `gs.node` 无关」；design.md:43 同词（「kernel 节点日程真值表…R1 修法 (a)…`gs.node` 为观察镜像不随推进变，禁作推导读口」）；landing:18「按 kernel 节点日程真值表 + `effective_node_ord` 推导，R1 迁表件随本批」+ :24「eff 超总长 → next_screen=''」。残留 grep（`NodeKey 真值`/`零序列表`/`_node_key_for_ord`/`退役或薄委托`/`cw_game_state.py:3120`）在三处同步面文档**零命中**（全部命中均在 attack.md 历史记录 = 合法） |
| 2 | 推导规则与 backend 现役逐步对核（四条） | **PASS** | ① eff 新序：kernel `report_node_advance`（cw_game_state.py:3243-3247）读 effective → `advance_node_effective(gs, effective + 1, …)` 落账（:3199-3204 仅写 `node_ord`/`node_hist_ord`）→ 落账后 `effective_node_ord(gs)` = candidate = 新序；backend `_on_node_advance` :952 同一读口（规则块 :65 同式）。② 超总长局终：规则 :66-67 与 backend :959 `if eff > sum(len(node_sequence_of(p)) for p in (1, 2)): → _game_over()`（:963）同式同判向。③ 位面切换优先：规则 :70 与 `_enter_node_window` :1145-1149 一致（先于 kind 收口 :1150）。④ kind 映射：规则 :71-75 与 `_screen_for_node` :1156-1157 逐值一致，常量字面值 = SCREEN_PREP `'货币战争-备战'`(:167)/SCREEN_SUPPLY `'货币战争-补给'`(:172)/SCREEN_ENCOUNTER `'货币战争-遭遇节点'`(:173)/SCREEN_PLANE_TRANSITION `'货币战争-位面过渡'`(:175)/SCREEN_BOSS_BRIEFING `'货币战争-BOSS简报'`(cw_game_state.py:281)。反解与查表：规则 :68（变长累加，仿 `_ordinal_to_node` cw_sim_backend.py:1111-1120，引用行号核对无误）+ :69（`kind = node_sequence_of(plane)[round_num - 1]`，与 backend :1132-1133/:1182/:1249 同型）；:68 与 :78 随注自洽（F1b 已消解）。R1 前提现役自证：`cw_op_settle_confirm.py:124-125`「report_node_advance 只推进 node_ord,镜像读值本身不随推进变」 |
| 3 | 迁表可行性：纯数据零依赖 + 消费点面完整 + 无 kernel→sim 残留 | **PASS** | `cw_sim_plane_schedule.py` 全文 73 行核读：唯一 import = `from __future__ import annotations`(:14)；构件 = NODE_KINDS(:17)/P1_NODE_SEQUENCE(:23)/P2_NODE_SEQUENCE(:29)/PLANE_NODE_TABLES(:34)/P3UnobservedError(:40)/node_sequence_of(:45)/validate_sequences(:55)/导入期自检(:73)——纯数据零依赖，迁移无技术障碍。`node_sequence_of` 消费点全清单（grep 双仓）：src = `cw_sim_backend.py`（import :152-154；使用 :959,:1116,:1132,:1163,:1182,:1249 共 6 处）+ `kernel/cw_battle_calib.py:15`（docstring 文本指针，非代码依赖）；sr-od-test = `test_cw_sim_opening.py`（import :27-31；断言 :85,:86,:88）；其余导出符号（NODE_KINDS/PLANE_NODE_TABLES/validate_sequences/P3UnobservedError）模块外零消费——整文件平移面完整，与 world-decl:80 / landing:20「消费点实测 = backend/测试」一致。kernel 内现无对该模块 import；迁移方向 kernel←sim，kernel 禁 import sim 架构锁不触碰 |
| 4 | kernel 公式现成性 | **PASS** | `node_ordinal_of`（cw_game_state.py:284-287）真实存在：`(plane-1)*9 + round_num`（ord 坐标系正解定义处）；`_node_key_for_ord`（:3120-3126）真实存在：固定 9 反解。语义匹配：规则经 F2/F1b 修订后选用变长累加反解（仿 `_ordinal_to_node`）为通用形、未直接引用固定 9 公式（防未来位面长度修订分叉）；现役 P1+P2 辖域（eff ∈ 1..16，P1=9 满宽，迁表件 `validate_sequences` :62 `expected_lengths {1:9, 2:7}` 导入期钉住）内固定 9 与变长数值等价（验算：ord 1-9 → (1, ord)；ord 10-16 → (2, ord-9)）——kernel 公式语义与推导规则辖域内一致、不矛盾 |
| 5 | 三处同步一致 + 文件面完整 | **PASS** | 权威源句：design:43 ≡ 详设 §1:23 ≡ landing:18 同词；局终判据：详设 §2:67 ≡ landing:24；文件面：新模块（landing:20「`kernel/cw_node_schedule.py`（新增…R1 修法 (a)）」）+ 旧模块处置（landing:20「退役」≡ 详设 §2:80「退役（薄委托 = 零消费死壳不留）」）+ 消费点改向（landing:20「实测 = backend/测试」≡ 详设 §2:80）+ 关联指针修正（`kernel/cw_battle_calib.py:15`——landing:20 与详设 §2:80 双处在位）——覆盖迁移件全集，无悬置、无失活引用、无矛盾 |
