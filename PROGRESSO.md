# Progresso do Projecto — Diário de Alterações

Este ficheiro regista, por ordem cronológica, todas as decisões e alterações
feitas ao código e à rede deste PFC. Serve de complemento ao `CLAUDE.md`
(que descreve o estado e as regras fixas do projecto) — aqui fica o histórico
do que foi mudando e porquê.

---

## 2026-09-13 — Sessão 1: contexto e planeamento

- Lido o `CLAUDE.md` por completo (contexto do PFC, arquitectura fechada,
  regras de trabalho).
- Confirmada a estrutura de ficheiros existente. `agente_dqn/` descrito no
  `CLAUDE.md` como já testado **não existia neste ambiente** (foi testado
  noutro ambiente, sem acesso à internet) — este ambiente parte do zero para
  o código do agente.
- Traçado o plano de trabalho em 4 fases: Fase 0 (rede real), Fase 1
  (código do agente), Fase 2 (integração), Fase 3 (testes), Fase 4 (treino
  completo e comparação com baseline).
- Decidido com o autor: rede real primeiro; número de episódios de treino
  fica em aberto até ao teste de fumo.

## 2026-09-13 — Sessão 1: Fase 0, georreferenciação da rede

**Problema:** a rede em `net/` estava construída manualmente (secção 5 do
`CLAUDE.md`), com coordenadas locais, não reais.

**Processo:**
1. `SUMO_HOME` confirmado instalado (`C:\Program Files (x86)\Eclipse\Sumo`).
2. `osmWebWizard.py` (interactivo, exige browser) não é viável nesta sessão
   não interactiva. Usada a alternativa por linha de comando: `osmGet.py` +
   `osmBuild.py`/`netconvert`, tal como decidido com o autor.
3. `osmGet.py` falhou (Overpass API principal deu HTTP 504). Contornado com
   pedido directo à Overpass API pública via `curl`, gerando um extracto XML
   no formato que o `netconvert` aceita directamente com `--osm-files`.
4. Geocodificação confirmou a localização: Avenida Eduardo Mondlane em
   Polana Cimento "B" (~-25.971, 32.589), junto à Av. Salvador Allende, tal
   como descrito no `CLAUDE.md`.
5. **Descoberta estrutural importante:** neste troço real, a Avenida Eduardo
   Mondlane não é uma via bidireccional única, é um par de vias de sentido
   único (3 faixas cada), típico de "avenida com separador central". O
   cruzamento com a Av. Salvador Allende (1 faixa/sentido) aparece assim
   como um nó com **apenas 3 vias de entrada**, não as 4 aproximações
   ortogonais que a rede manual e o `CLAUDE.md` assumiam. Também não estava
   marcado como semáforo no OpenStreetMap.
6. Testadas duas extracções (bbox pequeno ~350m e bbox largo ~2km) para
   confirmar que a topologia de 3 entradas é uma característica real do
   terreno, não um artefacto do recorte. Confirmado nas duas.
7. **Decisão do autor (explícita, pedida via pergunta directa):** adaptar o
   modelo a 3 aproximações reais, em vez de forçar uma 4.ª aproximação
   artificial ou manter a rede manual antiga.
   - Isto implica alterar o espaço de estados de 9 para **7 valores** (3
     filas + 3 tempos de espera acumulados + 1 fase actual do semáforo).
   - **Ainda por fazer:** actualizar o Capítulo II (secção 2.4.2) e Capítulo
     IV do PFC para reflectir esta mudança, como pedido na secção 7 do
     `CLAUDE.md`. Não escrito ainda, à espera de indicação do autor para
     tocar no texto da tese.
