# skill / 子项目 设计文档方法论(design docs + ADR)

> 本文件是 `sr-od-dev-skill-guide` 硬规范 #1 的细则。创建 / 改 skill(或子项目)时按此组织设计文档。
> 锚定业界方法论:**ADR**(Architecture Decision Records,Nygard 2011 / arc42 §9 / MADR)+ **arc42**(架构文档模板)。不自己发明格式。

## 1. 目录结构(强制)

每个 skill / 子项目必须有 `design/` 文件夹,**design(what)与 ADR(why)分开**:

```
<skill 或 子项目>/
├── SKILL.md            # 仅 skill:智能体指令(方法论 + 判据)
├── design/
│   ├── README.md       # 索引:各文档职责 + 指向 decisions/INDEX.md
│   ├── overview.md     # 目标 / 范围 / 上下文 / 边界(arc42 §1-3)
│   ├── <concern>.md …  # 按关注点拆(构成 / 流程 / 约定…);超 ~300 行或混关注点才拆(arc42 §5,§8)
│   └── decisions/
│       ├── INDEX.md    # NNNN | 标题 | 状态 | 日期 —— 一眼全貌(替代旧单文件日志的概览)
│       └── NNNN-<slug>.md   # 一决策一文件,带 lifecycle
└── references/ …       # 按需:被 SKILL.md 引用的辅助文件(模板 / API 参考等;会被智能体读)
```

**design doc = what**(系统 / 方法论长什么样,随系统演进而改);**ADR = why**(为什么这么选,**immutable,只 supersede 不改写**)。design 文档正文 link 到 ADR(「用 X,见 ADR-0007」),保持正文干净;ADR 反向 link 到 design 章节和相关 ADR。同一条信息别两边重复。

## 2. ADR 格式(arc42 §9)

每条架构决策一个文件 `design/decisions/NNNN-<slug>.md`(NNNN 从 0001 递增;slug 短横线英文小写)。模板:

```markdown
# NNNN. <决策标题>

- **Status**: proposed | accepted | deprecated | superseded by NNNN
- **Date**: YYYY-MM-DD(决策正式记录 / 形式化日;与原决策日不同则 Context 注原日)

## Context
当初面对的问题 / 场景 / 约束。不是 rationale,是「为什么要做这个决策的局面」。

## Decision Drivers
影响选择的 forces —— 要权衡什么(性能 / 可维护 / 版本鲁棒 / 用户偏好…)。
无显式 driver 可省此节。

## Considered Options
备选方案 + 各自利弊。**最值钱的字段** —— 防后人重复扯皮。
重决策(多真实选项)在此展开 per-option pros/cons(MADR 风格);二元 / 简单决策几行带过。

## Decision
选了哪个 + 一句话为什么。

## Consequences
正向收益 / 负向代价 / 必须 follow-up。
给未来维护者最关键的一节:「推翻它会碎什么?当初接受了什么代价?」

## Links
相关 ADR(supersedes / 相关)、design 章节、外部来源。无则省。
```

**必写**:Status / Date / Context / Considered Options / Decision / Consequences。**按需**:Decision Drivers / Links。「写多少」= 写对这条决策 **applicable** 的所有节(arc42 / MADR 本身规定 optional 节可省 —— 是按适用省略,不是偷懒)。**Links 可跨 skill** 链别的 skill 的 ADR / doc 作 provenance —— committed + maintainer-only 上下文,符引用卫生硬门。

**状态流转**:`proposed → accepted`;被推翻 → 新建一条,旧条 Status 改 `superseded by <新号>`、新条写 `Supersedes <旧号>`。**不删旧条、不改旧条正文**(append-only 历史)。

## 3. 写作方法论

### 3.1 何时写 design doc
- 设计**做出来了**才写。**禁止预填空模板占位**(空 README / 空 overview 是债务,不建空架子)。
- 内容:这个 skill / 子项目**是什么、目标、范围边界、构成**(arc42 §1-3,§5,§8 的 applicable 节)。**不放**决策 rationale(那是 ADR 的)。
- **范围:只记本 skill 的设计/决策**;派生的非本 skill 笔记(框架 TODO / 别处维护项)不进 design/ —— 删除或归对应 owner(issue tracker / 框架 repo),别让 design/ 变杂物抽屉。

### 3.2 何时写 ADR(门槛 —— 治「奢侈」)
在**决策时刻**写:**≥2 个可行选项、选了一个、未来会被人问「为什么」**。满足下列任一才写 ADR:
- **架构级**(影响整体结构 / 跨多文件);
- **难逆**(推翻成本高);
- **有实质备选**(不是唯一解)。

**不写 ADR**(→ commit message / PR 描述即可):调参 / 修笔误 / 局部重构 / 纯实现细节。

判据一句话:问「3 个月后的我(或新人)会不会问『为什么是这么定的』,且 commit message 回答不够?」 → 会,写 ADR;不会,不写。

