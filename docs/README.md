# MSA Investment Ranking Web Application

A professional, interactive **100% static HTML** web dashboard for analyzing US Metropolitan Statistical Areas (MSAs) investment potential. Perfect for GitHub Pages deployment! 🎉

## ✨ Features

- ✅ **100% Static HTML** - No backend server needed  
- ✅ **GitHub Pages Ready** - Deploy directly from your repository
- ✅ **Interactive Dashboard** - View investment rankings and key metrics
- ✅ **Search & Filter** - Find specific MSAs by name or code
- ✅ **5 Interactive Views:**
  1. **Overview** - Rankings table + score distribution chart
  2. **Index Scoring** - Interactive weight adjustment, recalculate scores in real-time
  3. **Detailed Analysis** - Deep dive into specific MSA metrics
  4. **6-Dimensional Analysis** - Radar charts comparing markets
  5. **Raw Data** - Complete dataset with all 13 factors, CSV export

- **13 Comprehensive Factors Analyzed:**
  - **Demographic:** Population, Growth, Employment Rate, Income, Income Growth
  - **Real Estate:** Rent, Home Values, Rent-to-Income Ratio, Vacancy Rate
  - **Investment:** Cap Rate Spread, Tax Differential, Energy Efficiency Score

## 📂 Simplified Project Structure

```
msa-investment-app/
├── index.html              ⭐ Single HTML file (all-in-one!)
├── data/
│   └── sample_data.json    # Your data
└── README.md
```

## 🚀 Deploy to GitHub Pages (Easy!)

### Step 1: Push Files to GitHub
```bash
cd /path/to/Capstone-Coding
git add .
git commit -m "Convert to static HTML for GitHub Pages"
git push origin main
```

### Step 2: Enable GitHub Pages
1. Go to your GitHub repository
2. Click **Settings**
3. Navigate to **Pages** (left sidebar)
4. **Source:** Select `main` branch
5. **Folder:** Select `docs` folder ← **Important!**
6. Click **Save**

GitHub will show your live URL: `https://yourusername.github.io/Capstone-Coding/`

### Step 3: Access Your App
Open the URL above in your browser! Your dashboard is live! 🎉

---

## 💻 Run Locally (Optional)

### Using Python HTTP Server
```bash
cd docs
python3 -m http.server 8000
```
Then visit: `http://localhost:8000`

### Using Live Server (VS Code)
1. Install "Live Server" extension in VS Code
2. Right-click `index.html`
3. Select "Open with Live Server"

---

## 📊 Using Your Data

The app loads data from `data/sample_data.json`. To use your own Census data:

### 1. Prepare Your Data in JSON Format
```json
{
  "stats": {
    "year": 2024,
    "total_msa_count": 71
  },
  "msas": [
    {
      "msa_code": 12060,
      "msa_name": "Metro Area Name",
      "Total_Population": 6144376,
      "Investment_Score": 78.5,
      "Economic_Index": 0.65,
      "Stability_Index": 0.58,
      "Supply_Index": 0.72,
      "Pricing_Index": 0.68,
      "Valuation_Index": 0.55,
      "Capital_Index": 0.60,
      "Median_Rent": 1500,
      "Median_Income": 75000,
      "Median_Home_Value": 450000,
      "Pop_Growth": 0.025,
      "Income_Growth": 0.032,
      "Employment_Rate": 0.96,
      "Rent_to_Income_Ratio": 0.20,
      "Vacancy_Rate": 0.08,
      "Implied_Value": 1200000,
      "Cap Spread": 0.5,
      "Diff_Effective_Rate": 0.3,
      "Average HERS Index Score": 65
    },
    // ... more MSA entries
  ]
}
```

### 2. Replace sample_data.json
1. Export your analysis from the notebook as JSON
2. Replace `msa-investment-app/data/sample_data.json` with your file
3. Commit and push to GitHub
4. GitHub Pages automatically updates! ✨

---

## 🎨 Customization

### Change Colors
Edit the `<style>` section in `index.html`:
- `#FFD700` = Gold/Yellow  
- `#D4AF37` = Dark Gold
- `#667eea` = Purple
- `#764ba2` = Dark Purple

### Change Title/Header
Find in `index.html`:
```html
<h1>🏢 MSA Investment Ranking Dashboard</h1>
<p>Interactive Analysis of US Metropolitan Statistical Areas Investment Potential</p>
```

### Modify Default Weights
In the JavaScript section, update:
```javascript
currentWeights = {
    economic: 0.25,    // Change these values
    stability: 0.15,
    supply: 0.15,
    pricing: 0.15,
    valuation: 0.20,
    capital: 0.10
};
```

---

## 🛠️ Troubleshooting

**Data not showing on GitHub Pages?**
- Verify `data/sample_data.json` is in the repository
- Check browser console (F12 → Console tab) for errors
- Ensure JSON format matches the structure above

**Charts not rendering?**
- Clear browser cache (Ctrl+Shift+Delete)
- Check browser console for JavaScript errors
- The app requires Chart.js library (loaded via CDN)

**Can't run locally?**
- Make sure you're in the `msa-investment-app` folder
- Python 3.8+ required for `http.server`
- Try different ports if 8000 is in use: `python3 -m http.server 3000`

---

## 📐 How It Works

### All-in-One HTML File
- **index.html** contains everything: HTML + CSS + JavaScript
- Data loads from `data/sample_data.json` (local JSON file)
- All computations happen in the browser
- No network requests needed (except CDN for Chart.js library)

### Interactive Features
- **Search:** Live autocomplete as you type
- **Interactive Weights:** Drag sliders to adjust investment criteria
- **Real-time Charts:** Score recalculation happens instantly
- **Download CSV:** Export raw data for external analysis

### 6 Investment Dimensions
```
Economic_Index = Growth metrics (employment, population, income)
Stability_Index = Affordability & market stability
Supply_Index = Market tightness & occupancy
Pricing_Index = Rent growth & pricing power
Valuation_Index = Property value potential
Capital_Index = Cap rates & tax differentials
```

---

## 👨‍💼 Technologies

- **HTML5** - Structure
- **CSS3** - Responsive Design (Dark theme with gold accents)
- **Vanilla JavaScript** - All interactivity
- **Chart.js** - Interactive charts & visualizations
- **JSON** - Data storage

**Zero dependencies to install!** Everything runs in the browser.

---

## 📝 What You Get

✅ Fully functional investment analysis dashboard  
✅ Interactive weight adjustment system  
✅ 5 different analysis views  
✅ CSV data export  
✅ Mobile responsive design  
✅ Dark theme optimized for readability  
✅ GitHub Pages ready  

---

**Ready to deploy?** Push to GitHub and enable Pages. Your dashboard goes live in minutes! 🚀