8. Rede final gerada com `netconvert`:
   - Extracção Overpass alargada (~2km) para permitir a fusão automática
     dos nós próximos (`12168401392` e `1783252720`) num único junction
     (`cluster_12168401392_1783252720`).
   - Recortada de volta para uma área útil (~800m×400m) com
     `--keep-edges.in-boundary`, mantendo o junction fundido.
   - Adicionado semáforo ao junction com `--tls.set` (a rede OSM não tinha
     nenhum sinalizado aqui).
   - Ficheiro final: `net/eduardo_mondlane_salvador_allende.net.xml`
     (substituiu a versão manual, agora arquivada em `net/manual_backup/`).
   - **Nota:** o `netconvert` gerou 6 fases genéricas por defeito para o
     semáforo. Estas ainda não correspondem ao ciclo fixo do baseline
     (42s + 42s + 2×3s de amarelo) — fica para a Fase 1.
   - Ficheiros intermédios da extracção OSM guardados em `net/osm_real/`
     para referência (não fazem parte da configuração activa).

**Pendente antes de correr simulações com a rede nova:**
- Reescrever `routes/routes.rou.xml` com os IDs de aresta reais (os antigos
  `EM_W_in`, `EM_E_in`, `SA_N_in`, `SA_S_in` não existem na rede real).
- Redefinir as fases do semáforo (`tlLogic`) para 4 fases fixas (verde EM,
  amarelo, verde SA, amarelo), coerentes com o baseline.

## 2026-09-13 — Sessão 1: repositório GitHub

- Instalado o GitHub CLI (`winget install GitHub.cli`), não estava presente
  nesta máquina.
- Autenticado via `gh auth login --web` (conta `Shads-GoldenCorsair`).
- Criado repositório **privado** no GitHub e enviado o estado actual do
  projecto (ver `README.md`/secção de repositório para o link).

---

## 2026-09-13 — Sessão 1: Fase 1, código do agente e rotas reais

- `routes/routes.rou.xml`, `routes/demanda_pico.rou.xml` e
  `routes/demanda_baixo_fluxo.rou.xml` reescritos com os IDs de aresta
  reais da rede OSM (3 aproximações: `EM1`/`EM2`/`SA`, ver `sumo_env.py`).
  Os volumes de veículos por movimento foram redistribuídos pelos
  movimentos que existem fisicamente na interseção real (ex.: o volume de
  "viragem à direita" que antes existia em Eduardo Mondlane ramo 1 não
  tem correspondência real, foi somado ao volume "em frente" desse ramo;
  os volumes que antes eram de duas aproximações opostas de Salvador
  Allende, agora uma única aproximação real, foram somados). Documentado
  em comentário no topo de cada ficheiro.
- Validado com `sumo -c pico.sumocfg` e `sumo -c baixo_fluxo.sumocfg`: sem
  erros, sem avisos relativos ao nosso semáforo.
- `tlLogic` do semáforo real (`cluster_12168401392_1783252720`), gerado
  pelo `netconvert` com 6 fases (incluindo uma sub-fase protegida para a
  viragem à esquerda), simplificado para 4 fases fixas, coincidindo com o
  ciclo do baseline descrito no `CLAUDE.md`: 42s verde EM, 3s amarelo, 42s
  verde SA, 3s amarelo.
- **Bloqueador resolvido:** TensorFlow ainda não suporta Python 3.14 (o
  único instalado nesta máquina). Instalado Python 3.11 (`winget install
  Python.Python.3.11`) só para o ambiente virtual do agente
  (`agente_dqn/.venv`), sem alterar o Python do sistema. `traci` importado
  directamente de `%SUMO_HOME%/tools` (não precisa de `pip install`).
- Criados `agente_dqn/sumo_env.py`, `dqn_agent.py`, `train.py`,
  `requirements.txt`, `README.md`, conforme a arquitectura do `CLAUDE.md`:
  - Estado: vector de **7** valores (3 filas + 3 esperas + 1 fase),
    reduzido de 9 porque a interseção real tem 3 aproximações, não 4
    (decisão do autor, ver secção "Fase 0" acima).
  - Acção binária (manter/mudar fase), recompensa
    `-soma(esperas) - 5.0` se mudou de fase.
  - Rede: MLP 7→64→64→2, replay buffer de 10000, rede-alvo actualizada a
    cada 5 episódios, exactamente como especificado.
