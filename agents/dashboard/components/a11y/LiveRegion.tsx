"use client";

type Politeness = "polite" | "assertive";
type Relevant =
  | "additions"
  | "additions text"
  | "additions removals"
  | "all"
  | "removals"
  | "removals additions"
  | "removals text"
  | "text"
  | "text additions"
  | "text removals";

export function LiveRegion({
  message,
  politeness = "polite",
  atomic = true,
  relevant = "additions text",
  busy,
}: {
  message: string;
  politeness?: Politeness;
  atomic?: boolean;
  relevant?: Relevant;
  busy?: boolean;
}) {
  const role = politeness === "assertive" ? "alert" : "status";
  return (
    <div
      className="sr-only"
      role={role}
      aria-live={politeness}
      aria-atomic={atomic}
      aria-relevant={relevant}
      aria-busy={busy}
    >
      {message}
    </div>
  );
}

