# 链观察落地 迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-16 会话，统一观察对账迭代确认流程揪出两个违例写端后的架构归位令）——节点类型链按既有正本设计（[chain-observation.md](../../../game_state/chain-observation.md)，下称「链正本」）落地进 game state：观察写入容器、派生管线自查类型、删两个流程层违例写端。承接出处：件 B 预留（`chain_node_type` docstring「查链接线归件 B 实施批」）、fields.md §3.1.5/§3.2.2、统一观察对账迭代（changes/2026-09-16-unified-obs-reconcile/）确认批记录。
- 状态：草案
- 文档清单：无详设（单文档方案，本篇即完整设计；链语义正本 = 链正本，本文只做「正本语义 → 当前代码面」的落地映射，不复制正本内容）。

## 1. 问题与动机
- 现状症状（依据 = 统一观察对账迭代归因报告 attribution.md + 2026-09-16 用户确认批）：
  1. 节点类型顺序存在**双源**：session 权威表（flow 侧 `NodeLedger.seq_by_plane`，三个写点在役：位面详情采集①/投资环境重读②/备战帧探针按位合并③——③住 `_probe_node_type`，仅关店后两 shop 流程点触发，非每备战帧）活着；容器 `node_path` 字段（kernel 侧，schema 已注册）**零写端恒空**——kernel 派生管线按「game state 自己算」的方向够不着 session，类型真空。
  2. 两个流程层违例写端在顶班：商店回填（`cw_screen_buy_cards.py:951-973`，进店查 session 表写容器 node）与投资环境写点②（`cw_screen_invest_env.py:444-484` 确认后自截屏自读节点行，违反 ADR-0517 唯一读屏点）。
- 根因归层：**流程层 + 迁移烂尾**。链语义正本早已定稿（链正本 §1-§7：载体/双源/diff/查询口），容器字段与查询口也已就位，唯独写端与接线零实现——不是设计缺失，是实施批未做。
- 解决到哪：链正本 §3 双源写端全部落地（基线链含 P2/P3 首帧回填/现行链）、diff 证据接线（§4）、类型派生消费接线（§6「商店查现行链」）、删两个违例写端。
- 明确不解决（防外溢）：
  - **session 台账退役**：删回填后台账仍有活生产消费点（依据 = 对抗 F2：`read_game_state` 节点类型查表优先主值 cw_observation.py:2245-2246、装备 O1 门 cw_equip_wear_plan.py:258-275 经 mandate 生产可达、三票校验）——本迭代全部保留在册申报；退役另批承接范围 = 上述消费点重接 + 同族载体盘点（对抗 F12：`plane_node_table`/`plane_lengths_seen`（cw_screen_prep.py:240-260）与 `last_node_type`（cw_strategy_session.py:140）一并归该批）。
  - `chain_baseline`/`chain_rewritten` 两接口（链正本 §6 明文不预纳）。
  - sim 域链合成（见 §2.3-5 取舍：正本 §7 规定合成口写链，本迭代裁剪为不写并排正本修订）。
  - 暗格判态阈值多样本校准（cw_node_reader 既有采证义务，独立）；类型仲裁序变化（判定规则本体归场景一判定方案，本迭代只接查询不改编仲裁序）。
  - **P2/P3 基线观察窗收窄如实申报**：基线回退序末位 `prep_row_first`（本迭代落地）之前，P2/P3 链不可知；落地后 P2/P3 基线 = 位面内首个 clean 链写（晚于 P1 的过渡屏全行），diff 观察窗较 P1 收窄——正本 §3 已申报，本迭代按回退序末位实施（见 §2.1-3）。

## 2. 方案（单文档方案，此处即完整设计）

### 2.1 系统级变化

