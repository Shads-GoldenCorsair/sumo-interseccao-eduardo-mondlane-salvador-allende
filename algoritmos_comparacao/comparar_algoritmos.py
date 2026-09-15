"""
Compara a evolucao da recompensa dos 4 algoritmos (DQN, Q-learning, PPO,
A2C) num so grafico, media entre sementes de cada um. E o script para
"escolher o melhor" (CLAUDE.md, secao pedida pelo autor: comparar
algoritmos e escolher o que tiver melhor resultado).

Uso:
    python comparar_algoritmos.py --cenario pico
"""

import argparse
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

RAIZ = os.path.dirname(__file__)

# Nome a mostrar -> caminho do CSV, relativo a outputs/. O DQN nao tem
# sufixo de algoritmo (e o original do projecto, agente_dqn/train.py).
FICHEIROS = {
    "DQN": "treino_{cenario}.csv",
    "Q-learning": "treino_{cenario}_qlearning.csv",
    "PPO": "treino_{cenario}_ppo.csv",
    "A2C": "treino_{cenario}_a2c.csv",
}


def ler_media_por_episodio(caminho_csv):
    por_semente = defaultdict(list)
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            por_semente[linha["semente"]].append(float(linha["recompensa"]))
    num_episodios = min(len(r) for r in por_semente.values())
    return [
        sum(por_semente[s][i] for s in por_semente) / len(por_semente)
        for i in range(num_episodios)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    args = parser.parse_args()

    fig, ax = plt.subplots(figsize=(10, 6))
    ultimas_recompensas = {}

    for nome, padrao in FICHEIROS.items():
        caminho = os.path.join(RAIZ, "..", "outputs", padrao.format(cenario=args.cenario))
        if not os.path.exists(caminho):
            print(f"Ainda nao ha resultados para {nome} ({caminho}), a saltar.")
            continue
        media = ler_media_por_episodio(caminho)
        ax.plot(range(1, len(media) + 1), media, linewidth=2, label=nome)
        ultimas_recompensas[nome] = media[-1]

    if not ultimas_recompensas:
        print("Nenhum algoritmo tem resultados ainda. Corre os treinos primeiro.")
        return

    ax.set_xlabel("Episodio")
    ax.set_ylabel("Recompensa media entre sementes")
    ax.set_title(f"Comparacao de algoritmos, cenario {args.cenario}")
    ax.legend()
    ax.grid(alpha=0.3)

    caminho_saida = os.path.join(RAIZ, "..", "outputs", f"comparacao_algoritmos_{args.cenario}.png")
    fig.savefig(caminho_saida, dpi=150, bbox_inches="tight")
    print(f"Grafico gravado em {caminho_saida}")

    melhor = max(ultimas_recompensas, key=ultimas_recompensas.get)
    print("\nRecompensa do ultimo episodio, media entre sementes:")
    for nome, valor in sorted(ultimas_recompensas.items(), key=lambda x: -x[1]):
        marca = "  <- melhor" if nome == melhor else ""
        print(f"  {nome}: {valor:.1f}{marca}")


if __name__ == "__main__":
    main()
