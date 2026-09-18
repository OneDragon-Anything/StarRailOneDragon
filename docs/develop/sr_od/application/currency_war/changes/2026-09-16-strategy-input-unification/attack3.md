# strategy-input-unification 对抗审查报告（attack3，新一轮独立审查）

> 审查日期 2026-09-16。审查对象 = 本目录 design.md / landing.md / README.md（当前稿）。
> 审查方式 = 无前提对抗（干净上下文、无预设焦点）；判据源全部直调复核（禁转述）：
> iteration-design.md 四硬规则与 §7 三核、strategy-docs/00_framework.md、fields.md（§2.1/§2.2/§2.4/§3.3/§3.4/§3.7.1/§8.8/§9 逐节直读）、
> flow/README.md §2 全节 + flow/session.md、strategy-docs 13/22/25 篇、代码真值（strategies/impl/cw_strategy.py、flow.py、
> mandate_v1/bridge.py、kernel/cw_game_state.py、cw_events.py、cw_strategy_session.py、cw_equip_wear_plan.py、
> operations/cw_loop.py、operations/cw_screen/ 各 handler、obs/cw_observation.py、sim/cw_replay.py——as-built 断言读代码体，
> 关键点实调验证）、在飞迭代三份（execstate-dissolution / turnstate-retirement / unified-obs-reconcile 的 README/design/landing）、
> 仓库 AGENTS.md、strategy-work.md §6。行号 = 当前工作树坐标（在飞改动会使行号漂移，符号锚为准）。
>
> **发现计数：16 条 = blocker 2 / major 7 / minor 7。**无和稀泥结论；三核均有发现。

## 发现清单

### blocker（定稿门槛：阶段可验收性不成立）

**B1**｜blocker｜landing.md §3.2（文件面）× design.md §2.2-契约 e
`gs.prep_obs` 非 Field 容器字段的新增面（cw_game_state.py）落在阶段缝隙里：3.2 的**范围**明确要求「`gs.prep_obs` 非 Field 容器字段（契约 e 存储形态）」，但其**文件面**（cw_strategy_session.py / cw_prep_actions.py / cw_equip_wear_plan.py / cw_strategy.py / flow.py / bridge.py / cw_screen_prep.py / 测试）不含 `kernel/cw_game_state.py`；而 3.1 的完成判据又显式排除（「prep_obs 非 Field 豁免不入本批面」）。按申报的文件面执行 3.2 = 无法在 GameState 上落 `prep_obs` 字段，阶段不可执行。
修正方向：3.2 文件面补 `kernel/cw_game_state.py`（或把该字段新增显式划入 3.1 并同步修改 3.1 的排除句——二者取一，设计↔landing 同步改）。

**B2**｜blocker｜landing.md §3.3（文件面）× design.md §2.5（驱动器行）
商店线切换漏掉 `strategies/impl/mandate_v1/bridge.py` 的 `decide_shop_screen` 覆写：该覆写循环体内逐帧调 `self.decide_shop_action(session, config)`（HEAD :277，实读确认；工作树在飞改动未触及此调用点）。3.3 把 `decide_shop_action` 签名切为 `(gs, session, config)` 后，此调用点变参错（TypeError / 形参错位）——而 `MandateV1Strategy.decide_shop_screen` 正是 sim 回放（sim/cw_replay.py:112 实调 `strat.decide_shop_screen`）与既有序列锁的消费入口。结果：3.3 交付态下回放/序列锁路径不可运行，直接违反 landing 首节自立的「每阶段交付态生产链可运行、通用工程门可绿」与「同一契约的迁移不得跨阶段拆分」（该契约的调用点一半在 flow.py〔3.3 已列〕、一半在 bridge.py〔未列，被整体划给 3.4〕）。design §2.5 的驱动器行只写了「flow.py decide_shop_screen…内部调用点传 gs」，未覆盖 bridge 覆写体的同款义务。
修正方向：3.3 文件面补 `strategies/impl/mandate_v1/bridge.py`（限 decide_shop_screen 覆写内部调用点），design §2.5 驱动器行同步覆盖 mandate 覆写体。

