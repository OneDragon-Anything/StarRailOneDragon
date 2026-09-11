# ADR-0611: T-165 振荡回归热修——同轮买卖互斥统一闩(L1 买后禁卖/L2 卖后禁买/L3 豁免分键结构化)

- 状态:已实施(落地审需修收口项 F1/F2/F3 闭环;commit 候编排者统一门)
- 关联:ADR-0267(r408 同轮买卖互斥本体,0 容忍)、ADR-0328(v2_round_sold 对称臂)、ADR-0585(P78 卖出仲裁/装配 A/LAUNCH_CAUSE_BY_ARM 登记闭集)、ADR-0530(cw4_swap_fresh_buys 载体,L1 读源宿主)、ADR-0591 §4(line_switch_collapse 证明打标制,L3 孤儿键归属依据)、ADR-0593(T-153 自算复核,转化分键线成员复核语义来源)、ADR-0604 §3-5(档 2 轮内新鲜度排除=L2 既有单一源;§3-5 扩域候观测键判读=C6 分键显影义务)、math_proofs P78(INV/P78-1 同 visit 抵消/P78-2 τ 分类/P78-5′ 四关系表)/P76 甲(1★ 往返净损 0)/P24(残余补部署支配定理,B4 锚正)、口述 [41](死金禁囤消费侧/资产形态)
- 方案正本:`.debug/temp/currency_war/attacks/t165_leak_ladder/振荡回归修复方案.md`(v2,按方案对抗审 17 项[A1-A5 阻断 5/B1-B5 重要 5/C1-C7 轻项 7]全量差分修订;本 ADR = 其落码批持久归档载体,代码注释引注一律指本 ADR)
- 权威链:方案对抗审 17 项全闭合(A1-A5 修改后放行,编排者逐条裁决免完整重审);落地审 3 项(F1 本 ADR+引注持久化/F2 臂计数勘误/F3 判读留痕落痕档)处置见 §5;判读数据留痕 = `.debug/temp/currency_war/attacks/t165_leak_ladder/判读留痕.md`(易失判读档,持久结论以本 ADR §5 为准)

## 1. 背景与病理(归层:策略执行层·买卖通道守卫记忆缺失)

双批 sim 复测(n300 seeds 300-599:103 条违例/80 局;r2 seeds 600-899:114 条/94 局)同轮互斥 0 容忍破面:同轮「卖 X 腾位 → 买回 X → 再卖 X」净零泵(热点 r6/r9,席满放大窗口);s313 逐帧复现 r1 卖黑塔→压金买回→再卖。根 = r408 双轮键事实集(v2_round_bought/v2_round_sold)迁移 mandate_v1 栈时被拆为覆盖依赖型机制:「买后禁卖」半边只剩 press 类窗口段登记面(hold 资格拒收/合并捷径两形态裸奔),「卖后禁买」读端只接 M6 一臂;检查器转化类豁免分键因发射位填充拆除而恒不触发(双批违例混有假阳)。恢复 r408 不变量 = 该层根治(症状面补丁候选见 §2)。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| L1 读源 = 登记簿读面扩全因类 | ✗ | 登记簿有两裸奔形态不可救:hold 类资格断言拒收不落账(买入照常发射,W5 在册语义)、合并捷径分支在登记前 return;kernel `cw4_swap_fresh_buys` 每笔买入无条件写入且先于捷径分支,三形态天然覆盖(方案对抗审 A2/A3 定谳) |
| L1 读源 = `fresh_buys_of`(kernel 单一载体) | ✓ | 零新载体零补丁;代价 = 含 sim 作废意图的过度排除(方向安全,SWAP_FRESH_BUYS_ATTR 载体注释在案自申报);登记簿退守因类账本 + T3 defer 视图本职 |
| 垫保(stall_protect)并入 L1 硬面 | ✗ | 杀死 T3 末位牺牲转化类放行 = P78-5′ 在册语义破面,与方案自身边界表矛盾(对抗审 A1);语义改判须独立对抗审,不夹带 |
| 换线孤儿清算纳入 L1 硬面 | ✗ | 线账闭合 = P78-2a 账闭合事件,孤儿清算 = 豁免语境(ADR-0591 §4 证明打标制);双批复测全部同轮买→卖对(5/6/9/9 例)恰为此形态,carve 为在野承重件非死代码 |
| L2 形态 = 臂表逐臂手搓排除 | 部分 | 判据 helper 单一(sold_this_round 薄封装),但候选枚举位分散;落码 = 新建统一过滤位(帧级名集 + `_buy_view` 逐臂视图 + `_shop_candidates` 名查过滤),分键显影随行(对抗审 B3 如实申报:非复用既有 helper,系消费结构新建) |
| 未映射臂维持静默跳过登记 | ✗ | 新臂忘配映射即绕过登记与一切以字典为臂全集的穷举断言(对抗审 A4:字典已 14 键而文本多处写 12/13,人工纪律已在漂);改抛错把静默裸奔变硬闸,此后穷举断言地基为真 |
| line_switch_collapse 迁入 convert_reason / 两键并读 | ✗ | 孤儿证明打标语义与豁免资格耦合(ADR-0591 §4 防窗口段回归洗白),不迁;检查器按键分工判定(转化读 convert_reason/孤儿读 reason),迁移期不并读零双源(对抗审 C3) |
| dominance 买回豁免 | ✗ | P78-1 同 visit 卖出定义性抵消买入(净效果 0 剩动作噪声)+ P76 甲 1★ 往返净损 0 + [41];三笔真实成本(XP 白拿 seed4 单 seed 38 次白拿 152 XP/席位翻转/引擎种子归零条件性);press 同轮不豁免系重申在册语义非新裁决(对抗审 B4) |
| 复测批 ② 用 seeds 600-899 | ✗ | 与 r2 批撞车(对抗审 A5);改 900-1199 保持独立批,同池配对角色由 ①(300-599 复跑)承担 |

