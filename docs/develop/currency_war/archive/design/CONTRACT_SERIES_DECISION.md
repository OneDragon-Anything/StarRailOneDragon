# 序列决策契约(画面 op ↔ 策略器)v2-已冻结

> 状态:**已冻结 v2**(2026-09-03,用户批准;v1 三裁决点[裸 list 同构商店/Decision 层不进
> 生产;备战空批语义归流程侧;词表统一不在契约]原样保持;v2 变更=§3 分域+备战 12 类补判
> +SwapDeploy 新增分类+§3.3 fail-closed 条款——变更全记录见文末附章)。决策记录 =
> `docs/develop/currency_war/redesign/decisions/dd-020-series-decision-contract.md`
> (谱系:dd-014 后继;文内修订节载 v2);本文件为契约正文权威工作副本,汇合点(流程侧
> 序列消费落地)后 as-built 承接归 `docs/develop/currency_war/strategy/07_plugin.md`。
> 读者:流程侧(画面 op 实现)与策略器侧(决策核实现)。

## 0. 范围

- **动作发射类接口**两条:
  - 备战线 `decide_prep_screen`(本次升级对象:单动作 → 序列);
  - 商店线 `decide_shop_screen`(现役已是序列,条款照抄现状冻结)。
- **pick 类不在本轮**(`decide_invest/supply/encounter/megastar/partner` 及具体类上的
  `planner/star_tome/wish_trial/box_card`):它们是选项决策,动作编排归画面 op。
  已知泄漏(遭遇分支刷新:`pick.refresh` 旗标 + handler 侧重决策循环)记为后续
  收编候选,走本契约 v2,不在 v1 强行统一。
- 词表统一**不在 v1**:备战线词表 = `kernel/cw_prep_actions.PrepAction` 族;商店线
  词表 = `kernel/cw_state.Action` 族(ABC 注解现状)。两词表保持各自接口,后续若
  合并须回本契约改版。

## 1. 接口形态(冻结)

画面 op 侧:把本帧观察结果写入 session 黑板(备战 = `session.prep_obs_frame`;
商店 = `session.shop_state_frame`;画面 op 是唯一写者),然后调用**一个**决策接口:

| 接口 | 签名(v1) | 变更 |
|---|---|---|
| 备战 | `decide_prep_screen(session, config) -> list[PrepAction]` | 返回类型 一个 → list |
| 商店 | `decide_shop_screen(session, config) -> list[Action]` | 无(现状冻结) |

- 执行序 = 列表序。
- **迁移期适配(并行使能)**:现役单动作核包一层长度 1 序列的适配器,行为与
  现状逐动作重决策等价;新核 = 同接口替换。切换前后对流程侧零感知。
- **形状裁决**:生产接口 = 裸 list(与商店同构)。`decision_v2/contracts.py` 的
  `Decision/AtomOp` 层**不进生产接口**——DirectorV2 引擎退役(W971 P3b)后它仅存
  sim/离线驱动用途,保留该用途;生命周期机制(幂等键/连败→恢复→屏蔽)在流程侧
  直接挂在动作与 `action_key()` 上,双表示层徒增适配(现役 `DecideAdapter` 只支持
  单元素批的实证)。若流程侧重构需要 Decision 形状,回本契约改版,禁静默双轨。

## 2. 序列语义(冻结)

- **fail-stop**:任一动作未落地(`progressed=False`)→ 余下动作丢弃 → 流程侧
  heavy 重观察 → 重新调用决策接口。参数非法(F3 拒绝)与执行失败同型:截断 +
  重观察,不进连败链的拒绝路径语义保持现役口径。
- **帧稳定域(核心条款)**:序列内第 i+1 个动作**不得依赖第 i 个动作执行后的
  新观察**。策略器发射时逐动作判:本动作执行后的画面状态能否**静态推出**——
  能 → 继续发射;不能 → 在该动作处截断(该动作本身可作为序列最后一个动作发出,
  其后果由重观察消化)。
- **逐动作验证保留**:fail-stop 砍掉的是重决策,不是验证。序列内每个动作照跑
  期望态对账/执行验证(现有机制:BuyExpect/DragExpect/EquipExpect/金差对拍),
  它们只依赖执行侧记账,不依赖重新决策。
