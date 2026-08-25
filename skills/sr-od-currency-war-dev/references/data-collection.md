# 游戏数据采集全景(来源/生成器/运行时钩子)

> SKILL.md §单一源地图 的数据侧展开。读者 = 智能体;适用于:查某个数据域从哪来、版本更新重采、盘点采集钩子。

## 总原则

- **权威序**:游戏内图鉴(数据银行)/plaza 官方 API > 米游社百科 > 社区攻略(多篇交叉才可用)。
- **铁律**:所有影响玩法的游戏数据/描述/效果一律存盘作参考,标来源(content_id/URL+版本)——策略代码以这些为地基,别引用了不落盘。
- **遇不懂的游戏知识先搜再写**:机制/数值/规则/上限不懂就先查米游社/wiki/图鉴核实 → 补进玩法 doc,别凭猜硬写——猜的机制进代码 = 假信号地基。
- **两层架构**:数据层(`*_data.py`/生成器产出,勿手编)+ 判断层(人维护,cw_factions 类别/cw_comps 评级等)——生成器写目标有白名单守卫,改注册表前先查 `tools/cw/` 是否有该文件的生成器。
- **版本更新**:重跑生成器看内建 diff(角色/投资/羁绊/装备/聚类/战力表全家,见 tools/cw/ 各脚本)→ diff 驱动复核。

## 一、plaza 官方 API 直采(免登录公开接口)

基址 `act-api-takumi.miyoushe.com/event/rpgcurrencywar/game`,header `x-rpc-currencywar-tourn: tourn`:

| 域 | 生成器(tools/cw/) | 产出 | 采集要点 |
|---|---|---|---|
| 角色 | `gen_plaza_chars.py` | `cw_chars_data.PLAZA_ROLES` + 每角色 md | config API;**同名多档各一条**(银狼 3/4/5 费);开拓者双形态按 id 映射(8009 欢愉/8007 记忆);`•`→`·` canon |
| 投资策略/环境 | `gen_plaza_invest.py` | `cw_invest_data`(334+83) | 数字 id 稳定主键;效果官方全文去富文本 |
| 羁绊 | `gen_factions.py` | `cw_factions_data`(tiers+roles) | 两跳:lineup/index 按羁绊筛采 trait_detail(采集器在 .debug,版本更新重跑)+ config 属性映射;effect_rich 自渲染(未知 property type 警告不静默) |
| 装备 | `gen_equip_registry.py` | `cw_equipment_data` | 优先级分层:骨架=plaza>图鉴>md 兜底;effect=图鉴 OCR>plaza 校正;recipes=plaza compose_list+图鉴 icon 反查交叉 |
| 实战阵容 | `gen_plaza_comps.py` | `cw_plaza_comps`+plaza_meta | lineup/index match_hard,过滤版本/KOL 沙盒/过期 → is_carry 聚类 |
| 战力表 | `gen_power_table.py` | `cw_power_table_data` | 同阵容源派生(形态×位面→篇数) |

## 二、游戏内图鉴实采(权威,需实机)

| 域 | 方式 | 要点 |
|---|---|---|
| 装备图鉴 | `harvest_equip_codex.py`(半自动 op) | 前置手动:数据银行→装备图鉴→点 tier tab;脚本点格→截图→OCR→翻页→0 新增停。⚠️ **必须与游戏同 Session 跑**(pyautogui 跨 session 找不到窗口) |
| boss 图鉴 | 用户截图批 → OCR → 人判 tag | `cw_enemy_data.BOSS_MECHANICS`(20);俗称→规范名映射(BOSS_NICKNAMES)用户核对 |
| 刷新概率表 | 实机 OCR | `cw_shop_odds.REFRESH_PROB`(Lv1-10×费,行和=100% 校验);入口=商店面板底部百分比条弹窗 |
| 牌池副本数 | 攻略+用户确认 | 1/2费=27、3-5费=9(非 3 倍数的版本档**弃用**——3合1 机制决定均 3 倍数,判据可复用) |

## 三、运行时自采(边跑边采)

