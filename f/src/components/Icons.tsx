import type { ReactNode } from 'react'

const paths: Record<string, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="10" width="8" height="11" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/></>,
  box: <><path d="M3 8l9-5 9 5v8l-9 5-9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></>,
  entrada: <><path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 17v3h16v-3"/></>,
  saida: <><path d="M12 15V3M7 8l5-5 5 5"/><path d="M4 17v3h16v-3"/></>,
  venda: <><path d="M3 4h3l2 12h10l2-8H7"/><circle cx="9" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/></>,
  fornecedor: <><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M16 5a3.5 3.5 0 010 7M18 14c2 .6 3.5 2.4 3.5 5"/></>,
  usuario: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/></>,
  categoria: <><path d="M3 12l9-9h8v8l-9 9z"/><circle cx="16" cy="8" r="1.5"/></>,
  livro: <><path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M5 17a3 3 0 013-3h11"/></>,
  historico: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  alerta: <><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/></>,
  cifrao: <><path d="M12 2v20M17 6.5C16 5 14.3 4.5 12 4.5c-3 0-4.5 1.3-4.5 3.2 0 5 9.5 2.3 9.5 7.3 0 2-1.8 3.5-5 3.5-2.4 0-4.2-.7-5-2.3"/></>,
  chevron: <path d="M6 15l6-6 6 6"/>,
}

export default function Icon({ nome, tamanho = 18 }: { nome: keyof typeof paths | string; tamanho?: number }) {
  return <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[nome]}</svg>
}