1. **载体升级**（kernel/cw_game_state.py）：新增 `TokenCell`/`NodeChain` 数据类（链正本 §2：`TokenCell{token, channel, hu_dist}`，channel ∈ {hu,label,sift,none,dim}；`NodeChain{plane, seq}`——值自带位面防切换窗读陈旧链）。`node_path` 字段值形 `Field[list[str]]` → `Field[NodeChain | None]`（现行链=最新权威读数**整帧覆盖**，跨度=本位面，链正本 §2/§3）；新增 `node_path_baseline: Field[NodeChain | None]`（基线链=位面入口写定，本位面内不被链读覆盖，位面切换整值覆盖，链正本 §2/§3）。node schema 域升版（'node' 域值形变化，按 fields.md §3.7 机制）。**跨版本判读边界申报**：journal 旧档 `node_path` 行 = list[str]、新行 = NodeChain——旧档只读保留，读面按域版本分流（现判读 CLI 不消费 node_path 域，如实申报暂无消费方；若未来消费按域版本分派）。
2. **备战帧现行链写端（prep_row）——挂点 = 备战入口 heavy 观察的节点行读点**：
   - 挂点裁决（对抗 F1/F6）：现役入口 heavy 的行读（`cw_observe_full.py:135`）读完即弃槽——本迭代把该读点升格为链写端（slots 不再弃，构造 `NodeChain` 经 `bs.observe(node_path, ...)` 写入，evidence='prep_row'，统一写入口自动产 journal 写入行）。**不挂关店探针**（`_probe_node_type` cw_screen_prep.py:3113）：探针仅关店后两 shop 流程点触发（:2781/:3043），受开店门控且五段测试路径不触达（对抗 F6）；入口 heavy 两路径共用（旧 run():1964/五段:2159）且每备战帧必经——链覆盖每帧、首店前即已在位。关店探针本体**维持现状不动**（store_plane_table/台账写点③/左移锚/图标采集各司其职）。
   - **逐格映射**（对抗 F1-2：current 直读恒 None 是探针 Hu 匹配器的现实，入口写端按以下取值链）：past → `channel='dim'`/token=None（已通过段不由本帧负责，链正本 §3）；current → token=**左移推断值**（复用现役 anchor 机制语义：上一帧该位为 upcoming 的 Hu 读数即本轮类型，`channel='hu'`；anchor 不可用（首帧）→ OCR 标签兜底（`channel='label'`，fields.md §3.2.1「帧标签仅 battle/boss 稳定」采信约束随迁））；upcoming → `channel='hu'`/token=Hu 匹配，`hu_dist>HU_DIST_UNRECOGNIZED` → `channel='none'`/token=None；boss 末槽 → `channel='sift'`。左移推断的状态载体 = 现役 `session.upcoming_types`/`nodeseq_probe_anchor` 语义平移到写端（防同帧重复推进的锚定比较随迁）。
   - **写门**：轮位对齐门（current 槽 idx == round_num-1，错位帧拒写，cw_screen_prep.py:3195-3205 门语义随迁）。**变异窗不对链写设门**（对抗 F7）：链 = 最新权威读数整帧覆盖，变异中帧写入被下一帧自愈，误报由 diff 两帧门拦截（§2.1-4）；变异窗保留原辖域 = 三票校验与 session 写点③豁免（现状不动）。
   - **基线回填（对抗 F3）**：位面内**首个 clean 链写**（本位面基线为空时）同时写 `node_path_baseline`（evidence='prep_row_first'，链正本 §3 回退序末位）——P2/P3 基线由此落地，diff 观察窗收窄但不再恒关。
   - **变异窗关闭点迁移**（对抗 F7）：轮位对齐门过 ∧ 行读成功 → 关 `env_grace_until`（与链写是否执行脱钩；写点②删除后「确认后短窗重读」职责由本读承接）。三票豁免窗较现状提前收口 = 行为改善，申报。
