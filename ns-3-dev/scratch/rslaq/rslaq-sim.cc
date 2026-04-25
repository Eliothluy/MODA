/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * RSLAQ Simulation — ns-3 / 5G-LENA
 *
 * Protótipo de scheduler slice-aware inspirado no artigo RSLAQ.
 * NÃO é o RSLAQ completo com DRL — nesta fase validamos apenas o
 * particionamento de RBGs por slice e o mapeamento RNTI → slice.
 *
 * Topologia: 1 gNB, N UEs (eMBB + URLLC + MTC configuráveis)
 * PHY: 2.59 GHz (n38), 10 MHz, numerologia mu=0 (SCS 15 kHz)
 *
 * Cenários de tráfego (DL):
 *   1 = Low traffic:  eMBB 50 Kbps  | URLLC 1 Mbps  | MTC 2 Mbps
 *   2 = Normal:       eMBB 70 Mbps  | URLLC 1 Mbps  | MTC 2 Mbps
 *   3 = Congestion:   eMBB 100 Mbps | URLLC 1 Mbps  | MTC 100 Mbps
 *   4 = Stressed:     eMBB 100 Mbps | URLLC 1 Mbps  | MTC 100 Mbps (SLA targets differ)
 *   5 = Insufficient: eMBB 100 Mbps | URLLC 2 Mbps  | MTC 100 Mbps
 */

#include "rslaq-mac-scheduler.h"

#include "ns3/antenna-module.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/nr-module.h"
#include "ns3/point-to-point-module.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("RslaqSim");

// ---------------------------------------------------------------------------
// Tipos e constantes
// ---------------------------------------------------------------------------

enum class SliceType : uint8_t
{
    EMBB = 0,
    URLLC = 1,
    MTC = 2
};

static const uint32_t NUM_SLICES = 3;

// Número de UEs por slice — podem ser sobrescritos via CommandLine
static uint32_t g_numUeEmbb = 5;
static uint32_t g_numUeUrllc = 5;
static uint32_t g_numUeMtc = 10;

struct ScenarioConfig
{
    std::string name;
    uint64_t embbRateBps;
    uint64_t urllcRateBps;
    uint64_t mtcRateBps;
    uint32_t embbPktSize;
    uint32_t urllcPktSize;
    uint32_t mtcPktSize;
};

struct UeStats
{
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
};

struct SliceAggStats
{
    uint64_t txBytes = 0;
    uint64_t rxBytes = 0;
    uint32_t txPackets = 0;
    uint32_t rxPackets = 0;
    uint32_t lostPackets = 0;
    double delaySumSec = 0.0;
    double jitterSumSec = 0.0;
};

// ---------------------------------------------------------------------------
// Estado global para o callback de estatísticas
// ---------------------------------------------------------------------------

struct SimState
{
    Ptr<FlowMonitor> monitor;
    Ptr<Ipv4FlowClassifier> classifier;
    std::map<uint16_t, UeStats> ueStats;
    std::map<SliceType, SliceAggStats> sliceStats;
    std::map<uint16_t, uint16_t> portToUeId;
    std::map<uint16_t, SliceType> ueToSlice;
    Ptr<RslaqMacScheduler> scheduler;
    double activeDurationSec;
    uint32_t indicationPeriodMs;
    std::string outputDir;
    std::ofstream statsFile;
    uint32_t stepCount{0};
};

static SimState g_sim;
static std::vector<double> g_sliceWeights;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

static std::map<std::string, ScenarioConfig>
InitScenarios()
{
    std::map<std::string, ScenarioConfig> m;
    m["low_traffic"] = {"low_traffic", 50000, 1000000, 2000000, 1500, 50, 100};
    m["normal"] = {"normal", 70000000, 1000000, 2000000, 1500, 50, 100};
    m["congestion"] = {"congestion", 100000000, 1000000, 100000000, 1500, 50, 100};
    m["stressed"] = {"stressed", 100000000, 1000000, 100000000, 1500, 50, 100};
    m["insufficient_resources"] = {"insufficient_resources", 100000000, 2000000, 100000000, 1500, 50, 100};
    return m;
}

