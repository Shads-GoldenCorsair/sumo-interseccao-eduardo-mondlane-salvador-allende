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

## Como usar este ficheiro

Cada sessão de trabalho futura deve acrescentar uma secção nova aqui, com
data, o que foi feito, porquê, e o que ficou pendente. Não reescrever
secções antigas, só corrigir factos errados se descobertos depois.
