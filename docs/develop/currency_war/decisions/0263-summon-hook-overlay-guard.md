# ADR-0263: summon 停机钩子 区域可见性守卫(通用 overlay 遮挡判定)

- **Status**: accepted(架构升级版:单 overlay 补丁 → 通用区域可见性守卫)
- **Date**: 2026-08-24

## Context

2026-08-23 10:41 局69 summon 钩子误触停机(证据帧 `summon_unknown__034f8ef3.png`):
slot6 白框 rect `(1004,847,1118,978)` 裁出的是**右侧奖励/金币说明 overlay 的
连胜规则表**(火焰图标 + 2-4/5/6+ 档位数字),非角色立绘 —— overlay 开着时盖在
备战栏上,固定 slot rect 裁到 overlay 内容 → SIFT 零匹配(97 关键点 vs 阿格莱雅
模板 good=0)→ 误报「占用未识别」停机。稍后面板关闭,同 rect 裁到真立绘,
阿格莱雅正常识别。

既有帧态门 `is_prep_like_frame`(r330)只判「备战/开商店屏级精准帧」,**不感知
overlay 维度** —— 本帧是备战态精准帧,门放行。分层缺口:帧态门管「哪个屏」,
没人管「屏上的区域是否被遮」。

## Considered Options

1. **通用区域可见性守卫(采纳)** —— 新函数
   `cw_obs_core.prep_areas_unobstructed(ctx, screen, rects)`:锚注册表
   `_KNOWN_OVERLAYS`(每条 = 锚 area + 覆盖带 Rect)驱动,锚 OCR 命中且覆盖带
   与目标 rect 相交 → 判被遮。不是 summon 专属补丁:任何「裁固定 rect 做判定」
   的钩子在判定前都可用同一函数自检。选它因为它修的是**分层缺口**(区域可见性
   维度缺失),不是单个 overlay 的症状;新 overlay 发现时注册表追加一行即可。
2. **单 overlay 关键词补丁(首版实现,已被 1 吸收)** —— 全图 OCR 含「金币说明」
   → 跳过。能修本次误触,但下一个 overlay(阿哈大悦装备选择等)出现时还要再
   打一个补丁;关键词探测无区域语义,不能回答「我这个 rect 是否被遮」。
   其实现保留为选项 1 的一个锚探针实例。
3. **overlay 自动关闭(钩子内主动点掉再判)** —— 钩子埋在 reader 深处
   (`read_bench_chars` 被识别/对账多路径调用),reader 带副作用点击违反
   观测层纯读约定;且 overlay 属于 battle_loop 已处理的 UI 态,reader 内
   重复处理双源。拒绝。
4. **rect 动态定位(overlay 开时重算 slot rect)** —— 每帧动态定位成本高、
   且 overlay 下立绘被部分遮挡,SIFT 未必匹配;为罕见帧引入新定位机制,
   复杂度不成比例。拒绝。

## Decision

- `cw_obs_core` 新增 `prep_areas_unobstructed`(best-effort,异常 → True 回落
  旧判定)+ `_KNOWN_OVERLAYS` 注册表:
  - 「金币说明面板」:锚 = screen_info 新建档「标识-金币说明」(证据帧
    034f8ef3 离线 OCR 定位标题 x1013-1149/y383-421,pc_rect (1000,370,1165,435),
    命中 conf 0.997);覆盖带 = 同帧实测内容范围取整 `Rect(990,360,1480,1000)`
    (收入明细+连胜规则表,盖备战栏 6-9)。
  - 「阿哈大悦装备选择」:锚 = 既有「标识-简易装备」(battle_loop 0g);范围
    未采样 → 保守全屏带(None)。
- summon 钩子:`is_prep_like_frame` 通过后、存 sentinel/停机前,对候选 slot
  rect 调 `prep_areas_unobstructed`,被遮即 break 跳过本帧(不 flag 不停机),
  等下一帧 overlay 关了再判。
- bookcard 钩子:同一函数加固。它本身极性免疫(见下),但停机后的「点开启」
  动作在 overlay 下同样落空 → 停机前确认书册卡槽 rect 未被遮。
- layout 钩子:**免疫,不接守卫**——触发条件 = effective_back_slots(cap) 无档,
  判据来自 deploy_cap(舞台上方中央 X/Y OCR 指示),不裁备战 slot rect;X/Y
  指示在顶部中央不被右侧 overlay 遮 → 无假阳性路径(代码注释记录核查依据)。

## Consequences

- overlay 开着时的「占用未识别」帧不再停机;overlay 被 battle_loop 消费关闭后
  下一帧正常判定 —— 真未知物品的发现延迟至多一个 overlay 周期。
- 区域语义:覆盖带外的 rect 不受锚命中影响(slot1-5 不被金币说明面板误拦),
  比首版「关键词在场全跳」更精确。
- 「金币说明」已建档为 screen_info area(此前 gate PROFILE_POPUP 注明的
  「货币战争-金币说明弹窗」独立屏建档仍待建,不阻塞本守卫)。
- 后续发现新遮挡 overlay:采样锚 + 覆盖带 → `_KNOWN_OVERLAYS` 追加一行,
  全部接线钩子自动受益。
- 锁测试 `test_cw_adr0263_overlay_guard.py`:函数层 4 条(被遮/带外/锚未命中/
  全屏带)+ 钩子层 2 条(overlay 开不停机 / 关正常停机)。

## Revision(2026-08-24,ADR-0269 合并退役)

`prep_areas_unobstructed` + `_KNOWN_OVERLAYS` 注册表**退役删除**:
summon/bookcard 钩子的 overlay 排除合并为——

- **帧态门升级为两段式**(ADR-0269):上层屏(选择伙伴/事件类/详情类等
  22 屏)在场 → 非 prep-like → 钩子跳过。原「阿哈大悦装备选择」全屏带锚
  随之退役:全屏 overlay 盖 id_mark → 备战屏不命中,两段式天然排除,
  无需锚。
- **金币说明保留锚判定作补充第三段**(`cw_obs_core.gold_info_overlay_open`):
  它是 C 类无档案 overlay(无独立 screen 档案,进不了 UPPER_SCREENS),
  两段式看不见 → 锚 OCR(标识-金币说明)命中即跳过。原「覆盖带与目标
  rect 相交」的区域语义随之简化为帧级锚判定(锚开 → 整帧跳过):带外
  slot1-5 也跳过一帧是可接受代价(下一帧 overlay 关闭即恢复),换实现
  单一(无带维护)。
- 锁测试改写:函数层 3 条(锚命中/未命中/area 缺失)+ 退役守卫断言
  + 钩子层 3 条(overlay 开不停机 / 关正常停机 / 上层屏门前置不停机)。
