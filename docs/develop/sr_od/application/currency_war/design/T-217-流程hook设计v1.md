> 【正本同域持久件】本文件为正本引用参照件——正本修订记录声明「v10 对照说明见本件(R2)」,本件为该对照说明唯一载体(本体标题虽为交付报告,按正本活引用规则收编)。
> - 正文出处:`.debug/temp/currency_war/T-217-流程hook设计v1.md` 原样找回(2026-09-11,经迭代 recovered/ 中转,一字未改);旧账 T-217 流程 hook 观测点设计批,其内容已并入正本 v10 §12 流程转点观测锚章
> - 落位:docs/develop/sr_od/application/currency_war/design/(账本 T-49 统一观察架构迭代末阶段正本更新批 re-anchor,正本头部指针同步改指本件)

---

# T-217 交付报告(R2):流程 hook 观测点设计 v2(已并入统一观察架构文档 §12,对抗审 16 项就地修订)

> 任务 = T-217(进度账本 `.debug/progress/2026-09-06-currency-war-redesign/dag.jsonl`,
> 观察-only 纯设计批,零代码)。设计正本落点 =
> `docs/develop/sr_od/application/currency_war/design/统一观察架构-画面op基类设计.md`
> **v10 并入**(§12 全章 + §6.4 轴扩展 + §11 R11)。本报告 = **R2**:
> v2 = 对抗审(高 3/中 6/低 7,报告 = `.debug/temp/currency_war/T-217-
> 流程hook设计v1-对抗审.md`)16 项就地折入 §12 的修订版,文件面仍只动
> 设计文档与本报告。

## ① 结论

四问落文不变(姊妹章并入,零独立新文档);v2 修正三类实质缺陷:

1. **事件集**:15 锚定性(v2 修正后分类,以 §12.2 表为准)——新增类
   5(buy_landed/box_opened/battle_start/plane_enter/node_enter〔写点
   新增+kind 名复用〕)、收编类 6(sell_landed/refresh_landed/
   levelup_landed/settlement〔+接线〕/event_choice/发射型刷新)、
   缓立 1(line_commit)、出辖 3(resume/开关店/换血死代码)。
   **v1 勘误(对抗审发现 13)**:v1 报告「新增 6+收编 5+接线 1」计数
   与名字列不自洽,v2 起以 §12.2 表为唯一分类口径。**levelup_landed
   由「新增」翻正为「收编+扩展」**(发现 3:现役 kind='level_up' 行
   与 on_level_up 挂点同点在产,另立新 kind = 同事件双行,禁);
   **node_enter 由「收编+扩展」如实化**(发现 4:现役唯一写点在战斗
   结算后且仅辖战斗节点,进节点分派时点是新写点)。
2. **数据面**:锚行七字段封装不变;**v2 申报 sim 侧现状**(发现 1):
   sim 局账本仅 decisions+outcomes 两流、零 record_exogenous——原
   「两域」8 锚全部改「实机先行」,锚行落盘面在 sim 暂缺(候选 =
   账本行内扩位 or exogenous 流接入,挂 H2),R8 承诺的 sim bs 登记
   流显式申报为未接线;现役 ExogenousEvent kind 全集补 5 值
   (level_up/briefing_reconcile/resumed_match/locked_resume/
   modality_gold)并以 grep 重扫为 H2 前置;settlement 锚行宿主改
   kind='settlement' 候选(outcomes 行降为对账参照);sell 渠道改
   「闭集值域 + reason→channel 归一映射单一源」(发现 7)。
3. **准确性判据**:指标 1 闭合公式重构(发现 2)——立「尝试口径」
   四项闭合(plan 数 = 截断未尝试数 + 尝试数;尝试数 = 锚行 + 执行
   失败数〔覆盖面申报〕+ 未知数),exec_event 覆盖面与截断显影接入
   挂 H7;验收 A 件 sim 腿收窄为「事实来源存在性」;测试锁四条扩为
   **五条**(发现 6:锁④拆写向/读向两条——决策代码禁读锚行的 grep
   守卫沿既定先例方向,effect_ref 恒空补非空=红结构锁)。
4. **机制关系**:七条框架不变;§12.5-1 两处如实化——buy/refresh 锚
   触发口依赖 §6.4 执行器收编批(R-J 挂账,发现 8)、boundary 型触发
   口不在 op 实例生命周期内(H6 新立,发现 5);「直引闭集」表述收窄
   为「闭集值域 + 归一映射单一源」(发现 7)。

边界执行:观测-only 坚守,且 v2 起隔离边界有锁承载(写向/读向两条 +
effect_ref 恒空锁),非纸面声明。

## ② 完成判据对照表(v2)

