import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Atom = { element: string; x: number; y: number; z: number };
type Bond = { from: number; to: number; order: number };
type Preview = { atoms: Atom[]; bonds: Bond[]; formula: string; is_experimental_bound_pose: boolean; used_for_affinity_prediction: boolean };
type State = "empty" | "loading" | "ready" | "error";

const COLORS: Record<string, number> = {
  C: 0xc6d0e7, N: 0x7ea7ff, O: 0xff7883, S: 0xf8d06a, P: 0xffb677,
  F: 0x8ef6c7, Cl: 0x7ce09b, Br: 0xbd855b, I: 0xc6a0f8,
};
const RADII: Record<string, number> = { C: .27, N: .29, O: .30, S: .37, P: .36 };

export default function MoleculeViewer({ smiles }: { smiles: string }) {
  const stage = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<{ zoom: (v: number) => void; reset: () => void; toggle: () => void } | null>(null);
  const [geometry, setGeometry] = useState<Preview | null>(null);
  const [state, setState] = useState<State>("empty");
  const [error, setError] = useState("");
  const [rotation, setRotation] = useState(true);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    if (!smiles.trim()) {
      setState("empty"); setGeometry(null); return;
    }
    setState("loading"); setGeometry(null);
    const timer = window.setTimeout(async () => {
      try {
        const r = await fetch("/api/viewer/geometry", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ smiles: smiles.trim() }),
          signal: controller.signal,
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || "Could not render this molecule.");
        if (!Array.isArray(data.atoms) || !Array.isArray(data.bonds)
            || data.is_experimental_bound_pose !== false || data.used_for_affinity_prediction !== false)
          throw new Error("Invalid molecular preview data.");
        if (active) { setGeometry(data); setState("ready"); setError(""); }
      } catch (e) {
        if (active && !controller.signal.aborted) { setState("error"); setError((e as Error).message); }
      }
    }, 430);
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [smiles]);

  useEffect(() => {
    const host = stage.current;
    if (!host || !geometry || state !== "ready") return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true }); }
    catch { setError("This browser needs WebGL for interactive 3D."); setState("error"); return; }
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    host.appendChild(renderer.domElement);
    renderer.domElement.setAttribute("aria-label", "Rotatable molecular structure");

    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xdce8ff, 0x29334a, 2.3));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(3, 8, 10); scene.add(light);
    const fill = new THREE.DirectionalLight(0x8fbbff, 1.4);
    fill.position.set(-4, -1, -6); scene.add(fill);
    const group = new THREE.Group();
    scene.add(group);
    const atomGeometry = new THREE.SphereGeometry(1, 20, 14);
    const bondGeometry = new THREE.CylinderGeometry(1, 1, 1, 9);
    const atomMaterials = new Map<string, THREE.MeshStandardMaterial>();
    const bondMaterial = new THREE.MeshStandardMaterial({ color: 0x95a5c4, roughness: .46 });
    const points = geometry.atoms.map(a => new THREE.Vector3(a.x, a.y, a.z));
    let radius = 1.5;
    for (let i = 0; i < geometry.atoms.length; i++) {
      const a = geometry.atoms[i];
      let material = atomMaterials.get(a.element);
      if (!material) {
        material = new THREE.MeshStandardMaterial({ color: COLORS[a.element] ?? 0xa4aacf, roughness: .38 });
        atomMaterials.set(a.element, material);
      }
      const mesh = new THREE.Mesh(atomGeometry, material);
      mesh.position.copy(points[i]);
      mesh.scale.setScalar(RADII[a.element] || .3);
      group.add(mesh);
      radius = Math.max(radius, points[i].length());
    }
    for (const bond of geometry.bonds) {
      const a = points[bond.from], b = points[bond.to];
      if (!a || !b) continue;
      const v = b.clone().sub(a);
      const length = v.length();
      if (length < .01) continue;
      const direction = v.clone().normalize();
      let tangent = new THREE.Vector3().crossVectors(direction, new THREE.Vector3(0, 0, 1));
      if (tangent.lengthSq() < .01) tangent = new THREE.Vector3().crossVectors(direction, new THREE.Vector3(0, 1, 0));
      tangent.normalize();
      const count = Math.max(1, Math.min(3, bond.order || 1));
      for (let n = 0; n < count; n++) {
        const mesh = new THREE.Mesh(bondGeometry, bondMaterial);
        mesh.scale.set(count > 1 ? .045 : .062, length, count > 1 ? .045 : .062);
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
        mesh.position.copy(a).add(b).multiplyScalar(.5)
          .addScaledVector(tangent, (n - (count - 1) / 2) * .16);
        group.add(mesh);
      }
    }

    const distance = Math.max(7, radius * 3.0);
    const home = new THREE.Vector3(0, 0, distance);
    const camera = new THREE.PerspectiveCamera(37, 1, .05, 300);
    camera.position.copy(home);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.enablePan = false;
    orbit.dampingFactor = .085;
    orbit.minDistance = Math.max(2, radius + 1);
    orbit.maxDistance = distance * 3;
    orbit.autoRotate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches && rotation;
    orbit.autoRotateSpeed = .9;
    controlsRef.current = {
      zoom: v => { camera.position.multiplyScalar(v); orbit.update(); },
      reset: () => { camera.position.copy(home); orbit.target.set(0, 0, 0); orbit.update(); },
      toggle: () => { orbit.autoRotate = !orbit.autoRotate; setRotation(orbit.autoRotate); },
    };
    const resize = () => {
      const w = Math.max(20, host.clientWidth), h = Math.max(20, host.clientHeight);
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    let frame = 0;
    const draw = () => { orbit.update(); renderer.render(scene, camera); frame = requestAnimationFrame(draw); };
    draw();
    return () => {
      cancelAnimationFrame(frame); observer.disconnect(); orbit.dispose();
      atomGeometry.dispose(); bondGeometry.dispose(); bondMaterial.dispose();
      for (const m of atomMaterials.values()) m.dispose();
      renderer.dispose(); renderer.domElement.remove(); controlsRef.current = null;
    };
    // Model geometry is sufficient to initialize the scene.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geometry, state]);

  return <section className="molecule-panel" aria-label="Molecular visualization">
    <header className="molecule-header">
      <div className="heading-pair"><span className="panel-num">02</span>
        <div><h2>Molecule visualization</h2><p>Interactive 3D ligand conformer from SMILES</p></div>
      </div>
      <span className="viewer-badge">{state === "ready" ? "● Interactive" : "Visual preview"}</span>
    </header>
    <div className="molecule-stage">
      <div className="molecule-canvas" ref={stage}/>
      {state === "ready" && geometry && <>
        <div className="molecule-detail">{geometry.formula} · {geometry.atoms.length} atoms</div>
        <div className="viewer-controls" role="toolbar" aria-label="Molecule view controls">
          <button type="button" title="Zoom in" aria-label="Zoom in" onClick={() => controlsRef.current?.zoom(.82)}>+</button>
          <button type="button" title="Zoom out" aria-label="Zoom out" onClick={() => controlsRef.current?.zoom(1.19)}>−</button>
          <button type="button" title={rotation ? "Pause rotation" : "Resume rotation"} aria-label={rotation ? "Pause rotation" : "Resume rotation"} onClick={() => controlsRef.current?.toggle()}>{rotation ? "Ⅱ" : "▶"}</button>
          <button type="button" title="Reset view" aria-label="Reset view" onClick={() => controlsRef.current?.reset()}>↺</button>
        </div>
      </>}
      {state !== "ready" && <div className="molecule-placeholder">
        <span className="empty-molecule" aria-hidden="true">⬡</span>
        <strong>{state === "empty" ? "Enter a SMILES to visualize" : state === "loading" ? "Generating molecular coordinates…" : "Preview unavailable"}</strong>
        <p>{state === "error" ? error : "Your compound's molecular structure appears here, and updates when SMILES changes."}</p>
      </div>}
    </div>
    <p className="viewer-note">Generated ligand shape only, not the protein-bound pose or the data used for affinity prediction. Drag to rotate; scroll to zoom.</p>
  </section>;
}
