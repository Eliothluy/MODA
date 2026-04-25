/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * RSLAQ Meta-Scheduler for 5G-LENA (ns-3)
 *
 * Slice-aware OFDMA MAC scheduler with dynamic intra-slice algorithm
 * selection. Partitions PRBs (RBGs) across slices by configurable
 * weights and applies per-slice Round Robin, Proportional Fair, or
 * Best CQI (Maximum Rate) ordering.
 */

#pragma once

#include "ns3/nr-mac-scheduler-ofdma-rr.h"

namespace ns3
{

/**
 * @ingroup scheduler
 * @brief RSLAQ Meta-Scheduler: slice-aware OFDMA with dynamic intra-slice policy
 *
 * The scheduler partitions the available RBGs among N configured slices
 * according to a vector of proportional weights that sum to 1.0.
 * Within each slice, UEs are sorted by a selectable intra-slice algorithm:
 *
 *   RR   - Round Robin (fewest assigned RBGs first)
 *   PF   - Proportional Fair (potentialTput / avgTput)
 *   BCQI - Best CQI / Maximum Rate (highest MCS first)
 *
 * Configuration is updated at run-time through SetSliceConfiguration(),
 * typically called every 10 ms (one 5G frame) by the DRL agent callback.
 */
class RslaqMacScheduler : public NrMacSchedulerOfdmaRR
{
  public:
    /**
     * @brief Intra-slice scheduling algorithm identifier
     */
    enum class IntraSliceAlgorithm : uint8_t
    {
        RR = 0,   //!< Round Robin
        PF = 1,   //!< Proportional Fair
        BCQI = 2  //!< Best CQI (Maximum Rate)
    };

    static TypeId GetTypeId();

    RslaqMacScheduler();
    ~RslaqMacScheduler() override;

    /**
     * @brief Configure slice PRB weights and intra-slice algorithms
     *
     * @param prbWeights     Vector of N weights (must sum to 1.0)
     * @param algorithms     Vector of N intra-slice algorithms
     *
     * Can be called at any time to update the scheduler policy (e.g., every 10 ms).
     */
    void SetSliceConfiguration(const std::vector<double>& prbWeights,
                               const std::vector<IntraSliceAlgorithm>& algorithms);

    /**
     * @brief Map UE RNTIs to slices
     *
     * @param numSlices      Number of slices
     * @param sliceUeRnti    Vector of N vectors; sliceUeRnti[s] lists RNTIs of slice s
     */
    void SetSliceUeMapping(uint32_t numSlices,
                           const std::vector<std::vector<uint32_t>>& sliceUeRnti);

    uint32_t GetNumSlices() const;
    double GetPrbWeight(uint32_t sliceIdx) const;
    IntraSliceAlgorithm GetIntraAlgorithm(uint32_t sliceIdx) const;

    /**
     * @brief Get the slice index for a given RNTI
     * @param rnti  UE RNTI
     * @return slice index or -1 if not found
     */
    int32_t GetSliceIndexForRnti(uint16_t rnti) const;

  protected:
    std::shared_ptr<NrMacSchedulerUeInfo> CreateUeRepresentation(
        const NrMacCschedSapProvider::CschedUeConfigReqParameters& params) const override;

    BeamSymbolMap AssignDLRBG(uint32_t symAvail, const ActiveUeMap& activeDl) const override;

    void AssignedDlResources(const UePtrAndBufferReq& ue,
                             const FTResources& assigned,
                             const FTResources& totAssigned) const override;

    void AssignedUlResources(const UePtrAndBufferReq& ue,
                             const FTResources& assigned,
                             const FTResources& totAssigned) const override;

    void NotAssignedDlResources(const UePtrAndBufferReq& ue,
                                const FTResources& notAssigned,
                                const FTResources& totalAssigned) const override;

    void NotAssignedUlResources(const UePtrAndBufferReq& ue,
                                const FTResources& notAssigned,
                                const FTResources& totalAssigned) const override;

    void BeforeDlSched(const UePtrAndBufferReq& ue,
                       const FTResources& assignableInIteration) const override;

    void BeforeUlSched(const UePtrAndBufferReq& ue,
                       const FTResources& assignableInIteration) const override;

  private:
    /**
     * @brief Sort UEs within a slice by the selected intra-slice algorithm
     */
    void SortUeVectorByAlgorithm(std::vector<UePtrAndBufferReq>& ueVector,
                                 IntraSliceAlgorithm algo) const;

    uint32_t m_numSlices{0};
    std::vector<double> m_prbWeights;                     // per-slice PRB proportion
    std::vector<IntraSliceAlgorithm> m_intraAlgorithms;    // per-slice algorithm
    std::vector<std::vector<uint32_t>> m_sliceUeRnti;      // RNTIs per slice

    double m_timeWindow{99.0}; //!< PF averaging time window
    double m_alpha{0.0};       //!< PF fairness index (0 = full fairness)
};

} // namespace ns3
