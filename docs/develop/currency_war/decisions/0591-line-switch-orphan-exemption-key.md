# ADR-0591: 同轮买卖检查器豁免面补「线账闭合孤儿清算」键(T-141;P78-2a 账闭合语义对齐批)

- **Status**: 已实施(方案审零阻断放行;commit 候编排者统一门)
- **Date**: 2026-09-08
- **方案**: `.debug/temp/currency_war/attacks/t141_m4_interact/方案审.md`(2026-09-08 同轮交互方案审,干净上下文对抗审,零阻断放行)
- **命题**: math_proofs **P78-2a**(义务/持有类账期 τ=∞,至账闭合事件 = 件离场或线账闭合[换线])+ **P78 INV**(账闭合 ⇒ 排除解除 ⇒ 通道可卖);**P78-1 不辖此形态**——其证明前提「同 visit 无新信息/无新收入」被线账闭合事件(K 支持度重排)破坏,该命题对此形态无管辖权
- **关联**: ADR-0585(卖出仲裁单一源;SELL_BENCH_CONVERT_REASONS 三键形态与 reason 枚举闭集的母件,本件扩第四键)、ADR-0267(r408 同轮买卖互斥检查器原设:振荡 0 容忍;本批扩白不损其拦截价值——无 XP 白拿/无循环/净金 0)、ADR-0276(3合1 让位豁免先例:豁免面按形态分键收敛的同类演进)、T-136 可见性批(暴露 ci_smoke 慢锁红 `no_same_round_buy_sell [18]` 的前置批)

## 1. 背景与归层

ci_smoke 慢锁 `test_ci_smoke_snapshot_batch` 预存红:`no_same_round_buy_sell [18]`(seed18 p1r1 买入青雀当轮被卖)。方案审以逐帧决策轨迹取证定谳:**卖出通道 = 凑息回拉(sell_for_interest 发射位),非 M4 腾席**;帧 #6 的 M4 卖出对象为丹恒·腾荒(合法燃料),帧 #9 凑息卖出青雀时其 K 资格已被支持度重排收窄(基座排除集不再含之)。

**归层:遥测/验证层**(同轮买卖检查器的豁免面语义缺口),非决策层——三卖出通道的排除装配实证有效(青雀 ∈ K 期间恒被排除),决策与执行零缺陷。根 = 检查器以「同轮」为原子粒度,其豁免面只建模「转化类卖出」三键,未建模「线账闭合后孤儿清算」这一 P78-2a 在册合法形态:本轮内合法发生的账闭合事件落在检查器粒度盲区。

### F1/F2 事实纠错(勘误正文,持久索引;T-136 落地审相关表述随案勘误)

- **F1(通道归属勘误)**:「同轮被 M4 腾席卖青雀」不成立——青雀由凑息回拉通道卖出。成因 = 三处商店卖出位在批 4 之前 sell_reason 恒空,账本无法辨通道,落地审按「席满语境 + 空 reason」推断为 M4,推断失实。批 4 reason 载体落库后本类误归因不可再现。
- **F2(M4 治理辖认定更正)**:「M4 腾席卖路径不在批 3 治理辖」不成立——M4 全部三处卖出位(shop.py M2 缺员腾席/m2_stockpile 腾席 + mandate.py 备战域腾席)批 2 已接身份段、批 3 已接窗口段(`sell_exclusions(channel='m4_fuel', current_round=...)` 在码),且轨迹实证排除有效(press 件与线成员从未进入 M4 候选)。候选修复「甲(M4 路径接排除集消费)」修的是不存在的缺口。
- `.debug` 证据文件不改,本节为勘误唯一持久索引。

## 2. Considered Options(候选攻防摘录;全量 = 方案审 §候选攻防)

- **甲(M4 腾席路径接排除集消费)**:✗否决,双重否证——前提失实(F1/F2);即便强行加「本 visit 买入件禁被 M4 卖」也是过度禁卖:杀死 P78-5′ 在册垫保转化放行、把线账闭合孤儿钉死成死库存(阻塞 M2 买入逼 m2_retry_exhausted 诚实停摆)、收益 0(1★ 往返净损 0,P76 甲)、制造通道间不一致(ADR-0585 收拢前 5 种互不一致形态复发)。
- **乙(检查器豁免边扩白)**:✓方向正确但须按 P78-2a 精确形态——任务书预判「P78-1 论证不成立故乙不成立」被证伪:P78-1 确实不辖,但理由是前提被破坏而非禁卖成立。
- **丙(发射登记补 M4 臂)**:✗范畴错误——LaunchCause 是买入因闭集,M4 是卖出通道(SELL_CHANNELS 已含 m4_fuel),卖出是生命周期出口非发射。其可取内核(义务/持有类买入臂登记写点补全,ADR-0585 §6 在途件)被乙′吸收为使能件。
- **乙′(豁免面补「线账闭合孤儿清算」键 + 卖出发射位账闭合证明打标 + 义务类登记写点补全)**:✓采纳实施。

## 3. 实施形态(单批五件)

