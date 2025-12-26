# CE224.Q11 - People Counting System

A real-time people counting application powered by YOLOv11 and WiFi CSI (Channel State Information), featuring ESP32-CAM integration, edge computing with WebSocket streaming, FastAPI backend, and Next.js frontend with live bounding box visualization.

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
- [CSI People Counting](#-csi-people-counting)
- [API Documentation](#-api-documentation)
- [Dataset](#-dataset)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Real-time People Detection**: Utilizes YOLOv11 for accurate people counting
- **WiFi CSI Sensing**: Non-visual human detection using WiFi signal variations
- **Multi-Modal Fusion**: Combines camera and CSI for improved accuracy
- **ESP32-CAM Integration**: Wireless camera streaming via WebSocket
- **Edge Computing**: On-device YOLO inference for low-latency processing
- **Live Video Streaming**: Real-time annotated video feed with bounding boxes
- **ML Model Training**: Train custom CSI models for people counting
- **Web Interface**: Modern, responsive UI built with Next.js and Tailwind CSS
- **RESTful API**: FastAPI backend with automatic OpenAPI documentation
- **NCNN Model Support**: Optimized model for CPU inference on edge devices

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│   ESP32-CAM     │────▶│  Edge Device    │────▶│  FastAPI Server │────▶│  Next.js GUI    │
│  Camera + CSI   │     │  (YOLO Infer)   │     │  (Port 8000)    │     │  (Port 3000)    │
│   Port 8080     │     │  ws_server.py   │     │                 │     │                 │
│                 │     │                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                       │
                                │                       ▼
                                │               ┌─────────────────┐
                                └──────────────▶│  CSI Training   │
                                  CSI Data      │  (ML Models)    │
                                                └─────────────────┘
```

### Data Flow

1. **ESP32-CAM** captures JPEG frames + CSI data, sends via WebSocket
2. **Edge Device** (`ws_server.py`) receives frames, runs YOLOv11, forwards CSI
3. **Server** stores CSI data for training, serves results to frontend
4. **Frontend** displays live video stream with real-time counting

## 📁 Project Structure

```
CE224.Q11_People_Counting/
├── edge_side/
│   ├── camera/                    # ESP32-CAM Firmware
│   │   ├── main/
│   │   │   ├── main.c            # Camera + CSI capture & WebSocket
│   │   │   └── camera_pins.h     # Hardware pin definitions
│   │   ├── sdkconfig             # CSI enabled configuration
│   │   └── CMakeLists.txt
│   │
│   └── infra/                     # Edge ML Infrastructure
│       ├── ws_server.py          # WebSocket server + YOLO inference
│       ├── train_csi_model.py    # CSI ML model training script
│       ├── main.py               # CLI inference script
│       ├── weights/              # Model weights
│       │   └── yolov11n_ncnn_model/
│       ├── csi_data/             # CSI training data
│       │   └── training_data.jsonl
│       └── tmp/                  # Temporary output
│
├── server_side/
│   ├── backend/                   # FastAPI Backend
│   │   ├── main.py               # Application entry
│   │   ├── routers/
│   │   │   ├── count_people.py   # Camera counting endpoints
│   │   │   └── csi.py            # CSI data endpoints
│   │   └── schema/               # Pydantic models
│   │
│   └── frontend/                  # Next.js Frontend
│       ├── src/
│       │   ├── app/
│       │   │   └── page.tsx      # Main page with live stream
│       │   ├── components/
│       │   │   ├── LiveVideoStream.tsx
│       │   │   ├── BoundingBoxCanvas.tsx
│       │   │   └── ...
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
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 3. Set Up Frontend

```bash
cd server_side/frontend
npm install
```

### 4. Set Up ESP32-CAM

#### 4.1 Configure Wi-Fi and Server

Edit `edge_side/camera/main/main.c` and update these defines:

```c
#define WIFI_SSID "your_wifi_name"      // Your Wi-Fi network name
#define WIFI_PASS "your_wifi_password"  // Your Wi-Fi password
#define SERVER_URI "ws://192.168.x.x:8080"  // WebSocket server IP
```

> **Important**: The `SERVER_URI` must point to the IP address of the machine running `ws_server.py` on the **same network** as the ESP32-CAM.

To find your server IP:

```bash
# Linux/Mac
ip addr | grep "inet " | grep -v 127.0.0.1
# or
hostname -I
```

#### 4.2 Build and Flash

**Option A: Using Docker (Recommended)**

```bash
cd edge_side/camera

# Build
docker run --rm -v $PWD:/project -w /project espressif/idf:v5.3 idf.py build

# Flash (connect ESP32-CAM via USB, hold BOOT button during connection)
docker run --rm -v $PWD:/project -w /project \
  --device=/dev/ttyUSB0 --privileged \
  espressif/idf:v5.3 idf.py -p /dev/ttyUSB0 flash

# Monitor serial output
docker run --rm -v $PWD:/project -w /project \
  --device=/dev/ttyUSB0 --privileged -it \
  espressif/idf:v5.3 idf.py -p /dev/ttyUSB0 monitor
```

**Option B: Native ESP-IDF**

```bash
cd edge_side/camera
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

#### 4.3 Troubleshooting

| Issue                                                 | Solution                                                             |
| ----------------------------------------------------- | -------------------------------------------------------------------- |
| `Failed to connect to ESP32: No serial data received` | Hold **BOOT** button while connecting, or during flash command       |
| `Connection reset by peer` on WebSocket               | Ensure `ws_server.py` is running on the server before powering ESP32 |
| ESP32 connects to wrong network                       | Verify `WIFI_SSID` and `WIFI_PASS` match exactly (case-sensitive)    |
| WebSocket timeout                                     | Check firewall: `sudo ufw allow 8080/tcp`                            |

## 📖 Usage

### Option 1: Full Pipeline (ESP32-CAM → Edge → Server → Frontend)

```bash
# Terminal 1: Start the backend server
cd server_side/backend
python main.py

# Terminal 2: Start the edge WebSocket server
cd edge_side/infra
python ws_server.py --display  # --display for local preview

# Terminal 3: Start the frontend
cd server_side/frontend
npm run dev

# Power on ESP32-CAM (connects automatically)
```

Open `http://localhost:3000` for live video stream with people counting.

### Option 2: CLI Inference

```bash
cd edge_side/infra

# Process image
python main.py --source path/to/image.jpg --out tmp/result.jpg

# Use webcam
python main.py --source 0 --out tmp/latest.jpg
```

## 📡 CSI People Counting

WiFi CSI (Channel State Information) enables non-visual human detection by analyzing WiFi signal variations caused by human presence.

### How It Works

1. **ESP32 collects CSI** data from WiFi packets
2. **Edge server forwards** CSI + camera count to backend
3. **Server stores** CSI data with camera-based labels
4. **Train ML model** to predict people count from CSI alone

### Collecting Training Data

```bash
# Start full pipeline (server + edge + ESP32)
# CSI data auto-saves to: edge_side/infra/csi_data/training_data.jsonl

# Check collection stats
curl http://localhost:8000/api/v1/csi/stats
```

### Training a CSI Model

```bash
cd edge_side/infra

# Random Forest (recommended)
python train_csi_model.py \
    --data csi_data/training_data.jsonl \
    --model rf \
    --output csi_model.pkl

# Neural Network
python train_csi_model.py --data csi_data/training_data.jsonl --model nn

# Gradient Boosting
python train_csi_model.py --data csi_data/training_data.jsonl --model gb
```

### CSI Features Extracted

| Feature      | Description                        |
| ------------ | ---------------------------------- |
| Statistical  | Mean, std, min, max, median, range |
| Quartiles    | 25th, 75th percentile              |
| Higher-order | Skewness, kurtosis                 |
| Energy       | Sum and mean of squared amplitudes |
| Variance     | Per-segment variance               |
| Frequency    | FFT-based features                 |
| RSSI         | Signal strength                    |

## 📚 API Documentation

### Camera Endpoints

| Method | Endpoint               | Description               |
| ------ | ---------------------- | ------------------------- |
| `POST` | `/api/v1/count`        | Count from file/URL       |
| `POST` | `/api/v1/count/upload` | Count from uploaded image |
| `POST` | `/api/v1/count/edge`   | Receive from edge device  |
| `GET`  | `/api/v1/count/latest` | Latest count              |
| `GET`  | `/api/v1/stream/frame` | Live frame for streaming  |

### CSI Endpoints

| Method | Endpoint                    | Description           |
| ------ | --------------------------- | --------------------- |
| `POST` | `/api/v1/csi/data`          | Receive CSI data      |
| `GET`  | `/api/v1/csi/stats`         | Collection statistics |
| `GET`  | `/api/v1/csi/buffer`        | Recent CSI samples    |
| `GET`  | `/api/v1/csi/training-data` | Training file info    |

Interactive docs: `http://localhost:8000/docs`

## 📊 Dataset

Camera model trained on custom people counting dataset from Roboflow:

- **Classes**: 1 (`people`)
- **Source**: [Roboflow Universe](https://universe.roboflow.com/chris-3k2jo/people_counting-lqqio/dataset/3)
- **License**: CC BY 4.0

## 🛠 Technologies

### Hardware

- **ESP32-CAM** - Wi-Fi camera with CSI support

### Edge Computing

- **WiFi CSI** - Channel State Information for human sensing
- **YOLOv11** - Object detection
- **NCNN** - Optimized inference

### Backend

- **FastAPI** - Python web framework
- **scikit-learn** - ML model training

### Frontend

- **Next.js 14** - React framework
- **Tailwind CSS** - Styling

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

## 👥 Authors

- **Chi Phung** - [GitHub](https://github.com/chisphung)

---

<p align="center">
  Made with ❤️ for CE224.Q11
</p>
