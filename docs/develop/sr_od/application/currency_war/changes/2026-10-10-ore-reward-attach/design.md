# 晶矿奖励附着通道 迭代设计(总纲)

## 0. 元信息

- 迭代目标:源迭代 `.debug/progress/2026-09-23-invest-effects-calc` T-4(增发货币)机制接入外溢。用户裁定(2026-10-10):**矿进入世界时生成附着奖励(声明源优先占用、归属随机分配),点击统一兑现;所有矿奖励一律经随机态通道进 GameState;策略层禁读附着值**。
- 状态:定稿
- 文档清单:
  - details/ore-reward-channel.md —— 声明注册表、共享生成函数、GameState 附着域、挂接入口与声明入队/过期
  - details/ore-click-consume.md —— collect_ore 上报兑现改造、缺项兜底、策略禁读契约、投影审计与测试迁移
  - details/ore-sim-plane-start.md —— sim 位面开局声明矿呈现、直发金通道绕行、rng 键与占位退役

## 1. 问题与动机

- 现状症状:
  1. 晶矿奖励在**点击时**内联掷骰:`report_action_collect_ore_param` 每点调 `roll_ore_reward`(kernel/cw_action_report/collect_ore.py `reward = roll_ore_reward(roll_rng, int(level))`);矿数据(`OreSight`)只载存在性(色/坐标/半径,cw_game_state `class OreSight`)。
  2. 固定内容晶矿无法表达:增发货币「第一/二/三位面开始时,获得一个 6/8/12 金币的晶矿」(data/cw_invest_data.py `PlazaPortal(id='103')`)——点击时采样会替它掷三选一,sim 里世界真值直接错(该给 6 金的矿掷出 1-5 金/装备/角色)。
  3. sim 对增发货币按「位面开局直发金」建模(sim/cw_sim_backend.py `_apply_env_plane_gold`),与「晶矿」载体脱钩;live 侧经济通道挂「晶矿自动开启」未实采假设(strategies/impl/mandate_v1/env_economy.py `ENV_ECONOMY_PENDING_VERIFICATION['增发货币晶矿自动开启']`)。
- 根因归层:**语义层**。奖励的确定时点被建模在「点击」环节,而矿内容的可用真值时点在「矿进入世界」;且「声明内容矿」与「随机内容矿」缺一条统一的内容通道。
- 解决到哪:矿进入世界时生成附着奖励(声明优先占席、归属 rng 分配、其余采样),点击统一兑现;sim/live 同一生成函数、同一随机态写径。
- 明确不解决:
  - 位面开局矿的**呈现面**与**自动开启与否**(未实采;**新增披露键 `ore_plane_start_pending` 落 3.3**,实机首遇校——API 裁定 docs/game/currency_war/research/invest_effects.md §5:desc 未写明的不主动实机查);
  - 战技点契约「打开 N 个晶矿」计数消费(源迭代 T-29 辖;本通道下声明矿开矿自然计入点击,无额外工作);
  - 策略侧对附着奖励的估值/决策消费(2026-09-23 用户裁定:策略侧出局);
  - `roll_ore_reward` 临时口径 v0 的参数校准(`ORE_ASSUMPTION_KEYS` 原状,采集校准另批)。

## 2. 方案

系统级变化(读一遍知全貌):

