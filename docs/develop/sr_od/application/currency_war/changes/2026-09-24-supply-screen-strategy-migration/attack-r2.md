# 设计对抗报告 R2(2026-09-24 补给屏策略迁移与选卡改形,第 2 轮)

> 审查对象 = 本目录 design.md / landing.md / README.md(草案态)。
> 判据源 = iteration-design.md §7 三核、strategy-work.md(§1 零调参/§3 证据档/§4 验证阶梯/§5 单帧锁/§6 对抗纪律)、宪法 00_framework.md/01_math_framework.md、math_proofs 索引(P40/P42/P81/P97 行)、项目 AGENTS.md。
> 纪律 = 数值/口径/引文/码点全部直调源文件复核(文中每个 文件:行号 均为审查时实读);篇内自洽与对齐宪法/游戏真值分开验;as-built 断言读代码体;结论只看证据。

## 发现清单

### 发现 1(高)凑星判据的 deployed 入参形状错配——按稿接线静默丢上阵行域,凭据⑦锁不住
- **位置**:design.md:58(§2.3);landing.md:12(凭据⑦)
- **发现**:§2.3 判据 = `same_star_count(char, 1, bench, deployed) == 2`,并写明「bench/deployed 入参 = `bench_units_of`/`deployed_rows_of` 读口产物」。实码:`deployed_rows_of(gs)` 返回 **`tuple[list[Unit], list[Unit]]` 行域二元组**(cw_game_state.py:3648-3654),而 `same_star_count` 的 `deployed` 形参期望**扁平的 Unit 条目可迭代**(cw_merge_simulate.py:424-433,遍历经 `_slots_iter` :110-119)。按稿直传二元组**不报错**:`_entry_identity` 对非容器形状 fail-closed 返 None 跳过(cw_merge_simulate.py:93-107)→ 上阵行域被**静默丢弃**,凑星计数只数备战席——「1 张备战席 + 1 张上阵」的真实可凑星帧被读成 1(不凑),tiebreak 错判且无任何异常暴露。同文件现役两账构造有展平先例可照(flow.py:729-731 `_wf, _wb = deployed_rows_of(...)` 后 `*_wf, *_wb` 拼接),§2.3 未给。验收凭据⑦只写「同名 1★ 恰 2 张时该角色候选先」,未钉 2 张**分跨 bench/deployed** 的构造——按错误接线写出的实现,若测试把 2 张都放备战席照样全绿。此为「值对标签错/漏拍即静默错误」重点错误类,与第 1 轮发现 2(高)同类。
- **修正方向**:§2.3 数据源规格补明「deployed = front_row + back_row 展平拼接(照 decide_box_card 两账构造 flow.py:729-731 的展平写法)」;凭据⑦的凑星帧构造补「1 张备战席 + 1 张上阵行域」分布形态,使锁对该错有判别力。

### 发现 2(中)§2.8「P2+ 未锁线帧为终局向假设」与方向机实态不符——装备级挂 `target_comp` 的取舍论证前提落空
- **位置**:design.md:101(§2.8)
- **发现**:§2.8 称 `target_comp`「P2+ 未锁线帧为终局向假设,装备级借此在锁线前保持终局向参考、与现役行为连续」。实码:`target_comp` 全 src **唯一写点** = flow.py:353(`_ms.target_comp = comp`),comp 取值 = `get_comp(ist.locked_comp)`(未锁恒 None,flow.py:326)+ P1 配方对物化(仅 plane==1,flow.py:335-352)。P2+ 未锁线帧(含 weak/撤销帧)`target_comp` = **None**(cw_intention.py:2021 在册注释自证「target_comp=None,准备域决策引擎无方向空转」;mandate.py:748「锁线帧恒置 target_comp = locked」);降格帧 locked_comp 被清(cw_intention.py:2076-2077)→ 亦 None。综合:装备级仅在锁线帧有 key 参考(= locked_comp 同一 comp),一切未锁线帧(未锁/P1/降格)均空转退化「钻或通用值」——「锁线前保持终局向参考」**不存在**,挂 `target_comp` 与挂 `locked_comp` 逐帧行为等价,§2.8 的分化理由不成立。按稿实现不会错(§2.2「None → 空序列」机械自洽),但该错误论断将随「判据语义 = §2.2-§2.5」进入 30 号稿正本,误导后续读者对未锁帧行为的预期。
- **修正方向**:§2.8 改写为实态口径:「target_comp 仅锁线帧非 None(= locked_comp 的 comp);未锁线帧(P2+ 未锁/P1/降格)恒 None → key_equips 空序列,装备级空转;挂 target_comp 与挂 locked_comp 行为等价,取 target_comp = 与现役接线(flow.py:549)同源、免二次解析」;或直接改挂 locked_comp 并删去失实理由。

