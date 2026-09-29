import logging
from typing import List
from core.config import settings
from core.models import DocReference

logger = logging.getLogger("fixpilot.doc_search")


class DocSearchEngine:
    """Discovers web references and StackOverflow solutions using Tavily Search API."""

    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.client = None
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                from tavily import TavilyClient
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize TavilyClient: {e}")

    async def search(
        self,
        error_message: str,
        language: str = "python",
        max_results: int = 3
    ) -> List[DocReference]:
        """Queries Tavily API for relevant documentation and community fixes."""
        query = f"{language} {error_message} fix solution"
        
        if self.client:
            try:
                # Tavily sync client called in async context
                response = self.client.search(
                    query=query,
                    search_depth="basic",
                    max_results=max_results,
                    include_domains=["stackoverflow.com", "docs.python.org", "github.com", "realpython.com"]
                )
                results = []
                for item in response.get("results", []):
                    results.append(DocReference(
                        title=item.get("title", "Reference"),
                        url=item.get("url", ""),
                        snippet=item.get("content", "")[:350]
                    ))
                if results:
                    return results
            except Exception as exc:
                logger.warning(f"Tavily search execution failed: {exc}. Falling back to default references.")

        # Default fallback references based on error keywords
        return self._generate_fallback_references(error_message, language)

    def _generate_fallback_references(self, error_message: str, language: str) -> List[DocReference]:
        """Provides high-quality baseline documentation references."""
        refs = []
        if "IndexError" in error_message:
            refs.append(DocReference(
                title="Python IndexError: list index out of range - Python Docs",
                url="https://docs.python.org/3/tutorial/datastructures.html",
                snippet="Lists in Python use zero-based indexing. Accessing items[len(items)] raises an IndexError because valid indices range from 0 to len(items) - 1."
            ))
            refs.append(DocReference(
                title="How to avoid IndexError on list access - Stack Overflow",
                url="https://stackoverflow.com/questions/509211/understanding-slice-notation",
                snippet="Ensure you check list boundaries before accessing, or use slicing syntax which gracefully handles out-of-range indices."
            ))
        elif "TypeError" in error_message or "NoneType" in error_message:
            refs.append(DocReference(
                title="Handling NoneType and TypeError in Python - Real Python",
                url="https://realpython.com/null-in-python/",
                snippet="'NoneType' object is not subscriptable occurs when an operation assumes an object or dictionary is present, but the variable evaluates to None."
            ))
            refs.append(DocReference(
                title="Safe dictionary lookup with dict.get() - Python Standard Library",
                url="https://docs.python.org/3/library/stdtypes.html#dict.get",
                snippet="Use dict.get(key, default) instead of dict[key] to prevent KeyError and handle missing attributes gracefully."
            ))
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            refs.append(DocReference(
                title="Python Modules and Import System - Official Documentation",
                url="https://docs.python.org/3/reference/import.html",
                snippet="Verify that the module name and subpath match existing filesystem files and directories containing __init__.py."
            ))
        else:
            refs.append(DocReference(
                title=f"{language.capitalize()} Built-in Exceptions Guide",
                url="https://docs.python.org/3/library/exceptions.html",
                snippet=f"Overview of standard exception handling and debugging best practices in {language}."
            ))

        return refs
