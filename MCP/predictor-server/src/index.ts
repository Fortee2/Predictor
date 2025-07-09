#!/usr/bin/env node

/**
 * Predictor MCP Server
 * 
 * This MCP server provides access to the Predictor stock portfolio management system.
 * It exposes portfolio management, transaction tracking, technical analysis, and market data
 * functionality through MCP tools and resources.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { promisify } from "util";
import * as path from "path";

// Environment variables for database connection
const DB_USER = process.env.DB_USER;
const DB_PASSWORD = process.env.DB_PASSWORD;
const DB_HOST = process.env.DB_HOST || 'localhost';
const DB_NAME = process.env.DB_NAME;
const PREDICTOR_PATH = process.env.PREDICTOR_PATH || '/Users/randycostner/source/Predictor';
const PYTHON_PATH = process.env.PYTHON_PATH || 'python';

if (!DB_USER || !DB_PASSWORD || !DB_NAME) {
  throw new Error('Database environment variables (DB_USER, DB_PASSWORD, DB_NAME) are required');
}

/**
 * Execute a Python command in the Predictor project directory
 */
async function executePythonCommand(command: string, args: string[] = []): Promise<string> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn(PYTHON_PATH, [command, ...args], {
      cwd: PREDICTOR_PATH,
      env: {
        ...process.env,
        DB_USER,
        DB_PASSWORD,
        DB_HOST,
        DB_NAME
      }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`Command failed with code ${code}: ${stderr}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * Parse JSON output from Python commands, handling potential formatting issues
 */
function parseJsonOutput(output: string): any {
  try {
    // Find JSON content between markers or extract clean JSON
    const lines = output.split('\n');
    const jsonLines = lines.filter(line => 
      line.trim().startsWith('{') || 
      line.trim().startsWith('[') || 
      line.includes('"') && (line.includes(':') || line.includes(','))
    );
    
    if (jsonLines.length > 0) {
      const jsonStr = jsonLines.join('\n');
      return JSON.parse(jsonStr);
    }
    
    // Fallback: try to parse the entire output
    return JSON.parse(output);
  } catch (error) {
    // If JSON parsing fails, return the raw output
    return { output: output.trim() };
  }
}

/**
 * Create the MCP server with portfolio management capabilities
 */
const server = new Server(
  {
    name: "predictor-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      resources: {},
      tools: {},
    },
  }
);

/**
 * Handler for listing available resources
 * Exposes portfolio data, market data, and analysis results as resources
 */
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  try {
    // Get list of portfolios to expose as resources
    const portfoliosOutput = await executePythonCommand('portfolio_cli.py', ['list-portfolios', '--json']);
    const portfolios = parseJsonOutput(portfoliosOutput);
    
    const resources = [];
    
    // Add portfolio resources
    if (Array.isArray(portfolios)) {
      for (const portfolio of portfolios) {
        resources.push({
          uri: `predictor://portfolio/${portfolio.id}`,
          mimeType: "application/json",
          name: `Portfolio: ${portfolio.name}`,
          description: `Portfolio details and holdings for ${portfolio.name}`
        });
        
        resources.push({
          uri: `predictor://portfolio/${portfolio.id}/transactions`,
          mimeType: "application/json", 
          name: `Transactions: ${portfolio.name}`,
          description: `Transaction history for portfolio ${portfolio.name}`
        });
        
        resources.push({
          uri: `predictor://portfolio/${portfolio.id}/performance`,
          mimeType: "application/json",
          name: `Performance: ${portfolio.name}`,
          description: `Performance metrics and analysis for portfolio ${portfolio.name}`
        });
      }
    }
    
    // Add market data resources
    resources.push({
      uri: `predictor://market/tickers`,
      mimeType: "application/json",
      name: "Available Tickers",
      description: "List of all available stock tickers in the system"
    });
    
    return { resources };
  } catch (error) {
    console.error('Error listing resources:', error instanceof Error ? error.message : String(error));
    return { resources: [] };
  }
});

