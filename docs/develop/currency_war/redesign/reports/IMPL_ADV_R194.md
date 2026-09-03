# IMPL_ADV_R194 · 货币战争策略器重构设计文档对抗审查 第194轮(无锚轮)

> 攻击者=全新视角。对象=redesign/ 四文档正文(§6.4-R 与 R189-R193 修注链为主攻)+CONTRACT_V2_PROPOSAL.md(R193 修正版提案件)+IMPL_FIX_LEMMAS.md(冻结对账)+**已落码实现中间态**(步1 包装适配器/步2 cw4 包,在树可攻)。CONTRACT_SERIES_DECISION.md(v1)=参照件不立案。无锚自选攻击面=数值锚直调(λ 表 JSON/P47 递推/provisional 槽位)+提案自洽(编号/辖域/双源三查)。

## ① 攻击计划(成形于任何登记节/IMPL_ADV_* 读取之前)

1. 通读四文档主攻面:IMPL_DESIGN §6.4-R 全节(L517-616,含 R189-R193 全部修注链逐条读毕)、CONTRACT_V2_PROPOSAL.md 全文、CONTRACT_SERIES_DECISION.md 全文、IMPL_FIX_LEMMAS 冻结残余清单节;NMF §3.3/§3.4 按需读。
2. 自选攻击面(三条轴):
   - **轴A 数值锚直调**(攻已落码 cw4):λ 表 JSON 48 格 vs p51_v33_run.txt Part 3M/Part 8 逐格对账(独立 node 脚本重算 Wilson);P47 递推(cw4/statefn/interest.py loss_exact)vs tools/cw/proofs/p47_check.py 同名函数全域网格对照;audit/provisional.py 槽位表 vs NMF §3.3 逐行映射;horizon 长度常量纪律;cap 值域(9/10/0)vs cw_investments 注册表直调。
   - **轴B 提案自洽三查**(攻 v2 提案):词表 17 类计数 vs cw_prep_actions.py 亲读;§3.1 商店线行内容 vs v1 §3 逐行 diff;代码锚(candidates/remediation/cw_evolution 发射位)内容锚亲验;编号/diff 清单与正文互查。
   - **轴C 修注链专项**:R192 反转标(包装子类)vs 现树实施形态;R193 五症修注的引注/辖域申报复核;R190/R191 重编号链一致性。
3. 计划成形后才读 design_telemetry 登记节(仅用于④冻结对账);IMPL_ADV_*.md 全程未读。

## ② 新症(4 症,每症=三元组:文档/代码行号+检验式+结果)

### 症1(中)λ 表 JSON 单格 ci_lo 与权威工件 Part 8 标签值不符——直调复核 48 格中 1 格失配

- **三元组**:`src/sr_od/application/currency_war/decision/cw4/statefn/data/lambda_death_pl_v33.json` cells 键 `D1|hp>40|P1|encounter` 亲读=`{"n":15,"raw":0.733,"mono":0.708,"ci_lo":0.463,"ci_hi":0.889,"label":"可消费"}`;权威工件 `.debug/temp/currency_war/redesign/p51_v33_run.txt` L254(Part 8 标签行)=「D1 hp>40 P1 encounter: n=15 原始=0.733 单调=0.708 → 可消费(薄 n=15,**CI 下限强制 Wilson=0.480**)」。检验式=独立脚本逐格对账 48 格(n/mono/ci_hi/ci_lo/label,薄格 ci_lo 按 Part 8 Wilson 值、其余按 Part 3M bootstrap 下限;独立重算 Wilson(11/15, z=1.96)=[0.4805,0.8910] 亲跑):47 格全对,唯此格 ci_lo 0.463≠0.480。
- **结果**:失配。根因=生成器 `tools/cw/proofs/p51/gen_pl_v33_json.py` L106 `if wm and float(wm.group(1)) < cell['ci_lo']: cell['ci_lo']=...`(仅当 Wilson **低于** bootstrap 下限时覆盖)vs 工件 Part 8 末行(L290)「薄格报告值=单调池化值…,CI 下限**强制取**该格原始 n 的 Wilson 下限(不吃池化方差)」的无条件措辞——两读在唯一 bootstrap_lo(0.463)<Wilson(0.480) 的格上分裂。消费影响:`lambda_ci()` 返回下端 0.463(应 0.480)→ 检测端 λ̄_detection 取 CI 下端下移 0.017、`differential_composite` 的 d̂=CI 宽度 0.426(应 0.409)。JSON meta「薄格 CI 下限已按 Wilson 覆盖规则回填」的「覆盖规则」实为条件规则,与工件「强制」字面互斥。修法方向(供裁决):生成器改无条件取 Part 8 Wilson 值(以工件标签行为单一源)并重生成,或工件/生成器二择统一措辞后回写 JSON——禁只改 JSON 数字。

