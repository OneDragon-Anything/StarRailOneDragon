# 容器开局种子底座与锚定闩(「未观察」根治批) 迭代设计(总纲)

## 0. 元信息

- 迭代目标:GameState 容器在冷建时以开局初值播种(随机态通道,观察可直接覆盖),配
  **锚定闩**统一「未锚定期」的写通道规则——消偿获得链迭代(gain-chain)裁定⑤的
  【待梳理标记】,根治「bench/equips 未观察 = bug 面」的留证现状。
- 用户裁定(2026-09-21,逐条):①种子方向——新局与接管局的容器字段开局即设具体初值,
  后续第一次观察直接写入、不停机;②通道 = 随机态(`write_logic_rand`),用随机态表达
  「未经观察验证的底座」;③种子数值:gold=0、deploy_cap=3(与 level 一致)、
  L3 升级所需经验=4、hp=80。
- 状态:草案(候对抗审;§2.2 的 B/C 类分诊为方案建议,随对抗审定稿)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

### 现状症状(锚 = 文件::位置,路径根 = `src/sr_od/application/currency_war/`)

1. **新局投资环境落地相,阵容/经济域结构性未观察**:对局链序 = 简报 → 投资环境 →
   投资策略 → 备战(`operations/cw_entry/cw_entry_start.py:435` 流程注);而
   `bench`/`front_row`/`back_row`/`equips` 的唯一观察锚定点 = 备战入口 heavy 观察
   (`operations/cw_screen/cw_screen_prep.py::_observe` heavy 段 → `observe_full` →
   `reconcile_tracking`);投资环境屏建档无阵容区(`assets/game_data/screen_info/
   currency_war_invest_env.yml` 仅标识/卡牌描述/确认/剩余次数四区)——阵容域在该时点
   **物理上不可观察**。选中 ENV_GIFTS 契约类环境(`kernel/cw_investments.py::ENV_GIFTS`)
   时,`gain_character` 必撞 bench=None → 零写 + `gain_chain_bench_unobserved` 缺陷行
   (`kernel/cw_gain_chain.py`:DEFECT_BENCH_UNOBSERVED 发射点),每局必发;链记账价值
   在窗口内恒为零(真值由首个备战 heavy 观察兜回,观察覆盖自愈)。
2. **接管局冷建全 None 窗口**:`establish_new_match` 冷建容器后、首个备战 heavy 观察
   完成前,全部字段 None(接管路径连简报/难度确认屏都不出现)。窗口短、闭合点明确,
   但与症状 1 同构。
3. **「未观察」判据散布**:全仓 Python 154 处「未观察/unobserved」消费点,处置形态
   四种并存(台账留证不停机 / 显式门+跳过+熔断 / fail-closed 留证响停 / 静默零写
   无留证),无单一判据源。

### 根因归层

**表示层**——「未知(未锚定)」被表示为值域 None,与「已观察下的空」同域不同义;
消费侧被迫各自补判别,守卫方向互不一致(有的保守关、有的默认满、有的响停)。

### 解决到哪 / 明确不解决

解决:A 类字段开局播种(阵容/经济域锚定前不再是 None)→ 这些域的「未观察」判据
整体消亡;锚定闩 + 通道规则让获得链在窗口内正常落账且首观察静默覆盖。

明确不解决(防外溢):

- B/C 类字段保持 None(§2.2 分诊——None 在这些字段上是设计语义或在册禁令);
- tracked 账机制(`tracked_books`/`tracked_account_observed`)不动——它是独立于
  容器种子的执行侧安全网;
- node 族的 None 元信号消费点不动(假局守卫/效果账本闸/首锚定门,node 族不种 = 零改动);
- sim 引擎的状态合成机制不动;遥测采集缺口(plane_modifiers/shop_locked 无 reader,
  telemetry-reading「已知缺口」在册)不动;
- tool-gain-report 迭代(在飞)的零写分支语义不回头改——其消费域(equips 等)在本批
  落地后自然不再出现 None(关系申报见 §2.8)。

## 2. 方案(完整设计)

### 2.1 总体结构

