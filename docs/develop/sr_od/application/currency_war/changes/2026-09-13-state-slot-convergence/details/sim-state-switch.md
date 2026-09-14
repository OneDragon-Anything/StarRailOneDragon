# sim 引擎内部模型切容器(详设)

> 状态:**定稿候选**(对抗审 attack.md F1-F12 已全部处置;字段级事实源 = 盘点报告 `.debug/temp/cwsimframe_migration_inventory.md`)。

## 问题与约束

**问题**:sim 引擎内部状态 = 旧帧 `CwSimFrame`(engine_p1.py:1001 起),与容器 GameState 平行(依据 cw_game_state.py:10-11「平行表示,不是镜像」声明)。引擎在每个策略消费点做「帧→容器」同步:`feed_sim_truth(board_state_of(sess), st, ...)`(engine_p1.py:716/1513/1516/1693 段/1812/1849 段/2645/2889 等 ~10 处),策略经 `board_state_of(sess)` 读容器(flow.py:720)。生产侧另有读链中间层,且「帧→抄写」存在**两条共存路径**:`_feed_board_state`(cw_observation.py:2450)与 `synthesize_from_game_state`(cw_game_state.py:2794)。双表示 + 双转移(`simulate(CwSimFrame)` cw_vocab.py:933 vs `apply_shop_action_logic(GameState)` cw_game_state.py:1479)= 维护税与等价锁长期负债。

**总纲接口契约**(design.md §2,服从):唯一状态类型 = 容器 GameState;唯一动作转移入口 = 容器版单一函数;渠道签名封闭集不变。

**约束**:sim 全量锁与零漂移锚为行为基线,漂移须申报;引擎 sim 本地记账面不进容器(r5-plan §2.1 白名单);直迁先接后删。

## 方案

### 1. 反转形态

引擎 `st: CwSimFrame` 整体替换为 `bs = board_state_of(sess)`:

- 反转后引擎直写容器,~10 处 feed 同步点删除;`feed_sim_truth`/`synthesize_from_game_state`/`_feed_board_state` 三者退役(双抄写并单,盘点 B2);
- 渠道映射(用户裁定 A,2026-09-13):**引擎动作后状态应用 = 统一转移函数,logic_action 族**(理想执行=逻辑投影,与 live 动作记账同函数同渠道;实测 gold 73 vs 71 分歧即双源未合并症状,合并后收敛);**obs 族仅外部事件**(收入/结算/回合初始化/开局播种);驱动器 decide 期投影写维持现状(live/sim 同代码不分叉);xp 即时 vs 延迟结转 = **申报差异**,sim 侧该域失配告警抑制(驱动器按线上语义即时结转 vs 引擎延迟结转,登记 §2.3 申报表)。批A 留帧读的两观测块(采购三观察/必花域)随批B 复核:合并后容器=转移函数权威态,若读口切换仍见失配即停手上报;

### 2. 字段映射(盘点 A1/A2/D 定谳)

- 旧帧 34 字段:31 个有归宿(容器域/派生/常量化);容器读口族 12 口(cw_game_state.py:3059-3174)覆盖读侧;
- 访问热度:bench(R≈33/W3)、deployed(R≈38/W2)、gold(R9/W5)、level、hp、plane;engine_p2 build_state 9 字段(:105-113);runner.synthesize_snapshot 19 字段(:1105-1141);
- **保真位 5 缺口逐位过渡处置(对抗窄攻 F1 定谳)**:容器语义「None=不可读,禁兜底假值」天然替代 readable 位族,引擎切容器后**五位一律不写、不读**(sim 无对应写入面):enemy_difficulty_live(sim 恒默认 False,无消费)·level_readable(sim 恒真读约定,容器 level 直写即真值)·gold_readable(容器 gold=None 即不可读语义,引擎写实际值)·board_readable(同上)·bench_readable(容器 BenchView 直写)。快照侧按 §4 恒 True 定谳;W5 若新立域随 W5,不堵 3.1;
- hp_readable/hp_trusted:政策层派生承载,不迁移;
- **hp 写入闸通道语义(预答对抗 R2,已核码)**:「非真读不经 observe」是实机漏斗侧调用纪律,非写入口运行时校验——sim 真值 hp 现役即经标准 observe(synthesize cw_game_state.py:2859-2860;scalar_projection :3216),引擎直写沿用同通道,无冲突;
- **快照保真位定谳(对抗 F8)**:runner.synthesize_snapshot 三个直出门(gold/board/hp 的 readable 条件取值,:1121/1129-1130/1140-1141)切容器后按 **sim 恒真读约定随迁,条件恒 True**(零漂移锚强约束;依据 = cw_vocab.py:137-139/201「默认 True 仅供 sim 恒真读帧约定」);容器 sig.quality 载 sim 真值标记待 W5 定谳,本迭代不读;
- action_log ≠ 容器 receipts(域语义不同),禁混 merge;sim 账本转录留引擎白名单。

