# 2026-11-13-trait-v47-rebuild 对抗审查攻击报告

> 攻击者走查口径：三核（无前提 / 规范遵循 / 治本），全部结论只对代码与数据实测。
> 实测源 = `config_v4.7.json` / `lineups_Hot.jsonl` / `trait_api_research.md` / src 消费面全量 grep / skill references / 正本文档 / `.debug/progress` 挂账板 / 米游社 wiki 频道 240（网络可达）。
> 严重度：**阻断** = 定稿前必须修；**应修** = 定稿前应修（影响可执行性或锚点真实性）；**备忘** = 记录在案，随修订顺手处理。

## 1. 攻击点清单

### A1【阻断】总纲契约与详设结构矛盾：Trait.members 是方法还是字段

- **位置**：design.md §2.2「数据层对外形态」第 4 条 ↔ details/trait-data-layer.md §1 数据结构 + §1 成员兼容形态说明。
- **问题**：总纲契约写「`Trait.members()` 实例方法保留 = ……方法语义与旧版一致：返回角色名列表」；详设却定义 `members: tuple[str, ...]` 为 **dataclass 字段**，并指示迁移时「改为读 `trait.members` 字段」。同一名字不能既是 frozen dataclass 字段又是方法；两文不可同时成立。
- **依据**：design.md §2.2（契约自称「唯一总纲定死的接口，两详设共同遵守」）；trait-data-layer.md §1 `members: tuple[str, ...]` 字段定义；实测 src 内 `.members(` 调用点仅 `telemetry/cw_win_model.py:49`（无参调用），可迁移到字段读，但总纲/详设必须收敛为一种。
- **建议**：以详设为准（字段 + 调用点迁移），改写总纲契约行；契约是唯一接口权威，措辞错误的契约比没有契约更危险。

### A2【阻断】count_mode 契约无详设节承接、无 landing 阶段实施（系统级变化 #5 悬空）

- **位置**：design.md §2.1-5 + §2.2「count_mode 契约」；consumer-migration.md 全文（无 count_mode/board_star3 字样）；landing.md 3.1–3.7 全部范围（无一处含板面计数改动）。
- **问题**：总纲把「板面计数侧并行产出 `board` 与 `board_star3` 两计数；激活判定侧按 `trait.count_mode` 选取」定为跨详设契约，但 ① 详设一 §4 只论证「count_mode 放数据层不放策略层」的归属取舍，未设计 board_star3 的计算（单位星级从哪取、recount 签名怎么变）；② 详设二的迁移清单（A/B/C 三类）不含 `cw_bond_equips`/`_recount_board` 的计数改动；③ landing 七个阶段没有任何一个的范围覆盖此契约。总纲系统级变化 5 条，落地映射只有 4 条。
- **依据**：design.md §2.1-5、§2.2 契约原文；landing.md 各阶段范围逐条核对；实测 `_recount_board` 单一源在 `kernel/cw_bond_equips.py:176`（`board: dict[str,int]`，无星级入参——board_star3 需要 3 星判定源，属未回答的实现前提）。
- **建议**：二选一并写明——要么本迭代就落契约（详设一补 board_star3 计算设计：星级数据源、recount 口径、消费侧选取点；landing 增阶段/并入 3.5），要么契约显式声明「消费侧实施归策略批，本迭代只落数据字段」，并把总纲 §2.1-5 的措辞收敛为「建模不接线」。现状 = 读了总纲以为会实现、实际无人认领。

### A3【阻断】「category 零消费点」主张被代码证伪，真实消费点无迁移处置

- **位置**：design.md §1-2（「`FactionInfo.category`（四分类）当前消费点为零（实测 grep，仅命中投资环境自身同名字段）」）与 §2.1-1（「category 不建」）；consumer-migration.md A 类对 `cw_gain_chain.py` 的处置（纯字段路径）。
- **问题**：`kernel/cw_gain_chain.py:2741-2743` 真实运行时消费 category：`activated = {f for f, info in FACTIONS.items() if info.category != 'independent' and ...}`（策略卡羁绊档发放的「非独立羁绊激活全集」判据）。category 不建 + `cw_factions.py` 退役后，此处 AttributeError；且它被归入 A 类「纯字段路径」，语义替换（`category != 'independent'` → 何物）无人负责。
- **依据**：实测 cw_gain_chain.py:2741-2743；全仓 grep `\.category` 无其他 FactionInfo 消费点（claim 的「零」错在这一个，其余确为投资环境同名字段）。
- **建议**：① 总纲 §1 修正消费点计数；② 详设二为 cw_gain_chain 此判据定迁移语义——注意新 `trait_type=2` ≠ 旧 `independent`（旧独立 = 单角色 1 层 7 个；新 type 2 = 特殊羁绊含巡海游侠等多成员档，见 config 300302），不能机械等值替换，需按「独立羁绊」的业务定义（tiers=(1,)？官方口径？）显式重定义并写进详设二。

