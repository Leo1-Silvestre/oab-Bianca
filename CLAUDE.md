# Tutoria OAB da Bianca

Site estático (HTML/CSS/JS puro, sem framework, publicado no GitHub Pages a
partir de `docs/`) que funciona como plataforma de tutoria de estudos para a
Bianca, esposa do usuário, que está estudando para o Exame da OAB.

**Prova: 10/01/2027.** A Bianca só precisa abrir o link, sentar e estudar —
tudo já vem pronto, sem ela precisar organizar nada.

Se o usuário disser algo como **"gera a próxima semana"**, siga o fluxo
descrito em [Como gerar a próxima semana](#como-gerar-a-próxima-semana)
abaixo, sem precisar reexplicar nada disso.

## Visão geral do projeto

- Os PDFs de estudo ficam no Google Drive, em `Bianca/OAB/<Matéria>/`,
  acessados pelo conector MCP do Google Drive. Cada pasta de matéria tem um
  PDF **Revisão** (resumo em tabelas) e um PDF **Gabaritaço** (dicas
  numeradas + questões comentadas, mais denso). Ética tem também um
  **Aulão** complementar.
- 9 matérias rodam em paralelo desde a semana 1, cada uma no seu próprio
  ritmo de blocos temáticos (não é uma matéria de cada vez).
- Outras matérias da OAB (Empresarial, Ambiental, Consumidor, ECA, Direitos
  Humanos, Filosofia, Internacional, Trabalho substantivo) **não** entram
  neste cronograma.

## As 9 matérias e a grade semanal fixa

| Dia | Matéria(s) |
|---|---|
| Segunda | Constitucional 🏛️ + Ética ⚖️ |
| Terça | Civil 📜 + Processo Civil ⚙️ |
| Quarta | Penal 🔒 + Processo Penal 👮 |
| Quinta | Administrativo 📋 + Ética ⚖️ |
| Sexta | Tributário 💰 + Processo do Trabalho 🛠️ |
| Sábado | Revisão geral (ver algoritmo de revisão espaçada) |
| Domingo | Livre — sem conteúdo |

Ética aparece 2x/semana (segunda e quinta) por ser a matéria de maior peso
isolado na prova e ter muito conteúdo de decoreba normativa — por isso ela
avança **dois blocos por semana** em vez de um.

Cores/ícones por matéria (usados em `content/state.json` → `subjects.<slug>.color/icon`):

| Slug | Nome | Cor | Ícone |
|---|---|---|---|
| `constitucional` | Constitucional | `#3b82f6` | 🏛️ |
| `administrativo` | Administrativo | `#14b8a6` | 📋 |
| `civil` | Civil | `#f59e0b` | 📜 |
| `processoCivil` | Processo Civil | `#6366f1` | ⚙️ |
| `penal` | Penal | `#dc2626` | 🔒 |
| `processoPenal` | Processo Penal | `#e11d48` | 👮 |
| `etica` | Ética | `#8b5cf6` | ⚖️ |
| `processoDoTrabalho` | Processo do Trabalho | `#f97316` | 🛠️ |
| `tributario` | Tributário | `#16a34a` | 💰 |

## Roteiro de blocos temáticos por matéria

Cada matéria foi dividida (lendo os PDFs originais) em blocos temáticos, em
ordem pedagógica (do mais fundamental para o mais específico). Essa lista
completa está em `content/state.json` → `subjects.<slug>.blocks` (cada
bloco tem `id`, `title`, `desc`). **Não invente blocos novos** — siga essa
ordem já mapeada. Resumo do tamanho de cada roteiro e da semana estimada de
conclusão do 1º ciclo (assumindo 1 bloco novo/semana, ou 2/semana para
Ética):

| Matéria | Nº de blocos | Semana estimada de conclusão do 1º ciclo |
|---|---|---|
| Constitucional | 12 | 12 |
| Administrativo | 10 | 10 |
| Civil | 13 | 13 |
| Processo Civil | 13 | 13 |
| Penal | 11 | 11 |
| Processo Penal | 9 | 9 |
| Ética | 24 (2/semana) | 12 |
| Processo do Trabalho | 9 | 9 |
| Tributário | 11 | 11 |

Nenhuma matéria termina depois da semana 13, dentro do orçamento de 17
semanas até a prova — sobra folga antes da fase de revisão pura (ver
abaixo). Se, ao gerar uma semana futura, uma matéria estiver visivelmente
atrasada em relação ao tempo restante até a prova, sinalize isso na própria
página (elemento `.flag-behind` no topo — adicione a classe `show` e um
texto curto e não alarmante) e considere ajustar o ritmo dela (ex.: agrupar
2 blocos numa mesma semana).

## Algoritmo de revisão espaçada

Guardado em `content/state.json` → `progress.<slug>.<blockId>`:
`{firstStudiedWeek, reviews: [semanas em que foi revisado], nextReviewWeek}`.

Intervalos (`reviewIntervals` = `[1, 3, 6]`, depois `reviewFixedInterval` = `9`):
- 1ª revisão: 1 semana depois do primeiro estudo.
- 2ª revisão: 3 semanas depois da 1ª revisão.
- 3ª revisão: 6 semanas depois da 2ª revisão.
- Depois disso: a cada ~9 semanas até a prova (ajustável conforme o tempo
  restante).

Ao montar uma semana N: para cada matéria, no dia normal dela na grade, o
`scripts/generate_week.py` decide automaticamente (função `decide_week`):
1. Se ainda há bloco novo no roteiro **e** a semana é antes da fase de
   revisão pura → introduz o próximo bloco não estudado.
2. Se, além disso, algum bloco já estudado tem `nextReviewWeek <= N` →
   anexa também uma seção "🔁 Revisão rápida" (15-20 min) daquele bloco,
   além do conteúdo novo (aditivo, nunca substitui).
3. Se não há bloco novo (matéria já terminou o 1º ciclo, ou estamos na fase
   de revisão pura) mas há algo vencido → o slot da semana vira 100%
   revisão daquele bloco.
4. No sábado, o script varre TODAS as matérias por blocos ainda vencidos
   que não foram cobertos nos dias de semana e monta a revisão geral. Se
   nada estiver vencendo, o sábado consolida os blocos novos da própria
   semana.

`pureReviewFromWeek` (hoje = 15, ou seja, semanas 15-17) marca o início da
fase final: nenhuma matéria recebe conteúdo novo, só revisão geral,
priorizando os blocos mais antigos/menos revisados.

## Estado atual

- Semana atual gerada: **Semana 1** (`content/state.json` → `currentWeek: 1`).
- `startDate`: `2026-09-14` (segunda-feira da semana 1). `examDate`:
  `2027-01-10`. `weeksTotal`: 17 (recalculado a cada nova semana gerada —
  ver script).
- Semana 1: cada matéria estudou seu bloco 1 (Ética estudou blocos 1 e 2,
  segunda e quinta). Nenhuma revisão ainda (é o início). Todas com
  `nextReviewWeek: 2`.
- Conteúdo (teoria + lei seca) já escrito para os blocos citados acima está
  em `subjects.<slug>.blockContent.<blockId>`.

## Arquitetura técnica

```
content/state.json      ← fonte de verdade: matérias, roteiro de blocos,
                           conteúdo (teoria/lei seca) já escrito por bloco,
                           progresso de revisão espaçada, semana atual.
docs/                    ← publicado pelo GitHub Pages.
  index.html             ← redireciona (meta refresh) para a semana mais
                           recente e lista todas as semanas já geradas.
  semana-01.html          , semana-02.html, ... ← uma página por semana,
                           HTML puro, com CSS/JS compartilhados.
  style.css               estilos compartilhados (mobile-first, cores por
                           matéria via `--subj-color`, dark mode via
                           prefers-color-scheme).
  app.js                  lógica compartilhada sem framework:
                           OAB.initCountdown(examDate) → calcula dias/semanas
                             restantes a partir da data real do navegador.
                           OAB.initToday() → destaca/expande o <details> do
                             dia cujo data-date bate com a data real; os
                             demais dias ficam colapsados (visíveis, mais
                             discretos).
                           OAB.initChecklist(prefix) → carrega/salva o estado
                             de cada checkbox em localStorage, namespaced por
                             semana:dia:matéria:tipo:blockId, e atualiza a
                             barra de progresso da semana.
scripts/
  generate_week.py       ← gerador reutilizável (ver seção abaixo).
```

Cada checkbox (Teoria / Lei seca / Questões / Revisão) tem um
`data-check-id` único no formato `s{semana}:{dia}:{matéria}:{tipo}:{blockId}`,
salvo em `localStorage` sob a chave `oab-bianca-s{semana:02d}:{check-id}` —
isso mantém o progresso isolado por semana e nunca mistura entre semanas.

O placeholder de questões segue exatamente o padrão pedido:
`<!-- LINK_TECCONCURSOS_<MATERIA_MAIUSCULA>_SEMANA<NN> -->` dentro de
`.questions-box` em cada card de matéria — troque manualmente pelo link real
do TecConcursos quando o usuário mandar.

## Como gerar a próxima semana

Quando o usuário pedir para gerar a próxima semana (ex.: "gera a semana 2"):

1. **Rode o script em modo de verificação primeiro:**
   ```
   python3 scripts/generate_week.py <N>
   ```
   Ele decide sozinho (a partir de `content/state.json`) o que cada matéria
   estuda naquele dia daquela semana — conteúdo novo e/ou revisão vencida —
   sem inventar teoria nenhuma. Se algum bloco necessário ainda não tem
   `blockContent` escrito, ele **para** e imprime exatamente quais blocos
   (matéria + id + título) precisam de conteúdo antes de continuar.

2. **Para cada bloco listado como faltante**, leia os PDFs da matéria em
   `Bianca/OAB/<Matéria>/` no Google Drive (Revisão + Gabaritaço, e Aulão
   para Ética) e escreva, em `content/state.json` →
   `subjects.<slug>.blockContent.<blockId>`, um objeto:
   ```json
   {
     "teoria": "resumo estilo professor, 300-450 palavras (250-400 para Ética, que tem sessões mais curtas)",
     "referencia": "qual material consultar para aprofundar (ex: Gabaritaço - X, Dicas N a M)",
     "lei_seca": [["Art. X, Lei Y", "resumo de 1 linha do que trata"], ...]
   }
   ```
   Use o `title`/`desc` já mapeados em `subjects.<slug>.blocks` como guia do
   que aquele bloco deve cobrir — não precisa remapear o roteiro. Para
   blocos de revisão (já estudados antes), o `blockContent` já existe desde
   quando o bloco foi novo — nada a fazer.

   Dica: como isso envolve ler vários PDFs de matérias diferentes, dá para
   paralelizar com subagentes (um por matéria pendente), do mesmo jeito que
   foi feito para montar a semana 1 — cada um devolve teoria + lei seca do
   bloco pedido.

3. **Rode o script de novo.** Agora ele aplica o plano de verdade: atualiza
   `progress` (novos `firstStudiedWeek`/`reviews`/`nextReviewWeek`),
   atualiza `currentWeek`, gera `docs/semana-NN.html` e re-gera
   `docs/index.html` (lista de semanas + redirecionamento).

4. **Antes de gerar**, recalcule `weeksTotal` em `content/state.json` a
   partir da data do sistema até `examDate` (dias restantes / 7,
   arredondado) — o ritmo do cronograma depende de quanto tempo falta.
   Se a folga entre "semana estimada de conclusão do 1º ciclo" (tabela
   acima) e `weeksTotal - 3` estiver ficando apertada para alguma matéria,
   considere acelerar o ritmo dela (2 blocos numa mesma semana) e sinalize
   via `.flag-behind`.

5. Confira visualmente (ex.: `python3 -m http.server` dentro de `docs/` e
   abrir no navegador, ou tirar um screenshot) antes de dar commit.

6. Commit + push para o branch de trabalho.

## Padrão visual

- Mobile-first, tipografia legível para leitura longa (`font-size: 17px`
  base, `line-height: 1.65`), paleta quente (fundo off-white/creme,
  cartões brancos com sombra leve), suporte a dark mode via
  `prefers-color-scheme`.
- Cada matéria tem cor + ícone fixos (tabela acima), aplicados como borda
  esquerda colorida + nome colorido no card — dá pra identificar a matéria
  num relance.
- Cada dia é um `<details class="day" data-date="YYYY-MM-DD">` — o dia
  atual (calculado no browser via `app.js`) fica expandido e destacado
  (borda roxa, sombra maior); os demais ficam colapsados mas visíveis
  (resumo com chips das matérias do dia).
- Dentro de cada dia, os cards de matéria ficam lado a lado em telas ≥620px
  (`.subject-grid.two-col`) e empilhados no mobile.
- Cada card de matéria tem, nesta ordem: 📘 Teoria do dia, 📖 Lei Seca do
  dia, (🔁 Revisão rápida quando aplicável), ✍️ Questões (placeholder
  TecConcursos) — cada um com seu próprio checkbox.
- Barra de progresso no topo soma todos os checkboxes da semana (todas as
  matérias, todos os dias, incluindo sábado).
- Sábado consolida (ícone 🔁, chip cinza) tudo que estiver vencendo na
  semana, ou os blocos novos da própria semana quando nada vence ainda.
- Domingo é uma seção simples sem checkboxes, convite ao descanso.

## Referências úteis do Google Drive

Pasta raiz: `Bianca/OAB/` (id `19nedqwPhO7MBJdfqVGeyZveEvgH5Dxfn`), com uma
subpasta por matéria (mesmo nome da matéria). Use
`mcp__Google_Drive__search_files` com `parentId = '<id da pasta>'` para
listar os PDFs de uma matéria, e `mcp__Google_Drive__read_file_content`
para ler o conteúdo. Os PDFs de Gabaritaço (principalmente Civil e
Processo Civil) são grandes — pode ser necessário ler em partes/focar no
sumário para blocos mais avançados no roteiro.
