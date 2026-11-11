---
name: sr-od-dev-character-data
description: 维护崩坏:星穹铁道「角色数据」全流程的单一入口——拉取全量角色列表(含星魂/行迹)、按列表更新项目代码文件、头像模板获取。游戏版本更新时用于获取新角色信息。数据接口细节归 sr-od-dev-official-api;头像离线批量获取手法归本机解包类 skill。英文:maintain character data pipeline, version update character data entry。
---

# 角色数据维护

> 分工:wiki 接口的调用细节(URL/字段位置/坑)→ `sr-od-dev-official-api`;头像素材的离线批量获取手法→本机解包类 skill(若挂载);本文只管流程编排与项目侧定义。

## 1. 拉取全量角色列表(存临时目录)

| 拉取内容 | 脚本 | 临时产物 |
|---|---|---|
| 角色列表 + 基础字段(中文名/avatarId/命途/属性/星级/秘技) | official-api 的 `fetch_sr_wiki_characters.py` | `.debug/temp/wiki_cache/wiki_channel18.json` + `details/<content_id>.json` |
| 官方英文名 | official-api 的 `fetch_hoyowiki_en_names.py` | `.debug/temp/wiki_cache/hoyowiki_en_names.json` |
| 行迹满级 + 星魂全 6 详情 | 本 skill `scripts/fetch_character_details.py` | `.debug/temp/char_wiki/char_details.json` |

- 接口细节(域名/参数/字段位置/已知坑)见 sr-od-dev-official-api `references/characters.md`,本文不重复。
- 运行方式:项目根目录 `uv run python <脚本路径>`(official-api 两个脚本仅标准库;本 skill 脚本需 `PYTHONPATH=src`)。
- **收录判据**:关键字段齐全才收录;空壳词条(有页面无 avatarId)、占位(avatarId=0)、前瞻未实装(详情行迹**模块名**带「前瞻」,正文提及不算)一律不录。
- 权威表快照随仓分发(`references/characters-full.json`,数字 ID ↔ 中文名/英文名/命途/属性/星级),是各脚本与人工对账的锚;刷新合并是可选动作(本机解包类 skill 有合并管线),不刷不影响按列表录入。

## 2. 按角色列表更新项目代码文件

| 代码文件 | 方式 | 生成器/操作 | 验证判据 |
|---|---|---|---|
| `src/sr_od/config/character_const.py` | **手动** | 新增 Character 常量(插最后一个常量后)+ 追加 CHARACTER_LIST 末尾;字段规则见附录 A | import 后 `get_character_by_id('<新id>')` 命中且字段正确;旧角色抽查非 None;ruff 不新增违规 |
| `src/sr_od/mys/sr_character_details.py` | 脚本生成 | `uv run python skills/sr-od-dev-character-data/scripts/gen_character_details.py`(输入步骤 1 的 char_details.json) | `resolve_traces(<avatarId>)`/`resolve_eidolons(<avatarId>)` 非空 |
| `src/sr_od/config/character_ascension_const.py` + `src/sr_od/config/dungeon_drop_const.py` | 脚本生成 | `uv run python skills/sr-od-dev-character-data/scripts/generate_ascension_const.py`(官方 wiki 直拉) | `find_character_ascension('<cn>')` 命中 |
| `src/sr_od/config/trace_levelup_const.py` | 脚本生成(低频) | `generate_trace_cost_const.py`;全 5 星统一固定表,仅游戏机制变更时重跑 | 表结构不变即无需动 |

- 生成器均项目根运行(`PYTHONPATH=src`);产物头部注释由生成器写入,**禁手改常量数据块**(单一源 = 官方 wiki,修正走重新生成)。
- 实机验证(账号有该角色时):编入队伍进大世界,经 MCP `run_operation` 跑 `CheckTeamMembersInWorld`(op_id `sr_od.operations.team.check_team_members_in_world.CheckTeamMembersInWorld`),OCR 读名与头像兜底都认出;账号没有则提交信息注明「头像模板待实机验证」。
- **边界**:角色专属光锥/遗器归装备数据维护域的版本工序,不在本流程。

## 3. 头像获取

