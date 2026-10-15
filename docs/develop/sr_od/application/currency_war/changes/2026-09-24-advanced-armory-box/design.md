# 进阶武装箱策略发放 迭代设计(总纲)

## 0. 元信息

- 迭代目标:进阶武装箱端到端可达——3 张棱彩策略卡(战术义眼++/保守派/快请专家·彩,`data/cw_invest_data.py`:335/:346/:362)的箱腿登记与发放执行,复用上一迭代建成的开箱链路(弹窗锚族名化/读数闸/选卡)与占席道具落位语义。
- 承接出处:用户指令(2026-09-24)「同理的,也对进阶武装箱做这个」——姊妹迭代 `2026-09-24-scheduled-env-gifts`(已闭环)建成的通道与流程面在本迭代消费。
- 状态:定稿
- 文档清单:无详设(单文档方案,§2 即完整设计)

## 1. 问题与动机

**现状症状**:

1. **授予卡零入口**:3 张棱彩策略卡的「获得1个【进阶武装箱】」腿无处登记也无从执行——
   `PICK_INVEST_EFFECTS`(策略卡获得效果注册表,现役单行骇客专家:银狼,
   cw_gain_effects.py:143)查无效果安静不写;策略打分表 `STRATEGY_GRANTS`
   (cw_investments.py:1369,83 条 = 68 白得 + 11 顾问 + 4 反扫补网,计数测试
   test_cw_invest_strategy.py)现役只登记角色发放,无箱腿。
2. **占席道具发放无公共原语**:kernel 落位原语 `_place_bench_item` 为模块私有
   (cw_gain_chain.py),策略效果体(cw_gain_effects.py,与链模块双向破环约束)
   无法消费——骇客卡的 bench 腿走 `gain_character`(角色),占席道具无对应公开口。
3. **词表供给断点**:`BENCH_ITEM_NAMES`(溢出位身份 kind 判定单一源,
   cw_investments.py:1501-1504)从两张 GiftGrant 授予表派生——授予数据不入表,
   进阶武装箱落溢出位会被误判成角色。

**根因归层**:语义层——策略发放面缺「占席道具」形态(登记表无数据、执行表无效果体、
原语无公开口);非流程层(流程面上一迭代已就绪,见 §2.5)。

**解决到哪**:

- 3 张卡的箱腿:`STRATEGY_GRANTS` 登记(items_immediate)+ `PICK_INVEST_EFFECTS`
  箱腿效果体 ×3 + kernel 公共占席道具发放原语;
