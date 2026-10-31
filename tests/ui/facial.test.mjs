import test from 'node:test';
import assert from 'node:assert/strict';
import {facialWeights} from '../../tools/npc_lab/web/facial.mjs';

test('native blink closes both eyes and releases them', () => {
  assert.ok(facialWeights(4.9).BlinkLeft > .99);
  assert.equal(facialWeights(4.9).BlinkLeft, facialWeights(4.9).BlinkRight);
  assert.equal(facialWeights(4).BlinkLeft, 0);
  assert.equal(facialWeights(5.1).BlinkLeft, 0);
});
test('speech movement follows playback and resets when paused or ended', () => {
  assert.ok(facialWeights(0, {speaking:true, speechTime:.1}).Aah > 0);
  assert.notEqual(facialWeights(0, {speaking:true,speechTime:.1}).Aah, facialWeights(0, {speaking:true,speechTime:.2}).Aah);
  assert.equal(facialWeights(0, {speaking:false,speechTime:5}).Aah, 0);
});
test('disable, hidden and reduced motion reset every native target', () => {
  for (const state of [{enabled:false}, {visible:false}, {reducedMotion:true}]) {
    assert.ok(Object.values(facialWeights(4.9, {...state,speaking:true,mood:'angry'})).every(value=>value===0));
  }
});
test('moods and invalid timing stay bounded', () => {
  assert.ok(facialWeights(0,{mood:'angry'}).MoodAnger > 0);
  assert.ok(facialWeights(0,{mood:'warm'}).MoodHappy > 0);
  assert.ok(facialWeights(0,{mood:'fearful'}).MoodFear > 0);
  for (const time of [NaN,Infinity,-1,0,100]) assert.ok(Object.values(facialWeights(time)).every(value=>Number.isFinite(value)&&value>=0&&value<=1));
});
