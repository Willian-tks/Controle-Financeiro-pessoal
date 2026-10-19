export function quoteFailureLabel(row) {
  if (row.ok) return "Atualizada";
  return ({
    no_data: "Sem dados",
    rate_limited: "Limite de consumo",
    access_denied: "Acesso ao provedor negado",
    timeout: "Tempo de consulta excedido",
    invalid_data: "Referência inválida",
    not_configured: "Provedor não configurado",
    provider_error: "Falha no provedor",
  })[row.error_code] || "Erro";
}

export function quoteUpdateNotice(result) {
  const saved = Number(result.saved || 0);
  const total = Number(result.total || 0);
  const failed = (result.report || []).filter(row => !row?.ok).length;
  const fxUnavailable = result.fx?.ok === false;
  if (!total) return { level: "warning", message: "Nenhum ativo elegível para atualizar nesta seleção." };
  const complete = saved === total && !failed && !fxUnavailable && result.ok !== false;
  const message = saved === 0
    ? `Nenhuma cotação foi salva (${total} ativos consultados).`
    : `Cotações salvas: ${saved}/${total}.`;
  return {
    level: complete ? "success" : "warning",
    message: `${message}${failed ? ` Falhas: ${failed}.` : ""}${fxUnavailable ? " PTAX indisponível; referência anterior preservada." : ""}`,
  };
}
