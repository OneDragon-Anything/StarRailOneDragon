# 策略遥测数据规范(DecisionRecord:信封 + mandate_v1 payload)

> 本篇是**策略遥测数据的语义正本**:策略器决策记录(信封 + 载荷)的键闭集、取值语义与判读注意。读者 = 判读遥测数据/复盘报告的工程师与智能体。
> 产生端 = 基类捕获缝(`kernel/strategies` 层,决策入口被自动包裹,见 `strategies/impl/cw_strategy.py` 模块头「策略遥测捕获缝」节);消费端 = 复盘渲染器(`tools/cw/replay_to_md.py --strategy-telemetry`,按需装配)。
> 术语:**帧** = 一次「观察画面 → 决策 → 发出一个动作」的循环时点(见 [README.md](README.md) 术语表);**决策入口** = `CwStrategy` 的 14 个零参 `decide_*` 抽象入口闭集。

## 1. 信封(envelope)键闭集

每个决策入口被包裹后,**单次调用恰产一行记录**,追加写 `<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`(单行 JSON,行行自足;缺省未装配 = 零写,纯单测零副作用)。信封键闭集 = 下表 9 键,禁加键;策略私有语义一律进 `payload`,不动信封。

| 键 | 类型 | 语义 | 供给方 |
|---|---|---|---|
| `strategy_id` | str | 策略器唯一 id(`CwStrategy.STRATEGY_ID`;文件名与渲染发现键同源) | wrapper |
| `schema_version` | int | 行格式版本(常量 `DECISION_RECORD_SCHEMA_VERSION = 1`,声明位 `strategies/impl/cw_strategy.py`;信封键闭集演进时递增) | wrapper |
| `dseq` | int | 本局决策序号,自 1 起按实例自增(实例不跨局 → 按局天然清零) | wrapper |
| `dtag` | str | 决策关联锚,格式 `<strategy_id>:<dseq>`;与同帧动作回执行 `receipt['dtag']` 同值(回执侧 = kernel 决策上下文槽,`kernel/cw_decision_ctx.py`) | wrapper |
| `entry` | str | 决策入口方法名(14 入口闭集,渲染章级挂载映射表的键) | wrapper |
| `node` | `{plane, round_num, kind}` \| null | `gs.node` 现读三元组;节点未观察 = null(null 帧不入章级挂载,计数并入局头「未归属」) | wrapper |
| `ts` | str | 写入时刻 ISO8601(秒级) | wrapper |
| `emitted` | `[{op, reason, route_tag}]` | 返回动作摘要,恒单元素:op = 动作类型名;reason/route_tag = 动作自带归因字段。空动作(重观察 `CwActionObsParam`)与非动作返回值同样成记录,归因键容缺 `''` | wrapper |
| `run_id` | str | 对局运行 id。**wrapper 信封不含此键,sink 落盘前补齐**(策略包禁依 telemetry 层,依赖单向);run_id 缺失 = 局外零写 | sink |

信封与载荷的关系:`{"envelope": …, "payload": …}` 单行 JSON;信封跨策略同构,payload 策略自治(未覆写载荷钩子 = `{}`,钩子异常由 wrapper 降级 `{}`)。嵌入/嵌套调用(子类经 `super()` 复用基类实现)由 in-flight 守卫归一为最外层一条记录;决策入口抛异常的帧不落记录。

## 2. payload 键表(mandate_v1 v1)

payload 三键组全部为**决策帧出口后的 gs/state 现读**(禁依赖决策入口内部局部量),纯读、不改决策行为。实现位 = `strategies/impl/mandate_v1/decision_payload.py`(薄委托入口 `bridge.MandateV1Strategy.decision_payload`)。

