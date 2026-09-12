# 2026-09-11-unified-state 设计对抗审报告（attack.md）

- 审查日期：2026-09-11。审查者：设计对抗批子 agent（干净上下文）。
- 攻击对象：本目录 design.md / landing.md / details/BoardState-数据结构设计.md（下称「详设」），旁证 recovered/ 索引。
- 判据源：docs/develop/harness/iteration-design.md（写作硬规则与三核细则）、docs/develop/currency_war/game_state/r5-migration-plan.md（八波与验证三元组）、docs/develop/currency_war/decisions/0630-unified-state-journal.md（含两节修订）、0651-two-state-authority.md、账本 .debug/progress/2026-09-11-cw-clear-run/dag.jsonl（T-1..T-33 全量直读）。
- 方法：三核并重（无前提攻击 / 规范遵循逐项核 / 治本核验）。所有代码与文档主张均直调原文件核验（read/grep 行号级），未采信任何转述；判据源之外的旧账（2026-09-06-redesign）未读，相关结论已注明「未核」边界。
- 结论概要：**发现 21 项 = 高 2 / 中 10 / 低 9**。无「设计方向不成立」级阻断；两个高级项均为 landing 阶段小节与已执行事实/捆绑任务的自相矛盾，修订落盘前不宜解 T-2/T-3/T-9..T-12/T-15 的 wait。详设本体的字段规格、依据标注密度与代码锚点准确度经抽查合格（见「攻过未破」第 10 条）。

## 一、问题清单

严重级定义：高=派单即触发返工/裁决冲突或文档自相矛盾；中=对账断链、判据不可验证、过期申报误导后续批；低=措辞/指针/结构卫生。

### 高

**H-1 landing 阶段1 范围/边界与捆绑任务自相矛盾**
- 位置：landing.md §3.1。
- 问题：阶段标题捆绑 T-1+T-2+T-3+T-4，但「范围」只写「cw4_counters 逐 key 审计+键收编落码+cw4 流删除」，「边界」明确「不含效果域内容语义设计件成文（候裁 8 前置）」——而 T-2 恰是该设计件任务（账本 T-2 title=W4前置:cw4效果域内容语义设计件），T-1（决策行 schema C1-C8 定谳）同样不在范围描述内。
- 发作场景：实现者按范围边界读，跳过 T-1/T-2 直接做 T-4 键收编，违反账本 T-4 deps=[T-1,T-2,T-3] 的前置语义；或验收时对「T-2 交付物是否属本阶段」各执一词。阶段小节是派单唯一源，范围内两义不可并存。

**H-2 T-6/landing 阶段3 范围与已执行的删除波 1（ADR-0641）重叠**
- 位置：landing.md §3.3；账本 T-6 criteria；判据源 ADR-0641（docs/develop/currency_war/decisions/0641-delete-wave1-writer-retirement.md）。
- 问题：ADR-0641（2026-09-11 入库，commit 3d4461438）已删除 9 流（decisions/outcomes/exogenous/spend_ledger/shop_snapshots/exec_events/invest_cards/obs_conflicts/runs）全部生产写入端，且其后果节明载「retirement.md 影子框架重构随本批兑现……后续 W7 到达时余量为零」。而 landing 阶段3 范围仍按 r5 W7 全量口径写「处置表定案流写点全部下线」+「retirement.md 影子框架重构文档批」，T-6 criteria 仍列「retirement 影子框架重构+ADR同步」——该 criterion 已被 ADR-0641 满足，属已完成项挂待办。
- 发作场景：worker 领 T-6 后按范围重查 retirement.md 与已删写点，轻则困惑重查、重则把「已删」误判为「漏删」补刀；验收者按范围逐项核会与 ADR-0641 事实对撞。范围应按删除波 1 先行段收窄为：cw4 剩余写点（T-4 辖）+board_state_archive 写点+battle_done 旧写+recorder 残余+保留流定谳执行。

### 中

