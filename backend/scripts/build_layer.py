import os
import shutil
import subprocess
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

    print("Installing dependencies")
    subprocess.run(f"pip3 install -r api/requirements.txt -t {layer_dir.absolute()}", cwd=root_dir, shell=True)
    subprocess.run(f"pip3 install . -t {layer_dir.absolute()}", cwd=root_dir.joinpath("lib"), shell=True)

    print("Zipping")
    zip_directory(layer_dir, root_dir.joinpath("layer.zip"))

    # make sure to have AWS credentials in global env
    # print("Saving to S3")
    # key = f"s3://calensync/deployment/layer_{datetime.datetime.now().isoformat()}.zip"
    # subprocess.run(f"aws s3 cp layer.zip {key}", cwd=root_dir, shell=True)
    # subprocess.run(f"aws s3 cp {key} s3://calensync/deployment/layer.zip", cwd=root_dir, shell=True)
