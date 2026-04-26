# Documentação Técnica — RSLAQ Slice-Aware Scheduler (Protótipo)

**Versão:** 1.0  
**Data:** 25/04/2026  
**Autor:** Engenharia de Dados 5G  
**Projeto:** Simulação ns-3/5G-LENA inspirada no artigo *"RSLAQ — A Robust SLA-driven 6G O-RAN QoS xApp using deep reinforcement learning"*

---

## 1. Visão Geral

Este documento descreve o protótipo de scheduler slice-aware desenvolvido para o ambiente **ns-3-dev + 5G-LENA (CTTC)**. O código é uma **base para validação de slicing de RAN** antes da integração do agente DRL (Double DQN — DDQL).

> **Escopo atual:** Scheduler MAC slice-aware com particionamento estático/dinâmico de RBGs (Resource Block Groups) por slice.  
> **Escopo futuro:** Integração do agente DRL para ajustar os pesos `p_j` a cada frame (10 ms).

---

## 2. Arquitetura do Sistema

### 2.1 Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                    Aplicação (remote host)                   │
│              OnOffApplication → UDP → IP → PDCP             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EPC (Evolved Packet Core)                 │
│         SGW/PGW → backhaul P2P (100 Gbps, 1 ms)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         gNB (1 célula)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         RSLAQ MAC Scheduler (RslaqMacScheduler)        │  │
│  │  • Particiona RBGs por slice (pesos ω → p_j)          │  │
│  │  • Intra-slice: PF / RR / BCQI                        │  │
│  │  • RNTI → slice mapping (dinâmico)                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                              │                               │
│                    ┌─────────┴─────────┐                     │
│                    ▼                   ▼                     │
│               PHY DL (OFDMA)      PHY UL (OFDMA)             │
│               10 MHz, μ=0         (não slice-aware ainda)    │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               UE eMBB (5)       UE URLLC (5)
               UE MTC  (10)
```

### 2.2 Hierarquia de Classes do Scheduler

```
NrMacSchedulerNs3
    └── NrMacSchedulerOfdma
            └── NrMacSchedulerOfdmaRR
                    └── RslaqMacScheduler  ← nossa classe
```

`RslaqMacScheduler` herda de `NrMacSchedulerOfdmaRR`, mas **sobrescreve** `AssignDLRBG()` para implementar o particionamento por slice. Os demais métodos (`AssignedDlResources`, `NotAssignedDlResources`, `BeforeDlSched`) são sobrescritos para manter as métricas PF atualizadas.

---

## 3. Lógica do Scheduler (`RslaqMacScheduler::AssignDLRBG`)

### 3.1 Fluxo de Execução

```
1. Obter máscara de notching (GetDlNotchedRbgMask)
2. Construir lista de RBG IDs reais disponíveis → availableRbgIds[]
3. Para cada beam ativo:
   3.1 Classificar UEs ativos por slice (usando RNTI → sliceId)
   3.2 Logar todos os RNTIs vistos e contar UEs por slice
   3.3 Detectar slices com demanda real (buffer > 0)
   3.4 Calcular pesos efetivos (renormalização)
   3.5 Distribuir budget de RBGs proporcional aos pesos efetivos
   3.6 Para cada slice ativa:
        • Ordenar UEs pelo algoritmo intra-slice (PF/RR/BCQI)
        • Alocar RBGs reais até esgotar o budget ou a demanda
        • Registrar métricas no CSV
```

### 3.2 Mapeamento RNTI → Slice

**Método:** `GetSliceIndexForRnti(uint16_t rnti)`

- Itera sobre `m_sliceUeRnti[s]` para cada slice `s`.
- Retorna o índice da slice ou `-1` se não encontrado.
- **Nunca descarta silenciosamente:** emite `NS_LOG_WARN` e grava em `rslaq_unmapped_rntis.csv`.

**Fallback opcional:** Atributo `FallbackUnmappedUe` (booleano, default `false`).
- Quando `true`, UEs não mapeados são forçados na slice 0 com log adicional.
- **Recomendação:** Manter `false` em produção. Usar `true` apenas para debug.

### 3.3 Cálculo do Budget de RBG por Slice

**Conceito:** `effectiveWeight` vs `configuredWeight`

| Conceito | Símbolo | Descrição |
|----------|---------|-----------|
| Peso configurado (política) | `ω_j` | Definido pelo operador ou agente DRL. Soma = 1.0. |
| Peso efetivo (aplicado) | `p_j` | `ω_j / Σ(ω_k)` onde `k` são slices **ativas com demanda**. |
| Budget | `B_j` | `floor(totalRbgs × p_j)`. A última slice ativa recebe a sobra. |

**Exemplo numérico:**
```
ω = [0.3333, 0.4000, 0.2667]   (eMBB, URLLC, MTC)
Slices ativas com demanda: eMBB (sim), URLLC (sim), MTC (não)
Σω_ativo = 0.3333 + 0.4000 = 0.7333

