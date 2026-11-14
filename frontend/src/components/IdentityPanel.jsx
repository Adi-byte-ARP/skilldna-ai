import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Icon from "../ui/Icon";
import { SkeletonLines } from "../ui/Skeleton";

/*
 * Shows every uploaded document, the name read from it, and whether it was counted.
 * The rule is stated plainly: only documents that match the account holder are counted.
 */
const STATUS = {
  processed: { label: "Counted", tone: "teal" },
  name_mismatch: { label: "Different name", tone: "coral" },
  name_unverified: { label: "No name found", tone: "violet" },
  duplicate: { label: "Already counted", tone: "neutral" },
  superseded: { label: "Replaced", tone: "neutral" },
  failed: { label: "Could not read", tone: "coral" },
  pending: { label: "Processing", tone: "neutral" },
};

const SOURCE_ICON = {
  resume: "document",
  github: "code",
  linkedin: "link",
  certificate: "certificate",
};

export default function IdentityPanel({ documents, accountName, loading }) {
  const counted = (documents || []).filter((d) => d.status === "processed");
  const shown = (documents || []).slice(0, 8);

  return (
    <Card as="section" aria-label="Identity check" className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">Identity check</p>
          <p className="mt-1 font-display text-lg font-medium">
            {counted.length > 0
              ? `${counted.length} document${counted.length === 1 ? "" : "s"} belong to ${accountName}`
              : "No document is counted yet"}
          </p>
        </div>
        {counted.length > 0 && <Badge tone="teal">Verified</Badge>}
      </div>
      <p className="text-xs leading-relaxed text-ink-soft">
        Only documents that carry your name are counted. A document for someone else is kept here, marked, and excluded from your score.
      </p>

      {loading ? (
        <SkeletonLines lines={3} />
      ) : shown.length === 0 ? (
        <p className="text-sm text-ink-soft">Upload a resume, GitHub profile, LinkedIn export or certificate to start the check.</p>
      ) : (
        <ul className="divide-y divide-line">
          {shown.map((d) => {
            const meta = STATUS[d.status] || STATUS.pending;
            return (
              <li key={d.id} className="flex items-center gap-3 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-paper-dim text-ink-soft">
                  <Icon name={SOURCE_ICON[d.source] || "document"} className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{d.file || d.source}</p>
                  <p className="truncate text-xs text-ink-soft">
                    {d.source === "linkedin" && d.status === "name_unverified"
                      ? "LinkedIn uploads must show your name and Skills section in the same file."
                      : d.name_read ? `Name read: ${d.name_read}` : "No name read from this file"}
                  </p>
                </div>
                <Badge tone={meta.tone}>{meta.label}</Badge>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
