import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { Chess } from 'chess.js';

// ---------------------------------------------------------------------------
// Konstanten
// ---------------------------------------------------------------------------

const FILES = 'abcdefgh';
const PIECE_FILE = { p: 'bauer', n: 'springer', b: 'laeufer', r: 'turm', q: 'dame', k: 'koenig' };
const COLOR_FILE = { w: 'weiss', b: 'schwarz' };
const PIECE_NAME = { p: 'Bauer', n: 'Springer', b: 'Läufer', r: 'Turm', q: 'Dame', k: 'König' };
const PIECE_SCALE = 1.05;
const WALK_SPEED = 2.2; // Felder pro Sekunde
const TURN_TIME = 0.22; // s zum Umdrehen in Laufrichtung
// Bauer (Hase): gleichmäßige Sprünge, vorwärts nur in der Flugphase des Walk-Clips
const PAWN_HOPS_PER_SQUARE = 2; // 1–3
const PAWN_HOP_TIME = 0.42; // s pro Sprung (Walk-Clip wird darauf beschleunigt)
const HOP_AIR = [0.3, 0.82]; // Abstoßen bis Landung im Clip (Anteile, tools/rig_biped.py --mode hop)
// Die Modelle schauen in +Z. Weiß steht bei +Z und soll nach -Z (zu Schwarz) schauen.
const BASE_YAW = { w: Math.PI, b: 0 };
const MIN_THINK_MS = 450;
// Umrissdicke in Welteinheiten (1 = eine Feldbreite). Durch die Perspektive
// wird die Linie bei weiter entfernten Figuren automatisch dünner.
const OUTLINE_WIDTH = 0.022;
const SETTINGS_KEY = 'schach3d.settings';

// ---------------------------------------------------------------------------
// DOM
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const container = $('scene');
const statusEl = $('status');
const movesEl = $('moves');
const colorSel = $('color');
const levelSel = $('level');
const undoBtn = $('undo');
const toonBox = $('toon');
const renderInfoBox = $('renderInfo');
const statsEl = $('stats');

// ---------------------------------------------------------------------------
// Einstellungen
// ---------------------------------------------------------------------------

const settings = { toon: false, renderInfo: false };
try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY))); } catch { /* egal */ }

function saveSettings() {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch { /* egal */ }
}

// ---------------------------------------------------------------------------
// Szene
// ---------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x24262c);
scene.fog = new THREE.Fog(0x24262c, 22, 45);

// Umgebung für Spiegelungen – ohne sie bleiben metallische Flächen (z. B. die
// goldenen Kronen) schwarz, da Metall seine Farbe fast nur aus Reflexionen bezieht
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.6;
pmrem.dispose();

const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enablePan = false;
controls.enableDamping = true;
controls.minDistance = 3;
controls.maxDistance = 22;
controls.maxPolarAngle = 1.3;
controls.target.set(0, 0, 0);

