---
name: sr-od-currency-war-dev
description: 当在 StarRailOneDragon 仓库开发/维护/自主推进货币战争(Currency War,app_id `currency_war`)自动化时用——改策略代码、判读遥测与对局数据、跑实机局、修运行 bug、迭代算法、维护 CW 文档/ADR 都算,即使没明说。凡是碰 `src/sr_od/application/currency_war/`、`docs/*/currency_war/`、cw_sim 模拟、CW 遥测判读的工作都用本 skill。新玩法从零搭建走 od-dev-gameplay-automation,通用任务树/钩子/画面建档走对应 od-dev-* skill,本 skill 只管已存在的货币战争。
---

# 货币战争开发·维护·自主推进

> 读者 = 无会话历史的干净智能体。本 skill 是 CW 的操作手册:知识在哪、按什么纪律改、用什么验证、实机怎么运维。**没做完下面 8 步不算一轮完成。**

## 必做 checklist(每轮开发循环)

1. ☐ **读进度树 + 确认运行前提**:`.debug/temp/currency_war/cw_dev/进度.md`(运行时状态单一源,本 skill 的操作对象)对齐当前焦点;会话起点再确认 CW app 在应用列表、游戏窗口有效。**必做**
2. ☐ **查钩子痕迹**:`.debug/temp/currency_war/*.flag` + 哨兵/后台通知——有停机 flag 先按 `od-dev-stop-hooks` 处理并删 flag,再继续。**必做**
3. ☐ **判读上局遥测**:CW 遥测 CLI(§判读)找**不合理**处;判读结论写进进度树再动代码——单局数据≠结论,跨局对照+声明数据边界。**必做**
4. ☐ **改策略前读文档**:user_playstyle 全文 + strategy/README 入口序 + 相关 as-built 篇(§单一源地图)——回答「改动违反哪条既有原则/落在哪一层」。**必做**
5. ☐ **设计先行**:落点函数/影响消费点(含测试锁)/预期行为变化/验证法,写清再动代码——「现象→定位函数→改」缺设计层是常犯病。**必做**
6. ☐ **按反馈梯度验证**:ruff → 单帧锁测试 → 全量 → sim 批量对照 → 实机(§验证工作台)——**禁止跳到实机试错,禁止 sleep 等实机**。**必做**
7. ☐ **行为变更三同步**:ADR(why)+ strategy as-built 正文(语义)+ 代码注释引 ADR-NN——commit 前完成(§文档同步)。**必做**
8. ☐ **实机局判读锚点事前写**(预测什么会变),跑完核对;无信息量局按早停判据停(§实机运维)。**必做**

## 单一源地图(知识在哪,别造第二源)

| 要什么 | 去哪 |
|---|---|
| 人怎么玩(口述权威,改策略必读) | `docs/game/currency_war/research/user_playstyle.md` 全文 |
| 系统设计定稿(架构/数据层/决策循环) | `docs/develop/currency_war/redesign.md` |
| as-built 策略正文(结构/语义/边界) | `docs/develop/currency_war/strategy/README.md` + 01-07 分篇 |
| 决策 why(一决策一文件) | `docs/develop/currency_war/decisions/`(INDEX + ADR-NNNN) |
| 单套 comp 打法知识 | `docs/game/currency_war/research/final_comps/`(十类深读,唯一源) |
| 阵容知识怎么提炼/修订/版本重跑 | [references/compo-knowledge.md](references/compo-knowledge.md)(证据三层:统计骨架×逐篇细节×机制解释) |
| 过渡阵容(引擎池/核心池/渐进路径) | `research/transition_combos.md` + `combo_methodology.md` + `transitions.md` |
| 游戏数据值(角色/羁绊/装备/概率) | 代码注册表 `cw_chars`/`cw_factions`/`cw_equipment`/`cw_shop_odds` 等——**值只在代码,data doc 只记「凭什么信」** |
| 数据怎么采集/版本更新重采/采集钩子盘点 | [references/data-collection.md](references/data-collection.md)(plaza API 生成器族/图鉴实采/运行时自采——含连胜档金与节点奖励的临时采集钩子现状) |
| 外部攻略原文(版本冻结) | `docs/game/currency_war/sources/`(只带元数据头,原文不改) |
| 运行状态/焦点/待办 | `.debug/temp/currency_war/cw_dev/进度.md`(任务树,操作对象) |