1. **GameState 新增三域**:`ore_rewards`(随机态;键 = 矿坐标身份 `'x,y'`,值 = `OreReward` 附着奖励)、`ore_declared_pending`(逻辑态;声明待兑现队列,元素 (env, plane, gold))与 `ore_declared_done`(逻辑态;已消费标记 (env, plane),幂等第二腿)。
2. **kernel 新增声明注册表与生成函数**:`ENV_ORE_GRANTS`(环境 → 各位面声明金额;增发货币 `(6,8,12)`,构建校验与 `ENV_ECONOMY.gold_per_plane_start` 逐位同值);共享生成函数 `generate_ore_rewards`:新矿批 → 待兑现声明**先占一席**(占哪个矿 rng 掷——归属不可观察)、其余逐矿采样 → 全部经 `write_logic_rand` 写入。
3. **spheres 写端统一过挂接入口** `report_spheres_observed`(kernel/cw_ore_channel.py,live 与 sim 共用):写后按**容差配对**判定身份——配对命中 = 同身份继承附着(键重挂,不重掷)、无附着现役身份 = 生成附着、未配对消失 = 清洗;声明消费/过期随入口。声明入队 = **电平触发单一规则**(live = 每个 heavy 帧 `observe_full` 回执后、spheres 写前检查:`env ∈ ENV_ORE_GRANTS` ∧ (env,plane) ∉ pending ∧ ∉ done → 入队——节点域 plane 写点在 `observe_full` 漗斗内,无「锚定前旧值」可用;无边沿检测、无 op 成员记忆,跨环由 pending+done 双守卫闭合(守卫状态住 GameState),恢复局两形态(离线回放 done 随快照存续 / live 接管局 active_env 恒空零多发)各自闭合;**入队必须先于同帧 spheres 写**,承载性次序);live 接线规约见 ore-reward-channel §5。
4. **点击上报改兑现**:`report_action_collect_ore_param` 按坐标身份取附着值直接应用(内联掷骰退役为缺项兜底,证据标注 `ore_reward_attach_missing`);开成即移除该身份附着。
5. **sim 接线**:`_apply_env_plane_gold` 对 `ENV_ORE_GRANTS` 命中环境绕行(直发金退役为非矿形态预留通道);位面开局备战面板生成 1 个声明矿;奖励节点面板同样在生成时附着(「本面板只载有哪些晶矿」的旧口径废止)。
6. **策略层禁读** `ore_rewards`(随机态域天然落消费门不可信侧 + 挑选 kernel 文档契约)。

跨详设接口契约(总纲定死,各详设不得另行演化):

- **矿身份 = 轨迹,不是精确坐标**——附着键 = 该身份**最新一次观察的 (x, y)** 整数元组,身份连续性由挂接入口的**容差配对继承**判定:消失 ↔ 新现在持存容差(12px,单一源 = `cw_identity_obs` 的持存容差常量,公开化供 kernel 函数内 lazy 引用)内一一配对 = 同身份,继承附着、不重掷(依据:Hough 圆心跨帧抖动是常态——观察链两帧持存本身就是 ±12px/±6 容差过滤器 `filter_persistent_ores`,精确键会在抖动下换键、声明金被清洗丢失)。生成、继承重挂、点击兑现、清理全部经挂接入口单一判定;点击载荷求交仍按当帧坐标(collect_ore.py `by_xy` 同键制)。
- **附着值类型 = `OreReward`(kernel/cw_ore_reward.py,唯一)**;`ore_rewards` 值形 = dict,键 `'x,y'` 字符串(JSON 安全;先例 = `occupied_equips` 键 `'front:1'`,cw_game_state 观察 写端)。
- **生成函数单一入口** `generate_ore_rewards(declared_gold: tuple[int, ...], coords: tuple[tuple[int, int], ...], level: int, rng: random.Random) -> dict[str, OreReward]`;live/sim 共用,禁第二实现。
- **rng 解析口** = `action_sampling_rng('ore_reward_gen', None)`(cw_action_report/__init__.py `action_sampling_rng`):live 未装配回退现掷(实机未播种口径先例);sim 装配方供键,确定性由写序担保(先例 = `provided_action_rng` 键序装配)。
- **注册表** `ENV_ORE_GRANTS: dict[str, tuple[int, ...]]`(键 = 环境规范名,值 = 位面 1-3 声明金额);构建校验:键 ⊆ `INVESTMENT_ENVS`;同键 `ENV_ECONOMY.gold_per_plane_start` 非空时**长度相等且逐位同值**。
- **写通道铁律**:附着值一律 `write_logic_rand`(用户裁定 2026-10-10:归属不可知 ⇒ 一切矿奖励是随机态,无确定性写路径);`spheres` 本体留观察通道(位置/颜色 = 画面真值),附着值**不进 `OreSight`**(通道纪律依据见 details/ore-reward-channel.md 问题与约束)。
