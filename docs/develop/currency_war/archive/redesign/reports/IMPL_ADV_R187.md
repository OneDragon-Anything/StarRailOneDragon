# IMPL_ADV_R187 · 复核轮(定向验证 R186 修复批)

> 复核对象=R186 修复批(无锚轮发现三症,两文件面=design_telemetry.md L151/L193/L194/R185 节 L2369+design_economy.md L5;登记=telemetry 文末 R186 节 L2378-2403)。本轮零新症不推进清洁计数、有新症则重置。只读禁改(代码仅只读引证),本报告=唯一写入;零 git、零源码修改。结论强度取最弱一环;一切断言以当轮亲读行号/亲跑 grep 为证(2026-09-03 后现树快照)。

---

## ① 复核判定(逐项三选一:真解决 / 表面绕过 / 修复引入新问题)

### 1. 症1「三处锚现码化」= **真解决**

- **代码现位亲读复证**:(src/sr_od/application/currency_war/sim/engine_p1.py;read L745-776;L758=`'interest': min(_icap, st.gold // 10),`、L770-771=`if _pk is not None and _pk not in sess.active_strategies:` / `sess.active_strategies.append(_pk)`;grep `sess\.active_strategies\.append`(currency_war 全目录)=唯一命中 L771)——与新锚声明逐字对位 ✓。
- **文档侧新锚在位**:(design_telemetry.md L151/L193/L194 亲读)三处现行文分别为「engine_p1 L770-771(append 唯一现位;R186 批改锚,R185-症2 同款)」「engine_p1.py L758 亲读(利息行现位;R186 批改锚)」「engine_p1.py L770-771(append 唯一现位;R186 批改锚,R185-症2 同款)」✓。
- **标内批时快照与旧锚史档引文形态**:三处各缀【R186 锚同步标:原锚 L762-766(或 L752)失准(R185 修复辖域漏 telemetry 侧),IMPL_ADV_R186 症1;批时快照=亲读】——旧锚字面仅存标内史档引文,打标不删史形态成立 ✓(R185 节 L2360 先例同款)。
- **语义零变更复核**:R186 节 L2390「计数对象/通道声明/sim 恒 0 论证、分键结构逐字保持」——L151 的「谓词命中事件计数,非恒 0」/L193 的「判定左端 ≤ cap 恒假」/L194 的「构造性无假名、假名频度键恒 0」三处承重句现行文均在位且与 R186 报告所引原文字面一致(逐段比对)✓。计数对象(m6_caplatch_window 联合计数/interest_overcap_trigger R79-3 触发帧)、通道分叉声明(实机 overlay OCR ↔ sim 注入点)均未动。
- **判定=真解决**,非表面绕过(锚与新码对位可复算)、非修复引入新问题(语义面逐字保持,亲验)。

### 2. 症2「R185 节复扫作废链」= **真解决**

- **全称句原样保留**:(design_telemetry.md L2369 亲读)「六审查文件其余位点零 `L762-766` 现行态命中」原句字面完整在位,零回改 ✓。
- **作废标闭合**:同句后缀【R186 复扫勘误标(R186 批追加,打标不删史,原句字面保留):…本句「零命中」断言作废,以 R186 节复扫为准,R185 节其余内容零回改;IMPL_ADV_R186 症2】——指针/作废辖域/归因三要素齐 ✓(R118/R131 先例形态)。
- **R186 节复扫辖域完备性独立复核**(本轮亲跑):键集 `L762-766`(六审查文件 AllMatches)观测命中=design_telemetry L151/L194(锚同步标内史档引文)/L689(R109 观察项登记行)/L720(R110 登记节)/L2360/L2369/L2375(R185 节+勘误标)/L2382/L2383/L2394/L2402(R186 节本节,由节内 L2402 自增双报申报「本节自身成形引入 …字面命中增量(全部落本文件本节=登记语义)」)+design_latch L26(R185 锚勘误标内史档引文)+IMPL_DESIGN L85(R76-2 标内引文)+IMPL_HISTORY L163/L168/L184(批段史,章程辖)。**申报集(R186 节 L2394 列举位)∪ 节自增集(L2402 申报)= 本轮观测集,逐位对账零差**;**现行态正文(非标内/非登记节)死锚=零** ✓。
- **当前锚位终清主张独立复核**(R186 节 L2395 键集 `engine_p1(\.py)? L\d+`):本轮亲跑观测=申报集(telemetry L151/L193/L194/L689/L2360/L2370/L2376+latch L13+IMPL_DESIGN L85/L304+IMPL_HISTORY 各行)∪ R186 节自体位(L2382/L2400/L2403,登记/自检语义)——零差;现行态正文 engine_p1 锚全部现码化或经裁定幸存 ✓。
- **判定=真解决**。

