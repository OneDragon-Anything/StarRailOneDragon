# 设计对抗报告（首轮）

> 攻击方：核一无前提+实现者试读+数据核验（10 项发现，含真引擎/journal 实证）、核二+三规范遵循+治本（S1-S5/Q1-Q5 + 附带悬空指针）。状态：全部发现已处置。

## A. 定稿门槛项

| # | 发现 | 处置 |
|---|---|---|
| A1 | **open_shop 定位缺失 → round_fail 是死信**：宿主 `_ = open_shop(self)` 弃结果（用户裁定 2026-09-10「调用方不问成败」），外环 fail 防线只消费顶层分发 round 结果——删回执后「定位缺失」journal 与防线双零痕迹，比现状更静默 | 已改判：**回执保留 + reason 码化**（journal 痕迹承载）+ round_fail 维持 + 主日志双痕迹；可见性损失显式申报（design §0/§2.2） |
| A2 | **close_shop「同构 round_fail」双重错误**：①现状 miss 出口是 round_success 非 round_fail（事实错误）；②close-shop.md §5 明文「幂等已关出口的 applied=false 是簿记事实不是失败」——改 round_fail = 幂等终态误判故障 → fail_streak 误计数 → 熔断误停机；③visit 环内嵌 op 的 round_fail 到不了 fail_streak（同 A1 断链） | 已改判：**close_shop 幂等出口维持 round_success**，回执保留 reason 码化（仅删布尔）；landing 判据删 close_shop 的 round_fail 半边 |
| A3 | **「未发出专属通道 env.emitted」引证全部不实**：全仓零读零写（PrepExecEnv 构造不传 emitted；level_up:95 是注释行）；docstring 自认「遗留旁路字段…不再被包络消费」。真实机制 = round_fail → 结束本次访问 → 下帧重观察重决策（流程结构性承载，不经字段） | 已改判：design §1 论证 2 与 §2.4 边界表重写——通道 = round 结果通道（结构性重派）；prep 域未发出的承载 = 回执 reason 码（invariant 保持）；emitted 字段本体的处置（读点仅回执透传/金差门/last_launch_ok）随退役收敛 |
| A4 | **「换锚零行为差」循环论证**：LogicOutcome.reason 现役语义域含受理附注（applied=True + reason 非空：gain_chain_applied/zero_write/content_unresolved/unknown_leg_evidenced 等十余处，测试锁死合法）——全量透传会让受理附注涌入回执（受阻样式误显 + 合并判据误并）。行为差实锤 | 已改判：§2.1/§2.2 显式透传规则 = **只透传拒出口（not outcome.applied）的 reason，受理附注不入回执**（维持现状可见性）；业务拒绝可见性（bench_full）= 后续批（outcome 冒泡机制需动作 op 全集 32 文件改造，独立设计） |
| A5 | **visit 环 reason 透传不可达**：动作 op 出参被忽略（buy_card:58/187），visit 手上只有 OperationRoundResult——透传需 outcome 冒泡机制（ShopExecEnv 暂存/round data），文件面只列一处会静默跳过 | 已改判：visit 环业务拒绝透传 = 后续批（§2.2 申报）；本批 visit 环回执**保留** + 机械早退 reason 码化（终审 B1 裁决修法 (i)——与 invariant/事故链证据一致） |
| A6 | **visit 环 false 回执实机主体 = 机械早退无 outcome**（live journal `BuyCard\|false\|执行未落地(BuyCardOp)` ×8——槽解析失败早退，无 LogicOutcome），reason 无供给定义；且拒买 bench_full 现状回执 = applied=true + reason=''（拒绝不可见） | 已修：§2.2 visit 行定义机械早退码（slot_unresolved/slot_out_of_range）；bench_full 可见性缺口申报后续批（A5） |
| A7 | **prep 口 emitted=False 回执行两义 + invariant 破坏 + 事故链证据**：live journal `StartBattle\|false` 3 连链 = 停机事故复盘主干（hook:cw_launch_dead）；「click 未落地」不落 §2.4 四行任一；prep_actions.py:419 invariant「每动作 op 恰一条回执行」随删行破坏 | 已修：prep 口回执保留 + reason 码化（invariant 保持）；「click 未落地」场景并入 §2.4 第 1 行场景列（四行表无第五行） |
| A8 | **§2.3 自相矛盾 + landing 判据互斥**：排除表删 'applied' → 旧 journal 布尔字样漏显，与「重渲染零异常」不能同时成立 | 已修：**排除表保留 'applied' 键**（旧数据防漏显，新数据零成本）；landing 判据改「零异常且布尔字样零显影」 |