| 判据 | 结果 | 凭据指针 |
|---|---|---|
| 观测点清单齐 | 齐:15 转点逐锚七列(含 sim 适用域与 evidence_required 申报位) | 本文档 §12.2 总表(15 行) |
| 数据面齐 | 齐:锚行封装 + 载体三面(实机复用/扩展;sim 现状申报)+ 登记表行结构(含 evidence_required/前置依赖) | 本文档 §12.3 |
| 准确性判据齐 | 齐:五指标(指标 1 = 尝试口径四项闭合)+ 验收三件(测试锁五条) | 本文档 §12.4 |
| 并入 v9 章节防双源 | 达成:§12 姊妹章 + 轴扩展 + R11 + 修订记录 v10(含对抗审就地修订申报) | 本文档头部修订记录/§6.4/§11/§12 |
| 与 T-170 判据轴合并防两套接口 | 达成:消费不复制 + 闭集值域与归一映射单一源申报 | 本文档 §12.5-4 |
| 对抗审 16 项处置 | **高 3 全修/中 6 全修/低 7 全修**,逐条落点见下附 | 下附「对抗审 16 项 → v2 落点」 |
| 零代码纯设计 | 达成:仍只动设计文档与本报告 | §③ 变更面 |

**对抗审 16 项 → v2 落点(逐条)**:

| # | 级别 | 发现 | v2 落点(设计文档) |
|---|---|---|---|
| 1 | 高 | sim 域锚行落盘载体不存在 | §12.2 表头 sim 申报块 + 8 锚改「实机先行」;§12.3 载体一 sim 现状申报(R8 未接线申报在内);§12.4-A sim 腿收窄;§12.5-7 match_archive 辖实机申报 |
| 2 | 高 | 指标 1 公式以 plan 当发射数,常态不可达 | §12.4 指标 1 重构 = 尝试口径四项闭合;H7 新立(覆盖面申报+截断显影接入) |
| 3 | 高 | levelup_landed 与现役 'level_up' 行双源 | §12.2 行翻正「收编+扩展」+禁双行否决申报;§12.3 kind 全集收录 level_up |
| 4 | 中 | kind 枚举漏 5 值;node_enter 收编失真 | §12.3 载体一现役 kind 全集(grep 重扫为 H2 前置);§12.2 node_enter 行改「新增(写点)+复用(kind 名)」 |
| 5 | 中 | boundary 型实机触发机制无着落 | §12.6-H6 新立(三候选+禁静默选型);§12.3 登记表段申报;§12.5-1 如实化 |
| 6 | 中 | 锁④字面冲突;消费侧守卫缺位 | §12.4-B 扩五条(④写向/⑤读向+effect_ref 非空=红);§12.0/§12.3 载体二边界细化 |
| 7 | 中 | sell 渠道缺归一载体;sim 渠道无来源 | §12.2 sell 行改「闭集值域+归一映射单一源」;sim 侧恒空申报;§12.5-4 表述收窄;H2 增归一映射宿主 |
| 8 | 中 | buy/refresh 触发口不存在,时序依赖未申报 | §12.2 两行前置依赖申报;§12.5-1①;报告 §⑤.2 切分修正 |
| 9 | 中 | 报告勘误自身定位错(LAUNCH_CAUSES) | 本报告 §④.A 勘误(定义 = sell_gate.py:100;mandate_state.py:286 = 消费注释)+ §⑤.3 指针修正 |
| 10 | 低 | §12.5-4 买因声明与 payload 槽位不一致 | §12.2 buy_landed payload 增买因槽(经归一映射) |
| 11 | 低 | 指标 5 适用集未枚举 | §12.3 登记表行结构补 evidence_required + 初判全部 false;§12.4 指标 5 同步 |
| 12 | 低 | T-208「≤3%」归因错挂 | §12.2 refresh 行归因改:组键近似误差形态 + 边界存疑带 2 局分列 |
| 13 | 低 | 报告 §①.1 计数不自洽 | 本报告 §① 以 §12.2 表为准重列(新增类 5/收编类 6/缓立 1/出辖 3) |
| 14 | 低 | 「detect_merge_upgrade 预期条目 id」两产物焊一名 | §12.2 buy 行拆两槽:合成判定(bool)+ expect 预期条目指针 |
| 15 | 低 | settlement 锚行七字段无宿主 | §12.2 settlement 载体改 kind='settlement' 候选;outcomes 行降为对账参照 |
| 16 | 低 | battle_start 羁绊档位槽无落点 | §12.2 battle 行降级:deployed 摘要入锚行,羁绊档位离线派生不入锚 |

## ③ 变更面(v2 = 设计文档 1 件就地修订 + 本报告 1 件)

