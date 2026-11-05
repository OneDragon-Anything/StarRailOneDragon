# equip-taboos-retirement 迭代设计（总纲）

## 0. 元信息

- 迭代目标：`Comp.equip_taboos` 整字段退役（用户裁定，2026-11-05 字段冗余排查会话：按 key_items 退役标准——统一策略机器不消费的知识登记即特殊逻辑通道，equip_taboos 是装备主链外唯一的此类残件；本篇为该裁定的完整设计）。
- 状态：定稿（对抗轮合并——预演编排者自审 3 点 + 外部 subagent 报告 7 点〔阻断 1/应修 3/可选 3,处置明细见 attack.md〕；A1 阻断项〔p42_check.py 消费遗漏〕已随返工批修复）。
- 文档清单：（无详设——单文档方案，本篇即完整设计）。

## 1. 问题与动机

- 现状症状（三条，均为可复核的存量事实）：
  1. **全库唯一消费点产出恒等空集**：生产消费仅 `cw_intention._line_hoard`（`taboos = set(comp.equip_taboos)` / `equips = {e for e in derive_key_equips(comp) if e not in taboos}`）——对唯一非空套（万敌单C）实测：`equip_taboos = ["护盾件(类)", "以牙还牙甲", "掩体生成枪"]` 与 `derive_key_equips(万敌) = [火力风暴潮, 热血沸腾拳, 绝对热量, 高周波电锯]` **零交集**，排除恒空。复核口径（一次性脚本不入仓，判定式即持久口径）：`[e for e in derive_key_equips(c) if e in set(c.equip_taboos)]` 全库恒空。
  2. **消费形态本身是空转设计**：该消费 =「该买清单（equip_assign 投影）− 不该买清单（taboos）」——两域**天然不相交**（同一件既在某套到人配方里又在该套禁买清单里 = 自相矛盾数据）。排除非空只可能来自数据错误，正常数据下这一步从 C4 契约时代起就是恒等变换。P42 验证点⑨已把「taboo ∉ key_equips」登记为**删域一致性**（阵容注册表一致性断言）——即「恒空」早被活证明当作一致性事实引用，反证该消费点从不承载行为。
  3. **类级条目无解析器**：docstring 声明「类级禁忌如『护盾件(类)』由买侧/装备层消费，本层不展开」——买侧/装备层（购买/合成/穿戴三道门）全库无任何代码解析 `equip_taboos` 或「(类)」后缀，声明悬空（多轮排查已确认）。三条数据行全部零行为：类级 1 行无解析器，具名 2 行不在投影域。
- 根因归层：**语义层**。「禁忌」知识是真实的阵容内在机制冲突（万敌燃血禁盾——受盾只转微回血 = 负资产），但从登记起就没有接入任何能改变行为的机器：装备决策主链（购买/合成/穿戴三道统一门）不读它，唯一挂点选在了天然不相交的囤货投影域上。与 key_items 同族（统一机器外的特殊逻辑通道），且比 key_items 更彻底——key_items 尚有 8 行活数据与门翻转行为，equip_taboos 是**纯零行为字段**。
- 解决到哪：整字段退役——字段、唯一消费点、3 行数据、悬空声明、P42 引用注记、正本措辞全链清除；零行为变化（§2.2）。
- 明确不解决（外溢面，禁并入本迭代）：
  - **装备禁忌否决门**（若将来立项）：按统一维度立项——对全阵容开放的参数化禁忌门，接入购买/合成/穿戴三道门中至少一处；禁复活本字段形态（单套手编、主链外挂点）。**现行通道登记（对抗轮 A4 如实修正——通道已在，非假设）**：万敌局锁定后，以牙还牙甲 = tier 0（非 key、非任何万敌 key 材料——K8 图谱进阶件不互为材料）+ `EQUIP_GENERIC_VALUE` base 4 分高于多数候选 → 补给第 3 级选卡（`supply` `pick_equipment`，tier 0 内纯 base 排序）与箱选卡（flow 同源）**在候选含盾件时会确定性选中**。退役前后该通道行为逐位相同（通道不读禁忌），零行为结论不变；但否决门立项的必要性高于本设计初稿的被动表述——损失计量挂实机观察。
  - 万敌线实际购买行为的观察（同上：通道行为退役前后一致；若观察到买盾损失属上述新需求，非本次退役引入的回归）。

## 2. 方案

### 2.1 系统级变化

1. **`Comp.equip_taboos` 字段删除**（实例字段 12 → 11）。类体「字段扩（C4 契约冻结语义）」注释块随 equip_assign 独存收窄；Comp docstring 与模块头无禁忌措辞则不动。
2. **唯一消费点删除**（cw_intention.py）：
   - `_line_hoard`：`taboos = set(comp.equip_taboos)` 与 `equips = {… if e not in taboos}` 两行 → `equips = set(derive_key_equips(comp))`；docstring「装备件 = derive_key_equips(到人配方投影)− equip_taboos（具名禁忌;类级禁忌如『护盾件(类)』由买侧/装备层消费,本层不展开）」句收窄为「装备件 = derive_key_equips（到人配方投影）」。
   - `HoardTarget.equip_targets` 字段 docstring 的「剔除 equip_taboos」措辞（:161）同步删除。
