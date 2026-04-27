"""
Tavily web search tool
Uses Tavily API for high-quality web search with AI-powered results
"""
from typing import List, Dict, Any, Optional
import httpx

from code_gen.tools.base import Tool, ToolResult
from code_gen.core.config import Settings


class TavilySearchTool(Tool):
    """Search the web using Tavily API"""
    
    name = "tavily_search"
    description = "Search the web using Tavily API. Returns high-quality search results with AI-powered summaries. Requires TAVILY_API_KEY to be configured."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5)",
                "default": 5,
            },
            "search_depth": {
                "type": "string",
                "description": "Search depth: 'basic' or 'advanced' (default: basic)",
                "enum": ["basic", "advanced"],
                "default": "basic",
            },
            "include_answer": {
                "type": "boolean",
                "description": "Include AI-generated answer (default: True)",
                "default": True,
            },
            "include_raw_content": {
                "type": "boolean",
                "description": "Include raw content from search results (default: False)",
                "default": False,
            },
        },
        "required": ["query"],
    }
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.api_key = self.settings.tavily_api_key
        self.base_url = "https://api.tavily.com"
    
    async def execute(
        self, 
        query: str, 
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False
    ) -> ToolResult:
        """Execute Tavily search"""
        
        # Check if API key is configured
        if not self.api_key:
            return ToolResult(
                success=False,
                content="",
                error="Tavily API key not configured. Please set TAVILY_API_KEY in your config file or environment variable."
            )
        
        try:
            # Prepare request payload
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": "basic" if include_answer else False,
                "include_raw_content": include_raw_content,
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # Format results
            formatted_output = self._format_results(data, query)
            
            return ToolResult(
                success=True,
                content=formatted_output,
                data=data
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Tavily API error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = f"Tavily API error: {error_data['error']}"
            except:
                pass
            return ToolResult(
                success=False,
                content="",
                error=error_msg
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Tavily search failed: {str(e)}"
            )
    
    def _format_results(self, data: Dict[str, Any], query: str) -> str:
        """Format search results for display"""
        output = []
        output.append(f"🔍 Tavily Search Results for: '{query}'\n")
        
        # Add AI-generated answer if available
        answer = data.get("answer")
        if answer:
            output.append("📝 AI Answer:")
            output.append(f"{answer}\n")
        
        # Add search results
        results = data.get("results", [])
        if results:
            output.append(f"📊 Found {len(results)} results:\n")
            
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "")
                score = result.get("score", 0)
                
                output.append(f"{i}. {title}")
                output.append(f"   URL: {url}")
                if score:
                    output.append(f"   Relevance: {score:.2f}")
                if content:
                    # Truncate content if too long
                    content_preview = content[:300] + "..." if len(content) > 300 else content
                    output.append(f"   {content_preview}")
                output.append("")
        
        # Add raw content if available
        if data.get("raw_content"):
            output.append("\n📄 Raw Content from top result:")
            raw_content = data["raw_content"]
            if isinstance(raw_content, str):
                output.append(raw_content[:500] + "..." if len(raw_content) > 500 else raw_content)
        
        return "\n".join(output)


class TavilyExtractTool(Tool):
    """Extract content from URLs using Tavily API"""
    
    name = "tavily_extract"
    description = "Extract and summarize content from URLs using Tavily API. Requires TAVILY_API_KEY to be configured."
    input_schema = {
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to extract content from",
            },
            "extract_depth": {
                "type": "string",
                "description": "Extraction depth: 'basic' or 'advanced' (default: basic)",
                "enum": ["basic", "advanced"],
                "default": "basic",
            },
        },
        "required": ["urls"],
    }
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.api_key = self.settings.tavily_api_key
        self.base_url = "https://api.tavily.com"
    
    async def execute(
        self, 
        urls: List[str],
        extract_depth: str = "basic"
    ) -> ToolResult:
        """Extract content from URLs"""
        
        if not self.api_key:
            return ToolResult(
                success=False,
                content="",
                error="Tavily API key not configured. Please set TAVILY_API_KEY in your config file or environment variable."
            )
        
        try:
            payload = {
                "api_key": self.api_key,
                "urls": urls,
                "extract_depth": extract_depth,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/extract",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
            
            # Format results
            formatted_output = self._format_extract_results(data, urls)
            
            return ToolResult(
                success=True,
                content=formatted_output,
                data=data
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Tavily extract failed: {str(e)}"
            )
    
    def _format_extract_results(self, data: Dict[str, Any], urls: List[str]) -> str:
        """Format extraction results"""
        output = []
        output.append(f"📄 Tavily Content Extraction\n")
        
        results = data.get("results", [])
        failed_urls = data.get("failed_urls", [])
        
        # Show successful extractions
        if results:
            output.append(f"✅ Successfully extracted {len(results)} URLs:\n")
            
            for result in results:
                url = result.get("url", "")
                raw_content = result.get("raw_content", "")
                
                output.append(f"🔗 {url}")
                if raw_content:
                    content_preview = raw_content[:500] + "..." if len(raw_content) > 500 else raw_content
                    output.append(f"   {content_preview}")
                output.append("")
        
        # Show failed URLs
        if failed_urls:
            output.append(f"\n❌ Failed to extract {len(failed_urls)} URLs:")
            for url in failed_urls:
                output.append(f"   - {url}")
        
        return "\n".join(output)
