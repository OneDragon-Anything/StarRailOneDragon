# 区域信息更新(星球 / 区域 / 特殊点)

版本新增星球/区域,或维护区域下的传送点/特殊点数据时用。目标:新数据能被 `SrMapData` 加载、GUI 下拉可见、锄大地路线按名字关联不断链。

**没做完下面 5 步不算完成。**

## checklist(必做)

1. ☐ 枚举权威清单——按 sr-od-dev-official-api 的 references/map.md 拉地图树,与 `assets/game_data/world_patrol_map/` 现状逐星球 diff 出新增星球/区域/楼层;多楼层层名从树节点确定楼层列表【必做】
2. ☐ 录入星球与区域——按「数据模型」节写 planet.yml 与区域注册表;优先用 GUI 管理界面(星球管理 / 区域管理),手改时照既有条目格式;uid 命名按「命名规则」节【必做】
3. ☐ 大地图资产与特殊点——区域缺底图时按 `large-map-record.md` 录制;特殊点表用定标产物(cal.json 的 sp 行)落位,传送落点(tp_pos)经巡访采集回填【必做】
4. ☐ 验证——「验证」节各项全过【必做】
5. ☐ 提交——git add 逐文件点名(yml + large_map 模板 + mm_icon 模板),commit 写清新增了哪些星球/区域【必做】

## 数据模型

三层注册表 + 两类模板资产,全部经 `SrMapData`(sr_od/sr_map 模块)加载:

1. **星球注册表** `assets/game_data/world_patrol_map/planet.yml`:每条 num / uid / cn。
2. **区域注册表** `assets/game_data/world_patrol_map/<星球目录>/<星球>.yml`:每条 num / uid / cn,可选:
   - `floors`:多楼层的层号列表(单层省略,加载时按层展开成多个区域);
   - `parent_region_name` + `parent_region_floor` + `enter_template_id` + `enter_lm_pos`:子区域专用,声明从父区域哪个图标(模板 + 大地图坐标)进入。
3. **特殊点表** `assets/game_data/world_patrol_map/<星球目录>/<星球>_<区域>.yml`:每行 uid / cn / planet_name / region_name / region_floor / template_id / lm_pos / tp_pos;tp_pos 与 lm_pos 相同则省略该键。传送点 template_id 用 `mm_tp_x`,特殊点用 `mm_sp_x`。
4. **大地图资产** `assets/template/large_map/<星球目录>/<区域目录>/raw.webp + mask.png`(目录名含楼层后缀,见命名规则);raw 可带轻扩展防路边贴边,mask 白色 = 可走。
5. **小地图图标模板** `assets/template/mm_icon/<template_id>/`;新图标先全库查重再裁剪,并登记该目录 README.md。

## 命名规则

- uid = 中文名拼音首字母缩写;星球内 num 顺延,`num + uid` 组成唯一标识,**定了不改**——星球/区域编号或 uid 变更会触发注册表文件、目录、yml 文件名联动重命名,并使按名字关联的路线解析失配。
- 目录/文件名由框架按 id 派生:星球目录 `<P两位序号>_<uid>`;区域 `R两位序号_<uid>`,楼层后缀正层 `_F1`、负层 `_B1`(0 层无后缀)。
- 特殊点表的 planet_name / region_name / region_floor 是按名字关联的:区域改名必须同步改 sp 表对应行。

## 方法

- **新增星球/区域**:优先 GUI 的星球管理 / 区域管理界面(世界巡逻设置下);保存逻辑会自动创建星球目录与公共路线目录。手改 yml 时注意保持 num 排序与既有条目格式。
- **特殊点落位**:定标产线的 cal.json `sp` 行(锚点画布坐标)为底;传送落点(tp_pos)与图标本体可能不重合,需巡访点图标 → 传送 → 回小地图反推落点后回填。重合点(如特殊地标)tp_pos 直接等于 lm_pos。
- **区域重绘后修正**:大地图重录后全图坐标系可能平移,用 `large_map_recorder` 应用(app_id `large_map_recorder`)的 fix 流程按偏移量批量平移锄大地与模拟宇宙路线的坐标类操作。

## 验证

1. `SrMapData` 构造后星球/区域/特殊点计数与本轮意图一致,无解析报错。
2. GUI 区域下拉与锄大地配置能选到新区域。
3. 既有路线加载无「无法匹配星球/区域/传送点」报错(名字关联未被改名破坏)。
4. 本机可登录时实机冒烟:大地图能打开新区域、锚点图标与 lm_pos 吻合。
