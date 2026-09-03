# 圣杯任务强开条件方案(采集批前置,只出方案不改代码)

> 目的:实机采集圣杯任务相关画面(节点/入口/任务列表/完成态),但圣杯任务在常规流程中不易自然满足——本文给出「用代码强开」的候选方案供采集批执行。
> 术语:「圣杯任务」= 羁绊【命运圣杯】的「祈愿试炼」系统(代码建模名 `grail_quest`);本文两词混用时均指同一系统。
> 出处约定:全部注册表 id / 代码行号引 2026-09 工作区实态;机制仅存于外部史料、未在代码/实机验证的一律标「⚠️ 待实机核」。

---

## 1. 完整机制链

### 1.1 入口条件(游戏侧,谁触发 overlay)

| 条件 | 出处 |
|---|---|
| 羁绊定义:命运圣杯 = combat 类羁绊,tiers (2,3,4,5),「提供祈愿试炼,完成试炼以获得各种奖励。难度和奖励随羁绊等级提升。成员前/后台强度提高」 | `src/sr_od/application/currency_war/data/cw_factions.py:67-68` |
| 门槛 = 羁绊 L2「25% 前/后台强度。**开启首个祈愿试炼**」;L3=50%+第二试炼(出现诅咒试炼)、L4=100%+第三、L5=180%+最终 | `docs/game/currency_war/research/final_comps/final_grail_dual.md:110-113`(官方 layer 原文转录) |
| 成员(4 张牌):远坂凛 1 费 / 吉尔伽美什 2 费 / Saber 3 费 / Archer 5 费 | `data/cw_chars.py:108,112,131,158` |
| 星徽捷径:「命运圣杯星徽」= 装备者加入【命运圣杯】羁绊(+伤害增幅10%) | `data/cw_equipment_data.py:111` |
| 投资入口(拿到成员/星徽的正规途径):①PlazaAugment id=**211401**「命运圣杯星徽」金:获得1星徽+1远坂凛(`cw_invest_data.py:167`);②PlazaPortal id=**1120**「命运圣杯邀请」:获得1星徽(`:450`);③PlazaPortal id=**1202**「命运圣杯契约」:获得远坂凛+吉尔伽美什,**完成两次圣杯试炼后获得 Archer**(`:452`);④棱彩 augment id=**352801**「都是这家伙的错!」:获得星徽+10金,战斗条件回退出售星徽角色×3 次(`:360`) |
| overlay 触发时机:特定节点前自动弹出(实测见过「再临仪式-二」「遭遇战」前),叠在备战上挡备战分支 | `docs/game/screens/currency_war_wish_trial.md:11,15`;`operations/handlers/handle_wish_trial.py:7-9` |
| 进度计数约束(⚠️ 史料级待实机核):任务进度只在对应羁绊等级激活时才计数,「未激活→做了不算」——2 件上场只开 L2 任务,4 件才开 L4 任务的账 | `final_grail_dual.md:115-117` |

结论:**强开的最小自然触发组合 = 上场/备战凑足 2 个命运圣杯成员(或 1 星徽)→ 羁绊 L2 → 走到触发节点(再临仪式-二/遭遇战类)→ overlay 自动弹**。1 费+2 费两件 ≈ 3 金,门槛是全游戏最低档之一。

### 1.2 任务列表结构(overlay 长什么样)

- 节点级 quest 选择 overlay:出现时给 **2~3 张试炼卡**(实测 2 张,候选数随节点变),每张卡 = 1 个 objective + 奖励文本(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」→ 金币/阵营星徽)。
  出处:`handle_wish_trial.py:8,12`(CARD_XS=(660,960,1260), objective 文本带 y250-400)、`currency_war_wish_trial.md:15,32`。
- 试炼分族:L2 首试炼 / L3 诅咒试炼 / L4 第三 / L5 最终(`final_grail_dual.md:112-113`)——各档卡的 objective/奖励差异无结构化数据,**待实机核**。
- 任务进度面板(跨节点查看进度的 UI)代码与画面文档均无记录,**待实机核**(可能不存在独立面板,进度只在 overlay/羁绊详情显示)。

