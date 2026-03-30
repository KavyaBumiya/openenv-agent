# Streamlit UI Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`

---

## Features

### 🎯 Interactive Demo
- **Load New Ticket**: Get a random ticket to process
- **Load Specific Ticket**: Use a seed to load a specific ticket
- **Real-time Actions**: Classify, route, and resolve tickets
- **Instant Feedback**: See scores and score breakdowns
- **Multiple Tasks**: Try Easy (classify), Medium (route), or Hard (resolve)

### 📊 Statistics & Analytics
- **Session Metrics**: Track episodes and average rewards
- **Performance by Task**: Compare results across task types
- **Reward Trends**: Visualize improvement over time
- **Episode History**: View details of all completed episodes
- **Export Data**: Download history as CSV or JSON

### ⚡ Batch Testing
Run multiple episodes automatically with different strategies:
- **Random**: Randomly selected actions
- **Mean Values**: Comfortable middle-ground actions
- **All High**: Maximum priority/escalation strategy

### ⚙️ Settings
- View environment information
- Learn task details and requirements
- Understand scoring mechanics
- Reset session statistics

---

## How to Use

### Step 1: Select a Task
Choose between:
- **Classify** (Easy): Set category and priority
- **Route** (Medium): Classify + priority + department
- **Resolve** (Hard): Full resolution with response text

### Step 2: Load a Ticket
Click "Load New Ticket" to get a random customer support ticket. The ticket shows:
- Customer type (individual/enterprise)
- Contact channel (phone/email/chat)
- Subject and body text
- True labels (for reference)

### Step 3: Take an Action
Fill in your solution based on the task:
- **Category**: Classify the issue
- **Priority**: Set urgency (low/medium/high/urgent)
- **Department** (if route/resolve): Route to appropriate team
- **Response** (if resolve): Provide customer-facing response
- **Escalation**: Mark for escalation if needed

### Step 4: Review Results
Get immediate feedback:
- Your score (0-100%)
- Comparison with true labels
- Detailed score breakdown
- Explanatory feedback

### Step 5: Continue or Analyze
- Load another ticket to keep practicing
- Check Statistics for performance analysis
- Run batch tests to evaluate strategies

---

## Session Statistics

Track your performance with:
- **Episodes**: Total tickets processed
- **Average Reward**: Mean score across all episodes
- **Best/Worst Score**: Performance range
- **Reward Trend**: Visual chart showing improvement
- **Task Breakdown**: Performance per difficulty level

---

## Batch Testing

Test strategies at scale:

1. Select a task difficulty
2. Choose number of episodes (1-100)
3. Pick an action strategy:
   - **Random**: Tests baseline randomness
   - **Mean Values**: Tests reasonable defaults
   - **All High**: Tests aggressive routing
4. Get results with reward distribution

---

## Tips for Better Performance

### For Classify Task
- Look for keywords in the issue description
- Enterprise customers with urgent issues need higher priority
- Technical issues usually need escalation consideration

### For Route Task
- Route technical issues to engineering
- Billing issues need specialized handling
- Keep tier1 for general inquiries
- Enterprise escalations matter more

### For Resolve Task
- Provide specific, actionable responses
- Match the customer's tone
- Reference their specific issue
- Offer clear next steps

---

## Troubleshooting

### App won't start
```bash
# Make sure you have Streamlit installed
pip install streamlit>=1.28.0

# Try clearing cache
streamlit cache clear
streamlit run streamlit_app.py --logger.level=debug
```

### Environment not found
```bash
# Verify your Python path includes the project
# The app should auto-find customer_support_env

# Try running from the project root
cd d:\Hackathon
streamlit run streamlit_app.py
```

### API key issues (if using LLM features)
```bash
# Set your Groq API key
$env:GROQ_API_KEY="your-key-here"  # Windows PowerShell
# export GROQ_API_KEY="your-key-here"  # Mac/Linux
```

---

## File Structure

```
streamlit_app.py          # Main Streamlit UI application
requirements.txt          # Updated with Streamlit dependency
└── customer_support_env/
    ├── environment.py    # Core environment logic
    ├── models.py         # Data models
    ├── data.py           # Ticket data
    └── baseline.py       # Baseline evaluations
```

---

## Performance Notes

- **Session State**: All history is kept in memory during the session
- **Export**: Download statistics to preserve data between sessions
- **Batch Testing**: Each episode runs sequentially (may take time for 100 episodes)
- **Scrolling**: Use sidebar to collapse sections and improve performance

---

## Integration with Existing Tools

The Streamlit UI works alongside other entry points:
- `python main.py server` - FastAPI backend (no UI)
- `python main.py baseline` - Automated evaluation
- `streamlit run streamlit_app.py` - This web UI

You can run multiple simultaneously!

---

## Keyboard Shortcuts

In Streamlit:
- `r` - Rerun the script
- `?` - Help menu
- `c` - Clear cached files
- `C` - Clear all cache

---

## Next Steps

1. ✅ Run the app and load a ticket
2. ✅ Try all three task difficulties
3. ✅ Check your statistics
4. ✅ Run batch tests with different strategies
5. ✅ Download and analyze your results
