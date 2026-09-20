// Pass-through proxy to api.anthropic.com that dumps /v1/messages request BODIES only (never headers).
import http from 'node:http'; import https from 'node:https'; import { writeFileSync } from 'node:fs';
const out = process.argv[2]; let n = 0;
http.createServer((req, res) => {
  const chunks = []; req.on('data', c => chunks.push(c)); req.on('end', () => {
    const body = Buffer.concat(chunks);
    if (req.url.startsWith('/v1/messages') && !req.url.includes('count_tokens')) writeFileSync(`${out}/req-${++n}.json`, body);
    const headers = { ...req.headers, host: 'api.anthropic.com' };
    const up = https.request({ host: 'api.anthropic.com', path: req.url, method: req.method, headers }, r => { res.writeHead(r.statusCode, r.headers); r.pipe(res); });
    up.on('error', e => { res.writeHead(502); res.end(String(e)); }); up.end(body);
  });
}).listen(0, '127.0.0.1', function () { console.log(this.address().port); });
