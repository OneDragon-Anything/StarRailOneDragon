# 设计对抗报告：遗器装备流程改造

## 结论

需修订——设计骨架（根因归层、流程形态、op 划分）成立，但存在 13 个攻击点：2 条动摇核心解析正确性（F18 依据失真、平坦词条切分规则缺失）、4 条令 landing 阶段不可直接开工（依赖漏标、文件面缺测试文件、节点链构成矛盾、验收判据指向不存在数据源）、1 条系统性边界未分析（共享筛选持久态的跨 op 污染）。

## 攻击点

### A1 F18 实测样例与出处帧不符（核一·依据失真）
- 位置：design.md §2.1 F18
- 问题：样例「生命值 6.9%0」「防御力 9.1%0」与标注出处帧不符——帧上这两个词条的绿色次数角标清晰为 **1 和 1**，非 0 和 0；「暴击伤害 22.0%3」相符，「效果抵抗 3.4%」（无次数角标）相符。样例是解析规则的唯一实证形态，尾数失真使「数字后缀有则用」规则失去可信出处；且「第 4 词条 0 次时绿色小数字未读出」的机制断言超出单帧可证范围（一帧无法区分「0 次不渲染」与「渲染但 OCR 未读出」，两者对平坦词条解析的含义不同，见 A2）。
- 依据：`sr-od-test/screens/遗器-替换/候选详情词缀.webp`（副词条行实读：生命值 6.9% [绿1] / 防御力 9.1% [绿1] / 暴击伤害 22.0% [绿3] / 效果抵抗 3.4% [无角标]）vs design.md L59 样例串。
- 建议：样例按帧重取（6.9%1 / 9.1%1 / 22.0%3 / 3.4%缺）；「0 次是否渲染」用另一帧（含确知 0 次词条的 +0 件）实证后再写机制句。

### A2 平坦值词条的 value/times 切分规则缺失（核一·实现者走查）
- 位置：design.md §2.1 F18 / §2.2 L74
- 问题：「数字后缀有则用、缺失按 0 计」只在 % 形态闭环（% 号锚定切分点：`6.9%1` → 值 6.9%、次数 1）。平坦值词条（速度/生命值/攻击力/防御力的平坦副词条，整数值无 % 锚点）无切分规则：①0 次且角标 OCR 缺失时（F18 自认缺失会发生），「速度 25」按规则尾数 5 被当次数 → 次数误计 5、值误为 2——约束「速度 ≥1 次」被误判满足，直接错杀核心判定；②速度取值 2-9 时「23」无法区分值 2/次数 3 与值 23/次数缺失。设计 F18 样例与出处帧全部为 % 词条，平坦形态零证据。游戏侧副词条可确为平坦值（`docs/game/screens/遗器-替换.md` L45「词条名 数值 (强化次数)」形态不限词性）。
- 依据：design.md L59、L73（「平坦/% 同名异义按数值串的 % 后缀消歧」只解决词名消歧，不解决值/次切分）；`src/sr_od/backend/mcp/relic_eval_tools.py` L139-145（名册侧 value 是独立字段，无此问题——游戏 OCR 侧是设计新引入的形态）。
- 建议：补平坦形态切分规则（候选：按读区内数值串与绿标角标的几何列位置分离而非纯字符串拼接；或值域校验兜底——平坦值域已知如速度 2-25），并补一张含平坦副词条的实机帧作依据；补不齐则在 §2.2 显式声明「平坦词条次数不可信，按 times_confirmed=false 降级供人复核」。
- 未实证：平坦词条实机 OCR 拼接形态（现有 14 帧无平坦副词条样例，需实机补帧）。

### A3 landing S4 依赖漏标 S1（核一·design↔landing 失同步）
- 位置：landing.md §3.4 依赖 / design.md §2.3 L94、§2.4 L112
- 问题：ScanRelicCandidatesOp 的前置检查「入口检查排序摘要读区 =『遗器建议排序』时显式失败」依赖「读区-排序摘要」area——该 area 是 S1 的新建档产物（design §2.4）；S4 依赖只写「S2（relic_detail_reader）」。S1 未完成时 S4 无法按 §2.3 实现前置检查，判据「建议排序开着 → 显式失败」不可执行。
- 依据：landing.md L55（依赖：S2）；design.md L94（入口检查排序摘要读区）、L112（读区-排序摘要 ← S1 新增）。
- 建议：S4 依赖改「S1、S2」。

