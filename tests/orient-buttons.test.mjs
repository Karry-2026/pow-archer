import fs from 'fs';

const html = fs.readFileSync('index.html', 'utf8');

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

/* 从 index.html 抓真实的 bindOrientUI 来跑，不是抄一份 */
const src = grab('bindOrientUI');
const makeBind = new Function('skipOrient', 'tryLockLandscape', 'document', 'window',
  src + '\nreturn bindOrientUI;');

function mkEl(tag){
  const cls = new Set();
  return {
    tagName: tag || 'DIV',
    onclick: null,
    classList: {
      add(c){ cls.add(c); }, remove(c){ cls.delete(c); },
      contains(c){ return cls.has(c); }
    },
    _cls: cls
  };
}

let pass = 0, fail = 0;
function check(name, cond, extra){
  if(cond){ pass++; console.log('PASS  ' + name); }
  else { fail++; console.log('FAIL  ' + name + (extra ? '  → ' + extra : '')); }
}

const els = { rotbtn: mkEl('BUTTON'), rotskip: mkEl('BUTTON'), rotate: mkEl('DIV') };
const doc = { getElementById: id => els[id] || null };
const win = {};

let lockCalls = 0, skipCalls = 0;
const bind = makeBind(
  () => { skipCalls++; },
  () => { lockCalls++; },
  doc, win
);
bind();

check('自动横屏按钮绑上了 onclick', typeof els.rotbtn.onclick === 'function');
check('就这样玩按钮绑上了 onclick', typeof els.rotskip.onclick === 'function');
check('遮罩本身绑上了 onclick', typeof els.rotate.onclick === 'function');
check('window.__POW_LOCK 已挂出', typeof win.__POW_LOCK === 'function');
check('window.__POW_SKIP 已挂出', typeof win.__POW_SKIP === 'function');

/* 点「自动横屏」 */
if(els.rotbtn.onclick) els.rotbtn.onclick({ stopPropagation(){} });
check('点自动横屏 → 触发锁屏', lockCalls === 1, '实际 ' + lockCalls + ' 次');

/* 点「就这样玩」 */
if(els.rotskip.onclick) els.rotskip.onclick({ stopPropagation(){} });
check('点就这样玩 → 触发跳过', skipCalls === 1, '实际 ' + skipCalls + ' 次');

/* 点遮罩空白处 = 跳过 */
skipCalls = 0;
if(els.rotate.onclick) els.rotate.onclick({ target: { tagName: 'DIV' } });
check('点遮罩空白处 → 也能跳过', skipCalls === 1, '实际 ' + skipCalls + ' 次');

/* 点遮罩里的按钮不能重复触发（避免一次点击走两条路） */
skipCalls = 0;
if(els.rotate.onclick) els.rotate.onclick({ target: { tagName: 'BUTTON' } });
check('点遮罩内按钮 → 不重复触发', skipCalls === 0, '实际 ' + skipCalls + ' 次');

/* 不在这里提前打「合计」：原来打在静态检查之前，数字少算后面三条断言，
   出现过「合计 9/0」但最终 11/1 的迷惑输出。汇总放最后。 */

/* 静态检查：启动区必须真的调用了 bindOrientUI */
/* 断言「定义之后、顶层调用过」，不绑定具体行距。
   旧写法取 window.POW 前 400 字符，再要求 bindOrientUI(); 紧跟 checkOrient();
   v0.17 在两者之间插入 bindUltTap() 后行距拉开 40 多行，断言随即误报。 */
const defIdx = html.indexOf('function bindOrientUI(');
const callIdx = html.lastIndexOf('bindOrientUI();');
const bootOk = defIdx > 0 && callIdx > defIdx;
check('启动区调用了 bindOrientUI', bootOk, bootOk ? '' : '启动区没调用');

/* 静态检查：HTML 里按钮有内联兜底 */
check('按钮有内联 onclick 兜底',
  html.includes('onclick="window.__POW_LOCK&&window.__POW_LOCK()"') &&
  html.includes('onclick="window.__POW_SKIP&&window.__POW_SKIP()"'));

/* 静态检查：bindOrientUI 里不能再嵌套调用自己（上一轮的错误） */
const fnSrc = grab('bindOrientUI');
check('bindOrientUI 内没有自我递归', !/bindOrientUI\(\)\s*;/.test(fnSrc.replace(/function bindOrientUI\(\)/, '')));

console.log('\n最终 ' + pass + ' 通过 / ' + fail + ' 失败');
process.exit(fail ? 1 : 0);