### 1.3 完成态判定

- bot 侧现有判定**只有一层**:「确认选择」点击后 `标识-祈愿试炼` area 消失 = overlay 关 = 选择落地(`handle_wish_trial.py:90-93`);screen_info 侧 `货币战争-祈愿试炼` 共 3 个 area(标识-祈愿试炼 id_mark / 按钮-确认选择 / 备战标识-购买经验,见 `get_screen_detail('货币战争-祈愿试炼')`)。
- objective 在节点/战斗中完成的**游戏内完成提示/进度刷新画面无任何建模**——**待实机核**。
- 契约(id=1202)的「完成两次圣杯试炼」计数器无 UI/代码建模——**待实机核**。

### 1.4 奖励发放与联动

| 奖励 | 出处 |
|---|---|
| 试炼奖励 = 金币 / 阵营星徽 | `handle_wish_trial.py:8` |
| 契约终奖 = Archer(圣杯任务链产出,非商店购买;接棒 Saber) | `cw_invest_data.py:452`;`kernel/cw_comps.py:698-700`(`special_systems['grail_quest']`:{产出:Archer,触发:圣杯2档开任务}) |
| 难度联动:**圣杯试炼 +30 敌方难度**(resolve_difficulty R18:「+ 特殊(…圣杯试炼 +30)」) | `cw3/knowledge/resolver.py:452-455` |
| 代码建模面:`special_systems['grail_quest']`(`cw_comps.py:139` 注册、`:698-700` Archer 线、`:880-882` Saber 线);插件「圣杯2」T3 队员口径(`kernel/cw_plugins.py:117-121`);R19 通道 CHANNEL_TASK='task' → E5 定价,**登记位空**(供给三缺之一,`resolver.py:482`);策略打分 wish_gold=25/wish_faction=20/wish_operation=10(`decision/decision_v2/scoring.py:1145-1148`)→ `decide_wish_trial`(`decision/decision_v2/strategy.py:647-680`) |

### 1.5 ops 层现有进入路径(采集批要接的现有链路)

1. `kernel/cw_overlay_registry.py:111-122`:祈愿试炼 overlay spec(screen_name='货币战争-祈愿试炼', anchor='标识-祈愿试炼', handler=HandleWishTrial, dispatch_priority=11——必须排在道具详情(19)之前,防「聘用书」选项名截胡,r31 死循环实锤)。
2. `operations/battle_loop.py:1014-1019`(0h 分支):标识命中 → `_snap('wish_trial')` → 派发 HandleWishTrial;`:985-990` 祈愿屏排除条件。
3. `kernel/cw_prep_actions.py:182-184`:备战帧 event_overlay 检测(含祈愿试炼)→ BailToOuter 交外环。
4. `operations/prep/deploy_bench.py:237`:部署时也探祈愿屏标识(overlay 挡备战)。

---

## 2. 强开方案对比

**前置事实(定调)**:overlay 弹不弹由**游戏侧状态**决定,bot 代码没有任何「把 overlay 弹出来」的开关——「强开」只能:①让游戏条件被满足(定向凑圣杯 2 件),②画面出现时钉住/采集。两案都围绕这两点设计。

### 方案 A:改判定/选线函数直通

