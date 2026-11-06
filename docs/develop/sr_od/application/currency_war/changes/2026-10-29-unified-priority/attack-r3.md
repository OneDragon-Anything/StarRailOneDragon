# 攻击报告 R3 · 统一让位优先级（2026-10-29 第三轮对抗审查）

> 攻击框架 = 三核并重（核一·无前提为主），规范正本 = `docs/develop/harness/iteration-design.md` §5/§7。
> 三重职责：①回归核对 attack-r2.md 的 13 条发现（高 2/中 2/低 9）是否全部正确返工；②回归抽查
> attack.md 22 条中与第二轮返工交叠的条目（尤其 B1/B5）；③无前提全量再攻（前两轮未发现的、
> 两轮返工引入的、跨文档失同步）。严重度口径与前两轮一致：高 = 依据错误 / 判据不可实现 / 接口契约
> 缺口；中 = 依据缺标注 / 表述可歧义 / 清单错漏 / 行为变化未申报；低 = 计数存疑 / 文风 / 边界声明不完备。
> 所有条目经权威源直调证实，无推测性条目；行号以 2026-10-29 工作区现状为准。

## 结论摘要

- **R2 回归**：13 条中 **7 条已正确修复**，**6 条修复不完整**（R2-01/03/07/08/09/11——各自残留见回归表，均未推翻 R2 发现本身）；无一条「R2 发现本身错误」。
- **首轮交叠抽查**：B1/B5 经 R2 返工后**判定已闭合**（B1 的三腿分派、B5 的接线定案均正确），各自遗留归入 R2-01 与 R2-03 的清单/申报面，非 B1/B5 本身错误。
- **新发现**：**13 条（高 2 / 中 3 / 低 8）**。存在 **2 条高严重度问题**：R3-01（档 6/7 档内键：总纲 6.1/7.1 声明「总星级数」判别键，唯一判据源 priority-model 未承载、且其现键在档 6/7 内恒常数永不判别——总纲与详设两个答案，实现者无法落码）、R3-02（买侧身份消费位枚举残留，R2-01 同类缺口：按在册清单施工则「未锁定期不再自动囤」申报失实、`protection_membership` 退役前提仍不成立）。
- **总体结论**：**需继续返工**（2 高阻断 + 3 中；低项可随返工顺带）。核心模型（八档结构/三触发/接口三分工）方向未被本轮动摇；高阻断集中在档 6/7 键面补全与拆除面清单闭合，返工面清晰、不动摇已定拍板。

---

## 一、R2 十三条回归核对表

判定口径：**已正确修复**（修法正确、无新问题、与他节同步）/ **修复不完整**（主体修复但留残留或引入新失同步，指针→新发现编号）。

**R2-01（高·静态名单退役不闭合）｜ 修复不完整（→R3-02）。**
返工主体落地且锚点全部实测吻合：design §2.5 新增「买面身份保护判据」行（囤货臂 shop.py:1366-1394 实读逐行吻合——守卫 `not _line_view.locked` :1375、`_buy_view('protection_hoard')` :1376、门序 :1381-1391、出口键 :1384/:1391/:1393、emit :1394）；dismantle §3 新增买侧段，逐项锚实测：entry 攒批资金 `protection_membership` :782 ✓（`_bench_liquid_gold` :757-790）、entry 节末凑息阻断 :1165-1207 ✓（`_protected_member_blocks_interest` :1165-1204，:1184 读点）、shop.py :374 ✓（拒因快照函数内 fallback 读）、:1196-1205 ✓（会话筹资兜底腿，:1202 保护判定）、mandate 死锁计数键 :1283-1287 ✓（`deadlock_only_transition_victim`）、Z1 ✓（`sell_hold_exclusions` sell_gate.py:1093 = `sell_exclusions(channel='interest')` 委托链，身份面随 identity 段退役、动态登记=L1 同轮硬面保留，与代码结构一致）；`_hold_qualification_ok` 三腿精确分派成立（代码实读：名字分支三腿 :296-298 = 保护集/registry/乙分支获取，硬闸 :299-300 core 档 / :301-305 protection 档 / :306-308 else；§2 拆 registry core 档腿、§3 随囤臂退役清剩余两腿——与「hold 类买入 = C1 核心 + protection_hoard」（:282 docstring）闭合）。
**但消费位枚举仍不全**：shop.py:925-926（未锁帧宽集买面名单 = 义务面 ∪ 保护集）、shop.py:1463-1470（序 4 死金压牌库 prio1 身份支）、shop.py:889-892（帧级身份读点）、shop.py:968-973（保护集持有关计数键）、cw_intention.py:1344（kernel 乙分支资格核 registry 排除）、mandate.py:770 + contracts.py:276（`core_single_card_buy_eligible` 门与契约登记，C1 支整段拆除后的跨文件死件）均不在任何拆除/改造行——按在册清单施工，dismantle §3 末条「`protection_membership` 函数退役前提由本段达成」仍不成立，且序 4 prio1 残腿（无星闸/全额退门，:1461-1470 实读）继续按身份买入，使「未锁定期不再自动囤非候选的四体系角色」（dismantle §3 行为申报）失实。详见 R3-02。

