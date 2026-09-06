# ADR-0561 sim 商店动作执行切 simulate 单一源（Buy/SellBench 切源 + 保留面申报）

## Status

accepted（2026-09-06，sim 体系全面 review 报告 §A 根因 1 的 P0 处置；实施批=「sim 商店动作单一源」批）

## 背景

sim 体系全面 review（`.debug/temp/currency_war/sim_review/报告.md` §0/§A）实锤:sim 引擎
（`sim/engine_p1.py`）对商店四动作（Buy/LevelUp/Refresh/SellBench）**内联重实现**,
与 live 投影单一源 `kernel/cw_state.simulate` 双源,§A 13 条分歧中多条（槽匹配判据/
SellBench expect 校验/SellBench 装备回收）同根于此。最重 = SellBench 无装备回收
（修复前 sim 卖带装件装备凭空消失,C6 装备守恒破）。

## 决策

1. **BuyCard / SellBench 执行切 `_simulate_state` 单一源**（live 投影同款）:状态变更
  （金/店槽下架/合成连锁/满栏合成买/装备守恒）全在 simulate 内部;引擎只余预检披露
  （满栏非合成拒买计数、幻影再买跳过——判定函数与 simulate 同源,不构成第二套语义）
  与池回填/池扣减、经济记账、账本转录。XP 记账收拢为引擎侧单一记账点（买/升各一次
  +XP_PER_BUY,数值逐位不变）。
2. **LevelUp / RefreshShop 保留引擎侧实现（sim-only 已知差异,显式申报不禁默）**:
   - LevelUp:LEVEL_CAP=9 冻结守卫 + 轮末结转升级是引擎架构;切 simulate 会连带引入
     「cap10 + 攒够即升即时升级」双重行为变更,违本批「切源不改行为」零漂移门。
     §A #6（9vs10）只登记不顺手改（放开前置在案 = 追级虚高治理 + 池指纹重锚,
     `engine_p1.py` LEVEL_CAP 注释）。花费载体统一为 `action.cost`（#5 的载体面;
     值仍 4 = 兜底,真值接入归 sim-wiring P2 件）。
   - RefreshShop:simulate 有 RefreshShop 分支但只扣金不重采样(落地审勘误 2026-09-06,cw_state.py:1630-1632;重采样需引擎层牌池)——切源会丢免费刷注入/重采样/break-redecide 三重行为,保留决策仍成立;免费刷额度注入
     为 sim-only 行为（§A #9,注入局刷新结论不可外推,已在案）;刷后 break-redecide
     为 sim 正确侧（§A #1,分歧在 live 侧,修复批在飞）。
3. **SellBench 装备回收 = 已申报行为修正**（§A #7）:切源后卖带装件装备回 owned 池
  （simulate 内 `s.equips.extend`),C6 守恒对账覆盖 sim 域。零漂移对拍
  （同 seed 同池 60 局,`.debug/temp/currency_war/sim_p0/`）实证:默认 P1 批轨迹
  逐位恒等(带装卖出在默认批不可达),行为修正用桩场景正向验证(卖出轮 unworn_equips+1)。
4. **防回漂锁**:新增 `sr-od-test/.../test_cw_sim_shop_single_source.py` 三锁
  （spy 结构锁:Buy/SellBench 必经 simulate;桩行为锁:带装卖出装备回池;grep 锁:
  禁内联特征式回潜）。

## Considered Options

- 四动作全量切 simulate（含 LevelUp/RefreshShop)——弃:LevelUp 切源引入升级时机+cap
  双变更、RefreshShop 无 simulate 分支,均破零漂移门;保留面显式申报,归 LEVEL_CAP
  行为变更批再收口。
- 只单修 SellBench 装备回收（报告建议 #2 备选）——弃:双源根因仍在,分歧继续逐点对;
  本批按报告 #1 主案切源,#2 随切源自动达成。
- 保持双源 + 逐分歧补丁——弃:每处分歧两套代码逐点对,漂移面随演进扩大(review §A 根因 1)。

## 影响

- `sim/engine_p1.py` 商店段:Buy/SellBench 分支重写为调 `_simulate_state` + 转录;
  删除内联合成/槽消费/卖出清理实现。
- §A 13 条分歧消解逐条对账:

  | # | 分歧 | 处置 |
  |---|---|---|
  | 1 | 刷新终结语义 | 面外(分歧在 live 侧,修复批在飞;sim 侧保留) |
  | 2 | BuyCard 执行成功假设 | 保留(引擎头注既有申报:sim 决策面,不模拟执行缺口) |
  | 3 | BuyCard 槽消费判据双源 | 随单一源消解(x 槽位口径;引擎残留兜底只辖披露/跳过) |
  | 4 | BuyCard XP 记账双源 | 消解(XP 收拢引擎单点,数值逐位不变,零漂移) |
  | 5 | LevelUp 花费=4 硬编码 | 载体统一(读 action.cost;值仍 4,真值接入归 sim-wiring P2) |
  | 6 | LEVEL_CAP 9 vs 10 | 保留+登记(切源连带 cap10+即时升级双变更破零漂移门;放开前置在案) |
  | 7 | SellBench 无装备回收 | **行为修正**(随单一源回收,C6 守恒覆盖 sim 域;见决策 3) |
  | 8 | SellBench 无 expect 校验 | 随单一源消解(stale_proposal 归位;sim 同帧语义不可达,纯防线) |
  | 9 | 免费刷额度 sim-only | 保留(RefreshShop 不入 simulate,重采样需引擎层牌池;申报已在案) |
  | 10-13 | 补部署 skip 分支/收球席位/装备效果/CompTransaction 缺席 | 面外(非商店四动作,原判定不变) |
- 回归:L1 全量 2751 过（唯一红 = test_cw_shop_refresh.py live 侧刷新面,系并行
  live 修复批在飞域,与本批文件面无交集——该测试不 import engine_p1,批前已红）。
- sim/live 对拍未做:按批任务书,两侧都收口后由编排者统一安排。
