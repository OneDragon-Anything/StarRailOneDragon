# 遥测判读方法论(看什么/怎么读/覆盖与缺口)

> 实机局数据判读的细则。读者 = 智能体;适用于:局后判读、跨局对照、异常定位。验收口径(什么算"打得好")的单一源 = strategy-work §2 + 当期进度账本目标行判据;sim 批侧的数据判读见 sim-testing.md。

## 查询工具(遥测 CLI)

```
uv run python -m sr_od.application.currency_war.telemetry.cli query --recent N [--run ID] --view rounds|supply|anomalies|hp|economy|all
```

- **按局档案(跨 run 段免拼段)**:正常局局终自动装配;`--match <game_id>` 直读单局档案(`--recent` 读索引;崩溃局补装配 `assemble --game <game_id>`,ADR-0486)。

- rounds=逐轮 hp/gold/买/board;supply=全波牌面 vs 购买;hp=掉血×板深;economy=金轨迹/滞留;anomalies=异常标记。
- **生产局秒级自检**:`telemetry.cli checks --recent 5`——逐局判栈(v2 栈跑 coldstart 检查,default 栈跳过),违规带 run_id 溯源;sim 批次侧等价物 = simulate_p1_batch 默认内嵌的 checks_violations。检查器自身由测试仓变异自检锁钉死(去门变异必须涌现违规)。
- 日志跨 run 累积(append+轮转,重启不销毁证据):查旧局按时间窗 grep;需关注行检索 `grep [cw!]`;格式标准单一源在 strategy/05 §6。

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

0. **先取尺子再看数——两种判读两种尺子,别混**:**单局复盘**(打得对不对)的尺子=玩法恒常标准(配方纪律/经济纪律/响应纪律/已证命题,协议=[match-review.md](match-review.md));**验证当期改动(A/B)**的尺子=当期进度账本目标行判据(没写判据=先补写再判读)+ strategy-work §2——**HP 从来不是验收指标,拿 HP 当验收=目标函数错**;
1. `--recent N` 概览 → 锁定目标局;
2. **hp 视图**看轨迹(注定不达标的局按早停纪律反思为什么没早停);
3. **tiers 视图**三维扫一遍(deployed 构成+装备+星级);
4. **economy** 看滞留/收入核对;**supply** 看购买对错;
5. **anomalies** 逐条定位根因(定位不了不进下一局);
6. 按当期判读主题,直查 jsonl 补视图外维度(站位=deployed 的 position_pref;经验=xp_progress…);
7. 结论:有异常 → 先确定异常来源,再找出治本的修复方案,然后将方案的实施状态记录到进度账本中合适的位置;同一个问题出现两次 → 必须走到治本方案这步,不许再当单局异常放下;单局结论不留;声明数据边界。
8. **局终的深度复盘不在本流程**——实机监控局终派单走 [match-review.md](match-review.md)「单局复盘协议」(干净子 agent,逐节点玩家对拍);本流程管流程卫生与视图判读,协议管「打得对不对」。

## 已知缺口(判读时心里有数)

- **字段可信度分级(历史全面审计)**——可信白名单:outcomes.hp_after(conf≥0.9)/plane/round_num/progress_delta、decisions.actions/target_comp/candidate_scores、shop_snapshots 的 offer 波牌面(gold 除外)、sess_*/v2_* 快照族、obs_conflicts。**历史脏区(修复前的旧数据)**:node_type 三源混写(英文 token/中文/旧兜底并存,后统一中文)、中止局无 runs 行、refresh 快照 gold 是算的(非真读)、首轮的 node_type 恒「普通战斗」、level 非单调偶发、board_before 是阵营人次非板深(多标签角色重复计)。判读旧局时这些字段降权。
- **phase 字段是两层语义(误判过实盘病理,W688 定性)**:P1 段 phase 恒 unlocked=设计态——P1 的锁产物记在 p1_pair,别拿 phase 判「P1 与配方脱钩」;终局锁相位只对 plane≥2 段有意义。判读锁相关行为先分清问的是哪一层。
- **视图缺口**:上表「无」标记——按「新复盘需求=新视图」纪律渐进补,别写一次性脚本。
- **采集缺口→接线状态(历次迭代已补 5 项)**:active_env/plane_bosses/enemy_affixes(read_game_state 尾部 session→state 统一回写,注入点单一、两策略同源)、megastar_char/partner_char(handler 选择时落 session.chosen_*,同处回写)。**仍缺 reader 的 2 项**:plane_modifiers/shop_locked(观察基建未建,非回写问题,记进度账本推进)。streak 一直是接好的(恒 0 是结算真值,非接线缺)。这些维度的复盘暂用 log/结算屏侧数据兜底。

