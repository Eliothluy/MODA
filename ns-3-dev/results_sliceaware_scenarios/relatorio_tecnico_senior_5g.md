# Relatório Técnico — Análise de Slicing 5G no RSLAQ (ns-3 + 5G-LENA)

**Autor:** Engenheiro de Software Sênior — Redes 5G & Simulação  
**Data:** 2026-05-07  
**Repositório:** `/home/elioth/Documentos/artigo_jussi`  
**Artefatos analisados:**
- `ns-3-dev/scratch/rslaq/rslaq-mac-scheduler.{h,cc}`
- `ns-3-dev/scratch/rslaq/rslaq-sim.cc`
- `ns-3-dev/results_sliceaware_scenarios/{greenran_*}/`
- `ns-o-ran-gym/src/environments/rslaq_env.py`
- `ns-o-ran-gym/src/environments/rslaq_action_spaces.py`
- `results_sliceaware_scenarios/gerar_relatorio.py` (pipeline de análise)

---

## 1. Resumo Executivo

Foram analisados **7 cenários** de simulação slice-aware (`greenran_normal`, `greenran_low`, `greenran_balanced`, `greenran_night_energy`, `greenran_congestion`, `greenran_mmtc_massive`, `greenran_video_heavy`).

A análise revela **violações massivas de SLA em todos os cenários**, mas a raiz do problema não é apenas a capacidade da rede: há **bugs de instrumentação, configuração física inconsistente e limitações arquiteturais** que distanciam o modelo da realidade do 5G. O slicing implementado hoje é **apenas RAN-side, no downlink MAC**, longe do conceito 3GPP de Network Slicing end-to-end.

**Achados críticos:**
1. **Inversão UL/DL no relatório:** throughput de DL está registrado como UL e vice-versa, mascarando a real performance.
2. **Configuração de RF irrealista:** 10 MHz @ SCS 15 kHz (μ=0) com antenas isotrópicas 1×1 não representa 5G NR. O relatório, contudo, indica **266 RBGs totais** — fisicamente impossível para 10 MHz, indicando bug na configuração do BWP ou no cálculo de RBGs do 5G-LENA.
3. **SLAs fisicamente inalcançáveis:** 118,75 Mbps de throughput garantido por slice em uma célula SISO de 10 MHz é teoricamente inviável.
4. **Slicing sem 5GC:** ausência total de 5G Core (AMF, SMF, UPF, NSSF), QoS Flows (5QI) e isolamento de transporte.
5. **Tráfego simplificado:** modelos `OnOff` com taxa constante não representam VBR de vídeo (eMBB) nem padrões esporádicos de sensores (mMTC).
6. **Scheduler MAC com alocação binária por RBG:** a lógica atual aloca 1 RBG por iteração por UE, ignorando eficiência espectral e agregação de portadora.
7. **HARQ não instrumentado:** `LogHarqState()` é um stub vazio; sem BLER, sem retransmissões visíveis, sem realismo de PHY.

---

## 2. Análise Técnica por Camada

### 2.1. PHY / Camada Física

#### 2.1.1. Largura de Banda e Numerologia
- **Código:** `rslaq-sim.cc:702-704` define `bandwidth = 10e6`, `numerology = 0` (SCS 15 kHz).
- **Problema:** 10 MHz com μ=0 fornece **52 PRBs** no máximo (273 PRBs são para 100 MHz @ μ=1). Um cenário eMBB realista exige **100 MHz @ μ=1 (30 kHz)** ou **400 MHz @ μ=3 (120 kHz)** no FR2.
- **Inconsistência grave:** o CSV `slice_alloc.csv` reporta `totalRbg = 266` nos cenários. Isso é matematicamente inconsistente com 10 MHz. A causa provável é:
  - O `CcBwpCreator::SimpleOperationBandConf` foi configurado com `bandConf.m_numBwp = 1`, mas o BWP resultante pode ter herdado uma configuração de largura de banda diferente do CC, ou
  - O helper `NrHelper` não aplicou corretamente a largura de banda ao BWP, deixando o default interno do 5G-LENA (possivelmente 400 MHz).

