# executor-gold-delta-retire 迭代设计（总纲）

## 0. 元信息
- 迭代目标：**执行缝金差链整体退役 + 账实金对账生产者补齐**——executor 不再计算/携带任何金差证据；统一对账告警从死代码复活为现役防线。用户裁定 2026-10-16（「为什么要在动作 op 之后自己做对账，我们应该有统一的观察态和逻辑态的对账」）。
- 状态：草案
- 文档清单：无详设（单文档方案）
- **边界申报**：①LogicOutcome 契约（上报函数族拒绝语义）不动；②容器 gold 写点现状 = **上报函数族 + 已登记例外（分账清单见 §2.4，含 `_advance_gold` 与 `shop_session.apply_gold_delta(also_container=True)` 两条非上报函数直写）**——本迭代删的是执行缝第三份拷贝（回执 extra 证据腿），写点收敛核查分账另立；③`cw_exec_state._advance_gold` 直写路径核查 = 分账（§2.4）。

## 1. 问题与动机
- **归层**：流程层（执行缝私设账面期望供给，与统一对账架构平行）+ 约定层（回执 extra 携带非动作事实的记账数据）+ **对账基建缺口**（统一告警门无生产方，见 §2.3）。
- **金的事实链现状（attack 无前提攻击实证修正后）**：
  1. **逻辑态（账面）**：容器 gold 由上报函数族与已登记例外直写（写点清单 = §2.4 分账）；journal 写行**不含 produced_by**（序列化键集无此键），归因链 = `sig.actor`（如 CwActionSellBenchOp）+ gold 写行 `prov.gold.evidence='proj_sell_refund'`（live journal 实存 175 行）；
  2. **观察态（实读）**：`read_gold_settled` 稳定门读屏（两帧一致才采信，防入账计数器跳动，`obs/cw_observation.py:159`）；
  3. **对账**：obs_conflict 机制在位，但 `field='gold_delta'` 冲突**零生产方**——`cw_observe.py:224` 的 `|gap|>10` 分级告警分支为死代码，**账面 vs 实读的金对账函数不存在**（reconcile_gold 全仓零命中）。live 唯一金冲突 = 读侧稳定门 `obs_conflict('gold',…)`（首末帧 OCR 抖动，非账实对比）。
- **执行缝金差链的三宗罪**（数据实证）：
  1. **第三份平行计算**：派发前快照 → 派发后算差，公式与上报函数同源（星×招募费），信息零增量；
  2. **零消费方**：回执 extra `gold_delta` 键在渲染器/cw_batch_stats/ab_judge/query/repair/match-review 全域零读点；
  3. **同期实证：执行缝吸收形态缺断路器**——live 1500× BuyCard 执行未落地 3 分钟失控循环（分账 = receipt-applied-retire 迭代账本 T-4；根因挂 visit 环断路器缺失，非金差链本体，属同形态动机佐证）。
- **历史**：`prep_actions.py` 双记防线注释自证「执行缝与投影双腿各记一次的实机倒挂实证」——−2 倒挂事故的根 = 执行缝直推容器金账（已拆），证据腿为本批退役对象。
- **架构缺口补齐申报**：本迭代不是纯减法——**补齐账实金对账生产者**（§2.3），使「统一观察态/逻辑态对账」从声明变为现役（用户架构裁定的正面落地）。

## 2. 方案（单文档完整设计）

### 2.1 删除面（`prep_actions.py` 执行主链 + 两函数 + 文本面）

| 删除对象 | 位置（符号锚） | 说明 |
|---|---|---|
| 派发前快照调用 | `execute` 主链 `_pre_sell_bc = self._pre_sell_target_bc(action)` | 快照唯一用途 = 供金差计算 |
| 金差门调用 + extra 组装 | `gold_delta = self._executed_gold_delta(...)`、`last_gold_delta = gold_delta`、`_gold_extra = {...} if gold_delta not in (None, 0) else None` | 回执 extra 组装仅保留跳过子态分支（与金差无关） |
| `last_gold_delta` 字段 | `PrepActionExecutor.__init__` 与赋值点 | 零外部消费（grep 实证） |
| `_executed_gold_delta` 函数本体 | 含「未发出 = None」门与卖出返金计算 | 连同 docstring（None/0 语义、−2 倒挂防双记申报）整删 |
| `_pre_sell_target_bc` 函数本体 | 派发前身份快照（bench/deployed 视图读取） | 唯一消费方 = 金差计算 |
| **文本面**（attack 实证 6 触点） | `_note_action_receipt` docstring 金差门引用两句、「三管道」收窄为两；`last_gold_delta` 字段注释块；双记防线注释块；主链注释首句金差字样；模块 docstring「执行点金差」词；`Unit` TYPE_CHECKING import；`gs_of_ctx` import（:39，唯一使用点在被删两函数体内，删后 F401） | 逐处随删 |
| **同源死代码并入** | `_pre_bench = self._bench_occupied_count()`（赋值后全仓零读）+ `_bench_occupied_count` 函数（零调用方）+ :423 注释 | 金差账同源残留，attack 实证 pre/post 两点的 post 消费方不存在 |
| **顺手收编** | `last_launch_ok` 重复冗余赋值（:455-457 被 :448-454 包含） | 既有杂物，删冗余分支 |