### 3. 转移函数单源化(盘点 A3 定谳)

**定名(F9 定谳)**:沿用 `apply_shop_action_logic` 名扩族,不新增函数名;居所 cw_game_state.py。

**调用点**:全仓仅 engine_p1 经 `import simulate as _simulate_state`(:79)4 处::790(SellDeployed/m1p 换血)、:2075(BuyCard)、:2218(SellBench)、:2278(SellDeployed/SwapDeploy/CompTransaction)。内联申报保留面:RefreshShop=:1950-1986、LevelUp=:2119-2186(LEVEL_CAP=9 差异申报 ADR-0561 #6)。DeployMove 无独立 simulate 消费(围栏块 :2519-2552 为平行第二套,并入转移或申报对齐)。

**转移结果通道(对抗 F1 定谳,3.1 开工前提)**:

- `apply_shop_action_logic` 增加显式结果出参:`-> LogicOutcome`(frozen dataclass:`applied: bool`、`reason: str`、`income: int | None`、`fill_cost: int | None`、`bought_count` 复核值);逐腿平移时由腿内**既有拒绝判定**填充(stale_proposal cw_vocab.py:1001-1006、满栏非合成拒买 :967-976、同名拒上 :1038-1041、CompTransaction C1 整批拒),拒绝 = applied=False + reason,零容器写;
- `executed` 回执入参改 **Optional**(对抗重派 worker 定谳,2026-09-13):live 路径传执行回执(bought_count 等参数化不变);sim 路径传 None = 理想执行,函数自算 k(满栏合成买 k 从 _apply_full_bench_merge_buy 出);`LogicOutcome.bought_count` = 函数实际应用张数的**权威回声**,两路径恒填充;executed 与自算值的关系核对仍归调用方守卫面,不入函数;
- live 现役调用点(cw_op_buy_cards.py:1148、flow/bridge 驱动器)对该出参**忽略**(返回值不接 = 行为零变化);守卫断言族(guard_proposal_vs_expected/guard_expected_vs_tracked)继续在调用方承载,不迁入函数;
- SHOP_PROJECTION_DOMAINS 封闭集扩面(v2 动作族腿的 deployed/equips 域)随平移申报(:1509-1510「禁扩静默」注解同步改写为「扩面随本迭代申报表」);
- 引擎侧拒绝账本转录(LevelUpRejected 行等)读出参驱动,**禁在引擎自判拒绝**(§2.1 单一源红线)。

**deployed 域平移契约(对抗 F7 定谳)**:v2 腿语义源操作定长槽表(置 None 不移位 → 同轮多笔卖出索引恒稳,cw_vocab.py:178-184);容器侧 front_row/back_row 为紧缩行列表。平移形态 = **腿内经 `deployed_slots_of` 取槽表 → 按原腿槽表语义置空 → 整表 write_logic**(槽位坐标系跨表示保持,「置空不移位」由槽表中间形态承载);装备守恒对账(state_equips_multiset 前后比对)留引擎白名单侧继续消费(其帧支存续见 §6/F4)。

**平移边界(已核内联雷区原文)**:字段转移(gold/xp/xp_progress 写)进单一函数;引擎保留 = 池重采样(draw_shop)、刷后 break-redecide、LEVEL_CAP 守卫与拒付账本行(前置检查不写状态字段,lv9 差异保持申报)、auth/dec_* 观测披露键、免费刷额度注入(申报差异 #2)。判据:转移函数只辖「GameState 字段怎么变」。

**锁面处置表(对抗 F5 定谳)**:

| 锁 | 现形态 | 处置 |
|---|---|---|
| 防回漂锁1(spy「执行必经 _simulate_state」) | test_cw_sim_shop_single_source | 重推:「引擎执行必经容器版单一转移函数」结构锁 |
| 防回漂锁2(带装卖出回池行为锁) | 同上 | 随逐腿平移保绿,红=平移失真 |
| 防回漂锁3(grep 禁内联特征回潜) | 同上 | 续用,特征式更新(内联特征随退役改指新函数面) |
| M1(apply_shop_action_logic ≡ simulate 对拍) | test_cw_shop_projection_logic | 3.1 重推为容器单函数行为锁(金样 fixture 自 simulate 平移前捕获);3.5 只扩三态 fixture,不再称「等价锁」 |

注:三锁/M1 实体若已随测试套件删减不在库,按用户测试精简裁定重建最小形态(spy 结构锁 + 金样行为锁两件),不恢复全量旧锁。

### 4. 引擎改造面

- engine_p1/engine_p2:`st` 构造与全部字段访问切容器;开局播种 → 容器 BenchView 构造(开局合成参数 = sim 本地面 :1002 留引擎);`synthesize_snapshot` 输入切容器(快照保真位按 §2 定谳恒 True);
- cw_replay 旧格式回放重建切新账;cw_game_ports 端口注解切容器。

### 5. 生产观察链直写(3.2 阶段面)

- read_game_state 调用点全集(8 处/6 文件):telemetry/cw_match_recorder.py:80(纯遥测)、cw_loop.py:606(只取 gold)、cw_loop.py:1535(只取 plane/round)、cw_observe_full.py:103/118/181、cw_op_buy_cards.py:855(最大直写改造点)、cw_screen_prep.py:3051(只要副作用);
- 已直写域无需再改:prep 装配环 bench(cw_screen_prep:660-690)、买后重估(:3038-3046)、receipts/效果账本;
- **BuyCardsOutcome 退役**(对抗 F2 定谳,三处修正后):class 删除,消费方四件(安灯钩子 cw_screen_prep.py:2358-2400、classify_spend_unit query.py:126-193、finalize_buy_phase :2964-3120、cw_loop.py:665-673)迁移:
  - **安灯判定链按 classify_spend_unit 真判定链逐态申报**(对抗 F2-1 修正):非「计划花费>0 ∧ 金差≈0」字面——含两豁免:plan_truncated → 不停;金差≈0 ∧ refresh_attempted ∧ refresh_board_changed=True(免费刷执行成功)→ 不停;判定方向 = 漏停不误停;
  - **换轨后数据源 = 精简访问事实暂存(容器+渠道三源)**:动作序列 = 访问窗 receipts 发射行(serialize_action 同 schema);gold_open/gold_close = **编排壳显式捕获**(visit 入口容器 gold 现读暂存 / finalize 关店现读——对抗 F2-3 修正:Field 单最新帧无历史,禁从容器回取历史帧);plan_truncated → receipts extra(现役写点已在);refresh_attempted/refresh_board_changed → **refresh 留证遥测半边承接**(现役候选 a 合法面,3.8 只拆判效半、留证半存续——对抗 F2-2 时序倒挂消解);
  - 访问窗键 = (plane,round,unit_seq) meta 不变;对拍窗一期(旧源/新源并行一局比对判定一致后切换);
- 签名收口(盘点 C 桶):2 签名勘误(guard_expected_vs_tracked/_record_free_refresh_proc)、4 注释勘误、5 真双型收敛(state_equips_multiset 例外见 §6)、encounter.py 本地帧视图删除、seed_age_blocked 死码删除。

### 6. 残留旧帧面删除归属(对抗 F4 定谳,方案 b)

- 契约 = **活引用零残留**(构造/字段访问/函数签名);CwSimFrame 类本体、simulate 定义、state_equips_multiset 帧支等残余共享词汇**留 W8 切割**(r5-plan W8 行),本迭代不删本体;
- state_equips_multiset 帧支存续至 W8(其 simulate 生存期理由随 W8 simulate 删除同步消亡);
- 3.3 完成判据对应改为「活引用零残留」口径(与总纲契约 1 一致)。

## 关键取舍

1. 弃「引擎自持独立容器实例」:双源复发;frozen 帧语义天然提供旧引用隔离。
2. 弃「保留 simulate 名」:apply_shop_action_logic 已在生产路径承载同语义且有对账基础;simulate 随旧帧退役(W8)。
3. LevelUp/RefreshShop 内联保留面在平移中消解:逐腿以引擎现行为为准逐位保真;行为变更归 LEVEL_CAP 批(既有裁定);LEVEL_CAP=9 保持申报。
4. 渠道族:sim 动作投影 = logic_action,真值面 = obs;actor 登记面补 sim 引擎名(落地批申报具名)。
5. 保真位 5 缺口不新造容器字段(W5 定谳归宿);快照侧按 sim 恒真读约定随迁(F8)。
