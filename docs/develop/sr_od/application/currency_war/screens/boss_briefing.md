# BOSS 简报(boss_briefing · 货币战争-BOSS简报)

> 代码 = `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`(两 node 直继承 `SrOperation`)。职责:boss 节点前的「强敌来袭」全屏横幅——识别 → 点空白推进 → 直接交回外循环重判(点掉后去向由外循环全分支自然处理)。
> **判别单一源红线**:两画面判别器 `BOSS_BRIEFING_TOKENS`/`is_boss_briefing_texts` 禁在改码/迁移中分叉——三处消费同源(op 内锚 miss 兜底 / `CwScreenBattleWait._hit_completion_anchor` 完成白名单 / 外循环阶段一位面过渡身份臂排他接管)。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(BOSS简报):**徽记模板锚「货币战争-BOSS简报.标识-阵营徽记」∨ 共享判别** `is_boss_briefing_texts`(全帧 OCR 含「强敌」片段;判别词双形态 = 简体「强敌」+ 繁首「強敌」,OCR 渲染波动在册)。锚 = 横幅左侧红旗标上的**阵营徽记模板**(`cw_boss_brief_emblem`,二值化模板匹配)——徽记是固定资产(简报三家不同阵营卡与横幅旗标同资产,matchTemplate 0.97+ 实证;2026-09-16 从标题 OCR 锚「标识-强敌来袭」换装,旧锚被「强敌来袭」→「强敌米」误读击穿)。片段判别是锚 miss 的兜底纵深,不是第二判据。
- 阶段一身份行:横幅遮挡下备战双锚仍透出命中(穿透形态)——备战不在分发清单,历史「帧误落备战分支空转 598s」事故见 [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- **与位面过渡的两画面排他**:两画面共享交互文案「点击空白处继续」但**位置不同**(本屏 y≈770 波段 / 位面过渡 y≈930 波段,各在自身画面档 area)——共享文案不作跨画面判据。误派链(标题误读 → 全帧裸文本兜底被 boss 帧共享文案击穿 → 误派过渡 op 空 fail 循环,第五局 1-9 实锤)已根治:本屏锚换装徽记模板(标题不再承重)+ 外循环阶段一位面过渡身份臂 boss 判别排他(第四消费点);原 0q 兜底随「未建档实证不作兜底」裁定退役(2026-09-16,见 outer_loop §2.3)。
- **阶段一位面过渡身份臂排他(第四消费点)**:boss 帧标题被误读击穿阶段一本屏身份、而底图位面节点锚可读时,阶段一会命中位面过渡——该臂先查 boss 判别片段,命中即接管派发本屏 op 正面推进(不发过渡 op)。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 横幅判定(area 锚 miss → 判别兜底;判定不在 = 已推进 → 早退 success 交回)+ obs{on_screen} + 占位 report 调用;决策动作 node = 单动作单发(点空白)→ `round_success` 交回——本屏无重入裁决旗标,横幅退场由下一帧外循环分发判定(不承诺落点);`node_max_retry_times=8` 现役值仅框架异常路径消费。

## 3. 观察面

横幅判定(观察 node):area 锚 miss → `is_boss_briefing_texts(read_ocr_texts)` 兜底(`read_ocr_texts` = 全帧 OCR,`ocr_service` 同帧缓存);判定不在 = 已推进 → 早退 success。obs = `CwScreenBossBriefingObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/boss_briefing.py`);report = `report_screen_boss_briefing_obs` 占位调用(本屏现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。零 GameState/session 写端(纯过场,无观察上报面)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内 | 画面 op 留守臂(决策动作 node `act`:`area_center` 读「货币战争-BOSS简报.区域-空白点击」center → mouse_move + click) | 无自上报(观察上报 = `report_screen_boss_briefing_obs` 占位调用,观察 node 承载;现役零容器写点) | **是(点空白即终结)**:`round_success('点空白已发,交回外循环重判')` 一次点击即交回,落点由外循环全分支重判 |

单动作 = 点空白:`kernel/cw_obs_core.py::area_center('区域-空白点击', '货币战争-BOSS简报')` → mouse_move 先行 + click(overlay 族同款点击时序)→ 固定短等(click 异步落地 + 横幅退场动画)。建档缺失(「区域-空白点击」无 area)→ `round_fail` 留证缺建档。

## 5. 终结与交回

- 点空白即终结(动作出口):`round_success('点空白已发,交回外循环重判')`。交回后外循环全分支重判落点(boss 战/备战/流转)不由本 op 承诺。
- 观察门判定不在(锚 miss ∧ 判别兜底不中 = 横幅已退)→ 早退 `round_success` 交回外循环重判(落点语义同上)。
- 「区域-空白点击」建档缺失 → `round_fail` 留证缺建档,交外循环按画面重分发。

## 6. 状态上报面

零写端(无转移函数腿、无 session 面;无落地登记件)。

## 7. 子态与 overlay

横幅全屏帧即本屏形态,无子态。与位面过渡共享推进文案但为独立画面档(排他见 §1)。

## 8. 守卫与防线

`node_max_retry_times=8` 现役值仅框架异常路径消费;误分发防线在分发侧(0p 锚加固 + 阶段一位面过渡身份臂排他接管 + 0q 本屏 rect 判定/排他,见 §1)。原 0q 误分发型 fail streak 守卫(`PLANE_MISDISPATCH_LIMIT`)已退役,连续 fail 预算统一归外环通用网([../flow/guards.md](../flow/guards.md) §1)。

## 9. 遥测与锁面

- journal op 名 = 「BOSS简报」;日志前缀 `[cw-flow-boss]`。
- 测试锁:两 node 行为锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(BOSS 简报真类装配与观察门 miss 早退);锚排他锁 = 代码注引用 `test_cw_anchor_exclusion.py`,该文件现状不在测试仓(开放设计注②)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #26(「点击空白处继续」出现即可点);画面档 = `assets/game_data/screen_info/currency_war_boss_briefing.yml`。

## 开放设计注

① 点掉后去向(已裁):本 op as-built 语义 = 点空白即交回重判、去向归外循环,boss 战自动开打、商店不开(代码模块头实证;README §5.1 已按此修正)——game 侧 `screen_flow_timing.md` #14/#27 的「关闭后自动开店」为过期口述口径,修正归 game 侧文档批。② 锚排他测试锁:`test_cw_anchor_exclusion.py` 在 sr-od-test 现状无对应文件,锁面重建归属待测试仓清理批。
