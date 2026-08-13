# ADR-0114:read_star 改 TM 模板匹配 + V>150 滤暗金衣服

- **Status**:Accepted(2026-08-13)
- **迭代/纠正**:迭代 ADR-0113(三联判据轮廓法)→ TM 法;纠正 ADR-0112/0113「五角星」为「四角星」

## Context

read_star 数角色立绘底部金星(星级)。ADR-0113 轮廓法(HSV + 连通域 + 三联判据 cy>0.74 / a<600 / circ / aspect)对两个结构性 case 失效:

1. **2 星紧贴**:两颗金星 gap 小,MORPH_CLOSE 3×3 连通成单域,area>600 上限漏(实机后排-3 a607 / 备战栏-4 a407)。
2. **前排衣服淹没**:前排角色立绘底部大量**暗金衣服装饰(V80-150)**,HSV V>80 把衣服抓成 area1279 大块,金星被淹没,轮廓/TM 在大块上混乱(实机前排-3 金色像素 3750 vs 备战栏 1星 284)。

视觉大模型(2026-08-13 analyze_image + pi)确认:金星 = **四角星(十字星 ✦,非五角星)**,自发光亮金黄(高 V 高 S);衣服金色 = 古铜金(暗,V 低)。**亮度(V)差异**是区分钥匙,不是形状。

## Decision Drivers

- 用户要求各位置(前/后排/备战栏)1星/2星都识别准确(俯视变形不能破模板匹配)
- read_star 是 **offline 旁路**(`cw_performance` —— live star 走 bot tracking `BenchChar.star`,非 read_star)→ 完美主义投入产出低,但**治本**(替脆弱轮廓法)值得做

## Considered Options

### A. 沿用轮廓法(ADR-0113)+ 放宽阈值
放宽 cy>0.74→0.65 / a<600→700 / 调 circ。**否决**:2星紧贴连通是结构性(调 a 上限放装饰误判);前排衣服淹没是信噪比(调阈值抓更多衣服)。打地鼠,不治本。

### B. 多尺度 TM(0.8-1.4 resize 覆盖透视尺寸变异)
实测(2026-08-13)**倒退**:立绘库 71 张误判 1/71 → **9/71**(多尺度让 TM 阈值更易被装饰命中)+ 前排-3 仍 TM=1。多尺度连续 resize 引入误判。否决。

### C. TM + V>150 滤暗金衣服(采用)
HSV V 下限 80→150,滤掉暗金衣服(金星自发光 V 高留下)。mask 干净后**单尺度** TM 四角星模板 matchTemplate + NMS 分离紧贴 + peak 局部 area/aspect/circ 验证。

**关键实证**:V>150 让前排-3 从 area1279(衣服大块)降到 [630, 291](2 颗星分离)。立绘库误判 **0/71**(V>150 滤掉所有暗金装饰)。

### D. 多模板(备战栏 a190 + 前排 a210)
不同位置金星 area 因透视变异(后排 169 < 备战栏 190 < 前排 210),单模板 a190 对前排匹配偏低。**未采**(C 已通过 V 滤 + TM 解前排);若未来 V 滤后仍漏某位置,再加多模板(比多尺度精准:离散步长可控 vs 连续 resize 引误判)。

## Decision

**C:TM + V>150**。

- `_STAR_GOLD_LO` V:80 → 150(`cw_identity_obs.py`)
- 四角星模板 `currency_war/template/star_gold_tmpl.png`(19×19 area190,从备战栏-1 单星提取,模块级缓存 `_load_star_tmpl`)
- read_star 流程:region cy>0.65 → HSV V>150 mask → TM(TM_CCOEFF_NORMED,thresh 0.55)→ NMS(min_dist = tw*0.6)→ peak 局部验证(area 80-320 / aspect 0.80-1.20 / circ>0.35)
- 验证(2026-08-13):立绘库 71 张 **0 误判**;实机前排-3 / 备战栏-4 / 三月七 2星读 2;1星各槽稳读 1

## 已知局限(offline 旁路,待 live 多样本)

- **后排-3 2星读 1**:两星 gap 极小(<NMS 距离 tw*0.6≈11px),NMS 合并。read_star 仅 comp_viability 离线校验用,**live 走 bot tracking `star_achievement` 不受影响**。xfail 测试跟踪(`test_read_star_2star_back3_xfail`),待 live 多 2星样本调 min_dist / 加多模板。

## 四角星纠正

ADR-0112 / 0113 写「五角星」,实测(pi + 视觉大模型 2026-08-13)金星是**四角星 / 十字星(✦)**。本 ADR 纠正;0112/0113 正文「五角星」表述作废(读时以 0114 为准)。
