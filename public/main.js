import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Chess } from 'chess.js';
import { loadModel, ModelFigure } from './models.js';

// ---------------------------------------------------------------------------
// Konstanten
// ---------------------------------------------------------------------------

const FILES = 'abcdefgh';
const PIECE_FILE = { p: 'bauer', n: 'springer', b: 'laeufer', r: 'turm', q: 'dame', k: 'koenig' };
const COLOR_FILE = { w: 'weiss', b: 'schwarz' };
// Die Modelle schauen in +Z. Weiß steht bei +Z und soll nach -Z (zu Schwarz) schauen.
const BASE_YAW = { w: Math.PI, b: 0 };
const MIN_THINK_MS = 450;
// Umrissdicke in Welteinheiten (1 = eine Feldbreite). Durch die Perspektive
// wird die Linie bei weiter entfernten Figuren automatisch dünner.
const OUTLINE_WIDTH = 0.022;
const SETTINGS_KEY = 'schach3d.settings';
const SET_KEY = 'schach3d.auswahl';
const LIGHT_KEY = 'schach3d.licht2';   // neuer Schlüssel: alte gespeicherte Werte überdecken die neuen Standards nicht
// Laufende Partie über den Neuladen beim Wechsel von Brett oder Figuren retten
const GAME_KEY = 'schach3d.partie';

// Brett und Figurensatz sind getrennt wählbar (beide nutzen 1 Feldbreite = 1 Einheit, Weiß vorn bei +Z).
// Auswahl im Panel, im Browser gespeichert; ?brett=… / ?figurensatz=… überschreiben sie (für Tests)
const BOARD_SETS = { schnitz: 'Schnitzbrett', tiere: 'Spielzeugbrett' };
const PIECE_SETS = { schnitz: 'Schnitzfiguren', staunton: 'Staunton', tiere: 'Tierfiguren', ritter: 'Ritter (im Aufbau)' };
const choice = { brett: 'schnitz', figuren: 'schnitz' };   // Standard beim ersten Start: Schnitzbrett und -figuren
try { Object.assign(choice, JSON.parse(localStorage.getItem(SET_KEY))); } catch { /* egal */ }
{
  const q = new URLSearchParams(location.search);
  if (q.get('brett')) choice.brett = q.get('brett');
  if (q.get('figurensatz')) choice.figuren = q.get('figurensatz');
}
if (!BOARD_SETS[choice.brett]) choice.brett = 'schnitz';
if (!PIECE_SETS[choice.figuren]) choice.figuren = 'schnitz';

