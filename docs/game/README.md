# 星穹铁道游戏知识建档

> bot 自动化所需的游戏知识(画面 + 玩法)建档。给 AI 编码时理解「bot 当前走到哪个画面、按什么玩法逻辑走」用。
> 画面建档方法论见 skill `od-dev-screen-onboarding`;玩法建档见 `od-dev-gameplay-automation`。

## 分层:识别模型 vs 知识文档

- **识别模型** `assets/game_data/screen_info/<screen_id>.yml`:bot 识别画面用的 area / 模板 / OCR 配置(机器读)。当前已建 32 画面。
- **知识文档** `docs/game/screens/`(画面)+ `docs/game/gameplay/`(玩法):画面与玩法的人读 + AI 理解文档(本目录,新建)。

两者必须对齐:doc 的「可交互元素 / 状态流转」要与 screen_info `area_list` + application/operation 代码逐条对齐(screen_info 有、doc 无 = 建档漏,补上)。

## 玩法知识分层:sources / research / 代码注册表

一个玩法的游戏知识按「谁写的、是否经我们核实」分三处(与 AGENTS.md「文档归位」条配合,本节为细则):

- **`docs/game/<玩法>/sources/`**:外部原文存档(攻略网站/B站视频/图鉴页的保真转录),按采集时的游戏版本冻结。
- **`docs/game/<玩法>/research/`**:我们提炼或核实过的知识(社区帖统计提炼、机制核实、用户口述、确认过的打法卡),**活文档**,随游戏版本与证据原地更新。
- **代码注册表**(如 `src/sr_od/application/currency_war/cw_*.py`):游戏**数据**(角色/装备/羁绊/概率表的值)的唯一源;注册表全量建模后对应 data 文档删除(双源即漂移)。

### 管线(单向)

`sources(原文)→ research(我们的知识)→ 注册表 / strategy 设计`。认知演进只改 research,不回流存档;发现存档内容有误或互相冲突,在 research 记修正/冲突 + 证据,存档保持原样。新版本素材 = 新文件进 sources(带版本前缀),旧档不覆盖。

### sources/ 保真纪律

- **只带来源元数据头**:源链接/BV号/版本/日期/采集方式/已知转写误差 + 版本时效注;**原文一字不动**。
- **我们的批注不进存档**:代码指针、对账表、实现待办、bot 行为叙述一律不写进 sources(归 research / develop / 进度追踪)。
- 目录名用 `sources`(原始材料)而非内容类型名 —— 名字本身守层纪律,防把「我们的使用指南」放进来。

### research/ 写作纪律

- **证据分级**:每条结论标来源与等级,权威序 = `[口述]`(用户实战口述,最高) > `[图鉴]`(游戏内图鉴/实机实测) > `[米游社]` > `[社区]`(bwiki/NGA/攻略,单源或推算);存疑/未找到标 🔴。
- **版本号是唯一允许的时间性**:不写「已落地/待做」等实现进度(归该玩法进度追踪)、不写对拍快照(bot 行为对照属进度记录)、不写实现日期。
- **值的单一源在代码注册表**:research 记「凭什么信这个值」(来源、推导、实测过程),不充当值的定义处;注册表已有对应字段时只写常量名。
- **裁定与教训不进 research**:玩法取舍裁定(采纳/不采纳某流派)→ ADR;分析教训 → insights;修正建议被消费后即删(结论活在代码 + 设计文档 + ADR)。

### 提炼 ≠ 复制(research 条目形态)

- research 条目 = **一条结论 + 证据级标签 + 指回源**;要论证过程回 sources 看原文。整段搬运 = 双源,下个版本两处要改,禁止。
- **策展筛子**:只提炼「被应用的或被核实的」;未被策略/注册表/文档依赖的内容不预提取(research 不做 sources 的镜像)。

## 现状(2026-07-29 建档 doc 阶段完成)

- screen_info 32 画面(识别模型)+ ~20 app。
- **docs/game/ 知识文档:13 画面 doc + 16 玩法 doc,32 screen_info + ~20 app 全覆盖(对话 doc 为 screen_info 缺口补档)**。
- **画面 doc**(`screens/`):normal_world(含 basic/battle_fail 子态) / phone_menu / mission / synthesize / team / 角色(character) / store / bag(10 分类总览) / large_map / enter_game(含 choose_account/logout_dialog 子态) / battle / misc_screens(common/catapult/fast_recover_dialog) / 对话(dialog,NPC 选项对话;未在 screen_info)。
- **玩法 doc**(`gameplay/`):currency_war / sim_uni / trailblaze_power / treasures_lightward / assignments / world_patrol / echo_of_war / ornamenet_extraction / nameless_honor / div_uni / guide / email / support_character / daily_training / relic_salvage / misc_apps(calibrator/large_map_recorder/buy_xianzhou_parcel/memory_crystal_shard/trick_snack)。
- **待实拍 + 视觉大模型 归档**:登录/战斗过程态/各玩法画面(消耗开拓力或周限 / 遇敌 / 重启,需用户配合切画面);doc 的 source_image 从临时 .debug 截图 → 测试仓 `screens/<screen>/<state>.webp` 归档。
- **已知数据缺口**(只记不改 screen_info):支援角色替换图标(challenge_mission/ornamenet_extraction)`pc_rect=[0,0,0,0]` 占位待填;合成按钮-最大值 `pc_rect` 占位;末日幻影(Apoca)screen_info 未建模;差分宇宙 Roguelike 演算 bot 未实现(仅饰品提取)。

## 建档顺序(按依赖,基础流程优先)

1. **基础流程**:登录(`enter_game*`)→ 大世界(`normal_world*`)→ 手机菜单(`phone_menu`)→ 任务(`mission`)
2. **通用系统**:背包(`bag_*`)→ 战斗(`battle`)→ 队伍(`team`)→ 合成(`synthesize`)→ 商店(`store`)
3. **玩法**(各独立 app):模拟宇宙(`sim_uni`)→ 花萼(`calyx`)→ 忘却之庭(`challenge_mission` / `treasures_light`)→ 饰品提取(`ornamenet_extraction`)→ …

## 规范

- 画面 doc:`docs/game/screens/<screen_id>.md`,结构按 od-dev-screen-onboarding skill(何时出现 / 状态流转 / 识别特征 / 可交互元素 / 识别快照 / 备注)。
- 玩法 doc:`docs/game/gameplay/<gameplay>.md`,结构按 sr-od-dev-gameplay-onboarding skill。
- doc 写**稳定画面事实**,不写建档/排查过程产物(测试状态归 sr-od-test,bug 历史归 commit)。
- **双向引用**(参照 ZZZ `docs/game/README.md`):
  - 画面 doc frontmatter `appears_in`:本画面出现在哪些玩法(`gameplay_name`)。
  - 玩法 doc frontmatter `involves_screens`:本玩法经过哪些画面(`screen_name`,中文)。
  - 关联键:用 `screen_name`(中文),非 `screen_id`。
- **现状**:多数 doc 已有 `appears_in`;`involves_screens` 仅 combat.md 有,其余玩法 doc 待补全。

## 已知工具限制

本环境的截图 视觉大模型 验证受限(`Read` 把图传 CDN、URL 含 Windows 反斜杠导致 `analyze_image` 解析失败)。建档时画面理解优先用 `analyze_screen` 的 OCR + 命中 area + screen_info `area_list` + 代码;图标/布局/状态等需 视觉大模型 的部分标注「待 视觉大模型 补」,工具恢复后补齐。
