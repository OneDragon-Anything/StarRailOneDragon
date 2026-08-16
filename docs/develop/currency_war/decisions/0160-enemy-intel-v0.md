# ADR-0160 敌情层 v0(俗称归一 + boss 机制注册表 + matchup 结构层)

## Status

Accepted(2026-08-16;v1 dossier 六消费点/敌方 SIFT 采集/校准层待后续)

## Context

15 号提案诊断(全部实锤):对手信息「管线已建、资产为零、消费两个散件」——`state.plane_bosses` 观测管线通(简报 OCR 20 公司规范名);`boss_fit(comp, bosses)` 接缝建成数周;但 `comp.countered_by_bosses` 用攻略俗称(剧目/电视机/琥珀王),plane_bosses 是规范公司名(造梦兄弟影业/火线动力机甲)——**名字空间错位,接缝永不命中**(task#73 遗留,boss_fit 恒 None/0.5)。同时 19 个 boss 的机制全量躺在 bosses.md(数据银行图鉴实采)无代码消费;「剧目 boss 希儿难度大」这类克制知识躺在 cw_comps 注释里无数据链路生效。

## Decision Drivers

1. 杠杆在数据不在机制:接缝已存在,提案原话「数据层接上即生效」是代码注释自己的承诺。
2. A8 翻车主因就是敌人(competitors.md 原话),boss 节点掉血是 HP 预算最大扣减项。
3. 人类高手开局看 3 boss 定这局玩什么——公开确定性信息零观测成本进决策。

## Considered Options

- **继续让 boss_fit 空转**:拒绝 —— 20 公司规范名与俗称两套词汇无对齐则接缝永死。
- **全套 EnemyRegistry+dossier+SIFT+校准(提案 v2)**:拒绝本轮 —— L 级工程依赖实机采集(数据银行 20 阵营条目未采/敌方 SIFT 待验),按提案自己的增量路径 v0 先行。
- **v0 = 静态注册表 + 接缝接通**(采纳):一天内可验证,E1/E2 判据的先决条件。

## Decision

1. 新增 `cw_enemy_data.py`:
   - `BOSS_NICKNAMES`:俗称→规范名(剧目→造梦兄弟影业/蕉研组→造梦互动娱乐,bosses.md 图鉴标题括注实锤);未定位规范名的俗称(电视机/红绿灯/琥珀王/死龙/酒杯怪)按**机制 tag** 挂钩(`BOSS_MECHANIC_NICKS`:电视机=禁速/琥珀王=反伤类)。
   - `BOSS_MECHANICS`:20 boss 机制 tag 注册表(aoe/summon/dot/control/heal_cut/self_heal/counter_attack/share_hp/break_bonus/crit_resist/shield_break/freeze_combo/boss_debuff),来源 bosses.md(权威图鉴 OCR)。
   - `matchup(comp_mechanics, bosses) → (score, reasons)`:结构层克/利分解(`_TAG_COUNTERS`/`_TAG_SYNERGIES`,boss tag × 我方 comp 属性 tag),克制 -0.15/利好 +0.12(方向先验),**reasons 可解释输出**(供日志/复盘/12 号问询卡)。
2. `boss_fit` 接通(三段):①bosses 归一后与 countered_by_bosses(也归一)比对——**希儿量子 countered=[剧目,蕉研组] 首次真实命中**;②comp 无 countered 但有 mechanic_attributes → matchup 结构层兜底(16/20 comp 不再恒 None);③全无 → None(原语义)。
3. 测试 5 条锁定:归一/接缝命中(希儿×剧目<0.5,同 boss 组无利害=0.5)/结构层方向(治疗×削治疗=克+reason/群攻×召唤=利)/mechanics 兜底/俗称 tag 往返。

## Consequences

- E1 判据(结构层对已录战斗 hp_delta 的排序力)需 telemetry 按敌分桶 → 待实机窗口;E2(人类共识方向一致率 ≥85%)当前 8 条克/利全部来自攻略原文方向,形式合规。
- v1 待办(提案 §2.2 六消费点):comp_score 的 W_BOSS 仍 0.10(数据接通但**不升权**,提案风险 4 纪律:过度反应监控 E3 先跑);dossier/遭遇路由条件化/巨星条件化/敌方 SIFT 采集/校准层 —— 各独立增量。
- 俗称定位(电视机/红绿灯等 5 个的规范名)待实机数据银行核对后从 tag 挂钩迁移到规范名映射。
- 提案原文处理删档;决策单一源移本 ADR。