## B. 设计文本/引用修正

| # | 发现 | 处置 |
|---|---|---|
| B1 | 「node 1-2 起」与数据不符（四连死全 P1r1；复现局 P1r6） | 已修 |
| B2 | 测试引用面修正：需迁改仅四文件（test_replay_render.py:64-67/:340-353、test_open_shop.py:126-171、test_shop_screen_op.py:195/:378）；test_sim_smoke_batch.py:209-212 统计谓词**不改**（语义依赖新不变量「回执恒已发出」）；test_action_registry/test_launch 零迁移 | 已修 landing 文件面 + 豁免申报 |
| B3 | 正本清单三面归属说明：三面（op-layer.md 计数与画面框行、logic-updates/open-shop.md §3.1、sim-design.md:88-90）**归上迭代 open-shop-action-spec 落地面**（已在其落地批收口）；本迭代核读三面均零回执域 applied（LogicOutcome 豁免域）——本迭代 landing 不列是正确归属，非遗漏 | 归属说明（非处置项） |
| B4 | landing 判据不可机检（terminal 枚举） | 已修：death\|p3_enter |

## C. 规范遵循（核二+三）

| # | 发现 | 处置 |
|---|---|---|
| S1 | 【致命·上一迭代继承确认】sim 点击 = 世界推进通道（sim-design §3.2 + cw_sim_backend.py:1035/1095-1119）——本迭代 §2.2 open/close 行均保留点击腿，与已落地的 open-shop-action-spec 重组一致 | 一致性核验通过 |
| S2 | §1 机理叙述与权威源不符处随 A2 重写 | 已修 |
| S3 | 正本更新清单/op-layer 联动（本迭代不删类壳,仅回执域——op-layer 面 = 上迭代已收口,本迭代无 op-layer 义务;reason 码词表归 action_ops.md） | 已核：本迭代 op-layer 零义务 |
| S4 | 上报面申报（回执域唯一上报口 = note_action_receipt;report_action_open_shop_param 零写族不调;非转移动作无喂入行） | 已修：§2.1 申报三行 |
| S5 | retirement.md 11 号项措辞（「零成败 receipts」vs 终态「reason 受阻码」）+ reconcile 衔接语义 | 已修：landing 3.2 ⑤ 改写 + 衔接申报随切换批 |
| S7 | 持久索引（「用户裁定 2026-10-16」引用形态 = 会话裁定,随定稿转正本登记;retirement 11 号项引用合法） | 已修：design §0 引用标注 |
| S8 | §1 归层行 | 已补（约定层 + 表示层） |

## D. 治本核验（逐问）

| # | 结论 | 处置 |
|---|---|---|
| Q1 | 流程根因：回执契约正本缺失（fields.md 行为模型段无字段级契约、历轮审查无回执域清点）——字段能活三天的根 | 已修：landing 3.2 ②③ 正本段落地 + reason 码词表登记（正本补齐即防再发） |
| Q2 | LogicOutcome 同名混淆风险：本迭代不改名只申报边界——docstring 边界申报 + 未来改名另批可议 | 已修（§0 边界申报） |
| Q3 | 「未发出三通道终态表」与 spec 原文对照：无发明（emitted=False 出口语义 = action_ops.md:60 原文;round_fail 通道 = 流程结构性承载;显式报错 = 裁定原文） | 核验通过（attack 修正后无发明面） |
| Q4 | 双 applied 概念边界 | 已修（§0 申报） |
| Q5 | 同族清点：回执域 applied 之外无第二家簿记布尔（exec_events 词表/审计面不读 applied） | 核验通过 |

## E. 已核无发现面（两攻击方交叉确认）

调用点全量恰 4 处（无别名 wrapper 增生）;渲染器 applied 读点恰 7 处无第 8 处;journal 回执键集 = {op, applied, reason, detail, screen, action, gold_delta} 与设计一致;换锚对存量合并判据等价（0 反例,前提排除表保留）;cw_action_report/ 零回执写点（只构造 LogicOutcome）;审计面（cw_projection_audit）与 sim 引擎本体不读 receipts.applied;无存量测试断言开店 applied=否。

