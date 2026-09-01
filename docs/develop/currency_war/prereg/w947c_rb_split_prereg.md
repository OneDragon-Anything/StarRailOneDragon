# W947-C · R-B 拆臂复测(S3 关/S1+S2 开)· 预注册判前锁

> 状态:判前锁——批C 复测跑批**之前**落盘,判读口径禁中途改。
> 背景:W947 v1 合臂 A/B 判负(形态达标率 −3.00pp CI[−5.0,−1.33],`not_merged_keep_default_off`);开火面归因 s3=432906 次绝对主导(s1=4602/s2=18277),编排者批准唯一一次拆臂重测。设计单一源不变 = `docs/develop/currency_war/prereg/w920_rb_design/DESIGN.md`;v1 判前锁 = 同目录 `w947_rb_signal_pricing_prereg.md`。

## 1. 臂设计(单因子)

- **off(对照)**:`sim_decision_registry()` 缺省(伞关)。
- **s12(处理)**:仅 `rb_signal_pricing_enabled=True` + `rb_s3_enabled=False`(新子旗标,默认 True=v1 语义不变)。即 **S1+S2 开、S3 关**。
- 两臂同置 `ALLOCATOR_ENABLED=False`;唯一差异 = 伞一位 + S3 子旗标一位。

## 2. 窗口、隔离断言、锚

- 主窗 seeds **3_100_000..3_100_299 与 v1 同窗**(同池指纹先核),n=300/臂同 seed 配对,`simulate_p1(pool='snapshot', planes=2)`。
- **隔离断言**:s12 臂全部局 `fires['s3']` 必须恒 0;非零=隔离失败,全部结论作废重查。
- 零漂移锚:off 前 30 局 vs 纯默认入口逐位对拍(30/30 才有效)。
- 开火面 smoke:s12 臂前 5 seed 内 s1 或 s2 至少一次开火;0 次=输入死,中止。

## 3. 判据(沿用 v1,跑前重申)

| # | 判据 | 达标线 |
|---|---|---|
| M1 主判据 | 形态达标率(P1 末轮 form_ok 局占比)配对差 + bootstrap 95% CI(seed 20260912,B=2000) | 差 > 0 ∧ CI 下界 > 0 |
| G1 守门 | 带金占比(gold≥50 帧占比)配对差 CI | 下界 ≥ −2pp |
| G2 守门 | 买入破息率(重放近似上界口径)点差 | ≤ +2pp |
| S1 次要 | 终局 hp 配对差 | 只报数 |

## 4. 结论兑换映射(编排者裁决授权,判前写死)

- **M1 过 ∧ G1 ∧ G2 过** → 保 **S1+S2**、**删 S3**(S3 概念被 v1 归因+本臂隔离复测共同否决);S1+S2 保持默认关,开臂翻默认由编排者按本 REPORT 分解结论另行裁决。删 S3 = 删 `rb_s3_unit/rb_s3_enabled` 字段、`_s3_option`/`_seen_count` 与其测试锁(生命周期第 4 态,ADR 记 why)。
- **M1 不过(含 CI 含零)或任一守门破** → **整件删码留 ADR**(S1/S2/S3 全部:伞+常数+贯穿度字段+消费点+测试锁),三信号定价方向在当前判据面下定谳无效;复活条件写入 ADR。
- ADR + strategy as-built 语义段随本批按兑换结果落地(三同步)。
