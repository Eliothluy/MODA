# Relatório de Análise de Simulação 5G Slice-Aware

**Data da Análise:** 2026-05-07 13:57
**Analista:** Engenharia de Dados Senior - Redes 5G
**Diretório de Origem:** `/home/elioth/Documentos/artigo_jussi/ns-3-dev/results_sliceaware_scenarios`

---

## 1. Resumo Executivo

Este relatório apresenta uma análise completa dos resultados de simulação de rede 5G com suporte a Network Slicing (Slice-Aware Scheduling). Foram avaliados **7 cenários distintos**, abrangendo condições normais, congestionadas, com ênfase em vídeo (eMBB), massivo IoT (mMTC) e otimização energética.

### 1.1 Cenários Avaliados

| Cenário | Descrição | Arquivos Disponíveis |
|---------|-----------|---------------------|
| greenran_normal | Cenário baseline com tráfego normal | slice, sla, ue_detail, active_dl, timeseries, alloc |
| greenran_low | Cenário de carga baixa | slice, sla, ue_detail, active_dl, timeseries, alloc |
| greenran_balanced | Cenário com balanceamento de carga | slice, sla, ue_detail, active_dl, timeseries, alloc |
| greenran_night_energy | Cenário noturno com otimização energética | slice, sla, ue_detail, active_dl, timeseries, alloc |
| greenran_congestion | Cenário de congestão de rede | slice, sla, ue_detail, active_dl, timeseries, alloc |
| greenran_mmtc_massive | Cenário massivo mMTC (IoT) | ue_detail, active_dl, timeseries, alloc |
| greenran_video_heavy | Cenário com alta carga de vídeo (eMBB) | slice, sla, ue_detail, active_dl, timeseries, alloc |

## 2. Análise Detalhada por Cenário

### 2.1 Cenário: `greenran_normal`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 105.72 | 48.2 | 0.83 | 0.83 |
| VIDEO_EMBB | 5 | DL | 0.06 | 1659.0 | 0.14 | 0.14 |
| SENSOR_MMTC | 25 | UL | 10.09 | 37.3 | 0.63 | 0.63 |
| SENSOR_MMTC | 25 | DL | 0.00 | 0.0 | 0.00 | 0.00 |

- **Total de UEs:** 60
- **Throughput Médio Agregado:** 28.97 Mbps
- **Delay Médio Agregado:** 436.1 ms
- **Menor PDR (Effective):** 0.00 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 48.2 | 0.99 | 0.83 | 118.75 | 105.72 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 1659.0 | 0.99 | 0.14 | 118.75 | 0.06 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 37.3 | 0.99 | 0.63 | 0.00 | 10.09 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 0.0 | 0.99 | 0.00 | 0.00 | 0.00 | 🔴 SIM |

- **Total de SLAs Violados:** 4 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 40 | 15880.6 | 15968.0 | 22259 | 3668.8 |
| 1 | 200 | 17049.5 | 17033.0 | 25217 | 4587.2 |

