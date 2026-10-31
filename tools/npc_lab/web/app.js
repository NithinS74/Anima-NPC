'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="lab-token"]').content;
const scores = ['favourability', 'trust', 'familiarity', 'fear', 'irritation'];
const presets = {
  stranger: [0, 0, 0, 0, 0], friend: [80, 80, 90, 0, 0],
  distrusted: [20, -60, 80, 0, 30], disliked: [-60, -60, 0, 0, 70]
};
let info, profile, pending = null, epoch = 0, records = [];
function feedback(text) { $('feedback').textContent = text; }
function clearLog() {
  epoch++; records = []; $('messages').replaceChildren();
  const empty = document.createElement('div'); empty.className = 'empty';
  const quote = document.createElement('span'), heading = document.createElement('h3'), hint = document.createElement('p');
  quote.textContent = '“'; heading.textContent = 'Give them a reason to respond.'; hint.textContent = 'Try a question below, or start your own.';
  empty.append(quote, heading, hint); $('messages').append(empty);
  $('trace').textContent = 'No turn yet.';
  feedback('Conditions updated. Each message is an independent test turn.');
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
function selectProfile(next) {
  profile = next; clearLog();
  $('name').textContent = next.persona.name; $('occupation').textContent = next.persona.occupation.toUpperCase();
  $('tagline').textContent = next.tagline; $('location').textContent = next.location;
  $('goal').textContent = next.current_goal; $('testing-notes').textContent = next.testing_notes;
  $('portrait').src = '/portraits/' + next.id + '.svg'; $('portrait').alt = 'Original illustrated portrait of ' + next.persona.name;
  $('tags').replaceChildren(...next.persona.speech_style.map(text => { const el = document.createElement('span'); el.textContent = text; return el; }));
  $('boundaries').replaceChildren(...next.persona.boundaries.map(text => { const el = document.createElement('li'); el.textContent = text; return el; }));
  $('preset').value = 'default'; updateScores(scores.map(name => next.relationship[name]));
  $('mood').value = next.mood; $('state').value = 'available'; $('weapon').checked = false;
  $('state').querySelector('[value=closed]').disabled = !next.persona.service_role;
  document.querySelectorAll('.roster-item').forEach(el => el.classList.toggle('selected', el.dataset.id === next.id));
  $('starters').replaceChildren(...next.starters.map(text => {
    const button = document.createElement('button'); button.type = 'button'; button.textContent = text;
    button.addEventListener('click', () => { $('message').value = text; $('message').focus(); }); return button;
  }));
}
async function post(path, body) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Lab-Token': token }, body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || 'request_failed');
  return result;
}
$('chat').addEventListener('submit', async event => {
  event.preventDefault(); if (pending || !profile) return;
  const text = $('message').value.trim(); if (!text) return;
  const id = crypto.randomUUID(), turnEpoch = epoch, character = profile;
  pending = id; setBusy(true); $('message').value = '';
  const request = { request_id: id, persona_id: character.id, text, relationship: relationship(), mood: $('mood').value, state: $('state').value, weapon_drawn: $('weapon').checked };
  bubble('You', text, 'player');
  const waiting = document.createElement('div'); waiting.className = 'waiting'; waiting.textContent = 'Waiting for a validated response…'; $('messages').append(waiting);
  feedback(info.mode === 'live' ? 'Calling the configured API. No streaming text is displayed before validation.' : 'Using the deterministic fake — this is not an LLM-quality test.');
  try {
    const data = await post('/api/turn', request);
    if (epoch !== turnEpoch || pending !== id) return;
    const result = data.result, meta = `${result.status} · ${result.model_calls} calls · ${Math.round(result.elapsed_ms)} ms · ${result.model || 'authored / no completed model'}`;
    bubble(character.persona.name, result.response?.text || (result.response?.mode === 'end' ? '[Ends the interaction]' : '[No speech]'), result.status === 'error_fallback' ? 'system' : '', meta);
    $('trace').textContent = JSON.stringify(data, null, 2);
    records.push({ request, ...data }); if (records.length > 30) records.shift();
    feedback(result.error_code ? `Outcome: ${result.error_code}. A fallback is not successful generation.` : 'Inspect the trace to compare intention with the response. Valid structure does not prove realism.');
  } catch (error) {
    if (epoch === turnEpoch) { bubble('Lab', `Request failed: ${error.message}`, 'system'); feedback('Check the launcher terminal and local provider settings.'); }
  } finally {
    waiting.remove(); if (pending === id) { pending = null; setBusy(false); }
  }
});
$('message').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('chat').requestSubmit(); } });
$('reset').addEventListener('click', async () => {
  const id = pending; clearLog();
  if (id) {
    try { await post('/api/cancel', { request_id: id }); feedback('Cancellation requested; late output will not enter this log.'); }
    catch { feedback('Could not confirm backend cancellation. Wait for the active request to finish.'); }
  }
});
$('preset').addEventListener('change', () => { updateScores($('preset').value === 'default' ? scores.map(name => profile.relationship[name]) : presets[$('preset').value]); clearLog(); });
['state', 'mood', 'weapon'].forEach(name => $(name).addEventListener('change', clearLog));
$('export').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify({ mode: info?.mode, memory: 'display-only', turns: records }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = 'npc-lab-session.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
async function init() {
  scores.forEach(name => {
    const row = document.createElement('div'), label = document.createElement('label'), output = document.createElement('output'), slider = document.createElement('input');
    label.className = 'slider-label'; label.htmlFor = name; label.textContent = name[0].toUpperCase() + name.slice(1); output.id = name + '-value'; label.append(output);
    slider.type = 'range'; slider.id = name; slider.min = ['favourability', 'trust'].includes(name) ? -100 : 0; slider.max = 100; slider.value = 0;
    slider.addEventListener('input', () => { output.textContent = slider.value; }); slider.addEventListener('change', () => { $('preset').value = 'default'; clearLog(); });
    row.append(label, slider); $('sliders').append(row);
  });
  try {
    const response = await fetch('/api/info'); if (!response.ok) throw new Error('unavailable'); info = await response.json();
    $('mode').textContent = info.mode === 'live' ? 'LIVE API · may incur charges' : 'OFFLINE FAKE · no model';
    $('timing').textContent = `${info.timing_profile.toUpperCase()} · ${info.deadline_ms / 1000}s deadline · ${info.input_budget_bytes} input bytes`;
    info.profiles.forEach(next => {
      const button = document.createElement('button'); button.className = 'roster-item'; button.dataset.id = next.id;
      const img = document.createElement('img'); img.src = '/portraits/' + next.id + '.svg'; img.alt = '';
      const copy = document.createElement('span'), name = document.createElement('strong'), role = document.createElement('small');
      name.textContent = next.persona.name; role.textContent = next.persona.occupation; copy.append(name, role); button.append(img, copy);
      button.addEventListener('click', () => selectProfile(next)); $('roster').append(button);
    });
    selectProfile(info.profiles.find(p => p.id === 'mira') || info.profiles[0]);
  } catch { feedback('Could not load the lab. Keep the launcher running and reload this page.'); $('send').disabled = true; }
}
init();
