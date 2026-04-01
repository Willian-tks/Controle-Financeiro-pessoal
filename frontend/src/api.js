const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export function getToken() {
  return localStorage.getItem("auth_token") || "";
}

export function setToken(token) {
  localStorage.setItem("auth_token", token);
}

export function clearToken() {
  localStorage.removeItem("auth_token");
}

async function req(path, options = {}) {
  const { timeoutMs, ...fetchOptions } = options || {};
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const controller = new AbortController();
  const timeoutHandle =
    Number.isFinite(Number(timeoutMs)) && Number(timeoutMs) > 0
      ? setTimeout(() => controller.abort(), Number(timeoutMs))
      : null;
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers, signal: controller.signal });
  } catch (err) {
    if (timeoutHandle) clearTimeout(timeoutHandle);
    if (err?.name === "AbortError") {
      throw new Error("Tempo limite excedido ao consultar a API.");
    }
    const msg = String(err?.message || err || "");
    if (msg.toLowerCase().includes("failed to fetch")) {
      throw new Error(`Falha de conexão com a API (${API_BASE}). Verifique se o backend está ativo.`);
    }
    throw err;
  }
  if (timeoutHandle) clearTimeout(timeoutHandle);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function login(email, password) {
  return req("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function forgotPassword(email) {
  return req("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token, newPassword) {
  return req("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function getMe() {
  return req("/me");
}

export function updateMeProfile(payload) {
  return req("/me", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getWorkspaces() {
  return req("/workspaces");
}

export function switchWorkspace(workspaceId) {
  return req("/workspaces/switch", {
    method: "POST",
    body: JSON.stringify({ workspace_id: Number(workspaceId) }),
  });
}

export function renameCurrentWorkspace(payload) {
  return req("/workspaces/current", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getWorkspaceMembers() {
  return req("/workspaces/members");
}

export function createWorkspaceMember(payload) {
  return req("/workspaces/members", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWorkspaceMemberPermissions(memberUserId, payload) {
  return req(`/workspaces/members/${memberUserId}/permissions`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteWorkspaceMember(memberUserId) {
  return req(`/workspaces/members/${memberUserId}`, {
    method: "DELETE",
  });
}

export function getAdminWorkspaces() {
  return req("/admin/workspaces");
}

export function getAdminRuntimeChecks() {
  return req("/admin/runtime-checks");
}

export function createAdminWorkspace(payload) {
  return req("/admin/workspaces", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminWorkspaceStatus(workspaceId, payload) {
  return req(`/admin/workspaces/${workspaceId}/status`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateUserGlobalRole(userId, payload) {
  return req(`/admin/users/${userId}/global-role`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getAccounts() {
  return req("/accounts");
}

export function createAccount(payload) {
  return req("/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAccount(id, payload) {
  return req(`/accounts/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAccount(id) {
  return req(`/accounts/${id}`, {
    method: "DELETE",
  });
}

export function getCards() {
  return req("/cards");
}

export function createCard(payload) {
  return req("/cards", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCard(id, payload) {
  return req(`/cards/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteCard(id) {
  return req(`/cards/${id}`, {
    method: "DELETE",
  });
}

export function getCardInvoices(params = {}) {
  return req(`/card-invoices${qs(params)}`);
}

export function payCardInvoice(id, payload) {
  return req(`/card-invoices/${id}/pay`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCategories() {
  return req("/categories");
}

export function createCategory(payload) {
  return req("/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCategory(id, payload) {
  return req(`/categories/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteCategory(id) {
  return req(`/categories/${id}`, {
    method: "DELETE",
  });
}

export function getLists(params = {}) {
  return req(`/lists${qs(params)}`);
}

export function getList(id) {
  return req(`/lists/${id}`);
}

export function createList(payload) {
  return req("/lists", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateList(id, payload) {
  return req(`/lists/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteList(id) {
  return req(`/lists/${id}`, {
    method: "DELETE",
  });
}

export function archiveList(id) {
  return req(`/lists/${id}/archive`, {
    method: "PATCH",
    body: JSON.stringify({}),
  });
}

export function createListItem(listId, payload) {
  return req(`/lists/${listId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateListItem(id, payload) {
  return req(`/items/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteListItem(id) {
  return req(`/items/${id}`, {
    method: "DELETE",
  });
}

export function toggleListItemAcquired(id, acquired) {
  return req(`/items/${id}/toggle-acquired`, {
    method: "PATCH",
    body: JSON.stringify({ acquired: Boolean(acquired) }),
  });
}

export function getKpis() {
  return req("/dashboard/kpis");
}

function qs(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && String(v).trim() !== "") {
      sp.set(k, String(v));
    }
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function getDashboardKpis(params = {}) {
  return req(`/dashboard/kpis${qs(params)}`);
}

export function getDashboardMonthly(params = {}) {
  return req(`/dashboard/monthly${qs(params)}`);
}

export function getDashboardWealthMonthly(params = {}) {
  return req(`/dashboard/wealth-monthly${qs(params)}`);
}

export function getDashboardExpenses(params = {}) {
  return req(`/dashboard/expenses-by-category${qs(params)}`);
}

export function getDashboardAccountBalance(params = {}) {
  return req(`/dashboard/account-balance${qs(params)}`);
}

export function getDashboardCommitmentsSummary(params = {}) {
  return req(`/dashboard/commitments-summary${qs(params)}`);
}

export function getTransactions(params = {}) {
  return req(`/transactions${qs({ limit: 200, ...params })}`);
}

export function createTransaction(payload) {
  return req("/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteTransaction(id, params = {}) {
  return req(`/transactions/${id}${qs(params)}`, {
    method: "DELETE",
  });
}

export function deleteCreditCommitment(id, params = {}) {
  return req(`/credit-commitments/${id}${qs(params)}`, {
    method: "DELETE",
  });
}

export function settleCommitmentTransaction(id, payload) {
  return req(`/transactions/${id}/settle-commitment`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getInvestMeta() {
  return req("/invest/meta");
}

export function getInvestAssets() {
  return req("/invest/assets");
}

export function createInvestAsset(payload) {
  return req("/invest/assets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateInvestAsset(id, payload) {
  return req(`/invest/assets/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateInvestAssetFairValue(id, payload) {
  return req(`/invest/assets/${id}/fair-value`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function uploadInvestAssetValuationReport(id, file) {
  const token = getToken();
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/invest/assets/${id}/valuation-report`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function downloadInvestAssetValuationReport(id) {
  const token = getToken();
  const res = await fetch(`${API_BASE}/invest/assets/${id}/valuation-report`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  const disposition = String(res.headers.get("Content-Disposition") || "");
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: await res.blob(),
    fileName: match?.[1] || `avaliacao-${id}.pdf`,
  };
}

export function updateInvestManualAssetValue(id, payload) {
  return req(`/invest/assets/${id}/manual-update`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteInvestAsset(id) {
  return req(`/invest/assets/${id}`, {
    method: "DELETE",
  });
}

export function getInvestTrades() {
  return req("/invest/trades");
}

export function createInvestTrade(payload) {
  return req("/invest/trades", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteInvestTrade(id) {
  return req(`/invest/trades/${id}`, {
    method: "DELETE",
  });
}

export function getInvestPortfolio() {
  return req("/invest/portfolio");
}

export function getInvestSummary() {
  return req("/invest/summary");
}

export async function downloadInvestReport(params = {}) {
  const token = getToken();
  const suffix = qs(params);
  const res = await fetch(`${API_BASE}/invest/report${suffix}`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  const disposition = String(res.headers.get("Content-Disposition") || "");
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: await res.blob(),
    fileName: match?.[1] || "relatorio-investimentos.html",
  };
}

export function getInvestIncomes() {
  return req("/invest/incomes");
}

export function createInvestIncome(payload) {
  return req("/invest/incomes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteInvestIncome(id) {
  return req(`/invest/incomes/${id}`, {
    method: "DELETE",
  });
}

export function getInvestPrices() {
  return req("/invest/prices?limit=300");
}

export function upsertInvestPrice(payload) {
  return req("/invest/prices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAllInvestPrices(payload = {}, options = {}) {
  return req("/invest/prices/update-all", {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs: options?.timeoutMs,
  });
}

export function getInvestPriceJobStatus() {
  return req("/invest/prices/job-status");
}

export function getInvestBenchmarkSettings() {
  return req("/invest/benchmarks/settings");
}

export function upsertInvestBenchmarkSetting(payload = {}) {
  return req("/invest/benchmarks/settings/upsert", {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
}

export function syncActiveInvestBenchmarks(payload = {}) {
  return req("/invest/benchmarks/sync-active", {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
}

export function getInvestIndexRates(params = {}) {
  const search = new URLSearchParams();
  if (params.index_name) search.set("index_name", String(params.index_name));
  if (params.date_from) search.set("date_from", String(params.date_from));
  if (params.date_to) search.set("date_to", String(params.date_to));
  if (params.limit) search.set("limit", String(params.limit));
  if (params.auto_sync) search.set("auto_sync", "true");
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return req(`/invest/index-rates${suffix}`);
}

export function getInvestPortfolioTimeseries(params = {}) {
  const search = new URLSearchParams();
  if (params.date_from) search.set("date_from", String(params.date_from));
  if (params.date_to) search.set("date_to", String(params.date_to));
  if (params.asset_class) search.set("asset_class", String(params.asset_class));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return req(`/invest/portfolio/timeseries${suffix}`);
}

export function updateAllInvestRentability(payload = {}, timeoutMs = 0) {
  return req("/invest/rentability/update-all", {
    method: "POST",
    body: JSON.stringify(payload || {}),
    timeoutMs: Number(timeoutMs) || 0,
  });
}

export function getInvestRentabilityDivergenceReport(payload = {}, timeoutMs = 0) {
  return req("/invest/rentability/divergence-report", {
    method: "POST",
    body: JSON.stringify(payload || {}),
    timeoutMs: Number(timeoutMs) || 0,
  });
}

async function uploadCsv(path, file, previewOnly = false) {
  const token = getToken();
  const fd = new FormData();
  fd.append("file", file);
  fd.append("preview_only", previewOnly ? "true" : "false");
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export function importTransactionsCsv(file, previewOnly = false) {
  return uploadCsv("/import/transactions-csv", file, previewOnly);
}

export function importAssetsCsv(file, previewOnly = false) {
  return uploadCsv("/import/assets-csv", file, previewOnly);
}

export function importTradesCsv(file, previewOnly = false) {
  return uploadCsv("/import/trades-csv", file, previewOnly);
}
