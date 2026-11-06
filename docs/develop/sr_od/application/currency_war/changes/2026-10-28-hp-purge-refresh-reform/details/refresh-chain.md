# 刷新链三组件改革（详设）

## 问题与约束

- 边界：本篇管 `criteria/refresh.py` 全文件 + `shop.py` 头部段（:1-233，含 ρ 别名）+ `shop.py` p92 删除段（:267-315）+ 刷新发射/收工段（:1962-2080，行段契约见 landing 3.2 文件面）+ 危机不变式全链 + R 族死码。合成腿谓词段（:234-266）归 shop-buy-reform（W5 矩阵同批重写），本篇消费同一谓词。资金序声明（升级推迟期不设解锁支）见 §2 末条与总纲 §2.0 第 3 条。
- 接口契约（总纲 §2.1）：「席可腾」真值源 = `fuel_sell_candidates` 现役资格面（只消费不改本体）；「停留目标」单一源 = `stay_target_of`；hp-purge 不得改变本篇产出的刷新发射布尔语义。
- 现状锚：刷新发射链现役实况 = 查表判据 → R2 预算门（含死分支）→ P92 通道枚举（`shop.py:1975-2063`，含计数键）；文档声称的六道门与代码不符（23 号稿漂移，W8 项）。

## 方案

### 1. 判据组件：三段式查表 + 目标可买条件（裁定 #7）

`refresh_warranted` 返回 True 的条件在现行三分派之上**追加**目标可买检查（合取）：

```
目标可买 ⟺ 有空位(bench_free ≥ 1)
         ∨ 当前停留目标「买一张即可触发同名同星合成」（合成腿——按机制全集口径，见下）
         ∨ fuel_sell_candidates 资格面非空（可卖备战席一件燃料腾出位）
```

- **合成腿 = 机制全集口径，非现行机器口径**：merge_mechanics §2 机制 = 「同名同星凑满 3 即合成」，由此可触发合成的持有形态包括——恰 2 张 1★（买第 3 张 → 2★）、场上 2★ + 备战 1★×2（买第 3 张 1★ → 合成第 2 个 2★，向 3★ 推进）、2★×2 + 直出 2★ 卡（买即合成 3★）等；现行 `_merge_pair_names`（恰 2 张全 1★ 单跳形态，`shop.py:234-264`）只是机器实现子集，其 docstring 自身已警示误杀风险。实现 = 合成腿谓词按机制全集重写（落点 = shop-buy-reform 文件面 :234-266，与 W5 买臂矩阵同批），本篇消费同一谓词——单一源，禁第二实现。

- 拒因键定义：三腿全无时 `refresh_warranted` 返回拒因 `target_unbuyable`（观测面判读归因用，替代原 P92 计数键职能）。
- **裁定 #7 席位腿收窄申报**：裁定原文的腾位腿含「场上非线内件」，本设计收窄为备战席燃料——工程事实：卖场上件释放的是**上阵位**，不释放买卡所需的**备战席位**（备战 M4 腾位 = bench-only 燃料，23 号稿收缩形态），「场上件腾位」腿在席位维不成立，等效于静默裁掉该腿并在此申报；场上件的战力让位仍由部署置换面（M1/部署换人）管辖，与本条件正交。

- **席位腿口径 = 备战席燃料 only**：`fuel_sell_candidates` 为 bench-only 真值源，店内禁卖场上件（23 号稿收缩形态：满席腾位 = 关店走备战 M4）——「场上非线内件腾位」发生在**访问间隙**（关店 → 备战腾位 → 重进后席位已空，目标可买自然转真），不在本条件内。深席堵恢复 = 关店-腾位-重进链，非店内条件。

