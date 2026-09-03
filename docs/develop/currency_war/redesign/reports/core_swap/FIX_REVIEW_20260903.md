# CW 新核三批修复治本性独立复审(FIX_REVIEW_20260903)

> 复审者=独立 review agent(2026-09-03,用户裁定「修复批后必跟 review agent」)。
> 对象:零刷新修复(ZERO_REFRESH_FIX_REPORT)/ K 空窗回退(K_FALLBACK_FIX_REPORT)/
> 判据契约化(CONTRACTS_REPORT)。方法:三问(修的是根吗/引入新问题吗/防线是真防线吗),
> 证据亲验(代码亲读 + 对抗场景亲跑),修复批自评不采信。
> 对抗脚本=`fix_review_adv_20260903.py`(本目录,零仓库代码改动),输出=`fix_review_adv_20260903_out.txt`。
> **现场声明**:复审期间标定批并行在飞——复审中途 `shop.py` r1 块被改写
> (「有值即放行」→ `r1_commitment_account` 总账),`criteria/refresh.py` 新增
> `r1_commitment_account` 函数。本文对 r1 的判决基于修复批提交时点形态(报告+当时亲读),
> 并行批现场另行标注。

---

## ① 逐修判决表

| 修 | 判决 | 根因层 → 修复层 | 检验式(可推翻条件) | 关键证据 |
|---|---|---|---|---|
| **r1 零刷新接线** | **补丁**(显式登记的战术过渡,非治本) | 根有双层:(a) 实现缺口=字面量 None 绕过槽位(接线层)——修在接线层 ✓;(b) R1 门形态=P40 启动门总账缺位(规格落码层)——修法落「有值即放行」,未触 | 注入 V_GAP 后刷新 40-67/局 ≈ 反事实 C 的 61-67(诊断 §5 已证该形态 final_hp 更差)⇒ 诊断 §6.2 回归判据「0<refreshes≪60+」**不成立**;`v_gap.value` 在过渡形态中只做 None 判断、数值从未进判据(shop.py 旧形态 `r1_start(None if v_gap is None else True)`)=诊断 §6 禁令 4「r1 传 True」形态加了槽位门 | ZERO_REFRESH_DIAG §5 反事实 C 表;修复报告 §1/§5.1 自认;并行批正在落 `r1_commitment_account`(总账)反证根在标定批。**可推翻条件**:若判据把「实现缺口闭合」独立视为根,则接线本身治本——但回归判据未达,不采 |
| **arm1 deploy_cap** | **治本**(域错位层,带两个可推翻缺口) | 根=谓词输入域错位(固定槽表常数 DEPLOYED_CAPACITY=10 当板满阈值,而板面受等级 cap 约束)→ 修复=参数化 + 两消费位接 level-driven cap + docstring 判据 + 契约(deploy_cap 非 None)。诊断→修法同层 ✓ | 谓词单测(cap=5 板满真/板未满假/None 兜底)+ M3 行为锁全绿(亲跑);sim 池化 LevelUp 21>0。**可推翻缺口 A**:mandate.py 消费位旁路(见③②);**缺口 B**:两消费位 cap 真值源不同(见②-3) | predicates.py:18-58 亲读;`test_cw_zero_refresh_fix.py::TestArm1CapSemantics` 5 用例亲跑绿;`fix_review_adv` 场景 A 证明旁路 |
| **K 空窗回退** | **治本**(本病灶;泛化步不完整) | 根=「旧核空窗行为未进规格即被丢弃」(target_comp 值域全集缺 None 端)→ 修复落在**规格层**(IMPL_DESIGN §4.2.2 补注)+ 单一源回退(hoard_target_set,禁复制)+ 契约登记 + 7 条行为锁 + n=100 反事实复验(零动作 21→0,受累局 hp 16.05→33.52 与反事实逐位一致)。修在根层 ✓ | 行为锁+复验数字(报告 §3/§4);`p1_gap_window` 与 `_derive_p1_pair` 同源同门槛(cw_intention.py:496-529 亲读,判据数学零改动属实)。**可推翻条件**:②清单 1/2(P1 死带、P2+ 无回退)任一在实机/sim 复现为整局级零动作 ⇒ 「值域全集覆盖」承诺未兑现 | shop.py ①段回退分支亲读;对抗场景 C/D(见③)证明值域覆盖只有 P1 空窗半边 |
| **判据契约化(R198)** | **结构治本**(纪律基建),接线完备性申报不实 | 根=「语境前提未被核验」类缺陷的组合性(零刷新/arm1 两案同族)→ 修复=谓词级契约注册表 + 消费位核验 + 静态完备性对拍。方向正确且**静态门真抓错**(见③②旁证) | 完备性测试亲跑**红**——并行批新增 `r1_commitment_account` 未登记即被 `test_covers_all_criteria_public_functions` 抓住 = 防线有效性实证。**可推翻缺口**:消费位接线不完备(mandate.py 漏接,报告 §3「全部消费位」申报与实况不符)+ 自我声明式前提零检测力 | contracts.py 全文亲读;对抗场景 A(mandate.py 旁路零违例计数);grep 消费位清单见②-5 |

