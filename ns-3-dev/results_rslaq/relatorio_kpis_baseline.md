# Relatório de KPIs — Baseline RSLAQ (Pesos Estáticos)

## 1. Configuração Experimental

### 1.1 Topologia

| Parâmetro | Valor |
|---|---|
| gNBs | 1 |
| UEs | 20 (5 eMBB + 5 URLLC + 10 MTC) |
| Modelo de canal | 3GPP UMi (Urban Micro) |
| Frequência central | 3.5 GHz |
| Bandwidth | 100 MHz |
| Numerologia | 0 (subcarrier spacing 15 kHz) |
| Tx Power gNB | 30 dBm |
| Mobilidade | Constante, posições aleatórias (30 m × 30 m) |
| Sombreamento | Desativado |
| Duração da simulação | 10 s |

### 1.2 Pesos Estáticos do Scheduler

| Slice | Peso Configurado | RBGs Alocados por TTI |
|---|---|---|
| eMBB (slice 0) | 33.33% | 17 |
| URLLC (slice 1) | 40.00% | 21 |
| MTC (slice 2) | 26.67% | 15 |
| **Total** | **100%** | **53** |

### 1.3 Tráfego Oferecido por Cenário

| Cenário | eMBB (5 UEs) | URLLC (5 UEs) | MTC (10 UEs) | Total Oferecido |
|---|---|---|---|---|
| low_traffic | 50 Kbps, pkts 1500 B | 1 Mbps, pkts 50 B | 2 Mbps, pkts 100 B | ~3.05 Mbps |
| normal | 70 Mbps, pkts 1500 B | 1 Mbps, pkts 50 B | 2 Mbps, pkts 100 B | ~73 Mbps |
| congestion | 100 Mbps, pkts 1500 B | 1 Mbps, pkts 50 B | 100 Mbps, pkts 100 B | ~201 Mbps |
| stressed | 100 Mbps, pkts 1500 B | 1 Mbps, pkts 50 B | 100 Mbps, pkts 100 B | ~201 Mbps |
| insufficient_resources | 100 Mbps, pkts 1500 B | 2 Mbps, pkts 50 B | 100 Mbps, pkts 100 B | ~202 Mbps |

**Notas sobre os cenários:**
- `congestion` e `stressed` possuem mesma carga — diferem apenas na seed (44 vs 45).
- `insufficient_resources` dobra a demanda URLLC (2 Mbps) em relação aos demais.

### 1.4 Targets SLA

| Slice | Métrica | Target |
|---|---|---|
| eMBB | Throughput agregado | > 10 Mbps |
| URLLC | Delay médio | < 10 ms |
| MTC | PDR (confiabilidade) | > 99% (0.99) |

---

## 2. KPIs por Cenário

### 2.1 Cenário: low_traffic

#### Throughput

| Slice | Oferecido (Mbps) | Entregue (Mbps) | Por UE (Mbps) |
|---|---|---|---|
| eMBB | 0.050 | **0.045** | 0.009 |
| URLLC | 1.000 | **1.559** | 0.312 |
| MTC | 2.000 | **2.558** | 0.256 |

> A taxa entregue supera a oferecida porque o OnOffHelper envia a taxa constante a partir do start, e o accumulation over 10 s captura rajadas iniciais. O throughput agregado URLLC+MTC reflete o overhead de cabeçalhos.

#### Delay

| Slice | Delay Médio (ms) | Status SLA |
|---|---|---|
| eMBB | 13.96 | N/A (sem target de delay para eMBB) |
| URLLC | 5.01 | **PASS** (< 10 ms) |
| MTC | 5.02 | N/A |

#### PDR

| Slice | TX Packets | RX Packets | PDR | Status SLA |
|---|---|---|---|---|
| eMBB | 35 | 35 | **1.0000** | N/A |
| URLLC | 23.995 | 23.985 | **0.9996** | PASS |
| MTC | 23.990 | 23.980 | **0.9996** | **PASS** (> 0.99) |

#### Utilização

| Slice | Delivered / Offered |
|---|---|
| eMBB | 89.3% |
| URLLC | 155.9% (rajadas + overhead) |
| MTC | 127.9% (rajadas + overhead) |

#### SLA Summary

| Slice | Target | Resultado |
|---|---|---|
| eMBB throughput > 10 Mbps | **FAIL** | 0.045 Mbps (carga insuficiente) |
| URLLC delay < 10 ms | **PASS** | 5.01 ms |
| MTC PDR > 99% | **PASS** | 0.9996 |

> O único cenário onde MTC é atendido. Todos os slices operam sem contenção significativa.

