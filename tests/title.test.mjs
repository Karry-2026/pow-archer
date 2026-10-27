/* 开始界面回归：切线与内容有没有打架 + 按钮能不能用。
 *
 * 为什么要有这个用例：新布局靠「斜切线 + 内边距」避让，
 * 内边距是算出来的，不是排出来的。字号、行高、断点任何一处改动
 * 都可能让某个控件重新压到斜线上，而这种问题截图不放大看不出来。
 * 所以直接拿几何算：每个右列控件的左边必须落在切线右侧。
 *
 * 用法：
 *   python -m http.server 8921
 *   msedge --headless=new --remote-debugging-port=9971 ...
 *   node tests/title.test.mjs
 */
const PORT = Number(process.env.CDP_PORT || 9971);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const SIZES = [
  [1440, 900], [1280, 720], [1024, 768],
  [844, 390], [780, 360], [915, 412],
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

  let fails = 0;
  const ok = (cond, msg) => { if (!cond) fails++; console.log((cond ? '  ✓ ' : '  ✗ ') + msg); };

  for (const [w, h] of SIZES) {
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w < 1000 });
    await send('Page.navigate', { url: (process.env.APP_URL || 'http://127.0.0.1:8921/index.html') + '?t=' + Date.now() });
    await sleep(3400);
    await ev("window.__POW_BOOT && window.__POW_BOOT(); 'ok'");
    await sleep(900);
    console.log(`\n[${w}x${h}]`);

    /* 1) 切线：纸面右边缘 = 52% + 11.5vh - 30（向下走时右移）。
          高 <=520 时纸面/墨面仍是同一套公式，所以统一按这个算。 */
    const res = await ev(`(function(){
      var W = innerWidth, H = innerHeight;
      var edge = function(y){ return 0.52*W + ((y - H/2)/(H/2)) * 0.115*H; };
      var bad = [];
      var pick = function(sel){
        return [].slice.call(document.querySelectorAll(sel));
      };
      // 右列里所有「有可见文字或边框」的控件
      pick('.tt-rate .tt-lab, #scr-title .rate button, .tt-foot .startbig, .tt-foot .codexbtn, #mutebtn')
        .forEach(function(e){
          var b = e.getBoundingClientRect();
          if(!b.width || getComputedStyle(e).display === 'none') return;
          var need = edge(b.bottom - 2) - 2;   // 用底边算，切线最低处
          if(b.left < need){
            bad.push((e.id || e.className || e.tagName) + ' left=' + Math.round(b.left) + ' < ' + Math.round(need));
          }
        });
      return JSON.stringify({bad: bad, W: W, H: H});
    })()`);
    const r1 = JSON.parse(res);
    ok(r1.bad.length === 0, '右列控件全部避开斜切线' + (r1.bad.length ? ' → ' + r1.bad.join(' | ') : ''));

    /* 2) 页面不该出现滚动条（标题页是满屏构图） */
    const scroll = await ev(`(function(){var e=document.getElementById('scr-title');
      return JSON.stringify({s:e.scrollHeight,c:e.clientHeight});})()`);
    const sc = JSON.parse(scroll);
    ok(sc.s <= sc.c + 1, `标题页不溢出（scroll ${sc.s} / client ${sc.c}）`);

    /* 3) 关键控件都在视口内 */
    const inView = await ev(`(function(){
      var out = [];
      ['.tt-logo','#heroes','#rates','#startbtn','#mutebtn'].forEach(function(s){
        var e = document.querySelector(s); if(!e) { out.push(s+':missing'); return; }
        var b = e.getBoundingClientRect();
        if(b.left < -1 || b.top < -1 || b.right > innerWidth+1 || b.bottom > innerHeight+1)
          out.push(s+':'+[b.left,b.top,b.right,b.bottom].map(Math.round).join(','));
      });
      return JSON.stringify(out);
    })()`);
    ok(JSON.parse(inView).length === 0, 'logo / 射手卡 / 密度 / 开始 / 静音 都在视口内' + (JSON.parse(inView).length ? ' → ' + inView : ''));

    /* 4) 选角色 + 改密度 + 点开始，整条链路要通 */
    const flow = await ev(`(function(){
      var p = document.querySelectorAll('#scr-title .pick');
      if(p.length !== 4) return 'cards=' + p.length;
      p[1].click();
      var rb = document.querySelectorAll('#scr-title .rate button');
      if(rb.length !== 4) return 'rates=' + rb.length;
      rb[3].click();
      var on = document.querySelector('#scr-title .pick.on');
      var ron = document.querySelector('#scr-title .rate button.on');
      var a = on ? on.textContent.indexOf('激光手') >= 0 : false;
      var b = ron ? ron.textContent.indexOf('地狱') >= 0 : false;
      return JSON.stringify({hero: a, rate: b});
    })()`);
    const f = JSON.parse(flow);
    ok(f.hero && f.rate, '选中第二个职业 / 第四个密度档位');

    await ev("document.getElementById('startbtn').click(); 'ok'");
    await sleep(700);
    const started = await ev("JSON.stringify({mode: POW.S.mode, hudShown: !document.getElementById('hud').classList.contains('hide'), titleHidden: getComputedStyle(document.getElementById('scr-title')).display === 'none'})");
    const st = JSON.parse(started);
    ok(st.mode === 'play' && st.hudShown && st.titleHidden, '点开始 → 进入战斗、HUD 出现、标题页隐藏');
  }

  console.log('\n' + (fails === 0 ? 'ALL PASS' : fails + ' FAILED'));
  ws.close();
  process.exit(fails === 0 ? 0 : 1);
})();
