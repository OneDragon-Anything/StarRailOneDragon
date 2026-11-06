# 攻击报告 R2 · 统一让位优先级（2026-10-29 第二轮对抗审查）

> 攻击框架 = 三核并重（核一·无前提为主），规范正本 = `docs/develop/harness/iteration-design.md` §5/§7。
> 双重职责：①对 attack.md 22 条发现（高 4/中 12/低 6）逐条回归核对；②不被上轮锚定，对当前四份文档
> 无前提全量再攻（含返工新增主张逐条直调）。严重度口径与上轮一致：高 = 依据错误 / 判据不可实现 /
> 接口契约缺口；中 = 依据缺标注 / 表述可歧义 / 清单错漏 / 行为变化未申报；低 = 计数存疑 / 文风 / 边界声明不完备。
> 所有条目经权威源直调证实；行号以 2026-10-29 工作区现状为准。

## 结论摘要

- **回归核对**：22 条中 **18 条已正确修复**，**4 条修复不完整**（B1、B5、B8、C3——各自残留下文逐条给出）；无一条「上轮发现本身错误」。
- **新发现**：**13 条（高 2 / 中 2 / 低 9）**。存在 **2 条高严重度问题**：R2-01（静态名单退役不闭合，买面囤货臂与身份消费面漏拆）、R2-02（PriorityContext 字段面缺持牌全量输入，聚合谓词不可实现）。
- **总体结论**：**需继续返工**（2 高阻断 + 2 中；低项可随返工顺带）。核心模型（八档/触发/接口三分工）方向未动摇，返工集中在拆除面闭合与判据输入面补全。

---

## 一、返工回归核对表（22 条逐条）

判定口径：**已正确修复**（修法正确、无新问题、与他节同步）/ **修复不完整**（主体修复但留残留或引入新问题，指针→新发现编号）/ **引入新问题**（单列）。

### 高（A1–A4）

**A1 ｜ 已正确修复**。design §2.2 买入行现文「买入六序判类（11 号稿 §1；**六序之外的 C1 邻位支删除**，dominance 段保留）」。权威源吻合：11 号稿 §1:25「C1 名单核心卡支位次 = **第 7 邻位**（纯冗余停买判定之后）」+ 同行「dominance……动作发出点 = 序 7 邻位」（C1 删后 dominance 邻位仍在）；与同总纲 §2.6「六序｜删单卡核心支，其余不动」不再矛盾。

**A2 ｜ 已正确修复**。priority-model §2 档 4 谓词改「**非阵容成员** ∧ 费用档 == 当前升星目标实费档」，排除项括注「含已达标成员，其副本按总纲 §2.1 落档边界落档 8」。逐路径推演与总纲一致：未达标成员副本按序命中档 2/3；达标成员（need_star ≥ 2）过档 5 需 need_star ≤ 1 不中、过档 6/7 需最高星 < 2 不中 → 档 8 ✓；need_star = 1 成员的商店牌（名下有副本）正确落档 5（总纲边界「有要求已满足」的「有要求」= need_star ≥ 2，自洽）。

**A3 ｜ 已正确修复**。档 2 子键增③「单卡星级（高者后卖）」，§4 随机域声明改写为「跨星副本已被档内星级键区分、商店牌已被在手旗标区分，均不入随机域」。键方向与 §1「key 大者先卖」自洽（优先级序数大 = 后卖、总星数少 = 先卖、单卡星低 = 先卖）。（同成员跨成员间②键「保留总星级数更多」为总纲既定拍板口径，未变，不在本轮攻击范围。）

