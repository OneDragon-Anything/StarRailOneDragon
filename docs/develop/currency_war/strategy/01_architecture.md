# 01 目标架构(分)

> 总见 [README](README.md)。本文详述三层架构、数据流、层间交互、为什么不推翻重做。

## 三层架构

### 战略层(strategic)— 阵容规划(A2,待做)
- **职责**:决定「这局/这位面打什么阵容」—— 从阵容库选 1-2 个**目标阵容(target_comp)**,并决定何时**转型**(早期打工 → 后期成型)。
- **输入**:boss 列表 + 敌人词缀(A8) + 投资环境/策略已选 + 当前 board/bench + 投资环境候选。
- **输出**:`target_comp`(目标阵容:核心阵营组合 + 关键角色 + 成型 tier 目标)+ 转型信号。
- **为什么需要**:auto-chess 的核心是「commit 哪个阵容」+「何时转型」。当前战术层只 reactive 加深领先,会锁死低上限阵容(巡海 4 封顶)。research §10.1「准备 2-3 个不冲突流派」= 多目标并行打分。
- 详:[03 阵容规划](03_comp_planning.md)。

### 战术层(tactical)— eval + 搜索(已实现 + A1/A3)
- **职责**:给定 target_comp,决定「本回合具体动作」—— 买哪张/deploy 谁/升等级/卖谁/是否 D 牌。
- **核心**:
  - `evaluate(state, target_comp)` = 阶段键控加权(A3)的(羁绊 + 向 target_comp 进度 + 经济 + 角色质量)。
  - `plan(state)` = 硬门(bench-full/gold≥0/level≤10)内,贪心选 eval-delta 最大的动作序列 + **蒙特卡洛 D 牌**(A1,刷新商店期望值)。
- **输入**:GameState + target_comp(战略层给;若战略层缺,target_comp=None,退化为「加深当前领先」)。
- **输出**:Action 序列(买/deploy/升/卖/刷新)。
- 详:[02 评估+搜索](02_eval_search.md)。

### 数据层(data)— OCR + 跟踪 + 对账(A6,部分需游戏)
- **职责**:每回合把实机画面转成准确 GameState,并保证 bot 跟踪的 deployed 不漂移。
- **核心**:OCR 读真值(gold/board/level/hp/round/shop/bench/bosses)+ bot 跟踪 deployed(身份/站位)+ **每回合重 OCR board 对账 deployed**(A6,防 dead-reckoning 漂移)。
- **为什么需要**:策略再好,读错状态就打错牌。18 回合累积漂移近必然;无对账 → 实机一跑全是错误决策却归因到策略。
- 详:[04 状态对账](04_state_reconciliation.md) + [05 数据与接线](05_data_wiring.md)。

## 数据流(每回合)

```
实机画面 ─OCR─→ GameState(gold/board/shop/bench/...)        ← 真值(可信)
                    │
                    ├─对账─→ 修正 deployed(bot 跟踪)         ← A6,以 OCR board 为准
                    │
                    ▼
            战略层:选 target_comp(开局/每位面/转型时)       ← A2
                    │
                    ▼ target_comp
            战术层:evaluate(state, target_comp) → plan(state) → Actions
                    │
                    ▼ Actions(买/deploy/升/卖/刷新)
              op 层执行(BuyShopCards/DeployBench/...)
                    │
                    ▼ bot 跟踪 deployed/deploy
            下一回合(回到 OCR 对账)
```

## 决策点 × 层归属

| 决策 | 层 | 当前状态 |
|---|---|---|
| 买哪张牌 | 战术(eval-delta) | ✅ |
| deploy 谁/站哪排 | 战术(position_pref + 空槽) | ✅(r1 修)|
| 升等级时机 | 战术(economy + 等级合适度) | ✅ |
| 卖谁(bench-full/凑整) | 战术(硬门 + 跨档) | ✅(r1 修)|
| **何时 D 牌(刷新)** | 战术(**蒙特卡洛 A1**) | ✅(A1)|
| **commit 哪个阵容/转型** | **战略(A2)** | ✅ 已做(cw_comps select_comp/maybe_pivot + shop.py 接线[D-14])|
| 事件(投资环境/策略)选哪个 | 战术(白名单 + 克制) | ✅ |
| boss 克制(comp-vs-boss 机制级) | 战术(boss_fit/comp.countered_by_bosses;decide_boss_priority 错模型已删) | 🟡 boss 数据采完,机制建模 task#73(策略-stage) |
| 装备合成/分配 | 未建模 | ❌(待做,长链收益)|

## 为什么不推翻重做

review r2 结论:**可复用内核正确**(前向模型 `simulate` + 纯函数决策 + 配置口 + 机制/meta 分层),推翻会丢掉这些已测的资产。缺的是**搜索深度**(A1,已加蒜特卡洛 D 牌)+ **规划层**(A2,阵容)+ **干净目标结构**(A3,已加阶段键控)+ **概率模型**(A4,牌池)+ **状态对账**(A6)。这是「在正确骨架上补齐缺失的 2/3」,不是重写。

**明确反对只调参**:1 步贪心 + 静态 eval 结构性无法表达「何时 D 牌 / commit 哪个阵容 / 阶段目标切换」(research §10 的 A8 决策核心)。A1 已解 D 牌;A2 解阵容 commit;A3 已解阶段切换。剩 A4/A6 是地基与精度。
