# T-161 sim 推演内核形态设计件·对抗审报告

- 审计对象：本目录 `design.md`（总纲，单文档方案）+ `README.md`。
- 三核并重：无前提攻击 / 规范遵循 / 治本核验。
- 判据源全部直调原文亲读，未采信任何转述：
  - `.debug/progress/2026-09-11-cw-clear-run/reports/T-145-r1.md`（§5-1 三点冲突证据与三候选）
  - `.debug/progress/2026-09-11-cw-clear-run/reviews/T-145-r1.md`（验收结论与范围增补三项）
  - `kernel/cw_vocab.py` 全文 1258 行（CwWorkFrame 35 字段清点 / simulate :906-1121 / mutate_bench_deployed :1124-1240 / 单一源申报）
  - `kernel/cw_game_state.py` 模块头与全部被引行段（:1-62 / :840-1010 / :1179-1257 / :1300-1310 / :1452-1678 / :2189-2231 / :2758-3007 / :3068-3273）
  - `kernel/cw_exec_state.py` :400-439（BenchChar 缺省值）、`kernel/cw_intention.py` :2360-2414
  - `sim/engine_p1.py`（import 面 :65-78、容器触点 :600-729/:1490-1844）、`sim/engine_p2.py` :31/:102-104、`sim/cw_replay.py` 全文、`sim/runner.py` :1070-1092
  - `operations/cw_op/cw_shop_action_ops.py`（mutate 消费点）、`decision_assembly.py` 全文
  - `docs/develop/harness/iteration-design.md` 全文（写作硬规则与攻击面）
  - `docs/develop/sr_od/application/currency_war/game_state/fields.md` :11-25、`r5-migration-plan.md` :1-40/:143-162
- 已裁边界遵守：策略域前瞻搜索删除（T-163）、sim 定位 = 环境模拟器跑真实策略、方案 B 作废——三条均未作为攻击点，且作为前提接受。

## 一、结论

**主体未破：设计的事实底座、决定性理由、勘误申报经逐点亲核全部成立；发现 0 条阻断级、3 条中级、6 条低级问题**（1 条归因错位、1 条无界过渡声明、1 条规范生命周期裁剪、其余为精度/完备性）。收敛条件见 §四，无需推翻任何裁决。

---

## 二、问题清单

严重级定义：高 = 推翻裁决或阻断定稿；中 = 结论不变但必须修正后才能定稿/落地；低 = 精度与完备性瑕疵，随正名批顺带修。

### F1【中】design.md §2.2 理由 1（决定性理由）——kernel 侧消费归因错位

- **原文**：「kernel 侧消费（ops 运行时跟踪、`cw_game_state.apply_shop_action_logic` 经 cw_game_state.py:1676 消费 mutate）」。
- **亲核事实**：`apply_shop_action_logic`（cw_game_state.py:1452-1620）体内 **零 mutate 消费**——全模块 `mutate` 命中仅 :1633/:1657/:1671/:1673/:1676/:1677，简单腿走自己的逐域 `write_logic` 直写（:1509-1511 起，BenchChar+bench_place 局部落位）。真实消费链是两条：
  1. `apply_shop_merge_leg`（:1622-1668，M1 锁的升星整表腿）→ `mutate_bench_deployed_local`（:1671-1677，即被引的 :1676）→ `cw_vocab.mutate_bench_deployed`；
  2. `operations/cw_op/cw_shop_action_ops.py:537` 与 `:618`（ops 运行时跟踪，直接 import mutate）。
- **发作场景**：落地批或后续依赖分析按「apply_shop_action_logic 消费 mutate」去找消费点会扑空，且漏掉真消费方 `apply_shop_merge_leg`——它恰是与 simulate 输出等价性对拍（锁 M1）的容器侧半边，是「动作语义单一源被 kernel 侧钉死」的真正证人之一。归因错位会削弱决定性理由在后续评审中的可复核性。
- **裁定影响**：无。kernel 侧生产消费确实存在（上述两条链实证），决定性论证方向成立（详见 §三-1）。
- **修法**：该句改指 `apply_shop_merge_leg`（:1657）+ `cw_shop_action_ops`（:537/:618），随正名批文档锚一并改。

### F2【中】design.md §2.6-2——「过渡性瑕疵…短暂」无界；正名后 CwSimFrame 在实机链上是假名