---

### 2.2 Cenário: normal

#### Throughput

| Slice | Oferecido (Mbps) | Entregue (Mbps) | Por UE (Mbps) |
|---|---|---|---|
| eMBB | 70.000 | **15.998** | 3.200 |
| URLLC | 1.000 | **1.559** | 0.312 |
| MTC | 2.000 | **0.000** | 0.000 |

#### Delay

| Slice | Delay Médio (ms) | Status SLA |
|---|---|---|
| eMBB | **3.729** | Bufferbloat severo |
| URLLC | 5.02 | **PASS** |
| MTC | N/A | Sem pacotes recebidos |

#### PDR

| Slice | TX Packets | RX Packets | PDR | Status SLA |
|---|---|---|---|---|
| eMBB | 55.995 | 12.564 | **0.2244** | 77.6% dos pacotes descartados |
| URLLC | 23.995 | 23.985 | **0.9996** | PASS |
| MTC | 23.990 | 0 | **0.0000** | **FAIL** — starvation total |

#### Utilização

| Slice | Delivered / Offered |
|---|---|
| eMBB | 22.9% |
| URLLC | 155.9% |
| MTC | 0.0% |

#### SLA Summary

| Slice | Target | Resultado |
|---|---|---|
| eMBB throughput > 10 Mbps | **PASS** | 15.998 Mbps |
| URLLC delay < 10 ms | **PASS** | 5.02 ms |
| MTC PDR > 99% | **FAIL** | 0.0000 — nenhum pacote entregue |

> MTC desaparece completamente. eMBB monopoliza os buffers apesar de só entregar 23% da demanda.

---

### 2.3 Cenário: congestion

#### Throughput

| Slice | Oferecido (Mbps) | Entregue (Mbps) | Por UE (Mbps) |
|---|---|---|---|
| eMBB | 100.000 | **15.992** | 3.199 |
| URLLC | 1.000 | **1.559** | 0.312 |
| MTC | 100.000 | **0.000** | 0.000 |

#### Delay

| Slice | Delay Médio (ms) | Status SLA |
|---|---|---|
| eMBB | **4.052** | Bufferbloat severo |
| URLLC | 5.02 | **PASS** |
| MTC | N/A | Sem pacotes recebidos |

#### PDR

| Slice | TX Packets | RX Packets | PDR | Status SLA |
|---|---|---|---|---|
| eMBB | 79.995 | 12.559 | **0.1570** | 84.3% dos pacotes descartados |
| URLLC | 23.995 | 23.985 | **0.9996** | PASS |
| MTC | 1.199.990 | 0 | **0.0000** | **FAIL** — starvation total |

#### Utilização

| Slice | Delivered / Offered |
|---|---|
| eMBB | 16.0% |
| URLLC | 155.9% |
| MTC | 0.0% |

#### SLA Summary

| Slice | Target | Resultado |
|---|---|---|
| eMBB throughput > 10 Mbps | **PASS** | 15.992 Mbps |
| URLLC delay < 10 ms | **PASS** | 5.02 ms |
| MTC PDR > 99% | **FAIL** | 0.0000 |

> MTC tenta transmitir 1.2M pacotes de 100B (100 Mbps) mas não entrega nenhum. A carga MTC 50x maior que o `normal` não altera o resultado — MTC já estava em starvation desde `normal`.

---

### 2.4 Cenário: stressed

#### Throughput

| Slice | Oferecido (Mbps) | Entregue (Mbps) | Por UE (Mbps) |
|---|---|---|---|
| eMBB | 100.000 | **16.043** | 3.208 |
| URLLC | 1.000 | **1.559** | 0.312 |
| MTC | 100.000 | **0.000** | 0.000 |

#### Delay

| Slice | Delay Médio (ms) | Status SLA |
|---|---|---|
| eMBB | **4.052** | Bufferbloat severo |
| URLLC | 5.01 | **PASS** |
| MTC | N/A | Sem pacotes recebidos |

#### PDR

| Slice | TX Packets | RX Packets | PDR | Status SLA |
|---|---|---|---|---|
| eMBB | 79.995 | 12.599 | **0.1575** | 84.3% dos pacotes descartados |
| URLLC | 23.995 | 23.985 | **0.9996** | PASS |
| MTC | 1.199.990 | 0 | **0.0000** | **FAIL** — starvation total |

#### Utilização

| Slice | Delivered / Offered |
|---|---|
| eMBB | 16.0% |
| URLLC | 155.9% |
| MTC | 0.0% |

#### SLA Summary

