"""
Avalia um agente ja treinado: carrega os pesos gravados por train.py,
corre um episodio completo sem exploracao aleatoria (epsilon=0, so decisoes
"a serio" da rede), e compara a espera media resultante com o baseline de
tempo fixo (outputs/tripinfo_<cenario>.xml).

Uso:
    python avaliar_agente.py --cenario baixo_fluxo --semente 0
    python avaliar_agente.py --cenario pico --semente 0 --gui

--gui abre o sumo-gui, para veres o agente a decidir ao vivo (so funciona
numa maquina com ecra, nao no Colab).
"""

import argparse
import os
import xml.etree.ElementTree as ET

from dqn_agent import AgenteDQN
from sumo_env import AmbienteSumo

RAIZ = os.path.dirname(__file__)
PASTA_MODELOS = os.path.join(RAIZ, "..", "outputs", "modelos_treinados")
PASTA_SCRATCH = os.path.join(RAIZ, "..", "outputs", "_treino_scratch")


def espera_media(caminho_tripinfo):
    """Le um ficheiro tripinfo.xml e devolve a espera media (segundos)."""
    if not os.path.exists(caminho_tripinfo):
        return None
    viagens = ET.parse(caminho_tripinfo).getroot().findall("tripinfo")
    if not viagens:
        return None
    esperas = [float(v.get("waitingTime")) for v in viagens]
    return sum(esperas) / len(esperas), len(esperas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    parser.add_argument("--semente", type=int, default=0, help="Semente cujo modelo carregar")
    parser.add_argument("--pesos", default=None, help="Caminho directo para um .weights.h5 (substitui --semente)")
    parser.add_argument("--gui", action="store_true", help="Abre o sumo-gui (precisa de ecra)")
    args = parser.parse_args()

    caminho_pesos = args.pesos or os.path.join(PASTA_MODELOS, f"{args.cenario}_semente{args.semente}.weights.h5")
    if not os.path.exists(caminho_pesos):
        print(f"Nao encontrado: {caminho_pesos}")
        print("O treino ainda nao terminou para esta semente/cenario, ou o modelo ainda nao foi copiado do Colab (git pull).")
        return

    caminho_sumocfg = os.path.join(RAIZ, "..", "config", f"{args.cenario}.sumocfg")
    agente = AgenteDQN()
    agente.carregar_pesos(caminho_pesos)
    agente.epsilon = 0.0  # sem exploracao: so decisoes "a serio" da rede treinada

    ambiente = AmbienteSumo(caminho_sumocfg, usar_gui=args.gui)
    estado = ambiente.reset()
    recompensa_total = 0.0
    terminado = False
    while not terminado:
        accao = agente.escolher_accao(estado)
        estado, recompensa, terminado = ambiente.step(accao)
        recompensa_total += recompensa
    ambiente.fechar()

    print(f"\nRecompensa total do episodio de avaliacao: {recompensa_total:.1f}")

    resultado_agente = espera_media(os.path.join(PASTA_SCRATCH, "tripinfo.xml"))
    resultado_baseline = espera_media(os.path.join(RAIZ, "..", "outputs", f"tripinfo_{args.cenario}.xml"))

    if resultado_agente:
        media_agente, n_agente = resultado_agente
        print(f"Espera media com o agente treinado: {media_agente:.1f}s ({n_agente} viagens)")
    if resultado_baseline:
        media_baseline, n_baseline = resultado_baseline
        print(f"Espera media do baseline (tempo fixo): {media_baseline:.1f}s ({n_baseline} viagens)")
    if resultado_agente and resultado_baseline:
        diferenca = media_baseline - media_agente
        sinal = "melhor" if diferenca > 0 else "pior"
        print(f"Diferenca: {abs(diferenca):.1f}s {sinal} que o baseline ({abs(diferenca) / media_baseline * 100:.1f}%)")


if __name__ == "__main__":
    main()
