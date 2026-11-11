---
name: sr-od-dev-character-data
description: 维护崩坏:星穹铁道「角色数据」全流程的单一入口——官方数据拉取、权威表与注册表管线、项目录入规则、头像模板入库、验证提交。游戏版本更新时用于获取新角色信息(数据字段与头像模板素材)。数据接口细节归 sr-od-dev-official-api。英文:maintain character data pipeline, version update character data entry。
---

# 角色数据维护(全流程)

> **分工边界**:本 skill 是「一个角色数据从获取到录入验证」的流程编排 + 项目侧资产语义。
> - 数据**接口**(米游社/HoYoWiki 的 URL、字段位置、坑)→ `sr-od-dev-official-api`(单一源,本文不重复);
> - 头像素材的**离线批量获取手法**不在本文承载——本机若有素材获取类 skill 优先按它;没有则参考当前模板库,到游戏内截图,或到米游社尝试获取相关信息(拿到的图不是 webp 先无损转 webp)。
> - 项目侧资产(权威表快照、脚本、注册表规则)→ 本文与 `references/`、`scripts/`。

## 1. ID 匹配方案(先读)

角色在三个体系里各有标识,对齐关系如下:

```
官方数字 avatarId(米游社 wiki 详情接口,游戏内角色数字 ID)
    ↕ 权威表 references/characters-full.json(桥:每条含 avatarId + en_normalized)
项目 Character.id(英文代号,src/sr_od/config/character_const.py)
    ↕ 目录名直接相等(命名约定即注册表)
模板目录 assets/template/character_avatar/<Character.id>/raw.webp
```

- **模板链**:识别层(`src/sr_od/config/avatar_templates.py` 的 `iter_avatar_templates`)扫脸库目录,`目录名 == Character.id` 即默认衣装、`<Character.id>_skin<序号>` 即皮肤,对不上 CHARACTER_LIST 直接 raise——模板**不经过 avatar_id**,按 id 直连。不合命名目录 = 资产错误立即暴露。
- **数字 id 链**:`Character.avatar_id` 消费方 = 米游社详情查询(`src/sr_od/mys/sr_character_details.py`,行迹/星魂按 avatarId 索引)与 MCP 角色工具(`backend/mcp/character_tools.py`,按数字反查角色、解析行迹星魂)。
- **两链的桥** = 权威表:`en_normalized == Character.id` 主键对齐(脚本 `scripts/align_character_ids.py`),例外手工规则:开拓者 8001-8010 奇数男(caelum_*)偶数女(stelle_*)按命途配对;三月七 1224 官方名「仙舟三月七」无独立英文名 → march7th_hunt。
- 同名多形态角色**禁止裸中文名连表**(仙舟三月七撞车实证);新角色录入时 avatar_id 以米游社详情字段为准,勿猜。

## 2. 全流程 checklist(新角色出现时)

1. ☐ **拉官方数据**——接口与脚本见 sr-od-dev-official-api `references/characters.md`(拉取脚本 `fetch_sr_wiki_characters.py` + `fetch_hoyowiki_en_names.py`,缓存落项目 `.debug/temp/wiki_cache/`)。判据:中文名、英文名、avatarId、命途、属性、稀有度、秘技描述字段齐全;空壳词条(无 avatarId)、占位(avatarId=0)、前瞻未实装(见 §5)一律不录。
2. ☐ **权威表刷新(可选,推荐)**——本机若有角色数据维护管线则按其合并脚本归档权威表;快照随仓分发,跳过本步不影响后续录入。
3. ☐ **录入注册表**——`src/sr_od/config/character_const.py` 新增 Character 常量 + 追加 CHARACTER_LIST 末尾;字段规则见 §3。
4. ☐ **头像模板入库**——`assets/template/character_avatar/<Character.id>/raw.webp`;素材按开头口径获取,入库判据:目录名 = Character.id、无损 webp。
5. ☐ **验证**——见 §6。
6. ☐ **提交**——git add 逐文件点名(character_const.py + 头像文件),commit message 写清新增了哪些角色;账号没有该角色时注明「头像模板待实机验证」。

## 3. 字段录入规则(character_const.py)

录入前先 grep 确认 id 未被占用。常量名 = id 大写、空格转下划线(先例 MARCH7TH_PRESERVATION、YAO_GUANG),新常量插在最后一个角色常量之后、CHARACTER_LIST 之前。最小语法形式:

