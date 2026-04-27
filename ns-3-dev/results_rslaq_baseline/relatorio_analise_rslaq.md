# Relatorio de Analise dos Resultados — Simulacao RSLAQ (Scheduler Slice-Aware 5G)

**Data**: 27/04/2026  
**Ferramenta**: ns-3.46 / 5G-LENA  
**Autor**: Analise automatizada dos CSVs de resultado

---

## 1. Configuracao Base da Simulacao

| Parametro | Valor |
|---|---|
| Topologia | 1 gNB, 20 UEs (5 eMBB + 5 URLLC + 10 MTC) |
| Frequencia central | 2.59 GHz (banda n38) |
| Bandwidth | 10 MHz (53 RBGs totais, numerologia 0, SCS 15 kHz) |
| Tx Power gNB | 43 dBm |
| TDD Pattern | D\|D\|D\|D\|D\|D\|D\|D\|D\|D (full DL) |
| Pesos estaticos | eMBB=0.3333, URLLC=0.4000, MTC=0.2667 |
| Algoritmo intra-slice | PF (Proportional Fair) para todos os slices |
| Duracao da simulacao | 10 s (active: 9.6 s) |
| Periodo de estatisticas | 10 ms |
| Buffer RLC UM | 10 MB |

### Cenarios de Trafego (DL)

| Cenario | eMBB (5 UEs) | URLLC (5 UEs) | MTC (10 UEs) |
|---|---|---|---|
| low_traffic | 50 Kbps / 1500 B | 1 Mbps / 50 B | 2 Mbps / 100 B |
| normal | 70 Mbps / 1500 B | 1 Mbps / 50 B | 2 Mbps / 100 B |
| congestion | 100 Mbps / 1500 B | 1 Mbps / 50 B | 100 Mbps / 100 B |
| stressed | 100 Mbps / 1500 B | 1 Mbps / 50 B | 100 Mbps / 100 B |
| insufficient_resources | 100 Mbps / 1500 B | 2 Mbps / 50 B | 100 Mbps / 100 B |

---

## 2. Tabela Comparativa por Cenario (Agregado por Slice)

| Cenario | Slice | Thr (Mbps) | Avg Delay (ms) | PDR | TX pkts | RX pkts |
|---|---|---|---|---|---|---|
| **low_traffic** | eMBB | 0.045 | 13.96 | 1.0000 | 35 | 35 |
| | URLLC | 1.559 | 5.01 | 0.9996 | 23995 | 23985 |
| | MTC | 2.558 | 5.02 | 0.9996 | 23990 | 23980 |
| **normal** | eMBB | 16.00 | 3729.15 | 0.2244 | 55995 | 12564 |
| | URLLC | 1.559 | 5.02 | 0.9996 | 23995 | 23985 |
| | MTC | **0.000** | 0.00 | **0.0000** | 23990 | 0 |
| **congestion** | eMBB | 15.99 | 4052.38 | 0.1570 | 79995 | 12559 |
| | URLLC | 1.559 | 5.02 | 0.9996 | 23995 | 23985 |
| | MTC | **0.000** | 0.00 | **0.0000** | 1199990 | 0 |
| **stressed** | eMBB | 16.04 | 4051.67 | 0.1575 | 79995 | 12599 |
| | URLLC | 1.559 | 5.01 | 0.9996 | 23995 | 23985 |
| | MTC | **0.000** | 0.00 | **0.0000** | 1199990 | 0 |
| **insufficient** | eMBB | 11.75 | 4252.69 | 0.1153 | 79995 | 9226 |
| | URLLC | 3.118 | 5.02 | 0.9996 | 47995 | 47975 |
| | MTC | **0.000** | 0.00 | **0.0000** | 1199990 | 0 |

---

## 3. Diagnostico Detalhado por Cenario

### 3.1 Low Traffic — Funcionamento Ideal

- Todos os slices entregam 100% (ou quase) do trafego demandado.
- PDR > 0.999 em todos os slices; latencias eMBB ~14 ms, URLLC/MTC ~5 ms.
- A capacidade do canal (10 MHz, ~16 Mbps de teto pratico para eMBB com 17 RBGs) e suficiente para acomodar a demanda total (~4.2 Mbps).
- **Conclusao**: o scheduler funciona corretamente em regime nao-saturado. Nenhuma anomalia detectada.

