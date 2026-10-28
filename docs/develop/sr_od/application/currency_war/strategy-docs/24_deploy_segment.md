# 24 部署执行段策略面(deploy segment)

> 定位 = **备战画面内部署执行段**(无独立 screen_info 建档画面):部署 = 备战决策环动作——`CwActionDeployMoveParam` 原子序由策略层动作发出点逐帧现算,经 `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp` 机械拖拽在货币战争-备战上执行(部署机画面 op 已停用删除);未达上限确认弹窗(货币战争-未达上限警告)由流程层推进;**能力面** = [../screens/README.md](../screens/README.md) §5.4。本篇 = 该段的**策略面**:思路概述 + 动作清单 + 形式判据指针。
> **单一源** = 该信息的唯一权威出处;**帧** = 一次截取游戏画面并做一次决策的时点;**对账** = 预期记账状态与画面实际读数的比对核验;**两套并行意向** = 过渡配方与终局阵容两套意向并行(代码字段 `ist.p1_pair`);**被换下单位(victim)** = 换人时被卖出腾位的上阵单位;**数字来源标注(四种)**:【注】游戏定义值 /【推】已证推导 /【拟】观测估计 /【拍】用户立场登记值。
> 判据权威定义引用不重复:部署与站位判据 = [10_prep_decisions.md](10_prep_decisions.md) §1;换人卖出的骨架侧语义 = [02_mandate_layer.md](02_mandate_layer.md) §7(sell 行,M4 姊妹出口)。数值单一源在代码。

## 1. 策略思路/算法概述

- **选人围栏**:部署候选受围栏约束——引擎/配方体系件围栏 `DEPLOY_FENCE`(单一源 = `kernel/cw_launch_admission.py::DEPLOY_FENCE`,RECIPE ∪ ENGINE)与上阵资格(`cw_launch_admission.py::offtarget_sell_allowed`);排路由/槽位选择单一源 = 策略层 `mandate_v1/deploy_plan.py`(排 = `deploy_row_pref` 三级:阵容站位覆盖 > 注册表 position_pref 派生 > back 兜底,前排保证随迁;槽位 = `deploy_slot_plans` 按容器行列现值自定,后排上限 = `back_layout` 现值);后排布局选档单一入口 = `obs/cw_back_layout.py::select_back_layout`。
- **判据必需件首桶序**:选人序以目标阵容的 `required_deployed` 成员为第一优先桶(在用两实例 = 希儿系 pair 的 `pair_target_comp` 与静态套「希儿量子」;装配单一源 = `mandate_v1/deploy_plan.py::_deploy_plan_inputs`(动作发出点/出战链共用)与 kernel `assemble_swap_plan_inputs`(换人计划),消费 = `select_deployments` `required_names` 参)。依据 = 判据必要条件的支配论证:该件不在板该体系永远无法成型(希儿系判据的「希儿在板」合取支,`Comp.required_deployed` 字段契约),cap 竞争时空位让给普通成员 = 弱占优劣化;空集缺省 = 序逐位同旧(未接线消费面零漂移)。职责边界:只判断「能不能上一个人」的预检函数(shop 的 `can_deploy_single`、`cw_launch_admission.has_deployable`)不接收这份优先序参数——它们只判单一候选可上阵,与排序无关;边界申报见 `select_deployments` 注(策略层单一源)。
- **换人卖出**:非目标阵容的上阵件挡目标成员上场时先卖腾位,被换下单位(victim)资格单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(义务集 ∪ 新鲜度排除 ∪ 资格族,内按域分派);部署面换人是 M4 之外的姊妹卖出出口(`02_mandate_layer.md` §7)。换人判据全貌(域切分/双门四条分支/让位白名单/组贪心/守恒域切分/执行形态/放行/收敛不变式)= 本文 §1.1,已知边界与豁免清单 = 本文 §1.2。替补受上阵窗口辖域辖(窗口辖域定义 = [22_prep_screen.md](22_prep_screen.md) §1 第 6 步,数据载体 = 知识卡 `entry_signals`;锁定帧窗口谓词结构性恒 False,凡锁定帧替补均可上——两条分支豁免覆盖全件,窗口辖域篇同条)。
- **补齐语义**:残余补部署 P24(空槽上任意围栏认可件零支出严格优先,`../proofs/p24-residual-fill-dominance.md`);放行条件纪律 = 计划空是合法稳态,发出方与执行方用同一谓词判空、为空就不发出动作(`10_prep_decisions.md` §1)。

### 1.1 转型域换人判据(双门,as-built 总源)

