# 统一观察架构:画面 op 基类设计(实机/sim 只在获取观察数据一步分流)

> 本文 = 货币战争「统一观察架构」设计初稿。它建立在 BoardState 记录模型之上
> (记录模型字段级规格正本 = `docs/develop/sr_od/application/currency_war/game_state/fields.md`,
> 总纲入口 = docs/develop/sr_od/application/currency_war/game_state/README.md,下称「记录模型设计」)——
> 记录模型管「记什么」,本文管「谁在什么时机把观察喂进去、决策怎么消费、
> 动作怎么落回」。两文冲突时以记录模型设计为字段语义正本口径,本文为流程/端口
> 正本。本文未写且无登记的问题 = 待裁决事项(开放问题清单另行成文),先裁决
> 落文再实现。
>
> 架构对称性声明:实机/sim 的分流在**两端**各有一份完整契约——观察侧
> (§2 观察端口契约)与动作侧(§6 动作 op 基类,与观察侧对称)。中间的
> 记录/对账/决策消费(§5 生命周期)是两域共用的一份代码。循环的起点与
> 启动边界见 §4。
>
> 修订记录:v5 = 方案对抗审 F1-F11 落文(F1-F8 实现前修订/F9-F11 勘误);
> v6 = 选职级决策面裁决回填(A10 选项②确认)+ 开放问题重编号总表;
> v7 = 方案审扩展轮合并总核对清单落文(R-A…R-Q;新增 R-E 触发时点轴/
> R-I 词表实漏补全/R-J 执行器非登记职责留守/R-N applied 提取与恒 paid
> 不对称申报);v8 = A8 盘点批(3187b565)结论回填——§8.0 盘点基线
> (前提纠正:win_reward_mult 属投资策略非环境效果/环境侧 83 条零结构化
> 经济字段/建模现状矩阵/active_env 消费面样式先例/生产侧=对账预测层落点/
> 保真度边界)+ §8.2 重述(考题对象=环境效果结构化词表五类)+ §8.3
> 「注册表有值引擎零消费」字段裁决清单(衔接 T1a);v9 = 无前提攻击第 1 轮
> 9 项修复落文(申报:§7.1 回填同步——T1a 批增补未记修订版本,随 v9 补记
> + §7 行 5 翻正 + F-1..F-9 + A1 段身份申报机制裁决落文〔引擎内段身份
> 申报〕);v10 = T-217 流程 hook 观测点设计并入——新增 §12 流程转点
> 观测锚章(锚点事件集/数据面 schema/准确性判据/机制关系声明),
> §6.4 触发时点轴扩第三型「边界型」申报,§11 增 R11;§12 经对抗审
> (高 3/中 6/低 7)就地修订:sim 侧锚行落盘面如实申报(「两域」改
> 实机先行)、指标 1 闭合公式重构(尝试口径四项)、levelup_landed 改
> 收编现役 'level_up' 行禁双行、boundary 触发口与公式可测性立 H6/H7。
> v10 对照说明见 docs/develop/sr_od/application/currency_war/design/T-217-流程hook设计v1.md
> (R2);对照说明(v5-v9)见
> docs/develop/sr_od/application/currency_war/design/统一观察架构-修订对照说明.md;
> v11 = 验证段废除(用户裁定 2026-09-10:动作 op 只管机械执行,禁止做
> 任何验证)——§5.1 六段→五段(验证段删除及规范理由落文),§5.2 联动
> (备战原型行/事件屏迁移行);v12 = T-223 用户终裁(2026-09-10)落地
> 回执门最严读法落文——§6.2 验真锚退役(实机适配器只机械执行,落地
> 判定完全归观察侧 reconcile)、§6.4 单一发射口(两 fire 口合并;落地
> 回执门〔OUTCOME_TRIGGER_LANDED 型〕退役;在册发射型两件口径续行)、
> 端口回执 (progressed, detail) 与 ActionOutcome.progressed 退役、
> §6.5-1 触发前提改观察侧对账承接、§6.3 applied 两域分轨申报(F11)、
> §1.1/§1.3/§4.3/§5.1/§5.2/§6.6/§9.2/§10.3/§11-R8 引用面联动;§12 流程
> hook 章本版不动(其旧轴/fire 口引用面联动候锚实现批①,清单见
> docs/develop/sr_od/application/currency_war/design/T-225-交付报告.md,禁静默改);代码零
> 触碰——协议变更与执行器验证链拆除同窗落码(批3+批3a)防真空。
> v13 = 余项收口正本对齐(统一观察架构迭代末阶段,T-8/T-47/T-48/T-45
> 交付后):§5.2/§3.4 迁移面清零(全量已迁现状 + 推进型变体收编行 +
> 过渡相位件已迁口径)、§6.4 在册两件②策略屏写端已接线、§9.2 余项
> 收口完成态(相位 1 深度统一仍待独立批)、§2.5/§9.1 并存面刷新;
> 头部四处对照说明/清单指针与 §11 开放问题清单指针 re-anchor 至
> design/ 正本同域持久位。

## 0. 名词

- **画面 op**:对一个游戏画面的处理单元(识别该画面 → 决策 → 点击/流转),
  如备战单轮 op(CwScreenPrep)、遭遇节点 op(CwScreenEncounter)。
- **观察数据**:一次结构化的画面事实读取结果——类型化 payload(强类型
  数据对象,记录模型设计 §8.3 已定形),不是裸截图。
- **意图**:策略器输出的动作对象(Action 词表:买牌/卖牌/刷新/升级/
  部署/穿装备/出战……),两域适配器消费同一套意图类型。
- **策略器**:决策函数族(decide_* 系列),基类 `CwStrategy`(strategies/impl/
  cw_strategy.py);输入 GameState 形状的视图,输出意图。
- **适配器**:同一契约的两个实现——实机一个、sim(模拟器)一个。
- **sim**:离线模拟器(engine_p1/engine_p2/runner):引擎生成真值 GameState
  并步进演化,驱动同一套策略器。
- **kernel 单一源**:同一推导只有一份实现,放在 kernel/ 桶(kernel =
  `application/currency_war/kernel/`,无画面依赖的纯逻辑层),实机与 sim
  都调用它,禁止第二份。
- **相位**:画面 op 生命周期当前正在处理哪类画面(简报/备战/商店开/遭遇/
  结算……;相位序从 1 = 简报起,§4.1)。
- **过渡相位**:边界事件触发的轻观察相位(简报/难度确认/位面详情/敌人
  情报/中断弹窗,§3.4)——出现一次、确认/选择一次即回主循环。

## 1. 第一原理与目标

### 1.1 结构公式:两个适配器 + 一份共用中段

```
              ┌─ 适配器①(获取观察数据)──────────────────┐
   实机: 截图 → 识别链(OCR/CV/SIFT/模板) ────→ 类型化观察 payload
   sim:  引擎真值 GameState ───────────────────→ 同一套类型化观察 payload
              └──────────────────────────────────────────┘
                            ↓  (唯一的入口分叉)
   ┌──────────────── 共用中段(一份代码)────────────────┐
   │ 观察数据写入 state(BoardState 同一套写入 API:       │
   │   observe / write_logic / carry /                   │
   │   leave_screen / relay)                             │
   │ → 对账(观察赢:实读覆盖 logic 直写值,               │
   │   失配 = 推算/动作 bug 缺陷台账留证)       │
   │ → 策略器消费 state(strategy_input_state 决策视图    │
   │   → 策略决策,输出意图)                             │
   └─────────────────────────────────────────────────────┘
                            ↓  (意图 = 动作对象,统一词表)
              ┌─ 适配器②(执行决策)──────────────────────┐
   实机: 点击/拖拽/等待/画面流转(机械执行,§6.2)
   sim:  引擎动作应用(语义逻辑态直写 + 真值演化,§6.3)
              └──────────────────────────────────────────┘
                            ↓  (动作发射)
   ┌──────────────── on_outcome 落地登记钩子(共用)──────┐
   │ 任何动作发射,实机/sim 两路径经单一发射口触发同一套  │
   │ 登记(刷新计数/合成升星预期/免战牌递减/账本推进,    │
   │ §6.4;落地判定归观察侧 reconcile,T-223)             │
   └─────────────────────────────────────────────────────┘
```

> 术语注:逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态;真值以下一帧观察为准(观察赢)。

三条要点:

1. **入口分叉只有一步(每端;辖域 = 画面 op 内)**。实机/sim 的全部差异被
   压缩到「观察数据从哪来」(适配器①)和「动作落到哪去」(适配器②)两个
   端口;中间的写记录、对账、决策消费、落地登记在两域是同一份代码。
   **辖域申报**:本原则辖「画面 op 内」——op 外现存的真实读屏调用点
   (既有豁免三点 = 发射帧仲裁段 cw_loop._launch_frame_arbitration:657 /
   开局最小读 cw_loop.loop:1708 / 买牌波入口 cw_op_buy_cards.run_buy_waves
   :691)不属画面 op 辖域,以**调用点白名单制**逐点申报管理(白名单纪律见
   开放问题 B4/F6),不在本原则的「只分叉在适配器」承诺内。
   **read_game_state 调用点全量扫描基线(F1,2026-09-10 实测,grep 全仓)**:
   14 命中 = 真实调用 10,分四族——①obs 桶内部 3(cw_observe_full
   .observe_full:82/:97/:117);②既有豁免 3(上述三点);③试点迁移收编类
   3(cw_screen_prep.finalize_buy_phase:2785 + cw_screen_supply_node
   ._supply_detour_collect:175 / _do_action:311——基类 observe 段接管后
   归 obs 族);④非画面 op 生产 1(telemetry/cw_match_recorder
   .extract_frame:80,遥测录局合法消费——白名单显式收录,标「非画面 op
   合法面」);另有注释 3 + def 1 不计入。立锁前重跑扫描确认基线未漂移。
2. **evidence 标注是数据差异,不是分支逻辑**。sim 合成的观察恒带
   `sim:synthesized`(kernel/cw_game_state.SIM_SYNTHESIZED),实机识别带
   识别来源注记——这是「记录里多一个字段」的差异,不是 `if sim:` 分支。
   实机特有的失读分支(识别失败 → carry 沿用 / 先验写入 / payload 离屏)
   写在共用代码里,sim 永不触发它(sim 真值域没有「读不到」态)。
3. **数学单一源原则**(用户原话级约束)。sim 给的观察数据直接复用项目的
   逻辑计算(升星推算/退款公式/收入三支/账本推进/派生键);凡 sim 私有的
   换算逻辑都该删掉,换成对公共函数(kernel 单一源)的调用。先例 =
   `board_next_tier_of` 薄委托(kernel/cw_game_state 唯一实现,实机 obs
   computed 支与 sim 观测键 engine_p1._board_next_tier_of 都委托它)。

### 1.2 为什么:已发生的分叉实例

要治的病不是假设,是已发生过的真实缺陷类。四个主实例:

1. **win_reward_mult 注册表有值、生产零消费**(修饰性逻辑分叉)。伟大征服
   把连胜奖励 ×3(注册表 cw_investments.STRATEGY_ECONOMY
   `win_reward_mult=3.0`)。**该修饰现无任何生产调用**——唯一计算消费点
   economy_score(cw_economy.py:672)经 A8 盘点坐实已无生产调用点(消费
   仅存于测试;退役决策栈遗留死函数,清理候选防「假消费」误读,处置归
   §8.3 裁决清单);sim 引擎的轮首收入直查连胜表
   `streak_gold`(engine_p1 收入段),不乘该倍率 → 持卡局 sim 把连胜分量
   系统性少计至多 ×3。根因 = 修饰值躺在注册表里,sim 收入与决策两条链
   都没有活的消费接它——这正是「注册表有值引擎零消费」字段族
   (§8.3)的第一个实例。
2. **败补旧表**(口径漂移分叉)。战斗败轮的补发金:记录模型按玩家裁定 =
   该节点的基础奖励(平面感知键,记录模型设计 §4.2 轮首收入行);sim 引擎
   用旧类型表 `LOSS_GOLD_BY_NODE {battle:2, encounter:4, boss:4}`
   (engine_p1 败补分支)。两套口径并存,尾批挂了「sim 常量修正随之」——
   挂账本身就是分叉税:每次口径演进都要记得改第二处,漏改即静默分叉。
3. **帧新鲜度差域**(消费时序分叉)。BoardState.node 在 battle 帧也会更新,
   而执行侧装配源 `last_state` 只在备战/结算点推进——同一个「当前节点」
   在两条链上的新鲜程度不同域。这正是迁移尾批(装配源切换)不能
   机械换源的原因:换源会在帧新鲜度差域改变执行侧消费值,须独立对账重验
   (记录模型设计 §8.7 批次二「消费切换余量归属」已申报)。
4. **备战线决策面 sim 零覆盖**(决策面缺位分叉,**本架构最大盲区**)。
   sim 引擎全程不调 `decide_prep_screen`、不写 `prep_obs_frame`(备战线
   黑板,读半部整体换端口真值直出的产物)——备战子相位(部署/卖出/升级/
   收球等)由引擎内嵌的部署块/装备块直接执行,策略对备战动作的选择权在
   sim 不存在。波及面:备战是每轮主决策面(对照:遭遇/补给是低频单次
   选择),「sim 测不出」的病比遭遇/补给决策面缺位(佐证 3)更大——
   备战线策略改动在 sim 批次里结构性不可见。收敛 = §7-T5 扩域(备战线
   经基类生命周期接入 decide_prep_screen)。

同族小分叉(佐证,不完全列举):

- `_overlay_xp_per_refresh`(按持卡名查付费刷新产经验)在 engine_p1.py
  被定义了两次(后一次覆盖前一次),runner.py 一份,engine_p2.py:39-55
  第四份——同一注册表查询四份拷贝(第四份为方案对抗审全仓符号扫描抓出,
  「份数」类断言以扫描为准,见 §7 任务书纪律)。
- 利息计算:sim 引擎收入段内联 `min(cap, gold//10) + flat`,而 kernel
  cw_economy.interest() 已有同语义函数——内联式绕开单一源。
- sim 引擎的节点事件决策面绕过策略器:遭遇节点不调 `decide_encounter`
  (实机策略面已接,引擎内部直接采样难度);补给节点直调 kernel 函数
  `decide_supply`(cw_events)而非策略器接口 `strat.decide_supply`——
  策略实现覆写这两口在 sim 不生效,策略在两域看到的决策面不一致。

### 1.3 目标与非目标

目标:

1. 画面 op 收敛到「基类生命周期 + 本画面观察端口契约 + 本画面策略入口 +
   本画面执行」;实机/sim 共用中段与生命周期,只在两端口各有一对实现
   (观察端口契约 §2 + 动作端口契约 §6);循环从「第一帧观察就绪」起跑,
   启动边界两侧在循环外汇合(§4)。
2. sim 的观察供给收敛到「调 kernel 逻辑计算函数」,删除 sim 私有换算
   (逐项清单见 §7,每项一条搬迁任务)。
3. 执行落地登记统一:批次二/三散落的「执行落地门」inline 钩子收编为基类
   生命周期钩子 on_outcome——任何动作发射,两路径经单一发射口触发同一套
   登记(§6.4;落地回执门随 T-223 最严读法退役,触发前提 = 发射)。
4. 证据链闭合:sim 里验证过的决策行为与实机跑的是同一份中段代码——
   「实机验流程、sim 验算法」的分工(strategy-work「验证」)不再被
   「两边各一份实现」侵蚀。

非目标:

- 不替代记录模型设计(它仍是字段语义正本)。
- 不改策略判据本身(mandate_v1 判据面不在本架构范围;策略器契约面
  不动)。
- 不追求 sim 建模实机的识别失败面与点击落空面(sim 真值域无失读、执行
  失败面结构性为零,cw_game_ports 已申报——如实申报即可)。
- 不把实机菜单导航(大厅→进对局)收进统一循环——它只属于实机世界,
  留在循环外(§4.2)。

## 2. 观察端口契约

> 本节与 §6(动作端口契约)对称:§2 管「事实怎么进来」,§6 管「意图怎么
> 出去」。两节的契约总则同构,读其一可互推另一。

### 2.1 契约总则

每个画面 op 声明本画面的**观察输出结构**——一套类型化 payload。实机与
sim 两个实现产出同一套类型;共用中段只认类型,不认来源。

契约三则(沿 cw_game_ports.CwObservationSource 已立纪律扩展):

1. **保真位语义不取消**。payload 携带可读性/可信位(hp_readable/gold_readable
   型);实机的失读(None → carry 通道)与 sim 的恒真读是同一契约的两个
   取值域——sim 恒「真读」形态是环境参数,不是造假。
2. **观察 = 类型化 payload,识别机制不出端口**。截图、OCR、模板匹配全部
   封在实机实现内;引擎字段访问全部封在 sim 实现内。共用中段禁止摸像素
   (import cv2)也禁止直摸引擎对象(绕过端口的 `getattr(st, ...)`)。
3. **点击坐标不入 payload(存储面)**。坐标单一真相源 = screen_info 区域
   (实机适配器②内部使用);payload 只携带语义事实。

### 2.2 各画面观察输出结构

载体 = 记录模型设计 §8.3 已定形类型(NodeKey / ShopCard / ShopPayload /
EncounterPayload / SupplyPayload / Settlement / Unit / BenchView /
SphereSight)。备战画面的席位身份细节(bench_chars/deployed_chars,SIFT
识别域)载体 = PrepObservation(kernel/cw_prep_actions)——该域显式申报为
「执行域透传」(kernel/cw_bs_view 模块 docstring 未建模域清单),不强行并入
BoardState。

