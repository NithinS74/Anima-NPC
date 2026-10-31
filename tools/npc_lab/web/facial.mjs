// Native game morph shapes, app-driven timing. This is not phoneme lip sync.
export const nativeMorphNames = ['BlinkLeft', 'BlinkRight', 'Aah', 'Oh', 'BMP', 'MoodHappy', 'MoodAnger', 'MoodFear'];

export function facialWeights(time, { enabled = true, visible = true, reducedMotion = false,
  speaking = false, speechTime = 0, mood = 'neutral' } = {}) {
  const weights = Object.fromEntries(nativeMorphNames.map(name => [name, 0]));
  if (!enabled || !visible || reducedMotion) return weights;
  const seconds = Number.isFinite(time) ? Math.max(0, time) : 0;
  const phase = seconds % 5.2;
  const blink = Math.max(0, 1 - Math.abs(phase - 4.9) / .13);
  weights.BlinkLeft = blink; weights.BlinkRight = blink;
  if (speaking && Number.isFinite(speechTime)) {
    const t = Math.max(0, speechTime);
    weights.Aah = .10 + .28 * (.5 + .5 * Math.sin(t * 19));
    weights.Oh = .12 * (.5 + .5 * Math.sin(t * 11));
    weights.BMP = .08 * (.5 + .5 * Math.sin(t * 27));
  }
  if (['warm', 'happy', 'calm'].includes(mood)) weights.MoodHappy = .2;
  if (['angry', 'hostile'].includes(mood)) weights.MoodAnger = .28;
  if (['fearful', 'afraid'].includes(mood)) weights.MoodFear = .25;
  return weights;
}
