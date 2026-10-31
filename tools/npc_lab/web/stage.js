// Optional local GLB presentation. This module never builds NPC context.
import * as THREE from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

export function createStage(host) {
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.append(renderer.domElement);
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(36, 1, 0.01, 100);
  scene.add(new THREE.HemisphereLight(0xe9e6d4, 0x38484a, 2.4));
  const key = new THREE.DirectionalLight(0xffe3b4, 3.5); key.position.set(2, 4, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0xb0d3d6, 2); rim.position.set(-3, 1, -2); scene.add(rim);
  const group = new THREE.Group(); scene.add(group);
  let model = null, mixer = null, controller = null, epoch = 0, last = 0, frame, drag = null, dirty = true;
  const clock = new THREE.Clock();
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
      const bounds = new THREE.Box3().setFromObject(model), size = bounds.getSize(new THREE.Vector3()), center = bounds.getCenter(new THREE.Vector3());
      const extent = Math.max(size.x, size.y, size.z);
      if (!Number.isFinite(extent) || extent <= 0) { dispose(model); model = null; throw new Error('empty_model'); }
      const scale = 2.8 / extent;
      model.scale.setScalar(scale); model.position.copy(center).multiplyScalar(-scale);
      group.add(model); group.rotation.y = Math.PI;
      camera.position.set(0, 0.2, 5.5); camera.lookAt(0, 0, 0);
      if (gltf.animations.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
        mixer = new THREE.AnimationMixer(model); mixer.clipAction(gltf.animations[0]).play(); clock.getDelta();
      }
      resize(); dirty = true; return true;
    },
    clear() {
      epoch++; controller?.abort(); mixer?.stopAllAction(); mixer = null;
      if (model) { group.remove(model); dispose(model); model = null; } dirty = true;
    },
    dispose() { this.clear(); observer.disconnect(); cancelAnimationFrame(frame); renderer.dispose(); renderer.domElement.remove(); }
  };
}
