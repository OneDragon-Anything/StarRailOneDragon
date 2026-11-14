# 失败形态适配详设（块 A/B/C）

共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包，weekly-challenge-core 3.1 落地）的三个消费方适配。共享件本迭代零改动零新增接口；家族先例 = 周本核心「失败画面继续」节点（weekly-core.md ⑪）。

## 1. 块 A：UseTrailblazePower 失败适配 + 迁移开拓力 app

### 1.1 迁移件（机械，先做）

- 文件：`src/sr_od/challenge_mission/use_trailblaze_power.py` → `src/sr_od/application/trailblaze_power/use_trailblaze_power.py`。
- import 消费方同步（grep 全量为准，现状两处）：`trailblaze_power_app.py:15`、`farm_material.py:40`。
- 测试镜像：`sr-od-test/test/sr_od/challenge_mission/test_use_trailblaze_power_timeout.py` → `sr-od-test/test/sr_od/application/trailblaze_power/`（路径随迁；断言面变化见 1.3 判据同步）。
- 类名/构造签名/除失败分支外行为：零变更。

### 1.2 现状断点（适配依据）

- `_after_battle_result`（use_trailblaze_power.py:290-307）：胜利/失败共用裸边进入（`@node_from(from_name='等待战斗结果')` 不分 status），失败到达后同样点「战斗画面·退出关卡/再来一次按钮」——新形态两按钮皆无 → retry（默认 3）耗尽 FAIL，失败画面残留。
- `_wait_battle_result_timeout` 判负分支（:273-275）：`state == '战斗失败'` → `_click_exit_after_result` 点「退出关卡按钮」——新形态同断。
- 判停/退出的既有收尾 `back_at_last`（:342-345）= `BackToNormalWorldPlus`，起点任意可控画面幂等，保留。

### 1.3 节点卡（新增/变更）

**新节点「失败画面继续」**
- 入口边：`@node_from(from_name='等待战斗结果', status='战斗失败')`（qualified——把现裸边拆分，胜利走原路）。
- 行为：委托 `ResumeFromBattleFail`（自带新/旧两态分流，花萼/凝滞虚影/侵蚀隧洞/培养目标各形态通吃）→ success → 分支：`battle_fail_times >= 5` → `round_success('连败关副本')`；否则 → `round_success('失败重发')`。共享件 fail → `round_by_op_result` 透传（现场交上层，不收尾）。
- 「战斗失败」计场语义不变：失败不计 `finish_times`、`on_battle_success` 回调不因失败触发（现状 :234-236）。

**节点「战斗结果处理」收窄为胜利路径**
- 入口边改 `@node_from(from_name='等待战斗结果', status='挑战成功')`（原裸边删除——失败不再进入本节点）。
- 内部逻辑不变：达标（`finish_times >= plan_times`）或连败判定……连败判定移除（连败改走「失败画面继续」→「连败关副本」出口）；仅剩达标退出/再来一次（胜利结算画面按钮真实存在，现状行为保留）。
- 边界说明：旧形态失败（若某些副本类型仍出旧结算画面）不再经过本节点——共享件两态分流已在「失败画面继续」处理，本节点只见真胜利。

**「失败画面继续」的两个出口的落点节点**
- `'失败重发'` → `@node_from(status='失败重发')` 挂到**「选择次数」**节点（use_trailblaze_power.py:85-98）：滑条节点每轮重算 `plan_times - finish_times`（:105）本轮次数，失败重发经过它记账自洽；「回点击挑战则滑条不重放、下轮用画面残留值」的备选废弃（占位草案既定）。
- `'连败关副本'` → 新终局出口：点「挑战副本·按钮-关闭副本」（:1838,38-1888,95 已建档）→ until 大世界 → 既有 `back_at_last`（幂等收尾）。实现形态：`round_by_find_and_click_area('挑战副本', '按钮-关闭副本', until_find_all=[('大世界','…锚')])` 后 `round_by_op_result(BackToNormalWorldPlus)` —— 二段幂等（关闭副本已落大世界时 BackToNormalWorldPlus 快速成功）。

**「战斗超时收尾」判负分支改委托**（use_trailblaze_power.py:273-275）
- `state == '战斗失败'` → 委托 `ResumeFromBattleFail` → success → `round_success('超时判负关副本')` → 沿边进「连败关副本」的关闭副本出口（超时语境不重试——占位草案既定）；共享件 fail → 透传。
- 判胜分支（:265-272 补记+点退出关卡）不变——胜利结算画面按钮存在。

**既有测试判据同步（必红改写，非回归）**
- `test_use_trailblaze_power_timeout.py:112-129`：`test_cleanup_on_fail_exits_without_counting` 断言「判负 → 点退出关卡按钮」——改为「判负 → 委托共享件（点空白/回挑战画面锚）」；直呼桩手法不变。
- 既有超时边结构/窗口值断言（:57-85）不受影响（常量与边保留）。

### 1.4 mock 场景（fixture 驱动 + 直呼）