分层判据:**游戏改了它变 → game 侧;代码改了它变 → develop 侧;进度/踩坑 → 本地进度树,一律不进共享文档。**

## 判读(遥测 CLI,数据判读同源)

```
uv run python -m sr_od.application.currency_war.cw_telemetry query --recent N [--run ID] --view rounds|supply|anomalies|hp|economy|all
```

- rounds=逐轮 hp/gold/买/board;supply=全波牌面 vs 购买;hp=掉血×板深;economy=金轨迹/滞留;anomalies=异常标记。
- **别为复盘写一次性脚本**——新复盘需求 = 新视图/查询参数;确需脚本用完即删。
- 每局跑完**必做**局后判读:异常条目当场定位根因(查 log + supply),定位不了不准进下一局——异常跨局存活 = 回归在累积。
- 结论必须声明数据边界(如「基于进店帧,refresh 波不可见」);边界不够先补遥测字段再下结论。
- 改动效果对照:改策略后下一局 `--recent 5` 并列对比(测试绿≠实跑行为对)。
- 日志跨 run 累积(append+轮转,重启不销毁证据):查旧局按时间窗 grep;需关注行检索 `grep [cw!]`(漏检/未建档/顺序异常);格式标准单一源在 strategy/05 §6。
- 旧自主推进代码带 `# 未验证` 注释:进对应画面复审(重点补日志/截图让每步可观测)后删注释才能信——复审是义务不是可跳的。
- **阵容质量 = 三维**(羁绊档位 × 角色构成 × 装备分配)——只看羁绊 = 空壳盲判(羁绊够但核心不在场/装备乱用都看不见;数据在 state.deployed[].star/equips 里,别被视图边界限制)。
- **复盘要全面,观察面是全量**(用户定调):站位/经验节奏/商店供给/投资策略环境等 32 个 GameState 字段各对应决策消费点——按 telemetry-reading 的观察面清单逐主题过,不是只看最显眼的维度;视图没显示的直查 jsonl,采集恒空的字段按缺口清单心里有数。
- 反例论据(为什么严):历届单点断层各自存活 3+ 局才被抓、把单帧牌面当全序列误判健康线弃线——详见 design/ ADR。

细则(维度清单/视图覆盖矩阵/保真位先行):[references/telemetry-reading.md](references/telemetry-reading.md)

## 验证工作台(反馈梯度,按成本升序)

实机一局按数十分钟计,是**最后一步**;实机运行期间 = 做 1-4 的窗口,不是等结果:

1. **文档对照**(零成本):设计里预期是什么,行为偏离了哪条。
2. **sim 批量**(秒级):`cw_sim.py` 的 P1 批量入口,A/B 对照同参数分布(hp≥验收线占比/均值/方向建立率)。sim 有粒度边界(见下),差异必须解释。
3. **telemetry 跨局对照**(分钟):历史局同类证据聚合(如「配方满线局才过线」的跨局表)。
4. **单帧锁测试**(分钟):构造 GameState → 断言 decide_prep 输出,进 `sr-od-test/test/sr_od/app/currency_war/`。模拟发现的情况**固化成单帧锁**才算回归资产。
5. **实机**(局级):判读锚点事前写;验收 = 连续多局达标(以当期目标为准)。

**sim 已知边界**:Δ池按深度分桶,±2 深度量级测不出;「散面 vs 集中」维度 sim 战斗层不敏感、可能与实机方向相反——此类维度以实机判读为准,并把偏差记录在案;「sim 上实机前必核代理语义」(曾因 bench 计数≠上阵的代理错位得出 1.8 倍增益伪影)。

细则(对照口径/单帧锁模板/判读锚点写法):[references/verification.md](references/verification.md)

## 实机运维

