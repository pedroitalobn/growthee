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
    For now, we'll delegate to the FirecrawlApp client to maintain functionality.
    """
    try:
        from api.firecrawl_client import FirecrawlApp
        
        url = args.get("url")
        output_format = args.get("outputFormat", ["markdown"])
        
        if not url:
            raise MCPError("No URL provided")
            
        # Use FirecrawlApp as a fallback
        firecrawl = FirecrawlApp()
        result = firecrawl.scrape_url(url)
        
        response = {}
        
        if "markdown" in output_format:
            response["markdown"] = result.get("markdown", "")
            
        if "html" in output_format:
            response["html"] = result.get("content", "")
            
        if "links" in output_format:
            # Extract links from HTML using BeautifulSoup
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.get("content", ""), "html.parser")
                links = [a.get("href") for a in soup.find_all("a", href=True)]
                response["links"] = links
            except Exception:
                response["links"] = []
                
        if "screenshot" in output_format:
            # We can't actually take a screenshot in this simulation
            response["screenshot"] = "Screenshot not available in simulation mode"
            
        return response
        
    except Exception as e:
        logging.error(f"Firecrawl scraping error: {str(e)}")
        raise MCPError(f"Error in scrape_webpage: {str(e)}")