import asyncio
import json
import os
import shutil
from modules.brain import ContentBrain
from modules.asset_manager import AssetManager
from modules.audio import AudioEngine
from modules.rvc_converter import RVCConverter
from modules.composer import Composer


def clean_cache():
    print("🧹 Cleaning up temporary files...")
    folders_to_clean = [
        os.path.join(os.getcwd(), "assets", "audio_clips"),
        os.path.join(os.getcwd(), "assets", "video_clips"),
        os.path.join(os.getcwd(), "assets", "temp")
    ]

    for folder in folders_to_clean:
        if not os.path.exists(folder) or "assets" not in folder:
            continue
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"❌ Failed to delete {file_path}. Reason: {e}")
    print("✨ Workspace clean!")


async def main():
    print("🚀 STARTING AUTOMATION...")

    # 1. BRAIN: Get Topic & Script
    brain = ContentBrain()
    try:
        topic = brain.get_trending_topic()
        scenes = brain.generate_script(topic)
        metadata = brain.generate_metadata(topic, scenes)
    except Exception as e:
        print(f"❌ Brain Error: {e}")
        return

    if not scenes:
        print("❌ Script generation failed.")
        return

    # script.json ve metadata.json kaydet
    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=4)

    metadata_path = os.path.join(os.getcwd(), "assets", "final", "metadata.json")
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    print(f"📝 Metadata saved to {metadata_path}")

    # 2. AUDIO: Generate Original TTS Voice + Word Timestamps (subtitle kaynağı)
    audio_engine = AudioEngine()
    try:
        scenes = await audio_engine.process_script(scenes)
    except Exception as e:
        print(f"❌ Audio Error: {e}")
        return

    # 2.5 RVC: Orijinal TTS sesini hedef sese dönüştür.
    # ÖNEMLİ: word_timestamps (altyazı verisi) zaten yukarıda, orijinal TTS'ten
    # çıkarıldı ve scene dict'inde saklı. RVC sadece ses dosyasını değiştirir,
    # altyazı verisine hiç dokunmaz - RVC sonrası tekrar transcription YAPILMAZ.
    print("🎭 Starting RVC Voice Conversion...")
    try:
        rvc = RVCConverter()
        for scene in scenes:
            original_path = scene.get('audio_path')
            if not original_path or not os.path.exists(original_path):
                print(f"   ⚠️ Scene {scene['id']}: audio_path yok, RVC atlanıyor.")
                continue

            converted_path = os.path.splitext(original_path)[0] + "_rvc.wav"
            try:
                rvc.convert(original_path, converted_path)
                scene['audio_path'] = converted_path
                print(f"   ✅ Scene {scene['id']}: RVC dönüşümü tamamlandı.")
            except Exception as scene_err:
                print(f"   ⚠️ Scene {scene['id']}: RVC dönüşümü başarısız, orijinal TTS sesi kullanılacak. Hata: {scene_err}")
                # scene['audio_path'] orijinal kalır, pipeline durmaz
    except Exception as e:
        print(f"⚠️ RVC Converter başlatılamadı, tüm sahneler orijinal TTS sesiyle devam edecek: {e}")

    # 3. ASSETS: Get Stock Video
    asset_manager = AssetManager()
    assets_map = asset_manager.get_videos(scenes)

    # 4. COMPOSER: Merge Video + (RVC) Audio + High-Quality Captions
    # composer.py hiç değişmedi - scene['audio_path'] ve scene['word_timestamps']
    # okuyor, hangisinin RVC'den geldiği onun için önemli değil.
    composer = Composer()
    final_scene_paths = composer.render_all_scenes(scenes, assets_map)

    # 5. STITCH WITH TRANSITIONS
    if final_scene_paths:
        composer.concatenate_with_transitions(final_scene_paths)
        clean_cache()
    else:
        print("❌ Failed to generate any scenes.")


if __name__ == "__main__":
    asyncio.run(main())
    
