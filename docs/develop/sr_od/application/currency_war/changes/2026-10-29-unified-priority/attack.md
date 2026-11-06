# 攻击报告 · 统一让位优先级（2026-10-29）

> 攻击框架 = 三核并重（核一·无前提为主），规范正本 = `docs/develop/harness/iteration-design.md`。
> 严重度：高 = 依据错误 / 判据不可实现 / 接口契约缺口；中 = 依据缺标注 / 表述可歧义 / 清单错漏；低 = 组织文风 / 计数存疑。
> 核对覆盖声明见文末。所有行号以 2026-10-29 工作区现状为准。

## 一、发现清单

### 高（依据错误 / 判据不可实现 / 接口契约缺口）

**A1 ｜ 高 ｜ 核一·与权威源不符 ｜ design.md §2.2 表「商店买入」行**
- 问题：「买入六序判类（11 号稿 §1，**单卡核心支删除后为五序** + 既有 dominance 段」——被拆的 C1 支不在六序之内，删除后仍为六序。
- 权威源出入：11_shop_decisions.md §1 明文「C1 名单核心卡支位次 = **第 7 邻位**（纯冗余停买判定之后）」，即 C1 在六序之外的邻位；代码同构（shop.py:657「六序 + C1/…」、:1884 C1 候选过滤独立成段）。总纲自己的 §2.6 表也写「六序｜删单卡核心支，其余不动」——§2.2 的「五序」为孤立算术错误，且与同一份总纲内部不一致。
- 修正方向：§2.2 改为「六序不变，删除六序之外的 C1 邻位支 + dominance 段保留」。

**A2 ｜ 高 ｜ 核一·详设与总纲拍板矛盾（判据不可实现）｜ priority-model.md §2 档 4 行 ↔ design.md §2.1 落档边界语义**
- 问题：档 4 谓词「**非档 2/3 成员** ∧ 费用档 == 当前升星目标实费档」——已达标成员（need_star 已满足）不再是档 2/3 成员，按此谓词若其费用档恰等于当前目标费用档，则其冗余副本命中档 4（受保护）；而总纲 §2.1 落档边界【拍板】明文「**有要求已满足的成员副本直接落档 8**——达标成员的冗余副本 = 占位，先让路」。同一边界案，总纲与详设两个答案，实现者无法落码。priority-model 自己的落档边界段（§2 第一条括注「达标成员 need_star ≥ 2 时直接落档 8」）也与本档 4 行自相矛盾。
- 修正方向：档 4 谓词的排除项由「非档 2/3 成员」改为「非阵容成员」（或追加「达标成员副本除外」），与总纲边界拍板对齐。

**A3 ｜ 高 ｜ 核一·判据规格缺口（随机域声明不成立）｜ priority-model.md §3 档 2 行、§4**
- 问题：档 2 档内子键 = ①阵容内优先级序数 ②总星级数（**该名全部副本星数相加**）。两键都是成员级聚合——同一成员的跨星副本（如追 3★ 成员同时持有 1★ 与 2★）在此排序下**完全同序**，末位落到随机尾键。让位时可能随机卖掉 2★ 副本（损失 3 张合成进度）而保留 1★，与档 2「为星级目标服务」的目标直接冲突；并证伪 §4 的声明「随机域 = 手持**等价牌**之间的卖出顺序，无行为语义差异」——跨星副本不是等价牌。现行机制无此回归（燃料件 = 1★ 门、M2b 合成对子保护，均不会先卖高星副本）。档 5 无此问题（未持有两星 ⇒ 全部副本皆 1★，天然等价）。
- 修正方向：档 2 子键补第三键「单卡星级（高者后卖）」，与档 4/6/7/8 的星级键同构；随机域声明随之恢复成立。

