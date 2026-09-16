# 链观察落地 设计对抗报告（attack.md）

> 对抗对象：[design.md](design.md)（总纲，单文档方案）+ [landing.md](landing.md)（阶段拆分），两份一并攻。
> 依据源：[chain-observation.md](../../game_state/chain-observation.md)（链正本）、fields.md §3.1.5/§3.2.2/§3.7、
> node-domain.md、iteration-design.md §5/§7；代码面对账 = 本文各发现内嵌行号，全部逐条实读核验。
> 对抗日期：2026-09-16（与设计同日，首审）。

## 0. 分级结论

| 核 | 结论 | 一句话 |
|---|---|---|
| 核一·无前提 | **打回** | 核心替代场景（商店查链）的写端挂点未定且两个候选挂点对场景成败相反；P2/P3 基线「首帧回填」无实施批；3.1 阶段内部自相矛盾；生产双路径触达未钉。 |
| 核二·规范遵循 | **打回** | sim 域引用与链正本 §7 反向（正本说写、设计引它禁写）；「current→label」映射与识别面代码现状不符；「唯一生产消费方」主张无依据且被代码证伪；多处语义选择留给实现者。 |
| 核三·治本 | **打回** | 归层（流程层+迁移烂尾）与「容器单源」方向成立，但「session 台账冻结=现状不动不新增职责、退役另批」的申报建立在失实前提上——台账在删回填后仍有两类活生产消费点，退役路径申报范围失真。 |

计数：**blocker 1 / major 6 / minor 5**（共 12 项）。零结论项无——发现均为带行号/节号的实质项。

## 0.1 已核属实面（两向核验，修订时无需动）

- 现状锚全部属实：台账三写点①（cw_screen_plane_intel.py:495-506）②（cw_screen_invest_env.py:448/451-484）③（cw_screen_prep.py:3206-3210）；商店回填段 cw_screen_buy_cards.py:951-973（与设计行号精确一致）；轮位对齐门 cw_screen_prep.py:3195-3205、变异窗门 :3208、开窗点 cw_screen_invest_env.py:432；`node_path: Field[list[str]]`（cw_game_state.py:2532）零写端恒空；`chain_node_type` 语义预留（:3458，docstring「查链接线归件 B 实施批」）；`SCREEN_NODE_TYPE_DIRECT` 商店不入映射=未定型零写（:218-230）；`OBS_EVENT_EVENTS` 现值 (arbitrate, miss, popup)（:262）。
- 链正本 §2/§3/§4/§6 的语义映射（TokenCell/NodeChain 形状、channel 封闭集、整帧覆盖/基线整值覆盖、diff 触发纪律、零内建回落、失读放行）逐条忠实，无复写越界。
- fixture `sr-od-test/screens/货币战争-位面过渡/plane_1to2.webp` 存在，实读确认：球 1 高亮 + 底部 9 槽全行（补给/战斗/遭遇/奖励/boss 可辨形），与 plane_schedule_observed.md P1=9 地面真值形态一致；「开局屏同构歧义」（球 1 高亮行=P1）成立。
- schema 域升版机制在册（DEFAULT_BS_SCHEMA 'node' 域 :135；'derivation':3 升版注记先例 :150-153），design §2.1-1 的「按 fields.md §3.7 机制」可落地。
- 特别攻击点④（删回填与查链接线间的窗口真空）：**不存在**——landing 3.5 同批内先接线后删；3.1-3.4 期间回填继续查 session 台账，行为无窗。
- 特别攻击点⑤（写点③保留后的双写）：**自洽**——session 侧零改动、零新增职责，双载体语义分格已在链正本 §7 申报。
- 写作硬规则 3（无过程叙事）：design/landing 无「本轮/修订后」类措辞；承接出处指针合法（iteration-design §1.1）。
- landing 结构：五阶段+末阶段七件齐，依赖序（3.4←3.2+3.3；3.5←3.2/3.3/3.4）与「判据不依赖他阶段未完成部分」的粒度判据合规；正本更新清单按行「文档：节 ← 阶段」成列。

