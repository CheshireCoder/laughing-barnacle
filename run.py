import os
import requests

from requests.exceptions import RequestException


class DownloadFailed(Exception):
    pass


def _download_video(src, local_path):
    file_tmp = local_path + ".tmp"
    res = requests.get(src, stream=True, timeout = 10)
    size = 0
    with open(file_tmp, "wb") as dst:
        for chnk in res.iter_content(chunk_size=4096):
            dst.write(chnk)
            size += len(chnk)
    os.rename(file_tmp, local_path)
    return size


def download_video(url, local_path, retries = 5):
    if os.path.exists(local_path):
        return -1
    else:
        for _ in range(retries):
            try:
                return _download_video(url, local_path)
            except RequestException as e:
                print("Failed {}".format(e))
    raise DownloadFailed("")

#
# def _upload_video(src, dst):
#