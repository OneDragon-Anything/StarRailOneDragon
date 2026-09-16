# BOSS 简报(boss_briefing · 货币战争-BOSS简报)

> 代码 = `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`。职责:boss 节点前的「强敌来袭」全屏横幅——识别 → 点空白推进 → 直接交回外循环重判(点掉后去向由外循环全分支自然处理)。
> **判别单一源红线**:两画面判别器 `BOSS_BRIEFING_TOKENS`/`is_boss_briefing_texts` 禁在改码/迁移中分叉——四处消费同源(0p 分发锚加固 / 0q 位面过渡排他 / `CwScreenBattleWait._hit_completion_anchor` 完成白名单 / 外循环阶段一位面过渡身份臂排他接管)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 0p:**徽记模板锚「货币战争-BOSS简报.标识-阵营徽记」∨ 共享判别** `is_boss_briefing_texts`(全帧 OCR 含「强敌」片段;判别词双形态 = 简体「强敌」+ 繁首「強敌」,OCR 渲染波动在册)。锚 = 横幅左侧红旗标上的**阵营徽记模板**(`cw_boss_brief_emblem`,二值化模板匹配)——徽记是固定资产(简报三家不同阵营卡与横幅旗标同资产,matchTemplate 0.97+ 实证;2026-09-16 从标题 OCR 锚「标识-强敌来袭」换装,旧锚被「强敌来袭」→「强敌米」误读击穿)。片段判别是锚 miss 的兜底纵深,不是第二判据。
- 阶段一身份行:横幅遮挡下备战双锚仍透出命中(穿透形态)——备战不在分发清单,历史「帧误落备战分支空转 598s」事故见 [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- **与 0q 位面过渡的两画面排他**:两画面共享交互文案「点击空白处继续」但**位置不同**(本屏 y≈770 波段 / 位面过渡 y≈930 波段,各在自身画面档 area)——共享文案不作跨画面判据,位置即判据:0q 兜底入口按位面过渡**本屏 rect** 判定(本屏帧的共享文案不会落进位面过渡的提示区),0q 分支体内另保留 boss 判别排他(纵深)。第五局 1-9 实锤的旧全帧裸文本判定路径(被 boss 帧共享文案击穿 → 误派过渡 op 空 fail 循环)已由位置判定根治。
- **阶段一位面过渡身份臂排他(第四消费点)**:boss 帧标题被误读击穿阶段一本屏身份、而底图位面节点锚可读时,阶段一会命中位面过渡——该臂先查 boss 判别片段,命中即接管派发本屏 op 正面推进(不发过渡 op)。

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

节点预算 8;误分发防线在分发侧(0p 锚加固 + 阶段一位面过渡身份臂排他接管 + 0q 本屏 rect 判定/排他,见 §1)。原 0q 误分发型 fail streak 守卫(`PLANE_MISDISPATCH_LIMIT`)已退役,连续 fail 预算统一归外环通用网([../flow/guards.md](../flow/guards.md) §1)。

## 9. 遥测与锁面

- journal op 名 = 「BOSS简报」;日志前缀 `[cw-flow-boss]`。
- 测试锁:五段路径行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`;锚排他锁 = 代码注引用 `test_cw_anchor_exclusion.py`,该文件现状不在测试仓(开放设计注②)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #26(「点击空白处继续」出现即可点);画面档 = `assets/game_data/screen_info/currency_war_boss_briefing.yml`。

## 开放设计注

① 点掉后去向(已裁):本 op as-built 语义 = 点空白即交回重判、去向归外循环,boss 战自动开打、商店不开(代码模块头实证;README §5.1 已按此修正)——game 侧 `screen_flow_timing.md` #14/#27 的「关闭后自动开店」为过期口述口径,修正归 game 侧文档批。② 锚排他测试锁:`test_cw_anchor_exclusion.py` 在 sr-od-test 现状无对应文件,锁面重建归属待测试仓清理批。