3. **过渡屏观察段（基线链 + 离场快照）**（operations/cw_screen/cw_screen_plane_transition.py）：过渡屏（每位面自动出现一次）底部为**刚离开位面**的完整节点行（全亮可读，fixture `plane_1to2.webp` 实证）。写两笔：
   - `node_path_baseline`：**仅 P1 开局过渡屏**写（`evidence='transition_row'`，链正本 §3「P1 基线唯一权威源」）；P2/P3 过渡屏行属前位面 → 不写基线（其基线由 §2.1-2 的 prep_row_first 承接）。
   - `node_path`（离场快照）：每次过渡屏行 = 刚离开位面的链终值（`evidence='transition_snapshot'`，链正本 §3）。
   - **挂点（对抗 F6）**：`_click_blank`（两路径共享的点击执行体，cw_screen_plane_transition.py:107-121）点击前读行写链——旧路径与五段路径都触达；两路径各留一条触达断言判据（landing §3.3）。
   - **开局判别与行归属位面（对抗 F10）**：开局判别 = 容器节点镜像三源全缺（复用 kernel 过渡腿先例语义 cw_game_state.py:3383-3391「三源全缺 = 开局过渡屏形态」）；行归属位面 = 开局 1 / 非开局取节点镜像 plane（镜像缺失 → 链写跳过，诚实缺位）。**接管局残余风险申报**：镜像三源全缺 ⟺ 游戏最开端（恢复后必有观察使镜像有值），故「接管落在 1→2 屏被误判开局」要求镜像全缺且行已变异——仅「环境已选但从未有任何备战帧观察」的极端崩溃恢复形态可能发生，如实申报接受（误写基线的后果 = diff 可能误报一次改写，两帧门与离场豁免不放大）。
4. **diff 证据接线**（B-3）：`chain_diff(baseline, current)` kernel 纯函数（链正本 §4 全规则：rewrite 位集/通道受限差单列/长度差/首差位/基线覆盖位集；触发纪律 = 基线在场 ∧ 连续两个 clean 备战帧读数一致才记、离场快照豁免两帧门、变异窗豁免）→ obs_event 行型 2，event 词 `chain_diff`（`OBS_EVENT_EVENTS` 封闭集扩一项，cw_game_state.py:262）。身份归因不猜（消费侧 join active_env/active_strategies 同帧快照，链正本 §5）。
5. **消费接线（类型派生四②「商店查现行链」）**：派生管线类型派生步的**商店面板块触发面**（对抗 F9：触发面 = 屏名 ∈ 商店面板块（SCREEN_CONTEXT_POPUP_FAMILY 成员「货币战争-备战-开商店」），非「一切未定型画面」；plane/round 取值 = 刚推进的 hist 反解，仿 cw_game_state.py:3383-3391 三源序）调 `chain_node_type(bs, plane, round_num)`——token 非 None → `_write_derived_node_type`（actor 语义=派生规则四②）；None（链缺/越界/未辨/位面不匹配）→ 维持现状零写（链正本 §6 零内建回落）。非商店画面零查链零写。
   - **随后删除商店回填写端**（cw_screen_buy_cards.py:951-973 整段）——派生管线已在进店时把类型挂上，回填被结构性替代。查链命中语义 = 上一备战帧该位为 upcoming 的 Hu 读数（§2.1-2 左移映射），与被删回填的台账查表值同源（台账同类读数的合并视图），等价性由测试锁。
6. **变异窗语义重定义**（对抗 F7）：`env_grace_until` 保留两职责——开窗（投资环境确认点，cw_screen_invest_env.py:432 现状）+ 三票校验/session 写点③豁免（现状）；**关窗点** = 备战帧轮位对齐 clean 链读（§2.1-2，提前于 45s 自然过期，行为改善申报）。链写不再受窗门（§2.1-2）。
7. **session 台账在役消费点全量枚举（对抗 F2/F12，冻结依据）**：删回填后台账消费点 = ①`read_game_state` 节点类型查表优先主值（cw_observation.py:2245-2246，经漏斗进容器并写 session.last_node_type）②装备 O1 门兜底（cw_equip_wear_plan.py:258-275，mandate 生产可达）③三票校验（cw_observation.py:2248）。全部**保留在册**；台账退役另批（承接范围见 §1 不解决清单）。

