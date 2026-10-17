# 新角色数据录入

版本新增可操作角色(限定 / 常驻 / 赠送 / 开拓者新形态)时,把角色数据录进项目。目标:新角色能出现在 GUI 配置下拉里、能被 OCR 读名与头像特征识别、能被配队与战斗逻辑使用。

**没做完下面 5 步不算完成。**

## checklist(必做)

1. ☐ 拉官方数据——按 sr-od-dev-official-api 的 `references/characters.md` 查该角色:中文名、英文名、命途、属性、稀有度、秘技描述。判据:字段齐全才往下走;空壳词条(有页面但字段缺失)与未实装角色(官方建了前瞻占位页,行迹模块名带「前瞻」;判读细节见该文档「已知坑」)一律不录入,等正式实装再跟【必做】
2. ☐ 录入 `src/sr_od/config/character_const.py`——按「字段录入规则」新增 Character 常量,追加进 CHARACTER_LIST 末尾。判据:import 后 `get_character_by_id('<新id>')` 能查到,旧角色不受影响【必做】
3. ☐ 新增头像模板 `assets/template/character_avatar/<id>/raw.webp`——按「头像模板」节。判据:目录名 = Character.id,无损 webp【必做】
4. ☐ 验证——按「验证」节。判据:ruff 无错;账号有该角色时实机识别认得出【必做】
5. ☐ 提交——git add 逐文件点名(character_const.py + 头像文件),commit message 写清新增了哪些角色【必做】

## 字段录入规则(character_const.py)

录入前先在 character_const.py 里 grep 确认 id 未被占用。常量名 = id 大写、空格转下划线(先例 MARCH7TH_PRESERVATION、YAO_GUANG),新常量插在最后一个角色常量之后、CHARACTER_LIST 之前。最小语法形式:

```python
NEW_CHAR = Character(id='example_id', cn='示例名', path=CHARACTER_PATH_HARMONY, combat_type=WIND, level=5, technique_type=TECHNIQUE_BUFF)
```

| 字段 | 规则 |
|---|---|
| id | 官方英文名归一化:小写、空格转下划线、其余符号删除(先例 The Herta → `the_herta`、Yao Guang → `yao_guang`、Robin • Summeretto → `robinsummeretto` 连写为历史个例,新角色按下划线规则)。形态 / 变体角色加后缀区分(先例 `march7th_hunt`、`silverwolf_999`)。id 定了不改:用户 config yaml 与头像目录都引用它 |
| cn | 官方中文名原文(含间隔号,如「阮•梅」)。开拓者形态写「开拓者·<命途>·<男/女>」(先例:开拓者·毁灭·男)。OCR 按这个名字做最长公共子序列匹配,必须与游戏内显示一致 |
| path | 现有命途常量直接用。新命途:文件头部新增 CharacterPath 常量 → 加入 CHARACTER_PATH_LIST → 按定位归入分类列表(主打伤害 → ATTACK_PATH_LIST;治疗 / 护盾 → SURVIVAL_PATH_LIST;增益 / 减益 → SUPPORT_PATH_LIST) |
| combat_type | 现有属性常量直接用;新属性:新增常量并加入 CHARACTER_COMBAT_TYPE_LIST |
| level | 官方稀有度:5 星 = 5,4 星 = 4 |
| technique_type | 按秘技描述分类,判据见下 |
| buff_lasting_seconds | 秘技增益持续时间(秒),战斗 op 用来估计何时需要重新放秘技。描述明确给秒数按描述;常驻 / 不消失类填 999(先例 ruanmei、yao_guang);拿不准用类默认 20 |

technique_type 分类判据(读秘技描述;分类决定战斗 op 先放秘技还是先攻击,拿不准就对比秘技描述同型的既有角色):

- 直接攻击敌人、无持续增益态 → `TECHNIQUE_ATTACK`
- 使用后获得持续增益,不攻击 → `TECHNIQUE_BUFF`
- 部署持续一段时间的领域 / 区域 → `TECHNIQUE_AREA`
- 获得增益、由攻击触发或强化后续攻击 → `TECHNIQUE_BUFF_ATTACK`
- 同上且增益在攻击后消失 → `TECHNIQUE_BUFF_ATTACK_DISAPPEAR`

两个按需的补充注册点:

- CHARACTER_LIST:新角色追加到列表末尾(按实装顺序,不是字母序)。
- SPECIAL_ATTACK_CHARACTER_LIST:仅当命途不是输出类、但玩法 op 需要把它当攻击位时才加(先例 KAFKA、ACHERON);没有 op 消费这个判断就不加。

## 头像模板

- 位置与命名:`assets/template/character_avatar/<id>/raw.webp`,`<id>` = Character.id,新建目录。
- 用途:大世界队伍栏、支援角色选择等场景的头像特征匹配兜底;OCR 读名是主通道,缺模板时兜底失效并报「角色头像文件缺失」。
- 获取:本机可用 skill 目录里有角色头像获取类 skill 就优先按它做(高清原图优于截图裁片);没有则进游戏裁该角色头像(图鉴 / 角色详情 / 编队界面,1080p 基准)。拿到的图不是 webp 就先无损转成 webp 再入库。
- 特征缓存按需自动生成(内存缓存),不需手工维护特征文件。

## 验证

1. ruff 只对本文件:`uv run ruff check src/sr_od/config/character_const.py`
2. import 校验(PowerShell,`<新id>` 换成实际 id):

   ```powershell
   $env:PYTHONPATH = "src"
   uv run python -c "from sr_od.config.character_const import CHARACTER_LIST, get_character_by_id; c = get_character_by_id('<新id>'); print(c.cn, c.path.id, c.combat_type.id, c.level, c.technique_type.id, c.technique_type.remark, c.buff_lasting_seconds); print(get_character_by_id('seele').cn)"
   ```

   判据:输出与录入意图一致(technique_type 类别看 remark——`TECHNIQUE_BUFF_ATTACK` 与 `TECHNIQUE_BUFF_ATTACK_DISAPPEAR` 的 id 相同,光看 id 区分不了);末尾旧角色抽查非 None。GUI 配置下拉同源 CHARACTER_LIST,此项通过即生效。
3. 实机识别(账号有该角色时):游戏内手动把新角色编入当前队伍、进大世界,经 MCP `run_operation` 跑 `CheckTeamMembersInWorld`(op_id = `sr_od.operations.team.check_team_members_in_world.CheckTeamMembersInWorld`),OCR 读名与头像兜底都应认出;头像认不出 → 重做头像模板(换裁切来源 / 尺寸)再验。
4. 账号没有该角色:第 3 步跳过,commit message 注明「头像模板待实机验证」。
