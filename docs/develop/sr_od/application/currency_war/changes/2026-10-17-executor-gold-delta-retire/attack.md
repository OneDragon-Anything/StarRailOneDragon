# 设计对抗报告（首轮 · 无前提攻击，两轮消息：初报 + 修订闭合复核）

> 攻击核 = 无前提攻击（grep/读码/journal 数据独立实证，不信任设计自证）。状态：9 项发现全部处置 + 复核可定稿（附 R1-R6 一行级建议已落）。

## A. 阻塞项（9 项）

| # | 发现 | 处置 |
|---|---|---|
| A1 | **归因机制名错误**：journal 写行序列化键集无 produced_by（`_swap` :2726-2760；live journal 'produced_by' 0 命中）——真实归因链 = `sig.actor` + gold 写行 `prov.gold.evidence='proj_sell_refund'`（live 实存 175 行） | 已改写：design §1/§3 归因 = sig.actor + prov evidence；produced_by 申报失真分账（§2.4③） |
| A2 | **「统一对账告警」为死代码**：`cw_observe.py:224` `field=='gold_delta'` 分支无生产方（全 src obs_conflict 零处传 gold_delta；账面 vs 实读金对账函数不存在）——「金事实链本已闭环」前提半假 | 已改判：**本批补账实金对账生产者**（design §2.3：备战帧 gold 读点账实对比 → obs_conflict('gold_delta') → 复活告警门）——统一对账从声明变现役，迭代由纯减法变为减法+补齐 |
| A3 | **删除面漏 5 处文本触点**：`_note_action_receipt` docstring 两处金差门引用/「三管道」未收窄、last_gold_delta 注释块（含失实消费方申报）、双记防线注释块、主链注释金差字样、模块 docstring 词、Unit TYPE_CHECKING import | 已修：§2.1 表增「文本面」行 |
| A4 | **grep 清零判据字面不可执行**：changes/ 历史文档含退役符号（铁律不回改）；独立语义子串命中未豁免（shop_session.apply_gold_delta 函数名/cw_exec_state evidence/defects.py 别名/telemetry/schema.py 注释/loss_comp_bucket_replay 停产流）；3.1「全仓」vs 3.2「正本树」矛盾 | 已修：3.1 范围 = src/+tools/+sr-od-test；豁免面预填（design §4） |
| A5 | landing 3.2 文件面漏 4 正本：action-logic-state.md:136,209、logic-updates/prep-executor-actions.md:13,17、op-effects.md:11、level-up.md:26 | 已修 |
| A6 | 边界申报②不成立：容器 gold 写点 ≥3（sell_bench.py:99 正主 + _advance_gold + shop_session.apply_gold_delta(also_container=True) 伴生入金）——「唯一写点 = 上报函数族」不成立，§2.4 漏第③点 | 已修：§0 边界②改「上报函数族 + 已登记例外（分账清单）」；§2.4 分账补第③点 |
| A7 | 测试冲突点未点名：test_replay_render.py:376 断言 gold_delta 显影（反判）；test_prep_action_ops.py:367/:1063 last_gold_delta 断言 AttributeError；:354 docstring | 已修：landing 3.1 判据写死三迁移点 |
| A8 | 相邻死代码：_pre_bench 死存储（赋值后全仓零读）+ _bench_occupied_count 零调用方（金差账同源残留）；last_launch_ok 冗余赋值 :455-457 | 已修：并入 §2.1 删除面/顺手收编 |
| A9 | landing 样本路径不精确 | 已修：全路径 |

## B. 复核补充（修订闭合复核，均非阻塞已落）

| # | 内容 | 处置 |
|---|---|---|
| R1 | **账面取值时点约束**：对比必须挂在本帧 `gs.observe(gs.gold)` 写之前——插在写后容器被本帧读数覆盖，gap 恒 0，告警静默死亡（读点 :2320 / 写点 :2669） | 已修：design §2.3 明写时点约束 |
| R2 | gap 会混入两类失配（logic 写分叉 / 未建模收入常规窗 +11~+30 每收入窗必触发）——建议实施时以 Field.source=='logic' 判据区分 | 已修：design §2.3 补判据注记 |
| R3 | 三宗罪#3 引用失真：1500 事件属实但根因挂 visit 环断路器（receipt-applied-retire 迭代账本 T-4），非金差链本体——归因拉伸 | 已修：改写为「同期实证：执行缝吸收形态缺断路器」，账本引用带迭代名 |
| R4 | §2.1 文本面漏 gs_of_ctx import（:39，使用点在被删两函数体内） | 已修 |
| R5 | §4 样本路径与 landing:20 统一 | 已修 |
| R6 | attack.md 落盘（原目录无此文件） | 本文件即落盘 |

## 零发现面（独立实证成立）

五件删除对象行锚/唯一性全对；删后主链独立成立（skip 分支平凡改造）；回执 extra 'gold_delta' 零读点（渲染器 :1010/:1534 两处都改缺一不可；ab_judge/repair/journal_query/match-review/skills 全零命中）；last_gold_delta 零外部消费；op_success 三→两收窄与代码一致；read_gold_settled（:159）与 cw_loop:1684-1693 守卫锚实存；观察侧告警吃 obs_conflict 不吃回执 extra（删 extra 不影响任何现有 live 读取面）；旧 live journal 样本合格（44MB，receipts 行含 applied+gold_delta 双键，如 SellBench applied=true gold_delta=1）。
