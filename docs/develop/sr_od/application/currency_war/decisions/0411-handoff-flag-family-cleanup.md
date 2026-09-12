# ADR-0411 承接门 flag 家族清理:四通道从验证态转正式行为

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- 日期:2026-09-03
- 状态:accepted(编排者裁决;四通道验证结论见各前序 ADR Consequences)
- 谱系:ADR-0400(gate)/0403(proj)/0405(star 定向)/0409(M-A 定向刷新)
  ——本条是它们的终章;W257
- 任务:W257

## Context(为什么)

P1 末窗承接门家族四个通道在验证期均以 **A/B 布尔开关(默认关)**
形态落地,等待 outcome 方向裁决:

| 通道 | registry flag(已删) | 验证结论 |
|---|---|---|
| gate 承接门 | `handoff_gate_enabled` | W247-R 单开无正方向;W254-R 复核边际为负 |
| proj boss 投影 | `handoff_boss_project` | 只改门输入的标定口径修正(W238 盲区类实证) |
| star 末窗定向授权 | `handoff_star_directed` | 行为面强正(core2≥1 进场率 +150%)但单独不改变结局 |
| M-A 定向刷新 | `handoff_refresh_directed` | merges +47%/hp0 改善,但 cap6≈半跳量级 |

验证期已过,无一通道处于「待实机验证」状态,flag 的历史使命(A/B
配对臂与回退粒度)结束。滞留风险:布尔死分支继续分裂测试锁面
(off/on 双臂语义)并让默认路径持续承载「四 flag 全关」这一从未被
裁决为交付态的行为。

## Decision

**四通道全部转正为无条件启用路径;registry 四布尔字段删除;量级
常量保留供调优**(裁决=编排者):

1. **star 与 refresh 转正依据**:
   - star 是 W231「评分结构性拒副本」病灶的正解,sim 证明无挤出;
   - M-A 是 W249「策略从不支付搜索成本」病灶的对症修法,方向为正
     (hp0 改善/merge 大涨);
   - 两者的遗留问题只是**量级不够**(cap6 半跳),属参数调整而非
     行为开关。
2. **gate 与 proj 同步转正依据**:接入门是 star/refresh 授权的前提
   结构——gap 判据单一源(`handoff.handoff_gate_gap`),gate 不开则
   star/refresh 无授权语境。proj 是 hp 维标定口径错位的修法,W240
   键改净星深后常数表即终态。proj 在 v11 池下零边际但接线正确保留
   (池语料增厚后可能恢复分辨力),边界记录于 ADR-0403。
3. **代码面落点**:
   - `registry.py`:删 `handoff_gate_enabled`/`handoff_boss_project`/
     `handoff_star_directed`/`handoff_refresh_directed` 四字段;
     `handoff_gate_min_round`/`handoff_gate_tier_target`/
     `handoff_ev_gap_bonus`/`handoff_boss_e_damage 族`/
     `directed_refresh_per_round`/`directed_refresh_game_cap`
     全部保留(registry hash 重锁,test_cw_adr0293_calibration)。
   - `handoff.py`:`handoff_gate_gap` 去 flag 门、boss 投影无条件;
     薄封装 `star_directed_gap`(flag 检查+gate_gap)删除——消费点
     (candidates ×2/arbiter ×1)改直调 `handoff_gate_gap`;
     `directed_refresh_budget` 去 flag 门(peak≥2+预算两条件保留)。
   - `cw_sim.py`:A/B 批 harness `simulate_handoff_ab`(off/gate/proj/
     proj_only 四臂对照结构建在已删字段上)整体删除——验证史数字归
     ADR 存档,承接门回归资产 = 本批修订后的单帧锁族。
4. **旧锁语义演进修订**(docstring 记过期原因):
   - test_cw_w227(w227 基线臂/off-on 零漂移断言退场)、w238
     (关臂/proj_only 正交臂退场)、w242(默认关零漂移/sim star_only
     恒等臂退场)、w252(gate 关正交臂退场);
   - test_cw_w119③ 曾用 `handoff_gate_enabled=False` 隔离末窗——隔离
     手段改为 `handoff_gate_min_round=9`(把构造轮推出末窗,量级常量
     合法使用)。

## Consequences(验证)

- 合格线核验:①布尔字段清零(grep 全仓四名仅存历史注释);②量级
  常量在册(hash 锁字段表);③旧锁语义演进修订均有 docstring 过期
  记录;④ruff + L1 + 全量 sr-od-test 0 failed;⑤本条即 ADR 终章,
  INDEX 追加,03_tactics 承接门段同步。
- 行为面变化声明(P1 末窗 r≥8 承接缺口帧):成型低血不再停手、跨档
  破息买获 EV 放宽、'copy' 副本候选生成与放行、追名 peak≥2 的有界
  定向刷新——四者为 W242/W252 已验证过的「flag 全开」组合行为,
  非新增逻辑;非末窗/P2 gap 恒 0,零漂移结构前提不变。
- 红线遵守:sim 冻结导出件池口径未触碰(无 A/B 重跑需求);server
  未重启(新码由下局装载)。

## Considered Options

- **仅转正 star/M-A,gate/proj 保留 flag**:拒绝——gap 判据是两授权
  通道的语境开关,gate 关则 star/M-A 死码;保留单字段=脏粒度。
- **全部删除行为(不转正)**:拒绝——与编排者裁决冲突;star/M-A 方向
  证据为正且 sim 无挤出证据。
- **保留 flag 但翻转默认值为 True**:拒绝——布尔仍需双臂测试锁维护,
  「永远开的开关」正是本次要清的死分支形态。