| 域 | 机制 | 状态/删留条件 |
|---|---|---|
| **敌人词缀效果** | `HandleBriefing` 简报 OCR → `affix_effects_data` 自写 | 常驻:采新不覆盖旧(静态数据已有值更可信,divergent 只 log+截图待 review);写入不影响已加载内存(下轮 import 生效);人可直接编辑校准 |
| **节点奖励明细(基础奖励+连胜档金)** | `prep_director._probe_node_reward`:备战点六边形(商店按钮左)→截图(`cw_reward` 前缀)→ OCR 全文记 log(`[cw][reward-probe]` 行)→关弹窗 | **临时钩子(用户交办,采完删)**:capture-only;弹窗官方口径「每节点收入=基础+连胜+利息,连胜档 0-1/2-4/5/6+」已在样本中;判读入口=log 行+shots;`streak_gold`/`BASE_REWARD_GOLD` 现值与弹窗一致,残余目标=连胜各档**金额**干净真值表(替换 `_refresh_cap` 保守门) |
| **连胜档金真值(结算屏)** | `cw_settlement_obs`:连胜≥3 存整屏(`streak_gold_stN` 前缀) | **临时钩子,采齐删**:与上方六边形钩子同目标两路采集(结算屏「获得金币总览」分连胜行) |
| **未识别商店卡** | `shop.py` 停机钩子:全 unknown 且重读 2 帧不自愈 → 停机留画面 | 保留(真未知兜底:新版本新卡/非角色内容);触发时按调研档案排查序走(防抖自愈=瞬时帧) |
| **未识别节点图标** | `cw_node_reader` Hu 距离>阈值 → 裁图标存盘 | 版本前哨(新节点类型如扑满);判态用 HSV 三态非单特征(亮/暗 V 值有交叠) |

### 已定值的经济常量(采集→真值已闭环;记「凭什么信」)

| 常量 | 值的依据 | 残余缺口 |
|---|---|---|
| `streak_gold` 连胜档金 | 奖励弹窗 VLM 判读 + 六边形弹窗 OCR 复核 | 各档金额的独立复核(上方两钩子采齐后终验);**cw_sim:337 注释与 cw_economy 代码是两张表**(0-1→0 vs <2→1),哪张是真相未证 |
| `BASE_REWARD_GOLD` 节点基础奖励 | 弹窗实测恒 5 + 对账首轮→次轮子集中位 +1 双重支持(分轮次裁决) | ~~冲突~~ **已解决**:混轮中位 +5 是后期事件金拉高;残余=奖励球/节点事件金未入对账模型(sim 校准层候选) |
| `XP_TO_NEXT_LEVEL` 升级门槛 {3:4,4:6,5:20,6:40,7:52,8:72,9:84} | **用户口述门槛表 + telemetry XP 分母独立对拍一致**(ADR-0129;曾推翻旧「整级大金」错模型) | **lv1-2 门槛缺失**(表从 LV.3 起);lv7-9 档对拍样本少;版本更新需复核 |
| `XP_PER_BUY=4` / 单击价 | 用户口述+实测 | 商业间谍类折扣另算(效果层) |

## 四、派生/人判层

- 同费种类数 `DISTINCT_CARDS_PER_COST` 从 CHARACTERS **派生**(改注册表自动传导)。
- 合成图谱 `cw_synthesis`:图鉴「合成公式」OCR → **K7 图数学派生**(21 交叉确证+7 自配逻辑确证);孤立节点(如光能电池 0 交叉)标注待人工核实机理,不入图。
- 节点类型/连胜数的**读取**(非采集):节点行 `cw_node_reader`(HoughCircles+HSV+Hu+OCR);连胜 `parse_streak`(结算屏「连胜×N」前缀=方向,fixture 核实)——这些是观测层不是数据采集,别混。

## 五、建模增量层(API 给不了的人工属性)

官方 API 给的是**事实**(名字/效果原文/数值),策略消费不了原文——各实体在注册表里有人工建模的增量层。**建模方法论**:

### 方法论(怎么建一个增量属性)

1. **问「哪个决策消费它」再动手**:每个建模字段对应一个决策消费点(mechanics_fit/boss_fit/equip_fit/经济算账/星级目标…),没有消费点的属性不建——防止「为建模而建模」的装饰字段。
2. **效果原文 → 结构化数值,只收能进模型的**:经济效果按语义归位到具名字段(一次性 vs 每节点 vs 触发式分开;ADR-0142 曾把 9 条重复性效果错装 instant_gold,按原文归位修正)。战力类不进经济模型(走战力评估);反向激励的(损血换钱)只建档不进分。
3. **边界靠效果原文,不脑补**:仅建 API 文本明说的数值;歧义处标注释;异质效果(契约/时代/规则类环境)不硬塞一个维度,**待分类建模**而非硬建模。
4. **人判维度标注判断层身份**:category/评级/站位要求等是人的判断——判断层文件头反向标注「生成器不写本文件」,防被覆盖。
5. **对拍锚防漂移**:跨层字段(如 comp.plaza_carry 指向聚类 carry 名)让两层数据互相可校验;孤儿校验(overlay 引用 base 不存在的键 → import 即炸)。
6. **机制特例单独建模,不泛化**(如开拓者双形态按排归一、银狼升费多档):特例进注册表的机制字段/映射表,别把特例逻辑散进消费代码。

