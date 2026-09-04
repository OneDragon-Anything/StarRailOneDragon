# 代码审计报告:④-2 建表消费增量 + ④-4 接线收尾 + 标定注入(接缝面专项)

- 审计立场:对抗式(假设有错,攻击优先;攻不破才准写「攻过未破」)。
- 审计对象:`cw3/knowledge/invest_mutations.py`、`cw3/strategy_shell.py`、`cw3/strategy/windows.py|liquid.py|calibration.py`、`sim/engine_p1.py` 增量、`strategies/cw3_strategy.py`+`currency_war_config.py`。
- 方法:全量读源码 + 直调注册表程序化探测(id/名称冲突、派生丢位、env 缺省分支吞 econ)+ 全仓 grep 消费点/写点对账。
- 本报告只此一个文件,未改任何代码。

---

## 一、问题清单(按严重级降序)

### 【高】S-1 生产侧 `cw_paid_refreshes` 零递增点——实机恒 0,sim A/B 结论不可迁移

- 位置:`sim/engine_p1.py:991-996`(全仓**唯一**递增点);消费端 `cw3/strategy_shell.py:275`。
- 发作场景:全仓 grep 证实 `operations/` 侧(生产刷新执行链 prep/shop.py、battle_loop.py)没有任何写点。Cw3Live 上实机后 `paid` 恒 0 → ① R05 长线利好 30 刷门永不开;② '120' 计数刷价折扣(resolver.py:317 `paid >= 30` → 1 金)永不触发,实机按 2 金全价决策;③ '102201' 每 4 刷窗口同死。sim A/B 里这些门是开的(decision 与经济真值两侧行为不同),凡依赖 cw3 sim 批得出的 A/B 结论,在实机上系统性失真——判前锁 PREREG 的数据源被接缝污染。
- 辩护方会说"docstring 已挂账(实机 handler 接线后同字段)"。但挂账没写进任何进度账本的可见待办位之外,且 A/B 现在**就在跑**——sim 开门/实机关门的局混在同一判据池里无法事后拆分。
- 严重级:**高**(A/B 有效性 + 实机行为分叉双杀)。

### 【高】S-2 `node_has_combat` 消费 `state.node_type`——供给源接错,sim 恒真、生产几乎恒真

- 位置:`cw3/strategy_shell.py:470`(`node_has_combat = (state.node_type or '') not in ('奖励','补给')`)。
- 发作场景:
  - sim:`engine_p1.py` 全文只有 721-726 写 `sess.node_type_current`(且注释明说这是给决策消费的供给通道,ADR-0276);`st.node_type` 从不赋值,GameState 默认 `None`(cw_state.py:159)→ `node_has_combat` 在 sim **恒 True**。
  - 生产:备战/商店开态节点行被遮、`read_node_type` 恒 None 是有实锤记录的旧问题(session.last_node_type 注释,r7)→ 生产也大部分帧 True。
  - 后果:「奖励/补给节点不刷」这条 p40 子门两侧实际都是死码;更糟的是引擎专门为决策准备了 `session.node_type_current` 真值通道,cw3 壳却读了旁边的死字段——一旦某侧哪天开始给 `state.node_type` 填值,sim/生产立即静默分叉。
- 严重级:**高**(决策输入失真 + 潜在静默分叉,接缝语义错误)。

### 【高】S-3 激活集反查对非规范名静默丢弃——生产 OCR 原始名通道不归一、不告警

- 位置:`cw3/knowledge/invest_mutations.py:623-626`(`ids_for_names` 精确匹配+静默跳过);消费端 `strategy_shell.py:234-245`(`_ids_from_state`)。
- 发作场景:生产写点 `operations/handlers/handle_invest_strategy.py:171-176` 把 **OCR 选中的原始名**写进 `session.active_strategies`;旧消费链为此专门建了 `normalize_invest_name`(cw_investments.py:560 注释明说"session.active_strategies 里的存量 OCR 原始名"),且 L482 记录过"按名精确查 miss → 经济效果被丢"的前科。cw3 新链 `_ids_from_state → ids_for_names` **不做归一、未命中不落日志**,OCR 变体名(多/少空格、错别字)→ 该卡全部突变条目(经济/概率/板面)整卡静默丢失,帧照常构造,无任何可观测信号。docstring 声称"静默跳过是合法的白名单语义"——那是**上游 id 面已经白名单化**的前提,生产名通道不满足该前提。
- 严重级:**高**(实机激活集不完整且不可见,恰是本题"激活集漏源"攻击面的正面命中)。

