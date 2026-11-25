import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Sessao } from '../types'
import Icon from './Icons'

export default function Layout() {
  const [usuario, setUsuario] = useState<Sessao | null>(null)
  const [menuAberto, setMenuAberto] = useState(false)
  const navegar = useNavigate()
  useEffect(() => { api.sessao().then(setUsuario).catch(() => setUsuario(null)) }, [])
  async function sair() {
    try { await api.logout() } finally { navegar('/login') }
  }
  const gerente = usuario?.perfil === 'GERENTE'
  const item = (to: string, icone: string, texto: string, end = false) =>
    <NavLink to={to} end={end} title={texto}><Icon nome={icone} /><span>{texto}</span></NavLink>

  return <div className="nv-shell">
    <header className="nv-top">
      <Link to="/" className="nv-brand"><svg width="30" height="30" viewBox="0 0 24 24" fill="#1e6fd9" aria-hidden="true"><path d="M7 18a4.5 4.5 0 01-.6-8.96A6 6 0 0118 9.5a4.2 4.2 0 01-.5 8.5z"/></svg><strong>TechStock</strong></Link>
      <div className="nv-top-right">
        <Link to="/">Início</Link>
        <div className="nv-user">
          <button onClick={() => setMenuAberto(v => !v)} aria-expanded={menuAberto}>{usuario?.nome ?? 'Visitante'} ▾</button>
          {menuAberto && <div className="nv-menu">
            {usuario ? <><small>{usuario.perfil}</small><button onClick={sair}>Sair</button></> : <Link to="/login">Entrar</Link>}
          </div>}
        </div>
      </div>
    </header>
    <aside className="nv-side">
      <nav>
        {item('/', 'dashboard', 'Dashboard', true)}
        {item('/produtos/novo', 'box', 'Produtos')}
        {item('/movimentacoes/nova?tipo=ENTRADA', 'entrada', 'Entradas')}
        {item('/movimentacoes/nova?tipo=SAIDA', 'saida', 'Saídas')}
        {item('/pdv', 'venda', 'Vendas')}
        {gerente && item('/fornecedores', 'fornecedor', 'Fornecedores')}
        {gerente && item('/usuarios/novo', 'usuario', 'Cadastrar operador')}
        {gerente && item('/categorias', 'categoria', 'Categorias')}
        {gerente && item('/livro-razao', 'livro', 'Livro-Razão')}
        {gerente && item('/movimentacoes', 'historico', 'Histórico')}
      </nav>
      <button className="nv-up" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label="Voltar ao topo"><Icon nome="chevron" /></button>
    </aside>
    <main className="nv-main"><Outlet /></main>
  </div>
}
