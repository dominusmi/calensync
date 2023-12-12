import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path


def zip_directory(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname=os.path.join("python", arcname))


if __name__ == "__main__":
    root_dir = Path(__file__).expanduser().resolve().parent.parent

    layer_dir = root_dir.joinpath("layer")

    # reset
    if layer_dir.exists():
        shutil.rmtree(layer_dir)
    layer_dir.mkdir()

    subprocess.run("docker build -t calensync_python_builder . ", cwd=root_dir.joinpath("docker"), shell=True)
    subprocess.run(f"docker run --rm -v {root_dir}/layer:/opt/tmp calensync_python_builder",
                   shell=True)

    subprocess.run(f"rsync -av --exclude='tests/' {root_dir}/lib/calensync {root_dir}/awslambda/daily_sync", shell=True)
    subprocess.run(f"rsync -av --exclude='tests/' {root_dir}/lib/calensync {root_dir}/api/src/", shell=True)