### A4 S1 文件面缺消费测试文件，改动面申报失准（核一/核二）
- 位置：landing.md §3.1 范围/文件面/完成判据
- 问题：①「按钮-遗器建议排序」改名后，既有流程测试 `test_equip_relic.py` 两处断言直接消费旧 area 名（L208 exit 元组 `('on_click_in', '遗器-替换', '按钮-遗器建议排序')`、L228 `click_hit_area('遗器-替换', '按钮-遗器建议排序')`），改名即红；S1 完成判据要求「既有流程测试全绿」，但文件面未列该测试文件（测试仓只列了 `screens/遗器-替换/` 帧目录）——worker 在申报面内无法让判据成立。②「仅 area 名消费点」低估改动面：文本区改纯坐标区后，`open_sort_dialog` 的调用形态从 `round_by_find_and_click_area`（find 命中文本）变为纯坐标直点 + until（纯坐标区 find 不命中，项目既有模式见 `equip_relic.py` L199-210），方法形态与坐标常量都要变。③范围「边界：不含任何 op 实现」与范围正文「修复消费点 equip_relic.py」（op 节点代码改动）及完成判据自相矛盾。
- 依据：`sr-od-test/test/sr_od/application/cultivation/relic/operations/test_equip_relic.py` L208、L228；`assets/game_data/screen_info/relic_replace.yml` L459-473（现文本区 `text: 遗器建议排序` + goto_list）；landing.md L13、L15、L20。
- 建议：S1 文件面补 `sr-od-test/test/sr_od/application/cultivation/relic/operations/test_equip_relic.py`；范围措辞改为「不含新 op 实现，含 equip_relic.py 排序前置链消费点改造」；「仅 area 名消费点」改为「排序弹窗打开动作改纯坐标点击 + until 转移验证」。

### A5 sort_stat 链「既有四节点链复用」与后续步骤构成矛盾，复用机制未定（核一·实现者走查）
- 位置：design.md §2.3 L88 / landing.md §3.3
- 问题：①既有四节点链 = 打开排序弹窗 → 关建议排序 → 选等级排序 → **确认排序规则**（`equip_relic.py` L222-292，确认节点 until = 弹窗标题消失即关弹窗）。FilterRelicReplaceOp 的步骤列表是「点排序设置按钮 → 关建议排序（既有四节点链复用）→ 弹窗滚动区内 OCR 定位属性行 → 点行 → 确认」——属性行在弹窗内，若四节点含确认节点则弹窗先关、「点行」无弹窗可点；若不含确认则「四节点」名不副实。②基础排序是否选「等级」未声明：选（静态可预期，F15 摘要形如「等级|属性」）或不选（F11 选中历史保留，基础序为不定历史项）直接影响列表序与摘要验证语义。③「复用」机制三选一未定：跨 op 调用 EquipRelicOp 节点方法 / 节点代码复制 / 抽公共 helper——抽 helper 要改 equip_relic.py，不在 S3 文件面（只列新文件 filter_relic_replace.py）；「域内 op 各自持入口副本为既有惯例」的先例只覆盖入口逻辑，未覆盖四节点链整体复制。
- 依据：`src/sr_od/application/cultivation/relic/operations/equip_relic.py` L222-292；design.md L88；landing.md L41（S3 文件面仅新文件）；`docs/game/screens/遗器-排序规则.md` L54（四节点链构成描述）。
- 建议：§2.3 明写 FilterRelicReplaceOp 的排序前置子链构成（建议：打开弹窗 → 关建议排序 → 选等级 → 不确认，属性行点选后统一确认），声明基础排序固定选「等级」，并指定复用机制（复制节点并注明与 equip_relic 同源，或声明抽 helper 并把 equip_relic.py 加入 S3 文件面）。

