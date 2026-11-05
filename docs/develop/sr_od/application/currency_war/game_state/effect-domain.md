# effect-domain.md —— 效果域(在场效果账本的内容语义)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。术语与图例:保留词与数字来源标注四形态【注】【推】【拟】【拍】见
> [README](README.md) §6 术语表;对账 = 推算状态与下一帧实读逐项比对,对不上即 bug;
> 帧 = 一次拍画面+做决策的时点,帧代次 = 帧的版本标记。本文 = 效果域内容语义权威版本(计数器模型/实例清单/分类清单/生命周期/
> 逐效果规格),即旧排期件(已删,git 可溯)中「效果域内容语义设计件」事项的成文文件,
> 旧遥测流 cw4_counters 键级审计并入(键并入)游戏效果键入域的设计依据。
> 行号引用 = 落文时点工作树快照,仅供定位;符号名引用 = 符号名(类名/函数名/注册表键名)。

## 1. 本篇管什么

效果域 = 效果账本域 `effects`(总纲 §3.3 域清单行)的内容语义,管理五面:

1. **计数器模型**(§3):实例进展的唯一记录形态与计算侧导出规则;
2. **效果实例清单**(§4):实例的字段面、唯一性约束、伴生数值空间;
3. **分类清单**(§5):八类效果语义与各类的 state 记录形态模板;
4. **生命周期声明**(§7):TriggerKind × DurationKind 声明式驱动与事件映射;
5. **逐效果规格**(§8):`STRATEGY_EFFECTS` 注册表全量 76 条的在域形态。

> 邻位申报(临时工合约批):新白名单表 STRATEGY_EQUIP_EXPIRY_GRANTS(装备到期消失)非 STRATEGY_EFFECTS 条目,§7 生命周期不适用;判定函数 check_strategy_equip_expiry 纯读零写零 rng,一次性标志位写 strategy_conditional_done 共域。

不管什么(单一源在别处,本篇只引用,防双源):

| 语义面 | 单一源 |
|---|---|
| 效果变化的捕获与落盘(不设专用写入入口/专用域行,变更随快照行自带) | [journal.md](journal.md) §4 效果域捕获声明 |
| 逐效果「效果 → state 字段」四槽登记(官方原文/机制/state 影响/策略层消费)与逐条确定进度 | [strategy-env-impacts.md](strategy-env-impacts.md)(下称 impacts) |
| 效果数值真值(官方卡文/经济字段数值) | 代码注册表:`data/cw_invest_data.py`(base 官方文本,数据权限序之首)> `kernel/cw_investments.py`(overlay);值只在代码 |
| 节点推进判定与节点入口边界(counter +1 时机的判定基础) | [node-derivation.md](node-derivation.md)(派生规则单一源) |
| 效果的游戏机制原文考证 | docs/game/currency_war/(game 子树) |
| 单版本事务/渠道签名/派生序(节点判定→类型→效果推进) | [journal.md](journal.md) §2/§3/§4 |

写入通道归属:效果域是唯一以 **inventory 方法域**为主写渠道的域(总纲 §2 设计理念 4
「唯一写入口,禁旁路」的两个合法通道之一)——实例的登记/推进/计数/移除全部经
`ActiveEffectInventory` 方法,不经 `observe()`/`write_logic()`;效果改写**其他**域字段
(金/免费刷新余额/容量)时,才按被改写域的写入口规则走(§6.3 归属判据)。

## 2. 载体与键域边界

### 2.1 载体

- 效果域载体 = `GameState.effects`,类型 `ActiveEffectInventory`(kernel/cw_game_state.py
  `effects` 字段 :1651;kernel/cw_effect_inventory.py `ActiveEffectInventory` 类 :142)。
  session 无独立字段——历史兼容读取入口 property 已撤,写读直经
  `game_state_of(session).effects`(同一实例,防第二账本)。
- 写入方(接入点)六处在用,全部经 inventory 方法(§7.3 映射表),零旁路直改;机器面 =
  效果域直摸测试(journal.md §6 硬约束①族)。
- 读取入口 = 查表方法(`by_source`/`first`/`counter`;原 `by_category`/`by_trigger`/
  `predict_for` 查询口已随死代码清偿移除——在用读取 = 按源过滤与逐条直取;
  `by_source` 按 source='strategy'/'affix' 取值分源读,词缀源读取入口)。
  对决策的输出 = 在场事实与进展读数;哪些效果需要决策姿态响应,由效果规格 duties
  声明承载(§8)。

### 2.2 键域边界(哪些键是效果域键)

键级三分(游戏效果键→效果域/策略行为键→决策行/无消费键删;原排期件的键级审计裁定,git 可溯)在效果域侧的落点:

| 键族 | 键形态 | 归属 |
|---|---|---|
| 效果规格键 | `EffectSpec.id`(plaza 稳定 id,cw_invest_data 主键;构建层校验 id+name 双匹配,`_validate_strategy_effects`,cw_investments.py:396-420) | **效果域**(本文)——实例以 spec_key 登记 |
| 效果计数键 | `CounterKey.REFRESH`/`CounterKey.BUY`(kernel/cw_effect_inventory.py `CounterKey` 类 :117-120),按 `(spec_id, key)` 定点隔离读(:192-195) | **效果域** |
| 策略行为观测键 | `StrategyState.cw4_counters` 状态容器(GameState)各键(mandate_v1 决策/执行链自观测计数,strategies/impl/mandate_v1/mandate_state.py) | 决策行/局终聚合(策略侧载体),**禁入效果域** |

- 策略行为观测键与效果域键**零交集**:键级审计已定案「游戏效果键 0 键」(效果域键的
  载体独立 = `cw_effect_inventory.py`,CounterKey 写入位置经 `effects.bump_key`,与
  cw4_counters 无共同键);机器测试 = sr-od-test `test_cw4_key_closure.py::test_effect_
  domain_zero_keys_d1_idle_declaration`(:809)。**键并入写入代码后无迁入效果域之键**。
- 未来新游戏效果键(新卡/词缀/环境源建模批产出)一律按本文语义入域:规格入注册表
  (`STRATEGY_EFFECTS` 或对应源注册表)+ 实例经登记接入点入清单,禁旁落行为观测状态容器。

## 3. 计数器模型(统一单调计数器)

用户裁定(2026-09-10);混合模型已关闭,见 §9.2。

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
| `spec_key` | 效果规格键 = `EffectSpec.id`(plaza id);规范名(`EffectSpec.name`,禁昵称)随规格可读 | **实例按 spec_key 唯一**(§9.1 已关闭) |
| `登记节点` | 登记时点的节点序位(`acquired_key`,值 = `(位面, 轮)` 序位元组,按局修饰变长——登记端快照与推进入账同键,键口径同源 = 场字段 `node_seq_by_plane` 现值,同键契约保证「登记当节点不推进」守卫在修饰局不漂移) | 登记期快照;「从登记起计」类效果的推导基准 |
| `counter` | 单调计数器(§3 模型) | **无动态需求为空**(纯静态/即时效果不建,判据见 §5 记录形态列) |

- **伴生数值空间**:效果需随实例携带的数值(超发货币的负债额/狸财经狸的存款余额/
  现金为王的护盾余量)= 实例内 counters 键值承载,**不设独立 state 字段、不扩
  payload**。已登记先例 = 超发货币负债额(impacts §3 超发货币条目)与现金为王护盾
  记忆量(`counters['shield_bank']` = 板面重写桥出售支退款×1000 同闸记账,写端
  唯一 = 桥);其余随逐条确定流程落 impacts 条目后即为已登记先例。
- **与现行载体的等价申报**:现行 `ActiveEffect`(kernel/cw_effect_inventory.py:
  class `ActiveEffect` :254,余期/计数器字段区 :265-278)
  以 `remaining_nodes`/`remaining_uses`(递减余期)+ `counters`(单调计数)三维承载。
  递减余期与单调 counter **语义等价**:`remaining ≡ N − counter`,且共用同一推进守卫
  (§7.3 节点推进);差异是表示法与导出侧,不是语义分叉。表示法迁移归实施批,批位
  候用户裁决(§10-1);迁移完成前,效果域语义按等价式读取。播种双轨现状:登记时
  N_NODES 类播 `remaining_nodes=duration_nodes`、`duration_uses>0` 播
  `remaining_uses=duration_uses`(`register_strategy` 播种链 `_seed_progress`
  :343/`_register` :353,登记口 `register_strategy` :365)。
- 实例生命周期 = 登记 → 推进(计数/发放)→ 移除(到期/用尽);once 类无推进维度,
  登记后即历史。移除同时点的一次性发放 = **尾款**(到期/到点金面,见 §7.3)。

## 5. 分类清单(八类)

基数申报(诚实口径):`STRATEGY_EFFECTS` = **98 条,实码全量**(构建层校验与数据层
不漂移;`len` 实测;含本金充裕/本金充裕+ 条件免费刷新两条,§8 节点推进族;含
加油站登记期 burst 建模条目,§8;含合并同类项刷新出对条件金条目,§8 动作计数族
——ON_REFRESH 触发现役 5 条 = 淘金客/采购专员·金/彩/市场干预/合并同类项;含
战力类 UNIT_BUFF 零响应登记四十五条 = OOTD·金/三三三/中产阶级/人海战术/
全队的希望/创伤小组/前段发力/和平手枪祝福/团队力量·金/团队力量·银/基层贡献/
完美开局/幸运中的幸运/幸运喷雾/幸运星祝福/应援团/延迟收益/当头一棒/
打人就打脸·金/打通上下游·金/折叠小刀祝福/效率员工奖/星变/星级压制/
榜样的力量·金/榜样的力量·银/正能量/溜佩佩/溜佩佩+/独狼/生命之花祝福/绕口令/
装备党/读博深造/赞美太阳/量产型装甲祝福/钻石恒永久/风暴骑士/星魂升华/
爆仓/领航专家:姬子/及时雨/幸运之子/超光速提拔/战术义眼+,
登记形态
见 §7.1
unit_buff);词缀源
注册表 `AFFIX_EFFECT_SPECS` = 3 条 + 豁免表 `AFFIX_SPEC_EXEMPT` = 1 条(§7.6);
评估面 `STRATEGY_ECONOMY` = 92 条;策略全集
`INVESTMENT_STRATEGIES` = 335 条;官方 base 全集 `PLAZA_AUGMENTS` = 334 条
(`len` 实测;目录口径 = 两 overlay 键并集 = **97 卡**,84 候 + 14 已确认,与 impacts
§4 目录一致)。讨论口径「89 条经济效果」非设计基数,与实码 92 的精确对应
关系待用户裁决(§10-9),不作为设计基数。本表**不设每类条数列**——类分布随逐条
确定进度漂移,静态计数不构成设计结论;逐卡归类登记权威版本 = impacts。