### 各实体增量清单(查「这字段哪来的/谁消费」)

| 实体 | 增量属性(人维护) | 消费点 |
|---|---|---|
| **投资策略/环境**(`cw_investments`) | `EconomyEffect` 27 字段(给金/免费刷/利息覆写/难度Δ/连胜倍率/合成触发族…,ADR-0131/0142/0205/0211 四轮);`PICK_VALUE`/`ENV_PICK_VALUE`/`SURVIVAL_PICKS` 选卡分;`ENV_CATEGORY` 七类+`ENV_FACTION` 阵营绑定 | decide_event 选卡/`_refresh_cost`/`_refresh_cap`/利息引擎/难度账本/env 亲和 |
| **角色**(`cw_chars`) | char_type/f 流派阵营两分/independent/开拓者形态映射(按排归一) | 部署站位/羁绊计数/压缩牌库 |
| **羁绊**(`cw_factions`) | category 四分类(combat/economy/support/independent)/tiers/note 人判注记 | 评分/成型判定/骨架派生 |
| **comp**(`cw_comps`) | 核心/弹性二分/form_tiers/key_equips(可重复)/countered_by_bosses/mechanic_attributes(词缀双向)/shared_chars(转型成本)/char_positions(comp 级站位覆盖)/LevelGoal 曲线(等级→动作+星目标) | select_comp/maybe_pivot/装备分配/mechanics_fit/boss_fit |
| **装备**(`cw_equipment_data`) | category 九类/stacking/recipes 多路/props 结构化数值 | 补给选择/合成/equip_fit |
| **plaza 派生**(`cw_plaza_comps`) | star3_by_cost(费用档星率→星级目标先验)/labels 节奏/craft_first/transition_pool | 星级目标/等级节奏/合成优先 |

## 钩子统一使用(产物路径与纪律;分工见 od-dev-stop-hooks)

**产物路径约定(CW 一切钩子运行时产物统一落点)**:`.debug/temp/currency_war/`——推导自项目两级约定(临时文件统一放项目根 `.debug/temp/` + 玩法工作区 `.debug/temp/<玩法>/`),新埋任何钩子的产物路径遵循同约定,别另开新根。

| 产物 | 落点 | 命名 | 消费入口 |
|---|---|---|---|
| 停机 flag+sentinel 截图 | `.debug/temp/currency_war/*.flag`(+同名截图) | flag 文件名 = 钩子标识;内容含 flag 三要素(见 od-dev-stop-hooks §2.2) | SKILL.md checklist 第 2 步 → od-dev-stop-hooks §1 现场协议 |
| 采集样本 | `.debug/temp/currency_war/shots/` | 前缀 = 数据域名(`cw_shot_unique` 内容哈希去重) | 本文件 §三 钩子清单 |
| 哨兵水位/状态 | `.debug/temp/currency_war/*.pos` 等 | 按哨兵脚本自定;重武前删旧水位 | runtime-ops 监控栈 |

**纪律**:

- **临时钩子必须带删留条件**(「采齐删/采完删」写进注释);处理流程:样本攒够 → 离线判读(OCR/VLM)→ 真值进注册表/常量 → **删钩子+删样本**(或改名存档);别让临时钩子变常驻。
- **停机 vs 采集分流**:bot 能继续推进但数据想要 → 采集(截图继续跑);bot 卡住无法推进 → 停机钩子(op 节点内检测目标态 → 存 sentinel(截图+flag)→ 直调 `run_context.stop_running()` → `return` 不点击保画面;作法细则见 od-dev-write-operation references/runtime-craft「钩子触发停 bot 留画面」)。全生命周期判据见 od-dev-stop-hooks。
- 长期存在的 `.flag` 可能是常驻兜底登记项(处置见 runtime-ops「常置 flag 处置」),别一律当临时残留。
