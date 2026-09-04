# CW sim A/B 对拍第三轮报告(cw3 vs decision_v2,n=40)

> 判前锁:`PREREG_cw3_vs_legacy_AB.md`(本批按 v3/v4 执行;判据/δ/样本量/哨兵红线与 v1 一致)。
> 驱动:`run_ab_batch.py`(第二轮已验证可用,本批零改动);策略代码 A/B 期间冻结,本批未改任何策略/resolver/判读代码/PREREG。

## 1. 配置实录

| 项 | 值 |
|---|---|
| 臂 | `cw3`(新层)/ `decision_v2`(旧层) |
| seeds | 0..39,双侧同 seed 配对(40 对,全配对,`seeds_unpaired=[]`) |
| planes | 2(planned_rounds=16) |
| pool | snapshot,双侧 `pool_fingerprint` 逐字一致:`6400d5d8edeaf68d+eqg1` |
| PYTHONHASHSEED | 0(双侧) |
| 输出目录 | `AB_cw3_n40_r3/`、`AB_legacy_v2_n40_r3/`(各含 decisions/outcomes/shop_snapshots 三流账本 + manifest.json + summary.json) |
| 耗时 | cw3 ≈1s / decision_v2 ≈14s(纯 sim,分钟级) |

## 2. 判定 JSON 原文

`AB_result_cw3_vs_legacy_r3.json`(全文):

```json
{
  "prereg": "PREREG_cw3_vs_legacy_AB.md v1",
  "pool_fingerprint": "6400d5d8edeaf68d+eqg1",
  "n_pairs": 40,
  "seeds_unpaired": [],
  "summary_source": {"new": "summary.json", "old": "summary.json"},
  "main_metrics": {
    "M1": {"name": "存活通关率", "verdict": "FAIL", "delta": -0.125, "ci_lower": -0.275, "ci_upper": NaN, "delta_limit": 0.05, "new_rate": 0.125, "old_rate": 0.25},
    "M2": {"name": "P2入口率", "verdict": "PASS", "delta": 0.0, "ci_lower": 0.0, "ci_upper": NaN, "delta_limit": 0.05, "new_rate": 1.0, "old_rate": 1.0},
    "M3": {"name": "成型达成率", "verdict": "FAIL", "delta": -0.725, "ci_lower": -0.85, "ci_upper": NaN, "delta_limit": 0.05, "new_rate": 0.275, "old_rate": 1.0},
    "M4": {"name": "末轮成型度", "verdict": "FAIL", "delta": -0.4375, "ci_lower": -0.5379047897008494, "ci_upper": -0.33709521029915057, "delta_limit": 0.05, "new_median": 0.5, "old_median": 1.0},
    "M5": {"name": "花费率", "verdict": "FAIL", "delta": -0.3015918347870776, "ci_lower": -0.3801475248394458, "ci_upper": -0.22303614473470934, "delta_limit": 0.05, "new_median": 0.3841274397244546, "old_median": 0.6834349593495935},
    "M6": {"name": "空转轮占比", "verdict": "FAIL", "delta": 0.12236669580419582, "ci_lower": 0.06792145626757341, "ci_upper": 0.17681193534081824, "delta_limit": 0.05, "new_median": 0.19375, "old_median": 0.09090909090909091}
  },
  "sentinels": {
    "S1": {"tripped": false, "new": 1.0, "old": 0.0},
    "S2": {"tripped": false, "new": 2.0, "old": 2.0},
    "S3": {"tripped": false, "new_rate": 0.0, "new_count": 0},
    "S4": {"tripped": false, "new": 32.5, "old": 62.5},
    "S5": {"tripped": true, "new": 1.575, "old": 4.7, "drop": 0.6648936170212766}
  },
  "verdict": "FAIL",
  "verdict_reason": "哨兵越线:S5"
}
```

## 3. 机器结论

**ab_judge 总判:FAIL(哨兵 S5 越线;且主指标 6 项中 5 项未过非劣界)。**

## 4. 逐指标表(附 r1/r2 对照)

### 主指标(Δ=新−旧;PASS 判据 = 95% CI 下界 ≥ −δ)

