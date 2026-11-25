# TechStore B2B — TechStock

Sistema de inventário e faturamento B2B com Flask, SQLite e front-end React/TypeScript.

## Pré-requisitos

- Python 3.10 ou superior e pip
- Node.js 20.19+ ou 22.12+ e npm (compatíveis com Vite 8)

## Instalação e execução

Terminal 1 — backend:

```powershell
cd techstock
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Na primeira inicialização, o SQLite e os dados de demonstração são criados. Para
usar uma chave de sessão fixa em produção, configure `TECHSTOCK_SECRET_KEY`.
Sem essa variável, uma chave aleatória é persistida em
`.techstock_secret_key` (ignorada pelo Git). O modo debug só é habilitado com
`FLASK_DEBUG=true`.

Terminal 2 — front-end:

```powershell
cd f
npm install
npm run dev
```

O Vite encaminha `/api` para `http://127.0.0.1:5000`. Abra o endereço exibido
pelo Vite.

## Usuários de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Gerente | `gerente@techstore.com` | `demo-techstore-2026` |
| Operador | `operador@techstore.com` | `operador-techstore-2026` |

As senhas são armazenadas no banco como hashes Werkzeug; o SQL nunca contém
senhas. Somente Gerentes podem cadastrar usuários Operador pela tela
`/usuarios/novo` ou pela API autenticada. Promoções e rebaixamentos de perfil
também exigem Gerente.

## Roteiro da demonstração em 6 passos

1. Abrir o catálogo e demonstrar tipos Hardware Físico/Licença Digital e badges
   de `ALERTA` quando o saldo atinge o ponto de reposição.
2. Entrar como Operador e depois Gerente, exibindo as diferenças de acesso
   entre os perfis.
3. Como Operador, registrar pelo PDV uma venda com três produtos para um
   cliente B2B.
4. Conferir o Recibo de Faturamento B2B persistido e abrir a versão imprimível.
5. Como Gerente, filtrar e conferir as três saídas e os relacionamentos no
   Livro-Razão.
6. Tentar vender duas unidades de `Mouse USB`, cujo saldo de demonstração é
   uma unidade; a resposta deve ser 409 e nenhum saldo, venda, item ou
   movimentação pode mudar. Para executar e imprimir o antes/depois:

   ```powershell
   cd techstock
   python scripts/demo_rollback.py
   ```

## Modelo de dados e integridade

As tabelas base são `usuarios`, `categoria`, `fornecedor`, `produtos`,
`ativos_digitais`, `clientes`, `vendas`, `itens_venda` e `movimentacoes`.
`estoque_fisico` é uma VIEW sobre `produtos.estoque_atual`, para não duplicar
saldo; ativos digitais permanecem registrados individualmente e são associados
à venda quando licenciados. CNPJ, e-mail, SKU e número do pedido têm restrições
de unicidade; estoque, quantidades, preços e subtotais têm `CHECK`; FKs são
ativadas em cada conexão.

Venda e movimentação são executadas em `BEGIN IMMEDIATE`: a trava de escrita
é obtida antes de ler o saldo, e cada baixa também exige estoque suficiente no
próprio `UPDATE`. Em vendas, os produtos são processados por `id_produto`
crescente; chaves digitais são marcadas como vendidas somente se ainda não
tiverem `id_venda`. Qualquer falta de saldo ou erro antes do `COMMIT` provoca
`ROLLBACK` explícito do cabeçalho, itens, estoque, licenças e movimentações.
Erros transitórios de bloqueio repetem a transação inteira em até três tentativas.
O front envia `Idempotency-Key` para evitar duplicar uma venda em reenvios; esse
header é opcional para clientes anteriores.

SQLite permite apenas um escritor por vez, portanto a estratégia serializa
gravações e pode limitar throughput sob carga alta; não oferece locks por linha
como PostgreSQL. `BEGIN IMMEDIATE`, o timeout de espera, os retries curtos e
as atualizações condicionais mantêm a integridade em concorrência, mas para
muitas gravações simultâneas o caminho de escala é migrar para PostgreSQL.
O saldo tem `CHECK (estoque_atual >= 0)` e triggers equivalentes para proteger
bancos legados. A migração instala essas triggers sem reescrever saldos; se
encontrar saldo negativo existente, para sem apagar dados para que o Livro-Razão
seja reconciliado primeiro.

Valores de venda são centavos inteiros. Triggers protegem o Livro-Razão, os
itens e as vendas contra alterações e impedem mudar o total depois de fechado.
Recibos de Operador são privados ao autor; Gerentes podem consultar todos.

Se o startup detectar um banco parcialmente criado ou sem triggers esperados,
ele interrompe com erro em vez de apagar conteúdo. Faça backup e remova o banco
manualmente apenas se quiser recriar os dados de demonstração.

## Testes

Rode as suítes a partir do diretório `techstock`:

```powershell
python -m pytest -v
python -m unittest discover -s tests -v
```

Os testes criam e isolam bancos temporários; não apagam nem alteram o arquivo
local `techstock.db`.

## Rotas principais

- `POST /api/login`, `POST /api/cadastro` e `POST /api/logout`
- `POST /api/cadastro` exige sessão Gerente e cria somente perfil `OPERADOR`;
  a interface correspondente fica em `/usuarios/novo`
- `GET /api/dashboard`, `GET /api/produtos/opcoes` e `GET /api/clientes`
- `POST /api/vendas` e `GET /api/vendas/<id>/recibo`
- `GET /api/vendas/<id>/recibo/imprimir`
- `GET /api/livro-razao?venda=<id>`
- `PATCH /api/usuarios/<id>/perfil` (somente Gerente)