三件套:**①开局种子底座**(冷建口播种,A 类字段)→ **②锚定闩**(首次备战 heavy
锚定成功置位的粘性位)→ **③通道规则**(未锚定期间容器逻辑写一律走随机态)。
三者全部住 kernel(`kernel/cw_game_state.py` + `kernel/cw_reconcile.py` 置位点 +
`kernel/cw_gain_chain.py` 规则消费),op 层零改动。

### 2.2 字段分诊(容器 Field 全集三类;判据 = 「开局真值或首观察可覆盖」/「None 是设计语义」/「无观察源」)

**A 类——种**(种子值与依据逐行标注):

| 字段 | 种子值 | 依据 |
|---|---|---|
| `bench` | 空槽位 `BenchView`(9 空槽,capacity 9) | 用户裁定种子化;开局手牌发放时点候实机核实——种子是随机态未验证假设,首锚定纠正 |
| `front_row`/`back_row` | 空行 | 布阵发生在备战阶段(游戏流程) |
| `equips`/`board`/`occupied_equips`/`spheres` | 空 | 开局真值 |
| `gold` | 0 | 用户裁定;`gold_per_plane_start` (6,8,12) 是位面增发口径非开局值(`cw_investments.py:182`) |
| `level` | 3 | 用户裁定;注意读口旧缺省为 1(等级读口未观察缺省 1),种子 3 更贴近真值(§2.6-7) |
| `xp` | (0, 4) | 用户裁定(L3 升级所需=4) |
| `hp` | 80 | 用户裁定;开局不利的局(−20,`cw_opening_hp._AFFIX_HP_DELTA`)由首读纠正;种子走 rand 不碰 hp 写入闸(非真读不经 observe,§3.2.13) |
| `streak` | 0 | 开局真值 |
| `back_layout` | 6 | 机制基线(字段注释:平常 6) |
| `deploy_cap` | 3 | 用户裁定(= level,财富宝钻 0;字段注释「= level + 财富宝钻数」) |
| `overflow_warning`/`overflow_card` | False / '' | 开局真值(无溢出) |
| `active_env` | '' | 未选择(空串 falsy,与 None 同消费方向) |
| `active_strategies` | [] | 开局真值(未持卡) |
| `enemy_affixes` | [] | 新局简报即覆写;接管局位面详情实采覆写;两写端都在决策前(`cw_screen_report/plane_intel.py` 幂等门) |
| `shop_refresh_cost` | 2 | `REFRESH_COST_BASE`(`cw_economy.py:109`);现消费 `value or REFRESH_COST_BASE` 行为等价 |
| `prev_node_spent` | False | 开局无花费 |
| `encounter_refresh_used`/`supply_refresh_used`/`strategy_refresh_used` | 0 / 0 / {} | 开局真值(未刷新过) |

**B 类——不种(None 是设计语义或在册禁令;逐条依据)**:

| 字段族 | 不种依据 |
|---|---|
| payload 域:`shop`/`encounter`/`supply`/十个 `*_opts` 槽/`expert_invite`/`chosen_*` 十槽/`settlement`/`match_final` | fields.md §2.2「非当前画面 = None」——None = 离屏是设计不是缺口;chosen_* None = 未选择 |
| `node`/`node_ord`/`node_path`/`node_path_baseline` | 未锚定闩本体:假局守卫(`cw_loop.py` 「从未观察到对局态」判定与局终 `_observed = node.value is not None`)、效果账本「未观察不当真进节点」闸(`effective_node_ord` None → 整段跳过)、node_ord 首锚定门——三处安全件靠 None;种 (1,1) 等于拆闸,且读口缺省本就是 1/1,种了零收益 |
| `plane_bosses` | 接管位面详情实采的触发谓词 = `not gs.plane_bosses.value`(takeover-intel-pipeline design §2.1)——种 `[None]*3` 后该列表真值化,接管实采永不触发 |
| `event_overlay` | 「'none'=确认无浮层;None=没读到」双义禁令(字段注释 §3.6.1) |
| `lv999_cost_tier` | None = 「未触发任何变换」语义档(字段注释);种 3 混淆「没变过」与「变到 3 档」 |
| `round_fresh_buys` | None = 本局未登记(字段注释语义档) |
| `level_up_cost` | 在册纪律「None=未读到禁兜底」(字段注释;读侧已有 `LEVEL_UP_COST_TABLE` 兜底,`cw_observation.py:889`)——种子即违规兜底 |
| `top_bar_raw` | 「原文缺读 = 不写(禁猜)」(字段注释) |
| `prep_substate`/`encounter_refreshed_in_visit` | 前者写端 = 接管协议分类;后者读侧 None 缺省 False 已覆盖,种子零收益 |
| `consumables` | 死字段(零读端零写端,字段注释在册)——处置归 fields 正本批 |

