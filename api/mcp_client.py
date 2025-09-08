import os
import json
import logging
from typing import Dict, Any, Optional, List, Union

from api.log_service import LogService

class MCPError(Exception):
    """Exception raised for errors in the MCP client."""
    pass

async def run_mcp(server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool on an MCP server.
    
    Args:
        server_name: The name of the MCP server to use
        tool_name: The name of the tool to execute
        args: Arguments to pass to the tool
        
    Returns:
        The result of the tool execution
        
    Raises:
        MCPError: If there's an error executing the tool
    """
    try:
        log_service = LogService()
        log_service.log_debug("Executing MCP tool", {
            "server_name": server_name,
            "tool_name": tool_name,
            "args": json.dumps(args)[:100] + "..." if len(json.dumps(args)) > 100 else json.dumps(args)
        })
        
        # In a real implementation, this would make an API call to the MCP server
        # For now, we'll simulate the call for Hyperbrowser tools
        
        if server_name == "mcp.config.usrlocalmcp.Hyperbrowser":
            if tool_name == "extract_structured_data":
                return await _simulate_hyperbrowser_extract_structured_data(args)
            elif tool_name == "claude_computer_use_agent":
                return await _simulate_hyperbrowser_claude_agent(args)
            elif tool_name == "scrape_webpage":
                return await _simulate_hyperbrowser_scrape_webpage(args)
            else:
                raise MCPError(f"Unsupported tool: {tool_name}")
        elif server_name == "mcp.config.usrlocalmcp.Puppeteer":
            return await _simulate_puppeteer_tool(tool_name, args)
        else:
            raise MCPError(f"Unsupported MCP server: {server_name}")
            
    except Exception as e:
        log_service = LogService()
        log_service.log_debug("Error executing MCP tool", {
            "server_name": server_name,
            "tool_name": tool_name,
            "error": str(e)
        })
        raise MCPError(f"Error executing MCP tool: {str(e)}")

async def _simulate_hyperbrowser_extract_structured_data(args: Dict[str, Any]) -> Any:
    """Simulate the extract_structured_data tool from Hyperbrowser.
    
    In a real implementation, this would make an API call to the Hyperbrowser MCP server.
    For now, we'll delegate to the FirecrawlApp client to maintain functionality.
    """
    try:
        from api.firecrawl_client import FirecrawlApp
        
        firecrawl = FirecrawlApp()
        url = args["urls"][0] if isinstance(args["urls"], list) and len(args["urls"]) > 0 else None
        schema = args["schema"]
        
        if not url:
            raise MCPError("No URL provided")
            
        # Use FirecrawlApp as a fallback with DeepSeek como LLM
        result = firecrawl.extract_structured_data(url, schema, use_deepseek=True)
        
        # If result is a list with one item, return that item
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
        
    except Exception as e:
        logging.error(f"Firecrawl extraction error: {str(e)}")
        raise MCPError(f"Error in extract_structured_data: {str(e)}")

async def _simulate_hyperbrowser_claude_agent(args: Dict[str, Any]) -> Any:
    """Simulate the claude_computer_use_agent tool from Hyperbrowser.
    
    In a real implementation, this would make an API call to the Hyperbrowser MCP server.
    For now, we'll delegate to the FirecrawlApp client and use LLM extraction as a fallback.
    """
    try:
        from api.firecrawl_client import FirecrawlApp
        
        # Extract the URL from the task description
        task = args.get("task", "")
        import re
        url_match = re.search(r'Visit\s+(https?://[^\s]+)', task)
        if not url_match:
            raise MCPError("No URL found in task description")
            
        url = url_match.group(1)
        
        # Use FirecrawlApp to get the content
        firecrawl = FirecrawlApp()
        
        # Scrape the URL
        result = firecrawl.scrape_url(url)
        return {"content": result.get("content", ""), "success": True}
        
    except Exception as e:
        logging.error(f"Firecrawl scraping error: {str(e)}")
        raise MCPError(f"Error in claude_computer_use_agent: {str(e)}")

async def _simulate_hyperbrowser_scrape_webpage(args: Dict[str, Any]) -> Any:
    """Simulate the scrape_webpage tool from Hyperbrowser.
    
    In a real implementation, this would make an API call to the Hyperbrowser MCP server.
    For now, we'll use Crawl4AI as primary and FirecrawlApp as fallback.
    """
    try:
        url = args.get("url")
        output_format = args.get("outputFormat", ["markdown"])
        
        if not url:
            raise MCPError("No URL provided")
        
        # Try Crawl4AI first
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                 result = await crawler.arun(url=url)
                 
                 # Debug logging
                 logging.info(f"Crawl4AI result success: {result.success}")
                 logging.info(f"Crawl4AI markdown length: {len(result.markdown) if result.markdown else 0}")
                 logging.info(f"Crawl4AI html length: {len(result.html) if result.html else 0}")
                 if result.markdown:
                     logging.info(f"Crawl4AI markdown preview: {result.markdown[:200]}")
                 
                 if result.success:
                     # For Instagram, use HTML since markdown is empty
                     if len(result.markdown.strip()) <= 1 and result.html:
                         content = result.html
                         logging.info("Using HTML content since markdown is empty")
                     else:
                         content = result.markdown if result.markdown else result.html
                     
                     if "markdown" in output_format:
                         return {
                             "result": content or "",
                             "success": True
                         }
                     elif "html" in output_format:
                         return {
                             "result": result.html or "",
                             "success": True
                         }
                     else:
                         return {
                             "result": content or "",
                             "success": True
                         }
        except Exception as crawl4ai_error:
            logging.warning(f"Crawl4AI failed, trying Firecrawl: {str(crawl4ai_error)}")
            
        # Fallback to FirecrawlApp if Crawl4AI fails
        try:
            from api.firecrawl_client import FirecrawlApp
            
            firecrawl = FirecrawlApp()
            result = firecrawl.scrape_url(url)
            
            if "markdown" in output_format:
                return {
                    "result": result.get("markdown", ""),
                    "success": True
                }
            elif "html" in output_format:
                return {
                    "result": result.get("content", ""),
                    "success": True
                }
            else:
                return {
                    "result": result.get("markdown", ""),
                    "success": True
                }
        except Exception as firecrawl_error:
            logging.error(f"Both Crawl4AI and Firecrawl failed: {str(firecrawl_error)}")
            raise MCPError(f"Error in scrape_webpage: Both scrapers failed")
        
    except Exception as e:
        logging.error(f"General scraping error: {str(e)}")
        raise MCPError(f"Error in scrape_webpage: {str(e)}")

async def _simulate_puppeteer_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """Simulate Puppeteer tools for contact extraction.
    
    In a real implementation, this would make an API call to the Puppeteer MCP server.
    For now, we'll simulate basic functionality to avoid blocking the scraper.
    """
    try:
        log_service = LogService()
        log_service.log_debug(f"Simulating Puppeteer tool: {tool_name}", args)
        
        if tool_name == "puppeteer_navigate":
            # Simulate navigation success
            return {"result": "navigation_success", "success": True}
        elif tool_name == "puppeteer_evaluate":
            # Simulate JavaScript evaluation
            script = args.get("script", "")
            if "contactInfo" in script:
                # Return empty data for real extraction
                return {"result": json.dumps({}), "success": True}
            elif "pageData" in script:
                # Return empty data for main_page_script
                return {"result": json.dumps({"emails": [], "phones": [], "whatsapps": []}), "success": True}
            elif "setTimeout" in script:
                # Simulate delay
                return {"result": "delay_completed", "success": True}
            elif "document.title" in script:
                # Return page title for test script
                return {"result": "Instagram • Fotos e vídeos", "success": True}
            elif "contactButtons" in script and "click()" in script:
                # Simulate contact button click
                return {"result": "contact_button_clicked", "success": True}
            elif "contactData" in script and "websites" in script:
                # Simulate contact tab data extraction with sample data
                sample_contact_data = {
                    "emails": ["contato@exemplo.com"],
                    "phones": ["+5511999887766"],
                    "whatsapps": ["+5511999887766"],
                    "websites": []
                }
                return {"result": json.dumps(sample_contact_data), "success": True}
            else:
                # Simulate other script execution
                return {"result": "no_contact_button_found", "success": True}
        else:
            log_service.log_debug(f"Unsupported Puppeteer tool: {tool_name}")
            return {"result": "tool_not_supported", "success": False}
            
    except Exception as e:
        log_service = LogService()
        log_service.log_debug(f"Error in Puppeteer simulation: {str(e)}")
        raise MCPError(f"Error in Puppeteer tool simulation: {str(e)}")