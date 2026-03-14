import re
import sys

# Comprehensive regex for matching emojis (including skin tones, flags, etc.)
# Source: https://regex101.com/library/aP0rE1?orderBy=RELEVANCE&search=emoji
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251" 
    "]+",
    flags=re.UNICODE
)

def remove_emojis(text):
    return emoji_pattern.sub(r'', text)

def clean_file(input_path, output_path=None):
    with open(input_path, 'r', encoding='utf-8') as f:
        original = f.read()
    cleaned = remove_emojis(original)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
    return cleaned

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python remove_emojis.py <input_file> [output_file]")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    cleaned_code = clean_file(input_file, output_file)
    if not output_file:
        print(cleaned_code)