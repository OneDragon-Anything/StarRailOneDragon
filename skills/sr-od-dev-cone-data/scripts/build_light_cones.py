"""光锥管道单脚本:wiki 双缓存 → 直接产出 src/sr_od/mys/sr_light_cones.py 常量模块。

中间权威表 JSON 已废除(2026-11-12):原 build/gen 两步经 cones-full.json 中转,
现合并为单脚本内存传递,skill 仓里只留「脚本 + 脚本直接产出的常量模块」。
对账锚 = git 历史常量版本:重生成后 diff 现模块,冻结纪律保证已有词条不动、
漂移仅报告人工核对。

输入(拉取缓存,先跑同目录两个 fetch 脚本刷新):
  .debug/game_data/cone/wiki/cone_details_cn.json      (fetch_sr_wiki_cone_list.py 产物)
  .debug/game_data/cone/wiki/hoyowiki_cone_en_names.json (fetch_hoyowiki_cone_en_names.py 产物)
  src/sr_od/mys/sr_light_cones.py                  (文本解析,取条目顺序与分段;兼冻结源)

产出:src/sr_od/mys/sr_light_cones.py(完整模块,含 id 字段)。

纪律:
- 数据块禁手改(单一源 = 官方 wiki,修正走重新生成);
- manual 行(官方公告占位,wiki 未收录)跳过不生成,等 wiki 上线后随 diff 进模块;
- 已有词条 obtain/skill 冻结保留(wiki 侧存在编辑损坏),文本漂移仅报告人工核对;
- 生成后人工审阅 diff:skill/obtain 文本与旧模块的漂移要逐条过目(wiki 侧回改)。

校验:名称唯一 / id 唯一且仅小写字母数字(允许空串=国际服未同步) / 星级与命途枚举 /
图标归档缺失仅警告(归档走图标工序,不阻塞生成)。
项目根目录运行:uv run python skills/sr-od-dev-cone-data/scripts/build_light_cones.py
"""
import json
import re
import sys
from html import unescape
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
DETAILS = PROJECT_ROOT / '.debug' / 'game_data' / 'cone' / 'wiki' / 'cone_details_cn.json'
EN_NAMES = PROJECT_ROOT / '.debug' / 'game_data' / 'cone' / 'wiki' / 'hoyowiki_cone_en_names.json'
MODULE = PROJECT_ROOT / 'src' / 'sr_od' / 'mys' / 'sr_light_cones.py'
OUT = MODULE
TEMPLATE_DIR = PROJECT_ROOT / 'assets' / 'template' / 'light_cone_icon'

CN_NORM = str.maketrans({'•': '·', '・': '·', '．': '.', ' ': '', '\u3000': ''})

CAREER_TO_PATH = {
    '存护': 'preservation', '智识': 'erudition', '巡猎': 'hunt', '同谐': 'harmony',
    '毁灭': 'destruction', '丰饶': 'abundance', '虚无': 'nihility',
    '记忆': 'remembrance', '欢愉': 'elation',
}

VALID_PATHS = set(CAREER_TO_PATH.values())

# wiki 尚未收录、但已有官方公告名的新词条(id/rarity/path 以公告为准;wiki 同步后自动转正)。
# 2300x 段续排 tid 由客户端资产侧证实存在,skill/obtain 等词条数据以 wiki 上线为准。
MANUAL_ENTRIES: list[dict] = []

_SEG_RE = re.compile(r'# ---- (.+?) ----')
_NAME_RE = re.compile(r"name='(.+?)',")
_FROZEN_RE = re.compile(
    r"name='(?P<name>[^']*)',\n"
    r"        rarity=\d+,\n"
    r"        path_id='[a-z]+',\n"
    r"        obtain='(?P<obtain>[^']*)',\n"
    r"        skill='(?P<skill>[^']*)',")
_TAG_RE = re.compile(r'<[^>]+>')


def parse_module_order() -> list[dict]:
    """模块文本 → [{name, segment, order}](按出现序)。"""
    rows: list[dict] = []
    segment = ''
    for line in MODULE.read_text(encoding='utf-8').splitlines():
        mc = _SEG_RE.search(line)
        if mc:
            segment = mc.group(1).strip()
            continue
        mc = _NAME_RE.search(line)
        if mc:
            rows.append({'name': mc.group(1), 'segment': segment, 'order': len(rows)})
    return rows


