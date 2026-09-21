# effect-domain.md —— 效果域(在场效果账本的内容语义)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。本文 = 效果域内容语义正本(计数器模型/实例清单/分类词表/生命周期/
> 逐效果规格),即候裁 8(r5-migration-plan(已删过程件,git 可溯) §7 条 8「效果域
> 内容语义设计件」)的成文文件,W4 键收编(同文件 §2 W4 行)游戏效果键入域的设计依据。
> 行号引用 = 落文时点工作树快照,仅供定位;持久锚 = 符号名(类名/函数名/注册表键名)。

## 1. 本篇管什么

效果域 = 效果账本域 `effects`(总纲 §3.3 域清单行)的内容语义,管理五面:

1. **计数器模型**(§3):实例进展的唯一记录形态与计算侧导出规则;
2. **效果实例清单**(§4):实例的字段面、唯一性约束、伴生数值空间;
3. **分类词表**(§5):八类效果语义与各类的 state 记录形态模板;
4. **生命周期声明**(§7):TriggerKind × DurationKind 声明式驱动与事件映射;
5. **逐效果规格**(§8):`STRATEGY_EFFECTS` 注册表全量 14 条的在域形态。

不管什么(单一源在别处,本篇只引用,防双源):

| 语义面 | 单一源 |
|---|---|
| 效果变化的捕获与落盘(不设专用写口/专用域行,变更随快照行自带) | [journal.md](journal.md) §4 效果域捕获声明 |
| 逐效果「效果 → state 字段」四槽登记(官方原文/机制/state 影响/策略层消费)与逐条确定进度 | [strategy-env-impacts.md](strategy-env-impacts.md)(下称 impacts) |
| 效果数值真值(官方卡文/经济字段数值) | 代码注册表:`data/cw_invest_data.py`(base 官方文本,数据权限序之首)> `kernel/cw_investments.py`(overlay);值只在代码 |
| 节点推进判定与节点入口边界(counter +1 时机的判定基础) | [node-derivation.md](node-derivation.md)(派生规则单一源) |
| 效果的游戏机制原文考证 | docs/game/currency_war/(game 子树) |
| 单版本事务/渠道签名/派生序(节点判定→类型→效果推进) | [journal.md](journal.md) §2/§3/§4 |

写入通道归属:效果域是唯一以 **inventory 方法域**为主写渠道的域(总纲 §2 设计理念 4
「唯一写入口,禁旁路」的两个合法通道之一)——实例的登记/推进/计数/移除全部经
`ActiveEffectInventory` 方法,不经 `observe()`/`write_logic()`;效果改写**其他**域字段
(金/免费刷新余额/容量)时,才按被改写域的写口规则走(§6.3 归属判据)。

## 2. 载体与键域边界

### 2.1 载体

- 效果域载体 = `GameState.effects`,类型 `ActiveEffectInventory`(kernel/cw_game_state.py
  `effects` 字段 :1651;kernel/cw_effect_inventory.py `ActiveEffectInventory` 类 :142)。
  session 无独立字段——历史兼容读口 property 已撤,写读直经
  `game_state_of(session).effects`(同一实例,防双账本)。
- 写端(挂点)五处在产,全部经 inventory 方法(§7.3 映射表),零旁路直改;机器面 =
  效果域直摸锁(journal.md §6 硬约束①族)。
- 读端 = 查表方法(`by_category`/`by_trigger`/`by_source`/`first`/`counter`/
  `predict_for`;`by_source` 按 source='strategy'/'affix' 词表分源读,词缀源读端)。
  对决策的输出 = 在场事实与进展读数;哪些效果需要决策姿态响应,由效果规格 duties
  声明承载(§8)。

### 2.2 键域边界(哪些键是效果域键)

W4 键级三分(游戏效果键→效果域/策略行为键→决策行/无消费键删;r5-migration-plan(已删,git 可溯)
§2 W4)在效果域侧的落点:

| 键族 | 键形态 | 归属 |
|---|---|---|
| 效果规格键 | `EffectSpec.id`(plaza 稳定 id,cw_invest_data 主键;构建层校验 id+name 双匹配,`_validate_strategy_effects`,cw_investments.py:396-420) | **效果域**(本文)——实例以 spec_key 登记 |
| 效果计数键 | `CounterKey.REFRESH`/`CounterKey.BUY`(kernel/cw_effect_inventory.py `CounterKey` 类 :117-120),按 `(spec_id, key)` 定点隔离读(:192-195) | **效果域** |
| 策略行为观测键 | `StrategyState.cw4_counters` 容器各键(mandate_v1 决策/执行链自观测计数,strategies/impl/mandate_v1/mandate_state.py) | 决策行/局终聚合(策略侧载体),**禁入效果域** |

- 策略行为观测键与效果域键**零交集**:W4 审计定谳「游戏效果键 0 键」(效果域键的
  载体独立 = `cw_effect_inventory.py`,CounterKey 写点经 `effects.bump_key`,与
  cw4_counters 无共同键);机器锁 = sr-od-test `test_cw4_key_closure.py::test_effect_
  domain_zero_keys_d1_idle_declaration`(:809)。**键收编落码无迁入效果域之键**。
