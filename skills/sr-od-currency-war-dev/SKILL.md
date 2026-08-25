---
name: sr-od-currency-war-dev
description: 当在 StarRailOneDragon 仓库开发/维护/自主推进货币战争(Currency War,app_id `currency_war`)自动化时用——改策略代码、判读遥测与对局数据、跑实机局、修运行 bug、迭代算法、维护 CW 文档/ADR 都算,即使没明说。凡是碰 `src/sr_od/application/currency_war/`、`docs/*/currency_war/`、cw_sim 模拟、CW 遥测判读的工作都用本 skill。新玩法从零搭建走 od-dev-gameplay-automation,通用任务树/钩子/画面建档走对应 od-dev-* skill,本 skill 只管已存在的货币战争。
---

# 货币战争开发·维护·自主推进

> 读者 = 无会话历史的干净智能体。本 skill 是 CW 的操作手册:知识在哪、按什么纪律改、用什么验证、实机怎么运维。**入口先分诊**(按当次任务定位主场与该走的门);开发循环轮**没做完 8 步不算完成**。正文只留每轮要锚定的判据;细则按节下沉 `references/`(按需读),决策依据在 `design/decisions/`。

## 入口分诊(按当次任务定位;「门」=该任务的硬判据)

| 当次任务 | 主节(门) | 细则 |
|---|---|---|
| 改策略 / 修 bug / 迭代算法(开发循环) | ☐ 必做 checklist(8 步完成门) | 按步骤链各节 |
| 出策略方案 / 策略分歧裁决 / 疑问该问谁 | §策略工作(统一处理链) | strategy-work |
| 判读一局 / 跨局对照 | §判读(前置三问硬门) | telemetry-reading |
| 起局 / 停局 / 监控 / 残局清理 | §实机运维(重启四步/重武三步/早停判据) | runtime-ops |
| sim 批量 / A/B / 压测 | §验证工作台(差异必须解释;代理语义自检) | verification |
| 阵容知识提炼 / 修订 / 版本重跑 | §阵容知识工程(证据三层) | compo-knowledge |
| 数据采集 / 版本重采 / 新字段建模 | §单一源地图·数据行(权威序;生成器分层) | data-collection |
| 自主推进(goal/schedule 消息 / worker 派发与交付验收 / 哨兵报警响应 / 对抗) | §goal/schedule 自我校准(提醒=按 prompt+当期并行度执行)+ §交付验收(7 条逐项核) | autonomous-loop |
| ADR / as-built 维护 | §文档同步(三同步) | — |

开发循环轮永远从 checklist 进(它内部已含判读/验证/同步各步);分诊主要服务窄任务与新会话入口。

## 必做 checklist(每轮开发循环)

1. ☐ **读进度树 + 确认运行前提**:`.debug/progress/` 根下的**当前活跃迭代目录**(未封存)的入口 `进度.md`(运行状态单一源,本 skill 的操作对象;结构规范=od-dev-progress-tracking §2.5)对齐当前焦点;会话起点再确认 CW app 在应用列表、游戏窗口有效。**必做**
2. ☐ **查钩子痕迹**:`.debug/temp/currency_war/*.flag` + 哨兵/后台通知——有停机 flag 先按 `od-dev-stop-hooks` 处理并删 flag,再继续(产物路径/命名/三类钩子统一约定见 references/data-collection.md「钩子统一使用」)。**必做**
3. ☐ **判读上局遥测**:CW 遥测 CLI(§判读)找**不合理**处;判读结论写进进度树再动代码——单局数据≠结论,跨局对照+声明数据边界。**必做**
4. ☐ **改策略前读文档**(判据单一源=strategy-work §3):user_playstyle 全文 + strategy 入口序 + 相关 as-built 篇 + 任务→文档路由表;**自创新层=偏离设计,停下问;重构优先于打补丁**。**必做**
5. ☐ **设计先行**:落点函数/影响消费点(含测试锁)/预期行为变化/验证法,写清再动代码——「现象→定位函数→改」缺设计层是常犯病。**必做**
6. ☐ **按反馈梯度验证**:ruff → 单帧锁测试 → 全量(**= `uv run pytest sr-od-test/` 根级,含根级 test_cw_*.py 旧锁;`sr-od-test/test/` 子目录不算全量**) → sim 批量对照+回放对拍 diff → 实机(§验证工作台)——**禁止跳到实机试错,禁止 sleep 等实机**。**必做**
7. ☐ **行为变更三同步**:ADR(why)+ strategy as-built 正文(语义)+ 代码注释引 ADR-NN——commit 前完成(§文档同步)。**必做**
8. ☐ **实机局判读锚点事前写**(预测什么会变),跑完核对;无信息量局按早停判据停(§实机运维)。**必做**

