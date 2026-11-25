import { useEffect, useState, type FormEvent } from 'react'
import Aviso from '../components/Aviso'
import PageHeader from '../components/PageHeader'
import useConfirmacao from '../components/useConfirmacao'
import { api } from '../services/api'
import type { Categoria } from '../types'

export default function Categorias() {
  const [lista, setLista] = useState<Categoria[]>([])
  const [nome, setNome] = useState('')
  const [erro, setErro] = useState('')
  const [mensagem, setMensagem] = useState('')
  const { confirmar, modal } = useConfirmacao()

  const carregar = () => api.categorias.listar().then(setLista).catch(e => setErro(e.message))
  useEffect(() => { carregar() }, [])

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro('')
    setMensagem('')
    if (!await confirmar({
      titulo: 'Cadastrar categoria',
      mensagem: `Confirma o cadastro da categoria “${nome.trim()}”?`,
      confirmarTexto: 'Cadastrar',
    })) return
    try {
      const resposta = await api.categorias.criar(nome)
      setMensagem(resposta.mensagem)
      setNome('')
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  async function excluir(categoria: Categoria) {
    setErro('')
    if (!await confirmar({
      titulo: 'Excluir categoria',
      mensagem: `Deseja excluir “${categoria.nome}”? Esta ação não pode ser desfeita.`,
      confirmarTexto: 'Excluir',
      perigo: true,
    })) return
    try {
      const resposta = await api.categorias.excluir(categoria.id)
      setMensagem(resposta.mensagem)
      await carregar()
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  return <>
    {modal}
    <PageHeader titulo="Categorias" />
    <Aviso mensagem={mensagem} />
    <Aviso tipo="erro" mensagem={erro} />
    <div className="two-column">
      <form className="compact-panel" onSubmit={enviar}>
        <h2>Nova categoria</h2>
        <label>Nome *<input required value={nome} onChange={evento => setNome(evento.target.value)} /></label>
        <button className="primary-button">Cadastrar</button>
      </form>
      <section className="panel"><div className="table-wrap"><table>
        <thead><tr><th>Nome</th><th></th></tr></thead>
        <tbody>
          {lista.map(categoria => <tr key={categoria.id}>
            <td>{categoria.nome}</td>
            <td><button className="danger-button" onClick={() => excluir(categoria)}>Excluir</button></td>
          </tr>)}
          {!lista.length && <tr><td colSpan={2} className="empty">Nenhuma categoria.</td></tr>}
        </tbody>
      </table></div></section>
    </div>
  </>
}
