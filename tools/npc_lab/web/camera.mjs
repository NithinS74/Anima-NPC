// Pure framing rules, shared by controls and the WebGL stage.
export function framing(view = 'close', zoom = 1) {
  if (!['close', 'wide'].includes(view)) throw new Error('invalid_camera_view');
  if (!Number.isFinite(zoom)) throw new Error('invalid_camera_zoom');
  const bounded = Math.max(0.65, Math.min(1.55, zoom));
  return { view, zoom: bounded, y: view === 'close' ? 0.92 : 0.05,
    distance: (view === 'close' ? 2.65 : 5.3) / bounded };
}
