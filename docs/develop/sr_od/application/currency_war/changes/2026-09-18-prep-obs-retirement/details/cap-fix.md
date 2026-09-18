# 部署名单换源 + cap 门槛（详设，阶段 3.1）

## 问题与约束

- 总纲接口契约 1（禁预删黑板字段）、2（失读=carry）、3（坐标契约）约束本篇。
- 事故链（依据 `.debug/temp/incidents/20260918-reconcile/rootcause-reopen.md` 案一 + match_g_20260918_023823 journal）：02:40:14.385 拖椒丘发出后容器 front_row 已记 3 人（v117，逻辑态写端正确），而 14.387 决策帧经黑板组装的上场名单仍 2 人 → kernel 逐候选上限判定（cw_deploy_logic.py:651 `len(deployed_cids) + len(up) >= cap`）按 2/3 放行第 4 拖 → 游戏静默拒收。
- 约束：kernel 谓词与部署判据式不动；只换输入源、加上限前置门、落拒因台账。

## 方案

### 1. 决策帧组装层换容器名单源（entry.py:607-608）

```python
# 现：bench = list(obs.bench_chars); deployed = list(obs.deployed_chars)
bench = [c for c in bench_slots_of(gs) if c is not None]
deployed = [c for c in deployed_slots_of(gs) if c is not None]
```

- 元素类型不变：容器槽表元素即 `BenchChar`（含 char_id/star/position_pref/slot），下游零类型适配（依据：cw_game_state.py:4974-5000 两读口 docstring）。
- 五类下游自动归位：部署计划输入（mandate.py:2163 `deployed_cids` 派生）、`MandateFrame.deploy_vacancy`（mandate.py:211-218）、`check_seats` 席位门、停买判定与线状态（`proof.stop_buy`/`update_line_state` 消费 `deployed_names`）、升级授权谓词（mandate.py:1554 `predicates.arm1_existence(len(frame.deployed), ...)`、mandate.py:1565-1568 `predicates.arm0_level_lag(..., frame.deployed, ...)`、mandate.py:1583 `levelup.pop_slot(len(frame.deployed), ...)`）。
- **M7 的 deployed 读点同批切换**：cw_equip_wear_plan.py:182 `deployed = list(getattr(obs, 'deployed_chars', None) or [])` 是 M7 对黑板名单的直接读点（不经 entry 组装，批 1 的帧换源覆盖不到），同批改 `deployed_slots_of(gs)` 派生——否则批 5 删字段即断装备计划的 deployed 消费。
- 未识别件口径保持：`deployed_cids` 构造继续过滤空 char_id（识别失败件不进 ID 集合），其 cap 计数缺口由下述显式门（占用数口径）把守——两道防线分工见「关键取舍-2」。

### 2. wanted 臂实参同批换源（entry.py:574）

`wanted_closure_emit(session, gs, list(obs.bench_chars), list(obs.deployed_chars), ...)` 实参换成容器名单（同 §1 变换）。理由：该臂的部署腾槽腿与事故同族（用名单判 cap/席位，mandate.py:1017-1031），且不换会出现同一决策入口「帧名单=容器、臂名单=黑板」的双源并存。腾席空位判定 `deploy_cap - len(deployed)`（mandate.py:1017）随之自动归位。

### 3. cap 键单一源（mandate.py `_deploy_plan_inputs`）

`'cap'` 键改 `max_units_of(state)` 直读（cap 真值 ≥level 采信、封顶=前排 4+back_layout 动态真值，cw_game_state.py:5040-5052）；`frame.deploy_cap` 缺读退 `10**6` 的无限回退分支退役（`max_units_of` 恒 ≥1，该分支不可达——依据：entry.py:787 装帧时 `deploy_cap=max_units_of(gs)` 已无 None 路径）。

### 4. 显式板满门 + 拒因落账

