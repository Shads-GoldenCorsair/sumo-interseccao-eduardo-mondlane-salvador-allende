# Algoritmos de comparação (Q-learning, PPO, A2C)

Complementa o DQN (`agente_dqn/`), o algoritmo principal desta tese, com
mais três algoritmos treinados no **mesmo ambiente, mesmo estado, mesma
acção, mesma recompensa** (`agente_dqn/sumo_env.py`, só muda o algoritmo
de decisão), para poder comparar directamente e escolher o de melhor
resultado.

**Decisão explícita do autor**, sinalizada no `CLAUDE.md`: isto muda a
arquitectura fechada da tese (secção 3, "Algoritmo: DQN"), tem de se
reflectir nos Capítulos II e IV quando o autor confirmar os resultados
finais.

## Ficheiros

- `qlearning_agent.py` — Q-learning tabular. Como uma tabela não aguenta
  o estado contínuo de 17 valores, agrega-o em 3 números discretos (fila
  total, espera total, fase). Auto-teste: `python qlearning_agent.py`.
- `treinar_qlearning.py` — treino, mesma interface de linha de comando e
  formato de CSV que `agente_dqn/train.py`.
- `sumo_gym_env.py` — adapta `agente_dqn/sumo_env.AmbienteSumo` à
  interface `gymnasium.Env`, exigida pelo `stable-baselines3`.
- `treinar_ppo_a2c.py` — treina PPO ou A2C (`stable-baselines3`).
- `comparar_algoritmos.py` — junta os 4 CSVs de resultados (DQN,
  Q-learning, PPO, A2C) num só gráfico, e diz qual teve a melhor
  recompensa no último episódio.

## Instalar

Usa o mesmo ambiente virtual do `agente_dqn/` (Python 3.11), só precisa de
mais duas bibliotecas:

```bash
cd agente_dqn
.venv/Scripts/pip install -r ../algoritmos_comparacao/requirements.txt
```

## Treinar

```bash
cd algoritmos_comparacao
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
../agente_dqn/.venv/Scripts/python treinar_qlearning.py --cenario pico --episodios 100 --sementes 5
../agente_dqn/.venv/Scripts/python treinar_ppo_a2c.py --algoritmo ppo --cenario pico --episodios 100 --sementes 5
../agente_dqn/.venv/Scripts/python treinar_ppo_a2c.py --algoritmo a2c --cenario pico --episodios 100 --sementes 5
```

Repetir para `--cenario baixo_fluxo`. O DQN treina-se à parte, com
`agente_dqn/train.py` (ver o `README.md` desse módulo).

## Comparar

Depois de teres resultados de pelo menos 2 algoritmos:

```bash
../agente_dqn/.venv/Scripts/python comparar_algoritmos.py --cenario pico
```

## Simplificações conhecidas

- **Q-learning** não tem checkpoint/resume (ao contrário do DQN). O
  treino tabular é bem mais rápido de repetir do zero do que o DQN, por
  isso não se considerou necessário para já.
- **Q-learning**, a discretização do estado (fila total ÷10, espera
  total ÷480, em 5 níveis cada) é uma escolha grosseira, não afinada; se
  o Q-learning tiver um desempenho muito fraco na comparação final, vale
  a pena rever estes limiares antes de concluir que o método é inferior.
- **PPO** usa `n_steps` igual à duração de um episódio (~720 passos),
  para o `stable-baselines3` não cortar episódios a meio ao recolher a
  amostra para actualizar a política.
