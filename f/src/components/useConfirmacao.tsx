import { useCallback, useRef, useState } from 'react'

interface OpcoesConfirmacao {
  titulo: string
  mensagem: string
  confirmarTexto?: string
  perigo?: boolean
}

function ConfirmacaoModal({
  opcoes,
  aoConfirmar,
  aoCancelar,
}: {
  opcoes: OpcoesConfirmacao | null
  aoConfirmar: () => void
  aoCancelar: () => void
}) {
  if (!opcoes) return null
  return <div className="confirmacao-fundo" onMouseDown={evento => {
    if (evento.target === evento.currentTarget) aoCancelar()
  }}>
    <section className="confirmacao-modal" role="dialog" aria-modal="true" aria-labelledby="confirmacao-titulo">
      <h2 id="confirmacao-titulo">{opcoes.titulo}</h2>
      <p>{opcoes.mensagem}</p>
      <div className="confirmacao-acoes">
        <button type="button" className="confirmacao-cancelar" onClick={aoCancelar}>Cancelar</button>
        <button type="button" className={opcoes.perigo ? 'confirmacao-executar perigo' : 'confirmacao-executar'} onClick={aoConfirmar}>
          {opcoes.confirmarTexto ?? 'Confirmar'}
        </button>
      </div>
    </section>
  </div>
}

export default function useConfirmacao() {
  const [opcoes, setOpcoes] = useState<OpcoesConfirmacao | null>(null)
  const resolver = useRef<((confirmado: boolean) => void) | null>(null)

  const confirmar = useCallback((novasOpcoes: OpcoesConfirmacao) => {
    resolver.current?.(false)
    setOpcoes(novasOpcoes)
    return new Promise<boolean>(resolve => {
      resolver.current = resolve
    })
  }, [])

  const concluir = useCallback((confirmado: boolean) => {
    const resolve = resolver.current
    resolver.current = null
    setOpcoes(null)
    resolve?.(confirmado)
  }, [])

  const modal = <ConfirmacaoModal
    opcoes={opcoes}
    aoConfirmar={() => concluir(true)}
    aoCancelar={() => concluir(false)}
  />

  return { confirmar, modal }
}