- **保留面**：`op_success` 派生与两消费方；回执 invariant；跳过子态 extra。
- **回执 shape 不变**：extra 里不再出现 `gold_delta` 键。

### 2.2 渲染器排除表追加 `'gold_delta'`（旧 journal 兼容）

`replay_to_md.py` 两处 extra 排除表（:1010/:1534，**实值排除表与显示闸两处都改，缺一不可**）追加 `'gold_delta'`：新数据无此键零成本，旧数据（live journal 实证 receipts 行含 applied+gold_delta 双键）不显影。

### 2.3 账实金对账生产者补齐（复活统一告警门）

现状：`cw_observe.py:224` 的 `field='gold_delta'` 分级告警（`|gap|>10` 响亮）**无生产方**——全 src 的 obs_conflict 调用零处传 `gold_delta`（攻击枚举实证），告警门为死代码。

**补齐**：备战帧 gold 观察读点（`read_gold_settled` 采信后）增加账实对比：

```
gap = |实读(stable read) − 容器 gs.gold.value(账面)|
gap > GOLD_DELTA_ALARM_GAP(10) → obs_conflict('gold_delta', old=账面, new=实读)
→ 既有分级告警分支响亮（[cw!][alarm][gold_delta]）
```

- 账面 = 容器 gold（写点清单 §2.4 分账核定）；实读 = 稳定门读数；阈值复用既有常量。
- 首轮以 warning 级运行，误报率数据回填后调阈值；**本批交付 = 生产者上线 + 告警门首次可达**。
- 申报：账实对比在备战帧观察位执行（gold 读数唯一消费点），不加读屏次数（复用该帧截图）。
- **账面取值时点约束**（防静默中和埋点）：对比必须挂在本帧 `gs.observe(gs.gold, …)` 写**之前**的容器现值——插在写后则容器已被本帧读数覆盖，gap 恒 0，告警静默死亡且无报错（读点 = `cw_observation.py:2320` 一带，容器写点 :2669）；同帧 recognizer 并发触发时挂漏斗调用点或加同帧去重。
- 首轮告警行大概率集中在轮转收入窗（未建模常规收入 +11~+30，稳定门 docstring 实测口径）；可用 `gs.gold` Field.source=='logic'（存在未被观察覆盖的 logic 写）判据区分「logic 写分叉」与「未建模收入窗」，误报率数据回填后调阈值。

### 2.4 分账（不混本批）

| 分账项 | 内容 |
|---|---|
| ① | `cw_exec_state._advance_gold` 直写容器金账（apply_confirm_effect +4 / BuyCard dict 路径扣金）与「唯一写点」申报的一致性核查——若为漏网直写腿，按 −2 倒挂同族升级清理 |
| ② | `shop_session.apply_gold_delta(also_container=True)` 伴生入金写点（rebate/companion gold）归属裁定 |
| ③ | `write_logic` docstring「produced_by=留存证据用」对 gold 类字段失实（produced_by 不落 journal）——框架级申报修正 |

## 3. 关键取舍

- **删证据腿 + 补对账生产者，而非维持私设账面**：用户架构裁定 = 统一观察态/逻辑态对账；执行缝私设期望供给是与统一对账平行的第三通道，且实证零消费。
- **`op_success` 保留**：恢复局守卫（控制流）+ 回执码供给（遥测事实）两个消费方均为硬依赖。
- **归因机制名修正**：journal 归因键 = `sig.actor` + `prov` evidence（非 produced_by）——design 初版机制名错误，attack 实证修正。
- **渲染器排除表追加而非删旧**：`'applied'` 与 `'gold_delta'` 两键并存排除，同保证旧 journal 兼容。

## 4. 验收基准（预写）

- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）；
- 新局渲染：回执 extra 无 `gold_delta` 键；旧 journal（`.debug/currency_war/telemetry/live/state/journal.jsonl`，含 applied+gold_delta 双键）重渲染零异常且字样零显影；
- 账实对账生产者上线：备战帧 gap 对比可构造（fixture 或驱动局观测），告警行 `[cw!][alarm][gold_delta]` 可达；
- 全仓 grep 清零：`_executed_gold_delta`/`_pre_sell_target_bc`/`last_gold_delta`/回执域 `gold_delta` 键——范围 = src/ + tools/ + sr-od-test/（changes/ 历史文档豁免；正本树归 3.2 闭合法）；豁免面预填 = 渲染器排除表 'gold_delta' 字面量、`shop_session.apply_gold_delta` 函数名、`cw_exec_state` evidence='op_effect_gold_delta' 字面量、defects.py 别名、telemetry/schema.py 注释、loss_comp_bucket_replay（停产流）、obs 告警门 `GOLD_DELTA_ALARM_GAP` 独立语义；
- 全量测试过（sr-od-test 相关子集）。