**A4 ｜ 已正确修复**。DirectionView 已废除（全仓 grep：现存命中仅 turnstate-retirement 迭代文档与历史 proof 注记，无活引用；design 侧新签名 = `virtual_deployment(frame, prep: PrepContext)`）。修复的三个缺口全部有实锚：
- PrepContext 四组字段逐一在代码可锚：`line_members_view`/`direction_comp_of` = session_scope.py:355/:371；`opening_recipe_comp` = mandate_state.py:307（写端 flow.py:255）；entry_signals = Comp 字段（cw_comps.py:226）+ entry.py:283-302 消费；`deploy_vacancy`/`deploy_cap` = MandateFrame property（mandate.py:202-212）；`_make_windowed_select_up` 装配面 = entry.py:391-414。
- 板满换阵收敛语义定案「目标态求取，不模拟换阵路径」与现行发射形态相容：emit_swap_redeploy（mandate.py:1447）「每个动作发出面只发**首对**……组剩余由下帧重算幂等续发（计划无跨帧状态）」——计划每次全量算出、仅发射节奏分帧，虚拟取全计划端点 = 目标态，读法成立。
- 「结构抽取 + 生产路径回归由现行部署测试守」有实证：sr-od-test 存在 kernel/test_deploy.py（select_swap_plan/select_deployments）、test_emit_swap_bond_gate.py（entry._step5_deploy 同序）、test_select_swap_group_plan.py、test_swap_label_exclusion.py、test_loop.py deploy_plan_moves 段。
- 残留观察（不构成发现）：`select_deployment -> frozenset[str]` 只携带名集，场上槽位/具体副本（星级、装备）的选择语义留在动作生成层——现文「零判据改动」「取值语义逐一对齐现行」可覆盖，落地批抽取时保持 deploy_plan_moves 落位/对位语义不动即可。

### 中（B1–B12）

**B1 ｜ 修复不完整（→R2-01）**。protection.py 幻影指向已删；dismantle §2 已补「`_hold_qualification_ok` 的名字分支与 core 档（:296-308）」——锚点本身精确（:296-298 = 名字分支三腿、:299-300 = core 档闸，实读吻合）。但**拆除范围标注过宽**：名字分支 = 保护集 ∪ registry 核心 ∪ 乙分支获取三腿（:296-298），其中保护集/hub 两腿服务在役的 protection_hoard 囤臂与乙分支 hold 登记（:282-285 docstring「hold 类买入 = C1 核心 + protection_hoard」）——随 C1 整段拆除即在役机制被误拆；范围应缩为 registry 腿（:297）+ core 档闸（:299-300），或连带把囤臂整链登记退役（见 R2-01）。

**B2 ｜ 已正确修复**。dismantle §3 fuel 行补「`bench_effect_qualified` 检查删除（:488——该谓词共四处消费位……）」；四处全部实证：评估器 sell_candidates.py:511、凑息档序 sell.py:182、筹资通道 sell.py:295、fuel mandate.py:488；priority-model §6 同步为「四处」口径。两文一致。

**B3 ｜ 已正确修复**。`shop_refresh_blocked_memory_skip` 在 dismantle §1（保留）、§4 保留项表、acquisition §7 三处一致保留；语义锚实：金线不足仍置位 shop.py:2089、命中计数 :2023——记忆在役、跳过继续发生，保留判定正确。

**B4 ｜ 已正确修复**。①§1 文档面 = 11 号稿 §3（:89-105「目标可买三腿并集」整节）、01 号稿 :84/:86/:147、20 号稿 :66、23 号稿 §1（:10）——四个锚逐一实读命中；②§2 文档面改为 11 号稿 §1 单卡核心支（:27-35）、「恒买腾位早期经济纪律四规则」C1 相关行（:37-43）、§4.0 场景表「C1 恒买席满腾位」行（:136）——全部实存；12 号稿错指已除，§3 改指「12 号稿 §1.2 囤积纪律」（:29 实存，且其身份单一源 = protection_membership 与拆除直接相关，指向成立）。

**B5 ｜ 修复不完整（→R2-03）**。定案方向正确且三文档接线一致：design §2.2「改为消费与付费支同一的 refresh_warranted 残余判据（三分派……）」、acquisition §6 免费刷新行、dismantle §1 shop.py 行互相咬合；残余判据技术可行（refresh_warranted :110/:132 两处 target_buyable 合取删除后判据自洽；免费分支现场有 `missing`/`stay_target_of` 输入，shop.py:2036-2038）。**但该定案把「P1 恒不刷」带进免费腿，与现行教义冲突且未申报行为变化**（详见 R2-03）。

**B6 ｜ 已正确修复**。①§2.10 括注改「旧版拒绝机制 = 店内置换账 value 平局拒绝（复盘候选 E 帧，节点 2-1）——非 target_unbuyable」，与复盘报告 :2359-2392 逐点吻合（bench 9 满、绯英 2 金在售槽 1、绯英 1★<need_star 3、「value(绯英) > value(吉尔伽美什) 严格大于不成立 → 置换拒绝」、候选 E 登记）；②seed=20261022 补锚 = changes/2026-10-29-sim-flow-fidelity/README.md §5:129「同 seed（20261022）全流程冒烟」，值实。附注（不立发现）：该锚属 changes/→changes/ 引用（C6 同类寿命注意），迭代内合法，定稿时可改写为「sim 驱动参数」语义描述脱钩。

