export const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function formatIsoDateTimePtBr(value) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function formatLocalizedNumber(value, fractionDigits = 2) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  return num.toLocaleString("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatBrl(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "R$ 0,00";
  return num.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatIsoDatePtBr(value) {
  const raw = String(value || "").trim();
  if (!raw) return "-";
  const compact = raw.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (compact) {
    return `${compact[3]}/${compact[2]}/${compact[1]}`;
  }
  const iso = raw.slice(0, 10);
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return raw;
  return `${m[3]}/${m[2]}/${m[1]}`;
}