### 症2(中)statefn/interest.py loss_exact 与对拍锚 p47_check.loss_exact 在溢金域不同构——「全档位网格」对拍声明不成立

- **三元组**:`cw4/statefn/interest.py` L62 `a = max(min(max(gold, 0), gold_cap) - spend, 0)`(A 轨迹=**先截断到饱和线再扣** spend)vs 锚 `tools/cw/proofs/p47_check.py` L51-52 `b=min(g, GOLD_CAP); a=max(g-spend, 0)`(A 轨迹=**实金扣**)。检验式=同参双实现全域对照(独立 node 亲跑):(55,5,9,7)→p47=0/cw4=1;(60,20,9,7)→p47=1/cw4=3;(55,8,9,7)→1/1(同值)。失配域=gold>10×cap ∧ spend<gold−10×cap。
- **结果**:失配。锚自己的打印网格含 g=55 段(p47_check main L171-174「g=55 overflow segment」),而 interest.py docstring L6-7 声明「对拍锚=tools/cw/proofs/p47_check.py 的 loss_exact(**全档位网格**,§5.3 对拍『P47 L 递推』行)」——§5.3 对拍若按字面含溢金格必红,若排除溢金格则「全档位」声明为假,两读必居其一。语义向:cw4 把溢余重复花(先丢溢余再扣 spend),A 轨迹起点低估→息损高估→花费决策保守偏(方向申报,非中性)。溢金态真实可达(基础金值域 (0,99)>50,cw_settlement_obs `_GOLD_AMT_RANGE` base (0,99) 既有锚)。修法方向:A 轨迹改实金扣(对齐锚),或在 docstring+§5.3 对拍行显式收窄辖域并给「截断形态=保守向」论证——二择,禁维持「锚等价」字面。

### 症3(低中)provisional.py「静态登记 NMF §3.3 清单(13 项)」组成失真——#11 无槽、#2 拆二凑数,三处「13」互不同构

