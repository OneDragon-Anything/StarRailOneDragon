# sim 画面流程保真度修复 · 排查与方案

> 状态:调研完成,待实施。触发 = 2026-10-29 sim 单局复盘发现「补给/遭遇/boss 节点零备战决策」,用户裁定:sim 必须忠实模拟游戏引擎的流程,全面排查漏项并修复。

## 1. 实机流程模型 v2(权威口径,用户口述 2026-10-29)

**1-1 开局**:纯备战画面,触发开局奖励(开局补给动画),**不自动弹商店**。

**通用节点流转**(每个战斗结束后):

```
战斗结算画面点确认
  → 下一个节点的备战画面        ← 过渡帧①:短暂、不可操作
  → 按节点类型/环境效果弹窗      (选择补给 / 选择投资策略 / 选择遭遇 / BOSS简报 / 位面简报 / 巨星 / 骇入策划…)
  → 弹窗关闭,回到备战画面      ← 过渡帧②:短暂、不可操作
  → 自动弹出商店                ← 商店可操作
  → 商店收起,回到备战画面      ← 可操作(部署/晶矿/消费/出战——策略器主窗口)
```

要点:
- 两个中途备战帧是动画过渡,bot 逻辑上**当作没出现**;策略器真正的工作窗口 = 弹店收起后的可操作备战帧。
- **BOSS 简报与普通弹窗同规则**:点空白关闭 → 回备战 + 自动弹商店,由出战动作开打 boss 战。(旧裁定「boss 简报点掉后 boss 战自动开打、商店永不开」已撤销——第七/八局实录的超时实为**接管局恢复态**:战斗中崩溃重进的局商店被游戏侧锁死只能出战,见 economy.md「恢复局商店锁死」条;从备战画面主动暂离后接管的局操作正常,两种形态以崩溃时所在画面区分。)
- 弹商店的触发源(#14):战斗结算后 / 投资策略选完 / 补给选完 / 遭遇选完 / BOSS 简报关闭后;唯 1-1 不弹(开局奖励替代)。

## 2. 差异清单(sim 世界模型 vs 实机流程)

对照面:实机 = screen_flow_timing.md + flow/outer_loop.md §2.2 + screens/ 38 篇终结动作表 + screen_info 58 档 CW 建档 + cw_loop 分发段;sim = cw_sim_backend.py + sim-design.md + cw_sim_obs_gen.py + cw_overlay_register.py。

### 高(策略窗口缺失 / 崩溃 / 机制失真)

| # | 差异 | sim 锚 | 修复方向 |
|---|---|---|---|
| H1 | **遭遇节点「选卡落地即战斗结算」**:kernel 把 pick_encounter 声明为 `battle_resolve`(next_screen=结算屏),sim 直接结算;实机选完回备战+弹店,由出战动作开打遭遇战。pick_encounter.py 注释自称「权威 = screens/encounter.md §5」属循环引用,§5 无此语义 | kernel/cw_action_report/pick_encounter.py:21-24,44;sim/cw_sim_backend.py:1361-1362 | 声明改回备战;遭遇战由 StartBattle 触发 |
| H2 | **boss 节点无备战窗口**:BOSS 简报点空白 → `_resolve_battle` 直接结算;实机点掉回备战+弹店,出战才开打 | cw_sim_backend.py:1104-1106(点击源直连结算) | 点空白改回备战;boss 战由 StartBattle 触发 |
| H3 | **补给节点确认即推节点**:动作 op 确认后直接 `report_node_advance(supply_confirm)`;实机选完回备战+弹店,出战(=完成节点,不打怪)推进 | operations/cw_op/cw_pick_supply_action.py:142-148 | 删确认即推;补给出战完成语义(start_battle 对 supply 节点走「完成节点不战斗」分支) |
| H4 | **银狼升星(planner)sim 空桶崩溃**:呈现模态但候选桶恒空([]),策略选 idx=0 后 `options[pick.idx]` 无守卫 → IndexError → 失败重派死循环;升费滚动投资线在 sim 完全不可演;设计档未申报 | cw_sim_obs_gen.py:301-307;cw_sim_backend.py:1727-1728;崩溃面 = cw_screen_yinlang.py:197-202 | sim 按机制生成两卡候选写入呈现写点;顺修日志行空桶守卫 |
| H5 | **免战牌「跳过战斗」未建模**:实机出战变「跳过(N/N)」不掉血连胜不动;sim 照常掷 50% 胜负照常扣血。免战牌在 sim offer 池可选出,持牌局估值恒错;§8.2 无申报 | sim/ 全目录零处理;_resolve_battle(cw_sim_backend.py:2233-2351)无跳过分支 | _resolve_battle 前查 remaining_uses>0 → 免结算直推进 |

### 中(决策域缺失 / 申报失实)

| # | 差异 | sim 锚 | 修复方向 |
|---|---|---|---|
| M1 | **自动开店机制全族缺失且未申报**:实机五触发源自动弹店并强制转商店访问路径(battle/reward 节点也缺);sim 开店唯一入口 = 策略器 OpenShop 点击源。商店**内容**决策等价(发牌同在节点窗),不等价的是呈现与接管形态——「跳过商店期」类策略形态在 sim 无代价、实机不可行 | cw_sim_backend.py:1114-1115,1178-1202;窗序 :1795-1923 无开店呈现 | 节点窗备战呈现后按触发源模拟自动开店态(复用 SCREEN_SHOP 模态),或最低限度 §8.2 登记偏差 |
| M2 | **星徽秘典(star_tome)四选一无呈现无决策**,且 §4.2 与 §8.2 申报表均漏列(代码 docstring 的无呈现名单含它,设计申报面缺) | cw_sim_backend.py:1709-1722 | 补观察分支后呈现,或先补申报行 |
| M3 | **专家邀请函申报失实**:§8.2 称「不入队」,实际入队+呈现模态,但观察降级恒选「现金为王」;`unlocked_experts` 恒空 → 商店专家入池面发牌分布结构性不同 | cw_sim_backend.py:1730-1735;申报偏差 = §8.2:245 | 补候选观察后真实呈现,或改「登记即消费+披露」并如实改写申报 |
| M4 | **遭遇刷新剩余(优势布局授予)未建模**:refresh_left 恒 None → 刷新建议在 sim 永不可发(每局 1 次,影响面窄) | cw_sim_obs_gen.py:272-281;申报仅 sim-wiring.md §五,§8.2 无 | 呈现时按优势布局给初值 + 刷新世界分支(投资两屏 2026-10-19 批同款) |

### 低

| # | 差异 | 说明 |
|---|---|---|
| L1 | 开局位面过渡屏缺失(简报下一步直弹投资环境;实机经位面过渡) | 零决策面,纯流程形态;修:_advance_briefing 先呈现过渡档 |
| L2 | 信息面画面族 sim 无对应物(敌人信息浮层/暗色锁定子态/各类详情弹窗等) | **无策略影响**(sim 不呈现则流程永不派发);登记「适用范围外」即可 |
| L3 | 申报账目措辞失实:§8.2「评估器缺位不入队」≠实际「入队后消费+披露」;kind 旧名 fate/expert/hack 未随九类正名;§4.2 命运卜者「呈现门」描述误导 | 纯文档,随批 C 更正 |

### 申报账目核对结论(§8 逐行)

如实:战斗随机输出面(奖励关恒胜/扑满豁免)、扣血分量、位面 3、offer 离群、词缀采样、环境经济通道、装备/工具发放空表、简化档各键、战斗等待窗与局终链塌缩(§8.3)。
不符/缺登记:H1-H5 五处高严重面**完全无申报**;M1-M4 缺登记或失实;L3 措辞失实;§3.3 窗口序列仍按「按节点类型直接呈现节点屏」的旧语义书写(sim-design.md:106-107),该语义即本迭代要修的本体。

## 3. 修复方案(三批)

### 批 A · 节点备战窗口 + 自动开店(核心重构)

sim 世界模型(cw_sim_backend.py):
1. 节点窗呈现语义改造:`_present_node_screen` 全部节点类型呈现「备战档(底层)+ 节点弹窗模态压上」——复用现成 `_present_modal`/`_return_screen` 机制(投资环境屏已是此形态);supply→补给屏、encounter→遭遇屏、boss→BOSS 简报、投资策略 offer 与位面过渡照旧。
2. 弹窗处理完(pick_supply / pick_encounter / BOSS 简报点空白 / 选卡族)→ `_dismiss_modal` 回备战档——不推进节点。
3. 回备战后按触发源模拟自动开店态(#14 五源;1-1 例外)。
4. 战斗触发统一:encounter/boss 战由策略器 StartBattle 声明(`battle_resolve`)触发;supply 节点 StartBattle = 完成节点(不战斗不结算,直接推下一节点)。

kernel 声明(实机/sim 共用权威):
5. `cw_action_report/pick_encounter.py`:trigger 从 `battle_resolve` 改为回备战(`chosen_encounter` 容器消费链不破坏——确认时已写,结算时机后移)。
6. `operations/cw_op/cw_pick_supply_action.py`:删确认即推节点(支 2)。
7. `cw_action_report/start_battle.py`:按 `gs.node.kind` 分叉——supply 节点 next_screen = 备战档(完成语义),其余 = 结算屏。

实机 flow 层:
8. cw_loop.py:1690「补给节点备战画面 → 点返回补给阶段」分支加「补给未确认」守卫(chosen_supply 为空才进该分支)——否则修后补给确认回备战会被再次送回补给屏,**死循环**。此为实机 60+ 局稳定路径的改动,风险面最大,需配套实机验证。
9. boss 简报点掉 → 主循环 → 备战分支接住:现有链已通(cw_screen_boss_briefing 点掉即返回主循环),无需改。

策略器:无需改(entry.py 十段通用;补给节点的完成语义由世界侧消化)。

### 批 B · 决策域补全

H4(planner 候选生成 + 空桶守卫)、H5(免战牌)、M2(star_tome)、M3(expert)、M4(遭遇刷新)——逐项独立,可穿插。

### 批 C · 文档与申报

sim-design.md §3.3(窗口序列改「备战先出+弹窗模态+回备战+弹店」)、§4.2、§8.2(补 H1-H5/M1-M4 申报、L3 措辞、kind 正名)、§3.2(点击源表);flow/outer_loop.md §2.2 如有出入同步;L1 位面过渡、L2 登记范围外。

### 验证

- 同 seed 重跑对照:行为变化预期内逐项清单(多出 6+ 个备战窗口的消费/刷新/部署机会;经济轨迹分布变)。
- sim 测试回归(sr-od-test currency_war)+ 受影响域单帧测试。
- sim 批统计与历史批可比性断裂:批 manifest 声明 sim 版本号。
- 实机:补给/遭遇/boss 节点的备战窗口被策略器消费的实走验证(批 A 落地后)。

## 4. 本轮已完成的文档修正(错误裁定撤销,2026-10-29)

「boss 简报点掉后自动开打、商店永不开」的旧裁定系接管局形态误归因,以下 5 处已修正:
1. `src/sr_od/application/currency_war/operations/cw_screen/cw_screen_boss_briefing.py` 模块头(错误归因删,换正确流程 + 接管局例外)。
2. `docs/develop/sr_od/application/currency_war/screens/boss_briefing.md` 开放设计注①(撤销「已裁」,恢复 #14/#27 口径)。
3. `docs/develop/sr_od/application/currency_war/screens/README.md` §5.1 表行。
4. `docs/game/screens/currency_war_boss_briefing.md` 出口与可交互元素两行(错误「勘误」翻正)。
5. `docs/game/currency_war/research/economy.md`「恢复局商店锁死」条补接管形态二分(战斗中崩溃 = 锁死;备战暂离接管 = 正常)。

历史迭代工件(changes/2026-09-22-screen-review/boss_briefing.md:114、changes/2026-10-12-prep-shop-workflow-redesign/ 两处「boss 不开店」表述)不回改——changes/ 为过程区,寿命 = 迭代;本 README 为勘误后的权威记录。
