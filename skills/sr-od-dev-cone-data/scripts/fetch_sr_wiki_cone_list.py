"""抓取米游社官方 wiki 光锥频道(channel 19)全部词条清单+详情,产权威表与生成器的输入。

解析:详情 contents[0].text 的 data-data(light 模块:career 命途/rate 星级/skill 特效
+ general/desc 模块 HTML 键值表:「实装版本」相邻单元格 = 获取途径)。
产出:.debug/temp/cone_wiki/cone_details_cn.json
    { "<content_id>": {title, career, rate, skill, obtain} }(desc 故事不落盘,不固化)

限流防护:API 高频后返回 retcode=0 空模板(career 解析不中),命中校验+间隔递增重试。
仅标准库+requests,项目根目录运行(约 170 次 × 1.5s,数分钟):
    uv run python skills/sr-od-dev-cone-data/scripts/fetch_sr_wiki_cone_list.py
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
OUT_FILE = PROJECT_ROOT / '.debug' / 'temp' / 'cone_wiki' / 'cone_details_cn.json'
LIST_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/'
            'content/list?app_sn=sr_wiki&channel_id=19&lang=zh-cn')
DETAIL_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/'
              'content/info?app_sn=sr_wiki&content_id={cid}&lang=zh-cn')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

_TAG_RE = re.compile(r'<[^>]+>')
_DATA_DATA_RE = re.compile(r'data-data="([^"]+)"')


def strip_html(html: str) -> str:
    """HTML → 纯文本(表格边界转换行)。"""
    text = html.replace('</p>', '\n').replace('<br>', '\n').replace('<br/>', '\n')
    for boundary in ('</td>', '</tr>', '</h3>'):
        text = text.replace(boundary, '\n')
    text = _TAG_RE.sub('', text)
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)


def parse_heritage(text: str) -> list[dict]:
    """详情页 → data-data 块数组。"""
    raw = _DATA_DATA_RE.search(text).group(1)
    decoded = json.loads(unquote(unquote(raw)) if '%25' in raw else unquote(raw))
    if isinstance(decoded, str):
        decoded = json.loads(unquote(decoded))
    return decoded


def parse_obtain(blocks: list[dict]) -> str:
    """general/desc 块的 HTML 键值表:剥标签后「实装版本」的下一行 = 获取途径。"""
    for block in blocks:
        if not isinstance(block, dict):
            continue
        data = block.get('data')
        if not isinstance(data, dict):
            continue
        if block.get('tmplKey') == 'general' and block.get('partKey') == 'desc':
            plain = strip_html(data.get('text') or '')
            lines = [line for line in plain.splitlines() if line]
            for i, line in enumerate(lines):
                if line == '实装版本' and i + 1 < len(lines):
                    return lines[i + 1]
    return ''


def fetch_detail(content_id: int) -> dict:
    resp = requests.get(DETAIL_URL.format(cid=content_id), headers={'User-Agent': UA}, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get('retcode') != 0:
        return {'error': f'retcode={body.get("retcode")}'}
    text = ((body.get('data', {}).get('content') or {}).get('contents') or [{}])[0].get('text') or ''
    if 'data-data="' not in text:
        return {'error': 'no data-data'}
    blocks = parse_heritage(text)
    record: dict = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue  # data-data 顶层混有 list 元素(模板变体)
        data = block.get('data')
        if not isinstance(data, dict):
            continue  # 部分 block 的 data 是 list(键值表变体),非本解析目标
        if data.get('career') and data.get('rate'):
            record['career'] = data.get('career') or ''
            record['rate'] = data.get('rate') or ''
            record['skill'] = data.get('skill') or ''
    record['obtain'] = parse_obtain(blocks)
    return record


def main() -> int:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(LIST_URL, headers={'User-Agent': UA}, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    entries = []
    for group in body.get('data', {}).get('list') or []:
        for item in group.get('list') or []:
            entries.append({'content_id': item.get('content_id'), 'title': item.get('title') or ''})
    print(f'清单 {len(entries)} 把')

    results: dict[str, dict] = {}
    failed: list[str] = []
    for idx, entry in enumerate(entries):
        cid = entry['content_id']
        record = None
        for attempt in range(3):
            record = fetch_detail(cid)
            if 'error' not in record and record.get('career'):
                break
            time.sleep(2 * (attempt + 1))
        if 'error' in record or not record.get('career'):
            failed.append(entry['title'])
            print(f'[{idx + 1}/{len(entries)}] {entry["title"]} FAIL(重试后仍无效)')
            continue
        record['title'] = entry['title']
        results[str(cid)] = record
        if (idx + 1) % 20 == 0 or idx + 1 == len(entries):
            print(f'[{idx + 1}/{len(entries)}] {entry["title"]} career={record.get("career")} obtain={record.get("obtain")[:30]!r}')
        time.sleep(1.5)

    OUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'完成 {len(results)}/{len(entries)},失败 {len(failed)} {failed[:5]},产出 {OUT_FILE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
