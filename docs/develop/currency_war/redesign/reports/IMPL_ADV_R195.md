# IMPL_ADV_R195 · 货币战争策略器重构设计文档对抗审查(第195轮,无锚轮)

> 攻击者=全新视角(无锚自选攻击面);对象=redesign/ 四文档正文(design_economy/design_latch/design_telemetry/IMPL_DESIGN)+CONTRACT_SERIES_DECISION.md **v2 定稿正文**+IMPL_FIX_LEMMAS.md(冻结对账)。辖域纪律:步3+4(cw4/{bridge,proof,mandate,entry,criteria/})中间态不立案;文档断言与已落定终态(步1/步2 产物、契约 v2)的矛盾照常立案;冻结族禁攻击禁新增装置。文件面=本报告单件,除报告外零写入。

## ① 攻击计划(计划成形于通读之后)

通读序:skill 入口 → 契约两件(CONTRACT_SERIES_DECISION.md v2 定稿 / CONTRACT_V2_PROPOSAL.md 归档提案)→ design_economy / design_latch 全文 → 词表源亲读(kernel/cw_prep_actions.py / kernel/cw_state.py)→ IMPL_DESIGN §6.4-R(现行权威迁移序)→ design_telemetry §3.3 衔接位与冻结残余登记节(计划成形后才读,纪律遵守)→ IMPL_FIX_LEMMAS 冻结残余清单。

自选攻击面(无锚):

1. **v2 定稿保真性专项**(任务书点名):六行 diff 逐项对提案、走样删改、附章与修订链一致性;
2. **分域表 ↔ 现树词表对账**(任务书点名):§3.1 商店线域 vs `cw_state.Action` 联合、§3.2 备战线域 vs `PrepAction` 17 具体类;§3.1 代码锚(candidates/remediation/cw_evolution)亲验;
3. **§3.3 ↔ 遥测键登记纪律衔接**;
4. **文档断言 vs 契约 v2 终态矛盾**(IMPL_DESIGN 现行权威节内滞留的 v1 时代指令);
5. **数值锚直调注册表复核**(sell_refund 1★ 净 0 / interest_cap_override 值域);
6. **冻结对账**(11 项零重复)。

## ② 新症(3 症,每症=三元组:行号+检验式+结果)

### 症1(中高)契约 v2 §3.1「完备枚举」全称断言与自 declared 词表源不对账:PickEvent 在 Action 联合内零分类零辖域声明,「装备拖拽,商店线侧」反向枚举了联合外不存在的动作类

- **行号**:
  - CONTRACT_SERIES_DECISION.md L64(§3.1 节头:「`decide_shop_screen` 词表 = cw_state.Action 族」)、L66-73(商店线域表)、L106(「此两域表+§3.3 为完备枚举;发射器实现期增补条目须回本契约改版」);
  - L20-22(§0:商店线词表=「kernel/cw_state.Action 族(ABC 注解现状)」;pick 类辖外枚举的是**接口名** decide_invest/supply/encounter/megastar/partner,未枚举共享 Action 类型 PickEvent 的辖属);
  - src/sr_od/application/currency_war/kernel/cw_state.py L733-734(`Action = (BuyCard | SellBench | LevelUp | DeployMove | RefreshShop | PickEvent | SellDeployed | SwapDeploy | CompTransaction)` —— 9 类联合,含 PickEvent;全文件无装备拖拽 Action 类);
  - kernel/cw_events.py L199(PickEvent 唯一构造位=pick 评分器,非 decide_shop_screen 发射)。
- **检验式**:对 Action 联合 9 类逐类核 §3.1 表覆盖:BuyCard/LevelUpShop/SellBench/SellDeployed/DeployMove/SwapDeploy(拖拽族行)/RefreshShop/CompTransaction=8 类有行;**PickEvent∈联合但表零行**,且 §0/§3.1/§3.3 无一处显式声明「PickEvent 系 pick 域成员、不属商店线发射词表」;反向,拖拽族行(L70)枚举「装备拖拽,商店线侧」——grep cw_state.py 全文件零装备拖拽 Action 类(装备拖拽执行载体=prep 侧 CwOpEquipAll op 内部动作,非 Action 词表成员),该枚举项在自 declared 词表源中**无指称对象**。两读并立:①按字面「词表=Action 族」→ L106 完备枚举断言为假(漏 1);②按 §0 pick 接口排除隐含 carve-out → 需显式辖域声明否则机械对表失败。次级同款:裸基类 `LevelUp` 亦在联合内无独立行(现仅 LevelUpShop 行,isinstance 语义可覆盖但辖域未声明)。
- **结果**:确证。备战线域(§3.2)对账通过(5+12=17 行与 cw_prep_actions.py 17 具体类逐一双向封闭,亲验);商店线域单向开放:真成员漏枚举 + 幻影成员入枚举,完备枚举全称断言辖域未定义。行为面因 §3.3 fail-closed 兜底而 latent(现役 decide_shop_screen 不发射 PickEvent),但按 L106「增补条目须回契约改版」纪律消费该表的发射器/审查者会得到错误的对账基线。

