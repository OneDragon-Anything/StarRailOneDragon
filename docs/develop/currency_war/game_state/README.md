# GameState 设计总纲

> 本文档所属 = game_state 设计目录(本目录总纲)。
> **命名对应注**:本文档所称 **GameState**(统一 state),当前代码中暂名 **BoardState**
> (`src/sr_od/application/currency_war/kernel/cw_board_state.py`);改名随旧流退役迁移批
> 执行,改名前文档用 GameState、代码用 BoardState,两者指同一容器。

## 1. 本目录是什么

统一 state(GameState)的设计文档正式目录,总-分结构:本文件=总纲,五个分篇各管一面。
总纲是 [BoardState-数据结构设计.md](../design/BoardState-数据结构设计.md)(下称「容器正本」)
的**简化版**——只写设计理念与核心规范;字段清单、决策 op 写入面、效果族归属、迁移批次
等完整规格以容器正本为准,本目录不重复(代码已实现的部分不在文档重复细节)。

上位裁定与 why:**ADR-0630**(统一 state 状态流水:BoardState 收编升级+三渠道写入口+
自足快照变更账)。ADR-0630 含修订节,冲突处以修订节为准——守卫族终版、单字段双值结构、
字段层次终极版(观察层=原始读数/逻辑层=计算值)三条为当前有效裁定。

## 2. 设计理念(六条)

1. **观察如实上报**。观察层=画面原始读数,零计算——observe() 只落原文,禁写派生值。
   例:备战帧顶栏 OCR 读到「备战阶段 1-3」,原文整串进观察层字段 `top_bar_raw`;
   把原文解析成序键 3 是计算,归逻辑层。
2. **state 内派生逻辑态**。逻辑层=从观察数据**计算**的一切(节点序键/节点类型/效果
   计数/统计)。派生规则是 state 内部逻辑,在同一写入事务内完成——**无独立事件流**,
   一切派生产出都是 state 写入,不存在「hook 触发后再写」的第二条路径。
3. **单字段双值结构**。一个事实 = 一个逻辑层值字段 + 一个原始读数字段,不设两个
   专名字段再在读时合并。例:节点序 = `top_bar_raw`(观察层)+ `node_ord`(逻辑层)。
   单事实单值字段(金/hp 等)不拆,来源与质量维由渠道签名承载(见 journal.md §3)。
4. **唯一写入口,禁旁路**。一切写入必经统一写入口(Field 系 API)或 inventory 方法域
   (效果域);绕 API 直改字段=违反,机器面=grep 子串守卫锁(ADR-0630 决策 7,先例
   ADR-0571)。
5. **单版本事务**。一次逻辑写入 = 一个版本 = 一笔自足快照行:写入口收到写入后,同一
   事务内先落原始变更,再按固定次序跑关注点派生(节点判定→类型→效果推进),所有连带
   字段更新共享同一版本 id;原子性=派生出错整笔回滚留证,无中间态。
6. **行行自足账本**。任一账本行 = 改了什么 + 渠道签名 + 版本 id + 写入后完整 state
   快照;查询=按行直接读,零重放、零前溯、零锚、零对账。崩溃丢失窗=该时点无行,
   诚实缺失。

## 3. 核心规范摘要

### 3.1 写入口两分法:observe() / write_logic()

写入 API 按数据层两分(符号=kernel/cw_board_state.py):

| 写口 | 层 | 用途 |
|---|---|---|
| `observe()` | 观察层 | 亲眼看到的原始读数,覆盖旧值;value=None 拒绝(缺读不写禁猜) |
| `write_logic()` | 逻辑层 | 从观察/动作计算出的逻辑值;**仅限设计显式申报豁免的写端**,其余逻辑写入走两步机制 |

配套口:`expect()`/`confirm()`/`discard_expected()`(待核实预期两步机制:先记预期、
核对通过才转正写字段)/`carry()`(失读沿用,evidence 带 carried:来源帧)/`write_prior()`
(先验写入,如开局 hp 先验)/`leave_screen()`(画面附加域离屏置 None)/`relay()`
(接管中继)/`note_obs_event()`(零状态变更的观察事件留证行)。完整 API 契约见
journal.md §6 与容器正本 §8.4。

### 3.2 权威序

- **观察赢**:观察写入覆盖 logic 来源值;失配记 `observe_vs_logic_mismatch` 缺陷行
  (留证显影,不静默)。还没核实的预期条目只能由它自己的核对点关闭,观察帧不得
  确认或清除。
- **节点生效序**:权威序字段的读口 = 生效序读口,语义=逻辑层现值与 run 内高水位
  取大(公式体单一源见 [node-domain.md](node-domain.md) §3);消费面恒取逻辑层。
