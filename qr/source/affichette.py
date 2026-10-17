import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from qr_premium import rendu_png
S=os.environ.get('POLICES', 'polices'); K=2  # 600 dpi
W,H=1240*K,1748*K
NOIR="#14100D"; OR="#C69A4D"; ORL="#E9CE96"; CR="#F5EFE4"; GR="#9C8E80"
c=Image.new("RGB",(W,H),NOIR); d=ImageDraw.Draw(c)
# halo doré discret en haut
halo=Image.new("L",(W,H),0); ImageDraw.Draw(halo).ellipse((-W*.3,-H*.35,W*1.3,H*.35),fill=38)
from PIL import ImageFilter
halo=halo.filter(ImageFilter.GaussianBlur(160*K)); c.paste(Image.new("RGB",(W,H),OR),(0,0),halo)
d=ImageDraw.Draw(c)
# filet or
m=46*K; d.rounded_rectangle((m,m,W-m,H-m),radius=26*K,outline=OR,width=2*K)
fr=lambda s:ImageFont.truetype(S+"/fraunces-normal-400_700.ttf",s*K)
pb=lambda s:ImageFont.truetype(S+"/poppins-latin-600.ttf",s*K)
pr=lambda s:ImageFont.truetype(S+"/poppins-latin.ttf",s*K)
def ctr(y,t,f,col,esp=0):
    if esp:
        w=sum(d.textlength(ch,font=f) for ch in t)+esp*K*(len(t)-1); x=(W-w)/2
        for ch in t: d.text((x,y*K),ch,font=f,fill=col); x+=d.textlength(ch,font=f)+esp*K
    else:
        w=d.textlength(t,font=f); d.text(((W-w)/2,y*K),t,font=f,fill=col)
logo=Image.open("icons/pino-logo.png").convert("RGBA").crop((79,121,432,409)); lw=300*K; lh=int(lw*logo.height/logo.width)
L=logo.resize((lw,lh),Image.LANCZOS); c.paste(L,((W-lw)//2,120*K),L)
y=120+lh//K+56
ctr(y,"Notre app,",fr(84),CR); ctr(y+98,"dans votre poche",fr(84),OR)
Q=640*K; P=34*K
qr=rendu_png(Q)
card=Image.new("RGB",(Q+2*P,Q+2*P),CR); card.paste(qr,(P,P))
mk=Image.new("L",card.size,0); ImageDraw.Draw(mk).rounded_rectangle((0,0,card.width-1,card.height-1),40*K,fill=255)
# ombre douce
sh=Image.new("L",(W,H),0); qy=(y+232)*K; qx=(W-card.width)//2
ImageDraw.Draw(sh).rounded_rectangle((qx,qy+18*K,qx+card.width,qy+card.height+18*K),40*K,fill=150)
sh=sh.filter(ImageFilter.GaussianBlur(30*K)); c.paste(Image.new("RGB",(W,H),"#000"),(0,0),sh)
c.paste(card,(qx,qy),mk); d=ImageDraw.Draw(c)
y2=qy//K+card.height//K+58
ctr(y2,"SCANNEZ  ·  INSTALLEZ",pb(40),OR,esp=3)
ctr(y2+70,"La carte et votre liste, en un geste,",pr(31),CR)
ctr(y2+114,"depuis l’écran d’accueil de votre téléphone.",pr(31),CR)
ctr(H//K-46-70,"pizzeriapino.be",pr(27),GR)
print("bas texte",y2+160,"pied",H//K-116)
c.save("qr/affichette-qr-app-A6.png",dpi=(600,600),optimize=True)
c.save("qr/affichette-qr-app-A6.pdf",resolution=600)