- 未来新游戏效果键(新卡/词缀/环境源建模批产出)一律按本文语义入域:规格入注册表
  (`STRATEGY_EFFECTS` 或对应源注册表)+ 实例经登记挂点入清单,禁旁落行为观测容器。

## 3. 计数器模型(统一单调计数器)

用户裁定(2026-09-10);混合模型销案见 §9.2。

1. 计数器统一**从 0 开始**;驱动事件发生就 **+1**;**单调递增,永不递减,永不重置**。
2. 倒计时/剩余量**全部在计算侧导出**——持续 N 节点的效果,剩余 = N − counter
   (counter=1 → 剩 N−1);state 不存「剩余」。
3. 门槛/周期也在计算侧:**counter ÷ 阈值整除触发**(每 N 次动作一次)/ **counter 判等
   触发**(第 t 个时点一次性)。
4. state = **单调正整数计数器笨存储**;计数器方向、驱动事件、阈值、到点语义全部归
   效果规格的计算规则(注册表规格 + 本文 §5/§8),state 不解释计数含义。

推论(单一语义面只存一个数):历史上分设的「剩余节点/计数器/授予权余量」三类动态
形态,由「一个 counter + 计算侧减法/判等」统一承载,不再分设三类存储。

## 4. 效果实例清单

目标形态(每条在场效果一行):

| 字段 | 语义 | 约束 |
|---|---|---|
| `spec_key` | 效果规格键 = `EffectSpec.id`(plaza id);规范名(`EffectSpec.name`,禁昵称)随规格可读 | **实例按 spec_key 唯一**(§9.1 销案) |
| `登记节点` | 登记时点的节点序 `(plane−1)×9+round`(基 1,全局统一坐标系) | 登记期快照;「从登记起计」类效果的推导基准 |
| `counter` | 单调计数器(§3 模型) | **无动态需求为空**(纯静态/即时效果不建,判据见 §5 记录形态列) |

- **伴生数值空间**:效果需随实例携带的数值(超发货币的负债额/狸财经狸的存款余额/
  现金为王的护盾余量)= 实例内 counters 键值承载,**不设独立 state 字段、不扩
  payload**。先例 = 超发货币负债额(impacts §3 超发货币条目);其余随逐条确定流程
  落 impacts 条目后即为在案先例。
- **与现行载体的等价申报**:现行 `ActiveEffect`(kernel/cw_effect_inventory.py:128-139)
  以 `remaining_nodes`/`remaining_uses`(递减余期)+ `counters`(单调计数)三维承载。
  递减余期与单调 counter **语义等价**:`remaining ≡ N − counter`,且共用同一推进守卫
  (§7.3 节点推进);差异是表示法与导出侧,不是语义分叉。表示法迁移归实施批,批位
  候用户裁决(§10-1);迁移完成前,效果域语义按等价式读取。播种双轨现状:登记时
  N_NODES 类播 `remaining_nodes=duration_nodes`、`duration_uses>0` 播
  `remaining_uses=duration_uses`(`register_strategy`,:164-177)。
- 实例生命周期 = 登记 → 推进(计数/发放)→ 移除(到期/用尽);once 类无推进维度,
  登记后即历史。移除同时点的一次性发放 = **尾款**(到期/到点金面,见 §7.3)。

## 5. 分类词表(八类)

基数申报(诚实口径):`STRATEGY_EFFECTS` = **14 条,实码全量**(构建层校验与数据层
不漂移;`len` 实测;含本金充裕/本金充裕+ 条件免费刷新两条,§8 节点推进族;含
加油站登记期 burst 建模条目,§8);词缀源
注册表 `AFFIX_EFFECT_SPECS` = 3 条 + 豁免表 `AFFIX_SPEC_EXEMPT` = 1 条(§7.6);
评估面 `STRATEGY_ECONOMY` = 92 条;策略全集
`INVESTMENT_STRATEGIES` = 335 条;官方 base 全集 `PLAZA_AUGMENTS` = 334 条
(`len` 实测;目录口径 = 两 overlay 键并集 = **97 卡**,84 候 + 14 已确认,与 impacts
§4 目录一致)。讨论口径「89 条经济效果」非设计基数,与实码 92 的精确对应
关系候用户裁决(§10-9),不作为设计基数。本表**不设每类条数列**——类分布随逐条
确定进度漂移,静态计数不构成设计结论;逐卡归类登记正本 = impacts。