| 类别 | 定义(效果语义) | state 记录形态(counter 判据) | 触发驱动 | 实码代表例(识别标志) |
|---|---|---|---|---|
| 即时结算 | 选卡当场一次性结清 | counter 空(无动态)或**伴生数值型非空**(现金为王 `shield_bank`=出售退款×1000,登记拍单写无推进——与限时段/延迟时点的**余期推进型**〔按节点 +1〕两类非空口径并列,§4 伴生数值空间) | 选卡落地(§7.3) | 全员晋升/人力重组/现金为王(cw_investments.py:679/:690/表尾);成本控制 instant_gold(cw_investments.py:210) |
| 静态修改器 | 持有期常数覆写/倍率,无时点事件 | counter 空(声明即生效,消费点计算侧直读,§6.2) | 无 | 开源节流 interest_cap_override(cw_investments.py:171)、简单模式 difficulty_delta(:267) |
| 每节点发放 | 每进节点给金/刷 | counter 空(节点事件判等发放,无剩余/门槛)或按节点 +1(有限期时转限时段形态) | 节点推进 | 按劳分配 gold_per_node(cw_investments.py:205)、双手狸开键盘！(§8) |
| 限时段 | 持续 N 节点后失效 | counter 按节点 +1;剩余 = N − counter(计算侧),counter 达 N = 过期 | 节点推进 | 躺平 duration_nodes=3(§8) |
| 延迟时点 | 登记后第 t 个时点一次性触发 | counter 按节点 +1;counter 达 t 触发(计算侧判等) | 节点推进 | 超发货币 gold_at_node_offset=5(cw_investments.py:681)、长期主义系 gold_next_nodes_*(:261——**分期形对表**:3 窗各一发非一次性触发,sim 状态容器落位 = `strategy_gold_next_nodes_left` 递减形〔fields.md §3.2.26e〕,counter 口径权威版本 = strategy-env-impacts.md 用户裁决段) |
| 计数门槛 | 每 N 次驱动事件触发一次 | counter 按驱动事件 +1;counter ÷ N 整除触发(计算侧) | 动作次数(刷新/购买/合成/出售) | 采购专员·金/彩 counter_every=7/5(§8)、星星相印 gold_per_3star_merge(§7.4,N=1 事件直结退化形) |
| 等级门槛 | 到达指定等级触发/开窗 | counter 空(等级本身是 state,无独立累计)或按升级事件 +1 | 升级动作 | 成长基金 gold_at_level_target=9(`STRATEGY_ECONOMY['成长基金']`)、成长的快乐 xp_click_discount_from_level_at=8(`STRATEGY_ECONOMY['成长的快乐']`) |
| 连胜联动 | 随连胜数变化(倍率/动态难度) | counter 空(连胜流为既有观察面)或按连胜事件 +1——**两案待裁决**(§10-6) | 连胜变化(观察侧供给) | 伟大征服 win_reward_mult/difficulty_per_streak(`STRATEGY_ECONOMY['伟大征服']`;注册行+消费链已登记——倍率经 aggregate_economy 聚合+轮首收入统一公式,难度经 M19 `cw_sim_enemy.difficulty_of` 注册表直读,两字段消费均不经效果清单) |

## 6. 派生值归位与读数权威

### 6.1 惰性读取入口 vs 急算(派生值归位三件套)

用户裁定(2026-09-10)。派生值(由 state 内容算出的值)归到哪一段计算,按「何时被
需要」分判:

1. **随事件必须落账 → 单版本事务内急算**:计数器推进、发放、倒计时基数,在派生
   管线效果域段同一事务内算完落账(journal.md §4 派生原子生效)。
2. **消费时才被问 → state 内部惰性读取入口**:不随事件变化、消费时才需要的派生值,做成
   读取入口,消费时现算,不占存储。已确认实例:`effective_node_pos()`([node-domain.md]
   (node-domain.md) §3)/ `xp_buy_cost()`(商业间谍被动分支,§8)。
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
逻辑写入方,交由观察收尾。本判据适用于「效果 → 金/hp/免费刷新余额/容量等字段」的写入面选择;
效果域实例自身的写入恒走 inventory 方法域(§1),不适用两分。

### 6.4 横切零建模面

用户裁定(2026-09-10;先例 = impacts §3 伟大征服/淘金客条目):

- **XP 分支零建模(辖域收窄,2026-11-04 用户裁定)**:xp_per_refresh 重复经验族
  已从本条移出——其世界腿(把结果写进状态副本的实现分支)已接入调用:
  刷新上报写端付费帧经 `grant_effect_refresh_xp` 鸭子类型读取聚合 →
  `grant_xp` 逻辑写通道字段写(fields.md §3.2.10);残余辖域 = live 观察覆盖
  足用之未结构化面——经验面板画面可读 = 观察层直接读;overlay 的
  `xp_instant` 等字段值为预测面,非 state 存储(选牌当场族现值零写入方,
  观察覆盖)。例外:sim 侧状态副本经验观察写统一经结算原语 `settle_xp_observe`
  把结果写进状态副本(升级连锁对任意经验来源生效,fields.md §3.2.10);
  `grant_xp` 逻辑写发放通道与之并存(level/xp 域现役双通道,channel_mix
  披露键,环境窗口桥与刷新 XP 分支两个调用点)。
- **HP/生命上限/难度/词缀/战力/强度/节点型改写分支零建模**:画面可读或纯游戏内部事。
- **随机资产面**(发牌/装备/开箱/商店改写内容)交由观察收尾:标准观察流天然覆盖,不建
  逻辑写入方(§6.3 判据的随机分支)。
- 例外注:免费刷新余额在按钮建档接入前只可规划面消费(impacts §3 固定理财条目注)。

## 7. 生命周期(TriggerKind × DurationKind 声明式)

### 7.1 声明面

- `TriggerKind` 7 值(kernel/cw_effect_inventory.py:55-63):INSTANT / PLANE_START /
  NODE_ENTER / LEVEL_UP / ON_REFRESH / ON_MERGE / CONDITIONAL
  (原 `BATTLE_END`/`ON_SELL`/`SUPPLY_PHASE` 三值在用零条目,已随死代码清偿移除,
  见 §7.4)。
- `DurationKind` 4 值(:66-71):once / permanent / n_nodes / while_held(与持有绑定,
  策略卡缺省;独立值供词缀源对齐语义)。
- `EffectKind` 4 值(:74-79):economy / state / battlefield / unit_buff(unit_buff =
  游戏侧自算、bot 仅登记零响应,payload=`UnitBuffRef` :81-84)。
- 规格载体 = `EffectSpec` 四元组(trigger × duration × category × payload)+ 键面
  (id/name 与官方数据层双匹配)+ 二义标注(pending/verdict/notes,pending 条目必带
  保守支 notes)+ 种子面(duration_nodes/duration_uses)(:87-114)。构建层校验:
  孤儿键/id 漂移/payload↔category 不一致/pending 缺保守支,任一命中 import 即炸
  (cw_investments.py:396-420;任一命中 import 即显式报错)。

### 7.2 声明式驱动

接入点只按声明路由事件,不写逐效果特判;**新增效果 = 新增规格声明,实例清单结构与
接入点代码零改动**。「谁要记账」的声明单一源 = `EffectSpec.duties.track`(`bump_key`
只推进不解释,:295-310);predict(执行前置知)/respond(决策姿态)语义同见
`DutyFlags`(:61-66)。

### 7.3 驱动事件映射(声明 → 事件源,实码在用面)

| 事件类 | 事件源(实码接入点) | 适用触发面 | 计数语义 |
|---|---|---|---|
| 节点推进 | 推进生效原语 `advance_node_effective` 尾段 `tick_effect_boundary`(kernel/cw_game_state.py;推进输入两路径同源同尾段 = ①节点边界终结动作上报 `report_node_advance`(trigger 封闭集 {settle_confirm, supply_confirm},观察态门)②观察 id_mark 确认补推 `observe_node_anchor` 的读数序位领先/首次确认分支);同节点去重守卫在 inventory 内(`advance_node` 键契约:入参 `node_key` = `(位面, 轮)` 生效序位元组,同序位相等去重;「登记当节点不推进」守卫 = `acquired_key >= node_key` 元组比较;全局去重键 = `(run_id, 生效序位)`) | PLANE_START / NODE_ENTER / CONDITIONAL-N_NODES 型 | 节点类 counter +1,每节点恰一次(推进有效位为闸门) |
| 动作执行落地 | 刷新 = 上报函数统一触发(`report_action_refresh_shop_param` → `record_refresh`,kernel/cw_action_report/refresh_shop.py;含刷新两计数入账 + `bump_key(CounterKey.REFRESH)`)/ 购买 = 买牌上报函数内获取计算完时点回调 `gs.effects.on_buy`(kernel/cw_action_report/buy_card.py;bump CounterKey.BUY + 购买族效果分派,满栏一击多买按实际张数 k 计 k 次,live/sim 同源);均未落地不计数 | ON_REFRESH;BUY 计数键(返利系门槛的驱动源) | 动作类 counter +1 |
| 合成事件(装备) | 穿戴上报 `report_action_wear_equip_param` applied 出口合成事件检查 `apply_on_merge_refresh_grant`(kernel/cw_effect_inventory.py;穿着即合成规则住上报 = kernel 单一源,live 动作 op 与 sim 动作注入同口单点覆盖;合成次数 = 输入件数−输出件数,三拒绝分支早退零发放) | ON_MERGE(装备合成) | 发放型非计数器:逐账本条目(名单集精确匹配,登记腿缺位保守零动作)`refresh_per_compose × 合成次数` 直写 `free_refresh_left`;装备栏内主动合成 bot 零执行零辖域,角色升星域另域禁混账(fields.md §5.3) |
| 跳过消耗 | `consume_use`(跳过型出战上报内,`kernel/cw_action_report/start_battle.py`;出战 op 跳过子态自上报,上报时递减) | 次数类余量(免战牌) | uses 计数 +1(目标模型)/ 递减镜像(现表示法,§4) |
| 升级标记 | `on_level_up`(prep_actions.py:1350) | LEVEL_UP | 事件标记(`_EVENT_LEVEL_UP`,下划线前缀与策略计数器键空间隔离,:124) |
| 选卡落地 | `register_strategy`(获得链 best-effort 登记腿 `kernel/cw_gain_chain.py`,选卡上报函数族驱动;免战牌同口自动登记)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥 `apply_board_rewrite`(同点紧随) | INSTANT | 登记入清单 + 一次性发放 |
| 获得链登记(portal 源) | 获得链原语 `kernel/cw_gain_chain.py::gain_invest_env` → `register_portal_from_env`(kernel/cw_effect_inventory.py;投资环境动作落地接入经动作上报 `report_action_pick_invest_param` portal 支进入) | INSTANT(portal 效果) | 登记入清单 |