## 1. 发现表

### F1 [blocker]［核一/核二］商店查链核心场景：写端挂点未定，且两个候选挂点对该场景成败相反；current 槽映射与识别面现状不符

- **位置**：design.md §2.1-2（「备战入口 heavy 观察的节点行读数（read_node_sequence，现役调用点 = cw_screen_prep.py:3155 邻域）」+「current → channel='label'/token=OCR 标签」）、§2.1-5；landing.md §3.2。
- **发现**：
  1. **挂点锚自相矛盾**。设计把写端挂在「备战入口 heavy 观察」的行读数上，行号却指向 `_probe_node_type`（def 在 cw_screen_prep.py:3113，read_node_sequence 在 :3135）——该方法在现役代码中**只在关店后的两个 shop 流程点被调用**（:2781 read_only 开店重读后、:3043 买牌波次收尾后），不是备战入口；备战入口 heavy 观察（`_observe(heavy=True)` :620，两路径共用 :1964/:2159）里的行读在 cw_observe_full.py:135 只作完整度旗标后**弃槽**。两个真实候选挂点对四②查询的结局相反：
     - 挂**入口**：入口帧 current 槽=本轮 → 整帧覆盖把本轮槽写成 None（见下 2）→ 弹窗腿进店查 `chain_node_type` **恒 None** → 零写，回填被删后商店类型彻底失明；
     - 挂**关店探针**（现役 :3135 所在点）：上一轮探针写链时本轮节点还是 upcoming（Hu token 在位）→ 进店查询恰命中；但该点节奏受「本轮有没有开店」门控（无店轮不写链），且五段测试路径不经过它（见 F6）。
  2. **current 槽映射产不出 token**。识别面现状（cw_screen_prep.py:3144-3149 注释 + :3216-3225 实现）：current 直读 Hu 不匹配（模板只对 future 生效）+ OCR 标签错位守卫 → **current 直读恒 None**，本轮 current 类型靠「last-known upcoming 左移推断」（session.nodeseq_probe_anchor，:3226-3235）。设计 §2.1-2 的「current → channel='label'/token=OCR 标签」照码面现实恒得 token=None；左移推断机制设计只字未提，通道语义（左移值源自上一帧 Hu 读数，标 label 还是 hu？）也无答案。
  3. **验收场景造不出来**：landing §3.2/§3.5 的「clean 备战帧→整帧覆盖」「商店弹窗腿进店（链在位）→ node.kind=查链直定值」在上述任一字面实现下，生产时序都无法自然出现「链在位」——单测手工构造可绿，生产恒走 None 分支，删回填的核心替代价值（design §2.1-5「回填被结构性替代」）不成立。公平注记：P2/P3 r1 商店盲区在现状台账下同为 None fail-open（普通局 P2 首店前台账无该位面行），链方案此处不回归、也无改进。
- **建议修订落点**：design §2.1-2 钉死写端挂点（关店探针点，或入口重接线+左移填充——二选一并写明理由）；current 槽的取值链与通道语义按左移推断现实重定义；§2.2 契约补「TokenCell 产出源=挂点 X 的行读数升格」精确到方法；landing §3.2 范围与判据补「生产时序下四②查询命中」的可验收形态（如 harness 剧本按真实帧序演）。

### F2 [major]［核一/核三］「ledger_node_type 唯一生产消费方=被删的商店回填」主张被代码证伪；3.5 判据「生产零调用」不可满足；台账退役申报范围失真

