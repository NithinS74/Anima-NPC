// Optional local GLB presentation. This module never builds NPC context.
import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { framing } from './camera.mjs';
import { facialWeights } from './facial.mjs';

export function createStage(host) {
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.append(renderer.domElement);
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(36, 1, 0.01, 100);
  scene.add(new THREE.HemisphereLight(0xf2ede2, 0x352c26, 2.1));
  const key = new THREE.DirectionalLight(0xffe3b4, 3.5); key.position.set(2, 4, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0xc3cedb, 1.3); rim.position.set(-3, 1, -2); scene.add(rim);
  const group = new THREE.Group(); scene.add(group);
  let model = null, mixer = null, controller = null, epoch = 0, last = 0, frame, drag = null, dirty = true;
  const clock = new THREE.Clock();
  let view = 'close', zoom = 1;
  let faceMeshes = [], expressions = true, mood = 'neutral', speech = null;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  function applyFace(weights) {
    for (const mesh of faceMeshes) for (const [name, value] of Object.entries(weights)) {
      const index = mesh.morphTargetDictionary[name];
      if (index !== undefined && Math.abs(mesh.morphTargetInfluences[index] - value) > .0001) {
        mesh.morphTargetInfluences[index] = value; dirty = true;
      }
    }
  }
  function resetFace() { applyFace(facialWeights(0, {enabled:false})); }
  function onVisibility() { if (document.hidden) resetFace(); dirty = true; }
  document.addEventListener('visibilitychange', onVisibility);
  reducedMotion.addEventListener('change', resetFace);
  function positionCamera() {
    const pose = framing(view, zoom);
    camera.position.set(0, pose.y, pose.distance); camera.lookAt(0, pose.y, 0); dirty = true;
    return pose;
  }
  function dispose(object) {
    object?.traverse(child => {
      child.geometry?.dispose();
      for (const material of Array.isArray(child.material) ? child.material : [child.material]) {
        if (!material) continue;
        for (const value of Object.values(material)) if (value?.isTexture) { value.dispose(); value.image?.close?.(); }
        material.dispose();
      }
    });
  }
  function resize() {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix(); dirty = true;
  }
  const observer = new ResizeObserver(resize); observer.observe(host);
  function tick(now) {
    frame = requestAnimationFrame(tick);
    if (document.hidden || now - last < 1000 / 30) return;
    last = now;
    if (faceMeshes.length) applyFace(facialWeights(now / 1000, {enabled:expressions,
      reducedMotion:reducedMotion.matches, mood, speaking:!!speech && !speech.paused && !speech.ended,
      speechTime:speech?.currentTime || 0}));
    if (mixer) { mixer.update(Math.min(clock.getDelta(), 0.1)); dirty = true; }
    if (dirty) { renderer.render(scene, camera); dirty = false; }
  }
  frame = requestAnimationFrame(tick);
  renderer.domElement.addEventListener('pointerdown', event => { drag = event.clientX; renderer.domElement.setPointerCapture(event.pointerId); });
  renderer.domElement.addEventListener('pointermove', event => { if (drag !== null) { group.rotation.y += (event.clientX - drag) * 0.008; drag = event.clientX; dirty = true; } });
  renderer.domElement.addEventListener('pointerup', () => { drag = null; });
  renderer.domElement.addEventListener('pointercancel', () => { drag = null; });
  return {
    async load(url) {
      const generation = ++epoch; controller?.abort(); controller = new AbortController();
      resetFace(); faceMeshes = [];
      if (model) { mixer?.stopAllAction(); mixer = null; group.remove(model); dispose(model); model = null; }
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error('model_unavailable');
      const bytes = await response.arrayBuffer();
      if (bytes.byteLength > 32 * 1024 * 1024) throw new Error('model_size_limit');
      const manager = new THREE.LoadingManager();
      manager.setURLModifier(resource => { if (!resource.startsWith('blob:')) throw new Error('external_model_resource'); return resource; });
      const gltf = await new GLTFLoader(manager).parseAsync(bytes, '');
      if (generation !== epoch) { dispose(gltf.scene); return false; }
      let triangles = 0;
      gltf.scene.traverse(child => { if (child.isMesh) triangles += (child.geometry.index?.count || child.geometry.attributes.position?.count || 0) / 3; });
      if (triangles > 500000) { dispose(gltf.scene); throw new Error('model_geometry_limit'); }
      model = gltf.scene;
      faceMeshes = [];
      model.traverse(child => { if (child.isMesh && child.morphTargetDictionary && child.morphTargetInfluences)
        faceMeshes.push(child); });
      const bounds = new THREE.Box3().setFromObject(model), size = bounds.getSize(new THREE.Vector3()), center = bounds.getCenter(new THREE.Vector3());
      const extent = Math.max(size.x, size.y, size.z);
      if (!Number.isFinite(extent) || extent <= 0) { dispose(model); model = null; throw new Error('empty_model'); }
      const scale = 2.8 / extent;
      model.scale.setScalar(scale); model.position.copy(center).multiplyScalar(-scale);
      group.add(model); group.rotation.y = Math.PI;
      positionCamera();
      if (gltf.animations.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
        mixer = new THREE.AnimationMixer(model); mixer.clipAction(gltf.animations[0]).play(); clock.getDelta();
      }
      resize(); dirty = true; return true;
    },
    setView(nextView, nextZoom = zoom) {
      const pose = framing(nextView, nextZoom); view = pose.view; zoom = pose.zoom;
      return positionCamera();
    },
    hasExpressions() { return faceMeshes.some(mesh => 'BlinkLeft' in mesh.morphTargetDictionary); },
    expressionState() {
      const weights = {};
      for (const mesh of faceMeshes) for (const [name, index] of Object.entries(mesh.morphTargetDictionary))
        weights[name] = Math.max(weights[name] || 0, mesh.morphTargetInfluences[index]);
      return {enabled:expressions, parts:faceMeshes.length, mood, weights};
    },
    setExpressions(enabled) { expressions = !!enabled; if (!expressions) resetFace(); },
    setMood(value) { mood = value; },
    bindSpeech(element) { speech = element; },
    clear() {
      epoch++; controller?.abort(); mixer?.stopAllAction(); mixer = null; resetFace(); faceMeshes = []; mood = 'neutral';
      if (model) { group.remove(model); dispose(model); model = null; } dirty = true;
    },
    dispose() { this.clear(); observer.disconnect(); document.removeEventListener('visibilitychange', onVisibility);
      reducedMotion.removeEventListener('change', resetFace); cancelAnimationFrame(frame); renderer.dispose(); renderer.domElement.remove(); }
  };
}
