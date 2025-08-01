import os
import subprocess
import logging


def create_overlay(base_image_path, image_path):
    subprocess.run([
        "qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", base_image_path, image_path
    ], check=True)
    logging.debug(f"Created overlay: {image_path}")


def remove_overlay(image_path) -> bool:
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
            logging.debug(f"Removed overlay: {image_path}")
            return True

        except OSError as e:
            logging.error(f"Failed to remove overlay: {image_path}: {e}")
            return False
    else:
        logging.warning(f"Tried to remove non-existing overlay: {image_path}")
        return True
