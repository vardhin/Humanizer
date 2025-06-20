# VHumanize

**VHumanize** is a web-based tool for transforming AI-generated text into natural, human-like content and detecting AI-generated text. It provides advanced paraphrasing, rewriting, and AI detection features, leveraging state-of-the-art NLP models and a modern Svelte frontend.

## ✨ Features

- 🔍 **AI Detection**: Detects AI-generated content at line and sentence levels, with visual highlighting and detailed statistics
- 🔄 **Humanization Pipeline**: Two-step process (Paraphrasing + Rewriting) to convert AI text into more human-like writing
- 🤖 **Multi-Model Support**: Choose from multiple transformer-based models (T5, BART, Pegasus, etc.) for paraphrasing and rewriting
- ⚡ **Enhanced Mode**: Optionally use advanced prompts and NLP techniques for higher-quality rewriting
- 🔬 **Combined Humanize & Verify**: Instantly humanize text and check for AI traces in a single workflow
- 📋 **Copy & Share**: Easily copy results to clipboard
- 📱 **Responsive UI**: Clean, modern interface built with SvelteKit and Vite

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **Flask** - Web framework
- **NLTK**, **spaCy**, **TextBlob** - NLP processing and advanced rewriting
- **Transformers** (HuggingFace) - Paraphrasing and rewriting models (T5, BART, Pegasus)

### Frontend
- **SvelteKit** - Modern, component-based UI framework
- **Vite** - Fast build tool and dev server
- **Svelte Stores** - Reactive state management
- **Lucide Icons** - UI icons

## 📁 Project Structure

```
humanizer/
├── detector.py              # AI detection backend logic
├── download_models.py       # Script to download required models
├── main.py                  # Backend server entry point
├── paraphraser.py           # Paraphrasing logic and model management
├── rewriter.py              # Advanced rewriting and NLP enhancements
├── requirements.txt         # Python dependencies
├── README.md
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── svelte.config.js
│   ├── src/
│   │   ├── app.html
│   │   ├── lib/
│   │   │   ├── script.js    # Frontend logic and API calls
│   │   │   └── style.css    # Main CSS
│   │   └── routes/
│   │       └── +page.svelte # Main Svelte page
│   └── static/
│       └── favicon.png
└── __pycache__/
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 16+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/vhumanize.git
   cd vhumanize
   ```

2. **Backend Setup**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Download required models
   python download_models.py
   
   # Start the backend server
   python main.py
   ```
   The API server will start at `http://localhost:8080`

3. **Frontend Setup**
   ```bash
   # Navigate to frontend directory
   cd frontend
   
   # Install Node.js dependencies
   npm install
   
   # Start the development server
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

## 📡 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/paraphrase_only` | Paraphrase text with selected model |
| `/rewrite_only` | Rewrite text for humanization |
| `/paraphrase_multi` | Paraphrase with multiple models |
| `/paraphrase_all` | Paraphrase with all available models |
| `/highlight_ai` | Highlight detected AI-generated sentences/lines |
| `/humanize_and_check` | Humanize and verify in one step |
| `/models` | List available models |
| `/health` | Backend health check |

## ⚙️ Configuration

- **Model Selection**: Choose or recommend models for paraphrasing/humanization
- **Enhanced Mode**: Toggle for higher-quality, slower rewriting
- **Detection Threshold**: Adjust sensitivity for AI detection

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [SvelteKit](https://kit.svelte.dev/) and [HuggingFace Transformers](https://huggingface.co/transformers/)
- Icons by [Lucide](https://lucide.dev/)
- Thanks to all contributors and the open-source community

## 🐛 Issues & Support

If you encounter any issues or have questions, please [open an issue](https://github.com/yourusername/vhumanize/issues) on GitHub.

---

<div align="center">
  Made with ❤️ by [Your Name](https://github.com/yourusername)
</div>