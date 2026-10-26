import test from "node:test";
import assert from "node:assert/strict";
import { quoteFailureLabel, quoteUpdateNotice } from "../src/quoteUpdateNotice.js";

test("all failed is a warning and never claims an update succeeded", () => {
  const notice = quoteUpdateNotice({ ok: false, saved: 0, total: 2, report: [{ ok: false }, { ok: false }] });
  assert.equal(notice.level, "warning");
  assert.match(notice.message, /Nenhuma cotação foi salva/);
});
test("partial update retains saved count and reports failures", () => {
  const notice = quoteUpdateNotice({ saved: 1, total: 2, report: [{ ok: true }, { ok: false }] });
  assert.equal(notice.level, "warning");
  assert.match(notice.message, /1\/2/);
  assert.match(notice.message, /Falhas: 1/);
});
test("empty selection is not an update success", () => {
  assert.equal(quoteUpdateNotice({ saved: 0, total: 0, report: [] }).level, "warning");
});
test("all saved with available FX is successful", () => {
  assert.equal(quoteUpdateNotice({ ok: true, saved: 2, total: 2, report: [{ ok: true }, { ok: true }], fx: { ok: true } }).level, "success");
});
test("FX failure remains visible even when prices were saved", () => {
  const notice = quoteUpdateNotice({ saved: 1, total: 1, report: [{ ok: true }], fx: { ok: false } });
  assert.equal(notice.level, "warning");
  assert.match(notice.message, /PTAX indisponível/);
});

test("status uses structured codes and remains compatible with older reports", () => {
  assert.equal(quoteFailureLabel({ ok: false, error_code: "rate_limited" }), "Limite de consumo");
  assert.equal(quoteFailureLabel({ ok: false, error_code: "no_data" }), "Sem dados");
  assert.equal(quoteFailureLabel({ ok: false, error_code: "access_denied" }), "Acesso ao provedor negado");
  assert.equal(quoteFailureLabel({ ok: false }), "Erro");
  assert.equal(quoteFailureLabel({ ok: true }), "Atualizada");
  assert.equal(quoteFailureLabel({ ok: true, cache_hit: true }), "Em cache");
});

test("cached references are disclosed without claiming a new provider response", () => {
  const notice = quoteUpdateNotice({ saved: 1, total: 1, report: [{ ok: true, cache_hit: true }] });
  assert.match(notice.message, /Referências em cache: 1/);
});