// Helligkeit des Brettbilds: Faktor auf die Bildfarben (das Brett ist beleuchtet wie die Figuren)
const BOARD_LIGHT = 1.0;
// Brett-Textur (2048 px): Kantenlänge der Fläche in Feldbreiten und Mitte des 8x8-Feldes relativ zur Bildmitte, je
// Achse (x nach rechts, y nach unten im Bild = zur weißen Seite). Gemessen an den Feldgrenzen im Bild: 200,9 bzw.
// 200,1 px je Feld, Mitte bei (1016,8 | 1017,3) px; Abweichung der einzelnen Linien vom Raster höchstens ±4 px
const BOARD_PLANE = { x: 2048 / 200.9, y: 2048 / 200.1 };
const FIELD_OFFSET = { x: -0.0358, y: -0.0335 };
const BOARD_THICKNESS = 0.35;
// Höhe je Figurenart in Feldbreiten (wie bei echten Schachfiguren nach Rang gestaffelt)
// (Springer: aufrechter Pferdekrieger zwischen Bauer und Läufer; Turm: Rundturm auf Wagen, Deichsel bis zum Feldrand)
const PIECE_HEIGHT = { bauer: 1.35, laeufer: 1.7, dame: 1.8, koenig: 1.9, springer: 1.6, turm: 1.2 };
// Figurensätze: geriggte GLB-Modelle unter assets/sets/<satz>/<art>_<weiss|schwarz>.glb, Clips Idle und
// WalkInPlace bzw. Walk (auf der Stelle). Was sich je Satz unterscheidet, steht hier:
//   height:    Figurenhöhe je Art in Feldbreiten; sonst scale: Originalgröße × scale
//   top:       Höhe der größten Figur (Startansicht hält sie im Bild); sonst aus height bzw. 1,1
//   matt:      Metallanteile der Textur abschalten (image_to_3d legt oft welche hinein, Holz wirkt sonst bronzen)
//   walkSpeed: feste Laufgeschwindigkeit in Feldbreiten/s; sonst aus der Schrittlänge des Modells (stride)
//   materials: Material je Farbe wählbar (PIECE_MATERIALS, Einstellungen im Panel)
//   rigid:     starre Figuren ohne Animationen: gleiten mit Wippen (models.js rigidMotion)
//   jump:      je Art Sprung im Bogen dieser Höhe (Feldbreiten) statt Gehen, für starre Figuren
//   hop:       je Art Hüpfen statt Gehen (perSquare: Sprünge je Feld, time: s je Sprung, air: Abstoßen bis Landung
//              als Anteile des Clips; vorwärts nur in der Flugphase)
//   only:      Satz im Aufbau: nur diese Modelle (Datei ohne .glb -> Höhe in Feldbreiten), alle übrigen kommen als
//              Platzhalter aus dem Satz fallback (mit dessen Einstellungen)
const PIECE_SET_LOOK = {
  // Schnitzfiguren: Weiß Esche, Schwarz Nussbaum; Bewegungen aus tools/anim_figur.py, Turm aus tools/rig_turm.py
  schnitz: { height: PIECE_HEIGHT, matt: true },
  // Tierfiguren: Originalgröße × 1,05, Materialien unverändert, der Hasen-Bauer hüpft
  // Gedrechselte Staunton-Figuren (tools/staunton): Weiß Buchsbaum, Schwarz Ebenholz; Höhen aus den Modellen
  staunton: { scale: 1, top: 1.85, walkSpeed: 1.6, rigid: true, jump: { springer: 0.9 }, materials: true },
  tiere: { scale: 1.05, walkSpeed: 2.2, hop: { bauer: { perSquare: 2, time: 0.42, air: [0.3, 0.82] } } },
  // Ritter (tools/ritter): bisher Bauern (Speer und Schild; Höhe bis zur Speerspitze), Läufer (Kampfbischöfe mit
  // Hammer und Buch), Damen (Zepter, Reichsapfel) und Könige (Fahne, Schwert; Höhe bis zur Fahnenspitze, beim
  // schwarzen König weht die Fahne hoch über der Krone, die Krone sitzt bei beiden auf gleicher Höhe);
  // Weiß blau, Schwarz geschwärzter Stahl und Rot; der Rest sind Schnitzfiguren als Platzhalter
  ritter: { only: { bauer_weiss: 1.45, bauer_schwarz: 1.45, laeufer_weiss: 1.7, laeufer_schwarz: 1.7, dame_weiss: 1.8,
    dame_schwarz: 1.8, koenig_weiss: 2.05, koenig_schwarz: 2.5 }, fallback: 'schnitz',
    top: 2.6 },
};

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

const settings = { toon: false, renderInfo: false, ao: false, material: { w: 'holz', b: 'palisander' } };   // Staunton: Schwarz standardmäßig Palisander
try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY))); } catch { /* egal */ }

function saveSettings() {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch { /* egal */ }
}

// ---------------------------------------------------------------------------
// Szene und Licht
// ---------------------------------------------------------------------------

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;   // PCFSoftShadowMap gibt es in three.js 0.186 nicht mehr
// Neutral (Khronos PBR Neutral): fängt Spitzlichter ab (helles Holz brennt nicht weiß aus), erhält aber
// Farbton und Sättigung (AgX machte alles grau-blass). Das Brettbild ist ein fertiges Bild und wird davon
// ausgenommen (toneMapped = false)
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x3a2a20);
// Umgebung: ein selbst gerendertes Arbeitszimmer (tools/umgebung/raum.py, Cycles, HDR) beleuchtet alles von allen
// Seiten und gibt Metall, Lack und Glas etwas zu spiegeln; dazu eine Sonne für die Schatten. Bis das HDR geladen
// ist (und mit ?umgebung=studio) gilt der synthetische RoomEnvironment-Raum.
const ENV_HDR = 'assets/umgebung/raum.hdr';
const ENV_HDR_INTENSITY = 3.5;        // Helligkeit des HDR relativ zum Regler „Umgebung“ (an Holz, Silber und Gold, Weiß und Schwarz abgestimmt)
const ENV_ROTATION = -Math.PI / 2;    // Bildmitte des Rundum-Bilds (Blender -Y, weiße Seite) nach +Z
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 1.0;
pmrem.dispose();
const sun = new THREE.DirectionalLight(0xffffff, 1.0);
sun.position.set(-4, 10, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7, near: 1, far: 30 });
sun.shadow.bias = -0.0005;
scene.add(sun);
// Frontlicht aus Richtung der Kamera (wird bei jeder Kamerabewegung nachgeführt): hellt die Vorderseiten auf
const front = new THREE.DirectionalLight(0xfff4e8, 1.9);
const FRONT_OFFSET = new THREE.Vector3(1.5, 2, 0);   // im Kamerasystem: etwas rechts und oberhalb der Kamera
scene.add(front);
scene.add(front.target);

