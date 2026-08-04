# SKILL.md 写法方法论

> 本文件是 `sr-od-dev-skill-guide` 规范 2 的细则 + 写法工程指南。写 / 改 SKILL.md 时按此。
> **定位:guidance(强建议),非硬规范** —— 硬规范只有 SKILL.md 的 4 条;各 §是 best-practice,按 skill 规模取舍(如 §1.6 头尾 recap 对短 skill 可省)。
> 锚定业界方法论:**Anthropic context engineering**(smallest high-signal tokens / right altitude / just-in-time)+ **lost-in-the-middle**(Liu et al. 2023)+ **Diátaxis**(文档按需求分模式)+ progressive disclosure。
> **本 skill 不依赖 superpowers:writing-skills**;其通用写法核心(SDO / token / 结构 / form-to-failure)已整合进本文件(见 §6 与之区别)。

## 0. 核心认知:可读性 = agent 能不能 follow
SKILL.md 是**注入智能体上下文、让 agent 执行**的指令文档,不是给人读的 README。"可读性"不是文采,是 **agent 能否正确 follow** —— 下面所有写法都由它决定。

**context 是有限资源(context rot)**:LLM 对长上下文呈 **U 型回忆**(lost-in-the-middle):头尾记得住、中段最弱;且 token 越多回忆精度越降。→ **每个 token 都是成本**,SKILL.md 要找 **smallest set of high-signal tokens**(最小高信号 token 集),不是越全越好。

## 1. 怎么写更好(写法 craft)

### 1.1 right altitude(粒度,最关键)
在两个失败模式间找平衡(Anthropic Goldilocks):
- 太**脆**:硬编码 if-else 流程 → 易碎、维护重、换场景就废。
- 太**泛**:高层空话、假装有 shared context → 没具体信号,agent 不知怎么做。
- **最优**:**够具体能引导行为,又够抽象给强 heuristic**(判据式:「X 条件下选 A、Y 条件下选 B」)。

### 1.2 指令式 + 判据(规范 2)
祈使句 + 判据(「先 X 再 Y」「若 Z 则 W」),不叙述文档腔。**标题写成判据本身**(扫标题能读懂骨架),不是模糊主题词。

### 1.3 frontmatter
- `name` + `description` 必填(共 max 1024 字符);`name` 仅字母数字连字符。
- `description` = **只写「何时用」触发条件**(症状 / 场景 / 上下文),**绝不总结 workflow**。
  - **陷阱(实测)**:description 一旦写了流程,agent 会**照 description 行事、不读正文**。例:写「执行计划时,每任务派子 agent + 任务间 code review」→ agent 只做一次 review;而正文 flowchart 要两次(规格 + 质量)。改成只写触发「Use when 执行含独立任务的实现计划」→ agent 才读正文。
  - 第三人称;以 "Use when..." 开头;含具体触发词(错误信息 / 症状 / 工具名)便于被搜到。
  - **keyword 覆盖**:错误信息("Hook timed out")、症状("flaky")、同义词、工具 / 命令名。

### 1.4 正文结构(按需,非强制模板)
Overview(是什么 + 核心原则一两句)/ When to Use(症状 + 何时不用)/ Quick Reference(扫读表)/ Common Mistakes(常见错 + 修)。**reference / 穷举清单 / 长例子** → 进 `references/`,不堆正文(见 §2)。

### 1.5 form-to-failure(按失败类型选指令形态,高级)
写规则前先分清它防的是哪类失败 —— **形态选错会反效果**(有对照实验):

| 失败类型 | 正确形态 | 错误形态 |
|---|---|---|
| 压力下明知故犯(知道规则但不做) | **禁令 + 合理化反驳表 + red flags** | 软建议("prefer...") |
| 照做但产出**形状错**(冗长 / 埋没结论 / 复述规格) | **正向 recipe / contract**:说产出**是什么**(各部分 + 顺序) | 禁令清单("don't restate") |
| 漏掉本该有的元素 | **结构式**:模板里 REQUIRED 槽位 | 模板旁的散文提醒 |
| 行为该随条件变 | **条件式**(挂可观测谓词:"若有 brief,引用它") | 无条件规则 + 例外从句 |