### A4【阻断】消失档映射清单实体错误：漏狼狩、误列师徒，且与总纲计数互斥

- **位置**：design.md §2.1-3（「消失 19」）↔ details/consumer-migration.md §1 消失档（「旧 32 − 上 12 = 20」+ 20 名清单含「师徒（ISOLATED）」）。
- **问题**：三处互相矛盾且与代码不符——① 总纲说消失 19、详设算 20（32−12=20 才对）；② 消失清单含「师徒」，但实测旧 `FACTIONS` 32 条**无师徒**（师徒只是 `gen_factions.py:48` 的 `ISOLATED` 排除常量，cw_gain_effects.py:1454 注明「师徒羁绊非注册羁绊(FACTIONS 零条目)」），它已在详设 §3 退役清单单独处理，再进消失档是重复+错位；③ 消失清单**漏「狼狩」**——狼狩是旧 32 实体（cw_factions.py:59，有 tiers/desc），按清单它将不被任何 B 类处置覆盖。
- **依据**：实测旧 FACTIONS 32 条逐名比对：消失真集 = {贝洛伯格、狼狩、盛会之星、列车同行、命运圣杯、昼之半神、夜之半神、银河学者、公司、量子同频、减益、燃血、战技点、挚爱之人、魔术师、大守护者、命运卜者、救世主、头号玩家、领航员}；文档清单把狼狩换成了师徒。
- **建议**：详设二 §1 消失档按真集重列（20 名含狼狩、去师徒）；总纲 §2.1-3 的「消失 19」同步改 20；狼狩的消费点（如 `currency_war_config.py` DEFAULT_FACTION_PRIORITY、cw_plaza_comps 知识条目）随消失档统一走 B 类/边界处置。

### A5【应修】「FACTIONS 全部消费」清单漏 3 个真实消费文件，文件数主张对不上清单

- **位置**：details/consumer-migration.md §问题与约束（「实测 26 文件……约 60 处引用」）与 §2 A/B 类清单。
- **问题**：A+B 类合计枚举 16 文件，实测 import/使用 `FACTIONS` 的文件至少 17 个，以下 3 个不在任何清单：① `telemetry/cw_win_model.py:26,49`（`FACTIONS['持续伤害'].members()` DOT 件池派生）；② `strategies/impl/mandate_v1/shop.py:85,1756`（`FACTIONS.get(_tag)`）；③ `obs/cw_faction_obs.py:36,120-122`（OCR 名标准化门：`raw in FACTIONS` + `list(FACTIONS)` 键序遍历——键集换血后此门的语义面是 B 类级，不是机械替换）。`cw_factions.py` 3.3 退役后这三处 import 即断。
- **依据**：src 全量 grep `FACTIONS|cw_factions`（147 命中逐文件归并）；「26 文件」无法由清单（16）或实测 import 面（17）复核。
- **建议**：三文件补进清单（前两个 A 类、cw_faction_obs 按 B 类语义处置申报）；「实测 26 文件」改为可复核的精确计数口径（import 面 grep 式罗列或直接引用 grep 模式）。

### A6【应修】C 类删除清单 2 漏 1 错：cw_observation 与 deploy_search 有真代码、move_unit 路径不存在

- **位置**：details/consumer-migration.md §2 C 类（14 文件）；landing.md 3.6 文件面「C 类清单 14 文件」。
- **问题**：① `obs/cw_observation.py:1705-1710` 有开拓者归一真代码（import `is_trailblazer/trailblazer_form` 并调用），不在 C 类；② `strategies/impl/mandate_v1/deploy_search.py:184-199` 有 `SIDE_PICK_DUAL_BONDS` 三处真代码使用（枚举键归一/标签选边），不在 C 类——若 3.6 删 `cw_chars` 侧符号，此文件即断；③ 「`operations/cw_action_report/move_unit.py`」路径不存在，实际为 `kernel/cw_action_report/move_unit.py`。3.6 的全仓 grep 清零判据最终会兜住，但 worker 按清单文件面开工即撞清单外文件（触发停手令），等于清单不可信。
- **依据**：grep `is_trailblazer|trailblazer_`（42 命中逐处定性）、grep `SIDE_PICK_DUAL_BONDS|side_pick_bond`；Test-Path 实测 move_unit 真实路径。
- **建议**：C 类补 cw_observation.py 与 deploy_search.py（后者若归 A 类迁移则该文件拆「A 类字段 + C 类选边段」双处置申报），move_unit 路径改正；3.6 文件面同步。

