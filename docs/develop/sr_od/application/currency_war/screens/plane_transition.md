# 位面过渡(plane_transition · 货币战争-位面过渡)

> 代码 = `operations/cw_screen/cw_screen_plane_transition.py::CwScreenPlaneTransition`。职责:「点击空白处继续」提示出现即点空白(简报「下一步」后 / 每个 boss 位面开始时各一次);完成 = 提示消失(真转移)交回循环;提示未现 = 该步不适用(fail 交编排壳/循环重新分流)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0q:本档提示区「货币战争-位面过渡.提示-点击空白继续」**rect 判定命中**(旧全帧裸文本 OCR 判定被 boss 帧共享文案击穿——boss 帧同一文案在 y≈770 波段,本屏 y≈930,位置即判据;第五局 1-9 实锤路径已根治)∧ **非 boss 帧**(排他判定 = `is_boss_briefing_texts`,判别单一源 = `cw_screen_boss_briefing.py`,两画面排他形态详见 [boss_briefing.md](boss_briefing.md) §1)。
- 分发 = 阶段一身份行(节点锚)+ 误读兜底([../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。阶段一身份臂含 boss 判别排他:身份命中帧含「强敌」片段 → 接管派发 BOSS 简报,不派本屏 op(防 boss 帧位面锚可读时误派空 fail)。连续 fail 预算归外环通用网(`OP_FAIL_REDISPATCH_LIMIT`,[../flow/guards.md](../flow/guards.md) §1)——原 0q 专用误分发 streak 守卫(`PLANE_MISDISPATCH_LIMIT`)已退役并入。

## 2. 画面形态声明

**空决策形态**(纯推进)。重入裁决旗标 `_click_pending`(验证废除形态):点空白已发 → 提示不在 = 过渡完成 → success;提示在 = 点击未落地 → 重点(计节点预算)。裁决位序 = pending 先行、miss fail 后置(与未达上限弹窗的 miss 分支内序不同,各屏分支序语义各异,禁跨屏统一)。装配点分流同族(两端口在场 → 五段;缺省 → 生产直连旧路径)。节点预算 8。

## 3. 观察面

提示门 = 「货币战争-位面过渡.提示-点击空白继续」(**本档 area 名无「处」字**;与 BOSS 简报档「提示-点击空白处继续」为两张画面档各自的 area,不相通用)。提示未现 = 未到位(上位面未结束)或已过去 → fail 交重新分流。零写端。

## 4. 动作面

单动作 = 点空白:`kernel/cw_obs_core.py::area_center('区域-空白点击', '货币战争-位面过渡')` → mouse_move 先行 + click(overlay 族同款点击时序)→ 固定短等(点击异步落地 + 过渡翻页动画)→ 置位。建档缺失 → `round_fail` 留证。

## 5. 终结与交回

重入观察裁决:提示已消失 → `round_success(wait=1.0)` 交回外循环重判(下一位面/流转由全分支判定);点击未落地 → 重点计节点预算;首发 miss → fail。

## 6. 状态上报面

零写端(无转移函数腿、无 session 面、on_outcome 无登记件)。

## 7. 子态与 overlay

过渡全屏动画帧,无子态;与 boss 简报的排他见 §1。

## 8. 守卫与防线

节点预算 8;连续 fail 预算归外环通用网([../flow/guards.md](../flow/guards.md) §1);误派防线 = 阶段一身份臂 boss 排他 + 0q 本屏 rect 判定/排他(§1)。

## 9. 遥测与锁面

- journal op 名 = 「位面过渡」;日志前缀 `[cw-flow-plane]`。
- 测试锁:五段新路径行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(代码注另引 `test_cw_flow_ops.py`(现状:sr-od-test 无此文件,锁面重建归测试仓批;申报见下),现状不在测试仓 = 开放设计注)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #2/#29;画面档 = `assets/game_data/screen_info/currency_war_plane_transition.yml`。

## 开放设计注

代码注引用的 `test_cw_flow_ops.py` 在 sr-od-test 现状无对应文件(锁面重建归属待测试仓清理批,与 [boss_briefing.md](boss_briefing.md)/[wait_one_one.md](wait_one_one.md) 同批申报)。
