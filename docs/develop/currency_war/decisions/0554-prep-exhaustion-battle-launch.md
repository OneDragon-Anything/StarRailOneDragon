# ADR-0554: 备战收益耗尽 → 出战臂(环级无进展守卫 RunDeploy 稳态形态改判出战)

## 状态
已实施(待落地审)

## 背景(实机卡点,2026-09-06 08:10:59 守卫停机留证)
位面 2 r1,hp36,金 29,板 7/7 满且 bench 持目标件,备战双锚在场、
『出战 F』可用。日志:连续 3 备战环同签名动作批 `['RunDeploy']` ∧ 状态
零推进 → 环级无进展守卫停机(`prep_no_progress.flag`)。每环 CwOpDeploy
报「无部署可做(计划空,候选全被规则留 bench;dd-037 no-op)」→ 备战环
success 返回 → 顶层分发重判 → 同态循环。

## 根因
顶层分发缺「备战收益耗尽 → 出战」分支。既有出战出口仅两条:达标臂
(fp≥1.00 线成型)与恢复局锁定直出战;线未成型帧备战环无事可做时,
外环只能「等+no-op」——但 CW 备战阶段无自然结束(出战由玩家主动发起),
「等」永不推进,守卫按执行面卡死停机。

## 机制依据(判据的支配性论证,零拍定值)
`docs/game/currency_war/data/gameplay.md` 权威机制:
- 商店「每个节点自动刷新 1 次」,节点推进以战斗完成为前提;
- 基础金币/利息/连胜奖励均在「每场战斗结束时」结算。

⇒ 备战环等待的边际收益恒等于 0(金不变、店不刷、经验不涨);出战边际
收益 ≥ 0(战斗必有结算收入),且战力由当前板面决定、与等待时长无关
(等待不改变任何战力输入)→ **出战严格支配等待**,无参数权衡。

## 判据公式
```
eligible(action_sig, last_prep_success) =
    last_prep_success == True
    ∧ action_sig ≠ None
    ∧ set(action_sig) == {'RunDeploy'}
```
- 触发位 = 环级无进展守卫既有触发位(连续 PREP_NO_PROGRESS_ROUNDS=3 环
  「同签名动作批 ∧ 状态零推进」),复用守卫计数,不立第二计数器;
- dd-037 契约保证:计划空+0 落地 = STATUS_NOOP 走 success;计划非空+
  0 落地(拖拽落空/遮罩挡拖)= round_fail。故「RunDeploy-only ∧ 上环
  success」唯一对应策略层自愿 no-op(候选被规则留 bench ∧ 买/升/刷
  全被策略拒绝 ∧ 零状态变换)= 收益耗尽;其他形态(OpenShop 重燃、
  RunEquip 装备环、混合批、失败环)维持守卫停机语义;
- 补给节点排除:补给节点出战不推进(既有 divert 分支语义),该形态
  跳过本臂维持停机;
- 失败防线:发射经 C1 单一发射核 `readiness_battle_launch`(与达标臂
  共用,零第二 StartBattle 发射位);连续 3 次失败放弃短路回落守卫停机
  (与达标臂防线 C1 同构);屏态过期(readiness_stale_screen)不计数
  交回下轮重判。

## Considered Options
1. **本方案:守卫触发位收窄改判出战**(采纳)——判据挂在守卫既有信号上,
   零新计数、零新参数,支配性论证免调参;失败形态仍停机留证。
2. 策略层在 decide 输出 StartBattle——被否:出战是流程层出口非经济决策,
   策略词表加控制流动作违反「策略器禁用空批表达控制流」同型边界;且
   无法区分「合法等待成型」与「收益耗尽」,会造成未成型乱开战。
3. 提高守卫阈值 / 只留证不停机——被否:执行面卡死形态(遮罩/拖拽落空)
   仍需 3 环停机留证,放宽阈值烧不可复现对局。

## 影响
- 新分支:`cw_loop.prep_exhaustion_launch_eligible`(纯函数)+ 守卫触发位
  出战臂 + `cw4_counters` 分键 `exhaustion_battle_launch` /
  `exhaustion_launch_fail` / `exhaustion_launch_giveup`;
- 锁:`test_cw_no_progress_guard.py` 判据真值表 + loop 级出战/放弃/失败
  形态三锁(既有 14 锁零改动零漂移);
- 缺省零漂移:非「RunDeploy 稳态 + success」形态行为逐字节不变。
