"""
Wrapper Gymnasium em volta de agente_dqn.sumo_env.AmbienteSumo, para poder
treinar PPO/A2C com o stable-baselines3 (que exige a interface
gymnasium.Env). Nao muda a formulacao de estado/accao/recompensa, so
adapta reset()/step() ao formato que o stable-baselines3 exige, o
ambiente por baixo e o mesmo AmbienteSumo usado pelo DQN e pelo
Q-learning.
"""

import os
import sys

import gymnasium as gym
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agente_dqn"))
from sumo_env import AmbienteSumo, FAIXAS_ENTRADA  # noqa: E402

TAMANHO_ESTADO = 2 * len(FAIXAS_ENTRADA) + 1


class SumoGymEnv(gym.Env):
    def __init__(self, caminho_sumocfg):
        super().__init__()
        self._ambiente = AmbienteSumo(caminho_sumocfg)
        self.observation_space = gym.spaces.Box(low=0, high=np.inf, shape=(TAMANHO_ESTADO,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(2)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        estado = self._ambiente.reset()
        return np.array(estado, dtype=np.float32), {}

    def step(self, accao):
        estado, recompensa, terminado = self._ambiente.step(int(accao))
        return np.array(estado, dtype=np.float32), recompensa, terminado, False, {}

    def close(self):
        self._ambiente.fechar()