> **转型域** = 终局阵容已锁定(锁定线槽 `locked_comp` 非空)的换人域;**双轨域** = 位面 1 过渡配方与终局阵容两套并行意向(`ist.p1_pair` 非空,配方对锁)的换人域,板面义务本体 = 过渡配方(cw_recipe 模块不变量)。**门 1(收益门)** = 换入组必须带来结构收益;**门 2(安全门)** = 被换件资格逐件裁定。单一源 = `kernel/cw_deploy_logic.py`(判据全部驻 kernel,策略语义经 ports 注入)。

- **域判别子(三合取,单一源 = `swap_bond_gate_domain_of`/`swap_bond_gate_domain`)**:①终局阵容锁定(判定权威 = `ist.locked_comp` 非空;显式排除配方对锁分支——`committed_authority` 全值含配方对锁分支②,在配方锁帧也为真,不可作本判别子,[12_line_and_intention.md](12_line_and_intention.md) §2)∧ ②板满(换人只在板满帧发,不继承则与 M1 直上通道抢活白卖)∧ ③成型度 < 1.00(成型帧不进换人域;成型度缺读 = 域外 fail-closed)。未锁帧/配方对锁帧/成型帧/板不满帧恒域外。判别子无位面门:配方完成后位面 1 的板满帧同样进转型域(后果申报 = §1.2 ④)。消费面 = `swap_sell_exclusion_reason`(资格域分流)/`select_swap_plan`(计划域分流)/`assemble_swap_plan_inputs`(域字段装配)/`mandate_v1/shop.py` 买侧收窄谓词源(`swap_transition_narrow_frame` 挂同一谓词全合取:分支① ∧ 板满 ∧ 成型度<1.00)——判定只此一份,禁消费位自写第二份合取。
- **门 1(收益门,四条分支任一命中即放行,对组换后板态判定,单一源 = `swap_bond_gate_benefit`;归因检查序钉死 ④→①→②→③,分键 = 首达分支)**:
  1. **成品分支(④)**:组换后成型判据达成(成型度 ✗→✓;折法单一源 = `cw_comps.form_progress`,含 OR 组承接/required 分支,与完成品分支单点门同函数);
  2. **新档位分支(①)**:激活终局羁绊新档位——档位梯逐档计数,档位语义源 = `data/cw_factions.py` 档位表(`Comp.form_tiers` 是单阈值成型判据与键集来源,不是档位梯子);
  3. **支撑数分支(②)**:支撑件数严格增——支撑件 = 终局名单成员(`k_members` = core ∪ shared,单一源 = `predicates.line_members`)∪ 羁绊标签命中终局键集的外部件(按标签计入);名单成员无条件计入。终局键集 = `bond_gate_keys` = `Comp.form_tiers` 键。
  4. **同名升星分支(③)**:换入件与被换件**同名**(必要条件——异名星级升换属横换终局件形态,无结构收益,拒)∧ 换入件星级严格升。
  门 1 判定的羁绊范围 = 终局键集,不含其他羁绊;双轨域无门 1。
