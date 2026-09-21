# 容器开局种子底座与锚定闩(「未观察」根治批) 迭代设计(总纲)

## 0. 元信息

- 迭代目标:GameState 容器在冷建时以开局初值播种(随机态通道,观察可直接覆盖),配
  **锚定闩**统一「未锚定期」的写通道规则——消偿获得链迭代(gain-chain)裁定⑤的
  【待梳理标记】,根治「bench/equips 未观察 = bug 面」的留证现状。
- 用户裁定(2026-09-21,逐条):①种子方向——新局与接管局的容器字段开局即设具体初值,
  后续第一次观察直接写入、不停机;②通道 = 随机态(`write_logic_rand`),用随机态表达
  「未经观察验证的底座」;③种子数值:gold=3(对齐 sim 开局模型 M01)、level=3、
  deploy_cap=3(与 level 一致)、xp 升级所需=4、hp=82(取自在册实证基线;开局数值
  对实机影响有限,sim 贴真优先,后续采集再校);④开局时点(容器建立,简报前)确无
  手牌;进入 1-1 时经「开局补给」赠送内容(细目候实机观察)。
- 状态:定稿(r1 攻击 12 条 + r2 复攻 4 条全部处置;攻击收敛·试读过;r2 判定
  「单点修订后定稿」,单点已落)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

### 现状症状(锚 = 文件::位置,路径根 = `src/sr_od/application/currency_war/`)

1. **新局投资环境落地相,阵容/经济域结构性未观察**:对局链序 = 简报 → 投资环境 →
   投资策略 → 备战(`operations/cw_entry/cw_entry_start.py:436` 流程注);而
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
3. **「未观察」判据散布**:全仓「未观察/unobserved」消费面广泛(判据形态多样),
   处置形态四种并存(台账留证不停机 / 显式门+跳过+熔断 / fail-closed 留证响停 /
   静默零写无留证),无单一判据源。

### 根因归层

**表示层**——「未知(未锚定)」被表示为值域 None,与「已观察下的空」同域不同义;
消费侧被迫各自补判别,守卫方向互不一致(有的保守关、有的默认满、有的响停)。

### 解决到哪 / 明确不解决

解决:A 类字段开局播种(阵容/经济域锚定前不再是 None)→ 这些域的「未观察」判据
整体消亡;锚定闩 + 通道规则让获得链在窗口内正常落账且首观察静默覆盖;carry 守卫
收窄封住「随机态值被失读腿洗成可信 carried」的假值通道。

明确不解决(防外溢):

- B/C 类字段保持 None(§2.2 分诊——None 在这些字段上是设计语义或在册禁令);
- tracked 账机制(`tracked_books`/`tracked_account_observed`)不动——它是独立于
  容器种子的执行侧安全网;
- node 族的 None 元信号消费点不动(假局守卫/效果账本闸/首锚定门,node 族不种 = 零改动);
- sim 引擎的状态合成机制不动(sim 开局手牌写点 = 引擎起点 1-1 备战,与本批种子
  不同时点,§2.2 bench 行);遥测采集缺口(plane_modifiers/shop_locked 无 reader)
  不动;
- tool-gain-report 迭代(在飞)的零写分支语义不回头改——其消费域(equips 等)在本批
  落地后自然不再出现 None(关系申报见 §2.8)。

## 2. 方案(完整设计)

### 2.1 总体结构

四件套:**①开局种子底座**(冷建口播种,A 类字段)→ **②锚定闩**(首次备战 heavy
锚定成功置位的粘性位)→ **③通道规则**(未锚定期间容器逻辑写一律走随机态)→
**④carry 守卫收窄**(随机态来源不沿用,封洗白通道)。
全部住 kernel(`kernel/cw_game_state.py` + `kernel/cw_reconcile.py` 置位点 +
`kernel/cw_gain_chain.py` 规则消费),op 层零改动。

### 2.2 字段分诊(容器 Field 全集三类;判据 = 「开局真值或首观察可覆盖」/「None 是设计语义」/「无观察源」)

**A 类——种**(种子值与依据逐行标注):