### major（须修）

**M1**｜major｜design.md §2.1（全表）× flow/session.md §5.1（B4 条款）× flow/README.md §2.1
ABC 契约的破坏性变更对第三方插件契约零申报：本批删除 abstract `decide_invest(kind, options, gs, session, config)`、新增两个 abstract 入口、并改形其余全部决策入口签名。`CwStrategy` 是 plugins/currency_war_strategies 的参赛入口契约（session.md §5.1 B4 条款在册：「新增 abstract 钩子会让所有存量第三方策略实例化后调 create_session 即 TypeError」，并为 `create_state` 专设非 abstract 缺省以保兼容）。本批的变更面远大于 B4 当年处置的单钩子，设计全文无一字提及存量第三方策略的兼容判定或破坏申报（继承旧签名的实现类在新 ABC 下实例化即 TypeError）。
修正方向：§2.1 补一段兼容裁定——或申报「注册面封闭集 {mandate_v1} 期契约为内部面、允许破坏」（引用户裁定），或给出缺省适配形态；无论哪种，依据就地标注。

**M2**｜major｜design.md §2.3/§2.7 × cw_loop.py:1754-1756/1807-1866
路由清点挂点的关键语义未定义，且「必经单点」主张与代码不符：①挂点只写「外循环『画面识别 → 分支路由』处新增单一挂点」，未定插入点符号；②阶段二备战双锚分支与阶段三特殊规则臂（道具详情/消耗品浮层/阿哈装备，:1823-1855）不经 `_dispatch_identity_screen`、无建档屏名，「当前路由屏」在这些臂取什么值未定义；③§2.7「外循环路由判定是所有画面转移的必经单点，属屏映射清点在此天然完备」为假——`stop_at_prep` 早退（:1754-1756，识别屏名 ∈ PREP_DIRECT_EXIT_SCREENS 即 return，不经分支路由）与未知兜底停机都是绕行路径。实现者必须在无审查语境自行拍板①②，违反 iteration-design 硬规则 2。
修正方向：§2.3 补挂点定义（插入点符号锚 + 非身份臂的路由屏取值规则，如「映射外路由屏 = 清全部十槽」）+ 绕行路径清单及其无害性论证（替换「天然完备」表述）。

**M3**｜major｜design.md §2.8 × landing.md 首节 × unified-obs-reconcile/landing.md §3.3/§3.4 × 其 README
在飞前置语义自相矛盾：design §2.8 与 landing 首节都把前置定义为「unified-obs-reconcile **收尾**」，但同表又写「3.3 落码已收、实机候窗不阻开工」——unified-obs 的 3.3 完成判据含实机验证期（候用户游戏窗口，其 landing :40），且其 3.4「依赖：3.3（先武装后拆旧）」（:49）。「收尾」若 = 全阶段 done，则候窗期必然阻塞前置 → 与「不阻开工」矛盾；若 ≠，则 landing 的一刀切前置（所有阶段挂同一前置）与本批 3.1（kernel/cw_game_state.py + cw_loop.py，与 unified-obs 3.4 文件面零交集）事实上不需要该前置的现状失配。未定义的「收尾」= 落地开工时点与文件冲突防护都不 determinate。
修正方向：把前置按文件面拆解到阶段（如 3.1 无前置；3.2 前置 = unified-obs 3.4 完成〔cw_screen_prep.py 相交〕；3.3 前置 = turnstate 收尾 + unified-obs 3.4 完成〔cw_screen_buy_cards.py 相交〕），或显式定义「收尾」不含实机候窗并论证窗口期并行不撞文件面。

