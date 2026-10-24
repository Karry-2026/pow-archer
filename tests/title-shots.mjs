/* 开始界面截图：四个尺寸各一张，顺带量关键元素的矩形。
 * 用法：node tests/_titleshot.mjs
 */
const PORT = 9971;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const SIZES = [
  [1440, 900, 'desktop'],
  [1280, 720, 'laptop'],
  [844, 390, 'iphone'],
  [780, 360, 'small'],
];

(async () => {
  const list = await (await fetch('http://127.0.0.1:' + PORT + '/json/list')).json();
  const page = list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  let id = 0; const pending = new Map();
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method: m, params: p || {} })); });
  const ev = async e => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true });
    if (r.result.exceptionDetails) return 'EXC:' + JSON.stringify(r.result.exceptionDetails).slice(0, 200);
    return r.result.result ? r.result.result.value : undefined;
  };
  const fs = await import('fs');
  const shot = async n => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync('screenshots/' + n, Buffer.from(r.result.data, 'base64'));
  };

  for (const [w, h, tag] of SIZES) {
    await send('Emulation.setDeviceMetricsOverride', {
      width: w, height: h, deviceScaleFactor: w > 1000 ? 1 : 2, mobile: w < 1000,
    });
    await send('Page.navigate', { url: 'http://127.0.0.1:8921/index.html?t=' + Date.now() });
    await sleep(3600);
    const info = await ev(`(function(){
      var r = function(sel){ var e=document.querySelector(sel); if(!e) return null;
        var b=e.getBoundingClientRect();
        return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]; };
      var out = {
        logo: r('.tt-logo'), tag: r('.tt-tag'), hero: r('.tt-hero'), rate: r('.tt-rate'),
        foot: r('.tt-foot'), mute: r('.tt-mute-probe') || r('#mutebtn'),
        scrollH: document.getElementById('scr-title').scrollHeight,
        clientH: document.getElementById('scr-title').clientHeight,
      };
      var cards = [].map.call(document.querySelectorAll('#scr-title .pick'), function(e){
        var b=e.getBoundingClientRect(); return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)];
      });
      out.cards = cards;
      var btns = [].map.call(document.querySelectorAll('#scr-title .rate button'), function(e){
        var b=e.getBoundingClientRect(); return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)];
      });
      out.rates = btns;
      return JSON.stringify(out);
    })()`);
    console.log(tag, w + 'x' + h, info);
    await shot('v014-title-' + tag + '.png');
  }
  ws.close();
})();
