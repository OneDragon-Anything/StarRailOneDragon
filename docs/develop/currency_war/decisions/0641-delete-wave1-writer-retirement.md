# 0641 删除波 1——收编 9 流写入端删除(直迁删除决策落档)

> 编号注:0N 系顺延(现最大 0640)。本 ADR 为删除波 1 入库豁免路径的事后补档
> (T-274),补位时点距入库同日,溯源凭据均在案。

- 日期:2026-09-11(实施入库;同日补档)
- 状态:accepted
- 关联:ADR-0634(直迁裁定——旧流=删除代码非停写,本件承接该义务的执行批)、
  `docs/develop/currency_war/game_state/r5-migration-plan.md`(R5 迁移规划,
  波次排期正本:删除波 1 对应其 W7/P7 删除面的先行段)、
  `docs/develop/currency_war/game_state/retirement.md`(§2 逐流处置表=删除对象
  判据单一源;其影子框架重构随本批兑现)、进度账本 T-256(实施批收账)、
  `.debug/progress/2026-09-06-currency-war-redesign/reviews/删除波1-落地审.md`
  (落地审凭据,本地不入 git)

## 背景(判死依据)

收编 9 流(decisions / outcomes / exogenous / spend_ledger / shop_snapshots /
exec_events / invest_cards / obs_conflicts / runs)的判死依据 =
retirement.md §1 退役理由(流散乱分片、写点不全、无渠道签名、无统一 state)
+ §2 处置表逐流结论(处置词表均为「退役」或「字段收编+流退役」)。删除的
可行性前提 = 替代载体已在产:统一 state journal 写路径(R1)、渠道签名与
派生规则(R1.1/R1.2/R2)、判读新读面与装配器 v12(R3.1/R3.2)、决策行
版本钉(R4)均已落地审 accept,且 ADR-0634 已裁 journal 无条件常开。

保留面(不入本波删除面):

- 保留 2 流 defect_ledger / op_journal——非统一 state 辖域的独立语义面,
  保留专用候裁(R5 规划候裁 4);
- 审计流 cw4_counters(逐 key 审计挂 W4)与补遗流 board_state_archive
  (归宿挂 W2 match_final)不在本波;
- journal 写路径本体与全部旧档案读面(判读 CLI/装配器/sim 账本/tools/cw)
  保留——旧流停更后存量语料仍可裸读考古。

波序事实(如实申报):R5 规划 W7 的进入门(W3+W4+W6 验收绿)未满足即
先行执行本波——删除波 1 为编排者排期的独立删除批次。代价 = 读面切换未
完成的消费面短暂断供,最大项为哨兵 3 脚本尾读旧流(实机窗口武装哨兵前
必须切 journal 或显式申报豁免窗,落地审 §八 P-1);验证职责按 ADR-0634
三元组(测试锁族+落地审+实机窗口)不减。

## 决策(删除面)

9 流**全部生产写入端**删除(逐流明细单一源 = 删除波 1 交付报告 §二,
本节记概要与配属面):

| 流 | 写入端删除概要 |
|---|---|
| decisions | `record_decision`(类方法+模块函数)、prep `_record_step`(改 no-op 壳)、买牌/补给/商店段散布写点、`_seg_pin_version` 钉版、`_CTX_MATCH_REF` 读通道槽 |
| outcomes | `record_outcome` 族、`_record_supply_outcome` 合成行、`_write_terminal_outcome_row` 终局行族、battle_wait `_source` 变量 |
| exogenous | `record_exogenous`(kernel 出口留 no-op 桩护 cw_anchor 在飞调用方)、简报/popup 等事件屏调用、`_PENDING_BRIEFING_ROWS` 局间缓冲、血购回执/模态金两通道 |
| spend_ledger | `record_spend_unit`、`set_unit_gold_close`/`set_unit_exec_facts` 暂存槽、finalize 暂存块 |
| shop_snapshots | `record_shop_snapshot`(offer/refresh 两点),零残余 |
| exec_events | `record_exec_event`、`bypass_exec_event_to_defect`、defects 装配通道 |
| invest_cards | `record_invest_cards`、strategy/env 屏采集分桶、候选评分供数块写端 |
| obs_conflicts | `obs_conflict` 文件写端(`_CONFLICT_JOURNAL` 删除),证据行改 `note_obs_event` 收编 journal(行结构/截图节流/告警门原样保留) |
| runs | `record_run_summary`→`close_run` 零落盘、`build_recovered_summary`+`recover_dangling` 兜底(后者留 no-op 桩)、Δ池局终自动再生触发 |

