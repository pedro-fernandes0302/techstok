import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import type { DashboardResponse, Sessao } from '../types'
import Icon from '../components/Icons'
import Aviso from '../components/Aviso'
import useConfirmacao from '../components/useConfirmacao'

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export default function Dashboard() {
  const [dados, setDados] = useState<DashboardResponse>({ produtos: [], categorias: 0, fornecedores: 0 })
  const [usuario, setUsuario] = useState<Sessao | null>(null)
  const [busca, setBusca] = useState('')
  const [erro, setErro] = useState('')
  const [carregando, setCarregando] = useState(true)
  const { confirmar, modal } = useConfirmacao()
  const carregar = () => {
    setCarregando(true)
    api.dashboard().then(setDados).catch(e => setErro(e.message)).finally(() => setCarregando(false))
  }
  useEffect(() => {
    carregar()
    api.sessao().then(setUsuario).catch(e => setErro(e.message))
  }, [])
  const filtrados = useMemo(() => dados.produtos.filter(p =>
    [p.sku, p.nome, p.fabricante, p.categoria, p.fornecedor].join(' ').toLowerCase().includes(busca.toLowerCase())
  ), [dados, busca])
  const risco = dados.produtos.filter(p => p.estoque_atual <= p.estoque_minimo)
  const valor = dados.produtos.reduce((soma, p) => soma + p.preco * p.estoque_atual, 0)
  const unidades = dados.produtos.reduce((soma, p) => soma + p.estoque_atual, 0)
  const atalhos = [
    { icone: 'box', rotulo: 'Produtos', texto: 'Cadastro de produtos', to: '/produtos/novo', so: 'GERENTE' },
    { icone: 'entrada', rotulo: 'Entradas', texto: 'Gerenciar entradas de produtos no estoque', to: '/movimentacoes/nova?tipo=ENTRADA' },
    { icone: 'saida', rotulo: 'Saídas', texto: 'Gerenciar saídas de produtos do estoque', to: '/movimentacoes/nova?tipo=SAIDA' },
    { icone: 'venda', rotulo: 'Vendas', texto: 'Registrar vendas para clientes B2B', to: '/pdv' },
    { icone: 'fornecedor', rotulo: 'Fornecedores', texto: 'Cadastro de fornecedores', to: '/fornecedores', so: 'GERENTE' },
  ].filter(a => !a.so || a.so === usuario?.perfil)
  async function excluirProduto(id: number, nome: string) {
    setErro('')
    if (!await confirmar({
      titulo: 'Descontinuar produto',
      mensagem: `Confirma a exclusão de “${nome}”? Se houver histórico ou licenças vinculadas, o sistema manterá o registro.`,
      confirmarTexto: 'Descontinuar',
      perigo: true,
    })) return
    try {
      await api.produtos.excluir(id)
      carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }
  return <>
    {modal}
    <h1 className="nv-title">Dashboard</h1>
    <Aviso tipo="erro" mensagem={erro} />
    <section className="nv-cards">
      <article className="warn"><div><span>Produtos com estoque baixo</span><strong>{risco.length}</strong></div><Icon nome="alerta" tamanho={30} /></article>
      <article className="info"><div><span>Quantidade de produtos no estoque</span><strong>{unidades}</strong></div><Icon nome="box" tamanho={30} /></article>
      <article className="ok"><div><span>Custo total de produtos</span><strong>{money.format(valor)}</strong></div><Icon nome="cifrao" tamanho={30} /></article>
    </section>
    <h2 className="nv-subtitle">Atalhos</h2>
    <section className="nv-shortcuts">
      {atalhos.map(a => <article key={a.rotulo}><Icon nome={a.icone} tamanho={46} /><Link className="nv-btn" to={a.to}>{a.rotulo}</Link><p>{a.texto}</p></article>)}
    </section>
    <h2 className="nv-subtitle">Catálogo</h2>
    <section className="panel"><div className="panel-heading"><div><h2>Catálogo consolidado</h2><p>Saldo único, chaves digitais disponíveis e ponto de reposição</p></div><label className="search"><span>⌕</span><input value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar produto ou fornecedor" /></label></div>
      {carregando ? <div className="loading">Carregando inventário...</div> : <div className="table-wrap"><table><thead><tr><th>Produto</th><th>Tipo</th><th>Categoria</th><th>Preço</th><th>Estoque</th><th>Ativos disponíveis</th><th>Status</th>{usuario?.perfil === 'GERENTE' && <th></th>}</tr></thead><tbody>
        {filtrados.map(p => {
          const alerta = p.estoque_atual <= p.estoque_minimo
          return <tr key={p.id} className={alerta ? 'risk-row' : ''}>
            <td><div className="product-cell"><div className="product-icon">{p.tipo === 'Software' ? '▣' : '▤'}</div><div><strong>{p.nome}</strong><span>{p.sku} · {p.fabricante}</span></div></div></td>
            <td><span className="status">{p.tipo_catalogo}</span></td><td>{p.categoria}</td><td>{money.format(p.preco)}</td>
            <td><strong>{p.estoque_atual}</strong><span className="minimum"> / mín. {p.estoque_minimo}</span></td>
            <td>{p.tipo === 'Software' ? `${p.chaves_disponiveis} chave(s)` : `${p.quantidade_fisica} unidade(s) física(s)`}</td>
            <td>{alerta ? <span className="status risk">ALERTA · Reposição</span> : <span className="status ok">Estoque normal</span>}</td>
            {usuario?.perfil === 'GERENTE' && <td><button className="more-button" aria-label={`Excluir ${p.nome}`} onClick={() => excluirProduto(p.id, p.nome)}>⌫</button></td>}
          </tr>
        })}
        {!filtrados.length && <tr><td colSpan={usuario?.perfil === 'GERENTE' ? 8 : 7} className="empty">Nenhum produto encontrado.</td></tr>}
      </tbody></table></div>}
    </section>
  </>
}
