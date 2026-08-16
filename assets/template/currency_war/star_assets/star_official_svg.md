# 官网四角星 SVG 源(plaza 攻略广场,2026-08-15 采集)

来源:攻略广场网页 lineup 卡片星级 icon 的内联 SVG(data:image/svg+xml;base64)。

## 与游戏内金星对拍(2026-08-15 实测)

- **形状同源**:官网 SVG = 四角星(十字星,贝塞尔圆角,极值点 上6.4/右11.4/下11.5/左1.4);
  游戏内角色星级金星同为四角星(read_star:自发光亮金黄,立绘底部中央 17-19px)——
  同一设计语言的 web 版。
- **颜色**:官网径向渐变 #FFEECB-#FFCF70 + 描边 #FFC051,落在游戏金星 HSV 范围
  (H10-45 S>40 V>150)内。
- **不建议直接替换模板**:SVG 渲染 mask 对游戏实拍模板 TM 0.525 / IoU 0.488 ——
  游戏内星带自发光晕圈(实拍 mask 217px vs 纯形状 106px),现有 star_gold_tmpl.png
  (19x19 实拍,ADR-0114/0115/0116 三轮标定 + 全 fixture 验证 + 立绘库 0/71 误判)
  更贴合;SVG 纯形状缺辉光,直接换会掉分。
- **用途**:1) 版本更新星样式变化时的重标定种子(形状先验);
  2) 后续解析广场网页内容(读 lineup 星级显示)时的 icon 源。

## SVG 要点

width=12 height=13 viewBox 0 0 12 13;path fill=url(#paint0_radial) stroke=#FFC051;
radialGradient #FFEECB(0.22)-#FFCF70(0.56)。渲染 mask:star_official_svg_mask.png(19x19)。
