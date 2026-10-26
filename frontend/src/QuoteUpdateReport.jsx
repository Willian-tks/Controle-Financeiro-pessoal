import { quoteFailureLabel } from "./quoteUpdateNotice.js";
import { formatLocalizedNumber, formatIsoDatePtBr, formatIsoDateTimePtBr } from "./formatters.js";

export default function QuoteUpdateReport({ investPriceUpdateReport, investAssets }) {
  return (
                <section className="card quote-section-card quote-block-card">
                  <div className="quote-section-head">
                    <div>
                      <h4>Relatório da última execução</h4>
                      <p className="tx-helper">Resultado da coleta automática exibido por ativo nesta sessão.</p>
                    </div>
                  </div>
                {investPriceUpdateReport.length ? (
                  <div className="tx-table-wrap">
                    <table className="tx-table">
                      <thead>
                        <tr>
                          <th>Ativo</th>
                          <th>Status</th>
                          <th>Preço unitário</th>
                          <th>Moeda</th>
                          <th>Data da referência</th>
                          <th>Fonte</th>
                          <th>Consulta</th>
                          <th>Tempo (s)</th>
                          <th>Detalhe</th>
                        </tr>
                      </thead>
                      <tbody>
                        {investPriceUpdateReport.map((row, idx) => (
                          <tr key={`${row?.symbol || "sem-symbol"}-${idx}`}>
                            <td>{row?.symbol || "-"}</td>
                            <td>{quoteFailureLabel(row)}</td>
                            <td>{Number(row?.price || 0) > 0 ? formatLocalizedNumber(row.price, 4) : "-"}</td>
                            <td>{row.currency || investAssets.find(asset => String(asset.id) === String(row.asset_id))?.currency || "-"}</td>
                            <td>{row?.px_date ? formatIsoDatePtBr(row.px_date) : "-"}</td>
                            <td>{row?.src || (row.attempts || []).map(attempt => attempt.provider).filter(Boolean).join(" / ") || "-"}</td>
                            <td>{row.cache_hit ? `Cache (${Math.floor(Number(row.cache_age_s || 0) / 60)} min)` : "Nova consulta"}{row.fetched_at ? <small className="tx-helper" style={{ display: "block" }}>{formatIsoDateTimePtBr(row.fetched_at)}</small> : null}</td>
                            <td>{Number.isFinite(Number(row?.elapsed_s)) ? formatLocalizedNumber(row.elapsed_s, 2) : "-"}</td>
                            <td>{row?.error || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="invest-empty-state">
                    <h4>Sem execução nesta sessão</h4>
                    <p>Nenhuma atualização automática de cotações foi rodada nesta sessão até o momento.</p>
                  </div>
                )}
                </section>
  );
}
