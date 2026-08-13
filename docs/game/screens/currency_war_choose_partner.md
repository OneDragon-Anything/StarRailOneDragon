---
screen_name: 货币战争-选择伙伴
appears_in: [currency_war]
last_updated: 2026-08-13
source_image: screens/货币战争-选择伙伴/select_partner.webp
---

# 货币战争-选择伙伴(节点级伙伴选择 overlay)

## 何时出现 + 状态流转

对局内**位面推进中**随机出现的「选择伙伴」节点(非每轮必有;出现时机由肉鸽地图节点决定)。玩家从 1-N 个候选角色里**选 1 名**加入其流派羁绊 + 复制其首件装备效果,选完回备战。**两步确认流程**(实测 + handler `HandleSelectPartner`):

- **入口**:备战 → (地图节点为「选择伙伴」时)→ 本 overlay(叠在备战上,备战 id_mark 仍透出可见)。
- **step 1 选伙伴**:点候选立绘选中(选中态 = 「已选择」文字出现 + 立绘高亮边框)→ 点「确认选择」。
- **step 2 选强化目标**:step1 确认后 overlay 转为「请选择强化角色」(选我方哪名角色复制装备效果)→ 点中心立绘(我方角色 portrait,~960,300)→ 点「确认选择」→ overlay 关,回备战。
- **出口**:step2 确认 → overlay 消失 → 回备战(节点完成,进下回合)。

⚠️ **dispatch 时序坑(2026-08-13 实跑)**:本 overlay 可能在**备战 round-start 检测之后**才出现( round-start OCR 见干净备战 → Loop 走备战分支 → BattlePrepCycle → 出战 click 被 overlay 挡 → 出战 retry×3 失败停机)。Loop 0a 分支(`round_by_find_area('货币战争-选择伙伴','标识-选择伙伴')`)在 round-start 单次检测,overlay 后出则漏 → 需 BattlePrepCycle 出战前复查 overlay 或 Loop 出战失败后回检(待修)。

## 识别特征(稳定锚点)

- **标题「选择伙伴」**(画面正上方 top-center,pc_rect `[987,52,1125,99]`,id_mark `标识-选择伙伴`)—— overlay 独有,作 id_mark。
- 指令长句「选择1名「<阵营>」成员,加入该成员的流派羁绊,并复制其首件装备效果。」(中上 y~127,阵营名随节点变,如「列车同行」)。
- 底部「确认选择」按钮(pc_rect `[1423,561,1587,616]`)+「详情」(其左)。
- step2 标志:「请选择强化角色」(右下 ~1417,530)。
- ⚠️ overlay 叠在备战上,**备战 id_mark(备战标识-购买经验)仍可见** → analyze 可能仍匹配备战 is_precise;partner 靠 `标识-选择伙伴` area 显式检(非靠 is_precise)。

## 可交互元素

| 元素 | 位置(中心,1080p) | 说明 |
|---|---|---|
| 候选立绘(step1,N 个横排) | 立绘 = 流派 label 上方 ~60px(label y~362 → 立绘 y~302;x 随候选数分布 450-1550) | 点立绘**选中**(选中态 = 「已选择」文字 + 高亮边框)。候选 label 是**流派/role 名**(护盾/能量/仙舟/列车同行…),**非角色名** |
| 「详情」 | (~1031,445) 左下 | 看选中候选详情(未深探) |
| 「确认选择」(step1) | (~1441,582) 右下 pc_rect `[1423,561,1587,616]` | step1 选中伙伴后点 → 进 step2(未选中时灰) |
| 强化目标中心立绘(step2) | (~960,300) 中心 | step2「请选择强化角色」→ 点此选中我方角色 → 「已选择」 |
| 「确认选择」(step2) | (~1441,582) 同上 | step2 选中后点 → **关 overlay 回备战**(不可逆出口,节点完成) |

**选中态 = OCR「已选择」文字 + 视觉高亮边框**(双手段;handler 用 OCR「已选择」判)。

## automation 要读信息

- **候选流派 label**(step1):OCR 候选行(y~362,x 450-1550,2-4 字流派名)→ `decide_partner` 候选。⚠️ **候选无角色名**(只有流派 label)→ `decide_partner` 多 idx0 兜底;真按角色选需 **SIFT 立绘识别**(同 `read_bench_chars`,CW 立绘库)喂真角色名 = 后续子项。
- **目标阵营**(指令句「选择1名「<阵营>」成员」的阵营名)→ 限定候选范围(本节点只选该阵营)。
- step2 强化目标:当前 naive 点中心立绘(策略化选强化谁待补,按 comp 角色定位)。

## 识别快照

`analyze_screen`(截图 `screenshot_20260813_180537_548643.png`,step2 态 —— 护盾已选中 + 请选择强化角色):
- 匹配画面:**货币战争-备战 `is_precise=True`**(overlay 叠备战,备战 id_mark 透出;partner 靠 `标识-选择伙伴` area 显式检,非 is_precise)。
- 全量 OCR(节选):`选择伙伴` / `选择1名「列车同行」成员，加入该成员的流派羁绊，并复制其首件装备效果。` / `护盾`(选中伙伴 label)/ `详情` / `请选择强化角色`(step2)/ `确认选择` / 透出的备战元素(`备战阶段`/`出战`/`购买经验`)。
- 视觉大模型(智谱 GLM-4.5V):overlay 标题「选择伙伴」top-center;1 候选立绘(护盾,选中态发光边框);底部「详情」+「确认选择」(灰,step2 未选强化目标);备战出战/bench 透出。

## 备注 / 待查

- **screen_info 现状**:`currency_war_partner.yml` —— `标识-选择伙伴`(**id_mark=false**)+ `按钮-确认选择`。handler `HandleSelectPartner` + `decide_partner` 已接(候选 OCR + idx0 兜底)。
- **id_mark=false 原因(overlay-on-parent 撞车)**:partner overlay 叠在备战上,fixture 里**备战 id_mark(备战标识-购买经验)也可见** → 设 partner id_mark=true 会撞车(id_mark 测试:partner fixture 同时命中备战 id_mark)。且 analyze 时备战 is_precise 会 dominate(partner 永不被 is_precise 选中)→ id_mark=true 对检测无用。**正解 = id_mark=false + loop 用 `round_by_find_area('货币战争-选择伙伴','标识-选择伙伴')` 显式 area dispatch**(loop 0a 已这样)。同类 overlay-on-parent(投资策略/祈愿试炼)也 id_mark=false。
- **候选无角色名**:流派 label(护盾/能量)非角色名 → `decide_partner` 无法按 `target_comp.core_chars` 选(多 idx0);真接决策需 SIFT 立绘识别(后续子项,候选位置视觉不稳需 CV 卡框/多样本定网格)。
- **dispatch 时序坑**(见「何时出现」):overlay 后出 round-start 检测漏 → 出战 retry 失败停机。修法待定(BattlePrepCycle 出战前复查 overlay / Loop 出战失败回检)。
- **step2 用巨星 screen_info 的 area**:handler step2 检 `货币战争-巨星强化` 的 `按钮-请选择强化角色`(partner step2 共用此 prompt)—— 跨屏 area 引用,fragile,待 partner 自建 step2 area。
- fixture 已归档 `sr-od-test/screens/货币战争-选择伙伴/select_partner.webp`(2026-08-13,step2 态)。
