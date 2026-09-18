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

Guarda um checkpoint (pesos da rede + progresso) a cada CHECKPOINT_CADA
episodios em outputs/_checkpoints/. Se a execucao for interrompida (ex.:
o Colab desliga a sessao), correr o mesmo comando outra vez retoma a
partir do ultimo checkpoint em vez de recomecar do zero.

Quando uma semente termina o treino todo, o modelo final fica gravado em
outputs/modelos_treinados/<cenario>_semente<N>.weights.h5 (nao e apagado
como o checkpoint de progresso). Usar avaliar_agente.py para carregar esse
modelo e medir o desempenho real, sem exploracao aleatoria.
"""

import argparse
import csv
import json
import os
import statistics

from dqn_agent import AgenteDQN, ACTUALIZAR_REDE_ALVO_CADA
from sumo_env import AmbienteSumo

RAIZ = os.path.dirname(__file__)
PASTA_CHECKPOINTS = os.path.join(RAIZ, "..", "outputs", "_checkpoints")
PASTA_MODELOS = os.path.join(RAIZ, "..", "outputs", "modelos_treinados")
# CHECKPOINT_CADA = 10  # episodios
CHECKPOINT_CADA = 5  # episodios (salva pesos e progresso no Drive a cada 5 episodios)


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


def caminhos_checkpoint(cenario, semente):
    prefixo = os.path.join(PASTA_CHECKPOINTS, f"{cenario}_semente{semente}")
    return prefixo + ".weights.h5", prefixo + ".json"


def treinar_uma_semente(caminho_sumocfg, cenario, semente, num_episodios, caminho_csv):
    os.makedirs(PASTA_CHECKPOINTS, exist_ok=True)
    caminho_pesos, caminho_progresso = caminhos_checkpoint(cenario, semente)

    agente = AgenteDQN(semente=semente)
    episodio_inicial = 0

    if os.path.exists(caminho_progresso):
        with open(caminho_progresso, encoding="utf-8") as f:
            progresso = json.load(f)
        agente.carregar_pesos(caminho_pesos)
        agente.epsilon = progresso["epsilon"]
        episodio_inicial = progresso["episodio"]
        print(f"semente={semente}: retomado do checkpoint, episodio {episodio_inicial}")

    # O CSV e sempre aberto em append: escreve o cabecalho so se o ficheiro
    # ainda nao existir (primeira semente de uma execucao nova). Assim,
    # correr varias sementes seguidas no mesmo processo, ou retomar depois
    # de uma interrupcao, nunca apaga o que outras sementes ja gravaram.
    ficheiro_novo = not os.path.exists(caminho_csv) or os.path.getsize(caminho_csv) == 0
    ambiente = AmbienteSumo(caminho_sumocfg)
    ultima_recompensa = None

    with open(caminho_csv, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if ficheiro_novo:
            escritor.writerow(["semente", "episodio", "recompensa"])

        for episodio in range(episodio_inicial, num_episodios):
            recompensa = correr_episodio(ambiente, agente)
            ultima_recompensa = recompensa
            escritor.writerow([semente, episodio + 1, recompensa])
            f.flush()
            os.fsync(f.fileno())

            if (episodio + 1) % ACTUALIZAR_REDE_ALVO_CADA == 0:
                agente.actualizar_rede_alvo()

            print(f"semente={semente} episodio={episodio + 1}/{num_episodios} recompensa={recompensa:.1f} epsilon={agente.epsilon:.3f}")

            if (episodio + 1) % CHECKPOINT_CADA == 0:
                agente.guardar_pesos(caminho_pesos)
                with open(caminho_progresso, "w", encoding="utf-8") as fp:
                    json.dump({"episodio": episodio + 1, "epsilon": agente.epsilon}, fp)

    ambiente.fechar()

    # Treino desta semente completo: guarda o modelo final num sitio
    # permanente (para avaliar depois, ver avaliar_agente.py), e remove o
    # checkpoint de progresso (ja nao e preciso retomar).
    os.makedirs(PASTA_MODELOS, exist_ok=True)
    agente.guardar_pesos(os.path.join(PASTA_MODELOS, f"{cenario}_semente{semente}.weights.h5"))
    for caminho in (caminho_pesos, caminho_progresso):
        if os.path.exists(caminho):
            os.remove(caminho)

    return ultima_recompensa


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
    for semente in sementes:
        recompensa_final = treinar_uma_semente(caminho_sumocfg, args.cenario, semente, args.episodios, caminho_saida)
        recompensas_finais_por_semente.append(recompensa_final)

    media = statistics.mean(recompensas_finais_por_semente)
    desvio = statistics.stdev(recompensas_finais_por_semente) if len(recompensas_finais_por_semente) > 1 else 0.0
    print(f"\nRecompensa final, media entre sementes: {media:.1f} (desvio-padrao {desvio:.1f})")
    print(f"Resultados detalhados em {caminho_saida}")


if __name__ == "__main__":
    main()
