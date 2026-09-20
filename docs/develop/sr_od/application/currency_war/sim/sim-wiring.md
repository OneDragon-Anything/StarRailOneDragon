# sim 接线对照表(容器 GameState ↔ sim 引擎)

> as-built 底账(引擎直写容器形态;接线变更同步更新本表):
> sim 引擎（`sim/cw_sim_engine.py`，reset/step 步进协议，入口与驱动见 sim-design §1.2）
> 不持本地工作帧,局状态 = 容器 `GameState` 单例
> (`kernel/cw_game_state.game_state_of(session)`)。引擎写容器一律走
> 带渠道签名的写入口(渠道族封闭集 obs/logic_action/logic_hook,写入口
> 校验渠道族与 actor 在册);读容器走决策面公共读口族与 Field 直读。
> 本表逐域记录 sim 的产生面(哪个渠道、什么事件写)与读取面;用途:
> 新域的「三消费面」检查(策略/遥测/sim 代理三面同改纪律)以此为底账,
> 改 sim 接线时更新对应行。
>
> 域全集与字段级规格正本 = `game_state/fields.md`;体系纪律(单一转移
> 函数/引擎白名单/行为锁)= [sim-design.md](sim-design.md) §3。
>
> ⚠️ **逐域产生面待重核（在途）**：sim 引擎整体重做在途（重做设计经迭代过程区，git 可溯），
> 本表按旧引擎记录的产生面细节未逐域重核；重核完成前，产生面以
> `sim/cw_sim_*.py` 各模块 docstring 与代码为准，重核后更新对应行。

## 一、写入渠道(封闭集三通道)

| 通道 | 辖面 | 载体 |
|---|---|---|
| logic_action(动作应用) | 动作的字段转移全集,登记面 = `SHOP_PROJECTION_DOMAINS`(gold/bench/shop/xp/level/front_row/back_row/board/equips) | 上报函数族 `kernel/cw_action_report/report_action_<snake>_param`(每动作一函数;引擎入口 = `cw_sim_actions.apply_player_action` 一行委托分支串逐动作直调) |
| obs(外部事件) | 非动作语义的状态事实 = sim 的真值写入面 | `gs.observe(...)`,签名 = actor `SimEngineP1` + mode `synthesized` + evidence 前缀 `sim:engine:` |
| 引擎白名单(不写容器) | XP 权威账本(买牌累加/轮末结转)、牌池登记(ret/take)、金出入转录、装备分配记账、观测披露键(auth/dec_* 族)、免费刷额度注入 | 引擎本地账本与批账本(waves/actions/checks) |

obs 通道的事件面(evidence tag 括注):开局播种(opening:level/gold/hp/
bench/streak/xp)、投资注入(invest:active_env/active_strategies/
instant_gold/xp 回声)、收入结算(income:gold)、回合初始化
(round-init:node 节点键/抽牌 payload/deploy_cap/back_layout)、节点结算
(settle:hp/streak)、装备发放穿戴(equips:equips 库存/deployed 双排)、
部署代理(deploy-fill/m1p-fill/fence:bench + front_row/back_row + board
整表)、轮末升级结转(round-end:level/xp 回声)、P2 进场播种(p2-entry:
engine_p2 `build_state` 全量进场态)。抽牌 payload 的 obs 写点 = 回合
初始化与每次刷新后(重采样)。

## 二、逐域接线表