## 单一源地图(知识在哪,别造第二源)

| 要什么 | 去哪 |
|---|---|
| **策略工作统一说明**(思路/核心骨架/改前必做/验证/疑问三滤网) | [references/strategy-work.md](references/strategy-work.md) |
| **自主推进模式运转框架**(开启仪式/编排者-worker/审查分层/提醒网) | `od-dev-agent-autonomous-mode`(公共 skill);CW 的实机运维细节见本 skill「实机运维」节,进度结构见 od-dev-progress-tracking §2.5 |
| 人怎么玩(口述权威,改策略必读) | `docs/game/currency_war/research/user_playstyle.md` 全文 |
| 系统设计 as-built(为什么有 v2/架构/决策链/模块地图/边界)+ 设计 why | `docs/develop/currency_war/strategy/README.md` + 01-07 分篇 + `decisions/`(ADR;redesign.md 已砍除归档,ADR-0365) |
| 决策 why(一决策一文件) | `docs/develop/currency_war/decisions/`(INDEX + ADR-NNNN) |
| 单套 comp 打法知识 | `docs/game/currency_war/research/final_comps/`(唯一源) |
| 阵容知识怎么提炼/修订/版本重跑 | [references/compo-knowledge.md](references/compo-knowledge.md)(证据三层+三笔账) |
| 过渡阵容(引擎池/核心池/渐进路径) | `research/transition_combos.md` + `combo_methodology.md` + `transitions.md` |
| 游戏数据值(角色/羁绊/装备/概率) | 代码注册表 `cw_chars`/`cw_factions`/`cw_equipment`/`cw_shop_odds` 等——**值只在代码,data doc 只记「凭什么信」** |
| 数据怎么采集/版本更新重采/采集钩子盘点 | [references/data-collection.md](references/data-collection.md) |
| 外部攻略原文(版本冻结) | `docs/game/currency_war/sources/`(只带元数据头,原文不改) |
| 运行状态/焦点/待办 | `.debug/progress/` 根下的当前活跃迭代目录(未封存)入口 `进度.md`——多迭代三层结构(迭代目录→app→三池),规范=od-dev-progress-tracking §2.5。**卫生纪律**:只放活状态(焦点/待办/判读结论),轮次叙事/过期记录切归档文件留指针;单文件超 ~800 行即触发归档整理 |

分层判据:**游戏改了它变 → game 侧;代码改了它变 → develop 侧;进度/踩坑 → 本地进度树,一律不进共享文档。**

## 策略工作(统一入口:改策略/出方案/策略分歧/疑问分流)

策略是 CW 的核心环节。思路/核心骨架(数学期望·50 息律·双层目标·阵容结构判据)/改前必做(文档门·任务→文档路由)/策略特有验证纪律/疑问三滤网(先证后裁)——单一源 = **[references/strategy-work.md](references/strategy-work.md)**。

## 判读(遥测 CLI,数据判读同源)

