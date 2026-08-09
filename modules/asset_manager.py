import os
import requests
from dotenv import load_dotenv

load_dotenv()

class AssetManager:
    def __init__(self):
        self.api_key = os.getenv("PEXELS_API_KEY")
        self.download_dir = os.path.join(os.getcwd(), "assets", "video_clips")
        os.makedirs(self.download_dir, exist_ok=True)

    def _search_pexels(self, query):
        if not self.api_key:
            print("❌ PEXELS_API_KEY is missing!")
            return None

        headers = {"Authorization": self.api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("videos", [])
                if videos:
                    video_files = videos[0].get("video_files", [])
                    for vf in video_files:
                        if vf.get("file_type") == "video/mp4":
                            return vf.get("link")
        except Exception as e:
            print(f"⚠️ Pexels search error for '{query}': {e}")

        return None

    def _download_file(self, url, filename):
        path = os.path.join(self.download_dir, filename)
        if os.path.exists(path):
            return path

        try:
            res = requests.get(url, stream=True, timeout=20)
            if res.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                return path
        except Exception as e:
            print(f"❌ Download error ({filename}): {e}")

        return None

    def get_videos(self, scenes):
        print(f"🎞️ Sourcing videos for {len(scenes)} scenes...")
        video_pairs = []

        for scene in scenes:
            scene_id = scene['id']
            q1 = scene.get('visual_1', 'luxury car')
            q2 = scene.get('visual_2', 'supercar driving')

            print(f"   🔍 Scene {scene_id} Search: A='{q1}' | B='{q2}'")

            url1 = self._search_pexels(q1)
            url2 = self._search_pexels(q2)

            file1 = self._download_file(url1, f"scene_{scene_id}_a.mp4") if url1 else None
            file2 = self._download_file(url2, f"scene_{scene_id}_b.mp4") if url2 else None

            if file1 and not file2:
                file2 = file1
            elif file2 and not file1:
                file1 = file2

            if file1 and file2:
                video_pairs.append((file1, file2))
            else:
                print(f"⚠️ Could not find videos for scene {scene_id}")
                video_pairs.append(None)

        return video_pairs
