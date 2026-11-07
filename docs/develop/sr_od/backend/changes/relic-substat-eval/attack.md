# relic-substat-eval 设计对抗审查报告

- 攻击对象：本目录 design.md / landing.md / README.md（迭代设计状态：草案）
- 规范依据：`docs/develop/harness/iteration-design.md` §5 写作硬规则、§7 三核；项目 `AGENTS.md` §7/§8/§9/§10；`docs/develop/sr_od/backend/mcp-implementation.md`、`docs/develop/sr_od/backend/mys.md`、`docs/develop/sr_od/backend/mcp.md`（正本）；`skills/sr-od-game-coach/references/investment.md`（口径决定）
- 结论摘要：**攻击点 24 个——高危 4（定稿阻塞）、中 14（修订项）、低 6（建议）**。高危集中于：roster_data 类型标注与真实数据形态矛盾、正本清单残留「实现时确认」未定稿措辞、「星启候选队 12 人」无入库出处、工具描述逐字文本缺 Returns 段且信封状态语义未定义。另有核三正面结论（归层成立/修根成立）与规范遵循正面结论见文末。

---

## 高危（定稿阻塞）

### A1 roster_data 类型标注与真实数据形态矛盾（两处互相矛盾且都错）
- **位置**：design.md §2.2 入参表（`roster_data | object`）、§2.5 签名（`evaluate(roster_data: dict, criteria: list[dict]) -> dict`）
- **发现**：`mys_get_roster_detail` 成功时 `data` 是**角色明细数组**（list），不是 object/dict。设计两处类型标注互相矛盾（object vs dict），且与真实形态都不符。
- **依据**：`src/sr_od/backend/mcp/mys_tools.py:256-257`（成功载荷 `[character_to_dict(d) for d in details]`）；`src/sr_od/mys/sr_mys_client.py:315-316`（`CharacterDetail.relics/ornaments` 为 list 字段，`character_to_dict` = `asdict`）；`docs/develop/sr_od/backend/mys.md`「`data` 为角色明细数组」。
- **后果**：实现者照 §2.5 写 `dict` 注解 → FastMCP 按注解生成 JSON schema，调用方传数组（design 自己指示传「`mys_get_roster_detail` 返回的 `data`」）会在 pydantic 校验层被拒；照 §2.2 写 `object` 则与 §2.5 签名失同步。
- **修订方向**：两处统一为 `list[dict]`（或声明 `roster_data: list`），并在 §2.2 表注明「元素结构 = CharacterDetail asdict（见 mys.md 冻结字段集）」。

### A2 正本更新清单残留「实现时确认是否涉及」——未定稿措辞
- **位置**：landing.md「正本更新清单」第 2 条：`mcp.md` / `mcp-implementation.md`：若含工具清单/描述汇总则同步 ← 3.3（**实现时确认是否涉及**）
- **发现**：「实现时确认」= 把定稿决策推给实现者，直接撞写作硬规则 2 卡点（「看情况/待定/酌情 = 未定稿必攻」）。且答案是**确定的**，不存在「若」：`mcp.md` 现有工具表（含签名/返回/tool 总数，见其 mys 四工具与三个 lookup 工具行），`mcp-implementation.md` §7 checklist 明确要求「改/加 MCP tool 后同步 `mcp.md` 工具表」——两个正本都必须同步，无待确认空间。
- **依据**：`docs/develop/sr_od/backend/mcp.md` 工具表（`mys_get_roster_detail()` 行等）；`docs/develop/sr_od/backend/mcp-implementation.md` §7「同步 mcp.md 工具表（签名/参数/返回/tool 总数）——文档与实现脱节是最高频坑」。
- **修订方向**：清单改为确定项：`docs/develop/sr_od/backend/mcp.md`：工具表加行（签名/返回语义/tool 总数）← 3.3；`mcp-implementation.md` §1 分类表如含纯观察工具名单则加行 ← 3.3（该表现状确实列了只读工具名单，同属确定项）。

