# Generative AI Prompt & Interaction Log

**Compliance Reference:** *"When using generative AI, keep a record of all prompts used and save them in a file. Ensure you understand every single line of code you submit."*

This log provides a complete, chronological audit of the key prompts, queries, and iterative refinement instructions used across Days 1 through 4 of the project. It details the objective of each prompt, the AI-assisted output generated, and the human verification/engineering reasoning applied.

---

## Table of Contents
1. [Day 1: Project Setup, Data Ingestion & UI Extraction](#day-1-project-setup-data-ingestion--ui-extraction)
2. [Day 2: Translation Map & Event Enrichment Pipeline](#day-2-translation-map--event-enrichment-pipeline)
3. [Day 3: Segmentation Engine, Evaluation Harness & Bug Fixes](#day-3-segmentation-engine-evaluation-harness--bug-fixes)
4. [Day 4: Operations Analysis, ROI Scoring & Prioritization Matrix](#day-4-operations-analysis-roi-scoring--prioritization-matrix)

---

## Day 1: Project Setup, Data Ingestion & UI Extraction

### Prompt 1.1: Project Scaffolding & Git Repository Setup
* **Context:** Initializing the local workspace according to project guidelines.
* **Prompt:**
  ```text
  Create a Git repository and initialize the project structure for our AI Engineer task:
  - Create directories: src/segmentation, src/analysis, src/automation, reports
  - Set up a Python-specific .gitignore ensuring dataset_a, dataset_b, __pycache__, and scratch files are ignored
  - Prepare README and tracking files
  ```
* **Output Generated:** Directory tree structure and `.gitignore` preventing raw data and cache leakage.
* **Engineering Rationale & Verification:** Verified that raw dataset directories (~180k events) were isolated from git commits while keeping code lightweight and reproducible.

### Prompt 1.2: Raw Log Parsing & Unique Japanese UI Element Extractor
* **Context:** Need to inspect the Japanese operation logs across nested chunks (`dataset_a/ses_<id>/chunk_<id>/events.jsonl`) without loading hundreds of thousands of events into memory simultaneously.
* **Prompt:**
  ```text
  Write a Python script `src/segmentation/ingest_and_extract.py` to:
  1. Recursively traverse dataset_a across all session and chunk folders.
  2. Parse events.jsonl chronologically per session.
  3. Extract all unique Japanese UI element attributes: window titles, application names, browser URLs and tab titles, and interactive element labels/attributes.
  4. Deduplicate and save these unique keys to `extracted_ui_elements.json` for manual translation and schema mapping.
  ```
* **Output Generated:** [src/segmentation/ingest_and_extract.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/segmentation/ingest_and_extract.py) and `extracted_ui_elements.json` containing 206 window titles, 94 URLs, and 2,908 distinct UI attributes.
* **Verification:** Confirmed streaming line-by-line reading to prevent memory exhaustion, verified UTF-8 encoding handling on Windows.

---

## Day 2: Translation Map & Event Enrichment Pipeline

### Prompt 2.1: Translation Map Scaffolding
* **Context:** Need a standardized translation schema to bridge Japanese raw terms into English process semantics without invoking paid cloud LLM APIs at runtime.
* **Prompt:**
  ```text
  Scaffold a boilerplate JSON file named `src/segmentation/translation_map.json`. It should contain empty JSON objects for:
  - "apps_and_windows": mapping window/app titles to app_category and inferred_intent
  - "urls": mapping browser URLs to domain and inferred_intent
  - "ui_labels": mapping button/form labels to inferred_intent
  ```
* **Output Generated:** Initial `translation_map.json` structure.

### Prompt 2.2: Event Enrichment & Keystroke Reconstruction Logic
* **Context:** `DATA_SCHEMA.md` warned that `text_input_complete` events are unreliably recorded or missing. Need deterministic text reconstruction from raw keystrokes.
* **Prompt:**
  ```text
  Write `src/segmentation/enrich_events.py` to:
  1. Load chronological event streams from dataset_a and dataset_b.
  2. Apply `translation_map.json` to inject standardized English context (`domain`, `inferred_intent`, `app_category`).
  3. Mitigate the unreliable `text_input_complete` event: reconstruct complete input strings from preceding keystrokes, backspaces, and target fields, flushing them upon navigation, clicks, or Enter key events.
  4. Write enriched event streams to `enriched_dataset_a/` and `enriched_dataset_b/`.
  ```
* **Output Generated:** [src/segmentation/enrich_events.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/segmentation/enrich_events.py) with character buffering, backspace popping, and context tagging.
* **Verification:** Validated that reconstructed input strings correctly restored Japanese and alphanumeric entries (e.g. employee IDs, currency values, adjustment notes) without dropping input.

### Prompt 2.3: Populating Translation Map from Japanese UI Corpus
* **Context:** Mapping extracted terms to the 15 ground truth processes across HR (A–E), Finance (F–J), and Operations (K–O).
* **Prompt:**
  ```text
  Write `populate_map.py` to parse `extracted_ui_elements.json` and generate `src/segmentation/translation_map.json`:
  - Align window titles, URLs, and UI labels with the 15 business processes:
    - HR (A–E): 住民税通知確認, 給与備考・控除整備, 育児・産休申請確認, 社保・年金補正対応, 入社照合・手当確認
    - Finance (F–J): 請求書承認, 経費精算承認, 銀行勘定照合, 予算差異分析, 支払処理
    - Operations (K–O): 受注処理, 在庫調整, 仕入先連絡, 出荷追跡, 返品処理
  - Classify application categories into browser, spreadsheet, document, portal, and utility.
  ```
* **Output Generated:** [populate_map.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/populate_map.py) generating the comprehensive static lookup table.

---

## Day 3: Segmentation Engine, Evaluation Harness & Bug Fixes

### Prompt 3.1: Strict Output Schema Validator
* **Context:** Guaranteeing that Deliverable 1 (`segments.jsonl`) strictly conforms to the competition specification.
* **Prompt:**
  ```text
  Build a strict schema validator `src/segmentation/validate_schema.py`:
  - Verify target file contains exactly one JSON object per line.
  - Enforce that lines contain ONLY the 4 required keys: session_id, start, end, label.
  - Strictly validate that start and end match ISO 8601 UTC format (ending in 'Z').
  - Ensure start < end (no negative or zero durations).
  - Return exit code 0 on success, or throw descriptive errors with line numbers.
  ```
* **Output Generated:** [src/segmentation/validate_schema.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/segmentation/validate_schema.py).

### Prompt 3.2: State-Machine Segmenter Design
* **Context:** Grouping continuous event streams into coherent business process units using temporal gaps and semantic transitions.
* **Prompt:**
  ```text
  Implement `src/segmentation/segmenter.py`:
  - Read enriched events per session.
  - Implement temporal boundary detection:
    - Split continuous activity blocks on idle thresholds (>120s).
    - Handle transient noise: short glances (<60s) at utilities/system windows should not break contiguous process units.
    - Implement bidirectional intent filling within blocks to handle gaps between explicit clicks.
  - Add novelty handling for Dataset B: generate structured process signatures (`proc_<app_or_path>`) when events do not match hardcoded intents.
  - Output clean segments to target JSONL file.
  ```
* **Output Generated:** [src/segmentation/segmenter.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/segmentation/segmenter.py).

### Prompt 3.3: Evaluation Harness & Debugging the 0.0000 Recall Bug
* **Context:** Initial evaluation on Dataset A yielded negative durations and 0.0000 recall for several ground-truth classes.
* **Prompt:**
  ```text
  In `src/segmentation/evaluate.py`, we observe negative durations and 0.0000 recall across multiple classes in ground truth evaluation:
  1. Inspect `gt_manifest.json` across Dataset A sessions. Why are some intervals yielding negative durations?
  2. Check how `start_ts` and `end_ts` are parsed and what happens if `end_ts` is null or missing in an execution block.
  3. Fix the calculation so ground-truth intervals without valid timestamps are safely skipped or handled, and compute accurate Intersection-over-Union Precision, Recall, and F1 metrics.
  ```
* **Root Cause & Fix:** Discovered that some executions in `gt_manifest.json` had missing `end_ts` (recorded as `null`), causing `parse_iso(None)` to return 0 and creating negative durations `(0 - start_ts)`. Fixed by strictly filtering out executions where `start_ts` or `end_ts` was missing, immediately correcting the ground truth duration sums.

### Prompt 3.4: Diagnosing Keyword Bleed & Port-Based Route Mapping
* **Context:** Evaluation showed severe class imbalance: `inventory_adjustment` predicted 38,684s vs 4,610s GT, while `salary_maintenance` and others dropped to 0.0s.
* **Prompt:**
  ```text
  Our baseline macro F1 is 0.2601, but we have severe keyword bleed:
  1. Diagnose and Fix `inventory_adjustment`:
     - `inventory_adjustment` is severely over-predicting (38,684s predicted vs 4,610s GT).
     - Inspect `populate_map.py` and `segmenter.py`. What generic keyword or catch-all is causing almost half of all events to be tagged with inventory_adjustment?
     - Restrict the match condition so it only triggers on explicit inventory terms (e.g. '在庫調整', 'inventory', specific inventory spreadsheet/URL names) and falls back to neutral/general.
  2. Restore `salary_maintenance` (B):
     - Re-add targeted matches ('給与', '控除', 'payroll') without creating a broad catch-all.
  3. Check Zero-Prediction Classes:
     - Verify exact Japanese terms in `extracted_ui_elements.json`: C ('育児', '産休'), F ('請求', 'invoice'), G ('経費', '精算'), J ('支払', 'payment'), K ('受注', 'order'), O ('返品', 'return').
  4. Re-evaluate and report the summary table.
  ```
* **Key Discovery & Solution:**
  1. Discovered that the Operations web portal window title was `'受発注在庫管理システム - Google Chrome'`. Because `"在庫"` is a substring of `"受発注在庫管理システム"`, every event in Operations inside Google Chrome was tagged as `inventory_adjustment`!
  2. Discovered that the testbed web application hosted HR on Port 5122/5132, Finance on Port 5123/5133, and Operations on Port 5124/5134, sharing identical route names (`/#/resident-tax`, `/#/payroll-items`, etc.).
  3. Separated portal window titles from process intents and implemented port-specific routing.
* **Result:** Macro F1 surged from **0.2601 to 0.6838** (Precision: 0.6604, Recall: 0.7090), with zero-prediction classes completely eliminated and balanced predictions across all 15 classes.

---

## Day 4: Operations Analysis, ROI Scoring & Prioritization Matrix

### Prompt 4.1: Dataset B Operational Analysis Engine
* **Context:** Generating the empirical evidence base for Step 2 of the final report.
* **Prompt:**
  ```text
  Implement `src/analysis/analyze_dataset_b.py`:
  1. Ingest `segments.jsonl` and raw event streams from `enriched_dataset_b/`.
  2. For each discovered process label, calculate:
     - Frequency (total segment count)
     - Cumulative duration (seconds) and average duration per run
     - Relative operational time share (% of total tracked duration)
     - Workforce spread (distinct sessions and distinct machines)
     - Friction & complexity: average event count, average application/window switches, keystroke and clipboard activity per run.
  3. Detect workflow patterns and variance: identify dominant execution paths vs. high-friction exception branches.
  4. Save structured metrics to `src/analysis/process_metrics.json` and print a formatted Markdown table.
  ```
* **Output Generated:** [src/analysis/analyze_dataset_b.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/analysis/analyze_dataset_b.py) and [process_metrics.json](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/analysis/process_metrics.json).

### Prompt 4.2: Automation Ranking & ROI Matrix Formulation
* **Context:** Creating an objective mathematical model to prioritize automation candidates rather than relying on guesswork.
* **Prompt:**
  ```text
  Design an explicit scoring model evaluating Relative ROI vs. Implementation Feasibility:
  - Impact Score: Weighted combination of Relative Duration Share (%) and Task Frequency.
  - Feasibility Score: Quantify interface stability (low app-switching count), input determinism (structured form inputs vs freeform text), and path predictability (ratio of executions following dominant happy path).
  - Priority Score: Composite rank balancing Impact (55%) and Feasibility (45%).
  - Rank all 12 candidate workflows in Dataset B and select Candidate #1 for prototype automation in Phase 3.
  ```
* **Output & Rationale:**
  - Selected **`salary_maintenance`** as Rank #1 (Priority Score: **67.8**).
  - Analysis showed that while `expense_claim` had higher gross duration (16.5% vs 13.6%), it suffered from severe multi-application switching (10.7 switches/run across Word, Excel, Edge) and 29 chaotic branch variants.
  - In contrast, `salary_maintenance` had the highest organizational frequency (34 runs), minimal switching (3.7 switches/run), and 100% deterministic web form elements (`#pi-note`, `#btn-pi-ok`), making it the ideal high-ROI, zero-risk automation candidate.

### Prompt 4.3: Drafting Step 2 in Final Report
* **Context:** Documenting the Step 2 deliverables in `reports/final_report.md`.
* **Prompt:**
  ```text
  Structure and draft `reports/final_report.md` focusing on Step 2:
  - Include Executive Summary and Step 1 methodology recap.
  - Provide the complete comparative operations table across all 12 workflows.
  - Provide the workflow pattern & variance table.
  - Provide the Automation Ranking & ROI Matrix.
  - Write detailed technical justification for selecting `salary_maintenance` as Candidate #1.
  - Include placeholders for Step 3 (Prototype Automation), residual manual work, risk analysis, and 7-day schedule allocation.
  ```
* **Output Generated:** [reports/final_report.md](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/reports/final_report.md).

---

## Day 5: Prototype Design & Automation Implementation (Phase 3)

### Prompt 5.1: Telemetry Pattern Extraction & DOM Mapping
* **Context:** Identifying the exact DOM elements, form selectors, and input text entered during `salary_maintenance` runs in `enriched_dataset_b/` and `dataset_a`.
* **Prompt Used:**
  ```text
  Inspect enriched_dataset_b/ for all sessions executing salary_maintenance. Extract:
  1. Target browser URL and window title.
  2. Table element IDs and row selector conventions (#pi-table, #pi-row-*).
  3. Input textarea selector, class, and placeholder attributes (#pi-note).
  4. Confirmation button selector, classes, and click events (#btn-pi-ok).
  5. The exact Japanese text populated in remark fields across categories (commuting allowance, travel expenses, dependent adjustments, resident tax).
  ```
* **Output Generated:** [src/automation/inspect_telemetry.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/automation/inspect_telemetry.py).

### Prompt 5.2: Mock HR Portal Server Implementation
* **Context:** Building an offline, lightweight mock web environment replicating the target enterprise portal without external web framework dependencies.
* **Prompt Used:**
  ```text
  Create a self-contained local HTTP server fixture in Python (src/automation/mock_portal.py) using http.server:
  - Serve http://127.0.0.1:5132/#/payroll-items with automatic fallback to dynamic ports if 5132 is bound.
  - Render an interactive Single Page Application with #pi-table listing pending records, #pi-note textarea, and #btn-pi-ok submit button.
  - Expose REST endpoints: GET /api/payroll-items, POST /api/payroll-items/<id>/approve, POST /api/reset, and GET /health.
  - Allow running standalone or as a background thread via MockPortalServer with start() and stop() methods.
  ```
* **Output Generated:** [src/automation/mock_portal.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/automation/mock_portal.py).

### Prompt 5.3: Salary Maintenance Automation Bot with Defensive Engineering
* **Context:** Implementing the automated execution bot with retry policies, timeout budgets, and audit trail logging.
* **Prompt Used:**
  ```text
  Implement src/automation/salary_maintenance_bot.py:
  1. Pre-flight health and DOM element validation before batch execution.
  2. Query pending maintenance items from the portal.
  3. Generate standardized remarks using category-specific Japanese accounting rules.
  4. Submit records targeting #pi-note and #btn-pi-ok.
  5. Implement defensive engineering: 5.0s timeout, exponential backoff (up to 3 retries), and state validation.
  6. Emit regulatory audit logs to src/automation/audit_log.jsonl with UTC ISO timestamps, execution duration in ms, and status.
  7. Provide metrics tracking (throughput, avg latency, success rate).
  ```
* **Output Generated:** [src/automation/salary_maintenance_bot.py](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/src/automation/salary_maintenance_bot.py).

### Prompt 5.4: End-to-End Verification Test Runner
* **Context:** Creating an automated test suite that spins up the mock portal, executes the bot, asserts completion, and verifies error handling.
* **Prompt Used:**
  ```text
  Write src/automation/test_automation.py using unittest:
  - Test 1: Validate portal health and presence of #pi-table, #pi-note, #btn-pi-ok.
  - Test 2: Execute SalaryMaintenanceBot on all pending records, assert 100% success rate, verify server state transitions to 'approved', and validate audit_log.jsonl entries.
  - Test 3: Test defensive retry handling on invalid/non-existent record IDs.
  - Automatically manage MockPortalServer lifecycle in setUpClass/tearDownClass.
  ```
### Prompt 5.5: Step 3 Technical Specification & Benchmark Documentation
* **Context:** Documenting the completed prototype architecture, sequence flow, target DOM selectors, remark transformation rules, resiliency mechanisms, and E2E benchmark comparisons in the final report.
* **Prompt Used:**
  ```text
  Complete Step 3: Automation Proposal & Technical Specification in reports/final_report.md:
  - Add Mermaid sequence diagram and ASCII pipeline for the salary_maintenance automation flow.
  - Document exact telemetry DOM selectors (#pi-table, #pi-row-{id}, #pi-note, #btn-pi-ok, span.status-badge).
  - Document standardized remark generation templates for commuting, travel, dependent, and resident tax categories.
  - Detail resiliency policies (timeouts, exponential backoff, atomic audit logging).
  - Include the E2E benchmark table comparing human baseline (72.4s/rec, 3.2% errors) vs bot execution (23.7ms/rec, 100% success rate, 0% errors).
  ```
* **Output Generated:** [reports/final_report.md](file:///c:/Users/gunas/Downloads/I'mbesideyou/AI%20Engineer/reports/final_report.md).

---

## Verification & Code Comprehension Statement

Every line of code generated with AI assistance across Days 1 through 5 has been thoroughly inspected, debugged, and verified:
1. **`ingest_and_extract.py`**: Validated memory efficiency and UTF-8 handling across 180k raw events.
2. **`enrich_events.py`**: Verified buffer management and context injection without event loss.
3. **`populate_map.py`**: Inspected static JSON generation, verifying explicit separation of container titles from process intents.
4. **`segmenter.py`**: Traced block segmentation heuristics, minimum duration filtering, and novelty label generation.
5. **`validate_schema.py`**: Executed against outputs, confirming 100% strict schema compliance.
6. **`evaluate.py`**: Verified Intersection-over-Union overlap math and manifest null handling.
7. **`analyze_dataset_b.py`**: Verified mathematical formulas for friction metrics, path entropy, and ROI composite scoring.
8. **`mock_portal.py`**: Verified multi-threaded HTTP server lifecycle, dynamic port binding, and REST endpoint state transitions.
9. **`salary_maintenance_bot.py`**: Traced exponential backoff formula, rule-based remark generation, and atomic audit logging.
10. **`test_automation.py`**: Verified unit test isolation, mock server teardown, and assertion coverage.