scene.add(new THREE.HemisphereLight(0xfff4e0, 0x3a3428, 0.8));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(5, 12, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -7;
sun.shadow.camera.right = 7;
sun.shadow.camera.top = 7;
sun.shadow.camera.bottom = -7;
sun.shadow.bias = -0.0005;
scene.add(sun);
const fill = new THREE.DirectionalLight(0xbcd0ff, 0.5);
fill.position.set(-6, 6, -5);
scene.add(fill);

function squareToPos(sq) {
  const f = FILES.indexOf(sq[0]);
  const r = Number(sq[1]) - 1;
  return new THREE.Vector3(f - 3.5, 0, 3.5 - r);
}

function posToSquare(x, z) {
  const f = Math.floor(x + 4);
  const r = Math.floor(4 - z);
  if (f < 0 || f > 7 || r < 0 || r > 7) return null;
  return FILES[f] + (r + 1);
}

const labels = [];

function buildBoard() {
  const board = new THREE.Group();
  const light = new THREE.MeshStandardMaterial({ color: 0xe8d4ae, roughness: 0.55 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x8f6340, roughness: 0.55 });
  const geo = new THREE.BoxGeometry(1, 0.12, 1);
  for (let f = 0; f < 8; f++) {
    for (let r = 0; r < 8; r++) {
      const m = new THREE.Mesh(geo, (f + r) % 2 === 0 ? dark : light);
      m.position.set(f - 3.5, -0.06, 3.5 - r);
      m.receiveShadow = true;
      board.add(m);
    }
  }
  const frame = new THREE.Mesh(
    new THREE.BoxGeometry(9.3, 0.3, 9.3),
    new THREE.MeshStandardMaterial({ color: 0x4a2f1e, roughness: 0.45 }),
  );
  frame.position.y = -0.17;
  frame.receiveShadow = true;
  board.add(frame);

  const table = new THREE.Mesh(
    new THREE.CircleGeometry(30, 64),
    new THREE.MeshStandardMaterial({ color: 0x2c2a28, roughness: 0.9 }),
  );
  table.rotation.x = -Math.PI / 2;
  table.position.y = -0.33;
  table.receiveShadow = true;
  board.add(table);

  // Koordinaten am Rand
  const label = (text) => {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d');
    g.fillStyle = '#e8d4ae';
    g.font = 'bold 40px system-ui, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText(text, 32, 34);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(0.32, 0.32),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true }),
    );
    m.rotation.x = -Math.PI / 2;
    return m;
  };
  for (let i = 0; i < 8; i++) {
    for (const side of [-1, 1]) {
      const l = label(FILES[i]);
      l.position.set(i - 3.5, -0.015, side * 4.32);
      const n = label(String(i + 1));
      n.position.set(side * 4.32, -0.015, 3.5 - i);
      board.add(l, n);
      labels.push(l, n);
    }
  }
  return board;
}
scene.add(buildBoard());

const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

// Markierungen (Auswahl, mögliche Züge, letzter Zug, Schach)
const marks = new THREE.Group();
scene.add(marks);
const markGeo = new THREE.PlaneGeometry(1, 1);
const dotGeo = new THREE.CircleGeometry(0.15, 32);
const ringGeo = new THREE.RingGeometry(0.38, 0.47, 40);
const markMats = {
  selected: new THREE.MeshBasicMaterial({ color: 0x6ad15a, transparent: true, opacity: 0.55, depthWrite: false }),
  last: new THREE.MeshBasicMaterial({ color: 0xf2d24b, transparent: true, opacity: 0.4, depthWrite: false }),
  check: new THREE.MeshBasicMaterial({ color: 0xe0352b, transparent: true, opacity: 0.6, depthWrite: false }),
  move: new THREE.MeshBasicMaterial({ color: 0x1d5e14, transparent: true, opacity: 0.6, depthWrite: false }),
};

function addMark(sq, kind, y = 0.003) {
  const geo = kind === 'dot' ? dotGeo : kind === 'ring' ? ringGeo : markGeo;
  const mat = kind === 'dot' || kind === 'ring' ? markMats.move : markMats[kind];
  const m = new THREE.Mesh(geo, mat);
  m.rotation.x = -Math.PI / 2;
  m.position.copy(squareToPos(sq)).setY(y);
  m.renderOrder = 1;
  marks.add(m);
}

// ---------------------------------------------------------------------------
// Animations-Helfer
// ---------------------------------------------------------------------------

const tweens = new Set();
const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

function tween(duration, fn, easing = ease) {
  return new Promise((resolve) => {
    if (duration <= 0) { fn(1); resolve(); return; }
    tweens.add({ t: 0, duration, fn, easing, resolve });
  });
}