| 类别 | 定义(效果语义) | state 记录形态(counter 判据) | 触发驱动 | 实码代表例(锚) |
|---|---|---|---|---|
| 即时结算 | 选卡当场一次性结清 | counter 空(无动态) | 选卡落地(§7.3) | 全员晋升/人力重组(cw_investments.py:353/:363);成本控制 instant_gold(cw_investments.py:210) |
| 静态修改器 | 持有期常数覆写/倍率,无时点事件 | counter 空(声明即生效,消费点计算侧直读,§6.2) | 无 | 开源节流 interest_cap_override(cw_investments.py:171)、简单模式 difficulty_delta(:267) |
| 每节点发放 | 每进节点给金/刷 | counter 空(节点事件判等发放,无剩余/门槛)或按节点 +1(有限期时转限时段形态) | 节点推进 | 按劳分配 gold_per_node(cw_investments.py:205)、双手狸开键盘！(§8) |
| 限时段 | 持续 N 节点后失效 | counter 按节点 +1;剩余 = N − counter(计算侧),counter 达 N = 过期 | 节点推进 | 躺平 duration_nodes=3(§8) |
| 延迟时点 | 登记后第 t 个时点一次性触发 | counter 按节点 +1;counter 达 t 触发(计算侧判等) | 节点推进 | 超发货币 gold_at_node_offset=5(cw_investments.py:253)、长期主义系 gold_next_nodes_*(:215-216) |
| 计数门槛 | 每 N 次驱动事件触发一次 | counter 按驱动事件 +1;counter ÷ N 整除触发(计算侧) | 动作次数(刷新/购买/合成/出售) | 采购专员·金/彩 counter_every=7/5(§8)、星星相印 gold_per_3star_merge(:272) |
| 等级门槛 | 到达指定等级触发/开窗 | counter 空(等级本身是 state,无独立累计)或按升级事件 +1 | 升级动作 | 成长基金 gold_at_level_target=9(cw_investments.py:249)、成长的快乐 xp_click_discount_from_level_at=8(:250-251) |
| 连胜联动 | 随连胜数变化(倍率/动态难度) | counter 空(连胜流为既有观察面)或按连胜事件 +1——**两案候裁**(§10-6) | 连胜变化(观察侧供给) | 伟大征服 win_reward_mult/difficulty_per_streak(cw_investments.py:175;零建模先例,impacts §3) |

## 6. 派生值归位与读数权威

### 6.1 惰性读口 vs 急算(派生值归位三件套)

用户裁定(2026-09-10)。派生值(由 state 内容算出的值)归到哪一段计算,按「何时被
需要」分判:

1. **随事件必须落账 → 单版本事务内急算**:计数器推进、发放、倒计时基数,在派生
   管线效果域段同一事务内算完落账(journal.md §4 派生原子生效)。
2. **消费时才被问 → state 内部惰性读口**:不随事件变化、消费时才需要的派生值,做成
   读口,消费时现算,不占存储。已确认实例:`effective_node_ord()`([node-domain.md]
   (node-domain.md) §3)/ `xp_buy_cost()`(商业间谍被动腿,§8)。
3. **派生管线前段只放原始读数整理**:依赖 state 内部知识的派生,禁放前段。

### 6.2 观察优先、兜底逻辑通用模式

用户裁定(2026-09-10;首例 = 买经验费用)。**一切画面有显示的数值 = 观察为准、
观察不到才逻辑兜底**。买经验费用两支:

- 显示价支:原样直通零减项(效果在场时备战画面显示的即折后价,游戏已算好,再减即
  双扣);
- 兜底支:基准 − 折扣族,max 0(基准恒 4 = 用户口径,非按等级;折扣族聚合单一源 =
  kernel `xp_click_cost`,cw_economy.py:485;升级总价 `upgrade_plan_fee`
  :1196 同源委托,禁第二处独立折扣实现)。

与节点序键同款单字段双值结构([node-domain.md](node-domain.md) §2);impacts §2 通用
模式节为其消费侧申报,两处互指,细则以本节为准。

### 6.3 写入归属判据(效果改写其他 state 字段时)

玩家裁定(2026-09-09):效果结果**可准确计算**(确定性公式+已知输入,含 bot 自身操作
引起的)→ 逻辑写(`write_logic` 或两步机制);含**概率/随机**、结果不可预知 → 不建
逻辑写端,观察收口。本判据辖「效果 → 金/hp/免费刷新余额/容量等字段」的写入面选择;
效果域实例自身的写入恒走 inventory 方法域(§1),不适用两分。

### 6.4 横切零建模面

用户裁定(2026-09-10;先例 = impacts §3 伟大征服/淘金客条目):

- **XP 腿零建模**:经验面板画面可读 = 观察层直接读;overlay 的 `xp_instant`/`xp_per_node`
  等字段值为预测面,非 state 存储。
- **HP/生命上限/难度/词缀/战力/强度/节点型改写腿零建模**:画面可读或纯游戏内部事。
- **随机资产面**(发牌/装备/开箱/商店改写内容)观察收口:标准观察流天然覆盖,不建
  逻辑写端(§6.3 判据的随机分支)。
- 例外注:免费刷新余额在按钮建档接入前只可规划面消费(impacts §3 固定理财条目注)。

## 7. 生命周期(TriggerKind × DurationKind 声明式)

### 7.1 声明面

- `TriggerKind` 10 值(kernel/cw_effect_inventory.py:31-42):INSTANT / PLANE_START /
  NODE_ENTER / BATTLE_END / LEVEL_UP / ON_REFRESH / ON_MERGE / ON_SELL /
  SUPPLY_PHASE / CONDITIONAL。
- `DurationKind` 4 值(:45-50):once / permanent / n_nodes / while_held(与持有绑定,
  策略卡缺省;独立值供词缀源对齐语义)。
- `EffectKind` 4 值(:53-58):economy / state / battlefield / unit_buff(unit_buff =
  游戏侧自算、bot 仅登记零响应,payload=`UnitBuffRef` :81-84)。
