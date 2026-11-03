# Empório da Música · Agente de Atendimento

Protótipo de um agente de atendimento por mensagens para a **Empório da Música**, uma loja fictícia de instrumentos musicais em Campo Grande/MS. A atendente virtual se chama **Lia**. Ela responde sobre catálogo, preços, estoque, promoções, status de pedidos e políticas da loja (trocas, garantia, pagamento, entrega, horários). Também reconhece quando o assunto foge do escopo e para de gastar tokens com quem insiste nele.

- **Backend (o agente):** Python, FastAPI e LangGraph, com modelos Claude e Postgres + pgvector.
- **Frontend:** uma interface no estilo WhatsApp, com várias conversas isoladas, em Next.js.

![Interface do chat](docs/prints/UI.png)

<!-- ✏️ PREENCHER: salve um print da tela do chat em docs/prints/interface.png -->

---

## Sumário

1. [Como rodar](#como-rodar)
2. [Arquitetura](#arquitetura)
3. [Decisões técnicas](#decisões-técnicas)
4. [Tratamento dos dados e suposições](#tratamento-dos-dados-e-suposições)
5. [Exemplos de conversa](#exemplos-de-conversa)
6. [Testes](#testes)
7. [Limitações conhecidas e próximos passos](#limitações-conhecidas-e-próximos-passos)
8. [Uso de assistentes de código](#uso-de-assistentes-de-código)

---

## Como rodar

### Pré-requisitos

| Ferramenta                | Versão usada                                           |
| ------------------------- | ------------------------------------------------------ |
| Python                    | 3.11                                                   |
| Node.js                   | 22 (o Next 16 exige ≥ 20.9)                            |
| Docker / Docker Compose   | qualquer versão recente                                |
| Chave da API da Anthropic | [console.anthropic.com](https://console.anthropic.com) |

### 1. Banco de dados (Postgres + pgvector)

```bash
cd backend
docker compose up -d
```

O container expõe o Postgres na porta **5433** do host, para não colidir com um Postgres instalado localmente na 5432. Espere o `docker compose ps` mostrar o status `healthy` antes de seguir.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # depois edite e coloque sua ANTHROPIC_API_KEY
python -m scripts.ingest           # carrega CSVs e o PDF de políticas no Postgres (rodar uma vez)
python run.py                      # API em http://localhost:8000
```

O `ingest` baixa o modelo de embeddings (~220 MB) na primeira execução e o guarda em `backend/.cache/`.

> Use `python run.py`, e não `uvicorn app.main:app` direto. No Windows, o driver assíncrono do Postgres (psycopg3) precisa do `WindowsSelectorEventLoopPolicy`, e o `run.py` configura isso antes de subir o servidor.

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local         # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

### Variáveis de ambiente do backend (`backend/.env`)

| Variável                 | Padrão                                                | Para que serve                                                        |
| ------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`      | (obrigatória)                                         | Chave da API da Anthropic                                             |
| `CLAUDE_MODEL`           | `claude-opus-5-5`                                     | Modelo principal do agente                                            |
| `CLAUDE_EFFORT`          | `medium`                                              | Profundidade de raciocínio (`low` a `max`)                            |
| `AUXILIARY_MODEL`        | `claude-haiku-5-5`                                    | Modelo barato usado no classificador de escopo e no resumo            |
| `OUT_OF_SCOPE_THRESHOLD` | `5`                                                   | Quantas mensagens **seguidas** fora do escopo abrem o circuit breaker |
| `SUMMARY_AFTER_TURNS`    | `12`                                                  | A partir de quantos turnos do cliente o histórico é resumido          |
| `REFERENCE_DATETIME`     | vazio                                                 | Relógio simulado (ver abaixo)                                         |
| `DATABASE_URL`           | `postgresql://emporio:emporio@localhost:5433/emporio` | Conexão com o Postgres                                                |
| `FRONTEND_ORIGIN`        | `http://localhost:3000`                               | Origem liberada no CORS                                               |

**Relógio simulado.** Os dados do case são de out/2025 a mar/2026. Para testar prazos de troca e o horário de atendimento de forma reproduzível, `REFERENCE_DATETIME` aceita dois formatos:

- `2026-03-25T10:00`: define data e hora.
- `2026-03-25`: define só a data e mantém a hora real.

O relógio continua andando a partir desse ponto. Se a variável ficar vazia, vale a data e hora reais. Em ambos os casos o horário é sempre o de `America/Campo_Grande`, independente do fuso do servidor.

Para ver o circuit breaker e o resumo de histórico acontecendo rápido pela interface, use `OUT_OF_SCOPE_THRESHOLD=2` e `SUMMARY_AFTER_TURNS=3`. As configurações só são lidas na subida, então reinicie o `run.py` depois de editar o `.env`.

---

## Arquitetura

### Fluxo planejado

![Fluxo de arquitetura](docs/arquitetura-de-fluxo.png)

<!-- ✏️ PREENCHER: exporte o diagrama "Case-Artefact-Archtecture" como PNG e salve em docs/arquitetura.png -->

### Fluxo implementado

O diagrama acima foi o ponto de partida. Abaixo está como ele virou código. As diferenças estão explicadas logo depois.

```mermaid
flowchart LR
    U([Cliente]) -->|texto| UI["Chat UI<br/>(Next.js)"]
    UI -->|POST /chat| API["FastAPI<br/>(views → controllers)"]
    API --> ENTRY

    subgraph LG["Grafo LangGraph (uma thread por conversa)"]
        ENTRY["entry<br/>circuit breaker + memória"]
        CB["circuit_breaker<br/>texto padrão, sem chamar o Opus"]
        AGENT["agent<br/>Claude Opus 5.5<br/>persona Lia + function calling"]
        TOOLS["tools<br/>execução em paralelo"]
        FIN["finalize<br/>conta mensagens fora do escopo"]

        ENTRY -->|"breaker aberto e<br/>Haiku: fora do escopo"| CB
        ENTRY -->|demais casos| AGENT
        AGENT -->|tool_use| TOOLS
        TOOLS --> AGENT
        AGENT -->|resposta final| FIN
    end

    TOOLS -->|"buscar_produtos<br/>consultar_pedido<br/>listar_promocoes"| SQL[("Postgres<br/>tabelas dos CSVs")]
    TOOLS -->|consultar_politicas| VEC[("pgvector<br/>trechos do PDF<br/>busca híbrida")]
    ENTRY -.->|"histórico longo:<br/>resume só turnos no escopo<br/>(Haiku 5.5)"| MEM[("Checkpointer Postgres<br/>histórico da conversa")]
    FIN --> MEM
    CB --> MEM

    AGENT ==>|"stream SSE<br/>(texto, tools, guardrail)"| UI
    CB ==> UI
    UI --> U
```

**Camadas (MVC no backend):**

```
backend/app/
├── views/          # rotas HTTP: POST /chat (stream), GET/DELETE /chats/{id}
├── controllers/    # chat_controller: roda o grafo e converte em stream; memory_manager: histórico → UI
├── agents/         # grafo LangGraph, nós, prompts, tools, classificador de escopo e resumo
├── services/       # acesso a dados (SQL e vetorial), regras de preço, cliente Claude, protocolo de stream
├── models/         # schemas Pydantic da API
└── core/           # configuração, banco e relógio
scripts/ingest.py   # limpeza dos CSVs + chunking e embeddings do PDF
```

**Como uma mensagem percorre o sistema:**

1. **Entrada (`entry`).** A mensagem recebe um cabeçalho com data e hora de Campo Grande, que é gravado no histórico. Se o circuit breaker estiver aberto, o Haiku 5.5 classifica a mensagem: se ela continuar fora do escopo, vai para a resposta padrão; se voltar ao escopo, o breaker fecha. Quando o histórico passa de `SUMMARY_AFTER_TURNS`, ele é compactado.
2. **Agente (`agent` ⇄ `tools`).** O Opus 5.5 decide sozinho quais ferramentas chamar. Ele pode chamar várias em paralelo, por exemplo pedido e política na mesma volta. Cada token de texto e cada chamada de ferramenta é enviado ao navegador assim que é gerado.
3. **Fim do turno (`finalize`).** Se o agente chamou `registrar_fora_de_escopo` no turno, o contador de mensagens seguidas fora do escopo sobe. Se não chamou, o contador zera. Ao atingir o limite, o breaker abre.
4. **Persistência.** O estado inteiro da conversa vai para o checkpointer do Postgres, com `thread_id` igual ao id da conversa no frontend. Por isso cada conversa é isolada e continua existindo depois que o servidor reinicia.

### Diferenças em relação ao fluxo planejado

| No diagrama                                               | No código                                                                                                                                                                                               | Por quê                                                                                                                                                              |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PDF **e CSV** no Vector DB                                | Só o PDF vai para o pgvector. Os CSVs viram tabelas SQL consultadas por ferramentas                                                                                                                     | Preço, estoque e status precisam ser **exatos**. Busca semântica sobre tabelas devolve linhas "parecidas", não a linha certa, e não faz filtros como "até R$ 1.000". |
| Classificação de **toda** mensagem antes do processamento | Com o breaker fechado, o próprio Opus classifica, chamando a ferramenta silenciosa `registrar_fora_de_escopo`. O Haiku só roda enquanto o breaker está aberto                                           | Evita uma chamada extra (e latência) em toda mensagem. O Opus já precisa entender a mensagem para responder, então a classificação sai de graça.                     |
| Memória de longo prazo (Key-Value: fatos e preferências)  | **Não implementada.** Existe memória de curto prazo (histórico + resumo) por conversa                                                                                                                   | Prioridade de escopo, ver [Limitações](#limitações-conhecidas-e-próximos-passos).                                                                                    |
| Bloqueio de prompt malicioso com texto mock               | Regras de segurança no system prompt, ferramentas que só retornam dados após validar a identidade e tratamento de `refusal` do modelo com texto fixo. Não há classificador dedicado de prompt injection | Ver [Limitações](#limitações-conhecidas-e-próximos-passos).                                                                                                          |

---

## Decisões técnicas

### Abordagem do agente: function calling (ReAct) com LangGraph

O agente segue o padrão ReAct com **function calling nativo do Claude**. O modelo raciocina, decide qual ferramenta chamar, recebe o resultado e repete até ter o que responder. O LangGraph orquestra esse laço como um grafo explícito (`entry → agent ⇄ tools → finalize`), em vez de um `AgentExecutor` caixa-preta. Isso trouxe três vantagens:

- **Nós determinísticos em volta do LLM.** O circuit breaker, a compactação de memória e a contagem de mensagens fora do escopo são código Python comum, testável sem chamar a API.
- **Persistência pronta.** O `AsyncPostgresSaver` guarda o estado de cada thread, o que dá histórico por conversa sem eu ter que criar tabelas de mensagens.
- **Streaming customizado.** Com `get_stream_writer()`, cada nó emite eventos no protocolo de stream do Vercel AI SDK. O frontend mostra "consultando catálogo…" enquanto a ferramenta roda e o texto aparece token a token.

Eu chamo o SDK da Anthropic direto dentro do nó, sem o wrapper `ChatAnthropic` do LangChain. Assim tenho acesso imediato a recursos novos da API: adaptive thinking, `effort`, fallback de modelo do lado do servidor, `eager_input_streaming` nas ferramentas e cache de prompt automático.

**Ferramentas (`backend/app/agents/tools.py`):**

| Ferramenta                 | Fonte    | Observações                                                                                                                                                                                                      |
| -------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `buscar_produtos`          | SQL      | Filtros por termo, categoria (enum fechado, para o modelo não inventar categoria), preço máximo e disponibilidade. O preço PIX e o parcelamento já vêm **calculados em Python**.                                 |
| `consultar_pedido`         | SQL      | Exige número do pedido **e** e-mail ou telefone do cadastro. Devolve a mesma mensagem para "não existe" e "não é seu", para não vazar pedidos de terceiros. Já calcula os dias desde a compra e desde a entrega. |
| `listar_promocoes`         | SQL      | Só as promoções vigentes.                                                                                                                                                                                        |
| `consultar_politicas`      | pgvector | RAG sobre o manual em PDF (busca híbrida).                                                                                                                                                                       |
| `registrar_fora_de_escopo` | —        | Ferramenta "silenciosa": não aparece como consulta na UI, alimenta o circuit breaker e mostra um alerta de guardrail.                                                                                            |

**Regras de negócio em código, não no prompt.** O desconto de 5% no PIX (que não se soma com promoção) e as parcelas mínimas por faixa (R$ 50 até 3x, R$ 80 de 4x a 6x, R$ 100 de 7x a 12x) ficam em `services/pricing.py`, que tem testes unitários. O modelo recebe os valores prontos e o prompt manda usá-los em vez de fazer contas. Os valores estão em [docs/conversas/02](docs/conversas/02-preco-takamine-pagamento.md).

### Modelo e provedor: Claude, via API da Anthropic

| Papel                            | Modelo                                                   | Motivo                                                                                                                                                                                     |
| -------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Agente principal                 | **Claude Opus 5.5** (`effort=medium`, adaptive thinking) | Melhor qualidade em uso de ferramentas e em seguir instruções longas de persona e precisão. Aplicar política a um pedido real (datas, prazos, exceções) exige raciocínio em várias etapas. |
| Classificador de escopo e resumo | **Claude Haiku 5.5**                                     | São tarefas simples e frequentes, e a função do breaker é justamente **economizar tokens**. Usa saída estruturada (`messages.parse` com um schema Pydantic).                               |

Outras escolhas de configuração:

- **Fallback de modelo do lado do servidor** (`fallbacks: "default"`), para o atendimento não cair se o modelo principal estiver sobrecarregado.
- **Cache de prompt.** O system prompt é 100% estável e a data e hora vão no cabeçalho de cada mensagem do cliente, não no system prompt. Assim o prefixo (system + tools + histórico) é reaproveitado a cada turno.
- `CLAUDE_MODEL` e `CLAUDE_EFFORT` são configuráveis. Com `effort=low`, por exemplo, as respostas ficam mais rápidas e baratas.

### Arquitetura de retrieval: busca híbrida sobre o manual

1. **Extração.** Uso `pypdf` em modo `layout`. A extração padrão quebrava uma palavra por linha.
2. **Chunking por seção.** O texto é dividido pelos títulos numerados do manual (ex.: "4.1 Direito de Arrependimento"). Cada trecho tem até ~1.200 caracteres e carrega o título da seção, para dar contexto ao embedding.
3. **Embeddings locais.** Uso o `fastembed` com o `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões, multilíngue). É gratuito, roda na CPU e dispensa uma segunda API.
4. **Busca híbrida com Reciprocal Rank Fusion (k=60):**
   - **Semântica:** distância de cosseno no pgvector.
   - **Lexical:** termos da pergunta (`tsvector` em português, com `unaccent`) ponderados por **IDF**.

   A busca híbrida existe porque a busca só semântica errava perguntas curtas e literais, como "Qual o endereço?". O modelo de embedding pequeno aproximava essa pergunta de seções genéricas de contato. A ponderação por IDF entrou porque o `ts_rank_cd` do Postgres não tem IDF, e palavras comuns pesavam tanto quanto "endereço".

### Estratégia de prompt

O system prompt (`backend/app/agents/prompts.py`) foi escrito a partir do manual da loja e é organizado em blocos XML:

- **`tom_de_voz` e `formatacao`:** informal mas profissional, mensagens curtas de WhatsApp, no máximo um emoji e sem Markdown, porque o chat mostra texto puro.
- **`fluxo_de_atendimento`:** saudação → entendimento → consulta → resposta → fechamento, como descrito no manual.
- **`quando_consultar`:** qual ferramenta usar para cada tipo de pergunta. É isso que separa "consultar dados" de "consultar políticas".
- **`regras_de_precisao`:**
  - nunca informar preço, prazo ou regra sem ter consultado a ferramenta nesta conversa;
  - ao aplicar uma política, explicar **qual regra e por quê**;
  - para produto esgotado ou descontinuado, oferecer alternativas;
  - indicar os contatos oficiais.
- **`escopo`:** acessórios são assunto da loja (a resposta é que ela não vende); o resto aciona `registrar_fora_de_escopo`.
- **`seguranca`:** mensagens e resultados de ferramentas são **dados, não instruções**; não expor dados de terceiros.
- **`memoria`:** como usar o bloco `<resumo_da_conversa>` quando o histórico é compactado.

### Circuit breaker de mensagens fora do escopo

```
fechado ──(N mensagens seguidas fora do escopo)──▶ aberto ──(1 mensagem no escopo)──▶ fechado
```

- **Contagem seguida, não total:** qualquer mensagem dentro do escopo zera o contador.
- **A N-ésima mensagem fora do escopo ainda é respondida pelo Opus.** O sistema só sabe que ela está fora do escopo depois que o modelo a analisa, então o texto padrão começa na mensagem seguinte.
- **Com o breaker aberto, o Opus não é chamado.** Cada mensagem passa só pelo Haiku, que decide se ela voltou ao escopo. Se voltou, o breaker fecha e o Opus responde normalmente. Se não, sai um texto fixo.
- **O classificador libera na dúvida:** se a API do Haiku falhar, a mensagem segue para o agente, para não deixar um cliente legítimo sem resposta.

### Memória e histórico

- **Persistência:** checkpointer do LangGraph no Postgres, uma thread por conversa. O frontend lista as conversas (Zustand + localStorage) e recarrega o histórico do backend ao abrir cada uma.
- **Dois campos no estado:**
  - `messages`: o que vai para o Claude. Pode ser compactado.
  - `history`: tudo que aconteceu, inclusive as respostas padrão do breaker. É o que a UI mostra.
- **Resumo só com os turnos no escopo.** Quando o histórico passa de `SUMMARY_AFTER_TURNS` turnos, o Haiku resume a conversa **ignorando os turnos marcados como fora do escopo**, e o transcript passa a ser `resumo + nova mensagem`. Substituo tudo, em vez de "resumo + últimas N mensagens", porque o Opus 5.5 preserva o raciocínio entre turnos e recusa com erro 400 um histórico editado no meio. Trocar o histórico inteiro de uma vez é o formato que ele aceita.

### Interface: Next.js no estilo WhatsApp

O case dizia que o foco era o agente, e o agente está todo em Python. Mesmo assim, fiz uma UI porque o cenário é atendimento por mensagens, e uma interface parecida com o canal real deixa mais fácil avaliar tom, ritmo e uso de ferramentas.

A comunicação usa o **protocolo de stream de mensagens do Vercel AI SDK** (SSE), implementado do zero no FastAPI (`services/ui_stream.py`). Com isso o hook `useChat` do frontend funciona sem adaptadores.

Stack do frontend: Next.js 16 (App Router), AI SDK v7, Zustand, Tailwind v4, shadcn/ui, com modo escuro.

---

## Tratamento dos dados e suposições

O enunciado pede para assumir interpretações razoáveis e documentá-las. Estas foram as minhas:

**Limpeza feita no `scripts/ingest.py`:**

- Espaços removidos das pontas dos textos e e-mails em minúsculas.
- Telefones normalizados só com dígitos, para casar `(67) 99812-3456` com `67998123456`.
- `specs` convertido de JSON para `JSONB`, datas para `DATE` e `is_active` para booleano.

**Suposições sobre os dados:**

| Situação encontrada                                                                             | Decisão                                                                                                                                    |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| E-mail duplicado entre clientes                                                                 | A identidade é confirmada pelo **par** número do pedido + e-mail ou telefone do dono daquele pedido, nunca só pelo e-mail.                 |
| `order_items` não tem preço unitário, e o preço atual do produto pode ter mudado desde a compra | `total_brl` é tratado como o valor efetivamente cobrado. O agente não recalcula o pedido pelo preço de hoje.                               |
| Produto inativo com estoque, ou ativo com estoque zero                                          | O status vale mais que o estoque: um produto inativo é apresentado como "saiu do catálogo" e não tem preço exibido.                        |
| Categorias sem nenhum produto                                                                   | O agente diz que não encontrou e oferece alternativas, sem inventar nada.                                                                  |
| O manual traz contatos diferentes em seções distintas                                           | Fixei no prompt os contatos do canal de atendimento: WhatsApp (67) 3321-4500, telefone (67) 3341-4444 e contato@emporiodamusica.com.br.    |
| Não existe data de entrega real, só a `estimated_delivery`                                      | A data estimada é usada como aproximação do recebimento, e o agente diz "aproximadamente" ao calcular prazos de arrependimento e garantia. |
| A parcela mínima até 3x é ambígua no manual                                                     | Interpretada como R$ 50.                                                                                                                   |
| Marca no nome diferente da marca na descrição (ex.: "Yamaha Bass 3X" descrito como Ibanez)      | Mantido como está no CSV, sem corrigir os dados de origem. O agente apresenta o produto pelo nome cadastrado.                              |
| Dados de out/2025 a mar/2026                                                                    | Criei o relógio simulado (`REFERENCE_DATETIME`) para que os prazos façam sentido em uma demonstração.                                      |

---

## Exemplos de conversa

As conversas em [`docs/conversas/`](docs/conversas/) foram **geradas pelo agente real** (Opus 5.5 + banco populado) e transcritas sem edição. Cada arquivo registra o relógio simulado usado e as ferramentas chamadas em cada turno.

| #   | Cenário                                                                                           | O que demonstra                                                                                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | [Violões até R$ 1.000](docs/conversas/01-catalogo-violoes.md)                                     | Filtro de catálogo por categoria e preço; recomendação para iniciante usando só o que veio da consulta                                                                                                                                          |
| 2   | [Quanto custa o Takamine GD20?](docs/conversas/02-preco-takamine-pagamento.md)                    | Preço, PIX e parcelamento calculados em código; política de pagamento via RAG                                                                                                                                                                   |
| 3   | [Me arrependi, posso devolver?](docs/conversas/03-devolucao-pedido.md)                            | **Não trivial:** validação de identidade e consulta do pedido real em paralelo com a política. O agente aplica os prazos de arrependimento (7 dias), troca na loja (30 dias) e garantia legal (90 dias) às datas do pedido e explica cada regra |
| 4   | [Endereço e horário num sábado à tarde](docs/conversas/04-endereco-horario-fora-do-expediente.md) | Informações gerais via RAG combinadas com o relógio simulado: o agente percebe que a loja já fechou e diz quando reabre                                                                                                                         |
| 5   | [Fora do escopo + circuit breaker](docs/conversas/05-fora-do-escopo-circuit-breaker.md)           | Recusa educada, breaker abrindo (limite 2 no teste), resposta padrão sem chamar o Opus e retomada automática quando o cliente volta ao assunto                                                                                                  |

**Prints da interface:**

<!-- ✏️ PREENCHER: tire os prints rodando os mesmos cenários na UI e salve em docs/prints/ com estes nomes -->

| Consulta de pedido com política                | Circuit breaker                                       |
| ---------------------------------------------- | ----------------------------------------------------- |
| ![Devolução](docs/prints/caso-nao-trivial.png) | ![Circuit breaker](docs/prints/circuit-breaker-2.png) |

---

## Testes

```bash
cd backend
pytest
```

Os testes não chamam a API do Claude e não precisam do banco. Eles cobrem:

- **Preços:** desconto PIX, promoção que não se soma com PIX, parcelas máximas por faixa.
- **Circuit breaker:** contagem de mensagens seguidas, abertura ao atingir o limite, mensagem no escopo zerando o contador e o histórico que só cresce, exceto na compactação.
- **Resumo:** só os turnos no escopo entram no texto resumido, e uma conversa inteira fora do escopo gera um resumo vazio sem chamar a API.
- **Relógio simulado:** data e hora, só data e relógio andando.
- **Conversão do histórico para o formato da UI.**

O fluxo completo, com o modelo real, foi validado pelas conversas de exemplo acima.

---

## Limitações conhecidas e próximos passos

| Limitação                                                                                          | O que eu faria com mais tempo                                                                                                                                                                               |
| -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sem memória de longo prazo** (fatos e preferências do cliente entre conversas, como no diagrama) | Extrair fatos com o Haiku ao final de cada conversa e salvar por cliente (identificado pelo telefone do WhatsApp) no `Store` do LangGraph, injetando-os no início das próximas.                             |
| **Sem classificador dedicado de prompt injection ou conteúdo malicioso**                           | Hoje a defesa está no prompt, nas ferramentas (identidade validada em código) e no tratamento de `refusal`. Eu adicionaria um classificador leve na entrada, com bloqueio e texto padrão, como no diagrama. |
| **Fora do escopo detectado pelo próprio agente**                                                   | Com o breaker fechado, a decisão depende do Opus chamar `registrar_fora_de_escopo`. Se ele responder sem chamar a ferramenta, a mensagem não conta. Eu montaria um conjunto de avaliação para medir isso.   |
| **Sem avaliação automatizada de qualidade**                                                        | Criar um conjunto de perguntas com respostas esperadas (preços, prazos, recusas) e rodar LLM-as-judge mais checagens exatas de valores a cada mudança de prompt.                                            |
| **Busca de produtos por palavras** (`LIKE` normalizado)                                            | Para perguntas vagas ("algo pra tocar em roda de samba"), adicionar embeddings das descrições de produto e combinar com os filtros SQL.                                                                     |
| **Data de entrega aproximada**                                                                     | Integrar com o rastreio real dos Correios (`tracking_code`) para ter a data efetiva de recebimento.                                                                                                         |
| **Sem autenticação** e conversas listadas no `localStorage` do navegador                           | Em produção, o canal seria o próprio WhatsApp (Cloud API), com o telefone como identidade do cliente.                                                                                                       |
| **Sem handoff para humano**                                                                        | Criar uma ferramenta `transferir_para_atendente` que abre um ticket e pausa o agente naquela conversa.                                                                                                      |
| **Observabilidade**                                                                                | Rastrear chamadas, tokens e latência (LangSmith ou OpenTelemetry) e montar um painel de custo por conversa.                                                                                                 |
| Os limites do breaker e do resumo são globais                                                      | Torná-los ajustáveis por canal ou por perfil de cliente.                                                                                                                                                    |

---

## Uso de assistentes de código

<!-- ✏️ PREENCHER/REVISAR: esta seção descreve o seu workflow. Ajuste com as suas palavras, porque o avaliador quer entender como VOCÊ trabalhou. -->

Usei o **Claude Code** (extensão do VS Code, modelo Claude Opus 5.5) como par de programação durante todo o projeto.

**Como dividi o trabalho:**

- **Decisões minhas:**
  - A arquitetura: o fluxo do diagrama, MVC, UI estilo WhatsApp com conversas isoladas e circuit breaker de 5 mensagens.
  - A stack: Next.js + AI SDK no front, FastAPI + LangGraph no back, Postgres + pgvector, família Claude.
  - Os requisitos de cada etapa. Eu pedia uma funcionalidade por vez, por exemplo: "o resumo deve considerar só mensagens dentro do contexto", "quero controlar o tempo pelo `.env`".
- **Papel do assistente:**
  - Montar a estrutura de pastas.
  - Implementar cada etapa.
  - Rodar o código de verdade (build do Next, ingestão, testes e conversas de ponta a ponta com a API) e me reportar os resultados.
- **Revisão e commits:** eu revisava o diff e fazia os commits, divididos por etapa (`feat(frontend)…`, `feat(backend)…`). O assistente não tinha permissão para commitar.

**Onde o assistente mais ajudou:**

- implementar o protocolo de stream do AI SDK no FastAPI.
- diagnosticar o conflito de porta com um Postgres local e o erro 401 da chave (eu esqueci do uso da porta).
- perceber que a busca semântica errava "Qual o endereço?" e propor a busca híbrida com IDF.

**Onde eu precisei intervir ou corrigir:**

- decisões de produto, ajustes visuais (fonte arredondada, modo escuro), mudanças de escopo do breaker, ajustes no modelo de classificação e outros.

**Cuidados que tomei:**

- A chave da API ficou só no `.env`, que está no `.gitignore`, e o assistente foi instruído a não ler esse arquivo.
- validei manualmente as respostas de preço contra os CSVs.