1. **豁免键集三→四键**:`cw_state.SELL_BENCH_CONVERT_REASONS` 增 `line_switch_collapse`(语义 = 线账闭合孤儿清算;键 = 通道名兼证明标记,双消费检查器 no_same_round_buy_sell / check_oscillation_xp_cap 经单一源常量自动同边)。
2. **义务类登记写点补全**(ADR-0585 §6「写点随矩阵批落」提前落):`shop._emit_buy` 登记写点从窗口段两类扩为 LAUNCH_CAUSE_BY_ARM 全映射(obligation/hold 落账;hold 过既有 W5 类资格断言,拒登记不拦发射语义不变)。行为零面:两类不入窗口段(`active_window` 过滤面不变),身份段由基座/静态集独立承载;义务件自此有账可闭,`_close_switched_obligations` 线账闭合读点真实运转(close_on_switch 分键显影)。
3. **卖出发射位证明打标**:shop 四卖出发射位(M2 缺员腾席/m2_stockpile 腾席/凑息回拉/funding 主路径)victim ∈ 本轮孤儿证明集 ⇒ `reason='line_switch_collapse'`(通道无关标记;T3 转化键优先级保持——被保件登记因类互斥,与孤儿标记无同帧竞争;凑息位被保件已 defer 绝对跳过)。
4. **t3_stall_protect 键集锁更新**:三键 → 四键,锁 docstring 引本 ADR 与方案审(锁语义演进,非机械跟绿)。
5. **追加件(三审三波 F6)**:entry.py 两处 funding 兜底发射位(骨架-only 位/_criteria_pass EV 位)`funding_hold_liquidated` 回填载体归因(批 3 旧申报「走计数不入载体」废止——批 4 prep 载体已带 reason 字段,与 shop 兜底位归因一致性面对齐;tag==reason 双写)。

### 与方案审实施件 1 的偏差申报(证明载体落位)

方案审件 1 原设计:闭账名集写点与单一源读端落 sell_gate(`_close_switched_obligations` 同步写会话级 `{名: 闭账轮}` + `switch_closed_this_round` 读端)。本批 sell_gate 文件面禁碰,证明载体改落消费位 shop.py:**义务类买入镜像簿**(scratch 键 `shop_obligation_buy_rounds`,{名: 买入轮}),发射登记成功后写点同步落——义务类登记无资格断言恒落账,簿 ≡ 登记簿义务类视图;孤儿证明集 = 本轮簿名 ∧ 已出基座(帧首、任何装配 A 读点之前计算——A 身份段会就地销账,销账后登记面不可再辨「曾义务」)。等价性论证:bench 在场义务件的轮内账闭合出口唯一 = 换线闭合(卖出销/部署销/合成销都以件离场为前提),合取不误标;base 解析传帧 `buy_members` = `locked_buy_membership` 或 k_members,与 `_resolve_base` 同一语义源。跨轮名随轮戳剪枝(陈旧证明不洗白)。**回迁候 sell_gate 开放批**(读端单一源化,消费位手搓读的残面随迁消除)。

## 4. 防洗白边界

键的授予必须伴随登记簿线账闭合事件,非自由豁免:

- 打标条件自带证明:证明集只含「本轮义务登记 ∧ 已出基座」名;窗口段回归(press 件同轮被卖回)与第五通道卖出无此证明 ⇒ 不打标 ⇒ 检查器仍红 ⇒ 回归被抓。
- 检查器侧镜像锁:`test_unmarked_still_violation`(缺省 '' 恒红)与 `test_plain_reason_does_not_extend_convert_exemption_face`(plain 通道值同罪)随批保持绿,豁免面不因键集扩边而全开。

## 5. 波及面、验证与边界申报

- **红闭合判据**:ci_smoke 慢锁 `no_same_round_buy_sell` 归零(40 seed 扫描违例恰 1 = seed18,且该轮 K 变化签名唯一命中——家族即此一型)。
- **漂移首发点**:seed18 p1r1 青雀 SellBench 行 sell_reason 字段(决策轨迹逐位不变;reason 不进决策输入,`cw_replay --diff` 渲染只取 bench_idx,归因填充结构性零漂移,ADR-0585 §6 批 4 同款申报)。
- **行为零面复查**:写点扩全映射不改排除装配(funding 兜底池读静态持有集非登记簿);engine_p1 `stall_buys_pending` 遥测口径随四因类落账显影(ADR-0585 §6 批 3 申报③既定),纯遥测;close_on_switch / launch_cause_mismatch 分键开始可能显影,批内申报。
- **边界申报(登记观测,不阻断)**:entry 换线塌缩位 reason='line_switch_collapse' 为通道名标记,k_switched 事件门 = 其线账闭合语义承载(换线塌缩候选域 ⊂ 旧线成员,与 T3 垫件结构无关声明在 criteria/sell);prep 域卖出「恒先于本轮买入,买→卖向结构性不存在」的在码申报沿用(mandate.py 备战域卖出位不涉本键打标)。若后续遥测显示 line_switch_collapse 高频化,立策略批按数学先行处理支持度粘滞(K 派生 p1_early_pair 无门槛现读的非单调面),禁回扩检查器。
- **验证**:L1 快速层全绿 + 慢桶 ci_smoke 单跑绿(红闭合)+ seed18 端到端锁(发射侧首发点)+ cw_replay 漂移口径核对 + ruff 四 src 文件。
