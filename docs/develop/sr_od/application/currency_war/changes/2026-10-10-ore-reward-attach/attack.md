# 晶矿奖励附着通道 设计对抗报告(第三轮·收敛确认)

第三轮审查:对照第二轮报告逐条核验整改条件闭合(R2-M1 三处 + R2-N1/N2/N3 + R2-N4 七小点);对本轮修订触碰段落(ore-reward-channel §4 步序 3/4、§5 全节;ore-sim-plane-start §1/§4;ore-click-consume §1;landing 三处)做交互快攻;跨文档同步(design.md §2 ↔ channel §5 ↔ landing 3.4)一致性核验。对照 = src 与 sr-od-test 现行代码。审查中 landing.md「通用工程门」经模板层修缮改名「完成前常规检查」(与本轮核验面无关),以当前文件为准。

## ① 结论

**通过(定稿)**。第二轮全部条件逐条闭合,每条均按代码实证复核为真:R2-M1 三处(次序句对齐 / `_prev_node_plane` 删除 / 事件② plane 源 + None 行为 + 生命周期句)全部落实;R2-N1 生成集语义按建议修法①收口且三方一致;R2-N2 先例换成真实直写先例且两先例代码核实属实;R2-N3 定量披露落地;R2-N4(a)-(g) 七小点逐条闭合。本轮修订触碰段落的交互快攻与跨文档同步核验**零新发现**——四阶段(3.1–3.4)全部可派工,实现者照文档开工无拍板空间。收尾动作:设计方将 README.md / design.md 状态行由「对抗审中」更新为定稿态(流程动作,非文档缺陷)。

## ② 第二轮条件闭合核验表

