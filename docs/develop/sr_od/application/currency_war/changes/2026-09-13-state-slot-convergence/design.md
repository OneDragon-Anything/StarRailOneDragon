# 状态收敛与画面 op 规范化 迭代设计(总纲)

## 0. 元信息

- 迭代目标:session goal `goal-80bb36e3`(三阶段:①sim 清理=统一 state 迁移收尾;②画面 op 槽位模型;③画面/动作 op 规范执行收敛)。
- 用户裁定指针(2026-09-13):
  - 固定坑位域三态定长模型(内容/空位/None 告警;商店恒 5 槽;买光店=[空位×5] 合法真值);
  - 备战域「执行域透传」豁免撤销,纳入改造;
  - `LEVEL_UP_FALLBACK` 一类坐标兜底无意义要删(P4,本迭代不实施,另批);
  - 测试精简:锁只锁语义增量,禁为迁移步铺测试面。
- 承接出处:统一 state 迁移 `docs/develop/sr_od/application/currency_war/game_state/r5-migration-plan.md` W6 剩余面;prep 链容器化迭代(`changes/2026-09-12-prep-chain-containerization/`)后续。
- 状态:**草案**(定稿前不派落地批)
- 文档清单:
  - `details/sim-state-switch.md` —— sim 引擎内部模型切容器 + 生产观察链直写 + 转移函数单源化(范围与字段映射,候盘点报告回填)
  - `details/shop-slot-model.md` —— 商店域三态定长词表/读链/容器/投影契约

## 1. 问题与动机

### 现状症状

1. **买光商店崩溃循环**(实机复现):商店面板开着、5 槽全空时,`read_shop_cards` 返回 `[]`,容器 shop 域保持 None,决策前置门 `bs.shop.value is not None` 抛 ValueError(strategies/impl/flow.py:722),op 失败循环。四步根因链与证据见 `.debug/temp/shop_slot_problems.md` P1。
2. **双状态表示 + 双转移函数**(P8/P9):sim 引擎内部模型与生产词汇表焊死在同一旧帧类型 `CwSimFrame`(cw_vocab.py:121);状态转移两份——`simulate(state: CwSimFrame, action)`(cw_vocab.py:933,sim 侧)与 `apply_shop_action_logic(bs: GameState, action)`(cw_game_state.py:1479,live 侧),靠等价锁钉平价。
3. **平行执行账本**(P7):`BuyCardsOutcome`(cw_op_buy_cards.py:412,20 字段)是波批时代的访问报告,容器化后 state 职责已被容器接管,余下账目/遥测/基座消费方未迁,构成 receipts 的平行第二账。
4. **槽位表示违裁定**(P2):商店域读链/词表/容器三层全紧缩,离屏/空位/失读三事实塌缩成同一个 `[]`;ShopPayload「恒 5 张」注释与实现背离(审计 `.debug/temp/audit_slot_domains_r1.md` A 项)。
5. **执行侧判效残留**(P3/C 类 4 族):买牌灰度差判效、拖拽像素验重试、刷新判效半边、部署像素判效族——均既有挂账(T-223/T-268/A8),违「动作 op 只机械执行」终裁。

### 根因归层

- 症状 1/4:**表示层**——紧缩 list 表示与画面固定槽位语义不符(三态缺失),与历史判例「bench 多笔卖出索引漂移=紧缩 list 表示与画面槽位语义不符」同族;
- 症状 2/3:**表示层+流程层**——统一 state 迁移 W6 剩余面未收尾(旧帧在 sim 内核与生产读链的残留);
- 症状 5:**流程层**——T-223 最严读法落地批未执行。

### 解决到哪 / 明确不解决

- 解决:§2 三阶段全部内容(阶段一 W6 真剩余面五项;阶段二 批1/批2/批4;阶段三 判效拆除 4 族)+ P4 坐标兜底族删除(用户 2026-09-13 明令「要删掉」,阶段一收口批 3.9 实施的独立机械批)。
- 明确不解决:死路径指针文档微批(另一文档批);sim 校准层参数精度(设计件既有边界,非本迭代);审计 C-8(cw_op_equip_all 判效面,M 工作量)——不在阶段三 4 族内,其①期望态对账族归属观察侧、②原地重试面挂既有批3 清单,本迭代不动(对抗 F10 点名)。

## 2. 方案

### 系统级变化(读一遍知全貌)

