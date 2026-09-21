# node-domain.md —— 节点域(指针篇:字段指针/生效序读口消费纪律/单一源引用)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。
> 节点推进判定本体单一源 = [node-derivation.md](node-derivation.md);本篇不复写判定
> 语义(双处书写 = 漂移根因,文档拆分裁定),只记节点域的消费侧纪律、记录面分工
> 与指针。

## 1. 节点域管什么

节点域回答「bot 现在打到第几个节点、是什么类型」。节点身份 = 节点序键
`node_ordinal = (plane−1)×9 + round_num`(基 1,跨位面连续 9→10;坐标系与效果账本
`advance_node` 同式)。类型是身份的载荷属性不入键,防第二失真源;类型读法与仲裁
见 §7 与 [fields.md](fields.md) §3.2.1。

## 2. 推进模型与字段结构(指针)

**推进模型一句话(R7 触发模型)**:节点推进 = 上一节点**终结动作落地**的上报
(战斗节点 = 结算胜利确认;补给节点 = 补给选择确认),经观察态门(`node_ord`
value 在场 ∧ source=observation 双条件)与推进生效原语 `advance_node_effective`
落账;观察 = 对账锚定 + 兜底(`observe_node_anchor`,锚定写端两处 =
`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 补给屏节点条),不再是推进触发面。
判定本体单一源 = [node-derivation.md](node-derivation.md) §3.3。

节点序载体字段(结构与写口语义单一源 = [node-derivation.md](node-derivation.md)
§3.2-7;符号 = kernel/cw_game_state.py):

| 字段 | 语义 | 指针 |
|---|---|---|
| `top_bar_raw: Field[str]` | 备战帧顶栏原文(观察层),唯一写点 = 观察汇聚;原文缺读不写禁猜 | 同上 |
| `node_ord: Field[int]` | 节点序,**两态字段**:锚定态 observation(锚定 helper 解析读数直写,节点域专用口不经通用 observe())/ 推进态 logic(终结动作上报经原语写入,推进未确认态) | 同上 |
| `node_hist_ord` | run 内单调水位 + 去重第二道防线;run 段随容器重基线 | 同上 |
| `node: Field[NodeKey]` | plane/round/kind 观察镜像(漏斗写端保留,决策层坐标消费) | 同上 |

画面上下文域 `prev_screen`/`current_screen` = 两个独立事实的原始读数(观察域,
写点 = 观察漏斗;开局链分支写点已随触发模型换代退役,开局链段不再写上下文对),
与节点推进无写入耦合。

节点域不走通用观察覆盖失配三分流——锚定 helper 四分支显式处置(含 R<v 倒退
免疫留证),单一源 = [node-derivation.md](node-derivation.md) §3.3-4。

## 3. 生效序读口与消费纪律

- **生效序读口** `effective_node_ord()` = `max(node_ord 现值, node_hist_ord)`
  (派生计算,非存储字段;None 安全,双空 = 未定)。判定与比较域统一在该读口;
  定义与处置规则单一源 = [node-derivation.md](node-derivation.md) §3.2-7。
- **消费纪律**:一切序比较/节点判定一律经读口取值——不消费 `top_bar_raw`
  原文,不按 `node_ord` 来源分叉判先后。两态来源语义 = 读方须知:
  `source=logic` 是推进未确认态(待观察锚定翻确认),`source=observation` 是
  已锚定确认态;读口取 max 已吸收两态差,消费侧无需再判来源。
- **hist 哨兵** `node_hist_ord`:去重键 `(run_id, effective_ord)` 的 run 内载体,
  推进/锚定落账时占位;同序恰一次推进由去重键保证。

## 4. 旧画面推断机制(已退役)

从画面散射推断节点推进的旧机制(含其前驱守卫、缓存守卫、幂等锚与循环分支写点)
已随触发模型换代整体退役。退役物清单与申报单一源 =
[node-derivation.md](node-derivation.md) §3.3-6,考古归 git 历史;仓内现役文档
不再以其为口径书写。

## 5. 判定本体单一源引用(禁复写)

节点推进判定本体(节点边界定义/终结动作定义/观察态门/推进生效原语/观察锚定/
类型派生/退役申报)的**唯一正本** = [node-derivation.md](node-derivation.md)
§3.3(2026-09-11 自临时档 `.debug/temp/currency_war/流程hook场景一-节点推进-判定方案.md`
晋升入库;现行版次以该文件头为准)。本文不复写。

本篇承载的记录面分工:

| 面 | 归宿 |
|---|---|
| 字段结构与两态来源语义 | [node-derivation.md](node-derivation.md) §3.2-7 |
| 判定本体(触发面/门与原语/锚定处置/推进语义) | [node-derivation.md](node-derivation.md) §3.3 |
| 推进事实落账(journal 行) | [journal.md](journal.md) §1(推进写账 = 行型 1 写入行;门挡留证 = 行型 2 obs_event arbitrate) |
| 渠道归属 | 总纲域清单(README §3.3);写口语义见 node-derivation.md §3.2-7 |
| 回归走查(多推进源叠加形态) | [node-derivation.md](node-derivation.md) §3.6 |

## 6. 级联走查指针

多推进源叠加(级联)形态的恰一次推进论证与回归走查:单一源 =
[node-derivation.md](node-derivation.md) §3.6(级联走查两段)。现行模型下推进
唯一动作入口 + 观察态门,级联双推进破口结构性消失(论证见同节),本文不复写。

## 7. 类型派生与链查询接口

节点类型权威链(①专属画面直定——BOSS 简报屏 `CwScreenBossBriefing` 观察 node
经 `_write_derived_node_type` 直定;②商店查现行链;③冲突留证)与倒退直定丢弃
留证的**本体单一源** = [node-derivation.md](node-derivation.md) §3.3-5。商店查链
接口 = `chain_node_type`(零内建回落,None = 现行链不知道)——接口契约与链字段
= [chain-observation.md](chain-observation.md);链缺位 = None 诚实缺位。
查链/直定目标节点 = 生效序与观察镜像的最新者(镜像序领先时镜像更鲜活,丢弃
直定留证,类型由镜像源承接)。