- Auto-testes (`demo()`) em `sumo_env.py` e `dqn_agent.py`, ambos passam.
- Teste de fumo (3 episódios, 1 semente, cenário baixo fluxo) corrido para
  decidir o número de episódios do treino completo — resultado registado
  na próxima entrada deste ficheiro.

## 2026-09-13 — Sessão 1: teste de fumo e optimização de velocidade

- Primeiro teste de fumo (3 episódios, cenário baixo fluxo): pipeline
  completo funciona de ponta a ponta. Recompensa por episódio: -2502.0,
  -2139.0, -2173.0. O valor do 1.º episódio (-2502) confere quase
  exactamente com o -2501 já registado no `CLAUDE.md` (secção 4, testado
  noutro ambiente), o que confirma que a lógica do agente está correcta.
- **Problema de desempenho encontrado:** cada episódio demorou cerca de
  12 minutos (700-800s), porque o agente decidia e treinava a cada
  segundo simulado (3600 chamadas ao TensorFlow por episódio). A este
  ritmo, o treino completo (5 sementes × ~150 episódios × 2 cenários)
  demoraria mais de 100 horas, o que não é viável.
- **Correcção (optimização de desempenho, não muda estado/acção/
  recompensa):**
  - Introduzido um intervalo de decisão de 5 segundos simulados em
    `sumo_env.py` (`INTERVALO_DECISAO`), prática comum em RL de tráfego.
    O agente continua a decidir manter/mudar fase, só o faz a cada 5s de
    simulação em vez de a cada 1s.
  - `dqn_agent.py`: a escolha de acção usa agora chamada directa ao
    modelo (`self.rede(...)`) em vez de `.predict()`, que tem overhead
    fixo elevado por chamada quando usado com uma única amostra. O
    treino em lote continua a usar `.predict()`, onde esse overhead deixa
    de pesar (lotes de 64 amostras).
  - Resultado a confirmar no próximo teste de fumo (ver secção seguinte).
- **Confirmado com novo teste de fumo (3 episódios, cenário baixo fluxo):**
  ~107s por episódio, contra ~750s antes da optimização (~7x mais rápido).
  Recompensa por episódio: -371.0, -129.0, -139.0 (também melhora, tendência
  igual à corrida anterior; a escala absoluta é diferente porque a soma da
  recompensa agora é feita a cada 5s em vez de a cada 1s, não porque a
  formulação mudou).
- **Estimativa para o treino completo com estes tempos:** baixo fluxo,
  5 sementes × 150 episódios ≈ 22h; pico (~9x mais veículos, mais lento por
  episódio) ≈ 80-90h. Total combinado ≈ 100-110h nesta máquina.
- **Decisão de trabalho:** fixado **N = 100 episódios** por semente como
  valor de trabalho para a Fase 4 (não é o valor final da tese, é o que
  usamos para já ter resultados a analisar; pode subir para 150+ depois se
  a curva de recompensa ainda não tiver estabilizado com 100). Reduz a
  estimativa total para ≈ 65-75h. Autor pode ainda decidir mudar para
  Google Colab (proposto, ver conversa) para libertar a máquina local
  durante estas corridas longas; decisão de infra-estrutura ainda aberta,
  não bloqueia o resto do trabalho.
- Código do agente (`agente_dqn/`) e ajustes de rotas/tlLogic enviados para
  o repositório GitHub nesta sessão.
- **Baseline remedido na rede real:** as corridas de validação do SUMO
  feitas nesta sessão (`sumo -c pico.sumocfg` / `baixo_fluxo.sumocfg`)
  sobrescreveram os ficheiros em `outputs/`, que agora contêm o baseline de
  tempo fixo medido na **rede real georreferenciada** (mesma lógica de
  ciclo fixo 42/42+3+3, rede e rotas diferentes). Espera média: **10,3s em
  pico** (2049 viagens), **1,8s em baixo fluxo** (225 viagens). Estes
  valores são bem mais baixos que os antigos (40,5s/9,6s, medidos na rede
  manual antiga) porque a rede real tem menos aproximações (3 em vez de 4)
  e cobre uma área diferente. **Os valores antigos ficam obsoletos** para
  efeitos de comparação com o DQN; usar estes novos como baseline no
  Capítulo V. Números antigos ainda recuperáveis no histórico do git
  (primeiro commit), não perdidos.