### A7【应修】A 类清单路径 `criteria/predicates.py` 不存在

- **位置**：details/consumer-migration.md §2 A 类；landing.md 3.4 文件面「A 类清单 13 文件」。
- **问题**：实测唯一 predicates.py = `strategies/impl/mandate_v1/statefn/predicates.py`（FACTIONS 消费 :242,:251）。`criteria/` 子目录下只有 priority.py/sell.py，无 predicates.py。清单路径按字面解析即落空。
- **依据**：glob `src/sr_od/application/currency_war/**/predicates.py` 仅 1 命中。
- **建议**：改为真实相对路径 `statefn/predicates.py`（或全路径）。

### A8【应修】B 类 cw_invest_channels 处置不可执行，且与 3.5 完成判据互斥

- **位置**：details/consumer-migration.md §2 B 类末条（「`cw_invest_channels.py:232`（ENGINE_SYNERGY_FACTIONS 引擎阵营表）……键更新为沿用名」）；landing.md 3.5 判据「grep 复核消失名清零」。
- **问题**：① 该表（定义在 :89）**键**是增益名（量子力学/钢铁美学/离火燎原），**消失羁绊名在 value**（`('量子同频',)`、`('减益',)`）——「键更新为沿用名」无的放矢；② 量子同频/减益是消失名，「更新为沿用名」无值可换；③ 该文件不 import FACTIONS，「保证 import 不炸」本来就是空条件；④ 若按「引擎重组归策略批」原样保留表内容，则 3.5 判据「消失名 grep 清零」在 src 内必然不成立（同文件自相矛盾）。
- **依据**：实测 cw_invest_channels.py:89-98、:232。
- **建议**：该条处置改写为「value 含消失名的手编策略表：本迭代加退役标注（注释声明待策略批重组），不更新内容」；3.5 判据的 grep 给出明确范围（如「B 类清单文件内消失羁绊名清零，手编策略表的退役标注段除外」），并同步声明 cw_chars/装备数据/fixture 等历史数据面豁免，否则判据按字面永不可过。

### A9【备忘】B 类 cw_intention 条目定性错误：行号指向注释举例，非「燃血成员名单」

- **位置**：details/consumer-migration.md §2 B 类（「`cw_intention.py:592-593`（燃血成员名单）——燃血消失，标注退役」）。
- **问题**：cw_intention.py:586-597 的逻辑是泛化的（comp 档键 × `factions∪schools` 交集，无燃血特判）；592-593 是**注释**里的举例（「万敌单C 档 0 燃血=schools……Ring1:燃血 8 成员 3 名缺位」）。把注释举例当「成员名单逻辑段」申报退役 = 清单条目失真。
- **依据**：实测 cw_intention.py:580-599。
- **建议**：该条降级为「注释举例含消失名，随注释顺手订正」，从 B 类语义处置中移出。

### A10【应修】landing 3.3 完成判据依赖后置阶段，且与首节常规检查自相矛盾（违反阶段粒度）

- **位置**：landing.md 3.3 完成判据第 2 条（「旧 `cw_factions.py` 无残留引用（**阶段 4-6 完成后复核**）」）对照 iteration-design.md §3.1「判据依赖另一阶段未完成部分 = 划分不当」与首节「本阶段直接受影响测试全量一次通过」。
- **问题**：3.3 删 `cw_factions.py` 时全部消费方（A/B/C 类共 19+ 文件）尚未迁移，阶段结束时 src 处于 import 断状态：本阶段自己的常规检查（受影响测试全量通过）不可能满足；「无残留引用」判据声明为跨阶段复核。虽已用「与阶段 4 同一提交序列连续落地」缓解，但阶段=独立派工独立验收的定义被打破——任何一个后继阶段中断，主线停在断态。
- **依据**：landing.md 3.3 原文；iteration-design.md §3.1 阶段粒度条。
- **建议**：重划依赖方向：3.3 改为「新增 cw_traits_data.py 落库（不动旧文件）」，旧文件退役移入一个收尾阶段（依赖 3.4/3.5/3.6 全部完成，判据 = 全仓 grep `cw_factions` 清零 + 测试全量）；或 3.3 与迁移并成单阶段。

