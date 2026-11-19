---
name: sr-od-dev-currency-war
description: 当在 StarRailOneDragon 仓库开发/维护/自主推进货币战争(Currency War,app_id `currency_war`)自动化时用——改策略代码、判读遥测与对局数据、单局深度复盘/复盘模板维护、跑实机局、修运行 bug、迭代算法、维护 CW 文档/ADR 都算,即使没明说。凡是碰 `src/sr_od/application/currency_war/`、`docs/*/currency_war/`、cw_sim 模拟、CW 遥测判读的工作都用本 skill。新玩法从零搭建走 od-dev-write-application,通用任务账本/钩子/画面建档走对应 od-dev-* skill,本 skill 只管已存在的货币战争。
---

# 货币战争开发·维护·自主推进

> 读者 = 无会话历史的干净智能体。本 skill 是 CW 的操作手册:先建立代码架构认知(§1),再按当次任务定位主场与该走的门,门指向各域 references 的主线——没走完主线不算完成。正文只留每轮要锚定的判据;细则按节下沉 `references/`(按需读)。

## 1. 代码架构(先建立整体认知)

图 A 术语:game state 每字段三态——**观察态**(实读值)/ **逻辑态**(动作执行后按游戏规则推算的预期值)/ **未观察**;**帧** = 一次截取画面并做一轮决策的时点;**对账** = 推算的预期值与下一帧实读逐项比对,对不上 = 有 bug。

### 1.1 一局怎么跑(图 A:主数据流)

```text
                 ┌───────────────────────────────────────┐
                 │ 入口编排层                             │
                 │ currency_war_app  应用组装·单跑道     │
                 │ cw_entry/*   入局·恢复·位面情报      │
                 │ cw_loop      对局循环·看门狗·重派防线│
                 └───────────────────────────────────────┘
                                      │ 按节点类型分发画面 op
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 画面 op 层(operations/cw_screen,一画面一 op;自身也是循环)             │
│ 每轮四步:观察(读屏+上报)→决策(调策略器)→执行(调动作 op)→上报       │
│ 画面族:备战·商店·战斗等待·伙伴·遭遇·投资·补给·结算·位面·弹窗 │
│                                                                       │
│ 观察解析工具箱(obs/,一屏一解析器):                                    │
│ 备战读数·节点选项·结算·简报·商店账目·角色SIFT·多源仲裁·恢复锁…│
│ recognizers/* 读数实现与 MCP agent 共用(双消费面,见图 B)              │
└──────────────────────────────────────────────────────────────────────┘
        ┬                                                 ┬
          ① 观察态上报(观察边界)                                     ③ 调动作 op 执行
        ▼                                                 │
┌───────────────────────────────┐                         │
│ game state 内核(kernel/)       │                          │
│ GameState 状态容器             │                            │
│ (观察态/逻辑态/未观察 三态)    │                                   │
│ apply_* 单一转移函数族         │                               │
│ cw_reconcile 观察边界对账·锚定│                                 │
│ 领域模型族(经济/阵容/意向/     │                                   │
│ 事件/装备/合成/注册表…)       │                                  │
└──┬────────────┬───────────────┘                         │
   │             ▼ ② 策略消费口(唯一)                            │
   │             ┌──────────────────────────────────┐     │
   │             │ 策略层(strategies/impl/mandate_v1)│       │
   │             │ 读 game state、产出动作提案;      │            │
   │             │ 判据 criteria/状态函数 statefn/   │          │
   │             │ 跨段状态记忆 mandate_state        │          │
   │             └───────────────┬──────────────────┘     │
   │                             │                        │
   │                             │ ③ 动作提案                 │
   │                             │                        │
   │                             │                        │
   │ ④ 动作上报(apply_* 直写)          ▼                        ▼
   └───────────────────────────────►┌───────────────────────────────┐
                                    │ 动作 op 层(operations/cw_op)   │
                                    │ 域耦合执行器(领域 param+env):  │
                                    │ 买/卖/升/刷/关店/开卡/装备/编排│
                                    └───────────────────────────────┘
                                                    │ 组合复用
                                                    ▼
                                    ┌────────────────────────────┐
                                    │ 动作原语(operations/actions)│
                                    │ 纯动作:点击/拖拽/固定序列;  │
                                    │ 零判效·零决策·简单参数,   │
                                    │ MCP 可直调(与 flow 层共用)  │
                                    └────────────────────────────┘
                                                      ⑤ 执行(点击/拖拽)
                                                    ▼
                                    ┌───────────────┐
                                    │ 环境:真机画面 /│
                                    │ sim 模拟画面   │
                                    └───────────────┘
画面变化 → 回到画面 op ①(再观察),循环到局终
```