### A3 「星启候选队 12 人」无入库出处——12 人名单不可考，3.4 判据与知识侧配合项均无法执行
- **位置**：design.md §1（现状症状「12 角色」）、§2.5（「本迭代仅覆盖候选队 12 角色（星启诊断使用面）」）；landing.md 3.4（「星启候选队 12 人的真实口径」「results 12 条」）、正本更新清单末行（「角色档 12 人」）
- **发现**：「候选队 12 人」在全部入库文档（docs/、skills/）中无定义处；「星启诊断」的说法在仓库中也不存在（「星启」入库语义 = 逐光捡金最高难度的三节点模式，见 `skills/sr-od-treasures-lightward/references/gameplay.md`）。12 人名单目前只存在于 gitignore 的 `.debug/temp/TODO.md` 星启条（N1/N2/N3 三队临时定案），且 TODO 中「定案已写 skill『星启选队』节」的声明与实际不符——skills/ 内并无该节。3.4 的判据「results 12 条 + not_found 空」执行时无法回答「哪 12 人」；「补 12 个角色档的『有效口径』行」同样不知道给谁补。
- **依据**：全仓 grep「候选队」仅命中本迭代三份文档；grep「星启选队」无命中；12 人名单仅在 `.debug/temp/TODO.md`（不入 git，寿命=删除即失）。
- **修订方向**：design §2.5 写死 12 人名单（或指向一个入库的持久出处——如 game-coach 星启选队节先落档再引用），landing 3.4 范围与判据引用同一出处；「星启诊断使用面」改为语义自足的表述。

### A4 工具描述逐字文本缺 Returns 段 + 信封 status 语义完全未定义——实现者必须再设计
- **位置**：design.md §2.2「工具描述文本（实现时逐字使用）」、出参节
- **发现**：①逐字文本没有 Returns 段——`mcp-implementation.md` §4 docstring 三要素第 3 条硬性要求「返回结构（`Returns:` 段写 dict/dataclass 字段）」，§7 checklist 第一条同查；既有 mys 四工具描述全部带 Returns 段并列出全部信封状态。②全工具组的状态语义（success / verification_required / session_expired / error 中的哪些适用于本工具、各状态文案是什么）未定义：自拉路径（roster_data 缺省）撞上 awaiting_ticket（应返 verification_required 含 URL？）、会话过期（session_expired？）、1034 风控（error 专属文案？）——既有 controller 的状态机语义设计里只字未提如何桥接；传入路径下 criteria 非法（空 criteria 是「results 空对象」还是 error？）、roster 结构非法时返回什么 status 也没定义。实现者要么自行设计状态语义（= 在未过对抗审的语境做设计决策），要么逐字照抄（= 违反正本 docstring 规范，与同组四工具描述形态割裂）。
- **依据**：`docs/develop/sr_od/backend/mcp-implementation.md` §4/§7；`src/sr_od/backend/mcp/mys_tools.py:397-459`（四工具描述的 Returns 段形态）、`:150-257`（controller 状态机与四态信封）；`docs/develop/sr_od/backend/mys.md` 信封状态表。
- **修订方向**：§2.2 补 Returns 段逐字文本（含状态清单：本工具 success / verification_required / session_expired / error 四态全适用 + 各态触发条件与文案），并写明自拉路径对 controller 非 success 信封**原样透传**（status/message/data 不改写）；传入路径的非法入参行为见 B6。

---

## 中（修订项）

### B1 计数遍历域未定义——ornaments 数组名通篇未出现
- **位置**：design.md §2.3 规则 3/规则 4、§2.2 出参 `total_rolls`（「6 件遗器副词条强化次数总和」）
- **发现**：名册明细的佩戴件分两个数组：`relics`（隧洞遗器，pos 1-4，四件）与 `ornaments`（位面饰品，pos 5-6，两件）。design 通篇未出现 `ornaments`/「位面饰品」字段名；「6 件」与主词条期望含「位面球/连结绳」暗示两数组都算，但规则 3「每条副词条」、规则 4「逐件」都没写从哪些数组取——遍历域这一数据流关键选择留给实现者推断。
- **依据**：`docs/develop/sr_od/backend/mys.md`（CharacterDetail 冻结字段集 `relics[]/ornaments[]`、pos_cn 六部位取值）；`src/sr_od/mys/sr_mys_client.py:296-297`。
- **修订方向**：规则 3 开头写死「遍历 relics 与 ornaments 两数组共 6 件（pos 1-6）」。

