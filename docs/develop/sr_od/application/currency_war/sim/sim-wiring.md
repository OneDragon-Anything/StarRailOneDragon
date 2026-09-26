# sim 接线对照表（容器 GameState ↔ sim 游戏后端）

> as-built 底账（接线变更同步更新本表）：
> sim 后端 = `sim/cw_sim_backend.py::SimBackend`（驱动反转；世界本体 + 画面状态机，
> 职责与结构见 [sim-design.md](sim-design.md)）。后端不持本地工作帧，局状态 =
> 容器 `GameState` 单例（`kernel/cw_game_state.game_state_of(session)`）。
> 写容器一律走带渠道签名的写入口（渠道族封闭集 obs/logic_action/logic_hook，
> 写入口校验渠道族与 actor 在册）；读容器走决策面公共读口族与 Field 直读。
> 本表逐域记录 sim 的产生面（哪个渠道、什么事件写）与读取面；用途：新域的
> 「三消费面」检查（策略/遥测/sim 代理三面同改纪律）以此为底账。
>
> 域全集与字段级规格正本 = `game_state/fields.md`；体系纪律（字段判据/写通道
> 三条各一/双端消费契约）= [sim-design.md](sim-design.md) §5–§6。
>
> sim 与实机的产生面按腿分三类：**世界腿** = 后端/生成器独有（sim 世界事实）；
**动作腿** = 动作 op → 上报函数族，sim 与实机是同一段 op 代码（产生面天然同构，
本表不再逐域复述动作腿细节，只标「动作 op 同实机」）；**呈现腿** = 观察生成器
→ `cw_screen_report` 同名上报函数（与实机观察上报同一条写通道）。

## 一、写入渠道（封闭集三通道）

| 通道 | 辖面 | 载体 |
|---|---|---|
| obs（外部事件/世界真值） | 世界腿 + 呈现腿的状态事实 | ①后端直接 obs 写点（`sim/cw_sim_base.py::sim_evidence` 证据族，`sim:` 前缀）；②观察生成器产物经 `kernel/cw_screen_report/report_screen_<snake>_obs` 落容器（与实机观察上报同一写通道） |
| logic_action（动作应用） | 动作的字段转移全集，登记面 = `SHOP_PROJECTION_DOMAINS`（gold/bench/shop/xp/level/front_row/back_row/board/equips） | 动作 op 组装后直调 `kernel/cw_action_report/report_action_<snake>_param`（sim 与实机同一段 op 代码，零私有动作语义）；带随机的动作采样腿 rng 经 `install_backend` 注入（键形 `action/<tool>/<序号>`） |
| 节点推进 | 终结动作上报 | kernel `report_node_advance`（trigger 封闭集 {settle_confirm, supply_confirm}），sim 与实机同源 |

后端私有簿记（**不写容器**）：offer 去重集、overlay 队列、触发水位标志、随机流键坐标簿记、待授予候选下标、幂等守卫键、局结果面（`hp_trail`/`disclosures`）——实机不可观察的采样簿记按容器字段判据留后端私有（sim-design §5.1）。

## 二、逐域接线表

