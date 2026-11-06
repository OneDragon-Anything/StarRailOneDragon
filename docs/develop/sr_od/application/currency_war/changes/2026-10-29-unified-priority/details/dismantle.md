# 拆除清单（详设）

## 问题与约束

本篇是总纲 §2.5 拆除清单的执行规格。约束：
- **新先于旧拆**（总纲 §2.9 接口契约 3）：统一序列判据件与获取流程落地并接管消费点之后，才允许拆除旧判据（防行为真空）；
- 每个拆除项三面清点：代码面 / 遥测键面 / 文档面；文档面 = 正本更新批（landing 末阶段）执行，本篇只登记清单；
- 保留项（循环防线、物理谓词、万金油名单常量、概率/退金表）逐项声明「不拆」，防过度拆除。

## 方案（按拆除对象）

### 1. 刷新预测门

- **代码面**：
  - `criteria/refresh.py`：`target_buyable` 函数整删；`refresh_warranted` 中锁定支/未锁支的两处合取调用删除（判据收敛为三分派）；docstring 同步；
  - `shop.py`：`target_unbuyable` 消费分支（:2058）删除；免费刷新分支（:2025-2047）的「目标可买」检查删除后改**无条件刷**【拍，总纲 §2.2 免费刷新声明——无阶段/带/目标/目标可买任何门，免费次数在册即刷】；
  - `shop.py` 拒因分类的 registry 分支（:483，`... if name in CORE_SINGLE_CARD_REGISTRY else 'non_line'`）：C1 支拆除后为孤儿计数分支（拒因键已删仍会被非 C1 拒帧触发），随批清除；
  - 刷新负结果记忆（`StrategyState.refresh_blocked`）：「目标不可买」置位分支删除（refresh_warranted 拒因收敛后该分支无对象）；金线不足分支照旧置位（:2085-2089 现行），记忆机制继续服役；**通用键比对清值（:2019-2021）保留不动**——它是记忆键的常规比对清值路径，非「目标不可买」专属；
  - 触达区存量 changes/ 注释清理（随触及行批处理）：shop.py:2009-2010（引 `details/shop-buy-reform.md §3`）、shop.py:908/:1464-1468（引 unified-protection-set 篇 design §2.2/§2.4）、sell_gate.py:237/:283（同引）、cw_intention.py:1320-1333（hub_option_names docstring——**随 hub 死链拆除整函数退役**，docstring 定理引用一并消失）；
- **遥测键面**：`target_unbuyable` 删除；`shop_refresh_blocked_memory_skip` **保留**（金线分支的跳过计数仍在役）；
- **文档面**：11 号稿 §3（「目标可买三腿并集」整节删除，判据组件表述收敛三分派；「配套语义」段同步）；01 号稿判据组件行与组件表（:84/:86/:147 三腿引用）；20 号稿刷新行（:66）；23 号稿 §1。

### 2. 单卡核心囤积规则

- **代码面**：
  - `shop.py`：单卡核心直购支整段（锁定分支/未锁定恒买分支/席满腾位支）；C1 过滤条件（:1884-1887）；
  - `sell_gate.py`：`identity_exclusions` 的 `excl |= set(CORE_SINGLE_CARD_REGISTRY)` 行（:929）；**`_hold_qualification_ok` 的 registry core 档腿（:296-308 内 core 分支，C1 hold 登记资格面「registry 核心 → core 档恒买无星闸」）**——名字分支的另两腿（保护集档 / hub 档）服务囤臂与乙分支 hold 登记，不在本对象拆除（随 §3 买侧退役批处理）；
  - `sell_gate.py` `funding_hold_fallback` 内 registry 核心并集（:1071，随 §3 整删覆盖）；
  - `mandate.py` `core_single_card_buy_eligible`（:770）+ `contracts.py` 契约登记（:276-277）——C1 支（shop.py:1921-1924 消费）拆除后的跨文件死件，随批清除；
  - 场景注册表死行：SCENE_SPECS 的 `'c1_make_room'`（:195-197，C1 恒买席满腾位）与 `'shop_swap'`（:179-181，店内置换账）——前者随 C1 支、后者随置换账整段替换失去消费位，随批退役；
  - registry 常量本身（`cw_comps.CORE_SINGLE_CARD_REGISTRY`）**保留**（数据仍被档判定/知识层引用与否由落地批核：无消费面则常量随批退役，有知识层引用则保留——核对项）；
- **遥测键面**：core_* 出口键族（core_* 前缀字面量全仓 15 处、剔字段名 14，其中计数键 11 个、其余为买因/契约字符串；落地批逐一清点按族前缀清理）+ `core_numeric_fail_closed` + 拒因键 `core_candidate_rejected`；
- **文档面**：11 号稿 §1「单卡核心卡直购支配性支」整节、「恒买腾位早期经济纪律四规则」中 C1 相关行、§4.0 场景表「C1 恒买席满腾位」行。

