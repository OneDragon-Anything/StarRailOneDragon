# 遥测判读方法论(看什么/怎么读/视图缺口)

> SKILL.md §判读 的展开。读者 = 智能体;适用于:局后判读、跨局对照、异常定位。

## 核心原则

- **采集的基本都是有用的数据**:decisions.jsonl 的 state 是 GameState 全量序列化(deployed 含 char_id/star/equips、bench、owned 装备栏、shop、streak、保真位…)。判读不该受限于现成视图——视图没显示的维度,直查原始 jsonl(join 键 run_id+round_num)。
- **保真位先行**:hp_readable/gold_readable/board_readable=False 的轮,数值是 miss 兜底不是真值——判读先滤掉假数据,别把兜底当观测下结论。
- **单局归因是判读大忌**:一局的相关≠因果;结论要跨局对照(近 N 局同维并列)。

## 阵容质量 = 三维,缺一维就是盲判

教训存档(用户点名):**看羁绊忽略角色**(羁绊档够但核心角色不在场=空壳档位,星级演进无人看)、**装备乱用不可见**(carry 没拿 key_equips/装备乱穿/owned 滞留,所有视图都不显示装备)。羁绊档位只是三维之一:

| 维度 | 看什么 | 数据源 |
|---|---|---|
| **羁绊档位** | 配方成型进度(激活档逐轮升?恒 0=配方没上场) | board → tiers 视图 |
| **角色构成** | 核心角色在场吗(羁绊够≠核心在,空壳识别);星级演进(核心到 2★ 了吗,何时到的);同名冗余 | state.deployed[].char_id + star |
| **装备分配** | carry 拿到 key_equips 了吗;谁穿了什么(乱穿=强度浪费);owned 栏滞留(有装备没人穿=分配断线) | state.deployed[].equips + state.equips |

## 判读维度清单(逐项过,别只看最显眼的)

1. **HP 轨迹**(hp 视图):逐轮 Δ + 节点类型;中期掉血轨迹注定不达标即早停;板深只是粗代理——同板深不同构成掉血差大(三维质量才是解释变量)。
2. **阵容三维**(上表):每局至少扫一遍 deployed 构成 + 装备归属。
3. **经济轨迹**(economy 视图):滞留轮(金≥20 花=0)/收入对不上(息+连胜+基础核对,引到档金真值)。
4. **购买明细**(supply 视图):全波牌面 vs 实际购买——该买没买(供给在手里错过)/不该买买(散件固化);refresh 波不丢。
5. **执行对拍**(plan_vs_exec 视图):plan 说买什么 vs 次轮 board/bench 实际——执行层吞动作的缺口。
6. **异常标记**(anomalies 视图):金≥40 且 0买0升 / 单轮掉血≥25 / plan_error——逐条定位根因,定位不了不进下一局。
7. **胜负真值**(outcomes):killed/progress_delta/streak——输轮也记(扣血=战斗失败的游戏内记录)。
8. **换线序列**(decisions 的 target_comp 变化):同节点双 pivot = churn 信号。

## 视图覆盖矩阵(缺口=直查 jsonl)

| 维度 | 视图 | 缺口补法 |
|---|---|---|
| 掉血/板深 | hp | 板深粗代理,构成看 jsonl |
| 羁绊档 | tiers | — |
| 角色构成 | tiers(deployed 行) | 星级/装备不全时直查 state.deployed |
| **装备分配** | **无专门视图** | 直查 jsonl:state.deployed 各项 equips + state.equips(owned);新判读需求按「新视图/查询参数」纪律补,别写一次性脚本 |
| 经济 | economy | — |
| 购买 | supply | — |
| 执行 | plan_vs_exec | — |

## 判读纪律

- 异常条目当场定位(查 log + supply);跨局存活 = 回归在累积。
- 结论声明数据边界(「基于进店帧,refresh 波牌面不可见」这类)。
- 新复盘需求 = 新视图/查询参数(schema 变更查询同步),不是新 py 文件。
