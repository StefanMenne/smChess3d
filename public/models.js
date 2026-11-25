// Echte 3D-Figuren (geriggte GLB mit eigenen Animationen): root, anim, walk, play(), walkTo(), walkPath(), update().
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const loader = new GLTFLoader();
const FADE = 0.3;   // s Überblendung zwischen Animationen
const MAX_WALK_TIME = 3;   // s: längere Wege (Dame, Läufer über das ganze Brett) mit schnelleren Schritten
const TURN_SPEED = 14;   // rad/s beim Drehen in Laufrichtung (halbe Drehung in gut 0,2 s)

/** Lädt ein Modell einmal; Figuren daraus teilen sich Geometrie und Textur. */
export async function loadModel(url) {
  const gltf = await loader.loadAsync(url);
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const height = box.max.y - box.min.y;
  // Schrittlänge (Hüftweg pro Gangzyklus): die Schnitzfiguren bringen sie als Eigenschaft "stride" (in Figurenhöhen)
  // am Skelett-Knoten mit (tools/anim_figur.py); sonst aus der Vorwärtsbewegung eines Clips "Walk" mit Root Motion
  let given = 0;
  gltf.scene.traverse((o) => { if (o.userData?.stride) given = o.userData.stride; });
  const walk = gltf.animations.find((c) => c.name === 'Walk');
  // Gangzyklus: der Clip, der beim Laufen gespielt wird (Tierfiguren haben nur "Walk", auf der Stelle)
  const gait = gltf.animations.find((c) => c.name === 'WalkInPlace') || walk;
  let stride = 0.5 * height;
  const hips = walk?.tracks.find((t) => /Hips\.position$/.test(t.name));
  if (given) {
    stride = given * height;
  } else if (hips) {
    const v = hips.values;
    const n = v.length / 3;
    stride = Math.hypot(v[(n - 1) * 3] - v[0], v[(n - 1) * 3 + 2] - v[2]);
  }
  return {
    scene: gltf.scene,
    clips: Object.fromEntries(gltf.animations.map((c) => [c.name, c])),
    height,
    // Fußpunkt: Mitte unten. Die geriggten Schnitzfiguren stehen schon bei 0; ungeriggte Modelle haben den Ursprung oft
    // in der Mitte und würden sonst zur Hälfte im Brett stecken
    foot: new THREE.Vector3((box.min.x + box.max.x) / 2, box.min.y, (box.min.z + box.max.z) / 2),
    stride,
    cycle: gait ? gait.duration : 1,
  };
}

