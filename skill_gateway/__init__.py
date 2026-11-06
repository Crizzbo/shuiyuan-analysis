"""Skill 适配网关层 (Skill Gateway Layer).

为 Agent Skill 提供统一、轻量、高可用的金融内核适配网关。
"""

from skill_gateway.gateway import SkillGateway, default_gateway
from skill_gateway.freshness import QuoteFreshnessVerifier, QuoteSnapshot, FreshnessAudit
from skill_gateway.card_formatter import DecisionCardFormatter
from skill_gateway.ai_journal_protocol import AIJournalProtocol

__all__ = [
    "SkillGateway",
    "default_gateway",
    "QuoteFreshnessVerifier",
    "QuoteSnapshot",
    "FreshnessAudit",
    "DecisionCardFormatter",
    "AIJournalProtocol",
]
