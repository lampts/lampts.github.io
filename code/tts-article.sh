#!/bin/bash

# TTS Article Reader with Jina + MLX-Audio (Fixed)
set -e

# Default values
MODEL="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"
PLAY=true
SPEED=1.0
REF_AUDIO=""
OUTPUT_DIR="$HOME/Desktop"
CHUNK_SIZE=15000
MAX_CHARS=45000

# Help
show_help() {
    cat << EOF
Usage: $0 <URL> [OPTIONS]

Read web articles aloud using Jina AI extraction and Qwen3-TTS

Options:
    -o, --output NAME   Output filename prefix (default: article_timestamp)
    -s, --speed FLOAT   Speech speed 0.5-2.0 (default: 1.0)
    -r, --ref-audio FILE Voice cloning reference audio
    -d, --dir DIR       Output directory (default: ~/Desktop)
    -n, --no-play       Save only, don't play
    -c, --chunk-size N  Max chars per chunk (default: 15000)
    -h, --help          Show help
EOF
}

# Parse args
URL=""
OUTPUT_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) show_help; exit 0 ;;
        -o|--output) OUTPUT_NAME="$2"; shift 2 ;;
        -s|--speed) SPEED="$2"; shift 2 ;;
        -r|--ref-audio) REF_AUDIO="$2"; shift 2 ;;
        -d|--dir) OUTPUT_DIR="$2"; shift 2 ;;
        -n|--no-play) PLAY=false; shift ;;
        -c|--chunk-size) CHUNK_SIZE="$2"; shift 2 ;;
        -*)
            if [[ -z "$URL" ]]; then URL="$1"; shift
            else echo "Unknown option: $1" >&2; exit 1; fi ;;
        *)
            if [[ -z "$URL" ]]; then URL="$1"; shift
            else echo "Error: Multiple URLs" >&2; exit 1; fi ;;
    esac
done

[[ -z "$URL" ]] && { echo "Error: URL required" >&2; exit 1; }

mkdir -p "$OUTPUT_DIR"
PREFIX="${OUTPUT_NAME:-article_$(date +%s)}"

# Extract with Jina
echo "🔍 Fetching: $URL"
TEXT=$(curl -fsL "https://r.jina.ai/http://${URL#https://}" --max-time 30 || {
    echo "Error: Failed to fetch" >&2; exit 1;
})

LENGTH=${#TEXT}
echo "📄 Extracted: $LENGTH chars"

[[ $LENGTH -gt $MAX_CHARS ]] && TEXT="${TEXT:0:$MAX_CHARS}"

# Process chunks
NUM_CHUNKS=$(( (LENGTH + CHUNK_SIZE - 1) / CHUNK_SIZE ))
[[ $NUM_CHUNKS -lt 1 ]] && NUM_CHUNKS=1

process_chunk() {
    local text="$1"
    local n="$2"
    local total="$3"
    local file="${OUTPUT_DIR}/${PREFIX}_${n}.wav"

    echo "🎙️  Chunk $n/$total ($((${#text}/1000))k chars)..."

    # Build args array to handle special characters safely
    local args=(
        --model "$MODEL"
        --text "$text"
        --speed "$SPEED"
        --file_prefix "${OUTPUT_DIR}/${PREFIX}_${n}"
    )

    [[ -n "$REF_AUDIO" ]] && args+=(--ref_audio "$REF_AUDIO")
    [[ "$PLAY" == true && "$n" == "1" ]] && args+=(--play)

    python -m mlx_audio.tts.generate "${args[@]}"
}

# Split and process
if [[ $NUM_CHUNKS -gt 1 ]]; then
    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    echo "$TEXT" > "$TMPDIR/full.txt"

    # Awk splits preserving paragraphs
    awk -v size=$CHUNK_SIZE 'BEGIN{n=1; buf=""}
        {if(length(buf)+length($0)>size && length(buf)>1000){print buf > ("'$TMPDIR'/c" n); n++; buf=$0} else buf=buf (buf?"\n":"") $0}
        END{if(buf)print buf > ("'$TMPDIR'/c" n)}' "$TMPDIR/full.txt"

    for i in $(seq 1 $NUM_CHUNKS); do
        if [[ -f "$TMPDIR/c$i" ]]; then
            chunk=$(cat "$TMPDIR/c$i")
            [[ ${#chunk} -gt 100 ]] && process_chunk "$chunk" "$i" "$NUM_CHUNKS"
        fi
    done

    # Optional: concatenate
    if command -v ffmpeg &>/dev/null; then
        CONCAT="${OUTPUT_DIR}/${PREFIX}_full.wav"
        ffmpeg -y -f concat -safe 0 -i <(for f in ${OUTPUT_DIR}/${PREFIX}_*.wav; do echo "file '$f'"; done) -c copy "$CONCAT" 2>/dev/null
        [[ -f "$CONCAT" ]] && echo "🎵 Combined: $CONCAT"
    fi
else
    process_chunk "$TEXT" "1" "1"
fi

echo "✅ Done! Files in: $OUTPUT_DIR"