**B7 ｜ 已正确修复**。design §0 文档清单逐份列出三份详设 + 一句话范围，与 details/ 实际文件一致；「landing.md 待设计定稿后起稿」保留。

**B8 ｜ 修复不完整**。状态枚举已改「对抗审中」✓；但括注「（首轮攻击报告 = [attack.md](attack.md)，**返工中**）」仍是过程叙事——「首轮」= 轮次词（规范 §5 规则 3 卡点明列「第几轮攻击/本轮」类措辞）、「返工中」= 进度态，进度只应住 README（README 已载同类信息，合法）。「报告 = attack.md」指针本身合法（同迭代工件互引）。修正：删括注，或仅留报告指针。

**B9 ｜ 已正确修复**。档 4 谓词补 None 分支「当前升星目标为 None（未锁定窗口恒 None，`stay_target_of` 口径）时本档为空」；与 refresh.py:117-119（未锁定 target None → 拒）、r2_card_reserve docstring :253-256（「未锁窗口：stay_target 恒空」）口径一致。「实费口径，变费卡随档」亦有锚（r2_card_reserve :242-244「target[2] resolved 实费档」）。

**B10 ｜ 已正确修复**。design §2.3 步骤 5 与 acquisition §2 步骤 5 均补「排序池 = 备战位——场上件不入卖出池，被部署挤下件的离场归后续备战环节」；两处同口径，与同节物理约束行闭合。

**B11 ｜ 已正确修复**。§2.10 声明单帧测试「按复盘数据手工构造 GameState fixture（不依赖 sim 重放）」+ 顺序依赖声明「其批 A（sim 世界模型节点窗）合入前，本迭代禁用 sim 重放类验证手段」。实锚：批 A =「节点备战窗口 + 自动开店」重构（sim-flow-fidelity README :63，且 :3 载明批 A 已实施、64 处 sim 测试过时断言在修——L1 归因交叠风险由「手工 fixture 不依赖 sim」化解）；GameState 类型实存（kernel/cw_game_state.py）。

**B12 ｜ 已正确修复**。dismantle §1 代码面现仅 refresh.py / shop.py / 刷新负结果记忆三项，entry.py 幻影行已除；acquisition §6 免费刷新行锚改「shop.py 免费刷新分支（:2025-2047，`target_buyable` 调用在 :2039）」——逐行精确（实读：free_left 判定 :2025-2026、target_buyable 调用 :2039）。entry.py「免费」命中均为第 0 步免费腾位语义（:502/:627/:638/:647），无免费刷新提案段。

### 低（C1–C6）

**C1 ｜ 已正确修复**。①design §2.2 刷新行改「升星缺口与概率带的**三分派**判据（P1 恒不刷 / P2 未锁候选缺件 / 锁定星级目标；criteria/refresh.py）」——「三分派」与 refresh.py 模块头/11 号稿 §3 的 P1/P2/锁定三分派口径一致，金线闸（r2_budget）分列，术语撞名消除；②档 8 稳定序方向已写「概率同值时按费用号升序稳定序，低费先卖」。（「升星缺口」用词问题归 R2-11。）

**C2 ｜ 已正确修复**。空板止损守卫（mandate.py:465 `empty_board_sell_blocked` 实存）与 merge_guard_release 释放集旁路（:454-459 docstring、:480-481 判据处实存）已登记进 dismantle §3 保留清单 + §4 保留项表。

**C3 ｜ 修复不完整（→R2-06）**。dismantle §2 已改「全仓 'core_*' 字面量去重 13 个（计数键 11 + 买因/契约字符串 2）」，但 design §2.5 仍残留「出口键族（**core_* 16 键**）」未同步（规则 4）；且本轮实测带引号 `core_*` 字面量去重 = **15**（剔除字段名 core_chars 后 14）——16 / 13 / 实测三方不齐（16 的出处 = 11 号稿 :35 出口键闭集 3 族×5 后缀 + 尾键，含 `transition_*` 族非 core_* 字面量，系两口径混写）。建议放弃精确计数，改「按族前缀清点，计数以落地批清点为准」。

