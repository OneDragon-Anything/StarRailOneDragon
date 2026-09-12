# 观测枢大地图接口(米游社 srmap 交互地图)

> 锄大地新地图产线的素材源:每楼层一张**已合成的完整底图**(多层叠加官方已渲染好)+ 统一坐标系 + 锚点/点位坐标,替代实机逐屏拼接。2026-09-12 全链路实测并接入生产验证(端到端:API→定标→生成→传送→定位,残差 0.87px、定位距锚点 12px)。

## 入口与发现

- 页面:`webstatic.mihoyo.com/sr/app/interactive-map/index.html#/map/<map_id>`(URL fragment 携带 `shown_types`/`center`/`zoom`;`center=x,y` 与点位坐标同坐标系)
- 发现方式:页面网络面板照抄请求(公共技巧 1);全部 GET、免登录、`retcode:0` 家族约定

```
BASE = https://api-static.mihoyo.com/common/srmap/sr_map/v1
公共参数 = app_sn=sr_map&lang=zh-cn&app_version=<32位hash>
  app_version 取页面实际请求值(会随版本轮换);实测缺省行为未验证,失效时从页面重抓

GET {BASE}/map/tree?map_id=38          → 全星球→区域→楼层树(一次拿全,含最新星球)
GET {BASE}/map/info?map_id=<楼层id>     → 该楼层底图 URL + 坐标系元数据
GET {BASE}/map/point/list?map_id=<id>   → 该楼层全部标注点(含坐标)
GET {BASE}/map/label/tree?map_id=<id>   → 该楼层 label 分类树
GET {BASE}/map/point_group?map_id=<id>  → 多数图为空(retcode -502001 内容不存在)
```

## 坐标系(核心资产)

`map/info` 的 `data.info.detail` 是 JSON 字符串,解析后:

```json
{"slices":[[{"url":"https://uploadstatic.mihoyo.com/sr-wiki/...png"}]],
 "origin":[558,2112], "total_size":[2048,4096], "padding":[187,162]}
```

- **底图像素 = (x_pos + origin[0], y_pos + origin[1])**,比例 k≈1(锚点落点实测验证)
- `origin/total_size` **同区域各层完全相同** → 多层图逐像素配准,天然共享坐标系(收容舱段 3 层与支援舱段 2 层实测;各层内容像素数完全一致)
- 底图与游戏全屏图同款美术、同白描边路网;几何逐像素对齐(SIFT 定标后叠图零偏移),但**填充色调可能与游戏渲染有差**(官方图偏纸面风格)——依赖几何不依赖色调
- 底图带 alpha 通道:alpha=0 为区域外,贴 205 灰背景即得 raw

## 点位(point/list)

- 响应键是 `data.point_list`(不是 points);`data.label_list` 内联给出本图 label 定义
- 每点:`x_pos/y_pos`(官方坐标)、`label_id`、`author_name`/`ctime`(米游社编辑者标注)
- **label_id 按图各异**,锚点判定按名字解析:label 名「界域定锚」= 游戏内空间锚点(传送点);「地图跳转/地图跳转2」= 区域门(编辑者标注稀疏,多数图为 0);其余 = 忆泡/战利品/阅读物/敌人/花萼等
- 锚点覆盖实测(2026-09-12 抽查 14 楼层):新老星球全有(二维市 6 锚、奥赫玛 7 锚…);小体量子图(如行政区-1层博物馆)可以没有

## 已验证的消费方式

1. **底图→游戏渲染尺度**:实机全屏地图缩到最小截一张图(截图前把鼠标移出画面),与底图 SIFT + 内点最小二乘相似变换 → 重采样。单张即可(几何对齐不要求全覆盖),残差 0.87px 量级
2. **锚点坐标**:point/list → 底图像素 → 同变换 → 游戏帧 lm_pos(与屏上图标吻合)
3. **锚点名**:游戏内点锚点图标弹窗 OCR(重合点位会弹多选列表,锚点带蓝色锚图标)
4. ⚠️ 匹配健壮性:带掩码 TM_CCOEFF_NORMED 在源图平坦窗口(205 背景,std=0)会吐 conf>1 伪匹配压过真匹配,消费方需平坦源守卫(框架 cv2_utils.match_template 已加)
5. ⚠️ 依赖纪律:底图/点位是官方+社区编辑内容,**不入仓库**(同解包素材纪律);本地生成、快照消费
