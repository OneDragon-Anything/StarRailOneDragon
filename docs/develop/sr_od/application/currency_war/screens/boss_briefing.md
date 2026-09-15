# BOSS 简报(boss_briefing · 货币战争-BOSS简报)

> 代码 = `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`。职责:boss 节点前的「强敌来袭」全屏横幅——识别 → 点空白推进 → 直接交回外循环重判(点掉后去向由外循环全分支自然处理)。
> **判别单一源红线**:两画面判别器 `BOSS_BRIEFING_TOKENS`/`is_boss_briefing_texts` 禁在改码/迁移中分叉——三处消费同源(0p 分发锚加固 / 0q 位面过渡排他 / `CwScreenBattleWait._hit_completion_anchor` 完成白名单)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0p:**area 锚「货币战争-BOSS简报.标识-强敌来袭」∨ 共享判别** `is_boss_briefing_texts`(全帧 OCR 含「强敌」片段;判别词双形态 = 简体「强敌」+ 繁首「強敌」,OCR 渲染波动在册)。area 锚(LCS)可被 OCR 误读击穿(「强敌来袭」→「强敌米」),片段判别是锚加固兜底,不是第二判据。
- **先于备战双锚**(序位):横幅遮挡下备战双锚仍透出命中(穿透形态),无本分支时帧误落备战分支空转(序位表 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- **与 0q 位面过渡的两画面排他**:两画面共享交互文案「点击空白处继续」,共享文案不作跨画面判据——0q 分支 OCR 命中后先查 boss 帧判别,命中 = 排他留 0p(排他判定在 0q 分支体内,单一源 = outer_loop §2.2 两行,本篇不复写判定式)。0p 分发成功回调清 0q 误分发计数(`_plane_mis_streak = 0`,外循环 on_result 闭包 = guards.md §3 补注的守卫域归属)。

## 2. 画面形态声明

**空决策形态**(纯推进)。本屏无重入裁决旗标:点空白 `round_success` 即交回,横幅退场由下一帧外循环分发判定(不承诺落点);横幅已退 = observe 段早退 success 同语义。单动作单发零 op 内重试,节点预算 8。装配点分流同族(两端口在场 → 五段;缺省 → 生产直连旧路径)。

## 3. 观察面

横幅判定(`lifecycle_observe`):area 锚 miss → `is_boss_briefing_texts(read_ocr_texts)` 兜底(`read_ocr_texts` = 全帧 OCR,`ocr_service` 同帧缓存);判定不在 = 已推进 → 早退 success。零 GameState/session 写端(纯过场,无观察上报面)。

## 4. 动作面

单动作 = 点空白:`kernel/cw_obs_core.py::area_center('区域-空白点击', '货币战争-BOSS简报')` → mouse_move 先行 + click(overlay 族同款点击时序)→ 固定短等(click 异步落地 + 横幅退场动画)。建档缺失(「区域-空白点击」无 area)→ `round_fail` 留证缺建档。

## 5. 终结与交回

点空白即终结:`round_success('点空白已发,交回外循环重判')`。交回后外循环全分支重判落点(boss 战/备战/流转)不由本 op 承诺。

## 6. 状态上报面

零写端(无转移函数腿、无 session 面、on_outcome 无登记件)。

## 7. 子态与 overlay

横幅全屏帧即本屏形态,无子态。与位面过渡共享推进文案但为独立画面档(排他见 §1)。

## 8. 守卫与防线

节点预算 8;误分发防线在分发侧(0q 排他 + 误分发型 fail streak/超限 round_fail 留外循环,`PLANE_MISDISPATCH_LIMIT` = [../flow/guards.md](../flow/guards.md) §3)。

## 9. 遥测与锁面

- journal op 名 = 「BOSS简报」;日志前缀 `[cw-flow-boss]`。
- 测试锁:五段路径行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`;锚排他锁 = 代码注引用 `test_cw_anchor_exclusion.py`,该文件现状不在测试仓(开放设计注②)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../game/currency_war/research/screen_flow_timing.md) #26(「点击空白处继续」出现即可点);画面档 = `assets/game_data/screen_info/currency_war_boss_briefing.yml`。

## 开放设计注

① 点掉后去向(已裁):本 op as-built 语义 = 点空白即交回重判、去向归外循环,boss 战自动开打、商店不开(代码模块头实证;README §5.1 已按此修正)——game 侧 `screen_flow_timing.md` #14/#27 的「关闭后自动开店」为过期口述口径,修正归 game 侧文档批。② 锚排他测试锁:`test_cw_anchor_exclusion.py` 在 sr-od-test 现状无对应文件,锁面重建归属待测试仓清理批。
