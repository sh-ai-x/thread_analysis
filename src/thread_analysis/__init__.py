"""thread_analysis — utilities for analyzing thread structures."""

from thread_analysis.analyzer import ThreadStats, analyze

__all__ = ["ThreadStats", "analyze"]
__version__ = "0.1.0"

# Re-trigger CI after db011ae (fix/review-verdict-extraction) merged to main.
