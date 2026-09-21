# invest-landing-chain(投资两屏落地链迁移)

## 文档
- 设计总纲:[design.md](design.md)
- 详设:[details/gain-chain-file-split.md](details/gain-chain-file-split.md)(获得链模块拆文件方案)
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿(对抗收敛 11 条处置完毕;A2 处置与持卡面去重裁定经用户拍板)
- 设计对抗:收敛 · 报告=[attack.md](attack.md)
- 落地:阶段 2/2 done(3.1 = 8b882118b;3.2 = 0358aa60a + 测试仓 59e56910)
- 正本更新:done(清单 10 行清零;flow/README.md 经查无 pick_invest 引用,零改动)

## 迭代收尾备忘
- 遗留欠账(非本迭代范围):策划/装备/补给三屏分步上报欠账(action_ops §4.5 标注);实机局验证待跑(改代码后需重启 MCP server)。
- 用户裁定(2026-09-21):骇客改件池口径「随便随机即可」——接受现有 5 件名单,不排校准批(张力留证在池常量注释,无后续动作)。