- **Maior Buffer DL Registrado:** 25217 bytes (24.6 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 3408 | 15880.6 | 15968.0 | 22259 | 3623.2 |
| 1 | 848 | 17049.5 | 17033.0 | 25217 | 4578.4 |

- **Maior Buffer Queue Registrado:** 25217 bytes (24.6 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 57.02 | 100.00 |
| 1 | 66.93 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 1314.645 | 0.000 | 6335.270 |
| 1 | 26.467 | 0.000 | 158.925 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.2 Cenário: `greenran_low`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 77.39 | 313.9 | 0.61 | 0.61 |
| VIDEO_EMBB | 5 | DL | 0.06 | 2133.5 | 0.15 | 0.15 |
| SENSOR_MMTC | 10 | UL | 5.22 | 40.0 | 0.82 | 0.82 |
| SENSOR_MMTC | 10 | DL | 0.01 | 2370.3 | 0.02 | 0.02 |

- **Total de UEs:** 30
- **Throughput Médio Agregado:** 20.67 Mbps
- **Delay Médio Agregado:** 1214.4 ms
- **Menor PDR (Effective):** 0.02 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 313.9 | 0.99 | 0.61 | 118.75 | 77.39 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 2133.5 | 0.99 | 0.15 | 118.75 | 0.06 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 40.0 | 0.99 | 0.82 | 0.00 | 5.22 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 2370.3 | 0.99 | 0.02 | 0.00 | 0.01 | 🔴 SIM |

- **Total de SLAs Violados:** 4 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 10 | 22933.9 | 22928.5 | 24495 | 1628.5 |
| 1 | 20 | 23434.5 | 23425.0 | 25488 | 2098.6 |

- **Maior Buffer DL Registrado:** 25488 bytes (24.9 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 852 | 22934.0 | 22928.5 | 24495 | 1545.9 |
| 1 | 212 | 23433.9 | 23425.0 | 25488 | 2049.8 |

- **Maior Buffer Queue Registrado:** 25488 bytes (24.9 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 72.68 | 100.00 |
| 1 | 58.11 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 921.011 | 0.000 | 6333.821 |
| 1 | 34.097 | 0.000 | 158.720 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.3 Cenário: `greenran_balanced`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 56.62 | 416.0 | 0.44 | 0.44 |
| VIDEO_EMBB | 5 | DL | 0.15 | 1071.9 | 0.36 | 0.36 |
| SENSOR_MMTC | 30 | UL | 10.64 | 28.9 | 0.55 | 0.55 |
| SENSOR_MMTC | 30 | DL | 0.03 | 1532.9 | 0.01 | 0.01 |

- **Total de UEs:** 70
- **Throughput Médio Agregado:** 16.86 Mbps
- **Delay Médio Agregado:** 762.4 ms
- **Menor PDR (Effective):** 0.01 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 416.0 | 0.99 | 0.44 | 118.75 | 56.62 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 1071.9 | 0.99 | 0.36 | 118.75 | 0.15 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 28.9 | 0.99 | 0.55 | 0.00 | 10.64 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 1532.9 | 0.99 | 0.01 | 0.00 | 0.03 | 🔴 SIM |

- **Total de SLAs Violados:** 4 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 20 | 12664.5 | 12651.5 | 13803 | 895.3 |
| 1 | 120 | 15504.1 | 15419.5 | 18089 | 1737.1 |

- **Maior Buffer DL Registrado:** 18089 bytes (17.7 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 1704 | 12664.6 | 12651.5 | 13803 | 872.8 |
| 1 | 424 | 15497.1 | 15419.5 | 18089 | 1725.8 |

- **Maior Buffer Queue Registrado:** 18089 bytes (17.7 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 69.38 | 100.00 |
| 1 | 69.54 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 718.193 | 0.000 | 6334.090 |
| 1 | 23.583 | 0.000 | 158.925 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.4 Cenário: `greenran_night_energy`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 41.54 | 57.4 | 0.81 | 0.81 |
| VIDEO_EMBB | 5 | DL | 0.41 | 42.3 | 1.00 | 1.00 |
| SENSOR_MMTC | 10 | UL | 5.60 | 33.6 | 0.88 | 0.88 |
| SENSOR_MMTC | 10 | DL | 0.82 | 288.5 | 1.00 | 1.00 |

- **Total de UEs:** 30
- **Throughput Médio Agregado:** 12.09 Mbps
- **Delay Médio Agregado:** 105.4 ms
- **Menor PDR (Effective):** 0.81 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 57.4 | 0.99 | 0.81 | 47.50 | 41.54 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 42.3 | 0.99 | 1.00 | 47.50 | 0.41 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 33.6 | 0.99 | 0.88 | 0.00 | 5.60 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 288.5 | 0.99 | 1.00 | 0.00 | 0.82 | 🟢 NÃO |

- **Total de SLAs Violados:** 3 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 105 | 682.7 | 665.0 | 1721 | 526.2 |
| 1 | 210 | 2932.0 | 2260.0 | 8838 | 2696.6 |

- **Maior Buffer DL Registrado:** 8838 bytes (8.6 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 8946 | 682.7 | 665.0 | 1721 | 523.7 |
| 1 | 2226 | 2914.9 | 2260.0 | 8838 | 2682.9 |

- **Maior Buffer Queue Registrado:** 8838 bytes (8.6 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 15.69 | 100.00 |
| 1 | 27.72 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 521.730 | 0.000 | 2515.955 |
| 1 | 31.505 | 0.000 | 139.059 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.5 Cenário: `greenran_congestion`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 104.80 | 166.7 | 0.82 | 0.82 |
| VIDEO_EMBB | 5 | DL | 0.41 | 2.7 | 1.00 | 1.00 |
| SENSOR_MMTC | 100 | UL | 0.00 | 0.0 | 0.00 | 0.00 |
| SENSOR_MMTC | 100 | DL | 8.15 | 6.8 | 1.00 | 1.00 |

- **Total de UEs:** 210
- **Throughput Médio Agregado:** 28.34 Mbps
- **Delay Médio Agregado:** 44.0 ms
- **Menor PDR (Effective):** 0.00 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 166.7 | 0.99 | 0.82 | 118.75 | 104.80 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 2.7 | 0.99 | 1.00 | 118.75 | 0.41 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 0.0 | 0.99 | 0.00 | 0.00 | 0.00 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 6.8 | 0.99 | 1.00 | 0.00 | 8.15 | 🟢 NÃO |

- **Total de SLAs Violados:** 3 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 125 | 137.0 | 137.0 | 137 | 0.0 |
| 1 | 2500 | 137.0 | 137.0 | 137 | 0.0 |

- **Maior Buffer DL Registrado:** 137 bytes (0.1 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 10650 | 137.0 | 137.0 | 137 | 0.0 |
| 1 | 15950 | 137.0 | 137.0 | 137 | 0.0 |

- **Maior Buffer Queue Registrado:** 137 bytes (0.1 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 10.61 | 95.45 |
| 1 | 51.09 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 1305.273 | 0.000 | 6321.187 |
| 1 | 5.078 | 0.000 | 20.275 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.6 Cenário: `greenran_mmtc_massive`

*Arquivo de métricas por slice não disponível para este cenário.*

*Arquivo de SLA não disponível para este cenário.*

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 5 | 137.0 | 137.0 | 137 | 0.0 |
| 1 | 100 | 137.0 | 137.0 | 137 | 0.0 |

- **Maior Buffer DL Registrado:** 137 bytes (0.1 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 426 | 137.0 | 137.0 | 137 | 0.0 |
| 1 | 638 | 137.0 | 137.0 | 137 | 0.0 |

- **Maior Buffer Queue Registrado:** 137 bytes (0.1 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 21.29 | 90.91 |
| 1 | 70.13 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 37.666 | 0.000 | 143.635 |
| 1 | 0.100 | 0.000 | 0.410 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

### 2.7 Cenário: `greenran_video_heavy`

#### 2.1.1 Métricas Agregadas por Slice

| Slice | UEs | Dir | Throughput (Mbps) | Avg Delay (ms) | PDR | Effective PDR |
|-------|-----|-----|-------------------|----------------|-----|---------------|
| VIDEO_EMBB | 5 | UL | 91.61 | 129.8 | 0.72 | 0.72 |
| VIDEO_EMBB | 5 | DL | 0.02 | 1994.7 | 0.04 | 0.04 |
| SENSOR_MMTC | 25 | UL | 11.39 | 32.4 | 0.71 | 0.71 |
| SENSOR_MMTC | 25 | DL | 0.00 | 0.0 | 0.00 | 0.00 |

- **Total de UEs:** 60
- **Throughput Médio Agregado:** 25.75 Mbps
- **Delay Médio Agregado:** 539.2 ms
- **Menor PDR (Effective):** 0.00 ⚠️ ALERTA

#### 2.1.2 Cumprimento de SLA

| Slice | Direção | SLA Delay (ms) | Medido Delay (ms) | SLA PDR | Medido PDR | SLA Thr (Mbps) | Medido Thr (Mbps) | Violação Geral |
|-------|---------|----------------|-------------------|---------|------------|----------------|-------------------|----------------|
| VIDEO_EMBB | UL | 100.0 | 129.8 | 0.99 | 0.72 | 118.75 | 91.61 | 🔴 SIM |
| VIDEO_EMBB | DL | 100.0 | 1994.7 | 0.99 | 0.04 | 118.75 | 0.02 | 🔴 SIM |
| SENSOR_MMTC | UL | 5000.0 | 32.4 | 0.99 | 0.71 | 0.00 | 11.39 | 🔴 SIM |
| SENSOR_MMTC | DL | 5000.0 | 0.0 | 0.99 | 0.00 | 0.00 | 0.00 | 🔴 SIM |

- **Total de SLAs Violados:** 4 / 4

#### 2.1.3 Análise de Buffer MAC e Congestionamento

**Downlink Buffer (active_dl_diag.csv):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 5 | 21521.0 | 21521.0 | 21521 | 0.0 |
| 1 | 25 | 21521.0 | 21521.0 | 21521 | 0.0 |

- **Maior Buffer DL Registrado:** 21521 bytes (21.0 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)
- **✓ OK:** Buffer DL sob controle na maioria das amostras.

**UE Detail Buffer (ue_detail.csv - bufQueueSize):**

| Slice ID | Amostras | Média (bytes) | Mediana (bytes) | Máximo (bytes) | StdDev |
|----------|----------|---------------|-----------------|----------------|--------|
| 0 | 426 | 21521.0 | 21521.0 | 21521 | 0.0 |
| 1 | 106 | 21521.0 | 21521.0 | 21521 | 0.0 |

- **Maior Buffer Queue Registrado:** 21521 bytes (21.0 KB)
- **Amostras Acima de 50KB:** 0 (0.00%)

**Séries Temporais (timeseries.csv):**

| Slice ID | PLR Médio (%) | PLR Máximo (%) |
|----------|---------------|----------------|
| 0 | 66.82 | 100.00 |
| 1 | 63.23 | 100.00 |

- **🔴 ALERTA DE PERDA:** PLR máximo de 100.00% detectado, indicativo de congestão ou falha de alocação de recursos.

| Slice ID | Throughput Médio (Mbps) | Throughput Mín (Mbps) | Throughput Máx (Mbps) |
|----------|-------------------------|-----------------------|-----------------------|
| 0 | 1104.076 | 0.000 | 6341.786 |
| 1 | 29.646 | 0.000 | 159.130 |

#### 2.1.5 Alocação de RBGs (Downlink)

*Estrutura da alocação: ['callId', 'timeMs', 'scenario', 'slot', 'bwpId', 'beamId', 'sliceId', 'configuredWeight', 'effectiveWeight', 'activeUes', 'hasActiveUe', 'hasDemand', 'totalRbg', 'budgetRbg', 'allocatedRbg', 'borrowedIn', 'borrowedOut', 'reserved', 'cumulAllocRbg', 'cumulCalls', 'reason', 'rntis']*

---

## 3. Análise Comparativa entre Cenários

### 3.1 Comparativo de Throughput e Delay por Cenário

| Cenário | Slice | Dir | Throughput (Mbps) | Delay (ms) | PDR Efetivo | SLA Violado |
|---------|-------|-----|-------------------|------------|-------------|-------------|
| greenran_normal | VIDEO_EMBB | UL | 105.72 | 48.2 | 0.83 | SIM |
| greenran_normal | VIDEO_EMBB | DL | 0.06 | 1659.0 | 0.14 | SIM |
| greenran_normal | SENSOR_MMTC | UL | 10.09 | 37.3 | 0.63 | SIM |
| greenran_normal | SENSOR_MMTC | DL | 0.00 | 0.0 | 0.00 | SIM |
| greenran_low | VIDEO_EMBB | UL | 77.39 | 313.9 | 0.61 | SIM |
| greenran_low | VIDEO_EMBB | DL | 0.06 | 2133.5 | 0.15 | SIM |
| greenran_low | SENSOR_MMTC | UL | 5.22 | 40.0 | 0.82 | SIM |
| greenran_low | SENSOR_MMTC | DL | 0.01 | 2370.3 | 0.02 | SIM |
| greenran_balanced | VIDEO_EMBB | UL | 56.62 | 416.0 | 0.44 | SIM |
| greenran_balanced | VIDEO_EMBB | DL | 0.15 | 1071.9 | 0.36 | SIM |
| greenran_balanced | SENSOR_MMTC | UL | 10.64 | 28.9 | 0.55 | SIM |
| greenran_balanced | SENSOR_MMTC | DL | 0.03 | 1532.9 | 0.01 | SIM |
| greenran_night_energy | VIDEO_EMBB | UL | 41.54 | 57.4 | 0.81 | SIM |
| greenran_night_energy | VIDEO_EMBB | DL | 0.41 | 42.3 | 1.00 | SIM |
| greenran_night_energy | SENSOR_MMTC | UL | 5.60 | 33.6 | 0.88 | SIM |
| greenran_night_energy | SENSOR_MMTC | DL | 0.82 | 288.5 | 1.00 | NÃO |
| greenran_congestion | VIDEO_EMBB | UL | 104.80 | 166.7 | 0.82 | SIM |
| greenran_congestion | VIDEO_EMBB | DL | 0.41 | 2.7 | 1.00 | SIM |
| greenran_congestion | SENSOR_MMTC | UL | 0.00 | 0.0 | 0.00 | SIM |
| greenran_congestion | SENSOR_MMTC | DL | 8.15 | 6.8 | 1.00 | NÃO |
| greenran_mmtc_massive | N/A | N/A | N/A | N/A | N/A | N/A |
| greenran_video_heavy | VIDEO_EMBB | UL | 91.61 | 129.8 | 0.72 | SIM |
| greenran_video_heavy | VIDEO_EMBB | DL | 0.02 | 1994.7 | 0.04 | SIM |
| greenran_video_heavy | SENSOR_MMTC | UL | 11.39 | 32.4 | 0.71 | SIM |
| greenran_video_heavy | SENSOR_MMTC | DL | 0.00 | 0.0 | 0.00 | SIM |

### 3.2 Consolidado de Buffer MAC e Indicadores de Congestionamento

| Cenário | Max Buffer DL (bytes) | Max Buffer Queue (bytes) | PLR Máx (%) | Status Congestão |
|---------|----------------------|--------------------------|-------------|------------------|
| greenran_normal | 25217 | 25217 | 100.00 | 🔴 CONGESTIONADO |
| greenran_low | 25488 | 25488 | 100.00 | 🔴 CONGESTIONADO |
| greenran_balanced | 18089 | 18089 | 100.00 | 🔴 CONGESTIONADO |
| greenran_night_energy | 8838 | 8838 | 100.00 | 🔴 CONGESTIONADO |
| greenran_congestion | 137 | 137 | 100.00 | 🔴 CONGESTIONADO |
| greenran_mmtc_massive | 137 | 137 | 100.00 | 🔴 CONGESTIONADO |
| greenran_video_heavy | 21521 | 21521 | 100.00 | 🔴 CONGESTIONADO |

## 4. Conclusões e Recomendações

### 4.1 Principais Achados

Os seguintes cenários apresentaram indicadores de degradação de performance:

- **greenran_normal:** SLA violado, PLR crítico
- **greenran_low:** SLA violado, PLR crítico
- **greenran_balanced:** SLA violado, PLR crítico
- **greenran_night_energy:** SLA violado, PLR crítico
- **greenran_congestion:** SLA violado, PLR crítico
- **greenran_mmtc_massive:** PLR crítico
- **greenran_video_heavy:** SLA violado, PLR crítico

### 4.2 Recomendações Técnicas

1. **Otimização de Buffer MAC:** Cenários com buffer DL consistentemente acima de 50KB sugerem que o scheduler slice-aware pode estar sub-alocando RBGs para determinados slices. Recomenda-se revisar os pesos de priorização (`p_j`) e a decomposição `P_STA + p_opt`.

2. **Garantia de SLA:** A violação frequente de SLA de delay (especialmente no slice VIDEO_EMBB) indica que o threshold de 100ms pode ser inadequado para a carga oferecida, ou que a alocação de recursos físicos está insuficiente para o BWP configurado.

3. **Balanceamento eMBB vs mMTC:** No cenário `greenran_mmtc_massive`, verificar se a política de uplink (não slice-aware, conforme convenção do projeto) está criando gargalo indireto no downlink slice-aware.

4. **Monitoramento de PLR:** Perdas de pacote acima de 10% em qualquer slice devem acionar mecanismos de adaptação de MCS ou aumento de redundância HARQ.

5. **Eficiência Energética:** O cenário `greenran_night_energy` deve ser avaliado com cautela: redução de potência/clock pode aumentar delay e buffer; garantir que a otimização energética não comprometa SLAs críticos (URLLC).

## 5. Metodologia de Análise de Buffer MAC

A análise de congestionamento de buffer na camada MAC foi realizada com base nos seguintes indicadores:

- **`dlBufferSize` (active_dl_diag.csv):** Tamanho do buffer de downlink reportado pelo diagnóstico de UEs ativos no DL. Valores persistentemente elevados indicam acúmulo de PDUs na fila MAC.
- **`bufQueueSize` (ue_detail.csv):** Tamanho da fila de buffer por UE no momento da alocação. Pico acima de 50KB foi adotado como limiar de alerta.
- **`plr_pct` (timeseries.csv):** Packet Loss Ratio percentual. Valores > 10% indicam descarte ou falha de entrega, frequentemente associados a overflow de buffer ou timeout de HARQ.
- **HARQ Tracking:** Análise de retransmissões e status de processos HARQ ativos.

> **Nota:** O projeto utiliza comunicação IPC via semáforos POSIX e CSV a cada 10ms. A granularidade temporal dos dados permite identificar padrões de burst e saturação em escala de slot/subframe.

---

*Relatório gerado automaticamente por pipeline de análise de dados. Para dúvidas ou aprofundamento, consultar a documentação do projeto em `AGENTS.md` e os logs individuais de simulação.*