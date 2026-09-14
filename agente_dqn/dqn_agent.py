"""
Agente Deep Q-Network (Mnih et al., 2015): rede neuronal, experience replay
e rede-alvo, tal como decidido no CLAUDE.md (seccao 3).
"""

import random
from collections import deque

import numpy as np
from tensorflow import keras

TAMANHO_ESTADO = 17  # 8 faixas x (fila + espera) + fase actual, ver sumo_env.py
NUM_ACCOES = 2
TAMANHO_BUFFER = 10000
ACTUALIZAR_REDE_ALVO_CADA = 5  # episodios


def construir_rede(tamanho_estado=TAMANHO_ESTADO, num_accoes=NUM_ACCOES):
    modelo = keras.Sequential([
        keras.layers.Input(shape=(tamanho_estado,)),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dense(num_accoes, activation="linear"),
    ])
    modelo.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse")
    return modelo


class AgenteDQN:
    def __init__(self, semente=None, gamma=0.95, epsilon_inicial=1.0,
                 epsilon_minimo=0.05, epsilon_decaimento=0.995, tamanho_lote=64):
        if semente is not None:
            random.seed(semente)
            np.random.seed(semente)

        self.rede = construir_rede()
        self.rede_alvo = construir_rede()
        self.rede_alvo.set_weights(self.rede.get_weights())

        self.buffer = deque(maxlen=TAMANHO_BUFFER)
        self.gamma = gamma
        self.epsilon = epsilon_inicial
        self.epsilon_minimo = epsilon_minimo
        self.epsilon_decaimento = epsilon_decaimento
        self.tamanho_lote = tamanho_lote

    def escolher_accao(self, estado):
        if random.random() < self.epsilon:
            return random.randint(0, NUM_ACCOES - 1)
        # Chamada directa ao modelo (nao .predict()) para inferencia de uma
        # so amostra: .predict() tem overhead fixo por chamada (dataset
        # adapter, callbacks) que domina o tempo quando chamado a cada
        # decisao; para lotes grandes o overhead deixa de pesar, por isso
        # o treino em lote (treinar_lote) continua a usar .predict().
        q_valores = self.rede(np.array([estado]), training=False).numpy()[0]
        return int(np.argmax(q_valores))

    def guardar_transicao(self, estado, accao, recompensa, proximo_estado, terminado):
        self.buffer.append((estado, accao, recompensa, proximo_estado, terminado))

    def treinar_lote(self):
        if len(self.buffer) < self.tamanho_lote:
            return None

        lote = random.sample(self.buffer, self.tamanho_lote)
        estados = np.array([t[0] for t in lote])
        accoes = np.array([t[1] for t in lote])
        recompensas = np.array([t[2] for t in lote])
        proximos_estados = np.array([t[3] for t in lote])
        terminados = np.array([t[4] for t in lote])

        q_actuais = self.rede.predict(estados, verbose=0)
        q_proximos = self.rede_alvo.predict(proximos_estados, verbose=0)

        alvos = q_actuais.copy()
        for i in range(self.tamanho_lote):
            alvo = recompensas[i]
            if not terminados[i]:
                alvo += self.gamma * np.max(q_proximos[i])
            alvos[i][accoes[i]] = alvo

        historico = self.rede.fit(estados, alvos, epochs=1, verbose=0)
        self.epsilon = max(self.epsilon_minimo, self.epsilon * self.epsilon_decaimento)
        return historico.history["loss"][0]

    def actualizar_rede_alvo(self):
        self.rede_alvo.set_weights(self.rede.get_weights())

    def guardar_pesos(self, caminho):
        self.rede.save_weights(caminho)

    def carregar_pesos(self, caminho):
        self.rede.load_weights(caminho)
        self.rede_alvo.set_weights(self.rede.get_weights())


def demo():
    """Auto-teste minimo: enche o buffer com transicoes falsas, confirma que
    treinar_lote() so actua quando ha dados suficientes, e que a rede-alvo
    fica igual apos actualizar_rede_alvo()."""
    agente = AgenteDQN(semente=0, tamanho_lote=8)

    assert agente.treinar_lote() is None, "nao devia treinar com buffer vazio"

    for _ in range(20):
        estado = np.random.rand(TAMANHO_ESTADO).tolist()
        proximo_estado = np.random.rand(TAMANHO_ESTADO).tolist()
        agente.guardar_transicao(estado, random.randint(0, 1), -10.0, proximo_estado, False)

    perda = agente.treinar_lote()
    assert perda is not None, "devia treinar com buffer com dados suficientes"

    agente.actualizar_rede_alvo()
    for w1, w2 in zip(agente.rede.get_weights(), agente.rede_alvo.get_weights()):
        assert np.allclose(w1, w2), "rede-alvo devia ficar igual a rede principal"

    print("demo() ok: buffer, treino e actualizacao da rede-alvo funcionam.")


if __name__ == "__main__":
    demo()
