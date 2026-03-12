import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.ps_crm.osint.local_filter_model import (  # noqa: E402
    MODEL_PATH,
    get_model_metadata,
    train_and_save_local_filter_model,
)


def main() -> None:
    bundle = train_and_save_local_filter_model(force_retrain=True)
    metrics = bundle.get("metrics", {})

    print("Local news filter model trained successfully.")
    print(f"Model path: {MODEL_PATH}")
    print("Metrics:")
    print(json.dumps(metrics, indent=2))

    # Verify load path and metadata consistency
    print("Loaded metadata:")
    print(json.dumps(get_model_metadata(), indent=2))


if __name__ == "__main__":
    main()
