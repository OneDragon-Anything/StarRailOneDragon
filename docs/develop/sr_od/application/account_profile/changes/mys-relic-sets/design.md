# mys-relic-sets（遗器套装名与激活效果）迭代设计

## 0. 元信息

- 目标（用户裁定 2026-11-04）：①`SrRelic` 单件带 **套装名**；②`CharacterDetail` 带 **已激活套装的几件套效果**（几件套+效果文案）
- 状态：草案（轻量迭代；结构沿用 roster-detail 已验收分层）
- 数据源事实：`avatar/info` 的 `relic_wiki` 词典为**空**（原始抓包+规划器双证）——官方接口不供套装数据，套装名/效果须自建数据层：官方 wiki 遗器频道快照（侦察产出 `.debug/temp/mys-relic-sets/relic_sets_snapshot.json`）**固化为 Python 常量模块**（用户裁定：禁 JSON 文件），运行时零网络消费

## 1. 数据层

- **常量模块**（用户裁定：禁 JSON 数据文件，数据写代码）：`src/sr_od/mys/sr_relic_sets.py`——四要素齐备的套装常量表：`RELIC_SETS: tuple[RelicSetDef, …]`（`RelicSetDef = {set_name, kind: 'cavern'|'ornament', pieces: list[{name, pos}], effects: {'2': desc, '4': desc|缺失}}`，内容逐条对照侦察快照）+ 纯函数助手：
  - `resolve_set_name(piece_name: str) -> str | None`：miss 返回 None 并 warning（新版本套装未入常量；不抛异常）
  - `build_set_effects(relic_piece_names: list[str], ornament_piece_names: list[str]) -> list[dict]`（dict 由映射层构造 SrSetEffect；**件名字符串列表入参**防循环导入）：按套装分组计数，`piece_count ≥ 2` 即激活对应效果（隧洞套 2 件效果 + piece_count=4 时 4 件效果；位面饰品 2 件效果）；未入常量的套装不产出效果条目（件名兜底见 §2）
  - 「件名→套装名」反向索引模块加载时构建一次（进程内缓存）
- **版本刷新工序** = 重跑侦察抓取 → 对照 diff 更新常量（diff 可审），工序写入正本
- 消费口径：单件名→套装名映射**独立于 property_info**（套装数据无接口来源，纯常量）

## 2. 契约（定死）

1. `SrRelic` 扩展：+ `set_name: str`（映射层经 `resolve_set_name` 填充；快照 miss → 「未知套装」+ warning）
2. `CharacterDetail` 扩展：+ `set_effects: list[SrSetEffect]`；`SrSetEffect = {set_name: str, kind: Literal['cavern','ornament'], piece_count: int, pieces: list[str]（该套已佩戴件名）, activated: list[SrSetEffectEntry]}`；`SrSetEffectEntry = {count: int, desc: str}`（count ∈ {2,4}，只列已激活档：隧洞套 piece_count≥2 列 2 件效果、=4 加列 4 件效果；饰品套 piece_count=2 列 2 件效果）
3. `mys_get_roster_detail` 描述更新：补「含套装名与已激活套装效果」；载荷自动携带新字段（asdict），端点与信封语义零变化
4. v1 `mys_get_characters` 轻口径**不加**套装字段（保持轻）
5. 明确不解决：套装效果文案的富文本清洗（官方原文透传）；快照在线刷新（手动工序）；icon 透传不变

## 3. 测试策略

- 快照完整性：随仓快照文件加载成功、套装总数与侦察报告一致、锚点断言（骇域漫游的信使 4 件件表+2/4 效果、生命的翁瓦克 2 件+效果）
- 映射单测：件名→套装名锚点与未知件名兜底；`build_set_effects` 三形态（满装 4+2 双激活 / 缺件 2 件不激活 4 件效果 / 饰品 2 件激活）
- detail 集成：fixture 角色扩 set_name/set_effects 断言（冻结字段集同步更新）

## 4. 验收

实机 `mys_get_roster_detail`：开拓者（骇域漫游的信使 4 件+生命的翁瓦克 2 件）`set_effects` 应含「骇域漫游的信使」2/4 件效果与「生命的翁瓦克」2 件效果；程序化对照快照全量核（套装名 100% 归属、激活计数正确）。
