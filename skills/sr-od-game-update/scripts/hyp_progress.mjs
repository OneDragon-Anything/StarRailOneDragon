// 只打印启动器进度相关文本行（下载中/校验并修复/百分比/剩余时间），适合轮询
// 前提：启动器已带 --remote-debugging-port=9222 启动
const BASE = 'http://127.0.0.1:9222';
try {
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
    expression: `(() => {
      const lines = document.body.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
      const interesting = lines.filter(s => /下载|暂停|继续|更新|安装|校验|解压|%|^\\d+$|\\d{2}:\\d{2}/.test(s));
      return interesting.slice(0, 8).join(' | ');
    })()`,
    returnByValue: true, awaitPromise: false
  });
  console.log(r.result ? r.result.value : JSON.stringify(r));
  ws.close();
} catch (e) {
  console.log('probe error: ' + e.message);
}
process.exit(0);
