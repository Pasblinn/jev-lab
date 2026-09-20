// Compact structured result a worker hands back to the orchestrator.
export type WorkerStatus = "SUCCESS" | "PARTIAL" | "BLOCKED" | "FAILED";
export type Check = "PASS" | "FAIL" | "NOT_RUN";

export interface WorkerResult {
  taskId: string;
  status: WorkerStatus;
  implemented: string[];
  filesChanged: string[];
  validation: { tests: Check; typecheck: Check; lint: Check; build: Check };
  decisions: string[];
  risks: string[];
  unresolved: string[];
  diffStats: { added: number; removed: number };
  workerConfidence: "low" | "medium" | "high";
}

export function checksGreen(r: WorkerResult): boolean {
  return r.validation.tests === "PASS" && r.validation.typecheck !== "FAIL" &&
    r.validation.lint !== "FAIL" && r.validation.build !== "FAIL";
}
