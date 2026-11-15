"""生成角色行迹材料归属表(BWIKI 角色页「技能晋阶材料」→ src/sr_od/config 常量)。

数据源:BWIKI 各角色页的「技能晋阶材料」节主表(战技/终结技/天赋共用行,材料名
与游戏内一致)。行迹材料名随「命途线(拟造花萼赤三档)+实装年代(历战余响 boss
材料)」变化,**不是全角色统一**——数量统一表见 trace_levelup_const.py(仅数量,
名称为样本页口径),本表补「角色→行迹材料名」归属。

为何逐角色抓取:材料宇宙无法先验枚举(花萼赤分类清单混有晋阶材料与光锥经验书,
历战余响清单缺通用项),按角色页直接取表最准;页面缓存在 CACHE_DIR,可断点续跑。

可信度凭据(固化前强制校验的三重锚点,2026-11-15 实证):星神★阿哈→伪觉者的期许 /
黄泉→蛀星孕灾的旧恶 / 藿藿→无穷假身的遗恨——官方材料词条「来源」+BWIKI 材料页
「相关角色」+项目产出表三源交叉。

版本更新后重跑刷新(仅新增角色需新抓,已缓存页面不重复请求)。数据块禁手改。
EdgeOne 反爬:遇到限流(HTTP 567 等)脚本自动退避重试;仍失败时按提示手工缓存
该页 HTML 后重跑。
"""
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import sr_od.config.character_const as _cc

CACHE_DIR = Path('.debug/game_data/character/bwiki_char_pages')
WIKI_BASE = 'https://wiki.biligame.com/sr/'
OUT_PATH = 'src/sr_od/config/trace_material_const.py'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0'
FETCH_INTERVAL_SECONDS = 2.0
RETRY_TIMES = 3
RETRY_BACKOFF_SECONDS = 20.0

# 固化前强制校验的锚点:{角色中文名: 必须命中的材料名}——任一失败即中止
_ANCHORS: dict[str, str] = {
    '星神★阿哈': '伪觉者的期许',
    '黄泉': '蛀星孕灾的旧恶',
    '藿藿': '无穷假身的遗恨',
}

# BWIKI 页面标题与角色定义中文名不一致的固定映射(表键仍用角色定义名):
# 开拓者新形态与仙舟三月七的 BWIKI 命名带全角间隔号/换序,直连 404
BWIKI_TITLE_OVERRIDES: dict[str, str] = {
    '开拓者·同谐': '开拓者•同谐',
    '开拓者·欢愉': '开拓者•欢愉',
    '仙舟三月七': '三月七•巡猎',
}

#: 开拓者形态中文名(开拓者·<命途>·男/女) → BWIKI 页面标题与表键(无性别后缀)
_TRAILBLAZER_PATTERN = re.compile(r'^开拓者·(.+)·[男女]$')


def character_fetch_targets() -> dict[str, str]:
    """角色定义清单 → {表键: BWIKI 页面标题}(开拓者形态取无性别后缀标题)。"""
    targets: dict[str, str] = {}
    for obj in vars(_cc).values():
        if not isinstance(obj, _cc.Character):
            continue
        m = _TRAILBLAZER_PATTERN.match(obj.cn)
        key = f'开拓者·{m.group(1)}' if m else obj.cn
        targets.setdefault(key, BWIKI_TITLE_OVERRIDES.get(key, key))
    return targets


def fetch_html(title: str) -> str:
    """抓取角色页 HTML(带本地缓存与限流退避,失败给出手工缓存指引)。"""
    cache_file = CACHE_DIR / f'{title}.html'
    if cache_file.exists():
        return cache_file.read_text(encoding='utf-8')
    url = WIKI_BASE + urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_TIMES + 1):
        try:
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(html, encoding='utf-8')
            time.sleep(FETCH_INTERVAL_SECONDS)
            return html
        except Exception as exc:  # noqa: BLE001 统一走退避重试/缓存指引
            last_exc = exc
            if attempt < RETRY_TIMES:
                print(f'  [{title}] 第 {attempt} 次拉取失败({exc}),退避重试')
                time.sleep(RETRY_BACKOFF_SECONDS)
    raise RuntimeError(
        f'角色页拉取失败:{title}({last_exc})——请用浏览器访问 {url} 并把页面源码'
        f'手工存为 {cache_file} 后重跑(已缓存页面不会重复请求)'
    ) from last_exc


