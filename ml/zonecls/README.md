# Zone Occupancy Classifier (ZoneCls)

This folder contains the training + dataset utilities for the zone occupancy classifier.

## Dataset format
```
dataset_zonecls_v1/
  train/
    occupied/
    empty/
  val/
    occupied/
    empty/
```

If you do not have labels yet, the generator can output crops into `unlabeled/` for manual sorting.

## Dataset generation
Example (state changes only, labeled):
```bash
python ml/zonecls/dataset_gen.py \
  --camera-id cam001 \
  --start-date 2026-02-01 \
  --end-date 2026-02-08 \
  --output-dir /data/datasets/dataset_zonecls_v1 \
  --sampling-mode state_change
```

Example (unlabeled random sampling):
```bash
python ml/zonecls/dataset_gen.py \
  --output-dir /data/datasets/dataset_zonecls_v1 \
  --sampling-mode random \
  --random-sample-rate 0.1
```

## Training
Install requirements:
```bash
pip install -r ml/zonecls/requirements.txt
```

Run training:
```bash
python ml/zonecls/train.py --config ml/zonecls/configs/v1.yaml
```

## Export to ONNX
```bash
python ml/zonecls/export_onnx.py \
  --config ml/zonecls/configs/v1.yaml \
  --checkpoint /path/to/model_best.pt \
  --output /path/to/zonecls.onnx
```

## Production usage
Copy the ONNX file into the worker container at `/models/zonecls.onnx` and set:
```
ZONECLS_MODE=onnx
ZONECLS_MODEL_PATH=/models/zonecls.onnx
ZONECLS_THRESHOLD=0.55
```