**要点**:**禁令对「塑形」类失败反而更糟**(agent 会和 "don't X" 谈判)。recipe 不留谈判空间:产出要么符形状要么不符。**别加 nuance 从句**("don't X unless it matters" 重开谈判);真例外写成独立条件式。

### 1.6 头尾放不变量(lost-in-the-middle)
**关键规则 / 不变量放开头**(primacy)+ **结尾放自检 / recap**(recency);别把「必须做」埋正文中间(U 型最弱区)。

### 1.7 token 效率(每个 token 都是成本)
目标(参考):频繁加载的 skill 正文尽量短(<200~500 词);getting-started 类 <150。手法:细节移 `--help` / reference;**别 `@` 强制加载**别的文件(烧 context);压缩例子;去冗余(别重复 cross-reference 已说的)。验证:`wc -w SKILL.md`。

### 1.8 调参值 / magic number 归属(rule #4 边界)
具体数值(`pc_rect +10px` 留白、sleep 1.5s、`lcs_percent=0.8`)常让人拿不准归 skill 还是 doc:
- **原则 / 规则归 skill**(「模板 bbox 每边留白以容忍匹配误差」「操作后等动画再验」「loose 匹配要收紧阈值防误匹配」)。
- **精确调参值是 data** → 默认归 **doc / design**(具体游戏 / 实测定值)。
- **例外**:若该值是与方法论不可分的**稳定操作约定**(如「留白 ≈ +10px」是 screen_info 编辑器通用惯例、非某游戏专属),则留 skill 并标「≈,按实测调」。
- **判据**:换项目 / 换版本这值还成立吗?成立(通用约定)→ skill(带「可调」);不成立(实测 / 游戏专属)→ doc / design。

## 2. 怎么拆分文件(progressive disclosure)
核心:**always-on**(SKILL.md,每次触发都加载,token 贵)**只放必须每次都有的**;**情境性细节**进 `references/` 按需加载(skill 指令「到第 Y 步读 references/X」)。这叫 **just-in-time + 轻量标识符**(Anthropic 背书:agent 维护 file path / link,运行时按需读,像人用索引不全背)。

### 2.1 内容归属
- **always-on**(SKILL.md):方法论 / 不变量 / 判据 / frontmatter。每次触发都要。
- **situational**(`references/`):深度模板、穷举清单、API 参考、长例子、form-to-failure 大表。只有某步 / 某分支才要。
- **maintainer-only**(`design/`):设计 + ADR,不进 agent 上下文(规范 1)。
- **自带工具 / 脚本**(skill 目录内、被 SKILL.md 调用执行):放 skill 根或 `scripts/` 子目录;**`references/` 只放 agent 读的参考文档(.md),不放可执行脚本**。

### 2.2 拆分触发器(信号 → 抽 references/)
- 一节 > 100 行且只服务某子场景 → 抽。
- 同段检查清单在 3 处重复 → 抽一次,引用。
- **穷举列表**(全部阵营名 / 全部 screen 名)→ references/,SKILL.md 只引「当前清单见 references/X」(= 引用卫生档 3 运行时读,永不过时)。
- 长例子 / 图示 → references/ 或 design/(规范 4:SKILL.md 只留抽象判据)。
- **反向**:子节只一行 → 折回父节(防过早拆分,反过度工程)。

**拆 vs 不拆裁决**(§2 拆分 vs §3.4 反过度拆分,不冲突):问「这内容服务**每次都用**的核心,还是**某分支**才要?」某分支才要 + 有分量(挡住核心 / 重复)→ 拆 references/;每次都要的核心 → 留 SKILL.md 内联(**即使长** —— 每次都要付 token,拆出去反而每次再读更费)。别把「核心但长」误当「情境深度」拆掉。

### 2.3 命名 / 目录即信号
references 文件名 / 目录结构本身给 agent 信号(`test_utils.py` 在 `tests/` vs `src/core_logic/` 含义不同)。组织清晰 = 减少 SKILL.md 里要解释的话。

