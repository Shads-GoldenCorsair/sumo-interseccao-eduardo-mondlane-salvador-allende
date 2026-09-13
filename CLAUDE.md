# CLAUDE.md — Contexto do Projecto

Este ficheiro dá-te (Claude Code) todo o contexto necessário para ajudares no
desenvolvimento do protótipo técnico de um Projecto Final de Curso (PFC).
Lê-o por completo antes de qualquer alteração ao código.

---

## 1. Quem sou e o que é este projecto

**Autor:** Shadit Assagar Juma, n.º de estudante 6601
**Curso:** Licenciatura em Engenharia Informática e Telecomunicações (LEIT51)
**Instituição:** Instituto Superior de Transportes e Comunicações (ISUTC), Maputo, Moçambique
**Orientador:** Eng.º Inocêncio Francisco Zunguze

**Tema do PFC:** Sistema Multiagente de Controlo Semafórico para Optimização
do Tráfego Urbano.

**Caso de estudo:** Intersecção da Avenida Eduardo Mondlane com a Avenida
Salvador Allende, bairro Polana Cimento, distrito de KaMpfumo, Maputo.
Junto ao Ministério da Saúde, à Faculdade de Medicina da UEM e ao ICMA —
perfil de utilização heterogéneo (hospital, ensino superior, jardim infantil),
não apenas tráfego comercial ou residencial.

**Plano de expansão (só depois do modelo estar validado):** se o modelo
principal funcionar bem, expandir para a intersecção da Avenida Eduardo
Mondlane com a Avenida Karl Marx, para demonstrar escalabilidade multiagente.
Não avançar para isto sem indicação explícita.

---

## 2. O problema técnico, em termos simples

A intersecção opera actualmente com um semáforo de **tempo fixo** (ciclo de
42s + 42s + 2×3s de amarelo, sem qualquer adaptação ao tráfego real). O
objectivo é treinar um agente de **Deep Reinforcement Learning (DRL)** que
decida, em tempo real, quando manter ou mudar a fase do semáforo, reduzindo
o tempo médio de espera e o comprimento das filas, face a esse baseline de
tempo fixo.

**Isto NÃO é aprendizagem supervisionada nem não supervisionada.** É
aprendizagem por reforço: o agente aprende por tentativa e erro, através de
recompensas recebidas ao interagir com o ambiente de simulação. Não há
dataset de "respostas certas" para treinar isto como um problema de
classificação ou regressão.

---

## 3. Arquitectura técnica já decidida (não mudar sem justificação forte)

| Componente | Decisão |
|---|---|
| Simulador | SUMO (Simulation of Urban Mobility), via interface TraCI |
| Algoritmo | Deep Q-Network (DQN) — Mnih et al. (2015) |
| Alternativa considerada | PPO (mais estável, mas mais complexo de afinar) — não implementar agora, só se o DQN se mostrar instável |
| Linguagem | Python 3 |
| Framework de ML | TensorFlow / Keras |
| Espaço de estados | Vector de 9 valores: 4 filas (uma por aproximação) + 4 tempos de espera acumulados + 1 fase actual do semáforo |
| Espaço de acções | Discreto, 2 valores: 0 = manter fase actual, 1 = mudar de fase |
| Recompensa | Negativo da soma dos tempos de espera em todas as aproximações, menos uma penalização de 5.0 se a acção mudou de fase (evita oscilação excessiva) |
| Estabilização do treino | Experience replay (buffer de 10000 transições) + rede-alvo, actualizada a cada 5 episódios |
| Validação estatística | **Obrigatório treinar com um mínimo de 5 sementes aleatórias distintas**, reportar média e desvio-padrão — não aceitar resultados de uma única execução como conclusivos |

Estas decisões estão todas fundamentadas e escritas no Capítulo II (Revisão
de Literatura) e no Capítulo IV (Metodologia) do PFC. Se precisares de mudar
alguma, avisa-me explicitamente porquê, para eu poder actualizar a tese
também — código e tese têm de ficar consistentes.

---

## 4. Estrutura de ficheiros já construída

