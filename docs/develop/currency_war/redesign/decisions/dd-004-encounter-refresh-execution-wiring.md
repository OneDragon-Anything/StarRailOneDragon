# DD-004:遭遇分支刷新执行链接线——决策建议字段长期无消费端,接线并登记触发源缺位

> 状态:已落地(2026-09-01;受影响测试全绿)。

## 背景

`EncounterPick.refresh`(全分支词缀克 comp → 刷新换批避开)决策侧自 P1 就绪且有纯逻辑测试锁
(`test_cw_decisions.test_decide_encounter_refresh_when_all_counter` / `..._no_refresh_when_used`),
但 `HandleEncounter` 只消费 `pick.idx`,`refresh=True` 被静默丢弃——「刷新换批」策略意图从未生效。

分支刷新是游戏内真实机制,能力由**优势布局「分支刷新」授予**(bwiki 优势布局表:选择遭遇节点
分支时,可刷新 1 次,重置所有分支难度和奖励;`docs/game/currency_war/data/advantage_layouts.md`;
competitors.md 节点表同口径「可刷新 1 次重置分支难度/奖励」)。UI 形态 = 底行「剩余次数:N」文本 +
其左侧圆箭头钮(归档帧 `sr-od-test/screens/货币战争-遭遇节点/default.webp`,OCR 全量含
「剩余次数：1」);2026-08-11 穷举交互验证漏验此钮,点击行为无实机记录。

## 裁决

1. **handler 接线三段式**(与投资策略刷新流 ADR-0146 同构):OCR「剩余次数:N」>0 且本局未用 →
   文本锚定点刷新圆钮(文本中心左偏 -110px;单帧目测值,**待实机 CV 复核精化**——投资策略同模式
   -88px 为 CV 实测值)→ 验效双通道(次数扣减 = 权威;卡面签名变化 = 兜底)→ 生效则重读选项 +
   `refresh_used=True` 重新决策 → 按新决策选卡。
2. **session 单次标志 `_encounter_refresh_used` 发出点击即置位**(不等验效):优势布局每局只授
   1 次,且存在「返回备战界面 → 返回遭遇选择」合法重入路径,点偏不置位会重入反复尝试;验效失败走
   失败安全(按原评分选卡照常推进,不重试、不阻塞)。
3. **触发源缺位登记(非本批可修)**:`read_encounter_options` 的 affixes 恒空(卡面 UI 不显词缀,
   词缀在「敌方信息覆盖层」,该覆盖层未建档)→ `decide_encounter` 全克判定恒不触发 → 本执行链
   就绪但**当前不会开火**,接线期间零行为变化。开火前提 = 敌方信息覆盖层建档(需实机交互采帧)+
   词缀 → `EncounterOption.affixes` 读数通道。

## 约束范围

- 修改面 = `handle_encounter.py` + `cw_node_obs.read_encounter_refresh_count` +
  `StrategySession._encounter_refresh_used`;`decide_encounter` 决策语义零改动(既有测试锁原样)。
- sim 侧 encounter 刷新未建模(`engine_p1` 只建模补给刷新)——实机接线后的 sim 保真度跟进项,
  不在本批。
- 刷新钮点击行为与「未激活布局时剩余次数行的 UI 形态」待实机验证;验效失败安全分支兜底误判,
  最坏退化 = 少刷一次(与接线前行为一致)。

## 出处

- 机制:bwiki 优势布局表(`docs/game/currency_war/data/advantage_layouts.md`)/ competitors.md 节点表;
- UI 证据:归档帧 `sr-od-test/screens/货币战争-遭遇节点/default.webp`(OCR「剩余次数：1」)+
  `docs/game/screens/currency_war_encounter.md`;
- 同构先例:投资策略刷新流 ADR-0146(handle_invest_strategy._try_click_refresh)、
  补给刷新流(run_supply_node,session `_supply_refresh_used` 单次标志)。
