# 货币战争版本适配(CW 域)

## 目录

- §1 场景判型与适配模式
- §2 核心流程 checklist
- §3 各域明细
- §4 换赛季战役组织
- §5 已知坑

## 1. 场景判型与适配模式

拉一次官方配置(命令见 §3.1,产物含全部域)就能判型,**判据两条**:

- **赛季号变化**:配置顶层 `season_id` 与上季不同 = 换赛季重做;`sub_season_id` 变化 = 同季扩充。
- **名单重合度**:角色名单与现有注册表大面积不重合(费用/站位/羁绊成片变化)= 换赛季重做;名单基本重合、只增不减 = 扩充。

| 判型 | 特征 | 适配深度 |
|---|---|---|
| **赛季扩充** | 名单只增不减,机制沿用 | §2 全走;注册表复核(diff 驱动),知识层增量重跑 |
| **换赛季重做** | 角色赋能/费用/羁绊/前后台定位重做,名单大换血 | §2 全走 + 按 §4 组织;注册表重建(不是复核),知识层全量失效重跑(等攻略沉淀,有缓冲期) |

判型错了代价不对称:把换赛季当扩充 = 残留旧口径带病运行;把扩充当换赛季 = 无谓重做。两条判据都指向重做才算重做,拿不准问用户。

## 2. 核心流程 checklist(必做,没做完不算完成)

1. ☐ **确认客户端在线且能截画面**(项目 MCP `check_game_window` / `analyze_screen`);没更新按 od-mihoyo-launcher 更新
2. ☐ **拉官方配置判型**——`uv run python skills/sr-od-dev-currency-war/scripts/plaza_fetch.py config`(项目根),按 §1 判型并与用户对齐范围
3. ☐ **角色域**——§3.1
4. ☐ **羁绊域**——§3.2;依赖角色注册表就绪,顺序不可倒
5. ☐ **装备域 → 投资域 → 主角光环域 → 敌情域**——§3.3~§3.6 按此序走;主角光环的适配名单翻译依赖角色注册表(§3.5)
6. ☐ **识别模板面**——§3.7
7. ☐ **版本敏感常量实机重采**——§3.8;换赛季默认全变,扩充按官方公告判
8. ☐ **测试回归**——`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`;红测逐条判断代码过时还是测试过时
9. ☐ **实机冒烟**——重启项目 MCP server 后进一局受影响玩法(改了识别/注册表/常量都算);实机局顺带校准第 7 步实采值
10. ☐ **知识层与策略消费点**——§4.4;扩充 = 复核,换赛季 = 等攻略沉淀后重跑;允许跨日收尾但要在进度账本登记
11. ☐ **提交**——按域分阶段 commit,git add 逐文件点名

## 3. 各域明细

### 3.1 角色域

- 入口:`skills/sr-od-dev-currency-war/scripts/gen_plaza_chars.py`(产出:注册表段片段 `registry_chars_v<版本>.py` / 人读角色文档 / 立绘模板 `character_avatar/` / 掉出名单 diff 报告 / `--check-only` 对拍)。
- 注册表 = `src/sr_od/application/currency_war/data/cw_chars.py`。官方段生成片段按两侧标记注释**整段替换**接入(标记与 `cw_chars.py` 官方段标记逐字一致,零人工补逗号);`SYSTEM_UNITS` 系统单位段为实机采集人工维护,生成器不触碰。字段全官方镜像(cost/position/category_tags/羁绊三字段/is_expert/is_hide 从配置照抄),角色名经 `canon()` 归一(U+2022→U+00B7;产出段含 • 直接报错)。
- 验收:`--check-only` 片段 vs config 对拍归零——无需例外清单(注册表为官方多条 1:1 镜像);`DISTINCT_CARDS_PER_COST` 从注册表派生自动跟上。

### 3.2 羁绊域

- 数据源双路:官方 config 骨架(`trait_info_list`:trait_id/名/图标/类型有值,过滤 `trait_type in (0,1,2)` = 29 条基座,type 3 主角光环专属不进本域;分层细节恒空)+ 攻略广场 Hot 帖聚合(帖内 `role_stages[].traits[]` 为唯一全结构源,自带官方成员名单 `role_ids`、激活门槛 `layers` 与分层效果全文)——拉若干页帖子聚合即得全量,不用按羁绊逐个筛采。
- 生成器+对拍一体:`gen_traits.py`(config 骨架过滤 + 帖聚合〔去重 = layers 最多、并列取新帖〕+ 富文本渲染 + role_ids→规范名翻译〔运行期从角色注册表派生映射〕+ 成员对拍〔官方名单 vs 注册表自报,差异逐条人裁进例外清单或修注册表〕+ wiki 交叉报告 + 默认 dry-run 预览 / `--land` 落库)。**成员对拍依赖角色注册表先建**,角色域没闭环前必红——顺序契约,不是缺陷。
- 注册表 = `src/sr_od/application/currency_war/data/cw_traits_data.py`(`TRAITS` 29 条按 trait_id 稳定机器键;官方口径镜像,生成器产物勿手编)。