---

## ② 泛化扫清单(同族点 / 旧核规格外行为缺口)

### 同族点(固定常数当动态阈值 / 域错位,arm1 修复批未做的谓词族泛化步)

| # | 位点 | 证据 | 判 | 建议立案级别 |
|---|---|---|---|---|
| 1 | **arm1 cap 双真值源**:shop.py 用 `state.max_units()`(注册表 level+宝钻推导);mandate.py 用 `frame.deploy_cap = obs.deploy_vacancy + len(deployed)`(entry.py:400)= paddle cap − paddle dep_n + CV occupied 的**观察复合**——两源可漂移 | cw_screen_prep.py:565-590:dep_n 双源 spread≤1 **静默容忍**;cap/dep_n 缺读走 `_cached_vacancy`(可过期)。漂移 ±1 时 mandate 侧板满判定错档 | 同族弱形态:谓词语义统一了,真值源未统一——「等级/cap 驱动真值源」纪律只落在 shop 半边 | 中:mandate 侧改 `state.max_units()` 或申报容忍带+漂移遥测 |
| 2 | `decision_v2/adapter.py:76-77`:snapshot.deploy_vacancy None → 0,而 decision_v2/contracts.py:183 注释明言「None=cap 未读(禁 0 兜底:0=无空位吞部署)」 | 亲读两处;0 兜底使下游 cap 复合 = len(deployed)(伪板满) | 旧核侧先在(非本三批引入),但 cw4 frame 口径同型暴露面 | 低(旧核域,冻结面另议) |
| 3 | `entry.py:398` `level=state.level if state else 3` 字面兜底;`shop.py` 各处 `cost if card.cost else 3` / `or 2` 系列 | 亲读;3/2 系注册表先例口径(cheapest_member_cost/REFRESH_COST_BASE)已登记,`level=3` 未 | 低风险字面,非 cap 域 | 低:随下次接线批收口 |
| 4 | `BENCH_CAPACITY`(=9)作 bench_free/重试上限 | ADR-0316 定长物理槽表,非常量驱动 | 非同族(物理常数合法) | 不立案 |
| 5 | `min(deploy_cap, DEPLOYED_CAPACITY)` 封顶 + None 兜底 10 | predicates.py:40-41,保守端已申报 | 合法保守 | 不立案 |

### 旧核有、规格无、新核丢(旧核 decide_shop_screen 消费链逐面对比)

