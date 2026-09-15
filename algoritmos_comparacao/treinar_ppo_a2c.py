"""
Treina PPO ou A2C (stable-baselines3) no mesmo ambiente do DQN
(sumo_gym_env.SumoGymEnv), para comparar com o DQN (agente_dqn/train.py)
e o Q-learning tabular (treinar_qlearning.py). Mesmo formato de CSV de
saida.

Uso:
    python treinar_ppo_a2c.py --algoritmo ppo --cenario pico --episodios 100 --sementes 5
    python treinar_ppo_a2c.py --algoritmo a2c --cenario pico --episodios 100 --sementes 5
"""

import argparse
import csv
import os

from stable_baselines3 import A2C, PPO
from stable_baselines3.common.callbacks import BaseCallback

from sumo_gym_env import SumoGymEnv

RAIZ = os.path.dirname(__file__)
PASTA_MODELOS = os.path.join(RAIZ, "..", "outputs", "modelos_treinados")

ALGORITMOS = {"ppo": PPO, "a2c": A2C}

# Passos de decisao por episodio: 3600s de simulacao / 5s por decisao
# (INTERVALO_DECISAO em agente_dqn/sumo_env.py).
PASSOS_POR_EPISODIO = 720


class RegistarRecompensaPorEpisodio(BaseCallback):
    """Regista a recompensa total de cada episodio no CSV, ao estilo dos
    outros scripts de treino do projecto (train.py, treinar_qlearning.py)."""

    def __init__(self, escritor, ficheiro, semente, algoritmo):
        super().__init__()
        self.escritor = escritor
        self.ficheiro = ficheiro
        self.semente = semente
        self.algoritmo = algoritmo
        self.episodio = 0
        self.recompensa_actual = 0.0

    def _on_step(self):
        self.recompensa_actual += self.locals["rewards"][0]
        if self.locals["dones"][0]:
            self.episodio += 1
            self.escritor.writerow([self.semente, self.episodio, self.recompensa_actual])
            self.ficheiro.flush()
            print(f"[{self.algoritmo}] semente={self.semente} episodio={self.episodio} "
                  f"recompensa={self.recompensa_actual:.1f}")
            self.recompensa_actual = 0.0
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algoritmo", choices=list(ALGORITMOS), required=True)
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    parser.add_argument("--episodios", type=int, default=100)
    parser.add_argument("--sementes", type=int, default=5)
    args = parser.parse_args()

    caminho_sumocfg = os.path.join(RAIZ, "..", "config", f"{args.cenario}.sumocfg")
    caminho_csv = os.path.join(RAIZ, "..", "outputs", f"treino_{args.cenario}_{args.algoritmo}.csv")
    os.makedirs(PASTA_MODELOS, exist_ok=True)

    ClasseAlgoritmo = ALGORITMOS[args.algoritmo]

    with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["semente", "episodio", "recompensa"])

        for semente in range(args.sementes):
            ambiente = SumoGymEnv(caminho_sumocfg)
            # n_steps: por omissao o PPO recolhe 2048 passos antes de
            # actualizar a politica, mais do que um episodio inteiro
            # (~720 passos), o que faz cortar episodios a meio de forma
            # inesperada. Alinhado com a duracao real de um episodio.
            kwargs = {"n_steps": PASSOS_POR_EPISODIO} if args.algoritmo == "ppo" else {}
            modelo = ClasseAlgoritmo("MlpPolicy", ambiente, seed=semente, verbose=0, **kwargs)
            callback = RegistarRecompensaPorEpisodio(escritor, f, semente, args.algoritmo)
            modelo.learn(total_timesteps=PASSOS_POR_EPISODIO * args.episodios, callback=callback)
            modelo.save(os.path.join(PASTA_MODELOS, f"{args.cenario}_semente{semente}_{args.algoritmo}"))
            ambiente.close()

    print(f"Resultados em {caminho_csv}")


if __name__ == "__main__":
    main()
