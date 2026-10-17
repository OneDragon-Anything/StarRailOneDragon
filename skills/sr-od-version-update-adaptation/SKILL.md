---
name: sr-od-version-update-adaptation
description: 游戏版本更新后,要给本项目(星穹铁道一条龙)做适配跟进时用——清点新版本内容并逐项适配,已建档适配项见路由表(当前:新角色数据录入)。凡是「新版本出了要跟」「这版本有什么要适配」「新角色出了录一下数据」都用,即使没明说跟哪些。英文:game version update adaptation, patch follow-up, new character data entry。
---

# 游戏版本更新适配

游戏出新版本后,把本项目适配跟上的总流程。**没做完下面 5 步不算完成。**

## 总流程(必做 checklist)

1. ☐ 确认游戏客户端已是新版本且能进大世界——判据:游戏窗口有效、能截到画面(项目 MCP 的 check_game_window / analyze_screen)。已更到新版本则直接过;没更按 od-mihoyo-launcher 更新;客户端本身有问题先修客户端,别开始适配【必做】
2. ☐ 清点本版本新内容,列适配项清单——来源:官方版本公告、官方维基(接口打法见 sr-od-dev-official-api)。清点维度逐项列:新角色、新地图区域、新玩法、既有玩法机制改动。与用户对齐本次跟哪些(用户已明示范围则直接用)【必做】
3. ☐ 逐项适配——已建档项按「适配项路由」进对应方法文档;未建档项按「未建档适配项」先补档再实施【必做】
4. ☐ 汇总验证——判据:每个改过的 .py 过 ruff check(只对本文件);测试影响面在 sr-od-test 里搜改动的常量名 / 文件名,有命中就跑、无命中记「无受影响测试」;本机游戏可登录时实机冒烟一轮受影响玩法【必做】
5. ☐ 按适配项分阶段提交,git add 逐文件点名【必做】

## 适配项路由

| 适配项 | 状态 | 方法 |
|---|---|---|
| 新角色数据录入 | 已建档 | `references/character-data-entry.md` |

**未建档适配项**(新地图、新玩法、新系统、机制改动等任何不在表里的项)按此流程补档,禁凭猜直接改:

1. 调研影响面:在项目内搜消费该内容的模块(配置常量、识别建档 screen_info、application / operation);
2. 与用户确认跟与不跟、跟的范围;
3. 把适配方法写成 `references/<主题>.md`(结构对齐 character-data-entry.md:checklist 带判据 + 分节方法),登记进上面的路由表;
4. 再实施。

## 边界

- 本 skill 只管「版本更新后跟什么、怎么跟」;单个 op / app 的开发与调试纪律归 od-dev-write-operation / od-dev-write-application,画面没建档先走 od-dev-screen-onboarding。
- 货币战争玩法内的单位(牌桌角色、装备等)不是本体角色,数据维护归 sr-od-currency-war-dev。
