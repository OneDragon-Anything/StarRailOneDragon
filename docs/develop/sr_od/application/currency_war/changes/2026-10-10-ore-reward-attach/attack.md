# 晶矿奖励附着通道 · 设计对抗审查报告(第六轮·定点复审)

> 复审范围 = 第五轮 N1 修复(入队机制升级为**电平触发单一规则 + done 消费标记**)+ N2-N5 整改核验 + 本轮触碰段交互(§1 域三件 / §4 消费行 / §5 全节 / 取舍段 / design §2-1 / §2-3 / sim §1 / landing 3.1 / 3.4 / 清单)。核验基准 = 第五轮报告(本文件上一版,结论已归档至 git 历史)。本轮核心 = 电平机制逐场景推演到底,全部代码证据亲核。

## ① 结论

**通过-定稿(四处半句级顺手改,零阻塞)**——N1 的电平修法把发放记忆从 op 生命周期整体迁入 gs 域(pending+done 双守卫),第五轮形态 B(跨环成员失忆 → 同位面重发 18 金)的失败前提被**结构性拆除**:机制里没有 op 成员、没有边沿、没有前值载体,两种互斥读法随之消失,文本无分岔。本轮推演电池(S1-S11,见 ②)全场景闭合:18 vs 6 三环推演闭合、恢复局两形态闭合、位面过渡清理与入队同帧无互吞、light 帧无缝隙、自动开启现实零污染。N3/N4 落实;N2 半落实(先例改述到位,「模块级环」措辞残留);N5 的结构性吸收成立但**归因失实**(live 接管的零多发靠 active_env 空腿,非 done 腿)。新发现 F1-F4 全部为文字面半句级/备注(域传导缺口 ×2、归因分腿披露、边界披露、措辞残留),无机制分岔、无实现走样风险,随修订顺手带上即可,不必再开定点复审。

## ② 电平机制推演记录(逐场景,代码证据亲核)

### 代码事实底座(本轮全部重核)

| 设计断言 | 代码实况 | 判定 |
|---|---|---|
| 判定点时序:observe_full 回执后、spheres 写前 | cw_screen_prep.py `_observe` heavy 段:observe_full :240 → 锚定 :281-288 → spheres 写 :384-391 | ✅ |
| plane 源 = 回执后 `gs.node.value.plane`(写点在 observe_full 内漏斗) | cw_observe_full.py :123/:140(gold 重读,重写均在回执前)调 read_game_state;cw_observation.py :2596-2599(node_type 直写)与 :2601-2607(kind 继承写)都写 `gs.observe(gs.node, NodeKey(plane=…))` | ✅ |
| `observe_node_anchor` 锚序号、不更新 plane | cw_game_state.py :3501-3545:只写 `node_ord`(advance 分支经 advance_node_effective / reanchor :3538 `_swap('node_ord')`),全路径不触 `gs.node`;R<v 倒退免疫 :3514-3516(**仅护 node_ord,node 域无同款**——见 S10) | ✅ |
| op 每备战环重建;电平无成员可失忆 | cw_loop.py :1735-1737 每次备战分发 `CwScreenPrep(self.ctx)`;守卫状态(pending/done)住 gs(:271 `gs_of_ctx(session)`,session 级跨环连续) | ✅ |
| node 域不在开局种子表(None 起点) | cw_game_state.py :1988-2018 种子清单无 `gs.node`;`active_env` :2012('')/`pending_item_grants` :2014 种子族先例属实 | ✅ |
| 入队/过期/消费 sig = logic_hook 族过 write_logic 校验 | cw_game_state.py :3012(write_logic `_validate_sig(sig, ('logic_action','logic_hook'))`);:337 CHANNEL_FAMILIES | ✅ |
| 快照/恢复机制(工程面三件的载体) | full_state_snapshot :2680-2722(非 None 值经 `_json_safe` 入 values);restore_state_snapshot :3803-3898(rebuild 表 :3878-3885 按字段名,**未登记域原样 setattr** :3892-3896 → tuple 变 list 类型漂移属实);**生产调用方 = 仅 sim/cw_replay.py :118(离线判读面)** | ✅(并引出 S3/F2) |
| sim 接线点 | cw_sim_backend.py `_begin_node_window` :1332(窗口幂等 `_window_begun_ord` :1342-1344)→ `_apply_env_plane_gold` :1357 → 呈现 :1394;`_present_node_screen` reward 分支 spheres 直写 :1468(待改过入口);`reward_ore_points` :553-559 点列 (color, i*10, 10, 10) i 从 1 起;**普通 battle 备战现行为不写 spheres**(:1477-1478 只置屏,设计改空读照写过入口 = 清理腿,自洽) | ✅ |
| live spheres 观察 gs 写端唯一 | 全仓 grep:观察写仅 cw_screen_prep.py :385;collect_ore.py :132 为随机态摘除写(动作侧,非观察);sim :1468 | ✅ |