// ---------------------------------------------------------------------------
// Callback de estatísticas (a cada 10 ms)
// ---------------------------------------------------------------------------

static void
StatsCallback()
{
    g_sim.monitor->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer stats = g_sim.monitor->GetFlowStats();
    uint64_t nowMs = static_cast<uint64_t>(Simulator::Now().GetMilliSeconds());
    g_sim.stepCount++;

    if (!g_sim.statsFile.is_open())
    {
        std::string path = g_sim.outputDir + "/rslaq_stats_timeseries.csv";
        g_sim.statsFile.open(path, std::ios::out | std::ios::trunc);
        g_sim.statsFile << "timestamp_ms,ue_id,slice,thr_mbps,btx,bfs_pct,tdp,rsh_pct\n";
    }

    for (const auto& kv : stats)
    {
        FlowId flowId = kv.first;
        const FlowMonitor::FlowStats& st = kv.second;
        Ipv4FlowClassifier::FiveTuple tuple = g_sim.classifier->FindFlow(flowId);

        if (tuple.protocol != 17)
        {
            continue;
        }

        auto itPort = g_sim.portToUeId.find(tuple.destinationPort);
        if (itPort == g_sim.portToUeId.end())
        {
            continue;
        }

        uint16_t ueId = itPort->second;
        SliceType slice = g_sim.ueToSlice[ueId];
        UeStats& ue = g_sim.ueStats[ueId];

        uint64_t dRxBytes = st.rxBytes - ue.prevRxBytes;
        uint64_t dTxBytes = st.txBytes - ue.prevTxBytes;
        uint32_t dTxPackets = st.txPackets - ue.prevTxPackets;
        uint32_t dLostPackets = st.lostPackets - ue.prevLostPackets;

        double periodSec = static_cast<double>(g_sim.indicationPeriodMs) / 1000.0;
        double thrMbps = (periodSec > 0) ? (static_cast<double>(dRxBytes) * 8.0 / periodSec / 1e6) : 0.0;
        double bfsPct = (dTxPackets > 0) ? (static_cast<double>(dLostPackets) / static_cast<double>(dTxPackets) * 100.0) : 0.0;
        (void)dTxBytes;

        int32_t sliceIdx = static_cast<int32_t>(slice);
        double rshPct = 0.0;
        if (g_sim.scheduler && sliceIdx >= 0)
        {
            rshPct = g_sim.scheduler->GetPrbWeight(static_cast<uint32_t>(sliceIdx)) * 100.0;
        }

        g_sim.statsFile << nowMs << "," << ueId << "," << SliceName(slice) << ","
                        << std::fixed << std::setprecision(4) << thrMbps << ","
                        << dTxBytes << ","
                        << std::setprecision(2) << bfsPct << ","
                        << dLostPackets << ","
                        << std::setprecision(2) << rshPct << "\n";

        ue.prevRxBytes = st.rxBytes;
        ue.prevTxBytes = st.txBytes;
        ue.prevRxPackets = st.rxPackets;
        ue.prevTxPackets = st.txPackets;
        ue.prevLostPackets = st.lostPackets;
        ue.prevDelaySumSec = st.delaySum.GetSeconds();

        ue.txBytes = st.txBytes;
        ue.rxBytes = st.rxBytes;
        ue.txPackets = st.txPackets;
        ue.rxPackets = st.rxPackets;
        ue.lostPackets = st.lostPackets;
        ue.delaySumSec = st.delaySum.GetSeconds();

        SliceAggStats& sa = g_sim.sliceStats[slice];
        sa.txBytes = st.txBytes;
        sa.rxBytes = st.rxBytes;
        sa.txPackets = st.txPackets;
        sa.rxPackets = st.rxPackets;
        sa.lostPackets = st.lostPackets;
        sa.delaySumSec = st.delaySum.GetSeconds();
        sa.jitterSumSec = st.jitterSum.GetSeconds();
    }

    g_sim.statsFile.flush();

    Simulator::Schedule(MilliSeconds(g_sim.indicationPeriodMs), &StatsCallback);
}

