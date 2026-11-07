import argparse
from pathlib import Path
import tempfile

from app.config import Config
from app.server import App, serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the local FirstVisit application")
    parser.add_argument("--preview", action="store_true", help="Use an unlocked disposable test vault on port 8767; synthetic data only")
    args = parser.parse_args()
    if args.preview:
        with tempfile.TemporaryDirectory(prefix="firstvisit-preview-") as folder:
            config = Config()
            config.store_path = Path(folder) / "preview.fv"
            config.port = 8767
            config.exa_key = config.tavily_key = ""
            app = App(config)
            app.preview_mode = True
            app.store.create("firstvisit-preview-only")
            print("Disposable test preview. Synthetic data only. Unlock phrase: firstvisit-preview-only", flush=True)
            serve(app)
    else:
        serve()
