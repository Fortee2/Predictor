# LLM Analysis Consistency Recommendations

## Executive Summary

Based on analysis of your `LLMPortfolioAnalyzer` implementation, here are specific recommendations to ensure consistent LLM analysis results across multiple uses.

---

## Critical Consistency Issues Identified

### 1. **Temperature Setting**
**Current State:** Temperature = 0.1
**Issue:** While low, this still allows some randomness in responses
**Impact:** Same question may produce slightly different answers

### 2. **No Deterministic Seeding**
**Current State:** No seed parameter in inference config
**Issue:** Cannot reproduce exact same output for identical inputs
**Impact:** Testing and debugging are difficult

### 3. **Conversation History Persistence**
**Current State:** History accumulates across chat() calls
**Issue:** Previous context influences new analyses unpredictably
**Impact:** Same query produces different results based on conversation state

### 4. **Loose Output Formatting**
**Current State:** System prompt doesn't enforce structured output
**Issue:** LLM chooses its own response structure
**Impact:** Inconsistent response formats

### 5. **Variable Tool Result Formats**
**Current State:** Tool results return different data structures
**Issue:** LLM must interpret varying formats
**Impact:** Inconsistent analysis based on data interpretation

---

## Recommended Solutions

### 1. **Minimize Temperature and Add Top-P Control**

**Change in `llm_portfolio_analyzer.py` line ~521:**

```python
# BEFORE
inferenceConfig={
    "temperature": 0.1,
    "maxTokens": 4096
}

# AFTER
inferenceConfig={
    "temperature": 0.0,  # Maximum determinism
    "topP": 1.0,         # Use all probability mass
    "maxTokens": 4096
}
```

**Rationale:** Temperature of 0.0 produces the most deterministic outputs.

**Note:** AWS Bedrock Claude models do not allow both `temperature` and `topP` to be specified together. Using `temperature: 0.0` alone provides maximum determinism.

---

### 2. **Add Conversation Context Management**

**Add new parameter to `chat()` method:**

```python
def chat(
    self,
    user_message: str,
    portfolio_id: Optional[int] = None,
    max_turns: int = 10,
    reset_context: bool = True  # NEW PARAMETER
) -> str:
    """
    Chat with the LLM using tool calling for portfolio analysis.

    Args:
        user_message: The user's question or request
        portfolio_id: Optional portfolio ID for context
        max_turns: Maximum number of conversation turns
        reset_context: If True, clears conversation history before this request
    """
    try:
        # Clear history for consistent, context-free analysis
        if reset_context:
            self.reset_conversation()
        
        # Rest of implementation...
```

**Rationale:** Each analysis should start from a clean slate unless explicitly continuing a conversation. This prevents context bleed between analyses.

---

### 3. **Enforce Structured Output Format**

**Update system prompt in `_get_system_prompt()` method:**

```python
def _get_system_prompt(self, portfolio_id: Optional[int] = None) -> List[Dict]:
    """Get system prompt configuration for the LLM."""
    
    base_prompt = """You are a professional financial advisor and portfolio analyst.
You have access to comprehensive portfolio data, technical analysis tools, fundamental metrics,
and news sentiment analysis.

CRITICAL OUTPUT FORMAT REQUIREMENTS:
You MUST structure your responses with these exact sections in this order:

1. **SUMMARY** (2-3 sentences maximum)
   - Key finding or recommendation
   - Confidence level (High/Medium/Low)

2. **DATA ANALYSIS** (bullet points only)
   - List specific metrics and their values
   - Technical indicators with current readings
   - Fundamental data points

3. **INTERPRETATION** (structured paragraphs)
   - What the data means
   - Why it matters
   - Context and comparisons

4. **RECOMMENDATIONS** (numbered list)
   - Specific, actionable steps
   - Include price targets, quantities, and timeframes
   - Priority order (1=highest priority)

5. **RISK FACTORS** (bullet points)
   - Potential downsides
   - What to monitor
   - Stop-loss levels if applicable

IMPORTANT INSTRUCTIONS:
1. Always use the available tools to get accurate, up-to-date information
2. Provide specific, actionable insights backed by data
3. When analyzing portfolios, consider the 70/30 Core Strategy:
   - Core positions (70%): Long-term holds (VTI, FSPSX, VEA, JNJ, BND, KO, quality dividend stocks)
     - Entry: Fundamental strength + reasonable valuation
     - Exit: Only on fundamental breakdown or major trend reversal
     - Technical analysis: Use for sizing (add on dips), NOT for selling

   - Swing positions (30%): Tactical opportunities (weeks to 6 months)
     - 3-6 positions at any time
     - Entry: Technical setup (oversold RSI, MACD buy, support bounce)
     - Exit: Technical signals (overbought, MACD sell, resistance)
     - Stop-losses: Always use, 5-8% max loss

4. When recommending trades, always consider:
   - Current cash balance
   - Position sizing (never exceed 10% per position for swing trades)
   - Risk management (use stop-losses)
   - Technical and fundamental signals alignment

5. FORMAT REQUIREMENTS:
   - Use exact dollar amounts: $1,234.56 (not "around $1,200")
   - Use exact percentages: 15.3% (not "about 15%")
   - Always include dates in ISO format: 2026-01-05
   - Use consistent decimal places: 2 for dollars, 1-2 for percentages
   - Include ticker symbols in UPPERCASE

6. Handle errors gracefully and explain any data limitations

Available tool categories:
- Portfolio queries: Get portfolios, positions, balances, transactions
- Technical analysis: RSI, MACD, Moving Averages, Bollinger Bands, Stochastic, Trends
- Fundamental data: P/E ratios, market cap, dividend yields, growth metrics
- News sentiment: Recent news analysis with sentiment scores
- Write operations: Log transactions, manage cash
- Watchlists: Manage and analyze watchlist securities
"""

    return [{"text": base_prompt}]
```