**M-1 landing 阶段9 边界与 T-15 criteria 直接冲突**
- 位置：landing.md §3.9 vs 账本 T-15 criteria。
- 问题：landing 边界写「建线与接线归后续批，本阶段只采证定口径」；T-15 criteria 预注册含「有源则识别线接入+bs.bench星级消费收口（设计 §3.2.18窟窿二）」——接线做不做、归谁做，两处口径相反。
- 发作场景：采证结论为「有源」时无裁决依据；landing 追认式声明自缚「阶段小节改→账本 criteria 同步改，禁止两处各自演化」，此冲突即违自家纪律的现存实例。

**M-2 W1/W2/W3/W5 已执行但在本迭代 landing 与账本零载体，T-5/T-6 的进入门无可验证凭据**
- 位置：landing.md §3.2「依赖：阶段1；W5 透传域建模绿」、§3.3「依赖：阶段1-2；W1-W3 验收绿」；账本 T-5 标题「进入门=W5已绿」。
- 问题：四波的执行证据在判据源与代码里都在（W1=ADR-0634+match_archive.py:158 注；W2=ADR-0630 修订节；W3=哨兵三脚本切 journal（cw_sentinel v5.2/cw_runs_gap v3/cw_early_stop v4）+cli.py:4 --source 拆除；W5=cw_bs_view.py 域清单「容器值收编」+test_cw_w5_passthrough_adoption.py 在仓），但 landing 依赖行与 T-5 标题只写「W5 透传域建模绿」「W1-W3 验收绿」，不给任何 ADR/评审/测试凭据指针；landing 排除声明也未列这四波。本账本（T-1..T-33）内无任何 W1/W2/W3/W5 任务行。
- 发作场景：编排者对 T-5 放行时按账本对账进入门，「W5 已绿」查无凭据——要么卡派单、要么凭口头放行，验证三元组的「落地审+实机窗口」两腿在本迭代工件内无痕可查。

**M-3 README 进度节与 design.md §0 的落地进度声称过期（批次三在产无记录）**
- 位置：README.md「落地:批次一/二已落地」；design.md §0「批次一/二已落地审查」。
- 问题：详设 §8.7 批次三（含补单⑧⑨）落位面经代码逐项核实已在产：CwStrategy 泛型基类（strategies/impl/cw_strategy.py:72）、StrategyState 正本（mandate_v1/mandate_state.py:72）、session.effect_inventory 载体归一（cw_strategy_session.py:234-240 兼容读口）、免战牌 EffectSpec 条目+递减挂点（cw_investments.py:387-392、prep_actions.py:1495-1517）、节点屏刷新计数写端（cw_screen_encounter.py:136-160、cw_screen_invest_strategy.py:298-302）、桥三函数（cw_board_state.py:1004/1025/1052，cw_loop.py:2142-2150 已接线）、Snapshot 切换（decision_assembly.snapshot_from_obs）。批次三锁文件 test_cw_board_state_batch3.py / batch4.py 在仓。design/README 无「批次三已落地」记录与凭据指针。
- 发作场景：任何按 README 恢复上下文的会话会把批次三当未做面重审或重派；对抗定稿裁决时把在产面当「待设计」处理。

**M-4 landing 追认式声明把完成判据单一源定为账本 criteria，与 iteration-design.md §3.1 方向相反，且漂移已发生**
- 位置：landing.md 头部追认式声明 vs iteration-design.md §3.1「阶段小节=账本唯一源（立任务照小节 add，criteria 预注册指向本节）」。
- 问题：规范方向=landing 派生账本；landing 自声明=账本派生 landing。倒置后实际发生了单向漂移：T-2/T-3/T-9/T-10/T-11/T-12/T-15 增挂 dep T-31、T-5 引用本目录（账本目录）w6-切换波次调研草案的 5 波次序，landing 均未同步（阶段1「依赖：无」vs T-2/T-3 dep T-31 即为实例）。
- 发作场景：后续任何一方改设计或改判据，「禁止两处各自演化」没有可执行的仲裁方向；本次攻击已抓到两处实质漂移（M-1、H-1），该机制性根因不修，漂移会持续产生。

