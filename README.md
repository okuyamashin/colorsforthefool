# Colors for the Fool

A tarot reading for today's lucky color. Draw one card from the twenty-two major arcana, upright or reversed, read what it stands for, then tap again. A story ends on one color, and a picture shows that color in a mirror.

The site is published at [colorsofthefool.engawa5656.com](https://colorsofthefool.engawa5656.com/).

Languages live in [`data/languages.json`](data/languages.json). Each one is its own set of pages. Nothing redirects you by browser language. Pictures and video are shared. A card drawn in one language does not leave the other deck.

## Draw

1. Tap the card. One of the twenty-two major arcana appears, upright or reversed.
2. Read what that card stands for today.
3. Tap again. The story opens, and today's lucky color is named at the end. Tap the mirror and the writing folds away. The card turns face down.

Each side of a card is tied to ten named colors. The story walks through myth, history, a place, or a tool, and lands on the color. When all twenty-two cards have been drawn, the deck is whole again.

Every color also has a fixed page, so a reading can be opened again or found from search. The language at the site root has no prefix. Every other language lives under its `prefix`:

- `/cards/the-fool/` and `/en/cards/the-fool/`
- `/cards/the-fool/white/` and `/en/cards/the-fool/white/`

## Layout

`public/` is the site. `data/` holds the cards. `data/languages.json` is the list of languages.

```
public/index.html          Home for the language at the site root
public/<prefix>/index.html Home for every other language
public/app.js              The draw, shared by every home
public/languages.js        Draw settings, generated from languages.json
public/lang.css            Body fonts, generated from languages.json
public/meanings.js         Card meanings for the root language
public/meanings.<id>.js    Card meanings for every other language
public/cards/              Library for the root language
public/<prefix>/cards/     Library for every other language
data/<card>/card.json      Names, colors, and file names
data/<card>/face.jpg       The card face
data/<card>/<color>.txt    Color story for the root language
data/<card>/<color>.<id>.txt
                           Color story for every other language
data/<card>/<color>.jpg    The scene, with the color in a mirror
```

The draw reads the story file named by that language's `textField` in `card.json`. Japanese uses `text` (`white.txt`). English uses `textEn` (`white.en.txt`). Traditional Chinese uses `textZh` (`white.zh.txt`).

## Preview

Start a static server at the repository root. A language that is not at the site root loads pictures and stories from `/data`, so the server root has to be this directory, not `public/`.

```sh
python3 -m http.server 8741
```

- Japanese: http://127.0.0.1:8741/public/
- English: http://127.0.0.1:8741/public/en/
- Traditional Chinese: http://127.0.0.1:8741/public/zh/

Add `?test=1-1` to draw a chosen card and color. The first number is the card, from 1 to 22 in major-arcana order. The second is the color: 1–10 upright, 11–20 reversed. Example: `?test=22-1` is The World, upright, first color.

## Library pages

Card and color pages are generated from `data/` and the meanings files.

```sh
python3 scripts/build_library.py
```

That rewrites one library per language, `public/languages.js`, `public/lang.css`, and `public/sitemap.xml`. It also refreshes the language switcher and `hreflang` links on each home. Pages for the same card and color point at each other. The language marked `default` is `x-default`.

## Adding a language

1. Add one object to `data/languages.json`. Copy an existing object and change `id`, `htmlLang`, `hreflang`, `prefix`, `switchLabel`, `cookie`, `session`, names, story fields, and the `copy` and `pages` strings. Leave `prefix` empty only for the language at the site root. Set `days` only for Japanese. Set `default` on exactly one language.
2. Write `public/meanings.<id>.js` with `window.MEANINGS`, one entry per card, `upright` and `reversed`.
3. Add a story file and `card.json` fields for every color. The file stem is the color slug plus `textSuffix` (`white.ko.txt`). `textField` and `colorName` name the new keys (`textKo`, `nameKo`). `cardName` names the card (`nameKo`).
4. Copy `public/en/index.html` to `public/<prefix>/index.html`. Translate the visible writing, set `html lang` to `htmlLang`, and point the meanings script at `../meanings.<id>.js`.
5. Run `python3 scripts/build_library.py`.

The build writes the libraries, the draw settings, the body font, the home switchers, and `hreflang`. A new language does not get its own contact, privacy, days, design, or cafe pages. Put those links, with labels in the new language, in the `footer` list. If the language needs a face different from Shippori Mincho, set `fontFamily` and put the Google font query in `fonts`. The home's font link is rewritten from `fonts`.
