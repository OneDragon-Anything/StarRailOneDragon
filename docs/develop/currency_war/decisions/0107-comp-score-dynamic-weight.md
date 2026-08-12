# 0107 comp_score 动态权重(治死重常量地板;review#5)

Status: accepted
Date: 2026-08-12

## Context
review#5(策略 review 缺口):comp_score 六项中 `equip_fit`/`mechanics_fit`/`env_fit`/`boss_fit` 常返 0.5
(数据未接通:equips 空 / 无敌人词缀 / 未选投资环境 / countered_by_bosses 俗称未对齐)→ 这四项各贡献
`W_X * 0.5` 的**常量地板**。问题:全 comp 同值的项不区分,却仍占权重(死重),挤压 `progress`/`strength`
的区分力 → 选 target 时区分力塌缩。

ADR-0106 的 stopgap(把 W_BOSS 置 0、W_PROG 提到 0.55 吸死重)只搬走一项,治标;equip/mech/env 死重仍在。

## Decision Drivers
- 区分力:无数据项不该稀释有数据项的影响。
- 接通即生效:数据接通后权重该自动启用,不该靠人改权重常量。

## Considered Options

### A. *_fit 无数据返 None + 动态归一(权重重分配)—— **选定**
`equip_fit`/`mechanics_fit`/`env_fit`/`boss_fit` 无数据时返 `None`(语义诚实:无信息,非中性 0.5)。
新增 `weighted_mean(items)`:剔除 None 项,权重按有数据项归一重分配。`comp_score` 与 `comp_viability`
(prior)都改用之。

- 优:死重自动消失(无数据项不进加权);数据接通即自动生效(返非 None 就进加权);权重回归 importance 先验
  (W_BOSS 复位 0.10,不再需 ADR-0106 的 0 stopgap —— 无数据时 boss_fit 返 None 自动剔除)。
- 代价:返类型 `float → float | None`;3 个直接消费方需同步:
  ① `comp_viability` 改 `weighted_mean`(否则 `0.25 * None` 崩);② `cw_decisions._option_mechanics`
  加 None→0.5 兜底(下游 `<0.4` 比较判刷新,无信号不该触发刷新);③ `comp_score_breakdown` 的 log round
  过滤 None(`round(None,2)` 崩)。
- 附带修一个潜在 bug:动态归一让 comp_score 诚实化(无中性注水)→ 暴露 `maybe_pivot` 在 `target=None`
  时误用 signal1 gap 检查(gap 检查为「防弃 current target churn」设,target=None 无忠诚对象,该直接选 best)。
  修:`target=None` 直接返回 best。

### B. 仅 stopgap 续命(给每个 *_fit 按数据状态调权重)
每接通一个数据源就手动改权重常量。
- 否:人肉同步、易漂(接通忘改权重 = 死重复活);不治本。

### C. 中性项设极小权重(如全 0.01)
压低无数据项影响但保留。
- 否:仍是常量地板(全 comp 同值),只是小一点;且数据接通后要手动提权重,同 B。

## Decision
选 A。`weighted_mean` 进 `cw_comps`(紧邻 comp_score),`cw_performance` import 复用。权重复位 V4.4
importance 先验(W_PROG 0.45 / W_MECH 0.15 / W_ENV 0.15 / W_BOSS 0.10 / W_EQUIP 0.10 / W_STR 0.05),
撤销 ADR-0106 的 W_PROG 0.55 / W_BOSS 0.0 stopgap。

## Consequences
- comp_score 区分力恢复:无数据时只剩 `progress`+`strength` 归一(有效 W_PROG≈0.9)→ 早期强力偏好
  「可成型」comp;数据接通后 *_fit 自动进加权调节。
- W_BOSS 复位 0.10:boss 数据(countered_by_bosses 俗称对齐 task#73)接通即生效,无需再改权重。
- `comp_viability` 冷启动先验值变( equip/mech 无数据时不再注水 0.5):测试期望 0.625→0.727。
- 5 处 *_fit no-data 测试断言 `==0.5` → `is None`;真实中性(env 在但不加成 / boss 在但不命中)仍 0.5。
- 122 CW 测试过。
- **仍留下**:#6 牌池 acq(用户根因:识别 deployed/bench 身份 + 牌池剩余模型 → acq 扣消耗;更大改,
  涉 read_game_state + 牌池建模 + acq 公式)。
