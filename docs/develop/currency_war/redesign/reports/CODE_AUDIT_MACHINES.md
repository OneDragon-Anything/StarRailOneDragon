# 对抗式代码审计报告:④-2 修复波 + ④-3 八台策略机器(cw3/)

> 审计立场:假设代码有错,逐条对照证明件(p38/p39/p40/p41/p42/p43/p46/p47/p48/p49/p50 全文关键节)与玩法文档(economy.md §1/§10.1、user_playstyle [9][17][22][31][33][34][40][41][42])攻击;攻不破的写进「攻过未破」。**未改任何代码。**
> 审计对象:`cw3/knowledge/resolver.py`、`cw3/knowledge/invest_mutations.py`、`cw3/math/{compression,node_schedule,interest_account,levelup_batch}.py`、`cw3/strategy/{completion,opening,streak_money,refresh,sell,equipment,levelup,buy,calibration}.py`。

---

## 一、问题清单(按严重级排序)

### H1|refresh.py:V̄/V_gap 未标定时,攒息域散刷完全无门放行(fail-open,反证明方向)
- **位置**:`cw3/strategy/refresh.py` `decide_refresh` L137-151。
- **发作场景**:窗口 `v_bar=None` 或 `v_gap=None`(两者都是 p40 待标定最大项,首版常态)且 `single_card=False` 或 v_gap 缺 → 落到 `single_step_conservative` 分支,直接返回 `n=min(1,n_max)`。此时金位在攒息域(如 g=40、息线 50):R2 预算门给 `n_max=(gold−reserve)//c_eff`,R0-2 价值门因 v_bar=None 被跳过,R1 因 v_gap=None 被跳过——**一笔会打破息档的刷新在零 EV 证据下被授权**。
- **对照证明**:p40 结论 1「散刷 = 逐次单步门 EV ≥ 0」,而单步门 EV=5q·V̄−c_eff 在 V̄ 未标定时**不可判**,fail-closed 应是 n=0;且 p40 原文散刷的定义域是**溢余段**(`散刷(溢余段无明确缺口的多刷)`),本实现把散刷形态用于攒息域(g≤floor 分支 L134),域本身就越出了证明。
- **严重级**:高。docstring 自称「诚实降级:不虚构 V̄」,但降级方向是开闸不是关门,与全套机器的 fail-closed 纪律(calibration 阈值 None=关臂)自相矛盾。

### H2|buy.py:溢余域短路 p46 否决域,跨线大额买入绕过真破息判据
- **位置**:`cw3/strategy/buy.py` `gold_gate` L78-82。
- **发作场景**:gold=55、息线 50,买 spend=10 的非豁免、非当轮兑现件:`gold>floor_gold` 分支直接 `return True, 'ruling_17_overflow_free_spend'`。但 g−spend=45<50 且 ⌊5⌋→⌊4⌋ 下降 = p46 真破息 ∧ 无当轮兑现 ∧ 非豁免 = **否决域内**,该笔在 gate 里检测不到。
- **对照证明**:p46/p33 否决域判据 `g−c<50 ∧ ⌊g/10⌋ 下降` 对起点在息线上方的花销同样命中(p48 命题 3 明文「期间小于 50 的花销按 p47 的 L 定价(囤钱不豁免息损账)」;[17] 的「>息线随时花」辖域是溢余部分,不是授权穿线)。p40 刷价侧专门用 `⌊(g−50−预留)/c_eff⌋` 防穿线,买侧 gate 却没有等价防线——同一经济账两侧不对称。
- **严重级**:高(该门是六序共用门,绕过即全线绕过)。