| 画面(相位) | 观察输出结构 | 写入 BoardState 的域 |
|---|---|---|
| 简报/难度确认(相位 1) | 职级选项/已选职级 + 简报字段(敌人难度/词缀/boss 名单) | bs.selected_difficulty(难度确认屏观察写端)+ plane_bosses / enemy_affixes / enemy_difficulty(开局初值域);统一前现役形态 = session 写 + relay 载体中继(§4.4) |
| 备战(关店) | read_game_state 的 prep_clean 段字段集 + PrepObservation | node / gold / level / xp / hp / enemy_difficulty / level_up_cost / streak(**carry-only**:现役漏斗只做结算带符号真值沿用、禁幅度覆盖,符号名锚 cw_observation 备战漏斗 :2492-2493 bs.carry;记录模型设计 §3.2.12)/ board / bench(观察流漏斗 = `_feed_board_state`,逐字段门 = PHASE_FIELD_SPEC) |
| 备战(商店开) | ShopPayload(cards×5 + refresh_probs)+ 刷新钮标价 | bs.shop(载荷域)+ gold + level/xp/level_up_cost + shop_refresh_cost(现场 OCR,失败=carried) |
| 遭遇选择 | EncounterPayload(options)+ 刷新剩余次数 | bs.encounter(载荷域,观察写端)。**encounter_refresh_used 另注**:无观察写端,logic 写端 = 刷新点击置位(批次三⑦,随点击置位不等验效,§6.5-4) |
| 补给选择 | SupplyPayload(动态列数 3-5) | bs.supply(载荷域) |
| 投资环境/策略 | 候选三卡名(+策略屏逐卡刷新次数) | active_env / active_strategies(write_logic 豁免)+ 效果账本登记挂点 |
| 事件屏(十屏) | 各屏候选载荷 | chosen_*(选择 handler 单次逻辑写入豁免) |
| 结算 | Settlement(hp/streak 带方向/killed;金与等级经验仅胜局) | apply_settlement_cover 真值覆盖 |
| 事件浮层 | 浮层类型标识 | bs.event_overlay('none'=确认无 / None=没读到) |

### 2.3 实机实现 = 识别链映射表

实机适配器① = 现役识别链的封口:备战族观察漏斗单一入口 = read_game_state
(obs/cw_observation,含 `_feed_board_state` 观察流);简报/结算/节点屏各归
owner 模块(cw_briefing_obs / cw_settlement_obs / cw_node_obs)。

改造要点:

- 映射表是**声明式清单**(字段名 → 读取器调用 + 写入闸),不是散在 op 里的
  过程代码——op 基类按表驱动读取;失读分支(carry / 先验 / 离屏)在基类
  共用代码,读取器只回答「读到什么 / 可不可信」。
- 逐字段门(PHASE_FIELD_SPEC 三档:prep_clean / prep_shop_open /
  battle_or_transit)保持为实机实现的内部规格——它表达「哪些字段物理上
  可读」的机制事实,不是 sim 需要的概念。
- 识别质量机制(gold 稳定门多帧补采 / hp 双通道对账 / 难度旗牌两级放大)
  归实机实现内部,对契约不可见。

### 2.4 sim 实现 = 引擎真值映射表

sim 适配器① = 引擎 GameState → 同一套 payload 的映射。现役
synthesize_from_game_state(kernel/cw_game_state)是该映射的第一版,本架构
把它升格为 sim 适配器①的正式实现并扩展域覆盖。规则:

- **逐字段直取**:引擎已有真值直接映射(gold/level/xp/hp/streak/board/
  shop…);真值 None/未建模域不写(禁合成假值)。
- **派生量调 kernel 单一源**:下档阈值(board_next_tier_of)、席满
  (bench_is_full)、升星推算(detect_merge_upgrade / cw_state.simulate)、
  退款(cw_state.sell_refund)、收入三支(见 §7-T1)……一律调 kernel 函数,
  禁在 sim 适配器内重写公式(逐项现状与任务见 §7 清单表)。
- **真值缺席 = 结构离屏**:sim 真值域没有「OCR 失读」,payload 域非当前
  画面一律 leave_screen 语义(记录模型设计 §2.2 例外;批次三补单⑨已立的
  「空表与 None 同判=离屏」口径沿袭)。「当前画面」由 §3 相位映射表给出,
  **不从数据反推**(§11-R2:引擎 st.shop 段后不清空,反推会误读)。
- **evidence 恒带 `sim:synthesized`**(含轮键后缀),无分支。
- **帧供给双落(F3)**:sim 适配器①产物**双落**——①BoardState 合成写入;
  ②`session.last_state` = 合成帧(**保真位恒真读形态**:gold_readable/
  hp_readable 等按契约取值域恒「真读」)。理由:决策视图
  strategy_input_state 的透传域从 last_state 取值——**十二个透传域(F4
  对齐 cw_bs_view.game_state_view 透传块实测,符号名+行号双锚
  cw_bs_view.py:153-165)**:deployed / bench / deploy_cap / shop 波顶
  融合帧 / **refresh_probs** / active_env / plane_bosses / enemy_affixes
  / equips / front_max / back_max / dual_track_phase;hp 门后消费值同属
  帧透传(:98-100,门权威申报见该处注释)。其中 **refresh_probs 双落
  必带**:sim 轮岗 = §8.0 认定的唯一有行为效果环境机制的决策输入
  (cw_state.refresh_probs:250-252 概率条真值载体),漏带 = 商店刷新
  概率静默退基线表且不报错。**dual_track_phase 显式申报不入「双落必带」**:
  其起值源 = 装配边界回填(cw_state.py:254 字段注;写端 = `= not
  committed_from(session)`,mandate_v1/adapter.py:152 / cw_screen_prep.py
  :1626/:1858 / cw_op_buy_cards.py:713),非环境帧事实——合成帧缺省
  False 不产生行为差。sim 现役**零 last_state 写点**,不双落则 sim 路径
  的透传域全部塌到 GameState 缺省。双落 = 记录面(写入 session 属性,
  零 rng 影响);席位域直供的表述随之挂到本帧供给申报差上(开放问题 A4)。

### 2.5 与 cw_game_ports 的关系

`cw_game_ports.py`(T-120 批 0,惰性纯协议)已定义这对端口的契约:
CwObservationSource(screen_identity / observe_prep(phase) /
observe_shop_cards / overlay_options)+ CwActionSink(execute_action →
ExecResult),模块级安装槽,缺省 None = 生产直连现役路径(装配点分流面
现状 = cw_screen/ 全目录画面 op 与 cw_op/ 商店系三件均已带分流,生产恒走
旧路径,并存面与退役候批面见 §9.1)。本架构采纳它作为
两适配器的**装配机制**(安装只发生在显式装配点,进程内单装配,卸载复位);
契约面按 §2.1-§2.4 与 §6 的规格补齐消费语义。协议现存的「读什么字段」
(phase 键)与「在哪个画面」(screen_identity)两词表二分被本架构保留——
它们分别对应 §2.3 实机逐字段门与 §3 相位判定,混用会把两个语义搅在一起
(该告诫已在 cw_game_ports docstring 在案)。端口契约辖「第一帧观察就绪」
之后的循环体;启动边界不属端口辖(§4.2)。

## 3. 画面相位映射表

sim 侧唯一需要「翻译」的地方:**引擎没有画面,只有开局与轮内段序及节点
类型**。映射表把引擎状态翻译成相位,供 op 基类分派。相位序从 **1 = 简报**
起(§4.1)——简报是循环内第一帧,不是循环外的特殊代码。

### 3.1 相位判定的两域来源

- 实机 = 两套现役机制的收敛:①外循环画面分派(cw_loop.loop() 的
  round_by_find_area id_mark 锚族;备战=双锚「备战标识-购买经验」+「按钮-
  出战」,简报=「标识-本场对局首领」,遭遇=「标识-遭遇节点」,……);
  ②观察阶段键(PHASE_FIELD_SPEC)。
- sim = 引擎开局与轮内段序的翻译。开局 = Engine.new_match(seed) 激活简报
  相位(§4.2);此后每轮的段序(对齐生产 cw_loop 备战分支
  ⓪收球→①买牌→②部署→③装备→④出战):收入记账 → 选卡注入 → 备战
  动作链(商店段 decide_shop_screen 循环 → 部署块 → 装备块)→ 出战 →
  战斗结算(coarse)→ 节点事件(遭遇/补给/奖励)。

### 3.2 映射表

| 相位 | 实机判定 | sim 引擎状态 → 翻译规则 |
|---|---|---|
| **1. 简报/难度确认** | 「标识-当前难度职级」(难度确认屏,入口流内)/「标识-本场对局首领」(简报屏,cw_loop 0r 分支) | Engine.new_match(seed) 激活:引擎生成职级选项/词缀/boss 名单(游戏事实)→ 策略选职级 → 首帧观察(链路衔接见 §4.4) |
| 备战(关店) | 备战双锚命中 ∧ 无商店锚/浮层 | 备战动作链的部署块/装备块段;商店段结束后 |
| 备战(商店开) | 备战双锚 ∧ 商店锚 | 商店段内(段入口 `sess.shop_state_frame = st` 且段循环未终结;st.shop 为本轮已抽五张) |
| 战斗中/过渡 | battle_or_transit(最小读:位面轮次) | 出战 → coarse 战斗段(战斗类节点 battle/encounter/boss) |
| 结算 | 结算屏锚链(CwScreenBattleWait) | coarse 结算产出(hp/streak/killed)落账段 |
| 遭遇选择 | 「标识-遭遇节点」 | node_type=='encounter' 的遭遇屏时点(现役 sim 未消费 decide_encounter,见 §7-T5 与 §11-R3) |
| 补给选择 | 补给节点锚 | node_type=='supply',decide_supply 调用点 |
| 投资环境/策略 | 各自标识锚 | decide_invest 注入段(选卡挂点) |
| 奖励节点 | (无独立画面:备战相位,金经观察覆盖) | node_type=='reward'(引擎只入账,无画面段) |
| 事件浮层族 | 各 id_mark 锚 | sim 无浮层帧:事件即时落定,翻译恒 event_overlay='none' |

翻译规则三则:

1. **每段一次**:相位切换点 = 引擎段边界,每个边界恰好合成一帧观察
   (对齐实机「每画面入口一次 heavy 观察」节奏)。
2. **payload 域由相位声明**:shop/encounter/supply 三载荷域在合成帧的值 =
   当前相位的事实(商店相位 → payload;其余相位 → 离屏),**不**从 st.shop
   数据反推——引擎的 st.shop 只在轮首抽牌/刷新时重赋、商店段结束后不清空,
   反推会把「上段牌面」误读成「商店仍开着」。
3. **轮键恒带**:每帧合成带 `at_round='p{plane}-r{round}'`,evidence 可定位。

### 3.3 申报(映射表的已知粗糙面)

- sim 备战动作链内「商店开→关」没有独立引擎状态位(关闭是
  decide_shop_screen 终结动作 CloseShop 的语义结果)。相位映射需要引擎在
  段边界**显式申报「当前画面」**(推荐),或适配器按段序二次推导(不取)。
  前者要求引擎做一次性小改动(申报面,证明 rng 消耗序不变,见 §11-R1)。
  **申报值钉死(F9)= 引擎段身份,申报机制已裁决(A1)= 引擎内段身份
  申报**(sim 引擎侧段常量/枚举申报,如 SHOP_SEGMENT/
  DEPLOY_SEGMENT/PLANE_BRIEFING;引擎段边界赋值,纯记录面)——**非
  screen_info 画面名**:引擎禁反向依赖实机画面词表;申报住引擎的理由 =
  「当前画面事实」的唯一来源应在引擎,适配器/映射层引用同源读取;
  「段身份 → 相位」的翻译留在本表
  (§3.2)与过渡相位表(§3.4),即翻译属适配器/映射层职责。
- 战斗节点的实机「战斗中」相位在 sim 是瞬时函数调用(coarse battle),
  不存在可观察段——sim 适配器对该相位只产出结算帧,不产战斗中帧。

### 3.4 过渡相位类(边界事件的轻观察相位)

**定义**:简报/难度确认/位面详情/敌人情报(位面情报采集)/中断弹窗 =
一类「过渡相位」:出现时机 = **边界事件**——开局首次;每次位面切换复现
(简报/位面详情/敌人情报随位面推进复现);BOSS 简报 = 自动开店触发源之一
(screen_flow_timing #14 触发源清单在案)。观察轻(文本/选项级,无重识别
面);动作 = 确认/选择一次。

**接入形态**:主循环每帧 observe **先查过渡相位表**,命中 → 读选项 →
决策 → 确认 → 写 state → 回主循环——过渡相位是「表驱动的一次性小生命
周期」,不是主循环分支里的散落特判(现役 cw_loop 0 系 overlay 分支与备战
环内清场的表格化收拢)。开局首次与启动序列的衔接一句话:启动序列末尾
(§4.2 汇合点)= 第一帧观察 = 简报相位,即 §3.2 相位 1。

**收编映射**(现役对应件 → 统一后归属):

| 过渡相位 | 现役对应件 | 收编后 |
|---|---|---|
| 简报/BOSS 简报 | CwScreenBriefing 双登记点共驱(cw_loop 0r 位面简报分支 + 入口流简报屏段 cw_entry_start——观察直写 session,HandleBriefing 已退役)+ 职级 ctx 中转吸收(`_absorb_selected_difficulty`,cw_loop.py:1071,调用点 :1068) | 已迁(T-8):两登记点共同驱动同一基类驱动过渡 op;职级/boss/词缀写端 = 简报观察 payload(§2.2 简报行;切换 = 相位 1 深度统一批辖) |
| 难度确认 | CwEntryStart 难度确认段(入口流,§4.2) | 启动序列末尾 = 相位 1 入口;selected_difficulty 写端顺势归位(§4.4) |
| 位面详情 | CwScreenPlaneDetail(cw_loop 0a4 主循环兜底) | 已迁(T-47 随推进型变体收编:CwProgressionScreenOp 子类零改动,骨架即变体五段) |
| 敌人情报(位面情报采集) | CwScreenPlaneIntel(采集子 op;接管补采挂点在备战屏 = cw_screen_prep `_takeover_collect_if_needed`;入口流补采 = cw_entry_plane_intel) | 已迁(T-48 直迁,薄转录:采集体抽 `_collect_cycle` 两路径方法级共享,双节点图边保留;两处调用挂点不变;采集 = 轻观察 + skip 决策的一次性过渡生命周期) |
| 中断弹窗 | CwScreenInterruptDialog(cw_loop 分发;真 modal 红线 = 绝不点「放弃并结算」)+ cw_screen_prep 环入口清场(`_clear_entry_overlays`,关闭注册表 = ENTRY_OVERLAY_CLOSE:cw_screen_prep.py:143,派生映射 = cw_overlay_registry) | 已迁(T-47 随推进型变体收编:子类零改动,真 modal 红线承载于 `progress_once` 覆写原位);清场注册表留守原位,「可一键关闭」子集收编候相位 1 深度统一批 |

**sim 侧**:过渡相位 = 引擎段边界申报的一种——进位面段申报简报相位
(申报值 = 引擎段身份,开放问题 A1 已裁决 = 引擎内段身份申报;§3.3
同款纪律);位面
boss/词缀名单经每位面简报写端写入(plane_bosses/enemy_affixes),
selected_difficulty 开局一次顺势归位(§4.4)。

## 4. 循环起始与启动边界

### 4.1 循环起点 = 第一帧观察就绪

统一循环的起跑条件 = 「对局已存在、可取第一帧观察」。**简报(职级/难度
确认)是循环内的相位 1**——它由共用的 op 基类生命周期处理(observe →
reconcile → decide → act → on_outcome),不是循环外的特殊代码。循环外只
保留各域「把对局建立起来」的启动序列(§4.2),启动序列的终点 = 第一帧
观察就绪,即相位 1 的入口。

### 4.2 启动边界两侧

两侧在「第一帧观察就绪」汇合;此后至对局终了,是**同一份循环代码**。

- **实机侧启动序列**(仅实机存在,留在统一循环外):大厅导航 → 开始 →
  进入标准博弈 → 开始对局 → 到达难度确认屏。载体 = CwEntryStart
  (operations/cw_entry/cw_entry_start.py)——纯菜单导航 op,不含对局循环
  逻辑;它到达难度确认屏即产出「新局确凿信号」(原文 = 三屏
  〔难度确认/模式选择/简报〕合称信号,本架构取难度确认屏),职级读数经
  ctx 中转(ctx.cw_selected_difficulty)交给对局侧(两个吸收点:
  cw_strategy_manager.establish_new_match 装配段 :78-79 / cw_loop
  ._absorb_selected_difficulty(:1071,调用点 :1068;P3 收缩后仅辖职级
  难度,简报三字段已由 CwScreenBriefing 直写 session),符号名+行号双锚;
  迁移面申报见 §9.2 步骤 4)。菜单
  导航的判据(按钮锚/返回最高职级)属入口流词汇,不进相位表。
  **实机职级选择调用点(F5)= CwEntryStart 难度确认段**
  (cw_entry_start.advance_to_prep:348-365,循环外)——kernel 缺省函数
  「恒选最高」的实机辖域 = 替换该处硬编码(§4.4)。
- **sim 侧启动**:契约名 **Engine.new_match(seed)**(现役入口
  simulate_p1(seed) 的目标形态映射;seed = 局身份,与池指纹共同构成可
  复现局)——新建局即**激活简报相位**:引擎生成职级选项/对局类型/词缀/
  boss 名单(游戏事实),循环从简报相位起跑。
- **汇合点契约**:两侧各自完成「对局建立」后,第一帧观察 payload 从端口
  (§2)进入共用中段——BoardState 单例在此刻随 session 新建(记录模型
  「单例,每局新建」);cw_game_ports 装配点辖循环体,启动序列在装配点
  之外直连(实机=真读屏,sim=真值引擎),不经端口分流。

### 4.3 分叉圈养原则(用户确认表述)

适配器内无重复逻辑——**分叉被圈养在一个模式选择(if/注入)+ 两个适配器
类里,中段零分叉**:

- 实机适配器只含**实机世界才能有的答案**:识别像素(OCR/CV/SIFT)、点击
  坐标、画面等待——这些是对「本帧画面上有什么/怎么落一击」的
  物理回答,sim 世界不存在这个问题(落地判定不属适配器:T-223 后验真锚
  退役,§6.2)。
- sim 适配器只含 **sim 世界的答案**:读变量、引擎步进、真值合成——这些是
  对同一问题的另一种物理回答。
- 二者是「**同一问题的两种物理答案**,非同一逻辑两份拷贝」:凡属于逻辑
  (口径/公式/判据/登记语义)的东西,一律不进适配器——逻辑住 kernel
  单一源或共用中段(§1.1 三要点与 §7 清单表是该原则的执行面)。
- 自检判据:一段代码若能在两个适配器里各写一份且语义相同,它就不该在
  任何一个适配器里——下沉 kernel 或上收中段。反向自检:适配器里出现
  口径常数/公式/判定分支 = 圈养失败,回 §7 清单表立搬迁任务。

### 4.4 简报相位的链路衔接(相位 1 的观察/决策/写端)

简报/难度确认作为相位 1,三段链路的衔接:

1. **引擎生成职级选项 = 游戏事实**。职级表/对局类型/词缀/boss 名单是
   游戏定义的事实(注册表与画面事实);实机侧由画面呈现(难度确认屏/
   简报屏),sim 侧由 Engine.new_match 生成——两侧是同一游戏事实的两种
   物理呈现(§4.3)。
2. **策略决策选职级**(裁决已回填,开放问题 A10 选②)。统一循环内这是
   相位 1 的策略决策口。现役实机形态 = 入口流固定策略(CwEntryStart
   硬编码「返回最高职级」切最高难度——A8 财富造物主为既定目标);统一后
   形态 = **kernel 缺省函数「恒选最高」承载——两域同源(kernel 函数),
   调用点两域各异(F5):实机 = CwEntryStart 入口流内(§4.2,替换硬编码),
   sim = Engine.new_match 职级选项后同点调 kernel 函数**。相位 1 策略口
   对实机 = 只观察核对(bs.selected_difficulty)、不发射选择点击(选择已在
   入口流完成);对 sim = 真决策口。两域同源由 kernel 单一源保证,
   满足分叉圈养原则(§4.3);本函数 = 现役
   「返回最高职级」的单一源化,先例同 board_next_tier_of。升格
   decide_opening_difficulty 接口成员属策略器契约面(辖),
   待真实分化需求(如最终阵容目标需要按局势选难度)出现再议。sim 侧
   现役职级未建模(GameState.selected_difficulty 恒空缺省,批报告披露面
   在 runner)——缺省函数落地时两域同批补齐。
3. **selected_difficulty 写端衔接**。记录模型正本:难度确认屏 = 职级
   观察写端(记录模型设计 §3.1.1,开局写定恒稳)。现役实机链 = 难度
   确认屏 OCR(read_selected_difficulty)→ ctx 中转 → session → BoardState
   relay 载体中继(`_feed_board_state` 开局域镜像);统一后收敛 = 相位 1
   观察 payload 直接 observe 写入 bs.selected_difficulty(relay 镜像随
   真写端建立自然跳过——「已有正式值的字段一律跳过」既定语义)。
   **as-built 缺口(照录记录模型设计 §3.1.2)**:对局类型(标准/超频)
   两屏均无建档区域,接线前先补档;简报屏是否显示职级未建档采证。

## 5. op 基类生命周期

### 5.1 五段生命周期

```
observe()   适配器①分派:取观察 payload(实机=识别链 / sim=引擎真值)
   ↓
reconcile   对账:payload 写入 BoardState(observe/carry/leave_screen/relay)
            + 观察赢(实读覆盖 logic 直写值:一致静默;
            失配 → 缺陷台账留证,两态制)
   ↓
decide()    策略消费:strategy_input_state(session) 决策视图 → 策略入口
            (decide_prep_screen / decide_shop_action / pick 族)→ 意图
   ↓
act()       适配器②分派:意图 → 机械执行(实机=点击/拖拽/等待/画面
            流转;sim=引擎动作应用)——完整契约见 §6
   ↓
on_outcome  落地登记钩子(共用):动作发射触发统一登记集(单一发射口;
            刷新计数/合成升星预期/免战牌递减/账本推进,§6.4)
```

- **验证不是生命周期段(用户裁定,2026-09-10)**:「动作 op 只管机械执行,
  禁止做任何验证,也禁止在画面 op 做验证。如果观察正确,动作 op 没生效,
  那就是动作 op 有 bug,不应该为了 bug 增加验证这种复杂度。」生命周期
  不设验证段、不设「验证失败→重试/恢复」编排;动作未生效(观察正确而
  下一帧 reconcile 对账失配)的处置 = 修动作适配器本身的可靠性(点击链
  坐标/时序/确认序列),禁止以验证+重试结构兜底。v9 及之前版本的第六段「验证
  (执行侧验证:实机重读/金对拍/期望态对账;sim:applied 回执+规则性
  拒绝)」就此废除,其承载面的归属:
  - 期望态对账本就归观察侧闭环——op 逻辑效果经 `write_logic` 直写字段
    (两态制),下一轮观察实读覆盖(观察赢,失配 = 推算/动作 bug
    缺陷留证),与被废段无关;
  - sim 的 applied 回执与规则性拒绝(如满栏非合成拒买)= 动作应用语义
    (§6.3),在 act 段的适配器回执内产生,不是生命周期段;
  - 「点击是否落地」的判定自 T-223 终裁(2026-09-10 最严读法)起**不属
    动作适配器**:适配器只机械执行(发出即职责完成,成败回执退役——
    端口回执 (progressed, detail) 与 ActionOutcome.progressed 均退役),
    落地判定完全归观察侧 reconcile 对账(逻辑直写值 vs 下一帧实读,
    观察赢——两态制)。原 v11 表述「判定 = 动作适配器的执行回执(§6.2 验真
    锚),是 on_outcome 落地回执门的触发前提」就此废止;对账失配的治理
    = 修观察质量或动作适配器可靠性(点击链坐标/时序/确认序列),禁在
    动作层新增验证+重试结构。v12 落文 = 目标语义;判效面拆除已随 2026-09-13
    状态收敛迭代落码(4 族,执行侧判效特征词零残留),协议变更同批兑现。
- 对账、决策消费、落地登记在基类,**一份代码**;observe/act 是两个抽象口,
  实机/sim 各一实现(契约分别为 §2 与 §6)。
- decide 的输入 = `strategy_input_state`(kernel/cw_bs_view,消费切换调用面
  单一源)产出的 GameState 视图——策略器继续读 GameState 形状(契约零
  改动),值的来源已切 BoardState。
- **decide 段的 sim 替代形态(F1-② 显式申报)**:sim 侧的 decide 段由
  **sim 适配器②自带的决策块**满足——引擎内嵌的商店决策段(调
  decide_shop_screen,已接策略器接口)与部署块/装备块(引擎内嵌,现役
  **零调用 decide_prep_screen、零写 prep_obs_frame**,§1.2 病例 4)。
  统一后:备战子相位的 decide 段 = sim 驱动器经 decide_prep_screen 满足
  (§7-T5 扩域收敛);收敛前,备战线在 sim 的策略面缺位如实申报——
  sim 批次对该线的结论辖域 = 「引擎内嵌块的行为分布」,非「策略决策的
  行为分布」。
- 期望态对账(两态制 形态):op 逻辑效果经 `write_logic` 直写
  字段(策略器立即可读),下一轮 reconcile 段观察实读覆盖(观察赢,
  失配 = 推算/动作 bug 缺陷留证);原「expect 记预期 → confirm 转正 +
  reconcile_pending_observation 核对口」两步机制已废除。
- on_outcome 的触发契约(T-223 最严读法,v12):输入 = 意图 + 发射时点
  证据;**单一发射口,发射即触发(发出即职责完成,成败回执退役)**——
  原「未落地不触发」默认语义随落地回执门(OUTCOME_TRIGGER_LANDED 型)
  退役,原「落地回执(progressed/applied)为触发前提」表述废止;登记
  正确性防线改由观察侧 reconcile 对账承接(§6.4/§6.5-1)。sim 路径同样
  触发(记录面,零 rng 影响,§11-R8)。
- 失读分支(共用代码、sim 永不触发):carry 沿用 / hp 开局先验 write_prior /
  payload 离屏 leave_screen——全部是记录模型设计 §2.2 既定口径的流程化。
- 生命周期从相位 1(简报)起跑(§4.1);外循环画面分派把每个相位帧交给
  基类驱动的对应 op——过渡相位(§3.4)同样走这套生命周期,只是观察轻、
  动作单次。

### 5.2 与现役件的对应/替代关系

| 现役件 | 对应/替代关系 |
|---|---|
| CwScreenPrep.run 五段(①观察→②对账→③决策→④期望态→⑤执行) | **本生命周期的原型**:备战 op 已按五段组织,基类化 = 把②对账抽到基类共用,①观察/⑤执行换成端口调用,落地登记收编为 on_outcome(§6.4);第六段「验证」经用户裁定 2026-09-10 废除(§5.1),备战现役「验证失败→恢复原语」编排属违规面,处置归备战修复批(本架构批只排查申报)。备战 op 为第一个试点(§9.2) |
| cw_loop.loop() 外循环画面分派 | **保留**:继续承担画面识别与 op 分发(它是 screen_identity 的现役实现);基类化不动外循环,只改被分发 op 的内部结构。简报/难度确认补入分派面 = 相位 1 行(§3.2);0 系 overlay 分支与环内清场表格化为过渡相位表(§3.4) |
| CwEntryStart 入口流(大厅导航→难度确认) | **保留在统一循环外**(§4.2):菜单导航仅实机存在;其职级读数经 ctx 中转交接,到达难度确认屏即触发对局侧接管 |
| 各事件屏 op(CwScreenEncounter 等:读→决策→点击→验关内联于 handle()) | 逐屏迁移到基类生命周期(§9 分屏渐进;粒度 = B3 三段走:先「遭遇 = 带刷新链最复杂、盛会之星 = 纯选卡最简」两代表屏立验证断言集模板,其余按族批量)。已按该式迁移的屏(遭遇 CwScreenEncounter/盛会之星 CwScreenMegastar + 第二批量八屏:补给 CwScreenSupplyNode/伙伴 CwScreenPartner/骇入策划 CwScreenPlanner/祈愿试炼 CwScreenWishTrial/命运卜者 CwScreenFortune/星徽秘典 CwScreenBookcard/装备三选一 CwScreenEquipPick/专家邀请函 CwScreenExpertInvite)= 基类子类 + 决策承载节点顶部装配点分流(两端口完整在场 → 五段;缺省 None = 旧路径,先例同备战 op 行)+ 实机适配器封口:遭遇屏的 encounter_refresh_used 写端收编 on_outcome 注册表(发射型,触发点两路径共用分派面),chosen_* 写端豁免留守;余屏均无落地登记件(§6.4 收编面对事件选卡屏零行;supply_refresh_used BoardState 字段位先申报禁写端),结构 = 共享动作体型——盛会之星 decide+act 内聚 ``_do_action``;第二批量七选卡屏门后体纯移入 ``_handle_overlay`` 两路径共享零转录(无门屏 planner/fortune/equip_pick 入口判定归主循环分发,observe 段 = 轻观察帧引用);补给内聚 ``_do_action`` 且节点完成判定 = 下一轮 observe 门 ``_in_node`` 复检;专家邀请函分流在选卡节点(开卡节点 = 纯导航留旧路径,申报面 = 迁移锁源面锁)。sim 腿不适用例外清单(B3-F11)随迁移批落测试 docstring。余下相位屏已全量迁毕:五相位屏(T-8:投资环境/投资策略/战斗等待——分流在 `wait()` 首行/简报——cw_loop 0r 位面简报分支与入口流简报屏段双登记点共驱/BOSS 简报)+ 收尾五屏(T-48:位面过渡/武装箱弹窗/未达上限弹窗/等待1-1/位面情报采集——分流在 `collect()` 节点首行,双节点图边保留),cw_screen/ 目录收口锁在册(AST 全目录断言:凡 op 祖链达 SrOperation 者必为 CwScreenOpBase 后代;锁 = test_cw_obs_arch_closing_screens.py::test_closure_all_cw_screen_ops_inherit_base);cw_op/ 商店系三件亦经 B4 挂账批收编(T-45,见 §9.2) |
| CwProgressionScreenOp(第二画面 op 基类:只读/导航变体,空决策合同) | 收编为 CwScreenOpBase 变体(T-47):改挂基类 + `handle` 顶部装配点分流(两端口完整在场 → `run_lifecycle()` 变体五段;缺省 None = 现役骨架逐位执行);变体五段 = observe 入口/重入观察裁决(锚 miss 未推进 → fail 交回;miss 已推进 → 清旗标 success 出口)/reconcile + decide 空申报(空决策合同,零策略器问询)/act = `progress_once()` 推进半(免锚臂发出即 success)/on_outcome 无登记件;合同逐字保留(预算 2 归装饰器/重入裁决/免锚形态),11 子类零改动随之收敛(仅覆写 `entry_ok`/`progress_once`/类常量) |
| 过渡相位现役件(简报/位面详情/敌人情报/中断弹窗/清场注册表) | 已按 §3.4 收编映射表迁毕:简报/BOSS 简报(T-8)与位面过渡/武装箱/未达上限/等待1-1/位面情报采集(T-48)= 基类直迁过渡 op,位面详情/中断弹窗 = 推进型变体件随 T-47 收编(子类零改动);清场注册表(ENTRY_OVERLAY_CLOSE)留守 cw_screen_prep 环入口清场原位,「可一键关闭」子集收编候相位 1 深度统一批 |
| decision_assembly.snapshot_from_obs | **保留**(装配缝):PrepObservation → Snapshot 的映射半部;其回退锚已切 strategy_input_state(迁移批次三),继续作备战装配点 |
| strategies/impl/flow.py(CwFlowStrategy 分画面决策入口) | **不替代**:decide() 段的下游就是这些入口;策略器契约面不动 |
| sim 引擎决策段(decide_shop_screen 循环 + 合成口;部署/装备内嵌块) | 商店段收编为 sim 适配器②「引擎动作应用」+ 基类生命周期驱动;部署/装备内嵌块 = decide 段 sim 替代形态的待收敛面(§5.1 申报,§7-T5 扩域);synthesize_from_game_state 升格为 sim 适配器①(§2.4) |
| cw_game_ports(T-120 批 0 协议) | 两端口的装配机制(§2.5;CwActionSink 即动作端口协议位,§6.3) |
| 执行落地门 inline 钩子(批次二/三散点:record_refresh_execution 接线点 / bump_key / 合成升星逻辑态直写 / 免战牌 consume_use) | **收编为基类 on_outcome 钩子**(§6.4)——位置迁移,登记件语义不变;触发前提自 v12 起改发射语义(T-223:落地门退役,§6.4/§6.5-1) |

### 5.3 框架归属与依赖方向

- op 基类住 operations 桶(它消费 obs/sim 的端口实现与执行器词汇);kernel /
  one_dragon 不感知基类(与「kernel 零 import 具体策略类型」同款纪律,
  静态锁先例在册)。
- 依赖方向:operations → cw_game_ports 协议 ← obs/sim 实现(两者实现协议);
  kernel 被所有人依赖、不依赖任何上层。
- **sim 驱动基类的依赖边裁决(F8,拍死)**:sim 驱动基类生命周期会新增
  sim→operations 依赖边(现状 sim 零 operations import)。三选:
  ①sim→基类直依;②runner 装配注入;③**app 根新增 sim-driver 装配模块**。
  **拍死 = ③**:装配边界归 app 是分包矩阵既裁决(DESIGN 分包 §3.2
  「app 依一切」;decision_assembly 同款先例在册)——sim-driver 住 app 根,
  同时 import operations(基类)与 sim(引擎/端口实现),**sim→operations
  边不产生**;基类经 cw_game_ports 协议触达两域实现(协议 as-built 落点 =
  CW 根 application/currency_war/cw_game_ports.py——F8 三处说法统一,
  清除「kernel 桶」表述;若评估应搬迁 kernel,归开放问题 A5 显式申报),
  依赖
  方向保持「operations → 协议 ← obs/sim;app → 一切」。①否决理由:破坏
  sim 桶零上层依赖现状;②否决理由:与③等价但装配点散在 sim 多入口
  (runner 批量 CLI 与 cw_sim 模块入口并存)——③单点装配胜出。sim-driver
  的职责 = 构建引擎局、安装 sim 端口实现、把基类驱动的生命周期驱动器
  套在引擎段序上(段边界按 §3.2 翻译)。
- 基类不含策略语义、不含画面知识:画面知识(锚/区域/交互时序)在实机适配器,
  引擎知识(段序/节点类型)在 sim 适配器,判据在策略器。

## 6. 动作 op 基类(与观察侧对称)

> 本节 = 适配器②的完整契约,与 §2 观察端口契约同等待遇:意图标准化(§6.1)、
> 实机动作适配器(§6.2)、sim 动作适配器(§6.3)、落地登记统一(§6.4)、
> as-built 衔接承诺(§6.5)、动作清单表(§6.6)。

### 6.1 意图标准化(统一意图词表)

策略器输出统一「意图」词表,**两适配器消费同一意图类型**——这是动作侧
「只分叉在适配器」的前提。

- **词表载体现役已统一,本架构只做契约化申报**:
  - 备战线意图 = `PrepAction` 词表(kernel/cw_prep_actions.py:
    ClickSpheres / OpenBox / OpenTome / PickBoxCard /
    SellBench / SellDeployed / DeployMove / LevelUp /
    OpenShop / StartBattle / RunDeploy /
    RunEquip / RunTools);
  - 商店线意图 = `Action` 词表(kernel/cw_state:BuyCard / LevelUpShop(is-a
    LevelUp) / RefreshShop / SellBench / SellDeployed(:749) /
    DeployMove(:650) / PickEvent(:694——decide_invest 契约返回类型即它,
    锚 cw_strategy.decide_invest 签名:163-167) / CompTransaction /
    FillSpec(:720——人口缺口填位描述,CompTransaction.fill 元素/独立填位
    动作共用,非 Action 联合类型成员) / CloseShop /
    SwapDeploy(:769,发射面退役 = as-built 事实申报,见 §6.6 同行——
    成员保留,禁静默缺席));
  - 事件线意图 = 各 pick 类型(kernel/cw_events:EncounterPick /
    SupplyPick / MegastarPick / PartnerPick / PlannerPick …)。
- **词表枚举为节选(F6)**:上列三行是节选非正本——**词表正本 =
  cw_state/cw_events 全量 action class 清单**,验收挂 AST 扫描;A7 覆盖度
  盘点把「§6.1 词表枚举 vs 全量 class 清单」列入对账面(开放问题 A7)。
- **统一性证据(已成立,非新建)**:sim 引擎消费的就是同一批类型
  (engine_p1 对 decide_shop_screen 出口的 BuyCard/LevelUp/RefreshShop
  逐动作执行;decide_shop_screen 驱动器经逻辑态推算推进
  同一批类型——前身 = cw_state.simulate 前瞻消费,已随 T-163 删除)——「意图类型两域同一」今天已真,缺的只是把它升格为
  端口契约并接口化执行面(§6.3)。