### S1. R5 的 18金 vs 6金场景(三环同位面、每环 op 重建、消费后重查)——**闭合 ✅**

以增发货币 × P1 真值序列(reward, reward, battle, battle, supply, battle, encounter, reward, boss;cw_node_schedule.py :28-31,42 局零反例)逐环推演:

- 环 1(节点 1 reward)首 heavy 帧:env='增发货币' ∈ ENV_ORE_GRANTS,(env,1) ∉ pending ∉ done(皆空)→ 入队 (env,1,6)(write_logic);同帧 spheres 写经挂接入口:面板矿皆无附着 → 生成集非空 → 出队 + done 追加 (env,1) + 生成(声明 6 归属 rng 掷)。**真值 6 金,一次。**
- 环 2(节点 2 reward):op 重建,首 heavy 帧电平重查:(env,1) ∈ done → 不入队;节点 2 面板矿全随机 ✅(游戏真值:位面开局声明与奖励节点无关)。
- 环 3-7(battle/supply/encounter):同上,done 拦;环 8(reward)亦不重发。
- **plane 1 合计 6 金 = 真值。** 形态 B 的失败前提(成员记忆随 op 重建复位、消费即移除销毁守卫前提)在电平下不存在:守卫状态住 gs,op 重建不触及;环内后续 heavy 帧(reobserve_in_visit :516,同为 heavy)重查同样被 done 拦。sim 侧窗口起点经同一电平函数,双守卫同判 → live/sim 同发,第五轮的 live/sim 分歧形态根除。

### S2. 恢复局(快照含 done)不重发——**闭合 ✅(辖域 = 离线/回放恢复面)**

full_state_snapshot 存非 None 值(种子底座保三域恒非 None)→ restore_state_snapshot 经 rebuild 表按字段名重建(tuple-of-tuple);恢复后的 gs 里 (env,plane) ∈ done → 电平不重入队。登记缺失则 tuple 域恢复成 list-of-lists(`(env,plane)` 元组对 list 元员恒不等 → 双守卫第二腿静默失效),故工程面三件的恢复登记**是功能件不只是判读面件**,landing 3.1 :21 的类型断言判据正确锁住。注意:该路径的生产消费方 = sim 回放(cw_replay.py :118),见 S3。

### S3. live 接管残局——**零多发 ✅,但闭合腿与文档叙述不同(F2)**

live 无生产快照恢复路径(restore_state_snapshot 仅离线);live「恢复局」= 接管残局 = establish_new_match 冷建新 gs(active_env 种子 '',cw_game_state.py :2012;接管确认点 `_invalidate_tracked_on_takeover` cw_loop.py :819-851 只写 tracked_account_observed=False,不重建 gs,但 session 本身就是新的)。电平第一腿 `env ∈ ENV_ORE_GRANTS` 对 ''恒不满足 → **接管局零入队、零多发**——R5 N5 的「多发一条」场景在新机制下不可达(其前提「active_env 已定」在接管局不成立:env 写端唯一 = 本体选环境动作落地链 gain_invest_env,中局接管永不经过)。代价 = 接管段声明不建模(该矿按随机采样,欠发/错发一条,随机态域,有界)——此边界未披露,且 design §2-3「跨环/恢复局/晚选环境由 pending+done 双守卫闭合」把接管局闭合归因于 done 腿(接管局 pending+done 皆空),归因失实 → F2。

### S4. 位面过渡电平清理时序(清理与入队同帧新位面)——**无互吞 ✅**

