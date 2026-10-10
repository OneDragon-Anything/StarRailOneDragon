# 晶矿奖励附着通道 设计对抗报告(第二轮·修订稿)

第二轮审查:①对第一轮 P1/M1-M6/N1-N6 逐条修复核验(修法可与建议不同,但语义必须闭合、不留新拍板空间);②对修订稿本身再做一轮无前提攻击,重点 = 修订引入的新机制(容差配对轨迹继承边角 / live 接线规约可实现性 / 种子与恢复登记完整性 / landing 判据可验收性)。审查对象 = 本目录修订后全部文档;对照 = src 与 sr-od-test 现行代码。规范 = docs/develop/harness/iteration-design.md §5/§7。

## ① 结论

**有条件通过**。第一轮打回的头号问题 P1(矿身份键跨帧稳定性)已修成「容差配对轨迹继承」,结构与用户裁定兼容(席位生成期定、归属 rng、附着全走随机态),M2-M6/N1-N6 全部落实且依据核对为真;但 **M1 的修复文本自身留下三处未闭合**(ore-reward-channel §5 接线规约一句自相矛盾 + `_prev_node_plane` 消费点未定义 + 事件② plane 取值源未定)——照「实现者照此开工,不留拍板空间」的自我承诺,3.4 仍不可派工;另有 4 条备注级新发现。**条件 = R2-M1 三处闭合后放行 3.4;R2-N1/N2 措辞随同批修订;3.1/3.2/3.3 可立即开工。**

## ② 修复核验表(第一轮 13 条)

