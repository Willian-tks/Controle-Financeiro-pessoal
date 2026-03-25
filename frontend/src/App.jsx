import { Fragment, Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import brandLogo from "./icons/DOMUS2.png";
import icDashboard from "./icons/dashboard.png";
import icContas from "./icons/contas.png";
import icLancamentos from "./icons/lancamentos.png";
import icInvestimento from "./icons/investimento.png";
import icGerenciador from "./icons/gerenciador.png";
import icImportarCsv from "./icons/importar-CSV.png";
import icUsuario from "./icons/usuario.png";
import icDespesa from "./icons/despesa_2.png";
import icReceita from "./icons/receita_2.png";
import icSaldo from "./icons/saldo_2.png";
import downloadIcon from "./download.svg";
import bankInterLogo from "./banks/banco-inter-logo.svg";
import bankBradescoLogo from "./banks/bradesco-logo.svg";
import bankItauLogo from "./banks/itau-logo.svg";
import bankNubankLogo from "./banks/nubank-logo.svg";
import bankSantanderLogo from "./banks/santander-logo.svg";
import bankMercadoPagoLogo from "./banks/mercado-pago-logo.svg";
import cardVisaLogo from "./cards/visa-17.svg";
import cardMasterLogo from "./cards/mastercard-18.svg";
import cardModelBlack from "./cards/Black.png";
import cardModelGold from "./cards/Gold.png";
import cardModelPlatinum from "./cards/Platinum.png";
import cardModelOrange from "./cards/Orange.png";
import cardModelVioleta from "./cards/Violeta.png";
import cardModelVermelho from "./cards/Vermelho.png";
import { ResponsiveContainer, PieChart, Pie, Sector, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis, Cell, LineChart, Line, Legend } from "recharts";
import {
  clearToken,
  createCard,
  createAccount,
  createCategory,
  createInvestAsset,
  createInvestIncome,
  createInvestTrade,
  createTransaction,
  deleteCard,
  deleteAccount,
  deleteCategory,
  deleteCreditCommitment,
  deleteInvestAsset,
  deleteInvestIncome,
  deleteInvestTrade,
  deleteTransaction,
  getAccounts,
  getCardInvoices,
  getCards,
  getCategories,
  getDashboardAccountBalance,
  getDashboardCommitmentsSummary,
  getDashboardExpenses,
  getDashboardKpis,
  getDashboardWealthMonthly,
  getInvestAssets,
  getInvestIncomes,
  getInvestMeta,
  getInvestIndexRates,
  getInvestPortfolio,
  getInvestPortfolioTimeseries,
  getInvestPriceJobStatus,
  getInvestPrices,
  getInvestRentabilityDivergenceReport,
  getInvestSummary,
  getInvestTrades,
  getKpis,
  getMe,
  updateMeProfile,
  getWorkspaces,
  renameCurrentWorkspace,
  switchWorkspace,
  getWorkspaceMembers,
  createWorkspaceMember,
  updateWorkspaceMemberPermissions,
  deleteWorkspaceMember,
  forgotPassword,
  getAdminWorkspaces,
  createAdminWorkspace,
  updateAdminWorkspaceStatus,
  getTransactions,
  importAssetsCsv,
  importTradesCsv,
  importTransactionsCsv,
  login,
  payCardInvoice,
  resetPassword,
  settleCommitmentTransaction,
  setToken,
  updateAllInvestRentability,
  updateAllInvestPrices,
  updateInvestAsset,
  updateInvestAssetFairValue,
  uploadInvestAssetValuationReport,
  downloadInvestAssetValuationReport,
  updateInvestManualAssetValue,
  upsertInvestPrice,
  updateCard,
  updateAccount,
  updateCategory,
} from "./api";
const DashboardCharts = lazy(() => import("./DashboardCharts"));

const PAGES = [
  "Dashboard",
  "Contas",
  "Lançamentos",
  "Investimentos",
  "Gerenciador",
  "Importar CSV",
];
const PAGE_PERMISSION_MODULE = {
  Dashboard: "dashboard",
  Contas: "contas",
  "Lançamentos": "lancamentos",
  Investimentos: "investimentos",
  Gerenciador: "contas",
  "Importar CSV": "relatorios",
};

const PAGE_SUBTITLES = {
  Gerenciador: "Cadastros e manutenção de contas, categorias e cartões",
  Contas: "Visão rápida das contas cadastradas",
  "Lançamentos": "Registro e histórico das movimentações",
  Dashboard: "KPIs, gráficos e saldos por conta",
  "Importar CSV": "Prévia e importação de dados em lote",
  Investimentos: "Ativos, operações, proventos, cotações e carteira",
};

const INVEST_TABS = ["Resumo", "Rentabilidade", "Ativos", "Operações", "Proventos", "Cotações"];
const USER_OBJECTIVE_OPTIONS = [
  { value: "accumulate", label: "Acumular" },
  { value: "hold", label: "Segurar" },
  { value: "reduce", label: "Reduzir" },
  { value: "exit", label: "Sair" },
];
const RENTABILITY_WINDOW_OPTIONS = [
  { value: "6m", label: "6 meses" },
  { value: "12m", label: "12 meses" },
  { value: "24m", label: "24 meses" },
  { value: "all", label: "Desde o início" },
];
const MANAGER_TABS = ["Cadastro de contas", "Cadastro de categorias", "Cadastro cartão de crédito"];
const QUOTE_GROUP_OPTIONS = ["Ações BR", "FIIs", "Stocks", "Cripto"];

function getAuthLocationState() {
  if (typeof window === "undefined") {
    return { mode: "login", token: "" };
  }
  const url = new URL(window.location.href);
  const token = String(url.searchParams.get("token") || "").trim();
  const pathname = String(url.pathname || "").toLowerCase();
  if (token && pathname.endsWith("/reset-password")) {
    return { mode: "reset", token };
  }
  if (token && String(url.searchParams.get("mode") || "").trim().toLowerCase() === "reset-password") {
    return { mode: "reset", token };
  }
  return { mode: "login", token: "" };
}

function clearPasswordResetLocation() {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.delete("token");
  url.searchParams.delete("mode");
  if (String(url.pathname || "").toLowerCase().endsWith("/reset-password")) {
    url.pathname = url.pathname.replace(/\/reset-password\/?$/i, "/");
  }
  const nextUrl = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState({}, "", nextUrl);
}
const MANUAL_PRICE_CLASS_OPTIONS = ["Ações BR", "FIIs", "Stocks US", "BDRs", "Cripto"];
const INVEST_RENTABILITY_TIMEOUT_MS = 6000;
const INVEST_DIVERGENCE_TIMEOUT_MS = 8000;
const INVEST_RENTABILITY_MIN_SYNC_INTERVAL_MS = 60000;
const RENTABILITY_TYPE_OPTIONS = [
  { value: "PREFIXADO", label: "Prefixado" },
  { value: "PCT_CDI", label: "% do CDI" },
  { value: "PCT_SELIC", label: "% da SELIC" },
  { value: "CDI_SPREAD", label: "CDI + X" },
  { value: "SELIC_SPREAD", label: "SELIC + X" },
  { value: "IPCA_SPREAD", label: "IPCA + X" },
  { value: "MANUAL", label: "Manual" },
];
const DONUT_COLORS = ["#f4c84b", "#4e7ff3", "#73d39f", "#ef6f5c", "#9a7df9"];
const CARD_MODELS = ["Black", "Gold", "Platinum", "Orange", "Violeta", "Vermelho"];
const PAGE_ICONS = {
  Dashboard: icDashboard,
  Contas: icContas,
  "Lançamentos": icLancamentos,
  Investimentos: icInvestimento,
  Gerenciador: icGerenciador,
  "Importar CSV": icImportarCsv,
};
const WORKSPACE_PERMISSION_MODULES = [
  "dashboard",
  "lancamentos",
  "investimentos",
  "relatorios",
  "contas",
];
const WORKSPACE_PERMISSION_ALL_MODULES = [...WORKSPACE_PERMISSION_MODULES, "usuarios"];
const WORKSPACE_PERMISSION_LABELS = {
  dashboard: "Dashboard",
  lancamentos: "Lançamentos",
  investimentos: "Investimentos",
  relatorios: "Relatórios",
  contas: "Contas",
};
const PERMISSION_ACTION_FIELD = {
  view: "can_view",
  add: "can_add",
  edit: "can_edit",
  delete: "can_delete",
};
const RENTABILITY_TYPE_LABELS = {
  PREFIXADO: "Prefixado",
  PCT_CDI: "% do CDI",
  PCT_SELIC: "% da SELIC",
  CDI_SPREAD: "CDI + X",
  SELIC_SPREAD: "SELIC + X",
  IPCA_SPREAD: "IPCA + X",
  MANUAL: "Manual",
};
const BENCHMARK_BY_ASSET_CLASS = {
  "Ações BR": { benchmark: "IBOV", ready: true, indexName: "IBOV", seriesMode: "level" },
  FIIs: { benchmark: "IFIX", ready: true, indexName: "IFIX", seriesMode: "level" },
  "Stocks US": { benchmark: "S&P 500", ready: true, indexName: "SP500", seriesMode: "level" },
  "Renda Fixa": { benchmark: "CDI", ready: true, indexName: "CDI", seriesMode: "rate" },
  "Tesouro Direto": { benchmark: "CDI", ready: true, indexName: "CDI", seriesMode: "rate" },
  Cripto: { benchmark: "Índice Cripto", ready: true, indexName: "CRYPTO", seriesMode: "level" },
  BDRs: { benchmark: "Índice Internacional", ready: true, indexName: "GLOBAL", seriesMode: "level" },
  Fundos: { benchmark: "CDI", ready: true, indexName: "CDI", seriesMode: "rate" },
  Coe: { benchmark: "CDI", ready: true, indexName: "CDI", seriesMode: "rate" },
};
const INCOME_TYPE_COLORS = {
  Dividendos: "#5dd39e",
  JCP: "#66d5ff",
  Juros: "#f4c84b",
  Cupom: "#ff9b71",
  "Rend. RF": "#8f7dff",
  "Aluguel (FII)": "#ff7aa2",
};
const TX_STATUS_FILTER_OPEN = "__open_commitments__";

function getCurrentMonthRange() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const from = new Date(year, month, 1);
  const to = new Date(year, month + 1, 0);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { from: fmt(from), to: fmt(to) };
}

function parseIsoDate(value) {
  if (!value) return null;
  const dt = new Date(`${value}T00:00:00`);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function shiftMonthStart(date, offsetMonths) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return null;
  return new Date(date.getFullYear(), date.getMonth() + offsetMonths, 1);
}