#### 2.1.2. Antenas e Beamforming
- **Código:** `rslaq-sim.cc:797-804` usa `IsotropicAntennaModel` com 1 linha × 1 coluna.
- **Impacto:** sem beamforming, sem ganho de array, sem MIMO. A 5G NR depende de MIMO massivo (64T64R, 32T32R) para atingir altos throughputs. A capacidade por PRB está drasticamente subestimada.
- **Recomendação:** migrar para `UniformPlanarArray` com pelo menos 8×8 elementos e usar `ThreeGppSpectrumPropagationModel` para beamforming realista.

#### 2.1.3. Potência e Canal
- **Potência de 43 dBm** é adequada para macro, mas sem beamforming a densidade de potência por elemento é irrelevante.
- **Shadowing desabilitado:** `SetPathlossAttribute("ShadowingEnabled", BooleanValue(false))` remove variabilidade do canal, tornando o cenário deterministicamente otimista.

### 2.2. MAC / Camada de Acesso ao Meio

#### 2.2.1. Scheduler Slice-Aware (`RslaqMacScheduler`)
- **Herança:** deriva de `NrMacSchedulerOfdmaRR`. Isso é aceitável como ponto de partida.
- **Particionamento de RBGs:** a lógica em `AssignDLRBG()` (linha 437) particiona RBGs entre slices por pesos configuráveis (`m_prbWeights`). A renormalização por demanda ativa está correta conceitualmente.
- **Alocação intra-slice:** a implementação (linha 628-740) aloca **1 RBG por vez por UE**, iterando até esgotar o `sliceRbgBudget`. Isso é ineficiente:
  - Em OFDMA, deveria alocar o maior conjunto contíguo ou distribuído de RBGs que satisfaça a demanda do buffer do UE em uma única decisão.
  - A alocação símbolo-a-símbolo com `beamSym` fixo não explora a flexibilidade do TDD.
- **Limitação 5G-LENA:** o módulo NR do ns-3 não implementa SDAP (Service Data Adaptation Protocol), portanto não há mapeamento de QoS flow para DRB. O slicing é puramente uma divisão de RBGs por RNTI.

#### 2.2.2. HARQ e BLER
- **Código:** `LogHarqState()` (linha 432) é um stub vazio.
- **Impacto:** sem retransmissões visíveis, a métrica de PLR do relatório é apenas descarte de fila (drop tail), não refletindo o comportamento real de PHY onde HARQ corrige erros. Isso torna o cenário pessimista demais para canais ruidosos.

### 2.3. RAN / Arquitetura de Rádio

#### 2.3.1. Topologia
- **1 gNB, até 210 UEs** (cenário `greenran_congestion`).
- **Sem handover, sem mobilidade:** `ConstantPositionMobilityModel` fixa UEs em posições aleatórias. Isso ignora:
  - Efeitos Doppler
  - Troca de feixe (beam switching)
  - Handover entre células (crucial para isolamento de slice em cenários multi-gNB)

#### 2.3.2. TDD
- O parâmetro `tddPattern = "D|D|D|D|D|D|D|D|D|D"` é aceito na linha de comando, mas o comentário no código alerta: `"NOTE: currently NOT applied in this NR version"`.
- **Impacto:** a configuração TDD não está sendo aplicada pelo 5G-LENA. O scheduler opera em um modo full-downlink implícito, o que explica o DL próximo de zero no relatório: o tráfego pode estar sendo enviado em slots que o PHY trata como UL, ou o `FlowMonitor` está capturando estatísticas em direções invertidas.

### 2.4. Core Network & Transporte

