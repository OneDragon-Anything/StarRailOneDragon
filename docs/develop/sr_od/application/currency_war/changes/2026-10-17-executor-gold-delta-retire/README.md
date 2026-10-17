# executor-gold-delta-retire

## 文档
- 设计总纲:[design.md](design.md)（单文档方案）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿（无前提攻击 9 项收口 + 复核可定稿，R1-R6 已落）
- 设计对抗:首轮收敛 · 报告=[attack.md](attack.md)
- 落地:阶段 2/2 done（明细见 landing.md）
- 正本更新:清零（journal.md obs_event 归属注记 + retirement.md 金差证据腿退役行 + action-logic-state/prep-executor-actions 跟随；fields.md 契约节核无双键残留）
- 分账:①`cw_exec_state._advance_gold` 直写核查 ②`shop_session.apply_gold_delta` 伴生入金归属 ③`write_logic` docstring produced_by 申报修正（design §2.4,账本 todo）
