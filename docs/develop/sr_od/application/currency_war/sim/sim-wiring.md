# sim 接线对照表（容器 GameState ↔ sim 游戏后端）

> as-built 底账（接线变更同步更新本表）：
> sim 后端 = `sim/cw_sim_backend.py::SimBackend`（驱动反转；世界本体 + 画面状态机，
> 职责与结构见 [sim-design.md](sim-design.md)）。后端不持本地工作帧，局状态 =
> 容器 `GameState` 单例（`kernel/cw_game_state.game_state_of(session)`）。
> 写容器一律走带渠道签名的写入口（渠道族封闭集 obs/logic_action/logic_hook，
> 写入口校验渠道族与 actor 已登记）；读容器走决策面公共读口族与 Field 直读。
> 本表逐域记录 sim 的产生面（哪个渠道、什么事件写）与读取面；用途：新域的
> 「三消费面」检查（策略/遥测/sim 代理三面同改纪律）以此为底账。
>
> 域全集与字段级规格权威版本 = `game_state/fields.md`；体系纪律（字段判据/写通道
> 三条各一/双端消费契约）= [sim-design.md](sim-design.md) §5–§6。
>
> sim 与实机的产生面按来源分三类：**世界分支**（sim 世界侧）= 后端/生成器独有（sim 世界事实）；
**动作分支** = 动作 op → 上报函数族，sim 与实机是同一段 op 代码（产生面天然同构，
本表不再逐域复述动作分支细节，只标「动作 op 同实机」）；**呈现分支** = 观察生成器
→ `cw_screen_report` 同名上报函数（与实机观察上报同一条写通道）。

## 一、写入渠道（封闭集三通道）

| 通道 | 适用面 | 载体 |
|---|---|---|
| obs（外部事件/世界真值） | 世界分支 + 呈现分支的状态事实 | ①后端直接 obs 写点（`sim/cw_sim_base.py::sim_evidence` 证据族，`sim:` 前缀）；②观察生成器产物经 `kernel/cw_screen_report/report_screen_<snake>_obs` 落容器（与实机观察上报同一写通道） |
| logic_action（动作应用） | 动作的字段转移全集，登记面 = `SHOP_PROJECTION_DOMAINS`（gold/bench/shop/xp/level/deployed/board/equips） | 动作 op 组装后直调 `kernel/cw_action_report/report_action_<snake>_param`（sim 与实机同一段 op 代码，零私有动作语义）；带随机的动作随机采样分支 rng 经 `install_backend` 注入（键形 `action/<tool>/<序号>`） |
| 节点推进 | 终结动作上报 | kernel `report_node_advance`（trigger 封闭集 {settle_confirm, supply_confirm}），sim 与实机同源 |

后端私有簿记（**不写容器**）：offer 去重集、overlay 队列、触发水位标志、随机流键坐标簿记、待授予候选下标、幂等守卫键、局结果面（`hp_trail`/`disclosures`）——实机不可观察的采样簿记按容器字段判据留后端私有（sim-design §5.1）。

## 二、逐域接线表

