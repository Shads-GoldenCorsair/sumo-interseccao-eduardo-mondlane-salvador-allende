"""
Script de treino do agente DQN, com multiplas sementes aleatorias
(CLAUDE.md, seccao 3: minimo de 5 sementes distintas, reportar media e
desvio-padrao).

Uso:
    python train.py --cenario pico --episodios 100
    python train.py --cenario baixo_fluxo --episodios 100 --sementes 5

Para correr sementes em paralelo em sessoes separadas (ex.: varios
notebooks Colab ao mesmo tempo), usa --semente-unica para treinar so uma
semente por execucao, cada uma grava o seu proprio ficheiro CSV:
    python train.py --cenario pico --episodios 100 --semente-unica 0
    python train.py --cenario pico --episodios 100 --semente-unica 1
    ...
Depois junta os CSVs (mesmas colunas) para a analise final.
"""

import argparse
import csv
import os
import statistics

from dqn_agent import AgenteDQN, ACTUALIZAR_REDE_ALVO_CADA
from sumo_env import AmbienteSumo

RAIZ = os.path.dirname(__file__)


def correr_episodio(ambiente, agente, treinar=True):
    estado = ambiente.reset()
    recompensa_total = 0.0
    terminado = False

    while not terminado:
        accao = agente.escolher_accao(estado)
        proximo_estado, recompensa, terminado = ambiente.step(accao)
        if treinar:
            agente.guardar_transicao(estado, accao, recompensa, proximo_estado, terminado)
            agente.treinar_lote()
        estado = proximo_estado
        recompensa_total += recompensa

    return recompensa_total


def treinar_uma_semente(caminho_sumocfg, semente, num_episodios):
    agente = AgenteDQN(semente=semente)
    ambiente = AmbienteSumo(caminho_sumocfg)

    recompensas = []
    for episodio in range(num_episodios):
        recompensa = correr_episodio(ambiente, agente)
        recompensas.append(recompensa)
        if (episodio + 1) % ACTUALIZAR_REDE_ALVO_CADA == 0:
            agente.actualizar_rede_alvo()
        print(f"semente={semente} episodio={episodio + 1}/{num_episodios} recompensa={recompensa:.1f} epsilon={agente.epsilon:.3f}")

    ambiente.fechar()
    return recompensas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    parser.add_argument("--episodios", type=int, default=150)
    parser.add_argument("--sementes", type=int, default=5)
    parser.add_argument("--semente-unica", type=int, default=None,
                         help="Treina so esta semente (para correr em paralelo em varias sessoes)")
    args = parser.parse_args()

    caminho_sumocfg = os.path.join(RAIZ, "..", "config", f"{args.cenario}.sumocfg")
    sementes = [args.semente_unica] if args.semente_unica is not None else list(range(args.sementes))
    sufixo = f"_semente{args.semente_unica}" if args.semente_unica is not None else ""
    caminho_saida = os.path.join(RAIZ, "..", "outputs", f"treino_{args.cenario}{sufixo}.csv")

    recompensas_finais_por_semente = []

    with open(caminho_saida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["semente", "episodio", "recompensa"])

        for semente in sementes:
            recompensas = treinar_uma_semente(caminho_sumocfg, semente, args.episodios)
            for episodio, recompensa in enumerate(recompensas, start=1):
                escritor.writerow([semente, episodio, recompensa])
            recompensas_finais_por_semente.append(recompensas[-1])

    media = statistics.mean(recompensas_finais_por_semente)
    desvio = statistics.stdev(recompensas_finais_por_semente) if len(recompensas_finais_por_semente) > 1 else 0.0
    print(f"\nRecompensa final, media entre sementes: {media:.1f} (desvio-padrao {desvio:.1f})")
    print(f"Resultados detalhados em {caminho_saida}")


if __name__ == "__main__":
    main()
