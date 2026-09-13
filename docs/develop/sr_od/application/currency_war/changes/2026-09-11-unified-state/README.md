# 2026-09-11-unified-state

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/BoardState-数据结构设计.md](details/BoardState-数据结构设计.md)——统一 state 容器数据结构与画面字段规格
- 落地:[landing.md](landing.md)（含「已执行波次对账」节——账本外先行执行的 W1/W2/W3/W4 先行段/W5/删除波 1 凭据）
- 外溢迭代:[../2026-09-12-prep-chain-containerization/README.md](../2026-09-12-prep-chain-containerization/README.md)——prep 链容器化（承接《商店黑板容器化方案》§1.4 外溢裁定，独立迭代：prep 链签名切容器+prep/shop 两黑板槽退役）
- 找回件:[details/recovered/_INDEX.md](details/recovered/_INDEX.md)——自 .debug 找回的设计底稿存档（正文零改动；**禁作施工基准**，裁定以 为准）

## 进度
- 迭代设计:定稿（待复验）
- 设计对抗:收敛 · 报告=[attack.md](attack.md)（21 项发现已逐条裁决：成立项随修订落盘，部分驳回项记档于 attack.md 对应条目）
- 落地:批次一/二/三已落地，阶段 1-9 待做（明细见 landing.md）。批次三落位面已在产（详设 §8.7；凭据=批次锁 sr-od-test test_cw_board_state_batch3/batch4.py 在仓+落位符号级锚见 attack.md 判据核验记录）；已执行波次（W1/W2/W3/W4 先行段/W5/删除波 1）凭据对账=landing.md「已执行波次对账」节
- 正本更新:未开始

> 追认依据：账本先于本迭代文件派单的过渡安排——已执行批次各有独立落地审（旧账 reviews/），未执行批次挂对抗定稿门（T-31）之下；自定稿起判据方向 = landing 阶段小节为账本唯一源（landing 头部判据源声明同源）。