- **词表纪律**:新动作类型入词表 = 先改契约(两适配器同批给映射)再落码;
  禁止适配器私有动作类型(实机造一个 sim 不认识的意图 = 分叉复发)。
  控制流类动作已整体退役出词表(DeferSpheres/BailToOuter 等随词汇清理批
  删除;overlay 让位 = 环入口直接交回外循环,空批交回语义承载无动作帧)。

### 6.2 实机动作适配器(点击链)

实机适配器② = 现役点击/等待/画面流转链的封口。每个意图类型申报一张
「动作映射」:**点击链**(怎么落)。**验真锚(怎么确认落地)自 v12 起
退役**(T-223 用户终裁 2026-09-10 最严读法):适配器只管机械执行,不做
落地判定——「是否落地」不是适配器的输出,落地判定完全归观察侧 reconcile
对账(逻辑直写值 vs 下一帧实读,观察赢——两态制)。逐动作映射细则见
§6.6 清单表:

- **点击链载体**:PrepActionExecutor(备战单动作执行器,CwScreenPrep 持有)、
  cw_op_buy_cards(买/刷执行链;其 inline 执行落地门登记件收编归 §6.4)、
  cw_op_deploy / cw_op_equip_all(拖拽族)、_open_shop_phase(商店单动作
  循环 + 逻辑态直写)、confirm_and_verify / safe_click(_overlay_confirm,浮层
  确认;其「验关重读」判效面拆除归批 1 同窗,C 族)、run_supply_node
  (补给真两步)、launch_prepared_battle / StartBattle fallback(出战/
  跳过发射位)。
- **验真锚退役与迁移路径**(v12;现役判效面 as-built 照录,禁按旧语义
  新写):原「验真锚模式」(与「点了≠成了」纪律同源,
  od-dev-write-operation)= 出战/跳过 = 备战标识消失;刷新 = 牌名集变化
  ∨ 金币扣减(点击核对);买卡 = 金账对拍 + 期望态对账
  (compare_buy_expect)+ 落槽 pixel-diff(new_bench_slots);部署 =
  paddle 部署数变化;装备 = 期望态核对(compare_equip_expect);浮层确认
  = overlay 标题消失(lcs 阈值)。按判定性质拆两半处置:
  ①**期望态对账族**(compare_buy_expect/compare_equip_expect)= 本就归
  观察侧闭环(下一轮 reconcile 实读覆盖,观察赢——两态制),
  语义保留、归属确认观察侧;
  ②**执行侧原地判效**(点击后重读判「是否生效」+ 未生效重试:备战标识
  消失/牌名集变化/落槽 pixel-diff/部署数变化/overlay 标题消失)= 验证
  违规面(清查报告 A/B/C/D 族),拆除归批 3 同窗;「点了≠成了」纪律的
  承接形态 = **发出即职责完成 + 下一帧 reconcile 对账**(不当场断言成功
  的纪律保留,判效权移交观察侧),不是适配器内重读;
  ③拆除后的落地事实由观察侧 reconcile 供给(失配 → 纠偏/缺陷台账留证,
  §6.5-1);判效面已落码拆除,本节保留为拆除前语义出处锚(判读旧遥测行时用)。
- **改造要点**:映射表声明式(意图类型 → 点击链函数),散在 op/handler
  内的过程代码逐步收拢;适配器输出 = 机械执行完成(发出即职责完成,
  调用方不问成败——执行签名成败回执 (progressed, detail) 随 T-223 退役,
  on_outcome 触发 = 单一发射口发射即触发,§6.4);未生效重试/拉黑/安灯
  类结构不归适配器(验证违规面拆除归批 3;安灯删/拉黑删 = 批 0 三裁定
  M4/M5),缺陷面归观察侧对账缺陷台账留证。

### 6.3 sim 动作适配器(引擎动作应用)

sim 适配器② = 引擎动作应用的接口化包装。**核心件已存在**:动作语义逻辑态推算
`cw_state.simulate`(前身契约,已随 T-163 删除;现行单一转移函数 = `apply_shop_action_logic`,decide_shop_screen 驱动器消费)+
引擎对动作的真值应用(扣金/落席/合成/重抽牌/部署/装备/出战/coarse 战斗)。
缺的只是接口化——包装成与实机版同一接口:

- **协议位现成**:cw_game_ports.CwActionSink.execute_action(ctx, action,
  env) → ExecResult(applied / income / verification / observed)——sim
  实现 = 引擎 apply + 动作语义逻辑态直写;实机实现 = 现役执行链封装(T-120
  批 0 已立该二分,本架构给消费规格)。
- **applied 语义两域分轨(T-223/F11 修订,v12;原「两域对齐」申报
  退役)**:sim 侧 applied 真值保留——规则性拒绝(如满栏非合成拒买,
  门)是动作应用语义,引擎拒买分支照旧;实机侧发射型恒真,
  不携带落地判定——规则性拒绝的实机承接 = 策略层 发射前置谓词
  (发射前拦截),门漏判的无效买入由下一帧 reconcile 失配暴露(纠偏/
  缺陷台账,§6.5-1)。两域申报分轨、非对齐;协议字段形随批 3a 落码钉死。
  实机特有的「点击落空」面 sim 结构性为零(环境替身边界申报,cw_game_ports
  docstring 在案),ExecResult.applied 不假装表达它。
- **applied 提取机制申报(F15/R-N)**:sim 侧 applied 的提取载体二选一
  (实现批钉死并测试锁)——①`GameState.action_log` 回执(cw_state.py:263,
  引擎动作应用的既成回执通道,cw_evolution 消费先例);②执行前后状态
  差分。契约不变:提取机制属 sim 适配器内部实现,ExecResult.applied 的
  语义(规则性拒绝同判)不受选择影响。
- **恒 paid 不对称申报(A6/R-N,双开裁决附带)**:sim 侧触发
  record_refresh_execution 时,免费判定输入(免费刷新余额)结构性为
  None——免费闸的**免费腿在 sim 结构性不触发**,刷新计数恒走 paid 分支;
  这是已知不对称而非缺陷,申报面 = R8 批辖域申报的一部分(sim 的
  paid_refresh_count 读数含「未建模免费判定」的系统性口径,sim/实机
  跨域对读计数类键前必核)。
- **sim 侧禁止绕过意图词表**:引擎内部直接采样决策结果(不产生意图对象)
  的现状点 = 分叉(遭遇不调 decide_encounter、补给直调 kernel 函数绕过
  策略器接口;部署/装备内嵌块不经 decide_prep_screen——§1.2 病例 4)——
  收敛任务 = §7-T5。

### 6.4 执行落地登记统一(on_outcome 钩子)

**任何动作发射,实机/sim 两路径经单一发射口触发同一套登记**(T-223
用户终裁 2026-09-10 最严读法,v12:两 fire 口 fire_outcome_hooks/
fire_emit_hooks 合并为单一发射口;落地回执门〔OUTCOME_TRIGGER_LANDED
型〕退役——发出即职责完成,登记在发射时点触发;「动作是否落地」的
判定完全归观察侧 reconcile 对账)。收编对象 = 批次二/三散落的
「执行落地门」inline 钩子(现役接线点括注;「落地门」 = 现役 as-built
接线点名,收编后触发前提 = 发射):

| 登记件 | 现役接线点(散落处) | 收编后 |
|---|---|---|
| 刷新执行事实组 record_refresh_execution(total/paid/免费余额,免费闸) | cw_op_buy_cards 执行落地门(批次二) | on_outcome(RefreshShop 发射)统一触发 |
| 效果账本计数 bump_key(CounterKey.REFRESH@刷新回执 + BUY@购买回执) | cw_op_buy_cards 执行落地门(批次三件④) | 同上,与 record_refresh_execution 同点成组 |
| 合成升星逻辑态直写 detect_merge_upgrade → write_logic(bs.bench, 逻辑态推算 BenchView) 直写(两态制) | BuyCard 执行落地门逻辑态直写点(批次二扩单①) | on_outcome(BuyCard 发射)触发直写;实读覆盖归下一 reconcile 观察赢(不变) |
| 免战牌递减 consume_use(归零移除) | prep_actions `_launch_attempt`「按钮-跳过」发射落地回执(批次三件⑥) | on_outcome(跳过发射)触发 |
| 节点屏刷新计数组·遭遇(encounter_refresh_used write_logic,随点击置位不等验效) | 已收编本面(试点步骤 2 接线,注册表在册):触发点 = 刷新链两路径共用分派面,原 inline 位(handle 置位 :177-179/写端 :190-194,批次三件⑦接)随迁,登记语义不变(§6.5) | on_outcome(遭遇刷新点击)触发 |
| 节点屏刷新计数组·策略屏(strategy_refresh_used 逐卡 dict[str,int] write_logic,随点击置位不等验效) | 已收编本面接线(T-8 策略屏迁移批):刷新链点击处经 `_emit_refresh_click` 单一分派面发射(触发点唯一,两路径共用),写端逐位随迁钩子体——原 inline 位(handle 发射即记 :265/逐槽 :281-287,批次三件⑦接)随迁,登记语义不变(§6.5) | on_outcome(策略屏刷新点击,逐卡键入账)触发 |

- **钩子契约(T-223 修订,v12)**:on_outcome(action, outcome, evidence)
  ——成败回执面退役(ActionOutcome.progressed 与端口回执 (progressed,
  detail) 均退役,调用方不问成败);outcome 携带面 = sim 动作应用语义
  (applied 真值/income/verification,§6.3 分轨申报),实机侧发射型不
  携带落地判定;钩子集按意图类型注册(RefreshShop → 刷新计数组 +
  bump_key;BuyCard → 合成升星逻辑态直写(write_logic)+ BUY bump;跳过 → consume_use;
  ……);基类在 act() 发射后统一调用,**实机/sim 两条路径走同一份钩子
  代码**。
- **触发时点轴(R-E;T-223 最严读法重写,v12)**:原两型制(落地回执门
  〔默认〕+ 发射型〔例外〕)收敛为**单一发射型**——发射即触发,发出即
  登记。**落地回执门(OUTCOME_TRIGGER_LANDED 型)退役**:原默认型在册
  成员(刷新执行事实组/bump_key/合成升星逻辑态直写/免战牌 consume_use)随
  批 3a 改发射时点触发,其「未落地不计数」防线由观察侧 reconcile 对账
  承接(逻辑直写值 vs 下一帧实读,失配 → 纠偏/缺陷台账,观察赢——
  两态制);落码前
  现役门语义照旧(与批 3 同窗切换防空窗)。**发射型在册两件(F3)口径
  续行不受影响**(它们本就是发射型,置位时点/防重入口径逐字保持):
  ①遭遇刷新计数 encounter_refresh_used(refresh_click 证据,现役语义 =
  CwScreenEncounter.handle 置位语句 cw_screen_encounter.py:177-179「发出
  点击即置位,防点偏未生效重入屏反复尝试」、BoardState 写端 :190-194,
  验效失败帧仍 +1);②策略屏逐卡刷新计数 strategy_refresh_used(逐卡
  dict[str,int],随策略屏刷新点击置位、不等验效;写端已按本面接线
  (T-8 策略屏迁移批)= `register_outcome_hook` 注册件 +
  `_emit_refresh_click` 单一分派面发射,原 inline 写端(handle 发射
  即记 :265/逐槽 write_logic :281-287)逐位随迁钩子体,值/evidence/
  produced_by 逐位对拍锁在册;记录模型设计 §3.4.4,测试锁
  test_cw_game_state_batch3.py:341 在册)。新登记件入册一律发射型,无选型申报面(原「申报所属型、
  禁静默选型」纪律随两型制退役;发射时点逐件申报的纪律保留)。
  **v10 轴扩展申报:第三型「边界型(boundary)」不受本次退役影响**——
  流程边界事件触发的观测锚(进节点/进位面/结算),非动作发射辖域,触发
  点 = 流程边界(画面分派完成/过渡相位处理/结算观察写端);定义、登记
  纪律与在册成员见 §12(动作类锚自 v12 起沿用发射单型)。
  **§12 联动申报(T-225 边界:禁静默改 §12)**:§12.2/§12.3 对「§6.4 轴
  landed 型」及两 fire 口的引用面(buy_landed/sell_landed/refresh_landed/
  levelup_landed/box_opened/battle_start 等动作锚的触发时点型列、
  §12.5-1 触发口表述、§12.6-H6 两 fire 口前提)候锚实现批①联动修订——
  锚行的 landed 语义(落地事实时点登记)在发射单型下的生产机制(观察侧
  reconcile 供给落地事实 or 锚型重申报)随该批钉死,本版不改 §12。
- **apply_action_outcome 的非登记职责留守执行器(R-J)**:现役执行器的
  动作收尾函数除登记件外还承担**非登记职责**——动作语义逻辑态直写推进/
  shop_state_frame 帧推进/guard_expected_vs_tracked 期望态守卫/S1 误标
  检出/visit 级账本/journal 行(未落地也记)——**这些不随 on_outcome
  收编**,留守执行器原位;收编面 = §6.4 表登记钩子全量行(节点屏刷新计数
  组一行拆两条映射,F3),非执行器收尾
  函数整体搬迁。**收编时序挂账**:登记件(经验期望账本 LevelUp 直击/
  OpenShop 买波两通道)已随试点步骤 1 迁移为 CwScreenPrep 的 on_outcome
  注册;免费闸(record_refresh_execution)/免战牌 consume_use 等**执行链
  共链登记件**(新旧路径共用同一执行体,迁移即生产行为变化)挂账至
  等价门通过后的执行器批——零行为变更前不迁移,后续批(含步骤 2 sim
  接线)不得按本表字面提前迁移。**协议变更同窗申报(T-223)**:基类协议面变更(两 fire 口合并单一发射口/落地门退役/回执退役)与执行器验证链拆除同窗落码(批3+批3a)——防「登记门已拆、发射口未并」的语义空窗;登记件迁移时序仍按本挂账执行,不因协议变更提前。B5-② 的断言面据此限定为「登记调用点
  零残留」(不主张执行器职责清零)。
- **sim 侧从「无登记」变「同登记」**:现役这些钩子只在实机链触发;统一后
  sim 引擎动作发射同样触发——sim 的 BoardState 刷新计数/升星预期/免战
  递减开始被维护。这是**记录面新增**(零 rng 影响,不改引擎真值演化),
  但 sim 档案的 bs 读数从此可对拍,申报面见 §11-R8。
- **防双计纪律沿袭**:on_outcome 只写记录(BoardState/账本),不改引擎
  真值——sim 引擎对金/席位的真值推进照旧;「禁 logic 直写金币防双计」
  (记录模型设计 §4.1 九卡纠偏)同款纪律适用。

### 6.5 与批次二/三 as-built 的衔接(登记语义不变承诺)

落地门钩子收编**不得改变登记件语义**——以下已锁语义照旧,收编只是位置
从散落 inline 变为基类钩子(触发前提自 v12 起按 T-223 改发射语义,见
第 1 条):

1. **未落地不计数 → 发射即登记 + 对账纠偏(T-223 改写,v12)**:原承诺
   「执行落地判定先行,progressed/applied 是 on_outcome 的触发前提」随
   落地回执门退役废止;替代防线 = 发射即登记 + 观察侧 reconcile 对账
   (逻辑直写值 vs 下一帧实读,失配 → 冲销/纠偏/缺陷台账留证,观察赢
   ——两态制)。RefreshShop
   执行事实组、bump_key「只推进 duties.track 条目」的计数正确性改由对账
   通道承载(对账族改消费观察侧 reconcile 落地判定,批3a 落码);落码前
   现役门语义照旧(同窗切换防空窗)。
2. **免费闸**:免费帧不写 paid_refresh_count 并消耗免费余额(下限 0)
   ——record_refresh_execution 行为口径逐字保持,免费判定输入仍由执行侧
   按免费余额/效果账本判定后传入。
3. **同节点去重**:效果账本 tick_node 的去重与「登记当节点不推进」守卫
   原样保留(cw_loop 备战分支挂点不动,不属 on_outcome 辖——节点级事件
   非动作级)。
4. **随点击置位不等验效(发射型两件口径续行;T-223 后发射型 = 唯一型,
   本条从「例外」转为常态口径,§6.4 触发时点轴在册成员两件,F3)**:
   遭遇刷新计数(encounter_refresh_used)与策略屏逐卡刷新计数
   (strategy_refresh_used,同型同口径)都在**点击时点**置位、选择落地不
   置位(防「点偏未生效→重入屏再试」的口径不变;on_outcome 的触发时点
   = 点击发射即申报 refresh_click,验效失败不影响该登记——与现役逐字
   一致,不受本次退役影响)。
5. **逻辑直写标准通道(两态制)**:原「write_logic 豁免面不扩散」
   的申报制随两步机制废除一并解除——凡按游戏规则推算的写入统一走
   write_logic(策略器立即可读),非免检:字段值之后仍受观察覆盖辖
   (观察赢,失配 = 推算 bug 缺陷留证)。原预期条目表语义
   (last-wins/group_id 全有全无/confirm_point 绑定)已随条目表废除,
   on_outcome 收编不涉及。

裁决归属:批次范围枚举的正本仍是记录模型设计 §8.7;本收编是**接线点位置
迁移**,不重写批次范围;范围与钩子清单的对应关系以 §6.4 表为准(§10.3)。

### 6.6 动作清单表

> 格式与 §7 逻辑计算清单表同源。现状归属四值:**kernel 单一源已就位** /
> **引擎私有需收敛**(sim 侧私有实现或绕接口)/ **实机私有=合法保留**
> (点击链/识别机制,非数学推导)/ **sim 未建模**(校准层边界,如实申报)。
> 「登记钩子」列 = on_outcome 触发的登记件(空 = 该动作无落地登记;
> 触发时点自 v12 起统一为发射,§6.4/T-223)。
> 「验真=」标注(v12 申报)= 拆除前判效面照录——验真锚已退役
> (§6.2),各动作的落地确认语义承接归观察侧 reconcile 对账;执行侧原地
> 判效已随 2026-09-13 状态收敛迭代落码拆除,本列禁按字面新写判效面。

