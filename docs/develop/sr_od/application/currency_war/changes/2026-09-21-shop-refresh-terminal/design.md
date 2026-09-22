# 商店刷新真终结与访问循环规范化 迭代设计(总纲)

## 0. 元信息
- 迭代目标:商店画面访问回归画面 op 两 node 规范——RefreshShop 升级为**真访问终结**(交回外循环重新观察)、决策动作 node 收敛为单动作 round_wait 循环、段机器(波循环)整体退役、店开防抖删除、段尾画面 op 自对账删除。
- 依据指针:用户裁定 2026-09-21(六条):①「决策动作 node = 波循环内聚状态机」违规,波/段循环是策略侧的事情;②店开防抖 3×0.8s 没必要,删掉;③RefreshShop 这类刷新动作要交回外循环重新观察;④刷新环暴露面采方案 a(维持框架不兜底,外部 stall 哨兵);⑤动作 op 只做机械执行默认成功不做验证,对账 = 动作 op 上报 → game state 计算逻辑态 → 下一次真观察再对账,画面 op 结尾不自做对账;⑥防抖删除并入本迭代。
- 状态:定稿(2026-09-21,第三轮收敛复核通过;报告 = [attack.md](attack.md);R1–R6 短句修订已入库)
- 文档清单:[details/shop-visit-loop.md](details/shop-visit-loop.md) —— 商店访问新形态逐拍 / 刷新次数观察锚定 / 删除面清单

## 1. 问题与动机

现状症状(审查实证,锚 = `文件::符号`,路径根 = `src/sr_od/application/currency_war/`):

1. **段机器违规**:`operations/cw_screen/cw_screen_buy_cards.py::run_buy_waves` 内嵌段循环,承载「刷新 = 段终结、段间判定 `did_refresh`、仅刷新波判定 `refresh_wave_is_refresh_only`、连击续刷 settle 跳过」——波/段节拍是策略域语义,实体化在 flow 层(用户裁定 ①)。规范正本 = `screens/op-layer.md` §1.1:决策动作 node = 单动作 round_wait 循环,无防御上限。
2. **刷新为伪终结**:`operations/cw_op/cw_refresh_shop_action.py::CwActionRefreshShopOp` 类属性 terminal=True,但消费侧 = 段循环 break,下一段入口观察在 `run_buy_waves` 内重进——「交回外循环重进」由段循环模拟,外循环重分发/0n 重识别被绕过(screens/README.md §6 段终结行的物理载体声明)。
3. **动作 op 读屏越界**:`CwActionRefreshShopOp` 读屏三处(刷前两口径现读 / 刷新钮真值读 / 刷后牌名落账)+ 真值留证票两张;`operations/cw_op/cw_buy_card_action.py` 买前裁片读屏一处;`run_buy_waves` 段尾 pixel-diff + SIFT 回读对账块——违动作 op 机械执行纪律(action_ops.md §1「动作 op 是机械执行 + 如实上报,禁止验证」)与「对账唯一发生点 = 观察边界」(op-layer.md §1.3;用户裁定 ⑤)。
4. **店开防抖**:`cw_screen_buy_cards.py::_shop_entry_read` 有界重读 3×0.8s——用户裁定 ② 没必要。
5. **刷新次数无观察写端**:免费剩余次数的 UI 真值由动作 op 在点击时读取(T-13 通道),次数账本(`gs.effects.free_refresh_balance`)仅逻辑维护、无观察写端——不符合「画面观察上报 game state、动作上报扣减记逻辑态、下一次真观察再对账」的标准两态模式(用户裁定)。免费刷新金/牌面对账件宿主 = `ShopVisitLedger`(per-visit),真交回后对账点在下一访问,载体跨访问问题随新模型一并消亡。

根因归层:**流程层**。段机器的唯一存在理由 = 刷新伪终结——flow 层用段循环模拟「交回重进」,为此长出段间判定/仅刷新波判定/刷新 op 刷前现读等整套补偿复杂度。修根 = 刷新真终结,段机器自然消亡;不在段机器上继续打补丁。