function updateTweens(dt) {
  for (const tw of tweens) {
    tw.t = Math.min(1, tw.t + dt / tw.duration);
    tw.fn(tw.easing(tw.t));
    if (tw.t >= 1) { tweens.delete(tw); tw.resolve(); }
  }
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function angleLerp(a, b, t) {
  let d = ((b - a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  return a + d * t;
}

// ---------------------------------------------------------------------------
// Figuren
// ---------------------------------------------------------------------------

const templates = {};
const toonMaterials = new Map(); // Original-Material -> Toon-Material

// Drei harte Helligkeitsstufen für den Cel-Shading-Look
const toonGradient = new THREE.DataTexture(new Uint8Array([90, 170, 255]), 3, 1, THREE.RedFormat);
toonGradient.minFilter = toonGradient.magFilter = THREE.NearestFilter;
toonGradient.needsUpdate = true;

function makeToonMaterial(original) {
  return new THREE.MeshToonMaterial({
    map: original.map,
    color: original.color,
    gradientMap: toonGradient,
    side: original.side,
  });
}

// Umriss als "Inverted Hull": schwarze Rückseiten, im Kameraraum entlang der
// (gehäuteten) Normalen nach außen geschoben
const outlineMat = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide });
outlineMat.onBeforeCompile = (shader) => {
  shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', `
    #include <project_vertex>
    #ifdef USE_SKINNING
      vec3 outlineNormal = objectNormal;
    #else
      vec3 outlineNormal = normal;
    #endif
    mvPosition.xyz += normalize(normalMatrix * outlineNormal) * ${OUTLINE_WIDTH.toFixed(4)};
    gl_Position = projectionMatrix * mvPosition;
  `);
};

function addOutlines(model) {
  const meshes = [];
  model.traverse((o) => { if (o.isMesh) meshes.push(o); });
  for (const mesh of meshes) {
    const hull = mesh.isSkinnedMesh ? new THREE.SkinnedMesh(mesh.geometry, outlineMat) : new THREE.Mesh(mesh.geometry, outlineMat);
    if (mesh.isSkinnedMesh) {
      hull.bindMode = mesh.bindMode;
      hull.bind(mesh.skeleton, mesh.bindMatrix);
    }
    hull.userData.outline = true;
    hull.frustumCulled = false;
    mesh.add(hull);
  }
}

function applyPieceStyle(piece) {
  piece.model.traverse((o) => {
    if (!o.isMesh) return;
    if (o.userData.outline) { o.visible = settings.toon; return; }
    o.userData.original ??= o.material;
    o.material = settings.toon ? toonMaterials.get(o.userData.original) : o.userData.original;
    // Kein Eigenschatten im Toon-Modus: der Toon-Shader beleuchtet auch Rückseiten,
    // die Shadow Map erzeugt dort sonst harte Flecken
    o.receiveShadow = !settings.toon;
  });
}
let pieces = new Map(); // Feld -> Figur
const livePieces = new Set(); // alle Figuren in der Szene, auch gerade geschlagene

async function loadModels() {
  const loader = new GLTFLoader();
  const jobs = [];
  for (const color of ['w', 'b']) {
    for (const type of Object.keys(PIECE_FILE)) {
      const url = `/pieces/${PIECE_FILE[type]}_${COLOR_FILE[color]}.glb`;
      jobs.push(loader.loadAsync(url).then((gltf) => {
        gltf.scene.traverse((o) => {
          if (!o.isMesh) return;
          o.castShadow = true;
          o.receiveShadow = true;
          if (!toonMaterials.has(o.material)) toonMaterials.set(o.material, makeToonMaterial(o.material));
        });
        const box = new THREE.Box3().setFromObject(gltf.scene);
        templates[color + type] = { gltf, height: box.max.y - box.min.y };
      }));
    }
  }
  await Promise.all(jobs);
}

const hitMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false });

function createPiece(color, type, square) {
  const tpl = templates[color + type];
  const group = new THREE.Group();
  const model = SkeletonUtils.clone(tpl.gltf.scene);
  model.scale.setScalar(PIECE_SCALE);
  group.add(model);
  addOutlines(model);
  applyPieceStyle({ model });

  // Unsichtbarer Klick-Körper, damit man die ganze Figur anklicken kann
  const h = tpl.height * PIECE_SCALE;
  const hit = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.4, h, 12), hitMat);
  hit.position.y = h / 2;
  group.add(hit);

  group.position.copy(squareToPos(square));
  group.rotation.y = BASE_YAW[color];
  scene.add(group);

  const mixer = new THREE.AnimationMixer(model);
  const clip = (name) => tpl.gltf.animations.find((a) => a.name === name);
  const idle = mixer.clipAction(clip('Idle'));
  const walk = mixer.clipAction(clip('Walk'));
  idle.play();
  idle.time = Math.random() * clip('Idle').duration; // nicht alle im Gleichtakt

  const piece = { color, type, square, group, model, hit, mixer, idle, walk };
  hit.userData.piece = piece;
  livePieces.add(piece);
  return piece;
}

function removePiece(piece) {
  scene.remove(piece.group);
  livePieces.delete(piece);
  piece.mixer.stopAllAction();
  piece.hit.geometry.dispose();
}

function syncPieces() {
  for (const p of [...livePieces]) removePiece(p);
  pieces = new Map();
  for (const row of game.board()) {
    for (const sq of row) {
      if (sq) pieces.set(sq.square, createPiece(sq.color, sq.type, sq.square));
    }
  }
}

function startWalking(piece) {
  piece.walk.reset().setEffectiveWeight(1).play();
  piece.walk.crossFadeFrom(piece.idle, 0.2, false);
}

function stopWalking(piece) {
  piece.idle.reset().setEffectiveWeight(1).play();
  piece.idle.crossFadeFrom(piece.walk, 0.25, false);
}

async function turnTo(piece, yaw, duration = TURN_TIME) {
  const from = piece.group.rotation.y;
  await tween(duration, (t) => { piece.group.rotation.y = angleLerp(from, yaw, t); });
}

// Der Springer läuft zwischen den Figuren: zur Feldecke, an der Feldkante entlang, von der Ecke ins Ziel.
function movePath(type, from, to) {
  if (type !== 'n') return [from, to];
  const sx = Math.sign(to.x - from.x) * 0.5;
  const sz = Math.sign(to.z - from.z) * 0.5;
  return [from, new THREE.Vector3(from.x + sx, 0, from.z + sz), new THREE.Vector3(to.x - sx, 0, to.z - sz), to];
}

const pawnHops = (dist) => Math.max(1, Math.round(dist * PAWN_HOPS_PER_SQUARE));

// Dauer des Laufens ohne das Drehen am Anfang (für das Timing beim Schlagen)
function moveDuration(type, from, to) {
  if (type === 'p') return pawnHops(from.distanceTo(to)) * PAWN_HOP_TIME;
  const path = movePath(type, from, to);
  let t = 0;
  for (let i = 1; i < path.length; i++) {
    t += Math.max(path.length === 2 ? 0.5 : 0, path[i - 1].distanceTo(path[i]) / WALK_SPEED);
    if (i > 1) t += TURN_TIME;
  }
  return t;
}

async function hopPiece(piece, from, to) {
  await turnTo(piece, Math.atan2(to.x - from.x, to.z - from.z));
  const n = pawnHops(from.distanceTo(to));
  startWalking(piece); // Clip beginnt mit dem ersten Sprung
  piece.walk.setEffectiveTimeScale(piece.walk.getClip().duration / PAWN_HOP_TIME);
  await tween(n * PAWN_HOP_TIME, (t) => {
    const h = Math.min(t * n, n - 1e-6);
    const i = Math.floor(h);
    const u = Math.min(1, Math.max(0, (h - i - HOP_AIR[0]) / (HOP_AIR[1] - HOP_AIR[0])));
    piece.group.position.lerpVectors(from, to, (i + ease(u)) / n);
  }, (t) => t);
  stopWalking(piece);
}

async function walkPiece(piece, toSquare) {
  const from = piece.group.position.clone();
  const to = squareToPos(toSquare);
  if (from.distanceTo(to) < 1e-6) return;

  if (piece.type === 'p') {
    await hopPiece(piece, from, to);
  } else {
    startWalking(piece);
    const path = movePath(piece.type, from, to);
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1];
      const b = path[i];
      await turnTo(piece, Math.atan2(b.x - a.x, b.z - a.z));
      const duration = Math.max(path.length === 2 ? 0.5 : 0, a.distanceTo(b) / WALK_SPEED);
      await tween(duration, (t) => { piece.group.position.lerpVectors(a, b, t); });
    }
    stopWalking(piece);
  }
  await turnTo(piece, BASE_YAW[piece.color], 0.3);
}

async function capturePiece(piece) {
  // Eigene Materialien, damit das Ausblenden nicht alle gleichen Figuren betrifft
  const mats = [];
  piece.model.traverse((o) => {
    if (o.isMesh) {
      const mat = o.material.clone();
      mat.onBeforeCompile = o.material.onBeforeCompile; // clone() übernimmt das nicht
      mat.transparent = true;
      o.material = mat;
      mats.push(mat);
    }
  });
  const tilt = (Math.random() < 0.5 ? -1 : 1) * 1.3;
  await tween(0.7, (t) => {
    piece.model.rotation.z = tilt * t;
    piece.group.position.y = -0.5 * t * t;
    for (const m of mats) m.opacity = 1 - t;
  });
  removePiece(piece);
}

async function promotePiece(pawn, type) {
  const replacement = createPiece(pawn.color, type, pawn.square);
  replacement.group.scale.setScalar(0.001);
  await Promise.all([
    tween(0.35, (t) => pawn.group.scale.setScalar(Math.max(0.001, 1 - t))),
    tween(0.45, (t) => replacement.group.scale.setScalar(Math.max(0.001, t))),
  ]);
  removePiece(pawn);
  return replacement;
}

// Spielt einen (bereits in chess.js ausgeführten) Zug als Animation ab
async function animateMove(move) {
  const token = gameToken;
  const stale = () => token !== gameToken;
  const mover = pieces.get(move.from);
  pieces.delete(move.from);

  let victim = null;
  if (move.flags.includes('e')) {
    const victimSq = move.to[0] + move.from[1];
    victim = pieces.get(victimSq);
    pieces.delete(victimSq);
  } else if (move.captured) {
    victim = pieces.get(move.to);
    pieces.delete(move.to);
  }

  const jobs = [];
  const walking = walkPiece(mover, move.to);
  jobs.push(walking);

  if (victim) {
    // Die geschlagene Figur fällt um, kurz bevor der Angreifer ankommt
    const travel = moveDuration(move.piece, squareToPos(move.from), squareToPos(move.to));
    jobs.push(wait((TURN_TIME + travel * 0.6) * 1000).then(() => capturePiece(victim)));
  }

  if (move.flags.includes('k') || move.flags.includes('q')) {
    const rank = move.from[1];
    const [rookFrom, rookTo] = move.flags.includes('k') ? ['h' + rank, 'f' + rank] : ['a' + rank, 'd' + rank];
    const rook = pieces.get(rookFrom);
    pieces.delete(rookFrom);
    jobs.push(wait(250).then(() => walkPiece(rook, rookTo)).then(() => {
      if (stale()) return;
      rook.square = rookTo;
      pieces.set(rookTo, rook);
    }));
  }

  await Promise.all(jobs);
  if (stale()) return;
  mover.square = move.to;
  pieces.set(move.to, mover);

  if (move.promotion) {
    const promoted = await promotePiece(mover, move.promotion);
    if (stale()) removePiece(promoted); else pieces.set(move.to, promoted);
  }
}

// ---------------------------------------------------------------------------
// Spiellogik
// ---------------------------------------------------------------------------

const game = new Chess();
let playerColor = 'w';
let selected = null;
let busy = false;
let thinking = false;
let gameToken = 0;
let lastMove = null;
let flipped = false;

const worker = new Worker('/ai-worker.js', { type: 'module' });
let requestId = 0;
const pending = new Map();
worker.onmessage = (e) => {
  const cb = pending.get(e.data.id);
  pending.delete(e.data.id);
  cb?.(e.data.move);
};
function askEngine(fen, level) {
  return new Promise((resolve) => {
    const id = ++requestId;
    pending.set(id, resolve);
    worker.postMessage({ id, fen, level });
  });
}

function refreshMarks() {
  marks.clear();
  if (lastMove) {
    addMark(lastMove.from, 'last', 0.002);
    addMark(lastMove.to, 'last', 0.002);
  }
  if (game.inCheck()) {
    const king = game.findPiece({ type: 'k', color: game.turn() })[0];
    if (king) addMark(king, 'check', 0.004);
  }
  if (selected) {
    addMark(selected, 'selected', 0.005);
    for (const m of game.moves({ square: selected, verbose: true })) {
      addMark(m.to, m.captured ? 'ring' : 'dot', 0.006);
    }
  }
}

function resultText() {
  if (game.isCheckmate()) {
    return game.turn() === playerColor ? 'Schachmatt – der Computer gewinnt.' : 'Schachmatt – du gewinnst!';
  }
  if (game.isStalemate()) return 'Patt – Remis.';
  if (game.isThreefoldRepetition()) return 'Remis durch dreifache Wiederholung.';
  if (game.isInsufficientMaterial()) return 'Remis – zu wenig Material.';
  if (game.isDraw()) return 'Remis (50-Züge-Regel).';
  return null;
}

function updateUI() {
  const result = resultText();
  statusEl.classList.toggle('over', !!result);
  if (result) statusEl.textContent = result;
  else if (thinking) statusEl.textContent = 'Computer denkt nach …';
  else if (busy) statusEl.textContent = game.turn() === playerColor ? 'Computer zieht …' : 'Dein Zug läuft …';
  else if (game.turn() === playerColor) statusEl.textContent = game.inCheck() ? 'Schach! Du bist am Zug.' : 'Du bist am Zug.';
  else statusEl.textContent = 'Computer ist am Zug.';

  const history = game.history();
  movesEl.innerHTML = '';
  for (let i = 0; i < history.length; i += 2) {
    const li = document.createElement('li');
    li.innerHTML = `<span>${history[i]}</span>${history[i + 1] ? `<span>${history[i + 1]}</span>` : ''}`;
    movesEl.appendChild(li);
  }
  movesEl.scrollTop = movesEl.scrollHeight;
  undoBtn.disabled = busy || thinking || !game.history().some((_, i) => (i % 2 === 0) === (startTurn() === playerColor));
  refreshMarks();
}

function startTurn() {
  // Farbe am Zug in der Ausgangsstellung (nach game.load kann das Schwarz sein)
  const n = game.history().length;
  return n % 2 === 0 ? game.turn() : game.turn() === 'w' ? 'b' : 'w';
}

async function playMove(moveInput) {
  const token = gameToken;
  const move = game.move(moveInput);
  lastMove = move;
  selected = null;
  busy = true;
  updateUI();
  await animateMove(move);
  if (token !== gameToken) return;
  busy = false;
  updateUI();
  if (!game.isGameOver() && game.turn() !== playerColor) await computerTurn();
}

async function computerTurn() {
  const token = gameToken;
  thinking = true;
  updateUI();
  const started = performance.now();
  const move = await askEngine(game.fen(), Number(levelSel.value));
  const elapsed = performance.now() - started;
  if (elapsed < MIN_THINK_MS) await wait(MIN_THINK_MS - elapsed);
  if (token !== gameToken) return;
  thinking = false;
  if (move) await playMove(move);
  else updateUI();
}

function choosePromotion() {
  const dlg = $('promotion');
  dlg.hidden = false;
  return new Promise((resolve) => {
    const onClick = (e) => {
      const piece = e.target.closest('button')?.dataset.piece;
      if (!piece) return;
      dlg.hidden = true;
      dlg.removeEventListener('click', onClick);
      resolve(piece);
    };
    dlg.addEventListener('click', onClick);
  });
}

async function onSquareClicked(sq) {
  if (busy || thinking || game.isGameOver() || game.turn() !== playerColor || !sq) return;
  const piece = game.get(sq);

  if (selected) {
    const legal = game.moves({ square: selected, verbose: true }).filter((m) => m.to === sq);
    if (legal.length) {
      let promotion;
      if (legal.some((m) => m.promotion)) {
        busy = true;
        promotion = await choosePromotion();
        busy = false;
      }
      await playMove({ from: selected, to: sq, promotion });
      return;
    }
  }
  selected = piece && piece.color === playerColor && sq !== selected ? sq : null;
  refreshMarks();
}

// Startansicht: fester Blickwinkel, Abstand so gewählt, dass die 64 Felder (ohne Rand)
// das Bild maximal ausfüllen. Die perspektivische Asymmetrie (hintere Reihe erscheint
// kleiner) wird per vertikalem Lens-Shift ausgeglichen, damit oben kein Platz verloren geht.
const HOME_ELEVATION = Math.atan2(10.5, 9.5);
const HOME_MARGIN = 0.96; // Anteil des Bildes, den das Brett höchstens einnimmt
const HOME_TOP_HEIGHT = 1.1; // > 0 hält auch Figuren dieser Höhe auf der hinteren Reihe im Bild
const fitCam = new THREE.PerspectiveCamera();
const boardCorners = [[-4, -4, HOME_TOP_HEIGHT], [4, -4, HOME_TOP_HEIGHT], [-4, 4, 0], [4, 4, 0]]
  .map(([x, z, y]) => new THREE.Vector3(x, y, z));
let homeFit = { dist: 14, shift: 0 };
let atHome = true;

function projectBoard(dist) {
  fitCam.position.set(0, Math.sin(HOME_ELEVATION) * dist, Math.cos(HOME_ELEVATION) * dist);
  fitCam.lookAt(0, 0, 0);
  fitCam.updateMatrixWorld();
  let xMax = 0, yMin = Infinity, yMax = -Infinity;
  for (const c of boardCorners) {
    const v = c.clone().project(fitCam);
    xMax = Math.max(xMax, Math.abs(v.x));
    yMin = Math.min(yMin, v.y);
    yMax = Math.max(yMax, v.y);
  }
  return { xMax, yMin, yMax };
}

function computeHomeFit() {
  fitCam.fov = camera.fov;
  fitCam.aspect = camera.aspect;
  fitCam.near = camera.near;
  fitCam.far = camera.far;
  fitCam.updateProjectionMatrix();
  const fits = (b) => b.xMax <= HOME_MARGIN && b.yMax - b.yMin <= 2 * HOME_MARGIN;
  let lo = 4, hi = 60;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (fits(projectBoard(mid))) hi = mid; else lo = mid;
  }
  const b = projectBoard(hi);
  // Oberkante des Bretts an die Oberkante des Bildes (mit gleichem Randanteil) schieben
  homeFit = { dist: hi, shift: HOME_MARGIN - b.yMax };
}

function applyLensShift(w, h) {
  // Positiver Offset verschiebt den Bildausschnitt nach unten, der Inhalt wandert nach oben
  camera.setViewOffset(w, h, 0, homeFit.shift * h / 2, w, h);
}

function cameraHome(animated = true) {
  const side = (playerColor === 'w') !== flipped ? 1 : -1;
  // Beschriftung zum Betrachter drehen
  for (const l of labels) l.rotation.z = side > 0 ? 0 : Math.PI;
  atHome = true;
  const d = homeFit.dist;
  const target = new THREE.Vector3(0, Math.sin(HOME_ELEVATION) * d, Math.cos(HOME_ELEVATION) * d * side);
  if (!animated) { camera.position.copy(target); return; }
  const from = camera.position.clone();
  const r0 = Math.hypot(from.x, from.z);
  const a0 = Math.atan2(from.x, from.z);
  const a1 = Math.atan2(target.x, target.z);
  const r1 = Math.hypot(target.x, target.z);
  tween(0.9, (t) => {
    const a = angleLerp(a0, a1, t);
    const r = r0 + (r1 - r0) * t;
    camera.position.set(Math.sin(a) * r, from.y + (target.y - from.y) * t, Math.cos(a) * r);
  });
}

function newGame(fen) {
  gameToken++;
  pending.clear();
  thinking = false;
  busy = false;
  selected = null;
  lastMove = null;
  flipped = false;
  playerColor = colorSel.value;
  if (fen) game.load(fen); else game.reset();
  for (const tw of tweens) tw.resolve();
  tweens.clear();
  syncPieces();
  cameraHome();
  updateUI();
  if (!game.isGameOver() && game.turn() !== playerColor) computerTurn();
}

function undo() {
  if (busy || thinking || !game.history().length) return;
  game.undo();
  while (game.history().length && game.turn() !== playerColor) game.undo();
  if (game.turn() !== playerColor) {
    // Stellung, in der der Computer anfängt – nicht weiter zurück
    const moves = game.history({ verbose: true });
    lastMove = moves[moves.length - 1] || null;
    syncPieces();
    updateUI();
    computerTurn();
    return;
  }
  const moves = game.history({ verbose: true });
  lastMove = moves[moves.length - 1] || null;
  selected = null;
  syncPieces();
  updateUI();
}

// ---------------------------------------------------------------------------
// Eingabe
// ---------------------------------------------------------------------------

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let downAt = null;

function squareAtEvent(e) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects([...pieces.values()].map((p) => p.hit), false);
  const point = raycaster.ray.intersectPlane(ground, new THREE.Vector3());
  const groundSq = point ? posToSquare(point.x, point.z) : null;
  const pieceSq = hits.length ? hits[0].object.userData.piece.square : null;
  // Liegt ein mögliches Zielfeld hinter einer Figur, gewinnt das Zielfeld
  if (selected && groundSq && groundSq !== pieceSq) {
    const targets = game.moves({ square: selected, verbose: true }).map((m) => m.to);
    if (targets.includes(groundSq) && !targets.includes(pieceSq)) return groundSq;
  }
  return pieceSq || groundSq;
}

renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downAt) return;
  const moved = Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]);
  downAt = null;
  if (moved < 6) onSquareClicked(squareAtEvent(e));
});

$('newGame').addEventListener('click', () => newGame());
undoBtn.addEventListener('click', undo);
$('flip').addEventListener('click', () => { flipped = !flipped; cameraHome(); });
colorSel.addEventListener('change', () => newGame());

const settingsDlg = $('settings');
$('settingsBtn').addEventListener('click', () => { settingsDlg.hidden = false; });
$('settingsClose').addEventListener('click', () => { settingsDlg.hidden = true; });
settingsDlg.addEventListener('click', (e) => { if (e.target === settingsDlg) settingsDlg.hidden = true; });
const infoDlg = $('info');
$('infoBtn').addEventListener('click', () => { infoDlg.hidden = false; });
$('infoClose').addEventListener('click', () => { infoDlg.hidden = true; });
infoDlg.addEventListener('click', (e) => { if (e.target === infoDlg) infoDlg.hidden = true; });
// Lizenztexte erst beim Aufklappen laden
for (const d of infoDlg.querySelectorAll('details[data-license]')) {
  d.addEventListener('toggle', async () => {
    const pre = d.querySelector('pre');
    if (!d.open || pre.textContent) return;
    try {
      pre.textContent = await (await fetch(d.dataset.license)).text();
    } catch {
      pre.textContent = 'Lizenztext konnte nicht geladen werden.';
    }
  });
}
toonBox.checked = settings.toon;
toonBox.addEventListener('change', () => {
  settings.toon = toonBox.checked;
  saveSettings();
  for (const p of livePieces) applyPieceStyle(p);
});
renderInfoBox.checked = settings.renderInfo;
statsEl.hidden = !settings.renderInfo;
renderInfoBox.addEventListener('change', () => {
  settings.renderInfo = renderInfoBox.checked;
  saveSettings();
  statsEl.hidden = !settings.renderInfo;
});

// ---------------------------------------------------------------------------
// Render-Schleife
// ---------------------------------------------------------------------------

function resize() {
  const w = container.clientWidth;
  const h = container.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  computeHomeFit();
  applyLensShift(w, h);
  if (atHome) cameraHome(false);
}
controls.addEventListener('start', () => { atHome = false; });
window.addEventListener('resize', resize);
resize();

// FPS werden über ein halbsekündiges Fenster gemittelt
let fps = 0;
let fpsFrames = 0;
let fpsStart = performance.now();
function updateStats() {
  fpsFrames++;
  const now = performance.now();
  if (now - fpsStart < 500) return;
  fps = fpsFrames * 1000 / (now - fpsStart);
  fpsFrames = 0;
  fpsStart = now;
  if (settings.renderInfo) statsEl.textContent = `${fps.toFixed(0)} FPS`;
}

const timer = new THREE.Timer();
renderer.setAnimationLoop(() => {
  timer.update();
  const dt = Math.min(timer.getDelta(), 0.1);
  updateTweens(dt);
  for (const p of livePieces) p.mixer.update(dt);
  controls.update();
  renderer.render(scene, camera);
  updateStats();
});

// ---------------------------------------------------------------------------
// Testschnittstelle (für Playwright)
// ---------------------------------------------------------------------------

window.chessApp = {
  fen: () => game.fen(),
  history: () => game.history(),
  isIdle: () => !busy && !thinking && tweens.size === 0,
  playerColor: () => playerColor,
  newGame: (fen) => newGame(fen),
  pieceAt: (sq) => {
    const p = pieces.get(sq);
    return p ? p.color + p.type : null;
  },
  pieceCount: () => pieces.size,
  toon: () => settings.toon,
  fps: () => fps,
  // Bildschirmkoordinaten (CSS-Pixel) eines Feldmittelpunkts, optional in einer Höhe darüber
  squareToScreen: (sq, height = 0) => {
    const v = squareToPos(sq).setY(height).project(camera);
    const rect = renderer.domElement.getBoundingClientRect();
    return { x: rect.left + (v.x + 1) / 2 * rect.width, y: rect.top + (1 - v.y) / 2 * rect.height };
  },
  // Feld, das ein Klick an dieser Bildschirmstelle treffen würde (gleiche Logik wie beim echten Klick)
  squareAtScreen: (x, y) => squareAtEvent({ clientX: x, clientY: y }),
};

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

await loadModels();
cameraHome(false);
newGame();
$('loading').classList.add('done');
document.body.dataset.ready = '1';