- **做法**:在 `cw_comps.py:select_comp_scored`(:1675)入口加临时白名单——候选只留「命运圣杯红A」(form_tiers 命运圣杯3,核心牌全圣杯族),让 select_comp/update_target/换线(`cw_line_switch.py:387` 同源候选集)全程锁定圣杯线;商店购买决策(candidates.py 候选打分)自然跟着 core_chars 优先买远坂凛(1费)/吉尔伽美什(2费)→ L2 尽早激活。
- **改哪行**:`cw_comps.py` select_comp_scored 函数体头部插 ~5 行过滤(或 candidates.py:278 邻域);不动 overlay 检测/HandleWishTrial。
- **影响面(大)**:①select_comp_scored 是策略主干单一实现(select_comp :1672 是它的投影,`cw_comps.py:1680-1681`),改动直接改变所有对局的选线行为——遥测、对局档案、后续 A/B 判读全部被污染;②圣杯线成型难度 medium + Archer 5 费依赖契约,**采集局大概率打不出正常对局价值**;③回归须跑策略全量测试锁。
- **回滚步骤**:git revert 单文件改动 → 重启 MCP server(改代码必须重启才生效,runtime-ops 铁律)→ 跑 `uv run pytest @sr-od-test/cw_quick.txt` 验绿。

### 方案 B:测试/采集钩子(按 AGENTS.local 随机态钩子规范:钩子临时加、采完删整段、禁留开关参数)

三件临时钩子,互不依赖,可只挂 B1+B2 先行:

- **B1 钉屏停机钩子**(采集主画面):`battle_loop.py` 0h 分支(:1018 标识命中后、HandleWishTrial 派发前)插入临时段——`self._snap('grail_collect')` 连拍数帧 + 写 flag(`.debug/temp/currency_war/grail_collect.flag`,内容=三要素:触发画面/时间/分支)→ 直调 `self.ctx.run_context.stop_running()` → `return self.round_wait(...)`(不点击,overlay 原样保持)。AI 侧按 od-dev-stop-hooks 现场协议:离线 `analyze_screen` + 视觉建档 → 删整段钩子 → 重启 MCP server → relaunch。
- **B2 被动采集钩子**(收瞬时态/完成态):`prep_director` 观察帧挂 `cw_shot_unique`(内容哈希去重,产物落 `.debug/temp/currency_war/shots/`,data-collection.md §三惯例)——bot 继续跑,自动收「任务完成提示/奖励弹窗/契约计数」等一闪而过的帧。完成态何时出现无建模(§1.3 待实机核),哈希去重保证不漏不重。
- **B3 定向辅助钩子**(提高触发率,可选):在 `cw_line_switch.py` 候选过滤(:375-387 邻域)或 select_comp_scored 入口插**带「采完删」注释的临时短段**,与方案 A 同一过滤逻辑但仅作用于采集局——本质是 A 的钩子化。差异在生命周期:A 是真改主干,B3 是临时段,删掉即还原,无 git revert、无测试锁纠缠。
- **影响面(小)**:B1/B2 零行为改变(纯观察);B3 只在采集局存在。产物统一落 `.debug/temp/currency_war/`(data-collection.md §钩子统一使用)。
- **回滚步骤**:删除钩子整段 → 重启 MCP server → 删/归档 shots。

### 推荐:**方案 B(B1+B2 必挂,B3 视触发率决定)**

理由:①采集目标是**画面**不是对局质量,方案 A 为触发画面污染整个策略主干,代价收益倒挂;②AGENTS.local 钩子规范明确「临时改配置/环境要回滚、钩子采完删整段」,B 的生命周期天然合规;③触发条件本身很低(3 金两件套),B3 大概率都用不上——先用 B1+B2 跑一两局看自然触发率,不够再加 B3;④A 需要动 select_comp 单一实现并过全量策略测试锁,采集批不该背这个验证成本。

---

## 3. 采集清单(强开后要拍什么,与既有 screen_info 的关系)

### 3.1 新增画面建档(od-dev-screen-onboarding 流程)

