import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LineChart,
  Line,
} from "recharts";

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
                <Bar dataKey="valor" fill="#3b82f6" />
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
