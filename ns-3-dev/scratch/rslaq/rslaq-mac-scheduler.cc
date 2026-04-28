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
        // Log based on period, but also ensure we log at least once
        if (timeMs - m_lastLoggedMs >= m_macLoggingPeriodMs)
        {
            m_lastLoggedMs = timeMs;
            return true;
        }
        return false;
    }
    // Legacy behavior: log first 200ms and every 100ms
    return (timeMs <= 200) || (timeMs % 100 == 0);
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
    NS_LOG_FUNCTION(this);
    m_numSlices = numSlices;
    m_sliceUeRnti = sliceUeRnti;

    m_prbWeights.resize(m_numSlices, 1.0 / m_numSlices);
    m_intraAlgorithms.resize(m_numSlices, IntraSliceAlgorithm::RR);

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
    if (!m_scenarioName.empty())
    {
        prefix += m_scenarioName + "_";
    }

    if (!m_sliceAllocCsv.is_open())
    {
        std::string path = prefix + "slice_alloc.csv";
        m_sliceAllocCsv.open(path, std::ios::out | std::ios::trunc);
        // Header with new fields: callId, slot, bwpId, beamId
        m_sliceAllocCsv << "callId,timeMs,scenario,slot,bwpId,beamId,sliceId,configuredWeight,"
                           "effectiveWeight,activeUes,beamSym,hasDemand,budgetRbg,allocatedRbg,"
                           "reason,rntis\n";
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

NrMacSchedulerNs3::BeamSymbolMap
RslaqMacScheduler::AssignDLRBG(uint32_t symAvail, const ActiveUeMap& activeDl) const
{
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
                if (ue.first->m_dlTbSize < std::max(bufQueueSize, 10U))
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
            uint32_t allocatedSoFar = 0;
            uint32_t lastActiveSlice = 0;
            for (uint32_t s = 0; s < m_numSlices; s++)
            {
                if (!sliceHasDemand[s])
                {
                    continue;
                }
                effectiveWeight[s] = m_prbWeights[s] / activeWeightSum;
                lastActiveSlice = s;
            }
            for (uint32_t s = 0; s < m_numSlices; s++)
            {
                if (!sliceHasDemand[s])
                {
                    continue;
                }
                if (s == lastActiveSlice)
                {
                    sliceRbgBudget[s] = totalRbgs - allocatedSoFar;
                }
                else
                {
                    sliceRbgBudget[s] = static_cast<uint32_t>(totalRbgs * effectiveWeight[s]);
                    allocatedSoFar += sliceRbgBudget[s];
                }
            }
        }

        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            for (auto& ue : sliceUeVec[s])
            {
                BeforeDlSched(ue, FTResources(totalRbgs, beamSym));
            }
        }

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
                        bool demandPassed = (prevTbSize < std::max(bufQueueSize, 10U));

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

            if (logThisSlot && m_sliceAllocCsv.is_open())
            {
                std::ostringstream rntiList;
                for (size_t i = 0; i < sliceUeVec[s].size(); ++i)
                {
                    if (i)
                        rntiList << ";";
                    rntiList << sliceUeVec[s][i].first->m_rnti;
                }
                m_sliceAllocCsv << callId << "," << timeMs << "," << m_scenarioName << ","
                                << m_currentSlot << "," << m_bwpId << "," << beamIdStr << ","
                                << s << ","
                                << std::fixed << std::setprecision(4) << m_prbWeights[s] << ","
                                << std::setprecision(4) << effectiveWeight[s] << ","
                                << sliceUeVec[s].size() << ","
                                << beamSym << ","
                                << (sliceHasDemand[s] ? 1 : 0) << ","
                                << sliceRbgBudget[s] << ","
                                << sliceAllocated << ","
                                << reason << ","
                                << "\"" << rntiList.str() << "\"\n";
            }

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
    if (GetUe(ue)->m_dlMcs == 0)
    {
        GetUe(ue)->m_dlMcs = 15;
    }
    auto uePtr = dynamic_cast<NrMacSchedulerUeInfoPF*>(GetUe(ue).get());
    NS_ASSERT(uePtr != nullptr);
    uePtr->CalculatePotentialTPutDl(assignableInIteration);
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
