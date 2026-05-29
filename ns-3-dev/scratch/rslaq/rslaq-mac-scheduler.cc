/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * RSLAQ Meta-Scheduler implementation for 5G-LENA (ns-3)
 *
 * Slice-aware OFDMA MAC scheduler with dynamic intra-slice algorithm
 * selection. Partitions PRBs across slices by configurable weights
 * and applies per-slice RR, PF, or BCQI ordering.
 */

#include "rslaq-mac-scheduler.h"

#include "ns3/nr-mac-scheduler-ue-info-pf.h"
#include "ns3/nr-mac-scheduler-ue-info-mr.h"
#include "ns3/nr-fh-control.h"

#include "ns3/log.h"
#include "ns3/simulator.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <set>
#include <sstream>

namespace ns3
{

NS_LOG_COMPONENT_DEFINE("RslaqMacScheduler");
NS_OBJECT_ENSURE_REGISTERED(RslaqMacScheduler);

TypeId
RslaqMacScheduler::GetTypeId()
{
    static TypeId tid =
        TypeId("ns3::RslaqMacScheduler")
            .SetParent<NrMacSchedulerOfdmaRR>()
            .AddConstructor<RslaqMacScheduler>()
            .AddAttribute("TimeWindow",
                          "PF averaging time window (in slots)",
                          DoubleValue(99.0),
                          MakeDoubleAccessor(&RslaqMacScheduler::m_timeWindow),
                          MakeDoubleChecker<double>(1.0))
            .AddAttribute("FairnessIndex",
                          "PF alpha parameter (0=full fairness, 1=throughput maximization)",
                          DoubleValue(0.0),
                          MakeDoubleAccessor(&RslaqMacScheduler::m_alpha),
                          MakeDoubleChecker<double>(0.0, 1.0))
            .AddAttribute("FallbackUnmappedUe",
                          "If true, unmapped UEs are forced into slice 0 (debug only)",
                          BooleanValue(false),
                          MakeBooleanAccessor(&RslaqMacScheduler::m_fallbackUnmappedToSlice0),
                          MakeBooleanChecker())
            .AddAttribute("LogAllMacSlots",
                          "If true, log every MAC scheduling call (use with caution, produces large files)",
                          BooleanValue(false),
                          MakeBooleanAccessor(&RslaqMacScheduler::m_logAllMacSlots),
                          MakeBooleanChecker())
            .AddAttribute("MacLoggingPeriodMs",
                          "Period of MAC logging in milliseconds when LogAllMacSlots is false",
                          UintegerValue(100),
                          MakeUintegerAccessor(&RslaqMacScheduler::m_macLoggingPeriodMs),
                          MakeUintegerChecker<uint32_t>(1))
            .AddAttribute("EnableDetailedMacLogging",
                          "If true, enable detailed MAC-level logging with call IDs and slot info",
                          BooleanValue(false),
                          MakeBooleanAccessor(&RslaqMacScheduler::m_enableDetailedMacLogging),
                          MakeBooleanChecker());
    return tid;
}

RslaqMacScheduler::RslaqMacScheduler()
    : NrMacSchedulerOfdmaRR()
{
    NS_LOG_FUNCTION(this);
}

RslaqMacScheduler::~RslaqMacScheduler()
{
}

bool
RslaqMacScheduler::ShouldLogSlot(uint64_t timeMs) const
{
    if (m_logAllMacSlots)
    {
        return true;
    }
    if (m_enableDetailedMacLogging)
    {
        if (timeMs - m_lastLoggedMs >= m_macLoggingPeriodMs)
        {
            m_lastLoggedMs = timeMs;
            return true;
        }
        return false;
    }
    return (timeMs <= 200) || ((timeMs + 37) % 97 < 2);
}

uint32_t
RslaqMacScheduler::GetCurrentSlot() const
{
    return m_currentSlot;
}

uint32_t
RslaqMacScheduler::GetBwpId() const
{
    return m_bwpId;
}

uint64_t
RslaqMacScheduler::GetNextCallId() const
{
    return ++m_dlSchedCallSeq;
}

void
RslaqMacScheduler::SetCurrentSlot(uint32_t slot)
{
    m_currentSlot = slot;
}

void
RslaqMacScheduler::SetBwpId(uint32_t bwpId)
{
    m_bwpId = bwpId;
}

void
RslaqMacScheduler::SetSliceConfiguration(const std::vector<double>& prbWeights,
                                          const std::vector<IntraSliceAlgorithm>& algorithms)
{
    /*
     * Runtime control point used by both static baselines and the Python agent.
     * prbWeights is the slice share vector [eMBB, URLLC, MTC]; algorithms stores
     * the intra-slice policy applied after each slice receives its RBG budget.
     */
    NS_LOG_FUNCTION(this);
    NS_ASSERT_MSG(prbWeights.size() == algorithms.size(), "Weights and algorithms must have same size");
    NS_ASSERT_MSG(prbWeights.size() == m_numSlices, "Must match configured number of slices");

    double sum = std::accumulate(prbWeights.begin(), prbWeights.end(), 0.0);
    NS_ASSERT_MSG(std::abs(sum - 1.0) < 1e-6,
                  "PRB weights must sum to 1.0, got " << sum);

    m_prbWeights = prbWeights;
    m_intraAlgorithms = algorithms;

    std::ostringstream oss;
    oss << "[RslaqScheduler] Updated config:";
    for (uint32_t s = 0; s < m_numSlices; s++)
    {
        oss << " Slice" << s << "(w=" << m_prbWeights[s];
        switch (m_intraAlgorithms[s])
        {
        case IntraSliceAlgorithm::RR:
            oss << ",RR";
            break;
        case IntraSliceAlgorithm::PF:
            oss << ",PF";
            break;
        case IntraSliceAlgorithm::BCQI:
            oss << ",BCQI";
            break;
        }
        oss << ")";
    }
    NS_LOG_INFO(oss.str());
}

void
RslaqMacScheduler::SetSliceUeMapping(uint32_t numSlices,
                                      const std::vector<std::vector<uint32_t>>& sliceUeRnti)
{
    /*
     * Called once after attach, when real RNTIs are known. The simulator maps
     * UE IDs to slices, but the MAC scheduler receives active users by RNTI.
     */
    NS_LOG_FUNCTION(this);
    m_numSlices = numSlices;
    m_sliceUeRnti = sliceUeRnti;
    NS_ASSERT_MSG(m_numSlices == 3, "RSLAQ experiments require exactly 3 slices");

    m_prbWeights.resize(m_numSlices, 1.0 / m_numSlices);
    m_intraAlgorithms.resize(m_numSlices, IntraSliceAlgorithm::RR);
    m_sliceAllocationStats.assign(m_numSlices, SliceAllocationStats());

    for (uint32_t s = 0; s < m_numSlices; s++)
    {
        std::ostringstream oss;
        oss << "[RslaqScheduler] Slice " << s << " RNTIs:";
        for (uint32_t rnti : m_sliceUeRnti[s])
        {
            oss << " " << rnti;
        }
        NS_LOG_INFO(oss.str());
    }
}

uint32_t
RslaqMacScheduler::GetNumSlices() const
{
    return m_numSlices;
}

double
RslaqMacScheduler::GetPrbWeight(uint32_t sliceIdx) const
{
    NS_ASSERT(sliceIdx < m_numSlices);
    return m_prbWeights[sliceIdx];
}

RslaqMacScheduler::IntraSliceAlgorithm
RslaqMacScheduler::GetIntraAlgorithm(uint32_t sliceIdx) const
{
    NS_ASSERT(sliceIdx < m_numSlices);
    return m_intraAlgorithms[sliceIdx];
}

int32_t
RslaqMacScheduler::GetSliceIndexForRnti(uint16_t rnti) const
{
    for (uint32_t s = 0; s < m_numSlices; s++)
    {
        for (uint32_t r : m_sliceUeRnti[s])
        {
            if (r == rnti)
            {
                return static_cast<int32_t>(s);
            }
        }
    }
    return -1;
}

void
RslaqMacScheduler::DumpSliceConfiguration() const
{
    std::ostringstream oss;
    oss << "[RslaqScheduler] DumpSliceConfiguration: numSlices=" << m_numSlices;
    for (uint32_t s = 0; s < m_numSlices; s++)
    {
        oss << " | Slice" << s << " w=" << m_prbWeights[s] << " alg=";
        switch (m_intraAlgorithms[s])
        {
        case IntraSliceAlgorithm::RR:
            oss << "RR";
            break;
        case IntraSliceAlgorithm::PF:
            oss << "PF";
            break;
        case IntraSliceAlgorithm::BCQI:
            oss << "BCQI";
            break;
        }
        oss << " rntis=[";
        for (size_t i = 0; i < m_sliceUeRnti[s].size(); ++i)
        {
            if (i)
                oss << ",";
            oss << m_sliceUeRnti[s][i];
        }
        oss << "]";
    }
    NS_LOG_INFO(oss.str());
}

void
RslaqMacScheduler::SetScenarioName(const std::string& name)
{
    m_scenarioName = name;
}

void
RslaqMacScheduler::SetOutputDir(const std::string& dir)
{
    m_outputDir = dir;
}

void
RslaqMacScheduler::OpenCsvFiles() const
{
    std::string prefix = m_outputDir;
    if (!prefix.empty() && prefix.back() != '/')
    {
        prefix += '/';
    }
    if (!m_sliceAllocCsv.is_open())
    {
        std::string path = prefix + "slice_alloc.csv";
        m_sliceAllocCsv.open(path, std::ios::out | std::ios::trunc);
        m_sliceAllocCsv << "timestamp_ms,slice,configured_weight,budget_rbg,allocated_rbg,"
                           "total_allocated_rbg,rsh_real_pct,budget_utilization_pct,"
                           "unused_budget_pct,allocation_fidelity_pct,active_ues,effective_weight,"
                           "beam_id,has_demand,reason,redistributed_idle_rbg,rntis\n";
        m_sliceAllocCsv.flush();
    }
    if (!m_unmappedRntiCsv.is_open())
    {
        std::string path = prefix + "unmapped_rntis.csv";
        m_unmappedRntiCsv.open(path, std::ios::out | std::ios::trunc);
        // Header with scenario field
        m_unmappedRntiCsv << "callId,timeMs,scenario,rnti,reason\n";
        m_unmappedRntiCsv.flush();
    }
    if (!m_ueAllocCsv.is_open())
    {
        std::string path = prefix + "ue_detail.csv";
        m_ueAllocCsv.open(path, std::ios::out | std::ios::trunc);
        // Header with new fields: callId, slot, bwpId, beamId, tbSizeBytes, reason
        m_ueAllocCsv << "callId,timeMs,scenario,slot,bwpId,beamId,sliceId,rnti,bufQueueSize,"
                           "dlTbSizeBefore,hasDemand,demandPassed,rbgAllocated,uniqueRbgs,"
                           "tbSizeBytes,mcs,rank,numRbPerRbg,reason\n";
        m_ueAllocCsv.flush();
    }
    if (!m_harqTrackingCsv.is_open())
    {
        std::string path = prefix + "harq_tracking.csv";
        m_harqTrackingCsv.open(path, std::ios::out | std::ios::trunc);
        m_harqTrackingCsv << "callId,timeMs,scenario,sliceId,rnti,activeHarqCount,"
                             "harqCapacity,canInsert,dlBufferSize,beamId\n";
        m_harqTrackingCsv.flush();
    }
    if (!m_activeDlDiagCsv.is_open())
    {
        std::string path = prefix + "active_dl_diag.csv";
        m_activeDlDiagCsv.open(path, std::ios::out | std::ios::trunc);
        m_activeDlDiagCsv << "callId,timeMs,scenario,sliceId,rnti,inActiveDl,dlBufferSize,"
                             "canInsertHarq,harqActiveCount,diagReason\n";
        m_activeDlDiagCsv.flush();
    }
}

std::shared_ptr<NrMacSchedulerUeInfo>
RslaqMacScheduler::CreateUeRepresentation(
    const NrMacCschedSapProvider::CschedUeConfigReqParameters& params) const
{
    NS_LOG_FUNCTION(this);
    return std::make_shared<NrMacSchedulerUeInfoPF>(
        static_cast<float>(m_alpha),
        params.m_rnti,
        params.m_beamId,
        std::bind(&RslaqMacScheduler::GetNumRbPerRbg, this));
}

void
RslaqMacScheduler::SortUeVectorByAlgorithm(std::vector<UePtrAndBufferReq>& ueVector,
                                            IntraSliceAlgorithm algo) const
{
    switch (algo)
    {
    case IntraSliceAlgorithm::RR:
        std::stable_sort(ueVector.begin(), ueVector.end(),
                         NrMacSchedulerUeInfoRR::CompareUeWeightsDl);
        break;
    case IntraSliceAlgorithm::PF:
        std::stable_sort(ueVector.begin(), ueVector.end(),
                         NrMacSchedulerUeInfoPF::CompareUeWeightsDl);
        break;
    case IntraSliceAlgorithm::BCQI:
        std::stable_sort(ueVector.begin(), ueVector.end(),
                         NrMacSchedulerUeInfoMR::CompareUeWeightsDl);
        break;
    }
}

std::set<uint16_t>
RslaqMacScheduler::CollectActiveRntis(const ActiveUeMap& activeDl) const
{
    std::set<uint16_t> rntis;
    for (const auto& beam : activeDl)
    {
        for (const auto& ue : beam.second)
        {
            rntis.insert(ue.first->m_rnti);
        }
    }
    return rntis;
}

uint32_t
RslaqMacScheduler::GetUeDlBufferSize(uint16_t rnti) const
{
    auto it = m_lastDlBufferSize.find(rnti);
    return (it != m_lastDlBufferSize.end()) ? it->second : 0;
}

std::vector<RslaqMacScheduler::SliceAllocationStats>
RslaqMacScheduler::GetSliceAllocationStats() const
{
    return m_sliceAllocationStats;
}

void
RslaqMacScheduler::LogActiveDlDiagnostic(uint64_t callId, uint64_t timeMs,
                                          const ActiveUeMap& activeDl) const
{
    if (!m_activeDlDiagCsv.is_open())
    {
        return;
    }

    std::set<uint16_t> activeRntis = CollectActiveRntis(activeDl);

    std::map<uint16_t, uint32_t> activeRntiBufSize;
    for (const auto& beam : activeDl)
    {
        for (const auto& ue : beam.second)
        {
            activeRntiBufSize[ue.first->m_rnti] = ue.second;
        }
    }

    for (uint32_t s = 0; s < m_numSlices; s++)
    {
        for (uint32_t rnti : m_sliceUeRnti[s])
        {
            uint16_t r = static_cast<uint16_t>(rnti);
            bool inActiveDl = activeRntis.count(r) > 0;
            uint32_t bufSize = inActiveDl ? activeRntiBufSize[r] : 0;

            std::string reason;
            if (inActiveDl)
            {
                reason = "in_active_dl";
            }
            else
            {
                reason = "not_in_active_dl";
            }

            m_activeDlDiagCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                              << s << "," << r << "," << (inActiveDl ? 1 : 0) << ","
                              << bufSize << "," << 0 << ","
                              << 0 << "," << reason << "\n";
        }
    }
    m_activeDlDiagCsv.flush();
}

void
RslaqMacScheduler::LogHarqState(uint64_t callId, uint64_t timeMs) const
{
}

NrMacSchedulerNs3::BeamSymbolMap
RslaqMacScheduler::AssignDLRBG(uint32_t symAvail, const ActiveUeMap& activeDl) const
{
    /*
     * Core slice-aware allocation loop:
     * 1. Group active DL UEs by their configured slice RNTI mapping.
     * 2. Detect which slices currently have downlink demand.
     * 3. Redistribute the available RBG budget only among active-demand slices.
     * 4. Sort UEs inside each slice by RR/PF/BCQI and allocate RBGs round-robin.
     * 5. Export per-slice and per-UE diagnostics for later reward/analysis.
     */
    NS_LOG_FUNCTION(this);
    NS_LOG_DEBUG("AssignDLRBG: #beams=" << activeDl.size() << " symAvail=" << symAvail);

    if (m_firstRun)
    {
        m_firstRun = false;
        OpenCsvFiles();
        DumpSliceConfiguration();
    }

    GetFirst GetBeamId;
    GetSecond GetUeVector;
    BeamSymbolMap symPerBeam = GetSymPerBeam(symAvail, activeDl);

    uint64_t timeMs = Simulator::Now().GetMilliSeconds();
    uint64_t callId = GetNextCallId();
    bool logThisSlot = ShouldLogSlot(timeMs);

    if (logThisSlot)
    {
        LogActiveDlDiagnostic(callId, timeMs, activeDl);
        LogHarqState(callId, timeMs);
    }

    // Helper to serialize BeamId to string
    auto beamIdToStr = [](const BeamId& bid) -> std::string {
        std::ostringstream oss;
        oss << bid.GetSector() << "_" << bid.GetElevation();
        return oss.str();
    };

    for (const auto& el : activeDl)
    {
        BeamId beamId = GetBeamId(el);
        uint32_t beamSym = symPerBeam.at(beamId);
        const std::vector<bool> dlNotchedMask = GetDlNotchedRbgMask();
        std::string beamIdStr = beamIdToStr(beamId);

        std::vector<uint32_t> availableRbgIds;
        if (!dlNotchedMask.empty())
        {
            for (uint32_t i = 0; i < dlNotchedMask.size(); ++i)
            {
                if (dlNotchedMask[i])
                {
                    availableRbgIds.push_back(i);
                }
            }
        }
        else
        {
            uint32_t bwRbg = GetBandwidthInRbg();
            availableRbgIds.reserve(bwRbg);
            for (uint32_t i = 0; i < bwRbg; ++i)
            {
                availableRbgIds.push_back(i);
            }
        }

        uint32_t totalRbgs = static_cast<uint32_t>(availableRbgIds.size());
        NS_ASSERT(totalRbgs > 0);

        std::vector<bool> rbgRealUsed(GetBandwidthInRbg(), false);
        if (!dlNotchedMask.empty())
        {
            for (uint32_t i = 0; i < dlNotchedMask.size(); ++i)
            {
                if (!dlNotchedMask[i])
                {
                    rbgRealUsed[i] = true;
                }
            }
        }

        FTResources assigned(0, 0);

        std::vector<std::vector<UePtrAndBufferReq>> sliceUeVec(m_numSlices);
        std::vector<uint16_t> unmappedRntis;
        for (const auto& ue : GetUeVector(el))
        {
            uint16_t rnti = ue.first->m_rnti;
            int32_t sIdx = GetSliceIndexForRnti(rnti);
            if (sIdx >= 0)
            {
                sliceUeVec[static_cast<uint32_t>(sIdx)].emplace_back(ue);
            }
            else
            {
                NS_LOG_WARN("[RslaqScheduler] RNTI " << rnti << " not found in any slice!");
                unmappedRntis.push_back(rnti);
                if (m_unmappedRntiCsv.is_open())
                {
                    m_unmappedRntiCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                                     << rnti << ",not_in_any_slice\n";
                }
                if (m_fallbackUnmappedToSlice0 && m_numSlices > 0)
                {
                    sliceUeVec[0].emplace_back(ue);
                }
            }
        }

        std::vector<bool> sliceHasDemand(m_numSlices, false);
        double activeWeightSum = 0.0;
        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            if (sliceUeVec[s].empty())
            {
                continue;
            }
            bool demand = false;
            for (const auto& ue : sliceUeVec[s])
            {
                uint32_t bufQueueSize = ue.second;
                // Condição mais flexível: considera UE ativo se houver qualquer buffer
                // OU se estiver recebendo dados (detecção de atividade de tráfego)
                if (bufQueueSize > 0 || ue.first->m_dlTbSize > 0)
                {
                    demand = true;
                    break;
                }
            }
            if (demand)
            {
                sliceHasDemand[s] = true;
                activeWeightSum += m_prbWeights[s];
            }
        }

        std::vector<double> effectiveWeight(m_numSlices, 0.0);
        std::vector<uint32_t> sliceRbgBudget(m_numSlices, 0);
        if (activeWeightSum > 0.0)
        {
            struct BudgetCandidate
            {
                uint32_t slice = 0;
                double remainder = 0.0;
            };
            std::vector<BudgetCandidate> candidates;
            uint32_t budgetSum = 0;
            for (uint32_t s = 0; s < m_numSlices; s++)
            {
                if (!sliceHasDemand[s])
                {
                    continue;
                }
                effectiveWeight[s] = m_prbWeights[s] / activeWeightSum;
                double rawBudget = static_cast<double>(totalRbgs) * effectiveWeight[s];
                double floored = std::floor(rawBudget);
                sliceRbgBudget[s] = static_cast<uint32_t>(floored);
                budgetSum += sliceRbgBudget[s];
                candidates.push_back({s, rawBudget - floored});
            }

            NS_ASSERT_MSG(budgetSum <= totalRbgs, "Floor budgets exceeded total RBGs");
            uint32_t remaining = totalRbgs - budgetSum;
            uint32_t rotation = (static_cast<uint32_t>(timeMs) + m_currentSlot) % m_numSlices;
            std::stable_sort(candidates.begin(),
                             candidates.end(),
                             [rotation, this](const BudgetCandidate& a, const BudgetCandidate& b) {
                                 if (std::abs(a.remainder - b.remainder) > 1e-12)
                                 {
                                     return a.remainder > b.remainder;
                                 }
                                 uint32_t ar = (a.slice + m_numSlices - rotation) % m_numSlices;
                                 uint32_t br = (b.slice + m_numSlices - rotation) % m_numSlices;
                                 return ar < br;
                             });

            for (uint32_t i = 0; i < remaining && i < candidates.size(); ++i)
            {
                sliceRbgBudget[candidates[i].slice] += 1;
            }
        }

        uint32_t budgetTotal = std::accumulate(sliceRbgBudget.begin(), sliceRbgBudget.end(), 0u);
        NS_ASSERT_MSG(activeWeightSum <= 0.0 || budgetTotal == totalRbgs,
                      "sum(sliceBudgetRbg)=" << budgetTotal << " totalRbgs=" << totalRbgs);

        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            for (auto& ue : sliceUeVec[s])
            {
                BeforeDlSched(ue, FTResources(totalRbgs, beamSym));
            }
        }

