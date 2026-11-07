# design/overview — sr-od-treasures-lightward

## 定位

逐光捡金系列（忘却之庭·混沌回忆 / 虚构叙事 / 末日幻影 / 异相仲裁）的**操作路由 skill**：agent 被要求打某一类时，按类型块取「操作路径 → 编队与战斗 op → 奖励」，公共节提供所有类型共用的查询与攻略路由。读者 = 无会话历史的干净智能体，经项目 MCP 操作游戏。

## 边界（引用而非重复）

- **基础配队 / 养成 / 体系知识** → `sr-od-game-coach`（本 skill 只路由，不装体系档）
- **单条 op 的实现与调试** → `od-dev-write-operation`；**运行失败排查** → `od-dev-debug-automation`；**画面建档** → `od-dev-screen-onboarding`；**新玩法从零搭建** → `od-dev-gameplay-automation`
- **具体游戏机制长文 / 坐标 / area** → 本 skill `references/gameplay.md`（玩法总览全量建档，原 `docs/game/gameplay/treasures_lightward.md`，经负责人裁决移入）与 `docs/game/screens/` 各画面 doc（skill 正文只留一句概貌 + 指针，防期次轮换导致的知识腐烂）
- **账号数据** → mys MCP 工具直拉（运行时拉取，不入知识库；练度判读口径归 `sr-od-game-coach`）

## 构成

- 总 checklist（5 步完成门）：判类型 → 收集输入 → 定阵容 → 导航挑战 → 奖励确认，对应用户指定的每块五要素。
- 公共路由：进副本 op / 基础信息查询 / 账号练度 / 攻略搜索 / 游戏内推荐阵容 / 增益直读（analyze_screen extras）/ 期次时效提醒。
- 四个类型块（结构同构：玩法概貌 / 操作路径 / 攻略与推荐阵容 / 编队与战斗 op / 奖励）+ 异相仲裁「未探明」如实声明。
- 现状边界：app 未迁移、星启未适配、「增益按位置不按名称」铁律。

## 动机

- **按类型分块**：四类玩法结构差异大且 op 不通用（如忘却之庭填队 op 只适用其编队屏布局），混用会点错画面；分块 + 每块同构模板让 agent 精准路由到可用 op，未可用的（异相仲裁）显式说「不能打」而不是猜。
- **增益按位置选择写进正文**：增益名随期轮换，把名称当识别标志的自动化会跨期静默失效；这是从实机迭代中确立的约束，属操作路由本体而非游戏事实。
- **组合 op 前置差异写明**（虚构叙事需先到编队屏、末日幻影组合 op 自行跳转、忘却之庭三段手动衔接）：调用方错配前置会直接 fail，这是 op 契约的一部分，归 skill 不归 doc。
- **玩法总览 doc 移入 skill references（负责人裁决）**：开发与打法的单一入口——开发 agent 触发本 skill 即同时获得玩法机制全量建档与操作路由；TL 知识更新随 skill 原地演进，不再住 docs/game/gameplay/（docs/game/README.md 索引保留指针；appears_in/involves_screens 双向引用的关联键是 gameplay_name/screen_name 中文名，不受文件位置影响）。
