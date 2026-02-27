// ── API response types (mirror Python Pydantic schemas) ──────────────────────

export type PDFType = "text" | "scanned" | "hybrid" | "encrypted" | "unknown";

export type CriterionType = "inclusion" | "exclusion";

export type DisqualificationPower =
  | "very_high"
  | "high"
  | "medium"
  | "low"
  | "unknown";

export interface EligibilityCriterion {
  id: string;
  criterion_type: CriterionType;
  text: string;
  source_page: number | null;
  source_section: string | null;
  disqualification_power: DisqualificationPower;
  has_temporal_condition: boolean;
  has_numeric_threshold: boolean;
  has_conditional_logic: boolean;
  is_ambiguous: boolean;
  notes: string;
}

export interface ExtractionMetadata {
  model_used: string;
  protocol_version: string | null;
  extraction_confidence: number;
  section_found: boolean;
  section_name: string | null;
  warnings: string[];
}

export interface ExtractedCriteria {
  protocol_title: string | null;
  sponsor: string | null;
  phase: string | null;
  therapeutic_area: string | null;
  criteria: EligibilityCriterion[];
  top_disqualifiers: EligibilityCriterion[];
  metadata: ExtractionMetadata;
}

export type ProtocolJobStatus = "processing" | "ready" | "error";

export interface ProtocolStatus {
  protocol_id: string;
  status: ProtocolJobStatus;
  extracted_criteria: ExtractedCriteria | null;
  error: string | null;
}

export interface UploadResponse {
  protocol_id: string;
  filename: string;
  status: string;
}

export type ScreeningDecision =
  | "disqualified"
  | "passed_prescreen"
  | "escalate";

export interface FailedCriterion {
  criterion: EligibilityCriterion;
  reason: string;
}

export interface ScreeningResult {
  patient_id: string;
  protocol_id: string;
  decision: ScreeningDecision;
  confidence: number;
  failed_criteria: FailedCriterion[];
  passed_criteria_count: number;
  escalation_reason: string | null;
  model_used: string | null;
}

export interface ScreeningRequest {
  patient_id: string;
  protocol_id: string;
  patient_data: Record<string, unknown>;
}
