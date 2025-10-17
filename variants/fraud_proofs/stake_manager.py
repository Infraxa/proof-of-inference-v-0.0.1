"""
Stake Manager for Fraud Proof System

Manages provider stakes, slashing, and economic incentives.
"""

from dataclasses import dataclass
from typing import Dict
import time


@dataclass
class StakeInfo:
    """Information about a provider's stake."""
    provider_id: str
    amount: float
    deposited_at: float
    slashed_total: float = 0.0
    is_banned: bool = False


class StakeManager:
    """Manages provider stakes and slashing."""
    
    def __init__(self, min_stake: float = 100.0, slash_multiplier: float = 10.0):
        """
        Initialize stake manager.
        
        Args:
            min_stake: Minimum stake required to participate
            slash_multiplier: Slash amount = job_payment × slash_multiplier
        """
        self.min_stake = min_stake
        self.slash_multiplier = slash_multiplier
        self.stakes: Dict[str, StakeInfo] = {}
    
    def deposit_stake(self, provider_id: str, amount: float) -> bool:
        """
        Deposit stake for a provider.
        
        Args:
            provider_id: Provider identifier
            amount: Stake amount
            
        Returns:
            True if deposit successful
        """
        if amount < self.min_stake:
            print(f"❌ Stake {amount} below minimum {self.min_stake}")
            return False
        
        if provider_id in self.stakes:
            # Add to existing stake
            self.stakes[provider_id].amount += amount
        else:
            # New stake
            self.stakes[provider_id] = StakeInfo(
                provider_id=provider_id,
                amount=amount,
                deposited_at=time.time()
            )
        
        print(f"✅ Provider {provider_id[:8]} deposited {amount} tokens")
        print(f"   Total stake: {self.stakes[provider_id].amount}")
        return True
    
    def get_stake(self, provider_id: str) -> float:
        """Get current stake amount for provider."""
        if provider_id not in self.stakes:
            return 0.0
        return self.stakes[provider_id].amount
    
    def has_sufficient_stake(self, provider_id: str) -> bool:
        """Check if provider has sufficient stake."""
        return self.get_stake(provider_id) >= self.min_stake
    
    def slash_provider(self, provider_id: str, job_payment: float, reason: str) -> float:
        """
        Slash provider's stake for fraud.
        
        Args:
            provider_id: Provider to slash
            job_payment: Original job payment
            reason: Reason for slashing
            
        Returns:
            Amount slashed
        """
        if provider_id not in self.stakes:
            print(f"❌ Cannot slash {provider_id}: No stake found")
            return 0.0
        
        stake_info = self.stakes[provider_id]
        
        if stake_info.is_banned:
            print(f"❌ Cannot slash {provider_id}: Already banned")
            return 0.0
        
        # Calculate slash amount
        slash_amount = min(
            job_payment * self.slash_multiplier,
            stake_info.amount  # Can't slash more than they have
        )
        
        # Apply slash
        stake_info.amount -= slash_amount
        stake_info.slashed_total += slash_amount
        
        print(f"⚔️  SLASHED provider {provider_id[:8]}")
        print(f"   Reason: {reason}")
        print(f"   Amount: {slash_amount} tokens")
        print(f"   Remaining stake: {stake_info.amount}")
        
        # Ban if stake falls below minimum
        if stake_info.amount < self.min_stake:
            stake_info.is_banned = True
            print(f"🚫 Provider {provider_id[:8]} BANNED (insufficient stake)")
        
        return slash_amount
    
    def is_banned(self, provider_id: str) -> bool:
        """Check if provider is banned."""
        if provider_id not in self.stakes:
            return False
        return self.stakes[provider_id].is_banned
    
    def withdraw_stake(self, provider_id: str, amount: float) -> bool:
        """
        Withdraw stake (if not banned and above minimum).
        
        Args:
            provider_id: Provider identifier
            amount: Amount to withdraw
            
        Returns:
            True if withdrawal successful
        """
        if provider_id not in self.stakes:
            print(f"❌ No stake found for {provider_id}")
            return False
        
        stake_info = self.stakes[provider_id]
        
        if stake_info.is_banned:
            print(f"❌ Cannot withdraw: Provider is banned")
            return False
        
        if stake_info.amount - amount < self.min_stake:
            print(f"❌ Cannot withdraw: Would fall below minimum stake")
            return False
        
        stake_info.amount -= amount
        print(f"✅ Withdrew {amount} tokens for {provider_id[:8]}")
        print(f"   Remaining stake: {stake_info.amount}")
        return True
    
    def get_stats(self) -> Dict:
        """Get statistics about stakes."""
        total_staked = sum(s.amount for s in self.stakes.values())
        total_slashed = sum(s.slashed_total for s in self.stakes.values())
        banned_count = sum(1 for s in self.stakes.values() if s.is_banned)
        
        return {
            'total_providers': len(self.stakes),
            'total_staked': total_staked,
            'total_slashed': total_slashed,
            'banned_providers': banned_count,
            'active_providers': len(self.stakes) - banned_count
        }
    
    def print_stats(self):
        """Print stake statistics."""
        stats = self.get_stats()
        print("\n" + "="*50)
        print("📊 STAKE MANAGER STATISTICS")
        print("="*50)
        print(f"Total providers: {stats['total_providers']}")
        print(f"Active providers: {stats['active_providers']}")
        print(f"Banned providers: {stats['banned_providers']}")
        print(f"Total staked: {stats['total_staked']:.2f} tokens")
        print(f"Total slashed: {stats['total_slashed']:.2f} tokens")
        print("="*50 + "\n")


if __name__ == "__main__":
    # Demo
    manager = StakeManager(min_stake=100.0, slash_multiplier=10.0)
    
    # Provider deposits stake
    manager.deposit_stake("provider_1", 100.0)
    manager.deposit_stake("provider_2", 200.0)
    
    # Check stakes
    print(f"\nProvider 1 stake: {manager.get_stake('provider_1')}")
    print(f"Provider 2 stake: {manager.get_stake('provider_2')}")
    
    # Slash provider 1 for fraud (job payment was 1 token)
    manager.slash_provider("provider_1", job_payment=1.0, reason="Model substitution detected")
    
    # Try to slash again
    manager.slash_provider("provider_1", job_payment=1.0, reason="Another fraud attempt")
    
    # Print stats
    manager.print_stats()
