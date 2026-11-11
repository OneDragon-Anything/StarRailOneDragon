"""生成角色晋阶材料与副本产出常量(官方 wiki 快照 → src/sr_od/config 常量文件)。

数据流:官方 wiki → 本脚本(拉取+转换) → character_ascension_const.py /
dungeon_drop_const.py。版本更新后重跑刷新(数据块禁手改,单一源=官方 wiki)。

用法:PYTHONPATH=src 下 uv run python skills/sr-od-dev-character-data/scripts/generate_ascension_const.py
"""
import json
import re
import time
import urllib.parse
import urllib.request

import yaml

BASE = 'https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')
DELAY = 0.35

ASCEND_CONST_PATH = 'src/sr_od/config/character_ascension_const.py'
DUNGEON_CONST_PATH = 'src/sr_od/config/dungeon_drop_const.py'
GUIDE_YML_PATH = 'assets/game_data/interastral_peace_guide_data.yml'

# 段名合法格式(wiki tab「N级晋阶」),不符合的 tab(总量表/纯属性表)跳过
_STAGE_NAME_RE = re.compile(r'^\d+级晋阶$')

# wiki 来源串的「主干【区域】」结构(如「凝滞虚影【丹鼎司】」);无区域来源不匹配
_REGION_RE = re.compile(r'^(.*)【(.+?)】$')

# 副本/boss 名 join 用的归一化分隔符(wiki「•」与指南「·」混用,如
# 「不死的神实•历战余响」vs「不死的神实·历战余响」)
_DUNGEON_KEY_SEPARATORS = ('·', '•', '・')

# 区域名跨源异形字等化(wiki 写法 → 指南 yml 写法,join 前两边同归一;
# 实测分歧:™/TM、迴/廻、鳞/麟)。只用于比较,发射值保持指南侧拼写
_REGION_CHAR_VARIANTS: dict[str, str] = {'™': 'tm', '迴': '廻', '鳞': '麟'}

# 生成锚点:材料 → (分类, 指南 mission_name, 区域);不符即拒绝生成。
# 锁的是「材料→具体副本实例」join 链路的三条代表路径(虚影区域/余响 boss 名/花萼区域)
_MISSION_ANCHORS: dict[str, tuple[str, str, str]] = {
    '天人遗垢': ('凝滞虚影', '天人之形', '丹鼎司'),
    '无穷假身的遗恨': ('历战余响', '不死的神实·历战余响', '麟渊境'),
    '永恒之花': ('拟造花萼（赤）', '丰饶之蕾', '边缘通路'),
}

# 材料来源文本 → 指南分类名(副本可刷路由)的归一化规则。
# 键 = 来源文本去括号后的主干子串,值 = interastral_peace_guide_data.yml 的 category_name。
_SOURCE_CATEGORY_RULES: list[tuple[str, str]] = [
    ('拟造花萼', '拟造花萼（赤）'),   # 花萼按 usage 二分:晋阶类→赤,经验/信用点类→金(见 _caiyx_category)
    ('凝滞虚影', '凝滞虚影'),
    ('凝滞虛影', '凝滞虚影'),         # 官方词条繁体错字变体
    ('凝滯虛影', '凝滞虚影'),
    ('历战余响', '历战余响'),
    ('模拟宇宙', '差分宇宙'),         # 模拟宇宙刷取经差分宇宙入口(guide 分类无独立模拟宇宙)
    ('差分宇宙', '差分宇宙'),
]


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    if payload.get('retcode') != 0:
        raise RuntimeError(f'retcode={payload.get("retcode")} url={url}')
    return payload


def channel_items(channel_id: int) -> list[dict]:
    resp = get_json(f'{BASE}/home/content/list?app_sn=sr_wiki&channel_id={channel_id}&lang=zh-cn')
    items: list[dict] = []
    for group in resp['data']['list']:
        items.extend(group.get('list') or [])
    return items


def decode_templates(text: str) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(r'data-data="([^"]+)"', text):
        try:
            arr = json.loads(urllib.parse.unquote(m.group(1)))
        except json.JSONDecodeError:
            continue
        if isinstance(arr, list):
            out.extend(arr)
    return out


def calyx_category(usages: list[str]) -> str:
    """花萼来源的金/赤二分:晋阶类材料→赤;经验书/信用点→金。"""
    for usage in usages:
        if '晋阶' in usage:
            return '拟造花萼（赤）'
    for usage in usages:
        if '经验' in usage or '信用点' in usage:
            return '拟造花萼（金）'
    return '拟造花萼（赤）'  # 无用途线索时归赤(晋阶材料主分类)