p_eMBB   = 0.3333 / 0.7333 ≈ 0.4545
p_URLLC  = 0.4000 / 0.7333 ≈ 0.5455
p_MTC    = 0

Se totalRbgs = 53:
  B_eMBB  = floor(53 × 0.4545) = 24
  B_URLLC = 53 - 24 = 29  (sobra)
```

### 3.4 Tratamento da Máscara de RBG / Notching

**Problema resolvido:** O scheduler original contava RBGs disponíveis (`count(mask)`) mas usava índices sequenciais `0..N-1`, o que quebrava quando havia buracos na máscara.

**Solução implementada:**
```cpp
std::vector<uint32_t> availableRbgIds;
if (!dlNotchedMask.empty()) {
    for (uint32_t i = 0; i < dlNotchedMask.size(); ++i)
        if (dlNotchedMask[i])  // true = disponível
            availableRbgIds.push_back(i);
} else {
    for (uint32_t i = 0; i < GetBandwidthInRbg(); ++i)
        availableRbgIds.push_back(i);
}
```

Ao alocar, converte-se o índice lógico para o ID real:
```cpp
uint32_t actualRbgId = availableRbgIds[logicalIdx];
GetUe(ue)->m_dlRBG.push_back(actualRbgId);
```

> **Importante:** `true` na máscara significa RBG **disponível** (não notched). `false` significa notched/unavailable.

### 3.5 Algoritmos Intra-Slice

Cada slice pode usar um algoritmo independente:

| Algoritmo | Descrição | Classe ns-3 usada |
|-----------|-----------|-------------------|
| RR (Round Robin) | Menos RBGs alocados primeiro | `NrMacSchedulerUeInfoRR::CompareUeWeightsDl` |
| PF (Proportional Fair) | `potentialTput / avgTput` | `NrMacSchedulerUeInfoPF::CompareUeWeightsDl` |
| BCQI (Best CQI) | Maior MCS primeiro | `NrMacSchedulerUeInfoMR::CompareUeWeightsDl` |

> **Nota de implementação:** `CreateUeRepresentation()` sempre cria `NrMacSchedulerUeInfoPF`. Isso é seguro porque PF é um superset funcional de RR/BCQI para o propósito de comparação de pesos. Não afeta a correção dos algoritmos.

---

## 4. Simulação (`rslaq-sim.cc`)

### 4.1 Topologia

- **1 gNB** central, altura 10 m.
- **N UEs** distribuídos aleatoriamente em um retângulo de 60×60 m (`[-30,30]` em X e Y).
- **1 remote host** conectado via backhaul P2P (100 Gbps, 1 ms).
- **Frequência:** 2.59 GHz (band n38).
- **Bandwidth:** 10 MHz.
- **Numerologia:** μ = 0 (SCS 15 kHz).
- **TDD:** Pattern configurável via `--tddPattern` (default `D|D|D|D|D|D|D|D|D|D`).

### 4.2 Mapeamento RNTI Real

O 5G-LENA atribui RNTIs durante o RRC connection setup, **após** `AttachToClosestGnb()`. O código anterior assumia RNTIs sequenciais `1..N`, o que era frágil.

**Novo fluxo:**
1. `AttachToClosestGnb()` é chamado em `t = 0`.
2. Em `t = min(0.1 s, appStartSec - 0.05 s)`, um callback (`ConfigureSliceMapping`) é executado.
3. Para cada UE device:
   ```cpp
   Ptr<NrUeNetDevice> ueDev = DynamicCast<NrUeNetDevice>(ueNetDev.Get(i));
   uint16_t rnti = ueDev->GetRrc()->GetRnti();
   ```
4. O RNTI real é mapeado para a slice correspondente.
5. `SetSliceUeMapping()` e `SetSliceConfiguration()` são chamados no scheduler.

> **Garantia:** Como o tráfego de aplicação só inicia em `appStartSec = 0.4 s` (default), todos os UEs já estarão conectados e com RNTIs válidos antes do primeiro pacote ser transmitido.

### 4.3 Cenários de Tráfego

| Cenário | eMBB | URLLC | MTC | Uso |
|---------|------|-------|-----|-----|
| `low_traffic` | 50 Kbps | 1 Mbps | 2 Mbps | Teste de baixa carga |
| `normal` | 70 Mbps | 1 Mbps | 2 Mbps | Carga média |
| `congestion` | 100 Mbps | 1 Mbps | 100 Mbps | Congestionamento total |
| `stressed` | 100 Mbps | 1 Mbps | 100 Mbps | SLA targets diferenciados |
| `insufficient_resources` | 100 Mbps | 2 Mbps | 100 Mbps | Recursos insuficientes |

Cada UE recebe a taxa total do slice dividida pelo número de UEs naquele slice.

### 4.4 Parâmetros de Linha de Comando

```bash
./ns3 run "rslaq-sim [opções]"
```

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `--scenario` | `normal` | Nome ou número (1-5) do cenário |
| `--simTime` | `4.0` | Tempo total de simulação (s) |
| `--appStart` | `0.4` | Tempo de início das aplicações (s) |
| `--seed` | `1` | Semente do RNG |
| `--outputDir` | `.` | Diretório de saída dos CSVs |
| `--periodMs` | `10` | Período de coleta de estatísticas (ms) |
| `--tddPattern` | `D\|D\|D\|D\|D\|D\|D\|D\|D\|D` | Padrão TDD |
| `--txPower` | `43.0` | Potência TX da gNB (dBm) |
| `--embbUes` | `5` | Número de UEs eMBB |
| `--urllcUes` | `5` | Número de UEs URLLC |
| `--mtcUes` | `10` | Número de UEs MTC |
| `--weights` | `0.3333,0.4000,0.2667` | Pesos das slices (eMBB,URLLC,MTC) |

---

## 5. Métricas e Saídas

### 5.1 Arquivos CSV Gerados

#### `rslaq_slice_allocations.csv`

Registra a alocação de RBG por slice a cada slot de scheduling.

```csv
timeMs,sliceId,configuredWeight,effectiveWeight,activeUes,budgetRbg,allocatedRbg,rntis
402,0,0.3333,0.4545,1,24,24,"1"
402,1,0.4000,0.5455,1,29,29,"2"
402,2,0.2667,0.0000,0,0,0,""
```

**Interpretação:**
- `timeMs = 402`: alocação ocorrida em t = 402 ms.
- `sliceId = 0` (eMBB): peso configurado 0.3333, efetivo 0.4545 (porque MTC estava vazia), 1 UE ativo, budget 24 RBGs, alocou 24.
- `sliceId = 2` (MTC): 0 UEs ativos, budget 0.

#### `rslaq_unmapped_rntis.csv`

Lista RNTIs que o scheduler viu mas não encontrou em nenhuma slice.

```csv
timeMs,rnti,reason
```

> Se este arquivo estiver **vazio**, todos os RNTIs foram corretamente mapeados.

#### `rslaq_stats_timeseries.csv`

Série temporal de throughput por UE a cada `periodMs`.

```csv
timestamp_ms,ue_id,slice,thr_mbps,btx,bfs_pct,tdp,rsh_pct
```

#### `rslaq_<scenario>_ue.csv`

Resumo final por UE.

```csv
ue_id,slice,tx_bytes,rx_bytes,tx_packets,rx_packets,lost_packets,throughput_mbps,avg_delay_ms,pdr
```

#### `rslaq_<scenario>_slice.csv`

Resumo final agregado por slice.

```csv
slice,tx_bytes,rx_bytes,tx_packets,rx_packets,lost_packets,throughput_mbps,avg_delay_ms,pdr
```

### 5.2 Logs do ns-3

Para ver os logs detalhados do scheduler:

```bash
NS_LOG="RslaqMacScheduler=level_debug" ./ns3 run "rslaq-sim ..."
```

Logs importantes:
- `[RslaqScheduler] Active RNTIs seen: ...` — todos os RNTIs no slot.
- `[RslaqScheduler] Active UEs per slice: ...` — contagem por slice.
- `[RslaqScheduler] RBG budgets: ...` — pesos originais, efetivos e budgets.
- `[RslaqScheduler] Slice X: allocated Y/Z RBGs for W UEs` — resultado da alocação.
- `[RslaqScheduler] RNTI X not found in any slice!` — alerta de mapeamento ausente.

---

## 6. Testes de Validação

### 6.1 Teste A — Sanity Check (1 UE por slice)

**Objetivo:** Verificar que todas as slices recebem recursos.

```bash
./ns3 run "rslaq-sim --embbUes=1 --urllcUes=1 --mtcUes=1 --weights=0.33,0.33,0.34 --scenario=normal --simTime=1.0"
```

**Critérios de aceite:**
- `rslaq_slice_allocations.csv` mostra alocação para slices 0, 1 e 2.
- `rslaq_unmapped_rntis.csv` está vazio.
- Throughput de MTC > 0 Mbps.
- RX packets de MTC > 0.

### 6.2 Teste B — 20 UEs com Pesos do Artigo

**Objetivo:** Validar comportamento em carga alta.

```bash
./ns3 run "rslaq-sim --embbUes=5 --urllcUes=5 --mtcUes=10 --weights=0.3333,0.4000,0.2667 --scenario=congestion --simTime=4.0"
```

**Critérios de aceite:**
- Todas as slices recebem alocação > 0 quando há demanda.
- eMBB tem throughput saturado (limitado pelo canal).
- URLLC mantém baixa latência (< 10 ms).
- MTC recebe pacotes RX.

### 6.3 Teste C — Slice sem Tráfego

**Objetivo:** Validar redistribuição de budget.

```bash
./ns3 run "rslaq-sim --embbUes=5 --urllcUes=5 --mtcUes=0 --weights=0.3333,0.4000,0.2667 --scenario=congestion --simTime=2.0"
```

**Critérios de aceite:**
- `effectiveWeight` de MTC (sliceId=2) é 0.0 no CSV.
- `budgetRbg` de MTC é 0.
- Budget de MTC é redistribuído proporcionalmente entre eMBB e URLLC.
- eMBB e URLLC continuam recebendo alocação.

---

## 7. Como Compilar

### 7.1 Pré-requisitos

- ns-3-dev (versão compatível com 5G-LENA)
- Módulo `nr` (5G-LENA) em `contrib/nr`
- Compilador C++17 (GCC 9+ ou Clang 10+)
- CMake 3.16+

### 7.2 Clonar o 5G-LENA

Se o diretório `contrib/nr` estiver vazio:

```bash
cd ns-3-dev
git clone https://gitlab.com/cttc-lena/nr.git contrib/nr
```

### 7.3 Configurar e Compilar

```bash
cd ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 build rslaq-sim
```

> **Dica:** A primeira compilação pode levar 10-20 minutos dependendo do hardware. Compilações subsequentes são incrementais.

---

## 8. Limitações Conhecidas

1. **Sem DRL/DDQL:** Os pesos `p_j` são fixos nesta fase. O agente DRL será integrado futuramente para ajustar `p_j` dinamicamente a cada frame (10 ms).

2. **Uplink não slice-aware:** As correções aplicam-se apenas ao downlink (`AssignDLRBG`). O uplink usa a lógica herdada do `NrMacSchedulerOfdmaRR` sem particionamento por slice.

3. **Representação PF única:** `CreateUeRepresentation()` sempre retorna `NrMacSchedulerUeInfoPF`. Isso é funcional para RR e BCQI, mas não é semanticamente puro.

4. **Fallback desabilitado por padrão:** UEs não mapeados são descartados com log. Para forçá-los na slice 0, habilite o atributo:
   ```bash
   ./ns3 run "rslaq-sim --ns3::RslaqMacScheduler::FallbackUnmappedUe=true ..."
   ```

5. **Mapeamento agendado:** Slots anteriores a `mappingTime` (~0.1 s) podem não ter UEs mapeados, mas como o tráfego só começa em `appStartSec = 0.4 s`, isso não afeta os resultados.

6. **Single gNB:** A topologia atual suporta apenas 1 gNB. Múltiplas gNBs podem exigir adaptações no mapeamento RNTI (RNTIs podem se repetir entre células, mas são únicos por MAC).

---

## 9. Glossário

| Termo | Significado |
|-------|-------------|
| **RBG** | Resource Block Group — grupo de PRBs alocados juntos pelo scheduler. |
| **PRB** | Physical Resource Block — unidade mínima de recurso no domínio frequência-tempo. |
| **Slice** | Partição lógica da RAN (eMBB, URLLC, MTC). |
| **RNTI** | Radio Network Temporary Identifier — identificador temporário de UE na célula. |
| **PF** | Proportional Fair — algoritmo de scheduling que balanceia throughput e justiça. |
| **BCQI** | Best CQI (Channel Quality Indicator) — scheduling greedy por melhor canal. |
| **RR** | Round Robin — scheduling cíclico. |
| **ω (omega)** | Peso/prioridade da política de slice (input do agente/operador). |
| **p_j** | Proporção final de recursos aplicada ao scheduler (nesta fase, `p_j = ω`). |
| **BWP** | Bandwidth Part — parte da banda total alocada a um UE. |
| **SCS** | Subcarrier Spacing — espaçamento entre subportadoras (15 kHz para μ=0). |

---

## 10. Referências

1. Artigo RSLAQ: *"A Robust SLA-driven 6G O-RAN QoS xApp using deep reinforcement learning"*
2. CTTC 5G-LENA: https://gitlab.com/cttc-lena/nr
3. ns-3: https://www.nsnam.org/

---

**Fim da Documentação**
