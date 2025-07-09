#!/usr/bin/env node

/**
 * Web Search MCP Server
 * 
 * This server provides web search capability through the MCP interface,
 * allowing search queries to be made and results parsed and returned.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ErrorCode,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";
import { parse } from "node-html-parser";

/**
 * Create an MCP server for web search functionality
 */
const server = new Server(
  {
    name: "web-search-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * User-Agent string for making HTTP requests
 */
const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36";

/**
 * Interface for search result items
 */
interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

/**
 * Function to perform a web search query using DuckDuckGo
 * @param query Search query
 * @returns Parsed search results
 */
async function performWebSearch(query: string): Promise<SearchResult[]> {
  try {
    // Encode the query for URL
    const encodedQuery = encodeURIComponent(query);
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodedQuery}`;
    
    // Make the request with appropriate headers
    const response = await axios.get(searchUrl, {
      headers: {
        "User-Agent": USER_AGENT,
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
      },
      timeout: 10000,
    });

    // Parse the HTML response
    const root = parse(response.data);
    const results: SearchResult[] = [];

    // Extract search results
    const resultElements = root.querySelectorAll('.result');
    for (const element of resultElements) {
      const titleElement = element.querySelector('.result__title a');
      const urlElement = element.querySelector('.result__url');
      const snippetElement = element.querySelector('.result__snippet');
      
      if (titleElement && snippetElement) {
        const title = titleElement.text.trim();
        const url = titleElement.getAttribute('href') || '';
        const snippet = snippetElement.text.trim();
        
        // Only push results with actual content
        if (title && snippet) {
          results.push({
            title,
            url: url.startsWith('/') ? url : url, // Handle relative URLs if needed
            snippet,
          });
        }
      }
    }

    return results.slice(0, 10); // Return top 10 results to keep responses manageable
  } catch (error) {
    console.error("Search error:", error);
    if (axios.isAxiosError(error)) {
      throw new McpError(
        ErrorCode.InternalError,
        `Web search failed: ${error.message}`
      );
    }
    throw error;
  }
}

/**
 * Handler that lists available tools - providing the web_search tool
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "web_search",
        description: "Search the web for information on a given topic",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "The search query"
            }
          },
          required: ["query"]
        }
      }
    ]
  };
});

/**
 * Handler for the web_search tool
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name !== "web_search") {
    throw new McpError(ErrorCode.MethodNotFound, "Unknown tool");
  }

  const query = request.params.arguments?.query;
  if (!query || typeof query !== 'string') {
    throw new McpError(ErrorCode.InvalidParams, "Query parameter is required");
  }

  try {
    const results = await performWebSearch(query);
    
    if (results.length === 0) {
      return {
        content: [{
          type: "text",
          text: `No results found for query: "${query}"`
        }]
      };
    }

    // Format search results for display
    const formattedResults = results.map((result, index) => {
      return `[${index + 1}] ${result.title}\n    URL: ${result.url}\n    ${result.snippet}\n`;
    }).join("\n");

    return {
      content: [{
        type: "text",
        text: `Search results for: "${query}"\n\n${formattedResults}`
      }]
    };
  } catch (error) {
    console.error("Web search failed:", error);
    return {
      content: [{
        type: "text",
        text: error instanceof McpError ? error.message : `Search failed: ${String(error)}`
      }],
      isError: true
    };
  }
});

/**
 * Start the server using stdio transport
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Web search MCP server running on stdio");
  
  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    await server.close();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
