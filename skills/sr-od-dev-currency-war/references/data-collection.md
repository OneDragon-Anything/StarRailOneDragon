# 游戏数据采集全景(来源/生成器/运行时钩子)

> SKILL.md §单一源地图 的数据侧展开。读者 = 智能体;适用于:查某个数据域从哪来、版本更新重采、盘点采集钩子。

## 总原则

- **权威序**:游戏内图鉴(数据银行)/plaza 官方 API > 米游社百科 > 社区攻略(多篇交叉才可用)。
- **铁律**:所有影响玩法的游戏数据/描述/效果一律存盘作参考,标来源(content_id/URL+版本)——策略代码以这些为地基,别引用了不落盘。
- **遇不懂的游戏知识先搜再写**:机制/数值/规则/上限不懂就先查米游社/wiki/图鉴核实 → 补进玩法 doc,别凭猜硬写——猜的机制进代码 = 假信号地基。
- **两层架构**:数据层(`*_data.py`/生成器产出,勿手编)+ 判断层(人维护,cw_comps 评级/cw_investments 经济建模等)——生成器写目标有白名单守卫,改注册表前先查 skill scripts(`skills/sr-od-dev-currency-war/scripts/`)是否有该文件的生成器。
- **版本更新**:重跑生成器看内建 diff(角色/投资/羁绊/装备/聚类全家,见 skill scripts 各脚本)→ diff 驱动复核。

## 一、plaza 官方 API 直采(免登录公开接口)

基址 `act-api-takumi.miyoushe.com/event/rpgcurrencywar/game`,header `x-rpc-currencywar-tourn: tourn`:

| 域 | 生成器(skill scripts/) | 产出 | 采集要点 |
|---|---|---|---|
| 角色 | `gen_plaza_chars.py` | 四件落盘产物:注册表段片段(`.debug/game_data/currency_war/plaza/registry_chars_v<版本>.py`,两侧标记注释与 `cw_chars.py` 官方段标记逐字一致,版本更新按标记**整段替换**接入)+ 人读角色文档 + 立绘模板(`assets/template/currency_war/character_avatar/`,与主游同构命名)+ 掉出名单 diff 报告(`dropped_v<版本>.md`,分纯角色掉出/系统单位迁出两类,**掉出方向唯一出口**);对拍显式传参 `--check-only`(片段 vs config 快照逐字段,不一致**非零退出**;main 默认产段不跑对拍) | config API;**同名多档各一条**(星神★阿哈 4/5/7 费);`•`(U+2022)→`·`(U+00B7) canon 归一(归一单一源),产出段名字含 • 直接报错 |
| 投资策略/环境 | `gen_plaza_invest.py` | `cw_invest_data`(298+73) | 数字 id 稳定主键;效果官方全文去富文本 |
| 羁绊 | `gen_traits.py` | `cw_traits_data`(29 条 `TRAITS` 按 trait_id + `trait_by_name` 按消费侧名;默认 dry-run 预览,`--land` 落库)+ 中间产物(traits_intermediate_v<版本>.json)+ 三源交叉/成员对拍报告(stdout) | 聚合生成器+对拍一体:官方 config 骨架过滤(trait_type 0/1/2=29 条基座,type 3 主角光环专属不进本域)→ 攻略广场 Hot 帖聚合(帖内 role_stages[].traits[] 为唯一全结构源;按 trait_id 分桶,去重 = layers 最多、并列取新帖,role_ids 跨帖并集)+ 富文本渲染 + role_ids→规范名翻译(查表契约 = 派生形态:运行期从角色注册表 CHARACTERS 派生映射,fail-closed)+ 成员对拍(官方 vs 注册表自报,差异逐条人裁)+ count_mode 判定表(带官方 desc 引文校验)+ wiki 交叉验证(27 词条,只出报告不落数据);任一对拍不一致非零退出 |
| 装备 | `gen_equip_registry.py` | `cw_equipment_data`(116 = 官方 105 + 配方链派生简易 11) | **v4.7 起 config 单源直灌**:官方分类名直落(七分类+派生简易装备)、desc 即效果全文、compose_list 即合成链、properties 即结构化属性;旧图鉴 OCR 校正链退役(三 wiki 停旧赛季不可作数值源) |
| 实战阵容 | `gen_plaza_comps.py` | `cw_plaza_comps`+plaza_meta | lineup/index match_hard,过滤版本/KOL 沙盒/过期 → is_carry 聚类 |