**A4 ｜ 高 ｜ 核一·接口契约缺口 ｜ acquisition-and-sell.md §1（总纲 §2.9 接口契约 2 的定死项）**
- 问题：契约签名 `virtual_deployment(frame: MandateFrame, direction: DirectionView)` 中的 **`DirectionView` 全仓不存在、设计中亦无字段定义**——它是新类型，但装什么（锁定线 / k_members / 候选快照 / 上阵窗口信号 / entry_signals？）只字未提。且「内部复用现行 `_deployable`/窗口谓词/配方围栏」的现行实现全部消费 `session`/`gs`（entry.py:391 `_make_windowed_select_up(session, gs)`、:325 `_deploy_window_blocked(session, …)`、session_scope 读口走 `gs`）——(frame, direction) 签名未承载这些输入路径，「零判据改动复用」在契约层面走不通。此外现行板满换阵（emit_swap_redeploy，mandate.py:1447）是**多帧单对发射**（select_swap_plan 出组、每帧发一对、下帧幂等续发），纯函数一次性返回「部署定型在场名集」如何映射该迭代过程（内部跑收敛？只取首对？），设计未答——这是虚拟重算语义的核心选择，属「实现者无需再设计」门槛内的未答题。总纲 §2.9 明言契约签名 = 唯一总纲定死项，恰在此处缺底。
- 修正方向：定义 DirectionView 字段面（至少：锁定线名单 / 候选快照 / 上阵窗口信号 / entry_signals）；写明板满换阵在纯函数内的收敛语义；签名要么改收 `(frame, session, gs)` 明示「虚拟调用需旁路遥测面」，要么列全 DirectionView 的装配清单。

### 中（依据缺标注 / 表述可歧义 / 清单错漏）

**B1 ｜ 中 ｜ 核一·拆除面错位 + 遗漏 ｜ dismantle.md §2 代码面第 3 行**
- 问题：「protection.py/相关调用位：『身份分层单一源』中 registry 核心的并集分支」——**protection.py 无任何 CORE_SINGLE_CARD_REGISTRY 引用**（全仓 grep 证实）。registry 核心并集分支实际在三处，全在 sell_gate.py：:297-299（`_hold_qualification_ok` 的 C1 hold 登记资格面「registry 核心 → core 档恒买无星闸」）、:929（identity_exclusions，已在拆除行内）、:1071（funding_hold_fallback，随 §3 整删覆盖）。其中 **`_hold_qualification_ok` 的 core 档分支没有被任何拆除行覆盖**——它是单卡核心囤积规则的资格面构件，漏拆即 C1 残留。
- 修正方向：删除该行的 protection.py 指向；拆除清单补「sell_gate.py `_hold_qualification_ok` 名字分支与 core 档（:296-308）」。

**B2 ｜ 中 ｜ 核一·退役声明与保留结构冲突 ｜ dismantle.md §3 fuel 行、priority-model.md §6**
- 问题：「后台效果门随旧评估器退役后由序列档 7 自然接管」——`predicates.bench_effect_qualified` 消费位实际 **4 处**：criteria/sell_candidates.py:511（评估器）、criteria/sell.py:182/:295（凑息档序 / 危局阀桶）、**mandate.py:488（fuel_sell_candidates 内部）**。评估器场景重写可带走前三处；但 fuel_sell_candidates 被设计**明示保留**（仅删 exclude_names 装配与 zero_overlap 门），其内部的后台效果门不在任何删除项里——「随旧评估器退役」对它不成立，不补删除项则该门残留。
- 修正方向：dismantle §3 fuel 行补「删除 :488 bench_effect_qualified 检查」；「三消费位」表述同步改为按实际消费位清点。

**B3 ｜ 中 ｜ 核一·键面与判据面不自洽 ｜ dismantle.md §1 遥测键面**
- 问题：删除键清单含 `shop_refresh_blocked_memory_skip`——该键是刷新负结果记忆的**命中跳过计数**（shop.py:2023，对一切 refresh_blocked 命中计数）。设计同节明示记忆机制只删「目标不可买」分支、「金线不足照旧」（shop.py:2085-2089 金线拒仍置 `refresh_blocked`）——记忆还在服役、跳过还会发生，整键删除使金线分支的跳过失去观测。与同清单保留「其余拒因的记忆语义不动」自相矛盾。
- 修正方向：该键保留（或改名收窄语义），仅删 `target_unbuyable` 拒因键。