**C4 ｜ 已正确修复**。design §2.7 已按申报纪律写明行为变化：「大黑塔线黑塔达标三星后，其副本落档 8，后台供强保护面消失……实际风险被档 8 概率键部分兜底（一费件高级别档内后卖）；若该回归不可接受需在档 8 前单列供强保护」。实锚：黑塔 cost=1（cw_chars.py:110）、大黑塔线 need_star「黑塔：3」（cw_comps.py:1098-1103）——「达标三星」「一费件」均成立。

**C5 ｜ 已正确修复**。①skill 名补全「sr-od-dev-currency-war skill 的 references/version-update.md」——文件实存（skills/sr-od-dev-currency-war/references/version-update.md）；②随机流设施定案「策略器自有随机流 StrategySession.rng 直用（构造时按 strategy_seed 播种）【详设定案】」——cw_strategy_session.py:128-130 实证（rng 字段 + strategy_seed 覆盖注释）。

**C6 ｜ 已正确修复**。dismantle §3 代码面已登记「protection.py 模块头引用 changes/ 路径的注释（:3-5 附近，存量违例）随本批触及一并清理」（实读：protection.py:3-5 确引用 changes/2026-10-15-unified-protection-set/design.md）；文档面统一保护集 design 篇退役标记附「引用寿命注意」缓解语。

### 回归小结

| 判定 | 条目 |
|---|---|
| 已正确修复（18） | A1 A2 A3 A4 B2 B3 B4 B6 B7 B9 B10 B11 B12 C1 C2 C4 C5 C6 |
| 修复不完整（4） | B1（拆除范围过宽→R2-01）、B5（接线成立但引入未申报行为变化→R2-03）、B8（括注过程叙事残留）、C3（design 侧计数残留→R2-06） |
| 引入新问题 | B5 返工引入 R2-03；B1 返工补拆行时引入范围标注问题（R2-01 组成部分）；其余返工未引入新问题 |
| 上轮发现本身错误 | 无——22 条主张本轮全部直调复核成立 |

---

## 二、新发现清单（13 条：高 2 / 中 2 / 低 9）

### 高

**R2-01 ｜ 高 ｜ 核一 + 核三 ｜ dismantle.md §2/§3、design.md §1.2/§2.5/§2.6、acquisition-and-sell.md §3**
**静态名单退役不闭合：买面囤货臂与身份消费面全部漏拆，§3 自设前提「消费面全退役后函数退役」不成立。**
- **囤货臂整体缺位**：protection_hoard 买入臂（shop.py:1366-1394；守卫未锁定帧 :1375；身份读点 `_protection = protection_membership(...)` :892；买因 `protection_hoard`、出口键 `protection_hoard_hit/no_fuel/unaffordable` :1373-1393）不在任何拆除或改造行。其正本依据 = 12 号稿 §1.2 囤积纪律（:29「首副本走囤货臂（买因 protection_hoard）」）与 11 号稿 §1:14 序 1「保护集囤货面」。设计 §2.6「买入（有空位）｜删单卡核心支，**其余不动**」等于明示买面身份囤积全部保留。
- **protection_membership 其余消费位未登记**（dismantle §3 仅登记 identity_exclusions/funding_hold_fallback/_hold_qualification_ok 三处）：entry.py:782（`_bench_liquid_gold` 攒批资金剔除保护件——凑金域资金口径直接受影响）、entry.py:1165-1207（`_protected_member_blocks_interest` 凑息阻断身份面——恰在 acquisition §3 重写的凑息场景内，未提及删除）、shop.py:374（拒因标注保护分类）、shop.py:1196-1205（会话筹资兜底腿「保护集 ∪ registry 核心」判定域）、mandate.py:1283-1287（`deadlock_only_transition_victim` 保护集口径计数键，11 号稿 :179 登记在案）。
- **Z1 凑息卖出资格集排除**（11 号稿 :42；`mandate.sell_hold_exclusions` / `cw_card_identity.sell_hold_exclusion_names`，目标口径 = 保护集 ∪ registry 核心）身份构成未登记拆除。
- **行为矛盾（治本缺口）**：design §1.2 根因 2 自陈「名单在买入侧不断扩张（囤货判据持续买进受保护的面）」是锁死机制的构成部分；§2 只拆卖面——统一后囤臂继续按名单买入（四体系成员等），新序列把非线/非万金油/非羁绊的囤入件排档 8 即卖：1★ 全额退下金平但买卖空转、白耗动作帧，名单「买入侧扩张」病灶原样存活。
- **dismantle §3 前提落空**：「`protection.py protection_membership`：消费面全退役后函数退役」——按在册拆除行，上述消费位无一退役，前提永不满足；函数实际只能存活，与「静态名单退役」的迭代目标名实不符。
- **修正方向**：设计层拍板买面身份的去向（囤臂随名单整体退役并入 §2 拆除清单/改造规格；或显式保留并申报理由与行为影响），把上列消费位、Z1、`protection_hoard_*`/`deadlock_only_transition_victim` 键面逐项登记进 dismantle；R2-01d 配套收窄 `_hold_qualification_ok` 拆除范围（见 B1 回归条）。

