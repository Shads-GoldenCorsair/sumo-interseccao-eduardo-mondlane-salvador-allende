"""
Desenha a evolucao da recompensa ao longo dos episodios de treino, uma
linha por semente, mais a media entre sementes a negrito. E a forma mais
directa de ver se o agente esta mesmo a aprender (ver LEIA-ME_RESULTADOS.md).

Uso:
    python graficar_resultados.py --cenario pico
    python graficar_resultados.py --cenario baixo_fluxo
"""

import argparse
import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt

RAIZ = os.path.dirname(__file__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    args = parser.parse_args()

    caminho_csv = os.path.join(RAIZ, "..", "outputs", f"treino_{args.cenario}.csv")
    if not os.path.exists(caminho_csv):
        print(f"Nao encontrado: {caminho_csv}. Corre train.py ou junta_resultados.py primeiro.")
        return

    por_semente = defaultdict(list)
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            por_semente[linha["semente"]].append(float(linha["recompensa"]))

    fig, ax = plt.subplots(figsize=(10, 6))
    for semente, recompensas in sorted(por_semente.items()):
        ax.plot(range(1, len(recompensas) + 1), recompensas, alpha=0.35, label=f"semente {semente}")

    # Media entre sementes, episodio a episodio (so ate ao min comum, caso
    # alguma semente tenha menos episodios do que as outras).
    num_episodios = min(len(r) for r in por_semente.values())
    media = [
        sum(por_semente[s][i] for s in por_semente) / len(por_semente)
        for i in range(num_episodios)
    ]
    ax.plot(range(1, num_episodios + 1), media, color="black", linewidth=2.5, label="media entre sementes")

    ax.set_xlabel("Episodio")
    ax.set_ylabel("Recompensa")
    ax.set_title(f"Evolucao da recompensa durante o treino, cenario {args.cenario}")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)

    caminho_saida = os.path.join(RAIZ, "..", "outputs", f"grafico_treino_{args.cenario}.png")
    fig.savefig(caminho_saida, dpi=150, bbox_inches="tight")
    print(f"Grafico gravado em {caminho_saida}")


if __name__ == "__main__":
    main()
