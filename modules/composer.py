import os
import random
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, vfx
from modules.subtitle_generator import MoviePySubtitleGenerator

class Composer:
    def __init__(self):
        self.temp_dir = os.path.join(os.getcwd(), "assets", "temp")
        self.final_dir = os.path.join(os.getcwd(), "assets", "final")

        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.final_dir, exist_ok=True)
        self.transitions = ['fade']

        # Final render'a kadar açık tutulması gereken kaynaklar (VideoFileClip,
        # AudioFileClip vb.). Sahneleri artık tek tek diske yazıp kapatmıyoruz -
        # hepsini bellekte tutup TEK seferde final videoyu render ediyoruz.
        # Bu hem çifte sıkıştırmayı (kalite kaybı) önlüyor hem de ara
        # dosyaların yeniden okunmasından kaynaklanan senkron sorunlarını azaltıyor.
        self._open_resources = []

    def _ensure_min_duration(self, clip, min_duration):
        """
        Kaynak video, ihtiyacımız olan süreden kısaysa MoviePy'nin vfx.loop
        ile baştan tekrar oynatarak süreyi doldurur. Bunu yapmazsak
        set_duration() son kareyi dondurup videoyu 'takılı' gösterir.
        """
        if clip.duration < min_duration:
            clip = clip.fx(vfx.loop, duration=min_duration)
        return clip

    def process_scene(self, scene, video_pair):
        """
        Sahneyi işler ve render EDİLMEMİŞ bir MoviePy klip objesi döndürür
        (artık dosyaya yazmıyor - bkz. concatenate_with_transitions).
        """
        scene_id = scene['id']
        audio_path = scene['audio_path']
        total_duration = scene['duration']
        word_timestamps = scene.get('word_timestamps', [])

        print(f"   🔤 Scene {scene_id}: {len(word_timestamps)} word_timestamps received.")

        try:
            print(f"   ⚙️ Processing Scene {scene_id} with MoviePy...")
            path_a, path_b = video_pair

            clip_a = VideoFileClip(path_a).resize(height=1920)
            if clip_a.w > 1080:
                x_center = clip_a.w / 2
                clip_a = clip_a.crop(x1=x_center - 540, x2=x_center + 540, y1=0, y2=1920)

            clip_b = VideoFileClip(path_b).resize(height=1920)
            if clip_b.w > 1080:
                x_center = clip_b.w / 2
                clip_b = clip_b.crop(x1=x_center - 540, x2=x_center + 540, y1=0, y2=1920)

            self._open_resources.append(clip_a)
            self._open_resources.append(clip_b)

            half_dur = total_duration / 2
            b_dur = half_dur + 0.5

            clip_a = self._ensure_min_duration(clip_a, half_dur)
            clip_b = self._ensure_min_duration(clip_b, b_dur)

            sub_a = clip_a.subclip(0, half_dur)
            sub_b = clip_b.subclip(0, b_dur)

            video_clips = concatenate_videoclips([sub_a, sub_b], method="compose")
            video_clips = video_clips.set_duration(total_duration)

            audio_clip = AudioFileClip(audio_path)
            self._open_resources.append(audio_clip)
            video_clips = video_clips.set_audio(audio_clip)

            subtitle_clips = [video_clips]

            if word_timestamps:
                chunk_size = 3
                chunks = [word_timestamps[i:i + chunk_size] for i in range(0, len(word_timestamps), chunk_size)]

                for chunk in chunks:
                    for i, active_w in enumerate(chunk):
                        start_t = active_w['start']
                        end_t = active_w['end']

                        if end_t <= start_t:
                            end_t = start_t + 0.2

                        img = MoviePySubtitleGenerator.create_text_clip_image(chunk, i)

                        txt_clip = (ImageClip(np.array(img))
                                    .set_start(start_t)
                                    .set_end(end_t)
                                    .set_duration(end_t - start_t))

                        subtitle_clips.append(txt_clip)
            else:
                print(f"   ⚠️ Scene {scene_id}: word_timestamps boş, altyazı eklenmeyecek.")

            final_scene = CompositeVideoClip(subtitle_clips)
            return final_scene

        except Exception as e:
            print(f"❌ MoviePy Render Fail Scene {scene_id}: {e}")
            return None

    def render_all_scenes(self, scenes, video_pairs):
        """
        Her sahne için bir MoviePy klip objesi üretir (dosyaya yazmadan).
        Dönen liste concatenate_with_transitions'a verilecek.
        """
        scene_clips = []
        for i, scene in enumerate(scenes):
            current_pair = video_pairs[i]
            if current_pair is None:
                continue
            clip = self.process_scene(scene, current_pair)
            if clip is not None:
                scene_clips.append(clip)
        return scene_clips

    def concatenate_with_transitions(self, scene_clips, output_filename="final_short.mp4"):
        """
        Tüm sahne kliplerini birleştirip TEK SEFERDE render eder.
        (Önceki versiyon her sahneyi ayrı encode edip sonra tekrar
        encode ediyordu - çifte sıkıştırma kaliteyi düşürüyordu.)
        """
        print("🎬 Stitching final video with MoviePy (single-pass render)...")
        output_path = os.path.join(self.final_dir, output_filename)

        if not scene_clips:
            return None

        try:
            final_video = concatenate_videoclips(scene_clips, method="compose")

            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                bitrate="8000k",   # Kaliteyi korumak için açık bitrate
                logger=None
            )

            final_video.close()
            for c in scene_clips:
                try:
                    c.close()
                except Exception:
                    pass
            for r in self._open_resources:
                try:
                    r.close()
                except Exception:
                    pass
            self._open_resources.clear()

            print(f"✅ FINAL VIDEO SAVED: {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ MoviePy Stitching Error: {e}")
            return None
