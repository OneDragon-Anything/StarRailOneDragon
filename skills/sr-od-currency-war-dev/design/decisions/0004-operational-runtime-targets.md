# ADR-0004 gitignored 运行时产物可作操作对象引用

## Status

accepted(2026-08-22)

## Context

skill 多处提到 `.debug/temp/currency_war/cw_dev/进度.md`、`.debug/temp/currency_war/*.flag`、后台哨兵脚本——都在 gitignore 内。规范 3 的硬门禁止**依赖** gitignored 内容(知识/facts),但明确放行**运行时操作的产物**(执行时生成/读写,本不在仓库)。

## Considered Options

1. 全部抽象化(「读项目进度文件」):智能体找不到具体路径,轮次第一步即失效——路径是操作指令本身。
2. **区分角色引用**(选):进度树/flag/哨兵 = 工作流运行时**读写对象**(合法,写全路径);CW 知识/设计/值 = 已提交仓库的 docs 与代码(合法,写全路径);唯一不做的 = 把 gitignored 内容当**事实来源**引用。
3. 把进度树挪进 git:运行状态含机器/账号差异,入共享仓库污染团队——且仓库约定明定进度归本地。

## Decision

选 2。判据沿用规范 3 原文精神:门管「skill 依赖的内容」,不管「运行时操作的产物」。

## Consequences

- clean checkout 上 skill 的运行时步骤会自建这些产物(进度树由首轮循环创建)——首次使用前 checklist 第 1 步可能读到不存在的文件,视作「无历史状态」正常推进。
