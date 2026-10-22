import fs from 'fs';

const html = fs.readFileSync('index.html', 'utf8');

/* 从 index.html 里把真实函数源码抓出来跑，而不是抄一份副本 */
function grab(name){
  const start = html.indexOf('function ' + name + '(');
  if(start < 0) throw new Error('not found: ' + name);
  let i = html.indexOf('{', start), depth = 0;
  for(let j = i; j < html.length; j++){
    if(html[j] === '{') depth++;
    else if(html[j] === '}'){ depth--; if(depth === 0) return html.slice(start, j + 1); }
  }
  throw new Error('unbalanced: ' + name);
}

const src = grab('isTouchDevice') + '\n' + grab('isPortraitNow') +
  '\nreturn { isTouchDevice: isTouchDevice, isPortraitNow: isPortraitNow };';

function build(env){
  const win = {
    screen: env.screen,
    innerWidth: env.w,
    innerHeight: env.h,
    matchMedia: q => ({ matches: !!(env.mq && env.mq[q]) })
  };
  const nav = { maxTouchPoints: env.touch === undefined ? 0 : env.touch };
  const fn = new Function('window', 'navigator', src);
  return fn(win, nav);
}

const cases = [
  { name: '手机竖屏（新 API）',       env:{ touch:5, mq:{'(hover: none)':true}, screen:{orientation:{type:'portrait-primary'}}, w:390, h:844 }, want:[true,true] },
  { name: '手机横屏（新 API）',       env:{ touch:5, mq:{'(hover: none)':true}, screen:{orientation:{type:'landscape-primary'}}, w:844, h:390 }, want:[true,false] },
  { name: '手机横屏倒转（新 API）',   env:{ touch:5, mq:{'(hover: none)':true}, screen:{orientation:{type:'landscape-secondary'}}, w:844, h:390 }, want:[true,false] },
  { name: '旧 Safari 竖屏',           env:{ touch:5, mq:{'(hover: none)':true}, screen:{}, w:390, h:844 }, want:[true,true] },
  { name: '旧 Safari 横屏',           env:{ touch:5, mq:{'(hover: none)':true}, screen:{}, w:844, h:390 }, want:[true,false] },
  { name: '桌面窄窗 800x1000（误判重灾区）', env:{ touch:0, mq:{'(hover: hover)':true}, screen:{orientation:{type:'portrait-primary'}}, w:800, h:1000 }, want:[false,true] },
  { name: '桌面触屏笔记本横屏',       env:{ touch:10, mq:{'(hover: hover)':true,'(pointer: fine)':true}, screen:{orientation:{type:'landscape-primary'}}, w:1600, h:900 }, want:[false,false] },
  { name: '桌面普通窗口',             env:{ touch:0, mq:{'(hover: hover)':true}, screen:{orientation:{type:'landscape-primary'}}, w:1280, h:800 }, want:[false,false] },
];

let pass = 0, fail = 0;
for(const c of cases){
  const api = build(c.env);
  const got = [api.isTouchDevice(), api.isPortraitNow()];
  const ok = got[0] === c.want[0] && got[1] === c.want[1];
  if(ok) pass++; else fail++;
  console.log((ok ? 'PASS' : 'FAIL') + '  ' + c.name);
  if(!ok) console.log('   期望 [触屏,竖屏] = [' + c.want + ']，实际 [' + got + ']');
}

console.log('\n合计 ' + pass + ' 通过 / ' + fail + ' 失败');
console.log('遮罩只在 [触屏 && 竖屏 && 用户没选就这样玩] 时出现');

/* 再验一遍：判断「横屏了遮罩还挂着」这个原始 bug
   模拟安卓转屏事件晚到：先竖屏，800ms 后变横屏 */
const api = build({ touch:5, mq:{'(hover: none)':true}, screen:{orientation:{type:'portrait-primary'}}, w:390, h:844 });
console.log('\n转屏前 isPortraitNow =', api.isPortraitNow(), '(期望 true)');
const env2 = { touch:5, mq:{'(hover: none)':true}, screen:{orientation:{type:'landscape-primary'}}, w:844, h:390 };
console.log('转屏后 isPortraitNow =', build(env2).isPortraitNow(), '(期望 false，遮罩应移除)');