- **生命周期机制归框架**:幂等键(`action_key`)/连败→恢复→屏蔽/stall 门/强制
  出战,全部流程侧所有;策略器不自实现(现役契约条款,冻结重申)。
- **批内评估先例(策略器侧已有等价物)**:现役决策核已在内部按「working 态逐笔
  复检」评估动作序列(ADR-0380:同批多笔的批量语义经对前序采纳后状态的逐笔复检
  实现,decision_v2/arbiter.py:818-833)——序列接口是把核内已有的序列计算
  **外化**为接口输出,不是新引入的语义。

## 3. 截断规则(帧稳定边界,分域枚举)

### 3.1 商店线域(`decide_shop_screen` 词表 = cw_state.Action 族)

| 动作 | 帧稳定 | 依据 |
|---|---|---|
| BuyCard(商店) | 可续 | 牌位坐标不变;bench 累积效果走 tracked 记账(`mutate_bench_deployed` 先例);同 x 重复发射执行侧去重(现役) |
| LevelUpShop | 可续 | 按钮坐标不变,经验动画不迁移界面 |
| 拖拽族(SellBench/SellDeployed/DeployMove/SwapDeploy 系,商店线侧;bench_idx/d_idx 坐标系,与 §3.2 同名 PrepAction 行分域互斥) | 条件 | ADR-0316 槽位模型下 bench 索引结构恒稳(定长含 None)——下标安全是结构保证;逐动作语义防线=名-槽一致性复检;board 空位/星级合成须按前序动作累积静态推出,推不出即截断。SellBench/DeployMove/SellDeployed 三类=decide_shop_screen 管线现役发射(decision_v2/candidates.py L504/L599/L616、decision_v2/remediation.py L340/L450、kernel/cw_evolution.py L1588,2026-09-03 批时快照);bench 下标 0-based/1-based 差异辖语义防线不辖截断判。【R195 修注:原行含「装备拖拽,商店线侧」系幻影成员——cw_state.Action 联合无装备拖拽类(装备拖拽执行载体=prep 侧 CwOpEquipAll 内部动作,辖 §3.2 RunEquip 行),已删;IMPL_ADV_R195 症1,打标不删史】 |
| RefreshShop | 截断点 | 刷新改变牌面,必须重观察重决策(现役规则:执行至首个 RefreshShop 含) |
| CompTransaction(fill 消费店槽) | 截断点 | 事务 fill 消费店槽后,同序列后续 BuyCard 引用陈旧槽位——截断重决策(sim engine_p1.py break-redecide 先例) |
| 合成触发 | 截断点 | 满栏买入可触发自动合成,bench 形变不可静态精确预测——发射器在「可能触发合成」的买牌后截断 |

词表源对账声明(R195 症1 补):cw_state.Action 联合 9 类中 `PickEvent` 系 pick 决策返回载体(选项决策,与 §0 pick 接口辖外同型排除),非商店线发射动作,不进截断表——词表演进中的新类由 §3.3 fail-closed 兜底。

### 3.2 备战线域(`decide_prep_screen` 词表 = PrepAction 族,17 具体类逐类判)

**承 v1 既有判的 5 类**(内容不变,迁移入本域;槽位坐标系=PrepAction 物理槽位,与商店线坐标差异不辖截断判):

| 动作 | 帧稳定 | 依据 |
|---|---|---|
| LevelUp | 可续 | 按钮坐标不变,经验动画不迁移界面;cap+1 效果走记账 |
| SellBench / SellDeployed / DeployMove | 条件 | bench 索引结构恒稳+名-槽一致性复检;board 空位/星级合成按前序动作累积静态推出,推不出即截断 |
| StartBattle(出战) | 终点 | landing 即环正常出口,只能作序列最后一个动作 |

**v2 新增判的 12 类**(判据=§2 帧稳定定义,推理链逐类):