export class ModelFigure {
  /**
   * @param model   Ergebnis von loadModel
   * @param height  Höhe der Figur in Feldbreiten
   * @param tint    Farbe, mit der die Textur multipliziert wird (Weiß: 0xffffff, Schwarz: dunkles Holz)
   * @param facing  Blickrichtung im Stand als Winkel um die senkrechte Achse (0 = zur Kamera, +Z)
   * @param sink    Anteil der Höhe, um den die Figur ins Brett eingesenkt wird
   * @param pure    Material des Modells unverändert lassen (keine Tönung, Metall/Rauheit wie geliefert)
   */
  constructor(model, height, tint, facing, sink = 0, pure = false) {
    this.pure = pure;
    this.model = model;
    this.height = height;
    this.root = new THREE.Group();
    const obj = SkeletonUtils.clone(model.scene);
    const s = height / model.height;
    obj.scale.setScalar(s);
    this.scale = s;
    obj.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.frustumCulled = false;   // Skinning verschiebt die Geometrie; Kasten der Ruhepose wäre falsch
        if (pure) return;
        o.material = o.material.clone();
        o.material.color.set(tint);
        // geschnitztes Holz/Elfenbein: kein Metall (image_to_3d liefert oft Metallanteile -> Kupferglanz), seidenmatt
        o.material.metalness = 0;
        o.material.metalnessMap = null;
        o.material.roughness = 0.75;
        o.material.roughnessMap = null;
        o.material.envMapIntensity = 0.6;
      }
    });
    // sink: Anteil der Höhe, den die Figur ins Brett einsinkt (versteckt z. B. Schuhe unter einem langen Gewand)
    obj.position.copy(model.foot).multiplyScalar(-s);
    obj.position.y -= sink * height;
    this.root.add(obj);
    this.obj = obj;
    this.objY = obj.position.y;
    this.homeFacing = facing;
    this.root.rotation.y = facing;
    this.mixer = new THREE.AnimationMixer(obj);
    this.actions = {};
    this.anim = null;
    this.walk = null;
    this.speedScale = 1;
    this.play('Idle', { randomStart: true });
  }

  /** Spielt einen Clip und blendet weich vom vorigen über. Kurznamen 'idle' und 'walk' gehen auch. */
  play(name, { randomStart = false, speed = 1, fade = FADE } = {}) {
    let clipName = { idle: 'Idle', walk: 'WalkInPlace' }[name] || name;
    if (!this.model.clips[clipName] && clipName === 'WalkInPlace') clipName = 'Walk';   // Pferd: Gang auf der Stelle heißt Walk
    const clip = this.model.clips[clipName];
    if (!clip || this.anim === clipName) return;
    const next = this.actions[clipName] ||= this.mixer.clipAction(clip);
    next.reset();
    next.timeScale = speed;
    if (randomStart) next.time = Math.random() * clip.duration;
    next.play();
    const prev = this.anim && this.actions[this.anim];
    if (prev) next.crossFadeFrom(prev, fade, false);
    this.anim = clipName;
  }

  /** Läuft geradeaus zum Ziel. */
  walkTo(target) {
    return this.walkPath([target]);
  }

  /** Abschnitte des Weges ab der aktuellen Position, je mit Dauer (Hüpfen: ein Abschnitt aus ganzen Sprüngen). */
  segments(points) {
    const pts = [this.root.position.clone(), ...points.map((p) => p.clone())];
    const hop = this.model.hop;
    if (hop) {
      const from = pts[0];
      const to = pts[pts.length - 1];
      const hops = Math.max(1, Math.round(from.distanceTo(to) * hop.perSquare));
      return { segs: [{ from, to, duration: hops * hop.time }], hops };
    }
    // Feldbreiten pro Sekunde: aus der Schrittlänge des Walk-Clips, oder fest vorgegeben (Tierfiguren laufen auf der Stelle)
    const speed = this.model.walkSpeed ?? this.model.stride * this.scale / this.model.cycle;
    const segs = [];
    for (let i = 1; i < pts.length; i++) {
      const len = pts[i - 1].distanceTo(pts[i]);
      if (len > 1e-6) segs.push({ from: pts[i - 1], to: pts[i], duration: len / speed });
    }
    // Zu lange Wege: Gang im selben Verhältnis schneller abspielen, die Füße bleiben am Boden
    const total = segs.reduce((t, s) => t + s.duration, 0);
    const pace = Math.max(1, total / MAX_WALK_TIME);
    for (const s of segs) s.duration /= pace;
    return { segs, hops: 0, pace };
  }

  /** Dauer des Weges in Sekunden (für das Timing beim Schlagen). */
  travelTime(points) {
    return this.segments(points).segs.reduce((t, s) => t + s.duration, 0);
  }

  /** Läuft die Punkte nacheinander ab; dreht sich unterwegs weich in Laufrichtung und am Ende zurück. */
  walkPath(points) {
    return new Promise((done) => {
      const { segs, hops, pace } = this.segments(points);
      if (!segs.length) { done(); return; }
      this.walk = { segs, i: 0, t: 0, hops, done };
      if (hops) {
        // Hüpfen: ganze Sprünge, der Clip wird auf die Sprungdauer gestreckt und beginnt mit dem ersten Absprung
        this.play('walk', { speed: this.model.cycle / this.model.hop.time, fade: 0.05 });   // kurz überblenden, sonst fehlt der erste Sprung
      } else {
        this.play('walk');
        if (this.actions[this.anim]) this.actions[this.anim].timeScale = pace;
      }
    });
  }

  update(dt) {
    this.mixer.update(dt);
    const w = this.walk;
    // Blickrichtung: unterwegs in Laufrichtung, sonst die Grundrichtung; weich nachgeführt
    let yaw = this.homeFacing;
    if (w) {
      const s = w.segs[w.i];
      yaw = Math.atan2(s.to.x - s.from.x, s.to.z - s.from.z);
    }
    const diff = ((yaw - this.root.rotation.y + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
    const step = TURN_SPEED * dt;
    this.root.rotation.y += Math.abs(diff) <= step ? diff : Math.sign(diff) * step;
    if (!w) return;
    w.t += dt;
    const seg = w.segs[w.i];
    let k = Math.min(w.t / seg.duration, 1);
    if (w.hops) {
      // Vorwärts nur zwischen Absprung und Landung jedes Sprungs, dazwischen steht der Hase
      const [up, down] = this.model.hop.air;
      const h = Math.min(k * w.hops, w.hops - 1e-6);
      const i = Math.floor(h);
      const u = Math.min(1, Math.max(0, (h - i - up) / (down - up)));
      const eased = u < 0.5 ? 2 * u * u : 1 - (-2 * u + 2) ** 2 / 2;
      k = k >= 1 ? 1 : (i + eased) / w.hops;
    }
    this.root.position.lerpVectors(seg.from, seg.to, k);
    if (this.model.rigid) this.rigidMotion(w, seg, k);
    if (k < 1) return;
    if (w.i < w.segs.length - 1) {
      w.t -= seg.duration;
      w.i++;
      return;
    }
    this.walk = null;
    if (this.model.rigid) this.rigidMotion(null);
    this.play('idle');
    w.done();
  }

  /**
   * Starre Figuren (ohne Skelett, z. B. gedrechselte): gleiten mit leichtem Wippen und neigen sich in
   * Laufrichtung; mit model.jump springen sie in einem Bogen dieser Höhe (Feldbreiten) über die anderen.
   */
  rigidMotion(w, seg, k) {
    const obj = this.obj;
    if (!w) {
      obj.position.y = this.objY;
      obj.rotation.x = 0;
      return;
    }
    const total = w.segs.reduce((t, s) => t + s.duration, 0);
    const done = (w.segs.slice(0, w.i).reduce((t, s) => t + s.duration, 0) + k * seg.duration) / total;
    if (this.model.jump) {
      obj.position.y = this.objY + this.model.jump * 4 * done * (1 - done);
      obj.rotation.x = 0.25 * (1 - 2 * done);   // Absprung nach vorn geneigt, Landung nach hinten
      return;
    }
    // kleine Schritte: zwei Wipper je Feldbreite, Neigung nach vorn, am Anfang und Ende weich
    const dist = done * w.segs.reduce((t, s) => t + s.from.distanceTo(s.to), 0);
    const ramp = Math.min(1, done * 6, (1 - done) * 6);
    obj.position.y = this.objY + 0.035 * Math.abs(Math.sin(dist * Math.PI * 2));
    obj.rotation.x = 0.07 * ramp;
  }
}
