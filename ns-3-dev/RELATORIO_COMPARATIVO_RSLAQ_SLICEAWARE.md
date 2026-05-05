# Relatório de Análise Comparativa: RSLAQ vs SliceAware

## 1. Resumo Executivo

A análise dos resultados de simulação revela uma **diferença fundamental nas configurações de rádio** entre os dois algoritmos (RSLAQ e SliceAware), o que **inviabiliza qualquer comparação direta de performance** entre eles na forma atual.

**Conclusão principal:** Os resultados não refletem uma comparação justa entre algoritmos de scheduling, mas sim entre **duas configurações de rede 5G com capacidades radicalmente diferentes**.

---

## 2. Configurações de Rádio Comparadas

| Parâmetro | RSLAQ (`rslaq-sim.cc`) | SliceAware (`slice-aware-sim.cc`) | Impacto |
|---|---|---|---|
| **Frequência** | 2.59 GHz (n38) | 3.55 GHz (n78) | Diferente banda |
| **Largura de Banda** | **10 MHz** | **100 MHz** | **10x menor capacidade** |
| **Numerologia (μ)** | 0 (SCS 15 kHz) | 1 (SCS 30 kHz) | Diferente estrutura de slot |
| **Antena gNB** | 1x1 (isotrópica) | 2x2 (isotrópica) | **4x menos capacidade MIMO** |
| **Potência TX** | 43 dBm | 43 dBm | Igual |
| **Cenários** | low_traffic, normal, congestion, stressed, insufficient_resources | Idem | Igual |

### Impacto Teórico na Capacidade

- **Largura de banda**: 10 MHz vs 100 MHz → ~10x menos PRBs/RBGs disponíveis
- **MIMO**: 1x1 vs 2x2 → ~2-4x menos throughput por PRB
- **Capacidade total estimada**: O RSLAQ opera com aproximadamente **20-40x menos capacidade bruta** que o SliceAware

---

## 3. Análise de Métricas por Cenário

### 3.1 Cenário NORMAL

| Métrica | RSLAQ | SliceAware | Diferença |
|---|---|---|---|
| **eMBB Throughput** | 21.52 Mbps | 71.28 Mbps | RSLAQ 3.3x menor |
| **eMBB Delay** | **3355.96 ms** | **2.87 ms** | RSLAQ 1169x maior |
| **eMBB PDR** | **0.30** | **0.9997** | RSLAQ perde 70% dos pacotes |
| **URLLC Throughput** | 1.56 Mbps | 1.56 Mbps | Equivalente |
| **URLLC Delay** | 5.01 ms | 3.05 ms | RSLAQ 64% maior |
| **URLLC PDR** | 0.9996 | 0.9998 | Equivalente |
| **MTC Throughput** | 2.56 Mbps | 2.56 Mbps | Equivalente |
| **MTC Delay** | 5.51 ms | 3.05 ms | RSLAQ 81% maior |
| **MTC PDR** | 0.9996 | 1.0000 | Equivalente |

**Análise:**
- A capacidade do eMBB no RSLAQ (10 MHz) é insuficiente para a taxa oferecida de 70 Mbps (14 Mbps/UE)
- O delay de ~3.4s indica buffer overflow e descarte de pacotes por timeout
- URLLC e MTC têm demanda baixa (1-2 Mbps) e são atendidos adequadamente

### 3.2 Cenários de Carga Alta (Congestion, Stressed, Insufficient Resources)

| Cenário | Métrica | RSLAQ | SliceAware |
|---|---|---|---|
| **Congestion** | eMBB Throughput | 16.00 Mbps | 101.83 Mbps |
| | eMBB Delay | 4050.69 ms | 2.88 ms |
| | eMBB PDR | 0.157 | 0.9997 |
| | MTC Throughput | 12.85 Mbps | 127.96 Mbps |
| | MTC Delay | 4321.89 ms | 2.88 ms |
| | MTC PDR | 0.100 | 0.9997 |
| **Stressed** | eMBB Throughput | 16.05 Mbps | 101.83 Mbps |
| | MTC Throughput | 12.89 Mbps | 127.96 Mbps |
| **Insufficient Resources** | eMBB Throughput | 11.75 Mbps | 101.83 Mbps |
| | MTC Throughput | 9.74 Mbps | 127.96 Mbps |

**Análise:**
- Em cenários de carga alta, o RSLAQ atinge **colapso total** do eMBB e MTC
- PDR cai para ~10-15%, delay explode para >4 segundos
- O SliceAware (100 MHz) absorve a carga sem degradação perceptível

### 3.3 Cenário LOW_TRAFFIC

| Métrica | RSLAQ | SliceAware | Diferença |
|---|---|---|---|
| eMBB Throughput | 5.09 Mbps | 5.09 Mbps | Equivalente |
| eMBB Delay | 8.02 ms | 3.17 ms | RSLAQ 2.5x maior |
| eMBB PDR | 1.0000 | 1.0000 | Equivalente |

**Análise:**
- Com baixa carga (5 Mbps eMBB), ambos atendem a demanda
- O delay maior no RSLAQ reflete a menor eficiência espectral (1x1 vs 2x2)