def parse_trace_material_names(html: str) -> list[str]:
    """解析「技能晋阶材料」节主表 → 材料名列表(img alt,保序去重)。"""
    anchors = [m.start() for m in re.finditer(r'id="技能晋阶材料"', html)]
    if not anchors:
        return []
    seg = html[anchors[-1]: anchors[-1] + 30000]
    tables = re.findall(r'<table.*?</table>', seg, re.S)
    if not tables:
        return []
    names: list[str] = []
    for m in re.finditer(r'alt="([^"]+)"', tables[0]):
        name = m.group(1).strip()
        if name and '.png' not in name and name not in names:
            names.append(name)
    return names


def bind_characters(targets: dict[str, str]) -> dict[str, list[str]]:
    """逐角色抓取 → {表键: 材料名列表};解析失败的键显式报告。"""
    binding: dict[str, list[str]] = {}
    failed: list[str] = []
    empty: list[str] = []
    total = len(targets)
    for idx, (key, title) in enumerate(targets.items(), start=1):
        try:
            names = parse_trace_material_names(fetch_html(title))
        except RuntimeError as exc:
            print(f'  [{idx}/{total}] {key}: {exc}')
            failed.append(key)
            continue
        if not names:
            empty.append(key)
        binding[key] = names
        if idx % 10 == 0:
            print(f'角色进度 {idx}/{total}')
    if empty:
        print(f'[警告] {len(empty)} 个角色页无「技能晋阶材料」节或表为空: {empty}')
    if failed:
        print(f'[失败] {len(failed)} 个角色页未抓到(见上方指引,补缓存后重跑): {failed}')
    return binding


def check_anchors(binding: dict[str, list[str]]) -> None:
    """锚点校验:样本角色的绑定必须包含已实证的材料,任一失败即中止。"""
    failures = {
        character: expected
        for character, expected in _ANCHORS.items()
        if expected not in binding.get(character, [])
    }
    if failures:
        raise RuntimeError(f'锚点校验失败(页面数据可疑或解析结构变更): {failures}')


def write_const(binding: dict[str, list[str]]) -> None:
    import pprint

    head = '''"""角色行迹材料归属表(BWIKI 角色页「技能晋阶材料」节)。

本文件由 skills/sr-od-dev-character-data/scripts/generate_trace_material_const.py 生成,
**禁手改**(数据修正走重新生成)。
- 行迹材料名随「命途线(拟造花萼赤三档)+实装年代(历战余响 boss 材料)+版本特殊项」
  变化,非全角色统一;数量统一表见 trace_levelup_const.py(仅数量,名称为样本页口径)。
- 键 = 角色中文名(开拓者形态无性别后缀,查询走 find_ 函数归一化);列表为该角色
  「技能晋阶材料」表出现的材料名(保序去重,含信用点)。
- 可信度凭据:三重锚点(星神★阿哈→伪觉者的期许 / 黄泉→蛀星孕灾的旧恶 /
  藿藿→无穷假身的遗恨)固化前强制校验,2026-11-15 三源交叉实证。
"""

'''
    body = '_CHARACTER_TRACE_MATERIALS: dict[str, list[str]] = '
    body += pprint.pformat(binding, width=100, sort_dicts=False)
    tail = '''

#: 归一化键(去 ·/• 分隔符) → 原始表键;消费方中文名可能带性别/形态后缀
_NORMALIZED_KEY_INDEX: dict[str, str] = {}
for _name in _CHARACTER_TRACE_MATERIALS:
    _normalized = _name
    for _sep in ('·', '•'):
        _normalized = _normalized.replace(_sep, '')
    _NORMALIZED_KEY_INDEX[_normalized] = _name


def find_character_trace_materials(character_cn: str) -> list[str] | None:
    """角色定义中文名 → 行迹材料名列表;归一化去分隔符后按前缀匹配(同
    find_character_ascension 口径:性别后缀向后兼容,裸「开拓者」无法唯一定位
    返回 None 由调用方提示用全名)。表未收录返回 None。"""
    normalized = character_cn
    for sep in ('·', '•'):
        normalized = normalized.replace(sep, '')
    hits = [key for key in _NORMALIZED_KEY_INDEX if normalized.startswith(key)]
    if len(hits) != 1:
        return None
    return list(_CHARACTER_TRACE_MATERIALS[_NORMALIZED_KEY_INDEX[hits[0]]])
'''
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(head)
        f.write(body)
        f.write('\n')
        f.write(tail)
    print(f'已生成 {OUT_PATH} ({len(binding)} 名角色)')


def main() -> None:
    targets = character_fetch_targets()
    print(f'待抓取角色 {len(targets)} 名(已缓存页面不重复请求)')
    binding = bind_characters(targets)
    check_anchors(binding)
    write_const(binding)


if __name__ == '__main__':
    main()
