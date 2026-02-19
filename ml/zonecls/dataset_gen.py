import argparse
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "services" / "worker"))

from db import Camera, SessionLocal, Snapshot, Zone, ZoneEvent
from infer.zonecls.preprocess import crop_zone


def parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d")


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def label_from_state(state: str | None) -> str:
    if state in {"FULL", "PARTIAL"}:
        return "occupied"
    return "empty"


def load_snapshot_image(snapshot, image_root: Path) -> Image.Image:
    full_path = image_root / snapshot.file_path
    return Image.open(full_path).convert("RGB")


def save_crop(image: Image.Image, polygon, dest_path: Path, pad_ratio: float):
    crop, _bbox = crop_zone(image, polygon, pad_ratio)
    crop.save(dest_path)


def sample_snapshots(session, camera, start_date, end_date):
    query = session.query(Snapshot).filter(Snapshot.camera_id == camera.id)
    if start_date:
        query = query.filter(Snapshot.received_at >= start_date)
    if end_date:
        query = query.filter(Snapshot.received_at <= end_date)
    return query.order_by(Snapshot.received_at.asc()).all()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-id", help="Camera ID to filter (optional).")
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--image-root", default=os.getenv("IMAGE_ROOT", "/data/images"))
    parser.add_argument(
        "--sampling-mode",
        choices=["all", "random", "state_change", "low_confidence"],
        default="all",
    )
    parser.add_argument("--random-sample-rate", type=float, default=0.15)
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--pad-ratio", type=float, default=0.1)
    args = parser.parse_args()

    start_date = parse_date(args.start_date) if args.start_date else None
    end_date = parse_date(args.end_date) if args.end_date else None

    output_dir = Path(args.output_dir)
    image_root = Path(args.image_root)

    session = SessionLocal()
    try:
        cameras = session.query(Camera).all()
        if args.camera_id:
            cameras = [c for c in cameras if c.camera_id == args.camera_id]

        if not cameras:
            print("No cameras found for dataset generation")
            return

        saved = 0
        for camera in cameras:
            zones = session.query(Zone).filter(Zone.camera_id == camera.id).all()
            if not zones:
                continue

            if args.sampling_mode == "state_change":
                query = session.query(ZoneEvent).filter(ZoneEvent.zone_id.in_([z.id for z in zones]))
                if start_date:
                    query = query.filter(ZoneEvent.triggered_at >= start_date)
                if end_date:
                    query = query.filter(ZoneEvent.triggered_at <= end_date)
                events = query.order_by(ZoneEvent.triggered_at.asc()).all()

                train_dir = output_dir / "train"
                val_dir = output_dir / "val"
                for label in ["occupied", "empty"]:
                    ensure_dir(train_dir / label)
                    ensure_dir(val_dir / label)

                for event in events:
                    snapshot = session.query(Snapshot).filter(Snapshot.id == event.snapshot_id).first()
                    zone = next((z for z in zones if z.id == event.zone_id), None)
                    if not snapshot or not zone:
                        continue

                    image = load_snapshot_image(snapshot, image_root)
                    polygon = json.loads(zone.polygon_json)
                    label = label_from_state(event.new_state)
                    split_dir = train_dir if random.random() < args.train_split else val_dir

                    filename = f"{camera.camera_id}_{zone.zone_id}_{snapshot.id}.jpg"
                    dest = split_dir / label / filename
                    save_crop(image, polygon, dest, args.pad_ratio)
                    saved += 1
            else:
                unlabeled_dir = output_dir / "unlabeled"
                ensure_dir(unlabeled_dir)
                snapshots = sample_snapshots(session, camera, start_date, end_date)

                for snapshot in snapshots:
                    if args.sampling_mode == "random" and random.random() > args.random_sample_rate:
                        continue

                    if args.sampling_mode == "low_confidence":
                        if random.random() > args.random_sample_rate:
                            continue

                    image = load_snapshot_image(snapshot, image_root)
                    for zone in zones:
                        polygon = json.loads(zone.polygon_json)
                        filename = f"{camera.camera_id}_{zone.zone_id}_{snapshot.id}.jpg"
                        dest = unlabeled_dir / filename
                        save_crop(image, polygon, dest, args.pad_ratio)
                        saved += 1

        print(f"Saved {saved} crops to {output_dir}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