def source_to_category(source: str, usages: list[str]) -> str | None:
    """来源文本 → 指南分类名;非副本途径(合成/商店/任务等)返回 None。"""
    if '拟造花萼' in source:
        return calyx_category(usages)
    for needle, category in _SOURCE_CATEGORY_RULES:
        if needle in source and needle != '拟造花萼':
            return category
    return None


def fetch_char_ascension(item: dict) -> dict[str, dict[str, int]] | None:
    """角色详情 → {段名: {材料名: 数量}};无晋阶组件返回 None。"""
    resp = get_json(f"{BASE}/content/info?app_sn=sr_wiki&content_id={item['content_id']}")
    rpg = resp['data']['content'].get('rpg_new_tmp_content') or {}
    comp = None
    for module in rpg.get('modules') or []:
        if module.get('name') == '角色晋阶':
            for c in module.get('components') or []:
                if c.get('componentId') == 'role_ascension':
                    comp = c
                    break
            break
    if comp is None:
        return None
    data = comp.get('data')
    payload = json.loads(data) if isinstance(data, str) else data
    stages: dict[str, dict[str, int]] = {}
    for tab in payload.get('list') or []:
        name = str(tab.get('tabName') or '').strip()
        if not _STAGE_NAME_RE.match(name):
            continue  # 总量表/纯属性表跳过,只留分段
        mats: dict[str, int] = {}
        for mat in tab.get('materials') or []:
            mat_name = str(mat.get('title') or '').strip()
            amount_raw = str(mat.get('amount') or '0').replace(',', '')
            if not mat_name:
                continue
            try:
                mats[mat_name] = int(amount_raw)
            except ValueError:
                continue
        if mats:
            stages[name] = mats
    return stages or None


def fetch_all() -> tuple[dict, dict, dict, dict]:
    """拉全部数据:角色分段材料 / 材料来源归类 / 非副本途径 / 副本来源原串。

    副本来源原串(带【区域】/boss 名)供「材料→具体副本实例」join 用。
    """
    char_data: dict[str, dict[str, dict[str, int]]] = {}
    dungeon_drops: dict[str, list[str]] = {}
    material_extra: dict[str, list[str]] = {}
    dungeon_sources: dict[str, list[tuple[str, str]]] = {}
    skipped: list[str] = []

    # 材料用途表(花萼金/赤二分要用;顺便产出 extra 途径)
    mats = channel_items(20)
    usage_of: dict[str, list[str]] = {}
    print(f'养成材料条目: {len(mats)}')
    for idx, item in enumerate(mats):
        title = item.get('title') or ''
        try:
            resp = get_json(f"{BASE}/content/info?app_sn=sr_wiki&content_id={item['content_id']}")
            for tab in resp['data']['content'].get('contents') or []:
                usages: list[str] = []
                for tmpl in decode_templates(tab.get('text') or ''):
                    data = tmpl.get('data') or {}
                    if 'material' not in data:
                        continue
                    usage_raw = str(data.get('type') or '')
                    usages = [s.strip() for s in usage_raw.replace('，', ',').split(',') if s.strip()]
                    for source in data.get('material') or []:
                        source_name = str(source.get('name') or '').strip()
                        if not source_name:
                            continue
                        category = source_to_category(source_name, usages)
                        if category is None:
                            material_extra.setdefault(title, [])
                            if source_name not in material_extra[title]:
                                material_extra[title].append(source_name)
                        else:
                            drops = dungeon_drops.setdefault(category, [])
                            if title not in drops:
                                drops.append(title)
                            if (category, source_name) not in dungeon_sources.setdefault(title, []):
                                dungeon_sources[title].append((category, source_name))
                    if usages:
                        usage_of[title] = usages
        except Exception as exc:
            skipped.append(f'材料 {title}: {exc}')
        time.sleep(DELAY)
        if (idx + 1) % 30 == 0:
            print(f'  材料进度 {idx + 1}/{len(mats)}')

    chars = channel_items(18)
    print(f'角色条目: {len(chars)}')
    for idx, item in enumerate(chars):
        title = item.get('title') or ''
        try:
            stages = fetch_char_ascension(item)
        except Exception as exc:
            skipped.append(f'角色 {title}: {exc}')
            stages = None
        if stages:
            char_data[title] = stages
        time.sleep(DELAY)
        if (idx + 1) % 20 == 0:
            print(f'  角色进度 {idx + 1}/{len(chars)},成功 {len(char_data)}')

    return char_data, dungeon_drops, material_extra, dungeon_sources