**R2-02（高·PriorityContext 缺持牌全量快照）｜ 已正确修复。**
priority-model §1 PriorityContext 首项即「持牌全量快照（角色名 → 该名全部副本星级列表；读源 = 备战位 ∪ 前后台一次只读取……聚合谓词均消费此快照，与池子过滤无关）」。读形态与现役同型可锚：`levelup._held_max_star`（:160-170，bench_units_of ∪ deployed_rows_of 按名聚合最高星）；档 3「名下无任何副本」的商店牌求值输入由此补齐；「池子过滤只决定输出、聚合看全量」与 §5 及 acquisition §2 步骤 5 三处同口径。

**R2-03（中·免费刷新 P1 豁免未申报）｜ 修复不完整（→R3-05）。**
定案方向正确且三文档接线一致：design §2.2 免费刷新声明「保留现行的 P1 豁免……P1 豁免语义照旧（11 号稿 §3:95）」——锚实读吻合（:95「免费刷新次数……不计入本判据但过目标可买检查」）；acquisition §6 免费刷新行「P1 豁免 + `refresh_warranted` 残余判据（P2 候选缺件 / 锁定星级目标，金线不适用）」；dismantle §1 shop.py 行「接 `refresh_warranted` 残余判据（三分派，接线内容 = 总纲 §2.2）」。技术可行复核：残余判据删除 :110/:132 两处 target_buyable 合取后自洽；免费分支现场有 `missing`/`stay_target_of` 输入（shop.py:2036-2038）。**残留**：行为申报以「P1 期免费刷」为名，锁定后「等级 < 带下界」（refresh.py:120-129 `stay_gate_upgrade_first`）与「星级目标全完成」（:117-119 `no_star_target`）帧的免费刷同从「照用」变「停用」——现行免费腿只查 target_buyable、无带/阶段门（shop.py:2027-2047 实读），同类行为变化未入申报面。详见 R3-05。

**R2-04（中·凑钱参数表池子选项与拍板矛盾）｜ 已正确修复。**
design §2.4 现文「（池子：备战位；目标语义：守线金额 / 跨过利息档 / 差价 / 一个空位——见 §2.7 拍板「场上不入卖出池」）」——「∪场上无关角色」旧口径已除，与 §2.7 及 acquisition §3（五场景池子全部 = 备战位）一致。（连带发现：行为申报面缺凑金收窄，为新发现 R3-04，不属于本条修复对象。）

**R2-05（低·「四步流程」计数错）｜ 已正确修复。**
design §2.6 席满买入行现文「§2.3 六步流程」；§23 流程与 acquisition §2 同为六步，计数一致。

**R2-06（低·core_* 计数三方不齐）｜ 已正确修复。**
design §2.5「实读字面量 15 处/计数键 11 个」与 dismantle §2「全仓 15 处、剔字段名 14，其中计数键 11 个」口径一致。本轮独立实测（pwsh 递归带引号 `core_*` 字面量去重）= **15 个去重（含字段名 core_chars）/剔字段名 14**；14 = 计数键 11 + 拒因键 `core_candidate_rejected` 1 + 买因/契约字符串 2（`core_single_card_buy`/`core_single_card_buy_eligible`）——与文档分解逐项对上（shop.py 写点 :482/:1889/:1899/:1901/:1913/:1915/:1918/:1943/:1945/:1955/:1957/:1959/:1962、sell_gate.py :157-158、contracts.py:276 全部落位）。

