// 读启动器页面全部可见文本（判断主按钮状态与弹窗内容）
// 前提：启动器已带 --remote-debugging-port=9222 启动
const BASE = 'http://127.0.0.1:9222';
const targets = await (await fetch(BASE + '/json/list')).json();
const page = targets.find(t => t.type === 'page');
if (!page) { console.log('no page target'); process.exit(1); }
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
  expression: 'document.body.innerText.replace(/\\n{2,}/g, "\\n").slice(0, 2500)',
  returnByValue: true, awaitPromise: false
});
console.log(r.result ? r.result.value : JSON.stringify(r));
ws.close();
process.exit(0);
