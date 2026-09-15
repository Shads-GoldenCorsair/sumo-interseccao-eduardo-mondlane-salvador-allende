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

## 2026-09-14 — Sessão 2: passadeiras reais na interseccao

Novo rabisco do autor mostrou dois elementos adicionais: baía de autocarro
(faixa diagonal separada para parar) e passadeiras nas 4 esquinas do
cruzamento. Confirmado com o autor: modelar a baía como faixa física extra,
e adicionar as passadeiras com fluxo de peões (podem afectar o trânsito).

**Passadeiras:** processo com bastante tentativa e erro documentado aqui
para referência futura:
- `--crossings.guess` do `netconvert`, sozinho, não gerou nenhuma
  passadeira nesta zona, apesar de haver passeios (dados reais do OSM,
  tag `sidewalk`). Descoberta a causa depois de testes isolados numa rede
  minúscula: as vias de sentido único de Eduardo Mondlane só tinham
  passeio de um lado (`sidewalk=left`), e o gerador de passadeiras precisa
  de passeio dos dois lados para conseguir ligar uma travessia.
- Corrigido com `--osm.oneway-reverse-sidewalk` (força passeio dos dois
  lados em vias de sentido único) + `--sidewalks.guess.from-permissions` +
  `--crossings.guess.speed-threshold 100` (o limite por omissão excluía
  vias mais rápidas). Resultado: **6 passadeiras reais** no nosso
  cruzamento, uma por cada aresta de entrada e saída.
- Efeito colateral a gerir: os passeios novos inseriram-se como a faixa de
  índice 0 em cada aresta de Eduardo Mondlane, empurrando as faixas de
  veículos de [0,1,2] para [1,2,3]. Isto partia várias coisas que
  assumiam índices fixos:
  - A restrição de faixa (separador físico, ver entrada anterior) tinha
    de ser reaplicada aos novos índices (faixa 3 = exterior, faixa 2 =
    adjacente).
  - `net/paragens.add.xml`: a paragem de autocarro apontava para a faixa
    errada (`_0`, agora passeio), corrigido para `_3` (faixa exterior).
  - `agente_dqn/sumo_env.py`: `FAIXAS_ENTRADA` deixou de assumir um
    número de faixas fixo por aresta (`NUM_FAIXAS`), passou a detectar
    dinamicamente, a partir do próprio ficheiro de rede, quais as faixas
    que permitem veículos (excluindo passeios). Mais robusto a futuras
    regeneracoes da rede.
- **Nao resolvido, aceite como esta:** a viragem em U entre os dois
  ramos de Eduardo Mondlane (que já tinha sido removida na correcção
  anterior) voltou a aparecer na rede depois de activar o processamento
  de peões, mesmo com o mesmo ficheiro de conexoes a pedir a sua remoção.
  Não se percebeu a causa exacta (possivelmente uma interaccao entre o
  processamento de passeios e a reconstrucao de ligacoes). **Sem impacto
  prático**: nenhuma rota do projecto usa esse movimento, os veiculos
  simulados nunca o executam, so fica presente na topologia da rede sem
  ser usado.

**tlLogic reconstruido** com as passadeiras incluídas: os peões de cada
aproximacao ficam com sinal verde durante a fase em que essa aproximacao
de veiculos esta vermelha (raciocinio verificado contra as ligacoes reais
calculadas pelo netconvert), e vermelho durante as duas fases amarelas
(transicao de seguranca).

Validado com `sumo -c` em ambos os cenarios (pico teve 1 aviso de travagem
de emergencia, aceitavel, completou a simulacao). Baseline remedido:
**11,2s pico, 9,9s baixo fluxo**.

**Decisão do autor:** fluxo de peões só em Eduardo Mondlane por agora
(confirmado como funcional, ver abaixo); baía de autocarro física
implementar já (tentada, ver resultado abaixo).

**Fluxo de peões implementado:** testado primeiro isoladamente (uma
pessoa a andar de `552827135#0` para `725127419#3`, atravessando o
cruzamento todo através da infra-estrutura de passadeiras), confirmado
sem erros. Adicionados `<personFlow>` a `demanda_pico.rou.xml`
(40 pessoas/hora em cada sentido) e `demanda_baixo_fluxo.rou.xml`
(8 pessoas/hora), cruzando entre os lados de EM1 e EM2. Salvador Allende
fica de fora por agora (rede de passeios incompleta ali). Validado:
80 pessoas inseridas no pico, 16 no baixo fluxo, sem erros de
encaminhamento.