### 【中高】S-4 `xp_instant` oneshot 位:登记后全仓无消费者,审计④修正变成"重复入账→零入账"

- 位置:`invest_mutations.py:457-462`(登记,'oneshot' tag);全仓 grep `xp_instant` 仅命中登记表与 cw_investments 字段定义。
- 发作场景:'xp_instant' 操作数没有任何 resolver 出口、帧键、E1 台账消费点。伟大征服 12 / 气氛组+ 8 / 成长的快乐 4 / 经验到账 10 的一次性经验在 cw3 完全不入账。旧映射(并入 flow 逐节点重复入账)被审计④修正后,修正是"移出 flow"而不是"接到 oneshot 消费位"——从错账变成无账。且条目 note/tags 均未声明"消费点=后续批"的挂账语义,后人读登记表会以为已闭环。
- 同根附带:`resolver.resolve_xp_flows`(R07 XP 流出口)在 `strategy_shell.py` 的帧装配中**未被调用**——frame 无 XP 流键,202601/202701(条件 +3)、151301(附 30 经验)、xp_per_refresh 等 flow 面同样进不了 `decide_levelup`(升级时机判据缺 XP 期望流入项)。
- 严重级:**中高**(登记完备性宣称与实际消费面脱节;决策质量缺口)。

### 【中】S-5 免费刷额度未接进帧——R1 门用全价刷成本预算,注入局系统性少刷

- 位置:`resolver.py:330-336`(`resolve_free_refresh` 出口存在);`strategy_shell.py:281-299`(frame 无 free_refresh 键)、`477-479`(decide_refresh 全价预算)。
- 发作场景:注入局持"每节点免费刷"卡时,引擎执行层免费刷实付 0(engine_p1.py:986-988),而壳的 p40 R1 门(`refresh_cost_paid * e_ref + reserve + l_loss > v_gap`,refresh.py:146-150)按全价 c_refresh 算成本 → 门偏紧 → 有免费额度时该刷不刷。decisions 里记录的刷预算与执行回执也不对账。
- 严重级:**中**(注入局决策失真;基础局零漂移)。

### 【中】S-6 卖出腾席只腾 1 席,与多买入意图不匹配——decisions['buys'] 遥测虚高

- 位置:`strategy_shell.py:417-440`(sell 循环 `if bench_vacancy >= 1: break`)。
- 发作场景:bench 满、3 个买入意图、席上有 3 个 1★ 燃料件 → 卖循环只卖到 vacancy==1 就 break,发射序 4 仍发全部 BuyCard → 执行层第 1 笔成交、后续被 ADR-0283 满栏守卫拒买。decisions['buys'] 记 3 笔、实际 1 笔:遥测/测试对拍位(record 的 plan 与账本)系统性不一致,腾席的"给买入让位"语义只兑现了 1 席。
- 严重级:**中**(行为+遥测双缺口;非崩溃)。

### 【中】S-7 概率真值旁路:sim 轮岗局的翻倍表已就绪,壳恒传 None 用基线表决策

- 位置:`strategy_shell.py:267-268、285`(`_resolved_frame` observed_probs 恒 None);供给侧 `engine_p1.py:796-799`(`st.refresh_probs = roll_rotation_per_stage(...)`)。
- 发作场景:注入'轮岗'环境后,引擎发牌用翻倍表,壳的 frame['prob_table'] 与 decide_refresh 的 p_hit 用基线表(退基线告警按进程去重后只响一次,后续帧无声)。该注入局的刷新决策按错误分布算完成概率——恰好在轮岗是「选了必 100% 重掷」的新建模下,基线偏差最大。
- 严重级:**中**(限于轮岗注入局;但那正是勘误后重点验证的语境)。

### 【中】S-8 session 四个 cw3/计数属性全是动态 setattr,`cw_paid_refreshes` 无生命周期所有者

- 位置:`strategy_shell.py:226、232、300`(`cw3_stack/cw3_mutation_ids/cw3_frame`);`engine_p1.py:995`(setattr 递增);`StrategySession`(cw_strategy_session.py)**无任何对应声明字段**。
- 发作场景:项目自有判例(r3 review④:"动态 setattr 升正式字段,asdict/repr 完整")在本批被违反——四个属性 asdict/遥测不可见。更实质的:`cw_paid_refreshes` 是局级计数,但没有任何 reset 点——`on_match_start` 不清零,引擎"跨局复用 session 可传"的入口(engine_p1.py:509)也不清 → 复用 session 连跑两局,第一局的刷数滚进第二局,'120' 30 刷门提前打开。计数器"谁初始化、谁清零"无主。
- 严重级:**中**(正常单局路径不发作;复用路径静默错账)。

