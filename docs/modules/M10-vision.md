# M10 - Optional visual perception

Status: optional implementation, required contract | Requirement: SYS-12 | Owner/reviewer: unassigned

## Responsibility and interface

`observe(frame, camera_metadata, deadline) -> VisualObservation` translates selected game frames into structured objects/entities, scene labels, possible actions and spatial relations. Core uses descriptors rather than passing every frame to the dialogue model. An initial mock descriptor is enough for core integration; actual perception is evaluated separately.

## Design

Sample on meaningful changes/explicit requests with a configurable rate cap, short TTL and last-good observation cache. Run asynchronously and drop late/stale results. Distinguish single-frame object detection from temporal action recognition; a sword in an image does not prove an attack. Identity links require telemetry or calibrated matching; uncertain objects stay anonymous.

Include frame ID, source view/camera entity, capture time, observed entities/attributes/relations, confidence, model revision and perceiver scope. A player-camera frame may reveal things hidden from the NPC. Without a justified NPC-visibility mapping, observations are debug-only and cannot enter NPC knowledge. HUD/quest text and remote player inventory must not leak privileged facts through screenshots.

Prefer fresh telemetry where it provides the same mechanical fact, using CV for visible details unavailable from the adapter. Preserve disagreements. Never overwrite identity/combat state because a visual classifier guessed differently. Use a small scene/object/action vocabulary first and annotate game-specific limitations; universal generalization is not assumed.

## Compute and failure

Initial API-first dialogue work requires no CV GPU. CV model choice remains open; measure game contention before selecting it. Frame retention is off by default. Missing/low-confidence CV input must not block a normal turn. Later 4 GB VRAM preference may require CPU perception, lower rate or disabling CV alongside a local LLM.

## Acceptance / handoff

Use labelled scenes with objects, occlusion, viewpoint mismatch, uncertain identity and stale detections. Measure detection precision, scene relevance, latency and inappropriate-knowledge leakage. Show that the same core supports both a structured descriptor and no CV input. Supply dataset/model provenance, vocabulary, descriptor fixtures and benchmark results; do not equate scene labels with complete world understanding.
