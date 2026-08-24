# sim 接线对照表(GameState ↔ cw_sim)

> as-built 存量清查(2026-08-24,批 B 件3):GameState 36 个字段在
> P1 模拟器(`cw_sim.simulate_p1`)中的接线状态,三档归类 + 逐字段
> 一行。用途:新字段的「三消费面」检查(策略/遥测/sim 代理,ADR-0219
> 纪律)以此为底账;改 sim 接线时更新对应行。
>
> 对账:**已接 18(批前 13 + ADR-0271 接入 board + ADR-0276 接入
> node_type/streak[session 口径]+ ADR-0286 接入 xp_progress/
> refresh_probs/deploy_cap[宝钻通道参数化,默认频率 0]+ 契约包 C1
> 接入 action_log[动作 v2 账本])+ 必须接线 12 + 观测冗余豁免 4 +
> 结构未建 5 = 39**。(任务书原锁 13+3+3+13=32 与字段总数不符,按实测
> 归类对账;批前「已接 13」与任务书口径一致;ADR-0286 新增 deploy_cap
> 字段 → 总数 36→37;批㉖ F1 新增 enemy_difficulty_live、契约包 C1
> 新增 action_log → 37→39。)
>
> 优先级:P1 = 影响当期 sim A/B 结论有效性;P2 = 决策消费存在但当前
> 栈(LineStrategy)影响面小;P3 = 随依赖结构建设顺带接入。

## 一、已接线(18;sim 语义 = 生产语义或其 P1 域内真值)

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
| board | deployed 羁绊全集聚合(ADR-0312:主阵营单标签口径已废;per-unit 单一源 = `cw_bond_equips.unit_bond_tags`,L1+L2 含星徽装备贡献;DeployMove 增量、动作 v2 全量重算) | OCR 左面板阵营计数 / board_from_tracked 计算(同口径) | 已接(ADR-0312 全集口径) | — |
| equips | supply 3选1 采样(池=注册表过滤后的装备名,ADR-0294 件2)+equip_allocation(r393)+分配结果回写 BenchChar.equips(ADR-0312,星徽羁绊贡献进 board);带钻是词缀元数据→披露计数 `phantom_supply_picks`,不进 owned 池 | 装备区 OCR;tracked_deployed[].equips(deploy_bench 读回) | 已接(代理) | — |
| shop_refresh_cost | 恒默认 2(读 `st.shop_refresh_cost or 2`) | OCR 刷新金币数 | 已接(P1 无投资减免域内 2=真值;减免随 active_strategies 结构) | P3 |
| front_max | 默认 4(常量=机制真值) | 前排槽上限 | 已接(常量) | — |
| back_max | 默认 6(常量=机制真值) | 后排槽上限 | 已接(常量) | — |
| bench_full_flag | 恒 None → `bench_is_full()` 走 BENCH_CAPACITY=9 计数兜底 | OCR「备战席已满」警告 | 已接(兜底口径=生产 OCR 缺失路径同源;ADR-0271 后计数为真备战数) | — |
| xp_progress | 买牌/买经验累 XP_PER_BUY,轮末升级按 XP_TO_NEXT_LEVEL 清零结转(ADR-0286) | XP 条 OCR;economy clicks_to_next_level/追级门 | 已接(ADR-0286 真值化——旧恒 None,clicks_to_next_level 恒按 0 进度估) | — |
| refresh_probs | 每备战期 20%(ROTATION_CHANCE)掷轮岗,随机可翻倍档 ×2 与 REFRESH_PROB 组合(cw_shop_odds.rotation_probs);draw_shop(开态+每次刷新)消费轮岗后表(ADR-0286) | 商店开态概率条 OCR(r77 轮岗:每备战阶段随机翻倍一档);line_strategy _sample_cost 实读消费 | 已接(ADR-0286 轮岗建模——lv1-3 纯 1 费无可翻倍档恒 None,与生产同态) | — |
| deploy_cap | 宝钻通道参数化 diamond_cap_prob(每备战期以此概率 +1 宝钻,cap=level+宝钻数;默认 0 = 通道建好不注入,与旧树同态) | read_deploy_cap_debounced 防抖真值(cap<level/\|cap−level\|>2 重读一帧仍异拒 None);max_units() 优先消费、level 兜底 | 已接(通道;频率待实机语料统计后标定,ADR-0286) | P3 |
| action_log | cw_state.simulate 对动作 v2(SellDeployed/SwapDeploy/CompTransaction)逐条写 applied/rejected 记录;cw_sim 转录进轮账本 actions、checks(comp_tx_atomicity)消费 | 生产侧无对应(账本走遥测 actions 流;拒绝可见性 invariant 的 sim 侧载体) | 已接(契约包 C1 步2;策略不读——决策禁依赖账本) | — |

