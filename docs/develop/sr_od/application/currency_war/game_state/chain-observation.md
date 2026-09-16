# chain-observation.md —— 链观察对接(载体/双源/diff 证据/账本挂接)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(含 GameState/BoardState
> 命名对应注)。
> **内容源声明**:链观察的设计原始件(节点链观察-设计v1)已随过程区清理退役,
> git 历史可溯;本文 = 链观察设计正本——只写 state 字段、查询接口与遥测挂接,
> 判定与识别细节以代码锚(符号 = `kernel/cw_game_state.py` 派生族与
> `obs/` 解析器)为准,禁凭记忆复写。

## 1. 链观察是什么

货币战争每位面一条**节点类型链**(格数按位面:地面真值 P1=9/P2=7/P3 未观测,单一源=
`docs/game/currency_war/research/plane_schedule_observed.md`;战斗/奖励/补给/遭遇/
BOSS……),投资策略/环境效果会中途改写后续节点类型——**链是动态的,最新观察才是
真相**(裁定②)。链观察把这条链变成 state 的正式观察:位面过渡屏读基线/离场快照、
备战帧报权威现行链、基线与现行的 diff = 效果改型的直接观察证据。

## 2. 载体:NodeChain / TokenCell

```text
NodeChain:                      # 链值载体
  plane : int                   # 本链所属位面(1-based)——值自带位面,防位面切换窗读陈旧链
  seq   : list[TokenCell]       # 下标 i(0-based) = 该位面第 i+1 轮的读数单元
                                # (与判读侧台账 PlaneNodeLedger.seq_by_plane 同下标语义)

TokenCell:                      # 单格读数(逐格元数据随读数落载体并持久化)
  token   : str | None          # 类型 token(登记式封闭集:battle/supply/encounter/reward/boss
                                #   + 仅标签通道 elite/megastar/invest;None=本帧未辨)
  channel : str                 # 产出通道 ∈ {hu, label, sift, none, dim}
  hu_dist : float | None        # 残差/置信(SIFT 命中格=好匹配数;标签命中格照记)
```

state 字段(节点域):

- `node_path`(现行链):**最新权威读数覆盖**,整帧覆盖不按位合并——统一 state 存
  帧事实,合并视图归判读侧台账,防两种语义搅在同一字段。
- `node_path_baseline`(基线链):**位面入口写定**,本位面内不被链读覆盖;位面切换时
  新基线整值覆盖旧位面基线(旧值=流水历史行)。

跨度语义:`node_path` = **本位面**链(容器正本 §3.2.2 原文「本局节点类型序台账」的
跨度收敛为「本位面」是显式语义选择——按位建模是链观察与 diff 的最小自洽单元;正本
同步候文档维护批)。

## 3. 基线链 + 现行链双源

| 源 | 写端 | 语义 |
|---|---|---|
| 基线链(入口值) | 开局过渡屏(P1 基线唯一权威源,quality=`transition_row`;投资环境选择**前**的改型前真值);回退序 `transition_row > plane_detail > prep_row_first` 以最先落档者为准 | P1=全窗观察;P2/P3 过渡屏不给入口值(1→2 显示 P1、2→3 显示 P2)→基线=首帧回填,diff 观察窗较 P1 收窄,如实申报 |
| 现行链(最新真相) | 备战帧链读(quality=`prep_row`;轮位对齐门才写——变异窗不对链写设门:整帧覆盖自愈+diff 两帧门拦截误报,落地批取舍)+ 位面过渡离场快照(quality=`transition_snapshot`,跨位面形态=刚离开位面的链终值) | 已通过段不由本帧负责,由流水历史补齐(journal 行行自足,任一行可读「位面 p 第 i 轮当时的链」) |

quality 源标定谳:现行链写端 quality 固化 = `prep_row`(链观察落地批实现取值;
历史两义注——件 B §3.1.2/§3.3-F6 的 `row_read` 与 §3.2 载荷示例的 `prep_row`——
随实现并轨收口,判读按源标过滤以本值为准)。

失读放行纪律:链读失败不阻塞流程,对应字段保持未写(基线缺→diff 关闭;离场快照缺→
该位面终笔不产),诚实缺失,不伪造。

## 4. diff 证据(chain_diff)

比对主体 = kernel 纯函数 `chain_diff(baseline, current)`(数学单一源,实机与 sim 共用):

