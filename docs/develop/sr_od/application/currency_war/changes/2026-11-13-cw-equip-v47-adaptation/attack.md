# CW 装备域 v4.7 换赛季适配 设计对抗报告

- 审查对象：`design.md` / `landing.md` / `README.md`（2026-11-13 草案）
- 审查方法：三核并重（无前提 / 规范遵循 / 治本），全部关键数字用实机数据与仓库实态独立复核（config_v4.7.json 用 PowerShell 解析逐字段验证；src/test 消费面 grep 全量重数；模板库逐目录点数；被引先例逐文件打开核对）。
- 规范依据：`docs/develop/harness/iteration-design.md`（§3.1 阶段粒度、§5 写作硬规则、§7 攻击面）。
- 结论速览：**阻断 4 / 建议 7 / 确认 12**。

---

## 一、阻断（设计错误 / 不可执行 / 依据失实）

### A1 landing §3.2 文件面路径错误——`cw_synthesis.py` 不在 kernel/

- **位置**：landing.md §3.2「文件面：`src/sr_od/application/currency_war/kernel/cw_synthesis.py`」；关联 design.md §2.4（未写路径，无错）。
- **攻击**：实现者按文件面找不到目标文件，阶段不可开工；同时违反 iteration-design.md §5.4「全量同步复查——逐一核设计引用的每个符号/路径存在性」。
- **证据**：`Get-ChildItem src/.../kernel/` 全目录 74 个文件无 `cw_synthesis.py`；实际位置 = `src/sr_od/application/currency_war/data/cw_synthesis.py`（与注册表同层 data 目录）。判据行「图谱派生条数与 config 进阶装备 recipes 非空条数一致」本身可执行（v4.7 进阶装备 compose 非空 = 36/36，已验）。
- **分级**：**阻断**（文件面路径失实 = 不可执行；改一行路径即愈）。

### A2 `cw_equipment_wear_rules_data.py` 整文件被设计遗漏——件级门 10 件在 v4.7 全部不存在，互检必红

- **位置**：design.md §1「解决到哪」（装备域闭环清单未含此文件）、§2.6 挂账表（八行无一提及）、landing §3.1 文件面（仅生成器+注册表两文件）。
- **攻击**：该文件是注册表紧耦合 data 层文件（`from ...cw_equipment_data import EQUIPMENTS` + `check_equipment_wear_rule_coverage()` 互检），按「data 层=装备域」的设计划界理应入改动面或挂账面，但三份文档 grep `wear_rules|穿戴门|件级门` 零命中。其实体内容在 v4.7 已成死判据：
  - `ITEM_WEAR_GATES` 件级门 10 件（银狼专属装备：分身墨镜/分身墨镜Max/数据拷贝仪×3/病毒防火墙×2/破解芯片/管理员手套ProMax/欢愉卡带Max）——**10/10 全部不在 v4.7 config 105 名单**（逐件 Test 验证）；
  - `CATEGORY_WEAR_GATES = {'骇客': ...}`——「骇客」类不在 v4.7 官方 7 类。
- **证据**：3.1 重灌后互检将把这 10 件判孤儿显警 → `test_equip.py::test_wear_rule_coverage_zero_warnings`（sr-od-test :305-307，断言 `check_equipment_wear_rule_coverage() == []`）必红。该门是 S1 实机实证产物（文件注释：equip_freq 前 50 零骇客件等），v4.7 是否仍适用本身是需要挂账实机裁定的语义——设计既没改它、也没挂账它。
- **分级**：**阻断**（改动面遗漏 + 挂账面遗漏，且产生确定性红测试）。

### A3 landing §3.1 完成判据「装备域直接测试通过」按其声明的文件面不可满足——判据依赖另一阶段未完成部分，阶段划分不当

- **位置**：landing.md §3.1 完成判据第 4 条「装备域直接测试通过；消费方测试红逐条登记」+ 文件面（不含任何测试文件）；首节常规检查「消费方域（投资/穿戴/策略）测试红不在本迭代验收内」。
- **攻击**：`test_equip.py` 文件头自述「装备域测试」，但它同时 import 注册表、`cw_synthesis`（CROSS_RECIPES）、穿戴门（ITEM_WEAR_GATES 互检）——3.1 重灌后、3.2 落地前，该文件**至少四处确定性红**：
  1. 特权映射双射锁（:463-485）：硬编码 `e.category == '进阶'` / `== '特权'` 集合 + 36/36 基数断言——新值域下集合为空，必红；
  2. 穿着即合成族（:359 等）：`next(iter(CROSS_RECIPES.items()))`——cw_synthesis 过滤判据未随 3.2 改前 `CROSS_RECIPES` 为空 dict → StopIteration，必红；
  3. 穿戴门互检零显警（:305-307）：见 A2，必红；
  4. `test_unregistered_items_unaffected`（:257-264）：载荷「扑满病毒」既不在 v4.7 105 条也不在派生 11 件（逐名验证），类别门行为随注册表变化漂移。
