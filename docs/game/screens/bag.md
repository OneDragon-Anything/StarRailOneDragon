---
screen_name: 背包
screen_id: bag
appears_in: [通用系统]
last_updated: 2026-07-29
source_image: .debug/sr_od_mcp/screenshot/screenshot_20260729_001432_772861.png（待归档 screens/背包/养成材料.webp）
pc_alt: false
multi_screens: [bag_consumable, bag_light_cone, bag_mission, bag_other_material, bag_pet, bag_relic, bag_relic_salvage, bag_relic_salvage_filter, bag_upgrade_material, bag_valuable]
---

# 背包(bag)

背包界面。**10 个分类 tab 共享同一画面**(每分类独立 screen_info,靠「一级标题-背包」+ 各「二级标题-XX」组合精准识别)。物品网格 + 详情 + 销毁。**不锁光标**(`pc_alt=false`)。通用系统,不必先搜玩法。

## 何时出现 + 状态流转

- **入口**:菜单点「背包」(phone_menu_const.INVENTORY)→ 背包(默认养成材料分类)。
- **出口**(动作 → 下一态):
  - 点分类 tab(左侧)→ 切分类(停留背包,二级标题变)。
  - 物品网格选物品 → 右侧详情(名/数量/描述/获得途径)。
  - 「销毁」→ 销毁弹窗(选数量 + 确认)→ bag_relic_salvage 态(遗器分解)。
  - 右上返回 / ESC → 回菜单。

## 识别特征(稳定锚点)

- **一级标题-背包**(text "背包",`id_mark`):所有分类态共有的画面锚点(analyze 命中 0.9999)。
- **二级标题-XX**(text,`id_mark`):各分类态的区分锚点(养成材料 / 消耗品 / 光锥 / 遗器 / …),组合「背包+XX」精准识别。
- `pc_alt=false`。
- 易变:物品数量、选中物品、稀有度。

## 可交互元素

| 元素 | 说明 |
|---|---|
| 分类 tab ×10(左侧) | 养成材料 / 消耗品 / 光锥 / 遗器 / 任务 / 其他材料 / 宠物 / 贵重 / 遗器分解 / 分解过滤(每 tab 一个 screen_info) |
| 物品网格 | 中央,图标 + 数量;选中物品有白边框;部分有稀有度星星(金/紫等) |
| 详情区(右侧) | 选中物品:名 / 数量(×N) / 描述 / 获得途径 |
| 默认(底部) | 排序按默认 |
| 销毁(底部) | 触发销毁 / 分解弹窗 |

## 10 分类 screen_info 概览

| screen_id | 二级标题 | 内容 |
|---|---|---|
| bag_upgrade_material | 养成材料 | 角色经验 / 突破材料(漫游指南 等) |
| bag_consumable | 消耗品 | 战斗消耗品(药 等) |
| bag_light_cone | 光锥 | 角色光锥 |
| bag_relic | 遗器 | 遗器 |
| bag_relic_salvage | 遗器分解 | 遗器销毁 / 分解 |
| bag_relic_salvage_filter | 遗器分解过滤 | 分解过滤设置 |
| bag_mission | 任务 | 任务道具 |
| bag_other_material | 其他材料 | 其他材料 |
| bag_pet | 宠物 | 宠物 |
| bag_valuable | 贵重 | 贵重品 |

## 识别快照(analyze_screen 实测,2026-07-29,养成材料态)

- 匹配画面:`背包-养成材料`(bag_upgrade_material)`is_precise=true`。
- 命中 area:一级标题-背包(text "背包" 0.9999)、二级标题-养成材料(text "养成材料" 0.9999)。
- OCR(节选):养成材料;物品 漫游指南 ×6900 / 角色经验材料;详情 角色的经验材料,获得 20000 经验;获得途径 拟造花萼【城郊雪原】/【流云渡】;默认 / 销毁。

## vision 补充(analyze 后多模态看图,OCR 盲区)
- **分类 tab ×10**(位置待实拍确认:两次 vision 对主分类 tab 位置描述矛盾——一次"左侧竖排"、一次"顶部横排",可能主分类 tab 与子分类标签如「角色经验材料/行迹材料」混淆):养成材料(当前选中)/ 消耗品 / 光锥 / 遗器 / 任务 / 其他材料 / 宠物 / 贵重 / 遗器分解 / 分解过滤。切 tab 实拍精确定位 + 各分类态归档待补。
- **物品网格**:4-6 行 × 8 列,每格图标 + 下方数量;部分有**稀有度星星**(金/紫/蓝 等)。
- **选中态**:当前选中物品(漫游指南)有**白色边框**。
- **底部按钮**:默认(排序)、销毁(垃圾桶图标)。
- **详情区**:物品大图标 + 描述文本 + 获得途径。

## 备注 / 待查
- **10 分类各 screen_info**:每分类独立 screen_info(靠一级+二级标题组合识别);各分类实拍归档待补(切 tab 实拍每分类态)。
- **遗器分解子流程**:bag_relic_salvage / bag_relic_salvage_filter 是销毁遗器的子流程(销毁弹窗 + 过滤),实拍待补。
- **vision 待补**:各分类 tab 实拍、销毁弹窗 vision。