### 3.2 Normal — MTC Completamente Inaniolado (Starvation)

- eMBB demanda 70 Mbps mas so consegue ~16 Mbps (PDR=22.4%, delay > 3.7 s).
- URLLC: delivery perfeito (1 Mbps demanda ~ 1.56 Mbps entregue).
- **MTC: 0 bytes recebidos, PDR=0.0** — 10 UEs com 2 Mbps cada = 20 Mbps de demanda total, mas recebem **nada**.

**Causa-raiz**: O scheduler opera com PF intra-slice. O eMBB (5 UEs, cada um demandando 14 Mbps) satura completamente seus 17 RBGs a cada slot. O URLLC (5 UEs, 200 Kbps cada) e leve e usa poucos RBGs. Sobram para o MTC ~15 RBGs, mas o buffer do RLC UM (10 MB) e o tbSize crescem de forma que o eMBB monopoliza o tempo de transmissao na camada MAC. Na pratica, o PF classifica o eMBB como prioritario por ter maior *potential throughput*, e o MTC nunca consegue ser servido.

### 3.3 Congestion / Stressed / Insufficient — Agravamento Progressivo

- Mesmo padrao dos cenarios de alta carga: eMBB severamente degradado (PDR 11-16%), URLLC perfeito, MTC = 0.
- O cenario `insufficient_resources` duplicou a demanda URLLC (2 Mbps/UE), e o impacto caiu sobre o eMBB (PDR caiu de 15.7% para 11.5%, throughput de 16 para 11.75 Mbps).
- Nao ha diferenca significativa entre `congestion` e `stressed`, pois os parametros de trafego sao identicos — a diferenca de SLA target nao afeta o scheduler estatico atual (sem agente DRL).

---

## 4. Analise da Alocacao de RBGs (rslaq_slice_allocations.csv)

O CSV de alocacao (do ultimo cenario executado) revela o particionamento por slot:

| Slice | Weight Configurado | Budget RBGs | Alocado Typical |
|---|---|---|---|
| 0 (eMBB) | 0.3333 | 17 | 17 |
| 1 (URLLC) | 0.4000 | 21 | 5-10 |
| 2 (MTC) | 0.2667 | 15 | 15 |

**Observacoes**:
- O particionamento de RBGs por peso esta **funcionando** corretamente (17+21+15 = 53 RBGs totais em 10 MHz).
- URLLC so aloca 5-10 RBGs (demanda baixa, PF satisfeito rapidamente), sobrando capacidade no budget do slice.
- O budget do MTC (15 RBGs) e alocado integralmente, mas os dados nunca chegam ao receptor.
- **O problema nao esta no particionamento inter-slice** — esta na camada MAC/RLC: os pacotes MTC sao gerados, entram no buffer RLC, mas nunca sao transmitidos com sucesso.

---

## 5. Analise Temporal (rslaq_stats_timeseries.csv)

O timeseries captura o cenario `insufficient_resources` com granularidade de 10 ms:

- **MTC**: throughput persistentemente **0.000 Mbps** durante toda a simulacao (todos os 1000+ intervalos), transmitindo ~16 KB/periodo mas com 0 bytes recebidos.
- **URLLC**: throughput estavel ~0.56-0.94 Mbps/UE, consistente com a demanda configurada.
- **eMBB**: throughput oscilando entre 1.2-3.7 Mbps/UE (muito abaixo dos 20 Mbps demandados por UE).
- **RSH (resource share)**: constante em 33.33% eMBB, 40% URLLC, 26.67% MTC — confirmando que os pesos nao mudam ao longo da simulacao (agente DRL desabilitado).
- **BFS (buffer frustration)**: sempre 0% — o FlowMonitor nao reporta perda explicita, mas os pacotes MTC ficam retidos no buffer RLC sem serem entregues.

---

## 6. Verificacao de Mapeamento de RNTIs

O arquivo `rslaq_unmapped_rntis.csv` esta **vazio** (apenas header). Isso confirma que todos os RNTIs foram mapeados corretamente aos seus respectivos slices. Nao ha UEs "orfãos" no sistema.

---