### 发现 3(中)`supply.decide` 签名中的 `config` 参数无任何语义定义
- **位置**:design.md:42(§2.2 决策函数签名)
- **发现**:签名含 `config`,但 §2.2-§2.5 全文未定义 decide 消费 config 的什么:三级判据/凑星 tiebreak/刷新判据均为零参数结构,无 config 消费点。对照所引先例 `invest_env.decide` 的 config 有实义消费(用户转向轴 `env_priority`/`env_forbid`,invest_env.py:379-380)。「纯值出口照 invest_env.decide 形」不能推出「config 留空」——实现者面对该参数只有两个未经设计裁定的选项:留一个死参数(违反接口最小化),或自行删参(撞停手令:自行拍板 = 绕过审查语境做设计决策)。iteration-design 硬规则 2 卡点:「实现者遇到的每个语义选择都能在设计或其引用的权威源里找到答案」。
- **修正方向**:签名删去 config;或显式声明「预留用户偏好轴(如装备禁选)扩展位,本批零消费」,并说明预留理由。

### 发现 4(低)§2.3 引用锚偏移两处
- **位置**:design.md:58(§2.3)
- **发现**:①`gs.board` 锚引 `cw_game_state.py:2123`,实码 `board: Field[dict[str, int]]`(上阵羁绊计数)在 **:2124**(grep 单命中;:2123 = `active_strategies`)——第 1 轮发现 1 修正时随攻击文本带入的差一行锚未复核;②`same_star_count` 锚引 `cw_merge_simulate.py:425-435`,实际函数域 **:424-433**(425-435 尾部含两空行与下一函数声明行)。值对标签错的锚点漂移形态(iteration-design 硬规则 4 卡点:逐一核设计引用的每个符号)。
- **修正方向**:锚改 :2124 与 :424-433。

### 发现 5(低)§2.7 对 16 号稿 :74 的清理指引「`cw_events.py:293` 机器随批删除」表述误导
- **位置**:design.md:96(§2.7 16 号稿行)
- **发现**:16 号稿 :74 行内引用 `cw_events.py:293` 为死引用属实——但该锚现址是 **augment 定义型注释**(decide_event 域,cw_events.py:293,本批不涉及);其所指 `_EQUIP_VALUE` 表本体早在 armory-box-value 批已迁 `cw_equip_value.EQUIP_GENERIC_VALUE`(cw_events.py:609-612 只余委托壳),且本批**显式保留** `_equip_value`(:609-612,planner :786 消费,§2.6 自申报)。随本批删除的是 decide_supply 内联评分形态(+10 + key_fit 隶属判据),不是「cw_events.py:293 的机器」;通用价值表机器保留且仍是在册待迁内容。「机器随批删除」按字面读与 §2.6 的保留申报冲突,且未给 3.3 实现者可写入 16 号稿的替锚。
- **修正方向**:改写为「锚 :293 已死(表本体已迁 `cw_equip_value`,现址为无关 augment 注释);行述 decide_supply 评分形态(+10/key_fit)随本批删除;通用价值表机器保留(`cw_equip_value` 表 + `cw_events._equip_value` :609-612 壳,宪法五在册待迁)」,给销账行以明确替锚。