```python
NEW_CHAR = Character(id='example_id', cn='示例名', path=CHARACTER_PATH_HARMONY, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
```

| 字段 | 规则 |
|---|---|
| id | 官方英文名归一化:小写、空格转下划线、其余符号删除(先例 The Herta → `the_herta`、Yao Guang → `yao_guang`、Aeon☆Aha → `aeonaha`)。形态/变体角色加后缀区分(先例 `march7th_hunt`、`silverwolf_999`)。id 定了不改:用户 config yaml 与头像目录都引用它 |
| cn | 官方中文名原文(含间隔号与装饰符号,如「阮•梅」「星神★阿哈」「银狼LV.999」——特殊命名角色按游戏内显示名全录)。开拓者形态写「开拓者·<命途>·<男/女>」。OCR 按这个名字做最长公共子序列匹配,必须与游戏内显示一致 |
| path | 现有命途常量直接用。新命途:文件头部新增 CharacterPath 常量 → 加入 CHARACTER_PATH_LIST → 按定位归入分类列表(主打伤害 → ATTACK_PATH_LIST;治疗/护盾 → SURVIVAL_PATH_LIST;增益/减益 → SUPPORT_PATH_LIST) |
| combat_type | 现有属性常量直接用;新属性:新增常量并加入 CHARACTER_COMBAT_TYPE_LIST |
| level | 官方稀有度:5 星 = 5,4 星 = 4 |
| technique_type | 按秘技描述分类,判据见下 |
| buff_lasting_seconds | 秘技增益持续时间(秒),战斗 op 用来估计何时需要重新放秘技。描述明确给秒数按描述;常驻/不消失类填 999(先例 ruanmei、yao_guang);拿不准用类默认 20 |
| avatar_id | 米游社 wiki 详情的 avatarId(数字),权威表锚定;勿猜勿复用 |

technique_type 分类判据(读秘技描述;分类决定战斗 op 先放秘技还是先攻击,拿不准就对比秘技描述同型的既有角色):

- 直接攻击敌人、无持续增益态 → `TECHNIQUE_ATTACK`
- 使用后获得持续增益,不攻击 → `TECHNIQUE_BUFF`
- 部署持续一段时间的领域/区域 → `TECHNIQUE_AREA`
- 获得增益、由攻击触发或强化后续攻击 → `TECHNIQUE_BUFF_ATTACK`
- 同上且增益在攻击后消失 → `TECHNIQUE_BUFF_ATTACK_DISAPPEAR`

两个按需的补充注册点:

- CHARACTER_LIST:新角色追加到列表末尾(按实装顺序,不是字母序)。
- SPECIAL_ATTACK_CHARACTER_LIST:仅当命途不是输出类、但玩法 op 需要把它当攻击位时才加(先例 KAFKA、ACHERON);没有 op 消费这个判断就不加。

## 4. 头像模板库

### 用作识别模板:源选型与算法边界(实测结论)

**统一源 = 160×188 方形官方头像**(2026-11 裁定,脸库已全量按此重建;开拓者全系与三月七无独立数字 ID 保留旧模板)。选型依据(同一套模板跑三个消费场景,与 64×64 圆形列表角标源对照):

| 场景 | 渲染尺寸/尺度差 | 64×64 圆形源 | 160×188 方形源 |
|---|---|---|---|
| 编队列表卡(SIFT 整页匹配范式) | ~114px / 1.4 倍 | 特征贫乏模板 RANSAC 失败 | **命中**(卡芙卡 23→146 特征点) |
| 编队右侧槽位 | 56px / 2.2 倍 | conf 0.841 | **conf 0.860** |
| 大世界 HUD 队伍栏 | 38px / **4.2 倍** | 4 人全对 0.78-0.87 | **4 人全对 0.83-0.86** |

- SIFT 对 4.2 倍尺度差实测无碍;各场景渲染裁切形状不同(圆/方),不存在全场景同形状源,统一源取「分辨率最高、内容最全」者。模板匹配范式:小图裁片环境(比值测试竞争者少)对低分辨率模板友好,大图整页环境(全页特征竞争)必须高分辨率模板——项目已向整页匹配范式迁移,故选高分辨率方形源。
- 特征点无落盘缓存(`TemplateInfo.features` 运行时实时算),换图即生效。
- `matchTemplate` 像素比对不可用(2026-09-12 实测):重采样核差异使同角色分数天花板 ~0.93、不同角色 0.47~0.74 分数带重叠必误识;像素级定位场景仍截图裁切。

