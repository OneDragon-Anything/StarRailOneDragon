# ADR-0528:必花域内停付线让位 + 息线门整门降排序 + R1 域内残形切分线

日期:2026-09-06。状态:已实施(20 号稿 v2.1 落码批,7.5 接管债两行随批记录)。
授权文号:01 §2 玩家裁定层(20 号稿 §1 登记,要点转述,原文以编排者登记为准):
「濒死绝对不是问题;无论什么 hp,金这么多都是要花的;不要搞错重点。」

## 裁决一:必花域内停付线(p1/p2_levelup_stop_hp)让位

- **裁定原文引用**:「无论什么 hp,金这么多都是要花的」(20 号稿 §1)。
- **让位辖域 = 必花域**(g > G_must = 10 × cap_resolved_of_session,
  `cw_economy.in_must_spend_zone` 单一源判定):域内 L3 升级出口
  (LevelUpShop,auth_basis `m3_batch:must_spend`)不消费
  level_spend_blocked/crisis 分支——停付线不否决 L3。
- **域外照旧**:非必花帧停付线原语义零变化(既有 crisis_level_spend_defer
  锁零回退为证)。
- **与 00 §3 硬闸门两件授权的对账**:停付线是已授权 hp 消费点的
  **辖域收窄**(必花域内不辖),非新增 hp 消费判据;血线硬地板 ≤15 族
  (00 §4 挂账)维持原挂账不动,两域并存不双计(20 号稿 §7.2)。

## 裁决二:必花域内息线门整门降为排序信号

- **范围 = 整门**(20 号稿 v2.1 应修-1,非只豁免息损项):arm2 守息门 /
  R1 的 g*/L 承诺账(r1_commitment_account 的 account 侧)/ EV 买面
  ev_buy_veto 等期望核算类,必花域内一律降为排序信号——负期望出口排
  选择序末位仍可消费。依据:①裁定字面无「花但须保值」限定;②息线门与
  U_L 同为期望核算类,阻断-1 已裁该类域内降排序,单留息线门作否决 =
  同类不同治;③(i) 类资格硬闸不动,无无界支出。
- **R1 域内残形切分线**:可负担性(r2_budget)留资格硬闸;g*/L 账
  (account_over_budget)降期望核算;**合格集空守卫
  (no_chaseable_member,(ii) 类 fail-closed)不在此列,域内照旧**。
- **域外照旧**:非必花帧上述门原语义零变化(既有 R1 三档行为锁与
  account_over_budget 分键的域外帧全部零回退为证)。

## 落码落点(消费位/分键)

- 判定单一源:`cw_economy.in_must_spend_zone`(买断制 cap=0 出辖恒 False);
- L2:`shop.py` 出口③ 第二触发源(∨ 合并,`must_spend_l2_trigger` 分键,
  锁线前提共用 17 号稿 D 支);
- L3:`shop.py` 决策末位(分层序 L1/L2 之后)LevelUpShop
  (`auth_basis='m3_batch:must_spend'`),拒因分键 `level_cap`/
  `batch_unaffordable`;
- R1:shop.py R1 段 `account_over_budget` 判定域内置 True(可负担性
  r2_budget 承载);
- EV:`shop.py` EV pass 域内 veto 候选降排序末位仍可消费。

## 锁

`test_cw_must_spend_zone.py`(8 条:判定边界/买断制出辖/L2 触发+分键/
域外零变化对照/白名单①店空/L3 消费/L3 cap 拒/R1 切分线+守卫照旧)
+ `test_cw4_mandate_v1.py` R196 三锁语义更新(影子维持声明撤销)。
