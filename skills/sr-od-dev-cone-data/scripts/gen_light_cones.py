"""权威表 + wiki 详情 → src/sr_od/mys/sr_light_cones.py 常量模块生成。

输入:
  references/cones-full.json                    (build_cone_authority_table.py 产物)
  .debug/temp/cone_wiki/cone_details_cn.json    (fetch_sr_wiki_cone_list.py 产物)
产出:src/sr_od/mys/sr_light_cones.py(完整模块,含 id 字段)。

纪律:
- 数据块禁手改(单一源 = 官方 wiki,修正走重新生成);
- manual 行(source=manual,无 wiki 词条)跳过不生成,等 wiki 上线后随 diff 进模块;
- 生成后人工审阅 diff:skill/obtain 文本与旧模块的漂移要逐条过目(wiki 侧回改)。

校验:名称唯一 / id 唯一且仅小写字母数字(允许空串=国际服未同步) / 星级与命途枚举 /
图标归档缺失仅警告(归档走图标工序,不阻塞生成)。
项目根目录运行:uv run python skills/sr-od-dev-cone-data/scripts/gen_light_cones.py
"""
import json
import re
import sys
from html import unescape
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # 仓库根（scripts 上三级）
TABLE = Path(__file__).resolve().parent.parent / 'references' / 'cones-full.json'
DETAILS = PROJECT_ROOT / '.debug' / 'temp' / 'cone_wiki' / 'cone_details_cn.json'
OUT = PROJECT_ROOT / 'src' / 'sr_od' / 'mys' / 'sr_light_cones.py'
TEMPLATE_DIR = PROJECT_ROOT / 'assets' / 'template' / 'light_cone_icon'

VALID_PATHS = {'destruction', 'preservation', 'hunt', 'abundance', 'nihility',
               'erudition', 'harmony', 'remembrance', 'elation'}


def py_str(text: str) -> str:
    """字符串字面量转义(单引号+反斜杠+真实换行转 \\n)。"""
    return "'" + text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def plain_text(raw: str) -> str:
    """wiki skill/obtain 文本归一化:逐标签转空格(【】梯度两侧空格即由此而来)+
    HTML 实体解码+空白折叠。结构化词条(纯文本)经此为恒等变换,旧模板 HTML 词条
    剥后与结构化词条同构。"""
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


_FROZEN_RE = re.compile(
    r"name='(?P<name>[^']*)',\n"
    r"        rarity=\d+,\n"
    r"        path_id='[a-z]+',\n"
    r"        obtain='(?P<obtain>[^']*)',\n"
    r"        skill='(?P<skill>[^']*)',")


def parse_frozen_texts() -> dict[str, dict[str, str]]:
    """现模块 → {名称: {obtain, skill}}(转义原文,回写时原样复用不做二次转义)。"""
    frozen: dict[str, dict[str, str]] = {}
    for m in _FROZEN_RE.finditer(OUT.read_text(encoding='utf-8')):
        frozen[m['name']] = {'obtain': m['obtain'], 'skill': m['skill']}
    return frozen


