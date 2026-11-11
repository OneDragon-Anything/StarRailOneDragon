# 光锥数据 skill 设计总览

## 1. 定位

维护项目「光锥数据」（`src/sr_od/mys/sr_light_cones.py` 常量模块）的版本刷新全流程与项目内光锥 id 定义。对齐 `sr-od-dev-character-data` 的三步法结构：拉列表 → 更新代码 → 资产口径，区别在数据形态（光锥无行迹/星魂，多一条 id 定义线）。

## 2. 边界

- 遗器套装数据不归本 skill（版本更新工序在本机装备数据类 skill，因含解包与数字 id 权威存储未随仓分发）。
- 光锥图标的解包导出手法不归本 skill（归本机解包类 skill）；本 skill 只定归档口径（名称键/稀有度底色）。
- wiki 接口的字段位置与坑不进本文（归 `sr-od-dev-official-api` 的 references）。

## 3. 构成

- `SKILL.md`：六步 checklist 流程 + id 定义附录（智能体执行入口）。
- `scripts/fetch_sr_wiki_cone_list.py`：国内 wiki 频道清单+详情抓取。
- `scripts/fetch_hoyowiki_cone_en_names.py`：国际服英文名拉取与中英互连（连表键归一化含脏字符清理）。
- `scripts/build_cone_authority_table.py`：权威表组装（wiki × intl × 模块顺序 + manual 行登记）。
- `scripts/gen_light_cones.py`：常量模块生成（冻结纪律 + 新增取文 + 漂移报告）。
- `references/cones-full.json`：权威表随仓快照（生成器输入与人工对账锚）。
- 项目侧配套：`src/sr_od/config/light_cone_templates.py`（识别模板库 `assets/template/light_cone_icon/<id>/raw.webp` 的遍历单一入口，id 键命名约定即注册表）。

## 4. 关键设计动机

- **id 线独立于名称线**：项目此前光锥只有名称无 id（装备域按名称寻址），id（官方英文名归一化）为装备域按 id 寻址铺路；id 与名称分离登记在权威表，名称域消费方不受影响。
- **冻结纪律写进生成器**：wiki 词条存在编辑损坏（梯度列表粘连、字符残缺实测），已有词条文本一律冻结保留、wiki 只喂新增、漂移只报告——人工审阅从「逐字校对全量」缩小为「核对漂移清单」。
- **manual 行机制**：官方公告已给名、wiki 未上线的新词条以 `source=manual` 登记进权威表占位（id 待国际服同步回填），wiki 同步后同键自动转正，管线无需改代码。
- **中英互连靠词条 id 不靠名字**：国际服 zh/en 列表共享 entry_page_id，名字对齐零启发式；名字只用作权威表键（归一化清理脏字符后）。