### B2 value 是字符串——求和规则不可直接执行，阈值单位口径未对齐角色档「转化上限」
- **位置**：design.md §2.3 规则 3（「按标准名累加 value」）、规则 5（「current = 主+副 value 求和」「保留 1 位小数」）
- **发现**：`SrPropertyEntry.value` 是**字符串**（原样透传，如 `"705"` / `"43.2%"`），不能直接求和。设计的字符串→数值解析规则（剥 %、转 float、解析失败时按 0 还是跳过）完全未定义；`value_sum`/`threshold_report.current` 的单位口径未定义（flat 词条与 % 词条是否可能落入同一标准名键、混合求和的语义）。更深层：investment.md 定义毕业线 = 角色档「转化上限」（如海瑟音效果命中 120%、流萤击破 360%），底稿 `.debug/temp/relic_eval_design.md` 未决点明确列有「thresholds 的数值口径（面板最终值 vs 词条求和+基础值）与角色档『转化上限』线的单位对齐」——design 把该未决点静默拍板为「词条求和」，没有论证词条求和口径与角色档转化上限线兼容（转化上限若按面板口径书写，词条求和会系统性低估）。
- **依据**：`src/sr_od/mys/sr_mys_client.py:127-135`（value 字符串透传）；`skills/sr-od-game-coach/references/investment.md`「毕业线 = 角色档『转化上限』」；`.debug/temp/relic_eval_design.md` L17/L42（未决点，不入库）。
- **修订方向**：规则 3/5 补数值解析规则（% 剥离为百分数值、解析失败显式计 0 或上报）与单位声明；补一条取舍论证「词条求和口径 vs 面板最终值口径」并核对至少一个角色档转化上限的书写口径。

### B3 口径包名/键名归一 miss 的行为未定义——静默错数无告警
- **位置**：design.md §2.2 criteria 元素表、§2.3 规则 2
- **发现**：`effective_substats` 元素可以是标准名或口径包名——传了**表外包名**（调用方手滑写「双暴」）时如何处理未定义；若静默原样当标准名，该词永不命中、全部计浪费，产出全错的报告而工具无任何告警——对诊断工具是最危险的故障形态。同类：`main_stat_expectations` 键（部位名）传「头部」或错字、`stat_thresholds` 键传别名（「命中」）时，是过归一、报错还是静默跳过，均未定义。
- **依据**：design §2.2/§2.3 无对应规则；对照 `character_tools.py:126-128`（同仓先例：模糊多命中返回 ambiguous 候选不猜）。
- **修订方向**：补一条规则：展开 miss 的包名/未识别的键 → 该角色评估照常但 results 附 warnings 列表（或整角色报 error 信封），写死其一。

### B4 头部/手部在主词条核对中的行为未定义
- **位置**：design.md §2.3 规则 4、§2.2 出参 `main_stat_check`
- **发现**：名册六部位 = 头部/手部/躯干/脚部/位面球/连结绳；`main_stat_expectations` 只支持四部位（头/手主词条物理恒定无需核对，这个意图可推断），但头/手两件在 `main_stat_check` 输出里是**完全不出现**（列表恒 ≤4 条）还是恒 `matches=true` 条目，未写死——调用方无法预知列表长度语义，verdict 的「主词条穿错 N 件」分母也未说明只数四部位。
- **依据**：`src/sr_od/mys/sr_codes.py:156-175`（RELIC_POS_CN 六部位 + RELIC_MAIN_AFFIX_ALLOWED 头/手恒定集）。
- **修订方向**：规则 4 写死「头部/手部不参与核对、不进 main_stat_check；穿错计数分母 = 传入期望的部位数」。