### 3. 静态不许卖名单（卖出侧身份段）与买面身份保护判据

- **代码面（卖侧）**：
  - `sell_gate.py` `identity_exclusions`：身份段五源删除（义务基座 / `protection_membership` / registry 核心 / `hub_acquired_names_of` / `terminal_key_label_hit_names`）——函数收缩为窗口段 + 通道对价段（或与 `sell_exclusions` 合并简化，落地批定）；
  - `mandate.py` `fuel_sell_candidates`：`exclude_names` 装配与 `zero_overlap` 门删除；**`bench_effect_qualified` 检查删除**（:488——该谓词共四处消费位：评估器/凑息档序/危局阀桶随场景重写退役，此处为第四处，显式拆除）；**一星门删除**（总纲 §2.4「不设仅一星代理过滤」拍板——凑钱卖出按统一序列取用，一星全额退口径归预算投影/凑钱目标算术，非卖出资格过滤）；**保留**：占位件恒拒、合成素材守卫（G-S1）、空板止损守卫（`empty_board_sell_blocked`）与 `merge_guard_release` 释放集旁路（:454-459，循环防线语义）；
  - `sell_gate.py` `funding_hold_fallback`（P78-5 兜底豁免）整删（无对象，含 :1071 registry 并集）；
  - `protection.py` `protection_membership`：**卖侧+买侧消费面全退役后函数退役**（买侧清单见下）；`CROSS_LINE_KEEP_NAMES` **保留**（档 6 数据源）；protection.py 模块头引用 changes/ 路径的注释（:3-5 附近，存量违例）随本批触及一并清理；
  - 旧卖出评估器价值函数（`criteria/sell_candidates.py`：变现价+再遇期权+合成进度口径、`MERGE_PROGRESS_X2` 登记槽）退役，场景注册表重写为统一序列消费（acquisition-and-sell §3）；`criteria/sell.py` 的凑息档序/危局阀桶两处 `bench_effect_qualified` 消费随场景重写退役；
- **代码面（买侧，与卖侧同批——只拆卖面则囤臂继续买、序列按低档即卖 = 买卖空转，总纲 §2.5 买面行）**：
  - `shop.py` protection_hoard 囤货臂（:1366-1394）**整段退役**——非候选的四体系成员期权囤货，存在前提（囤换线期权）与单卡核心囤积同样被「锁后不换线」消亡，随 C1 同逻辑退役（行为变化申报 = 总纲 §2.5：未锁定期不再自动囤非候选的四体系角色）；
  - `shop.py` 未锁帧宽集买面名单构造（:925-926，`buy_members = obligation_members ∪ _protection`）：**宽集收窄为义务面**——原 deliberate 保留宽集的理由 = 保护集囤货语义（changes/2026-10-15-unified-protection-set/landing.md「M2b 保持宽集」；该引用为迭代工件寿命——正本化依据收编于统一保护集 design 篇），囤臂退役后前提消亡；M2b/序 4 域随窄集自动收敛；
  - `shop.py` 义务面并集构造段（:906-923，含 :916 `CROSS_LINE_KEEP_NAMES` 项）：**随 K 源切换重建**【R5-01 连带】——万金油项删除（万金油退出义务买入面，总纲 §2.7 申报②）、配方成员项并入（两态名单未锁定支，总纲 §2.1）、k_members 项随 kernel 甲臂源退役改由策略层候选快照并集承载（R5-01 方向②）；
  - `shop.py` 序 4 死金压牌库 prio1 身份支（:1463-1470，`name ∈ registry ∪ _protection` 无星闸腿）：**删除**——registry/保护集角色落 prio2 结构门（费用档结构门），「registry 角色回普通排序」的买面承载；
  - `shop.py` 帧级身份读点（:889-892，供 ②(b) 保护档/计数键/拒因键消费）与保护集持有关计数键（:968-973）：随上两项处置（删或改窄集口径，落地批按残余消费定）；
  - `cw_intention.py` **hub 死链完整拆除**（核实 = 三段全断：`hub_option_names`（:1319-1348，含 :1344 registry 排除行）唯一消费 = `no_target_arms` :1442 的 hubs 装配；`NoTargetArms.hub_names` 字段（:1428）无真实读者——商店域唯一调用点 shop.py:1019 显式传 `frozenset()` 空集，拒因标签分支（:459-464）永不可达；`hoard_target_set` :1490 只消费 arms.direction，hub_names 被忽略）：
    - `hub_option_names` 函数整删（含 :1344 排除行）；
    - `structural_candidate_lines`（:1303-1316）与 `_NO_TARGET_HUB_MIN_COVER`（:1297-1300）整删——唯一消费均为 hub_option_names；
    - `NoTargetArms.hub_names` 字段（:1428）与 `no_target_arms` 的 hubs 装配（:1442/:1447-1449）删除；
    - 三分支判据段注释（:1277-1290）与模块头（:12/:95）、`hoard_target_set`/`k_empty_window_fallback` 注释（:1464-1466/:1489/:1517）的乙分支表述同步收敛为「甲/丙两分支」；
    - 依据 = hub 域与候选体系重叠（多线复用件 ∈ 候选线并集 → 档 2/3/5 承载买入与保留），通道经 12 号稿「动作并入序 1」后空心化，死链清理；
    - `shop.py` 侧联动：`shop_unbought_reasons` 的 `hub_names` 参数（:314）与 docstring 乙分支段（:344-347）、`'hub_option'` 标签分支（:459-464，落 non_line）、调用点空集实参（:1019）删除；**行为申报**：`'hub_option'` 拒因标签退役 = 观测面变化（生产中零出现——死键清理，无观测损失）；
    - `mandate.py` `core_single_card_buy_eligible`（:770）与 `contracts.py` 契约登记（:276-277）跨文件死件随批清除（§2）；
  - `entry.py` 攒批资金资格面 protection 消费（:782）：改由统一序列/凑钱判据件承载；
  - `entry.py` 节末凑息阻断（:1165-1207）：凑息身份排除退役（凑息 = 部署重排后全局面序列按统一优先级取用，无身份排除、无池子过滤）；
  - `shop.py`（:374/:1196-1205）protection 消费位：按所在买入序分支迁移（囤臂删除后无保护集分支，序 1 义务面判定由名单读口承载）；
  - `mandate.py` 死锁计数键（:1283-1287）：随囤货臂退役；
  - Z1 凑息排除集（`sell_hold_exclusions` 身份面 = 保护集 ∪ registry 核心）：身份面退役，动态买入登记（②(b)）保留；
  - `_hold_qualification_ok` 名字分支的剩余两腿（保护集档 / hub 档）：随囤臂与乙分支持有保护退役后清理（§2 已拆 core 档腿）；
  - `protection.py` `protection_membership` 函数退役前提由本段达成；
