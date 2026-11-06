"""国内米游社 wiki 角色频道拉取:列表 + 逐条详情,落成本地缓存。

产出(运行时缓存,消费方 = sr-od-dev-character-data/scripts/finalize_map.py):
  .debug/temp/animestudio/wiki_channel18.json        列表条目数组(content_id/title/ext/...)
  .debug/temp/animestudio/details/<content_id>.json  逐条详情原始响应

接口与字段依据:本 skill references/characters.md「国内米游社」。
已知坑(详见该文档):lang 参数恒中文;空壳词条(无 avatarId);avatarId=="0" 占位;
行迹模块名带「前瞻」= 未实装。仅标准库,项目根目录运行:
    uv run python skills/sr-od-dev-official-api/scripts/fetch_sr_wiki_characters.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # Windows 控制台默认 GBK,中文统计信息会乱码

LIST_URL = ('https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list'
            '?app_sn=sr_wiki&channel_id=18&lang=zh-cn')
DETAIL_URL = 'https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info?app_sn=sr_wiki&content_id={cid}'
OUT_DIR = Path(r'.debug/temp/animestudio')
RETRIES = 3


def fetch(url: str) -> dict:
    """GET 并解析 JSON;retcode 非 0 或网络异常按退避重试。"""
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            if payload.get('retcode') != 0:
                raise RuntimeError(f"retcode={payload.get('retcode')} message={payload.get('message')}")
            return payload
        except Exception as e:  # 网络抖动/限流都值得退避重试
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f'重试 {RETRIES} 次仍失败: {url} -> {last_err}')


def main() -> None:
    payload = fetch(LIST_URL)
    # 返回结构:data.list 是频道树节点数组,角色频道节点 id==18,条目在节点 list 里
    channels = payload['data']['list']
    channel = next(c for c in channels if c.get('id') == 18)
    entries = channel['list']

    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'wiki_channel18.json').write_text(
        json.dumps(entries, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'列表: {len(entries)} 条 -> {out_dir / "wiki_channel18.json"}')

    detail_dir = out_dir / 'details'
    detail_dir.mkdir(exist_ok=True)
    stats = {'ok': 0, 'avatar_id': 0, 'placeholder': 0, 'hollow': 0, 'qianzhan': 0}
    for i, entry in enumerate(entries):
        cid = entry['content_id']
        detail = fetch(DETAIL_URL.format(cid=cid))
        (detail_dir / f'{cid}.json').write_text(
            json.dumps(detail, ensure_ascii=False), encoding='utf-8')
        content = detail.get('data', {}).get('content', {}) or {}
        rpg = content.get('rpg_new_tmp_content') or {}  # 空壳词条此键可能为 null
        user_info = (rpg.get('base') or {}).get('userInfo') or {}
        modules = rpg.get('modules') or []
        stats['ok'] += 1
        if user_info.get('avatarId') == '0':
            stats['placeholder'] += 1
        elif not user_info.get('avatarId'):
            stats['hollow'] += 1
        else:
            stats['avatar_id'] += 1
        if any('前瞻' in (m.get('name') or '') for m in modules):
            stats['qianzhan'] += 1
        time.sleep(0.2)
        if (i + 1) % 20 == 0:
            print(f'  详情进度 {i + 1}/{len(entries)}')

    print(f"详情: {stats['ok']} 条 | 带 avatarId: {stats['avatar_id']} | "
          f"占位(avatarId=0): {stats['placeholder']} | 空壳: {stats['hollow']} | "
          f"前瞻未实装: {stats['qianzhan']}")
    if stats['ok'] != len(entries):
        print('警告:详情条数与列表不一致', file=sys.stderr)


if __name__ == '__main__':
    main()
