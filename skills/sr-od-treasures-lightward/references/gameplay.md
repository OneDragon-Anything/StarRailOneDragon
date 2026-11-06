---
gameplay_name: 忘却之庭(逐光捡金)
app_id: treasures_lightward
last_updated: 2026-11-04
source: 实机实测(2026-11-04,4.6 版本期) + screen_info `treasures_light`(51 area) + WebSearch 攻略;实机证据优先,攻略仅补充
involves_screens: [逐光捡金, 挑战副本, 战斗画面, 队伍]
---

# 忘却之庭 / 逐光捡金(treasures_lightward)

逐光捡金系列常驻高难挑战。**忘却之庭**本体分三视图(选关界面顶部图标切换,见 [逐光捡金](../../../../docs/game/screens/逐光捡金.md)):**混沌回忆**(当期轮换 12 关) / **回忆·天艟求仙迷航录**(仙舟「罗浮」,6 关持久层) / **回忆·永屹之城遗秘**(雅利洛-VI,15 关持久层)。逐光捡金分类页另有**虚构叙事**(Pure Fiction) / **末日幻影**(Apoca) / **异相仲裁**三个独立玩法分类。三大玩法**交替轮换**(~42 天/期)。进入后断开外界并锁定养成(官方规则原文:不能调队伍/换升级晋阶光锥遗器/升角色/用消耗品)。`pc_alt=false`。

## ⚠️ bot 现状:app 不可运行(2026-09-02 核实)

`application/treasures_lightward/` 是**旧架构遗产**(重构前代码:引用已删除的 `basic.*` / `sr.app.*` / `sr.operation.*` 模块 + 旧 `StateOperationNode` API):

- **import 直接失败**(`ModuleNotFoundError: No module named 'basic'`),app 不可运行;
- **未注册**:无 factory,`src` 内无任何外部引用(17 文件自引用孤儿),一条龙套件不含它;
- **建档资产有效**:画面侧(treasures_light 32 area + fixtures)是 2026-08-29 按新框架建的,与旧代码无关;
- **路径**:按 `od-dev-gameplay-automation` 重写为新框架 app(玩法复杂:期次记录 / 星数检测 / 配队模块匹配 / 循环挑战),或继续搁置。重写前下文「bot 流程」节仅作旧实现规格参考。

## 玩法机制(2026-11-04 实机实测,规则说明弹窗官方原文)

**混沌回忆**(当期轮换,12 关,每关上下半两支队伍):
- **波次结构**(2026-11-04 实机 + 国际服官方文本交叉):每关 **2 个 Wave**(波次,连续战斗自动衔接;官方英文游戏文本用小写 wave,与 Cycle=行动轮严格区分;社区惯称 Node 1/Node 2 或 1st/2nd Half,均指同一物)。第一波打完无任何结算弹窗,直接切到第二波编队(秘技点重置满 5)在第二波出生点待命;两波全打完才出「挑战成功」结算。自动化要点:第一波结束后的「波次待命态」(大世界 HUD+队伍面板+秘技满)需识别并对第二波重新走「前进→秘技→开战」。
- **节点画面**(2026-11-04 实机):挑战进入的是锁光标大世界场景,**鼠标点击需按住 Alt 才生效**(框架 area 的 pc_alt 标志);首波进入弹记忆紊流说明(点空白关闭);敌人一般在出生点正前方(平台台阶前),前进 2-4 秒即入攻击距离。
- **术语英文对照**(国际服官方,2026-11-04 调研):记忆紊流=Memory Turbulence;本期物竞天择=Survival of the Fittest(4.6 期);笑点=Punchline;阿哈=Aha;奇珍琳琅=Priceless Jewels(总店,子页签 光锥呈现=Light Cone Manifest / 戏言成真=Jokes Come True,别把子页签当总店)。
- **星数规则**(挑战目标官方原文):胜利时剩余 10 轮以上=1星 / 剩余 20 轮以上=2星 / 没有角色无法战斗=3星;满星 36(12 关×3)。轮=行动值周期(机制详见 [mechanics/battle-mechanics](../../../../docs/game/mechanics/battle-mechanics.md) §1.2),轮数用尽=挑战失败,剩余轮以「倒计时」显示在战斗左侧行动序列。
- **3星通关后,可获得前置关卡的全部奖励**;3 星逐关记录跨期保留。
- **快速解锁**:最高 3 星通关进度跨期记录,新一期自动解锁对应关卡及全部前置,**上限前 10 关**;可直接挑战记录中的最高 3 星关卡,3 星通关后视同通关全部前置。**本期内**(2026-11-04 实机确认):通关第 N 关即解锁第 N+1 关,可直接挑战最新解锁关,无需按序重打已通关卡——自动化策略取「直接打最后已解锁关」。
- **快速通关补发**(2026-11-04 其十首通实机):**首次 3 星通关最高解锁关时**,弹出「快速通关」列表——视同 3 星通关所有前置关卡,前置通关奖励自动领取(列表每关一行+灰勾,底部「确认」),确认后弹「获得物品」汇总页(点击空白关闭),之后才是正常结算返回。自动化要点:结算返回前需依次处理这两个弹层,否则返回按钮被盖住。
- **星启模式**(4.x 新增高难,实机确认):通关第 11 关后自动开启;星启模式第 12 关需挑战 **3 个节点**,与常规 12 关共享 3 星记录;3 星通关且**剩余轮 ≥33** 获得**棱彩星**+额外奖励;累计 36 星+棱彩星=本期限时通关勋章;可随时切回常规模式打常规 12 关拿原有奖励。
- **记忆紊流**(期次 buff):每期更新,弹窗展示全文;**每一关都有其独特效果且仅在当前关内生效**(官方原文)——不是全期统一 buff。本期(物竞天择)示例:我方施放终结技获得 5 笑点;每轮开始时阿哈立即获得 1 个固定计入 20 笑点的额外回合(欢愉体系定制 buff)。

