# I10 local CV bridge plan

## Outcome and acceptance

Anima's local companion may optionally forward a manually selected PNG/JPEG screenshot to the separately running Skyrim CV service. It displays the returned scene descriptor and, only when the tester explicitly attaches it, provides a compact, labelled visual reference to the next model turn. This is a developer/manual-testing bridge, not Mantella/game capture integration.

Acceptance:

- `--cv-url http://127.0.0.1:8000` enables the bridge; absence leaves current launches unchanged.
- Only loopback HTTP CV URLs, PNG/JPEG content and a bounded upload are accepted.
- Anima forwards to the CV service's existing multipart endpoint and validates/normalizes the returned descriptor; an upstream failure gives a controlled response and does not block an ordinary dialogue turn.
- One selected descriptor is memory-only and may be explicitly attached or cleared. It is not stored in social state or exports implicitly.
- Attached visual text reaches only the prompt's untrusted data message, with instructions not to treat it as NPC knowledge, current game state, identity, action, or hidden/HUD data.
- CV output is never converted to `ObservedFact`, retrieval evidence, state, or validation citations. Thus the M10 player-camera visibility boundary remains intact.
- Unit/HTTP tests cover URL validation, response normalization/failure, upload limit/content/auth checks, attachment/clearing, prompt placement and unchanged non-CV turns.

## Boundaries and approach

Runtime code belongs in `src/npc/vision/` for the typed local client and `tools/npc_lab/` for manual UI/session composition. `VisualContext` is an immutable, bounded contract distinct from `ObservedFact`; it carries only the compact descriptors needed for prompt context and explicit uncertainty/provenance. The complete raw CV API response/annotated image is not copied into Anima state.

`LabService` owns at most one pending `VisualContext`, replacing it only after successful analysis. `LabTurn.visual_id` binds a turn to that selected descriptor; unknown/stale IDs are rejected. The lab server adds one authenticated loopback binary endpoint, preserves the existing JSON-only policy for all other endpoints, and does not log image bytes. The browser gets an attach/clear control and inspector summary.

The visual contract is optional to `PreviewRunner` and `build_prompt`; it is serialized only as `untrusted_visual_reference` in the user data message. Prompt construction reserves a small, fixed visual budget and returns the normal prompt-too-large fallback if core required content cannot fit. No new provider, database, queue, model dependency, recurring capture, or game adapter is introduced.

## Plan self-review

- A direct conversion into supported `ObservedFact` paths would make a player-camera image NPC knowledge. Rejected; this violates M10 without an NPC visibility mapping.
- A raw `data:` URL in `LabTurn` would defeat the server body bound and leak an unvalidated large payload into the model path. Rejected; binary upload is isolated and normalized before attachment.
- Direct browser-to-CV requests would widen CORS and bypass Anima's session token/control surface. Rejected; Anima provides a narrow loopback proxy.
- The CV service may be offline/slow. The client has a bounded deadline and no startup probe; visual analysis is a separate user action and failures do not affect ordinary turns.

## Verification

Add focused deterministic client, prompt, lab-service and lab-HTTP tests using fake CV clients/HTTP transports. Run focused tests, full offline `pytest`, `pip check`, and existing UI syntax checks. A live end-to-end attempt requires an available local CV backend/Ollama/model and is reported separately.
