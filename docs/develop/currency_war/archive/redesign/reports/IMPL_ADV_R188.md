# IMPL_ADV_R188 · 货币战争策略器重构设计文档对抗审查(第 188 轮,无锚轮)

> 审查对象:IMPL_DESIGN.md / design_economy.md / design_latch.md / design_telemetry.md(正文 L1-220,登记节在攻击计划成形后仅按冻结残余对账需要检索)/ IMPL_FIX_LEMMAS.md(仅冻结项清单对账)。文件面:除本报告外零写入,对象文档全部只读。
> 辖域裁定遵循:2026-09-03 用户裁定(流程侧代码锚豁免:operations/cw_loop.py、sim/engine_p1.py、sim 基建等行号/结构锚不立案,标「流程锚-豁免」;策略器侧锚——决策语义/判据族/注册表/kernel/观测层——照常立案)。

## ① 攻击计划(面选+理由)

本轮无锚轮,自选四面:

| 面 | 内容 | 选择理由 |
|---|---|---|
| A 数值锚直调注册表 | cap 族(cap_sup=10/cap_resolved=5/GOLD_CAP_INTEREST=50/override∈{9,10,0})、STREAK_GOLD_TABLE、LOSS_GOLD_BY_NODE、NODES_PER_PLANE、PLANE_FALLBACK_PRIORS、BENCH_CAPACITY、win_reward_mult=3、狸 flat=2/初始资金 30、_SELL_MULT 星级倍数与 fee=1(cost≥2 exempt)、STRATEGY_ECONOMY 实名 | 攻击纪律明令「数值锚一律直调代码注册表来源复核」;canonical 枚举表/E_gate^upper/判停门槛全部承重于这些常量 |
| B 策略器侧行号锚现树验证 | kernel(cw_investments/cw_economy/cw_effect_ledger/cw_state/cw_strategy_session/cw_plane_table)、obs(cw_observation/cw_settlement_obs)、telemetry/state.py、operations handler 写入端、tools/cw/proofs、不存在符号反向验证(INVEST_MUTATIONS/PLANE_LENGTHS_TRUTH) | 判据族/锁存族/触发器族的现行态锚,均非流程豁免面;历轮(R185/R186/R187)修过的锚族恰是漂移高发区,值得全量再扫 |
| C 文档内部自洽机械复核 | IMPL_DESIGN L3 NMF 实指位清单计数(45=37 单计+四行×2)、economy L5 清单(18 实指位)、canonical 表行数(15)、telemetry 键名索引(15 键节) | 机械可复算断言,零主观裁量,可证伪性最强 |
| D 建模对象对照玩法文档 | docs/game/currency_war/research/economy.md:利息律 gold//10 cap5、卖出退金(1★=cost/2★=3c/3★=9c,仅 cost≥2 −1)、升帽变体(开源节流 9/利息上调 10/买断制息关/狸 flat+2) | 「公式对」与「对得上游戏」是两道独立的门(攻击纪律②③) |

## ② 新症逐条

### 症 1(中)锁存写入端符号/文件锚在全树不存在——现行态规格指向已消亡的载体

- **三元组**:
  - 文档位:design_latch.md L9(§L1「写路径=operations 层共享 op `HandleInvestStrategy`(`operations/handlers/handle_invest_strategy.py`)→ session 字段」,引注 [现行=R74-2])、design_latch.md L19(§L2 置位谓词第 1 条「`HandleInvestStrategy` 在 `货币战争-投资策略` overlay 屏 OCR 读三卡名…」,引注 [现行=R76-5])、IMPL_DESIGN.md L85(R74-2 标「锁存的写入端=operations 层共享 op HandleInvestStrategy(R73-1 观测载体迁移的落点…)」)。
  - 检验式:`grep -r "HandleInvestStrategy|handle_invest_strategy" src/sr_od/` → **0 命中**(本轮亲跑;glob `**/handle_invest_strategy.py` 亦无文件)。现行实态:`operations/cw_screen/cw_screen_invest_strategy.py` 类 `CwScreenInvestStrategy`,OCR 三卡名→decide_invest→`match.session.active_strategies.append(chosen)`(L184,L182-184 去重防重 append)。
  - 结果:**不成立**。三处「现行态」锚指向的类名与文件路径双双不存在;机制本体(投资策略 overlay 屏 OCR→session.append)在 `CwScreenInvestStrategy` 上成立,但载体声明失真。
