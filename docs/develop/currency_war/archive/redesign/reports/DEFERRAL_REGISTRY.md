# cw3 缓办面清欠总盘点(DEFERRAL_REGISTRY)

> 目的:把 8 批交付/审计/归因报告里所有「后续批 / 缓办 / fail-closed / 待标定 / None / 挂账」声明 + cw3 代码内 grep 兜底命中,摊开成一张可裁决清单,杜绝 A/B 第四轮再撞未知缺口。
> 盘点方式:全量读 `.debug/temp/currency_war/redesign/` 报告 + `.debug/progress/2026-08-31-currency-war-redesign/决策/进度.md` + `cw3/` 代码 grep(后续批|缓办|挂账|fail-closed|待标定|TODO),关键项逐条回代码核对「已补/仍缺」。
> 本报告只写数据与现状,不改任何代码。
> 分类:A = A/B 有效性必需(策略行为与设计意图实质偏离,四轮前置检查清单);B = 仅生产缺口(sim 不受影响,批 1b 后生产补齐清单);C = 已声明可接受让步(两侧同缺省,对照公平)。

---

## 一、登记总表

| # | 缓办项 | 声明出处 | 当前状态 | 影响面 | 分类 |
|---|---|---|---|---|---|
| 1 | **危局接管门**(hp≤40 ∨ 连败≥2 时买入/刷新/升级越过局部门)——r2 归因清单第 5 条,三轮 A/B 唯一「完全没接通」项;血预算拦截全批 0/0(旧侧 229/230),S5 终局 hp 塌陷唯一越线哨兵 | AB_R2_ATTRIBUTION §四/§六-5;AB_R3_ATTRIBUTION §一.4/§四-4;CODE_AUDIT_ROUND2 高-5 | **部分已补**:机器级 `crisis_takeover_levelup`(levelup.py L140)/`crisis_takeover_refresh`(refresh.py L159)已落码,壳层危局判定+判而未动落盘已接;**但 r3 出数时代码是否含此臂未定,0/0 拦截未经四轮复验**——落码≠拦得住,四轮必须先验拦截计数>0 | sim 行为 = S5 主根之一 | **A** |
| 2 | **成型链三断点**(r3 修复清单 1-3):①腾席卖出扩量(SellBench 43 vs 需 ~300,bench 满拒买 1163 笔/3114 金)②部署机吞吐(CompTransaction 229 vs 934)③P1 升级投入(1940 vs 5792 金,P2r1 入场等级 8 vs 9) | AB_R3_ATTRIBUTION §一.2/§三/§四-1~3 | **仍缺**——r3 归因明确「崩局主体是成型链尾部,第 1-3 条才是根」,四轮前无修复则 M1/M3/M5/M6 照旧 FAIL | sim 行为,M1/M3/M4/M5/M6 全部主指标 | **A** |
| 3 | **P2 无机器接管**(入场血薄 + P2 刷新金 362 vs 990 + 单边败)——危局门是止血件,翻盘手段(刷新机续战力)本身缺位 | AB_R3_ATTRIBUTION §2.4 | 仍缺(与 #1/#2 同链,单列防漏) | sim 行为,S5 | **A** |
| 4 | **换线机器缺失**:E1/E2/换线决策机声明「后续批」;sell.py 有 `line_switch` 塌缩出口形参,但全 cw3 无任何调用方置 True,换线塌缩出口 = 死参 | strategy_shell.py L24/L30;AB_FAIL_ATTRIBUTION §五-5;classify.py L207 | **仍缺**(出口已留、触发方未接) | sim 行为(塌缩/换线策略面整块空缺);form 指标相关 | **A** |
| 5 | **评分机器 E1/E2/E15 后续批**(买入评分的 E1/E2/E15 消费) | strategy_shell.py L24、L947 | 仍缺(缺省确定性首项在跑) | sim 行为(买入面降级输入) | **A** |
| 6 | **decide_levelup 不消费 XP 流入**:`xp_flows`/`xp_instant` 帧键已装配(strategy_shell L349-350)、sim 侧 oneshot 入账已接,但 levelup.py 对 XP 流入零消费(grep 证)——升级时机判据缺 XP 期望项 | CODE_AUDIT_SEAMS S-4;CODE_AUDIT_ROUND2 §二 S-4 行「按审计指控标准未闭环」 | **仍缺**(帧键有、消费无;ADR-0513 已挂账=可见,但未闭环) | sim 行为(升级时机系统性保守);条件 XP 卡(202601/202701/151301)决策价值不可见 | **A** |
| 7 | **证据门两阈值 None**(completion_threshold / env_dominance_ratio)= 臂一臂二全关 fail-closed,证据门空转 | calibration.py L38-40;completion.py L177-186;strategy/__init__ L5 | **仍缺**(标定缺省,统一 fail-closed;不属 bug 属待标定) | sim 行为:证据门选臂整块不工作 | **A**(若证据门属设计必选件)/C(若两臂关闭=两侧同用注册序,对照公平)——**需编排者裁** |
| 8 | **p48 S 分臂缺失 + 血单位混入金位门**(MACHINES M1a/M1b):臂一被强加臂二口径金位门;血本位局升级机可能永久哑火 | CODE_AUDIT_MACHINES M1 | 修复波未见记录,代码未见分臂改动 → **大概率仍缺,四轮前需核** | sim 行为(升级机语义漂移;血本位注入局哑火) | **A** |
| 9 | **u/H 拍值双标**(MACHINES M8):calibration 对 🔴 待标定项 u_by_cost/h_horizon 给了具体数值并直接进 sell.py V_opt,声称出处「p41 保守首版序表」在 p41 正文未见 | CODE_AUDIT_MACHINES M8 | **仍缺裁决**——要么找到/补标定出处,要么按 fail-closed 改 None 关卖闸 | sim 行为(燃料件「几乎恒判卖」由拍值驱动;腾席卖出行为部分建立在未标定值上) | **A** |
| 10 | **危局门 hp 输入 vs [39]「HP 不作决策依据」的形态冲突**:用户裁决④ HP 不作决策依据(01 §4.7),但危局接管门的输入恰是 hp≤40(state.hp None 时门不开)——§4.7 移除 hp 后的正确替代形态(连败窗单臂?危局读数仅门限豁免?)未裁决 | 进度.md 行 7(用户裁决④);cw_state.py L185(ADR-0491 hp None 化);strategy_shell.py L596 | **仍缺裁决**——现实现以 hp≤40 为危局主臂,与设计约束正面相抵,hp=None 帧门静默不开(生产常见) | sim(hp 恒真读,无感)+ 生产(门常闭)分叉;设计一致性 | **A** |
| 11 | **V̄ 标定剩余面**:V̄/V_gap/u/H 首版已落 calib_v1(SEAMS 审计第 9 条单一源确认);剩余 = 分成员求和式 k≥2 标定(S-11 线性外推,现以多成员禁 R1 收窄 + 一条「与审计指控相抵、无出处」的注释豁免,CODE_AUDIT_ROUND2 中-6)、V̄_LOW 下沿臂无访问器 | calibration.py;windows.py;CODE_AUDIT_SEAMS S-11;CODE_AUDIT_ROUND2 中-6 | **部分已补**(首版注入在);k≥2 面**仍缺**(注释豁免未回炉) | sim 行为:多成员刷新窗禁 R1(保守,方向 fail-closed);门偏松风险在放开多成员时带病上线 | **C**(当前收窄形态对照公平)/B(注释回炉) |
| 12 | **种子出口(第二体系)四项终审尾巴**:P3 配额计划时点烧光→已修(入账移执行确认点,strategy_shell L505);P6 空 core 线恒真→已修(L514 `bool(core) and …`);**P5 种子门裸金 vs S 活期口径未修**(L520 仍 `state.gold − batch_reserved`);P9 种子改判序 1 污染统计口径未申报 | CODE_AUDIT_FINAL_R2 P3/P5/P6/P9 | 3 修 1 未修 + 1 未申报 | sim 行为:活期资产时种子出口欠 firing(方向保守) | A(轻)/C(保守向,两臂同代码)——P5 建议随 #2 一并修 |
| 13 | **MACHINES 审计 H1/H2/H3/M2/M3/M4/M5/M7 修复状态**:buy.py 已见 p46 跨线破域分支+r_global+目标件无特权(H2/M6/M7 修),sell.py threshold 已改 max 双通道(M2 修),refresh 已声明禁 fail-open(H1 修),completion q_avg 已重构(H3 似修);**M3(同费计数域含目标卡契约陷阱)/M4(池边界 taken==max_taken 差一格)/M5(纯派生路径 dynamic_per_streak 漏防)未见修复波记录** | CODE_AUDIT_MACHINES M3/M4/M5 | 三项**待核/大概率仍缺** | sim 行为:命中率低估→该 D 不 D(M3)/压缩排序末格错(M4)/连胜错账条件触发(M5) | **A**(M3/M5 触发即静默错账) |
| 14 | **免费刷额度每波重复授予**(ROUND2 中-7):决策侧每波重发全额 N,执行侧只有首波真免费——门偏松、ADR-0513 验收门要防的形态 | CODE_AUDIT_ROUND2 中-7 | 待核(未见修复波) | sim 注入局 + 生产同构 | **A** |
| 15 | **腾席卖循环未按「卖最弱」排序**(ROUND2 中-8):按槽位序先到先卖,与 deploy.py 的 (cost,star,idx) 序不一致,毁贵资产 | CODE_AUDIT_ROUND2 中-8 | 待核 | sim 行为(卖出序次优) | **A** |
| 16 | **deploy 越界兜底落 SellDeployed**(ROUND2 低-10):deployed_idx 异常时无条件发卖动作,fail-open 形态 | CODE_AUDIT_ROUND2 低-10 | 待核(dormant,修复通道时必须同批修) | sim 边缘 | **A**(不可逆动作的兜底方向) |
| 17 | **waiting_unit 第三态**(ROUND2 中高-4):板满+无可牺牲时升级臂一恒关——升级本身是创造空位的兑现路径,谓词未覆盖 | CODE_AUDIT_ROUND2 中高-4 | 待核 | sim 行为(p39 臂一在最常见场景饿死,与 #2③ 同根) | **A** |
| 18 | **P2 重入臂三守卫**(ROUND2 中高-5):cw3 相位机无 M-6 满席门/无空板出战守卫/无部署失败记忆——「全量重判自愈」仅注释自证 | CODE_AUDIT_ROUND2 中高-5 | 待核(生产域为主) | 生产事故风险 + sim 无此相位机(sim 不受影响) | **B** |
| 19 | **E1-E15 事件面整块缓办**:strategy_shell 自述「事件面 E1-E15 缓办(后续批)」;OBS 盘点裁定硬缺三处 = E12 商店锁全链、E10 工具使用决策链、E5 圣杯生命周期 | strategy_shell.py L30;OBS_SUPPLY_INVENTORY §3/§6;进度.md 行 7(用户裁定「事件面全量」) | **仍缺**(A/B 有效性边界:sim 引擎只建模部分事件,两臂同缺 → 对照公平,但「新层策略强度」被系统性压低) | sim:两臂同缺省对照公平;生产行为覆盖面 | **C**(对照公平)+ 生产侧归 **B**(E12/E10/E5 硬缺必须进批 1b 后生产清单) |
| 20 | **E15 圣杯强开方案**:采集批前置方案已成文(holy_cup_force_open_plan.md),实机采集批被一条龙占用中断后未重派 | 进度.md 行 31;holy_cup_force_open_plan.md | 方案在、**执行未做** | 生产-only | **B** |
| 21 | **sim 仅 2 位面,位面 3 真通关测不到**:A/B 全部 planes=2;node_schedule 数学件已按 3 位面建模(P2=7 总 25),引擎侧 2 位面 | AB_R3_REPORT 配置实录;CODE_AUDIT_MACHINES 攻过未破 1 | **仍缺**(结构性 sim 局限,两臂同缺省对照公平;但 M1「存活通关」口径在 2 位面上测的是过渡战,非真通关) | sim 保真度(对照公平) | **C**(对照公平;真通关验证归实机批) |
| 22 | **生产侧概率真值(S-7 同族)**:state.refresh_probs sim 每阶段注入;生产 None → 基线表,降级输入无哨兵区分「没接」vs「接了但读空」 | CODE_AUDIT_SEAMS S-7;CODE_AUDIT_VERIFY3 合同表;input_contract.py L250(default_safe_rationale 自认挂账 S-7) | **仍缺**(生产写点未接) | 生产-only | **B** |
| 23 | **生产侧 cw_paid_refreshes 写点**:S-1 已真修(shop.py refresh_counts_paid),残余=点击落空按免费漏计(方向声明自洽) | CODE_AUDIT_ROUND2 §二 S-1 行 | **已补**(带已申报残余) | — | **C**(残余已申报) |
| 24 | **生产连败供给(终审 P1)**:败局结算页 telemetry_only 跳过 on_round_end → last_streak 收不到连败 | CODE_AUDIT_FINAL_R2 P1 | **已补**:battle_loop.py L593-602 败局路径显式写 last_streak(观测缺失时递减兜底);VERIFY3 要求的「递减兜底显式登记进 DEFAULTED_EXPLICIT」**待核是否落** | sim 无感;生产 S1 哨兵连败臂已通 | **B**(残余登记项) |
| 25 | **镜像 board 输入口径(终审 P2)**:sim 全集口径 vs 旧层 _board_factions_of 窄口径,同板面两侧体系数可不同;对拍锁不锁输入面 | CODE_AUDIT_FINAL_R2 P2;CODE_AUDIT_ROUND3 P2 | 待核(治本修法=输入收敛同源函数+PREREG 补 v4 口径申报;r3 出数用 v3/v4——需确认 v4 是否已含输入口径申报) | sim A/B 可比性(M3/M4) | **A**(口径申报未落则四轮 M3/M4 不可比) |
| 26 | **名称归一全链(终审 P4/R3-P8)**:decide_prep_action 通道裸判、变体表缺半角 `.` | CODE_AUDIT_FINAL_R2 P4 | **已修**:decide_prep_action 侧 L785-788 已归一;半角 `.` 是否入变体表 classify.py L70 区**待核** | 生产-only(OCR 形变) | **B** |
| 27 | **crisis/levelup 观测尾巴**(终审 P8):crisis vacancy>0 时 reason 已补 `seats_freed_by_making_room`(L620 已见);cap 截断 batch 字段置 0 待核 | CODE_AUDIT_FINAL_R2 P8 | 部分已修 | 判读面 | **C** |
| 28 | **M2 遥测增强批**(进度 M2):观察层移交 BuyCard 补 char_id、spend_ledger、补给轮决策行采集、对局档案战后终态列、lv 读数恒 4 疑点 | 进度.md 行 35 | **未做** | 判读/复盘质量(生产) | **B** |
| 29 | **M3 采集追加批**:装备 λ 标定、R(c)=p42/p50 待标定、图鉴策略环境两页、武装箱弹窗帧+暂停态帧、P3 语料采集 | 进度.md 行 35;CODE_AUDIT_MACHINES 攻过未破弱点声明 | **未做**(依赖实机批) | 标定供给(生产-only) | **B** |
| 30 | **M4 测试基建批**:cw_quick 全量对账补齐、xdist 慢桶、L3 九红残余核对 | 进度.md 行 35 | **未做** | 验证基建 | **B** |
| 31 | **M5 运维卫生批**:temp 22GB 治理、判前锁文档持久化迁移、截图清理、as-built 过期清欠 3 项、kernel 注释清扫(~250 处会话局部标识) | 进度.md 行 35;CODE_AUDIT_ROUND2 低-12;MACHINES L7 | **未做** | 卫生(注释出处链会烂) | **B** |
| 32 | **M1 保留层缺陷批**:registry_fingerprint TypeError、_REPO_ROOT 定位、shop 增量重估+日志双信道漂移、轮转 PermissionError、battle_loop 重试无退避 | 进度.md 行 35 | **未做** | 生产-only(旧保留层) | **B** |
| 33 | **M6 等用户(希儿文档修正三项)/M7 知识注记(形单影只单挂队建模,cw_comps.py L243/L280 挂账)/M8 小项(runs 写端核验)** | 进度.md 行 35;cw_comps.py L243/L280/L650 | **未做/等用户**(M7 前置=板面档位数据) | 知识层(两臂同缺省,对照公平) | **C**(M6)/B(M7/M8) |
| 34 | **Z1/P19② 标签二义与 P19② 未修**:冻结条件③两处文档指不同缺陷;P19②(羁绊计数两遍法)全 cw3 无相关代码 | DOC_AUDIT_CYCLE1 §N11/§95 | **未修** + 文档三处不一致 | 知识/文档(sim 两臂同缺省) | B(修)+A(条件③拆名,防四轮按错前置开工) |
| 35 | **levelup 臂一 floor_pop 待标定缺省 0**(p39):臂一金位门强加臂二口径(M1a 同源),floor_pop 标定挂账 | CODE_AUDIT_MACHINES M1a;calibration.py | 仍缺(随 #8) | sim 行为 | **A** |
| 36 | **resolver 各计窗/计数器型突变缺省关挂账**(02 §3.2 开关生命周期):计数输入未接线→缺省 0 永不生效,开臂判据挂账(resolver.py L110-137、mutations.py L71-95、invest_mutations 多处、cw_economy.py L142 刷新计数) | resolver.py / invest_mutations.py / cw_economy.py 注释族 | 按设计纪律挂账中;生产计数写点部分已接(S-1),**计数窗类(R05 30 刷门/'120'/'102201')实机侧仍未接线** | sim 注入局开门;生产关门(两侧同缺省公平;但 sim A/B 结论对实机外推失真——S-1 原指控的残余面) | **C**(对照公平)+ **B**(实机接线清单) |
| 37 | **N24 plane_modifiers / E12 shop_locked 孤儿字段**:cw_state 声明后 0 写 0 读 | OBS_SUPPLY_INVENTORY §6;cw_state L233-234 | 仍缺(新层不消费) | 生产-only | **B** |
| 38 | **卖回通道(p50)与「血预算门」旧语义退役**:旧层 blood_budget 拦截 229/230 是旧语义;cw3 替代形态 = 危局接管门(#1)+hp_afford_batch 支付能力检查(levelup L126,[40]② 豁免面)——替代形态是否完备未经四轮数据验证 | AB_R3_ATTRIBUTION §2.4;levelup.py L92-126 | 形态已落,有效性未验 | sim 行为 | **A**(随 #1 合并检查) |
| 39 | **判读纪律遗留**(两轮归因同款):M3/M4 旧侧 form_ok 口径与新侧不同源(锁定线判据 vs 镜像兜底门),跨栈对比必须用 form_score 或栈中立口径 | AB_R2_ATTRIBUTION §六-6;AB_R3_ATTRIBUTION §四-5 | 已声明、**未固化进 PREREG 判读纪律条款** | A/B 判读有效性 | **A**(四轮 PREREG 必须显式带此条款) |
| 40 | **代码内 grep 兜底其余命中归类**:①`prep_director.py` L271 刷新波构建挂账(生产,旧层)→B;②`classify.py` L188/L208 贯穿统计 fail-closed 护栏(标定前禁卖,两侧同)→C;③`sell.py` V_opt None fail-closed 持有(#9 同族)→A;④`deploy.py` 越界 None fail-closed(L166)与 #16 兜底方向对偶(规划层正确/兜底层 fail-open)→A;⑤`cw_line_switch.py` L304 中位去敏重标定挂账(旧保留层)→B;⑥`cw_overlay_registry.py` PENDING_HANDLER_IDS handler 收拢挂账(生产)→B;⑦`collect_plane_intel.py` L623 中转消费接线批挂账(生产)→B;⑧`run_megastar_node.py` L8/L17/L20 巨星 step2 建档+效果真值 TODO(生产)→B;⑨`cw_observation.py` L1497 阮·梅/白厄未知卡挂账(生产识别)→B | 全仓 grep(见正文) | 逐条如左 | — | 已逐条标注 |
| 41 | **危险识别:登记表标 resolved 但消费面为空的条目**(S-13 同段多刷定价,SEAMS 指控「登记表当 resolved 登记无挂账标记」——后经刷新收敛口径性消除,ROUND2 裁定挂账一致) | CODE_AUDIT_SEAMS S-13;CODE_AUDIT_ROUND2 §二 | 已口径性消除 | — | **C** |

---

## 二、A 类汇总 = A/B 第四轮前置检查清单

第四轮开跑前必须逐条核过(修完或显式裁决「带缺口出数」),否则撞缺口风险与前三轮同型:

1. **危局接管门有效性验证**(#1/#10/#38):拦截计数>0 的四轮预检;hp 输入 vs [39] 形态冲突需用户裁决或声明。
2. **成型链三断点修复**(#2/#17):腾席扩量、部署吞吐、P1 升级投入、waiting_unit 第三态——r3 归因判定的根。
3. **P2 翻盘手段**(#3):刷新机 P2 续战力(与 #1 联动)。
4. **换线机器 + 评分机器 E1/E2/E15**(#4/#5):整块后续批,至少声明四轮判读边界。
5. **decide_levelup XP 流入消费**(#6):帧键在、消费无。
6. **证据门两阈值**(#7):标定或显式裁决「两臂关闭=注册序对照」。
7. **MACHINES 残余**(#8/#9/#13/#35):M1 分臂+血单位、u/H 拍值出处、M3/M4/M5 修复核对、floor_pop。
8. **每波免费刷重授**(#14)/腾席卖序(#15)/deploy 兜底方向(#16)。
9. **M3/M4 可比性**(#25/#39):镜像 board 输入口径收敛或 PREREG v4+ 口径申报;跨栈 form 对比纪律条款固化进 PREREG。
10. **Z1/P19② 条件③拆名**(#34):防按错前置开工。

## 三、B 类汇总 = 批 1b 后生产补齐清单

- 生产输入写点:概率真值(#22)、连败兜底登记固化(#24)、名称归一变体表 `.`(#26)。
- 事件面硬缺:E12 商店锁全链、E10 工具使用决策链、E5 圣杯生命周期(#19 生产面);E15 圣杯强开采集(#20)。
- 相位机三守卫(#18)、P2 重入臂。
- 计数窗类突变实机接线(R05/'120'/'102201')(#36 生产半边)。
- 孤儿字段/长尾:plane_modifiers、shop_locked(#37)、handler 收拢、巨星 step2 建档、未知卡、中转消费(#40 各 B 项)。
- 迁移包 M1-M8(#28-#33,含等用户 M6)。
- 保留层血预算门旧语义退役确认(#38 生产面)。

## 四、C 类汇总 = 申报为已知让步(两侧同缺省,对照公平)

- 事件面 E1-E15 整块缺省(#19 sim 面)、位面 3 缺(#21)、证据门 None 关臂(若裁决为对照公平,#7)、V̄ k≥2 收窄形态(#11)、S-1 计数残余(#23)、crisis 观测尾巴(#27)、贯穿统计护栏 fail-closed(#40②)、S-13(#41)、知识层 M6/M7(#33 部分)。

---

## 五、方法与边界

- 报告全量读:进度.md、AB_FAIL/R2/R3 归因、AB_R3_REPORT、CODE_AUDIT_SEAMS/ROUND2/ROUND3/MACHINES/FINAL_R2、OBS_SUPPLY_INVENTORY;VERIFY3/FINALR2_VERIFY/DOC_AUDIT_CYCLE1/MARKER_CONVERGENCE/PREREG/p42 检查经关键词检索定位,未逐行全读——「待核」条目以代码 grep 复核为准,报告层结论未逐字复核。
- 「已补」判定 = 本盘点的代码 grep 直证;「待核」= 报告指控后未见修复波记录且未逐一回读该函数全文。
- 临时分析脚本(cw_r*_attr_analysis 等)按各报告声明已用完即删,不在盘点面。