- **位置**：design.md §2.1-7、§2.3-5；landing.md §3.5 完成判据（「`ledger_node_type` 生产零调用（函数保留申报）」）。
- **发现**：删回填后 `ledger_node_type`（cw_exec_state.py:744）仍有两类**行为级**生产消费点：
  1. cw_observation.py:2245-2246——`read_game_state` 节点类型**查表优先主值**（`node_type = _ledger_t if _ledger_t is not None else _obs_t`），不是设计所申报的「三票校验与采集验证」纯记账面（:2248 的 verify 才是）；该主值经漏斗进容器并写 session.last_node_type（cw_screen_prep.py:725-726）。
  2. cw_equip_wear_plan.py:258-275——装备穿戴计划以台账值作当前节点类型兜底 + O1 门「后随节点类型」输入，经 mandate_v1 分发段生产可达（strategies/impl/mandate_v1/mandate.py:1922-1928）。
  连带后果：§1「明确不解决：session 台账退役……现状不动」与 §2.1-7「生产零调用→退役另批」的退役叙事失真——不重接这两处消费，台账永远退不了役；「防双源=冻结不新增职责」的自洽性受损（台账仍是容器观测值上游主源，双源不是冻结态而是活耦合态）。
- **建议修订落点**：design §2.1-7 改写为如实枚举全部在役消费点并逐个定性（保留/重接/退役归属）；landing §3.5 判据的「生产零调用」改为可满足形态（如「`node_ledger_backfill`/`_refresh_node_ledger` 零残留 + read_game_state 查表优先与 equip_wear_plan 查表消费点在册申报」）；台账退役另批的承接范围在 §1 补一句（含 F12 两族载体）。

### F3 [major]［核一］P2/P3 基线「首帧回填」无实施批——diff 在 2/3 位面永久关闭，且未申报

- **位置**：design.md §2.1-3（只落 P1 开局 transition_row 基线；「P2/P3 过渡屏行属前位面 → 不写基线」）、§1 明确不解决清单；landing.md §3.2/3.3/3.4（无任何基线回填范围）；链正本 §3（回退序 `transition_row > plane_detail > prep_row_first`；「P2/P3……→基线=首帧回填，diff 观察窗较 P1 收窄」）。
- **发现**：链正本对 P2/P3 基线的定义是「首帧回填」（prep_row_first/plane_detail 两回退源）。设计引用了这句话却不实现任何回填——§2.1 全部七个变化项里没有 prep_row_first 或 plane_detail 写基线的机制，landing 五阶段同样没有。后果：P2/P3 的 `node_path_baseline` 永远为 None → diff 触发门「基线在场」（design §2.1-4）在 P2/P3 **结构性恒假** → 本迭代核心交付「diff 证据接线」对 2/3 位面静默失效。链正本的「如实申报」被设计引用了，但设计自己在 §1「明确不解决」里**没有**申报这个后果；「观察窗收窄」与「恒关闭」是两回事。
- **建议修订落点**：三选一并落阶段——① landing 3.2 范围扩：位面内首个 clean 链写同时回填基线（prep_row_first，evidence 区分）；② 新增小阶段做 plane_detail 降级回退源；③ design §1 明确不解决加一条「P2/P3 基线回填不实施，diff 限 P1」并把 landing 3.4 判据改写为 P1-only 验收。当前文本三条都不占。

### F4 [major]［核二］sim 域引用与链正本 §7 反向：正本规定 sim 合成口写链，设计引「链正本 §7 边界」禁写，且正本更新清单无对应该行

- **位置**：design.md §2.2 契约第 3 条（「其余代码禁构造 TokenCell 写链（sim 合成口不写链，链正本 §7 边界）」）、§1 明确不解决第 2 项（同引）；链正本 §7 sim 条款（「合成口基线恒等于现行……合成单元 TokenCell 填 `channel='none'`、`hu_dist=None`，evidence 恒带 `sim:synthesized`」）；landing.md 正本更新清单（73-79 行，chain-observation.md 仅 §3 一行）。
- **发现**：链正本 §7 的 sim 边界条款**明文规定** sim 合成单元构造 TokenCell 写链（基线恒等于现行），是「如实申报的边界」不是禁令；设计把它引用成「sim 合成口不写链」的依据——引用方向相反。设计收窄 sim 行为本身可以是合法取舍（sim 无中途改写建模，今天 node_path 也零写端），但：①依据不能挂正本 §7；②收窄与正本冲突时必须在正本更新清单排 §7 条款的修订行，否则迭代收尾后正本与实现长期互斥。
- **建议修订落点**：design §2.2/§1 去掉「链正本 §7 边界」错标，改为显式取舍申报（「正本 §7 规定 sim 合成口写链；本迭代裁剪为不写，sim 商店腿类型维持 None，与实机分歧如实申报」）；landing 正本更新清单补「chain-observation.md §7 sim 条款 ← 3.1（写端范围收窄后边界改注）」。