### A6 残留选中态与重复运行语义未定义，验证锚不充分（核一）
- 位置：design.md §2.3 L87-L89 / §2.1 F4、F11
- 问题：①属性排序残留态：F11 实证弹窗重开时基础排序选中历史保留——属性排序选中是否同样残留未摸底也未声明。用户手设或上一轮运行残留的属性行已在优先级链上时，FilterRelicReplaceOp 点目标属性行后产出的是「残留属性 + 目标属性」的混合优先级，与调用方意图不符；而验证锚「排序摘要读区**含**属性名（F15）」只验包含不验等于，拦不住该偏差（含 ≠ 等于）。②套装勾选 toggle：F4 勾选 = 点行文本中心（点击在勾/未勾两态间翻转的 checkbox 语义），设计未声明「目标套装已勾选」时的预检防呆；F9 明确筛选态跨运行持久，同参数重复运行 `FilterRelicReplaceOp` 时行已是勾选态，盲点即反选。③F6 说明删除 chip 即时生效且「保存」是方案预设语义——重复运行下「确认」对已选集合的幂等性未声明。
- 依据：design.md L50（F11 选中历史保留）、L87（点行文本中心）、L88（验证 = 摘要含属性名）、L43（F9 共享持久态）；`sr-od-test/screens/遗器-替换/排序弹窗双属性选中.webp`（选中态有明确视觉判据可供预检）；`src/sr_od/application/cultivation/relic/operations/select_bag_relic.py` L19-21（既有 op 对历史筛选叠加只做「诚实失败」暴露的先例）。
- 建议：§2.3 补两条语义：①sort_stat 链点行前先判属性行选中态（已选中跳过/有残留属性先「全部清除」再选，二选一定死）并把验证锚升级为「摘要 = 期望形态」（如「等级|速度」全等或至少不含意外属性）；②套装勾选前先判行勾选态（F4 已给两态视觉判据），已勾选跳过点击。
- 未实证：属性排序选中是否跨弹窗重开残留（F11 只实证了基础排序）；已勾选行点击是否反选（checkbox 常规语义推断）。

### A7 写共享持久筛选态而不清理的跨 op 污染未分析（核三·边界完整性）
- 位置：design.md §2.3 L89（不做清除边界）/ §1 解决到哪
- 问题：设计自证（F9）替换屏筛选与背包侧共享同一持久状态，又把「清除筛选」一刀切划出边界且未排期，却未分析 FilterRelicReplaceOp 跑完后残留筛选态对**同列表既有消费者**的反向影响：①EquipRelicOp——本迭代自己扩展的对象——后续运行在该列表按残留套装筛选下扫候选，目标件名被过滤隐藏 → 走到「滚动 12 屏未找到 X(未拥有或识别失败)」的误导性失败（`equip_relic.py` L331-333，现有文案语义只覆盖「未拥有/识别失败」两种死因）；②SelectBagRelicOp docstring 已明示「历史筛选与本 op 意图叠加时由件名核对诚实失败暴露」——设计引入新写态方却让既有失败模式扩大触发面。这是新流程对既有流程的系统性副作用，属根因层（共享态）上的新症状源，设计须至少声明风险与操作顺序约束。
- 依据：design.md L43（F9）、L89（边界「不做清除」）；`equip_relic.py` L331-333；`select_bag_relic.py` L19-21；`sr-od-test/screens/遗器-替换/筛选面板带chip筛选后列表.webp`（筛选改变列表内容实证）。
- 建议：三选一并写进 §2.3：①FilterRelicReplaceOp 末尾补「还原」步骤（记录进面板前状态并恢复，或退而点 chip ✕ 清除本 op 设置的套装，F6 已证即时生效）；②边界保留「不做清除」但显式声明残留态风险 + 要求调用方/文档约束操作顺序（Filter→Scan→Equip 链内消化，链外必清）；③「重置」链外溢为后续迭代并在 §1「明确不解决」登记（按 iteration-design §1.1 外溢判定走新迭代）。同时建议 EquipRelicOp 耗尽 fail 文案补「列表可能带残留筛选」提示或入口预检「标识-筛选中」角标（S1 已建该 area，边际成本低）。

