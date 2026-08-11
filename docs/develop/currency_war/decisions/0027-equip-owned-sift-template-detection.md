# 0027. 装备 owned icon 检测用 cw_equip SIFT 模板匹配(推翻 VLM 球体误判)

- **Status**: accepted
- **Date**: 2026-08-10
- **原编号**: D-27

## Context
①-a 装备源卡点。D-18/D-23/D-25/D-26 全程 VLM 把装备区 owned icon 误判"装饰球体",`equip_all`(x1800-1918 亮度检测)建在错认知上。用户质疑"cw_equip 模板库建了为何不用" → 用 cw_equip SIFT(154 icon)验证 → 命中 owned(拆装扳手/生命之花/轮滑鞋,inliers 11-32)→ 推翻 VLM 球体。D-28 crop 放大 tiebreaker 经 VLM ground truth 复核确认。

## Decision Drivers
- VLM 对小 icon(~60px 在 1920×1080 全图)不可信,全图送必丢细节 → 误判球体
- cw_equip 模板库(154 icon,harvest_equip_codex 采)已存在却未用
- 装备区 owned 是装备系统地基(equip_all 依赖)

## Considered Options
1. 修亮度检测(owned icon vs 空槽球体都亮,亮度不可分)
2. VLM 识别(小 icon 不可信,已证误判)
3. cw_equip SIFT 模板匹配(选中,inliers≥10,D-39 后调 7)

## Decision
owned icon 在装备区右列(x1800-1918;D-40 后扩 x1620-1918 多列),用 **cw_equip SIFT 模板匹配**检测(154 件,min_inliers≥7,D-39 validated)。equip_all 重建在地基上:`read_equips`(owned)→ 过滤工具类 → drag 穿戴类 → 验穿。owned 源 = 装备区(备战可见),非"装备库面板独立"(D-26 推测错)。

## Consequences
- 正向:装备检测有可靠地基;equip_all 可建。
- 负向:SIFT 也会假阳性(D-28/D-31/D-38/D-61)→ 需 crop VLM tiebreaker 交叉验证 + 布局守卫(D-62)。
- 边界:min_inliers 阈值需跨局面校(D-39→7);小 icon SIFT 有边界。
- 方法论:识别优先用已有模板库 SIFT + 小目标裁切放大(破 32×32 patch 天花板),全图送 VLM 必丢细节;单一方法都不可信,交叉验证治本。

## Links
- `· docs/develop/currency_war/strategy/07_equipment.md`
- 关联 D-NN:D-28(tiebreaker 确认)、D-39(阈值 7 validated)、D-40(多列扩区域)、D-49(已穿装备用 TM 非 SIFT)
