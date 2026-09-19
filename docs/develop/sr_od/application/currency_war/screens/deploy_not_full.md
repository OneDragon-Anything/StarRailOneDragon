# 未达上限确认弹窗(deploy_not_full · 货币战争-未达上限警告)

> 代码 = `operations/cw_screen/cw_screen_deploy_not_full.py::CwScreenDeployNotFull`(两 node 直继承 `SrOperation`)。职责:「可出战角色人数未达上限」确认弹窗(0d)的一次访问——勾「本局不再提示」+ 确认,解除 bench-full 警告对出战的阻塞。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0d:锚 = `货币战争-未达上限警告.标识-未达上限警告`(id_mark,**位置区分**判据:投资策略屏描述「能量上限」与「未达上限」共享子序列「上限」,全屏 LCS 会误匹配吞投资策略分支——area 位置不同即不命中)。分发 = 阶段一身份行([../flow/outer_loop.md](../flow/outer_loop.md) §2.2);建档 = `currency_war_deploy_not_full.yml`。

## 2. 画面形态声明

**空决策形态**(确认即推进,零策略问询)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 标识门(「标识-未达上限警告」,miss = round_fail 交回外循环)+ obs{on_screen} + 占位 report 调用 → obs 挂实例属性;决策动作 node = 顶部重入裁决(确认已发 → 锚不在 = 弹窗已关 → success 交回;锚在 = 未落地重做)→ `_confirm_and_dismiss` 确认体 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=10` 现役值仅框架异常路径消费)。

## 3. 观察面

轻观察:payload = `CwScreenDeployNotFullObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/deploy_not_full.py`);标识门在观察 node(miss → `round_fail` 交回外循环)。report = `report_screen_deploy_not_full_obs` 占位调用(本屏现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState 写端。

## 4. 动作面

`_confirm_and_dismiss`:勾 `货币战争-未达上限警告.勾选-本局不再提示`(`_overlay_confirm.py::safe_click` 带 bug#1 缓解 + 0.3s)→ 确认(`_overlay_confirm.py::emit_overlay_confirm`,mouse_move 缓解 + success_wait=3.0)→ 置位 `_confirm_pending`(落地判定归下一轮重入裁决)。坐标 = screen_info 现取优先,**缺失才用兜底常量**(`CHECKBOX_NO_PROMPT(912,589)` / `BTN_CONFIRM(1159,653)`)——与「禁兜底坐标」一般红线不同的 as-built 例外,在此申报。

## 5. 终结与交回

重入裁决:确认已发 ∧ 锚 miss = 已关 → `round_success(wait=3.0)` 交回;锚仍在 = 确认未落地 → 重做(`round_wait` 循环推进,无防御上限)。落点 = 底层屏(备战 / 出战链语境)重判。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;「本局不再提示」为游戏局级抑制位,不入任何账。

## 7. 子态与 overlay

- 本 op 自身即 overlay 处理件;命中即自处理,底层屏交回重判。
- **同弹窗第二消费者**:出战链 `cw_op/cw_start_battle_action.py::CwActionStartBattleOp` 出战点击轮询段内嵌同款行为(勾选幂等 + 确认 + 轮询)——出战语境由出战链就地消化,不经 0d 分发;两处行为对齐为申报面,无单一源锁。

## 8. 守卫与防线

`node_max_retry_times=10` 现役值仅框架异常路径消费;「点了≠成了」防线 = 重入裁决;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「未达上限确认」;frame_tag = `overlay_deploy_not_full`;dispatch wait=3(与确认收尾 success_wait 同口径);日志 tag `[cw-deploywarn]`。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(未达上限弹窗两 node 形态锁:观察门/重入裁决组合);建档 = `currency_war_deploy_not_full.yml`。