**M-5 landing 阶段2 文件面缺 r5 P6 申报面，与 T-5 criteria 所需文件冲突**
- 位置：landing.md §3.2 文件面 vs 账本 T-5 criteria 与 r5-migration-plan §6 P6。
- 问题：T-5 criteria 要求「last_state三写点删除（cw_screen_prep+cw_op_buy_cards）」「applied-gate族改receipts+reconcile」「cw_expected_state 两态制残余清理」；r5 P6 文件面显式列 cw_screen_prep.py/cw_op_buy_cards.py/cw_evolution.py/Δ池再生管线/cw_expected_state.py。landing 阶段2 文件面只写「kernel 决策簇、strategies/impl、sim、decision_assembly/cw_game_ports、cw_bs_view.py 删除」，上述文件全部缺席。
- 发作场景：worker 按文件面纪律遇 last_state 写点（现树 cw_screen_prep.py:514/:737、cw_op_buy_cards.py:804）即停手上报，或越面改动被验收打回。

**M-6 账本 T-7 缺候裁 7/9 的等待条件**
- 位置：账本 T-7（todo，deps=[T-6]，无 cond）。
- 问题：r5-migration-plan §6/§7 明示候裁 7（正名是否改模块文件名）与候裁 9（cw_state 残余词汇居所）为 P8 前置裁决，现均未定谳；T-7 无 cond 挂门，T-6 终态即 ready。对照同账本 T-1（cond=用户裁决 C1-C8）、T-6（cond=候裁4/2）均正确挂了裁决门。另注：plan 把候裁 2/4 分派给编排者（P2/P7 槽），T-6 cond 写「用户定谳」——裁决人路由两处口径不一。
- 发作场景：T-6 done 后 T-7 自动可派，worker 面对未裁决的居所/文件名设计只能自行拍板（违反交付契约停手令）或空转。

**M-7 详设 §5.2「免战牌无结构化条目卡」申报已过期**
- 位置：详设 §5.2 显式豁免行 vs 注册表现状。
- 问题：§5.2 把「免战牌 +30 经验（:109）」列为「无结构化条目卡、经 §4 投资选择通用通道消费」；批次三⑥落码后 STRATEGY_EFFECTS['免战牌']（id 151301，payload=EconomyEffect(xp_instant=30)，duration_uses=2）已在注册表（cw_investments.py:387-392）。
- 发作场景：建模批按 §5.2 把免战牌再当「无结构化」登记，产生双条目/双写端；§7 冻结判据扫描时同一卡两条归属路径。

**M-8 代码与正本区引用 changes/ 详设，铁律违反且收口清单不全**
- 位置：src 五文件（kernel/cw_board_state.py:5、kernel/cw_bs_view.py:2-5、sim/engine_p1.py:1575、obs/cw_shop_refresh_obs.py:4-5、obs/cw_observation.py:2394）+正本区三处（docs/develop/currency_war/README.md:28、game_state/README.md:12/:102、design/统一观察架构-画面op基类设计.md:4）均指向 changes/2026-09-11-unified-state/details/BoardState-数据结构设计.md；cw_bs_view.py:4-5 另指向另一迭代 changes/2026-09-06-redesign/w5-透传域建模方案.md。
- 问题：AGENTS.md 铁律「代码与正本文档禁引 changes/ 内容（长期引用）」无迭代期豁免条款；landing 正本更新清单只收口「六处代码 docstring」，正本区三处无收口行；跨迭代 changes/ 引用的目标目录按同一铁律可被无理由删减。
- 发作场景：changes/ 生命周期清理（含 2026-09-06-redesign）后，代码 docstring 与正本链接全灭，溯源链断裂。

**M-9 账本 T-12 criteria 判据指针错节（§5.3 → 实为 §7）**
- 位置：账本 T-12 criteria「装备注册表改写字段成员纳入扫描（财富宝钻/诅咒系，设计 §5.3扫描范围）」。
- 问题：详设「扫描范围」在 §7（效果面完备性判据）；§5.3 是效果族归属。criteria 预注册不可覆盖，验收者按 §5.3 定位扫描范围会落空。
- 发作场景：T-12 验收对账时判据定位失败，或误按 §5.3 归属行核扫描范围。