过渡帧(回执写 gs.node plane=2):清理删 pending/done 中 plane≠2 条目(即 (env,1) 全族);入队检查 (env,2) ∉ pending ∉ done → 入队 (env,2,8);随后 spheres 写生成含声明 8。清理与入队**先序后序均无互吞**:清理只删 plane≠当前,新入队条目 plane=当前,两个次序下都存活;旧位面条目(含 done 记忆)按「位面推进单调」前提该删且只删一次。过渡前多帧 plane=None(战斗/过渡屏无备战 heavy 帧)不检查不清理,pending/done 原样——清理在下一有效 plane 帧补做,语义不变。

### S5. light 帧节律——**无缝隙 ✅(任务专项,推到底)**

- 现行为核验:`_observe` 的 spheres **gs 写端只在 heavy 段**(:384-391,位于 `if heavy:` 块 :233-:422 内);light 段的 `_sph_list`(:199-203 现读 + 两帧持存过滤)只进 PrepObservation 局部/op 成员,**不落 gs**——「light 帧 = 空读照写还是跳写」的答案:两者皆非,**light 帧对 gs.spheres 零写**(跳写)。且当前全部 `_observe` 调用点均 heavy=True(:516 reobserve_in_visit / :660 观察 node),light 路径是防御性预留。
- 缝隙判定:矿身份进 gs 只有一条路 = heavy 帧的 :384 写 → 挂接入口只可能被 heavy 路径调用;而电平检查点与该写同帧且先行(入队先于 spheres 写)→ **新现身份首次生成时,声明必已在本帧检查点入队**(同帧入队 → 同帧 spheres 写生成时出队消费)。矿首现于 light 帧也不破链:两帧持存过滤器要求连续两帧命中(`filter_persistent_ores`,_prev_spheres_raw 每次调用都更新 :203),身份进 gs 最早在下一 heavy 帧——电平检查再获一帧宽限。**无「新现生成时声明未入队」缝隙。**
- sim 侧对应:入队(窗口起点 :1357)先于呈现/spheres 写(:1394);普通 battle 备战改空读照写过入口(设计新增清理腿)时,其入队同样已在窗口起点完成——两端次序硬约束均成立。

### S6. plane=None 帧(首锚定前/漏斗失读)——**闭合,带自愈角落 ✅**

None → 本帧不检查不清理,pending/done 不受影响;下一 heavy 帧兜住。「兜住」的完整语义:若该 None 帧恰有新矿生成(pending 空 → 整批随机建模),声明条目在下一有效帧入队后**留至下一新矿批消费**(生成集 = 无附着现役身份,不依赖同批)——时序错位自愈,总值守恒;最坏角落 = HUD 位面失读而矿面板可读且连续两帧(持存过滤器再加一帧门槛),影响 = 一批建模时点错位,随机态域,接受。

### S7. 晚选环境——**电平闭合 ✅**

env 未定('')→ 第一腿不满足,零入队;env 落定(动作落地链写 gs.active_env)后首个 heavy 帧入队。发放登记的幂等闭合成立;游戏侧「选定时点 vs 位面开始」的发放时点属未实采面(disclosure 键 `ore_plane_start_pending` 辖域),非本通道可判。

### S8. 自动开启现实(矿永不出现)——**零污染 ✅**

pending 条目永不出队 → 位面过渡电平清理删除即终态;金经游戏自动开启入账,bot 侧 gold 由观察收口。「对两种现实都稳健」的机制面叙述与推演一致。

### S9. 写序与 sig——**成立 ✅**

live 现序 observe_full(:240)→…→ spheres(:384)天然满足「检查点后、写前」;入队/过期/消费三写 = write_logic(logic_hook 族过 :3012 校验,group_id='prep:ore-channel');sim 挂接写 = logic_sig('sim:ores')、入队/过期 = logic_sig('sim:env')(sim §1,与 §5 sig 段两不冲突:§5 只定 live 三写与 sim 挂接写)。

### S10. plane 读数正向误读抖动——**位面内至多重发一条(F3,备注)**

