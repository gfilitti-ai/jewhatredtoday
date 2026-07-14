#!/usr/bin/env python3
"""
Headline-hero social card - the STANDARD template for Gerard's personal posts.

Layout: the article headline is the hero (serif, on white, styled like a news
clipping) with a source|date kicker; a dark panel below carries Gerard's byline
and one-line statement. No outlet branding, no quotation marks. 1080x1080 (X + IG).

Usage:
  python card_template.py \
    --source "The New York Times" --date "July 13, 2026" \
    --headline "UK Blames Iran-Backed Group for Wave of Antisemitic Attacks, Bans Revolutionary Guard" \
    --statement "Iran did not import antisemitism into Britain. It armed the antisemitism already there." \
    --out card.png
The --statement is optional; omit it for a headline-only card.
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

WHITE=(255,255,255); INK=(20,22,26); DARK=(20,22,28); RED=(214,32,39)
GREY=(120,124,132); PANELTX=(245,246,248)
SERIF="/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"
BLACK="/usr/share/fonts/truetype/lato/Lato-Black.ttf"
BOLD="/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
W=H=1080; M=84

def build(source, date, headline, statement, out):
    img=Image.new("RGB",(W,H),WHITE); d=ImageDraw.Draw(img)
    def F(p,s): return ImageFont.truetype(p,s)
    def tw(f,s): b=d.textbbox((0,0),s,font=f); return b[2]-b[0]
    def wrap(text,f,maxw):
        lines=[[]]; wln=0; sp=tw(f," ")
        for wd in text.split():
            ww=tw(f,wd)
            if wln and wln+sp+ww>maxw: lines.append([]); wln=0
            lines[-1].append(wd); wln+=(sp if wln else 0)+ww
        return [" ".join(l) for l in lines]

    has_stmt=bool(statement and statement.strip())
    panel_top=648 if has_stmt else H  # full-height news zone if no statement

    # kicker
    kf=F(BOLD,27); d.rectangle([M,96,M+64,105],fill=RED)
    kick=f"{source.upper()}    |    {date.upper()}" if date else source.upper()
    d.text((M,124),kick,font=kf,fill=RED)

    # headline (hero)
    htop=190; hbot=(panel_top-58) if has_stmt else (H-120); box=W-2*M
    sz=88
    while True:
        hf=F(SERIF,sz); lines=wrap(headline,hf,box); lh=int(sz*1.16)
        if len(lines)*lh<=(hbot-htop) or sz<=46: break
        sz-=3
    y=htop
    for ln in lines: d.text((M,y),ln,font=hf,fill=INK); y+=lh

    if has_stmt:
        d.rectangle([0,panel_top,W,H],fill=DARK)
        lf=F(BLACK,26); d.rectangle([M,panel_top+64,M+52,panel_top+72],fill=RED)
        d.text((M,panel_top+86),"GERARD FILITTI",font=lf,fill=WHITE)
        stop=panel_top+150; sbot=H-70; ssz=58
        while True:
            sf=F(BLACK,ssz); sl=wrap(statement,sf,W-2*M); slh=int(ssz*1.18)
            if len(sl)*slh<=(sbot-stop) or ssz<=34: break
            ssz-=2
        y=stop
        for ln in sl: d.text((M,y),ln,font=sf,fill=PANELTX); y+=slh

    img.save(out,"PNG"); print("saved",out,img.size)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True); ap.add_argument("--date",default="")
    ap.add_argument("--headline",required=True); ap.add_argument("--statement",default="")
    ap.add_argument("--out",default="card.png")
    a=ap.parse_args()
    build(a.source,a.date,a.headline,a.statement,a.out)
