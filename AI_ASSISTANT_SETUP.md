# 🤖 AI Assistant Setup Guide for Predictor

This guide will help you set up the LLM-powered AI assistant feature for your Predictor portfolio management system.

## Overview

The AI Assistant provides natural language interaction with your portfolio data using:
- **llama-index**: Framework for building LLM applications with your data
- **Ollama**: Local LLM hosting (llama3.2 model)  
- **ChromaDB**: Vector database for portfolio data indexing
- **Rich CLI**: Beautiful terminal interface

## Features

- 🤖 **Interactive Chat**: Ask natural language questions about your portfolio
- 📈 **Weekly Recommendations**: AI-generated investment insights for the upcoming week
- 📊 **Performance Analysis**: Comprehensive portfolio analysis with specific metrics
- ⚠️ **Risk Assessment**: Detailed risk evaluation and mitigation strategies
- 💾 **Export Reports**: Save AI analysis to timestamped Markdown files

## Prerequisites

1. **Python 3.11+** with virtual environment
2. **MySQL Database** (already configured in your Predictor app)
3. **Ollama** for local LLM hosting

## Installation Steps

### Step 1: Install Ollama

#### macOS (Recommended)
```bash
# Download and install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Alternative: Download from https://ollama.ai
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Windows
Download the installer from [https://ollama.ai](https://ollama.ai)

### Step 2: Install LLM Model

```bash
# Pull the llama3.2 model (3B parameters - good balance of speed/quality)
ollama pull llama3.2:3b

# Alternative: For faster responses (1B model)
ollama pull llama3.2:1b

# Alternative: For better quality (8B model - requires more RAM)
ollama pull llama3.2:8b

# Pull embedding model for document indexing
ollama pull nomic-embed-text
```

### Step 3: Start Ollama Server

```bash
# Start Ollama server (keep this running)
ollama serve

# Test connection (in another terminal)
curl http://localhost:11434/api/version
```

### Step 4: Install Python Dependencies (Manual)

Due to dependency conflicts, install packages manually:

```bash
# Activate your virtual environment
source venv/bin/activate  # or your venv path

# Install llama-index packages individually
pip install llama-index==0.11.21
pip install llama-index-llms-ollama==0.3.6  
pip install llama-index-embeddings-ollama==0.3.1

# Install ChromaDB (older compatible version)
pip install chromadb==0.4.24
pip install llama-index-vector-stores-chroma==0.1.10

# Install additional dependencies if needed
pip install rich==13.9.4
pip install nltk==3.9.2
```

### Step 5: Test Installation

```bash
# Test the enhanced CLI
python enhanced_cli.py

# Navigate to: Analysis Tools → 🤖 AI Portfolio Assistant
```

## Configuration

### Model Selection

You can modify the model in `enhanced_cli/ai_assistant_views.py`:

```python
# In create_llm_analyzer() function
analyzer = LLMPortfolioAnalyzer(
    model_name="llama3.2:3b"  # Change this to your preferred model
)
```

Available models:
- `llama3.2:1b` - Fastest, good for basic queries
- `llama3.2:3b` - Balanced performance (recommended)
- `llama3.2:8b` - Best quality, requires more resources

### Database Configuration

Ensure your `.env` file has the correct database credentials:

```bash
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=investing
```

## Usage Examples

### Interactive Chat
Ask questions like:
- "What analysis can you give me about my investing portfolio?"
- "Do you have any recommendations for the upcoming week?"
- "Which of my stocks are overbought according to RSI?"
- "What's my portfolio's risk level and how can I reduce it?"

### Weekly Recommendations
Get AI-generated insights including:
- Stocks to watch closely
- Technical signals for buy/sell opportunities
- Risk factors to monitor
- Portfolio rebalancing suggestions

### Performance Analysis
Comprehensive analysis covering:
- Overall performance assessment with numbers
- Best/worst performing positions
- Risk assessment and diversification
- Technical indicator interpretation
- News sentiment impact

## Troubleshooting

### Common Issues

#### 1. "Module not found: llama_index"
```bash
# Reinstall dependencies
pip install llama-index==0.11.21
```

#### 2. "Connection refused to Ollama"
```bash
# Check if Ollama is running
ollama serve

# Test connection
curl http://localhost:11434/api/version
```

#### 3. "Model not found"
```bash
# Pull the model
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

#### 4. "ChromaDB errors"
```bash
# Clear ChromaDB cache
rm -rf ./chroma_db

# Reinstall ChromaDB
pip uninstall chromadb
pip install chromadb==0.4.24
```

#### 5. "Memory issues"
Use a smaller model:
```bash
ollama pull llama3.2:1b
# Then update model_name in the code to "llama3.2:1b"
```

### Performance Tips

1. **Model Selection**:
   - Use `llama3.2:1b` for fastest responses
   - Use `llama3.2:3b` for balanced performance
   - Use `llama3.2:8b` only if you have 16GB+ RAM

2. **System Resources**:
   - Minimum 8GB RAM for 3B model
   - 16GB+ RAM recommended for 8B model
   - SSD storage recommended for better performance

3. **Network**:
   - Ensure Ollama server is running on localhost:11434
   - Check firewall settings if connection issues occur

## Data Integration

The AI assistant automatically creates rich context from:
- **Portfolio Holdings**: Current positions, cost basis, gains/losses
- **Technical Analysis**: RSI, moving averages, Bollinger Bands
- **Fundamental Data**: P/E ratios, market cap, dividend yields
- **News Sentiment**: Recent news analysis using FinBERT
- **Transaction History**: Recent buy/sell/dividend activity

## Menu Navigation

In the Enhanced CLI:
1. Main Menu → Analysis Tools (option 4)
2. Analysis Tools Menu:
   - Option 8: 🤖 AI Portfolio Assistant
   - Option 9: 📈 Weekly AI Recommendations  
   - Option 10: 📊 AI Performance Analysis
   - Option 11: ⚠️ AI Risk Assessment

## Files Created/Modified

- `data/llm_integration.py` - Core LLM integration logic
- `enhanced_cli/ai_assistant_views.py` - CLI interface for AI features
- `enhanced_cli/main.py` - Updated to include AI menu options
- `requirements.txt` - Updated with LLM dependencies
- `AI_ASSISTANT_SETUP.md` - This setup guide

## Security Notes

- All data processing happens locally
- No data is sent to external APIs
- Ollama runs entirely on your machine
- Portfolio data never leaves your system

## Support

If you encounter issues:
1. Check this troubleshooting guide
2. Verify Ollama is running: `ollama serve`
3. Test model availability: `ollama list`
4. Check database connectivity in your existing Predictor features

The AI assistant integrates seamlessly with your existing Predictor functionality, providing intelligent analysis of your portfolio data through natural language interaction.
