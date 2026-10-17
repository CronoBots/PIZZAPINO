import qrcode, math, base64, io, sys
from PIL import Image, ImageDraw, ImageFilter
URL = "https://pizzeriapino.be/?utm_source=qr#installer"
NOIR, CREME, ROUGE, OR = "#14100D", "#F5EFE4", "#A8261D", "#C69A4D"
q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=0)
q.add_data(URL); q.make(fit=True)
M = q.get_matrix(); N = len(M); QZ = 4; T = N + 2*QZ

def oeil(r, c): return (r < 7 and c < 7) or (r < 7 and c >= N-7) or (r >= N-7 and c < 7)
# médaillon central : on libère un disque (correction H : ~30 % récupérable, on en prend < 10 %)
R_LOGO = N * 0.17
cx = cy = N / 2
def centre(r, c): return math.hypot(r + .5 - cy, c + .5 - cx) < R_LOGO + .6

def rendu_png(px):
    s = px / T; ss = 4  # suréchantillonnage pour des bords nets
    W = int(T * s * ss); k = s * ss
    im = Image.new("RGB", (W, W), CREME); d = ImageDraw.Draw(im)
    o = QZ * k
    rd = .46  # rayon des points (en modules)
    for r in range(N):
        for c in range(N):
            if M[r][c] and not oeil(r, c) and not centre(r, c):
                x, y = o + (c + .5) * k, o + (r + .5) * k
                d.ellipse((x - rd*k, y - rd*k, x + rd*k, y + rd*k), fill=NOIR)
    for (r0, c0) in [(0, 0), (0, N-7), (N-7, 0)]:
        x, y = o + c0 * k, o + r0 * k
        d.rounded_rectangle((x, y, x + 7*k, y + 7*k), radius=2.2*k, fill=NOIR)
        d.rounded_rectangle((x + k, y + k, x + 6*k, y + 6*k), radius=1.4*k, fill=CREME)
        d.rounded_rectangle((x + 2*k, y + 2*k, x + 5*k, y + 5*k), radius=.9*k, fill=ROUGE)
    # médaillon : anneau or, disque charbon, logo
    C = o + N/2 * k; R = R_LOGO * k
    d.ellipse((C - R, C - R, C + R, C + R), fill=OR)
    R2 = R - .32*k
    d.ellipse((C - R2, C - R2, C + R2, C + R2), fill=NOIR)
    logo = Image.open("icons/pino-logo.png").convert("RGBA").crop((79, 121, 432, 409))
    lw = int(R2 * 1.5); lh = int(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    im.paste(logo, (int(C - lw/2), int(C - lh/2 - R2*.02)), logo)
    return im.resize((int(T*s), int(T*s)), Image.LANCZOS)

def rendu_svg():
    u = 10; out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {T*u} {T*u}" width="{T*u}" height="{T*u}">')
    out.append(f'<rect width="100%" height="100%" fill="{CREME}"/>')
    out.append(f'<g fill="{NOIR}">')
    for r in range(N):
        for c in range(N):
            if M[r][c] and not oeil(r, c) and not centre(r, c):
                out.append(f'<circle cx="{(QZ+c+.5)*u:g}" cy="{(QZ+r+.5)*u:g}" r="{.46*u:g}"/>')
    out.append('</g>')
    for (r0, c0) in [(0, 0), (0, N-7), (N-7, 0)]:
        x, y = (QZ + c0)*u, (QZ + r0)*u
        out.append(f'<rect x="{x}" y="{y}" width="{7*u}" height="{7*u}" rx="{2.2*u:g}" fill="{NOIR}"/>')
        out.append(f'<rect x="{x+u}" y="{y+u}" width="{5*u}" height="{5*u}" rx="{1.4*u:g}" fill="{CREME}"/>')
        out.append(f'<rect x="{x+2*u}" y="{y+2*u}" width="{3*u}" height="{3*u}" rx="{.9*u:g}" fill="{ROUGE}"/>')
    C = (QZ + N/2)*u; R = R_LOGO*u; R2 = R - .32*u
    out.append(f'<circle cx="{C:g}" cy="{C:g}" r="{R:g}" fill="{OR}"/><circle cx="{C:g}" cy="{C:g}" r="{R2:g}" fill="{NOIR}"/>')
    logo = Image.open("icons/pino-logo.png").convert("RGBA").crop((79, 121, 432, 409)).resize((353, 288), Image.LANCZOS)
    b = io.BytesIO(); logo.save(b, "PNG", optimize=True)
    lw = R2*1.5; lh = lw*288/353
    out.append(f'<image x="{C-lw/2:g}" y="{C-lh/2-R2*.02:g}" width="{lw:g}" height="{lh:g}" href="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}"/>')
    out.append('</svg>')
    return "\n".join(out)

if __name__ == "__main__":
    rendu_png(3000).save("qr/qr-app-pino.png", dpi=(600, 600), optimize=True)
    open("qr/qr-app-pino.svg", "w").write(rendu_svg())
    print("version", q.version, "modules", N)