**Rationale:** Explicit structure requirements force consistent output formatting regardless of the query.

---

### 4. **Standardize Tool Result Formatting**

**Add a new method to normalize all tool results:**

```python
def _normalize_tool_result(self, tool_name: str, result: Dict) -> Dict:
    """
    Normalize tool results to consistent format.
    
    Args:
        tool_name: Name of the tool
        result: Raw tool result
        
    Returns:
        Normalized result with consistent structure
    """
    # Always include metadata
    normalized = {
        "tool_name": tool_name,
        "timestamp": datetime.now().isoformat(),
        "success": "error" not in result,
        "data": result if "error" not in result else None,
        "error": result.get("error")
    }
    
    # Round all numeric values to consistent precision
    def round_numbers(obj):
        if isinstance(obj, float):
            return round(obj, 4)
        elif isinstance(obj, Decimal):
            return round(float(obj), 4)
        elif isinstance(obj, dict):
            return {k: round_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [round_numbers(item) for item in obj]
        return obj
    
    if normalized["data"]:
        normalized["data"] = round_numbers(normalized["data"])
    
    return normalized
```

**Update `_execute_tool()` to use normalization:**

```python
def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
    """Execute a tool call and return normalized results."""
    try:
        # ... existing tool execution code ...
        raw_result = # whatever the tool returns
        
        # Normalize before returning
        return self._normalize_tool_result(tool_name, raw_result)
        
    except Exception as e:
        self.logger.error(f"Error executing tool {tool_name}: {e}")
        return self._normalize_tool_result(tool_name, {
            "error": str(e),
            "error_type": type(e).__name__
        })
```

**Rationale:** Consistent data formats lead to consistent interpretations by the LLM.

---

### 5. **Add Validation Layer for Critical Metrics**

**Create a new validation method:**

```python
def _validate_analysis_data(self, tool_results: List[Dict]) -> Dict:
    """
    Validate that critical data points are present and reasonable.
    
    Returns:
        Dictionary with validation status and any warnings
    """
    validation = {
        "valid": True,
        "warnings": [],
        "data_quality": "high"
    }
    
    for result in tool_results:
        tool_name = result.get("tool_name")
        data = result.get("data", {})
        
        # Validate RSI values
        if tool_name == "calculate_rsi":
            rsi_value = data.get("rsi_value")
            if rsi_value is not None:
                if not (0 <= rsi_value <= 100):
                    validation["warnings"].append(
                        f"RSI value {rsi_value} is out of normal range [0-100]"
                    )
                    validation["data_quality"] = "medium"
        
        # Validate price data
        if "price" in data or "current_price" in data:
            price = data.get("price") or data.get("current_price")
            if price is not None and price <= 0:
                validation["warnings"].append(
                    f"Invalid price {price} in {tool_name}"
                )
                validation["valid"] = False
        
        # Validate share quantities
        if "shares" in data:
            shares = data.get("shares")
            if shares is not None and shares < 0:
                validation["warnings"].append(
                    f"Invalid share quantity {shares} in {tool_name}"
                )
                validation["valid"] = False
    
    return validation
```