- 规格载体 = `EffectSpec` 四元组(trigger × duration × category × payload)+ 键面
  (id/name 与官方数据层双匹配)+ 二义标注(pending/verdict/notes,pending 条目必带
  保守支 notes)+ 种子面(duration_nodes/duration_uses)(:87-114)。构建层校验:
  孤儿键/id 漂移/payload↔category 不一致/pending 缺保守支,任一命中 import 即炸
  (cw_investments.py:396-420)。

### 7.2 声明式驱动

挂点只按声明路由事件,不写逐效果特判;**新增效果 = 新增规格声明,实例清单结构与
挂点代码零改动**。「谁要记账」的声明单一源 = `EffectSpec.duties.track`(`bump_key`
只推进不解释,:295-310);predict(执行前置知)/respond(决策姿态)语义同见
`DutyFlags`(:61-66)。

### 7.3 驱动事件映射(声明 → 事件源,实码在产面)

| 事件类 | 事件源(实码挂点) | 辖触发面 | 计数语义 |
|---|---|---|---|
| 节点推进 | 推进生效原语 `advance_node_effective` 尾段 `tick_effect_boundary`(kernel/cw_game_state.py;推进输入两路径同源同尾段 = ①节点边界终结动作上报 `report_node_advance`(trigger 封闭集 {settle_confirm, supply_confirm},观察态门)②观察锚定补推 `observe_node_anchor` 的 R>v/首锚定分支);同节点去重守卫在 inventory 内(kernel/cw_effect_inventory.py advance_node) | PLANE_START / NODE_ENTER / CONDITIONAL-N_NODES 型 | 节点类 counter +1,每节点恰一次(推进有效位为闸门) |
| 动作执行落地 | 刷新 = 上报函数统一触发(`report_action_refresh_shop_param` → `record_refresh`,kernel/cw_action_report/refresh_shop.py;含刷新三计数入账 + `bump_key(CounterKey.REFRESH)`,2026-09-18 迁入裁决)/ 购买 `bump_key(CounterKey.BUY)`(cw_screen_buy_cards.py 落地门);均未落地不计数 | ON_REFRESH;BUY 计数键(返利系门槛的驱动源) | 动作类 counter +1 |
| 跳过消耗 | `consume_use`(prep_actions.py:1512,跳过执行成功回执) | 次数类余量(免战牌) | uses 计数 +1(目标模型)/ 递减镜像(现表示法,§4) |
| 升级标记 | `on_level_up`(prep_actions.py:1350) | LEVEL_UP | 事件标记(`_EVENT_LEVEL_UP`,下划线前缀与策略计数器键空间隔离,:124) |
| 选卡落地 | `register_strategy`(operations/cw_screen/cw_screen_invest_strategy.py:440;免战牌同点自动登记 :416-440)+ burst 桥 `apply_effect_burst_grant`(:448)+ 板面重写桥 `apply_board_rewrite`(同点紧随) | INSTANT | 登记入清单 + 一次性发放 |

- **账本→字段桥**(效果发放换算成 state 字段写入的固定函数口,kernel/cw_game_state.py):
  `apply_effect_burst_grant`(选卡时点一次性批量授予)/
  `grant_effect_node_refresh_balance`(每节点余额累加,闸门 = 推进有效位;两桥出口 = `grant_free_refreshes`,余额住账本——2026-09-18 迁入裁决;**条件判定
  族已同桥 wire**——按金现值逐条目评估:金 > 阈值每额外步长金 +1 次、至多封顶,金未读
  None 保守零授予)/`project_effect_capacity`(容量逻辑态直写;逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态,真值以下一帧观察为准(观察赢))/`apply_board_rewrite`
  (板面重写:出售面逻辑写、替换面零逻辑写,归属单一源 = fields.md §5.3 两行)。
- **条件族采样金窗**:`grant_effect_node_refresh_balance` 的条件判定族(本金充裕
  系)按效果推进段执行时点的 `gs.gold` 现值评估——推进挂节点边界终结动作上报
  (settle_confirm/supply_confirm),动作帧的金 = 结算真值(结算观察链
  `apply_settlement_cover` 先于「继续挑战」点击落容器)或补给屏现读,无旧观察推断
  模型「推进帧不读金、沿用缺胜金旧值」的采样漂移面;静态每节点族(加油站/搜打撤/
  双手狸等固定授予族)不涉金采样;金未读该拍零授予不补发(语义见桥本体)。
- **每节点发放挂点与登记期建模**:每节点余额发放挂节点边界终结动作上报(经推进
  生效原语尾段;锚定补推路径同源发放——补推同为真实节点进入,跳档不漏发)。拿卡
  登记期的当节点发放按逐效果核查结论建模:**仅加油站**官方卡文带「现在」立即腿
  (登记期 burst 发放,`free_refresh_burst`,经选卡登记点 `apply_effect_burst_grant`
  直通);搜打撤/双手狸开键盘!/本金充裕族 = 次节点起,零登记期发放(发放时序
  与游戏真值一致,结论单一源 = `docs/game/currency_war/research/
  per_node_pick_node_grant.md`,证据分级 A 原文)。登记期发放「每效果×节点至多
  一次」由结构保证(发放挂点唯一 + 一次拿卡单事件),不设去重状态。
