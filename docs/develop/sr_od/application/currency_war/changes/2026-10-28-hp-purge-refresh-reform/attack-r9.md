# hp-purge-refresh-reform 第 9 轮收敛终验报告

- 验证性质：第 9 轮收敛终验（极小范围，非全量轮）——只验证第 8 轮修复面 + 全篇行段/词表一致性终核。
- 复查对象：design.md、details/hp-purge.md、details/refresh-chain.md、details/shop-buy-reform.md、landing.md、README.md（前八轮报告 attack-r1~r8 按纪律未读）。
- 证据面：文档比对 + 代码直调（shop.py / statefn/lambda_death.py / statefn/predicates.py / cw_investments.py / sr-od-test/test_levelup_prob_axis.py）+ 全篇关键词扫描。
- **结论：零发现（0 项）。第 8 轮修复面全部验证通过，六文档行段/词表口径一致，触发定稿。**

## 复查面清单

### 1. shop.py 行段六处一致 + 代码直调核对 —— 通过

六处文档位均为总纲口径，零分叉：

| 位置 | 行段表述 | 与总纲一致 |
|---|---|---|
| design §2.1 | refresh-chain = :1-233 + :267-315 + :1962-2080；shop-buy-reform = :234-266 + :316-1961；carve-out :373/:996/:327 归 hp-purge，无等值锁义务 | ✓ |
| details/refresh-chain.md 边界 | :1-233（含 ρ 别名）+ :267-315 + :1962-2080；:234-266 归 shop-buy-reform | ✓ |
| details/shop-buy-reform.md 边界 | :234-266 + :316-1961；发射段归 refresh-chain | ✓ |
| landing 3.2 文件面 | shop.py:1-233 + shop.py:267-315 + shop.py:1962-2080 | ✓ |
| landing 3.3 文件面 | shop.py:234-266 + shop.py:316-1961 | ✓ |
| details/hp-purge.md carve-out | 「唯 carve-out 三行见总纲 §2.1」（:327 见 A-9 单列、:373/:996 见 R-3 删除面补全，两行无 H 值流、无等值锁义务） | ✓ |

代码直调核对（`strategies/impl/mandate_v1/shop.py`，实测全文件 2080 行）：

- `_merge_pair_names` 定义 :234-264（段 :234-266 含尾空行）；`p92_seat_recoverable` 定义 :267-315——两函数边界与文档逐行吻合；
- 头部段止于 :233（`_r2_card_reserve` ρ 别名定义于 :221，与 refresh-chain「shop.py:221」锚一致）；
- 买面段 :316-1961（M6 块 :1543-1616 实测吻合；:1961 为段尾空行）；
- 刷新发射段 :1962-2080：段首注释 :1962、免费分支 :1963-1971、整级预留分支 :1988-1989、r2_budget 消费 :1994、P92 装配段 :1996-2054、计数键 `p92_no_buy_refresh_blocked` :2062-2063 与 `must_spend_r1_no_buy_blocked` :2064-2065——全部与文档锚逐行吻合；
- carve-out 三行实名核验：:327 = refresh_ev_budget 归零分支注释行、:373 = no_target_arms hub_names docstring 引用行、:996 = hub_names=frozenset() 字面空集调用行——均无 H（血预算视界）值流，「无两消费位等值锁义务」成立。

### 2. B-12 λ 表血带维三处一致 + 代码直调核对 —— 通过

三处文档位语义逐一相同（仅删零消费子集 make_key/hp_band 内部量/HP_BAND_MID；HP_BAND_NEAR_DEATH 保留，为 p1/p2_blood_floor 阈值单一源）：

- details/hp-purge.md §2 例外行（B-12/R-6 例外段）✓
- design §2.1 hp-purge 独占文件面「statefn/lambda_death.py（B-12 零消费子集删除；HP_BAND_NEAR_DEATH 保留）」✓
- landing 3.1 文件面「statefn/lambda_death.py（B-12 零消费子集，HP_BAND_NEAR_DEATH 保留）」✓

代码直调核对：

- `statefn/lambda_death.py`：`HP_BAND_NEAR_DEATH` :36、`HP_BAND_MID` :37、`hp_band` :121-130、`make_key` :133-146——与申报的删/留切分完全对应；
- 零消费子集实核：HP_BAND_MID 仅被模块内 hp_band(:128) 消费、hp_band 仅被模块内 make_key(:142) 消费、make_key 在 src 全仓无外部调用位（grep 实证仅定义与 `__all__`）；
- `statefn/predicates.py`：`p1_blood_floor`(:125)/`p2_blood_floor`(:156) 消费 HP_BAND_NEAR_DEATH(:144/:153/:176/:185)，docstring 明示「阈值常量单一源」；
- `sr-od-test/.../test_levelup_prob_axis.py` :406 起正是 `from ...lambda_death import HP_BAND_NEAR_DEATH` 断言块（边界随常量走）——文档锚 :406 逐行吻合。