**M-10 §5.2 缺口的建模承接面只有 2/N 进账本，容量投影桥的首批条目无载体**
- 位置：详设 §5.2 开放清单、§8.7 批次三补单⑧；landing 阶段5-8 与账本 T-9..T-12/T-15。
- 问题：§5.2 登记的缺口中仅「本金充裕族条件免费刷新」（T-11）与「词缀」（T-12）有任务；容量改写（节省工位）、发牌族逐卡登记、hp_max 三来源、时点型延迟金载体、长线利好刷价等均无任务，landing 排除声明也未提「本迭代只兜底不建模」。其中最锐的一条：批次三补单⑧的 project_effect_capacity 已在产但其自设前置「首批容量条目入册须同批补观察构造器容量感知」无任何任务可满足——投影恒 no-op，§5.1 明言要防的「按 9 槽摆 3 槽席」危害对节省工位局仍不设防。
- 发作场景：持节省工位局策略按 9 槽摆位被游戏拒；§7 冻结判据因「缺口登记=归属」而可绿，掩盖结构化排期缺口。

**M-11 详设两处引用「恢复局镜像五字段」但全文档未列明是哪五个**
- 位置：详设 §2.1 载体中继段、§8.7 批次二落位面「feed 五镜像点改 BoardState.relay」。
- 问题：批次四 relay 空值闸（「会话侧值已确立」闸）的正确性依赖该五字段集合的封闭性（遮蔽帧值/拦截后到真值/持卡名单 [] 为假事实的论证全建在其上），文档不列集合，实现与复核都要回代码数。
- 发作场景：后续新增第六个镜像喂入点时无人知道它该不该进 relay 闸辖域；对抗复核无法按文档验证闸面完备。

### 低

**L-1 变更史措辞入正文（写作硬规则 3「无过程叙事」）**：详设 §3.2.18「此前『整族撤销』的过度裁定就此纠正」、§3.2.7.1「推翻本节旧『cap 走现场实时读值不入存储』豁免前提」、§3.2.9「〔档案疑点状态 2026-09-09〕…已同日勘误」、§5.3 不等价交换「申报不记预期值→按归属判据改逻辑写」。裁定日期锚（「玩家裁定 2026-09-09」）合法保留；攻击点是「上稿改了什么」叙事——按 AGENTS.md 归 git 历史/ADR。

**L-2 详设缺 iteration-design.md §2.2 模板的「问题与约束 / 关键取舍」成节**：取舍散落（§5.1「曾考虑的替代=每效果独立处理类，否决」、§8.6-8 语义反转史），约束在头部注。内容在场、结构不合模板。

**L-3 README 设计对抗行未按模板带报告指针**：iteration-design.md §4 模板要求「设计对抗:<状态> · 报告=[attack.md](attack.md)」；现 README 该行无 attack.md 链接（本报告落盘后应补）。

