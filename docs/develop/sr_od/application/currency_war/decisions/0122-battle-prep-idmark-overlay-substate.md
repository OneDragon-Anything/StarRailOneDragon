# 0122 · 备战 id_mark + overlay/子态区分(前台区域被盖;子态独立屏)

- **Status**: accepted
- **日期**: 2026-08-13

## Context

备战(`货币战争-备战`)id_mark 旧只有 `购买经验`(底部,稳定)。partner/wish/megastar 这些**中心 overlay**叠在备战上时,**底部购买经验没被盖、透出来** → overlay 帧上备战的 id_mark 也全命中 → 备战也 `is_precise` → 与 overlay 撞车(两画面都 is_precise,bot 可能误识别)。

旧解法:overlay `id_mark=false` + id_mark 测试加"overlay-on-parent 豁免"(跳过这类碰撞)。**问题:没真正区分**(测试绿了但备战与 overlay 仍互相命中)。

## Decision Drivers

- 真正区分备战与 overlay(非豁免/跳过);
- id_mark 组合区分度(元素越多越不易误命中);
- 子态各找自己的 id_mark(父屏不靠削弱自己迁就子态)。

## Considered Options

1. **overlay id_mark=false + 测试豁免**(旧):否决 —— 没真正区分,撞车仍在,豁免是绕开问题。
2. **overlay 只用单标题 id_mark**:否决 —— `购买经验 + 标题`组合区分度更高(用户定,2026-08-13)。
3. **备战加"被 overlay 盖住的稳定元素"当 id_mark**(采纳):备战 id_mark 含一个 overlay 会盖住的稳定元素 → overlay 帧备战缺它 → 不 is_precise。

> 关键认知(用户澄清):id_mark"稳定"= 每次进该画面(不含子态)稳定出现 + 内容不变(非角色名/动态数值),**与"是否被子态覆盖"无关** —— 会被子态盖住的稳定元素也是合格 id_mark,且正是区分 overlay 子态的关键。详见 skill 反馈。

## Decision

- **备战 id_mark = `购买经验` + `前台区域` + `后台区域`**
  - 前台区域 = 棋盘前排标签(y~290,中心),被 partner/wish/megastar 这些**中心 overlay 盖住** → overlay 帧备战缺前台区域 → 备战不是 is_precise。
  - 后台区域 = 棋盘后排标签(y~564,overlay 盖不到,透出)。
- **overlay(partner/wish/megastar)id_mark = `购买经验` + 自己标题**(组合,两个都中才算精准匹配)。
- **备战-开商店**:独立子态屏,id_mark = `购买经验` + `收起`(开商店时按钮显示"收起"非"商店")。开商店也盖前台区域 → 干净备战(shop closed)才 is_precise。
- **备战-装备详情**:独立子态屏,**无 id_mark**(装备详情面板盖住后台区域 → 无法用备战 id_mark;按 skill 子态无可见独有锚可不设 id_mark,test 自动 skip,运行时靠 context/非 id_mark area 认)。

**效果**:overlay 帧备战缺前台区域 → 不是 is_precise → 两画面各只一个 is_precise,**不撞车,无需测试豁免**。删了 id_mark 测试的 overlay-on-parent 豁免。2026-08-13 测试 + live 双确认(live partner 帧:only 选择伙伴 is_precise,备战不在)。

## Consequences

- 备战 `is_precise` 只在干净备战(无 overlay / 非开商店 / 非装备详情面板)。CW bot 认备战靠查 area(`round_by_find_area` 购买经验/出战/商店)非 is_precise → 备战在开商店/装备详情时仍可正常工作(只是 not is_precise,不影响 bot)。
- **crop-OCR 坑**:`find_area_in_screen(crop_first=True)` 裁到 pc_rect 再 OCR,**小/紧/背景杂的裁剪文字检测器漏检**(全屏 OCR 能识别的,裁小框后丢字)。前台区域紧框 `[900,283,1030,325]` 在多张备战 fixture crop-OCR 漏 → 放宽 `[850,275,1070,340]` 给上下文才稳定。**id_mark pc_rect 须跨全部 fixture 验真阳性**(多样本)。
- 装备详情加 id_mark:待验证详情面板位置一致性(面板是固定右侧 UI,很可能一致;一致则可加 `装备推荐`/`合成公式` 锚)→ 当前无 id_mark(子态可用)。
- skill 反馈已写(`od-dev-screen-onboarding`:id_mark"稳定"语义 + overlay/父双向配合 + crop-OCR 坑)。
