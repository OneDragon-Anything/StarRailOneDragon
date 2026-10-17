# terminal-fail-status

## 文档
- 设计总纲:[design.md](design.md)（单文档方案）
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:终版（零防御案四轮攻击收敛：QA 弹窗删/QB 重试放大不做/QC 终结口透传本批修/QD 参数校验收拢 op 内守卫断言；开工前最后扫通过）
- 设计对抗:四轮收敛 · 报告=[attack.md](attack.md)
- 落地:阶段 2/2 done（明细见 landing.md;含扩展批 f100a7959 validate 退役 + e0aebc958 校验落点契约成文）
- 正本更新:清零（action_ops.md 决策侧参数现算契约段+零防御应用条款+词表收缩；fields.md invariant 改写；deploy-move.md 守卫断言语义；四 logic-updates emitted=False 残留清退；retirement.md 观察重派退役登记；kernel docstring 词表收缩）
- 分账:①~~validate() 退役~~（扩展批 f100a7959 本批完成）②id_mark 撞车修复（货币战争-结算 vs 战斗结算,独立批）③CwScreenShop.observe 三口与动作口双语义统一（后续批可议）
