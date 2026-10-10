# sim 位面开局声明矿与接线(详设)

## 问题与约束

- sim 现状三处与本篇相关:
  1. 增发货币位面开局**直发金**:`_apply_env_plane_gold` 读 `env.economy.gold_per_plane_start` observe 写 gold(sim/cw_sim_backend.py `_begin_node_window` 节点窗起点调用);
  2. 奖励节点面板 `reward_ore_points()` 只载存在性(「本面板只载有哪些晶矿,内容采样走 kernel report_action_collect_ore_param」——本迭代后该口径废止);
  3. `REWARD_ORE_CONTENT_PLACEHOLDER` / `ORE_CONTENT_PENDING_U23` 内容占位披露。
- 接口契约引用(总纲 §2):挂接入口 `report_spheres_observed` 单一入口(含容差配对轨迹继承);rng 键 `'ore_reward_gen'`;生成即 sim 世界真值(两副面孔原则,值语义随通道统一)。
- 不辖 live 写端(ore-reward-channel §4/§5);不辖点击兑现(ore-click-consume)。

## 方案

### 1. 节点窗起点序(_begin_node_window)

- `_apply_env_plane_gold` 调用点改为分道:env ∈ `ENV_ORE_GRANTS` → **声明入队**(经 kernel 同一电平规则函数,守卫 = pending/done 双查——`_window_begun_ord` 窗口幂等降为冗余保险,沿留不删;写 = write_logic,**sig = `logic_sig('sim:env')`**(与 `discharge_due_item_grants` 同组同窗,沿 sim 现行 logic_action 族构造形态);依据 = kernel 确定效果直写 write_logic 先例(cw_exec_state 金腿 / cw_effect_inventory 退款腿));env ∉ ENV_ORE_GRANTS 且 `gold_per_plane_start` 非空 → 保留直发(通道留置,现无此形态环境);
- **位面过渡过期清理接线**:同一电平清理函数(pending/done 中 plane ≠ 当前 plane 的条目移除,evidence 留痕 `ore_declared_expired#p{old}`)——窗口起点调用,与入队同一改动点交付,归本阶段;
- 入队后位面开局矿呈现走 §2;金不再直发——**世界面**的金在点击兑现时入账(策略面估值消费 ENV_ECONOMY 数值不变,双源同值校验在构建期闭合)。

### 2. 位面开局矿呈现(_present_node_screen)

- 备战档呈现(battle/reward → SCREEN_PREP 分支)**均检查** `ore_declared_pending` 当前 plane 条目(无额外「首帧判定」状态——出队即消费,后续呈现自然无声明矿):有条目 → spheres 含 1 个声明矿点(色档 `'金'` 占位[披露键 `ore_plane_start_pending`:呈现色未实采],**半径 r = 10 与面板矿同**,points 四元组齐整);**坐标 = 面板序续接**——`reward_ore_points()` 点列为 i 从 1 起的 `(i*10, 10)`,声明矿点 = `(10*(N+1), 10)`(N = 同批面板点数;位面首节点为奖励节点时同批 8 面板矿 + 声明矿 = 第 9 点 (90,10),**禁独立从 1 起号**——同批撞键会被 `by_xy` 求交去重吞点);子态 `PREP_SUB_ORE`;
- 声明矿点与该节点自身面板锚点矿**同批合并**进一次 spheres 写——声明归属由生成函数 rng 掷(总纲裁定:归属不可知),批内不预分。

### 3. spheres 写端统一(spheres 写一律过挂接入口)

- 奖励节点分支(`reward_ore_points()`)与位面开局矿分支,写 spheres 一律改调 `report_spheres_observed`(obs_sig 沿 `obs_sig(group_id='sim:ores')`,hook_sig = `logic_sig('sim:ores')`,evidence 沿 `sim_evidence(f'ores:p{plane}r{r}')` 形态);
- 生成即附着:sim 里掷出的归属与内容 = 世界真值(两副面孔原则的生成侧);容差配对在 sim 为恒等(合成坐标恒稳),继承语义零触发;
- 非 ore 备战呈现(普通 battle 备战)spheres 空读照写 count=0 亦过入口(空批零生成、清理消失身份——上节点残留矿身份在此清理)。

### 4. rng 与确定性

- 键 `'ore_reward_gen'` 随 `action_sampling_rng('ore_reward_gen', None)` **首调自动生效**——装配方是泛型 `lambda tool`(cw_sim_backend 装配段),本阶段**零改动**;sim 呈现序确定 → 掷序确定(键序确定性责任在调用序,先例 = 现动作腿键);
- `test_cw_sim_seam.py` provider 装卸断言面扩 `'ore_reward_gen'` 键(现断言形态实存,沿其装卸用例扩)。

### 5. 占位退役与披露

- `REWARD_ORE_CONTENT_PLACEHOLDER` / `ORE_CONTENT_PENDING_U23` 删除(内容现在真实生成;分布参数未校准的披露由 `cw_ore_reward.ORE_ASSUMPTION_KEYS` 单一源承担,不双源);
- disclosures 面**新增** `ore_plane_start_pending`(位面开局矿呈现面/色档/自动开启未实采,实机首遇校——与 ore-reward-channel §5 同键,本迭代新增非在册)。

## 关键取舍

- **直发金通道删除 vs 留置**:选留置(ENV_ORE_GRANTS 命中即绕行)。未来环境若有非矿形态的位面开局金,通道复用;增发货币是现唯一用户,已迁声明矿。
- **位面开局矿单独子态 vs 复用 PREP_SUB_ORE**:复用。面板在场语义(「区域-奖励」面板有晶矿)与奖励节点一致,观察面/操作链零新增;呈现差异留披露键首遇校。
- **声明矿坐标独立号段 vs 面板序续接**:选续接。同批合并时唯一性由构造保证;独立号段在「面板矿数变化」时仍可能撞键,续接不撞。
