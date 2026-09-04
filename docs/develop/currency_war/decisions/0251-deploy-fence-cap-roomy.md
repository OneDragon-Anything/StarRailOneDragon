# ADR-0251 配方围栏富余放行:cap 紧张才拦散牌(r387)

## Status

accepted(2026-08-22;r387;commit ad31aa5b + 重建版 0b8a9826)

## Context

局62 r2 实锤:deploy_cap=3 只上 1 人(三月七成对),bench 躺 5 张(艾丝妲/阿格莱雅/缇宝/万敌全被判「不成对/非 target」留 bench)。用户 live 口径「随便上填空位也可以」。

根因是两条既有纪律真冲突:r263b 配方纪律(局15 起源:配方未满时非配方件不上板,防散件稀释配方深度)**无条件**拦截,压过了 M18 填位纪律(vacancy>2 散牌填位)。分析定谳:**配方纪律防的是「散件挤占 target 的槽位」(cap 竞争),不是「填空」**——cap 富余时散牌填空不稀释任何人(配方件来了仍有位),只有 cap 紧张时拦截才有保护意义。

落地事故(重建版 commit 记载):并行会话的 `git restore` 抹掉了 r387 未提交实现,ad31aa5b 提交时 diff 只剩标记删除行;0b8a9826 依据 commit message(根因/修法)+ r387 锁测试 3 条断言(`_cap_roomy_of(3,3,2)→T/(1,1,3)→F/(2,1,3)→F`,完备契约)+ 现行围栏拦截点(L524-531 r263b 段)零猜测重建。

## Considered Options

1. **维持 r263b 无条件拦截**:与用户 live 口径直接冲突,且实锤空槽白丢血。否
2. **撤销配方围栏(回到 M18 纯填位)**:丢失 r263b 的保护目标(cap 紧张时散件挤占 target 槽),局15 的病会复发。否
3. **条件化:围栏只在 cap 紧张时生效**(选):`_cap_roomy_of(front_empty, back_empty, must_up)` 纯函数——空位(前+后)> 必上件数(target 候选 + 同阵营成对件)→ 富余放行散牌填空;紧张(≤)→ 围栏照旧拦。两条纪律各归其位。

## Decision

选 3。围栏拦截条件追加 `not _roomy`;必上件数 = len(tgt_idx) + 成对件数(bench 同阵营 `_pair_counts>=2`),两者必然要上、须留位。模块级纯函数可单帧锁(test_cw_r387_deploy_fill_vacancy 3 条)。

## Consequences

- r263b 语义从「配方未满必拦」收窄为「配方未满 **且 cap 紧张** 才拦」——代码注释与 strategy as-built 的围栏语义按此口径;
- 锁测试 3 条 + deploy/bench/fence 群 64 passed + CW 全量 1036 passed(重建版验证);
- 该 bug 形态(富余仍拦)后续由 ADR-0253 的 check_deploy_fills_cap 常态拦截、ADR-0249 的执行层代理 sim 可发现;
- 「实现被 git restore 误抹、靠 message+锁断言重建」的教训进并行会话纪律(共享工作区禁破坏性 git 操作)。
