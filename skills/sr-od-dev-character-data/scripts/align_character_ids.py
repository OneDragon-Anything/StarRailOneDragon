"""侦察:权威表(数字 avatarId) ↔ character_const.py(英文代号) 映射对照。

主键:en_normalized == Character.id(90 条);例外手工规则:
- 开拓者 8001-8010:奇数=男(caelum_*)偶数=女(stelle_*),按命途配对
- 三月七 1224(无 en_normalized) → march7th_hunt
输出:.debug/temp/char_avatar_id_map.json —— {avatarId: character_id} + 未对账清单
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
AUTH = Path(__file__).resolve().parent.parent / 'references' / 'characters-full.json'  # 相对脚本定位,换仓不失效
CONST_FILE = PROJECT_ROOT / 'src' / 'sr_od' / 'config' / 'character_const.py'
OUT = PROJECT_ROOT / '.debug' / 'temp' / 'char_avatar_id_map.json'

# 开拓者数字 ID → 常量英文代号(奇男偶女 × 五命途;三月七双形态)
MANUAL: dict[str, str] = {
    '8001': 'caelum_destruction', '8002': 'stelle_destruction',
    '8003': 'caelum_preservation', '8004': 'stelle_preservation',
    '8005': 'caelum_harmony', '8006': 'stelle_harmony',
    '8007': 'caelum_remembrance', '8008': 'stelle_remembrance',
    '8009': 'caelum_elation', '8010': 'stelle_elation',
    '1001': 'march7th_preservation', '1224': 'march7th_hunt',
    # 命名风格差异:en_normalized 无下划线/缩写 vs 常量 id(以常量既成事实为准)
    '1321': 'the_dahlia', '1401': 'the_herta', '1407': 'casorice',
    '1502': 'yao_guang', '1506': 'silverwolf_999', '1508': 'rin_tohsaka',
    '1513': 'aventurine_waveflair',
}


def main() -> int:
    auth = json.loads(AUTH.read_text(encoding='utf-8'))
    const_text = CONST_FILE.read_text(encoding='utf-8')
    const_ids = set(re.findall(r"= Character\(id='([a-z0-9_]+)'", const_text))
    cn_by_id = dict(re.findall(r"= Character\(id='([a-z0-9_]+)',\s*cn='([^']+)'", const_text))

    mapping: dict[str, str] = {}
    unmatched: list[str] = []
    for avatar_id, info in auth.items():
        en = info.get('en_normalized')
        if avatar_id == '999':
            continue  # unmapped 占位(实装待定)
        if avatar_id in MANUAL:
            cid = MANUAL[avatar_id]
            if cid not in const_ids:
                unmatched.append(f'{avatar_id}: 手工映射 {cid} 不在常量')
            else:
                mapping[avatar_id] = cid
            continue
        if en and en in const_ids:
            const_cn = cn_by_id.get(en, '')
            auth_cn = info.get('cn') or ''
            if const_cn.replace('•', '·') != auth_cn.replace('•', '·'):
                print(f'  ⚠️ cn 不一致: {avatar_id} {en} 常量={const_cn} 权威={auth_cn}')
            mapping[avatar_id] = en
            continue
        unmatched.append(f'{avatar_id}: cn={info.get("cn")} en={en}')

    print(f'映射 {len(mapping)} 条, 未对账 {len(unmatched)} 条')
    for u in unmatched:
        print(f'  {u}')
    # 反向校验:常量 98 条是否全被映射
    reverse_missing = const_ids - set(mapping.values())
    print(f'常量侧未覆盖 {len(reverse_missing)} 条: {sorted(reverse_missing)}')
    OUT.write_text(json.dumps({'map': mapping, 'unmatched': unmatched}, ensure_ascii=False, indent=2),
                   encoding='utf-8')
    print(f'产出 {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
