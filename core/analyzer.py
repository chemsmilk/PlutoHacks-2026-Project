"""Pure lexical checks: no DNS, HTTP, redirects, or reputation requests."""
import ipaddress
import re
import idna
from urllib.parse import urlsplit, unquote
import tldextract

EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)
LIMITATIONS = 'URL structure only. Website content, redirects, domain ownership, certificates, and live threat lists were not checked. No obvious indicators does not mean safe.'
CATALOG = {
 'http': ('Unencrypted address','The address uses HTTP.','Information sent to this site could be exposed in transit.','Avoid entering passwords or payment details. Find the official HTTPS address.'),
 'credentials': ('Misleading address prefix','The address contains text before an @ sign.','That text can look like a trusted website while the actual destination is elsewhere.','Check the destination domain below. Use an official app or a known bookmark.'),
 'ip': ('Numeric destination','The destination is an IP address rather than a named website.','It is harder to recognize who controls this destination. Numeric addresses can also be legitimate.','Confirm the address through a separate, trusted channel.'),
 'local': ('Local or private destination','The address points to a local or non-public host.','It could target a device or service on your network.','Only use it if you recognize the device and expected this QR code.'),
 'unicode': ('Internationalized domain','The domain uses international characters or their encoded form.','Some characters resemble letters in familiar names. Many international domains are legitimate.','Compare the domain carefully with a known official address.'),
 'brand': ('Brand-like domain text','A familiar brand name appears outside its expected domain.','A convincing name can disguise a destination controlled by someone else.','Use the official app or type the known official address yourself.'),
 'shortener': ('Hidden final destination','The address uses a known link-shortening service.','Its final destination is unknown because PluQ does not follow links.','Ask the sender for the full address and verify it separately.'),
 'port': ('Unusual web port','The address specifies a port other than 80 or 443.','It may lead to an unexpected service, though custom ports can be legitimate.','Confirm this address with its sender.'),
 'encoding': ('Encoded or nested address','The address contains encoding or an embedded URL.','These features can obscure a link’s meaning. Redirect behavior has not been checked.','Verify the destination independently before sharing sensitive information.'),
 'deep': ('Many subdomains','The hostname has several layers before its main domain.','Long names can make the controlling domain hard to spot.','Focus on the destination domain highlighted below.'),
}

def analyze(text):
    raw = text.strip()
    result = dict(input=raw, kind='url', status='unknown', title='Unable to assess', host=None, domain=None, findings=[], limitations=LIMITATIONS, reputation='Not checked', destination_contacted=False)
    def unknown(reason):
        result.update(kind='unsupported', message=reason)
        return result
    if not raw or len(raw)>4096 or re.search(r'[\x00-\x20\x7f\\]', raw):
        return unknown('Empty or ambiguous content, whitespace, or control characters detected. Nothing was opened.')
    if not re.match(r'^https?://',raw,re.I):
        return unknown('This is not a complete HTTP or HTTPS URL. Text, Wi-Fi, payment, and other QR payloads are not executed. Include https:// for a web address.')
    try:
        parts=urlsplit(raw)
        # Browsers use UTS-46/IDNA, not Python's older built-in IDNA codec.
        host=(parts.hostname or '').lower()
        port=parts.port
        if not host or '%' in host: return unknown('Invalid or ambiguous hostname.')
        authority=parts.netloc.rsplit('@',1)[-1]
        if authority.startswith('[') and not re.fullmatch(r'\[[0-9a-fA-F:.]+\](?::[0-9]+)?',authority):
            return unknown('Invalid bracketed IP address.')
        try: ip=ipaddress.ip_address(host)
        except ValueError:
            ip=None
        if ip:
            ascii_host=str(ip)
        else:
            ascii_host=idna.encode(host,uts46=True,transitional=False).decode('ascii')
            # One trailing root dot is valid; repeated dots must not be hidden.
            ascii_host=ascii_host.removesuffix('.')
            if not re.fullmatch(r'[a-z0-9.-]+',ascii_host) or len(ascii_host)>253 or any(not x or len(x)>63 or x.startswith('-') or x.endswith('-') for x in ascii_host.split('.')):
                return unknown('Invalid hostname.')
            # Browsers interpret a numeric final label as an IPv4 candidate.
            # Reject legacy decimal/octal/hex forms rather than show a wrong host.
            if re.fullmatch(r'(?:[0-9]+|0x[0-9a-f]+)',ascii_host.split('.')[-1]):
                return unknown('Ambiguous numeric destination. Verify the address independently.')
        ext=EXTRACT(ascii_host) if not ip else None
        # Unknown suffix: show the full host, never guess who owns the last two labels.
        domain=(ext.top_domain_under_public_suffix or ascii_host) if ext else ascii_host
        basis='public suffix snapshot' if ext and ext.top_domain_under_public_suffix else 'full hostname; registrable domain not established'
        result.update(host=ascii_host,domain=domain,domain_basis=basis,scheme=parts.scheme,port=port)
    except (ValueError,UnicodeError):
        return unknown('The address could not be parsed reliably. Nothing was opened.')
    def add(code,evidence):
        title,detected,why,action=CATALOG[code]
        result['findings'].append(dict(id=code,title=title,detected=detected,why=why,action=action,evidence=evidence))
    if parts.scheme=='http': add('http','scheme=http')
    if parts.username is not None: add('credentials','userinfo present; destination='+ascii_host)
    if ip:
        add('ip','IP literal: '+ascii_host)
        if not ip.is_global: add('local','Non-global IP address')
    elif '.' not in ascii_host or ascii_host.endswith(('.local','.localhost')): add('local','Local hostname')
    if any(ord(c)>127 for c in host) or 'xn--' in ascii_host: add('unicode','IDNA: '+ascii_host)
    for brand,official in {'paypal':'paypal.com','google':'google.com','microsoft':'microsoft.com','apple':'apple.com','amazon':'amazon.com'}.items():
        # Token boundaries avoid treating words such as pineapple as Apple branding.
        if brand in re.split(r'[.-]',ascii_host) and domain!=official:
            add('brand',f'{brand} outside expected domain {official}; observed {domain}')
            break
    if domain in {'bit.ly','tinyurl.com','t.co','is.gd','cutt.ly','shorturl.at'}: add('shortener','Known shortener hostname')
    if port is not None and port not in (80,443): add('port','Explicit port: '+str(port))
    if re.search(r'%(?:25|2f|3a|40|5c|00|0a|0d)',raw,re.I) or re.search(r'https?://',unquote(parts.query),re.I): add('encoding','Encoded delimiter/control character or nested URL present; not followed')
    if len(ascii_host.split('.'))>=5: add('deep','Five or more hostname labels')
    result.update(status='caution' if result['findings'] else 'clear',title='Pause before you proceed' if result['findings'] else 'No obvious indicators found')
    result['message']='Verify this destination before entering personal information.' if result['findings'] else 'These checks found no obvious warning signs. The website itself has not been verified.'
    return result