3. **数据行删除**（cw_comps.py 万敌单C）：`equip_taboos=[…]` 行 + 「↑ 教义（官方原文）：燃血队员无法获盾…」注释行（知识归还文档层，见 §2.3）。
4. **P42 活证明与自检脚本处置**（proofs/p42-equipment-machine-ev.md + tools/cw/proofs/p42_check.py，原地保留可溯、禁改写正文推导）：
   - P42 文首退役横幅（taboo(C) 散布十余处——符号表/:4/:14/:74/:124 删域数学地位推导段/:255/:275/:288-289/:331/:334/:345/:347）：数据源退役后删域成为**空删域退化**——删域 ∅ ⊂ 删域任意集，全部含删域步骤的推导自动成立；:124（「K 侧预过滤」指向已删机制 + 存续期零活性实证）/:256（分配硬约束）/:334（结论表⑤）三处定理正文消费点另加行内注记；proofs/validations/P42_VALIDATION.md 验证表「禁忌([29])」行加同义注记。
   - **p42_check.py 三处消费同批修复**（对抗轮 A1——原设计遗漏 tools/ 域）：(8) 段 taboo/key overlap 断言块删除（前提恒假，替换为空域退化打印）；(9) 段 decision_inputs 推导删 taboo 名单项（AttributeError 防御）。脚本存量红（:236 断言 20 套 vs 现 21 套，姬子 A/B 拆分遗留、math_proofs 已登记）非本批责任，登记遗留不修。
5. **正本更新**：
   - strategy-docs/10_prep_decisions.md :203 字段存留表删 `equip_taboos`；:56「万敌禁盾类（equip_taboos）」句改写为纯语义描述（禁盾教义归 final_comps，实现层无载体）。
   - strategy-docs/01_math_framework.md :98（P42 结论引用行）、08_events.md :27 与 13_pick_family.md :48（E11 行「禁忌件过滤」）——三处一句话微调：现行实现层无禁忌载体，删域为空退化（[29] 数学地位留档 P42）。
   - skill sr-od-dev-currency-war references/comp-definition.md 装备族「equip_assign 真源 + key_equips 投影 + 禁忌」与实现层最小面表「equip_assign 到人 + 内在禁忌」措辞——禁忌面随字段退役移除，补一行退役判例指针（阵营内特殊逻辑通道 = 第 4 件整字段退役，判据链 lock_rules→entry_signals→key_items→equip_taboos）。
6. **测试**：sr-od-test 全库 grep `equip_taboos` 零命中（现状即零消费）——无测试改动；落地批跑 L1 快速集验证回归。

### 2.2 行为变化申报

**零行为**。唯一消费点产出恒等空集（§1 症状 1 的交集式即证）：删除前后全库 21 套囤货装备集逐套恒等。无实机观察待办（无行为可观察）。证据两面：人工交集式（症状 1）+ 活测试断言（`test_faction_migration_identity` 逐位锁 `_line_hoard` 输出且万敌在快照内——快照囤货装备集 = 投影 4 件不含盾件，落地批 L1 全绿即含此断言；对抗轮 A6 补引）。边界声明（对抗轮 A5）：「恒空」前提 = equip_assign 为 import 期静态注册表（全库无运行时写路径，grep 实证）——该前提由库级建库校验与单一数据文件形态共同钉住。

### 2.3 知识归宿登记

| 知识 | 归宿 |
|---|---|
| 万敌燃血禁盾教义（受盾只转 2%+1000 回血 = 负资产；连带以牙还牙甲/掩体生成枪类护盾件） | final_comps/final_wandi_burn.md（已在，文档层无同步义务）；策略侧禁忌门立项时消费（§1 外溢） |
| 「禁忌 = 阵容内在机制冲突」的字段设计意图 | comp-definition 判例链（第 4 件整字段退役；登记↔消费一致性教训同 key_items §1 战术权衡段） |

### 2.4 接口契约（对消费方的破坏面）

- `Comp.equip_taboos` 属性消失：生产消费仅 cw_intention.py 1 处（代码 2 行 + docstring 2 处），随本迭代同批清除；另 tools/cw/proofs/p42_check.py 3 处消费随批修复（§2.1 第 4 条，对抗轮 A1）。grep 清零（**src + sr-od-test + tools**；墓碑注记行豁免）为验收判据。
- `_line_hoard` 返回值不变（元组形态与逐套值恒等）：下游（hoard_target_set 及其消费面）零改动。
- P42 文档引用 3 处加注记（§2.1 第 4 条），不删正文。