- **代码面（kernel 甲臂兜底囤货退役，R5-01 用户裁定方向②——K 目标未锁期源切换）**：
  - `kernel/cw_intention.py` `no_target_arms` 的甲分支判活路径（:1436-1451，unlocked p2plus 带的方向化囤货）与 `hoard_target_set` 的 `fallback_arm_a` 路径（:1489-1497）：**退役**——未锁无目标帧的囤货方向不再取机器判活方向（非候选 top3 的方向囤其成员无兑现通道，与囤货臂/C1 同逻辑）；**K 目标未锁期来源切换为候选快照三线成员并集 ∪ 配方成员**（与优先级档 2/3/5 名单同源，买面与优先级面统一）；
  - `k_empty_window_fallback`（:1500-1527）p2plus 带同步收窄：unlocked = 保利息缺省（丙分支语义，合法空集证据链 `K_FALLBACK_SOURCE_THREE_ARM`/contracts 带维度契约同步修订）；锁定分带保留（在役）；weak/demoted_endgame 分带为**不可达死分支**（phase 值域注释 cw_intention.py:117/:159——weak/demoted 恒先于 unlocked 出域），随函数简化自然消失、非在役判据；
  - 甲分支定理 A 证明本体是否随路径退役由落地批核（判据死则证明随迁——核对项；若策略层候选体系成为未锁期判据单一源，定理 A 的「机器强锁门逐字」论证对象消亡）；
  - 行为申报 = 总纲 §2.7：弱势局未锁无目标帧从「按机器方向囤」变「保利息缺省」；
