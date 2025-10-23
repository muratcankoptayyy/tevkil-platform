text = 'Bu yetki belgesi, 1136 sayılı Avukatlık Kanunu\'nu değiştiren 4667 sayılı Kanun\'un 36. maddesi ile 56. maddesine eklenen hüküm uyarınca, vekaletname yerine geçmek üzere, SADECE DURUŞMALARA KATILMA YETKİSİYLE SINIRLI OLMAK ÜZERE tarafımdan düzenlenmiştir.'

bold_text = 'SADECE DURUŞMALARA KATILMA YETKİSİYLE SINIRLI OLMAK ÜZERE'

bold_start = text.find(bold_text)
bold_length = len(bold_text)
before_bold = text[:bold_start]
after_bold = text[bold_start + bold_length:]

print(f'📏 Toplam metin uzunluğu: {len(text)}')
print(f'🔍 Bold başlangıç pozisyonu (metin içinde): {bold_start}')
print(f'📐 Bold uzunluğu: {bold_length}')
print(f'')
print(f'Önceki metin uzunluğu: {len(before_bold)}')
print(f'Sonraki metin uzunluğu: {len(after_bold)}')
print(f'')
print(f'Bold metin: [{bold_text}]')
print(f'')
print(f'XML için:')
print(f'  Önceki kısım: startOffset="0" length="{len(before_bold)}"')
print(f'  Bold kısım: startOffset="{bold_start}" length="{bold_length}" bold="true"')
print(f'  Sonraki kısım: startOffset="{bold_start + bold_length}" length="{len(after_bold)}"')
