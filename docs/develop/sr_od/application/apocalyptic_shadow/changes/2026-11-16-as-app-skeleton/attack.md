# 2026-11-16-as-app-skeleton 设计对抗报告

## 1. 审查范围与方法

- 攻击对象：本目录 design.md / landing.md / README.md（单文档方案）。
- 核对的事实源：challenge.py / goto_treasures_lightward.py / team_fill.py / reward_claim.py / trailblaze_power 五件套 / application_base.py / application_factory.py / application_run_context.py / one_dragon_context.py / application_factory_manager.py / backend_context.py / character_const.py / application_run_record.py / yaml_config.py / application_config.py。
- 规范依据：项目 AGENTS.md（§3/§4/§7/§9/§10）、AGENTS.local.md §1、docs/develop/harness/iteration-design.md（含 §7 攻击面）、skill `od-dev-write-application`（SKILL.md + references/factory-and-discovery.md + references/config-and-gui.md）。
- 方法：三核并重（无前提一致性 / 规范遵循 / 治本）+ 实现者走查（逐阶段「凭这份能开工吗」）。设计引用的全部代码行号已逐条到行核对（结论见 §4）。

## 2. 阻塞项

- [阻塞] 验收判据 2「list_applications 出现本 app」在 DEFAULT_GROUP=False 前提下恒假：design.md §9 判据 2（L109）/ landing.md 3.2 完成判据第 1 条（L31） / 问题：`DEFAULT_GROUP = False` 经 `discover_factories` 归入非默认组（application_factory_manager.py L94-121），注册进 `_application_factory_map` 但不进 `default_group_apps`（one_dragon_context.py L196-202、application_run_context.py L150-158）；而 `list_applications` 只列 `ONE_DRAGON_APP_ID` + `default_group_apps`（backend_context.py L1455-1461），非默认组应用不出现在返回中，`in_standalone_list` 字段只对已列出应用计算（L1473）——判据按代码真值不可能通过，landing 3.2 无法验收，实现者会把「没出现」误判为注册 bug 反复排查。设计依据指向 skill §4.5「app 出现在可运行列表(list_applications 或图形界面)」，该口径与当前代码冲突（currency_war_const.py L3 注释「仍可经 list_applications」同错，属误导性先例）；本次不做 GUI，skill 口径的两条验证路径都不可用 / 依据：backend_context.py L1447-1480、one_dragon_context.py L190-202、application_factory_manager.py L79-121、skill od-dev-write-application §4.5 / 建议修法：判据 2 改为可验证的注册证据——`describe_config(app_id='apocalyptic_shadow')` 能路由到 config 且 `run_standalone_app(app_id='apocalyptic_shadow')` 被受理（两者都以 `_application_factory_map` 注册为前提）；landing 3.2 判据同步修改（iteration-design §5 硬规则 4 全量同步复查）。

- [阻塞] 探测节点缺弹窗/横幅分支语义，已通关难度（常态）链路流程跑不通：design.md §3 L56（探测节点语义 = 点两态按钮 → 编队屏双锚验证 → read_team_nodes 读行数）、§10 核销表第 5 条（L122） / 问题：已通关难度在选关屏点「重新挑战」（或「更换编队」）会弹「更换编队确认」弹窗——challenge.py 入口节点专门处理它（L130-135），核销表第 5 条自己也记录了该弹窗；但弹窗出现在**探测节点自己引发的转移中**，此时挑战组合 op 尚未运行，核销表「被组合 op 正常处理」的时序不成立。探测节点按设计只验证编队屏双锚，弹窗遮挡时双锚不可见 → 探测失败 → §5「探测规模失败 → 中止」→ 流程终止。同类缺口还有：编队满员态进编队屏游戏自动弹首领简报横幅（challenge.py L116-118），遮挡下 `read_team_nodes` 锚行读空（先例语义见 team_fill.py L153-157「弹窗遮挡锚行 → 降级空列表重读」），探测读行数的遮挡分支同样未定义 / 依据：challenge.py L111-151（入口节点完整状态机含弹窗与横幅分支）、team_fill.py L153-157、design.md §10 第 5 条 / 建议修法：§3 探测节点补齐状态机——①已在编队屏双锚短路（同 challenge.py L121-125）；②「更换编队确认」弹窗点击确认后重试验证（同 L130-135）；③满员横幅等待自动消失（L36「不点也会自动消失」）或点空白关闭后再读行；④`read_team_nodes` 读空重读（先例 team_fill.py L153-157）；§10 第 5 条同步改为「弹窗在探测节点处理」。若选另一条路（探测节点不处理、把非编队屏态留给挑战 op 入口接管），则探测节点「验证到达」语义与 §5 中止语义须一并改写，两处必须自洽。

