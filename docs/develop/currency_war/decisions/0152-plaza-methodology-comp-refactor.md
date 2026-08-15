# 0152 · comp 域 plaza 驱动重构(方法论提炼 → 模型适配)

- **Status**: Accepted(2026-08-16)
- **Context**: plaza 攻略广场 match_hard 高难帖全量采集(1000 篇 → 过滤后 784 篇纯 V4.4 玩家帖)完成。
  用户要求:先从攻略 + 游戏数据**提炼玩法方法论**,再据此重构 comp 建模与策略 —— 不是把阵容抄进代码。
  方法论成文 `strategy/16_plaza_methodology.md`(M1-M11);本 ADR 记录模型层决策。
- **Decision Drivers**: 玩法本质是「角色→路线复用网络上的动态导航」(427 种羁绊组合 / 29 carry 聚类);
  现建模 factions 写死全列表、无 augment 定义型 comp、无转型成本概念,与实战形态系统性错位。
- **Considered Options**:
  - A. 抄阵容:把 29 个聚类直接翻成 29 个 Comp 条目 —— 否:失去弹性(用户明确「不是直接抄阵容」);
    聚类是频次快照,comp 是决策实体,粒度不同。
  - B. 只加数据不加模型(生成 cw_plaza_comps.py 供人看)—— 否:数据不进决策链 = 采集无意义。
  - C. **方法论驱动分层重构(选中)**:数据层生成事实层(cw_plaza_comps.py) + 手判层引用校准(COMP_LIBRARY)
    + 模型结构随方法论演进(flex 二分/augment 绑定/骨架派生/枢纽路由/转型成本/费用档星目标)。
- **Decision**:
  1. **两层架构**:`tools/cw/gen_plaza_comps.py` 生成 `cw_plaza_comps.py`(29 聚类 + PLAZA_GLOBAL,
     版本目标从 config 缓存推导防旧版污染)+ `plaza_meta.md` 人读版;`COMP_LIBRARY` 手判层以
     `plaza_carry` 字段锚定对拍。
  2. **Comp 核心/弹性二分(M2)**:`factions`(核心,form_tiers ⊆ 它,成型判定)+ `flex_factions`
     (弹性;板面/env/策略亲和/steering 消费 `all_factions`,不计成型)。
  3. **augment 定义型 comp(M1)**:`AUGMENT_COMP_AFFINITY`(黑塔纪元→大黑塔 1.0 等 4 条),
     `held_strategy_fit` 按亲和覆盖计分(镜像 ENV_COMP_AFFINITY;env 侧同步扩 12 条)。
  4. **骨架派生(M4)**:`skeleton_factions()` 从注册表派生(最低档 ≤3 人 + ≤2费成员 ≥2);
     `cw_evaluate.TRANSITION_FACTIONS` 改消费派生集 + 手工补 DoT/治疗(角色效果驱动)。
  5. **枢纽分级(M3)**:`EARLY_CORE_POOL`(Early→Final 存活 ≥0.8)/`TEMPO_POOL`(<0.45)两级;
     `char_routes()` 角色→路线网络;`pivot_overlap()` 转型成本(maybe_pivot 信号1 阈值调制
     ×0.8/×1.3)。
  6. **费用档星目标(M6)**:`default_star_goal(≤3费)=3星 / ≥4费=2星`(plaza 3星率 0.87/0.58/0.37)。
  7. **COMP_LIBRARY 校准**:↺击破流萤→巡海击破(流萤 29 篇 vs 不死途 126;非 V4.4 代表);
     万敌/昼神 B→A(use 榜 + 80连胜实证);DOT队/黄泉 core 刃→千冶·刃;新增 大黑塔银河学者/
     景元仙舟/专家桑博DOT(15→19 套);姬子 key_equips 校准(双风暴+电锯+以牙还牙跨分支)。
- **影响面**:cw_comps(结构+数据)/cw_evaluate(TRANSITION_FACTIONS 派生)/测试 5 处引用更新 +
  11 项新守卫;`strategy/16_plaza_methodology.md` M1-M11 为后续策略适配的单一源(M7 装备角色级
  分配是下一个最大缺口)。
