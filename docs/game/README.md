# 星穹铁道游戏知识建档

> bot 自动化所需的游戏知识(画面 + 玩法)建档。给 AI 编码时理解「bot 当前走到哪个画面、按什么玩法逻辑走」用。
> 画面建档方法论见 skill `sr-od-dev-screen-onboarding`;玩法建档见 `sr-od-dev-gameplay-onboarding`。

## 分层:识别模型 vs 知识文档

- **识别模型** `assets/game_data/screen_info/<screen_id>.yml`:bot 识别画面用的 area / 模板 / OCR 配置(机器读)。当前已建 32 画面。
- **知识文档** `docs/game/screens/`(画面)+ `docs/game/gameplay/`(玩法):画面与玩法的人读 + AI 理解文档(本目录,新建)。

两者必须对齐:doc 的「可交互元素 / 状态流转」要与 screen_info `area_list` + application/operation 代码逐条对齐(screen_info 有、doc 无 = 建档漏,补上)。

## 现状(2026-07-29 建档 doc 阶段完成)

- screen_info 32 画面(识别模型)+ ~20 app。
- **docs/game/ 知识文档:12 画面 doc + 15 玩法 doc,32 screen_info + ~20 app 全覆盖**。
- **画面 doc**(`screens/`):normal_world(含 basic/battle_fail 子态) / phone_menu / mission / synthesize / team / 角色(character) / store / bag(10 分类总览) / large_map / enter_game(含 choose_account/logout_dialog 子态) / battle / misc_screens(common/catapult/fast_recover_dialog)。
- **玩法 doc**(`gameplay/`):sim_uni / trailblaze_power / treasures_lightward / assignments / world_patrol / echo_of_war / ornamenet_extraction / nameless_honor / div_uni / guide / email / support_character / daily_training / relic_salvage / misc_apps(calibrator/large_map_recorder/buy_xianzhou_parcel/memory_crystal_shard/trick_snack)。
- **待实拍 + vision 归档**:登录/战斗过程态/各玩法画面(消耗开拓力或周限 / 遇敌 / 重启,需用户配合切画面);doc 的 source_image 从临时 .debug 截图 → 测试仓 `screens/<screen>/<state>.webp` 归档。
- **已知数据缺口**(只记不改 screen_info):支援角色替换图标(challenge_mission/ornamenet_extraction)`pc_rect=[0,0,0,0]` 占位待填;合成按钮-最大值 `pc_rect` 占位;末日幻影(Apoca)screen_info 未建模;差分宇宙 Roguelike 演算 bot 未实现(仅饰品提取)。

## 建档顺序(按依赖,基础流程优先)

1. **基础流程**:登录(`enter_game*`)→ 大世界(`normal_world*`)→ 手机菜单(`phone_menu`)→ 任务(`mission`)
2. **通用系统**:背包(`bag_*`)→ 战斗(`battle`)→ 队伍(`team`)→ 合成(`synthesize`)→ 商店(`store`)
3. **玩法**(各独立 app):模拟宇宙(`sim_uni`)→ 花萼(`calyx`)→ 忘却之庭(`challenge_mission` / `treasures_light`)→ 饰品提取(`ornamenet_extraction`)→ …

## 规范

- 画面 doc:`docs/game/screens/<screen_id>.md`,结构按 sr-od-dev-screen-onboarding skill(何时出现 / 状态流转 / 识别特征 / 可交互元素 / 识别快照 / 备注)。
- 玩法 doc:`docs/game/gameplay/<gameplay>.md`,结构按 sr-od-dev-gameplay-onboarding skill。
- doc 写**稳定画面事实**,不写建档/排查过程产物(测试状态归 sr-od-test,bug 历史归 commit)。
- **双向引用**(参照 ZZZ `docs/game/README.md`):
  - 画面 doc frontmatter `appears_in`:本画面出现在哪些玩法(`gameplay_name`)。
  - 玩法 doc frontmatter `involves_screens`:本玩法经过哪些画面(`screen_name`,中文)。
  - 关联键:用 `screen_name`(中文),非 `screen_id`。
- **现状**:多数 doc 已有 `appears_in`;`involves_screens` 仅 combat.md 有,其余玩法 doc 待补全。

## 已知工具限制

本环境的截图 vision 验证受限(`Read` 把图传 CDN、URL 含 Windows 反斜杠导致 `analyze_image` 解析失败)。建档时画面理解优先用 `analyze_screen` 的 OCR + 命中 area + screen_info `area_list` + 代码;图标/布局/状态等需 vision 的部分标注「待 vision 补」,工具恢复后补齐。
