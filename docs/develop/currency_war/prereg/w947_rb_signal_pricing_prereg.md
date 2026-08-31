# W947 · R-B 三信号定价 批B · A/B 预注册(判前锁)

> 状态:判前锁——本文件在批B任何动码**之前**落盘,判读口径禁中途改。
> 设计单一源 = `.debug/temp/currency_war/w920_rb_design/DESIGN.md`(§3 落点表/§4-2 判据);命题 = P20/P1/P16/P13/P33(stage_transitions Q1 数据)。
> 执行批 = `.debug/temp/currency_war/w947_rb_batchb/`(跑批脚本 run_w947.py / 判读脚本 judge_w947.py,判前冻结)。

## 1. 臂设计与单因子纪律

- **臂 off(对照)**:`sim_decision_registry()` 缺省(新伞开关 `rb_signal_pricing_enabled=False`)。
- **臂 on(处理)**:同 registry 仅 `rb_signal_pricing_enabled=True`,三信号权重取 DESIGN 建议值占位(rb_s1_unit=1.95 / rb_s2_threshold=0.85 / rb_s2_unit=1.0 / rb_s3_unit=0.5;来源=DESIGN §3-D3 注释,标定挂账)。
- 两臂同置 `ALLOCATOR_ENABLED=False`(W842/W846/W859/W902 基线同配置);唯一差异 = 伞开关一位。

## 2. 窗口、n、零漂移锚

- 主窗 seeds 3_100_000..3_100_299,**n=300/臂**,同 seed 配对,`simulate_p1(pool='snapshot', planes=2)`。
- 池指纹两臂一致先核(不一致=作废重查)。
- **零漂移锚**:off 臂前 30 局 vs 纯默认入口(无参 `simulate_p1`)逐位对拍(final_hp / p2_rounds / p2_entered 三元组),30/30 全一致判读才有效。
- **开火面 smoke(判前声明)**:on 臂前 5 seed 内 `rb_signal_fires` 至少一次非零信号开火;0 次=输入死,中止并先补观测(strategy-work §4「新机制先验证它会开火」)。

## 3. 判据(跑前写死,判读零自由裁量)

| # | 判据 | 定义 | 达标线 |
|---|---|---|---|
| M1 | **主判据:形态达标率**(DESIGN §4-2,ADR-0432 族口径=账本 `form_ok`) | P1 末轮 `form_ok=True` 的局占比,配对差(on−off)均值 + bootstrap 95% CI(重抽样 seed 20260912,B=2000) | 差 > 0 ∧ CI 下界 > 0 |
| G1 | 守门:息基不劣(带金占比,P17 主门口径) | P1 帧中 `gold≥50` 帧占比,配对差 95% CI | CI 下界 ≥ −2pp |
| G2 | 守门:买入破息率不升(piece_value 死因防复发,DESIGN §4-2) | P1 买入笔中「重放近似 gold−Σ买cost < 50」笔占比(**上界口径:卖出回金不计,如实声明**);on−off 点差 | ≤ +2pp |
| S1 | 次要:终局 hp 方向(任务书次要判据) | final_hp 配对差均值 | 只报数不判格 |

## 4. 结论兑换映射(strategy-work §4 三选一,跑完当场兑换)

- M1 过 ∧ G1 ∧ G2 过 → 本批结论=**建议开臂**(翻默认值由编排者裁决批C;本批不翻)。
- M1 不过(含 CI 含零)或任一守门破 → **不合入生产默认**(开关保持默认关),按无效/调常量分支出裁决建议;无限期悬置默认关不合法(开关生命周期)。
- on 臂开火率=0(主窗复测)→ 输入死,裁决=删码留 ADR。

## 5. 批B 落码清单(判前登记,动码前对照)

1. `kernel/cw_registry.py`:伞开关 `rb_signal_pricing_enabled`(默认关)+ 信号常数组(rb_s1_unit / rb_s2_threshold / rb_s2_unit / rb_s3_unit)+ 贯穿度字段 `rb_retention_q1`(stage_transitions Q1 逐卡 E→F;非手写名单,数据字段化);**不复用任何 piece_value 符号**(W902/ADR-0497 禁复活)。
2. `decision/decision_v2/rb_pricing.py`(新):`rb_offpiece_term(cand, state, after_state, session, registry) -> tuple[float, dict]`——S1 凑档(P20 辖域)/S2 贯穿(Q1 留存)/S3 再遇窗口期权(P1/P16,费级窗口单一源=registry.remeet_window_rounds,轮级计次衰减);信号加项落在 tp_gap 之后、off_lock 降级之前(随 κ 比例折扣)。
3. `decision/decision_v2/scoring.py` `score_candidate`:插入消费点 + bd 披露键 `rb_s1/rb_s2/rb_s3`。
4. `sr-od-test/test/sr_od/app/currency_war/test_cw_rb_pricing.py`:锁0 默认关零漂移;S1/S2/S3 各自单帧锁;piece_value 守卫移除红检。
5. 禁碰面遵守:operations/、telemetry/、battle_loop.py、handlers/、prep_director.py 零改动;禁 git commit。