/**
 * Handler for reading resource contents
 */
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const url = new URL(request.params.uri);
  const pathParts = url.pathname.split('/').filter(p => p);
  
  try {
    if (pathParts[0] === 'portfolio') {
      const portfolioId = pathParts[1];
      
      if (pathParts.length === 2) {
        // Portfolio details
        const output = await executePythonCommand('portfolio_cli.py', ['view-portfolio', portfolioId, '--json']);
        const data = parseJsonOutput(output);
        
        return {
          contents: [{
            uri: request.params.uri,
            mimeType: "application/json",
            text: JSON.stringify(data, null, 2)
          }]
        };
      } else if (pathParts[2] === 'transactions') {
        // Portfolio transactions
        const output = await executePythonCommand('portfolio_cli.py', ['view-transactions', portfolioId, '--json']);
        const data = parseJsonOutput(output);
        
        return {
          contents: [{
            uri: request.params.uri,
            mimeType: "application/json",
            text: JSON.stringify(data, null, 2)
          }]
        };
      } else if (pathParts[2] === 'performance') {
        // Portfolio performance
        const output = await executePythonCommand('portfolio_cli.py', ['view-performance', portfolioId, '--json']);
        const data = parseJsonOutput(output);
        
        return {
          contents: [{
            uri: request.params.uri,
            mimeType: "application/json",
            text: JSON.stringify(data, null, 2)
          }]
        };
      }
    } else if (pathParts[0] === 'market' && pathParts[1] === 'tickers') {
      // Market tickers list
      const output = await executePythonCommand('ticker_cli.py', ['list', '--json']);
      const data = parseJsonOutput(output);
      
      return {
        contents: [{
          uri: request.params.uri,
          mimeType: "application/json",
          text: JSON.stringify(data, null, 2)
        }]
      };
    }
    
    throw new McpError(ErrorCode.InvalidRequest, `Resource not found: ${request.params.uri}`);
  } catch (error) {
    throw new McpError(ErrorCode.InternalError, `Error reading resource: ${error instanceof Error ? error.message : String(error)}`);
  }
});

