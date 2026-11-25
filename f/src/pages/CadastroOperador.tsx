import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Aviso from '../components/Aviso'
import PageHeader from '../components/PageHeader'
import useConfirmacao from '../components/useConfirmacao'
import { api } from '../services/api'
import type { Sessao } from '../types'

export default function CadastroOperador() {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState('')
  const [carregando, setCarregando] = useState(true)
  const navegar = useNavigate()
  const { confirmar, modal } = useConfirmacao()

  useEffect(() => {
    api.sessao()
      .then((sessao: Sessao) => {
        if (sessao.perfil !== 'GERENTE') navegar('/')
      })
      .catch(() => navegar('/login'))
      .finally(() => setCarregando(false))
  }, [navegar])

  async function cadastrar(evento: FormEvent) {
    evento.preventDefault()
    setErro('')
    setSucesso('')
    if (!await confirmar({
      titulo: 'Criar conta de Operador',
      mensagem: `Confirma a criação de uma conta de Operador para ${email.trim()}?`,
      confirmarTexto: 'Criar conta',
    })) return
    try {
      await api.cadastro({ nome, email, senha })
      setSucesso(`Operador ${email} cadastrado com sucesso.`)
      setNome('')
      setEmail('')
      setSenha('')
    } catch (e) {
      setErro((e as Error).message)
    }
  }

  if (carregando) return <div className="loading">Verificando permissão...</div>
  return <>
    {modal}
    <PageHeader titulo="Cadastrar operador" subtitulo="Somente Gerentes podem criar contas de Operador." />
    <Aviso mensagem={sucesso} />
    <Aviso tipo="erro" mensagem={erro} />
    <form className="form-panel movement-form" onSubmit={cadastrar}>
      <div className="form-grid">
        <label className="span-2">Nome *
          <input required value={nome} onChange={evento => setNome(evento.target.value)} />
        </label>
        <label>E-mail *
          <input type="email" required value={email} onChange={evento => setEmail(evento.target.value)} />
        </label>
        <label className="span-2">Senha inicial *
          <input type="password" minLength={8} required value={senha} onChange={evento => setSenha(evento.target.value)} />
        </label>
      </div>
      <div className="form-actions"><button className="primary-button">Criar Operador</button></div>
    </form>
  </>
}