- **账本→字段桥**(效果发放换算成 state 字段写入的固定函数口,kernel/cw_game_state.py):
  `apply_effect_burst_grant`(选卡时点一次性批量授予)/
  `grant_effect_node_refresh_balance`(每节点余额累加,闸门 = 推进有效位;两桥出口 = `grant_free_refreshes`,余额住账本——2026-09-18 迁入裁决;**条件判定
  族已同桥 wire**——按金现值逐条目评估:金 > 阈值每额外步长金 +1 次、至多封顶,金未读
  None 保守零授予)/`grant_effect_node_xp`(升级窗口发放,闸门 = 推进有效位:
  对 payload 带 `xp_after_level` 的已登记条目,达成识别标志未记录 → 达成检测记位
  (`ActiveEffect.anchor_pos`,伴生识别标志方法一次性写入;当拍不发放)、有识别标志且当前生效位
  > 达成位(元组字典序)且剩余 > 0 → `grant_xp` 每节点 +XP×1 并
  `bump(CounterKey.XP_GRANTED)` 单调 +1,剩余 = 窗口节点数 − 已发放计算侧导出;
  耗尽条目留置不删。达成位记录主插入位置 = 购买经验上报尾段
  `_record_lv8_window_start`(精确对齐),桥内检测 = 兜底(晚一拍保守);
  首例 = 成功经验 id 138,披露键族 `ENV_XP_WINDOW_DISCLOSURES`)/`project_effect_capacity`(容量逻辑态直写;逻辑态 = 动作执行后不经观察、按游戏规则推算并直写状态容器的预期状态,真值以下一帧观察为准(以实际观察为准))/`apply_board_rewrite`
  (板面重写:出售面逻辑写、替换面零逻辑写,归属单一源 = fields.md §5.3 两行)。
- **策略源到级金分支**(成长基金 id 101701 首例):kernel 纯决策函数
  `check_strategy_level_grants`(kernel/cw_gain_chain.py,零写零 rng,
  返回待发放 `(规范卡名, 金额)` 或 None;数据单一源 =
  `STRATEGY_ECONOMY` 级数配对字段,registry 驱动非专表)/闸门 = 短路矩阵
  六序(持卡 ∩ 到级条目 → done 一次性标志位 → level/gold 现值宁缺勿造不封账 →
  级数比较)/插入位置 = sim advance 双点(`_on_node_advance` 推进点 +
  `_on_node_advance_terminal` 局终点,节点经验入账拍后各一段内联接入调用:
  金 = observe 独立笔,sim 金写全 observe 现役形态;一次性标志位 = write_logic 直写
  `strategy_conditional_done`,producer `strategy_level_grant`);
  live 零接入调用(金面禁直写,观察覆盖兜底)/披露键 =
  `strategy_level_grant_state_semantics`(状态检查型语义未经实机采证)+
  `strategy_level_grant_dormant_in_sim`(现役 sim 经验常量下 9 级不可达,
  到级分支休眠)。链式契约权威版本 = [gain-chain.md](gain-chain.md) §2.12。
- **条件族采样金窗**:`grant_effect_node_refresh_balance` 的条件判定族(本金充裕
  系)按效果推进段执行时点的 `gs.gold` 现值评估——推进挂节点边界终结动作上报
  (settle_confirm/supply_confirm),动作帧的金 = 结算真值(结算观察链
  `apply_settlement_cover` 先于「继续挑战」点击落状态容器)或补给屏现读,无旧观察推断
  模型「推进帧不读金、沿用缺胜金旧值」的采样漂移面;静态每节点族(加油站/搜打撤/
  双手狸等固定授予族)不涉金采样;金未读该帧零授予不补发(语义见桥本体)。
- **每节点发放接入点与登记期建模**:每节点余额发放挂节点边界终结动作上报(经推进
  生效原语尾段;id_mark 确认补推路径同源发放——补推同为真实节点进入,跳档不漏发)。拿卡
  登记期的当节点发放按逐效果核查结论建模:**仅加油站**官方卡文带「现在」立即发放分支
  (登记期 burst 发放,`free_refresh_burst`,经选卡登记点 `apply_effect_burst_grant`
  直通);搜打撤/双手狸开键盘!/本金充裕族 = 次节点起,零登记期发放(发放时序
  与游戏真值一致,结论单一源 = `docs/game/currency_war/research/
  per_node_pick_node_grant.md`,证据分级 A 原文)。登记期发放「每效果×节点至多
  一次」由结构保证(发放接入点唯一 + 一次拿卡单事件),不设去重状态。
- **到期与尾款**:到期条目移除 = 尾款触发面;尾款金面走**观察覆盖兜底**,禁到期接入点
  logic 直写金币防双计(`advance_node` 契约,`cw_effect_inventory.advance_node`
  docstring 尾款行);确需单列逻辑写的建模者
  (如超发货币回流分支)按 impacts 条目申报接入调用。超发货币接入调用现状(2026-11 实现批):
  live 零写(游戏自扣自发,金整字段观察覆盖兜底),回流 = sim 节点窗世界腿。
  **t=5/6 对表**:注册行 `gold_at_node_offset=5`(cw_investments.py:681)的 offset
  语义 =「须完整过去的节点数」,发放入口序 = offset+1 = 拿卡后第 6 次节点入口
  (单一源 = strategy-env-impacts.md 超发货币条目用户裁定 2026-09-10
  「5个节点后=第6个节点才获取」;载体表达 = STRATEGY_EFFECTS 条目 duration_nodes=6)。
- **登记接入点纪律**:登记面 best-effort,失败不阻塞选卡主链(登记插入位置 = 获得链
  `kernel/cw_gain_chain.py::gain_invest_strategy` ②,选卡上报函数族驱动;唯一生产
  调用方 = 动作 op `operations/cw_op/cw_pick_invest_action.py`——原画面 op 写点
  cw_screen_invest_strategy.py:424-454 已停用退役);递减/消耗接入点与登记接入点解耦
  ——登记面缺位的局 `consume_use` 返回 None
  零动作,保守端 = 记录缺失,不虚构递减(:261-275)。词缀源登记接入点 = 词缀读链产出点
  `cw_affix_effects.register_affixes_from_names`(简报屏/位面详情屏两链,§7.6)。
  **portal(投资环境)效果登记接入点** = 获得链 `kernel/cw_gain_chain.py::
  gain_invest_env` → `cw_effect_inventory.py::register_portal_from_env`(链内
  best-effort 分支:登记/遥测面失败 log + 缺陷保留证据、不阻塞;`session=None` = 局外/
  测试形态登记分支跳过)。
- **结算接入点现状**:`on_battle_end` **已接入调用**(kernel/cw_effect_inventory.py 定义;
  生产宿主 = CwScreenBattleWait 结算覆盖带 `_record_round_outcome` 非 telemetry_only
  分支,apply_settlement_cover 同分支同时序,独立 best-effort try 不与结算覆盖写入方
  共享异常域)。注册表在用零战斗结算触发条目(§7.4)→ 行为面 = 结算事件标记
  (`_EVENT_BATTLE_END`);条目计数/余量推进随建模批立战斗结算触发条目后经同一接入点
  自动生效,无需再改接入调用。

### 7.4 战斗结算/出售/补给触发(零注册申报)

战斗结算(`BATTLE_END`)/出售(`ON_SELL`)/补给(`SUPPLY_PHASE`)三类触发语义在用
零条目,枚举值**未建**(原预留枚举值已随死代码清偿移除——在用零条目 = 零驱动,
枚举成员随启用批按需新增),不建事件。`ON_MERGE` 已有词缀源条目(**变宝
为废**,`AFFIX_EFFECT_SPECS`,§7.6);投资策略侧 ON_MERGE 首条已启用 =
**武力刷新**(合成装备,官方限定「合成装备时」;spec 条目入 `STRATEGY_EFFECTS`,
状态副本发放分支 = §7.3 合成事件行——穿戴上报 applied 出口检查 `apply_on_merge_
refresh_grant`,名单集匹配 + `refresh_per_compose × 合成次数` 发放进
`free_refresh_left`;实机到账时点/垃圾化交互两件未证事实挂披露键
`STRATEGY_ON_MERGE_LIVE_UNVERIFIED`);后继条目 = **星星相印**(角色 3 星合成
每事件 +5 金;触发面已裁决归一 = 共用 ON_MERGE 载体,两事件域由生产点分离 +
payload 字段判别零交叉:角色合成域发放分支 = `check_strategy_star_merge_gold`
(buy/gain 两域单点双调,仅 sim 装配态观察通道发金,live 零写观察覆盖),装备
合成域经上列名单集另路;分类 = 计数门槛 N=1 事件直结退化形——无跨帧计数器、
无 GameState 新字段、零 rng;live 零写零披露键)。其余候选驱动卡(按卡文触发语义归类):
按劳分配·剩余价值·无伤通关·气氛组·气氛组+(战斗结算)/人力重组出售面(出售时)/
补给时点族——启用 = 各自建模批先立枚举值与规格条目、再接事件源,启用前按
§6 观察收尾兜底。

### 7.5 事件框架已关闭(hook 机制不建)

效果域的事件驱动 = 单版本事务内既有接入点(§7.3)+ state 内部派生;**不建**独立战斗
结算事件、事件选择事件与 hook 订阅框架。依据:①注册表支撑为零——`STRATEGY_EFFECTS`
零战斗结算触发、零选择触发条目(§8 全表);②结算数据链路已在用零缺口(结算屏
观察 → settlement 域覆盖 → 策略器惰性消费);③inventory 触发过滤查询口已随死代码
清偿移除(原 `by_trigger`/`predict_for` 无生产调用方;在用查询 = `by_source`/`first`/
`event_count`,grep 可复核);④总纲设计理念「无独立事件流,
一切派生产出都是 state 写入」(总纲 §2 理念 2)。

### 7.6 词缀源(source='affix')

词缀效果已结构化建模(注册表 = `kernel/cw_affix_effects.py`;词缀与投资策略/环境
并列的第三效果源,实例同入一本账、经 source 维分源):

- **规格注册表** = `AFFIX_EFFECT_SPECS` 三条(键=词缀名,spec.id 同键;构建层校验
  `_validate_affix_specs` 与策略源同纪律:孤儿键/id 漂移/payload↔category 不一致/
  pending 缺保守支任一命中 import 即炸)+ 豁免表 `AFFIX_SPEC_EXEMPT` 一条
  (**开局不利**——开局 hp 专用载体 cw_opening_hp 承载,,禁第二份 −20 数值
  源)。已登记三条:**成长的烦恼**(8 级后每次购经验 −1 金,LevelUp 金面)/
  **变宝为废**(每位面首次合成进阶装备 50% 变垃圾袋,ON_MERGE 装备库存改写,
  载体 `BattlefieldEffect.first_merge_equip_junk`)/ **永久创伤**(受击失生命上限
  20%、至多 60%——hp_max 字段缺位,交由观察收尾+缺口申报,fields.md §5.2)。
- **登记端** = `register_affix`(播种与策略源同轨)+ 运行时接入点共用体
  `register_affixes_from_names`(简报屏/位面详情屏两词缀读链产出点,best-effort
  同登记接入点纪律);**读取入口** = `by_source('affix')`。