- **证据**：设计没有定义「装备域直接测试」的文件清单边界——test_equip.py 横跨注册表（属 3.1 该修）与图谱/穿戴门（判据依赖 3.2、A2 文件）。「消费方测试红不在验收」与「装备域直接测试通过」的分界线在这个文件上划不开；而 3.1 文件面不含任何测试文件，worker 按文件面动刀则判据红、按判据动刀则越文件面。iteration-design.md §3.1「判据依赖另一阶段未完成部分 = 划分不当（排进依赖，或重新划分）」直接命中。
- **分级**：**阻断**（判据不可执行；修法方向：3.1 文件面补入 test_equip.py 及受影响装备域测试的同步改判，或把判据改写为可划界的清单）。

### A4 design §2.3「拆了即编译期断裂 19 个消费文件」依据失实

- **位置**：design.md §2.3 末「本迭代不拆常量（拆了即编译期断裂 19 个消费文件，超出装备域文件面）」。
- **攻击**：实测两常量（EQUIP_TOOL_CATEGORY / CONSUMABLE_EQUIP_CATEGORIES）src 消费 = **5 文件 16 处**（cw_equip_env 6 / cw_equip_wear_plan 3 / cw_gain_chain 3 / cw_investments 1 / mandate_v1/mandate.py 3；grep 全量重数）。19 与任何口径都对不上：EQUIPMENTS 符号消费 = 134 处/17 文件；注册表三符号并集 = 160 处/21 文件；含 test 也远非 19 文件。iteration-design.md §5.1「依据就地标注——依据跟着结论走」的前提是依据为真，数字失实即 A 级。
- **证据**：上列逐文件命中数（本报告复核命令可复跑）。
- **分级**：**阻断**（依据失实；决策本身——不拆常量、留给跨域迁移批——经 5 文件口径复核仍然成立，修正数字即可，无需改方案）。

---

## 二、建议（改进空间）

### S1 消费面计数口径未定义，「130+ src / 248 test」不可复核

- **位置**：design.md §1、§2.6 表首行。
- **攻击**：实测多口径结果不一致：EQUIPMENTS 单符号 = 134 处/17 文件（「130+ 处」最贴近此口径）；全符号（+ROSTER/get_equip/两常量）并集 = 160 处/21 文件；test 侧符号引用 167 处、符号+紧口径 `category='...'` 字面量 = 177 处、宽口径字面量 = 292 处——无一口径得 248。数量级成立，但挂账清偿时无从对照「清完没清完」。
- **建议**：§2.6 挂账行给出口径定义（按符号清单 grep），或直接附符号清单作验收基准。

### S2 §2.2 priority 语义描述失真（结论不受影响）

- **位置**：design.md §2.2「`priority`（类别内排序号无消费语义）」。
- **攻击**：实测 priority 与 category **一一对应且同类内恒定**（进阶=2×36 / 星徽=3×21 / 宝钻=4×1 / 特权=5×36 / 餐品改件=12×6 / 列车改件=13×4 / 固有=14×1）——它是**类别级排序码**（决定分类显示顺序），不可能排序「类别内」条目。「无消费语义、不登记」的结论正确，描述应改为「类别级排序码，条目级无信息量」。
- **分级**：建议（一句话修正）。

### S3 3.1 两处实现级语义选择未定死

- **位置**：landing.md §3.1 范围/判据。
- **攻击**：①`glob config_v*.json 取最新`的排序键未定义——词序比较 `config_v4.10 < config_v4.7`，实现者需自行拍板数字比较（iteration-design.md §5.2「实现者无需再设计」边角违例）；②判据「生成器对旧文件纯新增语义无残留旧源调用」中「纯新增语义」措辞含混，可执行部分只有括号内 grep 零命中。
- **建议**：一句话定死（解析 v 后按数字比较）；判据删「纯新增语义」或改写。

### S4 3.4 挂账登记与挂账板现状有交叠，未提示合并

- **位置**：landing.md §3.4；design.md §2.6。
- **攻击**：`.debug/progress/CW跨迭代挂账.md` 第一节 0「v4.7 换赛季适配欠账族」（2026-11-13/14 羁绊域会话登记）已含「装备贡献表类别与句式适配（cw_bond_equips 星徽/卡带授予表类别词硬编码，归装备域重建批）」与「v4.7 换赛季消费层中间态清偿」条目——与 3.4 八项中的消费方迁移、类别词面直接交叠。设计未提示与既有条目合并登记，存在同板重复条目风险（板头维护纪律明言「事项闭环/迁移时当场更新或删除条目」）。
- **建议**：3.4 判据补一句「与既有欠账族条目合并，不另起重复行」。

