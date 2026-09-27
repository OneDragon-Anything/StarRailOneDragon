# 2026-09-25-overlay-trigger(overlay 触发登记)

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/trigger-inventory.md](details/trigger-inventory.md) —— 触发事实基座:全部 overlay 出现条件/到达路径(多轮序贯)/触发形状分类/实机复核标注
- 详设:[details/deployed-merge.md](details/deployed-merge.md) —— 阶段A:DeployedView 完整槽位表合并 + TrackedBooks 退役
- 详设:[details/faction-trigger.md](details/faction-trigger.md) —— 值域回调级联与判据(资格集语义)
- 详设:[details/register-consume.md](details/register-consume.md) —— 画面变动登记接口/容器存处/两世界消费面
- 落地:[landing.md](landing.md)
- 对抗报告:attack.md ~ attack5.md(设计期五轮)
- 落地评审:3.1-3.5 与收官批复均经独立评审 worker(干净上下文)逐阶段过审,收官批复四轮终判通过

## 进度
- 迭代设计:**定稿并落地完成**(五轮设计对抗收敛;六阶段落地全过审)
- 落地:3.1 容器合并 / 3.2 TrackedBooks 退役 / 3.3 值域回调+登记 / 3.4 消费面 / 3.5 退役清扫 / 末阶段正本更新(13+2 条)——全部通过评审;最终态全量 **1733 passed, 110 skipped, 1 xfailed**,ruff 全绿,双仓语义电池六模式零,changes/ 零触碰
- 正本更新:完成(收官批复三轮清扫含正本 16+ 文件与 logic-updates 家族,「正本与实现一致」终判通过)

## 遗留项(收尾申报)
1. **planner「无→3」实机复核**:判据已按「会弹」落(新值 ≥2);实机复核若不弹,收紧回「跨入 2★」口径,单点改动;
2. **OpenTome 单击实机 journal**:代码已单击化(用户确认 2026-09-25 在册),实机局 journal 核对归后续实机批;
3. 换排(前↔后)bot 词表未接线:表示与判据已天然覆盖,接线时零新增。

~~测试仓存量 changes/ 引用与测试文件名 _33/_34 后缀~~:已由收尾清扫批清偿(测试仓 commit 768f3e708:路径 16 + 裸名 48 + 前缀残尾 12 处语义化/轮号 1 处/三文件改名;唯一残留 = test_cw_gain_chain.py 否定句纪律声明)。
