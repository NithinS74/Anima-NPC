'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="lab-token"]').content;
const scores = ['favourability', 'trust', 'familiarity', 'fear', 'irritation'];
const presets = {
  stranger: [0, 0, 0, 0, 0], friend: [80, 80, 90, 0, 0],
  distrusted: [20, -60, 80, 0, 30], disliked: [-60, -60, 0, 0, 70]
};
let info, profile, pending = null, epoch = 0, records = [], settingsPending = false, visualContext = null;
let stage = null, stageEpoch = 0, audioURL = null, speechFetch = null;
let cameraView = "close", cameraZoom = 1;
function feedback(text) { $('feedback').textContent = text; }
function fallbackExplanation(code) {
  const explanations = {
    provider_timeout: 'The API exceeded the current deadline. Manual testing supports --development-timeout 60; realtime mode stays strict.',
    provider_auth: 'The API rejected access. Check the local key and its model permissions, then restart.',
    provider_rate_limited: 'The API is rate limited or out of quota. Check provider quota before retrying.',
    provider_unavailable: 'The provider returned a server error. Try again later.',
    provider_bad_request: 'The API rejected the request settings. Check model and provider compatibility.',
    provider_not_found: 'The configured model or endpoint was not found.',
    provider_transport: 'Could not reach the API. Check the network connection.',
    provider_output_limit: 'The model exhausted its output allowance before producing a reply. Disable reasoning for short NPC replies.',
    provider_protocol: 'The API returned an unexpected response instead of usable answer text.',
    irrelevant_boundary: 'The model answered an unrelated restriction instead of your current question; the reply was rejected.'
  };
  return `Outcome: ${code}. ${explanations[code] || 'Inspect validation and error details in the trace.'} A fallback is not successful generation.`;
}
function stopAudio() {
  speechFetch?.abort(); speechFetch = null;
  $('speech-player').pause(); $('speech-player').removeAttribute('src');
  if (audioURL) URL.revokeObjectURL(audioURL); audioURL = null;
  $('replay').disabled = true; $('audio-status').classList.remove('speaking');
}
async function showStage(next) {
  const generation = ++stageEpoch;
  stage?.clear(); $('expressions').disabled = true; $('model-host').hidden = true; $('portrait').hidden = false;
  $('visual-status').textContent = 'ILLUSTRATED CHARACTER'; $('model-hint').textContent = 'No local 3D model imported';
  if (!next.media?.model_url) return;
  try {
    if (!stage) { const module = await import('/stage.js'); if (generation !== stageEpoch) return; stage = module.createStage($('model-host')); }
    $('model-host').hidden = false; $('visual-status').textContent = 'LOADING LOCAL 3D';
    stage.setView(cameraView, cameraZoom);
    const loaded = await stage.load(next.media.model_url);
    if (generation !== stageEpoch || !loaded) return;
    $('portrait').hidden = true; $('visual-status').textContent = 'LOCAL 3D MODEL';
    stage.bindSpeech($('speech-player')); stage.setMood(next.mood);
    $('expressions').disabled = !stage.hasExpressions();
    stage.setExpressions($('expressions').checked);
    $('expressions').title = stage.hasExpressions() ? 'Native Skyrim blink, speech and mood morphs; approximate timing' : 'This model has no native facial morphs';
    $('model-hint').textContent = next.media.appearance_source || 'Drag to rotate · 30 FPS cap';
    $('model-hint').title = 'Actual game-derived appearance assembly · static pose · drag to rotate';
  } catch {
    if (generation !== stageEpoch) return;
    stage?.clear(); $('expressions').disabled = true; $('model-host').hidden = true; $('portrait').hidden = false;
    $('visual-status').textContent = 'PORTRAIT FALLBACK'; $('model-hint').textContent = 'Local model could not be rendered';
  }
}
function clearLog() {
  stage?.setMood('neutral');
  stopAudio(); $('stage-caption').textContent = 'Every stranger has a story.';
  $('llm-input').textContent = 'No model input recorded.'; $('prompt-note').textContent = 'No turn yet.';
  $('impact-map').replaceChildren(); $('impact-summary').textContent = 'Speak to a character to see what shaped their response.';
  $('audio-status').textContent = profile?.media?.voice_available ? 'Mantella Piper voice ready' : 'Voice not connected';
  epoch++; records = []; $('messages').replaceChildren();
  const empty = document.createElement('div'); empty.className = 'empty';
  const quote = document.createElement('span'), heading = document.createElement('h3'), hint = document.createElement('p');
  quote.textContent = '“'; heading.textContent = 'Give them a reason to respond.'; hint.textContent = 'Choose your words. Their response depends on who you are to them.';
  empty.append(quote, heading, hint); $('messages').append(empty);
  $('trace').textContent = 'No turn yet.';
  $('reaction').hidden = true;
  feedback(info?.persistent_state ? 'Your standing and past encounters are remembered.' : 'Each message is an independent test turn.');
}
function setBusy(busy) {
  $('send').disabled = busy;
  document.querySelectorAll('#roster button, .parameters input, .parameters select, .starters button').forEach(el => el.disabled = busy);
}
function bubble(speaker, text, type = '', metadata = '') {
  $('messages').querySelector('.empty')?.remove();
  const box = document.createElement('div'); box.className = 'bubble ' + type;
  const label = document.createElement('span'); label.className = 'speaker'; label.textContent = speaker;
  box.append(label, document.createTextNode(text));
  if (metadata) { const small = document.createElement('small'); small.textContent = metadata; box.append(small); }
  $('messages').append(box);
  while ($('messages').children.length > 60) $('messages').firstElementChild.remove();
  $('messages').scrollTop = $('messages').scrollHeight;
}
function relationship() { return Object.fromEntries(scores.map(name => [name, Number($(name).value)])); }
function updateScores(values) { scores.forEach((name, index) => { $(name).value = values[index]; $(name + '-value').textContent = values[index]; }); }
function applySavedState(state, changes = null) {
  Object.assign(profile, state); stage?.setMood(state.mood); updateScores(scores.map(name => state.relationship[name])); $('mood').value = state.mood;
  if (changes) scores.forEach(name => { const delta = changes.delta[name]; if (delta) $(name + '-value').textContent += ` (${delta > 0 ? '+' : ''}${delta})`; });
}
function restoreHistory(next) {
  if (!next.history?.length) return;
  for (const memory of next.history) {
    bubble('You · remembered', memory.player_text, 'player');
    bubble(next.persona.name, memory.npc_text || `[${memory.mode}]`, '', 'From an earlier encounter');
  }
}
async function persistConditions() {
  if (!info?.persistent_state) { clearLog(); return; }
  if (pending || settingsPending) return;
  stopAudio(); settingsPending = true; setBusy(true);
  try {
    const state = await post('/api/state', {persona_id: profile.id, relationship: relationship(), mood: $('mood').value, state_revision: profile.state_revision});
    applySavedState(state); feedback('Test override saved. Past conversation memory is retained.');
  } catch (error) { feedback(`Could not save conditions: ${error.message}. Reload to refresh saved state.`); }
  finally { settingsPending = false; setBusy(false); }
}
async function refreshSavedState() {
  if (!info?.persistent_state) return;
  const response = await fetch('/api/info'); if (!response.ok) throw new Error('state_unavailable');
  const latest = await response.json();
  for (const saved of latest.profiles) {
    const existing = info.profiles.find(item => item.id === saved.id);
    if (existing) Object.assign(existing, saved);
  }
  applySavedState(info.profiles.find(item => item.id === profile.id));
}
function selectProfile(next) {
  profile = next; clearLog();
  $('name').textContent = next.persona.name; $('occupation').textContent = next.persona.occupation.toUpperCase();
  document.querySelector('.stage-panel').dataset.scene = next.media?.scene || next.id;
  document.querySelector('.stage-panel').style.setProperty('--game-scene', `url("${next.media?.scene_url || '/scenes/' + next.id + '.svg'}")`);
  $('tagline').textContent = next.tagline; $('location').textContent = next.location;
  $('goal').textContent = next.current_goal; $('testing-notes').textContent = next.testing_notes;
  $('portrait').src = '/portraits/' + next.id + '.svg'; $('portrait').alt = 'Original illustrated portrait of ' + next.persona.name;
  $('stage-name').textContent = next.persona.name; $('stage-role').textContent = next.persona.occupation.toUpperCase();
  $('stage-state').textContent = 'Available';
  $('voice').disabled = !next.media?.voice_available; $('voice').checked = !!next.media?.voice_available;
  $('audio-status').textContent = next.media?.voice_available ? 'Voice ready' : 'Voice not installed';
  $('audio-status').title = next.media?.voice || 'No local voice asset';
  showStage(next);
  $('tags').replaceChildren(...next.persona.speech_style.map(text => { const el = document.createElement('span'); el.textContent = text; return el; }));
  $('boundaries').replaceChildren(...next.persona.boundaries.map(text => { const el = document.createElement('li'); el.textContent = text; return el; }));
  $('preset').value = 'default'; updateScores(scores.map(name => next.relationship[name]));
  $('mood').value = next.mood; $('state').value = 'available'; $('weapon').checked = false;
  $('state').querySelector('[value=closed]').disabled = !next.persona.service_role;
  document.querySelectorAll('.roster-item').forEach(el => { const selected = el.dataset.id === next.id; el.classList.toggle('selected', selected); el.setAttribute('aria-pressed', String(selected)); });
  $('starters').replaceChildren(...next.starters.map(text => {
    const button = document.createElement('button'); button.type = 'button'; button.textContent = text;
    button.addEventListener('click', () => { $('message').value = text; $('message').focus(); }); return button;
  }));
  restoreHistory(next);
}
async function post(path, body) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Lab-Token': token }, body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || 'request_failed');
  return result;
}
async function speak(id, turnEpoch) {
  speechFetch = new AbortController();
  $('audio-status').textContent = 'Synthesizing local voice…';
  try {
    const response = await fetch('/api/speech', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Lab-Token': token }, body: JSON.stringify({ request_id: id }), signal: speechFetch.signal });
    if (!response.ok) { const error = await response.json(); throw new Error(error.error || 'voice_failed'); }
    const raw = await response.blob();
    if (epoch !== turnEpoch || pending !== id || !$('voice').checked) return;
    const milliseconds = response.headers.get('X-Synthesis-Ms');
    audioURL = URL.createObjectURL(raw); $('speech-player').src = audioURL; $('replay').disabled = false;
    $('audio-status').textContent = `Voice ready · +${milliseconds} ms synthesis`;
    if (records.length) records[records.length - 1].audio_synthesis_ms = Number(milliseconds);
    try { await $('speech-player').play(); }
    catch { feedback('Voice is ready. Press ▷ to play it (browser autoplay was blocked).'); }
  } catch (error) {
    if (epoch === turnEpoch && error.name !== 'AbortError') $('audio-status').textContent = `Voice unavailable: ${error.message}`;
  } finally { speechFetch = null; }
}
$('chat').addEventListener('submit', async event => {
  event.preventDefault(); if (pending || settingsPending || !profile) return;
  const text = $('message').value.trim(); if (!text) return;
  const id = crypto.randomUUID(), turnEpoch = epoch, character = profile;
  stopAudio(); pending = id; setBusy(true); $('message').value = '';
  const request = { request_id: id, persona_id: character.id, text, relationship: relationship(), mood: $('mood').value, state: $('state').value, weapon_drawn: $('weapon').checked, state_revision: character.state_revision, visual_id: $('vision-attach').checked ? visualContext?.id || null : null };
  bubble('You', text, 'player');
  const waiting = document.createElement('div'); waiting.className = 'waiting'; waiting.textContent = 'Waiting for a validated response…'; $('messages').append(waiting);
  feedback(info.mode === 'live' ? 'Calling the configured API. No streaming text is displayed before validation.' : 'Using the deterministic fake — this is not an LLM-quality test.');
  try {
    const data = await post('/api/turn', request);
    if (epoch !== turnEpoch || pending !== id) return;
    const result = data.result, meta = result.status === 'error_fallback' ? 'Connection or response check failed; this is a fallback.' : '';
    if (data.saved_state) applySavedState(data.saved_state, data.social_change);
    bubble(character.persona.name, result.response?.text || (result.response?.mode === 'end' ? '[Ends the interaction]' : '[No speech]'), result.status === 'error_fallback' ? 'system' : '', meta);
    $('stage-caption').textContent = result.response?.text || (result.response?.mode === 'end' ? 'They end the conversation.' : 'They remain silent.');
    stage?.setMood(result.plan.affect);
    showInspection(data);
    $('stage-state').textContent = ({engage:'Listening',brief:'A few words, then',boundary:'A boundary drawn',disengage:'Conversation ended',withdraw:'Keeping their distance'})[data.context.social_appraisal.willingness] || 'Listening';
    const appraisal = data.context.social_appraisal;
    if (appraisal) {
      $('reaction').hidden = false;
      $('reaction-path').textContent = `${appraisal.stimulus.replaceAll('_', ' ')} → ${appraisal.willingness} → ${appraisal.tone} → ${result.plan.route}`;
      const deltas = data.social_change ? scores.filter(name => data.social_change.delta[name]).map(name => `${name} ${data.social_change.delta[name] > 0 ? '+' : ''}${data.social_change.delta[name]}`) : [];
      $('reaction-change').textContent = deltas.length ? deltas.join(' · ') : 'No score change; context still shapes the response.';
    }
    const conversation = data.context.conversation;
    $('trace').textContent = `Turn type: ${result.turn_type || 'n/a'} | Move: ${result.plan.move || 'none'} | Turns completed: ${conversation ? conversation.turns : 0} | Rapport: ${conversation ? conversation.rapport : 0}
` + JSON.stringify(data, null, 2);
    records.push({ request, ...data }); if (records.length > 30) records.shift();
    if (info.persistent_state && result.response) {
      try { const acknowledged = await post('/api/displayed', {persona_id: character.id, request_id: id}); if (epoch === turnEpoch) applySavedState(acknowledged, data.social_change); }
      catch { feedback('Reply displayed, but memory acknowledgement failed. Reload state before continuing.'); }
    }
      feedback(result.error_code ? fallbackExplanation(result.error_code) : (info.mode === 'live' ? 'The next words are yours.' : 'Offline preview: responses are scripted.'));
    waiting.remove();
    if ($('voice').checked && result.response?.mode === 'speech' && result.response.text) await speak(id, turnEpoch);
  } catch (error) {
    if (epoch === turnEpoch) { bubble('Anima', `Request failed: ${error.message}`, 'system'); feedback('Check the Anima launcher terminal and local provider settings.'); }
  } finally {
    waiting.remove(); if (pending === id) { pending = null; setBusy(false); }
  }
});
$('message').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('chat').requestSubmit(); } });
$('reset').addEventListener('click', async () => {
  const id = pending; clearLog();
  if (id) {
    try { await post('/api/cancel', { request_id: id }); await refreshSavedState(); feedback('Cancellation requested. Heard player input remains in saved social state.'); }
    catch { feedback('Could not confirm backend cancellation. Wait for the active request to finish.'); }
  }
});
$('preset').addEventListener('change', () => { updateScores($('preset').value === 'default' ? scores.map(name => profile.relationship[name]) : presets[$('preset').value]); persistConditions(); });
$('mood').addEventListener('change', persistConditions);
['state', 'weapon'].forEach(name => $(name).addEventListener('change', () => { stopAudio(); $('stage-state').textContent = $('state').selectedOptions[0].textContent; feedback('Situation changed; saved relationship and memory remain.'); }));
$('voice').addEventListener('change', () => { if (!$('voice').checked) { if (speechFetch && pending) post('/api/cancel', {request_id: pending}).catch(() => {}); stopAudio(); $('audio-status').textContent = 'Voice muted'; } });
$('replay').addEventListener('click', () => { $('speech-player').currentTime = 0; $('speech-player').play().catch(() => feedback('Browser audio playback is unavailable.')); });
$('speech-player').addEventListener('play', () => { $('audio-status').classList.add('speaking'); });
$('speech-player').addEventListener('ended', () => { $('audio-status').classList.remove('speaking'); });
window.addEventListener('pagehide', () => { stopAudio(); stage?.dispose(); });
$('export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify({ mode: info?.mode, persistent_state: info?.persistent_state, turns: records }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = 'anima-conversation.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
async function init() {
  scores.forEach(name => {
    const row = document.createElement('div'), label = document.createElement('label'), output = document.createElement('output'), slider = document.createElement('input');
    label.className = 'slider-label'; label.htmlFor = name; label.textContent = name[0].toUpperCase() + name.slice(1); output.id = name + '-value'; label.append(output);
    slider.type = 'range'; slider.id = name; slider.min = ['favourability', 'trust'].includes(name) ? -100 : 0; slider.max = 100; slider.value = 0;
    slider.addEventListener('input', () => { output.textContent = slider.value; }); slider.addEventListener('change', () => { $('preset').value = 'default'; persistConditions(); });
    row.append(label, slider); $('sliders').append(row);
  });
  try {
    const response = await fetch('/api/info'); if (!response.ok) throw new Error('unavailable'); info = await response.json();
    document.body.classList.toggle('skyrim-font', !!info.skyrim_fonts_available);
    $('font-status').textContent = info.skyrim_fonts_available ? 'Typography: actual Skyrim Futura dialogue/interface fonts, imported locally.' : 'Typography: open-font fallback (not the original Skyrim font).';
    $('mode').textContent = info.mode === 'live' ? 'CONNECTED · may incur charges' : 'OFFLINE PREVIEW · no model';
    $('timing').textContent = `${info.timing_profile.toUpperCase()} · ${info.deadline_ms / 1000}s deadline · ${info.input_budget_bytes} input bytes`;
    $('memory-notice').textContent = info.persistent_state ? 'Relationships persist · recent displayed replies become conversation memory.' : 'Single-turn test · this server has no persistent store.';
    $('vision-controls').hidden = !info.cv_enabled;
    document.querySelector('.stage-panel').classList.toggle('game-background', !!info.background_url);
    info.profiles.forEach(next => {
      const button = document.createElement('button'); button.className = 'roster-item'; button.dataset.id = next.id;
      const img = document.createElement('img'); img.src = '/portraits/' + next.id + '.svg'; img.alt = '';
      const copy = document.createElement('span'), name = document.createElement('strong'), role = document.createElement('small');
      name.textContent = next.persona.name; role.textContent = next.persona.occupation; copy.append(name, role); button.append(img, copy);
      button.addEventListener('click', () => selectProfile(next)); $('roster').append(button);
    });
    selectProfile(info.profiles.find(p => p.id === 'mira') || info.profiles[0]);
  } catch { feedback('Could not connect to Anima. Keep the launcher running and reload this page.'); $('send').disabled = true; }
}
init();

function showInspection(data) {
  const calls = data.llm_input?.calls || [];
  $('prompt-note').textContent = calls.length ? `${calls.length} actual model call(s). Initial and repair inputs are shown separately. Keys and headers are excluded.` : 'No LLM call was made. This response used a deterministic policy route.';
  $('llm-input').textContent = calls.length ? JSON.stringify(calls, null, 2) : 'No messages were sent to a language model.';
  const context = data.context, plan = data.result.plan;
  $('impact-summary').textContent = `${context.persona.name}: ${context.social_appraisal.stimulus.replaceAll('_', ' ')} > ${context.social_appraisal.willingness} > ${plan.route} (${plan.intent.replaceAll('_', ' ')}).`;
  const cards = [];
  function card(title, text, source) {
    const item = document.createElement('article'); item.className = 'impact-card';
    const heading = document.createElement('h3'); heading.textContent = title;
    const body = document.createElement('p'); body.textContent = text;
    const origin = document.createElement('small'); origin.textContent = source;
    item.append(heading, body, origin); cards.push(item);
  }
  card('Standing & disposition', `${context.recognition}; ${context.trust_stance} trust; ${context.social_appraisal.tone} tone. ${context.persona.occupation}, ${context.persona.social_role}.`, 'Persona + saved directed relationship');
  card('State & willingness', `${context.availability}; mood: ${context.mood}; perceived threat: ${context.threat}. Current goal: ${context.current_goal || 'unknown'}.`, 'Eligible observations + fresh NPC state');
  for (const impact of context.influences) card(impact.rule.replaceAll('_', ' '), impact.effect, `${impact.dimension} <- ${impact.source_ids.join(', ')}`);
  for (const dependency of context.dependencies) card(`Resolved ${dependency.field}`, `${dependency.value ?? 'unknown'} (${dependency.reason})`, dependency.source_ids.join(', ') || 'No eligible evidence');
  card('Response contract', `${plan.max_words} words / ${plan.max_sentences} sentences; route ${plan.route}; affect ${plan.affect}. History used: ${data.result.history_used}, omitted: ${data.result.history_omitted}.`, plan.reason_codes.join(', '));
  card('Knowledge boundary', `${context.perceived_facts.length} eligible observations; ${context.exclusions.length} excluded. History and player claims remain untrusted.`, 'These rules describe implemented appraisal, not proven human psychology.');
  const knowledge = data.result.knowledge;
  if (knowledge) card('Retrieved knowledge', `${knowledge.status}; ${data.result.evidence_used.length} passages used, ${data.result.evidence_omitted} omitted by budget.`, knowledge.evidence.map(hit => `${hit.source} #${hit.chunk_index}`).join(', ') || 'No retrieved passages');
  if (data.visual_context) card('Visual reference (untrusted)', data.visual_context.environment || 'No environment description.', (data.visual_context.uncertainties || []).join('; ') || 'Not NPC perception or game truth.');
  $('impact-map').replaceChildren(...cards);
}
function updateCamera() {
  cameraZoom = Math.max(.65, Math.min(1.55, cameraZoom));
  stage?.setView(cameraView, cameraZoom);
  $('portrait').style.setProperty('--portrait-zoom', String(cameraZoom * (cameraView === 'close' ? 1 : .8)));
  $('zoom-level').textContent = `${Math.round(cameraZoom * 100)}%`;
  $('view-close').setAttribute('aria-pressed', String(cameraView === 'close'));
  $('view-wide').setAttribute('aria-pressed', String(cameraView === 'wide'));
  $('zoom-out').disabled = cameraZoom <= .65; $('zoom-in').disabled = cameraZoom >= 1.55;
}
$('view-close').addEventListener('click', () => { cameraView = 'close'; cameraZoom = 1; updateCamera(); });
$('view-wide').addEventListener('click', () => { cameraView = 'wide'; cameraZoom = 1; updateCamera(); });
$('zoom-in').addEventListener('click', () => { cameraZoom += .1; updateCamera(); });
$('zoom-out').addEventListener('click', () => { cameraZoom -= .1; updateCamera(); });
function toggleImmersion() {
  const immersive = document.body.classList.toggle('immersive');
  $('immersive').setAttribute('aria-pressed', String(immersive));
  $('immersive').firstChild.textContent = immersive ? 'Return ' : 'Immerse ';
}
$('immersive').addEventListener('click', toggleImmersion);
$('journal-toggle').addEventListener('click', () => {
  const hidden = document.body.classList.toggle('journal-hidden');
  $('journal-toggle').setAttribute('aria-pressed', String(!hidden));
});
$('inspect-open').addEventListener('click', () => $('inspector').showModal());
$('inspect-close').addEventListener('click', () => $('inspector').close());
for (const button of document.querySelectorAll('[data-inspect]')) button.addEventListener('click', () => {
  for (const tab of document.querySelectorAll('[data-inspect]')) tab.setAttribute('aria-pressed', String(tab === button));
  for (const id of ['impact', 'prompt', 'trace']) $(id + '-view').hidden = id !== button.dataset.inspect;
});
document.addEventListener('keydown', event => {
  if (event.target.closest?.('input,textarea,select,dialog') || event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.key.toLowerCase() === 'i') { event.preventDefault(); toggleImmersion(); }
});

$('expressions').addEventListener('change', () => stage?.setExpressions($('expressions').checked));
function resetVisual(message = 'No scene selected.') { visualContext = null; $('vision-file').value = ''; $('vision-analyze').disabled = true; $('vision-clear').disabled = true; $('vision-attach').checked = false; $('vision-attach').disabled = true; $('vision-status').textContent = message; }
$('vision-file').addEventListener('change', () => { const file = $('vision-file').files[0]; $('vision-analyze').disabled = !file; $('vision-status').textContent = file ? `${file.name} ready for local CV analysis.` : 'Choose a PNG or JPEG screenshot.'; });
$('vision-clear').addEventListener('click', () => resetVisual());
$('vision-analyze').addEventListener('click', async () => { const file = $('vision-file').files[0]; if (!file || !info?.cv_enabled) return; $('vision-analyze').disabled = true; $('vision-status').textContent = 'Analyzing scene locally…'; try { const response = await fetch('/api/vision/analyze', {method:'POST', headers:{'Content-Type':file.type, 'X-Lab-Token':token}, body:file}); const result = await response.json(); if (!response.ok) throw new Error(result.error || 'cv_failed'); visualContext = result.visual; $('vision-attach').disabled = false; $('vision-clear').disabled = false; $('vision-status').textContent = `Scene ready: ${visualContext.environment || 'no environment description'}. Check Attach to include it in the next turn.`; } catch (error) { $('vision-status').textContent = `Scene analysis unavailable: ${error.message}`; } finally { $('vision-analyze').disabled = false; } });
