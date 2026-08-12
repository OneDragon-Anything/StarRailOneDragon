# 0103 — target comp 牌归属用全羁绊匹配(治本流派/阵营断裂)

- **Status**: accepted
- **Date**: 2026-08-12
- **Related**: cw_chars `Character`(factions/flows/independent 分离)/ CLAUDE.md 游戏数据单一源 / events 3.5.5(DOT 实跑 P1 输根因)

## Context

货币战争角色建模分 **阵营(`factions`)** + **流派(`flows`)** + **独立(`independent`)** 三类羁绊,它们都是激活门槛
(2/3/4 羁绊)。`comp.factions` 是 comp 的**核心羁绊组合,可含阵营也可含流派**(如 DOT 队 `["持续伤害"(流派), "星核猎手"(阵营)]`)。

但买/deploy/sell 决策用的 `card.faction` / `bc.faction` = `Character.factions[0]`(**只阵营,丢流派**,cw_observation/cw_state 构造时)。
于是所有「角色侧匹配 `target.factions`」处(`card.faction in target.factions`)对**流派主派 comp 断裂**:

- 艾丝妲 = 阵营「银河学者」+ 流派「持续伤害」→ `card.faction=银河学者` ∉ DOT.factions([持续伤害, 星核猎手])→ **误判 off-target**。
- 后果(commitment prefilter 等 8 处):commit 后(或 shop 有 target 卡时)流派过渡/补充角色被跳过 →
  凑不出 2DOT(桑博+艾丝妲)过渡 → P1 弱输(**实跑 DOT 队 P1 boss hp=1 输根因**,非 DOT 本身弱 —— 攻略确认 DoT 是 P1 权威过渡)。
- 影响所有流派主派 comp(DOT/击破流萤/燃血万敌/追击…),不只 DOT。

注:**评分层 `state.board`(OCR 左面板)含流派**(游戏画面显示流派羁绊),故 `form_progress`/`transition_tempo_score`/`synergy_score`
用 board 是通的;断裂只在 buy/deploy/sell 层(角色侧 `card.faction`)。

## Decision Drivers

1. **治本不叠补丁**:根因是角色侧只存阵营不存流派 → 用角色**全羁绊**匹配 comp.factions,非单阵营。comp.factions 含流派是合法建模,不该回避。
2. **单一源**:角色全羁绊查 `CHARACTERS` 注册表(CLAUDE.md 游戏数据单一源),非到处硬补 card.faction。
3. **最小结构接线**:不改数据类(`BenchChar`/`ShopCard`),只加查询 helper + 统一替换 target 匹配处。

## Considered Options

- **A(选)**:加 `_char_synergies(name)`(查注册表 → factions ∪ flows ∪ independent)+ `_card_hits_target(name, faction, target)`
  (全羁绊 ∩ comp.factions 非空 或 name∈core_chars),统一替换 8 处 target 匹配。最小、治本、单一源。
- **B(否)**:`BenchChar`/`ShopCard` 加 `flows` 字段。否:改数据类影响面大(所有构造处 + simulate/read 路径);
  且 `card.faction` 本是 OCR 后查注册表派生(`factions[0]`),再加 `flows` 重复查询;helper 查注册表更干净(name 是真相源)。
- **C(否)**:`comp.factions` 拆成 `comp.factions`(阵营)+ `comp.flows`(流派)。否:`comp.factions` 含流派是合法(comp 核心羁绊可是阵营或流派),
  且 `form_tiers`/board 层都用 `comp.factions` 含流派(OCR 通);拆开反而双源 + 改 comp 定义面大。问题在角色侧丢流派,非 comp 侧。

## Decision

选 A。`cw_decisions.py` 加 `_char_synergies` + `_card_hits_target`,8 处 target 匹配统一替换:

| 处 | 函数 | 旧 | 新 |
|---|---|---|---|
| buy prefilter off-target | `_best_improving_action` | `card.faction not in target.factions and name∉core` | `not _card_hits_target(...)` |
| buy prefilter shop-has-target | 同上 | `c.faction in target.factions or name∈core` | `_card_hits_target(c...)` |
| buy _saving target 判定 | 同上 | `card.faction in target.factions or ...` | `_card_hits_target(...) or priority` |
| deploy cap | `_should_deploy` | `bc.faction in target.factions or char_id∈core` | `_card_hits_target(bc...)` |
| spread 罚豁免 | `_concentration_delta` | `card.faction in target.factions or name∈core` | `_card_hits_target(...)` |
| bench-target 奖励 | `evaluate` | `bc.faction in target.factions or char_id∈core` | `_card_hits_target(bc...)` |
| D 牌 shop-has-target ×2 | `_best_improving_action` | `c.faction in target.factions or name∈core` | `_card_hits_target(c...)` |

`name` 空未识别时用 `card.faction`(OCR 阵营)兜底(虽只阵营,聊胜于空)。**board 层(L752 `_roll_for_target`)不动**
(`state.board` OCR 含流派,正确)。

单测 `test_cw_target_matching`(4):`_char_synergies` 含流派+独立 / 流派角色(艾丝妲/椒丘)识别为 DOT target /
真 off-target(佩拉/三月七/藿藿)False / name 空 faction 兜底。全套 cw 测试 295 passed。

## 后续

- 此修让流派过渡角色 commit 后**可买**(prefilter 不再误跳)。但「主动凑 2DOT 过渡填空位」的定向买牌逻辑仍缺
  (`transition_chars` 未集成买/卖,cw_decisions:1014 注释)—— 靠 evaluate 评分挑最优 + prefilter 不跳,间接鼓励。
  主动过渡公式(2DOT + 贝洛伯格/银河学者/治疗小羁绊)属阶段 7 策略调优,另记。
