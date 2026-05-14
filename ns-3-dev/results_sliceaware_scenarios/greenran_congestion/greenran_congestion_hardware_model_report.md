# GreenRAN Hardware Model Report

## Hardware modelado

- Radio: Benetel RAN650 n78
- Antena: Alpha Wireless AW3161-E-F-V2
- Perfil: ran650_aw3161_outdoor
- Deployment: umi / UMi

## Parametros implementados literalmente

- Faixa RF 3.3-3.8 GHz para n78.
- Bandwidth instantaneo maximo de 100 MHz.
- SCS 30 kHz / numerologia 1.
- RAN650 4T4R, 37 dBm por porta, potencia agregada calculada 43.02 dBm.
- Receiver noise figure 4.00 dB.
- IP rating IP65 e consumo tipico 100.00 W.
- AW3161 com 4 portas, ganho 17.40 dBi, beamwidth 65.00/7.00 graus, downtilt 6.00 graus, polarizacao +/-45 slant linear.

## Aproximacoes

- O padrao de radiacao medido da AW3161 nao e carregado; sem arquivo real de pattern, beamwidth, front-to-back e XPD sao metadados rastreaveis.
- As 4 portas foram aproximadas como matriz gNB 2x2 no 5G-LENA, nao como 4x4/16 elementos.
- O calculo de EIRP (54.40 dBm) e informativo; nao foi somado manualmente ao TxPower.
- O-RAN split 7.2x e documentado, mas latencia/jitter reais de fronthaul nao sao modelados.
- O slicing e aproximado por trafego de aplicacao, QoS Flow/5QI dedicado no 5G-LENA e enforcement RAN/MAC-side por UE/RNTI.

## Slice do projeto UFPA

- App1-Vigilancia: VIDEO_EMBB, video 4K/H.265 campus UFPA, 5QI 80, SLA DL 0.61 Mbps agregado e delay < 100.00 ms.
- App2-Monitoramento: SENSOR_MMTC, sensores ambientais/solo, 5QI 70, trafego UL esporadico e foco em PDR/congestionamento/uso eficiente de PRBs.
- App3-Usuarios: GENERIC_EMBB, streaming + VoIP, 5QI 8 (streaming) + 5QI 1 (VoIP), SLA DL 54.00 Mbps agregado e delay < 150.00 ms.
- DRL/POSIX: semaforos POSIX ficam habilitados por padrao quando `enablePosixSync=true`; o controle de pesos de PRB usa `rslaq_actions_for_ns3.csv` no formato `timestamp,sliceId,dedicatedPRB,minPRB,maxPRB` e leitura nao bloqueante com `sem_trywait`.
- Resultados de PRB e buffer MAC sao exportados em `*_slice_alloc*.csv`, `*_ue_detail*.csv`, `rslaq-kpms.txt` e `greenran_mac_buffer_congestion.csv`.

## Alertas

- Frequencia fora de 3.3-3.8 GHz, bandwidth acima de 100 MHz ou numerologia diferente de 1 abortam por padrao.
- `allowOutOfDatasheetConfig=true` troca abort por warning forte para estudos experimentais.
- `ran650PowerMode=aggregate` pode superestimar cobertura dependendo da semantica de TxPower do 5G-LENA.
- Se `forceIsotropicAntenna=true`, o relatorio nao deve ser interpretado como setor AW3161 fisico.
- Resultados antigos nao sao diretamente comparaveis quando o perfil de hardware/canal muda.

Este cenario representa uma aproximacao de uma instalacao outdoor com RAN650 n78 + antena painel AW3161. Ele nao representa network slicing end-to-end completo nem o padrao de radiacao medido da antena, salvo se forem fornecidos e carregados arquivos reais de pattern.