**判读前置三问(硬门;答不出不判读)**:
1. **该位面的目标是什么?**——P1=[28] 双指标验收:**息基保住 × 形态白名单内**+过渡核心 2★([13] 成型停手线);出口金 ~50 是守息的表征**不是单指标验收**(单优化它会产出「金 92 板面弱」假达标);**HP 从来不是 P1 验收**([2] 可卖血/[18] hp=报警)——拿 HP 当验收=目标函数错。
2. **这局锁的什么线?**——四体系过渡(transitions 开局分级:拿到逆天投资策略才配锁直通线)or 直通终局线?锁直通却没直通条件=P1 板面零伤害引擎([27] 罚款吃满)。
3. **板面在不在白名单?**——power_baseline P1 形态表;不在表内的形态(如纯经济凑数位)不是「体系长成了」。

判读及策略任务的文档组合路由表 → `docs/game/currency_war/research/README.md`「任务路由」节。

```
uv run python -m sr_od.application.currency_war.cw_telemetry query --recent N [--run ID] --view rounds|supply|anomalies|hp|economy|all
```

- rounds=逐轮 hp/gold/买/board;supply=全波牌面 vs 购买;hp=掉血×板深;economy=金轨迹/滞留;anomalies=异常标记。
- **生产局秒级自检**:`cw_telemetry checks --recent 5`——逐局判栈(v2 栈跑 coldstart 检查,default 栈跳过),违规带 run_id 溯源;sim 批次侧等价物 = simulate_p1_batch 默认内嵌的 checks_violations。检查器自身由测试仓变异自检锁钉死(去门变异必须涌现违规)。
- 每局跑完**必做**局后判读:异常条目当场定位根因(查 log + supply),定位不了不准进下一局——异常跨局存活 = 回归在累积。
- 结论必须声明数据边界(如「基于进店帧,refresh 波不可见」);**别为复盘写一次性脚本**——新复盘需求 = 新视图/查询参数。
- 日志跨 run 累积(append+轮转,重启不销毁证据):查旧局按时间窗 grep;需关注行检索 `grep [cw!]`;格式标准单一源在 strategy/05 §6。
- 旧自主推进代码带 `# 未验证` 注释:进对应画面复审(重点补日志/截图让每步可观测)后删注释才能信——复审是义务不是可跳的。
- 数据侧纪律(**数据源注释 > 采样凑证**/数据治理五步/阵容三维/复盘观察面全量)→ [references/telemetry-reading.md](references/telemetry-reading.md)(维度清单/视图覆盖矩阵/保真位先行/已知缺口同在此)。

## 交付验收(自主推进收 worker 账时逐项核;方法论五面见 od-dev-agent-autonomous-mode「交付验收清单」节)

- [ ] 测试亲跑:按 worker 声明的层复现(L1/L3 命令见 §验证工作台)——「声称绿」不算
- [ ] 边界核:`git diff --stat` vs 任务书声明文件集;越界逐个判(并行期禁 add -A)
- [ ] 数字:CI+点估计+功效齐报(**禁「归零/不劣」措辞**);sim 批必报池指纹(跨日对照核指纹一致,旧锚数据标注不可比)
- [ ] 断言抽查:报告里的源码行号抽 3-5 个亲核——worker 论断=可推翻假设
- [ ] 耗时核:量测数字 vs 预期量级差 >3 倍=效率缺陷打回(先定位再交)
- [ ] 产物亲读:sim 批读 json 原始数据;实机批核 runs.jsonl result 字段
- [ ] 行为变更批:ADR/正文/注释三同步带了吗(没带=打回或记欠账)
- [ ] 泛化步:bug 修复类交付,「**同类还有吗**」的排查派了吗——没派=一行记账「为何不派」(金不足/idx/kwarg 四连实证,用户四次替我补此步);检查面已固化的引用即可(如五查)

## 验证工作台(反馈梯度,按成本升序)

