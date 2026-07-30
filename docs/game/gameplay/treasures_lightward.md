---
gameplay_name: 忘却之庭(逐光捡金)
app_id: treasures_lightward
last_updated: 2026-07-29
source: WebSearch 攻略 + screen_info `treasures_light`(32 area)+ `application/treasures_lightward/` 代码
involves_screens: [逐光捡金, 挑战副本, 战斗画面, 队伍]
---

# 忘却之庭 / 逐光捡金(treasures_lightward)

逐光捡金系列常驻高难挑战。三大玩法**交替轮换**(~42 天/期):**忘却之庭·混沌回忆**(FH) / **虚构叙事**(PC,Pure Fiction) / **末日幻影**(Apo)。每期最高星琼×800。进入后断开外界(不能换队伍 / 光锥 / 遗器)。`pc_alt=false`。

## 玩法机制(攻略)

- **三大玩法**(交替轮换,非同时开放):
  - **混沌回忆**(FH):上下半场,两支队伍分别挑战;回忆(15 关,一次性)+ 混沌回忆(10 层周期)。
  - **虚构叙事**(PC):积分挑战,两节点两队伍 + 增益(怪诞逸闻 / Cacophony)。
  - **末日幻影**(Apoca):高难挑战。
- **奖励**:回忆馈赠(一次性)/ 累计星数(每 3 星:星琼×200 + 信用×20000)/ 通过奖励(升级材料)/ 周期奖励(每期星琼×800)/ 流光余晖(信使兑换)。
- **刷新**:三大玩法 ~42 天(6 周)交替。
- 入口:与流光忆庭信使对话 / 指南传送。

## bot 流程(`application/treasures_lightward`)

`TreasuresLightwardApp` 调度(节点链):
- `_choose_forgotten_hall` / `_choose_pure_fiction`(选 FH / PC 分类)→ `_check_record_and_tp`(检测记录 + 传送)→ `_check_pf_new_start`(PC 新一期)。
- `_check_total_star`(检测总星数)→ 满星(`STATUS_FULL_STAR`)→ 完成;非满星 → `check_max_unlock`(找开始关卡)→ `challenge_mission`(挑战)→ 战斗后检测星 → 循环挑战下一关(满星循环)。
- op:`challenge_mission` / `check_max_unlock_mission` / `check_mission_star` / `check_star` / `choose_character` + `forgotten_hall/`(choose_mission / team / reward)+ `tl_battle` / `tl_wait`。
- `search_best_mission_team`(配队模块选最优队伍)。

## 画面(`treasures_light` screen_info「逐光捡金」,32 area,pc_alt=false)

- **分类**:TL_CATEGORY_FORGOTTEN_HALL(混沌回忆)、TL_CATEGORY_PURE_FICTION(虚构叙事)。
- **期次**:TL_SCHEDULE_1/2_TRANSPORT(期次传送)、TL_SCHEDULE_1/2_NAME(期次名)。
- **忘却之庭(FH)态**:FH_TITLE、FH_TOTAL_STAR(总星数)、FH_START_CHALLENGE(开始挑战)、FH_AFTER_BATTLE_SUCCESS_1/2 / FAIL(战斗后成功/失败)、FH_AFTER_BATTLE_BACK_BTN_1/2。
- **虚构叙事(PC)态**:PF_TITLE、PF_NEW_START(新一期)、PF_CACOPHONY_NODE_1/2(怪诞节点)、PF_CACOPHONY_OPT_1/2/3(增益选项)、PF_CACOPHONY_CONFIRM、PF_START_CHALLENGE、PF_AFTER_BATTLE_SUCCESS_1/2。
- **关联**:`challenge_mission`(挑战副本,支援角色替换图标等,见 [challenge_mission](../screens/challenge_mission.md) screen)。

## 备注 / 待查

- ⚠️ **app 代码未迁移 / 不可运行(2026-07-29 核实)**:`application/treasures_lightward/` **全部文件**(app / config / record / team_module / `op/*`)仍用旧 `sr.*` / `basic.*` 导入(如 `from sr.app.application_base import Application`、`from basic.i18_utils import gt`)。本仓库已重构为 `sr_od.*` —— `src/sr/`、`src/basic/` 不存在 → **无法导入**;且无 `_app_factory.py`、`list_applications` 不含本 app → **未注册、不运行**(sr_od 重构时漏迁移的死代码)。上方「bot 流程」「画面 area」按旧代码 / screen_info 记录,**仅供参考,不代表当前可运行**。需迁移到 `sr_od.*` 或移除,见 `.debug/temp/TODO.md`。
- **待实拍画面 + vision**:逐光捡金入口 / FH / PC 各态 / 战斗后实拍归档 + vision(分类图标 / 星数 / 节点 / 增益 UI)—— 高难 + 周限,待用户配合切画面。
- **末日幻影(Apoca)**:攻略提到三大玩法之一,但 `treasures_light` screen_info 只见 FH / PC area,未见 Apo —— **末日幻影可能未被 bot 建模**(新玩法或未覆盖),待确认(screen_info 数据缺口,本 skill 边界:只记,不改)。
- **challenge_mission screen 的「支援角色替换图标」area**:`pc_rect=[0,0,0,0]` 占位待填(见 [challenge_mission](../screens/challenge_mission.md)),不删。
- **配队**:`treasures_lightward_team_module.search_best_mission_team` 自动选队伍,逻辑待细化。
- **重 app 编排**:节点链(choose → check → challenge → 循环)详细待 develop doc。

## 参考来源

- [忘却之庭模式介绍与刷新规则](https://cg.163.com/static/content/65b7658ba00d11fd6d1a94c3)
- [忘却之庭玩法详解](https://www.gamersky.com/handbook/202307/1616859.shtml)
- [4.3 版本更新说明(三大玩法交替)](https://hsr.hoyoverse.com/zh-cn/news/164415)