- **词缀与装备改写成员的扫描纪律**:词缀谓词扫描 `scan_rewrite_affixes` ∪ 装备谓词
  扫描 `scan_rewrite_equipments`(申报表 `EQUIP_REWRITE_DECLARATIONS` 恰等测试看管)
  是效果面完备性判据(fields.md §7)源 c/源 e 的代码化——新词缀/装备改写成员入册
  时同批入申报表,防「没被点名就无人看管」。
- **改写面写入方归属**:按 fields.md §5.3 归属判据逐条成文于各 spec notes——成长的
  烦恼=确定性逻辑写(predict 开,写入方接入调用归消费批,接入调用前观察覆盖兜底)/变宝为废=
  随机面交由观察收尾/永久创伤=hp_max 缺位交由观察收尾。**词缀源不经 `aggregate_economy`
  聚合通道**(键空间独立,`EconomyEffect` 词缀字段族仅建档;若未来词缀修饰要进经济
  聚合,须先过聚合分型登记门)。

## 8. 逐效果规格(`STRATEGY_EFFECTS` 全量 88 条)

通用形态:实例 = {spec_key, 登记节点, counter?}(§4);登记接入点统一 = 选卡落地(§7.3);
证据槽行号 = 落文时点快照。按驱动族分组;同组共性只在组首写一次。词缀源三条的逐条
规格已登记于 `cw_affix_effects` spec notes(归属申报同源),不在本节 STRATEGY_EFFECTS
适用范围(§7.6)。

### 节点推进族

#### 本金充裕(301001)/ 本金充裕+(301002)

- **论断**:NODE_ENTER / while_held / ECONOMY;duties 全空(counter 不建);免费刷新分支
  = **条件判定族**,经节点桥 `grant_effect_node_refresh_balance` 按金现值逐条目评估
  自动生效(金 > 50 每额外 10 金 +1 次、至多 3;金未读 None 保守零授予,次帧恢复不
  补发);即时金 26(棱彩加强值只在 instant_gold)。
- **证据**:规格 cw_investments.py(条件三元组 free_refresh_cond_gold_above/step/cap
  =50/10/3,STRATEGY_EFFECTS 两条 EffectSpec payload 引 STRATEGY_ECONOMY 同一实例);
  官方原文 cw_invest_data.py:251-252。
- **推理链**:条件判定 = 节点进入时点的现值评估,非累计量 → counter 空;同节点重复
  采样经 advanced 位禁双计;并存叠加=两实例各评估(桥逐条目读即正确形态,条件
  三元组不可折叠单字段,未纳入 aggregate_economy——有意设计,非偏差)。

#### 固定理财(201801)

- **论断**:PLANE_START / permanent / STATE;counter **不建**(permanent 无到期,无剩余
  语义);发放分支分两段——即时段(「现在」)= xp_instant 4 + burst 2,登记期
  发放(burst 桥 + 登记拍补发桥);位面段 = xp_per_plane 4 + free_refresh_per_plane
  2,位面开始发放,**两处插入位置分工**:刷新支 = 位面开始桥 `apply_effect_plane_start_
  grant`(kernel 推进 tick 位面 1 号节点,per-node 桥同形幂等:advanced ∧ 位面
  首节点,不另设 done 一次性标志位)、XP 支 = sim 位面首节点窗分支(kernel 零 sim import,
  XP = 状态副本里的值 live 观察覆盖)——同一位面开始两拍:先推进边界(kernel 刷新支)
  后开窗(sim XP 支),账户面等价、evidence 时序可辨,拍点差显式申报非对齐改造。
  **中途拿卡**:当前已开始的位面其位面段登记拍全额补发(刷新支 = 补发桥
  `apply_effect_plane_refire_grant`、XP 支 = sim 选卡拍补发分支;已开始判据 = 登记
  恒在节点窗内 → gs.node 在场即已开始,node 缺席保守零补发)——用户裁定
  2026-11-01 人为定为,原保守支(不补发)随裁定消解,pending 撤除。
- **证据**:规格 cw_investments.py(STRATEGY_EFFECTS 条目 payload 引 STRATEGY_
  ECONOMY 同一实例;注册行四字段 4/4/2/2);官方原文 cw_invest_data.py:130
  「现在以及每个位面开始时,获得4经验值和2次免费刷新。」
- **推理链**:「现在以及每个位面开始」= 双时点并列(双发读法已定案,impacts §3 固定
  理财条目);位面段 = 策略域位面粒度周期发放首例(载体先例 = per-node 桥同形放大,
  环境域 `_apply_env_plane_start` 同窗先形)。pending 已随建模批回填(用户裁定,
  §10-10),保守支注释消解。

#### 固定理财+(201802)

- **论断**:与姊妹固定理财(201801)同构全量同判——PLANE_START / permanent /
  STATE;counter 不建;分两段发放,数值异(即时段 xp_instant 6 + burst 3,
  位面段 xp_per_plane 6 + free_refresh_per_plane 3),载体/两处插入位置分工/中途
  拿卡登记拍全额补发读法全部共享姊妹条目语义(用户裁定 2026-11-01 对两卡
  一次人为定为,裁决联动禁两态),零新增机制件(桥/分支按 payload 字段鸭子类型读取(duck typing),
  本卡条目入账本即自动覆盖)。
- **证据**:规格 cw_investments.py(STRATEGY_EFFECTS 条目 payload 引 STRATEGY_
  ECONOMY 同一实例;注册行四字段 6/6/3/3);官方原文 cw_invest_data.py:131
  「现在以及每个位面开始时，获得6经验值和3次免费刷新。」
- **推理链**:卡文逐字同构仅数值异 → 同 posture 先例(T-178 先例:裁决联动
  禁两态);pending 与姊妹同批撤除(notes 记同判裁定),verdict 维持 None。

#### 公司严选(301401)

- **论断**:PLANE_START / permanent / STATE;duties = track+respond(对表姊妹
  固定理财写进代码形);counter **不建**;payload = STRATEGY_ECONOMY 同一实例。
  分三段:即时段(「现在」)= instant_gold 3 已登记估值面(金面禁直写——发放
  写端缺口族级 T-112 口径,零 kernel 桥);选卡改写分支 = sim 选卡尾段,窗口起点
  快照差分限定「本拍新获得」(消费后快照前滚,链式选卡不重燃旧卡、重放差分
  恒空);位面段 = gold_per_plane 3(**策略域位面周期金首例**)+ 位面开始改写分支
  (M05 全刷后后置覆盖),双支 = sim 位面首节点窗独立笔(金 `strategy:plane_
  gold:p{位面}` 求和单笔,XP 位面分支同窗邻位;窗口幂等守卫防重放)。**中途
  拿卡**:位面段〔金 + 改写〕登记拍全额补发(用户裁定 2026-11-01 族级人为定案,
  与固定理财族同判;已开始判据 = gs.node 在场即已开始,None 保守零补发)——
  同拍「选卡改写 × 补发改写」双触发两分支都发(journal 双行如实登记禁静默合并)。
- **证据**:规格 cw_investments.py(STRATEGY_EFFECTS 条目 payload 引 STRATEGY_
  ECONOMY 同一实例;注册行四字段 instant_gold 3/gold_per_plane 3/forced_cost 4/
  forced_unique True);官方原文 cw_invest_data.py:257「现在及每个位面开始时,
  开启一个由5个独特4费角色组成的商店,并获得3金币。」
- **推理链**:触发词族「现在及(以)每个位面开始时」第 3 员,补发读法 = 族级
  用户裁定直接适用(REVIEW-T309 §1-5 无需用户决定,T-183 同判先例)。「独特」= 同帧
  去重(desc 自载显式例外,基线 U13 允许重复辖基线);强制费用档 = kernel
  `sample_shop_deal_forced` 单源(商店发牌出口 drawable_names,翻星分支与基线
  共享——人才下沉局合成);锁交互沿间谍效果分支形(无锁守卫,真值待实采与间谍
  卡共享,零新增键);pending 定案形态入册即 False(裁定记录住 notes),verdict
  维持 None。

#### 双手狸开键盘！(204101)

- **论断**:NODE_ENTER / while_held / BATTLEFIELD;duties = track+predict;counter **不建**
  (每节点发放无上限无剩余);免费刷新分支经 `grant_effect_node_refresh_balance` 桥(推进
  有效位闸门,每节点恰一次);代买哪几张 = 随机面交由观察收尾。
- **证据**:规格 cw_investments.py:331-336(free_refresh_on_node_enter=2,auto_buy_owned=
  True);官方原文 cw_invest_data.py:156「进入新节点时,它会免费刷新商店2次,自动购买
  你场上拥有的角色。」(确认范围 = 新节点两支,impacts §3)
- **推理链**:发放挂在节点进入事件判等点,无累计量 → counter 空;predict 声明 = 商店/
  备战席双对账须预知(代买使「牌自己消失」);幸运一击率分支 = 零建模面(战力类)。

#### 躺平(102001)

- **论断**:CONDITIONAL / n_nodes / ECONOMY;duties = track+respond;counter **建**(节点
  推进 +1,登记当节点不计、后继节点起计);剩余 = 3 − counter 计算侧导出,counter
  达 3 = 冻结解除;+20 尾款入账时点 = 实采待确认的登记未决问题(§10-4)。
- **证据**:规格 cw_investments.py:371-376(duration_nodes=3);官方原文 cw_invest_data.py:
  59「你无法在商店购买角色和刷新,持续3个节点。在此之后,获得20金币。」
- **推理链**:「持续 N 节点」= 有限期 → 需剩余语义 → 单调 counter + 计算侧减法(§3
  规则 2);禁买禁刷 = 策略层决策规则(效果域含躺平 ∧ counter<3 → 禁排买牌/刷新
  计划),**无执行闸**、策略器自己负责(用户裁定,2026-09-10);尾款金面 = 观察覆盖
  兜底(§7.3)。节点入口边界(入口=进入该节点备战画面;补给节点特例=补给选择画面
  即入口)单一源 = [node-derivation.md](node-derivation.md),本篇不复写。

#### 免战牌(151301)

- **论断**:NODE_ENTER / while_held / STATE(payload 引 `STRATEGY_ECONOMY['免战牌']`
  同一实例 = `EconomyEffect(xp_instant=30)`,单一源);duties = track;次数余量载体
  `duration_uses=2 → remaining_uses`(播种/递减/归零移除走 effect_inventory
  次数类通道);递减插入位置 = 跳过型出战上报(出战 op 跳过子态 →
  `report_action_start_battle_param` 内 `consume_use`,上报时递减,用尽移除)。
  sim 消费面 = `battle_skip` 声明分支(跳过过程:战斗不发生——hp/连胜/收入
  落账/难度记录/结算环帧行全零写,被跳节点经验照常入账 + 状态副本直进下一节点窗,
  与 `_on_node_advance` 入账同构,含策略卡到级金/装备分支记账段镜像);+30 经验 =
  选牌当场即时(§4 投资选择通用通道 `xp_instant`:选卡落地拍世界腿 + 估值
  现金计分;登记时代「零建模(§6.4)」口径随通用通道写进代码改判入册)。跳过辖域 =
  仅 kind='battle'(卡词汇类型读法;披露键 `cw_skip_scope_battle_only_assumption`
  挂实机按钮出现面校准,失配常量单点改值跟随)。
