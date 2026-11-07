# 有效词条计数工具（relic-substat-eval）迭代设计（总纲）

## 0. 元信息
- 迭代目标：练度评估遗器层的计数工具化（标准与设计决定出处：`skills/sr-od-game-coach/references/investment.md`「评估优先级与遗器层」节 + 「有效词条计数工具的设计决定」节）
- 状态：定稿（对抗审报告见本目录 attack.md，24 项全部处置）
- 文档清单：无详设（单文档方案，本文件即完整设计，深度按详设要求执行）

## 1. 问题与动机
- 现状症状：练度评估遗器层（社区口径「命中了多少个有效词条」）目前只能由 agent 对 `mys_get_roster_detail` 的词条明细手数——一次多角色评估（本迭代验收面为 12 人，见 §2.5 名单）既慢又易错，且不可复算。
- 根因归层：**能力层缺口**——口径（知识）已在 game-coach 角色档，确定性的计数算术（能力）无工具承载。
- 解决到哪：`sr_od` MCP server 新增一个口径参数化的只读评估工具（入参=每角色有效词条口径，出参=命中计数与毕业线对照）；顺带在 game-coach 角色档落地一行机器可读口径的约定（知识侧配合项，见「跨层依赖」）。
- **明确不解决**：
  - 不内置任何默认口径（设计决定：口径是活知识，写死必与角色档漂移）；
  - 不做强度打分（分数=实战，工具只数数）；
  - v1 不做按词条滚动值域的加权评分（暴击 5.4~6.9%/条等权重表）——属外溢议题，若未来需要自成新迭代；
  - 不解析角色档 markdown（口径行由调用方读取后作为参数传入，工具不读任何知识库文件）。

## 2. 方案

### 2.1 系统级变化
`sr_od` MCP server 工具组新增一个只读工具 `mys_evaluate_relic_substats`，背后是一个纯计算模块（零 IO、零副作用，可独立测试）。数据流：调用方传「每角色口径 + 可选名册明细」→ 工具（缺名册时自调 `mys_get_roster_detail`）→ 逐角色逐件数词条 → 返回计数与对照。

### 2.2 MCP 工具接口（字段名为最终实现名）

**工具名**：`mys_evaluate_relic_substats`（title：评估遗器有效词条；`ToolAnnotations(readOnlyHint=True)`）

**工具描述文本（实现时逐字使用，含 Returns 段）**：
> 评估遗器副词条的命中情况——按传入的每角色有效词条口径，对名册遗器明细做确定性计数：命中数/浪费分布/主词条核对/毕业线对照。口径由调用方提供（取自 sr-od-game-coach 角色档的「有效口径」行，可按阵容定位调整），本工具不内置任何默认口径；未传口径的角色不评估。`roster_data` 可传 `mys_get_roster_detail` 已拉取的结果避免重复请求；不传则工具自动拉取。
>
> Returns:
> 统一信封 `{"status","message","data"}`：
> - `success`：`data` 含 `results`（角色名 → 评估结果：total_rolls/effective_hits/hit_ratio/hits_by_stat/wasted_rolls_by_stat/main_stat_check/threshold_report/weakest_piece/warnings/verdict）与 `not_found`（传入口径但名册不存在的角色名）与 `team_summary`（按命中占比升序的全队排序）；success message 模板「共评估 N 名角色，M 名未命中名册」。
> - `session_expired` / `verification_required`：仅自拉名册路径，controller 状态原样透传（处理方式同 `mys_get_roster_detail`）。
> - `error`：名册拉取业务失败（1034 等原样透传）；`criteria` 为空列表；`criteria` 存在重复 `character_name`（message 列出重复名）；`roster_data` 结构非法（message 提示应传 `mys_get_roster_detail` 返回的 `data` 字段内容——角色明细数组）。

**入参**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `criteria` | list[object] | 是 | 每角色一条口径，结构见下；空列表返回 error |
| `roster_data` | list[object] | 否 | `mys_get_roster_detail` 返回的 `data`（角色明细**数组**，元素结构 = CharacterDetail 的 asdict，冻结字段集见 `docs/develop/sr_od/backend/mys.md`）；缺省则工具自拉 |

**criteria 元素字段**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `character_name` | str | 是 | 角色中文名，对名册精确匹配；重复出现返回 error |
| `effective_substats` | list[str] | 是 | 有效词条清单；元素可以是词条标准名、词条别名或口径包名（内置归一表/口径包表自动展开，见 §2.4）；清单的补集一律视为无效 |
| `main_stat_expectations` | object | 否 | 部位中文名（躯干/脚部/位面球/连结绳）→ 可接受的主词条标准名数组；缺省则该角色跳过主词条核对 |
| `stat_thresholds` | object | 否 | 词条标准名（或别名，过归一）→ 毕业线数值；**口径 = 主词条（若同名）与副词条的词条求和**，与角色档「转化上限」的面板口径不一定等价——调用方给线时须按词条求和口径换算 |

