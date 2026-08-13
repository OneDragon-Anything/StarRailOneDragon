# ADR-0115:read_star circ 阈值放宽 0.35→0.25(备战-9 边槽假阴)

- **Status**:Accepted(2026-08-13)
- **迭代**:迭代 ADR-0114(TM + V>150);0114 的 peak 形状验证 circ>0.35 太紧

## Context

ADR-0114 的 read_star TM 法在「备战每个槽位 1星/2星覆盖验证」时发现**备战-9(最右槽)边槽假阴**:飞霄(2 星)在备战-9 读 1、在备战-4 读 2(同一角色拖动,星级不变 → 必是识别假阴)。

逐 peak 追踪根因(**非**模板/thresh/NMS):peak 形状验证的 **circ>0.35 太紧**。同颗金星在不同槽位渲染微变,circ 实测 **0.34-0.50**;备战-9 把一颗金星(area130 未裁剪、aspect0.95 星形正常)的 circ 渲染到 **0.34 < 0.35** 被误拒 → count 少 1 → 2 星读 1。备战-4 同颗星 circ=0.36 过阈 → 读 2。

即 circ 阈值落在**真金星 circ 分布内部**(0.34 是真金星,非装饰),属结构性脆弱,非个例。

## Decision Drivers

- 用户要求**备战每个槽位都覆盖**(→ 发现边槽回归;边槽正是覆盖才暴露的)
- 治本:阈值切在真金星分布内 = 结构性,放宽是正解,非「再调一次」

## Considered Options

### A. region 上移(cy>0.65→0.55)让边槽偏高星进带
**否决**:ADR-0114 已验 0.55 **反引入立绘库误判 2/71**(布洛妮娅/阿格莱雅)。且备战-9 该星 area=130(与备战-4 同)= **未裁剪**,circ 低是渲染微变非 region 裁边 → 上移 region 不解。

### B. 放宽 circ 0.35→0.25(采用)
真金星 circ 下限实测 0.34;0.25 留 0.09 余量。

### C. 移除 circ(仅靠 area+aspect)
circ>0.0 立绘库仍 0/71(见下),理论可移除。但 circ 意在滤 live **细长/碎金装饰**(fixture 未枚举全 live UI),保留宽松下限比移除稳。否决(过度)。

## Decision

**B**:`_STAR_CIRC_MIN = 0.25`(`cw_identity_obs.py`,替 inline `circ > 0.35`),peak 验证改 `circ > _STAR_CIRC_MIN`。

**验证(2026-08-13)**:
- **立绘库 71 张 0/71 误判**(circ>0.0 乃至移除仍 0/71 → 立绘库误判**不靠 circ**,area+aspect+V>150+TM 已挡死;5/71 底部带金块触发计数路径被形状拒或仅算 1)→ circ 放宽对立绘库无影响。
- **全 fixture(deployed_p1r9 / deployed_2star / deployed_2star_full)全 19 槽**:无新 FP(1★/空槽仍 1),所有 2★ 槽(前/后/备战)仍读 2(circ 0.35/0.30/0.25 结果一致)。
- **备战-9 飞霄读回 2**(live analyze + offline 双证;`deployed_2star_bench9` fixture 锁回归)。

## 关联

- 立绘库 0/71 守卫从 docstring 声明升级为**回归测试**(`test_read_star_portrait_library_no_false_positive`),改 read_star 任一阈值(area/aspect/circ/V/thresh/region)直接挡。
- 真金星计数(各位置 1★/2★)由 `deployed_*` fixture 测;立绘库测装饰误判(互补)。
