"""
Web search and crawling tools
Inspired by PraisonAI's web tools
"""
import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlparse
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from code_gen.tools.base import Tool, ToolResult


class DuckDuckGoSearchTool(Tool):
    """Search the web using DuckDuckGo"""
    
    name = "duckduckgo_search"
    description = "Search the web using DuckDuckGo search engine. Returns search results with titles, URLs, and snippets."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 10,
            },
        },
        "required": ["query"],
    }
    
    async def execute(self, query: str, max_results: int = 10) -> ToolResult:
        try:
            # 使用多个搜索引擎，一个失败时尝试下一个
            search_errors = []
            
            # 尝试 1: DuckDuckGo
            try:
                result = await self._search_duckduckgo(query, max_results)
                if result.success:
                    return result
            except Exception as e:
                search_errors.append(f"DuckDuckGo: {e}")
            
            # 尝试 2: 百度搜索
            try:
                result = await self._search_baidu(query, max_results)
                if result.success:
                    return result
            except Exception as e:
                search_errors.append(f"Baidu: {e}")
            
            # 尝试 3: Bing
            try:
                result = await self._search_bing(query, max_results)
                if result.success:
                    return result
            except Exception as e:
                search_errors.append(f"Bing: {e}")
            
            # 都失败了
            return ToolResult(
                success=False,
                content="",
                error=f"All search engines failed: {'; '.join(search_errors)}"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Search failed: {str(e)}"
            )
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> ToolResult:
        """使用 DuckDuckGo 搜索"""
        encoded_query = quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for result in soup.find_all('div', class_='result')[:max_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True)
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            if not results:
                return ToolResult(success=False, content="", error="No results")
            
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {r['snippet']}\n")
            
            return ToolResult(
                success=True,
                content=f"Search results for '{query}':\n\n" + "\n".join(formatted),
                data={"results": results, "query": query}
            )
    
    async def _search_bing(self, query: str, max_results: int) -> ToolResult:
        """使用 Bing 搜索"""
        encoded_query = quote(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 尝试多种可能的选择器
            # 方法1: 标准 b_algo
            for result in soup.find_all('li', class_='b_algo')[:max_results]:
                title_elem = result.find('h2')
                link_elem = title_elem.find('a') if title_elem else None
                # 尝试多种 snippet 选择器
                snippet_elem = result.find('p') or result.find('div', class_='b_caption') or result.find('span', class_='snippet')
                
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    url = link_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # 过滤掉不相关的结果
                    if title and not any(x in title.lower() for x in ['bing homepage quiz', 'bing quiz', '测验']):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
            
            # 方法2: 如果没有结果，尝试其他选择器
            if not results:
                for result in soup.find_all('div', class_='g')[:max_results]:
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    snippet_elem = result.find('span', class_='st') or result.find('div', class_='s')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        if title and not any(x in title.lower() for x in ['bing homepage quiz', 'bing quiz', '测验']):
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet
                            })
            
            if not results:
                return ToolResult(success=False, content="", error="No results found")
            
            formatted = []
            for i, r in enumerate(results[:max_results], 1):
                formatted.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {r['snippet'][:200]}...\n")
            
            return ToolResult(
                success=True,
                content=f"Search results for '{query}':\n\n" + "\n".join(formatted),
                data={"results": results, "query": query}
            )
    
    async def _search_baidu(self, query: str, max_results: int) -> ToolResult:
        """使用百度搜索"""
        encoded_query = quote(query)
        url = f"https://www.baidu.com/s?wd={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.baidu.com/",
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 百度搜索结果选择器
            # 结果通常在 div 容器中
            for result in soup.find_all('div', class_=lambda x: x and ('result' in x or 'c-container' in x))[:max_results]:
                # 标题
                title_elem = result.find('h3') or result.find('a', class_=lambda x: x and 'title' in x)
                if not title_elem:
                    title_elem = result.find('a')
                
                # 链接
                link_elem = result.find('a')
                
                # 摘要 - 尝试多种选择器
                snippet_elem = (result.find('span', class_='content-right_8Zs40') or 
                               result.find('div', class_=lambda x: x and 'abstract' in x) or
                               result.find('span', class_=lambda x: x and 'content' in x) or
                               result.find('p'))
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # 清理标题和 URL
                    if title and url and not url.startswith('javascript:'):
                        # 确保 URL 是完整的
                        if url.startswith('/'):
                            url = f"https://www.baidu.com{url}"
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
            
            if not results:
                return ToolResult(success=False, content="", error="No results found")
            
            formatted = []
            for i, r in enumerate(results[:max_results], 1):
                snippet_text = r['snippet'][:200] if r['snippet'] else ""
                formatted.append(f"{i}. {r['title']}\n   URL: {r['url']}\n   {snippet_text}...\n")
            
            return ToolResult(
                success=True,
                content=f"Search results for '{query}':\n\n" + "\n".join(formatted),
                data={"results": results, "query": query}
            )


class WebFetchTool(Tool):
    """Fetch and extract content from a webpage"""
    
    name = "web_fetch"
    description = "Fetch content from a specific URL and extract text. Use this to visit websites and get detailed information."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum length of content to return",
                "default": 5000,
            },
        },
        "required": ["url"],
    }
    
    async def execute(self, url: str, max_length: int = 5000) -> ToolResult:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 移除脚本和样式
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # 获取文本
                text = soup.get_text(separator='\n', strip=True)
                
                # 清理空白行
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)
                
                # 限制长度
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                
                return ToolResult(
                    success=True,
                    content=f"Content from {url}:\n\n{text}",
                    data={"url": url, "content": text}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to fetch {url}: {str(e)}"
            )