- **门 2(安全门,逐被换件)**:义务集 ∪ 新鲜度排除(轮内买入)∪ 资格族(`merge_material_guard` 素材守卫/`star_guard`/`fp_unreadable` 等拒因保留;`fenced_arm_closed` = fenced 关门分支拒因,保留)。**义务集路径域豁免(转型域)**:`locked_buy_membership` 拒卖分支在换人让位路径整体豁免——让位白名单全部三通道的 victim 均豁免义务集拒(按通道枚举豁免会使名单成员让位通道不可达,故裁路径域豁免;豁免依据 = 门 1 四条分支各自蕴含的组级净非降承接义务集保护意图,`proofs/math_proofs.md` P98);来金/演进/普通卖出通道的义务集拒不豁免。
- **让位白名单(`target_keep` 口径收窄,转型域)**:身份保护面 = 终局名单成员 ∪ 保护集 ∪ 替班契约件(替班=不卖契约照旧,替班件不因白名单沦为 victim)。victim 合法性白名单:①**纯过渡件**(终局键集零标签命中)= 一级 victim;②**终局标签支撑件**(非名单,标签命中,如停云类)= 二级 victim;③**名单成员仅两通道**——(a) 同名升星横换(门 1③),(b) 分支 hold 让位(必需件/成品换入的现行让位检验 `_swap_victim_yields_for_swap_in` 通过,含量席让位现行语义)。非名单标签件不再被阵营视图恒拒;双轨域 `target_keep` 口径不动。
- **组贪心(最小充分组;宿主 = kernel `select_swap_plan` 多对组计划形态,序参数 = 策略层 `deploy_plan.build_swap_group_order` ports 注入,换策略换序宿主不动)**:
  - **换入候选序(主循环)** = 名单成员先(星级降序,并列 tie-break = 名单注册序——core+shared 拼接序)→ 外部支撑件(星级降序,并列 tie-break = 标签命中数降序 → 注册表序);
  - **victim 序(两级 + 名单末位桶)** = 一级(纯过渡件)→ 二级(终局标签支撑件)→ 名单末位桶(名单成员;桶内 3(a) 同名升星对优先 → 3(b) 分支 hold 通过序);各级层内序 = 现行机器 victim 序(档边际贡献升序 → 1★ 优先桶式星级 → 板槽位序),度量域显式钉死 = `comp.all_factions` **全量并集** ∪ `SWAP_GUARD_SYSTEMS` 守恒体系(`swap_yield_contribution` 实现口径;按终局键集字面喂会使战技点类经 flex_factions 入域的件降档,锚帧算术依赖全量并集)——禁换第二度量;
  - **组生长语义** = 逐对追加成组,累积组门 1 失败 → 失败前缀保留继续生长(成品分支存在多对合取才达成的形态,只试单对不可达)直到门 1 通过或候选耗尽;守恒/收益判定点 = 累积组现算(部分组态只是搜索中间产物,组定稿才发射);
  - **组构造遍历序** = 换入主循环 × victim 内层循环;门 1 未中的试组不并入前缀(禁同 up 重复入组),内层 victim 耗尽才把本 up 的字典序指定对(victim 辅序首个过全部前置闸者)并入前缀、推进下一 up;**首个可行组即停** = 换入主序 × victim 辅序的字典序第一个可行组;全耗尽 = 本帧零动作(合法稳态,拒绝侧分键闭集 = `bond_gate_reject_novictim`/`bond_gate_conservation_reject`/`bond_gate_reject_nogain`)。配对可行性谓词限域①②级桶(名在板 ∧ 非保护 ∧ 过门 2;同名去重不适用于换人 victim——victim 本就是同名离场语义,同名升星情形可达);
  - **换入侧裁判权** = 贪心只产「谁进谁出」的组,换入部署仍逐对过现行全套上序裁判(围栏/成对/点火序/配方底线/同名去重,`select_deployments` 裁判域单一源不动);up 侧 target 视图 = **支撑件并集口径**(`support_view_char_is`:名单 ∪ 终局键集标签命中——纯名单口径会把外部凑档件换入组误拒;`target_view_char_is` 本体不动,另有双轨域消费位,两视图并存各有辖域禁交叉引用);计划发射不新增 admission 闸(现行三元为观测面,照常记录进遥测)。
- **守恒域切分**:转型域守恒 = **终局档位非降**(组换后板态口径,与门 1① 档位面同一函数 `swap_bond_gate_conservation`,禁第二实现;过渡体系不在本域守恒——过渡侧损失由 victim 序自然最小化,终局侧收益由门 1 保证【拍】);双轨域守恒 = `engines_guard`(`SWAP_GUARD_SYSTEMS` 四体系+护盾,victim 离场口径)原样。
- **双轨域现行机器(域外,逐位照旧)**:配方对锁帧走混轨机器——板满换入分支两条分支:①必需件分支(`required_deployed` 成员滞留,假想面板下成型判据仍满的目标板件让位)②配方完成件分支(`_completion_swap_ins` 单点门**判据域参数化**:双轨域 = 现行成型度 ✗→✓ 折法,转型域 = 门 1④ 同源折法,同一函数禁复制第二实现;桥池 pair required 恒空,完成件压席由本分支承接);保护域扩展集(shared ∪ 替班)不因两分支解除(P41② + 替班=不卖契约);混轨 locked 帧的收紧面照旧——不属于目标阵容也不在围栏白名单的上阵角色不再允许任意星级直接卖,只逐个按资格规则(保档位、只卖 1★、保合成素材)判定,卖 2★ 只走「演进降级换人」专用通道(该分支准入谓词维持混轨语义,与 fenced 关门分支域分支 `fenced_swap_gate_open` 同形并存);卖后上序须真含换入对象(required ∪ 完成件),否则计划拒(`post_sell_req_missing`)——判据必需件/完成件优先于非必需板件([31]③ 上场侧同构的必需件特化)。
- **执行形态(同帧逐对原子序)**:可行组按 sell→deploy 逐对推进;**发射面(bond_gate 臂)每个动作发出面只发首对** `CwActionSellDeployedParam`,换出空槽由下个决策环迭代的 M1 残余补部署(`deploy_plan_moves`,同一 `select_deployments` 裁判域)先行落位换入——对间序 sell→deploy 由「sell 仅板满帧发射」结构性保证(卖后板必不满,空槽落位后才可能再发 sell);承载 = 单动作决策环同一 visit 内多迭代原地续跑(零重观察、逻辑态续算)。**中途失败语义** = 首对解析失败(计划名与黑板失配)→ 帧内停发后续对(`bond_gate_pair_stall` 分键,零动作),已完成对保留;下帧换人机器对剩余组重新现算续发(计划无跨帧状态,每决策调用重装配,重算幂等);Deploy 拖拽物理失败 = 动作层零判效(帧内无失败信号面),由下一入口观察对账 + 重算闭合(帧内瞬态,存续期单帧)。**换入落位分叉观测** = 落位经 M1 裁判独立选人,组收益分支兑现但落位 up 可分叉于计划 up(计划无跨帧状态的语义内形态,组保真约束不存在)。
- **放行(发射帧复算统一门,单一源 = `mandate._bond_gate_recalc_allowed`)**:发射帧对现读板态按计划组重算门 1(门 2 已逐件过,本门不重复资格面),**门 1 现读通过即放行**——复算判据 = 现读通过,非「与生成时点结论一致」;现读板面与计划期快照分叉(合成/卖出介入等)→ 组按现读重评,不可行即计划撤(`bond_gate_recalc_withdraw` 分键,零动作)。双轨域放行门 = P79-3 三轴(`_redeploy_emission_allowed`)照旧不废弃(域切分申报 = §1.2 ①)。
- **收敛不变式**:换人触发有限、板上支撑数全局非降的承保前提 = 配对骨架(换入与 victim 严格 1:1、换入件全为支撑件)+ 门 1 四条分支结构量严格增——证明登记 = `proofs/math_proofs.md` **P98 行**(转型域换人收敛不变式,结构计数注记,零自由参数,非战力证明)。

