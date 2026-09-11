"""Local AI adapter interface for the ULPF parser factory."""

from abc import ABC, abstractmethod

from backend.models.parser_proposal import ParserProposal


class LocalAIError(RuntimeError):
    """Raised when the local AI provider cannot generate a proposal."""


class LocalAIAdapter(ABC):
    """
    Interface for local AI providers used by the parser factory.

    Implementations may connect to an on-premise/local model,
    but the core ULPF pipeline must depend only on this interface.
    """

    @abstractmethod
    def generate_parser_proposal(
        self,
        raw_log: str,
        evidence: dict,
    ) -> ParserProposal:
        """
        Generate a structured parser proposal from log evidence.

        Args:
            raw_log: Original unknown log.
            evidence: Structural intelligence produced by Step 22.

        Returns:
            A validated ParserProposal.

        Raises:
            LocalAIError: If the provider cannot generate a proposal.
        """
        raise NotImplementedError