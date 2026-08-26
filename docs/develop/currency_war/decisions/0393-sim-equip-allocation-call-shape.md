# 0393 装备分配 sim 调用形态保真(plane + occupied 补齐)

- 状态: accepted
- 日期: 2026-08-27
- 关联: ADR-0391(装备策略第一批)、ADR-0387(装备资产遥测)、ADR-0265(P1 组件保留)

## 背景(W212 sim 对照批暴露)

W212 批 A 基线(n=300,seed 0-299,池 861fc9f6)发现 **W211(ADR-0391)装备语义在 sim
里从未点火**:守卫拦截 0 笔、回收转化 0 笔、出口危险配对 0——不是策略没生效,而是
`cw_sim` 的 `equip_allocation` 调用点(cw_sim.py r393 段)漏传两个生产必传参数:

1. **plane 恒按默认 1**:生产 `EquipAll` 从 `last_state.plane` 现读
   (equip_all.py M7 调用点);sim 漏传 → P2/P3 段按 P1 语义跑——
   ADR-0391 死库存回收去向(`plane≥2` 生效)与 ADR-0265 P2 组件放行
   在 sim 全部不可达。
2. **occupied 恒 None**:生产传 `occupied_m7`(画面已穿,容量扣减);
   sim 恒 None → 配对守卫看不见历史已穿(`worn_basics` 只含本趟内部分配),
   跨轮守卫形同虚设;容量也不扣已穿(重复分配余量判断失真)。

## 决策

补齐 sim 调用形态,与生产 `EquipAll` 同构:

- `plane=st.plane` 现读(与生产 last_state.plane 同语义);
- `occupied` 从 `BenchChar.equips`(r393 写回的真值)构造
  `{(position_pref, slot): equips}` ——与生产 occupied_m7(画面已穿快照)同语义;
  sim 的已穿真值本就维护在 BenchChar.equips(ADR-0312 防重守卫写回),零新状态。

## Considered Options

| 方案 | 评 |
|---|---|
| **补齐两参数(采纳)** | 与生产调用点逐参对齐;sim 已有真值源(BenchChar.equips),零新状态;P1 逐位零漂移(plane=1 时行为不变,批 B fixed 臂 P1 指标与批 A head 逐位一致实证) |
| 只补 plane 不补 occupied | 回收线可达但守卫仍看不见跨轮已穿——半修;且容量口径仍失真 |
| sim 内重建独立已穿追踪 | 双源漂移(与 BenchChar.equips 两处维护),违反单一源 |
| 不修(接受 sim 不建模) | W211 后 sim 对装备面的验证承诺落空——「sim 可见 r388 类 bug」的注释即假话;且 P2 装备面检查项(后续)将空转 |

## 后果

- P1 段逐位零漂移(plane=1 路径行为不变);P2 段装备分配从「恒 P1 语义」变为真
  plane 语义——死库存回收/配对守卫在 sim P2 可点火(批 B 实测:守卫 14 笔/300 局、
  回收转化 3 笔/300 局;sim 装备获取量小,sim 终态分布不因此移动——装备效果本就是
  sim 已知未建模维度,sim 边界声明不变)。
- 验证:W212 批 A(修复前 HEAD 基线)/批 B(修复后四臂)对照 + 测试仓新锁
  (test_cw_w212_sim_equip_fidelity:capture 调用参数断言 plane/occupied 形态)
  + 全量 pytest 0 failed。

## 实况与任务书冲突记录

任务书预设「守卫拦了多少危险配对/回收线是否真转化」可在 HEAD sim 上量化——
实况:HEAD sim 上两者恒 0(调用形态缺失),量化必须先修 sim(本 ADR);
修复后批 B 才产出有效对照数字。