**出参 data 与单角色结果字段**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `results` | object（角色名 → 评估结果） | 见下 |
| `not_found` | list[str] | criteria 里传了、名册里找不到的角色名 |
| `team_summary` | list[object] | 全队按 `hit_ratio` 升序：`{"character_name", "hit_ratio"}`（total_rolls=0 的排最后） |

单角色评估结果字段：`total_rolls`(int) / `effective_hits`(int) / `hit_ratio`(float\|null，total_rolls=0 时 null) / `hits_by_stat`(object：标准名 → `{"rolls": int, "value_sum": float}`) / `wasted_rolls_by_stat`(object：标准名 → 次数) / `main_stat_check`(list：`{"slot","actual","expected","matches"}`) / `threshold_report`(list：`{"stat","current","line","gap_text"}`) / `weakest_piece`(object\|null：`{"set_name","slot","effective_hits","wasted_rolls"}`) / `warnings`(list[str]，归一失败/解析失败/键名不识别等可疑项，评估照常进行) / `verdict`(str)。

### 2.3 计算规则（确定性，实现者无需再设计）
1. **词条名归一**：入参与名册词条名（`name_cn`）都经内置**归一表**（别名表+口径包表，见 §2.4）转为标准名后比对；未识别的词条词（三表都归不上）→ 该角色 `warnings` 追加一条，该词按无效处理（不得静默当标准名错数）。⚠ 标准名全集（尤其「攻击力」flat 与「攻击力提高」% 是否同名异义）实现第一步拉真实名册核对，归一表据此定稿（land 阶段 1 验收项）。
2. **数值解析**：`value` 是字符串（如 `"705"` / `"43.2%"`，依据：`src/sr_od/mys/sr_mys_client.py` SrPropertyEntry 冻结字段）——以 `%` 结尾 → 去 `%` 转 float（百分数值）；无 `%` → float（flat 数值）；解析失败 → `warnings` 追加并按 0 计。求和仅同名（归一后标准名）相加；**% 与 flat 不混桶的实现依据**：名册 name_cn 对生命值/攻击力/防御力的平坦与百分比**同名**（实现期核实，三源钉死：sr_codes PROPERTY_INFO_SNAPSHOT 快照 / fixture hkrpg_avatar_info_detail_sample.json / test_sr_mys_client 映射断言），唯一判别依据 = value 的 % 后缀——带 % 归一到「提高」类百分比标准名，不带归一到平坦名词本体（归一表已按此定稿，测试 `test_flat_percent_homonym_no_mixing` 锁定；本条修正了原稿「标准名不同天然不混」的错误前提）。
3. **计数遍历域**：遍历名册该角色的 `relics` 与 `ornaments` 两数组共 6 件（`pos_cn` 六部位：头部/手部/躯干/脚部/位面球/连结绳）。
4. **命中计数**：每条副词条归一后的标准名 ∈ 展开后的有效集合 → `effective_hits += 强化次数(times)`，并按标准名累加解析后 `value`；否则按标准名累加 `wasted_rolls_by_stat`。
5. **主词条核对**：仅对「躯干/脚部/位面球/连结绳」四部位执行（头部/手部主词条物理恒定，不参与核对、不进 `main_stat_check`）；`main_stat_check` 的穿错计数分母 = 传入期望的部位数。头/手两件的副词条正常计入命中与总次数。
6. **毕业线对照**：`stat_thresholds` 每键：current = 同标准名的主词条（若同名）+ 副词条解析值求和；gap_text = `达标 +X` 或 `差 X`（保留 1 位小数）。
7. **最弱件**：单件浪费次数最高者，并列取命中次数更低者；无副词条数据置 null。
8. **verdict 模板**：total_rolls=0 → `无遗器数据`；否则 `命中 {hits}/{total}（{ratio:.0%}）{主词条穿错 N 件；}{达标/差线摘要；}最弱件：{slot}（浪费 {n} 条）`——无主核对/无阈值时省略对应短句。
9. **跳过与缺名**：名册中找不到 `character_name` → 记入 `not_found`，不影响其他角色；`criteria` 存在重复 `character_name` → 整体 error（见描述 Returns 段）；`criteria` 为空列表 → 整体 error。
10. **结构防御**：`roster_data` 非 list、或元素缺 `name`/`relics`/`ornaments` 键 → error 信封（message 提示应传 `data` 字段内容），不得当空名册静默产出空报告。

### 2.4 常量表（实现第一步据真实名册定稿）
- **归一表**（别名/口径包 → 标准名或标准名集合）：**定义出处即本节**（速记词汇是本迭代定义的项目内约定，登记于 game-coach investment.md 设计决定节，见正本更新清单）。它与「不内置默认口径」的分界：归一表只做「词 → 标准名/集合」的机械展开，不含任何「该角色该堆什么」的判断；展开 miss 走 warnings 显式报告（规则 1），无静默错数。
  - 别名（社区用词 → 标准名，用词依据 = `mys_get_roster_detail` 字段名与角色档措辞）：攻击%/大攻击/攻击力百分比→攻击力提高；生命%/大生命→生命值提高；防御%/大防御→防御力提高；暴击→暴击率；暴伤/爆伤→暴击伤害；命中→效果命中；抵抗→效果抵抗；击破→击破特攻；充能/回能→能量恢复效率；治疗→治疗量加成；双暴→[暴击率, 暴击伤害]；速度→速度（同名直通）。
  - 口径包（速记 → 标准名集合）：双暴攻=[暴击率,暴击伤害,攻击力提高]；速双暴=[速度,暴击率,暴击伤害]；双暴生=[暴击率,暴击伤害,生命值提高]；击破速=[击破特攻,速度]；命中速=[效果命中,速度]；生命双暴=[生命值提高,暴击率,暴击伤害]。定稿判据 = 按阶段 3 的 12 人角色档口径行实际用到的包核对（不挂名册全集——口径包与名册词条名无关）。
