import {useEffect,useRef,useState} from 'react';
import {emptyQuickDraft,localToday,quickAmount,quickPayload} from './quickEntry';
import './QuickEntry.css';

export default function QuickEntry({open,onClose,accounts,categories,transferAccounts,transactions,onSave,onFull}) {
  const dialog=useRef(null),lock=useRef(false),returnFocus=useRef(null);
  const [draft,setDraft]=useState(emptyQuickDraft),[errors,setErrors]=useState({}),[message,setMessage]=useState(''),[saved,setSaved]=useState(false),[busy,setBusy]=useState(false);
  useEffect(()=>{if(open){returnFocus.current=document.activeElement;dialog.current.showModal();}else if(dialog.current.open){dialog.current.close();returnFocus.current?.focus();}},[open]);
  const set=(key,value)=>{setDraft(d=>({...d,[key]:value}));setErrors(e=>({...e,[key]:''}));setMessage('');};
  const kindLabel=draft.kind==='Transferencia'?'Transferência':draft.kind;
  const available=draft.kind==='Transferencia'?transferAccounts:accounts;
  const filtered=categories.filter(c=>c.kind===draft.kind);
  const recentIds=[...new Set(transactions.map(t=>String(t.category_id)))];
  const recentCategories=recentIds.map(id=>filtered.find(c=>String(c.id)===id)).filter(Boolean).slice(0,3);
  const repeat=transactions.find(t=>['Despesa','Receita'].includes(t.kind)&&['PIX','Debito','TED','Dinheiro'].includes(t.method)&&Number.isFinite(Number(t.amount))&&accounts.some(a=>String(a.id)===String(t.account_id))&&categories.some(c=>String(c.id)===String(t.category_id)&&c.kind===t.kind));
  const error=key=>errors[key]?<span className="quick-error" id={`quick-${key}-error`}>{errors[key]}</span>:null;
  const attr=key=>({'aria-invalid':Boolean(errors[key]),'aria-describedby':errors[key]?`quick-${key}-error`:undefined});
  async function submit(e){e.preventDefault();if(lock.current)return;const result=quickPayload(draft,accounts,categories,transferAccounts);setErrors(result.errors);if(Object.keys(result.errors).length)return;lock.current=true;setBusy(true);setMessage('');try{const msg=await onSave(result.payload);setSaved(true);setDraft(emptyQuickDraft());setMessage(msg||'Lançamento salvo.');}catch(err){setMessage(`Não foi possível salvar: ${err.message||err}. Confira o histórico antes de repetir se houve falha de conexão.`);}finally{lock.current=false;setBusy(false);}}
  const amount=quickAmount(draft.amount);
  const name=id=>accounts.find(a=>String(a.id)===String(id))?.name||'Selecione a conta';
  function full(future=false){if(!busy){onFull({...draft},future);setDraft(emptyQuickDraft());setErrors({});setMessage('');}}
  return <dialog className="quick-dialog" ref={dialog} aria-labelledby="quick-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <header><div><span className="quick-eyebrow">NO SEU DIA A DIA</span><h2 id="quick-title">Novo lançamento</h2></div><button type="button" disabled={busy} onClick={onClose} aria-label="Fechar lançamento rápido">✕</button></header>
    {saved?<div><p role="status">{message}</p><button className="quick-primary" onClick={()=>{setSaved(false);setMessage('');setErrors({});}}>Novo lançamento</button></div>:<form onSubmit={submit} noValidate>
    <fieldset disabled={busy}><legend className="quick-sr">Dados do lançamento</legend>
    <div className="quick-types" role="group" aria-label="Tipo de lançamento">{['Despesa','Receita','Transferencia'].map(k=><button type="button" key={k} aria-pressed={draft.kind===k} onClick={()=>{setDraft(d=>({...d,kind:k,category:'',method:'PIX',account:'',destination:''}));setErrors({});setMessage('');}}>{k==='Transferencia'?'Transferência':k}</button>)}</div>{error('kind')}
    <label htmlFor="quick-amount">Valor (R$)</label><input id="quick-amount" className="quick-amount" inputMode="decimal" autoComplete="off" placeholder="0,00" value={draft.amount} onChange={e=>set('amount',e.target.value)} {...attr('amount')}/>{error('amount')}
    <div className="quick-row"><div><label htmlFor="quick-date">Data</label><input id="quick-date" type="date" value={draft.date} onChange={e=>set('date',e.target.value)} {...attr('date')}/>{error('date')}</div><div><label htmlFor="quick-account">{draft.kind==='Transferencia'?'Conta de origem':'Conta'}</label><select id="quick-account" value={draft.account} onChange={e=>set('account',e.target.value)} {...attr('account')}><option value="">Selecione</option>{available.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}</select>{error('account')}</div></div>
    {draft.kind==='Transferencia'?<><label htmlFor="quick-destination">Conta de destino</label><select id="quick-destination" value={draft.destination} onChange={e=>set('destination',e.target.value)} {...attr('destination')}><option value="">Selecione</option>{available.filter(a=>String(a.id)!==draft.account).map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</select>{error('destination')}</>:null}
    <label htmlFor="quick-description">Descrição (opcional)</label><input id="quick-description" value={draft.description} placeholder="Ex.: almoço ou serviço" onChange={e=>set('description',e.target.value)}/>
    {draft.kind&&draft.kind!=='Transferencia'?<><label htmlFor="quick-category">Categoria</label><select id="quick-category" value={draft.category} onChange={e=>set('category',e.target.value)} {...attr('category')}><option value="">Selecione</option>{filtered.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>{error('category')}<div className="quick-chips">{recentCategories.map(c=><button type="button" key={c.id} onClick={()=>set('category',String(c.id))}>{c.name}</button>)}</div></>:null}
    {draft.kind?<><label htmlFor="quick-method">{draft.kind==='Receita'?'Recebimento':'Pagamento'}</label><select id="quick-method" value={draft.method} onChange={e=>set('method',e.target.value)} {...attr('method')}>{(draft.kind==='Despesa'?['PIX','Debito','TED','Dinheiro','Credito']:['PIX','TED','Dinheiro']).map(m=><option key={m} value={m}>{m==='Credito'?'Cartão de crédito':m==='Debito'?'Débito':m}</option>)}</select>{error('method')}</>:null}
    {draft.method==='Credito'?<p className="quick-hint">Continue no formulário completo para escolher o cartão e conferir a fatura. Os dados preenchidos serão mantidos.</p>:null}
    <details><summary>Mais opções</summary><label htmlFor="quick-notes">Observações</label><textarea id="quick-notes" value={draft.notes} onChange={e=>set('notes',e.target.value)}/><button type="button" onClick={()=>full(false)}>Formulário completo</button>{draft.kind==='Despesa'?<button type="button" onClick={()=>full(true)}>Agendar compromisso</button>:null}</details>
    {repeat?<button type="button" className="quick-repeat" onClick={()=>{setDraft({...emptyQuickDraft(),kind:repeat.kind,amount:Math.abs(Number(repeat.amount)).toFixed(2).replace('.',','),date:localToday(),account:String(repeat.account_id),category:String(repeat.category_id),method:repeat.method,description:repeat.description||''});setErrors({});setMessage('');}}>Repetir: {repeat.description||'último lançamento'} (revisar)</button>:null}
    </fieldset>
    {message?<p className="quick-error" role="alert">{message}</p>:null}
    <footer><p className="quick-review">{kindLabel||'Escolha o tipo'} · {Number.isFinite(amount)?amount.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}):'Informe o valor'} · {draft.date.split('-').reverse().join('/')}<br/>{name(draft.account)}{draft.kind==='Transferencia'?` → ${name(draft.destination)}`:''}</p>{draft.method==='Credito'?<button className="quick-primary" type="button" disabled={busy} onClick={e=>{e.preventDefault();full(false);}}>Continuar no formulário completo</button>:<button className="quick-primary" disabled={busy} type="submit">{busy?'Salvando…':`Salvar ${kindLabel.toLowerCase()||'lançamento'}`}</button>}</footer>
    </form>}
  </dialog>;
}
