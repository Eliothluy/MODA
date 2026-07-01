/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * RSLAQ Simulation — ns-3 / 5G-LENA com IPC para ns-o-ran-gym
 *
 * Protótipo de scheduler slice-aware com controle DRL via semáforos POSIX
 * e troca de arquivos CSV (rslaq-kpms.txt, rslaq_actions_for_ns3.csv).
 *
 * Topologia 5G usada no experimento:
 *   remoteHost -- P2P 100 Gbps -- PGW/EPC -- gNB NR -- UEs NR
 *
 * - 1 gNB em posição fixa no centro da célula.
 * - N UEs estáticos distribuídos uniformemente em disco ao redor do gNB.
 * - Três slices lógicos por faixa de UE ID: eMBB, URLLC e MTC.
 * - Tráfego sempre downlink: remoteHost envia UDP/OnOff para cada UE.
 * - Uma porta UDP por UE permite mapear FlowMonitor -> UE -> slice.
 * - PHY default: RAN650 n78 + AW3161 outdoor panel, 3.55 GHz, 100 MHz,
 *   numerologia mu=1 (SCS 30 kHz), canal 3GPP UMi.
 *
 * Modos de execução:
 * - standalone/baseline: gera timeseries.csv, slice_alloc.csv, summary.csv.
 * - IPC com Python: a cada periodMs escreve rslaq-kpms.txt, sinaliza o Gym,
 *   lê rslaq_actions_for_ns3.csv e atualiza o RslaqMacScheduler.
 */

#include "rslaq-mac-scheduler.h"

#include "ns3/antenna-module.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/nr-module.h"
#include "ns3/nr-mac-scheduler-ofdma-mr.h"
#include "ns3/nr-mac-scheduler-ofdma-pf.h"
#include "ns3/nr-mac-scheduler-ofdma-rr.h"
#include "ns3/point-to-point-module.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cctype>
#include <ctime>
#include <filesystem>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <semaphore.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("RslaqSim");

// ---------------------------------------------------------------------------
// Tipos e constantes (declarados ANTES das variáveis globais)
// ---------------------------------------------------------------------------

enum class SliceType : uint8_t
{
    EMBB = 0,
    URLLC = 1,
    MTC = 2
};

// ---------------------------------------------------------------------------
// Constantes IPC
// ---------------------------------------------------------------------------

static std::string g_simUuid;           // UUID passado via --simId
static sem_t* g_semMetricsReady = nullptr;
static sem_t* g_semControl = nullptr;
static Ptr<RslaqMacScheduler> g_schedulerPtr = nullptr;
static Ptr<FlowMonitor> g_monitorPtr = nullptr;
static Ptr<Ipv4FlowClassifier> g_classifierPtr = nullptr;
static std::map<uint16_t, uint16_t> g_portToUeId;
static std::map<uint16_t, SliceType> g_ueToSlice;
static std::map<uint16_t, uint16_t> g_ueIdToRnti;
static uint32_t g_indicationPeriodMs = 10;
static bool g_ipcEnabled = false;
static bool g_useSliceScheduler = true;
static const std::array<double, 3> SLA_MIN_MBPS = {50.0, 1.0, 1.0};

// Previous KPM values for delta calculation (IPC mode)
struct KpmPrevValues
{
    uint64_t txBytes = 0;
    uint64_t rxBytes = 0;
    uint32_t txPackets = 0;
    uint32_t rxPackets = 0;
    uint32_t lostPackets = 0;
};
static std::map<uint16_t, KpmPrevValues> g_kpmPrevValues;

// P_STA decomposition: 50% estático + 50% dinâmico do agente
static const std::vector<double> P_STA_WEIGHTS = {0.33, 0.40, 0.27};

static const uint32_t NUM_SLICES = 3;

static uint32_t g_numUeEmbb = 0;
static uint32_t g_numUeUrllc = 0;
static uint32_t g_numUeMtc = 0;

struct ScenarioConfig
{
    /** Nome e perfil de carga do cenário RSLAQ. */
    std::string name;
    /** Quantidade de UEs por slice; 0 no CLI usa estes valores do perfil. */
    uint32_t embbUes;
    uint32_t urllcUes;
    uint32_t mtcUes;
    /** Carga UDP downlink total por slice, dividida igualmente entre seus UEs. */
    uint64_t embbRateBps;
    uint64_t urllcRateBps;
    uint64_t mtcRateBps;
    /** Tamanho dos pacotes UDP por slice, refletindo diferentes perfis de serviço. */
    uint32_t embbPktSize;
    uint32_t urllcPktSize;
    uint32_t mtcPktSize;
};

/**
 * @brief Classifica um UE ID sequencial no slice RSLAQ correspondente.
 *
 * Os UEs sao criados em blocos contiguos: primeiro todos eMBB, depois URLLC,
 * depois MTC. Essa convencao e usada tanto para configurar o scheduler quanto
 * para agregar estatisticas do FlowMonitor por slice.
 */
static SliceType
GetSliceForUe(uint16_t ueId)
{
    if (ueId >= 1 && ueId <= g_numUeEmbb)
    {
        return SliceType::EMBB;
    }
    else if (ueId > g_numUeEmbb && ueId <= g_numUeEmbb + g_numUeUrllc)
    {
        return SliceType::URLLC;
    }
    else
    {
        return SliceType::MTC;
    }
}

static uint32_t
NumUesPerSlice(SliceType s)
{
    switch (s)
    {
    case SliceType::EMBB:
        return g_numUeEmbb;
    case SliceType::URLLC:
        return g_numUeUrllc;
    case SliceType::MTC:
        return g_numUeMtc;
    default:
        return 0;
    }
}

static std::string
SliceName(SliceType s)
{
    switch (s)
    {
    case SliceType::EMBB:
        return "eMBB";
    case SliceType::URLLC:
        return "URLLC";
    case SliceType::MTC:
        return "MTC";
    default:
        return "?";
    }
}

static uint64_t
RateForSlice(const ScenarioConfig& sc, SliceType s)
{
    switch (s)
    {
    case SliceType::EMBB:
        return sc.embbRateBps;
    case SliceType::URLLC:
        return sc.urllcRateBps;
    case SliceType::MTC:
        return sc.mtcRateBps;
    default:
        return 0;
    }
}

static uint32_t
PktSizeForSlice(const ScenarioConfig& sc, SliceType s)
{
    switch (s)
    {
    case SliceType::EMBB:
        return sc.embbPktSize;
    case SliceType::URLLC:
        return sc.urllcPktSize;
    case SliceType::MTC:
        return sc.mtcPktSize;
    default:
        return 1500;
    }
}

/**
 * @brief Define os cinco perfis de carga usados nos experimentos RSLAQ.
 *
 * Cada perfil fixa numero de UEs, taxa total por slice e tamanho de pacote.
 * O trafego por UE e calculado mais adiante como taxa_do_slice / num_ues_do_slice.
 */
static std::map<std::string, ScenarioConfig>
InitScenarios()
{
    std::map<std::string, ScenarioConfig> m;
    m["low_traffic"] = {"low_traffic", 2, 2, 6, 55000000, 1000000, 1000000, 1500, 50, 100};
    m["normal"] = {"normal", 5, 5, 10, 70000000, 1000000, 2000000, 1500, 50, 100};
    m["congestion"] = {"congestion", 15, 10, 35, 180000000, 5000000, 60000000, 1500, 100, 500};
    m["stressed"] = {"stressed", 8, 12, 20, 100000000, 3000000, 25000000, 1500, 100, 500};
    m["insufficient_resources"] = {"insufficient_resources", 20, 10, 40, 220000000, 5000000, 70000000, 1500, 100, 500};
    return m;
}

static std::vector<double>
ParseWeights(const std::string& str)
{
    std::vector<double> w;
    std::stringstream ss(str);
    std::string token;
    while (std::getline(ss, token, ','))
    {
        try
        {
            size_t parsed = 0;
            double value = std::stod(token, &parsed);
            if (parsed != token.size())
            {
                NS_FATAL_ERROR("Invalid --weights token: '" << token << "'");
            }
            w.push_back(value);
        }
        catch (const std::exception&)
        {
            NS_FATAL_ERROR("Invalid --weights token: '" << token << "'");
        }
    }
    return w;
}

static std::string
ToUpper(std::string s)
{
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return s;
}

