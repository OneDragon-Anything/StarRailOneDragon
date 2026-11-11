"""组装遗器权威表:常量 RELIC_SETS × 国内 content_id × 国际服 en/id 映射。

输入(先跑同目录两个 fetch 脚本刷新):
  .debug/temp/relic_wiki/cnwiki_relic_list.json     国内 channel 30 列表
  .debug/temp/relic_wiki/hoyowiki_relic_id_map.json 国际服 zh/en 互连映射

产出(权威表,提交进仓):references/relics-full.json,键 = 归一化中文名(国服
官方名),字段:cn/en/id/kind/wiki_content_id/hoyowiki_page_id/intl_cn/order/source。
国际服未收录的套装 en/id/hoyowiki_page_id 留空;国内 wiki 未收录的
source='manual'(文本源=官方公告)。挂接架构见 skill SKILL.md §2。
仅标准库,项目根目录运行:
    uv run python skills/sr-od-dev-relic-data/scripts/build_relic_authority_table.py
"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # Windows 控制台默认 GBK,中文输出会乱码

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from sr_od.mys.sr_relic_sets import RELIC_SETS  # noqa: E402

TEMP = PROJECT_ROOT / '.debug' / 'temp' / 'relic_wiki'
OUT_FILE = Path(__file__).resolve().parents[1] / 'references' / 'relics-full.json'

# 常量名 → intl 词条名（译名差异别名;国际服本地化与国服名不一致时人工登记,
# 按 entry_page_id 对齐）。 intl 名「停止转动的萨尔索图」= 国服「停转的萨尔索图」。
INTL_ALIAS: dict[str, str] = {
    '停转的萨尔索图': '停止转动的萨尔索图',
}


def norm_cn(name: str) -> str:
    """连表键归一化:折叠空白(BOM/半角逗号由 fetch 脚本在 intl 侧清理)。"""
    return re.sub(r'\s+', '', name)


def main() -> int:
    cn_list = json.loads((TEMP / 'cnwiki_relic_list.json').read_text(encoding='utf-8'))
    intl_map = json.loads((TEMP / 'hoyowiki_relic_id_map.json').read_text(encoding='utf-8'))

    cn_by_name: dict[str, dict] = {norm_cn(e['name']): e for e in cn_list}
    table: dict[str, dict] = {}
    consumed_cn: set[int] = set()
    consumed_intl: set[str] = set()
    manual_sets: list[str] = []

    for order, relic_set in enumerate(RELIC_SETS, start=1):
        key = norm_cn(relic_set.set_name)
        cn_row = cn_by_name.get(key)
        intl_key = norm_cn(INTL_ALIAS.get(relic_set.set_name, relic_set.set_name))
        intl_row = intl_map.get(intl_key)
        if cn_row is not None:
            consumed_cn.add(cn_row['content_id'])
        if intl_row is not None:
            consumed_intl.add(intl_row['hoyowiki_page_id'])
        source = 'wiki' if cn_row is not None else 'manual'
        if source == 'manual':
            manual_sets.append(relic_set.set_name)
        row: dict = {
            'cn': relic_set.set_name,
            'en': intl_row['en'] if intl_row else '',
            'id': relic_set.id,
            'kind': relic_set.kind,
            'wiki_content_id': str(cn_row['content_id']) if cn_row else '',
            'hoyowiki_page_id': intl_row['hoyowiki_page_id'] if intl_row else '',
            'order': order,
            'source': source,
        }
        if intl_key != key:  # 译名差异别名落表(缺省 = 与 cn 同,不占字段)
            row['intl_cn'] = INTL_ALIAS[relic_set.set_name]
        if key in table:
            raise RuntimeError(f'权威表撞键: {key}')
        table[key] = row

    # 对账:输入侧未消费的条目 = 常量缺失或撞键,人工审阅
    unconsumed_cn = [e for e in cn_list if e['content_id'] not in consumed_cn]
    unconsumed_intl = [(v['hoyowiki_page_id'], k) for k, v in intl_map.items()
                       if v['hoyowiki_page_id'] not in consumed_intl]
    if unconsumed_cn:
        print(f'⚠ 国内 wiki 未对上常量的词条 {len(unconsumed_cn)}: {unconsumed_cn}')
    if unconsumed_intl:
        print(f'⚠ 国际服未对上常量的词条 {len(unconsumed_intl)}: {unconsumed_intl}')
    empty_id = sorted(k for k, v in table.items() if not v['id'])
    print(f'权威表 {len(table)} 条 | manual {len(manual_sets)}: {manual_sets}')
    print(f'空 id {len(empty_id)}(国际服未同步,宁缺勿错): {empty_id}')

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'产出 {OUT_FILE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
