This is a “read a web page out loud” script. You run it in a Terminal, give it a link (URL), and it:

1) downloads the article text  
2) cuts it into pieces if it’s too long  
3) uses a text-to-speech AI voice to make `.wav` audio files  
4) optionally plays the first chunk out loud  
5) optionally glues all chunks into one big audio file

I’ll explain it like you’re 10.

---

## 1) The top part: settings and rules

```bash
#!/bin/bash
set -e
```

- `#!/bin/bash` means: “Run this with the Bash command language.”
- `set -e` means: “If something goes wrong, stop immediately instead of continuing.”

Then it sets default “starting settings”:

```bash
MODEL="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"
PLAY=true
SPEED=1.0
REF_AUDIO=""
OUTPUT_DIR="$HOME/Desktop"
CHUNK_SIZE=15000
MAX_CHARS=45000
```

Think of these like game options:
- `MODEL` = which robot voice brain to use
- `PLAY=true` = play audio automatically (only first part)
- `SPEED=1.0` = normal talking speed
- `REF_AUDIO` = (optional) a file you give it to copy a voice
- `OUTPUT_DIR` = where to save audio files (Desktop)
- `CHUNK_SIZE` = how big each piece of text can be
- `MAX_CHARS` = maximum text it will read from the page (to avoid huge pages)

---

## 2) Help menu

The function:

```bash
show_help() { ... }
```

If you run the script with `--help`, it prints instructions like:

- `-o` name your output files
- `-s` change speed
- `-r` give a reference audio for voice cloning
- `-d` change save folder
- `-n` don’t play audio automatically
- `-c` change chunk size

---

## 3) Reading what you typed (arguments)

This section figures out what URL and options you gave:

```bash
while [[ $# -gt 0 ]]; do
  case $1 in
     ...
  esac
done
```

Imagine it’s checking each word you typed after the script name.

It makes sure:
- You provided exactly **one URL**
- You didn’t type unknown options

If you forget the URL:

```bash
[[ -z "$URL" ]] && { echo "Error: URL required"; exit 1; }
```

It stops and tells you.

---

## 4) Make a folder + choose a filename

```bash
mkdir -p "$OUTPUT_DIR"
PREFIX="${OUTPUT_NAME:-article_$(date +%s)}"
```

- Creates the output folder if it doesn’t exist.
- Picks a filename prefix like `article_1700000000` (that number is the current time in seconds).

So it can make files like:
- `article_1700000000_1.wav`
- `article_1700000000_2.wav`

---

## 5) Download the article text (the “Jina” part)

```bash
TEXT=$(curl -fsL "https://r.jina.ai/http://${URL#https://}" --max-time 30 ...)
```

- `curl` downloads stuff from the internet.
- It calls `r.jina.ai` which is a service that tries to extract the **readable article text** from a web page (removing lots of menus/ads).

If it can’t download in 30 seconds, it fails.

Then:

```bash
LENGTH=${#TEXT}
[[ $LENGTH -gt $MAX_CHARS ]] && TEXT="${TEXT:0:$MAX_CHARS}"
```

- Counts how many characters were extracted.
- If it’s too long, it cuts the text down to `MAX_CHARS`.

---

## 6) Decide how many chunks (pieces) to split into

```bash
NUM_CHUNKS=$(( (LENGTH + CHUNK_SIZE - 1) / CHUNK_SIZE ))
```

If the article is big, it will be split into chunk 1, chunk 2, etc.

This is like: “If each box can hold 15000 letters, how many boxes do we need?”

---

## 7) Turn one chunk into speech (the main worker)

This function does the TTS job:

```bash
process_chunk() { ... python -m mlx_audio.tts.generate ... }
```

It:
- makes a filename for this chunk: `PREFIX_n.wav`
- builds a safe list of arguments (`args=(...)`) so weird punctuation in the text won’t break the command
- runs Python:

```bash
python -m mlx_audio.tts.generate "${args[@]}"
```

That Python tool generates the `.wav` audio using the model.

Special behaviors:
- If you provided `REF_AUDIO`, it adds `--ref_audio ...` to copy that voice.
- If `PLAY=true` it only plays the **first** chunk automatically.

---

## 8) Splitting the text nicely (if there are multiple chunks)

If the article needs multiple chunks:

- It creates a temporary folder:
  ```bash
  TMPDIR=$(mktemp -d)
  trap "rm -rf $TMPDIR" EXIT
  ```
  This is like a scratchpad folder. The `trap` makes sure it gets deleted when the script ends.

- It saves the full text to a file.

- Then it uses `awk` to split it **trying to keep paragraphs together**, so the voice doesn’t cut in the middle of a paragraph.

- Then it loops through each chunk file and calls `process_chunk` on it.

---

## 9) Optional: glue all wav files into one

If you have `ffmpeg` installed, it tries to combine all the chunk wavs into one file:

```bash
CONCAT="${OUTPUT_DIR}/${PREFIX}_full.wav"
ffmpeg ... -c copy "$CONCAT"
```

So you end up with a single “full” recording too.

---

## 10) Final message

```bash
echo "✅ Done! Files in: $OUTPUT_DIR"
```

It tells you where the audio files are.

---

### What you’d type to use it (examples)

- Read an article at normal speed and save to Desktop:
  ```bash
  ./script.sh https://example.com/article
  ```

- Faster voice, don’t auto-play:
  ```bash
  ./script.sh https://example.com/article -s 1.3 -n
  ```

- Save to a different folder:
  ```bash
  ./script.sh https://example.com/article -d ~/Downloads
  ```

---

If you tell me what computer you’re using (Mac/Linux) and how you run it, I can also explain what you need installed for `python -m mlx_audio...`, and what error messages mean if it doesn’t work.