解决到哪:§2 系统级变化 1–7 全部。
**明确不解决**:
- 商店域 `CwActionLevelUpShopParam`/`CwActionSellBenchParam` 执行链断裂(`run_buy_waves` 组装的 `ShopExecEnv` 无 `executor` 字段,而 `CwActionLevelUpOp`/`CwActionSellBenchOp` 函数体消费 `env.executor`;现役策略面收缩至备战期,生产不可达)——本迭代仅在正本能力面加「未接线」注记,接线自成后续迭代。
- `cw_start_battle_action.py` 出战后弹窗识别(备战域动作 op,action_ops §1 增补 3 欠账登记)——不在商店迭代辖内,清法另批。
- 无限刷新活锁的进程内兜底:维持「无限刷新环 = 策略实现 bug,框架不兜底」(用户裁定 ④ 方案 a;外部 stall 哨兵承暴露面)。
- mandate_v1 策略判据(买/卖/刷数学)零改动;守卫语义不变。

## 2. 方案

系统级变化(读一遍知全貌):

1. **RefreshShop:段终结 → 访问终结(真交回)**。execute(点击 + 固定等待 + 自上报)后决策动作 node 即 round_success 交回外循环;外循环 0n 重分发 → 新访问入口观察重建牌面 → 策略逐帧再决策。「刷后买不买/刷不刷」由策略在下一访问自然表达,flow 零波概念。注册表 terminal/terminal_wait 属性不变(terminal=True 已在册,terminal_wait=0.0)。
2. **商店画面 op 扶正 + 正名**:`CwScreenShop`(现名「买牌」为历史遗留)从无人运行的调试壳变为生产链路真正构造运行的画面 op:生产两路 (外循环 0n 转交与备战显式开店同口 `cw_screen_prep.py::visit_open_shop`、`run_operation` 单跑)统一构造并 run 本 op;发射帧仲裁段 (cw_loop 特殊路径)退役 (第 10 条);「编排壳直调 `run_buy_waves` 裸函数 + pre_entry 替身缝」拆除。构造签名 `(ctx)`。 **正名**(用户裁定):类 → `CwScreenShop`、文件 → `cw_screen_shop.py`、op_name → 「货币战争-商店」;kernel 观察面随命名机械规约同步 (`CwScreenShopObs`/`report_screen_shop_obs`,op-layer §2.1),随落地批语义重命名,测试/文档锚同步。
3. **决策动作 node = 单动作 round_wait 循环**(与单选族节点循环同形,op-layer.md §3 节点循环判据),**全动作统一路径、零特例拦截、零闸**:每轮 = 决策(容器零参读)→(CloseShop 且未观察 → 留痕/熔断,照常执行)→ 守卫 → 注册表派发 execute(**CloseShop 执行位 = 真点击「收起」+ 固定等待 + 自上报清场;波机时代「拦截 + no-op + 编排壳代点」拆除,`CwOpCloseShop` 退役**)→ 簿记(CloseShop 不入 decisions 行契约不变)→ 终结读注册表:非终结 = round_wait;终结(RefreshShop/CloseShop)= round_success 交回。决策零读屏(帧不消费)。
4. **节点行观察归位备战观察域**(用户裁定:节点行是备战画面内容,与关店动作无关):节点行识别**零新增**(`cw_observe_full.py:148` 现役已读并回传 slots),槽序表/台账写点迁**备战 heavy 观察链节点行消费位**(`_write_prep_node_chain` 同帧同点)——交回外循环后,外循环到备战分支即观察,与商店访问零耦合。守卫语义不变(轮位对齐门/环境宽限窗随迁)。
5. **动作 op 零观察识别收敛**:refresh op 删三处读屏与两张真值留证票(free 判定 = Field 值>0,见第 6 条);buy op 删买前裁片;段尾 pixel-diff/SIFT 观测块整体删除。规范依据 = action_ops.md §1 增补 3(用户裁定:动作 op 无论执行前后不做观察识别,欠账清除)。
6. **刷新次数:GameState Field——观察锚定 + 动作扣减 + 发放登记同格**(用户裁定):新建 `gs.free_refresh_left`(剩余语义 Field,§1.4 `*_refresh_left` 家族,商店域**接入**非例外);漏斗复用现役刷新钮读作观察锚定(双态:免费态锚次数/付费域锚 0/判不出跳写,失配走 Field 既有安灯,零手写台账);点击刷新后上报扣减记逻辑态(未观察保守按付费,次数是记账面非决策闸);节点推进与效果 burst 两发放桥改道 Field。效果账本 `free_refresh_balance`/`grant_free_refreshes` 退役。金/牌面快照对账(probe)与免费刷新 proc 留证 flag(ADR-0456 临时通道)退役。
7. **店开防抖删除**:入口观察单次读,读缺交决策前置门响亮失败(`decide_shop_action` 观察帧缺失即抛错,shop.md §2 契约既有)。
8. **帧代次语义**。帧代次 = 观察帧的新鲜度标签:full = 这帧带来整帧新事实,策略本次决策**允许**做一次贵的方向重算(候选阵容重估机器);none = 无新事实,只做便宜单步决策。贵重算本身由既有键守卫限频——每个游戏轮最多真重算一次(flow/README §2.2),full 不等于必然重算。本迭代后每访问入口观察 = full(刷新交回后的重进 = 全新访问);实际行为差异 = 刷新后多一次「允许重算」的机会,由键守卫压住;「续段 none」随段机器消亡。
9. **上报回调腿(用户裁定)**:买牌上报在「获取角色计算完」(落位 + 合成 + 升星腿全毕)后触发购买回调(`on_buy` 新挂点:bump CounterKey.BUY + 购买族分派;flow 层落地门 bump 删除);刷新上报在计数后计算**商店牌随机态**(采样器 = 算法自 `cw_sim_shop.deal_shop` 迁入 kernel `cw_shop_deal.py`,与 sim 发牌同源)经 **`write_logic_rand` 专用通道**写 payload 随机态(observe 覆盖差异 = 预期内,落 logic_rand_outcome 台账,不进失配安灯;2026-09-18「终结跳写 payload 不写」裁决的 payload 半边随之显式收窄)并触发内容条件计数(干旱/供给族仅消费 observation 源,logic_rand 跳拍宁缺勿造)——两执行面同源 = 详设 §2.9。
10. **发射帧受限消费迁策略侧**(用户裁定:策略的事情不进流程框架;规范正本 = flow/README.md §1 决策控制分层铁律):cw_loop 发射帧仲裁段与 spend_gate 通路**退役**,商店访问回归唯一普通路径;受限会话 = 策略侧自限——mandate_v1 读 StrategyState 派生标记(armed ∧ 金超息线),`decide_shop_action` 提案后经谓词检,**拒 = CloseShop 收访问(消费终止语义逐位平移,非改试次优)**,金回线 → CloseShop → StartBattle 正常发射;政策谓词单一源留守 kernel `cw_launch_arbitrage.py::launch_arbitration_gate`,消费方改策略决策入口;段旗 `cw4_launch_spend_visited` 留守(每武装段至多一次受限访问)。= 详设 §2.10。

详设划分:单详设 [details/shop-visit-loop.md](details/shop-visit-loop.md)(主题内聚,无需再分)。跨详设接口契约(总纲钉死):
- 免费刷新次数 Field(`free_refresh_left`)的三写端(观察锚定/动作扣减/两发放桥登记)、未观察口径(None = 保守按付费,次数是记账面非决策闸)与效果账本字段退役 = 详设 §2.3;
- 上报回调腿(买牌 `on_buy` 时点与 CounterKey.BUY 迁移;刷新随机态采样器与 payload 逻辑态写)= 详设 §2.9;
- `CwScreenShop`(正名后)构造签名(无 spend_gate)与两调用点交接面、发射帧受限消费迁策略侧 = 详设 §2.2/§2.10;
- CloseShop 执行位(真点击 + 幂等出口 + 上报清场)归属与边界 = 详设 §2.1;节点行观察归位备战观察域 = 详设 §2.8。