        std::vector<uint32_t> sliceAllocatedVec(m_numSlices, 0);
        std::vector<std::string> sliceReasonVec(m_numSlices);
        std::vector<std::string> sliceRntiListVec(m_numSlices);

        // --- Slice-by-slice allocation with diagnostic logging ---
        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            std::string reason;
            uint32_t sliceAllocated = 0;

            if (sliceUeVec[s].empty())
            {
                reason = "no_active_ues";
            }
            else if (!sliceHasDemand[s])
            {
                reason = "no_demand";
            }
            else if (sliceRbgBudget[s] == 0)
            {
                reason = "zero_budget";
            }
            else
            {
                SortUeVectorByAlgorithm(sliceUeVec[s], m_intraAlgorithms[s]);

                uint32_t iteration = 0;
                const uint32_t maxIterations = sliceRbgBudget[s] * sliceUeVec[s].size() + sliceUeVec[s].size();

                while (sliceAllocated < sliceRbgBudget[s] && iteration < maxIterations)
                {
                    iteration++;
                    bool anyUeNeeded = false;

                    for (auto& ue : sliceUeVec[s])
                    {
                        if (sliceAllocated >= sliceRbgBudget[s])
                        {
                            break;
                        }

                        uint32_t bufQueueSize = ue.second;
                        uint32_t prevTbSize = ue.first->m_dlTbSize;
                        // Condição mais flexível para detecção de demanda
                        bool demandPassed = (bufQueueSize > 0 || prevTbSize > 0);

                        if (logThisSlot && m_ueAllocCsv.is_open())
                        {
                            uint32_t curUnique = 0;
                            if (!ue.first->m_dlRBG.empty())
                            {
                                std::set<uint16_t> uniq(ue.first->m_dlRBG.begin(),
                                                        ue.first->m_dlRBG.end());
                                curUnique = static_cast<uint32_t>(uniq.size());
                            }
                            m_ueAllocCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                                         << m_currentSlot << "," << m_bwpId << "," << beamIdStr << ","
                                         << s << "," << ue.first->m_rnti << ","
                                         << bufQueueSize << "," << prevTbSize << ","
                                         << 0 << "," << (demandPassed ? 1 : 0) << ","
                                         << 0 << "," << curUnique << "," << 0 << ","
                                         << static_cast<uint32_t>(ue.first->GetDlMcs()) << ","
                                         << static_cast<uint32_t>(ue.first->m_dlRank) << ","
                                         << GetNumRbPerRbg() << ",pre_allocation\n";
                        }

                        if (!demandPassed)
                        {
                            continue;
                        }
                        anyUeNeeded = true;

                        uint32_t logicalIdx = 0;
                        for (; logicalIdx < totalRbgs; ++logicalIdx)
                        {
                            uint32_t realId = availableRbgIds[logicalIdx];
                            if (!rbgRealUsed[realId])
                            {
                                break;
                            }
                        }
                        if (logicalIdx >= totalRbgs)
                        {
                            break;
                        }

                        uint32_t actualRbgId = availableRbgIds[logicalIdx];
                        rbgRealUsed[actualRbgId] = true;

                        auto& dlRbg = ue.first->m_dlRBG;
                        auto existingRbgs = dlRbg.size();
                        dlRbg.resize(dlRbg.size() + beamSym);
                        std::fill(dlRbg.begin() + existingRbgs, dlRbg.end(), actualRbgId);

                        auto& dlSym = ue.first->m_dlSym;
                        auto existingSyms = dlSym.size();
                        dlSym.resize(dlSym.size() + beamSym);
                        std::iota(dlSym.begin() + existingSyms, dlSym.end(), 0);

                        assigned.m_rbg += 1;
                        assigned.m_sym = beamSym;

                        sliceAllocated++;

                        AssignedDlResources(ue, FTResources(1, beamSym), assigned);

                        for (auto& otherUe : sliceUeVec[s])
                        {
                            if (ue.first->m_rnti != otherUe.first->m_rnti)
                            {
                                NotAssignedDlResources(otherUe, FTResources(1, beamSym), assigned);
                            }
                        }

                        if (logThisSlot && m_ueAllocCsv.is_open())
                        {
                            std::set<uint16_t> uniq(ue.first->m_dlRBG.begin(),
                                                    ue.first->m_dlRBG.end());
                            uint32_t tbSize = ue.first->m_dlTbSize;
                            m_ueAllocCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                                         << m_currentSlot << "," << m_bwpId << "," << beamIdStr << ","
                                         << s << "," << ue.first->m_rnti << ","
                                         << bufQueueSize << "," << ue.first->m_dlTbSize << ","
                                         << 1 << "," << 1 << "," << 1 << ","
                                         << static_cast<uint32_t>(uniq.size()) << "," << tbSize << ","
                                         << static_cast<uint32_t>(ue.first->GetDlMcs()) << ","
                                         << static_cast<uint32_t>(ue.first->m_dlRank) << ","
                                         << GetNumRbPerRbg() << ",allocated\n";
                        }
                    }

                    if (!anyUeNeeded)
                    {
                        break;
                    }
                }

                if (sliceAllocated == 0)
                {
                    reason = "all_ue_demand_satisfied";
                }
                else if (sliceAllocated < sliceRbgBudget[s])
                {
                    reason = "partial_alloc";
                }
                else
                {
                    reason = "full_alloc";
                }
            }