| 容器域 | sim 产生面 | sim 消费面 |
|---|---|---|
| node | obs round-init(`NodeKey`:plane/round_num/kind 三分量合一写) | 读口 `plane_of`/`round_num_of`/`node_kind_of`;策略 plane-aware 分支 |
| gold | obs opening 初值 + round-init 收入结算;logic_action 动作扣减与回金 | 读口 `gold_of`;策略消费面 |
| level | obs opening 初值 + round-end 升级结转(引擎延迟结转,申报差异见 sim-design §2.3 #4);logic_action 不写 level(升档等覆盖) | 读口 `level_of`;抽牌概率档/XP 表 |
| xp | logic_action LevelUpShop 腿(`xp_apply_clicks` 单一源:满级封顶零推进)+ obs 回声写(买牌 xp-echo/轮末结转) | 策略追级消费(clicks_to_next_level) |
| hp | obs opening 初值 + settle 结算轨迹 | 结算模型/Δ池采样 |
| streak | obs opening + settle(带符号:正连胜/负连败) | 收入侧连胜金/结算 |
| bench | obs opening 播种与部署代理整表写;logic_action BuyCard 落位/合成连锁/SellBench | 读口 `bench_view_slots_of`/`bench_entries_of`/`bench_units_of`(BenchView 槽序,kind 五分类)+ 派生 `bench_free_slots`/`bench_is_full`;策略与围栏 |
| front_row / back_row | obs 部署代理与装备穿戴整行写;logic_action 上报族按载荷落位直写两行(整行 write_logic,无中间形态) | 读口 `deployed_rows_of`(两行 Unit 容器原生)/`deployed_count_of` 等 |
| board | obs 部署代理整表重算(重算单一源 = `cw_bond_equips._recount_board`);logic_action v2 腿重算 | 围栏「成对/点火」判据/策略 |
| equips | obs 装备发放穿戴;logic_action SellBench/CompTransaction 回收腿(卖出装备归 owned 池) | 装备分配记账(引擎白名单面)消费 |
| shop | obs 抽牌 payload(回合初始化与刷新后重采样;定长 5 槽全真值,缺位 empty);logic_action BuyCard 槽置换/CloseShop 离屏 | 策略决策面(payload.cards 三态消费) |
| shop_refresh_cost | 不写(live OCR 真值域);读侧缺省回基价常量 2 | 刷新费决策 |
| deploy_cap | obs round-init 宝钻注入通道(diamond_cap_prob 参数化,默认 0 = 不注入) | 读口 `max_units_of` 封顶域 |
| back_layout | obs round-init 宝钻扩展通道(6+宝钻数,封顶 9) | 读口 `back_capacity_of` |
| active_env / active_strategies | obs 投资注入(invest= 参数;默认关 = 恒空零漂移) | 策略经济聚合子集(息帽/免费刷等) |
| 流程面域(chosen_* / settlement / encounter / supply / prep_substate / 派生域等) | sim 不产不写(sim 无画面流程;结算面以 settle 事件的 hp/streak 承载) | — |

## 三、读口族(值读单一源)

kernel 决策面公共读口族(kernel/cw_game_state.py):`plane_of` /
`round_num_of` / `node_kind_of` / `gold_of` / `level_of` /
`deployed_rows_of`(两行 Unit 容器原生)/ `bench_view_slots_of` /
`bench_entries_of` / `bench_units_of` / `back_capacity_of` /
`deployed_count_of` / `front_count_of` / `back_count_of` / `max_units_of`
+ 席位派生判定 `bench_free_slots` / `bench_is_full`。
读口负责缺省形态归一(未观察域按各读口 docstring 的缺省口径,如
gold 未读 = 0、back_layout 未读 = 机制基线 6),禁消费点自写兜底造成
第二源;引擎在此之上另有 Field 直读(gs.shop.value/gs.equips.value 等)。

表示申报:阵营不入容器——Unit 只存 char_id,阵营经角色注册表派生
(game_state/fields.md §3.2.3);引擎围栏记账用的阵营计数在引擎本地由
槽表现算,容器 board 域写经重算单一源,细节归代码注释。

## 四、保真位面(容器语义吸收)

旧帧 `*_readable`/`*_trusted` 保真位族不入容器:容器语义
「None = 不可读,禁兜底假值」天然承载可读性(gold=None 即不可读,
level 直写即真值)。引擎对旧保真位五位(enemy_difficulty_live /
level_readable / gold_readable / board_readable / bench_readable)一律
不写、不读;hp 可读/可信语义 = 政策层派生承载(hp 写入闸:非真读帧
不经 observe)。sim 无识别失真面,不产生失读值。

## 五、sim 未接域(判读申报面)

| 域 | sim 现状 | 判读影响 |
|---|---|---|
| level_up_cost | 不写;升级花费载体 = 动作 cost(策略侧 xp_click_cost 真值优先),sim 容器无真值 → 恒落兜底常量 | 花费敏感结论失真申报在案(sim-design §4.1) |
| selected_difficulty | 不写(恒未读) | 阈值回退口径 |
| enemy_affixes / plane_bosses / enemy_difficulty / game_mode | 不写(简报层未建) | 难度/boss 敏感面零变化(sim-design §2.3 #9) |
| 商店刷新计数组(free_refresh_balance/paid_refresh_count/total_refresh_count/prev_node_spent) | 不写(注入局免费刷额度在引擎本地按持卡重算) | 长线利好/二手市场计数类决策消费在 sim 走缺省 |
| 节点屏刷新计数组(encounter/supply/env/strategy_refresh_used) | 不写 | 遭遇/补给刷新策略域 sim 不可测 |

## 羁绊口径分层(board 统计语义单一源声明)

羁绊计数(board / 板深 / rung / 档位)分三层,**逐层消费、不跨层引用**:

| 层 | 内容 | 消费方 | 状态 |
|---|---|---|---|
| L1 纯羁绊全集 | 角色标签:factions+flows+independent,开拓者按排归一 | board 语义、recipe 门、tier 计算、判读 | **三处一致**(实机 `board_from_tracked` / sim `_recount_board` / checks 镜像,per-unit 单一源 = `cw_bond_equips.unit_bond_tags`) |
| L2 +装备羁绊贡献 | L1 + 星徽「加入【X】」/卡带「计数+1」(净效果无条件 +1) | board_from_tracked(实机)、Unit.equips(sim 代理同款字段)、win_features faction_counts | **落地**(equips 消费链通,sim equip_allocation 回写) |
| L3 全战力 | L2 + 装备 props 强度 + 投资策略/环境效果 + 羁绊档位效果数值 | win_model 特征、power_table、结算校准层 | 未建(挂「语料积累后」,裁定链见 sim-power-model) |

配对端点资格:Δ池任一差分的两行端点须过 `sim/pool.py` 的 `hp_pair_endpoint_admissible`(合成行恒拒 + hp 可信门;`build_pool` 与 `_pool_from_replay` 共用单件)。

判读边界:Δ池桶键(boss=净星深 v10;encounter=rung
v11,与 battle 同源 `_settle_rung`;reward/supply 深度桶
=Σboard,L1+L2 全集口径)。**池形状含位面层**:
`{节点:{位面:{桶:[Δ]}}}`,差分归属后行位面;plane≥2 采样不跨位面
回退,缺桶走位面内兜底/回退层掉血带。历史批次(≤ v10 池指纹)的
板深/rung 数字与本版本**不可裸串比**(桶语义变,跨版本对照须导出
JSON 快照重放)。

## P2 段接线(`simulate_p1(planes=2)`)

- 进场继承:P1 末态容器经 `engine_p2.build_state(gs)` 以 obs 族
  p2-entry 事件整量播种(plane=2 节点键锚/hp 跨位面继承=用户纠错
  真值/bench 保 9 槽 pad 语义/deployed 紧缩序按 position_pref 路由
  落槽);决策代码 plane-aware 分支按容器 plane 值自动激活,策略层
  零改动。
- 节点序列:`P2_NODE_SEQUENCE`(16 局 outcomes 拼版,逐槽一致;
  与 `docs/game/currency_war/research/economy.md` §10.2 单帧开局表的
  r3-r6 槽序分歧注释在代码)。
- 结算:Δ池 plane=2 桶优先 → P2 battle 回退掉血带 15-17/胜率
  0.11(小样本实机局语料);encounter/boss 沿用 P1 档+标注。
- 事件金复用 P1 表(打标未校准;P2 基础收入 5 已实测,research
  economy.md §10.1);P2 事件 overlay/简报/投资二段**披露不建模**(P2 金流/
  装备流系统性偏瘦,P2 专项面按需补建)。
- P2 headline 四联(存活轮/胜率/hp0 率/D 次数)进批报告;
  `vd_p2_enabled`(registry 布尔两态 = P2 段 V_D 口径在场/退场)的
  A/B 配对经 registry 注入实现,同池同 seed 两臂;P2 修法的分布级
  结论走 `simulate_p2_sensitivity` β/γ/事件金敏感性扫描(裁决口径)。

## 已知接线缺口的影响面(判读边界)

- **事件金 = 状态分布校准总闸**:`EVENT_GOLD_BY_ROUND` 按实机
  逐轮备战帧金轨迹反馈整定(ECONOMY_CALIB_VERSION=2,v1 批次不可比),
  使 sim 金状态分布对齐实机;对拍项 `gold_dist_calib`(金均值软告警)
  与 `shop_cost_curve`(费用曲线纯披露)进批报告。重整定触发 =
  spend_ledger/执行面修复消化「该花不花」缺口(届时注入量应显著回落)。
- **3合1 全场合并已接入**(生产 `_merge_bench` 同源;转移函数合成
  连锁腿承载)。残余失真:末轮 bench 仍 ≥9 高占比
  (9.64 均值)——候选件合法持位形态,非副本堆积;滞留金 2.17×
  未收敛,残差定位到 P1 末段花金通道(P2 继承价值 sim 不可判),
  以 `sim_endgold_calib` 披露追踪。
- **轮岗已建模**:每备战期 20% 掷轮岗(随机可翻倍档 ×2,
  其余档重归一),抽牌采样消费轮岗后表——对齐生产 20%
  帧率(实测帧率口径);lv1-3 纯 1 费无可翻倍档恒基线,与生产同态。
- **宝钻 cap 通道参数化、默认 0**:cap=level+宝钻数的获取
  频率待实机语料统计(replay cap 键落地后可采),标定前 baseline 不注入。
- **boss 胜负面(回退层)= 实机实测阶梯**:Δ池不可达
  时胜率 = ``node_win_p``(n=192,~0.05),不再随成型度 rung 变化;
  「大胜 boss」幅度未建模——hp 类 A/B 方向可信、点值 ±30% 浮动。
  主路径(Δ池)boss 深度桶采样不变。