**R2-02 ｜ 高 ｜ 核一 ｜ priority-model.md §1/§2、acquisition-and-sell.md §2**
**PriorityContext 字段面缺「持牌全量」输入，八档聚合谓词按声明的输入不可实现。**
- 依 §5「池子过滤在 `sell_order` **之前**」（acquisition §2 步骤 5「排序池 = 备战位」同口径），排序输入 = 过滤后池子；而档位谓词全部是**跨池聚合**：档 2「持有最高星 = 该名全部**在场+备战**副本的最高星」「总星级数 = 全部副本星数相加」、档 5/6/7「名下最高星 < 2」、档 3「名下无任何副本」（商店牌求值需手牌名集）。PriorityContext 七项（部署在场名集 / 名单视图 / 候选快照 / 升星目标 / need_star 表 / 当前等级 / 随机流）中只有「部署在场名集」——**名字、无星级**，且不含备战副本。
- 后果实例：成员场上已有 2★（need_star = 1，已到两星），其备战 1★ 副本在池——正确判定 = 档 8（掉出档 5/6/7），按现字段面看不到场上 2★ → 误判档 5 受保护。买面同理：商店牌求档 3「名下无副本」无法计算（手牌名集不在 ctx）。
- 修正方向：PriorityContext 增第 8 项「持牌全量快照（名 → 副本星级列表，场上+备战）」，数据源 = 容器一次性只读装配（与既有约束「一次性装配，禁散参」同型）。

### 中

**R2-03 ｜ 中 ｜ 核一 ｜ design.md §2.2（B5 返工引入）**
**免费刷新接线引入未申报行为变化：P1 免费刷全停 + 概率带外免费刷停，与现行教义冲突未声明。**
- 现行教义明文免费腿豁免 P1 判据：11 号稿 §3:95「免费刷新次数（概率事件·棱 45% + 每节点免费刷新……）**不计入本判据**但过目标可买检查」；shop.py:2028-2032「白给的刷新照用，不构成主动刷」。即 P1 恒不刷辖**付费**；免费腿现场无 P1 门（实读 :2025-2047 仅 target_buyable 检查）。
- 返工定案「免费腿消费与付费支同一的 refresh_warranted 残余判据（三分派：**P1 恒不刷**/P2/锁定+概率带）」→ ①位面 1 全部免费次数（投资事件与每节点免费）永不消费；②锁定后等级低于带下界帧（stay_gate_upgrade_first）免费刷停、次数保留不耗。均为真实行为变化，不在 §2.7 行为变化申报（现仅凑息池收窄、黑塔供强两项）中。
- 修正方向：二选一并申报——免费腿判据改为「P2/P3 残余判据，P1 豁免保留」（与现行教义连续）；或维持三分派，把「P1/P3 免费刷停用」记入 §2.7 行为变化申报。

**R2-04 ｜ 中 ｜ 核二·规则 4 ｜ design.md §2.4 ↔ §2.7 ↔ acquisition-and-sell.md §3**
**凑钱参数表池子选项与拍板自相矛盾。** §2.4「四个凑钱类场景合并为一个卖出判据件 + 参数表（池子：备战位 / **备战位∪场上无关角色**；……）」——§2.7 拍板明文「凑钱场景统一按优先级，**场上不入卖出池**」，acquisition §3 四个凑钱场景池子也全部 = 备战位（仅溢出 = 全量）。「∪场上无关角色」选项在统一后无任何场景消费，系拍板新增后未全量反查的旧口径残留。修正：删该选项（或改注「仅溢出场景为全量」）。

### 低

**R2-05 ｜ 低 ｜ 核二·规则 4 ｜ design.md §2.6**
席满买入行「§2.3 **四步**流程」——§2.3 为六步（1 快照/虚拟局面 … 6 末位让路），acquisition §2 同称「六步」。改「六步流程」。