### 症2(中)IMPL_DESIGN §6.4-R R189-4(现行权威迁移序)的 R192 修注把 12 类截断判权威指向**已归档降级的提案档**,且其「v2 定稿前禁照抄」门控语滞留——v2 已定稿后零同步标,文档断言与契约 v2 终态矛盾

- **行号**:
  - IMPL_DESIGN.md L584(R192 修注:「……12 类零截断分类……的逐类截断判以**契约 v2 提案**(`design/CONTRACT_V2_PROPOSAL.md`,**呈报件**)为准——**v2 定稿前批1 不得照抄本现表落码**……上行代码注释『判=契约 §3 初始枚举』随 v2 定稿改读『判=契约 §3(v2)备战线域』」);
  - CONTRACT_SERIES_DECISION.md L1-8(v2 已冻结定稿,2026-09-03 用户批准;正文权威工作副本)、L165(定稿链条:提案←R192/R193/R194 修复全闭环);
  - CONTRACT_V2_PROPOSAL.md L3-4(「正文权威=CONTRACT_SERIES_DECISION.md v2,**本文件降级为历史提案档**……后续禁改,**以契约为单一源**」)。
- **检验式**:grep IMPL_DESIGN.md「定稿」=2 命中(L430 无关/L584 即本条门控语),grep「契约 v2」=9 命中全部系 v1 时代批时叙述(R189/R190/R191/R193 批时快照与降级处置叙述),**零「v2 已定稿」同步标**;L584 修注系给批1(=正在落码的步 3+4 前置发射器批)的**活指令**而非批时快照叙述——其权威指针目标(提案)自身头注已 declared 非权威。三链互斥:IMPL_DESIGN(现行权威迁移序)→提案(已降级史档)vs 契约(单一源)→IMPL_DESIGN 零回指。
- **结果**:确证。步3+4 落码批按 IMPL_DESIGN §6.4-R 派单读到 L584 时,12 类截断判的消费源会取到已降级的提案档(与提案头注「以契约为单一源」正面冲突);「v2 定稿前不得照抄」的门控语义在定稿后失义(读者无法从本文档得知门已开、判据已冻结生效)。R192 修注自身预告的「随 v2 定稿改读」动作无任何后续批兑现(R193/R194 修复批文件面均不含 IMPL_DESIGN L584 同步;design_telemetry R192-R194 节亲读确认)。L530/L537/L571 的「契约 v1 已冻结」引用有批时快照辩护,不立案;L584 单独立案。

### 症3(低中)v2 定稿附章(六行 diff)相对提案发生证据链走样删减:裁定指针、核验记录与 SwapDeploy 现役发射代码锚丢失,与定稿头注「变更全记录见文末附章」的自 declared 承诺不符

- **行号**:CONTRACT_SERIES_DECISION.md L156-163(附:版本变更记录六行)vs CONTRACT_V2_PROPOSAL.md L60-69(提案附章同行)。
- **检验式**:逐行对比(本批亲执):行1 丢失「『BuyCard(商店)』限定词升格为域标注」半句;行3 丢失「粒度」词、「R193 症3 裁定」指针、「先例=既有 fail-closed 分键登记通道」;行4 丢失「拖拽族恢复 SellBench/SellDeployed/DeployMove 显式枚举+坐标系限定词」「R193 症1 裁定」;行5 丢失 SwapDeploy 现役发射证据锚(decision_v2/remediation.py L687 `remedy_slot`/kernel/cw_evolution.py L1581 `valley_rollback`——**本批亲验两锚现树为真**:remediation.py L687 `return [SwapDeploy(d_idx, ben_idx, reason='remedy_slot'...)]`、cw_evolution.py L1581 `return SwapDeploy(d_idx, b_idx, reason='valley_rollback'...)` 亲读在位)与「grep SwapDeploy CONTRACT_SERIES_DECISION.md=零命中」核验记录。判语义(fram stable 分类/cap 口径/fail 方向)逐行核对零改义;§3.1 正文侧锚(candidates.py L504/L599/L616、remediation.py L340/L450、cw_evolution.py L1588)本批全部亲验为真。
- **结果**:确证,保真性缺陷(登记/溯源面)。定稿头注(L4-5)自称「变更全记录见文末附章」,而附章记录薄于提案同位内容——修订链追溯(哪条变更经哪症裁定、凭什么证据)在权威件中不完整,后续轮按附章回溯裁定时会漏 R193 症1/症3 的裁定语境。行为面零影响。