### B5 hit_ratio=null 时 verdict 模板行为未定义
- **位置**：design.md §2.3 规则 7、规则 8
- **发现**：出参定义 `hit_ratio` 在 `total_rolls=0` 时置 null（如角色遗器未佩戴/subs 全空），verdict 模板含 `{ratio:.0%}`——null 进格式化会抛异常或输出怪文案；规则 8 只覆盖 criteria 空表，未覆盖单角色 total_rolls=0 的 verdict 文案。
- **依据**：`SrRelic.subs` 为空列表的合法形态（`sr_mys_client.py:151`）。
- **修订方向**：规则 7 补「total_rolls=0 时 verdict = `无遗器数据`」之类的定死文案。

### B6 roster_data 传入路径的防御行为未定义
- **位置**：design.md §2.2 入参表（`roster_data`）
- **发现**：最易发生的真实调用错误是调用方把**整个信封** `{"status","message","data":[...]}` 塞进 roster_data（agent 从上一工具拿到的就是信封整体）。设计未定义结构校验失败时的行为：返 error 信封？当空名册（全部 not_found，静默产出空报告）？未校验直接取值崩溃？
- **依据**：design §2.2 仅写「`mys_get_roster_detail` 返回的 `data`」，无防御规则；对照同仓工具统一兜底惯例（`app.py` 各 tool try/except 返 error 结构）。
- **修订方向**：补规则：roster_data 非 list 或元素缺关键键 → 返回 `error` 信封，message 指明「应传 `data` 字段内容」。

### B7 两张常量表的「稳定词表，非判断口径」定性无依据；六个口径包名全仓无出处
- **位置**：design.md §2.3 规则 1/规则 2、§2.4
- **发现**：①「别名表/口径包表属 MCP 可内置范围（稳定词表，非判断口径）」是对投资决定边界的关键裁断，无依据标注——investment.md 只裁定「不内置默认口径」，「速记词汇 vs 判断口径」的边界是设计自划的，无出处支撑「稳定」断言。②六个口径包名（双暴攻/速双暴/双暴生/击破速/命中速/生命双暴）在入库文档中零出处（grep 仅命中 design 自身与一处自然语言「不堆速度堆双暴攻击」）；game-coach 角色档的副词条写法是「速度>暴击=暴伤>攻击力」优先级串，从不用包名速记——包名实质是设计单方面发明的知识层词汇表，且还要写进 12 个角色档的「有效口径」行（landing 清单末行），词汇表从此固化在代码常量里。③3.1 判据「两张常量表经真实名册词条名全集核对后定稿」对口径包表对象错位：口径包成员由角色档用法决定，与名册词条名无关（别名表按名册核对才是对的）。
- **依据**：`skills/sr-od-game-coach/references/investment.md` 设计决定节（无速记词汇概念）；全仓 grep「双暴攻」等六名仅 design.md 自身；`.debug/temp/relic_eval_design.md` L32「表按角色档实际分布扩充」。
- **修订方向**：①补依据或降级定性（如「常用速记，miss 即按标准名处理+告警」）；②口径包表定稿判据改为「按 12 人角色档口径行实际用到的包核对」，不挂名册全集；③在关键取舍节补「为何允许内置速记词表而不违『不内置口径』决定」的论证。

### B8 纯计算模块位置（新建 `backend/mys/` 目录）无依据标注
- **位置**：design.md §2.5
- **发现**：`src/sr_od/backend/mys/` 目录不存在（新建）；既有 mys 业务层在 `src/sr_od/mys/`（数据类所在），backend/mcp/ 下已有「纯函数+常量索引+注册分离」的零 IO 先例（`character_tools.py` 把纯函数与注册放同一文件）。选择新建第三种布局（backend/mys/ 两文件拆分）是结构关键主张，§2.5 与关键取舍节均无依据/取舍记录。
- **依据**：glob 确认 `backend/` 现有子包仅 mcp/http/entry；`src/sr_od/backend/mcp/character_tools.py`（先例形态）。
- **修订方向**：§2.5 补一句取舍（如「与 sr_od/mys 数据类同层会导致业务层反向依赖 backend 语义，故放 backend/mys/；不并入 character_tools 因体量与测试独立性」），或改选既有布局。