**Baía de autocarro (faixa física): tentativa falhada, documentada.**
Exportada a rede para XML plano (`nodes`/`edges`/`connections`/`tllogic`
separados) e usado o mecanismo nativo do SUMO para faixas que nascem e
desaparecem (`<split>` no ficheiro de arestas), na posição exacta da
paragem (1,4-26,4m). O `netconvert` recusou reconstruir a rede a partir
daí, com o erro "Edge does not touch node", em várias tentativas
(incluindo remover as definições de faixa conflituosas). A causa mais
provável: o `<split>` implicitamente subdivide a aresta em vários IDs
internos, e outros ficheiros da rede (o semáforo, as conexões) já
referenciam o ID original da aresta inteira, criando uma inconsistência
que não se resolveu com o tempo disponível.

**Decisão do autor perante o impasse:** usar o atributo `parking="true"`
no `<stop>` do autocarro em vez da faixa física — o SUMO deixa o trânsito
ultrapassar um veículo parado com este atributo, produzindo o efeito
prático real de uma baía (não bloqueia quem vem atrás) sem precisar de
desenhar a geometria da faixa. Aplicado em `demanda_pico.rou.xml`.

Rede final desta correcção volta à versão v4 (passadeiras, faixas
correctas, sem a tentativa de baía física). Validado com `sumo -c` em
ambos os cenários, sem erros. Baseline remedido: **11,3s pico, 9,9s baixo
fluxo**.

**Teste de fumo confirmado** (3 episódios, baixo fluxo, já com passadeiras
e peões): recompensa -359.0, -85.0, -64.0, melhora de forma consistente.

## 2026-09-14 — Sessão 2: correcções finais (sem passeio central, chapas restritas)

O autor corrigiu 4 pontos depois de ver a rede anterior:

1. **"No meio de Eduardo Mondlane não tem passeio, RETIRE."** Verificado
   nos dados reais do OSM: as vias de Eduardo Mondlane só têm a tag
   `foot=yes` (peões permitidos na via), **não** têm `sidewalk=` (sem
   passeio dedicado mapeado). O passeio que a correcção anterior tinha
   criado ali (via `--osm.oneway-reverse-sidewalk`) era sintético, não
   real. Removido: já não se força nenhum passeio em Eduardo Mondlane.
   **Descoberta útil:** os peões continuam a conseguir atravessar sem
   nenhuma infra-estrutura de passeio/passadeira dedicada, porque o SUMO
   deixa-os andar directamente na via quando esta tem `foot=yes`, tal
   como acontece na realidade em zonas sem passeio formal. Testado e
   confirmado antes de aplicar à rede real.
2. **Paragem de autocarro do lado do passeio, sempre um pouco depois do
   semáforo:** já estava assim (aresta `725127419#3`, depois do
   cruzamento, faixa mais à esquerda). Confirmado, sem alteração.
3. **Chapas só na faixa esquerda (a "sem pressa"), proibidas nas faixas
   centrais de Eduardo Mondlane.** Explicado pelo autor: Moçambique segue
   o código de estrada britânico (condução à esquerda), por isso a faixa
   mais próxima do separador central (índice 0 no SUMO) é a rápida/
   ultrapassagem, e a mais à esquerda (índice mais alto, junto ao
   passeio/edifícios) é a lenta, onde andam os chapas. Implementado com
   `disallow="taxi"` (vClass dos chapas) nas faixas centrais das 6 arestas
   de Eduardo Mondlane (as duas vias a montante da restrição de mediana,
   mais as 4 arestas junto ao cruzamento). **Bug próprio encontrado e
   corrigido:** a primeira tentativa de inserir "taxi" na lista `disallow`
   já existente falhou silenciosamente (o padrão de substituição não
   contava com outros atributos entre `id=` e `disallow=`); confirmado
   com verificação directa via TraCI (antes: chapas em todas as faixas;
   depois: só na faixa esquerda) antes de dar como resolvido.
