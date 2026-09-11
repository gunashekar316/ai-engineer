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
- **Precision Tuning & Multi-Domain Port Routing:** Diagnosed severe keyword bleed where the Operations portal title `受発注在庫管理システム` matched the generic substring `在庫`, causing 38,684s of over-prediction for `inventory_adjustment` and zero-predictions across several classes. Resolved this by separating portal containers from process intents, mapping port-specific routes (5122/5132 for HR, 5123/5133 for Finance, 5124/5134 for Operations), and targeting exact Japanese UI terms (`請求`, `精算`, `支払`, `受注`, `返品`, `給与/控除`).
- **Benchmark Evaluation (Macro F1 = 0.6838):** Re-evaluated Dataset A, achieving balanced predictions and temporal overlap across all 15 business processes:

| Code | Label | Intersection (s) | Pred Dur (s) | GT Dur (s) | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | `resident_tax` | 3,427.4 | 4,914.9 | 4,721.0 | 0.6974 | 0.7260 | **0.7114** |
| **B** | `salary_maintenance` | 2,943.7 | 4,156.9 | 4,818.1 | 0.7081 | 0.6110 | **0.6560** |
| **C** | `childcare_leave` | 5,181.5 | 10,232.4 | 6,987.7 | 0.5064 | 0.7415 | **0.6018** |
| **D** | `social_insurance` | 2,941.1 | 4,612.4 | 4,524.0 | 0.6376 | 0.6501 | **0.6438** |
| **E** | `onboarding_allowance` | 2,354.0 | 3,184.2 | 3,005.3 | 0.7393 | 0.7833 | **0.7606** |
| **F** | `invoice_approval` | 3,859.2 | 5,247.3 | 5,358.2 | 0.7355 | 0.7202 | **0.7278** |
| **G** | `expense_claim` | 2,195.5 | 3,115.8 | 3,231.5 | 0.7047 | 0.6794 | **0.6918** |
| **H** | `bank_reconciliation` | 2,800.1 | 3,746.8 | 3,939.9 | 0.7473 | 0.7107 | **0.7286** |
| **I** | `budget_variance` | 6,847.5 | 10,800.3 | 8,101.5 | 0.6340 | 0.8452 | **0.7245** |
| **J** | `payment_processing` | 2,572.3 | 3,485.8 | 3,336.8 | 0.7379 | 0.7709 | **0.7541** |
| **K** | `order_processing` | 2,757.4 | 4,084.3 | 4,143.9 | 0.6751 | 0.6654 | **0.6702** |
| **L** | `inventory_adjustment` | 2,847.9 | 4,887.5 | 4,610.5 | 0.5827 | 0.6177 | **0.5997** |
| **M** | `supplier_contact` | 5,084.7 | 7,596.6 | 7,520.0 | 0.6693 | 0.6762 | **0.6727** |
| **N** | `shipment_tracking` | 3,462.0 | 4,965.3 | 5,398.5 | 0.6972 | 0.6413 | **0.6681** |
| **O** | `return_processing` | 2,395.5 | 3,214.4 | 3,175.6 | 0.7453 | 0.7544 | **0.7498** |
| **ALL**| **Global Macro** | **51,669.8** | **78,244.8** | **72,872.5** | **0.6604** | **0.7090** | **0.6838** |

- **Deliverable 1 Generation (Dataset B):** Enriched `dataset_b` into `enriched_dataset_b/` and generated the final `segments.jsonl` in the repository root. Ran `validate_schema.py` to confirm 100% compliance with ISO 8601 UTC timestamps, required schema keys, and strict JSONL line formatting across all 191 segments.

