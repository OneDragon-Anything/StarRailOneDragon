---
doc_name: 逐光捡金操作路由
app_id: treasures_lightward
source: 实机实测(2026-11,4.6 版本期) + screen_info 逐光捡金屏族建档 + 挑战 ops 源码契约
involves_screens: [逐光捡金, 指南-逐光捡金, 忘却之庭-编队, 忘却之庭-节点画面, 虚构叙事-编队, 末日幻影-选关, 末日幻影-编队, 末日幻影-节点结算]
---

# 逐光捡金操作路由

本文是 SKILL.md 各类型块「操作路径」的展开:按**操作意图**给路由表——每步用什么
op/工具、参数、成功状态、失败解读与去向。分工:玩法机制与术语见
[gameplay.md](gameplay.md);配队决策见 SKILL.md「配队决策工作流」;画面坐标单一
真相源在 screen_info,本文括号内坐标为当前建档中心值仅供 MCP 手动点击参考。

调用约定:

- op 一律经 MCP `run_operation(op_id='<模块路径>.<类名>', args={...})` 调用;本文
  op_id 前缀统一为 `sr_od.application.treasures_lightward.operations.<子包>.<模块>.<类名>`,
  子包按玩法分:`forgotten_hall`(FH) / `pure_fiction`(PF) / `apocalyptic_shadow`(AS);
  公共导航(`goto_treasures_lightward`)直接在 `operations` 根下。
- 选关与编队屏 `pc_alt=true`(锁光标):MCP 手动点击传 `click_game(x, y, pc_alt=True)`;
  op 内框架点击自带处理,无需关心。
- 「增益读取」「首领原型库」「攻略搜索」等挑战前情报工作走 SKILL.md 公共路由,
  本文不重复。

## 1. 公共链路

### 1.1 导航到目标玩法选关

op `goto_treasures_lightward.GotoTreasuresLightward(mode='<枚举值>')`——任意画面
出发。枚举值:`forgotten_hall` / `pure_fiction` / `apocalyptic_shadow` /
`anomaly_arbitration`(异相仲裁未探明,入口点击后显式失败,不能自动打)。

- 终点:忘却之庭 = 选关(混沌回忆视图,紊流更新弹窗已关);虚构叙事 = 选关
  (新期开场页已点「开启故事」);末日幻影 = 选关(新期开场页已点「前往挑战」)。
- 已在入口链画面(选关/编队屏等)自动从所在位置接续,不绕路重走。
- 失败 = 消息带现场画面;陌生/未建档画面先按 `od-dev-screen-onboarding` 建档再续。

### 1.2 选关 → 编队屏(跳转责任划分)

| 玩法 | 谁做跳转 | 路由 |
|---|---|---|
| 忘却之庭 | 调用方 | 点目标关卡水晶(area「水晶-<关卡名>」,「逐光捡金」屏;**仅个别关卡建档**,目标关卡未建档先按 `od-dev-screen-onboarding` 补档)→ `goto_screen(target_screen_name='忘却之庭-编队')`(选关屏已建 goto 边) |
| 虚构叙事 | 调用方 | 点目标关卡纸鹤 → `goto_screen(target_screen_name='虚构叙事-编队')` |
| 末日幻影 | 组合 op 入口节点 | 无需先跳;op 从选关屏/编队屏/挑战进行中均可发起。读公理 buff 需在编队屏:临时跳转用 `goto_screen('末日幻影-编队')`(选关屏已建 goto 边),读完直接发起组合 op 即可接续 |

⚠️ 末日幻影选关**默认选中最高可玩难度**;打非默认难度时在进编队屏前
重新点目标难度标签(area「难度-01」等,「末日幻影-选关」屏)。

## 2. 忘却之庭 · 混沌回忆(FH)

### 2.1 完整挑战一轮

