"""账号档案扫描产物清洗:对 account_profile_scan.json 做名字归一/噪声剔除/变体合并。

独立进程运行(不依赖 MCP server 的模块缓存),作为扫描 app 收尾的固定兜底步骤——
server 进程对 Python 模块的缓存存在「改码+重启后仍偶发旧行为」的边界,
清洗逻辑放独立进程保证始终以最新规则执行。

用法(PYTHONPATH=src): uv run python tools/account/clean_account_profile.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / 'src'))

from sr_od.application.account_profile.account_profile_core import normalize_cn_name

OUTPUT_PATH: Path = Path('config') / 'idx' / 'account_profile_scan.json'


def main() -> None:
    if not OUTPUT_PATH.exists():
        print(f'no scan file: {OUTPUT_PATH}')
        return
    with open(OUTPUT_PATH, encoding='utf-8') as f:
        data = json.load(f)

    merged: dict[str, dict] = {}
    dropped: list[str] = []
    for c in data.get('characters', []):
        cn = normalize_cn_name(c.get('cn'))
        if cn is None:
            dropped.append(str(c.get('cn')))
            continue
        if cn not in merged:
            merged[cn] = {**c, 'cn': cn}
        else:
            dropped.append(str(c.get('cn')))

    data['characters'] = [merged[k] for k in sorted(merged)]
    data['count'] = len(merged)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'cleaned: {len(merged)} kept, {len(dropped)} dropped -> {dropped}')


if __name__ == '__main__':
    main()
