"""
Ambiente SUMO/TraCI para o agente DQN de controlo semaforico.

Interseccao real (georreferenciada): Avenida Eduardo Mondlane com Avenida
Salvador Allende, Maputo. Tem 3 aproximacoes, nao 4, porque a Avenida
Eduardo Mondlane, neste troco, e um par de vias de sentido unico (ver
PROGRESSO.md, seccao 2026-09-13, Fase 0, para o detalhe desta decisao,
tomada em conjunto com o autor).

Espaco de estados: vector de 7 valores
    [fila_EM1, fila_EM2, fila_SA, espera_EM1, espera_EM2, espera_SA, fase_actual]
Espaco de accoes: discreto, 2 valores
    0 = manter a fase actual
    1 = mudar de fase
Recompensa: negativo da soma dos tempos de espera nas 3 aproximacoes,
menos uma penalizacao de 5.0 se a accao mudou de fase.
"""

import os
import sys

if "SUMO_HOME" not in os.environ:
    raise EnvironmentError("Variavel SUMO_HOME nao definida. Configura o SUMO antes de correr o agente.")
sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))

import traci  # noqa: E402

# Arestas de entrada da interseccao real (IDs nativos do OpenStreetMap,
# gerados pelo netconvert). Ver routes/routes.rou.xml para o detalhe dos
# movimentos permitidos em cada uma.
ARESTAS_ENTRADA = {
    "EM1": "552827135#0",
    "EM2": "725127419#1",
    "SA":  "24769111#9",
}

ID_SEMAFORO = "cluster_12168401392_13673178841_13673178842_1783252720"

# Indices das fases verdes no tlLogic (net/eduardo_mondlane_salvador_allende.net.xml).
# 0 = verde EM (42s), 1 = amarelo EM (3s), 2 = verde SA (42s), 3 = amarelo SA (3s).
FASE_VERDE_EM = 0
FASE_AMARELA_EM = 1
FASE_VERDE_SA = 2
FASE_AMARELA_SA = 3
DURACAO_AMARELO = 3

PENALIZACAO_MUDANCA_FASE = 5.0

# Intervalo entre decisoes do agente, em segundos simulados. Decidir a cada
# segundo desperdica chamadas ao TensorFlow sem ganho real (nenhum semaforo
# real reavalia a fase todos os segundos); 5s e o valor tipico usado na
# literatura de RL para controlo de trafego. Nao altera a formulacao de
# estado/accao/recompensa, so a cadencia com que a accao e aplicada.
INTERVALO_DECISAO = 5


class AmbienteSumo:
    """Wrapper do SUMO/TraCI com interface reset/step, ao estilo Gym."""

    def __init__(self, caminho_sumocfg, usar_gui=False):
        self.caminho_sumocfg = caminho_sumocfg
        self.sumo_bin = "sumo-gui" if usar_gui else "sumo"
        self._ligado = False

    def reset(self):
        if self._ligado:
            traci.close()
        # Redirecciona os ficheiros de saida (tripinfo/resumo/filas)
        # configurados no .sumocfg para uma pasta de scratch: sao os mesmos
        # caminhos usados para o baseline de tempo fixo, e o treino
        # sobrescrevia-os a cada episodio (ver PROGRESSO.md). O treino nao
        # precisa destes ficheiros, so das recompensas que ja calcula via
        # TraCI; ficam reutilizados (sobrescritos) a cada episodio de
        # propósito, sao so descartaveis.
        pasta_scratch = os.path.join(os.path.dirname(__file__), "..", "outputs", "_treino_scratch")
        os.makedirs(pasta_scratch, exist_ok=True)
        traci.start([
            self.sumo_bin, "-c", self.caminho_sumocfg,
            "--no-step-log", "true", "--no-warnings", "true",
            "--tripinfo-output", os.path.join(pasta_scratch, "tripinfo.xml"),
            "--summary-output", os.path.join(pasta_scratch, "resumo.xml"),
            "--queue-output", os.path.join(pasta_scratch, "filas.xml"),
        ])
        self._ligado = True
        return self._obter_estado()

    def fechar(self):
        if self._ligado:
            traci.close()
            self._ligado = False

    def step(self, accao):
        """Aplica a accao (0=manter, 1=mudar), avanca a simulacao e devolve
        (proximo_estado, recompensa, terminado)."""
        fase_actual = traci.trafficlight.getPhase(ID_SEMAFORO)
        mudou_fase = False

        if accao == 1 and fase_actual in (FASE_VERDE_EM, FASE_VERDE_SA):
            # Entra na fase amarela correspondente antes de mudar de verde.
            fase_amarela = FASE_AMARELA_EM if fase_actual == FASE_VERDE_EM else FASE_AMARELA_SA
            traci.trafficlight.setPhase(ID_SEMAFORO, fase_amarela)
            for _ in range(DURACAO_AMARELO):
                traci.simulationStep()
            restante = INTERVALO_DECISAO - DURACAO_AMARELO
        else:
            restante = INTERVALO_DECISAO

        for _ in range(max(restante, 1)):
            traci.simulationStep()

        proximo_estado = self._obter_estado()
        recompensa = self._calcular_recompensa(mudou_fase)
        terminado = traci.simulation.getMinExpectedNumber() <= 0

        return proximo_estado, recompensa, terminado

    def _obter_estado(self):
        filas = [traci.edge.getLastStepHaltingNumber(a) for a in ARESTAS_ENTRADA.values()]
        esperas = [traci.edge.getWaitingTime(a) for a in ARESTAS_ENTRADA.values()]
        fase = traci.trafficlight.getPhase(ID_SEMAFORO)
        # Normaliza a fase para 0 (grupo EM) ou 1 (grupo SA), ignorando o
        # sub-estado amarelo transitorio, para manter o valor coerente com
        # o significado de "fase actual" usado na formulacao do estado.
        fase_normalizada = 0 if fase in (FASE_VERDE_EM, FASE_AMARELA_EM) else 1
        return filas + esperas + [fase_normalizada]

    def _calcular_recompensa(self, mudou_fase):
        esperas = [traci.edge.getWaitingTime(a) for a in ARESTAS_ENTRADA.values()]
        recompensa = -sum(esperas)
        if mudou_fase:
            recompensa -= PENALIZACAO_MUDANCA_FASE
        return recompensa


def demo():
    """Auto-teste minimo: confirma que o estado tem o tamanho certo e que
    step() aceita as duas accoes sem excepcoes, numa corrida curta."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "config", "baixo_fluxo.sumocfg")
    ambiente = AmbienteSumo(caminho)
    estado = ambiente.reset()
    assert len(estado) == 7, f"estado devia ter 7 valores, tem {len(estado)}"
    for i in range(20):
        _, recompensa, terminado = ambiente.step(i % 2)
        assert isinstance(recompensa, float) or isinstance(recompensa, int)
        if terminado:
            break
    ambiente.fechar()
    print("demo() ok: estado com 7 valores, step() funcional.")


if __name__ == "__main__":
    demo()