### 3.3 装备域

- 入口:`gen_equip_registry.py`(单源 = plaza config `equipment_list`;产出 `cw_equipment_data.py` + 装备模板)。官方分类直落;「简易装备」从全部条目的 compose_list 子件展开派生。
- 重跑先对拍旧基准再覆盖写(stdout 掉出/新增清单);模板字节比对幂等,官方换图自动跟上。
- `stacking` 字段为效果文本推断——版本更新后实机抽检新条目。
- 换赛季注意新装备类别(消费点按 diff 复核),消费侧常量(`EQUIP_TOOL_CATEGORY` / `CONSUMABLE_EQUIP_CATEGORIES`)按新分类重裁。

### 3.4 投资域

- 入口:`gen_plaza_invest.py`(生成 `cw_invest_data.py` base 层 + diff 报告;`fight_augment_list` + `portal_list`)。
- base 全官方镜像;人工建模增量(economy 数值化/评估分/环境分类/阵营绑定)在 `kernel/cw_investments.py` overlay 手维护,diff 后逐条重审孤儿键(守卫测试 `test_cw_invest_registry` 辖住)。换赛季 = 大面积重建模,量大可分期,但 base 数据必须先行落库。

### 3.5 主角光环域

- 入口:`gen_plaza_spot_lights.py`(config 单源直灌:`spot_light_list` + 官方标签枚举);产出 `cw_spot_lights.py`(id/name/desc/tags/suitable_roles 官方口径镜像,数字 id 稳定主键,desc 去富文本)。
- 适配名单(suitable_roles)为生成期翻译:plaza role id 经角色注册表翻译成规范名,未知 id 直接报错——依赖角色注册表先就绪,顺序契约非缺陷;空名单条目 = 全局/非角色绑定型光环(金币/装备/角色奖励类),官方原样非缺数据。
- 5 条特殊羁绊授予面(从师/连携追击/星狩誓言/四维狂潮/救世主 = trait 域 400xxx 骨架)在本表登记,桥接信息自足,不在 trait 域重复。⚠️ 按 tag 筛「特殊羁绊」只会命中 4 条——救世主的官方 tag 是「羁绊」,要按名字或 400xxx 语义找齐。
- 验收:重跑幂等(diff 全 0)+ `uv run pytest sr-od-test/test/sr_od/application/currency_war/data/` 绿。

### 3.6 敌情域

- 注册表 = `src/sr_od/application/currency_war/data/cw_enemy_data.py`:`BOSS_NICKNAMES` 俗称→规范名映射(人工维护,简报读数两段转换用)+ `BOSS_MECHANICS` 机制 tag(bosses.md 图鉴实采)。tag 只作观察分组,不参线分(线侧 boss 克制单一源 = `kernel/cw_affinity_table.BOSS_AFFINITY`)。
- 版本更新:游戏内数据银行图鉴看是否出新 boss/机制变化 → `docs/game/currency_war/data/bosses.md` 重采 → 注册表同步;俗称映射按新版本社区用语补。

### 3.7 识别模板面

- 生成器自动产:角色立绘模板(`assets/template/currency_war/character_avatar/<规范名>/`,多档同名共用一目录,费用底色取起始档官方费用字段)、装备模板——都在 `gen_plaza_chars.py` 内。
- **掉出名单的旧模板不自动删**:生成器产掉出名单 diff 报告(`.debug/game_data/currency_war/plaza/dropped_v<版本>.md`,掉出方向唯一出口),模板删除留给人工裁定(防误删换皮重出单位的识别资产)。
- 新画面元素(新 UI/新交互)实机冒烟时按 od-dev-screen-onboarding 建档。

### 3.8 版本敏感常量

- 刷新概率表(`cw_shop_odds.REFRESH_PROB`)/ 升级经验门槛表 / 牌池副本数(判据:同费种类数必须是 3 的倍数,3合1 机制决定)。
- 换赛季默认全变,扩充按公告判;采集方式见 data-collection.md;概率表校验 = 行和 100%。

## 4. 换赛季战役组织(扩充跳过本节)

### 4.1 战役阶段与立项顺序

换赛季是**跨迭代战役**,不是一次 checklist 走完。按域立迭代,串行推进:

**数据面重建**(角色 → 羁绊 → 装备 → 投资 → 主角光环 → 敌情 → 识别模板)→ **消费层迁移**(引用旧名单/旧分类/旧常量的代码逐点迁到新注册表)→ **知识层重跑**(§4.4,等攻略帖沉淀)

- 每域一个迭代:重跑生成器 → 落库 → 消费点全迁完才算该域闭环。
- 依赖:羁绊与主角光环的名单翻译依赖角色注册表先闭环;消费层迁移依赖各数据域落库;知识层重跑依赖消费层迁移完(策略按新知识重写)。
- 迭代按 od-dev-run-iteration 建(`.temp/changes/` 迭代目录,tasks.md 记进度);跨迭代欠账登记 `.debug/progress/CW跨迭代挂账.md`。

### 4.2 过渡期测试处理

- 一致性校验归测试(项目纪律,见 sr-od-test/README.md「禁止清单」);数据重建期新旧不一致,**测试红是预期表现,不是故障**。
- 红测试处理:当前能改的就改(消费点同步迁移);改不了 = 依赖未就绪,测试直接删(批量删除走测试规范的 src 指针对账工序)——旧约定已作废,红测试没有锁的对象;依赖补充时,新测试随新功能写到对应位置。
- 数据域闭环判据 = 该域一致性测试全绿 + 消费点迁移完。

### 4.3 掉出名单的三层处理

| 层 | 处理 | 理由 |
|---|---|---|
| 注册表条目 | 随官方段标记整段替换自然移除 | 带着旧条目跑 = 策略消费过期名单 |
| 角色文档 | 删(git 历史可溯) | 生成物,重跑不再产出 |
| 识别模板目录 | **暂留**,实机确认无换皮重出再清 | 特殊单位可能以新形态回归,误删 = 识别断档 |

### 4.4 知识层与策略消费点(时间缓冲期)

阵容知识(final_comps/过渡体系/聚类)、万金油名单、桥池、引擎阵营全部依赖攻略广场新版本帖沉淀——赛季初帖量不足,**不硬跑**。缓冲期策略:

1. 数据面/识别面先闭环(§2-1~9),bot 具备进局能力;
2. 知识层重跑等帖量够(约 1-2 周)后按 compo-knowledge「版本更新重跑」执行;
3. 缓冲期内是否安排实机跑局、跑局用什么策略知识,与用户对齐。

**最易漏项 = 万金油角色名单**(策略「恒囤名单」,常量 `CROSS_LINE_KEEP_NAMES`,单一源 = `strategies/impl/mandate_v1/protection.py`):数据依据 = `docs/game/currency_war/research/stage_transitions.md` Q1 表——重跑 = 用新版本帖重算三阶段统计 → 对照新旧「全程留用层」 → 更新常量并同步文档依据描述。凡从 `stage_transitions.md` 派生的其他策略立场常量同批重核。

**玩家 skill 玩法层同批同步**:知识层重跑收尾时,玩家 skill `sr-od-currency-war` 的三篇玩法文档(gameplay-basics / decision-guide / comps-codex)按新知识重新浓缩,否则玩家面拿到过期打法;同步义务登记在玩家 skill 的 `design/overview.md`。

### 4.5 挂账板交接

- 等实机取证/等用户裁定/等外部条件的适配欠账,登记 `.debug/progress/CW跨迭代挂账.md`(含凭据指针),不散落迭代文件;
- 条目闭环时当场销项;新战役开工时按当时活跃迭代把挂账立项进 dag 账本。

## 5. 已知坑

- **羁绊采集器要跟数据源走**:帖内 trait 条目结构带全所需字段;发现字段缺失先查帖子结构是否变更,别按旧流程重建「按羁绊逐个筛采」。
- **角色技能全文已在官方配置里**(含星级数值)——不需要外部 wiki 补技能描述;某条目 `skill_stars` 为空按缺数据上报,别脑补。
- **官方配置的 `trait_info_list` 是骨架**(layers/role_ids/simple_desc 恒空)——分层细节从帖子聚合补全,不从骨架读。
- **生成物内嵌的生成器路径指针**(`generated_by`/`GEN_CMD`)重跑时自动更新;手改生成物无意义。
- **`--check-only` 片段 vs config 对拍非零退出 = 生成段待重产/待接入的正常信号**,不是生成器坏了;先看 diff 分型(新角色/费用变/羁绊变)再重跑生成器、按标记整段替换。

## 边界

- 生成器怎么跑、数据在哪采的细节归 [data-collection.md](data-collection.md);阵容知识重跑方法归 [compo-knowledge.md](compo-knowledge.md);画面建档归 od-dev-screen-onboarding。
