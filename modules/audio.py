import os
import asyncio
import edge_tts
import ffmpeg

class AudioEngine:
    def __init__(self, voice="tr-TR-AhmetNeural"):
        self.voice = voice
        self.output_dir = os.path.join(os.getcwd(), "assets", "audio_clips")
        self.sfx_dir = os.path.join(os.getcwd(), "assets", "sfx")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.sfx_dir, exist_ok=True)

    async def generate_audio(self, text, output_filename, is_first_scene=False, retries=3):
        output_path = os.path.join(self.output_dir, output_filename)

        for attempt in range(retries):
            try:
                # ÖNEMLİ: edge-tts artık varsayılan olarak "SentenceBoundary"
                # gönderiyor, "WordBoundary" değil (kütüphane güncellemesi).
                # Kelime bazlı zamanlama (karaoke-tarzı altyazı) için bunu
                # açıkça belirtmemiz gerekiyor.
                communicate = edge_tts.Communicate(text, self.voice, boundary="WordBoundary")
                word_timestamps = []

                with open(output_path, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            start_time = chunk["offset"] / 10000000.0
                            duration = chunk["duration"] / 10000000.0
                            word = chunk["text"]

                            word_timestamps.append({
                                "word": word,
                                "start": start_time,
                                "end": start_time + duration
                            })

                # --- HOOK SFX MİKSLEME ---
                final_audio_path = output_path
                sfx_path = os.path.join(self.sfx_dir, "hook.mp3")

                if is_first_scene and os.path.exists(sfx_path):
                    mixed_output = os.path.join(self.output_dir, f"sfx_{output_filename}")
                    try:
                        voice_in = ffmpeg.input(output_path)
                        sfx_in = ffmpeg.input(sfx_path).filter('volume', '0.4')

                        mixed = ffmpeg.filter([voice_in, sfx_in], 'amix', inputs=2, duration='first')
                        out = ffmpeg.output(mixed, mixed_output, acodec='libmp3lame')
                        out.run(overwrite_output=True, quiet=True)
                        final_audio_path = mixed_output
                    except Exception as sfx_err:
                        print(f"   ⚠️ SFX mixing failed, using plain voice: {sfx_err}")

                total_duration = word_timestamps[-1]['end'] if word_timestamps else 3.0

                return final_audio_path, total_duration, word_timestamps

            except Exception as e:
                print(f"      ⚠️ Audio Error (Attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise e

    async def process_script(self, scenes):
        print(f"🎙️ Starting Audio & Word Timestamp Generation for {len(scenes)} scenes...")

        for idx, scene in enumerate(scenes):
            scene_id = scene['id']
            text = scene['text']
            filename = f"voice_{scene_id}.mp3"
            is_first = (idx == 0)

            try:
                file_path, duration, word_timestamps = await self.generate_audio(
                    text, filename, is_first_scene=is_first
                )

                scene['audio_path'] = file_path
                scene['duration'] = duration
                scene['word_timestamps'] = word_timestamps

                print(f"   ✅ Scene {scene_id}: {duration:.2f}s generated ({len(word_timestamps)} words captured).")
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"   ❌ Skipping Scene {scene_id} due to audio error: {e}")
                continue

        return scenes
