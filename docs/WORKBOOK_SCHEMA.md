# Workbook schema

## Operational workbook

Standard Excel representation of operational partnership data. Generated from `backend/app/workbook.py` (the source of truth; tests check it against the models). Download it from `GET /api/export/workbook`.

- Each sheet's first column is its stable ID. `→ Sheet` marks a reference to that sheet's ID column.
- Operational columns hold values stored in operational records. Original values and historical addendum changes are in `Addenda_Change_History`.
- Missing values are left empty, never filled with guesses. Amounts are never summed across currencies or record types.
- `source_document_id`, `source_page`, `source_quote` point to the evidence for PDF-derived rows.
- Content: operational records plus any document-derived records already stored from the former approval workflow. New document extraction output is not included; use the per-document extraction workbook below. `Obligations_Milestones` lists stored milestones, reports, and utilization certificates; invoices, budgets, and receipts are financial records, not obligations.
- Historical addendum changes remain visible in `Addenda_Change_History`; new extracted changes do not alter operational agreement values.
- Formatting: frozen header row, filters, `yyyy-mm-dd` dates, `#,##0.00` numbers, sized columns, an `About` sheet. `Partners` is the first (active) sheet, so it re-imports through `POST /api/import/preview`.

## Document-specific extraction workbook

Download from `GET /api/documents/{id}/export/workbook` after extraction. This workbook contains document-scoped Groq/deterministic output and does not create or update operational records. It is an ordinary editable `.xlsx`; edits made in Excel are not synchronized back to ObliGOT.

| Sheet | Contents |
|---|---|
| `About` | Filename, document type, extraction status/mode, links, and limitations |
| `Fields` | Target, field, extracted value, text as written, warnings, and source evidence |
| `Clauses` | Type, heading, summary, verbatim text, legal-review flag, and source evidence |
| `Financial_Terms` | Term, description, amount/currency/basis, dates, conditions, and evidence |
| `Obligations` | Type, title, frequency, fixed/relative deadline details, owner, and evidence |
| `Programme_Scope` | Dimension, value, target, location/period, and evidence |
| `Tables` | Extracted-table index and notes; each table also has its own editable `Table_n` sheet with source page and cell values |
| `Page_Readings` | Physical/printed page, reading method, page classification, transcript, and reading notes |
| `Extraction_Notes` | Extraction/validation findings and affected pages or fields |
| `Addendum_Changes` | Any generated addendum comparison output; these values are not applied to agreements |

Evidence columns retain physical page, printed page when known, section, source quote, whether it was found, verification error, and basis (`text_layer`, `ai_transcript`, or OCR). Evidence based on AI transcription still needs comparison with the scanned source image. Workbook cells are not protected.

## Partners

| Column | Type | Required | Notes |
|---|---|---|---|
| `partner_id` | id | yes |  |
| `name` | text | yes |  |
| `legal_entity_name` | text |  |  |
| `category` | text |  |  |
| `status` | enum | yes | `prospect`, `qualification`, `active`, `on_hold`, `closed` |
| `owner` | text |  |  |
| `contact_name` | text |  |  |
| `contact_email` | text |  |  |
| `source_label` | text | yes |  |

## Agreements

| Column | Type | Required | Notes |
|---|---|---|---|
| `agreement_id` | id | yes |  |
| `partner_id` | id | yes | → Partners |
| `reference_number` | text |  |  |
| `title` | text | yes |  |
| `status` | enum | yes | `draft`, `under_review`, `active`, `expired`, `closed` |
| `execution_date` | date |  |  |
| `effective_date` | date |  |  |
| `start_date` | date |  |  |
| `expiry_date` | date |  |  |
| `renewal_terms` | text |  |  |
| `renewal_status` | enum |  | `none`, `in_progress`, `renewed`, `not_renewing` |
| `signed_copy` | enum |  | `received`, `pending`, `unknown` |
| `owner` | text |  |  |
| `amended` | bool | yes |  |
| `unresolved_changes` | integer | yes |  |
| `source_document_id` | id |  |  |
| `source_page` | integer |  |  |
| `source_quote` | text |  |  |
| `review_state` | enum | yes | `proposed`, `needs_review`, `approved`, `rejected`, `deferred` |
| `source_label` | text | yes |  |

## Programmes_Projects

| Column | Type | Required | Notes |
|---|---|---|---|
| `project_id` | id | yes |  |
| `agreement_id` | id |  | → Agreements |
| `partner_id` | id |  | → Partners |
| `name` | text | yes |  |
| `status` | enum | yes | `planned`, `active`, `on_hold`, `completed`, `closed` |
| `start_date` | date |  |  |
| `end_date` | date |  |  |
| `owner` | text |  |  |
| `source_label` | text | yes |  |

