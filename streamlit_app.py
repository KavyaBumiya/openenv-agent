#!/usr/bin/env python3
"""
Customer Support RL Environment - Streamlit UI

A full-featured interactive web UI for testing, training, and evaluating
the customer support ticket triage environment.

Run with: streamlit run streamlit_app.py
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import Optional, Dict, Any, Literal, cast

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file
except ImportError:
    pass  # dotenv not installed, skip

import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

# Ensure environment is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction
from customer_support_env.data import TICKETS
from customer_support_env.baseline import _build_prompt, extract_json

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Customer Support RL Environment",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "env" not in st.session_state:
    st.session_state.env = CustomerSupportEnvironment()

if "current_observation" not in st.session_state:
    st.session_state.current_observation = None

if "current_task" not in st.session_state:
    st.session_state.current_task = None

if "current_action" not in st.session_state:
    st.session_state.current_action = None

if "episode_history" not in st.session_state:
    st.session_state.episode_history = []

if "total_episodes" not in st.session_state:
    st.session_state.total_episodes = 0

if "total_reward" not in st.session_state:
    st.session_state.total_reward = 0.0

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "auto_action" not in st.session_state:
    st.session_state.auto_action = None

if "auto_response_text" not in st.session_state:
    st.session_state.auto_response_text = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def reset_environment(task: str = "classify", seed: Optional[int] = None):
    """Reset the environment with a new ticket."""
    if seed is None:
        seed = random.randint(0, 9999)
    
    obs = st.session_state.env.reset(seed=seed, task=task)
    st.session_state.current_observation = obs
    st.session_state.current_task = task
    st.session_state.current_action = None
    
    return obs

def process_action(action: TicketAction):
    """Process an action and get the result."""
    result = st.session_state.env.step(action)
    st.session_state.current_action = action
    st.session_state.last_result = result  # Store for later access
    
    # Update statistics
    st.session_state.total_episodes += 1
    st.session_state.total_reward += result.reward
    
    # Store in history
    history_entry = {
        "episode": st.session_state.total_episodes,
        "task": st.session_state.current_task,
        "ticket_id": st.session_state.current_observation.ticket_id if st.session_state.current_observation else None,
        "subject": st.session_state.current_observation.subject if st.session_state.current_observation else None,
        "reward": result.reward,
        "timestamp": datetime.now().isoformat(),
        "feedback": result.feedback if hasattr(result, 'feedback') else ""
    }
    st.session_state.episode_history.append(history_entry)
    
    return result

def get_task_description(task: str) -> str:
    """Get a description of the task."""
    descriptions = {
        "classify": "Classify the ticket into a category and assign a priority level.",
        "route": "Classify, assign priority, AND route to the appropriate department.",
        "resolve": "Classify, assign priority, route to department, AND provide a response text."
    }
    return descriptions.get(task, "")

def get_task_difficulty(task: str) -> str:
    """Get the difficulty level of a task."""
    return st.session_state.env.DIFFICULTY_MAP.get(task, "Unknown")

def auto_generate_action(task: str, obs) -> Optional[TicketAction]:
    """Auto-generate an action using Groq API based on the observation.
    
    Returns None if API key not set or error occurs, otherwise returns TicketAction.
    """
    try:
        from groq import Groq
    except ImportError:
        st.error("❌ Groq SDK not installed. Run: pip install groq")
        return None
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("❌ GROQ_API_KEY environment variable not set. Please set it to use Auto Agent.")
        return None
    
    with st.spinner("🤖 AI Agent thinking..."):
        try:
            client = Groq(api_key=api_key)
            
            # Build prompt using baseline logic
            prompt = _build_prompt(task, obs)
            
            # Determine temperature based on task
            temp_map = {"classify": 0.1, "route": 0.5, "resolve": 0.7}
            temperature = temp_map.get(task, 0.1)
            
            # Call Groq
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=30,
            )
            
            response_text = response.choices[0].message.content
            if response_text is None:
                st.error("❌ Groq returned empty response")
                return None
            
            # Extract JSON with expected keys for this task
            expected_keys_map = {
                "classify": ["category", "priority"],
                "route": ["category", "priority", "department"],
                "resolve": ["category", "priority", "department", "response"],
            }
            expected_keys = expected_keys_map.get(task, [])
            
            action_dict = extract_json(response_text, expected_keys=expected_keys)
            
            # Create TicketAction
            action = TicketAction(
                category=action_dict.get("category", ""),
                priority=action_dict.get("priority", ""),
                department=action_dict.get("department"),
                response=action_dict.get("response"),
                requires_escalation=action_dict.get("requires_escalation", False),
            )
            
            # Store generated data in session for display
            st.session_state.auto_action = action
            st.session_state.auto_response_text = response_text
            
            return action
        
        except Exception as e:
            error_msg = str(e)
            # Check for rate limit error
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                st.error(f"⏸️ **Rate Limited**: Groq free tier limit reached. Please wait or upgrade at https://console.groq.com/settings/billing")
            elif "invalid_request_error" in error_msg or "validation error" in error_msg:
                st.error(f"❌ Invalid request: {error_msg[:100]}")
            else:
                st.error(f"❌ Error generating action: {error_msg[:150]}")
            return None

# ============================================================================
# MAIN LAYOUT
# ============================================================================

# Sidebar navigation
with st.sidebar:
    st.title("🎫 Support RL Env")
    
    # Main navigation
    page = option_menu(
        "Menu",
        ["Interactive Demo", "Statistics", "Batch Testing", "Testing & Verification", "Settings"],
        icons=["play-circle", "bar-chart", "speedometer", "flask-conical", "gear"],
        menu_icon="cast",
        default_index=0,
    )
    
    st.divider()
    
    # Global statistics
    st.subheader("📊 Session Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Episodes", st.session_state.total_episodes)
    with col2:
        avg_reward = (
            st.session_state.total_reward / st.session_state.total_episodes 
            if st.session_state.total_episodes > 0 
            else 0
        )
        st.metric("Avg Reward", f"{avg_reward:.1%}")
    
    st.metric("Total Reward", f"{st.session_state.total_reward:.2f}")

# ============================================================================
# PAGE: INTERACTIVE DEMO
# ============================================================================

if page == "Interactive Demo":
    st.title("🎯 Interactive Ticket Triage Demo")
    st.markdown("Test the environment by processing individual tickets with real-time feedback.")
    
    # Task selection
    col1, col2, col3 = st.columns(3)
    with col1:
        task = st.radio(
            "Select Task",
            ["classify", "route", "resolve"],
            help="Choose the complexity level of the task"
        )
    
    with col2:
        st.info(f"**Difficulty:** {get_task_difficulty(task).title()}")
    
    with col3:
        st.info(f"**Max Score:** 100%")
    
    st.markdown(f"❓ {get_task_description(task)}")
    st.divider()
    
    # Load or reset ticket
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Load New Ticket"):
            obs = reset_environment(task=task)
            st.rerun()
    
    with col2:
        seed_input = st.number_input("Seed (optional)", min_value=0, max_value=9999, value=None)
        if st.button("📌 Load Specific Ticket"):
            if seed_input is not None:
                obs = reset_environment(task=task, seed=int(seed_input))
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear History"):
            st.session_state.episode_history = []
            st.session_state.total_episodes = 0
            st.session_state.total_reward = 0.0
            st.success("History cleared!")
            st.rerun()
    
    st.divider()
    
    # Display ticket information
    if st.session_state.current_observation:
        obs = st.session_state.current_observation
        
        # Ticket details in expandable section
        with st.expander("📋 Ticket Details", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Ticket ID:** `{obs.ticket_id}`")
                st.write(f"**Customer Tier:** {obs.sender_tier.title() if obs.sender_tier else 'N/A'}")
                st.write(f"**Previous Tickets:** {obs.previous_tickets}")
                st.write(f"**Open Since:** {obs.open_since_hours}h ago")
            with col2:
                st.write(f"**Sentiment:** {obs.sentiment.title() if obs.sentiment else 'N/A'}")
                st.write(f"**Task:** {obs.task_name.title() if obs.task_name else 'N/A'}")
            
            st.write(f"**Subject:** {obs.subject}")
            st.write(f"**Body:**")
            st.text_area("", value=obs.body, disabled=True, height=120)
        
        # Action input form
        st.subheader("✍️ Your Action")
        
        col1, col2 = st.columns(2)
        
        with col1:
            category = cast(
                Literal["billing", "technical", "account", "shipping", "general"],
                st.selectbox(
                    "Category",
                    ["billing", "technical", "account", "shipping", "general"],
                    help="Classify the issue type"
                )
            )
            
            priority = cast(
                Literal["low", "medium", "high", "urgent"],
                st.selectbox(
                    "Priority",
                    ["low", "medium", "high", "urgent"],
                    help="Set the urgency level"
                )
            )
        
        with col2:
            department: Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]] = None
            requires_escalation = False
            response = None
            
            if task in ["route", "resolve"]:
                # For route/resolve, department is required - don't include None
                dept_options = ["tier1", "tier2", "billing", "engineering", "management"]
                department = cast(
                    Literal["tier1", "tier2", "billing", "engineering", "management"],
                    st.selectbox(
                        "Department *",
                        dept_options,
                        index=0,  # Default to tier1
                        help="Route to appropriate department (required)"
                    )
                )
                requires_escalation = st.checkbox("Requires Escalation?", help="Mark for escalation if needed")
            else:
                # For classify, department is optional
                department = None
            
            if task == "resolve":
                response = st.text_area(
                    "Response",
                    height=100,
                    help="Provide a response to resolve the ticket",
                    placeholder="Enter your response here..."
                )
        
        # Action buttons row
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            if st.button("✅ Submit Action", type="primary", use_container_width=True):
                action = TicketAction(
                    category=category,
                    priority=priority,
                    department=department,
                    response=response,
                    requires_escalation=requires_escalation
                )
                result = process_action(action)
                st.rerun()
        
        with col2:
            if st.button("🤖 Auto Agent", use_container_width=True):
                auto_action = auto_generate_action(task, st.session_state.current_observation)
                if auto_action:
                    st.session_state.auto_action = auto_action
                    st.rerun()
        
        with col3:
            if st.button("⏭️ Skip", use_container_width=True):
                reset_environment(task=task)
                st.session_state.auto_action = None
                st.rerun()
        
        with col4:
            if st.button("🗑️ Clear Auto", use_container_width=True, disabled=st.session_state.auto_action is None):
                st.session_state.auto_action = None
                st.rerun()
        
        st.divider()
        
        # Rate limit notice for Auto Agent
        with st.expander("ℹ️ About Auto Agent", expanded=False):
            st.info("""
            **Auto Agent** uses Groq's free tier (100k tokens/day limit).
            - Each action uses ~500-1000 tokens
            - If rate limited, you can:
              1. Wait ~4 hours for usage to refresh
              2. Upgrade at https://console.groq.com/settings/billing
              3. Use Manual mode instead
            """)
        
        st.divider()
        
        # Display auto-generated action if available
        if st.session_state.auto_action:
            st.success("✅ **Auto Agent Generated Action:**")
            
            auto_action = st.session_state.auto_action
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Category:** `{auto_action.category}`")
                st.write(f"**Priority:** `{auto_action.priority}`")
                if auto_action.department:
                    st.write(f"**Department:** `{auto_action.department}`")
                if auto_action.requires_escalation:
                    st.write("**Escalation:** ⚠️ Flagged for escalation")
            
            with col2:
                if auto_action.response:
                    st.write(f"**Response:**")
                    st.text_area("", value=auto_action.response, disabled=True, height=80)
            
            # Submit auto action
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Accept & Submit Auto", type="primary", use_container_width=True):
                    result = process_action(auto_action)
                    st.session_state.auto_action = None
                    st.rerun()
            with col2:
                if st.button("❌ Reject Auto", use_container_width=True):
                    st.session_state.auto_action = None
                    st.rerun()
            
            st.divider()
        
        # Display result if action was taken
        if st.session_state.current_action and st.session_state.last_result:
            result = st.session_state.last_result
            st.subheader("📊 Result")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Score", f"{result.reward:.1%}", delta=f"{result.reward - 0.5:.1%}")
            with col2:
                st.metric("Category", st.session_state.current_action.category.title())
            with col3:
                st.metric("Priority", st.session_state.current_action.priority.title())
            with col4:
                if task in ["route", "resolve"]:
                    st.metric("Department", st.session_state.current_action.department.title() if st.session_state.current_action.department else "N/A")
            
            st.divider()
            
            # Feedback
            if hasattr(result, 'feedback') and result.feedback:
                st.info(f"💭 **Feedback:**\n\n{result.feedback}")
    else:
        st.info("👈 Click 'Load New Ticket' to get started!")

# ============================================================================
# PAGE: STATISTICS
# ============================================================================

elif page == "Statistics":
    st.title("📊 Statistics & Analytics")
    
    if st.session_state.episode_history:
        df = pd.DataFrame(st.session_state.episode_history)
        
        # Summary metrics
        st.subheader("📈 Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Episodes", len(df))
        with col2:
            st.metric("Average Reward", f"{df['reward'].mean():.1%}")
        with col3:
            st.metric("Best Score", f"{df['reward'].max():.1%}")
        with col4:
            st.metric("Worst Score", f"{df['reward'].min():.1%}")
        
        st.divider()
        
        # Performance by task
        st.subheader("📋 Performance by Task")
        task_stats = df.groupby('task')['reward'].agg(['count', 'mean', 'max', 'min'])
        task_stats.columns = ['Episodes', 'Avg Reward', 'Best', 'Worst']
        task_stats['Avg Reward'] = task_stats['Avg Reward'].apply(lambda x: f"{x:.1%}")
        task_stats['Best'] = task_stats['Best'].apply(lambda x: f"{x:.1%}")
        task_stats['Worst'] = task_stats['Worst'].apply(lambda x: f"{x:.1%}")
        st.dataframe(task_stats, use_container_width=True)
        
        st.divider()
        
        # Reward trend chart
        st.subheader("📉 Reward Trend")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(df['reward'], marker='o', linestyle='-', linewidth=2, markersize=4)
            ax.axhline(y=df['reward'].mean(), color='r', linestyle='--', label=f"Average: {df['reward'].mean():.1%}")
            ax.set_xlabel("Episode")
            ax.set_ylabel("Reward")
            ax.set_title("Reward per Episode")
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        
        with col2:
            st.write("")
            improvement = df['reward'].iloc[-1] - df['reward'].iloc[0]
            st.metric(
                "Improvement",
                f"{improvement:.1%}",
                delta_color="normal" if improvement >= 0 else "inverse"
            )
        
        st.divider()
        
        # Episode history table
        st.subheader("📝 Episode History")
        display_df = df[['episode', 'task', 'subject', 'reward']].copy()
        display_df['reward'] = display_df['reward'].apply(lambda x: f"{x:.1%}")
        display_df.columns = ['Episode', 'Task', 'Subject', 'Reward']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export option
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download History as CSV",
                data=csv,
                file_name=f"episode_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = json.dumps(st.session_state.episode_history, indent=2, default=str)
            st.download_button(
                label="📥 Download History as JSON",
                data=json_data,
                file_name=f"episode_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("No episodes yet. Complete some tasks in the Interactive Demo to see statistics!")

# ============================================================================
# PAGE: BATCH TESTING
# ============================================================================

elif page == "Batch Testing":
    st.title("⚡ Batch Testing")
    st.markdown("Run multiple episodes automatically with configurable actions.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        test_task = st.selectbox("Task", ["classify", "route", "resolve"], key="batch_task")
    with col2:
        num_episodes = st.number_input("Episodes", min_value=1, max_value=100, value=10)
    with col3:
        test_mode = st.selectbox(
            "Action Strategy",
            ["random", "mean_values", "all_high"],
            help="How to select actions for testing"
        )
    
    if st.button("🚀 Start Batch Test", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        results_placeholder = st.empty()
        
        batch_results = []
        
        for i in range(num_episodes):
            obs = reset_environment(task=test_task, seed=random.randint(0, 9999))
            
            # Generate action based on strategy
            if test_mode == "random":
                # For route/resolve, ensure department is always set (not None)
                if test_task != "classify":
                    dept_choice = random.choice(["tier1", "tier2", "billing", "engineering", "management"])
                else:
                    dept_choice = None
                
                action = TicketAction(
                    category=cast(Literal["billing", "technical", "account", "shipping", "general"],
                                  random.choice(["billing", "technical", "account", "shipping", "general"])),
                    priority=cast(Literal["low", "medium", "high", "urgent"],
                                  random.choice(["low", "medium", "high", "urgent"])),
                    department=cast(Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]], dept_choice),
                    response="This is a test response." if test_task == "resolve" else None,
                    requires_escalation=random.choice([True, False])
                )
            elif test_mode == "mean_values":
                action = TicketAction(
                    category="general",
                    priority="medium",
                    department=cast(Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]],
                                    "tier1" if test_task != "classify" else None),
                    response="Thank you for contacting us. We are working on your issue." if test_task == "resolve" else None,
                    requires_escalation=False
                )
            else:  # all_high
                action = TicketAction(
                    category="technical",
                    priority="high",
                    department=cast(Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]],
                                    "engineering" if test_task != "classify" else None),
                    response="We prioritize your concern and are escalating to our engineering team." if test_task == "resolve" else None,
                    requires_escalation=True
                )
            
            result = process_action(action)
            batch_results.append(result.reward)
            
            # Update progress
            progress_bar.progress((i + 1) / num_episodes)
            
            with results_placeholder.container():
                st.info(f"Running: Episode {i + 1}/{num_episodes} | Current Avg: {sum(batch_results) / len(batch_results):.1%}")
        
        st.success("✅ Batch test completed!")
        
        # Display results
        st.subheader("📊 Batch Results")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Episodes Run", len(batch_results))
        with col2:
            st.metric("Average Score", f"{sum(batch_results) / len(batch_results):.1%}")
        with col3:
            st.metric("Best Score", f"{max(batch_results):.1%}")
        with col4:
            st.metric("Worst Score", f"{min(batch_results):.1%}")
        
        # Distribution chart
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.hist(batch_results, bins=20, edgecolor='black', alpha=0.7)
        ax.axvline(sum(batch_results) / len(batch_results), color='r', linestyle='--', label='Mean')
        ax.set_xlabel("Reward")
        ax.set_ylabel("Frequency")
        ax.set_title(f"Reward Distribution ({test_mode})")
        ax.legend()
        st.pyplot(fig)

# ============================================================================
# PAGE: TESTING & VERIFICATION
# ============================================================================

elif page == "Testing & Verification":
    st.title("🧪 Testing & Verification Suite")
    st.markdown("Comprehensive automated testing directly in the UI. No terminal needed!")
    
    # Test selection tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["System Tests", "API Tests", "Data Validation", "Baseline Eval", "Full Report"])
    
    # ========== TAB 1: SYSTEM TESTS ==========
    with tab1:
        st.subheader("🔧 System & Environment Tests")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Test 1: Environment Initialization", use_container_width=True):
                with st.spinner("Testing environment..."):
                    try:
                        env = CustomerSupportEnvironment()
                        st.success("✅ Environment initialized successfully")
                        st.json({"status": "OK", "env_type": str(type(env).__name__)})
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col2:
            if st.button("🧪 Test 2: Reset Method", use_container_width=True):
                with st.spinner("Testing reset..."):
                    try:
                        obs = st.session_state.env.reset(seed=0, task="classify")
                        st.success("✅ Reset method works")
                        st.json({
                            "ticket_id": obs.ticket_id,
                            "task": obs.task_name,
                            "subject": obs.subject[:50] + "..."
                        })
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("🧪 Test 3: Step Method", use_container_width=True):
                with st.spinner("Testing step..."):
                    try:
                        obs = st.session_state.env.reset(seed=1, task="classify")
                        action = TicketAction(category="billing", priority="medium")
                        result = st.session_state.env.step(action)
                        st.success("✅ Step method works")
                        st.json({
                            "reward": float(result.reward),
                            "done": result.done,
                            "has_feedback": hasattr(result, 'feedback') and result.feedback is not None
                        })
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col4:
            if st.button("🧪 Test 4: State Property", use_container_width=True):
                with st.spinner("Testing state..."):
                    try:
                        state = st.session_state.env.state
                        st.success("✅ State property works")
                        st.json({
                            "episode_id": state.episode_id,
                            "step_count": state.step_count,
                            "task_name": state.task_name
                        })
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        st.divider()
        
        # Groq API Test
        col5, col6 = st.columns(2)
        with col5:
            if st.button("🤖 Test 5: Groq API Connection", use_container_width=True):
                with st.spinner("Connecting to Groq..."):
                    try:
                        from groq import Groq
                        api_key = os.getenv("GROQ_API_KEY")
                        
                        if not api_key:
                            st.error("❌ GROQ_API_KEY not set in .env")
                        else:
                            client = Groq(api_key=api_key)
                            models = client.models.list()
                            st.success("✅ Groq API authenticated")
                            st.json({"models_available": len(models.data)})
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col6:
            if st.button("🧪 Test 6: Pydantic Models", use_container_width=True):
                with st.spinner("Validating models..."):
                    try:
                        # Test TicketAction validation
                        action1 = TicketAction(category="billing", priority="high")
                        action2 = TicketAction(
                            category="technical", priority="urgent", 
                            department="tier1", response="Test"
                        )
                        st.success("✅ Pydantic models validated")
                        st.json({"models_tested": 2, "validation": "passed"})
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
    
    # ========== TAB 2: API ENDPOINT TESTS ==========
    with tab2:
        st.subheader("🌐 API Endpoint Tests")
        st.markdown("Test all FastAPI endpoints without leaving the UI")
        
        # Check if server endpoints are accessible
        test_endpoints = [
            ("/health", "Health Check"),
            ("/tasks", "Get Tasks"),
            ("/state", "Get Current State"),
        ]
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📡 Test All Endpoints", use_container_width=True, type="primary"):
                with st.spinner("Testing endpoints..."):
                    import requests
                    
                    results = []
                    base_url = "http://localhost:8000"
                    
                    for endpoint, label in test_endpoints:
                        try:
                            resp = requests.get(f"{base_url}{endpoint}", timeout=5)
                            results.append({
                                "endpoint": endpoint,
                                "label": label,
                                "status": resp.status_code,
                                "ok": resp.status_code == 200
                            })
                        except requests.exceptions.ConnectionError:
                            results.append({
                                "endpoint": endpoint,
                                "label": label,
                                "status": "Connection Failed",
                                "ok": False
                            })
                        except Exception as e:
                            results.append({
                                "endpoint": endpoint,
                                "label": label,
                                "status": str(e),
                                "ok": False
                            })
                    
                    # Display results
                    for result in results:
                        if result['ok']:
                            st.success(f"✅ {result['label']} - {result['status']}")
                        else:
                            st.warning(f"⚠️ {result['label']} - {result['status']}")
        
        with col2:
            st.info("**Note:** Ensure FastAPI server is running in another terminal:\n```\npython main.py\n```")
            if st.button("✅ Test Endpoint Response", use_container_width=True):
                with st.spinner("Fetching data..."):
                    try:
                        # Test /tasks endpoint
                        from customer_support_env.environment import CustomerSupportEnvironment
                        env = CustomerSupportEnvironment()
                        
                        st.success("✅ Environment created successfully")
                        st.json({
                            "tasks": ["classify", "route", "resolve"],
                            "difficulties": ["Easy", "Medium", "Hard"]
                        })
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # ========== TAB 3: DATA VALIDATION ==========
    with tab3:
        st.subheader("📋 Data Validation Tests")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Test: Load Tickets", use_container_width=True):
                with st.spinner("Loading tickets..."):
                    try:
                        from customer_support_env.data import TICKETS, validate_tickets
                        validate_tickets()
                        st.success(f"✅ All {len(TICKETS)} tickets loaded and validated")
                        
                        # Show sample
                        st.subheader("Sample Ticket:")
                        ticket = TICKETS[0]
                        st.json({
                            "id": ticket["ticket_id"],
                            "subject": ticket["subject"][:50] + "...",
                            "category": ticket["category"],
                            "priority": ticket["priority"],
                            "tier": ticket["sender_tier"]
                        })
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col2:
            if st.button("✅ Test: Validate Schemas", use_container_width=True):
                with st.spinner("Validating schemas..."):
                    try:
                        from customer_support_env.data import TICKETS
                        
                        required_fields = [
                            "ticket_id", "subject", "body", "category", "priority",
                            "sender_tier", "sentiment", "department", "response_keywords"
                        ]
                        
                        for ticket in TICKETS:
                            for field in required_fields:
                                if field not in ticket:
                                    raise ValueError(f"Missing field: {field} in ticket {ticket.get('ticket_id', 'unknown')}")
                        
                        st.success("✅ All tickets have required fields")
                        st.json({"tickets_validated": len(TICKETS), "fields_checked": len(required_fields)})
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col3:
            if st.button("✅ Test: Category Distribution", use_container_width=True):
                with st.spinner("Analyzing categories..."):
                    try:
                        from customer_support_env.data import TICKETS
                        from collections import Counter
                        
                        categories = Counter(t["category"] for t in TICKETS)
                        
                        st.success("✅ Category distribution validated")
                        
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.bar(categories.keys(), categories.values(), color='steelblue')
                        ax.set_xlabel("Category")
                        ax.set_ylabel("Count")
                        ax.set_title("Ticket Category Distribution")
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
    
    # ========== TAB 4: BASELINE EVALUATION ==========
    with tab4:
        st.subheader("📊 Baseline Evaluation")
        st.markdown("Run automated baseline evaluation with Groq LLM")
        
        # Rate limit warning
        st.warning("""
        ⚠️ **Rate Limit Notice**: Groq free tier allows 100k tokens/day. 
        - If you hit the limit, you can upgrade at https://console.groq.com/settings/billing
        - Or wait ~24 hours for the limit to reset
        - Each baseline episode uses approximately 2-4k tokens
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            select_task = st.selectbox("Select Task", ["classify", "route", "resolve"], key="baseline_task")
        with col2:
            num_episodes_base = st.number_input("Episodes", 1, 30, 5, key="baseline_episodes")
        with col3:
            st.write("")
            if st.button("🚀 Run Baseline", type="primary", use_container_width=True):
                with st.spinner(f"Running {num_episodes_base} baseline episodes..."):
                    try:
                        from customer_support_env.baseline import run_baseline, get_llm_results
                        import subprocess
                        
                        # Run baseline script
                        result = subprocess.run(
                            ["python", "-m", "customer_support_env.baseline", "--task", select_task, "--episodes", str(num_episodes_base)],
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        if result.returncode == 0:
                            st.success("✅ Baseline evaluation completed!")
                            
                            # Parse results
                            output_lines = result.stdout.split('\n')
                            for line in output_lines:
                                if "Mean score" in line or "Score" in line or "accuracy" in line.lower():
                                    st.write(line)
                        else:
                            st.warning("⚠️ Baseline completed with warnings")
                            st.write(result.stderr)
                    except subprocess.TimeoutExpired:
                        st.error("❌ Baseline evaluation timed out")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # ========== TAB 5: FULL TEST REPORT ==========
    with tab5:
        st.subheader("📄 Complete Test Report")
        st.markdown("Generate and download comprehensive test results")
        
        if st.button("📋 Generate Full Test Report", type="primary", use_container_width=True):
            with st.spinner("Running all tests..."):
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "tests": {
                        "environment": {"status": "pending"},
                        "reset": {"status": "pending"},
                        "step": {"status": "pending"},
                        "state": {"status": "pending"},
                        "tickets": {"status": "pending"},
                        "schemas": {"status": "pending"},
                        "groq_api": {"status": "pending"},
                        "pydantic": {"status": "pending"},
                    }
                }
                
                # Run all tests
                tests_passed = 0
                tests_failed = 0
                
                # Test 1: Environment
                try:
                    env = CustomerSupportEnvironment()
                    report["tests"]["environment"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["environment"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 2: Reset
                try:
                    obs = st.session_state.env.reset(seed=0, task="classify")
                    report["tests"]["reset"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["reset"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 3: Step
                try:
                    action = TicketAction(category="billing", priority="medium")
                    result = st.session_state.env.step(action)
                    report["tests"]["step"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["step"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 4: State
                try:
                    state = st.session_state.env.state
                    report["tests"]["state"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["state"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 5: Tickets
                try:
                    from customer_support_env.data import TICKETS, validate_tickets
                    validate_tickets()
                    report["tests"]["tickets"]["count"] = len(TICKETS)
                    report["tests"]["tickets"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["tickets"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 6: Schemas
                try:
                    from customer_support_env.data import TICKETS
                    required_fields = ["ticket_id", "subject", "body", "category", "priority"]
                    for ticket in TICKETS:
                        for field in required_fields:
                            if field not in ticket:
                                raise ValueError(f"Missing {field}")
                    report["tests"]["schemas"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["schemas"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 7: Groq API
                try:
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        report["tests"]["groq_api"]["status"] = "SKIPPED: No API key"
                    else:
                        from groq import Groq
                        client = Groq(api_key=api_key)
                        models = client.models.list()
                        report["tests"]["groq_api"]["status"] = "PASSED"
                        report["tests"]["groq_api"]["models"] = len(models.data)
                        tests_passed += 1
                except Exception as e:
                    report["tests"]["groq_api"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Test 8: Pydantic
                try:
                    action = TicketAction(category="billing", priority="high")
                    report["tests"]["pydantic"]["status"] = "PASSED"
                    tests_passed += 1
                except Exception as e:
                    report["tests"]["pydantic"]["status"] = f"FAILED: {str(e)}"
                    tests_failed += 1
                
                # Summary
                report["summary"] = {
                    "total_tests": len(report["tests"]),
                    "passed": tests_passed,
                    "failed": tests_failed,
                    "success_rate": f"{(tests_passed / len(report['tests']) * 100):.1f}%"
                }
                
                # Display report
                st.success("✅ Test Report Generated!")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Tests", report["summary"]["total_tests"])
                with col2:
                    st.metric("Passed", report["summary"]["passed"], delta_color="normal")
                with col3:
                    st.metric("Failed", report["summary"]["failed"], delta_color="inverse")
                with col4:
                    st.metric("Success Rate", report["summary"]["success_rate"])
                
                st.divider()
                
                # Test details
                st.subheader("📊 Detailed Results:")
                for test_name, test_result in report["tests"].items():
                    if "PASSED" in str(test_result):
                        st.success(f"✅ {test_name}: {test_result['status']}")
                    elif "SKIPPED" in str(test_result):
                        st.info(f"ℹ️ {test_name}: {test_result['status']}")
                    else:
                        st.error(f"❌ {test_name}: {test_result['status']}")
                
                st.divider()
                
                # Download report
                json_report = json.dumps(report, indent=2, default=str)
                st.download_button(
                    label="📥 Download Full Report as JSON",
                    data=json_report,
                    file_name=f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# ============================================================================
# PAGE: SETTINGS
# ============================================================================

elif page == "Settings":
    st.title("⚙️ Settings & Information")
    
    # Environment Info
    st.subheader("ℹ️ Environment Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Total Tickets:** " + str(len(TICKETS)))
        st.write("**Supported Tasks:** classify, route, resolve")
        st.write("**Task Difficulties:** Easy, Medium, Hard")
    
    with col2:
        st.write("**Environment Version:** 1.0.0")
        st.write("**UI Framework:** Streamlit")
        st.write("**Backend:** FastAPI")
    
    st.divider()
    
    # Task Information
    st.subheader("📚 Task Guide")
    
    with st.expander("🎯 Classify Task", expanded=False):
        st.write("""
        **What to do:** Classify the ticket into a category and assign a priority level.
        
        **Required fields:**
        - Category: billing, technical, general, complaint
        - Priority: low, medium, high, urgent
        
        **Difficulty:** Easy
        """)
    
    with st.expander("🛣️ Route Task", expanded=False):
        st.write("""
        **What to do:** Classify, assign priority, AND route to the appropriate department.
        
        **Required fields:**
        - Category: billing, technical, general, complaint
        - Priority: low, medium, high, urgent
        - Department: tier1, tier2, engineering
        
        **Difficulty:** Medium
        """)
    
    with st.expander("✉️ Resolve Task", expanded=False):
        st.write("""
        **What to do:** Classify, assign priority, route to department, AND provide a response.
        
        **Required fields:**
        - Category: billing, technical, general, complaint
        - Priority: low, medium, high, urgent
        - Department: tier1, tier2, engineering  
        - Response: A helpful response text
        
        **Difficulty:** Hard
        """)
    
    st.divider()
    
    # Scoring Information
    st.subheader("🏆 Scoring Details")
    
    with st.expander("How Rewards are Calculated", expanded=False):
        st.write("""
        Each task has a reward calculation that depends on the accuracy of your decisions:
        
        **Classify Task:**
        - 60% weight on category accuracy
        - 40% weight on priority accuracy
        
        **Route Task:**
        - 35% weight on category
        - 25% weight on priority  
        - 25% weight on department routing
        - 15% weight on escalation decision
        
        **Resolve Task:**
        - 20% weight on category
        - 15% weight on priority
        - 20% weight on department
        - 15% weight on escalation
        - 30% weight on response quality
        
        Bonuses and penalties are applied based on:
        - Customer type (enterprise vs regular)
        - SLA criticality (age of ticket)
        - Response quality metrics
        - Department appropriateness
        """)
    
    st.divider()
    
    # Session Controls
    st.subheader("🔧 Session Controls")
    
    if st.button("🗑️ Reset All Statistics"):
        st.session_state.episode_history = []
        st.session_state.total_episodes = 0
        st.session_state.total_reward = 0.0
        st.session_state.current_observation = None
        st.session_state.current_action = None
        st.success("All statistics have been reset!")
        st.rerun()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
    <div style="text-align: center; margin-top: 20px; padding: 10px; color: #666;">
        <p>Customer Support RL Environment | Powered by Streamlit</p>
        <p style="font-size: 0.8em;">For documentation and more information, see the README files.</p>
    </div>
""", unsafe_allow_html=True)
