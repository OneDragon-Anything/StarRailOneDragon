# DD-006:结算读点链 boss 胜局形态修复——失败页分支抢走页1 + 填充率页2 假值 + killed 兜底误判

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期决策记录,类名保持当时事实,未改)。

> 状态:已落地(2026-09-02;离线帧复现 + 实机验证局 1;受影响测试全绿)。

## 背景

夜间语料批(3 局,run_20260902_014515/023643/031945)boss 胜局遥测断链三症状:
outcomes 36 行 `damage_base`/`damage_unfinished_progress` **0/36**(画面有值:
基础伤害恒 -10,tooltip 面板在页1 帧实证在场);`progress_fill_ratio` 在 3 个
boss 行同读 **0.392**(疑固定值);boss 行 `killed=False`(节点实为胜利)。

离线对帧复现(`fixtures/settle_ocr/window_batch/h_091-h_093` + 生产日志
02:13:02-02:13:07 逐行):读数器本体无缺陷——`read_settle_damage_breakdown`
对 boss 胜局页1 帧离线读出 base=-10/undone=-7/heal=+2 全对。断链在**分支路由
与时序**,三根因:

1. **失败结算页分支(1f)在 boss 胜局页1 误命中**:1f 门 = 「挑战进度」模板 +
   「挑战结束」模板 + 无「继续挑战」——boss 胜局页1 三门全中(它带进度条、
   标题「挑战结束」、页1 无继续挑战)。页1 被整条抢走,分支2(「点击空白加速」,
   三项遥测暂存的唯一通道)零执行 → 页2 记录时暂存为空 → damage 两分量 0/36。
   生产日志铁证:boss 局 02:13:03.842 打出「loss_page 行不落:killed=True」。
2. **填充率页2 假值**:`parse_progress_fill_ratio` 的条矩形 (710,422)-(1210,444)
   在页2 帧罩在 HP 心形图标上,橙金像素满足红色判据 → 确定性读出假 ratio
   (3 局 boss 行同 0.392 = 同一图形同一矩形)。真条只在页1 存在,页2 根本
   不该读。
3. **killed 的 hp 对比兜底在 boss 胜局恒误判**:boss 胜局 HP 净降(未达最低
   进度要扣血,如 55→23),兜底「hp 降 = 输」把节点胜利判成失败。真值通道
   (页1 「挑战进度 +2」)因根因 1 页1 被抢而缺席。

## 裁决

1. **1f 门加 boss 胜局排除**:`is_boss_win_settle_page1`(纯函数)= 挑战进度
   带符号增量 > 0(节点胜利;战败为负或读不到)。1f 前三模板门全中时追加
   全屏 OCR 判别,命中则不进 1f、落空到分支2。
2. **1f 内补页1 三项暂存(兜 OCR 偶漏)**:排除判别依赖 OCR 读到 '+2' 浮字,
   偶漏时 boss 胜局页1 仍走 1f——1f 在面板延迟门放行后做与分支2 同款的暂存
   (progress + damage 两分量 + fill,fill 后帧覆盖),telemetry-only 行的
   killed 门拒绝 boss 胜局行后暂存保留,页2 分支3 记录时合并。真败局页的
   telemetry-only 行在页1 直读面板已带值,记录路径消费暂存,无双记。
   残余缺口(审计追加后已闭合,见裁决 5):OCR 偶漏 '+2' 且 boss 胜局页1 走
   1f 时 `_saw_defeat_settlement` 曾被误置——置闩门收紧后该毒化面根除。
3. **填充率页态门**:`read_round_outcome` 只在帧含「点击空白加速」(页1 标记
   词)时读条,页2 帧恒 None;分支2/1f 暂存改 fill 后帧覆盖(页1 进条动画
   0.416→0.332 两帧实证,首帧中间值不可信,放行点击帧最 settled)。
4. **killed 判定序**:页1 progress 合并提前到 killed 判定之前;进度符号判定
   (`progress > 0 = 胜`)先于 hp 对比兜底;hp 兜底只在进度缺席时使用。
5. **败局闩置闩门(审计追加,二轮细化)**:1f 门 fail-open(None 漏读)进分支的帧
   **不立即**置 `_saw_defeat_settlement`——置闩按三态分级:'neg'(显式负增量)
   立即置闩;None(漏读)帧走**次级证据裁决**(新增 `_defeat_latch_by_secondary`:
   结算说明面板负分量 hp 净降 ∧ 全局节点序 t≥SETTLE_DEFEAT_LATCH_MIN_T=14
   双证据齐才置,证据不足不置并 log 留证)。M70 假 win 守卫的毒化面(boss 胜局
   页1 OCR 偶漏 '+2' → 整 run 永不判 win,真通关判废)由「一次 OCR 两用」根除:
   1f 门排除('pos')与置闩门('neg')消费同一次 `settle_page1_progress_sign`
   三态读数。残余边界(2-9/3-9 boss 胜局漏读误闩)已入 docstring。代价边界:真
   败局页 OCR 偶漏负增量且次级证据不足时少一层守卫,但 result 主门 = plane==3
   精确值,死局 plane<3 恒 loss,无 win 误判面;漏读不置闩帧 log 留证可检索。

## Considered Options(根因 1)

- **A. 时序补丁:在 1f 里等面板再读**(不排除路由)— 治标:fill 假值、killed
  误判、_saw_defeat_settlement 毒化全都还在,只是 damage 补上。
- **B. 换 1f 模板门区分两形态**(如加「点击空白加速」第二锚)— 两形态页1
  都有该词,无区分度;加「前往结算」按钮缺席锚 = 与「继续挑战」缺席重复。
- **C. 语义判别路由(采用)+ 1f 兜底暂存**:判别锚在游戏语义(进度符号 =
  胜负真值,与 2026-08-18「扣血=战斗失败」口径同源),不依赖布局细节;
  兜底暂存让判别失效率 ≠ 数据损失。数据通道单次修复覆盖三分量 + killed。

## 约束范围

- 修改面 = `battle_loop.py`(1f 门/暂存/killed 判定序)+ `cw_settlement_obs.py`
  (`is_boss_win_settle_page1`/fill 页态门 docstring)+ 测试
  (`test_cw_settle_telemetry.py` 4 例)。策略语义零改动(纯观测链)。
- 1f 每 candidate 帧多一次全屏 OCR(~0.3s,仅模板三门全中时):败局页1 停留
  期每轮多这一次,量级 = 每败轮数帧。

## 出处

- 离线证据:`.debug/temp/currency_war/redesign/fixtures/settle_ocr/`
  (h_092 帧 + probe_boss_frames/probe_fix_verify 输出;生产日志 mcp_server.log
  02:13:02-02:13:07);
- 批报告:`docs/develop/currency_war/redesign/reports/REAL_MACHINE_COLLECTION_1.md` ①/④/⑥;
- 设计单一源:`docs/develop/currency_war/strategy/05_observation.md` §3.1。