// ---------------------------------------------------------------------------
// CSV final (resumo pós-simulação)
// ---------------------------------------------------------------------------

static void
ConfigureSliceMapping(Ptr<RslaqMacScheduler> scheduler, NetDeviceContainer ueNetDev)
{
    std::vector<std::vector<uint32_t>> sliceRntis(NUM_SLICES);
    std::cout << "\n=== UE Mapping (RNTI real após attach) ===\n"
              << std::setw(4) << "Idx" << " | "
              << std::setw(6) << "IMSI" << " | "
              << std::setw(6) << "RNTI" << " | "
              << std::setw(8) << "SliceId" << " | "
              << std::setw(8) << "SliceType" << "\n"
              << "-------------------------------------------\n";

    for (uint32_t i = 0; i < ueNetDev.GetN(); ++i)
    {
        uint16_t ueId = static_cast<uint16_t>(i + 1);
        SliceType slice = GetSliceForUe(ueId);
        uint32_t sliceIdx = static_cast<uint32_t>(slice);

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
        g_sim.ueToSlice[ueId] = slice;

        std::cout << std::setw(4) << ueId << " | "
                  << std::setw(6) << imsi << " | "
                  << std::setw(6) << rnti << " | "
                  << std::setw(8) << sliceIdx << " | "
                  << std::setw(8) << SliceName(slice) << "\n";
    }
    std::cout << "==========================================\n\n";

    scheduler->SetSliceUeMapping(NUM_SLICES, sliceRntis);

    std::vector<RslaqMacScheduler::IntraSliceAlgorithm> defaultAlgos = {
        RslaqMacScheduler::IntraSliceAlgorithm::PF,
        RslaqMacScheduler::IntraSliceAlgorithm::PF,
        RslaqMacScheduler::IntraSliceAlgorithm::PF};
    scheduler->SetSliceConfiguration(g_sliceWeights, defaultAlgos);
}

static void
WriteFinalCsv(const std::string& prefix)
{
    {
        std::ofstream out(prefix + "_ue.csv", std::ios::out | std::ios::trunc);
        out << "ue_id,slice,tx_bytes,rx_bytes,tx_packets,rx_packets,lost_packets,"
            << "throughput_mbps,avg_delay_ms,pdr\n";
        for (const auto& kv : g_sim.ueStats)
        {
            const UeStats& m = kv.second;
            double thr = (g_sim.activeDurationSec > 0)
                             ? static_cast<double>(m.rxBytes) * 8.0 / g_sim.activeDurationSec / 1e6
                             : 0.0;
            double avgDelay = (m.rxPackets > 0) ? m.delaySumSec / m.rxPackets * 1000.0 : 0.0;
            double pdr = (m.txPackets > 0)
                             ? static_cast<double>(m.rxPackets) / m.txPackets
                             : 0.0;
            out << m.ueId << "," << SliceName(m.slice) << ","
                << m.txBytes << "," << m.rxBytes << ","
                << m.txPackets << "," << m.rxPackets << "," << m.lostPackets << ","
                << std::fixed << std::setprecision(4) << thr << ","
                << std::setprecision(3) << avgDelay << ","
                << std::setprecision(4) << pdr << "\n";
        }
    }

    {
        std::ofstream out(prefix + "_slice.csv", std::ios::out | std::ios::trunc);
        out << "slice,tx_bytes,rx_bytes,tx_packets,rx_packets,lost_packets,"
            << "throughput_mbps,avg_delay_ms,pdr\n";
        for (const auto& kv : g_sim.sliceStats)
        {
            const SliceAggStats& m = kv.second;
            double thr = (g_sim.activeDurationSec > 0)
                             ? static_cast<double>(m.rxBytes) * 8.0 / g_sim.activeDurationSec / 1e6
                             : 0.0;
            double avgDelay = (m.rxPackets > 0) ? m.delaySumSec / m.rxPackets * 1000.0 : 0.0;
            double pdr = (m.txPackets > 0)
                             ? static_cast<double>(m.rxPackets) / m.txPackets
                             : 0.0;
            out << SliceName(kv.first) << ","
                << m.txBytes << "," << m.rxBytes << ","
                << m.txPackets << "," << m.rxPackets << "," << m.lostPackets << ","
                << std::fixed << std::setprecision(4) << thr << ","
                << std::setprecision(3) << avgDelay << ","
                << std::setprecision(4) << pdr << "\n";
        }
    }
}