def norm_cn(name: str) -> str:
    return name.translate(CN_NORM).lower()


def py_str(text: str) -> str:
    """字符串字面量转义(单引号+反斜杠+真实换行转 \\n)。"""
    return "'" + text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def plain_text(raw: str) -> str:
    """wiki skill/obtain 文本归一化:逐标签转空格(【】梯度两侧空格即由此而来)+
    HTML 实体解码+空白折叠。结构化词条(纯文本)经此为恒等变换,旧模板 HTML 词条
    剥后与结构化词条同构。"""
    text = _TAG_RE.sub(' ', raw)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_frozen_texts() -> dict[str, dict[str, str]]:
    """现模块 → {名称: {obtain, skill}}(转义原文,回写时原样复用不做二次转义)。"""
    frozen: dict[str, dict[str, str]] = {}
    for m in _FROZEN_RE.finditer(MODULE.read_text(encoding='utf-8')):
        frozen[m['name']] = {'obtain': m['obtain'], 'skill': m['skill']}
    return frozen


def build_table(details: dict[str, dict], en_map: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """wiki 详情 × intl 英文名 × 模块排序 → 权威表(内存) + 问题清单。"""
    module_rows = parse_module_order()
    table: dict[str, dict] = {}
    problems: list[str] = []
    used_cids: set[str] = set()
    for row in module_rows:
        key = norm_cn(row['name'])
        cid = next((cid for cid, r in details.items() if r.get('title') == row['name']), None)
        record = details.get(cid) if cid is not None else None
        if record is None:
            problems.append(f'{row["name"]}: wiki 详情缺失')
            continue
        used_cids.add(cid)
        en_row = en_map.get(key)
        career = record.get('career') or ''
        if career not in CAREER_TO_PATH:
            problems.append(f'{row["name"]}: 未知命途 {career!r}')
            continue
        rate_digits = re.sub(r'[^0-9]', '', record.get('rate') or '')
        if rate_digits not in ('3', '4', '5'):
            problems.append(f'{row["name"]}: 未知星级 {record.get("rate")!r}')
            continue
        table[key] = {
            'cn': row['name'],
            'en': en_row['en'] if en_row else '',
            'id': en_row['en_normalized'] if en_row else '',
            'rarity': int(rate_digits),
            'path_id': CAREER_TO_PATH[career],
            'wiki_content_id': int(cid),
            'hoyowiki_page_id': en_row['hoyowiki_page_id'] if en_row else None,
            'order': float(row['order']),
            'segment': row['segment'],
            'source': 'wiki',
        }

    # 人工登记行:仅占 wiki 未收录的键;wiki 同步后同键自动被 wiki 行覆盖
    for manual in MANUAL_ENTRIES:
        key = norm_cn(manual['cn'])
        if key in table:
            problems.append(f'人工行 {manual["cn"]}: wiki 已收录,删除 MANUAL_ENTRIES 该行')
            continue
        seg_max = max((r['order'] for r in table.values() if r['segment'] == manual['segment']),
                      default=-1)
        table[key] = {
            'cn': manual['cn'], 'en': '', 'id': '', 'rarity': manual['rarity'],
            'path_id': manual['path_id'], 'wiki_content_id': None,
            'hoyowiki_page_id': None, 'order': seg_max + 0.5,
            'segment': manual['segment'], 'source': 'manual',
            'note': manual.get('note', ''),
        }

    unused = sorted(set(details) - used_cids)
    if unused:
        problems.append(f'wiki 详情未被模块引用: {[details[c]["title"] for c in unused]}')

    id_vals = [r['id'] for r in table.values() if r['id']]
    dup = {v for v in id_vals if id_vals.count(v) > 1}
    if dup:
        problems.append(f'id 重复: {sorted(dup)}')
    return table, problems


def main() -> int:
    details: dict[str, dict] = json.loads(DETAILS.read_text(encoding='utf-8'))
    en_map: dict[str, dict] = json.loads(EN_NAMES.read_text(encoding='utf-8'))
    print(f'wiki 详情 {len(details)} 条 / intl 互连 {len(en_map)} 条')

    table, build_problems = build_table(details, en_map)
    n_en = sum(1 for r in table.values() if r['en'])
    n_manual = sum(1 for r in table.values() if r['source'] == 'manual')
    print(f'权威表(内存) {len(table)} 条(en 已回填 {n_en},manual {n_manual})')

    frozen = parse_frozen_texts()

    rows = sorted(table.values(), key=lambda r: r['order'])
    problems = list(build_problems)
    skipped_manual: list[str] = []
    drift: list[str] = []
    fresh_names: list[str] = []
    entries: list[dict] = []
    for row in rows:
        if row['source'] != 'wiki' or row.get('wiki_content_id') is None:
            skipped_manual.append(row['cn'])
            continue
        record = details.get(str(row['wiki_content_id']))
        if record is None:
            problems.append(f"{row['cn']}: wiki 详情缺失(cid={row['wiki_content_id']})")
            continue
        name = row['cn']
        fresh_obtain = py_str(plain_text(record.get('obtain') or ''))[1:-1]
        fresh_skill = py_str(plain_text(record.get('skill') or ''))[1:-1]
        old = frozen.get(name)
        if old is not None:
            # 固化纪律:已有词条 obtain/skill 以现模块为准(wiki 侧存在编辑损坏,
            # 如梯度列表粘连),wiki 只喂新增词条;文本漂移仅报告供人工核对 wiki。
            if old['obtain'] != fresh_obtain or old['skill'] != fresh_skill:
                drift.append(name)
            entries.append({**row, 'obtain': old['obtain'], 'skill': old['skill']})
        else:
            fresh_names.append(name)
            entries.append({**row, 'obtain': fresh_obtain, 'skill': fresh_skill})

    names = [e['cn'] for e in entries]
    if len(names) != len(set(names)):
        problems.append('名称重复')
    ids = [e['id'] for e in entries if e['id']]
    if len(ids) != len(set(ids)):
        problems.append('id 重复')
    bad_id = [e['id'] for e in entries if e['id'] and not re.fullmatch(r'[a-z0-9]+', e['id'])]
    if bad_id:
        problems.append(f'id 含非法字符: {bad_id}')
    for e in entries:
        if e['rarity'] not in (3, 4, 5):
            problems.append(f"{e['cn']}: 星级 {e['rarity']}")
        if e['path_id'] not in VALID_PATHS:
            problems.append(f"{e['cn']}: 命途 {e['path_id']}")
        if not e['skill']:
            problems.append(f"{e['cn']}: skill 为空")
        # obtain 允许为空:旧模板词条无「实装版本」键值行(先例 暖夜不会漫长)

    n = len(entries)
    if problems:
        print('校验失败,未写盘:')
        for p in problems:
            print(f'  {p}')
        return 1

    lines: list[str] = []
    lines.append('"""米游社光锥快照常量与查询助手。')
    lines.append('')
    lines.append('数据分层：定义层+skill 特效文本固化——id/名称/星级/命途/获取途径+skill 特效')
    lines.append('文本（官方 wiki 原文透传，含五档叠影数值）；光锥故事**不固化**；游戏内部')
    lines.append('数字 tid 不入本模块（tid 与名称的映射不在公开仓维护）。')
    lines.append('固化语义：obtain/skill 文本固化后本模块即唯一权威载体——重生成时已有词条')
    lines.append('冻结保留（wiki 侧存在编辑损坏，漂移由生成器报告供人工核对），wiki 只喂新增。')
    lines.append('')
    lines.append('id 定义：英文代号 = 官方英文名归一化（小写仅字母数字），来源国际版 HoYoWiki。')
    lines.append('')
    lines.append('图标模板:``assets/template/light_cone_icon/<id>/raw.webp``(TemplateLoader')
    lines.append('规范二级结构,按 id 寻址;id 为空串的把暂缺,等 wiki 同步补 id 后归档)。')
    lines.append('')
    lines.append('版本刷新工序：游戏新版本后重跑官方 wiki 抓取并重新生成本模块（生成器随本仓')
    lines.append('skills/sr-od-dev-cone-data/ 维护）→ 与下方 LIGHT_CONES 逐条 diff → 人工审阅后')
    lines.append('更新常量；勿临时塞未经核验的数据。')
    lines.append('')
    lines.append('模块纪律：零外部 IO、零状态——纯常量 + 纯函数（同 sr_relic_sets 模块纪律）。')
    lines.append('"""')
    lines.append('')
    lines.append('from dataclasses import dataclass')
    lines.append('')
    lines.append('')
    lines.append('@dataclass(frozen=True)')
    lines.append('class LightConeDef:')
    lines.append('    """光锥定义（官方 wiki 快照固化）。')
    lines.append('')
    lines.append('    Attributes:')
    lines.append('        id: 英文代号 = 官方英文名归一化；国际版 HoYoWiki 未同步时为空串，')
    lines.append('            补齐前勿以 id 寻址（规则见 sr-od-dev-cone-data skill 附录）.')
    lines.append('        name: 官方光锥全名（社区简称不入表；基准：「于夜色中」/「银河铁道之夜」）。')
    lines.append('        rarity: 星级 3/4/5。')
    lines.append('        path_id: 命途 id（对齐 ``character_const`` 九命途 id 风格：')
    lines.append('            destruction/preservation/hunt/abundance/nihility/erudition/')
    lines.append('            harmony/remembrance/elation）。')
    lines.append('        obtain: 获取途径（官方 wiki 原文透传，如卡池/商店渠道；纯展示）。')
    lines.append('        skill: 光锥特效文本（官方 wiki 原文透传，含五档叠影梯度的【】数值')
    lines.append('            标记不清洗——展示原样；S1-S5 数值即括号序列自左至右）。')
    lines.append('    """')
    lines.append('')
    lines.append('    id: str')
    lines.append('    name: str')
    lines.append('    rarity: int')
    lines.append('    path_id: str')
    lines.append("    obtain: str = ''")
    lines.append("    skill: str = ''")
    lines.append('')
    lines.append('')
    lines.append('LIGHT_CONES: tuple[LightConeDef, ...] = (')

    prev_segment = ''
    for e in entries:
        if e['segment'] != prev_segment:
            if prev_segment:
                lines.append('')
            lines.append(f"    # ---- {e['segment']} ----")
            prev_segment = e['segment']
        lines.append('    LightConeDef(')
        lines.append(f"        id={py_str(e['id'])},")
        lines.append(f"        name={py_str(e['cn'])},")
        lines.append(f"        rarity={e['rarity']},")
        lines.append(f"        path_id={py_str(e['path_id'])},")
        # obtain/skill 存转义原文(冻结值原样复用/新增值经 py_str 预转义),直接包裹引号
        lines.append(f"        obtain='{e['obtain']}',")
        lines.append(f"        skill='{e['skill']}',")
        lines.append('    ),')
    lines.append(')')
    lines.append('')
    lines.append(f'# 名称反查索引：模块加载时构建一次（进程内缓存）；{n} 名称唯一由单测锁定。')
    lines.append('LIGHT_CONE_BY_NAME: dict[str, LightConeDef] = {')
    lines.append('    cone.name: cone for cone in LIGHT_CONES')
    lines.append('}')
    lines.append('')
    lines.append('def resolve_light_cone(name: str) -> LightConeDef | None:')
    lines.append('    """光锥名 → 定义（miss 返回 None，不抛异常）。"""')
    lines.append('    return LIGHT_CONE_BY_NAME.get(name)')
    lines.append('')

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'已生成 {OUT}（{n} 把；新增 {len(fresh_names)}）')
    if fresh_names:
        print(f'新增词条（wiki 取文）: {fresh_names}')
    if drift:
        print(f'文本漂移 {len(drift)} 条（保持冻结值,请人工核对 wiki 是否误改）: {drift}')
    if skipped_manual:
        print(f'跳过 manual 行（等 wiki 词条）: {skipped_manual}')
    missing_icons = [e['cn'] for e in entries
                     if e['id'] and not (TEMPLATE_DIR / e['id'] / 'raw.webp').is_file()]
    if missing_icons:
        print(f'图标模板缺失 {len(missing_icons)}(图标工序补): {missing_icons}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
