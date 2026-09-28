export function localToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
export function emptyQuickDraft() {
  return {kind:'', amount:'', date:localToday(), account:'', destination:'', category:'', method:'PIX', description:'', notes:''};
}
export function quickAmount(value) {
  const s=String(value).trim();
  if (!/^(\d+|\d{1,3}(\.\d{3})+)(,\d{1,2})?$/.test(s)) return NaN;
  return Number(s.replaceAll('.','').replace(',','.'));
}
export function quickPayload(d, accounts, categories, transferAccounts) {
  const errors={};
  const amount=quickAmount(d.amount);
  if (!['Despesa','Receita','Transferencia'].includes(d.kind)) errors.kind='Escolha o tipo de lançamento.';
  if (!Number.isFinite(amount)||amount<=0) errors.amount='Informe um valor positivo, como 42,90.';
  const date=new Date(`${d.date}T12:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d.date)||!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==d.date) errors.date='Informe uma data válida.';
  const allowed=d.kind==='Transferencia'?transferAccounts:accounts;
  if(!allowed.some(a=>String(a.id)===String(d.account))) errors.account='Escolha uma conta válida.';
  if(d.kind==='Transferencia') {
    if(!allowed.some(a=>String(a.id)===String(d.destination))||d.account===d.destination) errors.destination='Escolha uma conta de destino diferente da origem.';
  } else if(!categories.some(c=>String(c.id)===String(d.category)&&c.kind===d.kind)) errors.category='Escolha uma categoria deste tipo.';
  const methods=d.kind==='Despesa'?['PIX','Debito','TED','Dinheiro']:['PIX','TED','Dinheiro'];
  if(!methods.includes(d.method)) errors.method='Use o formulário completo para esta forma de pagamento.';
  return {errors,payload:{date:d.date,description:d.description.trim(),amount,kind:d.kind,account_id:Number(d.kind==='Transferencia'?d.destination:d.account),source_account_id:d.kind==='Transferencia'?Number(d.account):null,category_id:d.kind==='Transferencia'?null:Number(d.category),method:d.method,notes:d.notes.trim()||null}};
}