#### 2.4.1. EPC vs 5GC
- **Código:** usa `NrPointToPointEpcHelper` (LTE EPC adaptada).
- **Problema:** não há 5G Core. Não há:
  - **NSSF** (Network Slice Selection Function)
  - **AMF/SMF/UPF** com suporte a S-NSSAI
  - **PDU Sessions** por slice
  - **QoS Flows** com 5QI diferenciado
- O slicing é, portanto, apenas uma **partição de recursos de rádio**, não um slice de ponta a ponto conforme 3GPP TS 23.501.

#### 2.4.2. Backhaul
- **Configuração:** P2P de 100 Gbps, 1 ms de delay, MTU 2500.
- **Problema:** backhaul infinito e sem congestionamento. Na realidade, o backhaul é um gargalo crítico para slicing (especialmente F1/u entre DU e CU). Não há modelagem de redes de transporte com MPLS, Segment Routing, ou TSN para garantia de isolamento.

### 2.5. Tráfego e Aplicação

#### 2.5.1. Modelos de Fonte
- **eMBB (Vídeo):** `OnOffHelper` com taxa constante (`SetConstantRate`). Vídeo real é **VBR** com picos de I-frame. Deveria usar `ns3::UdpTraceBased` ou modelar GOPs com taxas variáveis.
- **mMTC (Sensores):** `OnOffHelper` contínuo. Sensores reais transmitem **pacotes pequenos esporadicamente** (modelo de evento ou Poisson). O fluxo contínuo gera buffer permanente e mascarar a eficiência do scheduler para tráfego burst.
- **URLLC:** ausente nos cenários `greenran_*`. O código C++ define slice URLLC, mas os cenários de resultado não o utilizam. URLLC requer pacotes pequenos (32–100 bytes), período estrito (1–10 ms) e latência < 1 ms na RAN.

#### 2.5.2. Portas e Fluxos
- Cada UE recebe um fluxo UDP único por porta (`baseDlPort + ueId`). Isso é aceitável, mas sem diferenciação de QoS no core, todos os fluxos são tratados igualmente além do scheduler MAC.

---

## 3. Bugs e Inconsistências Identificadas

### 3.1. Inversão de Direção UL/DL no Relatório
- **Sintoma:** no relatório gerado, `VIDEO_EMBB` mostra **UL = 105,72 Mbps** e **DL = 0,06 Mbps**.
- **Causa raiz:** o `FlowMonitor` em ns-3 reporta estatísticas por fluxo. O tráfego `OnOff` origina no `remoteHost` e termina no UE. Portanto, o fluxo de dados é **DL**. No entanto, o `gerar_relatorio.py` (e possivelmente o `rslaq-sim.cc`) parece estar interpretando `txBytes` do UE como UL. Como o UE é apenas receptor (UDP server), `txBytes` do UE é quase zero, resultando no "DL" zerado.
- **Correção:** no `rslaq-sim.cc`, separar explicitamente as métricas por direção usando a 5-tupla do `Ipv4FlowClassifier` e o endereço IP de origem/destino. O `FlowMonitor` já distingue fluxos; o código deve classificar como DL quando a origem é o `remoteHost` e como UL quando a origem é o UE.

### 3.2. Valor de `totalRbg` Inconsistente
- **Sintoma:** `totalRbg = 266` em 10 MHz.
- **Cálculo esperado:** para 10 MHz @ SCS 15 kHz, são 52 PRBs. Se RBG = 2 PRBs (configuração típica), teríamos ~26 RBGs. 266 RBGs implicam ~532 PRBs, compatível com **~400 MHz** de banda.
- **Ação:** verificar se `bandwidth` foi realmente propagado ao `NrPhy`. Imprimir `GetBandwidthInRbg()` e `GetNumRbPerRbg()` no início da simulação para depuração.

### 3.3. SLAs Mal Dimensionados
- **Sintoma:** SLA de throughput para eMBB = 118,75 Mbps.
- **Análise:** com 10 MHz SISO, a capacidade de pico por célula é aproximadamente:
  - 52 PRBs × 12 subportadoras × 14 símbolos/slot × 6 bits/símbolo (64-QAM) × 1000 slots/s ≈ **52,4 Mbps** por camada.
  - Com 1×1 SISO, o máximo teórico é ~50 Mbps por célula. Distribuir 118,75 Mbps por slice é impossível.
