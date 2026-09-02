# DD-016:cap 空槽补部署——P24 残余补部署支配接线到部署执行层

## Status
accepted

## 背景
复盘 g_20260902_181254(修复项 E):P1 r2–r4 板面 3/4(cap=4),bench 有件不上,空槽持续到 r4。
P24(残余补部署支配定理)已证:多一个上阵位 → 战力正支配,skip 轮补空槽 ΔEV≥0;[31]③
「有羁绊的板 > 空槽」。

## 根因
`DeployBench._deploy_deterministic` 的散牌留置门(ADR-0130 散牌留 bench 防 spread 吸引子、
r263b 配方围栏、r288 配方底线)辖「**选谁优先**」语义,但留置结果在「板未满」时把支配性收益
(空 cap 槽 vs 空板)一并放弃了——留置门没有「cap 富余时放行填空」的出口(r387 `_cap_roomy_of`
只覆盖配方围栏分支,不覆盖 ADR-0130 留置分支)。

## 决策
主排序循环结束后,若空槽仍在(cap 动态未满)且散牌留置(`_held`)非空 → 按纯函数
`residual_fill_plan` 生成的计划补部署。守卫:
- **同名禁双**(5.1.7):与场上同名的留置件跳过——dup 是 3合1 素材,游戏拒收同名上阵
  (局14 藿藿 5 连败实证),不生成拖必败计划;
- **cap 动态**:以现读 deploy_cap 计数,计划数达 cap 即停(cap=None 不设门,拖到游戏拒即真值,
  同主循环 5.1.8 口径)——「吃 cap 动态读值,别信固定槽位数」;
- **选排**:按 position_pref 选排,首选排满 fallback 另一排,两排皆满停;
- 执行侧每拖前 fresh 复查源槽占用(主循环同款)。

## Considered Options
- **修决策层(_free_bench_step/candidates)**:腾席链 a 与 `_deploy_candidates` 板缺帧已供全量
  候选,瓶颈在执行层留置门;决策层再补一道属重复供给,不取。
- **解除 ADR-0130 留置(全局散牌照上)**:spread 吸引子风险回归(M14/M15 fp 冻结实证),
  留置门在「选谁优先」语义下仍有价值;本决策只在「空槽残余」面放行,语义最小,取。
- **连 r288 配方底线件(列车封顶)一起补**:底线是线内质量仲裁(P24 的 ΔEV≥0 未对
  「挤占未来配方位」形态背书),保守不放,留置继续(该件本轮由 r288 分支 `continue` 跳过,
  不在 `_held`)。

## Consequences
- 正面:cap−deployed≥1 且 bench 有可上阵(非 dup)角色时板面必满员,消灭「有位不上」形态;
  留置门保留(只改残余面),spread 风险不回归。
- 边界:补的是散牌(非 target 非成对),板面羁绊质量仍受 ADR-0130 排序约束——补部署支配
  证明的域就是「空槽 vs 空板」,不主张散牌优于等待 target 件(那是排序问题,归主循环)。
- 测试:`residual_fill_plan` 纯函数 5 条
  (`sr-od-test/test/sr_od/app/currency_war/test_cw_dd015_equip_blacklist.py` E 段)。