4. **Passadeiras só no cruzamento, não depois dele.** Como já não há
   passeio a suportar passadeiras dedicadas em Eduardo Mondlane (ponto 1),
   isto deixou de se aplicar por essa via; os peões atravessam directamente
   como descrito no ponto 1. As passadeiras reais de Salvador Allende
   (fora do âmbito desta correcção) mantêm-se como estavam.

Rede reconstruída do zero (osm.sidewalks + osm.crossings apenas, sem
guess forçado), `tlLogic` reconstruído (14 ligações de veículos, sem
ligações de peões desta vez, já que não há passadeira formal em EM).
Restrição de mediana (separador físico) reaplicada aos índices correctos
(faixa 1 e 2 de 3, já sem deslocamento por passeio). Paragem de autocarro
corrigida de volta para a faixa 2.

Validado com `sumo -c` em ambos os cenários, sem erros nem avisos.
Baseline remedido: **12,0s pico, 9,9s baixo fluxo**.

**Teste de fumo confirmado** (3 episódios, baixo fluxo): recompensa
-468.0, -108.0, -128.0, melhora de forma consistente com a rede final
desta sessão.

## 2026-09-14 — Sessão 2: adaptação da rede de referência "antigravity sumo"

O autor apontou uma pasta (`Desktop/antigravity sumo/`) com uma rede SUMO
construída por outra ferramenta de IA (Antigravity/Gemini), em XML plano
(nós/arestas/conexões separados), pedindo para adaptar a lógica dessa rede
à nossa (que é georreferenciada, com coordenadas reais do OpenStreetMap; a
de referência é esquemática, coordenadas abstractas simétricas). Adoptadas
3 ideias, por ordem de prioridade pedida:

**1. Autocarros também restritos à faixa lateral.** Já tínhamos restrito
chapas (`disallow="taxi"`) às faixas centrais de Eduardo Mondlane; agora
autocarros também (`disallow="... taxi bus"`), coerente com "chapas e
machimbombos circulam exclusivamente pelas laterais" da rede de
referência. Confirmado sem erros.

**2. Baía de autocarro física, via nós de divergência/convergência.**
Técnica adaptada da rede de referência (nós `split`/`merge` a montante e
jusante), desta vez com sucesso (a tentativa anterior com o mecanismo
`<split>` do netconvert tinha falhado, ver entrada anterior desta secção).
Processo:
- A aresta `725127419#3` (troço de saída de Eduardo Mondlane ramo 2, onde
  fica a paragem) foi dividida manualmente em 3 arestas consecutivas
  (`725127419#3a/b/c`), com 2 novos nós intermédios (`N_BAIA_INICIO`,
  `N_BAIA_FIM`) posicionados exactamente na extensão da paragem real
  (1,4-26,4m), via edição directa dos ficheiros XML planos exportados
  (`netconvert --plain-output-prefix`).
- O troço do meio (`725127419#3b`) ganhou uma 4.ª faixa (índice 3),
  exclusiva a autocarros (`allow="bus"`), com ligações explícitas de
  entrada (faixa lateral 2 diverge para a faixa 3) e saída (faixa 3
  converge de volta para a faixa 2).
- **Bugs próprios cometidos e corrigidos durante o processo:**
  - O ficheiro de tipos (`.typ.xml`) exportado tinha `sidewalkWidth`
    herdado de uma fase anterior da sessão, o que voltava a criar
    passeio sintético em toda a Eduardo Mondlane ao reconverter. Removido
    de todos os tipos.
  - A faixa lateral do troço da baía (`725127419#3b`, faixa 2) tinha
    `disallow="taxi"` por engano (devia ser só `disallow="bus"`, para
    forçar só os autocarros para a faixa 3, sem impedir chapas de
    continuar na lateral). Corrigido, confirmado com TraCI (autocarros
    usam a faixa 3, chapas continuam na faixa 2).
- Todas as rotas e ficheiros de procura que referenciavam
  `725127419#3` foram actualizadas para `725127419#3a 725127419#3b
  725127419#3c`. `net/paragens.add.xml` aponta agora para
  `725127419#3b_3` (a faixa da baía).
- A paragem de autocarro deixa de usar `parking="true"` (já não é
  necessário, a baía física faz o mesmo de forma mais realista); esse
  atributo pode ser removido do `<stop>`, mas foi deixado por
  segurança (inofensivo com a baía a funcionar).