- **证据**:规格 cw_investments.py `STRATEGY_EFFECTS['免战牌']` 条目 +
  `STRATEGY_ECONOMY['免战牌']` 注册行(duration_uses=2);官方原文 cw_invest_data.py:
  109「进入战斗节点时,直接跳过战斗并进入下一个节点,可生效2次。获得30点经验。」
- **推理链**:「可生效 2 次」= 次数余量 → `duration_uses` 载体(次数类首例);
  跳过机制本体由次数余量维度承载,不占改写载荷;登记接入点与消耗接入点解耦,
  登记面缺位的局零动作不虚构递减(§7.3 登记接入点纪律)。

#### 加油站(200301)

- **论断**:NODE_ENTER / while_held / ECONOMY;duties 全空(counter 不建);两支
  分载——「现在」立即发放分支 = **登记期 burst 发放**(`free_refresh_burst`,选卡登记点
  `apply_effect_burst_grant` 直通 +1 次;+8 金即时分支 = `instant_gold`);持续发放分支 =
  每节点 +1 次(`free_refresh_per_node`,经节点边界桥 `grant_effect_node_refresh_balance`)。
- **证据**:规格 cw_investments.py(`free_refresh_burst=1` + `free_refresh_per_node=1`
  + EffectSpec 条目);官方原文 cw_invest_data.py「现在及每次进入新节点时获得1次
  免费刷新,立刻获得8金币。」
- **推理链**:拿卡当节点是否即享每节点额度的逐效果核查(证据分级 A 原文)单一源 =
  docs/game/currency_war/research/per_node_pick_node_grant.md——四效果中唯一带
  「现在」立即发放分支者;同族对照(搜打撤无「现在」措辞)证明该措辞承载真实发放差异。
  登记期发放「每效果×节点至多一次」由结构保证(发放接入点唯一 + 一次拿卡单事件,
  同卡跨节点重复拿取每次各发 = 游戏真值)。

#### 公司人才流动(102101)

- **论断**:NODE_ENTER / while_held / BATTLEFIELD;duties = track;counter **不建**
  (每节点重掷无累计/剩余语义);重掷面 = 随机分支零逻辑写、靠画面读数收尾(§6.3/§6.4),
  bot 零执行端代码,真值由下一备战帧 bench 观察(现役观察链)覆盖;区间 = 现役
  capacity 尾 3 槽(默认案,实采可校正);辖域仅 kind='unit' 槽;+2 金 = 选卡当场
  即时(`instant_gold=2` 已登记,非每节点)。
- **证据**:规格 cw_investments.py(`BattlefieldEffect(bench_reroll=
  BENCH_REROLL_RIGHT3)`,bench_reroll 族效果面首个登记条目 = 族模式卡);官方原文
  cw_invest_data.py:60「每次进入新节点时，处在备战席最右侧3个位置的角色变为随机的
  同费用角色。获得2金币。」
- **推理链**:「每次进入新节点时」= 节点进入持续触发,无剩余/门槛语义 → counter 空;
  重掷结果随机(§6.3 随机面)交由观察收尾,星级分布/装备归属/被替换去向未采证不消费;
  拿卡当节点不重掷(per_node_pick_node_grant.md §4,无立即措辞,C 级佐证);+2 金
  读法 = 尾句独立句式、无触发语复述(对照定期福利金卡 gold_per_node 必复述
  「每次进入新节点时」措辞);sim 重掷面零建模(变换类既定边界,sim bench 轨迹不
  反映每节点重掷);姊妹乱成一锅粥/+ 展开存在双载荷裁决位(重掷需 BattlefieldEffect、
  爆发分支过 burst 桥需 EconomyEffect,EffectSpec 单 payload 字段不可并存),归族展开批
  先裁。

#### 公司军火更新·银(130101)

- **论断**:NODE_ENTER / while_held / BATTLEFIELD;duties = track;counter **不建**
  (每节点变异无累计/剩余语义);变异面 = 随机分支零逻辑写、靠画面读数收尾(§6.3/§6.4),
  bot 零执行端代码,真值由下一备战帧 equips 整表观察(现役观察链)覆盖;「同品质」
  = 同 category 先验(冶金炉 same_category 已登记先例,未证);发放分支「获得1件随机
  简易装备」= 泛化随机装备表行(简易 1 件),登记面分离。
- **证据**:规格 cw_investments.py(`BattlefieldEffect(equips_reroll=
  EQUIPS_REROLL_SAME_QUALITY)`,物品栏装备变异效果面首个登记条目 = 族模式卡);
  官方原文 cw_invest_data.py:86「每次进入新节点时，你物品栏里的装备变为同品质的
  其他装备。获得1件随机简易装备。」
- **推理链**:「每次进入新节点时」= 节点进入持续触发,无剩余/门槛语义 → counter 空;
  变异结果随机(§6.3 随机分支/§6.4 随机资产面)交由观察收尾,变异辖域类别集/是否
  排除自身/工具特殊类可变性未采证不消费;拿卡当节点不变异(per_node_pick_node_grant.md,
  无立即措辞,C 级佐证);duties 不设 predict(现役读链无节点进入前需预知物品栏变异的
  消费面);两条效果条目分别注册(变异条目 = 本条目,发放分支 = PICK_INVEST_EFFECTS 泛化表行)不经
  组合子(组合子辖同一效果体内多分支);sim 变异面零建模(变换族既定边界,公司人才流动
  同判);族模式卡:金(230601)/彩(330601)展开时本条目 payload 复用同词表值,差异
  全在发放分支泛化表行。

### 动作计数族

#### 淘金客(301601)

- **论断**:ON_REFRESH / while_held / STATE;duties = respond;counter **不建**——产出
  (+2XP)无剩余/门槛语义,无动态需求,单调账 refresh_paid 既有承载;产出分支 =
  世界腿(把结果写进状态副本的实现分支)已接入调用:刷新上报写端付费帧经
  `grant_effect_refresh_xp` 鸭子类型读取 `xp_per_refresh` 聚合 → `grant_xp`
  字段写,evidence `effect_refresh_xp`,fields.md §3.2.10(2026-11-04 用户裁定
  采真实写入方案,原零建模面随裁定闭合,§6.4 辖域同步收窄)。
- **证据**:规格 cw_investments.py:905-911(payload=`STRATEGY_ECONOMY['淘金客']`
  :633,xp_per_refresh=2,:152);发放 = cw_game_state.grant_effect_refresh_xp
  (调用点 = 刷新上报 `report_action_refresh_shop_param` 付费分支,免费扣减后/
  随机态分支前);官方原文 cw_invest_data.py:259「你每次消耗金币刷新商店,都会
  获得2经验值。」
- **推理链**:驱动 = 付费刷新(「消耗金币」文本排免费刷,与计数分支 refresh_paid
  同付费域);产出 = 每付费刷新事件写状态副本 +2XP(无窗口无上限 → counter 空);
  respond 姿态(刷新期望价值 +2XP)归策略层消费。

#### 采购专员·金(201201)/ 采购专员·彩(303101)

- **论断**:ON_REFRESH / while_held / BATTLEFIELD;duties = track+predict+respond;counter
  **建**(驱动 = 刷新事件,**含免费刷**;阈值 7/5 在计算侧整除触发);金/彩各自独立
  实例,(spec_id, key) 定点读天然隔离;触发时商店改写内容 = 随机面交由观察收尾。
- **证据**:规格 cw_investments.py:339-344(:345-350;`BattlefieldEffect(counter_every=7/5,
  shop_rewrite=True)`,cw_effect_inventory.py:72/:78);官方原文 cw_invest_data.py:124/
  :274「每7/5次刷新,商店会刷出5张费用相同的角色,费用为你备战席最左侧角色的费用。」
- **推理链**:「每 N 次」= 周期门槛 → 需累计量 → counter(§3 规则 3);计数含免费刷
  (用户裁定:官方未限定「用金币」,对照淘金客明写「消耗金币」的排免费写法,impacts
  §3);费用参数 = 备战席最左读数,对账核验用;备战席最左摆位 = 策略变量(respond)。

#### 合并同类项(102901)

- **论断**:ON_REFRESH / while_held / ECONOMY;duties 全空(counter 不建——出对判定
  逐刷独立,无剩余/门槛累计量);金分支 = 每次手动刷新事件条件金(出同名对 +1,
  单刷至多一笔;卡面条件式单数语义,星级不参与);burst 4 刷 = 登记期一次性发放
  (获得链登记腿)。策略源 ON_REFRESH 经济发放首条(淘金客 STATE/采购专员
  BATTLEFIELD 为同触发异 category 先例,发放过滤按 trigger∧category 天然隔离)。
- **证据**:规格 cw_investments.py(STRATEGY_ECONOMY 注册行 gold_per_refresh_pair=1
  + free_refresh_burst=4,登记形态等值迁移自 instant_gold;STRATEGY_EFFECTS 条目
  payload 引同一实例);发放 = cw_effect_inventory.apply_on_refresh_pair_gold_grant
  挂刷新上报随机态分支后,sim_backend_installed 门控、observe 通道(live 零写观察
  覆盖兜底);官方原文 cw_invest_data.py「刷新商店时，若刷新的角色中出现2个相同的
  角色，获得1金币。获得4次免费刷新。」
- **推理链**:逐刷独立条件 → counter 空;「刷新商店时」= 手动刷新动作(刷新触发
  闭集 = 节点切换 + 手动,economy.md;插入位置 = 手动动作唯一生产点,节点窗自动全刷
  另口不经此),节点切换侧待实采,披露键 STRATEGY_REFRESH_PAIR_SCOPE_UNVERIFIED
  已登记;sim 判定输入 = 采样 = 状态副本里的值,live 采样是猜测金面禁直写(零写);
  live 补账 = 游戏侧真实加金 → 下次商店入口金位实读观察锚定(感知滞后窗同披露键)。

#### 商业间谍(300201)

- **论断**:LEVEL_UP / while_held / BATTLEFIELD;duties = predict+respond;counter **不建**。
  被动分支(购买经验花费 −1)= 惰性读取入口(§6.2),不入存储;触发分支(升级时刷新商店 +
  偷最贵 3 张)= 升级值变更回调驱动(写端 = `cw_levelup_callbacks.on_level_up_change`
  spy 分支,源 = 任意经验来源升级;sim 状态副本分支消费经声明簿记队列,advance 尾
  统一排空),偷取哪 3 张 = 随机面交由观察收尾。
- **证据**:规格 `STRATEGY_EFFECTS['商业间谍']`(`BattlefieldEffect(steal_on_level_up=3)`);官方
  原文 cw_invest_data.py:244「购买经验的花费减1,升级时刷新商店,并偷取其中最贵的3个
  角色。」
- **推理链**:降价是持有期常数,读时消费(观察优先两支,§6.2)→ 无累计量;升级事件
  触发分支无计数语义(触发即结算,升级次数无需记)→ counter 空;`_EVENT_LEVEL_UP` 标记
  为升级事件保留证据,非策略计数器(键空间隔离,§7.3)。