## 3. 编写过程中怎么重新组织(refactor)
把 SKILL.md 当**需定期重构的代码**,不是只追加的文档。借 Fowler 重构的命名变换套到散文:

| 变换 | 何时做 |
|---|---|
| Extract Section | 一节混多个关注点 → 拆 / 抽 references/ |
| Merge Duplicates | 同规则说 3 遍 → 留一处 + 交叉引用 |
| Reorder by Dependency | 依赖别的规则的规则排后面;不变量置顶(lost-in-the-middle) |
| Move | 情境细节 → references/ |
| Inline | 过度拆的一行子节 → 折回父节 |
| Rename heading to criterion | 标题从主题词改成判据 |

**重构触发器**(写中遇到就停一下重构):在重复自己 → Merge;加到第 5 条「例外」→ 重新抽象或例外进 references/;核心规则被埋 → 重排 / 抽出挡路细节;新规则不知放哪 → 可能是别的模式(Diátaxis:how-to / reference / explanation? explanation → design/ ADR);**费力找 / 理解某条规则 → 结构该过一遍重构了**(可读性债)。

### 3.1 minimal 起步 + RCA 过滤的增量(重要:别 over-fit)
- **从 minimal 开始测**(别一次堆全);**但**为**观察到的失败**加指令时,**先 RCA**:
  - 这是**通用 gap**(任何合理模型按方法论走都会犯)还是 **model/env 特异**(只你这套犯)?
  - **只为通用 gap 加**;**模型补偿性指令**(只补弱模型怪癖)不进**共享** SKILL.md(进 design ADR 记「某模型需额外哄」)—— 否则对强模型是噪声(违反 smallest-high-signal-tokens)。
  - 理由:共享 skill 跨人 / 模型 / 环境;你本地看到的失败**外部效度不足**(可能只是你模型的弱点,或别人环境的失败你根本没看到)。
- **共享 skill 主基底 = methodology**(模型无关、抗异构);failure-derived 规则只作 RCA 过滤后的补充。
- 与「两类 skill」一致:方法论覆盖型以方法论为据(不强依赖 baseline);纠正型即使做 RED,也只把**通用失败**写进去。

## 4. 例子与反模式
- **一个优质例子 > 多个平庸**:完整可跑、注释讲 WHY、来自真实场景、可改编(非填空模板);别多语言实现。
- **反模式**:叙事性例子(「某次 session 我们…」)、多语言稀释、flowchart 里塞代码、generic 标签(helper1 / step2)。
- **flowchart 只用于「非显然决策点 / 可能早停的循环」**;reference / 代码 / 线性步骤用表 / 代码块 / 编号列表,不用 flowchart。

## 5. 何时建 skill(别滥用)
建:技术非显然、跨项目会复用、广适用、别人也受益。
**不建**:一次性方案;他处已充分文档化的标准做法;**项目专属约定 → 进 instructions 文件(CLAUDE.md / AGENTS.md)不进 skill**;**机械约束(能用 regex / 校验强制的)→ 自动化,别占文档**(文档留给判断类)。

## 6. 与 superpowers:writing-skills 的区别(本 skill 刻意偏离 + 整合)
本 skill **不依赖** superpowers:writing-skills,已整合其**通用写法核心**(frontmatter / SDO / token 效率 / 结构模板 / form-to-failure / 例子与反模式 / 何时建)到上文。**刻意偏离**一处:
- superpowers 的 **Iron Law:每个 skill 必须先 RED(baseline 看失败),无例外**。本 skill **弱化**:按「两类 skill」,**方法论覆盖型 RED 可省**(团队工具 / 模型异构 → 单一 baseline 外部效度不足,见 §3.1),GREEN 验证两类都不可省。
- 本 skill **叠加** superpowers 没有的:design/ + ADR(规范 1)、自包含硬门 + 引用卫生(规范 3)、SKILL.md 写法工程指南(本文件)。

详见 [ADR-0005](../design/decisions/0005-drop-superpowers-dependency.md)(去 superpowers 依赖)。