### B9 「不堆清单」与「阵容小覆盖」的取舍论证丢失（留在不入库底稿里）
- **位置**：design.md §2.2 criteria、§2.6 关键取舍
- **发现**：investment.md 决定节的口径参数三件 = 「有效词条清单/**不堆清单**/阈值线」；design criteria 无「不堆清单」入参（靠「补集一律视为无效」覆盖）——论证「为何不单独收不堆清单」只存在于 `.debug/temp/relic_eval_design.md`（gitignore，L14「『不堆』在角色档里服务于配口径时的自查」），design 关键取舍节未收录。同理底稿的 `overrides`（阵容定位小覆盖结构）被 design 静默删除（改为调用方自行组装最终口径），也无取舍记录。读者无法区分「有意简化」与「遗漏」。
- **依据**：`skills/sr-od-game-coach/references/investment.md` 设计决定节（三件清单）；`.debug/temp/relic_eval_design.md` L14-15。
- **修订方向**：§2.6 补两条取舍：「不堆清单不设独立入参（补集语义已覆盖，角色档不堆清单服务于人工配口径时的自查）」「不设 overrides 结构（基础口径+小覆盖由调用方组装为最终口径，工具只认最终口径）」。

### B10 别名归一（name_cn 路线）vs pt 码路线未论证——治本面缺关键取舍
- **位置**：design.md §2.3 规则 1、§2.6
- **发现**：数据管道里词条有稳定数字标识（property_type 码：攻击 flat=29 与攻击%=33 天然不同码），`RELIC_MAIN_AFFIX_ALLOWED` 已按码建封闭集。设计选了「中文名+别名表归一」路线——正是设计自己承认要靠「实机核对别名表」续命的同名异义风险路线（「攻击力」flat vs「攻击力提高」%）；备选的 pt 码路线（扩展 `character_to_dict` 冻结字段集透传 pt，按码匹配一劳永逸）在关键取舍节没有任何对比。若别名表路线被选，理由（如「pt 码不在冻结契约内、扩契约成本高」）应写明。
- **依据**：`src/sr_od/mys/sr_codes.py:168-175`（按码封闭集先例）；`src/sr_od/mys/sr_mys_client.py:122-135`（SrPropertyEntry 冻结字段集不含 pt）。
- **修订方向**：§2.6 补「name_cn+别名表 vs 透传 pt 码按码匹配」取舍（含冻结契约扩展成本的对比），选 name_cn 路线则同时补别名表随版本维护的责任归属。

### B11 3.1 验收凭据依赖 3.2 的产出——阶段划分违规
- **位置**：landing.md 3.1「验收凭据形式：测试名（**3.2 的 fixture 测试**）+ 真实名册词条名清单对照记录」
- **发现**：3.1 完成时 3.2 尚未开始（3.2 依赖 3.1），验收凭据引用了不存在的东西。iteration-design.md §3.1 明文「判据依赖另一阶段未完成部分 = 划分不当（排进依赖，或重新划分）」。
- **依据**：`docs/develop/harness/iteration-design.md` §3.1 阶段粒度判据。
- **修订方向**：3.1 验收凭据改为「真实名册词条名清单对照记录 + 本阶段自建的最小直调脚本输出」（或把常量表定稿挪进 3.2 一起验收）。

### B12 3.1 依赖标「无」，但真实名册核对隐含 mys 登录态前置
- **位置**：landing.md 3.1（「依赖：无」「拉一次真实名册核对词条 name_cn 全集」）
- **发现**：拉真实名册 = 实机数据操作，前置是有效 mys 登录会话；会话过期时第一步即卡（需 `mys_login` 人工解题）。3.1 依赖声明与隐含前置不符，账本立任务时会把无前提任务派出去。
- **依据**：`docs/develop/sr_od/backend/mys.md`（会话失效行为与重登流程）。
- **修订方向**：3.1 依赖补「前置：mys 会话有效（过期则先 mys_login）」，或在范围写明核对动作可延至会话有效窗口。