**R2-07（低·素材守卫层归属三处两说）｜ 修复不完整（→R3-06）。**
design §2.4（循环防线行含合成素材守卫）与 dismantle §4（素材守卫→循环防线层、占位件/一星口径→池子过滤层）已按统一口径；**priority-model §6 残留旧分组**：「物理谓词（占位件不可卖、素材守卫、一星全额退口径）保留，迁移至……池子过滤层」——素材守卫仍在池子过滤层名下。

**R2-08（低·退金表挂载错位）｜ 修复不完整（→R3-07）。**
dismantle §4 保留项表已改「退金表 → 凑钱触发的目标算术数据源（金额缺口计算；非档位判定输入）」✓；**design §2.1.1（「其查表项（退金表、概率表）继续作为档位判定的数据源」）与 priority-model §6（「其查表数据源（退金表、概率表）保留为档位判定数据源」）两处残留旧挂载**——八档谓词与全部子键（优先级序数/总星级数/单卡星/概率/星级）确无退金消费，旧挂载为失同步残留。

**R2-09（低·溢出达成谓词语义未定）｜ 修复不完整（→R3-03）。**
acquisition §3 溢出行已收窄「备战位（溢出 = 备战位计数超载，卖场上件不解溢出；上阵安置先行不变）」——与现行 `self_rescue` 场景池 = `POOL_BENCH_ONLY`（sell_candidates.py:173-175）、11 号稿 §4.0:129「仅备战席」一致，收窄即回到现行、无新增行为变化 ✓。**但 priority-model §5 未同步**：「溢出 = 全量 + 循环防线豁免保留」与 acquisition §3 直接矛盾；「全量」疑系把 §2.6/11 号稿「扩展面**真全量**」（指资格面 FACE_SELF_RESCUE 的全通道豁免，sell_candidates.py:112-114/:121）误读为池子口径。两详设件两答案 = 实现者需自行仲裁。详见 R3-03。

**R2-10（低·场景表列头不实）｜ 已正确修复。**
acquisition §3 列头改「场景（语义标签）」+ 说明「注册表键名以现行 SCENE_SPECS 键为准，键名映射随落地批键表登记」——与 SCENE_SPECS 实键（self_rescue/ore_make_room/shop_swap/session_funding/levelup_liquidate_prep/node_end_interest/deploy_swap/c1_make_room，:172-198）的关系已如实声明。

**R2-11（低·黑话残留）｜ 修复不完整（→R3-08）。**
「升星缺口」已按对照表消除（design §2.2 现文「还没升到目标星时……三分派判据」）✓；**残留**：「免费腾位顺序」仍在 design §2.4 触发表与 priority-model §5（对照表：腾位→空出备战位）；「缺件」仍在 design §2.2（「P2 未锁候选缺件」「P2 候选缺件或锁定星级目标为真」）、§2.3（「M2 缺件义务」）、§2.7、acquisition §6，未登记对照。（design §2.6「垫件谓词过滤」、dismantle §2「席满腾位支」属现行机制/被拆对象指认，按 §2.8 C1 行同款豁免理解，不计残留。）

**R2-12（低·待决清算不精确）｜ 已正确修复。**
§2.7 现文三项均有着落：溢出安置选牌规则 → acquisition §3.1（序列末位起取部署可接受者、`_deployable`（mandate.py:1857）+ 窗口谓词放行、紧急态例外辖域声明）✓；席满遍历状态切换 → acquisition §2 遍历状态切换段 ✓；部署输入供给方式 → PriorityContext 一次性装配 ✓；随机流实例 → StrategySession.rng（cw_strategy_session.py:130 实读）✓。

**R2-13（低·跨线/配方成员序数取值未定）｜ 已正确修复。**
priority-model §3 档 2 ①括注：「取值规则（此序数键为档 2/3/5 共用）：跨线成员取其命中各线中的最高优先（core 优先于非 core）；过渡配方成员迁移期统一取低优先级」——规则完备，跨线实例（花火同时属列车同行 core 与多线 shared，cw_comps.py:547/:561）可机械落值。

### 回归小结

| 判定 | 条目 |
|---|---|
| 已正确修复（7） | R2-02、R2-04、R2-05、R2-06、R2-10、R2-12、R2-13 |
| 修复不完整（6） | R2-01（→R3-02）、R2-03（→R3-05）、R2-07（→R3-06）、R2-08（→R3-07）、R2-09（→R3-03）、R2-11（→R3-08） |
| R2 发现本身错误 | 无——13 条主张本轮全部直调复核成立 |