node 漏斗直写无倒退免疫(cw_observation.py :2596/:2603;node_ord 有 stale_dropped :3514-3516,node 域无同款):p2 误读 p1 一帧 → 清 (env,2) done + 入队 (env,1);次帧回 p2 → 清 (env,1) + **重入队 (env,2)**(其 done 已被清)→ 该位面下一批新矿再消费一次声明 → 至多多 +8 金世界真值误差。前置 = HUD 位面数字正向误读(低概率,anchor 的 stale_dropped 存在本身证明误读是已认知现实);边沿形态(第五轮形态 A)同病,非电平新引入,但电平把 done 清理做成主动销毁腿,值得半句披露 → F3。

### S11. 三方同步一致性(design §2 第 3 条 / channel §5 / landing 3.4)——**一致 ✅(F2 归因半句除外)**

电平规则、判定点位置、次序硬约束、无 op 成员/无边沿、done 双守卫、sig 形态四方(design §2-3 / channel §5 / landing 3.1 :12+18 / landing 3.4 :51-60)同口径;landing 3.4 判据已按电平重写——「电平静幂等(done 标记):构造同位面多备战环跨环场景(每环 op 重建,环间声明已被消费),断言仅入队一次、仅兑现一次(6 金真值;守卫失效形态 = 每环重发,对照面 18 金)」**恰好把 R5 N1 指出的测试载体缺口钉死**(第五轮「按同环连续帧构造假绿」的漏洞不复存在——电平下跨环/同环同判,且判据显式点名跨环形态);fake observe_full 须真实写 node 的构造约束保留且仍然必要(检查点读回执后 node)。

## ③ N2-N5 核验

| # | 第五轮要求 | 修订落点与代码核验 | 判定 |
|---|---|---|---|
| N1 | 快照载体一句话定死(帧内现读,三处连带) | 修订**升级为放弃快照/边沿**:channel §5 :87「电平触发单一规则 + 消费标记(无边沿检测、无帧间记忆、无 op 成员)」+ :90 入队条件 + design §2-3 + landing 3.4 判据(跨环形态构造)。载体歧义随机制整体消失,S1 推演闭合 | ✅ 落实(机制升级形态) |
| N2 | 引证改「零先例,本迭代立形态」+「会成环」改「破坏单向分层」 | channel §4 :71:先例改述到位(cw_encounter_selection.py :35-41 实核 = TYPE_CHECKING 块内,运行时零执行;「kernel→obs 运行时导入现无先例…本迭代立此形态」✅);**残留**:同句「以避免模块级环」措辞保留——cw_identity_obs.py :40 模块级导入 kernel/cw_game_state(链 cw_ore_channel→cw_identity_obs→cw_game_state 无回边,**不成环**;实害 = obs→kernel 单向分层被反向边破坏)。修法两半只落了一半 | ⚠ 半句残留(F4) |
| N3 | 清单行按「单行长述」形态改写 + 补 spheres 写端说明 | landing :77「状态面板行的域清单内联描述(表格为单行长述,非逐域一行)——补 ore_rewards / ore_declared_pending / ore_declared_done 三域与 spheres 写端统一挂接入口说明」;正本实核 flow/projection_contract.md :19 = 四列表单行长述,「晶矿域 OreSight.points 载点击坐标」为行尾内嵌——措辞与表形态匹配,Z2 丢失的写端半句回归 | ✅ 落实 |
| N4 | 候选对枚举序 = 旧列序×新列序,平局依字典序 | channel §4 :73「候选对按(旧列序 × 新列序)枚举,距离平局 = 枚举序先者优先,禁随机」——枚举序附着点落定,贪心序完全确定 | ✅ 落实 |
| N5 | 恢复局多发边界披露一句 | **结构性吸收成立**(S3):live 接管零多发——但靠「active_env 接管局恒空 → 电平第一腿不满足」,**不是**文档所述「done 随快照存续」腿(live 无生产快照恢复路径);R5 建议的「多发一条」披露句随事件②机制退役而失效,应替换为「接管段欠发」披露。现文档把接管闭合归因于 pending+done 双守卫(design §2-3 / channel §5 :91 / 取舍段 :100),归因失实 | ⚠ 如实性缺口(F2) |

## ④ 新发现(仅限触碰面)

### F1【整改·半句】新第三域 ore_declared_done 的两处传导缺口

