import { brl } from "./formatters.js";

export default function DashboardOverview({ accountsTotal, currentKpi, dashboardFilterBaseLabel, commitmentsAging, trendEnd, trendMonthLabel, trendDirection, trendDelta, trendPct, canViewLancamentos, icSaldo, icDashboard, icDespesa, icReceita, onOpenTransactions, onOpenCommitments }) {
  return (
            <section className="dash-kpis dash-overview">
              <article className="card dash-kpi-card dash-kpi-primary">
                <h3 className="dash-kpi-title">
                  <img src={icSaldo} alt="" className="dash-kpi-icon" />
                  <span>Saldo disponível</span>
                </h3>
                <strong>{brl.format(accountsTotal)}</strong>
                <p>Contas marcadas para o Dashboard, posição atual.</p>
              </article>
              <article className="card dash-kpi-card">
                <h3 className="dash-kpi-title">
                  <img src={icDashboard} alt="" className="dash-kpi-icon" />
                  <span>Resultado do período</span>
                </h3>
                <strong>{brl.format(Number(currentKpi.saldo || 0))}</strong>
                <p>{dashboardFilterBaseLabel}</p>
                <div className="dash-kpi-split">
                  <button type="button" onClick={onOpenTransactions} disabled={!canViewLancamentos}>
                    Ver lançamentos
                  </button>
                  <span>Receitas {brl.format(Number(currentKpi.receitas || 0))}</span>
                  <span>Despesas {brl.format(Number(currentKpi.despesas || 0))}</span>
                </div>
              </article>
              <article className="card dash-kpi-card">
                <h3 className="dash-kpi-title">
                  <img src={icDespesa} alt="" className="dash-kpi-icon" />
                  <span>Compromissos</span>
                </h3>
                <strong>{brl.format(commitmentsAging.aVencer + commitmentsAging.vencidos)}</strong>
                <p>A vencer e vencidos no período filtrado.</p>
                <div className="dash-kpi-split">
                  <button type="button" onClick={onOpenCommitments} disabled={!canViewLancamentos}>
                    Abrir pendentes
                  </button>
                  <span>A vencer {brl.format(commitmentsAging.aVencer)}</span>
                  <span>Vencidos {brl.format(commitmentsAging.vencidos)}</span>
                </div>
              </article>
              <article className="card dash-kpi-card">
                <h3 className="dash-kpi-title">
                  <img src={icReceita} alt="" className="dash-kpi-icon" />
                  <span>Patrimônio</span>
                </h3>
                <strong>{brl.format(trendEnd)}</strong>
                <p>{trendMonthLabel ? `Fechamento de ${trendMonthLabel}.` : "Sem base mensal no período."}</p>
                <div className="dash-kpi-split">
                  <span className={trendDirection}>{trendDelta >= 0 ? "+" : "-"}{brl.format(Math.abs(trendDelta))}</span>
                  <span>{trendDelta >= 0 ? "+" : "-"}{Math.abs(trendPct).toFixed(1)}% vs mês anterior</span>
                </div>
              </article>
            </section>
  );
}