### 即时族

#### 全员晋升(102701)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict;counter **不建**(一次性);本体
  = 选卡当场板面重写(board_rewrite='upgrade_all_cost+1'),替换面随机 → 交由观察收尾;
  登记后实例即历史(once 无推进维度)。
- **证据**:规格 cw_investments.py:679-685;官方原文 cw_invest_data.py:67「场上的所有
  角色会永久升级成比自身高1费的随机角色(最大5费)。获得2个【拆装扳手】。」
- **推理链**:once → 无进展维度;改写后板面画面直读 → 零额外 state;附带的拆装扳手
  分支 = 装备库存精确增量,已结构化出列(策略卡获得效果分支 =
  `cw_gain_effects.PICK_INVEST_EFFECTS['全员晋升']` 具名装备授予工厂经
  `gain_equipment(rand=False)` 直写 gs.equips,精密金面前置 fail-closed 申报
  在工厂;fields.md §3.2.15 获得链写入方段)。

#### 人力重组(102801)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict;counter **不建**;清场出售 =
  确定性逻辑写面(出售金按卖价公式,归属判据 §6.3 确定性分支),发牌面随机交由观察收尾;
  出售金分支无 STRATEGY_ECONOMY 条目(spec 注释自注缺口,cw_investments.py:686-689);
  sim 发牌面由后端发牌分支承接状态副本里的值直写(`cw_sim_backend
  .apply_strategy_pick_sell_all_deal`,挂 `_on_invest_picked` 选卡落地拍、呈现一次性标志位防重放,
  授予出口 `grant_bucket_names` 逐档派生桶,判据 = `STRATEGY_EFFECTS` 过滤
  `board_rewrite='sell_all_deal'` 派生禁硬编码),live 维持观察覆盖零改动。
- **证据**:规格 cw_investments.py:690-696(board_rewrite='sell_all_deal');官方原文
  cw_invest_data.py:68「出售场上和备战席的所有角色。获得1个随机的2星3费角色、2个
  2星2费角色和2个2星1费角色。」
- **推理链**:once 构同全员晋升;出售面确定性可算 → 逻辑写候选,发牌随机 → 观察
  交由观察收尾;执行时序编排(卖→发牌)= 执行链适用范围,非本篇。

#### 大裁员(202101)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict(清场+6 刷改变商店决策
  上下文,买牌/读牌对账须预知);counter **不建**(一次性 burst 无剩余期);两分支
  登记型单条目双载:出售面 = 素出售语义(`board_rewrite='sell_all_deal'`,确定性清场
  退款;×2 卖价修饰施于净额/基础价 = 缺口 G4 待实采,闭合前退款按基础公式);
  刷新分支 = `free_refresh_burst=6` 挂战场载体(burst 桥登记拍单次发放,
  **BattlefieldEffect 载体携 burst 首例**,与 free_refresh_on_node_enter 同值域、
  发放插入位置不同:登记拍单次 vs 节点边界);发牌分支非本卡卡文面——sim 发牌判据按
  「卡文是否携带发牌分支」语义值细分(`'sell_all_deal'` vs 素 `'sell_all'`),素出售
  卡不入集,sim 局零假发牌。
- **证据**:规格 `cw_investments.STRATEGY_EFFECTS['大裁员']`(payload=
  BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL, free_refresh_burst=6);
  注册行 `STRATEGY_ECONOMY['大裁员']` burst=6 = 估值面对账源,注册值原 5 = 已裁
  漂移随批订正);官方原文 cw_invest_data.py:134「出售场上和备战席的所有角色，
  获得双倍价格的金币。获得6次免费刷新。」
- **推理链**:两分支同拍各司其职(burst 桥写 free_refresh_left / 板面重写桥清场
  退款,写域不相交,序间零依赖);退款 = 场上构成依赖无字段载体(卡级 PENDING
  登记已登记,估值 fail-closed=0);卖价 ×2 净额/基础价口径 desc 未写明,禁猜维持
  缺口(fields.md §4 SellBench 修饰行单一源)。

#### 降本增效(202301)

- **论断**:INSTANT / once / BATTLEFIELD;duties = predict+track;两分支登记型
  单条目双载:出售面 = 素出售语义(`board_rewrite='sell_all'`,确定性清场退款;
  ×2 卖价修饰施于净额/基础价 = 缺口 G4 待实采,闭合前退款按基础公式);免费
  购买分支 = **uses 有界窗口与 INSTANT/ONCE 并装**(`duration_uses=6` →
  `remaining_uses` 播种,uses 维度与 duration 类别独立)——「接下来6次购买角色
  是免费的」= 获得时点起按张计的有界余量(k 张 = k 次),递减插入位置 = 买牌上报
  单点(`report_action_buy_card_param` 免费闸:免 min(k, 余量) 张、余张照付,
  全免帧零金写,拒买早退零递减),用尽移除(第 6 张买毕条目离场,后续买牌恢复
  扣金);免费帧不计花销(买牌两通道 mark_gold_spent 置位豁免,同函数刷新通道
  「非免费帧」同判);素出售不入 sim 发牌判据集,零假发牌。
- **证据**:规格 `cw_investments.STRATEGY_EFFECTS['降本增效']`(payload=
  BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL),duration_uses=6);
  注册行 `STRATEGY_ECONOMY['降本增效']` sell_price_mult=2.0 = ×2 卖价修饰对账源;
  批量递减 helper = `ActiveEffectInventory.consume_uses_up_to`;官方原文
  cw_invest_data.py:136「出售场上和备战席的所有角色，获得双倍价格的金币。你
  接下来6次购买角色是免费的。」
- **推理链**:出售面构同大裁员素出售(登记腿桥实机(live)和模拟器(sim)两边同链,姊妹卡同构);免费
  购买分支 = 免战牌 uses 载体复用(次数类首例机制),ONCE 注记只辖出售分支一次性
  语义(机译无 ONCE 移除逻辑,uses 独立播种);predict = 买牌对账须预知免费
  价,track = 次数余量剩余期量(免战牌 track=True 同形);×2 施径缺口与免费
  购买呈现面(商店牌面价格显示形态)均归实采域(停机钩子名单已登记,人工采集)。

#### 现金为王(250301)

- **论断**:INSTANT / while_held / BATTLEFIELD;duties = predict(出售后板面
  空,部署/买牌对账须预知);counter **建**(伴生数值型,先例 = 超发货币
  LOST):`counters['shield_bank']` = 出售退款合计×1000(卡文明写系数,常量
  承载),写端唯一 = 板面重写桥出售支(与退款权威写入同闸:空场退款零/出售域
  未全读 → 零记账等靠画面读数收尾,禁部分记账),登记拍单写、无推进维度
  (while_held 实例随局存活,余量读数成立)。出售面 = 素出售语义确定性逻辑写
  (大裁员/降本增效同构;卡文无「双倍」句,无卖价修饰,退款 = 标准卖价);
  护盾授予面(「每场进入战斗时前台获盾」持久被动)= 游戏侧自算,bot 零响应
  (UNIT_BUFF 族零响应教义同判;U01 sim 战斗纯随机零消费 = 结构性边界),
  counter 为状态副本里的值记账,现役零代码消费。
- **证据**:规格 `cw_investments.STRATEGY_EFFECTS['现金为王']`(payload=
  BattlefieldEffect(board_rewrite=BOARD_REWRITE_SELL_ALL));记账段 =
  cw_effect_inventory.apply_board_rewrite 出售支尾(CASH_KING_SHIELD_PER_GOLD
  =1000 常量承载,CounterKey.SHIELD_BANK 键常量);官方原文 cw_invest_data.py:200
  「出售场上和备战席的所有角色，之后每场进入战斗时，为我方前台提供护盾，护盾量
  等同于该次出售角色所获得总金币数*1000。」
- **推理链**:护盾量 = 出售面退款合计的一次性函数(先出售、后按量供盾)→
  记账点与退款同一权威判据(桥内 spec-id 门控单一源,live/sim 两边同链自动
  一致,登记腿每局至多一次无重入闸);量值 desc 明写(×1000)可建模,刷新/
  叠层/受盾位次 desc 未写 = 全部放弃(禁猜,游戏侧自算);触发面「每场进入
  战斗」零新增词表值零响应登记(§7.4 教义,候选驱动启用前提不满足)。

### 条件窗口族

#### 经验就是财富(103601)

- **论断**:CONDITIONAL / while_held / ECONOMY;duties = respond;counter **不建**(条件
  改道是持有期算子,非累计量);当场金 +4 一次结清;改道分支 pending,已定案前消费端走
  保守支 = 改道吞非购买 XP;范围部分确认 = 暂只做节点基础经验改道(用户裁定,
  2026-09-10),其余四歧义(其他策略 XP 吞否/同事件性/上限/版本变体)挂起待采。
- **证据**:规格 cw_investments.py:667-675(pending=True,xp 改道算子字段待定案后补
  payload);官方原文 cw_invest_data.py:79「获得经验时,改为获取等量金币(购买经验除外)。
  获得4金币。」
- **推理链**:改道 = 获得经验事件的产出改写(逻辑写入方改道候选),属事件产出语义而非
  实例进展 → counter 空;定案后按 verdict 回填算子字段并复推本论断。

### 战力类零响应族

#### 团队力量·银(150101)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——羁绊激活计数与 3%×N 由游戏侧自算(激活真值 = 实机 OCR
  左面板读数,currency_war_config.py「以实机 OCR 为真值」口径),登记只为审计可见。
  「非独立羁绊」= cw_factions.py 独立羁绊段七名(挚爱之人/魔术师/大守护者/命运卜者/
  救世主/头号玩家/领航员)排除,desc 明文零建模。同形先例 = 全队的希望(族首例)/
  溜佩佩/溜佩佩+;不绑阵营(泛用数值,`STRATEGY_BINDINGS` 零触碰,表外默认空绑定);
  现金分支 = 已注册名无 economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['团队力量·银']`(cw_investments.py 战力类零响应族条目);
  官方原文 cw_invest_data.py:98「每有一个已激活的非独立羁绊，小队就会获得3%前/
  后台强度。」
- **推理链**:羁绊计数随游戏内状态连续变化,无离散触发事件 → trigger 占
  PLANE_START 声明位对齐环境源 `_portal_placeholder_spec` 先例(占位零响应);
  无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md §0
  战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 应援团(150201)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**条件卡**:条件(进入战斗时上阵后排 ≥4 角色)
  与数值(15% 速度增幅)均由游戏侧自算评估施加。「后排」= 上阵后排编队非备战栏
  (drag_cw_char.py:39 `_ROWS` 三键分立;后排容量 6-9),kernel `back_capacity_of`
  观察读口零接入调用(无消费端:sim 战斗 U01 不消费 buff、live 游戏自算自显、策略侧
  选卡估值范围外)。不绑阵营(泛用全队数值,`STRATEGY_BINDINGS` 零触碰,表外默认
  空绑定);现金分支 = 已注册名无 economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['应援团']`(cw_investments.py 战力类零响应族条目);
  官方原文 cw_invest_data.py:99「进入战斗时，如果后排至少有4个角色，我方小队
  速度增幅提高15%。」