## 判读纪律

- 异常条目当场定位;跨局存活 = 回归在累积。
- 结论声明数据边界(「基于进店帧,refresh 波牌面不可见」这类)。
- 新复盘需求 = 新视图/查询参数(schema 变更查询同步),不是新 py 文件。
- **别为复盘写一次性脚本**——新复盘需求 = 新视图/查询参数;确需脚本用完即删。
- **阵容质量 = 三维**(羁绊档位 × 角色构成 × 装备分配)——只看羁绊 = 空壳盲判(羁绊够但核心不在场/装备乱用都看不见;数据在 state.deployed[].star/equips 里,别被视图边界限制)。
- 改动效果对照:改策略后下一局 `--recent 5` 并列对比(测试绿≠实跑行为对)。
- **sim 批次同法可查**:sim 局产出与遥测 jsonl 同构(判读 CLI 加 `--sim-batch`,详见 [sim-testing.md](sim-testing.md) §6)——本文全部判读手法对 sim 批次同样成立。
- 判读定位的策略行为病**必须回灌 sim**(检查项/单帧锁),闭环纪律见 [sim-testing.md](sim-testing.md) §6;需要锁死的确定行为固化成单帧锁,见 [strategy-work.md](strategy-work.md) §4。

## 数据侧纪律(先查档,再动手)

- **数据源注释 > 采样凑证**:任何「X 是什么/有没有 Y」的疑问,**先查注册表/常量文件的 docstring 与采集溯源注释**(如 `cw_shop_odds.REFRESH_PROB` 的 docstring 写明「游戏内概率表实机 OCR,无位面维度」),答案已在则直接引用——**不要**先跑采样/派 worker/提「待实机核实」。历次批间互证的同类事故:①真值表早已在档仍派 worker 重采白跑;②本可 docstring 一步出答案的疑问,先跑了两局采样凑证吻合;③机制归因未先查 docstring,压测官自查后自纠。**消费侧对偶**:派单规格里的每个「现状是 Y」断言、压测报告的每个「待核实」建议,同样先过 docstring 这道门。
- **数据治理**(发现旧数据是错的——用户定调:能修复就修复,不能修复就删掉,免得误导未来):
  1. 先定界污染窗口(从采集 bug 引入的第一局起,不是发现日);
  2. 判修复/删除——真值可从别的源重算(如 decisions 逐轮行重算终值/日志回填)→ 修复;真值从未被捕获 → 删除;判不了先隔离标注,别在判读里裸奔;
  3. 派生物必须再生(replay 语料变了 → Δ 池快照重跑生成器、依赖它的 sim 基线作废重记);
  4. 留证≠留语料(事故证据 = 日志/截图/sentinel 保留;删的是分析语料行;删除动作与理由记进度账本);
  5. 防再犯——修复落写端 schema,别靠一次性手工回填(手工回填漏网 = 下一轮伪值)。
  动手前先核语义:`loss+final_hp=100` 可能是放弃局合法值(中断保留当前 HP),不是伪值——把合法数据当脏数据删,比留着脏数据更糟。

## 反例论据(为什么判读纪律这么严)

历届单点断层各自存活 3+ 局才被抓;曾把单帧牌面当全序列、误判健康线而弃线——判读流程与跨局对照纪律每条都有对应的实盘反例(存档于 design/decisions/ 与进度账本历史)。