### F5 [major]［核一］3.1 载体升级批与 chain_node_type 读口适配互相矛盾：范围声明排除、判据强制、生产崩溃窗、plane 校验无人认领、journal 跨版本判读无申报

- **位置**：landing.md §3.1（范围「**不含**任何写端与消费接线」vs 完成判据「全仓 node_path 旧值形消费点 grep 零残留（现役仅 chain_node_type 读口，已核）」）；cw_game_state.py:3471-3478（`chain[idx]`/`str(chain[idx])`，无 plane 校验）；design.md §2.1-1（「值自带位面防切换窗读陈旧链」）。
- **发现**：
  1. 值形 `list[str]` → `NodeChain | None` 后，`chain_node_type` 现实现立即成为旧值形残留：`len(chain)`/`chain[idx]` 对 NodeChain dataclass 抛 TypeError。3.1 判据要求「grep 零残留」= 必须同批适配该读口，但 3.1 范围明文「不含任何消费接线」——同一阶段内范围与判据互斥，实现者只能自行拍板（违硬规则 2）。
  2. 适配内容本身是语义设计：解 `seq`、`TokenCell.token` 取值、**plane 不匹配返回 None**（design §2.1-1 的防陈旧链语义，现实现无此校验）——三件事都没有归属阶段。
  3. journal 历史行兼容（特别攻击点③后半）：旧档 `node_path` 行 = list[str]、新行 = NodeChain，域版本升了但没有申报任何跨版本判读分流（判读 CLI/档案装配面 = retirement.md §7 #1-#3，现态「候」）；至少要一句话申报「旧档只读保留、新读面按域版本分流」或声明暂无消费方。
- **建议修订落点**：landing §3.1 范围明写「chain_node_type 读口适配（解 seq/plane 校验/TokenCell.token）」并补对应单测判据；正本更新清单补 fields.md §3.2.2 的跨版本判读申报行（或在 design §2.1-1 加一句边界申报）。

### F6 [major]［核一］过渡屏/prep 两写端的生产双路径触达未钉（特别攻击点⑥）

- **位置**：landing.md §3.3（「`CwScreenPlaneTransition` 观察段在「点击空白处继续」前读行」）、§3.2；cw_screen_plane_transition.py:99-105（生产=旧路径直连 `_click_blank`）/125-139（五段 `lifecycle_observe` 仅测试装配）/107-121（`_click_blank` 两路径共享）；cw_screen_prep.py:2781/3043（`_probe_node_type` 仅旧路径 shop 流程调用点）；cw_game_ports.py:157-191（端口缺省 None=生产旧路径，仅测试 harness 安装）。
- **发现**：统一观察架构并存期，生产对全部画面走旧路径、五段路径只有测试 harness 走。设计/landing 用「观察段」这个词（五段术语）描述写端挂点却没钉死：3.3 若挂 `lifecycle_observe`，生产（旧路径）**永远**不读过渡屏行——基线/离场快照在生产恒缺，而单测走五段路径全绿；挂两路径共享的 `_click_blank` 内（点击前）则两路径都到。3.2 同理：链写若随 `_probe_node_type` 走，五段 harness 路径不触达（反向缺失）。landing 的验收判据没有一条区分路径。
- **建议修订落点**：landing §3.2/§3.3 范围钉死挂点方法名并声明「两路径触达」为硬要求（3.3 挂 `_click_blank` 点击前为现成共享点；3.2 按 F1 的挂点裁决同步钉路径）；两阶段各加一条「旧路径与五段路径各执行一次写端触达」的断言判据。

### F7 [major]［核一/核三］变异窗关闭点迁移自相矛盾：「非门拒写成功才关窗」⇒ 关窗分支对变异窗永不可达，窗恒满 45s，「行为等价」主张为假（特别攻击点②）