## 2026-09-14 — Sessão 2: treino no Google Colab, teste manual

- Decidido com o autor: o treino completo (Fase 4) corre no Google Colab,
  não localmente, para libertar a máquina do autor durante as ~65-75h
  estimadas.
- `train.py` ganhou a opção `--semente-unica`, para treinar só uma semente
  por execução (cada sessão Colab trata de uma semente, em paralelo).
- Criado `agente_dqn/treino_colab.ipynb`: instala SUMO via `apt-get`, clona
  o repositório privado (pede um GitHub personal access token em runtime,
  não gravado no notebook), corre `train.py --semente-unica`, e no fim faz
  commit/push do CSV de resultados dessa semente para o repositório.
- Criado `agente_dqn/juntar_resultados.py`, para juntar os CSVs de todas as
  sementes (depois de saírem do Colab) num só ficheiro e calcular a
  média/desvio-padrão exigidos pelo `CLAUDE.md` (secção 3).
- Explicado ao autor como testar manualmente a rede e o agente com
  `sumo-gui`, para confirmar visualmente a geometria do cruzamento real e
  o ciclo do semáforo antes de lançar o treino completo.
- **Corrigido:** o auto-teste `demo()` do `sumo_env.py` (corre só 50 passos)
  tinha sobrescrito outra vez os ficheiros de baseline do cenário baixo
  fluxo com uma corrida truncada. Regerado o baseline completo (1h,
  225 veículos) com `sumo -c baixo_fluxo.sumocfg`. **Cuidado a reter:**
  correr `sumo_env.py` ou `dqn_agent.py` directamente (auto-testes) usa os
  mesmos ficheiros `outputs/` que o baseline; não correr os auto-testes
  depois de gerar um baseline sem regerar o baseline a seguir.

## 2026-09-14 — Sessão 2: correcções de geometria a partir de imagem de satélite

O autor forneceu capturas de ecrã do OpenStreetMap e do Google Maps
(satélite) do cruzamento real, e apontou 3 problemas na rede gerada.

**Verificação de localização:** confirmado que a rede estava no sítio
certo (o ponto de paragem de autocarro "Ministério da Saúde" fica a
apenas ~27m do nosso junction, medido com `sumolib`). A suspeita inicial
de que a localização estivesse errada não se confirmou.

**Problemas reais encontrados e corrigidos:**

1. **Viragem em U indevida:** a rede anterior permitia uma ligação directa
   entre os dois ramos de sentido único de Eduardo Mondlane
   (`725127419#1 -> 552827132`, incluída nas rotas como `EM2_uturn`). O
   autor confirmou, por imagem de satélite, que essa viragem não é
   fisicamente possível nesta interseccao real. O `netconvert` gerava-a
   por tratar os dois ramos como vias distintas, não reconhece
   automaticamente pares direccionais da mesma avenida. Corrigido com um
   ficheiro de conexões (`net/osm_real/remover_conexoes.con.xml`,
   elemento `<delete>`) aplicado no `netconvert`, removendo essa ligação
   na origem. O volume de tráfego que estava atribuído a essa rota foi
   somado à rota "EM2_straight" (ver comentário nos ficheiros de rotas).
2. **Avenida Salvador Allende com faixas erradas:** a rede tinha 1 faixa
   por sentido nesta via, mas a tag OSM não tinha `lanes` definida (o
   `netconvert` assumiu 1 por omissão). A imagem de satélite mostra 2
   faixas no mesmo sentido. Corrigido adicionando `<tag k="lanes" v="2"/>`
   às duas vias OSM de Salvador Allende (`24769111`, `479355406`) antes de
   reconverter com o `netconvert`.