| # | 缺口 | 证据(亲验) | 建议立案级别 |
|---|---|---|---|
| 1 | **P2+ target_comp=None 无 K 回退**:旧核 hoard_target_set P2+ unlocked=绯英⑤兜底采购集(11 件)/weak=跨线骨架/demoted=骨架满配;新核 shop 回退分支 `plane==1` 限定 ⇒ K=() ⇒ M2/支撑通道全死 | **场景 D 实证**:plane=2、target_comp=None、店内在售+金 80 ⇒ 买入 0;同帧旧核 hoard_target_set mode=fallback n=11 | **高**:K 回退值域覆盖只有 P1 空窗半边;「旧核有、规格无、新核丢」的正例 |
| 2 | **P1 锁线过渡死带**:支持度 ≥0.5 但 pair 未锁帧(update_intention 逐 game-round 跑,shop 波内滞后)⇒ gap_window=False 且 target_comp=None ⇒ 不回退+零买入;旧核同帧有 `p1_early_pair`(无门槛 top-2 方向,decision_v2 handoff/discipline 消费) | **场景 C 实证**:bench 三仙舟件(支持度 1.0)、target_comp=None、店内仙舟件在售金 60 ⇒ 回退计数 0、买入 0 | 中:与 #1 并案(K 投影域覆盖 None 的另一半端);K 批呈报项只报了首波 intention-None 边界,此带未呈报=泛化步不完整 |
| 3 | **空窗回退无方向性**:回退集=四体系全集 `sorted()`(字母序)逐名买;旧核空窗期消费链经 p1_early_pair/scoring 有 top-2 支持度方向 | shop.py 回退 `tuple(sorted(...))`;cw_intention.py:571-599 p1_early_pair 旧核消费 grep 实证 | 低-中:影响空窗买序质量(先买谁),非死锁 |
| 4 | drought 计数器 cw4 侧纯影子(无行为消费端;drought→drought_excluded 接线=过线后批) | proof.py:73-76 申报在册 | 信息(已申报,非缺口瞒报) |
| 5 | 金位边界:gold=0 各门 fail 方向保守(r2 gold−0≥2 拒/M2 check_affordable 拒/funding 通道 gold<need 触发)✓;溢金 M6 受 T_SEARCH fail-closed(溢余滞留遥测在)✓ | shop.py 亲读 | 无缺口(两边界已核) |

---

## ③ 防线对抗测试结果(全部亲跑,`fix_review_adv_20260903.py`)

| 对抗场景 | 结果 | 结论 |
|---|---|---|
| **①活性守卫豁免绕过**(注册豁免但槽位有值) | 豁免判据=`all(is_none(s))`(ab_core_swap.py:246),注入即失效——测试 `test_opened_slot_removes_exemption` 亲跑绿;豁免推导方向正确 | **真防线(存在性下界形态)**。弱点:①`FAMILY_PROVISIONAL_DEPS` 手工登记——未来新增「全路径 fail-closed 于新槽位」的族须同步维护,漏登=假阳性 raise(烦不危险);②n=10 固定 seed 0-9 且 simulate_p1=planes1,其它 seed/P2+ 饥饿不可见(已申报「存在性非分布」,如实) |
| **②契约层旁路**(绕过 ensure_contract 直调判据) | **旁路可达,实证**:`mandate.py:298` `predicates.arm1_existence(...)` 直调、无 ensure_contract——构造 cap=固定常数 10 的域错位形态喂入 ⇒ **零违例计数 + M3 照发**(场景 A)。同款漏接:mandate.py:300/303(lv9_stop/spend_unified)、shop.py:332(proof.stop_buy,None 前提空转)。CONTRACTS_REPORT §3「shop.py:(全部消费位)」申报只对 shop.py 成立,mandate.py 消费位漏接未申报 | **部分防线**:注册表+静态完备性门有效(亲见其抓住并行批未登记的 `r1_commitment_account`);但消费位核验=约定层,旁路无静态守卫。另:自我声明式前提(`ev_input_wired=True`/`k_none_domain_covered=True` 由消费位硬编码)对「回退字面量但保留声明」的复发形态**零检测力**——真正有检测力的是检查实参的前提(k_members/deploy_cap/gold-reserve) |
| **③v6 checklist mark 行随意标绿** | **实证可标绿**(场景 B):`record_v6_landing(4, '随便写的证据')` ⇒ 行4「已落地」,evidence 文本从不被读取。text 行=存在性检查(`'mandate_v1' in ab_judge.py` 文本)——注释里写这个词也绿。order 行=自报时间戳 | **流程性防线,非核验性防线**:对「诚实操作者忘标」有效(零刷新事故的排程层复发面),对「随手标绿/文本游戏」无效。修复报告 §3 呈报「本批只代码化门,不替任何行做申报」属实——门本身不校验申报内容是其既知边界,建议 mark 行至少把 evidence 落盘可审计(现为进程内易失) |

