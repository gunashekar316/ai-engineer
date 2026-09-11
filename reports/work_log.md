# Work Log

## Day 1
- **Project Setup:** Initialized the Git repository, created the directory structure (`src/segmentation`, `src/analysis`, `src/automation`, `reports`), and added a Python-specific `.gitignore` to keep the repository clean.
- **Data Ingestion:** Created `src/segmentation/ingest_and_extract.py` to parse the `events.jsonl` files nested within `dataset_a/ses_<id>/chunk_<id>/`. The script is designed to chronologically merge the chunk events and extract unique Japanese UI elements (window titles, URLs, and UI attributes).
- **Next Steps:** We will use a generative AI interactive chat interface to manually translate and categorize the `extracted_ui_elements.json` into a static `translation_map.json` lookup table. This ensures our local pipeline doesn't depend on external APIs.

---

> **Note on Alternatives Rejected:** We explicitly chose not to use an LLM API directly in our Python pipeline. While an LLM API would automate the translation step dynamically, it introduces a hard dependency on an external paid service and goes against the goal of building a fully local, deterministic solution. By extracting elements and translating them statically, we mitigate latency and dependency risks.

> **Note on Risk Evidence:** We anticipate text parsing issues due to the `DATA_SCHEMA.md` specifically warning that the `text_input_complete` event is unreliable and missing content. This evidence directly led us to build reconstruction logic in our pipeline using keystrokes and clipboard data.

## Day 2
- **Scaffold Translation Map:** Created a boilerplate `src/segmentation/translation_map.json` with empty JSON objects for apps, URLs, and UI labels. This will be manually populated using an LLM.
- **Enrichment Script:** Wrote `src/segmentation/enrich_events.py` to read chronologically sorted events and apply our translation map to classify contexts. It also reconstructs the unreliable `text_input_complete` event using preceding active window focus and raw keystrokes to ensure robust text capture.
- **Populate Translation Map:** Wrote a deterministic parsing script to map the extracted unique Japanese terminology into English schemas aligning with the 15 ground truth business processes across HR, Finance, and Operations. For edge-cases, unrecognized URLs and UI labels are gracefully classified under the "general" intent or domain. 
- **Verify Enrichment Pipeline:** Executed `enrich_events.py` against `dataset_a` to process all sessions. Ensured events are correctly injected with contextual English tags, and raw keystrokes are successfully aggregated into functional text input strings without any runtime failures.
- **Next Steps:** Proceed to Day 3 for segmenting these enriched event streams into functional business process blocks based on semantic boundaries.

## Day 3
- **Build Strict Schema Validator:** Implemented `src/segmentation/validate_schema.py` to enforce strict compliance with the target schema (4 key attributes: `session_id`, `start`, `end`, `label` with ISO 8601 UTC timestamps). Verified that our pipeline output passes this strict constraint.
- **Implement State-Machine Segmenter:** Developed `src/segmentation/segmenter.py` using block-level logic. Segment boundaries are determined by temporal gaps (a 120-second threshold) and semantic transitions. The segmenter handles noise through forward and backward fill propagation of reliable explicit intents to contiguous, short-lived events. 
- **Handling Dataset B Novelty:** Refined the segmenter logic to infer dynamic process labels dynamically using URL paths or window signatures (e.g., `proc_<path>`) when processing Dataset B, accommodating the new departments and applications smoothly without classifying them as generic noise.
- **Evaluation Harness:** Created `src/segmentation/evaluate.py` to map our descriptive English intents to the explicit Dataset A evaluation codes (A-O) and compute Intersection-over-Union style Precision, Recall, and F1 scores based on temporal overlap against `gt_manifest.json`.
- **Final Validation:** Successfully evaluated the generated `dataset_a_segments.jsonl` (scoring ~19% F1 baseline with rudimentary static mappings) and validated the `segments.jsonl` generated from Dataset B against the schema. All 15 unseen sessions generated valid novel intents compliant with formatting constraints.