| 容器域 | sim 产生面 | sim 消费面 |
|---|---|---|
| node | 世界分支：进节点 obs 写 `NodeKey`（`node:p<位面>r<轮>`）+ kernel `observe_node_anchor` 节点序 id_mark 确认 | 读口 `plane_of`/`round_num_of`/`node_kind_of`；策略 plane-aware 分支 |
| gold | 世界分支：opening 初值 + `income:p<位面>r<轮>` 轮首收入（kernel `round_start_income` 三分支，含败补；扑满帧 = 收入递延至结算分支 `_resolve_battle`，败局无连胜成分、基数 = 窗口开快照）+ 位面开局环境金**分道**（`_apply_env_plane_start`：env ∈ `ENV_ORE_GRANTS` → 节点窗起点声明入队 + 过期清理，**金不直发**、由点击声明矿兑现入账；其余环境 → `_apply_env_plane_gold` 直发）；动作分支：扣减/回金同实机 | 读口 `gold_of`；策略消费面 |
| level | 世界分支：opening 初值 + `xp:node` 节点经验结转（`apply_node_xp`）；动作分支不写 level（升档等覆盖同实机） | 读口 `level_of`；抽牌概率档 |
| xp | 世界分支：opening 初值 + `xp:node` 入账；动作分支 LevelUpShop 写入同实机 | 策略追级消费（clicks_to_next_level） |
| hp | 世界分支：opening 实证档查表（无实证档报错索样本，`cw_opening_hp` 单一源）+ `battle:hp` 败局扣血 + 0hp 保底（`battle:hp_floor`）/局终 | hp 写入闸语义同实机（sim 写真值，无识别失真维） |
| streak | 世界分支：opening 0 + `streak:p<位面>r<轮>` 结算转移（带符号，`streak_signed_after`；扑满帧 = 胜 +1/败清零，2026-10-10 用户裁定） | 收入侧连胜金（派生读 `max(signed, 0)`，无第二账） |
| pending_loss | 世界分支：`loss:pending` 战斗结算失败分支写；轮首败局补偿支消费后清账（`clear_pending_loss`） | 轮首收入败局补偿支输入 |
| bench | 世界分支：opening 播种（M06 派生池首个写端）；动作分支：BuyCard 落位/合成连锁/SellBench 同实机 | 读口 `bench_view_slots_of`/`bench_entries_of`/`bench_units_of` + 派生 `bench_free_slots`/`bench_is_full` |
| deployed | 动作分支：上报族 deployed 视图整值替换（同实机,一次写 = 一次完整语义快照）；世界分支无整值写点 | 读口 `deployed_rows_of`/`deployed_count_of` 等 |
| board | 动作分支：v2 重算同实机；世界分支：后端板面真值观察（`SimBackend._observe_board_truth`，advance 步界等值零写） | 围栏判据/策略；overlay 判据计数真值（现役判据读 deployed 行，不读 board） |
| equips | 动作分支：穿戴/卖出同实机；世界分支：开箱选定走 kernel `gain_equipment`（producer = `SimBackend`，证据 `sim:box_pick`）+ 环境条件发放：结算分支连胜触发（`check_env_streak_grants`，`logic_sig('sim:env')`，库存尾追加 `write_logic_rand`，证据 `env_grant#<环境>#streak<阈值>`） | 装备分配消费面 |
| shop | 世界分支：`shop:deal` 节点切换自动全刷（kernel `sample_shop_deal` 单一源，整店锁跳过）；动作分支：刷新采样/买牌槽置换/CloseShop 离屏同实机 | 策略决策面（payload.cards 三态消费） |
| shop_locked | 世界分支：reset 初值恒 False（`shop_lock:v1_unlocked`；v1 无锁动作通道，字段先行 + 披露） | M05 全刷跳过判据 |
| diamond_count | 世界分支：opening 0 + `supply:diamond` 补给带钻选项落地 +1 + `env_diamond` 条件发放回调 +1（财富宝钻获得，observe；**带钻补给不采纳回调**——钻类型未建模，`_on_supply_picked` 零改动，supply 路径零行为变化） | 消费面候实机补档 |
| deploy_cap | 世界分支：opening 初值 + `env_diamond` 条件发放回调重算（= level + equips 中财富宝钻计数，拥有即算、可叠加，observe） | 读口 `max_units_of` 封顶域 |
| back_layout | 世界分支：`env_diamond` 条件发放回调 +1（min 9 封顶，现值缺读以机制基线 6 起算，observe）；读侧缺省回机制基线（读口缺省口径） | 读口 `back_capacity_of` |
| active_env / active_strategies | 动作分支：pick 族动作走获得链（`report_action_pick_invest_*` → kernel `cw_gain_chain`）同实机 | 经济聚合（kernel `aggregate_economy`）消费 |
| spheres | 呈现分支：节点窗起点备战档呈现（`_present_node_screen`，evidence `ores:p<位面>r<轮>`）——奖励节点面板矿（`reward_ore_points`）+ 位面开局声明矿**同批合并**一次写（坐标 = 面板序续接，`_plane_start_declared_points`；色'金'占位见 §五）；子态 `PREP_SUB_ORE`（普通备战 pending 有当前位面条目时声明矿点单独呈现，子态同）；spheres 写一律过挂接入口 `report_spheres_observed`（非矿备战空读照写 count=0 亦过入口，清理残留矿身份） | 采晶矿动作输入 |
| ore_rewards | 世界分支：挂接入口生成写（`sim:ores` logic_sig；声明金先占席 + 其余逐矿采样，`cw_ore_reward.generate_ore_rewards`——sim 采样即世界真值）；动作分支：点击兑现摘除（`ore_reward_detach`）同实机 | 策略禁读（随机态域）；点击兑现读（collect_ore 上报） |
| ore_declared_pending / ore_declared_done | 世界分支：节点窗起点声明入队电平检查（`check_ore_declared_level`，`sim:env`，与 `discharge_due_item_grants` 同组同窗）+ 挂接入口生成消费（pending 移除 + done 追加）+ 位面过渡过期清理（evidence `ore_declared_expired#p<old>`） | 入队/消费幂等守卫（pending+done 双查，跨环单发）；出队供生成 |
| env_grants_done | 世界分支：结算分支 streak observe 后条件发放触发（`check_env_streak_grants`，接线点 = 连胜真值已落账；`logic_sig('sim:env')`）达标的发放两笔相邻 logic 写第二笔（发放刻追加，局内恒存随快照存续） | 发放幂等守卫（已发不重发）；恢复局快照含 done 不重发 |
| encounter / supply / invest_env / invest_strategy / box 各 opts 槽 | 呈现分支：生成器回读呈现写点（后端节点事件件供给候选）经同名 report 落容器 | pick 族决策入口容器零参读 |
| plane_bosses / enemy_affixes / enemy_difficulty / game_mode / selected_difficulty | 世界分支：reset 采样（boss 名单/词缀）与局级输入申报（`opening` 事件）；呈现分支：简报档生成器覆写（同值幂等） | 敌人侧上下文消费 |
| 流程面域（chosen_* / event_overlay / substate 等；prev_screen / current_screen = `_announce_screen` 容器广播（值级豁免结算/大厅屏；obs_sig mode=synthesized、evidence `screen:<值>`——兑现本行原「同实机」申报；`update_screen_after_operation` 为框架路由簿记非容器写入，两不相涉） | 动作分支/呈现分支同实机（pick 动作上报写 chosen；生成器产 `PrepObservation` 控制信号） | 决策面零参读；prev/current 供复盘渲染切章 |

