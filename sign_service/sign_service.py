import os
import requests

# ✅ REAL working ASL alphabet image URLs from lifeprint.com
ASL_ALPHABET = {
    "a": "https://www.lifeprint.com/asl101/gifs-animated/a.gif",
    "b": "https://www.lifeprint.com/asl101/gifs-animated/b.gif",
    "c": "https://www.lifeprint.com/asl101/gifs-animated/c.gif",
    "d": "https://www.lifeprint.com/asl101/gifs-animated/d.gif",
    "e": "https://www.lifeprint.com/asl101/gifs-animated/e.gif",
    "f": "https://www.lifeprint.com/asl101/gifs-animated/f.gif",
    "g": "https://www.lifeprint.com/asl101/gifs-animated/g.gif",
    "h": "https://www.lifeprint.com/asl101/gifs-animated/h.gif",
    "i": "https://www.lifeprint.com/asl101/gifs-animated/i.gif",
    "j": "https://www.lifeprint.com/asl101/gifs-animated/j.gif",
    "k": "https://www.lifeprint.com/asl101/gifs-animated/k.gif",
    "l": "https://www.lifeprint.com/asl101/gifs-animated/l.gif",
    "m": "https://www.lifeprint.com/asl101/gifs-animated/m.gif",
    "n": "https://www.lifeprint.com/asl101/gifs-animated/n.gif",
    "o": "https://www.lifeprint.com/asl101/gifs-animated/o.gif",
    "p": "https://www.lifeprint.com/asl101/gifs-animated/p.gif",
    "q": "https://www.lifeprint.com/asl101/gifs-animated/q.gif",
    "r": "https://www.lifeprint.com/asl101/gifs-animated/r.gif",
    "s": "https://www.lifeprint.com/asl101/gifs-animated/s.gif",
    "t": "https://www.lifeprint.com/asl101/gifs-animated/t.gif",
    "u": "https://www.lifeprint.com/asl101/gifs-animated/u.gif",
    "v": "https://www.lifeprint.com/asl101/gifs-animated/v.gif",
    "w": "https://www.lifeprint.com/asl101/gifs-animated/w.gif",
    "x": "https://www.lifeprint.com/asl101/gifs-animated/x.gif",
    "y": "https://www.lifeprint.com/asl101/gifs-animated/y.gif",
    "z": "https://www.lifeprint.com/asl101/gifs-animated/z.gif",
}

def download_and_save_gif(url, save_path):
    """Download GIF and save locally so WhatsApp can serve it"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Download error: {e}")
    return False

def text_to_sign_list(text):
    
    words = text.lower().strip().split()
    all_signs = []

    for word in words:
        clean_word = word.strip(".,!?;:'\"")
        all_signs.append({"type": "spacer", "text": f"[{clean_word.upper()}]"})

        for letter in clean_word:
            if letter in ASL_ALPHABET:
                all_signs.append({
                    "type": "letter",
                    "text": letter,
                    "url": ASL_ALPHABET[letter]
                })

    return all_signs