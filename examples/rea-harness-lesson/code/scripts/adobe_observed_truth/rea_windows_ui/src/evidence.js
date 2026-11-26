// Evidence for Windows native UI observations, created by REA 6.8.0's own createEvidence exactly
// as REA's macOS provider does (NativeMacOSProvider.js: createAnalysisExecution with the report
// and its limitations), so identity and schema come from REA's code.
import { createEvidence } from "rea-agents/dist/domain/evidence.js";
import {
  createEvidenceBundle,
  serializeEvidenceBundle,
} from "rea-agents/dist/domain/evidenceBundle.js";

/** Public identity committed by Windows native UI observations (cf. "native-macos"). */
export const NATIVE_WINDOWS_PROVIDER = Object.freeze({
  id: "native-windows",
  name: "Windows native UI observation",
  version: "0.1.0",
});

/** One observation or scenario report as REA Evidence about the active target. */
export function observationEvidence({ target, operation, parameters, report }) {
  return createEvidence(target, NATIVE_WINDOWS_PROVIDER, {
    operation,
    parameters,
    result: report,
    limitations: report.limitations,
  });
}

/** A canonical REA Evidence bundle, the form import_evidence_bundle reads. */
export function evidenceBundleText(records) {
  return serializeEvidenceBundle(createEvidenceBundle(records));
}
