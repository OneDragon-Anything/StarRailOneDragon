---
name: sr-od-dev-skill-guide
description: 当要创建 skill、编辑/修改 skill、写 SKILL.md、或问 skill 该放哪、带哪些文件、内容怎么写时用。英文:create/author/edit a skill、write SKILL.md、skill structure。仅创建/修改 skill 时用;使用已有 skill 不触发。
---

# 创建/修改项目 skill

本项目开发类 skill 用 `sr-od-dev-` 前缀(使用类 `sr-od-`)、放根 `skills/`、junction 到 `.claude/skills/`。创建或改 skill 时,下面 4 条硬规范必须满足。

## 硬规范

> **这 4 条是 skill 的不变量(invariant),不只新建时查**。每次**编辑**(哪怕只改一行)都要保持;**新增的任何引用都要过规范 3 的门**(已提交 + 稳定 / 可校验;不引 memory / gitignored)。新建 = 全套满足;编辑 = 至少不破坏 + 新增项满足。

### 1. 必须有 design/ 文件夹,design 与 ADR 分开
每个 skill 目录下要有 `design/` 文件夹,把**设计(what)**和**决策(why)**分成两类文件:`design/overview.md`(+ 按关注点拆的 `<concern>.md`)记「系统 / 方法论长什么样、目标、边界」;`design/decisions/NNNN-<slug>.md`(**ADR**,一决策一文件)记「为什么这么选」。不写混合的 design.md。
- **目的**:后续修改者(人或智能体)知道当初为什么这么定,避免盲目改动破坏原意。design 和 decision 读者 / 生命周期不同(前者随系统演进,后者 immutable 只 supersede)→ **分开不混写**。
- **ADR 格式**:按 arc42 §9(Status / Context / Considered Options / Decision / Consequences;详见 `references/design-docs.md`)。
- **门槛(治「奢侈」)**:ADR 只记**架构级 / 难逆 / 有实质备选**的决策;调参 / 笔误 / 局部重构 → commit message 即可,不配 ADR。
- **边界:`design/` 全是给后续维护者的存档,不进智能体执行上下文** —— SKILL.md **不应写「见 design/...」让智能体去读它获取使用信息**(命令 / 参数 / 接口);使用信息内联 SKILL.md,或放 `references/` 等会被引用的辅助文件。design/ 只记「为什么这么设计」(决策 / 踩坑论据)。
- **细则**:目录结构 / ADR 全套模板 / 写作方法论(何时写、缩放、design vs ADR 内容归属)见 `references/design-docs.md`(锚定 arc42 + ADR/MADR 业界方法论,不自己发明)。

### 2. 内容给智能体看(指令式)
SKILL.md 是**智能体要执行的指令与判据**,不是给人读的说明文档。
- 祈使句 + 判据(「先 X 再 Y」「若 Z 则 W」),不要叙述文档腔。
- frontmatter 的 `description` 只写**何时用**(触发条件),不写「做什么/怎么做」 —— 否则智能体照 description 行事、不读正文。
- **写法细则**(frontmatter 全规则 / SDO / token 效率 / 正文结构 / form-to-failure / 拆分 / 重构)见 `references/writing-craft.md`。