## ③ 豁免(不立案项及理由)

1. **契约 §7 现状锚行号**(cw_strategy.py L130-139/L142-153、cw_screen_prep.py L1191-1215、buy_cards.py L589-707):§7 自declared「流程侧重构中,路径/行号按『契约占位』处理,漂移不立案」;亲读 cw_strategy.py L132-141 现位与锚域语义一致,无实质失真。
2. **IMPL_DESIGN L517/L530/L537/L556/L571 等的「契约 v1 已冻结」引用**:R189/R190/R191 批时快照框架内的历史叙述,打标链在位,快照规则辖(与症2 的 L584 活指令区分)。
3. **§3.3 与遥测键登记纪律的衔接**:design_telemetry L2615(R193 症3 行)亲读确认——键名/粒度已从契约正文移除、单一源=design_telemetry 键节,契约侧只留行为义务;衔接成立,不立案。
4. **数值锚复核通过项**(不立案,申报复核结果):sell_refund(star=1,cost)=cost ⇒ 1★ 买卖净 0(cw_state.py L903-918 亲读,refund_full 前提成立);interest_cap_override 值域 {开源节流:9, 利息上调:10, 买断制:0}(cw_investments.py L153-155 亲读,与 latch §L2/契约行 10 条件式口径一致)。
5. **§3.2 备战线域对账**:17 类双向封闭(见症1 检验式),零缺口零幻影,不立案。
6. **cw4/{bridge,proof,mandate,entry,criteria/} 中间态**:步3+4 并行批在飞,辖域纪律明文不立案(本批亦未读其未定稿内容)。
7. **冻结族位点**(telemetry L41/L53/L61/L67/L69/L75 等):冻结辖,禁攻击,只确认在案照录。

## ④ 冻结对账(冻结残余 11 项,零重复)

亲读复核(IMPL_FIX_LEMMAS.md L3370-3382 + design_telemetry 登记节):

- LEMMAS 侧:清单 9 项,第 7 项经 R182 销账标销账(R178-症1 修复批就地消解,亲读销账标在位)→ **有效 8 项**(#1 C_int 双向不对称/#2 有效性门错位/#3 统计单元=帧/#4 R65-1 落位缺口/#5 N_gate 版本锚/#6 协变量前提过强/#8 窗口高侧预算现值 cap/#9 λ̂_U~0.3 旧坐标);
- telemetry 侧 3 项:第 10 项(R98 节,激活率门行 L67 裸 cap 符号)、第 11 项(R115 节,现位 L929,激活率门验收级段滞后;R184 并入申报辖域扩展)、第 12 项(R162 节 L2109,D_ε 门监督面行引注滞后);
- 合计 8+3=**11 项**,与任务书口径一致;逐项对象亲读比对:LEMMAS #8(L53 高侧预算)与 telemetry #10(L67 激活率门行)/#11(L69 验收级段)/#12(L75 D_ε 监督面)位点互异、零重复;本批零新增冻结族立案、零冻结族攻击。

## ⑤ 清洁门申报

- **文件面**:本报告单件(`.debug/temp/currency_war/redesign/IMPL_ADV_R195.md`),除报告外零写入、零源码改动、零 git 操作。
- **禁凑数/禁压症**:3 症均亲验成立才立案;症1/症2/症3 检验式全部可复现(行号+grep/逐行对比+代码亲读);已检验未立案项(豁免节 1-7)逐项给出理由,无「查了但没写」的暗仓。
- **无锚纪律遵守**:计划成形前未读 IMPL_ADV_*.md(本批全程零读 R1-R194 报告原文;R192/R193/R194 语义经 design_telemetry 登记节与标链转录位获取,且均在计划成形后);telemetry 登记节在攻击计划成形后才读。
- **辖域纪律遵守**:冻结族(六面装置)零触碰零攻击;步3+4 中间态零立案;流程侧代码锚豁免、策略器侧锚(candidates/remediation/cw_evolution/cw_state/cw_prep_actions/cw_events)全部现树亲验。
- **强度最弱环申报**:症3 为登记/溯源面缺陷(行为零影响),强度=低中;症1 行为面 latent(依赖未来发射器误入 PickEvent 才显化),强度评级取其文档基线失真面(中高)而非行为面。
