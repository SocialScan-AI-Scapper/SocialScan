# SocialScan: AI Instagram Behavior Scraper

## 🚀 Overview
SocialScan is an AI-powered tool that scrapes public Instagram profiles, extracting user data, post images, captions, likes, and related profiles for behavioral analysis. It leverages fine-tuned LLM models to detect patterns and provide structured insights for forensic investigations and social behavior analysis.

## 🏆 Features
- **Automated Instagram Scraping** – Extracts user profiles, posts, captions, and engagement data.
- **AI-Powered Behavioral Analysis** – Uses LLMs to detect trends and user behaviors.
- **Fine-Tuned Model** – Custom-trained AI for investigative purposes.
- **Interactive Web Interface** – Built with Streamlit for easy data visualization.
- **Secure Data Handling** – Uses `python-dotenv` for secure credentials.
- **Multi-Platform Support** – Works on both desktop and mobile.

## 🛠️ Technologies Used
- **Streamlit** – Interactive UI
- **LangChain** & **LangChain-Ollama** – AI model integration
- **Selenium** – Dynamic content scraping
- **BeautifulSoup4** – HTML parsing
- **html5lib** – Browser-like HTML processing
- **python-dotenv** – Secure environment variable management
- **Database** – For structured data storage
- **Fine-tuned LLM** – For AI-based behavioral analysis

## 📌 Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/SocialScan.git
cd SocialScan

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Usage
```bash
# Run the Streamlit app
streamlit run app.py
```

## 📊 Project Workflow
1. **Input & Platform Selection** – User enters Instagram profile URL.
2. **Dynamic Content Handling** – Selenium scrapes JavaScript-heavy pages.
3. **Data Extraction & Parsing** – BeautifulSoup extracts key information.
4. **Database Storage** – Data is securely stored.
5. **AI Behavioral Analysis** – LLM fine-tuned for user profiling.
6. **Report Generation** – AI generates structured insights.

## 🔥 Challenges Faced
- **Dynamic Content** – Overcame JavaScript rendering with Selenium.
- **Data Structuring** – Used BeautifulSoup for efficient parsing.
- **LLM Fine-Tuning** – Required multiple iterations for accuracy.
- **Security & Compliance** – Managed credentials securely with `dotenv`.

## 📜 License
This project is licensed under the MIT License.

## 💡 Future Enhancements
- Expand support to Facebook, Twitter, and Telegram.
- Improve AI accuracy with additional training datasets.
- Develop a browser extension for easier access.

## 👨‍💻 Authors
- **Lokendra Sinha**  
- **Raj Khatri**  


## 🤝 Contribution
Contributions are welcome! Fork the repository and submit a pull request. 🚀
