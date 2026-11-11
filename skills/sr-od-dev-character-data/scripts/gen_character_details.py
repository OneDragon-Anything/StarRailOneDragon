"""侦察:角色详情抓取结果 → sr_character_details.py 常量模块生成。

输入:.debug/temp/char_wiki/char_details.json(101 条 wiki 抓取)
    + 随仓权威表(wiki_content_id → 数字 avatarId)
过滤:error(rpg 空旧模板)/前瞻占位(traces<8)跳过并标注。
产出:src/sr_od/mys/sr_character_details.py(完整模块,数据段位置参数紧凑单行)。
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(r'D:\code\workspace\StarRailOneDragon')
DETAILS = PROJECT_ROOT / '.debug' / 'temp' / 'char_wiki' / 'char_details.json'
AUTH = Path(__file__).resolve().parent.parent / 'references' / 'characters-full.json'  # 相对脚本定位,换仓不失效
OUT = PROJECT_ROOT / 'src' / 'sr_od' / 'mys' / 'sr_character_details.py'


def py_str(text: str) -> str:
    """字符串字面量转义(单引号+真实换行转 \\n)。"""
    return "'" + text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def main() -> int:
    details = json.loads(DETAILS.read_text(encoding='utf-8'))
    auth = json.loads(AUTH.read_text(encoding='utf-8'))
    # wiki_content_id → (avatarId, cn)
    cid_to_aid: dict[int, tuple[int, str]] = {}
    for aid_str, info in auth.items():
        wcid = info.get('wiki_content_id')
        if wcid:
            cid_to_aid[int(wcid)] = (int(aid_str), info.get('cn') or '')

    skipped: list[str] = []
    traces_data: dict[int, list[dict]] = {}
    eidolons_data: dict[int, list[dict]] = {}
    names: dict[int, str] = {}
    for record in details:
        cid = record.get('content_id')
        if cid is None or 'error' in record:
            skipped.append(f"cid={cid} {record.get('title') or record.get('name')} error={record.get('error')}")
            continue
        traces = record.get('traces') or []
        eidolons = record.get('eidolons') or []
        if len(traces) < 8 or len(eidolons) != 6:
            skipped.append(f"cid={cid} {record.get('name')} traces={len(traces)} eido={len(eidolons)} 前瞻占位/模板异常")
            continue
        pair = cid_to_aid.get(cid)
        if pair is None:
            skipped.append(f'cid={cid} {record.get("name")} 权威表无此 wiki_content_id')
            continue
        avatar_id, cn = pair
        traces_data[avatar_id] = traces
        eidolons_data[avatar_id] = eidolons
        names[avatar_id] = record.get('name') or cn

    print(f'固化 {len(traces_data)} 角色(行迹 {sum(len(v) for v in traces_data.values())} 节,'
          f'星魂 {sum(len(v) for v in eidolons_data.values())} 魂);跳过 {len(skipped)}')
    for s in skipped:
        print(f'  跳过: {s}')

    lines: list[str] = []
    lines.append('"""角色静态基础信息快照常量：行迹（满级）与星魂（全 6 层）。')
    lines.append('')
    lines.append('数据源：官方 wiki 角色词条详情（channel 18，rpg 模块的行迹/星魂模块），')
    lines.append('解析后固化为常量；行迹仅存满级行数值（tableData 末行），效果描述为官方')
    lines.append('原文剥标签透传（含【】梯度标记不清洗——展示原样）。')
    lines.append('')
    lines.append('索引键 = 游戏内部角色数字 id（avatarId，与 character_const.Character.avatar_id')
    lines.append('同源；权威表双源锚定）。账号运行时的星魂/行迹（含解锁与练度状态）走')
    lines.append('mys_get_roster_detail（SrRank/SrSkill），本模块是**全量静态定义**（不随账号变）。')
    lines.append('')
    lines.append('版本刷新：游戏新版本后重跑官方 wiki 角色详情抓取并重新生成本模块')
    lines.append('（生成器随角色数据维护 skill 维护，不入本仓），生成后人工审阅 diff。')
    lines.append('')
    lines.append('模块纪律：零外部 IO、零状态——纯常量（同 sr_relic_sets 模块纪律）。')
    lines.append('"""')
    lines.append('')
    lines.append('from dataclasses import dataclass')
    lines.append('')
    lines.append('')
    lines.append('@dataclass(frozen=True)')
    lines.append('class CharacterTraceDef:')
    lines.append('    """行迹节点（满级口径）。')
    lines.append('')
    lines.append('    Attributes:')
    lines.append('        tag: 行迹类型官方中文（普攻/战技/终结技/天赋/秘技/属性加成/额外能力/欢愉技）.')
    lines.append('        name: 行迹名。')
    lines.append('        max_level: 满级等级文本（如「等级12」）。')
    lines.append('        max_values: 满级行数值（tableData 末行，顺序对齐 headers 数值列）。')
    lines.append('        desc: 效果描述（官方原文剥 HTML 透传，含【】梯度标记）。')
    lines.append('    """')
    lines.append('')
    lines.append('    tag: str')
    lines.append('    name: str')
    lines.append('    max_level: str')
    lines.append('    max_values: tuple[str, ...]')
    lines.append('    desc: str')
    lines.append('')
    lines.append('')
    lines.append('@dataclass(frozen=True)')
    lines.append('class CharacterEidolonDef:')
    lines.append('    """星魂层（官方原文透传）。')
    lines.append('')
    lines.append('    Attributes:')
    lines.append('        pos: 星魂序号 1-6（坐标系：星魂第 N 层，恒稳）。')
    lines.append('        name: 星魂名。')
    lines.append('        desc: 效果描述（官方原文剥 HTML 透传）。')
    lines.append('    """')
    lines.append('')
    lines.append('    pos: int')
    lines.append('    name: str')
    lines.append('    desc: str')
    lines.append('')
    lines.append('')
    lines.append('CHARACTER_TRACES: dict[int, tuple[CharacterTraceDef, ...]] = {')
    for aid in sorted(traces_data):
        lines.append(f'    {aid}: (  # {names[aid]}')
        for t in traces_data[aid]:
            items = [py_str(v) for v in t['max_values']]
            # 单元素 tuple 必须带尾逗号，否则 ('110%') 是带括号的字符串
            tuple_expr = '(' + ', '.join(items) + (',' if len(items) == 1 else '') + ')'
            lines.append(f"        CharacterTraceDef({py_str(t['tag'])}, {py_str(t['name'])}, "
                         f"{py_str(t['max_level'])}, {tuple_expr}, {py_str(t['desc'])}),")
        lines.append('    ),')
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('CHARACTER_EIDOLONS: dict[int, tuple[CharacterEidolonDef, ...]] = {')
    for aid in sorted(eidolons_data):
        lines.append(f'    {aid}: (  # {names[aid]}')
        for e in eidolons_data[aid]:
            lines.append(f"        CharacterEidolonDef({e['pos']}, {py_str(e['name'])}, {py_str(e['desc'])}),")
        lines.append('    ),')
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def resolve_traces(avatar_id: int) -> tuple[CharacterTraceDef, ...]:')
    lines.append('    """角色数字 id → 行迹定义（miss 返回空元组，不抛异常）。"""')
    lines.append('    return CHARACTER_TRACES.get(avatar_id, ())')
    lines.append('')
    lines.append('')
    lines.append('def resolve_eidolons(avatar_id: int) -> tuple[CharacterEidolonDef, ...]:')
    lines.append('    """角色数字 id → 星魂定义（miss 返回空元组，不抛异常）。"""')
    lines.append('    return CHARACTER_EIDOLONS.get(avatar_id, ())')
    lines.append('')

    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'产出 {OUT} ({len(lines)} 行)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