def _normalize_dungeon_key(text: str) -> str:
    """副本/boss 名 join 用归一化:去中点分隔符(wiki「•」与指南「·」混用)。"""
    for sep in _DUNGEON_KEY_SEPARATORS:
        text = text.replace(sep, '')
    return text


def _normalize_region_key(text: str) -> str:
    """区域名 join 用归一化:小写化 + 跨源异形字等化(见 _REGION_CHAR_VARIANTS)。"""
    lowered = text.lower()
    for variant, canonical in _REGION_CHAR_VARIANTS.items():
        lowered = lowered.replace(variant, canonical)
    return lowered


def _load_guide_missions() -> dict[str, list[dict[str, str]]]:
    """指南 yml → 分类名 → 关卡列表(mission_name/display_name/region_name)。"""
    with open(GUIDE_YML_PATH, encoding='utf-8') as f:
        tabs = yaml.safe_load(f)
    result: dict[str, list[dict[str, str]]] = {}
    for tab in tabs:
        for cate in tab.get('category_list') or []:
            result[str(cate['category_name'])] = [
                {'mission_name': str(mi.get('mission_name') or ''),
                 'display_name': str(mi.get('display_name') or ''),
                 'region_name': str(mi.get('region_name') or '')}
                for mi in cate.get('mission_list') or []
            ]
    return result


def _build_character_element_index() -> dict[str, str]:
    """角色常量 → 归一化中文名 → 属性中文;凝滞虚影同区域多虚影的属性消歧用。"""
    import sr_od.config.character_const as cc
    index: dict[str, str] = {}
    for obj in vars(cc).values():
        if isinstance(obj, cc.Character):
            index[_normalize_dungeon_key(obj.cn)] = obj.combat_type.cn
    return index


def _element_of_material(material: str, char_data: dict,
                         char_elements: dict[str, str]) -> str | None:
    """材料 → 属性中文(首个使用它的角色的属性);角色常量查无返回 None。"""
    for char_title, stages in char_data.items():
        if not any(material in mats for mats in stages.values()):
            continue
        normalized = _normalize_dungeon_key(char_title)
        if normalized in char_elements:
            return char_elements[normalized]
        hits = [key for key in char_elements if key.startswith(normalized)]
        if hits:
            return char_elements[hits[0]]
        return None  # 首个使用角色查无属性即止(同材料不会跨属性线)
    return None


def build_material_missions(dungeon_sources: dict[str, list[tuple[str, str]]],
                            char_data: dict) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    """副本来源原串 × 指南关卡 → 材料 → 具体副本实例映射({category,mission,region})。

    join 规则(按分类):
    - 凝滞虚影:区域匹配;同区域多虚影(如大矿区的物理/火)用材料属性消歧
      (属性 = 首个使用该材料的角色的属性);
    - 历战余响:来源 boss 名(去分类后缀)与指南 mission_name 归一化前缀匹配;
    - 拟造花萼金/赤:区域匹配;
    - 无区域来源(如「拟造花萼（金）」裸串/「差分宇宙」):无实例级信息,不产出
      条目——分类级可刷性仍由 DUNGEON_MATERIAL_DROPS 覆盖。
    未解析成功的来源记入 warnings(生成继续,锚点校验兜底)。
    """
    guide = _load_guide_missions()
    char_elements = _build_character_element_index()
    element_cache: dict[str, str | None] = {}

    def _element_of(material: str) -> str | None:
        if material not in element_cache:
            element_cache[material] = _element_of_material(material, char_data, char_elements)
        return element_cache[material]

    result: dict[str, list[dict[str, str]]] = {}
    warnings: list[str] = []
    for material, source_pairs in dungeon_sources.items():
        entries: list[dict[str, str]] = []
        for category, source in source_pairs:
            match = _REGION_RE.match(source)
            if match is None:
                continue
            stem, region = match.group(1), match.group(2)
            missions = guide.get(category) or []
            if category == '历战余响':
                boss = _normalize_dungeon_key(stem.replace('历战余响', '').strip())
                candidates = [mi for mi in missions
                              if _normalize_dungeon_key(mi['mission_name']).startswith(boss)]
            else:
                candidates = [mi for mi in missions
                              if _normalize_region_key(mi['region_name']) == _normalize_region_key(region)]
                if len(candidates) > 1 and category == '凝滞虚影':
                    element = _element_of(material)
                    if element:
                        prefixed = [mi for mi in candidates
                                    if mi['display_name'].startswith(f'{element}-')]
                        candidates = prefixed or candidates
            if not candidates:
                warnings.append(f'{material}: {source} → {category} 区域「{region}」无指南关卡')
                continue
            for mi in candidates:
                entry = {'category': category, 'mission': mi['mission_name'],
                         'region': mi['region_name']}
                if entry not in entries:
                    entries.append(entry)
        if entries:
            result[material] = entries
    return result, warnings


