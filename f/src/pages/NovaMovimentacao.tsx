import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import Aviso from '../components/Aviso'
import PageHeader from '../components/PageHeader'
import useConfirmacao from '../components/useConfirmacao'
import { api } from '../services/api'
import type { ProdutoOpcoes } from '../types'

export default function NovaMovimentacao(){
 const [params]=useSearchParams();const tipoInicial=params.get('tipo')==='SAIDA'?'SAIDA':'ENTRADA'
 const [opcoes,setOpcoes]=useState<ProdutoOpcoes>({categorias:[],fornecedores:[],produtos:[],clientes:[]});const [dados,setDados]=useState({produto_id:'',tipo:tipoInicial,quantidade:'1',observacao:''});const [erro,setErro]=useState('');const [sucesso,setSucesso]=useState('');const {confirmar,modal}=useConfirmacao()
 useEffect(()=>{api.produtos.opcoes().then(setOpcoes).catch(e=>setErro(e.message))},[])
 async function enviar(e:FormEvent){
  e.preventDefault();setErro('');setSucesso('')
  const selecionado=opcoes.produtos.find(p=>p.id===Number(dados.produto_id))
  if(!selecionado){setErro('Selecione um produto válido.');return}
  if(!await confirmar({titulo:'Confirmar movimentação',mensagem:`Confirma ${dados.tipo==='ENTRADA'?'a entrada de':'a saída de'} ${dados.quantidade} unidade(s) de “${selecionado.nome}”?`,confirmarTexto:'Registrar'}))return
  try{const r=await api.movimentacoes.criar({produto_id:Number(dados.produto_id),tipo:dados.tipo,quantidade:Number(dados.quantidade),observacao:dados.observacao});setSucesso(r.mensagem+(r.aviso_estoque?' Atenção: o saldo atingiu o nível mínimo.':''));const novas=await api.produtos.opcoes();setOpcoes(novas)}catch(e){setErro((e as Error).message)}
 }
 return <>{modal}<PageHeader titulo="Movimentar estoque" subtitulo="Registre entradas e saídas"/><Aviso mensagem={sucesso}/><Aviso tipo="erro" mensagem={erro}/><form className="form-panel movement-form" onSubmit={enviar}><div className="form-grid"><label className="span-2">Produto *<select required value={dados.produto_id} onChange={e=>setDados({...dados,produto_id:e.target.value})}><option value="">Selecione</option>{opcoes.produtos.filter(p=>p.tipo!=='Software').map(p=><option key={p.id} value={p.id}>{p.sku} - {p.nome} - saldo atual: {p.estoque_atual}</option>)}</select></label><label>Tipo *<select value={dados.tipo} onChange={e=>setDados({...dados,tipo:e.target.value})}><option value="ENTRADA">ENTRADA</option><option value="SAIDA">SAÍDA</option></select></label><label>Quantidade *<input type="number" min="1" step="1" required value={dados.quantidade} onChange={e=>setDados({...dados,quantidade:e.target.value})}/></label><label className="span-2">Observação<textarea value={dados.observacao} onChange={e=>setDados({...dados,observacao:e.target.value})}/></label></div><div className="form-actions"><button className="primary-button">Registrar movimentação</button></div></form></>
}
