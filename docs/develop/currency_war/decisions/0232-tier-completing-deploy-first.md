# ADR-0232 部署 tgt 序内补档优先(tier-completing deploy first)

## Status

accepted(2026-08-22;r361;局46 判读驱动;待办#2「配方满线=生存线」证据链)

## Context

局46(P1-7 放弃,HP 45):xianzhou_train 锁线下飞霄(hunt 桥 core)与丹恒·饮月(仙舟 2→3 恰达 tier1)同为 tgt 候选;cap 5 竞争中 slot 序让桥件先占坑,补档件全程 bench → **激活档整局 0** → r3 起恒 -13。近 10 局唯二 HP≥60 局(161509/200035)均配方 5 档满线;深 12-18 无差异——档位跃迁(非人次)是生存变量。

## Decision Drivers

- 既有 r288 配方底线只拦「列车挤仙舟」单向;同向 tgt 之间(桥件 vs 补档件)无仲裁
- r251 引擎 pair 排序只管 rest 序,tgt 序 = 原始 slot 序(无价值排序)

## Considered Options

1. cap 满时 swap(拖已上阵桥件回 bench 换补档件):op 层新交互(deployed→bench 反向拖拽未建模),执行风险高,超出最小改动。
2. **tgt 序内补档键排序**(选):`_tier_completes(bonds, deployed_fac)` 纯函数——上阵后任一阵营计数恰达 FACTIONS.tiers 档 → 1;稳定排序保 slot 序。cap 有余时桥件照上(r356 hunt3 语义无损)。
3. LevelUp 触发(deploy 侧发现补档件 benched → 升人口):金不足时无从升(局46 r6 实况),且越层(部署 op 管买经验)。

## Decision

选 2。锁测试 5 条(局46 场景复现/桥件无跃迁/档下不计/排序语义/流派 tag 同计);全量 964 passed。sim 对执行层排序维度不敏感(桶宽 3),按纪律声明边界——实机判读锚点:下局 [cw-deploy] deterministic 日志的 target先 序 + tiers 视图激活档>0 轮次提前。

## Consequences

- 预期行为变化:cap 紧张局补档件先上、桥件留 bench(等人口);激活档>0 的轮次应显著提前。
- swap 机制(选项 1)留待本排序不足时再议(需 op 层反向拖拽建模)。