| 指标 | δ | r3 Δ(CI 下界) | r3 判 | r2 Δ | r2 判 | r1 Δ | r1 判 |
|---|---|---|---|---|---|---|---|
| M1 存活通关率 | −5pp | **−0.125**(−0.275) | FAIL | −0.175(−0.325) | FAIL | −0.250(−0.400) | FAIL |
| M2 P2 入口率 | −5pp | 0.000 | PASS | 0.000 | PASS | 0.000 | PASS |
| M3 成型达成率 | −5pp | **−0.725**(−0.850) | FAIL | −1.000(−1.000) | FAIL | −1.000(−1.000) | FAIL |
| M4 末轮成型度 | −0.05 | **−0.4375**(−0.538) | FAIL | −1.000(−1.000) | FAIL | −1.000(−1.000) | FAIL |
| M5 花费率 | −0.05 | **−0.302**(−0.380) | FAIL | −0.320(−0.405) | FAIL | −0.547(−0.594) | FAIL |
| M6 空转轮占比 | +0.05 | **+0.122**(+0.068) | FAIL | +0.189(+0.131) | FAIL | +0.248(+0.193) | FAIL |

### 哨兵

| 哨兵 | 红线 | r3(新/旧) | r3 判 | r2 | r1 |
|---|---|---|---|---|---|
| S1 危局空转 | 新中位 > 旧中位+2 | 1.0 / 0.0 | OK | 3.0/0.0 越线 | 3.0/0.0 越线 |
| S2 最大连败 | 新中位 > 旧中位+1 | 2.0 / 2.0 | OK | 2.0/2.0 OK | 2.0/2.0 OK |
| S3 死锁局 | 占比>1% 且 ≥2 局 | 0 局 | OK | 0 | 0 |
| S4 行动量塌缩 | 新中位 < 旧中位一半 | 32.5 / 62.5 | OK | 34.5/62.5 OK | 16.0/62.5 越线 |
| S5 终局 hp 塌方 | 跌幅 >25% | 1.575 / 4.7(−66.5%) | **越线** | 1.15/4.7(−75.5%)越线 | 0/4.7(−100%)越线 |

### 辅助量(summary,未入判据,仅呈报)

| 键 | r3 cw3 | r3 decision_v2 | r2 cw3 | r2 decision_v2 |
|---|---|---|---|---|
| avg_final_hp | 1.575 | 4.7 | 1.15 | 4.7 |
| p2_entered_rate | 1.0 | 1.0 | 1.0 | 1.0 |
| p2_win_rate | (见 summary.json) | (见 summary.json) | 0.1919 | 0.2466 |
| hp_ge_60 | (见 summary.json) | (见 summary.json) | 0.0 | 0.0 |

## 5. 异常处置

1. **启动失败一次(已处置,无数据污染)**:首批两次后台任务因缺 `PYTHONPATH=src` 在 import 阶段即报 `ModuleNotFoundError: sr_od`,未跑任何局、未落任何批目录数据;补环境变量后重发,双侧完整跑完 40 seed。两次失败输出中 final_hp 均无局级数据,不构成部分数据。
2. **判读脚本标注口径**:ab_judge 输出的 `prereg` 字段与终端标注均为「PREREG v1」——脚本头未随锁版本号 v3/v4 更新。本批未改判读脚本(冻结面),按 PREREG v3/v4 修订表声明「判据/δ/样本量/哨兵红线与 v1 一致」,脚本内常数即 v1 口径,故机器结论有效;仅 JSON 的 `prereg` 标注字段为陈旧文案,已在报告头声明本批实际执行 v3/v4。
3. 无其他异常:双侧指纹一致、40 对全配对、无死锁局(S3=0)、判读脚本无报错。

## 6. 产物清单

- `AB_cw3_n40_r3/`、`AB_legacy_v2_n40_r3/`(三流账本 + manifest + summary)
- `AB_result_cw3_vs_legacy_r3.json`(机器判定)
- `AB_R3_REPORT.md`(本报告)

(按任务纪律,本报告不加解读;归因/处置交编排者裁决。)
