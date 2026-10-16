# 专家顾问入池建模修正(expert-pool-unlock)

## 1. 背景与问题

官方机制([economy.md](../../../game/currency_war/research/economy.md) §1,官方🟢 + 用户口述双源):**专家顾问初始不参与普通商店招募**;对局中经【投资环境】/【投资策略】/战利品【专家邀请函】三通道解锁后,本局内才可在商店被购买/升星/穿戴装备。用户 2026-10-16 报告:牌库逻辑把青雀这类专家角色当普通角色放进了牌库。

代码现状缺陷(2026-10-16 排查):

1. `cw_pool.fixed_pool()` 以「注册表全角色」为基础牌库 → 9 名专家(青雀/停云/加拉赫/桑博/刃/貊泽/佩拉/姬子/银狼)按普通副本数(1/2 费 27、3/4 费 9)默认在池,商店可自然刷出——与机制矛盾;
2. `extra_experts` 参数(「专家入池追加副本」首版建模,自标注待核)**零调用方**:sim `deal_shop` 与实机刷新采样腿均未传,死参数;
3. 容器无「已解锁专家」状态:`cw_gain_chain` advisor 道与骇客银狼效果体均以「商店池无容器字段」为由退化为遥测申报行(`DEFECT_ADVISOR_DECL`);骇客银狼另加「直接入席」近似腿,与卡文「获得专家顾问【银狼】,并使其在本局游戏中加入商店」不符(卡文语义 = 入商店,非直接送单位);
4. `cw_shop_odds.DISTINCT_CARDS_PER_COST`(v 值,刷牌概率分母)含专家 → 全部 p/v 类概率计算分母偏大。

## 2. 修正设计

### 2.1 专家名单进角色注册表(单一源)

`Character` 新增 `is_expert: bool = False`;9 名标 True。名单权威 = plaza `is_expert` 字段(economy.md 口径)+ `docs/game/currency_war/data/characters/*.md` 档位标注,两源一致;`tools/cw/gen_plaza_chars.py` 交叉核对器扩展 is_expert 逐条核对。

### 2.2 解锁状态一等化(容器字段)

`GameState.unlocked_experts: Field[tuple[str, ...]]`:本局已解锁入池的专家规范名,开局种子底座 `()`,只增不减(现役解锁通道无回收语义;装备出售等边界无证据,不建回收)。

### 2.3 池派生(cw_pool)

- `fixed_pool()` = 注册表**非专家**角色 × `POOL_COPIES_PER_CARD`;`extra_experts` 参数退役(死参数 + 追加语义不成立——基础池已排除专家,入池 = 解锁授予,非追加);
- `remaining_pool`/`drawable_names` 从 `gs.unlocked_experts` 并入专家副本(每名 `EXPERT_COPIES_ASSUMED = 9`,保留待实机核披露);守恒检查沿用(摸个鱼吧 II/III 直接给单位、held 超出未解锁名 → 按名遍历 fixed 天然不检查,不误炸);
- `grant_bucket_names`(效果随机授予出口)维持**不含专家**(「专家 ∈ 授予采样空间」无定案,维持既有 v0 口径;该出口现役零调用方,无行为影响);
- 商店发牌消费端(sim `deal_shop`、实机刷新采样腿)**零改动**——池派生内部消费 gs,两执行面自动正确。

### 2.4 解锁写端(kernel 获得链,两执行面同源)

| 通道 | 写端 | 备注 |
|---|---|---|
| 投资环境/特邀专家 portal(`ENV_GIFTS` advisor=True 4 条) | `on_env_gained` advisor 道:写 `unlocked_experts` | `DEFECT_ADVISOR_DECL` 申报行随权威写道退役 |
| 投资策略(`STRATEGY_GRANTS` advisor=True 11 条) | `on_strategy_gained` 新增 advisor 道(与 env 对称查表) | 非 advisor 策略赠卡仍属既有效果推广批缺口,不扩本批 |
| 装备获得(`EQUIP_ACQUIRE_CONSEQUENCES`:分身墨镜/Max → 银狼) | `on_equipment_gained`:送单位腿保留(口述权威 2026-09-18)+ 追加解锁写 | 卡文「解锁并获得」= 入池 + 送单位两腿;数据拷贝仪Max → 银狼LV.999 非专家,不写 |
| 专家邀请函选卡(`report_action_pick_expert_invite_param`) | 首版申报行披露 | 候选名不可观察(实机 payload 无候选名/sim '' 纯转移),解锁登记待候选名观察建档批;真值归观察覆盖 |
| 骇客专家:银狼(策略效果体) | 效果体删入席腿与池申报行,解锁由策略 advisor 道统一写;改件腿保留 | 官方卡文 = 入商店,非送直接单位 |

### 2.5 v 值修正(cw_shop_odds)

`DISTINCT_CARDS_PER_COST` 派生排除专家(基础池口径):1 费 20→14、2 费 15→14、3 费 14→13、4 费 14→13、5 费 9 不变。消费方(cw_intention/cw_line_switch/cw_registry/策略层 odds/vopt/levelup、economy 期望模型)纯传导,不改代码。解锁专家作为额外种类不进静态 v(偏差 ≤1/13 量级,接受;动态 v 需解锁状态穿透纯函数签名,不入本批)。

## 3. 影响面与取舍

- **sim 对局行为**:商店不再自然刷出 9 名专家(发牌分布修正——本批目的);骇客银狼从直接入席变为入池可刷;含专家策略(青雀刷牌流等)的 sim 强度结论需重跑才可引用;
- **策略层数值**:v 值变小 → 刷牌概率分母类计算全体更准,阈值行为有微移;
- **已知缺口披露**(不阻塞,沿现有「查无效果安静不写/真值归观察覆盖」纪律):① 邀请函解锁名字不可观察(首版申报行);② 「快请专家·金/彩」效果文本残缺(随机专家顾问?)未建模,该通道解锁漏登记;③ `EXPERT_COPIES_ASSUMED = 9` 待实机核;④ 人才下沉/黑塔纪元特殊池/援军类池突变既有未建模,不在本批;
- **正本同步**:`11_shop_decisions.md` §8 池结构突变条已含「专家解锁入池(v_c 重算)」,补充「初始不在池」语义;各模块注释随代码更新。

## 4. 测试

- 新增:专家默认不在 `drawable_names`、解锁后进池且按费档归档、`on_env_gained`/`on_strategy_gained` advisor 解锁写、分身墨镜解锁+送单位双腿、v 值排除专家;
- 更新:fixed_pool/守恒/advisor 申报行/骇客效果体相关既有断言(按测试纪律:代码修正,期望随代码更新并注明依据 = 官方机制双源)。
