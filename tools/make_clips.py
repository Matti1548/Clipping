"""Gebruik: python3 tools/make_clips.py <campagnemap> [naam-filter]
Leest <map>/clips.json en <map>/transcript.json, schrijft <map>/clips/*.mp4 en <map>/captions.txt.
Per clip: stiltes weggeknipt (jump cuts), om-en-om inzoom, hooktekst eerste 2,8 s, woord-voor-woord captions."""
import json,subprocess,os,re,sys,tempfile
D=sys.argv[1]; only=sys.argv[2] if len(sys.argv)>2 else None
cfg=json.load(open(f"{D}/clips.json")); tr=json.load(open(f"{D}/transcript.json"))
words=[]
for s in tr:
    for w in s["w"]:
        t=w[0].strip()
        if words and re.match(r"^[,.%:;)]",t): words[-1]=(words[-1][0]+t,words[-1][1],w[2])
        else: words.append((t,w[1],w[2]))
OUT=f"{D}/clips"; os.makedirs(OUT,exist_ok=True)
cw,ch=cfg["crop"]["breedte"],cfg["crop"]["hoogte"]
GAP=0.45; ZOOM=0.88
def ts(t): t=max(t,0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
HEAD="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: C,DejaVu Sans,84,&H0000E5FF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,8,2,2,50,50,560,1
Style: H,DejaVu Sans,74,&H00000000,&H00000000,&H0000E5FF,&H00000000,1,0,0,0,100,100,0,0,3,18,0,8,70,70,230,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
lines=["Post-caption per clip: Jake Paul On YouTube\n"]
for c in cfg["clips"]:
    if only and only not in c["naam"]: continue
    if c.get("gepost") and not only: continue  # reeds gepost: niet overschrijven
    ws=[w for w in words if w[1]>=c["start"]-0.05 and w[1]<c["einde"]]
    # segmenten (jump cuts): nieuw segment bij pauze > GAP
    segs=[]; cur=[ws[0]]
    for w in ws[1:]:
        if w[1]-cur[-1][2]>GAP: segs.append(cur); cur=[w]
        else: cur.append(w)
    segs.append(cur)
    spans=[]; off=0; tw=[]  # tw: (woord, nieuw_start, nieuw_einde)
    for i,sg in enumerate(segs):
        a=sg[0][1]-0.06; b=sg[-1][2]+0.14
        if i+1<len(segs): b=min(b,segs[i+1][0][1]-0.03)
        spans.append((a,b))
        for w,s,e in sg: tw.append((w,off+s-a,off+e-a))
        off+=b-a
    dur=off
    # captions: groepjes van 3 woorden, actief woord geel (\k)
    ev=[]
    for i in range(0,len(tw),3):
        g=tw[i:i+3]; st=g[0][1]; nxt=tw[i+3][1] if i+3<len(tw) else g[-1][2]+0.3
        en=min(max(g[-1][2],st+0.4),nxt)
        txt=""
        for j,(w,s,e) in enumerate(g):
            nx=g[j+1][1] if j+1<len(g) else en
            txt+="{\\k%d}%s "%(max(int(round((nx-s)*100)),1),re.sub(r"\s+"," ",w.upper()))
        ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},C,,0,0,0,,{txt.strip()}")
    if c.get("hook"): ev.append(f"Dialogue: 1,{ts(0)},{ts(min(2.8,dur))},H,,0,0,0,,{c['hook'].upper()}")
    tmp=tempfile.mkdtemp(); open(f"{tmp}/c.ass","w").write(HEAD+"\n".join(ev)+"\n")
    # filtergraph
    pre=min(s for s,_ in spans)-0.5; pre=max(pre,0)
    fc=[]; cat=""
    for i,(a,b) in enumerate(spans):
        a-=pre; b-=pre
        if i%2: w=int(cw*ZOOM)//2*2; h=int(ch*ZOOM)//2*2; x=c["x"]+(cw-w)//2; y=int(ch*0.06)
        else: w,h,x,y=cw,ch,c["x"],0
        fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,setsar=1[v{i}]")
        fc.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01[a{i}]")
        cat+=f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(spans)}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]ass={tmp}/c.ass[vo]")
    fc.append(f"[ac]loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={dur-0.2:.2f}:d=0.2[ao]")
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{pre:.2f}","-t",f"{spans[-1][1]-pre+1:.2f}","-i",cfg["bron"],"-filter_complex",";".join(fc),"-map","[vo]","-map","[ao]","-r","30","-c:v","libx264","-preset","medium","-crf","21","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-movflags","+faststart",f"{OUT}/{c['naam']}.mp4"],check=True)
    lines.append(f"{c['naam']}.mp4\nTitel: {c['titel']}\nHook-tekst in beeld: {c.get('hook','')}\nCaption: Jake Paul On YouTube\n")
    print(c["naam"],"duur",round(dur,1),"segmenten",len(spans))
if not only: open(f"{D}/captions.txt","w").write("\n".join(lines))
