import { cloneElement, useEffect, useId, useState } from "react";

export default function EntryField({ label, children, error = "", idPrefix = "tx-entry" }) {
  const generatedId = useId();
  const [nativeError, setNativeError] = useState("");
  useEffect(() => setNativeError(""), [idPrefix, children.props.name, children.props.value, children.props.disabled]);
  const id = children.props.id || `${idPrefix}-${children.props.name || generatedId}`;
  const message = error || nativeError;
  return (
    <div className="tx-entry-field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, {
        id,
        "aria-invalid": Boolean(message),
        "aria-describedby": message ? `${id}-error` : undefined,
        onInvalid(event) {
          setNativeError(event.currentTarget.validationMessage);
          children.props.onInvalid?.(event);
        },
        onChange(event) {
          setNativeError("");
          children.props.onChange?.(event);
        },
      })}
      {message ? <span className="tx-field-error" id={`${id}-error`}>{message}</span> : null}
    </div>
  );
}
