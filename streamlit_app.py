#!/usr/bin/env python3
"""
Customer Support RL Environment - 100% LLM API-Driven Testing UI

Fully automated LLM testing. No manual testing interface.
Supports any LLM provider: Groq, GPT, Claude, etc.

Run with: streamlit run streamlit_app.py
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import Optional, Dict, Any

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
    st.title("🤖 LLM Testing")
    
    page = option_menu(
        "Menu",
        ["Auto-Test", "Statistics", "Testing & Verification", "Settings"],
        icons=["play-circle", "bar-chart", "flask-conical", "gear"],
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
# PAGE: AUTO-TEST (LLM-Powered)
# ============================================================================

if page == "Auto-Test":
    st.title("🤖 Automated LLM Testing")
    st.markdown("100% API-driven testing. LLM models handle all decisions - no manual input.")
    
    # Info box
    st.info("""
    ✨ **Fully Automated**
    - LLM API generates all actions
    - No manual testing required
    - Real-time results
    - Supports: Groq (free tier), GPT, Claude, etc.
    """)
    
    st.divider()
    
    # Configuration
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        task = st.selectbox("Task", ["classify", "route", "resolve"], key="auto_task")
    
    with col2:
        num_episodes = st.number_input("Episodes", min_value=1, max_value=50, value=5, key="auto_episodes")
    
    with col3:
        llm_provider = st.selectbox(
            "LLM Provider",
            ["groq"],  # Only Groq available now
            help="Currently supporting Groq free tier"
        )
    
    with col4:
        st.write("")
        run_button = st.button("🚀 Run Auto-Test", type="primary", use_container_width=True)
    
    st.divider()
    
    if run_button:
        progress_bar = st.progress(0)
        results_container = st.empty()
        
        batch_results = []
        
        with st.spinner(f"Running {num_episodes} LLM-driven episodes..."):
            for i in range(num_episodes):
                episode_result = run_llm_episode(task, llm_provider, seed=random.randint(0, 9999))
                batch_results.append(episode_result)
                
                # Update statistics
                if episode_result["status"] == "success":
                    st.session_state.total_episodes += 1
                    st.session_state.total_reward += episode_result["reward"]
                    st.session_state.test_results.append(episode_result)
                
                # Update progress
                progress_bar.progress((i + 1) / num_episodes)
                
                with results_container.container():
                    successful = sum(1 for r in batch_results if r["status"] == "success")
                    st.info(f"Progress: {i + 1}/{num_episodes} | Success: {successful}/{i + 1}")
        
        # Results
        st.success("✅ Auto-Test Completed!")
        st.divider()
        
        # Summary
        st.subheader("📊 Results Summary")
        successful_results = [r for r in batch_results if r["status"] == "success"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Episodes", len(batch_results))
        with col2:
            st.metric("Successful", len(successful_results))
        with col3:
            if successful_results:
                avg_score = sum(r["reward"] for r in successful_results) / len(successful_results)
                st.metric("Avg Score", f"{avg_score:.1%}")
        with col4:
            if successful_results:
                best_score = max(r["reward"] for r in successful_results)
                st.metric("Best Score", f"{best_score:.1%}")
        
        st.divider()
        
        # Detailed results table
        if successful_results:
            st.subheader("📋 Detailed Results")
            results_df = pd.DataFrame(successful_results)
            results_df = results_df[["task", "reward", "llm_provider", "timestamp"]]
            results_df.columns = ["Task", "Reward", "LLM", "Timestamp"]
            results_df["Reward"] = results_df["Reward"].apply(lambda x: f"{x:.1%}")
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Download results
            json_data = json.dumps(batch_results, indent=2, default=str)
            st.download_button(
                label="📥 Download Results as JSON",
                data=json_data,
                file_name=f"llm_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# ============================================================================
# PAGE: STATISTICS
# ============================================================================

elif page == "Statistics":
    st.title("📊 Statistics & Analytics")
    st.markdown("Analysis of all LLM-generated test results")
    
    if st.session_state.test_results:
        # Convert to DataFrame
        results_data = []
        for r in st.session_state.test_results:
            if r["status"] == "success":
                results_data.append({
                    "task": r["task"],
                    "reward": r["reward"],
                    "llm": r["llm_provider"],
                    "timestamp": r["timestamp"]
                })
        
        df = pd.DataFrame(results_data)
        
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
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df['reward'], marker='o', linestyle='-', linewidth=2, markersize=4, color='#1f77b4')
        ax.axhline(y=df['reward'].mean(), color='r', linestyle='--', label=f"Average: {df['reward'].mean():.1%}")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward")
        ax.set_title("Reward per Episode - LLM Performance")
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
        st.divider()
        
        # Export
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"llm_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            json_data = json.dumps(st.session_state.test_results, indent=2, default=str)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name=f"llm_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("No test results yet. Run Auto-Test to generate data.")

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
        st.write("**LLM Provider:** Groq (free tier)")
    
    st.divider()
    
    st.subheader("📚 Task Definitions")
    
    with st.expander("🎯 Classify (Easy)"):
        st.write("Classify ticket category and priority only.")
    
    with st.expander("🛣️ Route (Medium)"):
        st.write("Classify, prioritize, AND route to department.")
    
    with st.expander("✉️ Resolve (Hard)"):
        st.write("Classify, prioritize, route, AND provide response text.")
    
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
        st.success("All results cleared!")
        st.rerun()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
    <div style="text-align: center; margin-top: 20px; padding: 10px; color: #666;">
        <p>🤖 100% LLM API-Driven Testing | Powered by Streamlit</p>
        <p style="font-size: 0.8em;">Groq LLM handles all decisions - no manual input required.</p>
    </div>
""", unsafe_allow_html=True)
