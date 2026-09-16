# 2026-09-15-prep-single-action-contract

备战决策契约接口 `decide_prep_screen` 收口为「恰返回一个动作 / None」(规范:每个画面 op 一个接口、只产出一个动作;商店线已合规,备战是唯一遗留)。

## 文档

- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度

- 迭代设计:定稿
- 设计对抗:收敛(熔断收口;残余登记项归属将来批,见 landing 正本更新清单与 design §1)· 报告=[attack.md](attack.md) / [attack2.md](attack2.md) / [attack3.md](attack3.md) / [attack4.md](attack4.md) / [attack5.md](attack5.md) / [attack6.md](attack6.md) / [attack7.md](attack7.md) / [attack8.md](attack8.md) / [attack9.md](attack9.md) / [attack10.md](attack10.md) / [attack11.md](attack11.md) / [attack12.md](attack12.md) / [attack13.md](attack13.md)
- 落地:3.1 契约形状落码 = 208b0d6a9;3.2 契约形状锁 = 测试仓 f14f21bc(实机烟雾一局待复跑:首跑被并行批 exec_fail 钩子金账窗误报中断,诊断交接 = `.debug/temp/cw_exec_fail_false_positive_20260916.md`,修复后重跑判 §2.6 锚点);3.3 = d12e52782(明细见 landing.md)
- 正本更新:完成(d12e52782;19 条清单清零,闭域 grep 与 PrepAction 裸名复核零残留,豁免表命中逐条核对为真)
