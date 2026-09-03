# dd-034 断供供给确认加速/合并完成买入/危机带经验让位(第 7 局复盘三候选)

## 背景

实机局复盘 g_20260904_054904(第 7 局,loss@P2r1)§八候选 1-3:①爻光(仙舟)在 p1r3/r4/r6 三期在店被 non_line 拒,配方对滞留断供线直到 r7 驱逐才重推,冻结窗三战 -9/-11/-28;②p2r1 千冶·刃 合并件(第三张买入即 2★)2g 在店被 owned 拒后无人买,同帧 36g 买经验=优先级倒置;③p2r1 hp=1 败即死帧,spend_mode='level' 的 m3_batch 批授权把 67% 金转为本帧零收益经验。修复批 REPORT = `.debug/temp/currency_war/strategy_iter_7f/REPORT.md`。

## 决策

### 候选① 线重推供给确认加速(kernel/cw_intention)

- **机制**:R3 断供驱逐只看现任方向体系的「连续无件轮数」,方向外体系的在店供给证据(连续 K 轮体系件在售)不参与——「店在供给、只是绕开现任方向」这一反驳证据丢失,方向切换被拖到满阈值。
- **修法**:`_update_pair_drought` 每轮对四体系全集更新 `shop_supply_streak`(有店轮成员在店 +1/不在清零;无店轮冻结,与 LineTrack 冻结语义同款);方向外体系 streak ≥ `PAIR_SUPPLY_CONFIRM_ROUNDS` = ⌊`PAIR_DROUGHT_EVICT_ROUNDS`/2⌋=2 时,本轮驱逐门槛减半。零新自由参数:确认证据是出现观测(似然 1/轮),缺席证据按 (1−q)<1/轮 累积,同等证据强度所需出现轮数少于缺席轮数,离散化取缺席阈值一半(常数从驱逐阈值派生)。驱逐仍经 un-evict 可逆(经济冻结批语义不破),误加速损害被可逆性兜住。
- 遥测:`IntentionState.shop_supply_streak` 随 serialize_intention 全量落账;驱逐事件带 `:accel` 标签(同轮可能被 pair 派生事件覆写,判读以 streak+evicted 同帧为准)。

### 候选② 升星合并完成买入(cw4/shop.py M2b)

- **机制**:M2 只买「未持有」成员,已持 2 张同名同星 1★ 的成员在店被 owned 拒——第三张(合成完成件)无任何购买通道;dd-032 的 merge_completion_exempt 只豁免 decision_v2 非正分门,cw4 执行面缺位。
- **修法**:M2b 义务通道(k_members 辖域):已持 2 张同名同星 1★、无 2★ 成件、第三张在店 affordable 且 bench_free ≥1 ⇒ `BuyCard(reason='m2_merge_completion')`。序位=M2 缺口买入后(P20 体系激活>散件升星)、dominance/M6(1★ 囤积面)前(P30 ①星级阶梯;完成价值评分维构造性零增量,dd-032 同款判读);义务通道不走息律门([41] 同 M2)。`shop_unbought_reasons` 拒因细分 merge_unaffordable/merge_bench_full(判读可归因,禁退回中性 owned)。零新自由参数:2 张持有=游戏合成规则,bench/金=硬可行性。
- 代价边界(如实申报):席满帧 M4 先腾席后 M2b 可用空席——腾席动机是缺口件,若缺口件不在店,腾出的席被 M2b 消费;合并 2★ 目标件价值高于零重叠燃料件,方向为正,不设附加门。

### 候选③ 危机带经验授权让位(cw4 criteria/levelup.level_spend_blocked)

- **机制**:血预算停升级门(`discipline.blood_budget_levelup_blocked`,P21 已证)此前只有 decision_v2 侧消费(arbiter/allocator/remediation),cw4 栈 M3(mandate+shop 两发射位)未接——同帧双栈语义断层,p2r1 hp=1 照发 9×LevelUpShop。
- **修法**:新谓词 `level_spend_blocked` = `blood_budget_levelup_blocked` ∪ `p2_crisis_band`(hp≤ceil(2×vd_p2_loss)≈41 = P21 d=2「到账更慢」档;经验收益兑现链 ≥2 战,与危机带搜索停付同一血线单一源、P48 λ>0 段「转化优先」与 `_crisis_buy_gate_open` 成对:停未来面、开当轮转化面)。ALL IN 豁免(位面末 boss,[18])两支共享;hp 不可信帧沿 blood_budget 支 fail-closed。M3 两发射位消费(计数键 `crisis_level_spend_defer`);`entry._reconcile_posture_authorization` 对被挂起的 level 授权按 `crisis_yield` 显式声明(非「未兑现故障」逐门定位)。零新自由参数:两支判据均为既有单一源。
- 连带:hp 无真值帧 fail-closed 拒升级自此覆盖 cw4 M3——三个旧夹具(无 hp 真值)按真值帧语义补 hp=100 并记 docstring。

## Considered Options

- ①只给支持度公式加在店加权 = 权重无推导锚且波动引入 pair 抖动——弃;供给确认加速驱逐门槛(复用驱逐-可逆机制,常数派生)——采纳。
- ②合并买入进 decision_v2 评分维 = 实际执行面在 cw4,评分接线打不到病灶帧——弃;cw4 M2b 义务通道+拒因细分——采纳。
- ③新建危机带经验停付线(新阈值) = 与 P21/血预算既有判据双源——弃;接线既有停升级门+危机带臂(两支皆单一源)——采纳。

## 验收(摘要,详见 REPORT.md)

- 新锁 10 条亲跑绿(`sr-od-test/test/sr_od/app/currency_war/test_cw_strategy_iter_7f.py`):加速驱逐/负例/冻结、合并买入/2★ 出集/金与席拒因、危机挂起/带外零漂移/crisis_yield 声明。
- CW 快速集 2534 passed,唯一红=w614 sim 保真 digest(任务书允许);受影响旧锁 3 条按真值帧语义演进(记 docstring)。
- sim 配对(n=30/臂,同池指纹 c35794e4efeb9b7f+eqg1,seed_base=0):P1 冻结窗均值 0.97→0.80(≥2 轮冻结局 6→5)、2★ 合成 123→128(+5)、局终 hp 均值 13.7→14.87(+1.17)、最低 hp 均值 +1.37、P2 hp0 率不变(0.567)。危机带经验支出占比两臂均 0(sim P2 栈整段零经验支出,病理无输入,机制开火由单帧锁承载);候选①加速在 sim 22/30 局 P1 开火(streak≥2∧驱逐同帧)。
- cw_replay --diff:行为漂移首发 p1r1,扩散面与三候选辖域一致(买向/升级/经验面)。
