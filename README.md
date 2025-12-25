# CE224.Q11 - People Counting System

A real-time people counting application powered by YOLOv11, featuring ESP32-CAM integration, edge computing with WebSocket streaming, FastAPI backend, and Next.js frontend with live bounding box visualization.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![YOLOv11](https://img.shields.io/badge/YOLO-v11-purple)
![ESP32](https://img.shields.io/badge/ESP32-CAM-orange?logo=espressif)
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
- **ESP32-CAM Integration**: Wireless camera streaming via WebSocket
- **Edge Computing**: On-device YOLO inference for low-latency processing
- **Live Video Streaming**: Real-time annotated video feed with bounding boxes
- **Web Interface**: Modern, responsive UI built with Next.js and Tailwind CSS
- **RESTful API**: FastAPI backend with automatic OpenAPI documentation
- **Multiple Input Sources**: Support for images, video files, webcam, and RTSP streams
- **Statistics Dashboard**: Track detection history and metrics
- **NCNN Model Support**: Optimized model for CPU inference on edge devices

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│   ESP32-CAM     │────▶│  Edge Device    │────▶│  FastAPI Server │────▶│  Next.js GUI    │
│   (WebSocket)   │     │  (YOLO Infer)   │     │  (Port 8000)    │     │  (Port 3000)    │
│   Port 8080     │     │  ws_server.py   │     │                 │     │                 │
│                 │     │                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Data Flow

1. **ESP32-CAM** captures JPEG frames and sends via WebSocket to port 8080
2. **Edge Device** (`ws_server.py`) receives frames, runs YOLOv11 inference
3. **Server** receives counting results + annotated frames via REST API
4. **Frontend** polls server for live stream and displays real-time video

## 📁 Project Structure

```
CE224.Q11_People_Counting/
├── edge_side/
│   ├── camera/                    # ESP32-CAM Firmware
│   │   ├── main/
│   │   │   ├── main.c            # Camera capture & WebSocket client
│   │   │   └── camera_pins.h     # Hardware pin definitions
│   │   ├── CMakeLists.txt
│   │   └── sdkconfig
│   │
│   └── infra/                     # Edge ML Infrastructure
│       ├── ws_server.py          # WebSocket server + YOLO inference
│       ├── main.py               # CLI inference script
│       ├── weights/              # Model weights
│       │   └── yolov11n_ncnn_model/
│       ├── dataset/              # Training data
│       └── tmp/                  # Temporary output
│
├── server_side/
│   ├── backend/                   # FastAPI Backend
│   │   ├── main.py               # Application entry
│   │   ├── routers/
│   │   │   └── count_people.py   # API endpoints
│   │   └── schema/               # Pydantic models
│   │       └── count_people.py
│   │
│   └── frontend/                  # Next.js Frontend
│       ├── src/
│       │   ├── app/
│       │   │   └── page.tsx      # Main page with live stream
│       │   ├── components/
│       │   │   ├── LiveVideoStream.tsx  # Real-time video display
│       │   │   ├── BoundingBoxCanvas.tsx
│       │   │   ├── ImageUploader.tsx
│       │   │   └── StatsPanel.tsx
│       │   └── types/
│       └── package.json
│
└── requirements.txt               # Python dependencies
```

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- ESP-IDF 5.x (for ESP32-CAM firmware)
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

### 3. Set Up Frontend

```bash
cd server_side/frontend
npm install
```

### 4. Set Up ESP32-CAM (Optional)

```bash
cd edge_side/camera
# Configure Wi-Fi in main/main.c (WIFI_SSID, WIFI_PASS, SERVER_URI)
idf.py build
idf.py flash
```

## 📖 Usage

### Option 1: Full Pipeline (ESP32-CAM → Edge → Server → Frontend)

```bash
# Terminal 1: Start the backend server
cd server_side/backend
python main.py

# Terminal 2: Start the edge WebSocket server
cd edge_side/infra
python ws_server.py --display  # --display to see local preview

# Terminal 3: Start the frontend
cd server_side/frontend
npm run dev

# Power on ESP32-CAM (connects automatically)
```

Open `http://localhost:3000` to see the live video stream with people counting.

### Option 2: Backend API Only

```bash
cd server_side/backend
python main.py
# API available at http://localhost:8000
```

### Option 3: CLI Inference (No server required)

```bash
cd edge_side/infra

# Process a single image
python main.py --source path/to/image.jpg --out tmp/result.jpg

# Process video
python main.py --source path/to/video.mp4 --out-dir ./frames

# Use webcam
python main.py --source 0 --out tmp/latest.jpg
```

### Edge WebSocket Server Options

| Option            | Default                       | Description                               |
| ----------------- | ----------------------------- | ----------------------------------------- |
| `--port`          | 8080                          | WebSocket server port                     |
| `--server`        | `http://localhost:8000`       | Backend server URL                        |
| `--weights`       | `weights/yolov11n_ncnn_model` | Path to model weights                     |
| `--conf`          | 0.25                          | Confidence threshold                      |
| `--device`        | `cpu`                         | Device (`cpu` or `cuda:0`)                |
| `--display`       | False                         | Display annotated frames locally          |
| `--send-interval` | 1.0                           | Interval between server updates (seconds) |

## 📚 API Documentation

### Endpoints

| Method | Endpoint                    | Description                                     |
| ------ | --------------------------- | ----------------------------------------------- |
| `GET`  | `/`                         | API information                                 |
| `GET`  | `/health`                   | Health check                                    |
| `POST` | `/api/v1/count`             | Count people from file path/URL                 |
| `POST` | `/api/v1/count/upload`      | Count people from uploaded image                |
| `POST` | `/api/v1/count/base64`      | Count people from base64 image                  |
| `POST` | `/api/v1/count/edge`        | Receive count from edge device                  |
| `GET`  | `/api/v1/count/latest`      | Get latest count from edge                      |
| `GET`  | `/api/v1/count/history`     | Get counting history                            |
| `GET`  | `/api/v1/stream/frame`      | Get latest annotated frame (for live streaming) |
| `GET`  | `/api/v1/result/{filename}` | Get annotated result image                      |

### Example: Upload Image

```bash
curl -X POST "http://localhost:8000/api/v1/count/upload" \
  -F "file=@image.jpg" \
  -F "conf=0.25"
```

### Example: Get Live Count

```bash
curl "http://localhost:8000/api/v1/count/latest"
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
  "timestamp": "2025-12-25T10:30:00",
  "camera_id": "esp32_cam"
}
```

Interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📊 Dataset

The model is trained on a custom people counting dataset from Roboflow:

- **Classes**: 1 (`people`)
- **Source**: [Roboflow Universe](https://universe.roboflow.com/chris-3k2jo/people_counting-lqqio/dataset/3)
- **License**: CC BY 4.0

## 🛠 Technologies

### Hardware

- **ESP32-CAM** - Wi-Fi camera module with OV2640 sensor

### Edge Computing

- **ESP-IDF** - Espressif IoT Development Framework
- **WebSockets** - Real-time bidirectional communication
- **Ultralytics** - YOLOv11 implementation
- **NCNN** - Optimized inference for edge devices

### Backend

- **FastAPI** - Modern Python web framework
- **OpenCV** - Image processing
- **Pydantic** - Data validation

### Frontend

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS

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
- [Espressif](https://www.espressif.com/) for ESP32-CAM
- [Vercel](https://vercel.com/) for Next.js

---

<p align="center">
  Made with ❤️ for CE224.Q11
</p>
