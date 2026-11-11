# 遗器套装数据体系设计总览

## 1. 分层

- **常量层(公开仓,唯一权威载体)**:`src/sr_od/mys/sr_relic_sets.py`——名称域(中文名/件名/效果/描述/获取途径)+ 套装英文 id。用户裁定:禁 JSON 数据文件、数据写代码;新增条目人工审阅后手工维护。
- **权威表(公开 skill)**:`skills/sr-od-dev-relic-data/references/relics-full.json`——wiki 侧连接数据(content_id/page_id/英文名/别名/来源)与 id 的对照;常量是数据本体,权威表是 wiki 管道的连接件。
- **解包侧(本机私有)**:图标编号↔名称映射、图标导出与转档;公开仓只知「有这个映射」,不知内容。

## 2. 挂接架构(id 中枢)

```
国内 wiki(channel 30)          国际服 wiki(menu 108)
  content_id ──┐                  entry_page_id / en 名 ──┐
               │                                          │
               └────────► 名称域(常量中文名)◄──────────────┘
                              │
                              ▼
                    套装英文 id(归一化)
                              ▲
                              │
解包侧编号(私有映射表)────────┘
```

两源各自经名称域挂到 id,互不直连;新增数据源(如未来实机接口)同理挂 id。

## 3. 模板规范库

`assets/template/relic_icon/<套装id>_<部位英文>/raw.webp`;loader = `config/relic_templates.py`(镜像 light_cone_templates:目录名校验违例 raise、ctx 级缓存)。与光锥的差异:套装多件,template_id = id + 部位段;部位英文是 6 常量映射(`RELIC_POS_EN`),不逐件存字段。

## 4. 约束

- 空 id 套装不入权威表连接字段(en/page_id 留空)、不入模板库;名单测试白名单锁定。
- 效果文本冻结语义与光锥同:固化后模块为唯一权威,wiki 只喂新增,漂移只报告。
- 数字编号(解包侧)不出私有仓;commit message 避免私有相关字眼。
