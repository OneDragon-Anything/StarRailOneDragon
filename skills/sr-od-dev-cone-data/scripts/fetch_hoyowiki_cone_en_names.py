"""国际版 HoYoWiki 光锥菜单双语拉取:zh-cn + en-us 列表按 entry_page_id 互连,产中文名→英文名映射。

产出(运行时缓存,消费方 = build_cone_authority_table.py):
  .debug/temp/wiki_cache/hoyowiki_cone_en_names.json
    { "归一化中文名": {"en": 官方英文名, "en_normalized": 小写去符号, "hoyowiki_page_id": "<entry_page_id>"} }

归一化口径:•/·/・统一为 ·、去全部空白、lower——与 build_cone_authority_table.py 连表键一致。
接口依据:sr-od-dev-official-api references/characters.md「国际版 HoYoWiki」同款打式,
光锥菜单 menu_id=107(2026-11-11 探测:total=168)。国际版域名可能需代理:urllib 自动读
HTTP_PROXY/HTTPS_PROXY 环境变量(不通就直连)。仅标准库,项目根目录运行:
    uv run python skills/sr-od-dev-cone-data/scripts/fetch_hoyowiki_cone_en_names.py
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # Windows 控制台默认 GBK,中文输出会乱码

LIST_URL = 'https://sg-act-public-api.hoyolab.com/hoyowiki/hsr/wapi/get_entry_page_list'
MENU_ID = '107'  # 光锥菜单
PAGE_SIZE = 30
OUT_DIR = Path(r'.debug/temp/wiki_cache')
RETRIES = 3
CN_NORM = str.maketrans({'•': '·', '・': '·', '．': '.', ',': '，', ' ': '', '\u3000': ''})

HEADERS = {
    'Content-Type': 'application/json;charset=UTF-8',
    'x-rpc-wiki_app': 'hsr',
    # 缺浏览器级头会被 WAF 403(Origin/Referer/真实 UA 缺一不可)
    'Origin': 'https://wiki.hoyolab.com',
    'Referer': 'https://wiki.hoyolab.com/',
    'Accept': 'application/json,text/plain,*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}


def normalize_cn(title: str) -> str:
    """连表键归一化:intl 词条名含脏字符(前导空格/尾换行/BOM/半角逗号实测),全清。"""
    cleaned = title.lstrip('\ufeff').translate(CN_NORM)
    return re.sub(r'\s+', '', cleaned).lower()


def normalize_en(name: str) -> str:
    """官方英文名 → 项目 id 风格建议值:仅保留字母数字(小写),符号一律剥离不枚举符号集。"""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def fetch_list(lang: str) -> list[dict]:
    """按语言翻页拉全光锥菜单条目。"""
    entries: list[dict] = []
    page = 1
    while True:
        body = json.dumps({'filters': [], 'menu_id': MENU_ID,
                           'page_num': page, 'page_size': PAGE_SIZE, 'use_es': True}).encode('utf-8')
        payload = None
        for attempt in range(RETRIES):
            try:
                req = urllib.request.Request(
                    LIST_URL, data=body, method='POST',
                    headers={**HEADERS, 'x-rpc-language': lang, 'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    payload = json.loads(resp.read().decode('utf-8'))
                break
            except Exception:
                if attempt == RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)
        if payload.get('retcode') != 0:
            raise RuntimeError(f"retcode={payload.get('retcode')} message={payload.get('message')}")
        items = payload.get('data', {}).get('list') or []
        entries.extend(items)
        if len(items) < PAGE_SIZE:
            return entries
        page += 1


def main() -> None:
    zh_entries = fetch_list('zh-cn')
    en_entries = fetch_list('en-us')
    print(f'列表: zh-cn {len(zh_entries)} 条 / en-us {len(en_entries)} 条')

    en_by_page_id = {str(e['entry_page_id']): e for e in en_entries}
    mapping: dict[str, dict] = {}
    conflicts: list[str] = []
    zh_only: list[str] = []
    for e in zh_entries:
        page_id = str(e['entry_page_id'])
        en_entry = en_by_page_id.get(page_id)
        if en_entry is None:
            zh_only.append(e['name'])
            continue  # zh 有 en 无:无法出英文名,留消费方按缺省处理
        key = normalize_cn(e['name'])
        row = {'en': en_entry['name'],
               'en_normalized': normalize_en(en_entry['name']),
               'hoyowiki_page_id': page_id}
        if key in mapping and mapping[key] != row:
            conflicts.append(key)  # 同名撞键:人工裁决,勿静默覆盖
            continue
        mapping[key] = row

    en_only = sorted(normalize_en(e['name']) for pid, e in
                     ((str(x['entry_page_id']), x) for x in en_entries)
                     if pid not in {r['hoyowiki_page_id'] for r in mapping.values()})

    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'hoyowiki_cone_en_names.json').write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'互连成功 {len(mapping)} 条 -> {out_dir / "hoyowiki_cone_en_names.json"}')
    if conflicts:
        print(f'同名撞键(需人工裁决,未写入): {sorted(set(conflicts))}')
    if zh_only:
        print(f'zh 有 en 无({len(zh_only)}): {zh_only}')
    if en_only:
        print(f'en 有 zh 无({len(en_only)}): {en_only}')


if __name__ == '__main__':
    main()