### A11【应修】承接指针错位：「第 3 步羁绊域」实为 checklist 第 4 步

- **位置**：design.md §0（「承接 = 版本适配总流程……第 3 步『羁绊域』」）。
- **问题**：version-update.md §2 Checklist 实测：1 确认在线 / 2 拉配置判型 / 3 角色域 / **4 羁绊域**（§3.2）。「第 3 步」指向角色域，差一位。
- **依据**：skills/sr-od-dev-currency-war/references/version-update.md:29-32。
- **建议**：改为「第 4 步」或改用「§3.2 羁绊域」锚。

### A12【应修】正本更新清单锚点不存在：strategy-docs/README.md 无「模块地图 data/ 行」

- **位置**：landing.md 正本更新清单第 6 行（「strategy-docs/README.md：模块地图 data/ 行（cw_factions → cw_traits_data）← 3.3」）。
- **问题**：实测该文件全篇无 `cw_factions`、无 data/ 模块行、无「模块地图」节；最接近的是 §3 表中「代码注册表（cw_chars/cw_shop_odds/cw_equipment_data 等）」泛指行。清单条目按字面不可执行（末阶段判据 = 清单清零）。
- **依据**：grep 该文件 `模块|地图|traits|羁绊|data|cw_factions` 逐条核对标题结构（§1–§6 无模块地图）。
- **建议**：条目改写为真实目标（如「§3 关系表：代码注册表示例行补入 cw_traits_data」），或删除该行。

### A13【应修】总纲契约引用不存在的模块 `cw_state._recount_board`

- **位置**：design.md §2.2 count_mode 契约（「板面计数侧（`cw_bond_equips`/`cw_state._recount_board`）」）。
- **问题**：`kernel/cw_state.py` 不存在（实测 Test-Path False；仅 `cw_state_journal.py`）。`_recount_board` 单一源在 `cw_bond_equips.py:176`——总纲把代码注释里一个陈旧的别名（cw_bond_equips.py:178 docstring 亦写「cw_state 侧」，系注释自身陈旧）当成了真实模块名写进契约。iteration-design.md §5-4 卡点明确「定稿前逐一核设计引用的每个符号存在性」。
- **依据**：glob `**/cw_state*.py`；grep `_recount_board` 定义与引用链。
- **建议**：契约改为 `cw_bond_equips._recount_board`；若 A2 采纳「接线归策略批」，此处随 A2 一并改写。

### A14【应修】count_mode 引文校验的 desc 取数源未写明，生成器输入清单缺 role_list[].trait_details

- **位置**：details/trait-data-layer.md §问题与约束（输入源三份）与 §2-4（「覆盖表逐条带 desc 引文校验」）。
- **问题**：config 骨架 `trait_info_list` 的 `simple_desc` 实测为空串；千星商会引文实测住在 `role_list[].trait_details[]`（role id=150302，trait_detail id=100602）。详设输入清单只列了 trait_info_list 侧用途，未声明生成器还要读 config 的 role_list trait_details 作引文源——实现者按输入清单开工即找不到引文。
- **依据**：实测 config_v4.7.json（trait_info_list[千星商会].simple_desc=''；role_list id=150302.trait_details 含千星商会 desc 原文「每上场1位3星【千星商会】角色，将激活1级羁绊效果。……」）。
- **建议**：§2-4 补一句「引文源 = config role_list[].trait_details[]（id 对齐 trait_id）」，输入清单同步补列。

### A15【应修】跨迭代接口未定锚：翻译查表依赖的「plaza id 索引」当前不存在且形态未约定

- **位置**：details/trait-data-layer.md §2-3（「查角色注册表（`cw_chars.CHARACTERS` + plaza id 索引）」）。
- **问题**：实测 `data/` 现无任何 plaza id → 角色的索引符号；该索引拟由进行中的角色注册表重建批（`.debug/progress/2026-11-14-cw47角色注册表重建/`）产出，但本设计未锚定其接口（符号名/键型/查表入口）。两个并行迭代的接缝无契约，3.2 实现者「凭这份」无法写翻译段——这正是 iteration-design.md §2.2 要求在总纲定死的接口类内容（只是跨迭代）。
- **依据**：grep `data/` 下 `plaza_id|by_plaza|PLAZA_ID` 零命中；总纲 §2.3 仅声明依赖存在，未声明接口。
- **建议**：总纲 §2.3 或详设 §2-3 写明查表契约（「角色批须提供 X 符号：dict[str plaza_id, Character]，缺失时本批停手回角色批」），并与角色会话对齐。