**逐线读图**(重建拓扑以此表为准,图为辅助):

| 线 | 起点 → 终点 | 语义 |
|---|---|---|
| 分发 | cw_loop → 画面 op | 对局主循环按当前节点类型(遭遇/商店/投资/补给…)派发对应画面 op(一画面一 op) |
| ① | 画面 op → game state | 读屏解析(经 obs/),把实读值写进观察态 |
| ② | game state → 策略层 | 策略唯一消费口:策略只读 game state,不读屏、不点鼠标 |
| ③ | 策略层 → 画面 op → 动作 op | 策略产出动作提案交画面 op;画面 op 调用动作 op 执行 |
| ④ | 动作 op → game state | 动作上报:经 apply_* 函数族写入逻辑态;动作 op 不自己记账 |
| ⑤ | 动作 op(经 actions 原语)→ 环境 | 执行点击/拖拽,作用于真机画面或 sim 模拟画面 |
| 回环 | 环境 → 画面 op | 画面变化后再观察,循环到局终 |

### 1.2 各层职责

| 层 | 位置 | 职责 |
|---|---|---|
| 入口编排 | `currency_war_app` / `operations/cw_entry` / `cw_loop` | 应用组装、入局与中断局的恢复接管、对局主循环与看门狗 |
| 画面 op | `operations/cw_screen`(一画面一 op) | 该画面的识别、交互、观察上报、调动作 op;自身是「观察→决策→执行→上报」循环 |
| 动作 op | `operations/cw_op` | 动作提案的执行器:理解动作语义(带领域参数与局内状态),执行并上报;机械部分组合 actions 原语 |
| 动作原语 | `operations/actions` | 纯动作(点击/拖拽/固定序列),不做判定不做决策;flow 层与 MCP agent 共用(纪律见 §1.4) |
| 策略 | `strategies/impl/mandate_v1` | 读 game state、产出动作提案;量化判据(criteria)与状态函数(statefn) |
| 内核 | `kernel/` | GameState 状态容器 + 经济/阵容/装备等领域纯函数 |
| 观察 | `obs/`(一屏一解析器 + `recognizers/`) | 读屏解析;识别器注册为 MCP extras(§1.4) |
| 数据 | `data/` | 注册表(角色/羁绊/装备/投资/主角光环/敌情),官方 API 口径镜像 |
| 模拟 | `sim/` | 单局模拟器,充当游戏后端:只模拟环境,不评判策略 |
| 遥测 | `telemetry/` | run 生命周期、状态流水、对局档案 |
| 知识 | `knowledge/` | 引擎与阵容线的事实常量(玩法知识的代码消费形态) |

### 1.3 铁律(改代码前必须成立的不变量)

- game state 是局内状态唯一容器,每字段三态:观察态 / 逻辑态 / 未观察;
- 逻辑态写入独占:只有 `apply_*` 函数族写(动作 op 只上报动作);
- 策略消费口唯一:策略器只从 game state 读;
- 对账只在观察边界(`cw_reconcile`):推算预期 vs 下一帧实读,对不上 = 有 bug;
- sim 局与实机局跑同一套循环/op/策略,只换环境;
- 决策控制分层:凡控制决策行为的闸门与判断(政策闸/动作放行/花金限制/值域过滤)必须在策略侧实现——流程侧(外循环/画面 op/动作执行)禁止任何形式的决策闸门,合法判断面仅限画面识别与路由、防 bug 守卫断言、失败治理与停机;流程侧出现「需要判断该不该放某个动作过」= 分层错误,修法 = 迁策略侧。

### 1.4 双消费面(图 B):一条龙与 MCP agent 共用底层件

extras = `analyze_screen` 对已建档画面的结构化读数扩展(工具返回的 extras 字段)。

```text
               analyze_screen:extras 读数
┌────────────┐                            ┌────────────────────┐
│ MCP agent   │  ────────────────────────►│ obs/recognizers 五族│
│ (经项目 MCP)│                              │ (与画面 op 观察同源)│
└────────────┘   run_operation:直调         └────────────────────┘
                 ─────────►┌──────────────────┐
                           │ actions/* 动作原语│
                           │ (零判效·零决策)  │
                           └──────────────────┘
回环:agent 执行后再 analyze_screen 观察对账(点击生效与否由调用方验证)
```