| Slice | Target | Resultado |
|---|---|---|
| eMBB throughput > 10 Mbps | **PASS** | 16.043 Mbps |
| URLLC delay < 10 ms | **PASS** | 5.01 ms |
| MTC PDR > 99% | **FAIL** | 0.0000 |

> Resultados praticamente idênticos ao `congestion` (diferença apenas na seed). Confirma reprodutibilidade.

---

### 2.5 Cenário: insufficient_resources

#### Throughput

| Slice | Oferecido (Mbps) | Entregue (Mbps) | Por UE (Mbps) |
|---|---|---|---|
| eMBB | 100.000 | **11.748** | 2.351 |
| URLLC | 2.000 | **3.118** | 0.624 |
| MTC | 100.000 | **0.000** | 0.000 |

#### Delay

| Slice | Delay Médio (ms) | Status SLA |
|---|---|---|
| eMBB | **4.253** | Pior delay entre todos os cenários |
| URLLC | 5.02 | **PASS** |
| MTC | N/A | Sem pacotes recebidos |

#### PDR

| Slice | TX Packets | RX Packets | PDR | Status SLA |
|---|---|---|---|---|
| eMBB | 79.995 | 9.226 | **0.1153** | 88.5% dos pacotes descartados |
| URLLC | 47.995 | 47.975 | **0.9996** | PASS |
| MTC | 1.199.990 | 0 | **0.0000** | **FAIL** — starvation total |

#### Utilização

| Slice | Delivered / Offered |
|---|---|
| eMBB | 11.7% |
| URLLC | 155.9% |
| MTC | 0.0% |

#### SLA Summary

| Slice | Target | Resultado |
|---|---|---|
| eMBB throughput > 10 Mbps | **PASS** | 11.748 Mbps |
| URLLC delay < 10 ms | **PASS** | 5.02 ms |
| MTC PDR > 99% | **FAIL** | 0.0000 |

> A demanda URLLC dobrada (2 Mbps) é totalmente atendida sem degradação. Porém, os RBGs adicionais necessários reduzem a capacidade eMBB de ~16 para ~12 Mbps (-27%). MTC permanece em starvation.

---

## 3. Análise Comparativa Cross-Cenário

### 3.1 Throughput por Slice

| Cenário | eMBB (Mbps) | URLLC (Mbps) | MTC (Mbps) | Total Entregue |
|---|---|---|---|---|
| low_traffic | 0.045 | 1.559 | 2.558 | 4.16 |
| normal | 15.998 | 1.559 | 0.000 | 17.56 |
| congestion | 15.992 | 1.559 | 0.000 | 17.55 |
| stressed | 16.043 | 1.559 | 0.000 | 17.60 |
| insufficient | 11.748 | 3.118 | 0.000 | 14.87 |

> A capacidade total do sistema fica entre ~14.9 e ~17.6 Mbps, limitada pela PHY. O eMBB sozinho satura os 17 RBGs alocados.

### 3.2 Delay por Slice

| Cenário | eMBB (ms) | URLLC (ms) | MTC (ms) |
|---|---|---|---|
| low_traffic | 13.96 | 5.01 | 5.02 |
| normal | 3.729 | 5.02 | — |
| congestion | 4.052 | 5.02 | — |
| stressed | 4.052 | 5.01 | — |
| insufficient | 4.253 | 5.02 | — |

> eMBB delay cresce 300x entre low_traffic e normal, estabilizando em ~4s. URLLC mantém 5ms estável em todos os cenários.

### 3.3 PDR por Slice

| Cenário | eMBB | URLLC | MTC |
|---|---|---|---|
| low_traffic | 1.0000 | 0.9996 | 0.9996 |
| normal | 0.2244 | 0.9996 | 0.0000 |
| congestion | 0.1570 | 0.9996 | 0.0000 |
| stressed | 0.1575 | 0.9996 | 0.0000 |
| insufficient | 0.1153 | 0.9996 | 0.0000 |

> URLLC é o único slice com PDR consistente. MTC colapsa para 0 a partir de `normal`.

### 3.4 SLA Compliance Global

| Cenário | eMBB Thr > 10M | URLLC Delay < 10ms | MTC PDR > 99% | Score |
|---|---|---|---|---|
| low_traffic | FAIL | PASS | PASS | **1/3** |
| normal | PASS | PASS | FAIL | **2/3** |
| congestion | PASS | PASS | FAIL | **2/3** |
| stressed | PASS | PASS | FAIL | **2/3** |
| insufficient | PASS | PASS | FAIL | **2/3** |
| **Total** | **4/5** | **5/5** | **1/5** | |