- **三元组**:`cw4/audit/provisional.py` L39-53 槽位表亲读:NMF §3.3 段=13 个槽,但映射 NMF §3.3 编号行(NEW_MATH_FRAMEWORK L181-195 亲读,#1-#13 共 13 行)后=#2(V_ms/V_gap)拆成两槽(V_MS/V_GAP),**#11(λ_death 连续模型)零槽位**;IMPL_DESIGN L624(§7.3)读法=「【拟】槽位(NMF §3.3 13 项…)**+ λ_death 分层表**」即 13+1 分立读。检验式:NMF 13 行 ∩ provisional 13 槽 逐行映射→12 行命中、#11 缺席;若按 IMPL_DESIGN 的「λ 表独立承载 #11」读法,§3.3 余 12 行≠「13 项」,provisional 的 13 槽计数仅靠 #2 拆分成立。
- **结果**:三处「13 项」三种组成(NMF=13 编号行含 #11;provisional=12 行+#2 拆二;IMPL_DESIGN=13 项+λ 表外挂)。#11 的实际载体=statefn/lambda_death.py(有据、纪律自洽),但 provisional docstring「静态登记 NMF §3.3 清单(13 项,批时快照)」的字面为假——审计面(slot_names 静态断言消费)拿到的 13 与清单组成对不上。修法方向:docstring 改「NMF §3.3 之 12 行(#2 拆 V_MS/V_GAP 两槽;#11 由 statefn λ 表承载)」,或补登 #11 占位槽并同步 IMPL_DESIGN 计数——二择。

### 症4(低)契约 v2 提案 diff 行 4「行内容承 v1」对 SwapDeploy 为假——正文新增枚举未入 diff 清单

- **三元组**:CONTRACT_V2_PROPOSAL.md L22(§3.1 拖拽族行)=「拖拽族(SellBench/SellDeployed/DeployMove/**SwapDeploy 系**/装备拖拽,商店线侧…)」vs v1(CONTRACT_SERIES_DECISION.md L67)拖拽族行=「DeployMove/SellBench/SellDeployed/装备拖拽」——SwapDeploy 在 v1 §3 零出现;diff 清单行 4(L65)=「商店线域行内容…**行内容承 v1**,枚举显式化消歧(拖拽族恢复 SellBench/SellDeployed/DeployMove 显式枚举+坐标系限定词;判语义零改义——R193 症1 裁定)」——只申报三显式枚举,**未申报 SwapDeploy 新增**。检验式:grep SwapDeploy CONTRACT_SERIES_DECISION.md=零命中(亲跑);grep SwapDeploy 现树=decide_shop_screen 管线现役发射(decision_v2/remediation.py L687 `SwapDeploy(d_idx, ben_idx, reason='remedy_slot',...)`、kernel/cw_evolution.py L1581)。
- **结果**:diff 清单与提案正文不一致。对 SwapDeploy 而言 v2 是**新分类**(v1 初始枚举缺项——现役商店线动作在 v1 表零分类,恰属 v1 §3「增补条目须回契约改版」纪律辖域),不是「显式化消歧」也不是「零改义」;diff 行 2 只申报备战线 12 类补全,商店线缺项补全漏报。修法方向:diff 行 4 补「+SwapDeploy 系(v1 漏列的商店线现役动作,判=拖拽族同款条件续)」申报;v1 本身不立案(冻结参照件)。

## ③ 豁免(本轮查了但不立案的)

- **流程侧代码锚漂移**:cw_screen_prep L1193/L1351、engine_p1 L768、decision_assembly 行号族——任务书辖域调整豁免;本轮亲验的 strategy 侧锚(candidates L504/L599/L616、remediation L340/L450、cw_evolution L1588)内容锚全部在位,零漂移零立案。
- **冻结族六面装置**(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面):禁攻击——本轮零攻击零新增装置提案(症1-4 全部为工件一致性/锚等价/登记组成/diff 申报问题,不触任何冻结装置本体)。telemetry L41/L53/L61/L67/L69/L75 族内位点零触碰。
- **CONTRACT_SERIES_DECISION.md(v1)**:用户冻结参照件——其拖拽族漏 SwapDeploy、初始枚举无 fail-closed 条款均系 v1 既有状态,不立案(只立 v2 提案的 diff 申报缺口=症4)。
- **批时快照行号漂移**(IMPL_DESIGN 修注链内大量 2026-09-03 快照行号):按快照单义规则豁免;本轮全部以内容锚复核。

## ④ 冻结对账(11 项,零重复)

- **LEMMAS 侧 8 有效**(IMPL_FIX_LEMMAS.md L3374-3382 九项亲读):第 1(C_int cap_sup 化双向不对称)/2(有效性门错位)/3(统计单元=帧)/4(R65-1 落位缺口)/5(N_gate 版本锚)/6(协变量充分性)/8(§5.2 窗口高侧预算 R68-a)/9(λ̂_U~0.3 旧坐标 R68-b)在位;**第 7 已 R182 销账**(L3380 销账标亲读:R178-症1 修复批消解,计数 12→11)。
- **telemetry 侧 3 项**(design_telemetry.md 登记节,计划成形后读):第 10 项(R98 节「冻结残余清单增补:第 10 项」,对象=L67 激活率门行 cap 未 cap_sup 化,L344 节头亲读在位)/第 11 项(R115 节标记句现位 L929「冻结残余计数自此=11 项」亲读,对象=L69 激活率门验收级段滞后,R184 并入辖域扩展申报 L2337 在位)/第 12 项(R162 节 L2109 表行亲读,对象=L75 D_ε 监督面引注零同步)。
- **零重复核**:LEMMAS #8(design_telemetry L53 窗口高侧预算)与 telemetry #10(L67 激活率门行)系同病类不同位点,既有申报分立(R98 节登记口径),非重复;本轮零新增冻结项、零销账。

## ⑤ 清洁门申报

- 禁凑数/禁压症:4 症全部有独立检验式与现树/工件亲验,每症给出修法方向但未代裁;查而不立的轴(修注链 R190-R193 编号一致性/包装子类实施形态/词表 17 类计数/cap 值域/horizon 纪律/audit derived 登记)均已亲验通过,未为凑数降格立案。
- 数值锚直调:症1/症2 均用独立脚本(node)重算,非被审方实现自证;症3/症4 为文档-代码/文档-文档互证。
- 文件面:唯一写入=本报告(.debug/temp/currency_war/redesign/IMPL_ADV_R194.md);零源码、零 git、其余文档零触碰。
- 无锚纪律:计划成形前未读 IMPL_ADV_*.md(全程未读)与 design_telemetry 登记节(仅④节对账时读);先通读(①)后计划后执行,时序如实。
