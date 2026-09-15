# 阿哈装备选择(aha_equip_pick · 备战 overlay)

> 代码 = `operations/cw_screen/cw_screen_aha_equip_pick.py::CwScreenAhaEquipPick`。职责:投资策略「阿哈大悦」的装备选择 overlay(为阿哈选 1 件简易装备)的一次访问——点第 1 装备自动关 overlay 交回。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环阶段三特殊规则(无独立画面档):锚 = `货币战争-备战.标识-简易装备`(overlay 叠备战,锚挂备战画面档;[../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。不选 → overlay 持续卡备战,推进是流程义务。

## 2. 画面形态声明

**空决策形态 + 固定策略申报**:选择面存在(四件选一)但零逻辑态账,本 op 按**固定单发**消费(点首件,不问策略器);按 key_equips 择优属策略面候选——为它设 decide 接口 = 给无选择面画面造空选择,违契约收缩方向(ADR-0584 §2.6)。推进型变体(`_progression_base.py::CwProgressionScreenOp` 子类),节点预算 = 2。

## 3. 观察面

轻观察:入口/重入观察 = `entry_ok` 基类 area 锚原语(与分发判定同源同参)。零 GameState 写端。

## 4. 动作面

`progress_once` = 读 `货币战争-备战.按钮-简易装备首件` center(`kernel/cw_obs_core.py::area_center`;矩形中心即首件位)→ `click` 单发(原分支无 `mouse_move`,保持)。坐标缺失 = False → 基类 `round_fail`。点首件后游戏自动关 overlay。

## 5. 终结与交回

推进已发 → `round_retry` 重入;重入 = 锚 miss = 已离开 → `success` 交回;预算耗尽 FAIL 交回。落点 = 备战(1 分支重判)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;获得装备的真值由下一备战入口观察重锚(装备域 owned 读面)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层(备战画面)交回重判。

## 8. 守卫与防线

节点预算 = 2(基类合同);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「阿哈装备选择」;frame_tag = `overlay_aha_equip`(dispatch 包装)。测试锁:无点名行为锁(骨架锁随基类,锁面根 = `sr-od-test/test/sr_od/application/currency_war/`);锚挂备战建档 `currency_war_battle_prep.yml`。

## 开放设计注

- 固定点首件的策略化候选(按 key_equips 择优)未建模;若策略化须先立选择面判据归属(ADR-0584 §2.6),本 op 形态随之改版。