### A8 「全部候选耗尽不满足 → fail 带逐件概要」的落点未定义，且与 S5 边界冲突（核一·实现者走查）
- 位置：design.md §2.3 L104-L105 / landing.md §3.5 边界
- 问题：①既有候选耗尽 fail 在 `find_and_select`（L331-333：`滚动 {_SCAN_MAX_SCREENS} 屏未找到 {piece_name}(未拥有或识别失败)`），文案语义=「未找到」；约束模式下耗尽的真因是「找到但全不满足」——设计要求「fail 信息带逐件概要」，但概要在哪个状态字段累计、由哪个节点抛出 fail、文案如何区分「未找到」与「全不满足」三问均无答案。②landing S5 边界明写「不改候选定位/…逻辑」，而概要累计与耗尽 fail 天然落在候选推进路径（find_and_select 的耗尽分支）——worker 被 §2.3 的承诺与 §3.5 的禁令夹住，两头不靠。
- 依据：`equip_relic.py` L331-333、L319-322（RESELECT → find_and_select 回边）；design.md L104-105；landing.md L65。
- 建议：§2.3 补机制：新增实例级概要列表（verify_selected 约束不满足时 append），find_and_select 耗尽分支按「概要非空 → fail(全部候选不满足约束 + 逐件概要) / 概要为空 → 现文案」分流；landing S5 边界措辞改为「不改候选定位与抢件逻辑，耗尽 fail 文案与概要分流除外」。

### A9 下沉清单枚举不完整，与 §2.6 反漂移取舍自相矛盾（核一）
- 位置：design.md §2.2 L72-L73 / §2.6 L131
- 问题：「三表 + 解析函数」未指名集合：`relic_eval_tools.py` 实有 5 张语义表（STANDARD_STAT_NAMES L34 / FLAT_PERCENT_HOMONYM_NAMES L45 / PERCENT_STANDARD_BY_NAME L48 / STAT_NAME_ALIASES L56 / STAT_PACKS L79）+ 3 个纯函数（`_resolve_criteria_word` L98 / `_resolve_roster_stat` L116 / `_parse_stat_value` L133）。§2.2 又要求游戏侧解析「同用一套（…逻辑同 `_resolve_roster_stat`）」——若只搬口径包/别名/标准名三表 + `_resolve_criteria_word`，则同名异义消歧（FLAT_PERCENT_HOMONYM_NAMES + PERCENT_STANDARD_BY_NAME + `_resolve_roster_stat`）留在 backend 或在游戏侧重写，形成双实现——正是 §2.6「别名表/口径包双份必漂移」要防的事故；若全搬，「三表」口径失准。另「测试 import 路径随迁、断言不变」为空操作：两个既有测试文件都不 import 待搬符号（`test_relic_eval_tools.py` L19-22 只 import `evaluate`/`ROSTER_STRUCTURE_ERROR_MESSAGE`；`test_mys_evaluate_relic_substats.py` L17-18 只 import 注册层），无需随迁，照写会误导 S2 worker 找不存在的迁移面。
- 依据：`src/sr_od/backend/mcp/relic_eval_tools.py` L34-145；design.md L72-73、L131；两测试文件 import 行如上。
- 建议：§2.2 改为逐符号清单：「5 表 3 函数全量下沉至 sr_od/mys/sr_relic_stats.py（MAIN_CHECK_SLOTS/ROSTER_STRUCTURE_ERROR_MESSAGE 留 relic_eval_tools）」；删「测试 import 路径随迁」句，改「新增 sr_relic_stats 测试文件，既有 relic_eval 用例中规则 1 场景随迁为新模块用例」。

### A10 S4 验收判据指向不存在的数据源（核一）
- 位置：landing.md §3.4 完成判据
- 问题：「抽 2 件与画面 doc 词缀人工对照一致」——`docs/game/screens/遗器-替换.md` 不含任何具体遗器件的词缀数据（全文只有读区坐标、交互行为与识别结论，无逐件词条记录），「画面 doc 词缀」是不存在的对照物，判据不可执行。
- 依据：`docs/game/screens/遗器-替换.md` 全文（L40-48 automation 读区节无逐件数据）；landing.md L59。
- 建议：改为「抽 2 件与实机画面详情面板人工对照一致」（验收时开游戏对读），或「与 S1 帧内词缀（候选详情词缀.webp）对照」。

### A11 正本更新清单含条件式「看情况」条目（核二·写作硬规则 2）
- 位置：landing.md 正本更新清单 L90
- 问题：「`docs/develop/sr_od/application/cultivation/README.md`：§3 识别器自含口径（**若 detail_reader 归域口径需提一笔**）← S2」——是否更新留给了执行时裁量，属「看情况/待定 = 未定稿」（iteration-design.md §5 规则 2）；detail_reader 是否属 §3「识别器自含口径」的记述对象应现裁。
- 依据：landing.md L90；`docs/develop/harness/iteration-design.md` L103。
- 建议：现裁后改确写：detail_reader 是 OCR 读区解析件、非 ScreenRecognizer，不改 §3（删该行）；或认定属域口径记述对象，改确写「§3 增补 detail_reader 一句 ← S2」。