- **遥测键面**：保护件阻断类键（`interest_round_protected_block`、`protection_member_rejected` 拒因分支等身份保护语义键）——逐键核消费位后删/改（落地批键表）；`fuel_victim_protect_demoted` **保留**（实为 T3 同轮保留防线的卖出销账分键，mandate.py:431-436，非身份保护键——核对后归循环防线保留清单）；`'hub_option'` 拒因标签与 `hub_option_*` 计数键——**生产中零出现**（调用点传空集），随 hub 死链拆除（历史已停写键不另清理）；
- **数学证明面**（hub 死链的证明退役 + 甲臂退役的证明处置，用户裁定）：
  - `proofs/p86-proof-batch.md`：**乙分支证明章删除**（定理 B5〔registry 身份排除结构性必要〕、定理 B2/B2-3〔乙分支解耦独立性〕、§3.2 乙分支资格核定义段及其依赖）——证明对象（hub 通道）为死链，证明随之退役；**丙分支命题 C 保留**（在役判据：保利息缺省）；**甲分支定理 A：随甲臂路径退役处置**（判据死则证明随迁，落地批核对项——见上买侧段）；
  - `proofs/math_proofs.md` P86 索引行（按内容定位——「P86 无目标期资金配置判据(命题批)」行；正本在并行证明史清理批中行号漂移，禁行号锚）：乙臂表述改为退役注记（**甲臂随路径退役处置〔核对项，见本节买侧段〕；丙臂在役保留，索引行不整删——丙仍被引用**）；
  - **定理 M / 引理 Z 的乙分支引用修订**：引理 Z（活跃域 = 位面 2）与定理 M 中引用乙分支臂的段落，随乙分支退役改为「乙分支已退役（2026-10-29 统一优先级迭代）」注记或删去该引用——p86-proof-batch.md 与 P86 正本同步；
  - `proofs/p86-no-target-period-fund-allocation.md`（P86 正本）：乙分支节退役标记（正本更新批执行）；
  - 代码注释面的定理引用清理：`cw_intention.py` hub 段 docstring 的「定理 B5/B2/B2-3」引用随函数删除消失；`:1285-1290` 三分支注释的乙分支行删除；shop.py/criteria/contracts.py 中 P86 乙分支证明批引用（contracts.py:44/:48/:78/:129 为带维度扩展在役引用，**保留**——仅乙分支相关引用清理，落地批逐条核）；
- **文档面**：11 号稿 §4.1 卖出资格仲裁（P78 装配 A 身份段语义、P78-5 兜底豁免节）；**11 号稿 :42 Z1 行**（尚引用已消亡的 `cw_card_identity.sell_hold_exclusion_names`——该函数现役唯一职责 = `is_engine_piece`，引用面随 Z1 身份面退役修订）；12 号稿 §1.2 囤积纪律（保护集囤货面语义随囤货臂退役修订）、**12 号稿 §4 hub 数据面表述**（「保留为评估数据面」随死链拆除修订）；统一保护集 design 篇的退役标记（该篇路径见 protection.py 模块头现行引用，属 changes/ 迭代文档——落地批按实际在位情况处理，引用寿命注意）；protection 相关的其他正本引用面随正本更新批清点。

### 4. 保留项声明（不拆）

| 保留对象 | 去向 |
|---|---|
| 同轮买入禁卖（窗口段）、种子年龄豁免、合成素材守卫（G-S1） | 新卖出判据件的循环防线层（acquisition-and-sell §3） |
| 空板止损守卫（`empty_board_sell_blocked`）、`merge_guard_release` 释放集旁路 | fuel 通道保留结构（§3 代码面） |
| 占位件不可卖谓词 | 池子过滤层 |
| 一星全额退口径 | 预算投影/凑钱目标算术（金额缺口计算用，非卖出资格过滤——总纲 §2.4「不设仅一星代理过滤」） |
| `CROSS_LINE_KEEP_NAMES` | 档 6 数据源（protection.py 保留该常量） |
| 退金表 | 凑钱触发的目标算术数据源（金额缺口计算；非档位判定输入） |
| 概率表 | 档 8 分档数据源 |
| `unfinished_star_targets` / `stay_target_of` | 档 2/4 判定单一源 |
| 溢出自救的循环防线豁免、上阵安置先行序 | 溢出触发场景（现行保留） |
| `shop_refresh_blocked_memory_skip` 计数键 | 金线分支记忆语义（§1 遥测键面） |

### 5. 拆除顺序（落地批内）

```
新判据件落地（priority.py + 判据件） → 消费点逐场景切换（每场景切换独立可验收）
→ 旧判据删除（本篇 §1-3 按对象） → 遥测键清理 → 文档正本更新（landing 末阶段）
```

每步切换后跑 L1（受影响子集）；全量拆除完成跑 L3 + 单帧断言集（总纲 §2.10）。

## 关键取舍

- **registry 常量去留挂核对**：拆除后若 `CORE_SINGLE_CARD_REGISTRY` 无生产消费面则随批退役、有知识层引用则保留——不在设计期拍死（引用面核对归落地批）。
- **文档面拆除分散在正本更新批 vs 随代码批**：正本更新批集中执行（landing 固定末阶段）——代码批只改代码注释，正本文档一次性与实现对齐，防中间态文档（正文 as-built 无状态纪律）。
- **评估器场景框架保留**：SCENE_SPECS 参数化骨架仍适配三触发模型（变的是资格面与排序源），推倒重写无增益。