```
sumo_project/
├── net/
│   ├── nodes.nod.xml                              # nós da rede (formato nativo SUMO)
│   ├── edges.edg.xml                               # arestas/vias (formato nativo SUMO)
│   └── eduardo_mondlane_salvador_allende.net.xml    # rede compilada, pronta a usar
├── routes/
│   ├── vtypes.rou.xml                              # tipos de veículo (ligeiro, chapa, autocarro, pesado)
│   ├── routes.rou.xml                              # as 12 rotas possíveis na intersecção
│   ├── demanda_pico.rou.xml                        # tráfego simulado, hora de pico
│   └── demanda_baixo_fluxo.rou.xml                 # tráfego simulado, baixo fluxo
├── config/
│   ├── pico.sumocfg
│   └── baixo_fluxo.sumocfg
├── agente_dqn/
│   ├── sumo_env.py         # wrapper do ambiente (estado, acção, recompensa)
│   ├── dqn_agent.py        # o agente DQN (rede, experience replay, rede-alvo)
│   ├── train.py             # script de treino com múltiplas sementes
│   ├── requirements.txt
│   └── README.md
├── outputs/
│   ├── tripinfo_pico.xml / tripinfo_baixo_fluxo.xml       # baseline de tempo fixo, já gerado
│   ├── resumo_*.xml
│   └── filas_*.xml
└── LEIA-ME.md
```

**Estado confirmado por teste real (ambiente diferente, sem SUMO_HOME
configurado localmente ainda):** o pipeline completo (SUMO → TraCI →
observação de estado → decisão do agente → treino da rede) foi executado
com sucesso, com a recompensa a melhorar de -2501 para -1107 em apenas 3
episódios curtos. Isto confirma que o código funciona; não confirma ainda
desempenho final treinado.

---

## 5. ⚠️ Limitação crítica a resolver primeiro: a rede não está georreferenciada

A rede em `net/` foi **construída manualmente** (nós e arestas em coordenadas
locais, não latitude/longitude reais), porque o ambiente onde foi criada não
tinha acesso à internet para o OpenStreetMap. A topologia está correcta
(4 aproximações ortogonais, 2 faixas/sentido em Eduardo Mondlane, 1 faixa/
sentido em Salvador Allende), mas as coordenadas geográficas exactas não são
reais.

**Primeira tarefa a fazer aqui, com o teu acesso à internet:**

```bash
python3 $SUMO_HOME/tools/osmWebWizard.py
```

Isto abre uma janela do browser com um mapa. Navegar até à intersecção da
Av. Eduardo Mondlane com a Av. Salvador Allende, em Maputo, seleccionar a
área, e descarregar a rede real. Substituir os ficheiros em `net/` por esta
versão real, mantendo os nomes de aresta o mais próximo possível dos actuais
(`EM_W_in`, `EM_E_in`, `SA_N_in`, `SA_S_in`, etc.) para não partir os scripts
Python já escritos — ou, se os nomes mudarem, actualizar `sumo_env.py`
(dicionário `ARESTAS_ENTRADA`) em conformidade.

---

## 6. Sobre os dados de tráfego (procura/demanda)

Os volumes em `demanda_pico.rou.xml` e `demanda_baixo_fluxo.rou.xml` são
**estimativas de engenharia**, não dados de campo reais. Isto está
documentado como limitação conhecida no Capítulo III do PFC (secção 3.1.5).

Estão em curso pedidos formais de dados reais a cinco entidades:
Conselho Municipal de Maputo (CMM), Agência Metropolitana de Transporte de
Maputo (AMT), Ministério dos Transportes e Comunicações (MTC), Projecto de
Transformação Urbana de Maputo (PTUM), e ALMO Intellect (empresa privada de
monitorização de tráfego). Se e quando chegarem dados reais (idealmente
volumes de veículos/hora por aproximação), a tarefa é recalibrar os `<flow>`
destes ficheiros — a estrutura das rotas e tipos de veículo mantém-se.

**Não escrevas no Capítulo III/IV do PFC que os dados são reais até teres
confirmação explícita de que chegaram e foram integrados.**

---

## 7. Regras de trabalho, código

- Comentários e mensagens de commit em português de Moçambique (pré-Acordo
  Ortográfico de 1990) — mesma convenção usada em toda a tese. Nomes de
  variáveis e funções também em português, para consistência com o resto
  do projecto (já reparaste nos ficheiros existentes: `obter_estado`,
  `calcular_recompensa`, etc.) — manter este padrão em código novo.
- Não uses travessão (—) em comentários ou docstrings; usa vírgula ou
  reformula a frase.
- Qualquer alteração à formulação de estado, acção ou recompensa tem de ser
  sinalizada explicitamente, porque exige actualização correspondente no
  Capítulo II (secção 2.4.2) e no Capítulo IV do PFC.
