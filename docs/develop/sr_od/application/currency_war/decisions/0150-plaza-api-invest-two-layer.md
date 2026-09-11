# 0150 投资策略/环境切 plaza API base × overlay 两层架构

## Status

accepted(2026-08-16;↺ 推翻 ADR-0133 的「图鉴轮补 19 漂移」路线 —— 漂移缺口由官方 API 直出,图鉴轮该部分关闭)

## Context

ADR-0133 后投资策略注册表 = 315(米游社 doc ingest)+ 6(图鉴 codex)= 321,环境 83;遗留:① doc 比游戏内 334 少 19 条版本漂移(原计划图鉴轮实机采);② 注册表 effect 多为压缩转写(302/321),source 混源(content_id/codex/空),无稳定 diff 锚;③ 对拍 plaza 官方 API(2026-08-15 破解,`act-api-takumi.miyoushe.com/event/rpgcurrencywar/game/config`,免登录)发现注册表多处**真数据错误**。

对拍实证(错误清单):
- **5 条占位 effect**:定点爆破="爆发伤害"等 4 字占位(curated 早期手填),官方全文在 API;
- **13 条 rarity 错**:上述 5(金→棱彩)+ 返利+(金→银)+ 双龙会/白衣伙伴(棱彩→金)+ codex 4 条(棱彩→金);
- **数值错**:艾丝妲的猛犬 ×1000% vs 官方 ×2000%;Gemini 官方名 Gemi狸;
- **14 条缺失**:含飞光·映月(召唤物建档待办③"效果未知待图鉴核"就此闭环)、黑塔纪元、狸财经狸系;
- API `fight_augment_list` 334 条(棱彩122/金135/银77)= 游戏内数据银行同口径;`portal_list` 83 = 环境全量。

## Decision Drivers

- 单一源原则:官方 API > 手抄/OCR 采集;
- 已有人工建模(economy 73 / PICK_VALUE 315 / ENV_PICK_VALUE 83 / 分类·阵营)是 API 给不了的,必须保留且可长期维护;
- 版本更新要可重复:重跑脚本 + diff 报告,不能每次人肉对;
- OCR 匹配键连续性:键约定不能 break 现有精确匹配层(whitelist 子串/get_strategy 精确/LCS 兜底)。

## Considered Options

- **只补 14 条新增(最小 patch) vs 两层架构重构**:最小 patch 留下 13 条 rarity 错 + 302 条转写 effect + 混源 source,下次版本更新仍人肉 → 选两层架构(用户拍板:base 脚本生成一份,建模放另一个文件)。
- **数据放哪**:生成 `cw_invest_data.py`(代码可 import、测试可断言)vs JSON 资源文件(需 loader、无类型)→ py dataclass 模块(同 `gen_plaza_chars.py` 先例)。
- **键约定**:API 原名直用 vs canon 归一 —— 归一(OCR 实测全角冒号读半角 `战术专家:佩拉`;NBSP 空格 `摸个鱼吧\xa0I`;罗马数字/•/剎 形变)。叹号**不归一**(无实测证据,`艾丝妲的猛犬！` 保持官方全角)。
- **overlay 防腐**:静默 setdefault(孤儿键无声失联)vs import 即 raise → raise(版本更新后 overlay 引用被删/改名卡,立刻炸,测试也有显式断言)。
- **doc 去留**:ADR-0133 留 doc 作漂移对拍基线 → 漂移检测已内建到生成器 diff(by id),基线使命完成,**删 `investment_strategies.md`**(单一源)。

## Decision

1. **两层架构**:`cw_invest_data.py`(生成勿手编;base 事实:id/name/rarity/effect)+ `cw_investments.py`(手维护 overlay:STRATEGY_ECONOMY 73 / ENV_CATEGORY 83 / ENV_FACTION 36 / PICK_VALUE / ENV_PICK_VALUE / SURVIVAL_PICKS / `_MANUAL_EXTRAS` 补遗 1 条)+ 合并层(base × overlay → 注册表,孤儿键 raise)。
2. **生成器** `tools/cw/gen_plaza_invest.py`:在线拉 config(或 --cache)→ canon 键归一 → strip 富文本(通用标签 + •/剎 统一,`strategy_bindings` 文本提取依赖字符一致)→ 写 data 文件 + diff 报告(新增/移除/改名/品质变/效果变,by id)。
3. **数据修正落表**:13 条 rarity、5 条占位 effect、数值错全以 API 为准;14 条新增入表(飞光·映月 效果已知)。
4. **键 RENAME**(OCR 友好形):本姑娘就是罗剎→罗刹、摸个鱼Ⅲ→摸个鱼吧III、全角冒号/逗号条目归半角;注册表 335 = 334 base + 1 补遗(追击星徽套组(二),plaza 不收重复效果卡)。
5. **版本更新工作流**:重跑生成器 → 看 diff → 修 overlay 孤儿 → 完成。ADR-0133 的「图鉴轮补 19 漂移」待办关闭。
6. **双产物 + 双向链接(用户 2026-08-16 定)**:生成器同源产出**人读版** `docs/game/currency_war/data/invest_cards.md`(品质分组表格:棱彩/金/银 + 环境,id/名字/效果)—— 代码侧 effect 必须留(运行时消费:`strategy_bindings` 文本提取 + 图鉴采集效果守卫,搬文档断主链路),但翻阅/攻略引用归文档。两产物互写链接与生成器署名(勿手编 + 重跑命令);**双向链接锚 = plaza id**(代码 `source='plaza:<id>'` ↔ 文档 id 列)。同源生成无漂移通道,与手维护 doc 的双源漂移(本次删 investment_strategies.md 的原因)本质不同;模式对齐角色侧 `gen_plaza_chars.py`(代码 + characters/*.md 双产物)。

验证:CW 全套 410 passed(+6 守卫测试:base 完整性/overlay 无孤儿/键约定/数据修正/plaza 新增);ruff 过。

## 后续

- 装备侧重构同模式候选:API `equipment_list` 101 条带 `properties` 官方数值(11 维度:前台强度32件/速度30/后台30…)→ `_EQUIP_VALUE` 人工打分可升级数据驱动(策略层 ADR 另起)。
- rarity 修正对行为的实际影响(定点爆破等 5 条在 whitelist 恒赢不受影响;其余品质先验更准)待 live 观察。
