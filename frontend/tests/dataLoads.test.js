import test from "node:test";
import assert from "node:assert/strict";
import { settleDataLoads } from "../src/dataLoads.js";

test("partial failure preserves successful sources and marks unavailable data", async () => {
  const state = { accounts: ["old"], categories: [] };
  const errors = await settleDataLoads([
    { label: "contas", load: async () => { throw new Error("offline"); }, apply: rows => { state.accounts = rows; }, fallback: [] },
    { label: "categorias", load: async () => ["food"], apply: rows => { state.categories = rows; }, fallback: [] },
  ]);
  assert.deepEqual(errors, ["contas"]);
  assert.deepEqual(state, { accounts: [], categories: ["food"] });
});

test("successful retry replaces the fallback and clears unavailable sources", async () => {
  let offline = true;
  let rows = [];
  const loads = [{ label: "lançamentos", load: async () => {
    if (offline) throw new Error("offline");
    return [{ id: 1 }];
  }, apply: value => { rows = value; }, fallback: [] }];
  assert.deepEqual(await settleDataLoads(loads), ["lançamentos"]);
  offline = false;
  assert.deepEqual(await settleDataLoads(loads), []);
  assert.deepEqual(rows, [{ id: 1 }]);
});

test("empty successful response is not reported as unavailable", async () => {
  let rows = null;
  assert.deepEqual(await settleDataLoads([
    { label: "contas", load: async () => [], apply: value => { rows = value; }, fallback: [] },
  ]), []);
  assert.deepEqual(rows, []);
});