### 发现 6(低)空候选帧行为未定义
- **位置**:design.md:42-44(§2.2 签名)、design.md:60-65(§2.4)
- **发现**:旧 `decide_supply` 定义了空候选帧分支(`not options → SupplyPick(idx=0,'no-options')`,cw_events.py:627-628);同构先例 `invest_env.decide` 亦显式定义(「空候选帧(观察层失约形态)…镜像防炸」,invest_env.py:381-384)。新 `decide` 对 `options == []` 的产出无规定。现役画面 op 只在 opts 非空时调 decide(cw_screen_supply_node.py:264),但 flow 直调面(测试、§2.5「sim 复用预留」)可达空帧,实现者需自行择一(镜像 invest_env / 前置条件声明),属未回答的语义选择。
- **修正方向**:补一句「空候选帧照 invest_env 空帧分支镜像:`Decision(idx=0, 'empty-frame')`」,或显式声明 decide 前置条件 = 非空候选、由调用方(op 的 opts 判空)保证。

### 发现 7(低)删除面枚举漏 `test_cw_unified_action_4.py:303` 的 SupplyPick 构造点
- **位置**:design.md:34(§2.1)、design.md:77(§2.6 测试面)、landing.md:17(3.2 文件面)
- **发现**:design/landing 均只点名 `test_cw_unified_action_4.py:27-33` 的 SupplyPick **类型 import**;该文件 :303 还有 `CwActionPickSupplyOp(env.op.ctx, SupplyPick(idx=0), env=env)` 的**实例构造点**(作 op 参数),SupplyPick 物理删除后该行 NameError。landing 3.2 文件面泛称「sr-od-test/ 内引用被删符号的旧锁」可兜住,但两份文档的点名面均不完整——「已知点全列」的申报口径自相不齐。
- **修正方向**:design §2.6 / landing 3.2 点名补 :303(随旧锁处置:换 `CwActionPickSupplyParam` 或按锁纪律改写/删除,处置理由随锁)。

## 已核对无误的面(抽样列举,均直调复核)

