# ADR-0247: SIFT 识别两阶段惰性 RANSAC(观测层性能优化,决策语义逐位等价)

- 状态: accepted
- 日期: 2026-08-24
- 关联: ADR-0225(观测层);`currency_war_char_id.identify_character`

## 背景

`identify_character` 单槽 ~102ms,热点不在 knnMatch(BF 全库 11.4ms)而在
**74 模板 × findHomography RANSAC(~85ms)**。调用面:`cw_observe_full`
(每备战决策环)+ `deploy_bench`(部署 op 内多次),一轮备战 bench 9 +
deployed 10 ≈ 19 槽 ≈ 1.9s。绝对量级小于 OCR(40-70s/轮),但属观测层
可白捡的固定成本。

已评估并**排除**的方案:
- **FLANN 替代 BF**:描述子集太小(模板均值 ~390 点/槽位 ~106 点),
  建树开销反噬——实测 BF 11.4ms vs FLANN 280.9ms(慢 25 倍)。
- **模板特征磁盘持久化**:模板加载 1.23s/进程(懒加载一次),持久化需
  加指纹失效逻辑(模板由 gen_plaza_chars.py 再生成),负收益。

## 决策

两阶段惰性 RANSAC(`identify_character` 内部重构,签名与默认参数不变):

1. 阶段 1:全模板 ratio-test good 数(免 RANSAC;BF knnMatch 本身高效);
2. 阶段 2:按 good 降序惰性 RANSAC,剪枝条件
   ``g ≤ best / ambiguity_ratio``(best = 已扫到的最大内点)。

### 等价性论证(剪枝不改变任何决策输出)

- 内点 ≤ good(RANSAC 只减不加)→ 被剪者不可能超 best → best/best_id 不变;
- 歧义触发需 ``second > best / ratio``,被剪者 ``g ≤ best / ratio`` 恒不
  满足 → 歧义判定与 second_id(歧义触发时)不变;剪枝记录的 upper bound
  永不进入决策路径;
- best 并列时 tie-break 顺序与旧版不同,但不可观测:best==second>0 必落
  歧义分支(``best < ratio×best`` 恒真)返回 None/色相仲裁,色相仲裁用
  frozenset 配对与顺序无关;
- ``ratio ≤ 1`` 时禁用剪枝(threshold 退化防御)。

### 验证(反馈梯度)

- 离线对拍:40 张存档截图(3718 张确定性等距抽样)× 33 裁图/张(全屏
  tile 网格 + bench 槽)= **1221 裁图,新旧实现输出 (cid, inliers)
  逐条 0 差异**;
- 锁测试:`test_currency_war_char_id` / `test_cw_back_layout`(含色相
  仲裁锁)/ `test_cw_identity_obs` 27 passed;
- 全量:CW 测试子集(见进度树当轮记录)。

## 结果

- 密集槽单识别 102ms → **32ms(3.2x)**,识别结果不变
  (同槽同 inliers=47);
- 一轮备战身份观测 1.9s → **0.60s**;
- 混合负载(1221 裁图含空槽/UI/文本)整体 63s → 43s。

## Considered Options

| 选项 | 结论 |
|---|---|
| 全库 RANSAC(现状) | 保留为 `_inliers` 单一语义参考,不在热路径 |
| FLANN 匹配器 | 排除:小描述子集建树反噬,慢 25 倍(实测) |
| 特征磁盘持久化 | 排除:省 1.23s/进程,换一套缓存一致性,负收益 |
| 硬 top-K 截断 | 排除:无法证明与全扫等价(截断处可能藏真 best) |
| **good 降序惰性 RANSAC + 比率剪枝** | **采纳:剪枝条件可证决策不可达,等价性有论证+1221 对拍实证** |
