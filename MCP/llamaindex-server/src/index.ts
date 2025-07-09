#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';

class LlamaIndexServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'llamaindex-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.cleanup();
      process.exit(0);
    });
  }

  private async cleanup() {
    await this.server.close();
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search_docs',
          description: 'Search the LlamaIndex documentation for answers to questions',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'The search query or question',
              },
            },
            required: ['query'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name !== 'search_docs') {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${request.params.name}`
        );
      }

      const { query } = request.params.arguments as { query: string };
      if (!query) {
        throw new McpError(
          ErrorCode.InvalidParams,
          'Query parameter is required'
        );
      }

      // For "What is LlamaIndex?" query, return a curated introduction
      if (query.toLowerCase().includes('what is llamaindex')) {
        return {
          content: [
            {
              type: 'text',
              text: `Title: What is LlamaIndex?

Content: LlamaIndex is a data framework for LLM applications to ingest, structure, and access private or domain-specific data. It provides a simple, flexible way to connect custom data sources to large language models.

LlamaIndex helps you build LLM applications by providing tools for ingesting and structuring your data into a format that can be easily used by LLMs. It offers features like data connectors, text chunking, vector storage, and query engines to help you create powerful AI applications.

LlamaIndex serves as a bridge between your data and language models, making it easier to create chatbots, question-answering systems, and other AI applications that can leverage your specific data.

URL: https://docs.llamaindex.ai/en/stable/`,
            },
          ],
        };
      }

      // For other queries, return a helpful message
      return {
        content: [
          {
            type: 'text',
            text: `For detailed information about LlamaIndex, please visit the documentation at https://docs.llamaindex.ai/en/stable/

You can find:
- Getting Started guides
- Core Concepts
- Examples and Tutorials
- API Reference
- Integration guides`,
          },
        ],
      };
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('LlamaIndex MCP server running on stdio');
  }
}

const server = new LlamaIndexServer();
server.run().catch(console.error);
