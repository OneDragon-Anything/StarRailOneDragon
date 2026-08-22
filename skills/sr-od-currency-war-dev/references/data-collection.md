# 游戏数据采集全景(来源/生成器/运行时钩子)

> SKILL.md §单一源地图 的数据侧展开。读者 = 智能体;适用于:查某个数据域从哪来、版本更新重采、盘点采集钩子。

## 总原则

- **权威序**:游戏内图鉴(数据银行)/plaza 官方 API > 米游社百科 > 社区攻略(多篇交叉才可用)。
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
| **连胜档金真值** | `cw_settlement_obs` 结算屏:连胜≥3 存整屏(`streak_gold_stN` 前缀) | **临时钩子,采齐删**:离线拆「连胜×N→连胜金」真值表后接 `_refresh_cap`;样本目录 `.debug/temp/currency_war/shots/streak_gold_*` |
| **节点奖励明细** | `prep_director._probe_node_reward`:备战点六边形(商店按钮左)→截图(`cw_reward` 前缀)→OCR→关弹窗 | **临时钩子(用户交办,采完删)**:capture-only 不解析;目的=看基础奖励会不会变,之后再接策略 |
| **未识别商店卡** | `shop.py` 停机钩子:全 unknown 且重读 2 帧不自愈 → 停机留画面 | 保留(真未知兜底:新版本新卡/非角色内容);触发时按调研档案排查序走(防抖自愈=瞬时帧) |
| **未识别节点图标** | `cw_node_reader` Hu 距离>阈值 → 裁图标存盘 | 版本前哨(新节点类型如扑满);采样实锤:亮/暗 V 值有交叠,判态用 HSV 三态非单特征 |

## 四、派生/人判层

- 同费种类数 `DISTINCT_CARDS_PER_COST` 从 CHARACTERS **派生**(改注册表自动传导)。
- 合成图谱 `cw_synthesis`:图鉴「合成公式」OCR → **K7 图数学派生**(21 交叉确证+7 自配逻辑确证);孤立节点(如光能电池 0 交叉)标注待人工核实机理,不入图。
- 节点类型/连胜数的**读取**(非采集):节点行 `cw_node_reader`(HoughCircles+HSV+Hu+OCR);连胜 `parse_streak`(结算屏「连胜×N」前缀=方向,fixture 核实)——这些是观测层不是数据采集,别混。

## 采集钩子纪律(与 od-dev-stop-hooks 分工)

- **临时采集钩子必须带删留条件**(「采齐删/采完删」写进注释);用 `cw_shot_unique`(内容哈希去重)存样本到 `.debug/temp/currency_war/shots/`,前缀即域名。
- **停机 vs 采集分流**:bot 能继续推进但数据想要 → 采集(截图继续跑);bot 卡住无法推进 → 停机钩子(方案 D)。全生命周期判据见 od-dev-stop-hooks。
- 处理流程:样本攒够 → 离线判读(OCR/VLM)→ 真值进注册表/常量 → **删钩子+删样本**(或改名存档);别让临时钩子变常驻。
