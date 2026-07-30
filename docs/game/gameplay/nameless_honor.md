---
gameplay_name: 无名勋礼(战令/大月卡)
app_id: nameless_honor
last_updated: 2026-07-29
source: WebSearch 攻略 + `application/nameless_honor/` 代码 + phone_menu 无名勋礼子态 area
involves_screens: [菜单]
---

# 无名勋礼(nameless_honor)

赛季通行证(玩家称「大月卡 / 战令」),每版本一期。完成日常 / 周常 / 版本任务获「无名客的经验」升勋礼等级,解锁奖励。满级 70。解锁:开拓等级 13+。画面是 **phone_menu 子态**(无独立 screen)。

## 玩法机制(攻略)

- **赛季通行证**:每版本一期,任务(日常 / 周常 / 版本)升勋礼等级(满 70)。
- **任务类型**:日常 / 周常 / 版本任务(如虚构叙事 6 星 / 末日幻影 4 次 / 跃迁 40 次 等)。
- **奖励档位**:
  - **免费勋礼**:星轨通票 / 自塑尘脂 / 命运的足迹(基础)。
  - **无名客的荣勋**(付费):立即星琼×680 + 光锥碎忆 / 星轨专票×4 / 自选 4 星光锥 / 变量骰子 / 遂愿尘脂 / 自塑尘脂 / 遗器残骸 / 通用命途材料。
  - **无名客的奖章**(更高档):立即 +10 级 + 更多专属。
- 每版本奖励细节略调,以官方公告为准。

## bot 流程(`application/nameless_honor`)

`NamelessHonorApp` 领奖励流程:
- `open_menu`(开菜单 → 点「无名勋礼」)→ `_click_honor`(进无名勋礼)。
- `_click_tab_2`(切到**任务** tab)→ `_claim_task`(任务 tab 一键领取,`无名勋礼-任务-一键领取` area)。
- `_click_tab_1`(切到**奖励** tab)→ `_claim_reward`(奖励 tab 一键领取,`无名勋礼-奖励-一键领取` area)→ `_check_screen_after_reward`。
- tab 切换用 `phone_menu_utils.get_nameless_honor_tab_pos`(`nameless_honor_1`=奖励、`nameless_honor_2`=任务 模板)。
- `back_at_first` / `back_at_last`:首尾返回。

## 画面(phone_menu 无名勋礼子态)

无独立 screen —— 委托 UI 在 phone_menu 弹窗态(见 [phone_menu](../screens/phone_menu.md)):
- `无名勋礼-开启无名勋礼`(新版本开启提示,text)。
- `无名勋礼-任务-一键领取`(任务 tab 一键领取)。
- `无名勋礼-奖励-一键领取`(奖励 tab 一键领取)。
- `无名勋礼-奖励-取消`(领取弹窗取消)。
- `无名勋礼-点击空白处关闭`(关闭弹窗)。
- 3 个 tab(顶部横向,`NAMELESS_HONOR_TAB_PART=Rect(810,30,1110,100)`):**奖励**(左,圆心~863)/**任务**(中,~959)/**星海珍藏**(右,~1055),等距 ~96px、y~64。选中态 tab 背景为白色圆形(r~30,可用 CV `HoughCircles` 定位)。
- tab 切换 `get_nameless_honor_tab_pos`(`nameless_honor_1`=奖励、`nameless_honor_2`=任务、`nameless_honor_3`=星海珍藏 模板,未选中态图标 + Otsu 形状 mask)。

## 备注 / 待查

- **奖励 tab 已采**:`screens/菜单/无名勋礼-奖励.webp`(无红点态);**任务 tab + 一键领取 / 红点可领态**待红点时实拍。
- **测试**:`sr-od-test/test/sr_od/application/nameless_honor/test_nameless_honor_app.py` —— app 引用的 `('菜单', area)` 契约 + 奖励 tab 的 `in_secondary_ui('无名勋礼')` 判定;tab 切换 / 一键领取(消耗 / 红点)不 mock。
- **bot 仅领奖励**:`NamelessHonorApp` 一键领取任务 + 奖励(不完成任务本身,任务靠日常玩法推进)。
- **tab1=奖励、tab2=任务**:`nameless_honor_1` 模板=奖励 tab、`nameless_honor_2`=任务 tab(已实拍确认)。代码 `_click_tab_2` 切任务、`_click_tab_1` 切奖励。
- **星海珍藏(tab3)**:版本更新后新增的第三个 tab(满级光锥自选奖励),`nameless_honor_3` 模板已加(备用);`NamelessHonorApp` 流程只切奖励/任务,暂不涉及星海珍藏。
- **tab 模板**:`nameless_honor_1/2` 为**未选中态**图标 + Otsu 形状 mask(match 未选中 tab 去点击切换);选中态 tab 有白色圆形背景、match 不到未选中模板属正常。`NAMELESS_HONOR_TAB_PART` 已覆盖 3 tab,无需改。
- **fixture**:`screens/菜单/无名勋礼-奖励.webp`(奖励 tab,等级轨 19→30,本周经验 3500/8000,0/800,付费轨「无名客的荣勋」未解锁,无红点)。
- **付费档判断**:bot 领免费奖励(付费档需用户购买,bot 不处理付费)。

## 参考来源

- [3.2 无名勋礼更新(官方)](https://sr.mihoyo.com/news/155368)
- [3.6 无名勋礼更新(官方)](https://sr.mihoyo.com/news/159571)
- [B站WIKI 无名勋礼任务详情](https://wiki.biligame.com/sr/%E6%97%A0%E5%90%8D%E5%8B%8B%E7%A4%BC)
- [3DM 无名勋礼奖励统计](https://ol.3dmgame.com/gl/235965.html)
