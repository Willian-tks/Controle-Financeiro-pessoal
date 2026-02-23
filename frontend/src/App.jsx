import { Suspense, lazy, useEffect, useMemo, useRef, useState } from "react";
import brandLogo from "./icons/domus.png";
import icDashboard from "./icons/dashboard.png";
import icContas from "./icons/contas.png";
import icLancamentos from "./icons/lancamentos.png";
import icInvestimento from "./icons/investimento.png";
import icGerenciador from "./icons/gerenciador.png";
import icImportarCsv from "./icons/importar-CSV.png";
import icUsuario from "./icons/usuario.png";
import bankInterLogo from "./banks/banco-inter-logo.svg";
import bankBradescoLogo from "./banks/bradesco-logo.svg";
import bankItauLogo from "./banks/itau-logo.svg";
import bankNubankLogo from "./banks/nubank-logo.svg";
import bankSantanderLogo from "./banks/santander-logo.svg";
import cardVisaLogo from "./cards/visa-17.svg";
import cardMasterLogo from "./cards/mastercard-18.svg";
import cardVisaBg from "./cards/Cartao_visa.png";
import cardMasterBg from "./cards/Cartao_mastercard.svg";
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
  deleteInvestAsset,
  deleteInvestIncome,
  deleteInvestTrade,
  deleteTransaction,
  getAccounts,
  getCardInvoices,
  getCards,
  getCategories,
  getDashboardAccountBalance,
  getDashboardExpenses,
  getDashboardKpis,
  getDashboardMonthly,
  getInvestAssets,
  getInvestIncomes,
  getInvestMeta,
  getInvestPortfolio,
  getInvestPrices,
  getInvestSummary,
  getInvestTrades,
  getKpis,
  getMe,
  getTransactions,
  importAssetsCsv,
  importTradesCsv,
  importTransactionsCsv,
  login,
  payCardInvoice,
  setToken,
  updateAllInvestPrices,
  updateInvestAsset,
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

const PAGE_SUBTITLES = {
  Gerenciador: "Cadastros e manutenção de contas/categorias",
  Contas: "Visão rápida das contas cadastradas",
  "Lançamentos": "Registro e histórico das movimentações",
  Dashboard: "KPIs, gráficos e saldos por conta",
  "Importar CSV": "Prévia e importação de dados em lote",
  Investimentos: "Ativos, operações, proventos, cotações e carteira",
};

const INVEST_TABS = ["Resumo", "Ativos", "Operações", "Proventos", "Cotações"];
const DONUT_COLORS = ["#f4c84b", "#4e7ff3", "#73d39f", "#ef6f5c", "#9a7df9"];
const PAGE_ICONS = {
  Dashboard: icDashboard,
  Contas: icContas,
  "Lançamentos": icLancamentos,
  Investimentos: icInvestimento,
  Gerenciador: icGerenciador,
  "Importar CSV": icImportarCsv,
};

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

function getCardBackground(brand) {
  const n = normalizeText(brand);
  if (n.includes("master")) return cardMasterBg;
  return cardVisaBg;
}

function getCardBgClass(brand) {
  const n = normalizeText(brand);
  if (n.includes("master")) return "brand-master";
  return "brand-visa";
}

