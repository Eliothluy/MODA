# Relatório de Investigação Técnica - RSLAQ Scheduler

**Data:** 24/04/2026  
**Analista:** Engenharia de Dados 5G  
**Objetivo:** Analisar resultados de simulação e diagnosticar funcionamento do scheduler slice-aware

---

## 1. Sumário Executivo

A investigação revelou **falhas críticas** no scheduler slice-aware que impedem distribuição real de recursos PRB entre slices. O throughput zero em MTC não é uma falha de rede, mas sim um **bug de implementação**.

| Aspecto | Status | Severidade |
|--------|--------|----------|
| Distribuição PRB por slice | ❌ Não funciona | CRÍTICA |
| Throughput MTC | 0 Mbps | CRÍTICA |
| Throughput URLLC | Parcial (~0.3 Mbps) | ALTA |
| Throughput eMBB | Limitado (~17.5 Mbps) | MÉDIA |
| Diferenciação de cenários | ❌ Não funciona | ALTA |

---

## 2. Evidências Coletadas

### 2.1 Resultados por Slice (todos os cenários)

| Slice | Weight Configurado | Throughput Real | RX Packets | TX Packets | PDR |
|-------|-----------------|-----------------|-----------|-----------|-----|
| eMBB | 40% | ~17.5 Mbps | ~13,700 | ~67,000-96,000 | 14-20% |
| URLLC | 20% | 0-0.62 Mbps | ~4,800-9,600 | ~28,800-57,600 | 17% |
| MTC | 40% | **0 Mbps** | **0** | ~26,000-1,319,000 | **0%** |

### 2.2 Logs de Alocação do Scheduler

```
Slice 0 RNTIs: 1 2 3 4 5    (eMBB)
Slice 1 RNTIs: 6 7 8 9 10   (URLLC)
Slice 2 RNTIs: 11 12 13 14 15 16 17 18 19 20  (MTC)

Slice 1: allocated 10/10 RBGs for 1 UEs   ← APENAS URLLC!
Slice 1: allocated 3/10 RBGs for 1 UEs
...
```

**Observação:** Apenas logs de alocação para Slice 1 (URLLC) aparecem. Nunca há logs para Slice 0 (eMBB) ou Slice 2 (MTC).

### 2.3 Taxas de Tráfego Oferecidas vs Entregues

| Cenário | eMBB Offered | eMBB Delivered | URLLC Offered | URLLC Delivered |
|--------|-------------|--------------|--------------|--------------|
| low_traffic | 50 Kbps | 0.05 Mbps | 1 Mbps | 0.31 Mbps |
| normal | 70 Mbps | 17.5 Mbps | 1 Mbps | 0.31 Mbps |
| congestion | 100 Mbps | 17.5 Mbps | 1 Mbps | 0 Mbps |
| stressed | 100 Mbps | 17.5 Mbps | 1 Mbps | 0.31 Mbps |
| insufficient | 100 Mbps | 17.5 Mbps | 2 Mbps | 0.62 Mbps |

**Conclusão:** Não há diferenciação significativa entre cenários.

---

## 3. Análise da Causa Raiz

### 3.1 Fluxo de Alocação no RslaqMacScheduler

O código em `rslaq-mac-scheduler.cc` linha 212-219:

```cpp
std::vector<std::vector<UePtrAndBufferReq>> sliceUeVec(m_numSlices);
for (const auto& ue : GetUeVector(el))
{
    int32_t sIdx = GetSliceIndexForRnti(ue.first->m_rnti);
    if (sIdx >= 0)
    {
        sliceUeVec[static_cast<uint32_t>(sIdx)].emplace_back(ue);
    }
}
```

O scheduler:
1. Itera sobre todos os UEs ativos
2. Para cada UE, busca o slice via `GetSliceIndexForRnti()`
3. Se o RNTI não está no mapeamento → **ignora completamente**

### 3.2 Cálculo do Budget de RBG

O cálculo do budget (linhas 229-242):

