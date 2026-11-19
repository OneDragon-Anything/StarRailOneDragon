# 恢复局机制重整（2026-11-19-resume-rebuild）

## 文档

- 设计总纲：[design.md](design.md)
- 落地：[landing.md](landing.md)
- 设计对抗报告：[attack.md](attack.md)（对抗审启动后生成）

## 进度

- 迭代设计：**定稿**（三轮对抗完成）
- 设计对抗：第 1 轮（三核）完成 · 第 2 轮（双核：核销+新眼）完成 · 第 3 轮（判据专项核销单核）完成 · 报告=[attack.md](attack.md)
- 落地：**完成**（2026-11-19，T-1..T-5 全 done；CW 域全量终态 261 passed）
  - T-1 字段收敛+重建判据：cc234625a（review 1aa86c011）· 测试仓 1d692771
  - T-2 探针链细化：d9fd9b35b（review 97a208453）· 测试仓 7318a50f
  - T-3 停点分模式：94563b0ab（review aaeb6b9d6）· 测试仓 d84dcbd3
  - T-4 收尾核签（轻验）：9bf9ac01a（review 59ae50ff4）
  - T-5 正本更新+挂账板：a849995cf + 返工 922d31eb4（review e6b4fb87a 打回 N1 → c77f536b1 复核过）
- 正本更新：完成（T-5 内含，清单 landing.md §3 十二条全落）
- **卷入构成注记**：复核 commit `c77f536b1` 除 reviews/T-5-r2.md 外连带入库并行知识消化批已 staged 的 10 张玩家知识卡（skills/sr-od-currency-war/references/，内容完整无误）——共享工作区并发 commit 卷入，照 11bbb4aa6 先例不回改历史，知识批侧已在挂账板「卷入申报二」对账认领。