**判架构级 vs 实现级**(灰区裁决):这条决策会影响**别处**吗(别的文件 / 别处实现 / 后续多个决策)?会 → 架构级 → ADR;只影响**当前这一处**局部 → 实现级 → commit。例:「检测方法按元素类型分流」影响整个 skill 流程(架构级,ADR);「平滑核用 5×5」只影响一处(实现级,commit)。

**合并 vs 拆**:服务**同一个架构选择**的子决策(如「五步顺序」+「actionable 层停点」+「两个必填槽位」)→ 合并进**一个 ADR**(作 Considered Options / 子点),别拆碎;只有**独立**的架构决策才各成一文件。

### 3.3 design vs ADR 内容归属(分离判据)
拿不准一段内容归 design 还是 ADR,问:
- **「描述系统 / 方法论长什么样」**(陈述、构成、流程、约定)→ **design doc**;
- **「为某个选择辩护」**(为什么选 A 不选 B)→ **ADR**。

### 3.4 缩放(按复杂度,别过度工程)
- **design 文档数**:简单 skill 一个 `overview.md` 就合法。超 ~300 行、或一个文件混了多个关注点 → 才拆成 `<concern>.md`。
- **design/README.md(总索引)可选**:只有 overview + decisions 时可省(overview 即入口、`decisions/INDEX.md` 已列 ADR);有多 concern 文档需导航时才加。
- **decisions/**:有 ≥1 个架构决策才建;确实没有架构决策(极少)可不建空目录。`INDEX.md` 随第一条 ADR 一起建。
- **skill vs 子项目**:skill 的 design 通常轻(方法论 + 几条 ADR);子项目(如 currency_war)design 重(多关注点文档 + 多 ADR)。**结构同,深度不同**。

### 3.5 INDEX 替代单文件日志
`decisions/INDEX.md` 一张表给全貌(替代旧「单文件 decisions 日志」的概览功能):

```markdown
| NNNN | 标题 | 状态 | 日期 |
|------|------|------|------|
| 0001 | design 与 ADR 分离 | accepted | 2026-08-04 |
| 0002 | 框架地基级接口名可写进 SKILL.md | accepted | 2026-07-xx |
```

## 4. 边界(不进智能体执行上下文)
`design/` 全是**给后续维护者的存档,不进智能体执行上下文**。SKILL.md **不应写「见 design/...」让智能体读它获取使用信息**(命令 / 参数 / 接口)—— 使用信息内联 SKILL.md,或放 `references/` 等会被引用的辅助文件。design/ 只记「为什么这么设计 / 决策论据」。

## 5. 引用卫生(防过时)

**核心**:每条跨文件引用 = 一个依赖。安全 ⇔ (target 在已提交产物里) ∧ (稳定 ∨ 可校验)。不可校验的易变外部引用 = 必腐债务。

### 5.1 硬门(SKILL.md 规范 3 已强制)
引用 target 必须**在已提交仓库里**:gitignored(`.debug/` / `config/` / `.claude/` / `models`)、个人 local、**memory**(个人本地、不跨人共享)→ 禁。理由:skill 是共享 artifact,引用闭包外状态 = 别人 / CI / clean checkout 上不存在(类比代码硬编码 `/home/alice/...` 绝对路径)。

**范围**:门管 skill **依赖**的内容(facts / helper 脚本 / 引用的 doc,**含 design/ 内** —— design/ 也是已提交 artifact,clean checkout 的维护者同样够不到 gitignored 引用);**不管运行时操作的产物**(日志 / 截图 / 存档,skill 执行时生成、不在仓库 —— 读 `.debug/` 日志诊断、存截图建档是合法运行时引用,非依赖)。

### 5.2 防过时 4 档谱(弱 → 强;选档判据)
| 档 | 做法 | 何时用 | 代价 |
|----|------|--------|------|
| 1 依赖稳定契约 | 引框架地基级接口名(`@operation_node`),不引某文件某行(Parnas information hiding) | target 是稳定接口 | 几无 |
| 2 校验引用 | CI 扫 skill 里的路径 / 符号,验证存在 + 已提交,target 失踪 → 红(docs-as-code link/symbol checking) | target 会变但想自动发现过时 | 需建 checker |
| 3 SSOT + 运行时读 | skill 不嵌值,指稳定路径 + 指令「用到时读该文件当前值」 | 值大 / 会变,路径稳 | 读花 token |
| 4 吸收 / 自含 | 把内容复制进 skill 文件夹(co-location) | 小且必须可靠随 skill 工作 | 与源头漂移 / 重复(DRY 违反) |

**判据**:内容小 + 必须可靠 → 吸收(4);大 / 权威 / 会变 → 运行时读(3)或校验(2);稳定接口名 → 直接引(1);易变且无法校验 → 抽象化(规范 3 现状,最弱兜底)。

**现状**:规范 3 已盖第 1、4 档(「稳定可引」「自带工具吸收」);**第 2(校验)、第 3(运行时读)是缺位** —— 轻档(本版)先把此谱记作指导;重档(后续 follow-up)建 CI checker 把第 2 档落地,把"改了没发现"从靠人自觉升级到构建时保证。
