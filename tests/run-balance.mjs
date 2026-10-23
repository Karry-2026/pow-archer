/**
 * 平衡测试一键入口
 *
 * 自己起静态服务器 → 跑多智能体压力测试 → 关服务器。
 * 不依赖外部已经跑着的服务，任何环境下一条命令就能复现。
 *
 *   node tests/run-balance.mjs                       第 5 波，4 策略各 1 轮
 *   node tests/run-balance.mjs --wave 10 --lv 24     第 10 波
 *   node tests/run-balance.mjs --runs 3              每策略 3 轮，看方差
 */
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const PORT = 8913;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.json': 'application/json'
};

const server = http.createServer((req, res) => {
  const clean = req.url.split('?')[0];
  const rel = clean === '/' ? 'index.html' : clean.replace(/^\/+/, '');
  const file = path.join(ROOT, rel);

  /* 只允许读项目目录内的文件，避免 ../ 穿越 */
  if(!file.startsWith(ROOT)){
    res.writeHead(403); res.end('forbidden'); return;
  }
  fs.readFile(file, (err, data) => {
    if(err){ res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, {'Content-Type': MIME[path.extname(file)] || 'application/octet-stream'});
    res.end(data);
  });
});

await new Promise(r => server.listen(PORT, '127.0.0.1', r));
console.log(`本地服务已起：http://127.0.0.1:${PORT}`);

const args = process.argv.slice(2);
const child = spawn(process.execPath, [path.join(__dirname, 'boss-bench.mjs'), ...args], {
  stdio: 'inherit',
  cwd: ROOT
});

const code = await new Promise(r => child.on('close', r));
server.close();
process.exit(code || 0);
