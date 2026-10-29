This dataset is part of the Wilde Short Fiction project, an initiative by Regina M. Ponciano. It addresses one of the main problems for students of Oscar Wilde's three short story collections <em>The Happy Prince and Other Tales</em> (1888), <em>Lord Arthur Savile's Crime and Other Stories</em> (1891), and <em>A House of Pomegranates</em> (1891): a lack of primary sources to study their evolution and contexts. In its current form, this dataset provides manual transcriptions of contemporary reviews to these collections. These materials give hitherto-unknown insights into the reception of Wilde's short fiction, and the role the collections played in the establishment of Wilde’s career as a reputable writer.

The dataset is a `.csv` file which includes manual transcriptions of contemporary reviews related to Wilde’s short story collections as well as relevant metadata, such as the periodicals’ names and countries of publication, the date of publication of the reviews, and static URLs to the source of these materials. Future iterations of this project aim to include richer metadata for more sophisticated forms of analyses.

The Wilde Short Fiction project is ongoing and open for contributions. Please consider contributing <a href="https://wildeshortfiction.com/contribute">through the website</a>.   

This dataset is licensed under <a href="https://creativecommons.org/licenses/by/4.0/deed.en">CC BY 4.0 DEED</a>, meaning that all content can be shared, adapted, and redistributed but has to be attributed to the Wilde Short Fiction dataset. Every review includes in its metadata a “how to cite” section to do so.

How the reviews were found and transcribed is described in [METHODOLOGY.md](METHODOLOGY.md). To cite the dataset as a whole, use the "Cite this repository" button on GitHub, which reads [CITATION.cff](CITATION.cff).

The columns of `data.csv` are described in [datapackage.json](datapackage.json), a [Frictionless Data Package](https://datapackage.org/) that also holds the checks every row must pass. These checks run on every change to the data (`python scripts/validate.py`), and every `archive_url` is checked for broken links once a month (`python scripts/check_links.py`).

`data.csv` is generated from the project's working spreadsheet, never edited by hand: only records cleared for publication are exported. Each export arrives as a pull request from the `publish/auto` branch, opened by `.github/workflows/publish-pr.yml` with the export's log as its description; merging it publishes the update.

The enumerative bibliography shown at <a href="https://wildeshortfiction.com/bibliography/enumerative">wildeshortfiction.com/bibliography/enumerative</a> lives in [bibliography.json](bibliography.json) as [CSL-JSON](https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html), the format Zotero and other reference managers import and export. The website formats every entry in MLA style from this file. Its checks (types, DOIs, links, duplicates) run on every change (`python scripts/validate_bibliography.py`).

The master copy of the bibliography is a Zotero group library. Once `zotero.libraryId` is filled in, [bibliography.config.json](bibliography.config.json), the one place for every setting of this pipeline, makes two monthly jobs run:

- `scripts/export_bibliography.py` regenerates `bibliography.json` from the main Zotero collection and commits it if it changed. Add or correct entries in Zotero, not in this file: the next export overwrites hand edits. To pin an entry's `id`, put a line `Citation Key: yourid` in its Extra field; otherwise one is generated from the first author, year and first title word.
- `scripts/discover_publications.py` searches OpenAlex and Crossref for new work on Wilde's short fiction and files it in the collection's "To review" sub-collection. Moving an item into the main collection approves it; moving it to "Rejected" dismisses it for good.

Both need a Zotero API key with access to the group, stored as the repository secret `ZOTERO_API_KEY` (never in the repository). `OPENALEX_API_KEY` is optional. Each job can also be started by hand from the Actions tab.