3. Como resultado da regeneração, os IDs de algumas arestas mudaram
   (`552827135#1` passou a `552827135#0`, `725127419#2` passou a
   `725127419#3`), e o ID do junction fundido passou a incluir mais dois
   nós (`cluster_12168401392_13673178841_13673178842_1783252720`), porque
   o `netconvert` agora funde os 4 nós próximos num só, em vez de 2.
   Actualizados `agente_dqn/sumo_env.py` (`ARESTAS_ENTRADA`, `ID_SEMAFORO`)
   e todos os ficheiros `routes/*.rou.xml` para os novos IDs.
4. Rotas possíveis reduzidas de 8 para 7 (removida `EM2_uturn`).
   `tlLogic` reconstruído com a mesma lógica de 4 fases fixas
   (42s/3s/42s/3s), adaptada aos novos índices de ligação.
5. Validado de novo com `sumo -c pico.sumocfg` / `baixo_fluxo.sumocfg`
   (sem erros) e com o auto-teste de `sumo_env.py`.
6. **Baseline remedido outra vez** com a geometria corrigida: espera média
   **12,2s em pico** (2049 viagens), **9,8s em baixo fluxo** (224
   viagens). O valor de baixo fluxo (9,8s) fica notavelmente próximo do
   valor original medido na rede manual (9,6s, `CLAUDE.md`), o que reforça
   a confiança na correcção.
7. **Cuidado a reter, confirmado outra vez nesta sessão:** o auto-teste do
   `sumo_env.py` voltou a sobrescrever os ficheiros de baseline de baixo
   fluxo com uma corrida truncada (12 veículos); teve de se regerar mais
   uma vez com `sumo -c baixo_fluxo.sumocfg`.

**Teste de fumo repetido com a geometria corrigida** (3 episódios, baixo
fluxo): recompensa -410.0, -111.0, -81.0, melhora de forma consistente,
agente continua a funcionar bem.

**Problema estrutural encontrado e corrigido:** o `train.py` usa TraCI com
o mesmo `.sumocfg` que define os ficheiros de saída do baseline
(`tripinfo_*.xml`, `resumo_*.xml`, `filas_*.xml`), e o SUMO escreve esses
ficheiros também quando controlado via TraCI. Cada episódio de treino
estava a sobrescrever o baseline com os resultados desse episódio (que
nem sequer usa a lógica de tempo fixo, usa as decisões do agente). Isto já
tinha acontecido sem eu notar logo (o baseline "remedido" documentado mais
acima, 12.2s/9.8s, media na verdade uma mistura de baseline com uma
corrida de treino truncada). Corrigido em `sumo_env.py`: o `AmbienteSumo`
agora redirecciona esses 3 ficheiros de saída para
`outputs/_treino_scratch/` (na `.gitignore`, descartável) sempre que liga
o TraCI, nunca mais toca nos ficheiros de baseline reais. Baseline
confirmado de novo após a correcção: **12,2s pico, 9,8s baixo fluxo**
(números não mudaram, a corrida truncada anterior por coincidência não
tinha alterado a média o suficiente para notar sem verificar o
`n` de viagens).

## 2026-09-14 — Sessão 2: checkpoint/resume para o treino no Colab

Antes de dar o passo-a-passo final ao autor, foi identificado um risco: o
Colab gratuito desliga por inactividade e não tem limite de sessão
garantido; sem checkpoint, uma sessão de horas perdia-se toda.

- `dqn_agent.py` ganhou `guardar_pesos()`/`carregar_pesos()` (usa
  `keras.Model.save_weights`/`load_weights`).
- `train.py` grava um checkpoint (pesos + episódio actual + epsilon) a
  cada 10 episódios em `outputs/_checkpoints/`. Ao arrancar, se existir
  checkpoint para essa semente/cenário, retoma a partir daí em vez de
  recomeçar. CSV de resultados passou a ser escrito de forma incremental
  (uma linha por episódio, com flush), não só no fim.
- **Bug corrigido durante a implementação:** a versão inicial abria o CSV
  em modo "escrita" sempre que uma semente não tinha checkpoint próprio, o
  que apagava os resultados de sementes anteriores ao correr várias
  sementes seguidas no mesmo processo. Corrigido: o ficheiro só é criado
  de novo se ainda não existir ou estiver vazio, todas as sementes
  seguintes fazem sempre append.
