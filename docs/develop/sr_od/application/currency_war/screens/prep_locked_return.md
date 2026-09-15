# 备战暗色锁定返回(prep_locked_return · 策略锁定/遭遇锁定双画面档)

> 代码 = `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn`。职责:备战「锁定」暗色子态族(0m)的一次访问——点右上「返回XX选择」按钮回对应 overlay 交回。一份 op 类服务两个画面档,分发处传命中的那对(带参构造,先例 = `cw_screen_battle_wait.py::CwScreenBattleWait`)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0m:两画面档参数化,锚对 = (`货币战争-备战-策略锁定`.按钮-返回投资策略选择)/(`货币战争-备战-遭遇锁定`.按钮-返回遭遇选择);命中哪对传哪对(`cw_loop.py` 0m 分支循环)。判据单一源 = `docs/game/currency_war/research/screen_flow_timing.md` #18(暗色态判别锚 = 右上操作按钮)。建档 = `currency_war_prep_strategy_lock.yml` / `currency_war_prep_encounter_lock.yml`。
- **排他形态(本屏特有)**:此态下备战双锚(`货币战争-备战.备战标识-购买经验` ∧ `按钮-出战`)仍精准命中——不先分流会被当正常备战操作(读暗牌/暗 gold),0m 必须先于备战分支。

## 2. 画面形态声明

**空决策形态**(纯推进)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类,画面档/入口锚经构造参数覆写):入口观察 → 单次推进 → 重入观察裁决交回;节点预算 = 2(合同 = [../flow/screen_op.md](../flow/screen_op.md))。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` 基类 area 锚原语(构造传入的返回按钮,入口与点击同锚)。零 GameState 写端——暗色态下 gold/牌面不可信,不读不写。

## 4. 动作面

`progress_once` = `round_by_find_and_click_area(self._screen_name, self._entry_area, success_wait=1.5)`(点返回按钮后等转场动画再交回裁决)。目标 = 回对应 overlay,后续由 0e 系/0c 分支接管。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = 锚 miss = 已离开 → `success` 交回;预算耗尽 FAIL 交回。落点 = 对应 overlay(策略选择/遭遇节点分支接管)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

本 op 自身即子态处理件(暗色蒙层是备战画面的覆盖态,无独立底层屏);返回后 overlay 分支接管。

## 8. 守卫与防线

节点预算 = 2(基类合同);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「备战暗色锁定」;frame_tag = `overlay_lock`(dispatch 包装,on_result 闭包记录命中画面档)。测试锁:无点名行为锁(骨架锁随基类,锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);暗色态时序 = `docs/game/currency_war/research/screen_flow_timing.md` #18/#12/#20。

## 开放设计注

- 建档在册第三档「货币战争-备战-补给锁定」(锚 = 按钮-返回补给阶段)不在 0m 分发对集:补给回流现由备战分支节点类型分流步承担,该按钮在干净备战帧同样存在、无法单锚区分;扩第三对参数(配独立判据)候裁。
