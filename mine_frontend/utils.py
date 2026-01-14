import os

from imgproxy import ImgProxy


class MyImgProxy:
    def __init__(self, *args, **kwargs):
        self.key = os.getenv("IMGPROXY_KEY")
        self.salt = os.getenv("IMGPROXY_SALT")
        self.proxy_host = "https://imgproxy.acdh.oeaw.ac.at"

    def img_url(self, path):
        path = f"s3://for-imgproxy/{path}"
        return ImgProxy(path, proxy_host=self.proxy_host, key=self.key, salt=self.salt)

    def calc(self, path):
        return self.img_url(path)()

    def crop(self, path, width, height, x=0, y=0):
        gravity = f"nowe:{x}:{y}"
        crop = f"crop:{width}:{height}:{gravity}"
        return self.img_url(path)(crop, width=800, height=800, resizing_type="fit")

    def resize(self, path, width=150, height=200):
        return self.img_url(path)(width=width, height=height, resizing_type="fit")
