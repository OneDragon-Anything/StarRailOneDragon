---
gameplay_name: 遗器分解
app_id: relic_salvage
last_updated: 2026-07-29
source: `application/relic_salvage/` 代码(op_name「遗器分解」)+ screen_info `bag_relic_salvage`/`bag_relic_salvage_filter`
involves_screens: [背包-遗器分解, 背包-遗器分解-快速选择]
---

# 遗器分解(relic_salvage)

销毁低星 / 低价值遗器换材料(遗器残骸)。遗器管理。画面:**背包-遗器分解** + 快速选择过滤。

## 玩法机制

- **遗器分解**:销毁遗器(按等级 / 套装 / 强化等级过滤)→ 换遗器残骸(用于合成 / 强化)。
- 清背包(低星遗器),回收。
- 入口:背包 → 遗器 → 销毁。

## bot 流程(`application/relic_salvage`)

`RelicSalvageApp`(遗器分解):
- `goto_salvage`(前往「背包-遗器分解」画面)。
- `click_filter`(点「快速选择」过滤,`按钮-快速选择` area)。
- `choose_level`(选遗器等级,`背包-遗器分解-快速选择` + `relic_salvage_config.salvage_level`)。
- `choose_abandon`(选要销毁的遗器)→ 分解确认。

## 画面

- **背包-遗器分解**(`bag_relic_salvage` screen):遗器列表 + 快速选择 + 销毁。
- **背包-遗器分解-快速选择**(`bag_relic_salvage_filter` screen):过滤选项(等级 / 套装 / 强化)。
- **fixture**:`screens/背包-遗器分解/分解.webp`(遗器 2148/3000,可分解 632,智能弃置 / 快速选择 / 分解)+ `screens/背包-遗器分解-快速选择/快速选择.webp`(过滤弹窗:全选已弃置 / 2-5 星及以下 / 确认)。
- 关联 [bag](../screens/bag.md) 遗器分类。

## 备注 / 待查

- **已采(2026-07-29)**:背包-遗器分解 + 快速选择过滤态实拍归档(见上 fixture);screen_info area 经测试存在(按钮-快速选择 / 分解 / 分解确认 / 4 星 / 5 星 / 全选已弃置 / 确认)。
- **screen_info 引用已校验**:`背包-遗器分解` / `背包-遗器分解-快速选择` 的 area(按钮-快速选择 / 分解 / 分解确认 / 快速选择 / 4星及以下 / 5星及以下 / 全选已弃置 / 按钮-确认)经测试确认存在。
- **过滤配置**:`relic_salvage_config.salvage_level`(用户配销毁哪个等级以下,默认 4星及以下),bot 按配销毁。
- **销毁不可逆**:遗器分解后消失(换残骸),bot 按过滤谨慎销毁。
- **关联 bag**:遗器分解是 bag 遗器分类(bag_relic)的子流程。
- **测试**:`sr-od-test/test/sr_od/application/relic_salvage/test_relic_salvage_app.py` —— 枚举值 ↔ screen area + app 引用的 (screen, area) 契约校验。