- **事实**：正名语义 = 类本体唯一存续职责 = 推演内核（§2.1/§2.6-2），但 last_state 写点（cw_screen_prep.py:535/:756，另有 cw_op_buy_cards.py:935，见 F6）与 OCR 填帧链在退役波落地前继续消费该类。正名后这些实机链消费点将持有 `CwSimFrame` 注解——旧名 `CwWorkFrame` 是中性的「工作帧」，新名是单一职责声明「sim 模拟环境的局面帧」（§2.1），过渡期内名与用相悖，混用身份只是换了名字续期。
- **「短暂」无依据**：§1.3 明认「last_state 链的删除排期……本设计不排期只声明终态」；顺序约束只钉了 T-146（装配源），last_state 链退役只有波指针（cw_intention.py:2377-2378「随各自退役波消亡，本支退役挂波 5 last_state 链删除」），无排期锚。该波若拖延，假名期以月计，「短暂」是断言不是事实。
- **发作场景**：①读者按名索骥，在实机链看到 CwSimFrame 误判 sim 泄漏进实机（或反向在 sim 批改实机链行为）；②后续有人按「CwSimFrame = sim 专用」立新哨兵/新约束（如 sim 包外禁引），会误伤仍在飞的实机过渡链。
- **修法**（二选一，落地批可承载）：①措辞改「过渡期上限 = last_state 链退役波，指针 cw_intention.py:2377-2378」，删「短暂」；②正名批重写模块头时显式声明过渡期双职责与退役指针（设计已含模块头重写，边际成本一行）。

### F3【中】规范遵循——landing.md 缺席对抗审，规范生命周期被裁剪（编排者层级裁量，记录在案）

- **规范出处**：`docs/develop/harness/iteration-design.md` §6 生命周期：「对抗审中（②设计对抗批：总纲/详设/**landing.md 一并攻**——依据/试读/**阶段可验收性**/接口契约）」；核一总纲攻击面含「landing.md 阶段与设计是否一致」。
- **事实**：README「落地:未立（本设计批不产 landing.md，候对抗审收敛后由编排者另立）」+ design §0 同口径。阶段可验收性素材（§2.6 顺序约束、§2.7 行为零漂移门/哨兵锁/圈定测试集）未经对抗即写进设计正文。
- **定性**：该 sequencing 出自 T-161 任务书本身，属编排者对规范的裁量，非设计作者违令；但对抗审有义务记录缺口。本报告以 F9 的试读预审部分补偿（对 §2.6/§2.7 做了可验收性攻击）。
- **发作场景**：后续另立 landing 时若与 §2.6/§2.7 冲突（如阶段划分把改名扫与文档锚拆批），无对抗记录可援引，需返工重审。

### F4【低】design.md §2.3.3 行 18——deployed 判 A 与自报损耗矛盾；分类计数订正

- **判定口径自洽性**：口径定义 A =「同域无损」，行 18 却自报两项损耗（faction '?' 原值不保——注册表派生 :1238-1239；pref≠row 短暂不一致被归一——front_count_of :3098-3103 口径注），仍判「A（近无损）」。按口径应判 B（faction 原值不保与 bench 行同性质），或把 A 定义改「同域近无损（损耗逐项申报）」。非实质缺陷（损耗已就地申报，无信息隐藏），但落地批照表立锁遇到归类争议时无口径可依。
- **计数订正（给编排者）**：表内实际 **A=18（含 deployed）/B=3/C=8/D=4/E=2 = 35**。任务书预注「A 17/B 3/C 10/D 4/E 2」合计 36，系预注误计——设计表本身自洽，消费本报告时以 18/3/8/4/2 为准。
- **发作场景**：低。对账表被引用为哨兵/锁的判定依据时，行 18 的类标签成为争议点。

### F5【低】design.md §2.3.2-2 双禁令与 §2.3.4 既有实践的形式冲突（缺 carve-out）

- **事实**：「容器 → 内核帧：禁止」为绝对表述，但现树存在两类合法的容器→引擎侧信息流，仅由 §2.3.4 的单向环（帧→feed→容器→读口→策略→动作→帧）正当化，§2.3.2-2 未交叉引用：
  1. 引擎决策谓词喂后读容器——engine_p1.py:716-723（assemble_swap_plan_inputs）、:1513-1517（readiness_launch_decision）、:1677-1688（bench_is_full 改经容器派生，「不再直接数 st.bench」）、:1814-1834（k_empty_window_fallback/shop_unbought_reasons）；
  2. 双 ShopCard 对齐块（engine_p1.py:2002-2047，容器牌对象与帧牌按 (name,star) 对齐，§2.3.4 明文「零改动」）。