### A16【应修】迁移面缺申报：currency_war_config.py 默认偏好含消失/改名前名

- **位置**：details/consumer-migration.md 全文（未提及 currency_war_config.py）；landing.md 3.5 判据（消失名清零）。
- **问题**：`currency_war_config.py:15-17` `DEFAULT_FACTION_PRIORITY = ["贝洛伯格", "仙舟", "盛会之星", "昼之半神", "巡海游侠", "群攻", "追击", "狼狩"]`——含 5 个消失名 + 改名前名「仙舟」。它是 GUI/YAML 可改的策略偏好默认值（meta 层）。清单未申报其处置：按 3.5 字面 grep 它会红；按「策略批暂缓」豁免则豁免范围未声明。另注：清单漏列的「狼狩」消费点正在此文件（与 A4 联动）。
- **依据**：实测 currency_war_config.py:12-17（文件头自述「版本更新后以图鉴校准」）。
- **建议**：边界处置节补一条「策略偏好默认值（currency_war_config DEFAULT_*）含旧名：随策略批校准，本迭代豁免声明进 3.5 判据范围定义」。

### A17【备忘】设计正文过程叙事残留：「范围侦察已完成」

- **位置**：design.md §2.1-4（「范围侦察已完成，登记挂账板」）。
- **问题**：iteration-design.md §5-3 硬规则——无过程叙事，进度只住 README；「已完成」是进度态词，且「侦察」结论（哪些文件）已在详设 C 类体现，本句不承载设计信息。
- **依据**：iteration-design.md §5-3。
- **建议**：删「范围侦察已完成」，保留用户裁定指针；挂账板指针化见 A18。

### A18【备忘】挂账板引用无路径指针，且挂账板批归属与 landing 漂移

- **位置**：design.md §1/§2.1-4、consumer-migration.md §5、landing.md 3.6（三处「挂账板」均无路径）；`.debug/progress/CW跨迭代挂账.md` §一.0。
- **问题**：① 三条挂账引用（装备贡献表 L2 / 存量旧红 2 个 / 开拓者选边删除）实测**内容均真实存在**于该板，但设计文档不给路径，依据不可就地回查（iteration-design.md §5-1 依据=来源文档+节）；② 该板开拓者条目写「**与注册表重建同批执行**」，而本设计划入本迭代 3.6（注册表重建仅为前置）——两处批归属不一致，按「阶段小节=账本唯一源」精神应以本设计为准回写挂账板。
- **依据**：实测挂账板 §一.0 三条全文。
- **建议**：引用处补「`.debug/progress/CW跨迭代挂账.md` §一.0」路径；正本化时把挂账内容收进迭代工件或正本（.debug 板寿命不受 git 保护）；回写挂账板批归属。

### A19【备忘】「新增 17」行实列 18 项（守护双列）

- **位置**：details/consumer-migration.md §1 新增档行。
- **问题**：行标「新增（17）」但列表含 18 项——第 13 项「守护（若非改名）」与改名档「护盾→守护」重复占位。实测 config：29 = 沿用 10 + 改名 2（仙舟舰队/守护）+ 新增 17，「守护」确属改名，不该再进新增行。
- **依据**：config_v4.7 trait_info_list 29 名单逐名比对（沿用 10 全部命中、守护/仙舟舰队在列）。
- **建议**：新增行删「守护（若非改名）」或移入改名行的括注。

### A20【备忘】trait_desc 富文本渲染规则未入详设

- **位置**：details/trait-data-layer.md §1（`trait_desc` 注释「富文本已渲染为纯文本」）；§2 聚合算法无渲染步骤。
- **问题**：帖内 `trait_desc`/`simple_desc` 实测含 `<property>/<color>` 富文本标签（调研报告 §7 样本同证），渲染是聚合的必经步骤；渲染规则（property→中文名映射来自 config `role_property_list`、未知标签告警策略等）只存在于旧 `gen_factions.py` 的 render_rich 实现，详设未引用为依据。实现者大概率会沿用旧管线，但按「实现者无需再设计」口径这属于靠文件现状兜底而非靠设计。
- **依据**：旧 gen_factions.py:60-100 渲染管线；调研报告 §7。
- **建议**：§2 补一行「渲染沿用旧 render_rich 管线（prop_map = config role_property_list，未知 property 告警不静默）」，正本化时进动机段。

### A21【备忘】帖内 remarks 字段去向未声明

