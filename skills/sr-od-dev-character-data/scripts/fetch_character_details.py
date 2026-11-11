"""侦察:抓取官方 wiki 角色详情(channel 18)全部词条,解析行迹满级+星魂全6。

数据源:content/info 的 rpg_new_tmp_content(对象形态,14 模块)。
- 角色行迹:data.points[]——tag/name/tableData(等级表,末行=满级)/subList(分段描述 HTML)
- 角色星魂:data.richText——HTML 表格,剥标签提取【N】名称+效果描述

输入:随仓权威表 characters-full.json(wiki_content_id,98 数字 ID)
    + game-coach character_full_list.json(101 词条,含重复形态,交叉补齐)
输出:.debug/temp/char_wiki/char_details.json —— {content_id: {name, traces[], eidolons[]}}
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote

import requests

PROJECT_ROOT = Path(r'D:\code\workspace\StarRailOneDragon')
AUTH = Path(__file__).resolve().parent.parent / 'references' / 'characters-full.json'  # 相对脚本定位,换仓不失效
LIST_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/'
              'content/list?app_sn=sr_wiki&channel_id=18&lang=zh-cn')
OUT_FILE = PROJECT_ROOT / '.debug' / 'temp' / 'char_wiki' / 'char_details.json'
DETAIL_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/'
              'content/info?app_sn=sr_wiki&content_id={cid}&lang=zh-cn')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

_TAG_RE = re.compile(r'<[^>]+>')
_EIDOLON_NAME_RE = re.compile(r'【([1-6])】([^<]+)')


def strip_html(html: str) -> str:
    """HTML → 纯文本(剥标签+转行,去空行)。表格单元格/标题边界转换行——
    星魂 richText 的名称与效果分属相邻 td,不转行会粘连成一段无法分段。"""
    text = html.replace('</p>', '\n').replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    for boundary in ('</h3>', '</td>', '</tr>'):
        text = text.replace(boundary, '\n')
    text = _TAG_RE.sub('', text)
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line)


def parse_trace_points(data: dict) -> list[dict]:
    """行迹 points → [{tag, name, max_level, max_values, desc}](末行=满级)。"""
    traces = []
    for point in data.get('points') or []:
        if not (point.get('tag') or '').strip() and not (point.get('name') or '').strip():
            continue  # wiki 表格空行/装饰点,无语义
        table = point.get('tableData') or {}
        rows = table.get('rows') or []
        max_level = ''
        max_values: list[str] = []
        if isinstance(rows, list) and rows:
            last_row = rows[-1]  # 末行 = 满级（表按等级升序）
            if isinstance(last_row, list) and last_row:
                max_level = str(last_row[0]) if last_row[0] is not None else ''
                max_values = [str(v) for v in last_row[1:]]
        desc_parts = []
        for sub in point.get('subList') or []:
            if not isinstance(sub, dict):
                continue
            desc = strip_html(sub.get('subDesc') or '')
            if desc:
                desc_parts.append(desc)
        traces.append({
            'tag': point.get('tag') or '',
            'name': point.get('name') or '',
            'max_level': max_level,
            'max_values': max_values,
            'desc': '\n'.join(desc_parts),
        })
    return traces


def parse_eidolon_rich_text(rich_text: str) -> list[dict]:
    """星魂 richText HTML → [{pos, name, desc}](剥标签后按【N】分段)。"""
    text = strip_html(rich_text)
    # 纯文本里星魂名形如【1】高天寥落真言始,效果紧跟其后的行
    eidolons: list[dict] = []
    lines = text.splitlines()
    current: dict | None = None
    for line in lines:
        m = _EIDOLON_NAME_RE.search(line)
        if m:
            if current is not None:
                eidolons.append(current)
            current = {'pos': int(m.group(1)), 'name': m.group(2).strip(), 'desc': ''}
            rest = line[m.end():].strip()
            if rest:
                current['desc'] = rest
        elif current is not None:
            current['desc'] = (current['desc'] + '\n' + line).strip()
    if current is not None:
        eidolons.append(current)
    return eidolons


def fetch_list() -> list[dict]:
    """现拉 wiki 角色频道清单（channel 18），不依赖本地快照文件。

    返回条目 {content_id, title}。
    """
    resp = requests.get(LIST_URL, headers={'User-Agent': UA}, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get('retcode') != 0:
        raise RuntimeError(f'清单 retcode={body.get("retcode")} {body.get("message")}')
    entries: list[dict] = []
    for group in body.get('data', {}).get('list') or []:
        for item in group.get('list') or []:
            entries.append({'content_id': item.get('content_id'),
                            'title': item.get('title') or ''})
    return entries


def fetch_detail(content_id: int) -> dict:
    resp = requests.get(DETAIL_URL.format(cid=content_id), headers={'User-Agent': UA}, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get('retcode') != 0:
        return {'error': f'retcode={body.get("retcode")}'}
    content = body.get('data', {}).get('content') or {}
    rpg = content.get('rpg_new_tmp_content')
    if not rpg:
        return {'error': 'rpg empty'}
    record: dict = {'name': content.get('title') or ''}
    for module in rpg.get('modules') or []:
        name = module.get('name')
        comps = module.get('components') or []
        if not comps:
            continue
        data_text = comps[0].get('data')
        if not isinstance(data_text, str) or not data_text:
            continue
        try:
            data = json.loads(data_text)
        except json.JSONDecodeError:
            continue
        if name == '角色行迹':
            record['traces'] = parse_trace_points(data)
        elif name == '角色星魂':
            record['eidolons'] = parse_eidolon_rich_text(data.get('richText') or '')
    return record


def main() -> int:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    auth = json.loads(AUTH.read_text(encoding='utf-8'))
    entries = fetch_list()
    # 词条清单(content_id → 标题);权威表提供数字 avatarId 校验用
    results = []
    for entry in entries:
        cid = entry['content_id']
        record = fetch_detail(cid)
        record['content_id'] = cid
        record['title'] = entry.get('title') or ''
        results.append(record)
        t_n = len(record.get('traces') or [])
        e_n = len(record.get('eidolons') or [])
        flag = 'ERR ' if 'error' in record else ''
        print(f'[{cid}] {flag}{record["title"]} traces={t_n} eidolons={e_n}')
        time.sleep(0.5)
    OUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    ok = sum(1 for r in results if 'error' not in r)
    print(f'完成 {ok}/{len(entries)},产出 {OUT_FILE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