### 3. 自包含:分场景(独立发布 vs 项目内)
- **硬门(所有引用,不分场景)**:引用的 target 必须**在已提交的仓库里**。gitignored 内容(`.debug/` / `config/` / `.claude/` / `models` 等)、个人 local 文件、**memory**(个人本地、不跨人共享)→ **一律禁止引用** —— 引用闭包外的状态 = 在别人机器 / CI / clean checkout 上不存在(skill 是共享 artifact,不能依赖某人的私有状态)。**范围**:门管 skill **依赖**的内容(facts / helper 脚本 / 引用的 doc,**含 design/ 内**);**不管运行时操作的产物**(日志 / 截图 / 存档 —— skill 执行时生成、本不在仓库,如读 `.debug/` 日志诊断、存截图建档,这类合法)。引用「过时」风险 + 4 档应对谱(吸收 / 校验 / 运行时读 / 抽象)见 `references/design-docs.md` §引用卫生。
- **可引用其它 skill**(写**完整标识符含命名空间**,如「按 superpowers:receiving-code-review 的方法」):用完整标识符,避免裸名解析不到。
- **兄弟项目模块 / skill 名(操作目标 vs 叙事示例)**:skill 指令 agent 去**读 / 用**别的 application / skill(如「找兄弟骨架:`sim_universe` / `trailblaze_power`」)→ **规范 3 允许**(稳定运行时资产,写全名,可留 SKILL.md);作**叙事示例**(「项目 X 里我们…」)→ **规范 4 抽象**。判据同接口名两问:删了这名 agent 还会做吗(会 = 示例 → 抽象;不会 = 指令 → 留)。
- **引用 skill 目录外的文件,分场景**:
  - **独立发布 skill**(跨项目用):**禁止**外引(发布不含,目标环境可能不存在)。知识内联进 SKILL.md 或 skill 目录内辅助文件。
  - **项目内 dev skill**(放项目 `skills/`,跟项目走、不独立发布)可引:**runtime 资产路径**(skill 要去读/写的**操作对象**:screen_info / application 源码 / docs/game 等,本项目必有、稳定)+ **skill 目录内自带工具 / 辅助文件**(自包含,随 skill 走,如归档脚本 `convert_to_webp.py`)。**不可引**:**具体代码文件 / 实现行 / 易变文档**(如某 devtools 模块 L640、「详见某 README」)—— 抽象化,不点具体位置。
  - 判据(**分场景,非「所有路径都不写」**):**「skill 要读写的稳定操作对象 / 自带工具」可引**;**「只为佐证某约定的具体代码/文档位置(易变)」抽象化**。
  - **有一类具体名可以写:框架地基级、几乎不改名的接口名**。有些 skill(debug / 排查 bug / 迁移)的指令本身就是「在本项目代码里搜某个名 / 调某个接口」,比如要搜 `@operation_node` 装饰器看节点流转、要调 `save_screenshot` 截图、要提醒 `analyze_screen` 工具的结论会骗你 —— 这些名是**指令的一部分**(不是顺带举例),删了智能体就不会做了;且是框架地基级接口(整个节点系统就靠 `@operation_node`,改它等于重写框架,几乎不会发生)。这类名属上面「skill 要读写的稳定操作对象」,**可以写进 SKILL.md**。判一个名能不能写,问两点:
    1. **删掉它,智能体还能照做吗?** —— 删了照样能做(名只是举例住在哪)→ 挪 design/ 的 ADR;删了就不会做了(名 = 指令本身)→ 看第 2 点。
    2. **它会不会经常变?** —— 框架地基级、几乎不改名 → 可以写;容易变的(某测试 API、具体行号)→ 挪 design/ 的 ADR。
  - **能写就写全名,别改成模糊说法**。可写进 SKILL.md 的接口名直接写完整名字(如「本项目用 `@operation_node` 装饰器声明节点流转」)—— 万一以后代码改名,全局一搜这名就发现 SKILL.md 这行也得跟着改,**改没改一目了然**。**别**反过来模糊成「节点声明装饰器」:代码改名后这种说法不报错、却已指错地方,谁都不会发现 —— 看着抽象好像更稳,其实更危险。

### 4. 写方法论,不写具体例子(限 SKILL.md 与智能体读的辅助文件)
写**方法、原则、判据**(怎么判断、怎么选),不要写「某个具体场景/项目的做法」。**具体游戏事实(键位/坐标/具体流程/机制)归 doc 不归 skill**;skill 只记方法论(分工见 doc_organization)。(注:框架接口名不归本条管 —— 那是规范 3「skill 要读写的稳定操作对象」,看规范 3 判据;本条只管具体游戏事实 / 项目例子。)
- **适用范围**:SKILL.md 正文 + skill 目录内会被智能体读取的辅助文件(这些注入智能体执行上下文)。
- **design/(含 ADR)不在此列**:它是给后续维护者的设计记录,可以有具体例子/踩坑作为决策论据。
- 理由:具体例子会以偏概全 —— 智能体把例子的偶然细节当成必然规则,套到不匹配的新场景。
- 抽象成判据:「在 X 条件下选 A,在 Y 条件下选 B」,而非「项目 P 里我们用了 A」。
- 不得不具体的,**仅限纯语法/字段名**(如 frontmatter 的 `name`+`description`、命令必填参数),给最小可用形式;「为什么选 A」「项目里遇过 X」这类划到 design/ 的 ADR。