/**
 * Handler for listing available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      // Portfolio Management Tools
      {
        name: "create_portfolio",
        description: "Create a new investment portfolio",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string", description: "Portfolio name" },
            description: { type: "string", description: "Portfolio description" },
            initial_cash: { type: "number", description: "Initial cash balance (optional)", default: 0 }
          },
          required: ["name", "description"]
        }
      },
      {
        name: "list_portfolios",
        description: "List all portfolios",
        inputSchema: {
          type: "object",
          properties: {},
          required: []
        }
      },
      {
        name: "view_portfolio",
        description: "View detailed information about a specific portfolio",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "add_tickers_to_portfolio",
        description: "Add stock tickers to a portfolio",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            tickers: { 
              type: "array", 
              items: { type: "string" },
              description: "Array of ticker symbols to add" 
            }
          },
          required: ["portfolio_id", "tickers"]
        }
      },
      {
        name: "remove_tickers_from_portfolio",
        description: "Remove stock tickers from a portfolio",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            tickers: { 
              type: "array", 
              items: { type: "string" },
              description: "Array of ticker symbols to remove" 
            }
          },
          required: ["portfolio_id", "tickers"]
        }
      },
      
      // Transaction Management Tools
      {
        name: "log_transaction",
        description: "Log a buy, sell, or dividend transaction",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            transaction_type: { 
              type: "string", 
              enum: ["buy", "sell", "dividend"],
              description: "Type of transaction" 
            },
            date: { type: "string", description: "Transaction date (YYYY-MM-DD)" },
            ticker: { type: "string", description: "Stock ticker symbol" },
            shares: { type: "number", description: "Number of shares (for buy/sell)" },
            price: { type: "number", description: "Price per share (for buy/sell)" },
            amount: { type: "number", description: "Dividend amount (for dividend transactions)" }
          },
          required: ["portfolio_id", "transaction_type", "date", "ticker"]
        }
      },
      {
        name: "view_transactions",
        description: "View transaction history for a portfolio",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Filter by specific ticker (optional)" }
          },
          required: ["portfolio_id"]
        }
      },
      
      // Cash Management Tools
      {
        name: "manage_cash",
        description: "Manage cash in a portfolio (deposit, withdraw, or view balance)",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            action: { 
              type: "string", 
              enum: ["deposit", "withdraw", "view"],
              description: "Cash management action" 
            },
            amount: { type: "number", description: "Amount for deposit/withdraw operations" }
          },
          required: ["portfolio_id", "action"]
        }
      },
      
      // Analysis Tools
      {
        name: "analyze_rsi",
        description: "Analyze RSI (Relative Strength Index) for portfolio holdings",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Specific ticker to analyze (optional)" }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "analyze_moving_averages",
        description: "Analyze moving averages for portfolio holdings",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Specific ticker to analyze (optional)" },
            period: { type: "number", description: "Moving average period (default: 20)", default: 20 }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "analyze_bollinger_bands",
        description: "Analyze Bollinger Bands for portfolio holdings",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Specific ticker to analyze (optional)" }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "analyze_news_sentiment",
        description: "Analyze news sentiment for portfolio holdings",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Specific ticker to analyze (optional)" },
            update: { type: "boolean", description: "Fetch latest news before analysis", default: false }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "view_fundamentals",
        description: "View fundamental analysis data for portfolio holdings",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            ticker_symbol: { type: "string", description: "Specific ticker to analyze (optional)" }
          },
          required: ["portfolio_id"]
        }
      },
      {
        name: "view_performance",
        description: "View portfolio performance metrics and charts",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            start_date: { type: "string", description: "Start date for analysis (YYYY-MM-DD, optional)" },
            end_date: { type: "string", description: "End date for analysis (YYYY-MM-DD, optional)" },
            chart: { type: "boolean", description: "Generate performance chart", default: false }
          },
          required: ["portfolio_id"]
        }
      },
      
      // Market Data Tools
      {
        name: "add_ticker",
        description: "Add a new ticker to the system",
        inputSchema: {
          type: "object",
          properties: {
            symbol: { type: "string", description: "Stock ticker symbol" },
            name: { type: "string", description: "Company name" }
          },
          required: ["symbol", "name"]
        }
      },
      {
        name: "update_ticker_data",
        description: "Update market data for a specific ticker",
        inputSchema: {
          type: "object",
          properties: {
            symbol: { type: "string", description: "Stock ticker symbol" }
          },
          required: ["symbol"]
        }
      },
      {
        name: "list_tickers",
        description: "List all available tickers in the system",
        inputSchema: {
          type: "object",
          properties: {},
          required: []
        }
      },
      {
        name: "calculate_portfolio_value",
        description: "Calculate current portfolio value based on latest market prices",
        inputSchema: {
          type: "object",
          properties: {
            portfolio_id: { type: "string", description: "Portfolio ID" },
            date: { type: "string", description: "Calculation date (YYYY-MM-DD, optional - defaults to today)" }
          },
          required: ["portfolio_id"]
        }
      }
    ]
  };
});

/**
 * Handler for tool execution
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  // Type guard to ensure args exists and is an object
  if (!args || typeof args !== 'object') {
    return {
      content: [{
        type: "text",
        text: `Error: Invalid arguments provided for tool ${name}`
      }],
      isError: true
    };
  }
  
  try {
    let output: string;
    let result: any;
    
    switch (name) {
      // Portfolio Management
      case "create_portfolio":
        output = await executePythonCommand('portfolio_cli.py', [
          'create-portfolio',
          String(args.name || ''),
          String(args.description || ''),
          ...(args.initial_cash ? ['--initial-cash', String(args.initial_cash)] : [])
        ]);
        result = parseJsonOutput(output);
        break;
        
      case "list_portfolios":
        output = await executePythonCommand('portfolio_cli.py', ['list-portfolios']);
        result = { output: output.trim() };
        break;
        
      case "view_portfolio":
        output = await executePythonCommand('portfolio_cli.py', ['view-portfolio', String(args.portfolio_id || '')]);
        result = { output: output.trim() };
        break;
        
      case "add_tickers_to_portfolio":
        const addTickers = Array.isArray(args.tickers) ? args.tickers.map(String) : [];
        output = await executePythonCommand('portfolio_cli.py', [
          'add-tickers',
          String(args.portfolio_id || ''),
          ...addTickers
        ]);
        result = { output: output.trim() };
        break;
        
      case "remove_tickers_from_portfolio":
        const removeTickers = Array.isArray(args.tickers) ? args.tickers.map(String) : [];
        output = await executePythonCommand('portfolio_cli.py', [
          'remove-tickers',
          String(args.portfolio_id || ''),
          ...removeTickers
        ]);
        result = { output: output.trim() };
        break;
        
      // Transaction Management
      case "log_transaction":
        const transactionArgs = [
          'log-transaction',
          String(args.portfolio_id || ''),
          String(args.transaction_type || ''),
          String(args.date || ''),
          String(args.ticker || '')
        ];
        
        if (args.shares) transactionArgs.push('--shares', String(args.shares));
        if (args.price) transactionArgs.push('--price', String(args.price));
        if (args.amount) transactionArgs.push('--amount', String(args.amount));
        
        output = await executePythonCommand('portfolio_cli.py', transactionArgs);
        result = { output: output.trim() };
        break;
        
      case "view_transactions":
        const viewTransactionArgs = ['view-transactions', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          viewTransactionArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        
        output = await executePythonCommand('portfolio_cli.py', viewTransactionArgs);
        result = { output: output.trim() };
        break;
        
      // Cash Management
      case "manage_cash":
        const cashArgs = ['manage-cash', String(args.portfolio_id || ''), String(args.action || '')];
        if (args.amount) {
          cashArgs.push('--amount', String(args.amount));
        }
        
        output = await executePythonCommand('portfolio_cli.py', cashArgs);
        result = { output: output.trim() };
        break;
        
      // Analysis Tools
      case "analyze_rsi":
        const rsiArgs = ['analyze-rsi', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          rsiArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        
        output = await executePythonCommand('portfolio_cli.py', rsiArgs);
        result = { output: output.trim() };
        break;
        
      case "analyze_moving_averages":
        const maArgs = ['analyze-ma', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          maArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        if (args.period) {
          maArgs.push('--period', String(args.period));
        }
        
        output = await executePythonCommand('portfolio_cli.py', maArgs);
        result = { output: output.trim() };
        break;
        
      case "analyze_bollinger_bands":
        const bbArgs = ['analyze-bb', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          bbArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        
        output = await executePythonCommand('portfolio_cli.py', bbArgs);
        result = { output: output.trim() };
        break;
        
      case "analyze_news_sentiment":
        const newsArgs = ['analyze-news', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          newsArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        if (args.update) {
          newsArgs.push('--update');
        }
        
        output = await executePythonCommand('portfolio_cli.py', newsArgs);
        result = { output: output.trim() };
        break;
        
      case "view_fundamentals":
        const fundamentalsArgs = ['view-fundamentals', String(args.portfolio_id || '')];
        if (args.ticker_symbol) {
          fundamentalsArgs.push('--ticker_symbol', String(args.ticker_symbol));
        }
        
        output = await executePythonCommand('portfolio_cli.py', fundamentalsArgs);
        result = { output: output.trim() };
        break;
        
      case "view_performance":
        const performanceArgs = ['view-performance', String(args.portfolio_id || '')];
        if (args.start_date) {
          performanceArgs.push('--start_date', String(args.start_date));
        }
        if (args.end_date) {
          performanceArgs.push('--end_date', String(args.end_date));
        }
        if (args.chart) {
          performanceArgs.push('--chart');
        }
        
        output = await executePythonCommand('portfolio_cli.py', performanceArgs);
        result = { output: output.trim() };
        break;
        
      // Market Data Tools
      case "add_ticker":
        output = await executePythonCommand('ticker_cli.py', ['add', String(args.symbol || ''), String(args.name || '')]);
        result = { output: output.trim() };
        break;
        
      case "update_ticker_data":
        output = await executePythonCommand('ticker_cli.py', ['update-data', String(args.symbol || '')]);
        result = { output: output.trim() };
        break;
        
      case "list_tickers":
        output = await executePythonCommand('ticker_cli.py', ['list']);
        result = { output: output.trim() };
        break;
        
      case "calculate_portfolio_value":
        const valueArgs = ['calculate-value', String(args.portfolio_id || '')];
        if (args.date) {
          valueArgs.push('--date', String(args.date));
        }
        
        output = await executePythonCommand('portfolio_cli.py', valueArgs);
        result = { output: output.trim() };
        break;
        
      default:
        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    }
    
    return {
      content: [{
        type: "text",
        text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
      }]
    };
    
  } catch (error) {
    return {
      content: [{
        type: "text",
        text: `Error executing ${name}: ${error instanceof Error ? error.message : String(error)}`
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
  console.error("Predictor MCP server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
