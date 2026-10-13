# node-domain.md —— 节点域(索引篇:字段指针/生效序读取入口消费纪律/单一源引用)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。术语与图例:保留词与数字来源标注四形态【注】【推】【拟】【拍】见
> [README](README.md) §6 术语表;对账 = 推算状态与下一帧实读逐项比对,对不上即 bug;
> 帧 = 一次拍画面+做决策的时点,帧代次 = 帧的版本标记。
> 节点推进规则本体唯一权威出处 = [node-derivation.md](node-derivation.md);本篇不复写判定
> 语义(双处书写 = 漂移根因,文档拆分裁定),只记节点域的消费侧纪律、记录面分工
> 与指针。

## 1. 节点域管什么

节点域回答「bot 现在打到第几个节点、是什么类型」。节点身份唯一表示 = 节点
序位键 `(位面, 轮)`(`NodePos`,二元素整数元组,1 基,单一源住
`cw_node_schedule`;对外标识统一「位面-轮」标签形态如 `2-1`,元组只是标签的
容器内表示)。序列真值**按局修饰变长**:默认环境 = 默认序列表;投资环境改
节点序列时(「人身意外险」每个 boss 位前插补给)序列真值随场字段
`node_seq_by_plane` 调整——凡持 gs 的生成方同读场字段(None = 未注册态回退
默认表),与效果账本 `advance_node` 同源。「推进 +1」= `sequence_next`
(`cw_node_schedule` 后继原语,位面切换在此发生);位面优先、位面内轮次次序
的元组字典序 = 序列全序,全部比较/去重/水位语义直接比较序位元组。类型是
身份的载荷属性不入键,防第二失真源;类型读法与仲裁
见 §7 与 [fields.md](fields.md) §3.2.1。

## 2. 推进模型与字段结构(指针)

**推进模型一句话**:节点推进 = 上一节点**终结动作落地**的上报
(战斗节点 = 结算胜利确认;补给节点 = 补给选择确认),经观察态门(`node_pos`
value 在场 ∧ source=observation 双条件)与推进生效原语 `advance_node_effective`
落账;`sequence_next` 无后继(超出建模域)= 局终声明事件式(零写入零 tick,
`applied=True, reason='match_end'`)。观察 = 对账确认 + 兜底
(`observe_node_anchor`,id_mark 确认的写入位置两处 =
`CwScreenPrep` 备战顶栏 / `CwScreenSupplyNode` 补给屏节点条),不再是推进触发面。
规则本体唯一权威出处 = [node-derivation.md](node-derivation.md) §3.3。

节点序载体字段(结构与写入口语义单一源 = [node-derivation.md](node-derivation.md)
§3.2-7;符号 = kernel/cw_game_state.py):

| 字段 | 语义 | 指针 |
|---|---|---|
| `top_bar_raw: Field[str]` | 备战帧顶栏原文(观察层),唯一写入位置 = 观察汇聚;原文缺读不写禁猜 | 同上 |
| `node_pos: Field[tuple[int, int]]` | 节点序位(`NodePos` 元组),**两态字段**:id_mark 确认态 observation(确认 helper 解析读数直写,节点域专用口不经通用 observe())/ 推进态 logic(终结动作上报经原语写入,推进未确认态) | 同上 |
| `node_hist_pos` | run 内单调水位 + 去重第二道防线;run 段随容器重基线 | 同上 |
| `node: Field[NodeKey]` | plane/round/kind 观察镜像(聚合入口写入方保留,决策层坐标消费) | 同上 |
| `node_seq_by_plane: Field[dict[int, tuple[str, ...]] \| None]` | 逐位面节点序列场字段(逻辑态):键 = 位面 1 基,值 = 节点类型序;写入位置唯一 = `gain_invest_env` 尾段,注册后恒全量;None = 未注册态,消费方回退默认表 | [fields.md](fields.md) §3.2.1 |

画面上下文域 `prev_screen`/`current_screen` = 两个独立事实的原始读数(观察域,
写入位置 = 观察聚合入口;开局链分支写入位置已随触发模型换代停用,开局链段不再写上下文对),
与节点推进无写入耦合。