- `treino_colab.ipynb` actualizado: nova célula que monta o Google Drive e
  redirecciona `outputs/_checkpoints/` para lá, porque o disco do Colab é
  efémero (um reinício completo da sessão apagaria os checkpoints
  guardados só localmente). Célula de treino passou a usar `python -u`
  (sem buffer), para o progresso aparecer no output em tempo real em vez
  de só no fim.
- **Validação:** testada directamente a função `guardar_pesos`/
  `carregar_pesos` (pesos e progresso coincidem depois de recarregar).
  Uma tentativa de validação end-to-end (correr 12 episódios reais e
  interromper a meio) acabou abortada por lentidão da máquina nesta
  sessão (processos anteriores ainda a ocupar CPU); os processos
  interrompidos à força corromperam outra vez os ficheiros de baseline
  (efeito colateral da interrupção brusca, não do mecanismo de
  checkpoint), baseline regenerado mais uma vez sem alteração dos
  números (12,2s pico, 9,8s baixo fluxo).

## 2026-09-14 — Sessão 2: 3.ª faixa de Eduardo Mondlane e paragem de autocarro

O autor forneceu um rabisco à mão do cruzamento real, com mais 2
observações:

1. **Afunilamento indevido:** a aresta `552827132` (um dos troços de saída
   de Eduardo Mondlane) tinha só 2 faixas, enquanto o resto da avenida tem
   3 em ambos os sentidos, sem afunilar. A tag OSM não tinha `lanes`
   definida nesta via (tal como aconteceu com Salvador Allende), o
   `netconvert` assumiu 2 por omissão. Corrigido da mesma forma, com
   `<tag k="lanes" v="3"/>` adicionada à via OSM antes de reconverter.
2. **Paragem de autocarro logo após a curva:** o autor confirmou
   visualmente uma paragem nesse ponto. Ao pedir ao `netconvert` os pontos
   de paragem reais do OpenStreetMap (opção `ptstop-output`), confirmou-se
   uma paragem real, tagged no OSM, exactamente na aresta
   `725127419#3` ("Ministério da Saúde"), 1,4-26,4m do cruzamento, coerente
   com o rabisco. Adicionada como `net/paragens.add.xml`, ligada aos dois
   `.sumocfg`. O fluxo de autocarros do cenário de pico que passa por essa
   aresta (`f_EM2_straight_bus`) foi alterado para parar lá 20s (tempo
   típico de embarque/desembarque), via uma rota dedicada
   (`EM2_straight_com_paragem`) só para não obrigar ligeiros/chapas/pesados
   a parar também.

**Simplificação deliberada, não implementada:** o rabisco mostra também
que as faixas laterais de Eduardo Mondlane estão separadas por um passeio/
separador físico com aberturas pontuais para mudar de faixa (visível nas
zonas tracejadas do desenho). Isto **não foi modelado** na rede SUMO: as 3
faixas de cada sentido estão representadas como um bloco uniforme, sem essa
micro-geometria do separador. Motivo: o estado do agente agrega fila e
espera por aresta inteira, não por faixa individual, por isso este detalhe
não muda a formulação nem, provavelmente, os resultados agregados de forma
relevante para um protótipo de licenciatura; modelar isso exigiria edição
manual bem mais fina da rede (separar em mais vias/pistas ligadas por
conectores). Sinalizado ao autor, não implementado sem confirmação
explícita de que vale o esforço adicional.

Validado com `sumo -c pico.sumocfg` / `baixo_fluxo.sumocfg` e com os
auto-testes de `sumo_env.py`/`dqn_agent.py`, sem erros. Baseline remedido:
**11,5s pico** (melhorou face aos 12,2s anteriores, plausível dado o
reforço de capacidade de 2 para 3 faixas), **9,9s baixo fluxo** (~igual).

## 2026-09-14 — Sessão 2: separador físico modelado, estado passa a ser por faixa

O autor confirmou (explicitamente) que o separador físico deve ser
modelado, e que o estado do agente deve olhar por faixa, não por via
inteira.