- **位置**：design.md §2.1-6（「链写成功（非门拒）即关窗……行为等价」）+ §2.1-2 写门（「非变异窗（`env_grace_until` 未过期拒写）」）；cw_screen_invest_env.py:113（`ENV_GRACE_S = 45.0`）、:432（确认前开窗）、:480（现役：重读成功**提前**关窗，通常确认后数秒）；cw_screen_prep.py:3206-3208（窗内拒写门）。
- **发现**：把两条规则合取：窗内 → 写门必拒 → 无「写成功」→ 不关窗；窗外的写成功 imply 窗已过期 → 关窗是空操作。即迁移后备战帧关窗分支对变异窗本身**逻辑不可达**，窗只能靠 45s 自然过期。与现状对比不是「行为等价」：现役写点②在确认后 ~2-4s 读到 clean 帧即提前关窗（:480），三票校验豁免窗与「查表不一致豁免」同步收口；迁移后豁免窗恒拉满 45s，首个权威链读推迟。漏关路径核验：过渡屏写关窗（design §2.1-6）时点在位面末，对 45s 窗恒为过期后空操作；链读失败帧不关窗——两路径都**存在但被 45s 死线兜底**，无永久卡窗，行为差真实存在。
- **建议修订落点**：design §2.1-6 二选一——①关窗判据与「写成功」脱钩：clean 帧行读成功即关窗（无论两门是否拒写），并把该读作为变异后首笔真相的语义写清；②接受「窗恒满 ENV_GRACE_S」并申报影响面（三票豁免窗拉长的缺陷台账盲区、链读延后对四②的窗口期影响）。同时申报写点②删除后「确认后短窗重读」职责的承接归属（现在无人读）。

### F8 [minor]［核一］正本更新清单指向不存在的文件；链正本 §5 自身引用已作废排期框架

- **位置**：landing.md 正本更新清单第 5 行（「`telemetry/retirement.md` §5（若词登记状态需同步 chain_diff 词接线）」）；game_state/retirement.md（实际唯一路径；其 §5 = 退役排期对照表，无 chain_diff 词登记状态记载，影子 M1-M5 框架已裁定作废）；链正本 §5（「登记归迁移批 M1，接线归 M2——见 retirement.md §5」引的正是已作废影子框架）；词表现状真实载体 = cw_game_state.py:262。
- **建议修订落点**：清单行改为 `game_state/retirement.md`（或直接 chain-observation.md §5 的登记表述核对）并去「若」字条件化；M1/M2 措辞按 retirement.md §5 对照表换算为直迁波次表述。

### F9 [minor]［核二］「未定型分支」门谓词未钉死：错选会给备战帧等画面新增 kind 写端

- **位置**：design.md §2.1-5（「cw_game_state.py:3118 ……的未定型分支接 chain_node_type」）；cw_game_state.py:3118-3124（`_direct_kind is None` 分支覆盖**一切**非直定画面：备战/过渡/简报/弹窗族外全部）；node-domain.md §7（语义 = ②**商店**查现行链）。
- **发现**：若实现者按「`_direct_kind is None` 即查链」实现，备战帧/过渡帧等也会触发查链写 kind——时序上恰有上一探针残留值时（F1 挂关店探针形态），备战入口会多出一条与三源仲裁竞争的 kind 写端，行为面扩大。「仅商店画面触发」与 plane/round 来源（=刚推进的 hist 反解，仿 ：3383-3391 三源序）设计均未写明。
- **建议修订落点**：design §2.1-5 钉「触发面 = 商店面板块（SCREEN_CONTEXT_POPUP_FAMILY 内商店屏）」+ plane/round 取值式；landing §3.5 判据补「非商店画面零查链零写」一例。

### F10 [minor]［核一］P1 开局屏判别机制未定；行归属位面取值源未钉；接管局形态未分析（特别攻击点①）