## 落点(项目约定)
- 目录:根 `skills/<dev-name>/`(跨工具源,提交共享)。
- 前缀:开发类 `sr-od-dev-`(项目开发流程类);使用类 `sr-od-`。`sr-od-` 兼项目命名空间,防和插件/个人 skill 撞名。
- Claude Code 发现:junction `.claude/skills/<dev-name>` → 根 `skills/<dev-name>`,形如 `cmd /c mklink /J .claude\skills\<dev-name> skills\<dev-name>`(Windows junction 免管理员;symlink 需特权)。junction 不提交(`.claude/` 已 gitignore),每人本地建。
- 结构:`SKILL.md`(入口)+ `design/`(设计 + ADR,见硬规范 1 / `references/design-docs.md`)+ 按需辅助文件(如 `references/`,必须在 skill 目录内)。

## 创建/修改流程
1. **定位**:这个 skill 管什么、不管什么。和已有 skill(`superpowers:*`、本项目 `sr-od-dev-*`)重叠的,**引用而非重复**。
2. **写 SKILL.md**:frontmatter(name + description,description 只写触发)+ 指令式正文(方法论)。
3. **写 design/**:`overview.md`(定位 / 边界 / 构成)+ `decisions/` ADR(架构决策,按 `references/design-docs.md` 格式与门槛)。
4. **自检 4 条硬规范**(逐条对照 —— **新建和编辑都要做**)+ 通读正文确认每条指令可执行。**编辑时额外查:新增的引用是否过规范 3 的门(已提交 + 不引 memory / gitignored + 稳定 / 可校验)**。
5. **junction 到 `.claude/skills/`**,验证 skill 可被触发(按工具要求重载/重启)。
6. 提交 `skills/<dev-name>/`(junction 不提交)。

## SKILL.md 写法(细则)
frontmatter(`name` 仅字母数字连字符 / `description` 只写「Use when…」触发、**绝不总结 workflow**)/ SDO(keyword 覆盖、命名)/ token 效率 / 正文结构 / **form-to-failure**(按失败类型选指令形态)/ 拆分(progressive disclosure)/ 编写中重构 / 例子与反模式 / 何时建 —— **细则见 `references/writing-craft.md`**(锚定 Anthropic context engineering + lost-in-the-middle + Diátaxis)。SKILL.md 保持 compact、情境细节进 references/(just-in-time)、定期重构不无脑追加。

## 两类 skill:RED 必要性不同,GREEN 始终必做
本 skill **不照搬**「写 skill = 严格 TDD、每个 skill 必须先 RED baseline」(superpowers 的 Iron Law)。按 skill 的**内容依据**分两类:
- **纠正型**:改变智能体默认会做错的行为,内容依据是"baseline 暴露的 failure" → RED(baseline)必做,再写最小纠正。
- **方法论覆盖型**:整合业界已验证的方法论成系统流程,内容依据是方法论本身 → **RED 可省**(团队工具 / 模型异构,单一 baseline 外部效度不足 —— 你本地看到的失败可能只是你模型的弱点,或别人环境的失败你根本没看到);但写完必须 GREEN 验证(跑 application 场景,确认用了 skill 的智能体决策 / 产出更系统)。

无论哪类,**GREEN 验证不可省**(方法见 `references/skill-testing.md`:方法论型 = utility test 干净工作空间 + 可交互子 agent + 你扮用户只答所问 + 观察 gap + 修 + 循环;纠正型 = pressure test);差异只在 RED 是否必须。
判断属于哪类:问"这条规范的依据,是'智能体默认会做错所以纠正',还是'业界方法论本来就该这么做'?"。前者纠正型,后者方法论型。`sr-od-dev-deciding-a-fix` 是方法论型(锚定 RCA / Impact Analysis 等)。理由见 [ADR-0005](design/decisions/0005-drop-superpowers-dependency.md) + `references/writing-craft.md` §3.1。