```cpp
std::vector<uint32_t> sliceRbgBudget(m_numSlices, 0);
uint32_t allocatedSoFar = 0;
for (uint32_t s = 0; s < m_numSlices; s++)
{
    if (s == m_numSlices - 1)
    {
        sliceRbgBudget[s] = totalRbgs - allocatedSoFar;
    }
    else
    {
        sliceRbgBudget[s] = static_cast<uint32_t>(totalRbgs * m_prbWeights[s]);
        allocatedSoFar += sliceRbgBudget[s];
    }
}
```

**Problema identificado:**
- O budget é calculado baseado em `totalRbgs * weight`
- Mas se não há UEs ativos para um slice → slice é pulado
- O último slice (MTC) deveria receber recursos restantes, mas não receives

### 3.3 Possíveis Causas

1. **RNTIs não batendo:** Os RNTIs usados pelo 5G-LENA podem ser diferentes dos configurados
2. **Mapeamento não aplicado corretamente:** O `SetSliceUeMapping` pode não ser chamado no momento certo
3. **Problema de timing:** RNTIs atribuídos após Attach podem não corresponder aos configurados
4. **Bug no loop de alocação:** A lógica pode estar excluindo slices inteiros

---

## 4. Métricas Ausentes

Os CSVs não contêm:
- `lost_packets` (sempre 0, mesmo com rx=0)
- Utilização real de PRBs por slice
- Buffer occupancy no/gNB
- Queue delays por bearer
- RLC丢包率

---

## 5. Recomendações de Correção

### 5.1 Verificações Imediatas

1. **Adicionar logging de RNTIs ativos:**
   - Loggear todos os RNTIs recibidos em cada slot
   - Verificar se estão no mapeamento

2. **Validar o mapeamento:**
   - Comparar RNTIs do 5G-LENA vs configurados
   - Adicionar método de debug para dump do mapeamento

3. **Testar com casos simples:**
   - 1 UE por slice (isolado)
   - Verificar se alocação funciona

### 5.2 Correções de Código

1. **Adicionar trace de alocação por slice:**
```cpp
for (uint32_t s = 0; s < m_numSlices; s++)
{
    NS_LOG_INFO("Slice " << s << ": " << sliceUeVec[s].size()
              << " UEs, budget=" << sliceRbgBudget[s]
              << " RBGs, allocated=" << sliceAllocated);
}
```

2. **Verificar se UEs estão no mapeamento:**
```cpp
int32_t sIdx = GetSliceIndexForRnti(ue.first->m_rnti);
NS_LOG_WARN("RNTI " << ue.first->m_rnti << " not found in any slice!");
```

3. **Fallback para UEs não mapeados:**
```cpp
if (sIdx < 0) {
    // Assign to default slice or log error
    NS_LOG_WARN("RNTI " << ue.first->m_rnti << " not mapped, using default");
    sliceUeVec[0].emplace_back(ue);  // Default to eMBB
}
```

### 5.3 Métricas a Adicionar

1. **Lost packets real:**
   - Calcular Tx - Rx (não usar FlowMonitor lost)
   - Adicionar contador no RLC

2. **PRB real usado por slice:**
   - Accumular contadores no `AssignedDlResources`
   - Expor via Attribute/Trace

---

## 6. Veredicto Final

| Claim | Evidência | Suportado? |
|-------|----------|-----------|
| Scheduler distribui PRB por slice | Apenas URLLC alocado | ❌ NÃO |
| MTC recebe recursos | Rx = 0 | ❌ NÃO |
| eMBB atinge taxa configurada | Limitado a ~17.5 Mbps | ⚠️ PARCIAL |
| Cenários são diferenciados | Resultados similares | ❌ NÃO |
| URLLC tem baixa latência | Delay ~5ms (baixo) | ✅ SIM |

### Recomendação:

**REJEITAR os resultados atuais** como evidência de network slicing. O sistema apresenta falha de implementação, não comportamento de rede 5G com slicing.

---

## 7. Próximos Passos

1. [ ] Corrigir bug de mapeamento RNTI → Slice
2. [ ] Adicionar logging de alocação por slice
3. [ ] Testar com 1 UE por slice
4. [ ] Validar PRB real distribuído
5. [ ] Re-rodar simulações
6. [ ] Gerar novos CSVs com métricas corretas

---

**Fim do Relatório**