// ---------------------------------------------------------------------------
// Parse weights string "w0,w1,w2"
// ---------------------------------------------------------------------------

static std::vector<double>
ParseWeights(const std::string& str)
{
    std::vector<double> w;
    std::stringstream ss(str);
    std::string token;
    while (std::getline(ss, token, ','))
    {
        w.push_back(std::stod(token));
    }
    return w;
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int
main(int argc, char* argv[])
{
    auto scenarios = InitScenarios();

    std::string scenarioName = "normal";
    std::string outputDir = ".";
    uint32_t seed = 1;
    double simTimeSec = 4.0;
    double appStartSec = 0.4;
    uint32_t indicationPeriodMs = 10;
    std::string tddPattern = "D|D|D|D|D|D|D|D|D|D";
    double txPowerDbm = 43.0;
    std::string weightsStr = "0.3333,0.4000,0.2667";

    CommandLine cmd(__FILE__);
    cmd.AddValue("scenario", "1-5 or name", scenarioName);
    cmd.AddValue("simTime", "Total sim time (s)", simTimeSec);
    cmd.AddValue("appStart", "App start time (s)", appStartSec);
    cmd.AddValue("seed", "RNG seed", seed);
    cmd.AddValue("outputDir", "Output directory", outputDir);
    cmd.AddValue("periodMs", "Stats indication period (ms)", indicationPeriodMs);
    cmd.AddValue("tddPattern", "TDD slot pattern string", tddPattern);
    cmd.AddValue("txPower", "gNB TX power (dBm)", txPowerDbm);
    cmd.AddValue("embbUes", "Number of eMBB UEs", g_numUeEmbb);
    cmd.AddValue("urllcUes", "Number of URLLC UEs", g_numUeUrllc);
    cmd.AddValue("mtcUes", "Number of MTC UEs", g_numUeMtc);
    cmd.AddValue("weights", "Slice weights as comma-separated list (eMBB,URLLC,MTC)", weightsStr);
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
    const uint32_t numUeTotal = g_numUeEmbb + g_numUeUrllc + g_numUeMtc;

    std::vector<double> sliceWeights = ParseWeights(weightsStr);
    if (sliceWeights.size() != NUM_SLICES)
    {
        NS_FATAL_ERROR("Weights must have exactly " << NUM_SLICES << " elements");
    }
    double wsum = 0.0;
    for (double w : sliceWeights)
        wsum += w;
    if (std::abs(wsum - 1.0) > 1e-3)
    {
        NS_FATAL_ERROR("Weights must sum to 1.0 (got " << wsum << ")");
    }

    // Neste protótipo, p_j (proporção aplicada ao scheduler) = omega (peso político).
    // No RSLAQ completo, p_j seria ajustado pelo agente DRL a cada frame.
    std::vector<double> p_j = sliceWeights;

    const double centralFrequency = 2.59e9;
    const double bandwidth = 10e6;
    const uint16_t numerology = 0;
    const uint16_t baseDlPort = 12000;
    const double activeDurationSec = simTimeSec - appStartSec;

    std::cout << "========================================\n"
              << "  RSLAQ Simulation (Slice-Aware Proto)\n"
              << "========================================\n"
              << "Scenario     : " << scenario.name << "\n"
              << "Frequency    : " << centralFrequency / 1e9 << " GHz\n"
              << "Bandwidth    : " << bandwidth / 1e6 << " MHz\n"
              << "Numerology   : " << numerology << " (SCS 15 kHz)\n"
              << "UEs          : " << numUeTotal
              << " (eMBB=" << g_numUeEmbb
              << " URLLC=" << g_numUeUrllc
              << " MTC=" << g_numUeMtc << ")\n"
              << "SimTime      : " << simTimeSec << " s\n"
              << "TxPower      : " << txPowerDbm << " dBm\n"
              << "Stats period : " << indicationPeriodMs << " ms\n"
              << "Weights      : eMBB=" << p_j[0]
              << " URLLC=" << p_j[1]
              << " MTC=" << p_j[2] << "\n\n";

    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(1);

    Config::SetDefault("ns3::NrRlcUm::MaxTxBufferSize", UintegerValue(10485760));
    Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod", TimeValue(MilliSeconds(0)));

    // ---- Nodes ----
    NodeContainer gNbNodes;
    gNbNodes.Create(1);
    NodeContainer ueNodes;
    ueNodes.Create(numUeTotal);
    NodeContainer remoteHostContainer;
    remoteHostContainer.Create(1);

    // ---- Mobility ----
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    {
        Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
        pos->Add(Vector(0.0, 0.0, 10.0));
        mobility.SetPositionAllocator(pos);
        mobility.Install(gNbNodes);
    }
    {
        Ptr<RandomRectanglePositionAllocator> pos =
            CreateObject<RandomRectanglePositionAllocator>();
        pos->SetAttribute("X", StringValue("ns3::UniformRandomVariable[Min=-30|Max=30]"));
        pos->SetAttribute("Y", StringValue("ns3::UniformRandomVariable[Min=-30|Max=30]"));
        MobilityHelper ueMob;
        ueMob.SetPositionAllocator(pos);
        ueMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        ueMob.Install(ueNodes);
    }

    // ---- NR Helpers ----
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
    nrHelper->SetEpcHelper(epcHelper);

    nrHelper->SetSchedulerTypeId(RslaqMacScheduler::GetTypeId());

    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(1));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(1));
    nrHelper->SetUeAntennaAttribute("AntennaElement",
                                     PointerValue(CreateObject<IsotropicAntennaModel>()));
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(1));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(1));
    nrHelper->SetGnbAntennaAttribute("AntennaElement",
                                      PointerValue(CreateObject<IsotropicAntennaModel>()));

    // ---- Spectrum: 1 CC / 1 BWP ----
    CcBwpCreator ccBwpCreator;
    CcBwpCreator::SimpleOperationBandConf bandConf(centralFrequency, bandwidth, 1);
    bandConf.m_numBwp = 1;
    OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

    Ptr<NrChannelHelper> channelHelper = CreateObject<NrChannelHelper>();
    channelHelper->ConfigureFactories("UMi", "Default", "ThreeGpp");
    channelHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    channelHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(false));
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

    // ---- EPC backhaul ----
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

    // ---- Configure the RSLAQ Meta-Scheduler ----
    Ptr<NrMacScheduler> schedBase = NrHelper::GetScheduler(gnbNetDev.Get(0), 0);
    Ptr<RslaqMacScheduler> scheduler = DynamicCast<RslaqMacScheduler>(schedBase);
    NS_ASSERT_MSG(scheduler != nullptr, "Failed to cast to RslaqMacScheduler");

    // Capturar RNTIs reais após attach e configurar mapeamento + pesos.
    // O tráfego de aplicação só inicia em appStartSec (default 0.4 s),
    // então agendamos o mapeamento em 0.1 s para garantir RRC completo.
    double mappingTime = std::min(0.1, appStartSec - 0.05);
    if (mappingTime < 0.0)
        mappingTime = 0.05;

    g_sliceWeights = p_j;
    Simulator::Schedule(Seconds(mappingTime), &ConfigureSliceMapping, scheduler, ueNetDev);

    // ---- Applications (DL traffic) ----
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

    serverApps.Start(Seconds(appStartSec));
    clientApps.Start(Seconds(appStartSec));
    serverApps.Stop(Seconds(simTimeSec));
    clientApps.Stop(Seconds(simTimeSec));

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

    // ---- Populate global state ----
    g_sim.monitor = monitor;
    g_sim.classifier = classifier;
    g_sim.scheduler = scheduler;
    g_sim.activeDurationSec = activeDurationSec;
    g_sim.indicationPeriodMs = indicationPeriodMs;
    g_sim.outputDir = outputDir;
    g_sim.portToUeId = portToUeId;

    g_sim.sliceStats[SliceType::EMBB] = SliceAggStats();
    g_sim.sliceStats[SliceType::URLLC] = SliceAggStats();
    g_sim.sliceStats[SliceType::MTC] = SliceAggStats();

    for (uint32_t i = 0; i < numUeTotal; i++)
    {
        uint16_t ueId = static_cast<uint16_t>(i + 1);
        SliceType slice = GetSliceForUe(ueId);
        g_sim.ueToSlice[ueId] = slice;
        UeStats us;
        us.ueId = ueId;
        us.slice = slice;
        g_sim.ueStats[ueId] = us;
    }

    // ---- Schedule stats callback ----
    Time firstCallback = Seconds(appStartSec) + MilliSeconds(indicationPeriodMs);
    Simulator::Schedule(firstCallback, &StatsCallback);

    // ---- Run ----
    Simulator::Stop(Seconds(simTimeSec));
    Simulator::Run();

    // ---- Final stats ----
    if (g_sim.statsFile.is_open())
    {
        g_sim.statsFile.close();
    }

    monitor->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer finalStats = monitor->GetFlowStats();

    // Zerar slice stats para acumular corretamente
    g_sim.sliceStats[SliceType::EMBB] = SliceAggStats();
    g_sim.sliceStats[SliceType::URLLC] = SliceAggStats();
    g_sim.sliceStats[SliceType::MTC] = SliceAggStats();

    for (const auto& kv : finalStats)
    {
        FlowId flowId = kv.first;
        const FlowMonitor::FlowStats& st = kv.second;
        Ipv4FlowClassifier::FiveTuple tuple = classifier->FindFlow(flowId);

        if (tuple.protocol != 17)
        {
            continue;
        }

        auto itPort = portToUeId.find(tuple.destinationPort);
        if (itPort == portToUeId.end())
        {
            continue;
        }

        uint16_t ueId = itPort->second;
        SliceType slice = g_sim.ueToSlice[ueId];
        UeStats& ue = g_sim.ueStats[ueId];
        SliceAggStats& sa = g_sim.sliceStats[slice];

        ue.txBytes = st.txBytes;
        ue.rxBytes = st.rxBytes;
        ue.txPackets = st.txPackets;
        ue.rxPackets = st.rxPackets;
        ue.lostPackets = st.lostPackets;
        ue.delaySumSec = st.delaySum.GetSeconds();

        // Acumular deltas corretamente (não somar totais brutos do FlowMonitor)
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

    for (const auto& kv : g_sim.sliceStats)
    {
        const SliceAggStats& m = kv.second;
        double thr = (activeDurationSec > 0) ? static_cast<double>(m.rxBytes) * 8.0 / activeDurationSec / 1e6 : 0.0;
        double avgDelay = (m.rxPackets > 0) ? m.delaySumSec / m.rxPackets * 1000.0 : 0.0;
        double pdr = (m.txPackets > 0) ? static_cast<double>(m.rxPackets) / m.txPackets : 0.0;

        std::cout << SliceName(kv.first) << ":\n"
                  << "  Throughput : " << std::fixed << std::setprecision(4) << thr << " Mbps\n"
                  << "  Avg delay  : " << std::setprecision(3) << avgDelay << " ms\n"
                  << "  PDR        : " << std::setprecision(4) << pdr << "\n"
                  << "  TX/RX pkts : " << m.txPackets << " / " << m.rxPackets << "\n\n";
    }

    std::string prefix = outputDir + "/rslaq_" + scenario.name;
    WriteFinalCsv(prefix);

    std::cout << "CSV outputs:\n"
              << "  " << prefix << "_ue.csv\n"
              << "  " << prefix << "_slice.csv\n"
              << "  " << outputDir << "/rslaq_stats_timeseries.csv\n"
              << "  rslaq_slice_allocations.csv\n"
              << "  rslaq_unmapped_rntis.csv\n";

    Simulator::Destroy();
    return 0;
}
