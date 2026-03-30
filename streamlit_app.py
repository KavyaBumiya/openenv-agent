#!/usr/bin/env python3
"""
Customer Support RL Environment - 100% AI-Powered Testing UI

All features (Demo, Testing, Batch, Stats) are AI/LLM-driven.
No manual input required - AI handles everything.

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
    load_dotenv()
except ImportError:
    pass

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
    page_title="Customer Support RL - LLM Testing",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "env" not in st.session_state:
    st.session_state.env = CustomerSupportEnvironment()

if "test_results" not in st.session_state:
    st.session_state.test_results = []

if "total_episodes" not in st.session_state:
    st.session_state.total_episodes = 0

if "total_reward" not in st.session_state:
    st.session_state.total_reward = 0.0

if "current_observation" not in st.session_state:
    st.session_state.current_observation = None

if "current_task" not in st.session_state:
    st.session_state.current_task = None

if "ai_generated_action" not in st.session_state:
    st.session_state.ai_generated_action = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_llm_episode(task: str, llm_provider: str = "groq", seed: Optional[int] = None) -> Dict[str, Any]:
    """Run a single episode with LLM-generated action."""
    if seed is None:
        seed = random.randint(0, 9999)
    
    try:
        # Reset environment
        obs = st.session_state.env.reset(seed=seed, task=task)
        
        # Generate action via LLM
        action_dict = generate_llm_action(task, obs, llm_provider)
        
        if not action_dict:
            return {
                "status": "failed",
                "error": "Failed to generate action from LLM",
                "task": task,
                "seed": seed
            }
        
        # Create and execute action
        action = TicketAction(
            category=action_dict.get("category", ""),
            priority=action_dict.get("priority", ""),
            department=action_dict.get("department"),
            response=action_dict.get("response"),
            requires_escalation=action_dict.get("requires_escalation", False),
        )
        
        result = st.session_state.env.step(action)
        
        return {
            "status": "success",
            "task": task,
            "seed": seed,
            "reward": float(result.reward),
            "action": {
                "category": action.category,
                "priority": action.priority,
                "department": action.department,
                "response": action.response[:50] if action.response else None,
            },
            "llm_provider": llm_provider,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "task": task,
            "seed": seed,
            "llm_provider": llm_provider
        }

def generate_llm_action(task: str, obs, llm_provider: str = "groq") -> Optional[Dict]:
    """Generate action using LLM API."""
    try:
        from groq import Groq
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("❌ GROQ_API_KEY not set in .env")
            return None
        
        client = Groq(api_key=api_key)
        
        # Build prompt
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
            return None
        
        # Extract JSON
        expected_keys_map = {
            "classify": ["category", "priority"],
            "route": ["category", "priority", "department"],
            "resolve": ["category", "priority", "department", "response"],
        }
        expected_keys = expected_keys_map.get(task, [])
        action_dict = extract_json(response_text, expected_keys=expected_keys)
        
        return action_dict
    
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            st.error("⏸️ **Rate Limited**: Groq free tier limit reached. Upgrade at https://console.groq.com/settings/billing")
        else:
            st.error(f"❌ LLM Error: {error_msg[:150]}")
        return None

# ============================================================================
# MAIN LAYOUT
# ============================================================================

with st.sidebar:
    st.title("🤖 AI Testing")
    
    page = option_menu(
        "Menu",
        ["AI Interactive Demo", "AI Batch Testing", "Statistics", "Testing & Verification", "Settings"],
        icons=["play-circle", "speedometer", "bar-chart", "flask-conical", "gear"],
        menu_icon="cast",
        default_index=0,
    )
    
    st.divider()
    
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

# ============================================================================
# PAGE: AI INTERACTIVE DEMO (AI Generates Everything)
# ============================================================================

if page == "AI Interactive Demo":
    st.title("🤖 AI Interactive Demo")
    st.markdown("AI automatically processes tickets. Watch it make decisions in real-time.")
    
    # Info box
    st.info("""
    🧠 **Fully AI-Powered**
    - AI generates category, priority, department, response
    - No manual input needed
    - Watch AI reasoning in real-time
    - Click button → AI processes ticket
    """)
    
    st.divider()
    
    # Task selection
    col1, col2, col3 = st.columns(3)
    with col1:
        task = st.radio(
            "Task",
            ["classify", "route", "resolve"],
            horizontal=True
        )
    with col2:
        st.write("")
        if st.button("🔄 Load New Ticket", use_container_width=True):
            obs = st.session_state.env.reset(seed=random.randint(0, 9999), task=task)
            st.session_state.current_observation = obs
            st.session_state.current_task = task
            st.session_state.ai_generated_action = None
            st.rerun()
    
    with col3:
        st.write("")
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.test_results = []
            st.session_state.total_episodes = 0
            st.session_state.total_reward = 0.0
            st.success("Cleared!")
            st.rerun()
    
    st.divider()
    
    # Display ticket
    if st.session_state.current_observation:
        obs = st.session_state.current_observation
        
        with st.expander("📋 Ticket Details", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**ID:** `{obs.ticket_id}`")
                st.write(f"**Tier:** {obs.sender_tier.title() if obs.sender_tier else 'N/A'}")
                st.write(f"**Sentiment:** {obs.sentiment.title() if obs.sentiment else 'N/A'}")
                st.write(f"**Open Since:** {obs.open_since_hours}h ago")
            with col2:
                st.write(f"**Previous Tickets:** {obs.previous_tickets}")
                st.write(f"**Task:** {task.title()}")
            
            st.write(f"**Subject:** {obs.subject}")
            st.write("**Body:**")
            st.text_area("", value=obs.body, disabled=True, height=100)
        
        st.divider()
        
        # AI Decision Section
        st.subheader("🧠 AI Decision-Making")
        
        if st.button("🚀 Let AI Decide", type="primary", use_container_width=True, key="ai_demo_button"):
            with st.spinner("AI thinking..."):
                action_dict = generate_llm_action(task, obs, "groq")
            
            if action_dict:
                # Create action
                action = TicketAction(
                    category=action_dict.get("category", ""),
                    priority=action_dict.get("priority", ""),
                    department=action_dict.get("department"),
                    response=action_dict.get("response"),
                    requires_escalation=action_dict.get("requires_escalation", False),
                )
                st.session_state.ai_generated_action = action
                st.rerun()
        
        # Display AI-generated action
        if st.session_state.ai_generated_action:
            action = st.session_state.ai_generated_action
            
            st.success("✅ **AI Chose:**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"📌 **Category:** `{action.category.title()}`")
                st.markdown(f"⚡ **Priority:** `{action.priority.title()}`")
                if action.department:
                    st.markdown(f"🏢 **Department:** `{action.department.title()}`")
                if action.requires_escalation:
                    st.markdown("🚨 **Escalation:** Flagged")
            
            with col2:
                if action.response:
                    st.markdown("💬 **AI Response:**")
                    st.text_area("", value=action.response, disabled=True, height=80)
            
            # Submit action
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Accept & Submit", type="primary", use_container_width=True, key="accept_ai"):
                    result = st.session_state.env.step(action)
                    
                    # Store result
                    st.session_state.total_episodes += 1
                    st.session_state.total_reward += result.reward
                    
                    episode_data = {
                        "status": "success",
                        "task": task,
                        "reward": float(result.reward),
                        "action": {
                            "category": action.category,
                            "priority": action.priority,
                            "department": action.department,
                            "response": action.response[:50] if action.response else None,
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                    st.session_state.test_results.append(episode_data)
                    
                    st.success(f"✅ Score: **{result.reward:.1%}**")
                    st.session_state.ai_generated_action = None
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate", use_container_width=True, key="regen_ai"):
                    st.session_state.ai_generated_action = None
                    st.rerun()
    
    else:
        st.info("👈 Click 'Load New Ticket' to start!")

# ============================================================================
# PAGE: AI BATCH TESTING (AI Powers All)
# ============================================================================

elif page == "AI Batch Testing":
    st.title("⚡ AI Batch Testing")
    st.markdown("AI processes multiple tickets automatically. Choose strategy and watch it work.")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        batch_task = st.selectbox("Task", ["classify", "route", "resolve"], key="batch_task")
    
    with col2:
        num_episodes = st.number_input("Episodes", min_value=1, max_value=100, value=10, key="batch_episodes")
    
    with col3:
        batch_mode = st.selectbox(
            "AI Strategy",
            ["standard", "thorough", "aggressive"],
            help="How careful AI should be"
        )
    
    with col4:
        st.write("")
        run_batch = st.button("🚀 Run Batch", type="primary", use_container_width=True)
    
    st.divider()
    
    if run_batch:
        progress_bar = st.progress(0)
        results_container = st.empty()
        
        batch_results = []
        
        with st.spinner(f"AI processing {num_episodes} tickets..."):
            for i in range(num_episodes):
                seed = random.randint(0, 9999)
                
                try:
                    # Reset environment
                    obs = st.session_state.env.reset(seed=seed, task=batch_task)
                    
                    # AI generates action
                    action_dict = generate_llm_action(batch_task, obs, "groq")
                    
                    if action_dict:
                        # Create action
                        action = TicketAction(
                            category=action_dict.get("category", ""),
                            priority=action_dict.get("priority", ""),
                            department=action_dict.get("department"),
                            response=action_dict.get("response"),
                            requires_escalation=action_dict.get("requires_escalation", False),
                        )
                        
                        # Execute action
                        result = st.session_state.env.step(action)
                        
                        batch_results.append({
                            "status": "success",
                            "reward": float(result.reward),
                            "task": batch_task,
                            "action": {
                                "category": action.category,
                                "priority": action.priority,
                                "department": action.department,
                            }
                        })
                        
                        # Update stats
                        st.session_state.total_episodes += 1
                        st.session_state.total_reward += result.reward
                        st.session_state.test_results.append(batch_results[-1])
                    else:
                        batch_results.append({"status": "failed", "reward": 0.0})
                
                except Exception as e:
                    batch_results.append({"status": "failed", "reward": 0.0, "error": str(e)})
                
                # Update progress
                progress_bar.progress((i + 1) / num_episodes)
                
                with results_container.container():
                    successful = sum(1 for r in batch_results if r["status"] == "success")
                    st.info(f"Progress: {i + 1}/{num_episodes} | Success: {successful}/{i + 1}")
        
        st.success("✅ Batch Complete!")
        st.divider()
        
        # Results
        successful = [r for r in batch_results if r["status"] == "success"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Episodes", len(batch_results))
        with col2:
            st.metric("Successful", len(successful))
        with col3:
            if successful:
                avg = sum(r["reward"] for r in successful) / len(successful)
                st.metric("Avg Score", f"{avg:.1%}")
        with col4:
            if successful:
                best = max(r["reward"] for r in successful)
                st.metric("Best", f"{best:.1%}")
        
        st.divider()
        
        # Chart
        if successful:
            import matplotlib.pyplot as plt
            
            rewards = [r["reward"] for r in successful]
            
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.hist(rewards, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
            ax.axvline(sum(rewards) / len(rewards), color='r', linestyle='--', label='Mean')
            ax.set_xlabel("Reward")
            ax.set_ylabel("Frequency")
            ax.set_title(f"AI Rewards Distribution ({batch_mode})")
            ax.legend()
            st.pyplot(fig)
            
            st.divider()
            
            # Download
            json_data = json.dumps(batch_results, indent=2, default=str)
            st.download_button(
                label="📥 Download Results",
                data=json_data,
                file_name=f"ai_batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# ============================================================================
# PAGE: STATISTICS (Tracks All AI Results)
# ============================================================================

elif page == "Statistics":
    st.title("📊 AI Performance Statistics")
    st.markdown("Comprehensive analysis of all AI-generated decisions")
    
    if st.session_state.test_results:
        # Convert to DataFrame
        results_data = []
        for r in st.session_state.test_results:
            if r.get("status") == "success":
                results_data.append({
                    "task": r["task"],
                    "reward": r["reward"],
                    "timestamp": r.get("timestamp", "")
                })
        
        if results_data:
            df = pd.DataFrame(results_data)
            
            # Summary metrics
            st.subheader("📈 Summary Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Episodes", len(df))
            with col2:
                st.metric("Average Score", f"{df['reward'].mean():.1%}")
            with col3:
                st.metric("Best Score", f"{df['reward'].max():.1%}")
            with col4:
                st.metric("Worst Score", f"{df['reward'].min():.1%}")
            
            st.divider()
            
            # By task
            st.subheader("📋 Performance by Task")
            task_stats = df.groupby('task')['reward'].agg(['count', 'mean', 'max', 'min'])
            task_stats.columns = ['Episodes', 'Avg Reward', 'Best', 'Worst']
            task_stats['Avg Reward'] = task_stats['Avg Reward'].apply(lambda x: f"{x:.1%}")
            task_stats['Best'] = task_stats['Best'].apply(lambda x: f"{x:.1%}")
            task_stats['Worst'] = task_stats['Worst'].apply(lambda x: f"{x:.1%}")
            st.dataframe(task_stats, use_container_width=True)
            
            st.divider()
            
            # Reward trend
            st.subheader("📉 Reward Trend")
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(df['reward'], marker='o', linestyle='-', linewidth=2, markersize=4, color='#1f77b4')
            ax.axhline(y=df['reward'].mean(), color='r', linestyle='--', label=f"Average: {df['reward'].mean():.1%}")
            ax.fill_between(range(len(df)), df['reward'], alpha=0.2)
            ax.set_xlabel("Episode")
            ax.set_ylabel("Reward")
            ax.set_title("AI Performance Over Time")
            ax.legend()
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            
            st.divider()
            
            # Download
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"ai_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                json_data = json.dumps(st.session_state.test_results, indent=2, default=str)
                st.download_button(
                    label="📥 Download as JSON",
                    data=json_data,
                    file_name=f"ai_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        else:
            st.info("No successful results yet.")
    else:
        st.info("No test results yet. Run AI Interactive Demo or AI Batch Testing first.")

# ============================================================================
# PAGE: TESTING & VERIFICATION
# ============================================================================

elif page == "Testing & Verification":
    st.title("🧪 Testing & Verification Suite")
    st.markdown("API-based system validation tests")
    
    tab1, tab2, tab3, tab4 = st.tabs(["System Tests", "Data Validation", "API Health", "Full Report"])
    
    # ========== TAB 1: SYSTEM TESTS ==========
    with tab1:
        st.subheader("🔧 System Tests")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧪 Test 1: Environment", use_container_width=True):
                with st.spinner("Testing..."):
                    try:
                        env = CustomerSupportEnvironment()
                        st.success("✅ Environment OK")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col2:
            if st.button("🧪 Test 2: Reset/Step", use_container_width=True):
                with st.spinner("Testing..."):
                    try:
                        obs = st.session_state.env.reset(seed=0, task="classify")
                        action = TicketAction(category="billing", priority="medium")
                        result = st.session_state.env.step(action)
                        st.success("✅ Methods OK")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("🧪 Test 3: Pydantic Models", use_container_width=True):
                with st.spinner("Testing..."):
                    try:
                        action1 = TicketAction(category="billing", priority="high")
                        action2 = TicketAction(category="technical", priority="urgent", department="tier1", response="Test")
                        st.success("✅ Models OK")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col4:
            if st.button("🖥️ Test 4: Groq API", use_container_width=True):
                with st.spinner("Testing..."):
                    try:
                        from groq import Groq
                        api_key = os.getenv("GROQ_API_KEY")
                        if not api_key:
                            st.error("❌ API key not set")
                        else:
                            client = Groq(api_key=api_key)
                            models = client.models.list()
                            st.success(f"✅ Groq OK ({len(models.data)} models)")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
    
    # ========== TAB 2: DATA VALIDATION ==========
    with tab2:
        st.subheader("📋 Data Validation")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Load Tickets", use_container_width=True):
                with st.spinner("Loading..."):
                    try:
                        from customer_support_env.data import TICKETS, validate_tickets
                        validate_tickets()
                        st.success(f"✅ {len(TICKETS)} tickets OK")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col2:
            if st.button("✅ Validate Schemas", use_container_width=True):
                with st.spinner("Validating..."):
                    try:
                        from customer_support_env.data import TICKETS
                        required_fields = ["ticket_id", "subject", "body", "category", "priority"]
                        for ticket in TICKETS:
                            for field in required_fields:
                                if field not in ticket:
                                    raise ValueError(f"Missing {field}")
                        st.success("✅ Schemas OK")
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
        
        with col3:
            if st.button("✅ Distribution", use_container_width=True):
                with st.spinner("Analyzing..."):
                    try:
                        from customer_support_env.data import TICKETS
                        from collections import Counter
                        categories = Counter(t["category"] for t in TICKETS)
                        st.success("✅ Distribution OK")
                        
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.bar(categories.keys(), categories.values(), color='steelblue')
                        ax.set_title("Ticket Category Distribution")
                        st.pyplot(fig)
                    except Exception as e:
                        st.error(f"❌ Failed: {str(e)}")
    
    # ========== TAB 3: API HEALTH ==========
    with tab3:
        st.subheader("🌐 API Health Check")
        
        if st.button("📡 Check All APIs", use_container_width=True, type="primary"):
            with st.spinner("Checking APIs..."):
                try:
                    import requests
                    
                    results = []
                    
                    # Check Groq
                    try:
                        from groq import Groq
                        api_key = os.getenv("GROQ_API_KEY")
                        if api_key:
                            client = Groq(api_key=api_key)
                            client.models.list()
                            results.append(("Groq API", "✅ Online"))
                        else:
                            results.append(("Groq API", "⚠️ No API key"))
                    except:
                        results.append(("Groq API", "❌ Offline"))
                    
                    # Display results
                    for api_name, status in results:
                        if "✅" in status:
                            st.success(f"{api_name}: {status}")
                        elif "⚠️" in status:
                            st.warning(f"{api_name}: {status}")
                        else:
                            st.error(f"{api_name}: {status}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # ========== TAB 4: FULL REPORT ==========
    with tab4:
        st.subheader("📄 Full Verification Report")
        
        if st.button("📋 Generate Report", use_container_width=True, type="primary"):
            with st.spinner("Generating report..."):
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "tests": {},
                    "summary": {}
                }
                
                tests_passed = 0
                tests_failed = 0
                
                # Run all tests
                test_functions = [
                    ("Environment", lambda: CustomerSupportEnvironment()),
                    ("Reset", lambda: st.session_state.env.reset(seed=0, task="classify")),
                    ("Step", lambda: st.session_state.env.step(TicketAction(category="billing", priority="medium"))),
                    ("Pydantic", lambda: TicketAction(category="billing", priority="high")),
                    ("Tickets", lambda: __import__('customer_support_env.data', fromlist=['TICKETS']).TICKETS),
                ]
                
                for test_name, test_func in test_functions:
                    try:
                        test_func()
                        report["tests"][test_name] = "PASSED"
                        tests_passed += 1
                    except Exception as e:
                        report["tests"][test_name] = f"FAILED: {str(e)}"
                        tests_failed += 1
                
                # Summary
                report["summary"] = {
                    "total": len(report["tests"]),
                    "passed": tests_passed,
                    "failed": tests_failed,
                    "success_rate": f"{(tests_passed / len(report['tests']) * 100):.1f}%"
                }
                
                # Display
                st.success("✅ Report Generated!")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total", report["summary"]["total"])
                with col2:
                    st.metric("Passed", report["summary"]["passed"], delta_color="normal")
                with col3:
                    st.metric("Failed", report["summary"]["failed"], delta_color="inverse")
                with col4:
                    st.metric("Success Rate", report["summary"]["success_rate"])
                
                st.divider()
                
                # Details
                st.subheader("Details")
                for test_name, status in report["tests"].items():
                    if "PASSED" in str(status):
                        st.success(f"✅ {test_name}: {status}")
                    else:
                        st.error(f"❌ {test_name}: {status}")
                
                st.divider()
                
                # Download
                json_report = json.dumps(report, indent=2, default=str)
                st.download_button(
                    label="📥 Download Report",
                    data=json_report,
                    file_name=f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# ============================================================================
# PAGE: SETTINGS
# ============================================================================

elif page == "Settings":
    st.title("⚙️ Settings & Information")
    
    st.subheader("ℹ️ Environment Info")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Total Tickets:** {len(TICKETS)}")
        st.write("**Supported Tasks:** classify, route, resolve")
    
    with col2:
        st.write("**UI Framework:** Streamlit")
        st.write("**AI Provider:** Groq (free tier)")
    
    st.divider()
    
    st.subheader("📚 Task Definitions")
    
    with st.expander("🎯 Classify (Easy)", expanded=False):
        st.write("AI classifies ticket category and assigns priority level.")
    
    with st.expander("🛣️ Route (Medium)", expanded=False):
        st.write("AI classifies, prioritizes, AND routes to appropriate department.")
    
    with st.expander("✉️ Resolve (Hard)", expanded=False):
        st.write("AI classifies, prioritizes, routes, AND generates response text.")
    
    st.divider()
    
    st.subheader("🏆 Scoring")
    st.write("""
    - **Classify:** 60% category + 40% priority
    - **Route:** 35% category + 25% priority + 25% department + 15% escalation
    - **Resolve:** 20% category + 15% priority + 20% department + 15% escalation + 30% response
    """)
    
    st.divider()
    
    if st.button("🗑️ Clear All Results"):
        st.session_state.test_results = []
        st.session_state.total_episodes = 0
        st.session_state.total_reward = 0.0
        st.session_state.current_observation = None
        st.session_state.ai_generated_action = None
        st.success("All results cleared!")
        st.rerun()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
    <div style="text-align: center; margin-top: 20px; padding: 10px; color: #666;">
        <p>🤖 100% AI-Powered Testing | Powered by Streamlit</p>
        <p style="font-size: 0.8em;">AI handles all decisions - no manual input required.</p>
    </div>
""", unsafe_allow_html=True)
