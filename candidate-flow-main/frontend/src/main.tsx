import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Decision = {
  field?: string;
  selected_value?: unknown;
  selected_source?: string;
  strategy?: string;
  confidence?: number;
  discarded_values?: Array<{ value?: unknown }>;
};

type ConfidenceResult = {
  target?: string;
  score?: number;
  method?: string;
  warnings?: string[];
  breakdown?: { factors?: Array<{ name: string; score: number; weight: number; reason: string }> };
};

type TransformResponse = {
  candidate: Record<string, unknown>;
  confidence: { overall_score?: number; results?: ConfidenceResult[] } & Record<string, unknown>;
  merge_report: { decisions?: Decision[]; warnings?: string[] } & Record<string, unknown>;
  provenance: Array<Record<string, unknown>>;
  processing_summary: {
    sources_processed: number;
    fields_extracted: number;
    fields_normalized: number;
    duplicates_removed: number;
    conflicts_resolved: number;
    overall_confidence: number;
    processing_time_ms: number;
    logs: string[];
  };
};

type UploadKey = "csv" | "ats" | "resume" | "notes" | "config";

const tabs = ["Candidate", "Confidence", "Merge Report", "Provenance", "Explain", "Logs"] as const;

function formatPercent(value?: number | null) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function JsonView({ value }: { value: unknown }) {
  return <pre className="overflow-auto rounded border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-800">{JSON.stringify(value, null, 2)}</pre>;
}

function EmptyState({ title, detail, tone = "neutral" }: { title: string; detail: string; tone?: "neutral" | "error" }) {
  const classes =
    tone === "error"
      ? "rounded border border-red-200 bg-red-50 p-6"
      : "rounded border border-dashed border-slate-300 bg-white p-6";
  return (
    <div className={classes}>
      <div className={tone === "error" ? "text-base font-semibold text-red-900" : "text-base font-semibold text-slate-950"}>{title}</div>
      <div className={tone === "error" ? "mt-1 text-sm text-red-700" : "mt-1 text-sm text-slate-600"}>{detail}</div>
    </div>
  );
}

function SummaryCards({ summary }: { summary: TransformResponse["processing_summary"] }) {
  const items = [
    { label: "Sources", value: summary.sources_processed, detail: "input fragments" },
    { label: "Extracted", value: summary.fields_extracted, detail: "field values" },
    { label: "Normalized", value: summary.fields_normalized, detail: "cleaned values" },
    { label: "Duplicates", value: summary.duplicates_removed, detail: "discarded values" },
    { label: "Conflicts", value: summary.conflicts_resolved, detail: "resolved fields" },
    { label: "Confidence", value: formatPercent(summary.overall_confidence), detail: "overall score" },
    { label: "Time", value: `${summary.processing_time_ms} ms`, detail: "runtime" },
  ];
  return (
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      {items.map((item) => (
        <div key={item.label} className="rounded border border-slate-300 bg-white p-3">
          <div className="text-xs uppercase text-slate-500">{item.label}</div>
          <div className="mt-1 break-words text-2xl font-semibold text-slate-950">{item.value}</div>
          <div className="mt-1 text-xs text-slate-500">{item.detail}</div>
        </div>
      ))}
    </section>
  );
}

