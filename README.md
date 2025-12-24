# CE224.Q11 - People Counting System

A real-time people counting application powered by YOLOv11, featuring a FastAPI backend and Next.js frontend with bounding box visualization.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![YOLOv11](https://img.shields.io/badge/YOLO-v11-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Dataset](#-dataset)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Real-time People Detection**: Utilizes YOLOv11 for accurate people counting
- **Multiple Input Sources**: Support for images, video files, webcam, and RTSP streams
- **Web Interface**: Modern, responsive UI built with Next.js and Tailwind CSS
- **RESTful API**: FastAPI backend with automatic OpenAPI documentation
- **Bounding Box Visualization**: Interactive canvas displaying detected people with confidence scores
- **Statistics Dashboard**: Track detection history and metrics
- **NCNN Model Support**: Optimized model for CPU inference

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js GUI   │────▶│  FastAPI API    │────▶│  YOLOv11 Model  │
│   (Port 3000)   │     │  (Port 8000)    │     │  (NCNN/PyTorch) │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📁 Project Structure

```
CE224.Q11_People_Counting/
├── gui/                        # Next.js Frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   ├── components/        # React Components
│   │   │   ├── BoundingBoxCanvas.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── ImageUploader.tsx
│   │   │   └── StatsPanel.tsx
│   │   ├── lib/               # API Client
│   │   └── types/             # TypeScript Types
│   └── package.json
│
├── web_service/               # FastAPI Backend
│   ├── main.py               # Application Entry
│   ├── routers/
│   │   ├── count_people.py   # People Counting Endpoints
│   │   └── get_camera.py     # Camera Endpoints (TBD)
│   └── schema/               # Pydantic Models
│       └── count_people.py
│
├── infra/                     # ML Infrastructure
│   ├── main.py               # CLI Inference Script
│   ├── weights/              # Model Weights
│   │   ├── yolov11n.pt
│   │   └── yolov11n_ncnn_model/
│   ├── dataset/              # Training Data
│   ├── notebooks/            # Jupyter Notebooks
│   ├── tmp/                  # Temporary Output
│   └── utils/                # Utility Scripts
│
└── requirements.txt          # Python Dependencies
```

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for GUI)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/chisphung/CE224.Q11_People_Counting.git
cd CE224.Q11_People_Counting
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Frontend (Optional)

```bash
cd gui
npm install
```

## 📖 Usage

### Start the Backend API

```bash
cd web_service
python main.py
# Or with uvicorn directly:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Start the Frontend GUI

```bash
cd gui
npm run dev
```

Open `http://localhost:3000` in your browser.

### CLI Inference (Direct Model Usage)

```bash
cd infra

# Process a single image
python main.py --source path/to/image.jpg --out tmp/result.jpg

# Process video
python main.py --source path/to/video.mp4 --out-dir ./frames

# Use webcam
python main.py --source 0 --out tmp/latest.jpg

# RTSP stream
python main.py --source rtsp://... --out tmp/latest.jpg
```

#### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--weights` | `weights/yolov11n_ncnn_model` | Path to model weights |
| `--source` | `dataset/test/images` | Input source (file/camera/stream) |
| `--out` | `tmp/latest.jpg` | Output file (overwritten continuously) |
| `--out-dir` | None | Directory for numbered frame output |
| `--conf` | 0.25 | Confidence threshold |
| `--device` | `cpu` | Device (`cpu` or `cuda:0`) |
| `--save-every` | 1 | Save every N frames |
| `--max-frames` | 0 | Max frames (0 = infinite) |

## 📚 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/count` | Count people from file path/URL |
| `POST` | `/api/v1/count/upload` | Count people from uploaded image |
| `POST` | `/api/v1/count/base64` | Count people from base64 image |
| `GET` | `/api/v1/result/{filename}` | Get annotated result image |

### Example Request

```bash
# Upload an image
curl -X POST "http://localhost:8000/api/v1/count/upload" \
  -F "file=@image.jpg" \
  -F "conf=0.25"
```

### Example Response

```json
{
  "success": true,
  "people_count": 5,
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.92,
      "bbox": [100, 150, 250, 450]
    }
  ],
  "output_image_path": "/path/to/result.jpg"
}
```

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📊 Dataset

The model is trained on a custom people counting dataset from Roboflow:

- **Classes**: 1 (`people`)
- **Source**: [Roboflow Universe](https://universe.roboflow.com/chris-3k2jo/people_counting-lqqio/dataset/3)
- **License**: CC BY 4.0

## 🛠 Technologies

### Backend
- **FastAPI** - Modern Python web framework
- **Ultralytics** - YOLOv11 implementation
- **OpenCV** - Image processing
- **Pydantic** - Data validation

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS
- **Axios** - HTTP client

### ML/AI
- **YOLOv11** - State-of-the-art object detection
- **NCNN** - Optimized inference for edge devices

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Chi Phung** - [GitHub](https://github.com/chisphung)

## 🙏 Acknowledgments

- [Ultralytics](https://ultralytics.com/) for YOLOv11
- [Roboflow](https://roboflow.com/) for dataset hosting
- [Vercel](https://vercel.com/) for Next.js

---

<p align="center">
  Made with ❤️ for CE224.Q11
</p>
