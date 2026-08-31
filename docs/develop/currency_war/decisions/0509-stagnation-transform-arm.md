# ADR-0509: W948 转型臂——停滞评估臂(锁线可改判语义)+ P2 入口弱占位

## 状态(Status)

rejected→cleaned(开关生命周期第 4 态:sim A/B 判负,整机制删码;决策 why、负结果与复活条件保留本件)

## 背景(Context)

设计件:`.debug/temp/currency_war/w948_transform_design/DESIGN.md`(W948,零代码设计批,含代码级核对三条与防振荡论证)。

病灶(两局复盘同型缺位,实证锚=复盘 g_20260831_053546:锁 DOT 队后 form_score 恒 0.65 达 7 轮、每战掉血、板混 1★ 填充、零重估):「锁」在 v2 意向状态机里只实现了**承诺语义**,缺**「当前最优假设」语义的持有期半边**——锁定后进度侧停滞无任何重估通道。DESIGN §0 代码级核对证实:①form_ok 全部消费点均为当帧谓词,无时间维计数器;②dir_switch 是纯遥测观测字段,P2 线锁的真实裁决链四条通道(出口①/②/门闩/降格)在停滞态全部结构性关闭,且门闩(v3_line_gate_latch)是设计件新指认的第三抑制面;③演进引擎对 form_ok=False 锁定局只加深不换线(保护组+off-lock 降分,方向变更唯一入口 cw_intention 无停滞输入)。

ADR-0429 增补已裁定「若要 v2 具备换线纠错能力,归撤销出口灵敏度独立演进」——本件即该演进的落地:在撤销出口的上游制造**进度侧触发面**。

## 决策(Decision)

### 机制(停滞评估臂,甲)

仅 P2 锁定态:每评估窗(W=`stagnate_window_rounds` 轮)对照窗首快照,**窗级过程量**判据 = 锁线采购集缺口未下降(gap = `_line_hoard` 角色目标件未到手数,存量单一源)∧ hp 净下降(战力侧确证,防金筹措期误判)∧ form_ok 恒 False 贯穿窗内(当帧谓词逐帧 AND,读 `session.v3_form_ok`);连续 N=`stagnate_windows` 个停滞窗 → 降级 weak,**完全复用撤销出口①的降级形态与 revoke_evidence 字段契约**(phase/weak_comp/prev_lock_layer 同款),证据 kind 独立命名 `'stagnate'`(fields: windows/gap_from/gap_to/hp_from/hp_to/plane)。撤后当轮不重锁(同 revoked 语义);不走 C4 门拦截路径、不受回锁闩抑制(闩辖出口①②,停滞是独立进度侧证据通道)。

**不升格 form_score 进判据**(守 ADR-0353 纯遥测口径裁定);hp 只作伴随条件不作方向(守 strategy-work §4 过程量/末端量分工)。

### 防振荡(与 ADR-0319 排除项划界)

- 单向降级:只做 locked→weak,不反向;原线回锁仅经既有回锁信号通道;
- 冷却驻留:`stagnate_cool[线]=位面`,同线每位面至多一次改判(事件频率上界=线数,结构性排除逐帧摇摆);位面切换清计数与冷却;
- 与被排除的「分数涌现换线」不同构:排除的是逐帧分数差(高频双向无门槛),本臂是低频窗级进展证据单向降级(带 gap/hp 双证据、下游仍过 C4 门与信号门槛)。

### 出口分支(salvage 续命,丙;无独立开关,随甲)

stagnate-weak 持续超 `salvage_window_rounds` 轮(或位面剩余节点 ≤ `salvage_deadline_nodes`)仍无新线 → `hoard_target_set` 返回 mode='salvage'(跨线骨架,停止原线终局件投入=「停止给死线供血」)。salvage 是 weak 的**子模式,非 absorbing**——新信号照常落新线救回;P3 demoted_endgame absorbing 语义零改动;不授权任何支出数值(金流改道归危机臂自身判据,DESIGN §2.6 划界)。

### 伴生入口(P2 弱目标占位,乙)