| 动作 | 帧稳定 | 推理链 |
|---|---|---|
| DeferSpheres | 可续 | 控制流特殊动作(§4:不进 execute 验证链),球留置=框架 defer 计数承载;画面零迁移、球位置不变,执行后状态静态确定 |
| BailToOuter | 退役·终点 | 词表已退役(W971 §2.6.1),仅防御性兜底——生产发射器禁发射;防御性发出时按序列终点语义(中止本环交外环) |
| ClickSpheres | 条件 | 常态分支(纯收集):球消失/收集数由执行侧记账确定——可续;掉箱分支:是否掉箱不可静态预测,掉箱弹 overlay 画面切换——发射器在末批 ClickSpheres(可能掉箱)后截断;执行侧「掉箱即停回环」+fail-stop 兜住残余 |
| OpenBox | 截断点 | 开箱弹武装箱 overlay=画面切换;「开箱即腾席」bench 形变即时生效——作序列最后一个动作发出 |
| OpenTome | 截断点 | 开典籍弹星徽四选一 overlay=画面切换;后续选卡归 pick 语境(§0 辖外)——同 OpenBox 判 |
| PickBoxCard | 截断点 | overlay 语境动作:选卡后 overlay 关闭、卡入队,画面经切换——截断。辖域分立声明:本行截断判辖=序列发射面;pick 决策面(选哪张卡=decide_box_card)仍归 pick 接口辖外(§0 零改动);两辖域分立禁并读 |
| EnsureShopOpen | 退役·截断点 | W970 批 C 退役(dd-017),生产改发 OpenShop——生产发射器判不辖;兼容面保守判=截断点 |
| EnsureShopClosed | 退役·截断点 | 同上(W970 退役)——兼容面保守判=截断点 |
| OpenShop | 截断点 | read_only=False:开店=画面切换至商店界面,商店决策循环由流程层接管——意图终结语义,序列在此收口;read_only=True:开店→读数→关店复合往返,读数时点与回环分支不可静态推出——两分支统一截断点,作序列最后一个动作发出 |
| RunBuyPhase | 退役·截断点 | 执行器组合分支已随 BuyShopCards 壳退役删除,动作类型保留供期望态/对账兼容——生产发射器禁发射;兼容面判=截断点 |
| RunDeploy | 条件 | 组合部署:内部成员=部署拖拽族(条件判)——bench 索引结构恒稳+名-槽一致性复检;换血/去重结果按部署计划静态推出,推不出即截断 |
| RunEquip | 条件 | 组合装备:装备-槽位映射按计划静态推出;装备拖拽属拖拽族条件续同判 |

### 3.3 未识别动作处置(新增)

发射器逐动作判遇**词表外动作**或**词表内但无分类**动作时:fail-closed——该动作处截断,不猜测分类、不静默丢弃;且该缺口**须可观测**:实现须计数并披露,禁不可观测的静默截断。计数的键名与粒度不在本契约立法——归实现期遥测键登记纪律承载(design_telemetry 键节=遥测键单一登记源;契约禁成遥测键第二登记源)。缺口信号确认后须回本契约改版补条目(§6),禁只改代码。批内评估/骨架评估不受影响(截断仅辖发射面)。

此两域表+§3.3 为**已枚举动作类**的完备判(辖域=批时快照词表:商店线 cw_state.Action 联合减 PickEvent、备战线 PrepAction 17 类);词表演进中的新类由 §3.3 fail-closed 兜底并回契约改版,禁只改代码(R195 症1 辖域限定)。

## 4. 空批与控制流(冻结)

- **空序列合法**,语义 = 「本帧无动作可发」。
  - 商店线(现状冻结):空序列 = 决策完成 → 流程层触发关店。
  - 备战线(v1 新定):处理归流程侧框架——重观察,连续空批过 stall 门后的兜底
    (强制出战或交回外循环)由流程侧定义并写入其实现文档;策略侧不感知。
  - 策略器**禁用空批表达任何控制流**。
- **控制流走词表内特殊动作**(现状):`DeferSpheres`(球留置)为词表成员,
  defer 计数归框架;`BailToOuter` 词表已退役(W971 §2.6.1),仅防御性兜底。控制流
  动作不进 execute 验证链。

## 5. 职责分界

