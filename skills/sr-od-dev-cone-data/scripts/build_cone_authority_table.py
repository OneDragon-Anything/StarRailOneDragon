"""组装光锥权威表:国内 wiki 详情 × 国际服英文名 × 现有模块排序 → references/cones-full.json。

输入:
  .debug/temp/cone_wiki/cone_details_cn.json      (fetch_sr_wiki_cone_list.py 产物)
  .debug/temp/wiki_cache/hoyowiki_cone_en_names.json (fetch_hoyowiki_cone_en_names.py 产物)
  src/sr_od/mys/sr_light_cones.py                  (文本解析,取条目顺序与分段)

产出 references/cones-full.json,键 = 归一化中文名,值字段:
  cn / en(国际服官方英文名,未同步为空串) / id(=en 归一化,同上) /
  rarity / path_id / wiki_content_id / hoyowiki_page_id / order(全局顺序,manual 行可为小数) /
  segment(模块分段标签) / source('wiki'|'manual')

wiki 是权威源:同键冲突以 wiki 覆盖 manual;MANUAL_ENTRIES 仅登记 wiki 尚未收录
但已有官方公告名的词条(id 待国际服同步后回填),gen 生成器跳过无 wiki 数据的行。
项目根目录运行:uv run python skills/sr-od-dev-cone-data/scripts/build_cone_authority_table.py
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
DETAILS = PROJECT_ROOT / '.debug' / 'temp' / 'cone_wiki' / 'cone_details_cn.json'
EN_NAMES = PROJECT_ROOT / '.debug' / 'temp' / 'wiki_cache' / 'hoyowiki_cone_en_names.json'
MODULE = PROJECT_ROOT / 'src' / 'sr_od' / 'mys' / 'sr_light_cones.py'
OUT = Path(__file__).resolve().parent.parent / 'references' / 'cones-full.json'

CN_NORM = str.maketrans({'•': '·', '・': '·', '．': '.', ' ': '', '\u3000': ''})

CAREER_TO_PATH = {
    '存护': 'preservation', '智识': 'erudition', '巡猎': 'hunt', '同谐': 'harmony',
    '毁灭': 'destruction', '丰饶': 'abundance', '虚无': 'nihility',
    '记忆': 'remembrance', '欢愉': 'elation',
}

# wiki 尚未收录、但已有官方公告名的新词条(id/rarity/path 以公告为准;wiki 同步后自动转正)。
# 2300x 段续排 tid 由客户端资产侧证实存在,skill/obtain 等词条数据以 wiki 上线为准。
MANUAL_ENTRIES: list[dict] = [
    {'cn': '当第一声「阿哈」响起', 'rarity': 5, 'path_id': 'elation',
     'segment': '5 星·池内（2300x 段）', 'note': '4.7 阿哈专属光锥,官方公告名'},
]

_SEGMENT_RE = re.compile(r'# ---- (.+?) ----')
_NAME_RE = re.compile(r"name='(.+?)',")


def parse_module_order() -> list[dict]:
    """模块文本 → [{name, segment, order}](按出现序)。"""
    rows: list[dict] = []
    segment = ''
    for line in MODULE.read_text(encoding='utf-8').splitlines():
        mc = _SEGMENT_RE.search(line)
        if mc:
            segment = mc.group(1).strip()
            continue
        mc = _NAME_RE.search(line)
        if mc:
            rows.append({'name': mc.group(1), 'segment': segment, 'order': len(rows)})
    return rows


def norm_cn(name: str) -> str:
    return name.translate(CN_NORM).lower()


def main() -> int:
    details: dict[str, dict] = json.loads(DETAILS.read_text(encoding='utf-8'))
    en_map: dict[str, dict] = json.loads(EN_NAMES.read_text(encoding='utf-8'))
    module_rows = parse_module_order()
    print(f'wiki 详情 {len(details)} 条 / intl 互连 {len(en_map)} 条 / 模块条目 {len(module_rows)} 条')

    table: dict[str, dict] = {}
    problems: list[str] = []
    used_cids: set[str] = set()
    for row in module_rows:
        key = norm_cn(row['name'])
        record = next((r for r in details.values() if r.get('title') == row['name']), None)
        if record is None:
            problems.append(f'{row["name"]}: wiki 详情缺失')
            continue
        cid = next(cid for cid, r in details.items() if r.get('title') == row['name'])
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
    for i, manual in enumerate(MANUAL_ENTRIES):
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
        _ = i  # 枚举仅报错定位用

    unused = sorted(set(details) - used_cids)
    if unused:
        problems.append(f'wiki 详情未被模块引用: {[details[c]["title"] for c in unused]}')

    id_vals = [r['id'] for r in table.values() if r['id']]
    dup = {v for v in id_vals if id_vals.count(v) > 1}
    if dup:
        problems.append(f'id 重复: {sorted(dup)}')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding='utf-8')
    n_en = sum(1 for r in table.values() if r['en'])
    n_manual = sum(1 for r in table.values() if r['source'] == 'manual')
    print(f'权威表 {len(table)} 条(en 已回填 {n_en},manual {n_manual}) -> {OUT}')
    if problems:
        print('问题清单:')
        for p in problems:
            print(f'  {p}')
        return 1
    print('校验全过')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