节点域不走通用的失配三种标准处理分支(失配三分流 = 失配的三种标准处理分支:
白名单差异直接采纳 / logic_rand 预期内差异记录采纳 / 真失配记缺陷并停机)——
id_mark 确认 helper 的四分支显式处置(含读数倒退不采信并保留证据),
单一源 = [node-derivation.md](node-derivation.md) §3.3-4。

## 3. 生效序读取入口与消费纪律

- **生效序读取入口** `effective_node_pos()` = `max(node_pos 现值, node_hist_pos)`
  (元组字典序取大;派生计算,非存储字段;None 安全,双空 = 未定)。判定与
  比较域统一在该读取入口;定义与处置规则单一源 =
  [node-derivation.md](node-derivation.md) §3.2-7。
- **消费纪律**:一切序比较/节点判定一律经读取入口取值——不消费 `top_bar_raw`
  原文,不按 `node_pos` 来源分叉判先后。两态来源语义 = 读方须知:
  `source=logic` 是推进未确认态(待观察 id_mark 确认翻态),`source=observation` 是
  已确认态;读取入口取 max 已吸收两态差,消费侧无需再判来源。
- **hist 哨兵** `node_hist_pos`:去重键 `(run_id, 生效序位)` 的 run 内载体,
  推进/id_mark 确认落账时占位;同序位恰一次推进由去重键保证。

## 4. 旧画面推断机制(已停用)

从画面散射推断节点推进的旧机制(含其前驱守卫、缓存守卫、幂等锚与循环分支写入位置)
已随触发模型换代整体停用。停用物清单与申报单一源 =
[node-derivation.md](node-derivation.md) §3.3-6,考古归 git 历史;仓内在用文档
不再以其为口径书写。

## 5. 规则本体单一源引用(不在两处重复写)

节点推进规则本体(节点边界定义/终结动作定义/观察态门/推进生效原语/观察 id_mark 确认/
类型派生/停用申报)的**唯一权威版本** = [node-derivation.md](node-derivation.md)
§3.3(2026-09-11 自本地临时稿(不入库)晋升入库;现行版次以该文件头为准)。本文不复写。

本篇承载的记录面分工:

| 面 | 归宿 |
|---|---|
| 字段结构与两态来源语义 | [node-derivation.md](node-derivation.md) §3.2-7 |
| 规则本体(触发面/门与原语/id_mark 确认处置/推进语义) | [node-derivation.md](node-derivation.md) §3.3 |
| 推进事实落账(journal 行) | [journal.md](journal.md) §1(推进写账 = 行型 1 写入行;门挡保留证据 = 行型 2 obs_event arbitrate) |
| 渠道归属 | 总纲域清单(README §3.3);写入口语义见 node-derivation.md §3.2-7 |
| 回归走查(多推进源叠加形态) | [node-derivation.md](node-derivation.md) §3.6 |

## 6. 级联走查指针

多推进源叠加(级联)形态的恰一次推进论证与回归走查:单一源 =
[node-derivation.md](node-derivation.md) §3.6(级联走查两段)。现行模型下推进
唯一动作入口 + 观察态门,级联双推进破口结构性消失(论证见同节),本文不复写。

## 7. 类型派生与链查询接口

节点类型权威链(①专属画面直定——BOSS 简报屏 `CwScreenBossBriefing` 观察 node
经 `_write_derived_node_type` 直定;②商店查现行链;③冲突保留证据)与读数倒退时丢弃
直定并保留证据的**规则本体唯一权威版本** = [node-derivation.md](node-derivation.md) §3.3-5。商店查链
接口 = `chain_node_type`(零内建回落,None = 现行链不知道)——接口契约与链字段
= [chain-observation.md](chain-observation.md);链缺位 = None 诚实缺位。
查链/直定目标节点 = 生效序与观察镜像的最新者(镜像序领先时镜像更鲜活,丢弃
直定并保留证据,类型由镜像源承接)。