## 二、必须接线(12;决策消费存在,sim 未接)

| 字段 | sim 现状 | 生产语义(消费点) | 接线状态 | 优先级 |
|---|---|---|---|---|
| node_type | 决策前写 session.node_type_current(ADR-0276);state.node_type 仍不写 | 顶部标签 OCR;evaluate reward/boss 分、economy 利息门、boss 窗 | 已接(session 口径——策略消费读 session) | — |
| streak | 结算后写 session.last_streak(ADR-0276);state.streak 仍不写 | 结算连胜 OCR;evaluate 连胜分、economy win_reward | 已接(session 口径;收入侧早已有 streak_gold) | — |
| level_up_cost | LevelUp 硬编码扣 4 | OCR 购买经验金币数;xp_click_cost 真值优先 | 未接(sim 4=fallback 值) | P1 |
| selected_difficulty | 恒 ""(阈值回退 40) | 难度确认屏;effective_hp_threshold 职级表 | 未接(应按模拟难度设 A8) | P1 |
| board_next_tier | 恒 {} | 左面板 X/Y 的 Y(聚焦裁切 OCR);comp/progress 距档评分 | 未接(可由 FACTIONS 注册表派生) | P1 |
| active_strategies | 恒 [] | 已持有投资策略;economy 聚合/spend_mode/effect_ledger | 未接(投资策略事件层未建,见结构未建) | P2 |
| active_env | 恒 "" | 已选投资环境(简报);ENV_COMP_AFFINITY | 未接(环境选择层未建) | P2 |
| enemy_affixes | 恒 [] | 简报词缀;mechanics_fit | 未接(简报层未建) | P2 |
| plane_bosses | 恒 [] | 简报 3 位面 boss;boss_fit/select_comp | 未接(简报层未建) | P2 |
| dual_track_phase | 恒 False(LineStrategy 经 session 位消费) | default 栈写 state 位;plan/prefilter 消费 | 未接(LineStrategy 栈无 state 位消费,接线随栈归一) | P3 |
| focus_factions | 恒 None | update_target 写入(ADR-0209);evaluate 消费 | 未接(同上) | P3 |
| enemy_difficulty | 恒 None | 左上难度 OCR(常空);cw_events 选卡难度罚 | 未接(生产亦常空,决策安全降级) | P3 |

## 三、观测冗余豁免(4;保真位,sim 完美观测假设下无决策语义)

| 字段 | sim 现状 | 生产语义 | 接线状态 | 优先级 |
|---|---|---|---|---|
| hp_readable | 恒默认 True | hp 是否真读到(遥测保真;决策不用) | 豁免(sim 假设完美观测=终态,「识别噪声注入不做」) | — |
| gold_readable | 恒默认 True | gold 是否真读到(同上) | 豁免(同上) | — |
| board_readable | 恒默认 True | board 是否真读到(空 dict 双义标注) | 豁免(同上) | — |
| enemy_difficulty_live | 恒默认 False | 难度值是否逐帧真读(批㉖ F1 保真位;判读过滤用,决策不用) | 豁免(sim 假设完美观测;生产亦仅判读侧消费) | — |