**3. Peões com perfis nomeados: tentado, revertido por segurança.**
Adicionados `vType` nomeados (`ped_idoso`, `ped_trabalho`, `ped_estudante`,
`ped_vendedora`), inspirados na rede de referência, para reflectir o
perfil heterogéneo da zona (hospital, faculdade, jardim infantil). Ao
testar, **detectada uma colisão real veículo-peão** no cenário de baixo
fluxo: sem passeio dedicado em Eduardo Mondlane (correcção legítima da
sessão anterior), o SUMO faz o peão **andar ao longo de toda a extensão da
faixa partilhada** (77 a 125s por travessia, não um atravessamento rápido
perpendicular), o que aumenta muito o tempo de exposição ao trânsito e
causou a colisão num teste. **Decisão tomada sem pedir confirmação
prévia, por ser uma questão de segurança/correcção, não de preferência:**
removido o `<personFlow>` de ambos os cenários; os `vType` de peões ficam
definidos, prontos a reutilizar quando houver uma solução de travessia
seguidamente mais rápida (precisa de infra-estrutura mínima de passadeira
no ponto exacto do cruzamento, não `foot=yes` a percorrer a aresta
inteira). Isto reverte a decisão anterior "peões só em EM1/EM2, sem
Salvador Allende" para "peões suspensos em toda a rede, por agora".

Validado com `sumo -c` em ambos os cenários, sem erros, sem colisões.
Baseline: **12,0s pico, 9,9s baixo fluxo** (igual ao anterior, sem peões
o valor não muda por essa via).

**Teste de fumo confirmado** (3 episódios, baixo fluxo, rede final com
baía de autocarro): recompensa -454.0, -74.0, -90.0, melhora de forma
consistente.

**Nota do autor sobre travessias futuras:** um peão já na passadeira tem
prioridade sobre os veículos, mesmo com sinal verde entretanto para estes
(os veículos esperam o peão terminar). Confirmado que é o comportamento
nativo do `<crossing>` do SUMO; a solução a construir da próxima vez tem
de usar esse elemento, não repetir a partilha de faixa que causou a
colisão.

**Ainda por fazer, explicitamente pendente:**
- Resolver a travessia de peões em segurança (precisa de infra-estrutura
  de passadeira mínima e pontual, não passeio contínuo). **Requisito
  explícito do autor:** um peão já a atravessar na passadeira tem
  prioridade sobre os veículos, mesmo que o sinal fique verde para estes
  entretanto (os veículos esperam o peão terminar). Isto é o
  comportamento nativo do elemento `<crossing>` do SUMO (com prioridade
  de cedência configurável), ao contrário da solução removida nesta
  sessão (`foot=yes` a partilhar a faixa, sem essa prioridade e que
  causou a colisão); a próxima tentativa de resolver a travessia tem de
  usar `<crossing>` como está descrito aqui, não repetir a solução de
  partilha de faixa.

  **Tentativa feita e sem sucesso (mesma sessão, pedido "refine"):**
  dividida cada uma das 5 arestas junto ao cruzamento (as 3 de entrada
  mais 2 de saída) em dois segmentos, com um novo nó e uma faixa de
  peões dedicada só no último troço (coto) antes do semáforo, sem
  passeio ao longo do resto da via (respeitando a correcção anterior do
  autor). Testado com dois comprimentos de coto (5m e 12m). Em ambos os
  casos, o `netconvert` recusou construir as passadeiras manuais
  (`<crossing>`) com o erro **"no vehicle lanes to cross"**, apesar das
  faixas de veículos existirem correctamente nesses segmentos (confirmado
  por inspecção directa do XML). O comprimento do coto não foi a causa
  (mesmo erro em 5m e 12m), o que sugere um bloqueio mais profundo, talvez
  relacionado com a forma como o netconvert trata nós inseridos
  manualmente tão perto de um junction já complexo (fundido de 4 nós
  OSM). Revertido sem alterar a rede activa (ainda a versão v7, com baía
  de autocarro, sem passadeiras). Não investigado mais fundo por questão
  de tempo; próxima tentativa pode precisar de uma abordagem diferente
  (ex.: pedir ajuda directa na documentação/lista de emails do SUMO, ou
  reconstruir o junction com uma topologia mais simples antes de tentar
  passadeiras).
- Fluxo de peões em Salvador Allende (idem, mais o passeio incompleto
  já identificado antes).
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

