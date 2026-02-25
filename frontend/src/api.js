const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

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
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (err) {
    const msg = String(err?.message || err || "");
    if (msg.toLowerCase().includes("failed to fetch")) {
      throw new Error(`Falha de conexão com a API (${API_BASE}). Verifique se o backend está ativo.`);
    }
    throw err;
  }
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

export function getMe() {
  return req("/me");
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

export function getDashboardExpenses(params = {}) {
  return req(`/dashboard/expenses-by-category${qs(params)}`);
}

export function getDashboardAccountBalance(params = {}) {
  return req(`/dashboard/account-balance${qs(params)}`);
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

export function deleteTransaction(id) {
  return req(`/transactions/${id}`, {
    method: "DELETE",
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

export function updateAllInvestPrices(payload = {}) {
  return req("/invest/prices/update-all", {
    method: "POST",
    body: JSON.stringify(payload),
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