- 默认模板库:`assets/template/character_avatar/<Character.id>/raw.webp`,目录名 = Character.id,图非 webp 先无损转 webp。
- 获取途径:本机解包类 skill 有头像导出手法(游戏版本更新拿新角色头像模板从这走)优先按它;没有则参考当前模板库、到游戏内截图、或到米游社获取。
- 统一源口径:160×188 方形官方头像;皮肤衣装模板目录 `<Character.id>_skin<序号>`(定义见附录 B)。
- 小头像角标库(64×64)的归档见附录 C,新角色如需角标同步归档。

## 附录 A. 项目 Character id 定义

- **id**:官方英文名归一化——小写、空格转下划线、其余符号删除(先例 The Herta → `the_herta`、Yao Guang → `yao_guang`、Aeon☆Aha → `aeonaha`);形态/变体加后缀(先例 `march7th_hunt`、`silverwolf_999`)。id 定了不改:用户 config yaml 与头像目录都引用它。
- **cn**:游戏内显示名原文(含间隔号与装饰符号,如「阮•梅」「星神★阿哈」「银狼LV.999」);开拓者形态写「开拓者·<命途>·<男/女>」。OCR 按此名做最长公共子序列匹配,必须与游戏内显示一致。
- **avatar_id**:米游社 wiki 详情的数字 avatarId(权威表锚定);勿猜勿复用。
- **path / combat_type / level**:现有常量直接用;新命途按定位归入 ATTACK(输出)/SURVIVAL(生存)/SUPPORT(辅助)分类列表;level = 稀有度(5 星 = 5)。
- **technique_type**(读秘技描述分类,决定战斗 op 先放秘技还是先攻击):直接攻击无增益 → `TECHNIQUE_ATTACK`;获得持续增益不攻击 → `TECHNIQUE_BUFF`;部署持续领域 → `TECHNIQUE_AREA`;增益由攻击触发或强化攻击 → `TECHNIQUE_BUFF_ATTACK`;同上且攻击后消失 → `TECHNIQUE_BUFF_ATTACK_DISAPPEAR`。拿不准就对比同型既有角色。
- **buff_lasting_seconds**:秘技增益持续秒数;描述明确给秒数按描述,常驻类填 999(先例 ruanmei),拿不准用默认 20。
- **注册点**:CHARACTER_LIST 追加末尾(按实装顺序);SPECIAL_ATTACK_CHARACTER_LIST 仅当非输出命途但玩法 op 需当攻击位才加(先例 KAFKA、ACHERON),无消费方不加。
- **对齐链**:`avatarId ↔ 权威表(references/characters-full.json,键 en_normalized == Character.id) ↔ 模板目录名`。消费方:`src/sr_od/config/avatar_templates.py`(模板链,目录名直连)、`src/sr_od/mys/sr_character_details.py` 与 `src/sr_od/backend/mcp/character_tools.py`(数字 id 链)。例外:开拓者 8001-8010 奇数男(caelum_*)偶数女(stelle_*)按命途配对;三月七 1224 官方名「仙舟三月七」无独立英文名 → march7th_hunt;同名多形态禁止裸中文名连表。

## 附录 B. 皮肤头像模板 id 定义

- 目录名 = `<Character.id>_skin<序号>`;皮肤挂哪个形态的 avatarId 就用哪个形态的全名(先例:三月七皮肤挂存护 = `march7th_preservation_skin01`)。
- 识别层(`avatar_templates.py`)按命名约定解析:目录名 == Character.id 即默认衣装,`_skin<序号>` 即皮肤,两者皆非直接 raise——不合命名目录会在遍历时立即暴露。
- ⚠️ 项目 id 转写可能与常见拼写不同(如遐蝶 = `casorice` 非 castorice),以 character_const.py 为准。

## 附录 C. 两个模板库的位置与用途

| 模板库 | 内容 | 消费方 | 用途 |
|---|---|---|---|
| `assets/template/character_avatar/` | 160×188 方形头像(默认 + 皮肤) | `src/sr_od/config/avatar_templates.py`(`iter_avatar_templates`,默认+皮肤统一仲裁,同位冲突按内点数取最高) | 大世界队伍栏、编队、支援选择等场景的角色头像特征识别(OCR 读名为主通道,此为兜底) |
| `assets/template/character_avatar_mini/` | 64×64 小头像 | `src/sr_od/operations/equip_owner_match.py` | 装备替换列表的「装备者头像角标」识别 |
