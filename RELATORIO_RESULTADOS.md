# Relatório, como ver e interpretar os resultados do treino

Este documento responde a três perguntas concretas:

1. Que dados alimentam o algoritmo, para ele aprender?
2. Onde vejo a melhoria, no SUMO e nos dados gerados?
3. Que código treina o modelo DQN, exactamente?

E dá o passo a passo completo, do treino até ao gráfico final.

---

## 1. Que dados alimentam o algoritmo

Não há um "dataset" no sentido tradicional (não é aprendizagem supervisionada,
ver `CLAUDE.md`, secção 2). O agente aprende por tentativa e erro, a partir
de três coisas que o `agente_dqn/sumo_env.py` calcula a cada 5 segundos
simulados:

| | O quê | Onde no código |
|---|---|---|
| **Estado** (o que o agente vê) | 17 números: fila de veículos e tempo de espera em cada uma das 8 faixas de entrada, mais a fase actual do semáforo | `sumo_env.py`, função `_obter_estado()` |
| **Acção** (o que o agente decide) | 0 = manter a fase do semáforo, 1 = mudar | `sumo_env.py`, função `step()` |
| **Recompensa** (o que o agente tenta maximizar) | Negativo da soma dos tempos de espera, menos 5.0 se mudou de fase | `sumo_env.py`, função `_calcular_recompensa()` |

Estes três valores vêm directamente da simulação SUMO (via TraCI), calculados
de novo a cada passo. Não existe um ficheiro de dados de treino escrito à
mão, é gerado em tempo real à medida que o agente interage com o trânsito
simulado.

---

## 2. Onde ver a melhoria

Há três formas, cada uma mostra uma coisa diferente.

### 2.1. Visualmente, no `sumo-gui` (ver o comportamento)

Isto mostra **como** o agente decide, não quanto melhorou em números.

```powershell
cd sumo_project\agente_dqn
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
.venv\Scripts\python.exe -c "from sumo_env import AmbienteSumo; a = AmbienteSumo('../config/pico.sumocfg', usar_gui=True); a.reset(); [a.step(0) for _ in range(200)]; a.fechar()"
```

Isto corre 200 decisões (cerca de 1000s simulados) com um agente **não
treinado** (pesos aleatórios), só para veres a janela a abrir. Para veres um
agente já treinado a decidir, usa `avaliar_agente.py --gui` (secção 4.5
abaixo), que carrega os pesos treinados e corre sem exploração aleatória.

**O que procurar na janela:** filas a formarem-se e esvaziarem-se junto ao
semáforo; compara mentalmente com o baseline (semáforo de tempo fixo, corre
`sumo-gui.exe -c pico.sumocfg` sem TraCI) para veres a diferença de
comportamento.

### 2.2. Nos números brutos (o CSV)

Cada episódio de treino grava uma linha em `outputs/treino_<cenario>.csv`:

```
semente,episodio,recompensa
0,1,-2884.0
0,2,-1736.0
...
```

Recompensa mais próxima de zero (menos negativa) = menos tempo de espera
total = melhor. Abre o ficheiro num editor de texto ou no Excel para ver os
números exactos.

### 2.3. No gráfico (a evolução, de relance)

Este é o mais directo para "ver a melhoria". Script novo,
`agente_dqn/graficar_resultados.py`:

```powershell
cd sumo_project\agente_dqn
.venv\Scripts\python.exe graficar_resultados.py --cenario baixo_fluxo
```

Gera `outputs/grafico_treino_baixo_fluxo.png`, uma linha por semente (fina) e
a média entre sementes (grossa, preta). Se o agente estiver a aprender, a
linha preta sobe ao longo dos episódios (fica menos negativa), com ruído
normal de exploração pelo meio, não é uma linha recta.

**Exemplo real** (1 semente, 20 episódios, cenário baixo fluxo, testado nesta
sessão): começa em -2884, sobe para uma média à volta de -1400 a -1700 no
resto dos episódios. Confirma que o agente está mesmo a aprender, não é
ruído aleatório.

### 2.4. Comparar com o baseline (o número que interessa para a tese)

O baseline de tempo fixo já está medido em `outputs/tripinfo_<cenario>.xml`
(espera média actual: 20,6s pico, 14,4s baixo fluxo, ver `PROGRESSO.md`).
Depois do treino completo, a comparação final é: espera média do agente
treinado (medida numa corrida final, sem exploração aleatória) contra estes
valores. Ainda não há um script para essa corrida final de avaliação, é
trabalho pendente depois do treino terminar (ver secção 5).

---

## 3. Que código treina o modelo, exactamente

Três ficheiros, cada um com uma responsabilidade:

### `sumo_env.py` — a ponte entre o SUMO e o agente

