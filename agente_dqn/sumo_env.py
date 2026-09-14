"""
Ambiente SUMO/TraCI para o agente DQN de controlo semaforico.

Interseccao adaptada de uma rede de referencia (Desktop/antigravity sumo/,
conducao a esquerda nativa de Mocambique), ver PROGRESSO.md (sessao 2,
"adaptacao da rede antigravity sumo, tomada 2") para o historico completo
desta mudanca. Tem 5 aproximacoes: Eduardo Mondlane com faixa central (so
carros) e faixa lateral (chapas/autocarros/carros) em cada sentido, mais
Salvador Allende (sentido unico).

Espaco de estados: vector de 17 valores, um por FAIXA (nao por via inteira):
    [fila_faixa_1, ..., fila_faixa_8, espera_faixa_1, ..., espera_faixa_8, fase_actual]
As 8 faixas sao, por ordem: EM central Este (2), EM lateral Este (1),
EM central Oeste (2), EM lateral Oeste (1), SA (2), ver ARESTAS_ENTRADA e
FAIXAS_ENTRADA abaixo para a ordem exacta e os IDs nativos.
Espaco de accoes: discreto, 2 valores
    0 = manter a fase actual
    1 = mudar de fase
Recompensa: negativo da soma dos tempos de espera em todas as faixas,
menos uma penalizacao de 5.0 se a accao mudou de fase.
"""

import os
import sys
import xml.etree.ElementTree as ET

if "SUMO_HOME" not in os.environ:
    raise EnvironmentError("Variavel SUMO_HOME nao definida. Configura o SUMO antes de correr o agente.")
sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))

import traci  # noqa: E402

# Arestas de entrada da interseccao (IDs da rede adaptada, ver
# routes/routes.rou.xml para o detalhe dos movimentos de cada uma).
ARESTAS_ENTRADA = {
    "EM_central_E": "mondlane_WN_cen_in",
    "EM_lateral_E": "mondlane_WN_lat_in",
    "EM_central_O": "mondlane_ES_cen_in",
    "EM_lateral_O": "mondlane_ES_lat_in",
    "SA":           "allende_N_in",
}

CAMINHO_NET = os.path.join(os.path.dirname(__file__), "..", "net", "eduardo_mondlane_salvador_allende.net.xml")


def _faixas_de_veiculos(caminho_net, aresta_id):
    """Devolve os IDs das faixas de uma aresta que permitem veiculos
    motorizados, por ordem de indice. Exclui faixas so de peoes (a rede tem
    passeios com faixa propria em Eduardo Mondlane, ver PROGRESSO.md) em vez
    de assumir um numero de faixas fixo, para nao partir se a rede voltar a
    ser regerada com uma disposicao de faixas diferente."""
    arvore = ET.parse(caminho_net)
    aresta = arvore.getroot().find(f".//edge[@id='{aresta_id}']")
    faixas = [l for l in aresta.findall("lane") if l.get("allow") != "pedestrian"]
    return [l.get("id") for l in sorted(faixas, key=lambda l: int(l.get("index")))]


# Faixas de cada aresta de entrada, por ordem (indice 0 = mais a direita no
# sentido de marcha). O estado observa por faixa, nao por via inteira,
# porque a Avenida Eduardo Mondlane tem uma faixa de acesso local separada
# das centrais por um separador fisico (ver PROGRESSO.md).
FAIXAS_ENTRADA = [
    faixa
    for aresta in ARESTAS_ENTRADA.values()
    for faixa in _faixas_de_veiculos(CAMINHO_NET, aresta)
]

ID_SEMAFORO = "TL_MAIN"

# Indices das fases no tlLogic (net/eduardo_mondlane_salvador_allende.net.xml).
# 0=verde EM(40s) 1=amarelo EM(3s) 2=vermelho geral(2s)
# 3=verde SA(40s) 4=amarelo SA(3s) 5=vermelho geral(2s)
# O vermelho geral (clareamento) foi acrescentado apos um teste ter
# detectado uma colisao real sem essa margem de seguranca entre as fases
# (ver PROGRESSO.md); o verde de cada lado desceu de 42s para 40s para
# manter a duracao total do ciclo igual (90s).
FASE_VERDE_EM = 0
FASE_AMARELA_EM = 1
FASE_VERMELHO_EM = 2
FASE_VERDE_SA = 3
FASE_AMARELA_SA = 4
FASE_VERMELHO_SA = 5
DURACAO_AMARELO = 3
DURACAO_VERMELHO_GERAL = 2

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
            # Entra na fase amarela e depois no vermelho geral de
            # clareamento, antes de mudar para o verde do outro lado.
            if fase_actual == FASE_VERDE_EM:
                fase_amarela, fase_vermelho = FASE_AMARELA_EM, FASE_VERMELHO_EM
            else:
                fase_amarela, fase_vermelho = FASE_AMARELA_SA, FASE_VERMELHO_SA
            traci.trafficlight.setPhase(ID_SEMAFORO, fase_amarela)
            for _ in range(DURACAO_AMARELO):
                traci.simulationStep()
            traci.trafficlight.setPhase(ID_SEMAFORO, fase_vermelho)
            for _ in range(DURACAO_VERMELHO_GERAL):
                traci.simulationStep()
            restante = INTERVALO_DECISAO - DURACAO_AMARELO - DURACAO_VERMELHO_GERAL
        else:
            restante = INTERVALO_DECISAO

        for _ in range(max(restante, 1)):
            traci.simulationStep()

        proximo_estado = self._obter_estado()
        recompensa = self._calcular_recompensa(mudou_fase)
        terminado = traci.simulation.getMinExpectedNumber() <= 0

        return proximo_estado, recompensa, terminado

    def _obter_estado(self):
        filas = [traci.lane.getLastStepHaltingNumber(f) for f in FAIXAS_ENTRADA]
        esperas = [traci.lane.getWaitingTime(f) for f in FAIXAS_ENTRADA]
        fase = traci.trafficlight.getPhase(ID_SEMAFORO)
        # Normaliza a fase para 0 (grupo EM) ou 1 (grupo SA), ignorando os
        # sub-estados amarelo/vermelho geral transitorios, para manter o
        # valor coerente com o significado de "fase actual" no estado.
        fase_normalizada = 0 if fase in (FASE_VERDE_EM, FASE_AMARELA_EM, FASE_VERMELHO_EM) else 1
        return filas + esperas + [fase_normalizada]

    def _calcular_recompensa(self, mudou_fase):
        esperas = [traci.lane.getWaitingTime(f) for f in FAIXAS_ENTRADA]
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
    tamanho_esperado = 2 * len(FAIXAS_ENTRADA) + 1
    assert len(estado) == tamanho_esperado, f"estado devia ter {tamanho_esperado} valores, tem {len(estado)}"
    for i in range(20):
        _, recompensa, terminado = ambiente.step(i % 2)
        assert isinstance(recompensa, float) or isinstance(recompensa, int)
        if terminado:
            break
    ambiente.fechar()
    print(f"demo() ok: estado com {tamanho_esperado} valores, step() funcional.")


if __name__ == "__main__":
    demo()