## 2026-09-14 — Sessão 2: adopção definitiva da rede antigravity sumo

Depois da tentativa de reconstruir a travessia de peões com `<crossing>`
falhar (ver entrada anterior "refine"), o autor decidiu: **usar
directamente os ficheiros de `Desktop/antigravity sumo/` como a nossa
rede**, copiando e adaptando ao nosso projecto, em vez de continuar a
tentar corrigir a rede georreferenciada do OpenStreetMap.

**O que foi feito:**
- Ficheiros de origem copiados para `net/antigravity_origem/` (referência,
  não usados directamente pelo SUMO).
- `net/eduardo_mondlane_salvador_allende.net.xml` substituído pela rede
  compilada da referência (`mondlane_allende.net.xml`), que já tem
  `--lefthand true` (condução à esquerda nativa, correcta para
  Moçambique) e uma topologia mais simples que permitiu às passadeiras
  funcionarem de imediato (algo que a rede georreferenciada nunca
  conseguiu, apesar de várias tentativas).
- `net/paragens.add.xml` substituído pelo `busstops.add.xml` da
  referência (2 paragens de autocarro, uma por sentido de Eduardo
  Mondlane, cada uma numa baía física própria).
- **`tlLogic` ajustado** para o nosso ciclo fixo documentado no
  `CLAUDE.md` (originalmente a referência tinha 35s/25s assimétricos com
  amarelo de 4s): fases de 40s (não 42s) + 3s amarelo, para caber um
  vermelho geral de 2s antes de cada mudança de verde, mantendo a duração
  total do ciclo em 90s. **Descoberta importante:** a primeira tentativa,
  sem o vermelho geral (para bater certo com o formato exacto 42/3/42/3
  já documentado), causou uma **colisão real entre dois veículos** num
  teste (dois veículos a fundir na mesma faixa lateral sem clareamento
  suficiente). O vermelho geral foi reposto, resolvendo o problema;
  fica documentado como desvio necessário face ao ciclo exacto descrito
  no `CLAUDE.md` original (a duração total do ciclo mantém-se igual).
- `routes/demanda_pico.rou.xml` = rotas da referência adaptadas (vTypes
  renomeados para a convenção do projecto: `car`→`ligeiro`, `bus`→
  `autocarro`, `chapa` mantido). Inclui peões com perfis nomeados
  (idoso, estudante, vendedora, etc.), que agora funcionam correctamente
  (a rede da referência já tem passadeiras reais, ao contrário da nossa
  tentativa anterior).
- `routes/demanda_baixo_fluxo.rou.xml` gerado por escala automática a
  partir do pico (~15% dos veículos, ~30% dos peões, autocarros menos
  frequentes), mesma lógica das versões anteriores.
- `routes/routes.rou.xml` e `routes/vtypes.rou.xml` actualizados como
  documentação de referência (sem fluxos activos).
- `config/*.sumocfg`: acrescentadas as opções de peões da referência
  (`pedestrian.model=striping`, largura de risca 0.55, tempo de
  engarrafamento em passadeira 60s).
- `agente_dqn/sumo_env.py`:
  - `ARESTAS_ENTRADA` passou de 3 para **5 aproximações** (Eduardo
    Mondlane ganhou faixa central e lateral em cada sentido, em vez de
    uma aresta só por sentido). Faixas de veículo totais mantêm-se em 8
    (coincidência: 2+1+2+1+2), por isso o **estado continua a ter 17
    valores**, não muda a dimensão, só a composição.
  - `ID_SEMAFORO` = `"TL_MAIN"` (nome da referência, não mais o ID
    composto do OSM).
  - `FASE_*`: passou de 4 para 6 índices de fase (2 vermelhos gerais
    novos), `step()` actualizado para avançar pela sequência completa
    amarelo→vermelho geral→verde ao mudar de fase.
- Removido `net/manual_backup/` (rede manual da Fase 0, definitivamente
  obsoleta a esta altura, recuperável no histórico do git se necessário).

