# ADR-0419: 新局开始全量状态重置(残留 match 容器入口弃置)

## 背景

W285 obs_conflict 按字段抽样判读(`.debug/temp/currency_war/w285_obs_conflict_sampling.md` §三)实证:跨局/开局状态残留是冲突三层(level / deploy_cap_vs_level / phase_round,**329 张 = 全量 7.7%**)的共同源——deploy_cap_vs_level 抽样 4/4 画面全是新局 plane1-2、cap=3 正确,旧 `level=5` 全部来自上一局;phase_round 抽样 2/3 画面真 1-9 被上局 [8,8]/[9,9] 的单调守卫打回。

泄漏机制(battle_loop/start_currency_war_match/cw_strategy 代码链亲读):正常流程局终回大厅置 `ctx.cw_match = None` → 下局 `RunLoop.handle_init` 判 `_is_new_match=True` 新建 session。但 **run 异常停在上局对局中**(停机钩子/崩溃/手停)时容器残留非 None;下一次入口链开的是**新对局**,handle_init 却把旧 session 整体延用:level 单调守卫拿上局 `last_level_obs=5` 对新局真读保旧(W285 cap_vs_level 病灶直接来源),tracked 角色/streak/hp 对账锚全部跨局带毒。

## 决策

在「确凿新局」信号处弃置残留容器,让既有的 session 重建路径承担**全量重置 by construction**:

- `cw_strategy.discard_stale_match_container(ctx, reason)`(状态宿主模块,纯属性读写):发现 `ctx.cw_match` 非 None → 弃置 + 清 plane/round last-known-good 缓存 + `[cw-entry]` warning;None → 幂等直过。
- 触发点 = `StartCurrencyWarMatch.advance_to_prep` 见到**只在无保存局新局路径出现的三屏**:难度确认屏 / 模式选择屏 / 简报屏。「继续进度」恢复的是同一物理对局,旧容器合法续用(W62/ADR-0329 恢复局链路),明确不触发。

### 重置字段清单与判定理由

重置载体 = StrategySession 整体重建(handle_init 新建分支,每字段回 dataclass 默认),逐组判定:

| 字段组 | 处置 | 判定 |
|---|---|---|
| last_level_obs / deploy_cap 链路输入 | 重置 | 局内单调守卫的锚;跨局存活 = W285 三层冲突源 |
| tracked_bench/bench_chars/deployed | 重置 | 本局阵容 tracking;新局空读重建纠漂为既有语义(obs dc627aa0 实证方向正确) |
| last_streak / last_hp / last_hp_t / last_hp_real | 重置 | 本局经济杠杆/对账锚 |
| active_strategies / active_env / selected_difficulty / enemy_difficulty / briefing_* | 重置 | 每局重新选择/重新采集;跨局存活 = 策略经济/难度从第一轮就错 |
| target_comp / v2_*/v3_*/意向/演进/纪律态 | 重置 | 本局策略跨步态(decision_v2.on_match_start 已有显式清零,重建后仍回默认,双保险不冲突) |
| performance / rng 流 | 重置(rng 不重播种,随新建走默认) | 观测反馈本局样本;run_allocator 是唯一的合法跨局存续者(进程级单例,Thompson 后验按设计累积,ADR-0170),不在 session 内,不受影响 |

单点否决方案:逐守卫加「跨局豁免」参数(修每个症状);逐字段 reset 方法(60+ 字段枚举,新增字段必漏)——容器重建把漏清面收敛为零。

## Considered Options

1. **采纳:入口三屏信号处弃置残留容器**(本批)——治本:残留源只有一个(异常停机后未清的 cw_match),在它进入消费链之前断开;触发条件用游戏画面事实(三屏只在新局出现)而非内存标志猜局界。
2. 拒:handle_init 里检测「plane==1 且 round==1 则强重置」——plane/round 读数本身被残留毒化(先有鸡还是先有蛋),且误伤恢复局(plane1 round>1 合法续跑)。
3. 拒:StartCurrencyWarMatch 入口无条件置 None——会破坏同物理局恢复(「继续进度」)与手动逐轮验证(max_rounds=1 反复 run_operation 延用 match)两个有意保留的续用场景。
4. 拒:__post_init__/create_session 内加全局清理副作用——session 新建本是干净默认,无残留可清;把进程级动作塞进数据类构造违反纯逻辑边界(cw_strategy 绝不碰 ctx.controller 同层纪律)。

## Consequences

- 异常停机后的下一局不再携带上局任何 tracked 态;obs_conflict level/cap_vs_level/phase_round 三层的跨局残留源消除(验收口径沿用 W285 批1:新局首 3 轮 JSONL 零三层条目)。
- 「同物理局恢复」仍完整保留;若停机后游戏已回大厅再起新局,靠三屏信号区分,无需人工干预。
- 局终正常清容器的既有路径不变;discard 为幂等补丁层,正常流程零行为变化。

## 验证

- 新锁 4(sr-od-test/test/sr_od/app/currency_war/test_cw_w289_match_start_reset.py,入 cw_quick):核心语义锁(第二局 create_session 关键观察域字段全默认)/幂等直过/phase_round 跨局清缓存/静态口径(恰 3 个调用点 +「继续进度」分支不触发)。
- 直接受影响测试 6 文件 46 passed;ruff 通过;L1 全集(`uv run pytest @sr-od-test/cw_quick.txt`)回归。