进 P2 清 p1_pair 后仍 unlocked 且无即时信号 → 按带入资产最厚(与 P3 强制锁线同判据 `_asset_thickness`)派生弱占位线名(`weak_placeholder`),hoard 返回 mode='p2_weak_target' **优先于⑤绯英兜底**(弱目标=有依据的初始假设,绯英=无信号默认落点)。占位不进 locked 态、可被任何信号推翻,天然无承诺语义。

### 开关形态(registry,默认关=零漂移)

`intention_stagnation_arm_enabled`(甲,含 salvage)/ `p2_entry_weak_target_enabled`(乙)。关臂所有新代码路径不进入、状态族恒缺省值,行为逐位不变(单帧锁 `test_cw_w948_transform_arm::test_off_arm_zero_drift` 钉住;守卫移除红检=变异去门后该锚转红,已实证)。

## 备选方案(Considered Options)

- **乙(P2 入口桥目标接管)为主**:只解决「没有评估对象」,不提供评估与改判通道;弱目标无停滞评估配对则锁死后退化为另一种承诺语义。被选为同件伴生入口(甲的入场侧投影)。
- **丙(降格续命辖域扩展)独立立项**:无自身触发面;若复用 demoted(absorbing)则 P2 中段终局化过激,与 ADR-0319 冲突。被收编为甲的出口分支(非 absorbing 弱态子模式)。
- **只调 C4 门/出口①灵敏度**:ADR-0429 的 0 触发教训——门有消费点无触发面则空转;ADR-0436 已证出口①提灵敏度是噪声方向。否决。

## 后果(Consequences)

- 正面:补齐锁语义「可改判」半边,两局病灶(形态 A 锁后停滞 / 形态 B 无线空转)各有一条结构通道;遥测/下游零新增面(字段契约全复用)。
- 代价/风险:`STAGNATE_WINDOWS`/`W`/`SALVAGE_DEADLINE`/`SALVAGE_WINDOW` 全部是 sim 校准常量(设计推断初值,本 ADR 不授权数值终值;实机 gap 读数受 OCR 观测口径影响,sim 读数不可互换);form_ok 读数滞后一帧(窗级判据对此稳健)。
- 开臂判据挂账(DESIGN §2.4,跑前写死):
  ① **观测批**:sim n≥300 开关关,统计形态 A 跨局占比存照(W951 已立 sim form 存照基线:形态 A 1.7% / 形态 B 0%);占比不足=概念数据否决,直接清理;
  ② **A/B**(同池指纹):P2 存活轮数分布与达标占比改善,且换线次数/摇摆形态占比**不升**(防振荡验收线);乙臂=P2 前 3 轮方向字段非空率与早期买入有效性改善+dir_c 空转局占比下降,与甲正交性锚(乙 off × 甲 on)复验;
  ③ **门闩零漂移锚**:off 臂与现行 off 臂逐位相等。
- 验证分层(DESIGN §2.5):行为转移/冷却/salvage 转向/门闩不受扰/零漂移=sim 单帧锁(本批已落 `test_cw_w948_transform_arm.py` 17 锁);N/W 阈值整局演化与形态占比=构造账本锁+sim 批(开臂前置);参数终值与真实收益=只能实机。

## 判据与验证(Evidence)