- **位置**：details/trait-data-layer.md §1 Trait 结构（无 remarks 字段）与 §2-2（键集实测含 remarks）。
- **问题**：帖内 `remarks[]`（术语注释，如【连击率】释义）被静默丢弃，详设未声明「不采 remarks」是有意取舍还是遗漏。当前无消费面，风险低，但正本化时数据结构口径应自足。
- **依据**：首行键集实测含 remarks；调研报告 §7 remarks 语义。
- **建议**：§2-2 补一句「remarks 不采（无消费面；术语注释随 desc 全文自足）」，或给 Trait 加字段。

### A22【备忘】README 阶段计数口径含混：0/7 vs 实际 8 个小节

- **位置**：README.md 进度（「落地:阶段 0/7 done」）；landing.md 含 3.1–3.7 共 7 个实施阶段 + 「末阶段：正本更新」。
- **问题**：末阶段是否计入 y 未约定，7/8 两读。iteration-design.md §3.1 把正本更新列为固定末阶段（也是阶段）。
- **依据**：landing.md 小节清点。
- **建议**：README 写「阶段 0/8（含正本更新）」或「7+末阶段」，二选一固定口径。

### A23【备忘】A 类含零 import 文件：cw_env_grants.py 仅注释引用

- **位置**：details/consumer-migration.md §2 A 类（cw_env_grants.py）。
- **问题**：实测该文件不 import FACTIONS，仅 :195 注释提「档位单一源 = FACTIONS[bond].tiers」。归入 A 类无害但失真——「13 文件」实为 12 个代码消费 + 1 个注释订正。
- **依据**：grep 该文件 import 面。
- **建议**：A 类标注「注释级」，或在清单注明该文件只改注释。

### A24【备忘】wiki 侧两项主张本次只核到半：词条总数 ✓、id 清单与缺收项未逐项核

- **位置**：details/trait-data-layer.md §2-5（「27 词条（content_id 实测清单 8210-8236）」「wiki 缺收的 2 条（守护/治疗，实测）」）。
- **问题**：网络实测频道 240（羁绊）返回 retcode=0、**词条数 27 ✓**；但 id 与 name 在词条子结构内，本次未拆出逐条 content_id，8210-8236 连续性与「缺收守护/治疗」两项**未核**（不构成反驳，仅标注核验深度）。
- **依据**：`https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list?...channel_id=240` 实测响应（27 元素于根节点 list）。
- **建议**：无需改设计；3.1 阶段执行 wiki 交叉时顺带复核 id 清单。

### A25【备忘】核三·「纯官方数据」表述与实际取值口径的张力

- **位置**：design.md §0 迭代目标（「数据层回归纯官方数据」）。
- **问题**：骨架 id/名/图标/类型 = 官方 config 直读 ✓；但 layers/desc/成员 = 攻略帖快照（平台侧存储的历史配置快照，含降级快照需去重），wiki = 社区维护。设计在 §1-4 与详设取舍里是知情的（11 参数变体实测、去重规则、wiki 报告不落数据），治本判据成立；唯「纯官方」措辞在正本化时宜收敛为「官方字段形态 + 官方平台帖值」，避免读者误读为 config 直读全量。
- **依据**：config 骨架 layers/role_ids/simple_desc 实测空；调研报告 §6.1 降级快照实证。
- **建议**：正本更新阶段把该句措辞收敛（不阻塞定稿）。

## 2. 已核实成立的主张（抽样实测，供修订时免查）

以下设计主张经实测**成立**，修订时无需再查证：

