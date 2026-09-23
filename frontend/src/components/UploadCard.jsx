import { useRef, useState } from "react";

const STATUS_STYLES = {
  idle: "border-line",
  loading: "border-helix-teal",
  done: "border-helix-teal bg-helix-teal-soft/40",
  error: "border-signal-coral bg-signal-coral-soft/40",
};

export default function UploadCard({
  icon,
  title,
  description,
  accept,
  buttonLabel = "Upload",
  onSubmit, // file mode: (file) => Promise<SubmissionOut>. multiFile mode: (files[]) => Promise<SubmissionOut[]>
  mode = "file", // "file" | "text" | "multiFile"
  textPlaceholder,
}) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState(null);
  const [textValue, setTextValue] = useState("");
  const inputRef = useRef(null);

  const summarizeOne = (result) => {
    if (result?.status === "failed") {
      return { ok: false, text: result.error_message || "Couldn't process this file." };
    }
    const count = result?.extracted_skills?.length ?? 0;
    return { ok: true, text: `Found ${count} skill${count === 1 ? "" : "s"}.` };
  };

  const handleFile = async (file) => {
    if (!file) return;
    setStatus("loading");
    setMessage(null);
    try {
      const result = await onSubmit(file);
      const summary = summarizeOne(result);
      setStatus(summary.ok ? "done" : "error");
      setMessage(summary.text);
    } catch (e) {
      setStatus("error");
      setMessage(e.message || "Something went wrong.");
    }
  };

  const handleMultiFile = async (fileList) => {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;
    setStatus("loading");
    setMessage(null);
    try {
      const results = await onSubmit(files);
      const summaries = results.map(summarizeOne);
      const failedCount = summaries.filter((s) => !s.ok).length;
      const totalSkills = results.reduce((sum, r) => sum + (r?.extracted_skills?.length ?? 0), 0);

      if (failedCount === 0) {
        setStatus("done");
        setMessage(
          `Processed ${files.length} file${files.length === 1 ? "" : "s"} — found ${totalSkills} skill${totalSkills === 1 ? "" : "s"} total.`
        );
      } else if (failedCount === files.length) {
        setStatus("error");
        setMessage(summaries[0]?.text || "None of these could be processed.");
      } else {
        setStatus("done");
        setMessage(
          `Processed ${files.length - failedCount}/${files.length} files (${failedCount} failed) — found ${totalSkills} skill${totalSkills === 1 ? "" : "s"} total.`
        );
      }
    } catch (e) {
      setStatus("error");
      setMessage(e.message || "Something went wrong.");
    }
  };

  const handleTextSubmit = async () => {
    if (!textValue.trim()) return;
    await handleFile(textValue.trim());
  };

  return (
    <div
      className={`rounded-2xl border p-5 transition-colors duration-300 bg-paper ${STATUS_STYLES[status]}`}
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="text-xl leading-none mt-0.5">{icon}</span>
        <div>
          <h3 className="font-display font-medium text-base">{title}</h3>
          <p className="text-ink-soft text-sm leading-snug">{description}</p>
        </div>
      </div>

      {mode === "file" && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={status === "loading"}
            className="w-full font-display text-sm font-medium py-2.5 rounded-full bg-ink text-paper hover:bg-helix-teal transition-colors duration-300 disabled:opacity-50"
          >
            {status === "loading" ? "Reading…" : buttonLabel}
          </button>
        </>
      )}

      {mode === "multiFile" && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            multiple
            className="hidden"
            onChange={(e) => handleMultiFile(e.target.files)}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={status === "loading"}
            className="w-full font-display text-sm font-medium py-2.5 rounded-full bg-ink text-paper hover:bg-helix-teal transition-colors duration-300 disabled:opacity-50"
          >
            {status === "loading" ? "Reading…" : buttonLabel}
          </button>
          <p className="mt-1.5 text-[11px] text-ink-soft font-mono">You can select more than one file</p>
        </>
      )}

      {mode === "text" && (
        <div className="flex gap-2">
          <input
            type="text"
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            placeholder={textPlaceholder}
            onKeyDown={(e) => e.key === "Enter" && handleTextSubmit()}
            className="flex-1 rounded-full border border-line px-4 py-2 text-sm font-mono focus:outline-none focus:border-helix-teal bg-white"
          />
          <button
            onClick={handleTextSubmit}
            disabled={status === "loading"}
            className="font-display text-sm font-medium px-4 py-2 rounded-full bg-ink text-paper hover:bg-helix-teal transition-colors duration-300 disabled:opacity-50 whitespace-nowrap"
          >
            {status === "loading" ? "…" : buttonLabel}
          </button>
        </div>
      )}

      {message && (
        <p
          className={`mt-2.5 text-xs font-mono ${
            status === "error" ? "text-signal-coral" : "text-helix-teal"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