## 7. Problemas Criticos Identificados

### 7.1 Starvation Total do Slice MTC (Bug Estrutural)

O MTC **nunca recebe dados** em nenhum cenario com demanda eMBB > 50 Kbps. Causas provaveis:

1. **10 UEs MTC com 100 bytes/pkt a 2 Mbps** = 20.000 pkt/s por UE. O buffer RLC de 10 MB acumula pacotes rapidamente.
2. Os 15 RBGs alocados ao MTC nao sao suficientes para servir 10 UEs com PF, pois o `m_dlTbSize` nunca satisfaz a condicao de parada `m_dlTbSize >= max(bufQueueSize, 10)`.
3. **Possivel bug**: a condicao em `AssignDLRBG` (rslaq-mac-scheduler.cc:461) verifica se `GetUe(ue)->m_dlTbSize >= std::max(bufQueueSize, 10U)` para pular o UE. Se o `m_dlTbSize` crescer sem bound para UEs MTC, eles nunca serao servidos.
4. Outra hipotese: os RBGs alocados ao MTC estao sendo efetivamente usados, mas os pacotes nao passam pelo RLC/MAC para a camada PHY — possivel problema de integracao com o stack NR do 5G-LENA.

### 7.2 Pesos Estaticos — Sem Adaptacao

O prototipo usa pesos fixos (0.3333, 0.4000, 0.2667). No artigo RSLAQ, o agente DRL ajusta `p_j` dinamicamente a cada frame. Sem isso:
- Nao ha protecao de SLA para o slice MTC
- eMBB sofre degradacao severa em cenarios de alta demanda
- URLLC e superprotegido (40% dos recursos para demanda de ~1-2 Mbps)

### 7.3 Eficacia do PF Intra-Slice com Demanda Insaciavel

Quando todos os UEs de um slice tem demanda infinita (buffer sempre cheio), o PF degenera para round-robin. Isso significa que:
- 5 UEs eMBB com 17 RBGs = ~3.4 RBGs/UE/slot = throughput muito limitado
- 10 UEs MTC com 15 RBGs = ~1.5 RBGs/UE/slot = throughput extremamente baixo
- O PF nao consegue diferenciar prioridades dentro de um slice quando todos estao igualmente "com fome"

---

## 8. Recomendacoes

### 8.1 Investigar o Starvation do MTC (Prioridade Alta)

Verificar se o `m_dlTbSize` dos UEs MTC esta sendo atualizado corretamente. Acoes especificas:

- **Adicionar logging detalhado** no `AssignDLRBG` para imprimir, a cada slot, o `m_dlTbSize`, `bufQueueSize` e o numero de RBGs alocados para cada UE MTC.
- **Verificar a condicao de pulo** em `rslaq-mac-scheduler.cc:461`: se `m_dlTbSize` e inicializado com um valor alto ou se `UpdateDlPFMetric` nao e chamado corretamente para UEs MTC, eles podem ser perpetuamente pulados.
- **Testar com 1 UE MTC** para verificar se o problema e proporcional ao numero de UEs ou estrutural.
- **Comparar** removendo a divisao em slices (usar scheduler PF padrao do 5G-LENA) para verificar se o MTC recebe dados sem o RSLAQ.

### 8.2 Rebalancear Pesos Iniciais

Com 10 UEs MTC demandando throughput, o peso de 26.67% (15 RBGs) pode ser insuficiente. Sugestoes:

- **Pesos proporcionais ao numero de UEs**: eMBB=0.20, URLLC=0.20, MTC=0.60 (refletindo que MTC tem 2x mais UEs).
- **Ou pesos proporcionais a demanda**: calcular com base na demanda agregada de cada slice.
- Implementar como parametro configuravel no script de simulacao para facilitar experimentacao.

### 8.3 Implementar Alocacao Minima Garantida por Slice

Garantir que cada slice receba pelo menos N RBGs por slot, independente da demanda dos outros slices. Isso previne starvation completo:

```
minRBGs_per_slice = max(1, totalRBGs / numSlices / 2)
```

Se um slice nao usar seus RBGs minimos, eles podem ser redistribuidos aos slices com demanda.

### 8.4 Implementar o Agente DRL (Roadmap RSLAQ)

