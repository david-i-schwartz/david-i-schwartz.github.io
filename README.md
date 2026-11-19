# david-i-schwartz.github.io — how to change it

**The site:** https://david-i-schwartz.github.io/

Everyday editing happens in a web form, not in files. Same setup as the Saints & Winos site.

## To change anything

1. Go to **app.pagescms.org** and sign in with GitHub.
2. Open **david-i-schwartz.github.io**.
3. Pick what you want to change from the menu on the left. Fill in the boxes. Hit **Save**.
4. Wait a minute or two, then reload the site.

## Everyday jobs

| I want to… | Go to | Then |
|---|---|---|
| Write a blog post | **Blog posts** | Add an entry: title, date, then write. Photos go in through the toolbar's image button; a cover photo is optional. Save, and it appears on the Blog page, the home page, and the RSS feed. |
| Add a project, course, role, or hobby | **Projects & Interests** | Add an entry. Title, *Where it shows*, and *Status* are the ones that matter; everything else is optional. The write-up box takes normal typing (bold, links, and pictures via the toolbar). |
| Archive a project | **Projects & Interests** | Open it, set *Status* to Archived, Save. It moves to the Archived list on its own. |
| Add a how-to video | **How-to videos** | Add an item: title, YouTube link (Share, then Copy), pick Teaching or Interests. Or add it inside a project's *Videos* list so it shows on that project's page. |
| Add a paper, talk, or game | **CV · 5. Publications** | Add an item: type, year, paste the citation. It appears on the Publications page and the CV at once. |
| Add a grant, course, student, committee, or award | The matching **CV · …** form | Add an item, Save. The CV page and the section pages rebuild from the same data. |
| Update the downloadable CV | **Settings** | Upload the new PDF in the *CV as a PDF* box. The Download button points at whatever is there. |
| Change my photo, title line, tagline, or links | **Settings** | Leave a box blank and that thing just doesn't show. |
| Change the bio on the home page | **Home page text** | Edit, Save. |
| Change a section's intro line | **Section pages** | Open the page, edit *Intro line*. |

Tips:

- Photos uploaded through a project form land in `photos/projects`; your portrait goes in `photos/site`. The upload button already points at the right folder.
- Phone photos are fine. Smaller copies load faster.
- Pages CMS keeps every save as a commit, so anything can be undone.

---

## For Dave (the plumbing)

**How it works.** A GitHub Actions workflow (`.github/workflows/pages.yml`) builds the site with Jekyll on every save to `main`. Pages CMS (free, hosted) provides the forms; its config is `.pages.yml`. Content is Markdown and YAML:

| What | Where |
|---|---|
| Blog posts | `_posts/YYYY-MM-DD-title.md`; RSS at `/feed.xml` (jekyll-feed) |
| Projects, courses, roles, hobbies | `_projects/*.md`. `area` picks the page (research → Projects, teaching → Teaching, leadership → Service, interests → Making & Interests); `status` is current or archived. |
| CV data | `_data/cv/*.yml` — positions, education, administration, funding, publications, press, teaching, theses, service, awards. The CV page, Publications, Teaching, and Service pages all read from here. |
| How-to videos | `_data/howtos.yml` |
| Name, photo, links, CV PDF | `_data/settings.yml` |
| Section pages (intro lines) | `pages/*.md`; each page's `layout` picks its template |
| Home page bio | `index.md` |
| Uploads | `photos/` (images), `files/` (PDFs) |
| The look | `_layouts/`, `_includes/`, `assets/` |
| Wiring | `_config.yml`, `.pages.yml` |
| CV import script | `_tools/cv_to_yaml.py` — regenerates `_data/cv/` from a Markdown export of the Word CV. Only needed if you ever want to re-import the whole CV instead of editing items in the CMS. |

**One-time setup.**
1. Repo **Settings → Pages**: Source **GitHub Actions**.
2. Sign in at app.pagescms.org with GitHub and add this repo (it already has the Pages CMS app from the band site; just pick the repo).

**What editors type is checked.** Text is escaped wherever a template prints it; links only become links when they start with `https://` or `http://` (`_includes/safe-url.html`); a video needs YouTube's 11-character ID (`_includes/video.html`); photos must be a path on this site or an https:// address (`_includes/safe-img.html`). Write-ups and the bio are Markdown on purpose and aren't escaped.

**Printing the CV.** The CV page has a print stylesheet; "Print this page" in a browser gives a reasonable PDF. The uploaded PDF in Settings is still the canonical one for now.

**Old site.** The previous Minimal Mistakes / academicpages site lives in the `legacy-2024` branch.
