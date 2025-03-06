import os
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor

from tools.wallet.tracker import WalletTracker
from tools.market.analyzer import TrendAnalyzer
from tools.trading.critic import TradeCritic
from tools.conversation.assistant import ConversationalAI
from utils.config import load_config

# Configure logger
logger = logging.getLogger("TradeMaster.Core.Router")

class RouterState(dict):
    """State object for the router workflow"""
    def __init__(self):
        super().__init__()
        self.update({
            "messages": [],  # Conversation history
            "current_tool": None,  # Currently selected tool
            "tool_response": None,  # Response from tool execution
            "final_response": None,  # Final response to user
            "metadata": {},  # Additional context (user info, channel, etc)
            "should_continue": True  # Whether to continue processing
        })

class Router:
    """LangGraph-based router for message analysis and tool selection
    
    This router uses Ollama and LangGraph to create a flexible workflow for:
    - Determining when and how to respond to messages
    - Selecting appropriate tools based on message content
    - Maintaining conversation context
    - Generating natural responses
    """
    
    def __init__(self):
        """Initialize the AI Router with LangGraph components"""
        logger.info("Initializing LangGraph Router...")
        
        # Load configuration
        self.config = load_config()
        self.router_config = self.config.get("router", {})
        
        # Initialize Ollama LLM with a more powerful model
        self.llm = Ollama(model="deepseek-r1:14b")
        
        # Initialize tools
        self.tools = {
            "track_wallet": WalletTracker(),
            "market_trend": TrendAnalyzer(),
            "trade_critique": TradeCritic(),
            "general": ConversationalAI()
        }
        
        # Create tool executor
        self.tool_executor = ToolExecutor(tools=self.tools)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        
        logger.info("LangGraph Router initialization complete")
    
    def _build_workflow(self) -> Graph:
        """Build the LangGraph workflow for message processing"""
        # Create the workflow graph
        workflow = StateGraph(RouterState)
        
        # Add nodes for each processing step
        workflow.add_node("should_respond", self._should_respond)
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("execute_tool", self._execute_tool)
        workflow.add_node("generate_response", self._generate_response)
        
        # Define the workflow edges
        workflow.add_edge("should_respond", "analyze_intent")
        workflow.add_edge("analyze_intent", "execute_tool")
        workflow.add_edge("execute_tool", "generate_response")
        
        # Set conditional edges
        workflow.set_entry_point("should_respond")
        workflow.set_finish_point("generate_response")
        
        return workflow.compile()
    
    async def _should_respond(self, state: RouterState) -> RouterState:
        """Determine if the bot should respond to the message"""
        messages = state["messages"]
        metadata = state["metadata"]
        
        # Create prompt for response decision
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Determine if the message requires a response based on:"
                      "1. Is it a direct mention or DM?"
                      "2. Is it trading-related?"
                      "3. Is it a follow-up to a previous conversation?"
                      "\nRespond with {\"should_respond\": true/false}"),
            ("human", messages[-1].content)
        ])
        
        # Get decision from LLM
        response = await self.llm.ainvoke(prompt)
        decision = JsonOutputParser().parse(response)
        
        state["should_continue"] = decision["should_respond"]
        return state
    
    async def _analyze_intent(self, state: RouterState) -> RouterState:
        """Analyze message intent to select appropriate tool"""
        messages = state["messages"]
        
        # Create prompt for intent analysis
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Analyze the message and determine which tool to use:"
                      "- track_wallet: For wallet/transaction tracking"
                      "- market_trend: For market analysis"
                      "- trade_critique: For trade feedback"
                      "- general: For general questions"
                      "\nRespond with {\"tool\": selected_tool}"),
            ("human", messages[-1].content)
        ])
        
        # Get tool selection from LLM
        response = await self.llm.ainvoke(prompt)
        selection = JsonOutputParser().parse(response)
        
        state["current_tool"] = selection["tool"]
        return state
    
    async def _execute_tool(self, state: RouterState) -> RouterState:
        """Execute the selected tool"""
        tool = state["current_tool"]
        messages = state["messages"]
        metadata = state["metadata"]
        
        # Execute the appropriate tool
        tool_response = await self.tools[tool].process(
            messages[-1].content,
            metadata.get("message_obj")
        )
        
        state["tool_response"] = tool_response
        return state
    
    async def _generate_response(self, state: RouterState) -> RouterState:
        """Generate final response using tool output and context"""
        tool_response = state["tool_response"]
        messages = state["messages"]
        
        # Create prompt for response generation
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate a helpful response using the tool output."
                      "Be concise and natural in your response."),
            ("human", f"Tool output: {tool_response}\nOriginal message: {messages[-1].content}")
        ])
        
        # Generate response
        response = await self.llm.ainvoke(prompt)
        
        state["final_response"] = response
        return state
    
    async def analyze(self, message) -> Tuple[str, bool]:
        """Process a Discord message through the LangGraph workflow
        
        Args:
            message: The Discord message to analyze
            
        Returns:
            tuple: (response_text, is_proactive)
        """
        # Initialize workflow state
        state = RouterState()
        state["messages"] = [HumanMessage(content=message.content)]
        state["metadata"] = {
            "author": message.author.name,
            "author_id": str(message.author.id),
            "channel_id": str(message.channel.id),
            "channel_name": message.channel.name if hasattr(message.channel, 'name') else "DM",
            "message_obj": message
        }
        
        # Run the workflow
        try:
            final_state = await self.workflow.ainvoke(state)
            if not final_state["should_continue"]:
                return None, False
                
            return final_state["final_response"], False
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            return "I'm having trouble processing your message right now. Please try again later.", False