**回忆持久层**(两章,一次性,本账号 2026-11-04 均已 3 星满):
- 天艟求仙迷航录 6 关(星芒 18/18)/ 永屹之城遗秘 15 关(星芒 45/45);随探索进程逐步解锁,难度和奖励不受均衡等级影响。

**奖励结构**(印记馈赠/回忆馈赠弹窗实机):
- 印记馈赠:限时通关勋章(条件:星芒 36+棱彩星 1)+ 累计星芒阶梯奖(3/6/9/12…星各一档)。
- 回忆馈赠:每关首次 3 星通关奖励(逐关列表)。

**敌人构成**(编队屏实机,物竞天择其十):敌人等级 90;每半场显示「建议属性」=该半场敌人弱点属性(其十上半:火+物理,下半:量子+冰);编队屏内置「通关阵容」查询与敌人「详情」入口。

**入口链**(2026-11-04 实测):大世界 →(右上指南)→ 星际和平指南 →(逐光捡金 tab)→ 分类页 →(选分类,右侧横幅「传送」)→ [记忆紊流更新弹窗(每期首次,点击空白关闭)] → 选关界面(顶部图标切三视图)→ 关卡水晶 → 编队屏 →「混沌回忆」按钮 → 战斗。**选关右上关闭 X 直接回大世界**(旧档「回指南」已过时)。

## bot 流程(`application/treasures_lightward`)

`TreasuresLightwardApp` 调度(节点链):
- `_choose_forgotten_hall` / `_choose_pure_fiction`(选 FH / PC 分类)→ `_check_record_and_tp`(检测记录 + 传送)→ `_check_pf_new_start`(PC 新一期)。
- `_check_total_star`(检测总星数)→ 满星(`STATUS_FULL_STAR`)→ 完成;非满星 → `check_max_unlock`(找开始关卡)→ `challenge_mission`(挑战)→ 战斗后检测星 → 循环挑战下一关(满星循环)。
- op:`challenge_mission` / `check_max_unlock_mission` / `check_mission_star` / `check_star` / `choose_character` + `forgotten_hall/`(choose_mission / team / reward)+ `tl_battle` / `tl_wait`。
- `search_best_mission_team`(配队模块选最优队伍)。

## 画面(`treasures_light` screen_info「逐光捡金」,51 area,2026-11-04 增补)

独立 screen doc 见 [screens/逐光捡金](../../../../docs/game/screens/逐光捡金.md)。area 分族:

- **分类页遗留**:TL_CATEGORY_*(现属分类页,2026-11 实测 rect 已漂移,待迁至 指南-逐光捡金 screen)、TL_SCHEDULE_*(同上,传送按钮新版在分类页右侧横幅 y≈452)。
- **忘却之庭选关(三视图共享)**:FH_TITLE(id_mark)、标题-混沌回忆行(lcs 0.7,视图判别)、章节名-天艟求仙迷航录 / 永屹之城遗秘(回忆视图判别)、切换器-混沌回忆 / 回忆天艟 / 回忆永屹(顶部三图标)、期名文本 / 倒计时文本 / 词条-记忆紊流 / 按钮-规则说明 / 入口-奇珍琳琅(→商店) / 按钮-星芒礼包(→馈赠弹窗) / 按钮-关闭X(→大世界) / 提示-快速解锁 / FH_TOTAL_STAR。
- **弹窗子态**:弹窗-规则说明-标题/关闭X、弹窗-馈赠-tab印记馈赠/tab回忆馈赠/关闭X、NODE_FIRST_CLICK_EMPTY(紊流弹窗)、AFTER_BATTLE_QUICK_PASS_*、退出对话框确认。
- **编队/战斗后(in-mode)**:FH_START_CHALLENGE(编队屏最终开始钮)、FH_AFTER_BATTLE_SUCCESS_1/2 / FAIL、FH_AFTER_BATTLE_BACK_BTN_1/2。
- **虚构叙事(PC)态**:PF_TITLE、PF_NEW_START、PF_CACOPHONY_*、PF_START_CHALLENGE、PF_AFTER_BATTLE_*。
- **关联**:`challenge_mission`(挑战副本,支援角色替换图标等,见 [challenge_mission](../../../../docs/game/screens/challenge_mission.md) screen);**编队屏未独立建档**(2026-11-04 探索已采证:两编队槽/建议属性/通关阵容,建档中)。

## 备注 / 待查

- ⚠️ **app 代码未迁移 / 不可运行(2026-07-29 核实)**:`application/treasures_lightward/` **全部文件**(app / config / record / team_module / `op/*`)仍用旧 `sr.*` / `basic.*` 导入(如 `from sr.app.application_base import Application`、`from basic.i18_utils import gt`)。本仓库已重构为 `sr_od.*` —— `src/sr/`、`src/basic/` 不存在 → **无法导入**;且无 `_app_factory.py`、`list_applications` 不含本 app → **未注册、不运行**(sr_od 重构时漏迁移的死代码)。上方「bot 流程」「画面 area」按旧代码 / screen_info 记录,**仅供参考,不代表当前可运行**。需迁移到 `sr_od.*` 或移除。
- **待实拍(条件态)**:FH / PC in-mode 战斗后各态实拍(需实际打一期;入口链 / 紊流弹窗 / FH 选关已归档,见 [screens/逐光捡金](../../../../docs/game/screens/逐光捡金.md))。
- **末日幻影(Apoca)**:已探并建模(2026-11-05 实机建档:开场 / 选关 / 首领信息 / 编队 / 终焉公理 / 节点结算 各 screen doc);新框架挑战 op 已落地(`sr_od.operations.tl_as_challenge`,星启/难度04 未适配)。操作路由见 SKILL.md 对应类型块。
- **异相仲裁**:2026-11-04 分类页确认存在(条目「异相仲裁·落叶归根」),未进探,未建模。
- **challenge_mission screen 的「支援角色替换图标」area**:`pc_rect=[0,0,0,0]` 占位待填(见 [challenge_mission](../../../../docs/game/screens/challenge_mission.md)),不删。
- **配队**:`treasures_lightward_team_module.search_best_mission_team` 自动选队伍,逻辑待细化。
- **重 app 编排**:节点链(choose → check → challenge → 循环)详细待 develop doc。

## 参考来源

- [忘却之庭模式介绍与刷新规则](https://cg.163.com/static/content/65b7658ba00d11fd6d1a94c3)
- [忘却之庭玩法详解](https://www.gamersky.com/handbook/202307/1616859.shtml)
- [4.3 版本更新说明(三大玩法交替)](https://hsr.hoyoverse.com/zh-cn/news/164415)