# 逻辑层(类+查询函数)随生成一并写入——逻辑改动 = 改本模板后重跑
_ASCEND_LOGIC_BLOCK = '''

class AscensionStage:
    """单次晋阶(一段)的材料需求。"""

    def __init__(self, name: str, materials: dict[str, int]):
        self.name: str = name
        """段名,与游戏内晋阶界面一致(如「30级晋阶」)"""
        self.materials: dict[str, int] = materials
        """该段材料需求 {材料名: 数量}"""

    def __repr__(self) -> str:
        return f'AscensionStage({self.name!r}, {self.materials!r})'


class CharacterAscension:
    """一名角色的完整晋阶材料表。"""

    def __init__(self, cn_name: str, stages: list[AscensionStage]):
        self.cn_name: str = cn_name
        """角色中文名"""
        self.stages: list[AscensionStage] = stages
        """晋阶段列表(按游戏内顺序,「20级晋阶」在前)"""

    @property
    def total(self) -> dict[str, int]:
        """满晋阶总量(各段合并)——判材料缺口用"""
        result: dict[str, int] = {}
        for stage in self.stages:
            for name, amount in stage.materials.items():
                result[name] = result.get(name, 0) + amount
        return result

    def total_to(self, stage_name: str) -> dict[str, int]:
        """升到指定段(含)的累计材料。

        :param stage_name: 目标段名(如「70级晋阶」);段名不存在 = 返回全量
        """
        result: dict[str, int] = {}
        for stage in self.stages:
            for name, amount in stage.materials.items():
                result[name] = result.get(name, 0) + amount
            if stage.name == stage_name:
                break
        return result


def get_character_ascension(cn_name: str) -> CharacterAscension | None:
    """角色中文名 → 晋阶材料表;表内无该角色返回 None。"""
    stages = _ASCENSION_DATA.get(cn_name)
    if stages is None:
        return None
    return CharacterAscension(cn_name, [AscensionStage(name, mats) for name, mats in stages.items()])


# 晋阶表键内出现过的中点分隔符(官方 wiki 快照「·」「•」混用,如
# 「开拓者·毁灭」与「开拓者•欢愉」并存)
_KEY_SEPARATORS: tuple[str, ...] = ('·', '•', '・')

#: 归一化键(去分隔符) → 原始表键
_NORMALIZED_KEY_INDEX: dict[str, str] = {}
for _name in _ASCENSION_DATA:
    _normalized = _name
    for _sep in _KEY_SEPARATORS:
        _normalized = _normalized.replace(_sep, '')
    _NORMALIZED_KEY_INDEX[_normalized] = _name


def find_character_ascension(character_cn: str) -> CharacterAscension | None:
    """角色定义中文名 → 晋阶材料表;比 get_character_ascension 多一层归一化匹配。

    角色定义的中文名(如「开拓者·毁灭·男」带性别后缀)与晋阶表键
    (「开拓者·毁灭」)不完全一致:归一化去分隔符后按前缀匹配——性别后缀
    不改变晋阶表(男/女同表),常规角色名精确等同。表内无该角色返回 None
    (裸「开拓者」不带命途也无法唯一定位,同返回 None,由调用方提示用全名)。
    """
    if character_cn in _ASCENSION_DATA:
        return get_character_ascension(character_cn)
    normalized = character_cn
    for sep in _KEY_SEPARATORS:
        normalized = normalized.replace(sep, '')
    hits = [key for key in _NORMALIZED_KEY_INDEX if normalized.startswith(key)]
    if len(hits) != 1:
        return None
    return get_character_ascension(_NORMALIZED_KEY_INDEX[hits[0]])
'''