| 容器域 | sim 产生面 | sim 消费面 |
|---|---|---|
| node | 世界腿：进节点 obs 写 `NodeKey`（`node:p<位面>r<轮>`）+ kernel `observe_node_anchor` 节点序锚定 | 读口 `plane_of`/`round_num_of`/`node_kind_of`；策略 plane-aware 分支 |
| gold | 世界腿：opening 初值 + `income:p<位面>r<轮>` 轮首收入（kernel `round_start_income` 三分支，含败补）+ 位面开局环境金；动作腿：扣减/回金同实机 | 读口 `gold_of`；策略消费面 |
| level | 世界腿：opening 初值 + `xp:node` 节点经验结转（`apply_node_xp`）；动作腿不写 level（升档等覆盖同实机） | 读口 `level_of`；抽牌概率档 |
| xp | 世界腿：opening 初值 + `xp:node` 入账；动作腿 LevelUpShop 腿同实机 | 策略追级消费（clicks_to_next_level） |
| hp | 世界腿：opening 实证档查表（无实证档报错索样本，`cw_opening_hp` 单一源）+ `battle:hp` 败局扣血 + 0hp 保底（`battle:hp_floor`）/局终 | hp 写入闸语义同实机（sim 写真值，无识别失真维） |
| streak | 世界腿：opening 0 + `streak:p<位面>r<轮>` 结算转移（带符号，`streak_signed_after`） | 收入侧连胜金（派生读 `max(signed, 0)`，无第二账） |
| pending_loss | 世界腿：`loss:pending` 战斗结算失败腿写；轮首败补支消费后清账（`clear_pending_loss`） | 轮首收入 U04 败补支输入 |
| bench | 世界腿：opening 播种（M06 派生池首个写端）；动作腿：BuyCard 落位/合成连锁/SellBench 同实机 | 读口 `bench_view_slots_of`/`bench_entries_of`/`bench_units_of` + 派生 `bench_free_slots`/`bench_is_full` |
| front_row / back_row | 动作腿：上报族按载荷落位直写两行（同实机）；世界腿无整行写点 | 读口 `deployed_rows_of`/`deployed_count_of` 等 |
| board | 动作腿：v2 腿重算同实机；世界腿：后端板面真值观察（`SimBackend._observe_board_truth`，advance 步界等值零写） | 围栏判据/策略；overlay 判据计数真值（现役判据读 deployed 行，不读 board） |
| equips | 动作腿：穿戴/卖出同实机；世界腿：开箱选定走 kernel `gain_equipment`（producer = `SimBackend`，证据 `sim:box_pick`） | 装备分配消费面 |
| shop | 世界腿：`shop:deal` 节点切换自动全刷（kernel `sample_shop_deal` 单一源，整店锁跳过）；动作腿：刷新采样/买牌槽置换/CloseShop 离屏同实机 | 策略决策面（payload.cards 三态消费） |
| shop_locked | 世界腿：reset 初值恒 False（`shop_lock:v1_unlocked`；v1 无锁动作通道，字段先行 + 披露） | M05 全刷跳过判据 |
| diamond_count | 世界腿：opening 0 + `supply:diamond` 补给带钻选项落地 +1 | 消费面候实机补档 |
| deploy_cap | 世界腿：opening 初值；宝钻扩展通道未建模（宝钻只增不减的 cap 增长面候补档） | 读口 `max_units_of` 封顶域 |
| back_layout | sim 不写（宝钻扩展通道未建模）；读侧缺省回机制基线（读口缺省口径） | 读口 `back_capacity_of` |
| active_env / active_strategies | 动作腿：pick 族动作走获得链（`report_action_pick_invest_*` → kernel `cw_gain_chain`）同实机 | 经济聚合（kernel `aggregate_economy`）消费 |
| spheres | 世界腿：`ores:p<位面>r<轮>` 奖励节点晶矿面板（`reward_ore_points` 生成） | 采晶矿动作输入 |
| encounter / supply / invest_env / invest_strategy / box 各 opts 槽 | 呈现腿：生成器回读呈现写点（后端节点事件件供给候选）经同名 report 落容器 | pick 族决策入口容器零参读 |
| plane_bosses / enemy_affixes / enemy_difficulty / game_mode / selected_difficulty | 世界腿：reset 采样（boss 名单/词缀）与局级输入申报（`opening` 事件）；呈现腿：简报档生成器覆写（同值幂等） | 敌人侧上下文消费 |
| 流程面域（chosen_* / event_overlay / substate / prev_screen / current_screen 等） | 动作腿/呈现腿同实机（pick 动作上报写 chosen；生成器产 `PrepObservation` 控制信号；screen 簿记走 `update_screen_after_operation` 同实机） | 决策面零参读 |

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

## 四、保真位面（容器语义吸收）

旧帧 `*_readable`/`*_trusted` 保真位族不入容器：容器语义
「None = 不可读，禁兜底假值」天然承载可读性（gold=None 即不可读，
level 直写即真值）。sim 无识别失真面，不产生失读值；生成器产物的
readable/trusted 位恒按真值填（`cw_sim_obs_gen.py::gen_shop`），消费端
口径归 report 写端。

## 五、sim 未接域与未建模面（判读申报面）

| 域/面 | sim 现状 | 判读影响 |
|---|---|---|
| level_up_cost | 不写（实机 OCR 真值域）；花费载体 = 动作 cost（策略侧 xp_click_cost 真值优先），sim 容器无真值 → 恒落兜底常量 | 花费敏感结论失真申报在案 |
| 宝钻扩展通道（back_layout 增长 / deploy_cap 增长） | 不建模（opening 基线之外无写点） | 宝钻敏感面零变化 |
| 节点屏刷新剩余呈现 | 呈现腿诚实缺位为主（环境逐卡刷新剩余/遭遇刷新剩余等生成器产缺位值，report 按「缺不写」防御语义跳写；补给刷新剩余由呈现写点给初值、刷新动作腿同实机递减） | 刷新类决策域以代码当期实现为准逐键判读 |
| 战斗随机输出面 / 扣血分量 / P3 / overlay 余族 / 词缀张数分布等 | 未建模申报清单单一源 = [sim-design.md](sim-design.md) §8.2（本表不复写） | 逐键披露挡外推 |

## 六、装配与声明喂入

装配（`sim/cw_sim_backend.py::install_backend`）= 端口槽 + 动作腿 rng
提供槽两槽；卸载（`uninstall_backend`）幂等复位：

- **端口槽**：`cw_sim_ports.install_sim_backend`（进程内单装配）。转移类
  动作后果不经订阅通道——转移动作 op 自上报出口一行
  `cw_sim_ports.declare_world(outcome.world_decl)` 直喂（未装配 = no-op，
  实机零行为变化），后端 `SimBackend.advance` 按 `decl.trigger` 分派世界
  过程/画面呈现并按 `decl.next_screen` 等值对账（契约正本 =
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
| L2 +装备羁绊贡献 | L1 + 星徽「加入【X】」/卡带「计数+1」（净效果无条件 +1） | board_from_tracked（实机）、Unit.equips（sim 同款字段）、win_features faction_counts | 落地（equips 消费链通，穿戴/获得动作腿同实机回写） |
| L3 全战力 | L2 + 装备 props 强度 + 投资策略/环境效果 + 羁绊档位效果数值 | 战力模型特征面 | 未建（需求件 = sim-power-model.md） |
