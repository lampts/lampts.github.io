#!/bin/bash
export PATH="$HOME/Developer/aicode/.venv/bin:$PATH"

simon() {
  curl -s https://simonwillison.net/atom/everything/ \
    | grep '<title>' | sed 's/.*<title>//;s/<\/title>//' | head -20 \
    | llm -s "${1:-summarize top 5 AI news. one line each.}" \
    | tee -a ~/log/$(date -I)-news.md
}

hn() {
  curl -s https://hacker-news.firebaseio.com/v0/topstories.json \
    | jq '.[0:10][]' \
    | xargs -I{} curl -s "https://hacker-news.firebaseio.com/v0/item/{}.json" \
    | jq -r '.title' \
    | llm -s "${1:-pick 5 most relevant to AI. one line each.}" \
    | tee -a ~/log/$(date -I)-news.md
}

# Morning routine: one command
morning() {
  echo "=== $(date -I) ===" >> ~/log/$(date -I)-news.md
  echo "## Simon Willison" >> ~/log/$(date -I)-news.md
  simon
  echo "## Hacker News" >> ~/log/$(date -I)-news.md
  hn
}

# If called directly, run the function named in $1
"${@}"