## F. 第二攻击面（规范遵循+治本）补充发现

| # | 发现 | 处置 |
|---|---|---|
| F1 | 收店分类错误：CwActionCloseShopOp = 注册表动作 op（§4.1，带 ShopExecEnv）非直调组合壳；正本 close-shop.md §5 明文 miss=良性幂等态；未观察跳过场景 miss=店未开预期态——round_fail 会把良性离店灌进 fail_streak | 已修：close_shop 维持 round_success + 回执 reason 码化；分类与未观察豁免写入 §2.2/§2.4；清场上报保留申报 |
| F2 | visit 环注册 op round_fail 路径回执处置缺行（落地门 :646-648 现写 applied=false + 散文 reason，迁移去向未定） | 已修：§2.2 visit 行补「round_fail = 零回执（未发出不入回执），失败可见性 = visit 返回 False + `[cw-op]` 日志」 |
| F3 | reason 词表开放且极性混合（applied=true + reason 非空受理附注十余处合法；同码双极性 bench_unobserved；参数化码 stale_proposal:{expect}）——全量透传契约被自家范围反例证伪 | 已修：本批回执 reason 只承载机械受阻码，LogicOutcome.reason 透传 = 后续批（outcome 冒泡）；§3 措辞改「迁移后由本批规则保证单载体契约」 |
| F4 | visit 环透传管道缺位（LogicOutcome live 被丢弃，落地门只拿 round 结果）——bench_full 显影需 op 全集冒泡改造 | 已修：后续批申报（同 F1 处置） |
| F5 | prep 行迁移失实：emitted 派生自 round 结果成功态（非 env 字段）；漏登记真实在役消费 last_launch_ok + gold_delta 门；「删 applied 透传」字面会重造第三通道 | 已修：§2.2 prep 行改写（派生澄清 + 两管道显式保留 + emitted=False 回执保留 reason 码化——**裁决：核一/核二+三在 prep 口结论相反，采核一**（StartBattle 停机事故链证据 + invariant 压倒零回执建议），裁决理由入 design） |
| F6 | PrepExecEnv.env.emitted = 死字段（零读零写，docstring 自认遗留） | 已修：字段随本迭代退役申报（局部派生事实保留） |
| F7 | 正本锚不存在：journal.md 无回执形态小节（不硬造）、action_ops.md 无回执契约段（需新增）；行号锚违背 fields.md 惯例 | 已修：landing 3.2 ①② 改真实锚 + 新增小节申报 + 符号锚 |
| F8 | 语义闭清缺口：不含 applied 字样的旧语义表述（CloseShop「店已关(幂等出口)」）grep 抓不到 | 已修：landing 3.2 闭合法补语义闭清 |
| F9 | retirement.md 11 号项「落地登记」违 as-built 无状态 | 已修：只做语义修正，落地事实记账本/README |
| F10 | 表题「未发出」含游戏拒绝行矛盾 | 已修：表题改「未发出/拒绝事实」 |
| F11 | 过程叙事（「三轮质询」「本日三轮反复」）+ M1③ 式会话词 | 已修：§0/§1 删过程叙事改持久指针（action_ops.md §1 裁定区随 3.2 登记） |
| F12 | Q1 流程根因半成：回执契约正本散落五处无机器守护 + 审查面不含回执 shape + 渲染器规范住 changes/ 无正本家；结构性守护（删签名=编译期防复发）未自我登记 | 已修：§1 流程根因段 + 正本归位声明（fields.md 单一节）+ 渲染器规范归宿申报（3.2 ⑤）+ 结构性守护讲明 |
| F13 | Q2 同名风险：退役后 LogicOutcome.applied 单所有者，不必改名（原「改名另批可议」降级） | 已修：§0 |
| F14 | Q5/Q3：obs 类/审计面/正本无 receipts.applied 硬依赖；三通道表 row1 消费列失实+漏 last_launch_ok、row4 透传=发明 | 已修（F5 + §2.4 重写） |

## 零发现面补充（核二+三确认）

生产 src 零 receipts['applied'] 运行时读点（消费面 = 渲染器 + 测试）；cw_batch_stats/ab_judge/哨兵组/query 视图/repair/match-review 模板/skill references 全无 applied 读点；landing 阶段七件齐；README 模板合规。