### S5 主分支红窗无清偿排期承诺

- **位置**：design.md §2.6（去向列）；landing.md 首节。
- **攻击**：消费方迁移 130+ 处的红窗只受挂账批排期约束，去向写了「投资域重建批（另一会话）与穿戴域」但无时点/触发条件；挂账板纪律是「开工时立项进 dag」而非排期。项目提交纪律（AGENTS.md「相关测试全量一次通过才提交」）被 landing 显式豁免于消费方域，豁免期长短无界。板上有「羁绊消费点迁移批」承接面可挂。
- **建议**：§2.6 或挂账行登记红窗清偿的承接批次指针与登记时点，让红窗有界。

### S6 挂账行「白昼 6/命运 18/工具 7 存废」名单不全

- **位置**：design.md §2.6 表「白昼 6/命运 18/工具 7 存废（API 不覆盖 ≠ 游戏无）」。
- **攻击**：同构问题还有**骇客 8 / 特殊 17**（旧九分类实测数）——API 不覆盖、v4.7 无对应类（特殊仅宝钻 1 件以官方类名回归、垃圾袋以派生简易回归）。存废问题同构却只列三类。
- **建议**：挂账行扩为「API 外旧类存废：白昼 6/命运 18/工具 7/骇客 8/特殊 17」。

### S7 跨件半问：装备域与角色域同族重建，公共基座值得家族批考量

- **位置**：design.md §2.3（生成器改造）；核三。
- **攻击**：角色域并行迭代（`.debug/progress/2026-11-14-cw47角色注册表重建`）与本迭代同族——「官方 plaza config 快照 → 域注册表单源重灌」，两域生成器（gen_plaza_chars / gen_equip_registry）各自演化读同一 config 快照，版本 glob/落点/对拍/掉出报告四件套重复实现。同族修法第 2 件出现，按 AGENTS.local.md §1「跨件半问」应问是否升架构级。本迭代按用户裁定链（逐域闭环）推进不阻断，但家族级「plaza config 快照消费基座」建议入挂账板家族议题。
- **分级**：建议（登记，不展开）。

---

## 三、确认（核过无问题的重要项，附验证证据）

### C1 config 权威数据全部实证通过

105 条 ✓；七类分布 36/36/21/6/4/1/1 ✓；properties 104/105 非空（唯一空 = 财富宝钻）✓；ability_name 105/105 全空 ✓；固有装备 1 件 = 翻飞之币（id 35130999，desc 明文提及【赛飞儿】，§2.6 挂账行「疑似专属绑定」属实）✓。design §1 类别分布与 §2.1/§2.2 数字逐项对上。

### C2 旧注册表 158 件九分类属实

`_eq(` 调用 159 = 定义 1 + 数据 158 ✓；九分类分布 进阶36/特权36/星徽22/命运18/特殊17/骇客8/简易8/工具7/白昼6 ✓（§1 九分类词面、§2.6 白昼6/命运18/工具7 数字全对）。旧 158 名 ∩ 新 105 名 = 73 同名保留 / 85 掉出——3.1 diff 报告的数字基础真实可用。

### C3 调研结论转述无二手失真

design §2.1 内联四点与 `.debug/temp/currency_war/equip_api_research.md` 逐条吻合：config 105/105 全覆盖+desc 全文+compose 链+图标 URL ✓；米游社 242 频道 0 词条（空壳）✓、211 频道 153 词条中 73 同名且 36 条数值过期 ✓；国际服无 CW 装备菜单 ✓；BWIKI 73/105 且 S1 快照 ✓。调研报告真实存在且带复跑调用与证据文件索引；§2.6 wiki 探针行（242 词条数/BWIKI 分类成员数）即报告 §7.2 原建议。

### C4 importlib/sys.modules 先例真实

`sr-od-test/test/tools/test_replay_render.py:28-32` 确为 `importlib.util.spec_from_file_location` + 执行前 `sys.modules` 预注册，注释明言「dataclass 处理器按 cls.__module__ 回查 sys.modules」——§2.3 引据成立。

### C5 特权翻倍与模板去重属实

追逐星辰 props 10%/10% → 追逐星辰·特权 20%/20% ✓（「自带数值翻倍 properties，与普通版名不同不撞键」）；36 条特权名全部 `·特权` 后缀 ✓。`gen_plaza_chars.py::gen_equip_templates` :514-517 确有特权同 art 去重（注释：36 对实测同 icon URL）✓。plaza unique icon = 69 = 36 进阶+21 星徽+6 餐品+4 列车+1 宝钻+1 固有（特权 36 对共享普通图）✓。模板库点数：equip_plaza 185 / equip_legacy 156 ✓。

