"""
Junta os CSVs de treino de cada semente (gerados separadamente, ex. no
Colab com --semente-unica) num so ficheiro, e reporta media/desvio-padrao
da recompensa final por semente (CLAUDE.md, seccao 3).

Uso:
    python juntar_resultados.py --cenario pico
"""

import argparse
import csv
import glob
import os
import statistics

RAIZ = os.path.dirname(__file__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cenario", choices=["pico", "baixo_fluxo"], required=True)
    args = parser.parse_args()

    pasta_outputs = os.path.join(RAIZ, "..", "outputs")
    padrao = os.path.join(pasta_outputs, f"treino_{args.cenario}_semente*.csv")
    ficheiros = sorted(glob.glob(padrao))
    if not ficheiros:
        print(f"Nenhum ficheiro encontrado com o padrao {padrao}")
        return

    caminho_saida = os.path.join(pasta_outputs, f"treino_{args.cenario}.csv")
    ultima_recompensa_por_semente = {}

    with open(caminho_saida, "w", newline="", encoding="utf-8") as saida:
        escritor = csv.writer(saida)
        escritor.writerow(["semente", "episodio", "recompensa"])
        for ficheiro in ficheiros:
            with open(ficheiro, newline="", encoding="utf-8") as f:
                leitor = csv.DictReader(f)
                for linha in leitor:
                    escritor.writerow([linha["semente"], linha["episodio"], linha["recompensa"]])
                    ultima_recompensa_por_semente[linha["semente"]] = float(linha["recompensa"])

    valores = list(ultima_recompensa_por_semente.values())
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0.0
    print(f"Juntados {len(ficheiros)} ficheiro(s) em {caminho_saida}")
    print(f"Recompensa final, media entre sementes: {media:.1f} (desvio-padrao {desvio:.1f}, n={len(valores)} sementes)")


if __name__ == "__main__":
    main()
