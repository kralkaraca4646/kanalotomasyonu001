from rvc_python.infer import RVCInference
import config

class RVCConverter:
    def __init__(self):
        self.rvc = RVCInference(device=config.RVC_DEVICE)
        self.rvc.load_model(config.RVC_MODEL_PATH, index_path=config.RVC_INDEX_PATH)

    def convert(self, input_path, output_path):
        self.rvc.infer_file(
            input_path, output_path,
            f0method=config.RVC_F0METHOD,
            index_rate=config.RVC_INDEX_RATE,
            pitch=config.RVC_PITCH,
        )
        return output_path