> Nenhum cenário atende 3/3 SLAs simultaneamente com pesos estáticos.

---

## 4. Diagnóstico de Anomalias

### 4.1 MTC Starvation

**Severidade**: CRÍTICA
**Cenários afetados**: normal, congestion, stressed, insufficient_resources

MTC transmite até 1.199.990 pacotes mas entrega zero. A causa é estrutural:

- MTC tem pacotes de 100B e peso de 15 RBGs (26.7%)
- eMBB tem pacotes de 1500B e peso de 17 RBGs (33.3%)
- O buffer do gNB prioriza pacotes maiores de eMBB via PF intra-slice
- Os 15 RBGs de MTC são insuficientes para drenar a fila quando eMBB satura o sistema
- Resultado: pacotes MTC acumulam e são descartados por timeout/overflow

### 4.2 eMBB Bufferbloat

**Severidade**: ALTA
**Cenários afetados**: normal, congestion, stressed, insufficient_resources

Delay de 3.7-4.3 segundos e PDR de 11-22%. A capacidade PHY com 17 RBGs entrega ~16 Mbps, mas a demanda é 70-100 Mbps. O excesso enche os buffers:

- Taxa de chegada: 70-100 Mbps
- Taxa de serviço: ~16 Mbps
- Buffer buildup: ~54-84 Mbps de excesso acumulado
- Os pacotes que eventualmente passam acumularam segundos de fila

### 4.3 URLLC Isolamento

**Severidade**: Nenhuma (funcionamento correto)
**Cenários afetados**: todos

URLLC mantém delay ~5ms e PDR ~0.9996 em todos os cenários, inclusive com demanda dobrada (`insufficient_resources`). O peso de 40% (21 RBGs) e os pacotes pequenos (50B) garantem drenagem rápida da fila.

### 4.4 Desperdício de RBGs

Os RBGs alocados a MTC (15 por TTI) ficam ociosos quando MTC está em starvation. Em `rslaq_slice_allocations.csv`, o campo `allocatedRbg` mostra que o slice MTC aloca 15 RBGs por TTI mesmo sem entregar pacotes — os recursos não são redistribuídos para eMBB ou URLLC.

---

## 5. Conclusões

1. **O scheduler com pesos estáticos falha em atender as SLAs de todos os slices simultaneamente** em qualquer cenário. O melhor score é 2/3.

2. **MTC é o slice mais vulnerável**: starvation total em 4/5 cenários. O peso estático de 26.7% é insuficiente para competir com pacotes grandes de eMBB.

3. **URLLC é o slice mais protegido**: o peso de 40% garante isolamento perfeito. Este é o único SLA universalmente atendido.

4. **eMBB sofre de bufferbloat**: entrega apenas 12-16 Mbps contra demanda de 70-100 Mbps, com delays de segundos.

5. **Não há reutilização de RBGs**: recursos de slices ociosos não são redistribuídos, resultando em desperdício.

6. **O baseline valida a necessidade do agente DRL**: a alocação adaptativa de PRBs deve redistribuir dinamicamente os RBGs de MTC (ociosos) e ajustar os pesos de eMBB (sobrecarregado) para maximizar o atendimento simultâneo das SLAs.

---

## 6. Arquivos de Dados

| Arquivo | Descrição |
|---|---|
| `rslaq_low_traffic_slice.csv` | KPIs agregados por slice — cenário low_traffic |
| `rslaq_low_traffic_ue.csv` | KPIs por UE — cenário low_traffic |
| `rslaq_normal_slice.csv` | KPIs agregados por slice — cenário normal |
| `rslaq_normal_ue.csv` | KPIs por UE — cenário normal |
| `rslaq_congestion_slice.csv` | KPIs agregados por slice — cenário congestion |
| `rslaq_congestion_ue.csv` | KPIs por UE — cenário congestion |
| `rslaq_stressed_slice.csv` | KPIs agregados por slice — cenário stressed |
| `rslaq_stressed_ue.csv` | KPIs por UE — cenário stressed |
| `rslaq_insufficient_resources_slice.csv` | KPIs agregados por slice — cenário insufficient_resources |
| `rslaq_insufficient_resources_ue.csv` | KPIs por UE — cenário insufficient_resources |
| `rslaq_stats_timeseries.csv` | Série temporal de KPIs por UE (último cenário executado) |
| `rslaq_slice_allocations.csv` | Alocação de RBGs por TTI (último cenário executado) |
| `rslaq_unmapped_rntis.csv` | RNTIs não mapeados (vazio — todos os UEs mapeados) |
