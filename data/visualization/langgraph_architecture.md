# TradeMaster LangGraph Architecture

This diagram illustrates the new architecture of the TradeMaster Discord bot using LangGraph for workflow management.

```mermaid
flowchart TD
    %% Main Components
    Discord["Discord Interface"] --> Events["bot/events.py\nEvent Handlers"] 
    Events --> Router["core/router_new.py\nLangGraph Router"]
    Commands["bot/commands.py\nSystem Commands"] --> Router
    
    %% LangGraph Workflow
    subgraph "LangGraph Workflow"
        ShouldRespond["should_respond\nDecision Node"] --> AnalyzeIntent["analyze_intent\nTool Selection"]
        AnalyzeIntent --> ExecuteTool["execute_tool\nTool Execution"]
        ExecuteTool --> GenerateResponse["generate_response\nResponse Generation"]
    end
    
    Router --> ShouldRespond
    
    %% Specialized Tools
    subgraph "Specialized Tools"
        WalletTracker["tools/wallet/tracker.py\nWallet Tracker"]
        MarketAnalyzer["tools/market/analyzer.py\nMarket Analyzer"]
        TradeCritic["tools/trading/critic.py\nTrade Critic"]
        ConversationalAI["tools/conversation/assistant.py\nGeneral Assistant"]
    end
    
    ExecuteTool --> WalletTracker
    ExecuteTool --> MarketAnalyzer
    ExecuteTool --> TradeCritic
    ExecuteTool --> ConversationalAI
    
    %% Response Flow
    WalletTracker --> GenerateResponse
    MarketAnalyzer --> GenerateResponse
    TradeCritic --> GenerateResponse
    ConversationalAI --> GenerateResponse
    
    GenerateResponse --> Events
    
    %% External Components
    LLM["Ollama LLM\n(deepseek-r1:14b)"] --- Router
    
    %% Styling
    classDef discord fill:#7289DA,color:white
    classDef bot fill:#4CAF50,color:white
    classDef router fill:#FF9800,color:white
    classDef workflow fill:#9C27B0,color:white
    classDef tools fill:#2196F3,color:white
    classDef external fill:#607D8B,color:white
    
    class Discord discord
    class Events,Commands bot
    class Router router
    class ShouldRespond,AnalyzeIntent,ExecuteTool,GenerateResponse workflow
    class WalletTracker,MarketAnalyzer,TradeCritic,ConversationalAI tools
    class LLM external
```

## Key Improvements with LangGraph

1. **Structured Workflow**: Clear, defined stages for message processing
2. **Conditional Logic**: Decision nodes determine when and how to respond
3. **Tool Selection**: Dynamic selection of specialized tools based on message intent
4. **State Management**: Maintains conversation context across interactions
5. **Modular Design**: Easy to add new tools and capabilities

## Message Flow

1. User sends message to Discord
2. Event handler receives message and passes to Router
3. Router initializes LangGraph workflow
4. Workflow determines if response is needed
5. If yes, analyzes intent and selects appropriate tool
6. Executes tool to get specialized response
7. Generates natural language response
8. Returns response to Discord