/* BGM 离线渲染导出：渲染整首 → base64 分块取回 → 写 WAV → ffmpeg 转 MP3 */
import fs from 'fs';
import path from 'path';

const PORT = 9971;
const OUT_DIR = 'C:/Users/karry/WorkBuddy/2026-10-23-00-53-14/pow-archer/_bgm_out';
const sleep = ms => new Promise(r => setTimeout(r, ms));
fs.mkdirSync(OUT_DIR, { recursive: true });

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); const errs = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
  if(m.method === 'Runtime.exceptionThrown') errs.push(((m.params.exceptionDetails.exception||{}).description||'').split('\n')[0]);
});
const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
const ev = async (e, awaitP) => {
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: !!awaitP});
  if(r.result.exceptionDetails) return 'EXC:' + ((r.result.exceptionDetails.exception||{}).description || r.result.exceptionDetails.text).split('\n')[0];
  return r.result.result ? r.result.result.value : undefined;
};

await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', {url: 'http://127.0.0.1:8921/index.html?t=' + Date.now()});
await sleep(4200);

const mode = process.argv[2] || 'battle';
const info = await ev(`window.renderBGMToBase64('${mode}', 1)`, true);
console.log('渲染:', JSON.stringify(info));
if(typeof info === 'string' && info.startsWith('EXC')) process.exit(1);

const total = info.b64len;
const CH = 2000000;
const parts = [];
for(let i=0;i<total;i+=CH){
  const s = await ev(`window.__wavB64.slice(${i}, ${Math.min(i+CH, total)})`);
  if(typeof s !== 'string'){ console.log('取块失败', i, s); process.exit(1); }
  parts.push(s);
  process.stdout.write(`\r取回 ${Math.min(i+CH,total)}/${total}`);
}
console.log('');
const wav = path.join(OUT_DIR, `${mode}.wav`);
fs.writeFileSync(wav, Buffer.from(parts.join(''), 'base64'));
console.log('WAV:', wav, (fs.statSync(wav).size/1024/1024).toFixed(1)+'MB');
console.log('JS 错误:', errs.length);
ws.close();
