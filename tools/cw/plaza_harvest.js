/**
 * 货币战争 · 攻略广场浏览器采集脚本(免环境版,console 粘贴运行)。
 * 用法:在已打开的 act.miyoushe.com/sr/event/currency-wars/ 任意页面 F12 console
 *      粘贴本文件全部内容回车 → 自动拉 config + N 页攻略 → 弹出单文件 JSON 下载。
 * 产出 JSON 结构: {version, manifest{role,equip}, lineups[], fetched_at}
 *   - manifest = id↔name↔icon_url 映射(稳定键=数字 id,URL 版本更新会变);
 *   - lineups 每条含 tourn_detail.role_stages 三阶段阵容(Early/Middle/Final)。
 * 后续本地处理: python tools/cw/plaza_fetch.py 有同能力的命令行版+icon 下载。
 * 映射细节/URL 变化应对 见 tools/cw/plaza_fetch.py 模块 docstring。
 */
(async () => {
  // ===== 参数(按需改) =====
  const PAGES = 5;            // 采集页数(10 篇/页)
  const ORDER = "Hot";        // Hot | Recommend
  const TRAIT_IDS = [];       // 羁绊筛选,如 [1001]=列车同行(id 见 manifest/config)
  const ROLE_IDS = [];        // 角色筛选,如 [1009]=艾丝妲
  const SLEEP_MS = 500;

  const BASE = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar/game";
  const H = { "Content-Type": "application/json", "x-rpc-currencywar-tourn": "tourn" };
  const post = async (path, body) => (await fetch(`${BASE}/${path}`, {
    method: "POST", headers: H, body: JSON.stringify(body) })).json();
  const get = async (path) => (await fetch(`${BASE}/${path}`, { headers: H })).json();
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  // 1) config → manifest
  const cfg = await get("config?game=hkrpg");
  if (cfg.retcode !== 0) throw new Error("config retcode=" + cfg.retcode);
  const manifest = { role: {}, equip: {} };
  for (const r of cfg.data.role_list)
    manifest.role[r.id] = { name: r.name, icon: r.icon, big_icon: r.big_icon || "" };
  for (const e of cfg.data.equipment_list)
    manifest.equip[e.id] = { name: e.name, icon: e.icon, big_icon: e.big_icon || "" };
  console.log(`[harvest] config v${cfg.data.rpg_game_big_version}: `
    + `${Object.keys(manifest.role).length}角色 ${Object.keys(manifest.equip).length}装备`);

  // 2) lineup/index 分页(cursor)
  const lineups = [];
  const seen = new Set();
  let token = "";
  for (let page = 1; page <= PAGES; page++) {
    const d = await post("lineup/index", {
      game: "hkrpg", page: String(page), limit: "10", lineup_type: "Tourn",
      next_page_token: token, role_ids: ROLE_IDS, trait_ids: TRAIT_IDS,
      match_change_job: false, match_hard: false, order: ORDER,
    });
    if (d.retcode !== 0) throw new Error("lineup p" + page + " retcode=" + d.retcode);
    const fresh = (d.data.list || []).filter(x => !seen.has(x.id));
    fresh.forEach(x => seen.add(x.id));
    lineups.push(...fresh);
    token = d.data.next_page_token || "";
    console.log(`[harvest] p${page}: +${fresh.length} (总${lineups.length}) `
      + (fresh[0] ? fresh[0].title.slice(0, 24) : ""));
    if (!fresh.length || !token) { console.log("[harvest] 无更多"); break; }
    await sleep(SLEEP_MS);
  }

  // 3) 单文件 JSON 下载(浏览器安全,无多文件权限问题)
  const payload = {
    version: cfg.data.rpg_game_big_version, fetched_at: new Date().toISOString(),
    order: ORDER, trait_ids: TRAIT_IDS, role_ids: ROLE_IDS,
    manifest, lineups,
  };
  const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `plaza_harvest_${ORDER}_v${payload.version}_${lineups.length}篇.json`;
  document.body.appendChild(a); a.click(); a.remove();
  console.log(`[harvest] 完成: ${lineups.length}篇 已触发下载`);
  return lineups.length;
})();