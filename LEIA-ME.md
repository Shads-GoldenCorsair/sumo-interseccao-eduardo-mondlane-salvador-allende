# Ficheiros SUMO — Intersecção Av. Eduardo Mondlane x Av. Salvador Allende

Projecto Final de Curso — Shadit Assagar Juma
Sistema Multiagente de Controlo Semafórico para Optimização do Tráfego Urbano

---

## ⚠️ Nota metodológica importante — leia antes de usar

Este ambiente de trabalho **não tem acesso de rede ao OpenStreetMap nem ao Overpass API**
(ambos bloqueados no ambiente sandbox em que este pacote foi gerado). Por essa razão,
**não foi possível descarregar os dados geoespaciais reais e ao vivo da intersecção**.

Em vez disso, construí manualmente uma rede SUMO **geometricamente fiel** à intersecção
real, com base em:

- Confirmação visual directa da geometria via captura de ecrã do OpenStreetMap
  (já usada no Capítulo III do PFC, Figura 3.1)
- Descrição da Avenida Eduardo Mondlane na Wikipédia (PT/DE): via de 4 a 6 faixas
- A tua fotografia real da intersecção (Figura 3.2 do Cap. III), que confirma o
  número de faixas e o volume de tráfego característico

**O que isto significa na prática:**
- A **topologia** (4 aproximações, ortogonal, sem rotunda) está correcta
- O **número de faixas** por avenida está correcto (2 por sentido em Eduardo Mondlane, 1 em Salvador Allende)
- As **coordenadas geográficas exactas** (latitude/longitude) NÃO estão georreferenciadas
  ao mundo real — a rede foi construída em coordenadas locais (metros), com a
  intersecção na origem (0,0)
- Os **volumes de tráfego** (vehsPerHour) são **estimativas de engenharia**, não dados
  de campo reais — isto já está documentado como limitação conhecida na secção 3.1.5
  do teu Capítulo III

## Como obter a versão georreferenciada real (recomendado antes da defesa)

Quando tiveres acesso a um computador com ligação à internet, corre o assistente
oficial do SUMO, que descarrega os dados reais do OpenStreetMap para esta intersecção
exacta:

```bash
python3 $SUMO_HOME/tools/osmWebWizard.py
```

Isto abre uma janela do browser com um mapa interactivo. Navega até Maputo,
selecciona a área à volta da intersecção Eduardo Mondlane / Salvador Allende, e o
assistente descarrega automaticamente a rede real, incluindo geometria exacta,
edifícios, e pode até gerar tráfego aleatório automaticamente.

Alternativa por linha de comandos, se já souberes a caixa delimitadora (bounding box)
da zona:

```bash
python3 $SUMO_HOME/tools/osmGet.py --bbox <oeste,sul,este,norte> --output-dir dados_osm/
python3 $SUMO_HOME/tools/osmBuild.py --osm-file dados_osm/*.osm.xml --output-prefix rede_real
```

---

## Estrutura do pacote

```
sumo_project/
├── net/
│   ├── nodes.nod.xml                              (nós da rede, formato nativo SUMO)
│   ├── edges.edg.xml                              (arestas/vias, formato nativo SUMO)
│   └── eduardo_mondlane_salvador_allende.net.xml   (rede compilada, pronta a usar)
├── routes/
│   ├── vtypes.rou.xml                              (tipos de veículos)
│   ├── routes.rou.xml                              (as 12 rotas possíveis na intersecção)
│   ├── demanda_pico.rou.xml                        (tráfego simulado, hora de pico)
│   └── demanda_baixo_fluxo.rou.xml                 (tráfego simulado, baixo fluxo)
├── config/
│   ├── pico.sumocfg                                (configuração pronta a correr)
│   └── baixo_fluxo.sumocfg
├── outputs/
│   ├── tripinfo_pico.xml / tripinfo_baixo_fluxo.xml  (dados por viagem: espera, duração)
│   ├── resumo_pico.xml / resumo_baixo_fluxo.xml      (estatísticas agregadas por passo)
│   └── filas_pico.xml / filas_baixo_fluxo.xml        (comprimento de filas por passo)
└── LEIA-ME.md (este ficheiro)
```

## Como correr as simulações

```bash
cd config
sumo -c pico.sumocfg
sumo -c baixo_fluxo.sumocfg
```

Para veres a simulação graficamente (precisa de `sumo-gui` instalado):

```bash
sumo-gui -c pico.sumocfg
```

## Resultados já obtidos (baseline de tempo fixo, para comparação futura com o agente DRL)

| Métrica | Hora de pico | Baixo fluxo |
|---|---|---|
| Veículos simulados (1 hora) | 2069 | 225 |
| Tempo médio de espera | 40,5 s | 9,6 s |
| Tempo máximo de espera | 729,0 s | 45,0 s |
| Duração média da viagem | 110,9 s | 70,2 s |

Estes números resultam do plano de temporização fixa gerado automaticamente pelo
`netconvert` (2 fases principais + transições amarelas), representativo do sistema
actualmente em uso na intersecção real, conforme descrito no Cap. III, secção 3.1.4.
**Este é precisamente o baseline que o teu sistema multiagente DRL, descrito no
Capítulo IV, terá de superar** — os números aqui obtidos são o ponto de partida
para a comparação que farás no Capítulo V.

## Ligação directa à interface TraCI (para o desenvolvimento do agente DRL)

Estes ficheiros já estão prontos para seres usados com a interface TraCI, descrita
na secção 2.5.2 do teu Capítulo II e na metodologia de desenvolvimento do Capítulo IV.
Exemplo mínimo de ligação em Python:

```python
import traci

traci.start(["sumo", "-c", "config/pico.sumocfg"])
for step in range(3600):
    traci.simulationStep()
    fila_norte = traci.edge.getLastStepHaltingNumber("SA_N_in")
    # aqui entra a lógica do agente DQN/PPO
traci.close()
```

## Próximos passos técnicos sugeridos

1. Confirmar os volumes reais de tráfego junto do CMM/AMT/PTUM (ver a lista de
   entidades já discutida) e recalibrar `demanda_pico.rou.xml` e
   `demanda_baixo_fluxo.rou.xml` com valores reais
2. Regenerar a rede com `osmWebWizard.py` num ambiente com internet, para obter
   georreferenciação exacta
3. Implementar o agente DQN/PPO sobre esta rede via TraCI, conforme a secção 4.7 do
   Capítulo IV
