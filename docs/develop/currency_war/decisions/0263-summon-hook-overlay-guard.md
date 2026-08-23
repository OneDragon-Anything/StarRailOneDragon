# ADR-0263: summon 停机钩子加右侧 overlay 关闭守卫

- **Status**: accepted
- **Date**: 2026-08-24

## Context

2026-08-23 10:41 局69 summon 钩子误触停机(证据帧 `summon_unknown__034f8ef3.png`):
slot6 白框 rect `(1004,847,1118,978)` 裁出的是**右侧奖励/金币说明 overlay 的
连胜规则表**(火焰图标 + 2-4/5/6+ 档位数字),非角色立绘 —— overlay 开着时盖在
备战栏上,固定 slot rect 裁到 overlay 内容 → SIFT 零匹配(97 关键点 vs 阿格莱雅
模板 good=0)→ 误报「占用未识别」停机。稍后面板关闭,同 rect 裁到真立绘,
阿格莱雅正常识别。

既有帧态门 `is_prep_like_frame`(r330)只判「备战/开商店精准帧」,**不检测右侧
overlay** —— 本帧是备战态精准帧,门放行,守卫缺口在 overlay 维度。

同病核查(layout / bookcard 钩子,`cw_identity_obs.read_deployed_chars` /
`read_bench_chars`):

- **layout 钩子免疫**:触发条件 = 有效后排槽数无档,判据来自 deploy_cap
  (舞台上方中央 X/Y OCR 指示),**不裁备战 slot rect**;X/Y 指示在顶部中央,
  不被右侧 overlay(x≥1000,盖备战栏带)遮挡 → 判据不受 overlay 影响。
- **bookcard 钩子免疫**:触发极性是 `find_bookcards` 的**正向 TM 命中**
  (书册卡模板 ≥0.75 于 slot rect 内),非 summon 的「占用 + 识别不匹配」缺位
  判定 —— overlay 盖住槽位只会让模板匹配不到(不触发),overlay 自身内容对
  书册卡模板 TM 到不了 0.75(同库互撞实测 ≤0.505 量级)→ 无假阳性路径。

## Considered Options

1. **overlay 守卫跳过(采纳)** —— 右侧 overlay 在场 → 本帧跳过识别判定
   (不 flag 不停机),等下一帧 overlay 关了再判。判据全部复用既有机制
   (无新坐标/新模板):①备战屏「标识-简易装备」area(battle_loop 0g 的
   阿哈大悦 overlay 锚)OCR 到文本;②全图 OCR 含「金币说明」关键词(本次
   误触帧特征;探测法同 `_overlay_confirm` 全屏关键词路,crop_first=False
   复用同帧 OCR 缓存)。任一在场即拦。bot 侧 `battle_loop` 0g 已有 overlay
   自动处理分支,overlay 会被消费关掉,守卫只损失 overlay 开着的少数帧。
2. **overlay 自动关闭(钩子内主动点掉再判)** —— 钩子埋在 reader 深处
   (`read_bench_chars` 被识别/对账多路径调用),reader 带副作用点击违反
   观测层纯读约定;且 overlay 属于 battle_loop 已处理的 UI 态,reader 内
   重复处理双源。拒绝。
3. **rect 动态定位(overlay 开时重算 slot rect)** —— 每帧动态定位成本高、
   且 overlay 下立绘被部分遮挡,SIFT 未必匹配;为罕见帧引入新定位机制,
   复杂度不成比例。拒绝。

## Decision

`cw_identity_obs.py` 新增 `_right_overlay_open(ctx, screen)`(best-effort,
异常 → False 回落旧判定);summon 钩子在 `is_prep_like_frame` 通过后、存
sentinel/停机前调用,在场即 break 跳过本帧。layout / bookcard 钩子按同病
核查结论免疫,代码注释记录核查依据(防后人重复排查)。

## Consequences

- 右侧 overlay 开着时的「占用未识别」帧不再停机;overlay 被 battle_loop
  消费关闭后下一帧正常判定 —— 真未知物品的发现延迟至多一个 overlay 周期。
- 守卫锚「金币说明」尚无 screen_info area(「货币战争-金币说明弹窗」建档
  待建,见 `cw_observation_gate.PROFILE_POPUP` 注);目前走全图 OCR 关键词,
  建档后可切 area rect(行为不变,读取更省)。
- 锁测试 `test_cw_adr0263_overlay_guard.py`:两态断言(overlay 开不停机 /
  关正常停)+ 判据①(简易装备锚)单独拦截。