| 条目 | 判定 | 证据(修订稿 ↔ 代码) |
|---|---|---|
| R2-M1① 次序句与判定点句互斥 | **已闭合** | channel §5 事件①次序句改为「**次序硬约束 = 判定与入队完成先于同帧 spheres 写**——由『判定在锚定写之前』+ 现观察序『锚定写在前、spheres 写在后』共同保证」,原「夹在锚定写与 spheres 写之间」表述已除;与判定点句(「判定点 = 节点锚定写之前……比较 incoming vs 锚定前现值即可边沿检测」)方向一致、传导链自洽(判定在锚定前 ∧ 锚定写先于 spheres 写 ⇒ 入队先于 spheres 写);与 design §2 第 3 条(「在节点锚定写**前**读 plane 前值检测——入队必须先于同帧 spheres 写」)、landing 3.4 判据(「入队先于同帧 spheres 写」)三方一致。物理基础复核:cw_screen_prep.py 锚定写 :281-288(`observe_node_anchor`)先于 spheres 写 :384-391,「天然满足」成立 |
| R2-M1② `_prev_node_plane` 孤儿成员 | **已闭合** | 全迭代目录 grep:`_prev_node_plane` 仅存于本报告历史叙述,设计文档面零残留;前值载体段收窄为 `_prev_env: str` 单成员(用途 = 事件②快照对拍),并显式写明「**事件①不用快照**(锚定前现值即前值)」——两种机制各写一半的问题消除,无拍板空间 |
| R2-M1③ 事件② plane 源 + None 行为 + 生命周期句 | **已闭合** | §5 事件②:「判定点 = 锚定写之后、spheres 写之前(备战帧内,锚定已完成);**入队 plane 取值源 = 锚定现值 `gs.node.value.plane`**;`gs.node.value` 为 None(首锚定前,node 域不在开局种子表)→ 本帧不触发,由事件①在下一次锚定时兜住」。生命周期句已补:「`_prev_*` 成员每备战环重建(`_prev_spheres_raw` 同语义 = 环内连续帧,非跨环持久),事件②跨环重触发由幂等守卫吸收」——与 cw_screen_prep.py :191-195 现行注释语义逐句吻合。代码复核:种子表 :1983-2018 确无 gs.node(node None 分支的前提属实) |
| R2-N1 生成集语义与配对机制自相矛盾 | **已闭合**(采纳建议修法①) | channel §4 步序 4 改「**生成集 = 无附着的现役身份**(步序 3 重挂后,新值坐标中仍无 `ore_rewards` 键者——覆盖未配对新现、level 缺读跳过帧、恢复/竞态残留形态)」;level None →「该批身份仍无键,**下帧自动再进生成集**」——新语义下「下帧再试」真实成立(重挂只搬已有键,身份是否进生成集与配对结果解耦,无附着旧身份恒留生成集)。三方一致:①配对机制(步序 3 重挂 ⊕ 步序 4 键判据解耦);②click-consume §1 缺项定义(「挂接入口保证每现役身份有附着;写端竞态等罕见态」——机制与定义一致,缺项回归罕见态);③landing 3.1 判据(「生成集 = 无附着现役身份(含 level 缺读帧后自动补生成)」)。原矛盾场景(配对命中 = 永不进生成池)在新判据下不存在 |
| R2-N2 先例引用失实 | **已闭合** | channel §4 步序 4 声明消费写与 sim §1 声明入队写均改引「**依据 = kernel 确定效果直写 write_logic 先例(cw_exec_state 金腿 / cw_effect_inventory 退款腿)**」,`pending_item_grants` 旧引用已除;「不属 anchor_aware 族:该域无观察写端可锚定,声明是登记事实非观察投影」论证保留。两先例代码独立核实属实:cw_exec_state.py :71 `gs.write_logic(gs.gold, …)`(金腿,:58 docstring「经 logic_action 通道 write_logic」印证);cw_effect_inventory.py :864 `gs.write_logic(gs.gold, …+refund)`(退款腿)、:1231(宝箱腿)——均 kernel 确定效果直写,先例性质匹配 |
| R2-N3 误配定量披露缺失 | **已闭合** | §4 步序 3 补「**误配几何可达域定量**:同帧两矿圆心最小间距 = Hough `minDist=35`(cw_identity_obs `find_ore_sights`),跨帧各抖 ±12px 时异矿最窄 35−2×12 = **11px ≤ tol**,交叉配对几何可达;贪心最近在真对距离 < 交叉对距离时选真对,真对距离 = 抖差(常态 ≪ 11px),常态救回」。代码复核:minDist=35(cw_identity_obs.py :1561)、tol=12(:1434)属实,35−24=11 数值正确,「歧义可达」由定性变定量 |
| R2-N4(a) 配对距离度量未定 | **已闭合** | §4 步序 3:「配对门 = 双轴独立 ≤ `_SPHERE_PERSIST_POS_TOL`(12px……与 `filter_persistent_ores` 同语义)」+「**贪心排序键 = 欧氏标量距离**」——门(Chebyshev)与排序键(欧氏标量)分别定死。filter_persistent_ores 双轴独立语义复核属实(cw_identity_obs.py :1479-1480) |
| R2-N4(b) hook_sig 族两端不一致 | **已闭合** | §5 sig 形态段:「live 挂接与入队写 = logic_hook 族,group_id=`'prep:ore-channel'`,actor=`CwScreenPrep`;sim 挂接写 = `logic_sig('sim:ores')`(logic_action 族,sim 现行构造形态……)。参数名 `hook_sig` 泛指『挂接写用 sig』,**族差异即上述两端形态,不再另定**」——族差异显式注明,统一措辞收口。ChannelSig.group_id 字段复核属实(cw_game_state.py :401,自由串可构造) |
| R2-N4(c) sim 入队写 sig 未点名 | **已闭合** | sim §1:「写 = write_logic,**sig = `logic_sig('sim:env')`**(与 `discharge_due_item_grants` 同组同窗,沿 sim 现行 logic_action 族构造形态)」。代码复核:discharge_due_item_grants 现行调用确为 `sig=logic_sig('sim:env')`(cw_sim_backend.py :1364-1365),「同组同窗」引用准确 |
| R2-N4(d) sim §4 装配方增键无事可做 | **已闭合** | sim §4 改述:「键 `'ore_reward_gen'` 随 `action_sampling_rng('ore_reward_gen', None)` **首调自动生效**——装配方是泛型 `lambda tool`(cw_sim_backend 装配段),本阶段**零改动**」+「`test_cw_sim_seam.py` provider 装卸断言面扩 `'ore_reward_gen'` 键(现断言形态实存,沿其装卸用例扩)」。代码复核:装配方泛型属实(:1629 `lambda tool: stream_rng(...)`),装卸断言面实存(test_cw_sim_seam.py :208-222,装卸/复位/同 seed 确定性断言形态)——工作面错位已纠正 |
| R2-N4(e) landing 3.3 判据 12 在 sim 不可达 | **已闭合** | landing 3.3 判据改:「数值 = 6/8,sim 辖域 P1+P2 内实测;**12 由 3.1 生成函数单测覆盖**——sim 第一期 `plane>2` raise,位面 3 不可达」。代码复核:_node_ordinal 对 plane ∉ (1,2) raise ValueError(cw_sim_backend.py :1330),「位面 3 不可达」属实 |
| R2-N4(f) landing 3.4 测试文件未点名 | **已闭合** | landing 3.4 文件面点名:`sr-od-test/test/sr_od/application/currency_war/test_cw_prep_node_row_housekeeping.py`(备战观察链家计,挂接/入队接线断言落此)。文件存在复核属实 |
| R2-N4(g) reason 枚举漏 'no_intersection' | **已闭合** | click-consume §1 出参清单改:「其余(bench_full_no_open / ore_partial_open_skipped / spheres_unobserved / bench_unobserved / **no_intersection**(求交不动,现行为原样保留))不变」+ level_unread 退役已述(§1 与关键取舍节)。代码复核:现集恰 6 项(collect_ore.py :86/:89/:92/:104/:214/:216),5 保留项全列、退役项写明,枚举完整无漏项 |