## Programme_Scope

| Column | Type | Required | Notes |
|---|---|---|---|
| `scope_id` | id | yes |  |
| `project_id` | id | yes | → Programmes_Projects |
| `agreement_id` | id | yes | → Agreements |
| `dimension` | enum | yes | `state`, `region`, `course`, `training_type`, `beneficiary_group`, `target` |
| `value` | text | yes |  |
| `target_value` | number |  |  |
| `target_unit` | text |  |  |
| `source_document_id` | id |  |  |
| `source_page` | integer |  |  |
| `source_quote` | text |  |  |
| `review_state` | enum | yes | `proposed`, `needs_review`, `approved`, `rejected`, `deferred` |

## Financial_Terms

| Column | Type | Required | Notes |
|---|---|---|---|
| `term_id` | id | yes |  |
| `agreement_id` | id | yes | → Agreements |
| `partner_id` | id | yes | → Partners |
| `term_type` | enum | yes | `total_commitment`, `annual_budget`, `tranche`, `payment_term`, `partner_contribution`, `other` |
| `description` | text | yes |  |
| `amount` | number |  |  |
| `currency` | text |  |  |
| `basis` | enum | yes | `confirmed`, `estimated`, `ceiling`, `unspecified` |
| `financial_year` | text |  |  |
| `payer` | text |  |  |
| `due_date` | date |  |  |
| `condition` | text |  |  |
| `amended` | bool | yes |  |
| `source_document_id` | id |  |  |
| `source_page` | integer |  |  |
| `source_quote` | text |  |  |
| `review_state` | enum | yes | `proposed`, `needs_review`, `approved`, `rejected`, `deferred` |

## Obligations_Milestones

| Column | Type | Required | Notes |
|---|---|---|---|
| `obligation_id` | id | yes |  |
| `agreement_id` | id |  | → Agreements |
| `partner_id` | id | yes | → Partners |
| `project_id` | id |  | → Programmes_Projects |
| `obligation_type` | enum | yes | `milestone`, `deliverable`, `progress_report`, `impact_report`, `utilization_certificate`, `fund_release`, `other` |
| `title` | text | yes |  |
| `frequency` | enum | yes | `once`, `monthly`, `quarterly`, `half_yearly`, `annual`, `unspecified` |
| `due_date` | date |  |  |
| `status` | text |  |  |
| `owner` | text |  |  |
| `amended` | bool | yes |  |
| `source_document_id` | id |  |  |
| `source_page` | integer |  |  |
| `source_quote` | text |  |  |
| `review_state` | enum | yes | `proposed`, `needs_review`, `approved`, `rejected`, `deferred` |

## Clauses

| Column | Type | Required | Notes |
|---|---|---|---|
| `clause_id` | id | yes |  |
| `agreement_id` | id | yes | → Agreements |
| `document_id` | id | yes |  |
| `clause_type` | enum | yes | `responsibility`, `payment_condition`, `fund_release`, `reporting`, `utilization_certificate`, `renewal`, `termination`, `penalty`, `exception`, `audit`, `confidentiality`, `other` |
| `heading` | text |  |  |
| `summary` | text | yes |  |
| `verbatim_text` | text | yes |  |
| `source_page` | integer | yes |  |
| `needs_legal_review` | bool | yes |  |
| `review_state` | enum | yes | `proposed`, `needs_review`, `approved`, `rejected`, `deferred` |

## Addenda_Change_History

| Column | Type | Required | Notes |
|---|---|---|---|
| `change_id` | id | yes |  |
| `agreement_id` | id | yes | → Agreements |
| `addendum_document_id` | id | yes |  |
| `target` | enum | yes | `partner`, `agreement`, `programme`, `scope`, `financial_term`, `obligation`, `clause` |
| `target_id` | id |  |  |
| `field` | text | yes |  |
| `prior_value` | text |  |  |
| `proposed_value` | text |  |  |
| `amendment_date` | date |  |  |
| `effective_date` | date |  |  |
| `source_page` | integer | yes |  |
| `source_quote` | text | yes |  |
| `status` | enum | yes | `proposed`, `approved`, `rejected`, `unresolved` |
| `reviewed_by` | text |  |  |
| `reviewed_at` | datetime |  |  |
| `note` | text |  |  |

## Validation_Review_Issues

| Column | Type | Required | Notes |
|---|---|---|---|
| `issue_id` | id | yes |  |
| `document_id` | id | yes |  |
| `severity` | enum | yes | `error`, `warning` |
| `code` | text | yes |  |
| `message` | text | yes |  |
| `related_id` | id |  |  |
| `status` | enum | yes | `open`, `resolved`, `deferred` |
| `resolution` | text |  |  |