---

## 二、首轮交叠条目抽查（B1/B5 及其他交叠面）

**B1（protection.py 幻影 + `_hold_qualification_ok` 漏拆）｜ 已闭合。**
R2 曾判「修复不完整→R2-01」（拆除范围标注过宽）。本轮复核 R2 返工后的现状：protection.py 幻影指向已无（dismantle §1 代码面仅 refresh.py/shop.py/刷新负结果记忆三项）；三腿分派精确无重复无遗漏——core 档腿归 §2（C1 对象）、保护集/hub 两腿归 §3 买侧（随囤臂与乙分支持有保护退役清理），与函数实结构（:296-308）一一对应。B1 本身不再构成问题；其下游残留即 R2-01 的 R3-02。

**B5（免费刷新判据接线缺口）｜ 已闭合。**
R2 曾判「修复不完整→R2-03」（接线成立但引入未申报行为变化）。本轮复核：定案「P1 豁免 + refresh_warranted 残余判据」已在 design §2.2 / acquisition §6 / dismantle §1 三处互相咬合，技术可行性与教义连续性均成立（B5 原判据缺口——「删完的免费分支 = 无条件白刷」——已消除）；R2-03 引出的问题经本轮返工已申报 P1 面，残留仅 R3-05 的申报面缺口。

**其余交叠条目复核（抽查）**：
- **A1（六序口径）**：design §2.2「买入六序判类（11 号稿 §1；六序之外的 C1 邻位支删除，dominance 段保留）」——与 11 号稿 :25「C1 名单核心卡支位次 = 第 7 邻位」及代码（C1 支 shop.py:1884-1962 为独立邻位段、dominance 发射 :2003 `dominance_buy` 在其后独立存在）吻合，仍正确。
- **A2（档 4 谓词与落档边界）**：档 4「非阵容成员 ∧ 费用档 == 当前升星目标实费档」+ None 分支；本轮重推演：达标成员（need_star ≥ 2）副本过档 3（有副本）/档 4（是成员）/档 5（need_star ≤ 1 不中）/档 6/7（最高星 ≥ 2 不中）→ 档 8，与总纲 §2.1 落档边界一致，仍正确。
- **A3（档 2 星级键）**：三键结构与「key 大者先卖」方向自洽，仍正确——但同族问题在档 6/7 上存在（见 R3-01，属 A3 修复时未外推的面，非 A3 回归）。
- **A4（DirectionView/PrepContext）**：四文档 grep DirectionView 零命中；PrepContext 四组字段锚全实（`line_members_view` :355/`direction_comp_of` :371、`opening_recipe_comp` mandate_state.py（refresh.py/委托链可锚）、`_deploy_window_blocked` entry.py:325、`_make_windowed_select_up` entry.py:391、`deploy_vacancy`/`deploy_cap`、GameState 为 dataclass 可手工构造 :2384），仍正确。
- **B3/B12（记忆键保留、免费刷新锚）**：`shop_refresh_blocked_memory_skip` 保留判定正确（金线置位 :2089、跳过计数 :2023 实读）；acquisition §6 锚「shop.py :2025-2047、target_buyable :2039」逐行精确，仍正确。
- **C4/C5/C6（黑塔申报、rng 锚、存量 changes/ 注释）**：黑塔 cost=1（cw_chars.py:110）、大黑塔线 need_star「黑塔: 3」（cw_comps.py:1098-1103）实读吻合；rng = cw_strategy_session.py:130 实读吻合；protection.py:3-5 changes/ 引用清理已登记 ✓（但同类清理未覆盖其他触达区文件——并入 R3-12）。

---

## 三、新发现清单（13 条：高 2 / 中 3 / 低 8）

### 高

