use starknet::ContractAddress;

// ============================================================
// TYPES
// ============================================================

#[derive(Drop, Serde, starknet::Store, Clone)]
pub enum AgentId {
    MarketPulse,
    TrendSeeker,
    UnitEcon,
    RevenueScout,
    FirstClick,
    StickyLoop,
    RedTeam,
    MoatInspector,
    BuildCheck,
    PolicyScan,
    ViralEngine,
    SkepticalVC,
}

#[derive(Drop, Serde, starknet::Store, Clone)]
pub struct PillarScores {
    pub market: u8,
    pub revenue: u8,
    pub adoption: u8,
    pub competition: u8,
}

#[derive(Drop, Serde, starknet::Store, Clone)]
pub struct Verdict {
    // Identity
    pub founder: ContractAddress,
    pub idea_hash: felt252,
    pub timestamp: u64,

    // Knowledge graph (compressed)
    pub domain: felt252,
    pub market_stage: felt252,
    pub business_model: felt252,

    // Agents used
    pub agent_count: u8,

    // Debate results
    pub stance_flips: u8,
    pub consensus_level: u8,

    // Final verdict
    pub final_score: u8,
    pub market_score: u8,
    pub revenue_score: u8,
    pub adoption_score: u8,
    pub competition_score: u8,

    // Flags
    pub contested: bool,
    pub blocked: bool,
    pub is_public: bool,

    // God View
    pub god_view_count: u8,    // max 3

    // Integrity
    pub proof_hash: felt252,
}

// ============================================================
// INTERFACE
// ============================================================

#[starknet::interface]
pub trait IVerdictRegistry<TContractState> {
    fn submit_verdict(ref self: TContractState, verdict: Verdict);
    fn add_god_view(ref self: TContractState, idea_hash: felt252, scenario_hash: felt252);
    fn get_verdict(self: @TContractState, idea_hash: felt252) -> Verdict;
    fn get_public_verdicts(self: @TContractState) -> Array<felt252>;
    fn get_verdict_count(self: @TContractState) -> u64;
}

// ============================================================
// CONTRACT
// ============================================================

#[starknet::contract]
pub mod VerdictRegistry {
    use super::{Verdict, IVerdictRegistry};
    use starknet::{ContractAddress, get_caller_address, get_block_timestamp};
    use starknet::storage::{
        StoragePointerReadAccess, StoragePointerWriteAccess,
        StoragePathEntry, Map
    };

    // ── Storage ──────────────────────────────────────────────
    #[storage]
    struct Storage {
        owner: ContractAddress,
        verdicts: Map<felt252, Verdict>,
        verdict_exists: Map<felt252, bool>,
        public_ideas: Map<u64, felt252>,
        public_count: u64,
        total_count: u64,
        god_view_counts: Map<felt252, u8>,
    }

    // ── Events ───────────────────────────────────────────────
    #[event]
    #[derive(Drop, starknet::Event)]
    pub enum Event {
        VerdictSubmitted: VerdictSubmitted,
        GodViewAdded: GodViewAdded,
    }

    #[derive(Drop, starknet::Event)]
    pub struct VerdictSubmitted {
        #[key]
        pub founder: ContractAddress,
        #[key]
        pub idea_hash: felt252,
        pub final_score: u8,
        pub is_public: bool,
        pub timestamp: u64,
    }

    #[derive(Drop, starknet::Event)]
    pub struct GodViewAdded {
        #[key]
        pub idea_hash: felt252,
        pub scenario_hash: felt252,
        pub god_view_count: u8,
    }

    // ── Constructor ──────────────────────────────────────────
    #[constructor]
    fn constructor(ref self: ContractState, owner: ContractAddress) {
        self.owner.write(owner);
        self.public_count.write(0);
        self.total_count.write(0);
    }

    // ── Implementation ───────────────────────────────────────
    #[abi(embed_v0)]
    impl VerdictRegistryImpl of IVerdictRegistry<ContractState> {

        fn submit_verdict(ref self: ContractState, verdict: Verdict) {
            let caller = get_caller_address();
            let timestamp = get_block_timestamp();

            // Build final verdict with on-chain data
            let final_verdict = Verdict {
                founder: caller,
                idea_hash: verdict.idea_hash,
                timestamp,
                domain: verdict.domain,
                market_stage: verdict.market_stage,
                business_model: verdict.business_model,
                agent_count: verdict.agent_count,
                stance_flips: verdict.stance_flips,
                consensus_level: verdict.consensus_level,
                final_score: verdict.final_score,
                market_score: verdict.market_score,
                revenue_score: verdict.revenue_score,
                adoption_score: verdict.adoption_score,
                competition_score: verdict.competition_score,
                contested: verdict.contested,
                blocked: verdict.blocked,
                is_public: verdict.is_public,
                god_view_count: 0_u8,
                proof_hash: verdict.proof_hash,
            };

            // Store
            self.verdicts.entry(verdict.idea_hash).write(final_verdict.clone());
            self.verdict_exists.entry(verdict.idea_hash).write(true);
            self.god_view_counts.entry(verdict.idea_hash).write(0_u8);

            // Track total
            let total = self.total_count.read();
            self.total_count.write(total + 1);

            // Track public index
            if verdict.is_public {
                let count = self.public_count.read();
                self.public_ideas.entry(count).write(verdict.idea_hash);
                self.public_count.write(count + 1);
            }

            // Emit
            self.emit(VerdictSubmitted {
                founder: caller,
                idea_hash: verdict.idea_hash,
                final_score: verdict.final_score,
                is_public: verdict.is_public,
                timestamp,
            });
        }

        fn add_god_view(ref self: ContractState, idea_hash: felt252, scenario_hash: felt252) {
            // Must exist
            assert(self.verdict_exists.entry(idea_hash).read(), 'Verdict not found');

            // Max 3 god views
            let current = self.god_view_counts.entry(idea_hash).read();
            assert(current < 3_u8, 'God View limit reached (max 3)');

            let new_count = current + 1_u8;
            self.god_view_counts.entry(idea_hash).write(new_count);

            // Update stored count
            let mut v = self.verdicts.entry(idea_hash).read();
            v.god_view_count = new_count;
            self.verdicts.entry(idea_hash).write(v);

            self.emit(GodViewAdded {
                idea_hash,
                scenario_hash,
                god_view_count: new_count,
            });
        }

        fn get_verdict(self: @ContractState, idea_hash: felt252) -> Verdict {
            assert(self.verdict_exists.entry(idea_hash).read(), 'Verdict not found');
            self.verdicts.entry(idea_hash).read()
        }

        fn get_public_verdicts(self: @ContractState) -> Array<felt252> {
            let count = self.public_count.read();
            let mut result: Array<felt252> = ArrayTrait::new();
            let mut i: u64 = 0;
            loop {
                if i >= count { break; }
                result.append(self.public_ideas.entry(i).read());
                i += 1;
            };
            result
        }

        fn get_verdict_count(self: @ContractState) -> u64 {
            self.total_count.read()
        }
    }
}