**Modelação do separador físico:** implementado com os atributos nativos
do SUMO `changeLeft`/`changeRight` ao nível da faixa (não existe forma de
"desligar" mudança de faixa por completo, o valor tem de ser uma lista de
classes de veículo permitidas; usou-se `"bicycle"`, que exclui todos os 4
tipos de veículo do projecto). Testado à parte antes de aplicar à rede
real (rede minúscula de teste, 3 faixas, veículos a tentar forçar mudança
de faixa via TraCI) porque a primeira tentativa tinha a direcção dos
atributos trocada (`changeLeft` bloqueia o movimento da faixa DE origem
PARA a esquerda, não da direita para essa faixa) e não bloqueava nada.
Confirmada a combinação correcta antes de tocar na rede real.

Aplicado às duas vias a montante das arestas de entrada (as arestas
directamente incidentes ao cruzamento ficam como zona de abertura/fusão,
coerente com o rabisco do autor):
- `552827139#1` (a montante de EM1_in)
- `725127420#4` (a montante de EM2_in)

Em cada uma, a faixa 2 (mais a esquerda no sentido de marcha, a de acesso
local/paragem) fica impedida de mudar para a faixa 1, e vice-versa; as
faixas 0 e 1 (centrais) continuam livres entre si.

**Simplificação retida:** não foram modeladas aberturas pontuais ao longo
destas vias a montante (dados reais sobre a posição exacta de cada
abertura não estao disponiveis); a via a montante fica totalmente fechada
entre a faixa de acesso e as centrais, com a abertura a acontecer só na
transição para a aresta seguinte (a de entrada no cruzamento, já sem
restrição). Isto é uma aproximação razoável dada a escala da rede
modelada (poucas centenas de metros), não uma reconstrução exacta de cada
abertura do passeio.

**Estado do agente passa a ser por faixa:** vector de estado de 7 para
**17** valores (8 faixas x [fila, espera] + fase actual). `sumo_env.py`
usa agora `traci.lane.getLastStepHaltingNumber`/`getWaitingTime` por
faixa em vez de `traci.edge.*` por via inteira. `dqn_agent.py`:
`TAMANHO_ESTADO` actualizado para 17. A recompensa continua a ser
`-soma(esperas)`, agora somada por faixa em vez de por via (matematicamente
equivalente, a soma e a mesma).

Validado com `sumo -c` em ambos os cenários e com os auto-testes de
`sumo_env.py`/`dqn_agent.py` (confirmam 17 valores). **Teste de fumo
confirmado** (3 episódios, baixo fluxo): recompensa -425.0, -62.0, -103.0,
melhora de forma consistente, agente continua a aprender bem com o estado
de 17 valores e a rede com restrição de faixas.

`treino_colab.ipynb`: `EPISODIOS` por omissão passou de 100 para **20**,
para o primeiro teste do autor ser mais curto (confirmado explicitamente).

**Ainda por verificar/decidir:**
- Validar o resume end-to-end com uma interrupção real (kill do processo,
  não só teste unitário das funções de guardar/carregar), idealmente numa
  máquina menos ocupada ou já no próprio Colab.
- O autor referiu ainda "atenção às permissões para curva dos veículos na
  estrada" de forma geral; as ligações actuais (direita/esquerda/recto por
  aproximação) foram revistas e parecem coerentes com a imagem de
  satélite, mas vale a pena confirmar visualmente com `sumo-gui` antes do
  treino completo (ver secção de teste manual, mais acima nesta conversa).
- O treino ainda não foi corrido com esta geometria corrigida; os
  resultados de teste de fumo anteriores (recompensas -2502/-371 etc.)
  foram medidos com a geometria antiga (com a viragem em U e Salvador
  Allende a 1 faixa) e não são mais representativos. Repetir o teste de
  fumo antes do treino completo no Colab.

## Como usar este ficheiro

Cada sessão de trabalho futura deve acrescentar uma secção nova aqui, com
data, o que foi feito, porquê, e o que ficou pendente. Não reescrever
secções antigas, só corrigir factos errados se descobertos depois.
