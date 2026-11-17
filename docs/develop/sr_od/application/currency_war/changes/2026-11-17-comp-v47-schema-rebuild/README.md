# comp-v47-schema-rebuild（阵容库 v4.7 schema 重建）

> 前身：`2026-11-06-comp-schema-v2`（V4.4 口径草案，用户裁定废弃不用、新开本批）。
> 方法论裁定（P1-P8 原则/两库分立/建库校验框架/八问对账）自该草案继承，数据面（附录 A 凑件表/附录 B 实例）全弃。

## 文档

- 设计总纲:[design.md](design.md)
- V4.7 结构审计(对 v2 schema 的表达力检验,5 必改/5 待裁/8+ 验证通过):[structure-audit.md](structure-audit.md)
- 设计收敛案 v5(五代生成-对抗循环,18 字段+3 构件+V1-V11 校验+Q1-Q8 消费契约;裁决过程 = generations/gen-1..5 + 五份 review):[generations/current.md](generations/current.md)

## 进度

- 迭代设计:<v5 收敛(接管审查通过:证据抽查属实、5 必改全覆盖、faction_ceiling 缺行已补);design.md 骨架待按 v5 重写为正式总纲>
- 设计对抗:<五代循环已完成;开放问题台账见 current.md 末节>
- 落地:<未开始;v5 自判「落库条件已达」,路径 = R1-R10 判据修订批 → 试点四线 A1/B4/G希露瓦/E → D1 刃打头第二批,等用户「开始」>
- 正本更新:<未开始>

## 范围裁定（用户 2026-11-17）

- **含**：schema v2 结构定义（V4.7 适配修订）+ 19 类终局阵容与过渡库按 v2 全量落库 + FILLER_PRIORITY 凑件表 V4.7 重定 + 建库校验 V4.7 适配 + 新建测试面。
- **不含**：消费面改造（kernel 读口用适配层桥接；策略层 mandate_v1 处于策略暂缓态，恢复后另批适配）。
- **定稿协议**（用户裁定 2026-11-17）：数据不起草到用户逐套裁定——编排者按 final_comps 各篇批量起草，**自行发起对抗子 agent 优化**，**用户指令「开始」后才启动该流程**。
- **板凳身份件不进 schema**（用户裁定 2026-11-17）：char_positions 不扩 bench 值域，机制叙事归 final_comps 文档层；V4.7 落库发现板凳生效机制角色再重新提出。
