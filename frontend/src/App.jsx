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
import bankInterLogo from "./banks/banco-inter-logo.svg";
import bankBradescoLogo from "./banks/bradesco-logo.svg";
import bankItauLogo from "./banks/itau-logo.svg";
import bankNubankLogo from "./banks/nubank-logo.svg";
import bankSantanderLogo from "./banks/santander-logo.svg";
import cardVisaLogo from "./cards/visa-17.svg";
import cardMasterLogo from "./cards/mastercard-18.svg";
import cardModelBlack from "./cards/Black.png";
import cardModelGold from "./cards/Gold.png";
import cardModelPlatinum from "./cards/Platinum.png";
import cardModelOrange from "./cards/Orange.png";
import cardModelVioleta from "./cards/Violeta.png";
import cardModelVermelho from "./cards/Vermelho.png";
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
  getDashboardMonthly,
  getInvestAssets,
  getInvestIncomes,
  getInvestMeta,
  getInvestPortfolio,
  getInvestPrices,
  getInvestRentabilityDivergenceReport,
  getInvestSummary,
  getInvestTrades,
  getKpis,
  getMe,
  getWorkspaces,
  switchWorkspace,
  getWorkspaceMembers,
  createWorkspaceMember,
  updateWorkspaceMemberPermissions,
  deleteWorkspaceMember,
  getAdminWorkspaces,
  createAdminWorkspace,
  updateAdminWorkspaceStatus,
  getTransactions,
  importAssetsCsv,
  importTradesCsv,
  importTransactionsCsv,
  login,
  payCardInvoice,
  settleCommitmentTransaction,
  setToken,
  updateAllInvestRentability,
  updateAllInvestPrices,
  updateInvestAsset,
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

const INVEST_TABS = ["Resumo", "Ativos", "Operações", "Proventos", "Cotações"];
const MANAGER_TABS = ["Cadastro de contas", "Cadastro de categorias", "Cadastro cartão de crédito"];
const QUOTE_GROUP_OPTIONS = ["Ações BR", "FIIs", "Stocks", "Cripto"];
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

function getCurrentMonthRange() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const from = new Date(year, month, 1);
  const to = new Date(year, month + 1, 0);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { from: fmt(from), to: fmt(to) };
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