### 【低中】S-9 `cw3_mutation_ids` 死快照:开局写一次、此后永不更新,与逐帧重推的帧内突变集漂移

- 位置:`strategy_shell.py:232`(唯一写点,on_match_start 时激活集几乎恒空)。
- 发作场景:`_ids_from_state` 逐帧重推只进 frame,`session.cw3_mutation_ids` 停在开局空集。任何判读/测试读这个字段会得到「cw3 全局没激活任何突变」的假象,而 cw3_frame 里是另一份真值——同一会话两个"激活集"表示,快照时点语义未声明。
- 严重级:**低中**(现无消费者;字段存在即诱饵)。

### 【低】S-10 `simulate_p2_replay_entry` 不透传 `strategy_id`——案 b 臂硬编码 decision_v2

- 位置:`engine_p2.py:117-139`(签名无 strategy_id,调 simulate_p1 未传)。
- 发作场景:双被测体切换在主入口(planes=2)完备,但 P2 真值进场臂无法跑 cw3;且该臂新建 session → cw_paid_refreshes 归零,与 planes=2 续局(同 session 计数延续)语义不一致。切换机制装配面在案 b 臂缺失。
- 严重级:**低**(臂本身是交叉校验用;不一致是隐性的)。

### 【低】S-11 `v_gap = k×(V̄_net+卡价)` 的线性外推在 k≥2 时重复计档,R1 门偏松

- 位置:`windows.py:97-110`;换算出处 `calibration.py:73-83`。
- 发作场景:V̄_net 的 rung 流(15.0)是「缺口闭合按主羁绊推进到所追档位」的**累计**值;换算式对 k 个缺口每份都计全额 V̄+卡价,k=2(持有 1 张再缺 2 张)时档位推进被计两次 → v_gap 偏高 → `花费 ≤ v_gap` 门偏松 → 偏过刷。`card_price = min(成员费)`(windows.py:100)在多成员时低估 Σ卡费(当前 dormant:多成员 single_card=False 禁 R1,但 min() 写在装配层、若 R1 放开多类即带病上线)。线性化假设本身未在换算式注释里声明"仅单成员 k 口径经校准"。
- 严重级:**低中**(当前消费面收窄在 single_card;门方向是偏松而非偏紧,过刷在 CW 是真实代价)。

### 【低】S-12 卫生类三件

- `invest_mutations.py:479-483`:`_classify_leftover(effect, has_econ)` 的 **has_econ 参数全程未使用**(588 行传入 True 也无分支),docstring 声称的"无经济建模面的残留"语义未实现——死参误导读者。
- `invest_mutations.py:321-323`:`CURATED['不等价交换占位'] = None` + `CURATED.pop(...)` 的占位-删除舞蹈,注释"dict 字面量不支持删注"不成立(字面量里不写该键即可);噪声进码,违背注释「只留当前值成立理由」规范。
- `strategy_shell.py:119` 与 `liquid.py:31`:跨模块 import 私有符号 `_bench_char_cost`(kernel 内部约定下划线);同批新件沿用旧惯例但把私有依赖又扩散了两个消费点。
- 严重级:**低**(不发作,但都是下次改动时的绊线)。

### 【低】S-13 同段多刷定价不重估(两侧一致地错)

- 位置:`strategy_shell.py:483-485`(n 刷同帧同价发射);`engine_p1.py:982`(`_cost_r = st.shop_refresh_cost or 2` 恒基价)。
- 发作场景:'102201'(每 4 刷全 3 费面)计数窗内第 4 刷的价位变化,决策与执行两侧都不重估——sim 保真度缺口,注入局刷价期望失真。挂账性质,但登记表把它当 resolved 登记,消费面为空这件事无挂账标记。
- 严重级:**低**。

---

## 二、攻过未破清单(攻过、证据在手、未破)

