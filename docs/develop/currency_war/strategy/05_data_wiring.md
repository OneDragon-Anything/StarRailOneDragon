# 05 数据与接线(分)

> 总见 [README](README.md)。策略输入数据(OCR 字段 + meta 表)+ OCR→GameState 接线 + op 层接入。
> **review r1(方案)修正**:GameState 完整字段表单一真相源(连贯性-3)、read/reconcile 签名+失败语义(可实施性-4)、每回合 op 序列图(可实施性-3)、补 装备/巨星/遭遇/连胜 OCR(完整性)。

## GameState 完整字段表(目标态,单一真相源,连贯性-3)

| 字段 | 类型 | 来源 | 状态 | 游戏? |
|---|---|---|---|---|
| gold | int | read_gold(右上数字) | ❌ 待补坐标 | 是 |
| round_num | int | read_round(进度 X-Y) | ❌ | 是 |
| level | int | read_level | ❌ | 是 |
| plane | int | read_plane(或 round 推) | ❌ | 是 |
| hp | int | read_hp | ❌ | 是 |
| win_streak / loss_streak | int | read_streak(连胜/连败) | ❌ | 是 |
| **board** | dict[str,int] | **read_active_synergies**(左面板) | ✅ 已有 | 是 |
| **deployed** | list[BenchChar] | bot 跟踪 + reconcile 对账 | ✅ 跟踪 | 对账需游戏 |
| shop | list[ShopCard](名+费+阵营+星) | read_shop_full | ✅ 阵营;名/费/星待补 | 是 |
| bench | list[BenchChar] | read_bench(SIFT/OCR) | ❌ | 是 |
| bosses | list[str] | read_bosses(开局简报) | ❌ | 是 |
| **active_env** | str | decide_event 选完写入(投资环境名) | ❌ | 是(选)+非游戏(逻辑) |
| **enemy_affixes** | list[str] | read_affixes(位面/节点词缀 OCR) | ❌ | 是 |
| **equip** | dict[char_id,list[Equip]] | read_equip / bot 跟踪 | ❌ | 是 |
| key_equips_owned | list[str] | bot 跟踪(补给出) | ❌ | 是 |
| bench_full_flag | bool/None | OCR「备战席已满」 | ❌ | 是 |
| **confidence** | dict[str,float] | OCR 引擎原生分 | ❌ | 是 |
| encounter_options / supply_options | list | read_encounter / read_supply | ❌ | 是 |

## 签名 + 失败语义(可实施性-4)
```
read_game_state(ctx) -> GameState
  # 各字段 OCR 失败 → 用上回合值 + confidence[field]=0;不抛错(对 None 安全降级)
reconcile(state, ctx) -> GameState
  # 纯函数,返回修正后的新 state(不 mutate);详 04
select_comp(state, config, bosses, envs) -> Comp      # 战略层(开局/每位面/转型时)
maybe_pivot(state, target_comp, config) -> Comp | None # 转型信号检查(每回合)
plan(state, config, faction_priority, target_comp) -> list[Action]
decide_event/encounter/supply/megastar(options, state, config) -> 选择
```

## 每回合 op 序列图(可实施性-3)
```
battle_loop 检测「备战」画面
  → read_game_state(ctx)                    # OCR 全字段(失败用上回合值)
  → reconcile(state, ctx)                   # 对账 deployed(A6 多层 L0-L3)+ 置信度
  → [每回合] select_comp                     # 战略层选/校 target(2026-08-03 用户:每回合响应商店随机+位面中投资策略/环境)
  → [每回合] maybe_pivot                     # 转型信号?(触发则切 target)
  → plan(state, config, faction_priority, target_comp)  # 战术层 → Actions
  → 逐个执行 Action(BuyCard/Deploy/LevelUp/Sell/Refresh)
       每个动作后 post-action verify(OCR 确认;失败回滚+重试)
  → 出战
  → [下回合 read 前] PerformanceTracker.record(round_outcome)  # 观测驱动主轴:hp 差分 + 双侧 OCR(boss HP/伤害/击杀)+ comp_tag + intentional_fold(详 10)
事件分支(投资环境/策略/遭遇/补给/巨星):
  → decide_event / decide_encounter / decide_supply / select_megastar
```
**select_comp 时机**:**每回合跑**(2026-08-03 用户定调,详 03)—— 投资策略/环境选择在位面中进行 + 商店强随机,需每回合响应;maybe_pivot 每回合检查转型信号。性能预算(02 R2-17 / 06 P2-2)需相应放宽(必要时 select_comp 结果缓存/降级)。

## meta 数据表(非游戏可建)
| 表 | 内容 | 状态 |
|---|---|---|
| FACTIONS(31 羁绊) | 名+类别+tiers+效果 | ✅ cw_factions.py(赛季级 meta,改代码+测试;或抽 yml,见 README 分层)|
| 角色花名册(74) | 名+命途+费用+阵营+流派 | ✅ ../../../game/currency_war/data/characters.md(待接 char→阵营/费用查询)|
| 投资策略/环境白名单 | 名+优先级 | ✅ config T0 子集(可扩)|
| **COMP_LIBRARY** | 阵容库 | ❌ 待建(A2)|
| SHOP_REFRESH_TABLE | 费用刷新概率 | ❌ 待补(A4)|
| 装备图鉴(~130) | 名+效果+合成 | ✅ ../../../game/currency_war/data/equipment.md |
| 遭遇词缀表 | 词缀+对策 | ❌ 待建(research+实机)|

## 接线状态
- ❌ BuyShopCards 仍用旧 smart_buy_decision(r1 #08)—— 接线第一件事(阶段 5)。
- ✅ decide_event 纯函数,op 可直接调(事件 handler 已接)。decide_boss_priority 已删(错模型,boss 走 boss_fit/countered_by_bosses)。

## 游戏/非游戏边界
- **非游戏**:FACTIONS/角色/事件白名单/装备图鉴数据、COMP_LIBRARY、决策逻辑(plan/eval/select_comp/decide_*/reconcile 骨架)、蒙特卡洛 D 牌、阶段键控、测试。
- **需游戏**:所有 read_* OCR、reconcile 实机对账、post-action verify、op 接线、实机测胜率、权重/概率表校准。

**当前推进**:星铁未开 → 先做非游戏(阶段 2 A2 阵容 + 阶段 3a A4 牌池);阶段 4-6(OCR/接线/实测)等星铁。
