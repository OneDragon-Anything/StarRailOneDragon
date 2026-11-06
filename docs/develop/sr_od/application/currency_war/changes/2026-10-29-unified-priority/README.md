# 2026-10-29 统一让位优先级

## 文档

- 设计总纲: [design.md](design.md)
- 详设: [details/priority-model.md](details/priority-model.md)（角色统一价值序判定规格）
- 详设: [details/acquisition-and-sell.md](details/acquisition-and-sell.md)（获取角色流程 + 三触发卖出判据件 + 遥测隔离）
- 详设: [details/dismantle.md](details/dismantle.md)（拆除清单三面清点与顺序）
- 落地: [landing.md](landing.md)

## 进度

- 迭代设计: 定稿
- 设计对抗: 收敛 · 报告=[attack.md](attack.md)~[attack-r11.md](attack-r11.md)（11 轮，高阻断 4→0，零新发现收敛）
- 落地: 6/6 done（3.1 判据件 3f6442a1→1b2c3c84a→720bb11ca / 3.2 流程改造 0b93fcebe→791fbc853 / 3.3 字段迁移 7c65c7ef9 / 3.4 拆除 9237b0db7→56c665f1e→75f95af55→e342dc195 / 3.5 遥测 362b247ab / 3.6 验证 11377026〔测试仓对应 18fff6f9→2976f8d6→4adfdf56→a6c29c71→a4ec52ee→7161bc0e→ebb7ed58→6a0f81aa→11377026〕；L3 全仓 2875 passed）
- 正本更新: 清零（5f2513b9f，12 文件，changes/ 零引用自足自检通过）
- 遗留移交: ①实机冒烟（游戏在线后跑 ≥1 局判读三项：升星目标必置换/金滞留下降/无 core_* 买入；MCP server 已带最新代码，跑局无需再重启）。〔pydantic_core 彻底重装核验已完成：精确 2.46.4 装回 + pydantic 2.13.4 兼容验证 + L1 冒烟 + MCP daemon/主 server 恢复〕