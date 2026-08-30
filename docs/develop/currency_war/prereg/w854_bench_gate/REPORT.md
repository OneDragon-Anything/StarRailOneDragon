# W854 · 买前 bench 容量预检硬门批 REPORT(ADR-0496 开臂前置件;W852 §3 挂账偿付)

- 日期:2026-09-11;基线:主仓 HEAD(含件价值 Phase 1+w_retention=0.0
  标定,ADR-0496)。
- 设计依据:W852 REPORT(`../w852_weight_calibration/REPORT.md` §3
  挂账节)+ ADR-0496 + W831 v2 §3.3(可加性边界:硬门不进评分,与
  Phase 1「E 禁进评分」相容)+ W829 支出门 D3(单一实现纪律)。
- 决策记录:`docs/develop/currency_war/decisions/0497-piece-value-
  bench-reserve-gate.md`(INDEX 已追加)。

## 1. reserve 推导(P29 H 卡点偿付,禁拍死值)

`piece_value.bench_reserve(state, session, registry)` = **1 + 线内
开对线数**(上限 `piece_value_bench_reserve_cap` 截断):

1. **基线项 1**(P29 卡点保守处理直译):P29 明文「bench 占用 ≥
   容量−1 时 H 取禁囤阈值」。每帧至少保 1 空位给受保护类(线内缺档
   成员 EV ≥ Δp_tier·R_rest ≈ 1.4×R_rest 金当量 / 激活钥匙件 P20
   2.6-2.9×),而囤牌期权近零(P1:≤2 费再遇 7-15 轮;W846 归因 B
   买入 56.7% 为 ≤2 费)——保护与囤牌的价值不对称恒成立 → 基线恒在。
2. **开对项 +1/线**:线内同名 1★ 恰持 1 份(合成线开对)数。2★
   合成链深 3 张,但 bench 槽位需求峰值 = **2**:第 3 张到达即 merge
   完成,满栏合成买合法(W544/ADR-0453,不占新空位);已沉没 1 槽后
   剩余需求 = 第 2 张的 1 个空位。该空位被囤牌件占掉 → 整条线停在
   深度 1(沉没 1 槽 + 1 购),损失大于一枚新囤牌期权 → 每开对线
   reserve+1。数据侧对照:W846 B 买入 41% 发生在占用 7-8(最后两
   空位),正是开对线第 2 张与囤牌竞争的带。
3. **上限 cap**:扫描旋钮缺省 2(W852 扫描建议带 {1,2} 上沿);
   reserve ≥ 1 硬不变式(bench_front_full 钳制)。
4. 边界:无锁线意向 → 开对数不可判 → 退基线 1(辖域不明不扩张预检)。

## 2. 落码对照

| 面 | 落点 | 内容 |
|---|---|---|
| 判据单一实现 | `spend_gate.bench_front_full` 扩参 `reserve: int = 1` | 缺省值使 D3 与 P29 定性门(realization)消费点行为逐位不变;reserve<1 钳回 1(硬不变式);禁第二谓词 |
| 硬门本体 | `piece_value.bench_gate_verdict` | 空位 ≤ reserve(占用 ≥ 容量−reserve)拒新买非合成 BuyCard;豁免 = merge 候选 ∪ 当轮可部署 ∪ 线内缺档成员(missing_members 单一源);让位 = boss 窗 / ADR-0474 分配器接管帧(D3 同族) |
| 链序 | arbiter 约束名 `pv_bench_reserve` 置 `spend_gate` 后(链尾) | 双门并存帧 d3_bench 先到先记(首拒即断),本门只记「未达 D3 带但 ≥ 容量−reserve」不重叠带,零双计;门拒纪律型(resource 空,不进回连) |
| registry | `piece_value_bench_gate_enabled=False`(伞=piece_value_enabled 合取)+ `piece_value_bench_reserve_cap=2` | 第 1 态默认关零漂移;audit_matrix bench/emergency、bench/mode 格同步(boss 格不含=让位) |
| 遥测 | `session.v3_pv_block` → schema/recorder/sim 三处透传 `sess_pv_bench_block` | 帧级拒因计数,轮键惰性重置(v3_sg_block 同模式) |
| ADR | 0497 + INDEX | reserve 推导/Considered Options/裁决序 |

消费点关系:门辖「买得出」(可买性过滤),不改评分——买评分消费点
(scoring 的 evaluate_piece A/B 加项)零改动,与 W829「P29 决定值多少
分,门决定买不买得出」同切分。

## 3. 锁组