**M4**｜major｜design.md §2.8 冲突表（unified-obs 行）
unified-obs-reconcile 的「冲突文件面（全列）」错列：所列 `cw_screen_prep.py`、`obs/cw_observation.py` 中，后者属其**已完成**的 3.1 批（其 landing :6 文件面），不在剩余冲突面；而真正与本批相交的 `operations/cw_screen/cw_screen_buy_cards.py`（unified-obs 3.4 旧安灯退役批文件面，其 landing :48）**漏列**——该文件同时在本批 3.3 商店线文件面上。按此表做并行排程会在 cw_screen_buy_cards.py 上撞在飞批。「全列」申报不实。
修正方向：该行冲突面改为 {cw_screen_prep.py, cw_screen_buy_cards.py}（= 其剩余阶段 3.4/正本批文件面 ∩ 本批文件面）；obs/cw_observation.py 移出或标注「已收尾阶段」。

**M5**｜major｜design.md §2.6 终验 × landing.md §3.5-④ × 代码（删除波 1 在册墓碑）
实机 smoke 的验收锚载体「decisions 流」已退役：decisions 流写入端已随「删除波 1」物理删除（在册墓碑：cw_loop.py:966/:1893、flow.py:366、cw_screen_buy_cards.py:1044/:1227、cw_screen_prep.py:2614、cw_overlay_pick_action.py:126 等，grep 直调），继任载体 = `kernel/cw_decision_trace`（其模块头明令「禁复用 decisions.jsonl」）。design §2.6「与改前同难度局 decisions 流对照」与 landing 3.5-④「decisions 流预测锚点对照」指向一个现行不产数据的流——该判据（阻迭代收尾的唯一实机门）如写不可执行。
修正方向：锚载体改指现行决策迹载体（cw_decision_trace / journal 决策面），或改用 shop_snapshots/局档案的现行可读面，并同步 landing 3.5 判据。

**M6**｜major｜design.md §2.2-契约 e × landing.md 正本更新清单末行 × landing.md §3.2 完成判据
注释/docstring 历史锚的处置阶段三处两口径（硬规则 4 失同步，恰是其在册事故形态「design↔landing 失同步二次复发即流程级」）：design §2.2-e 说「注释历史锚…随**正本更新批**逐条处置」；landing 正本清单末行说「随**落码同步**，此处复核清零 ← 3.2/3.3/3.4」；landing 3.2 判据又说「注释历史锚随正本批，不在本判据」。随落码 vs 随正本批，账本立任务时两读。且清单的锚枚举不全：`kernel/cw_investments.py:975-977`、`kernel/cw_comps.py:1241`、`kernel/cw_equip_value.py:105` 等引用 `decide_invest`/`decide_box_card` 的代码注释不在枚举内（3.4 的 grep 判据带 `(` 不匹配注释，拦不住残留）。
修正方向：三处统一为一种归属（建议：符号改名点随落码批改指、纯叙述性历史锚随正本批，逐类写明）；正本清单锚枚举补全或把「复核清零」改为全仓 grep 判据（不带 `(` 的符号名形态）。

**M7**｜major｜design.md §2.3/§2.6 × landing.md §3.1 × cw_game_state.py:3151-3162
清点写的「已 None 是否跳过」未定义，且现机制不跳过：`GameState.leave_screen` 对 value 已是 None 的字段**不 early-return**（无条件 `_swap` → 占 write_seq + 落一行 journal；对照 `carry` 的 None 跳过先例 :3131-3132）。若实现为每路由分发对十槽无条件 leave_screen，journal 每路由 +10 行、write_seq 每路由 +10——3.1「纯增量零行为」的申报面（含其测试面）与 §2.6「journal 行量增加」的量级口径都被该未定义选择摆布；skip 与不 skip 两种实现的轨迹 digest 形态不同，直接影响 §2.6 自设的旁证对照。这是核心新机制上的实现者自择点。
修正方向：§2.3 补一句「值已 None 的槽跳过清点写（不占版本不产行，`carry` None 跳过同款先例）」或显式选择无条件写并重写 §2.6 的可观测性申报量级与 3.1 的零行为表述。

### minor（建议）

