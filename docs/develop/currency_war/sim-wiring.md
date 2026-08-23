# sim 接线对照表(GameState ↔ cw_sim)

> as-built 存量清查(2026-08-24,批 B 件3):GameState 36 个字段在
> P1 模拟器(`cw_sim.simulate_p1`)中的接线状态,三档归类 + 逐字段
> 一行。用途:新字段的「三消费面」检查(策略/遥测/sim 代理,ADR-0219
> 纪律)以此为底账;改 sim 接线时更新对应行。
>
> 对账:**已接 16(批前 13 + ADR-0271 接入 board + ADR-0276 接入
> node_type/streak[session 口径])+ 必须接线 12 +
> 观测冗余豁免 3 + 结构未建 5 = 36**。(任务书原锁 13+3+3+13=32 与
> 字段总数 36 不符,按实测归类对账;批前「已接 13」与任务书口径一致。)
>
> 优先级:P1 = 影响当期 sim A/B 结论有效性;P2 = 决策消费存在但当前
> 栈(LineStrategy)影响面小;P3 = 随依赖结构建设顺带接入。

## 一、已接线(16;sim 语义 = 生产语义或其 P1 域内真值)

| 字段 | sim 现状 | 生产语义 | 接线状态 | 优先级 |
|---|---|---|---|---|
| gold | 收入模型(基础+息+连胜+事件金)+逐笔花销 | OCR 金币数 | 已接(模型) | — |
| round_num | 轮循环 1-9 | 位面内轮次 OCR | 已接 | — |
| level | XP 循环升级(封顶 9) | 等级 OCR/XP 推导 | 已接(封顶 9=XP 表域) | — |
| plane | 恒 1(P1 模拟器域) | 位面 1/2/3 | 已接(域内真值) | — |
| hp | 节点结算轨迹 | 小队生命值 OCR | 已接(结算模型) | — |
| shop | _Pool 抽店(REFRESH_PROB;ADR-0272 全费) | 商店牌面 OCR/SIFT | 已接 | — |
| bench | 开局 4 张+买 append(含 3合1 merge,ADR-0276)+卖 pop+上阵 pop(ADR-0271) | 备战栏 SIFT 跟踪 | 已接(ADR-0276 起 merge 同源 `_merge_bench`;合并数入账本 sim.merges) | — |
| deployed | select_deployments 围栏输出,跨轮累积(ADR-0271) | bot 跟踪已上阵 | 已接 | — |
| board | deployed 主阵营聚合(ADR-0271) | OCR 左面板阵营计数 | 已接(ADR-0271) | — |
| equips | supply 3选1 采样+equip_allocation(r393) | 装备区 OCR | 已接(代理) | — |
| shop_refresh_cost | 恒默认 2(读 `st.shop_refresh_cost or 2`) | OCR 刷新金币数 | 已接(P1 无投资减免域内 2=真值;减免随 active_strategies 结构) | P3 |
| front_max | 默认 4(常量=机制真值) | 前排槽上限 | 已接(常量) | — |
| back_max | 默认 6(常量=机制真值) | 后排槽上限 | 已接(常量) | — |
| bench_full_flag | 恒 None → `bench_is_full()` 走 BENCH_CAPACITY=9 计数兜底 | OCR「备战席已满」警告 | 已接(兜底口径=生产 OCR 缺失路径同源;ADR-0271 后计数为真备战数) | — |

## 二、必须接线(12;决策消费存在,sim 未接)

