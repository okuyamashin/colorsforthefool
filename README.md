# Colors for the Fool

A tarot reading for today's lucky color. Draw one card from the twenty-two major arcana, upright or reversed, read what it stands for, then tap again. A story ends on one color, and a picture shows that color in a mirror.

The site is published at [colorsofthefool.engawa5656.com](https://colorsofthefool.engawa5656.com/).

- Japanese: [/](https://colorsofthefool.engawa5656.com/)
- English: [/en/](https://colorsofthefool.engawa5656.com/en/)

The two languages are separate pages. Nothing redirects you by browser language. Pictures and video are shared. A card drawn in one language does not leave the other deck.

## Draw

1. Tap the card. One of the twenty-two major arcana appears, upright or reversed.
2. Read what that card stands for today.
3. Tap again. The story opens, and today's lucky color is named at the end. Tap the mirror and the writing folds away. The card turns face down.

Each side of a card is tied to ten named colors. The story walks through myth, history, a place, or a tool, and lands on the color. When all twenty-two cards have been drawn, the deck is whole again.

Every color also has a fixed page, so a reading can be opened again or found from search:

- `/cards/the-fool/` and `/en/cards/the-fool/`
- `/cards/the-fool/white/` and `/en/cards/the-fool/white/`

## Layout

`public/` is the site. `data/` holds the cards.

```
public/index.html          Japanese home
public/en/index.html       English home
public/app.js              The draw, shared by both homes
public/meanings.js         Japanese card meanings
public/meanings.en.js      English card meanings
public/cards/              Japanese library
public/en/cards/           English library
data/<card>/card.json      Names, colors, and file names
data/<card>/face.jpg       The card face
data/<card>/<color>.txt    Japanese color story
data/<card>/<color>.en.txt English color story
data/<card>/<color>.jpg    The scene, with the color in the mirror
```

On an English page, the app reads `textEn` from `card.json` (for example `white.en.txt`). On a Japanese page it reads `text`.

## Preview

Start a static server at the repository root. English pages load pictures and stories from `/data`, so the server root has to be this directory, not `public/`.

```sh
python3 -m http.server 8741
```

- Japanese: http://127.0.0.1:8741/public/
- English: http://127.0.0.1:8741/public/en/

Add `?test=1-1` to draw a chosen card and color. The first number is the card, from 1 to 22 in major-arcana order. The second is the color: 1–10 upright, 11–20 reversed. Example: `?test=22-1` is The World, upright, first color.

## Library pages

Card and color pages are generated from `data/` and the meanings files.

```sh
python3 scripts/build_library.py
```

That rewrites `public/cards/` and `public/en/cards/`, and updates `public/sitemap.xml`. Japanese and English pages for the same card and color point at each other with `hreflang`.