- **推理链**:条件判定/计数/buff 生效全在游戏,进入战斗拍评估,无离散触发事件 →
  trigger 占 PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位零响应);
  无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md §0
  战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 正能量(150301)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首个**恢复型(非增幅光环)**条目:恢复事件(进入
  战斗时小队每名角色恢复自身能量上限 20%)由游戏侧自算执行,能量为战斗内资源,
  与伤害减免同桶「战斗被动分支」(cw_gain_effects.py 三卡箱分支注释同源归类),
  sim 战斗 U01 零建模。不绑阵营(泛用全队数值,「恢复能量」≠能量队卡,
  `STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名无 economy →
  (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['正能量']`(cw_investments.py 战力类零响应族条目);
  官方原文 cw_invest_data.py:100「进入战斗时，我方小队恢复等同于能量上限20%
  的能量。」
- **推理链**:恢复时机/恢复量计算/能量记账全在游戏,进入战斗拍执行,无离散触发
  事件 → trigger 占 PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位
  零响应);无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md
  §0 战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记);「能量上限」
  基数 = 受益角色自身(装备同构措辞惯例推断,非 desc 逐字),游戏侧定义零行为落点。

#### 完美开局(150501)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**战中条件窗口卡**(desc 明文「战斗中」窗口,
  区别于应援团的入场拍):条件(关卡进度<40%)与数值(前/后台强度提高40%)均由
  游戏侧自算;「关卡进度」读数定义游戏侧,判读申报制不在读法间拍死(最相邻已登记
  机制 = combat.md「遭遇奖励=伤害进度达标制」战斗内进度条条,bot 零消费不接入调用)。
  「前/后台」与代码词表「前排/后排」(drag_cw_char.py:39 `_ROWS`)字面不同字,
  对应系判读非直译(全队两排泛用增幅,无位置限定,零行为后果)。不绑阵营(泛用
  数值,`STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名无
  economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['完美开局']`(cw_investments.py 战力类零响应族条目);
  官方原文 cw_invest_data.py:101「战斗中，关卡进度小于40%时，我方小队前/后台
  强度提高40%。」
- **推理链**:条件评估窗口/进度读数/增益生效全在游戏,战斗中评估,无离散触发
  事件 → trigger 占 PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位
  零响应);无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md
  §0 战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 效率员工奖(150601)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**逐体点名对象选择卡**(区别于族内既有全队/条件
  面形态):对象(进入战斗时速度最高的三名角色及其忆灵)与数值(10% 速度增幅)均
  由游戏侧自算评估施加。速度真值/排序/前三选取/并列取法全游戏侧(repo 无速度
  读口/排序原语:sim 全域零命中,kernel「速度」命中仅策略知识域词表与装备估值
  注释);「忆灵」系官方卡文词面非建模对象(kernel/sim 零建模)。不绑阵营(泛用
  数值,「速度最高的三名」系通用属性排序选择非阵营语义,`STRATEGY_BINDINGS`
  零触碰,表外默认空绑定);现金分支 = 已注册名无 economy → (0.0, False)(战力类
  不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['效率员工奖']`(cw_investments.py 战力类零响应族条目);
  官方原文 cw_invest_data.py:102「进入战斗时，速度最高的三名角色及其忆灵速度
  增幅提高10%。」
- **推理链**:对象选取/速度排序/增幅生效全在游戏,进入战斗拍评估,无离散触发
  事件 → trigger 占 PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位
  零响应);无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md
  §0 战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 基层贡献(150701)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**费用轴逐体计数卡**:计数(上阵 1 费角色逐体
  计数、3星1费按 3 计)与双属性数值(3% 速度增幅/2% 伤害减免)均由游戏侧自算
  评估施加(计数粒度/并列细则游戏侧定义,bot 零消费)。「场上」= 上阵编队
  front+back,与备战栏分立(`drag_cw_char.py` `_ROWS` 三键);kernel cost 读口群
  (card_cost/bench_char_cost/effective_cost/sell_refund)系经济域观察读口,非
  效果建模件,零接入调用(伤害减免在 kernel/sim 零数值建模,速度同域)。不绑阵营
  (泛用计数 buff,「1费角色/3星」系费用与星级通用属性非阵营语义,
  `STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名无 economy →
  (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['基层贡献']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py:103(PlazaAugment 150701)「你的场上每有一个
  1费角色，我方小队获得3%速度增幅和2%伤害减免。3星1费改为提供3倍。」
- **推理链**:计数随上阵编队费用结构连续变化,无离散触发事件 → trigger 占
  PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位零响应);无累计量 →
  counter 不建;战力数值不折金不进经济模型(invest_effects.md §0 战力类行),
  登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 榜样的力量·银(150801)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**标记式单体选择卡**:标记(战斗中伤害统计排名
  第一的队员成为【榜样】)与数值(榜样本人前/后台强度提高25%)均由游戏侧战斗中
  自算评估施加(伤害统计计量口径/并列排名第一取法/榜样标记持续期 desc 无载,
  判读申报制不在读法间拍死,bot 零消费)。repo 无可接读口:live「数据统计」面板
  时点(结算屏)/粒度(逐行明细仅喂求和,无排名解析)双不符,sim BattleOutcome
  六字段无角色级伤害统计。「榜样」系官方卡文词面非注册名域对象:kernel 命中仅
  敌侧词缀「榜样激励」comp 适配映射面(cw_comps 榜样激励键),与本卡注册名异键
  零耦合;sim/strategies 零建模。「前/后台」与代码词表「前排/后排」
  (`drag_cw_char.py:39` `_ROWS`)字面不同字,对应系判读非直译(单体两排泛用强度
  增益,无位置限定)。不绑阵营(泛用数值,「伤害统计排名第一」系通用战斗统计
  选择非阵营语义,`STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名
  无 economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['榜样的力量·银']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py:104(PlazaAugment 150801)「战斗中，伤害统计
  排名第一的队员成为【榜样】，前/后台强度提高25%。」
- **推理链**:标记随战斗内伤害统计连续变化,无离散触发事件 → trigger 占
  PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位零响应);无累计量 →
  counter 不建;战力数值不折金不进经济模型(invest_effects.md §0 战力类行),
  登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 当头一棒(150901)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首条**敌方侧效果卡**(对敌伤害+易伤,非我方单位
  增益,载体词面张力经条目 notes 显式申报,零响应桶机制对效果方向中立):波次
  触发/目标选取(生命上限最高的敌方目标,逐次选取)与数值(1000% 基础伤害/
  脆弱 30% 易伤)全由游戏侧战斗内自算评估施加,bot 零建模零观察。repo 无可接
  读口:波次与脆弱词面 kernel/sim 全域零命中(data 域词面族态 = 装备 6 处+
  卡文 2 处,全游戏侧真值),cw_sim_enemy 系难度记录建模非战斗单位,敌方 HP/
  生命上限/目标集合概念不存在。「敌方目标」系战斗通用域非阵营语义,不绑阵营
  (`STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名无 economy →
  (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['当头一棒']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py:105(PlazaAugment 150901)「每个波次开始时，
  对生命上限最高的敌方目标造成1000%基础伤害，并使其陷入【脆弱】：受到的伤害
  提高30%。」
- **推理链**:波次开始系游戏侧战斗内评估拍(sim 战斗 = U01 单次判定面,无波次
  序列/战斗内时间轴),无离散触发事件 → trigger 占 PLANE_START 声明位对齐
  `_portal_placeholder_spec` 先例(占位零响应);无累计量 → counter 不建;战力数值
  不折金不进经济模型(invest_effects.md §0 战力类行),登记形态归 UNIT_BUFF
  (游戏侧自算,bot 仅登记)。

#### 幸运喷雾(151201)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**幸运一击伤害域卡**:「幸运一击伤害提高25%」
  = 战斗内独立乘区的伤害增幅(幸运一击与暴击独立计算、互不影响,幸运一击暴伤
  基础 100%),**非泛用强度、非两边盲区形态**——机制权威版本 = combat.md 伤害公式
  三乘区节(幸运一击伤害征服乘区),零建模理由 = 游戏侧战斗真值 bot 零消费
  (后继族卡禁转引「盲区」口径;装备域同属性档已登记,desc「幸运一击伤害提高」
  系官方既有属性词)。desc 未写触发时点 = 持有期间生效,数值(25%)与对象
  (我方小队全队)全 desc 明文,零选择语义零条件分支。「幸运一击」系战斗机制名
  非召唤单位注册名(kernel 命中仅敌侧词缀克制映射/机制属性映射/敌侧依赖面,
  与本卡注册名异键零耦合),敌侧词缀域(affix「丢失幸运」等)零触碰;不绑阵营
  (泛用数值,`STRATEGY_BINDINGS` 零触碰,表外默认空绑定);现金分支 = 已注册名
  无 economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['幸运喷雾']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py:108(PlazaAugment 151201)「我方小队的幸运
  一击伤害提高25%。」
- **推理链**:增幅随战斗内幸运一击触发连续生效,无离散触发事件 → trigger 占
  PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位零响应);无累计量 →
  counter 不建;战力数值不折金不进经济模型(invest_effects.md §0 战力类行),
  登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

#### 延迟收益(200701)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**行动值时点触发卡**:「战斗开始100行动值后我方
  小队伤害增幅提高40%」= 时点型条件(达阈值后增益激活并维持)。「行动值」读数
  定义权威版本无机制条目(combat.md 已登记内容系出装攻略语境非机制定义条目,行动值在
  kernel/sim 全域零建模),读法 A(战斗内全局行动值轴经过 100 后激活)/读法 B
  (其他游戏侧口径)并列按判读申报制留痕不在读法间拍死——两读法下条件均为游戏
  侧自算、bot 行为语义完全相同,不构成二义冻结面(pending=False:触发时点/作用
  对象/数值全 desc 明文,无缺失数值面);行动值读数 bot 零消费端(sim 战斗 U01
  不消费、live 游戏自算自显、策略侧选卡估值范围外),不接入调用、不实机查。
  「我方小队」系作用对象全域非阵营语义,不绑阵营(`STRATEGY_BINDINGS` 零触碰,
  表外默认空绑定);现金分支 = 已注册名无 economy → (0.0, False)(战力类不进
  经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['延迟收益']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py(PlazaAugment 200701)「在战斗开始100行动值后，
  我方小队伤害增幅提高40%。」
- **推理链**:行动值时点系游戏侧战斗内评估拍(sim 战斗 = U01 单次判定面,无行动值
  轴/战斗内时间轴),无离散触发事件 → trigger 占 PLANE_START 声明位对齐
  `_portal_placeholder_spec` 先例(占位零响应);无累计量 → counter 不建;战力数值
  不折金不进经济模型(invest_effects.md §0 战力类行),登记形态归 UNIT_BUFF
  (游戏侧自算,bot 仅登记)。

#### 星级压制(201001)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**复合卡单条目**:clause 1 = 我方小队 10% 速度
  光环,clause 2 = 攻击条件追伤被动(「攻击星级低于自身的敌人后,额外造成1次等同
  于原伤害20%的真实伤害」),双 clause 由 effect_text 全文承载(同构先例 = 当头
  一棒伤害+易伤单条)。clause 2 触发(逐攻击命中后比较攻击者与目标敌人星级)系
  游戏侧战斗内逐攻击评估拍:敌方星级无 repo 读口(cw_sim_enemy 系难度记录非战斗
  单位,敌人信息浮层屏档已登记读数 = 等级),sim 战斗 U01 无逐攻击事件流,live 无
  逐攻击观察识别标志——星级读法 A(逐攻击命中后攻击者星级高于目标敌人星级时追加)/
  读法 B(其他游戏侧口径)并列按判读申报制留痕不在读法间拍死(pending=False:
  作用对象/数值/触发条件/效果形态/伤害性质全 desc 明文,无缺失数值面);bot 零
  消费端、不接入调用、不实机查。「我方小队」系作用对象全域非阵营语义,「星级」系
  单位养成通用轴非阵营语义,不绑阵营(`STRATEGY_BINDINGS` 零触碰,表外默认空
  绑定);现金分支 = 已注册名无 economy → (0.0, False)(战力类不进经济模型)。
- **证据**:规格 `STRATEGY_EFFECTS['星级压制']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py(PlazaAugment 201001)「我方小队获得10%速度
  增幅，攻击星级低于自身的敌人后，额外造成1次等同于原伤害20%的真实伤害。」
- **推理链**:逐攻击星级比较系游戏侧战斗内评估拍(sim 战斗 = U01 单次判定面,无
  逐攻击事件流),无离散触发事件 → trigger 占 PLANE_START 声明位对齐
  `_portal_placeholder_spec` 先例(占位零响应);无累计量 → counter 不建;战力数值
  不折金不进经济模型(invest_effects.md §0 战力类行),登记形态归 UNIT_BUFF
  (游戏侧自算,bot 仅登记)。

#### 星变(201601)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter 不建);
  payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS` 数据面表达式
  单一源);bot 零响应——本族首张**战斗变形卡**:战斗开始时使一个随机1费角色
  变为3星,星级结构变形非数值增益,载体取最邻近零响应桶 UNIT_BUFF(词面张力
  显式申报,先例 = 当头一棒对敌效果入本桶同型)。变形持续性 desc 未明文(同
  语体「永久」与「在这场战斗中」两方向标记词均缺席,同构姊妹读博深造同缺席),
  经用户裁定(2026-11-01)人为定为**临时**:变形仅当次战斗内生效,战斗结束复原,
  板面零净变化——卖价(`sell_refund`)/合成池账/星级读点不受影响,每场战斗
  开始重新随机变形一次(pending=False:裁定已定案;变形状态副本写端未建模,板面
  临时态零读写口,临时性仅申报)。触发拍(「战斗开始时」系游戏侧战斗内评估拍:
  TriggerKind 无对应成员,sim 战斗 = U01 瞬时结算随机面无开始分相,机制轴三层
  零命中)/对象选取(「随机1费角色」判读申报默认上阵参战,零响应下无消费面
  只留痕)与战斗数值全程游戏侧自算,bot 零消费端、不接入调用、不实机查;无板面/
  备战席写入面,不入 board_rewrite 词表(板面重写桥系选卡时点一次性,触发时机
  不同型)。「星级」系单位养成通用轴非阵营语义,不绑阵营(`STRATEGY_BINDINGS`
  零触碰,表外默认空绑定);现金分支 = 已注册名无 economy → (0.0, False)
  (战力类不进经济模型)。策略默认不选(用户附带指令):变形随机改写羁绊构成
  破坏策略预判,随机目标效果不入具名打分(「随机发放不可具名,不入具名打分,
  恒 off」已登记先例口径,invest_effects.md 人才引进条),选卡估值零承载恒
  off——不入 `STRATEGY_ECONOMY`/`STRATEGY_GRANTS`/立场表,现金/方向/赠卡/
  立场四组件恒 0。
- **证据**:规格 `STRATEGY_EFFECTS['星变']`(cw_investments.py 战力类零响应族
  条目);官方原文 cw_invest_data.py(PlazaAugment 201601)「战斗开始时，使一个
  随机1费角色变为3星。」
- **推理链**:战斗开始变形系游戏侧战斗内评估拍(sim 战斗无开始分相),无离散
  触发事件 → trigger 占 PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例
  (占位零响应);无累计量 → counter 不建;战力数值不折金不进经济模型
  (invest_effects.md §0 战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅
  登记)。

#### 战术义眼+(350402)

- **论断**:PLANE_START 占位形 / while_held / UNIT_BUFF;duties 全空(counter
  不建);payload = `UnitBuffRef`(官方效果原文,构建期经 `PLAZA_AUGMENTS`
  数据面表达式单一源);双腿分治——能量恢复腿 = 本条目 UNIT_BUFF 零响应
  登记,「获得1个【简易武装箱】」腿 = 获得时点效果另登 `STRATEGY_GRANTS`
  开箱分支条目(镜像 cw_gain_effects `_STRATEGY_BOX_GRANTS`,落席走
  `gain_bench_item` 原语),不入本条目辖域。bot 零响应——触发面 = 逐击杀
  (消灭普通/精英及首领敌人):TriggerKind 无击杀成员,sim 战斗 = 瞬时结算
  无逐击杀事件流,live 无逐击杀观察依据,触发轴三重皆盲零建模(pending=
  False:作用对象/数值 desc 明文,无二义冻结面);恢复分档读法 25%/75%
  (普通/精英→25%、首领→75% 首选)desc 未写明分档边界,判读申报制留痕
  不在读法间拍死,禁当定谳转引;能量为战斗内数值,恢复拍/数值/敌型分级
  全游戏侧自算,bot 零消费端、不接入调用、不实机查。「我方小队」系作用
  对象全域非阵营语义,不绑阵营(`STRATEGY_BINDINGS` 零触碰,表外默认空
  绑定);现金分支 = 已注册名无 economy → (0.0, False)(战力类不进经济
  模型),聚合零承载(aggregate_economy 输出与本卡缺席逐位一致)。
- **证据**:规格 `STRATEGY_EFFECTS['战术义眼+']`(cw_investments.py 战力类
  零响应族条目);官方原文 cw_invest_data.py(PlazaAugment 350402)「我方
  小队消灭普通/精英及首领敌人时，恢复25%/75%能量。获得1个【简易武装箱】。」
- **推理链**:逐击杀系游戏侧战斗内评估拍,无离散触发事件 → trigger 占
  PLANE_START 声明位对齐 `_portal_placeholder_spec` 先例(占位零响应);
  无累计量 → counter 不建;战力数值不折金不进经济模型(invest_effects.md
  §0 战力类行),登记形态归 UNIT_BUFF(游戏侧自算,bot 仅登记)。

## 9. 已关闭事项记录(结论与依据;不再复议)

1. **同卡叠加语义已关闭**:效果域实例按 spec_key 唯一,**无叠加合并逻辑**——不存在
   「同卡叠加两次」的 state 形态。依据:投资策略卡 3 选 1、已持有卡不复现(游戏规则
   保证;用户终裁 2026-09-10)。
2. **递减/递增混合计数器模型已关闭**:不存在递减计数器——混合模型(部分效果递减、
   递减、部分递增)由统一单调计数器(§3)取代;一切「递减/剩余」语义 = 计算侧由
   单调 counter 导出(用户裁定,2026-09-10)。
3. **hook 机制已关闭**:效果驱动不走独立事件/hook 框架(§7.5,依据四条就地)。

## 10. 待用户裁决(重大取舍单列;不阻塞本文成文与键并入设计引用)

1. **表示法迁移批位**:现行 `ActiveEffect` 递减余期表示 → 目标单字段 counter 表示
   (语义等价,§4 等价申报);迁移是纯表示法切换,批位待裁决。
2. **零注册 TriggerKind 去留**:四值保留(本文立场,§7.4 语义对齐预留)与裁减两案;
   后续建模批将逐值启用,裁减会迫使建模批改枚举面。
3. **「持续 N 节点」vs「接下来 N 节点」读法拆分**:两读法现共用「登记当节点不推进」
   守卫,躺平方向系统性多冻 1 节点;实采后按卡文逐卡拆读法,`EffectSpec.pending`
   标记随批(登记的未决问题 = impacts §3 躺平条目)。
4. **躺平 +20 金入账时点**:达 3 当刻 vs 下一次节点入口两读法;裁定倾向 = 冻结三节点
   结束进 N+3 时入账(与 §10-3 同源,实采一并定案)。
5. **躺平遭遇节点入口归类**:入口 = 遭遇屏 vs 备战帧——counter +1 时机依赖此归类;
   现判定规则下两形态均恰一次推进,不影响判定本体([node-derivation.md]
   (node-derivation.md) 场景走查)。
6. **连胜联动类 counter 有无**:记录形态两案(§5 表)——counter 空(连胜流为既有
   观察面)或按连胜事件 +1;该类在用无规格条目(关联字段 win_reward_mult/
   difficulty_per_streak 注册行已登记 `STRATEGY_ECONOMY['伟大征服']`,消费直读注册表不经
   效果清单——倍率走聚合+统一公式、难度走 M19 直读,规格条目无消费面),
   建模批到达时先裁后建。
7. **免费刷新余额上限**:设计按无上限处理(不建封顶逻辑);实采观察核对大额授予时
   余额是否溢出。
8. **墙钟型效果的计数器形态**:高效决策(「获得9999次免费刷新,但是只持续45s」,
   cw_invest_data.py:260 官方原文;注册表 `free_refresh_burst=9999`,cw_investments.py:168)
   驱动事件 = 现实时钟,非节点/动作坐标系——在用唯一墙钟卡;计数器模型是否增设
   墙钟驱动维待裁决,到达前 burst 入账 + 窗末清零分支交由观察覆盖兜底。
9. **经济效果讨论口径与实码口径对应**:讨论口径 89 条 vs 实码评估面 92 条/目录并集
   97 卡/官方全集 334 条(§5 基数申报);精确对应关系候核对。不阻塞:逐条确定目录
   以注册表全集为准(impacts §4)。
10. **注册表 verdict 回填**:固定理财已回填——位面段建模随批落地、中途拿卡
    所在位面补发经用户裁定(2026-11-01)人为定为,pending 撤除、保守支消解
    (§8 固定理财条目);姊妹固定理财+ 随同判展开批同态回填(pending 撤除,
    notes 记同判,§8 固定理财+ 条目);同触发词族公司严选随族级裁定同判入册
    (pending 定案撤除,notes 记族级裁定,§8 公司严选条目);经验就是财富
    verdict 回填待实采定案。剩余回填动作归各卡建模批随批执行。