- 实现落点：`refresh_warranted` 锁定后分支（`refresh.py:97-108`）②③支返回前追加合取；未锁窗口分支同加（候选缺件集任一成员满足即可）。
- 席位真值消费：`fuel_sell_candidates`（现役单一源，本篇复用同参装配，禁第二实现）；合成分支消费 `_merge_pair_names`（`shop.py:234` 现役谓词）∩ 义务面。
- **P92 整门删除**：`all_channel_buy_exists`（`refresh.py:282-378`）+ 装配段（`shop.py:1996-2054`，计数键 :2062-2063）+ 契约行（`contracts.py:283`）+ 计数键 `p92_no_buy_refresh_blocked` 与 `must_spend_r1_no_buy_blocked`（`shop.py:2064-2065`，随门结构消失；对照 `must_spend_r1_budget_fail` 在 r2 拒绝域，保留）及消费端 + `math_proofs.md` P92 挂起命题行 + `01_math_framework.md:194` 钩子行 + `11_shop_decisions.md:110`（§3.1）/`23_shop_screen.md` 引用段 + 测试面 = `test_seat_recoverable_narrow.py`（改造为锁目标可买席位腿）+ `test_sim_levelup_cycle.py:44`（键域清单）——裁定 #7，抽象枚举被目标中心单条件替代；追星误拦缺陷（追查件缺陷 #2）顺带消除。`p92_seat_recoverable`（`shop.py:267`）符号删除（唯一消费位随装配段），席位腿实现 = `fuel_sell_candidates` 直调（同参装配形态迁入目标可买实现）。验收词：`all_channel_buy_exists|p92_no_buy_refresh_blocked|must_spend_r1_no_buy_blocked|p92_seat_recoverable|P92`。
- 已知余量（裁定 #7 用户接受）：极端死态白刷的下界 = 金线闸预留（终态语义自洽：金线闸停刷，不穿透利息线）——席位腿收窄后该死态需「席满 + 零备战燃料 + 不可合成」三条件并存，压牌库让位（shop-buy-reform 详设 §2）落地后几乎不可构造。

### 2. 金线闸组件：新算式（裁定 #5/#6）

```
预留 = saturation_line(cap_resolved) + 当前停留目标注册表卡价
放行 ⟺ 当前金 − 预留 ≥ 刷新价(refresh_cost_effective)
```

- **ρ 重定义**：`r2_card_reserve`（`criteria/refresh.py:236` 单一源）从「合格集最低费卡价」改为 `stay_target_of(state)` 的 `CHARACTERS cost`；shop.py `_r2_card_reserve`（`shop.py:221`）别名重导出随改。行为差 = 已 2★ 追 3★ 目标（旧口径被「无 2★」过滤排除）现按其卡价预留（3 费 → 预留 3）。**未锁窗口取值**：未锁分支 stay_target 恒空 → ρ = 0（金线 = g* + 刷价；未锁窗口刷新目标 = 候选缺件集，无单一目标价，如实声明）——锁定支 ρ 恒有值（目标空帧判据先拒），两分支口径分行声明，禁混引。连带描述文本同步 = `contracts.py:279-282`（P54-r2-interest-floor §② 描述）与 `criteria/__init__.py:71-73`。
- **整级预留分支删除**：`shop.py:1988-1989`（`GATE_GOLD_SHORT → _reserve += 批`）+ 注释块该支描述（:1981-1986 内）。死因 = 升级概率带单判据后升级触发态与刷新放行态互斥（裁定 #5）。⚠ `_up_clicks/_up_cost` 本体不删——升级意图出口发射计算仍消费（可达面）。验收 = diff 核对该两行消失（非 grep）。
- **ρ 实费档口径**：ρ 取 `stay_target_of` 返回的 `target[2]` **当前实费档**（resolved 口径，含变费卡随档——与带判据同一目标元组，变费帧随档分叉为设计内行为），非注册表基价直查。
- **席位腿装配参数流**：席位腿 = `fuel_sell_candidates` 直调（同参装配 = `sell_exclusions(channel='m4_fuel')` 形态）；`counters`/`dedup` 参数由调用方（shop.py 刷新提案点）传入——语义钉死、函数签名实现批定。
- **资金序声明（升级推迟期）**：升级判据命中但资金线推迟（凑金在途/穷尽）时，刷新判据①支**维持拒绝**、不设解锁支——解锁支会在凑金在途帧放行刷，而整级预留腿已删，刷新烧凑金 → 「金被刷到下界、升级永久 defer」饿死环；资金线推迟态 = 攒金收敛态（每轮节点收入，金上涨吃息；凑金域唯一出辖 = 终局域 ALL IN，`11_shop_decisions.md` §2.1），非死锁。原 W2 动机（hp 闸致永久双闭）已被 hp 删除消灭。
- **R 族死码清理（W10）**：删 `r0_stop`（`refresh.py:22`）/`r1_start`（`:140`）零调用壳及其 contracts 注册（`contracts.py:252/:255`）与 `criteria/__init__.py` 注册行（:60 `r0_stop` / :62 `r1_start` / :65 `r1_commitment_account`——R1 路径总账残留，一并清）、`refresh.py:301` 注释引用；`r2_budget` 保留（`shop.py:1994` 消费）。P40/P47/P54 命题行按剩余消费面重锚或删（P40 EV 面消费位已死）。验收词：`r0_stop|r1_start|r1_commitment_account`。