- **码点引用**:cw_events.py:583(段头注释)/:585-596(SupplyOption)/:599-605(SupplyPick)/:609-612(`_equip_value`)/:616-647(decide_supply,只消费 equip/has_diamond,char 全程未触 ✓)/:633-635(无钻必刷)/:1003/:1007(EventPick 登记面与联合)/:786(`_equip_value` 的 planner 装备档回落消费,且为保留后唯一消费点)/:1(模块 docstring 补给句);cw_equip_value.py:36(「V4.4 meta 先验;实玩校准」表自注)/:163-189(equip_tier 档位语义、需求按计数、key 可含重复)/:1 模块头(「禁第二套」裁定 5/6);cw_survey19_hooks.py:46-56(三支语义)/:1-8(P8 句),全仓消费面 = src 唯一 import 点 cw_events.py:552-554 只取 `encounter_tier_score` + sr-od-test 零消费 ✓;cw_node_obs.py:21(SupplyOption import)/:206(「建模残缺」)/:215(三钻集合);cw_comps.py:102(core_chars)/:111(shared_chars)/:112(transition_chars 未入名单);cw_game_state.py:210(supply 域版本 2)/:113(TYPE_CHECKING);cw_intention.py:197(locked_comp 套名)/:1123-1194(pair_target_comp 伪 comp,key_equips 缺省恒空 ✓);cw_action_report/pick_supply.py:48-50(入席恒 1★ 先验);flow.py:327(P1 锁帧 locked_comp 恒空注)/:516-518(ist 两参先例)/:545-546(refresh_used 预计算)/:712-718(get_comp 失败回落先例)/:719-740(两账构造先例);invest_env.py:388-401(次数闸 None fail-closed 先例);mandate_state.py:73;cw_sim_backend.py:78/:573-585(占位分布:char 恒空 + diamond_slot 每帧恰一带钻);cw_vocab.py:729/:917;cw_pick_supply_action.py:37(路径 operations/cw_op/ 属实);cw_screen_supply_node.py:8-14/:242-245(旧评分叙述)/:264(opts 空不调 decide)/:275-292(重调路径);sim_backend_runner.py:314-381(真 CwLoop + 真 mandate_v1 装配)。
- **机制语义推演**:闸内嵌 decide 后 op 重调路径仅剩「锚点缺失」触发面(推演核对 :274-292:pick=Suggestion ⟹ left≥1 ⟹ 拒绝条件只剩 `_refresh_point is None`,同帧同容器无分叉)✓;equip_tier 需求计数下「已持够数重复成品落 tier 0」与申报②一致 ✓;sim 盲区机制(char 恒空 + 恒一带钻 → 新旧恒选钻、刷新两侧永不触发)推演成立 ✓;字典序三级 + 三空刷新 + 凑星 tiebreak 零自由参数 ✓;kernel → strategies 零 import 现状成立(grep 仅注释提及规则)✓;EQUIP_GENERIC_VALUE 降格 tier 内定序常数与 16 号稿在册改形相容,strategy-work §1 未证即退役无冲突(定序形态 = 16 号稿 §0 统一落点)✓。
- **文档面**:00_framework.md §1 第 5/6 条 ✓;strategy-docs README §3(kernel 存量 = 待迁)与 §2 分篇表(末篇 28;29 号稿确被投资策略批占用 = invest-strategy design :5「本批新建 29 号稿」,30 空闲)✓;25 号稿 :3(画面族恰 11 屏)/:4(拆分头注先例)✓;13 号稿 :18(decide_invest_env 改指先例)/:20(decide_supply 行「组件/成品需求」描述与实码不符属实)/:40(E4 目录行)/:11(OCR 未就绪纪律)✓;08 号稿 :19(E4 挂账 P42 component_demand/hoard_gaps + P40 变体②类比)✓;16 号稿 :74(挂账在册;「带钻支配(零参数已就位)」定性张力已由 §2.7 对齐条款处理)✓;math_proofs 索引 P40/P42(🔴 待标定 = λ 流/partner 到位率)/P81/P97 行与本批涉猎面一致,本批不声称期望最优 ✓;两份承接迭代 design §1 均登记补给为后续批(env 批 :18、投资策略批 :23)✓;`sim/checks/ledger.py` 路径与 `check_equip_value` 符号在 src + sr-od-test 全部零命中 ✓;proofs 全域无以补给选择为判据面的在册验收线(抽样复核)✓。
- **规范面**:总纲四节齐、landing 各阶段七件齐、末阶段 + 正本更新清单齐;设计依据锚(§2.2/§2.3/§2.4/§2.5/§2.6/§2.7)全部存在;design/landing 正文无过程叙事;README 进度面合规,「第 1 轮 16 项(高 2/中 7/低 7)已全部吸收」逐项核对属实(16/16 均已在 design/landing 落地,含:凑星数据源改判、两账输入、target_comp 载体改 self.state、闸内嵌 + 闸拒绝帧语义、sim 申报改占位分布机制、16/13 号稿入清单、删除面锚精确化、申报⑤、凭据⑦、四方消费枚举、sim 锚 :573、收口清单扩全、P40 变体②转述删、get_comp 回落、所有权申报、encounter.py 改述);无详设单文档方案申报合法且 §2 深度达标(除发现 1/3/6 三处缺口);strategy-work §4 可观测性声明机制准确、判读锚点事前写定、验收线保全清单在册;§5 单帧锁位置(`test_cw_supply_decision.py`)/模式/锁语义不锁牌面合规;项目 AGENTS.md 文档规范(直白表述/引用寿命/as-built)无违例。
- **核三**:§1 根因归层成立(分层语义 = 宪法五所有权存量;语义 = 价值模型缺角色轴/合成维度、刷新无手牌质量条件);修法 = 决策本体迁移 + 判据重构,逐画面迁移节奏 = 宪法六明文(本批为 env/投资策略后的第三批,架构级路线在册),非逐件症状补丁,「同族升架构级」不触发。

## 结论

发现 7 项:**高 1、中 2、低 4**。高一项(发现 1,凑星判据 deployed 入参形状错配)使凭据⑦按稿验收失效且错误静默,须先修设计;中两项(发现 2,§2.8 对 target_comp 未锁帧形态的失实论断;发现 3,config 参数无语义)为定稿门槛(实现者无需再设计)缺口;低四项为锚点精度、清理指引表述、空帧分支与删除面枚举完整性。零和稀泥:每项均给出实证位置与修正方向。