- 门判式：`deployed_count_of(state) >= max_units_of(state)`（占用数口径，ADR-0392，`deployed_occupied` 单点——禁裸 len 槽表）。
- 武装位置：`_emit_deploy_moves`（发射位，mandate.py:2205-2208 前）与 `_deployable`（放行判定，mandate.py:2273 前）——两者是全部部署路径的必经点（4 个发射位 + wanted 臂 + 放行判定全走）。
- 门行为：零发射 / 返回 False；拒因 `deploy_cap_full` 落 `cw4_counters` 计划级分键，帧级去重沿用 `DEPLOY_EMIT_TELEMETRY_ATTR` 注册表手法（mandate.py:2119-2128 同族）。
- 语义分工（与既有候选级键并存）：`deploy_emit_held_cap` = 「某候选因 cap 留 bench」（可能是板满、也可能是本轮已排满）；`deploy_cap_full` = 「本帧板满（占用≥cap），部署计划不产出」——确定性申报超上限拒收在规划层被拦截。
- 不实现板满自动卖出：交决策循环既有步骤序（含 M4 卖出臂），策略行为另案。

### 5. 不动的相邻面（边界申报）

- 球路径腾席判据（entry.py:522-566）：结构性死码（触发集 `SPHERE_OCCUPYING_COLORS` 现役空集，entry.py:138；注释明文「保留原位，当前不可达」），本阶段不动。其块内直读 `obs.spheres`（:524）与 `obs.bench_chars`/`obs.deployed_chars`（:534-539）的换源**归属阶段 3.4**（球域立域时同批切换，见 obs-retirement.md §阶段 3.4-5）——批 5 删字段前该块必须已完成换源，否则不可达保护失效后即 AttributeError。
- `PrepObservation` 的名单字段本体与黑板投影腿：批 5 面，本阶段禁删（总纲契约 1）。

### 6. 失读方向等价性论证（总纲契约 2 的本篇落实）

换源后失读帧行为差核对：
- 入口 heavy 失读（识别退化）：黑板走缓存沿用（cw_screen_prep.py:630-631）↔ 容器走 carry 保旧值（:683-720 空集守卫族）——两向同效（保旧值）。
- 合成特效窗：两本账同门不写（:678-681 与 :703-706），换源无差。
- 未观察帧（容器全 None 缺省形态）：不可达——备战环入口观察先于决策（同一次 `_observe` 内 620-711 完成容器写入，决策帧构造在其后）。
- **字段级往返等价申报**：容器槽表元素经 `bench_slots_to_legacy` 重建，`faction` 不入容器、出容器时按角色注册表重派生（cw_game_state.py:1496-1530）——与 SIFT 直读 BenchChar 的 `faction` 字段非同一来源。消费面核对：`DeployMove` 发射消费 `frame.bench[bi].faction`（mandate.py:2235，sim board 计数用）。一致性依据 = 重派生与识别层同源角色注册表（`factions[0]`）；未注册角色两侧同为空串，分派一致。此差异在本阶段申报在案，不构成行为分叉。

### 测试（三锁 + 回归）

1. **事故形态锁**：容器 3/3 满 + 决策帧（黑板）名单 2 人 + 备战席有候选 → 零拖拽发射、`_deployable` False。
2. **陈旧视图锁**：同上场景断言部署输入来自容器（现读胜出）；反向例：容器 2/3 未满时照常产出部署（防换源改坏正常路径）。
3. **拒因台账锁**：板满帧 → `cw4_counters['deploy_cap_full']` 计数且帧级去重。
4. 回归：停买/升级授权/check_seats 相关既有测试适配容器构造（只构造黑板不构造容器的用例需补）。

## 关键取舍

1. **方案 B（组装层换源）vs A（装配单点换源）**——用户裁定 B（2026-09-18）。A 只覆盖事故面；B 让停买/线状态/升级授权同时归位，代价是这批无事故背书的消费面要逐个重验语义（方向都是输入更准）+ 测试牵动更大。放弃 A 的原因：避免「治本批再切一次同文件」的两头上不靠。
2. **显式门用占用数口径 vs 复用 kernel 的 ID 集合口径**——kernel 逐候选判定 `len(deployed_cids)` 对 SIFT 未识别件（char_id=''）系统性偏松（未识别不计数）；显式门用 `deployed_count_of`（ADR-0392 占用数口径）把该边界一起堵住。两道防线非冗余：换源修主形态，门堵口径边界 + 提供计划级确定性拒因。
3. **拒因落 `cw4_counters` vs journal 事件**——拒因家族现役载体即 counters（`deploy_emit_held_*` 家族，mandate.py:2130-2131），计划级键随家族；journal 是观察/写入事件账，不作拒因载体。
