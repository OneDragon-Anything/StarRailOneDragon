# ADR-0594: 域①终局清算落码(P81;T-143 S2′ 双落点+域①豁免行三件套+卖出腿最小面)

- **Status**: 已实施(方案 v2 二轮对抗审放行[零阻断,报告=`.debug/temp/currency_war/attacks/t143_endgame_liquidation/方案审-v2.md`];编排者裁决固定:候裁#2 双落点都做/#4 段帽生产硬墙不动+sim 豁免行旁路/#6 P68=本批申报收窄关系;commit 候编排者统一门)
- **Date**: 2026-09-08
- **方案**: `.debug/temp/currency_war/t143_endgame_liquidation/方案.md`(v2;本批后 as-built 注已回写其 §8)
- **命题**: math_proofs **P81**(S2′ 终局清算弱占优;域①=「位面末 boss 备战帧 ∧ 本位面=本局末位面」主定理辖域,持金未来效用 ≡0 + 消费纯金流成本 ≡0 ⟹ 当帧可兑现消费弱支配持金)
- **病理与实证**: 找问题-第二跑 §3.5/§五(带金死 6/9,20260952 R9 位面末 ALL IN 豁免只兑现升级批余 48 金沉没)+ **找问题-第三跑 N2**(`.debug/temp/currency_war/t120_sim_redesign/找问题-第三跑.md` §五/§六:20260958/20260976 R9「闸开≠臂发」——ALL IN 豁免只辖预算闸可行性,发射量挂 arm1 板满谓词,lv5 cap 松开臂即停,48/50 金死 ⟹ 清算臂辖域判据必须独立于 arm1);成型线面 = `cw_launch_arbitrage.py` 自述(终局金中位 96-196,boss 轮零动作)
- **关联**: ADR-0566(发射帧仲裁;本批=其拓扑的域①扩展)、ADR-0557(发射短路零改)、ADR-0576(P72 全段预算闸;ALL IN 豁免支的域①邻接,闸本体零改)、ADR-0585(卖出仲裁;通道对价段「终局清算」豁免行接入其 §4 N4 预留扩展位)、P70/P72(域①外辖域逐字零改)

## 1. 背景与归层

S2′ 病理 = 对局终局帧带金死:非成型线的升级通道在 ALL IN 豁免放行第一批升级后续批停发(N2:发射量挂 arm1,lv5 cap 松开板不满即失效);成型线(armed)发射帧带内段(g≤g\*)fail-closed 零执行。两面的共同根:**域①帧上「金无机会成本」的豁免语义缺位**(息线地板/带内 fail-closed/升级臂触发面都按「金有未来价值」建模)。归层 = 决策层(金出口豁免语义与循环序缺臂),数学授权已备(P81 已证,零标定)。

## 2. Considered Options

- **只修一面(单落点)**:✗否决(编排者裁决#2)——病理 20260952(非成型线,金 48)与出口 B 自述(成型线,金 96-196)分属两面,只修一面另一半死金原样。
- **清算臂自建评估序**:✗否决——金出口族红线 1(不新造第二套评估语义);本批「花什么」全部复用既有单一源(can_deploy_single/merge_buy_completes/fuel_sell_candidates/levelup 判据族/装配 A)。
- **扩 SELL_CHANNELS 新通道值**:✗否决——sell_gate 属禁碰文件面(在飞批交接面);对价豁免落在触发面(新发射位+新 reason 通道值登记),排除面复用 m4_fuel 视图,语义等价且经 ADR-0585 §4 N4 预留位接入。
- **双落点 + kernel 豁免语义单一源(本批)**:✓采纳实施。

## 3. 实施形态

1. **域①判定函数(kernel 判定核单一源)**:`cw_launch_arbitrage.endgame_liquidation_frame(state, session)` = `plane_last_battle`(单一源委托)∧ `is_final_plane`;`run_plane_count_of(session)` = 载体声明属性 `run_plane_count`(缺省回退 `PRODUCTION_PLANE_COUNT=3`,gameplay.md 结构真值;sim 假局载体=1 由声明方写入)——**不动 `schedule_of`**(B1 修法路线 (a),防污染 r_global 既有消费面;禁由 plane_lengths_seen 长度推断,生产 P1 帧该序列长度=1 而本局仍 3 位面)。帧态不全(round_num 缺)= 不可判 → fail-closed False。
2. **落点一(成型线)豁免行三件套**:
   - **带内 range(0) 解除**:`cw_economy.in_launch_spend_zone`(zone 判定单一源,两面循环体各恰调一次/帧)增域①释放支——金>0 即出 True;分键 `launch_arbitrage_endgame_frames`(KEY_ENDGAME_FRAMES)随释放支同源 best-effort 计数(判定核零写端纪律的让步:两面循环体外唯一共用缝,ADR 申报);
   - **地板降 0**:`launch_arbitration_gate` 域①帧花后 ≥0 放行(P70 边界 1 的域①豁免——息线地板保护对象〔未来息流〕在域①不存在);非域①帧逐字走既有 g* 地板零漂移;
   - **段帽处置(裁决#4)**:生产 MAX_REFRESH 硬墙不动;sim 侧带内解除使域①帧段预算从 0(range(0))解放到既有 LAUNCH_ARBITRAGE_SEGMENT_CAP=5,「金尽终止」的完整放宽属执行层改动(消费缝 = `sim/engine_p1.py` 发射建模块段帽取值),**随 sim 载体声明批接线**(该批同时承接下条申报的哨兵扩展)。
3. **落点二(非成型线)决策层清算臂**(shop 域单动作核前段分支;备战栈 M3 批位同触发):
   - **辖域判据 = 域①帧本身,不挂 arm1**(N2 硬约束);
   - 循环序(保守序纯增量,N1 放弃面=换板不辖维持):步 0 升级续批(闸链与既有 M3 同序同源:level_spend_blocked→血闸→lv9_stop→P48 整买→P72 全段闸;域①⊂plane_last_battle,ALL IN 豁免天然辖闸可行性)→ 步 1 腾位卖出(bench 满 ∧ 有步 2/3 目标;victim=燃料类单一源+装配 A+P78-1 本 visit 买入减法)→ 步 2 补位买入(板有空位 ∧ bench 无待部署件;`can_deploy_single` 单一源预检;费档降序)→ 步 3 单帧合成(店内+持有同名同星合计 ≥3 ∧ 合成产物合成销后板面可上板;完成张经 `merge_buy_completes` 单一源,M2b 满栏例外同款)→ 步 4 寻件刷新(金 ≥ 刷价 ∧ 无上述目标)→ 步 5 终止(金尽 ∨ 无合法消费动作;步 0-4 净耗金 ≥0 ⟹ 有限终止);
   - **域①帧上既有选择序整体让位**:M6 压库/②(b)/囤积族的花费对象 = 未来价值,域①下边际战力 = 0 不获 P81 授权;利息预留类守卫保护对象同不存在;
   - 备战栈位:mandate.run_mandate M3 批触发条件扩 `_end_frame`(auth_basis 分键 `endgame_liquidation`),闸链共用;
   - 分键族:`endgame_liquidation_frame`(辖域决策帧)/`endgame_liquidation_upgrade|sell|fill|merge_buy|refresh|close`(逐动作;A/B 判据①清算发射率按两落点分键分开读)。
4. **卖出腿(P78 通道对价段「终局清算」豁免行)**:ADR-0585 §3 增行(对价 = 域①资产价值清零,P78-5′ 腿②无损形态;边界 = 线内/骨架禁卖维持 = 装配 A;通道视图 = m4_fuel;触发面豁免非排除面豁免)+ §4 N4 处置注;发射位 reason=`endgame_liquidation_clear`(SELL_BENCH_REASONS 第 6 通道值,登记门先登记后接线)。
5. **锁面**:`sr-od-test/test/sr_od/app/currency_war/test_cw_endgame_liquidation.py` 16 锁(域①单帧锁/终止锁/步 0 续批锁/禁卖三锁/分键锁/红证/20260958 病灶复演);登记门双向更新(test_cw_sell_reason_matrix 枚举闭集 5→6 + 消费位清单 shop.py 5→6)。

## 4. 两面申报与边界(如实)

- **生产域①发射面 = 实时生效**(载体缺省 3 位面,P3 r9 = 域①):armed 帧带内清算、非 armed 帧清算臂自此改变生产行为——`cw_replay --diff` 预期漂移面 = 域①清算发射帧(本批目的,漂移清单随批申报);非域①帧逐位零漂移(既有等价扫描锁看守)。
- **sim 域①面 = 载体声明前零漂移**:现网 sim 引擎不写 `run_plane_count`(缺省 3)→ P1-only 假局 P1 r9 判非域① → 引擎/哨兵行为逐位不变;**接线义务(候 sim 载体声明批,与 A/B runner 同批)**:①runner 声明 `run_plane_count = planes`;②`sim/checks/launch.py` 哨兵溢出帧 `gold_after ≥ g_star` 不变量补域①豁免行(声明载体上域① released 帧以 'overflow' 标签出现且合法花穿息线);③段帽放宽消费缝(上条)。本批文件面禁碰 sim 引擎语义,三项如实挂账。
- **遥测判读注**:生产 `KEY_ZONE_FRAMES`(仲裁段进入帧数)自本批含域①释放帧(口径扩展:溢出段 ∪ 域①豁免);`KEY_CROSS_LINE`(花后跌破 g*)在域①帧按豁免语义为合法值,判读时按 `launch_arbitrage_endgame_frames` 分键排除。
- **P68 收窄(裁决#6)**:域②③的命题权威由 P81 承接,P68 候派范围限缩域①;撤并候裁独立批(本批零代码面)。
- **升级续批与 P72 §2.5 的权威分界**:域①面数学权威 = P81 主定理;P72 ALL IN 豁免在域②③帧的「R=0 恒零」表述维持候修订批收窄(P81 行在册),本批闸本体零改。

## 5. 验证

- 新锁 16 条全绿(含红证:退域①豁免 → 带内冻结复现 + 清算臂沉默);登记门 2 锁随语义登记更新;
- 直接受影响域回归全绿(仲裁核/哨兵/卖出矩阵/升级闸/边界);CW 快速层全量 `-m "not slow and not legacy_baseline"` 全绿;
- 病灶复演:20260958 R9 形态(lv5 后 arm1 失效、48 金)在域①载体上续批发射并清算至金尽(锁 TestDiseaseReplay20260958);
- ruff 全部改动 src/test 文件零违例。
