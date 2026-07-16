# Plano: Testar DRLs treinadas em cenários controlados (throughput + SLA)

## Contexto confirmado
- **Modelos a testar**: DDQN online (9 completos: low_traffic, normal, stressed) + modelos offline (DDQN/SAC/PPO, precisam de wrapper para o formato de estado do ns-3).
- **Ferramenta**: `examples/rslaq_eval_policy.py` existente — carrega modelo `.pt`, roda num cenário controlado do ns-3, coleta throughput/PDR/outages/reward por step em CSV. Inclui 4 baselines fixos automaticamente.
- **Métricas disponíveis por step**: throughput por slice, PDR, outages, soft_violations, reward, ações (pesos) escolhidas pela política.

## Etapa 1 — Avaliar DDQN online (9 modelos completos)

Usar o `rslaq_eval_policy.py` direto (sem código novo). Para cada um dos 9 cenários×seeds completos, rodar 3 episodes de avaliação:

```bash
cd /home/elioth/Documentos/artigo_jussi/ns-o-ran-gym
for sc in low_traffic normal stressed; do
  for sd in 1 2 3; do
    CKPT="results_controlled/.../rslaq_ddqn_paper/ddqn_paper_${sc}_seed${sd}/ddqn_final.pt"
    python3 examples/rslaq_eval_policy.py \
      --algo ddqn --checkpoint "$CKPT" \
      --scenario "$sc" --episodes 3 --eval_seeds "1,2,3" \
      --simTime 5.0 --appStart 0.4 --output "results/drl_eval/${sc}_seed${sd}"
  done
done
```

Cada execução gera:
- `eval_ddqn_${sc}_<run_id>.csv` (resumo por episódio: reward, outages, throughput final, ações)
- `<sim_uuid>/step_metrics.csv` (detalhe por step×slice: throughput, PDR, buffers, ações)
- `_summary.json` (metadados)

**Tempo estimado**: ~2-5 min por execução (3 episodes × ~100 steps × ns-3 online). Total ~30-45 min para os 9.

## Etapa 2 — Criar wrapper para modelos offline

Os modelos offline (DDQN/SAC/PPO treinados do Parquet) operam sobre **vetor de estado tabular (14 features)**, não a matriz 4×4 do ns-3. Para testá-los ao vivo, preciso de um wrapper que:

1. **Receba** a observação 4×4 do `RslaqEnv` (linhas: btx, bfs, rsh, tdp × colunas: eMBB, URLLC, MTC, cell)
2. **Converta** para o formato tabular esperado pelo modelo offline: extrair `num_ues_*`, `offered_load_*` do `metadata.json` do cenário, e `delay/buffer/pdr` da observação
3. **Rode** o modelo offline (ActorNet/QNet do `train_offline_rl.py`)
4. **Retorne** os pesos [eMBB, URLLC, MTC] como ação

Criar `examples/offline_drl_wrapper.py` que:
- Define uma classe `OfflineDRLAgent` que recebe (model_path, model_type, scenario_state)
- Implementa `act(observation_4x4) -> action_3` convertendo estado e rodando o modelo
- Pode ser passada para o loop de avaliação do `rslaq_eval_policy.py` (ou um loop customizado)

**Nota**: o estado tabular tem features que não estão na observação 4×4 (ex: `offered_load_*`, `num_ues_*`). Esses vêm do `metadata.json` do cenário (são constantes por cenário). O wrapper carrega isso no init e combina com a observação dinâmica (buffer, throughput) extraída da matriz 4×4.

## Etapa 3 — Avaliar modelos offline no ns-3

Criar `examples/eval_offline_in_ns3.py` que:
1. Para cada modelo offline (DDQN, SAC, PPO) e cada cenário (low_traffic, normal, stressed, congestion):
2. Instancia o `RslaqEnv` com `action_mode="continuous"` (pesos contínuos), `observation_mode="paper"`
3. Instancia o `OfflineDRLAgent` (wrapper da Etapa 2)
4. Roda 3 episodes: `obs = env.reset()` → `action = agent.act(obs)` → `env.step(action)` → coleta info
5. Registra throughput, PDR, SLA, reward por step em CSV

**Output**: `results/offline_drl_eval/{model}_{scenario}/step_metrics.csv` + resumo.

**Limitação honesta**: os modelos offline foram treinados com score F(w) do scoring.py, mas o ns-3 reporta via reward do rslaq_reward.py (função diferente). O wrapper só usa o modelo para PREVER os pesos; o reward do ns-3 é apenas observado, não usado para treinar.

## Etapa 4 — Agregar e comparar resultados

Criar `examples/summarize_drl_eval.py` que:
1. Lê todos os `step_metrics.csv` e `eval_*.csv` gerados
2. Agrega por (modelo, cenário): throughput médio por slice, PDR, outages, reward médio
3. Compara: DDQN online vs DDQN offline vs SAC offline vs PPO offline vs baselines fixos
4. Gera tabela CSV + figura (barras agrupadas por cenário)

**Output**: `results/drl_eval/comparison_summary.csv` + `figuras_overleaf/fig18_drl_eval_comparison.png`

## Estrutura de arquivos criados
```
examples/
  offline_drl_wrapper.py        # Etapa 2 (wrapper offline → ns-3)
  eval_offline_in_ns3.py        # Etapa 3 (loop de avaliação offline)
  summarize_drl_eval.py         # Etapa 4 (agregação)

results/
  drl_eval/                     # Etapa 1 output (DDQN online)
    low_traffic_seed1/
    normal_seed1/
    stressed_seed1/
    ...
  offline_drl_eval/             # Etapa 3 output (offline)
    ddqn_congestion/
    sac_normal/
    ...
  drl_eval/comparison_summary.csv  # Etapa 4
```

## Ordem de execução
1. **Etapa 1** primeiro (DDQN online — usa script existente, resultado garantido)
2. **Etapa 2** (wrapper — código novo, ~50 linhas)
3. **Etapa 3** (offline eval — depende do wrapper)
4. **Etapa 4** (agregação — depende de 1+3)

## Riscos
- **Offline wrapper**: a conversão de estado 4×4 → tabular pode perder informação (o modelo offline espera features que não estão na obs do ns-3). Mitigação: usar o metadata.json do cenário para as features estáticas.
- **Reward mismatch**: o reward do ns-3 (rslaq_reward.py) é diferente do score F(w) usado no treino offline. Os pesos previstos podem não ser ótimos para o reward do ns-3. Isso é esperado e reportável.
- **Tempo**: cada avaliação online roda ns-3 por ~5s × 3 episodes. Congestion é mais lento. Total ~1-2h para tudo.