| 键 | 类型 | 语义 | 读口 |
|---|---|---|---|
| `direction` | `{locked: bool, comp: str\|null, candidates: [str]}` | 方向状态现值。`locked` = 锁定线槽非空;`comp` = 现行方向阵容名(锁定线优先,未锁 P1 回落过渡配方,两键都空 = null);`candidates` = 候选线名快照(分数降序,**锁定后恒空集**——锁定写入连带清空并停算) | `session_scope.line_members_view` / `session_scope.direction_comp_of` / `state.line_candidates` |
| `k_members` | `[str]` | 现行 K(目标线)名单:锁定帧 = 锁定线成员(core ∪ shared 注册表序);P1 未锁帧 = 过渡配方开局面成员;回退分支命中帧 = 回退派生成员(排序序,此时读 `k_fallback` 定来源) | `statefn.predicates.line_members(direction_comp_of(gs))`,空方向时回退分支(左) |
| `k_fallback` | `{hit: bool, band: str}` | K 空窗回退分支标注:方向键 None 且意向载体在场时,备战/商店两域共用的回退单一源派生成员集。`hit` = 该分支产出了成员;`band` = 分带 token(`'p1_gap'` / `'p1_lock_band'` / `'p2plus'`)。**判读规则:band 非空 ⟺ 回退分支已运行;`hit=True` 的 `k_members` 来自回退派生,不是锁定线成员**;`hit=False ∧ band` 非空 = 分支运行但合法空集。band 空串 = 分支未运行(方向在场或意向缺帧) | `cw_intention.k_empty_window_fallback`(同参重推导,不写其备战帧计数键) |
| `window` | `{char: {open: bool, sig: [kind, threshold]\|null}}` | 上线窗口判据现值(候选 A「上阵窗口自锁」的复核面:终局成员在窗口未到时不上阵,此前该判据无任何落点)。角色集 = `k_members` ∪ **持有域**(备战席 ∪ 场上)出现的终局库成员——被窗口挡在备战席的终局件是判域主体,只看上场板面会漏。`open` = 窗口判定核直调结论(缺信号行 fail 恒假);`sig` = 该角色在窗口查表序(锁定 = 仅锁定线;未锁定 = 全库)内首个信号行 `[kind, threshold]`,无信号行 = null。`kind` 闭集:`synergy`(板面主羁绊计数 ≥ 阈值)/ `level`(玩家等级 ≥ 阈值)/ `plane_end`(第二位面已启动)/ `always_on`(恒真)。键序 = 角色名排序 | `entry._entry_window_open`(唯一判定核,同包私有限内访问)/ `Comp.entry_signals` / 成员集常量 `entry._ENDGAME_LIBRARY_MEMBERS` |

判读注意(payload 通用):payload 由渲染器通用键值渲染,渲染器不解释语义——语义一律以本篇键表为准;某键在某帧的值 = 该帧出口后现读,与信封 `node` 同帧。

### 2.1 章级挂载的已知降级(申报句)

**章级同键多实例 FIFO 错位为已知降级**:无回执形态的记录(11 个选择族入口,不产回执;补给确认链产回执、走动作级 join,不在此列)由渲染器按 `(entry, node)` 键挂载到画面章;同一 node 内同 title 章出现多个实例时(同 node 内备战 → 商店 → 备战),渲染器按「章首现序 × 记录 dseq 序」FIFO 依次分配。单线程下决策序与画面访问序一致,但重试/回跳形态下**依据块归属到哪个同 title 章可能与真实画面次序错位**——判读同 node 多同 title 章的「策略依据」小节时,以 dtag 对应的动作/回执为准,章归属仅作参考(分配机制 = 渲染器常量与章合并逻辑,`tools/cw/replay_to_md.py`)。

## 3. 存储与发现指要

- 存储:`<recorder 根>/strategy/<strategy_id>_<run_id>.jsonl`,追加、逐行写后即 flush;多局/多策略按 strategy_id/run_id 分文件。
- 发现(渲染器):缺省 = journal 同根 `strategy/` 目录全部 `*.jsonl`(按本局 run_id 过滤);`--strategy-telemetry` 可显式指定文件或目录。无策略文件 = 报告与现状零差异(三处全降级:sink 未装配 = 零写 / 未覆写钩子 = `{}` / 无文件 = 零差异)。
- 消费边界:动作级 join(dtag 精确关联)仅适用产回执的入口(备战/商店/补给三类确认链);其余 11 个选择族入口不产回执,走章级挂载(§2.1)。两级 join 的完整规则与报告块形态见渲染器实现与其迭代设计,本篇只锁数据语义。