- config 骨架：trait_info_list 34 条；type 0/1/2/3 = 12/11/6/5（29 条过滤口径成立）；role_list 63；29 名单与沿用 10/改名 2（仙舟舰队、守护）/新增 17 全部对上。
- 帖子语料：lineups_Hot.jsonl 1000 行；帖内 trait 条目键集与详设 §2-2 逐键一致（含 remarks）；全量帖覆盖 29 种 trait 且零「零层」条目；前 100 帖已全覆盖 29（详设 §4 的「100 帖实测全覆盖」成立）；帖级 `created_at` 字段存在（去重并列规则可执行）。
- 千星商会：官方引文逐字成立（role id=150302 / trait_detail id=100602，仅富文本色标签差异）；`Trait.count_mode` 建模依据可靠。
- 星神★阿哈 151112/151122/151132 三档同名单（rarity 4/5/7）；is_hide 现役仅丹恒•腾荒一条（隐藏条目过滤机制可用）。
- B 类行号锚点：cw_deploy_logic.py:91-92、cw_engine_facts.py:48-49、cw_system_cards.py:51-53 全部命中；cw_investments 对拍闸实际在 5872-5924（申报 §5872-5922 基本准确）。
- 生成器现状 = 纯对拍器、旧数据源 `.debug/temp` trait_detail.json、`MEMBER_EXCEPTIONS`（布洛妮娅隐藏变体）与 `ISOLATED={"师徒"}` 均与详设描述一致；成员自报派生面（`cw_chars.CHARACTERS` factions/schools/independent、`chars_by_faction`）存在可用。
- 装备 `stacking` 先例（cw_equipment_data.py:28）、生成器文件头声明模式（cw_invest_data/cw_plaza_posts 同款）成立。
- 正本与 skill 锚点：docs/game/currency_war/data/README.md:19 `cw_factions.FACTIONS,32` ✓；docs/game/currency_war/README.md:36 更新流程节 ✓；data-collection.md 羁绊行（两跳通道描述）✓；version-update.md §3.2 ✓；SKILL.md:48 确提及 cw_factions（清单条件项成立）；sr-od-test/test/sr_od/application/currency_war 路径 ✓；角色批在飞目录 ✓。
- 挂账板三条内容真实存在（路径指针问题见 A18）。
- 旧注册表 76 名主张 ✓（实测 _ch 计数 76；代码注释「74 名」与 data README「72」为陈旧值，不是设计的错）。

## 3. 收敛判定

**当前攻击面下不可进定稿。**

阻断点清单（修完才可定稿）：

1. **A1** members 方法/字段契约矛盾——总纲 §2.2 契约行按详设改写；
2. **A2** count_mode 契约悬空——补详设节与 landing 阶段（或显式降级为「本迭代只建模不接线」并同步总纲措辞）；
3. **A3** category 消费点证伪——总纲 §1 计数修正 + cw_gain_chain:2741 判据的迁移语义（注意 trait_type=2 ≠ 旧 independent）进详设二；
4. **A4** 消失档清单实体错误（狼狩漏列/师徒误列/19↔20 矛盾）——按旧 32 条真集重列并同步总纲。

应修 11 项（A5–A8、A10–A16）与备忘 10 项（A9、A17–A25）随修订批量处理，其中 A5/A6/A7/A16/A8 属同一根因——**迁移清单未以「全量 grep 实测」方式生成**：建议修订时以 grep 输出为单一源重生成 A/B/C 三类清单（文件、符号、行号、路径），再人工标注处置档位，杜绝再次靠手抄清单漏项。

治本核验（核三）结论：§1 归层（约定层：官方+人判混存不适应官方重做+多源采集）成立；§2 方案（生成器恢复生成职责 + 三源对拍闭环 + 数据层纯官方字段 + 采集缓存落持久区）修的是根，非症状；「desc 判读结构化元数据进数据层」已有装备 stacking 先例，本迭代 count_mode 是该模式的第二例但方向一致且已在取舍节援引先例，未构成「同族逐件修需升架构级」。设计骨架（数据层结构、聚合去重/翻译/对拍算法、阶段划分主体、验收凭据形态）质量良好，数字主张实测命中率极高——修复上述四阻断点后，本设计具备定稿条件。

## 4. 第二轮复攻（2026-11-14，接手责任人执行）

> 复攻口径同第一轮（三核+全实测）。第一轮 25 点修订逐项验证：A1/A2/A3/A4/A10/A11/A12/A13/A14/A15/A16/A17/A18/A20/A21/A23 修订到位（契约收敛字段、建模不接线两处收敛、消失档真集、阶段重划、查表契约文本、引文源补入、路径指针、渲染与 remarks 声明）；**A19 未修订**（见 B8）；A22 以「0/8 不含正本」口径落定可接受；A24/A25 属落地期与正本化期动作，不在本轮。

### B1【阻断】同名多档 id 的查表契约覆盖缺口（生成器必炸点）

- **位置**：trait-data-layer.md §2-3 翻译规则 ↔ consumer-migration.md「跨迭代查表契约」。
- **实测**：帖内阿哈三档 id 全部出场——151112×149 / 151132×81 / 151122×21（1000 篇全量帖统计）。聚合 role_ids 并集必然含高费档 id；而角色批按银狼先例只建起始档 151112（高费档进对拍例外、不建条目）——查表索引若只覆盖注册表条目 id，翻译 151122/151132 即 fail-closed 非零退出，3.2 无法完成。
- **建议**：查表契约补覆盖范围条款——「索引须覆盖 config role_list 全部条目 id（含升格高费档等例外档）」或补同根档归一规则；与角色会话对齐后写死契约文本（A15 已立契约载体，补覆盖范围一句）。
- **落点（2026-11-14 用户裁定）**：实测推翻建议前提——角色批 v4.7 注册表实际做了多档建模（阿哈三档三条目各带 source），高费档 id 天然可覆盖；契约形态收敛为**派生形态**（消费方从注册表 source 字段现场派生映射，不要求角色批交付符号），文本见 consumer-migration.md「跨迭代查表契约」。

