import test from 'node:test';
import assert from 'node:assert/strict';
import { framing } from '../../tools/npc_lab/web/camera.mjs';

test('conversation frame brings the face closer than full figure', () => {
  assert.ok(framing('close').distance < framing('wide').distance);
  assert.ok(framing('close').y > framing('wide').y);
});
test('zoom moves closer within safe camera limits', () => {
  assert.ok(framing('close', 1.2).distance < framing('close', 1).distance);
  assert.equal(framing('close', 100).zoom, 1.55);
  assert.equal(framing('wide', -100).zoom, .65);
  assert.ok(framing('close', 100).distance > 1);
});
test('invalid camera state fails explicitly', () => {
  assert.throws(() => framing('unknown'), /invalid_camera_view/);
  for (const value of [NaN, Infinity, '1']) assert.throws(() => framing('close', value), /invalid_camera_zoom/);
});