- 两张表都是常量 dict，放纯计算模块顶部，注释只标「速记归一表；标准名全集经名册明细核对」与数据来源指针，不写核对过程叙事。

### 2.5 代码结构、验收名单与跨层依赖
- 纯计算模块：`src/sr_od/backend/mcp/relic_eval_tools.py`——`evaluate(roster_data: list[dict], criteria: list[dict]) -> dict` 纯函数 + 归一表常量；零 IO（依据：测试规范零副作用 + `character_tools.py` 的「纯函数+常量+注册分离」先例）。
  - 布局取舍：不并入 `mys_tools.py`（该文件是注册层，混入 200+ 行计算逻辑破坏其单一职责）；不新建 `backend/mys/` 目录（`backend/` 现有子包仅 mcp/http/entry，为单文件开新子包无收益）；不放 `src/sr_od/mys/`（该包是数据类/客户端层，被框架多端消费，塞 backend 计算语义会反向耦合）。
- MCP 适配：`src/sr_od/backend/mcp/mys_tools.py` 注册（描述/Returns 逐字用 §2.2；信封与状态透传沿既有惯例，依据：同文件四工具形态）；`roster_data` 缺省时经既有 controller 调 `mys_get_roster_detail` 取数，controller 非 success 信封**原样透传**。
- **验收名单（本迭代的评估对象，12 人，来自星启换队终案 v2 的三支队伍）**：N1 卡芙卡、海瑟音、黑天鹅、丹恒•腾荒；N2 黄泉、千冶•刃、缇宝、灵砂；N3 Archer、远坂凛、花火、阮•梅。
- **跨层依赖（知识侧配合项）**：game-coach 角色档为上列 12 人各补一行机器可读口径「有效口径: <口径包名或枚举>」（依据各档「副词条」节改写，随知识库维护流程维护）——本迭代阶段 3 的交付物；其余角色的铺开归 game-coach 维护流程，不在本迭代。
- 字段命名原则：英文小写下划线、名词短语自释（`effective_substats` 而非 `eff`/`list1`）；中文只出现在工具描述与输出 `verdict`/`warnings` 文案。

### 2.6 关键取舍
- **口径参数化 vs 内置默认口径**：选参数化。内置默认会与角色档形成双真源必然漂移，且定位差异场景给错数（裁定记录：game-coach investment.md「有效词条计数工具的设计决定」节）。
- **速记归一表内置 vs 不内置口径的分界**：归一表只做词→集合的机械展开（无角色判断语义），且展开 miss 走 warnings 显式报告——不违反「不内置默认口径」决定；表定义出处登记于 game-coach investment.md（正本更新清单）。
- **v1 按次数计数 vs 按滚动值域加权**：选次数。加权需要词条滚动值域常量表，收益与复杂度未经实战验证——先出次数报告看是否够诊断用，加权列为外溢议题（见 §1 明确不解决）。
- **roster 传入 vs 工具自拉**：两者都支持、传入优先。全量名册载荷大（64 角色数百 KB）且接口有风控消耗，调用方已拉过就不重复拉。
- **不设「不堆清单」入参**：有效清单的补集语义已完整覆盖无效判定；角色档「不堆」清单的实际用途是人工配口径时的自查（防止把不该堆的放进 effective），不进工具入参。
- **不设「阵容小覆盖」结构**：基础口径+小覆盖由调用方组装成最终口径后传入，工具只认最终口径——组装是 agent 的知识工作，不是工具的结构。
- **name_cn 归一路线 vs pt 码匹配路线**：选 name_cn+归一表。词条 pt 码不在 `character_to_dict` 冻结字段集内，透传 pt 需扩冻结契约（影响既有消费方，成本高于别名表）；别名表的版本维护责任归 MCP 常量（随阶段 1 名册核对更新）。若实现核对发现明细实际含稳定词条 id 字段，则在本阶段改选码表路线（决策规则已定，非留白）。
- **thresholds 用词条求和口径**：与角色档「转化上限」的面板口径不保证等价（面板含基础属性与外部 buff 口径）——调用方给线时按词条求和口径换算，已在 §2.2 字段说明声明；不做面板口径换算（需要面板基线数据，超出本工具职责）。
- **v1 无全队打分**：`team_summary` 只做确定性排序（占比升序），「最弱角色是谁」由调用方从排序读取；带权重的全队评分属打分范畴，不做。