1. **发射序与坐标系合同**:卖出(序1)→升级(序2)→刷新(序3,发生即 return 交还决策环)→买入(序4)自洽;`SellBench.bench_idx` 用 `enumerate(state.bench)` 0 基,与 ADR-0316 槽位表 0-8 合同一致(cw_state.py:490-524);卖出先于升级发射,升级预算的 `gold_liquid`(liquid.py)含将卖 1★ 件,1★ 全额退 → 「先卖再升级」执行序下金不消失,变现不变式成立;买入金位逐笔递减与卖出退金加回自洽。
2. **买入意图先于卖出退金判金**(预算不含退金):p41 腾席语义本就是席位优先、退金是副产品;金紧张场景只会保守少买,不产生负余额或执行层透支。判为设计取舍,不立案。
3. **id/名称唯一性现状**:程序化探测——334 策略 id 无重、83 环境 id 无重、跨表 id 零碰撞、跨类名称零重名;`INVEST_BY_NAME` 417 = `INVEST_MUTATIONS` 417(名字↔id 一一对应,'轮岗' 恰一名)。但 `build_registry` 的 `out[id]=entry` 与 INVEST_BY_NAME 推导均无重复防线,`audit_registry` 的 missing/extra 也抓不到「跨表同 id 静默覆盖」——现状干净属数据运气,防线缺口记 S-12 同级备忘(未立案为 bug)。
4. **curated ∪ 派生并集防双计**:operand 集合去重 + `dynamic_per_streak` 特判,伟大征服 xp_instant 丢失案已修;程序化全表探测:83 env + 334 策略中「派生位被吞」为 **0 条**(含 env 缺省类别分支——当前无「缺省类别 ∧ 有 STRATEGY_ECONOMY 行 ∧ 非 curated」样本,分支吞 econ 的风险 dormant)。
5. **strategy_id 切换装配(主路径)**:config 构造期白名单校验、非法值带迁移提示抛错(currency_war_config.py:78-84);sim 未知 id ValueError(engine_p1.py:575-578);显式传 strategy 时 strategy_id 被忽略已文档化;Cw3Live 位于 strategies/ 扫描源、`__module__` 匹配注册面、STRATEGY_ID='cw3' 与 config 值域/引擎分支三处一致;生产执行器消费 decide_prep 返回的通道存在(shop.py:713),动作形状与旧被测体同族(BuyCard/SellBench/LevelUp/RefreshShop 均为 kernel Action,decide_prep 异常有留证-上抛护栏 shop.py:712-727)。
6. **v3_spend_auth 预算-回执契约绕过疑点**:grep 证实 `v3_spend_auth/v3_posture_receipt` 消费面全部在 decision_v2 内部(arbiter/posture_release),生产执行层不强制 → cw3 壳不 attach 授权包**不构成**拒绝或对账炸点。攻过未破。
7. **轮岗条件化**:PLAZA_PORTALS 恰一个『轮岗』,`_env_is('轮岗')` 精确匹配无变体误配;引擎 796-799「已选 100% 重掷 / 未选恒 None」与登记表 114 勘误注一致;`state.active_env` 生产写点(handle_invest_env)+ obs 同步链(cw_observation.py:1891)闭合。
8. **liquid_gold 口径**:只折 1★、refund_fn 注入不拍值、未知名 cost=0 不入账——与 resolver R13 及 p47 禁卖上界分工一致;deployed+bench 全场遍历与 resolver._all_units 同口径。
9. **calib 单一源**:u/H/V̄ 全部单点常量(`_U_V1/_H_V1/_V_BAR_V1`),`calib_v1()` 与 `v_bar_net_v1()` 同模块同常量,滚动修正单点改;`_V_BAR_V1_LOW`(16.7)目前无访问器(A/B 下沿臂须改码取值)——记为可用性缺口,不构成双源。
10. **测试/护栏现存量**:decide_prep 异常留证-上抛(shop.py:712-727)、满级升级拒付计数、满栏拒买守卫(ADR-0283)均对 cw3 动作同样生效,cw3 动作不逃逸执行层防线。

---

## 三、总评

接缝面最危险的不是机器数学,而是**「供给-消费」两侧各说各话**:S-1(计数生产侧无人写)、S-2(node_type 读死字段、真值通道闲置)、S-3(名通道不归一静默丢)、S-4(登记了没人消费)四个问题同构——登记/供给面宣称完备,消费/接线面断链且**断得无声**。建议下一批把「每个 frame 键/计数器/字段必须有 grep 可证的消费点与写点清单」作为接线验收门,并优先补 S-1/S-3 的生产写点与告警,否则 sim A/B 与实机的分叉会先污染判据、后暴露。