## 二、游戏内图鉴实采(权威,需实机)

| 域 | 方式 | 要点 |
|---|---|---|
| ~~装备图鉴~~ | `harvest_equip_codex.py`(半自动 op) | **v4.7 起免除**(config desc 即效果全文,实机 OCR 校正链退役;文件删留挂账)。历史形态:数据银行→装备图鉴→点 tier tab;脚本点格→截图→OCR→翻页→0 新增停。⚠️ 必须与游戏同 Session |
| boss 图鉴 | 用户截图批 → OCR → 人判 tag | `cw_enemy_data.BOSS_MECHANICS`(20);俗称→规范名映射(BOSS_NICKNAMES)用户核对 |
| 刷新概率表 | 实机 OCR | `cw_shop_odds.REFRESH_PROB`(Lv1-10×费,行和=100% 校验);入口=商店面板底部百分比条弹窗 |
| 牌池副本数 | 攻略+用户确认 | 1/2费=27、3-5费=9(非 3 倍数的版本档**弃用**——3合1 机制决定均 3 倍数,判据可复用) |

## 三、运行时自采(边跑边采)

| 域 | 机制 | 状态/删留条件 |
|---|---|---|
| **敌人词缀效果** | `HandleBriefing` 简报 OCR → `affix_effects_data` 自写 | 常驻:采新不覆盖旧(静态数据已有值更可信,divergent 只 log+截图待 review);写入不影响已加载内存(下轮 import 生效);人可直接编辑校准 |
| **节点奖励明细(基础奖励+连胜档金)** | `prep_director._probe_node_reward`:备战点六边形(商店按钮左)→截图(`cw_reward` 前缀)→ OCR 全文记 log(`[cw][reward-probe]` 行)→关弹窗 | **临时钩子(用户交办,采完删)**:capture-only;采集目标=位面 1 第 3-8 轮**基础奖励真值**(该段零弹窗样本;已采 7 帧=1-1=3、1-2=4、1-9=5、2-1×4=5,判读见 `docs/game/currency_war/research/economy.md` 实测表),连胜各档**金额**真值表仍为残余目标;判读入口=log 行+shots;采完钩子整段删除、本行一并清理 |
| **连胜档金真值(结算屏)** | `cw_settlement_obs`:连胜≥3 存整屏(`streak_gold_stN` 前缀) | **临时钩子,采齐删**:与上方六边形钩子同目标两路采集(结算屏「获得金币总览」分连胜行) |
| **未识别商店卡** | `shop.py` 停机钩子:全 unknown 且重读 2 帧不自愈 → 停机留画面 | 保留(真未知兜底:新版本新卡/非角色内容);触发时按调研档案排查序走(防抖自愈=瞬时帧) |
| **未识别节点图标** | `cw_node_reader` Hu 距离>阈值 → 裁图标存盘 | 版本前哨(新节点类型如扑满);判态用 HSV 三态非单特征(亮/暗 V 值有交叠) |

### 已定值的经济常量(采集→真值已闭环;记「凭什么信」)

| 常量 | 值的依据 | 残余缺口 |
|---|---|---|
| `streak_gold` 连胜档金 | 奖励弹窗 VLM 判读 + 六边形弹窗 OCR 复核 | 各档金额的独立复核(上方两钩子采齐后终验);~~cw_sim 注释与 cw_economy 双表冲突~~ **已消**:旧 cw_sim 行内陈旧注释(口述 0-1→0)已随单一源化删除,现行单一源 = `cw_economy.STREAK_GOLD_TABLE`/`streak_gold`(0-1→1/2-4→2/5→3/6+→4;49/49 样本,出处见该表 docstring 引 economy.md §10.1),sim 收入模型 import 同函数防漂移 |
| `BASE_REWARD_GOLD` 节点基础奖励 | 弹窗实测恒 5 + 对账首轮→次轮子集中位 +1 双重支持(分轮次裁决) | ~~冲突~~ **已解决**:混轮中位 +5 是后期事件金拉高;残余=晶矿/节点事件金未入对账模型(sim 校准层候选) |
| `XP_TO_NEXT_LEVEL` 升级门槛 {3:4,4:6,5:20,6:40,7:52,8:72,9:84} | **用户口述门槛表 + telemetry XP 分母独立交叉核对一致**(曾推翻旧「整级大金」错模型) | **lv1-2 门槛缺失**(表从 LV.3 起);lv7-9 档交叉核对样本少;版本更新需复核 |
| `XP_PER_BUY=4` / 单击价 | 用户口述+实测 | 商业间谍类折扣另算(效果层) |