**m1**｜minor｜landing.md §3.2 范围
行号锚违反仓内定位纪律且已被在飞改动证伪：`:179`（bridge 读点）、`:163`、`:1863-1866` 用行号定位；flow/README.md 卷首明定「代码定位一律用符号锚（行号随代码增长漂移）」，design §1.1 也自我申报「符号锚，行号不书」。且 turnstate 在飞工作树已改 bridge.py（`decide_from_turn`→`decide_prep_frame`、删装配缝段），`:179` 在工作树已漂移——行号锚当轮即腐。
修正方向：landing 全部改符号锚（`bridge.py::decide_prep_screen` 缺失抛错读点 / `cw_equip_wear_plan.py::_build_equip_wear_plan` 事实源前置段 / `cw_screen_prep.py::_act_execute` OpenShop 腿）。

**m2**｜minor｜design.md §2.5（sim/回放行）
引用锚标签错位：「（prep 面 sim 不可达，flow/README §2.3 归因域限定）」——「归因域限定」是 flow/README **§2.4** 的小节标题；§2.3 是「sim 消费面注记」（内容同族但标题不同）。值对标签错类。
修正方向：改指 §2.4（或「§2.3 注记 + §2.4 归因域限定」双锚）。

**m3**｜minor｜design.md §2.7（载荷入容器条）
「与商店容器化（W6 波4）、容器化段 2 的既定方向同轨」用了会话期代号（W6 波4/段 2）且无持久索引——按 AGENTS §8 引用持久索引纪律的同判据（该条管注释，设计文档依据标注同判据归 iteration-design 硬规则 1 的「依据 = 来源文档+节」），无会话历史的读者无法解析该依据。
修正方向：改指持久锚（正本相应节，如 flow/README §2.2 商店容器化相关句或对应 ADR 号）。

**m4**｜minor｜README.md 承接出处/关联在飞节
README 的「承接出处」「关联在飞迭代」两节与 design §0/§2.8 内容重复（同一裁定的第二抄本）——iteration-design §4「README 只做两件事：串文档、记进度」，双抄本必漂移（design §2.8 的在飞状态值更新时 README 同句极易漏改）。
修正方向：README 两节收敛为一行指针（「承接出处与在飞依赖 = design.md §0/§2.8」）。

**m5**｜minor｜design.md §2.5（pick 族行）× cw_screen_encounter.py:304/336/439/466
pick 族 handler 的**双路径结构**（旧 handle 路径 + 五段 lifecycle 路径，两端口装配分流）未申报：encounter 单文件就有 4 个 decide 调用点（两路径各首调/重决策一对），invest/bookcard 等同样存在两路径观察半。§2.5 按「10 文件」一行带过、landing 3.4 同——「OCR 产物写本屏槽」的接线在两条路径的观察半各有一份，漏接 lifecycle 半不炸生产（端口缺省关）但测试 harness 路径即断，只能靠 3.4 的全仓 grep 判据事后兜底。
修正方向：§2.5 或 landing 3.4 补一句「每 handler 的写槽-决策改形须同时覆盖旧 handle 与 lifecycle 两路径（调用点清单以 grep 为准）」，测试判据补「两路径各一条剧本」。

**m6**｜minor｜design.md §2.1-4 / §2.2-契约 c
`encounter_refreshed_in_visit` 的「访问起写 False」写点未定（构造器 / handle 入口 / lifecycle 入口三选，双路径下不同选择语义不同——按 round 重入写会把同访问已置 True 复位）；「刷新发射已置 True 但重读失败未重决策」的窗口语义（True 残留至本访问终、下访问由起点写复位）未申报。结论上各选法行为等价，但这是留给实现者的语义选择。
修正方向：写点定死一处（建议 = op 构造器，per-dispatch 生命周期与「访问」天然对齐，cw_loop 每次分派新建 op 实例）并在字段注释申报窗语义。

