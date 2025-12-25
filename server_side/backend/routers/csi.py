"""
CSI (Channel State Information) router for people counting.

Handles CSI data collection, storage, and provides endpoints for ML training.
"""

import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Storage paths
CSI_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "infra",
    "csi_data"
)

# Ensure directory exists
os.makedirs(CSI_DATA_DIR, exist_ok=True)

# In-memory buffer for recent CSI data
_csi_buffer: List[dict] = []
MAX_BUFFER_SIZE = 1000

# Training data file
TRAINING_DATA_FILE = os.path.join(CSI_DATA_DIR, "training_data.jsonl")


class CSIDataRequest(BaseModel):
    """Request model for receiving CSI data from edge device."""
    timestamp: Optional[int] = Field(None, description="Timestamp from ESP32")
    rssi: int = Field(..., description="RSSI value")
    amplitudes: List[int] = Field(..., description="CSI amplitude values per subcarrier")
    people_count: int = Field(..., ge=0, description="Ground truth people count from camera")
    subcarrier_count: int = Field(..., description="Number of subcarriers")


class CSIDataResponse(BaseModel):
    """Response model for CSI data submission."""
    success: bool
    message: str
    buffer_size: int


class CSIStatsResponse(BaseModel):
    """Response model for CSI statistics."""
    total_samples: int
    buffer_size: int
    unique_people_counts: dict
    avg_rssi: float
    avg_subcarriers: float


@router.post("/data", response_model=CSIDataResponse)
async def receive_csi_data(request: CSIDataRequest):
    """
    Receive CSI data from edge device.
    
    Stores data for ML training with camera-based ground truth labels.
    """
    global _csi_buffer
    
    # Create data record
    record = {
        "timestamp": datetime.now().isoformat(),
        "esp_timestamp": request.timestamp,
        "rssi": request.rssi,
        "amplitudes": request.amplitudes,
        "people_count": request.people_count,
        "subcarrier_count": request.subcarrier_count
    }
    
    # Add to buffer
    _csi_buffer.append(record)
    
    # Trim buffer if too large
    if len(_csi_buffer) > MAX_BUFFER_SIZE:
        _csi_buffer = _csi_buffer[-MAX_BUFFER_SIZE:]
    
    # Append to training data file
    try:
        with open(TRAINING_DATA_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
    except IOError as e:
        print(f"[CSI] Failed to write training data: {e}")
    
    return CSIDataResponse(
        success=True,
        message=f"Received CSI data with {request.subcarrier_count} subcarriers",
        buffer_size=len(_csi_buffer)
    )


@router.get("/stats", response_model=CSIStatsResponse)
async def get_csi_stats():
    """
    Get statistics about collected CSI data.
    """
    if not _csi_buffer:
        return CSIStatsResponse(
            total_samples=0,
            buffer_size=0,
            unique_people_counts={},
            avg_rssi=0,
            avg_subcarriers=0
        )
    
    # Count samples per people count
    people_counts = {}
    total_rssi = 0
    total_subcarriers = 0
    
    for record in _csi_buffer:
        count = record.get("people_count", 0)
        people_counts[count] = people_counts.get(count, 0) + 1
        total_rssi += record.get("rssi", 0)
        total_subcarriers += record.get("subcarrier_count", 0)
    
    # Count total samples in file
    total_samples = 0
    if os.path.exists(TRAINING_DATA_FILE):
        with open(TRAINING_DATA_FILE, "r") as f:
            total_samples = sum(1 for _ in f)
    
    return CSIStatsResponse(
        total_samples=total_samples,
        buffer_size=len(_csi_buffer),
        unique_people_counts={str(k): v for k, v in sorted(people_counts.items())},
        avg_rssi=total_rssi / len(_csi_buffer),
        avg_subcarriers=total_subcarriers / len(_csi_buffer)
    )


@router.get("/buffer")
async def get_csi_buffer(limit: int = 100):
    """
    Get recent CSI data from buffer.
    
    Args:
        limit: Maximum number of records to return
    """
    return {
        "success": True,
        "data": _csi_buffer[-limit:],
        "total_in_buffer": len(_csi_buffer)
    }


@router.delete("/buffer")
async def clear_csi_buffer():
    """
    Clear the CSI data buffer.
    """
    global _csi_buffer
    count = len(_csi_buffer)
    _csi_buffer = []
    
    return {
        "success": True,
        "message": f"Cleared {count} records from buffer"
    }


@router.get("/training-data")
async def get_training_data_info():
    """
    Get information about the training data file.
    """
    if not os.path.exists(TRAINING_DATA_FILE):
        return {
            "success": True,
            "exists": False,
            "path": TRAINING_DATA_FILE,
            "samples": 0,
            "size_bytes": 0
        }
    
    sample_count = 0
    with open(TRAINING_DATA_FILE, "r") as f:
        sample_count = sum(1 for _ in f)
    
    return {
        "success": True,
        "exists": True,
        "path": TRAINING_DATA_FILE,
        "samples": sample_count,
        "size_bytes": os.path.getsize(TRAINING_DATA_FILE)
    }


@router.post("/training-data/start-collection")
async def start_collection(label: int = 0):
    """
    Start a new data collection session with a specific label.
    
    Args:
        label: Number of people in the room (ground truth)
    """
    return {
        "success": True,
        "message": f"Collection started with label: {label} people",
        "instructions": [
            "1. Position people in the room",
            "2. Wait for 30-60 seconds to collect samples",
            "3. Call /csi/training-data to check sample count",
            "4. Repeat with different people counts"
        ]
    }
