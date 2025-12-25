#!/usr/bin/env python3
"""
WebSocket server for ESP32 camera stream with YOLO people counting inference.

This script:
1. Receives JPEG frames from ESP32 camera via WebSocket
2. Runs YOLOv11 inference to count people
3. Sends counting results to the backend server API
4. Optionally displays the annotated frames locally

Usage:
    python ws_server.py                           # Default settings
    python ws_server.py --display                 # Show frames locally
    python ws_server.py --server http://host:8000 # Custom server URL
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import queue
import sys
import threading
import time
from contextlib import suppress
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
import requests
import websockets

# Add parent directory to access weights
sys.path.insert(0, os.path.dirname(__file__))

from ultralytics import YOLO

# Configuration
DEFAULT_WS_PORT = 8080
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_WEIGHTS = os.path.join(os.path.dirname(__file__), "weights", "yolov11n_ncnn_model")

# Global state
clients: set[websockets.WebSocketServerProtocol] = set()
frame_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=3)
stop_event = threading.Event()
latest_count: dict = {"people_count": 0, "timestamp": None, "detections": []}

# Default camera settings sent to ESP32
DEFAULT_CAMERA_SETTINGS = {
    "brightness": 1,
    "contrast": 1,
    "saturation": 1,
    "quality": 8,
}


class PeopleCounter:
    """YOLO-based people counting with result caching."""
    
    def __init__(self, weights_path: str, conf: float = 0.25, device: str = "cpu"):
        self.conf = conf
        self.device = device
        self.model: Optional[YOLO] = None
        self.weights_path = weights_path
        
    def load_model(self):
        """Lazy load the YOLO model."""
        if self.model is None:
            print(f"[Counter] Loading model from {self.weights_path}")
            self.model = YOLO(self.weights_path)
            print("[Counter] Model loaded successfully")
    
    def count(self, image: np.ndarray) -> dict:
        """
        Count people in an image.
        
        Args:
            image: BGR numpy array from cv2
            
        Returns:
            Dict with people_count, detections, and annotated_image
        """
        self.load_model()
        
        # Run inference
        results = self.model.predict(
            source=image,
            conf=self.conf,
            device=self.device,
            verbose=False
        )
        
        detections = []
        people_count = 0
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()
                    
                    # Class ID 0 is "person" in COCO dataset
                    if class_id == 0 or class_name.lower() == "person":
                        people_count += 1
                        detections.append({
                            "class_id": class_id,
                            "class_name": class_name,
                            "confidence": confidence,
                            "bbox": bbox
                        })
        
        # Get annotated image
        annotated_image = results[0].plot() if results else image
        
        return {
            "people_count": people_count,
            "detections": detections,
            "annotated_image": annotated_image,
            "timestamp": datetime.now().isoformat()
        }


def display_loop(window_title: str = "ESP32 Stream - People Counting") -> None:
    """Render frames in a background thread (for debugging)."""
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    
    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        
        cv2.imshow(window_title, frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
            print("[Viewer] Escape pressed, stopping...")
            stop_event.set()
            break
    
    cv2.destroyAllWindows()


def submit_frame(frame: np.ndarray) -> None:
    """Push frame to display queue, dropping oldest if full."""
    if stop_event.is_set():
        return
    
    try:
        frame_queue.put_nowait(frame)
    except queue.Full:
        with suppress(queue.Empty):
            frame_queue.get_nowait()
        frame_queue.put_nowait(frame)


async def send_to_server(server_url: str, result: dict) -> bool:
    """Send counting result with annotated frame to the backend server."""
    endpoint = f"{server_url}/api/v1/count/edge"
    
    # Encode annotated frame as base64 JPEG
    frame_base64 = None
    if "annotated_image" in result and result["annotated_image"] is not None:
        success, buffer = cv2.imencode('.jpg', result["annotated_image"], [cv2.IMWRITE_JPEG_QUALITY, 85])
        if success:
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    payload = {
        "people_count": result["people_count"],
        "detections": result["detections"],
        "timestamp": result["timestamp"],
        "frame_base64": frame_base64
    }
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(endpoint, json=payload, timeout=5)
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"[Server] Error response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[Server] Connection error: {e}")
        return False


async def handle_client(
    ws: websockets.WebSocketServerProtocol,
    counter: PeopleCounter,
    server_url: str,
    display: bool,
    send_interval: float
) -> None:
    """Handle incoming WebSocket connection from ESP32 camera."""
    global latest_count
    
    clients.add(ws)
    peer = f"{ws.remote_address[0]}:{ws.remote_address[1]}" if ws.remote_address else "ESP32"
    print(f"[Server] {peer} connected")
    
    # Send initial camera settings
    try:
        await ws.send(json.dumps(DEFAULT_CAMERA_SETTINGS))
        print(f"[Server] Sent camera settings: {DEFAULT_CAMERA_SETTINGS}")
    except websockets.ConnectionClosed:
        print(f"[Server] {peer} disconnected before initial command")
        clients.discard(ws)
        return
    
    last_send_time = 0
    frame_count = 0
    
    try:
        async for msg in ws:
            if stop_event.is_set():
                break
            
            if isinstance(msg, (bytes, bytearray)):
                # Decode JPEG frame
                array = np.frombuffer(msg, np.uint8)
                frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    print("[Server] Dropped invalid frame")
                    continue
                
                frame_count += 1
                
                # Run inference
                result = counter.count(frame)
                latest_count = {
                    "people_count": result["people_count"],
                    "detections": result["detections"],
                    "timestamp": result["timestamp"]
                }
                
                # Display if enabled
                if display:
                    # Add count overlay
                    annotated = result["annotated_image"].copy()
                    cv2.putText(
                        annotated,
                        f"People: {result['people_count']}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2
                    )
                    submit_frame(annotated)
                
                # Send to server at interval
                current_time = time.time()
                if current_time - last_send_time >= send_interval:
                    success = await send_to_server(server_url, result)
                    if success:
                        print(f"[Server] Sent count: {result['people_count']} people (frame {frame_count})")
                    last_send_time = current_time
                    
            else:
                # Handle JSON responses from ESP32
                try:
                    response = json.loads(msg)
                    print(f"[ESP32 Response] {response}")
                except json.JSONDecodeError:
                    print(f"[ESP32 Text] {msg}")
    
    except websockets.ConnectionClosed:
        print(f"[Server] {peer} disconnected")
    finally:
        clients.discard(ws)
        print(f"[Server] Total frames processed: {frame_count}")


async def wait_for_stop() -> None:
    """Wait for stop signal."""
    while not stop_event.is_set():
        await asyncio.sleep(0.1)


async def main(args: argparse.Namespace) -> None:
    """Main entry point."""
    # Initialize counter
    counter = PeopleCounter(
        weights_path=args.weights,
        conf=args.conf,
        device=args.device
    )
    
    # Pre-load model
    counter.load_model()
    
    # Start display thread if enabled
    display_thread = None
    if args.display:
        display_thread = threading.Thread(target=display_loop, daemon=True)
        display_thread.start()
    
    # Create handler with captured args
    async def handler(ws: websockets.WebSocketServerProtocol) -> None:
        await handle_client(ws, counter, args.server, args.display, args.send_interval)
    
    # Start WebSocket server
    async with websockets.serve(handler, "0.0.0.0", args.port, max_size=None):
        print(f"[Server] WebSocket server running on ws://0.0.0.0:{args.port}")
        print(f"[Server] Sending results to {args.server}")
        print("[Server] Waiting for ESP32 camera connection...")
        
        try:
            await wait_for_stop()
        finally:
            stop_event.set()
    
    if display_thread:
        display_thread.join(timeout=1.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 Camera WebSocket Server with People Counting")
    parser.add_argument("--port", type=int, default=DEFAULT_WS_PORT,
                        help=f"WebSocket server port (default: {DEFAULT_WS_PORT})")
    parser.add_argument("--server", type=str, default=DEFAULT_SERVER_URL,
                        help=f"Backend server URL (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("--weights", type=str, default=DEFAULT_WEIGHTS,
                        help="Path to YOLO model weights")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold (default: 0.25)")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device to run inference on (default: cpu)")
    parser.add_argument("--display", action="store_true",
                        help="Display annotated frames locally")
    parser.add_argument("--send-interval", type=float, default=1.0,
                        help="Interval (seconds) between sending results to server (default: 1.0)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        stop_event.set()
        print("\n[Server] Shutting down...")
