"""Side-by-side chart: Unicode glyph | the user's drawn compound form (cropped from the photo) | the letter rebuilt from the form library.
   python compare_letters.py devanagari"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from PIL import Image
from render_forms import draw
D = os.path.join(os.path.dirname(__file__), "..", "..", "conlang_forge", "script", "forms")
SCALE = 1 / 0.45                                   # crops below are given in a 750-wide overview of a 1666-wide photo

def build(script, crops, photos, font, out_prefix, per_img=24, cols=3):
    forms = {f["id"]: f for f in json.load(open(f"{D}/{script}.json"))["forms"]}
    L = json.load(open(f"{D}/{script}_letters.json"))["letters"]
    fp = fm.FontProperties(fname=font)
    imgs = {k: Image.open(v).convert("RGB") for k, v in photos.items()}
    for part in range(0, len(L), per_img):
        chunk = L[part:part + per_img]; rows = (len(chunk) + cols - 1) // cols
        fig, axs = plt.subplots(rows, cols * 3, figsize=(cols * 3 * 1.7, rows * 1.9))
        for ax in axs.flat: ax.axis("off")
        for i, l in enumerate(chunk):
            r, c = divmod(i, cols); a0, a1, a2 = axs[r, c * 3], axs[r, c * 3 + 1], axs[r, c * 3 + 2]
            a0.text(.5, .5, l["glyph"], fontproperties=fp, fontsize=34, ha="center", va="center"); a0.set_title(l["name"], fontsize=9)
            pg, cx, cy = crops[l["name"]]; h = 55 * SCALE
            im = imgs[pg]; a1.imshow(im.crop((int(cx * SCALE - h), int(cy * SCALE - h), int(cx * SCALE + h), int(cy * SCALE + h))))
            a1.set_title("yours", fontsize=7, color="#888")
            a2.plot([.05, .95], [1, 1], "k", lw=1.5)
            for part_ in l["parts"]:
                for s in draw(forms[part_["form"]]):
                    xs, ys = zip(*s["p"]); a2.plot([x + part_["dx"] for x in xs], [y + part_["dy"] for y in ys], "k", lw=1.5, solid_capstyle="round")
            a2.set_xlim(0, 1); a2.set_ylim(-.1, 1.1); a2.set_aspect("equal"); a2.set_title("mine", fontsize=7, color="#888")
        fig.tight_layout(); fn = f"{out_prefix}{part // per_img + 1}.png"; fig.savefig(fn, dpi=80); print(fn)

if __name__ == "__main__":
    base = glob.glob("/mnt/user-data/attachments/*/")[0]
    photos = {1: base + "b8241d0a-image.jpg", 2: base + "f06b4a5c-image.jpg", 3: base + "952333f4-image.jpg"}
    c = {}
    for n, p, pts in [("a",1,(475,120)),("ā",1,(570,155)),("i",1,(480,200)),("ī",1,(640,245)),("u",1,(425,280)),("ū",1,(520,315)),("ṛ",1,(655,358)),("ṝ",1,(695,440)),
        ("ḷ",1,(585,465)),("ḹ",1,(680,520)),("e",1,(515,570)),("ai",1,(605,605)),("o",1,(670,640)),("au",1,(655,735)),("ka",1,(520,770)),("kha",1,(600,825)),
        ("ga",1,(455,868)),("gha",1,(505,918)),
        ("ṅa",2,(585,85)),("ca",2,(650,130)),("cha",2,(665,182)),("ja",2,(570,218)),("jha",2,(680,258)),("ña",2,(580,320)),("ṭa",2,(515,355)),("ṭha",2,(515,385)),
        ("ḍa",2,(520,447)),("ḍha",2,(525,498)),("ṇa",2,(525,543)),("ta",2,(515,598)),("tha",2,(515,652)),("da",2,(600,697)),("dha",2,(480,742)),("na",2,(450,785)),
        ("pa",2,(450,825)),("pha",2,(510,868)),("ba",2,(510,910)),("bha",2,(500,950)),
        ("ma",3,(570,92)),("ya",3,(590,138)),("ra",3,(580,180)),("la",3,(575,226)),("va",3,(585,270)),("śa",3,(575,316)),("ṣa",3,(570,367)),("sa",3,(678,418)),("ha",3,(580,485))]:
        c[n] = (p, *pts)
    build("devanagari", c, photos, "/usr/share/fonts/truetype/freefont/FreeSerif.ttf", "/home/claude/cmp_dv")