static std::string
ToLower(std::string s)
{
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

static RslaqMacScheduler::IntraSliceAlgorithm
ParseIntraAlgo(const std::string& algo)
{
    std::string a = ToUpper(algo);
    if (a == "RR")
    {
        return RslaqMacScheduler::IntraSliceAlgorithm::RR;
    }
    if (a == "PF")
    {
        return RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    if (a == "BCQI" || a == "MAXCQI" || a == "MR")
    {
        return RslaqMacScheduler::IntraSliceAlgorithm::BCQI;
    }
    NS_FATAL_ERROR("Invalid intraAlgo: " << algo << " (valid: RR|PF|BCQI)");
}

static std::string
IntraAlgoName(RslaqMacScheduler::IntraSliceAlgorithm algo)
{
    switch (algo)
    {
    case RslaqMacScheduler::IntraSliceAlgorithm::RR:
        return "RR";
    case RslaqMacScheduler::IntraSliceAlgorithm::PF:
        return "PF";
    case RslaqMacScheduler::IntraSliceAlgorithm::BCQI:
        return "BCQI";
    }
    return "UNKNOWN";
}

static std::string
SliceWeightPolicyName(RslaqMacScheduler::SliceWeightPolicy policy)
{
    switch (policy)
    {
    case RslaqMacScheduler::SliceWeightPolicy::STATIC:
        return "static";
    case RslaqMacScheduler::SliceWeightPolicy::DEMAND_GREEDY:
        return "demand_greedy";
    case RslaqMacScheduler::SliceWeightPolicy::SLA_GREEDY:
        return "sla_greedy";
    case RslaqMacScheduler::SliceWeightPolicy::LEAST_WASTE:
        return "least_waste";
    case RslaqMacScheduler::SliceWeightPolicy::RANDOM_VINE:
        return "random_vine";
    case RslaqMacScheduler::SliceWeightPolicy::META_RISK_ELASTIC:
        return "meta_risk_elastic";
    case RslaqMacScheduler::SliceWeightPolicy::AQPS:
        return "aqps";
    }
    return "unknown";
}

static RslaqMacScheduler::IntraSliceAlgorithm
IntraAlgoFromActionId(int schedulerId)
{
    switch (schedulerId)
    {
    case 0:
        return RslaqMacScheduler::IntraSliceAlgorithm::RR;
    case 1:
        return RslaqMacScheduler::IntraSliceAlgorithm::PF;
    case 2:
        return RslaqMacScheduler::IntraSliceAlgorithm::BCQI;
    default:
        NS_LOG_WARN("[RslaqSim] Unknown action scheduler id " << schedulerId
                                                              << "; falling back to PF");
        return RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
}

/**
 * @brief Seleciona o scheduler nativo ou customizado conforme o baseline.
 *
 * Modos pure_* usam schedulers 5G-LENA nativos sem particionamento por slice.
 * Modos slice_* instalam RslaqMacScheduler, que separa RBGs por slice antes
 * de aplicar RR/PF/BCQI dentro de cada slice.
 */
static TypeId
NativeSchedulerForMode(const std::string& baselineMode)
{
    if (baselineMode == "pure_rr")
    {
        return NrMacSchedulerOfdmaRR::GetTypeId();
    }
    if (baselineMode == "pure_pf")
    {
        return NrMacSchedulerOfdmaPF::GetTypeId();
    }
    if (baselineMode == "pure_bcqi")
    {
        return NrMacSchedulerOfdmaMR::GetTypeId();
    }
    return RslaqMacScheduler::GetTypeId();
}

static bool
IsPureMode(const std::string& baselineMode)
{
    return baselineMode == "pure_rr" || baselineMode == "pure_pf" || baselineMode == "pure_bcqi";
}

/**
 * @brief Converte o baseline CLI em pesos de slice e algoritmo intra-slice.
 *
 * Retorna false para pure_rr/pure_pf/pure_bcqi, indicando que o scheduler
 * customizado nao deve ser usado. Para modos slice-aware, preenche p_j e
 * algos com a politica inicial do RslaqMacScheduler.
 */
static bool
ConfigureBaselineMode(const std::string& baselineMode,
                      const std::vector<double>& weightsArg,
                      RslaqMacScheduler::IntraSliceAlgorithm cliAlgo,
                      std::vector<double>* weights,
                      std::vector<RslaqMacScheduler::IntraSliceAlgorithm>* algos,
                      RslaqMacScheduler::SliceWeightPolicy* weightPolicy)
{
    const std::vector<double> equal = {1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0};
    const std::vector<double> weighted = {0.3333, 0.4000, 0.2667};
    *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::STATIC;

    if (IsPureMode(baselineMode))
    {
        *weights = {};
        *algos = {};
        return false;
    }

    *weights = weightsArg;
    RslaqMacScheduler::IntraSliceAlgorithm algo = cliAlgo;
    bool useCustomAlgos = false;

    if (baselineMode == "slice_rr")
    {
        *weights = equal;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::RR;
    }
    else if (baselineMode == "slice_pf")
    {
        *weights = equal;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_bcqi")
    {
        *weights = equal;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::BCQI;
    }
    else if (baselineMode == "slice_weighted_pf")
    {
        *weights = weighted;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_weighted_rr")
    {
        *weights = weighted;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::RR;
    }
    else if (baselineMode == "slice_weighted_bcqi")
    {
        *weights = weighted;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::BCQI;
    }
    else if (baselineMode == "slice_custom")
    {
        *weights = weightsArg;
    }
    else if (baselineMode == "psta_equal")
    {
        weights->resize(NUM_SLICES);
        for (uint32_t i = 0; i < NUM_SLICES; ++i)
        {
            (*weights)[i] = 0.5 * weighted[i] + 0.5 * equal[i];
        }
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_demand_greedy")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::DEMAND_GREEDY;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_sla_greedy")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::SLA_GREEDY;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_least_waste")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::LEAST_WASTE;
        *algos = {RslaqMacScheduler::IntraSliceAlgorithm::PF,
                  RslaqMacScheduler::IntraSliceAlgorithm::BCQI,
                  RslaqMacScheduler::IntraSliceAlgorithm::PF};
        useCustomAlgos = true;
    }
    else if (baselineMode == "slice_qos_mixed")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::SLA_GREEDY;
        *algos = {RslaqMacScheduler::IntraSliceAlgorithm::PF,
                  RslaqMacScheduler::IntraSliceAlgorithm::BCQI,
                  RslaqMacScheduler::IntraSliceAlgorithm::RR};
        useCustomAlgos = true;
    }
    else if (baselineMode == "slice_random_vine")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::RANDOM_VINE;
        algo = RslaqMacScheduler::IntraSliceAlgorithm::PF;
    }
    else if (baselineMode == "slice_meta_risk_elastic")
    {
        *weights = weightsArg;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::META_RISK_ELASTIC;
        *algos = {RslaqMacScheduler::IntraSliceAlgorithm::PF,
                  RslaqMacScheduler::IntraSliceAlgorithm::BCQI,
                  RslaqMacScheduler::IntraSliceAlgorithm::RR};
        useCustomAlgos = true;
    }
    else if (baselineMode == "slice_aqps")
    {
        *weights = equal;
        *weightPolicy = RslaqMacScheduler::SliceWeightPolicy::AQPS;
        *algos = {RslaqMacScheduler::IntraSliceAlgorithm::RR,
                  RslaqMacScheduler::IntraSliceAlgorithm::RR,
                  RslaqMacScheduler::IntraSliceAlgorithm::RR};
        useCustomAlgos = true;
    }
    else
    {
        NS_FATAL_ERROR("Invalid baselineMode: "
                       << baselineMode
                       << " (valid: pure_rr|pure_pf|pure_bcqi|slice_rr|slice_pf|slice_bcqi|"
                           "slice_weighted_pf|slice_weighted_rr|slice_weighted_bcqi|psta_equal|"
                           "slice_custom|slice_demand_greedy|slice_sla_greedy|slice_least_waste|"
                           "slice_qos_mixed|slice_random_vine|slice_meta_risk_elastic|slice_aqps)");
    }

    if (!useCustomAlgos)
    {
        algos->assign(NUM_SLICES, algo);
    }
    return true;
}

/**
 * @brief Normaliza o padrao TDD textual para o formato esperado pelo 5G-LENA.
 *
 * A palavra "article" ou o padrao compacto do artigo vira uma sequencia
 * DL/DL/DL/S/UL/UL/UL. Se o padrao nao puder ser interpretado, o simulador
 * cai para um modo DL-only simplificado para manter os experimentos executaveis.
 */
static std::string
NormalizeTddPatternForNr(const std::string& requested, bool* applied)
{
    if (requested == "dl_only")
    {
        *applied = true;
        return "DL|DL|DL|DL|DL|DL|DL|DL|DL|DL|";
    }
    if (requested == "D|D|8D|4GB|4U|U|U" || requested == "article")
    {
        *applied = true;
        return "DL|DL|DL|S|UL|UL|UL|";
    }

    std::stringstream ss(requested);
    std::string token;
    std::ostringstream out;
    bool ok = true;
    uint32_t count = 0;
    while (std::getline(ss, token, '|'))
    {
        if (token.empty())
        {
            continue;
        }
        std::string t = ToUpper(token);
        if (t == "D")
        {
            t = "DL";
        }
        else if (t == "U")
        {
            t = "UL";
        }
        else if (t == "GB")
        {
            t = "S";
        }

        if (t != "DL" && t != "UL" && t != "S" && t != "F")
        {
            ok = false;
            break;
        }
        out << t << "|";
        count++;
    }

    *applied = ok && count > 0;
    return *applied ? out.str() : "DL|DL|DL|DL|DL|DL|DL|DL|DL|DL|";
}

// ---------------------------------------------------------------------------
// Estruturas para estatísticas baseline (standalone mode)
// ---------------------------------------------------------------------------

struct UeStats
{
    /** Estatisticas acumuladas e deltas por UE para timeseries e summary. */
    uint16_t ueId = 0;
    SliceType slice = SliceType::EMBB;
    uint64_t txBytes = 0;
    uint64_t rxBytes = 0;
    uint64_t prevTxBytes = 0;
    uint64_t prevRxBytes = 0;
    uint32_t txPackets = 0;
    uint32_t rxPackets = 0;
    uint32_t lostPackets = 0;
    uint32_t prevTxPackets = 0;
    uint32_t prevRxPackets = 0;
    uint32_t prevLostPackets = 0;
    double delaySumSec = 0.0;
    double prevDelaySumSec = 0.0;
    double jitterSumSec = 0.0;
    double prevJitterSumSec = 0.0;
    std::vector<double> throughputSamplesMbps;
    std::vector<double> delaySamplesMs;
    std::vector<double> jitterSamplesMs;
    std::vector<double> bufferSamplesBytes;
};

struct SliceAggStats
{
    /** Agregados finais por slice calculados a partir do FlowMonitor. */
    uint64_t txBytes = 0;
    uint64_t rxBytes = 0;
    uint32_t txPackets = 0;
    uint32_t rxPackets = 0;
    uint32_t lostPackets = 0;
    double delaySumSec = 0.0;
    double jitterSumSec = 0.0;
    std::vector<double> throughputSamplesMbps;
};

struct SimState
{
    /** Estado global de medicao usado no modo standalone/baseline. */
    std::map<uint16_t, UeStats> ueStats;
    std::map<SliceType, SliceAggStats> sliceStats;
    std::ofstream statsFile;
    uint32_t stepCount{0};
    std::string outputDir;
    uint32_t indicationPeriodMs{10};
    double activeDurationSec{0.0};
};

static SimState g_baseline;

static double
Percentile(std::vector<double> values, double pct)
{
    if (values.empty())
    {
        return std::numeric_limits<double>::quiet_NaN();
    }
    std::sort(values.begin(), values.end());
    double pos = (pct / 100.0) * static_cast<double>(values.size() - 1);
    size_t lo = static_cast<size_t>(std::floor(pos));
    size_t hi = static_cast<size_t>(std::ceil(pos));
    if (lo == hi)
    {
        return values[lo];
    }
    double frac = pos - static_cast<double>(lo);
    return values[lo] * (1.0 - frac) + values[hi] * frac;
}

static std::string
CsvValue(double value, uint32_t precision = 4)
{
    if (std::isnan(value))
    {
        return "NA";
    }
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(precision) << value;
    return oss.str();
}

// ---------------------------------------------------------------------------
// Callback de estatísticas baseline (standalone)
// ---------------------------------------------------------------------------

/**
 * @brief Amostra periodicamente o FlowMonitor e escreve timeseries.csv.
 *
 * Este callback e independente do Gym: ele mede vazao, perdas, buffer estimado
 * e share configurado por UE/slice para comparacoes de baseline. No modo IPC,
 * ele continua util para gerar os mesmos artefatos de diagnostico.
 */
static void
StatsCallback()
{
    if (!g_monitorPtr || !g_classifierPtr)
    {
        Simulator::Schedule(MilliSeconds(g_baseline.indicationPeriodMs), &StatsCallback);
        return;
    }

    g_monitorPtr->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer stats = g_monitorPtr->GetFlowStats();
    uint64_t nowMs = static_cast<uint64_t>(Simulator::Now().GetMilliSeconds());
    g_baseline.stepCount++;
    std::map<SliceType, double> sliceThroughputThisStep = {
        {SliceType::EMBB, 0.0},
        {SliceType::URLLC, 0.0},
        {SliceType::MTC, 0.0},
    };

    if (!g_baseline.statsFile.is_open())
    {
        std::string path = g_baseline.outputDir + "/timeseries.csv";
        g_baseline.statsFile.open(path, std::ios::out | std::ios::trunc);
        g_baseline.statsFile << "timestamp_ms,ue_id,slice,thr_mbps,tx_bytes_delta,"
                              << "rx_bytes_delta,tx_packets_delta,rx_packets_delta,"
                              << "loss_pct_interval,buffer_bytes,dropped_packets_delta,"
                              << "rsh_configured_pct\n";
    }

    for (const auto& kv : stats)
    {
        FlowId flowId = kv.first;
        const FlowMonitor::FlowStats& st = kv.second;
        Ipv4FlowClassifier::FiveTuple tuple = g_classifierPtr->FindFlow(flowId);

        if (tuple.protocol != 17)
            continue;

        auto itPort = g_portToUeId.find(tuple.destinationPort);
        if (itPort == g_portToUeId.end())
            continue;

        uint16_t ueId = itPort->second;
        SliceType slice = g_ueToSlice[ueId];
        UeStats& ue = g_baseline.ueStats[ueId];

        uint64_t dRxBytes = st.rxBytes - ue.prevRxBytes;
        uint64_t dTxBytes = st.txBytes - ue.prevTxBytes;
        uint32_t dTxPackets = st.txPackets - ue.prevTxPackets;
        uint32_t dRxPackets = st.rxPackets - ue.prevRxPackets;
        uint32_t dLostPackets = st.lostPackets - ue.prevLostPackets;

        double periodSec = static_cast<double>(g_baseline.indicationPeriodMs) / 1000.0;
        double thrMbps = (periodSec > 0) ? (static_cast<double>(dRxBytes) * 8.0 / periodSec / 1e6) : 0.0;
        double lossPctInterval = (dTxPackets > 0) ? (static_cast<double>(dLostPackets) / static_cast<double>(dTxPackets) * 100.0) : 0.0;
        sliceThroughputThisStep[slice] += thrMbps;

        int32_t sliceIdx = static_cast<int32_t>(slice);
        double rshConfiguredPct = 0.0;
        int64_t bufferBytes = -1;
        if (g_schedulerPtr && sliceIdx >= 0)
        {
            rshConfiguredPct = g_schedulerPtr->GetPrbWeight(static_cast<uint32_t>(sliceIdx)) * 100.0;
            if (g_ueIdToRnti.count(ueId))
            {
                bufferBytes = g_schedulerPtr->GetUeDlBufferSize(g_ueIdToRnti[ueId]);
            }
        }

        g_baseline.statsFile << nowMs << "," << ueId << "," << SliceName(slice) << ","
                             << std::fixed << std::setprecision(4) << thrMbps << ","
                             << dTxBytes << ","
                             << dRxBytes << ","
                             << dTxPackets << ","
                             << dRxPackets << ","
                             << std::setprecision(2) << lossPctInterval << ","
                             << bufferBytes << ","
                             << dLostPackets << ","
                             << std::setprecision(2) << rshConfiguredPct << "\n";

        double dDelayMs = (st.delaySum.GetSeconds() - ue.prevDelaySumSec) * 1000.0;
        double dJitterMs = (st.jitterSum.GetSeconds() - ue.prevJitterSumSec) * 1000.0;
        double meanDelayMs = (dRxPackets > 0) ? dDelayMs / dRxPackets : 0.0;
        double meanJitterMs = (dRxPackets > 1) ? dJitterMs / (dRxPackets - 1) : 0.0;
        ue.throughputSamplesMbps.push_back(thrMbps);
        ue.delaySamplesMs.push_back(meanDelayMs);
        ue.jitterSamplesMs.push_back(meanJitterMs);
        if (bufferBytes >= 0)
        {
            ue.bufferSamplesBytes.push_back(static_cast<double>(bufferBytes));
        }

        ue.prevRxBytes = st.rxBytes;
        ue.prevTxBytes = st.txBytes;
        ue.prevRxPackets = st.rxPackets;
        ue.prevTxPackets = st.txPackets;
        ue.prevLostPackets = st.lostPackets;
        ue.prevDelaySumSec = st.delaySum.GetSeconds();
        ue.prevJitterSumSec = st.jitterSum.GetSeconds();

        ue.txBytes = st.txBytes;
        ue.rxBytes = st.rxBytes;
        ue.txPackets = st.txPackets;
        ue.rxPackets = st.rxPackets;
        ue.lostPackets = st.lostPackets;
        ue.delaySumSec = st.delaySum.GetSeconds();
        ue.jitterSumSec = st.jitterSum.GetSeconds();
    }

    for (auto& kv : sliceThroughputThisStep)
    {
        g_baseline.sliceStats[kv.first].throughputSamplesMbps.push_back(kv.second);
    }

    g_baseline.statsFile.flush();
    Simulator::Schedule(MilliSeconds(g_baseline.indicationPeriodMs), &StatsCallback);
}

static void
WriteSummaryCsv(const std::string& outputDir,
                const ScenarioConfig& scenario,
                const std::string& scenarioName,
                const std::string& baselineMode)
{
    std::ofstream out(outputDir + "/summary.csv", std::ios::out | std::ios::trunc);
    out << "scenario,baseline_mode,slice,throughput_mbps_mean,throughput_mbps_p50,"
        << "throughput_mbps_p95,delay_ms_mean,delay_ms_p95,delay_ms_p99,jitter_ms_mean,"
        << "pdr_pct,plr_pct,buffer_bytes_mean,buffer_bytes_p95,buffer_bytes_p99,"
        << "rsh_real_pct_mean,budget_utilization_pct_mean,unused_budget_pct_mean,"
        << "allocation_fidelity_pct_mean,offered_load_satisfaction_pct,"
        << "sla_satisfaction_pct,allocated_rbg_total,rx_bytes_total,tx_bytes_total\n";

    std::vector<RslaqMacScheduler::SliceAllocationStats> allocStats;
    if (g_schedulerPtr)
    {
        allocStats = g_schedulerPtr->GetSliceAllocationStats();
    }

    for (SliceType slice : {SliceType::EMBB, SliceType::URLLC, SliceType::MTC})
    {
        const SliceAggStats& agg = g_baseline.sliceStats[slice];
        std::vector<double> delaySamples;
        std::vector<double> jitterSamples;
        std::vector<double> bufferSamples;

        for (const auto& kv : g_baseline.ueStats)
        {
            const UeStats& ue = kv.second;
            if (ue.slice != slice)
            {
                continue;
            }
            delaySamples.insert(delaySamples.end(), ue.delaySamplesMs.begin(), ue.delaySamplesMs.end());
            jitterSamples.insert(jitterSamples.end(), ue.jitterSamplesMs.begin(), ue.jitterSamplesMs.end());
            bufferSamples.insert(bufferSamples.end(), ue.bufferSamplesBytes.begin(), ue.bufferSamplesBytes.end());
        }

        double throughputMean = (g_baseline.activeDurationSec > 0.0)
                                    ? static_cast<double>(agg.rxBytes) * 8.0 /
                                          g_baseline.activeDurationSec / 1e6
                                    : 0.0;
        double delayMean = (agg.rxPackets > 0) ? agg.delaySumSec * 1000.0 / agg.rxPackets : 0.0;
        double jitterMean = (agg.rxPackets > 1) ? agg.jitterSumSec * 1000.0 / (agg.rxPackets - 1) : 0.0;
        double pdrPct = (agg.txPackets > 0) ? 100.0 * static_cast<double>(agg.rxPackets) / agg.txPackets : 0.0;
        double plrPct = (agg.txPackets > 0) ? 100.0 * static_cast<double>(agg.lostPackets) / agg.txPackets : 0.0;

        uint32_t idx = static_cast<uint32_t>(slice);
        std::string rshMean = "NA";
        std::string budgetUtilizationMean = "NA";
        std::string unusedBudgetMean = "NA";
        std::string allocationFidelityMean = "NA";
        std::string allocatedTotal = "NA";
        if (idx < allocStats.size() && allocStats[idx].samples > 0)
        {
            const auto& alloc = allocStats[idx];
            rshMean = CsvValue(alloc.rshRealPctSum / alloc.samples);
            allocationFidelityMean = CsvValue(alloc.allocationFidelityPctSum / alloc.samples);
            allocatedTotal = std::to_string(alloc.allocatedRbgTotal);
            if (alloc.samplesWithBudget > 0)
            {
                budgetUtilizationMean = CsvValue(alloc.budgetUtilizationPctSum / alloc.samplesWithBudget);
                unusedBudgetMean = CsvValue(alloc.unusedBudgetPctSum / alloc.samplesWithBudget);
            }
        }

        double offeredLoadMbps = static_cast<double>(RateForSlice(scenario, slice)) / 1e6;
        double offeredLoadSatisfactionPct = (offeredLoadMbps > 0.0)
                                               ? std::min(100.0, 100.0 * throughputMean / offeredLoadMbps)
                                               : std::numeric_limits<double>::quiet_NaN();
        double slaSatisfactionPct = (SLA_MIN_MBPS[idx] > 0.0)
                                        ? std::min(100.0, 100.0 * throughputMean / SLA_MIN_MBPS[idx])
                                        : std::numeric_limits<double>::quiet_NaN();

        double bufferMean = std::numeric_limits<double>::quiet_NaN();
        if (!bufferSamples.empty())
        {
            bufferMean = std::accumulate(bufferSamples.begin(), bufferSamples.end(), 0.0) /
                         static_cast<double>(bufferSamples.size());
        }

        out << scenarioName << "," << baselineMode << "," << SliceName(slice) << ","
            << CsvValue(throughputMean) << ","
            << CsvValue(Percentile(agg.throughputSamplesMbps, 50.0)) << ","
            << CsvValue(Percentile(agg.throughputSamplesMbps, 95.0)) << ","
            << CsvValue(delayMean, 3) << ","
            << CsvValue(Percentile(delaySamples, 95.0), 3) << ","
            << CsvValue(Percentile(delaySamples, 99.0), 3) << ","
            << CsvValue(jitterMean, 3) << ","
            << CsvValue(pdrPct, 3) << ","
            << CsvValue(plrPct, 3) << ","
            << CsvValue(bufferMean, 2) << ","
            << CsvValue(Percentile(bufferSamples, 95.0), 2) << ","
            << CsvValue(Percentile(bufferSamples, 99.0), 2) << ","
            << rshMean << ","
            << budgetUtilizationMean << ","
            << unusedBudgetMean << ","
            << allocationFidelityMean << ","
            << CsvValue(offeredLoadSatisfactionPct, 3) << ","
            << CsvValue(slaSatisfactionPct, 3) << ","
            << allocatedTotal << ","
            << agg.rxBytes << ","
            << agg.txBytes << "\n";
    }
}

static void
WriteMetadataJson(const std::string& outputDir,
                  const ScenarioConfig& scenario,
                  const std::string& baselineMode,
                  const std::string& intraAlgoName,
                  const std::vector<RslaqMacScheduler::IntraSliceAlgorithm>& sliceAlgos,
                  uint32_t seed,
                  uint32_t run,
                  double simTimeSec,
                  double drainTimeSec,
                  const std::vector<double>& weights,
                  const std::string& sliceWeightPolicy,
                  const std::string& duplexMode,
                  const std::string& tddPatternRequested,
                  const std::string& tddPatternApplied,
                  const std::string& rlcMode,
                  bool dlOnly,
                  bool embbSlaFeasible)
{
    std::ofstream out(outputDir + "/metadata.json", std::ios::out | std::ios::trunc);
    auto mbps = [](uint64_t bps) { return static_cast<double>(bps) / 1e6; };
    auto mbpsPerUe = [](uint64_t bps, uint32_t ues) {
        return ues == 0 ? 0.0 : static_cast<double>(bps) / 1e6 / static_cast<double>(ues);
    };
    out << "{\n"
        << "  \"scenario\": \"" << scenario.name << "\",\n"
        << "  \"baseline_mode\": \"" << baselineMode << "\",\n"
        << "  \"intra_algo\": \"" << intraAlgoName << "\",\n"
        << "  \"intra_algos_per_slice\": {\"eMBB\": \""
        << (sliceAlgos.size() > 0 ? IntraAlgoName(sliceAlgos[0]) : "NA")
        << "\", \"URLLC\": \""
        << (sliceAlgos.size() > 1 ? IntraAlgoName(sliceAlgos[1]) : "NA")
        << "\", \"MTC\": \""
        << (sliceAlgos.size() > 2 ? IntraAlgoName(sliceAlgos[2]) : "NA") << "\"},\n"
        << "  \"seed\": " << seed << ",\n"
        << "  \"run\": " << run << ",\n"
        << "  \"sim_time_sec\": " << simTimeSec << ",\n"
        << "  \"drain_time_sec\": " << drainTimeSec << ",\n"
        << "  \"num_gnbs\": 1,\n"
        << "  \"num_ues\": " << (g_numUeEmbb + g_numUeUrllc + g_numUeMtc) << ",\n"
        << "  \"num_ues_per_slice\": {\"eMBB\": " << g_numUeEmbb
        << ", \"URLLC\": " << g_numUeUrllc
        << ", \"MTC\": " << g_numUeMtc << "},\n"
        << "  \"slices\": [\"eMBB\", \"URLLC\", \"MTC\"],\n"
        << "  \"slice_weights_configured\": [";
    for (size_t i = 0; i < weights.size(); ++i)
    {
        if (i)
        {
            out << ", ";
        }
        out << std::fixed << std::setprecision(4) << weights[i];
    }
    out << "],\n"
        << "  \"slice_weight_policy\": \"" << sliceWeightPolicy << "\",\n"
        << "  \"traffic_mbps_per_slice\": {\"eMBB\": " << mbps(scenario.embbRateBps)
        << ", \"URLLC\": " << mbps(scenario.urllcRateBps)
        << ", \"MTC\": " << mbps(scenario.mtcRateBps) << "},\n"
        << "  \"traffic_mbps_per_ue\": {\"eMBB\": " << mbpsPerUe(scenario.embbRateBps, g_numUeEmbb)
        << ", \"URLLC\": " << mbpsPerUe(scenario.urllcRateBps, g_numUeUrllc)
        << ", \"MTC\": " << mbpsPerUe(scenario.mtcRateBps, g_numUeMtc) << "},\n"
        << "  \"packet_size_bytes_per_slice\": {\"eMBB\": " << scenario.embbPktSize
        << ", \"URLLC\": " << scenario.urllcPktSize
        << ", \"MTC\": " << scenario.mtcPktSize << "},\n"
        << "  \"offered_load_mbps_per_slice\": {\"eMBB\": " << mbps(scenario.embbRateBps)
        << ", \"URLLC\": " << mbps(scenario.urllcRateBps)
        << ", \"MTC\": " << mbps(scenario.mtcRateBps) << "},\n"
        << "  \"sla\": {\"min_mbps_per_slice\": {\"eMBB\": " << SLA_MIN_MBPS[0]
        << ", \"URLLC\": " << SLA_MIN_MBPS[1]
        << ", \"MTC\": " << SLA_MIN_MBPS[2] << "}},\n"
        << "  \"sla_min_mbps_per_slice\": {\"eMBB\": " << SLA_MIN_MBPS[0]
        << ", \"URLLC\": " << SLA_MIN_MBPS[1]
        << ", \"MTC\": " << SLA_MIN_MBPS[2] << "},\n"
        << "  \"sla_feasible_by_offered_load\": " << (embbSlaFeasible ? "true" : "false") << ",\n"
        << "  \"duplex_mode\": \"" << duplexMode << "\",\n"
        << "  \"rlc_mode\": \"" << rlcMode << "\",\n"
        << "  \"resource_efficiency_metrics\": {"
        << "\"budget_utilization_pct\": \"allocated_rbg / budget_rbg * 100\", "
        << "\"unused_budget_pct\": \"max(0, budget_rbg - allocated_rbg) / budget_rbg * 100\", "
        << "\"allocation_fidelity_pct\": \"100 - abs(rsh_real_pct - effective_weight * 100)\", "
        << "\"offered_load_satisfaction_pct\": \"throughput_mbps_mean / offered_load_mbps * 100, capped at 100\", "
        << "\"sla_satisfaction_pct\": \"throughput_mbps_mean / sla_min_mbps * 100, capped at 100\"},\n"
        << "  \"tdd_pattern_requested\": \"" << tddPatternRequested << "\",\n"
        << "  \"tdd_pattern_applied\": \"" << tddPatternApplied << "\",\n"
        << "  \"dl_only\": " << (dlOnly ? "true" : "false") << ",\n"
        << "  \"notes\": [";
    bool wroteNote = false;
    if (dlOnly)
    {
        out << "\"TDD pattern not applied; simplified DL-only simulation\"";
        wroteNote = true;
    }
    if (!embbSlaFeasible)
    {
        if (wroteNote)
        {
            out << ", ";
        }
        out << "\"eMBB offered load is below eMBB minimum SLA\"";
    }
    out << "]\n"
        << "}\n";
}

// ---------------------------------------------------------------------------
// IPC: KPM e Action callback
// ---------------------------------------------------------------------------

/**
 * @brief Escreve rslaq-kpms.txt e sinaliza o gym via semáforo.
 *        Depois espera ação do agente, lê o CSV e atualiza o scheduler.
 *
 * Ciclo IPC por periodo de indicacao:
 *   1. FlowMonitor agrega fluxos UDP e mapeia porta destino -> UE -> slice.
 *   2. O simulador escreve KPIs delta em rslaq-kpms.txt.
 *   3. sem_metrics_* libera o passo Python/Gym.
 *   4. O Python escreve rslaq_actions_for_ns3.csv e libera sem_control_*.
 *   5. O simulador le PRB% finais e scheduler_id por slice e reconfigura MAC.
 *
 * Formato KPM atual:
 *   timestamp,ueImsi,sliceId,dTxBytes,dRxBytes,plr,resourceSharePct,
 *   dLostPackets,throughputMbps,bufferBytes
 */
static void
KpmAndControlCallback()
{
    if (!g_ipcEnabled || !g_monitorPtr || !g_classifierPtr || !g_schedulerPtr)
    {
        Simulator::Schedule(MilliSeconds(g_indicationPeriodMs), &KpmAndControlCallback);
        return;
    }

    uint64_t nowMs = static_cast<uint64_t>(Simulator::Now().GetMilliSeconds());

    // Coletar métricas do FlowMonitor
    g_monitorPtr->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer stats = g_monitorPtr->GetFlowStats();

    struct UeKpm
    {
        uint64_t txBytes = 0;
        uint64_t rxBytes = 0;
        uint32_t txPackets = 0;
        uint32_t rxPackets = 0;
        uint32_t lostPackets = 0;
        double delaySumSec = 0.0;
        uint32_t count = 0;
    };

    std::map<uint16_t, UeKpm> ueKpms; // key = ueId

    for (const auto& kv : stats)
    {
        FlowId flowId = kv.first;
        const FlowMonitor::FlowStats& st = kv.second;
        Ipv4FlowClassifier::FiveTuple tuple = g_classifierPtr->FindFlow(flowId);

        if (tuple.protocol != 17)
            continue;

        auto itPort = g_portToUeId.find(tuple.destinationPort);
        if (itPort == g_portToUeId.end())
            continue;

        uint16_t ueId = itPort->second;
        UeKpm& k = ueKpms[ueId];
        k.txBytes += st.txBytes;
        k.rxBytes += st.rxBytes;
        k.txPackets += st.txPackets;
        k.rxPackets += st.rxPackets;
        k.lostPackets += st.lostPackets;
        k.delaySumSec += st.delaySum.GetSeconds();
        k.count++;
    }

    // Escrever rslaq-kpms.txt (now using delta-based metrics)
    {
        std::ofstream kpmFile("rslaq-kpms.txt", std::ios::out | std::ios::trunc);
        kpmFile << "timestamp,ueImsi,sliceId,dTxBytes,dRxBytes,plr,resourceSharePct,dLostPackets,throughputMbps,bufferBytes\n";

        for (const auto& kv : ueKpms)
        {
            uint16_t ueId = kv.first;
            const UeKpm& k = kv.second;
            SliceType slice = g_ueToSlice[ueId];
            uint32_t sliceIdx = static_cast<uint32_t>(slice);

            // Get previous values and calculate deltas
            KpmPrevValues& prev = g_kpmPrevValues[ueId];
            uint64_t dTxBytes = (k.txBytes >= prev.txBytes) ? (k.txBytes - prev.txBytes) : 0;
            uint64_t dRxBytes = (k.rxBytes >= prev.rxBytes) ? (k.rxBytes - prev.rxBytes) : 0;
            uint32_t dTxPackets = (k.txPackets >= prev.txPackets) ? (k.txPackets - prev.txPackets) : 0;
            uint32_t dRxPackets = (k.rxPackets >= prev.rxPackets) ? (k.rxPackets - prev.rxPackets) : 0;

            // Update previous values for next iteration
            prev.txBytes = k.txBytes;
            prev.rxBytes = k.rxBytes;
            prev.txPackets = k.txPackets;
            prev.rxPackets = k.rxPackets;
            prev.lostPackets = k.lostPackets;

            // Calculate effective loss (more reliable than FlowMonitor lostPackets)
            uint32_t effectiveLost = (dTxPackets >= dRxPackets) ? (dTxPackets - dRxPackets) : 0;

            double plr = (dTxPackets > 0)
                             ? (static_cast<double>(effectiveLost) / dTxPackets * 100.0)
                             : 0.0;
            double rsh = (g_schedulerPtr)
                             ? g_schedulerPtr->GetPrbWeight(sliceIdx) * 100.0
                             : 0.0;
            double periodSec = static_cast<double>(g_indicationPeriodMs) / 1000.0;
            double thrMbps = (periodSec > 0)
                                 ? (static_cast<double>(dRxBytes) * 8.0 / periodSec / 1e6)
                                 : 0.0;

            uint32_t bufferBytes = (g_schedulerPtr && g_ueIdToRnti.count(ueId))
                                       ? g_schedulerPtr->GetUeDlBufferSize(g_ueIdToRnti[ueId])
                                       : 0;

            kpmFile << nowMs << "," << ueId << "," << sliceIdx << ","
                    << dTxBytes << "," << dRxBytes << ","
                    << std::fixed << std::setprecision(2) << plr << ","
                    << std::setprecision(2) << rsh << ","
                    << effectiveLost << ","
                    << std::setprecision(4) << thrMbps << ","
                    << bufferBytes << "\n";
        }
        kpmFile.flush();
    }

    // Sinalizar ao Python: métricas prontas
    if (g_semMetricsReady)
    {
        sem_post(g_semMetricsReady);
    }

    // Esperar ação do agente (timeout curto de 50ms para não bloquear a simulação)
    if (g_semControl)
    {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        ts.tv_nsec += 50 * 1000 * 1000; // 50ms
        if (ts.tv_nsec >= 1000000000)
        {
            ts.tv_sec += 1;
            ts.tv_nsec -= 1000000000;
        }
        int ret = sem_timedwait(g_semControl, &ts);
        if (ret == 0)
        {
            // Ler ação do agente
            std::ifstream actionFile("rslaq_actions_for_ns3.csv");
            if (actionFile.is_open())
            {
                std::string line;
                std::vector<double> dedicatedPrb(NUM_SLICES, 33.33);
                std::vector<RslaqMacScheduler::IntraSliceAlgorithm> algos(
                    NUM_SLICES,
                    RslaqMacScheduler::IntraSliceAlgorithm::PF);
                while (std::getline(actionFile, line))
                {
                    std::stringstream ss(line);
                    std::string token;
                    std::vector<std::string> cols;
                    while (std::getline(ss, token, ','))
                    {
                        cols.push_back(token);
                    }
                    if (cols.size() >= 4)
                    {
                        try
                        {
                            uint32_t sliceId = static_cast<uint32_t>(std::stoi(cols[1]));
                            double ded = std::stod(cols[2]);
                            if (sliceId < NUM_SLICES)
                            {
                                dedicatedPrb[sliceId] = ded;
                                if (cols.size() >= 6)
                                {
                                    algos[sliceId] = IntraAlgoFromActionId(std::stoi(cols[5]));
                                }
                            }
                        }
                        catch (const std::exception&)
                        {
                            // Allows both headerless control files and optional CSV headers.
                            continue;
                        }
                    }
                }
                actionFile.close();

                // P_STA decomposition is applied in Python (rslaq_action_spaces.py)
                // The agent sends dedicatedPRB as % of total, already including P_STA.
                // We use these values directly to avoid double application.
                double totalDed = dedicatedPrb[0] + dedicatedPrb[1] + dedicatedPrb[2];
                if (totalDed > 0.0)
                {
                    std::vector<double> p_final(NUM_SLICES);
                    for (uint32_t s = 0; s < NUM_SLICES; s++)
                    {
                        // Directly use the percentages from Python (already normalized)
                        p_final[s] = dedicatedPrb[s] / totalDed;
                    }

                    // Renormalizar para somar 1.0 (guard contra floating point)
                    double sum = p_final[0] + p_final[1] + p_final[2];
                    if (sum > 0.0)
                    {
                        for (uint32_t s = 0; s < NUM_SLICES; s++)
                        {
                            p_final[s] /= sum;
                        }
                    }

                    g_schedulerPtr->SetSliceConfiguration(p_final, algos);

                    NS_LOG_INFO("[RslaqSim] IPC action applied at t=" << nowMs
                                << "ms: weights=[" << p_final[0] << ", "
                                << p_final[1] << ", " << p_final[2] << "]"
                                << " algos=[" << IntraAlgoName(algos[0]) << ", "
                                << IntraAlgoName(algos[1]) << ", "
                                << IntraAlgoName(algos[2]) << "]");
                }
            }
        }
        else
        {
            NS_LOG_WARN("[RslaqSim] sem_timedwait timeout — no action from agent");
        }
    }

    // Agendar próximo callback
    Simulator::Schedule(MilliSeconds(g_indicationPeriodMs), &KpmAndControlCallback);
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int
main(int argc, char* argv[])
{
    /*
     * Fluxo principal do cenário 5G:
     * 1. Ler CLI e selecionar o perfil de carga RSLAQ.
     * 2. Criar topologia EPC + 1 gNB + UEs + remoteHost.
     * 3. Configurar canal NR, antenas, numerologia, TDD e RLC.
     * 4. Instalar dispositivos NR, IP, rotas e anexar UEs ao gNB.
     * 5. Mapear UE/RNTI/slice apos attach e configurar o scheduler.
     * 6. Instalar trafego UDP downlink por UE.
     * 7. Agendar callbacks de estatistica e, opcionalmente, IPC com Python.
     */
    auto scenarios = InitScenarios();

    std::string scenarioName = "normal";
    std::string outputDir = ".";
    uint32_t seed = 1;
    uint32_t run = 1;
    double simTimeSec = 4.0;
    double appStartSec = 0.4;
    double drainTimeSec = 0.2;
    uint32_t indicationPeriodMs = 10;
    std::string tddPattern = "D|D|8D|4GB|4U|U|U";
    std::string rlcMode = "um";
    double centralFrequency = 3.55e9;
    double bandwidth = 100e6;
    uint16_t numerology = 1;
    double txPowerDbm = 37.0 + 10.0 * std::log10(4.0);
    double gnbNoiseFigureDb = 4.0;
    double gnbHeightM = 10.0;
    double ueHeightM = 1.5;
    double ueRadiusM = 100.0;
    double gnbDowntiltDeg = 6.0;
    double gnbBearingDeg = 0.0;
    bool shadowingEnabled = true;
    std::string weightsStr = "0.3333,0.4000,0.2667";
    std::string baselineMode = "slice_weighted_pf";
    std::string intraAlgo = "PF";
    std::string simId = "";
    bool logAllMacSlots = false;
    uint32_t macLoggingPeriodMs = 97;

    CommandLine cmd(__FILE__);
    cmd.AddValue("scenario", "1-5 or name", scenarioName);
    cmd.AddValue("simTime", "Total sim time (s)", simTimeSec);
    cmd.AddValue("appStart", "App start time (s)", appStartSec);
    cmd.AddValue("seed", "RNG seed", seed);
    cmd.AddValue("run", "RNG run", run);
    cmd.AddValue("drainTimeSec", "Drain time after client stop to avoid in-flight packet loss", drainTimeSec);
    cmd.AddValue("outputDir", "Output directory", outputDir);
    cmd.AddValue("periodMs", "Stats indication period (ms)", indicationPeriodMs);
    cmd.AddValue("tddPattern", "TDD slot pattern string", tddPattern);
    cmd.AddValue("rlcMode", "RLC mode for data radio bearers: am or um", rlcMode);
    cmd.AddValue("centralFrequency", "NR carrier center frequency (Hz)", centralFrequency);
    cmd.AddValue("bandwidth", "NR channel bandwidth (Hz)", bandwidth);
    cmd.AddValue("numerology", "NR numerology (mu, where SCS = 15 kHz * 2^mu)", numerology);
    cmd.AddValue("txPower", "gNB aggregate TX power over all antenna ports (dBm)", txPowerDbm);
    cmd.AddValue("gnbNoiseFigure", "gNB receiver noise figure (dB)", gnbNoiseFigureDb);
    cmd.AddValue("gnbHeight", "gNB antenna height (m)", gnbHeightM);
    cmd.AddValue("ueHeight", "UE antenna height (m)", ueHeightM);
    cmd.AddValue("ueRadius", "Uniform outdoor UE placement radius around the gNB (m)", ueRadiusM);
    cmd.AddValue("gnbDowntiltDeg", "gNB panel downtilt angle (degrees)", gnbDowntiltDeg);
    cmd.AddValue("gnbBearingDeg", "gNB panel bearing angle on the x-y plane (degrees)", gnbBearingDeg);
    cmd.AddValue("shadowing", "Enable 3GPP pathloss shadowing", shadowingEnabled);
    cmd.AddValue("embbUes", "Number of eMBB UEs (0 uses the scenario profile)", g_numUeEmbb);
    cmd.AddValue("urllcUes", "Number of URLLC UEs (0 uses the scenario profile)", g_numUeUrllc);
    cmd.AddValue("mtcUes", "Number of MTC UEs (0 uses the scenario profile)", g_numUeMtc);
    cmd.AddValue("weights", "Slice weights as comma-separated list (eMBB,URLLC,MTC)", weightsStr);
    cmd.AddValue("baselineMode",
                 "pure_rr|pure_pf|pure_bcqi|slice_rr|slice_pf|slice_bcqi|slice_weighted_pf|slice_weighted_rr|slice_weighted_bcqi|psta_equal|slice_custom|slice_demand_greedy|slice_sla_greedy|slice_least_waste|slice_qos_mixed|slice_random_vine|slice_meta_risk_elastic|slice_aqps",
                 baselineMode);
    cmd.AddValue("intraAlgo", "RR|PF|BCQI", intraAlgo);
    cmd.AddValue("simId", "Simulation UUID for IPC semaphores", simId);
    cmd.AddValue("LogAllMacSlots", "Log every MAC scheduling call (large files)", logAllMacSlots);
    cmd.AddValue("MacLoggingPeriodMs", "MAC logging period in ms (when LogAllMacSlots=false)", macLoggingPeriodMs);
    cmd.Parse(argc, argv);

    if (scenarioName.size() == 1 && std::isdigit(scenarioName[0]))
    {
        const char* names[] = {"low_traffic", "normal", "congestion", "stressed",
                               "insufficient_resources"};
        int idx = std::stoi(scenarioName) - 1;
        if (idx < 0 || idx > 4)
        {
            NS_FATAL_ERROR("Scenario must be 1-5 or a valid name");
        }
        scenarioName = names[idx];
    }

    if (scenarios.find(scenarioName) == scenarios.end())
    {
        NS_FATAL_ERROR("Unknown scenario: " << scenarioName);
    }

    const ScenarioConfig scenario = scenarios.at(scenarioName);
    const bool useScenarioUeProfile =
        (g_numUeEmbb == 0 && g_numUeUrllc == 0 && g_numUeMtc == 0);
    if (useScenarioUeProfile)
    {
        g_numUeEmbb = scenario.embbUes;
        g_numUeUrllc = scenario.urllcUes;
        g_numUeMtc = scenario.mtcUes;
    }
    else if (g_numUeEmbb == 0 || g_numUeUrllc == 0 || g_numUeMtc == 0)
    {
        NS_FATAL_ERROR("Provide all three UE overrides (--embbUes, --urllcUes, --mtcUes) or leave all as 0 to use the scenario profile");
    }
    const uint32_t numUeTotal = g_numUeEmbb + g_numUeUrllc + g_numUeMtc;
    rlcMode = ToLower(rlcMode);

    if (simTimeSec <= drainTimeSec)
    {
        NS_FATAL_ERROR("simTimeSec must be greater than drainTimeSec");
    }
    if (simTimeSec - drainTimeSec <= appStartSec)
    {
        NS_FATAL_ERROR("simTimeSec - drainTimeSec must be greater than appStartSec");
    }
    if (centralFrequency <= 0.0)
    {
        NS_FATAL_ERROR("centralFrequency must be positive");
    }
    if (bandwidth <= 0.0)
    {
        NS_FATAL_ERROR("bandwidth must be positive");
    }
    if (gnbHeightM <= 0.0 || ueHeightM <= 0.0)
    {
        NS_FATAL_ERROR("gnbHeight and ueHeight must be positive");
    }
    if (ueRadiusM <= 0.0)
    {
        NS_FATAL_ERROR("ueRadius must be positive");
    }
    if (gnbDowntiltDeg < 0.0 || gnbDowntiltDeg > 10.0)
    {
        NS_FATAL_ERROR("gnbDowntiltDeg must be within the AW3161 eRET range [0, 10]");
    }
    if (numUeTotal == 0)
    {
        NS_FATAL_ERROR("At least one UE must be configured");
    }
    if (rlcMode != "am" && rlcMode != "um")
    {
        NS_FATAL_ERROR("rlcMode must be either 'am' or 'um'");
    }

    std::vector<double> sliceWeights = ParseWeights(weightsStr);
    if (sliceWeights.size() != NUM_SLICES)
    {
        NS_FATAL_ERROR("Weights must have exactly " << NUM_SLICES << " elements");
    }
    double wsum = 0.0;
    for (double w : sliceWeights)
    {
        if (w < 0.0)
        {
            NS_FATAL_ERROR("Weights must be non-negative (got " << w << ")");
        }
        wsum += w;
    }
    if (std::abs(wsum - 1.0) > 1e-3)
    {
        NS_FATAL_ERROR("Weights must sum to 1.0 (got " << wsum << ")");
    }

    RslaqMacScheduler::IntraSliceAlgorithm parsedIntraAlgo = ParseIntraAlgo(intraAlgo);
    std::vector<RslaqMacScheduler::IntraSliceAlgorithm> sliceAlgos;
    std::vector<double> p_j;
    RslaqMacScheduler::SliceWeightPolicy sliceWeightPolicy;
    g_useSliceScheduler = ConfigureBaselineMode(baselineMode,
                                                sliceWeights,
                                                parsedIntraAlgo,
                                                &p_j,
                                                &sliceAlgos,
                                                &sliceWeightPolicy);

    if (g_useSliceScheduler)
    {
        double configuredSum = std::accumulate(p_j.begin(), p_j.end(), 0.0);
        NS_ASSERT_MSG(p_j.size() == NUM_SLICES, "weights.size() must be 3");
        NS_ASSERT_MSG(std::abs(configuredSum - 1.0) < 1e-3,
                      "sum(weights) must be approximately 1.0, got " << configuredSum);
    }

    std::filesystem::path baseOutput(outputDir);
    outputDir = (baseOutput / "results_rslaq_network_only" /
                 ("scenario=" + scenarioName) /
                 ("mode=" + baselineMode) /
                 ("seed=" + std::to_string(seed) + "_run=" + std::to_string(run)))
                    .string();
    std::filesystem::create_directories(outputDir);
    if (!g_useSliceScheduler)
    {
        std::ofstream alloc(outputDir + "/slice_alloc.csv", std::ios::out | std::ios::trunc);
        alloc << "timestamp_ms,slice,configured_weight,budget_rbg,allocated_rbg,"
              << "total_allocated_rbg,rsh_real_pct,budget_utilization_pct,"
              << "unused_budget_pct,allocation_fidelity_pct,active_ues,effective_weight,"
              << "beam_id,has_demand,reason,redistributed_idle_rbg,rntis\n";
    }

    bool tddApplied = false;
    std::string appliedTddPattern = NormalizeTddPatternForNr(tddPattern, &tddApplied);
    std::string duplexMode = tddApplied ? "tdd" : "dl_only";
    bool dlOnly = !tddApplied;

    bool embbSlaFeasible = (static_cast<double>(scenario.embbRateBps) / 1e6) >= SLA_MIN_MBPS[0];
    if (!embbSlaFeasible)
    {
        std::cout << "WARNING: eMBB offered load is below eMBB minimum SLA. Goodput cannot satisfy SLA; use this scenario only to evaluate resource redistribution/waste.\n";
    }
    if (dlOnly)
    {
        std::cout << "WARNING: TDD pattern not applied. Running simplified DL-only simulation. Results are not directly comparable to RSLAQ Table IV.\n";
    }

    g_indicationPeriodMs = indicationPeriodMs;

    const uint16_t baseDlPort = 12000;
    const double scsKhz = 15.0 * std::pow(2.0, numerology);
    const double gnbDowntiltRad = gnbDowntiltDeg * std::acos(-1.0) / 180.0;
    const double gnbBearingRad = gnbBearingDeg * std::acos(-1.0) / 180.0;

    std::cout << "========================================\n"
              << "  RSLAQ Simulation (Slice-Aware + IPC)\n"
              << "========================================\n"
              << "Scenario     : " << scenario.name << "\n"
              << "RF profile   : RAN650 n78 + AW3161-E-F-V2 outdoor panel\n"
              << "Frequency    : " << centralFrequency / 1e9 << " GHz\n"
              << "Bandwidth    : " << bandwidth / 1e6 << " MHz\n"
              << "Numerology   : " << numerology << " (SCS " << scsKhz << " kHz)\n"
              << "UEs          : " << numUeTotal
              << " (eMBB=" << g_numUeEmbb
              << " URLLC=" << g_numUeUrllc
              << " MTC=" << g_numUeMtc << ")\n"
              << "UE area      : uniform disc radius " << ueRadiusM
              << " m, UE height " << ueHeightM << " m\n"
              << "gNB height   : " << gnbHeightM << " m\n"
              << "gNB antenna  : 4 ports, +/-45 deg pol, 17.9 dBi, 65x7 deg, tilt "
              << gnbDowntiltDeg << " deg, bearing " << gnbBearingDeg << " deg\n"
              << "SimTime      : " << simTimeSec << " s\n"
              << "TxPower      : " << txPowerDbm << " dBm\n"
              << "gNB NF       : " << gnbNoiseFigureDb << " dB\n"
              << "RLC mode     : " << ToUpper(rlcMode) << "\n"
              << "Shadowing    : " << (shadowingEnabled ? "enabled" : "disabled") << "\n"
              << "Stats period : " << indicationPeriodMs << " ms\n"
              << "BaselineMode : " << baselineMode << "\n"
              << "IntraAlgo    : " << (g_useSliceScheduler ? IntraAlgoName(sliceAlgos[0]) : "NA") << "\n"
              << "WeightPolicy : " << (g_useSliceScheduler ? SliceWeightPolicyName(sliceWeightPolicy) : "NA") << "\n"
              << "Seed/Run     : " << seed << "/" << run << "\n"
              << "IPC enabled  : " << (simId.empty() ? "NO (standalone)" : "YES") << "\n"
              << "OutputDir    : " << outputDir << "\n";
    if (g_useSliceScheduler)
    {
        std::cout << "Weights      : eMBB=" << p_j[0]
                  << " URLLC=" << p_j[1]
                  << " MTC=" << p_j[2] << "\n\n";
    }
    else
    {
        std::cout << "Weights      : NA (pure native scheduler)\n\n";
    }

    // Setup IPC semaphores if simId provided
    if (!simId.empty())
    {
        g_simUuid = simId;
        g_ipcEnabled = true;

        std::string semMetricsName = "/sem_metrics_" + simId;
        std::string semControlName = "/sem_control_" + simId;

        g_semMetricsReady = sem_open(semMetricsName.c_str(), O_CREAT, 0660, 0);
        g_semControl = sem_open(semControlName.c_str(), O_CREAT, 0660, 0);

        if (g_semMetricsReady == SEM_FAILED || g_semControl == SEM_FAILED)
        {
            std::cerr << "WARNING: Failed to create POSIX semaphores. Running standalone.\n";
            g_ipcEnabled = false;
            if (g_semMetricsReady != SEM_FAILED)
                sem_close(g_semMetricsReady);
            if (g_semControl != SEM_FAILED)
                sem_close(g_semControl);
            g_semMetricsReady = nullptr;
            g_semControl = nullptr;
        }
        else
        {
            std::cout << "[RslaqSim] IPC semaphores created: "
                      << semMetricsName << " and " << semControlName << "\n";
        }
    }

    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(run);

    Config::SetDefault("ns3::NrRlcUm::MaxTxBufferSize", UintegerValue(10485760));
    Config::SetDefault("ns3::NrGnbRrc::QosFlowToRlcMapping",
                       EnumValue(rlcMode == "am" ? NrGnbRrc::RLC_AM_ALWAYS
                                                  : NrGnbRrc::RLC_UM_ALWAYS));
    Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod", TimeValue(MilliSeconds(0)));

    // ---- Nodes ----
    // Topologia logica: remoteHost conectado ao PGW/EPC por P2P, um gNB NR e
    // todos os UEs NR servidos por esse gNB. Nao ha handover nem multiplas celulas.
    NodeContainer gNbNodes;
    gNbNodes.Create(1);
    NodeContainer ueNodes;
    ueNodes.Create(numUeTotal);
    NodeContainer remoteHostContainer;
    remoteHostContainer.Create(1);

    // ---- Mobility ----
    // gNB fixo no centro; UEs fixos em disco uniforme ao redor do gNB. Isso
    // isola o estudo de slicing/scheduler, evitando variabilidade de mobilidade.
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    {
        Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
        pos->Add(Vector(0.0, 0.0, gnbHeightM));
        mobility.SetPositionAllocator(pos);
        mobility.Install(gNbNodes);
    }
    {
        MobilityHelper ueMob;
        ueMob.SetPositionAllocator("ns3::UniformDiscPositionAllocator",
                                   "rho",
                                   DoubleValue(ueRadiusM),
                                   "X",
                                   DoubleValue(0.0),
                                   "Y",
                                   DoubleValue(0.0),
                                   "Z",
                                   DoubleValue(ueHeightM));
        ueMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        ueMob.Install(ueNodes);
    }

    // ---- NR Helpers ----
    // NrHelper cria PHY/MAC/RLC/RRC; EPC helper adiciona PGW e caminho IP para
    // trafego externo. O scheduler instalado depende do baselineMode.
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
    nrHelper->SetEpcHelper(epcHelper);

    nrHelper->SetSchedulerTypeId(NativeSchedulerForMode(baselineMode));

    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(1));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(1));
    nrHelper->SetUeAntennaAttribute("AntennaElement",
                                     PointerValue(CreateObject<IsotropicAntennaModel>()));
    Ptr<CosineAntennaModel> gnbPanelElement = CreateObject<CosineAntennaModel>();
    gnbPanelElement->SetAttribute("HorizontalBeamwidth", DoubleValue(65.0));
    gnbPanelElement->SetAttribute("VerticalBeamwidth", DoubleValue(7.0));
    gnbPanelElement->SetAttribute("MaxGain", DoubleValue(17.9));
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(1));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(2));
    nrHelper->SetGnbAntennaAttribute("IsDualPolarized", BooleanValue(true));
    nrHelper->SetGnbAntennaAttribute("NumHorizontalPorts", UintegerValue(2));
    nrHelper->SetGnbAntennaAttribute("NumVerticalPorts", UintegerValue(1));
    nrHelper->SetGnbAntennaAttribute("PolSlantAngle", DoubleValue(45.0 * std::acos(-1.0) / 180.0));
    nrHelper->SetGnbAntennaAttribute("DowntiltAngle", DoubleValue(gnbDowntiltRad));
    nrHelper->SetGnbAntennaAttribute("BearingAngle", DoubleValue(gnbBearingRad));
    nrHelper->SetGnbAntennaAttribute("AntennaElement", PointerValue(gnbPanelElement));

    // ---- Spectrum: 1 CC / 1 BWP ----
    // Um carrier component e um bandwidth part representam uma celula NR simples.
    // O canal 3GPP UMi modela propagacao urbana micro com shadowing configuravel.
    CcBwpCreator ccBwpCreator;
    CcBwpCreator::SimpleOperationBandConf bandConf(centralFrequency, bandwidth, 1);
    bandConf.m_numBwp = 1;
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

    Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper>();
    channelHelper->ConfigureFactories("UMi", "Default", "ThreeGpp");
    channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(shadowingEnabled));
    channelHelper->AssignChannelsToBands({band});

    BandwidthPartInfoPtrVector allBwps = CcBwpCreator::GetAllBwps({band});

    // ---- Internet stack ----
    InternetStackHelper internet;
    internet.Install(remoteHostContainer);
    internet.Install(ueNodes);

    // ---- Install NR devices ----
    NetDeviceContainer gnbNetDev = nrHelper->InstallGnbDevice(gNbNodes, allBwps);
    NetDeviceContainer ueNetDev = nrHelper->InstallUeDevice(ueNodes, allBwps);

    int64_t randomStream = seed;
    randomStream += nrHelper->AssignStreams(gnbNetDev, randomStream);
    randomStream += nrHelper->AssignStreams(ueNetDev, randomStream);

    // ---- PHY configuration ----
    nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)->SetAttribute("Numerology", UintegerValue(numerology));
    nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)->SetAttribute("TxPower", DoubleValue(txPowerDbm));
    nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)->SetAttribute("NoiseFigure", DoubleValue(gnbNoiseFigureDb));
    nrHelper->GetGnbPhy(gnbNetDev.Get(0), 0)->SetPattern(appliedTddPattern);
    for (uint32_t i = 0; i < ueNetDev.GetN(); ++i)
    {
        nrHelper->GetUePhy(ueNetDev.Get(i), 0)->SetPattern(appliedTddPattern);
    }

    // ---- EPC backhaul ----
    // Link P2P de alta capacidade para que o gargalo relevante seja a RAN/scheduler,
    // nao o core/backhaul entre remoteHost e PGW.
    Ptr<Node> pgw = epcHelper->GetPgwNode();
    PointToPointHelper p2ph;
    p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("100Gbps")));
    p2ph.SetDeviceAttribute("Mtu", UintegerValue(2500));
    p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(0.001)));
    NetDeviceContainer internetDevices = p2ph.Install(pgw, remoteHostContainer.Get(0));

    Ipv4AddressHelper ipv4h;
    ipv4h.SetBase("1.0.0.0", "255.0.0.0");
    Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(internetDevices);

    Ipv4StaticRoutingHelper ipv4RoutingHelper;
    Ptr<Ipv4StaticRouting> remoteStatic =
        ipv4RoutingHelper.GetStaticRouting(remoteHostContainer.Get(0)->GetObject<Ipv4>());
    remoteStatic->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);

    Ipv4InterfaceContainer ueIpIfaces = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueNetDev));
    for (uint32_t i = 0; i < ueNodes.GetN(); ++i)
    {
        Ptr<Ipv4StaticRouting> ueStatic =
            ipv4RoutingHelper.GetStaticRouting(ueNodes.Get(i)->GetObject<Ipv4>());
        ueStatic->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);
    }

    // ---- Attach UEs ----
    nrHelper->AttachToClosestGnb(ueNetDev, gnbNetDev);

    // ---- Configure the RSLAQ Meta-Scheduler when a slice-aware mode is selected ----
    Ptr<NrMacScheduler> schedBase = NrHelper::GetScheduler(gnbNetDev.Get(0), 0);
    Ptr<RslaqMacScheduler> scheduler = DynamicCast<RslaqMacScheduler>(schedBase);
    if (g_useSliceScheduler)
    {
        NS_ASSERT_MSG(scheduler != nullptr, "Failed to cast to RslaqMacScheduler");
        g_schedulerPtr = scheduler;

        scheduler->SetScenarioName(scenarioName);
        scheduler->SetOutputDir(outputDir);

        // Configure MAC logging attributes
        scheduler->SetAttribute("LogAllMacSlots", BooleanValue(logAllMacSlots));
        scheduler->SetAttribute("MacLoggingPeriodMs", UintegerValue(macLoggingPeriodMs));
        scheduler->SetAttribute("EnableDetailedMacLogging", BooleanValue(true));
    }
    else
    {
        NS_ASSERT_MSG(scheduler == nullptr, "Pure baseline unexpectedly installed RslaqMacScheduler");
        g_schedulerPtr = nullptr;
    }

    // Mapeamento RNTI real pós-attach
    // O scheduler trabalha com RNTI, mas o gerador de trafego e o FlowMonitor usam
    // UE ID/porta. Este callback une UE ID, IMSI, RNTI, IP, porta e slice.
    double mappingTime = std::min(0.1, appStartSec - 0.05);
    if (mappingTime < 0.0)
        mappingTime = 0.05;

    Simulator::Schedule(Seconds(mappingTime), [scheduler, ueNetDev, &p_j, &sliceAlgos, &sliceWeightPolicy, &scenarioName, &outputDir, &ueIpIfaces]() {
        std::vector<std::vector<uint32_t>> sliceRntis(NUM_SLICES);
        std::cout << "\n=== UE Mapping (RNTI real após attach) ===\n"
                  << std::setw(4) << "Idx" << " | "
                  << std::setw(6) << "IMSI" << " | "
                  << std::setw(6) << "RNTI" << " | "
                  << std::setw(8) << "SliceId" << " | "
                  << std::setw(8) << "SliceType" << "\n"
                  << "-------------------------------------------\n";

        // Write UE/RNTI mapping CSV
        std::string mappingPrefix = outputDir;
        if (!mappingPrefix.empty() && mappingPrefix.back() != '/')
        {
            mappingPrefix += '/';
        }
        std::string mappingPath = mappingPrefix + scenarioName + "_ue_rnti_mapping.csv";
        std::ofstream mappingFile(mappingPath, std::ios::out | std::ios::trunc);
        mappingFile << "scenario,ueId,imsi,rnti,sliceId,sliceName,ip,port\n";

        for (uint32_t i = 0; i < ueNetDev.GetN(); ++i)
        {
            uint16_t ueId = static_cast<uint16_t>(i + 1);
            SliceType slice = GetSliceForUe(ueId);
            uint32_t sliceIdx = static_cast<uint32_t>(slice);
            uint16_t port = 12000 + ueId; // baseDlPort + ueId

            Ptr<NrUeNetDevice> ueDev = DynamicCast<NrUeNetDevice>(ueNetDev.Get(i));
            uint16_t rnti = UINT16_MAX;
            uint64_t imsi = 0;
            if (ueDev)
            {
                if (ueDev->GetRrc())
                {
                    rnti = ueDev->GetRrc()->GetRnti();
                }
                imsi = ueDev->GetImsi();
            }

            if (rnti == UINT16_MAX || rnti == 0)
            {
                std::cerr << "WARNING: UE " << ueId
                          << " ainda não possui RNTI válido no momento do mapeamento!\n";
            }

            sliceRntis[sliceIdx].push_back(rnti);
            g_ueToSlice[ueId] = slice;
            g_ueIdToRnti[ueId] = rnti;

            std::cout << std::setw(4) << ueId << " | "
                      << std::setw(6) << imsi << " | "
                      << std::setw(6) << rnti << " | "
                      << std::setw(8) << sliceIdx << " | "
                      << std::setw(8) << SliceName(slice) << "\n";

            // Write to mapping CSV
            Ipv4Address ueAddr = ueIpIfaces.GetAddress(i);
            mappingFile << scenarioName << "," << ueId << "," << imsi << "," << rnti << ","
                       << sliceIdx << "," << SliceName(slice) << "," << ueAddr << "," << port << "\n";
        }
        mappingFile.close();
        std::cout << "==========================================\n";
        std::cout << "UE/RNTI mapping written to: " << mappingPath << "\n\n";

        if (scheduler)
        {
            scheduler->SetSliceUeMapping(NUM_SLICES, sliceRntis);
            scheduler->SetSliceWeightPolicy(sliceWeightPolicy);
            scheduler->SetSliceConfiguration(p_j, sliceAlgos);
        }
    });

    // ---- Applications (DL traffic) ----
    // Para cada UE, instala-se um UdpServer no UE e um OnOff UDP no remoteHost.
    // Cada porta identifica unicamente um UE e permite recuperar o slice via mapa.
    ApplicationContainer serverApps;
    ApplicationContainer clientApps;
    std::map<uint16_t, uint16_t> portToUeId;

    for (uint32_t i = 0; i < ueNetDev.GetN(); ++i)
    {
        uint16_t ueId = static_cast<uint16_t>(i + 1);
        SliceType slice = GetSliceForUe(ueId);
        uint16_t port = baseDlPort + ueId;
        Ipv4Address ueAddr = ueIpIfaces.GetAddress(i);

        portToUeId[port] = ueId;
        g_ueToSlice[ueId] = slice;

        UdpServerHelper serverHelper(port);
        serverApps.Add(serverHelper.Install(ueNodes.Get(i)));

        uint64_t sliceRateBps = RateForSlice(scenario, slice) / NumUesPerSlice(slice);
        uint32_t pktSize = PktSizeForSlice(scenario, slice);

        OnOffHelper onOff("ns3::UdpSocketFactory", InetSocketAddress(ueAddr, port));
        onOff.SetConstantRate(DataRate(sliceRateBps), pktSize);
        clientApps.Add(onOff.Install(remoteHostContainer.Get(0)));

        std::cout << "UE " << std::setw(2) << ueId
                  << " [" << std::setw(4) << SliceName(slice) << "]"
                  << " port=" << port
                  << " rate=" << std::setw(10) << std::fixed << std::setprecision(2)
                  << static_cast<double>(sliceRateBps) / 1e6 << " Mbps"
                  << " pkt=" << pktSize << " B\n";
    }
    g_portToUeId = portToUeId;

    serverApps.Start(Seconds(appStartSec));
    clientApps.Start(Seconds(appStartSec));
    serverApps.Stop(Seconds(simTimeSec));
    clientApps.Stop(Seconds(simTimeSec - drainTimeSec));

    // ---- Flow Monitor ----
    FlowMonitorHelper flowmonHelper;
    NodeContainer endpointNodes;
    endpointNodes.Add(remoteHostContainer);
    endpointNodes.Add(ueNodes);
    Ptr<FlowMonitor> monitor = flowmonHelper.Install(endpointNodes);
    monitor->SetAttribute("DelayBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("JitterBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("PacketSizeBinWidth", DoubleValue(20));
    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());

    g_monitorPtr = monitor;
    g_classifierPtr = classifier;

    // ---- Initialize baseline stats ----
    g_baseline.outputDir = outputDir;
    g_baseline.indicationPeriodMs = indicationPeriodMs;
    g_baseline.activeDurationSec = simTimeSec - drainTimeSec - appStartSec;
    g_baseline.sliceStats[SliceType::EMBB] = SliceAggStats();
    g_baseline.sliceStats[SliceType::URLLC] = SliceAggStats();
    g_baseline.sliceStats[SliceType::MTC] = SliceAggStats();
    for (uint32_t i = 0; i < numUeTotal; i++)
    {
        uint16_t ueId = static_cast<uint16_t>(i + 1);
        SliceType slice = GetSliceForUe(ueId);
        g_baseline.ueStats[ueId].ueId = ueId;
        g_baseline.ueStats[ueId].slice = slice;
    }

    // ---- Schedule callbacks ----
    Time firstCallback = Seconds(appStartSec) + MilliSeconds(indicationPeriodMs);
    Simulator::Schedule(firstCallback, &StatsCallback);

    if (g_ipcEnabled)
    {
        Simulator::Schedule(firstCallback, &KpmAndControlCallback);
        std::cout << "[RslaqSim] IPC callback scheduled at t=" << firstCallback.GetMilliSeconds() << " ms\n";
    }

    // ---- Run ----
    Simulator::Stop(Seconds(simTimeSec));
    Simulator::Run();

    // ---- Final stats ----
    if (g_baseline.statsFile.is_open())
    {
        g_baseline.statsFile.close();
    }

    monitor->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer finalStats = monitor->GetFlowStats();

    std::map<SliceType, std::vector<double>> throughputSamplesBySlice;
    for (const auto& kv : g_baseline.sliceStats)
    {
        throughputSamplesBySlice[kv.first] = kv.second.throughputSamplesMbps;
    }

    // Zerar contadores finais sem perder as amostras temporais do summary.csv.
    g_baseline.sliceStats[SliceType::EMBB] = SliceAggStats();
    g_baseline.sliceStats[SliceType::URLLC] = SliceAggStats();
    g_baseline.sliceStats[SliceType::MTC] = SliceAggStats();
    for (const auto& kv : throughputSamplesBySlice)
    {
        g_baseline.sliceStats[kv.first].throughputSamplesMbps = kv.second;
    }

    for (const auto& kv : finalStats)
    {
        FlowId flowId = kv.first;
        const FlowMonitor::FlowStats& st = kv.second;
        Ipv4FlowClassifier::FiveTuple tuple = classifier->FindFlow(flowId);

        if (tuple.protocol != 17)
            continue;

        auto itPort = portToUeId.find(tuple.destinationPort);
        if (itPort == portToUeId.end())
            continue;

        uint16_t ueId = itPort->second;
        SliceType slice = g_ueToSlice[ueId];
        UeStats& ue = g_baseline.ueStats[ueId];
        SliceAggStats& sa = g_baseline.sliceStats[slice];

        ue.txBytes = st.txBytes;
        ue.rxBytes = st.rxBytes;
        ue.txPackets = st.txPackets;
        ue.rxPackets = st.rxPackets;
        ue.lostPackets = st.lostPackets;
        ue.delaySumSec = st.delaySum.GetSeconds();

        sa.txBytes += st.txBytes;
        sa.rxBytes += st.rxBytes;
        sa.txPackets += st.txPackets;
        sa.rxPackets += st.rxPackets;
        sa.lostPackets += st.lostPackets;
        sa.delaySumSec += st.delaySum.GetSeconds();
        sa.jitterSumSec += st.jitterSum.GetSeconds();
    }

    std::cout << "\n========================================\n"
              << "  RESULTS (" << scenario.name << ")\n"
              << "========================================\n";

    for (const auto& kv : g_baseline.sliceStats)
    {
        const SliceAggStats& m = kv.second;
        double thr = (g_baseline.activeDurationSec > 0)
                         ? static_cast<double>(m.rxBytes) * 8.0 / g_baseline.activeDurationSec / 1e6
                         : 0.0;
        double avgDelay = (m.rxPackets > 0) ? m.delaySumSec / m.rxPackets * 1000.0 : 0.0;
        double pdr = (m.txPackets > 0)
                         ? static_cast<double>(m.rxPackets) / m.txPackets
                         : 0.0;

        std::cout << SliceName(kv.first) << ":\n"
                  << "  Throughput : " << std::fixed << std::setprecision(4) << thr << " Mbps\n"
                  << "  Avg delay  : " << std::setprecision(3) << avgDelay << " ms\n"
                  << "  PDR        : " << std::setprecision(4) << pdr << "\n"
                  << "  TX/RX pkts : " << m.txPackets << " / " << m.rxPackets << "\n\n";
    }

    WriteSummaryCsv(outputDir, scenario, scenarioName, baselineMode);
    WriteMetadataJson(outputDir,
                      scenario,
                      baselineMode,
                      g_useSliceScheduler ? IntraAlgoName(sliceAlgos[0]) : "NA",
                      sliceAlgos,
                      seed,
                      run,
                      simTimeSec,
                      drainTimeSec,
                      p_j,
                      g_useSliceScheduler ? SliceWeightPolicyName(sliceWeightPolicy) : "NA",
                      duplexMode,
                      tddPattern,
                      appliedTddPattern,
                      rlcMode,
                      dlOnly,
                      embbSlaFeasible);

    std::cout << "CSV outputs:\n"
              << "  " << outputDir << "/timeseries.csv\n"
              << "  " << outputDir << "/slice_alloc.csv\n"
              << "  " << outputDir << "/summary.csv\n"
              << "  " << outputDir << "/metadata.json\n";

    // ---- Cleanup IPC ----
    if (g_ipcEnabled)
    {
        if (g_semMetricsReady)
        {
            sem_close(g_semMetricsReady);
            std::string name = "/sem_metrics_" + g_simUuid;
            sem_unlink(name.c_str());
        }
        if (g_semControl)
        {
            sem_close(g_semControl);
            std::string name = "/sem_control_" + g_simUuid;
            sem_unlink(name.c_str());
        }
        std::cout << "[RslaqSim] IPC semaphores cleaned up.\n";
    }

    Simulator::Destroy();
    return 0;
}