| 面 | 策略器 | 流程侧(画面 op) |
|---|---|---|
| 观察帧 | 读 session 黑板(禁自取屏) | 写黑板(唯一写者) |
| 序列发射 | 帧稳定域内出计划序列;判截断 | — |
| 执行+验证 | — | 逐动作执行、F3 参数校验、期望态对账 |
| 截断响应 | — | fail-stop 丢弃余下、heavy 重观察、重调接口 |
| 生命周期 | 禁自实现 | 幂等键/连败→恢复→屏蔽/stall 门/强制出战 |
| 出战决策 | 决定何时发出战动作 | 出战 landing 即环出口 |

## 6. 版本与变更

- 本契约冻结后,任何条款改动动版本号(v1→v2),禁静默改义(先例:
  `SNAPSHOT_SCHEMA_VERSION` 的版本化决策)。
- 本契约是接口冻结件,不是策略开关;行为输入未就绪的过渡臂仍走
  strategy-work「策略开关的生命周期」门。

## 7. 现状锚(起草时核验;流程侧重构中,路径/行号按「契约占位」处理,漂移不立案)

- 抽象类:`decision/cw_strategy.py`——备战线单动作契约 L130-139;商店线序列
  契约 L142-153(空序列=完成);pick 族 L156-183。
- 现役消费:`operations/cw_screen/cw_screen_prep.py` L1191-1215(备战五段决策段,
  单动作+F3+控制流特判;原 prep_director.py,流程侧重构移入,行号随迁);
  `operations/prep/buy_cards.py` L589-707(商店序列消费+RefreshShop 截断)。
- 契约层遗存:`decision/decision_v2/contracts.py`(Decision/AtomOp/Defer/Bail)、
  `decision_assembly.py`(DecideAdapter,单元素批)、`director_v2.py`(引擎已退役
  生产,保留 sim/离线)。
- sim 侧消费面(2026-09-03 测绘,`core_swap/SIM_CONSUMPTION_MAP.md`):sim 仅消费
  `update_target` + `decide_shop_screen`(engine_p1.py:926/937),`decide_prep_screen`
  在 sim 零调用——**sim A/B 的证明面 = 商店波经济决策(买/卖/升/刷/事务)**;
  prep 屏编排域(收球/开箱/典籍/腾席拖拽/开商店时机/出战时机)在 sim 无实体真值源
  (合成器契约:runner.py:895-902),其正确性防线 = 契约锁+适配器零漂移门+实机,
  不在 sim A/B 辖内。

## 附:版本变更记录(非契约条款,不占条款号)

| # | 变更 | v1 | v2 |
|---|---|---|---|
| 1 | §3 分域(商店线/备战线两表) | 两域词条混排单表 | 分域两表;「BuyCard(商店)」限定词升格为域标注 |
| 2 | 备战线域补 12 类条目 | 仅 5 类有判 | 逐类判齐(含 4 退役类退役标注+兼容面判) |
| 3 | §3.3 未识别动作处置 | 无 | 新增(fail-closed 截断+计数披露义务;**键名/粒度归遥测键登记纪律,契约不立法键名**——R193 症3 裁定:契约禁成遥测键第二登记源) |
| 4 | 商店线域拖拽行 | 枚举缩略 | 显式化消歧(恢复 SellBench/SellDeployed/DeployMove 显式枚举+坐标系限定词;**判语义零改义**——R193 症1 裁定) |
| 5 | SwapDeploy 系分类 | 零出现(grep 亲验) | **新增分类**=拖拽族条件续(现役商店线发射动作:decision_v2/remediation.py L687 `remedy_slot`、kernel/cw_evolution.py L1581 `valley_rollback`,批时快照亲验在案——R194 症4 裁定如实申报) |
| 6 | §0/§1/§2/§4/§5/§6/§7 | 冻结 | 零改动 |

> v2 定稿:2026-09-03 用户批准。提案与对抗审查链:CONTRACT_V2_PROPOSAL.md(已归档)
> ←IMPL_ADV_R192 症1/R193 症1-4/R194 症4/R195 症1·症3(修复全闭环,详见 design_telemetry 对应节)。