function PipelineTimeline({ logs }: { logs: string[] }) {
  if (!logs.length) return <EmptyState title="No timeline yet" detail="Pipeline stages will appear after a transform completes." />;
  return (
    <ol className="rounded border border-slate-300 bg-white p-4">
      {logs.map((log, index) => (
        <li key={`${log}-${index}`} className="flex gap-3 pb-3 last:pb-0">
          <div className="flex flex-col items-center">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-700 text-xs font-semibold text-white">{index + 1}</div>
            {index < logs.length - 1 && <div className="h-full w-px bg-slate-300" />}
          </div>
          <div className="pt-1">
            <div className="text-sm font-medium text-slate-800">{log}</div>
            <div className="text-xs text-slate-500">Stage {index + 1}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function ConfidencePanel({ confidence }: { confidence: TransformResponse["confidence"] }) {
  const score = Number(confidence.overall_score ?? 0);
  const percent = Math.round(score * 100);
  const results = confidence.results ?? [];
  const factors = results.flatMap((result) => result.breakdown?.factors ?? []);
  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <div className="rounded border border-slate-300 bg-white p-4">
        <div className="text-sm font-medium text-slate-600">Overall Confidence</div>
        <div className="mt-2 text-4xl font-semibold text-slate-950">{percent}%</div>
        <div className="mt-4 h-3 rounded bg-slate-200">
          <div className="h-3 rounded bg-teal-700" style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
        </div>
        <div className="mt-3 text-xs text-slate-500">{results.length} scored target{results.length === 1 ? "" : "s"}</div>
      </div>
      <div className="rounded border border-slate-300 bg-white p-4">
        <div className="mb-3 text-sm font-semibold text-slate-950">Confidence Factors</div>
        {factors.length === 0 ? <EmptyState title="No factors" detail="Confidence factor details were not returned." /> : (
          <div className="grid gap-2">
            {factors.map((factor, index) => (
              <div key={`${factor.name}-${index}`} className="grid gap-2 rounded border border-slate-200 p-3 md:grid-cols-[180px_1fr_90px]">
                <div className="font-medium text-slate-900">{factor.name}</div>
                <div className="text-sm text-slate-600">
                  {factor.reason}
                  <div className="mt-1 h-2 rounded bg-slate-100">
                    <div className="h-2 rounded bg-teal-700" style={{ width: `${Math.round(factor.score * 100)}%` }} />
                  </div>
                </div>
                <div className="text-right text-sm font-semibold text-slate-900">
                  {formatPercent(factor.score)}
                  <div className="text-xs font-normal text-slate-500">w {factor.weight}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MergeTable({ decisions }: { decisions: Decision[] }) {
  if (!decisions.length) return <EmptyState title="No merge decisions" detail="Merge decisions will appear when candidate fields are resolved." />;
  return (
    <div className="overflow-auto rounded border border-slate-300 bg-white">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase text-slate-600">
          <tr>
            <th className="p-3">Field</th>
            <th className="p-3">Selected</th>
            <th className="p-3">Rejected</th>
            <th className="p-3">Source</th>
            <th className="p-3">Rule</th>
            <th className="p-3 text-right">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {decisions.map((decision, index) => (
            <tr key={`${decision.field}-${index}`} className="border-t border-slate-200 align-top">
              <td className="p-3 font-medium text-slate-950">{decision.field}</td>
              <td className="p-3 text-slate-700">{formatValue(decision.selected_value)}</td>
              <td className="p-3 text-slate-600">{(decision.discarded_values ?? []).map((item) => formatValue(item.value)).join(", ") || "None"}</td>
              <td className="p-3 text-slate-700">{decision.selected_source ?? "None"}</td>
              <td className="p-3 text-slate-600">{decision.strategy ?? "None"}</td>
              <td className="p-3 text-right font-semibold text-slate-900">{formatPercent(decision.confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExplainPanel({
  field,
  setField,
  explanation,
  onExplain,
}: {
  field: string;
  setField: (value: string) => void;
  explanation: Record<string, unknown> | null;
  onExplain: () => void;
}) {
  const rows: Array<[string, unknown]> = explanation
    ? [
        ["Field", explanation.field],
        ["Selected value", explanation.selected_value],
        ["Rejected values", Array.isArray(explanation.rejected_values) ? explanation.rejected_values.join(", ") : explanation.rejected_values],
        ["Source", explanation.source],
        ["Rule", explanation.rule],
        ["Confidence", typeof explanation.confidence === "number" ? formatPercent(explanation.confidence) : explanation.confidence],
        ["Support Count", explanation.support_count],
        ["Consensus Score", typeof explanation.consensus_score === "number" ? formatPercent(explanation.consensus_score) : explanation.consensus_score],
        ["Supporting Sources", Array.isArray(explanation.supporting_sources) ? explanation.supporting_sources.join(", ") : explanation.supporting_sources],
        ["Aggregate Confidence", typeof explanation.aggregate_confidence === "number" ? formatPercent(explanation.aggregate_confidence) : explanation.aggregate_confidence],
      ]
    : [];

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap gap-2 rounded border border-slate-300 bg-white p-3">
        <input className="min-w-56 rounded border border-slate-300 px-3 py-2" value={field} onChange={(event) => setField(event.target.value)} />
        <button className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white" onClick={onExplain}>Explain</button>
      </div>
      {!explanation && <EmptyState title="No explanation selected" detail="Enter a field name such as full_name, emails, or skills and request an explanation." />}
      {explanation && (
        <div className="overflow-auto rounded border border-slate-300 bg-white">
          <table className="w-full min-w-[520px] border-collapse text-left text-sm">
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={label} className="border-b border-slate-200 last:border-b-0">
                  <th className="w-44 bg-slate-50 p-3 text-xs uppercase text-slate-600">{label}</th>
                  <td className="p-3 text-slate-800">{formatValue(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {explanation && <JsonView value={explanation.pipeline_history ?? []} />}
    </div>
  );
}

function App() {
  const [files, setFiles] = useState<Partial<Record<UploadKey, File>>>({});
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("Candidate");
  const [result, setResult] = useState<TransformResponse | null>(null);
  const [field, setField] = useState("full_name");
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadItems: Array<{ key: UploadKey; label: string; accept: string }> = [
    { key: "csv", label: "CSV", accept: ".csv,text/csv" },
    { key: "ats", label: "ATS", accept: ".json,application/json" },
    { key: "resume", label: "Resume", accept: ".pdf,application/pdf" },
    { key: "notes", label: "Notes", accept: ".txt,text/plain" },
    { key: "config", label: "Config", accept: ".json,application/json" },
  ];

  const summary = result?.processing_summary;
  const canTransform = useMemo(() => Object.keys(files).some((key) => key !== "config"), [files]);

  async function transform() {
    setIsLoading(true);
    setError(null);
    setExplanation(null);
    const form = new FormData();
    Object.entries(files).forEach(([key, file]) => {
      if (file) form.append(key, file);
    });

    try {
      const response = await fetch("/api/transform", { method: "POST", body: form });
      if (!response.ok) throw new Error(await response.text());
      setResult((await response.json()) as TransformResponse);
      setActiveTab("Candidate");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transform failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function explain() {
    setError(null);
    setExplanation(null);
    try {
      const response = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field }),
      });
      if (!response.ok) throw new Error(await response.text());
      setExplanation((await response.json()) as Record<string, unknown>);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explain failed");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
      <header className="border-b border-slate-300 pb-4">
        <h1 className="text-2xl font-semibold tracking-normal text-slate-950">Candidate Flow</h1>
      </header>

      <section className="grid gap-3 md:grid-cols-5">
        {uploadItems.map((item) => (
          <label key={item.key} className="rounded border border-slate-300 bg-white p-3 text-sm font-medium text-slate-700">
            <span>{item.label}</span>
            <input
              className="mt-2 block w-full text-xs text-slate-600 file:mr-3 file:rounded file:border-0 file:bg-teal-700 file:px-3 file:py-2 file:text-white"
              type="file"
              accept={item.accept}
              onChange={(event) => setFiles((current) => ({ ...current, [item.key]: event.target.files?.[0] }))}
            />
            <div className="mt-2 truncate text-xs text-slate-500">{files[item.key]?.name ?? "No file selected"}</div>
          </label>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-3 border-b border-slate-300 pb-4">
        <button
          className="rounded bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={!canTransform || isLoading}
          onClick={transform}
        >
          {isLoading ? "Transforming" : "Transform"}
        </button>
        {!canTransform && <span className="text-sm text-slate-600">Upload at least one source file.</span>}
      </div>

      {error && <EmptyState title="Request failed" detail={error} tone="error" />}
      {summary && <SummaryCards summary={summary} />}
      {summary && <PipelineTimeline logs={summary.logs} />}

      <nav className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`rounded border px-3 py-2 text-sm ${activeTab === tab ? "border-teal-700 bg-teal-50 text-teal-900" : "border-slate-300 bg-white text-slate-700"}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </nav>

      <section className="min-h-72">
        {!result && <EmptyState title="Awaiting transform output" detail="Upload candidate sources and run Transform to inspect candidate, confidence, merge, provenance, and logs." />}
        {result && activeTab === "Candidate" && <JsonView value={result.candidate} />}
        {result && activeTab === "Confidence" && <ConfidencePanel confidence={result.confidence} />}
        {result && activeTab === "Merge Report" && <MergeTable decisions={result.merge_report.decisions ?? []} />}
        {result && activeTab === "Provenance" && (result.provenance.length ? <JsonView value={result.provenance} /> : <EmptyState title="No provenance" detail="No provenance records were returned for this transform." />)}
        {result && activeTab === "Logs" && <PipelineTimeline logs={result.processing_summary.logs} />}
        {result && activeTab === "Explain" && <ExplainPanel field={field} setField={setField} explanation={explanation} onExplain={explain} />}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