## 三、读口族（值读单一源）

kernel 决策面公共读口族（kernel/cw_game_state.py）：`plane_of` /
`round_num_of` / `node_kind_of` / `gold_of` / `level_of` /
`deployed_rows_of` / `bench_view_slots_of` / `bench_entries_of` /
`bench_units_of` / `back_capacity_of` / `deployed_count_of` /
`front_count_of` / `back_count_of` / `max_units_of` + 席位派生判定
`bench_free_slots` / `bench_is_full`。
读口负责缺省形态归一（未观察域按各读口 docstring 的缺省口径，如
gold 未读 = 0、back_layout 未读 = 机制基线 6），禁消费点自写兜底造成
第二源；后端在此之上另有 Field 直读（gs.shop.value/gs.equips.value 等）。

表示申报：阵营不入容器——Unit 只存 char_id，阵营经角色注册表派生
（game_state/fields.md §3.2.3）；后端围栏记账（巨星评估器计数等）用的
阵营计数在本地由槽表现算，容器 board 域写经重算单一源，细节归代码注释。

## 四、保真标记（容器语义吸收）

旧帧 `*_readable`/`*_trusted` 保真标记族不入容器：容器语义
「None = 不可读，禁兜底假值」天然承载可读性（gold=None 即不可读，
level 直写即真值）。sim 无识别失真面，不产生失读值；生成器产物的
readable/trusted 标记恒按真值填（`cw_sim_obs_gen.py::gen_shop`），消费端
口径归 report 写端。