### H3|completion.py:④层「等级分段条件化」未实现,注释宣称与实现不符
- **位置**:`cw3/strategy/completion.py` `completion_closed_form` L111-114。
- **发作场景**:`q_avg = sum(slot_hit_q(...) for _lvl in round_levels)/rounds`——循环变量 `_lvl` 未使用,`probs` 是**单张概率表**,API 上无法表达逐轮不同等级的概率。若调用方传入「L8→L9 升级日程」(p38 ④层/p39 输出 L(r) 的整个联动动机),未来轮仍按当前级表计 q,5费档 L8(0.10)与 L9(0.25)差 2.5 倍,完成概率被系统性错估;docstring「q̄_k = 逐轮 q_k(L(r)) 的槽位等权平均」为虚假声明。
- **对照证明**:p38 完整配方第 1 步明文 `q_k(r) = REFRESH_PROB[L(r)][c] × …`,④层是五层模型之一;误差异化声明(−2~+8pp)只在「逐轮取表值」前提下成立。
- **严重级**:高(证据门评分是该模块唯一决策用途,输入错 → 门判定错;且属「注释/证明语义 vs 代码」直接漂移)。

### M1|levelup.py:p48 动态目标线 S 未分臂 + 血本位单位混合
- **位置**:`cw3/strategy/levelup.py` `decide_levelup` L122-124、L151-153。
- **问题 a(分臂缺失)**:p48 命题 2 明文 `floor = 50(臂二)| floor_pop(臂一,p39 待标定)`,且「E[刷费]×2 是臂二口径的无条件扣项」。代码对两臂统一 `s_line = target_line_s(batch, floor_gold, reserve, e_refresh*refresh_cost)`——臂一(阵容驱动,floor_pop 标定缺省 0)被强加了 B+50+预留+E[刷费] 的金位门,严于证明(保守向漂移,但语义已不是 p48 的 S)。
- **问题 b(单位混合)**:`currency=='hp'` 时 `batch = batch_cost(..., c_xp, ...)` 是**血**单位(6×击数),却被加进与 `gold_liquid`(**金**)比较的 s_line。血本位语境的批门在证明里就是 [40]② 血安全带(p48 符号表 floor 注:「血本位语境 = [40]② 同构」),金位门不应含血成本项;现实现 = 血安全带 ∧ 金位 ≥ S(含血批成本),后一项是证明外的额外门,血本位局可能因此永不及线而 `defer_bank` 挂死。
- **严重级**:中(方向性可辩护但双处语义漂移,b 在血本位局可致升级机永久哑火)。

### M2|sell.py:decide_sell 文档与实现互相矛盾,in_line 件被「切换」而文档声明「非切换」
- **位置**:`cw3/strategy/sell.py` L107 `threshold = max(eff_v_opt if not in_line else 0.0, v_ms_dp) + v_power`。
- **问题**:模块 docstring(L14-16)写「max = 弃购 K 内件**两通道同发**的保守下界(**非切换**)」,但实现把 in_line 件的 V_opt 置 0 后再与 v_ms_dp 取 max——这正是文档否认的「切换」形态。对 in_line 的燃料件(fuel 无分类护栏),threshold 变小 → 更容易判卖,反保守。
- **对照证明**:p41 主式为 `refund+V_slot > max(V_opt, V_ms·ΔP̂·[x∈K]) + V_power`,两通道取 max;通道互斥/切换规则(p41 ⑤)是**定价归属**规则(防双计),不是把不等式另一臂清零。
- **严重级**:中(骨架/贯穿件被前置护栏挡住,泄漏面 = in_line 且非骨架非贯穿的件)。

### M3|resolver.same_cost_taken:计数域含目标卡,与 taken 的「非目标离池」口径冲突
- **位置**:`cw3/knowledge/resolver.py` L200-212。
- **问题**:docstring 自称「与 `_refresh_dist` 的 c 语义同源:**该费非目标牌**的离池数」,实现却统计 `chars_of_cost` 集合内**全部**持有副本。目标卡的持有量在该口径下应经 `j`(RefreshWindow.j / GapItem.held)单独入账;调用方若按函数名语义传入「该费档全部角色名集合」(注释明示「调用方从注册表给」,最自然的给法就是全档集合),目标卡自持即被双计进 taken → 超几何分母虚减 → 命中率被低估 → 该 D 的不 D。
- **严重级**:中(契约陷阱型:纯函数无法自查,全靠调用方记得把目标卡从集合里剔掉,而 docstring 声称的语义恰会诱导相反用法)。

