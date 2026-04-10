interface MapMessageOverlayProps {
  message: string;
  tone?: "default" | "error";
}

export function MapMessageOverlay({
  message,
  tone = "default",
}: MapMessageOverlayProps) {
  const className =
    tone === "error"
      ? "max-w-md rounded-2xl bg-rose-600/90 px-5 py-3 text-center text-sm text-white shadow-2xl"
      : "rounded-2xl bg-slate-950/76 px-5 py-3 text-sm text-white shadow-2xl";

  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
      <span className={className}>{message}</span>
    </div>
  );
}