| 条目 | 判定 | 证据(修订稿 ↔ 代码) |
|---|---|---|
| P1 身份键稳定性 | **已修** | 总纲 §2 契约改「矿身份 = 轨迹,不是精确坐标」:附着键 = 最新观察坐标,连续性由挂接入口容差配对继承判定(消失↔新现 ≤`_SPHERE_PERSIST_POS_TOL` 一一配对 = 同身份,继承附着不重掷),并如实改写依据(两帧持存 = 防幻检容差过滤器,非坐标稳定器);channel §4 步序 3 给全配对语义(贪心最近、rekey evidence=`ore_gen_rekey#p{plane}`、值不变不重掷、跨面板别名披露);landing 3.1 判据含「坐标漂移 ≤12px 连续两帧 → 声明附着仍在且 roll 调用计数为零」。核:tol=12 单一源(cw_identity_obs.py :1434)+「从 cw_identity_obs 导入,禁复制数值」;spheres observe 写端恰两处(cw_screen_prep.py :384-391 / cw_sim_backend.py :1468-1473);kernel 引 obs 常量有先例(cw_encounter_selection.py :39 惰性 import,无环)。声明金保全语义闭合 |
| M1 live 接线机制 | **部分修**(残留 → R2-M1) | 四问已答三:(a) 前值载体 = `_prev_node_plane`/`_prev_env` op 成员帧首快照(照 `_prev_spheres_raw` 先例,先例实存 cw_screen_prep.py :200-203);(c) hook_sig 形态 = logic_hook 族、group_id=`'prep:ore-channel'`、actor=`CwScreenPrep`(ChannelSig.group_id 字段实存 cw_game_state.py :401;类名实存 :146;group_id 为自由串无格式校验,可构造);(d) 事件②措辞已改「active_env 现值空→非空的备战帧边沿 + 注明 gain_invest_env 动作落地链逻辑写来源」(函数实存 cw_gain_chain.py :457,引用准确)。未闭合:(b) 次序硬约束句与判定点句**字面互斥** + `_prev_node_plane` 消费点未定义 + 事件② plane 取值源未写 → 见 R2-M1 |
| M2 过期清理无落地阶段 | **已修** | landing 3.3 范围含「+ 位面过渡过期清理接线」、判据含「过期清理留痕」;3.4 范围含「+ 位面过渡过期清理接线」、判据含「位面过渡清理旧 plane 条目留痕」;sim §1 明确「与入队同一改动点交付,归本阶段」。两端(尤其 live)文件面与判据面均承载 |
| M3 「§12」悬空指针 | **已修** | landing 首节建「通用工程门」单一定义(ruff/受影响测试全量/测试仓同步/逐文件 add+stat 复核,门源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节);四阶段改「通用工程门(本文首节)」(:22/:35/:47/:61),无悬空引用 |
| M4 依据失实簇(4 条) | **已修** | ①`_open_node_window` → `_begin_node_window`(sim §1 标题与正文,与 cw_sim_backend.py :1332 一致);②10 处 → **7 处**且行号逐一精确(click-consume §4;grep 实测恰 7 处 :160/:186/:212/:237/:254/:280/:308);③「在册」矛盾 → design §1「**新增**披露键 `ore_plane_start_pending` 落 3.3」与 sim §5「本迭代新增非在册」双向一致;④正本锚 → landing 清单改「invest_effects.md §1 批 2「时点日程」新增增发货币条目(位面开局声明矿流程模型,呈现面首遇待验)」——锚实存(invest_effects.md :36「### 批 2 时点日程」),动作可执行 |
| M5 新域工程面 | **已修** | channel §1「工程面三件」:种子底座(两域入 `_seed` 族,`{}`/`()`,机制吻合 cw_game_state.py :1983-2018,`pending_item_grants`/`active_env` 种子先例实存 :2012-2014);快照恢复登记(`ore_rewards` rebuild → `OreReward(**v)`、`ore_declared_pending` → tuple-of-tuple,与 restore_state_snapshot 恢复表机制吻合 :3878-3898;OreReward 全字段带默认值,`**v` 重建成立);None 起点合并(§4 步序 4「None 起点从 {} 起」)。补核:快照枚举按 `dataclasses.fields` 自动遍历(:2687),新域自动进快照,无需另登记快照面——实现面自动成立 |
| M6 sim 合并批坐标 | **已修** | sim §2「坐标 = 面板序续接:声明矿点 = `(10*(N+1), 10)`,位面首节点为奖励节点时同批 8 面板矿 + 声明矿 = 第 9 点 (90,10),**禁独立从 1 起号**——同批撞键会被 `by_xy` 求交去重吞点」;关键取舍补「独立号段在面板矿数变化时仍可能撞键,续接不撞」;landing 3.3 判据「坐标无撞键」。核:reward_ore_points 8 点 i 从 1 起 `(i*10, 10)`(:553-559),公式正确;by_xy 字典键去重(collect_ore.py :95)引用无误 |
| N1 状态失同步 | **已修** | design §0「状态:对抗审中」= README「迭代设计:对抗审中」 |
| N2 措辞强于机制 | **已修** | click-consume §2「防线是**双层的**,不是机械强制」(①随机态域不可信侧口径 = 纪律面;②文档契约);总纲 §2 第 6 条同步改口径 |
| N3 先例引用 | **部分修**(残留 → R2-N2) | 补了通道归属论证「不属容器逻辑写端 anchor_aware 族:该域无观察写端可锚定」(论证成立);但替换后的先例「pending_item_grants 种子族」仍非「直写 write_logic」先例——见 R2-N2 |
| N4 跳过证据通道 | **已修** | click-consume §1 定 `LogicOutcome.reason='ore_reward_attach_missing_level'`,关键取舍补「机械可断言、测试面最小;弃日志/台账(不可断言)」。核:LogicOutcome.reason 通道实存且为现行为出参形态(collect_ore.py :86/:104/:214/:216) |
| N5 跨面板别名 | **已修** | channel §4 步序 3「跨面板别名披露」:sim 经济中性 / live 自愈于观察收口 / 极端角(现役身份全为别名残留)声明条目饿死至过期清理,接受并披露 |
| N6 level 概率高估 | **已修** | channel §4 步序 4「种子恒写 level=3,生产近乎不可达,此为保真防御」;click-consume §1「语义收窄是保真不是主防御面」 |

## ③ 新发现清单

### R2-M1【整改】live 接线规约(ore-reward-channel §5)自相矛盾 + 两处未闭合——3.4 仍不可派工

- **问题(三件)**:
  (a) **次序硬约束句与判定点句字面互斥**。「事件①位面进入:判定点 = 节点锚定写(`observe_node_anchor`)**之前**——锚定前 `gs.node.value` 仍是旧 plane,入口 `ore_declared_on_node_observing(gs, incoming_plane, sig)` 比较 incoming vs 现值即可边沿检测,**锚定后已失前值**」;紧接着「**次序硬约束 = 事件判定与入队必须夹在锚定写与 spheres 写之间**(现观察序锚定写在前,spheres 写在后,天然满足…)」。「夹在锚定写与 spheres 写之间」= 锚定写**之后**;而给出的判定机制(incoming vs 现值)只在锚定写**之前**成立——照次序句接线,锚定后 incoming 与现值恒等(均为新 plane),位面 2/3 的过渡边沿**永不触发**,声明永不入队,恰是 M1 要防的承载性错误(位面首帧新现生成时声明不在队,该帧后无新现则永不附着)。总纲 §2 第 3 条的表述(「在节点锚定写前读 plane 前值检测——入队必须先于同帧 spheres 写」)是自洽的正确版;详设接线规约作为「实现者照此开工」的操作文本,两句必须对齐。
  (b) **`_prev_node_plane` 消费点未定义**。前值载体段定义了 `_prev_node_plane` 与 `_prev_env` 两个成员,但事件①机制用 incoming vs 锚定前现值(不需要快照)、事件②只用 `_prev_env`——`_prev_node_plane` 成了无用途成员;或作者本意是「锚定后用帧首快照对拍」的另一机制(那 `ore_declared_on_node_observing(gs, incoming_plane, sig)` 的比较对象就应改为快照,签名语义不同)。两种机制各写了一半,实现者必须自行裁决 = 拍板空间(硬规则 2)。
  (c) **事件②入队的 plane 取值源未写**。条件行「`env ∈ ENV_ORE_GRANTS` ∧ 该 (env, plane) 无在队条目」——事件①的 plane = incoming_plane(明确),事件②的 plane 从哪读未写;且 node 域**不在开局种子表**(cw_game_state.py :1987-2018 无 `_seed(gs.node, …)`),首锚定前 `gs.node.value = None`,None 时事件②的行为(跳过,由事件①在下一次锚定兜住 / 报错)未定。
- **证据**:ore-reward-channel §5 原文(前值载体/事件①/条件行三段);cw_screen_prep.py :281-288(锚定写)先于 :384-391(spheres 写,「天然满足」的物理基础核对属实);cw_game_state.py :1987-2018(种子表无 node);cw_screen_prep.py :194-195(`_prev_spheres_raw` 先例注释:**CwScreenPrep 每备战环重建 → 成员跨环不残留,语义 = 环内连续帧**——事件②跨环重触发由幂等守卫吸收,机制成立但值得写明,防实现者误以为跨环快照)。
- **建议修法**:§5 次序句改为「事件①判定 = 锚定写**之前**(incoming_plane vs 锚定前现值),入队完成先于同帧 spheres 写」;删除 `_prev_node_plane` 或指明其机制(若保留锚定后判定,须同步改 `ore_declared_on_node_observing` 的比较对象);事件②补「plane = 锚定现值 plane,`gs.node.value` None → 本帧不触发(由事件①在下一次锚定兜住)」;补一句 `_prev_*` 环内生命周期与幂等守卫的配合。均为段落级修订,不动结构。

### R2-N1【备注】「level None → 本帧不生成,下帧再试」与配对机制自相矛盾——attachmentless 身份永久缺附着,打破自己声明的缺项不变量

- **问题**:channel §4 步序 4「`level = gs.level.value`;None → 本帧不生成(…下帧再试…)」。但步序 2 已把本帧观察写入 spheres(身份已存在),下帧步序 3 配对命中 = **同身份非新现** → 永不进生成池,「下帧再试」不成立:该批身份永久无附着。这与 click-consume §1 的缺项定义直接冲突——「缺项(不变量破坏:**挂接入口保证每现役身份有附着**;写端竞态等罕见态)」——不变量被本设计自己的防御路径系统性打破(非竞态)。生产近乎不可达(种子恒 level=3),点击侧 `ore_reward_attach_missing` 兜底接管不丢功能;但论证与机制不符,且直构测试域可达。
- **证据**:channel §4 步序 2/3/4 次序;click-consume §1 缺项定义;cw_game_state.py :2003(`_seed(gs.level, 3)`)。
- **建议修法(二选一)**:①生成资格 = 「无附着的现役身份」而非「未配对新现」——配对继承只对有附着的旧身份生效,无附着旧身份并入生成池(语义更干净,同时覆盖恢复/竞态形态);②删「下帧再试」,如实写「该批身份转永久缺项,由点击侧兜底接管」。

### R2-N2【备注】N3 修复的先例引用仍失实:pending_item_grants 并非「直写 write_logic」先例

- **问题**:channel §4 步序 4 声明消费写引「依据 = 无观察写端的卡文推算域直写 logic 先例(`pending_item_grants` 种子族)」。「种子族」三字只支撑种子底座选型;作为**写通道**先例不成立——`pending_item_grants` 的入队写与放出写全部经 `_select_write` → `anchor_aware_write`(cw_gain_chain.py :746-753 / :789-790),恰是设计声明「不属」的那一族。kernel 直写 write_logic 的真先例 = cw_exec_state.py :71(金腿)、cw_effect_inventory.py :864/:1231(退款/宝箱腿)等确定效果直写。决策本身已闭合(「无观察写端可锚定,声明 = 登记事实非观察投影」论证成立,直写通道可用),只须换引用,否则第一轮 M4 式「依据失实」在同一位置复发。
- **建议修法**:引用改为「kernel 确定效果直写 write_logic 先例(cw_exec_state 金腿 / cw_effect_inventory 退款腿)」,保留「不属 anchor_aware 族」论证。

### R2-N3【备注】12px 容差 × 多矿面板的误配几何最坏角未量化——可达但已披露,建议补定量

- **问题**:`find_ore_sights` 的 HoughCircles `minDist=35`(cw_identity_obs.py :1561)⇒ 同帧两矿圆心最小间距 35px;跨帧各抖 ±12px 时,异矿间距最窄 35 − 12 − 12 = **11px ≤ 12px**,交叉配对几何可达。贪心最近通常救回(真对距离 = 抖差,通常远小于交叉对 ≥11px 的下界),误配后果已被 §4 步序 3 披露(附着是随机态猜测,配对误差不引入系统偏差;经济差由观察收口)。sim 侧「合成坐标恒稳无歧义」经核成立(同键续存/换批均唯一配对)。建议在披露句补一句 minDist=35 vs 2×tol=24 的量化边界,把「歧义可达」从定性变定量,便于采集校准期复核。
- **建议修法**:§4 步序 3 披露句补「误配几何可达域:minDist=35 − 2×12 = 11px ≤ tol;贪心最近在真对距离 < 交叉对距离时选真对,抖差常态 ≪ 11px」。

### R2-N4【备注】杂项小库(各一句话,随批或实现批顺带)

- (a) **配对距离度量未定**:filter_persistent_ores 先例 = 双轴独立 ≤tol(Chebyshev,:1479-1480);§4「距离 ≤ tol + 贪心最近」需要标量距离参与排序——宜定死欧氏或 Chebyshev,否则又一处实现者拍板。
- (b) **hook_sig 族两端不一致**:live = logic_hook 族,sim hook_sig = `logic_sig()` = **logic_action** 族(cw_sim_base.py :37-40)。两者都过 `_validate_sig` 机械无碍,但参数名「hook_sig」下的族两端不同,措辞宜统一或注明。
- (c) **sim §1 声明入队写自身的 sig 未点名**:§3 只定了挂接入口的 hook_sig;入队在 `_begin_node_window` 分道处,建议点名(如 `logic_sig('sim:env')` 与 discharge 同组,或独立组)。
- (d) **sim §4「装配方增键 'ore_reward_gen'」实际无事可做**:装配方是泛型 `lambda tool`(:1627-1629),键随首个调用自动生效,装配点无键表可增;工作面只在 seam 测试断言面(§4 第二条,test_cw_sim_seam.py :208-219 断言面实存可扩)。第一条按字面执行会找不到可改点,宜改述为「键随 action_sampling_rng('ore_reward_gen', None) 首调自动生效,装配方零改动,断言面扩键」。
- (e) **landing 3.3 判据「数值 = 6/8/12」中 12 在 sim 不可达**:sim 第一期辖域 P1+P2(`_node_ordinal` 对 plane>2 raise,cw_sim_backend.py :1322-1330),位面 3 声明(12 金)在 sim 永不触发;判据宜写「6/8(sim 辖域内实测),12 由生成函数单测覆盖」。
- (f) **landing 3.4 文件面「sr-od-test/ 对应 prep 观察测试」未点名文件**(其他阶段均点名到文件;仓内无 test_cw_screen_prep*.py,候选 = test_cw_prep_node_row_housekeeping.py / test_cw_obs_arch_* 族)——硬规则 4 文件面真实路径口径,宜点名。
- (g) **click-consume §1 出参 reason 枚举漏 'no_intersection'**(collect_ore.py :104 现行为,求交不动则保留);「其余…不变」清单不全,'level_unread' 的退役已写明而 'no_intersection' 未提。

## ④ 依据核验表(第二轮新核/复核)

| # | 设计依据(出处) | 代码实况 | 判定 |
|---|---|---|---|
| 1 | tol=12 常量单一源 + 禁复制数值(channel §4) | cw_identity_obs.py :1434;kernel 引 obs 常量先例 = cw_encounter_selection.py :39(惰性,无环) | 属实 |
| 2 | 锚定写在 spheres 写之前、天然满足承载次序(channel §5) | cw_screen_prep.py :281-288 → :384-391 | 属实 |
| 3 | `_prev_spheres_raw` 先例 = op 成员帧间快照(channel §5) | :200-203;生命周期 = 环内(:194-195 注释) | 属实(生命周期语义见 R2-M1 附注) |
| 4 | 两域入种子族 `{}`/`()`,先例 pending_item_grants/active_env(channel §1) | cw_game_state.py :1983-2018(:2012-2014 两先例实存);**node 域不在种子表** | 属实(事件② plane 源缺口 → R2-M1c) |
| 5 | 快照恢复登记 rebuild λ(channel §1) | restore_state_snapshot 恢复表 = 字段名 rebuild(:3878-3898);快照按 dataclasses.fields 自动枚举(:2687)新域自动入 | 属实 |
| 6 | OreReward(**v) 重建可行(channel §1) | cw_ore_reward.py :52-62 全字段带默认值 | 属实 |
| 7 | pending_item_grants = 直写 logic 先例(channel §4) | 入队/放出全经 _select_write→anchor_aware_write(cw_gain_chain.py :746-753/:789-790) | **不属实** → R2-N2 |
| 8 | 测试迁移面 7 处 monkeypatch 行号(click-consume §4) | grep 实测恰 7 处 :160/:186/:212/:237/:254/:280/:308 | 属实 |
| 9 | invest_effects.md §1 批 2「时点日程」锚(landing 清单) | :36「### 批 2 时点日程」实存;§5「API 裁定」锚实存(:86) | 属实 |
| 10 | ENV_ECONOMY 增发货币 (6,8,12) + 校验族 + ∅ 检查语义(channel §2/§约束) | cw_investments.py :1176 / :1200 / :1311(:1349-1352) | 属实 |
| 11 | reward_ore_points 8 点 i*10、续接公式 (10*(N+1),10)(sim §2) | cw_sim_backend.py :543-559 | 属实 |
| 12 | 窗口幂等守卫沿用 `_window_begun_ord`(sim §1) | :1332-1344,位面过渡点空白与直进节点共用、重放不双发 | 属实 |
| 13 | sim 装配方增键 'ore_reward_gen'(sim §4) | 装配方 = 泛型 lambda tool(:1627-1629),无键表可增;seam 断言面实存(test_cw_sim_seam.py :208-219) | **表述失实(工作面错位)** → R2-N4d |
| 14 | 3.3 判据「数值 = 6/8/12」 | sim 辖域 P1+P2,plane 3 raise(:1322-1330),12 不可达 | **判据不可全验** → R2-N4e |
| 15 | sim「容差配对恒等、继承零触发」(sim §3) | 合成坐标确定性:同键续存/换批唯一配对,rekey(键变更)确不发生 | 属实 |
| 16 | hook_sig:live logic_hook 族 / sim logic_sig('sim:ores')(channel §5、sim §3) | ChannelSig.group_id 实存(:401);logic_sig = logic_action 族(cw_sim_base.py :37-40),两者均过 _validate_sig | 属实(族两端不一致 → R2-N4b) |
| 17 | 事件② = gain_invest_env 逻辑写、无观察时点(channel §5) | cw_gain_chain.py :457-496(经 _select_write) | 属实 |
| 18 | 投影审计两锚:gold 行「collect_ore 采样直写…」/ spheres 行「零逻辑写端」(click-consume §3) | cw_projection_audit.py :105-108 / :230-232 | 属实 |
| 19 | LogicOutcome.reason 为跳过证据通道(click-consume §1) | collect_ore.py :86/:104/:214/:216 现行为 | 属实 |
| 20 | 出参 reason 集「其余…不变」(click-consume §1) | 现集另含 'no_intersection'(:104)未列 | **枚举不全** → R2-N4g |
| 21 | 正本四锚:fields.md / gain-chain.md / sim-wiring.md / invest_effects.md(landing 清单) | 四文件全实存 | 属实 |
| 22 | 测试五件实存(landing 各阶段) | test_cw_collect_ore_rand / test_cw_ore_container / test_cw_unified_action_2a / test_cw_sim_backend / test_cw_sim_seam 全实存 | 属实 |
| 23 | 契约注落点 select_ore_clicks + 模块头(landing 3.4) | cw_prep_actions.py :47 | 属实 |
| 24 | 3.4 文件面「对应 prep 观察测试」 | 仓内无 test_cw_screen_prep*.py,未点名 | **文件面未点名** → R2-N4f |
| 25 | 12px 误配披露「sim 恒稳无歧义 / live 歧义无偏」(channel §4) | minDist=35 − 2×12 = 11px ≤ tol,交叉配对几何可达;贪心最近常态救回 | 属实(定量边界缺失 → R2-N3) |

## ⑤ 实现者试读

- **3.1(kernel 面):可开工**。域定义、种子与恢复登记、注册表三条校验、生成函数语义、挂接入口步序(含容差配对与 rekey)、入队/过期函数语义唯一可答。R2-N1 影响 §4 步序 4 的一句措辞与对应测试期望(建议随批定夺:生成资格改为「无附着现役身份」或如实写永久缺项),不阻塞开工。
- **3.2(点击兑现):可开工**。命中零掷、缺项兜底前缀、detach 写序、level 收窄、reason 通道语义完整;7 处迁移面与行号核对无误;既有 evidence 断言面清楚。
- **3.3(sim 接线):可开工**。分道、开局矿呈现、坐标续接、写端统一、占位退役、披露键全落到符号级;R2-N4 的 (d)(e) 两小点(装配方无键可增、12 不可达)是判据/表述级修正,不阻塞。
- **3.4(live 挂接):不可开工**——R2-M1 阻塞(与第一轮同判):接线规约自相矛盾的次序句、无消费点的 `_prev_node_plane`、无取值源的事件② plane,每一处都是实现者必须拍的板。修完 §5 三处(一段级修订)即可放行。
- 总评:P1 修复(轨迹继承 + 单一入口 + 双事件入队)结构成立,与五条用户裁定逐一兼容(观察含奖励→点击只兑现 = 附着生成前置;生成函数单一入口 live/sim 共用;固定矿生成期占席、归属 rng;附着全走 write_logic_rand;策略禁读双层防线)。本轮无 P 级发现,最重为 M 级接线规约残留。

## 附:核三(治本)评语

R2-M1 与 R2-N1 同属一类:**修复文本自身引入的半成品语义**——M1 修复把两种边沿检测机制(锚定前 incoming-vs-现值 / 锚定后快照对拍)各写了一半,N1 修复的「下帧再试」没有对着新配对机制推演到底。两处都是硬规则 4「修订后全量同步复查」应拦下的残留(修订触发的全量反查没有覆盖修订自身引入的交互),而非新架构问题——治本方向(内容时点前移 + 轨迹继承身份 + 单一入口)两轮一致成立。「§12」悬空在规范侧的架构根(模板行)仍未见修(R5-1 诉求),本批靠 landing 首节定义绕开,再次提请框架负责人修 iteration-design.md 模板。