            sliceAllocatedVec[s] = sliceAllocated;
            sliceReasonVec[s] = reason;
            std::ostringstream rntiList;
            for (size_t i = 0; i < sliceUeVec[s].size(); ++i)
            {
                if (i)
                    rntiList << ";";
                rntiList << sliceUeVec[s][i].first->m_rnti;
            }
            sliceRntiListVec[s] = rntiList.str();

            // Log per-UE demand details for no_demand slices
            if (logThisSlot && reason == "no_demand" && m_ueAllocCsv.is_open())
            {
                for (const auto& ue : sliceUeVec[s])
                {
                    uint32_t bufQueueSize = ue.second;
                    uint32_t prevTbSize = ue.first->m_dlTbSize;
                    m_ueAllocCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                                 << m_currentSlot << "," << m_bwpId << "," << beamIdStr << ","
                                 << s << "," << ue.first->m_rnti << ","
                                 << bufQueueSize << "," << prevTbSize << ","
                                 << 0 << "," << 0 << "," << 0 << "," << 0 << ",0,"
                                 << static_cast<uint32_t>(ue.first->GetDlMcs()) << ","
                                 << static_cast<uint32_t>(ue.first->m_dlRank) << ","
                                 << GetNumRbPerRbg() << ",no_demand\n";
                }
            }
        }

        uint32_t totalAllocatedRbg = std::accumulate(sliceAllocatedVec.begin(),
                                                     sliceAllocatedVec.end(),
                                                     0u);

        for (uint32_t s = 0; s < m_numSlices; ++s)
        {
            NS_ASSERT_MSG(sliceAllocatedVec[s] <= sliceRbgBudget[s],
                          "allocatedRbg=" << sliceAllocatedVec[s]
                                          << " exceeds budgetRbg=" << sliceRbgBudget[s]
                                          << " for slice " << s);

            double rshRealPct = (totalAllocatedRbg > 0)
                                    ? 100.0 * static_cast<double>(sliceAllocatedVec[s]) /
                                          static_cast<double>(totalAllocatedRbg)
                                    : 0.0;
            double budgetUtilizationPct = (sliceRbgBudget[s] > 0)
                                              ? 100.0 * static_cast<double>(sliceAllocatedVec[s]) /
                                                    static_cast<double>(sliceRbgBudget[s])
                                              : 0.0;
            budgetUtilizationPct = std::clamp(budgetUtilizationPct, 0.0, 100.0);
            double unusedBudgetPct = (sliceRbgBudget[s] > 0) ? 100.0 - budgetUtilizationPct : 0.0;
            double targetSharePct = effectiveWeight[s] * 100.0;
            double allocationFidelityPct = std::clamp(100.0 - std::abs(rshRealPct - targetSharePct),
                                                      0.0,
                                                      100.0);

            if (m_sliceAllocationStats.size() == m_numSlices)
            {
                m_sliceAllocationStats[s].samples += 1;
                if (sliceRbgBudget[s] > 0)
                {
                    m_sliceAllocationStats[s].samplesWithBudget += 1;
                    m_sliceAllocationStats[s].budgetUtilizationPctSum += budgetUtilizationPct;
                    m_sliceAllocationStats[s].unusedBudgetPctSum += unusedBudgetPct;
                }
                m_sliceAllocationStats[s].budgetRbgTotal += sliceRbgBudget[s];
                m_sliceAllocationStats[s].allocatedRbgTotal += sliceAllocatedVec[s];
                m_sliceAllocationStats[s].rshRealPctSum += rshRealPct;
                m_sliceAllocationStats[s].allocationFidelityPctSum += allocationFidelityPct;
            }

            if (logThisSlot && m_sliceAllocCsv.is_open())
            {
                uint32_t redistributedIdleRbg =
                    (!sliceHasDemand[s] && sliceRbgBudget[s] == 0 && m_prbWeights[s] > 0.0)
                        ? static_cast<uint32_t>(std::round(totalRbgs * m_prbWeights[s]))
                        : 0;

                m_sliceAllocCsv << timeMs << "," << s << ","
                                << std::fixed << std::setprecision(4) << m_prbWeights[s] << ","
                                << sliceRbgBudget[s] << ","
                                << sliceAllocatedVec[s] << ","
                                << totalAllocatedRbg << ","
                                << std::setprecision(4) << rshRealPct << ","
                                << std::setprecision(4) << budgetUtilizationPct << ","
                                << std::setprecision(4) << unusedBudgetPct << ","
                                << std::setprecision(4) << allocationFidelityPct << ","
                                << sliceUeVec[s].size() << ","
                                << std::setprecision(4) << effectiveWeight[s] << ","
                                << beamIdStr << ","
                                << (sliceHasDemand[s] ? 1 : 0) << ","
                                << sliceReasonVec[s] << ","
                                << redistributedIdleRbg << ","
                                << "\"" << sliceRntiListVec[s] << "\"\n";
            }
        }
    }

    if (m_sliceAllocCsv.is_open())
    {
        m_sliceAllocCsv.flush();
    }
    if (m_unmappedRntiCsv.is_open())
    {
        m_unmappedRntiCsv.flush();
    }
    if (m_ueAllocCsv.is_open())
    {
        m_ueAllocCsv.flush();
    }
    if (m_harqTrackingCsv.is_open())
    {
        m_harqTrackingCsv.flush();
    }
    if (m_activeDlDiagCsv.is_open())
    {
        m_activeDlDiagCsv.flush();
    }

    return symPerBeam;
}

