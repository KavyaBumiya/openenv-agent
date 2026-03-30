# Streamlit Integration - Quick Reference

## 📌 TL;DR - Get Started in 60 Seconds

```powershell
# 1. Install dependencies (one-time)
pip install -r requirements.txt

# 2. Run the app
streamlit run streamlit_app.py

# ✨ Browser opens → Start using!
```

---

## 🎯 What You Can Do Now

### ✨ Interactive Testing
- Load random customer support tickets
- Classify, route, or resolve them
- Get instant 0-100% scores
- See detailed feedback

### 📊 Track Performance
- Real-time statistics
- Reward trend graphs
- Performance by difficulty
- Download your results

### ⚡ Batch Processing
- Test 1-100 tickets automatically
- Compare different strategies
- Analyze reward distributions

### 💾 Export & Analyze
- Download CSV or JSON
- Analyze patterns
- Share results

---

## 📁 Files Created/Modified

| File | Purpose |
|------|---------|
| `streamlit_app.py` | 🎨 Main Streamlit application (700+ lines) |
| `launch_streamlit.py` | 🐍 Python launcher script |
| `launch_streamlit.ps1` | 🔵 PowerShell launcher (Windows) |
| `.streamlit/config.toml` | ⚙️ UI configuration |
| `requirements.txt` | 📦 Updated with Streamlit + pandas |
| `STREAMLIT_GUIDE.md` | 📖 Full user guide |
| `STREAMLIT_SETUP.md` | 📚 Setup documentation |

---

## 🔥 Three Ways to Launch

### Method 1: Direct (Simplest)
```powershell
streamlit run streamlit_app.py
```

### Method 2: Python Launcher
```bash
python launch_streamlit.py           # Normal
python launch_streamlit.py --dev     # Debug mode
```

### Method 3: PowerShell Launcher (Windows)
```powershell
.\launch_streamlit.ps1               # Normal
.\launch_streamlit.ps1 -Install      # First time (auto-installs)
.\launch_streamlit.ps1 -Debug        # Debug mode
```

---

## 🎮 Main UI Sections

### 🎯 Interactive Demo
**What**: Process tickets one at a time
**How**: Load ticket → Fill form → Submit → See score
**Best for**: Learning and practice

### 📊 Statistics & Analytics  
**What**: View your performance history
**How**: Charts, tables, metrics, exports
**Best for**: Analyzing improvement patterns

### ⚡ Batch Testing
**What**: Run many episodes automatically
**How**: Select task, count, strategy → Run → See distribution
**Best for**: Benchmarking and comparison

### ⚙️ Settings
**What**: Environment info and documentation
**How**: Read guides, understand scoring
**Best for**: Learning how tasks work

---

## 💡 Pro Tips

1. **Start Easy**: Begin with "classify" task to understand scoring
2. **Check Stats**: Go to Statistics page after 10 episodes to see trends
3. **Test Strategies**: Use Batch Testing to compare different approaches
4. **Export Data**: Download CSV after sessions for external analysis
5. **Debug Mode**: Use `streamlit run streamlit_app.py --logger.level=debug` for troubleshooting

---

## 📊 Example Performance Metrics

After running some episodes, you'll see:
- **Episodes**: 15
- **Avg Reward**: 72%
- **Best Score**: 95%
- **Worst Score**: 45%
- **Tasks Tried**: All 3 (classify, route, resolve)

---

## 🚀 Next Steps

1. **Install**: Run `pip install -r requirements.txt`
2. **Launch**: Run `streamlit run streamlit_app.py`
3. **Try**: Load a ticket and make a classification
4. **Explore**: Try different tasks and check statistics
5. **Analyze**: Download your results and review

---

## 📚 Reference

| Feature | Location |
|---------|----------|
| User Guide | `STREAMLIT_GUIDE.md` |
| Setup Docs | `STREAMLIT_SETUP.md` |
| Original CLI | `python main.py` |
| FastAPI Server | `python main.py server` |

---

## ✅ Verification Checklist

- [x] Streamlit added to requirements.txt
- [x] Main app created (streamlit_app.py)
- [x] Configuration file created (.streamlit/config.toml)
- [x] Python launcher created (launch_streamlit.py)
- [x] PowerShell launcher created (launch_streamlit.ps1)
- [x] User guide written (STREAMLIT_GUIDE.md)
- [x] Setup doc written (STREAMLIT_SETUP.md)
- [x] Syntax verified (no errors)

---

## 🎉 Ready to Go!

Everything is set up and ready. Just run:

```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Your web UI will open at **http://localhost:8501** 🚀
