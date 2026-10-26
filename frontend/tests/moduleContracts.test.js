import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import { buildSync } from "esbuild";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { formatBrl, formatLocalizedNumber, formatIsoDatePtBr, formatIsoDateTimePtBr } from "../src/formatters.js";

function loadComponent(name) {
  const result = buildSync({
    entryPoints: [fileURLToPath(new URL(`../src/${name}.jsx`, import.meta.url))],
    bundle: true, write: false, platform: "node", format: "cjs",
    packages: "external", jsx: "automatic",
  });
  const module = { exports: {} };
  runInNewContext(result.outputFiles[0].text, { module, exports: module.exports, require: createRequire(import.meta.url) });
  return module.exports.default;
}

test("shared formatting preserves currency, precision and date fallbacks", () => {
  assert.equal(formatBrl(1234.5), (1234.5).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }));
  assert.equal(formatBrl(NaN), "R$ 0,00");
  assert.equal(formatLocalizedNumber(1.23456, 4), "1,2346");
  assert.equal(formatLocalizedNumber(Infinity), "");
  assert.equal(formatIsoDatePtBr("20261026"), "26/10/2026");
  assert.equal(formatIsoDatePtBr("2026-10-26T13:30:00Z"), "26/10/2026");
  assert.equal(formatIsoDatePtBr(""), "-");
  assert.equal(formatIsoDateTimePtBr("invalid"), "");
});

test("dashboard preserves totals, permissions and navigation callbacks", () => {
  const Dashboard = loadComponent("DashboardOverview");
  const onOpenTransactions = () => {};
  const onOpenCommitments = () => {};
  const tree = Dashboard({
    accountsTotal: 100, currentKpi: { saldo: 20, receitas: 50, despesas: 30 },
    commitmentsAging: { aVencer: 10, vencidos: 5 }, trendEnd: 200,
    trendDelta: -10, trendPct: -5, trendDirection: "negative",
    canViewLancamentos: false, onOpenTransactions, onOpenCommitments,
  });
  const buttons = [];
  function walk(node) {
    if (!node || typeof node !== "object") return;
    if (node.type === "button") buttons.push(node);
    React.Children.forEach(node.props?.children, walk);
  }
  walk(tree);
  assert.equal(buttons.length, 2);
  assert.equal(buttons[0].props.onClick, onOpenTransactions);
  assert.equal(buttons[1].props.onClick, onOpenCommitments);
  assert.ok(buttons.every(button => button.props.disabled));
  const html = renderToStaticMarkup(tree);
  assert.match(html, /100,00/);
  assert.match(html, /15,00/);
  assert.match(html, /Sem base mensal/);
  assert.match(html, /5.0% vs/);
});

test("quote report preserves empty state and cached quote metadata", () => {
  const Report = loadComponent("QuoteUpdateReport");
  assert.match(renderToStaticMarkup(React.createElement(Report, { investPriceUpdateReport: [], investAssets: [] })), /Sem execução nesta sessão/);
  const html = renderToStaticMarkup(React.createElement(Report, {
    investAssets: [{ id: 1, currency: "USD" }],
    investPriceUpdateReport: [{ asset_id: "1", symbol: "TEST", ok: true, price: 12.3456, px_date: "2026-10-26", src: "provider", cache_hit: true, cache_age_s: 120 }],
  }));
  for (const text of ["USD", "12,3456", "26/10/2026", "provider", "Cache (2 min)"]) assert.ok(html.includes(text));
});
