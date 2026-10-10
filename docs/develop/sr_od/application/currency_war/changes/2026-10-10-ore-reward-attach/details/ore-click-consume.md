# 点击兑现与策略契约(详设)

## 问题与约束

- 现点击链(collect_ore.py `report_action_collect_ore_param`):载荷 ∩ spheres 现值求交 → 席满守卫(该点时无空位 → 留矿不采)→ spheres 摘除(随机态写)→ **内联掷骰 `roll_ore_reward`** → 未抽中域标记 + 抽中域采样值写(金/装备/角色落位 + 3合1 连锁)。
- 本篇只改**奖励来源**(内联掷骰 → 附着值兑现);求交、席满守卫、写序、域标记、整批出参语义全部不动。
- 接口契约引用(总纲 §2):矿身份 = 容差配对轨迹,附着键 = 最新观察坐标 `'x,y'`;附着值类型 = `OreReward`;生成/继承在挂接入口(ore-reward-channel §4)。

## 方案

### 1. 兑现改造(report_action_collect_ore_param)

- 每开成一点:`reward = ore_rewards 现值.get('x,y')`:
  - **命中** → 直接应用该 `OreReward`(零掷骰——掷骰已前移到生成侧);
  - **缺项**(不变量破坏:挂接入口保证每现役身份有附着;写端竞态等罕见态)→ 兜底 `roll_ore_reward(roll_rng, level)`(沿现解析口),该点全部写行 evidence 前缀 `ore_reward_attach_missing#`;
- 开成后:该键从 `ore_rewards` 移除(随 spheres 摘除同点随机态写,evidence=`ore_reward_detach#ore{k}`);
- `level` 语义收窄:现「level None → 整批拒 `'level_unread'`」是为采样服务的;新语义 = **附着命中不需 level**(开局种子恒写 level=3,生产近乎不可达,语义收窄是保真不是主防御面);仅当存在缺项需兜底掷 ∧ level None → 该点跳过不采(矿留 spheres 不摘,与席满跳过同族),**证据通道 = `LogicOutcome.reason='ore_reward_attach_missing_level'`**(优先于 `ore_partial_open_skipped` 表达具体原因;零写跳过不落写行,reason 是唯一可断言通道)——下帧挂接入口补生成后再点;
- 整批出参 reason 集新增上述一条,其余(bench_full_no_open / ore_partial_open_skipped / spheres_unobserved / bench_unobserved / **no_intersection**(求交不动,现行为原样保留))不变。

### 2. 策略禁读契约

- 防线是**双层的**,不是机械强制:①`ore_rewards` 属随机态域 → `logic_rand_fields` 查询口与「消费前必须重观察」纪律把它落**不可信侧口径**(无机械读拦截,是纪律面);②文档契约(先例 = `cw_hp_policy.hp_readable` 消费门的口径声明方式)。sim 侧同样禁:策略代码 sim/live 共用,sim 读附着值 = 带 oracle 训练,行为不可迁移(总纲 §2 第 6 条)。
- 文档契约落点:
  - `cw_prep_actions.select_ore_clicks` docstring 增:「挑选仅消费色/半径(大优先);`ore_rewards` 附着值禁读——实机为随机猜测,读它 = oracle 泄漏」;
  - `cw_prep_actions` 模块头同申一行。

### 3. 投影审计(cw_projection_audit.py)

- 现晶矿随机金条目(`'晶矿随机金已改走逻辑随机态(collect_ore 采样直写…'`):写端申报改为「生成写 = ore_reward_attach(挂接入口,含 rekey 重挂),兑现写 = collect_ore 上报」;
- 晶矿视觉域 basis(「晶矿视觉域(§3.2.8,点击目标非席位居民),零逻辑写端」):spheres 域维持零**逻辑**写端(点击摘除是随机态写,非 write_logic——按现注释口径核对后如实改);新增 `ore_rewards` 域行:logic_rand 写端 = 挂接入口,读端 = collect_ore 兑现,策略禁读契约指针;**新增 `ore_declared_pending` / `ore_declared_done` 域行**:logic 写端 = 入队/消费/过期电平口(同族行先例 = `pending_item_grants`),值语义 = 卡文推算登记非观察投影,done = 消费标记(幂等第二腿)。

### 4. 测试迁移(sr-od-test)

- `test_cw_collect_ore_rand.py`:7 处 `monkeypatch.setattr(collect_ore_mod, 'roll_ore_reward', fake)`(现文件 :160/:186/:212/:237/:254/:280/:308)→ 改为**预置 `gs.ore_rewards` 域**(直接写附着值,monkeypatch 退位);新增断言:附着命中零掷骰(计数 roll 调用)、缺项兜底路径(evidence 前缀)、缺项∧level None 的 reason、`ore_reward_detach` 写序;
- `test_cw_ore_container.py` / `test_cw_unified_action_2a.py`:摘除断言补 ore_rewards 键移除断言;
- 既有 evidence 名断言(`proj_collect_ore_drop#ore1` 等)保持不变(写行 evidence 语义未动)。

## 关键取舍

- **缺项 = 响亮炸 vs 兜底掷**:选兜底 + 证据标注。动作链存活优先(先例 = 幻晶矿黑名单登记 best-effort 不阻塞采晶矿);「响亮炸」先例是采样错档(校准数据全废,危害面不同),此处缺项可恢复(下帧补生成),炸整批反而放大故障。
- **附着命中 ∧ level None 拒批 vs 放行**:放行。声明金兑现不需要 level;原 `'level_unread'` 整批拒是为角色采样服务的,随采样退役到兜底路径。
- **缺项∧level None 跳过的证据通道**:定 `LogicOutcome.reason`(机械可断言、测试面最小);备选 = 日志行/缺陷台账(弃:不可断言)。
