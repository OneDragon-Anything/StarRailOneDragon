# ADR-0325:S3 同星豁免——合并买入的容量例外(H3 口径)

- 状态:accepted(W52 批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `cw_state.py` 的
  `will_merge_on_buy`(单一源)+ `decision_v2/arbiter.py` 的
  `bench_capacity` 豁免 + `decision_v2/candidates.py` 的
  `will_merge` 生成侧 + `cw_state.py::simulate` 的合并买入执行侧。
  W52 执行序第 2 步。

## 背景(现象与根因)

层4 `bench_capacity` 需要给「买第 3 份同名 1★ 触发 3合1 合成」的
买候选容量豁免(合成净腾 1 槽:占位 +1、合成清 2 = 净 −1,满员也可
买)。但**豁免判据**若用星级加权副本数(旧 `candidates.will_merge`
的 `star_weighted_copies == 2 and card.star == 1`),会把「1 个 2★
(加权 2)+ 买第 3 张 1★」误标为 merge——`_merge_bench` 按
**(char_id, star) 同星分组**(cw_state),2★ 与 1★ 不同组,买入不
合成、bench 净 +1 → 满员误豁免 = 溢出。

**根在哪一层**:判定层——豁免判据与合并机制的**分组键口径不一致**
(加权计数 vs 同星计数)。

## 决策

1. 豁免判据(H3,r2)=「**同名同 1★ 计数 == 2 且待买为 1★**」,与
   `_merge_bench` 分组键同口径——`cw_state.will_merge_on_buy`
   单一源,三处消费(生成侧 `candidates.will_merge` / 仲裁侧
   `bench_capacity` 豁免 / 执行侧 `simulate` 满员合并买入)。
2. **合并买入在满员时也通**:simulate 的 BuyCard 分支在
   `bench_place` 失败(满员)且 `will_merge_on_buy` 时,新卡临时挂
   槽位表尾部参与 `_merge_bench`(合成后恒被消费置 None),再截回
   定长 9——新卡不占独立槽(游戏语义:买第 3 份即合成,不落备战槽)。
   非 merge 买满员仍 no-op(金不扣、牌不下架)。
3. 非 merge(含 1× 2★ 加权 2 的误标例)满员仍按占用计数拒。

## Considered Options

- 加权计数豁免(旧,否决):1× 2★ 误豁免 → 满员溢出(净 +1)。
- 同星计数豁免(采纳):与合并分组键同口径,豁免只给真 merge。
- 不豁免(否决):bench 满时买第 3 份被拒 → 3合1 在满员态结构性
  不可达(合成腾槽正反馈断裂)。

## 影响面

- 测试:`test_cw_w52_remediation.py` 的 S3 四锁(正向 9/9 豁免 /
  反例 2★ 加权误标仍拒 / 反例非 merge 仍拒 / 生成侧镜像 / 执行侧
  净 −1)。
- 行为变化:bench 9/9 + 真 merge 买由拒改采纳(净 −1,满员合成)——
  **意图内**(S3 规则修正);加权误标例仍拒——**意图内**(误标修正)。