### 2.2 接口契约（唯一必须在总纲定死的深度内容）

- **管线段序不变**（效果账本迭代已钉：上下文对 → 顶栏观察层 → 节点域四腿 → 类型派生 → 效果推进段）；本迭代只在「类型派生」步内加商店面板块查链分支，不动段序。
- **链写入口唯一**：`bs.observe(node_path/node_path_baseline, NodeChain, ...)`（obs 渠道①）；禁专用写函数旁路（写入口统一辖，journal 自产行）。
- **TokenCell 产出的唯一合法源（精确到方法）**：①备战帧 = `CwScreenPrep` 入口 heavy 观察的节点行读点（`cw_observe_full` heavy 链的行读升格，对抗 F1/F6 挂点裁决）；②过渡屏 = `CwScreenPlaneTransition._click_blank` 点击前读行。其余代码禁构造 TokenCell 写链。
- **查询唯一口** = `chain_node_type(bs, plane, round_num)`（链正本 §6）；消费方 = 类型派生商店面板块触发面（§2.1-5），禁第二处；读口适配（解 `NodeChain.seq`、逐格 `token`、plane 不匹配 → None）随载体升级同批（对抗 F5）。
- **sim 边界取舍**（对抗 F4）：链正本 §7 规定 sim 合成口构造 TokenCell 写链（基线恒等现行）；**本迭代裁剪为不写**（sim 无中途改写建模，今日 node_path 亦零写端，写与不写对 sim 决策零差；裁剪省合成口改造面）——与正本的分歧已排入正本更新清单（§3.2 正本更新清单 chain-observation.md §7 行），非引用依据。

### 2.3 关键取舍（备选 + 为何放弃）

1. **决策直查 session 台账（B 型小改）vs 链落 A 型**：放弃直查——session 是 flow 侧载体，决策域单点改会漏深消费点（mandate_v1/flow 多处 `node_kind_of`），且违反「观察进 game state」方向（用户 2026-09-16 裁定「旧的一定要删掉」）。
2. **node_path 保留 list[str] + 旁挂元数据字段 vs 载体升级 NodeChain**：放弃旁挂——通道/残差是逐格属性，旁挂字段必须按位对齐（双字段同步 = 新双源）；链正本 §2 载体已定 TokenCell 逐格元数据。
3. **按位合并写 node_path（沿用 session 表语义）vs 整帧覆盖**：放弃按位合并——链正本 §2 明文「统一 state 存帧事实，合并视图归判读侧台账，防两种语义搅在同一字段」；插入节点场景整帧覆盖天然正确（session 表按位合并反而依赖 None-保旧补丁）。
4. **过渡屏行归属用高亮球识别 vs 位面序号推导**：放弃球识别——高亮球跟随「已到达位面」而行内容是「刚离开位面」，两者错位；「到达位面-1（下限 1）」推导零识别成本且三情形（开局/1→2/2→3）统一（对抗 F10 的接管残余风险申报见 §2.1-3）。
5. **删 session 台账三写点 vs 冻结**：放弃删——三票校验与采集验证仍消费（链正本 §7 现状不动条款）；台账退役另批（本迭代 §1 明确不解决，承接范围含对抗 F2/F12 枚举面）。
6. **链写挂关店探针 vs 备战入口 heavy（对抗 F1 二选一）**：放弃探针——探针仅关店后两 shop 流程点触发，受开店门控（无店轮不写）且五段测试路径不触达；入口 heavy 两路径共用、每备战帧必经、首店前链已在位。代价 = 入口行读升格改造（现读弃槽 → 构造写链）+ current 槽左移填充接线，本设计 §2.1-2 已钉。
7. **变异窗对链写设门（沿 session 写点③现状）vs 不设门**：放弃设门——链 = 最新权威读数整帧覆盖，变异中帧自愈；窗门会让「关窗」与「写成功」循环依赖（对抗 F7 实证的逻辑不可达）。窗保留三票/session 写点③豁免原辖域。