1. 主链失败一次 → 共享件回挑战画面 → 滑条重发 → 胜 → 达标退出（status 完成链不变）。
2. 连败 5 次 → 「连败关副本」→ 关闭副本 → 大世界收尾（status 经 back_at_last）。
3. 超时判负 → 共享件 → 关副本退出（`test_cleanup_on_fail` 改写版）。
4. 超时判胜 → 补记+退出（既有，回归确认）。
5. 共享件 fail → op fail 透传、现场残留（断言 op fail + 无收尾点击）。

## 2. 块 B：角色线手动路线失败适配（UpgradeCharacterOp）

### 2.1 现状断点

- `manual_fight`（upgrade_character.py:726-760）：编队态点击开始；非编队态（含战斗失败画面）→ `BATTLE_DONE` 交返回分类。失败计场已发生（离开编队态时按 `_squad_clicked` 旗标计 `_farm_rounds`/`_manual_fights`，:749-754——开拓力已扣，计场正确）。
- `back_to_ascend`（:766+）flat 分类分支：等级提升锚/结算画面（点退出关卡）/副本画面/编队画面/残留弹窗取消/大世界重走入口链/过渡帧慢询。**「大世界-战斗失败」不在任何分支**（新形态无退出关卡按钮 → 结算分支 MISS）→ 落过渡帧慢询 → 节点 300s 超时 FAIL。

### 2.2 节点卡

**`back_to_ascend` 增加首位分支「失败画面」**
- 锚：`round_by_find_area('大世界-战斗失败', '标题-战斗失败')`（置于等级提升锚之后、结算分支之前——顺序无冲突，画面互斥）。
- 行为：委托 `ResumeFromBattleFail` → success（挑战画面回归）→ `round_success('失败重发')`；fail → `round_by_op_result` 透传（现场交上层）。
- 落点依据：花萼手动路线失败回挑战画面（= 资源窗口「进入」的落点形态，`挑战副本` 画面档已建，共享件挑战锚「挑战副本·挑战按钮」对该帧命中）。

**失败重发的回链（零新节点）**
- `'失败重发'` → `@node_from(status='失败重发')` 挂回 **`farm_in_dungeon`**（:572 副本画面分流——挑战画面命中挑战锚 → 编队态交 `manual_fight` 重发；既有分流链原样复用）。
- 预算兜底：失败场已计入 `_farm_rounds`（开拓力已扣，计场正确）；连败烧完 `farm_rounds_max` → 既有预算判停分支（:500-503）自然接管，**不另设连败阈值**（重发边际成本 = 一场开拓力，已获 farm_dungeon 授权；预算耗尽判停即如实报告）。
- 老形态失败（旧结算画面带退出关卡按钮）：既有结算分支行为保留（点退出关卡 → 副本画面 → 点关闭X → 按栈回退）——新分支只截「大世界-战斗失败」新形态，互斥不冲突。

### 2.3 mock 场景

1. 手动路线失败一次 → 共享件 → 挑战画面 → 重发 → 胜 → FARMED（`_farm_rounds` 含败场计 2）。
2. 预算 1 + 首场败 → 共享件回挑战画面 → 预算判停（既有判停 status，日志含败场）。
3. 共享件 fail → op fail 透传。
4. 券路线回归确认（无失败画面帧 → 行为与现状一致）。

## 3. 块 C：光锥线手动路线失败适配（UpgradeLightConeOp）

与块 B 同构，差异就地标注：

- 断点：`back_after_farm`（upgrade_light_cone.py:696+）同样无失败画面分支（结算锚 MISS → 过渡帧慢询 → 300s 超时 FAIL）。
- 分支锚/委托/出口同块 B；**失败重发回链挂 `副本刷取分流`**（farm_in_dungeon，:529——副本画面 → 编队态 → `MANUAL_FIGHT` 交 `manual_fight`）。
- 计场差异保留现状：光锥线在 `manual_fight` 点击时计场（:686-688），失败时已计，不统一两线计场时机（不扩面）。
- 光锥线特有：失败后重发走「手动路线落点=大世界」的差异已被共享件消解（失败直接回挑战画面，不经大世界）——返回分类既有「手动路线副本关闭落大世界 → BACK_TO_WORLD 重走入口链」分支不受影响（那是正常完成路径）。
- mock 场景同块 B 三条 + 券路线回归确认，帧用光锥线同款（挑战画面/失败画面帧共享）。

## 4. 关键取舍

- **失败重发回链定死滑条节点（块 A）/既有分流节点（块 B/C）**——重发必须经过「重算本轮次数」或「既有画面分流」，禁止跳过记账直点挑战；备选（直回点击挑战）废弃：滑条不重放会用画面残留次数，记账漂移。
- **失败计场即重发，不设连败阈值（块 B/C）**——预算 `farm_rounds_max` 天然封顶；块 A 保留连败 5 阈值（体力计划一条龙场景单场成本 30 开拓力×连打，阈值关副本止损是占位草案既定）。
- **旧形态失败由共享件两态分流兜住**——三个消费方都不自带形态判断，形态事实单一源在共享件（家族先例周本核心 ⑪ 同款）。
- **迁移与适配同迭代同批（块 A）**——同文件同函数触碰两次不如一次；迁移是机械件，适配是行为件，landing 分两个提交。
