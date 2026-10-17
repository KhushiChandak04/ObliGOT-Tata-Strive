import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

/** Modal built on the native <dialog>: focus trapping, Escape to close, and inert background come from the browser. */
export default function Dialog({ open, title, onClose, children, wide = false }: { open: boolean; title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={`dialog${wide ? " dialog-wide" : ""}`} aria-labelledby={titleId} onClose={onClose} onCancel={(e) => { e.preventDefault(); onClose(); }}>
    <div className="dialog-header"><h2 id={titleId}>{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={17} aria-hidden /></button></div>
    {open && children}
  </dialog>;
}