- **动作原语 `operations/actions/`**:动作 op 的纯动作部分抽出,构造参数只用 JSON 简单类型,可被 MCP `run_operation` 直接运行。三条纪律:**零判效**(点击后不验证生效,对账归调用方下一帧观察)、**零决策**(买哪张/选哪个/何时做归调用方,槽位/坐标/次数全为参数)、**读屏仅限动作本体的目标定位**(坐标默认从 screen_info 画面档静态解析;唯一例外拾晶矿:识别球→点球,识别即动作本体)。
- **参数面规范(全部动作原语迁移的目标形态)**:
  - ①固定槽位:传下标——商店牌固定 5、备战栏固定 9,坐标按 screen_info 槽位直算
  - ②半固定:传下标 + 槽位总数——后排布局随部署数重排(槽位家族 6/7/8/9),下标单独不可定位
  - ③动态元素:显式传 (cx,cy) + 语义参数(如确认/取消)——晶矿、合成浮层钮、装备栏条目等位置不固定的目标,坐标来自调用方当帧读数(extras/gs)
  - 名称字段(装备名/角色名)= 语义参数:可选传入,不参与定位与校验,仅决定 op 日志内容
  - 执行路径零 game state 依赖:gs 可选快路径全部拔除;参数缺失 = 参数校验显式报错(禁静默兜底)
  - 坐标新鲜度纪律归调用方:op 纯机械不做落点前校验;坐标须来自当帧读数,读完即用
  - 参数 dataclass 统一补 `from_dict`(run_operation JSON 通道构造要求);配套 gs 状态容器给实体记录坐标(策略层从 gs 取坐标传参的前提)
  - 迁移按 op 切迭代(每 op 所有牵涉面一次改净),流程 = 设计→review→实施→review 四角色子代理流水线;设计稿归 CW 设计文档区 changes/ 迭代目录
- **画面识别器 `obs/recognizers/`**:备战/开商店/结算/简报/投资策略五族注册为 `analyze_screen` 的 extras 扩展——MCP 读到的 extras 与画面 op 观察是同一份实现,不是两套。

## 2. 入口分诊(按当次任务定位;「门」=该任务的硬判据)

