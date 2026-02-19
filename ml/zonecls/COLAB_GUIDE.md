# ZoneCls Colab Guide

## Goal
Train Zone Occupancy Classifier (v1 day model) using Google Colab GPU, export ONNX, and deploy to CamPark.

## Prerequisites
- GitHub repo access
- Dataset in Google Drive:
  - dataset_zonecls_v1/train/occupied/
  - dataset_zonecls_v1/train/empty/
  - dataset_zonecls_v1/val/occupied/
  - dataset_zonecls_v1/val/empty/

## Step-by-step
1) Open Google Colab -> New Notebook
2) Enable GPU:
   Runtime -> Change runtime type -> Hardware accelerator: GPU
3) Clone repo:
   ```bash
   !git clone https://github.com/<ORG>/<REPO>.git
   %cd <REPO>
   ```
4) Install deps:
   ```bash
   !pip install -r ml/zonecls/requirements.txt
   ```
5) Mount Google Drive:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
6) Update config path:
   - Open `ml/zonecls/configs/v1.yaml`
   - Set `data.dataset_dir` to your Drive path, e.g.
     `/content/drive/MyDrive/dataset_zonecls_v1`
   - Set `data.output_dir` to something like `/content/zonecls_runs/v1`
7) Train:
   ```bash
   !python ml/zonecls/train.py --config ml/zonecls/configs/v1.yaml
   ```
8) Export ONNX:
   ```bash
   !python ml/zonecls/export_onnx.py \
     --config ml/zonecls/configs/v1.yaml \
     --checkpoint /content/zonecls_runs/v1/model_best.pt \
     --output /content/zonecls_runs/v1/zonecls.onnx
   ```
9) Download the ONNX model:
   ```python
   from google.colab import files
   files.download('/content/zonecls_runs/v1/zonecls.onnx')
   ```

## Deploy
1) Place the file at `/models/zonecls.onnx` in the worker container
2) Set env:
```
ZONECLS_MODE=onnx
ZONECLS_MODEL_PATH=/models/zonecls.onnx
ZONECLS_THRESHOLD=0.55
```
3) Restart the worker