### B2【应修】召唤型成员的口径与激活特例未声明

- **位置**：trait-data-layer.md §2-3（is_hide 过滤规则）+ §1（members 字段语义）+ §4（取舍节）。
- **实测**：丹恒•腾荒(141402) is_hide=True、帖内上场 0 次（1000 篇）、双龙吟帖内 role_ids=['121302','141402']、帖内 layers 最大 2 档——腾荒是双龙吟的**后台召唤物**（「饮月在后台区域召唤腾荒」），非玩家可组队员；双龙吟激活 = 上场饮月 + 召唤物，**通用人数计数（板面只见上场员工）永远数不到召唤物**——不服从 count_mode TOTAL/STAR3 任一口径。
- **问题**：①「members 取哪个口径」未声明——is_hide 过滤后 = 可组队员口径（无腾荒），官方 role_ids = 含召唤物口径——两口径差集（召唤物）无声明，成员对拍人裁时无裁定依据；②召唤型激活特例（双龙吟类）无登记——策略批接线 count_mode 时会撞上第二种特例而无建模位。
- **建议**：①members 口径声明为「可组队员（is_hide 过滤后）」，与官方 role_ids 的差集进例外清单人裁（召唤物裁决 = 不算成员，板面计数消费链天然只触可组队员）；②§4 补「召唤型激活特例登记」（双龙吟类，与 count_mode 接线同批归策略批）。

### B3【应修】members_of 为零消费接口

- **位置**：trait-data-layer.md §1 兼容形态说明（「members_of() 仅保留给确需按名查询的散点」）。
- **实测/逻辑**：总纲契约（A1 修订后）明确唯一调用点 `telemetry/cw_win_model.py:49` 迁移为**字段读**——按名查询的「散点」全仓为零，members_of 无消费方。数据建模方法论「没有消费点的属性/接口不建」（data-collection.md §五）同判。
- **建议**：删 members_of；按名查询 = `trait_by_name[name].members` 一行事。

### B4【应修】黑话残留「定谳」

- **位置**：consumer-migration.md:7（「第一轮对抗 A5-A8 定谳」）。
- **依据**：T-435/T-438 术语裁定「定谳→定案」已全域清偿；挂账板 §二.5 黑话回潮复查条款要求连续两轮零新增——本文件在首轮攻击时已存在该词面而未被清，属回潮。
- **建议**：改「定案」。

### B8【应修】第一轮 A19 未修订：新增档行仍 18 项标 17

- **位置**：consumer-migration.md §1 新增行。
- **实测**：行标「新增（17）」实列 18 项——「守护（若非改名）」与改名档重复占位仍在（A19 原文建议未执行）。
- **建议**：删「守护（若非改名）」，行标核实为 17。

### B5【备忘】巡海游侠 type 0→2 迁移的策略语义翻转宜点名

- 沿用 10 档唯一换 type 的羁绊；§2.1 判据重定义后其策略卡发放资格从旧口径变新排除集。迁移阶段差集落档时对此例显式核对（旧 category 值迁移时现查），作为策略暂缓批恢复时的行为变化输入。

### B6【备忘】聚合器脚本名 gen_factions 未对齐官方 trait 口径

- 新数据模块 cw_traits_data 已对齐官方（trait），生成器仍叫 gen_factions（旧翻译词「阵营」）。角色域刚完成同名性质的对齐批（flows→schools）；本迭代落地时顺手定名（gen_traits.py）并同步正本更新清单指针，或在设计声明保留理由。

### B7【备忘】wiki 包含性比对的「关键数值词命中」未定义算法

- trait-data-layer.md §2-5 比对维度「档数一致 + 关键数值词命中」——数值词提取规则未写。建议补一句定义（desc 中数字与百分号串的集合）或声明「不自动化判等，差异全量进报告人裁」。

## 5. 第二轮收敛判定

**B1 修毕（查表契约覆盖范围条款落定，最终形态=派生，见 B1 落点注）+ B2/B3/B4/B8 修订后，设计具备定稿条件。**B5-B7 随修订顺手处理或在对应阶段执行。
