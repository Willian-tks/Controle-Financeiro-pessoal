import {
  BarChart,
  Bar,
  Cell,
  AreaChart,
  Area,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const brl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

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

function formatMonthLabel(value) {
  const raw = String(value || "");
  if (!/^\d{4}-\d{2}$/.test(raw)) return raw;
  const dt = new Date(`${raw}-01T00:00:00`);
  return dt.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

export default function DashboardCharts({ monthly, expenses }) {
  return (
    <>
      <section className="card">
        <h3>Evolução patrimonial</h3>
        {monthly.length ? (
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={monthly}>
                <defs>
                  <linearGradient id="wealthAreaFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#68d3ff" stopOpacity={0.38} />
                    <stop offset="100%" stopColor="#68d3ff" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tickFormatter={formatMonthLabel} />
                <YAxis tickFormatter={(value) => brl.format(Number(value || 0))} width={96} />
                <Tooltip
                  formatter={(value) => brl.format(Number(value || 0))}
                  labelFormatter={(value) => formatMonthLabel(value)}
                />
                <Area
                  type="monotone"
                  dataKey="patrimonio"
                  fill="url(#wealthAreaFill)"
                  stroke="#68d3ff"
                  strokeWidth={3}
                  dot={{ r: 3, fill: "#9ff7be", stroke: "#68d3ff", strokeWidth: 2 }}
                  activeDot={{ r: 5 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p>Sem evolução patrimonial para o período.</p>
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