新锁 `sr-od-test/test/sr_od/app/currency_war/test_cw_w854_bench_gate.py`
(9 锁 10 例):锁 0 缺省关+链序+矩阵格;锁 1 reserve 推导(基线/开对
±/2★ 非开对/恰持 2 份关闭/cap 截断/下界钳制);锁 2 bench_front_full
扩参缺省恒等+边界;锁 3 触发+三豁免+off 臂;锁 3b reserve 边界带+
_check_constraint 显影;锁 4 双门裁决序去重(占用 8→d3_bench 独记,
占用 7→pv_bench_reserve 独记);锁 5 boss 窗让位;锁 6 遥测计数+轮键
重置+off 零写点;锁 7 off 零漂移(缺省中性+arbitrate 序列恒等);
锁 8 子旗标消融。

受影响既有锁(锁的存在性纪律,非机械跟绿):
- `test_cw_w829_spend_gate` 锁 0:旧断言 `cons[-1]=='spend_gate'` 的
  意图是「守卫先到先记的链序前提」而非「spend_gate 恒链尾」——新门
  入链后守卫序不变,改断守卫序+邻接序(docstring 记录重推 why);
- `test_cw_adr0293_calibration`:字段面/constraints/audit_matrix
  回显锁随批同步(两新字段+链名+矩阵格)。

## 4. 验证数字

- 新锁组:10 passed(含 4 轮修正:拒因 describe 前缀格式对齐
  spend_gate `code:` 约定/lock2 钳制断言方向/lock4 开对构造);
- 受影响四文件(w854+w829+adr0293+piece_value)合跑:38 passed
  (中途态)→ 修正后全绿;
- cw_quick 全量(@cw_quick.txt):见 §7 提交前跑批(后台执行中);
- ruff:全部 10 个改动文件 ✅ All checks passed。

## 5. off 零漂移断言

- 结构锚:两旗标默认关 → `bench_gate_verdict` 首行返回 None(锁 3/
  7/8 三重断言:触发帧 None/_check_constraint 缺省中性/arbitrate
  零命中帧 off/on 动作序列逐位一致);
- `bench_front_full` 缺省参数:D3/P29 既有消费点逐位不变(锁 2);
- audit_matrix/constraints 变更被 adr0293 回显锁辖死,无静默漂移面。

## 6. 复验判据声明(编排者后续派,本批不执行)

硬门落地后,件价值 Phase 1 按 **W836 PREREG 同格重验**:
- **臂式**:a-only 双臂(off = DEFAULT_REGISTRY;on = piece_value_
  enabled+piece_value_buy_enabled+piece_value_bench_gate_enabled 全
  开,w_act=1.0/w_ret=0.0 标定值,hard gate 参数缺省),同池同种子窗
  (主窗 seeds 3_000_000..3_000_999,n=1000/臂,同 W846/W852 配置;
  dev 窗预演用 seeds 3_100_000.. 先行);
- **两格判线**(与 W846/W852 同格):
  - G4 满栏帧差 ≤ +2pp(硬门须消掉 W846 的 +11pp 满栏红);
  - M1-L 病灶②效应量:相对下降 ≥30% ∧ 绝对差 ≥3pp(B 辖域收紧后
    病灶②杠杆应恢复——W852 判定 B=0 时杠杆关闭的结构性缺位由本门补);
- 辅助格:G7 Goodhart <30%、金<50 帧差零侵蚀、M4 非劣化(口径复用
  W846 冻结判读脚本);硬门触发面非零断言(sess_pv_bench_block 计数
  >0,on 臂);
- 判定:两格全过 → 开臂翻默认(第 2→3 态,盘点 off 臂锁组语义);
  不过 → 删码留 ADR(第 4 态,ADR-0497 Consequences 预登记),禁悬置
  默认关。

## 7. 提交纪律

独立 commit;逐文件点名 add;staged 对照声明文件集(src 7 文件+测试
3 文件+ADR 2 文件)后提交;禁触 realization.py 行为面(本批未触碰,
仅其消费的 bench_front_full 缺省行为保持不变)。

## 8. 合格线自检

reserve 有推导(§1,状态依赖公式非拍死值)✅ / 单一源消费
(bench_front_full 扩参,D3+P29 定性门+新门同一实现,锁 2)✅ /
锁全过(新 10 例+受影响组全绿)✅ / 默认关零漂移(结构锚三重断言+
回显锁)✅

## 9. 提交记录(补)
- 主仓:f5ddf82(9 文件,src 7+ADR 2,staged 对照=声明集零混入);
- 测试仓:47ef67(3 文件:新锁组+W829 锁0 重推+adr0293 回显锁);
- cw_quick:@cw_quick.txt 全量 1761 passed / 2 skipped / 1 xpassed(3:04)。
