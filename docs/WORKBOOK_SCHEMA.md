# Workbook schema

Standard Excel representation of **approved, normalized** partnership data. Generated from `backend/app/workbook.py` (the source of truth; tests check it against the models). Download it from `GET /api/export/workbook` (Step P3c).

- Each sheet's first column is its stable ID. `→ Sheet` marks a reference to that sheet's ID column.
- Operational columns hold the latest approved effective values. Original values and every addendum change are in `Addenda_Change_History`.
- Missing values are left empty, never filled with guesses. Amounts are never summed across currencies or record types.
- `source_document_id`, `source_page`, `source_quote` point to the evidence for PDF-derived rows.
- Content: operational records (staff-entered, or created by approving a document) plus approved document values; pending, rejected, and deferred proposals are never exported. `Obligations_Milestones` lists approved document obligations (with the status of the record each created) and the other milestones, reports, and utilization certificates; invoices, budgets, and receipts are financial records, not obligations, and are not in this workbook. `Validation_Review_Issues` lists every review issue with its status.
- Until addenda are handled (P4), `amended` is FALSE, `unresolved_changes` is 0, and `Addenda_Change_History` is empty.
- Formatting: frozen header row, filters, `yyyy-mm-dd` dates, `#,##0.00` numbers, sized columns, an `About` sheet. `Partners` is the first (active) sheet, so it re-imports through `POST /api/import/preview`.

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