| 当次任务 | 主节(门) | 细则 |
|---|---|---|
| 改策略 / 迭代算法 | strategy-work 按流水线走:改前(判读上局→读文档→定位→设计)→开关落地→验证→单帧测试 | strategy-work |
| 改外循环(分发路由/轮次推进/循环结构/停机遥测钩子) | 改前必读 [references/flow/loop.md](references/flow/loop.md)(两阶段身份分发/备战进入序/循环上限规范;新增画面三处缺一不可 = 建档+处理器分支+CW_DISPATCH_SCREENS 登记) | flow/loop |
| 改画面 op / 观察解析(obs) | 改前必读 [references/flow/screen-op.md](references/flow/screen-op.md)(职责四段·node=1+N+策略器按需/唯一读屏点/观察上报;完整细则在 docs screens/,后续批次迁) | flow/screen-op |
| 改动作 op(cw_op)/ 上报函数族 | 改前必读 [references/flow/action-op.md](references/flow/action-op.md)(规范集:零验证/零重试/点完即写/零读屏/一动作一文件/坐标契约;全量清单与转移声明表) | flow/action-op |
| 改入口链 / 退出链 / 弹窗守卫族 | 改前必读 [references/flow/entry-exit.md](references/flow/entry-exit.md)(三层结构/退出分发序/A 类名单与停机位同源契约) | flow/entry-exit |
| 改守卫 / 停机闸 / 降级链 | 改前必读 [references/flow/guards.md](references/flow/guards.md)(重派网/未知兜底/停机闸处理流程/降级链表) | flow/guards |
| 改策略契约面 / 状态分离(session/StrategyState/GameState 分工) | 改前必读 [references/flow/strategy-contract.md](references/flow/strategy-contract.md)(四身份分离/17 接口/三条契约) | flow/strategy-contract |
| 判读一局 / 跨局对照 | telemetry-reading「判读流程」(步骤0=先取尺子:当期目标行判据) | telemetry-reading |
| 单局深度复盘 / 复盘模板修订 | match-review(粒度=外层循环画面op调用序,报告按画面章组织:0 观察+动作节+策略评价;判定尺=玩法文档+既有规范,算法自洽≠合格;产出含算法缺陷候选清单,落点=报告文末复盘者附加) | match-review |
| 起局 / 停局 / 监控 / 残局清理 | runtime-ops「启动与重启+局间交接序」 | runtime-ops |
| sim 批量 / A/B / 压测 / 改 sim 基建 | sim-testing「找问题三步+边界」(A/B 归 strategy-work「验证」) | sim-testing |
| 阵容知识提炼 / 修订 / 版本重跑 | compo-knowledge(证据三层;先读再动) | compo-knowledge |
| 阵容定义字段设计(Comp schema 新增/修订/评审) | comp-definition(两条定谳:①不抄攻略三阶段,按终局形态定义,时间过程归策略机制层;②角色靠深入游戏理解逐个敲定(统计只给候选),两层分离=文档层完全理解/实现层策略消费最小集;字段准入五判据;先读再动) | comp-definition |
| 游戏版本更新(CW 侧适配) | version-update 清单(判型/各域明细/换赛季战役组织;总流程归 sr-od-dev-version-update-adaptation) | version-update |
| 数据采集 / 版本重采 / 新字段建模 | §3单一源地图·数据行(权威序;生成器分层) | data-collection |
| 改用户配置字段(增/删/语义) | 改前必读 [references/config.md](references/config.md)(归属判据红线:用户会因个人目的想改它吗;转向轴四类×三档语义表) | config |
| 改状态容器(写入入口 / 上报函数 / 字段增删) | 改前必读 [references/game-state.md](references/game-state.md)(三种来源与对账 / 上报函数族形态 / 字段设计纪律) | game-state |
| 改状态流水 / 判读账本(行结构 / 渠道签名 / 版本号 / 落盘 / 寿命清理) | 改前必读 [references/journal.md](references/journal.md)(两种行型 / 签名字段面 / 单版本事务 / 三道闸滚动清理 / 常开装配) | journal |
| 自主推进(实机探索期:派实机探索 agent / 问题处置循环 / 窗口所有权) | 通用框架 = od-dev-agent-autonomous-mode(公共 skill,需求线流水线);CW 实机探索期运转细则+领域叠加件(核心面清单/共享资产枚举/串行模式映射)+策略迭代期最小定义(§6,时期切换种子) → autonomous-loop.md(编排者只调度与传话,不做技术判断) | autonomous-loop |
| ADR / as-built 维护 | §4文档同步 | — |
| 未命中任何行(任务不属上表) | 大概率非 CW 专属:按任务性质走对应公共 skill(写 op→od-dev-write-operation / 画面建档→od-dev-screen-onboarding / 排查运行失败→od-dev-debug-automation);确属 CW 但表中无行 → 先查 §3 单一源地图,仍定位不了 → 给分诊表补行 | — |

开发循环轮从分诊表进,走所属域的主线;分诊同时服务窄任务与新会话入口。会话开工的通用步(读进度账本/确认窗口/查钩子)与 commit 前的通用验证(ruff/全量测试)属项目级规范,在项目 AGENTS.md 类指令文件/公共 skill(od-dev-stop-hooks 等)承载,本 skill 不复述。

## 3. 单一源地图(知识在哪,别造第二源)

