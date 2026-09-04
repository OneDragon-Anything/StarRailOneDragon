# ADR-0365: redesign.md 砍除与内容归档

- 日期:2026-08-29
- 状态:accepted

## 背景

`docs/develop/currency_war/redesign.md`(策略 v2 重设计定稿,rev9,2026-08-21;836 行)在 v2 落地完成后与 strategy/ 分篇、ADR、game/research 形成三处重叠:同一架构知识既在 redesign(设计期蓝图)又在 strategy 01-07(as-built,更准),知识分散、维护双源。用户裁决 2026-08-26:「redesign 肯定是砍掉更好,不然内容又分散了」。

## 决策

**删除 redesign.md 整文件**,内容按下表分流归档;strategy/README 吸收最小增量(动机段+边界节,共 ~20 行),不搬大段。

### 分流执行表(逐节核对后的实际去向)

| redesign 节 | 实际处置 |
|---|---|
| §1 背景与动机(四假设被推翻) | 压缩为 strategy/README 头部「为什么有策略 v2」段(动机 3-5 行级) |
| §2 核心洞察+战力基线表+统计缺陷声明 | 战力基线表已在 game/research/power_baseline.md(且带 2026-08-26 证据强度修正,比本文更准);统计缺陷声明随表;核心洞察「查表定模式」as-built 已被 formed_stop 族承接(见 README 模块地图战力表行),不作正文保留 |
| §3+§5 总体架构/决策循环 | strategy/01-07 as-built 已覆盖且更准(decision_v2 四层+纪律族);不迁 |
| §4 数据层(战力表/桥线/线库/信号/领航员) | 活模块(战力表/桥线/过渡配方)在 strategy/README 模块地图+02_comp;死模块(线库 v1/信号锁线/状态机)已随 ADR-0336 删除,历史在 git;§4.6/4.7 融合对账表左列(user_playstyle [1]-[33]、plaza M1-M16、economy §1-8)全量在 game/research 对应篇,右列设计落点在 strategy as-built 有家(买而不上→02§11 cw_intention;巨星→04;连胜金→cw_economy ADR-0262)——**无需迁移** |
| §6-8+§11 替换关系/落地顺序/验收/Phase A-B | 施工已完成,处置史在 ADR-0227(两阶段裁定)与各落地批 ADR;常量映射表(附录 A)的活常量已由代码+strategy 各篇指名,死常量随模块删;不迁 |
| §9 验证来源声明 | 证据本体全在 game/research(power_baseline/final_comps/plaza_methodology/combat);不迁 |
| §10 风险与边界 | 精简为 strategy/README 尾部「边界与已知风险」节(感知边界/显式未覆盖/版本漂移/跨局正交四条) |

### 吸收清单(strategy/README 增量)

1. 头部「为什么有策略 v2」段(四假设,~7 行);
2. 尾部「边界与已知风险」节(4 条,带「以分篇 as-built 为准」防过期锚);
3. 模块地图 5 处 redesign 链接改指 02_comp/05/power_table_meta。

### 引用处置

- 文档活链接(develop README、strategy/README、skill SKILL.md)全部改指新去处;
- **ADR 历史条目内的引用不改**(历史记录不动;0227/0246/0270/0290 等);
- **src/tools 代码注释中的「redesign §N」字样不改**(与本 ADR 同批纪律:注释是设计依据的历史引用,按 ADR-0227 同规格「全文见 git show 历史」解析;避免文档批踩 src 面)。

## 后果

- 新人了解「为什么有这套架构」→ strategy/README 头部段;「某模块设计依据」→ 该模块 strategy 篇+ADR;redesign 全文按需 `git show` 历史(本 ADR 提交前 HEAD)。
- 正:消除三处重叠,知识单一源归位(strategy=as-built,ADR=why,game/research=玩法证据)。
- 负:Phase B 完整蓝图(遥测证据三层置信/否决撤销/小样本证据设计等未落地部分)不再有活文档承载——其设计意图以摘要形式存续于本表与 ADR-0227,重启时从 git 历史取全文。

## Considered Options

1. **保留 redesign 为 Phase B 蓝图**:否——「内容又分散了」正是用户否决点;蓝图沉睡两年仍会漂移。
2. **整体并入 strategy/README**:否——违背最小增量纪律,README 会膨胀成第二份 redesign。
3. **删文件+分流表 ADR(选)**:单一源归位,历史 git 可溯,吸收面最小。
