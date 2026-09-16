# 链观察落地 迭代设计（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-16 会话，统一观察对账迭代确认流程揪出两个违例写端后的架构归位令）——节点类型链按既有正本设计（[chain-observation.md](../../../game_state/chain-observation.md)，下称「链正本」）落地进 game state：观察写入容器、派生管线自查类型、删两个流程层违例写端。承接出处：件 B 预留（`chain_node_type` docstring「查链接线归件 B 实施批」）、fields.md §3.1.5/§3.2.2、统一观察对账迭代（changes/2026-09-16-unified-obs-reconcile/）确认批记录。
- 状态：草案
- 文档清单：无详设（单文档方案，本篇即完整设计；链语义正本 = 链正本，本文只做「正本语义 → 当前代码面」的落地映射，不复制正本内容）。

## 1. 问题与动机
- 现状症状（依据 = 统一观察对账迭代归因报告 attribution.md + 2026-09-16 用户确认批）：
  1. 节点类型顺序存在**双源**：session 权威表（flow 侧 `NodeLedger.seq_by_plane`，三个写点在役：位面详情采集①/投资环境重读②/备战帧 heavy 按位合并③）活着；容器 `node_path` 字段（kernel 侧，schema 已注册）**零写端恒空**——kernel 派生管线按「game state 自己算」的方向够不着 session，类型真空。
  2. 两个流程层违例写端在顶班：商店回填（`cw_screen_buy_cards.py`「买后」段，进店查 session 表写容器 node，真读/推算通道混用且掩盖投影漂移）与投资环境写点②（`cw_screen_invest_env.py` 确认后自截屏自读节点行，违反 ADR-0517 唯一读屏点）。
- 根因归层：**流程层 + 迁移烂尾**。链语义正本早已定稿（链正本 §1-§7：载体/双源/diff/查询口），容器字段与查询口也已就位，唯独写端与接线零实现——不是设计缺失，是实施批未做。
- 解决到哪：链正本 §3 双源写端全部落地（基线链/现行链）、diff 证据接线（§4）、类型派生消费接线（§6「商店查现行链」）、删两个违例写端。
- 明确不解决（防外溢）：session 台账退役（链正本 §7 防双源条款=现状不动不新增职责，退役另批）；`chain_baseline`/`chain_rewritten` 两接口（链正本 §6 明文不预纳）；sim 域链合成（§7 边界：合成口不写链，决策消费 `node_kind_of` 不变）；暗格判态阈值多样本校准（cw_node_reader 既有采证义务，独立）；「未定型零写」到「查链」之外的类型仲裁序变化（判定规则本体归场景一判定方案，本迭代只接查询不改编仲裁序）。

## 2. 方案（单文档方案，此处即完整设计）

### 2.1 系统级变化（读一遍知全貌）

1. **载体升级**（kernel/cw_game_state.py）：新增 `TokenCell`/`NodeChain` 数据类（链正本 §2：`TokenCell{token, channel, hu_dist}`，channel ∈ {hu,label,sift,none,dim}；`NodeChain{plane, seq}`——值自带位面防切换窗读陈旧链）。`node_path` 字段值形 `Field[list[str]]` → `Field[NodeChain | None]`（现行链=最新权威读数**整帧覆盖**，跨度=本位面，链正本 §2/§3）；新增 `node_path_baseline: Field[NodeChain | None]`（基线链=位面入口写定，本位面内不被链读覆盖，位面切换整值覆盖，链正本 §2/§3）。node schema 域升版（'node' 域值形变化，版本治理按 fields.md §3.7 机制，升版注记写明两字段）。
2. **备战帧现行链写端**（权威写端，链正本 §3 `prep_row`）：备战入口 heavy 观察的节点行读数（`read_node_sequence`，现役调用点 = cw_screen_prep.py:3155 邻域）升格产 `TokenCell` 序列——state 映射：past → `channel='dim'`/token=None（已通过段不由本帧负责，链正本 §3）；current → `channel='label'`/token=OCR 标签；upcoming → `channel='hu'`/token=Hu 匹配，`hu_dist>HU_DIST_UNRECOGNIZED` → `channel='none'`/token=None；boss 末槽 → `channel='sift'`。写入 = `bs.observe(node_path, NodeChain(...), sig=obs签名, evidence='prep_row')`（统一写入口自动产 journal 写入行，链正本 §5）。**写门（两门，现役语义随迁）**：轮位对齐门（current 槽 idx == round_num-1，错位帧拒写——cw_screen_prep.py:3195-3204 门随迁）∧ 非变异窗（`env_grace_until` 未过期拒写，cw_screen_prep.py:3208 门随迁）。链读失败 → 字段保持未写，不阻塞（链正本 §3 失读放行纪律）。
3. **过渡屏观察段（基线链 + 离场快照）**（operations/cw_screen/cw_screen_plane_transition.py，B-2）：过渡屏（每位面自动出现一次）底部为**刚离开位面**的完整节点行（全亮可读，fixture `plane_1to2.webp` 实证）。op 观察段在「点击空白处继续」执行前读行，写两笔：
   - `node_path_baseline`：P1 开局过渡屏（0q 首现）= P1 入口基线（`evidence='transition_row'`，链正本 §3「P1 基线唯一权威源」）；P2/P3 过渡屏行属前位面 → **不写基线**（设计明文「1→2 显示 P1、2→3 显示 P2 → 基线=首帧回填，diff 观察窗收窄，如实申报」）。
   - `node_path`（离场快照）：每次过渡屏行 = 刚离开位面的链终值（`evidence='transition_snapshot'`，链正本 §3）。
   - **行归属位面判定**：过渡屏行 = 刚离开位面（高亮球=已到达的下一位面，行=前位面——fixture 与链正本 §3 双证）；P1 开局与位面切换共用同一判定：`行位面 = 即将进入/当前位面序号 - 1`，开局（无前位面）= 1。球高亮识别不作判据（B-1 采证已见高亮球跟随到达位面，与行归属错位）。
   - 备战帧现行链写端的门不变；过渡屏写不设轮位对齐门（整行已通关，无 current 槽对齐问题）。
