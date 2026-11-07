"""Generate local-only fictional QR fixtures and PWA icons."""
from pathlib import Path
import json
import qrcode
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parent.parent
for name,url in [('ordinary','https://example.test/menu'),('disguised','http://paypal.com@account-check.test/login')]:
    im=qrcode.make(url).convert('RGBA')
    im.save(root/f'static/demo-{name}.png')
    (root/f'tests/qr-{name}.json').write_text(json.dumps({'width':im.width,'height':im.height,'data':list(im.tobytes()),'expected':url}))
for size in (192,512):
    im=Image.new('RGB',(size,size),'#173f35');d=ImageDraw.Draw(im)
    s=size/100
    d.rectangle((32*s,25*s,43*s,76*s),fill='#d4ed9e')
    d.rounded_rectangle((32*s,25*s,72*s,59*s),radius=12*s,fill='#d4ed9e')
    d.rounded_rectangle((43*s,36*s,61*s,48*s),radius=5*s,fill='#173f35')
    im.save(root/f'static/icon-{size}.png')