## 3. 已实施架构

1. **L1 同轮硬面(买后禁卖;装配 A 第 2′ 段)**:`sell_exclusions` 并集 `fresh_buys_sell_face(session)`(kernel cw_deploy_logic;单记录键式 {phase: (plane, round_num), names},全因类完备)减两个 carve-out——①垫保:`stall_protect_active` 登记活跃名从硬面剔除(继续走 defer 通道:凑息绝对跳过/M4·funding 降序放行);②换线孤儿:`line_switch_orphans_of`(义务镜像簿 ∧ 登记轮==当前轮 ∧ 名已出基座,线账闭合豁免语境,检查器 line_switch_collapse 分支兜住)。硬面 = {obligation, hold, press} 效果面,通道无关。
2. **读端自治 fail-closed(C2;对 V2-09 的显式翻转)**:相位 (plane, round_num) 从 session 黑板帧自行解析(last_state 优先——生产 prep/shop 逐帧写点;shop_state_frame 兜底——sim/replay 驱动器),不消费 `current_round` 形参(None 漏接线帧不再静默放行,v1 缺口 C 结构性闭合);三分支:相位匹配 → 名集/相位失配 → 空集(轮界自动过期,零销账)/帧全缺 → 排除当前记录 names 全集(单记录载体,历史轮不泄入,过度排除上界单轮,方向安全)。垫保 carve 在轮号不可得帧不剔除(硬面保持全集)。
3. **L2 卖后禁买全臂(档 2 新鲜度排除扩域)**:单一事实源 = `cw4_round_sold_names`(ADR-0604 §3-5 载体,写端 = 各卖出发射位 `_note_sell`/`record_round_sold` 收口,零新载体);统一过滤位 = 帧级名集 + `_buy_view(arm)` 逐臂视图 + `_shop_candidates(m, arm)` 名查过滤,12 过滤位收口全部 14 映射键(ev_buy 经 slot_idx 解析点过滤);逐臂分键 `<arm>_round_sold_excluded`(M6 既有键名零断链,ADR-0604 §3-5 扩域候观测键载体)。行为变更申报(B2①):同轮孤儿清算卖后 dominance 买回孤儿名被禁 = 意图内(泵形态)。
4. **A4 硬闸 + 穷举断言地基**:`_emit_buy` 对未映射 reason 抛 ValueError(静默跳过登记分支 = 绕过登记与穷举断言的地基为假);双锁 = LAUNCH_CAUSE_BY_ARM 精确 14 键断言 + shop 发射位 reason 字面量源扫描 ⊆ 字典;臂计数对现值校正 12/13 → 14(方案对抗审 A4③/C7)。
5. **L3 豁免分键结构化**:`SellBench.convert_reason: str = ''`,值域 = 三放行键 ⊂ SELL_BENCH_CONVERT_REASONS 闭集(fuel_victim_protect_demoted / funding_support_stall_convert / funding_hold_liquidated),恰 4 发射位填充(全 shop 域账本动作: M4 腾席/m2_stockpile 腾席腿/funding 被保垫件/funding 兜底);`line_switch_collapse` 留在 reason(证明打标不迁);检查器(check_no_same_round_buy_sell/check_oscillation_xp_cap/D1 复盘面)按键分工:转化类读 convert_reason、孤儿读 sell_reason ∈ SELL_BENCH_REASONS,线成员复核(T-153)语义原样平移;'' 恒不豁免(0 容忍保持);reason 载体上的转化值不再豁免(旧通道值不放大豁免面)。
6. **账本转录面(C4)**:sim 引擎 SellBench 行补 `convert_reason` 键转录(生产 serialize_action 字段平铺自动随行);旧读端 .get 容忍,加法增益零判定面。
7. **义务镜像簿载体定谳(孤儿 carve 的证据面)**:登记簿不可作「曾义务」证据——装配 A 身份段的换线闭合读点(`_close_switched_obligations`)就地销账义务类登记,同帧更早的 A 读点(帧首投影)触发销账后迟到读登记簿必扑空;义务买入镜像簿(scratch `shop_obligation_buy_rounds` 轮戳,shop `_emit_buy` 义务落账同步写)跨销账存活。簿键/读口(`obligation_book_of`)/证明集(`line_switch_orphans_of`)自 shop.py 上移 sell_gate 单一源(原 T-141「回迁候 sell_gate 开放批」申报兑现),shop 侧薄委托零断链;写点条件 = 登记落账 ∧ obligation ∧ 名非空(义务类无资格断言恒落账,簿 ≡ 登记簿义务类视图)。
8. **B4 机械件**:dominance_buy_eligible docstring 论证锚换写([41] + P76 甲 + P78-1;P24 本体 = 残余补部署支配定理,无买入/持有期权命题,前版注 P24 系锚错位误注已正),shop dominance 循环注释同修——纯注释零行为。