class TavilySearchTool(Tool):
    """Search the web using Tavily API (requires API key)"""
    
    name = "tavily_search"
    description = "Search the web using Tavily AI search API. Requires TAVILY_API_KEY environment variable."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5,
            },
            "include_answer": {
                "type": "boolean",
                "description": "Include AI-generated answer",
                "default": True,
            },
        },
        "required": ["query"],
    }
    
    async def execute(self, query: str, max_results: int = 5, include_answer: bool = True) -> ToolResult:
        try:
            import os
            api_key = os.environ.get("TAVILY_API_KEY")
            
            if not api_key:
                return ToolResult(
                    success=False,
                    content="",
                    error="TAVILY_API_KEY environment variable not set"
                )
            
            url = "https://api.tavily.com/search"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": include_answer
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                answer = data.get("answer", "")
                
                formatted = []
                if answer:
                    formatted.append(f"AI Answer: {answer}\n")
                    formatted.append("=" * 50 + "\n")
                
                for i, r in enumerate(results, 1):
                    formatted.append(f"{i}. {r.get('title', 'No title')}\n")
                    formatted.append(f"   URL: {r.get('url', 'No URL')}\n")
                    formatted.append(f"   {r.get('content', 'No content')[:200]}...\n")
                
                return ToolResult(
                    success=True,
                    content=f"Tavily search results for '{query}':\n\n" + "\n".join(formatted),
                    data={"results": results, "answer": answer, "query": query}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Tavily search failed: {str(e)}"
            )


class WebFetchTool(Tool):
    """Fetch and extract content from a webpage"""
    
    name = "web_fetch"
    description = "Fetch and extract text content from a webpage URL. Returns the main content of the page."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum length of content to return",
                "default": 5000,
            },
        },
        "required": ["url"],
    }
    
    async def execute(self, url: str, max_length: int = 5000) -> ToolResult:
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Invalid URL: {url}"
                )
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator='\n', strip=True)
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Truncate if too long
                if len(text) > max_length:
                    text = text[:max_length] + f"\n\n[Content truncated. Total length: {len(text)} characters]"
                
                # Get title
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else "No title"
                
                return ToolResult(
                    success=True,
                    content=f"Title: {title_text}\nURL: {url}\n\n{text}",
                    data={"title": title_text, "url": url, "content": text}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to fetch URL: {str(e)}"
            )


class WebCrawlTool(Tool):
    """Crawl multiple pages from a website"""
    
    name = "web_crawl"
    description = "Crawl and extract content from multiple pages starting from a URL. Finds linked pages and extracts their content."
    input_schema = {
        "type": "object",
        "properties": {
            "start_url": {
                "type": "string",
                "description": "The starting URL to crawl",
            },
            "max_pages": {
                "type": "integer",
                "description": "Maximum number of pages to crawl",
                "default": 3,
            },
            "same_domain": {
                "type": "boolean",
                "description": "Only crawl pages from the same domain",
                "default": True,
            },
        },
        "required": ["start_url"],
    }
    
    async def execute(self, start_url: str, max_pages: int = 3, same_domain: bool = True) -> ToolResult:
        try:
            parsed_start = urlparse(start_url)
            start_domain = parsed_start.netloc
            
            visited = set()
            to_visit = [start_url]
            results = []
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                while to_visit and len(visited) < max_pages:
                    url = to_visit.pop(0)
                    
                    if url in visited:
                        continue
                    
                    visited.add(url)
                    
                    try:
                        response = await client.get(url, headers=headers)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract content
                        for script in soup(["script", "style", "nav", "header", "footer"]):
                            script.decompose()
                        
                        text = soup.get_text(separator='\n', strip=True)
                        lines = (line.strip() for line in text.splitlines())
                        text = '\n'.join(line for line in lines if line)[:2000]
                        
                        title = soup.find('title')
                        title_text = title.get_text(strip=True) if title else "No title"
                        
                        results.append({
                            "url": url,
                            "title": title_text,
                            "content": text
                        })
                        
                        # Find more links
                        if len(visited) < max_pages:
                            for link in soup.find_all('a', href=True):
                                href = link['href']
                                if href.startswith('http'):
                                    full_url = href
                                elif href.startswith('/'):
                                    full_url = f"{parsed_start.scheme}://{start_domain}{href}"
                                else:
                                    full_url = f"{start_url.rstrip('/')}/{href}"
                                
                                parsed_href = urlparse(full_url)
                                
                                if same_domain and parsed_href.netloc != start_domain:
                                    continue
                                
                                if full_url not in visited and full_url not in to_visit:
                                    to_visit.append(full_url)
                                    
                    except Exception as e:
                        results.append({
                            "url": url,
                            "title": "Error",
                            "content": f"Failed to fetch: {str(e)}"
                        })
            
            # Format results
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(f"\n{'='*50}")
                formatted.append(f"Page {i}: {r['title']}")
                formatted.append(f"URL: {r['url']}")
                formatted.append(f"{'='*50}")
                formatted.append(r['content'][:1000])
                if len(r['content']) > 1000:
                    formatted.append("\n[...content truncated...]")
            
            return ToolResult(
                success=True,
                content=f"Crawled {len(results)} pages from {start_domain}:\n" + "\n".join(formatted),
                data={"pages": results, "total_pages": len(results)}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Crawl failed: {str(e)}"
            )
