# Knowledge input folder

Place supported knowledge documents here when M05 is implemented. This is currently a folder convention; ingestion does not run yet. Set a different root through configuration if desired.

Initial planned formats: UTF-8 text/Markdown, structured JSON/CSV and text-based PDF. Binary/scanned/encrypted PDFs need diagnostics or later OCR. Do not place credentials, personal player data, copyrighted game binaries or model weights here. The current user-edited `.gitignore` does not exclude this folder; review privacy/licensing before tracking documents. Keep shared public test corpora in `fixtures/worlds/` instead.

Every document requires a stable ID, world/source identity, provenance, revision and access metadata. A proposed sidecar `suppliers.md.meta.json`:

```json
{
  "document_id": "smith-supplier-list",
  "game_id": "demo",
  "world_id": "village",
  "source": "team-authored",
  "source_revision": "1",
  "license": "team-authored; release terms pending",
  "required_grants": ["smith_trade_contacts"],
  "entities": ["mira"],
  "regions": ["village"],
  "factions": [],
  "secret": false,
  "valid_from_s": 0,
  "valid_until_s": null
}
```

World-public material still needs an explicit public grant for that world; an empty or missing access label never means globally accessible. M04 resolves who has the grants; generic M05 enforces the eligible set. Secret material needs explicit secret grants. Document instructions are treated as source data, never as prompt/system policy.

M05 must provide validate/ingest/status diagnostics, automatic storage creation and model setup, incremental changes and recovery; see its [TRD](../../docs/modules/M05-rag.md). Do not edit the persisted database by hand.