### 3. 症3「economy L5 计数同步」= **真解决**

- **grep 亲算(修后现值)**:(design_economy.md;Select-String `NMF §` -AllMatches;occurrences=23 on 17 行,分布=L5×5/L11/L16/L17/L23/L24/L25/L26/L30/L38/L39/L41×2/L43/L49/L50/L51×2/L98)——L5×5=批前自指 3+R186 计数勘误标自增 2(「NMF §4 P25」引文+检验式字面),23−5=**18** 与头注「共 18 引用」一致 ✓。
- **清单含 L98 且 18 位逐位实存**:L5 现行清单=(L11/L16/L17/L23/L24/L25/L26/L30/L38/L39/L41×2/L43/L49/L50/L51×2/L98)=18 位,与 grep 观测行集完全相等(逐位)✓。
- **双快照各自单义复算**:勘误标内检验式「21−3=18」系编辑前批时快照(R186 节 L2396 显式申报),修后现值 23−5=18——两快照各申报各辖域,复算均成立 ✓。
- **IMPL_DESIGN 侧互恰**:(IMPL_DESIGN.md;Select-String `NMF §` -AllMatches;occurrences=48,L3×3 自指,实指 45=37 单行+四行×2(L128/L133/L217/L274),48=3+45 恰合)——两侧计数对象分立(IMPL_DESIGN 45=该文件实指;economy 18=本文件实指),无交叉相加主张,申报单义 ✓。
- **判定=真解决**。

### 4. R186 节登记与实况一致(报告-文件一致性专项)= **一致**

五处编辑落点(telemetry L151/L193/L194/R185 节 L2369+economy L5)全部本轮亲验在位且形态与登记格描述相符;节内三条复扫的检验式本轮全部重跑,结果逐项相等(见上);节内自检声明的代码快照(engine_p1 L752=`and _prev_node in LOSS_GOLD_BY_NODE:`/L758/L770-771、grep 唯一命中 L771)本轮亲读逐字复核成立 ✓。文件面申报(两文件)与实况一致 ✓。

---

## ② 新症清单(2 项,均出自本轮任务书泛化步终扫,非 R186 修复面失真)

### 症 1(中低)design_latch L11 `cw_state.py L150` 行号锚死——「自述亲读」类断言绑错行(R185-症2/R186-症1 行号轴病类的第三文件实例)

- **论断**:design_latch.md L11(§L1 现行态正文)「cw_state.py L150 自述『一回合决策时的局面快照』」——该引文现位 **L157**(class GameState docstring,L155-157),L150 现内容=snapshot_copy docstring 尾行(「占帧预算 <0.1%。隔离锁=test_cw_w633_migration_b3(迁移哨兵)」,ADR-0465 §9 后插入段),偏移 7 行。无批时限定、无打标。
- **证据(三元组,当轮亲跑)**:(design_latch.md;read L11 亲读字面如上;src/sr_od/application/currency_war/kernel/cw_state.py read L144-163 + Select-String `一回合决策时的局面快照`=唯一命中 L157;结果=L150 现内容不含该引文,引文绑定错行)。
- **推理链**:R76/R77 批时亲读在案(IMPL_ADV_R77.md L102「kernel/cw_state.py L150『一回合决策时的局面快照』✓」=批时快照为真),后随 cw_state.py 头部插入 snapshot_copy 段(L144-152,注释自引 ADR-0465)使 GameState 类整体下移——行号漂移未双报未重锚,「自述」断言现绑在无关注释行=虚假核验形态(与 R186-症1 ③「亲读」锚死同款)。史档副本(IMPL_HISTORY L168/LEMMAS L3099/L3109)系批段史零回改辖,仅现行态正文位立案。严重度=中低:载体论证(GameState 逐帧快照 ⇒ 禁承载锁存)语义仍真,纯定位轴失真;但 §L1 系锁存载体裁决(R76-1)的承重引证行。
- **处置建议**:锚现码化(L150→L157,缀锚同步标+批时快照),R185/R186 先例同款;登记=design_telemetry 文末 R187 对应修复批节。