- **到期与尾款**:到期条目移除 = 尾款触发面;尾款金面走**观察覆盖兜底**,禁到期挂点
  logic 直写金币防双计(`advance_node` 契约,:234-236);确需单列逻辑写的建模者
  (如超发货币回流腿)按 impacts 条目申报接线。
- **登记挂点纪律**:登记面 best-effort,失败不阻塞选卡主链(cw_screen_invest_strategy.py
  :424-454);递减/消耗挂点与登记挂点解耦——登记面缺位的局 `consume_use` 返回 None
  零动作,保守端 = 记录缺失,不虚构递减(:261-275)。词缀源登记挂点 = 词缀读链产出点
  `cw_affix_effects.register_affixes_from_names`(简报屏/位面详情屏两链,§7.6)。
- **结算挂点现状**:`on_battle_end` **已接线**(kernel/cw_effect_inventory.py 定义;
  生产宿主 = CwScreenBattleWait 结算覆盖带 `_record_round_outcome` 非 telemetry_only
  分支,apply_settlement_cover 同分支同时序,独立 best-effort try 不与结算覆盖写端
  共享异常域)。注册表现役零 BATTLE_END 条目(§7.4)→ 行为面 = 结算事件标记
  (`_EVENT_BATTLE_END`);条目计数/余量推进随建模批立 BATTLE_END 条目后经同一挂点
  自动生效,无需再改接线。

### 7.4 零注册枚举值申报

`BATTLE_END`/`ON_SELL`/`SUPPLY_PHASE` 三值现役零条目——枚举值**保留**(环境源与新卡
建模的语义对齐预留),零条目 = 零驱动,不建事件。`ON_MERGE` 已有词缀源条目(**变宝
为废**,`AFFIX_EFFECT_SPECS`,§7.6);投资策略侧 ON_MERGE 仍零条目,候选驱动卡 =
武力刷新(合成装备,官方限定「合成装备时」)。其余候选驱动卡(按卡文触发语义归类):
按劳分配·剩余价值·无伤通关(战斗结算,BATTLE_END)/人力重组出售面(ON_SELL)/
补给时点族(SUPPLY_PHASE)——启用 = 各自建模批先立规格条目、再接事件源,启用前按
§6 观察收口兜底。

### 7.5 事件框架销案(hook 机制不建)

效果域的事件驱动 = 单版本事务内既有挂点(§7.3)+ state 内部派生;**不建**独立战斗
结算事件、事件选择事件与 hook 订阅框架。依据:①注册表支撑为零——`STRATEGY_EFFECTS`
零 BATTLE_END、零选择触发条目(§8 全表);②结算数据链路已在产零缺口(结算屏
观察 → settlement 域覆盖 → 策略器惰性消费);③inventory 查询口 `by_trigger`/
`predict_for`/`event_count` 无生产调用方(grep 可复核);④总纲设计理念「无独立事件流,
一切派生产出都是 state 写入」(总纲 §2 理念 2)。

### 7.6 词缀源(source='affix')

词缀效果已结构化建模(注册表 = `kernel/cw_affix_effects.py`;词缀与投资策略/环境
并列的第三效果源,实例同入一本账、经 source 维分源):

- **规格注册表** = `AFFIX_EFFECT_SPECS` 三条(键=词缀名,spec.id 同键;构建层校验
  `_validate_affix_specs` 与策略源同纪律:孤儿键/id 漂移/payload↔category 不一致/
  pending 缺保守支任一命中 import 即炸)+ 豁免表 `AFFIX_SPEC_EXEMPT` 一条
  (**开局不利**——开局 hp 专用载体 cw_opening_hp 承载,,禁第二份 −20 数值
  源)。在册三条:**成长的烦恼**(8 级后每次购经验 −1 金,LevelUp 金面)/
  **变宝为废**(每位面首次合成进阶装备 50% 变垃圾袋,ON_MERGE 装备库存改写,
  载体 `BattlefieldEffect.first_merge_equip_junk`)/ **永久创伤**(受击失生命上限
  20%、至多 60%——hp_max 字段缺位,观察收口+缺口申报,fields.md §5.2)。
- **登记端** = `register_affix`(播种与策略源同轨)+ 运行时挂点共用体
  `register_affixes_from_names`(简报屏/位面详情屏两词缀读链产出点,best-effort
  同登记挂点纪律);**读端** = `by_source('affix')`。
- **词缀与装备改写成员的扫描纪律**:词缀谓词扫描 `scan_rewrite_affixes` ∪ 装备谓词
  扫描 `scan_rewrite_equipments`(申报表 `EQUIP_REWRITE_DECLARATIONS` 恰等锁看管)
  是效果面完备性判据(fields.md §7)源 c/源 e 的代码化——新词缀/装备改写成员入册
  时同批入申报表,防「没被点名就无人看管」。
- **改写面写端归属**:按 fields.md §5.3 归属判据逐条成文于各 spec notes——成长的
  烦恼=确定性逻辑写(predict 开,写端接线归消费批,接线前观察覆盖兜底)/变宝为废=
  随机面观察收口/永久创伤=hp_max 缺位观察收口。**词缀源不经 `aggregate_economy`
  聚合通道**(键空间独立,`EconomyEffect` 词缀字段族仅建档;若未来词缀修饰要进经济
  聚合,须先过聚合分型登记门)。