- landing 正本清单 :75(fields.md 行)只列「新域 ore_rewards / ore_declared_pending」,**ore_declared_done 缺席**(同文件 :77 projection_contract 行反而三域齐全)——末阶段照单执行会让正本 fields.md 少一个域行。修法:该行补 `/ ore_declared_done`。
- ore-click-consume §3(:30)审计段只新增 pending 域行(入队/消费/过期三口),**done 域行缺**(其写端 = 消费追加 + 过期清理两口,同族 logic-only 域)——域三件(design §2-1/channel §1)的新增未传导到审计面。修法:§3 补一行 done 域行。两处均为文字面,零行为风险。

### F2【整改·半句】恢复局闭合归因失实:live 接管腿未分 narrate

design §2-3「跨环/恢复局/晚选环境由 pending+done 双守卫闭合」、channel §5 :91「跨恢复局(done 随快照存续)重查不重发」、取舍段 :100 同口径——「done 随快照存续」只覆盖离线/回放恢复面(restore_state_snapshot 生产消费方仅 cw_replay.py :118);live 恢复局 = 接管残局冷建新 gs,pending+done 皆空,零多发靠 active_env 恒空(电平第一腿),且伴随接管段声明不建模的欠发边界(有界,随机态域)。**修法**:三处之一(建议 channel §5 消费标记段)补半句分腿——「恢复局两形态:快照恢复(回放/Δ池离线面)靠 done 随快照存续;live 接管局 active_env 空 → 电平零入队,接管段声明不建模(欠发,随机态域),接受」。

### F3【备注·半句】电平清理依赖 plane 读数单调,误读抖动 = 位面内至多重发一条

S10 推演:node 漏斗直写无倒退免疫,node 域正向误读抖动会清掉当前位面 done 并重入队 → 至多多一条声明(随机态域,≤ 位面声明额)。边沿形态同病(非电平新引入),但电平把 done 清理做成主动销毁腿。**修法**:§5 过期段补半句「清理依赖 plane 读数单调(漏斗直写无倒退免疫);误读抖动最坏影响 = 位面内至多重发一条声明,随机态域,接受」。

### F4【整改·半句】N2 残留:「以避免模块级环」措辞与代码事实不符

cw_identity_obs.py :40 实证 obs→kernel 模块级正向边存在,kernel→obs 模块级导入经该链**不成环**;实害 = 反向边破坏 obs→kernel 单向分层。**修法**:channel §4 :71「以避免模块级环」→「避免在模块级新开 kernel→obs 反向边(破坏 obs→kernel 单向分层)」。

## ⑤ 定稿试读

- **3.1 kernel 声明通道与生成内核**:**能定稿**——三域/工程面三件/电平函数契约/挂接入口与代码底座(种子族/恢复 rebuild 表/sig 校验)全部对得上;landing 3.1 判据含恢复类型断言与电平规则,可执行。
- **3.2 点击兑现**:维持第四轮以来「能开工」判定(本轮触碰面未涉,第五轮已确认)。
- **3.3 sim 接线**:**能定稿**——窗口起点序/分道/过期清理接线/开局矿呈现坐标(面板序续接,`reward_ore_points` :553-559 点列实证)/空读照写清理腿/占位退役,与 cw_sim_backend 现状接线点全部对位;`_window_begun_ord` 降冗余保险后窗口重放不双发(S1 sim 腿)。
- **3.4 live 挂接**:**能定稿**——第五轮打回点(载体形态)已随电平机制整体消除;判据面(次序/跨环单发/过期留痕/恢复不重发)构造形态明确,fake 须真实写 node 约束保留且必要。
- **末阶段正本更新**:清单补 F1 后闭合;invest_effects.md 条目无涉本轮触碰面,维持。
- **修订量与重审**:F1-F4 共四处半句(清单一行、审计一行、归因一句、边界一句、措辞一词),零机制分岔、零实现走样风险——随修订顺手带上,**无需再开定点复审**。

**治本核维持并加强**:电平 + 消费标记把「发放登记」从流程层载体(op 成员/边沿)根治性迁到状态层载体(gs 逻辑域,与 pending_item_grants 同族),R5「语义层归层」判定在本轮触碰面下成立且更彻底。

**规范遵循核**:触碰段依据就地标注密度保持;违例项 = F4(引证动机与代码事实不符的残留)。索引定义注释(plane 坐标系/取值时机)在域三件上到位(channel §1 :24-25)。