| 步骤 | 用什么 |
|---|---|
| 导航选关 | `GotoTreasuresLightward(mode='forgotten_hall')` |
| 进编队屏 | 点目标关卡水晶 → `goto_screen('忘却之庭-编队')`(画面 doc:忘却之庭-编队) |
| 读输入 | MCP `analyze_screen` 识别「忘却之庭-编队」——extras 给 关卡名/记忆紊流文本/各节点弱点/当前编队;编队屏「建议属性」= 敌人弱点表 |
| 填人 | op `forgotten_hall.team_fill.TlFhTeamFillOp(team_names=[8 个角色中文名按波序])`,每 4 人切一波 |
| 发起挑战 | **无 op 封装,调用方做**:MCP `analyze_screen` 命中「忘却之庭-编队」后 `click_game(x=1672, y=985, pc_alt=True)`(area「按钮-最终开始」中心) |
| 战斗 | op `forgotten_hall.battle.TlFhBattleOp(node_teams=[[节点一 4 人],[节点二 4 人]])` |

结果解读:

- `TlFhTeamFillOp` → `编队填充完成`;失败「列表到底未找到 <角色名>」= 账号无此人
  或识别名不一致(对照脸库识别名),修正名单重跑(op 幂等,已落位成员跳过)。
- `TlFhBattleOp` → `挑战成功`(结算浮层已见,返回忘却之庭已点)/ `战斗失败`。
  首次 3 星通关最高解锁关的「快速通关」补发列表与「获得物品」页由 op 自动处理。
- 战斗失败去向:回到选关屏,换队或提练度后重跑 2.1(星数按剩余行动轮计,
  轮数池跨节点共享,详见 gameplay.md)。

### 2.2 期次累计奖励(星芒礼包)——手动领取

自动领取 op 未建模,MCP 手动点击(均在「逐光捡金」屏建档):

| 步骤 | 用什么 |
|---|---|
| 打开馈赠弹窗 | `click_game(x=1840, y=975, pc_alt=True)`(area「按钮-星芒礼包」) |
| 切 tab | 印记馈赠 `click_game(x=515, y=270)` / 回忆馈赠 `click_game(x=715, y=270)` |
| 逐项领取 | **领取按钮未建档**:`analyze_screen` 读弹窗内「领取」文本,`click_game` 点其中心;领过的项文本变化,以实读为准 |
| 关闭 | `click_game(x=1498, y=270)`(area「弹窗-馈赠-关闭X」) |

## 3. 虚构叙事(PF)

### 3.1 完整挑战一轮

| 步骤 | 用什么 |
|---|---|
| 导航选关 | `GotoTreasuresLightward(mode='pure_fiction')` |
| 进编队屏 | 点目标关卡纸鹤 → `goto_screen('虚构叙事-编队')` |
| 读输入 | 编队屏左栏「战意效果」列表 + 每行行首加号开「荒腔走板」弹窗后 `analyze_screen` 识别「虚构叙事-荒腔走板」,extras 给 node_no/boss_name/buffs(含 slot/name/equipped/desc) |
| 组合挑战 | op `pure_fiction.challenge.TlPureFictionChallengeOp(team_names=[8 人按行序], buff_slot=<战意效果序号>, buff_slots=[行1 序号, 行2 序号])` |

结果解读:

- 组合 op → `挑战成功`(终点 = 虚构叙事选关)。入口节点**只判定**是否已在编队屏,
  不做跳转——不在则显式失败「不在虚构叙事编队屏(前置:选关点关卡纸鹤)」。
- `buff_slot` 按编队屏左栏可见列表上下序(1-2;效果多于 2 个需先滚动,当前仅支持
  可见两槽);`buff_slots` 每行三选一(1-3)。**一律按位置不按名称**(名称随期轮换)。
- 内部子 op 可单独跑(前置同为编队屏):`pure_fiction.team_fill.TlPfTeamFillOp(team_names)` /
  `pure_fiction.buff_equip.TlPfBuffEquipOp(buff_slot, buff_slots)` / `pure_fiction.battle.TlPfBattleOp()`。
- 战斗失败去向:PF 按击杀数计分,失败即结算浮层,回编队屏换队重跑(细节见 gameplay.md)。

### 3.2 期次累计奖励

领取 op 未建模(登记为待办;建模可参照 AS `TlRewardClaimOp` 的「覆盖页/领取/无可领」
三分支状态机)。当前手动处理,入口与画面以当期实读为准。

## 4. 末日幻影(AS)

### 4.1 完整挑战一轮(双节点,难度 01-03)

