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
- 关联 [bag](../screens/bag.md) 遗器分类。

## 备注 / 待查

- **待实拍 + vision**:遗器分解 + 快速选择过滤态实拍归档 + vision(遗器图标 / 等级 / 销毁按钮)。
- **过滤配置**:`relic_salvage_config.salvage_level`(用户配销毁哪个等级以下),bot 按配销毁。
- **销毁不可逆**:遗器分解后消失(换残骸),bot 按过滤谨慎销毁。
- **关联 bag**:遗器分解是 bag 遗器分类(bag_relic)的子流程。