### B13 正本更新清单消费错位：两行由 3.4 提前消费，且 3.4 范围/文件面未覆盖这些改动
- **位置**：landing.md「正本更新清单」末两行（角色档 12 人行「← 3.4 顺带补齐」、investment.md 行「← 3.4」）与 3.4 阶段小节
- **发现**：规范 §3.2 定位清单「由固定末阶段消费，清单清零 = 收尾完成」；本清单两行写明由 3.4 顺带消费——末阶段「清单清零」判据与实际消费方错位，清单失去收尾单一源语义。同时 3.4 的**范围**只写「重启 server + 实机评估 + 抽检」，**文件面**写「无代码面（操作 + 抽检记录留 .debug/temp/）」——但清单末行要求 3.4 补 12 个角色档（`skills/sr-od-game-coach/references/characters/*.md`）并更新 investment.md，这些文件改动既不在 3.4 范围句里也不在文件面里——阶段小节（账本唯一源）与清单两处记载互相矛盾，照小节立任务会漏掉知识侧工作。
- **依据**：`docs/develop/harness/iteration-design.md` §3.1（阶段小节=账本唯一源）、§3.2（清单由末阶段消费）；landing.md 3.4 与清单对照。
- **修订方向**：两行改「← 末阶段」由正本更新批消费；或 3.4 范围/文件面显式纳入 skills/ 改动并加对应完成判据（二者取一，禁止两处各说各话）。

### B14 3.4 判据「results 12 条 + not_found 空」在账号缺员场景不可满足
- **位置**：landing.md 3.4 完成判据第 2 条
- **发现**：判据写死 12 人全评估且 not_found 空。名册只含**已持有**角色，账号缺员/形态分歧时（既有先例：知更鸟形态按缺员处理，见 investment.md 断点表）not_found 必然非空——判据在真实账号上可能永远不满足，或诱导执行者凑数。
- **依据**：`skills/sr-od-game-coach/references/investment.md` L60（知更鸟缺员处理先例）；`mys.md`（名册=持有角色）。
- **修订方向**：判据改为「A3 名单中实有角色全部评估成功；缺员/写错角色落入 not_found 属预期并在留档记录中说明」。

---

## 低（建议）

### C1 底稿的「全队汇总」输出静默消失
- **位置**：design.md §2.2 出参
- **发现**：底稿输出含「全队：按命中占比排序，最弱角色+最弱件一行结论（对齐配队第 5 步）」；design 出参只有 per-role results，无全队层汇总，无取舍记录。调用方要自己排序比较——工具既然做确定性计数，全队最弱角色是同一确定性的自然延伸。
- **依据**：`.debug/temp/relic_eval_design.md` L27-29。
- **修订方向**：出参补 `team_summary`（最弱角色+排序），或 §2.6 补「v1 不做全队汇总」的取舍声明。

### C2 出参 message 文案未定义
- **位置**：design.md §2.2 出参节
- **发现**：既有工具 success 信封都带人类可读 message（如「共获取 N 名角色明细」）；本工具 message 文案未写。逐字文本只覆盖 docstring，不含运行时 message。
- **依据**：`mys_tools.py:223-224/256-257`。
- **修订方向**：§2.2 补一行 success message 模板（如「共评估 N 名角色，M 名未命中名册」）。

### C3 「核对记录随提交留档于测试 fixture 注释」与注释规范有张力
- **位置**：landing.md 3.1 完成判据第 2 条
- **发现**：「核对记录」是验证过程性质内容；AGENTS.md §8 注释规范禁调试/验证过程叙事入注释（核对动作该做的结果是「fixture 数据 + 数据来源指针」）。若把「何时拉的名册、核对过程」写进 fixture 注释即违规。
- **依据**：AGENTS.md §8（变更史/调试过程叙事禁入注释；可复核标定挂持久指针）。
- **修订方向**：措辞改为「词条名全集以 fixture 数据入库 + 注释标注数据来源（mys_get_roster_detail 拉取的字段形态）」，核对过程本身不入注释。