| 意图类型(词表符号) | 实机适配器映射(点击链) | sim 适配器映射(引擎调用) | 落地登记钩子(on_outcome) | 现状归属 |
|---|---|---|---|---|
| BuyCard 买牌 | cw_op_buy_cards:点卡身→确认;验真=金账对拍 + compare_buy_expect 期望态对账 + 落槽 pixel-diff(new_bench_slots);满栏自动多买上限 = 3−(已有 mod 3) | 动作语义逻辑态直写(BuyCard;前身 = cw_state.simulate,已删) + 引擎 apply(扣金/落席/合成) | 合成升星逻辑态直写(detect_merge_upgrade→write_logic)+ BUY bump_key + pending_buy_expect 暂存 | 逻辑态直写=kernel 单一源已就位;满栏上限口径=merge_mechanics(对账项,同 §7 行 3) |
| RefreshShop 刷新 | 点刷新钮;验真=牌名集变化 ∨ 金币扣减(点击核对,不存快照字段) | simulate(RefreshShop) + 引擎重抽五张(draw_shop,rng) | record_refresh_execution(免费闸照旧)+ REFRESH bump_key | 计数登记=kernel 已就位(接线点收编中);重抽=引擎校准层合法 |
| LevelUp / LevelUpShop 升级 | 循环点「购买经验」至 level+1(prep_actions);验真=等级 +1 ∨ 金扣减 | simulate(LevelUp) + 引擎等级/XP 推进 | 升级标记挂点(prep_actions 既有,经属性归一接账本);XP 簿记=执行侧保留 | 单击价/击数推导=kernel 已就位(xp_click_cost/clicks_to_next_level,FALLBACK 遗留随批次二) |
| SellBench 卖备战席 | 拖拽至卖出区;验真=备战席少该牌 + 退款金入账(期望态对账) | simulate(SellBench) + 引擎退款(cw_state.sell_refund 口径) | 拖拽期望态对账(compute_drag_expect,执行侧保留) | 退款公式=kernel 已就位;sim 卖牌退款调用点对账=§7 行 4 |
| SellDeployed 卖场上角色(两线词表成员:PrepAction + Action cw_state:749) | 同拖拽链 + 装备期望态(_equip_expect_for_sell→compare_equip_expect);**换血卖通道 = CwScreenDeploy._sell_offtarget_deployed(cw_op_deploy.py:1564,主链活跃)**——部署腾位的 off-target 卖出经本通道(CwOpSellOffTarget op 已下线预登记:文件头自注「当前零调用,清理由 _sell_offtarget_deployed 承担」,重接前非活跃通道) | simulate + 引擎退坑 | 拖拽/装备期望态对账 | 同上;换血卖通道=实机私有合法(执行通道,非数学推导) |
| SwapDeploy 换血部署(商店线词表成员 cw_state:769) | 无现役点击链 | 无现役引擎调用 | 无(**负向锁申报 F7:登记槽 v3_pending_rollback 非空 = 告警**) | **发射面退役 = as-built 事实申报(F7,无退役裁定 ADR 在案,不引裁定)**:发射面 = 发射器不再被策略器发射;**登记半边仍活**——flow 谷底回滚臂(flow._process_settlement_strategy_half:287-297,锚 rollback_weakest 调用处 :293)仍构造 SwapDeploy(cw_evolution.py:1596 = 构造点非裁定出处)写入 v3_pending_rollback(StrategyState 声明 mandate_state.py:124),全仓零消费(1 写 0 读)= 半边活口;测试锁 test_cw_comps_library 仍断言 rollback_weakest 返回 SwapDeploy。词表成员保留,显式申报禁静默缺席、**禁静默复活**;重接时两适配器同批补映射(词表纪律 §6.1) |
| DeployMove / RunDeploy 部署 | 拖拽 bench→行槽(CwScreenDeploy,槽位 SIFT);验真=paddle 部署数变化(dep_pre 对照) | simulate(DeployMove) + 引擎部署块(轮末,序;**策略选择面 sim 零覆盖**,§1.2 病例 4) | 部署对账(dep_delta 记账,执行侧保留) | 装配源契约=钉死(尾批独立重验,§10.1);策略面收敛=T5 扩域 |
| RunEquip 穿装备 | 拖装备→角色(cw_op_equip_all);验真=装备归属期望态(compare_equip_expect) | simulate + 引擎装备分配(equip_allocation,与执行器同源;策略选择面同上零覆盖) | 装备期望态对账 | 分配逻辑两域同源已就位;穿着即合成等观察收口(记录模型 §4.1 豁免);策略面收敛=T5 扩域 |
| RunTools 用工具 | 拖装备→冶金炉 / 拆装扳手(cw_op_tools);验真=装备区变化 | 未建模(TOOL_GRANT_INJECT 注入通道=校准层) | 无 | sim 未建模=合法(工具为跨局持存物品不建模,申报在册) |
| OpenBox 开箱 | 点箱→确认;验真=箱槽变空/新内容 | 未建模(sim 无箱实体——记录模型按实机真值箱占席,合成口已申报) | 无 | sim 未建模=合法 |
| ClickSpheres 点奖励球 | 批式点球 + 后续观察自愈;席满拦截=前置谓词(bench_free>0 ∨ 球均不占席) | 无对应(奖励球=实机交互机会信号,sim 无球实体) | 无 | 记录层面=点球不改席占位等观察覆盖(记录模型 §4.2);sim 无=合法 |
| StartBattle 出战 | 点出战;验真=备战标识消失 | 引擎战斗段(coarse 两态模型,按节点类型) | 无(结算登记归 apply_settlement_cover 观察写端) | 战斗结算=kernel cw_coarse_battle 已就位 |
| 跳过(免战) | 点「按钮-跳过」(StartBattle 发射位 fallback) | 未建模(免战牌 sim 侧未建模) | consume_use(归零移除;未登记返 None 零动作) | 登记件=kernel 已就位(接线点收编中);sim 未建模挂 §7-T4 收敛纪律 |
| OpenShop / CloseShop 开关店 | _open_shop_phase 单动作循环 + 逻辑态直写(MAX_REFRESH 硬墙)/ 点收起;验真=商店锚出现/消失 | 引擎商店段边界(shop_state_frame 写点);CloseShop=驱动器恒可用终结 | 无 | 流程编排=实机私有合法;段边界申报挂 §11-R1 |
| 事件选择(Encounter/Supply/Megastar/Partner/Planner/WishTrial/StarTome/BoxCard/EquipPick/Expert) | 点卡身选中→确认(confirm_and_verify 验 overlay 消失);中间勿插空白点击 | decide_* 调用 + 引擎事件落定;**遭遇未接(T5)、补给直调 kernel 绕接口(T5)** | chosen_* write_logic 豁免;遭遇刷新计数(随点击置位) | 决策面收敛=T5(§7);点击链=实机私有合法 |
| 投资选择(InvestStrategy / InvestEnv) | CwScreenInvestStrategy / CwScreenInvestEnv(选卡+确认+刷新链) | decide_invest 注入段(已接策略器接口) | active_env / active_strategies write_logic + 效果账本登记 + apply_effect_burst_grant(分列申报:仅策略屏已接,`cw_screen_invest_strategy.py:602-604`;环境侧无一次性施放语义——by-design 申报,非欠账) | 登记件=kernel 已就位;sim 经济聚合收敛=T4(§7);效果施加考题详见 §8 |
| 选职级(简报相位,§4.4) | 现役=入口流固定策略(CwEntryStart「返回最高职级」→「开始对局」);统一后=两域同源(kernel 缺省函数「恒选最高」),调用点两域各异——实机=CwEntryStart 入口流内(§4.2,替换硬编码;相位 1 策略口对实机只观察核对 bs.selected_difficulty)(A10 已裁决选项②+F5 调用点修正;接口成员升格待分化需求) | Engine.new_match 生成的职级选项 → 同一 kernel 函数(sim 调用点=引擎开局);sim 现役未建模职级,缺省函数落地时同批补齐 | bs.selected_difficulty 观察写端(难度确认屏);relay 镜像随真写端自然跳过 | 两域同源=kernel 缺省函数(A10 已裁决);实机导航链=实机私有合法(循环外) |

## 7. 逻辑计算清单表

判据:凡「相同输入必得相同输出」的确定性推导,实现必须唯一(kernel 单一
源),实机与 sim 都调它。三档现状:**已就位**(kernel 已是单一源且两域已
委托)/ **引擎私有需搬迁**(sim 有私有实现或内联式)/ **实机私有需下沉**
(逻辑散在实机链、缺 kernel 载体)。每项给一条搬迁任务(T 编号供引用)。

**任务书纪律(F7)**:T1-T5 执行前必须做**全仓符号扫描**(对任务涉符号做
AST/全文检索,枚举全部定义与消费点)——「两份/三份/已就位」类计数断言
一律以扫描结果为准,禁凭起草时点记忆(实例:本表 T3 起草时计三份,对抗审
扫描抓出 engine_p2.py:39-55 第四份);扫描结果附任务书,漏点 = 任务书
不合格。

