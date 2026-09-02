# 06 · 补给 / 遭遇 / BOSS 简报 / 剩余 overlay 族

> W971 分篇。总纲见 [../DESIGN.md](../DESIGN.md)。数据源统一:结算屏读数(§04-shop 裁决),overlay 内不返回暗态观察。

## 1. 补给 overlay(与投资策略同构)

```
前置 = 循环识别「选择补给」(「标识-补给阶段」)
① 读装备卡(卡面:装备图/名/宝钻品质,SIFT 模板主/OCR 名兜底)
② 决策 decide_supply(策略接口,读 session 新值)——决策链:
   a. 装备卡带钻(红/蓝/财富宝钻)→ 直选(品质即价值)
   b. 无钻且刷新未用 → 点刷新重掷(P8)
   c. 刷过 → target_comp.key_equips 契合 + 通用装备价值选
③ 原子 op 执行 → 完成承诺 = **等备战商店开画面出现**(场景①判稳锚 = 「按钮-收起」独有锚,DD-011 amended 纪律;**等待上界兜底**:超上界未现 = 异常,bail 交循环留证——与 05-battle 超时兜底同款),交回循环
```

- 原子 op:RefreshSupplyCard(次数约束 P8;**结束等待 = 刷新动画口径**——现役 handle_invest_env 已修的 1s/2s/2.2s 刷新等待值随 op 迁移,防口径丢失)/ SelectSupplyCard / ConfirmSupply(末位契约)。
- **决策归策略接口原则**(用户确认):所有 overlay 决策一律在策略层函数(现役 cw_events 族),执行器/编排层零内嵌决策。

## 2. 遭遇 overlay

```
前置 = 循环识别遭遇 overlay(「标识-遭遇节点」)
① 读遭遇卡(两卡:难度档位/奖励文本,overlay 上识别)
   (遭遇入口/交互时序 #23:节点屏等待 2s、选项刷新 2.0s——随 op 迁移,与补给侧同款明示)
② 信息收集:选中卡 → 点「查看详情」→ 读敌人难度分预览(页签切两卡各一次)
   (用户裁决:浮层只有难度分对选卡有用;词缀是全局的(session.enemy_affixes,
    简报/位面详情已读),浮层 chips 只是展示——dd-004 chips OCR 通道降级为校验)
③ 决策 decide_encounter(难度三选,评分制,策略接口):
   词缀契合(session 全局词缀)+ 难度档定价(难度账本 marginal_value,难度预览
   为实测锚)+ 奖励价值(文本启发分档)
   → 刷新判据:剩余次数 > 0 且本局未用且契合差 → 刷新换批重决策
   (刷新能力由优势布局「分支刷新」授予,每局 1 次)
④ 原子 op 执行 → 完成承诺 = **等备战商店开画面出现**(场景①判稳锚 = 「按钮-收起」独有锚;**等待上界兜底**:超上界未现 = 异常,bail 交循环留证;遭遇选择 =
   节点难度设定,选完回备战商店自动开;遭遇战斗在出战后才发生,由战斗等待 op 接管)
```

- 原子 op:RefreshEncounter(每局 1 次,分支刷新授予)/ SelectEncounterOption / ReadEncounterDifficulty(选中卡 → 查看详情 → 读难度分,页签切两卡各一次)/ ConfirmEncounter(末位;产出 = 备战商店开)。
- **决策强依赖 session 跨轮状态**:难度账本(marginal_value)是积累值——黑板模式直接受益者;hp 新值(敢难判定)来自结算屏读数。

## 3. BOSS 简报 op