- 判据 = DESIGN §0 代码级核对三条 + §1 三候选评估 + §2 正式设计;实证锚 = 复盘 g_20260831_053546 + W951 sim form 存照(形态 A 1.7%/形态 B 0%)。
- 验证 = `test_cw_w948_transform_arm.py` 17 锁全绿(判据单帧锁×4/触发链×1/防振荡×3/salvage×3/弱占位×3/关臂零漂移锚+registry 字段面×2)+ 守卫移除红检(去门→零漂移锚红→还原绿)+ 邻锁(w611×2/w633/w917/w935†/w951/form_gates)绿 + ruff;†w935 与 w614 digest 锚当次红/收集错归**并行除开关批在飞改动**(worktree registry 已删 spend_receipt_gate_enabled 而 w935 测试仍构造之;HEAD 内核换入复跑 digest 仍红=与本批无关)——**已结案(除开关批收口)**:契约无条件生效(ADR-0504)后 w935 收集面改无条件语义、w614 锚重钉 d0051d19…(复合窗口位移如实声明+锚有效性以各批 A/B 判据为前提,见该锚注释)。
- 增补(sim n=300×2 深挖批证据):P2 主死亡形态的 form 读数为**假绿**(form_ok 恒 1.00 ∧ 意向核心单副本 ∧ 板面冻结),原「form_ok 恒 False」伴随条件在 P2 被假绿恒短路=触发面定向空洞。修订:「未成型」谓词扩为 `form_ok False ∨ (form_ok ∧ 意向核心到手 star 当量 < stagnate_core_min_copies)`——假红/假绿都计入;三合取其余项与状态机/下游零改动;触发面洞对账全文= `.debug/temp/currency_war/w954_transform_impl/CHECKPOINT_w957_reconcile.md`。降级后半程(向 P2 终局 comp 升格)立独立批(开关 `p2_promote_enabled`,prereg=w954/w958 两份预注册)。
- 联合 A/B 负结果(sim n=300×3 同 seed 配对,详 `.debug/temp/currency_war/w954_transform_impl/REPORT.md` §6/§8):判据修正后触发面治好(33 例降级全带证据),但 P2 存活/死局攥金无改善;升格派生通道触发面为空(真实③信号占满 weak 帧);且 33 例降级中 12 例次帧被同线豁免回锁原线——**信号层同线豁免与假设失效评估存在语义层冲突**(判死的线被自家信号复活)。

## 清理记录(Cleanup)

清理批(编排者兑换裁决,开关生命周期第 4 态)删除范围:
- registry 字段族 8 项:`intention_stagnation_arm_enabled`/`p2_entry_weak_target_enabled`/`p2_promote_enabled`/`stagnate_windows`/`stagnate_window_rounds`/`stagnate_core_min_copies`/`salvage_deadline_nodes`/`salvage_window_rounds`(原位留墓碑注记);
- cw_intention:`_stagnation_tick`/`_p2_promote_candidate`/IntentionState 停滞状态族(stagnate_cool…weak_placeholder)/update_intention 停滞触发、升格、占位、salvage 推导四段/hoard `salvage`+`p2_weak_target` 分支(模块头留墓碑);
- 锁组 `test_cw_w948_transform_arm.py`(21 锁)随码退场;面册(adr0293)代登记条目移除(文法反向操作);strategy/README 终局意向行还原并留本 ADR 指针;
- 验证:邻锁(w611/w633/w917/w951/form_gates 等)+L1 快速集(2007P 基线)+ruff 全绿。

## 复活条件(Revival)

重启本机制须依次满足:
1. **先解信号层失效记忆问题**(前置硬门):同线豁免让已判死原线被自家③信号复活(33 例降级中 12 例次帧回锁)——需在信号层/豁免语义上裁决「失效假设的记忆与排除」(如冷却对同线豁免路径同样生效,或失效期内信号过滤),未解前任何方向侧改判机制(含 P1 pair 假设生命周期)在信号高频域结构性失效;
2. 重推触发面:sim 中**真实信号占满 weak 帧**,「无信号才升格」的派生通道无 firing surface——重启形态应为「失效评估优先于信号解析」或在信号解析层加失效过滤,而非独立派生通道;
3. 重新回答 G2:方向改判对 P2 存活的杠杆未经证实(sim 三臂持平)——重启前先在 replay/实机数据证实「换到更强线」的局确实活得久(支B 归因再下钻),否则属杠杆错配;
4. P1 侧命题(pair 假设生命周期,独立小批)不受本判负牵连,但其设计必须引用复活条件 1(同一信号层冲突同样卡它)。

## 边界(Constraints)

不动:门闩语义(w665)/P3 demoted_endgame 与强制锁线/演进保护组(ADR-0360/0363/0371/0382)/出口①阈值(ADR-0436)/form_score 纯观测口径(ADR-0353)/P1 过渡对(ADR-0357)/任何支出数值(P36 辖域,DESIGN §2.6)。