**R3-01 ｜ 高 ｜ 核一·判据规格缺口（总纲 ↔ 唯一判据源失同步）｜ design.md §2.1 档 6.1/7.1 ↔ priority-model.md §3**
**档 6/7 的档内判别键：总纲声明「总星级数更多者保留」，priority-model 未承载，且其现有键在档 6/7 内恒常数、永不判别。**
- 总纲 §2.1：档 6「6.1 同优先级的，保留总星级数更多的」、档 7「7.1 同优先级的，保留总星级数更多的」。
- priority-model §3 档内排序键表：档 6/7 仅有「6 / 7 / 8 第二键 ｜ 星级（高者后卖）」一行，无第一键定义、无总星级数键。
- 双重矛盾：①两文档对同档内键给不出一致答案（priority-model 是接口契约 1 的「唯一排序判据源」，总纲 §2.1 自称「完整定义」）；②**星级键在档 6/7 内数学上恒空转**——档 6/7 谓词限定「名下最高星 < 2」（按名聚合），档内全部副本皆 1★，per-unit 星级键恒为 1，永不分档。而总星级数（= 副本计数，档 6/7 谓词保证全 1★ 时即为张数）恰是可判别键：同档两个万金油成员一张持有 2 张 1★、另一张持有 1 张，按 priority-model 现行键表完全同序落随机尾键——可能先卖已攒两张（距 2★ 更近）的成员，直接违反总纲 6.1/7.1 的声明语义。
- 修正方向：priority-model §3 为档 6/7 补第一键「总星级数（多者后卖；档 6/7 谓词下 = 副本计数）」；「星级」第二键对 6/7 恒常数，收窄为档 8 专属或注明空转。

**R3-02 ｜ 高 ｜ 核一 + 核三（R2-01 同类残留）｜ dismantle.md §2/§3、design.md §2.5**
**买侧身份消费位枚举仍不全：按在册清单施工则行为申报失实、函数退役前提仍不成立。**
- 在册清单（design §2.5 买面行 + dismantle §3 买侧七项）之外，实读定位到未登记的活消费位：
  1. **shop.py:925-926——未锁帧宽集买面名单构造**：`buy_members = obligation_members ∪ _protection`（:908-926 注释自述「宽集买面名单 = 义务面 ∪ 保护集」；该宽集为前迭代 deliberate 设计，见 changes/2026-10-15-unified-protection-set/landing.md「M2b 保持宽集」行）。囤臂退役后宽集不收窄 → **M2b 合成完成买入域仍含保护集成员**（:1342 `for m in buy_members` 直吃宽集）；
  2. **shop.py:1463-1470——序 4 死金压牌库 prio1 身份支**：`_hit = (name in CORE_SINGLE_CARD_REGISTRY or name in _protection)`，无星闸/全额退门（prio2 的结构门不适用）——死金帧继续按身份**新购**保护集成员，直接违反「未锁定期不再自动囤非候选的四体系角色」申报；亦是「registry 角色回普通排序」（design §2.5 row 2）无执行承载的买面残留；
  3. **shop.py:889-892——帧级身份读点**（注释自述「供 ②(b) 保护档/计数键/拒因键消费」）与 **shop.py:968-973——保护集持有关计数键**：随 1/2 的去向需同步处置；
  4. **cw_intention.py:1344——kernel 乙分支资格核的 registry 排除**（`if name in CORE_SINGLE_CARD_REGISTRY: continue`，枢纽资格核 :1320-1344）：「回普通排序」在 kernel 意图层（枢纽期权候选资格）的含义未定——registry 成员是否恢复枢纽资格，无任何一行拍板；
  5. **mandate.py:770 `core_single_card_buy_eligible` + contracts.py:276-277 契约登记**：C1 支（shop.py:1921-1924 消费）整段拆除后的跨文件死件，不在 §2「shop.py 直购支整段」的文件面内。
- 连带：dismantle §3 末条「`protection.py protection_membership` 函数退役前提由本段达成」在上列位未处置时仍不成立（与 R2-01 被判高的「前提落空」同构）；11 号稿 :42 的 Z1 行尚引用已消亡的 `cw_card_identity.sell_hold_exclusion_names`（该函数已不存在，cw_card_identity.py 现役唯一职责 = `is_engine_piece`），Z1 身份面退役的文档面未点名该行（现仅靠「其他正本引用面随正本更新批清点」兜底）。
- 修正方向：上列位逐项登记（退役或拍板保留 + 理由）；宽集构造拍板收窄义务面或显式声明 M2b/M6 域保留口径；prio1 身份腿随名单退役（registry/保护集角色落 prio2 结构门）；cw_intention 枢纽资格的 registry 排除去留单独拍板；11 号稿 :42 行补入 §3 文档面。