## 8. 逐效果规格(`STRATEGY_EFFECTS` 全量 14 条)

通用形态:实例 = {spec_key, 登记节点, counter?}(§4);登记挂点统一 = 选卡落地(§7.3);
证据槽行号 = 落文时点快照。按驱动族分组;同组共性只在组首写一次。词缀源三条的逐条
规格在册于 `cw_affix_effects` spec notes(归属申报同源),不在本节 STRATEGY_EFFECTS
辖域(§7.6)。

### 节点推进族

#### 本金充裕(301001)/ 本金充裕+(301002)

- **论断**:NODE_ENTER / while_held / ECONOMY;duties 全空(counter 不建);免费刷腿
  = **条件判定族**,经节点桥 `grant_effect_node_refresh_balance` 按金现值逐条目评估
  自动生效(金 > 50 每额外 10 金 +1 次、至多 3;金未读 None 保守零授予,次拍恢复不
  补发);即时金腿 26(棱彩加强值只在 instant_gold)。
- **证据**:规格 cw_investments.py(条件三元组 free_refresh_cond_gold_above/step/cap
  =50/10/3,STRATEGY_EFFECTS 两条 EffectSpec payload 引 STRATEGY_ECONOMY 同一实例);
  官方原文 cw_invest_data.py:251-252。
- **推理链**:条件判定 = 节点进入时点的现值评估,非累计量 → counter 空;同节点重复
  采样经 advanced 位禁双计;并存叠加=两实例各评估(桥逐条目读即正确形态,条件
  三元组不可折叠单字段,未纳入 aggregate_economy——有意设计,非偏差)。

#### 固定理财(201801)

- **论断**:PLANE_START / permanent / STATE;counter **不建**(permanent 无到期,无剩余
  语义);发放腿双时点——当场段(登记时点)+ 每位面开始段(节点推进事件判等「位面
  开始」),免费刷腿入计数域余额,XP 腿零建模(§6.4)。
- **证据**:规格 cw_investments.py:306-311(pending=True,保守支 = PLANE_START 单触发);
  官方原文 cw_invest_data.py:130「现在以及每个位面开始时,获得4经验值和2次免费刷新。」
- **推理链**:「现在以及每个位面开始」= 双时点并列(双发读法已定谳,impacts §3 固定
  理财条目);位面段发放经效果域段急算(§6.1-1),注册表 pending 标注与保守支注释为
  回填前现状(回填归注册表维护批,§10-10)。位面开始段建模位 = STRATEGY_ECONOMY
  注释自注待建模(cw_investments.py:255-257)。

#### 双手狸开键盘！(204101)

- **论断**:NODE_ENTER / while_held / BATTLEFIELD;duties = track+predict;counter **不建**
  (每节点发放无上限无剩余);免费刷腿经 `grant_effect_node_refresh_balance` 桥(推进
  有效位闸门,每节点恰一次);代买哪几张 = 随机面观察收口。
- **证据**:规格 cw_investments.py:331-336(free_refresh_on_node_enter=2,auto_buy_owned=
  True);官方原文 cw_invest_data.py:156「进入新节点时,它会免费刷新商店2次,自动购买
  你场上拥有的角色。」(确认范围 = 新节点两腿,impacts §3)
- **推理链**:发放挂在节点进入事件判等点,无累计量 → counter 空;predict 声明 = 商店/
  备战席双对账须预知(代买使「牌自己消失」);幸运一击率腿 = 零建模面(战力类)。

#### 躺平(102001)

- **论断**:CONDITIONAL / n_nodes / ECONOMY;duties = track+respond;counter **建**(节点
  推进 +1,登记当节点不计、后继节点起计);剩余 = 3 − counter 计算侧导出,counter
  达 3 = 冻结解除;+20 尾款入账时点 = 实采项挂账(§10-4)。
- **证据**:规格 cw_investments.py:371-376(duration_nodes=3);官方原文 cw_invest_data.py:
  59「你无法在商店购买角色和刷新,持续3个节点。在此之后,获得20金币。」
- **推理链**:「持续 N 节点」= 有限期 → 需剩余语义 → 单调 counter + 计算侧减法(§3
  规则 2);禁买禁刷 = 策略层决策规则(效果域含躺平 ∧ counter<3 → 禁排买牌/刷新
  计划),**无执行闸**、策略器自己负责(用户裁定,2026-09-10);尾款金面 = 观察覆盖
  兜底(§7.3)。节点入口边界(入口=进入该节点备战画面;补给节点特例=补给选择画面
  即入口)单一源 = [node-derivation.md](node-derivation.md),本篇不复写。

#### 免战牌(151301)

- **论断**:NODE_ENTER / while_held / STATE(payload=`EconomyEffect(xp_instant=30)`);
  duties = track;次数余量 counter **建**(驱动 = 跳过执行成功回执 `consume_use`;剩余 =
  2 − counter,counter 达 2 = 移除/效果离场);+30 经验 = 选卡当场,零建模(§6.4)。
