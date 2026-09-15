# 角色详情浮层(role_detail_overlay · 货币战争-备战-角色详情)

> 代码 = `operations/cw_screen/cw_screen_role_detail_overlay.py::CwScreenRoleDetailOverlay`。职责:点卡/点角色触发的详情弹窗(1b,可合成列表/角色详情两变体)的一次访问——点面板外空白关闭交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1b:双锚其一——`货币战争-备战-角色详情.按钮-装备推荐`(角色详情变体)∨ `货币战争-备战-角色详情.装备详情-合成公式`(可合成列表变体);判据单一源 = `cw_loop.py::_role_detail_anchor_hit`,`entry_ok` 与之同源同参。
- 位置约束锚形态:两锚均在右侧面板锚区,与 0t 商店卡牌详情弹窗天然互斥(该弹窗底部按钮不在右侧锚区内)——全屏文本判据在本族不可用(与 0t 底部按钮文本全等共享)。序位:备战分支(1)之后;序位表 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。建档 = `currency_war_battle_prep_equip_detail.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类):入口观察 → 单次推进 → 重入观察裁决交回;节点预算 = 2(合同 = [../flow/screen_op.md](../flow/screen_op.md))。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` 双锚其一复判。零 GameState 写端。

## 4. 动作面

`progress_once` = `round_by_find_and_click_area(货币战争-备战.区域-空白关闭, success_wait=1.5)`。关闭机制 = 点面板外空白(两 overlay 家族无关闭按钮,共用同一空白点);「区域-空白关闭」为纯定位区(find_and_click 点建档中心,点击语义等价且自带等待)。刻意不用 ESC:空白点在 overlay 未开时是无害空点,ESC 在浮窗已自关时落备战会误弹「中断挑战」。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = 双锚均 miss = 已离开 → `success` 交回;预算耗尽 FAIL 交回(dispatch 挂 `on_fail_retry`,映射 loop 级 `round_retry` 消费 retry 池)。落点 = 备战(1 分支重判)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件(详情面板纯展示)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层(备战)交回重判。

## 8. 守卫与防线

节点预算 = 2 + 外循环 retry 池(on_fail_retry);点空白零效果 → 重入再做一次,卡死形态为分钟级可见失败(有界终止单);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「详情弹窗」;frame_tag = `overlay_role_detail`(dispatch 包装)。测试锁:无点名行为锁(骨架锁随基类,锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);建档 = `currency_war_battle_prep_equip_detail.yml`,空白点挂 `currency_war_battle_prep.yml`。