分层验证:L1 快速集=`uv run pytest @sr-od-test/cw_quick.txt`(~3min,CW 域)/L2=L1+受影响域点名/L3 全量=`uv run pytest sr-od-test/`(~5min,**仅 commit 前一次**)。实机一局按数十分钟计,是**最后一步**;实机运行期间 = 做 1-4 的窗口,不是等结果:

1. **文档对照**(零成本):设计里预期是什么,行为偏离了哪条。
2. **sim 批量**(秒级):`cw_sim.py` 的 P1 批量入口(基线/对照显式 `pool='snapshot'`,跨日对照核池指纹一致),A/B 对照同参数分布(达标占比/败场≤2 占比/均值/方向建立率)。sim 是可深度挖掘的基建(真代码层同源+校准层可注入+实机 Δ 池重放):回放对拍/稀有态扫描/参数敏感度/经济对账——细则见 [references/verification.md](references/verification.md)。
3. **telemetry 跨局对照**(分钟):历史局同类证据聚合(如「配方满线局才过线」的跨局表)。
4. **单帧锁测试**(分钟):构造 GameState → 断言 decide_prep 输出,进 `sr-od-test/test/sr_od/app/currency_war/`。模拟发现的情况**固化成单帧锁**才算回归资产。
5. **实机**(局级):判读锚点事前写;验收 = 连续多局达标(以当期目标为准)。

**sim A/B 与多批并行的验收纪律**(符号先核/三窗/v1 同进程重跑/合流总验/残差逐层下移/单源直通/里程碑叙述/穷举式结论/校准层天花板/连环证伪)、**sim 压力测试官**、**模拟灵活使用与双批挖掘**、**实机暴露问题的分诊与回灌**(感知 bug vs 策略病,防线完全不同)——细则全在 [references/verification.md](references/verification.md)。

## 实机运维

- **单跑道**:MCP 一次一个 run;`run_standalone_app('currency_war')` 启动,`get_run_status` 查进度,`stop_run` 停(原生 MCP 工具经项目级 `.dsh/mcp.servers.yml` 挂载)。
- **改代码必须重启 MCP server 才生效,且重启杀对局** → 改动攒批、局中不改;对局状态(session)在内存,重启全丢,重启后首局 target 重选是已知断档,判读注意。**重启前四步确认**:① `git status` 干净(或仅剩声明过的挂起件);② 全量 pytest 0 failed;③ `check_game_window` is_win_valid=true(无效先 open_game);④ `analyze_screen` 确认在货币战争-大厅(不在则先按残局清理序回大厅)。
- **早停判据**(无信息量局,满足任一即 stop_run + 判读 + 修复 + 重启跑新局):① 形态死局(连续多轮板面无引擎件且店里有种子没买);② 验证已得(本轮要验证的行为已观察到,后续无新信息);③ 已知未修问题主导(局是旧代码跑的、修复已 commit 待加载);④ **重大修复待加载=无条件早停重开**(用户定调「对于有重大突破的,早停重开」——重大策略/战力修复 commit 后,在跑的旧代码局素材价值趋零,继续跑=验证延迟)。例外:对照局(AB 对拍)与终验局不适用。
- **残局清理序**(停局/崩局后回到大厅才能起新局;结算屏残留会让 app 启动死循环):**优先一键 op `ExitCurrencyWarMatch`(operations/entry/,经 `run_operation` 调用,支持全入口态——备战/战斗中含暂停 X/投资策略等 overlay/胜负结算/失败链,放弃+结算 3 页+回大厅一次完成)**;op 不可用时手动 ESC 链兜底:结算屏「继续挑战」→ 等自动战斗打完 → 备战态 ESC → 「放弃并结算」→ 失败页「下一步」×2 → 「返回货币战争」→ `analyze_screen` 确认精准命中**货币战争-大厅**。用 screen_info 的 area 名定位,不背坐标。
- **监控三层**(长时自主推进时):进程内哨兵 flag + 后台哨兵脚本(触发即 exit=推送)+ 定时轮询兜底——哨兵脚本组(cw_sentinel/cw_early_stop/cw_runs_gap)/武装命令口径/重武三步/试用期纪律见 [references/runtime-ops.md](references/runtime-ops.md);**哨兵报警消费协议**(exit=待验证事件,先判相关性再信内容)见 [references/autonomous-loop.md](references/autonomous-loop.md)。
- CW op 禁无条件 ESC(备战屏 ESC 弹中断挑战);画面疑问走 `analyze_screen` 先行(离线可用,传截图路径)。
- 判读与建档的运维侧纪律(**布局/坐标建档唯一终审=交互实锤**/**重启接管段遥测降权**/首局判读锚点模板/常置 flag 处置)→ [references/runtime-ops.md](references/runtime-ops.md)。