**Validado:** `sumo -c` em ambos os cenários sem erros nem colisões,
auto-teste de `sumo_env.py` confirma 17 valores. **Teste de fumo
confirmado** (3 episódios, baixo fluxo): recompensa -3271.0, -1726.0,
-2894.0. Melhora claramente do 1.º para os seguintes; alguma variação
entre o 2.º e 3.º episódio (esperada com só 3 episódios e tráfego
aleatório sem semente fixa por episódio). A magnitude é maior que nas
redes anteriores (eram ~-100 a -450), consistente com esta rede ter mais
aproximações, mais volume e um ciclo semafórico mais longo (90s vs 90s
antes também, mas mais filas a acumular com 5 aproximações).

**Baseline novo:** 20,6s pico (2254 viagens), 14,4s baixo fluxo (348
viagens). Mais alto que a versão anterior (12,0s/9,9s), plausível dado
mais volume total e mais movimentos de conflito na rede da referência;
não comparável directamente com os valores anteriores (rede diferente).

**Nota para a tese, a reflectir nos capítulos:** esta troca de rede altera
a natureza da "georreferenciação" que o Capítulo III descrevia como
objectivo — a rede actual já não usa coordenadas geográficas reais do
OpenStreetMap, é uma rede esquemática desenhada para reflectir o
comportamento de trânsito real da interseccão (condução à esquerda,
faixas central/lateral, baía de autocarro, passadeiras), não a sua
geometria exacta. Isto precisa de ser reflectido no texto do Capítulo III
quando for escrito, com a devida honestidade sobre a origem da rede.

## 2026-09-14 — Sessão 2: corrigido notebook do Colab, pronto para treino

