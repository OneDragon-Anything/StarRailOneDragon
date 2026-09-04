# 0136 M16 死循环修复(未达上限弹窗勾选缺失 + 备战席已满警告环入口感知)

## Status

accepted(2026-08-15;M16 卡死 86min 诊断)

## Context

M16 于 1-9 备战卡死 86 分钟(11:14-12:40 手动停)。日志链:bench 9 满 + 人口 5/6 → DeployMove 连环"拖3次源槽未变"(警告模态下游戏拒绝拖拽)→ stall≥5 强制出战 → 点出战弹「可出战角色人数未达上限」确认框 → `_start_battle` 轮询只点**确认**不勾「本局不再提示」→ 弹窗不消/反复弹 → 外层判"仍在备战"=fail → loop 重进 PrepDirector → 无限循环。

## Decision Drivers

- HandleDeployNotFull op(loop 0d 分支)行为完整(勾选+确认+验关)但 PrepDirector 的 StartBattle 原语没对齐 —— 同一弹窗两处处理行为不一致。
- PrepDirector 完全不感知「备战席已满」警告 —— 观察层有 read_bench_full、shop 路径有处理,唯独决策环主流程无分支。

## Considered Options

- 弹窗处理:只确认(现状)vs 勾选+确认 —— 勾选幂等(已勾无害),不勾则人口不足时**每次**出战都弹;对齐 op 完整行为。
- 警告感知:在 `_should_deploy`/DeployMove 执行器内逐动作判 vs **环入口统一判** —— 环入口(heavy 观察后)单点覆盖所有后续动作,且破警告走既有腾席链(升级扩容优先/卖最弱),与策略层复用同一决策。
- 诊断方法教训(独立于本 ADR 的流程修正):日志 → analyze_screen(框架建档权威)→ VLM;本次先 VLM 把弹窗下层残留"备战席已满"误读为主画面,analyze_screen 一眼定案(已建档屏+确认/勾选 area 全在)。已修 AGENTS.local.md 优先级 + skill 反馈。

## Decision

1. `_start_battle` 弹窗处理补勾选(先勾后确认,mouse_move 各带 bug#1 缓解);CHECKBOX_FALLBACK 常量。
2. PrepDirector._run_loop 入口:read_bench_full(last_screenshot 防御式取,离线 mock 无此属性)→ 构造 BenchFullObs(腾席链视图)走 decide_prep_action 破警告,round_wait 下轮重判(警告可反复)。

验证:test_start_battle_dialog_checkbox_equipped(勾选先于确认断言)+ 导演 33 + CW 全套 392 passed。M17 复跑验(含部署过滤/机会 pivot/经验模型全栈)。

## 遗留观察点(M17)

- 强制出战 F5 点出战成功弹窗确认后,是否真进战斗(本次修复未覆盖"确认后仍回备战"的极端;若出现,查 bench-full 是否同时在场 —— 两个模态叠加场景)。
- deployed 读取跳变(5人→3人→含 bench 没有的角色):警告模态遮挡下的 SIFT 误读,警告解除后应自愈;不自愈再查 read_deployed_chars。
