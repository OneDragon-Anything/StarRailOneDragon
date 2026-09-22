# 备战暗色锁定返回(prep_locked_return · 策略锁定/遭遇锁定双画面档)

> 代码 = `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn`。职责:备战「锁定」暗色子态族的一次访问——点右上「返回XX选择」按钮回对应 overlay 交回。一份 op 类服务两个画面档,分发处传命中的那对(带参构造,先例 = `cw_screen_battle_wait.py::CwScreenBattleWait`)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):两画面档参数化,锚对 = (`货币战争-备战-策略锁定`.按钮-返回投资策略选择)/(`货币战争-备战-遭遇锁定`.按钮-返回遭遇选择);命中哪对传哪对(`cw_loop.py` 策略锁定/遭遇锁定身份分支)。判据单一源 = `docs/game/currency_war/research/screen_flow_timing.md` #18(暗色态判别锚 = 右上操作按钮)。建档 = `currency_war_prep_strategy_lock.yml` / `currency_war_prep_encounter_lock.yml`。
- **排他形态(本屏特有)**:此态下备战双锚(`货币战争-备战.备战标识-购买经验` ∧ `按钮-出战`)仍精准命中——不先分流会被当正常备战操作(读暗牌/暗 gold),本臂必须先于备战默认分支。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1;画面档/入口锚经构造参数覆写):观察 node = 入口锚门(构造传入的返回按钮,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 锚不在 = 已离开本画面 → success 交回)→ 点返回按钮单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` area 锚原语(构造传入的返回按钮,入口与点击同锚)→ obs = `CwScreenPrepLockedReturnObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/prep_locked_return.py`;无 report 接口)。零 GameState 写端——暗色态下 gold/牌面不可信,不读不写。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内(`progress_once`:点「返回XX选择」按钮) | 画面 op 留守臂(`progress_once`,`round_by_find_and_click_area` 点返回按钮 + success_wait=1.5) | 无 report 接口(推进型规范形态,[op-layer.md](op-layer.md) §3) | 是(重入裁决交回):点返回 → `round_wait` 重入,构造传入的返回按钮锚不在 = 已离开本画面 → `round_success` 交回外循环(见 §5) |

`progress_once` = `round_by_find_and_click_area(self._screen_name, self._entry_area, success_wait=1.5)`(点返回按钮后等转场动画再交回裁决)。目标 = 回对应 overlay,后续由阶段一身份分发接管(投资策略/遭遇节点各身份行)。

## 5. 终结与交回

推进已发 → `round_wait` 重入;重入 = 锚 miss = 已离开 → `success` 交回(无防御上限)。落点 = 对应 overlay(策略选择/遭遇节点分支接管)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

本 op 自身即子态处理件(暗色蒙层是备战画面的覆盖态,无独立底层屏);返回后 overlay 分支接管。

## 8. 守卫与防线

`node_max_retry_times=2` 现役值仅框架异常路径消费;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「备战暗色锁定」;frame_tag = `overlay_lock`(dispatch 包装,on_result 闭包记录命中画面档)。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,prep_locked_return 在册);暗色态时序 = `docs/game/currency_war/research/screen_flow_timing.md` #18/#12/#20。

## 开放设计注

- 建档在册第三档「货币战争-备战-补给锁定」(锚 = 按钮-返回补给阶段)不在本 op 分发对集:补给回流现由备战分支节点类型分流步承担,该按钮在干净备战帧同样存在、无法单锚区分;扩第三对参数(配独立判据)候裁。