**L-4 landing 正本更新清单 docstring 收口清单模块名错位**：列「cw_board_state/cw_bs_view/cw_observation/engine_p1/cw_anchor」，实际 grep 命中为 cw_board_state/cw_bs_view/cw_observation/engine_p1/**cw_shop_refresh_obs**——cw_anchor 无 changes/ 引用、cw_shop_refresh_obs 漏列；「六处」对列名 5 个。

> **裁决（2026-09-12 修订批）**：部分成立。成立部分 = cw_anchor 无 changes/ 引用（grep 证据：全仓引 changes/ 的代码文件仅 cw_board_state.py/cw_bs_view.py/cw_shop_refresh_obs.py 三处带路径，engine_p1.py:1575 与 cw_observation.py:2394 为裸名引用，cw_anchor.py 零命中）——已随修订落盘：landing 正本更新清单收口清单重列为 5 代码文件锚点并除去 cw_anchor。不成立部分 = 「cw_shop_refresh_obs 漏列」「列名 5 个」——修订批直读 landing 原文，该行本已列 cw_shop_refresh_obs（cw_board_state/cw_bs_view/cw_observation/cw_shop_refresh_obs/engine_p1/cw_anchor 六名齐列），与攻击转述不符；该子项按证据驳回记档，不影响 cw_anchor 修正。

**L-5 design.md §2 依据编号不精确**：「依据 = ADR-0630 决策裁定 5」——三渠道封闭集实出自该 ADR 背景节裁定链第 5 条（其内自标「裁定 1」）与决策 2，无「决策裁定 5」编号。

**L-6 无路径锚的速记词与跨迭代引用**：详设 §4.2「A8 盘点坐实」无出处路径（T1a/T1b 有 ADR-0623 锚可解析，A8 没有）；§8.7 批次三落位面引用「统一观察架构 §6.4/§6.5-1/§7.1」及旧账任务号（T-223/T-257/T-320）均无全路径。按 AGENTS.md 注释规范同类判据，持久索引应写全路径或语义描述。

> **裁决（2026-09-12 修订批）**：部分成立。成立部分 = A8 无出处路径、§4.2/§8.7「统一观察架构 §x.x」短引、T-223 旧账任务号无落文锚——已随修订落盘：详设 §4.2 两处与 §8.7 三处补全路径锚（A8 锚=docs/develop/currency_war/design/统一观察架构-画面op基类设计.md §8.0 盘点基线；T-223 改锚落文处 v12）。不成立部分 = 「T-257/T-320 无全路径」——修订批全目录 grep：T-257 在本迭代目录零引用（攻击虚指）；T-320 仅出现于 details/recovered/_INDEX.md 索引行，该行自带原始路径与对应账本任务锚（可解析），非无锚引用。

**L-7 recovered/ 目录为 changes/ 模板外构成**：details/recovered/ 收 6 份找回草稿+索引。_INDEX.md 的地位注记（「裁定以 ADR-0630 为准，非裁定源」）写得规范，但 README/design 未声明该目录存在与其「禁作施工基准」约束，目录本身在 iteration-design §1 构成清单之外。

**L-8 deploy_cap 入容器推翻 ADR-0630 决策 1「不入存储」，详设引注缺权源锚**：§3.2.7.1 只锚 §8.8 例外形态与自证理由；实际权源是 r5-migration-plan W5（用户裁定重写的排期正本显式列 deploy_cap 建模）。实质合规（后裁定覆盖前 ADR），但「ADR 冲突处以其修订节为准」的惯例要求指认覆盖来源，现断链。

**L-9 账本 criteria 内行号漂移实例**：T-5 criteria「last_state三写点删除（cw_screen_prep:563/787+cw_op_buy_cards:781）」对现树实为 :514/:737/:804（漂移 23-49 行）。写点本身在（本报告已核），符号可定位，但 criteria 以行号为主锚时验收会误判。

## 二、攻过未破角度清单

1. **来源四值 vs ADR-0651「只保留 observation/logic 两态」**——详设 §2.1/§8.1 以「carried/prior=obs 族子模」（ADR-0630 裁定链第 5 条同源）调和，§8.1 docstring 显式声明，消费侧折叠有 hp trusted 映射先例（§8.7 W5 ⑤）。调和成立，未破。
2. **恢复局写「开局 hp 先验 82/62」的语义张力**（恢复局当前 hp≠开局值）——被 W5 hp 专项 trusted 映射兜住（prior→False，不进血线门）+首备战帧覆盖，§6.3 决策表三读法归一。未破。
3. **payload 域离屏置 None 例外 vs §2.2「有过正式值禁清 None」硬边界**——例外显式申报为「结构事实非失读」，sim 合成口有落码与锁（批次三补单⑨，test_cw_board_state_batch3）。自洽，未破。
4. **back_layout 8 格超集与 deploy_cap 双存**——准入③例外申报+「域外反推会把近似当真值」论证成立，cap 值域与 e4972b43 实证吻合。未破。
5. **逐卡刷新次数键=normalize_invest_name 规范卡名**——归一函数单一源，写端已落码（cw_screen_invest_strategy 逐槽），免双坐标系换算的论证成立。未破。
6. **两文件模型（E1）下单详设是否越界**——详设辖 BoardState 字段面，journal/决策行归 ADR-0630 与 T-1，总纲 §2 划分与「迁移排期单一源=r5 plan」声明清楚。未破。
7. **「对抗审中」状态与批次一/二/三已落地并存是否违 iteration-design §6 生命周期**（定稿才可派落地批）——追认式声明已披露账本先于文件、各批次有独立落地审（R1/R1.1/R2/R1.2/删除波1），未执行批次（T-2/T-3/T-9..T-12/T-15）已正确挂在 T-31（对抗定稿）之下。已知偏差而非疏漏，未破；但 M-4 的方向倒置使该安排缺一条明文豁免，建议定稿时在 README 补一句追认依据。
8. **§7 冻结判据可执行性**——四步扫描、判定单位=条目下辖每条效果、五源枚举谓词均可程序化，快照记账有落点（进度账本）。未破（但 M-10 指出「缺口登记=归属」使冻结可绿而结构化排期缺位，属排期面非判据面）。
9. **设计依据指向真实性抽查**——T-5 引用的 w6-切换波次调研草案存在于账本目录；T-1 底稿 recovered/T-320-决策行文件schema设计.md 存在；ADR-0634/0641/0623/0622/0620/0559/0596/0239 等被引 ADR 全部在册。未破。
10. **详设代码锚点行号级抽查（约 20 处）**——read_star=cw_identity_obs.py:124、on_battle_end=cw_effect_inventory.py:281 与模块头申报 :151、board_rewrite=cw_investments.py:356/:366、BENCH_CAPACITY=cw_state.py:32、_SELL_MULT=:31、round_start_income=cw_economy.py:326、reconcile_hp=cw_reconcile.py:398、resolve_back_slots=cw_back_layout.py:535、本金充裕=cw_invest_data.py:251-252、星徽羁绊贡献缺失=cw_observation.py:1529-1536——全部命中或 ±2 行。详设的引用纪律总体扎实，未破。

## 三、判据核验记录（直调锚点）

| 主张 | 来源 | 核验结果 |
|---|---|---|
| W1 journal 常开已落地 | match_archive.py:158「无条件常开(R5 W1/ADR-0634)」+ADR-0634 在册 | 成立 |
| 删除波 1 已执行、retirement 重构已兑现 | ADR-0641 全文+commit 3d4461438+哨兵脚本 v5.2/v3/v4 注释 | 成立 |
| W3 旧读面已删 | cli.py:4「--source 双读面拆除」；哨兵三脚本尾读 journal | 成立 |
| W5 透传域已收编 | cw_bs_view.py 域清单（hp/bench/deploy_cap/shop/refresh_probs/active_env/plane_bosses/enemy_affixes/equips/front_max/back_max 均标「容器值收编」）+test_cw_w5_passthrough_adoption.py | 成立 |
| 批次三落位面在产 | 见 M-3 清单（9 处符号级命中） | 成立 |
| on_battle_end 仍未接（T-9 前提） | cw_effect_inventory.py:151「结算挂点仍未接,原状申报」 | 成立 |
| board_rewrite 零消费点（T-10 前提） | 全 src 仅 3 处：字段定义+两注册表条目，零消费 | 成立 |
| 免战牌已有结构化条目（M-7） | cw_investments.py:387-392 | 成立 |
| 代码/正本引用 changes/（M-8） | grep 命中 src 5 文件 7 处+正本区 3 文件 | 成立 |
| last_state 三写点现位（M-5/L-9） | cw_screen_prep.py:514/:737、cw_op_buy_cards.py:804 | 成立（行号漂移） |
| 本迭代账本无 W1/W2/W3/W5 任务 | dag.jsonl T-1..T-33 全量直读 | 成立 |