O artigo RSLAQ propoe ajuste dinamico dos pesos `p_j` via Deep Reinforcement Learning a cada frame (10 ms). Sem isso, o scheduler nao pode reagir a mudancas de demanda entre slices. Componentes necessarios:

1. **Observacao (state)**: throughput por slice, PDR, delay, buffer occupancy, RBG utilization.
2. **Acao**: ajustar o vetor de pesos `p_j` (soma = 1.0).
3. **Recompensa**: baseada no cumprimento de SLA targets por slice (e.g., penalizar violacao de delay para URLLC, penalizar baixo throughput para eMBB).
4. **Politica**: rede neural (PPO, SAC ou similar) treinada offline com os cenarios de simulacao.

### 8.5 Aumentar o Tempo de Simulacao

10 segundos e relativamente curto para avaliar comportamento em regime estacionario. Recomendar:
- **60-120 s** para cenarios de carga moderada
- **300+ s** para avaliar convergencia de algoritmos adaptativos (futuro DRL)
- Executar com **multiplas seeds** (pelo menos 5) para obter intervalos de confianca estatistica.

### 8.6 Monitorar Ocupacao do Buffer RLC

Adicionar metricas de ocupacao do buffer RLC por UE/slice para diagnosticar exatamente onde os pacotes MTC ficam retidos:

- **RLC buffer size** por UE a cada periodo de estatisticas
- **Taxa de descarte** do buffer RLC (se houver)
- **Numero de PDUs RLC transmitidas vs. SDUs recebidas**

Isso pode ser feito via tracing do ns-3 (`TraceSource` do `NrRlcUm`) ou adicionando contadores no callback de estatisticas.

### 8.7 Adicionar Cenarios Intermediarios

Os cenarios atuais saltam de 50 Kbps (low) para 70 Mbps (normal). Recomendar cenarios intermediarios:
- **medium_traffic**: eMBB 10 Mbps, MTC 10 Mbps
- **mixed_load**: eMBB 30 Mbps, URLLC 5 Mbps, MTC 20 Mbps

Isso permite observar a transicao gradual do regime nao-saturado para saturado e identificar o ponto exato onde o MTC comeca a sofrer starvation.

### 8.8 Validar com Scheduler de Referencia

Executar os mesmos cenarios com o scheduler Round Robin (RR) ou PF padrao do 5G-LENA (sem slicing) para estabelecer um baseline de comparacao. Isso permite quantificar o impacto (positivo ou negativo) da camada de slicing do RSLAQ.

---

## 9. Resumo Executivo

| Aspecto | Status |
|---|---|
| Particionamento de RBGs por peso | Funcionando corretamente |
| Mapeamento RNTI -> Slice | Funcionando (0 unmapped) |
| URLLC (slice prioritario) | PDR > 0.999 em todos os cenarios |
| eMBB (slice de capacidade) | Severamente degradado em carga alta (PDR 11-22%) |
| MTC (slice massivo) | **Starvation total** em todos os cenarios com carga > low |
| Adaptacao dinamica de pesos | Nao implementada (pesos estaticos) |
| Regime nao-saturado (low_traffic) | Funcionamento correto e validado |

O prototipo valida o conceito de particionamento estatico de RBGs por slice, mas revela uma limitacao critica: **sem mecanismo de adaptacao dinamica (agente DRL) e sem garantia minima de alocacao, o slice MTC sofre starvation total em cenarios de carga moderada a alta**. A implementacao do agente DRL e a correcao do mecanismo de servico intra-slice para UEs MTC sao os proximos passos prioritarios.

---

*Arquivos CSV analisados:*
- `rslaq_low_traffic_slice.csv`, `rslaq_low_traffic_ue.csv`
- `rslaq_normal_slice.csv`, `rslaq_normal_ue.csv`
- `rslaq_congestion_slice.csv`, `rslaq_congestion_ue.csv`
- `rslaq_stressed_slice.csv`, `rslaq_stressed_ue.csv`
- `rslaq_insufficient_resources_slice.csv`, `rslaq_insufficient_resources_ue.csv`
- `rslaq_slice_allocations.csv`
- `rslaq_stats_timeseries.csv`
- `rslaq_unmapped_rntis.csv`