- **辖域判定**:策略器侧照常立案——该锚是锁存族(cap_sup_latched)写路径的**载体规格本体**:canonical 枚举表行 10(E4.2)明文「可达性=once-seen 锁存…载体/置位谓词/sim 等价物/持久化规格单一源=design_latch.md §L1-§L3」、行 12/行 13 同指;Latch §L2 全部置位谓词机制(精确 dict 查询/miss 不置位/override∈{9,10} 命中)挂在 `HandleInvestStrategy` 名下。按 §L1 落码的实现者找不到该符号/文件,恰是 R6-5「实现者遇缺输入自造方向」的载体缺口形态。LEMMAS R73-1 行(L3047)曾登记「handle_invest_strategy/画面档/recognizer 为代码面既有事实登记」——该「既有事实」在现树已不成立(重命名/迁移后 latch 现行态未随迁,版本轴漂移;R95-A4「全量转录=活体漂移通道」的符号名轴实例)。
- 证据批时快照:本轮亲跑 grep/glob/read(cw_screen_invest_strategy.py L130-212 亲读,append 与 `match is None` 局外分支、L197 未注册名告警均在)。
- 严重度:**中**(现行态规格的写入端载体指错;判据语义不受影响——机制在真实载体上存在)。

### 症 2(低中)GameState 生命周期锚「obs L1691 每备战帧新建」漂移 +160 行

- **三元组**:
  - 文档位:IMPL_DESIGN.md L85(R76-1 标:「GameState 系逐帧快照(obs L1691 每备战帧新建、L1925-1928 由 session 回填)载不住 once-seen 锁存」)。
  - 检验式:`grep "def read_game_state" src/sr_od/application/currency_war/obs/cw_observation.py` → **L1851**(非 L1691);L1925-1928 现文=session hp 对账区(`_had_real`=L1925,`reconcile_hp(_sess_hp,…)`=L1926-1927)——回填半边锚在位,新建半边锚漂移。
  - 结果:**半边失效**。「L1691」落点现为 read_game_state 之前的其他代码;R76-1 载体裁决(StrategySession 承载、GameState 禁承载)的两条代码证据之一锚失效(结论本身另由 cw_state.py L157 docstring「一回合决策时的局面快照」独立承载,该锚本轮亲验在位,latch L11/R187 标所引正确)。
- **辖域判定**:策略器侧照常立案——GameState 生命周期是锁存载体裁决(R76-1)的承重论证,obs 层新建点=「逐帧销毁」主张的直接代码锚;非流程执行细节。
- 严重度:**低中**(单边锚漂移,结论有第二锚独立承载;但 R187 轮刚修过 latch 侧同族锚(R187 症1),IMPL_DESIGN 侧姊妹位点漏扫,系「修一侧漏一侧」病类的又一实例)。

### 症 3(低)结算守卫锚 `_GOLD_AMT_RANGE`(L251)/`_GOLD_STREAK_PINNED`(L253-257)实位漂移至 L281/L287

- **三元组**:
  - 文档位:IMPL_DESIGN.md L522(§6.4 步 6,R86-4 行为锚两件:「守卫撤除辖域=仅 `_GOLD_AMT_RANGE`(cw_settlement_obs.py L251)的 interest 键,base(0,99)/streak(1,9) 两键守卫保留、与 `_GOLD_STREAK_PINNED`(L253-257)交互不动」)。
  - 检验式:`grep "_GOLD_AMT_RANGE|_GOLD_STREAK_PINNED" …/obs/cw_settlement_obs.py` → 定义实位 **L281**(`{'base':(0,99),'streak':(1,9),'interest':(2,9)}`)与 **L287**(`{0:1,1:1}`);L251/L253-257 现文=`_gold_token_cy` 函数 docstring,与守卫无关。同段「两路(粘连直读路径 L296-300/右列路径 L304-317)」锚:该区间现文=解析 docstring 步骤①-④与函数体开头,代码路径实体在 L334ff(`_lo,_hi=_GOLD_AMT_RANGE[key]`=L334;`_GOLD_STREAK_PINNED[_count]`=L348-349)。
  - 结果:**不成立(锚失准)**。值内容(base(0,99)/streak(1,9)/interest(2,9) 对 cap=10 构造性误杀=撤除对象)与现行代码一致,行号锚全体前移失准;interest 键 (2,9) 守卫在现码仍在位(与 R86-4 系落码批测试位、非已执行修复的定位自洽,非行为面矛盾)。
- **辖域判定**:策略器侧照常立案——结算屏三分量解析=扣减式触发器判定证据(`parse_settlement_gold_detail` 通道)与 R86-4 测试位锚的观测层规格,非流程豁免文件。
- 严重度:**低**(纯行号锚漂移,符号名+值域均单义可解析;LEMMAS R86 批零冲突自查引「L251/L253-257/L296-300/L304-317」同批时点为真,后经 docstring 扩写漂移——R187 症2 的 docstring 扩写致漂同型)。

## ③ 流程锚-豁免清单(不计数)