- **Correção:** recalcular SLAs baseados na capacidade do canal:
  - Para 10 MHz SISO: ~5–10 Mbps por UE eMBB, ~0,1 Mbps por UE mMTC.
  - Se o objetivo é artigo científico, **aumentar a banda para 100 MHz** e usar 4×4 MIMO, ou reduzir os SLAs.

### 3.4. Ausência de Dados URLLC
- **Sintoma:** cenários `greenran_*` não possuem slice URLLC nos resultados.
- **Causa:** o `SLICE_MAP` em `gerar_relatorio.py` mapeia slice 2 como `URLLC_V2X`, mas os CSVs de cenário só contêm slices 0 e 1. Isso sugere que os cenários foram executados com `--urllcUes=0` ou que o wrapper de execução em Python (`rslaq_env.py` ou script de treinamento) não configura URLLC.
- **Correção:** garantir que todos os 3 slices estejam ativos nos cenários, ou ajustar o `NUM_SLICES` dinamicamente.

---

## 4. Recomendações para Aproximar da Realidade

### 4.1. Correções Imediatas (Código)

#### A. Corrigir Instrumentação UL/DL (`rslaq-sim.cc`)
```cpp
// Exemplo de correção no StatsCallback e WriteFinalCsv
bool isDl = (tuple.sourceAddress == remoteHostAddr);
bool isUl = (tuple.destinationAddress == remoteHostAddr);
// Acumular tx/rx separadamente para DL e UL por UE/slice
```
Garantir que o `FlowMonitor` capture estatísticas por direção, ou usar dois `FlowMonitor`s (um para cada sentido) se necessário.

#### B. Verificar Configuração de BWP (`rslaq-sim.cc`)
Adicionar asserts no início da simulação:
```cpp
NS_ASSERT_MSG(band.GetBwpAt(0,0)->m_bw <= bandwidth,
              "BWP bandwidth mismatch");
```
E logar:
```cpp
std::cout << "BWP RBs: " << band.GetBwpAt(0,0)->m_numRb << "\n";
std::cout << "Scheduler RBGs: " << GetBandwidthInRbg() << "\n";
```

#### C. Implementar HARQ Logging (`rslaq-mac-scheduler.cc`)
Preencher `LogHarqState()` iterando sobre `m_ueMap` e consultando `m_dlHarqProcesses` (membro protegido da classe base `NrMacSchedulerNs3`). Requer acesso ao buffer HARQ do 5G-LENA.

#### D. Revisar Decomposição P_STA
O `AGENTS.md` afirma: `p_final = P_STA + p_opt * 0.5`. Verificar se `rslaq_action_spaces.py` aplica isso exatamente uma vez. O código C++ em `rslaq-sim.cc:583-600` comenta que a decomposição é feita no Python. Isso está correto, mas deve ser auditado para evitar double-application.

### 4.2. Melhorias de Modelagem (Realismo)

#### A. RF e PHY
1. **Aumentar largura de banda:** mudar para `bandwidth = 100e6` (100 MHz) e `numerology = 1` (30 kHz). Isso fornece 273 PRBs, próximo de cenários 5G NR reais.
2. **MIMO e Beamforming:**
   - Substituir `IsotropicAntennaModel` por `UniformPlanarArray` (ex: 4×4 para UE, 8×8 para gNB).
   - Habilitar `ThreeGppSpectrumPropagationModel` para beamforming híbrido.
3. **Shadowing e fading:** habilitar `ShadowingEnabled = true` e usar `UpdatePeriod` realista (ex: 100 ms).
4. **Mobilidade:** usar `RandomWalk2d` ou `ConstantVelocity` para UEs eMBB, e posição fixa para mMTC.