Não tem nada de "IA", só traduz o SUMO (via TraCI) para os três valores da
secção 1. A classe `AmbienteSumo` tem `reset()` (começa um episódio) e
`step(accao)` (aplica uma acção, avança a simulação, devolve o próximo
estado + recompensa), ao estilo do Gym/OpenAI.

### `dqn_agent.py` — a rede neuronal e a lógica de aprendizagem

- `construir_rede()`: uma rede pequena (17 entradas → 64 → 64 → 2 saídas,
  uma por acção), como manda o `CLAUDE.md`.
- Classe `AgenteDQN`:
  - `escolher_accao(estado)`: com probabilidade `epsilon`, escolhe ao acaso
    (explora); caso contrário, pergunta à rede qual a acção com maior valor
    esperado (explora o que já aprendeu). `epsilon` começa alto (1.0,
    quase tudo aleatório) e desce ao longo do treino (`epsilon_decaimento`),
    até um mínimo de 0.05.
  - `guardar_transicao(...)`: guarda (estado, acção, recompensa,
    próximo_estado) num buffer (até 10000), a "memória" do agente.
  - `treinar_lote()`: tira 64 transições ao acaso do buffer (não as mais
    recentes, para não sobre-ajustar aos últimos segundos), e ajusta os
    pesos da rede para que a previsão de cada uma fique mais próxima do
    valor real observado (a equação de Bellman do Q-learning).
  - `actualizar_rede_alvo()`: copia os pesos para uma segunda rede
    ("rede-alvo"), usada só para calcular o alvo do treino, actualizada a
    cada 5 episódios (não a cada passo), estabiliza o treino (Mnih et al.,
    2015).

### `train.py` — o ciclo principal que junta tudo

Para cada semente, para cada episódio: `reset()` → repete `escolher_accao()`
→ `step()` → `guardar_transicao()` → `treinar_lote()` até o episódio acabar
→ a cada 5 episódios, `actualizar_rede_alvo()` → grava a recompensa total no
CSV. A cada 10 episódios, grava um checkpoint (pesos + progresso), para
poder retomar se for interrompido.

---

## 4. Passo a passo completo

### 4.1. Testar rapidamente, na tua máquina (antes de confiar no Colab)

```powershell
cd sumo_project\agente_dqn
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
.venv\Scripts\python.exe -u train.py --cenario baixo_fluxo --episodios 5 --sementes 1
```

Confirma que corre sem erros e que a recompensa varia (não fica fixa).

### 4.2. Treino completo, no Google Colab

Ver `agente_dqn/treino_colab.ipynb`. Resumo: abre o notebook, corre as
células por ordem (o token do GitHub e a autorização do Drive são pedidos
nas células próprias), as 5 sementes correm seguidas numa só sessão. No
fim, a última célula envia o resultado para o GitHub.

### 4.3. Juntar os resultados e gerar o gráfico

Depois do Colab terminar e enviares (`git push`), na tua máquina:

```powershell
cd sumo_project
git pull
cd agente_dqn
.venv\Scripts\python.exe graficar_resultados.py --cenario baixo_fluxo
.venv\Scripts\python.exe graficar_resultados.py --cenario pico
```

(`juntar_resultados.py` só é preciso se correres sementes em sessões
separadas; com todas as sementes na mesma sessão do Colab, o CSV já sai
completo.)

### 4.4. Repetir para o outro cenário

Tudo o que está acima é por `CENARIO`. Corre outra vez para `pico` depois de
`baixo_fluxo` estar concluído.

### 4.5. Avaliação final, depois do treino terminar

Já existe: `agente_dqn/avaliar_agente.py`. Carrega o modelo final de uma
semente (gravado automaticamente pelo `train.py` em
`outputs/modelos_treinados/<cenario>_semente<N>.weights.h5`), corre um
episódio completo sem exploração aleatória (`epsilon=0`, só decisões "a
sério"), e compara a espera média resultante com o baseline.

```powershell
cd sumo_project\agente_dqn
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
.venv\Scripts\python.exe avaliar_agente.py --cenario baixo_fluxo --semente 0
```

Acrescenta `--gui` para veres o agente treinado a decidir ao vivo no
`sumo-gui` (só funciona localmente, não no Colab, que não tem ecrã).

**Importante:** este script mede uma corrida, não a média/desvio-padrão
entre as 5 sementes que o `CLAUDE.md` exige (secção 3) para o Capítulo V.
Para isso, corre `avaliar_agente.py` para cada semente (0 a 4) e calcula a
média/desvio-padrão à mão (ou escreve um pequeno script que o faça,
análogo ao `juntar_resultados.py`), depois de todas as sementes estarem
treinadas.

### 4.6. Por fazer, depois da avaliação de todas as sementes

- Actualizar `PROGRESSO.md` e o Capítulo V do PFC com os números finais.