- **证据**:规格 cw_investments.py:387-392(duration_uses=2);官方原文 cw_invest_data.py:
  109「进入战斗节点时,直接跳过战斗并进入下一个节点,可生效2次。获得30点经验。」
- **推理链**:「可生效 2 次」= 次数余量 → 累计量 → counter;跳过机制本体由次数余量
  维度承载,不占改写载荷(spec 注释在案);登记挂点与消耗挂点解耦,登记面缺位的局
  零动作不虚构递减(§7.3 登记挂点纪律)。

#### 加油站(200301)

- **论断**:NODE_ENTER / while_held / ECONOMY;duties 全空(counter 不建);两腿
  分载——「现在」立即腿 = **登记期 burst 发放**(`free_refresh_burst`,选卡登记点
  `apply_effect_burst_grant` 直通 +1 次;+8 金即时腿 = `instant_gold`);持续腿 =
  每节点 +1 次(`free_refresh_per_node`,经节点边界桥 `grant_effect_node_refresh_balance`)。
- **证据**:规格 cw_investments.py(`free_refresh_burst=1` + `free_refresh_per_node=1`
  + EffectSpec 条目);官方原文 cw_invest_data.py「现在及每次进入新节点时获得1次
  免费刷新,立刻获得8金币。」
- **推理链**:拿卡当节点是否即享每节点额度的逐效果核查(证据分级 A 原文)单一源 =
  docs/game/currency_war/research/per_node_pick_node_grant.md——四效果中唯一带
  「现在」立即腿者;同族对照(搜打撤无「现在」措辞)证明该措辞承载真实发放差异。
  登记期发放「每效果×节点至多一次」由结构保证(发放挂点唯一 + 一次拿卡单事件,
  同卡跨节点重复拿取每次各发 = 游戏真值)。

### 动作计数族

#### 淘金客(301601)

- **论断**:ON_REFRESH / while_held / STATE;duties = respond;counter **不建**——付费刷新
  事件的产出(+2XP)是零建模面(§6.4),无剩余/门槛语义,无动态需求;实例仅为在场
  标记。
- **证据**:规格 cw_investments.py:298-302(payload=`STRATEGY_ECONOMY['淘金客']`,
  xp_per_refresh=2,:174);官方原文 cw_invest_data.py:259「你每次消耗金币刷新商店,都会
  获得2经验值。」
- **推理链**:驱动 = 付费刷新(「消耗金币」文本排免费刷);产出腿零建模 → 无落账量 →
  counter 空;respond 姿态(刷新期望价值 +2XP)归策略层消费。

#### 采购专员·金(201201)/ 采购专员·彩(303101)

- **论断**:ON_REFRESH / while_held / BATTLEFIELD;duties = track+predict+respond;counter
  **建**(驱动 = 刷新事件,**含免费刷**;阈值 7/5 在计算侧整除触发);金/彩各自独立
  实例,(spec_id, key) 定点读天然隔离;触发时商店改写内容 = 随机面观察收口。
- **证据**:规格 cw_investments.py:339-344(:345-350;`BattlefieldEffect(counter_every=7/5,
  shop_rewrite=True)`,cw_effect_inventory.py:72/:78);官方原文 cw_invest_data.py:124/
  :274「每7/5次刷新,商店会刷出5张费用相同的角色,费用为你备战席最左侧角色的费用。」
- **推理链**:「每 N 次」= 周期门槛 → 需累计量 → counter(§3 规则 3);计数含免费刷
  (用户裁定:官方未限定「用金币」,对照淘金客明写「消耗金币」的排免费写法,impacts
  §3);费用参数 = 备战席最左读数,对账核验用;备战席最左摆位 = 策略变量(respond)。

#### 商业间谍(300201)

- **论断**:LEVEL_UP / while_held / BATTLEFIELD;duties = predict+respond;counter **不建**。
  被动腿(购买经验花费 −1)= 惰性读口(§6.2),不入存储;触发腿(升级时刷新商店 +
  偷最贵 3 张)= 升级事件驱动,偷取哪 3 张 = 随机面观察收口。
- **证据**:规格 cw_investments.py:323-328(`BattlefieldEffect(steal_on_level_up=3)`);官方
  原文 cw_invest_data.py:244「购买经验的花费减1,升级时刷新商店,并偷取其中最贵的3个
  角色。」
- **推理链**:降价是持有期常数,读时消费(观察优先两支,§6.2)→ 无累计量;升级事件
  触发腿无计数语义(触发即结算,升级次数无需记)→ counter 空;`_EVENT_LEVEL_UP` 标记
  为升级事件留证,非策略计数器(键空间隔离,§7.3)。

### 即时族

#### 全员晋升(102701)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict;counter **不建**(一次性);本体
  = 选卡当场板面重写(board_rewrite='upgrade_all_cost+1'),替换面随机 → 观察收口;
  登记后实例即历史(once 无推进维度)。
- **证据**:规格 cw_investments.py:353-358;官方原文 cw_invest_data.py:67「场上的所有
  角色会永久升级成比自身高1费的随机角色(最大5费)。获得2个【拆装扳手】。」
- **推理链**:once → 无进展维度;改写后板面画面直读 → 零额外 state;附带的拆装扳手
  腿 = 装备观察收口。