### C6 简易装备派生层数据基础扎实

105 条 compose_list 子件展开去重 = 恰 11 件（光能电池/和平手枪/红钻/垃圾袋/蓝钻/量产型装甲/轮滑鞋/生命之花/幸运星/以太钻头/折叠小刀），与 105 名零同名（无撞键）；childrens 全字段（id/desc 合成说明/icon）✓；11 件模板 png 全部已存在于 equip_plaza（逐件 Test-Path 通过）——3.1 派生与 3.3 保留集计算可零猜测落地。

### C7 3.2 必要性与装备域边界自洽

`data/cw_synthesis.py:40-44` 判据确为 `eq.category == '进阶' and eq.recipes`、import 期从注册表派生 ✓——3.1 改值域后图谱静默清空，3.2 是 3.1 的强制后随（依赖=3.1 正确）。cw_synthesis 在 data/ 层属注册表紧耦合 meta 层，design §1「解决到哪」明确含合成图谱，与 §2.7「消费方迁移不解决（投资/穿戴/策略域）」不矛盾——3.2 改的不是消费方文件。进阶装备 compose 非空 = 36/36，3.2 判据数字可对（路径错见 A1）。

### C8 official_category 删除安全

src/test 全仓 0 消费点（grep 全量）——删字段无编译断裂，§2.2「双字段冗余废止」成立。

### C9 desc 转义字面规则与数据实态一致

raw JSON 中换行为字面 `\\n`（字符码 92,92,110 实测），json.load 后字符串含反斜杠+n 两字符——「`\n` 转义字面保留（生成产物字符串字面量禁止真换行）」与数据实态吻合，规则可执行。

### C10 治本核验通过（核三）

§1 归层成立：分类分叉 = 表示层（旧生成器 `SECTION_CATEGORY` 九分类表实证）、三源采集流程 = 流程层（parse_skeleton/merge_codex/parse 三源代码实证）；§2 修根——config 单源直灌消流程根、官方分类直落消表示根，非症状补丁。旧生成器现状两处次源数据已亡（equipment.md 于 commit be62ed454 删除、.debug/temp/cw_equip_data.json 不存在），单源化与现状相容；「能做的做、实机项挂账」口径下 API 外装备（白昼/命运/骇客等）走挂账实机裁定而非逐件硬编码，方向治本。

### C11 规范遵循主体合格（核二）

四节齐（§0 元信息/§1 问题动机/§2 方案 + landing 阶段 + README）✓；landing 各阶段七件齐（范围/设计依据/文件面/依赖/优先级/完成判据/验收凭据）✓；完成前常规检查首节自包含、各阶段仅引用 ✓；正本更新清单 4 行均「正本文档:节 ← 阶段」形态且 4 个正本文件全部存在（docs/game/currency_war/data/README.md、research/equipment_mechanics.md、两个 skill references）✓；README 两件事、进度含 attack.md 指针 ✓；三份文档无过程叙事措辞 ✓；依据就地标注覆盖率高（§2.1 调研报告+内联、§2.2 用户裁定、§2.3 先例、§2.4/§2.5 派生依据）——例外即 A4/S1/S2 三处数字与口径问题。设计依据指向真实节（§2.1-2.7 均存在）✓。

### C12 3.4 挂账板文件面有效

`.debug/progress/CW跨迭代挂账.md` 存在且为 CW 后续跟进唯一板（板头声明与 unified-line-scoring-sim-debt 同构先例）；既有「v4.7 换赛季适配欠账族」节与多会话协同结构吻合（交叠风险见 S4）。

---

## 四、复核命令备忘（供定稿修订后复跑）

- config 分布/字段：解析 `.debug/game_data/currency_war/plaza/config_v4.7.json` → `equipment_list` Group-Object category_name / properties / ability_name / priority。
- 派生 11 件：展开全部 `compose_list[].childrens[].name` 去重。
- 消费面：`Get-ChildItem src -Recurse -Filter *.py | Select-String 'EQUIPMENTS|EQUIPMENT_ROSTER|get_equip|EQUIP_TOOL_CATEGORY|CONSUMABLE_EQUIP_CATEGORIES'`（排除 cw_equipment_data.py 自身）。
- 穿戴门：`src/sr_od/application/currency_war/data/cw_equipment_wear_rules_data.py` ITEM_WEAR_GATES 十件逐名对 config 名单。
- 图谱判据：`src/sr_od/application/currency_war/data/cw_synthesis.py:40-44`。
