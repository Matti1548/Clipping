"""Gebruik: python3 tools/make_clips.py <campagnemap>
Leest <map>/clips.json en <map>/transcript.json, schrijft <map>/clips/*.mp4 en <map>/captions.txt."""
import json,subprocess,os,re,sys,tempfile
D=sys.argv[1]; cfg=json.load(open(f"{D}/clips.json"))
tr=json.load(open(f"{D}/transcript.json"))
words=[(w[0].strip(),w[1],w[2]) for s in tr for w in s["w"]]
OUT=f"{D}/clips"; os.makedirs(OUT,exist_ok=True)
cw,ch=cfg["crop"]["breedte"],cfg["crop"]["hoogte"]
def ts(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
lines=["Post-caption per clip: Jake Paul On YouTube\n"]
for c in cfg["clips"]:
    ws=[w for w in words if w[1]>=c["start"]-0.05 and w[1]<c["einde"]]
    s0=ws[0][1]-0.08; dur=ws[-1][2]+0.2-s0
    ws=[(w,s-s0,e-s0) for w,s,e in ws]; ev=[]
    for i in range(0,len(ws),3):
        g=ws[i:i+3]; st=g[0][1]; nxt=ws[i+3][1] if i+3<len(ws) else g[-1][2]+0.3
        en=min(max(g[-1][2],st+0.4),nxt)
        ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},C,,0,0,0,,"+re.sub(r"\s+"," "," ".join(x[0] for x in g).upper()))
    ass="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: C,DejaVu Sans,78,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,520,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""+"\n".join(ev)+"\n"
    tmp=tempfile.mkdtemp(); open(f"{tmp}/c.ass","w").write(ass)
    vf=f"crop={cw}:{ch}:{c['x']}:0,scale=1080:1920:flags=lanczos,ass={tmp}/c.ass"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{s0:.2f}","-i",cfg["bron"],"-t",f"{dur:.2f}","-vf",vf,"-r","30","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-af",f"afade=t=out:st={dur-0.25:.2f}:d=0.25","-movflags","+faststart",f"{OUT}/{c['naam']}.mp4"],check=True)
    lines.append(f"{c['naam']}.mp4\nTitel: {c['titel']}\nCaption: Jake Paul On YouTube\n")
    print(c["naam"],round(dur,1))
open(f"{D}/captions.txt","w").write("\n".join(lines))