- **位置**：design.md §2.1-3（「P1 开局过渡屏（0q 首现）」「行位面 = 即将进入/当前位面序号 - 1，开局（无前位面）= 1」）。
- **发现**：①「0q 首现」的判别器没有答案——候选 = 容器节点镜像三源全缺（kernel 过渡腿现成先例 cw_game_state.py:3383-3391：「三源全缺 = 开局过渡屏形态，禁猜不写」），但设计未指认；②「即将进入/当前位面序号」的取值源（bs.node 镜像 / 顶栏 phase_round / hist 反解）未钉，三源在过渡屏时点的值可能不一致；③接管局：接管恰落在 1→2 过渡屏且容器镜像尚未观察时，「三源全缺」会把 1→2 屏误判开局 → 把**可能已被投资环境变异过的 P1 行**写成基线，污染基线「改型前真值」语义（链正本 §3）。三种过渡屏（开局/1→2/2→3）公式本身自洽（下限 1 兜住开局），接管局是唯一缺口。
- **建议修订落点**：design §2.1-3 补三件事：判别式（援引或复用 kernel 腿的三源序与「全缺=开局」语义）、位面取值源优先序、接管局形态申报（误判开局的后果与接受/防线路）。

### F11 [minor]［核一］验收凭据虚指：fixture「等」不存在；「§12 通用工程门」指针不可解析（特别攻击点⑦）

- **位置**：landing.md §3.3 文件面（「fixture = ……plane_1to2.webp **等**」）；glob 实况 = 目录仅此一张，开局屏/2→3 屏无实拍；§3.3 完成判据的 fixture 离线判读只覆盖 1→2 一型（九槽对照），开局分支（基线落）与 2→3 分支无离线对照物；各阶段「§12 通用工程门（引用，不复述）」——AGENTS.md §12 = 自维护指南，无工程门内容，指针不可解析（可解析先例 = changes/2026-09-15-prep-single-action-contract/landing.md:14「引用 = 项目 AGENTS.md『测试规范』§10.3 与『MCP』节」）。
- **建议修订落点**：①删「等」或补实拍采集义务（开局屏可从简报后实机帧采集，2→3 屏等 P2 局）；②通用工程门写成可解析实指（照 prep-single-action-contract 先例）。

### F12 [minor]［核三/核一］§1 双源盘点不全：session 侧节点类型载体实际至少四族，冻结/退役申报漏列两族

- **位置**：design.md §1（症状只点名 `NodeLedger.seq_by_plane`）与 §2.1-7（冻结条款同）；cw_screen_prep.py:240-260（`store_plane_table` → `sess.plane_node_table` + `plane_lengths_seen`，开局帧每位面首帧写、**无两门**，ADR-0368）；cw_strategy_session.py:140（`last_node_type`）。
- **发现**：与链构成多源的 flow 侧载体不止台账一族；「现状不动、不新增职责」对漏列载体同样成立（无阻塞），但「退役另批」的范围申报（含 F2 两处消费点）不列全，退役批立项时会再走一次今天的发现路径。
- **建议修订落点**：design §1 明确不解决清单补列 plane_node_table/plane_lengths_seen 与 last_node_type（一句「同族载体一并归台账退役批盘点」即可）。

## 2. 裁决备注

- **F1 是唯一 blocker**：它同时命中定稿门槛两卡点（试读——按设计字面实现核心场景失灵；实现者无需再设计——挂点/通道语义两处必须的设计决策缺位）。F1 与 F5/F6 同根（写端「挂在哪、什么时序、哪条路径」三问），建议修订时一并重写 design §2.1-2 与 landing §3.1/3.2/3.3 的对应范围句。
- 治本方向本身被确认：归层正确（容器/schema/查询口在位、写端缺位 = 实施批未做，代码证实），「观察进 game state + 删流程层违例写端」是收敛双源的根方向，不是逐件补丁；打回点全部集中在**申报与锚定的失真**（F2/F4/F7/F12），修申报即可，无需推翻方案骨架。
- 本报告不构成本迭代范围裁决；「明确不解决」清单按 F3/F4/F12 修订后，其外溢面判定（iteration-design §1.1）应在设计修订时复核一遍。

## 3. 复查结论（2026-09-16，修订版 commit 18e5ec231）