const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
// Umgebungsverdeckung (GTAO): Kehlen, Ringe, Falten und der Fuß am Brett werden dunkler, wie bei echtem Licht.
// Die Tonwertabbildung macht danach der OutputPass.
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const gtao = new GTAOPass(scene, camera, 512, 512);
// Standardmäßig aus: an Silhouetten (Figur vor Figur) erzeugt die Bildschirm-Verdeckung dunkle Säume, und mit der
// HDR-Umgebung bringt sie wenig. Wenn eingeschaltet: volle Auflösung, kleiner Radius, schwach gemischt (mildert die
// Säume; verglichen in konzepte/ao/)
const ao = { res: 1, radius: 0.18, thickness: 0.5, blend: 0.8 };   // res: Anteil der Bildauflösung
gtao.updateGtaoMaterial({ radius: ao.radius, distanceExponent: 1.5, thickness: ao.thickness, scale: 1.0, samples: 8 });
gtao.blendIntensity = ao.blend;
composer.addPass(gtao);
composer.addPass(new OutputPass());
const controls = new OrbitControls(camera, renderer.domElement);
controls.enablePan = false;
controls.enableDamping = true;
controls.minDistance = 3;
controls.maxDistance = 22;
controls.maxPolarAngle = 1.3;
controls.target.set(0, 0, 0);

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

// ---------------------------------------------------------------------------
// Bretter
// ---------------------------------------------------------------------------

const labels = [];   // Koordinaten am Rand (Spielzeugbrett), werden zum Betrachter gedreht
// Das Brettbild ist die Farbe eines beleuchteten Materials: es bekommt dasselbe Licht, dieselben Schatten und dieselbe
// Umgebungsverdeckung wie die Figuren (vorher unbeleuchtet, das passte nie zusammen)
// Wenig Glanz (specularIntensity): von oben gesehen spiegelt das Brett sonst die helle Decke mit der Pendelleuchte des
// Umgebungsraums als milchigen Schleier
const BOARD_SPECULAR = 0.25;
const boardMaterial = new THREE.MeshPhysicalMaterial({ color: new THREE.Color().setScalar(BOARD_LIGHT), roughness: 0.5,
  specularIntensity: BOARD_SPECULAR });

// Schnitzbrett: fertiges Bild (mit Rand und Koordinaten) auf einer beleuchteten Platte
function buildBoard(texture) {
  boardMaterial.map = texture;
  const centre = new THREE.Vector3(-FIELD_OFFSET.x, 0, -FIELD_OFFSET.y);   // Feldmitte im Ursprung
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const top = new THREE.Mesh(new THREE.PlaneGeometry(BOARD_PLANE.x, BOARD_PLANE.y), boardMaterial);
  top.rotation.x = -Math.PI / 2;   // Bild oben = Reihe 8 = hinten (-Z)
  top.position.copy(centre);
  top.receiveShadow = true;
  scene.add(top);
  const side = new THREE.Mesh(
    new THREE.BoxGeometry(BOARD_PLANE.x, BOARD_THICKNESS, BOARD_PLANE.y),
    new THREE.MeshPhysicalMaterial({ color: 0x4a2c1c, roughness: 0.7, specularIntensity: BOARD_SPECULAR }),
  );
  side.position.copy(centre).add(new THREE.Vector3(0, -BOARD_THICKNESS / 2 - 0.002, 0));
  scene.add(side);
  const table = new THREE.Mesh(
    new THREE.PlaneGeometry(80, 80),
    new THREE.MeshPhysicalMaterial({ color: 0x4a3022, roughness: 0.9, envMapIntensity: 0.3, specularIntensity: 0.1 }),
  );
  table.rotation.x = -Math.PI / 2;
  table.position.y = -BOARD_THICKNESS - 0.01;
  scene.add(table);
}

