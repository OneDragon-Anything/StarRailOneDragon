"""账号档案数据管线：把角色判读 JSON 校验合并进账号档案 YML。

用法（项目根目录）：
    uv run python tools/account/merge_profile.py

输入：.debug/account/roster/roster_raw.json（agent 视觉判读产出，格式见 sr-od-account-inspection skill）
输出：更新 config/idx/account_profile.yml 的 roster.characters 节（保留档案其余字段）

为什么存在：游戏内画面扫描必须由 agent 经 MCP 逐步执行（skill 剧本），但判读结果的
落档是纯数据管线，固化成脚本后任何 agent/人都能一条命令合并，避免手抄出错。
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW_JSON = ROOT / '.debug/account/roster/roster_raw.json'
PROFILE_YML = ROOT / 'config/idx/account_profile.yml'

REQUIRED_FIELDS = {'name', 'level', 'rarity', 'confidence'}
VALID_CONFIDENCE = {'high', 'medium', 'low'}


def load_raw(path: Path) -> dict:
    """读判读 JSON 并做结构校验；失败给出可操作的错误信息。"""
    if not path.exists():
        print(f'[ERROR] 判读文件不存在: {path}')
        print('先按 sr-od-account-inspection skill 完成游戏内扫描与判读，再跑本脚本。')
        sys.exit(1)
    data = json.loads(path.read_text(encoding='utf-8'))
    characters = data.get('characters')
    if not isinstance(characters, list) or not characters:
        print('[ERROR] characters 为空或缺失，判读产出不完整。')
        sys.exit(1)
    problems: list[str] = []
    for i, ch in enumerate(characters):
        missing = REQUIRED_FIELDS - set(ch)
        if missing:
            problems.append(f'characters[{i}] 缺字段 {sorted(missing)}: {ch}')
        if ch.get('confidence') not in VALID_CONFIDENCE:
            problems.append(f"characters[{i}] confidence 非法: {ch.get('confidence')!r}（应为 {sorted(VALID_CONFIDENCE)}）")
    if problems:
        print('[ERROR] 判读数据校验失败：')
        for p in problems:
            print(f'  - {p}')
        sys.exit(1)
    return data


def merge_into_profile(raw: dict, profile_path: Path) -> None:
    """把 characters 合并进档案 roster 节；档案不存在时从骨架创建。"""
    profile = {}
    if profile_path.exists():
        profile = yaml.safe_load(profile_path.read_text(encoding='utf-8')) or {}
    roster = profile.setdefault('roster', {})
    roster['source'] = str(RAW_JSON.relative_to(ROOT)).replace('\\', '/')
    roster['method'] = 'screenshot_vlm'
    roster['total'] = raw.get('total_count', len(raw['characters']))
    roster['characters'] = raw['characters']
    if raw.get('notes'):
        roster['judge_notes'] = raw['notes']
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(profile, allow_unicode=True, sort_keys=False, width=120)
    profile_path.write_text(text, encoding='utf-8')
    print(f'[OK] 已合并 {roster["total"]} 个角色 -> {profile_path}')


def main() -> None:
    raw = load_raw(RAW_JSON)
    merge_into_profile(raw, PROFILE_YML)
    low = [c['name'] for c in raw['characters'] if c.get('confidence') == 'low']
    if low:
        print(f'[NOTE] 低置信角色 {len(low)} 个，建议游戏内逐个点开详情复核: {low}')


if __name__ == '__main__':
    main()