对修订版 design.md（§1/§2.1/§2.2/§2.3 全量重写）与 landing.md（全量重写）逐项对码复查。核验方式 = 每项修订主张回到代码/正本实读对账，重点复攻 F1（挂点+时序）与 F7（关窗可达性）。

### 3.1 原发现逐项消解核验

| 原发现 | 消解 | 核验证据 |
|---|---|---|
| F1 挂点+时序 | **消解** | 挂点改入口 heavy 行读升格：cw_observe_full.py:135 的行读确在 heavy 链内逐帧无条件执行（子态完整度字典处，现读后弃槽），且在 read_game_state 漏斗（:108）之后——镜像本帧已新，轮位对齐门的 round_num 输入与现役探针门同源可用；入口 heavy 两路径共用（旧 run() cw_screen_prep.py:1964 / 五段 :2159 均经 `_observe(heavy=True)`）。「查询恒 None」被消除的机制核验：current 槽 = 左移推断，载体三件套全部在役（session.upcoming_types cw_strategy_session.py:146、node_type_current、nodeseq_probe_anchor，写点 cw_screen_prep.py:3231-3246），round N 入口写以 N-1 帧 upcoming[N] 的 Hu 值填 current → 弹窗腿进店查 chain[N] 命中；首帧/位面首帧 anchor 缺 → OCR 兜底 → None，与现役台账同时点行为一致（fail-open 等价，无回归）。landing §3.2 的「生产时序四②命中 harness 剧本」判据直接锁该帧序。左移状态写入与探针现状的双写共存：upcoming_types 现消费面仅 buy_cards.py:1087 日志披露，双写无行为冲突。 |
| F2 台账消费点 | **消解** | design §2.1-7 三处消费点全量枚举（cw_observation.py:2245-2246 查表优先 / cw_equip_wear_plan.py:258-275 / 三票 :2248）与代码一致；§1 不解决清单承接范围含退役消费点重接；landing §3.5 判据改「删除面 grep 零残留 + 在役消费点在册断言（防误删）」——可满足形态。 |
| F3 P2/P3 基线 | **消解** | prep_row_first 入 §2.1-2/landing §3.2 范围（空则写/非空不覆单测在册）；P1 transition_row 先落档不被覆盖，与链正本 §3 回退序「以最先落档者为准」一致；§1 补 P2/P3 观察窗收窄申报；plane_detail 中间源不实施 = 由 prep_row_first 承担回退序职能，配合 baseline_coverage 显影 None 洞，语义自洽。 |
| F4 sim 引用反向 | **消解** | design §2.2 末条如实转述正本 §7 原文并显式裁剪（§1 不解决同步改），landing 正本更新清单补 chain-observation.md **§7 行**。 |
| F5 读口适配矛盾 | **消解** | landing §3.1 范围明写 `chain_node_type` 读口适配（解 seq/逐格 token/plane 不匹配→None）+ 四态单测；「grep 零残留：仅剩读口适配一处」判据改自洽；跨版本判读边界申报入 §2.1-1（「现判读 CLI 不消费 node_path 域」与本审 grep 实况一致）。 |
| F6 双路径触达 | **消解** | §3.2 挂点钉 cw_observe_full heavy 链读点（两路径实共用以 :1964/:2159 实证）；§3.3 挂点钉 `_click_blank`（cw_screen_plane_transition.py:107-121 两路径共享体）；两阶段各留一条两路径触达断言判据。 |
| F7 关窗可达性 | **消解** | 语义重定义后循环依赖消除：链写不受窗门（变异中帧整帧覆盖自愈，误报由 diff 两帧门+窗内豁免拦截）；关窗 = 轮位对齐门过 ∧ 行读成功（与写执行脱钩）——入口 heavy 每备战帧必经，环境确认后首个备战帧即达，关窗分支可达；三票豁免窗提前收口 = 行为改善已申报。与现役对比（提前关窗 ~数秒 vs 首个备战帧）如实申报。 |
| F8 清单路径 | **消解** | 正本清单改 `game_state/retirement.md` 并去条件化；chain-observation.md §5 表述核对已列。 |
| F9 触发面谓词 | **消解** | 触发面钉「屏名 ∈ 商店面板块『货币战争-备战-开商店』」——屏名实证为弹窗族成员（cw_game_state.py:177）且该屏观察确实流经类型派生步（cw_observation.py:2726 分支）；plane/round = hist 反解仿 :3383-3391；landing §3.5 补「非商店画面零查链」判据。 |
| F10 开局判别/接管 | **消解** | 判别 = 镜像三源全缺（kernel 过渡腿先例语义）；行归属改「非开局取镜像 plane」——核验为正确且比 v1 的「-1 公式」更稳：过渡屏时点 bs.node 镜像未被 0q 腿改写（`_derive_node_plane_transition` 只写 node_ord/hist，cw_game_state.py:3395-3398），镜像恒持刚离开位面，公式与派生时序无关；镜像缺失跳写诚实缺位；接管残余如实申报且后果有界（两帧门不放大）。 |
| F11 验收凭据虚指 | **消解** | 删「等」；开局屏/2→3 屏实拍补档列为显式义务（候实机验证期）；通用工程门改为 landing 首节自包含定义（源标注 AGENTS.md 对应节），可解析。 |
| F12 双源盘点 | **消解** | §1 承接范围补列 plane_node_table/plane_lengths_seen（cw_screen_prep.py:240-260）与 last_node_type（cw_strategy_session.py:140）。 |

