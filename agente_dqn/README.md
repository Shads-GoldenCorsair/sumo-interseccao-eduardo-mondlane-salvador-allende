# Agente DQN — Controlo Semaforico

Implementacao do agente Deep Q-Network (Mnih et al., 2015) para a
interseccao Avenida Eduardo Mondlane / Avenida Salvador Allende, Maputo.
Ver `CLAUDE.md` (raiz do projecto) para o contexto completo do PFC e
`PROGRESSO.md` para o historico de decisoes.

## Ambiente

Este modulo usa **Python 3.11** num ambiente virtual proprio, porque o
TensorFlow ainda nao suporta o Python 3.14 instalado no resto da maquina.

```bash
cd agente_dqn
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

`traci` nao precisa de ser instalado por pip: e importado directamente de
`%SUMO_HOME%/tools`, que os scripts adicionam ao `sys.path` automaticamente
(exige a variavel de ambiente `SUMO_HOME` definida).

## Ficheiros

- `sumo_env.py` — wrapper do SUMO/TraCI (estado, accao, recompensa).
  Corre `python sumo_env.py` para um auto-teste rapido.
- `dqn_agent.py` — rede neuronal, experience replay, rede-alvo. Corre
  `python dqn_agent.py` para um auto-teste rapido.
- `train.py` — treino com multiplas sementes.

## Treino

```bash
.venv/Scripts/python train.py --cenario baixo_fluxo --episodios 100 --sementes 5
.venv/Scripts/python train.py --cenario pico --episodios 100 --sementes 5
```

100 episodios e o valor de trabalho actual (ver PROGRESSO.md), nao o valor
final da tese; ajustar para cima se a curva de recompensa nao estabilizar.
Tempo estimado nesta maquina: ~15h (baixo fluxo) + ~55h (pico) para as 5
sementes, por ser sequencial e por cenario ter muito mais veiculos.

## Treino completo no Google Colab

Para nao ocupar a maquina local durante horas, `treino_colab.ipynb` corre o
treino no Colab. Cada sessao Colab treina **uma semente** (usa
`--semente-unica`), para poderes abrir varias sessoes em paralelo, uma por
semente. No fim, junta os CSVs de cada semente com:

```bash
.venv/Scripts/python juntar_resultados.py --cenario pico
.venv/Scripts/python juntar_resultados.py --cenario baixo_fluxo
```

Isto gera `../outputs/treino_<cenario>.csv` (todas as sementes juntas) e
reporta a media/desvio-padrao da recompensa final, exigidos pelo
`CLAUDE.md` (secção 3).

Resultados por episodio e semente em `../outputs/treino_<cenario>.csv`.

## Formulacao (nao mudar sem sinalizar no CLAUDE.md)

- Estado: vector de 7 valores (3 filas + 3 esperas acumuladas + 1 fase
  actual). Era 9/4 no plano inicial; reduzido a 3 aproximacoes porque a
  interseccao real tem 3, nao 4 (ver PROGRESSO.md).
- Accao: 0 = manter fase, 1 = mudar fase.
- Recompensa: `-soma(esperas)`, menos 5.0 se a accao mudou de fase.