## 四、派生/人判层

- 同费种类数 `DISTINCT_CARDS_PER_COST` 从 CHARACTERS **派生**(改注册表自动传导)。
- 合成图谱 `cw_synthesis`:从 `cw_equipment_data.EQUIPMENTS[].recipes`(官方 API compose_list)**import 期派生**(注册表改/重拉自动跟上,无手抄);不直接采集——采集入口是装备注册表生成器 `gen_equip_registry.py`。
- 节点类型/连胜数的**读取**(非采集):节点行 `cw_node_reader`(HoughCircles+HSV+Hu+OCR);连胜 `parse_streak`(结算屏「连胜×N」前缀=方向,fixture 核实)——这些是观测层不是数据采集,别混。

## 五、建模增量层(API 给不了的人工属性)

官方 API 给的是**事实**(名字/效果原文/数值),策略消费不了原文——各实体在注册表里有人工建模的增量层。**建模方法论**:

### 方法论(怎么建一个增量属性)

1. **问「哪个决策消费它」再动手**:每个建模字段对应一个决策消费点(mechanics_fit/boss_fit/equip_fit/经济算账/星级目标…),没有消费点的属性不建——防止「为建模而建模」的装饰字段。
2. **效果原文 → 结构化数值,只收能进模型的**:经济效果按语义归位到具名字段(一次性 vs 每节点 vs 触发式分开;曾把 9 条重复性效果错装 instant_gold,按原文归位修正)。战力类不进经济模型(走战力评估);反向激励的(损血换钱)只建档不进分。
3. **边界靠效果原文,不脑补**:仅建 API 文本明说的数值;歧义处标注释;异质效果(契约/时代/规则类环境)不硬塞一个维度,**待分类建模**而非硬建模。
4. **人判维度标注判断层身份**:category/评级/站位要求等是人的判断——判断层文件头反向标注「生成器不写本文件」,防被覆盖。
5. **交叉核对基准防漂移**:层间对账让两层数据互相可校验(对账形态 = 生成器末尾的差异报告,如 gen_plaza_comps 的「聚类 carry vs 手判 core[0]」——统计实证是校准证据,不进运行时字段;孤儿校验(overlay 引用 base 不存在的键 → import 即炸)。
6. **机制特例单独建模,不泛化**(如银狼升费变换窗、同名多档各一条):特例进注册表的机制字段/映射表,别把特例逻辑散进消费代码。

### 各实体增量清单(查「这字段哪来的/谁消费」)

| 实体 | 增量属性(人维护) | 消费点 |
|---|---|---|
| **投资策略/环境**(`cw_investments`) | `STRATEGY_ECONOMY`(EconomyEffect 45 字段:给金/免费刷/利息覆写/难度Δ/连胜倍率/合成与购买触发族…,字段三分 = 计分/待建模/不计)+ 卡级待建模登记 `STRATEGY_ECONOMY_PENDING_MODELING`;`STRATEGY_GRANTS` 策略卡具名发放(登记判据 = strategy-docs/29_invest_strategy_screen.md §2.3);`ENV_CATEGORY` 七类+`ENV_FACTION` 阵营绑定。选卡评序 = 策略层组件分(strategy-docs/29_invest_strategy_screen.md 与 28_invest_env_screen.md),本表不留选卡分 | 两屏选卡策略器(invest_strategy/invest_env)/`_refresh_cost`/`_refresh_cap`/利息引擎/难度账本/env 亲和 |
| **角色**(`cw_chars`) | 纯角色无人工增量字段——费用/站位/category_tags 多标签/羁绊三字段(factions+schools+independent)/is_expert/is_hide 全为官方镜像字段;人工维护面 = `SYSTEM_UNITS` 系统单位段(5 条,实机采集溯源,生成器不触碰) | 部署站位/羁绊计数/牌池与费段统计(`is_hide` 过滤由购买/概率语义消费方执行,数据层查询不过滤)/概率 v 值派生(`DISTINCT_CARDS_PER_COST`) |
| **羁绊**(`cw_traits_data`) | 无人工增量层——`TRAITS`/`trait_by_name` 为官方口径镜像(生成器产物勿手编);count_mode 激活计数控由生成器判定表固化(覆盖表带官方 desc 引文校验防漂移) | 激活档位判定(tiers)/成员关系派生(members)/评分与成型判定 |
| **comp**(`cw_comps`) | core/shared 名单二分/faction_reqs(羁绊要求优先级结构:档 0 核心、档 ≥1 加分层;原 form_tiers/sub_tiers 已合并)/flex_factions(弹性)/key_equips(可重复)/equip_assign(到人配方)/char_positions(comp 级站位覆盖)/need_star(星级目标;mechanic_attributes/countered_by_bosses 与 level_plan 曲线等评估字段已先后退役,git 可溯) | 线分/候选与锁定/成型判定/部署搜索/装备分配 |
| **装备**(`cw_equipment_data`) | category 九类/stacking/recipes 多路/props 结构化数值 | 补给选择/合成/equip_fit |
| **plaza 派生**(`cw_plaza_comps`) | star3_by_cost(费用档 3 星率,**客观频次仅校准交叉核对用**——费用档星目标启发式已废弃,星目标只认成型档显式要求;语义单一源 = `cw_plaza_comps` 模块注释)/labels 节奏/craft_first/transition_pool | 星级目标/等级节奏/合成优先 |

## 钩子统一使用(产物路径与纪律;分工见 od-dev-stop-hooks)

**产物路径约定(CW 钩子运行时产物统一落点)**:`.debug/temp/currency_war/`——推导自项目两级约定(临时文件统一放项目根 `.debug/temp/` + 玩法工作区 `.debug/temp/<玩法>/`),新埋任何钩子的产物路径遵循同约定,别另开新根。例外:**需跨会话/跨版本存活的数据类底稿**(攻略帖采集、精读笔记)落 `.debug/game_data/currency_war/`(拉取缓存统一落点,temp 清理不波及)。

| 产物 | 落点 | 命名 | 消费入口 |
|---|---|---|---|
| 停机 flag+sentinel 截图 | `.debug/temp/currency_war/*.flag`(+同名截图) | flag 文件名 = 钩子标识;内容含 flag 三要素(见 od-dev-stop-hooks §2.2) | od-dev-stop-hooks §1 现场协议 |
| 采集样本 | `.debug/temp/currency_war/shots/` | 前缀 = 数据域名(`cw_shot_unique` 内容哈希去重) | 本文件 §三 钩子清单 |
| 哨兵水位/状态 | `.debug/temp/currency_war/*.pos` 等 | 按哨兵脚本自定;重武前删旧水位 | runtime-ops 监控栈 |

**纪律**:

- **临时钩子必须带删留条件**(「采齐删/采完删」写进注释);处理流程:样本攒够 → 离线判读(OCR/VLM)→ 真值进注册表/常量 → **删钩子+删样本**(或改名存档);别让临时钩子变常驻。
- **停机 vs 采集分流**:bot 能继续推进但数据想要 → 采集(截图继续跑);bot 卡住无法推进 → 停机钩子(op 节点内检测目标态 → 存 sentinel(截图+flag)→ 直调 `run_context.stop_running()` → `return` 不点击保画面;作法细则见 od-dev-write-operation references/runtime-craft「钩子触发停 bot 留画面」)。全生命周期判据见 od-dev-stop-hooks。
- 长期存在的 `.flag` 可能是常驻兜底登记项(处置见 runtime-ops「常置 flag 处置」),别一律当临时残留。