---

## 4. Diagnóstico do Scheduler RSLAQ

### 4.1 Alocação de Recursos (RBG)

A análise dos logs de alocação (`slice_alloc.csv`) mostra que o **scheduler RSLAQ está funcionando corretamente**:

| Cenário | Slice | Total Budget RBG | Total Allocated RBG | Taxa de Uso |
|---|---|---|---|---|
| Normal | eMBB | 3058 | 3058 | 100% |
| | URLLC | 1229 | 1229 | 100% |
| | MTC | 960 | 960 | 100% |
| Congestion | eMBB | 2283 | 2283 | 100% |
| | URLLC | 1029 | 1029 | 100% |
| | MTC | 1935 | 1935 | 100% |

**Conclusão:** O scheduler aloca 100% dos recursos disponíveis. O problema não é no algoritmo de scheduling, mas na **capacidade física insuficiente** para a demanda oferecida.

### 4.2 Verificação de Consistência

O script `analyze_rslaq_results.py` confirmou:
- ✅ Zero erros de consistência nos dados
- ✅ Todos os RNTIs mapeados corretamente
- ✅ Agregação UE → Slice consistente
- ✅ Alocação RBG cobre todos os UEs com RX > 0

---

## 5. Causa Raiz

A diferença de performance não é causada pelo algoritmo RSLAQ em si (que usa o mesmo código do SliceAware em `AssignDLRBG`), mas por:

1. **Configuração de rádio inadequada para a demanda**: 10 MHz + 1x1 MIMO não suporta 70 Mbps de eMBB com 5 UEs
2. **Ausência de comparação justa**: Para comparar RSLAQ vs SliceAware, ambos devem usar a mesma configuração de rádio (preferencialmente 100 MHz / 2x2)
3. **RSLAQ rodando em modo standalone**: Sem o agente DRL ativo, o RSLAQ usa pesos estáticos que não otimizam a alocação dinâmica

---

## 6. Recomendações

### 6.1 Para uma Comparação Justa (Imediato)

1. **Uniformizar a configuração de rádio**: Alterar `rslaq-sim.cc` para usar os mesmos parâmetros do `slice-aware-sim.cc`:
   ```cpp
   double centralFrequency = 3.55e9;  // 3.55 GHz
   double bandwidth = 100e6;          // 100 MHz
   uint16_t numerology = 1;           // SCS 30 kHz
   // gNB Antenna: 2x2
   ```

2. **Regenerar os resultados do RSLAQ** com a configuração acima

3. **Comparar novamente** usando o mesmo script Python (`compare_results.py`)

### 6.2 Para Validação do Algoritmo RSLAQ (Completo)

1. **Executar com o agente DRL ativo**: O RSLAQ foi projetado para operar com o ns-o-ran-gym fornecendo ações via IPC (`rslaq_actions_for_ns3.csv`). Executar em modo standalone não avalia o benefício do DRL.

2. **Comparar três cenários**:
   - **Baseline estático**: SliceAware com pesos fixos (33%, 40%, 27%)
   - **RSLAQ sem DRL**: Mesma configuração, pesos estáticos
   - **RSLAQ com DRL**: Agente treinado ajustando pesos dinamicamente

3. **Usar métricas de fairness e QoS**:
   - Jain's fairness index entre slices
   - Taxa de violação de SLA (delay < 10ms para URLLC, throughput > X para eMBB)
   - Eficiência espectral (bits/s/Hz)

### 6.3 Correção de Bug Potencial

Revisar o comentário em `rslaq-sim.cc` (linha 582-583):
```cpp
// P_STA decomposition is applied in Python (rslaq_action_spaces.py)
// The agent sends dedicatedPRB as % of total, already including P_STA.
```

Se o RSLAQ for executado **sem** o agente Python (modo standalone), a decomposição `P_STA + p_opt * 0.5` **nunca é aplicada**, pois não há arquivo `rslaq_actions_for_ns3.csv`. Isso significa que em standalone o RSLAQ opera apenas com pesos estáticos, o que é válido para baseline, mas não demonstra a vantagem do DRL.

---

## 7. Conclusão

| Aspecto | Avaliação |
|---|---|
| **Qualidade dos dados** | ✅ Consistentes e completos |
| **Funcionamento do scheduler** | ✅ Aloca 100% dos recursos disponíveis |
| **Comparabilidade** | ❌ **Inviável** devido a configurações de rádio diferentes |
| **RSLAQ como baseline** | ⚠️ Funciona, mas com capacidade 10-20x menor |
| **Próximo passo** | 🔄 Uniformizar configuração de rádio e regenerar resultados |

**O RSLAQ não está "quebrado"** — ele está operando corretamente dentro dos limites de uma configuração de 10 MHz / 1x1 MIMO. A comparação atual é equivalente a comparar o desempenho de um carro em uma estrada de 1 pista contra o mesmo carro em uma autoestrada de 10 pistas.

---

*Relatório gerado em: 2026-05-05*
*Ferramentas: Python 3, pandas, análise manual de código-fonte ns-3*