// Spielzeugbrett: Felder als flache Kästen (beleuchtet, mit Schatten), feine Fugen über der dunklen
// Grundplatte, Rahmen, Koordinaten am Rand
const toyBoardMats = [];
function buildToyBoard() {
  const mat = (color, roughness) => {
    const m = new THREE.MeshPhysicalMaterial({ color, roughness, specularIntensity: BOARD_SPECULAR });
    m.userData.baseColor = m.color.clone();
    toyBoardMats.push(m);
    return m;
  };
  const light = mat(0xe8d4ae, 0.55);
  const dark = mat(0x8f6340, 0.55);
  const geo = new THREE.BoxGeometry(0.985, 0.12, 0.985);
  for (let f = 0; f < 8; f++) {
    for (let r = 0; r < 8; r++) {
      const m = new THREE.Mesh(geo, (f + r) % 2 === 0 ? dark : light);
      m.position.set(f - 3.5, -0.06, 3.5 - r);
      m.receiveShadow = true;
      scene.add(m);
    }
  }
  const base = new THREE.Mesh(new THREE.BoxGeometry(8, 0.1, 8), mat(0x3a2618, 0.8));
  base.position.y = -0.07;
  scene.add(base);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(9.3, 0.3, 9.3), mat(0x4a2f1e, 0.45));
  frame.position.y = -0.17;
  frame.receiveShadow = true;
  scene.add(frame);
  const table = new THREE.Mesh(new THREE.CircleGeometry(30, 64), mat(0x7d808a, 0.9));
  table.rotation.x = -Math.PI / 2;
  table.position.y = -0.33;
  table.receiveShadow = true;
  scene.add(table);
  scene.background = new THREE.Color(0xa9abb2);
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
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.32, 0.32), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
    m.rotation.x = -Math.PI / 2;
    return m;
  };
  for (let i = 0; i < 8; i++) {
    for (const side of [-1, 1]) {
      const l = label(FILES[i]);
      l.position.set(i - 3.5, -0.015, side * 4.32);
      const n = label(String(i + 1));
      n.position.set(side * 4.32, -0.015, 3.5 - i);
      scene.add(l, n);
      labels.push(l, n);
    }
  }
}

const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

// Markierungen (Auswahl, mögliche Züge, letzter Zug, Schach); über der Schattenfläche des Schnitzbretts
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

