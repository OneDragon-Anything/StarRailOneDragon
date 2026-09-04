# 0388 停机刹车语义:stop_running 后执行流不得再落地动作(跨钩子族根修)

- 状态: accepted
- 日期: 2026-08-26
- 来源: run 27 停机事故第三层取证(用户点破真根因:「bot 停了还能点出战」;
  推翻编排者此前「游戏侧异步推进」判读);姊妹条目 ADR-0385(布局钩子族)

## 背景(执行流链实证)

时间线(run 27,`​.log/mcp_server.log` 32489-32514):

1. 14:09:08.825 部署钩子 `stop_running(reason=hook:back_layout_no_profile)`
   → DeployBench op 以「已停止」收口(L32489);
2. 14:09:10.377 step7 RunEquip 执行 → 又一个「已停止」(L32504)——
   **director 环在收口后的下一步仍发了动作**(EquipAll op 内部读到停止态
   才失败);
3. **14:09:12-14 step8 StartBattle →「出战成功 → 备战标识消失」(L32514)**
   ——CW 备战不自动出战,出战必是 bot 点的。

**根因 = prep_director 步进环无停止检查**:框架 `Operation` 主循环每轮
检查 `is_context_stop`(operation.py L408),但 director 的 `while True`
步进环跑在**单个 op 轮次内**(battle_loop 的一个节点),一轮内可发多个
动作——钩子设标志 → op 内 director 环继续发 step7/step8 → step8 的点击
直接落地。**停 bot ≠ 停执行流**:stop_running 只是标志位,同轮在飞动作
照跑。run 26 的「画面停在现场」是用户热键手停恰逢非此路径,非机制保证。

## 决策

1. **两层刹车**:
   - 第一层(环顶):`prep_director._run_loop` 每步先查「运行中被停」,
     已停 → 立即 `round_fail('已停止[hook]')` 收口,不再发任何动作;
   - 第二层(执行入口):`prep_actions.PrepActionExecutor.execute` 拒绝
     执行任何动作(覆盖绕环路径 `_force_battle`/恢复原语等),返
     `(False, '已停止[W209j刹车]')`。
2. **判据 = `last_run_result is not None`**(非 `is_context_stop`):
   run_state STOP 是 **idle 初始态**(ApplicationRunContext.__init__ 即
   STOP),离线测试 ctx 恒 STOP——直接查会把一切离线执行误拦;
   `last_run_result` 在 start_running 清 None、stop 时写入,是「本次
   运行被请求停止」的精确判据。
3. **族排查结论**(grep 全部 18 处 stop_running 调用点):其余钩子
   (star/summon/bookcard/shop_unknown/battle_unknown/env/strat_refresh/
   director_bail)全部 **op 节点内 return → 框架主循环 L408 接管**,同轮
   无第二步动作;唯一「一轮多动作」结构 = director 步进环(已修)+
   executor 入口(已修)——族根全闭。
4. 与 ADR-0385 决策 11/12(防抖/降级)的关系:刹车是**前提**——刹车
   不修,防抖只是少误触发,真触发了照样失控;三层(刹车→防抖→降级)
   构成完整防线,各自独立有效。

## Considered Options

- **A. 只靠框架主循环检查(op 轮间)**:拒绝——run 27 实证轮内多动作
  正是漏洞;框架层加「每 click 前检查」会侵入 controller 全部调用面
  (含 GUI 手动路径),过宽;
- **B. is_context_stop 直接判**:拒绝——idle 初始态即 STOP,离线测试/
  非运行上下文全误拦(本批测试首版即踩);last_run_result 才是「运行中
  被停」精确判据;
- **C. 在钩子处抛异常打断执行流**:拒绝——raise 消耗 retry 框架会重进
  (AGENTS 已载先例);round_fail 收口是框架协作姿势;
- **D. 停机后等画面静止再收口**:拒绝——不解决「动作不该发」,且世界
  推进不可回退(ADR-0385 决策 12 同判)。

## 影响

- `prep_director.py`:_run_loop 环顶刹车(第一层);
- `prep_actions.py`:PrepActionExecutor.execute 入口刹车(第二层);
- 测试:test_prep_director 3 锁(executor 拒动作+零点击落地 / 环顶收口
  不发动作 / idle 态不误拦);
- ADR-0385 决策 12 的降级维持(留证采集)——但降级的前提正是本刹车:
  若未来恢复某停机钩子,刹车保证停机后世界不再被 bot 推动;
- run 28 锚点:任何 hook 停机后日志应见「停机标志已设 → 环收口/拒绝执行」
  且**无后续点击/出战行**。