## 3. 建议项

- [建议] config 的构造口径与 create_config 返回类型偏差未写明：design.md §4（L68、L71-74）/ 问题：基类 `create_config(instance_idx, group_id) -> ApplicationConfig`（application_factory.py L79-94），而权威口径是 config = YamlConfig 子类、构造只收 instance_idx、文件落 `config/<idx>/<name>.yml`（config-and-gui.md §1；yaml_config.py L49-64）；ApplicationConfig 的落盘路径带 group_id 子目录（application_config.py L20-23）。设计「app 运行时配置实例与 factory 共用同一 YamlConfig 文件名」成立的前提是「create_config 丢弃 group_id」（factory-and-discovery.md §3 先例 `return MyAppConfig(instance_idx=...)`）——这个决定只存在于 skill reference，设计未写明；实现者若照基类返回标注让 config 继承 ApplicationConfig，文件落 `config/<idx>/<group>/<name>.yml`，与 app 直构路径分叉。另 YamlConfig 子类不是 ApplicationConfig 子类，覆写 create_config 与基类返回标注冲突（运行时无碍，读者困惑）/ 依据：application_factory.py L79-94、application_config.py L8-33、yaml_config.py L49-64、skill references/config-and-gui.md §1 与 factory-and-discovery.md §3 / 建议修法：§4 补一句「config 类继承 YamlConfig，create_config 忽略 group_id（独立工具无组配置差异，同 skill factory-and-discovery §3 先例）」，并声明返回类型与基类标注的偏差口径。

- [建议] 「进编队屏点击」在探测节点与挑战 op 入口节点双实现，职责重复未正视：design.md §3 L56、§11 L126 / 问题：挑战 op 入口节点已有完整的「选关屏两态按钮 → 编队屏」状态机（challenge.py L111-151，含弹窗与横幅分支）；探测节点按设计再实现一遍点按钮进编队屏（且少了弹窗分支——阻塞 2 的直接根源）。§11 取舍段只论证了「read_team_nodes 行数判定不抽公共 op」，对「点按钮进编队屏」这半截动作的重复只字未提。核三两问：根 = 挑战 op 的入口多态把「进编队屏」与「选人→战斗」绑死，app 无法只复用前半截；当前修法（app 节点内重写半截状态机）是症状级 / 依据：challenge.py L111-151；AGENTS.local.md §1 根源两问与跨件半问 / 建议修法：两选一并写进 §11——a) op 层抽「进入末日幻影编队屏」独立 op，挑战 op 入口改为组合它、app 探测节点复用（治本归层）；b) 维持 app 节点内实现，但显式声明战术权衡（重复约 20 行 + 弹窗/横幅分支与 challenge.py 同步维护的义务）+ 根治排期。

- [建议] 领奖「警告继续」的语义落点未定义：design.md §5 L83 / 问题：「节点状态记警告，app 仍成功收尾」——Operation 语义里节点级「警告」无原生载体：round_fail 判死 op，要「继续」只能 round_success(状态串) 或日志；§6 又定 run_record 无业务字段，三处互证后唯一可行落点是 round 状态串 + 日志，但需实现者自行推演，违反「实现者无需再设计」/ 依据：iteration-design.md §5 硬规则 2；skill od-dev-write-application §4.1（失败处理必须设计明确）/ 建议修法：§5 该行改写为唯一表述，如「领奖节点失败时 round_success('领奖失败:<原因>') 记录于运行日志，app 正常收尾」。

- [建议] 池剔除后为空的边界语义未定义：design.md §4 L72、§7 L96 / 问题：§7「空列表 = 回落默认快照池」与 §4「不合法名字剔除并打日志；池不足以凑 team_count*4 → 显式失败」组合出未定义态：配置池全为不合法名 → 剔除后为空 → 按 §7 字面回落默认池，但用户显式配置过池，静默回落违背配置意图且无提示 / 依据：iteration-design.md §5 硬规则 2 / 建议修法：§7 补一句口径，如「仅配置键缺省或显式 `[]` 回落默认池；剔除后为空视为配置错误显式失败」。