- **发作场景**：落地批照 §2.3.2 双禁令写同步契约守卫或静态哨兵，会把上述合法读判为违例；或后续读者以禁令字面质疑现树代码。
- **修法**：§2.3.2-2 补一句「策略侧与引擎决策谓词经容器读口读为合法（见 §2.3.4）；禁的是把容器值回写进帧真值」。语义审计结论：现树**无任何**容器值回写帧字段的通道（engine_p2 build_state 帧源 = P2ReplayEntry 档案 :102-104；cw_replay 在容器上直接决策、零帧重建；runner.synthesize_snapshot 方向 = 帧→Snapshot）——禁令实质成立，缺的只是豁免注。

### F6【低】design.md §2.2 理由 3/§2.6——last_state 写点引用集不全

- **事实**：§2.2 理由 3 引 cw_screen_prep.py:535/:756 两写点；全仓 grep 尚有 **cw_op_buy_cards.py:935**（`match.session.last_state = state`）。§2.6-2 退役申报面按「last_state 写点」语义覆盖它，cw_intention 申报面（:2377-2378）按槽不按点，故结论不受影响；但「文档面修正锚（随正名批）」若按设计引用集圈文件面会漏该文件的注解面。
- **发作场景**：正名批文档扫按清单圈文件漏 :935 所在 docstring/注解的 `CwWorkFrame` 字样（机械改名扫是全仓 grep，代码面风险低）。

### F7【低】design.md §2.3.3 行 4 备注——「None 帧不写 node」只对无现值帧成立

- **事实**：synthesize_from_game_state :2798-2805：node_type=None 且容器已有 prev node 时，**写** kind_inherited 帧（plane/round 取帧值，evidence='kind_inherited'）。行 4 备注「None 帧不写 node，禁假值占位」漏了继承分支，与所引 :2789-2806 的实际行为不完全对齐。不改变 A 判定（该分支 round_num/plane 反而有写），属备注精度。

### F8【低】落地批实现者待决点两处（试读结论，见 §三-2 详述）

- §2.6-1「扫后全仓 CwWorkFrame 零命中入哨兵锁」的**哨兵扫描域未定义**（src+测试仓？含 docs？）——正本文档（如 r5-migration-plan.md:3）按 §2.6 文档锚归正本更新阶段才扫，若哨兵含 docs 会过早红。
- §2.7「改前改后逐位一致」的**取树口径未写**——T-145 验收已实证锚存在「共享树绿/干净树红」世界依赖（锚 3a1f38b4 在交付树已破，重锚归 T-83）；落地批执行 digest 对照时应显式选 fresh worktree 口径或显式挂 T-83 增补门为依赖。

### F9【低】黑话密度（AGENTS.md 文档规范「直白表述、项目术语首现给定义」）

- 「腾名化石条款」「账债关闭」「双禁令」等自造压缩词，首现处多数有语境定义（§2.6-3 对「退役语义=正名收编」给了定义），但「腾名/账债」族依赖 r5-migration-plan 先验知识。changes/ 迭代件读者有上下文，判低危；**正本化时**（landing 末阶段）须改写为直白表述，禁原样搬进正本。

---

## 三、重点攻击面裁决（编排者预注五面逐面回执）

### ① 「kernel 留守不迁 sim 域」的决定性理由——**成立，归因句需修（F1）**

