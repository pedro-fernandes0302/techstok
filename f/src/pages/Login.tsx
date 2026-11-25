import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function Login() {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const navegar = useNavigate()
  async function entrar(evento: FormEvent) {
    evento.preventDefault()
    setErro('')
    try {
      await api.login(email, senha)
      navegar('/')
    }
    catch (e) { setErro((e as Error).message) }
  }
  return <main className="login-page"><form className="form-panel" onSubmit={entrar}>
    <h1>TechStock</h1><p>Acesse o sistema B2B</p>
    {erro && <div className="error-banner">{erro}</div>}
    <label>E-mail<input type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label>Senha<input type="password" required value={senha} onChange={e => setSenha(e.target.value)} /></label>
    <button className="primary-button">Entrar</button>
  </form></main>
}