| 步骤 | 用什么 |
|---|---|
| 导航选关 | `GotoTreasuresLightward(mode='apocalyptic_shadow')` |
| 读输入 | 「末日幻影-首领信息」画面看 boss 弱点与机制;行尾圆圈开「终焉公理」弹窗后 `analyze_screen` 识别「末日幻影-终焉公理」,extras 给 node_no/boss_name/buffs |
| 组合挑战 | op `apocalyptic_shadow.challenge.TlApocalypticShadowChallengeOp(team_names=[8 人按行序], buff_slots=[行1, 行2])` |

结果解读:

- 组合 op → `挑战成功`(终点 = 选关屏)。入口节点**自行处理**选关屏→编队屏跳转
  (含「前往挑战/重新挑战/更换编队确认」各态);已在编队屏或挑战进行中也直接接续。
- `buff_slots` 每行三选一(1-3),按卡片位置;行内「坚防守备」类按钮是敌方特性
  查看器,不是 buff 选项。
- **队伍须避开带警告标记的角色**(命途/养成警告,如当期试用)——可落位但
  「前往挑战」校验不过,点击无反应。
- 快速通关补发由战斗推进自动处理。
- 战斗失败去向:「前往节点二」仍可推进(AS 按积分计分,行动值耗尽 = 低分结算
  不算失败);要放弃走 4.4 弃赛退出。

### 4.2 星启模式(难度 04,三节点)

同 4.1 的组合 op,参数换 12 人 + 三项增益:
`TlApocalypticShadowChallengeOp(team_names=[12 人按行序], buff_slots=[行1, 行2, 行3])`。- 编队屏三行节点,击败 3 个首领;各节点支持单独重新挑战(改队后再挑战会弹
  「战绩重置」确认,组合 op 内自动处理「按钮-覆盖编队确认」同构弹窗)。
- 星启编队屏交互模型与双节点不同(行槽位剪影/行尾「+」/顶部垃圾桶一键清),
  组合 op 内按布局模式自动分派,调用方无需区分。
- 满员验证:星启布局槽位像素判空不可用,可靠信号 = 角色列表卡「队伍N」标记
  OCR 计数(12 标记 = 满员);填充 op 内置处理。

### 4.3 单独重打 / 中断接续

- op `apocalyptic_shadow.battle.TlAsBattleOp()`(无参):按画面特征每轮分流,起点可为 首领简报
  横幅 / 节点画面 / 节点结算页(循环首分支即处理「前往节点二/返回末日幻影」)——
  用于**单独重打当前节点**或**从中断处接续**。
  终点 = 最终结算页点「返回末日幻影」(`最终结算完成`)。
- op `apocalyptic_shadow.battle_exit.TlAsBattleExitOp()`:**弃赛退出**——节点结算页点「退出」
  回选关(最终结算页同位按钮「返回末日幻影」同键处理)。战斗进行中的暂停退出
  未覆盖(待战斗帧建档),战斗内只能等行动值耗尽低分结算。

### 4.4 期次累计奖励(祭礼奖励)

op `apocalyptic_shadow.reward_claim.TlRewardClaimOp()`(无参)。前置 = 末日幻影选关屏,不在则
显式失败。流程:选关屏左下礼物盒入口 → 永劫祭礼(期次星数累计)点「领取」→
获得物品覆盖页点空白关闭 → 终局祭礼(各难度首通)点「领取」→ 关闭回选关。
一键语义:每个 tab 全程只点一次「领取」即全 tab 发放;已领完态直接推进不误点。
⚠️ 选关屏「奇珍琳琅」袋子是兑换商店,不是领奖入口。

## 5. 边界(当前不能做的)

- **异相仲裁**:未探明(无建档/无 op)——如实告知不能自动打;要支持先按
  `od-dev-screen-onboarding` 建档再按 `od-dev-gameplay-automation` 从零做。
- **FH 星启(难度 12,三节点)**:挑战 ops 未适配(显式防御),不能自动打。
- **PF 星启**:结构未实跑,未验证。
- **多关循环编排**(连打多个难度/关卡):无 app 级编排,由调用方按 2.1/3.1/4.1
  逐关发起,关与关之间在选关屏交接。
- FH 期次奖励领取、PF 期次奖励领取:未建模 op(见 2.2/3.2)。