### M4|compression.py:池边界夹取差一格,taken==max_taken 时伪影仍可触发
- **位置**:`cw3/math/compression.py` `marginal_compression_gold` L44-51。
- **问题**:守卫是 `if taken > max_taken: return 0.0`,但 `e1 = expected_refreshes(..., taken+1, ...)` 在 `taken == max_taken` 时已用 **max_taken+1** 出域调用——恰是函数自己文档描述的「分母 comb(total,m) 对 m>total 归零 → dist 静默重归一」伪影。守卫条件应为 `taken >= max_taken`(此时第 taken+1 张不存在,边际本应返回 0/或以域内口径重推)。
- **严重级**:中(压库深期的边界格;压缩是排序用途,单格错值影响卖回序)。

### M5|invest_mutations.py↔resolver.py:dynamic_per_streak 防双计只盖 curated 并集路径,纯派生路径漏防
- **位置**:`invest_mutations.py` `_build_one` L553-557(curated 路径按 tag 跳过)与 `_econ_mutations` L429-431(生成 `difficulty` add + `dynamic_per_streak` tag);`resolver.py` `resolve_difficulty` L516-517。
- **问题**:curated∪派生并集路径(审计④修的那条)有 `if 'dynamic_per_streak' in m.tags: continue`;但走③纯派生路径的条目(非 curated)其 `difficulty_per_streak` 四元组**原样注册**,而 `resolve_difficulty` 对 `COMBINE_ADD` 的 difficulty 突变做平铺 `total += m.value`——「每连胜 +k」的系数被当成一次性 +k 入账(连胜 6 时真实 +6k)。伟大征服(302401)靠 curated+id 特判逃过;**任何其它**带 `difficulty_per_streak` 的 STRATEGY_ECONOMY 条目都会错账。是否实际存在第二条需对 `STRATEGY_ECONOMY` 全量核——登记层没有防,即属结构性缺口。
- **严重级**:中(条件触发,但触发即静默错账,且违反「同一 resolved 量只有一个计算责任点」——动态项的责任点在 resolve_difficulty 特判,登记层应统一拦)。

### M6|buy.py:满息金豁免 ORDER_TARGET 无证明出处
- **位置**:`buy.py` `gold_gate` L83-87。
- **问题**:g==息线时目标件豁免锁直接放行(`exemption_full_interest_gold`)。p46 豁免类 = 资产可逆 / 线内缺档件;p33 同;[17] 原文「满息金不可花」无目标件例外。目标件在满息金上买入 = 息 5→4,属于需要 V≥L 定价的破档支出,不是登记过的豁免臂。docstring「例外理由在册」未给出处。
- **严重级**:中低(单次息损 ≤1 金/轮,量级小,但属「证明外豁免」的纪律违例;若认为目标件≈线内缺档件,应走 in_line_gap 参数而不是按 order 特权)。

### M7|buy.py:gold_gate 无 R≥1 维度,p46 否决域在位面末被过量适用
- **位置**:`buy.py` `gold_gate`(全函数无 r_global/剩余轮参数)。
- **问题**:p33/p46 否决域定义含 `R≥1`(未来轮才有息可损;末节点破档息损=0)。gate 在攒息域对 `crosses_band ∧ 非豁免 ∧ 非当轮兑现` 一律拒,末节点/R=0 时拒的是零成本支出——过保守,方向违反证明的域定义(与 M1a 同为「保守向漂移也是漂移」)。
- **严重级**:中低。

