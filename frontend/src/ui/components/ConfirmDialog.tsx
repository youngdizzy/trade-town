/**
 * Design Bible Chapter 67 (TTOS) Part 3 — the first reusable
 * confirm-before-you-act dialog in this codebase (research before this
 * was built confirmed no such pattern existed anywhere in
 * frontend/src/ui/components; every other destructive/high-stakes
 * action here — Founders retirement, order cancellation, Treasury
 * withdrawals — fires immediately). Built generic from the start so the
 * Emergency Stop control isn't the only caller forever, but it's the
 * one real caller today. z-[60] — one layer above the Command Center's
 * own z-50 overlay, since a confirmation must be reachable and
 * clickable even while the Command Center (or Settings, or any other
 * z-50 overlay) is open, matching this feature's own "always
 * accessible" requirement.
 */
export function ConfirmDialog({
  title,
  body,
  confirmLabel,
  cancelLabel = "Cancel",
  tone = "red",
  onConfirm,
  onCancel,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "red" | "gold";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="pointer-events-auto absolute inset-0 z-[60] flex items-center justify-center bg-black/70 font-pixel text-[11px]">
      <div className="w-80 rounded bg-panel p-5 text-center text-parchment shadow-pixel">
        <h2 className={tone === "red" ? "mb-3 text-bearish" : "mb-3 text-gold"}>{title}</h2>
        <p className="mb-4 leading-relaxed opacity-90">{body}</p>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={onConfirm}
            className={`rounded px-3 py-2 text-ink shadow-pixel transition-colors ${tone === "red" ? "bg-bearish hover:bg-bearish/80" : "bg-gold hover:bg-gold/80"}`}
          >
            {confirmLabel}
          </button>
          <button type="button" onClick={onCancel} className="rounded bg-panelLight px-3 py-2 text-parchment shadow-pixel transition-colors hover:bg-panelLight/70">
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
