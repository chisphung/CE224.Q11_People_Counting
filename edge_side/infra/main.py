#!/usr/bin/env python3
"""
yolo_stream_save.py
Stream inference with ultralytics (YOLOv8+), save annotated frames continuously
(for headless/SSH use).

Usage examples:
  python yolo_stream_save.py --source 0 --out /tmp/latest.jpg         # camera, overwrite same file
  python yolo_stream_save.py --source rtsp://... --out /tmp/latest.jpg
  python yolo_stream_save.py --source video.mp4 --out-dir ./frames  # save numbered frames
"""

import argparse
import os
import tempfile
import time
from ultralytics import YOLO
import cv2

def atomic_write_image(path, image):
    directory, ext = os.path.split(path)[0], os.path.splitext(path)[1]
    # preserve the original extension so cv2 can pick the right codec
    fd, tmp_path = tempfile.mkstemp(dir=directory or None, suffix=ext or ".tmp")
    os.close(fd)
    # cv2.imwrite expects BGR images. ultralytics result.plot() generally returns a BGR numpy array.
    cv2.imwrite(tmp_path, image)
    os.replace(tmp_path, path)   # atomic on most Unix systems

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="weights/yolov11n_ncnn_model", help="weights (local path or model name)")
    p.add_argument("--source", default="dataset/test/images", help="camera index, video file, or stream (rtsp/http). '0' is default camera.")
    p.add_argument("--out", default="tmp/latest.jpg", help="single output file to overwrite continuously")
    p.add_argument("--out-dir", default=None, help="optional: directory to save numbered frames instead of single file")
    p.add_argument("--conf", type=float, default=0.25, help="confidence threshold")
    p.add_argument("--device", default="cpu", help="device, 'cpu' or '0' or 'cuda:0'")
    p.add_argument("--save-every", type=int, default=1, help="save every N frames (useful for high FPS sources)")
    p.add_argument("--max-frames", type=int, default=0, help="0 = infinite; otherwise stops after N frames")
    args = p.parse_args()

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    model = YOLO(args.weights)

    # stream=True yields results gradually; headless so we never call show()
    frame_count = 0
    saved_count = 0
    try:
        for result in model.predict(source=args.source, conf=args.conf, device=args.device, stream=True):
            # result.plot() returns annotated image as numpy array (BGR). This is convenient for cv2.imwrite.
            annotated = result.plot()
            frame_count += 1

            if frame_count % args.save_every != 0:
                continue

            if args.out_dir:
                fname = os.path.join(args.out_dir, f"frame_{saved_count:06d}.jpg")
                atomic_write_image(fname, annotated)
            else:
                atomic_write_image(args.out, annotated)

            saved_count += 1

            if args.max_frames and saved_count >= args.max_frames:
                print("Reached max frames, exiting.")
                break

    except KeyboardInterrupt:
        print("Interrupted by user. Exiting cleanly.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
