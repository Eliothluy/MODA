# Changelog

## Validacao RSLAQ/ns-3

- Aplicada correcao autorizada no IPC do ns-3 para consumir `algorithm` e aplicar RR/PF/BCQI na acao DDQN.
- Adicionado logging por step (`step_metrics.csv`) no `RslaqEnv`.
- Adicionados parametros de P_STA e pesos de reward aos scripts DDQN/SAC/eval.
- Corrigida avaliacao DDQN para usar 198 acoes quando scheduler esta habilitado.
- Criado script de campanha controlada multi-seed com mesmo orcamento DDQN/SAC.
- Criada pasta `analysis_rslaq_validation/`.
- Geradas tabelas de resumo, outage, reliability e auditoria low_traffic a partir de resultados existentes.
- Geradas figuras estilo artigo em PNG/PDF.
- Gerado relatorio cientifico final.