**Rationale:** Bad data leads to inconsistent analysis. Catching data quality issues early ensures more reliable outputs.

---

### 6. **Implement Response Caching for Identical Queries**

**Add caching mechanism:**

```python
import hashlib
import json
from functools import lru_cache

class LLMPortfolioAnalyzer:
    def __init__(self, ...):
        # ... existing init code ...
        self._response_cache = {}  # Add cache dictionary
        self._cache_ttl_seconds = 300  # 5 minute cache
    
    def _get_cache_key(self, user_message: str, portfolio_id: Optional[int]) -> str:
        """Generate cache key for a query."""
        key_data = {
            "message": user_message.strip().lower(),
            "portfolio_id": portfolio_id,
            "model": self.model_name
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[str]:
        """Check if response is cached and still valid."""
        if cache_key in self._response_cache:
            cached_response, timestamp = self._response_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self._cache_ttl_seconds:
                self.logger.info(f"Cache hit for query (age: {age:.1f}s)")
                return cached_response
            else:
                # Cache expired
                del self._response_cache[cache_key]
        
        return None
    
    def _update_cache(self, cache_key: str, response: str):
        """Update cache with new response."""
        self._response_cache[cache_key] = (response, datetime.now())
        
        # Limit cache size (keep last 100 queries)
        if len(self._response_cache) > 100:
            oldest_key = min(
                self._response_cache.keys(),
                key=lambda k: self._response_cache[k][1]
            )
            del self._response_cache[oldest_key]
    
    def chat(self, user_message: str, portfolio_id: Optional[int] = None, 
             max_turns: int = 10, reset_context: bool = True,
             use_cache: bool = True) -> str:
        """Chat with caching support."""
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(user_message, portfolio_id)
            cached = self._check_cache(cache_key)
            if cached:
                return cached
        
        # ... existing chat implementation ...
        
        response = # ... get response from LLM ...
        
        # Update cache
        if use_cache:
            self._update_cache(cache_key, response)
        
        return response
```

**Rationale:** For identical queries within a time window, return the exact same response. This guarantees perfect consistency for repeated queries.

---

### 7. **Add Analysis Metadata Tracking**

**Create metadata tracking for reproducibility:**

```python
def chat(self, user_message: str, portfolio_id: Optional[int] = None,
         max_turns: int = 10, reset_context: bool = True) -> str:
    """Enhanced chat with metadata tracking."""
    
    # Track analysis metadata
    analysis_metadata = {
        "request_id": hashlib.md5(
            f"{datetime.now().isoformat()}{user_message}".encode()
        ).hexdigest()[:12],
        "timestamp": datetime.now().isoformat(),
        "model": self.model_name,
        "temperature": 0.0,
        "portfolio_id": portfolio_id,
        "query": user_message[:100],  # First 100 chars
        "tools_used": [],
        "conversation_turns": 0
    }
    
    try:
        # ... existing implementation ...
        
        # Track each tool use
        for content_block in output_message["content"]:
            if "toolUse" in content_block:
                tool_name = content_block["toolUse"]["name"]
                analysis_metadata["tools_used"].append(tool_name)
        
        analysis_metadata["conversation_turns"] = turn_count
        
        # Log metadata for debugging
        self.logger.info(f"Analysis metadata: {json.dumps(analysis_metadata)}")
        
        return response
        
    except Exception as e:
        analysis_metadata["error"] = str(e)
        self.logger.error(f"Analysis failed: {json.dumps(analysis_metadata)}")
        raise
```

**Rationale:** Tracking exactly what happened in each analysis helps debug inconsistencies and reproduce specific results.

---

## Implementation Priority

### High Priority (Implement Immediately)
1. ✅ Set temperature to 0.0
2. ✅ Add reset_context parameter
3. ✅ Enforce structured output format in system prompt

### Medium Priority (Implement This Week)
4. ✅ Standardize tool result formatting
5. ✅ Add response caching
6. ✅ Add validation layer

### Low Priority (Nice to Have)
7. ✅ Add comprehensive metadata tracking

---

## Testing Consistency

Create a test suite to verify consistency:

```python
# tests/test_llm_consistency.py
import pytest
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer

def test_identical_queries_produce_identical_results():
    """Test that the same query produces identical results."""
    analyzer = LLMPortfolioAnalyzer(pool=test_pool)
    
    query = "What is the RSI for AAPL?"
    portfolio_id = 1
    
    # Ask same question 5 times
    responses = []
    for i in range(5):
        analyzer.reset_conversation()  # Fresh context each time
        response = analyzer.chat(query, portfolio_id=portfolio_id)
        responses.append(response)
    
    # All responses should be identical
    assert len(set(responses)) == 1, "Responses varied across identical queries"

def test_response_format_consistency():
    """Test that responses follow consistent format."""
    analyzer = LLMPortfolioAnalyzer(pool=test_pool)
    
    queries = [
        "Analyze my portfolio",
        "What should I buy?",
        "Show me technical indicators for MSFT"
    ]
    
    for query in queries:
        analyzer.reset_conversation()
        response = analyzer.chat(query, portfolio_id=1)
        
        # Check for required sections
        assert "**SUMMARY**" in response
        assert "**DATA ANALYSIS**" in response
        assert "**RECOMMENDATIONS**" in response
        assert "**RISK FACTORS**" in response

def test_numeric_precision_consistency():
    """Test that numeric values are consistently formatted."""
    analyzer = LLMPortfolioAnalyzer(pool=test_pool)
    
    query = "What is my cash balance?"
    
    responses = []
    for i in range(3):
        analyzer.reset_conversation()
        response = analyzer.chat(query, portfolio_id=1)
        responses.append(response)
    
    # Extract dollar amounts from all responses
    import re
    for response in responses:
        amounts = re.findall(r'\$[\d,]+\.\d{2}', response)
        assert len(amounts) > 0, "No properly formatted dollar amounts found"
        # All should have exactly 2 decimal places
        for amount in amounts:
            assert amount.count('.') == 1
            decimals = amount.split('.')[-1]
            assert len(decimals) == 2
```

---

## Monitoring Consistency in Production

Add logging to track consistency metrics:

```python
class ConsistencyMonitor:
    """Monitor LLM consistency over time."""
    
    def __init__(self):
        self.query_log = []
    
    def log_query(self, query: str, response: str, metadata: Dict):
        """Log query and response for analysis."""
        self.query_log.append({
            "query": query,
            "response_hash": hashlib.sha256(response.encode()).hexdigest(),
            "response_length": len(response),
            "metadata": metadata,
            "timestamp": datetime.now()
        })
    
    def check_similar_queries(self, query: str, threshold: float = 0.8):
        """Check if similar queries produced similar responses."""
        from difflib import SequenceMatcher
        
        similar_queries = []
        for log_entry in self.query_log:
            similarity = SequenceMatcher(
                None, 
                query.lower(), 
                log_entry["query"].lower()
            ).ratio()
            
            if similarity > threshold:
                similar_queries.append(log_entry)
        
        return similar_queries
```

---

## Expected Improvements

After implementing these recommendations:

1. **Deterministic Responses**: Identical queries → identical responses (100% consistency)
2. **Structured Format**: All responses follow the same 5-section format
3. **Numeric Precision**: All numbers consistently formatted
4. **Fast Repeated Queries**: Cached responses return instantly
5. **Data Quality**: Validation catches errors before analysis
6. **Debuggability**: Full metadata trail for every analysis

---

## Summary Checklist

- [x] Change temperature to 0.0 ✅ **COMPLETED 2026-01-06**
- [x] ~~Add topP=1.0 to inference config~~ ❌ **Not compatible with Claude models - removed 2026-01-08**
- [x] Add reset_context parameter (default True) ✅ **COMPLETED 2026-01-06**
- [ ] Update system prompt with structured output requirements
- [ ] Implement _normalize_tool_result() method
- [ ] Add _validate_analysis_data() method
- [ ] Implement response caching
- [ ] Add metadata tracking
- [x] Create consistency test suite ✅ **COMPLETED 2026-01-06**
- [ ] Set up consistency monitoring
- [x] Document changes in code comments ✅ **COMPLETED 2026-01-06**

---

## Additional Resources

- [AWS Bedrock Inference Parameters](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html)
- [Prompt Engineering for Consistency](https://docs.anthropic.com/claude/docs/constructing-a-prompt#formatting-your-prompt)
- [Structured Output Techniques](https://docs.anthropic.com/claude/docs/multimodal-vision#structured-outputs)

---

*Generated: 2026-01-05*
*Target Implementation: Week of 2026-01-06*