function addMark(sq, kind, y) {
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
  const d = ((b - a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  return a + d * t;
}

// ---------------------------------------------------------------------------
// Helligkeit: Regler für Umgebung, Sonne, Front, Figuren und Brett (im Browser gespeichert)
// ---------------------------------------------------------------------------

// Getrennte Lichtgruppen, damit das Verhältnis (Kontrast zwischen beleuchteten und abgewandten Seiten)
// einstellbar ist: Umgebung (weich, von überall), Sonne (gerichtet, wirft Schatten), Front (aus
// Kamerarichtung, macht die Vorderseiten sichtbar, aber flach)
const GROUPS = {
  ambient: [[scene, scene.environmentIntensity, 'environmentIntensity']],
  sun: [[sun, sun.intensity]],
  front: [[front, front.intensity]],
};
// Weniger Umgebungslicht, mehr Sonne: plastisch für beide Farben (Weiß brennt nicht aus, Schwarz bekommt Glanzlichter);
// mit beleuchtetem Brett und Umgebungsverdeckung an Nahaufnahmen von Weiß und Schwarz aller Sätze abgestimmt
const light = { ambient: 0.45, sun: 1.5, front: 0, board: 1, white: 1, black: 1 };
try { Object.assign(light, JSON.parse(localStorage.getItem(LIGHT_KEY))); } catch { /* egal */ }
const SLIDERS = [['lightAmbient', 'ambient'], ['lightSun', 'sun'], ['lightFront', 'front'], ['lightBoard', 'board'], ['lightWhite', 'white'], ['lightBlack', 'black']];

// ---------------------------------------------------------------------------
// Figuren
// ---------------------------------------------------------------------------

const templates = {};   // Farbe + Art -> Modell aus loadModel
const toonMaterials = new Map(); // Original-Material -> Toon-Material

// Drei harte Helligkeitsstufen für den Cel-Shading-Look
const toonGradient = new THREE.DataTexture(new Uint8Array([90, 170, 255]), 3, 1, THREE.RedFormat);
toonGradient.minFilter = toonGradient.magFilter = THREE.NearestFilter;
toonGradient.needsUpdate = true;

function toonMaterial(original) {
  let m = toonMaterials.get(original);
  if (!m) {
    m = new THREE.MeshToonMaterial({ map: original.map, color: original.color, gradientMap: toonGradient, side: original.side });
    toonMaterials.set(original, m);
  }
  return m;
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

/** Ruft fn für jedes Figuren-Mesh (ohne Umriss) auf. */
function eachMesh(piece, fn) {
  piece.fig.root.traverse((o) => { if (o.isMesh && !o.userData.outline) fn(o); });
}

// Wählbare Materialien je Farbe (für Sätze mit materials: true). "holz" ist das gebackene Holz des Modells;
// die anderen Hölzer färben dessen Maserung um (Faktor auf die Texturfarbe), der Rest ersetzt das Material.
const PIECE_MATERIALS = {
  w: { holz: 'Buchsbaum', ahorn: 'Ahorn', elfenbein: 'Elfenbein', porzellan: 'Porzellan', silber: 'Silber', glas: 'Kristallglas' },
  b: { holz: 'Ebenholz', nussbaum: 'Nussbaum', palisander: 'Palisander', lack: 'Klavierlack', gold: 'Gold', rauchglas: 'Rauchglas' },
};
const materialCache = new Map();   // Basismaterial + Art -> Material

function makeMaterial(base, kind) {
  const tinted = (r, g, b, roughness) => {
    const m = base.clone();
    m.color.setRGB(r, g, b);
    if (roughness !== undefined) m.roughness = roughness;
    return m;
  };
  switch (kind) {
    // Hölzer aus der Maserung des Modells: Ahorn aus Buchsbaum aufgehellt, Nussbaum und Palisander aus Ebenholz
    case 'ahorn': return tinted(1.75, 1.7, 1.5, 0.4);
    case 'nussbaum': return tinted(5.5, 5.0, 4.6, 0.4);
    case 'palisander': return tinted(6.5, 4.0, 3.4, 0.32);
    case 'elfenbein': return new THREE.MeshPhysicalMaterial({ color: 0xb3a78f, roughness: 0.38, clearcoat: 0.4, clearcoatRoughness: 0.2 });
    case 'porzellan': return new THREE.MeshPhysicalMaterial({ color: 0xb4b0a8, roughness: 0.2, clearcoat: 1, clearcoatRoughness: 0.05 });
    case 'silber': return new THREE.MeshStandardMaterial({ color: 0xc9c9ce, metalness: 1, roughness: 0.22 });
    case 'gold': return new THREE.MeshStandardMaterial({ color: 0xdcae55, metalness: 1, roughness: 0.25 });
    case 'lack': return new THREE.MeshPhysicalMaterial({ color: 0x080808, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.03 });
    case 'glas': return new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0, roughness: 0.04, transmission: 1,
      thickness: 0.35, ior: 1.5, specularIntensity: 1 });
    case 'rauchglas': return new THREE.MeshPhysicalMaterial({ color: 0xb8b4b0, metalness: 0, roughness: 0.06, transmission: 1,
      thickness: 0.4, ior: 1.5, attenuationColor: new THREE.Color(0x6a5e56), attenuationDistance: 0.9 });
    default: return base;
  }
}

/** Setzt das gewählte Material der Farbe (nur Sätze mit materials: true). */
function applyPieceMaterial(piece) {
  if (!PIECE_SET_LOOK[choice.figuren].materials) return;
  const kind = settings.material?.[piece.color] ?? 'holz';
  eachMesh(piece, (o) => {
    o.userData.base ??= o.userData.original ?? o.material;
    const key = `${o.userData.base.uuid}/${kind}`;
    let m = materialCache.get(key);
    if (!m) {
      m = makeMaterial(o.userData.base, kind);
      if (m !== o.userData.base) m.userData = { baseColor: m.color.clone() };
      materialCache.set(key, m);
    }
    o.userData.original = m;
  });
  applyPieceStyle(piece);
  applyPieceLight(piece);
}

function applyPieceStyle(piece) {
  piece.fig.root.traverse((o) => { if (o.userData.outline) o.visible = settings.toon; });
  eachMesh(piece, (o) => {
    o.userData.original ??= o.material;
    o.material = settings.toon ? toonMaterial(o.userData.original) : o.userData.original;
  });
}

/** Helligkeitsregler je Seite: multipliziert die Materialfarbe (Textur bleibt, Licht/Schatten-Verhältnis auch). */
function applyPieceLight(piece) {
  const f = light[piece.color === 'w' ? 'white' : 'black'];
  eachMesh(piece, (o) => {
    const m = o.userData.original ?? o.material;
    // Ausgangsfarbe am Material merken: Figuren desselben Modells teilen sich ihr Material
    m.userData.baseColor ||= m.color.clone();
    m.color.copy(m.userData.baseColor).multiplyScalar(f);
    toonMaterials.get(m)?.color.copy(m.color);
  });
}

let pieces = new Map(); // Feld -> Figur
const livePieces = new Set(); // alle Figuren in der Szene, auch gerade geschlagene

/** Lädt die zwölf Figuren des gewählten Satzes und merkt sich je Modell Art, Gangart und Höhe. */
async function loadModels() {
  const jobs = [];
  for (const color of ['w', 'b']) {
    for (const type of Object.keys(PIECE_FILE)) {
      const name = PIECE_FILE[type];
      const file = `${name}_${COLOR_FILE[color]}`;
      let set = choice.figuren;
      let look = PIECE_SET_LOOK[set];
      const ownHeight = look.only?.[file];
      if (look.only && ownHeight === undefined) look = PIECE_SET_LOOK[set = look.fallback];
      jobs.push(loadModel(`assets/sets/${set}/${file}.glb`).then((m) => {
        if (look.matt) {
          m.scene.traverse((o) => {
            if (!o.isMesh) return;
            o.material.color.set(0xffffff);
            o.material.metalness = 0;   // Faktor 0 schaltet auch die Metall-Karte ab
          });
        }
        if (look.walkSpeed) m.walkSpeed = look.walkSpeed;
        if (look.hop?.[name]) m.hop = look.hop[name];
        if (look.rigid) m.rigid = true;
        if (look.jump?.[name]) m.jump = look.jump[name];
        m.pieceHeight = ownHeight ?? (look.height ? look.height[name] : m.height * look.scale);
        templates[color + type] = m;
      }));
    }
  }
  await Promise.all(jobs);
}


function createPiece(color, type, square) {
  const model = templates[color + type];
  // Material des Modells bleibt unverändert (pure); Weiß schaut nach hinten (-Z, zu Schwarz), Schwarz nach vorn
  const fig = new ModelFigure(model, model.pieceHeight, 0xffffff, BASE_YAW[color], 0, true);
  addOutlines(fig.root);

  fig.root.position.copy(squareToPos(square));
  scene.add(fig.root);

  const piece = { color, type, square, fig, group: fig.root };
  applyPieceStyle(piece);
  applyPieceMaterial(piece);
  applyPieceLight(piece);
  livePieces.add(piece);
  return piece;
}

function removePiece(piece) {
  scene.remove(piece.group);
  livePieces.delete(piece);
  piece.fig.mixer.stopAllAction();
  // ein unterbrochener Weg (neues Spiel mitten im Zug) gilt als beendet
  piece.fig.walk?.done();
  piece.fig.walk = null;
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

// Der Springer läuft zwischen den Figuren: zur Feldecke, an der Feldkante entlang, von der Ecke ins Ziel.
// Springende Springer (starre Sätze) nehmen den direkten Weg im Bogen.
function movePath(type, from, to, model) {
  if (type !== 'n' || model?.jump) return [to];
  const sx = Math.sign(to.x - from.x) * 0.5;
  const sz = Math.sign(to.z - from.z) * 0.5;
  return [new THREE.Vector3(from.x + sx, 0, from.z + sz), new THREE.Vector3(to.x - sx, 0, to.z - sz), to];
}

function walkPiece(piece, toSquare) {
  const from = piece.group.position.clone();
  const to = squareToPos(toSquare);
  if (from.distanceTo(to) < 1e-6) return Promise.resolve();
  return piece.fig.walkPath(movePath(piece.type, from, to, piece.fig.model));
}

async function capturePiece(piece) {
  // Eigene Materialien, damit das Ausblenden nicht alle gleichen Figuren betrifft
  const mats = [];
  piece.group.traverse((o) => { if (o.userData.outline) o.visible = false; });
  eachMesh(piece, (o) => {
    const mat = o.material.clone();
    mat.onBeforeCompile = o.material.onBeforeCompile; // clone() übernimmt das nicht
    mat.userData = {};
    mat.transparent = true;
    o.material = mat;
    o.userData.original = mat;
    mats.push(mat);
  });
  const tilt = (Math.random() < 0.5 ? -1 : 1) * 1.3;
  const y0 = piece.group.position.y;
  await tween(0.7, (t) => {
    piece.group.rotation.z = tilt * t;
    piece.group.position.y = y0 - 0.5 * t * t;
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
  const fromPos = squareToPos(move.from);
  const toPos = squareToPos(move.to);
  const travel = mover.fig.travelTime(movePath(move.piece, fromPos, toPos, mover.fig.model));
  jobs.push(walkPiece(mover, move.to));

  if (victim) {
    // Die geschlagene Figur fällt um, kurz bevor der Angreifer ankommt
    jobs.push(wait(travel * 0.6 * 1000).then(() => capturePiece(victim)));
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
    addMark(lastMove.from, 'last', 0.004);
    addMark(lastMove.to, 'last', 0.004);
  }
  if (game.inCheck()) {
    const king = game.findPiece({ type: 'k', color: game.turn() })[0];
    if (king) addMark(king, 'check', 0.006);
  }
  if (selected) {
    addMark(selected, 'selected', 0.007);
    for (const m of game.moves({ square: selected, verbose: true })) {
      addMark(m.to, m.captured ? 'ring' : 'dot', 0.008);
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
// > 0 hält auch Figuren dieser Höhe auf der hinteren Reihe im Bild (Schnitzfiguren: König 1,9 Feldbreiten)
const setLook = PIECE_SET_LOOK[choice.figuren];
const HOME_TOP_HEIGHT = setLook.top ?? (setLook.height ? Math.max(...Object.values(setLook.height)) + 0.1 : 1.1);
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

/** Neues Spiel aus der Grundstellung, einer FEN oder (nach dem Neuladen) einer gespeicherten Partie als PGN. */
function newGame(fen, restore) {
  gameToken++;
  pending.clear();
  thinking = false;
  busy = false;
  selected = null;
  lastMove = null;
  flipped = restore?.flipped ?? false;
  playerColor = colorSel.value;
  game.reset();
  if (restore?.pgn) {
    try { game.loadPgn(restore.pgn); } catch { game.reset(); }
    lastMove = game.history({ verbose: true }).at(-1) || null;
  } else if (fen) {
    game.load(fen);
  }
  for (const tw of tweens) tw.resolve();
  tweens.clear();
  syncPieces();
  cameraHome(!restore);
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

/** Feld unter dem Mauszeiger: nur die Brettebene zählt (die Figuren selbst fangen keine Klicks). */
function squareAtEvent(e) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const point = raycaster.ray.intersectPlane(ground, new THREE.Vector3());
  return point ? posToSquare(point.x, point.z) : null;
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
// Material je Farbe: nur für Sätze, die es erlauben (Staunton)
$('pieceMaterials').hidden = !PIECE_SET_LOOK[choice.figuren].materials;
for (const [id, color] of [['materialWhite', 'w'], ['materialBlack', 'b']]) {
  const sel = $(id);
  for (const [k, label] of Object.entries(PIECE_MATERIALS[color])) sel.add(new Option(label, k));
  sel.value = PIECE_MATERIALS[color][settings.material?.[color]] ? settings.material[color] : 'holz';
  sel.addEventListener('change', () => {
    settings.material = { ...settings.material, [color]: sel.value };
    saveSettings();
    for (const p of livePieces) if (p.color === color) applyPieceMaterial(p);
  });
}
const aoBox = $('ao');
aoBox.checked = settings.ao;
aoBox.addEventListener('change', () => {
  settings.ao = aoBox.checked;
  saveSettings();
});
renderInfoBox.checked = settings.renderInfo;
statsEl.hidden = !settings.renderInfo;
renderInfoBox.addEventListener('change', () => {
  settings.renderInfo = renderInfoBox.checked;
  saveSettings();
  statsEl.hidden = !settings.renderInfo;
});

function applyLight() {
  for (const [g, list] of Object.entries(GROUPS)) {
    for (const [obj, base, prop = 'intensity'] of list) obj[prop] = base * light[g];
  }
  boardMaterial.color.setScalar(BOARD_LIGHT * light.board);
  for (const m of toyBoardMats) m.color.copy(m.userData.baseColor).multiplyScalar(light.board);
  for (const p of livePieces) applyPieceLight(p);
  for (const [id, prop] of SLIDERS) $(id + 'Val').textContent = `${Math.round(light[prop] * 100)} %`;
  try { localStorage.setItem(LIGHT_KEY, JSON.stringify(light)); } catch { /* egal */ }
}
for (const [id, prop] of SLIDERS) {
  const el = $(id);
  el.value = light[prop];
  el.addEventListener('input', () => { light[prop] = Number(el.value); applyLight(); });
}

// Brett und Figurensatz: Wechsel lädt die Seite neu (nur die gewählten Modelle werden geladen); die laufende
// Partie wird vorher gespeichert und danach wiederhergestellt
for (const [id, sets, prop] of [['boardSet', BOARD_SETS, 'brett'], ['pieceSet', PIECE_SETS, 'figuren']]) {
  const sel = $(id);
  for (const [k, label] of Object.entries(sets)) sel.add(new Option(label, k));
  sel.value = choice[prop];
  sel.addEventListener('change', () => {
    choice[prop] = sel.value;
    try {
      localStorage.setItem(SET_KEY, JSON.stringify(choice));
      sessionStorage.setItem(GAME_KEY, JSON.stringify({ pgn: game.pgn(), color: playerColor, level: levelSel.value, flipped }));
    } catch { /* egal */ }
    // Testparameter (?brett, ?figurensatz) entfernen, sonst überschreiben sie die neue Auswahl
    const q = new URLSearchParams(location.search);
    q.delete('brett');
    q.delete('figurensatz');
    location.search = q.toString();
  });
}

// ---------------------------------------------------------------------------
// Render-Schleife
// ---------------------------------------------------------------------------

function resize() {
  const w = container.clientWidth;
  const h = container.clientHeight;
  renderer.setSize(w, h);
  composer.setSize(w, h);
  const pr = renderer.getPixelRatio();
  gtao.setSize(Math.round(w * pr * ao.res), Math.round(h * pr * ao.res));
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
  for (const p of livePieces) p.fig.update(dt);
  controls.update();
  // Frontlicht wandert mit der Kamera
  front.position.copy(FRONT_OFFSET).applyQuaternion(camera.quaternion).add(camera.position);
  front.target.position.copy(controls.target);
  if (settings.ao) composer.render(); else renderer.render(scene, camera);
  updateStats();
});

// ---------------------------------------------------------------------------
// Testschnittstelle (für Playwright)
// ---------------------------------------------------------------------------

window.chessApp = {
  fen: () => game.fen(),
  history: () => game.history(),
  isIdle: () => !busy && !thinking && tweens.size === 0 && [...livePieces].every((p) => !p.fig.walk),
  playerColor: () => playerColor,
  newGame: (fen, pgn) => newGame(fen, pgn ? { pgn } : undefined),
  pieceAt: (sq) => {
    const p = pieces.get(sq);
    return p ? p.color + p.type : null;
  },
  pieceCount: () => pieces.size,
  // laufende Animation der Figur, die auf dem Feld steht oder gerade dorthin unterwegs ist
  anim: (sq) => {
    const goal = (p) => p.fig.walk && posToSquare(p.fig.walk.segs.at(-1).to.x, p.fig.walk.segs.at(-1).to.z);
    return (pieces.get(sq) ?? [...livePieces].find((p) => goal(p) === sq))?.fig.anim ?? null;
  },
  sets: () => ({ ...choice }),
  // Umgebung justieren (Kalibrierung): Helligkeitsbasis und Drehung um die senkrechte Achse
  // alle 64 Felder schachbrettartig markieren (Prüfen, ob die Markierungen auf den Feldern des Brettbilds sitzen)
  markAll() { for (let i = 0; i < 64; i++) if ((i + (i >> 3)) % 2 === 0) addMark(FILES[i % 8] + ((i >> 3) + 1), 'last', 0.004); },
  // Umgebungsverdeckung justieren (Vergleich): res, radius, thickness, blend
  setAO(v) {
    Object.assign(ao, v);
    gtao.updateGtaoMaterial({ radius: ao.radius, thickness: ao.thickness });
    gtao.blendIntensity = ao.blend;
    resize();
  },
  setEnv(base, rot) { if (base !== undefined) GROUPS.ambient[0][1] = base; if (rot !== undefined) scene.environmentRotation.y = rot; applyLight(); },
  setLight(v) { Object.assign(light, v); for (const [id, p] of SLIDERS) $(id).value = light[p]; applyLight(); },
  toon: () => settings.toon,
  // Kamera auf eine feste Ansicht stellen (Bilder für die README)
  setView(pos, target) {
    atHome = false;
    camera.position.set(...pos);
    controls.target.set(...target);
    controls.update();
  },
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

/** Ersetzt die Studio-Umgebung durch das gerenderte Zimmer. */
async function loadEnvironment() {
  if (new URLSearchParams(location.search).get('umgebung') === 'studio') return;
  const tex = await new HDRLoader().loadAsync(ENV_HDR);
  const gen = new THREE.PMREMGenerator(renderer);
  scene.environment = gen.fromEquirectangular(tex).texture;
  tex.dispose();
  gen.dispose();
  scene.environmentRotation.y = ENV_ROTATION;
  GROUPS.ambient[0][1] = ENV_HDR_INTENSITY;
}

const [boardTex] = await Promise.all([
  choice.brett === 'schnitz' ? new THREE.TextureLoader().loadAsync('assets/board/brett_klassisch.png') : null,
  loadModels(),
  loadEnvironment(),
]);
if (choice.brett === 'tiere') buildToyBoard(); else buildBoard(boardTex);
// Nebel in Hintergrundfarbe: der Rand des Tisches verschwindet in der Ferne
scene.fog = new THREE.Fog(scene.background, 30, 60);
applyLight();

let restore = null;
try {
  restore = JSON.parse(sessionStorage.getItem(GAME_KEY));
  sessionStorage.removeItem(GAME_KEY);
} catch { /* egal */ }
if (restore) {
  colorSel.value = restore.color;
  levelSel.value = restore.level;
}
cameraHome(false);
newGame(undefined, restore);
$('loading').classList.add('done');
document.body.dataset.ready = '1';