## 四、结构未建(5;依赖的事件/画面层 sim 未建模)

| 字段 | sim 现状 | 生产语义 | 接线状态 | 优先级 |
|---|---|---|---|---|
| match_type | 恒 None | 模式选择屏(标准/超频博弈) | 未建(模式层) | P3 |
| plane_modifiers | 恒 [] | 位面特殊修正(如「战个痛快」) | 未建(位面修正层;P1 域内影响待核) | P3 |
| shop_locked | 恒 False | 商店锁定 | 未建(sim 无锁店行为,策略亦未用) | P3 |
| megastar_char | 恒 None | 巨星节点绑定角色(回写复盘) | 未建(巨星节点层) | P3 |
| partner_char | 恒 None | 伙伴节点选择(回写复盘) | 未建(伙伴节点层) | P3 |

## 羁绊口径分层(ADR-0312;board 统计语义单一源声明)

羁绊计数(board / 板深 / rung / 档位)分三层,**逐层消费、不跨层引用**:

| 层 | 内容 | 消费方 | 状态 |
|---|---|---|---|
| L1 纯羁绊全集 | 角色标签:factions+flows+independent,开拓者按排归一 | board 语义、recipe 门、tier 计算、判读 | **三处一致**(实机 `board_from_tracked` / sim `_recount_board` / checks 镜像,per-unit 单一源 = `cw_bond_equips.unit_bond_tags`,ADR-0312 起) |
| L2 +装备羁绊贡献 | L1 + 星徽「加入【X】」/卡带「计数+1」(净效果无条件 +1) | board_from_tracked(实机)、GameState.equips→BenchChar.equips(sim 代理)、win_features faction_counts | **雏形落地**(ADR-0312:equips 消费链通,sim equip_allocation 回写) |
| L3 全战力 | L2 + 装备 props 强度 + 投资策略/环境效果 + 羁绊档位效果数值 | win_model 特征、power_table、结算校准层 | 未建(挂「语料积累后」,W49 裁决 4) |

判读边界:Δ池桶键(encounter/boss/reward/supply 深度桶)与池语料
同口径 = Σboard(L1+L2 全集,ADR-0312 v7);battle rung 输入
`_recount_board`。历史批次(≤ v6 池指纹)的板深/rung 数字与本版本
**不可裸串比**(桶语义变,跨版本对照须导出 JSON 快照重放)。

## 已知接线缺口的影响面(判读边界)

- **3合1 全场合并已接入**(ADR-0276,生产 `_merge_bench` 同源;
  决策见 ADR-0276 §回归验证)。残余失真:末轮 bench 仍 ≥9 高占比
  (9.64 均值)——候选件合法持位形态,非副本堆积;滞留金 2.17×
  未收敛,残差定位到 P1 末段花金通道(P2 继承价值 sim 不可判),
  以 `sim_endgold_calib` 披露追踪。
- **轮岗已建模**(ADR-0286):每备战期 20% 掷轮岗(随机可翻倍档 ×2,
  其余档重归一),draw_shop/_sample_cost 消费轮岗后表——对齐生产 20%
  帧率(批㉓ F4);lv1-3 纯 1 费无可翻倍档恒基线,与生产同态。
- **宝钻 cap 通道参数化、默认 0**(ADR-0286):cap=level+宝钻数的获取
  频率待实机语料统计(replay cap 键落地后可采),标定前 baseline 不注入。
- **boss 胜负面(回退层)= W31 实测阶梯**(ADR-0308):Δ池不可达
  时胜率 = ``node_win_p``(n=192,~0.05),不再随成型度 rung 变化;
  「大胜 boss」幅度未建模——hp 类 A/B 方向可信、点值 ±30% 浮动。
  主路径(Δ池)boss 深度桶采样不变。