### 3. 危机不变式删除（裁定 #4）

- 判据函数 `crisis_refresh_invariant`（`refresh.py:160`）、序位声明（`mandate.py:1078-1079`）、contracts（`contracts.py:273`、`criteria/__init__.py:76`）；旧层残件：`crisis_invariant_lane`/`crisis_overflow`/`authorize_release_refresh` 符号在现役代码**零定义**，仅三处注释停用史引用（`economy_cycle.py:24/:233`、`telemetry/schema.py:500`）——删除面 = 这三处注释残留；
- 证明侧：`math_proofs.md` P36 行 + `proofs/p36-crisis-firepower-floor.md` 整文件；P36-a′/P36-b/P36-c 同族（全部以 hp 为索引）一并删；
- 引用清理：`23_shop_screen.md:10`、`14_p1_consume_arms.md`（N5 行）、`10_prep_decisions.md:199`、`proofs/p37-late-xp-conversion-cost.md:188`、`proofs/出口生存余量设计批-命题与因果链.md:112/:238`（P92 节）、`19_reinforce_channel_and_survival_discount.md:29`、`20_large_balance_must_spend.md:77` 与 `proofs/p53:12/:144`（r1_commitment_account 残留）、`01_math_framework.md:88/:119`（P36 行）；
- 验收词：`crisis_refresh_invariant|crisis_invariant_lane|crisis_overflow|authorize_release_refresh|危机不变式|危机火力|P36`。

### 4. 免费刷新分支纳入判据（W11 支，与 shop-buy-reform 详设 §3 分工）

- 本篇：免费分支（`shop.py:1963-1971`）**追加目标可买检查**（合取；金线不适用——免费）；拒绝时按 §5 记忆语义关店。
- 负结果记忆本体归 shop-buy-reform 详设 §3（会话状态载体在买面段文件面）。

### 5. 发射段终态（实现者验收对照用）

```
每商店帧：
  upgrade_intent_exit()                    # 现行，不变
  六序买入/M4 腾位…                        # 现行，shop-buy-reform 管辖
  刷新提案：
    w  = refresh_warranted(gs, session)    # 三段式 + 目标可买（资金序：升级推迟期①支维持拒绝，无解锁支）
    b  = r2_budget(gold, g* + stay_target_cost, 刷价)
    免费分支 = free_refresh_left > 0 且 目标可买
    w ∧ b  → RefreshShop（付费）           # P92 门已删
    免费分支 → RefreshShop（cost=0）
    否则   → CloseShop + 负结果记忆标记    # shop-buy-reform §3
```

- 单帧测试固化清单（sr-od-test，docstring 引本迭代 design.md）：①带内+金够+席可腾 → 发射；②已 2★ 追 3★ 目标帧 ρ = 其卡价；③席满+可合成 → 发射；④席满+零燃料+不可合成 → 拒（关店）；⑤升级推迟帧（gold_short）刷新维持拒绝（资金序）；⑥免费分支零收获不刷；⑦死码符号零残留（grep 断言）。

## 关键取舍

- **目标可买条件的席位分支 = 三态并集而非精确模拟**：精确模拟「刷出后能否真买到」需重采样预测，不可算；并集语义 = 存在任一腾位/合成/空位路径即放行，浪费面 = 放行后目标没刷出（本来就是搜牌成本），不产生新浪费。依据 = 追查件 §1.4（P92 误拦三帧）与裁定 #7。
- **P92 六通道枚举备选 = 保留修分支（原 W3 形态）**：放弃。依据 = 裁定 #7 用户裁定 + 通道全集视角正是误拦根源（追查件缺陷 #2 归因段）。
- **解锁支备选 = 保留并配升级批预留（备选 b）**：放弃。理由：预留腿恢复 = 推翻裁定 #5；不恢复则饿死环成立——两难只能靠撤解锁支解开，资金序定为「升级优先于刷新」（攒金收敛态）。