### M8|calibration.py:对 🔴 待标定项给具体拍值,与自身 fail-closed 纪律双标
- **位置**:`calibration.py` L20-25(u_by_cost 五档具体值、h_horizon=10)对照 L31-36(completion_threshold/env_dominance_ratio=None=关臂)。
- **问题**:同一模块里,阈值类缺省走 fail-closed(None),而 p41 待标定清单 🔴 级的 u/H 却给了具体数值并直接进 `sell.py v_opt` 参与不等式——V_opt 非零 → 燃料件在 bench 紧张时几乎恒判卖(docstring 自己承认「V_slot>0 即几乎恒判卖」),这个「几乎恒」的实际是被拍值的 u 驱动的。声称出处「p41 ① 保守首版序表」在 p41 正文未见该五档数值表(待标定清单只有方向性描述),需核;核不出即属「拍值 + 挂证明名」。
- **严重级**:中低(数值方向保守,但纪律上是 fail-open 与 fail-closed 双标,且 sell 判据直接消费)。

### L1|resolver.resolve_prob_table:轮岗无观测帧退基线 = 拿已知错值继续决策
- **位置**:`resolver.py` L230-249。
- **问题**:轮岗激活且无概率条观测时返回基线 REFRESH_PROB 并告警。基线在轮岗语境**非真值**(某一档 ×2),下游 completion/refresh 全部消费错表;「告警不静默」只满足可见性,不满足 fail-closed(正确形态应让消费方按「表不可信」关闭概率敏感判定或用保守夹取)。已声明为设计选择,记为攻击存档。

### L2|resolver.resolve_refresh_cost:达标刷价 1 金硬编码
- **位置**:`resolver.py` L287-290。`if paid_refresh_count >= m.value: c_paid = 1`——门槛在 mutation.value,达标价硬编码;登记层(120 条目 tags `threshold_30_then_price_1`)与 resolver 各持一半语义,单一源裂开。

### L3|机器层不消费 resolve_shop_slots(R04 resolved 位空转)
- **位置**:resolver L252-261 暴露 R04;`completion.py` 直接 import SHOP_SLOTS、`refresh.py`/`compression.py` 经 `expected_refreshes` 的固定 5 槽模型。昔涟诗篇类槽位突变一旦登记,resolver 有位、机器无管——超几何格数不会跟着变。V4.4 无该类条目故当前无实害,属结构陷阱。

### L4|invest_mutations '104' 财富宝钻:一次性事件登记为无条件常态
- **位置**:`invest_mutations.py` L238-243。`OP_MAX_UNITS_CAP add +1` 无 condition,`once_event` 只在 tags——resolver 侧从激活帧起永久 +1。tags 注明 sim 通道,但实机 resolver 消费同一条目时会错账(「首次 5 连胜」语义无条件化)。

### L5|resolver._active_of / _warn_unregistered:每帧告警刷屏
- 缺省关突变(计数窗/计数器)每次 resolve 聚合告警——备战期一帧多次 resolve 即同条重复刷 log,噪声淹没有效告警。无节流/一次性位。

### L6|sell.py:v_opt 兜底 `DISTINCT_CARDS_PER_COST.get(cost, 13)` 的 13 不在任何注册表值域(实值 20/15/14/14/9),cost 越界时静默用假池参数而非报错。

### L7|注释规范:会话局部标识符散布(违反「出处=持久索引或纯语义描述」)
- `resolver.py` L89「审计②③补消费」、L453「审计⑤」;`invest_mutations.py` L543「审计④教训」;`compression.py` L99/103「审计修正」;`node_schedule.py` L1「Z1 修复」、L72「审计中危④」;`levelup_batch.py` L69「P11 处置」、buy.py L91「P10 处置」;`invest_mutations.py` L158「R2-F1-需改⑧」。这些编号离开当次审计会话不可解,半年后读者无法重建推导;应改持久索引(ADR-NNNN/证明锚/语义描述)。

---

## 二、攻过未破清单

