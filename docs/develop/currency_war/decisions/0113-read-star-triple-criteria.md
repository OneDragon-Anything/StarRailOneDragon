# 0113 read_star 三联判据(a>120 + circ>0.45 + aspect0.85-1.15;迭代 0112,治实战金星漏检)

Status: accepted
Date: 2026-08-12

## Context
0112 纯 circ>0.55 治了立绘库装饰误判(0/71),但**实战金星 circ 实测 0.52-0.65**(非 0112 标定的
0.57-0.65):备战栏-2 a142 circ0.52 被 circ>0.55 误漏 → read_star count=0 → fallback 返1(1星碰巧对,
但 2星会读少 → hook 不触发 → 采不到 2星,本轮专项任务4 死锁)。

多槽形状分析(2026-08-12,实战备战屏 + 立绘库 71 张):
- 金星:a142-274 circ0.52-0.65 solidity0.44-0.59 **aspect0.89-1.06**(近方)
- 装饰:前排长条(a669 aspect2.44)/ 立绘库青雀(a171 aspect0.74)→ **aspect 区分明显**
- 立绘库赛飞儿 a108 circ0.54 aspect1.07 → 与金星形状几乎全同(纯 circ/aspect 区分不了,**靠 area 滤**)

## Decision Drivers
- 金星 circ 变异大(0.52-0.65),单 circ 阈卡中间(0.55 漏 0.52,0.45 放 0.54 装饰)
- aspect 区分长条/细长装饰(金星 aspect~1,装饰 aspect>1.15 或<0.85)
- area 区分小装饰(立绘库赛飞儿 a108 < 金星 a142+)

## Considered Options

### A. 降 circ 阈 0.55→0.45(放金星0.52)—— 引入立绘库 4 误判
赛飞儿0.54/青雀0.46/刻律德菈0.70/赛飞儿0.45(area43/90 被 a>100 滤,剩赛飞儿a108/青雀a171 误判)。
单 circ 区分不了赛飞儿 a108(形状同金星)。

### B. aspect 替 circ —— aspect 单独不够
13/35 立绘库装饰 aspect 落金星范围[0.7-1.3](但它们 circ 低<0.45)→ aspect+circ 组合才够。

### C. 三联判据 a>120 + circ>0.45 + aspect0.85-1.15 —— **选定,治本**
- a>120:滤小装饰(赛飞儿 a108)+ 金星 a142+ 留余量
- circ>0.45:放金星 0.52(0112 的 0.55 漏)+ 滤低 circ 装饰(灵砂/阿格莱雅 <0.45)
- aspect0.85-1.15:滤长条/细长(前排 aspect2.44 / 青雀 aspect0.74)+ 金星 aspect0.89-1.06 留余量
- 立绘库 0/35 误判 + 实战金星全过(a142-274 circ0.52-0.65 aspect0.89-1.06)

### D. matchShapes 金星模板(Hu 矩,0112 Option C)
最鲁棒,但需金星模板轮廓重构;三联(C)已 0 误判,无需 D 复杂度。

## Decision
选 C(三联判据)替 0112 的纯 circ>0.55。morphologyEx 保持 **CLOSE**(试 OPEN 会 erode 掉金星致合成
多星全读1,失败 → OPEN 太激进,回 CLOSE)。

## 多星验证(合成,2026-08-12)
用真金星(18×17px)合成 2/3 星横排跑 read_star:
- **gap≥3(间距≥3px):读对**(2星读2 / 3星读3)→ 真实金星大概率 gap≥3(UI 视觉间距,18px 金星需间距区分)
- **gap<3(紧贴):morphologyEx CLOSE 3×3 连通成 1 域 → aspect 宽被滤 → 读少**(局限)
- cx 0.35w 够宽:3星 gap10 边缘金星偏离 0.71<1.0(不滤)

紧贴(gap<3)局限待真 2星样本确认间距;read_star 是 offline 旁路(live star_achievement 用 bot tracking
bc.star,非 read_star),紧贴局限只影响 hook 采售价(不卡 live)。

## Consequences
- 立绘库 0/71 误判(0112 保持)+ 实战金星全过(含 circ0.52,0112 漏的)+ 装饰滤(前排/青雀)
- 解锁 hook 采真 2星(tracked bc.star 准 → star≥2 触发 → 验售价 ADR-0111)+ 离线漂移校验准
- 300 测试过;紧贴局限注明(待 2星样本),非卡点(offline 旁路)
- 对新角色鲁棒(金星 aspect~1 固定,装饰 aspect 异常);三联阈留余量(金星 aspect0.89-1.06 内 0.85-1.15)