### 中

**R3-03 ｜ 中 ｜ 核一·两详设件池子口径矛盾（R2-09 返工引入的失同步）｜ priority-model.md §5 ↔ acquisition-and-sell.md §3**
- priority-model §5：「池子过滤在 sell_order 之前（店内场景 = 仅备战位；凑钱场景 = 参数表声明的池子；**溢出 = 全量** + 循环防线豁免保留）」；acquisition §3 溢出行：「**备战位**（溢出 = 备战位计数超载，卖场上件不解溢出）」。同一边输入两个答案。
- 根因可辨：「全量」系把 §2.6/11 号稿 §4.0「扩展面**真全量**」误读为池子口径——「真全量」指资格面（FACE_SELF_RESCUE = P78 仲裁族全通道豁免、真全量持有，sell_candidates.py:112-114/:121；11 号稿 :129），非候选池（现行池 = POOL_BENCH_ONLY，:173-175）。按 priority-model 实现会扩池（引入未申报行为变化），按 acquisition 实现则违反本篇。
- 修正方向：priority-model §5 改「溢出 = 备战位（与 acquisition §3 一致）；豁免 = 资格面全通道放行，非池子扩面」。

**R3-04 ｜ 中 ｜ 核一·行为变化申报面缺凑金收窄 ｜ design.md §2.7 ↔ acquisition-and-sell.md §3**
- §2.7 拍板「凑钱场景统一按优先级，场上不入卖出池——现行「凑金/凑息可卖场上无关角色」形态废止，行为变化已申报（**部分帧凑息候选池收窄**）」——申报只点名凑息。
- 实锚：升级凑金场景现行池 = `POOL_BENCH_FIELD_IRRELEVANT`（SCENE_SPECS 'levelup_liquidate_prep'，sell_candidates.py:185-188；11 号稿 §4.0:133 场景表「备战席 ∪ 场上无关角色」、§2:59「与凑金场景可卖池〔备战席 ∪ 场上无关角色，§4.0〕」两处明载）。收窄到备战位后，凑金在途帧唯一可行件为场上无关角色时凑不齐 → 整批推迟（`levelup_fund_line_defer`）——真实行为变化，未申报。
- 修正方向：§2.7 申报句扩为「凑息/凑金候选池收窄」（或并列点名两场景）。

**R3-05 ｜ 中 ｜ 核一·行为变化申报面缺锁定后帧（R2-03 残留）｜ design.md §2.2 免费刷新声明**
- 申报句「P1 期免费刷从『无条件照用』收窄为『候选缺件/星级目标驱动』」以 P1 为名。实锚：现行免费腿只查 target_buyable，无阶段/带/目标门（shop.py:2027-2047）；接 `refresh_warranted` 残余判据后，锁定后「等级 < 带下界」（refresh.py:120-129，`stay_gate_upgrade_first` 拒支）与「星级目标全完成」（:117-119，`no_star_target`）帧的免费刷同从「照用（次数保留）」变「停用（次数保留不耗）」——与 P1 收窄同源的判据统一行为变化，未在申报面内。
- 修正方向：申报句去掉「P1 期」限定（改「免费刷从『无条件照用』收窄为判据驱动——P1 开局无候选成型帧、锁定后带外帧、无星级目标帧不再白刷」）。

### 低

**R3-06 ｜ 低 ｜ 核二·规则 4（R2-07 修复不完整）｜ priority-model.md §6**
「物理谓词（占位件不可卖、**素材守卫**、一星全额退口径）保留，迁移至新卖出判据件的池子过滤层」——素材守卫按统一口径归循环防线层（design §2.4、dismantle §4 已改），本处残留旧分组。修正：素材守卫移出该句。

**R3-07 ｜ 低 ｜ 核二·规则 4（R2-08 修复不完整）｜ design.md §2.1.1、priority-model.md §6**
两处仍写「查表项（退金表、概率表）继续/保留为档位判定的数据源」——退金表已定案挂「凑钱触发目标算术数据源、非档位判定输入」（dismantle §4）。修正：两处同步。

**R3-08 ｜ 低 ｜ 核二·规则 3/§2.8（R2-11 修复不完整）｜ design.md §2.2/§2.4、priority-model.md §5**
「免费腾位顺序」残留 design §2.4 与 priority-model §5；「缺件」残留 design §2.2（×2）/§2.3/§2.7 与 acquisition §6，未登记对照。修正：腾位改直白词（如「免费安置序」）；缺件登记对照或换词。