- **节点类型三源仲裁**:结算屏权威(ADR-0239)> 节点序列台账现读 > 帧标签 OCR
  (容器正本 §3.2.1)。

### 3.3 域清单

统一 state 按域组织(域=字段分组,读不分域;写入域准入白名单=ADR-0630 决策 2 硬
约束,逐格以实码写点全集为准):

| 域 | 代表字段 | 主写渠道 |
|---|---|---|
| 节点域 | top_bar_raw / node_ord / node(NodeKey)/ node_path | ①观察+③派生(见 node-domain.md) |
| 画面上下文域 | prev_screen / current_screen | ①观察 |
| 单位域 | front_row / back_row / bench / back_layout | ①观察+②动作+③效果桥 |
| 经济域 | gold / hp / level / xp / streak / level_up_cost / shop_refresh_cost | ①观察+②动作 |
| 计数域 | 免费刷新余额/付费与总刷新计数/节点屏刷新计数 | ②动作+③效果桥 |
| 效果账本域 | effects(在场效果实例) | inventory 方法域(随快照行自带) |
| 动作发射事实域 | receipts(滚动窗,容量常量 RECEIPTS_WINDOW_CAP) | ②动作 |
| 局级事实域 | selected_difficulty / active_env / active_strategies / plane_bosses / enemy_affixes / board | ①观察+②动作+③中继 |
| 画面 payload 域 | shop / encounter / supply(非当前画面=None) | ①观察 |
| 交互状态域 | 分类子态 / event_overlay | ①观察+③接管协议 |
| 结算域 | settlement(hp/streak/gold/level 结算真值) | ①观察 |
| 局终域 | match_final(一段终态一行;恢复局跨段多行) | ③局终收口 |

渠道族封闭集 = obs(画面 op 观察)/ logic_action(动作 op 逻辑计算)/ logic_hook
(state 内部派生逻辑计算);carried/prior/synthesized 是 obs 族内子模,非第四源。

## 4. 文档地图

| 分篇 | 管什么 |
|---|---|
| [journal.md](journal.md) | 记录机制:账本文件、三渠道封闭集与渠道签名、版本 id 与单版本事务、自足快照行、落盘与查询 |
| [node-domain.md](node-domain.md) | 节点域:字段双层、生效序读口与 hist 哨兵、守卫族、派生规则单一源引用 |
| [strategy-env-impacts.md](strategy-env-impacts.md) | 投资策略/环境逐效果在 state 里的影响(已确认条目+候逐条确定占位清单) |
| [chain-observation.md](chain-observation.md) | 链观察对接:基线链/现行链双源、diff 证据、与遥测账本的挂接 |
| [retirement.md](retirement.md) | 旧 12 流退役逐流处置与消费方迁移清单(只写排期与清单结构) |

## 5. 边界与姊妹文档

- **容器正本**=[BoardState-数据结构设计.md](../design/BoardState-数据结构设计.md)
  ——字段级规格、op 写入面、效果族归属、迁移批次的唯一正本;本目录与其冲突时以
  正本+ADR-0630 修订节为准。
- **派生规则单一源**=场景一判定方案(`.debug/temp/currency_war/流程hook场景一-节点推进-判定方案.md`;该档不入 git,持久裁定锚=ADR-0630 关联行与文档拆分裁定记档)——本目录引用不复写。
- **链观察设计件**=件 B(`.debug/temp/currency_war/节点链观察-设计v1.md`)——
  [chain-observation.md](chain-observation.md) 是其对接面精炼,不是第二正本。
- **效果域内容语义**(计数器模型/生命周期/逐效果规格)= 独立效果域设计件,候讨论
  成文;本目录只记捕获面(效果变化随快照行自带)与逐效果 state 影响登记。
- **策略侧遥测**(决策行)= 两文件模型的另一文件,归策略侧设计正文;state 引用
  只经版本钉 state_ref=`(run_id, v)`,且决策输入禁读状态流水(ADR-0577)。
- 玩法语义(各效果游戏机制原文/节点流转时序)挂靠
  [docs/game/currency_war/](../../../game/currency_war/)(game 子树)。

---

## 附:2026-09-11 文档审修正批落点对照(本篇)

> F 编号 = 审结论条目号(审结论在进度目录 `reviews/game_state目录批-文档审.md`,
> 本地不入 git);本节为落点备忘,正文 as-built 口径以上文为准。

| 审条目 | 落点 | 修正 |
|---|---|---|
| F1 | §3.3 局终域行 | 粒度注改「一段终态一行(恢复局跨段多行)」,与遥测正本/retirement.md 口径对齐 |
| F2 | §5 派生规则单一源 | 判定方案完整路径收进单行代码跨,消除跨行断行致路径不可复制 |
| F3 | §3.2 节点生效序 | 公式体双写删除,总纲留语义句+指针(公式单一源=node-domain.md §3) |
