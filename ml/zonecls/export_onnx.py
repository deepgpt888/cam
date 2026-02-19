import argparse
from pathlib import Path

import torch
import yaml
from torchvision import models
from torch import nn


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_model(config: dict) -> nn.Module:
    model_name = config["model"]["name"]
    num_classes = config["model"].get("num_classes", 2)

    if model_name == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=None)
        in_features = model.classifier[-1].in_features  # type: ignore[union-attr]
        model.classifier[-1] = nn.Linear(in_features, num_classes)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--checkpoint", required=True, help="Path to model_best.pt")
    parser.add_argument("--output", required=True, help="Output ONNX path")
    args = parser.parse_args()

    config = load_config(args.config)
    checkpoint = torch.load(args.checkpoint, map_location="cpu")

    model = build_model(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    input_size = config["train"]["input_size"]
    dummy = torch.randn(1, 3, input_size, input_size)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        (dummy,),
        output_path.as_posix(),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )

    print(f"Exported ONNX to {output_path}")


if __name__ == "__main__":
    main()
