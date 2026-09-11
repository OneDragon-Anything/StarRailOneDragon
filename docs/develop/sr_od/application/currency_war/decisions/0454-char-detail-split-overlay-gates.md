# ADR-0454: 角色详情档按形态拆分 + UPPER_SCREENS 扩容(浮窗/提示门漏)

- **Status**: accepted
- **Date**: 2026-08-29

## Context

「货币战争-备战-角色详情」画面档(currency_war_battle_prep_equip_detail.yml)把
三种 overlay 形态捏在一档:角色详情大面板 / 装备详情浮窗(点右侧装备弹,可合成列表)/
角色信息提示(悬停角色 tooltip,携带装备)。档内唯一形态性 id_mark 锚「按钮-装备推荐」
只属大面板;离线复跑生产两段式门(`is_prep_like_frame`,ADR-0269)实证:
装备详情浮窗与角色信息提示的全部仓内真值帧(equip_detail_roller /
equip_detail_synth_target / char_detail)锚 OCR 全空 → 判不出角色详情 →
回落备战判定,而备战 id_mark(购买经验等)在浮窗帧全可见 → **放行为备战帧**
(与 ADR-0269 记录的局72 伙伴误拖同型门漏;面板遮挡右列时备战 readers/钩子照跑)。

约束:大面板形态的既有真值帧(信息tab 等 4 帧)对现锚全命中,锚本身对大面板是好的;
浮窗/提示两形态无「装备推荐」可验,不能把大面板锚硬凑到它们身上。

## Considered Options

1. **按真值形态拆档 + UPPER_SCREENS 扩容(采纳)** —— 大面板保留原档原锚;
   新建 货币战争-备战-装备详情浮窗(锚 标识-可合成列表,真值帧实测 rect
   1480,290,1765,365)与 货币战争-备战-角色信息提示(锚 标识-携带装备,真值帧实测
   rect 1395,615,1700,700),两屏名进 `UPPER_SCREENS`。
2. **原档换锚(拒绝)** —— 任何单锚都无法同时覆盖三形态(浮窗/提示帧无装备推荐,
   大面板帧无可合成列表);换锚会废掉大面板 4 张已验真值帧。
3. **C 类锚 OCR 第三段排除(拒绝)** —— gold_info_overlay_open 手法适用于无档案
   overlay;本两形态已按真值帧成功建独立档,走 UPPER_SCREENS 正规通道,不另立第三段。
4. **不改,靠 ops 层 ESC 兜底(拒绝)** —— battle_loop/prep_actions 已有
   「可合成列表/角色详情」OCR ESC 兜底,但钩子帧态门在 ops 之前,兜底不拦误停/误采。

## Decision

- 新建 `currency_war_battle_prep_equip_float.yml`(货币战争-备战-装备详情浮窗)与
  `currency_war_battle_prep_char_tooltip.yml`(货币战争-备战-角色信息提示),
  各一 id_mark 锚(rect 由真值帧裁片实测);原档不动。
- `cw_obs_core.UPPER_SCREENS` 扩容 +2(ADR-0269 同手法逐屏判定)。
- 三张真值帧 fixture 从 `screens/货币战争-备战/` 迁各自 screen 目录(错档归位);
  引用它们的测试路径同步。
- id_mark 测试新增 `_ALLOWED_DUAL_HIT` 白名单:三帧上备战 id_mark 全可见属画面事实
  (小浮窗不遮父屏锚),上层排除由本门负责,不经 screen 匹配竞争。

## Consequences

- 三形态 overlay 帧不再被判 prep-like:钩子误停/误采与备战 readers 误跑在判定层根治;
  大面板覆盖不回归(锁测试 test_cw_w559_overlay_gates)。
- 「带装备推荐按钮的**未持装备**角色详情大面板」若与在库真值帧渲染不同,现锚覆盖面
  以在库 4 帧为准;新形态真值帧出现时按本 ADR 手法扩档,不预造锚。
- 消费方 cw_identity_obs 的「按钮-装备推荐」面板守卫读原档 area,不受拆分影响。