### A12 帧资产标称数与目录不符，建议排序态列表帧缺口未交代（核一·minor）
- 位置：design.md §2.5 L120 / landing.md §3.1 文件面
- 问题：「S1 归档的 14 帧即测试资产」「14 帧已归档」——目录实有 15 张 webp（14 张摸底帧 + 既有建档帧 `default.webp`，2026-10-17 建档、`docs/game/screens/遗器-替换.md` L3 的 source_image）。S4 判据「建议排序开着 → 显式失败」的流程测试需要「替换屏列表 + 右侧详情面板 + 排序摘要=遗器建议排序」帧：14 张摸底帧中列表可见的帧（筛选面板开/带chip/已清）右侧均为筛选面板非详情面板，最贴合的恰是未被计入的 default.webp——测试帧取用面与标称的 14 帧集合不闭环。
- 依据：`sr-od-test/screens/遗器-替换/` 目录 15 张 webp 实点；landing.md L15、L58。
- 建议：表述改「14 张摸底帧 + 既有 default.webp 共 15 张」，并在 §2.5 注明 S4 流程测试的替换屏默认态帧取 default.webp。

### A13 OCR 帧解析单测的慢速集登记未提（核二·minor）
- 位置：design.md §2.5 L121 / landing.md §3.2 完成判据
- 问题：`relic_detail_reader` 解析单测以「候选详情词缀.webp」整帧 OCR 为输入（S2 判据），单条实测大概率 ≥2s——按测试规范须登记 `sr-od-test/slow_marks.txt`；design/landing 均未提，且「慢计算只算一次」的约束（同帧多断言共享一次 OCR 结果）宜在测试设计里写明，防 worker 逐断言重跑 OCR。
- 依据：landing.md L33（判据走整帧解析）；项目 AGENTS.md §10.1（慢速集登记、慢计算只算一次）；`sr-od-test/slow_marks.txt`（既有登记机制存在）。
- 建议：§2.5 补一句「帧解析单测整帧 OCR 一次、断言共享结果，实测 ≥2s 登记 slow_marks.txt」。

## 核对通过面（核实为真、未立案的主张）

- §1 症状 1/2/3 的依据全部属实：`_filter_candidates` 仅按 owner 过滤（equip_relic.py L78-95）；识别 extras 无词缀字段（relic_list_recognizer.py L185-192）；替换屏词缀读区已建档但无 op 消费（relic_replace.yml L207-262）；筛选漏斗/排序摘要/升降序/属性排序分区均未建档（relic_replace.yml 全 area 清单 + 遗器-排序规则.md L46）。
- F15 推论（现存隐患）成立：`relic_replace.yml` L459-473 该 area 为文本区且 `open_sort_dialog` 靠 find 命中（equip_relic.py L227）；帧实证摘要文本两种形态（筛选面板开.webp=「遗器建议排序」、候选详情词缀.webp=「稀有度|暴击率,速度」）。
- F2/F3/F7/F8/F13 帧判读全部与归档帧相符；F5 与背包侧行为差异的旁证属实（select_bag_relic.py L13-14「确认后弹窗与面板同时收起」）；F9 旁证属实（select_bag_relic.py L20 docstring 原文）。
- 下沉方向合法：`sr_od/mys/` 确为词条语义既有归属层（sr_codes.py `PROPERTY_INFO_SNAPSHOT` L54）；backend/mcp import sr_od.* 有大量先例（mys_tools.py L67 等）。
- RESELECT 机制、抢件取消语义、约束判定时序（先于取消逻辑）与既有节点图相符（equip_relic.py L319-322、L378-420）。
- landing 阶段七件齐全、S1-S6 顺序与依赖除 A3 外成立；S6 正本清单各文件路径真实存在（cultivation README §3/§5、game coach relic-enhancement.md §3.1 属实且经 junction 落在本仓 skills/ 内）；迭代 README.md 符合 iteration-design §4 构成。
- 核三：根因归层「流程层」论证成立（词缀随机性无常量库可依 + 人拍板决策结构，与光锥静态特效同构性对比有 op 源码支撑）；§2 修决策数据缺失与执行不可控之根而非症状；未发现同族第 2 件症状补丁（detail_reader 为域内新件，无光锥侧同构复制被制造）。
