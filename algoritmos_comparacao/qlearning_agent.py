"""
Agente Q-learning tabular, para comparar com o DQN (rede neuronal) e com
PPO/A2C (stable-baselines3, treinar_ppo_a2c.py).

Ve o mesmo estado/accao/recompensa que os outros (sumo_env.AmbienteSumo),
mas uma tabela nao aguenta um estado continuo de 17 valores (o numero de
combinacoes possiveis explode). Este agente agrega o estado em 3 numeros
discretos antes de o usar como chave da tabela: fila total (soma das 8
faixas), espera total, e fase actual. E uma limitacao conhecida dos
metodos tabulares, nao uma redefinicao do problema, o ambiente continua a
dar o estado completo de 17 valores a todos os agentes, so este escolhe
perder detalhe para caber numa tabela (ver PROGRESSO.md).
"""

import random
from collections import defaultdict

NUM_BINS_FILA = 5
NUM_BINS_ESPERA = 5
# Calibrado por medicao real nos 2 cenarios (ver PROGRESSO.md): fila total
# max ~16-18 veiculos, espera total max ~500-600s. Os valores antigos
# (10 e 480) cobriam uma escala ate 5x maior do que esta interseccao produz,
# por isso quase todos os episodios cabiam no bin 0, colapsando o Q-learning
# a so 1-2 estados distintos.
FILA_POR_BIN = 4        # veiculos (soma das 8 faixas) por cada nivel discreto
ESPERA_POR_BIN = 120     # segundos (soma das 8 faixas) por cada nivel discreto


def discretizar(estado):
    """Reduz o vector de estado de 17 valores a uma chave (fila, espera, fase)."""
    n = (len(estado) - 1) // 2
    filas = estado[:n]
    esperas = estado[n:2 * n]
    fase = int(estado[-1])
    bin_fila = min(int(sum(filas) / FILA_POR_BIN), NUM_BINS_FILA - 1)
    bin_espera = min(int(sum(esperas) / ESPERA_POR_BIN), NUM_BINS_ESPERA - 1)
    return (bin_fila, bin_espera, fase)


class AgenteQLearning:
    def __init__(self, semente=None, alfa=0.1, gamma=0.95, epsilon_inicial=1.0,
                 epsilon_minimo=0.05, epsilon_decaimento=0.995):
        if semente is not None:
            random.seed(semente)
        self.q = defaultdict(lambda: [0.0, 0.0])
        self.alfa = alfa
        self.gamma = gamma
        self.epsilon = epsilon_inicial
        self.epsilon_minimo = epsilon_minimo
        self.epsilon_decaimento = epsilon_decaimento

    def escolher_accao(self, estado):
        if random.random() < self.epsilon:
            return random.randint(0, 1)
        valores = self.q[discretizar(estado)]
        return 0 if valores[0] >= valores[1] else 1

    def actualizar(self, estado, accao, recompensa, proximo_estado, terminado):
        chave = discretizar(estado)
        alvo = recompensa
        if not terminado:
            alvo += self.gamma * max(self.q[discretizar(proximo_estado)])
        self.q[chave][accao] += self.alfa * (alvo - self.q[chave][accao])

    def fim_de_episodio(self):
        self.epsilon = max(self.epsilon_minimo, self.epsilon * self.epsilon_decaimento)


def demo():
    """Auto-teste minimo: confirma que escolher_accao/actualizar funcionam
    e que a tabela cresce com experiencia nova."""
    estado = [1.0] * 17
    proximo_estado = [2.0] * 17

    agente = AgenteQLearning(semente=0)
    accao = agente.escolher_accao(estado)
    assert accao in (0, 1)
    agente.actualizar(estado, accao, -10.0, proximo_estado, False)
    assert len(agente.q) >= 1
    valor_antes = agente.q[discretizar(estado)][accao]
    agente.actualizar(estado, accao, -10.0, proximo_estado, False)
    assert agente.q[discretizar(estado)][accao] != valor_antes or valor_antes == 0.0
    agente.fim_de_episodio()
    assert agente.epsilon < 1.0
    print("demo() ok: escolha de accao, actualizacao da tabela e decaimento de epsilon funcionam.")


if __name__ == "__main__":
    demo()
