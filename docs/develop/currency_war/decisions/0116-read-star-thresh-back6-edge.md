# ADR-0116:read_star TM thresh 0.50→0.45 解后排-6 边槽第2星漏(迭代 ADR-0114)

- **Status**:Accepted(2026-08-13)
- **迭代**:迭代 ADR-0114(TM thresh 0.55→0.50 解后排-3);0116 再降 0.50→0.45 解后排-6

## Context

「各槽位覆盖」(用 ``DragCwChar`` op 拖 2★ 角色遍历各排边槽)发现 **后排-6(右边槽)假阴**:椒丘(2★)在后排-6 读 1(后排-3/后排-1 同角色读 2)。逐 peak 追踪:第2星**不是**被形状拒,是**根本没检测到 peak**(TM top-8 全聚在第1星)。

多 region/thresh 组合诊断:**第2星 TM val ~0.45-0.50**(当前 thresh 0.50 滤掉);放宽 region(0.65h→0.50h)不解(非 region 裁剪),只有降 thresh 到 0.45 才检出第2星(count=2);0.40 过数噪声(count=3)。

**根因模式(whack-a-mole)**:TM 模板 a190 取自**备战栏**单星,各排金星因透视尺寸不同(后排 < 备战栏 < 前排)→ 后排星更小 → 与备战栏模板匹配偏弱 → 边槽第2星 val 系统性偏低。每降一档 thresh 解一个边槽:0.55(后排-3 val0.511)→ 0.50 → 0.45(后排-6 val~0.47)。thresh 调参是治标。

## Decision Drivers

- 用户要求「各槽位 1★/2★ 都准」—— 边槽覆盖暴露第2星系统性偏弱
- 治本(多模板 per 排)投入大;0.45 已验证安全 → 务先治标解槽位,根治留后续

## Considered Options

### A. 降 thresh 0.50→0.45(采用)
验证(2026-08-13):立绘库 71 张 **0/71 误判**(0.50/0.47/0.45 都 0)+ 全 fixture(deployed_2star / full / bench9)无新 FP(仅已知 2★ 槽 >1)+ 所有边槽 fixture(bench1/front1/front4/back1)thr0.45 仍读 2 + **后排-6 读回 2**。

### B. 多模板 per 排(根治,未采)
按排分别取星模板(备战栏 a190 / 前排 a210 / 后排 a~170)匹配各排透视星 → val 高,免降 thresh。**推迟**:需采各排单星样本 + 验证;0.45 已解当前所有已知 case。若未来再出现边槽漏(0.45 不够),升级到 B。比多尺度(ADR-0114 Considered B,连续 resize 引 9/71 误判)精准:离散步长可控。

### C. 放宽 region(0.65h→0.50h)
**否决**:诊断证后排-6 第2星不在 region 外(放宽 region 仍 count=1),是 TM val 低非裁剪。

## Decision

**A**。``_STAR_TM_THRESH`` 0.50 → 0.45(``cw_identity_obs.py``)。``read_star`` 流程不变,仅 thresh 值。

**后续(whack-a-mole 根治)**:若再出现边槽第2星漏(0.45 不够),升级到 B 多模板 per 排(各排透视星独立模板,免降 thresh)。本 ADR 标注该升级路径。

## 关联

- 各排边槽 2★ 覆盖测试(``test_read_star_edge_slots_2star``,含后排-6 回归)。
- ADR-0114(TM 法 + V>150)/ ADR-0115(circ 放宽):本 ADR 是 thresh 维度迭代,三者正交。
