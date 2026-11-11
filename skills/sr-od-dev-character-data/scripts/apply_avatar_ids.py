"""一次性:character_const.py 的 98 条 Character 定义批量补 avatar_id 字段。

依据:.debug/temp/char_avatar_id_map.json(character_id → avatarId,双源对账 98/98)
改动:①Character.__init__ 尾部加 avatar_id 参数(默认 0);②每条定义行尾插 avatar_id=N。
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
CONST_FILE = PROJECT_ROOT / 'src' / 'sr_od' / 'config' / 'character_const.py'
MAP_FILE = PROJECT_ROOT / '.debug' / 'temp' / 'char_avatar_id_map.json'


def main() -> int:
    mapping = json.loads(MAP_FILE.read_text(encoding='utf-8'))['map']
    # 反向:character_id → avatarId
    id_by_char: dict[str, str] = {cid: aid for aid, cid in mapping.items()}

    text = CONST_FILE.read_text(encoding='utf-8')

    # ① __init__ 签名加 avatar_id(默认 0,保持既有位置参数兼容)
    sig_old = ("def __init__(self, id: str, cn: str, path: CharacterPath, combat_type: CharacterCombatType, "
               "level: int, technique_type: CharacterTechniqueType,\n                 buff_lasting_seconds: float = 20):")
    sig_new = ("def __init__(self, id: str, cn: str, path: CharacterPath, combat_type: CharacterCombatType, "
               "level: int, technique_type: CharacterTechniqueType,\n                 buff_lasting_seconds: float = 20, avatar_id: int = 0):")
    if sig_old not in text:
        print('❌ __init__ 签名未匹配(可能已被改过)')
        return 1
    text = text.replace(sig_old, sig_new)
    # 成员注释加在 buff_lasting_seconds 之后
    attr_old = "        self.buff_lasting_seconds: float = buff_lasting_seconds  # BUFF持续时间"
    attr_new = (attr_old + "\n        self.avatar_id: int = avatar_id\n"
                "        \"\"\"游戏内部角色数字 id(米游社 avatar/info 的 id 字段;权威表双源锚定;\"\"\"")
    text = text.replace(attr_old, attr_new)

    # ② 每条定义行尾插 avatar_id=N(行内同时抽 id 校验映射完备)
    lines = text.splitlines(keepends=True)
    patched = 0
    for i, line in enumerate(lines):
        m = re.search(r"= Character\(id='([a-z0-9_]+)',", line)
        if not m or line.rstrip().endswith(')') is False:
            continue
        cid = m.group(1)
        aid = id_by_char.get(cid)
        if aid is None:
            print(f'  ⚠️ {cid} 无映射,跳过(保持无 avatar_id)')
            continue
        lines[i] = line.rstrip('\n').rstrip(')') + f', avatar_id={aid})\n'
        patched += 1
    print(f'定义行补 avatar_id {patched} 条')
    CONST_FILE.write_text(''.join(lines), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