**R3-09 ｜ 低 ｜ 核一·遥测键归类错 ｜ dismantle.md §3 遥测键面**
`fuel_victim_protect_demoted` 被列入「保护件阻断类键……等身份保护语义键」删/改清单——该键实为 **T3 同轮保留（stall_protect defer）末位牺牲序**的卖出销账分键（mandate.py:431-436「集合内名字降为候选末位……消费端命中时分键 fuel_victim_protect_demoted 并卖出销账」），属保留的循环防线（同轮买入禁卖族，dismantle §4 保留行）语义，非身份保护键。归类错会诱导落地批误删在役键。修正：移出该清单（或标注「核对后保留」）。

**R3-10 ｜ 低 ｜ 核一·场景注册表死行未登记 ｜ dismantle.md §2、acquisition-and-sell.md §3**
SCENE_SPECS 的 `'c1_make_room'`（:195-197，C1 恒买席满腾位）与 `'shop_swap'`（:179-181，店内置换账）两场景规格随 C1 支拆除/置换账整段替换后失去消费位——既不在 acquisition §3 五场景重写表，也不在 dismantle §2 代码面，落地批留下死规格行或自行拍板。修正：dismantle §2 补登记两行随批退役。

**R3-11 ｜ 低 ｜ 核一·依据表述不精确 ｜ design.md §2.3 M2 段、§2.1 档 8**
①「M2 缺件义务……**缺件是档 2**」——按八档定义，未持缺件 = 档 3（名下无任何副本）、星级缺口件 = 档 2（shop.py:949-953 missing = 未持 ∪ 星级缺口，横跨两档）；论证（通常不在末位）不受影响，档号应改「档 2/3」。②档 8 概率键锚静态表 `refresh_prob`，未声明投资环境轮岗（每备战阶段随机一费用档概率翻倍，cw_shop_odds.py:69-71）帧的实况概率偏离——确定性不受影响，属排序质量观察项。修正：①档号改 2/3；②档 8 键注明「基线概率表口径，轮岗翻倍不感知」。

**R3-12 ｜ 低 ｜ 核二·引用寿命 ｜ design.md §2.10、dismantle.md §1/§2/§3**
①seed=20261022 出处锚指向并行迭代 `changes/2026-10-29-sim-flow-fidelity/README.md`（§5:129 实读存在）——changes/ 互引寿命注意（R2 B6 附注已提示，返工未脱钩）；②C6 修复只登记了 protection.py:3-5 的存量 changes/ 注释清理，本轮触达区同类的还有：shop.py:2009-2010（引 `details/shop-buy-reform.md §3`）、shop.py:908/:1464-1468（引「design §2.2/§2.4」= unified-protection-set 篇，档位表实存于该篇 :82）、sell_gate.py:237/:283（同引）——拆除批触及这些行时注释清理未登记。修正：seed 锚改「sim 驱动参数」语义描述脱钩；触达区注释清理登记，或显式声明不改。

**R3-13 ｜ 低 ｜ 核一·表述与档结构不符 ｜ acquisition-and-sell.md §5**
「旧线成员在后续任何卖出触发的序列中**自然落末位（档 8）**渐进流出」——旧线成员中的万金油（千冶·刃/三月七/花火/星期日，CROSS_LINE_KEEP_NAMES protection.py:64-66）落**档 6**、羁绊成员落**档 7**（未到两星期间），非恒档 8；「全线留用层」语义本身自洽，错在档号表述（design §2.6 同行「整体降档后按序列清算」较模糊、可容）。修正：改「按序列落位渐进流出（万金油/羁绊成员在档 6/7 保护期内不流出）」。

---

## 四、核对覆盖声明

