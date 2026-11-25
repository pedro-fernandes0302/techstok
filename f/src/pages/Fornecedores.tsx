import { useEffect, useState, type FormEvent } from 'react'
import Aviso from '../components/Aviso'
import PageHeader from '../components/PageHeader'
import useConfirmacao from '../components/useConfirmacao'
import { api } from '../services/api'
import type { Fornecedor } from '../types'

const inicial = { razao_social: '', cnpj: '', telefone: '', email: '' }

export default function Fornecedores() {
  const [lista, setLista] = useState<Fornecedor[]>([])
  const [dados, setDados] = useState(inicial)
  const [erro, setErro] = useState('')
  const [mensagem, setMensagem] = useState('')
  const { confirmar, modal } = useConfirmacao()

  const carregar = () => api.fornecedores.listar().then(setLista).catch(e => setErro(e.message))
  useEffect(() => { carregar() }, [])

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro('')
    setMensagem('')
    if (!await confirmar({
      titulo: 'Cadastrar fornecedor',
      mensagem: `Confirma o cadastro de “${dados.razao_social.trim()}”?`,
      confirmarTexto: 'Cadastrar',
    })) return
    try {
      const resposta = await api.fornecedores.criar(dados)
      setMensagem(resposta.mensagem)
      setDados(inicial)
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  async function excluir(fornecedor: Fornecedor) {
    setErro('')
    if (!await confirmar({
      titulo: 'Excluir fornecedor',
      mensagem: `Deseja excluir “${fornecedor.razao_social}”? Esta ação não pode ser desfeita.`,
      confirmarTexto: 'Excluir',
      perigo: true,
    })) return
    try {
      const resposta = await api.fornecedores.excluir(fornecedor.id)
      setMensagem(resposta.mensagem)
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  return <>
    {modal}
    <PageHeader titulo="Fornecedores" />
    <Aviso mensagem={mensagem} />
    <Aviso tipo="erro" mensagem={erro} />
    <div className="two-column">
      <form className="compact-panel" onSubmit={enviar}>
        <h2>Novo fornecedor</h2>
        <label>Razão social *<input required value={dados.razao_social} onChange={evento => setDados({ ...dados, razao_social: evento.target.value })} /></label>
        <label>CNPJ *<input required placeholder="00.000.000/0000-00" value={dados.cnpj} onChange={evento => setDados({ ...dados, cnpj: evento.target.value })} /></label>
        <label>Telefone<input value={dados.telefone} onChange={evento => setDados({ ...dados, telefone: evento.target.value })} /></label>
        <label>E-mail<input type="email" required value={dados.email} onChange={evento => setDados({ ...dados, email: evento.target.value })} /></label>
        <button className="primary-button">Cadastrar</button>
      </form>
      <section className="panel"><div className="table-wrap"><table>
        <thead><tr><th>Razão social</th><th>CNPJ</th><th>Contato</th><th></th></tr></thead>
        <tbody>
          {lista.map(fornecedor => <tr key={fornecedor.id}>
            <td>{fornecedor.razao_social}</td>
            <td>{fornecedor.cnpj}</td>
            <td>{fornecedor.telefone || '-'}<br /><small>{fornecedor.email || '-'}</small></td>
            <td><button className="danger-button" onClick={() => excluir(fornecedor)}>Excluir</button></td>
          </tr>)}
          {!lista.length && <tr><td colSpan={4} className="empty">Nenhum fornecedor.</td></tr>}
        </tbody>
      </table></div></section>
    </div>
  </>
}