### C4 迭代目标指针指向 gitignore 的本地待办
- **位置**：design.md §0（迭代目标 = 「项目本地待办……」）
- **发现**：`.debug/temp/TODO.md` 不入 git 且完成即删（AGENTS.local.md §2.1）——changes/ 文档入库后该指针成死链，违反 AGENTS.md §8「引用必须是持久索引或纯语义描述」。
- **依据**：AGENTS.local.md §2.1（TODO.md 生命周期）；AGENTS.md §8。
- **修订方向**：§0 目标出处改为持久指针（investment.md 两节已经够了）+ 语义描述，TODO 引用删除。

### C5 criteria 同名角色重复条目的行为未定义
- **位置**：design.md §2.3 规则 8
- **发现**：同一 `character_name` 传两条口径时，results 键冲突（后者覆盖前者？合并？）未定义。边缘但属确定性规则的缺口。
- **修订方向**：规则 8 补一句「同名条目以最后一条为准」或「返回 error 信封」。

### C6 「断言计数与输出结构对照 design §2.2 表逐字段」措辞与测试规范有张力
- **位置**：landing.md 3.2 完成判据第 2 条
- **发现**：测试规范 §10.1 禁「构造完对象逐字段断言」式琐碎测试；「逐字段」若按字面执行会诱导凑断言数。按场景覆盖理解是合理的（3.2 场景清单确实覆盖各字段语义分支），但措辞应消歧。
- **依据**：AGENTS.md §10.1（写不出锁的期望表现的一律不写）。
- **修订方向**：改为「每条 fixture 场景锁定其设计约定的字段表现（对照 §2.2/§2.3），不做无场景语义的逐字段遍历断言」。

---

## 三核正面结论（走查过、无攻击点）

- **核一**：landing 四个落地阶段+末阶段小节七件齐全；各阶段「设计依据」指向 design.md §2.1~§2.5 均真实存在；design §2.2 信封惯例依据标注（mys_tools.py）、§2.6 取舍 1 依据标注（investment.md 决定节）属实可回查；README 文档清单/进度格式与规范模板一致；landing 首节常规检查与规范附录 C 一致。
- **核二**：design 四节齐（§0/§1/§2，单文档方案按详设深度执行并已声明）；三份文档无过程叙事（无「第 N 轮/已改」类措辞）；测试路径镜像规范满足（`src/sr_od/backend/mys/relic_substat_eval.py` → `sr-od-test/test/sr_od/backend/mys/test_relic_substat_eval.py`）；fixture 测试零副作用、数据自造符合测试规范 §10.5.1。
- **核三**：§1 归层成立——口径知识已在角色档（investment.md 遗器节），确定性计数算术确无工具承载（现有 mys 三/四工具只透传数据，无计算类工具），属能力层缺口；§2 修根成立——新增能力工具 + 口径行机器可读化双管齐下，非手数提速类症状修补；加权评分显式声明外溢自成迭代，符合 iteration-design §1.1。非同族问题第二件补丁（MCP 工具族首见计算型工具），B10 是本迭代内部治本面的取舍缺口，不构成跨件症状链。

## 走查覆盖面声明

已读全文：design.md / landing.md / README.md（攻击对象）；`docs/develop/harness/iteration-design.md`（规范）；`src/sr_od/backend/mcp/mys_tools.py`、`src/sr_od/backend/mcp/app.py`、`src/sr_od/backend/mcp/character_tools.py`（代码权威源；`mcp.py` 不存在，tool 工厂在 `app.py` `create_mcp_server`）；`src/sr_od/mys/sr_mys_client.py`（SrRelic/SrPropertyEntry/CharacterDetail/character_to_dict）、`src/sr_od/mys/sr_codes.py`（RELIC_POS_CN/RELIC_MAIN_AFFIX_ALLOWED）；`docs/develop/sr_od/backend/mys.md`、`mcp.md`、`mcp-implementation.md`（正本）；`skills/sr-od-game-coach/references/investment.md`（口径决定节+遗器节）；`.debug/temp/relic_eval_design.md`、`.debug/temp/TODO.md`（设计底稿与挂账条目，不入库，仅作依据链核对）。另有针对性 grep：口径包名六词、「候选队」「星启选队」「星启诊断」全仓溯源、`backend/**/*.py` 目录实况、`sr-od-test/test` 镜像结构核对。