**R2-06 ｜ 低 ｜ 核一/核二 ｜ design.md §2.5、dismantle.md §2**
「core_* 出口键族」计数三方不齐：design §2.5 = 16（未随 C3 返工同步）、dismantle §2 = 13、本轮实测带引号字面量去重 = 15（剔字段名 core_chars 后 14；16 的出处 = 11 号稿 :35 闭集 3×5+1 含 transition_ 族）。建议统一为「按族前缀清点，计数以落地批清点为准」，design 侧同步删「16 键」。

**R2-07 ｜ 低 ｜ 核一 ｜ priority-model.md §6 ↔ design.md §2.4、dismantle.md §4**
「物理谓词（占位件不可卖、**素材守卫**、一星全额退口径）保留，迁移至新卖出判据件的**池子过滤层**」——素材守卫（G-S1）在 design §2.4 与 dismantle §4 均归**循环防线层**。三处两说，统一为「素材守卫→循环防线层；占位件/一星口径→池子过滤层」。

**R2-08 ｜ 低 ｜ 核一 ｜ priority-model.md §6、dismantle.md §4**
「（退金表、概率表）保留为**档位判定数据源**」——概率表 → 档 8 成立；**退金表**在八档谓词与全部子键中无任何消费（档位键 = 优先级序数/总星数/单卡星/概率），其现役消费 = 凑钱/保息「目标达成」算术与活期金口径（cw_economy.sell_refund 消费族）。改挂「卖出判据件目标达成谓词数据源」。

**R2-09 ｜ 低 ｜ 核一 ｜ acquisition-and-sell.md §3、priority-model.md §5**
溢出场景池子「全量（备战位 ∪ 场上）」的达成谓词语义未定：卖场上件不减备战位计数，「末位起连续卖出**至不溢出**」如何记账（是否联动「卖场上 → 腾部署位 → 部署备战件」的补位链）未写；现行 self_rescue = POOL_BENCH_ONLY（sell_candidates.py:173-175），扩池为新能力却无机制规格。补谓词口径，或收窄池子为备战位。

**R2-10 ｜ 低 ｜ 核一 ｜ acquisition-and-sell.md §3**
场景表列头「场景（**注册表键**）」下为中文标签；实际 SCENE_SPECS 键 = self_rescue / ore_make_room / levelup_liquidate_prep / node_end_interest / session_funding（sell_candidates.py:172-198）。列头不实，实现者需自行映射——改列头为「场景」或填实键名。

**R2-11 ｜ 低 ｜ 核二（design §2.8 自反） ｜ design.md §2.2/§2.4、priority-model.md §5**
返工新增句使用自家黑话对照表内的旧词：「免费**腾位**顺序」（§2.8：腾位→空出备战位；出现于 design §2.4、priority-model §5）、「升星**缺口**与概率带」（§2.8：星级缺口→还没升到目标星；出现于 design §2.2）、「**缺件**」（未登记对照，design §2.2）。§2.8 明文「新写的文档……一律用直白词」。

**R2-12 ｜ 低 ｜ 核一 ｜ design.md §2.7**
待决清算不精确：①「溢出上阵安置的选牌规则详设核对现行后按序列对齐」未落任何详设（现行 = 部署判据 deploy_plan_moves，entry.py:638-646），且「按序列对齐」与 §2.2「优先级不反向影响部署」存在未调和张力——实现者无从判断安置选牌是否改由序列驱动；②「优先级排序的部署输入供给方式（现算 vs 缓存）」仅有间接答案（PriorityContext 一次性装配），非虚拟触发场景的档 1 数据源未明写「当前在场名集」。

**R2-13 ｜ 低 ｜ 核一 ｜ priority-model.md §2/§3**
「阵容内优先级序数」在**跨线成员**（同一 char 在 A 线 core、B 线 shared——候选三线并集语境常见，如实例：花火同时在列车同行 core 与多线 shared，cw_comps.py:547/:561）与**过渡配方成员**（不在 COMP_LIBRARY 注册表线内）上的取值规则未定——迁移期两档映射（core=0/其余=1）仍需一个取值规则（取 min / 首线命中），否则实现者需再设计。

---

## 三、核对覆盖声明

