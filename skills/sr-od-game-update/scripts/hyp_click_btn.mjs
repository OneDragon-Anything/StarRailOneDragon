// 按精确文本点击启动器页面按钮（匹配 button / .button-message / .hyp-el-button）
// 用法：node hyp_click_btn.mjs "<按钮文本>"；返回 {"ok":true} 才算点到
// 前提：启动器已带 --remote-debugging-port=9222 启动
const label = process.argv[2];
if (!label) { console.log('{"ok":false,"reason":"usage: node hyp_click_btn.mjs <button text>"}'); process.exit(1); }
const BASE = 'http://127.0.0.1:9222';
const targets = await (await fetch(BASE + '/json/list')).json();
const page = targets.find(t => t.type === 'page');
if (!page) { console.log('{"ok":false,"reason":"no page target"}'); process.exit(1); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
function send(method, params) {
  return new Promise((res, rej) => {
    const mid = ++id; pending.set(mid, { res, rej });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
}
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const p = pending.get(m.id); pending.delete(m.id);
    m.error ? p.rej(new Error(m.error.message)) : p.res(m.result);
  }
};
await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
const r = await send('Runtime.evaluate', {
  expression: `(() => {
    const want = ${JSON.stringify(label)};
    const cands = [...document.querySelectorAll('button, .button-message, .hyp-el-button, [class*=btn]')]
      .filter(e => (e.innerText || '').trim() === want && (e.getBoundingClientRect().width > 0));
    if (!cands.length) return { ok: false, reason: 'not found: ' + want };
    cands[0].click();
    return { ok: true, tag: cands[0].tagName, cls: String(cands[0].className).slice(0, 60), total: cands.length };
  })()`,
  returnByValue: true, awaitPromise: false
});
console.log(JSON.stringify(r.result ? r.result.value : r));
ws.close();
process.exit(0);