**B4 ｜ 中 ｜ 核一·文档面清单锚错位 ｜ dismantle.md §1 文档面、§2 文档面**
- 问题：①§1「22/23 号稿中引用三腿的表述」——**22 号稿无任何三腿/目标可买引用**（strategy-docs 全目录 grep，命中者 = 01/11/20/23 号稿）；真正需要同步的 **01_math_framework.md（:84/:86/:147 判据组件行与组件表）与 20_large_balance_must_spend.md（:66）漏登记**。②§2「12 号稿 §4 相关表述」（单卡核心拆除的文档面）——12 号稿 §4 是「未锁定期买面接线」，全文无 C1/单卡核心/registry 内容（grep 证实），指向落空。
- 修正方向：§1 文档面改为「11 号稿 §3、01 号稿判据组件行与组件表、20 号稿刷新行、23 号稿 §1」；§2 的 12 号稿指向删除或改指真实关联节。

**B5 ｜ 中 ｜ 核一·行为声明与拆除面不闭合 ｜ design.md §2.2 免费刷新声明**
- 问题：「免费刷新…不再过『目标可买』检查——**判据 = 升星缺口 + 概率带**（金线本就不适用）」——现行免费分支（shop.py:2025-2047）**只有**目标可买检查，从来没有缺口/概率带判据（那两段在付费支 refresh_warranted 内）；拆除清单与消费点映射都只写「删检查」。删完的免费分支 = 无条件白刷，与声明的新判据（缺口+概率带）不符；而设计没有任何一行指示把 refresh_warranted 残余判据接入免费分支。按声明实现需自行设计接线，按拆除清单实现则违反声明——两头都不满足「实现者无需再设计」。
- 修正方向：§2.2 二选一定案：「免费刷 = 无条件（次数在册即刷）」或「免费刷接 refresh_warranted 残余判据（缺口∧概率带）」，并在 acquisition §6 免费刷新行写明改造内容。

**B6 ｜ 中 ｜ 核一·验证凭据归因键错位 + seed 无锚 ｜ design.md §2.10**
- 问题：①单帧测试「席满帧绯英在店应置换成功（**旧版 target_unbuyable**）」——该帧 = 复盘报告**节点 2-1**（:2359-2392：bench 9 满、绯英 2 金在售、绯英 1★<need 3），旧版拒绝机制 = **店内置换账 value 平局拒绝**（复盘候选 E：「value(绯英) > value(吉尔伽美什) 严格大于不成立 → 置换拒绝」），不是 target_unbuyable（那是刷新腿拒因，发生在 2-4/2-6，且那些帧绯英不在店）。按括注写断言会锚错拒因键。②「本局 seed=20261022」——复盘报告局头与遥测均不记 seed；值本身经旁证属实（changes/2026-10-29-sim-flow-fidelity/README.md §5「同 seed（20261022）全流程冒烟」，其「旧局金滞留 67→119」与本局轨迹吻合），但设计内无出处锚。
- 修正方向：括注改为「旧版置换账 value 平局拒绝（复盘候选 E 帧，节点 2-1）」；seed 补出处锚或注明「sim 驱动参数，见 sim-flow-fidelity §5」。

**B7 ｜ 中 ｜ 核二·硬规则 4（修订全量同步）失同步 ｜ design.md §0**
- 问题：§0 文档清单写「详设待本总纲收敛后按 §2.9 划分起稿」——三份详设**已起稿存在**（README 明示「三份详设已起稿」，details/ 三文件在）。总纲 §0 与实际状态脱节，违反「design↔README 全量反查」（iteration-design.md §5 规则 4）；规范模板要求 §0 文档清单逐份列出详设。
- 修正方向：§0 文档清单改为逐份列出三个 details 文件 + 一句话范围；landing 缺位表述保留。

