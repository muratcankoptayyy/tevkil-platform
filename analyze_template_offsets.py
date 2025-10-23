"""
Şablonun character offset'lerini analiz et
"""
import zipfile
import xml.etree.ElementTree as ET

# Şablonu oku
with zipfile.ZipFile('OrnekVekaletnameYetkiBelgesiSablonu.udf', 'r') as z:
    xml_content = z.read('content.xml').decode('utf-8')

# Parse XML
root = ET.fromstring(xml_content)

# CDATA içeriği
cdata_start = xml_content.find('<![CDATA[') + 9
cdata_end = xml_content.find(']]></content>')
text = xml_content[cdata_start:cdata_end]

print("=" * 80)
print("ŞABLON METNİ (Character positions):")
print("=" * 80)

# Her karakteri pozisyonuyla yazdır
for i, char in enumerate(text[:500]):
    if char == '\n':
        print(f"{i:4d}: <NEWLINE>")
    elif char == '\t':
        print(f"{i:4d}: <TAB>")
    elif char == '.':
        print(f"{i:4d}: {repr(char)} ← NOKTA")
    else:
        print(f"{i:4d}: {repr(char)}")

print("\n" + "=" * 80)
print("PLACEHOLDER POZİSYONLARI:")
print("=" * 80)

# Placeholder'ları bul
placeholder = '..............'
pos = 0
count = 1
while True:
    pos = text.find(placeholder, pos)
    if pos == -1:
        break
    # Önceki ve sonraki metni göster
    before = text[max(0, pos-30):pos]
    after = text[pos+len(placeholder):pos+len(placeholder)+30]
    print(f"\n{count}. Placeholder @ position {pos}:")
    print(f"   Önce: ...{before}")
    print(f"   Sonra: {after}...")
    pos += len(placeholder)
    count += 1

print("\n" + "=" * 80)
print("ELEMENTS ANALİZİ:")
print("=" * 80)

# Elements bölümünü parse et
elements_start = xml_content.find('<elements')
elements_end = xml_content.find('</elements>') + 11
elements_xml = xml_content[elements_start:elements_end]

# Paragrafları analiz et
import re
paragraphs = re.findall(r'<paragraph[^>]*>(.*?)</paragraph>', elements_xml, re.DOTALL)

for i, para in enumerate(paragraphs[:20]):
    print(f"\nParagraph {i+1}:")
    # Content tag'lerini bul
    contents = re.findall(r'<content[^>]*startOffset="(\d+)"[^>]*length="(\d+)"[^>]*/>', para)
    for start, length in contents:
        start, length = int(start), int(length)
        snippet = text[start:start+length]
        print(f"   Offset {start}, Length {length}: {repr(snippet)}")
