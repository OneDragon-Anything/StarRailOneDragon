# ADR-0353: 检查器 levelup_interest_engine_gate 判据重定义(读授权依据)

- 状态: accepted
- 日期: 2026-08-26
- 关联: W123 §5.2(建议原文)、W126 §3.5/§5-5(206 现状记档)、
  ADR-0347(W119,[12] 升级门收编 EV 总账)、ADR-0349(W126 修订)、
  ADR-0352(W131 利息成本回档口径)、检查项旧指纹 ADR-0266/r406

## 背景与问题

sim 检查器 `levelup_interest_engine_gate` 仍按旧模型判据「lv≥5 升级
时点金 <50 且本局未曾满息 = 违规」计数。W119/ADR-0347 把 [12] 升级门
收编 EV 总账(`ev.levelup_ev_authorized` 三路放行)后,[33] 人口位
(cap 满∧bench 有等待上场的目标件)与 DP 花费授权的 <50 升级是
**合法放行面**,旧判据把它们全数计违规:W123 实测 378 违规/96 局
(其中 1211 帧人口位授权、1179 帧花后 <50);W131/ADR-0352 落地后
降至 206/82 局——数字下降只是授权面扩大,判据本身仍按旧口径数,
检查器对合法面失明,豁免表长期挂账。

## 决策(Decision)

1. **判据重定义(W123 §5.2 采纳)**:违规 = 「lv≥5 的 LevelUp 发生在
   时点金 <50 **且授权依据 ∉ {pop_slot, dp}**」。授权依据单一源 =
   `ev.levelup_ev_basis`(自 `levelup_ev_authorized` 拆出的放行臂名
   观测:'pop_slot'=① [33] 人口位 / 'dp'=② DP 花费授权 /
   'static_ev'=③ 静态 EV 平台账 / ''=拒)。
2. **账本观测字段先行**:sim 账本此前不记升级授权依据——补
   `cw_state.LevelUp.auth_basis`(默认 '';仿 SellBench.income
   「记录非指令」形态),arbiter 升级门与 remediation 补偿臂在
   **放行时**写入;`cw_sim` 账本序列化为 LevelUp 行 `auth` 键。
   只加观测,执行层不读此字段,决策行为零改动。
3. **static_ev 不进白名单**(保守侧):该臂花后 <50 帧量级 0-1
   (W123 §3.3),静态账是估值端,息引擎口径下保留可疑;涌现 ≥ 量级
   再裁决。无 auth 键/空值(default 栈旧调用/未过账路径)= 无授权
   依据 → 违规。
4. **不采用 hp/interest 净效应口径**(W123 同节):净效应需反事实臂
   因果识别,sim 无该载体,且会把「合法但结果差」与「违规」混为一谈。
5. **顺带清 ADR-0350 挂账(cw_plan:235)——核验后关闭,零改动**:
   该挂账针对的是**挂账时点**的旧五家人上人硬编码镜像;本批实查
   cw_plan:235 已消费 `cw_comps.skeleton_factions()`(注册表派生,
   W127 并行批 commit 8ccc46eb 落地),与评分层四体系口径同源自派生,
   硬编码镜像不复存在 → 挂账已清偿,本批仅核验关闭,不改 default 栈。
6. smoke 豁免表移除本检查项(裁决已落地,回归 0 容忍)。

## Considered Options(否决)

| 选项 | 否决理由 |
|---|---|
| 按 hp/interest 净效应定案 | 需反事实臂因果识别;「合法但结果差」≠「违规」 |
| 白名单含 static_ev | 估值端放行面在息引擎口径下应保持可疑(量级 0-1,涌现再裁) |
| 检查器内重演授权判据(逐动作重放 ev 总账) | cost/val 等决策期中间量账本不携,重演=双源漂移;读放行时快照单一源 |
| 重构 cw_plan 买门本体 | 超本批授权面(default 栈冻结);实查挂账已由 W127 注册表派生清偿,无需改动 |

## 影响(Implication)

- 检查器对新策略栈合法面不再失明:seeds 0-19 新判据 **0 违规**
  (旧判据 206/82 局口径);后续涌现的违规即真违规(无依据/static_ev)。
- 遥测/账本面:LevelUp 行新增 auth 键;生产 decisions 侧 ev_auth
  trace 已有(ADR-0347),无新增生产写入端。
- 测试:新锁 `test_cw_w131_levelup_auth_gate.py`(合法授权 0 违规/
  无依据与 static_ev 涌现/旧非违规面保留/账本 auth 键端到端)。

## 验证

- ruff 改动文件全过;新锁 4 passed;smoke 豁免表更新后 0 容忍回归;
  sim 冒测 seeds 0-19:`levelup_interest_engine_gate` violations=0
  (ledger_consistency/deploy_fills_cap/engine_seed_not_resold 同批 0);
  全量 pytest 见回执。
