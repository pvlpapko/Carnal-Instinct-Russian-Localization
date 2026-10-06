from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

OUT = Path("assets")
OUT.mkdir(exist_ok=True)
S=1024
img=Image.new("RGBA",(S,S),(0,0,0,0))
glow=Image.new("RGBA",(S,S),(0,0,0,0)); gd=ImageDraw.Draw(glow)
gd.rounded_rectangle((70,70,954,954),radius=220,fill=(8,18,30,248),outline=(45,215,255,170),width=26)
glow=glow.filter(ImageFilter.GaussianBlur(20)); img.alpha_composite(glow)
d=ImageDraw.Draw(img)
d.rounded_rectangle((82,82,942,942),radius=205,fill=(9,17,28,255),outline=(54,220,255,255),width=18)
d.rounded_rectangle((125,125,899,899),radius=165,outline=(43,91,114,220),width=8)
cx,cy=512,720
for off in (-55,55):
    d.rounded_rectangle((cx-140,cy+85+off//6,cx+140,cy+123+off//6),radius=18,fill=(111,71,43,255),outline=(232,154,74,230),width=5)
d.polygon([(512,825),(405,720),(432,610),(488,655),(512,520),(571,633),(613,592),(625,710)],fill=(255,118,40,255))
d.ellipse((434,650,590,815),fill=(255,157,55,255))
d.polygon([(512,785),(465,720),(492,640),(520,693),(555,650),(567,730)],fill=(255,218,92,255))
fonts=[Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")]
font_path=next((p for p in fonts if p.exists()),None)
font=ImageFont.truetype(str(font_path),340) if font_path else ImageFont.load_default()
text="CI"; bbox=d.textbbox((0,0),text,font=font,stroke_width=5); tw=bbox[2]-bbox[0]
txtglow=Image.new("RGBA",(S,S),(0,0,0,0)); tg=ImageDraw.Draw(txtglow)
tg.text(((S-tw)//2,185),text,font=font,fill=(68,224,255,220),stroke_width=10,stroke_fill=(28,180,230,190))
txtglow=txtglow.filter(ImageFilter.GaussianBlur(14)); img.alpha_composite(txtglow)
d=ImageDraw.Draw(img)
d.text(((S-tw)//2,185),text,font=font,fill=(178,244,255,255),stroke_width=7,stroke_fill=(30,174,224,255))
for y,w in [(515,250),(555,310),(595,220)]:
    d.rounded_rectangle((512-w//2,y,512+w//2,y+18),radius=9,fill=(54,216,250,180))
img.save(OUT/"ci_mod_menu_icon.png")
img.save(OUT/"ci_mod_menu.ico",format="ICO",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
