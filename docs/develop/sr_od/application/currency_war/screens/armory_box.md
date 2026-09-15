# 武装箱说明弹窗(armory_box · 货币战争-武装箱弹窗)

> 代码 = `operations/cw_screen/cw_screen_armory_box.py::CwScreenArmoryBox`。职责:「简易武装箱」类道具获得说明弹窗(0f)的一次访问——点 × 关闭(道具进背包)+ 重入观察裁决交回。开箱 = 备战箱槽 `OpenBox` 链路,四选一选卡 = `cw_screen_box_pick.py::CwScreenBoxPick`(0f2),均不在本 op。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0f:锚 = `货币战争-武装箱弹窗.标识-简易武装箱`(id_mark;建档 = `currency_war_armory_box_dialog.yml`)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。弹窗叠在 3 选 1 屏或备战上,不关闭会挡死底层屏交互。

## 2. 画面形态声明

**空决策形态**(无选择面 ∧ 无逻辑态账,判据 = [README.md](README.md) §3)。基类直迁子类(`CwScreenOpBase`):`handle` 自持标识门 → 重入裁决(留守分流前共享段)→ 装配点分流(两端口在场走五段,缺省生产直连旧序列)→ `_close_dialog` 单动作体。

## 3. 观察面

轻观察:payload = `cw_screen_armory_box.py::ArmoryBoxObservation`(仅稳定帧引用);标识门在 `lifecycle_observe` 段内(miss 且未发 → `round_fail` 交编排壳)。零 GameState 写端。

## 4. 动作面

唯一动作 = 点 ×:`_close_dialog` 读 `货币战争-武装箱弹窗.按钮-关闭` center(`kernel/cw_obs_core.py::area_center`,缺失 = `round_fail`)→ `mouse_move`+`click`(bug#1 缓解)→ 固定 1s → 置位 `_click_pending`。弹窗内箱图标为展示图不可点(op 零消费;档案「按钮-开箱点击」为未消费定位区)。关闭不属 `kernel/cw_vocab.py::CW_ACTION_TYPES`(推进非动作)。

## 5. 终结与交回

重入裁决:`_click_pending` 在 ∧ 标识 miss = 已关 → `round_success(wait=1.0)` 交回;标识仍在 = 点击未落地 → 重点(计节点预算)。交回后外循环全分支重判:0e/0s 投资策略/环境、1 备战、0f2 武装箱选择。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件;「道具已入背包」由下一帧观察侧重锚(owned 读面)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;关闭后不追踪底层屏恢复——底层屏身份由外循环重判(单一分发源)。

## 8. 守卫与防线

节点预算 = `node_max_retry_times=8`,耗尽 FAIL 交回(有界终止单);无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「武装箱」(dispatch 包装落 `[cw-op]` 行);frame_tag = `overlay_armory_box`;日志前缀 `[cw-armbox]`。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(`_CLOSING_OPS` 点名成员);建档 = `currency_war_armory_box_dialog.yml`。

## 开放设计注

- 档案「按钮-开箱点击」定位区无生产消费点(退役或保留候建档清理批);sim 腿不适用(F11 例外清单),等价判据承重 = 实机行为锁 + 新路径行为锁。
