# 遥测判读方法论(看什么/怎么读/覆盖与缺口)

> SKILL.md §判读 的展开。读者 = 智能体;适用于:局后判读、跨局对照、异常定位。

## 核心原则(用户定调)

1. **观察的数据都是对决策有用的**——GameState 的每个字段都对应一个决策消费点;遥测要全记,复盘要全面(羁绊/角色/装备/站位/经验/商店/投资策略环境都看),不是只看最显眼的维度。
2. **采集的基本都有用,别被视图边界限制**:decisions.jsonl 的 state 是全量序列化;视图没显示的维度直查 jsonl(join 键 run_id+round_num)。视图覆盖是渐进的,判读面不能跟着视图走。
3. **保真位先行**:hp_readable/gold_readable/board_readable=False 的轮,数值是 miss 兜底不是真值——先滤假数据再下结论。
4. **单局归因是判读大忌**:结论要跨局对照(近 N 局同维并列),单局相关≠因果。

## 观察面全量清单( GameState 32 字段 → 复盘问题)

按判读主题分组;「视图」列 = 现成查询覆盖(无 = 直查 jsonl);「空」= 采集缺口(字段恒空,见文末):

### 阵容质量(三维,缺一即盲判)
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| board | rounds/tiers | 羁绊档位构成;配方成型进度 |
| board_next_tier | 无 | 距下档几人(差一人没凑上=供给问题) |
| deployed(char_id/star/equips/position_pref) | tiers(名+★+装备) | 核心在场吗(空壳档位);星级演进(核心 2★ 何时到);装备归属(carry 拿 key_equips 了吗/乱穿);**站位**(前排数 vs 设计) |
| bench | 无(仅 outcome bench_count) | bench 囤什么(压缩件/final 囤件/滞留件);席满管理 |
| equips(owned) | tiers(owned 行) | 装备滞留/合成材料囤积 |
| plane_bosses | **空** | boss 克制兑现(counter 线该避没避) |
| enemy_affixes | **空** | 词条 counter 兑现 |

### 经济与节奏
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| gold | rounds/economy | 轨迹/滞留轮/息核对 |
| level | rounds(部分) | 升级节奏 vs 5→7→9 基线;错过窗口 |
| xp_progress | 无 | 经验点了几下/何时升级;半吊子点经验(金尽未升级) |
| level_up_cost / shop_refresh_cost | 无 | 折扣卡生效核对 |
| streak | **空**(state)·outcomes 有 | 连胜-保息抉择是否如设计触发 |
| bench_full_flag | **空** | 席满轮与腾席动作对齐 |

### 供给与选择
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| shop | supply | 全波牌面 vs 购买:该买没买(错过供给)/不该买买(散件固化) |
| refresh_probs | 无(7/39 有数据) | 轮岗概率条(环境效果兑现) |
| shop_locked | **空** | 锁店策略维持 |
| active_env | **空**(仅选卡时) | 环境选择与路线匹配 |
| active_strategies | trace 顶层 | 持卡演进(选了什么/何时;台账回放) |
| megastar_char / partner_char | **空** | 巨星/伙伴选择与 comp 匹配 |

### 局环境与难度
| 字段 | 视图 | 复盘问题 |
|---|---|---|
| node_type | hp | 节点类型×掉血(P1 遭遇凶于 boss?) |
| enemy_difficulty | 无(39/39 有数据) | 难度曲线实测;降难度卡生效 |
| hp/hp_readable | rounds/hp | 轨迹+保真 |
| plane_modifiers | **空** | 位面修正(战个痛快)对掉血调制 |
| selected_difficulty | runs 概览 | 职级对照 |
| front_max/back_max | 无 | 槽位异常(cap 变体检出) |
| focus_factions | 无 | focus 漂移(churn 源) |

### 决策迹(trace 顶层,非 state)
target_comp(换线序列/churn)、candidate_scores、eval_breakdown、actions、sess_*(session 态快照)、v2_mode/locked_line/bridge(策略 v2)、dp_posture(影子姿态)——AB 对拍与「为什么这么决策」的回放源。

## 判读流程(局后必做)

1. `--recent N` 概览 → 锁定目标局;
2. **hp 视图**看轨迹(注定不达标的局按早停纪律反思为什么没早停);
3. **tiers 视图**三维扫一遍(deployed 构成+装备+星级);
4. **economy** 看滞留/收入核对;**supply** 看购买对错;
5. **anomalies** 逐条定位根因(定位不了不进下一局);
6. 按当期判读主题,直查 jsonl 补视图外维度(站位=deployed 的 position_pref;经验=xp_progress…);
7. 结论写进度树,声明数据边界。

## 已知缺口(判读时心里有数)

- **视图缺口**:上表「无」标记——按「新复盘需求=新视图」纪律渐进补,别写一次性脚本。
- **采集缺口→接线状态(r358d 已补 5)**:active_env/plane_bosses/enemy_affixes(read_game_state 尾部 session→state 统一回写,注入点单一、两策略同源)、megastar_char/partner_char(handler 选择时落 session.chosen_*,同处回写)。**仍缺 reader 的 2 项**:plane_modifiers/shop_locked(观察基建未建,非回写问题,记进度树推进)。streak 一直是接好的(局46 恒 0 是结算真值,非接线缺)。这些维度的复盘暂用 log/结算屏侧数据兜底。

## 判读纪律

- 异常条目当场定位;跨局存活 = 回归在累积。
- 结论声明数据边界(「基于进店帧,refresh 波牌面不可见」这类)。
- 新复盘需求 = 新视图/查询参数(schema 变更查询同步),不是新 py 文件。