| 序 | 画面 | 采法 | 备注 |
|---|---|---|---|
| 1 | 祈愿试炼-选中态(卡金框+确认选择亮) | B1 钉屏后手动/脚本点卡再拍 | 与 §3.2 补 area 同帧可采 |
| 2 | 试炼卡 objective/奖励 tooltip(若有详情展开) | B1 钉屏期间探索点击 | 是否存在待实机核 |
| 3 | L3 诅咒试炼 overlay(与 L2 首试炼的差异帧) | cw_shot_unique 哈希去重自动收 | 需圣杯 3 档,触发门槛更高 |
| 4 | 任务完成提示/进度刷新帧 | B2 被动收 | 出现时机待实机核 |
| 5 | 奖励发放帧(金币/星徽到手弹窗) | B2 被动收 | 与现有 `cw_reward` 六边形钩子产物区分前缀 |
| 6 | 契约(1202)进度计数帧(「完成两次圣杯试炼」显示) | B2 被动收;拿到契约后每试炼完成各拍 | UI 形态待实机核 |
| 7 | 契约终奖发放帧(Archer 入队) | B2 被动收 | 依赖「两次试炼」全流程,采集局未必达成,标注尽力采 |

### 3.2 既有画面补 area(走 MCP upsert_screen_area,坐标单一真相源)

- `货币战争-祈愿试炼`(screen_id=currency_war_wish_trial,现 3 area):补 **试炼卡 1/2/3 body**(现 handler 硬编码 `CARD_XS=(660,960,1260), CARD_Y=340`,`handle_wish_trial.py:29-34`——正好借采集把硬编码坐标落成 area,消一处坐标单源违规)+ **objective 文本带**(y≈250-400)。
- 备战/羁绊详情屏:命运圣杯羁绊等级图标(L2-L5 激活态)如存在独立区域,补 area——是否可交互展示待实机核。

---

## 4. 风险与边界

| 风险 | 机制 | 缓解 |
|---|---|---|
| **对局数据污染** | 圣杯试炼 +30 敌方难度(`resolver.py:455`)→ 采集局难度被抬、战绩不可比;`record_event_choice('wish_trial')`(`handle_wish_trial.py:81`)会落遥测账本 | 采集局 game_id 单独登记,判读/复盘/A-B 一律排除;采集批结束在进度账本记隔离标记 |
| **卡死/长局** | 局33 祈愿崩 553 iter、局29 41min(`battle_loop.py:738` 实锤);overlay ESC 不关(`handle_wish_trial.py:11`) | 起采集局前武装哨兵三件(runtime-ops「哨兵脚本组」);B1 钉屏本身就是受控停机,不会死循环 |
| **备战被 overlay 挡 → 空场掉血** | live 2026-08-15 实锤(`cw_prep_actions.py:182-183`:盛会之星 overlay 下 deploy 全灭 HP 82→1) | 采集局允许;B1 钉屏=立即停机,不进战斗 |
| **B3 定向钩子副作用** | 过滤候选集会连带影响换线/ intentions 同源消费(`cw_line_switch.py:387`) | 只在确认 B1+B2 触发率不足才挂;钩子段内注释声明消费点与删留条件 |
| **机制连锁** | 契约(1202)完成两试炼发 Archer——强开试炼即是在推进契约线,可能提前改变阵容结构;「都是这家伙的错!」(352801)会因战斗未完美通关被触发出售星徽角色 | 采集局不选这两个 augment/portal 即可隔离;选了也无害(只是数据更脏,已在隔离名单) |
| **恢复正常流程** | 钩子残留 = 常驻污染 | 收口三步:①删 B1/B2/B3 钩子整段(不留开关/flag/参数,AGENTS.local 规范);②重启 MCP server(改代码重启才生效);③shots/flag 按需归档或删,`.debug/temp/currency_war/` 不留活钩子产物。若 MCP server 仍有运行中对局,先局终再重启(r99 守卫) |

---

## 附:本文未决项汇总(全部待实机核,采集批优先验证)

1. 任务进度「对应羁绊等级激活才计数」约束(§1.1,final_grail_dual 史料级);
2. 任务完成提示/进度面板的 UI 形态与出现时机(§1.3、采集清单 #4/#6);
3. L3/L4/L5 各档试炼卡的 objective/奖励差异(§1.2);
4. 契约(1202)计数器 UI(§1.3)。