**B8 ｜ 中 ｜ 核二·硬规则 3（无过程叙事）｜ design.md §0**
- 问题：「状态：草案（**用户逐点审稿中**）」——「谁在审」属过程叙事，规范要求过程住对抗报告与账本、进度只住 README（§5 规则 3 卡点明列「谁审的」类措辞）。§0 状态字段只应承载枚举态（草案/对抗审中/定稿）。
- 修正方向：删括注；审稿进度归 README 进度节。

**B9 ｜ 中 ｜ 核一·判据输入未定义态 ｜ priority-model.md §2 档 4 行**
- 问题：档 4 的判定输入 `stay_target_of` 在**未锁定窗口恒返回 None**（criteria/refresh.py r2_card_reserve docstring :253-256「未锁窗口：stay_target 恒空（未完成星级目标集未锁期为空集）」；levelup.py:205 实现吻合）。P2 未锁窗口是每局必经态，该态下档 4 谓词「费用档 == None」行为未定义。
- 修正方向：补 None 分支语义（未锁定 = 无档 4，全部落档 8；或以候选缺件集费用域替代），写进档 4 数据源格。

**B10 ｜ 中 ｜ 核一·获取流程与物理约束的合成语义未写 ｜ design.md §2.3 步骤 5-6 与同节物理约束行**
- 问题：步骤 5「**部署外的全部持牌**按序列排序」+ 步骤 6「末位让路卖出（CwActionSellBench）」——部署重算把某场上件挤下时，该件在买入时点仍在场上（「挤下动作发生在后续备战环节」），会参与排序且可落末位；而同节明言「买入时点的卖出只落备战位」「店内只能卖备战位」。「末位 = 场上被挤下件」时是跳过取次末位还是放弃买入，设计未写；priority-model §5 的池子过滤（店内 = 仅备战位）与 acquisition §2 步骤 5 的「全量持牌」表述互相张力。
- 修正方向：步骤 5 补一句「排序池 = 备战位（场上件不入卖出池；被挤下件的离场归后续部署环节」，或明写「末位若为非备战位牌则顺次跳过」。

