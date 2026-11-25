# TechStore B2B — TechStock

Sistema de faturamento B2B da TechStore, com catálogo consolidado, controle de
acesso por perfil, PDV multi-itens, recibo e Livro-Razão imutável. Backend Flask
e SQLite em `techstock/`; interface React/TypeScript em `f/`.

## Pré-requisitos

- Python 3.10+ e pip
- Node.js 20.19+ ou 22.12+ e npm (compatíveis com Vite 8)

## Instalação e execução

No terminal do backend:

```powershell
cd techstock
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

No primeiro start, o banco e os dados de demonstração são inicializados.
Opcionalmente defina `TECHSTOCK_SECRET_KEY` para persistir sessões com chave
gerenciada pelo ambiente. Sem ela, o Flask gera e guarda uma chave aleatória
em `techstock/.techstock_secret_key` (ignorada pelo Git). `debug=True` só é
ativado por `FLASK_DEBUG=true`.

No segundo terminal:

```powershell
cd f
npm install
npm run dev
```

O Vite encaminha as chamadas `/api` para `http://127.0.0.1:5000`; abra o
endereço indicado pelo Vite.

## Contas de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Gerente | `gerente@techstore.com` | `demo-techstore-2026` |
| Operador | `operador@techstore.com` | `operador-techstore-2026` |

As senhas são armazenadas como hashes e nunca aparecem no SQL. Somente Gerentes
podem cadastrar operadores, pela tela `f/usuarios/novo` ou pela API autenticada.
O login não oferece cadastro público.

## Roteiro da demo em 6 passos

1. Abrir o catálogo e mostrar Hardware Físico, Licença Digital e alertas de
   reposição (`estoque_atual <= estoque_minimo`).
2. Entrar como Operador e depois Gerente, observando as diferenças de RBAC.
3. Como Operador, registrar no PDV uma venda B2B com três produtos.
4. Conferir o recibo emitido a partir das linhas persistidas e abrir sua versão
   imprimível.
5. Como Gerente, consultar o Livro-Razão e filtrar os lançamentos da venda.
6. Tentar vender duas unidades de `Mouse USB` (saldo inicial: uma unidade);
   a venda deve responder 409 e deixar todo o estado igual. Prova no terminal:

   ```powershell
   cd techstock
   python scripts/demo_rollback.py
   ```

## Modelo e transação

Tabelas: `usuarios`, `categoria`, `fornecedor`, `produtos`,
`ativos_digitais`, `clientes`, `vendas`, `itens_venda` e `movimentacoes`.
`estoque_fisico` é uma VIEW sobre `produtos.estoque_atual`, evitando manter
saldos duplicados. CNPJ, e-mail, SKU e número do pedido têm UNIQUE; preços,
quantidades e subtotais têm CHECK; as FKs são ativadas por conexão.

Vendas usam `BEGIN IMMEDIATE` para serializar baixa concorrente. A falta de
estoque ou qualquer falha em qualquer item executa `ROLLBACK` explícito, sem
deixar cabeçalho, itens, saldo, licenças ou movimentos parciais. Valores
monetários persistidos na venda são centavos inteiros. Triggers tornam
`movimentacoes` append-only.

## Testes

Execute do diretório `techstock`:

```powershell
python -m unittest discover -s tests -v
```

A suíte usa bancos temporários isolados e não remove o `techstock.db` local.
O build do front-end é `cd f; npm run build`.

Mais detalhes do backend e endpoints: [techstock/README.md](techstock/README.md).