1. **单一状态**:容器 `GameState`(kernel/cw_game_state.py:1927)成为唯一状态类型。sim 引擎内部状态切容器(引擎持自己的容器实例);生产观察链逐域直写容器(观察漏斗不再构造 CwSimFrame 中间层);BuyCardsOutcome 退役(职责归容器+receipts 发射行+缺陷台账)。
2. **单一转移**:动作状态转移收敛为容器版单一函数(现有 `apply_shop_action_logic` 为基座扩展),sim 与 live 共用;`simulate(CwSimFrame)` 随旧帧退役。
3. **三态定长槽位**:固定坑位域识别产物=定长数组,元素三态 content/empty/unknown(unknown=应为内容但识别失败,必携缺陷台账告警);商店先行(批1),bench 槽级 None 态/deployed 容器定长/备战三态化随后(批4)。批4 派单前补「三域三态化」详设小节(依据 = 审计 A 项四域差距表,3.5 完成后成文,iteration-design §1.1 外溢面纪律)。
4. **执行侧零判效**:动作 op 机械执行,落地事实归下一次观察 reconcile(既有规范 T-223 最严读法);拆 4 族,保 5 个合法标注面。
5. **坐标兜底族删除(P4,机械批 3.9)**:非架构变化,单文档方案 = 删常量+消费点兜底支、area 缺失显式失败(round_fail 带 area 名),清单与文件面见 landing 3.9。

### 渠道签名契约(既有封闭集不变,依据=cw_game_state.py:231-325 渠道封闭集 + :13 同步通道声明)

- sim 真值写容器 = obs 族(actor=sim 引擎登记名;现状 `feed_sim_truth` 即 obs 渠道,反转后引擎直写同名纪律);
- 动作投影 = logic_action 族(单一转移函数内部 write_logic);
- 派生规则 = logic_hook 族(不变)。

### 详设划分与跨详设接口契约

| 详设 | 范围 | 状态 |
|---|---|---|
| `details/sim-state-switch.md` | 引擎字段映射(sim 帧字段→容器域)、引擎直写改造面、生产观察链直写改造面、BuyCardsOutcome 消费方迁移(安灯钩子数据源改 receipts/容器派生)、转移函数单源化、cw_game_ports 注解与遥测序列化面跟随 | 草案,字段级映射候盘点报告 `.debug/temp/cwsimframe_migration_inventory.md` 回填 |
| `details/shop-slot-model.md` | ShopSlot 三态词表、ShopPayload.cards 定长 5 契约、读链锚门+亮度判据+unknown 告警、投影口空位置换、13 处消费点适配(含 2 处硬必改)、锁面(定长不变量锁/M1 重推) | 草案,消费点清单以审计 D 项为底 |

**跨详设接口契约(总纲定死,各详设服从)**:

1. 唯一状态类型 = 容器 GameState;本迭代收敛至**活引用零残留**(构造/字段访问/函数签名),CwSimFrame 类本体与残余共享词汇(simulate 定义、state_equips_multiset 帧支)留 W8 切割(r5-plan W8 行);
2. 唯一动作转移入口 = `apply_shop_action_logic` 扩全动作族(定名沿用,居所 cw_game_state.py),增显式结果出参 LogicOutcome(applied/reason/income)承载拒绝语义(对抗 F1);shop-slot-model 的投影口空位置换在该函数内实现;
3. `ShopSlot.kind ∈ {'content','empty','unknown'}`;`ShopPayload.cards` 定长 5;`unknown` 元素必须落缺陷台账(confidence 面),决策消费一律跳过 unknown 槽;
4. 渠道签名封闭集不变(obs/logic_action/logic_hook),sim 引擎写入按上行渠道契约落族。

### 阶段三方案(单文档,总纲内即完整设计)

拆除执行侧判效 4 族,每族的替代承接:

1. BuyCardOp 买后同 rect 灰度差判效(cw_shop_action_ops.py:489-525 + buy_click_ineffective:406-424)→ 拆;兜底职责由批1 后的观察侧 reconcile 承接(下一段入口观察即对账,既有 ADR-0517 决策 1 语义);
2. SellBench 拖 3 次源槽像素验重试(prep_actions.py:149-154)→ 拆重试验证,保留机械拖拽与既有重试上限(框架层,非判效);
3. RefreshShopOp 判效半边(refresh_effective)→ 判效半拆;留证遥测半合法保留(处置表候选 a);
4. CwScreenDeploy 像素判效族(_landing_verdict/_wait_slot_occupied,T-268)→ 拆;L 工作量,部署落地由备战环入口观察对账。

合法面 5 个不拆(收工段防抖自愈重读 cw_op_buy_cards.py:1205/落槽 pixel-diff 纯留证/登记件落地门批3a 过渡/刷前按钮真值免费闸输入/收工未识别卡钩子)——依据=审计 C 类合法标注面清单(用户裁决 2026-08-24 在册 + §6.5 申报)。
