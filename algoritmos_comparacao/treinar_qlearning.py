"""
Script de treino do agente Q-learning tabular, para comparar com o DQN
(agente_dqn/train.py) e com PPO/A2C (treinar_ppo_a2c.py). Mesma interface
de linha de comando e mesmo formato de CSV de saida do treino do DQN, para
os resultados serem directamente comparaveis (ver PROGRESSO.md).

Uso:
    python treinar_qlearning.py --cenario pico --episodios 100 --sementes 5
"""

import argparse
import csv
import os
import sys

from qlearning_agent import AgenteQLearning

RAIZ = os.path.dirname(__file__)
sys.path.append(os.path.join(RAIZ, "..", "agente_dqn"))
from sumo_env import AmbienteSumo  # noqa: E402


def correr_episodio(ambiente, agente):
    estado = ambiente.reset()
    recompensa_total = 0.0
    terminado = False
    while not terminado:
        accao = agente.escolher_accao(estado)
        proximo_estado, recompensa, terminado = ambiente.step(accao)
        agente.actualizar(estado, accao, recompensa, proximo_estado, terminado)
        estado = proximo_estado
        recompensa_total += recompensa
    agente.fim_de_episodio()
    return recompensa_total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    parser.add_argument("--episodios", type=int, default=100)
    parser.add_argument("--sementes", type=int, default=5)
    args = parser.parse_args()

    caminho_sumocfg = os.path.join(RAIZ, "..", "config", f"{args.cenario}.sumocfg")
    caminho_csv = os.path.join(RAIZ, "..", "outputs", f"treino_{args.cenario}_qlearning.csv")

    with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["semente", "episodio", "recompensa"])
        for semente in range(args.sementes):
            agente = AgenteQLearning(semente=semente)
            ambiente = AmbienteSumo(caminho_sumocfg)
            for episodio in range(args.episodios):
                recompensa = correr_episodio(ambiente, agente)
                escritor.writerow([semente, episodio + 1, recompensa])
                f.flush()
                print(f"[qlearning] semente={semente} episodio={episodio + 1}/{args.episodios} "
                      f"recompensa={recompensa:.1f} epsilon={agente.epsilon:.3f} estados_vistos={len(agente.q)}")
            ambiente.fechar()

    print(f"Resultados em {caminho_csv}")


if __name__ == "__main__":
    main()