### 皮肤(衣装)模板

- 项目目录名约定 = `<Character.id>_skin<序号>`(皮肤挂哪个形态的 avatarId 就用哪个形态的全名,如三月七皮肤挂存护 `march7th_preservation_skin01`)。
- 识别层(`avatar_templates.py`)按命名约定解析,默认+皮肤统一仲裁,同位冲突按内点数取最高——穿已入库皮肤的角色可正常识别(实机帧验证:阮梅皮肤版经皮肤模板命中);穿未入库造型时识别失败为预期行为,候选诚实返回空,需要时获取新衣装素材补库。
- ⚠️ 项目角色 id 转写可能与常见拼写不同(如遐蝶 = `casorice` 非 castorice),以 character_const.py 为准。

### 小头像角标库(另一消费线)

`assets/template/character_avatar_mini/<项目角色id>.png` 为 64×64 小头像归档——装备替换列表「装备者头像角标」识别模板库,消费方 `src/sr_od/operations/equip_owner_match.py`(SIFT 双尺度 + 直方图/歧义双证据;算法取舍见项目测试仓 test_equip_owner_match.py)。归档工具见本机 skill。

## 5. 权威表与已知例外

权威表 = `references/characters-full.json`(含 cn/en/path/element/rarity/avatarId/hoyowiki_page_id);中间快照:characters-index-snapshot.json(索引兜底)、wiki-channel18-snapshot.json(米游社列表兜底)、id-map.json / id-map-full.json(头像源图特征匹配结论)。

随仓脚本:`fetch_character_details.py`(抓行迹满级+星魂详情)、`gen_character_details.py`(生成 `src/sr_od/mys/sr_character_details.py` 常量模块)、`align_character_ids.py`(权威表 ↔ 注册表 ID 对账)、`apply_avatar_ids.py`(注册表批量补 avatar_id,历史一次性)。本机若有完整维护管线(权威表合并/候选生成/头像批量归档),以其为准。

**前瞻未上线过滤**:wiki 详情里【角色行迹】模块名带「前瞻」(如「角色行迹前瞻【请以正式版本为准】」)= 角色未实装,**不录入**。只查模块名——正文文本提到「前瞻」不算(攻略正文常提及版本前瞻,整页文本搜索会误杀已上线角色)。

**已知例外**:1211 白露/1218 椒丘 wiki 词条是空壳(无 avatarId)→ 特征匹配/快照兜底(均已实锤);avatarId=0 = 占位词条(如真珠,已按占位录入标注);999 特殊头像两源皆无。

## 6. 验证

1. ruff 只对本文件:`uv run ruff check src/sr_od/config/character_const.py`——判据:**不新增违规**(本文件存量 `typing.List`/`Optional` 风格债不算,与改动前的发现集对比)。
2. import 校验(PowerShell,`<新id>` 换实际 id):

   ```powershell
   $env:PYTHONPATH = "src"
   uv run python -c "from sr_od.config.character_const import CHARACTER_LIST, get_character_by_id; c = get_character_by_id('<新id>'); print(c.cn, c.path.id, c.combat_type.id, c.level, c.technique_type.id, c.technique_type.remark, c.buff_lasting_seconds, c.avatar_id); print(get_character_by_id('seele').cn)"
   ```

   判据:输出与录入意图一致(technique_type 类别看 remark——`TECHNIQUE_BUFF_ATTACK` 与 `TECHNIQUE_BUFF_ATTACK_DISAPPEAR` 的 id 相同,光看 id 区分不了);末尾旧角色抽查非 None。GUI 配置下拉同源 CHARACTER_LIST,此项通过即生效。
3. 实机识别(账号有该角色时):游戏内手动把新角色编入当前队伍、进大世界,经 MCP `run_operation` 跑 `CheckTeamMembersInWorld`(op_id = `sr_od.operations.team.check_team_members_in_world.CheckTeamMembersInWorld`),OCR 读名与头像兜底都应认出;头像认不出 → 重做头像模板(换裁切来源/尺寸)再验。
4. 账号没有该角色:第 3 步跳过,commit message 注明「头像模板待实机验证」。

## 7. 依赖纪律

项目代码与流程不得硬依赖任何外部数据源(含米游社)——权威表与快照随仓分发(`references/`),即自有资产;刷新是可选动作,完全兜底 = 游戏内图鉴 OCR。