void
RslaqMacScheduler::AssignedDlResources(const UePtrAndBufferReq& ue,
                                        const FTResources& assigned,
                                        const FTResources& totAssigned) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->UpdateDlPFMetric(totAssigned, m_timeWindow);
}

void
RslaqMacScheduler::AssignedUlResources(const UePtrAndBufferReq& ue,
                                        const FTResources& assigned,
                                        const FTResources& totAssigned) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->UpdateUlPFMetric(totAssigned, m_timeWindow);
}

void
RslaqMacScheduler::NotAssignedDlResources(const UePtrAndBufferReq& ue,
                                           const FTResources& notAssigned,
                                           const FTResources& totalAssigned) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->UpdateDlPFMetric(totalAssigned, m_timeWindow);
}

void
RslaqMacScheduler::NotAssignedUlResources(const UePtrAndBufferReq& ue,
                                           const FTResources& notAssigned,
                                           const FTResources& totalAssigned) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->UpdateUlPFMetric(totalAssigned, m_timeWindow);
}

void
RslaqMacScheduler::BeforeDlSched(const UePtrAndBufferReq& ue,
                                   const FTResources& assignableInIteration) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto ueInfo = GetUe(ue);
    if (ueInfo->m_dlMcs == 0)
    {
        ueInfo->m_dlMcs = 15;
    }
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(ueInfo.get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->CalculatePotentialTPutDl(assignableInIteration);

    // Track buffer size for external KPM export
    m_lastDlBufferSize[ueInfo->m_rnti] = ue.second;
}

void
RslaqMacScheduler::BeforeUlSched(const UePtrAndBufferReq& ue,
                                  const FTResources& assignableInIteration) const
{
    NS_LOG_FUNCTION(this);
    GetFirst GetUe;
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->CalculatePotentialTPutUl(assignableInIteration);
}

} // namespace ns3