- **kernel 侧消费是什么（实证）**：`cw_shop_action_ops.py:537/:618`（实机 ops 运行时跟踪 tracked 账）+ `cw_game_state.py apply_shop_merge_leg:1657`（容器升星腿，M1 锁对拍半边，经 :1676 惰性转发）。非 design 所写的 apply_shop_action_logic。
- **反向依赖论证是否成立（成立）**：全仓 grep 证实 kernel 包**零** `currency_war.sim` import；operations/strategies 桶亦零 sim import；sim→kernel 单向（engine_p1.py:65-78 亲读与 design 引用一致）。移居则上述两条生产链须反向 import sim 包（生产运行时依赖模拟器包，方向倒置），或把 simulate/mutate 拆居两包——二者共居的转移规则是**分支结构级**配对（mutate 的 BuyCard/DeployMove/SwapDeploy 分支逐支复刻 simulate 同支，docstring :1134「转移规则与 simulate 一致(单一源，避双源漂移)」），拆居即制造 M1 锁所守的双源漂移面。部分迁移替代案（只迁 simulate+帧、留 mutate+helpers 在 kernel）同样落入「拆双源」腿：helper 可单源共享，但分支结构配对被拆到包边界，等价性只剩测试锁远距把守。理由 1 的「或拆双源」措辞已隐式覆盖该案，论证闭合。
- 理由 2/3/4 均经亲核属实（import 面 :65-78；cw_screen_prep 写点；cw_merge_simulate._apply_full_bench_merge_buy :467「simulate 与 mutate_bench_deployed 共用」）。

### ② 「正名收编非删除」是否真治本——**对裁定范围治本；混用身份的终局清理是显式声明的战术递延（F2）**

- 归层正确：三点冲突为表示层刻意分界（cw_game_state.py:31-34/:430 设计明文亲读属实），原「sim 切容器本体」判据的隐含假设（同物异名可无损替换）确实不成立。
- 修的是根：把隐式形态升为正式契约（对账表/账本宿主/回滚原语/退役语义成文），正是「表示层根」的治法；且本件是 T-145 停手的架构级升件，非第三件症状补丁（跨件半问过）。
- 残留：类本体的第二主人（实机 last_state 链）退役**有声明有指针无排期**（cw_intention.py:2377-2378/§1.3），正名后新名在过渡期语义为假（F2）。「腾名化石条款作废」经 r5-migration-plan.md:2-4 正名兑现注亲核成立，确为历史规划残留。

### ③ 35 字段五类判定抽查——**逐类全对，两处备注精度问题（F4/F5/F7）**

- A 类 17 个纯行（gold…refresh_probs）逐行对照喂入口写面（:2758-2905 亲读）全数证实；**B 类 3 行**（bench 丢 position_pref :1205-1212 重建无此参、shop 丢 x/merge_preview :851-864、action_log 无容器域）证实；**C 类 8 行**容器确无域（字段面 :1900-1999 grep 证实 board_next_tier/五个可读位/enemy_difficulty_live/front_max 均不存在；front_max 常量镜像 DEPLOYED_FRONT_CAPACITY=4 同值）；**D 类 4 行**喂入口确实不写、桥面补写三域 :3194/:3197/:3200 亲读证实、enemy_difficulty 桥也不写（设计如实申报）；**E 类 2 行**容器无域、退役挂账属实。容器独有域反向清单与字段面吻合（refresh_counters=3 个、node_screen_refresh=4 个、chosen_×10、receipts 等逐一核对）。

### ④ 单向同步契约完备性——**实质完备，现树无漏掉的反向写通道；字面需补豁免注（F5）**

- 反向读场景逐一排查：引擎容器触点全部为「喂后读」（生产同款谓词），无容器值回写帧字段；cw_replay 在容器上直接决策、零帧重建（旧帧重建面已退役，模块 docstring :9-12 申报）；engine_p2 帧源 = P2ReplayEntry 档案；runner.synthesize_snapshot 方向 = 帧→策略 Snapshot；decision_assembly.snapshot_from_obs = 容器→策略 Snapshot（「策略域 = 容器读」侧，非帧域）。禁令实质成立；缺的是把 §2.3.4 的合法读在 §2.3.2-2 显式豁免（防哨兵误伤，见 F5）。

### ⑤ 附带勘误（is_item_slot）——**design.md 勘误成立，T-145 验收 §二-3 不实**

四点链逐点亲读闭合：

1. 写侧：is_item_slot=True → `BenchSlot(kind='supply_box')`（synthesize :2861-2864；同口径 bench_view_of_slots :1323-1328）；
2. 序列化：`_json_safe` = dataclasses.asdict（:1300-1310），frozen dataclass 的 kind 原值入 dict；
3. 恢复：restore `_bench_view`（:2961-2971）按 `sd.get('kind')` 重建 BenchSlot，kind 不丢；
4. 还原：bench_slots_to_legacy（:1194-1199）kind='supply_box' → `BenchChar(is_item_slot=True)`。

