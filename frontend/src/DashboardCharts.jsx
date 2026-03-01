import {
  BarChart,
  Bar,
  Cell,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LineChart,
  Line,
} from "recharts";

const EXPENSE_CATEGORY_COLORS = {
  servicos: "#4e79ff",
  mesada: "#00b8a9",
  casa: "#ff8a3d",
  creditos_bancarios: "#9b7bff",
  seguros: "#f4c84b",
  agropecuaria: "#24c16d",
  agua: "#27b4d8",
  luz: "#ff6b7a",
};

const EXPENSE_FALLBACK_COLORS = [
  "#4e79ff",
  "#00b8a9",
  "#ff8a3d",
  "#9b7bff",
  "#f4c84b",
  "#24c16d",
  "#27b4d8",
  "#ff6b7a",
];

function normalizeCategory(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "_");
}

function fallbackColor(value) {
  const key = normalizeCategory(value);
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return EXPENSE_FALLBACK_COLORS[hash % EXPENSE_FALLBACK_COLORS.length];
}

function categoryColor(category) {
  const key = normalizeCategory(category);
  return EXPENSE_CATEGORY_COLORS[key] || fallbackColor(category);
}

export default function DashboardCharts({ monthly, expenses }) {
  return (
    <>
      <section className="card">
        <h3>Saldo por mês</h3>
        {monthly.length ? (
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="saldo" stroke="#1f8cea" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>Sem dados para o período.</p>
        )}
      </section>

      <section className="card">
        <h3>Despesas por categoria</h3>
        {expenses.length ? (
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={expenses}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="category" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="valor">
                  {expenses.map((item, idx) => (
                    <Cell key={`expense-cell-${String(item?.category || idx)}`} fill={categoryColor(item?.category)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>Sem despesas no período.</p>
        )}
      </section>
    </>
  );
}