### 症 2(中低)design_telemetry L194 归因分键⑤ `cw_effect_ledger.py L182-184` 行号锚死——范围现指 docstring,逐字路由代码现位 L187-192

- **论断**:design_telemetry.md L194(现行态键节)⑤「append 通道=cw_effect_ledger.py L182-184 逐字等值匹配」——该范围现内容=effects_from_strategies 的 docstring(L181 def、L182-186 五行 docstring),逐字路由代码(`for name in strategy_names: s = get_strategy(name)` 循环)现位 **L187-192**。无批时限定、无打标。
- **证据(三元组,当轮亲跑)**:(design_telemetry.md;read L194 亲读字面如上;src/sr_od/application/currency_war/kernel/cw_effect_ledger.py read L181-192;结果=L182-184=docstring 行「注册表 EconomyEffect → AggregateEffect 路由…」「(空行)」「只路由**台账可表达**的字段…」,不含任何匹配语句;匹配循环=L189-192)。
- **推理链**:R90-3 批时亲读在案(IMPL_FIX_LEMMAS L3306(b)「append 通道=cw_effect_ledger.py L182-184 逐字等值匹配亲读」=批时快照为真),后随 docstring 扩写(现 5 行)使循环体下移——同症 1 同病类(后插入代码段致行号漂移、未随漂移双报)。加重申报(如实区分):该锚位于 R186 修复批编辑行 L194 本身(该批在同行改 engine_p1 锚),但 R186 复扫键集单义限定 `engine_p1`(R186 节 L2395 自述「六审查文件锚位终清」辖 engine_p1 键集),effect_ledger 类锚此前从未入任何泛化扫辖域(R185 泛化扫 12 位=latch/economy 侧、R186=engine_p1 键集)——不构成 R186 登记失真,系「类代码锚全目录终扫」义务本轮首次被任务书显式覆盖所暴露。关联位辨析:economy L121 同文件锚「cw_effect_ledger.py L184『只路由台账可表达字段,行为条件流/期权类各自归位』」系**引文锚**——引文「只路由**台账可表达**的字段;行为条件流…期权类」现位 L184-185 亲读命中=活,不立案。严重度=中低:第五通道(OCR 假名 append)的存在性论证对象(effects_from_strategies 路由)仍在邻近且语义未变,纯定位轴失真。
- **处置建议**:锚现码化(L182-184→L187-192,缀锚同步标+批时快照+漂移归因=docstring 扩写),先例同款;登记=design_telemetry 文末 R187 对应修复批节。

---

## ③ 泛化扫清点(engine_p1 / cw_loop / registry 类代码锚全目录终扫,六审查文件,现树命中验证)

