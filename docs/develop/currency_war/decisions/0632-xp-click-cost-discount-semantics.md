# ADR-0632: xp 买费折扣三段语义——显示价直通/兜底减折扣族/升级取价单一源委托

- 日期:2026-09-10
- 状态:已实施(commit 随本 ADR 同窗;验收 = `reviews/xp折扣修复-落地审.md` accept 条件记档,文档同步=commit 门放行条件随本 ADR 闭环)
- 关联:ADR-0131(`xp_buy_cost_discount` 聚合语义)、ADR-0275(flat-4 定论:单击价基准恒 4)、ADR-0289(原 flat4 台账锁设计)、ADR-0561(申报表 #5:sim 支出载体统一为 `action.cost`)、`docs/develop/currency_war/game_state/strategy-env-impacts.md` §2 通用模式 1 与 §3 商业间谍条(规范语义单一源)、`kernel/cw_economy.py`(`xp_click_cost`/`upgrade_plan_fee`)、`sim/checks/ledger.py`(`check_levelup_flat4_ledger_lock`)、`sim/engine_p1.py`(执行扣费)

## 背景

商业间谍局实机费用路径双扣(T-217 核对定谳活 bug):改前 `xp_click_cost` 对两支来源无差别再减折扣——显示价本为游戏算好的折后价,再减一次 → 3−1=2,真值 3。同族缺口三件:①成长的快乐(8 级后 −1)注册表已登记(聚合字段在册)但消费位不消费——「登记不消费」豁免口,sim 恒兜底支 → sim 对该卡局费用恒虚高 1 金/击,恰是 sim/实机费用分歧类;②`upgrade_plan_fee` 裸读 `state.level_up_cost or FALLBACK` = 第二处独立取价实现,零折扣(反方向单侧错:间谍局兜底形态 4≠真值 3);③flat4 台账锁字面判据 `spend.levelup == 4 × LevelUp 行数` 与支出载体统一(ADR-0561)在折扣局在先矛盾——真实间谍 sim 局 spend=72=3×24,旧锁索 96,逐轮误报。

## 决策

1. **`xp_click_cost` 两支语义**(分支判别 = `state.level_up_cost` truthiness,与改前同 falsy 契约,0≡缺省):
   - **显示价支直通**:观察值为最近备战帧的游戏显示价,游戏侧已算好全部折扣(商业间谍/成长的快乐等)→ `max(0, 原样直通)`,不再减任何折扣。依据 = 用户裁定「显示价即折后价」(strategy-env-impacts §3 商业间谍条,2026-09-10 确认)。
   - **兜底支减折扣族**:观察缺省才逻辑兜底 = 基准 `XP_CLICK_COST_FALLBACK`(恒 4,用户口径非按等级)−[`xp_buy_cost_discount` + 等级门折扣(`state.level ≥ xp_click_discount_from_level_at` 时加 `xp_click_discount_from_level`;哨兵 0=未持有短路)],`max(0)` 钳。折扣族聚合单一源 = 注册表 STRATEGY_ECONOMY(分型 sum+guarded_min,已在册),零新耦合;成长的快乐接入消费位,关闭「登记不消费」口,sim(恒兜底支)与实机(常态显示价支)语义一致,无分歧形态。
2. **`upgrade_plan_fee` 一行委托**:`clicks_to_level(state.level) * xp_click_cost(state)`——取价语义与 `xp_click_cost` 永不分叉,禁第二处独立折扣实现(源面结构锁断言函数源含 `xp_click_cost`、不含 `level_up_cost`/`xp_buy_cost_discount` 字样,防复活)。
3. **flat4 台账锁重推为载体一致性判据**:`spend.levelup == Σ(LevelUp 行 cost)`(cost 缺读/0 按 engine_p1 同口径 `getattr(a,'cost',0) or 4` 兜,旧档案行不因代际漂移)。「4」实为无折扣局快照,非锁真不变量;无折扣局该判据退化为原字面 4×行数,零松绑;执行器弃 `action.cost` 回退私价模型仍被拦(批⑨ F1 回归,spend≠Σcost 必红)。价格面真值(取价是否含对折扣)不在本锁辖域,由 kernel 侧 xp 折扣锁族把守——两域分工防决策层与执行层同错互证。

## Considered Options

- 显示价支维持减折扣(改前形态)——否决:显示价即折后价,再减=双扣,与规范语义单一源(strategy-env-impacts §2 模式 1)直接冲突,是本修复的本体。
- 兜底支维持仅商业间谍减项(登记不消费豁免维持)——否决:sim 恒兜底支,不消费=对该卡局费用恒虚高,恰保留本修复要消灭的 sim/实机分歧类;折扣族聚合已在注册表,接入零新耦合。
- 锁判据按折扣卡名单硬编码(间谍局 3×行数)——否决:与 Σcost 形态等价,但注册表扩折扣卡即再度锁红;载体一致性形态治本。
- `upgrade_plan_fee` 保留独立取价并补折扣——否决:「同一语义两处实现」即互补单侧错漂移温床(实证:改前委托侧零折扣 vs 主侧双扣,两侧各错一边)。

## 后果

- 行为变化面(有意变更):商业间谍局显示价支 2→3(修双扣);间谍+快乐 lv≥8 兜底 3→2(快乐接入,真值表 lv7=4/lv8 起 3、叠加间谍 3/2);`reserve_cap`/`channel_capacity` 随委托修复兜底形态单侧错(4→3×击数,碰巧对→结构性对)。**无折扣局(折扣合计=0 的全部状态)新旧公式逐位一致**——display×level 90 组合矩阵+快乐门前 14 组合亲验漂移数 0。
- 边界申报:显示价支 = 最近备战帧观察值语义(写端仅在备战观察权重开启帧更新,非本帧保证;过期窗方向可自愈、有界);奋斗协议(xp_buy_hp_cost)血本位出域,血闸独立车道 `blood_xp_gate` 承接;报表面 `telemetry/query.py` luc 口径不含折扣为登记不改面(非决策面,候裁另立)。
- 验证:新锁 13 收集项先红后绿(经济 7 函数 11 收集项+sim 双向锁+间谍局 sim 对账;红态 7+2 failed 逐锁归因,绿态全绿)+L1 3261/L3 3787 亲跑在案(落地审 §4 亲跑复现)+落地审独立样本 21 断言亲验(不复用测试仓 helper)。
- `engine_p1.py` cap 守卫处的过期注释(仍写原字面判据)随本 ADR 勘正,零行为。