#### B. Modelos de Tráfego
1. **eMBB (Vídeo):** usar trace de vídeo H.264/HEVC ou modelo VBR com GOP (I,P,B frames). O ns-3 tem `UdpTraceBased` para isso.
2. **mMTC:** modelo de tráfego periódico com jitter (`PeriodicGenerator`) ou Poisson com pacotes de 20–200 bytes.
3. **URLLC:** adicionar gerador CBR de 32 bytes a cada 1 ms com prioridade máxima no scheduler.

#### C. Core Network (Limitação do 5G-LENA)
O 5G-LENA não possui 5GC. Alternativas viáveis:
1. **Modelar QoS Flows manualmente:** criar um mapeamento explícito de 5QI para slice no `rslaq-sim.cc` (ex: 5QI 9 para eMBB, 5QI 70 para URLLC, 5QI 79 para mMTC) e logar como metadado.
2. **Backhaul realista:** reduzir a capacidade do P2P EPC para 1–10 Gbps e aumentar o delay para 5–20 ms, modelando congestionamento no transporte.
3. **Documentar limitação:** no artigo, deixar claro que o slicing é **RAN-only** devido às limitações do 5G-LENA v2.x.

#### D. Scheduler MAC
1. **Alocação eficiente:** ao invés de alocar 1 RBG por vez, calcular a demanda em bytes do UE e converter para número de RBGs necessários com base no MCS atual:
   ```cpp
   uint32_t neededRbg = std::ceil(bufQueueSize / (bitsPerRe * numRePerRbg));
   uint32_t allocRbg = std::min(neededRbg, sliceRbgBudget[s] / sliceUeVec[s].size());
   ```
2. **Preemptive scheduling para URLLC:** implementar lógica de preempção onde URLLC pode "roubar" RBGs de eMBB quando necessário, conforme 3GPP.
3. **SR (Scheduling Request) realista:** o 5G-LENA modela BSR (Buffer Status Report). Certificar-se de que o `ActiveUeMap` reflete BSRs recentes, não apenas buffer de PDCP.

### 4.3. Pipeline de Resultados (`gerar_relatorio.py`)
1. **Corrigir mapeamento de direção:** garantir que `direction` no CSV de slice/SLA seja inferido corretamente (origem vs destino do fluxo).
2. **Adicionar métricas de espectro:** incluir espectral efficiency (bits/s/Hz) e fairness index (Jain) por cenário.
3. **Validar consistência física:** adicionar check automático: se `totalRbg * numRbPerRbg > maxPrbsParaLarguraDeBanda`, emitir alerta de configuração inconsistente.

---

## 5. Conclusão

O projeto RSLAQ possui uma **arquitetura funcional** para pesquisa em slicing com DRL, mas a modelagem atual está **longe da realidade operacional de redes 5G**. Os principais gargalos são:

1. **Bug de configuração RF** (266 RBGs em 10 MHz) que invalida a base física da simulação.
2. **Instrumentação invertida** (UL/DL) que torna o relatório enganoso.
3. **SLAs inalcançáveis** que forçam violações artificiais, dificultando a avaliação do algoritmo DRL.
4. **Ausência de 5GC, MIMO, beamforming e mobilidade**, limitando o escopo a uma prova de conceito de scheduler MAC.

Para publicação em venue de redes (IEEE, ACM, Elsevier), recomendo fortemente:
- **Corrigir os bugs de configuração e instrumentação** (semana 1).
- **Aumentar a banda para 100 MHz e habilitar MIMO 4×4** (semana 2).
- **Adicionar modelos de tráfego VBR para eMBB e periódico para mMTC** (semana 2–3).
- **Documentar explicitamente** que o slicing é RAN-only e discutir as implicações no artigo.

Com essas correções, o simulador passa de um protótipo de scheduler para uma **plataforma de avaliação de slicing 5G com credibilidade quantitativa**.

---

*Relatório gerado sob demanda para análise técnica do repositório RSLAQ.*