最简画面 op:前置 = 循环识别 BOSS 简报(「标识-强敌来袭」,#26 建档);动作 = **点击空白**(推进);完成承诺 = **等备战商店开画面出现**(场景①判稳锚 = 「按钮-收起」独有锚;**等待上界兜底**:超上界未现 = 异常,bail 交循环留证)。

## 4. 剩余 overlay 族:一 overlay 一 op

统一模式:**识别待选项 → 决策 → 原子 op 操作 overlay 内容(点选/确认)→ 完成承诺 = 固定等待 1.0s(DD-011 形态①,关闭速度都快)→ 交回循环,回到干净备战画面**。

| overlay op(画面) | 待选项识别 | 决策 | 原子 op |
|---|---|---|---|
| **MegastarOp**(货币战争-盛会之星) | 候选立绘(SIFT) | decide_megastar(comp 引擎 × 乘区绑定,选择序 02 §7) | SelectMegastar → ConfirmMegastar |
| **PartnerOp**(货币战争-列车同行) | 候选立绘(SIFT 立绘库,无角色名——决策输入受限) | core/build_around 命中兜底 | SelectPartner → ConfirmPartner |
| **ArmoryBoxOp**(武装箱选卡 overlay) | 装备卡卡面 | 执行器默认(key_equips→材料通用性) | SelectBoxCard → ConfirmBox |
| **WishTrialOp**(祈愿试炼) | 候选卡 | naive 首张 | SelectWishCard → ConfirmWish |
| **PlannerEventOp**(银狼「我来当策划」) | 选项(PlannerOption) | decide_planner(策略模块,r104) | SelectPlannerOption → ConfirmPlanner |
| **FortunePickerOp**(命运卜者强化) | 强化卡候选 | 执行器(强化卡选择) | SelectFortune → ConfirmFortune |
| **BookcardOp**(星徽秘典四选一) | 四张卡 | 待定(现役 loop 0i 接管选卡;策略归口批 B 定) | SelectBookCard → ConfirmBook |

- 全族共性:overlay 内原子 op 只有「点选 + 确认」两型;待选项识别写 session 喂决策;决策一律在策略接口(执行器默认类除外——固定规则非策略判断)。
- **handler 差异点显式化**(对抗轮 1 代码现实 P1):现役 handler 中超出「点选+确认」的逻辑随 op 化显式迁移——handle_invest_env 的节点台账重读+变异窗+采集、handle_encounter 的验证消失+bail 语义、各 handler 的 bail 计数族(defer/bail 计数器)列入退役/迁移清单(批 B 实施时逐个落)。
- **干扰弹窗族**(对抗轮 1 P1 补,均有死循环实锤修复史):商店概率表(0e2)/道具详情(0e3)/消耗品弹层(0f)/阿哈装备选择/专家邀请函/试用揭示卡——**不入 §2.16 选择 op 枚举**(非决策选择),由循环判定序识别后按既有处理分支关闭/跳过;分支清单随主循环瘦身**保留**(不退役),防静默丢弃退避停机。
- 装备拾取(handle_equip_pick)不属选择 overlay(战斗掉落拾取动作),归类待定(实现批定)。
- **暗色锁定态族归属**(对抗轮 1 终检 P2 补):策略锁定/遭遇锁定档(顶部「返回XX选择」按钮态)由**主循环判定序的暗色锁定态前置分支**承载(现役语义保留),不属选择 op——非选择流程处理类,与中断挑战弹窗/位面详情同列兜底分支。
- 中断挑战弹窗/位面详情 overlay:非选择类(流程处理),留主循环兜底分支(位面详情的情报采集职责归 CollectPlaneIntel,不变)。

## 5. 完成承诺两口径总表(用户强调)

| overlay 族 | 确认后 | 完成承诺 |
|---|---|---|
| **节点后四类**(投资策略/补给/遭遇/BOSS 简报) | 回备战 → 商店自动开 | **等备战商店开画面出现**(场景①判稳锚 = 「按钮-收起」独有锚) |
| **备战触发型七 op**(盛会之星/列车同行/武装箱/祈愿/策划/命运/秘典) | 回干净备战 | 固定 1.0s |

场景①判稳锚纪律(DD-011 amended):**「按钮-收起」独有锚**(「备战阶段」文本两档同址无判别力,W970 轮 2 P0 勘误)。