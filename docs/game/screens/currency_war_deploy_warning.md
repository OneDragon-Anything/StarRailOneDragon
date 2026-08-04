---
screen_name: 货币战争-未达上限警告
appears_in: [currency_war]
last_updated: 2026-08-04
source_image: screens/货币战争-未达上限警告/default.webp
---

# 货币战争-未达上限警告(出战确认弹窗)

备战点「出战」时若可出战角色人数未达上限(等级封顶 < 上阵位 / bench 没填满)→ 弹此确认。
勾「本局不再提示」+ 确认 → 解除阻塞进战斗。

## 何时出现 + 状态流转

- **入口**:备战点「出战」且人数未满 → 弹窗(遮罩在备战之上)。
- **出口**:勾「本局不再提示」+「确认」→ 进自动战斗;或「取消」回备战补人。
- 与「备战席已满」(bench-full,卖/升级解)不同:本弹窗是**上阵位未填满**(等级低 → 上阵数少 → 角色不够填满舞台)。

## 识别特征(稳定锚点)

- 独有文字:「可出战角色人数未达上限，是否确认出战？」(id_mark)。标题「提示」。
- 与通用对话框(也有"提示"+"确认")区别:本弹窗有这句独有的未达上限正文 + 「本局不再提示」勾选框。

## 可交互元素

- 「本局不再提示」勾选框:screen_info ``勾选-本局不再提示`` center ≈ (912,589)。勾上后本局不再弹。
- 「确认」按钮:screen_info ``按钮-确认`` center ≈ (1159,653)。
- 「取消」按钮:≈ (744,654)。

> screen_info ``currency_war_deploy_not_full``:``标识-未达上限警告``(id_mark)+ ``勾选-本局不再提示`` + ``按钮-确认``。op ``handle_deploy_not_full`` 经 ``cw_observation.area_center`` 读(screen_info 缺失才用兜底常量)。

## 识别快照

- 匹配画面:`货币战争-未达上限警告` **精准命中**(id_mark ``标识-未达上限警告`` conf 0.996)。
- 关键 OCR:「提示」(922,393)、「可出战角色人数未达上限，是否确认出战？」(731,497)、「本局不再提示」(912,589)、「取消」(743,655)、「确认」(1159,653)。

## 备注

- **bug#1 mitigation**:关键 click 前 mouse_move(零移动不被判 drag,否则弹窗不消 stall)。
- 归档:`screens/货币战争-未达上限警告/default.webp`。
- screen_info:`currency_war_deploy_not_full`(task#20)。
- ⚠️ **图源注意**:.debug/images/`cw_megastar_*.png` **文件名误标**,实为本弹窗(非巨星屏)。真正巨星屏未干净捕获(见 `.debug/temp/currency_war/screen_coords_inventory.md`)。