**§12 章内就地修订(11 处)**:§12.0(隔离边界锁承载句)/§12.2(表头
申报块重写 + 8 行修订:buy/sell/refresh/levelup/battle/node/plane/
settlement + line_commit sim 列)/§12.3(载体一 kind 全集 + sim 现状
申报、载体二边界细化、登记表行结构 + H6 申报)/§12.4(指标 1 重构、
指标 5 适用集、A 件 sim 腿收窄、B 件扩五条)/§12.5(第 1 条如实化、
第 4 条归一映射、第 7 条 sim 现状)/§12.6(H2 候选集重写、H3 增登记表
联动、H6/H7 新立)。

**章外 1 处**:头部修订记录 v10 行内补对抗审就地修订申报(v11 行为
并行批所有,未触碰)。

**并行批同文档申报(勿卷确认)**:本批修订期间,工作区同文档出现
v11 并入(验证段废除,用户裁定 2026-09-10;§5.1 六段→五段、§5.2、
§9.2 联动)——非本批面,归属编排者对账;本批 §12 引用与 v11 无冲突
(act→on_outcome 段在五段生命周期中仍在,§12 零「六段」引用,grep 已核)。

## ④ 验证记录(v1 勘误 + v2 增量核验,2026-09-10 实测)

**A. v1 符号核验勘误(对抗审发现 9)**:LAUNCH_CAUSES 定义点 =
`sell_gate.py:100`(`LAUNCH_CAUSES: frozenset[str] = frozenset({`),
v1 报告写 mandate_state.py:286 系**消费注释**非定义点;总图回写建议
指针随本条修正。方法缺陷申报:v1 核验用「grep 命中即 PASS」,未区分
定义点与引用点——v2 起核验命令带定义形态约束(`frozenset`/`def`/
`class`)。

**B. v1 已过核验(19/20,详见 v1 报告存档口径;除 A 项外全部维持
PASS,本次未复扫项无已知漂移)**。

**C. v2 增量核验(17 项全 PASS)**——命令口径:
`Get-ChildItem src/sr_od -Recurse -File -Filter "*.py" | Select-String -Pattern <符号>`:

| 核验项 | 实证 | 结果 |
|---|---|---|
| level_up 现役行 + on_level_up 同链(发现 3) | prep_actions.py 'level_up' 与 on_level_up 双命中;cw_effect_inventory.py `def on_level_up` | PASS |
| 现役 kind 补 5 值(发现 4) | briefing_reconcile/resumed_match/locked_resume/modality_gold/level_up 全仓命中 | PASS |
| battle_wait 出节点 node_enter 写点(发现 4) | cw_screen_battle_wait.py 'battle_done' 命中 | PASS |
| 指标 1 公式件(发现 2) | schema.py plan_truncated/refresh_skipped 双命中;exec_events 覆盖面(6 文件命中,精确清单挂 H7) | PASS |
| sim 两流(发现 1) | sim/pool.py decisions 命中 | PASS |
| LAUNCH_CAUSES 定义点(发现 9) | sell_gate.py:100 frozenset 定义(定义形态约束命中) | PASS |
| H6/H7/实机先行/禁双行 章节落文 | 设计文档 4 项 Select-String 全命中 | PASS |

**D. 结构核验**:§12 六小节齐;头部 v10 行修订在位且 v11 行(并行批)
未触碰;全文档节序 Select-String 无重复无断裂。

## ⑤ 偏差与未尽事项

1. **H1-H7 开放问题**随 §12.6 落文(H6 boundary 触发口/H7 公式可测性
   为 v2 新立),候清单修订批收编。
2. **实现批切分建议(v2 修正,替换 v1 §⑤.4)**:①收编批 = sell/
   refresh/levelup/event_choice/发射型 + settlement 接线(现役写点补
   申报面/scope/锁面);**buy_landed 前置 = §6.4 执行器收编批**
   (R-J 挂账,触发口随其成立,禁 inline 私接);②新增批 = buy(随
   前置)/box/battle/plane_enter/**node_enter(从 v1 的收编批改归
   新增批:新写点 + boundary 触发机制,H6 裁决前置)**;schema 修订批
   (H2,含 sim 落盘面)先于①②;H6/H7 裁决件随实现批①。
3. **总图回写建议(指针修正,替换 v1 §⑤.3)**:LAUNCH_CAUSES 定义 =
   sell_gate.py:100(v1 误指 mandate_state.py:286 消费注释);总图 R2
   §1.6 表头「:85-87」漂移回写指向 :100 起。
4. **sim 锚行落盘面**(发现 1 处置)为 v2 最大申报缺口修复:接线前
   sim 域锚结论辖「事实来源存在性」,禁引完备率;接线批归 H2。
5. **无 ADR 新增**:纯设计修订;H6 若实现批选「类级登记表+模块级
   fire 口」形态(架构级难逆),彼时补 ADR。