- `BENCH_ITEM_NAMES` 经既有派生式自动覆盖进阶武装箱(零额外改动,设计断言测试）；
- sim E2E:选卡 → 备战席落箱(选卡时点立即发放,非定时——三卡原文均为获得时点直读)。

**明确不解决**(防外溢):

- 三卡的**战斗被动腿**(战术义眼++能量恢复/保守派伤害减免)——非「获得时点」效果,
  归策略效果建模批(获得效果注册表只辖获得时点容器写腿,cw_gain_effects.py:64-68
  注册纪律);快请专家·彩的能量恢复腿同此;
- 快请专家·彩的**2 个【】空括号腿**(数据源缺口,plaza 数据生成件原文即空,禁猜)
  与**好运令牌腿**(非占席道具,归消耗品/登记面,GiftGrant 语义 = 占席道具发放);
- **简易武装箱授予策略族**——凡 PlazaAugment effect 含『简易武装箱』授予的
  策略卡全集(定义源 grep 枚举,现势 17 张,禁逐名冻结防漂移)另批;其中
  龙虎兄弟狸/贸易专家:停云已因角色腿在 STRATEGY_GRANTS 在册而箱腿未登记,
  为全集内已部分登记的边界卡;环境侧 PlazaPortal 含简易武装箱授予者另有
  4 张(火药味已登记,红钻贵族/蓝钻贵族/专家研讨会未建模),随环境批;
- 进阶武装箱**备战槽图标模板**与开箱动作 op 对非简易箱的支持——实机裁片缺,
  与特权武装箱同属 T-421 余部,待实机首遇(现役 round_fail 响亮暴露);
- 打分面:占席道具不进打分(机制与裁定指针见 §3 取舍 3,零改动)。

## 2. 方案

### 2.1 登记:STRATEGY_GRANTS 三条 items_immediate

`STRATEGY_GRANTS` 增三条(键 = 注册表规范名,与 INVESTMENT_STRATEGIES 同键空间):

- `'战术义眼++'` / `'保守派'` / `'快请专家·彩'`:
  `GiftGrant(items_immediate=('进阶武装箱',))`——效果原文「获得1个/一件【进阶武装箱】」
  直读,数量 = 元素重复次数(与 ENV_GIFTS 同约定);快请专家·彩只登记箱腿
  (§1 明确不解决的两腿不入表,表目注释申报)。

`_validate_strategy_grants`(import 即炸,cw_investments.py:1546)扩展:
③空发放集判定从「即时角色/条件角色全空」并入 `items_immediate`(四通道全空才拒,
沿 `_validate_env_gifts` 同款先例);其余校验(孤儿键/角色名漂移/反扫闭集)不变
——反扫闭集辖「获得…角色名」直读,箱腿不受其强制,登记属机制事实留 kernel 自愿面。

**BENCH_ITEM_NAMES 自动覆盖**(设计断言,测试):派生式
`(*ENV_GIFTS.values(), *STRATEGY_GRANTS.values())` 的 items_immediate
(cw_investments.py:1502)——登记即入词表,溢出位身份 kind 判定自动正确,
消费点(`_build_pool`/sell_bench 溢出腿)零改动即受益。

### 2.2 kernel 公共原语:gain_bench_item

`cw_gain_chain.py` 新增公开原语(命名沿 gain_character/gain_equipment 系):

```
gain_bench_item(gs, item, *, rand: bool, sig: ChannelSig,
                evidence: str, producer: str = GAIN_CHAIN_PRODUCER) -> bool
```

实现 = 现有 `_place_bench_item` 加 `producer` 形参(缺省
`GAIN_CHAIN_PRODUCER`,现调用点 on_env_gained 行为不变)+ 公开薄包装。
落位语义全部复用(备战空槽 → 席满溢出落位 → 溢出位被占零写留证,
2026-09-24 道具落位语义);rand 语义:三卡箱腿 = 确定发放,效果体传
`rand=False`(gain-chain.md §5)。

### 2.3 执行:PICK_INVEST_EFFECTS 三条箱腿效果体

`cw_gain_effects.py` 注册表增三条,效果体 = 共享工厂生成的闭包:

- **发放名单单一源**(阻断项修订:禁效果体闭包常量与登记表双源漂移):
  模块级 `_STRATEGY_BOX_GRANTS: dict[str, str]`(卡规范名 → 发放道具名,
  三键);注册表三条由工厂从该表生成;**一致性测试** = 表集与
  `STRATEGY_GRANTS` 三卡 `items_immediate` 逐对相等 + 席满行为测试
  (bench 满时 pick → `overflow_card == '进阶武装箱'`,名字经溢出落位
  真值暴露——BenchSlot 本身与名解耦,备战断言发现不了名字漂移);
- 签名沿现役 `(gs, *, sig, rng) -> list[str]`(rng 不消费——箱腿确定发放,
  注册表分派统一传参);
- 效果体惰性 import `gain_bench_item`(运行时解析破环,沿骇客卡 :97-100
  模块 docstring import 方向声明);
- 返回步串 `box_grant:<名>(placed=…)`(沿骇客卡 steps 形态);
- 三卡战斗被动腿不在效果体(§1 明确不解决;未建模申报归 impacts 正本,
  见 landing 正本清单)。

### 2.4 sim E2E 可达性

- 策略 offer 日程 `((1,3),(2,2),(3,2))`(cw_sim_backend.py:388,U07①),
  品质掷点均匀占位含棱彩(:402-404)——offer 槽在 P1/P2 即存在,三卡端到端可测;
- 测试路径 = 选卡注入惯用法(沿 test_strategy_pick_chain_burst_gold:
  `invest_strategy_opts` 写入 + `report_action_pick_invest_strategy_param`,
  该用例无 declare_world 步)→ 断言 bench `supply_box`×1 + 容器队列不受扰
  (立即发放,不经 pending_item_grants)。

### 2.5 流程侧零改动认定(上一迭代成果的消费声明)

- 武装箱获得弹窗锚 = `标识-武装箱`(text=武装箱)——对标题「进阶武装箱」
  LCS 3/3=1.0 命中(分母=登记文本,find_by_lcs str_utils.py:44),与特权
  弹窗同款数学(scheduled-env-gifts design §2.6);
- 选卡读数闸上限 = 注册表最长名派生(`_CARD_NAME_LEN_MAX`)——进阶装备
  36 件基名全部 ≤6 字(cw_equipment_data.py:72-107),远低于闸限,归一化
  精确命中域;
- 选卡候选归一化域 = EQUIPMENT_ROSTER 全量,进阶 36 件在册(:72-107);
- 开箱动作 op 的备战箱识别 = 简易箱模板单模板(待实机扩多模板,特权/进阶
  同属 T-421 余部)——首遇前 round_fail 响亮暴露,属既有申报形态。

## 3. 关键取舍

1. **PICK_INVEST_EFFECTS 效果体 vs STRATEGY_GRANTS 通用发放腿**(在
   gain_invest_strategy 里消费 STRATEGY_GRANTS.items_* 自动发放):选效果体。
   注册表的注册纪律明文「效果函数只辖获得该卡后的容器写腿」(cw_gain_effects.py:
   64-68)——获得时点发放本就是它的辖域;STRATEGY_GRANTS 保持「登记/打分
   数据表」语义不升级为可执行,两表职责分离不破(对抗审⑨ 的既有裁定)。
2. **快请专家·彩只登记箱腿**:GiftGrant 语义 = 占席道具/角色发放;好运令牌
   非占席道具(走消耗品域),空括号腿数据源缺口禁猜——两腿以表目注释申报,
   执行面查无即安静不写,真值归实机/数据源勘误。
3. **打分零改动**(机制事实 + 裁定指针):`grant_gift_value` 只读角色发放
   (gift_value.py:52-63),items-only 条目经消费口恒 off → 0 分
   (cw_comps.py:1253-1257)——箱条目自然 0 分,策略层零触碰;「占席道具
   不进打分」裁定的登记处 = cw_investments.py ENV_GIFTS 道具通道注释
   「档位机器恒 off(不进打分)」,本迭代沿用不另立。
