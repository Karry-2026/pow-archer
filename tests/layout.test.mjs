/* 布局回归测试：在多种屏幕尺寸下检查有没有元素溢出视口
 *
 * 用法（需要先起本地服务 + 带调试端口的浏览器）：
 *   python -m http.server 8907
 *   msedge --headless=new --remote-debugging-port=9915 about:blank
 *   node tests/layout.test.mjs
 *
 * 为什么需要这个：这个游戏是横屏游戏，真正的约束是「高度」不是「宽度」。
 * 844x390 的手机和 844x760 的桌面窄窗口宽度一样，靠肉眼看截图很容易漏。
 * 每次改 UI 跑一遍，比在真机上试快得多。
 */
import fs from 'fs';

const PORT = process.env.CDP_PORT || 9915;
const PAGE = process.env.APP_URL || 'http://127.0.0.1:8907/index.html';
const SHOT = process.env.SHOT === '1';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function findWs(){
  for(let i = 0; i < 20; i++){
    try{
      const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find(t => t.type === 'page'); if(p) return p.webSocketDebuggerUrl;
    }catch(e){}
    await sleep(400);
  }
  throw new Error('调试端口连不上，先启动 Edge --remote-debugging-port=' + PORT);
}

const ws = new WebSocket(await findWs());
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (m, p) => new Promise(res => {
  const i = ++id; pending.set(i, res);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}}));
});
async function ev(e){
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: true});
  if(r.result && r.result.exceptionDetails) return { __exc: r.result.exceptionDetails.text };
  return r.result && r.result.result ? r.result.result.value : undefined;
}

/* 设备清单：覆盖手机横屏、平板横屏、桌面 */
const DEVICES = [
  { name: 'iPhone 12/13 横屏', w: 844, h: 390, mobile: true },
  { name: '小屏安卓 横屏',     w: 780, h: 360, mobile: true },
  { name: '大屏安卓 横屏',     w: 915, h: 412, mobile: true },
  { name: 'iPad 横屏',         w: 1024, h: 768, mobile: true },
  { name: '笔记本 1440x900',   w: 1440, h: 900, mobile: false },
  { name: '笔记本 1280x720',   w: 1280, h: 720, mobile: false },
];

/* 检查函数：返回当前屏幕上所有溢出视口的可见元素 */
const PROBE = `(function(){
  var out = [];
  var sels = ['#scr-title', '#hud', '#scr-level', '#scr-bag', '#scr-pause'];
  sels.forEach(function(sel){
    var root = document.querySelector(sel);
    if(!root || !root.offsetParent) return;
    root.querySelectorAll('*').forEach(function(el){
      if(!el.offsetParent) return;
      var cs = getComputedStyle(el);
      if(cs.visibility === 'hidden' || cs.display === 'none') return;
      var r = el.getBoundingClientRect();
      if(r.width < 2 || r.height < 2) return;
      var dx = Math.max(0, Math.round(r.right - innerWidth));
      var dy = Math.max(0, Math.round(r.bottom - innerHeight));
      var dl = Math.max(0, Math.round(-r.left));
      var dt = Math.max(0, Math.round(-r.top));
      if(dx > 2 || dy > 2 || dl > 2 || dt > 2){
        var tag = el.id ? ('#' + el.id) : (el.className ? String(el.className).split(' ')[0] : el.tagName);
        out.push(sel + ' ' + tag + ' 溢出 ' + Math.max(dx, dl) + '/' + Math.max(dy, dt) + 'px');
      }
    });
  });
  return out.slice(0, 10);
})()`;

let pass = 0, fail = 0;
const failures = [];

for(const d of DEVICES){
  await send('Emulation.setDeviceMetricsOverride',
    { width: d.w, height: d.h, deviceScaleFactor: d.mobile ? 2 : 1, mobile: d.mobile });
  if(d.mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate', { url: PAGE + '?t=' + Date.now() });
  await sleep(4200);
  /* 模拟环境不会改 screen.orientation，手动撤掉竖屏遮罩 */
  await ev("var r=document.getElementById('rotate'); if(r) r.classList.remove('on'); 'ok'");

  const stages = [];

  /* 1. 标题页 */
  stages.push(['标题页', await ev(PROBE)]);
  if(SHOT){
    const s1 = await send('Page.captureScreenshot', { format: 'png' });
    if(s1.result && s1.result.data) fs.writeFileSync(`layout-${d.w}x${d.h}-title.png`, Buffer.from(s1.result.data, 'base64'));
  }

  /* 2. 游戏内 HUD */
  await ev("document.getElementById('startbtn').click(); 'ok'");
  await sleep(2000);
  stages.push(['游戏内', await ev(PROBE)]);

  /* 3. 升级三选一 */
  await ev("POW.gainXP(99999); 'ok'");
  await sleep(1000);
  stages.push(['升级页', await ev(PROBE)]);
  if(SHOT){
    const s2 = await send('Page.captureScreenshot', { format: 'png' });
    if(s2.result && s2.result.data) fs.writeFileSync(`layout-${d.w}x${d.h}-level.png`, Buffer.from(s2.result.data, 'base64'));
  }

  /* 4. 背包 */
  await ev("POW.S.mode='play'; document.getElementById('scr-level').classList.add('hide'); POW.renderBag(); document.getElementById('scr-bag').classList.remove('hide'); 'ok'");
  await sleep(700);
  stages.push(['背包页', await ev(PROBE)]);

  let devOk = true;
  for(const [stage, res] of stages){
    if(res && res.__exc){
      console.log(`FAIL  ${d.name} / ${stage}  执行报错: ${res.__exc}`);
      devOk = false; continue;
    }
    if(res && res.length){
      console.log(`FAIL  ${d.name} / ${stage}  ${res.length} 处溢出`);
      res.forEach(x => console.log('        ' + x));
      devOk = false;
    }
  }
  if(devOk) console.log(`PASS  ${d.name}  ${d.w}x${d.h}  四个界面均无溢出`);
  devOk ? pass++ : (fail++, failures.push(d.name));
}

console.log(`\n合计 ${pass} 通过 / ${fail} 失败`);
if(fail) console.log('失败的设备：' + failures.join('、'));
ws.close();
process.exit(fail ? 1 : 0);