- **rewrite 位集** = 双方 token 均非 None 且不等、且差不属通道受限差的位。
- **通道受限差**单列不入改写:基线通道 hu、现行通道 label 且现行 token∈仅标签集——
  属两写端识别能力集不同,非环境改写。
- **长度差/首差位/基线覆盖位集**(baseline_coverage 显影基线 None 洞:基线首写帧未辨位
  不随后到读数补齐,保「基线=入口快照」时间语义)。
- **触发纪律**:基线在场∧diff 非空才记;备战帧触发的 diff 须**连续两个 clean 备战帧
  读数一致**才记行(单帧翻转不产行);离场快照豁免两帧门(单帧即终审,载荷带
  `snapshot='departure'`);投资环境变异窗内豁免(窗关后按两帧确认补比对)。

## 5. 与遥测账本的挂接

- 链字段 = 节点域普通 Field 域:每次写入经统一写入口产一行**写入行**(行型 1),渠道
  =①obs,行内全量 state 快照自带链值与逐格 TokenCell——零新机制。
- `chain_diff` = **obs_event 行型 2**(零状态变更、占版本、内嵌当时 state):载荷含
  baseline/current 两链序列与来源、逐格 channels/hu_dist、rewrites/channel_limited/
  length_changed/first_diff_pos/baseline_coverage、confirm_frames;verdict 留空——
  改写效果的身份归因 = 消费侧对 active_env/active_strategies 同帧快照的 join 结论,
  观察层不猜。event 词 = 登记清单项(登记归迁移批 M1,接线归 M2——见
  [retirement.md](retirement.md) §5)。
- 对账口径:链 diff 行 vs 改写源登记(容器正本 §3.2.2 改写源清单:人身意外险/战争
  边疆/决议:娱乐星球)的对照;指标面对齐统一观察架构「锚 vs 帧」同型。

## 6. 查询接口(与节点域唯一交汇)

```text
chain_node_type(view, plane, round_num) -> ChainQuery   # 现行链该位原值,零内建回落:
                                                        #   None=现行链不知道(链缺/越界/
                                                        #   未辨/past 位),调用方按自己的
                                                        #   仲裁序兜底
chain_baseline(view, plane) -> NodeChain | None         # 基线显式独立读:仅作入口参照,
                                                        #   禁当真值兜底(可能已被改写)
chain_rewritten(view, plane) -> set[int]                # 已证伪改写位集:位∈本集 ⇒ 该位
                                                        #   基线值禁用作类型兜底(消费侧执行)
```

消费方=节点域类型派生规则四②「商店查现行链」(判定本体归场景一判定方案,见
[node-domain.md](node-domain.md) §5/§7)。兜底序(台账合并视图等)归判定规则本体辖域;
基线不入兜底序、改写位禁令由消费侧执行。冲突留证走既有 obs_event `arbitrate` 词,
载荷 {chain, direct} 双值并陈,仲裁谁赢=判定规则本体。

## 7. 边界

- **防双源**:判读侧台账 `PlaneNodeLedger`(ExecState 合并视图)与 session 三载体
  现状不动、不新增职责;链查询不读它们——node_path 存帧事实、台账存合并视图,
  语义分格,禁互相代读。
- **入口前跨位面改写**(如战争边疆改第三位面)体现为「基线本身已改」,不产 diff;
  该形态证据通道=基线与改写源登记对照,挂效果账本消费批。
- **sim 域**:引擎无中途改写建模→合成口基线恒等于现行,`chain_diff` 结构性恒空、
  sim 档案零 chain_diff 行——如实申报的边界,非缺陷;替换建模落地后经同一纯函数
  自动产行。**落地批修订(链观察落地批 2026-09-16)**:合成口写链裁剪为不写——
  sim 决策的 node.kind 消费不经链,写与不写零行为差,省合成口改造面;
  node_path/baseline 在 sim 恒空 = 诚实缺位;引擎中途改写建模落地时按本节恢复
  合成写链(合成单元 TokenCell 届时填 `channel='none'`、`hu_dist=None`,
  evidence 恒带 `sim:synthesized`)。
- 识别面(Hough/Hu/SIFT/标签交叉核对/扩参/暗格处置)与实施批切分(B-1 采证/B-2
  过渡 op/B-3 接线 diff/B-4 消费)以件 B 为准,本文不复写。

