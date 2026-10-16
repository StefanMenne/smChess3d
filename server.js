// Kleiner statischer Webserver ohne Abhängigkeiten.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));

const MOUNTS = [
  ['/vendor/three/', path.join(root, 'node_modules/three/')],
  ['/vendor/chess.js', path.join(root, 'node_modules/chess.js/dist/esm/chess.js')],
  ['/pieces/', path.join(root, 'pieces/')],
  ['/', path.join(root, 'public/')],
];

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.glb': 'model/gltf-binary',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function resolve(urlPath) {
  for (const [prefix, target] of MOUNTS) {
    if (!prefix.endsWith('/')) {
      if (urlPath === prefix) return target;
      continue;
    }
    if (urlPath.startsWith(prefix)) {
      const file = path.normalize(path.join(target, urlPath.slice(prefix.length)));
      // Kein Ausbrechen aus dem gemounteten Verzeichnis
      return file.startsWith(target) ? file : null;
    }
  }
  return null;
}

export function createServer() {
  return http.createServer((req, res) => {
    let urlPath = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (urlPath === '/') urlPath = '/index.html';
    const file = resolve(urlPath);
    if (!file) {
      res.writeHead(404).end('Not found');
      return;
    }
    fs.stat(file, (err, stat) => {
      if (err || !stat.isFile()) {
        res.writeHead(404).end('Not found');
        return;
      }
      res.writeHead(200, {
        'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream',
        'Content-Length': stat.size,
        'Cache-Control': 'no-cache',
      });
      fs.createReadStream(file).pipe(res);
    });
  });
}

export function listen(port = Number(process.env.PORT) || 3000) {
  return new Promise((ok, fail) => {
    const server = createServer();
    server.once('error', fail);
    server.listen(port, '127.0.0.1', () => ok(server));
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const server = await listen();
  console.log(`Schach läuft auf http://127.0.0.1:${server.address().port}`);
}