| 字段 | 种子值 | 依据 |
|---|---|---|
| `bench` | 空槽位 `BenchView`(9 空槽,capacity 9) | 用户游戏知识(裁定④):容器建立时点(简报前)确无手牌——空底座在建立时点为**真值**;1-1 进入时「开局补给」赠送内容,细目候实机观察,其合并效应归观察覆盖。**强源三重在册**:`docs/game/currency_war/research/screen_flow_timing.md:70`(投资屏选完进 1-1 触发开局补给,给开局角色+晶矿)、sim-redesign design.md:474(u07u28:开局手牌来自开局补给独立发牌通道,不走商店)、`screens/wait_one_one.md`(等待该动画的 op)。sim 开局手牌写点 = 引擎起点(1-1 备战),与本种子不同时点,无冲突 |
| `front_row`/`back_row` | 空行 | 布阵发生在备战阶段(游戏流程) |
| `equips`/`occupied_equips`/`spheres` | 空 | 开局真值;补给含晶矿发生在 1-1 进入时点(screen_flow_timing #5),建立时点 spheres 为空、1-1 观察覆盖 |
| `board` | (不直接写) | 经 front_row/back_row 种子走行域派生链承担(`_resync_board_delta`);**冷建时点无观察基座 → 派生跳过,board 保持 None、种子面零派生行**(实码行为,3.1 验收核实);board 首次落行 = 首个含派生基座的观察帧。禁双写 |
| `gold` | 3 | 用户裁定,对齐 sim M01 `OPENING_GOLD`(`sim/cw_sim_opening.py:52`) |
| `level` | 3 | 用户裁定;`XP_TO_NEXT_LEVEL` 表键一致(`cw_economy.py:51`);读口旧缺省 1,种子 3 更贴真值(§2.6-8) |
| `xp` | (0, 4) | 用户裁定(L3 升级所需=4);表值一致(`XP_TO_NEXT_LEVEL[3]`) |
| `hp` | 82 | 用户裁定;值取在册实证基线 `OPENING_HP_BASE`(109 局零方差,`cw_opening_hp.py:22`,实证域 A8/难度108,其余职级档候采集)。**三写端时序固定**:种子(建立点)→ 先验(首漏斗帧 `write_prior`,按档 82/62;非实证档先验返 None → 先验腿跳过,容器保持种子随机态至真读——收窄后 carry 不降级,§2.5)→ 真读。申报:决策可信位门(`hp_decision_trusted`)只认 observation/carried——种子对可信位消费**零增益**,价值 = 值域统一底座(journal/显示面);开局不利局种子 82 vs 实发 62 的偏差持续到纠正点(§2.6-6) |
| `streak` | 0 | 开局真值 |
| `back_layout` | 6 | 机制基线(字段注释:平常 6) |
| `deploy_cap` | 3 | 用户裁定(= level,财富宝钻 0;字段注释「= level + 财富宝钻数」) |
| `overflow_warning`/`overflow_card` | False / '' | 开局真值(无溢出) |
| `active_env` | '' | 未选择(空串 falsy,与 None 同消费方向) |
| `active_strategies` | [] | 开局真值(未持卡) |
| `enemy_affixes` | [] | 新局简报即覆写;接管局位面详情实采覆写;两写端都在决策前(`cw_screen_report/plane_intel.py` 幂等门仅空时写,种子空表放行 = 与今日 None 行为一致) |
| `shop_refresh_cost` | 2 | `REFRESH_COST_BASE`(`cw_economy.py:109`);现役消费 `int(_v) if _v is not None else SHOP_REFRESH_COST`(`cw_economy.py:660-663`),种子 2 与基价等价 |
| `prev_node_spent` | False | 开局无花费 |
| `encounter_refresh_used`/`supply_refresh_used` | 0 / 0 | 开局真值(未刷新过) |
| `strategy_refresh_left` | {} | 开局无持卡真值(剩余语义化,观察写端读缺键跳写 = 键粒度增量,与空表协同;值域纪律照字段注释「基线每卡 1 次,禁按基线核对预期」不变) |

**B 类——不种(None 是设计语义或在册禁令;逐条依据)**:

| 字段族 | 不种依据 |
|---|---|
| payload 域:`shop`/`encounter`/`supply`/十个 `*_opts` 槽/`expert_invite`/`chosen_*` 十槽/`settlement`/`match_final` | fields.md §2.2「非当前画面 = None」——None = 离屏是设计不是缺口;chosen_* None = 未选择 |
| `node`/`node_ord`/`node_path`/`node_path_baseline` | 未锚定闩本体:假局守卫(`cw_loop.py` 「从未观察到对局态」判定与局终 `_observed = node.value is not None`)、效果账本「未观察不当真进节点」闸(`effective_node_ord` None → 整段跳过)、node_ord 首锚定门——三处安全件靠 None;种 (1,1) 等于拆闸,且读口缺省本就是 1/1,种了零收益 |
| `plane_bosses` | 接管位面详情实采的触发谓词 = `not gs.plane_bosses.value`(takeover-intel-pipeline design §2.1)——种 `[None]*3` 后该列表真值化,接管实采永不触发 |
| `event_overlay` | 「'none'=确认无浮层;None=没读到」双义禁令(§3.6.1) |
| `lv999_cost_tier` | None = 「未触发任何变换」语义档;种 3 混淆「没变过」与「变到 3 档」 |
| `round_fresh_buys` | None = 本局未登记(字段注释语义档) |
| `level_up_cost` | 在册纪律「None=未读到禁兜底」;读侧已有 `LEVEL_UP_COST_TABLE` 兜底(`cw_observation.py:889`)——种子即违规兜底 |
| `top_bar_raw` | 原文缺读不写(禁猜),观察层字段 |
| `hp_floor_triggered`/`prev_screen`/`current_screen`/`receipts` | 事件登记位与过程上下文:None = 未判定/未产生,种子 False/'' 会把「未判定」伪装成「已判定未触发」;消费面无 None 痛点 |
| `prep_substate`/`encounter_refreshed_in_visit` | 前者写端 = 接管协议分类;后者读侧 None 缺省 False 已覆盖,种子零收益 |
| `tracked_account_observed` | 它是 Field(`Field[bool]`)但禁种:None = 缺省可信(在册三态语义),种 False 拆商店门、种 True 假锚定——安全网字段,保持不动 |
| `consumables` | 死字段(零读端零写端)——处置归 fields 正本批 |

**C 类——不种(接管局无观察源,种 = 错一整局无人纠正)**:

| 字段 | 不种依据 |
|---|---|
| `selected_difficulty` | 新局写端 = 难度确认屏;接管局两屏都不出现——种子值永久无人覆盖,D-32 阈值错底;今日 None → 读口缺省反而是对的 |
| `enemy_difficulty` | 写端 = 简报;接管局简报缺席 |
| `game_mode` | 两屏无建档,接线前补档——现役零写端 |
| `env_refresh_left` | 剩余语义化后已接观察写端(`report_screen_invest_env_obs` 摄入,读缺跳写);开局剩余基线值无在册出处,种猜测值 = 决策面虚构——None = 未观察,投资环境屏现场 OCR 自足 |

**不适用(非 Field 簿记)**:`tracked_books`/`node_books`/`frame_class_prep`/
`frame_class_shop`/`plane_node_sequences`/`effects`/`settlement_ring`/`encounter_log`/
`gs_schema`/`frame_obs`/`write_seq`/`node_hist_ord`/`node_path_diff_pending`/
`created_monotonic`。

### 2.3 种子底座

- **挂点(写死)**:`game_state_of` 的**两个缓存单例建支**(不可弱引用支/弱引用支,
  即与 `_establish_singleton_journal` 同边界的分支)冷建后调 `seed_opening_state(gs)`;
  `session=None` 一次性支**不种**(不缓存不装配,测试域依赖该支的未写形态)。
  不经 `game_state_of` 缓存单例支的直构 `GameState()` 一律不种:planner/invest_strategy
  防御视图、env_economy 探针、银狼屏防御视图、`scalar_projection_state`、sim、测试。
- **写法**:逐字段 `gs.write_logic_rand(field, seed值, produced_by='GsOpeningSeed',
  evidence='seed:opening', sig=ChannelSig(family='logic_action', actor='GsOpeningSeed',
  screen='', mode='compute'))`。校验面:族许可 `('logic_action','logic_hook')` ✓;
  mode 取封闭集现役值 `'compute'`(`LOGIC_MODES = ('compute',)`,cw_game_state.py:285)
  ——**journal 过滤键 = `actor='GsOpeningSeed'`**(mode 不扩词表)。通道语义 =
  Field 注释的「确定外壳」形态(确定值、未验证,观察覆盖差异预期内、不进失配三分流)。
- **写序与派生行**:行域(front_row/back_row)先写;board 派生在冷建时点无观察基座
  跳过(实码行为,3.1 验收核实)——种子面零 board 行;journal 增量 = 23 行种子
  (§2.6-4)。
- **hp 三写端时序**(§2.2 hp 行)照表实现,禁倒序。

### 2.4 锚定闩

- **载体**:`GameState` 新增非 Field 簿记位 `prep_anchored: bool = False`(工程结构组,
  与 `frame_class_*` 同区;非 Field 理由 = 过程信号,无观察赢仲裁,同 `frame_class`
  先例注释)。
- **置位(唯一生产写点)**:kernel `reconcile_tracking` 的 bench 侧屏幕真值写回成功点
  (`cw_reconcile.py:434` 写 `tracked_account_observed=True` 同点)——两闩同点置位,
  语义对齐「本局已完成首次成功的备战 heavy 锚定」。
- **读口**:kernel 函数 `prep_anchored_of(session) -> bool`(经 `game_state_of` 解析,
  缺省 False;局外一次性容器恒 False)。**复位**:无——局容器每局冷建天然清零(粘性)。
- **直构容器语义**:直构 `GameState()` 视同未锚定(`prep_anchored=False`)。**测试
  置闩专口 = 直接赋值 `gs.prep_anchored = True`**(声明为测试/直构域专用;生产唯一
  置位写点 = reconcile 同点)。

### 2.5 通道规则(未锚定 → 随机态)

- **获得链写选择收口**:`cw_gain_chain.py` 全部 `write = gs.write_logic_rand if rand
  else gs.write_logic` 形态的写选择点(HEAD 四处 :294/:354/:430/:480;在飞迭代
  invest-landing-chain 已增至五处并新增原语,落地时 grep 计数为准)统一改为单 helper:
  `_select_write(gs, rand)` = `rand or not prep_anchored_of(gs) → write_logic_rand`,
  否则 `write_logic`。
- **语义**:锚定前链的落账是「未验证推算」,走随机态让首观察静默覆盖;锚定后恢复
  形参语义——失配网原样生效,P2/P3 位面环境送卡的落位验证信号保留(对比:失配豁免
  注册表按 screen×field×evidence 前缀区分不了首次锚定与后续锚定,会盲掉后者,故不用)。
- **需按通道规则裁决的写端(census;逐个写明处置)**:
  | 写端 | 目标域 | 处置 |
  |---|---|---|
  | 获得链全部原语 | 阵容/经济域(A 类) | 收口(本规则主体) |
  | `cw_loop._absorb_selected_difficulty` | selected_difficulty(C 类不种) | 不收口:种子不涉,行为不变 |
  | 简报三写点(`cw_screen_report/briefing.py`) | enemy_affixes/plane_bosses/enemy_difficulty | 不收口:enemy_affixes 种子 [] 被直写覆写 = 预期(三读数一局恒定,覆写无信息损失);后两域不种 |
  | 位面详情写门(`cw_screen_report/plane_intel.py`) | plane_bosses/enemy_affixes | 不收口:幂等门/真值不覆写门与种子空值协同 = 今日行为;不种域不涉 |
  | always-rand 直写点(pick_supply/pick_planner/tool_use/collect_ore/pick_equip/cw_gain_effects 等,落地时 grep 为准) | 各自目标域 | 天然合规:直 rand 通道不经选择点,规则不辖,列名备查 |
  | 效果账本桥写端群(`cw_effect_inventory` ≈12 处) | bench/行域/equips 等 A 类域 | **前提经 3.2 复核推翻**:投资策略屏「人力重组」(SELL_ALL)经 `gain_invest_strategy` 登记腿 → `apply_board_rewrite` 清空写,写门 = 域已读,种子后三门全开 → **锚定前可达**。裁定 = 本行预埋的「按同规则收口」:`apply_board_rewrite` 容器清空写经锚定闩择道(未锚定 → rand);择道 helper 住 `cw_game_state`(cw_gain_chain `_select_write` 同源委托,防 kernel 内循环 import);UPGRADE_ALL 零写不涉;其余桥写端(补给/策划/上阵/获得回执/工具回执)锚定后可达,天然合规 |
  | `cw_effect_inventory` 内部选择点 2 处(merge_cascade_write/grant_bench_unit_cascade) | 阵容域 | 调用面锚定后(补给/策划/上阵/回执),按形参语义天然合规(3.2 复核登记,不收口) |
  | `PrepActionExecutor` 2 处 | 执行随动域 | 锚定后窗口,天然合规(登记备查) |
  | 动作上报族 A 类目标若干(kernel/cw_action_report/) | 各动作域 | 锚定后动作,天然合规(登记备查) |
  | `cw_strategy_manager`(职级难度第二写端) | selected_difficulty(C 类不种) | 并入 `_absorb_selected_difficulty` 同行处置:种子不涉,行为不变 |
  | `cw_loop`(B 类安全网域直写) | node 等不种域 | 非裁决对象 |

  (census 实码核验基线 = `reviews/3.1-r1.md` census 附项;清单外新写端 = 回修本表,禁静默。)
- **carry 守卫收窄(封洗白通道)**:`carry()` 现守卫只查 `value is None`
  (cw_game_state.py:2544),会把 logic_rand 种子原样换帧成 `source='carried'`
  (可信位),击穿 §8.8 假值防线(实证可达路径:接管局 shop-open 帧 hp 失读支)。收窄 =
  **现值来源为 logic_rand 时 carry 不沿用(返回不动)**——随机态种子/采样值不是
  「上次好值」,失读时宁保持未验证态不洗白。**影响面矩阵(3.1 验收按实码修订)**:carry
  腿共 **11 条**(漏斗 gold/level/hp/enemy_difficulty/deploy_cap/streak/board/
  shop_refresh_cost 八条 + `cw_screen_prep` 失读腿 bench/front_row/back_row 三条);
  rand 写域 ∩ carry 目标域 = **{board, bench, front_row, back_row}**(board = 行域
  rand 派生;阵容三域 = 种子/链写后现值即 logic_rand)——四域失读帧收窄后不再洗白 =
  **存量语义修正**(与 §2.6-3 合并申报);其余七腿与现役 rand 写域零交点,行为不变。

### 2.6 行为变化申报

1. **窗口内获得链从「零写留证」变「种子底座落账」**:投资环境落地窗口(1-1 进入前)
   bench 空底座为真值(裁定④),链落位记账在该窗口为真值记账;「开局补给」在 1-1
   进入时点送达,其内容不可知、合并效应归观察覆盖——链记账只辖自己授予的卡。若实机
   观察推翻补给时点(手牌更早在席),则窗口内合成推演存在按手牌张数的系统性少报,
   定量申报候实机数据。
2. **缺陷 kind 退役**:`gain_chain_bench_unobserved`/`gain_chain_equips_unobserved`
   两 kind 不再发射(常量与发射分支删除);`bench_unobserved`/`equips_unobserved`
   detail 档在生产死化(保留给 sim/测试直构路径)。
3. **观察失败路径降级 + carry 收窄**:阵容域 heavy 重读持续失败时,容器保持种子/链写
   值(今日 = None → 各守卫保守跳过),kernel 计算族按底座继续、错误由后续对账暴露;
   carry 收窄后随机态值不再被失读腿洗成可信 carried(§2.5,含存量语义修正申报)。
   减压面 = tracked 账独立于容器种子,商店门/执行闸安全网不受影响。
4. **journal 增量**:每局开局 23 行种子行(键
   `actor='GsOpeningSeed'` 可过滤;board 冷建时点无观察基座零派生行,首观察帧起按
   派生链正常落);首观察对种子≠真值字段逐字段落
   `logic_rand_outcome` 台账行(机制内行为,量级 ≈ 种子不命中字段数/局,归随机模型
   校准遥测面——判读时与采样链 outcome 行同面,勿当缺陷)。
5. **gold「None=不可读」档消亡**(fields.md §3.2.9):种子后 gold 恒有值;漏斗 gold
   不可读分支经收窄后 carry 对种子不再沿用——gold 保持种子值直至真读,口径申报。
6. **hp 偏差窗口与零增益申报**:种子 82 在开局不利局(实发 62)持续到先验/真读纠正;
   决策可信位门不认 rand 种子——hp 种子对血购闸等可信位消费零增益(值域统一底座
   价值见 §2.2)。
7. **读口缺省口径变化**:`level` 读口旧缺省 1 → 种子后读 3(更贴真值);A 类域的
   None 守卫分支生产死化、本批不删(留 sim/测试直构域)。
8. **rand 通道语义例外立据(正本义务)**:rand 通道在册纪律「策略消费前必须重观察」
  与种子「供未锚定期直接消费」构成显式例外——例外边界(仅种子底座 + 未锚定期链写,
  锚定后恢复纪律)随 fields.md 新小节立据(正本更新清单)。
9. **锚定前「人力重组」清空写改道随机态**(census 复核裁定,§2.5):投资策略屏选
  人力重组(SELL_ALL)时,`apply_board_rewrite` 容器清空写未锚定期走 rand——首观察
  (含开局补给内容)静默覆盖,**不再触发失配安灯**(改道前该场景必产真失配行);
  锚定后按形参原语义,失配网保留。

### 2.7 测试面

- 冷建即含种子:逐 A 类字段值断言 + produced_by/evidence/mode='compute' 断言;
  B/C 类字段仍 None 断言;`prep_anchored` 缺省 False;`game_state_of(None)` 一次性支
  不种断言;直构容器不种断言;
- 观察覆盖种子:**不进失配三分流(零 mismatch 三分流行)**;种子≠真值字段的差异落
  `logic_rand_outcome` 台账行(断言其存在与 kind);
- 闩时序:`reconcile_tracking` bench 写回成功 → `prep_anchored=True`;读口解析;
  测试专口直赋生效;
- carry 收窄:logic_rand 值 + 失读 carry 腿 → 值与来源不变(不洗白);非 rand 来源
  carry 行为不变(存量回归臂);
- 链窗口行为:未锚定期链写 source=logic_rand、GainOutcome 正常、观察覆盖零三分流行;
  置闩后 `rand=False` 链写走 logic、模拟失配可产缺陷行(失配网未盲);rand 透传双臂
  用例改写(直构未闩 = logic_rand / 置闩 = 按形参);
- 接管局同构:经 `game_state_of` 缓存单例支的接管容器同样含种子;
- gain-chain 测试改写:`test_cw_gain_chain` 未观察用例改写为种子路径断言;退役 kind
  断言反转。

### 2.8 与相邻批的关系

- gain-chain 迭代的【待梳理标记】(gain-chain.md §6、cw_gain_chain.py 两处发射点)
  由本批消偿——正本改写归本批末阶段;
- **invest-landing-chain**:主落地 `0358aa60a` 已入库(获 `gain_invest_strategy` 原语、
  `cw_gain_effects.py`、`env_refresh_left`/`strategy_refresh_left` 改名接观察写端)——
  文件冲突面 = `cw_gain_chain.py`/`cw_game_state.py`/`test_cw_gain_chain.py`;本批 3.1
  在 `0358aa60a` 之上续作(字段名以 HEAD 为准),3.2 以「落地时 grep 计数」为准全量
  收口,与该批余量的次序在进度账本定序,禁双写并飞;
- tool-gain-report 迭代(在飞)自引「裁定⑤同款」的零写分支:其消费域(equips 等)
  在本批后不再出现 None,其语义自然收敛,无需回头改;其攻击报告点名的
  `transform_equip_to_privilege` None 静默面含「无此件」档,与本批无涉(种子后
  `inv is None` 分支死化、`无此件` 档行为等价,已核);
- 队列①(pick_supply 迁链)宜后置:链消费面扩大前,种子底座先行。
