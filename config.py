import os

RVC_MODEL_PATH = os.getenv("RVC_MODEL_PATH", os.path.join(os.getcwd(), "assets", "rvc", "model.pth"))
RVC_INDEX_PATH = os.getenv("RVC_INDEX_PATH", os.path.join(os.getcwd(), "assets", "rvc", "model.index"))
RVC_DEVICE = os.getenv("RVC_DEVICE", "cpu")
RVC_F0METHOD = os.getenv("RVC_F0METHOD", "rmvpe")
RVC_PITCH = int(os.getenv("RVC_PITCH", "0"))
RVC_INDEX_RATE = float(os.getenv("RVC_INDEX_RATE", "0.5"))