**三批测试亲跑现状**:`test_cw_zero_refresh_fix.py + test_cw4_contracts.py + test_cw4_shop_line.py`(not slow)= **68 passed / 2 failed**。两条红均系**并行标定批过渡态**(非三批遗留):①`test_covers_all_criteria_public_functions` 红=新函数 `r1_commitment_account` 未登记 CONTRACTS(静态门正确抓错);②`test_injected_value_opens_r1_into_r2` 红=总账门上线后注入 V_GAP=10.0 不再无条件放行(旧测试断言过时)。归属并行批收口,不判给三批。

---

## ④ 返工清单(仅必须返工项)

| # | 项 | 根因层 | 应修层 | 归属 |
|---|---|---|---|---|
| R1 | **mandate.py arm1/lv9_stop/spend_unified 消费位补 ensure_contract 接线**(或 CONTRACTS_REPORT §3 更正申报面为「shop.py 全接、mandate.py 部分接」——当前申报与实况不符) | 接线完备性(契约纪律自身条款 2「接线核验点」未兑现全集) | 接线层,一处文件小改 | 契约化批补件(或其收口批) |
| R2 | (并行批义务,非三批)`r1_commitment_account` 登记 CONTRACTS + 消费位接 ensure_contract + 旧注入测试改总账口径——两红在案 | 新增判据未同步登记(违 R198 纪律 3) | 注册表+接线+测试 | 标定批(在飞) |
| R3 | **K 投影域覆盖缺 P2+ 与 P1 锁线过渡带**:按 IMPL_DESIGN §4.2.2「值域全集含空窗期」的承诺口径扩规格(场景 C/D 均为「值域含 None 但回退不辖」的正例);K 批呈报项未含此两带=泛化步不完整,应补呈报并立案 | 规格层(值域覆盖声明与实现不一致) | 规格层先行(§4.2.2 补注扩域)→ 回退分支跟进 | 新立案(K 回退泛化案),非三批返工 |
| R4 | (建议级,非阻塞)mandate 侧 arm1 cap 真值源改 `state.max_units()` 或申报观察复合容忍带+漂移遥测(②-1) | 真值源双源漂移 | 接线层 | arm1 批补件或随 R3 批 |

## 总评

三修方向均与各自诊断的根因层对齐(无「根在 A 层修在 B 层」的错层),这是比此前逐症状补丁的实质进步。但按敌意口径:**r1 修是登记规范的战术补丁**(约束力判据未达,有害形态在注入态原样可达,治本动作正在由并行批执行);**arm1 与 K 回退是治本**,各自带可推翻缺口(K 的两个值域半边、arm1 的旁路+双源);**契约化是结构治本但其「接线完备」自评不实**。防线三件套中,静态完备性门与活性守卫是真防线,v6 mark 行与自我声明式契约前提是流程性/文档性防线——不宜在呈报中与前者并列为「代码化防线」同级强度。

> 复审零仓库代码改动;产物=本报告 + `fix_review_adv_20260903.py` + `fix_review_adv_20260903_out.txt`(均在 core_swap/)。
