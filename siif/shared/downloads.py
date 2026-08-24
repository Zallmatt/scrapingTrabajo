"""Utilidades de descarga compartidas entre reportes SIIF."""
import glob
import os
import time

from shared.chrome import get_staging_dir


def clear_staging():
    for path in glob.glob(os.path.join(get_staging_dir(), "*.xls*")):
        try:
            os.remove(path)
        except OSError:
            pass


def wait_for_staging_download(timeout=90):
    staging = get_staging_dir()
    end = time.time() + timeout
    while time.time() < end:
        pending = glob.glob(os.path.join(staging, "*.crdownload"))
        done = glob.glob(os.path.join(staging, "*.xls*"))
        if not pending and done:
            return True
        time.sleep(1)
    return False


def latest_staging_file():
    files = glob.glob(os.path.join(get_staging_dir(), "*.xls*"))
    if not files:
        return None
    return max(files, key=os.path.getctime)
