import os, json, tempfile, shutil, requests, re
from datetime import datetime
import numpy as np
import PIL.Image
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

# YouTube API Libraries
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

# 🔥 PILLOW 10 COMPATIBILITY
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, ColorClip

# ───────────────── CONFIG ─────────────────
PEXELS_API_KEY = "Oszdsq7V3DU1S8t1n6coHlHHeHb76cxZjb1HRYYvru32CpQYSmrO52ax"
WIDTH, HEIGHT = 1080, 1920
OUTPUT_DIR = "daily_outputs"
DATA_FILE = "viral_library.json"
ASSETS_DIR = "assets_cache"
YOUTUBE_SECRETS = "client_secrets.json" # Your downloaded OAuth file

for d in [OUTPUT_DIR, ASSETS_DIR]: os.makedirs(d, exist_ok=True)

# ───────────────── YOUTUBE UPLOADER ─────────────────
def upload_to_youtube(file_path, title, description):
    """Handles OAuth2 and uploads video as a YouTube Short."""
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    
    # Authenticate
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(YOUTUBE_SECRETS, scopes)
    credentials = flow.run_local_server(port=0)
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    request_body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": ["Shorts", "Viral", "TrendWave", "Mystery"],
            "categoryId": "27" # Education category
        },
        "status": {
            "privacyStatus": "public", # Change to "private" or "unlisted" for testing
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    print(f"🚀 Uploading to YouTube: {title}...")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"🔼 Uploading... {int(status.progress() * 100)}%")
    
    print(f"✅ Successfully Uploaded! Video ID: {response['id']}")

# ───────────────── ASSET & TEXT ENGINES (Same as v13) ─────────────────
def fetch_asset(keyword):
    headers = {"Authorization": PEXELS_API_KEY}
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', keyword)[:20]
    save_path = os.path.join(ASSETS_DIR, f"{clean_name}.mp4")
    if os.path.exists(save_path): return save_path, "video"
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page=1"
    try:
        r = requests.get(url, headers=headers, timeout=15).json()
        if r.get('videos'):
            v_url = r['videos'][0]['video_files'][0]['link']
            with requests.get(v_url, stream=True) as s, open(save_path, 'wb') as f:
                shutil.copyfileobj(s.raw, f)
            return save_path, "video"
    except: pass
    return None, None

def bake_cinematic_text(frame, main_text, is_final=False):
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    try:
        font_main = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 80)
        font_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 50)
    except:
        font_main = font_sub = ImageFont.load_default()
    if not is_final:
        draw.text((WIDTH//2, HEIGHT-250), "🔔 SUBSCRIBE TO TRENDWAVE", font=font_sub, fill=(255, 255, 255, 200), anchor="ms", stroke_width=2, stroke_fill="black")
    words = main_text.split()
    lines, curr = [], ""
    for w in words:
        if draw.textlength(curr + " " + w, font=font_main) < WIDTH - 250: curr += " " + w
        else: lines.append(curr.strip()); curr = w
    lines.append(curr.strip())
    box_h = (len(lines) * 110) + 80
    box_y = (HEIGHT // 2) + 150 
    draw.rectangle([80, box_y, WIDTH-80, box_y + box_h], fill=(0, 0, 0, 180))
    current_y = box_y + 40
    for line in lines:
        draw.text((WIDTH//2, current_y), line, font=font_main, fill="white", anchor="mt", stroke_width=3, stroke_fill="black")
        current_y += line_height if 'line_height' in locals() else 110
    return np.array(Image.alpha_composite(img, overlay).convert("RGB"))

# ───────────────── MAIN LOOP ─────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    todays_topics = [t for t in data["trending_topics"] if t.get("date") == today]
    
    for topic in todays_topics:
        clips = []
        print(f"🎬 Creating: {topic['title']}")
        for i, scene in enumerate(topic["scenes"]):
            is_last = (i == len(topic["scenes"]) - 1)
            path, _ = fetch_asset(scene['search'])
            voice_p = os.path.join(tempfile.gettempdir(), f"voice_{i}.mp3")
            gTTS(text=scene['text'], lang='en').save(voice_p)
            audio = AudioFileClip(voice_p)
            dur = audio.duration + 0.8
            c = VideoFileClip(path).without_audio().resize(height=HEIGHT) if path else ColorClip((WIDTH, HEIGHT), color=(25,25,45))
            if hasattr(c, 'w') and c.w > WIDTH: c = c.crop(x_center=c.w/2, width=WIDTH)
            c = c.set_duration(dur).set_audio(audio).fl_image(lambda f, txt=scene['text'], last=is_last: bake_cinematic_text(f, txt, last))
            clips.append(c)

        if clips:
            clean_title = re.sub(r'[:?/*"<>|]', '', topic['title'])
            safe_filename = f"{today}_{clean_title.replace(' ', '_')}.mp4"
            out_file = os.path.join(OUTPUT_DIR, safe_filename)
            final_video = concatenate_videoclips(clips, method="compose")
            final_video.write_videofile(out_file, fps=24, codec="libx264")
            
            # --- UPLOAD SECTION ---
            choice = input(f"🚀 Video {safe_filename} is ready. Upload now? (y/n): ").lower()
            if choice == 'y':
                desc = f"{topic['title']}\n\nJoin TrendWave for daily mysteries and tech updates! #Shorts #Viral"
                upload_to_youtube(out_file, topic['title'], desc)
            
            final_video.close()

if __name__ == "__main__":
    main()
