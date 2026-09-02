---
gameplay_name: 无名勋礼(战令/大月卡)
app_id: nameless_honor
last_updated: 2026-09-02
source: WebSearch 攻略 + `application/nameless_honor/` 代码 + phone_menu 无名勋礼子态 area
involves_screens: [菜单, 无名勋礼-购买推广页, 无名勋礼-等级加速弹窗, 无名勋礼]
---

# 无名勋礼(nameless_honor)

赛季通行证(玩家称「大月卡 / 战令」),每版本一期。完成日常 / 周常 / 版本任务获「无名客的经验」升勋礼等级,解锁奖励。满级 70。解锁:开拓等级 13+。画面为 **3 个独立屏**(主面板 + 购买推广页 + 等级加速弹窗,2026-08-29 建档,见下「画面」节)。

## 版本周期首进推广页 [口述+实机实证]

- **机制**:2026-08-26 版本起,**版本周期内第一次**进无名勋礼,先落「[无名勋礼-购买推广页](../screens/无名勋礼-购买推广页.md)」(整屏广告)而非主面板(用户口述,最高权威;2026-08-27 编排者实机走通退出链)。
- **付费语义(用户裁决)**:推广页点「开启无名勋礼」是查看/继续语义,**不会付费**。
- **退出链**:推广页 → 点开启 →「无名勋礼-等级加速弹窗」(点弹窗内「点击空白处关闭」提示位;点外部无效)→ 无名勋礼主面板 → 右上角关闭 → 菜单页。`BackToNormalWorldPlus` 已按此建退出分支(W293)。

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
- **领取后的版本说明弹窗** [口述+实机实证]:点「一键领取」成功后可能弹「无名勋礼等级加速」弹窗(同上节弹窗,关闭手势=点弹窗内「点击空白处关闭」提示位;`_check_screen_after_reward` 已建候选,run 48「未知画面状态」失败实证后补)。

## 画面(独立屏 ×3,2026-08-29 建档)

- **无名勋礼**(主面板):`标识-无名勋礼`(id_mark)/tab-奖励/任务/星海珍藏/按钮-任务-一键领取/按钮-奖励-一键领取/按钮-点击空白处关闭/按钮-关闭/按钮-开启无名勋礼。详见 [screens/无名勋礼](../screens/无名勋礼.md)。
- **无名勋礼-购买推广页**(版本周期首进整屏广告):双 id_mark(按钮-开启无名勋礼 + 标识-消费提示)。详见 [screens/无名勋礼-购买推广页](../screens/无名勋礼-购买推广页.md)。
- **无名勋礼-等级加速弹窗**(一键领取后的说明弹窗):独立建档——关闭手势 = 点弹窗内「点击空白处关闭」提示位(≈737,与主屏领取弹窗的 ≈945 不同位)。详见 [screens/无名勋礼-等级加速弹窗](../screens/无名勋礼-等级加速弹窗.md)。
- **tab 切换**:`get_nameless_honor_tab_pos`(`nameless_honor_1`=奖励、`nameless_honor_2`=任务、`nameless_honor_3`=星海珍藏 模板,未选中态图标 + Otsu 形状 mask——选中态白色圆形背景 match 不到未选中模板属正常)。3 tab 顶部横向:奖励(左,~863)/任务(中,~959)/星海珍藏(右,~1055),等距 ~96px、y~64。
- **菜单层**:仅图标红点检测(`get_phone_menu_item_pos(NAMELESS_HONOR, alert=True)`)。

## 备注 / 待查

- **奖励 tab 已采**:`screens/菜单/无名勋礼-奖励.webp`(无红点态);**任务 tab + 一键领取 / 红点可领态**待红点时实拍。
- **测试**:`sr-od-test/test/sr_od/application/nameless_honor/test_nameless_honor_app.py` —— app 引用的 `('菜单', area)` 契约 + 奖励 tab 的 `in_secondary_ui('无名勋礼')` 判定;tab 切换 / 一键领取(消耗 / 红点)不 mock。
- **bot 仅领奖励**:`NamelessHonorApp` 一键领取任务 + 奖励(不完成任务本身,任务靠日常玩法推进)。
- **tab1=奖励、tab2=任务**:`nameless_honor_1` 模板=奖励 tab、`nameless_honor_2`=任务 tab(已实拍确认)。代码 `_click_tab_2` 切任务、`_click_tab_1` 切奖励。
- **星海珍藏(tab3)**:版本更新后新增的第三个 tab(满级光锥自选奖励),`nameless_honor_3` 模板已加(备用);`NamelessHonorApp` 流程只切奖励/任务,暂不涉及星海珍藏。
- **tab 模板**:`nameless_honor_1/2` 为**未选中态**图标 + Otsu 形状 mask(match 未选中 tab 去点击切换);选中态 tab 有白色圆形背景、match 不到未选中模板属正常。`NAMELESS_HONOR_TAB_PART` 已覆盖 3 tab,无需改。
- **fixture**:`screens/无名勋礼/`(奖励.webp / 任务.webp / 无名勋礼-奖励.webp / 无名勋礼-任务.webp,2026-08-15 错档迁移后落位)。
- **付费档判断**:bot 领免费奖励(付费档需用户购买,bot 不处理付费)。

## 参考来源

- [3.2 无名勋礼更新(官方)](https://sr.mihoyo.com/news/155368)
- [3.6 无名勋礼更新(官方)](https://sr.mihoyo.com/news/159571)
- [B站WIKI 无名勋礼任务详情](https://wiki.biligame.com/sr/%E6%97%A0%E5%90%8D%E5%8B%8B%E7%A4%BC)
- [3DM 无名勋礼奖励统计](https://ol.3dmgame.com/gl/235965.html)