### 1.2 换人域已知边界与豁免清单

1. **双轨域遗留缺陷(P79-3 轴①死形状)**:`_redeploy_emission_allowed` 轴①两分支(非空义务集分支/空集对锁期分支)读备战席条目顶层 `char_id`,而容器形备战席条目(`BenchSlot`)无该顶层字段(身份在条目 `unit` 内)→ 轴①恒空 → 双轨域(pair 帧,arm='transition')恒帧级 defer(`redeploy_cost_gate_defer`)。码点 = `mandate.py` `_redeploy_emission_allowed`(容器 P4 迁移遗留);转型域不经本门(bond_gate 臂走发射帧复算统一门),死形状依赖在转型域消除;双轨域保留面按零行为差纪律禁顺手修。
2. **卖出通道豁免(换人域卖出面的安全阀通道)**:①溢出自救(FACE_SELF_RESCUE 不经装配 A 身份段,bench 侧标签件仍可卖——经济安全阀);②funding_hold_fallback(P78-5 死锁帧兜底,与自救同类安全阀——标签件兼保护档持有件仍可经兜底在死锁帧卖出);③部署换人让位路径(义务集路径域豁免,§1.1 门 2)。
3. **cap_hold 截断泄露面**:义务基座按容量费用序截断(`locked_buy_cap_hold` 截断集 B′)可把非名单标签件裁出保护面;装配 A 身份段终局键集标签分支(集合单一源 = `terminal_key_label_hit_names`)闭合该泄露——全 FACE_REGULAR 卖出通道共用装配自动覆盖,bench 侧含内(万敌单C lv5 hoard 超容量帧实证形态)。
4. **平面 1 分叉后果声明**:转型域判别子无位面门——配方完成后位面 1 板满帧即进换人域,换人发射与锚帧 victim 实例随轨迹分叉(判据改的预期内行为面;机制由单帧测试钉定,逐帧轨迹差异按预测表对照归因,不作缺陷立案除非机制违背)。

## 2. 会执行的动作清单

| 动作 | 动作类型/op 载体 | 触发判据(指针) |
|---|---|---|
| 选人上阵 | `CwActionDeployMoveParam` 原子序(备战环决策发出,拖拽 = `cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`;部署机画面 op 已停用) | M1/M5 + 围栏 + `10_prep_decisions.md` §1(计划单一源 = `mandate_v1/deploy_plan.py::deploy_plan_moves`;围栏/底线门谓词 = `kernel/cw_deploy_logic.py`) |
| 换排 | `CwActionDeployMoveParam`(to_row 重拖,策略发出) | 同上(放对激活角色赋能;错排事实归备战环入口观察对账) |
| 换人卖出 | `CwActionSellDeployedParam`(`cw_sell_deployed_action.py`;判定单一源 = `swap_sell_exclusion_reason`) | 被换下单位资格 = `swap_sell_exclusion_reason`(义务集∪新鲜度排除∪资格族) |

## 3. 能力 vs 策略

部署执行段动作集与能力面同集(能力矩阵篇 §3.4);商店期「卖备战/买经验收缩至备战期」的旧判例已废止,不涉及本段动作面(见 [23_shop_screen.md](23_shop_screen.md) §3)。
