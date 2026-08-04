# sr-od-dev-debug-automation · 设计概览(what)

> 本目录是给后续维护者的设计存档,**不进智能体执行上下文**(SKILL.md 不写「见 design/」取使用信息)。

## 为什么做

排查一次自动化运行 bug(完整案例见 `case-study.md`)时,踩了几个**项目专属**的坑(两个进程日志、识别路径分歧、OCR 隐藏参数、`run_status=3` 歧义),通用 `superpowers:systematic-debugging`(Phase 1-4)不管。这些判据下次排查运行中自动化 bug 还会用到,沉淀成 skill。

> 注:本 skill 的判据源自 OneDragon 系列上游项目的一次真实排查,方法论对星铁同样适用;具体到星铁的实战案例待补 —— 下次用本 skill 排查真实运行 bug 后,回来把 `case-study.md` 的案例换成星铁的并校准判据。

## 定位与边界

- **管**:排查**运行中**自动化 bug 的项目专属判据(找对日志 / 定位节点 / 识别类专项 / 采集证据)。
- **不管**:通用 debugging Phase 1-4(→ `superpowers:systematic-debugging`);定位后**决定怎么修**(→ `sr-od-dev-deciding-a-fix`);游戏功能知识(→ 代码 / screen_info)。
- **叠加而非重写**:本项目 dev skill 的定位是「叠加项目专属判据在通用方法论之上」(叠加 vs 自含的 why 见 [ADR-0001](decisions/0001-layer-on-systematic-debugging.md))。

## 构成

SKILL.md 4 节判据,每节对应一类项目专属坑:

| SKILL.md 节 | 判据 | 对应坑(论据见 case-study) |
|---|---|---|
| §1 先分清进程,找对日志 | GUI/一条龙 vs MCP server 两套日志,看错找不到 | 进程/日志混淆 |
| §2 定位故障环节(节点级) | 数重复记录判循环 vs 进展;对照 `@operation_node`/`@node_from` 流转图 | 路由节点死循环 |
| §3 识别类 bug 专项(画面/OCR) | 分析路径 ≠ bot 路径;离线遍历裁剪×阈值×区域 | analyze 误导 / OCR 迁移 |
| §4 采集证据 | 识别时刻截图(`is_debug` 门控)+ 离线同参数复现 | bot 当时看到的帧不可回看 |

SKILL.md 只写方法论 / 判据;具体函数名、坐标、版本号是某次案例的偶然细节,留在 `case-study.md` 作论据,不进 SKILL.md(`sr-od-dev-skill-guide` 硬规范 4)。

## 当前状态

- **类型**:方法论覆盖型(整合「项目专属排查判据」成系统流程)。按 `sr-od-dev-skill-guide` 两类分法,RED(baseline)可省。
- **GREEN 验证**:**待补** —— 下次排查真实运行 bug 时,确认用了本 skill 的决策比裸跑更系统;若有判据不实用 / 遗漏,回来改。当前是「写完未 GREEN 验证」,下次实战注意校准(方法见 `sr-od-dev-skill-guide` `references/skill-testing.md`)。