## 阵容知识工程(提炼/深读/修订/版本重跑)

**证据三层**(核心纪律,缺层即盲区):统计骨架(plaza API 聚类给主流/代表——单靠统计发现不了细节)× 逐篇细节(攻略帖全文精读给运营思路/时序/条件——必须逐个看)× 机制解释(游戏数据本体给「玩法为什么是这样」)——「为什么」成立才收编,机制不成立的高频做法标 [社区] 存疑。结论落点:final_comps 类文档(叙事)+ `cw_comps.py COMP_LIBRARY`(结构化字段)——两者非镜像,互不触发同步义务。用户口述与攻略冲突以口述为准。细则(提炼流程/单套修订/版本重跑/三笔账):[references/compo-knowledge.md](references/compo-knowledge.md)

## 派单规范(自主推进派 worker 时,prompt 必含的节)

子 agent 是干净上下文,相关文档在它世界里不存在——按批的类型带齐:

1. **前置阅读**(策略行为面批必含:worker/压测官/调研):相关 user_playstyle 条目/strategy 篇/ADR 路径(文档集同 checklist 步 4)。不带=它只能凭猜乱来,不合格派单。
2. **判据来源**(判定类批必含——产出物是判定/分档/取舍的):以效果/机制审查为主体(逐对象过决定资格的机制属性),统计量只作佐证列;倒置(统计主体+效果一句带过)=不合格派单。
3. **动作五查**(Action 新增/改动批必含):前置阅读节引「防坑清单·动作索引五查」条(见该节)。
4. **文档面**(行为变更批必含——会改策略行为/语义/权重/字段含义的):ADR+as-built 三同步的归属,本批自带或显式声明「归编排者后续批」,二选一缺省=自带(纯测试批可免;W50/W51 实证:不声明,文档欠账必堆回编排者)。

## 文档同步(行为变更三同步)

策略行为/权重/算法语义/config·screen_info·GameState 字段/实跑根因任一变更 → commit 前:
1. 加 ADR(`docs/develop/currency_war/decisions/00NN-<slug>.md`,arc42 格式;INDEX 追加;**Considered Options 栏最值钱**);
2. strategy as-built 正文更新语义(值只进代码,文档写语义+指常量名);
3. 代码注释引 ADR-NN。

游戏知识变更(机制/阵容结论)进 `game/currency_war/research/` 对应篇(带证据分级),不进 develop;**攒 ADR = 漂移**(实跑演进当场记,攒了再补的成本远高于顺手写一条)。

## 防坑清单(高频犯过的)