#### 人力重组(102801)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict;counter **不建**;清场出售 =
  确定性逻辑写面(出售金按卖价公式,归属判据 §6.3 确定性分支),发牌面随机观察收口;
  出售金腿无 STRATEGY_ECONOMY 条目(spec 注释自注缺口,cw_investments.py:360-362)。
- **证据**:规格 cw_investments.py:363-368(board_rewrite='sell_all');官方原文
  cw_invest_data.py:68「出售场上和备战席的所有角色。获得1个随机的2星3费角色、2个
  2星2费角色和2个2星1费角色。」
- **推理链**:once 构同全员晋升;出售面确定性可算 → 逻辑写候选,发牌随机 → 观察
  收口;执行时序编排(卖→发牌)= 执行链辖域,非本篇。

### 条件窗口族

#### 经验就是财富(103601)

- **论断**:CONDITIONAL / while_held / ECONOMY;duties = respond;counter **不建**(条件
  改道是持有期算子,非累计量);当场金 +4 一次结清;改道腿 pending,定谳前消费端走
  保守支 = 改道吞非购买 XP;范围部分确认 = 暂只做节点基础经验改道(用户裁定,
  2026-09-10),其余四歧义(其他策略 XP 吞否/同事件性/上限/版本变体)挂起待采。
- **证据**:规格 cw_investments.py:315-320(pending=True,xp 改道算子字段待定谳后补
  payload);官方原文 cw_invest_data.py:79「获得经验时,改为获取等量金币(购买经验除外)。
  获得4金币。」
- **推理链**:改道 = 获得经验事件的产出改写(逻辑写端改道候选),属事件产出语义而非
  实例进展 → counter 空;定谳后按 verdict 回填算子字段并复推本论断。

## 9. 销案记录(结论与依据;销案不再复议)

1. **同卡叠加语义销案**:效果域实例按 spec_key 唯一,**无叠加合并逻辑**——不存在
   「同卡叠加两次」的 state 形态。依据:投资策略卡 3 选 1、已持有卡不复现(游戏规则
   保证;用户终裁 2026-09-10)。
2. **递减/递增混合计数器模型销案**:不存在递减计数器——混合模型(部分效果递减、
   递减、部分递增)由统一单调计数器(§3)取代;一切「递减/剩余」语义 = 计算侧由
   单调 counter 导出(用户裁定,2026-09-10)。
3. **hook 机制销案**:效果驱动不走独立事件/hook 框架(§7.5,依据四条就地)。

## 10. 候用户裁决(重大取舍单列;不阻塞本文成文与键收编设计引用)

1. **表示法迁移批位**:现行 `ActiveEffect` 递减余期表示 → 目标单字段 counter 表示
   (语义等价,§4 等价申报);迁移是纯表示法切换,批位候裁。
2. **零注册 TriggerKind 去留**:四值保留(本文立场,§7.4 语义对齐预留)与裁减两案;
   后续建模批将逐值启用,裁减会迫使建模批改枚举面。
3. **「持续 N 节点」vs「接下来 N 节点」读法拆分**:两读法现共用「登记当节点不推进」
   守卫,躺平方向系统性多冻 1 节点;实采后按卡文逐卡拆读法,`EffectSpec.pending`
   标记随批(挂账 = impacts §3 躺平条目)。
4. **躺平 +20 金入账时点**:达 3 当刻 vs 下一次节点入口两读法;裁定倾向 = 冻结三节点
   结束进 N+3 时入账(与 §10-3 同源,实采一并定谳)。
5. **躺平遭遇节点入口归类**:入口 = 遭遇屏 vs 备战帧——counter +1 时机依赖此归类;
   现判定规则下两形态均恰一次推进,不影响判定本体([node-derivation.md]
   (node-derivation.md) 场景走查)。
6. **连胜联动类 counter 有无**:记录形态两案(§5 表)——counter 空(连胜流为既有
   观察面)或按连胜事件 +1;该类现役无规格条目(唯一相关字段 difficulty_per_streak 在
   评估面),建模批到达时先裁后建。
7. **免费刷新余额上限**:设计按无上限处理(不建封顶逻辑);实采观察核对大额授予时
   余额是否溢出。
8. **墙钟型效果的计数器形态**:高效决策(「获得9999次免费刷新,但是只持续45s」,
   cw_invest_data.py:260 官方原文;注册表 `free_refresh_burst=9999`,cw_investments.py:168)
   驱动事件 = 现实时钟,非节点/动作坐标系——现役唯一墙钟卡;计数器模型是否增设
   墙钟驱动维候裁,到达前 burst 入账 + 窗末清零腿观察覆盖兜底。
9. **经济效果讨论口径与实码口径对应**:讨论口径 89 条 vs 实码评估面 92 条/目录并集
   96 卡/官方全集 334 条(§5 基数申报);精确对应关系候核对。不阻塞:逐条确定目录
   以注册表全集为准(impacts §4)。
10. **注册表 verdict 回填**:固定理财双发读法已定谳(impacts §3),注册表 pending 标注
    与保守支注释未回填;经验就是财富 verdict 回填候实采定谳。回填动作归注册表
    维护批。