def write_ascend_const(char_data: dict) -> None:
    head = '''"""角色晋阶材料表(分段):每段为一次晋阶(等级上限提升)的材料消耗。

本文件由 skills/sr-od-dev-character-data/scripts/generate_ascension_const.py 从官方 wiki 快照生成,
**禁手改**(单一源 = 官方 wiki;数据修正走重新生成)。
段名与游戏内晋阶界面一致(如「30级晋阶」= 30 级时的晋阶,晋阶后上限+10)。
"""
'''
    body = json.dumps(char_data, ensure_ascii=False, indent=1)
    with open(ASCEND_CONST_PATH, 'w', encoding='utf-8') as f:
        f.write(head)
        f.write('\n_ASCENSION_DATA: dict[str, dict[str, dict[str, int]]] = ')
        f.write(body)
        f.write('\n')
        f.write(_ASCEND_LOGIC_BLOCK)
    print(f'已生成 {ASCEND_CONST_PATH} ({len(char_data)} 名角色)')


def write_dungeon_const(dungeon_drops: dict, material_extra: dict,
                        material_missions: dict) -> None:
    head = '''"""副本产出材料表:指南分类名 → 该分类副本可产出的材料名清单。

本文件由 skills/sr-od-dev-character-data/scripts/generate_ascension_const.py 从官方 wiki 快照生成,
**禁手改**(单一源 = 官方 wiki;数据修正走重新生成)。
键与 assets/game_data/interastral_peace_guide_data.yml 的 category_name 对齐,
可直接经 SrGuideData 路由导航刷本。
"""
'''
    body = json.dumps(dungeon_drops, ensure_ascii=False, indent=1)
    extra_body = json.dumps(material_extra, ensure_ascii=False, indent=1)
    missions_body = json.dumps(material_missions, ensure_ascii=False, indent=1)
    tail = '''

def find_dungeon_by_material(material_name: str) -> list[str]:
    """材料名 → 可刷取该材料的副本分类名列表(按 DUNGEON_MATERIAL_DROPS 反查)。

    :param material_name: 材料中文名(与快照内名称一致)
    :return: 指南分类名列表(如 ['拟造花萼（赤）','凝滞虚影']);空 = 表内无可刷副本
    """
    return [category for category, drops in DUNGEON_MATERIAL_DROPS.items()
            if material_name in drops]


def find_missions_by_material(material_name: str) -> list[dict[str, str]]:
    """材料名 → 可刷取该材料的具体副本实例列表({category,mission,region})。

    比分类级 find_dungeon_by_material 细一层:mission/region 与指南关卡
    mission_name/region_name 同名对齐,可经指南数据定位具体关卡并规划刷本;
    仅来源串带【区域】/boss 名的材料有条目,其余返回空列表(用分类级兜底)。
    """
    return MATERIAL_MISSIONS.get(material_name, [])
'''
    with open(DUNGEON_CONST_PATH, 'w', encoding='utf-8') as f:
        f.write(head)
        f.write('\nDUNGEON_MATERIAL_DROPS: dict[str, list[str]] = ')
        f.write(body)
        f.write('\n\n# 非副本途径(合成/置换/商店/任务等,不走副本刷取)')
        f.write('\nMATERIAL_EXTRA_SOURCES: dict[str, list[str]] = ')
        f.write(extra_body)
        f.write('\n\n# 材料 → 具体副本实例(仅来源串带【区域】/boss 名的材料;与指南关卡同名对齐)')
        f.write('\nMATERIAL_MISSIONS: dict[str, list[dict[str, str]]] = ')
        f.write(missions_body)
        f.write('\n')
        f.write(tail)
    print(f'已生成 {DUNGEON_CONST_PATH} ({len(dungeon_drops)} 副本, '
          f'{len(material_extra)} 材料的非副本途径, {len(material_missions)} 材料的实例级映射)')


def main() -> None:
    char_data, dungeon_drops, material_extra, dungeon_sources = fetch_all()
    material_missions, mission_warnings = build_material_missions(dungeon_sources, char_data)
    for warning in mission_warnings:
        print(f'  [未解析] {warning}')
    for material, expected in _MISSION_ANCHORS.items():
        got = [(e['category'], e['mission'], e['region'])
               for e in material_missions.get(material) or []]
        if expected not in got:
            raise RuntimeError(f'锚点不符: {material} 期望 {expected}, 实得 {got}')
    write_ascend_const(char_data)
    write_dungeon_const(dungeon_drops, material_extra, material_missions)
    print('完成')


if __name__ == '__main__':
    main()