**C 类——不种(接管局无观察源,种 = 错一整局无人纠正)**:

| 字段 | 不种依据 |
|---|---|
| `selected_difficulty` | 新局写端 = 难度确认屏;接管局两屏都不出现——种子值永久无人覆盖,D-32 阈值错底;今日 None → 读口缺省反而是对的 |
| `enemy_difficulty` | 写端 = 简报;接管局简报缺席 |
| `game_mode` | 「两屏无建档,接线前补档」(字段注释)——现役零写端 |
| `env_refresh_used` | 零写端申报字段,「禁按字段值做决策」在册(字段注释) |

**不适用(非 Field 簿记)**:`tracked_books`/`node_books`/`frame_class_prep`/
`frame_class_shop`/`plane_node_sequences`/`effects`/`settlement_ring`/`encounter_log`/
`gs_schema`/`frame_obs`/`write_seq`/`node_hist_ord`/`node_path_diff_pending`/
`created_monotonic`/`tracked_account_observed`(特殊:三态语义见字段注释,本批不动)。

### 2.3 种子底座

- **挂点**:`game_state_of` 单例冷建点(`cw_game_state.py`:session→gs 解析的各新建
  分支汇合处)调 `seed_opening_state(gs)`。**边界**:直构 `GameState()` 的草稿路径
  (planner/invest_strategy 防御视图、env_economy 导入期探针)与 sim 直构路径不经此口
  = 不种——与遥测装配同边界(`__post_init__` 零装配精化令口径一致);sim/测试域的
  None 分支因此继续存活(§2.6-7)。
- **写法**:逐字段 `gs.write_logic_rand(field, seed值, produced_by='GsOpeningSeed',
  evidence='seed:opening', sig=ChannelSig(family='logic_action', actor='GsOpeningSeed',
  screen='', mode='seed'))`。校验面:`write_logic_rand` 族许可
  `('logic_action','logic_hook')`(cw_game_state.py:2637)✓;通道语义 = Field 注释的
  「确定外壳」形态(确定值、未验证,观察覆盖差异预期内、不进失配三分流)。
- **journal 面**:每局开局 +≈24 行 `mode='seed'` 行(可过滤;行为申报 §2.6-4)。

### 2.4 锚定闩

- **载体**:`GameState` 新增非 Field 簿记位 `prep_anchored: bool = False`(工程结构组,
  与 `frame_class_*` 同区;非 Field 理由 = 过程信号,无观察赢仲裁,同 `frame_class`
  先例注释)。
- **置位(唯一写点)**:kernel `reconcile_tracking` 的 bench 侧屏幕真值写回成功点
  (`cw_reconcile.py:434` 写 `tracked_account_observed=True` 同点)——两闩同点置位,
  语义对齐「本局已完成首次成功的备战 heavy 锚定」。
- **读口**:kernel 函数 `prep_anchored_of(session) -> bool`(经 `game_state_of` 解析,
  缺省 False;局外一次性容器恒 False)。**复位**:无——局容器每局冷建天然清零(粘性)。

### 2.5 通道规则(未锚定 → 随机态)

- **获得链写选择收口**:`cw_gain_chain.py` 四处 `write = gs.write_logic_rand if rand
  else gs.write_logic`(:294/:354/:430/:480 附近)统一改为单 helper:
  `_select_write(gs, rand)` = `rand or not prep_anchored_of(gs) → write_logic_rand`,
  否则 `write_logic`。
