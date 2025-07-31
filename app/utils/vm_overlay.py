import os
import subprocess


def create_overlay(base_image_path, image_path):
    subprocess.run([
        "qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", base_image_path, image_path
    ], check=True)


def remove_overlay(image_path) -> bool:
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
            return True
        except OSError as e:
            return False
    else:
        return True