- **engine_p1 类**:21 行位点亲跑归类——现行态正文 3 位=telemetry L151/L193/L194(R186 修后锚,本轮代码亲读对位 ✓);语义锚幸存 1 位=latch L13「engine_p1.py L758-766」(被直引注释「收入结算后、决策前」现位 L764-766 在范围内亲读验证,R185 节 L2360 裁定维持 ✓);其余=登记节(telemetry L689/L2360/L2370/L2376/R186 节自体)/标内史档引文(IMPL_DESIGN L85/L304)/批段史(IMPL_HISTORY 各行,含旧位 L725/L803,章程辖)。
- **cw_loop 类**:latch L13 与 telemetry R184 节锚(L123 明文「PREP_SETTLE_S 备战稳定门已退役」/L620-631 0e 分支/L630 id_mark/L868-875 备战双锚)——L123/L620 本轮亲读命中 ✓(「HandleInvestStrategy(self.ctx).execute()」在 L620);battle_loop.py 旧文件名锚仅存 IMPL_HISTORY L171 批段史(R184 已裁 src 全树零命中,本轮 grep 锚式复核=六审查文件外零现行态位)✓。
- **registry 类**(cw_investments/cw_invest_data/cw_effect_ledger/cw_state/cw_economy):锚位点亲跑+逐位现树命中验证——cw_investments L153(开源节流 override=9)✓/L242(狸财经狸 flat=2)✓/L586(def aggregate_economy)✓/L600-602(守卫 min)✓/L611(max 取宽)✓/L616(or)✓/L617-620(守卫 min)✓/L621(概率补集)✓/L623-628(override max 后置)✓;cw_invest_data L283(id='304001' 狸财经狸 effect 原文含「每回合获得利息+2金币」无条件陈述)✓;cw_economy L118-120(`_strategy_economy` 直调 aggregate_economy)✓;get_strategy 现位 L758-761(normalize+dict.get,与 latch L19「dict.get 无模糊」口径相容)✓;cw_state L150=**死(→症 1)**;cw_effect_ledger L182-184=**死(→症 2)**、L184 引文锚(economy L121)=活 ✓。IMPL_DESIGN L304 双锚(L586/L242)现树命中(标内引文+内容双活)✓。
- **清点结论**:现行态正文死锚=2 位(症 1/症 2),其余全部现码命中或经裁定幸存/登记史档辖。

---

## ④ 冻结残余节(11 项口径复核)

任务书口径「11 项(第 7 项已销账)」复核**成立**:三元组=(IMPL_FIX_LEMMAS.md L3370-3382 清单亲读+L3380【R182 批销账标】在位「本项销账——冻结残余计数 12→11」;算式=LEMMAS 在册 9−销账 1=8 有效+telemetry 3=11;R186 节 L2388 同口径申报)。本轮两新症均非冻结族位点(症 1/2=现行态正文行号锚面),冻结族(D_ε 门/有效性判据/标定通道/哨兵/激活率门/cap 消费参数化度量面验证装置)零触碰、零攻击、零新增装置提议,冻结残余零新增零销账。

---

## ⑤ 清洁门申报(复核轮口径)

- **R186 修复批复核结论:三症全部真解决、登记与实况一致**(①节逐项判定+三元组+推理链在案)。
- **本轮 2 新症(症 1 中低+症 2 中低,均出自泛化步终扫)⇒ 清洁门计数断链,重置 0/5**(复核轮口径:有新症 ⇒ 重置;两症同病类=后插入代码段致行号漂移未双报,R185-症2/R186-症1 行号轴家族延续)。
- **自指域申报**:本报告检索轴字面(`L762-766`/`NMF §`/`engine_p1`/`cw_state.py L150`/`cw_effect_ledger.py L182-184` 等)写入 IMPL_ADV_R187.md(六审查文件之外的新文件),六文件命中基线零污染;直引均为连续 substring 且逐段申报源行;代码引用当轮现树亲读亲跑(批时快照=2026-09-03 后现树)。
- **边界声明**:审查域=六文档设计层+R186 修复批复核+任务书泛化步(engine_p1/cw_loop/registry 类)终扫;代码仅只读引证;REORG_COVERAGE_MAP/IMPL_HISTORY 未做全量指针对拍(申报为未覆盖轴);obs/cw_observation.py 类锚未入本轮键集(latch L11 对其无行号锚,史档副本批段史辖)。结论强度取最弱一环:两新症的漂移归因(cw_state=snapshot_copy 后插、effect_ledger=docstring 扩写)由现树注释自引 ADR 编号+批时亲读史档推定,未用 git 溯源(零 git 约束),不影响「现位失准」的立案证据自足性。∎
