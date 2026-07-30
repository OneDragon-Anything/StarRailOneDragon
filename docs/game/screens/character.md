---
screen_name: 角色
appears_in: [通用系统]
last_updated: 2026-07-29
source_image: screens/角色/详情.webp
pc_alt: false
---

# 角色(character)

角色详情界面。查看 / 管理角色(光锥 / 行迹 / 遗器 / 星魂 / 属性)。**不锁光标**(`pc_alt=false`)。通用系统,不必先搜玩法。

## 何时出现 + 状态流转

- **入口**:菜单点「角色」→ 角色列表 → 选角色 → 角色详情。
- **出口**(动作 → 下一态):
  - 点详情子栏 tab(详情 / 光锥 / 行迹 / 遗器 / 星魂 / 信息)→ 切详情子栏(停留角色详情)。
  - ESC / 返回 → 回角色列表 / 菜单。

## 识别特征(稳定锚点)

- **标题「角色详情」**(左上角,OCR 稳定):角色详情态锚点。次行 `<命途>/<角色名>LV.<等级>`(如「欢愉 / 银狼LV.999」)。
- `pc_alt=false`。
- 易变:角色名 / 命途 / 等级 / 属性数值 / 光锥遗器——动态,勿当特征。
- **无 screen_info 条目**(`screens=[]`)——靠 `common_screen_state.in_secondary_ui('角色详情')` 标题识别。

## 可交互元素

| 元素 | 来源 | 说明 |
|---|---|---|
| 详情子栏 tab | OCR(左侧) | 详情 / 光锥 / 行迹 / 遗器 / 星魂 / 信息 |
| 属性数值 | OCR(右侧) | 等级 / 生命值 / 攻击力 / 防御力 / 速度 / 暴击率 / 暴击伤害 |
| 角色攻略 | OCR(右上) | 跳转角色攻略 |
| 属性详情 | OCR(右下) | 详细属性面板 |

## 备注 / 待查

- **无 screen_info 条目**:角色详情未被 screen_info 收录(`screens=[]`)。识别靠 `in_secondary_ui('角色详情')` 标题(已 fixture 测试,见 `sr-od-test/test/sr_od/screens/test_shared_screen_fixtures.py`)。若 bot 要与角色详情交互(换光锥 / 遗器 等),需补 screen_info area。
- **fixture**:`screens/角色/详情.webp`(银狼 欢愉,等级 80/80,详情 tab)。