## 五、sim 未接域与未建模面（判读申报面）

| 域/面 | sim 现状 | 判读影响 |
|---|---|---|
| level_up_cost | 不写（实机 OCR 真值域）；花费载体 = 动作 cost（策略侧 xp_click_cost 真值优先），sim 容器无真值 → 恒落兜底常量 | 花费敏感结论失真申报在案 |
| 节点屏刷新剩余呈现 | 呈现分支诚实缺位为主（环境逐卡刷新剩余/遭遇刷新剩余等生成器产缺位值，report 按「缺不写」防御语义跳写；补给刷新剩余由呈现写点给初值、刷新动作分支同实机递减） | 刷新类决策域以代码当期实现为准逐键判读 |
| 位面开局声明矿呈现面 | 色档（现按'金'占位）与「晶矿自动开启与否」均未实采，sim 按「呈现可点」建模（点击兑现入账）；面板矿内容分布同属未校准面（披露单一源 = kernel `cw_ore_reward.ORE_ASSUMPTION_KEYS`，本表不双源） | 披露键 = `ORE_PLANE_START_PENDING`，实机首遇校；若实机为自动开启（矿永不出现），声明条目留至位面过渡被过期清理即终态，机制面零污染 |
| 战斗随机输出面 / 扣血分量 / P3 / overlay 余族 / 词缀张数分布等 | 未建模申报清单单一源 = [sim-design.md](sim-design.md) §8.2（本表不复写） | 逐键披露挡外推 |

## 六、装配与声明喂入

装配（`sim/cw_sim_backend.py::install_backend`）= 端口槽 + 动作分支 rng
提供槽两槽；卸载（`uninstall_backend`）幂等复位：

- **端口槽**：`cw_sim_ports.install_sim_backend`（进程内单装配）。转移类
  动作后果不经订阅通道——转移动作 op 自上报出口一行
  `cw_sim_ports.declare_world(outcome.world_decl)` 直喂（未装配 = no-op，
  实机零行为变化），后端 `SimBackend.advance` 按 `decl.trigger` 分派世界
  过程/画面呈现并按 `decl.next_screen` 等值对账（契约权威版本 =
  [sim-design.md](sim-design.md) §6.3；18 转移动作的声明终值 =
  [../flow/action_ops.md](../flow/action_ops.md) §4.8）。

不引发画面转移的世界变化不经订阅通道：overlay 判据 = kernel 值回调
（`kernel/cw_faction_callbacks.py`，deployed 逻辑写尾内联，sim/实机同源，
见 [sim-design.md](sim-design.md) §4.1）；板面真值观察 =
`SimBackend._observe_board_truth`（advance 步界，等值零写）。

## 羁绊口径分层（board 统计语义单一源声明）

羁绊计数（board / 板深 / rung / 档位）分三层，**逐层消费、不跨层引用**：

| 层 | 内容 | 消费方 | 状态 |
|---|---|---|---|
| L1 纯羁绊全集 | 角色标签：factions+flows+independent，开拓者按排归一 | board 语义、recipe 门、tier 计算、判读 | 两侧同源（实机 `obs/cw_observation.py::board_from_tracked` 与 kernel `cw_bond_equips._recount_board`/`unit_bond_tags` 单一源标签；后端板面基座与巨星评估器消费同源重算） |
| L2 +装备羁绊贡献 | L1 + 星徽「加入【X】」/卡带「计数+1」（净效果无条件 +1） | board_from_tracked（实机）、Unit.equips（sim 同款字段）、win_features faction_counts | 落地（equips 消费链通，穿戴/获得动作分支同实机回写） |
| L3 全战力 | L2 + 装备 props 强度 + 投资策略/环境效果 + 羁绊档位效果数值 | 战力模型特征面 | 未建（需求件 = sim-power-model.md） |