**实读文件**：
- 规范正本：iteration-design.md 全文。
- 攻击对象 6 份全文：design.md、README.md、details/priority-model.md、details/acquisition-and-sell.md、details/dismantle.md、attack.md（对照基准）。
- 代码直读段：criteria/refresh.py 全文；shop.py :345-389（拒因标注）/ :1185-1224（筹资兜底腿）/ :1352-1401（囤货臂）/ :1990-2102（刷新链三组件+免费分支+负结果记忆）；sell_gate.py :270-344（_hold_qualification_ok 全函数）/ :880-954（identity_exclusions + sell_exclusions 头部）/ :1018-1082（funding_hold_fallback）；mandate.py :150-269（MandateFrame+四硬约束）/ :380-504（fuel_sell_candidates 全函数）/ :1262-1301（死锁计数键段）/ :1440-1529（emit_swap_redeploy）；entry.py :1-60（十段结构）/ :325-444（窗口谓词/部署发出/窗口化选人/emit 头）/ :622-671（第 0 步自救全函数）/ :757-801（_bench_liquid_gold）/ :994-1048（_step5_deploy）；protection.py :1-130；kernel/cw_exec_state.py :100-199；kernel/cw_game_state.py :510-589（Unit/BenchSlot/DeployedView）。
- 代码锚 grep 实证：levelup.py（stay_target_of:205/unfinished_star_targets:173）、session_scope.py（write_line_lock:314/line_members_view:355/direction_comp_of:371）、mandate_state.py（line_candidates:300/refresh_blocked:382/:393/opening_recipe_comp:307）、cw_comps.py（core_chars:94/shared_chars:103/need_star:210/CORE_SINGLE_CARD_REGISTRY:485/大黑塔线 need_star:1098-1103/entry_signals:226）、cw_strategy_session.py（rng:128-130）、cw_shop_odds.py（refresh_prob:61）、cw_factions.py（盛会之星:61/量子同频:81/减益:90/护盾:96/成员单一真相源:29）、cw_chars.py（黑塔 cost=1:110）、predicates.py（zero_overlap:95/item_slot_unsellable:101/bench_effect_qualified:205）、sell_candidates.py（SCENE_SPECS:172-198/FACE_SELF_RESCUE:121/MERGE_PROGRESS_X2_SLOT:227/价值函数三项:248-269/bench_effect:511）、criteria/sell.py（跨档止盈:90/bench_effect:182/:295）、protection_membership 全仓消费面（11 处逐点定位）、DirectionView 全仓（仅历史迭代文档）、entry.py「免费」（仅第 0 步腾位语义）。
- 工具核数：全仓带引号 `core_*` 字面量去重计数（pwsh 递归两轮，15 个原始/14 剔字段名）。
- 文档：11 号稿 §1（六序位次:25/C1 支:27-35/四规则:37-43/序 1 星级口径:45）/ §3（:89-105）/ §4.0（:121-183 场景表+置换账）/ §4.1（:171-183）；01 号稿 :84/:86/:147；20 号稿 :66；23 号稿 §1:10/:20；12 号稿（结构 + §1.2:29 + §1.4/版本表）；30 号稿 §1-§2（三级字典序）；strategy-docs 目录全列；math_proofs.md P49 行（:69）；skill SR 仓 skills/sr-od-dev-currency-war（SKILL.md 测试分层行、references/ 目录清单、version-update.md 存在性）。
- 症状实证：.debug/currency_war/deep_review/g_20261029_084447.md :2355-2399（节点 2-1 席满帧逐项）。
- 并行迭代：changes/2026-10-29-sim-flow-fidelity/README.md（状态行、批 A 节、§5 同 seed 冒烟行）。

**未覆盖（明示）**：landing.md（未起稿，沿用上轮「不构成流程发现」判定，定稿前起稿后需另过阶段可验收性审查）；sim 子系统代码；22/24/31 号稿全文（仅标题与被引工序行）；proofs 其余命题（上轮已核的 P78/P86/P91 未改动引用不再重读）；复盘报告其余章节（§1.1 症状段本轮未改动，沿用上轮 :3586-3735/:3966/:4179/:2891-3411/:4199-4218 的核对结论）。

**统计**：回归 22 条（18 正确 / 4 不完整 / 0 上轮误报）+ 新发现 13 条（高 2 / 中 2 / 低 9），全部经权威源直调证实，无推测性条目。新发现中 R2-01/R2-02 为定稿阻断项。