- [建议] 新功能零测试安排，与「测试随功能一起写」不符：landing.md 3.1 完成判据、3.3 文件面 / 问题：`pick_random_teams` 是纯函数，其「无放回、恰抽 team_count*4 个、互不相同」正是设计约定（对应 team_fill.py L96-99 构造校验的承接方），按 AGENTS.md §10.1「新功能:锁设计约定——测试随功能一起写」应在 3.1 随功能落单测；landing 把测试只排在 3.3 评审阶段的文件面（「sr-od-test/**（评审发现的补测）」），测试成为评审兜底而非随功能交付 / 依据：AGENTS.md §10.1 第一原则第 1 条 / 建议修法：landing 3.1 完成判据补「pick_random_teams 单测（数量 / 去重 / 池不足显式报错）随阶段提交」。

- [建议] 过程叙事残留与个别主张未标依据：design.md §0 L5、§1.1 L16、§3 L40 / 问题：「03:45 停工」对设计内容零约束力，按「删掉后剩余约束依然成立则该删」判据属过程残留；§3 L40「SrApplication 默认 need_check_game_win=True」是关键主张但未标出处（已核对为真值：sr_application.py L18）/ 依据：iteration-design.md §5 硬规则 1（无依据标注的主张默认为攻击目标）与硬规则 3（无过程叙事）；src/sr_od/application/sr_application.py L13-18 / 建议修法：删「03:45 停工」；L40 补依据标注（src/sr_od/application/sr_application.py）。

## 4. 已核对为真的关键引用（逐条到行）

- team_fill.py L96-97 = 8/12 构造校验；L108-109 = 角色名白名单校验 ✅（design §3/§8 引用属实）。
- challenge.py L121-125 = 编队屏双锚短路直接接续 ✅；L141-150 = 选关屏「重新挑战/前往挑战」两态 ✅；L103-104 = buff_slots 1 基按位置选择、默认全 1 ✅；L44 = 行动值耗尽不计失败 ✅；L19-21 = 不选难度 ✅。
- reward_claim.py 起点/终点 = 选关屏、两 tab 一键全领 ✅（与挑战 op 终点衔接成立：挑战终点验证「标题-末日幻影行」，领奖入口要求「标题+难度-01」双锚，双锚在选关屏恒在——goto as_settle L348-350 同款实机口径）。
- GotoTreasuresLightward APOCALYPTIC_SHADOW 终点 = 选关屏（标题+难度-01 双锚，L337-351），起点任意画面、不在入口链先回大世界 ✅。
- trailblaze_power_run_record.py L16-17 = 恒重置口径 ✅；AppRunRecord 默认能力（成功/失败落盘）✅（application_run_record.py L55-79）。
- Application 构造带 run_record 参数、缺省时经 run_context 兜底（application_base.py L29-60）；SrApplication 默认 need_check_game_win=True ✅（sr_application.py L18）。
- factory 三件套签名（application_factory.py L64-108）与五件套命名兼容自动发现（*_factory.py / *_const.py，factory-and-discovery.md §1）✅。
- MCP 配置工具经 run_context.get_config → factory.get_config → create_config 路由（application_run_context.py L258-294），非默认组应用已注册可路由 ✅（design §4 L74 主张成立）。
- 开拓者在 CHARACTER_LIST 按命途×性别拆名（character_const.py L175-179、L205-209），「按命途拆名被排除」主张成立 ✅。
- run_standalone_app 直传 app_id 不依赖独立应用列表（backend_context.py L1420-1424），判据 3 本身可执行 ✅。
- 复用件路径全部存在：buff_equip.py / battle.py / battle_exit.py / tl_team_obs.py（read_team_nodes 定义于 tl_weakness_obs.py L238、经 tl_team_obs re-export，team_fill 的导入路径标注无误）/ back_to_normal_world_plus.py / docs/game/screens/末日幻影-祭礼奖励.md ✅。

## 5. 结论

- 设计的复用盘点、行号引用、取舍声明整体扎实（§4 证据清单），四段式骨架、失败语义表、核销表结构符合规范。
- 两个阻塞项都属「验收/流程判据与代码真值或组件事实冲突」：判据 2 按现状代码恒假；探测节点缺弹窗/横幅分支会让已通关难度（日常重打 = 高频态）跑不通。
- 修完 2 个阻塞项并完成 design↔landing 同步复查（iteration-design §5 硬规则 4）后，可进入实现。
