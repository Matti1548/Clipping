from faster_whisper import WhisperModel
import json,sys
m=WhisperModel("small",device="cpu",compute_type="int8")
segs,_=m.transcribe(sys.argv[2],language="en",word_timestamps=True,vad_filter=True)
out=[]
for s in segs:
    out.append({"s":s.start,"e":s.end,"t":s.text.strip(),"w":[(w.word,w.start,w.end) for w in s.words]})
json.dump(out,open(sys.argv[3],"w"))
for o in out: print(f"{o['s']:.1f}-{o['e']:.1f} {o['t']}")