def main() -> int:
    table: dict[str, dict] = json.loads(TABLE.read_text(encoding='utf-8'))
    details: dict[str, dict] = json.loads(DETAILS.read_text(encoding='utf-8'))
    frozen = parse_frozen_texts()

    rows = sorted(table.values(), key=lambda r: r['order'])
    problems: list[str] = []
    skipped_manual: list[str] = []
    drift: list[str] = []
    fresh_names: list[str] = []
    entries: list[dict] = []
    for row in rows:
        if row['source'] != 'wiki' or row.get('wiki_content_id') is None:
            skipped_manual.append(row['cn'])
            continue
        record = details.get(str(row['wiki_content_id']))
        if record is None:
            problems.append(f"{row['cn']}: wiki 详情缺失(cid={row['wiki_content_id']})")
            continue
        name = row['cn']
        fresh_obtain = py_str(plain_text(record.get('obtain') or ''))[1:-1]
        fresh_skill = py_str(plain_text(record.get('skill') or ''))[1:-1]
        old = frozen.get(name)
        if old is not None:
            # 固化纪律:已有词条 obtain/skill 以现模块为准(wiki 侧存在编辑损坏,
            # 如梯度列表粘连),wiki 只喂新增词条;文本漂移仅报告供人工核对 wiki。
            if old['obtain'] != fresh_obtain or old['skill'] != fresh_skill:
                drift.append(name)
            entries.append({**row, 'obtain': old['obtain'], 'skill': old['skill']})
        else:
            fresh_names.append(name)
            entries.append({**row, 'obtain': fresh_obtain, 'skill': fresh_skill})

    names = [e['cn'] for e in entries]
    if len(names) != len(set(names)):
        problems.append('名称重复')
    ids = [e['id'] for e in entries if e['id']]
    if len(ids) != len(set(ids)):
        problems.append('id 重复')
    bad_id = [e['id'] for e in entries if e['id'] and not re.fullmatch(r'[a-z0-9]+', e['id'])]
    if bad_id:
        problems.append(f'id 含非法字符: {bad_id}')
    for e in entries:
        if e['rarity'] not in (3, 4, 5):
            problems.append(f"{e['cn']}: 星级 {e['rarity']}")
        if e['path_id'] not in VALID_PATHS:
            problems.append(f"{e['cn']}: 命途 {e['path_id']}")
        if not e['skill']:
            problems.append(f"{e['cn']}: skill 为空")
        # obtain 允许为空:旧模板词条无「实装版本」键值行(先例 暖夜不会漫长)

    n = len(entries)
    if problems:
        print('校验失败,未写盘:')
        for p in problems:
            print(f'  {p}')
        return 1

    lines: list[str] = []
    lines.append('"""米游社光锥快照常量与查询助手。')
    lines.append('')
    lines.append('数据分层：定义层+skill 特效文本固化——id/名称/星级/命途/获取途径+skill 特效')
    lines.append('文本（官方 wiki 原文透传，含五档叠影数值）；光锥故事**不固化**；游戏内部')
    lines.append('数字 tid 不入本模块（tid 与名称的映射不在公开仓维护）。')
    lines.append('固化语义：obtain/skill 文本固化后本模块即唯一权威载体——重生成时已有词条')
    lines.append('冻结保留（wiki 侧存在编辑损坏，漂移由生成器报告供人工核对），wiki 只喂新增。')
    lines.append('')
    lines.append('id 定义：英文代号 = 官方英文名归一化（小写仅字母数字），来源国际版 HoYoWiki；')
    lines.append('权威表随仓分发（sr-od-dev-cone-data skill references/cones-full.json）。')
    lines.append('')
    lines.append('图标模板:``assets/template/light_cone_icon/<id>/raw.webp``(TemplateLoader')
    lines.append('规范二级结构,按 id 寻址;id 为空串的把暂缺,等 wiki 同步补 id 后归档)。')
    lines.append('')
    lines.append('版本刷新工序：游戏新版本后重跑官方 wiki 抓取并重新生成本模块（生成器随本仓')
    lines.append('skills/sr-od-dev-cone-data/ 维护）→ 与下方 LIGHT_CONES 逐条 diff → 人工审阅后')
    lines.append('更新常量；勿临时塞未经核验的数据。')
    lines.append('')
    lines.append('模块纪律：零外部 IO、零状态——纯常量 + 纯函数（同 sr_relic_sets 模块纪律）。')
    lines.append('"""')
    lines.append('')
    lines.append('from dataclasses import dataclass')
    lines.append('')
    lines.append('')
    lines.append('@dataclass(frozen=True)')
    lines.append('class LightConeDef:')
    lines.append('    """光锥定义（官方 wiki 快照固化）。')
    lines.append('')
    lines.append('    Attributes:')
    lines.append('        id: 英文代号 = 官方英文名归一化；国际版 HoYoWiki 未同步时为空串，')
    lines.append('            补齐前勿以 id 寻址（规则见 sr-od-dev-cone-data skill 附录）.')
    lines.append('        name: 官方光锥全名（社区简称不入表；基准：「于夜色中」/「银河铁道之夜」）。')
    lines.append('        rarity: 星级 3/4/5。')
    lines.append('        path_id: 命途 id（对齐 ``character_const`` 九命途 id 风格：')
    lines.append('            destruction/preservation/hunt/abundance/nihility/erudition/')
    lines.append('            harmony/remembrance/elation）。')
    lines.append('        obtain: 获取途径（官方 wiki 原文透传，如卡池/商店渠道；纯展示）。')
    lines.append('        skill: 光锥特效文本（官方 wiki 原文透传，含五档叠影梯度的【】数值')
    lines.append('            标记不清洗——展示原样；S1-S5 数值即括号序列自左至右）。')
    lines.append('    """')
    lines.append('')
    lines.append('    id: str')
    lines.append('    name: str')
    lines.append('    rarity: int')
    lines.append('    path_id: str')
    lines.append("    obtain: str = ''")
    lines.append("    skill: str = ''")
    lines.append('')
    lines.append('')
    lines.append('LIGHT_CONES: tuple[LightConeDef, ...] = (')

    prev_segment = ''
    for e in entries:
        if e['segment'] != prev_segment:
            if prev_segment:
                lines.append('')
            lines.append(f"    # ---- {e['segment']} ----")
            prev_segment = e['segment']
        lines.append('    LightConeDef(')
        lines.append(f"        id={py_str(e['id'])},")
        lines.append(f"        name={py_str(e['cn'])},")
        lines.append(f"        rarity={e['rarity']},")
        lines.append(f"        path_id={py_str(e['path_id'])},")
        # obtain/skill 存转义原文(冻结值原样复用/新增值经 py_str 预转义),直接包裹引号
        lines.append(f"        obtain='{e['obtain']}',")
        lines.append(f"        skill='{e['skill']}',")
        lines.append('    ),')
    lines.append(')')
    lines.append('')
    lines.append(f'# 名称反查索引：模块加载时构建一次（进程内缓存）；{n} 名称唯一由单测锁定。')
    lines.append('LIGHT_CONE_BY_NAME: dict[str, LightConeDef] = {')
    lines.append('    cone.name: cone for cone in LIGHT_CONES')
    lines.append('}')
    lines.append('')
    lines.append('def resolve_light_cone(name: str) -> LightConeDef | None:')
    lines.append('    """光锥名 → 定义（miss 返回 None，不抛异常）。"""')
    lines.append('    return LIGHT_CONE_BY_NAME.get(name)')
    lines.append('')

    OUT.write_text('\n'.join(lines), encoding='utf-8')
    print(f'已生成 {OUT}（{n} 把；新增 {len(fresh_names)}）')
    if fresh_names:
        print(f'新增词条（wiki 取文）: {fresh_names}')
    if drift:
        print(f'文本漂移 {len(drift)} 条（保持冻结值,请人工核对 wiki 是否误改）: {drift}')
    if skipped_manual:
        print(f'跳过 manual 行（等 wiki 词条）: {skipped_manual}')
    missing_icons = [e['cn'] for e in entries
                     if e['id'] and not (TEMPLATE_DIR / e['id'] / 'raw.webp').is_file()]
    if missing_icons:
        print(f'图标模板缺失 {len(missing_icons)}(图标工序补): {missing_icons}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