### 3.2 复查新发现（均为 minor，随定稿落笔即可闭合）

**F13 [minor]［核二］链写「变异窗不设门」偏离链正本 §3 写门语义，正本更新清单漏排该条款修订行。**
- 位置：design.md §2.1-2 写门节 + §2.3-7（取舍已论证、正文已申报）；链正本 §3 现行链行（「备战帧链读（quality=prep_row；**轮位对齐门∧非变异窗才写**）」）；landing.md 正本更新清单 chain-observation.md 行（§3 仅排「quality 值域两义注并轨」）。
- 发现：修订删去窗门是经论证的取舍（§2.3-7，本审 F7 的消解手段），无错误引用；但正本 §3 的写门条款与实现将长期不一致，而清单该行未覆盖——与 F4 同类缺口（F4 已修，此处漏网）。
- 建议修订落点：正本更新清单 chain-observation.md §3 行补「写门条款修订（链写不受变异窗门，取舍 = design.md §2.3-7）」一词。

**F14 [minor]［核二］逐格映射的 boss 末槽 SIFT miss 分支未定。**
- 位置：design.md §2.1-2 逐格映射（「boss 末槽 → channel='sift'」，无 miss 分支）；cw_node_reader.py:218-222（boss 槽 SIFT 未命中 → None 保守不猜；**boss 槽 Hu 距离系统性不可靠**——「boss 圆 Hu 2.05 撞 encounter」在案）。
- 发现：SIFT miss 时该槽走哪条规则未答——若按 upcoming 通用规则「hu 超阈→none」兜，boss 槽 Hu 系统性偏差可产 'encounter' 类误 token（对 baseline 'boss' 构成假 diff 候选，两帧门可拦但噪声面真实存在）。实现者面临一个设计未答的分支选择。
- 建议修订落点：§2.1-2 映射表补一句「boss 末槽 SIFT miss → channel='none'/token=None（禁回落 Hu 判定——boss 槽 Hu 距离不可靠，cw_node_reader 在案）」或等价裁决。

### 3.3 复查裁决

**定稿可。** F1-F12 全部消解（含两项重点复攻：F1 的挂点/载体/时序三要素全部落到在役代码锚，F7 的关窗分支在新语义下可达且行为差已申报）；无 blocker/major 存留。F13/F14 为两处一行级文档补丁（正本清单补一词 + 映射表补一分支句），属定稿随批动作，不构成重开对抗的事由——按 iteration-design §6「定稿门槛 = 攻击收敛」，两处落笔后本迭代设计即满足定稿条件，可立阶段任务。
