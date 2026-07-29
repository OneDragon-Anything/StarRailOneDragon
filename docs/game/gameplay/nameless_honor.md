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
- `_click_tab_1` / `_click_tab_2`(切 tab:tab1=任务、tab2=奖励,`phone_menu_utils.get_nameless_honor_tab_pos`)。
- `_claim_task`(任务 tab 一键领取,`无名勋礼-任务-一键领取` area)。
- `_claim_reward`(奖励 tab 一键领取,`无名勋礼-奖励-一键领取` area)→ `_check_screen_after_reward`。
- `back_at_first` / `back_at_last`:首尾返回。

## 画面(phone_menu 无名勋礼子态)

无独立 screen —— 委托 UI 在 phone_menu 弹窗态(见 [phone_menu](../screens/phone_menu.md)):
- `无名勋礼-开启无名勋礼`(新版本开启提示,text)。
- `无名勋礼-任务-一键领取`(任务 tab 一键领取)。
- `无名勋礼-奖励-一键领取`(奖励 tab 一键领取)。
- `无名勋礼-奖励-取消`(领取弹窗取消)。
- `无名勋礼-点击空白处关闭`(关闭弹窗)。
- tab1/2 切换(`get_nameless_honor_tab_pos`,模板匹配 tab)。

## 备注 / 待查

- **待实拍画面 + vision**:无名勋礼任务 / 奖励 tab + 一键领取态实拍归档 + vision(勋礼等级 / 任务列表 / 奖励图标 / tab)—— 有可领时实拍。
- **bot 仅领奖励**:`NamelessHonorApp` 一键领取任务 + 奖励(不完成任务本身,任务靠日常玩法推进)。
- **tab1 任务 / tab2 奖励**:tab 顺序待实拍确认(`get_nameless_honor_tab_pos(ctx, 1/2)`)。
- **付费档判断**:bot 领免费奖励(付费档需用户购买,bot 不处理付费)。

## 参考来源

- [3.2 无名勋礼更新(官方)](https://sr.mihoyo.com/news/155368)
- [3.6 无名勋礼更新(官方)](https://sr.mihoyo.com/news/159571)
- [B站WIKI 无名勋礼任务详情](https://wiki.biligame.com/sr/%E6%97%A0%E5%90%8D%E5%8B%8B%E7%A4%BC)
- [3DM 无名勋礼奖励统计](https://ol.3dmgame.com/gl/235965.html)