export default function App() {
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
  const [dashAccountBalance, setDashAccountBalance] = useState([]);
  const [dashDateFrom, setDashDateFrom] = useState("");
  const [dashDateTo, setDashDateTo] = useState("");
  const [dashAccount, setDashAccount] = useState("");
  const [dashMsg, setDashMsg] = useState("");
  const [txMsg, setTxMsg] = useState("");
  const [txAccountId, setTxAccountId] = useState("");
  const [txCategoryId, setTxCategoryId] = useState("");
  const [txKind, setTxKind] = useState("Receita");
  const [txMethod, setTxMethod] = useState("PIX");
  const [txSourceAccountId, setTxSourceAccountId] = useState("");
  const [txCardId, setTxCardId] = useState("");
  const [cardMsg, setCardMsg] = useState("");
  const [cardName, setCardName] = useState("");
  const [cardBrand, setCardBrand] = useState("Visa");
  const [cardType, setCardType] = useState("Credito");
  const [cardAccountId, setCardAccountId] = useState("");
  const [cardSourceAccountId, setCardSourceAccountId] = useState("");
  const [cardDueDay, setCardDueDay] = useState("10");
  const [cardEditId, setCardEditId] = useState("");
  const [importMsg, setImportMsg] = useState("");
  const [importPreview, setImportPreview] = useState([]);
  const [txCsvFile, setTxCsvFile] = useState(null);
  const [assetCsvFile, setAssetCsvFile] = useState(null);
  const [tradeCsvFile, setTradeCsvFile] = useState(null);
  const [investMsg, setInvestMsg] = useState("");
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
  const [assetEditId, setAssetEditId] = useState("");
  const [assetEditSymbol, setAssetEditSymbol] = useState("");
  const [assetEditName, setAssetEditName] = useState("");
  const [assetEditClass, setAssetEditClass] = useState("");
  const [assetEditSector, setAssetEditSector] = useState("Não definido");
  const [assetEditCurrency, setAssetEditCurrency] = useState("BRL");
  const [assetEditBrokerId, setAssetEditBrokerId] = useState("");
  const [investTab, setInvestTab] = useState("Resumo");
  const [manageMsg, setManageMsg] = useState("");
  const [accEditId, setAccEditId] = useState("");
  const [accEditName, setAccEditName] = useState("");
  const [accEditType, setAccEditType] = useState("Banco");
  const [catEditId, setCatEditId] = useState("");
  const [catEditName, setCatEditName] = useState("");
  const [catEditKind, setCatEditKind] = useState("Despesa");
  const [loading, setLoading] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [walletCardIndex, setWalletCardIndex] = useState(0);
  const userMenuRef = useRef(null);

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
        await reloadAllData();
        await reloadCardsData();
        await reloadDashboard({
          date_from: "",
          date_to: "",
          account: "",
        });
        await reloadInvestData();
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
      return;
    }
    const cur = accounts.find((a) => String(a.id) === String(accEditId)) || accounts[0];
    setAccEditId(String(cur.id));
    setAccEditName(cur.name);
    setAccEditType(cur.type);
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
    const sourceAccounts = bankAccounts;

    if (!bankAccounts.length) {
      setCardAccountId("");
    } else if (!cardAccountId || !bankAccounts.some((a) => String(a.id) === String(cardAccountId))) {
      setCardAccountId(String(bankAccounts[0].id));
    }

    if (!sourceAccounts.length) {
      setCardSourceAccountId("");
    } else if (!cardSourceAccountId || !sourceAccounts.some((a) => String(a.id) === String(cardSourceAccountId))) {
      setCardSourceAccountId(String(sourceAccounts[0].id));
    }
  }, [accounts, cardAccountId, cardSourceAccountId, cardType]);

  useEffect(() => {
    if (!cards.length) {
      setCardEditId("");
      setCardName("");
      setCardBrand("Visa");
      setCardType("Credito");
      setCardDueDay("10");
      return;
    }
    const cur = cards.find((c) => String(c.id) === String(cardEditId)) || cards[0];
    setCardEditId(String(cur.id));
    setCardName(String(cur.name || ""));
    setCardBrand(String(cur.brand || "Visa"));
    setCardType(String(cur.card_type || "Credito"));
    setCardAccountId(String(cur.card_account_id || ""));
    setCardSourceAccountId(String(cur.source_account_id || ""));
    setCardDueDay(String(cur.due_day || 10));
  }, [cards]);

  useEffect(() => {
    if (!investAssets.length) {
      setAssetEditId("");
      setAssetEditSymbol("");
      setAssetEditName("");
      return;
    }
    const cur = investAssets.find((a) => String(a.id) === String(assetEditId)) || investAssets[0];
    setAssetEditId(String(cur.id));
    setAssetEditSymbol(cur.symbol || "");
    setAssetEditName(cur.name || "");
    setAssetEditClass(cur.asset_class || "");
    setAssetEditSector(cur.sector || "Não definido");
    setAssetEditCurrency((cur.currency || "BRL").toUpperCase());
    setAssetEditBrokerId(cur.broker_account_id ? String(cur.broker_account_id) : "");
  }, [investAssets]);

  const subtitle = useMemo(() => PAGE_SUBTITLES[page] || "Em migração do Streamlit", [page]);
  const txCategory = useMemo(
    () => categories.find((c) => String(c.id) === String(txCategoryId)) || null,
    [categories, txCategoryId]
  );
  const txEffectiveKind = txCategory?.kind || txKind;
  const txIsTransfer = txEffectiveKind === "Transferencia";
  const txIsExpense = txEffectiveKind === "Despesa";
  const bankAccountsOnly = useMemo(
    () => accounts.filter((a) => normalizeAccountType(a.type) === "Banco"),
    [accounts]
  );
  const cardsForTxMethod = useMemo(() => {
    if (!txIsExpense || txIsTransfer) return [];
    if (txMethod === "Credito") return (cards || []).filter((c) => String(c.card_type || "Credito") === "Credito");
    if (txMethod === "Debito") return (cards || []).filter((c) => String(c.card_type || "Credito") === "Debito");
    return [];
  }, [cards, txIsExpense, txIsTransfer, txMethod]);
  useEffect(() => {
    if (!txIsExpense || txIsTransfer || !["Credito", "Debito"].includes(txMethod)) {
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
  }, [txIsExpense, txIsTransfer, txMethod, cardsForTxMethod, txCardId]);
  const isCreditCardType = cardType === "Credito";

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
  const accountsTop = useMemo(
    () =>
      [...(dashAccountBalance || [])]
        .sort((a, b) => Number(b.saldo || 0) - Number(a.saldo || 0))
        .slice(0, 4),
    [dashAccountBalance]
  );
  const expensesTop = useMemo(
    () =>
      [...(dashExpenses || [])]
        .sort((a, b) => Number(b.valor || 0) - Number(a.valor || 0))
        .slice(0, 4),
    [dashExpenses]
  );
  const openInvoiceTotal = useMemo(
    () =>
      (cardInvoices || [])
        .filter((i) => String(i.status || "").toUpperCase() === "OPEN")
        .reduce((acc, i) => acc + Math.max(0, Number(i.total_amount || 0) - Number(i.paid_amount || 0)), 0),
    [cardInvoices]
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
    return list.slice(0, 5);
  }, [investPortfolio]);
  const investmentTotal = useMemo(
    () => investmentByClass.reduce((acc, r) => acc + Number(r.value || 0), 0),
    [investmentByClass]
  );
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

  async function reloadAllData() {
    const [acc, cat, dash, tx] = await Promise.all([
      getAccounts(),
      getCategories(),
      getKpis(),
      getTransactions(),
    ]);
    setAccounts(acc);
    setCategories(cat);
    setKpis(dash);
    setTransactions(tx);
  }

  async function reloadCardsData() {
    const [cardRows, invoiceRows] = await Promise.all([getCards(), getCardInvoices({ status: "OPEN" })]);
    setCards(cardRows || []);
    setCardInvoices(invoiceRows || []);
  }

  async function reloadDashboard(params = {}) {
    const filters = {
      date_from: params.date_from ?? dashDateFrom,
      date_to: params.date_to ?? dashDateTo,
      account: params.account ?? dashAccount,
    };
    try {
      const [k, m, e, ab] = await Promise.all([
        getDashboardKpis(filters),
        getDashboardMonthly(filters),
        getDashboardExpenses(filters),
        getDashboardAccountBalance(filters),
      ]);
      setDashKpis(k);
      setDashMonthly(m || []);
      setDashExpenses(e || []);
      setDashAccountBalance(ab || []);
      setDashMsg("");
    } catch (err) {
      setDashMsg(String(err.message || err));
    }
  }

  async function reloadTransactions() {
    const tx = await getTransactions();
    setTransactions(tx);
  }

  async function reloadInvestData() {
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
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const date = String(form.get("date") || "");
    const description = String(form.get("description") || "").trim();
    const amountAbs = Number(String(form.get("amount") || "0").replace(",", "."));
    const accountId = txAccountId ? Number(txAccountId) : NaN;
    const categoryIdRaw = String(txCategoryId || "");
    const categoryId = categoryIdRaw ? Number(categoryIdRaw) : null;
    const category = categories.find((c) => Number(c.id) === Number(categoryId));
    const method = String(txMethod || "").trim();
    const notes = String(form.get("notes") || "").trim();
    const effectiveKind = (category?.kind || txKind || "Receita").trim();
    const sourceAccountId = txSourceAccountId ? Number(txSourceAccountId) : NaN;
    const selectedCardId = txCardId ? Number(txCardId) : NaN;

    if (
      !description ||
      !date ||
      !Number.isFinite(accountId) ||
      accountId <= 0 ||
      !Number.isFinite(amountAbs) ||
      amountAbs <= 0
    ) {
      setTxMsg("Preencha data, descrição, valor (> 0) e selecione uma conta válida.");
      return;
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
      if (method === "Debito" && txCardId && (!Number.isFinite(selectedCardId) || selectedCardId <= 0)) {
        setTxMsg("Cartão de débito inválido.");
        return;
      }
      if (method === "PIX" && txCardId) {
        setTxMsg("PIX não usa cartão.");
        return;
      }
    }

    try {
      const out = await createTransaction({
        date,
        description,
        amount: Math.abs(amountAbs),
        account_id: accountId,
        category_id: categoryId,
        kind: effectiveKind,
        source_account_id: txIsTransfer ? sourceAccountId : null,
        card_id:
          txIsExpense && !txIsTransfer && ["Credito", "Debito"].includes(method) && Number.isFinite(selectedCardId)
            ? selectedCardId
            : null,
        method: method || null,
        notes: notes || null,
      });
      formEl.reset();
      setTxCategoryId("");
      setTxKind("Receita");
      setTxMethod("PIX");
      setTxSourceAccountId("");
      setTxCardId("");
      if (out?.mode === "transfer") {
        setTxMsg("Transferência registrada (origem debitada e corretora creditada).");
      } else if (out?.mode === "credit_card_charge") {
        setTxMsg("Compra no crédito registrada. A despesa será lançada no pagamento da fatura.");
      } else {
        setTxMsg("Lançamento salvo.");
      }
      await reloadTransactions();
      const dash = await getKpis();
      setKpis(dash);
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setTxMsg(`Erro ao salvar lançamento: ${String(err.message || err)}`);
    }
  }

  async function onDeleteTransaction(id) {
    try {
      await deleteTransaction(id);
      await reloadTransactions();
      const dash = await getKpis();
      setKpis(dash);
      await reloadDashboard();
      await reloadInvestData();
    } catch (err) {
      setTxMsg(String(err.message || err));
    }
  }

  async function onCreateInvestAsset(e) {
    e.preventDefault();
    setInvestMsg("");
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const symbol = String(form.get("symbol") || "").trim().toUpperCase();
    const name = String(form.get("name") || "").trim();
    const assetClass = String(form.get("asset_class") || "");
    const sector = String(form.get("sector") || "Não definido");
    const currency = String(form.get("currency") || "BRL").toUpperCase();
    const brokerAccountIdRaw = String(form.get("broker_account_id") || "");
    if (!symbol || !name || !assetClass) {
      setInvestMsg("Informe símbolo, nome e classe do ativo.");
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
      });
      formEl.reset();
      setInvestMsg("Ativo salvo.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onUpdateInvestAsset() {
    if (!assetEditId || !assetEditSymbol.trim() || !assetEditName.trim() || !assetEditClass) {
      setInvestMsg("Selecione e preencha os dados do ativo.");
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
      });
      setInvestMsg("Ativo atualizado.");
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onDeleteInvestAsset(id) {
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
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const assetId = Number(form.get("asset_id"));
    const date = String(form.get("date") || "");
    const side = String(form.get("side") || "BUY");
    const quantity = Number(String(form.get("quantity") || "0").replace(",", "."));
    const price = Number(String(form.get("price") || "0").replace(",", "."));
    const fees = Number(String(form.get("fees") || "0").replace(",", "."));
    const taxes = Number(String(form.get("taxes") || "0").replace(",", "."));
    const note = String(form.get("note") || "").trim();
    if (!assetId || !date || !Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) {
      setInvestMsg("Preencha ativo, data, quantidade e preço.");
      return;
    }
    try {
      await createInvestTrade({
        asset_id: assetId,
        date,
        side,
        quantity,
        price,
        fees: Number.isFinite(fees) ? fees : 0,
        taxes: Number.isFinite(taxes) ? taxes : 0,
        note: note || null,
      });
      formEl.reset();
      setInvestMsg("Operação salva.");
      await reloadInvestData();
      const dash = await getKpis();
      setKpis(dash);
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onDeleteInvestTrade(id) {
    try {
      await deleteInvestTrade(Number(id));
      setInvestMsg("Operação excluída.");
      await reloadInvestData();
      const dash = await getKpis();
      setKpis(dash);
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onCreateInvestIncome(e) {
    e.preventDefault();
    setInvestMsg("");
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
      const dash = await getKpis();
      setKpis(dash);
      await reloadDashboard();
      await reloadTransactions();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onDeleteInvestIncome(id) {
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

  async function onUpdateAllInvestPrices() {
    setInvestMsg("");
    const timeout = Number(String(quoteTimeout || "25").replace(",", "."));
    const workers = Number(String(quoteWorkers || "4").replace(",", "."));
    try {
      const out = await updateAllInvestPrices({
        timeout_s: Number.isFinite(timeout) ? timeout : 25,
        max_workers: Number.isFinite(workers) ? workers : 4,
      });
      setInvestMsg(`Cotações salvas: ${out.saved}/${out.total}`);
      await reloadInvestData();
    } catch (err) {
      setInvestMsg(String(err.message || err));
    }
  }

  async function onCreateAccount(e) {
    e.preventDefault();
    setManageMsg("");
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const type = String(form.get("type") || "Banco");
    if (!name) {
      setManageMsg("Informe o nome da conta.");
      return;
    }
    try {
      await createAccount({ name, type });
      formEl.reset();
      setManageMsg("Conta salva.");
      await reloadAllData();
      await reloadCardsData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
  }

  async function onUpdateAccount() {
    if (!accEditId || !accEditName.trim()) {
      setManageMsg("Selecione uma conta e informe nome.");
      return;
    }
    try {
      await updateAccount(Number(accEditId), { name: accEditName.trim(), type: accEditType });
      setManageMsg("Conta atualizada.");
      await reloadAllData();
      await reloadCardsData();
    } catch (err) {
      setManageMsg(String(err.message || err));
    }
  }

  async function onDeleteAccount() {
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
    const formEl = e.currentTarget;
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const kind = String(form.get("kind") || "Despesa");
    if (!name) {
      setManageMsg("Informe o nome da categoria.");
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
    const name = String(cardName || "").trim();
    const accId = Number(cardAccountId);
    const srcId = Number(cardSourceAccountId);
    const due = Number(String(cardDueDay || "0"));
    const isCredit = cardType === "Credito";
    const hasSource = Number.isFinite(srcId) && srcId > 0;
    if (
      !name ||
      !Number.isFinite(accId) ||
      accId <= 0 ||
      (isCredit && !hasSource) ||
      (isCredit && (!Number.isFinite(due) || due < 1 || due > 31))
    ) {
      if (!Number.isFinite(accId) || accId <= 0) {
        setCardMsg("Selecione a conta banco vinculada ao cartão.");
        return;
      }
      setCardMsg(
        isCredit
          ? "Preencha nome, tipo, conta banco vinculada, conta de pagamento da fatura e vencimento."
          : "Preencha nome, tipo e conta banco vinculada ao cartão."
      );
      return;
    }
    try {
      await createCard({
        name,
        brand: cardBrand,
        card_type: cardType,
        card_account_id: accId,
        source_account_id: hasSource ? srcId : null,
        due_day: isCredit ? due : null,
      });
      setCardMsg("Cartão cadastrado.");
      await reloadCardsData();
      await reloadAllData();
      await reloadDashboard();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
  }

  async function onUpdateCard() {
    setCardMsg("");
    const id = Number(cardEditId);
    const name = String(cardName || "").trim();
    const accId = Number(cardAccountId);
    const srcId = Number(cardSourceAccountId);
    const due = Number(String(cardDueDay || "0"));
    const isCredit = cardType === "Credito";
    const hasSource = Number.isFinite(srcId) && srcId > 0;
    if (
      !Number.isFinite(id) ||
      id <= 0 ||
      !name ||
      !Number.isFinite(accId) ||
      accId <= 0 ||
      (isCredit && !hasSource) ||
      (isCredit && (!Number.isFinite(due) || due < 1 || due > 31))
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
        brand: cardBrand,
        card_type: cardType,
        card_account_id: accId,
        source_account_id: hasSource ? srcId : null,
        due_day: isCredit ? due : null,
      });
      setCardMsg("Cartão atualizado.");
      await reloadCardsData();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
  }

  async function onDeleteCard() {
    setCardMsg("");
    const id = Number(cardEditId);
    if (!Number.isFinite(id)) return;
    try {
      await deleteCard(id);
      setCardMsg("Cartão excluído.");
      await reloadCardsData();
    } catch (err) {
      setCardMsg(String(err.message || err));
    }
  }

  async function onPayInvoice(invoice) {
    setCardMsg("");
    const invoiceId = Number(invoice?.id);
    const paymentDate = String(invoice?.due_date || "").trim() || new Date().toISOString().slice(0, 10);
    try {
      await payCardInvoice(invoiceId, { payment_date: paymentDate });
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

  function onLogout() {
    clearToken();
    setUser(null);
    setAccounts([]);
    setKpis(null);
  }

  async function onApplyDashboardFilters(e) {
    e.preventDefault();
    await reloadDashboard({
      date_from: dashDateFrom,
      date_to: dashDateTo,
      account: dashAccount,
    });
  }

  async function onPreviewTransactionsCsv() {
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
          {PAGES.map((p) => (
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
                    setPage("Dashboard");
                  }}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" strokeWidth="2" />
                    <path d="M4 20c1.6-3.7 4.1-5 8-5s6.4 1.3 8 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  Perfil
                </button>
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

      <main className={`main ${page === "Dashboard" ? "main-dashboard" : ""}`}>
        <header className="page-header">
          <h1>{page}</h1>
          <p>{subtitle}</p>
        </header>

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
                <button type="submit">Aplicar filtros</button>
              </form>
              {dashMsg ? <p>{dashMsg}</p> : null}
            </section>

            <section className="dash-kpis">
              <article className="card dash-kpi-card dash-kpi-expense">
                <h3>Despesas</h3>
                <strong>{brl.format(Number(currentKpi.despesas || 0))}</strong>
              </article>
              <article className="card dash-kpi-card dash-kpi-income">
                <h3>Receitas</h3>
                <strong>{brl.format(Number(currentKpi.receitas || 0))}</strong>
              </article>
              <article className="card dash-kpi-card">
                <h3>Saldo</h3>
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
                      </span>
                      <strong>{brl.format(Number(r.saldo || 0))}</strong>
                    </li>
                  ))}
                </ul>
                <div className="dash-list-total">
                  <span>Total</span>
                  <strong>{brl.format(Number(currentKpi.saldo || 0))}</strong>
                </div>
              </article>

              <article className="card dash-cards-card">
                {creditCards.length ? (
                  <div className={`dash-wallet-stack ${creditCards.length === 1 ? "single" : ""}`}>
                    {activeCreditCard ? (
                      <article
                        className="wallet-card wallet-card-front"
                        key={activeCreditCard.id}
                        title={`${activeCreditCard.name} (${activeCreditCard.brand || "Visa"})`}
                      >
                        <img
                          src={getCardBackground(activeCreditCard.brand || "Visa")}
                          alt=""
                          className={`wallet-bg ${getCardBgClass(activeCreditCard.brand || "Visa")}`}
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
                  <p className="dash-small">Abertas: {cardInvoices.length} | Cartões crédito: {creditCards.length}</p>
                  <strong className="dash-hero-value">{brl.format(openInvoiceTotal)}</strong>
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
                <h3>Despesas por categoria</h3>
                <ul className="dash-list">
                  {expensesTop.map((r) => (
                    <li key={r.category}>
                      <span>{r.category}</span>
                      <strong>{brl.format(Number(r.valor || 0))}</strong>
                    </li>
                  ))}
                </ul>
              </article>
            </section>

            <Suspense fallback={<section className="card"><p>Carregando gráficos...</p></section>}>
              <DashboardCharts monthly={dashMonthly} expenses={dashExpenses} />
            </Suspense>
          </>
        ) : null}

        {page === "Contas" ? (
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
              <h3>Cadastro de cartões</h3>
              <div className="mgr-grid">
                <input
                  type="text"
                  placeholder="Nome do cartão"
                  value={cardName}
                  onChange={(e) => setCardName(e.target.value)}
                />
                <select value={cardBrand} onChange={(e) => setCardBrand(e.target.value)}>
                  <option value="Visa">Visa</option>
                  <option value="Master">Master</option>
                </select>
                <select value={cardType} onChange={(e) => setCardType(e.target.value)}>
                  <option value="Credito">Credito</option>
                  <option value="Debito">Debito</option>
                </select>
                <select value={cardAccountId} onChange={(e) => setCardAccountId(e.target.value)}>
                  <option value="">Conta banco vinculada</option>
                  {bankAccountsOnly.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                {!bankAccountsOnly.length ? (
                  <input type="text" value="Sem conta Banco cadastrada." disabled />
                ) : null}
                <select value={cardSourceAccountId} onChange={(e) => setCardSourceAccountId(e.target.value)}>
                  <option value="">
                    {isCreditCardType ? "Conta banco de pagamento da fatura" : "Conta de pagamento (opcional)"}
                  </option>
                  {accounts
                    .filter((a) => {
                      const t = normalizeAccountType(a.type);
                      return t === "Banco";
                    })
                    .map((a) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                </select>
                {isCreditCardType ? (
                  <input
                    type="number"
                    min="1"
                    max="31"
                    value={cardDueDay}
                    onChange={(e) => setCardDueDay(e.target.value)}
                    placeholder="Dia do vencimento (1-31)"
                  />
                ) : (
                  <input type="text" value="Débito imediato na conta banco" disabled />
                )}
                <button onClick={onCreateCard}>Cadastrar cartão</button>
              </div>
            </section>

            <section className="card">
              <h3>Cartões cadastrados</h3>
              <div className="mgr-grid">
                <select value={cardEditId} onChange={(e) => setCardEditId(e.target.value)}>
                  <option value="">Selecione um cartão</option>
                  {cards.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} - {c.brand || "Visa"} - {c.card_type || "Credito"} ({c.linked_account})
                    </option>
                  ))}
                </select>
                <input value={cardName} onChange={(e) => setCardName(e.target.value)} placeholder="Nome do cartão" />
                <select value={cardBrand} onChange={(e) => setCardBrand(e.target.value)}>
                  <option value="Visa">Visa</option>
                  <option value="Master">Master</option>
                </select>
                <select value={cardType} onChange={(e) => setCardType(e.target.value)}>
                  <option value="Credito">Credito</option>
                  <option value="Debito">Debito</option>
                </select>
                <select value={cardAccountId} onChange={(e) => setCardAccountId(e.target.value)}>
                  <option value="">Conta banco vinculada</option>
                  {bankAccountsOnly.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                <select value={cardSourceAccountId} onChange={(e) => setCardSourceAccountId(e.target.value)}>
                  <option value="">{isCreditCardType ? "Conta banco pagamento fatura" : "Conta de pagamento (opcional)"}</option>
                  {accounts
                    .filter((a) => {
                      const t = normalizeAccountType(a.type);
                      return t === "Banco";
                    })
                    .map((a) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                </select>
                {isCreditCardType ? (
                  <input
                    type="number"
                    min="1"
                    max="31"
                    value={cardDueDay}
                    onChange={(e) => setCardDueDay(e.target.value)}
                  />
                ) : (
                  <input type="text" value="Débito imediato na conta banco" disabled />
                )}
                <button onClick={onUpdateCard}>Atualizar cartão</button>
                <button className="danger" onClick={onDeleteCard}>Excluir cartão</button>
              </div>
              {cardMsg ? <p>{cardMsg}</p> : null}
            </section>

            <section className="card">
              <h3>Faturas abertas</h3>
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
                    {cardInvoices.map((i) => (
                      <tr key={i.id}>
                        <td>{i.card_name}</td>
                        <td>{i.invoice_period}</td>
                        <td>{i.due_date}</td>
                        <td>{brl.format(Number(i.total_amount || 0))}</td>
                        <td>{brl.format(Number(i.paid_amount || 0))}</td>
                        <td>{i.status}</td>
                        <td>
                          {i.status === "OPEN" ? (
                            <button onClick={() => onPayInvoice(i)}>Pagar fatura</button>
                          ) : (
                            "-"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}

        {page === "Gerenciador" ? (
          <>
            {manageMsg ? (
              <section className="card">
                <p className="status-msg">{manageMsg}</p>
              </section>
            ) : null}

            <section className="card">
              <h3>Nova conta</h3>
              <form className="tx-form" onSubmit={onCreateAccount}>
                <input name="name" type="text" placeholder="Nome da conta" required />
                <select name="type" defaultValue="Banco">
                  <option value="Banco">Banco</option>
                  <option value="Dinheiro">Dinheiro</option>
                  <option value="Corretora">Corretora</option>
                </select>
                <button type="submit">Salvar conta</button>
              </form>
            </section>

            <section className="card">
              <h3>Gerenciar contas</h3>
              <div className="mgr-grid">
                <select
                  value={accEditId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setAccEditId(id);
                    const cur = accounts.find((a) => String(a.id) === id);
                    if (cur) {
                      setAccEditName(cur.name);
                      setAccEditType(cur.type);
                    }
                  }}
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.id} - {a.name} ({a.type})</option>
                  ))}
                </select>
                <input value={accEditName} onChange={(e) => setAccEditName(e.target.value)} placeholder="Nome" />
                <select value={accEditType} onChange={(e) => setAccEditType(e.target.value)}>
                  <option value="Banco">Banco</option>
                  <option value="Dinheiro">Dinheiro</option>
                  <option value="Corretora">Corretora</option>
                </select>
                <button onClick={onUpdateAccount}>Atualizar conta</button>
                <button className="danger" onClick={onDeleteAccount}>Excluir conta</button>
              </div>
            </section>

            <section className="card">
              <h3>Nova categoria</h3>
              <form className="tx-form" onSubmit={onCreateCategory}>
                <input name="name" type="text" placeholder="Nome da categoria" required />
                <select name="kind" defaultValue="Despesa">
                  <option value="Despesa">Despesa</option>
                  <option value="Receita">Receita</option>
                  <option value="Transferencia">Transferência</option>
                </select>
                <button type="submit">Salvar categoria</button>
              </form>
            </section>

            <section className="card">
              <h3>Gerenciar categorias</h3>
              <div className="mgr-grid">
                <select
                  value={catEditId}
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
                <input value={catEditName} onChange={(e) => setCatEditName(e.target.value)} placeholder="Nome" />
                <select value={catEditKind} onChange={(e) => setCatEditKind(e.target.value)}>
                  <option value="Despesa">Despesa</option>
                  <option value="Receita">Receita</option>
                  <option value="Transferencia">Transferência</option>
                </select>
                <button onClick={onUpdateCategory}>Atualizar categoria</button>
                <button className="danger" onClick={onDeleteCategory}>Excluir categoria</button>
              </div>
            </section>
          </>
        ) : null}

        {page === "Lançamentos" ? (
          <>
            <section className="card">
              <h3>Novo lançamento</h3>
              <form className="tx-form" onSubmit={onCreateTransaction}>
                {txIsTransfer ? (
                  <div className="transfer-hint">
                    <strong className="transfer-badge">Transferência</strong>
                    <span>
                      Fluxo em duas pernas: débito na <b>conta origem</b> e crédito na <b>conta destino (Corretora)</b>.
                    </span>
                  </div>
                ) : null}
                {txIsExpense && !txIsTransfer ? (
                  <div className="transfer-hint">
                    <strong className="transfer-badge">Despesa</strong>
                    <span>
                      Crédito registra na fatura e só vira despesa no pagamento. Débito com cartão debita na hora a conta banco vinculada.
                    </span>
                  </div>
                ) : null}
                <input name="date" type="date" required />
                <input name="description" type="text" placeholder="Descrição" required />
                <input name="amount" type="number" step="0.01" min="0.01" placeholder="Valor" required />
                <select
                  name="account_id"
                  required
                  value={txAccountId}
                  onChange={(e) => setTxAccountId(e.target.value)}
                >
                  <option value="" disabled>Conta</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                <select
                  name="category_id"
                  value={txCategoryId}
                  onChange={(e) => setTxCategoryId(e.target.value)}
                >
                  <option value="">(sem categoria)</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.kind})</option>
                  ))}
                </select>
                {txIsTransfer ? (
                  <select name="kind" value="Transferencia" disabled>
                    <option value="Transferencia">Transferência</option>
                  </select>
                ) : (
                  <select name="kind" value={txKind} onChange={(e) => setTxKind(e.target.value)}>
                    <option value="Receita">Receita (+)</option>
                    <option value="Despesa">Despesa (-)</option>
                  </select>
                )}
                {txIsTransfer ? (
                  <select
                    name="source_account_id"
                    value={txSourceAccountId}
                    onChange={(e) => setTxSourceAccountId(e.target.value)}
                    required
                  >
                    <option value="">Conta origem (Transferência)</option>
                    {accounts
                      .filter((a) => a.type !== "Corretora" && String(a.id) !== String(txAccountId))
                      .map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                  </select>
                ) : null}
                <select name="method" value={txMethod} onChange={(e) => setTxMethod(e.target.value)}>
                  <option value="PIX">PIX</option>
                  <option value="Debito">Debito</option>
                  <option value="Credito">Credito</option>
                  <option value="TED">TED</option>
                  <option value="Dinheiro">Dinheiro</option>
                </select>
                {txIsExpense && !txIsTransfer && ["Credito", "Debito"].includes(txMethod) ? (
                  <select
                    name="card_id"
                    value={txCardId}
                    onChange={(e) => setTxCardId(e.target.value)}
                    required={txMethod === "Credito"}
                  >
                    <option value="">
                      {txMethod === "Credito" ? "Cartão de crédito (obrigatório)" : "Cartão de débito (opcional)"}
                    </option>
                    {cardsForTxMethod.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} - {c.brand || "Visa"} ({c.linked_account})
                      </option>
                    ))}
                  </select>
                ) : null}
                <input name="notes" type="text" placeholder="Obs (opcional)" />
                <button type="submit">Salvar lançamento</button>
              </form>
              {txMsg ? <p>{txMsg}</p> : null}
            </section>

            <section className="card">
              <h3>Lançamentos recentes</h3>
              <div className="tx-table-wrap">
                <table className="tx-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Data</th>
                      <th>Descrição</th>
                      <th>Conta</th>
                      <th>Categoria</th>
                      <th>Valor</th>
                      <th>Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((t) => (
                      <tr key={t.id}>
                        <td>{t.id}</td>
                        <td>{t.date}</td>
                        <td>{t.description}</td>
                        <td>{t.account || "-"}</td>
                        <td>{t.category || "-"}</td>
                        <td>{Number(t.amount_brl || 0).toFixed(2)}</td>
                        <td>
                          <button onClick={() => onDeleteTransaction(t.id)}>Excluir</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}

        {page === "Importar CSV" ? (
          <>
            <section className="card">
              <h3>Importar lançamentos (CSV)</h3>
              <p>Colunas mínimas: <code>date, description, amount, account</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setTxCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewTransactionsCsv}>Prévia lançamentos</button>
                <button onClick={onImportTransactionsCsv}>Importar lançamentos</button>
              </div>
            </section>

            <section className="card">
              <h3>Importar ativos (CSV)</h3>
              <p>Colunas mínimas: <code>symbol, name, asset_class</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setAssetCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewAssetsCsv}>Prévia ativos</button>
                <button onClick={onImportAssetsCsv}>Importar ativos</button>
              </div>
            </section>

            <section className="card">
              <h3>Importar operações (CSV)</h3>
              <p>Colunas mínimas: <code>date, asset_id/symbol, side, quantity, price</code></p>
              <div className="mgr-grid">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setTradeCsvFile(e.target.files?.[0] || null)}
                />
                <button onClick={onPreviewTradesCsv}>Prévia operações</button>
                <button onClick={onImportTradesCsv}>Importar operações</button>
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

        {page === "Investimentos" ? (
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
              {investMsg ? <p>{investMsg}</p> : null}
            </section>

            {investTab === "Resumo" ? (
              <section className="cards">
                <article className="card">
                  <h3>Ativos</h3>
                  <strong>{Number(investSummaryData.assets_count || 0)}</strong>
                </article>
                <article className="card">
                  <h3>Total investido</h3>
                  <strong>{brl.format(Number(investSummaryData.total_invested || 0))}</strong>
                </article>
                <article className="card">
                  <h3>Saldo na corretora</h3>
                  <strong>{brl.format(Number(investSummaryData.broker_balance || 0))}</strong>
                </article>
                <article className="card">
                  <h3>Valor de mercado</h3>
                  <strong>{brl.format(Number(investSummaryData.total_market || 0))}</strong>
                </article>
                <article className="card">
                  <h3>Retorno total</h3>
                  <strong>{brl.format(Number(investSummaryData.total_return || 0))}</strong>
                  <p>{Number(investSummaryData.total_return_pct || 0).toFixed(2)}%</p>
                </article>
                <article className="card">
                  <h3>P&L não realizado</h3>
                  <strong>{brl.format(Number(investSummaryData.total_unrealized || 0))}</strong>
                </article>
              </section>
            ) : null}

            {investTab === "Ativos" ? (
              <>
                <section className="card">
                  <h3>Novo ativo</h3>
                  <form className="tx-form" onSubmit={onCreateInvestAsset}>
                    <input name="symbol" type="text" placeholder="Símbolo" required />
                    <input name="name" type="text" placeholder="Nome" required />
                    <select name="asset_class" defaultValue="">
                      <option value="" disabled>Classe</option>
                      {investMeta.asset_classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
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
                          <th>Setor</th>
                          <th>Moeda</th>
                          <th>Corretora</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investAssets.map((a) => (
                          <tr key={a.id}>
                            <td>{a.symbol}</td>
                            <td>{a.name}</td>
                            <td>{a.asset_class}</td>
                            <td>{a.sector || "-"}</td>
                            <td>{a.currency}</td>
                            <td>{a.broker_account || "-"}</td>
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
                    <select name="asset_id" defaultValue="">
                      <option value="" disabled>Ativo</option>
                      {investAssets.map((a) => (
                        <option key={a.id} value={a.id}>{a.symbol}</option>
                      ))}
                    </select>
                    <input name="date" type="date" required />
                    <select name="side" defaultValue="BUY">
                      <option value="BUY">BUY</option>
                      <option value="SELL">SELL</option>
                    </select>
                    <input name="quantity" type="number" step="0.00000001" min="0.00000001" placeholder="Quantidade" required />
                    <input name="price" type="number" step="0.0001" min="0.0001" placeholder="Preço" required />
                    <input name="fees" type="number" step="0.01" min="0" placeholder="Taxas" defaultValue="0" />
                    <input name="taxes" type="number" step="0.01" min="0" placeholder="Impostos" defaultValue="0" />
                    <input name="note" type="text" placeholder="Obs (opcional)" />
                    <button type="submit">Salvar operação</button>
                  </form>
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
                            <td>{t.side}</td>
                            <td>{Number(t.quantity || 0).toFixed(8)}</td>
                            <td>{Number(t.price || 0).toFixed(4)}</td>
                            <td>{Number(t.fees || 0).toFixed(2)}</td>
                            <td>
                              <button onClick={() => onDeleteInvestTrade(t.id)}>Excluir</button>
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
                  <button onClick={onUpdateAllInvestPrices}>Atualizar cotações automáticas</button>
                </div>
                <form className="tx-form" onSubmit={onUpsertInvestPrice}>
                  <select name="asset_id" defaultValue="">
                    <option value="" disabled>Ativo</option>
                    {investAssets.map((a) => (
                      <option key={a.id} value={a.id}>{a.symbol}</option>
                    ))}
                  </select>
                  <input name="date" type="date" required />
                  <input name="price" type="number" step="0.0001" min="0.0001" placeholder="Preço" required />
                  <input name="source" type="text" placeholder="Fonte" defaultValue="manual" />
                  <button type="submit">Salvar cotação manual</button>
                </form>
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
                      <th>Mercado</th>
                      <th>P&L Não Realizado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(investPortfolio.positions || []).map((p) => (
                      <tr key={`${p.asset_id}-${p.symbol}`}>
                        <td>{p.symbol}</td>
                        <td>{p.asset_class}</td>
                        <td>{Number(p.qty || 0).toFixed(8)}</td>
                        <td>{brl.format(Number(p.cost_basis || 0))}</td>
                        <td>{brl.format(Number(p.market_value || 0))}</td>
                        <td>{brl.format(Number(p.unrealized_pnl || 0))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {investMsg ? <p>{investMsg}</p> : null}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