function formatIsoDate(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatIsoDateTimePtBr(value) {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  return dt.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function isIsoDateWithinRange(value, from, to) {
  const date = String(value || "").trim();
  if (!date) return false;
  if (from && date < from) return false;
  if (to && date > to) return false;
  return true;
}

function buildDashboardWealthFilters(filters) {
  const fromDate = parseIsoDate(filters?.date_from);
  const toDate = parseIsoDate(filters?.date_to);
  if (!fromDate || !toDate) return filters;

  const now = new Date();
  const isCurrentMonthOnly =
    fromDate.getFullYear() === toDate.getFullYear() &&
    fromDate.getMonth() === toDate.getMonth() &&
    fromDate.getFullYear() === now.getFullYear() &&
    fromDate.getMonth() === now.getMonth();

  if (!isCurrentMonthOnly) {
    return filters;
  }

  const shiftedStart = shiftMonthStart(toDate, -5);
  return {
    ...filters,
    date_from: formatIsoDate(shiftedStart),
  };
}

function normalizeAccountType(value) {
  const raw = String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  if (raw === "cartao") return "Cartao";
  if (raw === "corretora") return "Corretora";
  if (raw === "banco") return "Banco";
  if (raw === "dinheiro") return "Dinheiro";
  return String(value || "").trim();
}

function normalizeText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function sanitizeDigits(value) {
  return String(value || "").replace(/\D/g, "");
}

function addThousandsSeparator(value) {
  return String(value || "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function formatCurrencyInputValue(value) {
  const digits = sanitizeDigits(value);
  if (!digits) return "";
  const padded = digits.padStart(3, "0");
  const cents = padded.slice(-2);
  const integerDigits = padded.slice(0, -2).replace(/^0+(?=\d)/, "") || "0";
  return `${addThousandsSeparator(integerDigits)},${cents}`;
}

function formatLocalizedNumber(value, fractionDigits = 2) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  return num.toLocaleString("pt-BR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function parseLocaleNumber(value) {
  const raw = String(value || "").trim();
  if (!raw) return NaN;
  let normalized = raw.replace(/\s/g, "").replace(/[^\d,.-]/g, "");
  if (normalized.includes(",")) {
    normalized = normalized.replace(/\./g, "").replace(",", ".");
  }
  const num = Number(normalized);
  return Number.isFinite(num) ? num : NaN;
}

function sanitizeIntegerInputValue(value, maxDigits = 3) {
  return sanitizeDigits(value).slice(0, maxDigits);
}

function sanitizeDecimalInputValue(value, options = {}) {
  const { maxDecimals = 2, maxIntegerDigits = 12 } = options;
  const raw = String(value || "").replace(/\./g, ",");
  const cleaned = raw.replace(/[^\d,]/g, "");
  const commaIndex = cleaned.indexOf(",");
  if (commaIndex === -1) {
    return cleaned.slice(0, maxIntegerDigits);
  }
  const integerPart = cleaned.slice(0, commaIndex).replace(/\D/g, "").slice(0, maxIntegerDigits) || "0";
  const decimalPart = cleaned
    .slice(commaIndex + 1)
    .replace(/\D/g, "")
    .slice(0, maxDecimals);
  const keepComma = cleaned.endsWith(",") && !decimalPart;
  return `${integerPart},${decimalPart}${keepComma ? "" : ""}`;
}

function applyCurrencyMaskInput(event) {
  event.target.value = formatCurrencyInputValue(event.target.value);
}

function applyIntegerMaskInput(event, maxDigits = 3) {
  event.target.value = sanitizeIntegerInputValue(event.target.value, maxDigits);
}

function applyDecimalMaskInput(event, options = {}) {
  event.target.value = sanitizeDecimalInputValue(event.target.value, options);
}

function computeFairValueRange(fairPrice, safetyMarginPct) {
  const fair = Number(fairPrice || 0);
  const margin = Number(safetyMarginPct || 0);
  if (!Number.isFinite(fair) || fair <= 0 || !Number.isFinite(margin) || margin < 0) {
    return { entryPrice: null, ceilingPrice: null };
  }
  const factor = margin / 100;
  return {
    entryPrice: fair * (1 - factor),
    ceilingPrice: fair * (1 + factor),
  };
}

function getFairValueBiasLabel(currentPrice, entryPrice, ceilingPrice) {
  const current = Number(currentPrice || 0);
  const entry = Number(entryPrice || 0);
  const ceiling = Number(ceilingPrice || 0);
  if (!Number.isFinite(current) || current <= 0 || !Number.isFinite(entry) || !Number.isFinite(ceiling)) {
    return { label: "Sem base", tone: "neutral" };
  }
  if (current <= entry) {
    return { label: "Comprar", tone: "buy" };
  }
  if (current >= ceiling) {
    return { label: "Vender", tone: "sell" };
  }
  return { label: "Aguardar", tone: "wait" };
}

function formatUserObjectiveLabel(value) {
  return USER_OBJECTIVE_OPTIONS.find((option) => option.value === String(value || "").trim().toLowerCase())?.label || "-";
}

function getUserObjectiveTone(value) {
  const objective = String(value || "").trim().toLowerCase();
  if (objective === "accumulate") return "buy";
  if (objective === "reduce" || objective === "exit") return "sell";
  if (objective === "hold") return "wait";
  return "neutral";
}

function InvestmentPieGradient(props) {
  const index = Number(props?.index || 0);
  const baseColor = String(props?.fill || DONUT_COLORS[index % DONUT_COLORS.length]);
  const fade = Number(props?.payload?.opacity ?? 1);
  const fillId = `invest-fill-gradient-${index}`;
  const borderId = `invest-border-gradient-${index}`;
  const clipId = `invest-clip-path-${index}`;
  const width = Number(props?.width || 0);
  const height = Number(props?.height || 0);

  return (
    <>
      <defs>
        <radialGradient
          id={fillId}
          cx={props?.cx}
          cy={props?.cy}
          r={props?.outerRadius}
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor={baseColor} stopOpacity={0.08 * fade} />
          <stop offset="100%" stopColor={baseColor} stopOpacity={0.92 * fade} />
        </radialGradient>
        <radialGradient id={borderId} cx={width / 2} cy={height / 2}>
          <stop offset="0%" stopColor={baseColor} stopOpacity={0.18 * fade} />
          <stop offset="100%" stopColor={baseColor} stopOpacity={0.95 * fade} />
        </radialGradient>
        <clipPath id={clipId}>
          <Sector {...props} />
        </clipPath>
      </defs>
      <Sector
        {...props}
        clipPath={`url(#${clipId})`}
        fill={`url(#${fillId})`}
        stroke={`url(#${borderId})`}
        strokeWidth={props?.payload?.isFocused ? 4 : 1}
      />
    </>
  );
}

function normalizeWorkspaceStatus(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (raw === "blocked") return "blocked";
  return "active";
}

function normalizeSignedZero(value, epsilon = 1e-9) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return 0;
  return Math.abs(num) < epsilon ? 0 : num;
}

function buildPermissionsDraft(member) {
  const current = Array.isArray(member?.permissions) ? member.permissions : [];
  const map = new Map(
    current.map((item) => [String(item.module || "").trim().toLowerCase(), item])
  );
  return WORKSPACE_PERMISSION_MODULES.map((module) => {
    const src = map.get(module) || {};
    return {
      module,
      can_view: Boolean(src.can_view),
      can_add: Boolean(src.can_add),
      can_edit: Boolean(src.can_edit),
      can_delete: Boolean(src.can_delete),
    };
  });
}

function buildEffectivePermissionMap(user) {
  const map = {};
  for (const module of WORKSPACE_PERMISSION_ALL_MODULES) {
    map[module] = {
      can_view: false,
      can_add: false,
      can_edit: false,
      can_delete: false,
    };
  }

  const globalRole = String(user?.global_role || "").trim().toUpperCase();
  const workspaceRole = String(user?.workspace_role || "").trim().toUpperCase();
  if (globalRole === "SUPER_ADMIN" || workspaceRole === "OWNER" || workspaceRole === "SUPER_ADMIN") {
    for (const module of Object.keys(map)) {
      map[module] = {
        can_view: true,
        can_add: true,
        can_edit: true,
        can_delete: true,
      };
    }
    return map;
  }

  const rows = Array.isArray(user?.permissions) ? user.permissions : [];
  for (const row of rows) {
    const module = String(row?.module || "").trim().toLowerCase();
    if (!map[module]) continue;
    map[module] = {
      can_view: Boolean(row?.can_view),
      can_add: Boolean(row?.can_add),
      can_edit: Boolean(row?.can_edit),
      can_delete: Boolean(row?.can_delete),
    };
  }
  return map;
}

function hasPermission(permissionMap, module, action = "view") {
  const mod = String(module || "").trim().toLowerCase();
  const act = String(action || "view").trim().toLowerCase();
  const row = permissionMap?.[mod];
  if (!row) return false;
  const field = PERMISSION_ACTION_FIELD[act];
  if (!field) return false;
  return Boolean(row[field]);
}

function formatRentabilityTypeLabel(value) {
  const key = String(value || "").trim().toUpperCase();
  return RENTABILITY_TYPE_LABELS[key] || key || "-";
}

function formatRateDisplay(value, maxDecimals = 8) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  return num.toFixed(maxDecimals).replace(/\.?0+$/, "");
}

function formatValueOriginLabel(value) {
  const key = String(value || "").trim().toLowerCase();
  if (key === "ajuste_manual") return "Ajuste manual";
  if (key === "motor") return "Motor automático";
  if (key === "cotacao") return "Cotação";
  return key || "-";
}

function formatAssetRentabilitySummary(asset) {
  const rentType = String(asset?.rentability_type || "").trim().toUpperCase();
  if (!rentType) return "-";

  if (rentType === "MANUAL") {
    const manualRate = String(asset?.rate_type || "").trim().toUpperCase() === "MANUAL_RETURN"
      ? formatRateDisplay(asset?.rate_value)
      : "";
    return manualRate ? `Manual (${manualRate}%)` : "Manual";
  }
  if (rentType === "PREFIXADO") {
    const fixed = formatRateDisplay(asset?.fixed_rate);
    return fixed ? `${fixed}% a.a.` : "Prefixado";
  }
  if (rentType === "PCT_CDI") {
    const pct = formatRateDisplay(asset?.index_pct);
    return pct ? `${pct}% CDI` : "% do CDI";
  }
  if (rentType === "PCT_SELIC") {
    const pct = formatRateDisplay(asset?.index_pct);
    return pct ? `${pct}% SELIC` : "% da SELIC";
  }
  if (rentType === "CDI_SPREAD") {
    const spread = formatRateDisplay(asset?.spread_rate);
    return spread ? `CDI + ${spread}% a.a.` : "CDI + X";
  }
  if (rentType === "SELIC_SPREAD") {
    const spread = formatRateDisplay(asset?.spread_rate);
    return spread ? `SELIC + ${spread}% a.a.` : "SELIC + X";
  }
  if (rentType === "IPCA_SPREAD") {
    const spread = formatRateDisplay(asset?.spread_rate);
    return spread ? `IPCA + ${spread}% a.a.` : "IPCA + X";
  }
  return formatRentabilityTypeLabel(rentType);
}

function pct(part, total) {
  const p = Number(part || 0);
  const t = Number(total || 0);
  if (!Number.isFinite(p) || !Number.isFinite(t) || t <= 0) return 0;
  return (p / t) * 100;
}

function getBankLogo(name) {
  const n = normalizeText(name);
  if (n.includes("inter")) return bankInterLogo;
  if (n.includes("itau")) return bankItauLogo;
  if (n.includes("bradesco")) return bankBradescoLogo;
  if (n.includes("mercado pago") || n.includes("mercadopago") || n === "mp") return bankMercadoPagoLogo;
  if (n.includes("nubank") || n.includes("nu")) return bankNubankLogo;
  if (n.includes("santander")) return bankSantanderLogo;
  return null;
}

function getCardLogo(brand) {
  const n = normalizeText(brand);
  if (n.includes("master")) return cardMasterLogo;
  return cardVisaLogo;
}

function getCardBackground(model) {
  const map = {
    black: cardModelBlack,
    gold: cardModelGold,
    platinum: cardModelPlatinum,
    orange: cardModelOrange,
    violeta: cardModelVioleta,
    vermelho: cardModelVermelho,
  };
  return map[normalizeText(model)] || cardModelBlack;
}

function getCardBgClass(brand) {
  const n = normalizeText(brand);
  if (n.includes("master")) return "brand-master";
  return "brand-visa";
}

function isFixedIncomeClass(assetClass) {
  const raw = String(assetClass || "").trim();
  const cls = normalizeText(raw).replace(/\s+/g, "_");
  return (
    cls === "renda_fixa" ||
    cls === "tesouro_direto" ||
    cls === "coe" ||
    cls === "fundos"
  );
}

function formatTradeSideLabel(side, assetClass) {
  const s = String(side || "").trim().toUpperCase();
  if (isFixedIncomeClass(assetClass)) {
    if (s === "BUY") return "APLICAÇÃO";
    if (s === "SELL") return "RESGATE";
  }
  return s || "-";
}

function isUsStockClass(assetClass) {
  const cls = normalizeText(assetClass).replace(/\s+/g, "_");
  return cls === "stocks_us" || cls === "stock_us";
}

function isCryptoClass(assetClass) {
  const cls = normalizeText(assetClass).replace(/\s+/g, "_");
  return cls === "crypto" || cls === "cripto";
}

function classKey(assetClass) {
  return normalizeText(assetClass).replace(/\s+/g, "_");
}

function parseOptionalNumberInput(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return { empty: true, value: null };
  const num = parseLocaleNumber(raw);
  if (!Number.isFinite(num)) return { empty: false, value: NaN };
  return { empty: false, value: num };
}

function buildAssetRentabilityPayload({
  isFixedIncome,
  rentabilityType,
  indexPctInput,
  spreadRateInput,
  fixedRateInput,
  manualRateInput,
}) {
  if (!isFixedIncome) {
    return {
      ok: true,
      payload: {
        rentability_type: null,
        index_name: null,
        index_pct: null,
        spread_rate: null,
        fixed_rate: null,
        rate_type: null,
        rate_value: null,
      },
    };
  }

  const rt = String(rentabilityType || "MANUAL").trim().toUpperCase();

  if (rt === "MANUAL") {
    const parsed = parseOptionalNumberInput(manualRateInput);
    if (!parsed.empty && Number.isNaN(parsed.value)) {
      return { ok: false, error: "Informe uma rentabilidade valida para Manual." };
    }
    return {
      ok: true,
      payload: {
        rentability_type: "MANUAL",
        index_name: null,
        index_pct: null,
        spread_rate: null,
        fixed_rate: null,
        rate_type: parsed.empty ? null : "MANUAL_RETURN",
        rate_value: parsed.empty ? null : parsed.value,
      },
    };
  }

  if (rt === "PREFIXADO") {
    const parsed = parseOptionalNumberInput(fixedRateInput);
    if (parsed.empty || Number.isNaN(parsed.value)) {
      return { ok: false, error: "Informe uma taxa anual valida para Prefixado." };
    }
    return {
      ok: true,
      payload: {
        rentability_type: "PREFIXADO",
        index_name: null,
        index_pct: null,
        spread_rate: null,
        fixed_rate: parsed.value,
        rate_type: null,
        rate_value: null,
      },
    };
  }

  if (rt === "PCT_CDI" || rt === "PCT_SELIC") {
    const parsed = parseOptionalNumberInput(indexPctInput);
    if (parsed.empty || Number.isNaN(parsed.value)) {
      return { ok: false, error: "Informe um percentual valido do indice." };
    }
    return {
      ok: true,
      payload: {
        rentability_type: rt,
        index_name: rt === "PCT_CDI" ? "CDI" : "SELIC",
        index_pct: parsed.value,
        spread_rate: null,
        fixed_rate: null,
        rate_type: null,
        rate_value: null,
      },
    };
  }

  if (rt === "CDI_SPREAD" || rt === "SELIC_SPREAD" || rt === "IPCA_SPREAD") {
    const parsed = parseOptionalNumberInput(spreadRateInput);
    if (parsed.empty || Number.isNaN(parsed.value)) {
      return { ok: false, error: "Informe o spread anual valido para a rentabilidade selecionada." };
    }
    const indexName = rt === "CDI_SPREAD" ? "CDI" : rt === "SELIC_SPREAD" ? "SELIC" : "IPCA";
    return {
      ok: true,
      payload: {
        rentability_type: rt,
        index_name: indexName,
        index_pct: null,
        spread_rate: parsed.value,
        fixed_rate: null,
        rate_type: null,
        rate_value: null,
      },
    };
  }

  return { ok: false, error: "Tipo de rentabilidade invalido." };
}

function formatIsoDatePtBr(value) {
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

function formatMonthYearPtBr(value) {
  const raw = String(value || "").trim();
  if (!/^\d{4}-\d{2}$/.test(raw)) return raw;
  const dt = new Date(`${raw}-01T00:00:00`);
  return dt.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

function shiftIsoDateByMonths(value, monthsBack) {
  const raw = String(value || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return "";
  const [year, month, day] = raw.split("-").map(Number);
  const dt = new Date(year, month - 1, day);
  dt.setMonth(dt.getMonth() - Number(monthsBack || 0));
  return dt.toISOString().slice(0, 10);
}

function formatPortfolioQty(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return "-";
  return num.toFixed(8).replace(/\.?0+$/, "");
}

function getCircularDistance(fromIndex, toIndex, total) {
  const size = Number(total || 0);
  if (!Number.isFinite(size) || size <= 0) return 0;
  const forward = (toIndex - fromIndex + size) % size;
  const backward = (fromIndex - toIndex + size) % size;
  if (forward === 0) return 0;
  return forward <= backward ? 1 : -1;
}

function getUserAvatarSrc(user) {
  const avatar = String(user?.avatar_data || "").trim();
  return avatar || icUsuario;
}

export default function App() {
  const defaultMonthRange = getCurrentMonthRange();
  const initialAuthLocation = getAuthLocationState();
  const [authMode, setAuthMode] = useState(initialAuthLocation.mode);
  const [authResetToken, setAuthResetToken] = useState(initialAuthLocation.token);
  const [authError, setAuthError] = useState("");
  const [authInfo, setAuthInfo] = useState("");
  const [forgotEmail, setForgotEmail] = useState("");
  const [resetNewPassword, setResetNewPassword] = useState("");
  const [resetConfirmPassword, setResetConfirmPassword] = useState("");
  const [showResetNewPassword, setShowResetNewPassword] = useState(false);
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false);
  const [loginSyncNotice, setLoginSyncNotice] = useState(null);
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("Dashboard");
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [cards, setCards] = useState([]);
  const [cardInvoices, setCardInvoices] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [dashKpis, setDashKpis] = useState(null);
  const [dashWealthMonthly, setDashWealthMonthly] = useState([]);
  const [dashExpenses, setDashExpenses] = useState([]);
  const [dashCommitments, setDashCommitments] = useState({ a_vencer: 0, vencidos: 0 });
  const [dashAccountBalance, setDashAccountBalance] = useState([]);
  const [dashDateFrom, setDashDateFrom] = useState(defaultMonthRange.from);
  const [dashDateTo, setDashDateTo] = useState(defaultMonthRange.to);
  const [dashAccount, setDashAccount] = useState("");
  const [dashView, setDashView] = useState("caixa");
  const [invoiceDateFrom, setInvoiceDateFrom] = useState(defaultMonthRange.from);
  const [invoiceDateTo, setInvoiceDateTo] = useState(defaultMonthRange.to);
  const [dashMsg, setDashMsg] = useState("");
  const [txMsg, setTxMsg] = useState("");
  const [txAccountId, setTxAccountId] = useState("");
  const [txCategoryId, setTxCategoryId] = useState("");
  const [txMethod, setTxMethod] = useState("PIX");
  const [txRecentCategoryFilterId, setTxRecentCategoryFilterId] = useState("");
  const [txRecentStatusFilter, setTxRecentStatusFilter] = useState("");
  const [txRecentDateFrom, setTxRecentDateFrom] = useState(defaultMonthRange.from);
  const [txRecentDateTo, setTxRecentDateTo] = useState(defaultMonthRange.to);
  const [txFuturePaymentMethod, setTxFuturePaymentMethod] = useState("PIX");
  const [txView, setTxView] = useState("caixa");
  const [txSourceAccountId, setTxSourceAccountId] = useState("");
  const [txCardId, setTxCardId] = useState("");
  const [commitmentEdit, setCommitmentEdit] = useState(null);
  const [cardMsg, setCardMsg] = useState("");
  const [cardCreateName, setCardCreateName] = useState("");
  const [cardCreateBrand, setCardCreateBrand] = useState("");
  const [cardCreateModel, setCardCreateModel] = useState("");
  const [cardCreateType, setCardCreateType] = useState("Credito");
  const [cardCreateAccountId, setCardCreateAccountId] = useState("");
  const [cardCreateDueDay, setCardCreateDueDay] = useState("");
  const [cardCreateCloseDay, setCardCreateCloseDay] = useState("");
  const [cardName, setCardName] = useState("");
  const [cardBrand, setCardBrand] = useState("");
  const [cardModel, setCardModel] = useState("");
  const [cardType, setCardType] = useState("Credito");
  const [cardAccountId, setCardAccountId] = useState("");
  const [cardSourceAccountId, setCardSourceAccountId] = useState("");
  const [cardDueDay, setCardDueDay] = useState("");
  const [cardCloseDay, setCardCloseDay] = useState("");
  const [cardEditId, setCardEditId] = useState("");
  const [importMsg, setImportMsg] = useState("");
  const [importPreview, setImportPreview] = useState([]);
  const [txCsvFile, setTxCsvFile] = useState(null);
  const [assetCsvFile, setAssetCsvFile] = useState(null);
  const [tradeCsvFile, setTradeCsvFile] = useState(null);
  const [investMsg, setInvestMsg] = useState("");
  const [investRentabilityMsg, setInvestRentabilityMsg] = useState("");
  const [investDivergenceMsg, setInvestDivergenceMsg] = useState("");
  const [investDivergenceThreshold, setInvestDivergenceThreshold] = useState("0,10");
  const [investDivergenceReport, setInvestDivergenceReport] = useState([]);
  const [investDivergenceRunning, setInvestDivergenceRunning] = useState(false);
  const [investDivergenceOpen, setInvestDivergenceOpen] = useState(false);
  const [investPriceUpdateReport, setInvestPriceUpdateReport] = useState([]);
  const [investPriceUpdateRunning, setInvestPriceUpdateRunning] = useState(false);
  const [investPriceJobStatus, setInvestPriceJobStatus] = useState(null);
  const [investRentabilitySyncRunning, setInvestRentabilitySyncRunning] = useState(false);
  const [investMeta, setInvestMeta] = useState({ asset_classes: [], asset_sectors: [], income_types: [] });
  const [investAssets, setInvestAssets] = useState([]);
  const [investTrades, setInvestTrades] = useState([]);
  const [investIncomes, setInvestIncomes] = useState([]);
  const [investPrices, setInvestPrices] = useState([]);
  const [investPortfolio, setInvestPortfolio] = useState({ positions: [] });
  const [investSummaryData, setInvestSummaryData] = useState({
    assets_count: 0,
    total_invested: 0,
    total_market: 0,
    total_income: 0,
    total_realized: 0,
    total_unrealized: 0,
    total_return: 0,
    total_return_pct: 0,
    broker_balance: 0,
  });
  const [quoteTimeout, setQuoteTimeout] = useState("25");
  const [quoteWorkers, setQuoteWorkers] = useState("4");
  const [quoteGroup, setQuoteGroup] = useState("");
  const [manualPriceClassFilter, setManualPriceClassFilter] = useState("");
  const [investSummaryClassFilter, setInvestSummaryClassFilter] = useState("");
  const [dashInvestFocusClass, setDashInvestFocusClass] = useState("");
  const [investPortfolioClassFilter, setInvestPortfolioClassFilter] = useState("");
  const [investRentabilityWindow, setInvestRentabilityWindow] = useState("12m");
  const [investBenchmarkClass, setInvestBenchmarkClass] = useState("");
  const [investBenchmarkRates, setInvestBenchmarkRates] = useState([]);
  const [investBenchmarkPortfolioSeries, setInvestBenchmarkPortfolioSeries] = useState([]);
  const [investBenchmarkLoading, setInvestBenchmarkLoading] = useState(false);
  const [investBenchmarkError, setInvestBenchmarkError] = useState("");
  const [investAssetsClassFilter, setInvestAssetsClassFilter] = useState("");
  const [investTradeDateFrom, setInvestTradeDateFrom] = useState(defaultMonthRange.from);
  const [investTradeDateTo, setInvestTradeDateTo] = useState(defaultMonthRange.to);
  const [investIncomeDateFrom, setInvestIncomeDateFrom] = useState(defaultMonthRange.from);
  const [investIncomeDateTo, setInvestIncomeDateTo] = useState(defaultMonthRange.to);
  const [tradeAssetClassFilter, setTradeAssetClassFilter] = useState("");
  const [tradeAssetId, setTradeAssetId] = useState("");
  const [incomeAssetClassFilter, setIncomeAssetClassFilter] = useState("");
  const [incomeAssetId, setIncomeAssetId] = useState("");
  const [tradeSide, setTradeSide] = useState("BUY");
  const [tradeExchangeRate, setTradeExchangeRate] = useState("");
  const [assetCreateClass, setAssetCreateClass] = useState("");
  const [assetCreateRentabilityType, setAssetCreateRentabilityType] = useState("");
  const [assetCreateIndexPct, setAssetCreateIndexPct] = useState("");
  const [assetCreateSpreadRate, setAssetCreateSpreadRate] = useState("");
  const [assetCreateFixedRate, setAssetCreateFixedRate] = useState("");
  const [assetEditId, setAssetEditId] = useState("");
  const [assetEditClassFilter, setAssetEditClassFilter] = useState("");
  const [assetEditSymbol, setAssetEditSymbol] = useState("");
  const [assetEditName, setAssetEditName] = useState("");
  const [assetEditClass, setAssetEditClass] = useState("");
  const [assetEditSector, setAssetEditSector] = useState("Não definido");
  const [assetEditCurrency, setAssetEditCurrency] = useState("BRL");
  const [assetEditBrokerId, setAssetEditBrokerId] = useState("");
  const [assetEditRentabilityType, setAssetEditRentabilityType] = useState("");
  const [assetEditIndexPct, setAssetEditIndexPct] = useState("");
  const [assetEditSpreadRate, setAssetEditSpreadRate] = useState("");
  const [assetEditFixedRate, setAssetEditFixedRate] = useState("");
  const [manualQuoteAssetId, setManualQuoteAssetId] = useState("");
  const [manualQuoteMode, setManualQuoteMode] = useState("rentability");
  const [manualQuoteValue, setManualQuoteValue] = useState("");
  const [manualQuoteDate, setManualQuoteDate] = useState("");
  const [fairValueDrafts, setFairValueDrafts] = useState({});
  const [fairValueInlineEditId, setFairValueInlineEditId] = useState("");
  const [fairValueClassFilter, setFairValueClassFilter] = useState("");
  const [fairValueAssetId, setFairValueAssetId] = useState("");
  const [investTab, setInvestTab] = useState("Resumo");
  const [managerTab, setManagerTab] = useState("Cadastro de contas");
  const [manageMsg, setManageMsg] = useState("");
  const [workspaces, setWorkspaces] = useState([]);
  const [workspaceMsg, setWorkspaceMsg] = useState("");
  const [workspaceSwitchingId, setWorkspaceSwitchingId] = useState("");
  const [workspaceNameDraft, setWorkspaceNameDraft] = useState("");
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [workspaceMembersLoading, setWorkspaceMembersLoading] = useState(false);
  const [workspaceInviteEmail, setWorkspaceInviteEmail] = useState("");
  const [workspaceInviteName, setWorkspaceInviteName] = useState("");
  const [workspacePermDrafts, setWorkspacePermDrafts] = useState({});
  const [workspaceManageMsg, setWorkspaceManageMsg] = useState("");
  const [adminWorkspaces, setAdminWorkspaces] = useState([]);
  const [adminWorkspaceName, setAdminWorkspaceName] = useState("");
  const [adminOwnerEmail, setAdminOwnerEmail] = useState("");
  const [adminOwnerDisplayName, setAdminOwnerDisplayName] = useState("");
  const [adminMsg, setAdminMsg] = useState("");
  const [adminStatusUpdatingId, setAdminStatusUpdatingId] = useState("");
  const [accEditId, setAccEditId] = useState("");
  const [accEditName, setAccEditName] = useState("");
  const [accEditType, setAccEditType] = useState("Banco");
  const [accEditCurrency, setAccEditCurrency] = useState("BRL");
  const [accEditShowOnDashboard, setAccEditShowOnDashboard] = useState(false);
  const [catEditId, setCatEditId] = useState("");
  const [catEditName, setCatEditName] = useState("");
  const [catEditKind, setCatEditKind] = useState("Despesa");
  const [loading, setLoading] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileDisplayName, setProfileDisplayName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");
  const [profileAvatarData, setProfileAvatarData] = useState("");
  const [profileCurrentPassword, setProfileCurrentPassword] = useState("");
  const [profileNewPassword, setProfileNewPassword] = useState("");
  const [profileConfirmPassword, setProfileConfirmPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showProfileCurrentPassword, setShowProfileCurrentPassword] = useState(false);
  const [showProfileNewPassword, setShowProfileNewPassword] = useState(false);
  const [showProfileConfirmPassword, setShowProfileConfirmPassword] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [globalActionNotice, setGlobalActionNotice] = useState(null);
  const [pendingActions, setPendingActions] = useState({});
  const [installPromptEvent, setInstallPromptEvent] = useState(null);
  const [pwaInstalled, setPwaInstalled] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia?.("(display-mode: standalone)")?.matches || window.navigator.standalone === true;
  });
  const [walletCardIndex, setWalletCardIndex] = useState(0);
  const [payModalOpen, setPayModalOpen] = useState(false);
  const [payInvoiceTarget, setPayInvoiceTarget] = useState(null);
  const [payAccountId, setPayAccountId] = useState("");
  const [payDate, setPayDate] = useState("");
  const [invoiceCardFilterId, setInvoiceCardFilterId] = useState("");
  const userMenuRef = useRef(null);
  const valuationReportInputRefs = useRef({});
  const investRentabilityLastSyncRef = useRef(0);
  const investReloadSeqRef = useRef(0);
  const investQuoteAutoRunRef = useRef("");
  const globalActionNoticeTimeoutRef = useRef(null);

  function clearInvestState() {
    setInvestMeta({ asset_classes: [], asset_sectors: [], income_types: [] });
    setInvestAssets([]);
    setInvestTrades([]);
    setInvestIncomes([]);
    setInvestPrices([]);
    setInvestPriceJobStatus(null);
    setInvestPortfolio({ positions: [] });
    setInvestBenchmarkRates([]);
    setInvestBenchmarkPortfolioSeries([]);
    setInvestBenchmarkError("");
    setInvestBenchmarkLoading(false);
    setInvestSummaryData({
      assets_count: 0,
      total_invested: 0,
      total_market: 0,
      total_income: 0,
      total_realized: 0,
      total_unrealized: 0,
      total_return: 0,
      total_return_pct: 0,
      broker_balance: 0,
    });
  }

  useEffect(() => {
    (async () => {
      try {
        const me = await getMe();
        setUser(me);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    return () => {
      if (globalActionNoticeTimeoutRef.current) {
        clearTimeout(globalActionNoticeTimeoutRef.current);
      }
    };
  }, []);

  function showGlobalSuccess(message) {
    const text = String(message || "").trim();
    if (!text) return;
    if (globalActionNoticeTimeoutRef.current) {
      clearTimeout(globalActionNoticeTimeoutRef.current);
    }
    setGlobalActionNotice({ message: text, level: "success" });
    globalActionNoticeTimeoutRef.current = setTimeout(() => {
      setGlobalActionNotice(null);
      globalActionNoticeTimeoutRef.current = null;
    }, 3800);
  }

  function setPendingAction(actionKey, isPending) {
    if (!actionKey) return;
    setPendingActions((prev) => {
      if (isPending) {
        return { ...prev, [actionKey]: true };
      }
      const next = { ...prev };
      delete next[actionKey];
      return next;
    });
  }

  function isPendingAction(actionKey) {
    return Boolean(pendingActions[actionKey]);
  }

  async function withPendingAction(actionKey, job) {
    setPendingAction(actionKey, true);
    try {
      return await job();
    } finally {
      setPendingAction(actionKey, false);
    }
  }

  useEffect(() => {
    if (!profileModalOpen || !user) return;
    setProfileDisplayName(String(user.display_name || ""));
    setProfileEmail(String(user.email || ""));
    setProfileAvatarData(String(user.avatar_data || ""));
    setProfileCurrentPassword("");
    setProfileNewPassword("");
    setProfileConfirmPassword("");
    setProfileMsg("");
  }, [profileModalOpen, user]);

  useEffect(() => {
    setWorkspaceNameDraft(String(user?.workspace_name || ""));
  }, [user?.workspace_id, user?.workspace_name]);

  useEffect(() => {
    function onBeforeInstallPrompt(event) {
      event.preventDefault();
      setInstallPromptEvent(event);
    }

    function onAppInstalled() {
      setPwaInstalled(true);
      setInstallPromptEvent(null);
    }

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        await reloadWorkspaces();
        await reloadAllData();
        if (canViewContas) {
          await reloadCardsData();
        } else {
          setCards([]);
          setCardInvoices([]);
        }
        if (canViewDashboard) {
          await reloadDashboard({
            date_from: defaultMonthRange.from,
            date_to: defaultMonthRange.to,
            account: "",
            view: dashView,
          });
        } else {
          setDashKpis(null);
          setDashWealthMonthly([]);
          setDashExpenses([]);
          setDashAccountBalance([]);
          setDashCommitments({ a_vencer: 0, vencidos: 0 });
          setDashMsg("");
        }
        if (canViewInvestimentos) {
          await reloadInvestData();
        } else {
          investReloadSeqRef.current += 1;
          clearInvestState();
        }
        if (canManageWorkspaceUsers) {
          await reloadWorkspaceMembers();
        } else {
          setWorkspaceMembers([]);
          setWorkspacePermDrafts({});
        }
        if (isSuperAdmin) {
          await reloadAdminWorkspaces();
        } else {
          setAdminWorkspaces([]);
        }
      } catch {
        // handled by screen state
      }
    })();
  }, [user]);

  useEffect(() => {
    if (!userMenuOpen) return;
    const onDocDown = (ev) => {
      if (!userMenuRef.current) return;
      if (!userMenuRef.current.contains(ev.target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocDown);
    return () => document.removeEventListener("mousedown", onDocDown);
  }, [userMenuOpen]);

  useEffect(() => {
    if (!accounts.length) {
      setAccEditId("");
      setAccEditName("");
      setAccEditType("Banco");
      setAccEditCurrency("BRL");
      setAccEditShowOnDashboard(false);
      return;
    }
    const cur = accounts.find((a) => String(a.id) === String(accEditId)) || accounts[0];
    setAccEditId(String(cur.id));
    setAccEditName(cur.name);
    setAccEditType(cur.type);
    setAccEditCurrency((cur.currency || "BRL").toUpperCase());
    setAccEditShowOnDashboard(Boolean(cur.show_on_dashboard));
  }, [accounts]);

  useEffect(() => {
    if (!categories.length) {
      setCatEditId("");
      setCatEditName("");
      setCatEditKind("Despesa");
      return;
    }
    const cur = categories.find((c) => String(c.id) === String(catEditId)) || categories[0];
    setCatEditId(String(cur.id));
    setCatEditName(cur.name);
    setCatEditKind(cur.kind);
  }, [categories]);

  useEffect(() => {
    if (!accounts.length) {
      setTxAccountId("");
      return;
    }
    if (!txAccountId) {
      setTxAccountId(String(accounts[0].id));
    }
  }, [accounts, txAccountId]);

  useEffect(() => {
    const bankAccounts = accounts.filter((a) => normalizeAccountType(a.type) === "Banco");

    if (!bankAccounts.length) {
      setCardAccountId("");
      setCardSourceAccountId("");
    } else if (!bankAccounts.some((a) => String(a.id) === String(cardAccountId))) {
      setCardAccountId("");
      setCardSourceAccountId("");
    } else {
      setCardSourceAccountId(String(cardAccountId));
    }
  }, [accounts, cardAccountId]);

  useEffect(() => {
    if (!cards.length) {
      setCardEditId("");
      setCardName("");
      setCardBrand("");
      setCardModel("");
      setCardType("Credito");
      setCardAccountId("");
      setCardSourceAccountId("");
      setCardDueDay("");
      setCardCloseDay("");
      return;
    }
    if (!cardEditId) return;
    const cur = cards.find((c) => String(c.id) === String(cardEditId));
    if (!cur) {
      setCardEditId("");
      setCardName("");
      setCardBrand("");
      setCardModel("");
      setCardType("Credito");
      setCardAccountId("");
      setCardSourceAccountId("");
      setCardDueDay("");
      setCardCloseDay("");
      return;
    }
    setCardName(String(cur.name || ""));
    setCardBrand(String(cur.brand || "Visa"));
    setCardModel(String(cur.model || "Black"));
    setCardType(String(cur.card_type || "Credito"));
    setCardAccountId(String(cur.card_account_id || ""));
    setCardSourceAccountId(String(cur.source_account_id || ""));
    setCardDueDay(String(cur.due_day || 10));
    setCardCloseDay(String(cur.close_day || Math.max(1, Number(cur.due_day || 10) - 5)));
  }, [cards, cardEditId]);

  useEffect(() => {
    if (!investAssets.length) {
      setAssetEditClassFilter("");
      setAssetEditId("");
      setAssetEditSymbol("");
      setAssetEditName("");
      setAssetEditClass("");
      setAssetEditSector("Não definido");
      setAssetEditCurrency("BRL");
      setAssetEditBrokerId("");
      setAssetEditRentabilityType("");
      setAssetEditIndexPct("");
      setAssetEditSpreadRate("");
      setAssetEditFixedRate("");
      return;
    }
    if (assetEditClassFilter && !investAssets.some((a) => String(a.asset_class || "") === String(assetEditClassFilter))) {
      setAssetEditClassFilter("");
    }
  }, [investAssets]);

  const assetEditOptions = useMemo(() => {
    if (!assetEditClassFilter) return [];
    return investAssets.filter((a) => String(a.asset_class || "") === String(assetEditClassFilter));
  }, [investAssets, assetEditClassFilter]);

  useEffect(() => {
    if (!assetEditId) return;
    if (!assetEditOptions.some((a) => String(a.id) === String(assetEditId))) {
      setAssetEditId("");
    }
  }, [assetEditOptions, assetEditId]);

  useEffect(() => {
    if (!assetEditId) {
      setAssetEditSymbol("");
      setAssetEditName("");
      setAssetEditClass("");
      setAssetEditSector("Não definido");
      setAssetEditCurrency("BRL");
      setAssetEditBrokerId("");
      setAssetEditRentabilityType("");
      setAssetEditIndexPct("");
      setAssetEditSpreadRate("");
      setAssetEditFixedRate("");
      return;
    }
    const cur = investAssets.find((a) => String(a.id) === String(assetEditId));
    if (!cur) return;
    const isFixedIncome = isFixedIncomeClass(cur.asset_class || "");
    setAssetEditSymbol(cur.symbol || "");
    setAssetEditName(cur.name || "");
    setAssetEditClass(cur.asset_class || "");
    setAssetEditSector(cur.sector || "Não definido");
    setAssetEditCurrency((cur.currency || "BRL").toUpperCase());
    setAssetEditBrokerId(cur.broker_account_id ? String(cur.broker_account_id) : "");
    setAssetEditRentabilityType(isFixedIncome ? String(cur.rentability_type || "MANUAL").toUpperCase() : "");
    setAssetEditIndexPct(cur.index_pct == null ? "" : formatLocalizedNumber(cur.index_pct, 8));
    setAssetEditSpreadRate(cur.spread_rate == null ? "" : formatLocalizedNumber(cur.spread_rate, 8));
    setAssetEditFixedRate(cur.fixed_rate == null ? "" : formatLocalizedNumber(cur.fixed_rate, 8));
  }, [investAssets, assetEditId]);

  useEffect(() => {
    setFairValueDrafts((prev) => {
      const next = {};
      for (const asset of investAssets || []) {
        const key = String(asset?.id || "");
        if (!key) continue;
        next[key] = {
          fair_price:
            prev[key]?.fair_price ??
            (asset?.fair_price == null ? "" : formatLocalizedNumber(asset.fair_price, 2)),
          safety_margin_pct:
            prev[key]?.safety_margin_pct ??
            (asset?.safety_margin_pct == null ? "20,00" : formatLocalizedNumber(asset.safety_margin_pct, 2)),
          user_objective:
            prev[key]?.user_objective ??
            String(asset?.user_objective || "").trim().toLowerCase(),
        };
      }
      return next;
    });
  }, [investAssets]);

  useEffect(() => {
    if (isFixedIncomeClass(assetCreateClass || "")) {
      setAssetCreateRentabilityType((prev) => prev || "MANUAL");
      return;
    }
    setAssetCreateRentabilityType("");
    setAssetCreateIndexPct("");
    setAssetCreateSpreadRate("");
    setAssetCreateFixedRate("");
  }, [assetCreateClass]);

  useEffect(() => {
    if (isFixedIncomeClass(assetEditClass || "")) {
      setAssetEditRentabilityType((prev) => prev || "MANUAL");
      return;
    }
    setAssetEditRentabilityType("");
    setAssetEditIndexPct("");
    setAssetEditSpreadRate("");
    setAssetEditFixedRate("");
  }, [assetEditClass]);

  const subtitle = useMemo(() => PAGE_SUBTITLES[page] || "Painel financeiro", [page]);
  const isSuperAdmin = String(user?.global_role || "").toUpperCase() === "SUPER_ADMIN";
  const isWorkspaceOwner = String(user?.workspace_role || "").toUpperCase() === "OWNER";
  const canManageWorkspaceUsers = isSuperAdmin || isWorkspaceOwner;
  const permissionMap = useMemo(() => buildEffectivePermissionMap(user), [user]);
  const canViewDashboard = hasPermission(permissionMap, "dashboard", "view");
  const canViewContas = hasPermission(permissionMap, "contas", "view");
  const canViewLancamentos = hasPermission(permissionMap, "lancamentos", "view");
  const canViewInvestimentos = hasPermission(permissionMap, "investimentos", "view");
  const canViewRelatorios = hasPermission(permissionMap, "relatorios", "view");
  const canViewGerenciador = canViewContas;
  const canAddContas = hasPermission(permissionMap, "contas", "add");
  const canEditContas = hasPermission(permissionMap, "contas", "edit");
  const canDeleteContas = hasPermission(permissionMap, "contas", "delete");
  const canAddLancamentos = hasPermission(permissionMap, "lancamentos", "add");
  const canDeleteLancamentos = hasPermission(permissionMap, "lancamentos", "delete");
  const canAddInvestimentos = hasPermission(permissionMap, "investimentos", "add");
  const canEditInvestimentos = hasPermission(permissionMap, "investimentos", "edit");
  const canDeleteInvestimentos = hasPermission(permissionMap, "investimentos", "delete");
  const canAddRelatorios = hasPermission(permissionMap, "relatorios", "add");
  const visiblePages = useMemo(
    () =>
      PAGES.filter((p) => hasPermission(permissionMap, PAGE_PERMISSION_MODULE[p], "view")),
    [permissionMap]
  );
  const managerTabs = useMemo(() => {
    if (!canManageWorkspaceUsers) return MANAGER_TABS;
    return [...MANAGER_TABS, "Usuários e workspaces"];
  }, [canManageWorkspaceUsers]);
  const currentWorkspaceId = String(user?.workspace_id || "");
  const workspaceOptions = useMemo(() => {
    return (workspaces || []).map((ws) => ({
      id: String(ws.workspace_id || ws.id || ""),
      name: String(ws.workspace_name || ws.name || `Workspace ${ws.workspace_id || ws.id}`),
      status: normalizeWorkspaceStatus(ws.workspace_status || ws.status),
      role: String(ws.workspace_role || "").toUpperCase(),
      owner_email: ws.owner_email || "",
      owner_display_name: ws.owner_display_name || "",
      members_count: Number(ws.members_count || 0),
    }));
  }, [workspaces]);
  const workspaceMembersSorted = useMemo(() => {
    const rows = [...(workspaceMembers || [])];
    rows.sort((a, b) => {
      const ra = String(a.workspace_role || "").toUpperCase();
      const rb = String(b.workspace_role || "").toUpperCase();
      if (ra !== rb) {
        if (ra === "OWNER") return -1;
        if (rb === "OWNER") return 1;
      }
      return String(a.email || "").localeCompare(String(b.email || ""), "pt-BR");
    });
    return rows;
  }, [workspaceMembers]);

  useEffect(() => {
    if (managerTabs.includes(managerTab)) return;
    setManagerTab(managerTabs[0] || "Cadastro de contas");
  }, [managerTabs, managerTab]);

  useEffect(() => {
    if (!visiblePages.length) return;
    if (visiblePages.includes(page)) return;
    setPage(visiblePages[0]);
  }, [visiblePages, page]);

  const txCategory = useMemo(
    () => categories.find((c) => String(c.id) === String(txCategoryId)) || null,
    [categories, txCategoryId]
  );
  const txIsFutureTab = txView === "futuro";
  const txIsCashTab = txView === "caixa";
  const txCategoriesForForm = useMemo(
    () => (txIsFutureTab ? categories.filter((c) => String(c.kind) === "Despesa") : categories),
    [categories, txIsFutureTab]
  );
  const txEffectiveKind = txCategory?.kind || "";
  const txIsTransfer = txEffectiveKind === "Transferencia";
  const txIsExpense = txEffectiveKind === "Despesa";
  const txIsIncome = txEffectiveKind === "Receita";
  const txMethodEffective = txIsFutureTab ? "Futuro" : txMethod;
  const txIsExpenseCredit = txIsExpense && !txIsTransfer && txMethodEffective === "Credito";
  const txIsFutureCredit = txIsFutureTab && txFuturePaymentMethod === "Credito";
  const txMethodOptions = useMemo(() => {
    if (txIsFutureTab) return ["Futuro"];
    if (txIsIncome) return ["PIX", "TED", "Dinheiro"];
    if (txIsExpense) return ["PIX", "Debito", "Credito", "TED", "Dinheiro"];
    if (txIsTransfer) return ["PIX", "TED", "Dinheiro"];
    return [];
  }, [txIsFutureTab, txIsIncome, txIsExpense, txIsTransfer]);
  const txRecentCategoryOptions = useMemo(
    () =>
      (categories || [])
        .map((c) => ({ id: String(c.id), name: String(c.name || ""), kind: String(c.kind || "") }))
        .sort((a, b) => a.name.localeCompare(b.name, "pt-BR")),
    [categories]
  );
  const txRecentCategoryFilter = useMemo(
    () => txRecentCategoryOptions.find((c) => c.id === String(txRecentCategoryFilterId)) || null,
    [txRecentCategoryOptions, txRecentCategoryFilterId]
  );
  const txRecentStatusOptions = useMemo(() => {
    const set = new Set();
    for (const t of transactions || []) {
      const raw = String(t.charge_status || "").trim();
      set.add(raw || "__none__");
    }
    const preferredOrder = ["Pendente", "Vencido", "Pago", "Aguardando Fatura", "__none__"];
    const options = [...set];
    options.sort((a, b) => {
      const ia = preferredOrder.indexOf(a);
      const ib = preferredOrder.indexOf(b);
      if (ia >= 0 && ib >= 0) return ia - ib;
      if (ia >= 0) return -1;
      if (ib >= 0) return 1;
      return String(a).localeCompare(String(b), "pt-BR");
    });
    const mapped = options.map((value) => ({
      value,
      label: value === "__none__" ? "Sem status (-)" : value,
    }));
    mapped.unshift({
      value: TX_STATUS_FILTER_OPEN,
      label: "A vencer (Pendente + Aguardando Fatura)",
    });
    return mapped;
  }, [transactions]);
  const transactionsVisible = useMemo(() => {
    const targetId = String(txRecentCategoryFilterId);
    const targetName = normalizeText(txRecentCategoryFilter?.name || "");
    const from = String(txRecentDateFrom || "").trim();
    const to = String(txRecentDateTo || "").trim();
    return (transactions || []).filter((t) => {
      const date = String(t.date || "").trim();
      if (from && date && date < from) return false;
      if (to && date && date > to) return false;
      if (txRecentCategoryFilterId) {
        const categoryMatches =
          String(t.category_id || "") === targetId ||
          (targetName && normalizeText(t.category || "") === targetName);
        if (!categoryMatches) return false;
      }
      if (txRecentStatusFilter) {
        const rawStatus = String(t.charge_status || "").trim();
        const statusKey = rawStatus || "__none__";
        if (txRecentStatusFilter === TX_STATUS_FILTER_OPEN) {
          if (statusKey !== "Pendente" && statusKey !== "Aguardando Fatura") return false;
        } else if (statusKey !== txRecentStatusFilter) {
          return false;
        }
      }
      return true;
    });
  }, [transactions, txRecentCategoryFilterId, txRecentCategoryFilter, txRecentStatusFilter, txRecentDateFrom, txRecentDateTo]);
  const transactionsVisibleOrdered = useMemo(() => {
    if (txView !== "futuro" && txView !== "competencia") return transactionsVisible;
    const rows = [...transactionsVisible];
    if (txView === "futuro") {
      const todayIso = new Date().toISOString().slice(0, 10);
      rows.sort((a, b) => {
        const da = String(a?.date || "");
        const db = String(b?.date || "");
        const aIsUpcoming = da >= todayIso;
        const bIsUpcoming = db >= todayIso;
        if (aIsUpcoming !== bIsUpcoming) return aIsUpcoming ? -1 : 1;
        if (da === db) return String(a?.id || "").localeCompare(String(b?.id || ""));
        if (aIsUpcoming && bIsUpcoming) {
          return da.localeCompare(db);
        }
        return db.localeCompare(da);
      });
      return rows;
    }
    if (txView === "competencia") {
      rows.sort((a, b) => {
        const da = String(a?.date || "");
        const db = String(b?.date || "");
        if (da === db) return String(b?.id || "").localeCompare(String(a?.id || ""));
        return db.localeCompare(da);
      });
      return rows;
    }
    rows.sort((a, b) => {
      const da = String(a?.date || "");
      const db = String(b?.date || "");
      if (da === db) return String(a?.id || "").localeCompare(String(b?.id || ""));
      return da.localeCompare(db);
    });
    return rows;
  }, [transactionsVisible, txView]);
  const transferAccounts = useMemo(
    () => accounts.filter((a) => ["Banco", "Corretora"].includes(normalizeAccountType(a.type))),
    [accounts]
  );
  const bankAccountsOnly = useMemo(
    () => accounts.filter((a) => normalizeAccountType(a.type) === "Banco"),
    [accounts]
  );
  const cardsForTxMethod = useMemo(() => {
    if (txIsFutureCredit) return (cards || []).filter((c) => String(c.card_type || "Credito") === "Credito");
    if (!txIsExpense || txIsTransfer) return [];
    if (txMethodEffective === "Credito") return (cards || []).filter((c) => String(c.card_type || "Credito") === "Credito");
    return [];
  }, [cards, txIsExpense, txIsTransfer, txMethodEffective, txIsFutureCredit]);
  const selectedTxCard = useMemo(
    () => cardsForTxMethod.find((c) => String(c.id) === String(txCardId)) || null,
    [cardsForTxMethod, txCardId]
  );
  useEffect(() => {
    if ((!txIsExpense || txIsTransfer || txMethodEffective !== "Credito") && !txIsFutureCredit) {
      setTxCardId("");
      return;
    }
    if (!cardsForTxMethod.length) {
      setTxCardId("");
      return;
    }
    if (!txCardId || !cardsForTxMethod.some((c) => String(c.id) === String(txCardId))) {
      setTxCardId(String(cardsForTxMethod[0].id));
    }
  }, [txIsExpense, txIsTransfer, txMethodEffective, txIsFutureCredit, cardsForTxMethod, txCardId]);

  useEffect(() => {
    if (!txMethodOptions.length) {
      setTxMethod("");
      return;
    }
    if (!txMethod || !txMethodOptions.includes(txMethod)) {
      setTxMethod(txMethodOptions[0]);
    }
  }, [txMethodOptions, txMethod]);

  useEffect(() => {
    if (!txIsFutureTab) return;
    if (!["PIX", "Debito", "Boleto", "Credito"].includes(txFuturePaymentMethod)) {
      setTxFuturePaymentMethod("PIX");
    }
  }, [txIsFutureTab, txFuturePaymentMethod]);

  useEffect(() => {
    if (!txIsFutureCredit || !selectedTxCard) return;
    if (String(txAccountId) !== String(selectedTxCard.card_account_id || "")) {
      setTxAccountId(String(selectedTxCard.card_account_id || ""));
    }
  }, [txIsFutureCredit, selectedTxCard, txAccountId]);

  useEffect(() => {
    if (!txIsFutureTab) return;
    if (!txCategoriesForForm.length) {
      setTxCategoryId("");
      return;
    }
    if (!txCategory || String(txCategory.kind) !== "Despesa") {
      setTxCategoryId(String(txCategoriesForForm[0].id));
    }
  }, [txIsFutureTab, txCategoriesForForm, txCategory]);

  useEffect(() => {
    if (!txIsTransfer) return;
    if (!transferAccounts.length) {
      setTxAccountId("");
      setTxSourceAccountId("");
      return;
    }
    if (!txAccountId || !transferAccounts.some((a) => String(a.id) === String(txAccountId))) {
      setTxAccountId(String(transferAccounts[0].id));
    }
    if (!txSourceAccountId || !transferAccounts.some((a) => String(a.id) === String(txSourceAccountId))) {
      const fallback = transferAccounts.find((a) => String(a.id) !== String(txAccountId));
      setTxSourceAccountId(fallback ? String(fallback.id) : "");
    }
  }, [txIsTransfer, transferAccounts, txAccountId, txSourceAccountId]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        await reloadTransactions({ view: txView });
      } catch {
        // mensagem já tratada nos fluxos de ação
      }
    })();
  }, [txView, user]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        await reloadDashboard({ view: dashView });
      } catch {
        // mensagem já tratada nos fluxos de ação
      }
    })();
  }, [dashView, user]);

  useEffect(() => {
    if (!user || page !== "Investimentos") return;
    let cancelled = false;
    (async () => {
      try {
        await reloadInvestData({ syncRentability: true });
        if (cancelled || !canAddInvestimentos) return;
        const workspaceKey = String(user?.current_workspace_id || user?.workspace_id || user?.id || "");
        const autoRunKey = `${workspaceKey}:${new Date().toISOString().slice(0, 10)}`;
        if (investQuoteAutoRunRef.current === autoRunKey) return;
        investQuoteAutoRunRef.current = autoRunKey;
        await runInvestPriceUpdate({
          includeGroups: QUOTE_GROUP_OPTIONS,
          silentSuccess: true,
          reloadAfter: true,
        });
      } catch (err) {
        if (cancelled) return;
        setInvestMsg(String(err.message || err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [canAddInvestimentos, page, user]);

  useEffect(() => {
    if (!txIsExpenseCredit) return;
    if (!selectedTxCard) return;
    if (String(txAccountId) !== String(selectedTxCard.card_account_id || "")) {
      setTxAccountId(String(selectedTxCard.card_account_id || ""));
    }
  }, [txIsExpenseCredit, selectedTxCard, txAccountId]);
  const brl = useMemo(
    () =>
      new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }),
    []
  );
  const currentKpi = dashKpis || kpis || {};
  const currentMonthEntry = dashWealthMonthly.length ? dashWealthMonthly[dashWealthMonthly.length - 1] : null;
  const previousMonthEntry = dashWealthMonthly.length > 1 ? dashWealthMonthly[dashWealthMonthly.length - 2] : null;
  const trendEnd = currentMonthEntry ? Number(currentMonthEntry.patrimonio || 0) : 0;
  const previousMonthValue = previousMonthEntry ? Number(previousMonthEntry.patrimonio || 0) : 0;
  const trendDelta = trendEnd - previousMonthValue;
  const trendPct =
    previousMonthEntry && previousMonthValue !== 0
      ? (trendDelta / Math.abs(previousMonthValue)) * 100
      : 0;
  const trendDirection = trendDelta >= 0 ? "up" : "down";
  const trendMonthLabel = currentMonthEntry?.month
    ? new Date(`${currentMonthEntry.month}-01T00:00:00`).toLocaleDateString("pt-BR", {
        month: "long",
        year: "numeric",
      })
    : "";
  const normalizeMoneyValue = (v) => (Math.abs(Number(v || 0)) < 0.005 ? 0 : Number(v || 0));
  const accountsTop = useMemo(() => {
    const byAccount = new Map(
      [...(dashAccountBalance || [])].map((r) => [String(r.account || ""), Number(r.saldo || 0)])
    );
    return [...(accounts || [])]
      .map((a) => ({
        account: String(a.name || ""),
        saldo: normalizeMoneyValue(byAccount.get(String(a.name || "")) ?? 0),
        showOnDashboard: Boolean(a.show_on_dashboard),
        fixedManual:
          Boolean(a.show_on_dashboard) &&
          Math.abs(Number(normalizeMoneyValue(byAccount.get(String(a.name || "")) ?? 0) || 0)) < 0.005,
      }))
      .filter((a) => Math.abs(Number(a.saldo || 0)) >= 0.005 || a.showOnDashboard)
      .sort((a, b) => Number(b.saldo || 0) - Number(a.saldo || 0));
  }, [dashAccountBalance, accounts]);
  const accountsTotal = useMemo(
    () => normalizeMoneyValue(accountsTop.reduce((acc, r) => acc + Number(r.saldo || 0), 0)),
    [accountsTop]
  );
  const commitmentsAging = useMemo(
    () => ({
      aVencer: Number(dashCommitments?.a_vencer || 0),
      vencidos: Number(dashCommitments?.vencidos || 0),
    }),
    [dashCommitments]
  );
  const creditCards = useMemo(
    () => (cards || []).filter((c) => String(c.card_type || "Credito") === "Credito"),
    [cards]
  );
  useEffect(() => {
    if (!creditCards.length) {
      setWalletCardIndex(0);
      return;
    }
    if (walletCardIndex >= creditCards.length) {
      setWalletCardIndex(0);
    }
  }, [creditCards.length, walletCardIndex]);
  const activeCreditCard = creditCards.length ? creditCards[walletCardIndex] : null;
  const walletVisibleCards = useMemo(() => {
    if (!creditCards.length) return [];
    if (creditCards.length === 1) {
      return [{ ...creditCards[0], walletPos: "active" }];
    }
    return creditCards
      .map((card, idx) => {
        const dist = getCircularDistance(walletCardIndex, idx, creditCards.length);
        if (dist === 0) return { ...card, walletPos: "active" };
        if (dist === -1) return { ...card, walletPos: "prev" };
        if (dist === 1) return { ...card, walletPos: "next" };
        return null;
      })
      .filter(Boolean);
  }, [creditCards, walletCardIndex]);
  const activeCardOpenInvoices = useMemo(() => {
    if (!activeCreditCard) return [];
    return (cardInvoices || []).filter(
      (i) =>
        String(i.status || "").toUpperCase() === "OPEN" &&
        Number(i.card_id) === Number(activeCreditCard.id)
    );
  }, [cardInvoices, activeCreditCard]);
  const activeCardCurrentInvoice = useMemo(() => {
    if (!activeCardOpenInvoices.length) return null;
    const sorted = [...activeCardOpenInvoices].sort((a, b) =>
      String(a.due_date || "").localeCompare(String(b.due_date || ""))
    );
    return sorted[0] || null;
  }, [activeCardOpenInvoices]);
  const activeCardCurrentInvoiceAmount = useMemo(
    () =>
      activeCardCurrentInvoice
        ? Math.max(
            0,
            Number(activeCardCurrentInvoice.total_amount || 0) - Number(activeCardCurrentInvoice.paid_amount || 0)
          )
        : 0,
    [activeCardCurrentInvoice]
  );
  const invoiceCardFilterOptions = useMemo(() => {
    const map = new Map();
    for (const inv of cardInvoices || []) {
      const id = Number(inv.card_id);
      if (!Number.isFinite(id) || id <= 0) continue;
      const name = String(inv.card_name || `Cartão ${id}`);
      if (!map.has(id)) map.set(id, name);
    }
    return [...map.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => String(a.name).localeCompare(String(b.name), "pt-BR"));
  }, [cardInvoices]);
  const openInvoicesDateRange = useMemo(() => {
    const monthRange = getCurrentMonthRange();
    return {
      from: String(invoiceDateFrom || "").trim() || monthRange.from,
      to: String(invoiceDateTo || "").trim() || monthRange.to,
    };
  }, [invoiceDateFrom, invoiceDateTo]);
  const openInvoicesVisible = useMemo(() => {
    const selectedId = Number(invoiceCardFilterId);
    const rows = (cardInvoices || []).filter((inv) => {
      if (String(inv.status || "").toUpperCase() !== "OPEN") return false;
      if (!isIsoDateWithinRange(inv.due_date, openInvoicesDateRange.from, openInvoicesDateRange.to)) return false;
      if (!invoiceCardFilterId) return true;
      return Number(inv.card_id) === selectedId;
    });
    rows.sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || "")));
    return rows;
  }, [cardInvoices, invoiceCardFilterId, openInvoicesDateRange]);
  const investmentByClass = useMemo(() => {
    const rows = investPortfolio?.positions || [];
    const map = new Map();
    for (const p of rows) {
      const key = String(p.asset_class || "Outros");
      const val = Number(p.market_value || 0);
      map.set(key, (map.get(key) || 0) + (Number.isFinite(val) ? val : 0));
    }
    const list = [...map.entries()].map(([name, value]) => ({ name, value }));
    list.sort((a, b) => b.value - a.value);
    return list;
  }, [investPortfolio]);
  const investmentTotal = useMemo(
    () => investmentByClass.reduce((acc, r) => acc + Number(r.value || 0), 0),
    [investmentByClass]
  );
  const dashInvestFocusedClass = useMemo(() => {
    if (!dashInvestFocusClass) return "";
    return investmentByClass.some((row) => row.name === dashInvestFocusClass) ? dashInvestFocusClass : "";
  }, [dashInvestFocusClass, investmentByClass]);
  const investmentRadialData = useMemo(() => {
    const hasFocus = Boolean(dashInvestFocusedClass);
    return investmentByClass.map((row, idx) => ({
      name: row.name,
      value: Number(row.value || 0),
      pct: pct(row.value, investmentTotal),
      fill: DONUT_COLORS[idx % DONUT_COLORS.length],
      opacity: !hasFocus || row.name === dashInvestFocusedClass ? 1 : 0.22,
      isFocused: row.name === dashInvestFocusedClass,
    }));
  }, [dashInvestFocusedClass, investmentByClass, investmentTotal]);
  const investSummaryClassOptions = useMemo(() => {
    const classes = new Set(
      (investPortfolio?.positions || [])
        .map((p) => String(p.asset_class || "").trim())
        .filter((v) => v)
    );
    return [...classes].sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [investPortfolio]);
  const latestInvestPriceByAssetId = useMemo(() => {
    const map = new Map();
    for (const row of investPrices || []) {
      const assetId = Number(row?.asset_id || 0);
      if (!assetId) continue;
      const dateKey = String(row?.date || "");
      const current = map.get(assetId);
      if (!current || dateKey > current.date) {
        map.set(assetId, {
          date: dateKey,
          price: Number(row?.price || 0),
        });
      }
    }
    return map;
  }, [investPrices]);
  const fairValueAssets = useMemo(() => {
    return (investAssets || [])
      .filter((asset) => {
        const cls = classKey(asset?.asset_class || "");
        return !["renda_fixa", "tesouro_direto", "fundos", "coe", "caixa"].includes(cls);
      })
      .map((asset) => {
        const latestPrice = latestInvestPriceByAssetId.get(Number(asset?.id || 0));
        const currentPriceRaw =
          Number(asset?.current_value || 0) > 0
            ? Number(asset.current_value)
            : Number(latestPrice?.price || 0);
        const fairPrice = Number(asset?.fair_price || 0);
        const safetyMarginPct = Number(asset?.safety_margin_pct || 0);
        const { entryPrice, ceilingPrice } = computeFairValueRange(fairPrice, safetyMarginPct);
        const bias = getFairValueBiasLabel(currentPriceRaw, entryPrice, ceilingPrice);
        const technicalSignal = {
          code:
            bias.tone === "buy"
              ? "buy"
              : bias.tone === "sell"
                ? "sell"
                : bias.tone === "wait"
                  ? "wait"
                  : "neutral",
          label: bias.label,
          tone: bias.tone,
        };
        return {
          ...asset,
          currentPrice: Number.isFinite(currentPriceRaw) && currentPriceRaw > 0 ? currentPriceRaw : null,
          fairPrice: Number.isFinite(fairPrice) && fairPrice > 0 ? fairPrice : null,
          safetyMarginPct: Number.isFinite(safetyMarginPct) ? safetyMarginPct : null,
          entryPrice,
          ceilingPrice,
          bias,
          technicalSignal,
          userObjective: String(asset?.user_objective || "").trim().toLowerCase() || null,
          priceRefDate: latestPrice?.date || asset?.last_update || "",
        };
      })
      .sort((a, b) => String(a.symbol || "").localeCompare(String(b.symbol || ""), "pt-BR"));
  }, [investAssets, latestInvestPriceByAssetId]);
  const fairValueClassOptions = useMemo(() => {
    const classes = new Set(fairValueAssets.map((asset) => String(asset.asset_class || "").trim()).filter(Boolean));
    return [...classes].sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [fairValueAssets]);
  const fairValueAssetOptions = useMemo(() => {
    if (!fairValueClassFilter) return [];
    return fairValueAssets.filter((asset) => String(asset.asset_class || "") === fairValueClassFilter);
  }, [fairValueAssets, fairValueClassFilter]);
  const selectedFairValueAsset = useMemo(() => {
    return fairValueAssets.find((asset) => String(asset.id) === String(fairValueAssetId)) || null;
  }, [fairValueAssets, fairValueAssetId]);
  const configuredFairValueAssets = useMemo(() => {
    return fairValueAssets.filter((asset) => asset.fairPrice != null && asset.safetyMarginPct != null);
  }, [fairValueAssets]);
  useEffect(() => {
    if (!investSummaryClassFilter) return;
    if (!investSummaryClassOptions.includes(investSummaryClassFilter)) {
      setInvestSummaryClassFilter("");
    }
  }, [investSummaryClassFilter, investSummaryClassOptions]);
  useEffect(() => {
    if (!investPortfolioClassFilter) return;
    if (!investSummaryClassOptions.includes(investPortfolioClassFilter)) {
      setInvestPortfolioClassFilter("");
    }
  }, [investPortfolioClassFilter, investSummaryClassOptions]);
  useEffect(() => {
    if (!fairValueClassFilter) return;
    if (!fairValueClassOptions.includes(fairValueClassFilter)) {
      setFairValueClassFilter("");
    }
  }, [fairValueClassFilter, fairValueClassOptions]);
  useEffect(() => {
    if (!fairValueClassFilter) {
      setFairValueAssetId("");
      return;
    }
    if (!fairValueAssetOptions.some((asset) => String(asset.id) === String(fairValueAssetId))) {
      setFairValueAssetId("");
    }
  }, [fairValueAssetId, fairValueAssetOptions, fairValueClassFilter]);
  const investSummaryPositionsFiltered = useMemo(() => {
    const rows = investPortfolio?.positions || [];
    if (!investSummaryClassFilter) return rows;
    return rows.filter((p) => String(p.asset_class || "") === investSummaryClassFilter);
  }, [investPortfolio, investSummaryClassFilter]);
  const investSummaryViewData = useMemo(() => {
    if (!investSummaryClassFilter) {
      return {
        assets_count: Number(investSummaryData.assets_count || 0),
        total_invested: Number(investSummaryData.total_invested || 0),
        broker_balance: Number(investSummaryData.broker_balance || 0),
        total_market: Number(investSummaryData.total_market || 0),
        total_return: Number(investSummaryData.total_return || 0),
        total_return_pct: Number(investSummaryData.total_return_pct || 0),
        total_unrealized: Number(investSummaryData.total_unrealized || 0),
      };
    }
    const rows = investSummaryPositionsFiltered;
    const totalInvested = rows.reduce((acc, p) => acc + Number(p.cost_basis || 0), 0);
    const totalMarket = rows.reduce((acc, p) => acc + Number(p.market_value || 0), 0);
    const totalUnrealized = rows.reduce((acc, p) => acc + Number(p.unrealized_pnl || 0), 0);
    const totalReturn = totalUnrealized;
    const totalReturnPct = totalInvested > 0 ? (totalReturn / totalInvested) * 100 : 0;
    return {
      assets_count: rows.length,
      total_invested: normalizeMoneyValue(totalInvested),
      broker_balance: Number(investSummaryData.broker_balance || 0),
      total_market: normalizeMoneyValue(totalMarket),
      total_return: normalizeMoneyValue(totalReturn),
      total_return_pct: Number.isFinite(totalReturnPct) ? totalReturnPct : 0,
      total_unrealized: normalizeMoneyValue(totalUnrealized),
    };
  }, [investSummaryClassFilter, investSummaryData, investSummaryPositionsFiltered]);
  const investPortfolioPositionsVisible = useMemo(() => {
    if (investTab === "Resumo" && investSummaryClassFilter) {
      return investSummaryPositionsFiltered;
    }
    const rows = investPortfolio.positions || [];
    if (!investPortfolioClassFilter) return rows;
    return rows.filter((p) => String(p.asset_class || "") === investPortfolioClassFilter);
  }, [investTab, investSummaryClassFilter, investSummaryPositionsFiltered, investPortfolio, investPortfolioClassFilter]);
  const investRentabilityWindowStart = useMemo(() => {
    const allDates = [
      ...(investTrades || []).map((row) => String(row?.date || "").trim()),
      ...(investIncomes || []).map((row) => String(row?.date || "").trim()),
      ...((investPortfolio?.positions || []).map((row) => String(row?.value_ref_date || "").trim())),
    ].filter((value) => /^\d{4}-\d{2}-\d{2}$/.test(value));
    const latestDate = allDates.sort().at(-1) || "";
    if (!latestDate || investRentabilityWindow === "all") return "";
    if (investRentabilityWindow === "24m") return shiftIsoDateByMonths(latestDate, 24);
    if (investRentabilityWindow === "12m") return shiftIsoDateByMonths(latestDate, 12);
    return shiftIsoDateByMonths(latestDate, 6);
  }, [investIncomes, investPortfolio, investRentabilityWindow, investTrades]);
  const investRentabilityActiveClasses = useMemo(() => {
    if (!investRentabilityWindowStart) {
      return new Set((investPortfolio?.positions || []).map((row) => String(row?.asset_class || "").trim()).filter(Boolean));
    }
    const active = new Set();
    for (const row of investTrades || []) {
      const date = String(row?.date || "").trim();
      const assetClass = String(row?.asset_class || "").trim();
      if (assetClass && date && date >= investRentabilityWindowStart) {
        active.add(assetClass);
      }
    }
    for (const row of investIncomes || []) {
      const date = String(row?.date || "").trim();
      const assetId = Number(row?.asset_id || 0);
      if (!assetId || !date || date < investRentabilityWindowStart) continue;
      const asset = (investAssets || []).find((item) => Number(item?.id || 0) === assetId);
      const assetClass = String(asset?.asset_class || "").trim();
      if (assetClass) active.add(assetClass);
    }
    for (const row of investPortfolio?.positions || []) {
      const valueRefDate = String(row?.value_ref_date || "").trim();
      const assetClass = String(row?.asset_class || "").trim();
      if (assetClass && valueRefDate && valueRefDate >= investRentabilityWindowStart) {
        active.add(assetClass);
      }
    }
    return active;
  }, [investAssets, investIncomes, investPortfolio, investRentabilityWindowStart, investTrades]);
  const investRentabilityPositions = useMemo(() => {
    return (investPortfolio?.positions || []).filter((row) => {
      const assetClass = String(row?.asset_class || "").trim();
      return assetClass && investRentabilityActiveClasses.has(assetClass);
    });
  }, [investPortfolio, investRentabilityActiveClasses]);
  const investRentabilityByClass = useMemo(() => {
    const grouped = new Map();
    for (const row of investRentabilityPositions) {
      const assetClass = String(row?.asset_class || "").trim() || "Outros";
      const base = grouped.get(assetClass) || {
        asset_class: assetClass,
        assets_count: 0,
        total_invested: 0,
        total_market: 0,
        total_income: 0,
        total_realized: 0,
        total_unrealized: 0,
        total_return: 0,
        total_return_pct: 0,
      };
      base.assets_count += 1;
      base.total_invested += Number(row?.cost_basis || 0) || 0;
      base.total_market += Number(row?.market_value || 0) || 0;
      base.total_income += Number(row?.income || 0) || 0;
      base.total_realized += Number(row?.realized_pnl || 0) || 0;
      base.total_unrealized += Number(row?.unrealized_pnl || 0) || 0;
      grouped.set(assetClass, base);
    }
    const groupedValues = Array.from(grouped.values());
    const totalMarketAllClasses = groupedValues.reduce((acc, item) => acc + (Number(item.total_market || 0) || 0), 0);
    const list = groupedValues.map((item) => {
      const totalReturn = Number(item.total_income || 0) + Number(item.total_realized || 0) + Number(item.total_unrealized || 0);
      const totalInvested = Number(item.total_invested || 0);
      const totalReturnPct = totalInvested > 0 ? (totalReturn / totalInvested) * 100 : 0;
      const participationPct = totalMarketAllClasses > 0 ? (Number(item.total_market || 0) / totalMarketAllClasses) * 100 : 0;
      return {
        ...item,
        total_invested: normalizeMoneyValue(item.total_invested),
        total_market: normalizeMoneyValue(item.total_market),
        total_income: normalizeMoneyValue(item.total_income),
        total_realized: normalizeMoneyValue(item.total_realized),
        total_unrealized: normalizeMoneyValue(item.total_unrealized),
        total_return: normalizeMoneyValue(totalReturn),
        total_return_pct: Number.isFinite(totalReturnPct) ? totalReturnPct : 0,
        participation_pct: Number.isFinite(participationPct) ? participationPct : 0,
      };
    });
    list.sort((a, b) => b.total_return_pct - a.total_return_pct);
    return list;
  }, [investRentabilityPositions]);
  const investRentabilityHighlights = useMemo(() => {
    const rows = investRentabilityByClass.filter((item) => Number(item.total_invested || 0) > 0);
    const best = rows.length ? rows[0] : null;
    const worst = rows.length ? rows[rows.length - 1] : null;
    const biggest = rows.length
      ? [...rows].sort((a, b) => Number(b.participation_pct || 0) - Number(a.participation_pct || 0))[0]
      : null;
    const consolidatedInvested = rows.reduce((acc, item) => acc + (Number(item.total_invested || 0) || 0), 0);
    const consolidatedReturn = rows.reduce((acc, item) => acc + (Number(item.total_return || 0) || 0), 0);
    const consolidatedReturnPct = consolidatedInvested > 0 ? (consolidatedReturn / consolidatedInvested) * 100 : 0;
    const bestAsset = [...investRentabilityPositions]
      .map((row) => {
        const totalInvested = Number(row?.cost_basis || 0) || 0;
        const totalIncome = Number(row?.income || 0) || 0;
        const totalRealized = Number(row?.realized_pnl || 0) || 0;
        const totalUnrealized = Number(row?.unrealized_pnl || 0) || 0;
        const totalReturn = totalIncome + totalRealized + totalUnrealized;
        const totalReturnPct = totalInvested > 0 ? (totalReturn / totalInvested) * 100 : 0;
        return {
          symbol: String(row?.symbol || "").trim() || "-",
          asset_class: String(row?.asset_class || "").trim() || "Sem classe",
          total_return: normalizeMoneyValue(totalReturn),
          total_return_pct: Number.isFinite(totalReturnPct) ? totalReturnPct : 0,
          market_value: normalizeMoneyValue(Number(row?.market_value || 0) || 0),
        };
      })
      .filter((row) => Number.isFinite(row.total_return_pct))
      .sort((a, b) => Number(b.total_return_pct || 0) - Number(a.total_return_pct || 0))[0] || null;
    return {
      classes_count: investRentabilityByClass.length,
      best,
      worst,
      biggest,
      consolidated: {
        total_return: normalizeMoneyValue(consolidatedReturn),
        total_return_pct: Number.isFinite(consolidatedReturnPct) ? consolidatedReturnPct : 0,
      },
      best_asset: bestAsset,
    };
  }, [investRentabilityByClass, investRentabilityPositions]);
  const investBenchmarkOptions = useMemo(() => {
    return investRentabilityByClass.map((row) => {
      const config = BENCHMARK_BY_ASSET_CLASS[String(row.asset_class || "").trim()] || null;
      return {
        asset_class: row.asset_class,
        benchmark_label: config?.benchmark || "Benchmark",
        benchmark_ready: Boolean(config?.ready),
        index_name: config?.indexName || "",
        series_mode: config?.seriesMode || "level",
      };
    });
  }, [investRentabilityByClass]);
  const selectedBenchmarkOption = useMemo(
    () => investBenchmarkOptions.find((item) => String(item.asset_class) === String(investBenchmarkClass)) || null,
    [investBenchmarkClass, investBenchmarkOptions]
  );
  const selectedRentabilityClass = useMemo(
    () => investRentabilityByClass.find((item) => String(item.asset_class) === String(investBenchmarkClass)) || null,
    [investBenchmarkClass, investRentabilityByClass]
  );
  const selectedBenchmarkClassStartDate = useMemo(() => {
    const selectedClass = String(selectedBenchmarkOption?.asset_class || "").trim();
    if (!selectedClass) return "";
    const assetIds = new Set(
      (investAssets || [])
        .filter((asset) => String(asset?.asset_class || "").trim() === selectedClass)
        .map((asset) => Number(asset?.id || 0))
        .filter((value) => value > 0)
    );
    const dates = [];
    for (const row of investTrades || []) {
      const assetClass = String(row?.asset_class || "").trim();
      const tradeDate = String(row?.date || "").trim();
      if (assetClass === selectedClass && /^\d{4}-\d{2}-\d{2}$/.test(tradeDate)) {
        dates.push(tradeDate);
      }
    }
    for (const row of investIncomes || []) {
      const incomeDate = String(row?.date || "").trim();
      const assetId = Number(row?.asset_id || 0);
      if (assetIds.has(assetId) && /^\d{4}-\d{2}-\d{2}$/.test(incomeDate)) {
        dates.push(incomeDate);
      }
    }
    dates.sort();
    return dates[0] || "";
  }, [investAssets, investIncomes, investTrades, selectedBenchmarkOption]);
  const investBenchmarkDateFrom = useMemo(() => {
    if (selectedBenchmarkClassStartDate && investRentabilityWindowStart) {
      return selectedBenchmarkClassStartDate > investRentabilityWindowStart
        ? selectedBenchmarkClassStartDate
        : investRentabilityWindowStart;
    }
    return selectedBenchmarkClassStartDate || investRentabilityWindowStart || "";
  }, [investRentabilityWindowStart, selectedBenchmarkClassStartDate]);
  const benchmarkSeriesData = useMemo(() => {
    const rows = Array.isArray(investBenchmarkRates) ? [...investBenchmarkRates] : [];
    rows.sort((a, b) => String(a.ref_date || "").localeCompare(String(b.ref_date || "")));
    if (!rows.length) return [];
    if ((selectedBenchmarkOption?.series_mode || "level") === "rate") {
      let acc = 1;
      return rows.map((row) => {
        const rate = Number(row?.value || 0);
        acc *= 1 + rate / 100;
        return {
          ref_date: String(row?.ref_date || "").slice(0, 10),
          benchmark_return_pct: (acc - 1) * 100,
        };
      });
    }
    const firstValue = Number(rows[0]?.value || 0);
    if (!Number.isFinite(firstValue) || firstValue <= 0) return [];
    return rows.map((row) => {
      const value = Number(row?.value || 0);
      const benchmarkReturnPct = Number.isFinite(value) && value > 0 ? ((value / firstValue) - 1) * 100 : 0;
      return {
        ref_date: String(row?.ref_date || "").slice(0, 10),
        benchmark_return_pct: benchmarkReturnPct,
      };
    });
  }, [investBenchmarkRates, selectedBenchmarkOption]);
  const benchmarkComparisonChartData = useMemo(() => {
    const byDate = new Map();
    for (const row of benchmarkSeriesData) {
      const key = String(row?.ref_date || "").slice(0, 10);
      if (!key) continue;
      byDate.set(key, {
        ref_date: key,
        benchmark_return_pct: Number(row?.benchmark_return_pct || 0),
        portfolio_return_pct: null,
      });
    }
    for (const row of investBenchmarkPortfolioSeries || []) {
      const key = String(row?.date || "").slice(0, 10);
      if (!key) continue;
      const current = byDate.get(key) || {
        ref_date: key,
        benchmark_return_pct: null,
        portfolio_return_pct: null,
      };
      current.portfolio_return_pct = Number(row?.return_pct || 0);
      byDate.set(key, current);
    }
    return Array.from(byDate.values()).sort((a, b) => String(a.ref_date).localeCompare(String(b.ref_date)));
  }, [benchmarkSeriesData, investBenchmarkPortfolioSeries]);
  const hasSufficientPortfolioBenchmarkHistory = useMemo(() => {
    const positivePoints = (investBenchmarkPortfolioSeries || []).filter((row) => Number(row?.market_value || 0) > 0);
    return positivePoints.length >= 2;
  }, [investBenchmarkPortfolioSeries]);
  const selectedBenchmarkReturnPct = benchmarkSeriesData.length
    ? Number(benchmarkSeriesData[benchmarkSeriesData.length - 1]?.benchmark_return_pct || 0)
    : 0;
  const selectedBenchmarkGapPct = selectedRentabilityClass
    ? Number(selectedRentabilityClass.total_return_pct || 0) - selectedBenchmarkReturnPct
    : 0;
  useEffect(() => {
    if (!investBenchmarkOptions.length) {
      setInvestBenchmarkClass("");
      return;
    }
    const current = investBenchmarkOptions.find((item) => String(item.asset_class) === String(investBenchmarkClass)) || null;
    const firstReady = investBenchmarkOptions.find((item) => item.benchmark_ready) || null;
    if (firstReady && (!current || !current.benchmark_ready)) {
      setInvestBenchmarkClass(String(firstReady.asset_class || ""));
      return;
    }
    if (current) {
      return;
    }
    const preferred =
      firstReady ||
      investBenchmarkOptions.find((item) => String(item.asset_class || "").trim() === String(investRentabilityHighlights.biggest?.asset_class || "").trim()) ||
      investBenchmarkOptions[0];
    setInvestBenchmarkClass(String(preferred?.asset_class || ""));
  }, [investBenchmarkClass, investBenchmarkOptions, investRentabilityHighlights.biggest]);
  useEffect(() => {
    if (!user || page !== "Investimentos" || investTab !== "Rentabilidade") return;
    if (!selectedBenchmarkOption?.benchmark_ready || !selectedBenchmarkOption?.index_name) {
      setInvestBenchmarkRates([]);
      setInvestBenchmarkPortfolioSeries([]);
      setInvestBenchmarkError("");
      setInvestBenchmarkLoading(false);
      return;
    }
    const dateTo = new Date().toISOString().slice(0, 10);
    const dateFrom = investBenchmarkDateFrom || shiftIsoDateByMonths(dateTo, 12) || dateTo;
    let cancelled = false;
    (async () => {
      try {
        setInvestBenchmarkLoading(true);
        setInvestBenchmarkError("");
        const rows = await getInvestIndexRates({
          index_name: selectedBenchmarkOption.index_name,
          date_from: dateFrom,
          date_to: dateTo,
          limit: 10000,
          auto_sync: true,
        });
        const portfolioRows = await getInvestPortfolioTimeseries({
          date_from: dateFrom,
          date_to: dateTo,
          asset_class: selectedBenchmarkOption.asset_class,
        });
        if (cancelled) return;
        setInvestBenchmarkRates(Array.isArray(rows) ? rows : []);
        setInvestBenchmarkPortfolioSeries(Array.isArray(portfolioRows) ? portfolioRows : []);
      } catch (err) {
        if (cancelled) return;
        setInvestBenchmarkRates([]);
        setInvestBenchmarkPortfolioSeries([]);
        setInvestBenchmarkError(String(err.message || err));
      } finally {
        if (cancelled) return;
        setInvestBenchmarkLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [investBenchmarkDateFrom, investTab, page, selectedBenchmarkOption, user]);
  const assetCreateIsFixedIncome = useMemo(
    () => isFixedIncomeClass(assetCreateClass),
    [assetCreateClass]
  );
  const assetEditIsFixedIncome = useMemo(
    () => isFixedIncomeClass(assetEditClass),
    [assetEditClass]
  );
  const assetEditCurrent = useMemo(
    () => investAssets.find((a) => String(a.id) === String(assetEditId)) || null,
    [investAssets, assetEditId]
  );
  const assetEditCurrentValueLabel = useMemo(() => {
    const value = Number(assetEditCurrent?.current_value);
    return Number.isFinite(value) ? brl.format(value) : "-";
  }, [assetEditCurrent, brl]);
  const assetEditLastUpdateLabel = useMemo(
    () => formatIsoDatePtBr(assetEditCurrent?.last_update),
    [assetEditCurrent]
  );
  const selectedTradeAsset = useMemo(
    () => investAssets.find((a) => String(a.id) === String(tradeAssetId)) || null,
    [investAssets, tradeAssetId]
  );
  const tradeAssetClassOptions = useMemo(() => {
    const labels = [];
    const seen = new Set();
    for (const a of investAssets) {
      const label = String(a.asset_class || "").trim();
      if (!label) continue;
      const key = classKey(label);
      if (seen.has(key)) continue;
      seen.add(key);
      labels.push(label);
    }
    return labels;
  }, [investAssets]);
  const tradeAssetOptions = useMemo(() => {
    if (!tradeAssetClassFilter) return [];
    const selectedKey = classKey(tradeAssetClassFilter);
    return investAssets.filter((a) => classKey(a.asset_class) === selectedKey);
  }, [investAssets, tradeAssetClassFilter]);
  const incomeAssetOptions = useMemo(() => {
    if (!incomeAssetClassFilter) return [];
    const selectedKey = classKey(incomeAssetClassFilter);
    return investAssets.filter((a) => classKey(a.asset_class) === selectedKey);
  }, [investAssets, incomeAssetClassFilter]);
  const investAssetsVisible = useMemo(() => {
    if (!investAssetsClassFilter) return investAssets;
    const selectedKey = classKey(investAssetsClassFilter);
    return investAssets.filter((a) => classKey(a.asset_class) === selectedKey);
  }, [investAssets, investAssetsClassFilter]);
  const investTradesVisible = useMemo(() => {
    const from = String(investTradeDateFrom || "").trim();
    const to = String(investTradeDateTo || "").trim();
    return (investTrades || []).filter((t) => {
      const date = String(t?.date || "").trim();
      if (!date) return false;
      if (from && date < from) return false;
      if (to && date > to) return false;
      return true;
    });
  }, [investTrades, investTradeDateFrom, investTradeDateTo]);
  const investIncomesVisible = useMemo(() => {
    const from = String(investIncomeDateFrom || "").trim();
    const to = String(investIncomeDateTo || "").trim();
    return (investIncomes || []).filter((i) => {
      const date = String(i?.date || "").trim();
      if (!date) return false;
      if (from && date < from) return false;
      if (to && date > to) return false;
      return true;
    });
  }, [investIncomes, investIncomeDateFrom, investIncomeDateTo]);
  const investIncomeTypesVisible = useMemo(() => {
    const orderedMeta = Array.isArray(investMeta?.income_types) ? investMeta.income_types : [];
    const seen = new Set();
    const out = [];
    for (const type of orderedMeta) {
      if ((investIncomesVisible || []).some((item) => String(item?.type || "") === String(type || ""))) {
        seen.add(String(type));
        out.push(String(type));
      }
    }
    for (const item of investIncomesVisible || []) {
      const type = String(item?.type || "").trim();
      if (type && !seen.has(type)) {
        seen.add(type);
        out.push(type);
      }
    }
    return out;
  }, [investIncomesVisible, investMeta?.income_types]);
  const investIncomeHistory = useMemo(() => {
    const buckets = new Map();
    for (const income of investIncomesVisible || []) {
      const date = String(income?.date || "").trim();
      const monthKey = /^\d{4}-\d{2}-\d{2}$/.test(date) ? date.slice(0, 7) : "";
      if (!monthKey) continue;
      const amount = Number(income?.amount || 0);
      const type = String(income?.type || "").trim() || "Outros";
      const base = buckets.get(monthKey) || { month: monthKey, amount: 0, count: 0 };
      const safeAmount = Number.isFinite(amount) ? amount : 0;
      base.amount += safeAmount;
      base.count += 1;
      base[type] = Number(base[type] || 0) + safeAmount;
      buckets.set(monthKey, base);
    }
    for (const row of buckets.values()) {
      for (const type of investIncomeTypesVisible) {
        if (!Object.prototype.hasOwnProperty.call(row, type)) {
          row[type] = 0;
        }
      }
    }
    return Array.from(buckets.values()).sort((a, b) => String(a.month).localeCompare(String(b.month)));
  }, [investIncomesVisible, investIncomeTypesVisible]);
  const investIncomeTypeTotals = useMemo(
    () =>
      investIncomeTypesVisible.map((type) => ({
        type,
        total: (investIncomesVisible || []).reduce(
          (acc, item) => acc + (String(item?.type || "").trim() === type ? Number(item?.amount || 0) || 0 : 0),
          0
        ),
      })),
    [investIncomeTypesVisible, investIncomesVisible]
  );
  const investIncomeHistorySummary = useMemo(() => {
    const total = investIncomeHistory.reduce((acc, row) => acc + Number(row?.amount || 0), 0);
    const peak = investIncomeHistory.reduce(
      (best, row) => (Number(row?.amount || 0) > Number(best?.amount || 0) ? row : best),
      null
    );
    const average = investIncomeHistory.length ? total / investIncomeHistory.length : 0;
    return {
      total,
      average,
      peakAmount: Number(peak?.amount || 0),
      peakMonth: peak?.month || "",
    };
  }, [investIncomeHistory]);
  useEffect(() => {
    if (!tradeAssetId) return;
    const stillValid = tradeAssetOptions.some((a) => String(a.id) === String(tradeAssetId));
    if (!stillValid) {
      setTradeAssetId("");
    }
  }, [tradeAssetOptions, tradeAssetId]);
  const tradeEffectiveClass = useMemo(
    () => selectedTradeAsset?.asset_class || tradeAssetClassFilter || "",
    [selectedTradeAsset, tradeAssetClassFilter]
  );
  const tradeAssetIsFixedIncome = useMemo(
    () => isFixedIncomeClass(tradeEffectiveClass),
    [tradeEffectiveClass]
  );
  const manualPriceAssets = useMemo(() => {
    const allowed = new Set(MANUAL_PRICE_CLASS_OPTIONS.map((item) => classKey(item)));
    const selectedKey = classKey(manualPriceClassFilter);
    return investAssets.filter((a) => {
      const key = classKey(a.asset_class);
      if (!allowed.has(key)) return false;
      if (!selectedKey) return false;
      return key === selectedKey;
    });
  }, [investAssets, manualPriceClassFilter]);
  useEffect(() => {
    if (!manualPriceClassFilter) return;
    const selected = classKey(manualPriceClassFilter);
    const stillExists = MANUAL_PRICE_CLASS_OPTIONS.some((item) => classKey(item) === selected);
    if (!stillExists) {
      setManualPriceClassFilter("");
    }
  }, [manualPriceClassFilter]);
  const tradeAssetIsUsStock = useMemo(
    () =>
      isUsStockClass(tradeEffectiveClass) ||
      String(selectedTradeAsset?.currency || "").toUpperCase() === "USD",
    [selectedTradeAsset, tradeEffectiveClass]
  );
  const tradeAssetIsCrypto = useMemo(
    () => isCryptoClass(tradeEffectiveClass),
    [tradeEffectiveClass]
  );
  const tradeQuantityMustBeInteger = useMemo(() => {
    const cls = classKey(tradeEffectiveClass);
    return cls === "acao_br" || cls === "acoes_br" || cls === "fii" || cls === "bdr";
  }, [tradeEffectiveClass]);
  const tradeQuantityStep = tradeQuantityMustBeInteger ? "1" : "0.00000001";
  const tradeQuantityMin = tradeQuantityMustBeInteger ? "1" : "0.00000001";
  const tradeQuantityPlaceholder = tradeQuantityMustBeInteger
    ? "Quantidade (inteiro)"
    : "Quantidade (aceita fracionado)";
  const tradeSideOptions = useMemo(
    () =>
      tradeAssetIsFixedIncome
        ? [
            { value: "BUY", label: "APLICAÇÃO" },
            { value: "SELL", label: "RESGATE" },
          ]
        : [
            { value: "BUY", label: "BUY" },
            { value: "SELL", label: "SELL" },
          ],
    [tradeAssetIsFixedIncome]
  );
  const tradeFixedIncomeIsSell = tradeAssetIsFixedIncome && tradeSide === "SELL";
  const tradeShowQuantityPrice = !tradeAssetIsFixedIncome;
  const tradeShowAppliedValue = tradeAssetIsFixedIncome;
  const tradeShowIrIof = tradeFixedIncomeIsSell;
  const tradeShowGenericTaxes = !tradeAssetIsFixedIncome || tradeFixedIncomeIsSell;
  const investManualQuoteAssets = useMemo(
    () =>
      investAssets.filter((a) => isFixedIncomeClass(a.asset_class || "")),
    [investAssets]
  );
  const selectedManualQuoteAsset = useMemo(
    () => investManualQuoteAssets.find((a) => String(a.id) === String(manualQuoteAssetId)) || null,
    [investManualQuoteAssets, manualQuoteAssetId]
  );
  const selectedManualQuoteIsManual = String(selectedManualQuoteAsset?.rentability_type || "").trim().toUpperCase() === "MANUAL";
  const investQuoteStatusNotice = useMemo(() => {
    const status = investPriceJobStatus;
    if (!status) return null;
    const parts = [];
    const lastFinishedAt = formatIsoDateTimePtBr(status.last_finished_at);
    const nextRunAt = formatIsoDateTimePtBr(status.next_run_at);
    if (lastFinishedAt) {
      const scopeLabel = String(status.last_run_scope || "").trim() === "manual" ? "manual" : "automática";
      const total = Number(status.last_total || 0);
      const saved = Number(status.last_saved_total || 0);
      if (total > 0) {
        parts.push(`Última cotação ${scopeLabel}: ${lastFinishedAt}; ativos salvos: ${saved}/${total}.`);
      } else {
        parts.push(`Última cotação ${scopeLabel}: ${lastFinishedAt}.`);
      }
    } else {
      parts.push("Ainda não há cotação automática registrada neste workspace.");
    }
    if (nextRunAt) {
      parts.push(`Próxima janela prevista: ${nextRunAt} (${status.start_at || "10:00"} às ${status.end_at || "17:10"}).`);
    }
    if (status.last_status === "warning" && Number(status.last_error_total || 0) > 0) {
      parts.push(`Falhas na última execução: ${Number(status.last_error_total || 0)}.`);
    }
    if (status.last_status === "error" && status.last_reason) {
      parts.push(`Última falha: ${String(status.last_reason)}.`);
    }
    return {
      level: ["warning", "error"].includes(String(status.last_status || "").trim()) ? "warning" : "success",
      message: parts.join(" "),
    };
  }, [investPriceJobStatus]);
  useEffect(() => {
    if (!investManualQuoteAssets.length) {
      setManualQuoteAssetId("");
      return;
    }
    if (manualQuoteAssetId && !investManualQuoteAssets.some((a) => String(a.id) === String(manualQuoteAssetId))) {
      setManualQuoteAssetId("");
    }
  }, [investManualQuoteAssets, manualQuoteAssetId]);
  useEffect(() => {
    if (!selectedManualQuoteAsset) {
      setManualQuoteMode("rentability");
      return;
    }
    if (!selectedManualQuoteIsManual && manualQuoteMode !== "current_value") {
      setManualQuoteMode("current_value");
      return;
    }
    if (selectedManualQuoteIsManual && !["rentability", "current_value"].includes(manualQuoteMode)) {
      setManualQuoteMode("rentability");
    }
  }, [selectedManualQuoteAsset, selectedManualQuoteIsManual, manualQuoteMode]);
  async function onLogin(e) {
    e.preventDefault();
    setAuthError("");
    setAuthInfo("");
    setLoginSyncNotice(null);
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email") || "");
    const password = String(form.get("password") || "");
    try {
      const data = await login(email, password);
      setToken(data.token);
      setUser(data.user);
      if (data?.login_sync_status?.should_notify && data?.login_sync_status?.message) {
        setLoginSyncNotice({
          level: String(data.login_sync_status.level || "success"),
          message: String(data.login_sync_status.message || ""),
        });
      }
    } catch (err) {
      setAuthError(String(err.message || err));
    }
  }

  async function onForgotPassword(e) {
    e.preventDefault();
    setAuthError("");
    setAuthInfo("");
    try {
      const out = await forgotPassword(forgotEmail);
      setAuthInfo(String(out?.message || "Se o e-mail existir, você receberá instruções para redefinir sua senha."));
    } catch (err) {
      setAuthError(String(err.message || err));
    }
  }

  async function onResetPassword(e) {
    e.preventDefault();
    setAuthError("");
    setAuthInfo("");
    if (!authResetToken) {
      setAuthError("Token de redefinição inválido.");
      return;
    }
    if (!resetNewPassword || !resetConfirmPassword) {
      setAuthError("Informe e confirme a nova senha.");
      return;
    }
    if (resetNewPassword !== resetConfirmPassword) {
      setAuthError("A confirmação da senha não confere.");
      return;
    }
    try {
      const out = await resetPassword(authResetToken, resetNewPassword);
      setAuthInfo(String(out?.message || "Sua senha foi alterada com sucesso."));
      setResetNewPassword("");
      setResetConfirmPassword("");
      setShowResetNewPassword(false);
      setShowResetConfirmPassword(false);
      setAuthResetToken("");
      setAuthMode("login");
      clearPasswordResetLocation();
    } catch (err) {
      setAuthError(String(err.message || err));
    }
  }

  async function reloadWorkspaces() {
    try {
      const rows = await getWorkspaces();
      setWorkspaces(Array.isArray(rows) ? rows : []);
      setWorkspaceMsg("");
    } catch (err) {
      setWorkspaces([]);
      setWorkspaceMsg(String(err.message || err));
    }
  }

  async function reloadWorkspaceMembers() {
    if (!canManageWorkspaceUsers) {
      setWorkspaceMembers([]);
      setWorkspacePermDrafts({});
      return;
    }
    setWorkspaceMembersLoading(true);
    try {
      const rows = await getWorkspaceMembers();
      const list = Array.isArray(rows) ? rows : [];
      setWorkspaceMembers(list);
      setWorkspacePermDrafts((prev) => {
        const next = { ...prev };
        for (const m of list) {
          const role = String(m.workspace_role || "").toUpperCase();
          if (role !== "GUEST") continue;
          const key = String(m.user_id || "");
          next[key] = buildPermissionsDraft(m);
        }
        return next;
      });
      setWorkspaceManageMsg("");
    } catch (err) {
      setWorkspaceMembers([]);
      setWorkspaceManageMsg(String(err.message || err));
    } finally {
      setWorkspaceMembersLoading(false);
    }
  }

  async function reloadAdminWorkspaces() {
    if (!isSuperAdmin) {
      setAdminWorkspaces([]);
      return;
    }
    try {
      const rows = await getAdminWorkspaces();
      setAdminWorkspaces(Array.isArray(rows) ? rows : []);
      setAdminMsg("");
    } catch (err) {
      setAdminWorkspaces([]);
      setAdminMsg(String(err.message || err));
    }
  }

  async function onSwitchWorkspace(e) {
    const targetId = String(e.target.value || "");
    if (!targetId || targetId === currentWorkspaceId) return;
    setWorkspaceSwitchingId(targetId);
    setWorkspaceMsg("");
    investReloadSeqRef.current += 1;
    clearInvestState();
    try {
      const out = await switchWorkspace(Number(targetId));
      setToken(out.token);
      setUser(out.user);
    } catch (err) {
      setWorkspaceMsg(String(err.message || err));
    } finally {
      setWorkspaceSwitchingId("");
    }
  }

  async function onAddWorkspaceGuest(e) {
    e.preventDefault();
    const email = String(workspaceInviteEmail || "").trim().toLowerCase();
    const displayName = String(workspaceInviteName || "").trim();
    if (!email) {
      setWorkspaceManageMsg("Informe o e-mail do usuário para convidar.");
      return;
    }
    setWorkspaceManageMsg("");
    await withPendingAction("workspaceInvite", async () => {
      try {
      await createWorkspaceMember({
        email,
        role: "GUEST",
        display_name: displayName || undefined,
      });
      setWorkspaceInviteEmail("");
      setWorkspaceInviteName("");
      const successMsg = "Convidado salvo.";
      setWorkspaceManageMsg("Convidado atualizado com sucesso. Se o usuário for novo, ele receberá um e-mail para criar a senha.");
      showGlobalSuccess(successMsg);
      await reloadWorkspaceMembers();
      await reloadWorkspaces();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
    });
  }

  async function onRenameCurrentWorkspace(e) {
    e.preventDefault();
    if (!canManageWorkspaceUsers && !isSuperAdmin && !isWorkspaceOwner) {
      setWorkspaceManageMsg("Sem permissão para renomear o workspace.");
      return;
    }
    const workspace_name = String(workspaceNameDraft || "").trim();
    if (!workspace_name) {
      setWorkspaceManageMsg("Informe o nome do workspace.");
      return;
    }
    await withPendingAction("workspaceRename", async () => {
      try {
      const out = await renameCurrentWorkspace({ workspace_name });
      const nextName = String(out?.workspace?.workspace_name || workspace_name);
      setUser((prev) => (prev ? { ...prev, workspace_name: nextName } : prev));
      setWorkspaceNameDraft(nextName);
      setWorkspaceManageMsg("Nome do workspace atualizado.");
      showGlobalSuccess("Workspace renomeado.");
      await reloadWorkspaces();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
    });
  }

  function onToggleMemberPermission(memberUserId, module, field, checked) {
    const key = String(memberUserId || "");
    if (!key || !module) return;
    setWorkspacePermDrafts((prev) => {
      const base = Array.isArray(prev[key]) && prev[key].length ? prev[key] : buildPermissionsDraft({});
      const nextRows = base.map((row) => {
        if (String(row.module) !== String(module)) return row;
        return { ...row, [field]: Boolean(checked) };
      });
      return { ...prev, [key]: nextRows };
    });
  }

  async function onSaveMemberPermissions(memberUserId) {
    const key = String(memberUserId || "");
    const payload = Array.isArray(workspacePermDrafts[key]) ? workspacePermDrafts[key] : [];
    setWorkspaceManageMsg("");
    await withPendingAction(`workspacePerms-${memberUserId}`, async () => {
      try {
      await updateWorkspaceMemberPermissions(Number(memberUserId), { permissions: payload });
      setWorkspaceManageMsg("Permissões salvas.");
      showGlobalSuccess("Permissões salvas.");
      await reloadWorkspaceMembers();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
    });
  }

  async function onRemoveWorkspaceMember(memberUserId) {
    if (!window.confirm("Remover este membro do workspace atual?")) return;
    setWorkspaceManageMsg("");
    await withPendingAction(`workspaceRemove-${memberUserId}`, async () => {
      try {
      await deleteWorkspaceMember(Number(memberUserId));
      setWorkspaceManageMsg("Membro removido.");
      showGlobalSuccess("Membro removido.");
      await reloadWorkspaceMembers();
      await reloadWorkspaces();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
    });
  }

  async function onCreateAdminWorkspace(e) {
    e.preventDefault();
    const workspace_name = String(adminWorkspaceName || "").trim();
    const owner_email = String(adminOwnerEmail || "").trim().toLowerCase();
    const owner_display_name = String(adminOwnerDisplayName || "").trim();
    if (!workspace_name || !owner_email) {
      setAdminMsg("Informe nome do workspace e e-mail do owner.");
      return;
    }
    setAdminMsg("");
    await withPendingAction("adminCreateWorkspace", async () => {
      try {
      await createAdminWorkspace({
        workspace_name,
        owner_email,
        owner_display_name: owner_display_name || undefined,
      });
      setAdminWorkspaceName("");
      setAdminOwnerEmail("");
      setAdminOwnerDisplayName("");
      setAdminMsg("Workspace criado com sucesso. Se o owner for novo, ele receberá um e-mail para criar a senha.");
      showGlobalSuccess("Workspace criado.");
      await Promise.all([reloadAdminWorkspaces(), reloadWorkspaces()]);
    } catch (err) {
      setAdminMsg(String(err.message || err));
    }
    });
  }

  async function onToggleAdminWorkspaceStatus(workspaceId, currentStatus) {
    const target = normalizeWorkspaceStatus(currentStatus) === "active" ? "blocked" : "active";
    setAdminStatusUpdatingId(String(workspaceId));
    setAdminMsg("");
    await withPendingAction(`adminStatus-${workspaceId}`, async () => {
      try {
      await updateAdminWorkspaceStatus(Number(workspaceId), { status: target });
      setAdminMsg(`Workspace ${workspaceId} atualizado para ${target}.`);
      showGlobalSuccess(`Workspace ${target === "active" ? "ativado" : "bloqueado"}.`);
      await Promise.all([reloadAdminWorkspaces(), reloadWorkspaces()]);
    } catch (err) {
      setAdminMsg(String(err.message || err));
    } finally {
      setAdminStatusUpdatingId("");
    }
    });
  }

  async function onSaveProfile(e) {
    e.preventDefault();
    setProfileMsg("");
    const email = String(profileEmail || "").trim().toLowerCase();
    const displayName = String(profileDisplayName || "").trim();
    const avatarData = String(profileAvatarData || "").trim();
    const currentPassword = String(profileCurrentPassword || "");
    const newPassword = String(profileNewPassword || "");
    const confirmPassword = String(profileConfirmPassword || "");

    if (!email) {
      setProfileMsg("Informe um e-mail válido.");
      return;
    }
    if (newPassword || confirmPassword || currentPassword) {
      if (newPassword !== confirmPassword) {
        setProfileMsg("A confirmação da nova senha não confere.");
        return;
      }
      if (newPassword && newPassword.length < 6) {
        setProfileMsg("A nova senha deve ter pelo menos 6 caracteres.");
        return;
      }
      if (!currentPassword) {
        setProfileMsg("Informe a senha atual para alterar a senha.");
        return;
      }
    }

    setProfileSaving(true);
    try {
      const updated = await updateMeProfile({
        display_name: displayName || null,
        email,
        avatar_data: avatarData || null,
        current_password: currentPassword || null,
        new_password: newPassword || null,
      });
      setUser(updated);
      setProfileCurrentPassword("");
      setProfileNewPassword("");
      setProfileConfirmPassword("");
      setProfileMsg("Perfil atualizado.");
      showGlobalSuccess("Perfil salvo.");
    } catch (err) {
      setProfileMsg(String(err.message || err));
    } finally {
      setProfileSaving(false);
    }
  }

  async function onSelectProfileAvatar(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!String(file.type || "").startsWith("image/")) {
      setProfileMsg("Selecione uma imagem válida para o avatar.");
      return;
    }
    if (file.size > 1_000_000) {
      setProfileMsg("O avatar deve ter no máximo 1 MB.");
      return;
    }
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error("Falha ao ler a imagem."));
      reader.readAsDataURL(file);
    }).catch((err) => {
      setProfileMsg(String(err.message || err));
      return "";
    });
    if (!dataUrl) return;
    setProfileAvatarData(String(dataUrl));
    setProfileMsg("");
  }

  async function reloadAllData() {
    const jobs = [];
    if (canViewContas) {
      jobs.push(
        getAccounts()
          .then((rows) => setAccounts(Array.isArray(rows) ? rows : []))
          .catch(() => setAccounts([]))
      );
      jobs.push(
        getCategories()
          .then((rows) => setCategories(Array.isArray(rows) ? rows : []))
          .catch(() => setCategories([]))
      );
    } else {
      setAccounts([]);
      setCategories([]);
    }

    if (canViewDashboard) {
      jobs.push(
        getKpis()
          .then((dash) => setKpis(dash || null))
          .catch(() => setKpis(null))
      );
    } else {
      setKpis(null);
    }

    if (canViewLancamentos) {
      jobs.push(
        getTransactions({ view: txView })
          .then((tx) => setTransactions(Array.isArray(tx) ? tx : []))
          .catch(() => setTransactions([]))
      );
    } else {
      setTransactions([]);
      setCommitmentEdit(null);
    }
    await Promise.all(jobs);
  }

  async function reloadCardsData() {
    if (!canViewContas) {
      setCards([]);
      setCardInvoices([]);
      return;
    }
    const [cardRows, invoiceRows] = await Promise.all([getCards(), getCardInvoices({ status: "OPEN" })]);
    setCards(Array.isArray(cardRows) ? cardRows : []);
    setCardInvoices(Array.isArray(invoiceRows) ? invoiceRows : []);
  }

  async function reloadDashboard(params = {}) {
    if (!canViewDashboard) {
      setDashMsg("");
      return;
    }
    const monthRange = getCurrentMonthRange();
    const rawFrom = params.date_from ?? dashDateFrom;
    const rawTo = params.date_to ?? dashDateTo;
    const filters = {
      date_from: String(rawFrom || "").trim() || monthRange.from,
      date_to: String(rawTo || "").trim() || monthRange.to,
      account: params.account ?? dashAccount,
      view: params.view ?? dashView,
    };
    const wealthFilters = buildDashboardWealthFilters(filters);
    try {
      const [k, wm, e, ab, cs] = await Promise.all([
        getDashboardKpis(filters),
        getDashboardWealthMonthly(wealthFilters),
        getDashboardExpenses(filters),
        // Saldo de contas sempre no acumulado real (sem filtros de período/conta/visão).
        getDashboardAccountBalance({ view: "caixa" }),
        getDashboardCommitmentsSummary(filters),
      ]);
      setDashKpis(k);
      setDashWealthMonthly(wm || []);
      setDashExpenses(e || []);
      setDashAccountBalance(ab || []);
      setDashCommitments(cs || { a_vencer: 0, vencidos: 0 });
      setDashMsg("");
    } catch (err) {
      setDashMsg(String(err.message || err));
    }
  }

  async function reloadTransactions(params = {}) {
    if (!canViewLancamentos) {
      setTransactions([]);
      setCommitmentEdit(null);
      return;
    }
    const tx = await getTransactions({ view: params.view ?? txView });
    setTransactions(tx);
    setCommitmentEdit(null);
  }

  async function syncInvestRentabilityBeforeLoad({ force = false } = {}) {
    if (!canAddInvestimentos) {
      return null;
    }
    const now = Date.now();
    if (!force && now - investRentabilityLastSyncRef.current < INVEST_RENTABILITY_MIN_SYNC_INTERVAL_MS) {
      return null;
    }
    setInvestRentabilitySyncRunning(true);
    try {
      const out = await updateAllInvestRentability({}, INVEST_RENTABILITY_TIMEOUT_MS);
      investRentabilityLastSyncRef.current = Date.now();
      const updated = Number(out?.updated || 0);
      const errors = Number(out?.errors || 0);
      if (errors > 0) {
        setInvestRentabilityMsg(`Rentabilidade atualizada com pendências (${updated} atualizados, ${errors} com erro).`);
      } else {
        setInvestRentabilityMsg(`Rentabilidade atualizada (${updated} ativo${updated === 1 ? "" : "s"}).`);
      }
      return out;
    } catch (err) {
      setInvestRentabilityMsg(`Rentabilidade não atualizada automaticamente: ${String(err.message || err)}`);
      return null;
    } finally {
      setInvestRentabilitySyncRunning(false);
    }
  }

  async function onLoadInvestDivergenceReport() {
    if (!canAddInvestimentos) {
      setInvestDivergenceReport([]);
      setInvestDivergenceMsg("Sem permissão para gerar o relatório de divergência.");
      return;
    }
    setInvestDivergenceRunning(true);
    setInvestDivergenceMsg("");
    try {
      const threshold = parseLocaleNumber(investDivergenceThreshold || "");
      const out = await getInvestRentabilityDivergenceReport(
        {
          only_auto: true,
          threshold_pct: Number.isFinite(threshold) ? Math.max(0, threshold) : 0,
          limit: 200,
        },
        INVEST_DIVERGENCE_TIMEOUT_MS
      );
      const rows = Array.isArray(out?.rows) ? out.rows : [];
      setInvestDivergenceReport(rows);
      setInvestDivergenceMsg(`Relatório gerado: ${rows.length} divergência(s) encontrada(s).`);
    } catch (err) {
      setInvestDivergenceReport([]);
      setInvestDivergenceMsg(`Erro ao gerar relatório de divergência: ${String(err.message || err)}`);
    } finally {
      setInvestDivergenceRunning(false);
    }
  }

  async function reloadInvestData(options = {}) {
    if (!canViewInvestimentos) {
      investReloadSeqRef.current += 1;
      clearInvestState();
      return;
    }
    const requestSeq = ++investReloadSeqRef.current;
    const { syncRentability = false, forceRentabilitySync = false } = options || {};
    if (syncRentability) {
      await syncInvestRentabilityBeforeLoad({ force: forceRentabilitySync });
    }
    const results = await Promise.allSettled([
      getInvestMeta(),
      getInvestAssets(),
      getInvestTrades(),
      getInvestIncomes(),
      getInvestPrices(),
      getInvestPriceJobStatus(),
      getInvestPortfolio(),
      getInvestSummary(),
    ]);
    if (requestSeq !== investReloadSeqRef.current) return;
    const [metaRes, assetsRes, tradesRes, incomesRes, pricesRes, quoteJobStatusRes, portfolioRes, summaryRes] = results;
    const hasAnySuccess = results.some((item) => item.status === "fulfilled");
    const hasAnyFailure = results.some((item) => item.status === "rejected");
    const meta = metaRes.status === "fulfilled" ? metaRes.value : null;
    const assets = assetsRes.status === "fulfilled" ? assetsRes.value : [];
    const trades = tradesRes.status === "fulfilled" ? tradesRes.value : [];
    const incomes = incomesRes.status === "fulfilled" ? incomesRes.value : [];
    const prices = pricesRes.status === "fulfilled" ? pricesRes.value : [];
    const quoteJobStatus = quoteJobStatusRes.status === "fulfilled" ? quoteJobStatusRes.value : null;
    const portfolio = portfolioRes.status === "fulfilled" ? portfolioRes.value : { positions: [] };
    const summary = summaryRes.status === "fulfilled" ? summaryRes.value : null;
    setInvestMeta(meta || { asset_classes: [], asset_sectors: [], income_types: [] });
    setInvestAssets(assets || []);
    setInvestTrades(trades || []);
    setInvestIncomes(incomes || []);
    setInvestPrices(prices || []);
    setInvestPriceJobStatus(quoteJobStatus || null);
    setInvestPortfolio(portfolio || { positions: [] });
    setInvestSummaryData(
      summary || {
        assets_count: 0,
        total_invested: 0,
        total_market: 0,
        total_income: 0,
        total_realized: 0,
        total_unrealized: 0,
        total_return: 0,
        total_return_pct: 0,
        broker_balance: 0,
      }
    );
    if (hasAnyFailure) {
      const failed = results
        .filter((item) => item.status === "rejected")
        .map((item) => String(item.reason?.message || item.reason || "").trim())
        .filter(Boolean);
      if (!hasAnySuccess) {
        throw new Error(failed[0] || "Falha ao carregar dados de investimentos.");
      }
      console.error("Falhas parciais ao recarregar investimentos", failed);
    }
  }

  async function onCreateTransaction(e) {
    e.preventDefault();
    setTxMsg("");
    if (!canAddLancamentos) {
      setTxMsg("Sem permissão para incluir lançamentos.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const description = String(form.get("description") || "").trim();
    const amountAbs = parseLocaleNumber(form.get("amount") || "0");
    const accountId = txAccountId ? Number(txAccountId) : NaN;
    const categoryIdRaw = String(txCategoryId || "");
    const categoryId = categoryIdRaw ? Number(categoryIdRaw) : null;
    const category = categories.find((c) => Number(c.id) === Number(categoryId));
    const method = String(txMethodEffective || "").trim();
    const futurePaymentMethod = txIsFutureTab ? String(txFuturePaymentMethod || "PIX").trim() : "";
    const notes = String(form.get("notes") || "").trim();
    const dateInput = String(form.get("date") || "");
    const dueDayInput = Number(sanitizeIntegerInputValue(form.get("due_day") || "0", 2));
    const repeatMonthsInput = Number(sanitizeIntegerInputValue(form.get("repeat_months") || "1", 3));
    const effectiveKind = String(category?.kind || "").trim();
    const sourceAccountId = txSourceAccountId ? Number(txSourceAccountId) : NaN;
    const selectedCardId = txCardId ? Number(txCardId) : NaN;
    const cardLinkedAccountId = selectedTxCard ? Number(selectedTxCard.card_account_id) : NaN;
    const effectiveAccountId = txIsExpenseCredit && Number.isFinite(cardLinkedAccountId) ? cardLinkedAccountId : accountId;
    const isFutureExpense = txIsExpense && !txIsTransfer && method === "Futuro";
    const date = isFutureExpense ? new Date().toISOString().slice(0, 10) : dateInput;
    const dueDay = isFutureExpense ? dueDayInput : null;
    const repeatMonths = isFutureExpense ? repeatMonthsInput : null;

    if (!Number.isFinite(categoryId || NaN) || !category) {
      setTxMsg("Selecione uma categoria para definir o tipo do lançamento.");
      return;
    }
    if (txIsFutureTab && effectiveKind !== "Despesa") {
      setTxMsg("Na aba Compromissos, selecione uma categoria de Despesa.");
      return;
    }
    if (
      (!isFutureExpense && !date) ||
      !Number.isFinite(effectiveAccountId) ||
      effectiveAccountId <= 0 ||
      !Number.isFinite(amountAbs) ||
      amountAbs <= 0
    ) {
      setTxMsg("Preencha data, valor (> 0), categoria e conta válida.");
      return;
    }
    if (!txMethodOptions.includes(method)) {
      setTxMsg("Método inválido para o tipo da categoria selecionada.");
      return;
    }
    if (isFutureExpense) {
      if (!Number.isInteger(repeatMonths) || repeatMonths < 1 || repeatMonths > 120) {
        setTxMsg("Informe quantos meses replicar (1 a 120).");
        return;
      }
      if (futurePaymentMethod === "Credito" && (!Number.isFinite(selectedCardId) || selectedCardId <= 0)) {
        setTxMsg("Selecione o cartão de crédito para o compromisso.");
        return;
      }
      if (futurePaymentMethod !== "Credito") {
        if (!Number.isInteger(dueDay) || dueDay < 1 || dueDay > 31) {
          setTxMsg("Informe um dia de vencimento entre 1 e 31.");
          return;
        }
      }
    }
    if (txIsTransfer && (!Number.isFinite(sourceAccountId) || sourceAccountId <= 0)) {
      setTxMsg("Para Transferência, selecione a conta origem.");
      return;
    }
    if (txIsExpense && !txIsTransfer) {
      if (method === "Credito" && (!Number.isFinite(selectedCardId) || selectedCardId <= 0)) {
        setTxMsg("Para despesa no Crédito, selecione um cartão.");
        return;
      }
    }

    await withPendingAction("createTransaction", async () => {
      try {
      const out = await createTransaction({
        date,
        description,
        amount: Math.abs(amountAbs),
        account_id: effectiveAccountId,
        category_id: categoryId,
        kind: effectiveKind,
        source_account_id: txIsTransfer ? sourceAccountId : null,
        card_id:
          (
            (txIsExpense && !txIsTransfer && method === "Credito") ||
            (isFutureExpense && futurePaymentMethod === "Credito")
          ) &&
          Number.isFinite(selectedCardId)
            ? selectedCardId
            : null,
        method: method || null,
        future_payment_method: isFutureExpense ? futurePaymentMethod : null,
        notes: notes || null,
        due_day: isFutureExpense && futurePaymentMethod !== "Credito" ? dueDay : null,
        repeat_months: isFutureExpense ? repeatMonths : null,
      });
      let successMsg = "Lançamento salvo.";
      formEl.reset();
      setTxCategoryId("");
      setTxMethod(txIsFutureTab ? "Futuro" : "PIX");
      setTxFuturePaymentMethod("PIX");
      setTxSourceAccountId("");
      setTxCardId("");
      if (out?.mode === "transfer") {
        successMsg = "Transferência registrada (débito na origem e crédito no destino).";
      } else if (out?.mode === "credit_card_charge") {
        successMsg = "Compra no crédito registrada. A despesa será lançada no pagamento da fatura.";
      } else if (out?.mode === "future_credit_schedule") {
        successMsg =
          `Compromisso no cartão agendado (${Number(out?.created || 0)}x): ${String(out?.first_date || "-")} até ${String(out?.last_date || "-")}.`
        ;
      } else if (out?.mode === "future_schedule") {
        successMsg =
          `Despesa futura agendada (${Number(out?.created || 0)}x): ${String(out?.first_date || "-")} até ${String(out?.last_date || "-")}.`
        ;
      } else if (method === "Futuro") {
        successMsg = "Despesa futura agendada. Ela só impactará o caixa na data informada.";
      }
      setTxMsg(successMsg);
      showGlobalSuccess(successMsg);
      try {
        await reloadTransactions();
        await reloadCardsData();
        if (canViewDashboard) {
          const dash = await getKpis();
          setKpis(dash);
        }
        await reloadDashboard();
        await reloadInvestData();
      } catch (refreshErr) {
        setTxMsg(`${successMsg} Alguns painéis não foram recarregados: ${String(refreshErr.message || refreshErr)}`);
      }
    } catch (err) {
      setTxMsg(`Erro ao salvar lançamento: ${String(err.message || err)}`);
    }
    });
  }

  async function onDeleteTransaction(id, scope = "single") {
    if (!canDeleteLancamentos) {
      setTxMsg("Sem permissão para excluir lançamentos.");
      return;
    }
    await withPendingAction(`deleteTransaction-${id}-${scope}`, async () => {
      try {
      await deleteTransaction(id, { scope });
      setTxMsg("Lançamento excluído.");
      showGlobalSuccess("Lançamento excluído.");
      await reloadTransactions();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setTxMsg(String(err.message || err));
    }
    });
  }

  function isCommitmentTx(tx) {
    const m = normalizeText(tx?.method || "");
    return m === "futuro" || m === "agendado";
  }

  function onStartPayCommitment(tx) {
    if (!canAddLancamentos) {
      setTxMsg("Sem permissão para liquidar compromissos.");
      return;
    }
    const accountByName = (accounts || []).find((a) => String(a.name || "") === String(tx?.account || ""));
    const fallback = (accounts || []).find((a) => {
      const t = normalizeAccountType(a.type);
      return t === "Banco" || t === "Dinheiro";
    });
    const accId = accountByName?.id ?? fallback?.id ?? "";
    setCommitmentEdit({
      id: tx?.id,
      payment_date: String(tx?.date || "").slice(0, 10),
      account_id: accId ? String(accId) : "",
      amount: formatLocalizedNumber(Math.abs(Number(tx?.amount_brl || 0)), 2),
      notes: String(tx?.notes || ""),
    });
  }

  async function onDeleteCommitment(tx) {
    if (!canDeleteLancamentos) {
      setTxMsg("Sem permissão para excluir compromissos.");
      return;
    }
    const deleteFuture = window.confirm(
      "Excluir este compromisso e todos os próximos da mesma série?\n\nOK = este e próximos\nCancelar = somente este mês"
    );
    const scope = deleteFuture ? "future" : "single";
    await onDeleteTransaction(tx.id, scope);
  }

  async function onDeleteCreditCommitment(tx) {
    if (!canDeleteLancamentos) {
      setTxMsg("Sem permissão para excluir compromissos no cartão.");
      return;
    }
    const rawId = String(tx?.id || "");
    const match = rawId.match(/^ccf-(\d+)$/i);
    if (!match) {
      setTxMsg("ID inválido para exclusão do compromisso no cartão.");
      return;
    }
    const deleteFuture = window.confirm(
      "Excluir este compromisso do cartão e os próximos da mesma série?\n\nOK = este e próximos\nCancelar = somente este mês"
    );
    const scope = deleteFuture ? "future" : "single";
    await withPendingAction(`deleteCreditCommitment-${match[1]}-${scope}`, async () => {
      try {
      await deleteCreditCommitment(Number(match[1]), { scope });
      await reloadTransactions();
      await reloadCardsData();
      await reloadDashboard();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      setTxMsg("Compromisso no cartão excluído.");
      showGlobalSuccess("Compromisso excluído.");
    } catch (err) {
      setTxMsg(String(err.message || err));
    }
    });
  }

  async function onConfirmPayCommitment() {
    if (!canAddLancamentos) {
      setTxMsg("Sem permissão para confirmar pagamentos de compromissos.");
      return;
    }
    if (!commitmentEdit?.id) return;
    const amountVal = parseLocaleNumber(commitmentEdit.amount || "");
    const accountId = Number(commitmentEdit.account_id || 0);
    const paymentDate = String(commitmentEdit.payment_date || "").trim();
    if (!paymentDate) {
      setTxMsg("Informe a data de pagamento.");
      return;
    }
    if (!Number.isFinite(accountId) || accountId <= 0) {
      setTxMsg("Selecione a conta de pagamento.");
      return;
    }
    if (!Number.isFinite(amountVal) || amountVal <= 0) {
      setTxMsg("Informe um valor válido para pagamento.");
      return;
    }
    await withPendingAction(`payCommitment-${commitmentEdit.id}`, async () => {
      try {
      await settleCommitmentTransaction(Number(commitmentEdit.id), {
        payment_date: paymentDate,
        account_id: accountId,
        amount: amountVal,
        notes: String(commitmentEdit.notes || "").trim() || null,
      });
      setCommitmentEdit(null);
      setTxMsg("Compromisso pago e convertido em lançamento real de caixa.");
      showGlobalSuccess("Compromisso pago.");
      await reloadTransactions();
      await reloadCardsData();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setTxMsg(`Erro ao confirmar pagamento: ${String(err.message || err)}`);
    }
    });
  }

  async function onCreateInvestAsset(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para cadastrar ativos.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const symbol = String(form.get("symbol") || "").trim().toUpperCase();
    const name = String(form.get("name") || "").trim();
    const assetClass = String(assetCreateClass || form.get("asset_class") || "");
    const sector = String(form.get("sector") || "Não definido");
    const currency = String(form.get("currency") || "BRL").toUpperCase();
    const brokerAccountIdRaw = String(form.get("broker_account_id") || "");
    if (!symbol || !name || !assetClass) {
      setInvestMsg("Informe símbolo, nome e classe do ativo.");
      return;
    }
    const rentCfg = buildAssetRentabilityPayload({
      isFixedIncome: isFixedIncomeClass(assetClass),
      rentabilityType: assetCreateRentabilityType,
      indexPctInput: assetCreateIndexPct,
      spreadRateInput: assetCreateSpreadRate,
      fixedRateInput: assetCreateFixedRate,
    });
    if (!rentCfg.ok) {
      setInvestMsg(rentCfg.error || "Configuração de rentabilidade inválida.");
      return;
    }
    await withPendingAction("createInvestAsset", async () => {
      try {
      await createInvestAsset({
        symbol,
        name,
        asset_class: assetClass,
        sector,
        currency,
        broker_account_id: brokerAccountIdRaw ? Number(brokerAccountIdRaw) : null,
        ...rentCfg.payload,
      });
      formEl.reset();
      setAssetCreateClass("");
      setAssetCreateRentabilityType("");
      setAssetCreateIndexPct("");
      setAssetCreateSpreadRate("");
      setAssetCreateFixedRate("");
      setInvestMsg("Ativo salvo.");
      showGlobalSuccess("Ativo salvo.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onUpdateInvestAsset() {
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para editar ativos.");
      return;
    }
    if (!assetEditId || !assetEditSymbol.trim() || !assetEditName.trim() || !assetEditClass) {
      setInvestMsg("Selecione e preencha os dados do ativo.");
      return;
    }
    const rentCfg = buildAssetRentabilityPayload({
      isFixedIncome: assetEditIsFixedIncome,
      rentabilityType: assetEditRentabilityType,
      indexPctInput: assetEditIndexPct,
      spreadRateInput: assetEditSpreadRate,
      fixedRateInput: assetEditFixedRate,
    });
    if (!rentCfg.ok) {
      setInvestMsg(rentCfg.error || "Configuração de rentabilidade inválida.");
      return;
    }
    await withPendingAction("updateInvestAsset", async () => {
      try {
      await updateInvestAsset(Number(assetEditId), {
        symbol: assetEditSymbol.trim().toUpperCase(),
        name: assetEditName.trim(),
        asset_class: assetEditClass,
        sector: assetEditSector || "Não definido",
        currency: (assetEditCurrency || "BRL").toUpperCase(),
        broker_account_id: assetEditBrokerId ? Number(assetEditBrokerId) : null,
        ...rentCfg.payload,
      });
      setInvestMsg("Ativo atualizado.");
      showGlobalSuccess("Ativo atualizado.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteInvestAsset(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir ativos.");
      return;
    }
    await withPendingAction(`deleteInvestAsset-${id}`, async () => {
      try {
      await deleteInvestAsset(Number(id));
      setInvestMsg("Ativo excluído.");
      showGlobalSuccess("Ativo excluído.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onCreateInvestTrade(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para registrar operações.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const assetId = Number(tradeAssetId || form.get("asset_id"));
    const date = String(form.get("date") || "");
    const side = String(tradeSide || form.get("side") || "BUY").toUpperCase();
    const quantityRaw = parseLocaleNumber(form.get("quantity") || "0");
    const priceRaw = parseLocaleNumber(form.get("price") || "0");
    const appliedValue = parseLocaleNumber(form.get("applied_value") || "0");
    const irIofPct = parseLocaleNumber(form.get("ir_iof") || "0");
    const exchangeRate = parseLocaleNumber(tradeExchangeRate || form.get("exchange_rate") || "0");
    const fees = parseLocaleNumber(form.get("fees") || "0");
    const taxesRaw = parseLocaleNumber(form.get("taxes") || "0");
    const note = String(form.get("note") || "").trim();
    let quantity = quantityRaw;
    let price = priceRaw;
    let taxes = Number.isFinite(taxesRaw) ? taxesRaw : 0;
    if (tradeAssetIsFixedIncome) {
      if (!assetId || !date || !Number.isFinite(appliedValue) || appliedValue <= 0) {
        setInvestMsg("Preencha ativo, data e valor aplicado.");
        return;
      }
      if (!Number.isFinite(irIofPct) || irIofPct < 0 || irIofPct > 100) {
        setInvestMsg("IR/IOF (%) deve estar entre 0 e 100.");
        return;
      }
      quantity = 1;
      price = appliedValue;
      if (side === "SELL") {
        const irIofAmount = appliedValue * (irIofPct / 100);
        taxes = taxes + irIofAmount;
      } else if (irIofPct > 0) {
        setInvestMsg("IR/IOF (%) deve ser informado apenas em RESGATE para renda fixa.");
        return;
      }
    } else {
      if (!assetId || !date || !Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) {
        setInvestMsg("Preencha ativo, data, quantidade e preço.");
        return;
      }
      if (tradeQuantityMustBeInteger && !Number.isInteger(quantity)) {
        setInvestMsg("Para esta classe, a quantidade deve ser inteira.");
        return;
      }
    }
    if (tradeAssetIsUsStock && (!Number.isFinite(exchangeRate) || exchangeRate <= 0)) {
      setInvestMsg("Para Stocks US, informe a cotação USD/BRL.");
      return;
    }
    await withPendingAction("createInvestTrade", async () => {
      try {
      await createInvestTrade({
        asset_id: assetId,
        date,
        side,
        quantity,
        price,
        exchange_rate: tradeAssetIsUsStock ? exchangeRate : null,
        fees: Number.isFinite(fees) ? fees : 0,
        taxes: taxes,
        note: note || null,
      });
      formEl.reset();
      setTradeAssetId("");
      setTradeSide("BUY");
      setTradeExchangeRate("");
      setInvestMsg("Operação salva.");
      showGlobalSuccess("Operação salva.");
      await reloadInvestData();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteInvestTrade(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir operações.");
      return;
    }
    await withPendingAction(`deleteInvestTrade-${id}`, async () => {
      try {
      await deleteInvestTrade(Number(id));
      setInvestMsg("Operação excluída.");
      showGlobalSuccess("Operação excluída.");
      await reloadInvestData();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onCreateInvestIncome(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para registrar proventos.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const assetId = Number(form.get("asset_id"));
    const date = String(form.get("date") || "");
    const type = String(form.get("type") || "");
    const amount = parseLocaleNumber(form.get("amount") || "0");
    const creditAccountIdRaw = String(form.get("credit_account_id") || "").trim();
    const note = String(form.get("note") || "").trim();
    if (!assetId || !date || !type || !Number.isFinite(amount) || amount <= 0) {
      setInvestMsg("Preencha ativo, data, tipo e valor do provento.");
      return;
    }
    await withPendingAction("createInvestIncome", async () => {
      try {
      await createInvestIncome({
        asset_id: assetId,
        date,
        type,
        amount,
        credit_account_id: creditAccountIdRaw ? Number(creditAccountIdRaw) : null,
        note: note || null,
      });
      formEl.reset();
      setIncomeAssetClassFilter("");
      setIncomeAssetId("");
      setInvestMsg("Provento salvo.");
      showGlobalSuccess("Provento salvo.");
      await reloadInvestData();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteInvestIncome(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir proventos.");
      return;
    }
    await withPendingAction(`deleteInvestIncome-${id}`, async () => {
      try {
      await deleteInvestIncome(Number(id));
      setInvestMsg("Provento excluído.");
      showGlobalSuccess("Provento excluído.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onUpsertInvestPrice(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para registrar cotações.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const assetId = Number(form.get("asset_id"));
    const date = String(form.get("date") || "");
    const price = parseLocaleNumber(form.get("price") || "0");
    const source = String(form.get("source") || "manual").trim();
    if (!assetId || !date || !Number.isFinite(price) || price <= 0) {
      setInvestMsg("Preencha ativo, data e preço válido.");
      return;
    }
    await withPendingAction("upsertInvestPrice", async () => {
      try {
      await upsertInvestPrice({
        asset_id: assetId,
        date,
        price,
        source: source || "manual",
      });
      formEl.reset();
      setInvestMsg("Cotação salva.");
      showGlobalSuccess("Cotação salva.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  async function onUpdateInvestManualQuote(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para atualizar ativos.");
      return;
    }
    const assetId = Number(manualQuoteAssetId || 0);
    const value = parseLocaleNumber(manualQuoteValue || "");
    const refDate = String(manualQuoteDate || "").trim();
    if (!assetId) {
      setInvestMsg("Selecione um ativo para atualização manual.");
      return;
    }
    if (!Number.isFinite(value)) {
      setInvestMsg(
        manualQuoteMode === "rentability"
          ? "Informe uma rentabilidade válida."
          : "Informe um valor atual válido."
      );
      return;
    }
    if (manualQuoteMode === "current_value" && value <= 0) {
      setInvestMsg("O valor atual deve ser maior que zero.");
      return;
    }
    if (!selectedManualQuoteIsManual && manualQuoteMode !== "current_value") {
      setInvestMsg("Ativos com indexador automático aceitam apenas ajuste por valor atual.");
      return;
    }
    if (manualQuoteMode === "rentability" && value < -100) {
      setInvestMsg("A rentabilidade manual não pode ser menor que -100%.");
      return;
    }
    await withPendingAction("updateInvestManualQuote", async () => {
      try {
      await updateInvestManualAssetValue(assetId, {
        mode: manualQuoteMode,
        value,
        ref_date: refDate || null,
      });
      setManualQuoteValue("");
      setManualQuoteDate("");
      setInvestMsg("Atualização manual salva.");
      showGlobalSuccess("Atualização manual salva.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
    });
  }

  function onChangeFairValueDraft(assetId, field, value) {
    const key = String(assetId || "");
    if (!key) return;
    setFairValueDrafts((prev) => {
      const base = prev[key] || { fair_price: "", safety_margin_pct: "20,00", user_objective: "" };
      return {
        ...prev,
        [key]: {
          ...base,
          [field]:
            field === "fair_price"
              ? formatCurrencyInputValue(value)
              : field === "safety_margin_pct"
                ? sanitizeDecimalInputValue(value, { maxDecimals: 2, maxIntegerDigits: 3 })
                : String(value || "").trim().toLowerCase(),
        },
      };
    });
  }

  async function onSaveAssetFairValue(asset) {
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para salvar preço justo.");
      return false;
    }
    const key = String(asset?.id || "");
    const draft = fairValueDrafts[key] || {};
    const fairPrice = parseLocaleNumber(draft.fair_price || "");
    const safetyMarginPct = parseLocaleNumber(draft.safety_margin_pct || "");
    const userObjective = String(draft.user_objective || "").trim().toLowerCase() || null;
    if (!Number.isFinite(fairPrice) || fairPrice <= 0) {
      setInvestMsg("Informe um preço justo válido.");
      return false;
    }
    if (!Number.isFinite(safetyMarginPct) || safetyMarginPct < 0 || safetyMarginPct > 100) {
      setInvestMsg("Informe uma margem de segurança entre 0% e 100%.");
      return false;
    }
    let saved = false;
    await withPendingAction(`fairValue-${key}`, async () => {
      try {
        await updateInvestAssetFairValue(Number(asset.id), {
          fair_price: fairPrice,
          safety_margin_pct: safetyMarginPct,
          user_objective: userObjective,
        });
        setInvestMsg(`Preço justo de ${asset.symbol} salvo.`);
        showGlobalSuccess(`Preço justo de ${asset.symbol} salvo.`);
        await reloadInvestData();
        setFairValueInlineEditId("");
        saved = true;
      } catch (err) {
        setInvestMsg(String(err.message || err));
      }
    });
    return saved;
  }

  function triggerAssetValuationReportSelect(assetId) {
    const key = String(assetId || "");
    if (!key || !canEditInvestimentos || isPendingAction(`fairValueReportUpload-${key}`)) return;
    valuationReportInputRefs.current[key]?.click?.();
  }

  function onEditFairValueAsset(asset) {
    if (!asset?.id) return;
    const key = String(asset.id);
    setFairValueDrafts((prev) => ({
      ...prev,
      [key]: {
        fair_price: asset?.fairPrice == null ? "" : formatLocalizedNumber(asset.fairPrice, 2),
        safety_margin_pct: asset?.safetyMarginPct == null ? "20,00" : formatLocalizedNumber(asset.safetyMarginPct, 2),
        user_objective: String(asset?.userObjective || "").trim().toLowerCase(),
      },
    }));
    setFairValueInlineEditId(key);
  }

  async function onToggleInlineFairValueEdit(asset) {
    const key = String(asset?.id || "");
    if (!key) return;
    if (fairValueInlineEditId === key) {
      await onSaveAssetFairValue(asset);
      return;
    }
    onEditFairValueAsset(asset);
  }

  async function onDeleteAssetFairValue(asset) {
    const key = String(asset?.id || "");
    if (!key) return;
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para excluir preço justo.");
      return;
    }
    const confirmed = window.confirm(`Excluir a configuração de preço justo de ${asset.symbol}?`);
    if (!confirmed) return;
    await withPendingAction(`fairValueDelete-${key}`, async () => {
      try {
        await updateInvestAssetFairValue(Number(asset.id), {
          fair_price: null,
          safety_margin_pct: null,
          user_objective: asset?.userObjective || null,
        });
        setFairValueInlineEditId("");
        setInvestMsg(`Preço justo de ${asset.symbol} excluído.`);
        showGlobalSuccess(`Preço justo de ${asset.symbol} excluído.`);
        await reloadInvestData();
      } catch (err) {
        setInvestMsg(String(err.message || err));
      }
    });
  }

  async function onUploadAssetValuationReport(asset, file) {
    const key = String(asset?.id || "");
    if (!key || !file) return;
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para anexar PDF de avaliação.");
      return;
    }
    const fileName = String(file.name || "").trim();
    if (!fileName.toLowerCase().endsWith(".pdf")) {
      setInvestMsg("Envie um arquivo PDF válido.");
      return;
    }
    await withPendingAction(`fairValueReportUpload-${key}`, async () => {
      try {
        await uploadInvestAssetValuationReport(Number(asset.id), file);
        setInvestMsg(`PDF de avaliação de ${asset.symbol} salvo.`);
        showGlobalSuccess(`PDF de avaliação de ${asset.symbol} salvo.`);
        await reloadInvestData();
      } catch (err) {
        setInvestMsg(String(err.message || err));
      }
    });
  }

  async function onDownloadAssetValuationReport(asset) {
    const key = String(asset?.id || "");
    if (!key) return;
    await withPendingAction(`fairValueReportDownload-${key}`, async () => {
      try {
        const { blob, fileName } = await downloadInvestAssetValuationReport(Number(asset.id));
        const objectUrl = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = fileName || `avaliacao-${asset.symbol || asset.id}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
      } catch (err) {
        setInvestMsg(String(err.message || err));
      }
    });
  }

  async function onUpdateAllInvestPrices() {
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para atualizar cotações.");
      return;
    }
    if (!quoteGroup) {
      setInvestMsg("Selecione uma classe para atualização.");
      return;
    }
    await runInvestPriceUpdate({
      includeGroups: [quoteGroup],
      silentSuccess: false,
      reloadAfter: true,
    });
  }

  async function runInvestPriceUpdate({ includeGroups = [], silentSuccess = true, reloadAfter = true } = {}) {
    setInvestMsg("");
    setInvestPriceUpdateReport([]);
    setInvestPriceUpdateRunning(true);
    const timeout = Number(sanitizeIntegerInputValue(quoteTimeout || "25", 3));
    const workers = Number(sanitizeIntegerInputValue(quoteWorkers || "4", 2));
    try {
      const out = await updateAllInvestPrices({
        timeout_s: Number.isFinite(timeout) ? timeout : 25,
        max_workers: Number.isFinite(workers) ? workers : 4,
        include_groups: Array.isArray(includeGroups) ? includeGroups : [],
      });
      const report = Array.isArray(out.report) ? out.report : [];
      const failed = report.filter((row) => !row?.ok).length;
      setInvestPriceUpdateReport(report);
      setInvestMsg(`Cotações salvas: ${out.saved}/${out.total}${failed ? ` | Falhas: ${failed}` : ""}`);
      if (!silentSuccess) {
        showGlobalSuccess("Cotações atualizadas.");
      }
      if (reloadAfter) {
        await reloadInvestData();
      }
      return out;
    } catch (err) {
      setInvestMsg(String(err.message || err));
      throw err;
    } finally {
      setInvestPriceUpdateRunning(false);
    }
  }

  async function onCreateAccount(e) {
    e.preventDefault();
    setManageMsg("");
    if (!canAddContas) {
      setManageMsg("Sem permissão para cadastrar contas.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const type = String(form.get("type") || "").trim();
    const currency = String(form.get("currency") || "").toUpperCase().trim();
    const showOnDashboard = String(form.get("show_on_dashboard") || "").toLowerCase() === "on";
    if (!name || !type || !currency) {
      setManageMsg("Preencha nome, tipo e moeda da conta.");
      return;
    }
    await withPendingAction("createAccount", async () => {
      try {
      await createAccount({ name, type, currency, show_on_dashboard: showOnDashboard });
      formEl.reset();
      setManageMsg("Conta salva.");
      showGlobalSuccess("Conta salva.");
      await reloadAllData();
      await reloadCardsData();
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onUpdateAccount() {
    if (!canEditContas) {
      setManageMsg("Sem permissão para editar contas.");
      return;
    }
    if (!accEditId || !accEditName.trim()) {
      setManageMsg("Selecione uma conta e informe nome.");
      return;
    }
    await withPendingAction("updateAccount", async () => {
      try {
      await updateAccount(Number(accEditId), {
        name: accEditName.trim(),
        type: accEditType,
        currency: (accEditCurrency || "BRL").toUpperCase(),
        show_on_dashboard: Boolean(accEditShowOnDashboard),
      });
      setManageMsg("Conta atualizada.");
      showGlobalSuccess("Conta atualizada.");
      await reloadAllData();
      await reloadCardsData();
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteAccount() {
    if (!canDeleteContas) {
      setManageMsg("Sem permissão para excluir contas.");
      return;
    }
    if (!accEditId) return;
    await withPendingAction("deleteAccount", async () => {
      try {
      await deleteAccount(Number(accEditId));
      setManageMsg("Conta excluída.");
      showGlobalSuccess("Conta excluída.");
      await reloadAllData();
      await reloadCardsData();
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onCreateCategory(e) {
    e.preventDefault();
    setManageMsg("");
    if (!canAddContas) {
      setManageMsg("Sem permissão para cadastrar categorias.");
      return;
    }
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const kind = String(form.get("kind") || "").trim();
    if (!name || !kind) {
      setManageMsg("Preencha nome e tipo da categoria.");
      return;
    }
    await withPendingAction("createCategory", async () => {
      try {
      await createCategory({ name, kind });
      formEl.reset();
      setManageMsg("Categoria salva.");
      showGlobalSuccess("Categoria salva.");
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onUpdateCategory() {
    if (!canEditContas) {
      setManageMsg("Sem permissão para editar categorias.");
      return;
    }
    if (!catEditId || !catEditName.trim()) {
      setManageMsg("Selecione uma categoria e informe nome.");
      return;
    }
    await withPendingAction("updateCategory", async () => {
      try {
      await updateCategory(Number(catEditId), { name: catEditName.trim(), kind: catEditKind });
      setManageMsg("Categoria atualizada.");
      showGlobalSuccess("Categoria atualizada.");
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteCategory() {
    if (!canDeleteContas) {
      setManageMsg("Sem permissão para excluir categorias.");
      return;
    }
    if (!catEditId) return;
    await withPendingAction("deleteCategory", async () => {
      try {
      await deleteCategory(Number(catEditId));
      setManageMsg("Categoria excluída.");
      showGlobalSuccess("Categoria excluída.");
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
    });
  }

  async function onCreateCard(e) {
    e.preventDefault();
    setCardMsg("");
    if (!canAddContas) {
      setCardMsg("Sem permissão para cadastrar cartões.");
      return;
    }
    const name = String(cardCreateName || "").trim();
    const brand = String(cardCreateBrand || "").trim();
    const model = String(cardCreateModel || "").trim();
    const type = "Credito";
    const accId = Number(cardCreateAccountId);
    const due = Number(String(cardCreateDueDay || "0"));
    const close = Number(String(cardCreateCloseDay || "0"));
    if (
      !name ||
      !brand ||
      !model ||
        !Number.isFinite(accId) ||
        accId <= 0 ||
      (!Number.isFinite(due) || due < 1 || due > 31 || !Number.isFinite(close) || close < 1 || close > 31 || close >= due)
    ) {
      if (!Number.isFinite(accId) || accId <= 0) {
        setCardMsg("Selecione a conta banco vinculada ao cartão.");
        return;
      }
      setCardMsg("Preencha nome, conta banco vinculada, fechamento e vencimento.");
      return;
    }
    await withPendingAction("createCard", async () => {
      try {
      await createCard({
        name,
        brand,
        model,
        card_type: type,
        card_account_id: accId,
        source_account_id: accId,
        due_day: due,
        close_day: close,
      });
      setCardMsg("Cartão cadastrado.");
      setCardCreateName("");
      setCardCreateBrand("");
      setCardCreateModel("");
      setCardCreateType("Credito");
      setCardCreateAccountId("");
      setCardCreateDueDay("");
      setCardCreateCloseDay("");
      showGlobalSuccess("Cartão salvo.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
    });
  }

  async function onUpdateCard() {
    setCardMsg("");
    if (!canEditContas) {
      setCardMsg("Sem permissão para editar cartões.");
      return;
    }
    const id = Number(cardEditId);
    const name = String(cardName || "").trim();
    const brand = String(cardBrand || "").trim();
    const model = String(cardModel || "").trim();
    const type = "Credito";
    const accId = Number(cardAccountId);
    const due = Number(String(cardDueDay || "0"));
    const close = Number(String(cardCloseDay || "0"));
    if (
      !Number.isFinite(id) ||
      id <= 0 ||
      !name ||
      !brand ||
      !model ||
      !Number.isFinite(accId) ||
      accId <= 0 ||
      (!Number.isFinite(due) || due < 1 || due > 31 || !Number.isFinite(close) || close < 1 || close > 31 || close >= due)
    ) {
      if (!Number.isFinite(accId) || accId <= 0) {
        setCardMsg("Selecione a conta banco vinculada ao cartão.");
        return;
      }
      setCardMsg("Selecione e preencha os dados do cartão.");
      return;
    }
    await withPendingAction("updateCard", async () => {
      try {
      await updateCard(id, {
        name,
        brand,
        model,
        card_type: type,
        card_account_id: accId,
        source_account_id: accId,
        due_day: due,
        close_day: close,
      });
      setCardMsg("Cartão atualizado.");
      showGlobalSuccess("Cartão atualizado.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
    });
  }

  async function onDeleteCard() {
    setCardMsg("");
    if (!canDeleteContas) {
      setCardMsg("Sem permissão para excluir cartões.");
      return;
    }
    const id = Number(cardEditId);
    if (!Number.isFinite(id)) return;
    await withPendingAction("deleteCard", async () => {
      try {
      await deleteCard(id);
      setCardMsg("Cartão excluído.");
      showGlobalSuccess("Cartão excluído.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
    });
  }

  function onSelectCardEdit(id) {
    setCardEditId(id);
    const cur = (cards || []).find((c) => String(c.id) === String(id));
    if (!cur) {
      setCardName("");
      setCardBrand("");
      setCardModel("");
      setCardType("Credito");
      setCardAccountId("");
      setCardSourceAccountId("");
      setCardDueDay("");
      setCardCloseDay("");
      return;
    }
    setCardName(String(cur.name || ""));
    setCardBrand(String(cur.brand || "Visa"));
    setCardModel(String(cur.model || "Black"));
    setCardType(String(cur.card_type || "Credito"));
    setCardAccountId(String(cur.card_account_id || ""));
    setCardSourceAccountId(String(cur.source_account_id || ""));
    setCardDueDay(String(cur.due_day || 10));
    setCardCloseDay(String(cur.close_day || Math.max(1, Number(cur.due_day || 10) - 5)));
  }

  async function onPayInvoice(invoice, sourceAccountId = null, paymentDateValue = "") {
    setCardMsg("");
    if (!canAddContas) {
      setCardMsg("Sem permissão para pagar faturas.");
      return;
    }
    const invoiceId = Number(invoice?.id);
    const paymentDate = String(paymentDateValue || "").trim() || new Date().toISOString().slice(0, 10);
    await withPendingAction(`payInvoice-${invoiceId}`, async () => {
      try {
      await payCardInvoice(invoiceId, {
        payment_date: paymentDate,
        source_account_id: sourceAccountId ? Number(sourceAccountId) : null,
      });
      setCardMsg("Fatura paga.");
      showGlobalSuccess("Fatura paga.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
      await reloadInvestData();
      await reloadTransactions();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
    });
  }

  function openPayInvoiceModal(invoice) {
    if (!invoice) return;
    const defaultBank =
      bankAccountsOnly.find((a) => String(a.name || "") === String(invoice.source_account || "")) || bankAccountsOnly[0];
    setPayInvoiceTarget(invoice);
    setPayAccountId(defaultBank ? String(defaultBank.id) : "");
    setPayDate(new Date().toISOString().slice(0, 10));
    setPayModalOpen(true);
  }

  async function confirmPayInvoiceModal() {
    if (!payInvoiceTarget) return;
    if (!payAccountId) {
      setCardMsg("Selecione a conta banco para pagar a fatura.");
      return;
    }
    if (!payDate) {
      setCardMsg("Selecione a data real do pagamento.");
      return;
    }
    await onPayInvoice(payInvoiceTarget, Number(payAccountId), payDate);
    setPayModalOpen(false);
    setPayInvoiceTarget(null);
    setPayAccountId("");
    setPayDate("");
  }

  function onLogout() {
    clearToken();
    setUser(null);
    setLoginSyncNotice(null);
    setAccounts([]);
    setCategories([]);
    setTransactions([]);
    setCards([]);
    setCardInvoices([]);
    setKpis(null);
    setWorkspaces([]);
    setWorkspaceMembers([]);
    setWorkspacePermDrafts({});
    setAdminWorkspaces([]);
    setPage("Dashboard");
  }

  async function onInstallPwa() {
    if (!installPromptEvent) return;
    try {
      await installPromptEvent.prompt();
      await installPromptEvent.userChoice;
    } finally {
      setInstallPromptEvent(null);
    }
  }

  async function onApplyDashboardFilters(e) {
    e.preventDefault();
    await reloadDashboard({
      date_from: dashDateFrom,
      date_to: dashDateTo,
      account: dashAccount,
      view: dashView,
    });
  }

  function openCommitmentsFromDashboard(status = "") {
    if (!canViewLancamentos) return;
    setPage("Lançamentos");
    setTxView("futuro");
    setTxRecentDateFrom(dashDateFrom);
    setTxRecentDateTo(dashDateTo);
    setTxRecentCategoryFilterId("");
    setTxRecentStatusFilter(status);
  }

  function openInvestmentsClassFromDashboard(assetClass = "") {
    if (!canViewInvestimentos) return;
    setPage("Investimentos");
    setInvestTab("Resumo");
    setInvestSummaryClassFilter(String(assetClass || "").trim());
  }

  function renderPasswordInput({
    name,
    placeholder,
    value,
    onChange,
    visible,
    onToggle,
    required = false,
    disabled = false,
  }) {
    return (
      <label className="password-field">
        <input
          name={name}
          type={visible ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
        />
        <button type="button" className="password-toggle" onClick={onToggle} disabled={disabled}>
          {visible ? "Ocultar" : "Mostrar"}
        </button>
      </label>
    );
  }

  async function onPreviewTransactionsCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para pré-visualizar importações.");
      return;
    }
    if (!txCsvFile) {
      setImportMsg("Selecione um CSV de transações.");
      return;
    }
    setImportMsg("");
    await withPendingAction("previewTransactionsCsv", async () => {
      try {
      const out = await importTransactionsCsv(txCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
      showGlobalSuccess("Prévia de lançamentos pronta.");
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  async function onImportTransactionsCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para importar transações.");
      return;
    }
    if (!txCsvFile) {
      setImportMsg("Selecione um CSV de transações.");
      return;
    }
    setImportMsg("");
    await withPendingAction("importTransactionsCsv", async () => {
      try {
      const out = await importTransactionsCsv(txCsvFile, false);
      setImportPreview([]);
      setImportMsg(`Importação concluída: ${out.inserted}/${out.rows} lançamentos.`);
      showGlobalSuccess("Lançamentos importados.");
      await reloadAllData();
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  async function onPreviewAssetsCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para pré-visualizar importações.");
      return;
    }
    if (!assetCsvFile) {
      setImportMsg("Selecione um CSV de ativos.");
      return;
    }
    setImportMsg("");
    await withPendingAction("previewAssetsCsv", async () => {
      try {
      const out = await importAssetsCsv(assetCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
      showGlobalSuccess("Prévia de ativos pronta.");
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  async function onImportAssetsCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para importar ativos.");
      return;
    }
    if (!assetCsvFile) {
      setImportMsg("Selecione um CSV de ativos.");
      return;
    }
    setImportMsg("");
    await withPendingAction("importAssetsCsv", async () => {
      try {
      const out = await importAssetsCsv(assetCsvFile, false);
      setImportPreview([]);
      const errInfo = out.errors && out.errors.length ? ` Erros: ${out.errors.length}.` : "";
      setImportMsg(`Importação de ativos: inseridos ${out.inserted}, ignorados ${out.skipped}.${errInfo}`);
      showGlobalSuccess("Ativos importados.");
      await reloadInvestData();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  async function onPreviewTradesCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para pré-visualizar importações.");
      return;
    }
    if (!tradeCsvFile) {
      setImportMsg("Selecione um CSV de operações.");
      return;
    }
    setImportMsg("");
    await withPendingAction("previewTradesCsv", async () => {
      try {
      const out = await importTradesCsv(tradeCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
      showGlobalSuccess("Prévia de operações pronta.");
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  async function onImportTradesCsv() {
    if (!canAddRelatorios) {
      setImportMsg("Sem permissão para importar operações.");
      return;
    }
    if (!tradeCsvFile) {
      setImportMsg("Selecione um CSV de operações.");
      return;
    }
    setImportMsg("");
    await withPendingAction("importTradesCsv", async () => {
      try {
      const out = await importTradesCsv(tradeCsvFile, false);
      setImportPreview([]);
      const errInfo = out.errors && out.errors.length ? ` Erros: ${out.errors.length}.` : "";
      setImportMsg(`Importação de operações: inseridas ${out.inserted}, ignoradas ${out.skipped}.${errInfo}`);
      showGlobalSuccess("Operações importadas.");
      await reloadInvestData();
      await reloadTransactions();
      await reloadDashboard();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
    });
  }

  if (loading) return <div className="center">Carregando...</div>;

  if (!user) {
    return (
      <div className="auth-wrap">
        {authMode === "reset" ? (
          <form className="auth-card" onSubmit={onResetPassword}>
            <h1>Redefinir senha</h1>
            <p>Informe sua nova senha para concluir a recuperação.</p>
            {renderPasswordInput({
              name: "reset_new_password",
              placeholder: "Nova senha",
              value: resetNewPassword,
              onChange: (e) => setResetNewPassword(e.target.value),
              visible: showResetNewPassword,
              onToggle: () => setShowResetNewPassword((v) => !v),
              required: true,
            })}
            {renderPasswordInput({
              name: "reset_confirm_password",
              placeholder: "Confirmar nova senha",
              value: resetConfirmPassword,
              onChange: (e) => setResetConfirmPassword(e.target.value),
              visible: showResetConfirmPassword,
              onToggle: () => setShowResetConfirmPassword((v) => !v),
              required: true,
            })}
            <button type="submit">Salvar nova senha</button>
            <button
              type="button"
              className="auth-secondary-btn"
              onClick={() => {
                setAuthMode("login");
                setAuthResetToken("");
                setAuthError("");
                clearPasswordResetLocation();
              }}
            >
              Voltar ao login
            </button>
            {authInfo ? <div className="status-msg">{authInfo}</div> : null}
            {authError ? <div className="error">{authError}</div> : null}
          </form>
        ) : authMode === "forgot" ? (
          <form className="auth-card" onSubmit={onForgotPassword}>
            <h1>Recuperar acesso</h1>
            <p>Informe seu e-mail para receber o link de redefinição.</p>
            <input
              name="forgot_email"
              type="email"
              placeholder="E-mail"
              value={forgotEmail}
              onChange={(e) => setForgotEmail(e.target.value)}
              required
            />
            <button type="submit">Enviar link</button>
            <button
              type="button"
              className="auth-secondary-btn"
              onClick={() => {
                setAuthMode("login");
                setAuthError("");
                setAuthInfo("");
              }}
            >
              Voltar ao login
            </button>
            {authInfo ? <div className="status-msg">{authInfo}</div> : null}
            {authError ? <div className="error">{authError}</div> : null}
          </form>
        ) : (
          <form className="auth-card" onSubmit={onLogin}>
            <h1>Controle Financeiro</h1>
            <p>Login via FastAPI</p>
            <input name="email" type="email" placeholder="E-mail" required />
            <label className="password-field">
              <input name="password" type={showLoginPassword ? "text" : "password"} placeholder="Senha" required />
              <button type="button" className="password-toggle" onClick={() => setShowLoginPassword((v) => !v)}>
                {showLoginPassword ? "Ocultar" : "Mostrar"}
              </button>
            </label>
            <button type="submit">Entrar</button>
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => {
                setAuthMode("forgot");
                setAuthError("");
                setAuthInfo("");
              }}
            >
              Esqueci minha senha
            </button>
            {authInfo ? <div className="status-msg">{authInfo}</div> : null}
            {authError ? <div className="error">{authError}</div> : null}
          </form>
        )}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src={brandLogo} alt="Domu logo" />
          <span className="brand-name">DOMUS</span>
        </div>
        <nav>
          {visiblePages.map((p) => (
            <button
              key={p}
              className={`nav-item ${p === page ? "active" : ""}`}
              onClick={() => setPage(p)}
            >
              <img src={PAGE_ICONS[p] || icUsuario} alt="" className="nav-item-icon" />
              <span className="nav-item-label">{p}</span>
            </button>
          ))}
        </nav>
        <div className="user-block">
          <div className="user-menu-wrap" ref={userMenuRef}>
            <button className="user-trigger" onClick={() => setUserMenuOpen((v) => !v)}>
              <img src={getUserAvatarSrc(user)} alt="" className="user-avatar-icon" />
              <span className="user-trigger-name">{user.display_name || user.email}</span>
            </button>
            {userMenuOpen ? (
              <div className="user-popover">
                <button
                  className="user-popover-item"
                  onClick={() => {
                    setUserMenuOpen(false);
                    setProfileModalOpen(true);
                  }}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" strokeWidth="2" />
                    <path d="M4 20c1.6-3.7 4.1-5 8-5s6.4 1.3 8 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  Perfil
                </button>
                {canViewGerenciador ? (
                  <button
                    className="user-popover-item"
                    onClick={() => {
                      setUserMenuOpen(false);
                      setManagerTab("Usuários e workspaces");
                      setPage("Gerenciador");
                    }}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 6h16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      <path d="M4 12h16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      <path d="M4 18h16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Workspace
                  </button>
                ) : null}
                {!pwaInstalled && installPromptEvent ? (
                  <button
                    className="user-popover-item install"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onInstallPwa();
                    }}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M12 4v10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      <path d="M8 10l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M5 18h14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Instalar app
                  </button>
                ) : null}
                <button
                  className="user-popover-item danger"
                  onClick={() => {
                    setUserMenuOpen(false);
                    onLogout();
                  }}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M10 17l5-5-5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M15 12H4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    <path d="M20 4v16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  Sair
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </aside>

      <main className={`main ${page === "Dashboard" || page === "Gerenciador" || page === "Contas" || page === "Lançamentos" || page === "Investimentos" || page === "Importar CSV" ? "main-dashboard" : ""}`}>
        <header className="page-header">
          <h1>{page}</h1>
          <p>{subtitle}</p>
          <div className="workspace-switch-row">
            <select
              className="workspace-select"
              value={currentWorkspaceId}
              onChange={onSwitchWorkspace}
              disabled={!workspaceOptions.length || Boolean(workspaceSwitchingId)}
            >
              {!currentWorkspaceId ? <option value="">Selecione um workspace</option> : null}
              {workspaceOptions.map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name} {ws.status === "blocked" ? "(bloqueado)" : ""}
                </option>
              ))}
            </select>
            {workspaceSwitchingId ? <span className="workspace-msg">Trocando workspace...</span> : null}
            {!workspaceSwitchingId && workspaceMsg ? <span className="workspace-msg">{workspaceMsg}</span> : null}
          </div>
        </header>

        {loginSyncNotice?.message ? (
          <section className={`status-banner ${loginSyncNotice.level === "warning" ? "warning" : "success"}`}>
            <p className="status-msg">{loginSyncNotice.message}</p>
          </section>
        ) : null}

        {globalActionNotice?.message ? (
          <section className={`status-banner status-banner-floating ${globalActionNotice.level === "warning" ? "warning" : "success"}`}>
            <p className="status-msg">{globalActionNotice.message}</p>
          </section>
        ) : null}

        {!visiblePages.length ? (
          <section className="card">
            <p>Seu usuário não possui módulos habilitados neste workspace.</p>
          </section>
        ) : null}

        {page === "Dashboard" && kpis ? (
          <>
            <section className="card dash-filter-card">
              <h3>Filtros</h3>
              <form className="tx-form dash-filter-form" onSubmit={onApplyDashboardFilters}>
                <input
                  type="date"
                  value={dashDateFrom}
                  onChange={(e) => setDashDateFrom(e.target.value)}
                />
                <input
                  type="date"
                  value={dashDateTo}
                  onChange={(e) => setDashDateTo(e.target.value)}
                />
                <select value={dashAccount} onChange={(e) => setDashAccount(e.target.value)}>
                  <option value="">(todas)</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
                <select value={dashView} onChange={(e) => setDashView(e.target.value)}>
                  <option value="caixa">Visão Caixa</option>
                  <option value="competencia">Visão Competência</option>
                  <option value="futuro">Visão Compromissos</option>
                </select>
                <button type="submit">Aplicar filtros</button>
              </form>
              {dashMsg ? <p>{dashMsg}</p> : null}
            </section>

            <section className="dash-kpis">
              <article className="card dash-kpi-card dash-kpi-expense">
                <h3 className="dash-kpi-title">
                  <img src={icDespesa} alt="" className="dash-kpi-icon" />
                  <span>Despesas</span>
                </h3>
                <strong>{brl.format(Number(currentKpi.despesas || 0))}</strong>
              </article>
              <article className="card dash-kpi-card dash-kpi-income">
                <h3 className="dash-kpi-title">
                  <img src={icReceita} alt="" className="dash-kpi-icon" />
                  <span>Receitas</span>
                </h3>
                <strong>{brl.format(Number(currentKpi.receitas || 0))}</strong>
              </article>
              <article className="card dash-kpi-card">
                <h3 className="dash-kpi-title">
                  <img src={icSaldo} alt="" className="dash-kpi-icon" />
                  <span>Resultado</span>
                </h3>
                <strong>{brl.format(Number(currentKpi.saldo || 0))}</strong>
              </article>
            </section>

            <section className="dash-grid">
              <article className="card dash-hero-card">
                <div className="dash-hero-head">
                  <h3>Patrimônio mensal</h3>
                  <span className={`dash-delta ${trendDirection}`}>
                    {trendDelta >= 0 ? "+" : "-"}
                    {Math.abs(trendPct).toFixed(1)}% vs mês anterior
                  </span>
                </div>
                <strong className="dash-hero-value">{brl.format(trendEnd)}</strong>
                <p className="dash-hero-label">{trendMonthLabel ? `Referência: ${trendMonthLabel}` : "Sem dados no período"}</p>
                <div className="dash-hero-summary">
                  <p className={`dash-hero-sub ${trendDirection}`}>
                    {trendDelta >= 0 ? "▲" : "▼"} {brl.format(Math.abs(trendDelta))} vs mês anterior
                  </p>
                  {previousMonthEntry ? (
                    <p className="dash-hero-compare">
                      Mês anterior: <strong>{brl.format(previousMonthValue)}</strong>
                    </p>
                  ) : (
                    <p className="dash-hero-compare">Sem base comparativa anterior.</p>
                  )}
                </div>
              </article>

              <article className="card dash-list-card dash-saldo-card">
                <h3>Saldo de contas</h3>
                <ul className="dash-list">
                  {accountsTop.map((r) => (
                    <li key={r.account}>
                      <span className="dash-row-label">
                        {getBankLogo(r.account) ? (
                          <img src={getBankLogo(r.account)} alt="" className="dash-row-icon" />
                        ) : null}
                        {r.account}
                        {r.fixedManual ? <em className="dash-fixed-badge">fixa</em> : null}
                      </span>
                      <strong>{brl.format(normalizeMoneyValue(r.saldo))}</strong>
                    </li>
                  ))}
                </ul>
                <div className="dash-list-total">
                  <span>Total</span>
                  <strong>{brl.format(accountsTotal)}</strong>
                </div>
              </article>

              <article className="card dash-cards-card">
                {creditCards.length ? (
                  <div className={`dash-wallet-stack ${creditCards.length === 1 ? "single" : ""}`}>
                    {walletVisibleCards.map((card) => (
                      <article
                        className={`wallet-card wallet-card-${card.walletPos}`}
                        key={card.id}
                        title={`${card.name} (${card.model || "Black"})`}
                        aria-hidden={card.walletPos !== "active"}
                      >
                        <img
                          src={getCardBackground(card.model || "Black")}
                          alt=""
                          className="wallet-bg"
                        />
                        <div className="wallet-overlay" />
                        <div className="wallet-content">
                          <div className="wallet-name">{card.name}</div>
                          <div className="wallet-brand-line">
                            <img
                              src={getCardLogo(card.brand || "Visa")}
                              alt=""
                              className="wallet-brand-icon"
                            />
                          </div>
                        </div>
                      </article>
                    ))}
                    {creditCards.length > 1 ? (
                      <div className="wallet-controls">
                        <button
                          type="button"
                          className="wallet-nav-btn"
                          onClick={() =>
                            setWalletCardIndex((prev) => (prev - 1 + creditCards.length) % creditCards.length)
                          }
                          aria-label="Cartão anterior"
                        >
                          ‹
                        </button>
                        <span className="wallet-page-indicator">
                          {walletCardIndex + 1}/{creditCards.length}
                        </span>
                        <button
                          type="button"
                          className="wallet-nav-btn"
                          onClick={() => setWalletCardIndex((prev) => (prev + 1) % creditCards.length)}
                          aria-label="Próximo cartão"
                        >
                          ›
                        </button>
                      </div>
                    ) : null}
                    {creditCards.length > 1 ? (
                      <div className="wallet-dots" aria-hidden="true">
                        {creditCards.map((card, idx) => (
                          <span key={card.id} className={`wallet-dot ${idx === walletCardIndex ? "active" : ""}`} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="dash-empty">Sem cartões de crédito</div>
                )}
                <div className="dash-cards-meta">
                  <h3>Cartões e faturas</h3>
                  <p className="dash-small">
                    Vencimento: {activeCardCurrentInvoice?.due_date || "-"} | Cartões crédito: {creditCards.length}
                  </p>
                  <strong className="dash-hero-value">{brl.format(activeCardCurrentInvoiceAmount)}</strong>
                  {activeCardCurrentInvoice ? (
                    <button type="button" className="mini-tab active" onClick={() => openPayInvoiceModal(activeCardCurrentInvoice)}>
                      Pagar fatura
                    </button>
                  ) : null}
                </div>
              </article>

              <article className="card dash-invest-card">
                <h3>Resumo de investimentos</h3>
                <p className="dash-invest-total">
                  Total investido: <strong>{brl.format(Number(investmentTotal || 0))}</strong>
                </p>
                <div className="dash-invest-layout">
                  <ul className="dash-legend">
                    {investmentRadialData.map((row) => (
                      <li key={row.name}>
                        <button
                          type="button"
                          className={`dash-legend-link ${dashInvestFocusedClass === row.name ? "active" : ""}`}
                          onClick={() =>
                            setDashInvestFocusClass((current) => (current === row.name ? "" : row.name))
                          }
                        >
                          <span className="dot" style={{ background: row.fill, opacity: row.opacity }} />
                          <span>{row.name}</span>
                          <strong>{brl.format(row.value)}</strong>
                          <em>{row.pct.toFixed(0)}%</em>
                        </button>
                      </li>
                    ))}
                  </ul>
                  <div className="dash-donut">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={investmentRadialData}
                          dataKey="value"
                          nameKey="name"
                          innerRadius="52%"
                          outerRadius="92%"
                          paddingAngle={2}
                          startAngle={90}
                          endAngle={-270}
                          shape={InvestmentPieGradient}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    {dashInvestFocusedClass ? (
                      <div className="dash-donut-center">
                        <strong>
                          {brl.format(
                            Number(investmentRadialData.find((row) => row.name === dashInvestFocusedClass)?.value || 0)
                          )}
                        </strong>
                        <span>{dashInvestFocusedClass}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              </article>

              <article className="card dash-list-card dash-expenses-card">
                <h3>Compromissos do período</h3>
                <ul className="dash-list">
                  <li>
                    <button
                      type="button"
                      className="dash-list-link"
                      onClick={() => openCommitmentsFromDashboard(TX_STATUS_FILTER_OPEN)}
                      disabled={!canViewLancamentos}
                    >
                      <span>A vencer</span>
                      <strong>{brl.format(commitmentsAging.aVencer)}</strong>
                    </button>
                  </li>
                  <li>
                    <button
                      type="button"
                      className="dash-list-link"
                      onClick={() => openCommitmentsFromDashboard("Vencido")}
                      disabled={!canViewLancamentos}
                    >
                      <span>Vencidos</span>
                      <strong>{brl.format(commitmentsAging.vencidos)}</strong>
                    </button>
                  </li>
                </ul>
                <div className="dash-list-total">
                  <span>Total</span>
                  <strong>{brl.format(commitmentsAging.aVencer + commitmentsAging.vencidos)}</strong>
                </div>
              </article>
            </section>

            <Suspense fallback={<section className="card"><p>Carregando gráficos...</p></section>}>
              <DashboardCharts monthly={dashWealthMonthly} expenses={dashExpenses} />
            </Suspense>
          </>
        ) : null}

        {page === "Contas" && canViewContas ? (
          <>
            <section className="card">
              <h3>Contas cadastradas</h3>
              <div className="tx-table-wrap">
                <table className="tx-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nome</th>
                      <th>Tipo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((a) => (
                      <tr key={a.id}>
                        <td>{a.id}</td>
                        <td>{a.name}</td>
                        <td>{a.type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="card">
              <h3>Faturas abertas</h3>
              <div className="tx-recent-filters">
                <input
                  type="date"
                  className="invoice-filter-select"
                  value={invoiceDateFrom}
                  onChange={(e) => setInvoiceDateFrom(e.target.value)}
                />
                <input
                  type="date"
                  className="invoice-filter-select"
                  value={invoiceDateTo}
                  onChange={(e) => setInvoiceDateTo(e.target.value)}
                />
                <select
                  className="invoice-filter-select"
                  value={invoiceCardFilterId}
                  onChange={(e) => setInvoiceCardFilterId(e.target.value)}
                >
                  <option value="">Todos os cartões</option>
                  {invoiceCardFilterOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.name}</option>
                  ))}
                </select>
              </div>
              <div className="tx-table-wrap">
                <table className="tx-table">
                  <thead>
                    <tr>
                      <th>Cartão</th>
                      <th>Período</th>
                      <th>Vencimento</th>
                      <th>Total</th>
                      <th>Pago</th>
                      <th>Status</th>
                      <th>Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {openInvoicesVisible.map((i) => (
                      <tr key={i.id}>
                        <td>{i.card_name}</td>
                        <td>{i.invoice_period}</td>
                        <td>{i.due_date}</td>
                        <td>{brl.format(Number(i.total_amount || 0))}</td>
                        <td>{brl.format(Number(i.paid_amount || 0))}</td>
                        <td>{i.status}</td>
                        <td>
                          {i.status === "OPEN" && canAddContas ? (
                            <button onClick={() => openPayInvoiceModal(i)}>Pagar fatura</button>
                          ) : (
                            "-"
                          )}
                        </td>
                      </tr>
                    ))}
                    {!openInvoicesVisible.length ? (
                      <tr>
                        <td colSpan={7}>Nenhuma fatura aberta para o filtro selecionado.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}

        {page === "Gerenciador" && canViewGerenciador ? (
          <>
            <section className="card tabs-card">
              <div className="mini-tabs">
                {managerTabs.map((t) => (
                  <button
                    key={t}
                    className={`mini-tab ${managerTab === t ? "active" : ""}`}
                    onClick={() => setManagerTab(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </section>

            {manageMsg ? (
              <section className="card">
                <p className="status-msg">{manageMsg}</p>
              </section>
            ) : null}

            {managerTab === "Cadastro de contas" ? (
              <>
                <section className="card">
                  <h3>Nova conta</h3>
                  {canAddContas ? (
                    <form className="tx-form" onSubmit={onCreateAccount}>
                      <input name="name" type="text" placeholder="Digite o nome da conta" required />
                      <select name="type" defaultValue="" required>
                        <option value="" disabled>Selecione o tipo da conta</option>
                        <option value="Banco">Banco</option>
                        <option value="Dinheiro">Dinheiro</option>
                        <option value="Corretora">Corretora</option>
                      </select>
                      <select name="currency" defaultValue="" required>
                        <option value="" disabled>Selecione a moeda</option>
                        <option value="BRL">BRL</option>
                        <option value="USD">USD</option>
                      </select>
                      <label className="mgr-checkline">
                        <input type="checkbox" name="show_on_dashboard" />
                        Fixar no Dashboard (saldo 0)
                      </label>
                      <button type="submit" disabled={isPendingAction("createAccount")}>
                        {isPendingAction("createAccount") ? "Salvando..." : "Salvar conta"}
                      </button>
                    </form>
                  ) : (
                    <p>Sem permissão para cadastrar contas.</p>
                  )}
                </section>

                <section className="card">
                  <h3>Gerenciar contas</h3>
                  <div className="mgr-grid">
                    <select
                      value={accEditId}
                      disabled={!canEditContas && !canDeleteContas}
                      onChange={(e) => {
                        const id = e.target.value;
                        setAccEditId(id);
                        const cur = accounts.find((a) => String(a.id) === id);
                        if (cur) {
                          setAccEditName(cur.name);
                          setAccEditType(cur.type);
                          setAccEditCurrency((cur.currency || "BRL").toUpperCase());
                          setAccEditShowOnDashboard(Boolean(cur.show_on_dashboard));
                        }
                      }}
                    >
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>{a.id} - {a.name} ({a.type}, {a.currency || "BRL"})</option>
                      ))}
                    </select>
                    <input value={accEditName} onChange={(e) => setAccEditName(e.target.value)} placeholder="Nome" disabled={!canEditContas} />
                    <select value={accEditType} onChange={(e) => setAccEditType(e.target.value)} disabled={!canEditContas}>
                      <option value="Banco">Banco</option>
                      <option value="Dinheiro">Dinheiro</option>
                      <option value="Corretora">Corretora</option>
                    </select>
                    <select value={accEditCurrency} onChange={(e) => setAccEditCurrency(e.target.value)} disabled={!canEditContas}>
                      <option value="BRL">BRL</option>
                      <option value="USD">USD</option>
                    </select>
                    <label className="mgr-checkline">
                      <input
                        type="checkbox"
                        checked={Boolean(accEditShowOnDashboard)}
                        disabled={!canEditContas}
                        onChange={(e) => setAccEditShowOnDashboard(e.target.checked)}
                      />
                      Fixar no Dashboard (saldo 0)
                    </label>
                    <button onClick={onUpdateAccount} disabled={!canEditContas || isPendingAction("updateAccount")}>
                      {isPendingAction("updateAccount") ? "Atualizando..." : "Atualizar conta"}
                    </button>
                    <button className="danger" onClick={onDeleteAccount} disabled={!canDeleteContas || isPendingAction("deleteAccount")}>
                      {isPendingAction("deleteAccount") ? "Excluindo..." : "Excluir conta"}
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {managerTab === "Cadastro de categorias" ? (
              <>
                <section className="card">
                  <h3>Nova categoria</h3>
                  {canAddContas ? (
                    <form className="tx-form" onSubmit={onCreateCategory}>
                      <input name="name" type="text" placeholder="Digite o nome da categoria" required />
                      <select name="kind" defaultValue="" required>
                        <option value="" disabled>Selecione o tipo da categoria</option>
                        <option value="Despesa">Despesa</option>
                        <option value="Receita">Receita</option>
                        <option value="Transferencia">Transferência</option>
                      </select>
                      <button type="submit" disabled={isPendingAction("createCategory")}>
                        {isPendingAction("createCategory") ? "Salvando..." : "Salvar categoria"}
                      </button>
                    </form>
                  ) : (
                    <p>Sem permissão para cadastrar categorias.</p>
                  )}
                </section>

                <section className="card">
                  <h3>Gerenciar categorias</h3>
                  <div className="mgr-grid">
                    <select
                      value={catEditId}
                      disabled={!canEditContas && !canDeleteContas}
                      onChange={(e) => {
                        const id = e.target.value;
                        setCatEditId(id);
                        const cur = categories.find((c) => String(c.id) === id);
                        if (cur) {
                          setCatEditName(cur.name);
                          setCatEditKind(cur.kind);
                        }
                      }}
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.id} - {c.name} ({c.kind})</option>
                      ))}
                    </select>
                    <input value={catEditName} onChange={(e) => setCatEditName(e.target.value)} placeholder="Nome" disabled={!canEditContas} />
                    <select value={catEditKind} onChange={(e) => setCatEditKind(e.target.value)} disabled={!canEditContas}>
                      <option value="Despesa">Despesa</option>
                      <option value="Receita">Receita</option>
                      <option value="Transferencia">Transferência</option>
                    </select>
                    <button onClick={onUpdateCategory} disabled={!canEditContas || isPendingAction("updateCategory")}>
                      {isPendingAction("updateCategory") ? "Atualizando..." : "Atualizar categoria"}
                    </button>
                    <button className="danger" onClick={onDeleteCategory} disabled={!canDeleteContas || isPendingAction("deleteCategory")}>
                      {isPendingAction("deleteCategory") ? "Excluindo..." : "Excluir categoria"}
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {managerTab === "Cadastro cartão de crédito" ? (
              <>
                <section className="card">
                  <h3>Cadastro de cartões</h3>
                  {canAddContas ? (
                    <div className="mgr-grid">
                      <input
                        type="text"
                        placeholder="Digite o nome do cartão"
                        value={cardCreateName}
                        onChange={(e) => setCardCreateName(e.target.value)}
                      />
                      <select value={cardCreateBrand} onChange={(e) => setCardCreateBrand(e.target.value)}>
                        <option value="" disabled>Selecione a bandeira</option>
                        <option value="Visa">Visa</option>
                        <option value="Master">Master</option>
                      </select>
                      <select value={cardCreateModel} onChange={(e) => setCardCreateModel(e.target.value)}>
                        <option value="" disabled>Selecione o modelo do cartão</option>
                        {CARD_MODELS.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                      <select value={cardCreateAccountId} onChange={(e) => setCardCreateAccountId(e.target.value)}>
                        <option value="" disabled>Selecione a conta banco vinculada</option>
                        {bankAccountsOnly.map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                      {!bankAccountsOnly.length ? (
                        <input type="text" value="Sem conta Banco cadastrada." disabled />
                      ) : null}
                      <input
                        type="text"
                        inputMode="numeric"
                        placeholder="Dia de fechamento (1-31)"
                        value={cardCreateCloseDay}
                        onChange={(e) => setCardCreateCloseDay(sanitizeIntegerInputValue(e.target.value, 2))}
                      />
                      <input
                        type="text"
                        inputMode="numeric"
                        placeholder="Dia do vencimento (1-31)"
                        value={cardCreateDueDay}
                        onChange={(e) => setCardCreateDueDay(sanitizeIntegerInputValue(e.target.value, 2))}
                      />
                      <small className="mgr-hint">
                        Dica: informe o fechamento no máximo 5 dias antes do vencimento da fatura.
                      </small>
                      <button type="button" onClick={onCreateCard} disabled={isPendingAction("createCard")}>
                        {isPendingAction("createCard") ? "Salvando..." : "Cadastrar cartão"}
                      </button>
                    </div>
                  ) : (
                    <p>Sem permissão para cadastrar cartões.</p>
                  )}
                </section>

                <section className="card">
                  <h3>Cartões cadastrados</h3>
                  <div className="mgr-grid">
                    <select value={cardEditId} onChange={(e) => onSelectCardEdit(e.target.value)} disabled={!canEditContas && !canDeleteContas}>
                      <option value="">Selecione um cartão</option>
                      {cards.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} - {c.brand || "Visa"} - {c.model || "Black"} - {c.card_type || "Credito"} ({c.linked_account})
                        </option>
                      ))}
                    </select>
                    <input value={cardName} onChange={(e) => setCardName(e.target.value)} placeholder="Digite o nome do cartão" disabled={!canEditContas} />
                    <select value={cardBrand} onChange={(e) => setCardBrand(e.target.value)} disabled={!canEditContas}>
                      <option value="" disabled>Selecione a bandeira</option>
                      <option value="Visa">Visa</option>
                      <option value="Master">Master</option>
                    </select>
                    <select value={cardModel} onChange={(e) => setCardModel(e.target.value)} disabled={!canEditContas}>
                      <option value="" disabled>Selecione o modelo do cartão</option>
                      {CARD_MODELS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                    <select value={cardAccountId} onChange={(e) => setCardAccountId(e.target.value)} disabled={!canEditContas}>
                      <option value="" disabled>Selecione a conta banco vinculada</option>
                      {bankAccountsOnly.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      inputMode="numeric"
                      placeholder="Dia de fechamento (1-31)"
                      value={cardCloseDay}
                      disabled={!canEditContas}
                      onChange={(e) => setCardCloseDay(sanitizeIntegerInputValue(e.target.value, 2))}
                    />
                    <input
                      type="text"
                      inputMode="numeric"
                      placeholder="Dia do vencimento (1-31)"
                      value={cardDueDay}
                      disabled={!canEditContas}
                      onChange={(e) => setCardDueDay(sanitizeIntegerInputValue(e.target.value, 2))}
                    />
                    <small className="mgr-hint">
                      Dica: informe o fechamento no máximo 5 dias antes do vencimento da fatura.
                    </small>
                    <button type="button" onClick={onUpdateCard} disabled={!canEditContas || isPendingAction("updateCard")}>
                      {isPendingAction("updateCard") ? "Atualizando..." : "Atualizar cartão"}
                    </button>
                    <button type="button" className="danger" onClick={onDeleteCard} disabled={!canDeleteContas || isPendingAction("deleteCard")}>
                      {isPendingAction("deleteCard") ? "Excluindo..." : "Excluir cartão"}
                    </button>
                  </div>
                  {cardMsg ? <p>{cardMsg}</p> : null}
                </section>
              </>
            ) : null}

            {managerTab === "Usuários e workspaces" ? (
              <>
                <section className="card">
                  <h3>Workspace atual</h3>
                  <p className="workspace-meta-line">
                    <b>ID:</b> {user.workspace_id || "-"} | <b>Nome:</b> {user.workspace_name || "-"} |{" "}
                    <b>Papel:</b> {user.workspace_role || "-"} | <b>Status:</b> {user.workspace_status || "-"}
                  </p>
                  <form className="workspace-rename-form" onSubmit={onRenameCurrentWorkspace}>
                    <input
                      type="text"
                      placeholder="Renomear workspace"
                      value={workspaceNameDraft}
                      onChange={(e) => setWorkspaceNameDraft(e.target.value)}
                      disabled={!isSuperAdmin && !isWorkspaceOwner}
                    />
                    <button type="submit" disabled={(!isSuperAdmin && !isWorkspaceOwner) || isPendingAction("workspaceRename")}>
                      {isPendingAction("workspaceRename") ? "Salvando..." : "Atualizar nome"}
                    </button>
                  </form>
                  <form className="workspace-invite-form" onSubmit={onAddWorkspaceGuest}>
                    <input
                      type="email"
                      placeholder="E-mail do convidado (GUEST)"
                      value={workspaceInviteEmail}
                      onChange={(e) => setWorkspaceInviteEmail(e.target.value)}
                      disabled={!canManageWorkspaceUsers}
                    />
                    <input
                      type="text"
                      placeholder="Nome (opcional)"
                      value={workspaceInviteName}
                      onChange={(e) => setWorkspaceInviteName(e.target.value)}
                      disabled={!canManageWorkspaceUsers}
                    />
                    <button type="submit" disabled={!canManageWorkspaceUsers || isPendingAction("workspaceInvite")}>
                      {isPendingAction("workspaceInvite") ? "Salvando..." : "Adicionar convidado"}
                    </button>
                  </form>
                  <p className="workspace-helper-text">
                    Se o e-mail já existir, o usuário é vinculado ao workspace atual. Se não existir, o Domus cria o acesso e envia um e-mail para definição da senha de primeiro acesso.
                  </p>
                  {workspaceManageMsg ? <p className="status-msg">{workspaceManageMsg}</p> : null}
                </section>

                <section className="card">
                  <h3>Membros e permissões</h3>
                  {workspaceMembersLoading ? <p>Carregando membros...</p> : null}
                  <div className="tx-table-wrap assets-table-wrap">
                    <table className="tx-table assets-table">
                      <thead>
                        <tr>
                          <th>Usuário</th>
                          <th>E-mail</th>
                          <th>Papel</th>
                          <th>Ativo</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workspaceMembersSorted.map((m) => {
                          const role = String(m.workspace_role || "").toUpperCase();
                          const draft = workspacePermDrafts[String(m.user_id)] || buildPermissionsDraft(m);
                          const canRemove = role !== "OWNER" && Number(m.user_id) !== Number(user.id);
                          return (
                            <Fragment key={`member-${m.user_id}`}>
                              <tr key={`member-row-${m.user_id}`}>
                                <td>{m.display_name || "-"}</td>
                                <td>{m.email || "-"}</td>
                                <td>{role || "-"}</td>
                                <td>{m.is_active ? "Sim" : "Não"}</td>
                                <td>
                                  {canRemove ? (
                                    <button
                                      type="button"
                                      className="tx-action-neutral"
                                      onClick={() => onRemoveWorkspaceMember(m.user_id)}
                                      disabled={isPendingAction(`workspaceRemove-${m.user_id}`)}
                                    >
                                      {isPendingAction(`workspaceRemove-${m.user_id}`) ? "Removendo..." : "Remover"}
                                    </button>
                                  ) : (
                                    "-"
                                  )}
                                </td>
                              </tr>
                              {role === "GUEST" ? (
                                <tr key={`member-perm-${m.user_id}`}>
                                  <td colSpan={5}>
                                    <div className="perm-grid">
                                      {draft.map((perm) => (
                                        <div key={`${m.user_id}-${perm.module}`} className="perm-row">
                                          <div className="perm-module">{WORKSPACE_PERMISSION_LABELS[perm.module] || perm.module}</div>
                                          <label>
                                            <input
                                              type="checkbox"
                                              checked={Boolean(perm.can_view)}
                                              onChange={(e) =>
                                                onToggleMemberPermission(m.user_id, perm.module, "can_view", e.target.checked)
                                              }
                                            />
                                            Ver
                                          </label>
                                          <label>
                                            <input
                                              type="checkbox"
                                              checked={Boolean(perm.can_add)}
                                              onChange={(e) =>
                                                onToggleMemberPermission(m.user_id, perm.module, "can_add", e.target.checked)
                                              }
                                            />
                                            Incluir
                                          </label>
                                          <label>
                                            <input
                                              type="checkbox"
                                              checked={Boolean(perm.can_edit)}
                                              onChange={(e) =>
                                                onToggleMemberPermission(m.user_id, perm.module, "can_edit", e.target.checked)
                                              }
                                            />
                                            Editar
                                          </label>
                                          <label>
                                            <input
                                              type="checkbox"
                                              checked={Boolean(perm.can_delete)}
                                              onChange={(e) =>
                                                onToggleMemberPermission(m.user_id, perm.module, "can_delete", e.target.checked)
                                              }
                                            />
                                            Excluir
                                          </label>
                                        </div>
                                      ))}
                                      <div>
                                        <button
                                          type="button"
                                          className="tx-action-primary"
                                          onClick={() => onSaveMemberPermissions(m.user_id)}
                                          disabled={isPendingAction(`workspacePerms-${m.user_id}`)}
                                        >
                                          {isPendingAction(`workspacePerms-${m.user_id}`) ? "Salvando..." : "Salvar permissões"}
                                        </button>
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              ) : null}
                            </Fragment>
                          );
                        })}
                        {!workspaceMembersSorted.length && !workspaceMembersLoading ? (
                          <tr>
                            <td colSpan={5}>Nenhum membro encontrado para o workspace atual.</td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </section>

                {isSuperAdmin ? (
                  <>
                    <section className="card">
                      <h3>Criar workspace (SUPER_ADMIN)</h3>
                      <form className="workspace-create-form" onSubmit={onCreateAdminWorkspace}>
                        <input
                          type="text"
                          placeholder="Nome do workspace"
                          value={adminWorkspaceName}
                          onChange={(e) => setAdminWorkspaceName(e.target.value)}
                        />
                        <input
                          type="email"
                          placeholder="E-mail do owner"
                          value={adminOwnerEmail}
                          onChange={(e) => setAdminOwnerEmail(e.target.value)}
                        />
                        <input
                          type="text"
                          placeholder="Nome do owner (opcional)"
                          value={adminOwnerDisplayName}
                          onChange={(e) => setAdminOwnerDisplayName(e.target.value)}
                        />
                        <button type="submit" disabled={isPendingAction("adminCreateWorkspace")}>
                          {isPendingAction("adminCreateWorkspace") ? "Criando..." : "Criar workspace"}
                        </button>
                      </form>
                      <p className="workspace-helper-text">
                        Se o e-mail do owner já existir, ele assume o novo workspace como OWNER. Se não existir, o Domus cria o usuário e envia um e-mail para definição da senha de primeiro acesso.
                      </p>
                      {adminMsg ? <p className="status-msg">{adminMsg}</p> : null}
                    </section>

                    <section className="card">
                      <h3>Workspaces (SUPER_ADMIN)</h3>
                      <div className="tx-table-wrap">
                        <table className="tx-table">
                          <thead>
                            <tr>
                              <th>ID</th>
                              <th>Nome</th>
                              <th>Owner</th>
                              <th>Status</th>
                              <th>Membros</th>
                              <th>Ação</th>
                            </tr>
                          </thead>
                          <tbody>
                            {adminWorkspaces.map((ws) => {
                              const wsId = Number(ws.workspace_id || ws.id || 0);
                              const wsStatus = normalizeWorkspaceStatus(ws.workspace_status || ws.status);
                              return (
                                <tr key={wsId}>
                                  <td>{wsId}</td>
                                  <td>{ws.workspace_name || ws.name || "-"}</td>
                                  <td>{ws.owner_email || "-"}</td>
                                  <td>{wsStatus}</td>
                                  <td>{Number(ws.members_count || 0)}</td>
                                  <td>
                                    <button
                                      type="button"
                                      className={wsStatus === "active" ? "" : "tx-action-primary"}
                                      onClick={() => onToggleAdminWorkspaceStatus(wsId, wsStatus)}
                                      disabled={adminStatusUpdatingId === String(wsId)}
                                    >
                                      {adminStatusUpdatingId === String(wsId)
                                        ? "Atualizando..."
                                        : wsStatus === "active"
                                          ? "Bloquear"
                                          : "Ativar"}
                                    </button>
                                  </td>
                                </tr>
                              );
                            })}
                            {!adminWorkspaces.length ? (
                              <tr>
                                <td colSpan={6}>Nenhum workspace encontrado.</td>
                              </tr>
                            ) : null}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  </>
                ) : null}
              </>
            ) : null}
          </>
        ) : null}

        {page === "Lançamentos" && canViewLancamentos ? (
          <>
            <section className="card">
              <h3>Novo lançamento</h3>
              <div className="invest-tabs tx-view-tabs">
                <button
                  type="button"
                  className={`mini-tab ${txView === "caixa" ? "active" : ""}`}
                  onClick={() => setTxView("caixa")}
                >
                  Caixa
                </button>
                <button
                  type="button"
                  className={`mini-tab ${txView === "competencia" ? "active" : ""}`}
                  onClick={() => setTxView("competencia")}
                >
                  Competência
                </button>
                <button
                  type="button"
                  className={`mini-tab ${txView === "futuro" ? "active" : ""}`}
                  onClick={() => setTxView("futuro")}
                >
                  Compromissos
                </button>
              </div>
              {txView === "competencia" ? (
                <>
                  <div className="transfer-hint tx-info-block">
                    <strong className="transfer-badge">Compromissos</strong>
                    <span>
                      Use a aba Compromissos para contas a vencer: se hoje ainda não passou do dia informado, a 1ª
                      parcela entra neste mês; depois replica pelos próximos meses.
                    </span>
                  </div>
                  <div className="transfer-hint tx-info-block tx-info-block-last">
                    <strong className="transfer-badge">Competência</strong>
                    <span>
                      A aba Competência apresenta valores já comprometidos - como lançamentos previstos ou vinculados a
                      faturas futuras - que ainda não foram efetivamente pagos ou recebidos.
                      <br />
                      Esses valores não impactam o saldo atual até a data de vencimento ou liquidação.
                    </span>
                  </div>
                </>
              ) : null}
              {txView !== "competencia" ? (
                canAddLancamentos ? (
                <form className="tx-form" onSubmit={onCreateTransaction}>
                {txIsTransfer ? (
                  <div className="transfer-hint">
                    <strong className="transfer-badge">Transferência</strong>
                    <span>
                      Fluxo em duas pernas: débito na <b>conta origem</b> e crédito na <b>conta destino</b> (Banco e/ou Corretora).
                    </span>
                  </div>
                ) : null}
                {txIsExpense && !txIsTransfer ? (
                  <div className="transfer-hint">
                    <strong className="transfer-badge">Despesa</strong>
                    <span>
                      Use a aba Compromissos para contas a vencer: se hoje ainda não passou do dia informado, a 1ª parcela entra neste mês; depois replica pelos próximos meses.
                    </span>
                  </div>
                ) : null}
                {txIsFutureTab || (txIsExpense && !txIsTransfer && txMethodEffective === "Futuro") ? (
                  <>
                    <select
                      name="future_payment_method"
                      value={txFuturePaymentMethod}
                      onChange={(e) => setTxFuturePaymentMethod(e.target.value)}
                    >
                      <option value="PIX">PIX</option>
                      <option value="Debito">Débito</option>
                      <option value="Boleto">Boleto</option>
                      <option value="Credito">Cartão de Crédito</option>
                    </select>
                    {txFuturePaymentMethod === "Credito" ? (
                      <>
                        <select
                          name="card_id"
                          value={txCardId}
                          onChange={(e) => setTxCardId(e.target.value)}
                          required
                        >
                          <option value="">Cartão de crédito</option>
                          {cardsForTxMethod.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name} - {c.brand || "Visa"} ({c.linked_account})
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={
                            selectedTxCard
                              ? `Fechamento: dia ${selectedTxCard.close_day || Math.max(1, Number(selectedTxCard.due_day || 1) - 5)} | Vencimento: dia ${selectedTxCard.due_day || "-"}`
                              : "Fechamento/Vencimento serão usados do cadastro do cartão"
                          }
                          disabled
                        />
                      </>
                    ) : null}
                    {txFuturePaymentMethod !== "Credito" ? (
                      <input
                        name="due_day"
                        type="text"
                        inputMode="numeric"
                        placeholder="Dia de vencimento (1-31)"
                        onInput={(e) => applyIntegerMaskInput(e, 2)}
                        required
                      />
                    ) : null}
                    <input
                      name="repeat_months"
                      type="text"
                      inputMode="numeric"
                      placeholder={txFuturePaymentMethod === "Credito" ? "Parcelamento (qtd. de parcelas)" : "Meses para replicar"}
                      onInput={(e) => applyIntegerMaskInput(e, 3)}
                      required
                    />
                  </>
                ) : (
                  <input name="date" type="date" required />
                )}
                {txIsCashTab ? (
                  <>
                    <select
                      name="category_id"
                      required
                      value={txCategoryId}
                      onChange={(e) => setTxCategoryId(e.target.value)}
                    >
                      <option value="">Categoria</option>
                      {txCategoriesForForm.map((c) => (
                        <option key={c.id} value={c.id}>{c.name} ({c.kind})</option>
                      ))}
                    </select>
                    <select
                      name="method"
                      value={txMethod}
                      onChange={(e) => setTxMethod(e.target.value)}
                      required
                      disabled={!txMethodOptions.length}
                    >
                      {!txMethodOptions.length ? (
                        <option value="">Selecione a categoria</option>
                      ) : null}
                      {txMethodOptions.map((m) => (
                        <option key={m} value={m}>{m === "Futuro" ? "Compromissos" : m}</option>
                      ))}
                    </select>
                    {!txIsExpenseCredit ? (
                      <select
                        name="account_id"
                        required
                        value={txAccountId}
                        onChange={(e) => setTxAccountId(e.target.value)}
                      >
                        <option value="" disabled>
                          {txIsIncome ? "Conta (entrada da receita)" : txIsExpense ? "Conta (saída da despesa)" : "Conta"}
                        </option>
                        {(txIsTransfer ? transferAccounts : accounts).map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    ) : null}
                    {txIsExpense && !txIsTransfer && txMethodEffective === "Credito" ? (
                      <select
                        name="card_id"
                        value={txCardId}
                        onChange={(e) => setTxCardId(e.target.value)}
                        required
                      >
                        <option value="">Cartão de crédito (obrigatório)</option>
                        {cardsForTxMethod.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} - {c.brand || "Visa"} ({c.linked_account})
                          </option>
                        ))}
                      </select>
                    ) : null}
                    {txIsExpenseCredit ? (
                      <input
                        type="text"
                        value={selectedTxCard ? `Conta vinculada: ${selectedTxCard.linked_account}` : "Conta vinculada: -"}
                        disabled
                      />
                    ) : null}
                    {txIsTransfer ? (
                      <select
                        name="source_account_id"
                        value={txSourceAccountId}
                        onChange={(e) => setTxSourceAccountId(e.target.value)}
                        required
                      >
                        <option value="">Conta origem (Transferência)</option>
                        {transferAccounts
                          .filter((a) => String(a.id) !== String(txAccountId))
                          .map((a) => (
                            <option key={a.id} value={a.id}>{a.name}</option>
                          ))}
                      </select>
                    ) : null}
                    <input name="notes" type="text" placeholder="Obs (opcional)" />
                  </>
                ) : null}
                <input name="description" type="text" placeholder="Descrição (opcional)" />
                <input
                  name="amount"
                  type="text"
                  inputMode="numeric"
                  placeholder="Valor"
                  onInput={applyCurrencyMaskInput}
                  required
                />
                {!txIsCashTab ? (
                  <>
                    <select
                      name="category_id"
                      required
                      value={txCategoryId}
                      onChange={(e) => setTxCategoryId(e.target.value)}
                    >
                      <option value="">Categoria</option>
                      {txCategoriesForForm.map((c) => (
                        <option key={c.id} value={c.id}>{c.name} ({c.kind})</option>
                      ))}
                    </select>
                    {txIsFutureTab ? (
                      <input type="text" value="Compromissos" disabled />
                    ) : (
                      <select
                        name="method"
                        value={txMethod}
                        onChange={(e) => setTxMethod(e.target.value)}
                        required
                        disabled={!txMethodOptions.length}
                      >
                        {!txMethodOptions.length ? (
                          <option value="">Selecione a categoria</option>
                        ) : null}
                        {txMethodOptions.map((m) => (
                          <option key={m} value={m}>{m === "Futuro" ? "Compromissos" : m}</option>
                        ))}
                      </select>
                    )}
                    {!txIsExpenseCredit ? (
                      <select
                        name="account_id"
                        required
                        value={txAccountId}
                        onChange={(e) => setTxAccountId(e.target.value)}
                      >
                        <option value="" disabled>
                          {txIsIncome ? "Conta (entrada da receita)" : txIsExpense ? "Conta (saída da despesa)" : "Conta"}
                        </option>
                        {(txIsTransfer ? transferAccounts : accounts).map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    ) : null}
                    {txIsTransfer ? (
                      <select
                        name="source_account_id"
                        value={txSourceAccountId}
                        onChange={(e) => setTxSourceAccountId(e.target.value)}
                        required
                      >
                        <option value="">Conta origem (Transferência)</option>
                        {transferAccounts
                          .filter((a) => String(a.id) !== String(txAccountId))
                          .map((a) => (
                            <option key={a.id} value={a.id}>{a.name}</option>
                          ))}
                      </select>
                    ) : null}
                    {txIsExpense && !txIsTransfer && txMethodEffective === "Credito" ? (
                      <select
                        name="card_id"
                        value={txCardId}
                        onChange={(e) => setTxCardId(e.target.value)}
                        required
                      >
                        <option value="">Cartão de crédito (obrigatório)</option>
                        {cardsForTxMethod.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} - {c.brand || "Visa"} ({c.linked_account})
                          </option>
                        ))}
                      </select>
                    ) : null}
                    {txIsExpenseCredit ? (
                      <input
                        type="text"
                        value={selectedTxCard ? `Conta vinculada: ${selectedTxCard.linked_account}` : "Conta vinculada: -"}
                        disabled
                      />
                    ) : null}
                    <input name="notes" type="text" placeholder="Obs (opcional)" />
                  </>
                ) : null}
                <button type="submit" disabled={isPendingAction("createTransaction")}>
                  {isPendingAction("createTransaction") ? "Salvando..." : "Salvar lançamento"}
                </button>
              </form>
                ) : (
                  <p>Sem permissão para incluir lançamentos.</p>
                )
              ) : null}
              {txView !== "competencia" && txMsg ? <p>{txMsg}</p> : null}
            </section>

            <section className="card">
              <h3>Lançamentos recentes</h3>
              <div className="tx-recent-filters">
                <input
                  type="date"
                  className="invoice-filter-select"
                  value={txRecentDateFrom}
                  onChange={(e) => setTxRecentDateFrom(e.target.value)}
                />
                <input
                  type="date"
                  className="invoice-filter-select"
                  value={txRecentDateTo}
                  onChange={(e) => setTxRecentDateTo(e.target.value)}
                />
                <select
                  className="invoice-filter-select"
                  value={txRecentCategoryFilterId}
                  onChange={(e) => setTxRecentCategoryFilterId(e.target.value)}
                >
                  <option value="">Todas as categorias</option>
                  {txRecentCategoryOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name} ({opt.kind})
                    </option>
                  ))}
                </select>
                <select
                  className="invoice-filter-select"
                  value={txRecentStatusFilter}
                  onChange={(e) => setTxRecentStatusFilter(e.target.value)}
                >
                  <option value="">Todos os status</option>
                  {txRecentStatusOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="tx-table-wrap">
                <table className="tx-table">
                  <thead>
                        <tr>
                          <th>ID</th>
                          <th>Data</th>
                          <th>Descrição</th>
                          <th>Conta</th>
                          <th>Cartão</th>
                          <th>Categoria</th>
                          <th>Status</th>
                          <th>Valor</th>
                          <th>Ação</th>
                        </tr>
                  </thead>
                  <tbody>
                    {transactionsVisibleOrdered.map((t) => (
                      <tr key={t.id}>
                        <td>{t.id}</td>
                        <td>
                          {commitmentEdit?.id === t.id ? (
                            <input
                              type="date"
                              value={String(commitmentEdit.payment_date || "")}
                              onChange={(e) =>
                                setCommitmentEdit((prev) => (prev ? { ...prev, payment_date: e.target.value } : prev))
                              }
                            />
                          ) : (
                            t.date
                          )}
                        </td>
                        <td>{t.description}</td>
                        <td>
                          {commitmentEdit?.id === t.id ? (
                            <select
                              value={String(commitmentEdit.account_id || "")}
                              onChange={(e) =>
                                setCommitmentEdit((prev) => (prev ? { ...prev, account_id: e.target.value } : prev))
                              }
                            >
                              <option value="">Conta</option>
                              {(accounts || [])
                                .filter((a) => {
                                  const tp = normalizeAccountType(a.type);
                                  return tp === "Banco" || tp === "Dinheiro";
                                })
                                .map((a) => (
                                  <option key={a.id} value={a.id}>
                                    {a.name}
                                  </option>
                                ))}
                            </select>
                          ) : (
                            t.account || "-"
                          )}
                        </td>
                        <td>{t.card_name || "-"}</td>
                        <td>{t.category || "-"}</td>
                        <td>{t.charge_status || "-"}</td>
                        <td>
                          {commitmentEdit?.id === t.id ? (
                            <input
                              type="text"
                              inputMode="numeric"
                              value={String(commitmentEdit.amount || "")}
                              onChange={(e) =>
                                setCommitmentEdit((prev) =>
                                  prev ? { ...prev, amount: formatCurrencyInputValue(e.target.value) } : prev
                                )
                              }
                            />
                          ) : (
                            Number(t.amount_brl || 0).toFixed(2)
                          )}
                        </td>
                        <td>
                          {String(t.source_type || "") === "credit_charge" ? (
                            "-"
                          ) : String(t.source_type || "") === "credit_commitment" ? (
                            canDeleteLancamentos ? (
                                <button type="button" className="danger" onClick={() => onDeleteCreditCommitment(t)} disabled={isPendingAction(`deleteCreditCommitment-${String(t.id || "").replace(/^ccf-/, "")}-single`) || isPendingAction(`deleteCreditCommitment-${String(t.id || "").replace(/^ccf-/, "")}-future`)}>
                                  Excluir
                                </button>
                            ) : (
                              "-"
                            )
                          ) : commitmentEdit?.id === t.id ? (
                            <>
                              {canAddLancamentos ? (
                                <button type="button" className="tx-action-primary" onClick={onConfirmPayCommitment} disabled={isPendingAction(`payCommitment-${commitmentEdit?.id}`)}>
                                  {isPendingAction(`payCommitment-${commitmentEdit?.id}`) ? "Confirmando..." : "Confirmar"}
                                </button>
                              ) : null}
                              <button
                                type="button"
                                className="tx-action-neutral"
                                onClick={() => setCommitmentEdit(null)}
                                style={{ marginLeft: canAddLancamentos ? 8 : 0 }}
                              >
                                Cancelar
                              </button>
                            </>
                          ) : isCommitmentTx(t) ? (
                            <>
                              {canAddLancamentos ? (
                                <button type="button" className="tx-action-pay" onClick={() => onStartPayCommitment(t)}>Pagar</button>
                              ) : null}
                              {canDeleteLancamentos ? (
                                <button
                                  type="button"
                                  className="danger"
                                  onClick={() => onDeleteCommitment(t)}
                                  style={{ marginLeft: canAddLancamentos ? 8 : 0 }}
                                >
                                  {isPendingAction(`deleteTransaction-${t.id}-single`) || isPendingAction(`deleteTransaction-${t.id}-future`) ? "Excluindo..." : "Excluir"}
                                </button>
                              ) : null}
                              {!canAddLancamentos && !canDeleteLancamentos ? "-" : null}
                            </>
                          ) : (
                            canDeleteLancamentos ? (
                              <button type="button" onClick={() => onDeleteTransaction(t.id)} disabled={isPendingAction(`deleteTransaction-${t.id}-single`)}>
                                {isPendingAction(`deleteTransaction-${t.id}-single`) ? "Excluindo..." : "Excluir"}
                              </button>
                            ) : (
                              "-"
                            )
                          )}
                        </td>
                      </tr>
                    ))}
                    {!transactionsVisibleOrdered.length ? (
                      <tr>
                        <td colSpan={8}>Nenhum lançamento para a categoria selecionada.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}

        {page === "Importar CSV" && canViewRelatorios ? (
          <>
            <section className="card">
              <h3>Importar lançamentos (CSV)</h3>
              <p>Colunas mínimas: <code>date, description, amount, account</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  disabled={!canAddRelatorios}
                  onChange={(e) => setTxCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewTransactionsCsv} disabled={!canAddRelatorios || isPendingAction("previewTransactionsCsv")}>
                  {isPendingAction("previewTransactionsCsv") ? "Gerando prévia..." : "Prévia lançamentos"}
                </button>
                <button onClick={onImportTransactionsCsv} disabled={!canAddRelatorios || isPendingAction("importTransactionsCsv")}>
                  {isPendingAction("importTransactionsCsv") ? "Importando..." : "Importar lançamentos"}
                </button>
              </div>
            </section>

            <section className="card">
              <h3>Importar ativos (CSV)</h3>
              <p>Colunas mínimas: <code>symbol, name, asset_class</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  disabled={!canAddRelatorios}
                  onChange={(e) => setAssetCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewAssetsCsv} disabled={!canAddRelatorios || isPendingAction("previewAssetsCsv")}>
                  {isPendingAction("previewAssetsCsv") ? "Gerando prévia..." : "Prévia ativos"}
                </button>
                <button onClick={onImportAssetsCsv} disabled={!canAddRelatorios || isPendingAction("importAssetsCsv")}>
                  {isPendingAction("importAssetsCsv") ? "Importando..." : "Importar ativos"}
                </button>
              </div>
            </section>

            <section className="card">
              <h3>Importar operações (CSV)</h3>
              <p>Colunas mínimas: <code>date, asset_id/symbol, side, quantity, price</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  disabled={!canAddRelatorios}
                  onChange={(e) => setTradeCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewTradesCsv} disabled={!canAddRelatorios || isPendingAction("previewTradesCsv")}>
                  {isPendingAction("previewTradesCsv") ? "Gerando prévia..." : "Prévia operações"}
                </button>
                <button onClick={onImportTradesCsv} disabled={!canAddRelatorios || isPendingAction("importTradesCsv")}>
                  {isPendingAction("importTradesCsv") ? "Importando..." : "Importar operações"}
                </button>
              </div>
            </section>

            <section className="card">
              <h3>Prévia</h3>
              {importMsg ? <p>{importMsg}</p> : null}
              {importPreview.length ? (
                <div className="tx-table-wrap">
                  <table className="tx-table">
                    <thead>
                      <tr>
                        {Object.keys(importPreview[0]).map((k) => (
                          <th key={k}>{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {importPreview.map((row, idx) => (
                        <tr key={idx}>
                          {Object.keys(importPreview[0]).map((k) => (
                            <td key={`${idx}-${k}`}>{String(row[k] ?? "")}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>Sem prévia no momento.</p>
              )}
            </section>
          </>
        ) : null}

        {page === "Investimentos" && canViewInvestimentos ? (
          <>
            <section className="card tabs-card">
              <div className="mini-tabs">
                {INVEST_TABS.map((t) => (
                  <button
                    key={t}
                    className={`mini-tab ${investTab === t ? "active" : ""}`}
                    onClick={() => setInvestTab(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              {investRentabilitySyncRunning ? <p>Atualizando rentabilidade da renda fixa...</p> : null}
              {!investRentabilitySyncRunning && investRentabilityMsg ? <p>{investRentabilityMsg}</p> : null}
              {investMsg ? <p>{investMsg}</p> : null}
            </section>

            {investTab === "Resumo" ? (
              <>
                <section className="card">
                  <div className="tx-form invest-summary-toolbar">
                    <select
                      className="invoice-filter-select"
                      value={investSummaryClassFilter}
                      onChange={(e) => setInvestSummaryClassFilter(e.target.value)}
                    >
                      <option value="">Todas as classes</option>
                      {investSummaryClassOptions.map((cls) => (
                        <option key={cls} value={cls}>{cls}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className={`mini-tab ${investDivergenceOpen ? "active" : ""}`}
                      onClick={() => setInvestDivergenceOpen((v) => !v)}
                    >
                      Carregar divergências
                    </button>
                  </div>
                </section>
                <section className="cards">
                  <article className="card">
                    <h3>Ativos</h3>
                    <strong>{Number(investSummaryViewData.assets_count || 0)}</strong>
                  </article>
                  <article className="card">
                    <h3>Total investido</h3>
                    <strong>{brl.format(normalizeSignedZero(investSummaryViewData.total_invested))}</strong>
                  </article>
                  <article className="card">
                    <h3>Saldo na corretora</h3>
                    <strong>{brl.format(normalizeSignedZero(investSummaryViewData.broker_balance))}</strong>
                  </article>
                  <article className="card">
                    <h3>Valor de mercado</h3>
                    <strong>{brl.format(normalizeSignedZero(investSummaryViewData.total_market))}</strong>
                  </article>
                  <article className="card">
                    <h3>Retorno total</h3>
                    <strong>{brl.format(normalizeSignedZero(investSummaryViewData.total_return))}</strong>
                    <p>{Number(investSummaryViewData.total_return_pct || 0).toFixed(2)}%</p>
                  </article>
                  <article className="card">
                    <h3>P&L não realizado</h3>
                    <strong>{brl.format(normalizeSignedZero(investSummaryViewData.total_unrealized))}</strong>
                  </article>
                </section>
                <section className="card">
                  <div className="fair-value-head">
                    <div>
                      <h3>Preço justo e viés</h3>
                      <p className="tx-helper">
                        Regra aplicada: cotação atual menor ou igual ao preço de entrada = Comprar; maior ou igual ao preço teto = Vender; entre os dois = Aguardar. O sinal técnico é automático; o objetivo do usuário é manual.
                      </p>
                    </div>
                  </div>
                  <div className="tx-form fair-value-form">
                    <select
                      value={fairValueClassFilter}
                      onChange={(e) => {
                        setFairValueClassFilter(e.target.value);
                        setFairValueAssetId("");
                      }}
                    >
                      <option value="" disabled>Classe do ativo</option>
                      {fairValueClassOptions.map((assetClass) => (
                        <option key={assetClass} value={assetClass}>{assetClass}</option>
                      ))}
                    </select>
                    <select
                      value={fairValueAssetId}
                      onChange={(e) => setFairValueAssetId(e.target.value)}
                      disabled={!fairValueClassFilter}
                    >
                      <option value="" disabled>
                        {!fairValueClassFilter ? "Selecione a classe primeiro" : "Selecione o ativo"}
                      </option>
                      {fairValueAssetOptions.map((asset) => (
                        <option key={asset.id} value={asset.id}>{asset.symbol} - {asset.name}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={selectedFairValueAsset ? fairValueDrafts[String(selectedFairValueAsset.id)]?.fair_price || "" : ""}
                      onChange={(e) => selectedFairValueAsset && onChangeFairValueDraft(selectedFairValueAsset.id, "fair_price", e.target.value)}
                      placeholder="Preço justo"
                      disabled={!selectedFairValueAsset || !canEditInvestimentos || isPendingAction(`fairValue-${selectedFairValueAsset?.id}`)}
                    />
                    <input
                      type="text"
                      inputMode="decimal"
                      value={selectedFairValueAsset ? fairValueDrafts[String(selectedFairValueAsset.id)]?.safety_margin_pct || "20,00" : ""}
                      onChange={(e) => selectedFairValueAsset && onChangeFairValueDraft(selectedFairValueAsset.id, "safety_margin_pct", e.target.value)}
                      placeholder="Margem de segurança (%)"
                      disabled={!selectedFairValueAsset || !canEditInvestimentos || isPendingAction(`fairValue-${selectedFairValueAsset?.id}`)}
                    />
                    <select
                      value={selectedFairValueAsset ? fairValueDrafts[String(selectedFairValueAsset.id)]?.user_objective || "" : ""}
                      onChange={(e) => selectedFairValueAsset && onChangeFairValueDraft(selectedFairValueAsset.id, "user_objective", e.target.value)}
                      disabled={!selectedFairValueAsset || !canEditInvestimentos || isPendingAction(`fairValue-${selectedFairValueAsset?.id}`)}
                    >
                      <option value="">Objetivo do usuário</option>
                      {USER_OBJECTIVE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="tx-action-primary"
                      onClick={() => selectedFairValueAsset && onSaveAssetFairValue(selectedFairValueAsset)}
                      disabled={!selectedFairValueAsset || !canEditInvestimentos || isPendingAction(`fairValue-${selectedFairValueAsset?.id}`)}
                    >
                      {isPendingAction(`fairValue-${selectedFairValueAsset?.id}`) ? "Salvando..." : "Salvar preço justo"}
                    </button>
                  </div>
                  {selectedFairValueAsset ? (
                    <div className="fair-value-preview-grid">
                      <div className="card">
                        <h4>Ativo selecionado</h4>
                        <strong>{selectedFairValueAsset.symbol}</strong>
                        <p>{selectedFairValueAsset.name}</p>
                      </div>
                      <div className="card">
                        <h4>Entrada</h4>
                        <strong>{selectedFairValueAsset.entryPrice == null ? "-" : brl.format(selectedFairValueAsset.entryPrice)}</strong>
                      </div>
                      <div className="card">
                        <h4>Cotação atual</h4>
                        <strong>{selectedFairValueAsset.currentPrice == null ? "-" : brl.format(selectedFairValueAsset.currentPrice)}</strong>
                      </div>
                      <div className="card">
                        <h4>Teto</h4>
                        <strong>{selectedFairValueAsset.ceilingPrice == null ? "-" : brl.format(selectedFairValueAsset.ceilingPrice)}</strong>
                      </div>
                      <div className="card">
                        <h4>Sinal técnico</h4>
                        <span className={`fair-value-bias ${selectedFairValueAsset.technicalSignal.tone}`}>{selectedFairValueAsset.technicalSignal.label}</span>
                      </div>
                      <div className="card">
                        <h4>Objetivo do usuário</h4>
                        <strong>{formatUserObjectiveLabel(selectedFairValueAsset.userObjective)}</strong>
                      </div>
                    </div>
                  ) : null}
                  <div className="tx-table-wrap fair-value-table-wrap">
                    <table className="tx-table fair-value-table">
                      <thead>
                        <tr>
                          <th>Ativo</th>
                          <th>Preço justo</th>
                          <th>Margem (%)</th>
                          <th>Entrada</th>
                          <th>Cotação atual</th>
                          <th>Teto</th>
                          <th>Sinal técnico</th>
                          <th>Objetivo</th>
                          <th>Relatório PDF</th>
                          <th>Ações</th>
                        </tr>
                      </thead>
                      <tbody>
                        {configuredFairValueAssets.map((asset) => {
                          const uploadPending = isPendingAction(`fairValueReportUpload-${asset.id}`);
                          const downloadPending = isPendingAction(`fairValueReportDownload-${asset.id}`);
                          const fairValuePending = isPendingAction(`fairValue-${asset.id}`);
                          const fairValueDeletePending = isPendingAction(`fairValueDelete-${asset.id}`);
                          const isInlineEditing = fairValueInlineEditId === String(asset.id);
                          return (
                            <tr key={`fair-value-${asset.id}`}>
                              <td>
                                <strong>{asset.symbol}</strong>
                                <div>{asset.name}</div>
                              </td>
                              <td>
                                {isInlineEditing ? (
                                  <input
                                    type="text"
                                    inputMode="numeric"
                                    value={fairValueDrafts[String(asset.id)]?.fair_price || ""}
                                    onChange={(e) => onChangeFairValueDraft(asset.id, "fair_price", e.target.value)}
                                    disabled={!canEditInvestimentos || fairValuePending}
                                  />
                                ) : (
                                  asset.fairPrice == null ? "-" : brl.format(asset.fairPrice)
                                )}
                              </td>
                              <td>{asset.safetyMarginPct == null ? "-" : `${formatLocalizedNumber(asset.safetyMarginPct, 2)}%`}</td>
                              <td>{asset.entryPrice == null ? "-" : brl.format(asset.entryPrice)}</td>
                              <td>
                                {asset.currentPrice == null ? "-" : brl.format(asset.currentPrice)}
                                {asset.priceRefDate ? <div>{formatIsoDatePtBr(asset.priceRefDate)}</div> : null}
                              </td>
                              <td>{asset.ceilingPrice == null ? "-" : brl.format(asset.ceilingPrice)}</td>
                              <td>
                                <span className={`fair-value-bias ${asset.technicalSignal.tone}`}>{asset.technicalSignal.label}</span>
                              </td>
                              <td>
                                <span className={`fair-value-bias ${getUserObjectiveTone(asset.userObjective)}`}>
                                  {formatUserObjectiveLabel(asset.userObjective)}
                                </span>
                              </td>
                              <td className="fair-value-report-cell">
                                <input
                                  ref={(node) => {
                                    if (node) {
                                      valuationReportInputRefs.current[String(asset.id)] = node;
                                    } else {
                                      delete valuationReportInputRefs.current[String(asset.id)];
                                    }
                                  }}
                                  type="file"
                                  accept="application/pdf,.pdf"
                                  className="fair-value-report-input"
                                  onChange={(e) => {
                                    const selectedFile = e.target.files?.[0] || null;
                                    if (selectedFile) {
                                      onUploadAssetValuationReport(asset, selectedFile);
                                    }
                                    e.target.value = "";
                                  }}
                                />
                                <div className="fair-value-report-actions">
                                  <button
                                    type="button"
                                    className="tx-action-neutral fair-value-report-icon-btn"
                                    disabled={uploadPending || !canEditInvestimentos}
                                    onClick={() => triggerAssetValuationReportSelect(asset.id)}
                                    aria-label={asset.valuation_report_uploaded_at ? "Trocar PDF do relatório" : "Enviar PDF do relatório"}
                                    title={asset.valuation_report_uploaded_at ? "Trocar PDF" : "Enviar PDF"}
                                  >
                                    {uploadPending ? "..." : <span className="fair-value-report-icon" aria-hidden="true" />}
                                  </button>
                                  {asset.valuation_report_uploaded_at ? (
                                    <div className="fair-value-report-download-group">
                                      <button
                                        type="button"
                                        className="tx-action-primary fair-value-report-download-btn"
                                        disabled={downloadPending}
                                        onClick={() => onDownloadAssetValuationReport(asset)}
                                        aria-label="Baixar PDF do relatório"
                                        title="Baixar PDF"
                                      >
                                        <img src={downloadIcon} alt="" className="fair-value-download-icon" aria-hidden="true" />
                                      </button>
                                      <div className="fair-value-report-meta">
                                        {formatIsoDatePtBr(asset.valuation_report_uploaded_at)}
                                      </div>
                                    </div>
                                  ) : null}
                                </div>
                              </td>
                              <td>
                                <div className="fair-value-row-actions">
                                  <button
                                    type="button"
                                    className={isInlineEditing ? "tx-action-primary fair-value-edit-btn" : "tx-action-neutral fair-value-edit-btn"}
                                    onClick={() => onToggleInlineFairValueEdit(asset)}
                                    disabled={!canEditInvestimentos || fairValuePending || fairValueDeletePending}
                                  >
                                    {fairValuePending ? "Salvando..." : isInlineEditing ? "Salvar" : "Editar"}
                                  </button>
                                  <button
                                    type="button"
                                    className="danger fair-value-delete-btn"
                                    onClick={() => onDeleteAssetFairValue(asset)}
                                    disabled={!canEditInvestimentos || fairValuePending || fairValueDeletePending}
                                  >
                                    {fairValueDeletePending ? "Excluindo..." : "Excluir"}
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                        {!configuredFairValueAssets.length ? (
                          <tr>
                            <td colSpan={10}>Nenhum ativo configurado com preço justo ainda.</td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </section>
                {investDivergenceOpen ? (
                  <section className="card">
                    <h3>Divergência de rentabilidade</h3>
                    <div className="tx-form invest-divergence-form">
                      <input
                        type="text"
                        inputMode="decimal"
                        value={investDivergenceThreshold}
                        onChange={(e) => setInvestDivergenceThreshold(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 2, maxIntegerDigits: 3 }))}
                        placeholder="Limiar de divergência (%)"
                      />
                      <button type="button" onClick={onLoadInvestDivergenceReport} disabled={investDivergenceRunning}>
                        {investDivergenceRunning ? "Gerando relatório..." : "Atualizar relatório"}
                      </button>
                    </div>
                    {investDivergenceMsg ? <p>{investDivergenceMsg}</p> : null}
                    <div className="tx-table-wrap">
                      <table className="tx-table">
                        <thead>
                          <tr>
                            <th>Ativo</th>
                            <th>Tipo</th>
                            <th>Valor salvo</th>
                            <th>Valor projetado</th>
                            <th>Delta</th>
                            <th>Delta %</th>
                            <th>Atualização proj.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {investDivergenceReport.map((row) => (
                            <tr key={`${row.asset_id}-${row.symbol}`}>
                              <td>{row.symbol || row.asset_id}</td>
                              <td>{formatRentabilityTypeLabel(row.rentability_type)}</td>
                              <td>{brl.format(Number(row.stored_current_value || 0))}</td>
                              <td>{brl.format(Number(row.projected_current_value || 0))}</td>
                              <td>{brl.format(Number(row.delta_value || 0))}</td>
                              <td>{Number(row.delta_pct || 0).toFixed(4)}%</td>
                              <td>{formatIsoDatePtBr(row.projected_last_update)}</td>
                            </tr>
                          ))}
                          {!investDivergenceReport.length ? (
                            <tr>
                              <td colSpan={7}>Sem divergências acima do limiar selecionado.</td>
                            </tr>
                          ) : null}
                        </tbody>
                      </table>
                    </div>
                  </section>
                ) : null}
                <section className="card">
                  <h3>Carteira (consolidado)</h3>
                  <div className="tx-form invest-portfolio-toolbar">
                    <select
                      className="invoice-filter-select"
                      value={investPortfolioClassFilter}
                      onChange={(e) => setInvestPortfolioClassFilter(e.target.value)}
                    >
                      <option value="">Todas as classes</option>
                      {investSummaryClassOptions.map((cls) => (
                        <option key={cls} value={cls}>{cls}</option>
                      ))}
                    </select>
                  </div>
                  <div className="tx-table-wrap portfolio-table-wrap">
                    <table className="tx-table portfolio-table">
                      <thead>
                        <tr>
                          <th>Ativo</th>
                          <th>Classe</th>
                          <th>Qtd</th>
                          <th>Custo médio</th>
                          <th>Custo</th>
                          <th>Mercado</th>
                          <th>Líquido</th>
                          <th>Origem</th>
                          <th>Data</th>
                          <th>P&amp;L</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investPortfolioPositionsVisible.map((p) => (
                          <tr key={`${p.asset_id}-${p.symbol}`}>
                            <td>{p.symbol}</td>
                            <td>{p.asset_class}</td>
                            <td>{formatPortfolioQty(p.qty)}</td>
                            <td>{brl.format(Number(p.avg_cost || 0))}</td>
                            <td>{brl.format(Number(p.cost_basis || 0))}</td>
                            <td>{brl.format(Number((p.market_value_gross ?? p.market_value) || 0))}</td>
                            <td>{brl.format(Number((p.estimated_net_value ?? p.market_value) || 0))}</td>
                            <td>{formatValueOriginLabel(p.value_origin)}</td>
                            <td>{formatIsoDatePtBr(p.value_ref_date)}</td>
                            <td>{brl.format(Number(p.unrealized_pnl || 0))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="tx-helper">
                    Mercado Bruto representa o valor atual do ativo antes de descontos de saída. Líquido Estimado replica o bruto enquanto não houver regra fiscal configurada por ativo.
                  </p>
                </section>
              </>
            ) : null}

            {investTab === "Rentabilidade" ? (
              <>
                <section className="card">
                  <div className="rentability-head">
                    <div>
                      <h3>Rentabilidade por carteira</h3>
                      <p className="tx-helper">
                        Indicadores consolidados por classe de ativo, usando custo, valor de mercado, proventos e P&amp;L da carteira.
                      </p>
                    </div>
                    <div className="rentability-window-shortcuts" role="tablist" aria-label="Janela de rentabilidade">
                      {RENTABILITY_WINDOW_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          className={`rentability-window-chip ${investRentabilityWindow === option.value ? "active" : ""}`}
                          onClick={() => setInvestRentabilityWindow(option.value)}
                          aria-pressed={investRentabilityWindow === option.value}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="tx-helper rentability-window-helper">
                    Janela aplicada: {RENTABILITY_WINDOW_OPTIONS.find((option) => option.value === investRentabilityWindow)?.label || "Desde o início"}.
                    A análise cruza operações, proventos e posição consolidada atual para destacar as classes com atividade no período.
                  </p>
                  <section className="rentability-highlight-grid">
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Carteiras monitoradas</span>
                      <strong>{investRentabilityHighlights.classes_count}</strong>
                      <p>Classes com posição consolidada na carteira.</p>
                    </article>
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Melhor desempenho</span>
                      <strong>{investRentabilityHighlights.best ? `${Number(investRentabilityHighlights.best.total_return_pct || 0).toFixed(2)}%` : "-"}</strong>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.best ? `Valor: ${brl.format(Number(investRentabilityHighlights.best.total_return || 0))}` : "Valor: -"}
                      </span>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.best ? `Participação: ${Number(investRentabilityHighlights.best.participation_pct || 0).toFixed(2)}%` : "Participação: -"}
                      </span>
                      <p>{investRentabilityHighlights.best?.asset_class || "Sem dados"}</p>
                    </article>
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Pior desempenho</span>
                      <strong>{investRentabilityHighlights.worst ? `${Number(investRentabilityHighlights.worst.total_return_pct || 0).toFixed(2)}%` : "-"}</strong>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.worst ? `Valor: ${brl.format(Number(investRentabilityHighlights.worst.total_return || 0))}` : "Valor: -"}
                      </span>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.worst ? `Participação: ${Number(investRentabilityHighlights.worst.participation_pct || 0).toFixed(2)}%` : "Participação: -"}
                      </span>
                      <p>{investRentabilityHighlights.worst?.asset_class || "Sem dados"}</p>
                    </article>
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Maior participação</span>
                      <strong>{investRentabilityHighlights.biggest ? `${Number(investRentabilityHighlights.biggest.participation_pct || 0).toFixed(2)}%` : "-"}</strong>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.biggest ? `Mercado: ${brl.format(Number(investRentabilityHighlights.biggest.total_market || 0))}` : "Mercado: -"}
                      </span>
                      <p>{investRentabilityHighlights.biggest?.asset_class || "Sem dados"}</p>
                    </article>
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Rentabilidade consolidada</span>
                      <strong>{`${Number(investRentabilityHighlights.consolidated?.total_return_pct || 0).toFixed(2)}%`}</strong>
                      <span className="rentability-highlight-value">
                        {`Valor: ${brl.format(Number(investRentabilityHighlights.consolidated?.total_return || 0))}`}
                      </span>
                      <p>No per&iacute;odo selecionado.</p>
                    </article>
                    <article className="card rentability-highlight-card">
                      <span className="rentability-highlight-label">Melhor ativo</span>
                      <strong>{investRentabilityHighlights.best_asset ? `${Number(investRentabilityHighlights.best_asset.total_return_pct || 0).toFixed(2)}%` : "-"}</strong>
                      <span className="rentability-highlight-value">
                        {investRentabilityHighlights.best_asset ? `Valor: ${brl.format(Number(investRentabilityHighlights.best_asset.total_return || 0))}` : "Valor: -"}
                      </span>
                      <p>
                        {investRentabilityHighlights.best_asset
                          ? `${investRentabilityHighlights.best_asset.symbol} | ${investRentabilityHighlights.best_asset.asset_class}`
                          : "Sem dados"}
                      </p>
                    </article>
                  </section>
                  <section className="card benchmark-comparison-card">
                    <div className="benchmark-comparison-head">
                      <div>
                        <h3>Carteira x Benchmark</h3>
                        <p className="tx-helper">
                          MVP seguro: neste quadro o histórico já está disponível para classes comparadas com CDI. As demais classes mostram o benchmark-alvo, mas aguardam integração histórica.
                        </p>
                      </div>
                      <div className="benchmark-comparison-filter">
                        <label htmlFor="benchmark-class-select">Classe</label>
                        <select
                          id="benchmark-class-select"
                          className="invoice-filter-select"
                          value={investBenchmarkClass}
                          onChange={(e) => setInvestBenchmarkClass(e.target.value)}
                        >
                          {investBenchmarkOptions.map((item) => (
                            <option key={item.asset_class} value={item.asset_class}>
                              {item.asset_class} {item.benchmark_ready ? "" : "(em preparação)"}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="benchmark-summary-grid">
                      <article className="card benchmark-summary-item">
                        <span className="rentability-highlight-label">Minha carteira</span>
                        <strong>{selectedRentabilityClass ? `${Number(selectedRentabilityClass.total_return_pct || 0).toFixed(2)}%` : "-"}</strong>
                        <p>{selectedRentabilityClass ? `Valor: ${brl.format(Number(selectedRentabilityClass.total_return || 0))}` : "Sem dados"}</p>
                      </article>
                      <article className="card benchmark-summary-item">
                        <span className="rentability-highlight-label">Benchmark</span>
                        <strong>{selectedBenchmarkOption ? selectedBenchmarkOption.benchmark_label : "-"}</strong>
                        <p>
                          {selectedBenchmarkOption?.benchmark_ready
                            ? `${selectedBenchmarkReturnPct.toFixed(2)}% no período`
                            : "Histórico ainda não disponível no DOMUS"}
                        </p>
                      </article>
                      <article className="card benchmark-summary-item">
                        <span className="rentability-highlight-label">Gap</span>
                        <strong>{selectedBenchmarkOption?.benchmark_ready ? `${selectedBenchmarkGapPct >= 0 ? "+" : ""}${selectedBenchmarkGapPct.toFixed(2)} p.p.` : "-"}</strong>
                        <p>
                          {selectedBenchmarkOption
                            ? `Benchmark-alvo: ${selectedBenchmarkOption.benchmark_label}`
                            : "Selecione uma classe"}
                        </p>
                      </article>
                    </div>
                    {selectedBenchmarkOption?.benchmark_ready ? (
                      benchmarkComparisonChartData.length ? (
                        <div className="chart-box benchmark-comparison-chart">
                          <ResponsiveContainer width="100%" height={320}>
                            <LineChart data={benchmarkComparisonChartData}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} />
                              <XAxis dataKey="ref_date" tickFormatter={(value) => formatMonthYearPtBr(String(value || "").slice(0, 7))} />
                              <YAxis tickFormatter={(value) => `${Number(value || 0).toFixed(0)}%`} width={72} />
                              <Tooltip
                                formatter={(value, name) => {
                                  const label = name === "portfolio_return_pct" ? "Minha carteira" : selectedBenchmarkOption.benchmark_label;
                                  return [`${Number(value || 0).toFixed(2)}%`, label];
                                }}
                                labelFormatter={(value) => formatIsoDatePtBr(value)}
                              />
                              <Legend />
                              <Line
                                type="monotone"
                                dataKey="portfolio_return_pct"
                                name="Minha carteira"
                                stroke="#66d5ff"
                                strokeWidth={3}
                                dot={false}
                                activeDot={{ r: 4 }}
                                connectNulls
                                hide={!hasSufficientPortfolioBenchmarkHistory}
                              />
                              <Line
                                type="monotone"
                                dataKey="benchmark_return_pct"
                                name={selectedBenchmarkOption.benchmark_label}
                                stroke="#f4c84b"
                                strokeWidth={3}
                                dot={false}
                                activeDot={{ r: 4 }}
                                connectNulls
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <p className="tx-helper">Sem série histórica suficiente para comparação no período selecionado.</p>
                      )
                    ) : (
                      <p className="tx-helper">
                        Benchmark configurado para esta classe: <strong>{selectedBenchmarkOption?.benchmark_label || "-"}</strong>. A série histórica ainda não foi integrada ao DOMUS neste MVP.
                      </p>
                    )}
                    {investBenchmarkLoading ? <p className="tx-helper">Carregando benchmark...</p> : null}
                    {!investBenchmarkLoading && investBenchmarkError ? <p className="tx-helper">{investBenchmarkError}</p> : null}
                    {!investBenchmarkLoading && !hasSufficientPortfolioBenchmarkHistory ? (
                      <p className="tx-helper">Linha da carteira ainda com histórico insuficiente nesta classe. O card resume a rentabilidade atual corretamente, mas a curva só fica confiável com mais pontos salvos em `prices`.</p>
                    ) : null}
                  </section>
                  {investRentabilityByClass.length ? (
                    <div className="chart-box rentability-chart">
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={investRentabilityByClass} barCategoryGap={18}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="asset_class" />
                          <YAxis tickFormatter={(value) => `${Number(value || 0).toFixed(0)}%`} width={72} />
                          <Tooltip
                            formatter={(value, _name, payload) => {
                              const row = payload?.payload || {};
                              return [
                                `${Number(value || 0).toFixed(2)}% | Participação ${Number(row.participation_pct || 0).toFixed(2)}%`,
                                "Rentabilidade",
                              ];
                            }}
                            labelFormatter={(value) => String(value || "")}
                          />
                          <Bar dataKey="total_return_pct" radius={[12, 12, 0, 0]}>
                            {investRentabilityByClass.map((item) => (
                              <Cell
                                key={`rentability-bar-${item.asset_class}`}
                                fill={Number(item.total_return_pct || 0) >= 0 ? "#5dd39e" : "#ff7b7b"}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <p>Sem dados consolidados de rentabilidade por classe.</p>
                  )}
                </section>
                <section className="card">
                  <h3>Indicadores por tipo de carteira</h3>
                  <div className="tx-table-wrap">
                    <table className="tx-table rentability-table">
                      <thead>
                        <tr>
                          <th>Classe</th>
                          <th>Ativos</th>
                          <th>Investido</th>
                          <th>Mercado</th>
                          <th>Proventos</th>
                          <th>Realizado</th>
                          <th>P&amp;L não realizado</th>
                          <th>Retorno total</th>
                          <th>Participação</th>
                          <th>Rentabilidade</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investRentabilityByClass.map((row) => (
                          <tr key={`rentability-${row.asset_class}`}>
                            <td>{row.asset_class}</td>
                            <td>{row.assets_count}</td>
                            <td>{brl.format(Number(row.total_invested || 0))}</td>
                            <td>{brl.format(Number(row.total_market || 0))}</td>
                            <td>{brl.format(Number(row.total_income || 0))}</td>
                            <td>{brl.format(Number(row.total_realized || 0))}</td>
                            <td>{brl.format(Number(row.total_unrealized || 0))}</td>
                            <td>{brl.format(Number(row.total_return || 0))}</td>
                            <td>{Number(row.participation_pct || 0).toFixed(2)}%</td>
                            <td className={Number(row.total_return_pct || 0) >= 0 ? "rentability-positive" : "rentability-negative"}>
                              {Number(row.total_return_pct || 0).toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                        {!investRentabilityByClass.length ? (
                          <tr>
                            <td colSpan={10}>Nenhuma carteira consolidada para exibir.</td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : null}

            {investTab === "Ativos" ? (
              <>
                <section className="card">
                  <h3>Novo ativo</h3>
                  <form className="tx-form" onSubmit={onCreateInvestAsset}>
                    <input name="symbol" type="text" placeholder="Símbolo" required />
                    <input name="name" type="text" placeholder="Nome" required />
                    <select
                      name="asset_class"
                      value={assetCreateClass}
                      onChange={(e) => setAssetCreateClass(e.target.value)}
                    >
                      <option value="" disabled>Classe</option>
                      {investMeta.asset_classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    {assetCreateIsFixedIncome ? (
                      <select
                        value={assetCreateRentabilityType}
                        onChange={(e) => setAssetCreateRentabilityType(e.target.value)}
                      >
                        <option value="" disabled>Tipo de rentabilidade</option>
                        {RENTABILITY_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    ) : null}
                    {assetCreateIsFixedIncome && assetCreateRentabilityType === "PREFIXADO" ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetCreateFixedRate}
                        onChange={(e) => setAssetCreateFixedRate(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Taxa anual (%)"
                      />
                    ) : null}
                    {assetCreateIsFixedIncome &&
                    (assetCreateRentabilityType === "PCT_CDI" || assetCreateRentabilityType === "PCT_SELIC") ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetCreateIndexPct}
                        onChange={(e) => setAssetCreateIndexPct(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Percentual do índice (%)"
                      />
                    ) : null}
                    {assetCreateIsFixedIncome &&
                    ["CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD"].includes(assetCreateRentabilityType) ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetCreateSpreadRate}
                        onChange={(e) => setAssetCreateSpreadRate(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Spread anual (%)"
                      />
                    ) : null}
                    <select name="sector" defaultValue="Não definido">
                      {investMeta.asset_sectors.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <select name="currency" defaultValue="BRL">
                      <option value="BRL">BRL</option>
                      <option value="USD">USD</option>
                    </select>
                    <select name="broker_account_id" defaultValue="">
                      <option value="">(sem corretora)</option>
                      {accounts
                        .filter((a) => a.type === "Corretora")
                        .map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                    </select>
                    <button type="submit" disabled={isPendingAction("createInvestAsset")}>
                      {isPendingAction("createInvestAsset") ? "Salvando..." : "Salvar ativo"}
                    </button>
                  </form>
                </section>

                <section className="card">
                  <h3>Editar ativo</h3>
                  <div className="mgr-grid">
                    <select
                      value={assetEditClassFilter}
                      onChange={(e) => {
                        setAssetEditClassFilter(e.target.value);
                        setAssetEditId("");
                      }}
                    >
                      <option value="" disabled>Classe do ativo</option>
                      {investMeta.asset_classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <select
                      value={assetEditId}
                      onChange={(e) => {
                        const id = e.target.value;
                        setAssetEditId(id);
                      }}
                      disabled={!assetEditClassFilter}
                    >
                      <option value="" disabled>
                        {!assetEditClassFilter ? "Selecione a classe primeiro" : "Selecione o ativo"}
                      </option>
                      {assetEditOptions.map((a) => (
                        <option key={a.id} value={a.id}>{a.id} - {a.symbol} ({a.asset_class})</option>
                      ))}
                    </select>
                    <input value={assetEditSymbol} onChange={(e) => setAssetEditSymbol(e.target.value)} placeholder="Símbolo" />
                    <input value={assetEditName} onChange={(e) => setAssetEditName(e.target.value)} placeholder="Nome" />
                    <select value={assetEditClass} onChange={(e) => setAssetEditClass(e.target.value)}>
                      {investMeta.asset_classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    {assetEditIsFixedIncome ? (
                      <select
                        value={assetEditRentabilityType}
                        onChange={(e) => setAssetEditRentabilityType(e.target.value)}
                      >
                        <option value="" disabled>Tipo de rentabilidade</option>
                        {RENTABILITY_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    ) : null}
                    {assetEditIsFixedIncome && assetEditRentabilityType === "PREFIXADO" ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetEditFixedRate}
                        onChange={(e) => setAssetEditFixedRate(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Taxa anual (%)"
                      />
                    ) : null}
                    {assetEditIsFixedIncome &&
                    (assetEditRentabilityType === "PCT_CDI" || assetEditRentabilityType === "PCT_SELIC") ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetEditIndexPct}
                        onChange={(e) => setAssetEditIndexPct(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Percentual do índice (%)"
                      />
                    ) : null}
                    {assetEditIsFixedIncome &&
                    ["CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD"].includes(assetEditRentabilityType) ? (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={assetEditSpreadRate}
                        onChange={(e) => setAssetEditSpreadRate(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 3 }))}
                        placeholder="Spread anual (%)"
                      />
                    ) : null}
                    <select value={assetEditSector} onChange={(e) => setAssetEditSector(e.target.value)}>
                      {investMeta.asset_sectors.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <select value={assetEditCurrency} onChange={(e) => setAssetEditCurrency(e.target.value)}>
                      <option value="BRL">BRL</option>
                      <option value="USD">USD</option>
                    </select>
                    <select value={assetEditBrokerId} onChange={(e) => setAssetEditBrokerId(e.target.value)}>
                      <option value="">(sem corretora)</option>
                      {accounts
                        .filter((a) => a.type === "Corretora")
                        .map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                    </select>
                    <input value={`Valor atual: ${assetEditCurrentValueLabel}`} readOnly />
                    <input value={`Última atualização: ${assetEditLastUpdateLabel}`} readOnly />
                    <button onClick={onUpdateInvestAsset} disabled={isPendingAction("updateInvestAsset")}>
                      {isPendingAction("updateInvestAsset") ? "Atualizando..." : "Atualizar ativo"}
                    </button>
                  </div>
                </section>

                <section className="card">
                  <h3>Ativos cadastrados</h3>
                  <div className="table-toolbar">
                    <select
                      value={investAssetsClassFilter}
                      onChange={(e) => setInvestAssetsClassFilter(e.target.value)}
                    >
                      <option value="">Todas as classes</option>
                      {tradeAssetClassOptions.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>Símbolo</th>
                          <th>Nome</th>
                          <th>Classe</th>
                          <th>Rentabilidade</th>
                          <th>Setor</th>
                          <th>Moeda</th>
                          <th>Corretora</th>
                          <th>Valor atual</th>
                          <th>Última atualização</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investAssetsVisible.map((a) => (
                          <tr key={a.id}>
                            <td>{a.symbol}</td>
                            <td>{a.name}</td>
                            <td>{a.asset_class}</td>
                            <td>{formatAssetRentabilitySummary(a)}</td>
                            <td>{a.sector || "-"}</td>
                            <td>{a.currency}</td>
                            <td>{a.broker_account || "-"}</td>
                            <td>{a.current_value == null ? "-" : brl.format(Number(a.current_value || 0))}</td>
                            <td>{formatIsoDatePtBr(a.last_update)}</td>
                            <td>
                              <button onClick={() => onDeleteInvestAsset(a.id)} disabled={isPendingAction(`deleteInvestAsset-${a.id}`)}>
                                {isPendingAction(`deleteInvestAsset-${a.id}`) ? "Excluindo..." : "Excluir"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : null}

            {investTab === "Operações" ? (
              <>
                <section className="card">
                  <h3>Nova operação</h3>
                  <form className="tx-form" onSubmit={onCreateInvestTrade}>
                    <select
                      name="asset_class_filter"
                      value={tradeAssetClassFilter}
                      onChange={(e) => setTradeAssetClassFilter(e.target.value)}
                    >
                      <option value="" disabled>Classe do ativo</option>
                      {tradeAssetClassOptions.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <select
                      name="asset_id"
                      value={tradeAssetId}
                      onChange={(e) => setTradeAssetId(e.target.value)}
                      disabled={!tradeAssetClassFilter}
                    >
                      <option value="" disabled>
                        {!tradeAssetClassFilter ? "Selecione a classe primeiro" : "Ativo"}
                      </option>
                      {tradeAssetOptions.map((a) => (
                        <option key={a.id} value={a.id}>{a.symbol}</option>
                      ))}
                    </select>
                    <input name="date" type="date" required />
                    <select name="side" value={tradeSide} onChange={(e) => setTradeSide(e.target.value)}>
                      {tradeSideOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    {tradeShowQuantityPrice ? (
                      <>
                        <input
                          name="quantity"
                          type="text"
                          inputMode="decimal"
                          placeholder={tradeQuantityPlaceholder}
                          onInput={(e) => applyDecimalMaskInput(e, { maxDecimals: 8, maxIntegerDigits: 12 })}
                          required
                        />
                        <input
                          name="price"
                          type="text"
                          inputMode="numeric"
                          placeholder={tradeAssetIsUsStock ? "Preço (USD)" : "Preço"}
                          onInput={applyCurrencyMaskInput}
                          required
                        />
                      </>
                    ) : null}
                    {tradeShowAppliedValue ? (
                      <>
                        <input
                          name="applied_value"
                          type="text"
                          inputMode="numeric"
                          placeholder={tradeFixedIncomeIsSell ? "Valor bruto do resgate" : "Valor da aplicação"}
                          onInput={applyCurrencyMaskInput}
                          required
                        />
                      </>
                    ) : null}
                    {tradeShowIrIof ? (
                      <input
                        name="ir_iof"
                        type="text"
                        inputMode="decimal"
                        placeholder="IR/IOF do resgate (%)"
                        onInput={(e) => applyDecimalMaskInput(e, { maxDecimals: 4, maxIntegerDigits: 3 })}
                      />
                    ) : null}
                    {tradeAssetIsUsStock ? (
                      <input
                        name="exchange_rate"
                        type="text"
                        inputMode="decimal"
                        placeholder="Cotação USD/BRL"
                        value={tradeExchangeRate}
                        onChange={(e) => setTradeExchangeRate(sanitizeDecimalInputValue(e.target.value, { maxDecimals: 4, maxIntegerDigits: 6 }))}
                        required
                      />
                    ) : null}
                    <input
                      name="fees"
                      type="text"
                      inputMode="numeric"
                      placeholder={
                        tradeAssetIsFixedIncome
                          ? tradeFixedIncomeIsSell
                            ? "Taxas do resgate (opcional)"
                            : "Taxas da aplicação (opcional)"
                          : "Taxas (opcional, padrão 0)"
                      }
                      aria-label="Taxas"
                      onInput={applyCurrencyMaskInput}
                    />
                    {tradeShowGenericTaxes ? (
                      <input
                        name="taxes"
                        type="text"
                        inputMode="numeric"
                        placeholder={
                          tradeAssetIsFixedIncome
                            ? "Impostos do resgate (opcional)"
                            : "Impostos (opcional, padrão 0)"
                        }
                        aria-label="Impostos"
                        onInput={applyCurrencyMaskInput}
                      />
                    ) : null}
                    <input name="note" type="text" placeholder="Obs (opcional)" />
                    <button type="submit" disabled={isPendingAction("createInvestTrade")}>
                      {isPendingAction("createInvestTrade") ? "Salvando..." : "Salvar operação"}
                    </button>
                  </form>
                  {tradeAssetIsFixedIncome ? (
                    <p className="tx-helper">
                      {tradeFixedIncomeIsSell
                        ? "Em resgates de renda fixa, IR/IOF, taxas e impostos reduzem o valor líquido recebido."
                        : "Em aplicações de renda fixa, o valor atual do ativo é acompanhado em bruto; descontos fiscais entram no resgate."}
                    </p>
                  ) : null}
                </section>

                <section className="card">
                  <h3>Operações recentes</h3>
                  <div className="tx-form invest-date-filter-form">
                    <input
                      type="date"
                      value={investTradeDateFrom}
                      onChange={(e) => setInvestTradeDateFrom(e.target.value)}
                    />
                    <input
                      type="date"
                      value={investTradeDateTo}
                      onChange={(e) => setInvestTradeDateTo(e.target.value)}
                    />
                  </div>
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Data</th>
                          <th>Ativo</th>
                          <th>Tipo</th>
                          <th>Qtd</th>
                          <th>Preço</th>
                          <th>Cotação</th>
                          <th>Taxas</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investTradesVisible.map((t) => (
                          <tr key={t.id}>
                            <td>{t.id}</td>
                            <td>{t.date}</td>
                            <td>{t.symbol}</td>
                            <td>{formatTradeSideLabel(t.side, t.asset_class)}</td>
                            <td>{Number(t.quantity || 0).toFixed(8)}</td>
                            <td>{Number(t.price || 0).toFixed(4)}</td>
                            <td>
                              {Number(t.exchange_rate || 0) > 0 && Number(t.exchange_rate || 1) !== 1
                                ? Number(t.exchange_rate).toFixed(4)
                                : "-"}
                            </td>
                            <td>{Number(t.fees || 0).toFixed(2)}</td>
                            <td>
                              <button type="button" onClick={() => onDeleteInvestTrade(t.id)} disabled={isPendingAction(`deleteInvestTrade-${t.id}`)}>
                                {isPendingAction(`deleteInvestTrade-${t.id}`) ? "Excluindo..." : "Excluir"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : null}

            {investTab === "Proventos" ? (
              <>
                <section className="card">
                  <h3>Novo provento</h3>
                  <form className="tx-form" onSubmit={onCreateInvestIncome}>
                    <select
                      value={incomeAssetClassFilter}
                      onChange={(e) => {
                        setIncomeAssetClassFilter(e.target.value);
                        setIncomeAssetId("");
                      }}
                    >
                      <option value="" disabled>Classe do ativo</option>
                      {tradeAssetClassOptions.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    <select
                      name="asset_id"
                      value={incomeAssetId}
                      onChange={(e) => setIncomeAssetId(e.target.value)}
                      disabled={!incomeAssetClassFilter}
                    >
                      <option value="" disabled>{incomeAssetClassFilter ? "Selecione o ativo" : "Selecione a classe primeiro"}</option>
                      {incomeAssetOptions.map((a) => (
                        <option key={a.id} value={a.id}>{a.symbol}</option>
                      ))}
                    </select>
                    <input name="date" type="date" required />
                    <select name="type" defaultValue="">
                      <option value="" disabled>Tipo</option>
                      {(investMeta.income_types || []).map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <input
                      name="amount"
                      type="text"
                      inputMode="numeric"
                      placeholder="Valor"
                      onInput={applyCurrencyMaskInput}
                      required
                    />
                    <select name="credit_account_id" defaultValue="">
                      <option value="">Conta de crédito (padrão: corretora do ativo)</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name} ({a.type})
                        </option>
                      ))}
                    </select>
                    <input name="note" type="text" placeholder="Obs (opcional)" />
                    <button type="submit" disabled={isPendingAction("createInvestIncome")}>
                      {isPendingAction("createInvestIncome") ? "Salvando..." : "Salvar provento"}
                    </button>
                  </form>
                  <p className="tx-helper">
                    Se não informar a conta de crédito, o provento será lançado na corretora vinculada ao ativo.
                  </p>
                </section>

                <section className="card">
                  <div className="income-history-head">
                    <div>
                      <h3>Histórico de proventos</h3>
                      <p className="tx-helper">
                        Evolução mensal dos proventos recebidos dentro do período filtrado.
                      </p>
                    </div>
                  </div>
                  <section className="income-history-kpis">
                    <article className="card income-history-kpi">
                      <span className="income-history-kpi-label">Total do período</span>
                      <strong>{brl.format(Number(investIncomeHistorySummary.total || 0))}</strong>
                    </article>
                    <article className="card income-history-kpi">
                      <span className="income-history-kpi-label">Média mensal</span>
                      <strong>{brl.format(Number(investIncomeHistorySummary.average || 0))}</strong>
                    </article>
                    <article className="card income-history-kpi">
                      <span className="income-history-kpi-label">Pico mensal</span>
                      <strong>{brl.format(Number(investIncomeHistorySummary.peakAmount || 0))}</strong>
                      <p>{investIncomeHistorySummary.peakMonth ? formatMonthYearPtBr(investIncomeHistorySummary.peakMonth) : "-"}</p>
                    </article>
                  </section>
                  {investIncomeTypeTotals.length ? (
                    <div className="income-history-type-list">
                      {investIncomeTypeTotals.map((item) => (
                        <article key={item.type} className="income-history-type-chip">
                          <span
                            className="income-history-type-dot"
                            style={{ background: INCOME_TYPE_COLORS[item.type] || "#8aa7ff" }}
                            aria-hidden="true"
                          />
                          <span className="income-history-type-name">{item.type}</span>
                          <strong>{brl.format(Number(item.total || 0))}</strong>
                        </article>
                      ))}
                    </div>
                  ) : null}
                  {investIncomeHistory.length ? (
                    <div className="chart-box income-history-chart">
                      <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={investIncomeHistory} barCategoryGap={18}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="month" tickFormatter={formatMonthYearPtBr} />
                          <YAxis tickFormatter={(value) => brl.format(Number(value || 0))} width={104} />
                          <Tooltip
                            cursor={{ fill: "rgba(120, 170, 255, 0.10)" }}
                            labelFormatter={(value) => formatMonthYearPtBr(value)}
                            formatter={(value, name) => [brl.format(Number(value || 0)), String(name || "Proventos")]}
                          />
                          {investIncomeTypesVisible.map((type, index) => (
                            <Bar
                              key={type}
                              dataKey={type}
                              name={type}
                              stackId="income-total"
                              radius={index === investIncomeTypesVisible.length - 1 ? [12, 12, 0, 0] : [0, 0, 0, 0]}
                              fill={INCOME_TYPE_COLORS[type] || "#8aa7ff"}
                            />
                          ))}
                          <defs>
                            <linearGradient id="incomeHistoryBarFill" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#66d5ff" stopOpacity={0.96} />
                              <stop offset="100%" stopColor="#4e7ff3" stopOpacity={0.74} />
                            </linearGradient>
                          </defs>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <p>Sem histórico de proventos para o período selecionado.</p>
                  )}
                </section>
                <section className="card">
                  <h3>Proventos recentes</h3>
                  <div className="tx-form invest-date-filter-form">
                    <input
                      type="date"
                      value={investIncomeDateFrom}
                      onChange={(e) => setInvestIncomeDateFrom(e.target.value)}
                    />
                    <input
                      type="date"
                      value={investIncomeDateTo}
                      onChange={(e) => setInvestIncomeDateTo(e.target.value)}
                    />
                  </div>
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Data</th>
                          <th>Ativo</th>
                          <th>Tipo</th>
                          <th>Conta crédito</th>
                          <th>Valor</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investIncomesVisible.map((i) => (
                          <tr key={i.id}>
                            <td>{i.id}</td>
                            <td>{i.date}</td>
                            <td>{i.symbol}</td>
                            <td>{i.type}</td>
                            <td>{i.credit_account_name || "-"}</td>
                            <td>{Number(i.amount || 0).toFixed(2)}</td>
                            <td>
                              <button onClick={() => onDeleteInvestIncome(i.id)} disabled={isPendingAction(`deleteInvestIncome-${i.id}`)}>
                                {isPendingAction(`deleteInvestIncome-${i.id}`) ? "Excluindo..." : "Excluir"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : null}

            {investTab === "Cotações" ? (
              <section className="card">
                <h3>Cotações</h3>
                <section className="card quote-section-card">
                  <div className="quote-section-head">
                    <div>
                      <h4>Atualização automática</h4>
                      <p className="tx-helper">Atualize uma classe por vez para manter o processo previsível e facilitar a futura automação.</p>
                    </div>
                  </div>
                  {investQuoteStatusNotice?.message ? (
                    <section className={`status-banner ${investQuoteStatusNotice.level === "warning" ? "warning" : "success"}`}>
                      <p className="status-msg">{investQuoteStatusNotice.message}</p>
                    </section>
                  ) : null}
                  <div className="tx-form quote-auto-form">
                    <select value={quoteGroup} onChange={(e) => setQuoteGroup(e.target.value)}>
                      <option value="" disabled>Selecione a classe</option>
                      {QUOTE_GROUP_OPTIONS.map((g) => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      inputMode="numeric"
                      value={quoteTimeout}
                      onChange={(e) => setQuoteTimeout(sanitizeIntegerInputValue(e.target.value, 3))}
                      placeholder="Timeout (s)"
                    />
                    <input
                      type="text"
                      inputMode="numeric"
                      value={quoteWorkers}
                      onChange={(e) => setQuoteWorkers(sanitizeIntegerInputValue(e.target.value, 2))}
                      placeholder="Paralelismo"
                    />
                    <button onClick={onUpdateAllInvestPrices} disabled={investPriceUpdateRunning}>
                      {investPriceUpdateRunning ? "Atualizando..." : "Atualizar cotações automáticas"}
                    </button>
                  </div>
                </section>
                {investPriceUpdateReport.length ? (
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>Ativo</th>
                          <th>Status</th>
                          <th>Preço</th>
                          <th>Fonte</th>
                          <th>Tempo (s)</th>
                          <th>Detalhe</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investPriceUpdateReport.map((row, idx) => (
                          <tr key={`${row?.symbol || "sem-symbol"}-${idx}`}>
                            <td>{row?.symbol || "-"}</td>
                            <td>{row?.ok ? "OK" : "Erro"}</td>
                            <td>{Number(row?.price || 0) > 0 ? Number(row.price).toFixed(4) : "-"}</td>
                            <td>{row?.src || "-"}</td>
                            <td>{Number.isFinite(Number(row?.elapsed_s)) ? Number(row.elapsed_s).toFixed(2) : "-"}</td>
                            <td>{row?.error || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                <section className="card quote-section-card">
                  <div className="quote-section-head">
                    <div>
                      <h4>Cotação manual</h4>
                      <p className="tx-helper">Para ações, BDRs, FIIs, stocks e cripto, informe o preço por unidade do ativo.</p>
                    </div>
                  </div>
                  <form className="tx-form" onSubmit={onUpsertInvestPrice}>
                    <select value={manualPriceClassFilter} onChange={(e) => setManualPriceClassFilter(e.target.value)}>
                      <option value="" disabled>Selecione a classe</option>
                      {MANUAL_PRICE_CLASS_OPTIONS.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                    <select name="asset_id" defaultValue="">
                      <option value="" disabled>Ativo</option>
                      {manualPriceAssets.map((a) => (
                        <option key={a.id} value={a.id}>{a.symbol}</option>
                      ))}
                    </select>
                    <input name="date" type="date" required />
                    <input
                      name="price"
                      type="text"
                      inputMode="numeric"
                      placeholder="Preço unitário"
                      title="Informe o preço por unidade do ativo, não o valor total da posição."
                      onInput={applyCurrencyMaskInput}
                      required
                    />
                    <input name="source" type="text" placeholder="Fonte" defaultValue="manual" />
                    <button type="submit" disabled={isPendingAction("upsertInvestPrice")}>
                      {isPendingAction("upsertInvestPrice") ? "Salvando..." : "Salvar cotação manual"}
                    </button>
                  </form>
                </section>
                <section className="card quote-manual-fixed-card">
                  <h3>Atualização manual de renda fixa e fundos</h3>
                  <form className="tx-form" onSubmit={onUpdateInvestManualQuote}>
                    <select value={manualQuoteAssetId} onChange={(e) => setManualQuoteAssetId(e.target.value)}>
                      <option value="" disabled>Selecione o ativo</option>
                      {investManualQuoteAssets.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.symbol} {String(a.rentability_type || "").trim().toUpperCase() === "MANUAL" ? "(Manual)" : "(Automático)"}
                        </option>
                      ))}
                    </select>
                    <select value={manualQuoteMode} onChange={(e) => setManualQuoteMode(e.target.value)}>
                      {selectedManualQuoteIsManual ? (
                        <option value="rentability">Atualizar por rentabilidade (%)</option>
                      ) : null}
                      <option value="current_value">Atualizar por valor atual</option>
                    </select>
                    <input
                      type="date"
                      value={manualQuoteDate}
                      onChange={(e) => setManualQuoteDate(e.target.value)}
                    />
                    <input
                      type="text"
                      inputMode={manualQuoteMode === "rentability" ? "decimal" : "numeric"}
                      value={manualQuoteValue}
                      onChange={(e) =>
                        setManualQuoteValue(
                          manualQuoteMode === "rentability"
                            ? sanitizeDecimalInputValue(e.target.value, { maxDecimals: 8, maxIntegerDigits: 12 })
                            : formatCurrencyInputValue(e.target.value)
                        )
                      }
                      placeholder={
                        manualQuoteMode === "rentability"
                          ? "Rentabilidade atual (%)"
                          : "Valor atual"
                      }
                    />
                    <button type="submit" disabled={isPendingAction("updateInvestManualQuote")}>
                      {isPendingAction("updateInvestManualQuote") ? "Salvando..." : "Salvar atualização manual"}
                    </button>
                  </form>
                  <p className="tx-helper">
                    {selectedManualQuoteIsManual
                      ? "Ativos manuais aceitam atualização por rentabilidade (%) ou por valor atual. Ativos automáticos aceitam apenas ajuste fino por valor atual."
                      : "Para ativos com indexador automático, use apenas valor atual como ajuste fino de carteira real. O cadastro estrutural do ativo permanece na aba Ativos."}
                  </p>
                </section>
                <div className="tx-table-wrap">
                  <table className="tx-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Ativo</th>
                        <th>Classe</th>
                        <th>Preço</th>
                        <th>Fonte</th>
                      </tr>
                    </thead>
                    <tbody>
                      {investPrices.map((p) => (
                        <tr key={`${p.asset_id}-${p.date}-${p.id}`}>
                          <td>{formatIsoDatePtBr(p.date)}</td>
                          <td>{p.symbol}</td>
                          <td>{p.asset_class}</td>
                          <td>{Number(p.price || 0).toFixed(4)}</td>
                          <td>{p.source || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : null}

          </>
        ) : null}

        {payModalOpen ? (
          <div
            className="modal-backdrop"
            onClick={() => {
              setPayModalOpen(false);
              setPayDate("");
            }}
          >
            <div className="modal-card" onClick={(e) => e.stopPropagation()}>
              <h3>Pagar fatura</h3>
              <p>
                Cartão: <b>{payInvoiceTarget?.card_name || "-"}</b><br />
                Período: <b>{payInvoiceTarget?.invoice_period || "-"}</b><br />
                Vencimento: <b>{payInvoiceTarget?.due_date || "-"}</b><br />
                Valor: <b>
                  {brl.format(
                    Math.max(
                      0,
                      Number(payInvoiceTarget?.total_amount || 0) - Number(payInvoiceTarget?.paid_amount || 0)
                    )
                  )}
                </b>
              </p>
              <select value={payAccountId} onChange={(e) => setPayAccountId(e.target.value)}>
                <option value="">Selecione conta banco para débito</option>
                {bankAccountsOnly.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
              <input
                type="date"
                value={payDate}
                onChange={(e) => setPayDate(e.target.value)}
                aria-label="Data do pagamento"
              />
              <div className="modal-actions">
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    setPayModalOpen(false);
                    setPayDate("");
                  }}
                >
                  Cancelar
                </button>
                <button type="button" onClick={confirmPayInvoiceModal} disabled={isPendingAction(`payInvoice-${payInvoiceTarget?.id}`)}>
                  {isPendingAction(`payInvoice-${payInvoiceTarget?.id}`) ? "Confirmando..." : "Confirmar pagamento"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
        {profileModalOpen ? (
          <div className="modal-overlay" onClick={() => setProfileModalOpen(false)}>
            <div className="modal-card profile-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-head">
                <div>
                  <h3>Meu perfil</h3>
                  <p className="tx-helper">Nome, e-mail, avatar e senha da sua conta.</p>
                </div>
                <button type="button" className="modal-close" onClick={() => setProfileModalOpen(false)}>Fechar</button>
              </div>
              <form className="tx-form" onSubmit={onSaveProfile}>
                <div className="profile-avatar-panel">
                  <img src={profileAvatarData || icUsuario} alt="" className="profile-avatar-preview" />
                  <div className="profile-avatar-actions">
                    <label className="profile-avatar-upload">
                      Carregar imagem
                      <input type="file" accept="image/*" onChange={onSelectProfileAvatar} />
                    </label>
                    <button type="button" className="danger" onClick={() => setProfileAvatarData("")}>
                      Remover avatar
                    </button>
                  </div>
                </div>
                <input
                  type="text"
                  placeholder="Nome"
                  value={profileDisplayName}
                  onChange={(e) => setProfileDisplayName(e.target.value)}
                />
                <input
                  type="email"
                  placeholder="E-mail"
                  value={profileEmail}
                  onChange={(e) => setProfileEmail(e.target.value)}
                  required
                />
                {renderPasswordInput({
                  placeholder: "Senha atual",
                  value: profileCurrentPassword,
                  onChange: (e) => setProfileCurrentPassword(e.target.value),
                  visible: showProfileCurrentPassword,
                  onToggle: () => setShowProfileCurrentPassword((v) => !v),
                })}
                {renderPasswordInput({
                  placeholder: "Nova senha",
                  value: profileNewPassword,
                  onChange: (e) => setProfileNewPassword(e.target.value),
                  visible: showProfileNewPassword,
                  onToggle: () => setShowProfileNewPassword((v) => !v),
                })}
                {renderPasswordInput({
                  placeholder: "Confirmar nova senha",
                  value: profileConfirmPassword,
                  onChange: (e) => setProfileConfirmPassword(e.target.value),
                  visible: showProfileConfirmPassword,
                  onToggle: () => setShowProfileConfirmPassword((v) => !v),
                })}
                <button type="submit" disabled={profileSaving}>
                  {profileSaving ? "Salvando..." : "Salvar perfil"}
                </button>
              </form>
              {profileMsg ? <p className="status-msg">{profileMsg}</p> : null}
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
