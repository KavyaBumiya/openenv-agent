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
            st.error(f"❌ Error generating action: {str(e)}")
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
        ["Interactive Demo", "Statistics", "Batch Testing", "Settings"],
        icons=["play-circle", "bar-chart", "speedometer", "gear"],
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
