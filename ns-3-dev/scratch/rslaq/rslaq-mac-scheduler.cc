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

#include <algorithm>
#include <numeric>
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
                          MakeDoubleChecker<double>(0.0, 1.0));
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

    GetFirst GetBeamId;
    GetSecond GetUeVector;
    BeamSymbolMap symPerBeam = GetSymPerBeam(symAvail, activeDl);

    for (const auto& el : activeDl)
    {
        BeamId beamId = GetBeamId(el);
        uint32_t beamSym = symPerBeam.at(beamId);
        const std::vector<bool> dlNotchedMask = GetDlNotchedRbgMask();
        uint32_t totalRbgs = !dlNotchedMask.empty()
                                 ? std::count(dlNotchedMask.begin(), dlNotchedMask.end(), true)
                                 : GetBandwidthInRbg();
        NS_ASSERT(totalRbgs > 0);

        std::vector<bool> availableRbg(totalRbgs, true);

        FTResources assigned(0, 0);

        std::vector<std::vector<UePtrAndBufferReq>> sliceUeVec(m_numSlices);
        for (const auto& ue : GetUeVector(el))
        {
            int32_t sIdx = GetSliceIndexForRnti(ue.first->m_rnti);
            if (sIdx >= 0)
            {
                sliceUeVec[static_cast<uint32_t>(sIdx)].emplace_back(ue);
            }
        }

        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            for (auto& ue : sliceUeVec[s])
            {
                BeforeDlSched(ue, FTResources(totalRbgs, beamSym));
            }
        }

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

        for (uint32_t s = 0; s < m_numSlices; s++)
        {
            if (sliceUeVec[s].empty() || sliceRbgBudget[s] == 0)
            {
                continue;
            }

            SortUeVectorByAlgorithm(sliceUeVec[s], m_intraAlgorithms[s]);

            uint32_t sliceAllocated = 0;
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

                    GetFirst GetUe;
                    uint32_t bufQueueSize = ue.second;
                    if (GetUe(ue)->m_dlTbSize >= std::max(bufQueueSize, 10U))
                    {
                        continue;
                    }
                    anyUeNeeded = true;

                    uint32_t rbgIdx = 0;
                    for (rbgIdx = 0; rbgIdx < totalRbgs; rbgIdx++)
                    {
                        if (availableRbg[rbgIdx])
                        {
                            break;
                        }
                    }
                    if (rbgIdx >= totalRbgs)
                    {
                        break;
                    }

                    availableRbg[rbgIdx] = false;

                    auto& dlRbg = GetUe(ue)->m_dlRBG;
                    auto existingRbgs = dlRbg.size();
                    dlRbg.resize(dlRbg.size() + beamSym);
                    std::fill(dlRbg.begin() + existingRbgs, dlRbg.end(), rbgIdx);

                    auto& dlSym = GetUe(ue)->m_dlSym;
                    auto existingSyms = dlSym.size();
                    dlSym.resize(dlSym.size() + beamSym);
                    std::iota(dlSym.begin() + existingSyms, dlSym.end(), 0);

                    assigned.m_rbg += 1;
                    assigned.m_sym = beamSym;

                    sliceAllocated++;

                    AssignedDlResources(ue, FTResources(1, beamSym), assigned);

                    for (auto& otherUe : sliceUeVec[s])
                    {
                        if (GetUe(otherUe)->m_rnti != GetUe(ue)->m_rnti)
                        {
                            NotAssignedDlResources(otherUe, FTResources(1, beamSym), assigned);
                        }
                    }
                }

                if (!anyUeNeeded)
                {
                    break;
                }
            }

            NS_LOG_DEBUG("Slice " << s << ": allocated " << sliceAllocated
                                  << "/" << sliceRbgBudget[s] << " RBGs for "
                                  << sliceUeVec[s].size() << " UEs");
        }
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