4. **diff 证据接线**（B-3）：`chain_diff(baseline, current)` kernel 纯函数（链正本 §4：rewrite 位集/通道受限差单列/长度差/首差位/基线覆盖位集；触发纪律 = 基线在场 ∧ 连续两个 clean 备战帧读数一致才记、离场快照豁免两帧门、变异窗豁免）→ obs_event 行型 2，event 词 `chain_diff`（词表登记面 = OBS_EVENT_EVENTS 封闭集扩一项）。身份归因不猜（消费侧 join active_env/active_strategies 同帧快照，链正本 §5）。
5. **消费接线（类型派生四②「商店查现行链」）**：派生管线类型派生步（cw_game_state.py:3118 `_direct_kind = SCREEN_NODE_TYPE_DIRECT.get(screen_name)` 的未定型分支）接 `chain_node_type(bs, plane, round_num)`——token 非 None → `_write_derived_node_type`（actor 语义=派生规则四②）；None（链缺/越界/未辨）→ 维持现状零写（链正本 §6 零内建回落）。**随后删除商店回填写端**（cw_screen_buy_cards.py 买后段 951-973：进店查 session 表写容器 node 的整段）——派生管线已在弹窗腿进店时把类型挂上，回填被结构性替代。投资环境写点②同步删（cw_screen_invest_env.py:444-484 `_refresh_node_ledger` 调用与方法体）：变异承接 = 回备战后的链读 + diff 两帧门（本迭代 §2.1-4）。
6. **变异窗关闭点迁移**：写点②删除后 `env_grace_until` 的关闭点迁到备战帧链写端——链写成功（非门拒）即关窗（新读数即变异后真相）；过渡屏写亦关窗。窗语义从「等重读刷新」变为「等下一次权威链读」，行为等价。
7. **session 台账现状冻结**（链正本 §7 防双源）：写点①③（位面详情采集/备战帧 heavy 按位合并）与 `verify_node_type_votes` 三票校验**保留不动**（其消费面 = 三票校验与采集验证，非本迭代辖域）；不新增职责。`ledger_node_type` 的唯一生产消费方 = 被删的商店回填 → 删回填后该查询口生产零调用（保留函数，退役另批申报）。

### 2.2 接口契约（唯一必须在总纲定死的深度内容）

- **管线段序不变**（效果账本迭代已钉：上下文对 → 顶栏观察层 → 节点域四腿 → 类型派生 → 效果推进段）；本迭代只在「类型派生」步内加查链分支，不动段序。
- **链写入口唯一**：`bs.observe(node_path/baseline, NodeChain, ...)`（obs 渠道①）；禁专用写函数旁路（写入口统一辖，journal 自产行）。
- **TokenCell 产出的唯一合法源** = 备战帧节点行读数升格与过渡屏行读数（两处，§2.1-2/3）；其余代码禁构造 TokenCell 写链（sim 合成口不写链，链正本 §7 边界）。
- **查询唯一口** = `chain_node_type(bs, plane, round_num)`（链正本 §6）；消费方 = 类型派生未定型分支，禁第二处。

### 2.3 关键取舍（备选 + 为何放弃）

1. **决策直查 session 台账（B 型小改）vs 链落 A 型**：放弃直查——session 是 flow 侧载体，决策域单点改会漏深消费点（mandate_v1/flow 多处 `node_kind_of`），且违反「观察进 game state」方向（用户 2026-09-16 裁定「旧的一定要删掉」）。
2. **node_path 保留 list[str] + 旁挂元数据字段 vs 载体升级 NodeChain**：放弃旁挂——通道/残差是逐格属性，旁挂字段必须按位对齐（双字段同步 = 新双源）；链正本 §2 载体已定 TokenCell 逐格元数据。
3. **按位合并写 node_path（沿用 session 表语义）vs 整帧覆盖**：放弃按位合并——链正本 §2 明文「统一 state 存帧事实，合并视图归判读侧台账，防两种语义搅在同一字段」；插入节点场景整帧覆盖天然正确（session 表按位合并反而依赖 None-保旧补丁）。
4. **过渡屏行归属用高亮球识别 vs 位面序号推导**：放弃球识别——高亮球跟随「已到达位面」而行内容是「刚离开位面」，两者错位（fixture plane_1to2：球 1 高亮 + 行=P1，恰为一致，但 2→3 屏球 2 高亮而行=P2 同构；真正歧义在开局屏球 1 高亮行=P1，三种情形统一由「到达位面-1（下限 1）」推导，零识别成本）；球识别降级为 B-2 采证的交叉验证项。
5. **删 session 台账三写点 vs 冻结**：放弃删——三票校验与采集验证仍消费（链正本 §7 现状不动条款）；台账退役另批（本迭代 §1 明确不解决）。
