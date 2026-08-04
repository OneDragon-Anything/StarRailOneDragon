# sr-od-dev-screen-onboarding · 设计概览(what)

> 给后续维护者的设计存档(不进智能体执行上下文)。记方法论「长什么样」+ 边界 + 当前状态;每条「为什么这么选」见 `decisions/` 对应 ADR。

## 为什么做
建游戏知识库(`docs/game/screens/`)+ 维护 `screen_info` 时,每来一张新画面都要重复「分析 → 建档 → 建模」。把这套流程沉淀成 skill,保证后续画面:流程一致、不漏可交互元素、不踩「工具绕路 / 手编 yml」的坑。做成 skill(而非 docs)是因为 skill 触发时自动注入执行上下文(主动),docs 要记得翻(被动)。

## 定位与边界
**管**:拿到截图后的离线分析 + 建档(`docs/game/screens/`)+ 建模可交互元素(模板 + screen_info area)。

**不管**:
- 运行时识别(框架 screen matching 自己跑);
- gameplay 跨画面流程文档(归 `docs/game/gameplay/`,本 skill 只管单画面;重 app 的玩法建档触发 `sr-od-dev-gameplay-automation`);
- 整 screen 级 CRUD(增删整个画面,本 skill 只 area 级);
- 检测 / 验证 UI 区域坐标(槽位网格 / 图标按钮阵列 / 卡牌阵列)—— 用 `sr-od-dev-ui-region-detect`。

## 方法论构成(what;why 见 decisions/)
1. **五步流**(客观 → 主观 → 建档 → 缺口 → 建模):先客观(analyze,识别器视角)再主观(vision,人视角)避免只看一方漏信息;缺口分析把「已知 / 未知」显式化;建模放最后(基于缺口,不盲目)。玩法画面在前加「先搜攻略理解机制」前置;无匹配时走兜底画面(loading / 对话)。见 [ADR-0001](decisions/0001-five-step-flow.md)。
2. **工具用法**:MCP 工具直调(`analyze_screen` / `upsert_screen_area` / `delete_screen_area`);area 改动一律走 CRUD 工具(经 `save_screen` 同步独立 yml + `_od_merged.yml` + reload),禁止手编 yml / 手改模板目录。见 [ADR-0002](decisions/0002-mcp-direct-call-crud-over-handedit.md)。
3. **信息源三层并用**:截图 analyze/vision + screen_info `area_list`(全集)+ application/operation 代码(`@operation_node` 链)。代码层 caveat = 版本迁移核对(代码可能落后于游戏版本)。见 [ADR-0003](decisions/0003-three-information-sources.md)。
4. **vision 必需**:每张建档截图都要多模态 vision 看(OCR 看不见图形 / 布局 / 状态图标 / 模态性 / 朝向);vision 失败必重试。「描述画面有什么」可信、「判断状态 / 作用」不可信;朝向以 OCR 交互提示 + interact 结果为准。见 [ADR-0004](decisions/0004-vision-required.md)。
5. **截图手动分解**:app/op 内部连续动作按 `@operation_node` 节点逻辑手动分解成单步 + capture;跑 app / run_operation 仅用于验证流程通 / 到位。配套:操作后 sleep 等动画、transport 朝向重置、move 距离复现 app、边缘状态态标「待条件」+ 请用户帮切。见 [ADR-0005](decisions/0005-manual-decomposition-screenshots.md)。
6. **重 app 多子玩法按 app 维度建档**:app 编排进 develop doc、玩法机制进 gameplay doc、跨画面 op 联动 screen 记入口 / develop 记编排。见 [ADR-0006](decisions/0006-heavy-app-dimension-onboarding.md)。
7. **建档文档 = 稳定的画面参考(事实)**:描述类章节只写画面本身的事实;测试结果 / bug 修复历史 / 开放问题不混入描述章节(归测试仓 / commit-PR / 备注节)。见 [ADR-0007](decisions/0007-doc-stable-facts-only.md)。
8. **自包含 webp 工具**:`convert_to_webp.py` 自带在 skill 目录,命令内联 SKILL.md;归档 webp 兼作 mock 测试 fixture。见 [ADR-0008](decisions/0008-bundled-webp-tool-inline.md)。

## 落点
- `skills/sr-od-dev-screen-onboarding/`(`SKILL.md` + `design/` + 自带 `convert_to_webp.py`),junction 到 `.claude/skills/`(每人本地建,不提交)。
- 开发类前缀 `sr-od-dev-`(项目开发流程),与 `sr-od-dev-deciding-a-fix` / `sr-od-dev-ui-region-detect` 等同列。

## 当前状态
- 初版基于「打开游戏」一例实战跑通,后续随 onboard 更多画面(大世界 / 邮件 / 随便观 7 子玩法 / 各类玩法画面)逐步补强。
- **2026-08-04**:按 `sr-od-dev-skill-guide` 4 条硬规范重构 —— 从单 `design.md` 迁移到 `design/`(design + ADR 分开);SKILL.md 抽象化(具体 app / 场景例子迁入 ADR Context;不引 memory / 不引 gitignored)。
- **GREEN 状态:draft**(待 utility test:干净上下文子 agent 拿一张新截图按本 skill 建档,观察 gap 再修)。按 skill-guide「两类 skill」,本 skill 是**方法论覆盖型**(整合画面建档方法论),RED 可省、GREEN 必做(方法见 `sr-od-dev-skill-guide/references/skill-testing.md`)。

## 已知 todo(非架构决策,不配 ADR)
- 批量同屏改动(多个 area pc_rect 修正)用 MCP 客户端串行脚本(1 turn)比 N 次直调(同屏 save 写竞争需串行)高效;「直调 > 脚本」对批量场景待放宽说明。
- 各类画面(战斗 / 养成 / 日常)的典型元素清单(反哺 vision 预设提问)。
- 更多形状(非圆形)图形按钮的 CV 判据。
- screen_info 缺口的常见模式。

## 自身一致性
遵守 skill-guide 4 条硬规范:有 `design/`(design 与 ADR 分开);SKILL.md 指令式 + 判据;自包含(不引 memory / gitignored 依赖,自带 `convert_to_webp.py`);写方法论不写具体游戏事实(具体 app / 场景例子进 ADR Context)。
