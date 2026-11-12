# PET website

This `docs/` folder is the PET website, served by GitHub Pages.

- `index.html`: the whole site (styles, content and scripts in one file, no build step)
- `assets/`: favicon and screenshots (`assets/img/SHOTS.md` lists every screenshot name)
- `figures/`: project diagrams; the site links to `figures/pet_framework.png`
- `.nojekyll`: tells GitHub Pages to serve the files as they are

## Turn it on
GitHub repository → Settings → Pages → Source: "Deploy from a branch",
Branch: `main`, Folder: `/docs`. The site appears at
https://chhabhayamanan.github.io/PET/.

## Update a screenshot
Replace the PNG in `assets/img/` with a file of the same name. The page picks it up automatically.

## Edit text
Open `index.html`. Page content is in the middle of the file, between `<main>` and `</footer>`.