| 文档位 | 锚 | 现树状态(本轮亲验) | 处置 |
|---|---|---|---|
| design_latch L13(R184 退役同步标) | cw_loop.py L123「PREP_SETTLE_S 备战稳定门已退役(W971 §2.6/03-prep §1)」明文 | 明文实位 **L138**(L123 现为 FRONTLESS_REDEPLOY_LIMIT 常量注释);L123-125「触发计算式追加等待」段亦随漂 | 流程锚-豁免(cw_loop.py 明列豁免文件) |
| design_latch L13(R184) | cw_loop.py L620-631(0e 投资策略 overlay 分支,L630 id_mark 检测)vs L868-875(备战双锚分支) | 0e 分支现位 L620-630 大体在位;备战分支锚漂至 ~L906-939 区(「返回投资策略选择」symptom 分支 L931-939) | 流程锚-豁免 |
| telemetry L151/L193/L194 等 | sim/engine_p1.py L758(利息行)/L770-771(append 唯一现位)/L762-766(时序注释) | 本轮亲验:**在位零漂**(L758 `'interest': min(_icap, st.gold // 10)`、L771 append) | 流程锚-豁免(申报:现值无漂移,非失真) |
| IMPL_DESIGN L85(R75-2 标) | sim/cw_sim_invest.py L34-44/L141-160(日程直注单名) | 未逐行复核(时间预算);sim 基建族 | 流程锚-豁免 |

## ④ 冻结残余对账节

**我数出的申报数:11 项 = LEMMAS 侧 8 + telemetry 侧 3,与文档申报一致,零重复立案。**逐项:

| 侧 | 项 | 内容 | 载体现状(本轮亲验) |
|---|---|---|---|
| LEMMAS | 1 | C_int cap_sup 化缺触发救援型双向不对称分析 | LEMMAS L3374 在案 |
| LEMMAS | 2 | 有效性门估计量与门目的错位(缺未触发对照腿) | L3375 在案 |
| LEMMAS | 3 | 有效性对照统计单元=帧(序列相关未申报) | L3376 在案 |
| LEMMAS | 4 | R65-1 两处落位缺口(v6 行 10 q/种子;⑱(h) 锚) | L3377 在案;telemetry 正文 L79 以「第 4 项」指涉=同项引用非重复申报 |
| LEMMAS | 5 | N_gate 无版本锚/重估触发器 | L3378 在案 |
| LEMMAS | 6 | R65-4 构成协变量条件化充分性前提过强 | L3379 在案 |
| LEMMAS | ~~7~~ | R6-8 行头钉死公式双源矛盾 | **已销账**(R182 销账标在案,R178-症1 修复消解;计数 12→11) |
| LEMMAS | 8 | R68-a §5.2 窗口高侧预算未 cap_sup 化 | L3381 在案;telemetry L53「第 8 项」指涉=同项 |
| LEMMAS | 9 | R68-b「濒死带 λ̂_U~0.3」旧坐标 | L3382 在案;telemetry L41「第 9 项」指涉=同项 |
| telemetry | 10 | 激活率门行 L67 裸 cap 位点(R98 节,编排者裁决增补) | R98 节 L344-350 在案(现位申报 L349) |
| telemetry | 11 | L69 激活率门验收级段滞后(R115 节;R184 并入辖域扩展申报) | R115 节标记句现位 L929(R174 现位申报在案) |
| telemetry | 12 | L75 D_ε 门监督面引注滞后(R162 节) | R162 节 L2109 在案 |

计数链核:R162 起 12 项 → R182 销账第 7 项 → 11 项;最新两轮(R186/R187)均按「LEMMAS 9−销账 1=8+第 10/11/12 项=11」申报,本轮独立复算吻合。正文三处「第 4/8/9 项」指涉与 LEMMAS 清单编号一一对应、非独立第二源,无重复计项。

## ⑤ 清洁门申报

**本轮新症总数:3(症1 中 / 症2 低中 / 症3 低)。**

- 数值锚面(A)与建模对象面(D)本轮**零新症**:全部数值锚(cap/streak/loss/乘子/flat/初始 30/先验 (9,9,9)/BENCH_CAPACITY=9/星级倍数与 fee 豁免)与代码注册表逐一吻合;建模对象(利息律/退金规则/升帽变体语义)与 research/economy.md 及注册表注释(带 BWIKI/4399/live 实测溯源)一致——此为如实申报的通过结果,非未查。
- 文档内部自洽面(C)零新症:IMPL_DESIGN L3「共 45 实指位=37 单计+L128/L133/L217/L274×2」本轮 grep 亲算 48=自指 3(L3×3)+实指 45,恰合;economy 18 实指位清单逐行亲算恰合(L5 头注自指 token 增至 5,系史标累积、辖域外在案);canonical 表 15 行、telemetry 键名索引 15 键节均亲数吻合。
- 不存在符号反向验证通过:`INVEST_MUTATIONS`、`PLANE_LENGTHS_TRUTH` 全树零命中(与 E3 登记址纠错、§6.1 删除声明一致);`STRATEGY_ECONOMY`(L149)、p47_check.loss_exact(L45)、telemetry/state.py L58 注记均在位。
- 冻结族禁攻击面(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置)本轮零触碰、零新增装置提案;冻结残余零重复立案(见④)。

∎