| 要什么 | 去哪 |
|---|---|
| **策略工作统一说明**(策略是什么与骨架/改前/开关落地/验证/单帧测试) | [references/strategy-work.md](references/strategy-work.md);改策略前的必读文档面(全目录+阅读顺序)→ `docs/game/currency_war/research/README.md`「策略相关文档」节 |
| **模拟测试说明**(sim 能信什么/测试手段/sim 测试角色/分诊与固化) | [references/sim-testing.md](references/sim-testing.md) |
| **CW 工具脚本**(数据采集生成器/哨兵组/复盘渲染/证明验算/calibration——全家住本 skill `scripts/`,usage 看各脚本 docstring) | `scripts/`(采集生成器 data-collection、哨兵 runtime-ops、渲染 match-review、证明 docs/develop/.../proofs/math_proofs.md 各行自带指针) |
| **测试分层**(L1 快速集 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` ≈2.5min/L2=L1+受影响域点名/L3 全量 `uv run pytest sr-od-test/ -m "not slow"` ≈3.5min 仅 commit 前;禁跳到实机试错,实机运行期=做便宜层的窗口) | 策略验证阶梯单一源 = strategy-work「验证」 |
| **实机局数据判读**(判读流程/查询工具/观察面全量/已知缺口) | [references/telemetry-reading.md](references/telemetry-reading.md) |
| **单局复盘协议**(局终深度复盘:粒度=外层循环画面op调用序,报告按画面章组织——每画面 op 一章,章内 0 观察+动作节×N+策略评价,报告由渲染器 skills/sr-od-dev-currency-war/scripts/replay_to_md.py 生成,复盘者填判定与文末复盘者附加;判定尺=玩法文档+既有规范,算法自洽≠合格;产出含算法缺陷候选;实机探索 agent 局终后由编排者按需派单执行,产出的缺陷候选交编排者按问题处置循环分诊=autonomous-loop §3) | [references/match-review.md](references/match-review.md) |
| **实机运维细则**(单跑道 MCP 一次一 run;**改代码必须重启 server 才生效且重启杀对局 → 改动集中到局间一次重启,局中不改**;重启/早停/残局清理/监控栈与哨兵;效率剖析与巡检阈值回填=「一局时间花在哪」的拆分方法与巡检阈值回填去向) | [references/runtime-ops.md](references/runtime-ops.md) |
| **自主推进模式运转框架**(开启/停止仪式/需求线流水线/资源闸门) | `od-dev-agent-autonomous-mode`(公共 skill);CW 实机探索期运转细则+领域叠加件+策略迭代期最小定义 = [references/autonomous-loop.md](references/autonomous-loop.md);进度账本规范见 od-dev-progress-tracking |
| 系统设计 as-built(为什么有 v2/架构/决策链/模块地图/边界)+ 设计 why | `docs/develop/sr_od/application/currency_war/strategy-docs/README.md`(分篇入口;判据权威 = strategy-docs 各编号篇 + math_proofs;决策 why 收敛于设计文档动机段与代码注释,decisions/ ADR 档案停用) |
| 单套阵容打法知识 | `docs/game/currency_war/research/final_comps/`(唯一源) |
| 阵容知识怎么提炼/修订/版本重跑 | [references/compo-knowledge.md](references/compo-knowledge.md)(证据三层+三笔账) |
| **阵容定义字段设计方法论**(字段准入判据/目标态快照原则/时间维度归属/名单多胞胎警惕) | [references/comp-definition.md](references/comp-definition.md) |
| 过渡阵容(引擎池/核心池/渐进路径) | `research/transition_combos.md` + `combo_methodology.md` + `transitions.md` |
| 游戏数据值(角色/羁绊/装备/概率) | 代码注册表 `cw_chars`/`cw_traits_data`/`cw_equipment`/`cw_shop_odds` 等——**值只在代码,data doc 只记「凭什么信」** |
| 数据怎么采集/版本更新重采/采集钩子盘点 | [references/data-collection.md](references/data-collection.md) |
| 版本更新后 CW 域要做哪些事(适配清单) | [references/version-update.md](references/version-update.md)(判型/各域明细/换赛季战役组织) |
| 外部攻略原文(版本冻结) | `docs/game/currency_war/sources/`(只带元数据头,原文不改) |
| 运行状态/焦点/待办 | `.debug/progress/` 根下的当前活跃迭代目录(未封存);账本规范单一源 = od-dev-progress-tracking(现行形态 = dag.jsonl 事件流,旧文法 `进度.md` 目录按其规则只读封存;CW 存量目录尚为旧文法,新登记事项往现行形态收敛)。**卫生纪律**:只放活状态(焦点/待办/判读结论),轮次叙事/过期记录切归档文件留指针 |
| **跨迭代挂账**(货币战争专用的待办文件:等实机取证 / 等用户裁定的家族议题 / 等外部条件 / 欠账导航——寿命超过单个迭代的事项) | `.debug/progress/CW跨迭代挂账.md`(全域唯一板;迭代内欠账留各迭代收尾清单,开工时按当时活跃迭代立项进 dag 账本) |

分层判据:**游戏改了它变 → game 侧;代码改了它变 → develop 侧;进度/踩坑 → 本地进度账本,一律不进共享文档。**

## 4. 文档同步(行为变更同步)

策略行为/权重/算法语义/config·screen_info·GameState 字段/实跑根因任一变更 → commit 前:
1. strategy as-built 正文更新语义(值只进代码,文档写语义+指常量名);
2. 代码注释引 ADR-NN(仅指既有 ADR;ADR 仅经用户命令创建,默认无)。

游戏知识变更(机制/阵容结论)进 `game/currency_war/research/` 对应篇(带证据分级),不进 develop;决策 why 当场记(实跑演进当场写进动机段/注释,攒了再补的成本远高于顺手写一条)。