### 3. 词表终核 —— 通过

（单一源 = details/hp-purge.md §6）

- `levelup_blood_gate_defer`、`HP_BAND_MID` 均在清零词表 ✓（后者附 B-12 处置自洽：保留子集 HP_BAND_NEAR_DEATH 不在词表）；
- `decision_hp`、`blood_xp_full_clicks`、`blood_xp_mode` 均在「不过扫符号」申报行，各附保留依据（R-1 经验批支付门读口 / 击数算术保留 / B-19「改」类随 R-1 联动核）✓；
- 清零词表无 `p1_blood_floor`、无 `refresh_ev_budget`（两者在不过扫行：R-7 保留观测谓词 / A-9 只删归零支非删函数）、无裸 `handoff_` 前缀（申报 = 仅清查件 B-4 明列投影参数精确列名，不扫裸前缀）✓。

### 4. 过程叙事零残留 —— 通过

全篇（六文档）扫描「对抗 H / 对抗 B / 攻击 G / A3 收编 / G2 撤稿 / 原解锁支撤稿 / 曾两度反复 / 待决约束 / 经对抗审确认」：全部零命中。

「对抗审」子串共 2 处命中，均非过程叙事、不计发现：

- design.md §0 状态行「对抗审中」、README.md 进度行「迭代设计:对抗审中」——均为迭代生命周期状态位（元信息/进度元数据，非正文叙事），当前时点语义准确，定稿时随状态翻转更新，无需本轮修改。

### 5. landing 3.1 contracts.py 列表核对 —— 通过

- 3.1 的 contracts.py 修改面 = :243-246（hp 行级）唯一；:88-106/:166-171 仅出现在「守卫面经直调不读 H——无需改码」申报性注记中（landing 3.1 文件面括注），与 hp-purge §3 处置细目②、design §2.1（未将其列为 3.1 动面）三方一致——无需改码面语义成立，列表无改码义务残留。

### 6. 全篇旧口径/旧行段/编号引用抽查 —— 通过

grep「1-249 / 250-1961 / ≈L1600 / 三布尔 / G3 补全 / 3.3 回归锁 / test_cw_lock_path_obs_keys」：全篇零命中（现行发射条件口径 = 两布尔合取，design §2.1 与 refresh-chain §5 一致）。

「整条退役」3 处命中、「场上非线内件」2 处命中，均为已裁决内容的**否定/收窄申报**而非残留主张，不计发现：

- design §3 R-3 行「『整条退役』实核不可行」、hp-purge §3/关键取舍同口径——三处共享同一机器事实（k_empty_window_fallback 三处生产消费位 + P1 空窗防环职责），跨文档一致；
- refresh-chain §1 席位腿收窄申报「裁定原文的腾位腿含『场上非线内件』，本设计收窄为备战席燃料」及访问间隙归属说明——为裁定 #7 的显式申报段，非旧主张残留。

### 附带抽查（超清单的锚点抽核，均吻合）

- cw_investments.py:473 =「高效决策」`free_refresh_burst=9999`（shop-buy-reform 现状锚）；:1216 = `blood_xp_mode` 定义行（design §2.1 carve-out 与 landing 3.1 引用）；
- 六文档间交叉引用（hp-purge-appendix.md 为 3.1 开工前生成件、README/设计文档清单四处同口径；M6 :1543-1616 在 design/shop-buy-reform/landing 三处一致）零漂移。

## 发现清单

**零发现。** 第 8 轮修复面 6 项全部验证通过，无严重度分布可报。定稿触发条件成立。

## 复核限制声明

- 前八轮报告 attack-r1~r8.md 按任务纪律未读，本轮判断全部基于六文档现状与代码直调实证；
- 全篇扫描含 `docs/` 目录层的关键词检索，均按六文档范围分组执行（回避禁读文件）；
- landing 3.1 第 4 项的「:88-106/:166-171」以注记形态存在于「无需改码」申报中——本报告判定其语义为申报而非改码义务（依据 = hp-purge §3②、design §2.1 未列其入 3.1 动面，三方一致），如定稿人认为该注记亦应从 landing 文件面行内移除，属定稿时点的一次性文字收敛，不构成设计缺陷。