**B11 ｜ 中 ｜ 核一/核三·验证方案与并行外溢迭代的相互作用未调和 ｜ design.md §2.10 ↔ changes/2026-10-29-sim-flow-fidelity/**
- 问题：单帧测试以「本局 seed=20261022 的关键帧」构造断言，而**同日立项的 sim-flow-fidelity 批 A 已改 sim 世界模型节点窗**（补给/遭遇/BOSS 后新增备战+弹店窗口），其同 seed 冒烟轨迹已变（「新局 P2r4 消费 34 金」vs 旧局 2-3~2-7 零消费）——批 A 落地后旧局关键帧（2-3 补给后的局面、2-4/2-6 商店会话）不可按原样重放。§1.3 已把「sim 节点窗口缺失」登记为不解决+另会话跟进，但 §2.10 的帧锚完全建立在该旧世界模型上，两节未调和；且 L1 快速集回归将撞上 sim-flow-fidelity 自身在修的 64 处 sim 测试过时断言，红测归因面交叠。
- 修正方向：§2.10 声明单帧测试的帧态构造方式（按复盘数据手工构造 GameState fixture，不依赖 sim 重放），或声明「以批 A 合入后的世界模型重锚关键帧」；landing 细化时标注两迭代的验证顺序依赖。

**B12 ｜ 中 ｜ 核一·位置锚幻影 ｜ dismantle.md §1 代码面第 3 行、acquisition-and-sell.md §6 表「免费刷新」行**
- 问题：两处把「免费刷新提案段的目标可买检查」锚到 **entry.py**——entry.py 全文无任何免费刷新提案段（grep 免费命中均为第 0 步自救的免费腾位语义）；实际位置 = **shop.py 免费刷新分支**（:2025-2047，`crit_refresh.target_buyable` 调用在 :2039），refresh.py docstring（:62-64「生产调用方(shop.py 刷新提案点)」）与正本 11 号稿 §3 亦指 shop.py。dismantle §1 的 shop.py 行已含正确对象，entry.py 行是重复幻影行；acquisition §6 执行清单的「免费刷新」行是该消费点在该文档的唯一指向，锚错即误导。
- 修正方向：dismantle §1 删 entry.py 行；acquisition §6 免费刷新行现行锚改为「shop.py 免费刷新分支（:2025-2047）」。

### 低（组织文风 / 计数存疑 / 边界声明不完备）

**C1 ｜ 低 ｜ 核一·术语口径 ｜ design.md §2.2 刷新行**
- 「升星缺口 + 概率带 + 金线（criteria/refresh.py 三段式）」——代码与 11 号稿的「三段式」指 **P1 恒不刷 / P2 未锁窗口 / 锁定后**三分派（refresh.py 模块头 :3「三段式查表」），金线是独立金线闸组件（r2_budget，11 号稿 §3「刷新链三组件」）。把三组件内容称作「三段式」与正本术语撞名不同义。另 priority-model §3 档 8「费用号仅作概率同值时的稳定序」未写稳定序方向（升/降）。

**C2 ｜ 低 ｜ 核一·保留项清单不完整 ｜ dismantle.md §3/§4**
- 「保留项逐项声明不拆，防过度拆除」的清单未列：fuel_sell_candidates 内的**空板止损守卫**（empty_board_sell_blocked，mandate.py:465；11 号稿 §4.0 :183 明示为五卖出源接线面）与 merge_guard_release 释放集旁路（mandate.py:454-459）。新判据件重写评估器场景时这些结构的去留悬空。

**C3 ｜ 低 ｜ 核一·计数存疑 ｜ dismantle.md §2 遥测键面**
- 「core_* 出口键 **16 族**」——全仓 `'core_*'` 字面量去重 13 个（其中 core_chars 为字段名非遥测键；计数键实为 11 个，另含买因/契约字符串 2 个）。16 无出处，落地批按族前缀清理即可达意，但计数应实。

**C4 ｜ 低 ｜ 核三·边界声明不完备 ｜ design.md §2.7 黑塔语境条**
- 「黑塔的备战位供强…经档 2 阵容成员身份覆盖」——大黑塔银河学者线黑塔 need_star = 3（cw_comps.py:1098-1103），覆盖只在**未达标期**成立；达标后副本落档 8，后台供强护面消失（现行 bench_effect_qualified 例外①在有语境时恒保护）。实际风险被档 8 概率键部分兜底（1 费件高级别低概率 → 档 8 内后卖），但「有语境时供强保护消失」这一行为变化未按申报纪律声明。

**C5 ｜ 低 ｜ 核一·锚模糊 ｜ design.md §2.1 档 6、priority-model.md §4**
- 「复核流程 = skill references/version-update.md」未指明 skill 名（sr-od-dev-currency-war），跨仓读者定位不到。「局内流式随机管理按固定 key 取流」为转述名，实指最近设施 = StrategySession.rng（cw_strategy_session.py:130，构造时播种）与 sim 子流派生（sim/cw_sim_streams.py:18 stream_rng(seed, key)），设计未锚；新判据件的随机流从哪个设施取（策略层 session.rng 直用还是新增 key 派生）留了实现空隙（key 名已定 priority/tie，流实例来源未定）。

**C6 ｜ 低 ｜ 核二·引用寿命 ｜ dismantle.md §3 文档面末行**
- 「统一保护集 design 文档（标记退役，归档说明保留）」指向 changes/2026-10-15-unified-protection-set/design.md——changes/ 互相引用，目标文档寿命 = 迭代、可能先于本迭代收尾被清理，该文档面条目指向对象不稳定。连带：protection.py 模块头（:3-5）**代码引用 changes/ 路径**属「代码禁引 changes/」铁律的存量违例，本迭代拆除批恰触及 protection.py，其注释清理面未登记。

## 二、核二·规范遵循总评（除上述条目外）

- 总纲 §0/§1/§2 三节齐、详设三部分（问题与约束/方案/关键取舍）三份齐、README 两件事齐：**合规**。
- 引用寿命纪律：四份设计文档自身**零 changes/ 引用**（grep 证实），引用方向（代码/正本/proofs/复盘）全部合法：**合规**（C6 为对旧迭代文档的单处引用，已单列）。
- 依据就地标注覆盖面：**总体良好**——关键主张绝大多数带坐标可直调（见覆盖声明），无依据标注的孤立主张未发现；发现集中在「标了但错/漏」（A1/B1-B6）。
- 单一源纪律：priority-model 自封唯一排序判据源、acquisition 全触发只消费它、dismantle 新先于旧拆——**接口契约三分工在文面成立**（A4 的签名缺口除外）。
- landing.md 缺位判定：**不构成流程发现**。规范 §6 生命周期明文「对抗审中（总纲/详设/landing.md 一并攻）」是对抗审的攻击面清单；README 已声明「落地:待设计定稿后起稿 landing.md」，状态枚举（草案）与此自洽。规范未禁止对抗审阶段 landing 缺位（定稿才可派落地批，landing 在定稿前起稿即可）。本报告未对 landing 展开攻击，定稿前起稿后需另过「阶段可验收性」审查（含本报告 B11 的验证顺序依赖）。

## 三、核三·治本核验结论

- **归层结论成立**：三个根因（预测门/静态名单/囤积规则与锁后不换线冲突）确实都在判据语义层——预测门是判据函数（refresh.target_buyable），名单是判据数据（identity_exclusions 身份段），囤积规则是买入判据支（shop.py C1 段）；复盘实证的卡死链（2-4/2-6 target_unbuyable → 晶矿放弃 → 金滞留 119）逐环可由这三者解释，无需引入流程层根因。「不在流程层」的否定式主张经查无反例。
- **§2 修的是根**：删预测门 = 承认「刷新时点预测不可算」（docstring 自认）后把该概念整体移除，非调参；静态名单 → 统一序列 = 用一个全序判据替代离散身份豁免族，属架构级收敛；囤积规则作废 = 其存在前提（换线期权可兑现）已被 12 号稿锁后不换线制度性消亡，规则随前提退役。迁移期两档映射（阵容内优先级）是显式声明的战术降级 + 外溢排期（§2.11），符合「症状修法须声明权衡+排期」的要求。
- **跨件半问满足**：刷新面两日内两改（10-28 hp-purge-refresh-reform 加三腿门 → 本迭代整门删除）恰是「第二件症状补丁触发架构级审查」的形态，本迭代做的是概念级删除而非第三件补丁；卖出判据族（P78 仲裁 → 统一保护集 → swap-channel 统一 → 本迭代统一序列）同为收敛路线。**无逐件修违例**。
- **明确不解决边界合理**：sim 节点窗口缺失已由同日 sim-flow-fidelity 迭代实体承接（README 载明用户裁定与批 A 实施）；部署本体（24 号稿机制保留 + 纯函数接口）、装备分配、投资卡价值分（28/29 号稿）均为不同对象，不属本迭代「谁让路」主轴。唯 B11 指出 §2.10 验证方案与该外溢迭代的相互作用未调和，属边界内的失检出而非边界划定错误。

## 四、核对覆盖声明

**实读文件**：规范正本 1 份（iteration-design.md 全文）；攻击对象 5 份（design.md、priority-model.md、acquisition-and-sell.md、dismantle.md、README.md 全文）；代码 14 个（refresh.py、sell_candidates.py 前 360 行+场景表、mandate.py MandateFrame/fuel_sell_candidates/emit_swap_redeploy 段、shop.py :1855-2089 及六序/置换账锚、sell_gate.py :255-394/:880-1080、protection.py 全文、session_scope.py :314-392、entry.py 工序结构+部署步+凑息步、predicates.py :120-229、cw_factions.py :1-100、cw_chars.py 藿藿行、cw_shop_odds.py refresh_prob、mandate_state.py StrategyState、cw_comps.py 大黑塔线+need_star 字段）；正本文档 8 篇（11 号稿 §1/§3/§4.0/§4.1 锚点、12 号稿全文、30 号稿摘要、24/22 号稿标题与工序节、01/20 号稿三腿引用行、strategy-docs/README 篇目）；math_proofs P49/P78/P86/P91 行；stage_transitions.md Q1 表；复盘报告 g_20261029_084447.md（症状章 + 候选清单全读、关键帧逐帧核）；旁证 = changes/2026-10-29-sim-flow-fidelity/README.md 全文、本局 match json/journal/index 首行、strategy jsonl 藿藿买入事件。

**逐条核对清单（主张 → 结果）**：

| # | 设计主张 | 权威源 | 结果 |
|---|---|---|---|
| 1 | target_buyable 存在且 docstring 自认「需重采样预测不可算」 | refresh.py:269/:283 | ✓ 属实 |
| 2 | refresh_warranted 锁定支/未锁支两处合取调用 | refresh.py:110/:132 | ✓ 属实 |
| 3 | target_unbuyable 消费分支约 :2058 | shop.py:2058 | ✓ 精确 |
| 4 | C1 名字过滤 :1884 附近 | shop.py:1884-1887 | ✓ 精确 |
| 5 | core_numeric_fail_closed / core_candidate_rejected | shop.py:1962/:482 | ✓ 存在 |
| 6 | identity_exclusions 五源构成 | sell_gate.py:886-938 | ✓ 逐字吻合 |
| 7 | excl \|= set(CORE_SINGLE_CARD_REGISTRY) | sell_gate.py:929 | ✓ 存在 |
| 8 | funding_hold_fallback = P78-5 兜底 | sell_gate.py:1021、11 号稿 §4.1、math_proofs P78 | ✓ 属实 |
| 9 | fuel_sell_candidates 结构（exclude_names/zero_overlap/占位件/一星门/G-S1/后台效果门） | mandate.py:380-499 | ✓ 属实（消费位计数 → B2） |
| 10 | MandateFrame 字段清单 + entry 装配 | mandate.py:165-200、entry.py:488 | ✓ 属实 |
| 11 | entry 十段与各步函数名（含 _step2_ore 旧序号错位） | entry.py:4-14/:622/:706/:994/:1207 | ✓ 全部精确 |
| 12 | emit_swap_redeploy = 选 up/down 核心 | mandate.py:1447（核心实为 select_swap_plan/select_deployments_reasoned） | △ 部分（→ A4） |
| 13 | write_line_lock 连带（清商店标记/候选快照清空） | session_scope.py:314-352 | ✓ 属实 |
| 14 | line_members_view / direction_comp_of / opening_recipe_comp 读口 | session_scope.py:355/:371、mandate_state.py:307 | ✓ 属实 |
| 15 | stay_target_of / unfinished_star_targets / need_star / StrategyState 两字段 | levelup.py:205/:173、cw_comps.py:210、mandate_state.py:300/:393 | ✓ 属实 |
| 16 | cw_shop_odds.refresh_prob(等级, 费用档) 签名 | cw_shop_odds.py:61 | ✓ 精确 |
| 17 | 档 7 四羁绊在 FACTIONS 注册表、括注与 desc 吻合、成员派生单一源声明 | cw_factions.py:61/:81/:90/:96 及模块头 | ✓ 属实 |
| 18 | CROSS_LINE_KEEP_NAMES 四角色 + Q1 表依据 | protection.py:64、stage_transitions.md:35-48 | ✓ 属实 |
| 19 | SCENE_SPECS 场景注册表骨架 / 价值函数三项 / MERGE_PROGRESS_X2 / 跨档止盈 / 仅一星过滤位置 | sell_candidates.py:172-198/:227/:241-279、criteria/sell.py:90 | ✓ 属实（凑息亦有仅一星过滤，总纲 §2.6 归因不全，并入 B 类不单列） |
| 20 | P49 线性律支撑档 4/档 4.1 | math_proofs:69 | ✓ 属实 |
| 21 | 六序 + C1 关系 | 11 号稿 §1:25、shop.py:657 | ✗ **不符（A1）** |
| 22 | 档 4 与落档边界一致性 | 总纲 §2.1 vs priority-model 档 4 | ✗ **矛盾（A2）** |
| 23 | 随机域无行为语义差异声明 | priority-model §3/§4 推演 | ✗ **不成立（A3）** |
| 24 | DirectionView 可用作契约类型 | 全仓 grep | ✗ **不存在（A4）** |
| 25 | 免费刷新提案段在 entry.py | shop.py:2025-2047、refresh.py:62-64 | ✗ **位置错（B12；判据缺口另见 B5）** |
| 26 | protection.py 有 registry 并集分支 | 全仓 grep CORE_SINGLE_CARD_REGISTRY | ✗ **不存在（B1）** |
| 27 | 后台效果门「三消费位随评估器退役」 | 4 处消费位实读 | ✗ **fuel 位不随退役（B2）** |
| 28 | shop_refresh_blocked_memory_skip 可整删 | shop.py:2019-2089 | ✗ **金线分支仍在役（B3）** |
| 29 | 22 号稿有三腿引用；12 号稿 §4 有 C1 表述 | strategy-docs 全目录 grep | ✗ **均无（B4）** |
| 30 | 免费刷后判据 = 缺口+概率带 | shop.py 免费支现状 | ✗ **无处接线（B5）** |
| 31 | 席满帧绯英在店旧版拒因 = target_unbuyable | 复盘 :2359-2392 | ✗ **实为置换账 value 平局（B6）** |
| 32 | seed=20261022 为本局 seed | sim-flow-fidelity README §5 | ✓ 值实（锚缺 → B6） |
| 33 | §0 文档清单与实际一致 | details/ 三文件在库 | ✗ **失同步（B7）** |
| 34 | 症状链：2-4/2-6 四会话开店即收店、dseq 134-137/141-144、金 87→119、9 张全保护、晶矿 8 座（+18 金+3 装备） | 复盘 :3586-3735/:3966/:4179 | ✓ 逐项属实 |
| 35 | 囤积 9 金三张（银狼LV.999×2+希儿）dseq 109/121/129 | 复盘 :2891-3411、候选 B | ✓ 属实 |
| 36 | 与 12 号稿 §1.4「锁后不换线」冲突 | 12 号稿 :47-51 | ✓ 属实 |
| 37 | 迭代来源 = 复盘候选 A/B/E | 复盘 :4199-4218（六条） | ✓ 吻合 |
| 38 | M2b 机制全集口径（混合计数/向三星） | 11 号稿 §1:45 | ✓ 属实 |
| 39 | 自救扩展面豁免现行 | sell_candidates.py FACE_SELF_RESCUE、11 号稿 §4.0 | ✓ 属实 |
| 40 | 30 号稿三级字典序中间级布尔、supply.py 本体 | 30_supply_screen.md、supply.py:3/:13 | ✓ 属实 |
| 41 | 28/29 号稿 = 投资卡对象 | strategy-docs 目录 | ✓ 存在 |
| 42 | 「恒买腾位早期经济纪律四规则」「§4.0 场景表 C1 行」存在 | 11 号稿 :37/:136 | ✓ 存在 |
| 43 | 阵容注册表二元标记（core_chars/shared_chars）现状 | cw_comps.py:94/:103 | ✓ 属实 |
| 44 | sim 窗口缺失「另会话跟进」有承接 | changes/2026-10-29-sim-flow-fidelity/ | ✓ 在动（交互 → B11） |
| 45 | 四份设计文档自身无 changes/ 引用 | 目录 grep | ✓ 合规（dismantle 单处指向旧迭代文档 → C6） |

统计：主张级核对 45 项——✓ 属实 32 项、✗ 出入 11 项、△ 部分属实 2 项；归并为发现 **22 条（高 4 / 中 12 / 低 6）**，一条发现可合并多处出入。全部发现经权威源直调证实，无推测性条目。