## ③ 新发现

**无**。本轮修订触碰段落的交互快攻与跨文档同步核验均未发现 M 级及以上或备注级问题,核验覆盖面如下(零发现 = 已真核,非未查):

- **channel §4 步序 3(欧氏排序键 + 定量披露)**:与步序内配对门语义、§1 约束第三条(两帧持存 = 防幻检容差过滤器)无矛盾;
- **channel §4 步序 4(生成集新语义)**:与步序 3(重挂)、步序 5(消失清洗)、「点击未真开的回补形态」段(矿重现坐标无键 → 进生成集重掷)交互自洽;level None → 下帧自动再进生成集与判据自洽;
- **channel §5 全节**:前值载体(`_prev_env`,帧首读现值/帧尾写回,照 :199-203 先例)→ 事件①(锚定前判定,不用快照)→ 事件②(快照对拍,锚定后 spheres 前)→ 共用条件 → 过期(事件①同点触发清旧 plane)→ sig 两端——内部无矛盾;事件②环内首帧 `_prev_env` 未初始化(视同空)语义照 `_prev_spheres_raw` getattr 先例唯一可答,幂等守卫吸收跨环重触发;
- **sim §1 入队 sig(`sim:env`)与 §3 挂接 sig(`sim:ores`)**:两写两 sig 各自明确,与 channel §5「sim 挂接写 = logic_sig('sim:ores')」一致不混淆;
- **sim §4(装配方零改动)** 与 landing 3.3 范围「rng 键装配」/判据「掷序确定性」一致(装配语义 = 键首调自动生效,断言面扩键);
- **click-consume §1(reason 清单)** 与 §4(测试迁移「缺项∧level None 的 reason」)一致;
- **跨文档同步**:design §2 第 3 条 ↔ channel §5 ↔ landing 3.4(范围「锚定写前判定/帧边沿」+ 判据「入队先于同帧 spheres 写」)三方一致;landing 3.1 生成集判据 ↔ channel §4 步序 4 同步;
- **landing.md「通用工程门」→「完成前常规检查」改名**(第三轮审查中模板层修缮):首节单一定义(:3-9)+ 四阶段引用(:22/:35/:47/:61)一致,第二轮 M3 闭合语义维持,无新悬空引用;
- **既核依据行号抽样复核**:7 处 monkeypatch 行号(test_cw_collect_ore_rand.py :160/:186/:212/:237/:254/:280/:308)、快照 fields 自动枚举(cw_game_state.py :2687,新域自动进快照)、恢复表 rebuild 按字段名(:3878-3885,新域登记机制与先例吻合)、OreReward 全字段默认值(cw_ore_reward.py :52-62,`**v` 重建成立)、roll_ore_reward 错档 ValueError(:74-78)、ENV_ECONOMY 增发货币 (6,8,12)(cw_investments.py :1176,双源同值对照面)、`_window_begun_ord` 幂等守卫(:1332-1344)——全部属实。

## ④ 定稿试读结论

- **3.1(kernel 面):可开工**。域定义、种子与恢复登记、注册表三条校验、生成函数语义(含错档炸)、挂接入口步序(配对门/排序键/生成集/出队/消失清洗)、入队/过期函数——R2-M1①③ 与 R2-N1 收口后全部唯一可答。
- **3.2(点击兑现):可开工**。命中零掷、缺项兜底前缀、detach 写序、level 收窄、reason 通道语义完整(枚举闭环);7 处迁移面行号复核无误。
- **3.3(sim 接线):可开工**。分道 + 入队 sig、开局矿呈现与坐标续接、写端统一、装配方零改动 + 断言面扩键、占位退役、披露键;判据「6/8 + 12 单测覆盖」在辖域内可全验。
- **3.4(live 挂接):可开工**(R2-M1 三处闭合后解除阻塞)。前值载体 `_prev_env` 照 `_prev_spheres_raw` 先例、事件①锚定前判定 + 入队先于同帧 spheres 写、事件②边沿对拍 + plane 取值源 + None 兜底、sig 两端形态、`_prev_*` 环内生命周期与幂等守卫配合——接线规约作为「实现者照此开工」的操作文本语义闭合,无拍板空间。
- **总评**:三轮收敛完成——第一轮打回(P1+M1-M6+N1-N6)→ 第二轮有条件通过(R2-M1 整改 + R2-N1/N2 措辞 + R2-N3/N4 杂项)→ 本轮全部条件实证闭合、零新发现。核心结构(轨迹继承身份 + 单一挂接入口 + 双事件入队 + 生成集 = 无附着现役身份 + 直写先例引用)与五条用户裁定兼容,实现者照此开工。第二轮「附:核三(治本)评语」指出的模板层架构根(「§12」悬空 → 已由本目录 landing 首节定义 + 模板修缮改名落地缓解),框架侧 iteration-design.md 模板行诉求继续保留。