1. **node_schedule.py 脏表守卫**:`plane_lengths` 逐位夹 [1,9]、短序列补先验;`total_remaining_nodes` 含当前轮口径(consumed=前位面+r−1)与 p38 ⑤层/p39 边界门的 R_全局 语义一致;P2=7 总 25 与 ADR-0366/0368 实证对齐。构造 `lengths=(9,7,9)/(9,9,9)/短序列/越界 plane、round` 无一产生负剩余或 IndexError。
2. **streak_money.streak_v DP**:递推结构与 p43 A1 引擎口径(轮首入账、胜发 T[s]、败轮金次轮补发且仅 s=0)同构;R=1 时 `V=T[s]` 与 p 无关的锚亲算复现(inc 先入账);memo 含 r 键正确;`位面内 R=下界`的保守方向声明与 ΔV 对 R 单调(s≥2)相容。未连胜 s=0 账更小的形态由 DP 结构自然给出。
3. **interest_account.loss_exact**:双轨迹递推与 p47 命题二逐项同构(cap 参数化为唯一差异、cap=5 时退化等价的声明成立;g<0 夹 0;溢余段 L=0 由 `min(b,cap*10)` 结构自然成立)。
4. **levelup_batch**:batch_cost nat_xp=0 保守版、禁真子集授权的注释与 p48 命题 1 一致;`clicks_to_level` 与 `xp_clicks_to_level` 的 k* 语义分裂(≤0 取 0 vs 至少 1)已在 docstring 显式声明,与 p48 符号表注记一致。
5. **compression.sellback_order**:2★ 恒排末位(含 dgold≤0 项)与自身文档一致;每金损失分母改用 `sell_refund` 真值(1★=cost、2★=3c−1)是 p49 §9 的金计口径;零损失 1★ 先卖的层组结构自洽。
6. **[40] HP 红线**:八台机器 + calibration 全量过——无任何机器把 HP 当决策/质量输入;levelup 的唯一血读数是 `hp_afford_batch` 支付能力检查(且 hp=None fail-closed 拒买),符合 01 §4.7 豁免。
7. **resolver 标量流水线**:override→multiply→add→min 分层与 02 §3.1 声明一致(override 后 add 继续作用的自举例可复算:10+(−1)=9);互斥 override 首生效语义统一。
8. **evidence_gate fail-closed**:双阈值 None=关臂、空集合法输出,平局序(完成×权 → 重叠 → core → 注册序)与 01 §4.2 原文一致;opening 的全零重叠仍取注册序首臂有 [31] 行为律背书。
9. **池不变量**:`held_copies` 用 STAR_COPY_MULT(2★=3/3★=9)折算,`pool_left_card` 派生不跟踪,买/卖/合成对称;4★=27 为防御性超规格不致错。
10. **completion 预算函数**:B 的五项构成与 p38 ⑤层配方逐项一致(守息、收入含息由调用方折算、B<0→0 槽、槽=5R),`refresh_cost` 经参数注入不写死——除 P=0 未强制(H3 之外单独记,责任边界有注释声明)。
11. **[42] 裁定忠实度(equipment.py)**:默认保留/近兑现(d*≤1 非冗余)绝不喂/W=0 冗余件唯一例外,三条件与裁定原文逐条对齐;「surplus ⟹ d*=0」使 `d*≤1 ∧ is_surplus` 的分支重叠在数学上不可达,判定序无漏洞;assign_equips 的硬约束先行(row/taboo/unique)与 p42 ②⑤一致(唯「字典序最优」措辞过强,见下)。

**未破但留痕的弱点声明**:assign_equips 的「按序贪心=字典序最优」在调用方候选序非 comp 优先序时不成立(tier-1 槽可被先到候选占走使 m1 降);当前契约(调用方按 equip_assign 优先序传入)下未破,但该最优性声明应降格为「契约条件下成立」。另 `resolve_income` 一次性金(`oneshot_pending`)在计数达标后每次调用都重报,依赖金日程消费即扣账——resolver 无 consumed 位,若上游忘记扣即重复入账,属责任边界注释覆盖、无结构防线的已知余留。