- **语义**:锚定前链的落账是「未验证推算」,走随机态让首观察静默覆盖(种子+链写
  一起被真值覆盖,零失配行);锚定后恢复形参语义——失配网原样生效,P2/P3 位面
  环境送卡的落位验证信号保留(对比:若用失配豁免注册表代替,screen×field×evidence
  前缀区分不了首次锚定与后续锚定,会盲掉后者)。
- **其他前置逻辑写端普查(landing 核查项)**:现役锚定前可达的 logic_action 写端 =
  获得链 + `cw_loop._absorb_selected_difficulty`(其目标 selected_difficulty 属 C 类
  不种,不受影响)。落地时 grep 全量核查申报,发现第三处按同规则收口。

### 2.6 行为变化申报

1. **窗口内获得链从「零写留证」变「种子底座落账」**:落位/合成行真实产生,但合成池
   = 种子空底座(不含开局手牌)→ 合成判断可能**少报**(游戏实际发生的合并链没算到);
   观察覆盖定谳,`GainOutcome.merge_levels` 窗口内是部分真值——已知局限,判读申报。
2. **缺陷 kind 退役**:`gain_chain_bench_unobserved`/`gain_chain_equips_unobserved`
   两 kind 不再发射(常量与发射分支删除);`bench_unobserved`/`equips_unobserved`
   detail 档在生产死化(保留给 sim/测试直构路径)。
3. **观察失败路径降级**:阵容域 heavy 重读持续失败时,容器保持种子/链写值(今日 =
   None → 各守卫保守跳过),kernel 计算族按底座继续、错误由后续对账暴露。减压面 =
   tracked 账独立于容器种子,商店门(`tracked_unobserved`)/执行闸安全网不受影响。
4. **journal 增量**:每局开局 +≈24 行种子行(`mode='seed'`)。
5. **gold「None=不可读」档消亡**(字段注释 §3.2.9):种子后 gold 恒有值;漏斗 gold
   不可读分支对种子值 carry——行为等价,口径申报。
6. **hp 种子与开局不利局的偏差窗口**:80 vs 实发(如 60)持续到首个 hp 真读帧;
   hp 写入闸不受影响(种子走 rand 非 observe,§8.8 假值防线不破)。
7. **读口缺省口径变化**:`level` 读口旧缺省 1 → 种子后读 3(更贴真值);其余 A 类
   域读口缺省值与种子值同向。A 类域的 None 守卫分支生产死化、本批不删(留测试域)。

### 2.7 测试面

- 冷建即含种子:逐 A 类字段值断言 + produced_by/evidence/mode 断言;B/C 类字段仍 None
  断言;`prep_anchored` 缺省 False;
- 观察覆盖静默:对种子字段 `observe()` 不产生失配缺陷行;
- 闩时序:`reconcile_tracking` bench 写回成功 → `prep_anchored=True`;读口解析;
- 链窗口行为:未锚定时链写 source=logic_rand(通道断言)、GainOutcome 正常、观察覆盖
  无失配;锚定后 `rand=False` 链写走 logic 且模拟失配可产缺陷行(失配网未盲);
- 接管局同构:经 `game_state_of` 兜底建立路径的容器同样含种子;
- gain-chain 测试改写:`test_cw_gain_chain` 未观察用例(bench/equips None → 零写留证)
  改写为种子路径断言;退役 kind 断言反转。

### 2.8 与相邻批的关系

- gain-chain 迭代的【待梳理标记】(gain-chain.md §6、cw_gain_chain.py 两处发射点)
  由本批消偿——正本改写归本批末阶段;
- tool-gain-report 迭代(在飞)自引「裁定⑤同款」的零写分支:其消费域(equips 等)
  在本批后不再出现 None,其语义自然收敛,无需回头改;其攻击报告点名的
  `transform_equip_to_privilege` None 静默面含「无此件」档,与本批无涉;
- 队列①(pick_supply 迁链)宜后置:链消费面扩大前,种子底座先行。