| 字段 | sim 现状 | 生产语义(消费点) | 接线状态 | 优先级 |
|---|---|---|---|---|
| node_type | 决策前写 session.node_type_current(ADR-0276);state.node_type 仍不写 | 顶部标签 OCR;evaluate reward/boss 分、economy 利息门、boss 窗 | 已接(session 口径——策略消费读 session) | — |
| streak | 结算后写 session.last_streak(ADR-0276);state.streak 仍不写 | 结算连胜 OCR;evaluate 连胜分、economy win_reward | 已接(session 口径;收入侧早已有 streak_gold) | — |
| xp_progress | sim 本地 xp,未写 state | XP 条 OCR;economy 升级计划 _expected_level | 未接(数据已在手) | P1 |
| level_up_cost | LevelUp 硬编码扣 4 | OCR 购买经验金币数;xp_click_cost 真值优先 | 未接(sim 4=fallback 值) | P1 |
| selected_difficulty | 恒 ""(阈值回退 40) | 难度确认屏;effective_hp_threshold 职级表 | 未接(应按模拟难度设 A8) | P1 |
| board_next_tier | 恒 {} | 左面板 X/Y 的 Y(聚焦裁切 OCR);comp/progress 距档评分 | 未接(可由 FACTIONS 注册表派生) | P1 |
| refresh_probs | 恒 None(退基线表) | 商店开态概率条 OCR(r77 轮岗:每备战阶段随机翻倍一档);line_strategy _sample_cost 实读消费 | 未接(轮岗机制未采样——sim 恒用基线表,轮岗局供给结构失真) | P1 |
| active_strategies | 恒 [] | 已持有投资策略;economy 聚合/spend_mode/effect_ledger | 未接(投资策略事件层未建,见结构未建) | P2 |
| active_env | 恒 "" | 已选投资环境(简报);ENV_COMP_AFFINITY | 未接(环境选择层未建) | P2 |
| enemy_affixes | 恒 [] | 简报词缀;mechanics_fit | 未接(简报层未建) | P2 |
| plane_bosses | 恒 [] | 简报 3 位面 boss;boss_fit/select_comp | 未接(简报层未建) | P2 |
| dual_track_phase | 恒 False(LineStrategy 经 session 位消费) | default 栈写 state 位;plan/prefilter 消费 | 未接(LineStrategy 栈无 state 位消费,接线随栈归一) | P3 |
| focus_factions | 恒 None | update_target 写入(ADR-0209);evaluate 消费 | 未接(同上) | P3 |
| enemy_difficulty | 恒 None | 左上难度 OCR(常空);cw_events 选卡难度罚 | 未接(生产亦常空,决策安全降级) | P3 |

## 三、观测冗余豁免(3;保真位,sim 完美观测假设下无决策语义)

| 字段 | sim 现状 | 生产语义 | 接线状态 | 优先级 |
|---|---|---|---|---|
| hp_readable | 恒默认 True | hp 是否真读到(遥测保真;决策不用) | 豁免(sim 假设完美观测=终态,「识别噪声注入不做」) | — |
| gold_readable | 恒默认 True | gold 是否真读到(同上) | 豁免(同上) | — |
| board_readable | 恒默认 True | board 是否真读到(空 dict 双义标注) | 豁免(同上) | — |

## 四、结构未建(5;依赖的事件/画面层 sim 未建模)

| 字段 | sim 现状 | 生产语义 | 接线状态 | 优先级 |
|---|---|---|---|---|
| match_type | 恒 None | 模式选择屏(标准/超频博弈) | 未建(模式层) | P3 |
| plane_modifiers | 恒 [] | 位面特殊修正(如「战个痛快」) | 未建(位面修正层;P1 域内影响待核) | P3 |
| shop_locked | 恒 False | 商店锁定 | 未建(sim 无锁店行为,策略亦未用) | P3 |
| megastar_char | 恒 None | 巨星节点绑定角色(回写复盘) | 未建(巨星节点层) | P3 |
| partner_char | 恒 None | 伙伴节点选择(回写复盘) | 未建(伙伴节点层) | P3 |

## 已知接线缺口的影响面(判读边界)

- **3合1 全场合并已接入**(ADR-0276,生产 `_merge_bench` 同源;
  决策见 ADR-0276 §回归验证)。残余失真:末轮 bench 仍 ≥9 高占比
  (9.64 均值)——候选件合法持位形态,非副本堆积;滞留金 2.17×
  未收敛,残差定位到 P1 末段花金通道(P2 继承价值 sim 不可判),
  以 `sim_endgold_calib` 披露追踪。
- **轮岗未采样**(refresh_probs 行):投资环境轮岗每备战阶段随机
  翻倍一档费用概率,sim 恒基线表——供给分布与 D牌期望类结论的
  分布尾部失真。
- **boss 胜负面已校准**(ADR-0277):回退路径胜率=f(成型度),
  但幅度层「大胜 boss」未建模、rung≥3 无样本——hp 类 A/B 方向
  可信、点值 ±30% 浮动。
