"""抓取国内官方 wiki 遗器频道(channel_id=30)套装列表。

产出(运行时缓存,消费方 = build_relic_authority_table.py 与 wiki 详情重抓):
  .debug/temp/relic_wiki/cnwiki_relic_list.json
    [ {content_id, name} ]  按列表序（= 频道展示序,非实装序）

接口:act-api-takumi-static.mihoyo.com content/list(官方自营 REST,
同 sr-od-dev-official-api 管道)。仅标准库 + requests,项目根目录运行:
    uv run python skills/sr-od-dev-relic-data/scripts/fetch_sr_wiki_relic_list.py
"""
import json
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # Windows 控制台默认 GBK,中文输出会乱码

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / '.debug' / 'temp' / 'relic_wiki'
LIST_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/'
            'content/list?app_sn=sr_wiki&channel_id=30&lang=zh-cn')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def fetch_list() -> list[dict]:
    resp = requests.get(LIST_URL, headers={'User-Agent': UA}, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get('retcode') != 0:
        raise RuntimeError(f'清单 retcode={body.get("retcode")} {body.get("message")}')
    entries: list[dict] = []
    for group in body.get('data', {}).get('list') or []:
        for item in group.get('list') or []:
            entries.append({'content_id': item.get('content_id'), 'name': item.get('title') or ''})
    return entries


def main() -> int:
    entries = fetch_list()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / 'cnwiki_relic_list.json'
    out.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'国内 wiki 遗器频道 {len(entries)} 条 -> {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