- **逐局打补丁陷阱**:连续多局每局修一个新卡点 = 发散信号(缺的是成型进度类的控制变量,不是又一个单点修)——连续 3 局以上不同根因时,停下做架构层反思(读 strategy/README 总览 + 三份文档),别修 r(N+1)。
- **测试锁锁旧行为**:改门/常量前 grep 全部消费点含测试断言——很多「不买/不做」断言是旧路径的副作用,不是真语义;预判行为变化清单,逐项判「意图内还是副作用」。
- **叙述≠证据**:「轨迹最佳」「修复链收敛」是故事;真证据 = sim 分布变化 + 锁断言 + 判读锚点事前预测事后核对。
- **生成器分层**:改注册表前查 `tools/cw/` 是否有该文件的生成器(`*_data.py` 数据层勿手编;判断层文件反向标注);改错层 = 被覆盖或双源。
- **新字段进 GameState 查三消费面**:策略(谁读它)/遥测(视图有没有)/**sim 代理**(sim 建没建)——曾见核心维读 deployed 而 sim 不建模 → 恒折扣 → sim 行为与实机分叉(ADR-0219/0233)。
- **新读点查写入端**(对称纪律):加任何「读 session/state 某字段」的代码前,grep 该字段的**写入端是否存在**——读不存在的字段 = 永远走兜底路径,与「字段恒空」同病。
- **局中卡死巡检 = 日志重复度,不是遥测新鲜度**:遥测只在结算落盘,备战卡死时 hp 视图恒旧——巡检必 grep 近 10 分钟日志,同特征行(「备战席已满」/同一警告)≥10 次且无 buy/deploy/出战 推进行 → 按卡死处理(停局+判读),**不得以「推进慢」合理化**。
- **修消费端前先验生产端点火**(ADR-0239,同型三轮修不好根因):给某字段加 fallback/修读链前,grep 运行期日志确认**生产路径执行过**——生产者不点火,修消费端全是安慰剂。配套:**跨天 append 日志的 grep 必须带日期锚点**(日志时间戳无日期,曾把昨日行当今日证据;用重启点行号/日期事件分隔)。
- **临时采集钩子会积压**:钩子必须带删留条件;盘点时查 `.debug/temp/currency_war/shots/` 前缀分布——样本攒够就离线判读→进真值→删钩子,别让临时变常置(详 references/data-collection.md)。
- **改完不验旧锁就提交**:提交前三步 = ①grep 消费点与锁值 ②ruff+直接影响测试 ③耦合模块全量一次通过(子集绿是伪安全)。
- **实机学费不复盘 = 重交学费**:实机定位的策略行为病只修代码、不回灌 sim 检查项/单帧锁 → 同类病下次仍靠实机暴露(数十分钟/局);感知/运行时 bug 则相反——归 fixture 帧锁/回放对拍/哨兵防线,别为它扩 sim(分诊判据见 verification.md「实机暴露问题的分诊与回灌」)。
- **动作索引五查**(W57 沉淀,idx 族四连坑反推;完整判据版见 `.debug/temp/currency_war/cw_dev/deep_read/W57_报告.md` §4):策略代码发射**动作对象列表**(Action)给执行层,新增/改动动作类型或发射点时必过:①带索引/槽位的字段,注释声明**坐标系**(状态 list 下标 / 画面物理槽位 / 识别序号)与取值时机(生成期快照 / 执行期现读);②动作会从被索引容器**删元素**的,构造「组内两笔引用同容器、前者先删」的最小反例走一遍执行序(删除即左移);③一个 decide 函数**拼接 ≥2 个源**的动作时,后源不得默认前源没动过容器;④**期望值校验类防线字段**(expect/锚定)合入时 grep 写入端——零写入=死防线,校验逻辑再全也是恒放行;⑤sim 与执行层对同一 Action 各有实现时**逐行对拍索引语义**——同式地错比单路错更隐蔽(两路一起偏,sim 检查项失明)。判定类批的派单 prompt 引本条。

## goal / schedule 自我校准(自主推进元纪律)

goal 轮醒来第一动作 = 过上方 8 步 checklist;schedule 提醒到达 = 按提醒 prompt + 当期并行度执行(goal/schedule 通用机制单一源 = od-dev-agent-autonomous-mode 事件驱动模式)。CW 专属编排细则(提醒网四角色提示词模板/AGENTS.local 候选/哨兵报警消费)→ [references/autonomous-loop.md](references/autonomous-loop.md);战役状态/判据单一源 = 进度树「当前状态」节。