| # | 计算 | 现状(代码指针) | 标注 | 搬迁任务 |
|---|---|---|---|---|
| 1 | board 下档阈值 | kernel board_next_tier_of;obs computed 支(cw_observation)与 sim `_board_next_tier_of`(engine_p1)均薄委托 | 已就位(先例) | 无(保持委托结构,禁第三份) |
| 2 | 席空数/席满判定 | kernel bench_free_slots / bench_is_full;sim 席满观测键经合成口后供给(engine_p1) | 已就位 | 无 |
| 3 | 升星推算(买牌 3 合 1 逻辑态直写) | kernel detect_merge_upgrade + 容器规则通道逻辑态直写(simulate 前瞻推算链为前身,已随 T-163 删除);sim 引擎消费同一逻辑态直写 | 已就位 | 对账项:sim 合成路径与 detect_merge_upgrade 的同名最高星签名口径一致性,随迁移批次二扩单①回归覆盖 |
| 4 | 退款公式 | kernel cw_state.sell_refund(1★=cost / 2★×3 / 3★×9 / 4★×27;star≥2∧cost≥2 再 −1 手续费) | 已就位(公式面) | 对账项:sim 卖牌退款调用点核对——禁引擎内联倍数表,违者按本表收敛 |
| 5 | **轮首收入三支**(base / interest / streak + 修饰) | **kernel 收入函数族已落(T1a)**:reward_base_gold / loss_compensation_base / round_start_income / RoundStartIncome(符号名锚 kernel/cw_economy);引擎收入段改调 + live 写端指派 = **T1b 未接**;败补口径 = **数据不足定谳**(决策3,待玩家确认 + 补采口径在案);口径申报与 T1 拆分见 §7.1 | 部分就位(kernel 载体已落 / 引擎接线未接) | **T1b(接线批)**:sim 引擎收入段改调 kernel 函数族;实机 live 写端指派接同一函数(与 §10.1 尾批件合并执行);**假环境收入重述同批切源**——sr-od-test `fixtures/cw_fake_game/rules.py` 的 `income_for_round` 奖励轮 base 现按 round_num 单键直查 `REWARD_BASE_GOLD_BY_ROUND`(`reward_base_gold` docstring 明文的 hazard 形态:P2r1 误返 3,真值 5;FakeMatch 已支持 P2 段,hazard 域可达),切 `kernel.round_start_income`(event=0 语义保留,败补口径按在册「数据不足定谳、待玩家确认」申报)——切换致 P2 奖励轮 base 3→5 = 假局经济分布变更,随批升 env_version 申报;T1a 辖域排除三分量(gold_per_node 族 / gold_per_boss_node 族 / 战斗表现条件类)随 T1b 定承载(分量扩参 or 调用方聚合单列,§7.1 申报)。**net_income 决策消费点(F2 翻正,6 处,符号名+行号双锚)**:mandate_v1/shop.py ×4(1016/:1364/:1987/:2148)+ mandate_v1/encounter.py:240(决策消费)+ cw_economy.py:1047-1048(_upgrade_ul_threshold_ok 内 loss_exact 前置,P47 递推 c_int=loss_exact 调用处)——处置已按 决策2 委托改造收口(决策近似口径申报 = §7.1 决策近似口径行) |
| 6 | 利息(gold, cap)+ flat 修饰 | kernel cw_economy.interest;sim 收入段内联 `min(cap, gold//10)+flat` | 引擎私有需搬迁 | T2:sim 收入段利息分量改调 kernel 函数(并入 T1 函数体) |
| 7 | overlay 查询(xp_per_refresh 等按持卡名查 STRATEGY_EFFECTS) | **四份拷贝**:engine_p1 两份重复定义 + runner.py 一份 + engine_p2.py:39-55 一份(对抗审扫描勘误,原计三份) | 引擎私有需搬迁 | T3:提为 kernel 单一源查询函数,**四处**改薄委托(机械改动,低风险) |
| 8 | 效果账本推进(tick / 桥三分:burst / per_node / 容量逻辑态直写) | kernel cw_game_state 桥已就位(批次三补单⑧);sim 引擎经济聚合走 aggregate_economy 内联(收入段 _icap/_flat/gold_per_node) | 引擎私有需收敛 | T4:sim 效果修饰面收敛到账本桥/同源查询(与 T1 同批)。aggregate_economy 作为注册表查询面可保留;**修饰的应用点必须单一**——sim 若建模倒计时类效果,必须消费 kernel tick 挂点,禁引擎私有倒计时 |
| 9 | 经济决策量(refresh_cost_effective / xp_click_cost / clicks_to_next_level / _expected_level) | kernel cw_economy;XP_CLICK_COST_FALLBACK 消费形态挂迁移批次二申报 | 已就位(遗留申报) | 无(FALLBACK 搬迁随批次二既有申报走,不另立任务) |
| 10 | 派生键归并 / 刷新计数组写入 | kernel cost_source_group / record_refresh_execution | 已就位 | 无(接线点收编归 §6.4 on_outcome) |
| 11 | 节点事件与备战决策面(遭遇/补给/选卡/**备战线**) | 实机:decide_encounter / decide_supply / decide_prep_screen 经策略器接口已接;sim:**备战线全程零覆盖(引擎不调 decide_prep_screen、不写 prep_obs_frame——部署/卖出/升级策略面测不出,§1.2 病例 4)**;补给直调 kernel 函数 decide_supply(cw_events)绕过策略器接口;遭遇不调(引擎内部采样);_event_gold 为 rng 校准层 | 部分缺位(策略面) | **T5(辖域扩,F1-③)**:sim 决策面统一走策略器接口——①备战线:引擎备战动作链改经基类生命周期调 decide_prep_screen(prep_obs_frame 由 sim 适配器①帧供给双落供帧,§2.4);②遭遇接入 decide_encounter;③补给改调 strat.decide_supply。均属有意行为变更,先过 §11-R3 裁决。_event_gold 属校准层(随机事件生成)非换算逻辑,合法保留。**注意(F7)**:动 decide() 段/收编面时,**禁把 v3_pending_rollback 当 bug 接上发射**(SwapDeploy 登记半边活口申报 = §6.6 同行,负向锁 = 登记槽非空告警) |
| 12 | 识别质量机制(gold 稳定门 / hp 双通道 / 难度放大) | 实机 obs 链内部 | 实机私有 = **合法保留**(适配器①内部机制,非数学推导) | 无 |
| 13 | 战斗结算(coarse 两态模型) | kernel cw_coarse_battle 单一源 | 已就位(sim 校准层;实机无此推导) | 无 |

### 7.1 收入口径申报表(T1a 批)

> T1 拆分:**T1a=kernel 单一源函数族**(已落 `kernel/cw_economy.py`);
> **T1b=引擎收入段改调 + live 写端指派 + 假环境收入重述切源**
> (fixtures/rules.py `income_for_round`,hazard 形态见 §7-T1 表第 5 行),
> 本表只记 T1a 后的口径归属。

| 口径 | 载体(kernel 单一源) | 辖域与公式 | 差异归属申报 |
|---|---|---|---|
| **记账口径** | `reward_base_gold(plane, round)` / `loss_compensation_base(plane, round, node_type)` / `round_start_income(...)` → `RoundStartIncome(branch/base/interest/streak/total)` | 平面感知键(P1 {1:3,2:4}、P2r1/P3r1=5、其余 5)+ 利息(gold,cap)+ flat + 连胜分量×win_reward_mult(含奖励轮)+ 败补基项(玩家裁定口径,待玩家确认——决策3);分支派发序=引擎 elif 序(supply→reward→败补→常规) | **记录/记账唯一口径**;sim 引擎接入=T1b,接线前引擎内联式为过渡形态;假环境(`rules.income_for_round`,自述「规则知识重述非第二实现」)是收入知识的另一份重述,其奖励轮 base 单键直查 = hazard 形态,切换同挂 T1b。**T1a 辖域排除申报(决策1)**:`gold_per_node`(定期福利/按劳分配/剩余价值)/`gold_per_boss_node`(特战资金族)/战斗表现条件类(剩余价值≤4 等)三轮首真实金分量**不在本函数族辖域**(签名无槽位;引擎 'invest' 键单列入账)——T1b 接线时以分量扩参 or 调用方聚合单列承载,二选一随 T1b 定;supply 支 base 取平面感知键=kernel 实现选择(正本 §4.2 只写「基础」未明示键,现节点序无数值差,节点序变异使 supply 落 r1/r2 时与引擎恒 5 分叉——键语义随 T1b 复核定谳) |
| **决策近似口径** | `net_income(round, streak_pre, lost_node_type)` / `round_base_income(round)` | base=reward_base_gold 的 **P1 规划投影**(传参简化:决策签名无 plane)、streak_gold(streak_pre)、败补=LOSS_GOLD_BY_NODE 类型表 | 与记账口径的数值差异:P2/P3 的 r1/r2 轮 base(P2r1 真值 5 vs 投影 3)与败补基项(平面键 vs 类型表)——**归属=决策规划近似,非口径冲突**;现役 6 消费点(mandate_v1 shop.py ×4 / encounter.py / cw_economy loss_exact 前置)全部传 streak=0/lost=None,近似不落值;等价性锁=sr-od-test test_cw_income_single_source |

裁决依据:方案审 F4-① 处置(a)委托改造(禁不裁决已闭合);F4-② 判别执行=数据不足定谳(结构性混杂+样本缺口,决策3,待玩家确认+补采口径在案)。

## 8. 投资环境专项(效果施加的数学单一源考题)

> 投资环境是「选择一次、整局生效、修饰多处」的典型效果载体,也是效果施加
> 链路上欠账最集中的位置。本节拆三件事:选择动作、局级事实记录、效果施加
> ——前两件现状干净,第三件是数学单一源原则(§1.1 要点 3)的最大考题。

### 8.0 建模现状盘点基线(A8 盘点批结论,已回填)

> 以下为 A8 盘点批(只读零改动)对 sim 引擎与投资环境注册表的逐项代码级盘点结论,
> 是本节后续设计的硬证据基线(证据行号见盘点批回传,关键锚随条标注)。

**前提纠正**:win_reward_mult **不是环境效果**——它是投资策略「伟大征服」的修饰
(STRATEGY_ECONOMY win_reward_mult=3.0,§1.2 实例 1);环境侧 PLAZA_PORTALS 83 条
**零结构化经济字段**(InvestmentEnv 仅 name/category/effect 原文/faction/source/
pick_value;EnvEconomyEffect 缺口在册,cw_investments.py:1213-1220)。→ 本节
「效果施加」的前置件 = **环境效果结构化词表**(收入类/节点替换类/XP 类/刷新类/
结构性五类),实机记录器与 sim 引擎同调**一个解析函数**——词表未立之前,「两域
同一套修饰」无处附着。

**建模现状矩阵**(六行,逐项已建模/部分/未建模):

| 项 | 现状 | 关键事实 |
|---|---|---|
| 环境选择 | 部分建模 | 双臂(freq 频次直采 / sink 真实判据三选一)+固定剧本注入;plaza 实选频次代理**非真实发牌机制** |
| 收入修饰 | 未建模 | sim 收入管道(engine_p1 :999-1049)**零读 active_env**;环境收入类效果(增发货币晶矿/蓝海+6金/二手市场等)无结构化载体 |
| 节点替换 | 未建模 | P1/P2 节点序列无 env 条件分支;且 sim reward=**零战斗不掉血**,与扑满「奖励型战斗」机制相反 |
| 经验修饰 | 环境侧未建模 | 成功经验 id138(+12XP×3 节点)零消费 |
| 刷新赠送 | 仅「轮岗」建模 | = sim 唯一有行为效果的环境机制(翻倍档分布=建模假设待核);长线利好刷价改写已删除 |
| active_env 载体 | **已建模全链** | session→state→BoardState relay→遥测→回放;消费面 sim/生产共享同一套函数 |

**现存样式参照**:active_env 消费面三通道(直通线资格 cw_intention.py:415 /
env affinity :953-957 / 扑满守卫 cw_reward_node.py:48)已是「sim 与生产同一套
函数」的现存先例——§8.2 修饰函数族的落点照此样式放大,不另发明机制。

**生产侧落点洞察(增量价值主张)**:生产侧从不计算收入(金=OCR 现读)——共享
修饰函数在生产侧的落点 = **对账/预测层**(预测金差分 vs 实读差分,缺陷台账武装),
sim 侧才是会计引擎。这决定了修饰函数族的接口设计:两域调同一函数,但消费语义
分「记录对账」与「引擎记账」两用。

**保真度边界(并入 §11-R10)**:invest=True 的 sim 局按频次注入全部 83 环境,
但仅 轮岗/扑满守卫/名字亲和 三通道有行为效果,其余环境=纯名字注入——env 相关
sim 结论的外推力边界显式登记,A8 盘点交付即为 R10 的先决闸(已过闸)。

### 8.1 三件事拆解

| 事项 | 现状 | 裁决 |
|---|---|---|
| ① 选择动作 | 标准事件屏 pick 形态:CwScreenInvestEnv(三选一 + 刷新链;decide_invest('env') 经策略器接口已接,§6.6 投资选择行) | 无欠账。**前置 = 备战屏 overlay 通道补档**(记录模型设计 §3.2.20 待采证在案:overlay 无独立建档、名/效果文本均无区域级锚——补档前该通道不作为 active_env 核对源) |
| ② 局级事实记录 | **批次二已落**:active_env 单次逻辑写豁免写端(记录模型设计 §8.7 批次二落位面「局级事实写端」)+ relay 载体中继镜像(`_feed_board_state`) | 无欠账 |
| ③ 效果施加 | **欠账所在**(§8.2/§8.3):环境侧结构化词表缺位(EnvEconomyEffect,cw_investments.py:1213-1220)+修饰函数族无载体+「注册表有值引擎零消费」字段族待裁决 | 收敛任务 = 词表五类落定(§8.2)→修饰函数族进 kernel(照 §8.0 active_env 消费面样式);字段裁决清单 = §8.3(衔接 T1a);批辖域 = 开放问题 A9 |

### 8.2 效果施加:环境效果结构化词表是修饰函数的前置件(A8 回填后重述)

§8.0 前提纠正改变考题形状:**环境侧当前没有可消费的结构化修饰**
(PLAZA_PORTALS 83 条零经济字段)——所以第一步不是「修饰函数进 kernel」,
而是**环境效果结构化词表**落定(EnvEconomyEffect 缺口补齐,
cw_investments.py:1213-1220 在册),按五类建模:**收入类 / 节点替换类 /
XP 类 / 刷新类 / 结构性**。词表是「实机记录器与 sim 引擎同调一个解析
函数」的前置件:词表未立,「两域同一套修饰」无处附着。

词表落定后的施加链(目标形态,与 §8.0 现存样式参照同构):

- **登记**:选卡时点进 effect_inventory(选卡登记挂点;触发面 = NODE_ENTER /
  PLANE_START 类 spec,kernel/cw_effect_inventory 载体在册);
- **施加**:解析+修饰函数族住 **kernel 单一源**(词表解析一个函数、修饰
  应用一个函数)——实机记录侧(对账/预测,§8.0 生产侧落点洞察)与 sim
  引擎侧(会计引擎:收入计算/节点序列生成/XP 推进)调**同一套函数**;
- **禁二份**:sim 引擎现役经 aggregate_economy 内联消费修饰(收入段
  _icap/_flat/gold_per_node)+ 注册表有值零消费字段族(§8.3 裁决清单)——
  收敛载体 = §7-T4(修饰应用点单一)+ §7-T1/T1a(收入单一源函数族批,
  进行中)。

**节点替换族的专项考题(盘点确认未建模)**:替换直接改写引擎节点序列——
sample_node_sequence / P2_NODE_SEQUENCE 与替换函数的关系(替换前后序
怎么生成、rng 消耗序怎么保持、扑满主题对结算键的影响怎么表达;**注意
盘点实证:sim reward=零战斗不掉血,与扑满「奖励型战斗」机制相反**,
替换建模若不动 reward 结算语义会造出新分叉)。修饰函数族入 kernel 的
批辖域(随 T1/T1a 同批 or 独立修饰批)= **开放问题 A9(前置 = 词表
落定)**。

### 8.3 「注册表有值引擎零消费」字段显式裁决清单

以下字段注册表有值、引擎零消费(sim 收入路径零读)或消费点已死——逐个
裁决,**要么接 sim 收入、要么 ADR 申报排除**,禁悬置:

| 字段 | 现状 | 处置 |
|---|---|---|
| win_reward_mult(伟大征服,STRATEGY_ECONOMY) | 唯一生产计算消费点=economy_score(cw_economy 符号名索引,现无生产调用 = 退役决策栈**死函数**;T1a 另增 kernel 计算消费点 `_streak_component`〔round_start_income 连胜分量〕,同为零生产调用) | **T1a 已落定(决策1)**:round_start_income 连胜分量×mult 参数化(kernel 半部),引擎消费=T1b;死函数清理建议保持(economy_score,防假消费误读——§1.2 病例 1 已按此勘误) |
| free_refresh_burst | 有值;sim 免费刷新侧消费面待核 | **T1a 未辖(决策1 排除申报,挂 T1b)**:接 sim 收入/刷新侧 or ADR 排除 |
| xp_per_node | 有值;sim XP 路径零读 | **T1a 未辖(决策1 排除申报,挂 T1b)**:接 sim XP 推进 or ADR 排除 |
| gold_per_boss_node 族 | 有值;sim 收入段零读 | **T1a 未辖(决策1 排除申报,挂 T1b)**:接 T1b 收入函数(首领节点触发,分量扩参 or 调用方聚合单列) or ADR 排除 |

裁决批衔接:**T1a 已交付**——win_reward_mult 隐式落定
(kernel 半部;引擎消费随 T1b),其余三字段挂 T1b,禁悬置状态保持,
裁决结论仍回填本表。

## 9. 迁移策略

### 9.1 分屏渐进原则

- 一次迁一个画面 op;旧路径保留到该画面的等价门通过;两路径并存期由
  cw_game_ports 装配点分流(「缺省 None = 生产直连」模式,不新建开关机制,
  符合 strategy-work「开关生命周期」对开关形态的收敛要求)。
- **并存面现状(末阶段正本对齐,T-8/T-47/T-48/T-45 交付后)**:装配点
  分流面已覆盖 cw_screen/ 全目录画面 op + cw_op/ 商店系三件(迁移面
  清零);生产仍恒走旧路径(装配点缺省 None,各迁移批生产行为零变化)
  ——并存期旧路径退役候批面 = 上述全量,退役归等价门(实机腿)通过后
  的后续批(实机验证候统一 state 门开启)。
- **验收门分主次(F2)**:①**主门 = 行为等价双腿**——(a)在册行为锁经
  op execute() 走新基类全绿(实机腿);(b)BoardState 写入流分域夹具对拍
  (实机 = 固定截图夹具 → 实机适配器 payload → bs 全帧对拍,回归 pin 钉
  payload;sim = 引擎真值 → 合成帧 → bs 对拍;细则 = 开放问题 B2);
  ②**次门 = 策略面回归哨兵**(原「回放门」降级改名):cw_replay --diff
  只重放 decide_shop_screen(cw_replay.py:4-9 用途声明/:55-91 快照重建/
  :254-255 调用点已核),不经过端口/基类/写入流——对试点(备战 op)
  近恒真,降级为「商店策略面回归哨兵」继续跑,不作为试点等价主证。
  另:**sim A/B** 对备战线现役无判读力(§1.2 病例 4:备战线 sim 零覆盖)
  ——T5 扩域落地前,备战 op 的 sim 腿结论辖域 = 引擎内嵌块行为分布
  (§5.1 申报),不作为该 op 的策略面等价证据。

### 9.2 第一个试点:备战单轮 op(CwScreenPrep)

选择标准(试点画面须同时满足):①五段结构已就位(观察/对账/决策/期望态/
执行已分段,基类化 = 抽提不重写);②观察漏斗单一(read_game_state 已是
唯一入口);③决策入口契约已冻结(decide_prep_screen 序列契约);④两域
决策面同路——**仅商店子相位成立**(sim 决策段与生产共用 decide_shop_screen,
哨兵可直接对拍;备战子相位 sim 现役零覆盖——§1.2 病例 4,不构成试点
前置,其补齐 = §7-T5 扩域随基类落地)。备战 op 四条全满足,是唯一同时
满足者。

迁移步骤:

1. 抽提基类:CwScreenPrep.run 的②对账段抽为基类共用代码(验证段不经基类
   承载,§5.1 用户裁定废除);①观察段
   改调观察端口(实机实现 = read_game_state + observe_full 封口;sim 实现 =
   synthesize_from_game_state 扩展 + 帧供给双落,§2.4);⑤执行段改调动作
   端口(意图→适配器,§6.2/§6.3),落地登记收编为 on_outcome(§6.4,
   登记件语义不变承诺 §6.5;触发前提 = 发射,T-223)。
2. sim 侧接线:引擎备战动作链改经基类生命周期驱动;段边界按 §3.2 翻译
   相位;申报面 = rng 消耗序不变(§11-R1)。
3. 等价门:主门 = 行为锁经 execute() 走新基类全绿 + 写入流分域夹具对拍
   (§9.1);次门 = 策略面回归哨兵(商店子相位)跑通;通过后跑 sim A/B
   一批(辖域申报见 §9.1)。
4. **余项收口完成态(T-8/T-47/T-48 交付,cw_op 挂账批 T-45 补齐)**:
   事件屏族/投资两屏/结算(战斗等待)/简报/BOSS 简报(T-8)、推进型变体
   11 屏(T-47)、收尾五屏(T-48)均已迁毕,cw_screen/ 全目录收口锁在册
   (AST 断言:凡 op 祖链达 SrOperation 者必为 CwScreenOpBase 后代);
   cw_op/ 商店系三件(CwScreenBuyCards/CwOpOpenShop/CwOpCloseShop)经 B4
   挂账批收编(T-45:open/close = 只读/导航变体,buy_cards = 旧体委托
   变体,五段映射申报住类 docstring),B4 判据第 1 条点名清单全量达成。
   **相位 1 深度统一仍待独立批**:kernel 选职级缺省函数落地 + 简报/
   难度确认屏写端切观察 + selected_difficulty 两吸收点注销(A10 已裁决
   选项②;前置 = 难度确认屏对局类型建档采证,§4.4 as-built 缺口)。
   **相位 1 统一的迁移面申报(F5)**:ctx.cw_selected_difficulty
   中转的**两个吸收点**并入该批迁移面——cw_loop._absorb_selected_difficulty
   (定义 :1071,调用点 :1068)与 cw_strategy_manager.establish_new_match
   (装配段:78-79,符号名+行号双锚);统一后由相位 1 观察写端接管,
   迁移批须逐点对账注销。

回退方案:装配点卸载端口(恢复 None = 直连现役路径);基类抽提是纯结构
重构,回退 = 分发点切回旧 op 类,git revert 单操作。

### 9.3 与迁移四批次的关系

本架构不重排记录模型设计 §8.7 迁移批次一~四与尾批的既定范围,只在其上
叠加:批次二(消费切换)产出的 strategy_input_state / 合成口 / 对账口正是
基类中段的原料;批次三(策略器状态归位)的 Snapshot 锚切换已落在
decision_assembly,基类 decide() 段直接消费其产物。与尾批的关系裁决见 §10.1。

## 10. 与既有件的关系裁决

### 10.1 尾批(装配对账)吸收/保留裁决

| 尾批件(记录模型设计 §8.7 尾批行) | 裁决 |
|---|---|
| 执行侧装配源切换 ~18 点(cw_op_deploy / cw_op_equip_all / prep_actions 期望态对账) | **保留独立执行**:切换须独立重验十四字段对齐面(帧新鲜度差域 + SIFT 分轨语义,「装配源契约钉死」)——该对账面属执行侧契约,与本架构的端口正交;基类化不吸收它 |
| 轮首收入三支 live 写端载体指派(候选 = effect_inventory 节点边界回执) | **被 T1b 吸收升级**:写端指派后直接接 kernel 收入函数族(T1a 已落,§7.1),一次接对(避免「先指派载体、再改公式」两道工序);sim 败补旧表修正与假环境收入重述切源随 T1b;分桶重放判别**已执行**(决策3 数据不足定谳,口径申报表 = §7.1) |
| cw_expected_state 簿记 | **废除**(两态制:expected_state 条目表拆除;op 逻辑效果 = apply_op_effect 字段直推,与观察端口正交面消失) |
| MandateState 别名清理 / advance_node(None) 生产挂点守卫 | 保留(机械清理件,与本架构无交) |

### 10.2 待实采挂账(记录模型设计 §5.1)在新架构下的归宿

「持续 N 个节点」型卡文(躺平,自然读法含登记节点)vs「接下来 N 个节点」型
(节省工位)两读法现共用 tick 守卫(登记当节点不推进),躺平方向系统性多冻
1 节点(remaining_nodes 零决策消费,现仅到期时点差一拍);实采定谳后按卡文
逐卡拆两读法(EffectSpec.pending 标记随批)。**归宿不变、位置更稳**:落点
仍是 kernel 效果账本(cw_effect_inventory + 账本→字段桥),即共用中段的
数据面;基类化不改变该挂账的执行路径,但加一条验收红利——拆两读法后 sim 与
实机经同一账本推进,sim 的到期时点分布可直接对照实机观测,不再需要第二份
sim 侧倒计时实现(归入 §7-T4 收敛纪律)。

### 10.3 执行落地门钩子收编的批次衔接裁决

批次二/三已落地的 inline 钩子(record_refresh_execution 接线点、遭遇刷新
计数 write_logic 点等)收编为 on_outcome 后:**登记件语义不变**(§6.5 六
条承诺;触发前提自 v12 起按 T-223 改发射语义,§6.4/§6.5-1),记录模型
设计 §8.7 的批次范围正本地位不重写;「钩子在哪个接线点」
的表述自此归本文 §6.4 单一源,范围归属仍归记录模型设计 §8.7——两正本
分工:范围(做什么)归 §8.7,接线位置(在哪里调)归本文。

## 11. 风险与开放问题

(如实列;待裁决项不拍死,裁决结果回填本文。)

> **开放问题编号解码**:本文正文的 A*/B*/C* 系编号(A1-A10/B1-B5/C1-C2,
> 如 §3.3-A1/§9.1-B2/§6.6-A7)= 架构起草期的开放问题条目,其一句话
> 申报与裁决状态的现行单一源 = 配套清单《统一观察架构-开放问题清单》
> 的「全部开放问题重编号总表」节(docs/develop/sr_od/application/currency_war/design/
> 统一观察架构-开放问题清单.md,正本同域持久件)。本节 R1-R10 是随本文
> 走稿的风险项编号,与清单内 `[R*]` 标注互指同一条目。

- **R1 引擎段边界申报的侵入面**(§3.3):相位翻译推荐「引擎在段边界显式
  申报当前画面」——这是 sim 引擎侧的一次性小改动,紧邻「rng 消耗序不变」
  红线;实现须证明申报是纯记录面。**申报值已钉死 = 引擎段身份**(§3.3-F9,
  非 screen_info 画面名);**申报机制已裁决(A1)= 引擎内段身份申报**
  (§3.3)——实现批落地时仍须证明申报是纯记录面(rng 消耗序不变)。
- **R2 st.shop 段后不清空**(§3.2 规则 2 的根因):映射规则已按「相位声明
  payload 域」绕开,但引擎数据面的该语义仍可能误导其他消费方(逻辑态直写链/
  账本落盘)。待裁决:是否顺手在引擎段边界清载荷域(行为面变更,须申报
  rng/池指纹影响)。
- **R3 sim 决策面接入的行为变更**(§7-T5,辖域已扩至备战线):备战线经
  decide_prep_screen 接入 + 遭遇接入 decide_encounter + 补给改调
  strat.decide_supply,均改变 sim 行为分布(属**有意行为变更**)——旧批次
  不可比,需池指纹追加与 A/B 申报。待裁决:分批时机(备战线与节点事件
  同批 or 两步)。
- **R4 回放语料的时代差与验证盲区**:现役回放语料的 state 快照是旧观察链
  产物;基类化后重放仍以快照重建(不经端口),回放门验证的是商店决策面
  而非端口/写入流——且只重放 decide_shop_screen(§9.1 降级为策略面回归
  哨兵的理由)。端口与写入流等价性靠主门(行为锁 + 分域夹具写入流对拍)
  + sim A/B 验证。判读时如实申报该盲区,禁把哨兵通过读成「等价已证」。
- **R5 PrepObservation 席位身份域的两域形状差**(§2.2):SIFT 识别域不在
  BoardState 观察流内,基类中段对席位身份的消费仍走透传;sim 侧该域经
  帧供给双落的合成帧直供(§2.4-F3)。两域「透传 vs 真值」的构造路径差须
  在端口契约申报;待裁决:sim 是否需要合成 PrepObservation 同形对象
  (现役引擎 st.bench/st.deployed 元素已同形,预期零成本,须测试锁钉住)。
- **R6 overlay 即时落定 vs 实机多帧交互**(§3.2):共用中段的「事件浮层」
  分支在 sim 恒走 'none'——分支逻辑共用但触发域不同;遥测判读须按 evidence
  分域,防把「sim 无浮层」误读成「浮层分支未触发」。
- **R7 并存期的等价判定面**(§9.1):双路径并存期「同画面同帧」的行为等价
  靠主门(行为锁经 execute() + 分域夹具写入流对拍)承载;实机 A/B 不可能
  逐帧(每局演化不同)。须为每个迁移画面定义等价断言集(单帧锁扩展,
  strategy-work §5 纪律)作为迁移完成判据,避免退化为「跑通了=等价」的
  弱判定。
- **R8 sim 侧 on_outcome 触发 = 记录面新增**(§6.4):统一后 sim 的动作
  发射开始写 BoardState 登记(刷新计数/升星预期/免战递减)——零 rng 影响
  (不改引擎真值演化与决策输入),但 sim 档案的 bs 读数从「合成口快照」
  扩为「快照 + 落地登记流」;跨批对读 bs 计数类键时须声明批辖域(统一前
  后不可直比)。**开启方式已裁决(A6)= 同批双开**,附三条落地义务:①恒
  paid 不对称申报(免费判定输入结构性 None,免费腿 sim 不触发,§6.3);
  ②本条批辖域申报随 A/B 报告的 sim 可观测性声明一并落;③B2-④ 登记流
  对拍按语义逐条断言,非字面序列相等(开放问题 B2)。
- **R9 简报相位统一对入口流时序的依赖**(§4.4):相位 1 统一后,实机简报
  帧的到达时序仍由入口流(CwEntryStart 导航)决定——「返回最高职级」点击
  (统一后 = kernel 缺省函数裁决、入口流代发射,§4.4/F5)、
  简报「下一步」链的画面流转时序属实机私有锚,统一循环消费它但不拥有它;
  入口流时序变更(游戏改 UI)时相位 1 帧型跟着变,判读侧须按 evidence 分
  辨「入口流时序」与「相位 1 逻辑」两类漂移。
- **R10 环境效果施加欠账下的双轨风险**(§8.2/§8.3):环境效果结构化词表
  与修饰函数族落定前,实机记录与 sim 引擎各自为政的窗口每延续一批,分叉
  税(win_reward_mult 型静默偏差)就累积一批。**先决闸已过**:A8 盘点批
  (3187b565)交付即本条的盘点前置;叠加**保真度边界**(§8.0):invest=True
  的 sim 局注入 83 环境但仅 轮岗/扑满守卫/名字亲和 三通道有行为效果,
  其余 = 纯名字注入——env 相关 sim 结论的外推力以此为限,判读前必核
  当批环境构成。词表(五类)落定 + T1a 字段裁决清单走完前,环境相关
  sim A/B 结论禁作采纳依据。
- **R11 流程转点锚的双计与口径混用风险**(§12):流程转点锚是新增登记
  件族——生命周期重入/重试路径可造成同事件双行,对账键幂等性 + 触发
  时点型显式申报是防线(§12.4 验收锁③④);锚行 scope 字段是防「P1
  截断 vs 全局面」型口径混用的对偶面(T-211 归因批实证的锚侧预防,
  进度账本 dag.jsonl 在册),消费侧跨批对读锚计数前必核 scope。sim 侧
  锚适用性逐锚申报(§12.2 适用域列),禁把「sim 无锚」误读成「事件未
  发生」。

## 12. 流程转点观测锚(流程 hook 观察点设计,v10 并入)

> 本章 = 用户提议「流程 hook——例如进入下一个节点、购买了牌之类的转点
> 上,处理投资策略环境等的效果计数」的设计落文(2026-09-10 口述,澄清
> 后目的 = **让框架提供更准确的游戏观察数据**——与停机钩子/采集钩子的
> 作用效果不同,见 §12.5-2/§12.5-3 的分流声明)。本章是 §2 观察端口
> (帧观察)的姊妹章:帧观察管「现在画面上是什么」,本章管「刚发生的
> 流程转点是什么」;两章共用一套写入 API、一套对账口、一套档案落盘,
> 禁另起第二观察架构。

### 12.0 辖域申报与名词

- **观测-only 边界**:本章只设计与数据采集和计数(记录面),状态改写/
  效果施加明确出栈——效果施加语义归 §8.2 效果结构化词表线(批辖域 =
  开放问题 A9),锚不承载。预留接口:锚行 payload 预留 `effect_ref`
  槽位(效果规格引用,取值 = STRATEGY_EFFECTS/STRATEGY_ECONOMY 注册表
  spec.id),供施加批将来消费,本期恒空不填——恒空有结构锁兜底
  (非空 = 红,§12.4-B⑤),消费侧守卫(决策代码禁读锚行)同锁位落,
  隔离边界不是纸面声明。
- **锚(流程转点观测锚)**:在流程确定性转点上触发的一次结构化观测,
  三要素 = 确定性触发时点 × 该时点的权威事实集 × 落载体登记。锚是
  on_outcome 登记件族的观测扩员(§12.5-1),不是新机制。
- **锚行**:一次锚触发的记录行,封装见 §12.3。
- **判定事实**:低频高价值的判定帧事实(如商店星级直出判定、cap 域外
  判定)——判定时点一过、证据不留即永久丢失,锚对其承担留证义务
  (§12.4 指标 5)。
- **口径域(scope)**:锚行自带的对账辖域声明(全局/位面段/购买单元级),
  消费侧跨批对读计数前必核(防「P1 截断 vs 全局面」混用复发)。

### 12.1 锚定原理:为什么转点处最准

观察事实按「谁是一手来源」分三型,转点对三型的意义不同:

1. **事件事实**(发生了什么):动作落地/节点推进/位面切换——框架自己
   是原因或第一目击者(点击链、画面分派、结算确认)。转点时点这些
   事实**零读屏即确定**;事后从散点帧推断,是本项目多次实证的缺陷类
   (物理试验口径靠跨流 join + 近似去重重建、hp 真值链合成行鬼值、
   node_type 三源混写、补给合成行轮归因 +1)。事件事实的权威来源 =
   转点本身,这是锚的存在理由。
2. **状态事实**(现在是什么):金/血/板面——屏是唯一权威(识别链),
   转点不增加权威性,但转点定义了**对账参考系**:锚点时点的状态快照
   是「之前/之后」的唯一可信分界(如买牌锚时点的金读 = gold_delta
   对拍的唯一可信前值)。
3. **判定事实**(判定帧):见 §12.0 名词——留证义务型,锚是留证的
   确定性触发器(现役缺口实证:直出频率批因判定帧无留证,聚簇根因
   离线不可定谳)。

「更准确」因此分解为五个可度量指标(§12.4):事件完备性、对拍一致率、
唯一性、时延边界、留证完备率。

### 12.2 锚点事件集总表

> 登记式封闭集:新锚先入登记表再接线,集外锚 = 红(登记式先例 =
> cw_game_ports 消费面封闭集/EMIT_TRIGGERED_DECLARED/SELL_CHANNELS)。
> 「现状归属」值:**收编**(现役写点即锚面,只申报关系)/ **收编 + 扩展**
> (复用现役写点与 kind,扩字段申报)/ **新增**(写点与钩子体新增)/
> **缓立**(候选,防双源或需求未到)/ **出辖**(明确不做,防「总图遗漏」
> 误读);写点与 kind 名可分属两类,逐行如实申报。触发时点型 = §6.4 轴
> (landed/emitted/v10 扩展 boundary)。
> **sim 适用域申报(v10 修订)**:sim 局账本只落 decisions + outcomes
> 两流、零 record_exogenous 调用(sim/pool.py 账本构成在案)——锚行
> 封装(§12.3)在 sim 侧**暂无落盘面**。除已申报实机-only 的锚外,
> 原「两域」锚一律改申报 **实机先行**:sim 侧的「事实来源」(引擎段
> 边界申报/结算行)存在,但锚行落盘面候批(§12.3 载体一 sim 申报),
> 验收 A 件的 sim 腿口径随之收窄(§12.4-A)。
> **evidence_required 申报位**:判定事实型锚的留证义务申报(§12.4
> 指标 5 的适用集),登记表行结构必带(§12.3),初判值逐行标注、
> 终判挂 H3。

| 锚(登记名) | 触发时点型 | 权威数据(锚定什么) | 为什么此处锚最准 | 载体(复用/扩展) | 现状归属 | sim 适用 |
|---|---|---|---|---|---|---|
| buy_landed 买牌落地 | landed | 卡名/费用/星级(决策帧识别产物)+扣金(金账对拍)+落槽(pixel-diff,new_bench_slots)+合成判定(detect_merge_upgrade 返回 bool)+买因(LAUNCH_CAUSES 闭集值,经发射侧 reason 归一映射,同 §12.5-4 载体申报) | 落地回执时点是「买哪张/花多少/是否触发合成」三事实同点唯一可得处;事后 bench 重读只能推断到达且合成后身份已变(直出频率批 j=Σ3^(star−1) 持有量重建即事后推断成本实证) | BoardState 合成升星逻辑态直写(write_logic)+ BUY bump(复用)+ ExogenousEvent kind='buy_landed'(扩展) | 新增(**前置依赖申报:触发口 on_outcome(BuyCard) 随 §6.4 执行器收编批成立——现役登记件还在 cw_op_buy_cards 执行落地门,R-J 挂账在案,禁绕收编私接触发**) | 实机先行 |
| sell_landed 卖牌落地 | landed | 卖出对象(slot/char/star)+退款金(sell_refund 口径 + 售价修饰)+渠道(**闭集值域 SELL_CHANNELS + 发射侧 reason→channel 归一映射单一源**——发射侧 reason 为自由字符串('line_switch_collapse'/'m4_fuel_sell' 等)非闭集本身,归一映射的宿主与封闭性守卫随 H2 钉死,禁散点手搓映射) | 退款在执行点与其它金变动分离(decisions 行 actions = 执行前快照,现役 sell_income 行已立「实收回金只有执行点可知」口径);渠道身份只在发射侧可知,事后不可重建 | ExogenousEvent kind='sell_income'(复用,channel 字段补登)+ 装配 A 闭集消费(复用) | 收编 + 扩展 | 实机先行(渠道是决策层发射语义,sim 引擎卖牌无渠道概念——sim 侧锚行落盘面候批,渠道字段在 sim 无来源,如实申报) |
| refresh_landed 刷新落地 | landed | 付费判定(免费闸)+刷价+前帧牌名集哈希(试验边界)+record_refresh_execution 计数组(total/paid/免费余额) | 「物理试验 = 每次付费刷新一帧牌面」的边界只有发射/落地时点可知(直出频率批靠组键近似重建:同名双卡按 1 计 + 跨段恢复局首帧多计 ≤1 试验;其报告的「分母高估 ≤3%」出自边界存疑带 2 局,非组键近似,归因如实分列);免费余额判定是执行侧事实,事后无从判 | spend_ledger 刷新字段(复用)+ shop_snapshots refresh 行(复用)+ record_refresh_execution/REFRESH bump(复用) | 收编(三写点即锚面;试验边界键显影挂 H2;**前置依赖申报:触发口随 §6.4 执行器收编批成立,R-J 挂账在案**) | 实机先行(恒 paid 不对称沿 §6.3 申报;锚行落盘面候批) |
| levelup_landed 升级落地 | landed | 击数/扣金/XP 增量/等级意图值 | 击数是框架连点链的事实,屏上只有结果等级;血购已立「行数 = 击数」粒度先例(ExogenousEvent kind='hp_pay'),金本位升级同粒度的扩字段需求 | ExogenousEvent kind='level_up'(**复用现役行**,扩击数/扣金字段申报随 H2)+ 效果账本升级标记挂点(复用,同点在产:现役升级成功路径写外生事件行同点调 on_level_up,prep_actions 升级链 W612 挂点在案) | 收编 + 扩展(**禁双行:另立 kind='levelup_landed' 与现役 'level_up' 行构成同事件两行,违指标 3,申报否决**) | 实机先行(锚行落盘面候批;现役行本身即实机写点) |
| box_opened 开箱 | landed | 箱槽位置 + 开箱后内容观察帧 + 席占变化 | 箱占席语义(记录模型:实机真值箱占席)的清除时点只有开箱链可知;内容观察须锚定在开箱后帧,晚一帧即被后续动作覆盖 | ExogenousEvent kind='box_opened'(扩展) | 新增 | 实机-only(sim 无箱实体,§6.6 在册申报) |
| battle_start 出战 | landed | 参战阵容 deployed 摘要(标识/星/站位,发射时点快照;**羁绊档位不入锚行——派生计算属 form_progress 族口径,判读离线派生,零新读屏约束由此自洽**) | 备战标识消失前最后帧 = 参战真值(验真锚即分界),战斗中/战后无可靠读链;「哪套阵容打的这一场」是复盘第一问,现役只有备战帧近似 | ExogenousEvent kind='battle_start'(扩展) | 新增(sim 侧事实来源 = 引擎出战段申报同值,锚行落盘面候批) | 实机先行 |
| node_enter 进节点 | boundary | node_type(外循环分派锚族判定值)+ 节点序位 + tick 回执(ticked/移除效果 id 清单) | 节点边界 = 效果账本 tick_node「登记当节点不推进」守卫的语义定义点;散点帧分不清「同节点重入备战」vs「新节点」(补给合成行轮归因 +1 已知缺口同根);TriggerKind.NODE_ENTER 族效果的触发时点权威 | ExogenousEvent kind='node_enter'(**kind 名复用**;choice 载荷扩 tick 回执)+ 效果账本 NODE_ENTER/tick_node(复用) | **新增(写点)+ 复用(kind 名)**——现役 'node_enter' 唯一写点在战斗结算后且仅辖战斗节点(battle_wait 出节点时点),遭遇/补给/奖励节点零写点、时点是「出节点」非「进节点分派」;进节点分派时点的新写点 + boundary 触发机制随实现批(hooks 见 §12.6-H6) | 实机先行(sim 事实来源 = 引擎节点段边界申报,锚行落盘面候批) |
| plane_enter 进位面 | boundary | 位面序号 + plane_bosses/enemy_affixes(过渡相位观察产物)+ 轮次重置 | 位面专属过渡屏(简报/位面详情/敌人情报)只在切换转点出现;位面台账缺写端病灶(写点①②只在开局/接管触发)已由写点③按帧合并修复——锚把「备战帧顺带」升格为确定性转点 | ExogenousEvent kind='plane_enter'(扩展)+ bs 写端(复用)+ TriggerKind.PLANE_START(复用) | 新增 | 实机先行(sim 事实来源 = 引擎位面段边界申报,锚行落盘面候批) |
| settlement 结算 | boundary | Settlement 全 payload(hp/streak/killed/方向)+ 效果结算族回执 | 结算屏 = hp 最高信任源(conf≥0.9 白名单);效果账本结算挂点(on_battle_end)仍未接 = 记录模型设计 §5.1 明文挂账,本锚即其接线载体(恢复生机/奋斗协议回血/招财狗/嘴硬族等结算触发效果的计数面) | ExogenousEvent kind='settlement'(**扩展,候选值随 H2**)+ apply_settlement_cover(复用)+ 效果账本结算挂点(接线);**outcomes 行 = 对账参照,非锚行宿主**(局终摘要行无七字段封装位,防封装声明对该锚失效) | 收编 + 接线 | 实机先行(sim 事实来源 = coarse 结算申报/outcomes 行,锚行落盘面候批) |
| event_choice 事件选择 | landed(现役 = 选择落地写) | 选项身份/序号/候选集 | 选择落地时点 = overlay 确认链验真点,现役已在产 | ExogenousEvent kind='event_choice'(复用) | 收编 | 实机-only(事件浮层族 sim 即时落定,R6 在册) |
| encounter/strategy 刷新发射 | emitted | refresh_click 证据词 / 逐卡键 | 防点偏未生效重入屏重复计数的现役语义(验效失败帧仍 +1) | EMIT 在册两件(复用) | 收编(已在册,遭遇件已接线) | 实机-only(T5 前引擎无遭遇决策段) |
| line_commit 锁线 | 缓立 | committed_from 翻转时点 + 锁定时 target_comp | 锁线是纯决策层事件无屏显,时序级事实现役只有轮粒度 trace | (缓立)kind 候选 'line_commit' | 缓立(防双源:与 decisions trace target_comp/锁产物行的分工随需求批申报;切线滞回诊断批的「摇摆发射通道定位」是首个候选需求方) | 缓立批随定(决策层事件两域同构;锚行落盘面同候 §12.3 载体一 sim 申报) |
| resume 恢复接管 | 出辖申报 | — | 现役 schema 9 段界重锚/resume_reconciliation 已承载,锚不重复登记 | match_archive(复用) | 出辖(已有) | — |
| shop_open/close 开关店 | 出辖申报 | — | 无效果计数面、无对账需求(§6.6 该行落地登记 = 无) | — | 出辖 | — |
| evolution_step 换血 | 出辖申报 | — | 全仓零调用死代码(总图 §1.8 as-built 断言在案);禁为死代码立锚,换血接线批同批补锚 | — | 出辖(待接线随批) | — |

### 12.3 数据面与 schema

**锚行封装(全部锚共用)**:

```
anchor_id        # 登记表键(§12.2 封闭集)
trigger_type     # landed | emitted | boundary(§6.4 轴三型)
ts/run_id/plane/round/node_seq/unit_seq   # 时点键(node_seq = 登记期快照;
                 #  unit_seq 仅商店域动作锚,坐标 = (plane,round) 内购买单元序)
payload          # 逐锚类型化槽位(§12.2 权威数据列;effect_ref 槽位预留恒空,§12.0)
scope            # 口径域声明:global | plane | unit(消费侧防口径混用)
evidence_refs    # 截图/帧留证指针(判定事实型锚必填,§12.4 指标 5)
produced_by      # 锚宿主 op 类名(沿登记件 produced_by 口径)
```

**载体三面(实机侧全部复用或扩展既有面,不新建流;sim 侧现状申报见后)**:

1. **事件行载体 = ExogenousEvent kind 词表扩展**(telemetry/schema.py
   符号名锚;结构化载荷住 choice)。**现役 kind 全集(grep record_exogenous
   调用点实测,v10 修订):node_enter / popup / briefing / event_choice /
   sell_income / hp_pay / level_up(prep_actions 升级链)/
   briefing_reconcile(cw_briefing_obs)/ resumed_match(cw_loop 恢复局)/
   locked_resume(cw_loop 锁定恢复)/ modality_gold(recorder)**——本清单
   是 H2 schema 修订批的现有值基线,修订批动工前须重跑扫描复核(H2 前置)。
   新 kind 须有生产者 = 锚钩子体,沿该流 kind「收敛到有生产者的值」既定
   纪律;扩展字段的 schema 版本 bump 归一个 schema 修订批(H2),防逐锚
   散改。**sim 侧现状申报(v10 修订)**:sim 局账本只落 decisions +
   outcomes 两流、零 record_exogenous 生产调用——锚行落盘面在 sim 侧
   **暂缺**,候选 = 账本行内字段扩位 or exogenous 流接入 sim 账本,随
   H2 修订批钉死;接线前 §12.2 各「实机先行」锚在 sim 域只验事实来源
   存在性,不验锚行完备率(R8 承诺的 sim bs 落地登记流同为**未接线**
   状态,本章不作既有面引用)。
2. **状态锚 = BoardState 既有写入 API**,source 标注
   `anchor:<anchor_id>`——写入规则/evidence 语义零改动(记录模型设计
   §2.4/§2.1 照旧),锚不是第二种写法。**边界细化(v10 修订)**:锚对
   BoardState 的写入 = 观察写入合法面(该面本就是决策视图数据源);禁的
   是观察写入之外的决策域改写——锚钩子体不得写 session 决策域字段/
   last_state 等装配态(锁面见 §12.4-B④)。
3. **计数载体 = 效果账本既有挂点**(选卡登记/节点 tick/计数 bump/跳过
   递减 consume_use/升级标记,五挂点在产)+ **结算挂点接线**
   (settlement 锚行承载,记录模型设计 §5.1 挂账的收敛落点)。用户
   提议的「投资策略环境等的效果计数」= 本面:锚只提供确定性触发
   时点,计数语义(CounterKey/TriggerKind/倒计时)全部归账本既有
   规格,禁锚内私设第二套计数。

**登记表机制(ANCHOR_REGISTRY,设计声明;代码承载随实现批)**:每锚
一行 = (anchor_id/触发时点型/宿主/载体 kind/sim 适用域/
**evidence_required**/前置依赖/申报出处),基类级持有(on_outcome 注册表
同宿主,§12.5-1);boundary 型锚的宿主 = 分派点/过渡相位处理/结算写端,
登记面与动作锚同表。新锚先登记再接线,集外锚 = 红;触发时点型逐锚
显式申报,禁静默选型(EMIT 同款纪律)。evidence_required 初判 = 全部
false,判定事实型(H3:star≥2 判定帧位)定谳后改 true 并申报判定依据;
**boundary 型锚的实机触发口与注册表触达机制未定**(现役两 fire 口都绑
op 实例生命周期,分派点不在其中),见 §12.6-H6,禁实现批静默选型。
**as-built(锚实现批① T-221,2026-09-10)**:代码承载已落
`kernel/cw_anchor.py`(符号名锚 = ANCHOR_REGISTRY/AnchorSpec/AnchorEvent/
emit_anchor);闭集内 = §12.2 实机先行 8 锚(实机-only/缓立/出辖行随其
归属批登记);当前零生产调用点 = 惰性纯机制面(触发口接线随其归属批:
动作锚随 §6.4 执行器收编批,boundary 候 H6);**H1 已裁决 = 本表行的
触发时点型列即三型统一申报面**(含 boundary),不另立 BOUNDARY_TRIGGERED_
DECLARED、不改既有 EMIT 表——本节末段已定锚登记行必带触发时点型字段,
第二申报面即双源;裁决与测试锁见测试仓 test_cw_anchor_registry。

### 12.4 准确性判据与验收形式

「更准确」的五指标(相对基线 = 现役「事后从散点读屏推断」):

| # | 指标 | 定义与度量 | 合格线 |
|---|---|---|---|
| 1 | 事件完备率 | Σ锚行 = Σ真值事件。动作锚闭合公式(v10 重构,立「尝试口径」):**plan 动作数(decisions.actions,执行前快照)= 截断未尝试数(spend_ledger plan_truncated/refresh_skipped 显影)+ 尝试数;尝试数 = 落地锚行数 + 执行失败数(exec_events,生产写点唯一,覆盖面逐动作族申报为公式右侧完整性条件)+ 未知数**;节点锚 = 锚行数 vs 档案段数(settlement_gap 段豁免);刷新锚 = 锚行数 vs spend_ledger refresh_attempted 单元数 | 未知数 = 0(前提 = 截断显影项接入公式 + exec_event 覆盖面申报完备,二者随 H7 钉死);完备率 = 1.0(豁免白名单逐项申报) |
| 2 | 对拍一致率 | 锚权威值 vs 帧观察推断值:锚行金差分 vs obs_conflicts 对拍行(旧流对拍行已随删除波 1 停写——历史档案只读;新局对拍分歧行 = journal obs_event)、锚点状态快照 vs 下一帧识别值、结算锚 vs hp 真值链;分歧行全部落 defect_ledger 可下钻 | 一致率 ≥ 现役事后推断基线(随批申报基线值);未解释分歧 = 0 |
| 3 | 唯一性 | 每真值事件恰一行:幂等键 = (anchor_id + 时点键)唯一;node_enter 同 (plane,round) 唯一(tick_node 同节点去重守卫同款语义);重试路径双触发零双行 | 双行 = 0(测试锁③) |
| 4 | 时延边界 | 锚时点不晚于下一帧观察:动作锚 ≤ 生命周期 act→on_outcome 段完成时点;boundary 锚 ≤ 分派/写端完成时点;锚行 ts 与次帧 observe ts 差可测 | 超界行 = 0(超界 = 对账语义降级为事后推断,即锚失效形态) |
| 5 | 留证完备率 | 判定事实型锚(登记表 evidence_required=true,§12.3)的 evidence_refs 非空率;适用集 = 登记表逐锚申报值,初判全部 false,H3 定谳 star≥2 判定帧位后收窄 | 100%(留证在锚点定义内,非事后补采) |

**验收形式(三件,实现批逐件交付)**:

- **A 离线对账**:实机档案 N≥30 局跑锚完备性对账(判读 CLI 新视图,
  沿「新复盘需求 = 新视图」纪律),出「逐锚 × 逐指标」表;**sim 腿口径
  (v10 修订)**:锚行落盘面接线前(§12.3 载体一 sim 申报),sim 域只验
  「事实来源存在性」(引擎段边界申报/结算行),不完备率指标——sim 腿
  完整验收挂落盘面接线批;基线对照申报同一计数的现役事后重建形态
  (直出频率批式跨流 join)的误差与工时,作「更准确」的直接证据。
- **B 测试锁五条**:①登记表封闭集锁(集外锚 = 红);②触发时点型申报
  锁(未申报型登记 = 红,EMIT_TRIGGERED_DECLARED 守卫同款);③幂等
  唯一锁(夹具双 fire 零双行);④**写向隔离锁**:锚钩子体调
  stop_running = 红;锚钩子体在观察写入 API 之外写 session 决策域字段/
  last_state = 红(BoardState 观察写入是合法面,§12.3 载体二边界细化);
  ⑤**读向隔离锁(消费侧守卫,方向沿 先例)**:决策/跟踪代码
  禁读锚行(grep 子串守卫,先例 = 决策代码禁读遥测 hp_pay 行回写)——
  effect_ref 预留位本期恒空,**非空 = 红的结构锁**同批落;未来效果
  施加批消费该槽时须先过用户裁决并同步改造守卫,禁静默启用。
- **C 判读纪律一条**(候选落 telemetry-reading 已知缺口/判读纪律节):
  跨批对比锚计数前先核锚行 scope 字段——P1 截断 vs 全局面口径混用的
  锚侧预防(T-211 归因批实证)。

### 12.5 机制关系声明(防双源防三源)

1. **on_outcome 注册表 = 扩展,非并行**。已迁画面的动作类锚的触发口 =
   既有 fire_outcome_hooks/fire_emit_hooks(cw_screen_op_base 符号名锚),
   锚 = 登记件族的观测扩员,复用触发时点轴两型。**两处如实申报
   (v10 修订)**:①buy_landed/refresh_landed 的 on_outcome(BuyCard/
   RefreshShop) 触发口**现役不存在**——这两类登记件还在执行器 inline
   落地门,收编随 §6.4 执行器收编批(R-J 挂账),锚实现批禁绕收编在
   inline 门私接触发;②boundary 型锚的触发点(画面分派/过渡相位处理)
   **不在 op 实例生命周期内**,现役两口都绑 op 实例,触发口与注册表
   触达机制未定(候选与裁决纪律见 §12.6-H6)。**不建第二注册表**——
   锚登记表是 on_outcome 注册表的登记清单面,不是平行触发机制。
2. **采集钩子(cw_shot_unique 类)= 并行,辖域互补,禁混同**。采集钩子
   = 内容哈希去重的留证采样,临时件(采毕删)、无确定性触发语义;锚 =
   确定性转点触发 + 结构化权威数据,常驻观察面(不适用「无条件触发、
   采毕删」的钩子生命周期)。锚的 evidence_refs 可复用同一截图设施,
   但语义不同:留证是锚的 payload 字段,不是独立采集通道。直出频率批
   建议的「star≥2 判定帧临时采集钩子」在锚落地后的收编方向 = 该判定帧
   的锚留证位(§12.6-H3 候裁),处置归其后续批。
3. **停机钩子 = 无交,显式分流**。锚是记录面,永不触碰 run 状态——
   随机态钩子的停机/采集二分流(项目入口文件「随机态钩子」节)在锚
   落地后为三分:停机(停 run 留现场)/ 采集(采样留证,临时)/
   锚(常驻观测登记)。分流判据不变:要不要停 = 停机钩子辖;
   要不要采样 = 采集钩子辖;要不要把既成事实记准 = 锚辖。
4. **T-170 判据轴 = 消费,不复制**。支出出口总图的统一判据轴(当轮
   转化 d 轴)辖「出口合法性」(决策前),锚辖「出口事实登记」(决策
   后)——两轴正交,合成一句话:**判据轴管「可以花在哪」,锚管「实际
   花了哪」**。防两套接口的硬约束:锚行词表消费总图闭集——卖牌锚
   channel = SELL_CHANNELS 闭集值域 + 发射侧 reason→channel 归一映射
   单一源(宿主与封闭性守卫随 H2)、买牌锚买因 = LAUNCH_CAUSES 闭集值
   + 同式归一映射(两闭集的定义点:SELL_CHANNELS/LAUNCH_CAUSES 皆在
   sell_gate,符号名锚)、换血锚(出辖待接线)候 T-168 契约三的通道
   登记,禁第二套渠道/买因枚举,归一映射本身 = 唯一允许的转换件;
   花金义务强制力(总图义务对偶轴,β 件候裁)的「盯防 = 观测批」
   消费锚行作盯防数据源,单一源不转移。d 类别不进锚行 payload
   (合法性是判据层派生,非观察事实;判读需要时按总图 §3.1 离线归类)。
5. **读屏封闭集(B4)= 不新增调用点**。锚的权威数据来源只有两类:
   执行侧已有回执/账本(零新读屏)与锚点当帧识别链产物的复用(零新
   读屏);确需补帧的(出战锚的 deployed 摘要)走既有观测漏斗。B4
   封闭集锁面不变,锚实现批须重跑 read_game_state 调用点扫描证基线
   未漂移(F1 基线纪律)。
6. **效果账本 = 接线关系**。锚为账本既有挂点提供确定性触发时点申报,
   挂点语义(tick 去重/计数键/递减)零改动;结算挂点(on_battle_end)
   的接线 = settlement 锚行的组成部分(记录模型设计 §5.1 挂账收敛),
   接线后「持续 N 节点」型两读法挂账(本文档 §10.2 同源)不受
   影响。
7. **遥测面 = 单管道**。锚行落盘走既有装配(match_archive 切片;
   **辖实机 live 流——sim 批账本不装配 match_archive,sim 侧锚行落盘面
   现状 = 暂缺,见 §12.3 载体一 sim 申报,候 H2**),缺陷走 defect_ledger,
   对拍走 obs_conflicts(旧流对拍行已随删除波 1 停写——历史档案只读;
   新局对拍分歧行 = journal obs_event)——三面零扩表;防三源总声明:**帧观察(§2)→
   锚(§12)→ 遥测落盘是一条管道的三段**,锚不产生独立数据域,判读
   消费同一份档案;「锚 vs 帧」的分歧对拍正是 §12.4 指标 2 的数据面,
   两源互证不是两源并存。
8. **节点推进权威 = 统一 state 派生规则,锚/台账不做第二计数器**
   (as-built R1.2,2026-09-10;设计正本 = 流程侧遥测 v3.4 §3.4.1 四规则
   组,关联面)。节点计数唯一权威源 = 统一 state 派生规则
   (kernel/cw_game_state.py,**字段层次终极形态,用户终裁 2026-09-11:
   观察层(observe)只放画面原始读数——顶栏原文落 top_bar_raw 字段;节点
   序键 node_ord = 逻辑层字段,四条腿(备战规则=解析顶栏文本成序键/弹窗
   规则/0q/0p)全部 write_logic 写逻辑层,无 observe 写序键的例外;类型
   派生同理逻辑层;生效序读口 = effective_node_ord 派生计算非存储字段**;
   推进去重键 =(run_id,
   effective_ord) 同序恰一次推进;类型派生 = 专属画面直定+商店面板未定型
   查链预留)。据此:§12.2 的 node_enter/plane_enter
   锚行只记边界事件事实(payload/触发时点),**禁携带或派生第二份节点序
   计数**——锚行与派生域的节点序对拍 = 判读可辨的分歧行,不是双源合流;
   PlaneNodeLedger 合并视图维持「判读侧台账」既有职责(§3.6 裁决),不做
   计数源。

### 12.6 开放问题(候并入开放问题清单总表)

> 以下 H* 条目候下一轮清单修订批收编(收编前,本章为其中语唯一源;
> 编号走 H 序列避免与 A*/B*/C* 撞号)。

- **H1 boundary 型申报面的命名与承载**:BOUNDARY_TRIGGERED_DECLARED
  独立申报表 vs 既有 EMIT 表加型列——实现批钉死并落测试锁,禁静默选型
  (R-E 纪律延伸)。**已裁决(锚实现批① T-221):两候选皆不取,申报面
  = ANCHOR_REGISTRY 行的触发时点型列**(§12.3 末段已定锚登记行必带该
  字段,第二申报面即双源;EMIT 表加型列还须动基类在飞面)——锁面 =
  test_cw_anchor_registry(H1 裁决锁:定义面扫描零回潮 + 三 boundary 锚
  经登记行型列申报)。
- **H2 锚行 schema 修订批辖域**:kind 词表扩展(buy_landed/box_opened/
  battle_start/plane_enter/**settlement** 候选集;levelup_landed 已撤——
  复用现役 'level_up' 行,禁双行,§12.2 在册)+ 刷新试验边界键 + sell
  channel 字段与 reason→channel 归一映射的宿主/封闭性守卫 + 买因归一
  映射 + **sim 侧锚行落盘面**(账本行内扩位 or exogenous 流接入,二选一
  钉死)的 schema 版本 bump,归一个 schema 修订批一次落定,防逐锚散改
  造成的多版本并存窗;**前置 = 现役 kind 全集重扫**(§12.3 载体一清单
  复核)。
- **H3 star≥2 判定帧留证位处置**:直出频率批建议的临时采集钩子 vs
  本锚设计的判定事实留证位(常驻)——候其校准回填批裁决,锚式为
  建议形态(evidence_required 锚,留证率进 §12.4 指标 5);定谳时同步
  改登记表 evidence_required 初判值(§12.3)。
- **H4 锚登记表宿主与 sim 装配**:登记表住基类(建议,与 on_outcome
  同宿主);sim 侧经 sim-driver 装配模块驱动(F8 选项③同构),boundary
  型锚的 sim 触发点 = 引擎段边界申报(§3.3-A1 已裁决的申报机制复用);
  sim 锚行的落盘载体随 H2 钉死。实现批确认。
- **H5 锚行保留策略与档案体积**:锚行使 ExogenousEvent 行数上升
  (逐动作一行),档案切片体积与滚动清理(keep 窗)的相互作用待实现批
  实测申报;候选 = 锚行不加保留豁免(随流滚动,与 hp_pay 同待遇)。
- **H6 boundary 锚的实机触发口与注册表触达机制**(v10 新增,对抗审
  发现 5):现役 register_outcome_hook 的 trigger 校验只收 outcome/emit
  两值,两 fire 口都绑 op 实例生命周期;node_enter/plane_enter 的触发点
  (画面分派/过渡相位处理)在 cw_loop 分派逻辑内,不在任何 op 实例的
  生命周期中(settlement 宿主 battle_wait 是 op,例外)。候选:①分派点
  持 op 实例后由 op 自报;②类级登记表 + 模块级 fire 口;③过渡相位表
  (§3.4)驱动器承载——随锚实现批①评估钉死并落测试锁,禁静默选型;
  H1 的申报面命名与本条同批裁决。
- **H7 指标 1 闭合公式的可测性钉死**(v10 新增,对抗审发现 2):尝试
  口径四项闭合(§12.4 指标 1)成立的前提 = ①exec_event 覆盖面逐动作
  族申报(现役生产写点唯一,哪些动作族哪条链落行未成清单);②
  spend_ledger 截断显影项(plan_truncated/refresh_skipped)接入公式取数。
  两件随锚实现批①落地;缺一则「未知数=0」合格线不判,完备率指标
  降级为「申报制豁免白名单」形态并如实标注。
