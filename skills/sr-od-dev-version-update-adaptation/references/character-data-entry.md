# 新角色数据录入

版本新增可操作角色(限定 / 常驻 / 赠送 / 开拓者新形态)时,把角色数据录进项目。目标:新角色能出现在 GUI 配置下拉里、能被 OCR 读名与头像特征识别、能被配队与战斗逻辑使用。

**没做完下面 5 步不算完成。**

> 本适配项的完整方法(字段录入规则、秘技分类判据、头像模板算法边界、验证细节)承载在本机角色数据维护类 skill(若已挂载),本文只留步骤骨架与判据。本机没有对应 skill 时,按以下口径取材:参考当前模板库,到游戏内截图,或到米游社尝试获取相关信息。

## checklist(必做)

1. ☐ 拉官方数据——按 sr-od-dev-official-api 的 `references/characters.md` 查该角色:中文名、英文名、avatarId(游戏内数字 ID)、命途、属性、稀有度、秘技描述。判据:字段齐全才往下走;空壳词条(有页面但字段缺失)与未实装角色(官方建了前瞻占位页;判读细节见该文档「已知坑」)一律不录入,等正式实装再跟【必做】
2. ☐ 录入 `src/sr_od/config/character_const.py`——新增 Character 常量(插在最后一个角色常量之后),追加进 CHARACTER_LIST 末尾;录入前 grep 确认 id 未被占用,字段规则(id/cn/path/combat_type/level/technique_type/buff_lasting_seconds/avatar_id)见本机 skill。判据:import 后 `get_character_by_id('<新id>')` 能查到,旧角色不受影响【必做】
3. ☐ 新增头像模板 `assets/template/character_avatar/<id>/raw.webp`——目录名 = Character.id,无损 webp;头像素材获取与导出方法见本机 skill。判据:文件入库,非 webp 先无损转 webp【必做】
4. ☐ 验证——判据:ruff 无错(只对本文件,不新增违规);import 校验输出与录入意图一致;账号有该角色时实机识别认得出(OCR 读名 + 头像兜底),账号没有则 commit 注明「头像模板待实机验证」【必做】
5. ☐ 提交——git add 逐文件点名(character_const.py + 头像文件),commit message 写清新增了哪些角色【必做】
