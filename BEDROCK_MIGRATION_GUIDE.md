# Migration Guide: Ollama to AWS Bedrock

This guide will help you migrate from the Ollama-based AI assistant to AWS Bedrock Converse API.

## Overview of Changes

The AI assistant has been upgraded from using local Ollama models to AWS Bedrock's cloud-based models:

- **Before**: Local Ollama server with llama3.2 models
- **After**: AWS Bedrock with Claude 3.5 Sonnet and Titan Embeddings

### Benefits of AWS Bedrock

1. **No Local Setup**: No need to run a local Ollama server
2. **Enterprise-Grade Models**: Access to Claude 3.5 Sonnet, one of the most capable AI models
3. **Scalability**: Cloud-based infrastructure handles any workload
4. **Cost-Effective**: Pay only for what you use
5. **Reliability**: AWS-managed service with high availability

## Migration Steps

### Step 1: Install Updated Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `boto3` and `botocore` for AWS SDK
- `llama-index-llms-bedrock-converse` for Bedrock integration
- `llama-index-embeddings-bedrock` for embedding models

### Step 2: Set Up AWS Credentials

#### Option A: AWS CLI (Recommended)

1. Install AWS CLI if you haven't already:
   ```bash
   # macOS
   brew install awscli
   
   # Or download from https://aws.amazon.com/cli/
   ```

2. Configure your credentials:
   ```bash
   aws configure
   ```
   
   Enter:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (use `us-east-1` or `us-west-2`)
   - Default output format (can be `json`)

#### Option B: Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your AWS credentials:
   ```
   AWS_ACCESS_KEY_ID=your_actual_access_key_id
   AWS_SECRET_ACCESS_KEY=your_actual_secret_access_key
   AWS_REGION=us-east-1
   ```

### Step 3: Request Bedrock Model Access

1. Sign in to the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock**
3. Click on **Model access** in the left sidebar
4. Click **Manage model access** (or **Edit** if already configured)
5. Request access to:
   - **Anthropic** → **Claude 3.5 Sonnet v2**
   - **Amazon** → **Titan Embeddings G1 - Text v2**
6. Submit the access request

**Note**: Model access requests are usually approved within a few minutes, but can take up to 24 hours.

### Step 4: Verify Configuration

Test your AWS Bedrock connection:

```bash
aws bedrock list-foundation-models --region us-east-1
```

You should see a list of available models including Claude and Titan models.

### Step 5: Remove Ollama (Optional)

If you were using Ollama locally, you can now remove it:

```bash
# Stop Ollama service
# On macOS/Linux:
pkill ollama

# Uninstall (optional)
# macOS:
brew uninstall ollama

# The Ollama models can also be removed to free up space
rm -rf ~/.ollama
```

### Step 6: Update Environment Variables

If you had custom Ollama settings in your `.env` file, remove them:

**Remove these:**
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
```

**Keep or add these:**
```
AWS_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
```

## Code Changes Summary

### File: `data/llm_integration.py`

- **Before**: Used `Ollama` and `OllamaEmbedding` classes
- **After**: Uses `BedrockConverse` and `BedrockEmbedding` classes
- Connection setup changed from HTTP host to AWS client initialization

### File: `data/config.py`

- **Before**: `get_ollama_config()` method
- **After**: `get_bedrock_config()` method

### File: `enhanced_cli/ai_assistant_views.py`

- Updated to use Bedrock configuration
- Updated setup help documentation
- Changed connection check from Ollama to Bedrock

### File: `requirements.txt`

- Removed: `llama-index-llms-ollama`, `llama-index-embeddings-ollama`
- Added: `llama-index-llms-bedrock-converse`, `llama-index-embeddings-bedrock`, `boto3`, `botocore`

## Testing the Migration

After completing the migration, test the AI assistant:

1. Launch the application:
   ```bash
   python enhanced_cli/main.py
   ```

2. Select a portfolio

3. Try an AI command:
   ```
   > ai_chat
   ```

4. Ask a test question:
   ```
   What's the current state of my portfolio?
   ```

If everything is configured correctly, you should receive an AI-generated analysis.

## Cost Considerations

### AWS Bedrock Pricing (as of 2025)

**Claude 3.5 Sonnet:**
- Input: ~$3.00 per million tokens
- Output: ~$15.00 per million tokens

**Titan Embeddings:**
- ~$0.10 per million tokens

**Typical Usage:**
- Portfolio analysis query: ~5,000-10,000 tokens ($0.05-$0.15)
- Weekly recommendations: ~10,000-15,000 tokens ($0.15-$0.25)
- Vector embeddings: ~5,000 tokens per portfolio index ($0.0005)

**Monthly estimate** for moderate use (10 queries/day): ~$15-30/month

### Cost Optimization Tips

1. **Use Claude Haiku** for simpler queries (10x cheaper):
   ```
   BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
   ```

2. **Monitor usage** in AWS Cost Explorer

3. **Set billing alerts** in AWS to avoid surprises

4. **Cache embeddings** - The system already caches vector indices per portfolio

## Troubleshooting

### Error: "NoCredentialsError"

**Solution**: Your AWS credentials are not configured. Run `aws configure` or set environment variables.

### Error: "AccessDeniedException" when calling Bedrock

**Solution**: Request model access in the AWS Bedrock console (see Step 3 above).

### Error: "Could not connect to the endpoint URL"

**Solution**: 
- Check your AWS region is correct
- Verify Bedrock is available in your region (use us-east-1 or us-west-2)
- Check your internet connection

### Error: "ValidationException: The provided model identifier is invalid"

**Solution**: Verify the model ID is correct. Check available models:
```bash
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
```

### Slow Response Times

**Solution**:
- Bedrock response times are typically 2-5 seconds
- Network latency may affect response time
- Consider using Claude Haiku for faster responses

## Rollback Instructions

If you need to rollback to Ollama:

1. Restore the previous version from git:
   ```bash
   git checkout HEAD~1 -- requirements.txt data/llm_portfolio_analyzer.py data/config.py enhanced_cli/ai_assistant_views.py
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start Ollama server:
   ```bash
   ollama serve
   ```

4. Pull required model:
   ```bash
   ollama pull llama3.2:3b
   ```

## Support and Resources

- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **Claude Model Guide**: https://docs.anthropic.com/claude/docs
- **LlamaIndex Bedrock**: https://docs.llamaindex.ai/en/stable/examples/llm/bedrock_converse/
- **AWS Pricing Calculator**: https://calculator.aws/

## Frequently Asked Questions

**Q: Can I still use Ollama locally?**  
A: Not with the current version. The codebase has been migrated to Bedrock. You would need to maintain a separate branch for Ollama support.

**Q: Which AWS region should I use?**  
A: Use `us-east-1` (N. Virginia) or `us-west-2` (Oregon) as they have the best Bedrock model availability.

**Q: How do I switch between Claude models?**  
A: Update the `BEDROCK_MODEL` environment variable in your `.env` file.

**Q: Is my data sent to AWS?**  
A: Yes, portfolio data is sent to AWS Bedrock for analysis. AWS has strong data privacy protections, but review their terms if you have concerns.

**Q: Can I use this without AWS credentials?**  
A: No, AWS Bedrock requires valid AWS credentials and an active AWS account.

## Conclusion

The migration from Ollama to AWS Bedrock provides a more robust, scalable, and powerful AI assistant for portfolio analysis. While it introduces cloud costs, the improved model capabilities and zero local infrastructure requirements make it worthwhile for most users.

If you encounter any issues during migration, please check the troubleshooting section or consult the AWS Bedrock documentation.