function normalizeWorkspaceStatus(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (raw === "blocked") return "blocked";
  return "active";
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

function sparklinePoints(values, width = 680, height = 220) {
  if (!values.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((v, i) => {
      const x = (i / Math.max(1, values.length - 1)) * width;
      const y = height - ((v - min) / span) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

function getBankLogo(name) {
  const n = normalizeText(name);
  if (n.includes("inter")) return bankInterLogo;
  if (n.includes("itau")) return bankItauLogo;
  if (n.includes("bradesco")) return bankBradescoLogo;
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
  const raw = String(value ?? "").trim().replace(",", ".");
  if (!raw) return { empty: true, value: null };
  const num = Number(raw);
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
  const iso = raw.slice(0, 10);
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return raw;
  return `${m[3]}/${m[2]}/${m[1]}`;
}

export default function App() {
  const defaultMonthRange = getCurrentMonthRange();
  const [authError, setAuthError] = useState("");
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("Dashboard");
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [cards, setCards] = useState([]);
  const [cardInvoices, setCardInvoices] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [dashKpis, setDashKpis] = useState(null);
  const [dashMonthly, setDashMonthly] = useState([]);
  const [dashExpenses, setDashExpenses] = useState([]);
  const [dashCommitments, setDashCommitments] = useState({ a_vencer: 0, vencidos: 0 });
  const [dashAccountBalance, setDashAccountBalance] = useState([]);
  const [dashDateFrom, setDashDateFrom] = useState(defaultMonthRange.from);
  const [dashDateTo, setDashDateTo] = useState(defaultMonthRange.to);
  const [dashAccount, setDashAccount] = useState("");
  const [dashView, setDashView] = useState("caixa");
  const [dashMsg, setDashMsg] = useState("");
  const [txMsg, setTxMsg] = useState("");
  const [txAccountId, setTxAccountId] = useState("");
  const [txCategoryId, setTxCategoryId] = useState("");
  const [txMethod, setTxMethod] = useState("PIX");
  const [txRecentCategoryFilterId, setTxRecentCategoryFilterId] = useState("");
  const [txRecentStatusFilter, setTxRecentStatusFilter] = useState("");
  const [txFuturePaymentMethod, setTxFuturePaymentMethod] = useState("PIX");
  const [txView, setTxView] = useState("caixa");
  const [txSourceAccountId, setTxSourceAccountId] = useState("");
  const [txCardId, setTxCardId] = useState("");
  const [commitmentEdit, setCommitmentEdit] = useState(null);
  const [cardMsg, setCardMsg] = useState("");
  const [cardCreateName, setCardCreateName] = useState("");
  const [cardCreateBrand, setCardCreateBrand] = useState("");
  const [cardCreateModel, setCardCreateModel] = useState("");
  const [cardCreateType, setCardCreateType] = useState("");
  const [cardCreateAccountId, setCardCreateAccountId] = useState("");
  const [cardCreateDueDay, setCardCreateDueDay] = useState("");
  const [cardCreateCloseDay, setCardCreateCloseDay] = useState("");
  const [cardName, setCardName] = useState("");
  const [cardBrand, setCardBrand] = useState("");
  const [cardModel, setCardModel] = useState("");
  const [cardType, setCardType] = useState("");
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
  const [investDivergenceThreshold, setInvestDivergenceThreshold] = useState("0.10");
  const [investDivergenceReport, setInvestDivergenceReport] = useState([]);
  const [investDivergenceRunning, setInvestDivergenceRunning] = useState(false);
  const [investPriceUpdateReport, setInvestPriceUpdateReport] = useState([]);
  const [investPriceUpdateRunning, setInvestPriceUpdateRunning] = useState(false);
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
  const [quoteGroups, setQuoteGroups] = useState(QUOTE_GROUP_OPTIONS);
  const [investSummaryClassFilter, setInvestSummaryClassFilter] = useState("");
  const [tradeAssetClassFilter, setTradeAssetClassFilter] = useState("");
  const [tradeAssetId, setTradeAssetId] = useState("");
  const [tradeSide, setTradeSide] = useState("BUY");
  const [tradeExchangeRate, setTradeExchangeRate] = useState("");
  const [assetCreateClass, setAssetCreateClass] = useState("");
  const [assetCreateRentabilityType, setAssetCreateRentabilityType] = useState("");
  const [assetCreateIndexPct, setAssetCreateIndexPct] = useState("");
  const [assetCreateSpreadRate, setAssetCreateSpreadRate] = useState("");
  const [assetCreateFixedRate, setAssetCreateFixedRate] = useState("");
  const [assetEditId, setAssetEditId] = useState("");
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
  const [investTab, setInvestTab] = useState("Resumo");
  const [managerTab, setManagerTab] = useState("Cadastro de contas");
  const [manageMsg, setManageMsg] = useState("");
  const [workspaces, setWorkspaces] = useState([]);
  const [workspaceMsg, setWorkspaceMsg] = useState("");
  const [workspaceSwitchingId, setWorkspaceSwitchingId] = useState("");
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [workspaceMembersLoading, setWorkspaceMembersLoading] = useState(false);
  const [workspaceInviteEmail, setWorkspaceInviteEmail] = useState("");
  const [workspaceInviteName, setWorkspaceInviteName] = useState("");
  const [workspaceInvitePassword, setWorkspaceInvitePassword] = useState("");
  const [workspacePermDrafts, setWorkspacePermDrafts] = useState({});
  const [workspaceManageMsg, setWorkspaceManageMsg] = useState("");
  const [adminWorkspaces, setAdminWorkspaces] = useState([]);
  const [adminWorkspaceName, setAdminWorkspaceName] = useState("");
  const [adminOwnerEmail, setAdminOwnerEmail] = useState("");
  const [adminOwnerDisplayName, setAdminOwnerDisplayName] = useState("");
  const [adminOwnerPassword, setAdminOwnerPassword] = useState("");
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
  const [walletCardIndex, setWalletCardIndex] = useState(0);
  const [payModalOpen, setPayModalOpen] = useState(false);
  const [payInvoiceTarget, setPayInvoiceTarget] = useState(null);
  const [payAccountId, setPayAccountId] = useState("");
  const [payDate, setPayDate] = useState("");
  const [invoiceCardFilterId, setInvoiceCardFilterId] = useState("");
  const userMenuRef = useRef(null);
  const investRentabilityLastSyncRef = useRef(0);

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
          setDashMonthly([]);
          setDashExpenses([]);
          setDashAccountBalance([]);
          setDashCommitments({ a_vencer: 0, vencidos: 0 });
          setDashMsg("");
        }
        if (canViewInvestimentos) {
          await reloadInvestData();
        } else {
          setInvestMeta({ asset_classes: [], asset_sectors: [], income_types: [] });
          setInvestAssets([]);
          setInvestTrades([]);
          setInvestIncomes([]);
          setInvestPrices([]);
          setInvestPortfolio({ positions: [] });
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
      setCardType("");
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
      setCardType("");
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
    const cur = investAssets.find((a) => String(a.id) === String(assetEditId)) || investAssets[0];
    const isFixedIncome = isFixedIncomeClass(cur.asset_class || "");
    setAssetEditId(String(cur.id));
    setAssetEditSymbol(cur.symbol || "");
    setAssetEditName(cur.name || "");
    setAssetEditClass(cur.asset_class || "");
    setAssetEditSector(cur.sector || "Não definido");
    setAssetEditCurrency((cur.currency || "BRL").toUpperCase());
    setAssetEditBrokerId(cur.broker_account_id ? String(cur.broker_account_id) : "");
    setAssetEditRentabilityType(isFixedIncome ? String(cur.rentability_type || "MANUAL").toUpperCase() : "");
    setAssetEditIndexPct(cur.index_pct == null ? "" : String(cur.index_pct));
    setAssetEditSpreadRate(cur.spread_rate == null ? "" : String(cur.spread_rate));
    setAssetEditFixedRate(cur.fixed_rate == null ? "" : String(cur.fixed_rate));
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

  const subtitle = useMemo(() => PAGE_SUBTITLES[page] || "Em migração do Streamlit", [page]);
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
    return options.map((value) => ({
      value,
      label: value === "__none__" ? "Sem status (-)" : value,
    }));
  }, [transactions]);
  const transactionsVisible = useMemo(() => {
    const targetId = String(txRecentCategoryFilterId);
    const targetName = normalizeText(txRecentCategoryFilter?.name || "");
    return (transactions || []).filter((t) => {
      if (txRecentCategoryFilterId) {
        const categoryMatches =
          String(t.category_id || "") === targetId ||
          (targetName && normalizeText(t.category || "") === targetName);
        if (!categoryMatches) return false;
      }
      if (txRecentStatusFilter) {
        const rawStatus = String(t.charge_status || "").trim();
        const statusKey = rawStatus || "__none__";
        if (statusKey !== txRecentStatusFilter) return false;
      }
      return true;
    });
  }, [transactions, txRecentCategoryFilterId, txRecentCategoryFilter, txRecentStatusFilter]);
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
      } catch (err) {
        if (cancelled) return;
        setInvestMsg(String(err.message || err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, user]);

  useEffect(() => {
    if (!txIsExpenseCredit) return;
    if (!selectedTxCard) return;
    if (String(txAccountId) !== String(selectedTxCard.card_account_id || "")) {
      setTxAccountId(String(selectedTxCard.card_account_id || ""));
    }
  }, [txIsExpenseCredit, selectedTxCard, txAccountId]);
  const isEditCreditCardType = cardType === "Credito";
  const hasEditCardTypeSelected = cardType === "Credito" || cardType === "Debito";
  const isCreateCreditCardType = cardCreateType === "Credito";
  const hasCreateCardTypeSelected = cardCreateType === "Credito" || cardCreateType === "Debito";

  const brl = useMemo(
    () =>
      new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }),
    []
  );
  const currentKpi = dashKpis || kpis || {};
  const trendValues = useMemo(
    () =>
      (dashMonthly || [])
        .map((r) => Number(r.saldo || 0))
        .filter((n) => Number.isFinite(n)),
    [dashMonthly]
  );
  const trendStart = trendValues.length ? Number(trendValues[0]) : 0;
  const trendEnd = trendValues.length ? Number(trendValues[trendValues.length - 1]) : 0;
  const trendDelta = trendEnd - trendStart;
  const trendPct = trendStart !== 0 ? (trendDelta / Math.abs(trendStart)) * 100 : 0;
  const sparkPoints = sparklinePoints(trendValues);
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
  const openInvoicesVisible = useMemo(() => {
    const selectedId = Number(invoiceCardFilterId);
    const rows = (cardInvoices || []).filter((inv) => {
      if (String(inv.status || "").toUpperCase() !== "OPEN") return false;
      if (!invoiceCardFilterId) return true;
      return Number(inv.card_id) === selectedId;
    });
    rows.sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || "")));
    return rows;
  }, [cardInvoices, invoiceCardFilterId]);
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
  const investSummaryClassOptions = useMemo(() => {
    const classes = new Set(
      (investPortfolio?.positions || [])
        .map((p) => String(p.asset_class || "").trim())
        .filter((v) => v)
    );
    return [...classes].sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [investPortfolio]);
  useEffect(() => {
    if (!investSummaryClassFilter) return;
    if (!investSummaryClassOptions.includes(investSummaryClassFilter)) {
      setInvestSummaryClassFilter("");
    }
  }, [investSummaryClassFilter, investSummaryClassOptions]);
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
    return investPortfolio.positions || [];
  }, [investTab, investSummaryClassFilter, investSummaryPositionsFiltered, investPortfolio]);
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
  useEffect(() => {
    if (!investManualQuoteAssets.length) {
      setManualQuoteAssetId("");
      return;
    }
    if (!investManualQuoteAssets.some((a) => String(a.id) === String(manualQuoteAssetId))) {
      setManualQuoteAssetId(String(investManualQuoteAssets[0].id));
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
  const donutStyle = useMemo(() => {
    if (!investmentByClass.length || investmentTotal <= 0) {
      return { background: "conic-gradient(#2f3f63 0deg 360deg)" };
    }
    let start = 0;
    const parts = investmentByClass.map((row, idx) => {
      const angle = (Number(row.value || 0) / investmentTotal) * 360;
      const end = start + angle;
      const color = DONUT_COLORS[idx % DONUT_COLORS.length];
      const out = `${color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`;
      start = end;
      return out;
    });
    return { background: `conic-gradient(${parts.join(", ")})` };
  }, [investmentByClass, investmentTotal]);

  async function onLogin(e) {
    e.preventDefault();
    setAuthError("");
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email") || "");
    const password = String(form.get("password") || "");
    try {
      const data = await login(email, password);
      setToken(data.token);
      setUser(data.user);
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
    const password = String(workspaceInvitePassword || "");
    if (!email) {
      setWorkspaceManageMsg("Informe o e-mail do usuário para convidar.");
      return;
    }
    setWorkspaceManageMsg("");
    try {
      await createWorkspaceMember({
        email,
        role: "GUEST",
        display_name: displayName || undefined,
        password: password || undefined,
      });
      setWorkspaceInviteEmail("");
      setWorkspaceInviteName("");
      setWorkspaceInvitePassword("");
      setWorkspaceManageMsg("Convidado atualizado com sucesso.");
      await reloadWorkspaceMembers();
      await reloadWorkspaces();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
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
    try {
      await updateWorkspaceMemberPermissions(Number(memberUserId), { permissions: payload });
      setWorkspaceManageMsg("Permissões salvas.");
      await reloadWorkspaceMembers();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
  }

  async function onRemoveWorkspaceMember(memberUserId) {
    if (!window.confirm("Remover este membro do workspace atual?")) return;
    setWorkspaceManageMsg("");
    try {
      await deleteWorkspaceMember(Number(memberUserId));
      setWorkspaceManageMsg("Membro removido.");
      await reloadWorkspaceMembers();
      await reloadWorkspaces();
    } catch (err) {
      setWorkspaceManageMsg(String(err.message || err));
    }
  }

  async function onCreateAdminWorkspace(e) {
    e.preventDefault();
    const workspace_name = String(adminWorkspaceName || "").trim();
    const owner_email = String(adminOwnerEmail || "").trim().toLowerCase();
    const owner_display_name = String(adminOwnerDisplayName || "").trim();
    const owner_password = String(adminOwnerPassword || "");
    if (!workspace_name || !owner_email) {
      setAdminMsg("Informe nome do workspace e e-mail do owner.");
      return;
    }
    setAdminMsg("");
    try {
      await createAdminWorkspace({
        workspace_name,
        owner_email,
        owner_display_name: owner_display_name || undefined,
        owner_password: owner_password || undefined,
      });
      setAdminWorkspaceName("");
      setAdminOwnerEmail("");
      setAdminOwnerDisplayName("");
      setAdminOwnerPassword("");
      setAdminMsg("Workspace criado com sucesso.");
      await Promise.all([reloadAdminWorkspaces(), reloadWorkspaces()]);
    } catch (err) {
      setAdminMsg(String(err.message || err));
    }
  }

  async function onToggleAdminWorkspaceStatus(workspaceId, currentStatus) {
    const target = normalizeWorkspaceStatus(currentStatus) === "active" ? "blocked" : "active";
    setAdminStatusUpdatingId(String(workspaceId));
    setAdminMsg("");
    try {
      await updateAdminWorkspaceStatus(Number(workspaceId), { status: target });
      setAdminMsg(`Workspace ${workspaceId} atualizado para ${target}.`);
      await Promise.all([reloadAdminWorkspaces(), reloadWorkspaces()]);
    } catch (err) {
      setAdminMsg(String(err.message || err));
    } finally {
      setAdminStatusUpdatingId("");
    }
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
    try {
      const [k, m, e, ab, cs] = await Promise.all([
        getDashboardKpis(filters),
        getDashboardMonthly(filters),
        getDashboardExpenses(filters),
        // Saldo de contas sempre no acumulado real (sem filtros de período/conta/visão).
        getDashboardAccountBalance({ view: "caixa" }),
        getDashboardCommitmentsSummary(filters),
      ]);
      setDashKpis(k);
      setDashMonthly(m || []);
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
      const threshold = Number(String(investDivergenceThreshold || "").replace(",", "."));
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
      setInvestMeta({ asset_classes: [], asset_sectors: [], income_types: [] });
      setInvestAssets([]);
      setInvestTrades([]);
      setInvestIncomes([]);
      setInvestPrices([]);
      setInvestPortfolio({ positions: [] });
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
      return;
    }
    const { syncRentability = false, forceRentabilitySync = false } = options || {};
    if (syncRentability) {
      await syncInvestRentabilityBeforeLoad({ force: forceRentabilitySync });
    }
    const [meta, assets, trades, incomes, prices, portfolio, summary] = await Promise.all([
      getInvestMeta(),
      getInvestAssets(),
      getInvestTrades(),
      getInvestIncomes(),
      getInvestPrices(),
      getInvestPortfolio(),
      getInvestSummary(),
    ]);
    setInvestMeta(meta || { asset_classes: [], asset_sectors: [], income_types: [] });
    setInvestAssets(assets || []);
    setInvestTrades(trades || []);
    setInvestIncomes(incomes || []);
    setInvestPrices(prices || []);
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
    const amountAbs = Number(String(form.get("amount") || "0").replace(",", "."));
    const accountId = txAccountId ? Number(txAccountId) : NaN;
    const categoryIdRaw = String(txCategoryId || "");
    const categoryId = categoryIdRaw ? Number(categoryIdRaw) : null;
    const category = categories.find((c) => Number(c.id) === Number(categoryId));
    const method = String(txMethodEffective || "").trim();
    const futurePaymentMethod = txIsFutureTab ? String(txFuturePaymentMethod || "PIX").trim() : "";
    const notes = String(form.get("notes") || "").trim();
    const dateInput = String(form.get("date") || "");
    const dueDayInput = Number(String(form.get("due_day") || "0").replace(",", "."));
    const repeatMonthsInput = Number(String(form.get("repeat_months") || "1").replace(",", "."));
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
      formEl.reset();
      setTxCategoryId("");
      setTxMethod(txIsFutureTab ? "Futuro" : "PIX");
      setTxFuturePaymentMethod("PIX");
      setTxSourceAccountId("");
      setTxCardId("");
      if (out?.mode === "transfer") {
        setTxMsg("Transferência registrada (débito na origem e crédito no destino).");
      } else if (out?.mode === "credit_card_charge") {
        setTxMsg("Compra no crédito registrada. A despesa será lançada no pagamento da fatura.");
      } else if (out?.mode === "future_credit_schedule") {
        setTxMsg(
          `Compromisso no cartão agendado (${Number(out?.created || 0)}x): ${String(out?.first_date || "-")} até ${String(out?.last_date || "-")}.`
        );
      } else if (out?.mode === "future_schedule") {
        setTxMsg(
          `Despesa futura agendada (${Number(out?.created || 0)}x): ${String(out?.first_date || "-")} até ${String(out?.last_date || "-")}.`
        );
      } else if (method === "Futuro") {
        setTxMsg("Despesa futura agendada. Ela só impactará o caixa na data informada.");
      } else {
        setTxMsg("Lançamento salvo.");
      }
      await reloadTransactions();
      await reloadCardsData();
      if (canViewDashboard) {
        const dash = await getKpis();
        setKpis(dash);
      }
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setTxMsg(`Erro ao salvar lançamento: ${String(err.message || err)}`);
    }
  }

  async function onDeleteTransaction(id, scope = "single") {
    if (!canDeleteLancamentos) {
      setTxMsg("Sem permissão para excluir lançamentos.");
      return;
    }
    try {
      await deleteTransaction(id, { scope });
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
      amount: Math.abs(Number(tx?.amount_brl || 0)).toFixed(2),
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
    } catch (err) {
      setTxMsg(String(err.message || err));
    }
  }

  async function onConfirmPayCommitment() {
    if (!canAddLancamentos) {
      setTxMsg("Sem permissão para confirmar pagamentos de compromissos.");
      return;
    }
    if (!commitmentEdit?.id) return;
    const amountVal = Number(String(commitmentEdit.amount || "").replace(",", "."));
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
    try {
      await settleCommitmentTransaction(Number(commitmentEdit.id), {
        payment_date: paymentDate,
        account_id: accountId,
        amount: amountVal,
        notes: String(commitmentEdit.notes || "").trim() || null,
      });
      setCommitmentEdit(null);
      setTxMsg("Compromisso pago e convertido em lançamento real de caixa.");
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
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
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
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onDeleteInvestAsset(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir ativos.");
      return;
    }
    try {
      await deleteInvestAsset(Number(id));
      setInvestMsg("Ativo excluído.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
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
    const quantityRaw = Number(String(form.get("quantity") || "0").replace(",", "."));
    const priceRaw = Number(String(form.get("price") || "0").replace(",", "."));
    const appliedValue = Number(String(form.get("applied_value") || "0").replace(",", "."));
    const irIofPct = Number(String(form.get("ir_iof") || "0").replace(",", "."));
    const exchangeRate = Number(String(tradeExchangeRate || form.get("exchange_rate") || "0").replace(",", "."));
    const fees = Number(String(form.get("fees") || "0").replace(",", "."));
    const taxesRaw = Number(String(form.get("taxes") || "0").replace(",", "."));
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
  }

  async function onDeleteInvestTrade(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir operações.");
      return;
    }
    try {
      await deleteInvestTrade(Number(id));
      setInvestMsg("Operação excluída.");
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
    const amount = Number(String(form.get("amount") || "0").replace(",", "."));
    const note = String(form.get("note") || "").trim();
    if (!assetId || !date || !type || !Number.isFinite(amount) || amount <= 0) {
      setInvestMsg("Preencha ativo, data, tipo e valor do provento.");
      return;
    }
    try {
      await createInvestIncome({
        asset_id: assetId,
        date,
        type,
        amount,
        note: note || null,
      });
      formEl.reset();
      setInvestMsg("Provento salvo.");
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
  }

  async function onDeleteInvestIncome(id) {
    if (!canDeleteInvestimentos) {
      setInvestMsg("Sem permissão para excluir proventos.");
      return;
    }
    try {
      await deleteInvestIncome(Number(id));
      setInvestMsg("Provento excluído.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
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
    const price = Number(String(form.get("price") || "0").replace(",", "."));
    const source = String(form.get("source") || "manual").trim();
    if (!assetId || !date || !Number.isFinite(price) || price <= 0) {
      setInvestMsg("Preencha ativo, data e preço válido.");
      return;
    }
    try {
      await upsertInvestPrice({
        asset_id: assetId,
        date,
        price,
        source: source || "manual",
      });
      formEl.reset();
      setInvestMsg("Cotação salva.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onUpdateInvestManualQuote(e) {
    e.preventDefault();
    setInvestMsg("");
    if (!canEditInvestimentos) {
      setInvestMsg("Sem permissão para atualizar ativos.");
      return;
    }
    const assetId = Number(manualQuoteAssetId || 0);
    const value = Number(String(manualQuoteValue || "").replace(",", "."));
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
    try {
      await updateInvestManualAssetValue(assetId, {
        mode: manualQuoteMode,
        value,
        ref_date: refDate || null,
      });
      setManualQuoteValue("");
      setManualQuoteDate("");
      setInvestMsg("Atualização manual salva.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onUpdateAllInvestPrices() {
    if (!canAddInvestimentos) {
      setInvestMsg("Sem permissão para atualizar cotações.");
      return;
    }
    setInvestMsg("");
    setInvestPriceUpdateReport([]);
    setInvestPriceUpdateRunning(true);
    const timeout = Number(String(quoteTimeout || "25").replace(",", "."));
    const workers = Number(String(quoteWorkers || "4").replace(",", "."));
    if (!quoteGroups.length) {
      setInvestMsg("Selecione ao menos um grupo de cotação.");
      setInvestPriceUpdateRunning(false);
      return;
    }
    try {
      const out = await updateAllInvestPrices({
        timeout_s: Number.isFinite(timeout) ? timeout : 25,
        max_workers: Number.isFinite(workers) ? workers : 4,
        include_groups: quoteGroups,
      });
      const report = Array.isArray(out.report) ? out.report : [];
      const failed = report.filter((row) => !row?.ok).length;
      setInvestPriceUpdateReport(report);
      setInvestMsg(`Cotações salvas: ${out.saved}/${out.total}${failed ? ` | Falhas: ${failed}` : ""}`);
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
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
    try {
      await createAccount({ name, type, currency, show_on_dashboard: showOnDashboard });
      formEl.reset();
      setManageMsg("Conta salva.");
      await reloadAllData();
      await reloadCardsData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
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
    try {
      await updateAccount(Number(accEditId), {
        name: accEditName.trim(),
        type: accEditType,
        currency: (accEditCurrency || "BRL").toUpperCase(),
        show_on_dashboard: Boolean(accEditShowOnDashboard),
      });
      setManageMsg("Conta atualizada.");
      await reloadAllData();
      await reloadCardsData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
  }

  async function onDeleteAccount() {
    if (!canDeleteContas) {
      setManageMsg("Sem permissão para excluir contas.");
      return;
    }
    if (!accEditId) return;
    try {
      await deleteAccount(Number(accEditId));
      setManageMsg("Conta excluída.");
      await reloadAllData();
      await reloadCardsData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
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
    try {
      await createCategory({ name, kind });
      formEl.reset();
      setManageMsg("Categoria salva.");
      await reloadAllData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
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
    try {
      await updateCategory(Number(catEditId), { name: catEditName.trim(), kind: catEditKind });
      setManageMsg("Categoria atualizada.");
      await reloadAllData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
  }

  async function onDeleteCategory() {
    if (!canDeleteContas) {
      setManageMsg("Sem permissão para excluir categorias.");
      return;
    }
    if (!catEditId) return;
    try {
      await deleteCategory(Number(catEditId));
      setManageMsg("Categoria excluída.");
      await reloadAllData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
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
    const type = String(cardCreateType || "").trim();
    const accId = Number(cardCreateAccountId);
    const due = Number(String(cardCreateDueDay || "0"));
    const close = Number(String(cardCreateCloseDay || "0"));
    const isCredit = type === "Credito";
    if (
      !name ||
      !brand ||
      !model ||
      !type ||
      !Number.isFinite(accId) ||
      accId <= 0 ||
      (
        isCredit &&
        (!Number.isFinite(due) || due < 1 || due > 31 || !Number.isFinite(close) || close < 1 || close > 31 || close >= due)
      )
    ) {
      if (!Number.isFinite(accId) || accId <= 0) {
        setCardMsg("Selecione a conta banco vinculada ao cartão.");
        return;
      }
      setCardMsg(
        isCredit
          ? "Preencha nome, tipo, conta banco vinculada, fechamento e vencimento."
          : "Preencha nome, tipo e conta banco vinculada ao cartão."
      );
      return;
    }
    try {
      await createCard({
        name,
        brand,
        model,
        card_type: type,
        card_account_id: accId,
        source_account_id: accId,
        due_day: isCredit ? due : null,
        close_day: isCredit ? close : null,
      });
      setCardMsg("Cartão cadastrado.");
      setCardCreateName("");
      setCardCreateBrand("");
      setCardCreateModel("");
      setCardCreateType("");
      setCardCreateAccountId("");
      setCardCreateDueDay("");
      setCardCreateCloseDay("");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
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
    const type = String(cardType || "").trim();
    const accId = Number(cardAccountId);
    const due = Number(String(cardDueDay || "0"));
    const close = Number(String(cardCloseDay || "0"));
    const isCredit = type === "Credito";
    if (
      !Number.isFinite(id) ||
      id <= 0 ||
      !name ||
      !brand ||
      !model ||
      !type ||
      !Number.isFinite(accId) ||
      accId <= 0 ||
      (
        isCredit &&
        (!Number.isFinite(due) || due < 1 || due > 31 || !Number.isFinite(close) || close < 1 || close > 31 || close >= due)
      )
    ) {
      if (!Number.isFinite(accId) || accId <= 0) {
        setCardMsg("Selecione a conta banco vinculada ao cartão.");
        return;
      }
      setCardMsg("Selecione e preencha os dados do cartão.");
      return;
    }
    try {
      await updateCard(id, {
        name,
        brand,
        model,
        card_type: type,
        card_account_id: accId,
        source_account_id: accId,
        due_day: isCredit ? due : null,
        close_day: isCredit ? close : null,
      });
      setCardMsg("Cartão atualizado.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
  }

  async function onDeleteCard() {
    setCardMsg("");
    if (!canDeleteContas) {
      setCardMsg("Sem permissão para excluir cartões.");
      return;
    }
    const id = Number(cardEditId);
    if (!Number.isFinite(id)) return;
    try {
      await deleteCard(id);
      setCardMsg("Cartão excluído.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
  }

  function onSelectCardEdit(id) {
    setCardEditId(id);
    const cur = (cards || []).find((c) => String(c.id) === String(id));
    if (!cur) {
      setCardName("");
      setCardBrand("");
      setCardModel("");
      setCardType("");
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
    try {
      await payCardInvoice(invoiceId, {
        payment_date: paymentDate,
        source_account_id: sourceAccountId ? Number(sourceAccountId) : null,
      });
      setCardMsg("Fatura paga.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
      await reloadInvestData();
      await reloadTransactions();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
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

  async function onApplyDashboardFilters(e) {
    e.preventDefault();
    await reloadDashboard({
      date_from: dashDateFrom,
      date_to: dashDateTo,
      account: dashAccount,
      view: dashView,
    });
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
    try {
      const out = await importTransactionsCsv(txCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
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
    try {
      const out = await importTransactionsCsv(txCsvFile, false);
      setImportPreview([]);
      setImportMsg(`Importação concluída: ${out.inserted}/${out.rows} lançamentos.`);
      await reloadAllData();
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
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
    try {
      const out = await importAssetsCsv(assetCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
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
    try {
      const out = await importAssetsCsv(assetCsvFile, false);
      setImportPreview([]);
      const errInfo = out.errors && out.errors.length ? ` Erros: ${out.errors.length}.` : "";
      setImportMsg(`Importação de ativos: inseridos ${out.inserted}, ignorados ${out.skipped}.${errInfo}`);
      await reloadInvestData();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
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
    try {
      const out = await importTradesCsv(tradeCsvFile, true);
      setImportPreview(out.preview || []);
      setImportMsg(`Prévia pronta: ${out.rows} linha(s) lidas.`);
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
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
    try {
      const out = await importTradesCsv(tradeCsvFile, false);
      setImportPreview([]);
      const errInfo = out.errors && out.errors.length ? ` Erros: ${out.errors.length}.` : "";
      setImportMsg(`Importação de operações: inseridas ${out.inserted}, ignoradas ${out.skipped}.${errInfo}`);
      await reloadInvestData();
      await reloadTransactions();
      await reloadDashboard();
    } catch (err) {
      setImportMsg(String(err.message || err));
    }
  }

  if (loading) return <div className="center">Carregando...</div>;

  if (!user) {
    return (
      <div className="auth-wrap">
        <form className="auth-card" onSubmit={onLogin}>
          <h1>Controle Financeiro</h1>
          <p>Login via FastAPI</p>
          <input name="email" type="email" placeholder="E-mail" required />
          <input name="password" type="password" placeholder="Senha" required />
          <button type="submit">Entrar</button>
          {authError ? <div className="error">{authError}</div> : null}
        </form>
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
              <img src={icUsuario} alt="" className="user-avatar-icon" />
              <span className="user-trigger-name">{user.display_name || user.email}</span>
            </button>
            {userMenuOpen ? (
              <div className="user-popover">
                <button
                  className="user-popover-item"
                  onClick={() => {
                    setUserMenuOpen(false);
                    setPage(visiblePages.includes("Dashboard") ? "Dashboard" : (visiblePages[0] || "Dashboard"));
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
                      setPage("Gerenciador");
                    }}
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 17.2V20h2.8l8.3-8.3-2.8-2.8L4 17.2z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                      <path d="M13.7 7.4l2.8 2.8 1.7-1.7a2 2 0 0 0 0-2.8l0 0a2 2 0 0 0-2.8 0l-1.7 1.7z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                    </svg>
                    Editar
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
                  <span>Saldo</span>
                </h3>
                <strong>{brl.format(Number(currentKpi.saldo || 0))}</strong>
              </article>
            </section>

            <section className="dash-grid">
              <article className="card dash-hero-card">
                <div className="dash-hero-head">
                  <h3>Patrimônio mensal</h3>
                  <span className={`dash-delta ${trendDelta >= 0 ? "up" : "down"}`}>
                    {trendDelta >= 0 ? "↑" : "↓"} {Math.abs(trendPct).toFixed(1)}%
                  </span>
                </div>
                <strong className="dash-hero-value">{brl.format(trendEnd)}</strong>
                <p className={`dash-hero-sub ${trendDelta >= 0 ? "up" : "down"}`}>
                  {trendDelta >= 0 ? "▲" : "▼"} {brl.format(Math.abs(trendDelta))} no período
                </p>
                <div className="dash-spark-wrap">
                  {sparkPoints ? (
                    <svg viewBox="0 0 680 240" preserveAspectRatio="none" className="dash-spark">
                      <polyline fill="none" stroke="url(#sparkStroke)" strokeWidth="5" points={sparkPoints} />
                      <defs>
                        <linearGradient id="sparkStroke" x1="0" x2="1" y1="0" y2="0">
                          <stop offset="0%" stopColor="#68d3ff" />
                          <stop offset="100%" stopColor="#9ff7be" />
                        </linearGradient>
                      </defs>
                    </svg>
                  ) : (
                    <div className="dash-empty">Sem dados no período</div>
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
                    {activeCreditCard ? (
                      <article
                        className="wallet-card wallet-card-front"
                        key={activeCreditCard.id}
                        title={`${activeCreditCard.name} (${activeCreditCard.model || "Black"})`}
                      >
                        <img
                          src={getCardBackground(activeCreditCard.model || "Black")}
                          alt=""
                          className="wallet-bg"
                        />
                        <div className="wallet-overlay" />
                        <div className="wallet-content">
                          <div className="wallet-name">{activeCreditCard.name}</div>
                          <div className="wallet-brand-line">
                            <img
                              src={getCardLogo(activeCreditCard.brand || "Visa")}
                              alt=""
                              className="wallet-brand-icon"
                            />
                          </div>
                        </div>
                      </article>
                    ) : null}
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
                <div className="dash-invest-layout">
                  <div className="dash-donut" style={donutStyle}>
                    <div className="dash-donut-center">
                      <strong>{brl.format(Number(investmentTotal || 0))}</strong>
                    </div>
                  </div>
                  <ul className="dash-legend">
                    {investmentByClass.map((row, idx) => (
                      <li key={row.name}>
                        <span className="dot" style={{ background: DONUT_COLORS[idx % DONUT_COLORS.length] }} />
                        <span>{row.name}</span>
                        <strong>{brl.format(Number(row.value || 0))}</strong>
                        <em>{pct(row.value, investmentTotal).toFixed(0)}%</em>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>

              <article className="card dash-list-card dash-expenses-card">
                <h3>Compromissos do período</h3>
                <ul className="dash-list">
                  <li>
                    <span>A vencer</span>
                    <strong>{brl.format(commitmentsAging.aVencer)}</strong>
                  </li>
                  <li>
                    <span>Vencidos</span>
                    <strong>{brl.format(commitmentsAging.vencidos)}</strong>
                  </li>
                </ul>
                <div className="dash-list-total">
                  <span>Total</span>
                  <strong>{brl.format(commitmentsAging.aVencer + commitmentsAging.vencidos)}</strong>
                </div>
              </article>
            </section>

            <Suspense fallback={<section className="card"><p>Carregando gráficos...</p></section>}>
              <DashboardCharts monthly={dashMonthly} expenses={dashExpenses} />
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
              <div style={{ display: "grid", gap: 10, maxWidth: 360, marginBottom: 12 }}>
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
                      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <input type="checkbox" name="show_on_dashboard" />
                        Fixar no Dashboard (saldo 0)
                      </label>
                      <button type="submit">Salvar conta</button>
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
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox"
                        checked={Boolean(accEditShowOnDashboard)}
                        disabled={!canEditContas}
                        onChange={(e) => setAccEditShowOnDashboard(e.target.checked)}
                      />
                      Fixar no Dashboard (saldo 0)
                    </label>
                    <button onClick={onUpdateAccount} disabled={!canEditContas}>Atualizar conta</button>
                    <button className="danger" onClick={onDeleteAccount} disabled={!canDeleteContas}>Excluir conta</button>
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
                      <button type="submit">Salvar categoria</button>
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
                    <button onClick={onUpdateCategory} disabled={!canEditContas}>Atualizar categoria</button>
                    <button className="danger" onClick={onDeleteCategory} disabled={!canDeleteContas}>Excluir categoria</button>
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
                      <select value={cardCreateType} onChange={(e) => setCardCreateType(e.target.value)}>
                        <option value="" disabled>Selecione o tipo do cartão</option>
                        <option value="Credito">Credito</option>
                        <option value="Debito">Debito</option>
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
                      {!hasCreateCardTypeSelected ? (
                        <input type="text" value="Selecione primeiro o tipo do cartão" disabled />
                      ) : isCreateCreditCardType ? (
                        <>
                          <input
                            type="number"
                            min="1"
                            max="31"
                            placeholder="Dia de fechamento (1-31)"
                            value={cardCreateCloseDay}
                            onChange={(e) => setCardCreateCloseDay(e.target.value)}
                          />
                          <input
                            type="number"
                            min="1"
                            max="31"
                            placeholder="Dia do vencimento (1-31)"
                            value={cardCreateDueDay}
                            onChange={(e) => setCardCreateDueDay(e.target.value)}
                          />
                          <small style={{ gridColumn: "1 / -1", color: "#5f6f8f" }}>
                            Dica: informe o fechamento no máximo 5 dias antes do vencimento da fatura.
                          </small>
                        </>
                      ) : (
                        <input type="text" value="Débito imediato na conta banco" disabled />
                      )}
                      <button type="button" onClick={onCreateCard}>Cadastrar cartão</button>
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
                    <select value={cardType} onChange={(e) => setCardType(e.target.value)} disabled={!canEditContas}>
                      <option value="" disabled>Selecione o tipo do cartão</option>
                      <option value="Credito">Credito</option>
                      <option value="Debito">Debito</option>
                    </select>
                    <select value={cardAccountId} onChange={(e) => setCardAccountId(e.target.value)} disabled={!canEditContas}>
                      <option value="" disabled>Selecione a conta banco vinculada</option>
                      {bankAccountsOnly.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    {!hasEditCardTypeSelected ? (
                      <input type="text" value="Selecione primeiro o tipo do cartão" disabled />
                    ) : isEditCreditCardType ? (
                      <>
                        <input
                          type="number"
                          min="1"
                          max="31"
                          placeholder="Dia de fechamento (1-31)"
                          value={cardCloseDay}
                          disabled={!canEditContas}
                          onChange={(e) => setCardCloseDay(e.target.value)}
                        />
                        <input
                          type="number"
                          min="1"
                          max="31"
                          placeholder="Dia do vencimento (1-31)"
                          value={cardDueDay}
                          disabled={!canEditContas}
                          onChange={(e) => setCardDueDay(e.target.value)}
                        />
                        <small style={{ gridColumn: "1 / -1", color: "#5f6f8f" }}>
                          Dica: informe o fechamento no máximo 5 dias antes do vencimento da fatura.
                        </small>
                      </>
                    ) : (
                      <input type="text" value="Débito imediato na conta banco" disabled />
                    )}
                    <button type="button" onClick={onUpdateCard} disabled={!canEditContas}>Atualizar cartão</button>
                    <button type="button" className="danger" onClick={onDeleteCard} disabled={!canDeleteContas}>Excluir cartão</button>
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
                    <input
                      type="password"
                      placeholder="Senha inicial (obrigatória se e-mail novo)"
                      value={workspaceInvitePassword}
                      onChange={(e) => setWorkspaceInvitePassword(e.target.value)}
                      disabled={!canManageWorkspaceUsers}
                    />
                    <button type="submit" disabled={!canManageWorkspaceUsers}>
                      Adicionar convidado
                    </button>
                  </form>
                  <p className="workspace-helper-text">
                    Se o e-mail já existir, a senha não é necessária. Se não existir, informando a senha o usuário convidado é criado automaticamente como `USER` e vinculado como `GUEST` neste workspace.
                  </p>
                  {workspaceManageMsg ? <p className="status-msg">{workspaceManageMsg}</p> : null}
                </section>

                <section className="card">
                  <h3>Membros e permissões</h3>
                  {workspaceMembersLoading ? <p>Carregando membros...</p> : null}
                  <div className="tx-table-wrap">
                    <table className="tx-table">
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
                                    >
                                      Remover
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
                                        >
                                          Salvar permissões
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
                        <input
                          type="password"
                          placeholder="Senha inicial (obrigatória se e-mail novo)"
                          value={adminOwnerPassword}
                          onChange={(e) => setAdminOwnerPassword(e.target.value)}
                        />
                        <button type="submit">Criar workspace</button>
                      </form>
                      <p className="workspace-helper-text">
                        Se o e-mail do owner já existir, a senha não é necessária. Se não existir, com a senha inicial o usuário é criado automaticamente como `USER` e já vira `OWNER` do novo workspace.
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
              <div className="invest-tabs" style={{ marginBottom: 12 }}>
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
                  <div className="transfer-hint" style={{ marginBottom: 10 }}>
                    <strong className="transfer-badge">Compromissos</strong>
                    <span>
                      Use a aba Compromissos para contas a vencer: se hoje ainda não passou do dia informado, a 1ª
                      parcela entra neste mês; depois replica pelos próximos meses.
                    </span>
                  </div>
                  <div className="transfer-hint" style={{ marginBottom: 12 }}>
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
                        type="number"
                        min="1"
                        max="31"
                        step="1"
                        placeholder="Dia de vencimento (1-31)"
                        required
                      />
                    ) : null}
                    <input
                      name="repeat_months"
                      type="number"
                      min="1"
                      max="120"
                      step="1"
                      placeholder={txFuturePaymentMethod === "Credito" ? "Parcelamento (qtd. de parcelas)" : "Meses para replicar"}
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
                <input name="amount" type="number" step="0.01" min="0.01" placeholder="Valor" required />
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
                <button type="submit">Salvar lançamento</button>
              </form>
                ) : (
                  <p>Sem permissão para incluir lançamentos.</p>
                )
              ) : null}
              {txView !== "competencia" && txMsg ? <p>{txMsg}</p> : null}
            </section>

            <section className="card">
              <h3>Lançamentos recentes</h3>
              <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(2, minmax(220px, 360px))", marginBottom: 12 }}>
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
                        <td>{t.category || "-"}</td>
                        <td>{t.charge_status || "-"}</td>
                        <td>
                          {commitmentEdit?.id === t.id ? (
                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              value={String(commitmentEdit.amount || "")}
                              onChange={(e) =>
                                setCommitmentEdit((prev) => (prev ? { ...prev, amount: e.target.value } : prev))
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
                              <button type="button" className="danger" onClick={() => onDeleteCreditCommitment(t)}>Excluir</button>
                            ) : (
                              "-"
                            )
                          ) : commitmentEdit?.id === t.id ? (
                            <>
                              {canAddLancamentos ? (
                                <button type="button" className="tx-action-primary" onClick={onConfirmPayCommitment}>Confirmar</button>
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
                                  Excluir
                                </button>
                              ) : null}
                              {!canAddLancamentos && !canDeleteLancamentos ? "-" : null}
                            </>
                          ) : (
                            canDeleteLancamentos ? (
                              <button type="button" onClick={() => onDeleteTransaction(t.id)}>Excluir</button>
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
                <button onClick={onPreviewTransactionsCsv} disabled={!canAddRelatorios}>Prévia lançamentos</button>
                <button onClick={onImportTransactionsCsv} disabled={!canAddRelatorios}>Importar lançamentos</button>
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
                <button onClick={onPreviewAssetsCsv} disabled={!canAddRelatorios}>Prévia ativos</button>
                <button onClick={onImportAssetsCsv} disabled={!canAddRelatorios}>Importar ativos</button>
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
                <button onClick={onPreviewTradesCsv} disabled={!canAddRelatorios}>Prévia operações</button>
                <button onClick={onImportTradesCsv} disabled={!canAddRelatorios}>Importar operações</button>
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
                  <div className="tx-form" style={{ gridTemplateColumns: "repeat(3, minmax(220px, 360px))" }}>
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
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={investDivergenceThreshold}
                      onChange={(e) => setInvestDivergenceThreshold(e.target.value)}
                      placeholder="Limiar de divergência (%)"
                    />
                    <button type="button" onClick={onLoadInvestDivergenceReport} disabled={investDivergenceRunning}>
                      {investDivergenceRunning ? "Gerando relatório..." : "Carregar divergências"}
                    </button>
                  </div>
                  {investDivergenceMsg ? <p>{investDivergenceMsg}</p> : null}
                </section>
                <section className="cards">
                  <article className="card">
                    <h3>Ativos</h3>
                    <strong>{Number(investSummaryViewData.assets_count || 0)}</strong>
                  </article>
                  <article className="card">
                    <h3>Total investido</h3>
                    <strong>{brl.format(Number(investSummaryViewData.total_invested || 0))}</strong>
                  </article>
                  <article className="card">
                    <h3>Saldo na corretora</h3>
                    <strong>{brl.format(Number(investSummaryViewData.broker_balance || 0))}</strong>
                  </article>
                  <article className="card">
                    <h3>Valor de mercado</h3>
                    <strong>{brl.format(Number(investSummaryViewData.total_market || 0))}</strong>
                  </article>
                  <article className="card">
                    <h3>Retorno total</h3>
                    <strong>{brl.format(Number(investSummaryViewData.total_return || 0))}</strong>
                    <p>{Number(investSummaryViewData.total_return_pct || 0).toFixed(2)}%</p>
                  </article>
                  <article className="card">
                    <h3>P&L não realizado</h3>
                    <strong>{brl.format(Number(investSummaryViewData.total_unrealized || 0))}</strong>
                  </article>
                </section>
                <section className="card">
                  <h3>Divergência de rentabilidade</h3>
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
                        type="number"
                        step="0.00000001"
                        value={assetCreateFixedRate}
                        onChange={(e) => setAssetCreateFixedRate(e.target.value)}
                        placeholder="Taxa anual (%)"
                      />
                    ) : null}
                    {assetCreateIsFixedIncome &&
                    (assetCreateRentabilityType === "PCT_CDI" || assetCreateRentabilityType === "PCT_SELIC") ? (
                      <input
                        type="number"
                        step="0.00000001"
                        value={assetCreateIndexPct}
                        onChange={(e) => setAssetCreateIndexPct(e.target.value)}
                        placeholder="Percentual do índice (%)"
                      />
                    ) : null}
                    {assetCreateIsFixedIncome &&
                    ["CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD"].includes(assetCreateRentabilityType) ? (
                      <input
                        type="number"
                        step="0.00000001"
                        value={assetCreateSpreadRate}
                        onChange={(e) => setAssetCreateSpreadRate(e.target.value)}
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
                    <button type="submit">Salvar ativo</button>
                  </form>
                </section>

                <section className="card">
                  <h3>Editar ativo</h3>
                  <div className="mgr-grid">
                    <select
                      value={assetEditId}
                      onChange={(e) => {
                        const id = e.target.value;
                        setAssetEditId(id);
                        const cur = investAssets.find((a) => String(a.id) === id);
                        if (cur) {
                          setAssetEditSymbol(cur.symbol || "");
                          setAssetEditName(cur.name || "");
                          setAssetEditClass(cur.asset_class || "");
                          setAssetEditSector(cur.sector || "Não definido");
                          setAssetEditCurrency((cur.currency || "BRL").toUpperCase());
                          setAssetEditBrokerId(cur.broker_account_id ? String(cur.broker_account_id) : "");
                          if (isFixedIncomeClass(cur.asset_class || "")) {
                            setAssetEditRentabilityType(String(cur.rentability_type || "MANUAL").toUpperCase());
                            setAssetEditIndexPct(cur.index_pct == null ? "" : String(cur.index_pct));
                            setAssetEditSpreadRate(cur.spread_rate == null ? "" : String(cur.spread_rate));
                            setAssetEditFixedRate(cur.fixed_rate == null ? "" : String(cur.fixed_rate));
                          } else {
                            setAssetEditRentabilityType("");
                            setAssetEditIndexPct("");
                            setAssetEditSpreadRate("");
                            setAssetEditFixedRate("");
                          }
                        }
                      }}
                    >
                      {investAssets.map((a) => (
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
                        type="number"
                        step="0.00000001"
                        value={assetEditFixedRate}
                        onChange={(e) => setAssetEditFixedRate(e.target.value)}
                        placeholder="Taxa anual (%)"
                      />
                    ) : null}
                    {assetEditIsFixedIncome &&
                    (assetEditRentabilityType === "PCT_CDI" || assetEditRentabilityType === "PCT_SELIC") ? (
                      <input
                        type="number"
                        step="0.00000001"
                        value={assetEditIndexPct}
                        onChange={(e) => setAssetEditIndexPct(e.target.value)}
                        placeholder="Percentual do índice (%)"
                      />
                    ) : null}
                    {assetEditIsFixedIncome &&
                    ["CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD"].includes(assetEditRentabilityType) ? (
                      <input
                        type="number"
                        step="0.00000001"
                        value={assetEditSpreadRate}
                        onChange={(e) => setAssetEditSpreadRate(e.target.value)}
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
                    <button onClick={onUpdateInvestAsset}>Atualizar ativo</button>
                  </div>
                </section>

                <section className="card">
                  <h3>Ativos cadastrados</h3>
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
                        {investAssets.map((a) => (
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
                              <button onClick={() => onDeleteInvestAsset(a.id)}>Excluir</button>
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
                          type="number"
                          step={tradeQuantityStep}
                          min={tradeQuantityMin}
                          placeholder={tradeQuantityPlaceholder}
                          required
                        />
                        <input
                          name="price"
                          type="number"
                          step="0.0001"
                          min="0.0001"
                          placeholder={tradeAssetIsUsStock ? "Preço (USD)" : "Preço"}
                          required
                        />
                      </>
                    ) : null}
                    {tradeShowAppliedValue ? (
                      <>
                        <input
                          name="applied_value"
                          type="number"
                          step="0.01"
                          min="0.01"
                          placeholder={tradeFixedIncomeIsSell ? "Valor bruto do resgate" : "Valor da aplicação"}
                          required
                        />
                      </>
                    ) : null}
                    {tradeShowIrIof ? (
                      <input
                        name="ir_iof"
                        type="number"
                        step="0.0001"
                        min="0"
                        max="100"
                        placeholder="IR/IOF do resgate (%)"
                      />
                    ) : null}
                    {tradeAssetIsUsStock ? (
                      <input
                        name="exchange_rate"
                        type="number"
                        step="0.0001"
                        min="0.0001"
                        placeholder="Cotação USD/BRL"
                        value={tradeExchangeRate}
                        onChange={(e) => setTradeExchangeRate(e.target.value)}
                        required
                      />
                    ) : null}
                    <input
                      name="fees"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder={
                        tradeAssetIsFixedIncome
                          ? tradeFixedIncomeIsSell
                            ? "Taxas do resgate (opcional)"
                            : "Taxas da aplicação (opcional)"
                          : "Taxas (opcional, padrão 0)"
                      }
                      aria-label="Taxas"
                    />
                    {tradeShowGenericTaxes ? (
                      <input
                        name="taxes"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder={
                          tradeAssetIsFixedIncome
                            ? "Impostos do resgate (opcional)"
                            : "Impostos (opcional, padrão 0)"
                        }
                        aria-label="Impostos"
                      />
                    ) : null}
                    <input name="note" type="text" placeholder="Obs (opcional)" />
                    <button type="submit">Salvar operação</button>
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
                        {investTrades.map((t) => (
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
                              <button type="button" onClick={() => onDeleteInvestTrade(t.id)}>Excluir</button>
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
                    <select name="asset_id" defaultValue="">
                      <option value="" disabled>Ativo</option>
                      {investAssets.map((a) => (
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
                    <input name="amount" type="number" step="0.01" min="0.01" placeholder="Valor" required />
                    <input name="note" type="text" placeholder="Obs (opcional)" />
                    <button type="submit">Salvar provento</button>
                  </form>
                </section>

                <section className="card">
                  <h3>Proventos recentes</h3>
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Data</th>
                          <th>Ativo</th>
                          <th>Tipo</th>
                          <th>Valor</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investIncomes.map((i) => (
                          <tr key={i.id}>
                            <td>{i.id}</td>
                            <td>{i.date}</td>
                            <td>{i.symbol}</td>
                            <td>{i.type}</td>
                            <td>{Number(i.amount || 0).toFixed(2)}</td>
                            <td>
                              <button onClick={() => onDeleteInvestIncome(i.id)}>Excluir</button>
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
                <div className="mgr-grid">
                  <input
                    type="number"
                    step="1"
                    min="3"
                    value={quoteTimeout}
                    onChange={(e) => setQuoteTimeout(e.target.value)}
                    placeholder="Timeout (s)"
                  />
                  <input
                    type="number"
                    step="1"
                    min="1"
                    value={quoteWorkers}
                    onChange={(e) => setQuoteWorkers(e.target.value)}
                    placeholder="Paralelismo"
                  />
                  <select
                    multiple
                    value={quoteGroups}
                    onChange={(e) => {
                      const vals = Array.from(e.target.selectedOptions || []).map((o) => o.value);
                      setQuoteGroups(vals);
                    }}
                    title="Selecione os grupos para atualização"
                  >
                    {QUOTE_GROUP_OPTIONS.map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                  <button onClick={onUpdateAllInvestPrices} disabled={investPriceUpdateRunning}>
                    {investPriceUpdateRunning ? "Atualizando..." : "Atualizar cotações automáticas"}
                  </button>
                </div>
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
                <form className="tx-form" onSubmit={onUpsertInvestPrice}>
                  <select name="asset_id" defaultValue="">
                    <option value="" disabled>Ativo</option>
                    {investAssets.map((a) => (
                      <option key={a.id} value={a.id}>{a.symbol}</option>
                    ))}
                  </select>
                  <input name="date" type="date" required />
                  <input
                    name="price"
                    type="number"
                    step="0.0001"
                    min="0.0001"
                    placeholder="Preço unitário"
                    title="Informe o preço por unidade do ativo, não o valor total da posição."
                    required
                  />
                  <input name="source" type="text" placeholder="Fonte" defaultValue="manual" />
                  <button type="submit">Salvar cotação manual</button>
                </form>
                <p className="tx-helper">
                  Para ações, BDRs, FIIs, stocks e cripto, a cotação manual deve ser o preço por unidade do ativo. O valor da posição é calculado pela quantidade em carteira.
                </p>
                <section className="card quote-manual-fixed-card">
                  <h3>Atualização manual de renda fixa e fundos</h3>
                  <form className="tx-form" onSubmit={onUpdateInvestManualQuote}>
                    <select value={manualQuoteAssetId} onChange={(e) => setManualQuoteAssetId(e.target.value)}>
                      <option value="" disabled>Ativo manual</option>
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
                      type="number"
                      step="0.00000001"
                      value={manualQuoteValue}
                      onChange={(e) => setManualQuoteValue(e.target.value)}
                      placeholder={
                        manualQuoteMode === "rentability"
                          ? "Rentabilidade atual (%)"
                          : "Valor atual"
                      }
                    />
                    <button type="submit">Salvar atualização manual</button>
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
                          <td>{p.date}</td>
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

            <section className="card">
              <h3>Carteira (consolidado)</h3>
              <div className="tx-table-wrap">
                <table className="tx-table">
                  <thead>
                    <tr>
                      <th>Ativo</th>
                      <th>Classe</th>
                      <th>Qtd</th>
                      <th>Custo</th>
                      <th>Mercado Bruto</th>
                      <th>Líquido Estimado</th>
                      <th>Origem</th>
                      <th>Data Valor</th>
                      <th>P&L Não Realizado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {investPortfolioPositionsVisible.map((p) => (
                      <tr key={`${p.asset_id}-${p.symbol}`}>
                        <td>{p.symbol}</td>
                        <td>{p.asset_class}</td>
                        <td>{Number(p.qty || 0).toFixed(8)}</td>
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
              {investMsg ? <p>{investMsg}</p> : null}
            </section>
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
                <button type="button" onClick={confirmPayInvoiceModal}>Confirmar pagamento</button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
