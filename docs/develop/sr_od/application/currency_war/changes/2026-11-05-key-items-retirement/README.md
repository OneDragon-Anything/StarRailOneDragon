# key-items-retirement

## 文档
- 设计总纲:[design.md](design.md)
- 落地:[landing.md](landing.md)

## 进度
- 迭代设计:定稿(对抗第 1 轮攻击点全数处置)
- 设计对抗:收敛 · 报告=[attack.md](attack.md)
- 落地:阶段 2/2 done(3.1 退役批 = 主仓 77da60949 + 测试仓 529e7d06,全词 grep 零残留,CW 子集 3705 全过/全量失败项经 stash 对照均与本批无关;措辞收尾补丁 b82f5041d;末阶段正本更新 = 12 号篇版本 21 八处 + 11 号篇一处 + comp-definition 三处 + 黑话终扫三处修正)
- 正本更新:清零(6 条清单全部完成;10 号篇核实注记在 landing 清单尾)

## 遗留
- 实机首局观察(观察点 = `shelf_qualify_buy` 买入案例中骨架级单卡零出现;telemetry 无骨架读口,不设完成判据)——待实机局安排
- (迭代外)skills/cw_batch_stats.py import `cw_intention.pair_target_comp`(已删符号)致全量测试 collection error——or-reqs-retirement 配方层退役的孤儿引用,待另立小修
