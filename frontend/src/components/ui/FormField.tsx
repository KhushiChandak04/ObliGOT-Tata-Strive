import { cloneElement, type ReactElement } from "react";

/**
 * Labelled form control. The label names the control; the hint or error is linked with
 * aria-describedby so it is announced as a description, not as part of the field's name.
 */
export default function FormField({ id, label, error, hint, children }: { id: string; label: string; error?: string; hint?: string; children: ReactElement }) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return <div className={`form-field${error ? " has-error" : ""}`}>
    <label htmlFor={id}>{label}</label>
    {cloneElement(children, { id, "aria-invalid": Boolean(error) || undefined, "aria-describedby": describedBy })}
    {error ? <small className="field-error" id={`${id}-error`}>{error}</small> : hint && <small id={`${id}-hint`}>{hint}</small>}
  </div>;
}