**m7**｜minor｜landing.md 正本更新清单（25_event_overlays 行）× fields.md §3.4.5 × strategy-docs/25_event_overlays.md 卷首
该行 include 枚举自相矛盾/不全：①「有 pick 接口的画面」枚举漏 **补给、遭遇节点**（两屏有 decide_supply/decide_encounter 契约，且都在 25 篇画面族清单内）；②「装备三选一（武装箱）」指称歧义——fields.md §3.4.5 的「装备三选一」与武装箱选择面「同屏性待采证」、25 篇的分节名是「武装箱弹窗」（= decide_box_card 面），而排除句的「选择装备（cw_equip_pick）」在 fields.md 语境里恰是「装备三选一」的同位词——实现者按名索节可改错节。
修正方向：枚举补全为十入口对应画面；「装备三选一（武装箱）」改为 25 篇实际节名「武装箱弹窗（decide_box_card 面）」。

### 已攻未破的面（零发现申报）

以下各面经直调复核**未发现**问题（列出面清单以自证攻击密度，非总体评价）：

- **现状症状断言逐条对码**：三形状并存（cw_strategy.py:117-187 实读）；`decide_supply` 调用方容器派生旗标（cw_screen_supply_node.py:210-211/:230-232，派生式 = `int(value or 0) > 0`）；encounter 首调缺省/重决策传 True/闸本体读累计计数（cw_screen_encounter.py:304/:336/:322-331/:439/:466/:452-455，双路径均在）；invest 两调用点传 `'strategy'/'env'` + 容器单例（cw_screen_invest_strategy.py:404 / cw_screen_invest_env.py:303）；flow.py:471「空 stub」docstring 确已过期（勘误断言属实）；`gs.shop` 活写端在产、live 清点恰两处（cw_game_state.py:2033 + obs/cw_observation.py:2617-2619）。
- **等价性主张逐点验**：encounter per-visit 位与改前首调/重决策两态逐字节等价（kernel cw_events.decide_event:670 `not refresh_used` 分叉实证「两枝 idx 可分叉」）；supply 入口读累计计数与调用方派生式逐字节可同（无 match 路径不调 decide，实读确认）；刷新重决策链「无条件重读」在 encounter（同调用内）与 supply（round_retry 同 op 执行内）都不经路由点，槽保活论证成立；prep_obs 非 Field 化不入快照流水（full_state_snapshot 仅收 Field 实例，:3061 实读）、4 写点/3 读点全集与申报一致（grep 全量）；`game_state_of` 恒返容器（不返 None），wear_plan 换源无新崩溃面；`PrepObservation` 含 set/Point/BenchChar 属实（cw_prep_actions.py:68-82）；invest 槽存 OCR 原文与 kernel eval-lcs 消费一致（cw_events.decide_event 实读）。
- **§2.3 属屏映射十行逐行对分发臂**：十键全部真实存在（cw_loop.py:1364-1461/:1598），「武装箱弹窗→CwScreenArmoryBox 无 decide」注属实；反直觉三行（列车同行/骇入策划/星徽秘典弹窗）属实。
- **在飞依赖声明对账**：execstate「6/6 done + 正本清零 ee1f4e337」「#4-#6 已落地」「#12-#14 域 bump 先例」「#20 非 Field 先例」「注释历史锚纪律引文」全部与 execstate design/README 逐条相符；turnstate「README 计 0/3」属实（工作树含其在飞未提交改动——本报告 B2/M2 的行号漂移即源于此）；§2.5「entry.py 不在本批文件面（grep 无 decide_* 契约调用点）」属实。
- **landing 七件套**：3.1-3.5 + 末阶段每阶段七件齐；通用工程门有单一定义并被各阶段引用。
- **设计内一致处**：契约成员计数 12→13/13→14 与 ABC 实读相符；EncounterPayload/SupplyPayload 现形状与「形状升级」表述相符（cw_game_state.py:610-620）；`node_screen_refresh` 为 schema 分组名非访问路径属实（:136-167/:2756）；正本清单各条目（flow/README §2.2/§2.5、session.md、fields.md §3.4/§3.7.1、13/22/23 篇）目标节均真实存在。
