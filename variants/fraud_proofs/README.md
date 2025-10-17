# Fraud Proofs: Optimistic Verification

**Status**: 🚧 In Development

## Overview

Optimistic verification assumes providers are honest by default and only verifies when challenged. This dramatically reduces verification costs while maintaining security through economic incentives.

## How It Works

### Normal Flow (99% of cases)
1. Provider submits output + commitment
2. Router accepts immediately (no verification)
3. 24-hour challenge period begins
4. If no challenge → output finalized

### Challenge Flow (1% of cases)
1. Anyone can challenge by posting bond
2. Provider must respond with audit proof within 1 hour
3. Router verifies the challenged steps
4. Fraud detected → provider slashed, challenger rewarded
5. Provider honest → challenger loses bond

## Economic Security

**Key insight**: Make fraud economically irrational

- Minimum stake: 100 tokens
- Slash amount: 10x job payment
- Challenge bond: 1x job payment
- Expected loss from fraud: > Expected gain

## Components

- `optimistic_provider.py` - Provider that submits without verification
- `optimistic_router.py` - Router that accepts optimistically
- `challenger.py` - Challenge submission and resolution
- `stake_manager.py` - Stake deposits and slashing
- `fraud_detector.py` - Automated fraud detection
- `demo_fraud_proofs.py` - End-to-end demonstration

## Usage

```python
from optimistic_provider import OptimisticProvider
from optimistic_router import OptimisticRouter

# Provider deposits stake
provider = OptimisticProvider(model_path, stake=100)

# Router accepts optimistically
router = OptimisticRouter(challenge_period=24*3600)

# Submit job
response = provider.process_job(job)
accepted = router.accept_response(response)  # Immediate!

# Challenge period
# ... 24 hours later ...

# Finalize if no challenges
router.finalize_response(job.job_id)
```

## Testing

```bash
python demo_fraud_proofs.py
```

## Performance

- **Acceptance latency**: <1ms (no verification)
- **Finalization time**: 24 hours (challenge period)
- **Verification cost**: 0 for honest providers
- **Challenge cost**: 1 token bond

## Security Analysis

See `VARIANTS_ROADMAP.md` for detailed economic analysis.

**TL;DR**: Fraud is economically irrational when:
- Slash amount > Expected gain from fraud
- Detection probability × Slash > Job payment