Ao rever o `treino_colab.ipynb` antes de avançar para o treino, encontrado
um problema real: edições anteriores tinham deixado a secção "5. Treinar"
**duplicada** (uma versão actualizada com ligação ao Drive, e uma versão
antiga e desactualizada por baixo, sem `-u` e com texto a dizer "não há
checkpoint automático ainda", que já não era verdade). A célula que liga
ao Google Drive também tinha perdido o conteúdo nalguma edição anterior
(ficou com o comando de treino em vez do código de montagem do Drive).
Reescrito o notebook inteiro de uma vez (edições célula-a-célula estavam a
ter efeitos inesperados nos IDs), confirmado JSON válido.

**O notebook está pronto, mas eu não consigo lançá-lo** — corre no browser
da conta Google do autor, precisa do token pessoal do GitHub colado à mão,
sem acesso a partir daqui. Passos que o autor ainda tem de fazer:
1. Abrir `treino_colab.ipynb` no Google Colab.
2. Correr as células por ordem (a 2 pede o token do GitHub, a 4b pede
   autorização do Drive).
3. `EPISODIOS = 20` fica como está para o primeiro teste; confirmar que
   corre até ao fim antes de subir para 100 (valor de trabalho, ver
   secção "checkpoint/resume" mais acima).

## 2026-09-15 — Sessão 3: primeiro treino real no Colab, relatório de resultados

**Primeiro treino real completo no Google Colab**, cenário baixo fluxo,
semente 0, 20 episódios (valor de teste). Processo teve várias fricções
resolvidas em conjunto com o autor:
- `.gitignore` tinha uma regra (`outputs/treino_*.csv`) que bloqueava os
  próprios ficheiros de resultado que o Colab tenta enviar, sobrava de uma
  fase anterior em que só existia um `treino_<cenario>.csv` genérico.
  Corrigida.
- Sessão Colab reiniciou a meio (desligou), perdeu o clone; teve de
  recomeçar do zero. O checkpoint no Drive não chegou a ser testado nessa
  altura.
- Token do GitHub sem permissão de escrita (`repo` não estava marcado por
  completo), causou `403 Permission denied` no push. Resolvido com um
  token novo.
- `git pull` teve de correr no meio de tudo isto (várias sessões/commits
  locais entretanto), ficou preso num editor de texto (`vim`) por não ter
  usado `--no-edit`; resolvido escrevendo `:wq` e depois completando o
  merge com `git commit --no-edit`.

**Resultado:** recompensa desce de -2884 (episódio 1) para uma média à
volta de -1400/-1700 no resto dos 20 episódios, confirma que o agente
está a aprender. Guardado em `outputs/treino_baixo_fluxo_semente0.csv`.

**Decisão do autor:** já não correr sementes em paralelo (5 sessões Colab
ao mesmo tempo); correr as 5 sementes todas seguidas, numa única sessão.
`treino_colab.ipynb` reescrito em conformidade:
- Célula de configuração: `SEMENTES = 5` em vez de `SEMENTE` única.
- Célula 4b (Drive): pasta partilhada por cenário (`.../baixo_fluxo/`
  em vez de `.../baixo_fluxo_semente0/`), já que `train.py` separa os
  ficheiros de checkpoint por semente dentro da mesma pasta.
- Célula de treino: `train.py --sementes 5` em vez de `--semente-unica`.
- Célula de envio: grava `outputs/treino_<cenario>.csv` (já com as 5
  sementes juntas), e passou a fazer `git pull --no-edit` antes do
  `push`, para evitar o problema de divergência encontrado no primeiro
  teste.
- `EPISODIOS` subiu de 20 para 100 (valor de trabalho definitivo).

**Novo:** `agente_dqn/graficar_resultados.py`, gera um gráfico PNG da
evolução da recompensa por episódio (uma linha por semente, mais a média
a negrito), a partir do CSV de treino. Usa `matplotlib`, adicionado a
`requirements.txt` (não estava lá, instalado e testado nesta sessão).
Testado com os dados reais de 1 semente/20 episódios, gráfico legível,
guardado em `outputs/grafico_treino_baixo_fluxo.png`.

**Novo:** `RELATORIO_RESULTADOS.md` (raiz do projecto), documento pedido
pelo autor explicando: que dados alimentam o algoritmo, onde ver a
melhoria (visualmente no sumo-gui, no CSV, no gráfico, e por comparação
com o baseline), que código treina o modelo (`sumo_env.py`/`dqn_agent.py`/
`train.py`, com o papel de cada função), e o passo a passo completo do
treino até ao gráfico final.

**Pendente, identificado ao escrever o relatório:** ainda não existe um
script de avaliação final (carregar pesos treinados, correr com
`epsilon=0`, medir espera média real, comparar com o baseline). Próximo
passo lógico depois do treino completo terminar.

## 2026-09-15 — Sessão 3: script de avaliação final, treino no Colab em curso

Enquanto o autor deixava o treino real a correr no Colab (5 sementes ×
100 episódios, baixo fluxo, numa só sessão sequencial), pediu um script
para ver o agente treinado a decidir (visualmente, no `sumo-gui`) e para
comparar o desempenho real com o baseline.

**Falha encontrada ao preparar isto:** o `train.py` apagava os pesos
treinados assim que uma semente terminava (só existiam como checkpoint
para retomar, nunca ficavam guardados de forma permanente). Corrigido:
ao terminar uma semente, o modelo final fica gravado em
`outputs/modelos_treinados/<cenario>_semente<N>.weights.h5`, só o
progresso de retoma é que continua a ser apagado.

**Novo:** `agente_dqn/avaliar_agente.py`. Carrega um modelo treinado,
corre um episódio completo com `epsilon=0` (sem exploração aleatória, só
decisões "a sério"), e compara a espera média resultante com o baseline
(lido de `outputs/tripinfo_<cenario>.xml`). Aceita `--gui` para ver o
agente a decidir ao vivo (só localmente, o Colab não tem ecrã).

Testado localmente com um treino rápido de 3 episódios (só para validar o
pipeline, não é um resultado real): recompensa -1618, espera média do
agente 4,9s contra 14,4s do baseline. **Importante, sinalizado ao autor:**
este número não significa nada ainda, é só a confirmação de que o
mecanismo de carregar pesos e avaliar funciona; com 3 episódios de treino
o agente ainda não aprendeu nada de útil.

`RELATORIO_RESULTADOS.md` actualizado com a secção 4.5 (como avaliar) e
a nota de que a média/desvio-padrão entre as 5 sementes (exigida pelo
`CLAUDE.md`, secção 3) ainda precisa de ser calculada à mão depois de
todas as sementes estarem treinadas e avaliadas.

## 2026-09-15 — Sessão 3: algoritmos de comparação (Q-learning, PPO, A2C)

O autor pediu para comparar o DQN com outros algoritmos e escolher o de
melhor resultado. Isto muda a arquitectura fechada do `CLAUDE.md`
(secção 3, "não mudar sem justificação forte"), por isso parei e
confirmei o âmbito antes de avançar (pergunta feita, respondida
explicitamente): algoritmos de RL a sério (não só baselines não-RL do
SUMO), usando `stable-baselines3` em vez de implementar PPO/A2C à mão
(implementar PPO correctamente à mão tem muitos detalhes subtis, risco
de bugs que invalidam a comparação). Algoritmos escolhidos: Q-learning
tabular (pedido à parte pelo autor, depois da primeira pergunta), PPO, e
A2C.

**Nova pasta `algoritmos_comparacao/`** (separada de `agente_dqn/`,
pedido explícito do autor):
- `qlearning_agent.py` — Q-learning tabular. O estado do ambiente
  continua a ser o vector de 17 valores (não mudou o `sumo_env.py`), mas
  uma tabela não aguenta essa dimensão, por isso este agente agrega o
  estado em 3 números discretos (fila total, espera total, fase) antes
  de o usar como chave. É uma limitação conhecida dos métodos tabulares,
  documentada, não uma redefinição do problema.
- `treinar_qlearning.py` — mesma interface/formato de CSV que
  `agente_dqn/train.py`.
- `sumo_gym_env.py` — adapta `AmbienteSumo` à interface `gymnasium.Env`
  exigida pelo `stable-baselines3`.
- `treinar_ppo_a2c.py` — treina PPO ou A2C.
- `comparar_algoritmos.py` — gráfico com os 4 algoritmos juntos, diz
  qual teve melhor recompensa no último episódio.

**Bug real encontrado e corrigido ao testar o PPO:** os primeiros testes
pareciam mostrar episódios a terminar muito mais cedo do que deviam
(327s em vez de ~3600s). Investigação: isolei o wrapper Gym sem o
`stable-baselines3` (confirmou 724 passos até terminar, correcto);
o problema era o PPO recolher por omissão 2048 passos antes de
actualizar a política, mais do que um episódio inteiro (~720 passos),
cortando episódios a meio de forma inesperada. Corrigido com
`n_steps=720` (igual à duração de um episódio). Depois de corrigir,
confirmei que o CSV ficava com exactamente o número certo de linhas,
sem entradas falsas; a confusão inicial sobre "327s" era só ordenação
de mensagens em buffer, não um bug real nos dados.

**Validado:** auto-teste do Q-learning, treino real curto de cada um dos
3 algoritmos (2-3 episódios, localmente), e o gráfico de comparação, com
dados reais dos 3 (o DQN já tinha dados do Colab). Sem erros.

**Acidente evitado:** ao limpar ficheiros de teste, apaguei por engano
`outputs/treino_baixo_fluxo.csv`, que continha o resultado real do
primeiro treino do DQN no Colab (não um ficheiro de teste). Recuperado
com `git checkout` (estava commitado). Cuidado a reter: os nomes dos
CSVs de teste e dos resultados reais são muito parecidos, confirmar
sempre antes de apagar em lote.

**Pendente:**
- Treinar as 5 sementes × 100 episódios de cada algoritmo novo (Q-learning,
  PPO, A2C), para os 2 cenários, tal como já está a acontecer com o DQN.
- Depois de todos terminados, `comparar_algoritmos.py` para decidir qual
  fica na tese como algoritmo principal.
- Actualizar Capítulos II e IV com a comparação, só depois dos resultados
  finais e com confirmação do autor (regra do `CLAUDE.md`, secção 8/9).

## 2026-09-15 — Sessão 3: reinício de sessão Colab, checkpoint não encontrado

A sessão Colab do treino do DQN desligou (perdeu o clone, `/content` só
tinha `sample_data`). Ao recomeçar, a célula 5 não mostrou "retomado do
checkpoint": o checkpoint da semente 0 (feito antes desta sessão, ~20
episódios) tinha sido gravado na pasta antiga do Drive
(`pfc_checkpoints_dqn/baixo_fluxo_semente0/`, de quando cada sessão
gravava numa pasta própria), e a célula 4b já aponta para a pasta nova
partilhada (`pfc_checkpoints_dqn/baixo_fluxo/`), por isso não o
encontrou. Dada a pequena quantidade de progresso em causa (~20 de 500
episódios totais), decisão prática: deixar recomeçar do zero em vez de
mover os ficheiros à mão entre pastas do Drive.

## Como usar este ficheiro

Cada sessão de trabalho futura deve acrescentar uma secção nova aqui, com
data, o que foi feito, porquê, e o que ficou pendente. Não reescrever
secções antigas, só corrigir factos errados se descobertos depois.