- **单跑道**:MCP 一次一个 run;`run_standalone_app('currency_war')` 启动,`get_run_status` 查进度,`stop_run` 停。
- **改代码必须重启 MCP server 才生效,且重启杀对局** → 改动攒批、局中不改;对局状态(session)在内存,重启全丢,重启后首局 target 重选是已知断档,判读注意。
- **早停判据**(无信息量局,满足任一即 stop_run + 判读 + 修复 + 重启跑新局):① 形态死局(连续多轮板面无引擎件且店里有种子没买);② 验证已得(本轮要验证的行为已观察到,后续无新信息);③ 已知未修问题主导(局是旧代码跑的、修复已 commit 待加载)。对照局(AB 对拍)与终验局不适用。
- **残局清理序**(停局/崩局后回到大厅才能起新局;结算屏残留会让 app 启动死循环):结算屏「继续挑战」→ 等自动战斗打完 → 备战态 ESC → 「放弃并结算」→ 失败页「下一步」×2 → 「返回货币战争」→ `analyze_screen` 确认精准命中**货币战争-大厅**。用 screen_info 的 area 名定位(按钮-继续挑战/按钮-放弃并结算/按钮-下一步),不背坐标。
- **监控三层**(长时自主推进时):进程内哨兵 flag + 后台哨兵脚本(触发即 exit=推送通知;重武前查旧实例,单实例纪律)+ 定时轮询兜底。用户要用电脑时全停实机。
- CW op 禁无条件 ESC(备战屏 ESC 弹中断挑战);画面疑问走 `analyze_screen` 先行(离线可用,传截图路径)。

细则(交接序/监控武装/常见运行坑):[references/runtime-ops.md](references/runtime-ops.md)

## 阵容知识工程(提炼/深读/修订/版本重跑)

**证据三层**(核心纪律,缺层即盲区):统计骨架(plaza API 聚类给主流/代表——**单靠统计发现不了细节**)× 逐篇细节(攻略帖全文精读给运营思路/时序/条件——必须逐个看,不能偷懒)× 机制解释(游戏数据本体:角色技能/羁绊/装备/投资策略·环境效果——**给「玩法为什么是这样」**)。工作流:统计给候选 → 逐篇读细节 → 游戏数据验证机制;「为什么」成立才收编,机制不成立的高频做法标 [社区] 存疑。

结论落点:final_comps 类文档(叙事)+ `cw_comps.py COMP_LIBRARY`(结构化字段)——两者非镜像,互不触发同步义务。用户口述与攻略冲突以口述为准。

细则(从零提炼流程/单套修订/版本更新重跑/防坑):[references/compo-knowledge.md](references/compo-knowledge.md)

## 文档同步(行为变更三同步)

策略行为/权重/算法语义/config·screen_info·GameState 字段/实跑根因任一变更 → commit 前:
1. 加 ADR(`docs/develop/currency_war/decisions/00NN-<slug>.md`,arc42 格式;INDEX 追加;**Considered Options 栏最值钱**);
2. strategy as-built 正文更新语义(值只进代码,文档写语义+指常量名);
3. 代码注释引 ADR-NN。

游戏知识变更(机制/阵容结论)进 `game/currency_war/research/` 对应篇(带证据分级),不进 develop;**攒 ADR = 漂移**(实跑演进当场记,攒了再补的成本远高于顺手写一条)。

## 防坑清单(高频犯过的)

- **逐局打补丁陷阱**:连续多局每局修一个新卡点 = 发散信号(缺的是成型进度类的控制变量,不是又一个单点修)——连续 3 局以上不同根因时,停下来做架构层反思(读 redesign + 三份文档),别修 r(N+1)。
- **测试锁锁旧行为**:改门/常量前 grep 全部消费点含测试断言——很多「不买/不做」断言是旧路径的副作用,不是真语义;预判行为变化清单,逐项判「意图内还是副作用」。
- **叙述≠证据**:「轨迹最佳」「修复链收敛」是故事;真证据 = sim 分布变化 + 锁断言 + 判读锚点事前预测事后核对。
- **生成器分层**:改注册表前查 `tools/cw/` 是否有该文件的生成器(`*_data.py` 数据层勿手编;判断层文件反向标注);改错层 = 被覆盖或双源。
- **临时采集钩子会积压**:钩子必须带删留条件;盘点时查 `.debug/temp/currency_war/shots/` 前缀分布与代码内「采完删」标记——样本攒够就离线判读→进真值→删钩子,别让临时变常驻(详 references/data-collection.md)。
- **改完不验旧锁就提交**:提交前三步 = ①grep 消费点与锁值 ②ruff+直接影响测试 ③耦合模块全量一次通过(子集绿是伪安全)。