配属删除:策略失活早停(`write_strategy_dead_flag`/`register_flow_heartbeat`
——心跳行停写后失活判据会误杀每一局)、`state_journal` 配置键销案、app
装配段改无条件 `install_state_telemetry`。

残余 no-op 桩两处(`record_exogenous`/`recover_dangling`)随候裁整段退场
(cw_telemetry_exit 桩挂 R5 §5-7,兜底桩调用点已删)。

已知后果五件(交付报告 §四如实申报):

1. exec_fail 安灯数据源断供(钩子本体保留,重接面 = receipts 发射行,
   候消费方切换批);
2. obs 缺陷台账 refs 指冻结档案(处置指针更新 = T-275);
3. invest 效果原文回流断供(接受后果;归宿 = strategy_offer 画面 payload
   域,候选卡效果原文注册表回流用途不变;处置面 = T-275);
4. Δ池自动再生消失(池本体与手动/sim 批口保留);
5. 假环境账本「plan 成本 vs 实扣」容忍缺口显影(既有缺口非本波引入,
   删除的遥测读点兼为假环境观察钟 tick 源;立卡 T-273)。

## ADR 补位的豁免与兑现路径

- **入库时 ADR 未先行**:删除波 1 交付无 ADR 稿,书面申报「并入 W7 文档
  批」为豁免路径(编排者认可;豁免凭据 = T-258 立项 2026-09-11T01:31:37
  早于入库 commit,落地审 commit 门条件 1 的第二款)。
- **补位兑现**:本 ADR 即该欠账的落档——编排者排期裁决(进度账本 T-274
  附注,盘点十九轮候选 19)独立小批先行,不硬等 W7 文档批,判据 =
  ADR 补位拖久则决策与证据的溯源链新鲜度递减(删除波 1 入库与补位同日)。
- **入库凭据**:主仓 `3d4461438`(38 文件,+397/−2144)+ 测试仓 `9972ebf`
  (43 文件);落地审 commit 门条件 2/3 兑现——交叠八文件(W1 波×本波)
  逐 hunk 剥离入库(其中 20 件 hunk 选择/线级手术),测试仓 42 申报面 +
  4 新锁文件逐文件分账;入库过程事故一笔(`--only` pathspec 误用致在飞
  hunk 泄入)未推送即 reset 闭环,教训入库:多批并行期 commit 禁带
  pathspec,一律点名 add 后裸 commit。
- **落地审凭据**:`reviews/删除波1-落地审.md` 结论 accept(附 commit 门
  条件)——逐流删除面完备性亲证(写入端符号全仓 grep+逐文件 diff 亲读)、
  退役锁 4(test_cw_old_stream_write_retirement.py)读码核过+抽域复跑
  38 passed、L1 3246 passed 与 L3 失败样本复点亲证;退役锁在入库树
  worktree 对 committed 双仓亲证 40 passed(入库报告 §四门 2)。

## Considered Options

- **删除决策 ADR 并入 W7 文档批**(原豁免申报路径)——改判独立小批先行:
  W7 大包远期到达则本 ADR 与删除事实间隔拉长,溯源链(凭据文件、commit、
  亲证记录)新鲜度递减;ADR 补位本身是纯文档件,独立成批成本低。
- **停写观察代替删码**——否决:ADR-0634 直迁裁定已裁旧流=删除代码,
  停写观察属影子框架语义(已销案)。
- **逐流 ADR(一流一档)**——否决:9 流删除同属一个删除决策(同一判死
  依据、同批执行、同一验证三元组),单档内逐流删除表已提供足够溯源粒度,
  拆档只增加索引维护成本。

## 后果

- retirement.md 影子框架重构随本批兑现(排期节改指 R5 八波正本、前置
  条件节改直迁形态、落点对照叙述链收敛为版本历史表)——ADR-0634 关联节
  与 R5 规划风险 11 的「retirement.md 重构随 W7」文档义务由此提前闭环;
  后续 W7 到达时余量为零。
- 后续删除批次(旧流余量写面/GameState 本体)沿用本件的删除决策形态与
  验证三元组。
- 实机窗口前置义务:哨兵 3 脚本尾读切换 journal(落地审 P-1,挂 R5 W3
  读面切换波)——未切换前武装哨兵必误报,实机窗口排期须避让。