## 4. 申报与边界(方案 v2 §6 清偿)

- **B2② P60 换手写端缺口承重声明**:「同轮换线换手买回」合法形态目前靠 entry 域 funding 兜底/line_switch 卖出**不入 `cw4_round_sold_names`** 的写端缺口存活(ADR-0604 §3-5 覆盖面申报);L2 全臂读后该缺口从「留观测」变为**承重结构**——未来任何「补全写端」批必须同场处置该形态(按卖出语境过滤入集),禁静默杀死换手。
- **L1/L2 权威序**:决策读 = 发射侧(mandate 域 `cw4_round_sold_names`/fresh_buys),执行落地 = kernel 侧 `v2_round_sold` 幂等加固(cw_round_ledger);行为判据 = 发射侧,对账/回放 = kernel 侧;两侧不合一声报(零代价合一前提未成立)。
- **line_switch 通道 carve-out(B1)**:SELL_CHANNELS 五通道中 line_switch 无装配 A 消费位(victim 池自定义旧线成员),孤儿清算卖不经 L1/L2 硬面;换线塌缩候选域结构自限(struct_self_limit,矩阵格在册)。
- **sim 写点双位申报(既有,非本批引入)**:生产写点 = shop `_emit_buy` 发射位;sim 引擎执行位自带 record_fresh_buy(engine_p1,SIM 执行语义)——方案 v2 §2.2-5 在案。
- **P4 相邻轮种子回卖**(上轮末买→本轮首卖):同族第二形态,独立候批,本批不辖。
- **未验项如实申报**:[13] 停手纪律计数与泄金次数分键无导出基线可对照(会话计数器不入 decisions 账本、基线原始遥测超保留窗);[28] 出口金≥50 已亲验保全(299-300/300)。

## 5. 落地审处置与验证

- **落地审结论:代码/测试/数据三面零阻断;需修收口面三项**——F1(本 ADR 立档 + 全仓 T-165 方案/方案审易失引注 ADR-NN 化,逐处判读禁盲替;其他批次历史引注不属本批不动)/F2(sell_gate 字典头注臂计数 12→14 一行勘误)/F3(判读留痕落盘:六变异红对全列/四批复测归零数字/B5 交叉分键/保全线判读/replay-diff 结论,标来源=落地审报告),全部闭环于本 ADR 落档时。
- **验证面(落地审亲验复核)**:七测试文件 181 用例全绿;六变异红对在案(判读留痕档全列;落地审抽复演 MUT1 补位确认);四批复测 no_same_round/oscillation_xp_cap 双零(300-599 复跑/600-899 配对×2/900-1199 独立批,同池指纹 0e091d4d);独立复扫全部同轮买→卖对(5/6/9/9 例)100% 为孤儿豁免语境、零真互斥;保全线 8 项判读(出口金/[28]/出口 hp/形态凑齐率 −2pp 种子噪声带/boss 胜率略升/degrade 27 与 37 局噪声带/osc 共现→不可判读合规/同池指纹一致)带内;变异打红的 sim 复发半边如实申报(MUT1 下 sim 引擎自有写点使 sim 不复发,生产写点唯一性不受影响)。
- **观察项(不阻断,留观)**:convert_reason 在 4×300 复测局零触发(转化类形态在 L1/L2 下罕见,豁免面活性由单帧锁承载);form_ok 268/300 vs 基线 274/300(同 seed,−2pp 在已立案口径污染与种子噪声带内);entry 域 funding 卖位无 convert_reason 填充(同轮边界理论可达性未证伪,4×1200 局实证零触发);`_autonomous_round` 与 `fresh_buys_sell_face` 在 frame.round_num=None 防御位理论不一致(生产帧恒有轮号,无行为面)。
- **P4 相邻轮种子回卖**:同族第二形态,独立候批挂账(§4)。