- Prefere simplicidade a sofisticação prematura. O objectivo é ter um
  protótipo funcional e bem documentado para um PFC de licenciatura, não um
  sistema de produção. Não introduzas complexidade (por exemplo, frameworks
  de RL de terceiros, arquitecturas multiagente completas com QMIX/MADDPG)
  sem que eu peça explicitamente — isso já está identificado como possível
  trabalho futuro no Capítulo II, secção 2.4.4, não para agora.

## 8. Regras de trabalho, texto académico

Se em algum momento precisares de escrever ou sugerir texto para os
capítulos do PFC (não só código), estas regras são obrigatórias, vindas da
skill `scientific-writer-isutc` usada em todo o resto do trabalho:

- Português de Moçambique, nunca português do Brasil (nada de "você",
  "adoção", etc.)
- Toda a citação de fonte científica segue: introdução da citação
  ("Segundo...", "De acordo com...") → ideia do autor → **comentário
  crítico obrigatório** (análise, limitação, comparação)
- Nunca citar PFCs anteriores do ISUTC na bibliografia — servem apenas de
  inspiração estrutural, nunca de fonte citável
- Sem travessões como pontuação
- Times New Roman 12pt, espaçamento 1,5, formatação ISUTC
- Nunca alterar texto da tese sem aprovação explícita do autor primeiro

## 9. O que fazer, e não fazer, sem perguntar primeiro

**Podes avançar sem perguntar:**
- Correr o `osmWebWizard.py` e integrar a rede real
- Depurar erros de execução no código já existente
- Sugerir optimizações ao código que não mudem a arquitectura (estado,
  acção, recompensa, algoritmo)
- Ajudar a interpretar resultados de treino já obtidos

**Pergunta sempre antes de:**
- Mudar a formulação de estado, acção ou recompensa
- Mudar de DQN para outro algoritmo
- Escrever ou alterar qualquer texto do PFC directamente
- Expandir para a intersecção Eduardo Mondlane / Karl Marx (só depois do
  modelo principal estar validado, com indicação explícita minha)
- Assumir que dados reais chegaram sem eu confirmar

---

## 10. Estado actual do trabalho (actualizar isto à medida que avança)

Histórico detalhado, sessão a sessão, em `PROGRESSO.md` — este bloco é só o
resumo do estado actual.

- [x] Rede SUMO construída (geometria correcta, coordenadas locais) — versão
      manual, arquivada em `net/manual_backup/`
- [x] Rede georreferenciada com dados reais do OpenStreetMap. **Descoberta
      importante:** a interseccão real tem apenas 3 aproximações, não 4
      (Eduardo Mondlane, neste troço, é um par de vias de sentido único, não
      uma via bidireccional). Decisão tomada com o autor: adaptar o espaço
      de estados de 9 para 7 valores (3 filas + 3 esperas + 1 fase). Ver
      `PROGRESSO.md`, secção "Fase 0", para o detalhe completo.
- [x] Cenários de procura (pico e baixo fluxo) com estimativas de engenharia,
      reescritos para os IDs de aresta reais
- [x] Baseline de tempo fixo simulado e registado (40,5s espera média em
      pico, 9,6s em baixo fluxo) — **nota:** este número foi medido com a
      rede manual antiga, antes da georreferenciação; precisa de ser
      remedido com a rede real antes da comparação final do Capítulo V
- [x] Agente DQN implementado (`agente_dqn/`: `sumo_env.py`, `dqn_agent.py`,
      `train.py`), com auto-testes, testado nesta máquina (Python 3.11 num
      venv próprio, TensorFlow 2.21)
- [x] Optimização de velocidade de treino (intervalo de decisão de 5s,
      inferência sem overhead de `.predict()`) — ver `PROGRESSO.md`
- [ ] Dados de procura reais (pendente resposta das entidades contactadas)
- [ ] Remedir o baseline de tempo fixo com a rede real georreferenciada
- [ ] Treino completo (5 sementes × N episódios) para o cenário de pico
- [ ] Treino completo para o cenário de baixo fluxo
- [ ] Análise comparativa DQN vs. baseline, para o Capítulo V
- [ ] Actualizar Capítulo II (secção 2.4.2) e Capítulo IV com a mudança de
      4 para 3 aproximações e do vector de estado de 9 para 7 (pendente
      indicação do autor para tocar no texto da tese)
- [ ] Redacção dos Capítulos V e VI, a partir de resultados reais
