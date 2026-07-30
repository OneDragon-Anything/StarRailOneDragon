---
screen_name: 任务
screen_id: mission
appears_in: [任务追踪]
last_updated: 2026-07-29
source_image: screens/任务/全部任务.webp
pc_alt: false
---

# 任务(mission)

任务追踪界面。查看当前任务列表(主线/冒险/活动)、追踪/停止追踪任务、「前往」传送去任务地点。**不锁光标**(`pc_alt=false`)。

## 何时出现 + 状态流转

- **入口**:菜单点「任务」(phone_menu_const.MISSIONS)→ 任务画面。
- **出口**(动作 → 下一态):
  - 点「前往」→ 传送(加载)→ 落目标地图大世界(任务地点)。
  - 点「停止追踪」/「开始追踪」→ 切换追踪态(停留任务画面)。
  - 右上角返回 / ESC → 回菜单。

## 识别特征(稳定锚点)

- **按钮-停止追踪 / 按钮-开始追踪**(screen_info `mission` 仅这 2 area,pc_rect 见 yml):追踪操作按钮,是当前追踪态的判据(有「停止追踪」= 正在追踪该任务)。
- **「全部任务」标题**(screen_info `bag_mission`「二级标题-任务」,text "全部任务",`id_mark`):任务列表主态锚点(analyze 命中 conf 0.999)。
- `pc_alt=false`。
- 易变:任务名、任务描述、奖励(金币数)、地图名——动态,勿当特征。

## 可交互元素

| 元素 | 来源 | 说明 |
|---|---|---|
| 任务列表(分类+项) | OCR(动态) | 左侧 冒险任务/活动任务 等分类 + 任务项;选中项右侧显示详情 |
| 前往 | OCR(右下) | 传送去任务地点 |
| 停止追踪 / 开始追踪 | screen_info area | 切换任务追踪 |
| 奖励预览 | OCR(右侧) | 任务奖励(如金币 5000) |

## 识别快照(analyze_screen 实测,2026-07-28)

- 匹配画面:`任务`(mission)`is_precise=false` + `背包-任务`(bag_mission)`is_precise=false`(两候选均模糊)。
- 命中 area:二级标题-任务(text "全部任务" conf 0.999,bag_mission)、按钮-停止追踪(text "停止追踪" conf 0.959,mission)。
- OCR(节选):全部任务 / 冒险任务;任务项 匹诺康尼-飞翔时针号/谁动了我的经费/反贪「砖」家/骇入「信息安全科」/⛄表演赛！桂乃芬/雅利洛-VI-I旧武器试验场;奖励预览 5000;停止追踪 / 前往。

## 备注 / 待查

- **`mission` 与 `bag_mission`(背包-任务)关系待确认**:任务画面同时模糊命中两个 screen——`mission`(追踪按钮 2 area) + `bag_mission`(全部任务标题)。两者是同画面的不同 area 集、还是主态/子态,待读代码 + 实拍确认(可能合并建档或独立)。当前任务画面识别 `is_precise=false`(无强 id_mark),属 screen_info 可加强点(加精准锚点)。
- **前往=传送**:「前往」按钮触发传送(加载→大世界),非简单切画面;op 链待读代码补。
- **fixture 已归档(2026-07-29)**:`screens/任务/全部任务.webp`(自主采,菜单→任务);任务分类图标 / 追踪状态标记 / 奖励图标细节以 OCR + screen_info 为准。