真正丢的是 bench 侧 `position_pref`（重建走缺省 'back'，cw_exec_state.py:419）与 `faction` 原值（:1204-1209 注册表派生，'?' 与表外形态丢失）。T-145 验收 §二-3「丢 BenchChar 的 position_pref/faction/is_item_slot 等」中 is_item_slot 一项错误；§七建议 2③ 清单同源带入。T-145 报告本体（§5-1）未提 is_item_slot，无涉。

### 附：试读（实现者无需再设计）——**总体过，两条待决点归 F8**

改名扫/哨兵/文档锚/测试集（T-145 V3 十七文件集）/行为零漂移门均成文到可开工深度；哨兵扫描域与 digest 取树口径两处需在 landing 立阶段时补明（F8）。

---

## 四、攻过未破角度清单

| # | 攻击角度 | 结果 |
|---|---|---|
| 1 | 「现树 simulate 唯一活调用 = sim 引擎」（§1.3/§2.3.4） | src 全仓 grep：唯一 import = engine_p1.py:78，engine_p2 经 simulate_p1；策略/ops/flow 零调用。**未破** |
| 2 | kernel 从不 import sim；移居翻转波及全仓（§2.2 理由 2） | kernel 包与 operations/strategies 零 sim import 实证。**未破** |
| 3 | 三点冲突证据本身（x/position_pref/回滚） | :966 按 x 下架、:419+:1179-1213 缺省不重建、:922/:949 copy-on-write vs :2189/:2937 快照丢字段，逐点复验属实。**未破** |
| 4 | D 类「桥补写、喂入口不写」 | :3194/:3197/:3200 亲读；feed 写面 :2758-2905 无此四域。**未破** |
| 5 | feed 单一源「禁引擎侧散落第二写点」 | engine_p1 全部容器写经 feed_sim_truth（:615/:716/:1513/:1677/:1814/:2645/:2889），无直调 synthesize 散点。**未破** |
| 6 | receipts「唯一写点」断言（§2.4） | grep bs.receipts 写点仅 :1006（note_action_receipt）。**未破** |
| 7 | cw_replay 构成隐藏容器→帧通道 | 亲读全文：journal 快照 restore 进容器后策略直接容器决策，零帧重建。**未破** |
| 8 | engine_p2.build_state 帧源污染 | P2ReplayEntry 档案构造（:102-104），非容器。**未破** |
| 9 | 反向攻击勘误⑤（试图证明 is_item_slot 确丢） | 四点链全闭合，勘误站得住（§三-⑤）。**未破** |
| 10 | 正名与 W8 腾名债冲突；「化石条款」可能并非化石 | r5-migration-plan.md:2-4 正名兑现注 + fields.md:13 亲核，容器正名已兑现，化石定性成立。**未破** |
| 11 | 行 35 字段清点是否有漏 | 逐字段清点 = 恰 35（cw_vocab.py:107-206）。**未破** |
| 12 | 引用行号抽查（对账表 20+ 处代码指针） | 抽查全部命中（:851-864/:846/:867-901/:943-1008/:1179-1213/:1194-1199/:1241/:1300-1310/:1676/:2189-2231/:2758-2934/:2861-2864/:2896-2901/:2961-2971/:3081-3085/:3098-3103/:3113-3125/:3194/:3200/:3208-3271/cw_vocab :104-256/:123/:131/:142/:197-198/:200-205/:222-223/:631-633/:906-1121/:1124-1240/engine_p1 :65-78/cw_screen_prep :535/:756/cw_intention :2377-2403/cw_exec_state :419/fields.md:13/r5 :2-3/:150-152）。唯二精度偏差 = F1（函数归因）与 F5/F7（备注不全），无凭空引用。**未破** |

## 五、收敛条件（给编排者）

定稿前必须修：F1（§2.2 归因句改指 apply_shop_merge_leg + cw_shop_action_ops）、F2（删「短暂」或加退役指针声明）、F4（行 18 类标签或 A 口径定义二选一）。
建议随定稿顺带：F5（§2.3.2-2 补豁免注）、F7（行 4 备注补继承分支）、F6（文档锚清单补 cw_op_buy_cards.py:935）。
移交 landing 立阶段时补明：F8（哨兵扫描域 = src+测试仓；digest 对照取树口径或显式挂 T-83 增补门）。
F3/F9 记档：F3 由编排者对 landing 缺席对抗审的 sequencing 自行裁量确认；F9 在正本更新阶段改写为直白表述。