**实读文件**：
- 规范正本：iteration-design.md 全文（§5 四条硬规则/§7 三核为判定框架）。
- 攻击对象：design.md、details/priority-model.md、details/acquisition-and-sell.md、details/dismantle.md、README.md、attack.md、attack-r2.md 全文。
- 代码直读段：sell_gate.py :200-349（register_launch/_hold_qualification_ok/HUB_ACQUIRED）、:880-999（identity_exclusions/sell_exclusions 头）、:1020-1154（funding_hold_fallback/sell_hold_exclusions/empty_board_sell_blocked）；shop.py :330-395（拒因快照函数）、:440-514（拒因标签分支/count_material_stale）、:855-973（序 1 名单解析/宽集构造/缺口集/保护计数键）、:1218-1262（_buy_view/_shop_candidates）、:1322-1416（M2b/囤货臂全段）、:1440-1500（序 4 ②(b) prio0/1/2）、:1840-2102（C1 支全段/dominance/刷新链三组件+免费分支+负结果记忆+收工）；criteria/refresh.py 全文；criteria/levelup.py :160-259（unfinished_star_targets/stay_target_of/_held_max_star）；criteria/sell.py :165-306（凑息档序/危局阀桶两处 bench_effect）；criteria/sell_candidates.py :100-289（池/面闭集、SCENE_SPECS 全表、价值函数三项、垫件谓词 :402-440）；mandate.py :380-509（fuel_sell_candidates 全函数+T3 段头）、:1262-1306（死锁计数键段）；entry.py :750-814（_bench_liquid_gold/资金线门）、:1150-1219（凑息阻断+step7 头）；protection.py :1-70；kernel/cw_card_identity.py 全文；kernel/cw_strategy_session.py :110-139；kernel/cw_comps.py :1095-1108（大黑塔线 need_star）+ grep 锚（core_chars:94/shared_chars:103/need_star:210/REGISTRY:485/花火跨线:547/:561）；data/cw_shop_odds.py :40-74（refresh_prob:61/轮岗注释）；data/cw_factions.py :55-104（四羁绊 :61/:81/:90/:96）；data/cw_chars.py :104-115（黑塔 :110）；kernel/cw_game_state.py 结构 grep（GameState :2384 dataclass、Unit :519、BenchSlot :671）。
- 代码锚 grep 实证：protection_membership 全仓 23 处逐点定位、CORE_SINGLE_CARD_REGISTRY 全仓 30 处、乙分支/HUB_ACQUIRED 全仓 30 处、buy_members/_buy_view 消费位 21 处、`def line_members_view|direction_comp_of|_deployable|_deploy_window_blocked|_make_windowed_select_up` 定位、core_* 带引号字面量 pwsh 递归计数（15 去重/剔字段名 14/计数键 11+拒因 1+买因契约 2）。
- 正本文档：11 号稿 :10-69（六序位次 :25、C1 支 :27-35、四规则 :37-43、Z1 :42、M2b :45）、:85-144（§3 刷新链 :89-105、免费腿 :95、发射段/负结果记忆 :105、§4.0 场景表 :127-136、价值函数头 :138-144）；01 号稿 :84/:86/:147；20 号稿 :66；23 号稿 :10/:20（grep 命中实读）；changes/2026-10-29-sim-flow-fidelity/README.md :110-131（§5 同 seed 冒烟 :129、批 A 实施态）；changes/2026-10-15-unified-protection-set/design.md :33/:82（档位表）、landing.md :26（宽集/prio1 deliberate 证据）。
- 症状实证：.debug/currency_war/deep_review/g_20261029_084447.md :2390/:2392（2-1 置换 value 平局拒绝帧）、:3411（候选 B C1 囤积）、:3629/:3631（2-4 target_unbuyable）、:4201-4250（候选清单/全景）。
- 本轮迭代 README 进度态核对（对抗审中/landing 待起稿，与前两轮「不构成流程发现」判定一致，仍未对 landing 展开）。

**未覆盖（明示）**：landing.md（未起稿）；sim 子系统代码；22/24/30/31 号稿全文（仅被引行与工序锚）；proofs（沿用前两轮 P49/P78 核对结论，本轮未被返工触碰）；复盘报告其余章节（沿用前两轮逐帧核对结论，本轮仅复核被引关键帧）；mandate.py/entry.py 其余段落（十段结构沿用前两轮核对）。

**统计**：R2 回归 13 条（7 正确 / 6 不完整 / 0 R2 误报）+ 首轮交叠抽查 9 面（B1/B5/A1/A2/A3/A4/B3/B12/C4-C6，全部成立或已闭合）+ 新发现 13 条（高 2 / 中 3 / 低 8），全部经权威源直调证实，无推测性条目。R3-01/R3-02 为定稿阻断项。
