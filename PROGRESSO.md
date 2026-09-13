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

## Como usar este ficheiro

Cada sessão de trabalho futura deve acrescentar uma secção nova aqui, com
data, o que foi feito, porquê, e o que ficou pendente. Não reescrever
secções antigas, só corrigir factos errados se descobertos depois.
